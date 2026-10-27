from copy import deepcopy
import unittest
from unittest.mock import Mock, patch
import ast
from pathlib import Path
import tempfile
import json
import gui_instance_tabs as subject
HASHES={n:'a'*64 for n in ('ru_notepad.exe','Scintilla.dll','Lexilla.dll','RuSyntax.dll')}
def receipt():
    result={'schema':'ru-notepad-instance-tabs-gui-v1','name':'main-gui-instance-tabs','passed':True,'executed':True,'cleanup_killed':False,'exit_code':0,'checks':dict.fromkeys(subject.CHECKS,True),'fixture_binary_sha256':dict(HASHES),'phases':[{'phase':phase,'passed':True,'executed':True,'cleanup_killed':False,'exit_code':0,'fixture_binary_sha256':dict(HASHES)} for phase in subject.PHASES], 'secondary_processes':[{'purpose':purpose,'exit_code':0,'cleanup_killed':False,'visible_main_seen':purpose in ('disabled','explicit-multi'),'fixture_binary_sha256':dict(HASHES)} for purpose in subject.CHILDREN]}
    for phase in result['phases']:
        if phase['phase'] in ('startup-race','timeout-uncertain'):phase['participants']=[{'exit_code':0,'cleanup_killed':False} for _ in range(2)]
        if phase['phase']=='timeout-uncertain':phase.update(controlled_ui_suspend=True,owner_delivery_count=0)
    return result
class ReceiptTests(unittest.TestCase):
    def test_modal_commands_are_posted_to_owned_window(self):
        api=Mock()
        api.user.PostMessageW.return_value=True
        subject._post_command(api,123,805)
        api.user.PostMessageW.assert_called_once_with(123,0x111,805,0)
        api.scalar.assert_not_called()
        tree=ast.parse(Path(subject.__file__).read_text())
        for node in ast.walk(tree):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='command' and len(node.args)>1:
                self.assertFalse(isinstance(node.args[1],ast.Constant) and node.args[1].value in (805,113),'modal command was synchronously sent')

    def test_complete_synthetic_contract(self):self.assertTrue(subject.validate_result(receipt(),HASHES))
    def test_reject_incomplete_or_forged_receipts(self):
        mutations=[lambda r:r.update(extra=True),lambda r:r.pop('schema'),lambda r:r.update(schema='old'),lambda r:r.update(name='other'),lambda r:r.update(passed=False),lambda r:r.update(executed=False),lambda r:r.update(cleanup_killed=True),lambda r:r.update(exit_code=False),lambda r:r.update(exit_code=1),lambda r:r['fixture_binary_sha256'].update({'ru_notepad.exe':'b'*64}),lambda r:r['checks'].pop(subject.CHECKS[0]),lambda r:r['checks'].update(unknown=True),lambda r:r['checks'].update({subject.CHECKS[0]:1}),lambda r:r['checks'].update({subject.CHECKS[0]:False}),lambda r:r['phases'].pop(),lambda r:r['phases'].reverse(),lambda r:r['phases'][0].update(executed=False),lambda r:r['phases'][0].update(exit_code=False),lambda r:r['phases'][0].update(cleanup_killed=True),lambda r:r['phases'][0].update(fixture_binary_sha256={}),lambda r:r['secondary_processes'].pop(),lambda r:r['secondary_processes'].reverse(),lambda r:r['secondary_processes'][0].update(exit_code=False),lambda r:r['secondary_processes'][0].update(cleanup_killed=True),lambda r:r['secondary_processes'][0].update(visible_main_seen=True),lambda r:r['secondary_processes'][2].update(visible_main_seen=False),lambda r:r['secondary_processes'][0].update(visible_main_seen=0),lambda r:r['secondary_processes'][0].update(fixture_binary_sha256={}),lambda r:r['secondary_processes'][0].update(extra='unvalidated'),lambda r:r['phases'][-1].update(owner_delivery_count=True),lambda r:r['phases'][-1].update(owner_delivery_count=2),lambda r:r['phases'][-1].update(controlled_ui_suspend=False),lambda r:r['phases'][-2]['participants'].pop(),lambda r:r['phases'][-1]['participants'][0].update(exit_code=False),lambda r:r['phases'].__setitem__(0,None),lambda r:r['secondary_processes'].__setitem__(0,None),lambda r:r['phases'][-1]['participants'].__setitem__(0,None)]
        for i,mutate in enumerate(mutations):
            r=deepcopy(receipt());mutate(r)
            with self.subTest(mutation=i):
                with self.assertRaises(ValueError):subject.validate_result(r,HASHES)
class BusyBeforeIdleAPI:
    """Model the production order: register tabs, then later clear busy/locks."""
    def __init__(self,busy=True):
        self.busy=busy;self.active=2;self.ignored=0
        self.docs=[('Untitled · ru_notepad',b''),('一 😀.txt · ru_notepad',b'one'),('二 空格.txt · ru_notepad',b'two')]
        self.user=Mock()
        self.user.IsWindowEnabled.side_effect=lambda handle:not self.busy
        self.user.IsWindowVisible.side_effect=lambda handle:self.busy if handle==901 else True
    def control(self,hwnd,identifier):return identifier
    def editor(self,hwnd):return 100+self.active
    def scalar(self,handle,message,*args):
        if message==0x1304:return 3
        if message==2140:return int(self.busy)
        raise AssertionError('Unexpected fake API scalar '+str(message))
    def text(self,handle):
        if handle==11:return subject.ci._STATUS_PREFIXES['status.opening'][0]+' 100/100' if self.busy else 'Ln 1 Col 1'
        return 'Untitled · ru_notepad' if self.busy else self.docs[self.active][0]
    def editor_bytes(self,hwnd):return self.docs[self.active][1]
    def command(self,hwnd,command):
        if command!=112:raise AssertionError('unexpected command')
        if self.busy:self.ignored+=1
        else:self.active=(self.active+1)%3
    def no_dialog(self,pid):return []


class ReadyContractTests(unittest.TestCase):
    def test_registered_tabs_are_not_open_completion(self):
        api=BusyBeforeIdleAPI();expected={'一 😀.txt':b'one','二 空格.txt':b'two'}
        self.assertEqual(subject._tabs(api,1),3)
        # Reproduce the old count-only acceptance: commands are ignored while
        # busy and the original exact-name validator rejects this state.
        with self.assertRaisesRegex(RuntimeError,'did not display every synthetic file'):
            subject.ci.verify_gui_documents(api,1,expected)
        self.assertEqual(api.ignored,3)
        process=Mock(pid=77);process.poll.return_value=None
        observations={}
        with patch.object(subject.time,'sleep',side_effect=lambda _:setattr(api,'busy',False)) as sleep:
            subject._wait_ready(api,process,1,3,'handoff',observations)
        sleep.assert_called_once_with(.01)
        self.assertTrue(subject._is_ready(observations['handoff'],3))
        subject.ci.verify_gui_documents(api,1,expected)
        self.assertEqual(api.ignored,3)  # none ignored after ready

    def test_every_ready_signal_remains_required(self):
        good=subject._readiness(BusyBeforeIdleAPI(False),1)
        self.assertTrue(subject._is_ready(good,3))
        for key,value in [('tab_count',2),('tabs_enabled',False),('editor_enabled',False),
                          ('cancel_visible',True),('editor_readonly',1),
                          ('status',subject.ci._STATUS_PREFIXES['status.opening'][0]+' 1/1')]:
            with self.subTest(signal=key):
                broken=dict(good);broken[key]=value
                self.assertFalse(subject._is_ready(broken,3))
        self.assertFalse(subject._is_ready(good,3,'wrong title'))
        # Empty startup status is not a fictitious additional gate.
        good['status']='';self.assertTrue(subject._is_ready(good,3))

    def test_idle_does_not_waive_names_bytes_or_count(self):
        expected={'一 😀.txt':b'one','二 空格.txt':b'two'}
        api=BusyBeforeIdleAPI(False)
        self.assertTrue(subject._is_ready(subject._readiness(api,1),3))
        for broken in ({'wrong.txt':b'one','二 空格.txt':b'two'},
                       {'一 😀.txt':b'WRONG','二 空格.txt':b'two'},
                       {'一 😀.txt':b'one'}):
            api.active=2
            with self.assertRaises(RuntimeError):subject.ci.verify_gui_documents(api,1,broken)

    def test_ready_keeps_original_thirty_second_deadline(self):
        api=BusyBeforeIdleAPI();process=Mock(pid=7);process.poll.return_value=None
        with patch.object(subject.time,'monotonic',side_effect=[0,15,30]),patch.object(subject.time,'sleep'):
            with self.assertRaisesRegex(RuntimeError,'Timed out: blocked'):
                subject._wait_ready(api,process,1,3,'blocked')
        with patch.object(subject,'_wait') as wait:
            subject._wait_ready(api,process,1,3,'budget')
            self.assertEqual(wait.call_args.kwargs,{'timeout':30})

    def test_no_tab_count_only_waits_remain(self):
        tree=ast.parse(Path(subject.__file__).read_text())
        for node in ast.walk(tree):
            if not isinstance(node,ast.Call):continue
            name=node.func.id if isinstance(node.func,ast.Name) else node.func.attr if isinstance(node.func,ast.Attribute) else ''
            if name not in ('_wait','wait_gui'):continue
            for arg in node.args:
                if isinstance(arg,ast.Lambda):
                    for inner in ast.walk(arg.body):
                        self.assertFalse(isinstance(inner,ast.Call) and isinstance(inner.func,ast.Name) and inner.func.id=='_tabs','tab-only open wait bypasses ready contract')

    def test_failure_diagnostics_preserve_failure_and_partial_processes(self):
        record=receipt();record.update(passed=False,exit_code=None)
        record['phases']=record['phases'][:1];record['phases'][0]['passed']=False
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError,'exact title mismatch'):
                with subject._failure_evidence(tmp,record,{'handoff':{'title':'actual wrong','tab_count':3}}, {'一.txt':{'sha256':'a'*64}}):
                    raise RuntimeError('exact title mismatch')
            path=Path(tmp)/'instance-tabs-partial.json';self.assertLessEqual(path.stat().st_size,131073)
            diagnostic=json.loads(path.read_text())
            self.assertIs(diagnostic['accepted'],False)
            self.assertEqual(diagnostic['record']['secondary_processes'],record['secondary_processes'])
            self.assertEqual(diagnostic['observations']['handoff']['title'],'actual wrong')
            self.assertIn('src/main.ru',diagnostic['source_sha256'])
            with self.assertRaises(ValueError):subject.validate_result(diagnostic,HASHES)
        with tempfile.TemporaryDirectory() as tmp:
            not_directory=Path(tmp)/'file';not_directory.write_text('fixture')
            with self.assertRaisesRegex(RuntimeError,'original failure') as raised:
                with subject._failure_evidence(not_directory,record,{},{}):
                    raise RuntimeError('original failure')
            self.assertIn('Could not retain',raised.exception.__notes__[0])
        # Success does not create a diagnostic or alter the exact success schema.
        with tempfile.TemporaryDirectory() as tmp:
            with subject._failure_evidence(tmp,receipt(),{},{}):pass
            self.assertFalse((Path(tmp)/'instance-tabs-partial.json').exists())


class ModalDiagnosticTests(unittest.TestCase):
    def make_api(self,windows,visible=True):
        api=Mock();api.windows.return_value=windows
        api.user.GetDlgItem.return_value=44
        api.user.IsWindowVisible.return_value=visible
        api.user.IsWindowEnabled.return_value=True
        api.user.PostMessageW.return_value=True
        api.user.GetWindowTextW.return_value=0
        api.user.GetWindow.return_value=0
        return api

    def test_zero_multiple_or_hidden_button_remain_failures_with_owned_diagnostics(self):
        for windows,visible in [([],True), ([(10,'#32770',True),(11,'#32770',True)],True),
                                ([(10,'#32770',True)],False), ([(10,'#32770',False)],True)]:
            api=self.make_api(windows,visible);p=Mock(pid=123);p.poll.return_value=None
            observed={};clock=[0.0]
            with patch.object(subject.time,'monotonic',side_effect=lambda:clock[0]), \
                 patch.object(subject.time,'sleep',side_effect=lambda _:clock.__setitem__(0,clock[0]+1)):
                with self.assertRaisesRegex(RuntimeError,'Timed out: actual modal button 1'):
                    subject._button(api,p,1,observations=observed,label='test')
            self.assertEqual(clock[0],10)  # Existing deadline unchanged.
            self.assertEqual(observed['modal test']['requested_button'],1)
            self.assertEqual(len(observed['modal test']['windows']),len(windows))
            api.user.PostMessageW.assert_not_called()  # No guessed click.
            api.scalar.assert_not_called()  # No synchronous WM_GETTEXT observation.
            for hwnd,_,_ in windows:api.verify_owned_handles.assert_any_call(123,hwnd)

    def test_owner_identity_is_recorded_but_foreign_owner_is_not_inspected(self):
        import ctypes
        api=self.make_api([(10,'#32770',True)])
        api.user.GetWindow.return_value=987
        def pid(hwnd,out):
            ctypes.cast(out,ctypes.POINTER(subject.wintypes.DWORD)).contents.value=123 if hwnd==10 else 456
            return 7
        api.user.GetWindowThreadProcessId.side_effect=pid
        result=subject._modal_observation(api,Mock(pid=123),1)
        self.assertEqual(result['expected_pid'],123)
        row=result['windows'][0]
        self.assertEqual((row['pid'],row['owner_hwnd'],row['owner_pid']),(123,987,456))
        self.assertTrue(row['enabled'])
        self.assertEqual(api.user.GetWindowTextW.call_count,1)
        self.assertEqual(api.user.GetWindowTextW.call_args.args[0],10)
        self.assertTrue(all(c.args[0]==10 for c in api.user.GetDlgItem.call_args_list))

    def test_post_success_without_dialog_does_not_pass_or_replay_toggle(self):
        api=self.make_api([]);p=Mock(pid=123);p.poll.return_value=None
        observed={};clock=[0.0]
        with patch.object(subject,'_registry_observation',side_effect=[{'observation_error':'FileNotFoundError'},{'type':4,'value':0,'value_is_integer':True}]), \
             patch.object(subject.time,'monotonic',side_effect=lambda:clock[0]), \
             patch.object(subject.time,'sleep',side_effect=lambda _:clock.__setitem__(0,clock[0]+1)):
            with self.assertRaisesRegex(RuntimeError,'Timed out: actual modal button 1'):
                subject._toggle_preference(api,p,5,'isolated',observed,'disable')
        api.user.PostMessageW.assert_called_once_with(5,0x111,805,0)
        self.assertEqual(observed['disable registry after']['value'],0)
        self.assertEqual(observed['modal disable']['windows'],[])

    def test_diagnostic_read_failure_never_masks_original_timeout(self):
        api=self.make_api([]);p=Mock(pid=123);p.poll.return_value=None
        api.windows.side_effect=[[],OSError('read failed')]
        observed={};clock=[0.0]
        with patch.object(subject.time,'monotonic',side_effect=lambda:clock[0]), \
             patch.object(subject.time,'sleep',side_effect=lambda _:clock.__setitem__(0,10)):
            with self.assertRaisesRegex(RuntimeError,'Timed out: actual modal button 1'):
                subject._button(api,p,1,observations=observed)
        self.assertEqual(observed['modal 1']['observation_error'],'OSError')

    def test_registry_observation_is_read_only_and_isolated_and_failure_tolerant(self):
        import sys
        registry=Mock();registry.OpenKey.return_value.__enter__=Mock(return_value=11)
        registry.OpenKey.return_value.__exit__=Mock(return_value=False)
        registry.QueryValueEx.return_value=(0,4)
        path='Software\\ru_notepad\\SingleInstanceTests\\gui_'+'a'*32
        with patch.dict(sys.modules,winreg=registry):
            self.assertEqual(subject._registry_observation(path),{'type':4,'value':0,'value_is_integer':True})
            for wrong in ('Software\\ru_notepad\\Preferences',path+'\\child',path.replace('gui_','user_')):
                self.assertEqual(subject._registry_observation(wrong),{'observation_error':'invalid isolated namespace'})
            registry.OpenKey.assert_called_once_with(registry.HKEY_CURRENT_USER,path)
            registry.QueryValueEx.assert_called_once_with(11,'SingleInstance')
            registry.SetValueEx.assert_not_called()
            registry.OpenKey.side_effect=PermissionError('private details')
            self.assertEqual(subject._registry_observation(path),{'observation_error':'PermissionError','winerror':None})

if __name__=='__main__':unittest.main()
