"""Portable seam controls, not actual Windows measurements."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent))
import diagnose_markdown_open_windows as subject
import diagnose_instance_modal_windows as identity
import gui_instance_tabs as instance


class Api:
    def __init__(self):
        self.posts = []
        self.original_calls = []
        self.foreign = False
    def no_dialog(self, pid):
        self.original_calls.append(pid)
        return ['windows']
    def verify_owned_handles(self, pid, hwnd):
        if self.foreign: raise RuntimeError('foreign owner')
    def post_ru_snapshot(self, hwnd): self.posts.append(hwnd)
    def editor(self, hwnd): return 9
    def drop(self, hwnd, paths): pass


class DiagnosticTests(unittest.TestCase):
    def setup_probe(self):
        api = Api(); now = [0.0]; dead = [False]
        process = SimpleNamespace(pid=7, poll=lambda: 0 if dead[0] else None)
        record = {}; probe = subject.SchedulerProbe(api, process, 8, record, lambda: now[0]); probe.started = 0
        return api, now, dead, record, probe

    def test_three_total_posts_and_no_deadline_catchup(self):
        api, now, dead, record, probe = self.setup_probe()
        with probe.installed():
            for n in (0, .5, .6, 15, 15.1, 29, 29.1, 30, 31):
                now[0] = n; self.assertEqual(api.no_dialog(7), ['windows'])
        self.assertEqual(api.posts, [8, 8, 8]); self.assertEqual(len(record['requests']), 3)
        self.assertNotIn('no_dialog', api.__dict__)
        api, now, dead, record, probe = self.setup_probe()
        now[0] = 30.001; probe.no_dialog(7); self.assertEqual(api.posts, [])

    def test_missed_slots_never_burst_or_wait(self):
        api, now, dead, record, probe = self.setup_probe()
        now[0] = 29.5; probe.no_dialog(7)
        self.assertEqual(api.posts, [8]); self.assertEqual([x['sent'] for x in record['requests']], [False, False, True])
        self.assertEqual(record['requests'][-1]['elapsed_ms'], 29500)

    def test_original_modal_exception_restores_method(self):
        api, now, dead, record, probe = self.setup_probe()
        def reject(pid): raise RuntimeError('modal')
        api.no_dialog = reject
        probe = subject.SchedulerProbe(api, SimpleNamespace(pid=7, poll=lambda: None), 8, {}, lambda: 1)
        probe.started = 0
        with self.assertRaisesRegex(RuntimeError, 'modal'):
            with probe.installed(): api.no_dialog(7)
        self.assertIs(api.no_dialog, reject); self.assertEqual(api.posts, [])

    def test_foreign_pid_dead_process_or_foreign_window_cannot_post(self):
        api, now, dead, record, probe = self.setup_probe(); now[0] = 1
        probe.no_dialog(99); self.assertEqual(api.posts, [])
        dead[0] = True; probe.no_dialog(7); self.assertEqual(api.posts, [])
        dead[0] = False; api.foreign = True
        with self.assertRaisesRegex(RuntimeError, 'foreign'): probe.no_dialog(7)
        self.assertEqual(api.posts, []); self.assertFalse(record['requests'][0]['sent'])

    def test_post_failure_restores_and_records_unsent(self):
        api, now, dead, record, probe = self.setup_probe(); now[0] = 1
        def fail(hwnd): raise RuntimeError('post failed')
        api.post_ru_snapshot = fail
        with self.assertRaisesRegex(RuntimeError, 'post failed'):
            with probe.installed(): api.no_dialog(7)
        self.assertNotIn('no_dialog', api.__dict__); self.assertFalse(record['requests'][0]['sent'])

    def test_cpu_units_failure_and_nonmonotonic_never_fabricate_zero(self):
        start = {'available': True, 'kernel_100ns': 100000, 'user_100ns': 200000}
        end = {'available': True, 'kernel_100ns': 150000, 'user_100ns': 270000}
        self.assertEqual(subject.cpu_delta(start, end)['total_cpu_ms'], 12)
        self.assertFalse(subject.cpu_delta(end, start)['available'])
        for bad in ({'available': False}, {}):
            self.assertEqual(subject.cpu_delta(start, bad), {'available': False, 'reason': 'boundary sample unavailable'})
        for bad in (None, {'kernel_100ns': True, 'user_100ns': 0}, {'kernel_100ns': -1, 'user_100ns': 0}):
            reader = SimpleNamespace(read=lambda: bad)
            sample = subject.cpu_sample(reader)
            self.assertFalse(sample['available']); self.assertNotIn('kernel_100ns', sample)
        with patch.object(subject.sys, 'platform', 'linux'):
            with self.assertRaises(RuntimeError): subject.ProcessCpu(SimpleNamespace(_handle=123))

    def test_cpu_reads_exact_owned_handle_and_kernel_user_fields(self):
        calls=[]
        def query(handle,*pointers):
            calls.append(handle)
            for ptr,value in zip(pointers,[999,888,(1<<32)+5,(2<<32)+9]):
                cell=subject.ctypes.cast(ptr,subject.ctypes.POINTER(subject.wintypes.FILETIME)).contents
                cell.dwHighDateTime=value>>32;cell.dwLowDateTime=value&0xffffffff
            return 1
        kernel=SimpleNamespace(GetProcessTimes=query)
        with patch.object(subject.sys,'platform','win32'), patch.object(subject.ctypes,'WinDLL',return_value=kernel,create=True):
            with self.assertRaises(RuntimeError):subject.ProcessCpu(SimpleNamespace())
            reader=subject.ProcessCpu(SimpleNamespace(_handle=1234));result=reader.read()
        self.assertEqual(calls,[1234])
        self.assertEqual(result,{'kernel_100ns':(1<<32)+5,'user_100ns':(2<<32)+9})

    def test_registry_cleanup_accepts_only_absent_owned_namespace(self):
        key='Software\\ru_notepad\\SingleInstanceTests\\gui_'+'a'*32
        seen=[]
        def missing(root,path):seen.append(path);raise FileNotFoundError()
        with patch.dict(sys.modules,{'winreg':SimpleNamespace(HKEY_CURRENT_USER=1,OpenKey=missing)}):
            subject.verify_registry_removed(key)
            for invalid in ('Software\\ru_notepad',key+'0',key.replace('gui_','other_')):
                with self.assertRaises(ValueError):subject.verify_registry_removed(invalid)
        self.assertEqual(len(seen),2)
        @contextmanager
        def present(*unused):yield None
        with patch.dict(sys.modules,{'winreg':SimpleNamespace(HKEY_CURRENT_USER=1,OpenKey=present)}):
            with self.assertRaises(RuntimeError):subject.verify_registry_removed(key)

    def test_stage_original_entry_and_failure_receipt_are_preserved(self):
        for fail in (False, True):
            with self.subTest(fail=fail), tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp); runtime=root/'runtime'; runtime.mkdir(); evidence=root/'output/evidence'; evidence.mkdir(parents=True)
                hashes={}
                for n in subject.ci.portable.RUNTIME_NAMES:
                    (runtime/n).write_bytes(n.encode());hashes[n]=hashlib.sha256(n.encode()).hexdigest()
                api=Api(); process=SimpleNamespace(pid=7, _handle=123, poll=lambda: None)
                calls=[]; cpu_calls=[]
                class Cpu:
                    def __init__(self, owned): self.assert_owner=owned is process
                    def read(self):
                        cpu_calls.append(1);return {'kernel_100ns':len(cpu_calls)*10000,'user_100ns':len(cpu_calls)*20000}
                @contextmanager
                def settings(): yield 'Software\\ru_notepad\\SingleInstanceTests\\gui_'+'a'*32
                def stage(a,p,h,source,kind,operation,record,action):
                    calls.append((a,p,h,kind,operation,subject.ci.GUI_MARKDOWN_TIMEOUT_SECONDS))
                    self.assertNotIn('GH_TOKEN',os.environ); self.assertNotIn('GITHUB_TOKEN',os.environ)
                    action(); record.update(wall_ms=30001 if fail else 50, last_progress={'pending':fail})
                    if fail:raise RuntimeError('original deadline')
                def gui(a,owned,ev,**kwargs):
                    self.assertEqual(kwargs['arguments'],['--markdown-phase-diagnostics'])
                    try:kwargs['exercise'](process,8); result={'passed':True}
                    except RuntimeError as exc:result={'passed':False,'error':str(exc)}
                    (ev/'markdown-open-0.log').write_text('launcher\n')
                    return result
                with patch.object(identity,'validate_runtime'),patch.object(instance,'isolated_settings',settings), \
                     patch.object(subject,'verify_registry_removed'),patch.object(subject,'ProcessCpu',Cpu), \
                     patch.object(subject.ci,'Windows',return_value=api),patch.object(subject.ci,'run_gui',side_effect=gui), \
                     patch.object(subject.ci,'run_gui_markdown_stage',side_effect=stage), \
                     patch.dict(os.environ,{'GH_TOKEN':'private','GITHUB_TOKEN':'private'}):
                    result=subject.run(runtime,hashes,evidence)
                self.assertEqual(len(calls),1);self.assertEqual(calls[0][3:],('unclosed-fence','open',30))
                self.assertEqual(len(cpu_calls),2);self.assertEqual(result['cpu']['delta']['total_cpu_ms'],3)
                self.assertIs(result['stage_passed'],not fail);self.assertIs(result['process']['passed'],not fail)
                self.assertFalse(result['accepted']);self.assertEqual(result['status'],'NOT_ACCEPTED')
                self.assertTrue(result['registry_cleaned']);self.assertNotIn('no_dialog',api.__dict__)
                self.assertEqual(json.loads((evidence/'markdown-open/diagnostic.json').read_text()),result)

    def test_stage_has_no_additional_33671_posts_and_deadline_is_unchanged(self):
        import inspect
        source=inspect.getsource(subject.ci.run_gui_markdown_stage)
        self.assertNotIn('post_ru_snapshot',source);self.assertNotIn('33671',source)
        self.assertEqual(subject.ci.GUI_MARKDOWN_TIMEOUT_SECONDS,30)
        self.assertEqual(hashlib.sha256(subject.ci.gui_markdown_fixture('unclosed-fence')[0]).hexdigest(),subject.FENCE_SHA256)
        for check in ('styles_match','folds_match','context_match','end_styled','verify_owned_handles'):
            self.assertIn(check,source)


if __name__ == '__main__': unittest.main()
