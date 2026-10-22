"""Pure controls only; no downloaded or built application is executed here."""
import copy,ctypes,hashlib,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import npp_udl_compare as n
import npp_udl_result as p
import feasibility as f
from test_feasibility import FakeAPI,FakeClock

class API(FakeAPI):
    def __init__(self,mode=0,one_group=False):
        super().__init__(one_group,152 if mode else 1);self.mode=mode;self.proofs=0;self.style_reads=0;self.context_reads=0
    def scalar(self,h,m,w=0,l=0):
        if m==2028:return self.length
        if m==2010:self.style_reads+=1
        if m==2007:self.context_reads+=1
        return super().scalar(h,m,w,l)
    def mode_proof(self,h,e,mode):
        self.proofs+=1
        if mode!=self.mode:raise RuntimeError('synthetic wrong selected mode')
        return dict(language_type=15 if mode else 0,lexer=self.lexer,udl_menu_id=46181,udl_menu_checked=mode,plain_menu_checked=1-mode,file_count=1,same_buffer=1)


def report(mode_count=2):
    x=dict(schema=3,observer_revision=3,feasibility_only=1,text_times_are_observable_upper_bounds=1,folding_completion_measured=0,npp_version=[8,9,8,1],helper_commit=n.b.BASELINE,official_source_commit=n.NPP_SOURCE,
        archive_sha256=n.acquire.PINS['npp.8.9.8.1.portable.x64.zip'][1],udl_sha256='a'*64,udl_canonical_sha256=n.UDL_CANONICAL,
        executable_sha256='b'*64,fixture_sha256=hashlib.sha256(b'a'*f.SIZE).hexdigest(),harness_sha256='c'*64,receipt_sha256='d'*64,
        host=dict(windows_version=[10,0,20348],cpu_count=4,cpu_identifier_sha256='e'*64,runner_image_sha256='f'*64),
        clock_resolution_seconds=1e-7,requested_poll_seconds=.005,stages_seconds=30,process_seconds=120,official_fold_rules=9,official_nonempty_fold_rules=0,runs=[])
    for mode in range(mode_count):
        api=API(mode);clock=FakeClock();deadline=f.Deadline(clock);stages=[]
        for op in ('open','insert','backspace','undo'):
            row={};n.stage(api,1,2,deadline,mode,op,row,clock,clock.sleep);stages.append(row)
        x['runs'].append(dict(mode=mode,executed=1,passed=1,pid=100+mode,exit_code=1,cleanup_unconfirmed=0,runtime_unchanged=1,
           fixture_unchanged=1,provenance_unchanged=1,udl_unchanged=1,error_kind=0,elapsed_upper_ms=1,stages=stages))
    return x


def synthetic_xml():
    folds=''.join('<Keywords name="Folders in '+category+', '+part+'"></Keywords>' for category in ('code1','code2','comment') for part in ('open','middle','close'))
    return ('<NotepadPlus>\n<UserLang name="Markdown (preinstalled)" ext="md markdown" udlVersion="2.1"><Settings><Global allowFoldOfComments="no"/></Settings><KeywordLists>'+folds+'</KeywordLists></UserLang>\n</NotepadPlus>\n').encode()


class TestUDL(unittest.TestCase):
    def menu_api(self):
        from types import SimpleNamespace
        class User:
            nodes={1:[(46016,'Normal text',8),(0,'Language',0)],2:[(46181,n.UDL_NAME,0)]}
            def GetMenu(self,h):return 1
            def GetMenuItemCount(self,m):return len(self.nodes[m])
            def GetSubMenu(self,m,i):return 2 if m==1 and i==1 else 0
            def GetMenuItemID(self,m,i):return self.nodes[m][i][0]
            def GetMenuState(self,m,i,flags):
                if not flags:i=next(j for j,x in enumerate(self.nodes[m]) if x[0]==i)
                return self.nodes[m][i][2]
            def GetMenuStringW(self,m,i,buffer,size,flags):
                if not flags:i=next(j for j,x in enumerate(self.nodes[m]) if x[0]==i)
                buffer.value=self.nodes[m][i][1];return len(buffer.value)
        api=object.__new__(n.NppAPI);api.user=User();api.deadline=f.Deadline(FakeClock());api.process=SimpleNamespace(pid=7)
        api.base=SimpleNamespace(verify_owned_handles=lambda *args:None)
        return api
    def test_menu_exact_unique_and_mutually_exclusive(self):
        api=self.menu_api();self.assertEqual(api.menu(9),(46181,0,1))
        api.user.nodes=copy.deepcopy(api.user.nodes);api.user.nodes[2].append((46182,n.UDL_NAME,0))
        with self.assertRaises(RuntimeError):api.menu(9,full=True)
        api=self.menu_api();api.user.nodes=copy.deepcopy(api.user.nodes);api.user.nodes[2][0]=(46181,'another UDL',0)
        with self.assertRaises(RuntimeError):api.menu(9)
    def test_actual_scalar_mode_and_owned_buffer_checks(self):
        api=self.menu_api();api.buffer_id=None
        values={2084:12345,2088:0,4002:1,2031:1}
        api.base.scalar=lambda h,m,w=0,l=0:values[m]
        self.assertEqual(api.mode_proof(9,10,0)['same_buffer'],1)
        for key,value in ((2084,12346),(2088,15),(4002,152),(2031,2)):
            old=values[key];values[key]=value
            with self.assertRaises(RuntimeError):api.mode_proof(9,10,0)
            values[key]=old
    def test_cached_menu_uses_owned_path_and_never_reenumerates(self):
        api=self.menu_api();self.assertEqual(api.menu(9),(46181,0,1))
        api.user.GetMenuItemCount=lambda m: (_ for _ in ()).throw(AssertionError('no full traversal'))
        for _ in range(20):self.assertEqual(api.menu(9),(46181,0,1))
        api.user.GetSubMenu=lambda m,i:3
        with self.assertRaises(RuntimeError):api.menu(9)
    def test_cached_menu_label_item_and_root_changes_rejected(self):
        for kind in ('label','id','root'):
            api=self.menu_api();api.menu(9);api.user.nodes=copy.deepcopy(api.user.nodes)
            if kind=='label':api.user.nodes[2][0]=(46181,'other',0)
            elif kind=='id':api.user.nodes[2][0]=(46182,n.UDL_NAME,0)
            else:api.user.GetMenu=lambda h:4
            with self.assertRaises(RuntimeError):api.menu(9)
    def test_menu_bounds_and_cycles(self):
        api=self.menu_api();api.user.GetMenuItemCount=lambda m:257
        with self.assertRaises(RuntimeError):api.menu(9)
        api=self.menu_api();api.user.GetSubMenu=lambda m,i:1
        with self.assertRaises(RuntimeError):api.menu(9)
    def test_same_actions_natural_one_and_two_undo(self):
        for mode in (0,1):
            for one in (False,True):
                api=API(mode,one);clock=FakeClock();deadline=f.Deadline(clock)
                for op in ('open','insert','backspace','undo'):
                    row={};n.stage(api,1,2,deadline,mode,op,row,clock,clock.sleep)
                    self.assertEqual(row['completed'],1)
                self.assertEqual(row['undo_commands'],1 if one else 2)
                self.assertEqual(api.commands,[42003]*(1 if one else 2))
    def test_wrong_lexer_is_identity_failure_not_timeout(self):
        api=API(1);api.lexer=1;c=FakeClock();row={}
        with self.assertRaises(RuntimeError):n.stage(api,1,2,f.Deadline(c),1,'open',row,c,c.sleep)
        self.assertEqual(c.now,0)
    def test_pending_endstyled_does_not_read_styles(self):
        api=API(1);base=api.scalar;c=FakeClock();row={}
        api.scalar=lambda h,m,w=0,l=0:0 if m==2028 else base(h,m,w,l)
        with self.assertRaises(TimeoutError):n.stage(api,1,2,f.Deadline(c),1,'open',row,c,c.sleep)
        self.assertEqual(api.style_reads,0);self.assertEqual(api.context_reads,4);self.assertEqual(api.proofs,0);self.assertAlmostEqual(c.now,30)
    def test_pending_twenty_polls_only_four_scalar_state_reads(self):
        api=API(1);base=api.scalar;c=FakeClock();row={};reads=[]
        def scalar(h,m,w=0,l=0):
            reads.append((c.now,m))
            if m==2028 and c.now<.1:return 0
            return base(h,m,w,l)
        api.scalar=scalar;n.stage(api,1,2,f.Deadline(c),1,'open',row,c,c.sleep)
        middle=[m for t,m in reads if 0<t<.1]
        self.assertTrue(middle);self.assertEqual(set(middle),{2006,2159,4002,2028})
        self.assertEqual(api.context_reads,8);self.assertEqual(api.style_reads,32);self.assertEqual(api.proofs,2)
        self.assertEqual(row['first_text_upper_ms'],0);self.assertGreaterEqual(row['wall_ms'],100)
    def test_final_wrong_mode_and_changed_styles_rejected(self):
        for kind in ('mode','style','dirty','context','endstyled'):
            api=API(1);base=api.scalar;c=FakeClock()
            def scalar(h,m,w=0,l=0):
                if api.proofs:
                    if kind=='style' and m==2010:return 3
                    if kind=='dirty' and m==2159:return 1
                    if kind=='context' and m==2007:return 98
                    if kind=='endstyled' and m==2028:return 0
                return base(h,m,w,l)
            api.scalar=scalar
            if kind=='mode':api.mode=0
            with self.assertRaises(RuntimeError):n.stage(api,1,2,f.Deadline(c),1,'open',{},c,c.sleep)
    def test_stage_budget_not_restarted_on_open(self):
        api=API(1);c=FakeClock();d=f.Deadline(c);c.now=10;row={}
        n.stage(api,1,2,d,1,'open',row,c,c.sleep)
        self.assertEqual(row['first_text_upper_ms'],10000);self.assertEqual(d.hard,120);self.assertEqual(d.stage,30)
    def test_official_xml_raw_preservation_and_narrow_normalization(self):
        data=synthetic_xml();digest=hashlib.sha256(data).hexdigest()
        with tempfile.TemporaryDirectory() as tmp,patch.object(n,'UDL_CANONICAL',digest):
            root=Path(tmp);raw=data.replace(b'\n',b'\r\n');target=n.configure_settings(root/'settings',raw)
            self.assertEqual(n.official_udl(target),raw);n.settings_unchanged(root/'settings',raw)
            target.write_bytes(raw.replace(b'UserLang ',b'UserLang  '))
            with self.assertRaises(ValueError):n.official_udl(target)
    def test_settings_extra_and_modified_udl_rejected(self):
        data=synthetic_xml()
        with tempfile.TemporaryDirectory() as tmp,patch.object(n,'UDL_CANONICAL',hashlib.sha256(data).hexdigest()):
            root=Path(tmp)/'settings';target=n.configure_settings(root,data)
            extra=root/'unexpected.xml';extra.write_text('private synthetic content')
            with self.assertRaises(ValueError):n.settings_unchanged(root,data)
            extra.unlink();(root/'config.xml').write_text('synthetic config never published');n.settings_unchanged(root,data)
            target.write_bytes(data+b' ')
            with self.assertRaises(ValueError):n.settings_unchanged(root,data)
    def test_xml_links_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            real=Path(tmp)/'real';real.write_bytes(synthetic_xml());link=Path(tmp)/'link';os.link(real,link)
            with self.assertRaises(ValueError):n.official_udl(link)
    def test_public_valid_shapes_and_mode_evidence(self):
        x=report();p.validate(x)
        for field,value in [('lexer',1),('language_type',0),('udl_menu_checked',0),('plain_menu_checked',1),('file_count',2),('same_buffer',0)]:
            y=copy.deepcopy(x);y['runs'][1]['stages'][0]['mode_proof'][field]=value
            with self.assertRaises(ValueError):p.validate(y)
    def test_public_strict_numeric_hash_and_keys(self):
        x=report()
        for value in (True,float('nan'),float('inf'),{'private path':'a'*64},'a'*64):
            y=copy.deepcopy(x);y['host']['cpu_count']=value
            with self.assertRaises(ValueError):p.validate(y)
        for root in (x,x['host'],x['runs'][0],x['runs'][0]['stages'][0]):
            root['private path']=123
            with self.assertRaises(ValueError):p.validate(x)
            del root['private path']
    def test_failure_can_be_recorded_but_not_passed(self):
        x=report(1);r=x['runs'][0];r.update(passed=0,error_kind=2);r['stages']=[];p.validate(x)
        r['passed']=1
        with self.assertRaises(ValueError):p.validate(x)
    def test_duplicate_json_rejected(self):
        with self.assertRaises(ValueError):json.loads('{"schema":3,"schema":3}',object_pairs_hook=p.unique)
    def test_diagnostics_do_not_return_exception_text(self):
        try:raise RuntimeError('C:/private/path secret')
        except RuntimeError as exc:
            values=n.diagnostics(exc,4);self.assertTrue(all(type(v) is int for v in values));self.assertEqual(values[1],2)

if __name__=='__main__':unittest.main()
