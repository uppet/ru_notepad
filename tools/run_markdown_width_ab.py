#!/usr/bin/env python3
"""Same-job, fixed-source Markdown width diagnostic. No acceptance replacement."""
from __future__ import annotations
import argparse, hashlib, importlib, json, math, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path
from types import SimpleNamespace

BASELINE='6aa535d62c28cc9a03f33c3610fe99b3cf1bd14e'
COMPILER='85c7821fda35aa79deeaf67b4d430f24ddd7f07f'
COMPILER_TREE='a770e367e84d87a0d2fcb6d49ea6f06da2dbe4ba'
POLICY='src/markdown_policy.ru'
POLICIES=('e9658000e1c5fbe5fb49403af2a27eb11a0efb9d4bf5261617b760688ea2d720',
          'e3606ac3806d4b4b0255b10c4600f088bcdacaffab9918f62c91bd5115d648e0')
ADDED={'.github/workflows/markdown-width-ab.yml','tools/run_markdown_width_ab.py',
       'tools/test_markdown_width_ab.py','tools/test_markdown_width_policy.py',
       'docs/markdown-width-ab.md'}
ORDER=(0,1,1,0,0,1,1,0)
PAIRS=((0,1),(3,2),(4,5),(7,6))
ZERO='0'*64
LIMIT=256*1024

def failure_trace(error):
    # Fixed reviewed module IDs, line numbers and exception classes only.
    modules=('run_markdown_width_ab.py','run_markdown_owned_profile.py',
             'run_markdown_phase_profile.py','run_markdown_edit_profile.py','markdown_edit_observers.py')
    kinds={ValueError:1,OSError:2,TimeoutError:3,subprocess.TimeoutExpired:4,KeyError:5,TypeError:6}
    print('WIDTH_AB_EXCEPTION_KIND='+str(kinds.get(type(error),7)))
    tb=error.__traceback__
    while tb is not None:
        name=Path(tb.tb_frame.f_code.co_filename).name
        if name in modules:print('WIDTH_AB_TRACE='+str(modules.index(name)+1)+','+str(tb.tb_lineno))
        tb=tb.tb_next

def need(value):
    if not value:raise ValueError('width_ab_rejected')

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(value):return hashlib.sha256(canonical(value)).hexdigest()
def plain(path, *, directory=False):
    p=Path(os.path.abspath(path))
    for q in (p,*p.parents):
        need(not q.is_symlink())
        if q.exists():need(not (getattr(q.lstat(),'st_file_attributes',0)&0x400))
    need(p.is_dir() if directory else p.is_file())
    if not directory:need(p.stat().st_nlink==1)
    return p.resolve(strict=True)

def under(root, relative):
    need(type(relative) is str and relative and not Path(relative).is_absolute())
    p=plain(root/relative);need(p.is_relative_to(root));return p

def read(path):
    path=plain(path);need(path.stat().st_size<=LIMIT)
    data=path.read_bytes();need(len(data)<=LIMIT)
    def pairs(items):
        d={}
        for k,v in items:need(k not in d);d[k]=v
        return d
    return json.loads(data,object_pairs_hook=pairs,parse_constant=lambda _:need(False))

def git(root,*args):
    r=subprocess.run(['git','-C',str(root),*args],capture_output=True,timeout=30)
    need(r.returncode==0);return r.stdout.decode('utf-8','strict')

def checkout(root, expected):
    root=plain(root,directory=True)
    need(re.fullmatch('[0-9a-f]{40}',expected) is not None)
    need(git(root,'rev-parse','HEAD').strip()==expected)
    need(not git(root,'status','--porcelain'))
    paths=git(root,'ls-files','-z').split('\0');need(paths[-1]=='');paths.pop()
    need(len(paths)==len(set(paths)) and 0<len(paths)<2000)
    return {name:sha(under(root,name)) for name in paths}

def verify_compiler(root):
    checkout(root,COMPILER)
    need(git(root,'rev-parse','HEAD^{tree}').strip()==COMPILER_TREE)

def verify_roots(baseline,candidate,candidate_sha,compiler):
    baseline=plain(baseline,directory=True);candidate=plain(candidate,directory=True)
    compiler=plain(compiler,directory=True)
    need(baseline!=candidate and not baseline.is_relative_to(candidate) and not candidate.is_relative_to(baseline))
    need(not compiler.is_relative_to(baseline) and not compiler.is_relative_to(candidate))
    a=checkout(baseline,BASELINE);b=checkout(candidate,candidate_sha)
    need(set(b)-set(a)==ADDED and not set(a)-set(b))
    need(a[POLICY]==POLICIES[0] and b[POLICY]==POLICIES[1])
    need(all(a[k]==b[k] for k in a if k!=POLICY))
    verify_compiler(compiler)
    return digest({k:a[k] for k in sorted(a) if k!=POLICY})

def load_protocol(root):
    root=plain(root,directory=True)
    # Fresh prepare worker or one canonical coordinator import; never swap ROOT.
    for name in ('package','run_markdown_phase_profile','run_markdown_owned_profile','run_markdown_edit_profile'):
        if name in sys.modules:
            need(Path(sys.modules[name].__file__).resolve().parent==root/'tools')
    sys.path.insert(0,str(root/'tools'))
    p=SimpleNamespace(package=importlib.import_module('package'),base=importlib.import_module('run_markdown_phase_profile'),
                      owned=importlib.import_module('run_markdown_owned_profile'),edit=importlib.import_module('run_markdown_edit_profile'))
    need(p.owned.ROOT.resolve()==root)
    for module in (p.package,p.base,p.owned,p.edit):need(Path(module.__file__).resolve().parent==root/'tools')
    return p

def source_snapshot(root,p):
    result={x.relative_to(root).as_posix():sha(plain(x)) for folder in ('src','tests') for x in sorted((root/folder).glob('*.ru'))}
    result.update({x.relative_to(root).as_posix():sha(plain(x)) for x in sorted((root/'locales').glob('*.json'))})
    result['tools/generate_i18n.py']=sha(under(root,'tools/generate_i18n.py'))
    native=p.package.native_source_snapshot(root)
    for rel,want in native.items():need(sha(under(root,rel))==want)
    result.update(native);return result

def full_receipt(root,binary,cc,p):
    root=plain(root,directory=True);binary=plain(binary,directory=True);cc=plain(cc)
    receipt=read(binary/'ru_notepad.build.json')
    need(receipt['schema']==1 and receipt['ru_commit']==COMPILER and receipt['ru_tree']==COMPILER_TREE)
    need(receipt['entry_source']=='src/main.ru' and receipt['entry_sha256']==sha(under(root,'src/main.ru')))
    need(receipt['source_sha256']==source_snapshot(root,p))
    inputs=tuple(p.package.RESOURCE_INPUTS)+('packaging/diagnostic_launcher.c',)
    need(receipt['build_input_sha256']=={rel:sha(under(root,rel)) for rel in inputs})
    need(receipt['generated_c_sha256']==sha(under(root,'build/main.c')))
    need(receipt['translation_unit_sha256']==sha(under(root,'build/main-gui.c')))
    for name,key in zip(p.base.RUNTIME_NAMES,('exe_sha256','dll_sha256','lexilla_dll_sha256','native_helper_sha256')):
        need(sha(under(binary,name))==receipt[key])
    cmd=receipt['compiler_command'];need(type(cmd) is list and len(cmd)==15)
    need(cmd[1:7]==['-std=c99','-O2','-Wall','-Wextra','-Wno-unused-function','-static-libgcc'])
    need(cmd[8]=='-o' and cmd[10]=='-lm' and cmd[12:]==['-mwindows','-lshell32','-luser32'])
    for index,expected in ((0,cc),(7,root/'build/main-gui.c'),(9,binary/'ru_notepad.exe'),(11,root/'build/app-resource.o')):
        need(plain(cmd[index])==plain(expected))
    helper=read(binary/'RuSyntax.native-build.json');n=helper['build_inputs']
    need(helper['schema']==1 and helper['name']=='RuSyntax.dll' and n['output_name']=='RuSyntax.dll')
    need(n['source_sha256']==p.package.native_source_snapshot(root))
    need(n['driver_sha256']=={rel:sha(under(root,rel)) for rel in p.package.NATIVE_BUILD_DRIVERS})
    need(n['compile_sources']==list(p.package.NATIVE_COMPILE_SOURCES['RuSyntax.dll']))
    need(n['compiler_flags']==list(p.package.NATIVE_CFLAGS) and n['link_libraries']==list(p.package.NATIVE_LINK_LIBRARIES))
    need(plain(n['compiler_path'])==cc and n['compiler_sha256']==sha(cc))
    version=subprocess.run([str(cc),'--version'],capture_output=True,timeout=30);need(version.returncode==0)
    need(hashlib.sha256(version.stdout).hexdigest()==n['compiler_version_sha256'])
    need(helper['build_key']==p.package.native_build_key(n)==receipt['native_helper_build_key'])
    need(helper['dll_sha256']==receipt['native_helper_sha256'])
    return receipt

def atomic_private(path,value):
    data=canonical(value)+b'\n';need(len(data)<=LIMIT)
    need(not path.exists());plain(path.parent,directory=True)
    with path.open('xb') as f:f.write(data)

def prepare_arm(root,binary,compiler,cc,windres,private):
    p=load_protocol(root);verify_compiler(compiler);full_receipt(root,binary,cc,p)
    need(not private.exists());plain(private.parent,directory=True);private.mkdir()
    with (private/'prepare.log').open('xb') as stream:
        import contextlib
        sink=p.owned.PrivateOutput(stream)
        with contextlib.redirect_stdout(sink),contextlib.redirect_stderr(sink):
            release,profile,receipt,_=p.owned.prepare(compiler,binary,cc,windres,private,edit_profile=True)
    full_receipt(root,binary,cc,p);p.base.verify_manifest(receipt,root,release,profile)
    atomic_private(private/'ready.json',{'schema':1,'build_receipt_sha256':sha(binary/'ru_notepad.build.json'),
        'runner_receipt_sha256':sha(receipt),'cc_sha256':sha(cc)})

def verify_arm(root,binary,cc,private,p):
    ready=read(private/'ready.json');need(set(ready)=={'schema','build_receipt_sha256','runner_receipt_sha256','cc_sha256'})
    need(ready['schema']==1 and ready['build_receipt_sha256']==sha(binary/'ru_notepad.build.json'))
    need(ready['runner_receipt_sha256']==sha(private/'runner-receipt.json') and ready['cc_sha256']==sha(cc))
    build=full_receipt(root,binary,cc,p)
    manifest=p.base.verify_manifest(private/'runner-receipt.json',root,private/'release',private/'profile')
    need(manifest['compiler_commit']==COMPILER)
    need(manifest['runtime_sha256']['release']=={name:build[key] for name,key in zip(p.base.RUNTIME_NAMES,('exe_sha256','dll_sha256','lexilla_dll_sha256','native_helper_sha256'))})
    return ready,manifest

def sync_dlls(baseline,candidate,binary,cc):
    p=load_protocol(candidate);full_receipt(baseline,binary,cc,p)
    # Both archives were independently validated/extracted/built by old scripts.
    # Replace only generated dependency DLLs using this job's sealed baseline.
    for name,relative in (('Scintilla.dll','vendor/scintilla/bin/Scintilla.dll'),('Lexilla.dll','vendor/lexilla/bin/lexilla.dll')):
        source=under(binary,name);target=under(candidate,relative)
        need(target!=source);shutil.copyfile(source,target);need(sha(source)==sha(target))

def blank(p,candidate_sha):
    return {'schema':1,'diagnostic_only':1,'product_acceptance_claimed':0,'baseline_commit':BASELINE,
        'candidate_commit':candidate_sha,'compiler_commit':COMPILER,'policy_sha256':list(POLICIES),'protocol_sha256':ZERO,
        'stage_deadline_seconds':30,'process_deadline_seconds':120,'order':list(ORDER),
        'prepared':[0,0],'build_receipt_sha256':[ZERO,ZERO],'runner_receipt_sha256':[ZERO,ZERO],
        'release_attempted':[0]*8,'release_verified':[0]*8,'release_results':[p.edit.blank_public() for _ in ORDER],
        'profile_attempted':[0,0],'profile_verified':[0,0],'profile_results':[p.edit.blank_public(),p.edit.blank_public()],
        'pair_indices':[list(x) for x in PAIRS],'pair_complete':[0]*4,'pair_ratios':[[0.0]*4 for _ in PAIRS],
        'diagnostic_complete':0,'product_gate_failed':0,'passed':0,'failure_code':1}

def recompute(value):
    releases=[x['runs'][0] for x in value['release_results']]
    for i,(a,b) in enumerate(PAIRS):
        complete=bool(value['release_verified'][a] and value['release_verified'][b] and releases[a]['diagnostic_complete'] and releases[b]['diagnostic_complete'])
        value['pair_complete'][i]=int(complete)
        value['pair_ratios'][i]=[releases[b]['stages'][k]['wall_ms']/releases[a]['stages'][k]['wall_ms'] for k in range(4)] if complete else [0.0]*4
    value['diagnostic_complete']=int(value['failure_code'] in (0,1,2) and all(value['release_verified']) and all(value['profile_verified']) and all(r['diagnostic_complete'] for r in releases) and all(x['diagnostic_complete'] for x in value['profile_results']))
    value['product_gate_failed']=int(any(r['product_gate_failed'] for r in releases) or any(x['product_gate_failed'] for x in value['profile_results']))
    value['passed']=int(value['diagnostic_complete'] and not value['product_gate_failed'] and value['failure_code'] in (0,1))
    if value['passed']:value['failure_code']=0
    elif value['diagnostic_complete']:value['failure_code']=2 if value['product_gate_failed'] else value['failure_code']

def validate(value,p):
    template=blank(p,value.get('candidate_commit',''))
    def walk(a,b,key=''):
        if type(b) is dict:
            need(type(a) is dict and set(a)==set(b))
            for k in b:walk(a[k],b[k],k)
        elif type(b) is list:
            need(type(a) is list and len(a)==len(b))
            if key not in ('release_results','profile_results'):
                for x,y in zip(a,b):walk(x,y,key)
        elif type(b) is str:need(type(a) is str and re.fullmatch('[0-9a-f]{'+str(len(b))+'}',a) is not None)
        elif type(b) is float:need(type(a) in (float,int) and math.isfinite(a) and 0<=a<=1000000)
        else:need(type(a) is int and a>=0)
    walk(value,template)
    for k in ('schema','diagnostic_only','product_acceptance_claimed','baseline_commit','compiler_commit','policy_sha256','stage_deadline_seconds','process_deadline_seconds','order','pair_indices'):
        need(value[k]==template[k])
    need(re.fullmatch('[0-9a-f]{40}',value['candidate_commit']) is not None)
    for key in ('prepared','release_attempted','release_verified','profile_attempted','profile_verified','pair_complete'):need(all(type(x) is int and x in (0,1) for x in value[key]))
    need(value['failure_code'] in range(8))
    for i,x in enumerate(value['release_results']):
        p.edit.validate_public(x)
        need(x['runs'][1]['executed']==0 and x['phase_wall_measured']==0)
        need(not x['runs'][0]['executed'] or value['release_attempted'][i])
        need(not value['release_attempted'][i] or value['prepared'][ORDER[i]])
        need(not x['runs'][0]['executed'] or x['receipt_sha256']==value['runner_receipt_sha256'][ORDER[i]])
        need(not value['release_verified'][i] or (value['release_attempted'][i] and x['runs'][0]['diagnostic_complete']))
    for i,x in enumerate(value['profile_results']):
        p.edit.validate_public(x)
        need(not any(r['executed'] for r in x['runs']) or value['profile_attempted'][i])
        need(not value['profile_attempted'][i] or (value['prepared'][i] and all(value['release_verified'])))
        need(not value['profile_verified'][i] or (value['profile_attempted'][i] and x['diagnostic_complete']))
        need(not any(r['executed'] for r in x['runs']) or x['receipt_sha256']==value['runner_receipt_sha256'][i])
    for key in ('release_attempted','profile_attempted'):
        need(value[key]==sorted(value[key],reverse=True))
    expected=json.loads(canonical(value));recompute(expected)
    for k in ('pair_complete','pair_ratios','diagnostic_complete','product_gate_failed','passed','failure_code'):need(value[k]==expected[k])
    data=canonical(value)+b'\n';need(len(data)<=LIMIT);return data

def save(path,value,p):
    recompute(value);data=validate(value,p);plain(path.parent,directory=True)
    if path.exists():plain(path)
    temporary=path.with_suffix('.pending');need(not temporary.exists())
    with temporary.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    os.replace(temporary,path)

def must_stop(result):
    return (not result.get('diagnostic_complete') or result.get('cleanup_unconfirmed') or result.get('retained_output_unconfirmed') or result.get('drop_cleanup_failed'))

def run_release(root,private,out,p,ci):
    manifest=p.base.verify_manifest(private/'runner-receipt.json',root,private/'release',private/'profile')
    need(not out.exists());out.mkdir();p.base.ensure_local_launcher_directory(out)
    data,styles,folds=p.base.fixture_bytes(ci);source=out/'unclosed-fence.md';p.base.write_new(source,data)
    runtime=out/'release';p.base.copy_runtime(private/'release',runtime,manifest['runtime_sha256']['release'])
    result=p.edit.run_owned('release',runtime,source,ci,styles,folds)
    projected=p.edit.public_projection({'passed':False,'runs':[result],'receipt_sha256':sha(private/'runner-receipt.json')},sha(root/'native/markdown_edit_profile.h'),ci)
    return result,projected

def measure(baseline,candidate,candidate_sha,compiler,cc,output,*,release_runner=run_release):
    p=load_protocol(candidate);value=blank(p,candidate_sha);target=output/'markdown-width-ab.json'
    plain(output,directory=True)
    if target.exists():need(read(target)==value)
    save(target,value,p)
    roots=(baseline,candidate);bins=tuple(r/'build/markdown-edit-experiment/bin' for r in roots)
    private=tuple(r/'build/markdown-width-ab-private' for r in roots)
    def check():
        protocol=verify_roots(baseline,candidate,candidate_sha,compiler)
        need(value['protocol_sha256'] in (ZERO,protocol));value['protocol_sha256']=protocol
        all_ready=[];all_manifests=[]
        for i in range(2):
            ready,manifest=verify_arm(roots[i],bins[i],cc,private[i],p)
            if value['prepared'][i]:
                need(value['build_receipt_sha256'][i]==ready['build_receipt_sha256'] and value['runner_receipt_sha256'][i]==ready['runner_receipt_sha256'])
            value['prepared'][i]=1;value['build_receipt_sha256'][i]=ready['build_receipt_sha256'];value['runner_receipt_sha256'][i]=ready['runner_receipt_sha256']
            all_ready.append(ready);all_manifests.append(manifest)
        need(all(all_manifests[0]['runtime_sha256']['release'][n]==all_manifests[1]['runtime_sha256']['release'][n] for n in p.base.RUNTIME_NAMES[1:]))
    try:
        check();save(target,value,p)
        ci=p.base.load_ci(candidate)
        for index,arm in enumerate(ORDER):
            check();value['release_attempted'][index]=1;save(target,value,p)
            result,public=release_runner(roots[arm],private[arm],private[arm]/('release-'+str(index)),p,ci)
            value['release_results'][index]=public
            if must_stop(result):value['failure_code']=3
            else:
                check();value['release_verified'][index]=1
            save(target,value,p)
            if must_stop(result):return value
        for arm in range(2):
            check();value['profile_attempted'][arm]=1;save(target,value,p)
            partial={'passed':False,'runs':[],'receipt_sha256':sha(private[arm]/'runner-receipt.json')}
            def owned_checked(*args,**kwargs):
                need(not partial['runs'] or not must_stop(partial['runs'][-1]))
                check()
                result=p.edit.run_owned(*args,**kwargs)
                partial['runs'].append(result)
                partial['passed']=len(partial['runs'])==2 and all(r['passed'] for r in partial['runs'])
                value['profile_results'][arm]=p.edit.public_projection(partial,sha(roots[arm]/'native/markdown_edit_profile.h'),ci)
                if must_stop(result):value['failure_code']=3
                save(target,value,p)
                # A post-run receipt failure cannot discard the observed result.
                if not must_stop(result):check()
                return result
            summary=p.edit.run_pair(private[arm]/'runner-receipt.json',roots[arm],private[arm]/'release',private[arm]/'profile',private[arm]/'explanatory-pair',ci=ci,run=owned_checked)
            value['profile_results'][arm]=p.edit.public_projection(summary,sha(roots[arm]/'native/markdown_edit_profile.h'),ci)
            stop=len(summary['runs'])!=2 or any(must_stop(r) for r in summary['runs'])
            if stop:value['failure_code']=3
            else:
                check();value['profile_verified'][arm]=1
            save(target,value,p)
            if stop:return value
        check();save(target,value,p)
    except Exception as error:
        failure_trace(error)
        if value['failure_code']!=3:value['failure_code']=4
        save(target,value,p)
    return value

def host_guard():
    need(sys.platform=='win32' and os.environ.get('GITHUB_REPOSITORY')=='uppet/ru_notepad')
    need(os.environ.get('GITHUB_EVENT_NAME')=='push' and os.environ.get('GITHUB_REF')=='refs/heads/mi-perf-prototype')
    need(re.fullmatch('[0-9a-f]{40}',os.environ.get('GITHUB_SHA','')) is not None)

def main(argv=None):
    class PublicParser(argparse.ArgumentParser):
        def error(self,message):raise ValueError('width_ab_arguments')
    parser=PublicParser()
    parser.add_argument('mode',choices=('verify','prepare','sync-dlls','measure'))
    for name in ('baseline','candidate','compiler','cc'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--arm',type=int,choices=(0,1));parser.add_argument('--windres',type=Path);parser.add_argument('--output',type=Path)
    # argparse messages contain only declared option names, no private GUI data.
    try:
        a=parser.parse_args(argv);host_guard();commit=os.environ['GITHUB_SHA']
        roots=(plain(a.baseline,directory=True),plain(a.candidate,directory=True))
        verify_roots(*roots,commit,a.compiler)
        if a.mode=='verify':
            if a.output is not None:
                need(not a.output.exists());plain(a.output.parent,directory=True);a.output.mkdir()
                p=load_protocol(roots[1]);save(a.output/'markdown-width-ab.json',blank(p,commit),p)
            print('WIDTH_AB_VERIFIED=1');return 0
        if a.mode=='prepare':
            need(a.arm in (0,1) and a.windres is not None)
            root=roots[a.arm];prepare_arm(root,root/'build/markdown-edit-experiment/bin',a.compiler,a.cc,a.windres,root/'build/markdown-width-ab-private')
        elif a.mode=='sync-dlls':sync_dlls(*roots,roots[0]/'build/markdown-edit-experiment/bin',a.cc)
        else:
            need(a.output is not None)
            result=measure(*roots,commit,a.compiler,a.cc,a.output)
            print('WIDTH_AB_DIAGNOSTIC_COMPLETE='+str(result['diagnostic_complete']))
            print('WIDTH_AB_PRODUCT_GATE_FAILED='+str(result['product_gate_failed']))
            print('WIDTH_AB_FAILURE_CODE='+str(result['failure_code']))
            return 0 if result['passed'] else 1
        print('WIDTH_AB_COMMAND_COMPLETE=1');return 0
    except Exception as error:
        failure_trace(error)
        print('WIDTH_AB_COMMAND_FAILED=1');return 1

if __name__=='__main__':raise SystemExit(main())
