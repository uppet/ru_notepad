#!/usr/bin/env python3
"""Same-source, same-new-compiler, release-only owned Windows dense A/B study.

This does not use the old width source/compiler pins or profile preparation.
Formal 30s/120s gates and existing owned GUI proofs/cleanup remain unchanged.
"""
from __future__ import annotations
import argparse,difflib,hashlib,importlib,json,math,os,re,shutil,subprocess,sys,tempfile
from pathlib import Path
from types import SimpleNamespace

ORDER=(0,1,1,0,0,1,1,0)
PAIRS=((0,1),(3,2),(4,5),(7,6))
BINARY='build/markdown-dense-experiment/bin'
ORIGIN='build/markdown-dense-native-origin.json'
ZERO='0'*64
LIMIT=256*1024

def need(x):
    if not x:raise ValueError('dense_ab_rejected')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(v):return hashlib.sha256(canonical(v)).hexdigest()
def plain(path,*,directory=False,compiler=False):
    p=Path(os.path.abspath(path))
    for q in (p,*p.parents):
        need(not q.is_symlink())
        if q.exists():need(not (getattr(q.lstat(),'st_file_attributes',0)&0x400))
    need(p.is_dir() if directory else p.is_file())
    if not directory:need(p.stat().st_nlink>=1 if compiler else p.stat().st_nlink==1)
    return p.resolve(strict=True)
def under(root,rel):
    need(type(rel) is str and rel and not Path(rel).is_absolute())
    p=plain(root/rel);need(p.is_relative_to(root));return p
def read(path):
    p=plain(path);need(p.stat().st_size<=LIMIT)
    def pairs(items):
        d={}
        for k,v in items:need(k not in d);d[k]=v
        return d
    return json.loads(p.read_bytes(),object_pairs_hook=pairs,parse_constant=lambda _:need(False))
def git(root,*args):
    r=subprocess.run(['git','-C',str(root),*args],capture_output=True,timeout=30)
    need(r.returncode==0);return r.stdout.decode('utf-8','strict')
def checkout(root,commit):
    plain(root,directory=True);need(re.fullmatch('[0-9a-f]{40}',commit) is not None)
    need(git(root,'rev-parse','HEAD').strip()==commit and not git(root,'status','--porcelain'))
    paths=git(root,'ls-files','-z').split('\0');need(paths[-1]=='');paths.pop()
    need(0<len(paths)<2000 and len(paths)==len(set(paths)))
    return {n:sha(under(root,n)) for n in paths}
def job(commit):
    run=os.environ.get('GITHUB_RUN_ID','');attempt=os.environ.get('GITHUB_RUN_ATTEMPT','')
    need(re.fullmatch('[1-9][0-9]{0,19}',run) is not None and re.fullmatch('[1-9][0-9]{0,7}',attempt) is not None)
    need(os.environ.get('GITHUB_SHA')==commit)
    return {'run_id':run,'run_attempt':attempt,'source_commit':commit}
def protocol(root):
    names={'package':'package','base':'run_markdown_phase_profile','edit':'run_markdown_edit_profile','dense':'markdown_dense_build'}
    sys.path.insert(0,str(root/'tools'));p=SimpleNamespace()
    for key,name in names.items():
        module=importlib.import_module(name);need(Path(module.__file__).resolve().parent==root/'tools');setattr(p,key,module)
    return p

def verify_sources(roots,compiler,commit,compiler_commit,compiler_tree):
    a,b=roots;need(a!=b and not a.is_relative_to(b) and not b.is_relative_to(a))
    need(not compiler.is_relative_to(a) and not compiler.is_relative_to(b))
    left=checkout(a,commit);need(left==checkout(b,commit));checkout(compiler,compiler_commit)
    need(re.fullmatch('[0-9a-f]{40}',compiler_tree) is not None and git(compiler,'rev-parse','HEAD^{tree}').strip()==compiler_tree)
    return {'job':job(commit),'source_sha256':digest(left),'compiler_commit':compiler_commit,'compiler_tree':compiler_tree}

def source_snapshot(root,p):
    result={x.relative_to(root).as_posix():sha(plain(x)) for folder in ('src','tests') for x in sorted((root/folder).glob('*.ru'))}
    result.update({x.relative_to(root).as_posix():sha(plain(x)) for x in sorted((root/'locales').glob('*.json'))})
    result['tools/generate_i18n.py']=sha(under(root,'tools/generate_i18n.py'))
    native=p.package.native_source_snapshot(root)
    for rel,want in native.items():need(sha(under(root,rel))==want)
    result.update(native);return result

def native_inputs(root,cc,p):
    cc=plain(cc,compiler=True);version=subprocess.run([str(cc),'--version'],capture_output=True,timeout=30);need(version.returncode==0)
    sources=p.package.native_source_snapshot(root)
    for rel,want in sources.items():need(sha(under(root,rel))==want)
    return {'output_name':'RuSyntax.dll','compile_sources':list(p.package.NATIVE_COMPILE_SOURCES['RuSyntax.dll']),
        'source_sha256':sources,'driver_sha256':{rel:sha(under(root,rel)) for rel in p.package.NATIVE_BUILD_DRIVERS},
        'compiler_path':str(cc),'compiler_sha256':sha(cc),'compiler_version_sha256':hashlib.sha256(version.stdout).hexdigest(),
        'compiler_flags':list(p.package.NATIVE_CFLAGS),'link_libraries':list(p.package.NATIVE_LINK_LIBRARIES)}

def full_receipt(root,arm,cc,p,compiler_commit,compiler_tree):
    binary=plain(root/BINARY,directory=True);cc=plain(cc,compiler=True);r=read(binary/'ru_notepad.build.json')
    need(r['schema']==1 and r['ru_commit']==compiler_commit and r['ru_tree']==compiler_tree)
    need(r['entry_source']=='src/main.ru' and r['entry_sha256']==sha(under(root,'src/main.ru')))
    need(r['source_sha256']==source_snapshot(root,p))
    inputs=tuple(p.package.RESOURCE_INPUTS)+('packaging/diagnostic_launcher.c',p.dense.MANIFEST,p.dense.DRIVER)
    need(r['build_input_sha256']=={rel:sha(under(root,rel)) for rel in inputs})
    p.dense.verify_receipt(root,root/p.dense.MANIFEST,arm,r['experimental_markdown_dense'])
    for field,rel in [('generated_c','build/main.c'),('translation_unit','build/main-gui.c')]:
        f=under(root,rel);need(r[field+'_sha256']==sha(f) and r[field+'_bytes']==f.stat().st_size)
    for name,key in zip(p.base.RUNTIME_NAMES,('exe_sha256','dll_sha256','lexilla_dll_sha256','native_helper_sha256')):need(sha(under(binary,name))==r[key])
    need(r['exe_bytes']==(binary/'ru_notepad.exe').stat().st_size)
    cmd=r['compiler_command'];need(type(cmd) is list and len(cmd)==15)
    need(cmd[1:7]==['-std=c99','-O2','-Wall','-Wextra','-Wno-unused-function','-static-libgcc'])
    need(cmd[8]=='-o' and cmd[10]=='-lm' and cmd[12:]==['-mwindows','-lshell32','-luser32'])
    for i,want in ((0,cc),(7,root/'build/main-gui.c'),(9,binary/'ru_notepad.exe'),(11,root/'build/app-resource.o')):
        need(plain(cmd[i],compiler=i==0)==plain(want,compiler=i==0))
    h=read(binary/'RuSyntax.native-build.json');n=h['build_inputs']
    need(h['schema']==1 and h['name']=='RuSyntax.dll' and n==native_inputs(root,cc,p))
    need(h['build_key']==p.package.native_build_key(n)==r['native_helper_build_key'])
    need(h['dll_sha256']==r['native_helper_sha256'])
    return r

def write_new(path,value):
    data=canonical(value)+b'\n';need(len(data)<=LIMIT);plain(path.parent,directory=True);need(not path.exists())
    with path.open('xb') as f:f.write(data)

def sync_dlls(roots,cc,p,compiler_commit,compiler_tree,identity):
    a,b=roots;binary=a/BINARY;full_receipt(a,'ordinary',cc,p,compiler_commit,compiler_tree)
    hpath=under(binary,'RuSyntax.native-build.json');h=read(hpath)
    need(h['build_inputs']==native_inputs(a,cc,p)==native_inputs(b,cc,p))
    cache=b/'build/native-helper';origin=b/ORIGIN;need(not cache.exists() and not origin.exists());plain(cache.parent,directory=True)
    value={'schema':1,'identity':identity,'ordinary_build_receipt_sha256':sha(binary/'ru_notepad.build.json'),
        'helper_receipt_sha256':sha(hpath),'native_build_key':h['build_key'],
        'dll_sha256':{n:sha(under(binary,n)) for n in p.base.RUNTIME_NAMES[1:]}}
    for name,rel in [('Scintilla.dll','vendor/scintilla/bin/Scintilla.dll'),('Lexilla.dll','vendor/lexilla/bin/lexilla.dll')]:
        target=under(b,rel);source=under(binary,name);need(source!=target);shutil.copyfile(source,target);need(sha(source)==sha(target))
    cache.mkdir()
    for name in ('RuSyntax.dll','RuSyntax.native-build.json'):
        source=under(binary,name);target=cache/name
        with target.open('xb') as f:f.write(source.read_bytes())
        need(sha(source)==sha(plain(target)))
    write_new(origin,value)

def verify_pair(roots,compiler,commit,compiler_commit,compiler_tree,cc,p):
    identity=verify_sources(roots,compiler,commit,compiler_commit,compiler_tree)
    receipts=[full_receipt(r,arm,cc,p,compiler_commit,compiler_tree) for r,arm in zip(roots,('ordinary','dense'))]
    need(receipts[0]['source_sha256']==receipts[1]['source_sha256'] and receipts[0]['build_input_sha256']==receipts[1]['build_input_sha256'])
    origin=read(roots[1]/ORIGIN);h=read(roots[0]/BINARY/'RuSyntax.native-build.json')
    expected={'schema':1,'identity':identity,'ordinary_build_receipt_sha256':sha(roots[0]/BINARY/'ru_notepad.build.json'),
        'helper_receipt_sha256':sha(roots[0]/BINARY/'RuSyntax.native-build.json'),'native_build_key':h['build_key'],
        'dll_sha256':{n:sha(roots[0]/BINARY/n) for n in p.base.RUNTIME_NAMES[1:]}}
    need(origin==expected)
    for folder in (roots[1]/'build/native-helper',roots[1]/BINARY):
        need(sha(under(folder,'RuSyntax.native-build.json'))==origin['helper_receipt_sha256'])
        need(sha(under(folder,'RuSyntax.dll'))==origin['dll_sha256']['RuSyntax.dll'])
    need(origin['dll_sha256']=={n:sha(roots[1]/BINARY/n) for n in p.base.RUNTIME_NAMES[1:]})
    return {'identity':identity,'build_receipt_sha256':[sha(r/BINARY/'ru_notepad.build.json') for r in roots],
        'activation_receipt_sha256':[digest(r['experimental_markdown_dense']) for r in receipts],
        'manifest_sha256':sha(roots[0]/p.dense.MANIFEST),'native_origin_sha256':sha(roots[1]/ORIGIN),
        'runtime_sha256':[{n:sha(root/BINARY/n) for n in p.base.RUNTIME_NAMES} for root in roots],
        'compiler_binary_sha256':sha(cc),'fixture_sha256':p.base.FIXTURE_SHA256,'fixture_bytes':p.base.FIXTURE_SIZE}

def diagnostic_paths(code,root):
    # Normalize only exact ru_source assignments for sibling checkout paths.
    # Production C and every other source string remain untouched.
    def cstr(v):return '"'+''.join(chr(x) if 32<=x<=126 and x not in (34,92) else f'\\{x:03o}' for x in v.encode())+'"'
    counts={}
    for source in sorted((root/'src').glob('*.ru')):
        rel=source.relative_to(root).as_posix()
        for spelling in set((str(source.resolve()),source.resolve().as_posix())):
            old='ru_source = '+cstr(spelling)+';';count=code.count(old)
            if count:
                counts[rel]=counts.get(rel,0)+count
                code=code.replace(old,'ru_source = '+cstr('<notepad>/'+rel)+';')
    need(bool(counts));return code,counts

def check_generated_pair(roots):
    texts=[diagnostic_paths(under(r,'build/main.c').read_text(encoding='utf-8'),r) for r in roots]
    need(texts[0][1]==texts[1][1]);a,b=[x[0] for x in texts]
    changes=[x for x in difflib.ndiff(a.splitlines(),b.splitlines()) if x.startswith(('- ','+ '))]
    need(len(changes)==2 and 'v_fact(0)' in changes[0] and changes[0][2:].replace('v_fact(0)','v_fact(1)')==changes[1][2:])

def must_stop(result):
    return (not result.get('diagnostic_complete') or result.get('cleanup_unconfirmed') or result.get('retained_output_unconfirmed') or result.get('drop_cleanup_failed'))

def run_release(root,expected,out,p,ci):
    need(not out.exists());out.mkdir();p.base.ensure_local_launcher_directory(out)
    data,styles,folds=p.base.fixture_bytes(ci);source=out/'unclosed-fence.md';p.base.write_new(source,data)
    runtime=out/'release';p.base.copy_runtime(root/BINARY,runtime,expected)
    result=p.edit.run_owned('release',runtime,source,ci,styles,folds)
    projected=p.edit.public_projection({'passed':False,'runs':[result],'receipt_sha256':sha(root/BINARY/'ru_notepad.build.json')},sha(root/'native/markdown_edit_profile.h'),ci)
    return result,projected

def recompute(value):
    value['pair_complete']=[int(value['verified'][a] and value['verified'][b] and value['results'][a]['runs'][0]['passed'] and value['results'][b]['runs'][0]['passed']) for a,b in PAIRS]
    value['pair_ratios']=[[value['results'][b]['runs'][0]['stages'][i]['wall_ms']/value['results'][a]['runs'][0]['stages'][i]['wall_ms'] if value['pair_complete'][n] else 0 for i in range(4)] for n,(a,b) in enumerate(PAIRS)]
    value['windows_executed']=int(any(v['runs'][0]['executed'] for v in value['results']))
    value['diagnostic_complete']=int(all(value['verified']))
    value['product_gate_failed']=int(any(v['runs'][0]['product_gate_failed'] for v in value['results']))
    value['passed']=int(bool(value['diagnostic_complete']) and all(v['runs'][0]['passed'] for v in value['results']))
    value['failure_code']=0 if value['passed'] else (1 if value['diagnostic_complete'] else 2)

def validate_seal(seal,p):
    need(type(seal) is dict and set(seal)=={'identity','build_receipt_sha256','activation_receipt_sha256','manifest_sha256','native_origin_sha256','runtime_sha256','compiler_binary_sha256','fixture_sha256','fixture_bytes'})
    need(seal['fixture_sha256']==p.base.FIXTURE_SHA256 and type(seal['fixture_bytes']) is int and seal['fixture_bytes']==p.base.FIXTURE_SIZE)
    identity=seal['identity'];need(type(identity) is dict and set(identity)=={'job','source_sha256','compiler_commit','compiler_tree'})
    j=identity['job'];need(type(j) is dict and set(j)=={'run_id','run_attempt','source_commit'})
    for key,maximum in [('run_id',19),('run_attempt',7)]:need(type(j[key]) is str and re.fullmatch('[1-9][0-9]{0,'+str(maximum)+'}',j[key]) is not None)
    for v in (j['source_commit'],identity['compiler_commit'],identity['compiler_tree']):need(type(v) is str and re.fullmatch('[0-9a-f]{40}',v) is not None)
    hashes=[identity['source_sha256'],seal['manifest_sha256'],seal['native_origin_sha256'],seal['compiler_binary_sha256']]
    for key in ('build_receipt_sha256','activation_receipt_sha256'):
        need(type(seal[key]) is list and len(seal[key])==2);hashes.extend(seal[key])
    need(type(seal['runtime_sha256']) is list and len(seal['runtime_sha256'])==2)
    for runtime in seal['runtime_sha256']:
        need(type(runtime) is dict and set(runtime)==set(p.base.RUNTIME_NAMES));hashes.extend(runtime.values())
    for v in hashes:need(type(v) is str and re.fullmatch('[0-9a-f]{64}',v) is not None and v!=ZERO)
    need(all(seal['runtime_sha256'][0][n]==seal['runtime_sha256'][1][n] for n in p.base.RUNTIME_NAMES[1:]))

def validate_public(value,p):
    need(set(value)=={'schema','diagnostic_only','product_acceptance_claimed','windows_executed','stage_deadline_seconds','process_deadline_seconds','seal','order','attempted','verified','results','pair_complete','pair_ratios','diagnostic_complete','product_gate_failed','passed','failure_code'})
    for key,want in [('schema',1),('diagnostic_only',1),('product_acceptance_claimed',0),('stage_deadline_seconds',30),('process_deadline_seconds',120)]:need(type(value[key]) is int and value[key]==want)
    validate_seal(value['seal'],p)
    need(value['stage_deadline_seconds']==30 and value['process_deadline_seconds']==120 and value['order']==list(ORDER))
    for key in ('attempted','verified'):
        need(type(value[key]) is list and len(value[key])==8 and all(type(x) is int and x in (0,1) for x in value[key]))
    need(value['attempted']==sorted(value['attempted'],reverse=True) and len(value['results'])==8)
    need(all(not value['attempted'][i] or value['verified'][i-1] for i in range(1,8)))
    need(type(value['pair_complete']) is list and len(value['pair_complete'])==4 and all(type(x) is int and x in (0,1) for x in value['pair_complete']))
    need(type(value['pair_ratios']) is list and len(value['pair_ratios'])==4)
    for row in value['pair_ratios']:
        need(type(row) is list and len(row)==4)
        need(all(type(x) in (int,float) and math.isfinite(x) and x>=0 for x in row))
    for i,v in enumerate(value['results']):
        p.edit.validate_public(v);run=v['runs'][0]
        need(not v['runs'][1]['executed'] and (not run['executed'] or value['attempted'][i]))
        need(not value['verified'][i] or (value['attempted'][i] and run['diagnostic_complete']))
        need(not run['executed'] or v['receipt_sha256']==value['seal']['build_receipt_sha256'][ORDER[i]])
        if value['verified'][i]:need(all(st['wall_ms']>0 for st in run['stages']))
    expected=json.loads(canonical(value));recompute(expected)
    for key in ('windows_executed','pair_complete','pair_ratios','diagnostic_complete','product_gate_failed','passed','failure_code'):need(value[key]==expected[key])
    for key in ('windows_executed','diagnostic_complete','product_gate_failed','passed','failure_code'):need(type(value[key]) is int)
    data=canonical(value)+b'\n';need(len(data)<=LIMIT);return data

def save(path,value,p):
    recompute(value);data=validate_public(value,p);plain(path.parent,directory=True)
    if path.exists():plain(path)
    temp=path.with_suffix('.pending');need(not temp.exists())
    with temp.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    os.replace(temp,path)

def measure(roots,seal,output,p,check,*,runner=run_release,ci=None):
    need(not output.exists());plain(output.parent,directory=True);output.mkdir()
    value={'schema':1,'diagnostic_only':1,'product_acceptance_claimed':0,'windows_executed':0,'stage_deadline_seconds':30,'process_deadline_seconds':120,
        'seal':seal,'order':list(ORDER),'attempted':[0]*8,'verified':[0]*8,'results':[p.edit.blank_public() for _ in ORDER]}
    target=output/'markdown-dense-ab.json';save(target,value,p);ci=ci or p.base.load_ci(roots[1])
    # Private logs/fixture/runtime are never among the publishable report paths.
    private=plain(Path(tempfile.mkdtemp(prefix='markdown-dense-owned-',dir=output.parent)),directory=True)
    cleanup_complete=False
    try:
        p.base.ensure_local_launcher_directory(private)
        for index,arm in enumerate(ORDER):
            need(check()==seal);value['attempted'][index]=1;save(target,value,p)
            raw,projected=runner(roots[arm],seal['runtime_sha256'][arm],private/('run-'+str(index)),p,ci)
            value['results'][index]=projected;save(target,value,p)
            need(check()==seal)
            if must_stop(raw):break
            value['verified'][index]=1;save(target,value,p)
        cleanup_complete=all(value['verified'])
    finally:
        # Never recursively remove an unconfirmed process/log/drop scene. It is
        # private build evidence, excluded from public artifact uploads.
        if cleanup_complete:shutil.rmtree(private)
    save(target,value,p);return value

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('mode',choices=('verify','sync-dlls','check-built','measure'))
    for n in ('ordinary','dense','compiler','cc'):a.add_argument('--'+n,type=Path,required=True)
    for n in ('notepad-commit','compiler-commit','compiler-tree'):a.add_argument('--'+n,required=True)
    a.add_argument('--output',type=Path);v=a.parse_args()
    try:
        roots=tuple(plain(x,directory=True) for x in (v.ordinary,v.dense));compiler=plain(v.compiler,directory=True);cc=plain(v.cc,compiler=True)
        identity=verify_sources(roots,compiler,v.notepad_commit,v.compiler_commit,v.compiler_tree);p=protocol(roots[1])
        if v.mode=='sync-dlls':sync_dlls(roots,cc,p,v.compiler_commit,v.compiler_tree,identity)
        elif v.mode!='verify':
            check=lambda:verify_pair(roots,compiler,v.notepad_commit,v.compiler_commit,v.compiler_tree,cc,p)
            seal=check();check_generated_pair(roots);need(check()==seal)
            if v.mode=='measure':
                need(os.name=='nt' and v.output is not None);result=measure(roots,seal,Path(os.path.abspath(v.output)),p,check)
                print('DENSE_AB_DIAGNOSTIC_COMPLETE='+str(result['diagnostic_complete']))
                print('DENSE_AB_PRODUCT_GATE_FAILED='+str(result['product_gate_failed']))
                return 0 if result['passed'] else 1
        print('DENSE_AB_COMMAND_COMPLETE=1');return 0
    except Exception as e:
        # No arbitrary exception/path/source strings leave the private log.
        print('DENSE_AB_COMMAND_FAILED=1');print('DENSE_AB_EXCEPTION_KIND='+str({ValueError:1,OSError:2,TimeoutError:3,subprocess.TimeoutExpired:4,KeyError:5,TypeError:6}.get(type(e),7)))
        return 1
if __name__=='__main__':raise SystemExit(main())
