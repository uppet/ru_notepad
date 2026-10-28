#!/usr/bin/env python3
"""Strict fixed-artifact stage3 diagnostic driver. Never product acceptance."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import stat
import struct
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import profile_stage3_markdown as profile
CORE='26cc8a210d5cef2bd8ab37b6c270833884ea39a5'
CORE_TREE='847c68b4569e12ffaf8ae4c5b500fdbaad7b801d'
APP='1da616554198792ad8653718e6e9f8999e7658e6'
APP_TREE='0c0c1f4d2fdf4c51faa218cd5a543a7fc570a320'
RUN=40435043501
ARTIFACT=12704836670
ZIP_SIZE=36228771
ZIP_SHA='1687d5640f625dd8181f447bcfe6a9ce566022f0b9694cda942ed046589be2e3'
REPO='uppet/ru-language'
API='https://api.github.com/repos/'+REPO
TOOL_NAMES=('clang','llvm-as','llvm-link','opt','llvm-dis','llc')


PHASE='preflight'


class DriverValidationError(ValueError):
    def __init__(self,reason):
        super().__init__('Fixed diagnostic validation failed')
        self.reason=reason


def checkpoint(output,phase):
    global PHASE
    PHASE=phase
    (Path(output)/'driver-progress.json').write_text(json.dumps({'status':'NOT_ACCEPTED','accepted':False,'phase':phase}),encoding='utf-8')


def require(value,message):
    if not value:raise DriverValidationError(message)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def identity(path):return profile.identity(path)


class ArtifactHTTPError(RuntimeError):
    def __init__(self,stage,status):
        super().__init__('Fixed artifact HTTP failure')
        self.stage=stage;self.status=int(status)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


def json_api(path,token):
    req=urllib.request.Request(API+path,headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'ru-notepad-fixed-stage3-diagnostic'})
    try:
        with urllib.request.build_opener(NoRedirect).open(req,timeout=30) as response:
            raw=response.read(1024*1024+1)
        require(len(raw)<=1024*1024,'API metadata exceeds bound')
        return json.loads(raw)
    except urllib.error.HTTPError as exc:
        raise ArtifactHTTPError('metadata',exc.code) from None


def check_metadata(run,artifact):
    require(run.get('id')==RUN and run.get('head_sha')==CORE and run.get('run_attempt')==1 and
            run.get('status')=='completed' and run.get('conclusion')=='success','fixed core run identity/status mismatch')
    require(run.get('repository',{}).get('full_name')==REPO,'wrong artifact repository')
    require(artifact.get('id')==ARTIFACT and artifact.get('expired') is False and artifact.get('size_in_bytes')==ZIP_SIZE
            and artifact.get('digest')=='sha256:'+ZIP_SHA,'fixed artifact metadata mismatch')
    require(artifact.get('workflow_run',{}).get('id')==RUN and artifact.get('workflow_run',{}).get('head_sha')==CORE,
            'artifact belongs to different run/head')
    require(artifact.get('archive_download_url')==API+f'/actions/artifacts/{ARTIFACT}/zip','unexpected artifact download endpoint')
    return {'repository':REPO,'run_id':RUN,'run_attempt':1,'head_sha':CORE,'artifact_id':ARTIFACT,
            'size':ZIP_SIZE,'sha256':ZIP_SHA,'conclusion':'success','expired':False}


def blob_destination(url):
    parsed=urllib.parse.urlsplit(url)
    require(parsed.scheme=='https' and parsed.hostname and not parsed.username and not parsed.password
            and parsed.port in (None,443),'invalid artifact redirect origin')
    host=parsed.hostname.lower()
    require(host.endswith('.blob.core.windows.net') or host.endswith('.actions.githubusercontent.com'),
            'unreviewed artifact redirect host')
    return url


def download_fixed(path):
    token=os.environ.get('GITHUB_TOKEN','')
    require(bool(token),'GITHUB_TOKEN required for fixed read-only artifact download')
    metadata=check_metadata(json_api(f'/actions/runs/{RUN}',token),json_api(f'/actions/artifacts/{ARTIFACT}',token))
    request=urllib.request.Request(API+f'/actions/artifacts/{ARTIFACT}/zip',headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','User-Agent':'ru-notepad-fixed-stage3-diagnostic'})
    opener=urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request,timeout=30):raise RuntimeError('Expected a signed artifact redirect')
    except urllib.error.HTTPError as exc:
        if exc.code not in (302,303,307):raise ArtifactHTTPError('download',exc.code) from None
        url=blob_destination(exc.headers.get('Location',''))
    # Never forward API authorization to the blob or emit the signed URL.
    try:
        blob=urllib.request.Request(url,headers={'User-Agent':'ru-notepad-fixed-stage3-diagnostic'})
        with opener.open(blob,timeout=60) as response,Path(path).open('xb') as stream:
            total=0
            while True:
                block=response.read(1024*1024)
                if not block:break
                total+=len(block);require(total<=ZIP_SIZE,'artifact exceeds fixed size');stream.write(block)
    except urllib.error.HTTPError as exc:
        raise ArtifactHTTPError('blob',exc.code) from None
    require(Path(path).stat().st_size==ZIP_SIZE and sha(path)==ZIP_SHA,'artifact full ZIP identity mismatch')
    return metadata


def extract_fixed(archive,directory):
    require(Path(archive).stat().st_size==ZIP_SIZE and sha(archive)==ZIP_SHA,'unverified ZIP cannot be extracted')
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    names=set();total=0
    with zipfile.ZipFile(archive) as bundle:
        require(len(bundle.infolist())<=4096,'artifact member bound exceeded')
        for member in bundle.infolist():
            name=member.orig_filename
            require(name==member.filename,'normalized artifact member name rejected')
            relative=PurePosixPath(name)
            require(name and '\\' not in name and ':' not in name and not relative.is_absolute()
                    and all(p not in ('','..','.') for p in relative.parts),'unsafe artifact member')
            require(name.casefold() not in names,'duplicate/case-colliding artifact member');names.add(name.casefold())
            require(not stat.S_ISLNK(member.external_attr>>16) and not member.flag_bits&1,'linked/encrypted artifact member')
            total+=member.file_size
            require(member.file_size<=128*1024*1024 and total<=512*1024*1024,'artifact expansion bound exceeded')
            dest=directory.joinpath(*relative.parts)
            require(dest.resolve().is_relative_to(directory.resolve()),'artifact member escapes root')
            if member.is_dir():dest.mkdir(parents=True,exist_ok=True);continue
            dest.parent.mkdir(parents=True,exist_ok=True)
            with bundle.open(member) as source,dest.open('xb') as target:
                copied=0
                while True:
                    block=source.read(1024*1024)
                    if not block:break
                    copied+=len(block);require(copied<=member.file_size,'artifact member expansion changed');target.write(block)
            require(copied==member.file_size,'artifact member truncated')
    for name in ('stage3.exe','report.json','verification.json'):
        require((directory/name).is_file(),'missing exact root artifact member: '+name)
    return directory


def pe_x64(path):
    data=Path(path).read_bytes();require(data[:2]==b'MZ' and len(data)>=64,'not PE')
    offset=struct.unpack_from('<I',data,60)[0]
    require(offset+26<=len(data) and data[offset:offset+4]==b'PE\0\0' and struct.unpack_from('<H',data,offset+4)[0]==0x8664
            and struct.unpack_from('<H',data,offset+24)[0]==0x20b,'not x64 PE32+')


def load_file(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def clean_environment(environment):
    forbidden=('TOKEN','SECRET','PASSWORD','CREDENTIAL','PRIVATE_KEY','ACCESS_KEY')
    return {k:v for k,v in environment.items() if not any(word in k.upper() for word in forbidden)
            and k.upper() not in ('SSH_AUTH_SOCK','GIT_ASKPASS','SSH_ASKPASS')}


def verify_generated_sources(proof,prepared,source,core,frozen):
    expected={str((prepared/name).resolve()) for name in profile.SOURCE_NAMES}
    # Exact26cc bootstrap.py includes the native standard-library inventory even
    # when the two actual dependencies do not import it. Match that producer rule.
    expected.update(str(p.resolve()) for p in (core/'rulang/stdlib').rglob('*.ru') if p.is_file())
    require(expected<=set(frozen),'source inventory contains an unfrozen or untracked module')
    inventory=proof.get('source_inventory',[]);dependencies=proof.get('dependencies',[])
    require(len(inventory)==len(expected) and {r.get('path') for r in inventory}==expected,'generated plus exact tracked stdlib source inventory mismatch')
    required={str(source.resolve()),str((prepared/'markdown_policy.ru').resolve())}
    require(len(dependencies)==2 and {r.get('path') for r in dependencies}==required,'entry and exact policy dependency proof required')


def main_run(core,editor,output):
    require(sys.platform=='win32' and platform.machine() in ('AMD64','x86_64'),'actual Windows x64 required')
    core,editor,output=map(lambda p:Path(p).resolve(),(core,editor,output))
    require(not output.exists() and not any(output.is_relative_to(p) for p in (core,editor,HERE)),'fresh external diagnostic output required')
    output.mkdir(parents=True)
    sys.path.insert(0,str(editor/'tools'))
    import build_bootstrap_release as build
    import bootstrap_provenance as provenance
    import compile_bootstrap_native as wrapper
    require(Path(build.__file__).resolve()==editor/'tools/build_bootstrap_release.py' and Path(wrapper.__file__).resolve()==editor/'tools/compile_bootstrap_native.py' and Path(provenance.__file__).resolve()==editor/'tools/bootstrap_provenance.py','wrong production validator/wrapper import')
    checkpoint(output,'source-identity')
    core_files=build.snapshot(core,CORE,CORE_TREE);app_files=build.snapshot(editor,APP,APP_TREE)
    frozen={str((root/name).resolve()):digest for root,files in ((core,core_files),(editor,app_files)) for name,digest in files.items()}
    archive=output/'fixed-core-artifact.zip'
    checkpoint(output,'download-fixed-artifact')
    try:metadata=download_fixed(archive)
    finally:
        sanitized=clean_environment(os.environ)
        for key in list(os.environ):
            if key not in sanitized:os.environ.pop(key,None)
    checkpoint(output,'extract-fixed-artifact')
    directory=extract_fixed(archive,output/'accepted-core-artifact')
    (output/'artifact-identity.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    checkpoint(output,'toolchain-discovery')
    sys.path.insert(0,str(core))
    from rulang.llvm_toolchain import LLVMToolchain
    toolchain=LLVMToolchain();require(len(toolchain.clang)==1,'unexpected clang argv')
    tools={'clang':str(Path(toolchain.clang[0]).resolve()),**{k:str(Path(v).resolve()) for k,v in toolchain.tools.items()},
           'linker':str((Path(os.environ['VCToolsInstallDir'])/'bin/Hostx64/x64/link.exe').resolve())}
    require(set(tools)==set(TOOL_NAMES)|{'linker'},'tool inventory changed')
    tool_records={k:identity(v) for k,v in tools.items()};frozen.update({r['path']:r['sha256'] for r in tool_records.values()})
    env_module=load_file('_profile_llvm_environment',core/'rulang/toolchain_environment.py');environment=env_module.llvm_environment()
    require(not any(environment.get(k) for k in ('CL','_CL_','LINK','_LINK_')),'ambient compiler/linker flags forbidden')
    environment=clean_environment(environment)
    commands=[]
    def run(command,**kwargs):
        command=list(map(str,command));commands.append(command)
        number=len(commands);stdout=output/f'command-{number:02d}.stdout.log';stderr=output/f'command-{number:02d}.stderr.log'
        with stdout.open('x',encoding='utf-8') as out,stderr.open('x',encoding='utf-8') as err:
            result=subprocess.run(command,stdout=out,stderr=err,text=True,encoding='utf-8',env=environment,timeout=kwargs.pop('timeout',600),**kwargs)
        require(stdout.stat().st_size<=8*1024*1024 and stderr.stat().st_size<=8*1024*1024,'build/probe log exceeds bound')
        require(result.returncode==0,'diagnostic build/probe command failed: '+str(number));return stdout.read_text(encoding='utf-8')
    checkpoint(output,'toolchain-probes')
    require(re.match(r'clang version 14\.',run([tools['clang'],'--version'])) is not None,'LLVM14 clang required')
    for name in TOOL_NAMES[1:]:require(re.search(r'LLVM version 14\.',run([tools[name],'--version'])) is not None,'mixed LLVM versions')
    probe=run([tools['clang'],'-S','-emit-llvm','-x','c','-','-o','-'],input='')
    triples=re.findall(r'^target triple = "([^"]+)"',probe,re.M);layouts=re.findall(r'^target datalayout = "([^"]+)"',probe,re.M)
    require(len(triples)==len(layouts)==1 and re.fullmatch(r'x86_64-pc-windows-msvc(?:[0-9]+(?:\.[0-9]+)*)?',triples[0]),'unsupported target')
    triple,layout=triples[0],layouts[0]
    comparator=load_file('_profile_trusted_comparator',core/'tools/bootstrap_compare.py')
    checkpoint(output,'accepted-bootstrap-provenance')
    bootstrap=provenance.validate(core,directory,directory/'verification.json',CORE,CORE_TREE,comparator.compare_native,expected_triple=triple,expected_data_layout=layout)
    verification=json.loads((directory/'verification.json').read_text(encoding='utf-8'));cycle=json.loads((directory/'report.json').read_text(encoding='utf-8'))
    require(cycle==verification['bootstrap'],'report and verification bootstrap cycle differ')
    compiler=directory/'stage3.exe';pe_x64(compiler);frozen[str(compiler.resolve())]=sha(compiler)
    require(cycle['stages'][-1]['binary_sha256']==sha(compiler),'stage3 differs from accepted report')
    checkpoint(output,'prepare-fixed-harnesses')
    prepared=output/'prepared';profile.prepare(editor/'src/markdown_policy.ru',prepared)
    for path in prepared.iterdir():
        if path.is_file():frozen[str(path.resolve())]=sha(path)
    for path in HERE.glob('*.py'):frozen[str(path.resolve())]=sha(path)
    (output/'frozen-inputs.json').write_text(json.dumps(frozen,indent=2),encoding='utf-8')
    builds={};binaries={}
    for kind in ('policy','control'):
        target=output/kind;target.mkdir();source=prepared/(kind+'.ru');binary=target/(kind+'.exe');ir=target/(kind+'.ll');proof_path=target/'proof.json'
        checkpoint(output,'compile-'+kind)
        run(build.native_compile_command(core,source,compiler,prepared,tools,proof_path,ir,binary))
        checkpoint(output,'verify-'+kind)
        proof=json.loads(proof_path.read_text(encoding='utf-8'))
        build.verify_proof(proof,source=source,compiler=compiler,ir=ir,binary=binary,triple=triple,layout=layout,frozen=frozen,tools=tools,proof_path=proof_path)
        verify_generated_sources(proof,prepared,source,core,frozen)
        pe_x64(binary)
        for name,digest in frozen.items():require(sha(name)==digest,'frozen input changed during compilation')
        builds[kind]={'binary':identity(binary),'native_wrapper_validated':True,'proof':identity(proof_path),
                      'wrapper_receipt':identity(binary.with_name(binary.name+'.native-wrapper.json')),'compiler':identity(compiler)}
        binaries[kind]=binary
    build.snapshot(core,CORE,CORE_TREE);build.snapshot(editor,APP,APP_TREE)
    receipt={'status':'NOT_ACCEPTED','accepted':False,'artifact':metadata,'bootstrap':bootstrap,'stage3':identity(compiler),
             'source_commit':APP,'source_tree':APP_TREE,'trusted_comparator':identity(core/'tools/bootstrap_compare.py'),'verification':identity(directory/'verification.json'),'cycle_report':identity(directory/'report.json'),'tools':tool_records,'builds':builds,'commands':commands,
             'scope':'Fixed accepted compiler reused; new pure policy harness only. No GUI/editor acceptance.'}
    (output/'build-identity.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    checkpoint(output,'measure-six-fixed-processes')
    report=profile.measure(prepared,binaries,output/'measurement',builds)
    checkpoint(output,'verify-post-measurement')
    for name,digest in frozen.items():require(sha(name)==digest,'frozen input changed during measurement')
    require(report.get('diagnostic_completed') is True and report.get('all_outputs_validated') is True,'six fixed measurements did not complete validation')
    checkpoint(output,'diagnostic-completed-not-accepted')
    return report


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--core',type=Path,required=True);parser.add_argument('--editor',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    try:main_run(args.core,args.editor,args.output)
    except Exception as exc:
        # Exception URLs/headers may carry a signed blob query. Do not print them.
        if args.output.is_dir():
            failure={'status':'NOT_ACCEPTED','accepted':False,'phase':PHASE,'error_type':type(exc).__name__}
            if isinstance(exc,DriverValidationError):failure['validation_reason']=exc.reason[:256]
            if isinstance(exc,ArtifactHTTPError):failure.update(artifact_http_stage=exc.stage,http_status=exc.status)
            (args.output/'driver-failure.json').write_text(json.dumps(failure),encoding='utf-8')
        print('NOT_ACCEPTED: stage3 diagnostic driver failed ('+type(exc).__name__+')',file=sys.stderr)
        raise SystemExit(1)

if __name__=='__main__':main()
