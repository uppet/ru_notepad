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
        self.one_group=one_group; self.lexer=lexer; self.commands=[]; self.revision=0
    def scalar(self,h,m,w=0,l=0):
        if m==2006: return self.length
        if m==2159: return self.dirty
        if m==2007: return 120 if self.inserted and w==8 else 97
        if m==4002: return self.lexer
        if m==2028: return self.length if self.lexer==98 else 0
        if m==2174: return True
        if m==0x102:
            self.length=f.SIZE+1; self.inserted=True; self.dirty=True; self.revision+=1
        if m==0x100:
            self.length=f.SIZE; self.inserted=False; self.dirty=True; self.revision+=1
        return 0
    def command(self,h,identifier):
        self.commands.append(identifier); self.undos += 1; self.revision+=1
        self.inserted=not self.one_group and self.undos==1
        self.length=f.SIZE+int(self.inserted); self.dirty=self.inserted
    def verify_fixture_title(self,h):pass
    def markdown_done(self,h):
        self.last_markdown_marker=dict(id=self.revision+1,gen=1,rev=self.revision,pending=0,length=self.length,feed=self.length)
        return True

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


class InventoryDiagnostics(unittest.TestCase):
    def test_case_hash_and_unknown_paths_are_bounded(self):
        actual={'lexilla.dll':'a'*64,**{f'/private/customer/{i}':'secret' for i in range(30)}}
        expected={'Lexilla.dll':'a'*64}
        result=f.inventory_diagnostics(actual,expected)
        self.assertEqual(result['missing_count'],1)
        self.assertEqual(result['extra_count'],31)
        self.assertEqual(len(result['rows']),16)
        self.assertNotIn('private',__import__('json').dumps(result))
        self.assertNotIn('secret',__import__('json').dumps(result))
        self.assertTrue(all(len(row['path_sha256'])==64 for row in result['rows']))
        pair=f.inventory_diagnostics({'lexilla.dll':'a'*64},expected)['rows']
        self.assertEqual([(x['known_id'],x['case'],x['kind']) for x in pair],[(3,1,1),(3,2,2)])
    def test_hash_difference_exact_id(self):
        x=f.inventory_diagnostics({'ru_notepad.exe':'a'*64},{'ru_notepad.exe':'b'*64})
        self.assertEqual(x['changed_count'],1)
        self.assertEqual(x['rows'][0]['kind'],3)
        self.assertEqual(x['rows'][0]['known_id'],1)


class ArmDiagnostic(unittest.TestCase):
    def test_only_closed_numeric_fields(self):
        self.assertEqual(f.arm_failure_diagnostics('C',RuntimeError('/private/customer secret')),
                         'COMPARISON_ARM_FAILURE ARM=2 ERROR_KIND=2 SOURCE_ID=0 LINE=0')


class TitleIdentity(unittest.TestCase):
    def test_only_known_initial_titles_can_wait(self):
        names={'ru_notepad','Untitled 1 · ru_notepad'};source=Path('fixture.md')
        self.assertEqual(f.title_state('ru_notepad',source,names),0)
        self.assertEqual(f.title_state('Untitled 1 · ru_notepad',source,names),0)
        self.assertEqual(f.title_state('fixture.md · ru_notepad',source,names),1)
        self.assertEqual(f.title_state('* fixture.md · ru_notepad',source,names),1)
        for value in ('other.md · ru_notepad','Untitled 2 · ru_notepad','', '* Untitled 1 · ru_notepad'):
            self.assertEqual(f.title_state(value,source,names),2)

class MarkdownState(unittest.TestCase):
    def test_finite_private_status_classification(self):
        class CI:
            @staticmethod
            def status_contains(s,k):return k in s
            @staticmethod
            def status_startswith(s,k):return s.startswith(k)
        for status,expected in [('',(0,0,0,0,0)),('Markdown',(1,0,0,0,0)),('Markdown status.folding_markdown',(1,1,0,0,0)),('status.opening private/path Markdown status.heading_folds_off error.syntax.markdown_disabled',(1,0,1,1,1))]:
            got=f.markdown_state(CI,status)
            self.assertEqual(got,expected)
            self.assertTrue(all(type(x) is int and x in (0,1) for x in got))

class BoundedTitleRead(unittest.TestCase):
    def test_fixed_single_message_reader_growth_and_boundaries(self):
        import ast,ctypes,hashlib
        from test_full_receipt import ROOT
        code=(ROOT/'tools/windows_ci.py').read_bytes()
        self.assertEqual(hashlib.sha1(b'blob '+str(len(code)).encode()+b'\0'+code).hexdigest(),'bda339bdbbc531ba1df9e2c3c73f58e40a5207bd')
        cls=next(n for n in ast.parse(code).body if isinstance(n,ast.ClassDef) and n.name=='Windows')
        node=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='markdown_status')
        ns={'ctypes':ctypes};exec(compile(ast.Module(body=[node],type_ignores=[]),'<fixed-bounded-reader>','exec'),ns)
        class API:
            value='fixture-with-growing-title.txt · ru_notepad';bad_count=False
            def scalar(self,h,m,w,l):
                if m!=0x000D:raise AssertionError('must not ask changing text length')
                self.calls=getattr(self,'calls',0)+1
                text=self.value[:w-1];buf=ctypes.create_unicode_buffer(text)
                ctypes.memmove(l,buf,ctypes.sizeof(buf))
                return len(text.encode('utf-16-le'))//2+int(self.bad_count)
        api=API()
        for value in ['fixture-with-growing-title.txt · ru_notepad','未命名 1 · ru_notepad','x'*4096]:
            api.value=value;api.calls=0
            self.assertEqual(ns['markdown_status'](api,1),value);self.assertEqual(api.calls,1)
        api.value='x'*4097
        with self.assertRaises(RuntimeError):ns['markdown_status'](api,1)
        api.value='fixture';api.bad_count=True
        with self.assertRaises(RuntimeError):ns['markdown_status'](api,1)

class SparseMarkdown(unittest.TestCase):
    def test_pending_is_three_scalar_probes_without_bursts(self):
        clock=FakeClock()
        class API(FakeAPI):
            def __init__(self):super().__init__(lexer=98);self.events=[];self.status_times=[]
            def scalar(self,h,m,w=0,l=0):
                self.events.append(m);clock.now+=.001
                return super().scalar(h,m,w,l)
            def markdown_done(self,h):
                self.events.append('status');self.status_times.append(clock());clock.now+=.001
                super().markdown_done(h)
                return len(self.status_times)>20
        api=API();result={}
        f.run_stage(api,1,2,f.Deadline(clock),'C','open',result,clock,clock.sleep)
        indices=[i for i,x in enumerate(api.events) if x=='status']
        for a,b in zip(indices[:19],indices[1:20]):self.assertEqual(api.events[a+1:b],[2006,2159])
        self.assertTrue(all(b-a>=.25 for a,b in zip(api.status_times[:20],api.status_times[1:21])))
        self.assertEqual(result['pending_poll_count'],21);self.assertTrue(result['completed'])
        self.assertEqual(api.events[:indices[0]].count(2010),0)
    def test_never_done_uses_original_deadline_and_no_full_proof(self):
        clock=FakeClock()
        class API(FakeAPI):
            def scalar(self,h,m,w=0,l=0):
                if m in (2010,4002,2028,2223):raise AssertionError('heavy pending probe')
                return super().scalar(h,m,w,l)
            def markdown_done(self,h):return False
        result={};d=f.Deadline(clock)
        with self.assertRaises(TimeoutError):f.run_stage(API(lexer=98),1,2,d,'C','open',result,clock,clock.sleep)
        self.assertEqual((d.started,d.stage,d.hard),(0,30,120));self.assertEqual(clock.now,30)
        self.assertLessEqual(result['pending_poll_count'],120);self.assertIsNone(result['first_common_upper_ms'])
    def test_final_invalid_styles_not_accepted(self):
        clock=FakeClock()
        class API(FakeAPI):
            def scalar(self,h,m,w=0,l=0):return 1 if m==2010 else super().scalar(h,m,w,l)
        result={}
        with self.assertRaises(TimeoutError):f.run_stage(API(lexer=98),1,2,f.Deadline(clock),'C','open',result,clock,clock.sleep)
        self.assertFalse(result['completed'])

class MarkdownFreshness(unittest.TestCase):
    def test_fast_complete_natural_two_undo_with_fresh_revisions(self):
        clock=FakeClock();api=FakeAPI(lexer=98);d=f.Deadline(clock)
        stages=[]
        for operation in ('open','insert','backspace','undo'):
            r={};f.run_stage(api,1,2,d,'C',operation,r,clock,clock.sleep);stages.append(r)
        self.assertEqual([s['last']['markdown_rev'] for s in stages],[0,1,2,4])
        self.assertEqual(stages[-1]['undo_commands'],2);self.assertFalse(stages[-1]['last']['dirty'])
    def test_stale_revision_or_changed_generation_never_pass(self):
        for field,value in [('id',2),('rev',1),('gen',2),('pending',1),('feed',0),('length',0)]:
            clock=FakeClock()
            class API(FakeAPI):
                def markdown_done(self,h):
                    super().markdown_done(h);self.last_markdown_marker.update({field:value});return True
            api=API(lexer=98);api.revision=2;api.accepted_markdown_marker=dict(id=2,gen=1,rev=1)
            r={}
            with self.assertRaises(TimeoutError):f.run_stage(api,1,2,f.Deadline(clock),'C','open',r,clock,clock.sleep)
            self.assertFalse(r['completed'])
    def test_marker_changes_during_full_proof_never_pass(self):
        clock=FakeClock()
        class API(FakeAPI):
            def markdown_done(self,h):
                self.revision+=1;return super().markdown_done(h)
        r={}
        with self.assertRaises(TimeoutError):f.run_stage(API(lexer=98),1,2,f.Deadline(clock),'C','open',r,clock,clock.sleep)
        self.assertFalse(r['completed'])
    def test_dirty_changes_after_full_proof_never_pass(self):
        clock=FakeClock()
        class API(FakeAPI):
            reads=0
            def scalar(self,h,m,w=0,l=0):
                if m==2159:
                    self.reads+=1
                    return self.reads%3==1 and self.reads>1
                return super().scalar(h,m,w,l)
        r={}
        with self.assertRaises(TimeoutError):f.run_stage(API(lexer=98),1,2,f.Deadline(clock),'C','open',r,clock,clock.sleep)
        self.assertFalse(r['completed'])

class MarkdownFinalProof(unittest.TestCase):
    def test_final_wrong_context_lexer_or_changed_status_rejected(self):
        for bad in ('context','lexer','status'):
            clock=FakeClock()
            class API(FakeAPI):
                status_count=0
                def scalar(self,h,m,w=0,l=0):
                    if bad=='context' and m==2007 and self.status_count:return 0
                    if bad=='lexer' and m==4002:return 1
                    return super().scalar(h,m,w,l)
                def markdown_done(self,h):
                    self.status_count+=1;super().markdown_done(h)
                    return bad!='status' or self.status_count%2==1
            result={}
            with self.assertRaises(TimeoutError):f.run_stage(API(lexer=98),1,2,f.Deadline(clock),'C','open',result,clock,clock.sleep)
            self.assertFalse(result['completed']);self.assertIsNone(result['first_common_upper_ms'])

class FinalTitleBinding(unittest.TestCase):
    def test_exact_owned_title_required_without_missing_attribute_bypass(self):
        class CI:
            class Windows:
                def markdown_status(self,h):return self.value
        api=f.owned_api(CI,None,None);api.value='fixture.md · ru_notepad'
        with self.assertRaises(AttributeError):api.verify_fixture_title(1)
        api.expected_fixture_title='fixture.md · ru_notepad'
        api.verify_fixture_title(1);api.value='* '+api.value;api.verify_fixture_title(1)
        for value in ('other.md · ru_notepad','Untitled 1 · ru_notepad',''):
            api.value=value
            with self.assertRaises(RuntimeError):api.verify_fixture_title(1)
    def test_wrong_final_document_fails_identity_not_timeout(self):
        clock=FakeClock()
        class API(FakeAPI):
            def verify_fixture_title(self,h):raise RuntimeError('wrong document')
        result={}
        with self.assertRaises(RuntimeError):f.run_stage(API(lexer=98),1,2,f.Deadline(clock),'C','open',result,clock,clock.sleep)
        self.assertFalse(result['completed'])
