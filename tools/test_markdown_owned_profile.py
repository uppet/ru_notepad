#!/usr/bin/env python3
"""Optional-study controls only; never launches the GUI application.

Fixed numeric markers project from otherwise private logs. Stages:
1 Python, 2 host compile, 3 host run, 4 JSON, 5 Windows compile,
6 normal TLS, 7 foreign TLS, 8 complete. Exit 124 timeout, 125 other error.
"""
import argparse, json, os, subprocess, tempfile, unittest
from pathlib import Path
import test_markdown_phases
import test_markdown_phase_profile

ROOT=Path(__file__).resolve().parents[1]

def marker(kind, value):
    assert kind in ('STAGE','COMPLETE','EXIT')
    assert type(value) is int and -(2**31) <= value < 2**32
    print('MARKDOWN_OWNED_CONTROL_'+kind+'='+str(value), flush=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cc',default='gcc');args=ap.parse_args()
    stage=1
    try:
        marker('STAGE',stage)
        suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(m) for m in (test_markdown_phases,test_markdown_phase_profile))
        result=unittest.TextTestRunner(verbosity=2).run(suite)
        if not result.wasSuccessful():
            marker('EXIT',1);return 1
        marker('COMPLETE',stage)
        with tempfile.TemporaryDirectory(prefix='ru-markdown-profile-controls-') as tmp:
            exe=Path(tmp)/('controls.exe' if os.name=='nt' else 'controls')
            stage=2;marker('STAGE',stage)
            subprocess.run([args.cc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-pthread',str(ROOT/'tests/markdown_phase_profile_host.c'),'-o',str(exe)],check=True,timeout=60)
            marker('COMPLETE',stage)
            stage=3;marker('STAGE',stage)
            subprocess.run([str(exe)],check=True,timeout=10);marker('COMPLETE',stage)
            stage=4;marker('STAGE',stage)
            record=subprocess.check_output([str(exe),'--emit-valid'],timeout=10,text=True)
            prefix='RU_MARKDOWN_PHASE_PROFILE '
            assert record.startswith(prefix) and record.count('\n')==1
            data=json.loads(record[len(prefix):]);assert data['valid'] and data['complete']==1 and data['depth']==0
            marker('COMPLETE',stage)
            if os.name=='nt':
                native=Path(tmp)/'windows-controls.exe'
                stage=5;marker('STAGE',stage)
                subprocess.run([args.cc,'-std=c11','-O2','-Wall','-Wextra','-Werror',str(ROOT/'tests/markdown_phase_profile_windows.c'),'-o',str(native)],check=True,timeout=60)
                marker('COMPLETE',stage)
                for stage,mode in ((6,'--normal'),(7,'--foreign')):
                    marker('STAGE',stage)
                    subprocess.run([str(native),mode],check=True,timeout=15);marker('COMPLETE',stage)
        marker('COMPLETE',8);marker('EXIT',0)
        print('MARKDOWN_OWNED_PROFILE_HOST_CONTROLS_PASS=1');return 0
    except subprocess.CalledProcessError as error:
        code=error.returncode
        marker('EXIT',code if type(code) is int and -(2**31) <= code < 2**32 else 125)
        return 1
    except subprocess.TimeoutExpired:
        marker('EXIT',124);return 1
    except Exception:
        marker('EXIT',125);return 1
if __name__=='__main__':raise SystemExit(main())
