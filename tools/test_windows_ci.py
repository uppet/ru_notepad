#!/usr/bin/env python3
"""Portable harness tests with synthetic child programs and fake Win32 calls.

These verify orchestration/fail-closed policy only. They are NOT native editor,
GUI, DLL, file-codec, ACL, or Windows runtime acceptance evidence.
"""
from pathlib import Path
import re
import shutil
import subprocess
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

import windows_ci as ci


class NoDialogs:
    def no_dialog(self, _):
        return []


def kill_synthetic(process):
    if process.poll() is not None:
        return False
    process.kill()
    process.wait(timeout=5)
    return True


class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ci-harness-unit-')
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def console(self, code, timeout=3):
        with patch.object(ci, 'cleanup_process', side_effect=kill_synthetic):
            return ci.run_console(NoDialogs(), 'fixture', [sys.executable, '-c', code],
                                  self.root, r'^TOTAL PASS: 1\s*$', timeout=timeout)

    def powershell_resolver(self):
        source = (ci.ROOT / 'tools/windows_ci.ps1').read_text(encoding='utf-8')
        match = re.search(r'(?ms)^function Resolve-Application\b.*?^}', source)
        self.assertIsNotNone(match, 'Application resolution must use the shared helper')
        return source, match.group(0)

    def test_powershell_resolves_one_verified_application_object(self):
        source, resolver = self.powershell_resolver()
        self.assertEqual(source.count('Get-Command -'), 1)
        self.assertRegex(resolver, r'Get-Command -Name \$Name -CommandType Application -ErrorAction Stop\s*\|\s*Select-Object -First 1')
        self.assertIn('Test-Path -LiteralPath $Command.Source -PathType Leaf', resolver)
        self.assertIn('return [string]$Command.Source', resolver)

    def test_powershell_git_and_python_share_single_path_resolution(self):
        source, _ = self.powershell_resolver()
        self.assertIn("$Python = Resolve-Application 'python'", source)
        self.assertIn("$Git = Resolve-Application 'git'", source)
        self.assertNotRegex(source, r'\(Get-Command[^\n]+\)\.Source')
        self.assertIn('Test-Path -LiteralPath (Join-Path $Bin $name) -PathType Leaf', source)

    @unittest.skipUnless(sys.platform == 'win32',
                         'PowerShell duplicate-PATH execution requires the Windows CI host')
    def test_powershell_duplicate_path_executes_only_first_application(self):
        powershell = shutil.which('pwsh')
        self.assertIsNotNone(powershell, 'Windows CI must execute the PowerShell regression')
        _, resolver = self.powershell_resolver()
        first, second = self.root / 'first path', self.root / 'second path'
        first.mkdir()
        second.mkdir()
        name = 'ru-ci-resolve-probe.cmd'
        for folder, label in ((first, 'first'), (second, 'second')):
            (folder / name).write_text(f'@echo off\necho {label}\nexit /b 0\n', encoding='ascii')
        quote = lambda value: "'" + str(value).replace("'", "''") + "'"
        script = resolver + "\n" + f"""
$ErrorActionPreference = 'Stop'
$env:PATH = {quote(str(first) + ';' + str(second) + ';' + str(first) + ';')} + $env:PATH
$candidates = @(Get-Command -Name {quote(name)} -CommandType Application -All)
if ($candidates.Count -lt 2) {{ throw 'Duplicate PATH fixture did not create multiple candidates' }}
$selected = Resolve-Application {quote(name)}
if ($selected -isnot [string] -or $selected -ne {quote(first / name)}) {{
    throw 'Resolver did not select exactly the first executable path'
}}
if ((& $selected) -cne 'first' -or $LASTEXITCODE -ne 0) {{
    throw 'Selected executable did not run with its space-containing path intact'
}}
Write-Output 'DUPLICATE_PATH_RESOLUTION_PASS'
"""
        completed = subprocess.run([powershell, '-NoProfile', '-NonInteractive',
                                    '-Command', script], capture_output=True, text=True, timeout=30)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn('DUPLICATE_PATH_RESOLUTION_PASS', completed.stdout)

    def test_required_native_suite_counts_are_explicit_and_unchanged(self):
        expected = {
            'document_policy': r'^TOTAL PASS: 23\s*$',
            'ui_arguments': r'^TOTAL PASS: 19\s*$',
            'file_codec_flags': r'^TOTAL PASS: 80\s*$',
            'editor_native': r'^TOTAL PASS: 27\s*$',
            'app_native': r'^TOTAL PASS: 23\s*$',
            'file_codec_tests': r'^FILE_CODEC_TESTS_PASS=77\s*$',
        }
        self.assertEqual(dict(ci.NATIVE_CONSOLE_TESTS), expected)
        self.assertEqual(len(ci.NATIVE_CONSOLE_TESTS), 6)
        # Six console gates + normal GUI close + required ACL gate in the workflow.
        self.assertEqual(len(ci.NATIVE_CONSOLE_TESTS) + 1 + 1, 8)

    def test_flag_regression_is_built_packaged_and_in_user_test_runner(self):
        source = (ci.ROOT / 'tools/windows_ci.ps1').read_text(encoding='utf-8')
        builds = re.search(r"foreach \(\$test in @\(([^)]+)\)\)", source)
        self.assertIsNotNone(builds)
        self.assertIn("'file_codec_flags'", builds.group(1))
        self.assertEqual(ci.BINARY_NAMES.count('file_codec_flags.exe'), 1)
        runner = (ci.ROOT / 'packaging/run-tests.cmd').read_text(encoding='utf-8')
        self.assertIn('file_codec_flags.exe >>test-results.txt 2>&1\n'
                      'if errorlevel 1 set "FAILED=1"', runner)

    def test_console_requires_execution_exit_zero_and_marker(self):
        result = self.console("print('PASS: synthetic'); print('TOTAL PASS: 1')")
        self.assertTrue(result['passed'])
        self.assertTrue(result['executed'])
        self.assertFalse(result['cleanup_killed'])
        self.assertEqual(result['assertions_passed'], 1)

    def test_console_nonzero_fails_even_with_marker(self):
        result = self.console("print('TOTAL PASS: 1'); raise SystemExit(7)")
        self.assertFalse(result['passed'])
        self.assertEqual(result['exit_code'], 7)

    def test_console_missing_marker_fails(self):
        self.assertFalse(self.console("print('just ran')")['passed'])

    def test_console_fail_line_overrides_marker(self):
        self.assertFalse(self.console("print('FAIL: case'); print('TOTAL PASS: 1')")['passed'])

    def test_console_skip_is_recorded_and_fails_required_gate(self):
        result = self.console("print('SKIP: synthetic case'); print('TOTAL PASS: 1')")
        self.assertFalse(result['passed'])
        self.assertEqual(result['skips'], ['SKIP: synthetic case'])

    def test_console_timeout_and_cleanup_never_pass(self):
        result = self.console('import time; time.sleep(30)', timeout=0.05)
        self.assertFalse(result['passed'])
        self.assertTrue(result['cleanup_killed'])
        self.assertIn('deadline', result['error'])

    def test_console_oversized_output_fails_and_is_capped(self):
        result = self.console(f"print('x' * {ci.MAX_LOG_BYTES + 1})")
        self.assertFalse(result['passed'])
        self.assertLessEqual((self.root / 'fixture.stdout.log').stat().st_size, ci.MAX_LOG_BYTES)

    def gui(self, mode='normal'):
        binary = self.root / 'bin'
        evidence = self.root / 'evidence'
        binary.mkdir()
        evidence.mkdir()
        process = type('SyntheticProcess', (), {'pid': 12345, 'finished': mode == 'early',
            'returncode': 0, 'poll': lambda self: self.returncode if self.finished else None})()
        clock = [0.0]
        def monotonic():
            clock[0] += 0.2
            return clock[0]
        def launch(*_, **__):
            if mode != 'missing-log':
                lines = ['[launcher] Starting Ru program.', '[startup] menu installed',
                         '[startup] initial document ready', '[startup] main window shown',
                         '[launcher] Ru program returned with status 0.']
                if mode == 'bad-log':
                    lines[-1] = '[launcher] Ru program exited before returning to the launcher.'
                (binary / 'ru_notepad-synthetic.log').write_text('\n'.join(lines), encoding='utf-8')
            return process
        class FakeWindows:
            def no_dialog(self, _):
                if mode == 'dialog':
                    raise RuntimeError('Unexpected modal dialog in synthetic native test')
                return [] if mode == 'missing-window' else [(123, ci.MAIN_CLASS, True)]
            def responsive(self, _):
                if mode == 'unresponsive':
                    raise RuntimeError('Unresponsive synthetic window')
            def close(self, _):
                process.finished = mode != 'close-timeout'
        def cleanup(_):
            killed = not process.finished
            process.finished = True
            return killed
        with patch.object(ci.subprocess, 'Popen', side_effect=launch) as start, \
             patch.object(ci, 'cleanup_process', side_effect=cleanup), \
             patch.object(ci.time, 'monotonic', side_effect=monotonic), \
             patch.object(ci.time, 'sleep'):
            result = ci.run_gui(FakeWindows(), binary, evidence)
        return result, start

    def test_gui_requires_detached_visible_responsive_normal_close(self):
        result, start = self.gui()
        self.assertTrue(result['passed'])
        self.assertTrue(result['main_hwnd_seen'])
        self.assertTrue(result['close_posted'])
        self.assertFalse(result['cleanup_killed'])
        self.assertEqual(start.call_args.kwargs['creationflags'], 0x00000008)

    def test_gui_early_exit_is_failure(self):
        self.assertFalse(self.gui('early')[0]['passed'])

    def test_gui_error_dialog_is_failure(self):
        result, _ = self.gui('dialog')
        self.assertFalse(result['passed'])
        self.assertTrue(result['cleanup_killed'])

    def test_gui_missing_hwnd_is_failure(self):
        result, _ = self.gui('missing-window')
        self.assertFalse(result['passed'])
        self.assertFalse(result['main_hwnd_seen'])

    def test_gui_unresponsive_hwnd_is_failure(self):
        self.assertFalse(self.gui('unresponsive')[0]['passed'])

    def test_gui_close_timeout_cleanup_never_passes(self):
        result, _ = self.gui('close-timeout')
        self.assertFalse(result['passed'])
        self.assertTrue(result['close_posted'])
        self.assertTrue(result['cleanup_killed'])

    def test_gui_missing_log_is_failure(self):
        self.assertFalse(self.gui('missing-log')[0]['passed'])

    def test_gui_early_exit_log_is_failure(self):
        self.assertFalse(self.gui('bad-log')[0]['passed'])

    def test_log_reader_rejects_overflow(self):
        path = self.root / 'large.log'
        path.write_bytes(b'x' * (ci.MAX_LOG_BYTES + 1))
        with self.assertRaises(RuntimeError):
            ci.bounded_text(path)

    def test_pe_import_gate_rejects_unbundled_runtime(self):
        path = self.root / 'synthetic.exe'
        data = bytearray(128)
        data[:2] = b'MZ'
        struct.pack_into('<I', data, 60, 64)
        data[64:68] = b'PE\0\0'
        struct.pack_into('<H', data, 68, 0x8664)
        path.write_bytes(data)
        with patch.object(ci.subprocess, 'check_output', return_value='DLL Name: libgcc_s_seh-1.dll'):
            with self.assertRaisesRegex(RuntimeError, 'unpackaged'):
                ci.inspect_pe(path, 'synthetic-objdump')

    def test_missing_runtime_notices_block_packaging(self):
        license_dir = self.root / 'mingw/share/licenses/gcc'
        license_dir.mkdir(parents=True)
        (license_dir / 'COPYING3').write_text('GNU GENERAL PUBLIC LICENSE', encoding='utf-8')
        with self.assertRaisesRegex(RuntimeError, 'Runtime Library Exception'):
            ci.copy_runtime_licenses(self.root / 'mingw', self.root / 'out')


if __name__ == '__main__':
    unittest.main(verbosity=2)
