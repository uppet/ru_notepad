import contextlib,hashlib,io,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import feasibility as f
from test_full_receipt import ROOT

class PrivateDiagnostic(unittest.TestCase):
    def fresh(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);root=Path(t.name).resolve()
        (root/'app.exe').write_bytes(b'fixed')
        return root,{'app.exe':f.digest(root/'app.exe')},f.filetime_now(),123
    def log(self,root,tick,pid=123,attempt=0):
        p=root/f'ru_notepad-{pid:08x}-{tick:016x}-{attempt:02d}.log'
        p.write_bytes(b'private synthetic log text\n');return p
    def test_fixed_launcher_and_private_log_hash_only(self):
        b=(ROOT/'packaging/diagnostic_launcher.c').read_bytes()
        self.assertEqual(hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest(),'9d284647cef39c28f0601d3ea137f1012b084307')
        root,expected,tick,pid=self.fresh();p=self.log(root,tick);out=io.StringIO()
        with contextlib.redirect_stderr(out):f.post_runtime(root,expected,'A',pid,tick,tick,True)
        self.assertNotIn(p.name,out.getvalue());self.assertNotIn('private synthetic',out.getvalue())
        self.assertIn('PID=123 COUNT=1 BYTES=27 SHA256=',out.getvalue())
        (root/'app.exe').write_bytes(b'changed')
        with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(ValueError):f.post_runtime(root,expected,'C',pid,tick,tick,True)
    def test_pid_time_attempt_and_npp_rejected(self):
        for kind in ('pid','old','future','attempt','npp','multiple','unknown','missing'):
            with self.subTest(kind=kind):
                root,expected,tick,pid=self.fresh()
                self.log(root,tick+(-20_000_000 if kind=='old' else 20_000_000 if kind=='future' else 0),pid+int(kind=='pid'),64 if kind=='attempt' else 0)
                if kind=='missing':
                    for v in root.glob('*.log'):v.unlink()
                if kind=='multiple':self.log(root,tick,pid,1)
                if kind=='unknown':(root/'unexpected.dll').write_bytes(b'extra')
                with self.assertRaises(ValueError):f.post_runtime(root,expected,'B' if kind=='npp' else 'A',pid,tick,tick,True)
    def test_unconfirmed_cleanup_never_reads_log(self):
        root,expected,tick,pid=self.fresh();self.log(root,tick)
        with patch.object(Path,'open',side_effect=AssertionError('no log read')),self.assertRaises(ValueError):f.post_runtime(root,expected,'A',pid,tick,tick,False)
    def test_oversize_or_links_rejected(self):
        for kind in ('size','hardlink','symlink'):
            with self.subTest(kind=kind):
                root,expected,tick,pid=self.fresh();p=self.log(root,tick)
                if kind=='size':p.write_bytes(b'x'*(f.PRIVATE_LOG_LIMIT+1))
                else:
                    other=root.parent/(root.name+'-link');self.addCleanup(lambda q=other:q.unlink(missing_ok=True))
                    if kind=='hardlink':os.link(p,other)
                    else:
                        p.rename(other)
                        try:p.symlink_to(other)
                        except OSError:self.skipTest('symlink privilege unavailable')
                with self.assertRaises(ValueError):f.post_runtime(root,expected,'A',pid,tick,tick,True)

    def test_npp_recursive_original_inventory_without_output_exceptions(self):
        for change in ('none','changed','extra','missing','link'):
            with self.subTest(change=change):
                root,expected,tick,pid=self.fresh()
                folder=root/'themes';folder.mkdir();p=folder/'original.xml';p.write_bytes(b'original packaged settings')
                expected['themes/original.xml']=f.digest(p)
                if change=='changed':p.write_bytes(b'changed')
                elif change=='extra':(folder/'new.xml').write_bytes(b'unknown')
                elif change=='missing':p.unlink()
                elif change=='link':
                    other=root/'other';p.rename(other)
                    try:p.symlink_to(other)
                    except OSError:self.skipTest('symlink privilege unavailable')
                with contextlib.redirect_stderr(io.StringIO()):
                    if change=='none':f.post_runtime(root,expected,'B',pid,tick,tick,True)
                    else:
                        with self.assertRaises(ValueError):f.post_runtime(root,expected,'B',pid,tick,tick,True)
