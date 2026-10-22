import copy,hashlib,unittest
from types import SimpleNamespace
from unittest.mock import patch
import no_folds_compare as c
import no_folds_result as r

class API:
    def __init__(self,data,groups=2):self.data=data;self.original=data;self.dirty=0;self.groups=groups;self.history=[];self.style=0
    def scalar(self,h,m,w=0,l=0):
        if m==2006:return len(self.data)
        if m==2159:return self.dirty
        if m==2007:return self.data[w]
        if m==2028:return len(self.data)
        if m==2010:return self.style
        if m==2174:return 1
        if m==0x102:self.history.append(self.data);self.data=self.data[:8]+b'x'+self.data[8:];self.dirty=1
        if m==0x100:self.history.append(self.data);self.data=self.data[:8]+self.data[9:];self.dirty=1
        return 0
    def mode_proof(self,*a,**kw):return {}
    def command(self,h,n):
        if self.groups==1:self.data=self.original;self.history=[];self.dirty=0
        else:self.data=self.history.pop();self.dirty=int(bool(self.history))

class Tests(unittest.TestCase):
    def test_natural_groups(self):
        for groups in (1,2):
            api=API(c.TEXT,groups);deadline=c.f.Deadline();reference=None
            for op in ('prepare','insert','backspace','undo'):
                row={};reference=c.stage(None,api,1,2,deadline,1,c.TEXT,c.fixture(0)[1],op,row,reference)
                self.assertEqual(row['completed'],1)
                if op=='undo':
                    self.assertEqual(len(row['rounds']),groups)
                    self.assertEqual(row['rounds'][-1]['dirty'],0)
                    self.assertTrue(all(x['text_upper_ms']<=x['style_upper_ms']<=x['ready_upper_ms'] for x in row['rounds']))
    def test_reject_fake_styles(self):
        api=API(c.MARKDOWN)
        with self.assertRaises(ValueError):c.styles_ready(api,1,1,c.MARKDOWN,c.fixture(1)[1],False)
    def test_source_menu_is_real_disable(self):
        root=c.Path(__file__).resolve().parent.parent/'public-recovery-20261021/markdown_edit_profile'
        if not root.exists():root=c.Path(__file__).resolve().parents[2]/'baseline'
        main=(root/'src/main.ru').read_text();md=(root/'src/markdown_syntax.ru').read_text()
        self.assertIn("若 号 == 507",main)
        self.assertIn("语 其 设置折叠 编辑柄 (当前 其 查 'markdownFolds')",main)
        self.assertIn("若 非 开启 则 态 其 增 'policy' 空. 态 其 增 'phase' 'visibility'.",md)
        self.assertIn("若 非 旧['foldEnabled'] 则\n        态 其 增 'policy' 空.\n        态 其 增 'phase' 'disabled'.\n        态 其 增 'pending' 假.",md)
    def test_disabled_proof_getautomaticfold_not_modeventmask(self):
        calls=[]
        api=SimpleNamespace(verify_fixture_title=lambda h:None,comparison_document=17,
          scalar=lambda h,m,*a:(calls.append(m) or {2357:17,4002:98,2664:0}[m]),
          markdown_status=lambda h:'status',control=lambda *a:11)
        ci=SimpleNamespace(parse_markdown_diagnostic=lambda s:dict(id=1,phase=4,pending=0,feed=0,published=0))
        with patch.object(c.f,'markdown_state',return_value=(1,0,1,0,0)):c.ru_proof(ci,api,1,2,0,True)
        self.assertIn(2664,calls);self.assertNotIn(2378,calls)
    def test_original_budgets(self):
        self.assertEqual((c.f.STAGE,c.f.HARD),(30,120));self.assertEqual(c.ORDER,(0,1,2))


class SchemaTests(unittest.TestCase):
    def report(self):
        rows=[];api=API(c.TEXT);reference=None
        for op in ('prepare','insert','backspace','undo'):
            row={};reference=c.stage(None,api,1,2,c.f.Deadline(),1,c.TEXT,c.fixture(0)[1],op,row,reference);rows.append(row)
        for row in rows:
            for v in row['rounds']:v['lexer']=98
        return dict(schema=4,observer_revision=4,baseline_commit=c.b.BASELINE,compiler_commit=c.b.COMPILER,
          stages_seconds=30,process_seconds=120,poll_seconds=[.005,.005,.250],order=[0,1,2],repetitions=1,opening_compared=0,
          disabled_marker_after_edits=0,style_semantic_equivalence=0,fixture_sha256=[hashlib.sha256(c.fixture(k)[0]).hexdigest() for k in (0,1)],
          harness_sha256='a'*64,receipt_sha256='b'*64,udl_sha256='c'*64,
          runtime_sha256={'ru':{k:'a'*64 for k in ('ru_notepad.exe','Scintilla.dll','Lexilla.dll','RuSyntax.dll')},'npp':{'notepad++.exe':'b'*64}},
          host=dict(windows_version=[10,0,1],cpu_count=2,cpu_identifier_sha256='a'*64,runner_image_sha256='b'*64),
          runs=[dict(arm=0,fixture=0,passed=1,executed=1,cleanup_unconfirmed=0,runtime_unchanged=1,fixture_unchanged=1,provenance_unchanged=1,error_kind=0,stages=rows)])
    def test_schema_roundtrip(self):self.assertIsNotNone(r.validate(self.report()))
    def test_schema_rejects_fields_lengths_dirty_censor_and_budget(self):
        original=self.report()
        mutations=[lambda x:x.update(private_path='secret'),lambda x:x.update(process_seconds=121),
          lambda x:x['runs'][0]['stages'][0]['rounds'][0].update(length=999999),
          lambda x:x['runs'][0]['stages'][3]['rounds'][-1].update(dirty=1),
          lambda x:x['runs'][0]['stages'][3].update(censored=1),
          lambda x:x['runs'][0]['stages'][0]['rounds'][0].update(lexer=0),
          lambda x:x['runs'][0]['stages'][1]['dispatches'][0].update(acknowledged=0),
          lambda x:x.update(disabled_marker_after_edits=1)]
        for mutate in mutations:
            report=copy.deepcopy(original);mutate(report)
            with self.assertRaises(ValueError):r.validate(report)
    def test_partial_timeout_allowed_but_not_pass(self):
        x=self.report();run=x['runs'][0];run['passed']=0;run['error_kind']=3
        run['stages'][-1].update(completed=0,censored=1,rounds=[])
        self.assertIsNotNone(r.validate(x))
    def test_no_native_run_on_linux(self):
        with self.assertRaises(ValueError):c.b.host_guard(platform='posix')

if __name__=='__main__':unittest.main()
