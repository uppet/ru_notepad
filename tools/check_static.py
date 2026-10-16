#!/usr/bin/env python3
"""Run real Ru static checks. Does not execute native source or load DLLs."""
import argparse, pathlib, subprocess, sys
p=argparse.ArgumentParser();p.add_argument('--ru-root',type=pathlib.Path,required=True);a=p.parse_args()
root=pathlib.Path(__file__).resolve().parents[1]
for src in sorted((root/'src').glob('*.ru'))+sorted((root/'tests').glob('*.ru')):
 subprocess.run([sys.executable,str(a.ru_root/'ru'),'check','--target','c','--allow-native',str(src)],check=True)
subprocess.run([sys.executable,str(root/'tools/check_native_arguments.py'),'--ru-root',str(a.ru_root)],check=True)
subprocess.run([sys.executable,str(root/'tools/test_native_arguments.py'),'--ru-root',str(a.ru_root)],check=True)
