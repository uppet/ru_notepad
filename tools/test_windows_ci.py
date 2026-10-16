#!/usr/bin/env python3
"""Portable harness tests with synthetic child programs and fake Win32 calls.

These verify orchestration/fail-closed policy only. They are NOT native editor,
GUI, DLL, file-codec, ACL, or Windows runtime acceptance evidence.
"""
from pathlib import Path
import os
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
                                  self.root, r'^TOTAL PASS: 1\s*$', timeout=timeout, expected_assertions=1)

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
            'app_features_native': r'^TOTAL PASS: 23\s*$',
            'shortcuts': r'^TOTAL PASS: 34\s*$',
            'syntax_policy': r'^TOTAL PASS: 100\s*$',
            'status_native': r'^TOTAL PASS: 21\s*$',
            'syntax_native': r'^TOTAL PASS: 82\s*$',
            'file_codec_tests': r'^FILE_CODEC_TESTS_PASS=77\s*$',
        }
        self.assertEqual(dict(ci.NATIVE_CONSOLE_TESTS), expected)
        self.assertEqual(len(ci.NATIVE_CONSOLE_TESTS), 11)
        # Eleven console gates, two isolated lexer fallbacks, GUI and ACL.
        self.assertEqual(len(ci.NATIVE_CONSOLE_TESTS) + len(ci.SYNTAX_FALLBACK_TESTS) + 2, 15)

    def test_flag_regression_is_built_packaged_and_in_user_test_runner(self):
        source = (ci.ROOT / 'tools/windows_ci.ps1').read_text(encoding='utf-8')
        builds = re.search(r"foreach \(\$test in @\(([^)]+)\)\)", source)
        self.assertIsNotNone(builds)
        self.assertIn("'file_codec_flags'", builds.group(1))
        self.assertEqual(ci.BINARY_NAMES.count('file_codec_flags.exe'), 1)
        runner = (ci.ROOT / 'packaging/run-tests.cmd').read_text(encoding='utf-8')
        self.assertIn('file_codec_flags.exe >>test-results.txt 2>&1\n'
                      'if not "%ERRORLEVEL%"=="0" set "FAILED=1"', runner)

    def test_every_required_suite_is_built_packaged_and_explained_in_runner(self):
        source = (ci.ROOT / 'tools/windows_ci.ps1').read_text(encoding='utf-8')
        builds = re.search(r"foreach \(\$test in @\(([^)]+)\)\)", source)
        built_tests = set(re.findall(r"'([^']+)'", builds.group(1)))
        required = {name for name, _ in ci.NATIVE_CONSOLE_TESTS}
        self.assertEqual(built_tests, required | {'file_codec_security_probe'})
        runner = (ci.ROOT / 'packaging/run-tests.cmd').read_text(encoding='utf-8')
        for name in built_tests:
            self.assertEqual(ci.BINARY_NAMES.count(name + '.exe'), 1)
            self.assertIn(name + '.exe:', runner, 'Each executable needs a plain purpose label')
        for name in required:
            self.assertRegex(runner, rf'(?m)^{name}\.exe(?: |$)')
        self.assertIn('call :syntax_fallback missing-lexilla --expect-missing', runner)
        self.assertIn('call :syntax_fallback bad-lexer --expect-bad-lexer', runner)

    def test_runner_treats_every_nonzero_status_as_failure_without_shadowing(self):
        runner = (ci.ROOT / 'packaging/run-tests.cmd').read_text(encoding='utf-8')
        self.assertIn('setlocal EnableExtensions DisableDelayedExpansion\nset "ERRORLEVEL="\n', runner)
        self.assertNotIn('if errorlevel 1', runner.lower())
        lines = runner.split('\n:syntax_fallback\n', 1)[0].splitlines()
        commands = [index for index, line in enumerate(lines)
                    if re.match(r'^[a-z_]+\.exe(?: |$)|^call :syntax_fallback ', line)]
        self.assertEqual(len(commands), len(ci.NATIVE_CONSOLE_TESTS) + len(ci.SYNTAX_FALLBACK_TESTS))
        for index in commands:
            self.assertEqual(lines[index + 1], 'if not "%ERRORLEVEL%"=="0" set "FAILED=1"')
        self.assertIn('set "FALLBACK_STATUS=%ERRORLEVEL%"', runner)
        self.assertIn('exit /b %FALLBACK_STATUS%', runner)

    @unittest.skipUnless(sys.platform == 'win32',
                         'Real cmd.exe signed-exit regression requires the Windows CI host')
    def test_cmd_runner_handles_zero_positive_negative_and_shadowed_exit_codes(self):
        command = shutil.which('cmd.exe')
        self.assertIsNotNone(command, 'Windows CI must execute the real batch regression')
        runner = (ci.ROOT / 'packaging/run-tests.cmd').read_text(encoding='utf-8')
        lines = runner.splitlines()
        prologue = '\n'.join(lines[:3])
        failure_check = next(line for line in lines if line.startswith('if not "%ERRORLEVEL%"'))
        capture = next(line for line in lines if line.startswith('set "FALLBACK_STATUS='))
        propagate = next(line for line in lines if line == 'exit /b %FALLBACK_STATUS%')
        for code in (0, 7, -1, -1073741819):
            for inherited in ('0', '123'):
                for use_call in (False, True):
                    with self.subTest(code=code, inherited=inherited, call=use_call):
                        invoke = f'cmd.exe /d /c exit /b {code}'
                        body = 'call :probe' if use_call else invoke
                        script = self.root / 'exit policy probe.cmd'
                        script.write_text(prologue + '\nset "FAILED=0"\n' + body + '\n' +
                            failure_check + '\necho FAILED=%FAILED%\nexit /b 0\n' +
                            ':probe\n' + invoke + '\n' + capture + '\n' + propagate + '\n', encoding='ascii')
                        environment = {key: value for key, value in os.environ.items() if key.upper() != 'ERRORLEVEL'}
                        environment['ERRORLEVEL'] = inherited
                        result = subprocess.run([command, '/d', '/e:off', '/v:on', '/c', str(script)],
                            env=environment, capture_output=True, text=True, timeout=20)
                        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                        self.assertRegex(result.stdout, rf'(?m)^FAILED={int(code != 0)}\s*$')

    def test_syntax_fallbacks_use_isolated_actual_dependency_layouts(self):
        binary, fixtures, evidence = (self.root / name for name in ('bin', 'fixtures', 'evidence'))
        for folder in (binary, fixtures, evidence):
            folder.mkdir()
        (binary / 'syntax_native.exe').write_bytes(b'synthetic executable')
        (binary / 'Scintilla.dll').write_bytes(b'synthetic editor DLL')
        (binary / 'Lexilla.dll').write_bytes(b'synthetic correct lexer DLL')
        with patch.object(ci, 'run_console', return_value={'passed': True}) as run:
            results = ci.run_syntax_fallbacks(NoDialogs(), binary, fixtures, evidence)
        self.assertEqual(len(results), 2)
        for call, (name, argument, bad) in zip(run.call_args_list, ci.SYNTAX_FALLBACK_TESTS):
            isolated = fixtures / name
            self.assertEqual(call.kwargs['cwd'], isolated)
            self.assertEqual(call.kwargs['expected_assertions'], 8)
            self.assertEqual(call.args[2], [str(isolated / 'syntax_native.exe'), argument])
            self.assertEqual((isolated / 'syntax_native.exe').read_bytes(), (binary / 'syntax_native.exe').read_bytes())
            self.assertEqual((isolated / 'Scintilla.dll').read_bytes(), (binary / 'Scintilla.dll').read_bytes())
            self.assertEqual((isolated / 'Lexilla.dll').exists(), bad)
            if bad:
                self.assertEqual((isolated / 'Lexilla.dll').read_bytes(), (binary / 'Scintilla.dll').read_bytes())

    def acceptance(self):
        summary = {'acl_requested': True, 'tests': [],
                   'tested_binary_sha256': {name: name + '-hash' for name in ci.BINARY_NAMES}}
        names = [name for name, _ in ci.NATIVE_CONSOLE_TESTS] + [case[0] for case in ci.SYNTAX_FALLBACK_TESTS] + ['file_codec_security', 'main-gui-smoke']
        for name in names:
            result = {'name': name, 'passed': True, 'executed': True, 'cleanup_killed': False,
                      'exit_code': 0, 'skips': []}
            if name == 'main-gui-smoke':
                result.update(main_hwnd_seen=True, close_posted=True, detached_from_console=True)
            else:
                result['assertions_passed'] = ci.expected_assertions(name)
            if name.startswith('syntax_') and name != 'syntax_native':
                result['fixture_binary_sha256'] = {binary: summary['tested_binary_sha256'][binary]
                                                  for binary in ('syntax_native.exe', 'Scintilla.dll')}
                if name == 'syntax_bad_lexer':
                    result['fixture_binary_sha256']['Lexilla.dll'] = summary['tested_binary_sha256']['Scintilla.dll']
            summary['tests'].append(result)
        return summary

    def test_acceptance_requires_all_fifteen_groups_and_553_assertions(self):
        summary = self.acceptance()
        ci.validate_acceptance(summary)
        self.assertEqual(len(summary['tests']), 15)
        self.assertEqual(sum(test.get('assertions_passed', 0) for test in summary['tests']), 553)

    def test_acceptance_rejects_missing_or_duplicated_syntax_branch(self):
        summary = self.acceptance()
        summary['tests'] = [test for test in summary['tests'] if test['name'] != 'syntax_missing_lexilla']
        with self.assertRaisesRegex(RuntimeError, 'inventory'):
            ci.validate_acceptance(summary)
        summary['tests'].append(summary['tests'][0])
        with self.assertRaisesRegex(RuntimeError, 'inventory'):
            ci.validate_acceptance(summary)

    def test_acceptance_rejects_fallback_binary_hash_mismatch(self):
        summary = self.acceptance()
        next(test for test in summary['tests'] if test['name'] == 'syntax_bad_lexer')['fixture_binary_sha256']['Lexilla.dll'] = 'wrong'
        with self.assertRaisesRegex(RuntimeError, 'fixture does not match'):
            ci.validate_acceptance(summary)

    def test_acceptance_rechecks_individual_assertion_count(self):
        summary = self.acceptance()
        summary['tests'][0]['assertions_passed'] -= 1
        with self.assertRaisesRegex(RuntimeError, 'count mismatch'):
            ci.validate_acceptance(summary)

    def test_receipt_paths_are_portable_on_windows(self):
        build = (ci.ROOT / 'tools/build.py').read_text(encoding='utf-8')
        self.assertNotIn('str(p.relative_to(ROOT))', build)
        self.assertNotIn('str(source.relative_to(ROOT))', build)
        self.assertEqual(build.count('p.relative_to(ROOT).as_posix()'), 2)
        self.assertIn('source.relative_to(ROOT).as_posix()', build)

    def test_console_requires_execution_exit_zero_and_marker(self):
        result = self.console("print('PASS: synthetic'); print('TOTAL PASS: 1')")
        self.assertTrue(result['passed'])
        self.assertTrue(result['executed'])
        self.assertFalse(result['cleanup_killed'])
        self.assertEqual(result['assertions_passed'], 1)

    def test_console_marker_without_individual_assertions_fails(self):
        self.assertFalse(self.console("print('TOTAL PASS: 1')")['passed'])

    def test_console_extra_individual_assertions_fail(self):
        self.assertFalse(self.console("print('PASS: one'); print('PASS: two'); print('TOTAL PASS: 1')")['passed'])

    def test_console_duplicate_totals_fail(self):
        self.assertFalse(self.console("print('PASS: one'); print('TOTAL PASS: 1'); print('TOTAL PASS: 1')")['passed'])

    def test_console_conflicting_totals_fail(self):
        self.assertFalse(self.console("print('PASS: one'); print('TOTAL PASS: 2'); print('TOTAL PASS: 1')")['passed'])

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
