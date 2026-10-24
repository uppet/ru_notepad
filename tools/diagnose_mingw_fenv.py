"""Windows-only diagnostic. Does not modify installed tools or product sources."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

SOURCE = r'''#include <fenv.h>
extern "C" __declspec(dllexport) int probe() {
    fenv_t saved;
    if (fesetround(FE_UPWARD)) return 10;
    if (fegetenv(&saved)) return 11;
    if (fesetround(FE_DOWNWARD)) return 12;
    if (fegetround() != FE_DOWNWARD) return 17;
    if (fesetenv(FE_DFL_ENV)) return 13;
    int result = fegetround() == FE_TONEAREST ? 0 : 14;
    if (fesetenv(&saved)) return 15;
    if (fegetround() != FE_UPWARD) return 16;
    return result;
}
int main() { return probe(); }
'''


# No main and no FE_DFL_ENV token: only a saved environment crosses fesetenv.
SAVED_SOURCE = r'''#include <fenv.h>
extern "C" __declspec(dllexport) int probe() {
    fenv_t saved;
    if (fesetround(FE_UPWARD)) return 10;
    if (fegetenv(&saved)) return 11;
    if (fesetround(FE_DOWNWARD)) return 12;
    if (fegetround() != FE_DOWNWARD) return 17;
    if (fesetenv(&saved)) return 15;
    if (fegetround() != FE_UPWARD) return 16;
    return 0;
}
'''


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--mingw-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if os.name!='nt':raise SystemExit('Windows diagnostic only')
    root=args.mingw_root.resolve(strict=True);out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    tools={k:root/'bin'/v for k,v in {'gxx':'g++.exe','nm':'nm.exe','objdump':'objdump.exe'}.items()}
    for path in tools.values():
        if not path.is_file():raise SystemExit('Missing diagnostic tool: '+str(path))
    report={'diagnostic_only':True,'product_acceptance':False,'source_sha256':hashlib.sha256(SOURCE.encode()).hexdigest(),
            'script_sha256':sha(__file__),'tools':{k:{'path':str(v),'sha256':sha(v)} for k,v in tools.items()},'attempts':[]}
    env=os.environ.copy();env['PATH']=str(root/'bin')+os.pathsep+env.get('PATH','')
    for key in ('LIBRARY_PATH','GCC_EXEC_PREFIX','COMPILER_PATH','CPATH','CPLUS_INCLUDE_PATH','C_INCLUDE_PATH'):
        env.pop(key,None)
    def save(): (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    def run(name,argv):
        attempt={'name':name,'command':list(map(str,argv)),'returncode':None,'timeout':False}
        report['attempts'].append(attempt);save()
        stdout=stderr=b''
        try:
            r=subprocess.run(attempt['command'],cwd=out,env=env,capture_output=True,timeout=60)
            stdout,stderr=r.stdout,r.stderr;attempt['returncode']=r.returncode;attempt['returncode_hex']='0x%08X'%(r.returncode & 0xffffffff)
        except subprocess.TimeoutExpired as e:
            stdout,stderr=e.stdout or b'',e.stderr or b'';attempt['timeout']=True
        except OSError as e:attempt['error']=repr(e)
        finally:
            for label,data in [('stdout',stdout),('stderr',stderr)]:
                file=out/(name+'.'+label+'.log');file.write_bytes(data);attempt[label]={'path':file.name,'sha256':sha(file)}
            save()
        return attempt,stdout
    for expected in (0,7):
        control,_=run('recorder-control-'+str(expected),[sys.executable,'-I','-c','import sys; sys.exit('+str(expected)+')'])
        if control['returncode']!=expected:
            report['recorder_controls_passed']=False;save();raise SystemExit('Diagnostic return-code recorder control failed')
    report['recorder_controls_passed']=True;save()
    run('compiler-version',[tools['gxx'],'--version'])
    run('compiler-specs',[tools['gxx'],'-dumpspecs'])
    run('compiler-search-dirs',[tools['gxx'],'-print-search-dirs'])
    pacman=root.parent/'usr/bin/pacman.exe'
    package_result,package_data=run('installed-packages',[pacman,'-Q'])
    expected_packages={'mingw-w64-x86_64-gcc':'16.2.0-6',
        'mingw-w64-x86_64-crt':'14.0.0.r532.gdbbc8e99d-1',
        'mingw-w64-x86_64-headers':'14.0.0.r532.gdbbc8e99d-1',
        'mingw-w64-x86_64-winpthreads':'14.0.0.r532.gdbbc8e99d-1'}
    packages=dict(line.split(None,1) for line in package_data.decode('utf-8',errors='replace').splitlines() if len(line.split(None,1))==2)
    report['failed_job_comparison']={'job_id':120924837650,'expected_packages':expected_packages,
        'actual_packages':{key:packages.get(key) for key in expected_packages},
        'same_versions':package_result['returncode']==0 and all(packages.get(key)==value for key,value in expected_packages.items())}
    save()
    paths={}
    for lib in ('CRT_fp10.o','CRT_fp8.o','libmingwex.a','libmingw32.a','dllcrt2.o','crt2.o'):
        result,data=run('locate-'+lib,[tools['gxx'],'-print-file-name='+lib])
        if result['returncode']==0:
            path=Path(data.decode('utf-8').strip())
            if path.is_absolute() and path.is_file():
                paths[lib]=path;report.setdefault('libraries',{})[lib]={'path':str(path),'sha256':sha(path)}
                run('symbols-'+lib,[tools['nm'],'-A',path])
    source=out/'fenv-probe.cpp';source.write_bytes(SOURCE.encode())
    plans=[('exe-default',[],'.exe'),('dll-default',['-shared','-mwindows'],'.dll')]
    if 'CRT_fp10.o' in paths:plans.append(('dll-explicit-crt10',['-shared','-mwindows',str(paths['CRT_fp10.o'])],'.dll'))
    else:report['crt10_arm_unavailable']=True
    for name,flags,suffix in plans:
        binary=out/(name+suffix)
        cmd=[tools['gxx'],'-static',*flags,source,'-o',binary]
        run(name+'-link-plan',[*cmd,'-###'])
        result,_=run(name+'-link',cmd)
        if result['returncode']!=0 or not binary.is_file():continue
        report.setdefault('binaries',{})[name]={'path':binary.name,'sha256':sha(binary)}
        run(name+'-imports',[tools['objdump'],'-p',binary])
        if suffix=='.exe':run(name+'-execute',[binary])
        else:run(name+'-execute',[sys.executable,'-I','-c','import ctypes,sys; d=ctypes.CDLL(sys.argv[1]); d.probe.restype=ctypes.c_int; sys.exit(d.probe())',binary])
    # Separate object compilation makes the unresolved inputs to the linker
    # observable. Original three arms above are retained without alteration.
    saved_source=out/'saved-only-probe.cpp';saved_source.write_bytes(SAVED_SOURCE.encode())
    report['saved_source_sha256']=sha(saved_source)
    saved_object=out/'saved-only-probe.o'
    compiled,_=run('saved-only-compile',[tools['gxx'],'--std=c++17','-O3','-c',saved_source,'-o',saved_object])
    if compiled['returncode']==0 and saved_object.is_file():
        run('saved-only-object-symbols',[tools['nm'],'-A',saved_object])
        dll_arms=[('saved-dll-default',[]),('saved-dll-extra-mingw32',['-lmingw32'])]
        if 'CRT_fp10.o' in paths:dll_arms.append(('saved-dll-explicit-crt10',[str(paths['CRT_fp10.o'])]))
        scintilla_libs=['-lgdi32','-luser32','-limm32','-lole32','-luuid','-loleaut32','-ladvapi32','-lstdc++']
        for name,extra in dll_arms:
            binary=out/(name+'.dll')
            cmd=[tools['gxx'],'-shared','-static','-mwindows','-o',binary,'-s',saved_object,
                 *scintilla_libs,*extra,'-Wl,-Map,'+str(out/(name+'.map.log')),
                 '-Wl,--trace-symbol,__mingw_fe_dfl_env','-Wl,--trace-symbol,_fpreset']
            run(name+'-link-plan',[*cmd,'-###'])
            linked,_=run(name+'-link',cmd)
            if linked['returncode']!=0 or not binary.is_file():continue
            report.setdefault('binaries',{})[name]={'path':binary.name,'sha256':sha(binary)}
            run(name+'-imports',[tools['objdump'],'-p',binary])
            run(name+'-execute',[sys.executable,'-I','-c','import ctypes,sys; d=ctypes.CDLL(sys.argv[1]); d.probe.restype=ctypes.c_int; sys.exit(d.probe())',binary])
    report['collection_complete']=True
    save()

if __name__=='__main__':main()
