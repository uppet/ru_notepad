#!/usr/bin/env python3
"""Package built binaries with truthful validation state, never a fake release."""
from __future__ import annotations
import argparse, hashlib, json, re, shutil, struct, subprocess, time, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SYSTEM_DLLS={'advapi32.dll','gdi32.dll','imm32.dll','kernel32.dll','msvcrt.dll','ole32.dll','oleaut32.dll','user32.dll','comctl32.dll','comdlg32.dll','shell32.dll','shlwapi.dll','version.dll','winmm.dll','ntdll.dll','uxtheme.dll','dwmapi.dll'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def inspect(p, objdump):
 data=p.read_bytes()
 if data[:2]!=b'MZ':raise ValueError(f'{p.name}: not an executable')
 off=struct.unpack_from('<I',data,60)[0]
 if data[off:off+4]!=b'PE\0\0' or struct.unpack_from('<H',data,off+4)[0]!=0x8664:raise ValueError(f'{p.name}: not Windows x64')
 text=subprocess.check_output([objdump,'-p',str(p)],text=True)
 imports=re.findall(r'DLL Name:\s*(\S+)',text)
 unknown={x.lower() for x in imports}-SYSTEM_DLLS
 if unknown:raise ValueError(f'{p.name}: unpackaged/unapproved DLLs {unknown}')
 return {'bytes':len(data),'sha256':sha(p),'imports':imports,'machine':'AMD64'}
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--objdump',required=True)
 ap.add_argument('--unverified-preview',action='store_true',help='Explicitly package a cross-built preview with unrun native tests.')
 a=ap.parse_args()
 if not a.unverified_preview:raise SystemExit('This milestone has no Windows runtime pass. Use --unverified-preview only when that delivery is explicitly authorized.')
 if subprocess.check_output(['git','-C',str(ROOT),'status','--porcelain'],text=True).strip():
  raise SystemExit('Commit the reviewed local project snapshot before packaging.')
 version=(ROOT/'VERSION').read_text().strip()
 build=ROOT/'build'
 receipt=json.loads((build/'ru_notepad.build.json').read_text())
 if receipt.get('app_version')!=version:raise SystemExit('App version differs from build receipt.')
 if sha(build/'ru_notepad.exe')!=receipt['exe_sha256']:raise SystemExit('App changed after build receipt.')
 if sha(build/'Scintilla.dll')!=receipt['dll_sha256']:raise SystemExit('Scintilla changed after build receipt.')
 for rel,digest in receipt.get('build_input_sha256',{}).items():
  if sha(ROOT/rel)!=digest:raise SystemExit(f'Build input changed after app build: {rel}')
 if 'packaging/diagnostic_launcher.c' not in receipt.get('build_input_sha256',{}):
  raise SystemExit('The repaired GUI requires a hash-verified diagnostic launcher.')
 for rel,digest in receipt['source_sha256'].items():
  if sha(ROOT/rel)!=digest:raise SystemExit(f'Source changed after app build: {rel}')
 for name,count in [('document-policy-python.log',23),('document-policy-c.log',23),('ui-arguments-python.log',19),('ui-arguments-c.log',19),('file-codec-flags-python.log',80),('file-codec-flags-c.log',80)]:
  txt=(build/'logs'/name).read_text()
  if f'TOTAL PASS: {count}' not in txt or 'FAIL:' in txt:raise SystemExit(f'Policy test not verified: {name}')
 names=['ru_notepad.exe','Scintilla.dll','document_policy.exe','editor_native.exe','app_native.exe','file_codec_tests.exe','file_codec_security_probe.exe','ui_arguments.exe','file_codec_flags.exe']
 test_receipts={}
 for name in names:
  if name=='Scintilla.dll':continue
  r=json.loads((build/Path(name).with_suffix('.build.json')).read_text())
  if sha(build/name)!=r['exe_sha256'] or r['source_sha256']!=receipt['source_sha256'] or r['ru_tree']!=receipt['ru_tree']:
   raise SystemExit(f'Stale or mismatched build receipt: {name}')
  if sha(ROOT/r['entry_source'])!=r['entry_sha256']:raise SystemExit(f'Test source changed after build: {name}')
  test_receipts[name]={'entry_source':r['entry_source'],'entry_sha256':r['entry_sha256'],'generated_c_sha256':r['generated_c_sha256'],'runtime_tested':r['runtime_tested'],'build_input_sha256':r.get('build_input_sha256',{}),'translation_unit_sha256':r.get('translation_unit_sha256',r['generated_c_sha256'])}
 pe={name:inspect(build/name,a.objdump) for name in names}
 dist=ROOT/'dist';dist.mkdir(exist_ok=True)
 stage=dist/f'ru_notepad-{version}-windows-x64'
 if stage.exists():shutil.rmtree(stage)
 stage.mkdir();(stage/'licenses').mkdir()
 for name in names:shutil.copy2(build/name,stage/name)
 shutil.copy2(ROOT/'packaging/README-preview.txt',stage/'README.txt')
 shutil.copy2(ROOT/'packaging/开始前请读.txt',stage/'开始前请读.txt')
 shutil.copy2(ROOT/'packaging/run-tests.cmd',stage/'run-tests.cmd')
 shutil.copy2(ROOT/'CHANGELOG.md',stage/'CHANGELOG.md')
 shutil.copy2(ROOT/'docs/preview-validation.md',stage/'VALIDATION.md')
 shutil.copy2(ROOT/'docs/startup-fix-0.1.1.md',stage/'STARTUP-FIX.md')
 shutil.copy2(ROOT/'packaging/OPTIONAL-ACL-TESTS.txt',stage/'OPTIONAL-ACL-TESTS.txt')
 shutil.copy2(ROOT/'tests/file_codec_security_tests.ps1',stage/'optional-acl-tests.ps1')
 shutil.copytree(ROOT/'packaging/samples',stage/'samples')
 shutil.copy2(ROOT/'docs/notepadpp-parity-roadmap.md',stage/'ROADMAP.md')
 shutil.copy2(ROOT/'vendor/scintilla/License.txt',stage/'licenses/Scintilla.txt')
 shutil.copy2(ROOT/'.tools/root/usr/share/doc/gcc-mingw-w64-base/copyright',stage/'licenses/GCC-runtime.txt')
 shutil.copy2(ROOT/'.tools/root/usr/share/doc/mingw-w64-x86-64-dev/copyright',stage/'licenses/MinGW-w64.txt')
 common=Path('/usr/share/common-licenses/GPL-3')
 if common.exists():shutil.copy2(common,stage/'licenses/GPL-3.txt')
 shutil.copy2(ROOT/'assets/README.md',stage/'licenses/Artwork-provenance.md')
 deps=json.loads((ROOT/'.tools/metadata/PROVENANCE.json').read_text())
 build_packages=[{k:p[k] for k in ('Package','Version','Architecture','SHA256')} for p in deps['packages'] if 'mingw' in p['Package']]
 provenance={
  'schema':1,'version':version,'status':'cross-built; native Windows acceptance pending',
  'packaged_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
  'app_commit':subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
  'ru_commit':receipt['ru_commit'],'ru_tree':receipt['ru_tree'],
  'ru_public_commit':'5626adb791a8b3949a40e2421b9620fba8d785bf',
  'toolchain_native_ci':{'status':'13/13 jobs passed; language toolchain only, not application runtime acceptance','url':'https://github.com/uppet/ru-language/actions/runs/38854666925'},
  'build_entries':test_receipts,
  'build_packages':build_packages,
  'package_source':'https://deb.debian.org/debian/',
  'package_index_sha256':deps['index_sha256'],
  'package_inrelease_sha256':deps['inrelease_sha256'],
  'source_sha256':receipt['source_sha256'],'scintilla_version':receipt['scintilla_version'],
  'scintilla_archive_sha256':receipt['scintilla_archive_sha256'],'binaries':pe,
  'verification':{'passed':['Ru portable document policy: 23/23 Python interpreter','Ru portable document policy: 23/23 Linux native C','Shared GUI argument helpers: 19/19 interpreter and 19/19 Linux native C','Shared numeric flag predicate: 80/80 interpreter and 80/80 Linux C with a strict pure-Ru receiver','104 native call arities and known-syntax boolean parameter gate passed','Windows x64 PE build and DLL import inspection'],
    'not_run':['Windows application UI and dialogs','Scintilla editor integration native test','Win32 file codec native test','Application native integration test','Windows NTFS ACL integration test'],
    'blocker':'The build execution environment could not launch Wine/Xvfb. No Windows or Wine app execution pass is claimed.'}}
 (stage/'BUILD.json').write_text(json.dumps(provenance,indent=2)+'\n')
 files=sorted(p for p in stage.rglob('*') if p.is_file())
 (stage/'SHA256SUMS.txt').write_text(''.join(f'{sha(p)}  {p.relative_to(stage).as_posix()}\n' for p in files))
 archive=dist/(stage.name+'.zip')
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for p in sorted(stage.rglob('*')):
   if p.is_file():z.write(p,p.relative_to(dist).as_posix())
 with zipfile.ZipFile(archive) as z:
  if z.testzip() is not None:raise SystemExit('ZIP CRC validation failed.')
 (archive.with_suffix('.zip.sha256')).write_text(f'{sha(archive)}  {archive.name}\n')
 print(json.dumps({'path':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'status':provenance['status']},indent=2))
if __name__=='__main__':main()
