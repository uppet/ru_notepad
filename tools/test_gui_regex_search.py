"""Portable positive/negative controls. These are never Windows receipts."""
import inspect
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace
import gui_regex_search as gui
from test_gui_search_scope import layouts as scope_layouts
from test_gui_open_search import layouts as result_layouts

HASHES={'ru_notepad.exe':'a'*64}

def receipt():
    return dict(schema='ru-notepad-regex-search-gui-v1',name='main-gui-regex-search',
                passed=True,executed=True,cleanup_killed=False,main_hwnd_seen=True,
                close_posted=True,detached_from_console=True,exit_code=0,
                fixture_binary_sha256=dict(HASHES),fixtures=gui.inventory(),
                reopen=dict(name='main-gui-regex-reopen',passed=True,executed=True,cleanup_killed=False,main_hwnd_seen=True,close_posted=True,detached_from_console=True,exit_code=0,fixture_binary_sha256=dict(HASHES)),
                checks=dict.fromkeys(gui.CHECKS,True),cases=gui.expected_cases(),
                rejected=list(range(len(gui.REJECTED))),engine_gates=list(gui.ENGINE_GATES),
                disclosures=list(gui.DISCLOSURES),layouts=scope_layouts(),results_layouts=result_layouts(),
                labels=[dict(language=l,menu_verified=True,scope_verified=True) for l in gui.LANGUAGES],
                zero_ranges=[[0,0],[4,4],[5,5],[6,6],[0,0]],
                cancellations=[dict(action=a,running_seen=True,stable=True,seconds=.1) for a in gui.CANCEL_ACTIONS])


class Contract(unittest.TestCase):
    def reject(self,row):
        with self.assertRaises(ValueError):gui.validate_result(row,HASHES)
    def test_complete_is_contract_only(self):self.assertTrue(gui.validate_result(receipt(),HASHES))
    def test_required_fields(self):
        for key in receipt():
            row=receipt();del row[key];self.reject(row)
    def test_lifecycle_types(self):
        for key in ('passed','executed','main_hwnd_seen','close_posted','detached_from_console'):
            for value in (False,1,None,'true'):
                row=receipt();row[key]=value;self.reject(row)
        for key,value in (('cleanup_killed',True),('cleanup_killed',0),('exit_code',True),('exit_code',1),('error','bad'),('skips',['case']),('schema','old'),('name','main-gui-open-search'),('fixture_binary_sha256',{})):
            row=receipt();row[key]=value;self.reject(row)
    def test_reopen_lifecycle(self):
        for key in receipt()['reopen']:
            row=receipt();del row['reopen'][key];self.reject(row)
        for key,value in (('passed',1),('cleanup_killed',0),('exit_code',True),('error','bad'),('skips',['bad'])):
            row=receipt();row['reopen'][key]=value;self.reject(row)
    def test_inventory_order_and_identity(self):
        for field in ('fixtures','cases','rejected','engine_gates','disclosures','labels','cancellations'):
            row=receipt();row[field].reverse();self.reject(row)
            row=receipt();row[field].pop();self.reject(row)
        row=receipt();row['fixtures'][0]['sha256']='b'*64;self.reject(row)
        row=receipt();row['fixture_binary_sha256']['ru_notepad.exe']='b'*64;self.reject(row)
    def test_every_check_observed(self):
        source=inspect.getsource(gui.run)
        self.assertNotIn('dict.fromkeys(CHECKS,True)',source)
        for key in gui.CHECKS:
            self.assertIn("['"+key+"']=True",source)
            for value in (False,1,None):
                row=receipt();row['checks'][key]=value;self.reject(row)
            row=receipt();del row['checks'][key];self.reject(row)
        row=receipt();row['checks']['extra']=True;self.reject(row)
    def test_case_range_and_bool_types(self):
        for index in range(len(gui.cases())):
            for field,value in (('selection',[-1,-1]),('unchanged',1),('matched',1)):
                row=receipt();row['cases'][index][field]=value;self.reject(row)
        row=receipt();row['cases'][0]['selection']=[False,1];self.reject(row)
    def test_no_truthy_cancellation_or_latency_substitutes(self):
        for index in range(len(gui.CANCEL_ACTIONS)):
            for field,value in (('running_seen',False),('running_seen',1),('stable',False),('stable',1),('seconds',True),('seconds',-1),('seconds',2),('seconds',float('nan')),('seconds',float('inf'))):
                row=receipt();row['cancellations'][index][field]=value;self.reject(row)
            for field in ('action','running_seen','stable','seconds'):
                row=receipt();del row['cancellations'][index][field];self.reject(row)
    def test_zero_scalar_bytes_exact(self):
        self.assertEqual(gui.fixtures()['zero.txt'],'😀\r\n'.encode())
        row=receipt();row['zero_ranges'][1]=[1,1];self.reject(row)
        row=receipt();row['zero_ranges'][0]=[False,False];self.reject(row)
    def test_no_match_preserves_zero_marker_until_explicit_change(self):
        source=inspect.getsource(gui.run)
        self.assertIn('def no_zero_repeats(expected):',source)
        self.assertIn('for _ in range(3):',source)
        self.assertIn('no_zero_repeats((0,0))',source)
        self.assertIn('no_zero_repeats((6,6))',source)
        self.assertIn("for reset in ('query','caret','scope'):",source)
        self.assertIn("start(r'\\z')",source)
    def test_layout_samples_fail_closed(self):
        self.assertEqual(len(receipt()['layouts']),42)
        self.assertEqual(len(receipt()['results_layouts']),28)
        for field in ('layouts','results_layouts'):
            for index in range(len(receipt()[field])):
                row=receipt();row[field].pop(index);self.reject(row)
        for index in range(7):
            for key in ('menu_verified','scope_verified'):
                row=receipt();row['labels'][index][key]=1;self.reject(row)
    def test_fixture_oracles_are_not_python_regex(self):
        rows={c['id']:c for c in gui.cases()}
        self.assertEqual(rows['previous-nonoverlap']['expected'],(0,3))
        self.assertEqual(rows['previous-ceiling']['expected'],None)
        for name in ('doc-start-not-scope','line-start-not-scope','doc-end-not-scope','line-end-not-scope'):
            self.assertIsNone(rows[name]['expected'])
        for c in gui.cases():
            if c['expected'] is not None:
                a,b=c['expected'];self.assertTrue(0<=a<=b<=len(c['source']))
                c['source'][:a].decode();c['source'][:b].decode()
        self.assertIn('(a?)*',gui.REJECTED);self.assertIn('()+',gui.REJECTED)
    def test_hidden_bar_uses_real_guarded_shortcuts(self):
        self.assertIn('hidden_bar_shortcuts',gui.CHECKS)
        source=inspect.getsource(gui.run)
        self.assertIn('regex_shortcut(api,process,hwnd,api.editor(hwnd),backwards)',source)
        self.assertIn("ui_catalog['search.scope_required']['en']",source)
        self.assertIn('selection()==expected and not running()',source)
        helper=inspect.getsource(gui.regex_shortcut)
        for token in ('GetAsyncKeyState','GetGUIThreadInfo','api.verify_owned_handles(', 'SendInput', 'if not focused()', 'finally:', 'reversed(pending)', '(16,0x72) if backwards else (0x72,)'):
            self.assertIn(token,helper)
        self.assertEqual(len(gui.cases()),29)
        self.assertEqual(len(gui.CANCEL_ACTIONS),15)
        self.assertEqual(gui.RESPONSE_SECONDS,2.0)
        self.assertIn('finish(timeout=900)',source)
        self.assertIn('elapsed>=RESPONSE_SECONDS',source)
    def identity_fixture(self,handles=(200,201),active=0):
        state={'active':active}
        def command(hwnd,identifier):
            self.assertEqual(identifier,112)
            state['active']=(state['active']+1)%len(handles)
        api=SimpleNamespace(editor=Mock(side_effect=lambda hwnd:handles[state['active']]),
                            command=Mock(side_effect=command),responsive=Mock(),
                            text=Mock(return_value='*stress.txt · ru_notepad'),verify_owned_handles=Mock())
        return api,state
    def test_dirty_fixture_is_reactivated_by_verified_live_identity(self):
        api,state=self.identity_fixture(active=1)
        paths={'stress.txt':Path('stress.txt'),'other.txt':Path('other.txt')}
        identities={'stress.txt':200}
        with patch.object(gui,'activate_source') as clean_lookup:
            self.assertEqual(gui.activate_regex_fixture(api,SimpleNamespace(pid=77),100,'stress.txt',paths,identities),200)
        clean_lookup.assert_not_called();api.text.assert_not_called()
        api.verify_owned_handles.assert_called_with(77,100,200)
        self.assertEqual(api.command.call_args_list,[unittest.mock.call(100,112)])
    def test_unknown_fixture_learns_only_after_clean_lookup_and_ownership(self):
        api,state=self.identity_fixture();paths={'stress.txt':Path('stress.txt')};identities={}
        with patch.object(gui,'activate_source') as clean_lookup:
            gui.activate_regex_fixture(api,SimpleNamespace(pid=77),100,'stress.txt',paths,identities)
        clean_lookup.assert_called_once_with(api,100,paths['stress.txt'],1)
        self.assertEqual(identities,{'stress.txt':200})
        api.verify_owned_handles.assert_called_once_with(77,100,200)
        identities.clear();api.verify_owned_handles.side_effect=RuntimeError('foreign')
        with patch.object(gui,'activate_source'):
            with self.assertRaisesRegex(RuntimeError,'foreign'):
                gui.activate_regex_fixture(api,SimpleNamespace(pid=77),100,'stress.txt',paths,identities)
        self.assertEqual(identities,{})
    def test_missing_cached_fixture_does_not_fall_back_to_matching_caption(self):
        api,state=self.identity_fixture(handles=(201,202));paths={'stress.txt':Path('stress.txt')}
        with patch.object(gui,'activate_source') as clean_lookup:
            with self.assertRaisesRegex(RuntimeError,'not reachable'):
                gui.activate_regex_fixture(api,SimpleNamespace(pid=77),100,'stress.txt',paths,{'stress.txt':200})
        clean_lookup.assert_not_called();api.text.assert_not_called()
        self.assertEqual(api.command.call_count,2)
    def test_closed_fixture_identity_is_discarded_before_reopen(self):
        source=inspect.getsource(gui.run)
        before=source.index("del identities['stress.txt']")
        self.assertLess(before,source.index('api.command(hwnd,105)',before))
        self.assertLess(before,source.index("api.drop(hwnd,[paths['stress.txt']])",before))
    def test_partial_progress_persists_only_observed_completions(self):
        progress=dict(checks={'mode_restore':True},cases=[],rejected=[],cancellations=[])
        with tempfile.TemporaryDirectory() as directory:
            gui.write_progress(directory,progress,'cancellation-cleanup','edit')
            saved=json.loads((Path(directory)/'regex-search-progress.json').read_text())
        self.assertEqual(saved,dict(progress,phase='cancellation-cleanup',case='edit'))
        self.assertNotIn('passed',saved)
        self.assertNotIn('cancel_matrix',saved['checks'])
        source=inspect.getsource(gui.run)
        self.assertIn("result['progress']=progress",source)
        self.assertIn("phase('semantic-case',c['id'])",source)
        self.assertIn("phase('cancellation-cleanup',action)",source)
    def shortcut_fixture(self,*,allow_foreground=True,allow_focus=True,held=False):
        state={'foreground':900,'focus':0,'events':[]}
        def foreground(hwnd):
            state['events'].append(('foreground',hwnd))
            if allow_foreground:state['foreground']=hwnd
            return allow_foreground
        def thread_info(thread,pointer):
            pointer._obj.hwndFocus=state['focus'];return True
        def scalar(hwnd,message):
            state['events'].append(('scalar',hwnd,message))
            if allow_focus and message==2400:state['focus']=hwnd
            return 0
        def send(count,pointer,size):
            key=pointer._obj.value.ki
            state['events'].append(('key',key.wVk,key.dwFlags));return 1
        user=SimpleNamespace(
            GetForegroundWindow=Mock(side_effect=lambda:state['foreground']),
            SetForegroundWindow=Mock(side_effect=foreground),
            GetAsyncKeyState=Mock(return_value=0x8000 if held else 0),
            GetGUIThreadInfo=Mock(side_effect=thread_info),
            GetWindowThreadProcessId=Mock(return_value=7),
            SendInput=Mock(side_effect=send))
        api=SimpleNamespace(user=user,scalar=Mock(side_effect=scalar),
                            verify_owned_handles=Mock(),responsive=Mock())
        def wait(api,process,predicate,failure,**kwargs):
            if not predicate():raise RuntimeError(failure)
        return api,state,wait
    def test_shortcut_acquires_child_focus_after_foreground(self):
        for backwards,keys in ((False,[(0x72,0),(0x72,2)]),(True,[(16,0),(0x72,0),(0x72,2),(16,2)])):
            api,state,wait=self.shortcut_fixture()
            with patch.object(gui.ci,'wait_gui',side_effect=wait):
                gui.regex_shortcut(api,SimpleNamespace(pid=77),100,200,backwards)
            self.assertEqual(state['events'][:2],[('foreground',100),('scalar',200,2400)])
            self.assertEqual([item[1:] for item in state['events'] if item[0]=='key'],keys)
            self.assertEqual(state['foreground'],900)
            api.verify_owned_handles.assert_called_with(77,100,200)
            self.assertGreaterEqual(api.verify_owned_handles.call_count,3)
    def test_shortcut_never_injects_without_foreground_and_child_focus(self):
        for field in ('allow_foreground','allow_focus'):
            api,state,wait=self.shortcut_fixture(**{field:False})
            with patch.object(gui.ci,'wait_gui',side_effect=wait):
                with self.assertRaisesRegex(RuntimeError,'regex_focus='):
                    gui.regex_shortcut(api,SimpleNamespace(pid=77),100,200,False)
            api.user.SendInput.assert_not_called()
            if field=='allow_foreground':api.scalar.assert_not_called()
    def test_shortcut_rejects_preheld_keys_without_focus_or_input_changes(self):
        api,state,wait=self.shortcut_fixture(held=True)
        with patch.object(gui.ci,'wait_gui',side_effect=wait):
            with self.assertRaisesRegex(RuntimeError,'pre-existing held key'):
                gui.regex_shortcut(api,SimpleNamespace(pid=77),100,200,True)
        self.assertEqual(state['events'],[])
        api.user.SendInput.assert_not_called()
    def test_uninjected_allocation_failure_is_not_a_pass_claim(self):
        self.assertNotIn('allocation_failure_cleanup',gui.ENGINE_GATES)
        self.assertIn('has not been fault-injected',gui.DISCLOSURES[2])
        row=receipt();row['engine_gates'].append('allocation_failure_cleanup');self.reject(row)
    def test_native_owned_lifecycle_and_actual_input(self):
        source=inspect.getsource(gui.run)
        for token in ('isolated_settings()', '_copy_runtime(', 'ci.run_gui(', 'api.post_navigation(', 'api.verify_owned_handles(', 'api.command(hwnd,STOP)', 'api.command(hwnd,105)', 'api.drop(hwnd,[paths[\'stress.txt\']])',"status('regex.limit')",'scope_gui.native_layout(', 'open_gui.native_layout('):
            self.assertIn(token,source)
        for token in ('WriteProcessMemory','SCI_SETTEXT','SendInput','import re','re.search','re.finditer'):
            self.assertNotIn(token,source)
        self.assertEqual(gui.RESPONSE_SECONDS,2)
        self.assertEqual(gui.STRESS_BYTES,4*1024*1024)
        self.assertIn('not universal DPI',gui.DISCLOSURES[1])

if __name__=='__main__':unittest.main()
