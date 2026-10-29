#!/usr/bin/env python3
"""Optional-study controls only; never launches the GUI application."""
import argparse, json, os, subprocess, tempfile, unittest
from pathlib import Path
import test_markdown_phases
import test_markdown_phase_profile

ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cc',default='gcc');args=ap.parse_args()
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(m) for m in (test_markdown_phases,test_markdown_phase_profile))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():return 1
    with tempfile.TemporaryDirectory(prefix='ru-markdown-profile-controls-') as tmp:
        exe=Path(tmp)/('controls.exe' if os.name=='nt' else 'controls')
        subprocess.run([args.cc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-pthread',str(ROOT/'tests/markdown_phase_profile_host.c'),'-o',str(exe)],check=True,timeout=60)
        subprocess.run([str(exe)],check=True,timeout=10)
        record=subprocess.check_output([str(exe),'--emit-valid'],timeout=10,text=True)
        prefix='RU_MARKDOWN_PHASE_PROFILE '
        assert record.startswith(prefix) and record.count('\n')==1
        data=json.loads(record[len(prefix):]);assert data['valid'] and data['complete']==1 and data['depth']==0
        if os.name=='nt':
            native=Path(tmp)/'windows-controls.exe'
            subprocess.run([args.cc,'-std=c11','-O2','-Wall','-Wextra','-Werror',str(ROOT/'tests/markdown_phase_profile_windows.c'),'-o',str(native)],check=True,timeout=60)
            for mode in ('--normal','--foreign'):
                subprocess.run([str(native),mode],check=True,timeout=15)
    print('MARKDOWN_OWNED_PROFILE_HOST_CONTROLS_PASS=1');return 0
if __name__=='__main__':raise SystemExit(main())
