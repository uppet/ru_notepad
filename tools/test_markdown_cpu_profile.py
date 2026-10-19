#!/usr/bin/env python3
"""Host-only negative controls. Never launches Windows or a profiler session."""
from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_markdown_cpu_profile as profile


def tool_result(reason='scope_and_session_ownership_unverified'):
    ready = reason == 'scope_and_session_ownership_unverified'
    return {'schema': 1, 'reason': reason,
        'hashes': {name: 'a' * 64 if ready else None for name in profile.TOOL_NAMES},
        'verified': {name: ready for name in profile.TOOL_NAMES}}


class Contracts(unittest.TestCase):
    def test_default_never_claims_actual_profile(self):
        record = profile.validate_report(profile.blank_report())
        self.assertEqual(record['status'], 'profile_unavailable')
        self.assertFalse(record['native_profile_executed'])
        self.assertFalse(record['hotspots_available'])
        self.assertFalse(record['raw_trace_created'])

    def test_only_fixed_reasons_allowed(self):
        for reason in profile.REASONS:
            record = profile.blank_report()
            record['reason'] = reason
            if reason == 'scope_and_session_ownership_unverified':
                profile.apply_preflight(record, tool_result())
            elif reason == 'preflight_cleanup_unconfirmed':
                record['discovery_cleanup'] = 'unconfirmed'
            profile.validate_report(record)
        record['reason'] = 'private path C:/users/secret'
        with self.assertRaises(profile.PreflightError):
            profile.validate_report(record)

    def test_no_success_or_claimed_capture(self):
        for field, value in (('status', 'passed'), ('native_profile_executed', True),
                             ('hotspots_available', True), ('raw_trace_created', True)):
            record = profile.blank_report()
            record[field] = value
            with self.subTest(field=field), self.assertRaises(profile.PreflightError):
                profile.validate_report(record)

    def test_no_start_stop_or_application_count(self):
        for field in ('profiler_start_calls', 'profiler_stop_calls', 'application_launches'):
            record = profile.blank_report()
            record['counts'][field] = 1
            with self.subTest(field=field), self.assertRaises(profile.PreflightError):
                profile.validate_report(record)

    def test_no_unverified_capability_claim(self):
        for field in profile.CAPABILITIES[3:]:
            record = profile.blank_report()
            record['capabilities'][field] = True
            with self.subTest(field=field), self.assertRaises(profile.PreflightError):
                profile.validate_report(record)

    def test_private_text_cannot_enter_schema(self):
        for field in ('error', 'stdout', 'stderr', 'path', 'command_line', 'document'):
            record = profile.blank_report()
            record[field] = 'PRIVATE_SENTINEL'
            with self.subTest(field=field), self.assertRaises(profile.PreflightError):
                profile.validate_report(record)

    def test_only_fixed_hash_inventory(self):
        for field in ('tool_sha256', 'runtime_sha256'):
            record = profile.blank_report()
            record[field][next(iter(record[field]))] = 'PRIVATE_SENTINEL'
            with self.assertRaises(profile.PreflightError):
                profile.validate_report(record)
            record = profile.blank_report()
            record[field]['C:/private/path'] = 'a' * 64
            with self.assertRaises(profile.PreflightError):
                profile.validate_report(record)

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(profile.PreflightError):
            profile.strict_json('{"schema":1,"schema":1}')

    def test_nonfinite_json_rejected(self):
        for token in ('NaN', 'Infinity', '-Infinity'):
            with self.subTest(token=token), self.assertRaises(profile.PreflightError):
                profile.strict_json('{"x":' + token + '}')

    def test_ready_tools_remain_unavailable(self):
        record = profile.blank_report()
        profile.apply_preflight(record, tool_result())
        profile.validate_report(record)
        self.assertEqual(record['status'], 'profile_unavailable')
        self.assertEqual(record['reason'], 'scope_and_session_ownership_unverified')
        self.assertTrue(all(record['capabilities'][name] for name in profile.CAPABILITIES[:3]))
        self.assertFalse(any(record['capabilities'][name] for name in profile.CAPABILITIES[3:]))

    def test_invalid_discovery_is_not_trusted(self):
        variants = []
        raw = tool_result(); raw['path'] = 'PRIVATE_SENTINEL'; variants.append(raw)
        raw = tool_result(); raw['schema'] = True; variants.append(raw)
        raw = tool_result(); raw['verified']['collector'] = False; variants.append(raw)
        raw = tool_result(); raw['hashes']['config'] = 'PRIVATE_SENTINEL'; variants.append(raw)
        raw = tool_result(); raw['reason'] = 'success'; variants.append(raw)
        raw = tool_result('tool_absent'); raw['reason'] = 'scope_and_session_ownership_unverified'; variants.append(raw)
        for raw in variants:
            with self.subTest(raw=raw), self.assertRaises(profile.PreflightError):
                profile.apply_preflight(profile.blank_report(), raw)

    def test_readonly_discovery_script_has_no_collection_or_install_command(self):
        script = profile.PREFLIGHT_SCRIPT
        self.assertIn('Get-AuthenticodeSignature', script)
        self.assertIn('CPUUsageLow.json', script)
        self.assertIn("& $vswhere -latest -products '*' -property installationPath", script)
        for forbidden in ('& $collector', '/attach:', '/launch:', '/loadConfig:',
                          'Start-Process', 'Set-ExecutionPolicy', 'Invoke-WebRequest',
                          'wpr.exe', 'xperf.exe', 'vsinstr', 'Install-'):
            self.assertNotIn(forbidden.lower(), script.lower())
        self.assertEqual(re.findall(r'(?m)^\s*\$installations\s*=.*&\s+\$(\w+)', script), ['vswhere'])

    def test_only_powershell_discovery_and_owned_taskkill_can_launch(self):
        source = Path(profile.__file__).read_text(encoding='utf-8')
        tree = ast.parse(source)
        subprocess_calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
            and node.func.value.id == 'subprocess' and node.func.attr in ('Popen', 'run', 'call', 'check_call', 'check_output')]
        self.assertEqual(len(subprocess_calls), 2)
        self.assertEqual({call.func.attr for call in subprocess_calls}, {'Popen', 'run'})
        self.assertNotIn('import windows_ci', source)
        self.assertNotIn('SuspendThread', source)
        self.assertEqual((profile.PREFLIGHT_SECONDS, profile.TOTAL_SECONDS), (20, 30))


class FilesAndExecution(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.runtime = self.root / 'build/windows-ci/bin'
        self.runtime.mkdir(parents=True)
        for name in profile.RUNTIME_NAMES:
            (self.runtime / name).write_bytes(b'synthetic-runtime')
        self.output = self.root / 'build/windows-ci/evidence/markdown-cpu-profile.json'

    def test_nonwindows_does_not_invoke_any_tool(self):
        with patch.object(profile.sys, 'platform', 'linux'), patch.object(profile, 'invoke_preflight') as invoke:
            result = profile.run(self.runtime, self.output, root=self.root)
        invoke.assert_not_called()
        self.assertEqual(result['reason'], 'not_windows')
        self.assertEqual(json.loads(self.output.read_text()), result)
        self.assertFalse((self.root / 'build/windows-ci/private-cpu-profile').exists())

    def test_native_capability_success_is_still_unavailable(self):
        with patch.object(profile.sys, 'platform', 'win32'), patch.object(profile, 'invoke_preflight', return_value=tool_result()):
            result = profile.run(self.runtime, self.output, root=self.root)
        self.assertEqual(result['reason'], 'scope_and_session_ownership_unverified')
        self.assertFalse(result['native_profile_executed'])
        self.assertTrue(all(result['runtime_sha256'].values()))
        self.assertEqual(set(self.output.parent.iterdir()), {self.output})

    def test_exception_message_is_not_published(self):
        with patch.object(profile.sys, 'platform', 'win32'), patch.object(profile, 'invoke_preflight', side_effect=RuntimeError('PRIVATE_SENTINEL C:/users/person')):
            result = profile.run(self.runtime, self.output, root=self.root)
        self.assertEqual(result['reason'], 'preflight_failed')
        self.assertNotIn('PRIVATE_SENTINEL', self.output.read_text())

    def test_unknown_preflight_fields_fail_closed(self):
        raw = tool_result(); raw['private_path'] = 'PRIVATE_SENTINEL'
        with patch.object(profile.sys, 'platform', 'win32'), patch.object(profile, 'invoke_preflight', return_value=raw):
            result = profile.run(self.runtime, self.output, root=self.root)
        self.assertEqual(result['reason'], 'preflight_invalid')
        self.assertNotIn('PRIVATE_SENTINEL', self.output.read_text())

    def test_existing_private_directory_is_not_reused(self):
        private = self.root / 'build/windows-ci/private-cpu-profile'
        private.mkdir()
        (private / 'sentinel').write_text('unchanged')
        with patch.object(profile.sys, 'platform', 'win32'), patch.object(profile, 'invoke_preflight') as invoke:
            result = profile.run(self.runtime, self.output, root=self.root)
        invoke.assert_not_called()
        self.assertEqual(result['reason'], 'private_workspace_exists')
        self.assertEqual((private / 'sentinel').read_text(), 'unchanged')

    def test_output_outside_fixed_public_file_rejected(self):
        with self.assertRaises(profile.PreflightError):
            profile.run(self.runtime, self.root / 'other.json', root=self.root)
        self.assertFalse((self.root / 'other.json').exists())

    def test_linked_runtime_rejected(self):
        target = self.runtime / profile.RUNTIME_NAMES[0]
        target.unlink()
        target.symlink_to(self.runtime / profile.RUNTIME_NAMES[1])
        with patch.object(profile.sys, 'platform', 'win32'), patch.object(profile, 'invoke_preflight') as invoke:
            result = profile.run(self.runtime, self.output, root=self.root)
        invoke.assert_not_called()
        self.assertEqual(result['reason'], 'path_rejected')

    def test_linked_output_rejected_without_overwrite(self):
        self.output.parent.mkdir(parents=True)
        target = self.root / 'user-file'
        target.write_text('unchanged')
        self.output.symlink_to(target)
        with self.assertRaises(profile.PreflightError):
            profile.run(self.runtime, self.output, root=self.root)
        self.assertEqual(target.read_text(), 'unchanged')

    def test_existing_report_is_never_replaced_or_reused(self):
        self.output.parent.mkdir(parents=True)
        self.output.write_bytes(b'old-report-must-not-change')
        with patch.object(profile.sys, 'platform', 'win32'), \
                patch.object(profile, 'invoke_preflight') as invoke, \
                self.assertRaises(FileExistsError):
            profile.run(self.runtime, self.output, root=self.root)
        invoke.assert_not_called()
        self.assertEqual(self.output.read_bytes(), b'old-report-must-not-change')

    def test_expired_hash_deadline_rejected(self):
        with self.assertRaisesRegex(profile.PreflightError, 'preflight_timeout'):
            profile.file_hash(self.runtime / profile.RUNTIME_NAMES[0], time.monotonic() - 1)

    def test_oversized_runtime_rejected(self):
        with patch.object(profile, 'MAX_RUNTIME_BYTES', 1), self.assertRaises(profile.PreflightError):
            profile.file_hash(self.runtime / profile.RUNTIME_NAMES[0], time.monotonic() + 2)

    def test_missing_powershell_launch_does_not_increment_count(self):
        private = self.root / 'private'; private.mkdir()
        record = profile.blank_report()
        with patch.dict(os.environ, {'SystemRoot': str(self.root)}), self.assertRaises(profile.PreflightError):
            profile.invoke_preflight(private, time.monotonic() + 30, record)
        self.assertEqual(record['counts']['preflight_processes'], 0)

    def fake_discovery_process(self, raw, *, returncode=0):
        executable = self.root / 'System32/WindowsPowerShell/v1.0/powershell.exe'
        executable.parent.mkdir(parents=True)
        executable.write_bytes(b'host-test-placeholder-never-executed')
        class Process:
            pid = 197321
            killed = False
            def poll(self):
                return self.returncode
            def kill(self):
                self.killed = True
                self.returncode = -9
            def wait(self, timeout):
                if self.returncode is None:
                    raise AssertionError('Uncleaned owned process')
                return self.returncode
        process = Process()
        process.returncode = returncode
        calls = []
        def launch(command, **kwargs):
            calls.append(command)
            kwargs['stdout'].write(json.dumps(raw).encode('ascii'))
            kwargs['stdout'].flush()
            return process
        return process, launch, calls

    def test_actual_discovery_wrapper_only_launches_fixed_powershell_script(self):
        process, launch, calls = self.fake_discovery_process(tool_result())
        private = self.root / 'private'; private.mkdir()
        report = profile.blank_report()
        with patch.dict(os.environ, {'SystemRoot': str(self.root)}), \
                patch.object(profile.subprocess, 'Popen', side_effect=launch), \
                patch.object(profile.subprocess, 'run') as cleanup:
            result = profile.invoke_preflight(private, time.monotonic() + 30, report)
        self.assertEqual(result, tool_result())
        self.assertEqual(report['counts']['preflight_processes'], 1)
        self.assertEqual(calls[0][1:], ['-NoLogo', '-NoProfile', '-NonInteractive', '-Command', profile.PREFLIGHT_SCRIPT])
        self.assertEqual(Path(calls[0][0]).name, 'powershell.exe')
        cleanup.assert_not_called()
        self.assertFalse(process.killed)

    def test_discovery_timeout_cleans_only_its_own_process_tree(self):
        process, launch, calls = self.fake_discovery_process(tool_result(), returncode=None)
        private = self.root / 'private'; private.mkdir()
        report = profile.blank_report()
        with patch.dict(os.environ, {'SystemRoot': str(self.root)}), \
                patch.object(profile.subprocess, 'Popen', side_effect=launch), \
                patch.object(profile.subprocess, 'run', return_value=type('Result', (), {'returncode': 0})()) as cleanup, \
                patch.object(profile.time, 'monotonic', side_effect=[10, 10, 31]), \
                self.assertRaisesRegex(profile.PreflightError, 'preflight_timeout'):
            profile.invoke_preflight(private, 40, report)
        self.assertTrue(process.killed)
        self.assertEqual(cleanup.call_args.args[0][1:], ['/PID', str(process.pid), '/T', '/F'])
        self.assertEqual(cleanup.call_args.kwargs['timeout'], 3)
        self.assertEqual(len(calls), 1)
        self.assertEqual(report['counts']['profiler_stop_calls'], 0)
        self.assertEqual(report['discovery_cleanup'], 'confirmed')

    def test_failed_tree_cleanup_is_explicitly_unconfirmed(self):
        process, launch, calls = self.fake_discovery_process(tool_result(), returncode=None)
        private = self.root / 'private'; private.mkdir()
        report = profile.blank_report()
        with patch.dict(os.environ, {'SystemRoot': str(self.root)}), \
                patch.object(profile.subprocess, 'Popen', side_effect=launch), \
                patch.object(profile.subprocess, 'run', return_value=type('Result', (), {'returncode': 1})()), \
                patch.object(profile.time, 'monotonic', side_effect=[10, 10, 31]), \
                self.assertRaisesRegex(profile.PreflightError, 'preflight_cleanup_unconfirmed'):
            profile.invoke_preflight(private, 40, report)
        self.assertTrue(process.killed)
        self.assertEqual(report['discovery_cleanup'], 'unconfirmed')
        self.assertEqual(report['counts']['profiler_stop_calls'], 0)

    def test_nonzero_discovery_exit_does_not_run_any_cleanup_or_collector(self):
        process, launch, calls = self.fake_discovery_process(tool_result(), returncode=1)
        private = self.root / 'private'; private.mkdir()
        with patch.dict(os.environ, {'SystemRoot': str(self.root)}), \
                patch.object(profile.subprocess, 'Popen', side_effect=launch), \
                patch.object(profile.subprocess, 'run') as cleanup, \
                self.assertRaisesRegex(profile.PreflightError, 'preflight_failed'):
            profile.invoke_preflight(private, time.monotonic() + 30, profile.blank_report())
        cleanup.assert_not_called()
        self.assertEqual(len(calls), 1)

    def test_discovery_output_size_is_bounded(self):
        process, launch, calls = self.fake_discovery_process({'private': 'x' * 128})
        private = self.root / 'private'; private.mkdir()
        with patch.dict(os.environ, {'SystemRoot': str(self.root)}), \
                patch.object(profile.subprocess, 'Popen', side_effect=launch), \
                patch.object(profile, 'MAX_OUTPUT_BYTES', 64), \
                self.assertRaisesRegex(profile.PreflightError, 'preflight_invalid'):
            profile.invoke_preflight(private, time.monotonic() + 30, profile.blank_report())

    def test_wrong_runtime_path_does_not_start_discovery(self):
        with patch.object(profile.sys, 'platform', 'win32'), patch.object(profile, 'invoke_preflight') as invoke:
            result = profile.run(self.root, self.output, root=self.root)
        invoke.assert_not_called()
        self.assertEqual(result['reason'], 'path_rejected')

    def test_absent_tool_remains_explicitly_unavailable(self):
        with patch.object(profile.sys, 'platform', 'win32'), patch.object(profile, 'invoke_preflight', return_value=tool_result('tool_absent')):
            result = profile.run(self.runtime, self.output, root=self.root)
        self.assertEqual(result['reason'], 'tool_absent')
        self.assertEqual(result['status'], 'profile_unavailable')


if __name__ == '__main__':
    unittest.main()
