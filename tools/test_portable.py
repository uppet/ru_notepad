#!/usr/bin/env python3
"""Execute real shared Ru policies on Linux; never pretend Win32 calls ran."""
import argparse, pathlib, subprocess, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--ru-root',type=pathlib.Path,required=True);a=ap.parse_args()
ru=a.ru_root.resolve()/'ru';build=ROOT/'build';logs=build/'logs';logs.mkdir(parents=True,exist_ok=True)
def run(cmd, log, expected=0, contains=None):
 p=subprocess.run(list(map(str,cmd)),cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 (logs/log).write_text(p.stdout)
 if p.returncode!=expected or (contains and contains not in p.stdout):
  raise SystemExit(f'{log}: unexpected result {p.returncode}\n{p.stdout}')
 print(f'PASS: {log}')
for source,slug,count in [('document_policy','document-policy',23),('ui_arguments','ui-arguments',19),('file_codec_flags','file-codec-flags',80),('shortcuts','shortcuts',34)]:
 src=ROOT/'tests'/f'{source}.ru';exe=build/f'{source}_linux'
 run([sys.executable,ru,'run',src],f'{slug}-python.log',contains=f'TOTAL PASS: {count}')
 run([sys.executable,ru,'build','--cc','gcc',src,'-o',exe],f'{slug}-linux-build.log')
 run([exe],f'{slug}-c.log',contains=f'TOTAL PASS: {count}')
# The exact original source must still fail, demonstrating the actual root cause.
wrong=ROOT/'tests/fixtures/malformed_menu_arguments.ru';exe=build/'malformed_menu_arguments_linux'
run([sys.executable,ru,'run',wrong],'malformed-arguments-python.log',expected=1,contains='位置实参')
run([sys.executable,ru,'build','--cc','gcc',wrong,'-o',exe],'malformed-arguments-linux-build.log')
run([exe],'malformed-arguments-c.log',expected=1,contains='位置实参')
wrong=ROOT/'tests/fixtures/bad_bitfield_arguments.ru';exe=build/'bad_bitfield_arguments_linux'
run([sys.executable,ru,'run',wrong],'bad-bitfield-python.log',expected=1,contains='实际收到事实')
run([sys.executable,ru,'build','--cc','gcc',wrong,'-o',exe],'bad-bitfield-linux-build.log')
run([exe],'bad-bitfield-c.log',expected=1,contains='实际收到事实')
print('Portable policies and exact original failures verified in interpreter and native C.')
