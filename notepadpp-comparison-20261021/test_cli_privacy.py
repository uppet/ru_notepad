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
               ('feasibility.py',sum(([flag,'private-secret-path'] for flag in ['--source-root','--ru-dir','--npp-dir','--receipt','--compiler','--cc','--npp-receipt','--output-root']),[]),4)]
        for name,args,code in cases:
            with self.subTest(name=name):
                r=subprocess.run([sys.executable,str(root/name),*args],capture_output=True,text=True,timeout=10)
                self.assertEqual(r.returncode,1);self.assertEqual(r.stdout,'')
                self.assertEqual(r.stderr.strip(),f'COMPARISON_FAILURE_CODE={code}')
if __name__=='__main__':unittest.main()
