#!/usr/bin/env python3
"""Synthetic controls only; no Windows, editor processes or uploaded raw logs."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import run_markdown_edit_profile as r
import test_markdown_phase_profile as old
import test_windows_ci as harness
import windows_ci as ci


def sample():
    stages=harness.markdown_evidence()['cases'][2]['stages']
    rows=[]
    for index in range(1,6):
        row=old.profile_record()
        for key in ('record','diagnostic_only','product_acceptance','timing_kind','cpu_kind','cpu_bounds','sampling','whole_process_hotspots','valid','raw_counts_trusted'):row.pop(key)
        row.update(snapshot_index=index,scan_bytes=index*1000000+(index>=2)+(index>=4),completion_requested=0)
        for key in ('root_count','no_step_root_count','step_count','outermost_root_ticks','root_user_100ns','root_kernel_100ns','inter_root_gap_ticks','raw_native_other_entries','raw_native_bulk_entries'):row[key]*=index
        row['hot_totals']=[n*index for n in row['hot_totals']]
        for phase in row['phases']:
            for key in ('entries','inclusive_ticks','exclusive_ticks'):phase[key]*=index
            phase['hot']=[n*index for n in phase['hot']]
        row['progress'].update(identity=index,generation=1,revision=index-1,length=1000001 if index in (2,4) else 1000000)
        row['progress']['feed']=row['progress']['length'];rows.append(row)
    for stage,row in zip(stages,rows[:3]+rows[-1:]):
        stage['last_progress']['diagnostic'].update(id=row['progress']['identity'],gen=1,rev=row['progress']['revision'])
    record=dict(schema=1,record='markdown_edit_profile',diagnostic_only=True,product_acceptance='separate_not_claimed',
        timing_kind='nested_qpc_wall',cpu_kind='outer_timer_thread_only',sampling=False,whole_process_hotspots=False,
        valid=True,raw_counts_trusted=True,failure_code=0,snapshot_count=5,records=rows,final=copy.deepcopy(rows[-1]))
    return record,stages


def summary(late=False):
    record,stages=sample()
    if late:stages[-1]['wall_ms']=31000
    runs=[]
    for variant in ('release','profile'):
        run=dict(variant=variant,passed=not late,diagnostic_complete=True,executed=True,cleanup_killed=False,cleanup_unconfirmed=False,
            gates=[dict(product_gate_failed=late and n==3) for n in range(4)],stages=copy.deepcopy(stages),scenario_wall_ms=32000 if late else 1000)
        if variant=='profile':run['edit_profile']=record
        runs.append(run)
    return dict(passed=not late,runs=runs,receipt_sha256='a'*64)


class Controls(unittest.TestCase):
    def test_success_and_double_undo_group(self):
        record,stages=sample();r.validate_stages(ci,stages);r.validate_profile(record,stages)
        out=r.public_projection(summary(),'b'*64,ci)
        self.assertEqual(out['passed'],1)
        self.assertEqual(out['operation_deltas'][3][2],2) # two syntax revisions
        self.assertEqual(out['snapshots'][5],r.counters(record['final']))
    def test_single_undo_and_shutdown_snapshot_separate(self):
        record,stages=sample();record['records'].pop(3);last=record['records'][-1]
        last['snapshot_index']=4;last['scan_bytes']=4000001
        # This synthetic single Undo may skip revision numbers, but not completed scans.
        for key in ('root_count','no_step_root_count','step_count','outermost_root_ticks','root_user_100ns','root_kernel_100ns','inter_root_gap_ticks','raw_native_other_entries','raw_native_bulk_entries'):last[key]=last[key]*4//5
        last['hot_totals']=[n*4//5 for n in last['hot_totals']]
        for phase in last['phases']:
            for key in ('entries','inclusive_ticks','exclusive_ticks'):phase[key]=phase[key]*4//5
            phase['hot']=[n*4//5 for n in phase['hot']]
        stages[-1]['undo_commands']=1;record['snapshot_count']=4;record['final']=copy.deepcopy(last)
        final=record['final'];final['root_count']+=1;final['no_step_root_count']+=1;final['outermost_root_ticks']+=10
        final['phases'][0]['entries']+=1;final['phases'][0]['inclusive_ticks']+=10;final['phases'][0]['exclusive_ticks']+=10
        r.validate_profile(record,stages)
        value=summary()
        for run in value['runs']:run['stages']=copy.deepcopy(stages)
        value['runs'][1]['edit_profile']=record
        out=r.public_projection(value,'b'*64,ci)
        self.assertEqual(out['operation_deltas'][3][2],1)
        self.assertEqual(out['snapshots'][4],[0]*r.COUNTER_COUNT)
        self.assertEqual(out['snapshots'][5][3],out['snapshots'][3][3]+10)

    def test_late_never_passes(self):
        out=r.public_projection(summary(True),'b'*64,ci)
        self.assertEqual((out['passed'],out['diagnostic_complete'],out['diagnostic_late'],out['product_gate_failed']),(0,1,1,1))
        self.assertEqual(out['phase_wall_measured'],1)
        with self.assertRaises(Exception):r.validate_stages(ci,summary(True)['runs'][0]['stages'])
    def test_wrong_claims(self):
        for change in (lambda x:x.update(valid=False),lambda x:x.update(raw_counts_trusted=False),lambda x:x.update(failure_code=4),
                       lambda x:x.update(sampling=True),lambda x:x.update(whole_process_hotspots=True),lambda x:x.update(raw_text='PRIVATE')):
            with self.subTest(change=change):
                record,stages=sample();change(record)
                with self.assertRaises(Exception):r.validate_profile(record,stages)
    def test_revision_and_counter_rejections(self):
        changes=[lambda x:x['records'][2]['progress'].update(identity=1),
                 lambda x:x['records'][2]['progress'].update(generation=2),
                 lambda x:x['records'][2]['progress'].update(revision=1),
                 lambda x:x['records'][2].update(scan_bytes=1),
                 lambda x:x['records'][2].update(depth=1),
                 lambda x:x['records'][2].update(complete=0),
                 lambda x:x['records'][2].update(foreign_thread_invalid=1),
                 lambda x:x['records'][2].update(qpc_frequency=7),
                 lambda x:x['records'][2]['phases'][0].update(exclusive_ticks=999),
                 lambda x:x['final'].update(snapshot_index=4),
                 lambda x:x['records'].pop(),lambda x:x.pop('final')]
        for change in changes:
            with self.subTest(change=change):
                record,stages=sample();change(record)
                with self.assertRaises(Exception):r.validate_profile(record,stages)
    def test_partial_cannot_claim_profile(self):
        value=summary();run=value['runs'][1];run.update(passed=False,diagnostic_complete=False);value['passed']=False
        out=r.public_projection(value,'b'*64,ci)
        self.assertEqual((out['snapshot_count'],out['phase_wall_measured'],out['passed']),(0,0,0))
    def test_public_no_unknown_strings(self):
        value=summary();value['runs'][1]['failure']='PRIVATE PATH / DOCUMENT'
        out=r.public_projection(value,'b'*64,ci)
        self.assertNotIn(b'PRIVATE',r.validate_public(out))
        out['raw_log']='PRIVATE'
        with self.assertRaises(Exception):r.validate_public(out)
    def test_public_nonfinite_bool_hash_rejected(self):
        for key,val in [('snapshot_count',True),('header_sha256','PRIVATE'),('passed',float('nan')),('gc_time_measured',1)]:
            out=r.blank_public();out[key]=val
            with self.assertRaises(Exception):r.validate_public(out)
    def test_late_success_spoof_rejected(self):
        out=r.public_projection(summary(True),'b'*64,ci);out.update(passed=1,failure_code=0)
        with self.assertRaises(Exception):r.validate_public(out)
    def test_cross_level_claim_mismatch_rejected(self):
        changes=[lambda x:x['runs'][0].update(product_gate_failed=1,diagnostic_complete=0),
                 lambda x:x['runs'][0]['stages'][0].update(product_gate_failed=1),
                 lambda x:x.update(diagnostic_complete=0),
                 lambda x:x['runs'][1].update(diagnostic_late=1),
                 lambda x:x['operation_deltas'][0].__setitem__(0,999),
                 lambda x:x['runs'][0]['stages'][0].update(wall_ms=31000)]
        for change in changes:
            value=r.public_projection(summary(),'b'*64,ci);change(value)
            with self.assertRaises(Exception):r.validate_public(value)

    def test_launcher_bounds(self):
        record,stages=sample();text=old.lifecycle()+r.PREFIX+json.dumps(record)+'\n'
        self.assertEqual(r.validate_launcher(text,'profile',stages),record)
        for bad in (text+text,r.PREFIX+'{}',text.replace(r.PREFIX,'prefix '+r.PREFIX),text.replace(r.PREFIX,r.PREFIX+' '*49152)):
            with self.assertRaises(Exception):r.validate_launcher(bad,'profile',stages)
        with self.assertRaises(Exception):r.validate_launcher(text,'release',stages)
    def test_publish_no_replace(self):
        with tempfile.TemporaryDirectory() as d:
            r.publish_public(Path(d),r.blank_public())
            path=Path(d)/'markdown-edit-profile.json';before=path.read_bytes()
            with self.assertRaises(Exception):r.publish_public(Path(d),r.blank_public(2))
            self.assertEqual(path.read_bytes(),before)
    def test_hard_bound_and_no_foreign_pid_helpers(self):
        source=Path(r.__file__).read_text()
        self.assertNotIn('os.kill(',source);self.assertNotIn('OpenProcess(',source)
        clock=old.Clock();deadline=r.base.Deadline(0,clock);clock.value=120
        with self.assertRaisesRegex(r.base.StudyError,'hard_deadline'):deadline.remaining()
    def test_prepare_default_unchanged(self):
        import inspect,run_markdown_owned_profile as owned
        self.assertFalse(inspect.signature(owned.prepare).parameters['edit_profile'].default)


class LifetimeControls(unittest.TestCase):
    def setUp(self):
        self.fixture=old.Controls();self.fixture.setUp()
    def tearDown(self):self.fixture.tearDown()
    def run_fake(self,*,late=False,hang=False,unkillable=False,wrong_owner=False,nondeadline=False,kill_delay=0):
        f=self.fixture;clock=old.Clock();process=old.Process(clock,exit_delay=121 if hang else 0,unkillable=unkillable)
        calls=[]
        if kill_delay:
            def delayed_kill():
                process.kills+=1
                process.exit_at=clock()+kill_delay
            process.kill=delayed_kill
        class Api(old.API):
            def release_drops(self):pass
        def spawn(command,**kwargs):
            calls.append(command);(f.directory/f.log_name()).write_text(old.lifecycle())
            return process
        def perform(ci_,api,owned,deadline,source,logs,guard,sleeper,stages,gates):
            api.verify_owned_handles(owned.pid,1)
            if nondeadline:raise RuntimeError('PRIVATE native error')
            stages.extend(sample()[1]);gates.extend([dict(product_gate_failed=late and n==3) for n in range(4)])
            if late:clock.value=31;stages[-1]['wall_ms']=31000
            return 1
        with patch.object(r,'perform_edits',side_effect=perform):
            out=r.run_owned('release',f.directory,f.source,ci,[],[],spawn=spawn,
                api_factory=lambda c,p,d:Api(p,d,wrong_owner=wrong_owner),
                cpu_query=lambda p:dict(user_100ns=1,kernel_100ns=2,scope='whole_owned_process_lifetime',source='retained_popen_handle'),
                clock=clock,sleeper=clock.sleep,guard_factory=old.Guard)
        return out,process,clock,calls
    def test_success_uses_real_owned_launch_shape(self):
        out,p,c,calls=self.run_fake()
        self.assertTrue(out['passed']);self.assertTrue(out['diagnostic_complete']);self.assertEqual(p.kills,0)
        self.assertEqual(calls[0],[str(self.fixture.directory/'ru_notepad.exe'),'--markdown-phase-diagnostics'])
        self.assertEqual(out['process_cpu']['user_100ns'],1)
    def test_late_complete_is_not_product_success(self):
        out,p,_,_=self.run_fake(late=True)
        self.assertFalse(out['passed']);self.assertTrue(out['diagnostic_complete']);self.assertEqual(p.kills,0)
    def test_total_120_bound_kills_owned_only(self):
        out,p,c,_=self.run_fake(hang=True)
        self.assertFalse(out['passed']);self.assertFalse(out['diagnostic_complete'])
        self.assertEqual((out['failure'],p.kills,c()),('hard_deadline',1,120))
    def test_unconfirmed_cleanup_explicit(self):
        out,p,c,_=self.run_fake(hang=True,unkillable=True)
        self.assertTrue(out['cleanup_unconfirmed']);self.assertFalse(out['diagnostic_complete']);self.assertEqual(c(),120)
    def test_non_deadline_error_not_swallowed(self):
        out,p,_,_=self.run_fake(nondeadline=True)
        self.assertFalse(out['diagnostic_complete']);self.assertEqual(out['failure'],'runner_exception');self.assertEqual(p.kills,1)
        self.assertNotIn('PRIVATE',json.dumps(out))
    def test_async_termination_confirmed_inside_original_budget(self):
        out,p,c,_=self.run_fake(nondeadline=True,kill_delay=.2)
        self.assertEqual(p.kills,1);self.assertFalse(out['cleanup_unconfirmed'])
        self.assertGreaterEqual(c(),.2);self.assertLess(c(),120)
        self.assertFalse(out['diagnostic_complete']);self.assertFalse(out['passed'])
    def test_async_termination_cannot_extend_expired_budget(self):
        out,p,c,_=self.run_fake(hang=True,kill_delay=.2)
        self.assertEqual(p.kills,1);self.assertTrue(out['cleanup_unconfirmed'])
        self.assertEqual(c(),120);self.assertFalse(out['passed'])
    def test_owned_exception_numeric_trace_survives(self):
        out,_,_,_=self.run_fake(nondeadline=True)
        rows=r.owned_failure_rows({'runs':[out]})
        self.assertTrue(rows);self.assertEqual(rows[0][:2],(1,4))
        self.assertNotIn('PRIVATE',repr(rows))
    def test_wrong_owner_fails_before_actions(self):
        out,p,_,_=self.run_fake(wrong_owner=True)
        self.assertEqual(out['failure'],'wrong_hwnd_owner');self.assertEqual(out['stages'],[]);self.assertEqual(p.kills,1)



class PairControls(unittest.TestCase):
    def test_failed_gate_allows_clean_independent_profile(self):
        f=old.Controls();f.setUp()
        try:
            receipt,root,release,profile,_=f.make_manifest();calls=[]
            def run(variant,*args,**kwargs):
                calls.append(variant)
                return dict(variant=variant,passed=False,cleanup_unconfirmed=False)
            result=r.run_pair(receipt,root,release,profile,f.base/'pair',ci=f.ci,run=run)
            self.assertEqual(calls,['release','profile']);self.assertFalse(result['passed'])
        finally:f.tearDown()
    def test_uncertain_cleanup_blocks_second_process(self):
        f=old.Controls();f.setUp()
        try:
            receipt,root,release,profile,_=f.make_manifest();calls=[]
            def run(variant,*args,**kwargs):
                calls.append(variant)
                return dict(variant=variant,passed=False,cleanup_unconfirmed=True)
            result=r.run_pair(receipt,root,release,profile,f.base/'pair',ci=f.ci,run=run)
            self.assertEqual(calls,['release']);self.assertFalse(result['passed'])
        finally:f.tearDown()

class MainControls(unittest.TestCase):
    def test_late_stdout_matches_json_and_exit_failure(self):
        import contextlib,io,run_markdown_owned_profile as owned
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'build').mkdir();out=root/'evidence';out.mkdir()
            arguments=sum((["--"+key,str(out if key=='evidence-dir' else root)] for key in ('ru-root','binary-dir','evidence-dir','cc','windres')),[])
            stdout=io.StringIO()
            with patch.object(r.sys,'platform','win32'),patch.object(owned,'ROOT',root),patch.object(owned,'prepare',return_value=(root,root,root,{})),patch.object(r,'run_pair',return_value=summary(True)),patch.object(r.base,'digest',return_value='b'*64),patch.object(r.base,'load_ci',return_value=ci),contextlib.redirect_stdout(stdout):
                status=r.main(arguments)
            value=json.loads((out/'markdown-edit-profile.json').read_text())
            self.assertEqual(status,1)
            self.assertEqual((value['passed'],value['diagnostic_complete'],value['product_gate_failed']),(0,1,1))
            self.assertIn('MARKDOWN_EDIT_PROFILE_DIAGNOSTIC_COMPLETE=1',stdout.getvalue())
            self.assertIn('MARKDOWN_EDIT_PROFILE_PRODUCT_GATE_FAILED=1',stdout.getvalue())
    def test_unsupported_platform_never_prepares(self):
        import contextlib,io,run_markdown_owned_profile as owned
        with tempfile.TemporaryDirectory() as tmp:
            arguments=sum((["--"+key,tmp] for key in ('ru-root','binary-dir','evidence-dir','cc','windres')),[])
            with patch.object(r.sys,'platform','linux'),patch.object(owned,'prepare',side_effect=AssertionError('must not build')) as prepare,contextlib.redirect_stdout(io.StringIO()):
                status=r.main(arguments)
            prepare.assert_not_called();self.assertEqual(status,1)
            self.assertEqual(json.loads((Path(tmp)/'markdown-edit-profile.json').read_text())['failure_code'],1)



class BoundedObserverControls(unittest.TestCase):
    def test_one_wm_null_has_one_message_and_one_time_charge(self):
        from types import SimpleNamespace
        clock=old.Clock();deadline=r.base.Deadline(0,clock);native=[];owners=[]
        class FakeWindows:
            def __init__(self):self.user=SimpleNamespace(SendMessageTimeoutW=self.send)
            def send(self,hwnd,msg,wp,lp,flags,timeout,result):
                native.append((hwnd,msg,timeout));clock.value+=.001;return 1
            def verify_owned_handles(self,pid,*hwnds):owners.append((pid,hwnds))
        api=r.windows_api(SimpleNamespace(Windows=FakeWindows),SimpleNamespace(pid=42),deadline)
        record=ci.gui_ru_observer_record()
        with ci.GuiRuObserver(api,record,0,clock):api.responsive(1)
        self.assertEqual(len(native),1);self.assertEqual(native[0][1],0)
        self.assertEqual(record['wm_null_calls'],1);self.assertEqual(record['scalar_calls'],0)
        self.assertEqual(record['sendmessage_calls'],1);self.assertEqual(record['query_wall_ms'],1)
        self.assertEqual(owners,[(42,(1,))]);self.assertLessEqual(native[0][2],5000)
        clock.value=120
        with self.assertRaisesRegex(Exception,'hard_deadline'):api.responsive(1)
        self.assertEqual(len(native),1)

class FailureContextControls(unittest.TestCase):
    def test_private_error_message_not_projected(self):
        try: raise ValueError('PRIVATE_PATH=C:/private/input.md')
        except ValueError as error:
            rows=r.failure_context(error)
        self.assertNotIn('PRIVATE',repr(rows))
        self.assertTrue(all(type(value) is int for row in rows for value in row))
    def test_known_module_source_line_is_numeric(self):
        try: r.require(False,'PRIVATE_PATH=C:/private/input.md')
        except Exception as error: rows=r.failure_context(error)
        self.assertTrue(rows)
        self.assertLessEqual(len(rows),16)
        self.assertTrue(all(1<=module<=7 and 1<=line<=99999 and 1<=kind<=5 for module,line,kind in rows))

    def test_owned_context_rejects_non_numeric_and_unknown_values(self):
        for value in ('PRIVATE',True,8,-1):
            with self.subTest(value=value),self.assertRaises(Exception):
                r.owned_failure_rows({'runs':[dict(variant='release',owned_stage=value)]})
        for row in [('PRIVATE',1,1),(8,1,1),(1,100000,1),(1,1,6),(True,1,1)]:
            with self.subTest(row=row),self.assertRaises(Exception):
                r.owned_failure_rows({'runs':[dict(variant='release',failure_context=[row])]})

if __name__=='__main__':unittest.main()
