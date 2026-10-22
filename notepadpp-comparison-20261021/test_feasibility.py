import importlib.util
from pathlib import Path
import unittest, tempfile, subprocess
from unittest.mock import patch
import feasibility as f

class FakeClock:
    def __init__(self): self.now = 0.
    def __call__(self): return self.now
    def sleep(self, seconds): self.now += seconds

class FakeAPI:
    def __init__(self, one_group=False, lexer=0):
        self.length=f.SIZE; self.dirty=False; self.inserted=False; self.undos=0
        self.one_group=one_group; self.lexer=lexer; self.commands=[]
    def scalar(self,h,m,w=0,l=0):
        if m==2006: return self.length
        if m==2159: return self.dirty
        if m==2007: return 120 if self.inserted and w==8 else 97
        if m==4002: return self.lexer
        if m==2028: return self.length if self.lexer==98 else 0
        if m==2174: return True
        if m==0x102:
            self.length=f.SIZE+1; self.inserted=True; self.dirty=True
        if m==0x100:
            self.length=f.SIZE; self.inserted=False; self.dirty=True
        return 0
    def command(self,h,identifier):
        self.commands.append(identifier); self.undos += 1
        self.inserted=not self.one_group and self.undos==1
        self.length=f.SIZE+int(self.inserted); self.dirty=self.inserted
    def markdown_done(self,h): return True

class Test(unittest.TestCase):
    def test_natural_two_undo(self):
        self.sequence(False)
    def test_natural_one_undo(self):
        self.sequence(True)
    def sequence(self, one):
        c=FakeClock(); d=f.Deadline(c); api=FakeAPI(one)
        for op in ('open','insert','backspace','undo'):
            r={};f.run_stage(api,1,2,d,'B',op,r,c,c.sleep)
            self.assertTrue(r['completed'])
        self.assertEqual(r['undo_commands'],1 if one else 2)
        self.assertEqual(api.commands,[42003]*(1 if one else 2))
    def test_plain_has_no_full_endstyled_requirement(self):
        s=dict(lexer=0,endstyled=0,length=f.SIZE,styles=[0]*16,fold_header=False)
        self.assertTrue(f.common_ready(s,'A'));self.assertFalse(f.common_ready(s,'C'))
    def test_markdown_requires_98_and_full_styling(self):
        s=dict(lexer=98,endstyled=f.SIZE,length=f.SIZE,styles=[0]*16,fold_header=False)
        self.assertTrue(f.common_ready(s,'C'));self.assertFalse(f.common_ready(s,'A'))
        s['endstyled']=0;self.assertFalse(f.common_ready(s,'C'))
    def test_stage_30(self):
        c=FakeClock(); d=f.Deadline(c); c.now=30
        with self.assertRaises(TimeoutError): d.remaining()
    def test_hard_120(self):
        c=FakeClock(); d=f.Deadline(c); c.now=119;d.next_stage()
        self.assertEqual(d.remaining(),1);c.now=120
        with self.assertRaises(TimeoutError):d.remaining()
    def test_wrong_lexer_never_passes(self):
        c=FakeClock();d=f.Deadline(c);api=FakeAPI(lexer=3);r={}
        with self.assertRaises(TimeoutError):f.run_stage(api,1,2,d,'A','open',r,c,c.sleep)
        self.assertFalse(r['completed'])
    def test_observed_dirty_backspace_is_not_clean(self):
        self.assertFalse(f.text_matches(dict(length=f.SIZE,context=[97]*4,dirty=False),'backspace'))
    def test_owned_api_rejects_wrong_handle_before_message(self):
        class User:
            def SendMessageTimeoutW(self,*args): raise AssertionError('must not message')
        class Windows:
            def __init__(self): self.user=User()
            def verify_owned_handles(self,pid,hwnd): raise RuntimeError('wrong owner')
        class CI: pass
        CI.Windows=Windows
        class Process:
            pid=123
            def poll(self): return None
        api=f.owned_api(CI,Process(),f.Deadline())
        with self.assertRaisesRegex(RuntimeError,'wrong owner'):api.scalar(3,2006)
    def test_owned_api_rejects_exited_process(self):
        class Windows: pass
        class CI: pass
        CI.Windows=Windows
        class Process:
            pid=123
            def poll(self): return 0
        api=f.owned_api(CI,Process(),f.Deadline())
        with self.assertRaisesRegex(RuntimeError,'exited'):api.scalar(3,2006)
    def test_owned_api_timeout(self):
        class User:
            def SendMessageTimeoutW(self,*args):return 0
        class Windows:
            def __init__(self):self.user=User()
            def verify_owned_handles(self,*args):pass
        class CI:pass
        CI.Windows=Windows
        class Process:
            pid=123
            def poll(self):return None
        api=f.owned_api(CI,Process(),f.Deadline())
        with self.assertRaises(TimeoutError):api.scalar(3,2006)
    def test_cleanup_no_grace_after_budget(self):
        class P:
            def poll(self):return None
            def kill(self):self.killed=True
            def wait(self,timeout):raise AssertionError('no extra timeout')
        p=P();r=f.cleanup_owned(p,120,lambda:120)
        self.assertTrue(p.killed);self.assertTrue(r['cleanup_unconfirmed'])
    def test_cleanup_async_exit_with_remaining_only(self):
        class P:
            code=None
            def poll(self):return self.code
            def kill(self):pass
            def wait(self,timeout):self.timeout=timeout;self.code=-1
        p=P();r=f.cleanup_owned(p,120,lambda:119.5)
        self.assertEqual(p.timeout,.5);self.assertFalse(r['cleanup_unconfirmed'])
    def test_extra_dll_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'ok.dll').write_bytes(b'a')
            expected={'ok.dll':f.digest(root/'ok.dll')}
            f.closed_manifest(root,expected)
            (root/'foreign.dll').write_bytes(b'b')
            with self.assertRaises(ValueError):f.closed_manifest(root,expected)
    def test_copy_mutation_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'source';source.mkdir();(source/'ok.dll').write_bytes(b'a')
            expected={'ok.dll':f.digest(source/'ok.dll')}
            def mutate(inp,out):out.write(b'wrong')
            with patch.object(f.shutil,'copyfileobj',mutate),self.assertRaises(ValueError):f.copy_runtime(source,root/'target',expected)
    def test_undo_timeout_keeps_attempted_evidence(self):
        class API(FakeAPI):
            def command(self,*args):raise TimeoutError('uncertain')
        c=FakeClock();r={}
        with self.assertRaises(TimeoutError):f.run_stage(API(),1,2,f.Deadline(c),'B','undo',r,c,c.sleep)
        self.assertEqual(r['undo_commands'],1);self.assertEqual(r['undo_acknowledged'],0)
        self.assertTrue(r['dispatches'][0]['delivery_completion_unknown'])
    def test_coordinator_stops_unconfirmed_exit(self):
        called=[];results=[]
        def launch(arm):
            called.append(arm)
            return {'arm':arm,'passed':False,'cleanup_unconfirmed':True}
        f.drive_arms(launch,results,lambda:None)
        self.assertEqual(called,['A']);self.assertEqual(len(results),1)
    def test_coordinator_stops_prelaunch_validation_failure(self):
        called=[];results=[]
        def launch(arm):
            called.append(arm);raise ValueError('receipt changed')
        f.drive_arms(launch,results,lambda:None)
        self.assertEqual(called,['A']);self.assertFalse(results[0]['executed'])
    def test_load_real_source(self):
        here=Path(__file__).resolve().parent
        root=next((p for p in (here.parent/'public-recovery-20261021/markdown_edit_profile',here.parent.parent/'baseline') if (p/'tools/windows_ci.py').is_file()),None)
        self.assertIsNotNone(root,'fixed baseline source required')
        ci=f.load_ci(root)
        self.assertEqual(ci.MAIN_CLASS,'RuNotepad.Main.0.1')
        data,_,_=ci.gui_markdown_fixture('singleline')
        self.assertEqual(data,b'a'*f.SIZE)
        source=(root/'src/syntax.ru').read_text()
        self.assertIn('_发设 态 柄 4033 0 0.',source)

if __name__=='__main__': unittest.main()

class DiagnosticPrivacy(unittest.TestCase):
    def test_closed_failure_metadata(self):
        self.assertEqual(f.failure_diagnostics(ValueError('private-path/private-text'), 5), (5,1,0,0))
        self.assertEqual(f.failure_diagnostics(Exception('private-path'), {'private-key':1}), (0,99,0,0))
    def test_traceback_text_is_not_returned(self):
        try: f.closed_manifest(Path('/private-secret-missing'), {})
        except Exception as exc:
            stage, kind, source, line = f.failure_diagnostics(exc, 5)
            self.assertEqual(stage,5)
            self.assertIn(kind,range(1,9))
            self.assertIn(source,range(1,6))
            self.assertTrue(type(line) is int and 0 < line <= 10000)
