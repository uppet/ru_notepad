#!/usr/bin/env python3
"""Fixed-artifact Windows modal diagnostic; never build, acceptance or delivery."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import time
from unittest.mock import patch
import zipfile

REPOSITORY='uppet/ru_notepad'
RUN_ID=40484690558
HEAD='f0da2b224d224f377c3f90e0eb4b0e94f6a71fa0'
TREE='ebcab86300e23390b6cd69aa55da8dd3e8e0a7b2'
ARTIFACT_ID=12728275345
ARTIFACT_NAME='NOT-ACCEPTED-diagnostic-runtime-'+HEAD
ZIP_SHA256='787408015a04193713f686030b88e79413754c87318e17f227017c65fd44dcf0'
ZIP_SIZE=4358091
PRODUCT_SHA256='90f09299524146077df6568103b172231b0e0e84e08741474f7f6f09322d6b5e'
FILES={
 'ru_notepad.exe':('a2397a26bf1098f0652b3e2e5f4143d50591f7c07ec6f9c8db006d7ba5058278',7016448),
 'Scintilla.dll':('f2ffb884a76ba9c562750124a0d31d6f5b1ebc2f1423bb77da5a282d8af27bbf',2256384),
 'Lexilla.dll':('8984f67d256f000995ba404cae12e547cf43aafd4ecdcbea86f8bf51cd4f01fa',2860032),
 'RuSyntax.dll':('d381c2069403c2b8823c6e857de40390a607c7e6c30bfae1bcc58f86a4bfd8af',32256),
 'compile-proof.json':('9a5dac2454b461b1318c07e4d56b9814518ef861a6a6d747e86be2c2c29817f1',36799)}
RUNTIME=tuple(name for name in FILES if name!='compile-proof.json')
MEMBERS=set(FILES)|{'NOT_ACCEPTED.json'}


def require(condition,message):
    if not condition:raise ValueError(message)


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_metadata(artifact,run):
    require(isinstance(artifact,dict) and isinstance(run,dict),'metadata objects required')
    require(type(artifact.get('id')) is int and artifact['id']==ARTIFACT_ID,'artifact id mismatch')
    require(artifact.get('name')==ARTIFACT_NAME and artifact.get('expired') is False,'artifact identity/expiry mismatch')
    require(type(artifact.get('size_in_bytes')) is int and artifact['size_in_bytes']==ZIP_SIZE
            and artifact.get('digest')=='sha256:'+ZIP_SHA256,'artifact digest/size mismatch')
    origin=artifact.get('workflow_run',{})
    require(isinstance(origin,dict) and isinstance(run.get('repository'),dict),'metadata origin objects required')
    require(origin.get('id')==RUN_ID and origin.get('head_sha')==HEAD
            and origin.get('repository_id')==1421718936 and origin.get('head_repository_id')==1421718936,'artifact run mismatch')
    require(type(run.get('id')) is int and run['id']==RUN_ID and run.get('head_sha')==HEAD
            and run.get('status')=='completed' and run.get('conclusion')=='failure'
            and run.get('repository',{}).get('full_name')==REPOSITORY,'fixed source run mismatch')
    return {'repository':REPOSITORY,'run_id':RUN_ID,'head_sha':HEAD,'artifact_id':ARTIFACT_ID,
            'artifact_name':ARTIFACT_NAME,'zip_sha256':ZIP_SHA256,'zip_bytes':ZIP_SIZE}


def validate_zip_inventory(archive):
    entries=archive.infolist()
    require(len(entries)==len(MEMBERS) and {i.filename for i in entries}==MEMBERS,'exact six-file ZIP inventory required')
    for entry in entries:
        require(not entry.is_dir() and entry.filename==Path(entry.filename).name and '/' not in entry.filename
                and '\\' not in entry.filename and not entry.flag_bits&1,'unsafe ZIP member')
        mode=(entry.external_attr>>16)&0xffff
        require(not stat.S_ISLNK(mode) and (stat.S_IFMT(mode) in (0,stat.S_IFREG)), 'linked/nonregular ZIP member')
        require(0<entry.file_size<=8*1024*1024 and entry.compress_size<=ZIP_SIZE,'unbounded ZIP member')
    require(sum(i.file_size for i in entries)<=16*1024*1024,'unbounded ZIP total')


def validate_runtime(directory):
    directory=Path(directory)
    require({p.name for p in directory.iterdir()}==MEMBERS,'runtime inventory differs')
    require(not any(p.is_symlink() for p in (directory,*directory.parents)),'linked runtime directory')
    for name,(digest,size) in FILES.items():
        p=directory/name
        require(p.is_file() and not p.is_symlink() and p.stat().st_size==size and sha(p)==digest,'runtime bytes differ: '+name)
    marker_path=directory/'NOT_ACCEPTED.json'
    require(marker_path.is_file() and not marker_path.is_symlink() and marker_path.stat().st_size<=65536,'invalid marker')
    marker=json.loads(marker_path.read_text(encoding='utf-8'))
    require(marker.get('schema')=='ru-notepad-not-accepted-runtime-v1' and marker.get('status')=='NOT_ACCEPTED'
            and marker.get('user_delivery_authorized') is False and marker.get('product_status')=='failed'
            and marker.get('product_receipt_sha256')==PRODUCT_SHA256,'accepted/foreign runtime forbidden')
    require(marker.get('files')=={n:{'sha256':h,'size':s} for n,(h,s) in FILES.items()},'marker file identity mismatch')
    require(isinstance(marker.get('source_pins'),dict),'marker source object required')
    pin=marker['source_pins'].get('app_source',{})
    require(isinstance(pin,dict),'marker app source object required')
    require(pin.get('commit')==HEAD and pin.get('tree')==TREE,'marker source mismatch')
    return {n:FILES[n][0] for n in RUNTIME}


def extract_runtime(archive_path,destination):
    archive_path,destination=Path(archive_path),Path(destination)
    require(archive_path.stat().st_size==ZIP_SIZE and sha(archive_path)==ZIP_SHA256,'download ZIP identity mismatch')
    require(not destination.exists(),'refuse existing extraction destination')
    with zipfile.ZipFile(archive_path) as archive:
        validate_zip_inventory(archive)
        require(archive.testzip() is None,'ZIP CRC failure')
        destination.mkdir()
        for entry in archive.infolist():
            with (destination/entry.filename).open('xb') as target:target.write(archive.read(entry))
    return validate_runtime(destination)


def gh_json(endpoint):
    result=subprocess.run(['gh','api','--hostname','github.com',endpoint],capture_output=True,timeout=60)
    require(result.returncode==0 and len(result.stdout)<=1024*1024,'GitHub metadata request failed')
    return json.loads(result.stdout)


def acquire(output):
    base='repos/'+REPOSITORY+'/actions/'
    metadata=validate_metadata(gh_json(base+'artifacts/'+str(ARTIFACT_ID)),gh_json(base+'runs/'+str(RUN_ID)))
    archive=output/'artifact.zip'
    with archive.open('xb') as stream:
        result=subprocess.run(['gh','api','--hostname','github.com',base+'artifacts/'+str(ARTIFACT_ID)+'/zip'],stdout=stream,stderr=subprocess.PIPE,timeout=90)
    require(result.returncode==0,'fixed artifact download failed')
    runtime=output/'runtime';hashes=extract_runtime(archive,runtime)
    return runtime,hashes,metadata


def child_environment(environment):
    # Downloader credentials and runner tokens are not application inputs.
    return {k:v for k,v in environment.items() if 'TOKEN' not in k.upper() and 'SECRET' not in k.upper()
            and k.upper() not in ('SYSTEM_ACCESSTOKEN','GH_TOKEN','GITHUB_TOKEN')}


def diagnose(runtime,hashes,evidence):
    import windows_ci as ci
    import gui_instance_tabs as instance
    import winreg
    api=ci.Windows();cases=[]
    with patch.dict(os.environ,child_environment(os.environ),clear=True):
        for label,initial,handoff in (('A1-empty-on',1,False),('A0-empty-off',0,False),('B1-handoff-duplicate-on',1,True)):
            observations={};children=[];case={'case':label,'initial_dword':initial,'observations':observations,'children':children,
                                             'registry_cleaned':False,'accepted':False}
            cases.append(case);case_root=evidence.parent/label;case_root.mkdir()
            instance._copy_runtime(runtime,case_root/'owner',hashes)
            documents=[]
            for index in range(2):
                path=case_root/f'{index} 中文 😀 sample.txt';path.write_bytes(f'modal diagnostic {index} 中文\r\n'.encode());documents.append(path)
            originals={p.name:sha(p) for p in documents}
            try:
                with instance.isolated_settings() as registry:
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,registry,0,winreg.KEY_SET_VALUE) as key:
                        winreg.SetValueEx(key,'SingleInstance',0,winreg.REG_DWORD,initial)
                    def secondary(purpose,arguments):
                        target=case_root/purpose;instance._copy_runtime(runtime,target,hashes)
                        process=subprocess.Popen([str(target/'ru_notepad.exe'),*map(str,arguments)],cwd=case_root,creationflags=8)
                        row={'purpose':purpose,'pid':process.pid,'exit_code':None,'cleanup_killed':False,'visible_main_seen':False};children.append(row)
                        try:
                            deadline=time.monotonic()+15
                            while process.poll() is None and time.monotonic()<deadline:
                                row['visible_main_seen']|=any(c==ci.MAIN_CLASS and visible for _,c,visible in api.windows(process.pid))
                                time.sleep(.01)
                            process.wait(timeout=1);row['exit_code']=process.returncode
                            require(process.returncode==0 and not row['visible_main_seen'],'handoff child did not exit invisibly')
                        finally:
                            row['last_windows']=instance._modal_observation(api,process,1)
                            row['cleanup_killed']=ci.cleanup_process(process)
                            for i,log in enumerate(sorted(target.glob('ru_notepad-*.log'))[:2]):
                                ci.cap_log(log);shutil.copyfile(log,evidence/(label+'-'+purpose+'-'+str(i)+'.log'))
                    def exercise(process,hwnd):
                        case.update(owner_pid=process.pid,owner_hwnd=int(hwnd))
                        if handoff:
                            secondary('handoff',[p.name for p in documents])
                            instance._wait_ready(api,process,hwnd,3,'diagnostic handoff exact two paths',observations)
                            ci.verify_gui_documents(api,hwnd,{p.name:p.read_bytes() for p in documents})
                            secondary('duplicate',[documents[0]])
                            instance._wait_ready(api,process,hwnd,3,'diagnostic duplicate activation',observations,documents[0].name+' · ru_notepad')
                        observations['before command805']=instance._modal_observation(api,process,1)
                        try:
                            instance._toggle_preference(api,process,hwnd,registry,observations,label)
                            observations['toggle_returned']=True
                        finally:
                            observations['after command805']=instance._modal_observation(api,process,1)
                        after=instance._registry_observation(registry)
                        require(after.get('type')==winreg.REG_DWORD and after.get('value')==1-initial,'toggle DWORD differs')
                        return {}
                    case['process']=ci.run_gui(api,case_root/'owner',evidence,name='modal-diagnostic-'+label,exercise=exercise,log_prefix='modal-'+label)
                case['registry_cleaned']=True
            except Exception as exc:
                case['diagnostic_error']=type(exc).__name__
            finally:
                case['source_bytes_unchanged']={p.name:sha(p) for p in documents}==originals
                for folder in [case_root/'owner',*(p for p in case_root.iterdir() if p.is_dir() and p.name!='owner')]:
                    require(all(sha(folder/n)==hashes[n] for n in RUNTIME),'diagnostic runtime changed')
                (evidence/'cases.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return cases


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    output=args.output.resolve();require(not output.exists(),'refuse existing diagnostic output');output.mkdir(parents=True)
    evidence=output/'evidence';evidence.mkdir()
    report={'schema':'ru-notepad-instance-modal-diagnostic-v1','status':'NOT_ACCEPTED','accepted':False,
            'user_delivery_authorized':False,'compiled':False,'packaged':False,'full_feature_ci_required':True,
            'source_run':RUN_ID,'source_head':HEAD,'artifact_id':ARTIFACT_ID,'cases':[]}
    code=1
    try:
        require(sys.platform=='win32','real Windows required')
        runtime,hashes,metadata=acquire(output);report.update(artifact=metadata,runtime_sha256=hashes)
        report['cases']=diagnose(runtime,hashes,evidence);validate_runtime(runtime)
        report['diagnostic_completed']=True;code=0
    except Exception as exc:
        report.update(diagnostic_completed=False,diagnostic_error=type(exc).__name__)
    finally:
        (evidence/'diagnostic.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('NOT_ACCEPTED modal diagnostic evidence recorded; full feature CI still required.')
    return code


if __name__=='__main__':raise SystemExit(main())
