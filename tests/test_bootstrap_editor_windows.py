"""Portable policy tests only: none grants real Windows/LLVM acceptance."""
import importlib.util
import contextlib
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import verify_bootstrap_editor_windows as gate


def clock_ticks(values):
    iterator = iter(values)
    return lambda: next(iterator, values[-1])


class GatePolicyTests(unittest.TestCase):
    def test_missing_failed_skipped_timeout_or_cleanup_cannot_pass(self):
        rows = {name: {'passed': True, 'executed': True, 'cleanup_killed': False} for name in gate.CASES}
        self.assertTrue(gate.all_passed(rows))
        for key, value in [('passed', False), ('passed', 1), ('executed', False), ('executed', 1), ('cleanup_killed', True), ('cleanup_killed', 0), ('skipped', 1)]:
            bad = {name: dict(row) for name, row in rows.items()}
            bad['argv'][key] = value
            self.assertFalse(gate.all_passed(bad), (key, value))
        del rows['argv']
        self.assertFalse(gate.all_passed(rows))

    def test_wrong_platform_fails_not_skips(self):
        with patch.object(gate.sys, 'platform', 'linux'):
            with self.assertRaisesRegex(ValueError, 'real Windows'):
                gate.verify({})

    def test_argument_edge_cases_exact(self):
        self.assertEqual(gate.ARGV, ['', 'space value', 'quote"slash\\tail\\', '汉😀'])
        self.assertEqual(gate.DEADLINE_SECONDS, 60)
        source = (ROOT/'tests/bootstrap_pipeline/argv_probe.ru').read_text(encoding='utf-8')
        self.assertIn('BOOTSTRAP_ARGV_ENTERED', source)
        self.assertIn('BOOTSTRAP_ARGV_PASS', source)

    def test_log_missing_duplicate_failure_and_size_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            with self.assertRaises(ValueError):
                gate.successful_log(directory, 'PASS_MARKER')
            log = directory/'ru_notepad-owned.log'
            good = '[launcher] Starting Ru program.\nPASS_MARKER\n[launcher] Ru program returned with status 0.\n'
            log.write_text(good, encoding='utf-8')
            self.assertEqual(gate.successful_log(directory, 'PASS_MARKER'), gate.identity(log))
            for text in [good+'PASS_MARKER', good+'FAIL: bad', good.replace('status 0', 'status 1'), 'x'*(1024*1024+1)]:
                log.write_text(text, encoding='utf-8')
                with self.assertRaises(ValueError):
                    gate.successful_log(directory, 'PASS_MARKER')

    def test_log_mutation_after_actual_read_rejected_not_rebaselined(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary).resolve()
            log = directory/'ru_notepad-owned.log'
            good = b'[launcher] Starting Ru program.\nPASS_MARKER\n[launcher] Ru program returned with status 0.\n'
            log.write_bytes(good)
            original_open = Path.open
            reads = []
            @contextlib.contextmanager
            def raced_open(path, mode='r', *args, **kwargs):
                with original_open(path, mode, *args, **kwargs) as stream:
                    if path == log and mode == 'rb':
                        class Reader:
                            def read(self, count):
                                raw = stream.read(count)
                                reads.append((count, raw))
                                if len(reads) == 1:
                                    with original_open(log, 'wb') as writer:
                                        writer.write(b'FAIL: changed after read')
                                return raw
                        yield Reader()
                    else:
                        yield stream
            with patch.object(Path, 'open', raced_open):
                with self.assertRaisesRegex(ValueError, 'validated launcher log changed'):
                    gate.successful_log(directory, 'PASS_MARKER')
            self.assertEqual(reads[0], (1024*1024+1, good))
            self.assertEqual(reads[1][1], b'FAIL: changed after read')

    def test_log_raw_identity_and_invalid_utf8(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary).resolve()
            log = directory/'ru_notepad-owned.log'
            raw = b'[launcher] Starting Ru program.\r\nPASS_MARKER\r\n[launcher] Ru program returned with status 0.\r\n'
            log.write_bytes(raw)
            record = gate.successful_log(directory, 'PASS_MARKER')
            self.assertEqual(record, {'path': str(log), 'size': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
            log.write_bytes(raw+b'\xff')
            with self.assertRaises(UnicodeDecodeError):
                gate.successful_log(directory, 'PASS_MARKER')

    def test_log_changed_after_verify_before_publish_cannot_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary).resolve()
            log, config, output = directory/'ru_notepad-owned.log', directory/'config.json', directory/'output.json'
            log.write_bytes(b'validated bytes')
            record = gate.identity(log)
            config.write_text('{}', encoding='utf-8')
            def finished_verify(_):
                log.write_bytes(b'FAIL: later overwrite')
                return {'status': 'passed', 'results': {'argv': {'log': record}}}
            with patch.object(gate, 'verify', side_effect=finished_verify), patch.object(sys, 'argv', ['gate', '--config', str(config), '--output', str(output)]):
                self.assertEqual(gate.main(), 1)
            result = json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(result['status'], 'failed')
            self.assertIn('validated launcher log changed', result['error'])

    def test_identity_change_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary).resolve()/'owned.exe'
            path.write_bytes(b'original')
            record = gate.identity(path)
            self.assertEqual(gate.verify_identity(record), path)
            path.write_bytes(b'changed')
            with self.assertRaises(ValueError):
                gate.verify_identity(record)

    def test_dialog_control_dispatch_is_not_destruction(self):
        class User:
            alive = True
            def IsWindow(self, hwnd): return self.alive
            def GetDlgItem(self, hwnd, identifier): return 456
            def EnumChildWindows(self,h,callback,param): callback(456,0); return True
            def GetParent(self, hwnd): return 123
            def GetDlgCtrlID(self, hwnd): return 1
            def GetClassNameW(self, hwnd, name, count): name.value = 'Button'; return 6
            def IsWindowEnabled(self, hwnd): return True
            def IsWindowVisible(self, hwnd): return True
        class API:
            callback_type = staticmethod(lambda callback: callback)
            def __init__(self, title='Ru Notepad startup error'):
                self.title, self.events, self.user = title, [], User()
            def windows(self, pid): return [(123, '#32770', True)]
            def verify_owned_handles(self, pid, *handles): self.events.append(('owned', pid, handles))
            def text(self, hwnd): return self.title if hwnd == 123 else 'OK'
            def control(self, hwnd, control): return 456
            def scalar(self, *args): self.events.append(('dispatch', args)); return 0
        def state():
            return dict(found=False, request_attempted=False, dispatch_completed=False, destroyed=False, process_exited=False)
        with patch.object(gate, 'dialog_functions', lambda api: api.user):
            api, record = API(), state()
            gate.owned_dialog(api, 71, record)
            self.assertTrue(record['dispatch_completed'])
            self.assertFalse(record['destroyed'])
            self.assertFalse(record['process_exited'])
            self.assertIn(('dispatch', (123, 0x111, 1, 456)), api.events)
            gate.owned_dialog(api, 71, record)
            self.assertEqual(sum(event[0] == 'dispatch' for event in api.events), 1)
            api.user.alive = False
            gate.owned_dialog(api, 71, record)
            self.assertTrue(record['destroyed'])
            for mutation in ('title', 'parent', 'id', 'class', 'disabled', 'owner', 'dispatch'):
                api, record = API(), state()
                def fail(*args): raise ValueError('injected ownership/dispatch failure')
                if mutation == 'title': api.title = 'Unrelated dialog'
                if mutation == 'parent': api.user.GetParent = lambda h: 789
                if mutation == 'id': api.user.GetDlgCtrlID = lambda h: 3
                if mutation == 'class': api.user.GetClassNameW = lambda *args: 0
                if mutation == 'disabled': api.user.IsWindowEnabled = lambda h: False
                if mutation == 'owner': api.verify_owned_handles = fail
                if mutation == 'dispatch': api.scalar = fail
                with self.assertRaises(ValueError, msg=mutation): gate.owned_dialog(api, 71, record)
                self.assertFalse(record['dispatch_completed'])
                self.assertFalse(record['destroyed'])

    def test_observed_ok_ids_and_strict_unique_owned_selection(self):
        class User:
            def __init__(self, identifier):
                self.identifier,self.children,self.parent,self.caption = identifier,[456],123,'OK'
                self.visible,self.enabled,self.alive = True,True,True
            def IsWindow(self,h): return self.alive
            def GetParent(self,h): return 0 if h == 123 else self.parent
            def GetDlgCtrlID(self,h): return self.identifier
            def GetDlgItem(self,h,i): return 456 if i == self.identifier else 0
            def GetClassNameW(self,h,b,n): b.value='Button'; return 6
            def IsWindowEnabled(self,h): return self.enabled
            def IsWindowVisible(self,h): return self.visible
            def EnumChildWindows(self,h,callback,param):
                for c in self.children:
                    if not callback(c,0): return False
                return True
        class API:
            callback_type = staticmethod(lambda f:f)
            def __init__(self,i): self.user,self.sent,self.enumerations = User(i),[],0
            def windows(self,pid): return [(123,'#32770',True)]
            def text(self,h): return 'Ru Notepad startup error' if h == 123 else self.user.caption
            def verify_owned_handles(self,pid,*h):
                if pid != 71 or any(x not in (123,456,457) for x in h): raise ValueError('foreign PID')
            def scalar(self,*args): self.sent.append(args);return 0
        def state(): return dict(found=False,request_attempted=False,dispatch_completed=False,destroyed=False)
        with patch.object(gate,'dialog_functions',lambda api:api.user):
            for identifier in (1,2):
                api,record=API(identifier),state();gate.owned_dialog(api,71,record)
                self.assertEqual(api.sent,[(123,0x111,identifier,456)])
                self.assertEqual(record['button_control_id'],identifier)
                self.assertFalse(record['destroyed'])
                gate.owned_dialog(api,71,record);self.assertEqual(len(api.sent),1)
            for mutation in ('duplicate','other-id','cancel','ampersand','suffix','hidden','disabled',
                             'parent','foreign','lookup','change-between-selections','late-title','late-parent','late-lookup'):
                api,record=API(2),state()
                if mutation=='duplicate':
                    api.user.children=[456,457]
                    api.user.GetDlgItem=lambda h,i:456 if i==2 else 457
                    api.user.GetDlgCtrlID=lambda h:2 if h==456 else 1
                if mutation=='other-id': api.user.identifier=3
                if mutation=='cancel': api.user.caption='Cancel'
                if mutation=='ampersand': api.user.caption='&OK'
                if mutation=='suffix': api.user.caption='OK malicious'
                if mutation=='hidden': api.user.visible=False
                if mutation=='disabled': api.user.enabled=False
                if mutation=='parent': api.user.parent=789
                if mutation=='foreign': api.user.children=[999]
                if mutation=='lookup': api.user.GetDlgItem=lambda h,i:789
                if mutation in ('late-title','late-parent','late-lookup'):
                    original=api.user.EnumChildWindows
                    def late(h,callback,param):
                        api.enumerations+=1
                        result=original(h,callback,param)
                        if api.enumerations==2:
                            if mutation=='late-title': api.text=lambda h:'Other' if h==123 else 'OK'
                            if mutation=='late-parent': api.user.GetParent=lambda h:789 if h==123 else 123
                            if mutation=='late-lookup': api.user.GetDlgItem=lambda h,i:789
                        return result
                    api.user.EnumChildWindows=late
                if mutation=='change-between-selections':
                    original=api.user.EnumChildWindows
                    def changing(h,callback,param):
                        api.enumerations+=1
                        if api.enumerations==2: api.user.caption='Cancel'
                        return original(h,callback,param)
                    api.user.EnumChildWindows=changing
                with self.assertRaises(ValueError,msg=mutation): gate.owned_dialog(api,71,record)
                self.assertEqual(api.sent,[],mutation)
                self.assertFalse(record['request_attempted'],mutation)

    def test_structured_deadline_first_error_and_cleanup_evidence(self):
        class Process:
            pid=71
            returncode=None
            def poll(self): return self.returncode
            def kill(self): self.returncode=-9
            def wait(self,timeout): return self.returncode
        class Timer:
            def __init__(self,seconds,callback): self.callback=callback
            def start(self):
                if mode=='watchdog': self.callback()
            def cancel(self): pass
            def join(self):
                if mode=='join-error': raise RuntimeError('join failed')
            def is_alive(self): return False
        class API:
            def no_dialog(self,pid):
                if mode in ('prior-error','join-error','kill-error','wait-error','windows-error'):
                    raise ValueError('unknown runtime failure')
                return []
            def windows(self,pid):
                if mode=='windows-error': raise RuntimeError('enumeration failed')
                return []
        class Handshake:
            name='owned'
            def close(self): return mode!='close-error'
        for mode in ('poll','watchdog','prior-error','join-error','kill-error','wait-error','windows-error','close-error'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as temporary:
                process=Process()
                def fail(*args,**kw): raise RuntimeError('cleanup failed')
                if mode=='kill-error': process.kill=fail
                if mode=='wait-error': process.wait=fail
                ticks=[0,0,61,61.1,62] if mode in ('poll','close-error') else [0,0,60,60.1,62] if mode=='watchdog' else [0,0,1,1.1,62]
                with patch.object(gate.subprocess,'Popen',return_value=process), \
                     patch.object(gate.threading,'Timer',Timer),patch.object(gate.time,'sleep'), \
                     patch.object(gate.time,'monotonic',side_effect=clock_ticks(ticks)), \
                     patch.object(gate,'ProbeHandshake',Handshake):
                    row=gate.run_child(API(),Path(temporary)/'app.exe',[],required_dlls=('x',) if mode=='close-error' else ())
                obs=row['observation']; cleanup=obs['cleanup']
                self.assertFalse(row['passed'])
                self.assertEqual(obs['schema'],'ru-notepad-child-observation-v2')
                self.assertEqual(cleanup['pid'],71)
                self.assertTrue(obs['deadline_events'])
                expected='deadline' if mode in ('poll','watchdog','close-error') else 'exception'
                self.assertEqual(obs['first_error']['code'],expected)
                if expected=='exception':
                    self.assertEqual(obs['first_error']['message'],'unknown runtime failure')
                    self.assertEqual(row['error'],'unknown runtime failure')
                if mode in ('poll','watchdog'):
                    self.assertEqual(obs['nondeadline_errors'],[])
                    self.assertEqual(cleanup,dict(pid=71,errors=[],process_reaped=True,exit_code=-9,
                        windows_remaining=[],handshake_closed=True,watchdog_stopped=True))
                else:
                    if mode!='prior-error': self.assertTrue(cleanup['errors'])
                if mode=='windows-error': self.assertIsNone(cleanup['windows_remaining'])
                if mode=='close-error': self.assertFalse(cleanup['handshake_closed'])

    def test_watchdog_and_unknown_error_preserve_actual_first_order(self):
        class Process:
            pid=71
            returncode=None
            def poll(self): return self.returncode
            def kill(self): self.returncode=-9
            def wait(self,timeout): return self.returncode
        class Timer:
            current=None
            def __init__(self,seconds,callback): self.callback=callback;Timer.current=self
            def start(self): pass
            def cancel(self):
                if order=='unknown-first': self.callback()
            def join(self): pass
            def is_alive(self): return False
        class API:
            def no_dialog(self,pid):
                if order=='watchdog-first': Timer.current.callback()
                raise ValueError('independent runtime error')
            def windows(self,pid): return []
        for order in ('watchdog-first','unknown-first'):
            ticks=[0,0,1,60,60.1,62] if order=='watchdog-first' else [0,0,1,1.1,60,62]
            with tempfile.TemporaryDirectory() as temporary, \
                 patch.object(gate.subprocess,'Popen',return_value=Process()), \
                 patch.object(gate.threading,'Timer',Timer), \
                 patch.object(gate.time,'monotonic',side_effect=clock_ticks(ticks)):
                row=gate.run_child(API(),Path(temporary)/'app.exe',[])
            first=row['observation']['first_error']
            self.assertEqual(first['code'],'deadline' if order=='watchdog-first' else 'exception')
            if order=='unknown-first': self.assertEqual(first['message'],'independent runtime error')
            self.assertFalse(row['passed'])
            self.assertTrue(row['observation']['cleanup']['process_reaped'])
            self.assertTrue(any(e['message']=='independent runtime error'
                for e in row['observation']['nondeadline_errors']))

    def test_absolute_watchdog_waits_original_deadline_and_cancels_early_wake(self):
        import math
        deadline=64.002
        class Cancel:
            def __init__(self,cancel=False): self.cancel,self.stopped,self.waits=cancel,False,[]
            def is_set(self): return self.stopped
            def wait(self,seconds):
                self.waits.append(seconds)
                if self.cancel: self.stopped=True
        early=math.nextafter(deadline,float('-inf'))
        stop=Cancel()
        with patch.object(gate.time,'monotonic',side_effect=[early,deadline]):
            self.assertEqual(gate.await_owned_deadline(deadline,stop),deadline)
        self.assertEqual(stop.waits,[deadline-early])
        self.assertGreater(stop.waits[0],0)
        stop=Cancel(True)
        with patch.object(gate.time,'monotonic',return_value=early):
            self.assertIsNone(gate.await_owned_deadline(deadline,stop))
        self.assertEqual(stop.waits,[deadline-early])
        stop=Cancel();stop.stopped=True
        with patch.object(gate.time,'monotonic',side_effect=AssertionError('cancelled must not observe')):
            self.assertIsNone(gate.await_owned_deadline(deadline,stop))

    def test_absolute_deadline_evidence_retains_exact_float_subtraction(self):
        started=4.002;deadline=started+60
        self.assertLess(deadline-started,60)  # Actual binary floating-point boundary.
        class Process:
            pid=71
            returncode=None
            def poll(self): return self.returncode
            def kill(self): self.returncode=-9
            def wait(self,timeout): return self.returncode
        class Timer:
            def __init__(self,seconds,callback): self.callback=callback
            def start(self): self.callback()
            def cancel(self): pass
            def join(self): pass
            def is_alive(self): return False
        class API:
            def windows(self,pid): return []
        with tempfile.TemporaryDirectory() as temporary, \
             patch.object(gate.subprocess,'Popen',return_value=Process()), \
             patch.object(gate.threading,'Timer',Timer), \
             patch.object(gate.time,'monotonic',side_effect=clock_ticks([started,started,deadline,deadline,deadline,deadline,deadline])):
            row=gate.run_child(API(),Path(temporary)/'app.exe',[])
        obs=row['observation'];event=obs['deadline_events'][0]
        self.assertEqual(obs['schema'],'ru-notepad-child-observation-v2')
        self.assertEqual(obs['clock'],dict(started_monotonic=started,deadline_monotonic=deadline,
            finished_monotonic=deadline,budget_seconds=60))
        self.assertEqual(event['observed_monotonic'],deadline)
        self.assertEqual(event['elapsed_seconds'],deadline-started)
        self.assertLess(event['elapsed_seconds'],60)
        self.assertEqual(row['seconds'],deadline-started)
        self.assertEqual(obs['first_error']['observed_monotonic'],deadline)
        self.assertEqual(obs['nondeadline_errors'],[])
        self.assertFalse(row['passed'])

    def test_probe_projects_each_outcome_before_pointer_or_scalar_use(self):
        source = (ROOT/'tests/bootstrap_pipeline/dll_abi_probe.ru').read_text(encoding='utf-8')
        for expression in ('(开事件 其 调用 [1048576,0,名]) 其 值',
                           '(等事件 其 调用 [事,50000]) 其 值',
                           '(关事件 其 调用 [事]) 其 值'):
            self.assertIn(expression, source)
        self.assertLess(source.index('名 其 关闭'), source.index('若 事 其 为空'))
        self.assertIn('(等 其 数) != 0 或 (关 其 数) == 0', source)
        # Models only the documented Win32 result truth table, not runtime execution.
        for wait, close, accepted in [(0,1,True), (258,1,False), (0xffffffff,1,False), (0,0,False)]:
            self.assertEqual(wait == 0 and close != 0, accepted)

    def test_invalid_utf16_requires_destroyed_natural_exit_and_no_side_effect(self):
        class Process:
            pid = 81
            returncode = None
            killed = False
            def poll(self): return self.returncode
            def kill(self): self.killed = True; self.returncode = -9
            def wait(self, timeout): return self.returncode
        class API:
            callback_type = staticmethod(lambda callback: callback)
            def windows(self, pid): return []
        class User:
            def __init__(self, alive): self.alive = alive
            def IsWindow(self, hwnd): return self.alive
        for mode in ('good', 'not_destroyed', 'not_dispatched', 'zero_exit', 'side_effect'):
            process = Process()
            with tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                def dialog(api, pid, state):
                    state.update(found=True, hwnd=123, request_attempted=True,
                                 dispatch_completed=mode != 'not_dispatched')
                    process.returncode = 0 if mode == 'zero_exit' else 1
                    if mode == 'side_effect': (directory/'ru_notepad-owned.log').write_bytes(b'entered Ru')
                with patch.object(gate.subprocess, 'Popen', return_value=process), \
                        patch.object(gate, 'owned_dialog', dialog), \
                        patch.object(gate, 'dialog_functions', return_value=User(mode == 'not_destroyed')), \
                        patch.object(gate.time, 'sleep'):
                    result = gate.run_child(API(), directory/'app.exe', [], invalid=True)
            self.assertEqual(result['passed'], mode == 'good', mode)
            self.assertFalse(result['cleanup_killed'])
            self.assertNotIn('owned_startup_dialog_dismissed', result)
            self.assertTrue(result['owned_startup_dialog']['process_exited'])

    def test_owned_diagnostic_is_bounded_and_never_queries_foreign_pid(self):
        class User:
            def __init__(self):
                self.children = [456,789]
                self.foreign = set()
                self.calls = []
            def GetWindowThreadProcessId(self, h, owner): owner._obj.value = 99 if h in self.foreign else 71; return 1
            def GetClassNameW(self, h, name, count): name.value = '#32770' if h == 123 else 'Button'; return len(name.value)
            def GetDlgCtrlID(self,h): return 0 if h == 123 else 1
            def GetDlgItem(self,h,i): return 0
            def EnumChildWindows(self,h,callback,param): return True
            def GetParent(self,h): return 0 if h == 123 else 123
            def IsChild(self,parent,h): return parent == 123 and h in self.children
            def IsWindowVisible(self,h): return True
            def IsWindowEnabled(self,h): return True
            def SendMessageTimeoutW(self,h,msg,count,address,flags,timeout,copied):
                self.calls.append((h,msg,count,timeout))
                buffer = gate.ctypes.create_unicode_buffer('owned title' if h == 123 else 'OK')
                gate.ctypes.memmove(address, buffer, gate.ctypes.sizeof(buffer))
                copied._obj.value = len(buffer.value)
                return 1
            def EnumChildWindows(self,h,callback,param):
                for child in self.children:
                    if not callback(child,param): return 0
                return 1
        class API:
            callback_type = staticmethod(lambda callback: callback)
            def __init__(self): self.user = User()
        with patch.object(gate, 'dialog_functions', lambda api: api.user):
            api = API(); result = gate.owned_dialog_diagnostic(api,71,123,lambda:True)
            self.assertEqual(len(result['children']),2)
            self.assertEqual(result['getdlgitem_idok_now'],0)
            self.assertEqual(result['dialog']['text'],'owned title')
            self.assertTrue(all(msg == 0xD and count == 257 and timeout == 100 for _,msg,count,timeout in api.user.calls))
            api = API(); api.user.foreign.add(789)
            result = gate.owned_dialog_diagnostic(api,71,123,lambda:True)
            self.assertIn('no longer owned',result['error'])
            self.assertFalse(any(h == 789 for h,*_ in api.user.calls))
            api = API(); api.user.children = list(range(1000,1100))
            result = gate.owned_dialog_diagnostic(api,71,123,lambda:True)
            self.assertEqual(len(result['children']),32)
            self.assertTrue(result['truncated'])
            api = API(); result = gate.owned_dialog_diagnostic(api,71,123,lambda:False)
            self.assertIn('process exited',result['error'])
            self.assertEqual(api.user.calls,[])

    def test_missing_control_captures_once_before_cleanup_without_granting_pass(self):
        state = dict(found=True, hwnd=123, idok_lookup_result=0, request_attempted=False)
        calls=[]
        def observe(api,pid,hwnd,alive):
            self.assertTrue(alive());calls.append((pid,hwnd))
            return {'children':[{'hwnd':456,'control_id':2}], 'process_alive_after':True}
        with patch.object(gate,'owned_dialog_diagnostic',observe):
            for elapsed in (0.1,0.2,1.0,1.11,5.0,59.9):
                gate.capture_missing_control(object(),71,state,lambda:True,elapsed)
        self.assertEqual(calls,[(71,123)])
        snapshot=state['early_control_diagnostic']
        self.assertEqual(snapshot['observed_elapsed_seconds'],1.11)
        self.assertEqual(snapshot['trigger'],'owned-IDOK-still-null-after-1s')
        self.assertFalse(state['request_attempted'])
        self.assertNotIn('passed',state)
        state['failure_diagnostic']={'error':'HWND no longer owned','children':[]}
        self.assertEqual(snapshot['snapshot']['children'][0]['control_id'],2)
        with patch.object(gate,'owned_dialog_diagnostic',side_effect=AssertionError('must not observe')):
            for changes in ({'found':False},{'request_attempted':True},{'idok_lookup_result':456}):
                gate.capture_missing_control(object(),71,{**state,**changes},lambda:True,20)
            gate.capture_missing_control(object(),71,state,lambda:False,20)
        # Ownership/collection errors are evidence of failure, never a pass.
        for error in ('PID changed','child reparented','text unavailable'):
            failed=dict(found=True,hwnd=123,idok_lookup_result=0,request_attempted=False,control_missing_since=0)
            with patch.object(gate,'owned_dialog_diagnostic',return_value={'error':error,'children':[]}):
                gate.capture_missing_control(object(),71,failed,lambda:True,2)
            self.assertEqual(failed['early_control_diagnostic']['snapshot']['error'],error)
            self.assertFalse(failed['request_attempted'])
            self.assertNotIn('passed',failed)

    def test_missing_idok_waits_without_claiming_dispatch(self):
        class User:
            def GetDlgItem(self,h,i): return 0
            def EnumChildWindows(self,h,callback,param): return True
            def GetParent(self,h): return 0
        class API:
            callback_type = staticmethod(lambda callback: callback)
            user = User()
            def windows(self,pid): return [(123,'#32770',True)]
            def verify_owned_handles(self,pid,*handles): pass
            def text(self,h): return 'Ru Notepad startup error'
        record = dict(found=False, request_attempted=False, dispatch_completed=False, destroyed=False)
        with patch.object(gate,'dialog_functions',lambda api:api.user):
            gate.owned_dialog(API(),71,record)
        self.assertEqual(record['control_wait_polls'],1)
        self.assertTrue(record['found'])
        self.assertEqual(record['hwnd'],123)
        self.assertEqual(record['idok_lookup_result'],0)
        self.assertFalse(record['request_attempted'])
        self.assertFalse(record['dispatch_completed'])

    def test_delayed_idok_and_early_exit_keep_real_lifecycle_contract(self):
        class Process:
            pid = 71
            returncode = None
            def poll(self): return self.returncode
            def kill(self): self.returncode = -9
            def wait(self, timeout): return self.returncode
        class Timer:
            def __init__(self, seconds, callback): pass
            def start(self): pass
            def cancel(self): pass
            def join(self): pass
            def is_alive(self): return False
        class User:
            def __init__(self, process, mode): self.process,self.mode,self.lookups = process,mode,0
            def IsWindow(self, hwnd): return self.process.poll() is None
            def GetParent(self, hwnd): return 123 if hwnd == 456 else 0
            def GetDlgCtrlID(self, hwnd): return 1
            def GetClassNameW(self, hwnd, buffer, count): buffer.value = 'Button'; return 6
            def IsWindowEnabled(self, hwnd): return True
            def IsWindowVisible(self, hwnd): return True
            def EnumChildWindows(self, hwnd, callback, param):
                self.lookups += 1
                if self.mode == 'early': self.process.returncode = 1
                if self.mode == 'ready' and self.lookups > 1: callback(456,0)
                return True
            def GetDlgItem(self, hwnd, identifier):
                return 456 if self.mode == 'ready' and self.lookups > 1 else 0
        class API:
            callback_type = staticmethod(lambda callback: callback)
            def __init__(self, process, mode): self.user,self.process,self.sent = User(process,mode),process,[]
            def windows(self, pid): return [(123,'#32770',True)] if self.process.poll() is None else []
            def verify_owned_handles(self, pid, *handles):
                if pid != 71 or any(h not in (123,456) for h in handles): raise ValueError('not owned')
            def text(self, hwnd): return 'Ru Notepad startup error' if hwnd == 123 else 'OK'
            def scalar(self, *args): self.sent.append(args); self.process.returncode = 1; return 0
        for mode in ('ready','early','missing'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as temporary:
                process = Process(); api = API(process,mode)
                ticks = [0,0,1,2,3] if mode == 'ready' else [0,0,1,1.1,2] if mode == 'early' else [0,0,1,2.1,61,61.1,62]
                with patch.object(gate,'dialog_functions',lambda api:api.user), \
                     patch.object(gate.subprocess,'Popen',return_value=process), \
                     patch.object(gate.threading,'Timer',Timer),patch.object(gate.time,'sleep'), \
                     patch.object(gate.time,'monotonic',side_effect=clock_ticks(ticks)):
                    result = gate.run_child(api,Path(temporary)/'app.exe',[],invalid=True)
                self.assertEqual(result['passed'],mode == 'ready',result)
                self.assertEqual(result['cleanup_killed'],mode == 'missing')
                self.assertEqual(api.sent,[(123,0x111,1,456)] if mode == 'ready' else [])
                if mode == 'ready':
                    self.assertEqual(result['owned_startup_dialog']['control_wait_polls'],1)
                    self.assertTrue(result['owned_startup_dialog']['destroyed'])
                if mode == 'missing':
                    self.assertIn('60s',result['error'])
                    self.assertIn('early_control_diagnostic',result['owned_startup_dialog'])
                    self.assertIn('failure_diagnostic',result['owned_startup_dialog'])
                if mode == 'early':
                    self.assertNotIn('early_control_diagnostic',result['owned_startup_dialog'])

    def test_waiting_dialog_identity_changes_never_dispatch(self):
        class User:
            def GetDlgItem(self,h,i): return 0
            def EnumChildWindows(self,h,callback,param): return True
            def GetParent(self,h): return 0
            def IsWindow(self,h): return True
        class API:
            callback_type = staticmethod(lambda callback: callback)
            def __init__(self): self.user,self.sent = User(),[]
            def windows(self,pid): return [(123,'#32770',True)]
            def verify_owned_handles(self,pid,*handles): pass
            def text(self,h): return 'Ru Notepad startup error'
            def scalar(self,*args): self.sent.append(args)
        for mutation in ('pid','title','parent','other_dialog','hidden'):
            api=API(); state=dict(found=False,request_attempted=False,dispatch_completed=False,destroyed=False)
            with patch.object(gate,'dialog_functions',lambda api:api.user):
                gate.owned_dialog(api,71,state)
                def fail(*args): raise ValueError('PID ownership changed')
                if mutation == 'pid': api.verify_owned_handles=fail
                if mutation == 'title': api.text=lambda h:'Other'
                if mutation == 'parent': api.user.GetParent=lambda h:99
                if mutation == 'other_dialog': api.windows=lambda pid:[(789,'#32770',True)]
                if mutation == 'hidden': api.windows=lambda pid:[(123,'#32770',False)]
                with self.assertRaises(ValueError,msg=mutation): gate.owned_dialog(api,71,state)
                self.assertFalse(state['request_attempted'])
                self.assertEqual(api.sent,[])

    def test_timeout_kills_only_owned_child_and_cannot_pass(self):
        class Process:
            pid = 77
            killed = False
            def poll(self): return -9 if self.killed else None
            def kill(self): self.killed = True
            def wait(self, timeout): return -9
        class API:
            callback_type = staticmethod(lambda callback: callback)
            def no_dialog(self, pid): return []
        process = Process()
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(gate.subprocess, 'Popen', return_value=process), patch.object(gate.time, 'monotonic', side_effect=clock_ticks([0, 0, 61, 61.1, 62])):
                result = gate.run_child(API(), Path(temporary)/'app.exe', [])
        self.assertTrue(process.killed)
        self.assertTrue(result['executed'])
        self.assertTrue(result['cleanup_killed'])
        self.assertFalse(result['passed'])
        self.assertIn('functional', result['error'])

    def test_independent_watchdog_expiration_cannot_pass(self):
        class Process:
            pid = 78
            returncode = None
            def poll(self): return self.returncode
            def kill(self): self.returncode = -9
            def wait(self, timeout): return self.returncode
        class Timer:
            def __init__(self, seconds, callback): self.callback = callback
            def start(self): self.callback()
            def cancel(self): pass
            def join(self): pass
            def is_alive(self): return False
        class API:
            callback_type = staticmethod(lambda callback: callback)
            def windows(self, pid): return []
        process = Process()
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(gate.subprocess, 'Popen', return_value=process), patch.object(gate.threading, 'Timer', Timer), patch.object(gate.time,'monotonic',side_effect=clock_ticks([0,0,60,60,61,62])):
                result = gate.run_child(API(), Path(temporary)/'app.exe', [])
        self.assertEqual(process.returncode, -9)
        self.assertFalse(result['passed'])
        self.assertTrue(result['cleanup_killed'])
        self.assertIn('watchdog', result['error'])

    def test_watchdog_interrupts_blocked_gui_observation(self):
        class Process:
            pid = 79
            returncode = None
            killed = gate.threading.Event()
            def poll(self): return self.returncode
            def kill(self): self.returncode = -9; self.killed.set()
            def wait(self, timeout): return self.returncode
        process = Process()
        test = self
        class API:
            callback_type = staticmethod(lambda callback: callback)
            def no_dialog(self, pid):
                # A GUI observation cannot starve the independent process cap.
                test.assertTrue(process.killed.wait(timeout=1))
                return []
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(gate.subprocess, 'Popen', return_value=process), patch.object(gate, 'DEADLINE_SECONDS', 0.02):
                result = gate.run_child(API(), Path(temporary)/'app.exe', [])
        self.assertTrue(process.killed.is_set())
        self.assertTrue(result['cleanup_killed'])
        self.assertFalse(result['passed'])

    def test_wrong_dll_path_never_acknowledged_and_event_closed(self):
        class Process:
            pid = 80
            returncode = None
            def poll(self): return self.returncode
            def kill(self): self.returncode = -9
            def wait(self, timeout): return self.returncode
        class Handshake:
            name = 'owned-event'
            signaled = False
            closed = False
            def signal(self): self.signaled = True
            def close(self): self.closed = True
        process, event = Process(), Handshake()
        with tempfile.TemporaryDirectory() as temporary:
            bad = {'Scintilla.dll': {'path': str(Path(temporary)/'outside'/'Scintilla.dll')}}
            with patch.object(gate.subprocess, 'Popen', return_value=process), patch.object(gate, 'ProbeHandshake', return_value=event), patch.object(gate, 'loaded_dlls', return_value=bad):
                result = gate.run_child(object(), Path(temporary)/'app.exe', ['editor'], required_dlls=gate.DLLS)
        self.assertFalse(event.signaled)
        self.assertTrue(event.closed)
        self.assertEqual(process.returncode, -9)
        self.assertFalse(result['passed'])
        self.assertIn('outside owned snapshot', result['error'])

    def test_dll_probe_reuses_existing_native_pointer_callback_suites(self):
        source = (ROOT/'tests/bootstrap_pipeline/dll_abi_probe.ru').read_text(encoding='utf-8')
        for name in ('editor_native.ru', 'ru_syntax_native.ru', 'markdown_native.ru'):
            self.assertIn("'../"+name+"'", source)
        self.assertIn('BOOTSTRAP_DLL_ABI_PASS:', source)
        self.assertEqual(source.count('其 元初 []'), 3)


class ResourceDiagnosticTests(unittest.TestCase):
    def fixture(self, planes=1, payload=None):
        if payload is None:
            ihdr=b'IHDR'+gate.struct.pack('>IIBBBBB',16,16,8,6,0,0,0)
            payload=b'\x89PNG\r\n\x1a\n'+gate.struct.pack('>I',13)+ihdr+gate.struct.pack('>I',gate.zlib.crc32(ihdr))
            compressed=gate.zlib.compress(bytes(16*(1+16*4)))
            for kind,data in [(b'IDAT',compressed),(b'IEND',b'')]:
                payload+=gate.struct.pack('>I',len(data))+kind+data+gate.struct.pack('>I',gate.zlib.crc32(kind+data))
        header=gate.struct.pack('<HHH',0,1,1)
        icon=header+gate.struct.pack('<BBBBHHII',16,16,0,0,0,32,len(payload),22)+payload
        group=header+gate.struct.pack('<BBBBHHIH',16,16,0,0,planes,32,len(payload),7)
        return icon,group,payload

    def test_plane_difference_is_described_not_normalized(self):
        icon,group,payload=self.fixture()
        calls=[]
        def image(number): calls.append(number);return payload
        languages=lambda kind,name:{'available_langids':[1033],'selected_langid':1033}
        result=gate.icon_resource_diagnostic(icon,group,image,languages)
        entry=result['entries'][0]
        self.assertEqual(entry['source']['planes'],0)
        self.assertEqual(entry['group']['planes'],1)
        self.assertEqual(entry['source']['payload_sha256'],entry['group']['payload_sha256'])
        self.assertEqual(entry['group']['resource_id'],7)
        self.assertEqual(entry['group']['languages']['selected_langid'],1033)
        self.assertEqual(calls,[7])
        self.assertNotEqual(group[6:18],icon[6:18])  # Existing strict gate still rejects.
        self.assertNotIn('passed',result)
        self.assertEqual(entry['group']['raw_hex'],group[6:].hex())

    def test_missing_images_and_unknown_language_are_explicit(self):
        icon,group,payload=self.fixture()
        def missing(number): raise ValueError('missing image')
        result=gate.icon_resource_diagnostic(icon,group,missing,lambda *args:{'available_langids':None,'selected_langid':None,'unknown_reason':'not available'})
        self.assertEqual(result['entries'][0]['group']['payload_error'],'missing image')
        self.assertIsNone(result['group_languages']['selected_langid'])
        changed=gate.icon_resource_diagnostic(icon,group,lambda _:b'other',lambda *args:{})
        self.assertNotEqual(changed['entries'][0]['source']['payload_sha256'],changed['entries'][0]['group']['payload_sha256'])

    def test_bounds_truncation_and_outside_source_offsets(self):
        icon,group,payload=self.fixture()
        self.assertIn('description_error',gate.icon_resource_diagnostic(b'',group,lambda _:payload,lambda *args:{}))
        for data in (b'x'*(1024*1024+1),gate.struct.pack('<HHH',0,1,65)):
            with self.assertRaises(ValueError): gate.icon_resource_diagnostic(data,group,lambda _:payload,lambda *args:{})
        bad=bytearray(icon);gate.struct.pack_into('<I',bad,18,2**32-1)
        result=gate.icon_resource_diagnostic(bytes(bad),group,lambda _:payload,lambda *args:{})
        self.assertEqual(result['entries'][0]['source']['payload_error'],'outside source ICO')

    def test_snapshot_identity_change_is_not_a_new_baseline(self):
        with tempfile.TemporaryDirectory() as temp:
            pe,icon=Path(temp)/'app.exe',Path(temp)/'app.ico'
            pe.write_bytes(b'pe');icon.write_bytes(b'ico')
            diagnostic={'pe':gate.identity(pe),'source_ico':gate.identity(icon)}
            gate.resource_snapshot_stable(diagnostic,pe,icon)
            self.assertTrue(diagnostic['identity_stable'])
            pe.write_bytes(b'changed')
            with self.assertRaises(ValueError):gate.resource_snapshot_stable(diagnostic,pe,icon)
            self.assertFalse(diagnostic['identity_stable'])
            self.assertNotEqual(diagnostic['pe'],diagnostic['pe_after'])

    def test_mock_mapping_retains_exact_gate_and_single_read_snapshot(self):
        # Portable API model, NOT a real Windows resource/runtime result.
        class Function:
            def __init__(self,function):self.function=function
            def __call__(self,*args):return self.function(*args)
        class Kernel:pass
        for planes,changed_image,mutate in [(1,False,False),(0,False,False),(1,True,False),(1,False,True)]:
            with self.subTest(planes=planes,changed_image=changed_image,mutate=mutate),tempfile.TemporaryDirectory() as temp:
                app=Path(temp);(app/'assets').mkdir();(app/'packaging').mkdir()
                pe=app/'app.exe';pe.write_bytes(b'owned PE bytes')
                icon,group,payload=self.fixture(planes)
                (app/'assets/app-icon.ico').write_bytes(icon)
                (app/'packaging/app.manifest').write_bytes(b'manifest')
                version=gate.struct.pack('<13I',0xFEEF04BD,0x10000,1,8<<16,1,8<<16,0x3f,2,0x40004,1,0,0,0)
                version+=' '.join(('FileDescription','ru_notepad preview','FileVersion','0.1.8-preview','InternalName','OriginalFilename','ru_notepad.exe','ProductName','ProductVersion','040904B0')).encode('utf-16-le')
                resources={(14,1):group,(3,7):b'wrong' if changed_image else payload,(24,1):b'manifest',(16,1):version}
                reads={};kernel=Kernel()
                def read(pointer,size):
                    reads[pointer]=reads.get(pointer,0)+1
                    if mutate:pe.write_bytes(b'replaced PE')
                    return resources[pointer]
                methods={'LoadLibraryExW':lambda *args:1,'FindResourceW':lambda module,name,kind:(kind,name),
                         'SizeofResource':lambda module,found:len(resources[found]),'LoadResource':lambda module,found:found,
                         'LockResource':lambda found:found,'FreeLibrary':lambda module:True,
                         'EnumResourceLanguagesW':lambda module,kind,name,callback,param:callback(module,kind,name,1033,param)}
                for name,function in methods.items():setattr(kernel,name,Function(function))
                with patch.object(gate,'verify_gui_pe'),patch.object(gate.ctypes,'WinDLL',return_value=kernel,create=True), \
                     patch.object(gate.ctypes,'WINFUNCTYPE',gate.ctypes.CFUNCTYPE,create=True),patch.object(gate.ctypes,'string_at',side_effect=read):
                    if planes==1 and not changed_image and not mutate:
                        result=gate.verify_resources(pe,app)
                        self.assertTrue(result['passed'])
                        diagnostic=result['resource_diagnostics']
                    else:
                        with self.assertRaises(gate.ResourceEvidenceError) as caught:gate.verify_resources(pe,app)
                        diagnostic=caught.exception.diagnostic
                        expected='metadata differs' if planes!=1 else 'image differs' if changed_image else 'identity changed'
                        self.assertIn(expected,str(caught.exception))
                    self.assertEqual(diagnostic['icon']['group_languages']['selected_langid'],1033)
                    self.assertTrue(all(value==1 for value in reads.values()))
                    self.assertEqual(diagnostic['identity_stable'],not mutate)

    def test_only_observed_png_planes_transition_is_allowed(self):
        icon,group,payload=self.fixture()
        source=bytearray(icon[6:22]);actual=bytearray(group[6:20])
        for source_plane in (0,1):
            gate.struct.pack_into('<H',source,4,source_plane)
            gate.verify_png_icon_entry(bytes(source),bytes(actual),payload,payload)
        for source_plane,output_plane in [(2,1),(65535,1),(0,0),(1,0),(0,2),(1,2)]:
            gate.struct.pack_into('<H',source,4,source_plane);gate.struct.pack_into('<H',actual,4,output_plane)
            with self.assertRaises(ValueError):gate.verify_png_icon_entry(bytes(source),bytes(actual),payload,payload)
        source,actual=icon[6:22],group[6:20]
        for index in [0,1,2,3,6,7,8,9,10,11]:
            changed=bytearray(actual);changed[index]^=1
            with self.assertRaises(ValueError):gate.verify_png_icon_entry(source,bytes(changed),payload,payload)
        for changed in [payload+b'x',payload[:-1],payload[:-1]+bytes([payload[-1]^1])]:
            with self.assertRaises(ValueError):gate.verify_png_icon_entry(source,actual,payload,changed)
        for changed in [b'BM'+payload[2:],payload[:32],payload[:24]+b'\x10'+payload[25:],payload[:29]+b'bad!'+payload[33:]]:
            with self.assertRaises(ValueError):gate.verify_png_icon_entry(source,actual,changed,changed)

    def test_members_and_languages_are_not_relaxed(self):
        known={'available_langids':[1033],'selected_langid':1033}
        diagnostic={'group_languages':known,'entries':[{'group':{'languages':known}}]}
        gate.verify_icon_languages_and_members(diagnostic,[1])
        for ids in [[1,1],[1,2],[],[0],[-1]]:
            with self.assertRaises(ValueError):gate.verify_icon_languages_and_members(diagnostic,ids)
        for wrong in [{'available_langids':None,'selected_langid':None},{'available_langids':[2052],'selected_langid':2052},{'available_langids':[1033,2052],'selected_langid':1033}]:
            for where in ('group','image'):
                bad={'group_languages':wrong if where=='group' else known,'entries':[{'group':{'languages':wrong if where=='image' else known}}]}
                with self.assertRaises(ValueError):gate.verify_icon_languages_and_members(bad,[1])

    def test_failure_persists_diagnostics_but_never_grants_acceptance(self):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/'gui-acceptance.json'
            diagnostic={'scope':'diagnostic-only-not-runtime-acceptance','unicode':'汉😀','identity_stable':True}
            with patch.object(gate.sys,'argv',['gate','--config',str(Path(temp)/'config.json'),'--output',str(output)]), \
                    patch.object(gate,'read_json',return_value={}), \
                    patch.object(gate,'verify',side_effect=gate.ResourceEvidenceError('icon metadata differs',diagnostic)):
                self.assertEqual(gate.main(),1)
            result=json.loads(output.read_bytes())
            self.assertEqual(result['status'],'failed')
            self.assertFalse(result['release_permission'])
            self.assertEqual(result['resource_diagnostics'],diagnostic)
            self.assertNotIn('results',result)


if __name__ == '__main__':
    unittest.main()
