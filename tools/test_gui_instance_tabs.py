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
        def pid(hwnd,out):
            import ctypes
            ctypes.cast(out,ctypes.POINTER(subject.wintypes.DWORD)).contents.value=123
            return 7
        api.user.GetWindowThreadProcessId.side_effect=pid
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
            for hwnd,_,_ in windows:self.assertTrue(any(c.args[0]==hwnd for c in api.user.GetWindowThreadProcessId.call_args_list))

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
            with self.assertRaisesRegex(RuntimeError,'Timed out: command805 information box'):
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



class InformationBoxTests(unittest.TestCase):
    def shape(self,identifier=2):
        return {'owner':5,'caption':'ru_notepad','visible':True,'enabled':True,'controls':[
            {'hwnd':12,'class':'Static','control_type':0,'id':65535,'visible':True,'enabled':True,'text':'Expected information'},
            {'hwnd':13,'class':'Static','control_type':3,'id':20,'visible':True,'enabled':True,'text':''},
            {'hwnd':14,'class':'Button','control_type':1,'id':identifier,'visible':True,'enabled':True,'text':'OK'}]}

    def test_exact_information_shape_accepts_both_observed_ok_control_ids(self):
        for identifier in (1,2):
            self.assertEqual(subject._information_shape(self.shape(identifier),5,{'Expected information'}),14)
        # Button caption is OS localized; body and control structure, not an English OK string, bind the action.
        shape=self.shape();shape['controls'][-1]['text']='确定'
        self.assertEqual(subject._information_shape(shape,5,{'Expected information'}),14)

    def test_information_shape_rejects_wrong_dialog_or_any_second_choice(self):
        mutations=[lambda d:d.update(owner=6),lambda d:d.update(caption='Error'),
            lambda d:d.update(visible=False),lambda d:d.update(enabled=False),
            lambda d:d['controls'][0].update(text='Saving preferences failed'),
            lambda d:d['controls'][0].update(visible=False),
            lambda d:d['controls'][-1].update(visible=False),lambda d:d['controls'][-1].update(enabled=False),
            lambda d:d['controls'][1].update(control_type=13),
            lambda d:d['controls'][-1].update(control_type=2),
            lambda d:d['controls'][-1].update(id=6),lambda d:d['controls'][-1].update(id=7),
            lambda d:d['controls'].append(dict(d['controls'][-1],hwnd=15,id=1)),
            lambda d:d['controls'].append(dict(d['controls'][-1],hwnd=15,id=1,visible=False)),
            lambda d:d['controls'].append(dict(d['controls'][0],hwnd=16)),
            lambda d:d['controls'].append(dict(d['controls'][0],hwnd=16,**{'class':'Edit'})),
            lambda d:d['controls'].clear()]
        for i,mutation in enumerate(mutations):
            shape=self.shape();mutation(shape)
            with self.subTest(i=i):self.assertIsNone(subject._information_shape(shape,5,{'Expected information'}))

    def test_scoped_handler_clicks_actual_control_once_after_exact_match(self):
        catalog=json.loads((Path(subject.__file__).resolve().parents[1]/'locales'/'instance_tabs.json').read_text())
        for identifier in (1,2):
            shape=self.shape(identifier);shape['controls'][0]['text']=catalog['instance.next_launch']['en']
            api=ModalDiagnosticTests().make_api([(10,'#32770',True)]);p=Mock(pid=123);p.poll.return_value=None
            api.user.IsWindowVisible.return_value=False
            observed={}
            with patch.object(subject,'_information_dialog',return_value=shape):
                self.assertEqual(subject._information_button(api,p,5,observations=observed),10)
            api.verify_owned_handles.assert_called_once_with(123,5,10,14)
            api.user.PostMessageW.assert_called_once_with(14,0xf5,0,0)
            self.assertEqual(observed['information 805']['controls'][-1]['id'],identifier)

    def test_wrong_information_does_not_click_and_keeps_ten_second_deadline(self):
        api=ModalDiagnosticTests().make_api([(10,'#32770',True)]);p=Mock(pid=123);p.poll.return_value=None
        now=[0.0]
        with patch.object(subject,'_information_dialog',return_value=self.shape()), \
             patch.object(subject.time,'monotonic',side_effect=lambda:now[0]), \
             patch.object(subject.time,'sleep',side_effect=lambda _:now.__setitem__(0,now[0]+1)):
            with self.assertRaisesRegex(RuntimeError,'Timed out: command805 information box'):
                subject._information_button(api,p,5)
        self.assertEqual(now[0],10);api.user.PostMessageW.assert_not_called()

    def test_hidden_owned_observation_does_not_abort_and_foreign_pid_is_rejected(self):
        api=ModalDiagnosticTests().make_api([(10,'HiddenHelper',False),(11,'#32770',True)])
        result=subject._modal_observation(api,Mock(pid=123),1)
        self.assertNotIn('observation_error',result)
        self.assertEqual(len(result['windows']),2)
        self.assertFalse(result['windows'][0]['visible'])
        api.verify_owned_handles.assert_not_called()  # Its visibility precondition is deliberately not used for observing.
        with self.assertRaisesRegex(RuntimeError,'does not belong'):
            subject._owned_pid(api,456,10)
        with self.assertRaisesRegex(RuntimeError,'does not belong'):
            subject._information_dialog(api,Mock(pid=456),10,99999999999)
        api.user.PostMessageW.assert_not_called()

    def test_actual_information_inventory_reads_owned_controls_and_rejects_foreign_child(self):
        import ctypes
        api=ModalDiagnosticTests().make_api([(10,'#32770',True)])
        api.callback_type=lambda callback:callback
        api.user.GetWindow.return_value=5
        records={12:('Static',65535,'Expected information'),13:('Static',20,''),14:('Button',2,'OK')}
        def enumerate_children(hwnd,callback,unused):
            self.assertEqual(hwnd,10)
            for child in records:
                if not callback(child,0):return 0
            return 1
        def classname(hwnd,buffer,size):
            buffer.value=records[hwnd][0];return len(buffer.value)
        def gettext(hwnd,msg,size,address,flags,timeout,out):
            self.assertEqual(msg,0x000d);self.assertLessEqual(timeout,100)
            value=records[hwnd][2] if hwnd in records else 'ru_notepad'
            buffer=ctypes.create_unicode_buffer(value)
            ctypes.memmove(address,buffer,ctypes.sizeof(buffer))
            ctypes.cast(out,ctypes.POINTER(ctypes.c_size_t)).contents.value=len(value)
            return 1
        api.user.EnumChildWindows.side_effect=enumerate_children
        api.user.GetClassNameW.side_effect=classname
        api.user.GetDlgCtrlID.side_effect=lambda hwnd:records[hwnd][1]
        api.user.GetWindowLongPtrW.side_effect=lambda hwnd,index:3 if hwnd==13 else 0
        api.user.SendMessageTimeoutW.side_effect=gettext
        result=subject._information_dialog(api,Mock(pid=123),10,subject.time.monotonic()+10)
        self.assertEqual(subject._information_shape(result,5,{'Expected information'}),14)
        self.assertNotIn(13,[c.args[0] for c in api.user.SendMessageTimeoutW.call_args_list])  # SS_ICON is not text.
        original_pid=api.user.GetWindowThreadProcessId.side_effect
        def foreign_pid(hwnd,out):
            if hwnd!=14:return original_pid(hwnd,out)
            ctypes.cast(out,ctypes.POINTER(subject.wintypes.DWORD)).contents.value=999;return 7
        api.user.GetWindowThreadProcessId.side_effect=foreign_pid
        with self.assertRaisesRegex(RuntimeError,'does not belong'):
            subject._information_dialog(api,Mock(pid=123),10,subject.time.monotonic()+10)
        api.user.PostMessageW.assert_not_called()

    def test_information_text_queries_are_bounded_by_remaining_deadline(self):
        api=Mock();api.user.SendMessageTimeoutW.return_value=False
        with patch.object(subject.time,'monotonic',return_value=1):
            with self.assertRaisesRegex(RuntimeError,'did not respond'):
                subject._information_text(api,10,1.05)
        self.assertLessEqual(api.user.SendMessageTimeoutW.call_args.args[5],50)
        api.user.SendMessageTimeoutW.reset_mock()
        with patch.object(subject.time,'monotonic',return_value=2):
            with self.assertRaisesRegex(RuntimeError,'Timed out'):
                subject._information_text(api,10,1.05)
        api.user.SendMessageTimeoutW.assert_not_called()


class PhysicalPopupTests(unittest.TestCase):
    def labels(self):return [{str(i)} for i in range(6)]
    def state(self):
        return {'flags':4,'menu_owner':10,'foreground':10,'popups':[{'hwnd':20,'hmenu':30,'count':6,
            'items':[{'id':1300+i,'state':0,'label':str(i),'rect':[100,100+20*i,250,120+20*i]} for i in range(6)]}]}
    def api(self):
        api=Mock();api.user.GetForegroundWindow.return_value=10
        api.user.WindowFromPoint.return_value=20;api.user.SetCursorPos.return_value=True
        api.user.SendInput.return_value=2
        api.user.GetAsyncKeyState.return_value=0
        api.user.GetCursorPos.return_value=True;api.user.ClientToScreen.return_value=True
        api.user.SetForegroundWindow.return_value=True;api.user.IsWindow.return_value=True
        return api

    def test_win64_input_and_menu_abi_use_fixed_windows_widths(self):
        import ctypes
        self.assertEqual(ctypes.sizeof(subject._Point),8)
        self.assertEqual(ctypes.sizeof(subject._Rect),16)
        if ctypes.sizeof(ctypes.c_void_p)==8:
            self.assertEqual(ctypes.sizeof(subject._MouseInput),32)
            self.assertEqual(ctypes.sizeof(subject._Input),40)
            self.assertEqual(subject._Input.value.offset,8)
            self.assertEqual(ctypes.sizeof(subject._GUIThreadInfo),72)
            self.assertEqual(ctypes.sizeof(subject._MenuBarInfo),48)

    def test_popup_target_requires_exact_owned_menu_ids_labels_enabled_and_rectangle(self):
        target=subject._popup_target(self.state(),10,3,self.labels())
        self.assertEqual((target[0],target[1].x,target[1].y),(20,175,170))
        mutations=[lambda s:s.update(menu_owner=11),lambda s:s.update(flags=0),
            lambda s:s.update(observation_error='bad'),lambda s:s['popups'].append(deepcopy(s['popups'][0])),
            lambda s:s['popups'][0].update(count=5),lambda s:s['popups'][0]['items'][0].update(id=1301),
            lambda s:s['popups'][0]['items'][0].update(label='wrong'),
            lambda s:s['popups'][0]['items'][3].update(state=1),lambda s:s['popups'][0]['items'][3].update(state=2),
            lambda s:s['popups'][0]['items'][3].update(state=0xffffffff),
            lambda s:s['popups'][0]['items'][3].update(rect=[1,2,1,3])]
        for i,mutate in enumerate(mutations):
            state=self.state();mutate(state)
            with self.subTest(i=i):self.assertIsNone(subject._popup_target(state,10,3,self.labels()))

    def test_real_click_is_complete_normal_pair_and_guarded_before_injection(self):
        for right,flags in ((True,[8,16]),(False,[2,4])):
            api=self.api();pending=set()
            with patch.object(subject,'_owned_pid') as owned:
                subject._physical_click(api,Mock(pid=7),10,20,subject._Point(100,200),right,pending)
            count,events,size=api.user.SendInput.call_args.args
            self.assertEqual(count,2);self.assertEqual(size,subject.ctypes.sizeof(subject._Input))
            self.assertEqual([events[i].value.mi.dwFlags for i in range(2)],flags)
            self.assertEqual(pending,set());self.assertEqual(owned.call_count,2)
        for foreground,target in ((11,20),(10,99)):
            api=self.api();api.user.GetForegroundWindow.return_value=foreground;api.user.WindowFromPoint.return_value=target
            with patch.object(subject,'_owned_pid'),self.assertRaises(RuntimeError):
                subject._physical_click(api,Mock(pid=7),10,20,subject._Point(1,2),True,set())
            api.user.SendInput.assert_not_called()
        api=self.api()
        with patch.object(subject,'_owned_pid',side_effect=RuntimeError('foreign PID')),self.assertRaises(RuntimeError):
            subject._physical_click(api,Mock(pid=7),10,20,subject._Point(1,2),True,set())
        api.user.SendInput.assert_not_called()

    def test_partial_injection_tracks_only_our_possible_down_and_context_releases_it(self):
        for sent,expected in ((0,set()),(1,{16})):
            api=self.api();api.user.SendInput.return_value=sent;pending=set()
            with patch.object(subject,'_owned_pid'),self.assertRaises(RuntimeError):
                subject._physical_click(api,Mock(pid=7),10,20,subject._Point(1,2),True,pending)
            self.assertEqual(pending,expected)
        api=self.api();api.user.SendInput.side_effect=[1,1]
        api.control.return_value=20
        with patch.object(subject,'_item_rect',return_value=subject._Rect(0,0,40,20)), \
             patch.object(subject,'_popup_state',return_value=self.state()),patch.object(subject,'_owned_pid'), \
             self.assertRaisesRegex(RuntimeError,'both fixture mouse events'):
            subject._context(api,Mock(pid=7),10,2,0,{})
        self.assertEqual(api.user.SendInput.call_count,2)
        count,event,size=api.user.SendInput.call_args.args
        self.assertEqual((count,event[0].value.mi.dwFlags),(1,16))
        self.assertEqual(api.user.SetCursorPos.call_args.args,(0,0))

    def test_preheld_mouse_button_is_not_released_or_reused(self):
        for key in (1,2):
            api=self.api();api.user.GetAsyncKeyState.side_effect=lambda k:0x8000 if k==key else 0
            with self.assertRaisesRegex(RuntimeError,'pre-existing button'):
                subject._context(api,Mock(pid=7),10,2,0,{})
            api.user.SendInput.assert_not_called();api.user.SetCursorPos.assert_not_called()

    def test_popup_disappearance_after_right_up_does_not_reopen_or_fake_close(self):
        api=self.api();api.control.return_value=20
        bad=self.state();bad['popups'][0]['items'][0]['label']='not-ready'
        gone=self.state();gone['popups']=[]
        observations={}
        def wait(api,proc,predicate,description,*args,**kwargs):
            self.assertFalse(predicate());predicate()
        with patch.object(subject,'_item_rect',return_value=subject._Rect(0,0,40,20)), \
             patch.object(subject,'_popup_state',side_effect=[self.state(),bad,gone]), \
             patch.object(subject,'_owned_pid'),patch.object(subject,'_wait',side_effect=wait), \
             self.assertRaisesRegex(RuntimeError,'normal right-button release'):
            subject._context(api,Mock(pid=7),10,2,0,observations)
        self.assertEqual(api.user.SendInput.call_count,1)  # Exactly one complete right-click; no reopening.
        self.assertEqual(observations['popup 2 0'][-1]['popups'],[])
        api.user.PostMessageW.assert_not_called()


class ScalarFailureDiagnosticsTests(unittest.TestCase):
    def test_ready_failure_records_exact_stale_editor_request_without_retry(self):
        api=BusyBeforeIdleAPI(False);original=api.scalar;failure=RuntimeError('Synthetic GUI query did not respond within 5 seconds')
        calls=[]
        def query(hwnd,message,wparam=0,lparam=0):
            calls.append((hwnd,message,wparam,lparam))
            if message==2140:raise failure
            return original(hwnd,message,wparam,lparam)
        api.scalar=query;p=Mock(pid=123);p.poll.return_value=None;observed={}
        with patch.object(subject.ctypes,'get_last_error',return_value=1400,create=True), \
             patch.object(subject.ctypes,'set_last_error',create=True), \
             patch.object(subject.time,'perf_counter',side_effect=[0,1,1.002]), \
             patch.object(subject,'_scalar_window_state',return_value={'target_exists':False}), \
             self.assertRaises(RuntimeError) as raised:
            subject._wait_ready(api,p,10,5,'menu current',observed)
        self.assertIs(raised.exception,failure);self.assertIs(api.scalar,query)
        row=observed['scalar failure menu current']
        self.assertEqual((row['message'],row['target_hwnd'],row['last_error'],row['elapsed_ms']),(2140,102,1400,2.0))
        self.assertEqual(row['declared_timeout_ms'],5000);self.assertNotIn('lparam',row)
        self.assertEqual(sum(message==2140 for _,message,_,_ in calls),1)

    def test_real_timeout_and_observer_failure_preserve_original_failure_and_restore_api(self):
        for fail_observer in (False,True):
            api=Mock();failure=RuntimeError('original query failed');api.scalar.side_effect=failure
            original=api.scalar;observed={}
            with patch.object(subject.ctypes,'get_last_error',return_value=1460,create=True), \
                 patch.object(subject.ctypes,'set_last_error',create=True), \
                 patch.object(subject.time,'perf_counter',side_effect=[1,6]), \
                 patch.object(subject,'_scalar_window_state',side_effect=OSError('probe failed') if fail_observer else None,
                              return_value={'target_exists':True,'target_owned':True}), \
                 self.assertRaises(RuntimeError) as raised:
                with subject._scalar_failure_evidence(api,Mock(pid=123),10,observed,'probe'):
                    api.scalar(20,0x1304)
            self.assertIs(raised.exception,failure);self.assertIs(api.scalar,original)
            original.assert_called_once_with(20,0x1304,0,0)
            if fail_observer:self.assertIn('observation failed',failure.__notes__[0])
            else:
                self.assertEqual(observed['scalar failure probe']['elapsed_ms'],5000)
                self.assertEqual(observed['scalar failure probe']['last_error'],1460)

    def test_window_failure_snapshot_is_direct_queries_only_and_identifies_invalid_handle(self):
        import ctypes
        api=Mock();p=Mock(pid=123);p.poll.return_value=None
        api.user.IsWindow.side_effect=lambda hwnd:hwnd==10
        api.user.IsWindowVisible.return_value=False;api.user.IsWindowEnabled.return_value=False
        def pid(hwnd,out):
            ctypes.cast(out,ctypes.POINTER(subject.wintypes.DWORD)).contents.value=123 if hwnd==10 else 0
            return 7 if hwnd==10 else 0
        api.user.GetWindowThreadProcessId.side_effect=pid;api.user.GetGUIThreadInfo.return_value=True
        record=subject._scalar_window_state(api,p,10,20)
        self.assertFalse(record['target_exists']);self.assertFalse(record['target_owned'])
        self.assertEqual(record['target_pid'],0);self.assertTrue(record['main_exists'])
        self.assertEqual(record['main_pid'],123);self.assertIn('gui_thread',record)
        api.scalar.assert_not_called();api.user.SendMessageTimeoutW.assert_not_called()
        api.user.GetClassNameW.assert_not_called()

    def test_bounded_partial_keeps_deep_rectangle_scalar_leaves_without_unbounded_containers(self):
        state={'popup 2 0':[{'stage':'before left click','popups':[{'items':[{'rect':[11,22,33,44]}]}]}]}
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError,'fixture failure'):
                with subject._failure_evidence(tmp,receipt(),state,{}):raise RuntimeError('fixture failure')
            path=Path(tmp)/'instance-tabs-partial.json';self.assertLessEqual(path.stat().st_size,131073)
            record=json.loads(path.read_text())
            self.assertEqual(record['observations']['popup 2 0'][0]['popups'][0]['items'][0]['rect'],[11,22,33,44])
            self.assertFalse(record['accepted'])

if __name__=='__main__':unittest.main()
