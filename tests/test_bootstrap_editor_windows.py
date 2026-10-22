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

    def test_dialog_checks_owned_pid_and_title_before_close(self):
        class API:
            def __init__(self, title): self.title, self.events = title, []
            def windows(self, pid): self.events.append(('windows', pid)); return [(123, '#32770', True)]
            def verify_owned_handles(self, pid, hwnd): self.events.append(('owned', pid, hwnd))
            def text(self, hwnd): return self.title
            def command(self, hwnd, command): self.events.append(('command', hwnd, command))
        api = API('Ru Notepad startup error')
        self.assertTrue(gate.owned_dialog(api, 71))
        self.assertEqual(api.events, [('windows', 71), ('owned', 71, 123), ('command', 123, 1)])
        api = API('Unrelated dialog')
        with self.assertRaises(ValueError): gate.owned_dialog(api, 71)
        self.assertNotIn(('command', 123, 1), api.events)

    def test_timeout_kills_only_owned_child_and_cannot_pass(self):
        class Process:
            pid = 77
            killed = False
            def poll(self): return -9 if self.killed else None
            def kill(self): self.killed = True
            def wait(self, timeout): return -9
        class API:
            def no_dialog(self, pid): return []
        process = Process()
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(gate.subprocess, 'Popen', return_value=process), patch.object(gate.time, 'monotonic', side_effect=[0, 0, 61, 62]):
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
        class API:
            def windows(self, pid): return []
        process = Process()
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(gate.subprocess, 'Popen', return_value=process), patch.object(gate.threading, 'Timer', Timer):
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


if __name__ == '__main__':
    unittest.main()
