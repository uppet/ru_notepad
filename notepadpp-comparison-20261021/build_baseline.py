"""Independent comparison baseline build adapter. No environment spoofing.
Copied receipt checks originate in reviewed width A/B tooling; no imports from
or edits to that experiment. Native build CLI is guarded to comparison branch.
"""
from __future__ import annotations
import argparse, hashlib, importlib, io, json, os, re, subprocess, sys, zipfile, stat
from pathlib import Path
from types import SimpleNamespace
from acquire_npp import safe_members
BASELINE='6aa535d62c28cc9a03f33c3610fe99b3cf1bd14e'
COMPILER='85c7821fda35aa79deeaf67b4d430f24ddd7f07f'
COMPILER_TREE='a770e367e84d87a0d2fcb6d49ea6f06da2dbe4ba'
LIMIT=1024*1024
ARCHIVES=(('scintilla567.zip',1904249,'2309181e59e7da4659f890dbc128db7451ccd094748770e7be674b830494587c','scintilla'),
          ('lexilla554.zip',1598324,'5e0a21356e4e2f19d6a38ecd1c8172d5a2b7b4542940568b023386080db90fe0','lexilla'))
def need(value):
    if not value:raise ValueError('comparison_build_rejected')

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

TOOLS=('gcc.exe','g++.exe','windres.exe','ar.exe','ranlib.exe','mingw32-make.exe')


def tool_file(toolbin, name):
    # Only six explicitly selected build tools may have regular hardlink aliases.
    # Source/runtime/config/receipts retain the single-link plain() policy.
    need(name in TOOLS)
    toolbin=plain(toolbin,directory=True)
    path=toolbin/name
    for parent in (path,*path.parents):
        need(not parent.is_symlink())
        if parent.exists():need(not (getattr(parent.lstat(),'st_file_attributes',0)&0x400))
    need(stat.S_ISREG(path.lstat().st_mode) and path.stat().st_nlink>=1)
    return path.resolve(strict=True)


def compiler_file(path):
    path=Path(os.path.abspath(path))
    need(path.name=='gcc.exe')
    return tool_file(path.parent,'gcc.exe')


def tool_snapshot(toolbin):
    result={}
    for name in TOOLS:
        path=tool_file(toolbin,name);before=sha(path)
        version=subprocess.run([str(path),'--version'],capture_output=True,timeout=30)
        need(version.returncode==0 and sha(tool_file(toolbin,name))==before)
        result[name]={'path':str(path),'sha256':before,
                      'version_stdout_sha256':hashlib.sha256(version.stdout).hexdigest()}
    return result


def verify_tools(toolbin, expected):
    need(set(expected)==set(TOOLS))
    need(tool_snapshot(toolbin)==expected)


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

NONRUNTIME_NAMES=('RuSyntaxWrongAbi.dll','RuSyntaxWrongAbi.native-build.json')


def nonruntime_build(root,binary,p):
    # These two pinned negative-test build outputs are never GUI runtime inputs.
    expected=dict(read(under(binary,'RuSyntax.native-build.json'))['build_inputs'])
    expected.update(output_name=NONRUNTIME_NAMES[0],compile_sources=['native/ru_wrong_abi.c'])
    need(tuple(p.package.NATIVE_COMPILE_SOURCES[NONRUNTIME_NAMES[0]])==('native/ru_wrong_abi.c',))
    hashes={}
    for name in NONRUNTIME_NAMES:
        copied=under(binary,name);original=under(root,'build/native-helper/'+name)
        need(sha(copied)==sha(original))
        hashes[name]=sha(copied)
    negative=read(under(binary,NONRUNTIME_NAMES[1]))
    command=[expected['compiler_path'],*expected['compiler_flags'],*expected['compile_sources'],
             '-o',str(root/'build/native-helper/RuSyntaxWrongAbi.pending.dll'),
             *('-l'+name for name in expected['link_libraries'])]
    need(negative=={'schema':1,'name':NONRUNTIME_NAMES[0],'build_inputs':expected,
                    'build_key':p.package.native_build_key(expected),'dll_sha256':hashes[NONRUNTIME_NAMES[0]],
                    'compiler_command':command})
    return hashes


def full_receipt(root,binary,cc,p):
    root=plain(root,directory=True);binary=plain(binary,directory=True);cc=compiler_file(cc)
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
        need((compiler_file(cmd[index])==cc) if index==0 else (plain(cmd[index])==plain(expected)))
    helper=read(binary/'RuSyntax.native-build.json');n=helper['build_inputs']
    need(helper['schema']==1 and helper['name']=='RuSyntax.dll' and n['output_name']=='RuSyntax.dll')
    need(n['source_sha256']==p.package.native_source_snapshot(root))
    need(n['driver_sha256']=={rel:sha(under(root,rel)) for rel in p.package.NATIVE_BUILD_DRIVERS})
    need(n['compile_sources']==list(p.package.NATIVE_COMPILE_SOURCES['RuSyntax.dll']))
    need(n['compiler_flags']==list(p.package.NATIVE_CFLAGS) and n['link_libraries']==list(p.package.NATIVE_LINK_LIBRARIES))
    need(compiler_file(n['compiler_path'])==cc and n['compiler_sha256']==sha(cc))
    version=subprocess.run([str(cc),'--version'],capture_output=True,timeout=30);need(version.returncode==0)
    need(hashlib.sha256(version.stdout).hexdigest()==n['compiler_version_sha256'])
    need(helper['build_key']==p.package.native_build_key(n)==receipt['native_helper_build_key'])
    need(helper['dll_sha256']==receipt['native_helper_sha256'])
    return receipt


def host_guard(env=None, platform=None):
    env=os.environ if env is None else env
    need((os.name if platform is None else platform)=='nt')
    need(env.get('GITHUB_REPOSITORY')=='uppet/ru_notepad')
    need(env.get('GITHUB_REF')=='refs/heads/notepadpp-comparison')
    need(env.get('GITHUB_EVENT_NAME')=='push')
    need(re.fullmatch('[0-9a-f]{40}',env.get('GITHUB_SHA','')) is not None)


def command(argv, root, logs, index, timeout=1800):
    # Build output can contain local paths. Never publish these private logs.
    with (logs/f'{index}.private.log').open('xb') as out:
        completed=subprocess.run([str(x) for x in argv],cwd=root,stdout=out,
                                 stderr=subprocess.STDOUT,timeout=timeout)
    need(completed.returncode==0)


def extract_dependency(archive, vendor, size, expected, folder):
    archive=plain(archive);need(archive.stat().st_size==size and sha(archive)==expected)
    need(not (vendor/folder).exists())
    with zipfile.ZipFile(archive) as z:
        entries=safe_members(z)
        need(all(e.filename.split('/')[0]==folder for e in entries))
        # Exact official archive bytes + path/member checks, no foreign target.
        for entry in entries:
            target=vendor.joinpath(*entry.filename.rstrip('/').split('/'))
            if entry.is_dir():target.mkdir(parents=True,exist_ok=True)
            else:
                target.parent.mkdir(parents=True,exist_ok=True)
                with target.open('xb') as stream:stream.write(z.read(entry))


def build(root,compiler,toolbin,out,logs):
    root=plain(root,directory=True);compiler=plain(compiler,directory=True);toolbin=plain(toolbin,directory=True)
    need(root!=compiler and not root.is_relative_to(compiler) and not compiler.is_relative_to(root))
    snapshot=checkout(root,BASELINE);verify_compiler(compiler)
    cc=compiler_file(toolbin/'gcc.exe')
    for name in TOOLS:tool_file(toolbin,name)
    plain(out.parent,directory=True);plain(logs.parent,directory=True)
    need(not out.exists() and not logs.exists());out.mkdir();logs.mkdir()
    tools=tool_snapshot(toolbin)
    before_path=os.environ.get('PATH','')
    os.environ['PATH']=str(toolbin)+os.pathsep+before_path
    try:
        commands=[
            [sys.executable,'tools/test_source_archives.py'],
            [sys.executable,'tools/prepare_source_archives.py','--root',root,'--receipt',logs/'source-archives.json'],
        ]
        for i,cmd in enumerate(commands):command(cmd,root,logs,i)
        for filename,size,h,folder in ARCHIVES:
            extract_dependency(root/'vendor/downloads'/filename,root/'vendor',size,h,folder)
        commands=[
            [toolbin/'mingw32-make.exe','-j2','-C',root/'vendor/scintilla/win32','../bin/Scintilla.dll','CXX=g++.exe','WINDRES=windres.exe','AR=ar.exe','RANLIB=ranlib.exe'],
            [toolbin/'mingw32-make.exe','-j2','-C',root/'vendor/lexilla/src','../bin/lexilla.dll','CXX=g++.exe','WINDRES=windres.exe','AR=ar.exe','RANLIB=ranlib.exe','LDFLAGS=-shared -static -mwindows -Wl,--kill-at -s','windir=C:/Windows'],
            [sys.executable,'tools/check_static.py','--ru-root',compiler],
            [sys.executable,'tools/build.py','--ru-root',compiler,'--cc',cc,'--cxx',toolbin/'g++.exe','--windres',toolbin/'windres.exe','--ar',toolbin/'ar.exe','--ranlib',toolbin/'ranlib.exe','--skip-scintilla','--skip-lexilla','--source','src/main.ru','--output',out/'ru_notepad.exe'],
        ]
        for i,cmd in enumerate(commands,2):command(cmd,root,logs,i)
        need(checkout(root,BASELINE)==snapshot);verify_compiler(compiler)
        verify_tools(toolbin,tools)
        protocol=load_protocol(root)
        receipt=full_receipt(root,out,cc,protocol)
        for field,value in [('scintilla_archive_sha256',ARCHIVES[0][2]),('lexilla_archive_sha256',ARCHIVES[1][2]),('scintilla_version','5.6.7'),('lexilla_version','5.5.4')]:need(receipt[field]==value)
        # Generated dependencies must be byte-identical to the app's copied DLLs.
        for name,src in [('Scintilla.dll','vendor/scintilla/bin/Scintilla.dll'),('Lexilla.dll','vendor/lexilla/bin/lexilla.dll')]:need(sha(under(out,name))==sha(under(root,src)))
        record={'schema':1,'baseline_commit':BASELINE,'compiler_commit':COMPILER,'compiler_tree':COMPILER_TREE,
                'nonruntime_build_sha256':nonruntime_build(root,out,protocol),
                'tracked_source_sha256':snapshot,'build_receipt_sha256':sha(out/'ru_notepad.build.json'),
                'native_receipt_sha256':sha(out/'RuSyntax.native-build.json'),
                'tools':tools,'dependency_build_commands':[[str(x) for x in cmd] for cmd in commands[:2]],
                'compiler_sha256':sha(cc),'compiler_version_sha256':read(out/'RuSyntax.native-build.json')['build_inputs']['compiler_version_sha256'],
                'generated_c_sha256':receipt['generated_c_sha256'],'translation_unit_sha256':receipt['translation_unit_sha256'],
                'build_input_sha256':receipt['build_input_sha256'],
                'source_archives_receipt_sha256':sha(logs/'source-archives.json'),
                'runtime':{'ru':{name:sha(under(out,name)) for name in protocol.base.RUNTIME_NAMES}}}
        with (out/'comparison-build.json').open('x') as stream:json.dump(record,stream,sort_keys=True)
        return record
    finally:os.environ['PATH']=before_path


def main():
    ap=argparse.ArgumentParser()
    for name in ('baseline','compiler','toolbin','output','private-logs'):
        ap.add_argument('--'+name,type=Path,required=True)
    a=ap.parse_args();host_guard()
    build(a.baseline,a.compiler,a.toolbin,a.output.absolute(),a.private_logs.absolute())

if __name__ == '__main__':
    try:
        result = main()
    except Exception:
        import sys
        print('COMPARISON_FAILURE_CODE=2', file=sys.stderr)
        raise SystemExit(1)
    raise SystemExit(result or 0)
