import subprocess, sys, unittest, tempfile
from pathlib import Path
class Tests(unittest.TestCase):
    def test_cli_failures_hide_paths(self):
        root=Path(__file__).resolve().parent
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        missing=str(Path(temporary.name)/'missing-parent'/'private-secret-path')
        cases=[('acquire_npp.py',['--allow-download','--destination',missing],1),
               ('build_baseline.py',sum(([flag,'private-secret-path'] for flag in ['--baseline','--compiler','--toolbin','--output','--private-logs']),[]),2),
               ('seal_receipt.py',sum(([flag,'private-secret-path'] for flag in ['--baseline','--compiler','--cc','--ru-dir','--npp-dir','--npp-receipt','--output']),[]),3),
               ('feasibility.py',sum(([flag,'private-secret-path'] for flag in ['--source-root','--ru-dir','--npp-dir','--receipt','--compiler','--cc','--npp-receipt','--output-root']),[]),4),
               ('windows_smoke.py',sum(([flag,'private-secret-path'] for flag in ['--baseline','--compiler','--npp','--receipt','--future-output']),[]),5)]
        for name,args,code in cases:
            with self.subTest(name=name):
                r=subprocess.run([sys.executable,str(root/name),*args],capture_output=True,text=True,timeout=10)
                self.assertEqual(r.returncode,1);self.assertEqual(r.stdout,'')
                expected=f'COMPARISON_FAILURE_CODE={code}'
                if code == 1: expected += '\nCOMPARISON_ACQUIRE_STAGE=0 COMPARISON_ACQUIRE_REASON=102 COMPARISON_HTTP_STATUS=0'
                if code in (4,5):
                    lines=r.stderr.strip().splitlines()
                    self.assertEqual(lines[0],expected)
                    self.assertEqual(len(lines),2)
                    self.assertRegex(lines[1],r'^COMPARISON_PREP_STAGE=[0-9]+ ERROR_KIND=[0-9]+ SOURCE_ID=[0-9]+ LINE=[0-9]+$')
                else: self.assertEqual(r.stderr.strip(),expected)
if __name__=='__main__':unittest.main()
