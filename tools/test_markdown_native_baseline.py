#!/usr/bin/env python3
"""Bounded native-baseline controls. Host passes are not Windows GUI evidence."""
from copy import deepcopy
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_markdown_native_baseline as baseline


def sample(run=1):
    value = {'schema': 1, 'run': run, 'qpc_frequency': 10000000,
             'cleanup': True, **baseline.PRESENTATION, 'components': []}
    for index, component in enumerate(baseline.COMPONENTS):
        ticks = {name: 0 for name in baseline.TICK_FIELDS}
        active = ('style_ticks',) if index == 0 else ('fold_ticks',) if index == 1 else baseline.TICK_FIELDS
        for key in active: ticks[key] = 1000
        mode = 'untouched_default' if index == 0 else 'predetermined_final'
        value['components'].append({'component': component, 'qpc_start': 100000 + index * 100000,
            'qpc_end': 100000 + index * 100000 + sum(ticks.values()), **ticks, **baseline.PROOFS,
            'fold_mode': mode, 'fold_fnv1a64': baseline.FOLD_FNV[mode],
            'fold_writes': 0 if index == 0 else 100001, 'paint_count': 1 if index == 2 else 0})
    return value


def encoded(value):
    return json.dumps(value).encode('ascii')


def process_receipt():
    return {'returncode': 0, 'cleanup_confirmed': True, 'wall_ms': 1000.0,
        'stdout_bytes': 1000, 'stderr_bytes': 0, 'stdout_sha256': '1' * 64,
        'stderr_sha256': hashlib.sha256(b'').hexdigest()}


def summary():
    samples = [sample(run) for run in range(1, 4)]
    return {'schema': 1, 'status': 'passed', 'scope': 'native_host_only_not_product_acceptance',
        'corpus': {'kind': 'unclosed-fence', 'bytes': 1000000, 'lf_count': 100000,
            'document_lines': 100001, 'sha256': baseline.INPUT_SHA256},
        'budgets': {'build_seconds': 60, 'process_seconds': 15, 'total_seconds': 120,
            'repetitions': 3, 'max_log_bytes': 16384, 'job_memory_bytes': 512 * 1024 * 1024},
        'identity': {'native_source_sha256': '1' * 64, 'runner_source_sha256': '2' * 64,
            'corpus_source_sha256': '3' * 64, 'compiler_sha256': '4' * 64, 'executable_sha256': '5' * 64,
            'archives': dict(baseline.ARCHIVES), 'flags': list(baseline.FLAGS),
            'headers': {name: '6' * 64 for name in baseline.HEADERS},
            'dependencies': {'Scintilla.dll': {'version': '5.6.7', 'sha256': '7' * 64},
                             'Lexilla.dll': {'version': '5.5.4', 'sha256': '8' * 64}}},
        'build': process_receipt(), 'processes': [process_receipt() for _ in range(3)],
        'samples': samples, 'statistics': baseline.statistics_for(samples)}


class SchemaControls(unittest.TestCase):
    def reject(self, value):
        with self.assertRaises(baseline.BaselineError):
            baseline.parse_sample(encoded(value), 1)

    def test_valid_three_components_have_disjoint_pure_timers(self):
        value = baseline.parse_sample(encoded(sample()), 1)
        self.assertEqual([row['fold_writes'] for row in value['components']], [0, 100001, 100001])
        self.assertEqual([row['paint_count'] for row in value['components']], [0, 0, 1])

    def test_missing_extra_duplicate_and_nonjson_output_rejected(self):
        value = sample()
        for raw in (b'', b'private path\n' + encoded(value), encoded(value) * 2,
                    encoded(value).replace(b'"schema": 1', b'"schema": 1, "schema": 1'),
                    b'x' * (baseline.MAX_LOG_BYTES + 1), b'{"schema":NaN}', b'\xff'):
            with self.subTest(raw=raw[:40]), self.assertRaises(baseline.BaselineError):
                baseline.parse_sample(raw, 1)
        for key in sample():
            value = sample(); del value[key]; self.reject(value)
        value = sample(); value['path'] = 'private'; self.reject(value)
        for key in sample()['components'][0]:
            value = sample(); del value['components'][0][key]; self.reject(value)
        value = sample(); value['components'][0]['secret'] = 'private'; self.reject(value)

    def test_all_proof_values_and_types_fail_closed(self):
        for index in range(3):
            for key, current in sample()['components'][index].items():
                if key in baseline.TICK_FIELDS or key in ('qpc_start', 'qpc_end', 'component'):
                    continue
                value = sample()
                value['components'][index][key] = not current if type(current) is bool else (
                    current + 1 if type(current) is int else 'wrong')
                self.reject(value)
        for key in baseline.PRESENTATION:
            value = sample(); value[key] = None; self.reject(value)
        for key in ('schema', 'run', 'qpc_frequency'):
            value = sample(); value[key] = True; self.reject(value)
        value = sample(); value['cleanup'] = 1; self.reject(value)

    def test_qpc_invalid_or_nonfinite_values_rejected(self):
        for key in ('qpc_frequency',):
            for invalid in (0, -1, 1000000001, True, 1.5, float('nan'), float('inf')):
                value = sample(); value[key] = invalid; self.reject(value)
        for key in ('qpc_start', 'qpc_end', *baseline.TICK_FIELDS):
            for invalid in (-1, True, 0.5, 2**63, float('nan'), float('inf')):
                value = sample(); value['components'][0][key] = invalid; self.reject(value)
        for index in range(3):
            value = sample(); value['components'][index]['qpc_end'] = value['components'][index]['qpc_start']
            self.reject(value)
        value = sample(); value['components'][1]['qpc_start'] = 1; self.reject(value)
        value = sample(); value['components'][0]['qpc_end'] += 1; self.reject(value)
        value = sample(); value['components'][0]['style_ticks'] = 150000001
        value['components'][0]['qpc_end'] = value['components'][0]['qpc_start'] + 150000001
        self.reject(value)

    def test_total_qpc_span_and_receipt_wall_must_agree(self):
        value = sample()
        value['components'][2]['qpc_start'] += 150000000
        value['components'][2]['qpc_end'] += 150000000
        self.reject(value)
        value = summary(); value['processes'][0]['wall_ms'] = 0.1
        with self.assertRaises(baseline.BaselineError): baseline.validate_summary(value)
        value = summary()
        value['build']['wall_ms'] = 70000.0
        for process in value['processes']: process['wall_ms'] = 25000.0
        with self.assertRaises(baseline.BaselineError): baseline.validate_summary(value)

    def test_complete_repetitions_required_before_statistics(self):
        good = [sample(run) for run in range(1, 4)]
        self.assertEqual(baseline.statistics_for(good)['colourise']['median_ms'], 0.1)
        for bad in ([], good[:2], good + [sample(4)], [sample(1)] * 3):
            with self.assertRaises(baseline.BaselineError): baseline.statistics_for(bad)
        value = sample(); value['components'].reverse(); self.reject(value)
        value = sample(); value['components'].pop(); self.reject(value)

    def test_summary_strict_shape_identity_and_statistics(self):
        self.assertEqual(baseline.validate_summary(summary())['status'], 'passed')
        for key in summary():
            value = summary(); del value[key]
            with self.assertRaises(baseline.BaselineError): baseline.validate_summary(value)
        alterations = [
            lambda v: v['statistics']['colourise'].update(median_ms=0),
            lambda v: v['processes'][0].update(cleanup_confirmed=False),
            lambda v: v['processes'][0].update(stderr_bytes=1),
            lambda v: v['processes'][0].update(wall_ms=float('nan')),
            lambda v: v['identity'].update(compiler_sha256='0' * 64),
            lambda v: v['identity']['dependencies']['Lexilla.dll'].update(version='new'),
            lambda v: v['identity']['archives'].update({'lexilla554.zip': '9' * 64}),
            lambda v: v['budgets'].update(repetitions=True),
            lambda v: v['identity'].update(private_path='/private'),
            lambda v: v.update(samples=v['samples'][:2]),
        ]
        for alter in alterations:
            value = summary(); alter(value)
            with self.assertRaises(baseline.BaselineError): baseline.validate_summary(value)


class CorpusAndPathControls(unittest.TestCase):
    def test_exact_existing_fixture_and_independent_style_fold_oracles(self):
        data = baseline.fixture()
        self.assertEqual((len(data), data.count(b'\n')), (1000000, 100000))
        self.assertEqual(hashlib.sha256(data).hexdigest(), baseline.INPUT_SHA256)
        def fnv(values):
            value = 14695981039346656037
            for byte in values: value = ((value ^ byte) * 1099511628211) & ((1 << 64) - 1)
            return f'{value:016x}'
        self.assertEqual(fnv(6 if i == 0 else 1 if i in (9, 10) else 0 if i < 11 else 21
                             for i in range(1000000)), baseline.STYLE_FNV)
        for mode, final in (('untouched_default', False), ('predetermined_final', True)):
            levels = ((9216 if i == 0 else 1025) if final else 1024 for i in range(100001))
            self.assertEqual(fnv(byte for level in levels for byte in level.to_bytes(4, 'little')),
                             baseline.FOLD_FNV[mode])

    def test_no_traversal_symlink_hardlink_or_oversize(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); source = root / 'source'; source.write_bytes(b'valid')
            self.assertEqual(baseline.digest_file(source), hashlib.sha256(b'valid').hexdigest())
            for path in (root / '..' / 'source', root):
                with self.assertRaises(baseline.BaselineError): baseline.safe_path(path)
            with self.assertRaises(baseline.BaselineError): baseline.digest_file(source, 4)
            hard = root / 'hard'; os.link(source, hard)
            with self.assertRaises(baseline.BaselineError): baseline.digest_file(source)
            hard.unlink()
            try: (root / 'link').symlink_to(source)
            except OSError: pass  # Windows developer-mode privilege may be unavailable.
            else:
                with self.assertRaises(baseline.BaselineError): baseline.digest_file(root / 'link')

    def test_only_explicit_trusted_compiler_may_have_hardlink_aliases(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); compiler = root / 'gcc.exe'; compiler.write_bytes(b'official compiler')
            os.link(compiler, root / 'target-gcc.exe')
            with self.assertRaises(baseline.BaselineError): baseline.safe_path(compiler)
            with self.assertRaises(baseline.BaselineError): baseline.digest_file(compiler)
            self.assertEqual(baseline.safe_path(compiler, trusted_compiler=True), compiler)
            self.assertEqual(baseline.digest_file(compiler, trusted_compiler=True),
                             hashlib.sha256(b'official compiler').hexdigest())

    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'report.json'; output.write_bytes(b'existing')
            with redirect_stdout(io.StringIO()) as messages:
                self.assertEqual(baseline.main(['--cc', 'unused', '--runtime-dir', 'unused', '--output', str(output)]), 1)
            self.assertEqual(output.read_bytes(), b'existing')
            self.assertEqual(messages.getvalue().strip(), 'MD_NATIVE_BASELINE_FAILED output_exists')

    def test_unexpected_errors_are_sanitized_and_new_report_is_failed(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'report.json'
            with patch.object(baseline, 'execute', side_effect=RuntimeError('private text /secret/path')):
                with redirect_stdout(io.StringIO()) as messages:
                    self.assertEqual(baseline.main(['--cc', 'unused', '--runtime-dir', 'unused', '--output', str(output)]), 1)
            self.assertNotIn('private', output.read_text() + messages.getvalue())
            self.assertEqual(json.loads(output.read_text()), {'schema': 1, 'status': 'failed', 'error': 'internal_error'})
            self.assertEqual(list(Path(temporary).iterdir()), [output])

    def test_budgets_are_fixed_and_native_source_is_research_only(self):
        self.assertEqual((baseline.BUILD_SECONDS, baseline.SAMPLE_SECONDS, baseline.TOTAL_SECONDS), (60, 15, 120))
        self.assertEqual((baseline.REPETITIONS, baseline.MAX_LOG_BYTES), (3, 16384))
        source = baseline.SOURCE.read_text()
        for expected in ('SendMessageW', 'SCI_COLOURISE', 'SCI_SETFOLDLEVEL', 'SCI_GETSTYLEDTEXTFULL',
                         'GetUpdateRgn', 'EqualRgn', 'QueryPerformanceCounter', 'GetDpiForWindow'):
            self.assertIn(expected, source)
        for forbidden in ('SCI_GETDIRECTFUNCTION', 'ru_function_', 'file_drop', 'ShellExecute', 'CreateProcess'):
            self.assertNotIn(forbidden, source)
        self.assertFalse((baseline.ROOT / 'native/markdown_baseline.c').exists())


@unittest.skipUnless(os.name == 'nt', 'real Windows job controls')
class WindowsProcessControls(unittest.TestCase):
    def test_owned_process_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            raw, receipt = baseline.run_owned_process([sys.executable, '-c', 'print("ok")'],
                Path(temporary), 5, Path(temporary) / 'success')
            self.assertEqual(raw.strip(), b'ok'); self.assertTrue(receipt['cleanup_confirmed'])

    def test_output_and_timeout_are_rejected_with_cleanup(self):
        scripts = [('import os; os.write(1,b"x"*40000)', 5, 'process_output_bound'),
                   ('import time; time.sleep(60)', 0.2, 'process_timeout')]
        for script, seconds, error in scripts:
            with tempfile.TemporaryDirectory() as temporary:
                with self.assertRaisesRegex(baseline.BaselineError, '^' + error + '$'):
                    baseline.run_owned_process([sys.executable, '-c', script], Path(temporary), seconds,
                        Path(temporary) / 'negative')

    def test_timeout_terminates_spawned_descendant(self):
        import ctypes
        from ctypes import wintypes
        with tempfile.TemporaryDirectory() as temporary:
            pid_path = Path(temporary) / 'child.pid'
            script = ('import subprocess,sys,time; from pathlib import Path; '
                'p=subprocess.Popen([sys.executable,"-c","import time; time.sleep(60)"]); '
                'Path(' + repr(str(pid_path)) + ').write_text(str(p.pid)); time.sleep(60)')
            with self.assertRaisesRegex(baseline.BaselineError, '^process_timeout$'):
                baseline.run_owned_process([sys.executable, '-c', script], Path(temporary), 2,
                    Path(temporary) / 'descendant')
            self.assertTrue(pid_path.is_file())
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            kernel.OpenProcess.restype = wintypes.HANDLE
            kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            kernel.WaitForSingleObject.restype = wintypes.DWORD
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel.CloseHandle.restype = wintypes.BOOL
            handle = kernel.OpenProcess(0x100000, False, int(pid_path.read_text()))
            if handle:
                try: self.assertEqual(kernel.WaitForSingleObject(handle, 0), 0)
                finally: kernel.CloseHandle(handle)
            else:
                self.assertEqual(ctypes.get_last_error(), 87)  # PID no longer exists.

    def test_suspended_assignment_failure_never_runs_child(self):
        import ctypes
        real = ctypes.WinDLL
        class Wrapper:
            def __init__(self, library): self.library = library
            def __getattr__(self, name):
                if name == 'AssignProcessToJobObject':
                    def denied(*_): return 0
                    self.AssignProcessToJobObject = denied
                    return denied
                return getattr(self.library, name)
        with tempfile.TemporaryDirectory() as temporary:
            proof = Path(temporary) / 'must-not-exist'
            script = 'from pathlib import Path; Path(' + repr(str(proof)) + ').write_text("ran")'
            with patch.object(ctypes, 'WinDLL', side_effect=lambda *a, **kw: Wrapper(real(*a, **kw))):
                with self.assertRaisesRegex(baseline.BaselineError, '^process_job$'):
                    baseline.run_owned_process([sys.executable, '-c', script], Path(temporary), 5,
                        Path(temporary) / 'denied')
            self.assertFalse(proof.exists())


if __name__ == '__main__':
    unittest.main()
