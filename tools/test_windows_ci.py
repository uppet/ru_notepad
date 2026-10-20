#!/usr/bin/env python3
"""Portable harness tests with synthetic child programs and fake Win32 calls.

These verify orchestration/fail-closed policy only. They are NOT native editor,
GUI, DLL, file-codec, ACL, or Windows runtime acceptance evidence.
"""
from pathlib import Path
import ctypes
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import struct
import sys
import tempfile
import unittest
from types import SimpleNamespace
import xml.etree.ElementTree as ET
import zipfile
from unittest.mock import Mock, call, patch

import windows_ci as ci
import build as builder


class SyntheticWindowText(ci.Windows):
    """Controlled WM_GETTEXT payloads; no native API or platform override."""
    def __init__(self, before, after, reported_count=None):
        self.before, self.after = before, after
        self.reported_count, self.calls = reported_count, []

    def scalar(self, hwnd, message, wparam=0, lparam=0):
        self.calls.append((hwnd, message, wparam))
        if message == 0x000E:
            return len(self.before.encode('utf-16-le', 'surrogatepass')) // 2
        if message != 0x000D:
            raise AssertionError('Unexpected window-text message')
        encoded = self.after.encode('utf-16-le', 'surrogatepass')
        units = [int.from_bytes(encoded[index:index + 2], 'little') for index in range(0, len(encoded), 2)]
        count = min(len(units), wparam - 1)
        buffer = ctypes.cast(lparam, ctypes.POINTER(ctypes.c_wchar))
        for index, value in enumerate(units[:count]):
            buffer[index] = chr(value)
        buffer[count] = '\0'
        return count if self.reported_count is None else self.reported_count


def observer_evidence():
    """Synthetic receipt data only; never native or GUI execution evidence."""
    observer = ci.gui_ru_observer_record()
    observer.update(scalar_calls=24, wm_null_calls=3, sendmessage_calls=27,
        query_wall_ms=20.0, max_query_ms=2.0, snapshot_count=1, snapshot_wall_ms=50.0,
        max_snapshot_ms=50.0, max_snapshot_messages=24,
        snapshots=[{'start_ms': 10.0, 'wall_ms': 50.0, 'messages': 24, 'final': True}],
        response_starts_ms=[0.0, 50.0, 100.0])
    receipts = []
    for seq in range(1, 4):
        receipt = dict.fromkeys(ci.GUI_RU_SNAPSHOT_INTEGER_FIELDS | ci.GUI_RU_SNAPSHOT_TIME_FIELDS, 0)
        receipt.update(seq=seq, ok=1, generation=1 if seq == 1 else 2,
            pending=int(seq == 2), bytes=1000000 if seq == 3 else 100,
            feed=1000000 if seq == 3 else 100, read_bytes=1000000 if seq == 3 else 100)
        receipts.append(receipt)
    diagnostics = {'message': ci.GUI_RU_DIAGNOSTIC_MESSAGE, 'capture_limit_ms': 1000,
        'requests': [{'phase': phase, 'post_wall_ms': 0.1, 'accepted': True}
                     for phase in ('baseline', 'pending', 'final')],
        'receipts': receipts, 'post_wall_ms': 0.3, 'log_reads': 2,
        'captures': [{'phase': phase, 'wall_ms': 0.2, 'log_reads': 1} for phase in ('baseline', 'final')],
        'log_read_wall_ms': 0.2, 'max_log_read_ms': 0.1}
    return {'observer': observer, 'diagnostics': diagnostics,
            'clock': {'clock_name': 'perf_counter', 'implementation': 'QueryPerformanceCounter()',
                      'resolution': 1e-7, 'monotonic': True, 'adjustable': False},
            'clock_measurement': ci.PERFORMANCE_CLOCK_MEASUREMENT,
            'head_style_measurement': ci.GUI_RU_HEAD_MEASUREMENT}


def markdown_evidence():
    """Synthetic schema fixture only; never evidence of running the GUI."""
    record = {'measurement': ci.GUI_MARKDOWN_MEASUREMENT, 'clock': {
        'clock_name': 'perf_counter', 'implementation': 'QueryPerformanceCounter()',
        'resolution': 1e-7, 'monotonic': True, 'adjustable': False}, 'cases': []}
    for kind in ('many-lines', 'singleline', 'unclosed-fence'):
        data, probes, folds = ci.gui_markdown_fixture(kind)
        case = {'kind': kind, 'size': len(data), 'source_sha256': hashlib.sha256(data).hexdigest(),
                'style_probes': probes, 'fold_probes': folds, 'stages': []}
        record['cases'].append(case)
        for operation in ('open', 'insert', 'backspace', 'undo'):
            expected, styles, _ = ci.markdown_expected(kind, operation)
            style_positions = [position for probe in styles
                               for position in range(probe['offset'], probe['offset'] + probe['length'])]
            style_values = [probe['style'] for probe in styles for _ in range(probe['length'])]
            dirty = operation in ('insert', 'backspace')
            observer = ci.gui_ru_observer_record()
            observer.update(scalar_calls=30, wm_null_calls=1, sendmessage_calls=31,
                query_wall_ms=10.0, max_query_ms=1.0, snapshot_count=1, snapshot_wall_ms=20.0,
                max_snapshot_ms=20.0, max_snapshot_messages=30,
                snapshots=[{'start_ms': 10.0, 'wall_ms': 20.0, 'messages': 30, 'final': True}],
                response_starts_ms=[0.0])
            before = 9 if operation == 'insert' else 8
            response = {'navigation': [
                {'key': 'RIGHT', 'before': before, 'after': before + 1, 'wall_ms': 1.0, 'request_pending': True},
                {'key': 'LEFT', 'before': before + 1, 'after': before, 'wall_ms': 1.0, 'request_pending': False}],
                'paint': {'invalidations': 1, 'pending_observed': False, 'already_serviced': True,
                          'cleared': True, 'wall_ms': 1.0, 'request_pending': True}} if dirty else {}
            case['stages'].append({'operation': operation, 'length': len(expected), 'dirty': dirty,
                'source_sha256': case['source_sha256'], 'wall_ms': 100.0, 'probes': 1, 'observer': observer,
                'responsiveness': response, 'undo_commands': 2 if operation == 'undo' else 0,
                'collapsed_before_edit': kind == 'many-lines' and dirty,
                'memory': {'measurement': ci.GUI_MARKDOWN_MEMORY_MEASUREMENT, 'sample_count': 1,
                    'sampledWorkingSetPeak': 1048576, 'processPeakWorkingSet': 2097152,
                    'query_wall_ms': 0.1, 'max_query_ms': 0.1, 'samples': [{'start_ms': 10.0,
                    'query_wall_ms': 0.1, 'workingSetBytes': 1048576, 'processPeakWorkingSetBytes': 2097152}]},
                'last_progress': {'opened': True, 'length': len(expected), 'dirty': dirty, 'status': 'complete', 'tail_requested': True,
                    'diagnostic': {'seq': 1, 'via': 0, 'id': 1, 'gen': 1, 'rev': 0, 'phase': 4, 'pending': 0, 'length': len(expected), 'feed': len(expected), 'published': 1, 'tick': 1, 'work_us': 1, 'gap_us': 1, 'bulkCalls': 1, 'bulkLines': 1, 'fallbackBatches': 0,
                        'directCalls': 0, 'directLines': 0, 'maxPlanBytes': 48, 'bulkUs': 1, 'ownedBufferBytes': 1088, 'metric_valid': 1}},
                'last_probe': {'length': len(expected), 'dirty': dirty, 'end_styled': len(expected),
                    'status_done': True, 'styles_match': True,
                    'style_samples': {'positions': style_positions, 'expected': style_values, 'actual': list(style_values)},
                    'folds_match': True, 'context_match': True,
                    'lexer': 98, 'tail_requested': True, 'children_visible': True}})
    return record


def markdown_route_metrics():
    """Synthetic validator controls only; never Windows measurements."""
    records = [dict(route=route, **dict.fromkeys(ci.FOLD_ROUTE_METRIC_FIELDS, 0))
               for route in ci.FOLD_ROUTE_ORDER]
    for record in records:
        record['metric_valid'] = 1
    records[0]['fallbackBatches'] = 1
    records[1].update(bulkCalls=1, bulkLines=1, maxPlanBytes=48, ownedBufferBytes=1088, bulkUs=1)
    records[2].update(directCalls=1, directLines=1)
    return records


def markdown_route_markers():
    return ''.join('FOLD_METRICS1 route=' + row['route'] + ''.join(' ' + key + '=' + str(row[key])
        for key in ci.FOLD_ROUTE_METRIC_FIELDS) + '\n' for row in markdown_route_metrics())


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

    def powershell_archive_helper(self):
        source = (ci.ROOT / 'tools/windows_ci.ps1').read_text(encoding='utf-8')
        match = re.search(r'(?ms)^function Expand-VerifiedArchive\b.*?^}', source)
        self.assertIsNotNone(match, 'Official archive extraction must use the shared helper')
        return source, match.group(0)

    def archive_test_powershell(self):
        powershell = shutil.which('pwsh')
        if powershell is None:
            if sys.platform == 'win32':
                self.fail('Windows CI must execute the real PowerShell archive regression')
            self.skipTest('PowerShell archive execution unavailable: pwsh is absent on this non-Windows host')
        return powershell

    def test_official_archives_use_only_tested_offline_preparation(self):
        source, helper = self.powershell_archive_helper()
        tested = "Invoke-Checked $Python @('tools/test_source_archives.py')"
        prepared = "Invoke-Checked $Python @('tools/prepare_source_archives.py','--root',$Root,"
        self.assertLess(source.index(tested), source.index(prepared))
        self.assertIn("'--receipt',(Join-Path $Evidence 'source-archives.json'))", source)
        pins = (
            ('scintilla', 'scintilla567.zip', '$Archive', 1904249,
             '2309181e59e7da4659f890dbc128db7451ccd094748770e7be674b830494587c'),
            ('lexilla', 'lexilla554.zip', '$LexillaArchive', 1598324,
             '5e0a21356e4e2f19d6a38ecd1c8172d5a2b7b4542940568b023386080db90fe0'),
        )
        for name, filename, variable, size, digest in pins:
            guarded_expand = (f"Expand-VerifiedArchive -Archive {variable} "
                              "-DestinationPath (Join-Path $Root 'vendor') `\n"
                              f"        -ExpectedSize {size} -ExpectedSha256 '{digest}'")
            self.assertIn(guarded_expand, source)
            self.assertLess(source.index(prepared), source.index(guarded_expand))
            self.assertIn(f"$Root 'vendor/{name}'", source)
            self.assertIn(f"$Downloads '{filename}'", source)
        self.assertNotIn('Invoke-WebRequest', source)
        self.assertNotRegex(source, r'(?i)https?://|curl|wget|Start-BitsTransfer')
        self.assertEqual(source.count('Expand-VerifiedArchive -Archive '), 2)
        self.assertEqual(source.count('Expand-Archive -'), 1)
        self.assertIn('Expand-Archive -LiteralPath $Archive -DestinationPath $DestinationPath', helper)
        self.assertLess(source.index(prepared), source.index("Invoke-Checked (Join-Path $Bin 'mingw32-make.exe')"))

    def test_powershell_offline_test_or_helper_failure_blocks_extraction_and_build(self):
        powershell = self.archive_test_powershell()
        source, _ = self.powershell_archive_helper()
        checked = re.search(r'(?ms)^function Invoke-Checked\b.*?^}', source).group(0)
        # Execute the actual admission block and real checked subprocess exits.
        # Synthetic scripts are used only to force both failure boundaries.
        block = source[source.index("    Invoke-Checked $Python @('tools/test_source_archives.py')"):
                       source.index("    Invoke-Checked $Python @('tools/check_static.py'")]
        quote = lambda value: "'" + str(value).replace("'", "''") + "'"
        for failed_stage in ('tests', 'prepare'):
            with self.subTest(stage=failed_stage):
                root = self.root / failed_stage
                (root / 'tools').mkdir(parents=True)
                (root / 'evidence').mkdir()
                (root / 'tools/test_source_archives.py').write_text(
                    'raise SystemExit(' + ('9' if failed_stage == 'tests' else '0') + ')\n', encoding='utf-8')
                (root / 'tools/prepare_source_archives.py').write_text(
                    "from pathlib import Path\nimport sys\nPath('helper-called').write_bytes(b'yes')\n"
                    "Path(sys.argv[-1]).write_bytes(b'{\"passed\":true}')\nraise SystemExit(17)\n",
                    encoding='utf-8')
                script = root / 'probe.ps1'
                script.write_text("Set-StrictMode -Version Latest\n$ErrorActionPreference = 'Stop'\n" + checked + f"""
$Root = {quote(root)}
$Evidence = Join-Path $Root 'evidence'
$Bin = Join-Path $Root 'no-build-tools'
$Python = {quote(sys.executable)}
$script:Extractions = 0
function Expand-VerifiedArchive {{ $script:Extractions++; throw 'Extraction must not run' }}
Push-Location $Root
$Failure = ''
try {{
{block}
}} catch {{ $Failure = $_.Exception.Message }} finally {{ Pop-Location }}
if ($Failure -notlike 'Command failed with exit code *' -or $script:Extractions -ne 0) {{
    throw 'Offline preparation did not fail before extraction and build'
}}
Write-Output 'OFFLINE_FAILURE_GUARD_PASS'
""", encoding='utf-8')
                result = subprocess.run([powershell, '-NoProfile', '-NonInteractive', '-File', str(script)],
                    capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('OFFLINE_FAILURE_GUARD_PASS', result.stdout)
                self.assertEqual((root / 'helper-called').exists(), failed_stage == 'prepare')
                if failed_stage == 'prepare':
                    self.assertTrue(json.loads((root / 'evidence/source-archives.json').read_text(encoding='utf-8'))['passed'])
                self.assertFalse((root / 'vendor').exists())

    def test_archive_powershell_host_controls_fail_windows_and_skip_only_when_absent(self):
        for platform in ('win32', 'linux'):
            with self.subTest(platform=platform, available=True), \
                    patch.object(sys, 'platform', platform), \
                    patch.object(shutil, 'which', return_value='synthetic-pwsh'):
                self.assertEqual(self.archive_test_powershell(), 'synthetic-pwsh')
        with patch.object(sys, 'platform', 'win32'), patch.object(shutil, 'which', return_value=None):
            with self.assertRaisesRegex(self.failureException, 'Windows CI must execute'):
                self.archive_test_powershell()
        with patch.object(sys, 'platform', 'linux'), patch.object(shutil, 'which', return_value=None):
            with self.assertRaisesRegex(unittest.SkipTest, 'pwsh is absent on this non-Windows host'):
                self.archive_test_powershell()

    def test_powershell_archive_guards_execute_before_extraction(self):
        powershell = self.archive_test_powershell()
        _, helper = self.powershell_archive_helper()
        contents = {'scintilla/include/Scintilla.h': b'synthetic header\n',
                    'scintilla/win32/makefile': b'synthetic makefile\n'}
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in contents.items():
                archive.writestr(name, data)
        valid = buffer.getvalue()
        cases = []
        for name, data, error in (
                ('valid', valid, ''),
                ('html', b'<!doctype html><html>browser challenge</html>', 'ZIP magic mismatch'),
                ('size', valid, 'size mismatch'),
                ('digest', valid, 'SHA256 mismatch'),
                ('magic', b'HTML' + valid[4:], 'ZIP magic mismatch'),
                ('malformed', b'PK\x03\x04broken central directory', 'malformed ZIP')):
            archive_path = self.root / (name + '.zip')
            archive_path.write_bytes(data)
            cases.append({'name': name, 'archive': str(archive_path),
                          'destination': str(self.root / (name + ' extracted')),
                          'size': len(data) + int(name == 'size'),
                          'sha256': '0' * 64 if name == 'digest' else hashlib.sha256(data).hexdigest(),
                          'error': error})
        case_file = self.root / 'archive cases.json'
        case_file.write_text(json.dumps(cases), encoding='utf-8')
        quote = lambda value: "'" + str(value).replace("'", "''") + "'"
        # Exercise the actual production helper. The spy delegates to real
        # extraction on success and proves invalid bytes never reach it.
        script = self.root / 'archive probe.ps1'
        script.write_text("Set-StrictMode -Version Latest\n$ErrorActionPreference = 'Stop'\n" + helper + f"""
$script:ExtractionCalls = 0
function Expand-Archive([string]$LiteralPath, [string]$DestinationPath) {{
    $script:ExtractionCalls++
    Microsoft.PowerShell.Archive\\Expand-Archive -LiteralPath $LiteralPath -DestinationPath $DestinationPath
}}
$Cases = Get-Content -LiteralPath {quote(case_file)} -Raw | ConvertFrom-Json
foreach ($Case in $Cases) {{
    $Before = $script:ExtractionCalls
    $Failure = ''
    try {{
        Expand-VerifiedArchive -Archive $Case.archive -DestinationPath $Case.destination `
            -ExpectedSize $Case.size -ExpectedSha256 $Case.sha256
    }} catch {{
        $Failure = $_.Exception.Message
    }}
    if ($Case.error -eq '') {{
        if ($Failure -ne '' -or $script:ExtractionCalls -ne ($Before + 1)) {{
            throw "Valid ZIP was not extracted exactly once: $Failure"
        }}
    }} else {{
        if ($Failure -notlike ('*' + $Case.error + '*')) {{
            throw "Archive case $($Case.name) failed for the wrong reason: $Failure"
        }}
        if ($script:ExtractionCalls -ne $Before -or (Test-Path -LiteralPath $Case.destination)) {{
            throw "Rejected archive case $($Case.name) reached extraction"
        }}
    }}
    Write-Output ('ARCHIVE_GUARD_PASS ' + $Case.name)
}}
""", encoding='utf-8')
        result = subprocess.run([powershell, '-NoProfile', '-NonInteractive', '-File', str(script)],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.splitlines(), ['ARCHIVE_GUARD_PASS ' + case['name'] for case in cases])
        extracted = self.root / 'valid extracted'
        self.assertEqual({path.relative_to(extracted).as_posix() for path in extracted.rglob('*')},
                         set(contents) | {'scintilla', 'scintilla/include', 'scintilla/win32'})
        self.assertEqual({path.relative_to(extracted).as_posix(): path.read_bytes()
                          for path in extracted.rglob('*') if path.is_file()}, contents)
        for case in cases[1:]:
            self.assertFalse(Path(case['destination']).exists(), case['name'])

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

    def test_required_native_suite_counts_are_explicit(self):
        expected = {
            'document_policy': r'^TOTAL PASS: 23\s*$',
            'ui_arguments': r'^TOTAL PASS: 19\s*$',
            'file_codec_flags': r'^TOTAL PASS: 80\s*$',
            'editor_native': r'^TOTAL PASS: 27\s*$',
            'app_native': r'^TOTAL PASS: 23\s*$',
            'app_features_native': r'^TOTAL PASS: 31\s*$',
            'app_streaming_native': r'^APP_STREAMING_TESTS_PASS=63\s*$',
            'shortcuts': r'^TOTAL PASS: 42\s*$',
            'syntax_policy': r'^TOTAL PASS: 134\s*$',
            'status_native': r'^TOTAL PASS: 21\s*$',
            'syntax_native': r'^TOTAL PASS: 138\s*$',
            'app_ru_native': r'^TOTAL PASS: 73\s*$',
            'app_ru_timer_native': r'^TOTAL PASS: 8\s*$',
            'ru_lexical_policy': r'^TOTAL PASS: 338\s*$',
            'ru_syntax_native': r'^TOTAL PASS: 149\s*$',
            'ru_direct_styling_native': r'^TOTAL PASS: 36\s*$',
            'markdown_policy': r'^TOTAL PASS: 221\s*$',
            'markdown_selection_policy': r'^TOTAL PASS: 31\s*$',
            'markdown_native': r'^TOTAL PASS: 58\s*$',
            'app_markdown_native': r'^TOTAL PASS: 70\s*$',
            'markdown_direct_native': r'^TOTAL PASS: 114\s*$',
            'file_codec_tests': r'^FILE_CODEC_TESTS_PASS=73\s*$',
            'file_streaming_native': r'^FILE_STREAMING_TESTS_PASS=99\s*$',
            'editor_streaming_native': r'^EDITOR_STREAMING_TESTS_PASS=21\s*$',
            'editor_largefile_native': r'^EDITOR_LARGEFILE_TESTS_PASS=10\s*$',
            'associations_policy': r'^TOTAL PASS: 19\s*$',
            'associations_native': r'^TOTAL PASS: 36\s*$',
            'file_drop_native': r'^TOTAL PASS: 38\s*$',
        }
        self.assertEqual(dict(ci.NATIVE_CONSOLE_TESTS), expected)
        self.assertEqual(len(ci.NATIVE_CONSOLE_TESTS), 28)
        # The original 38 gates remain, with one new direct-fold native console.
        self.assertEqual(len(ci.NATIVE_CONSOLE_TESTS) + len(ci.SYNTAX_FALLBACK_TESTS) + len(ci.GUI_NAMES) + 1, 39)

    def test_console_and_gui_receipts_share_all_manifest_resource_inputs(self):
        common = {'packaging/app.rc', 'packaging/app.manifest', 'assets/app-icon.ico', 'VERSION'}
        self.assertEqual(set(builder.build_input_paths(True)), common)
        self.assertEqual(set(builder.build_input_paths(False)), common | {'packaging/diagnostic_launcher.c'})

    def test_shared_resource_compilation_uses_existing_application_manifest(self):
        with patch.object(builder, 'run') as run:
            resource = builder.compile_resources('fixture-windres', self.root)
        self.assertEqual(resource, self.root / 'app-resource.o')
        run.assert_called_once_with(['fixture-windres', '-I', builder.ROOT / 'packaging',
                                     builder.ROOT / 'packaging/app.rc', resource])
        rc = (builder.ROOT / 'packaging/app.rc').read_text()
        self.assertRegex(rc, r'(?m)^1 RT_MANIFEST "app\.manifest"$')

    def test_shared_manifest_requests_common_controls_v6_without_elevation(self):
        manifest = ET.parse(builder.ROOT / 'packaging/app.manifest')
        assembly = '{urn:schemas-microsoft-com:asm.v1}'
        identity = manifest.find(f'{assembly}dependency/{assembly}dependentAssembly/{assembly}assemblyIdentity')
        self.assertIsNotNone(identity)
        self.assertEqual(identity.attrib['name'], 'Microsoft.Windows.Common-Controls')
        self.assertEqual(identity.attrib['version'], '6.0.0.0')
        self.assertEqual(identity.attrib['processorArchitecture'], 'amd64')
        level = manifest.find('.//{urn:schemas-microsoft-com:asm.v3}requestedExecutionLevel')
        self.assertEqual(level.attrib, {'level': 'asInvoker', 'uiAccess': 'false'})

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
        required = {ci.CONSOLE_EXECUTABLES.get(name, name) for name, _ in ci.NATIVE_CONSOLE_TESTS}
        self.assertEqual(built_tests, required | {'file_codec_security_probe'})
        runner = (ci.ROOT / 'packaging/run-tests.cmd').read_text(encoding='utf-8')
        for name in built_tests:
            self.assertEqual(ci.BINARY_NAMES.count(name + '.exe'), 1)
            self.assertIn(name + '.exe:', runner, 'Each executable needs a plain purpose label')
        for name in required:
            if name == 'markdown_direct_native':
                self.assertIn('cmd /d /c "set RU_GC_THRESHOLD=64&&set RU_GC_STATS=1&&markdown_direct_native.exe" >>test-results.txt 2>&1\n'
                              'if not "%ERRORLEVEL%"=="0" set "FAILED=1"', runner)
            else:
                self.assertRegex(runner, rf'(?m)^{name}\.exe(?: |$)')
        self.assertIn('call :syntax_fallback missing-lexilla --expect-missing', runner)
        self.assertIn('call :syntax_fallback bad-lexer --expect-bad-lexer', runner)
        self.assertIn('call :syntax_fallback missing-ru-lexilla --expect-missing-lexilla ru_syntax_native', runner)

    def test_unicode_data_notice_matches_reviewed_official_bytes(self):
        source = ci.ROOT / 'packaging/licenses/Unicode.txt'
        self.assertEqual(source.stat().st_size, 1995)
        self.assertEqual(ci.portable.sha(source),
                         'e7a93b009565cfce55919a381437ac4db883e9da2126fa28b91d12732bc53d96')
        self.assertEqual(ci.portable.UNICODE_LICENSE_SHA256, ci.portable.sha(source))
        self.assertEqual(ci.portable.RUNTIME_FILES['packaging/licenses/Unicode.txt'], 'licenses/Unicode.txt')

    def test_build_inventory_sources_and_shared_helpers_exist(self):
        with patch.object(builder, 'ROOT', ci.ROOT):
            snapshot = builder.source_snapshot()
        for name in ci.portable.TEST_NAMES:
            self.assertIn(f'tests/{Path(name).stem}.ru', snapshot)
        for helper in ('tests/drop_fixture.ru', 'tests/file_streaming_native.ru'):
            self.assertIn(helper, snapshot)
        self.assertNotIn('drop_fixture.exe', ci.BINARY_NAMES)
        self.assertIn('src/main.ru', snapshot)
        for relative in snapshot:
            source = ci.ROOT / relative
            for imported in re.findall(r"外言\s+'([^']+)'", source.read_text(encoding='utf-8')):
                if not imported.startswith('如:'):
                    resolved = (source.parent / imported).resolve()
                    self.assertTrue(resolved.is_file(), f'Missing imported source: {relative}')
                    self.assertIn(resolved.relative_to(ci.ROOT).as_posix(), snapshot)

    def test_reviewed_compiler_pin_is_consistent_across_all_build_entrypoints(self):
        commit = '85c7821fda35aa79deeaf67b4d430f24ddd7f07f'
        tree = 'a770e367e84d87a0d2fcb6d49ea6f06da2dbe4ba'
        self.assertEqual(builder.BASELINE_TREE, tree)
        self.assertEqual(ci.HELPER_POLICY_COMMIT, commit)
        self.assertEqual(ci.HELPER_POLICY_TREE, tree)
        script = (ci.ROOT / 'tools/windows_ci.ps1').read_text(encoding='utf-8')
        workflow = (ci.ROOT / '.github/workflows/windows.yml').read_text(encoding='utf-8')
        self.assertIn(f"-ne '{commit}'", script)
        self.assertIn(f"-ne '{tree}'", script)
        self.assertEqual(workflow.count(f'ref: {commit}'), 3)  # two acceptance jobs plus manual growth diagnostic

    def test_new_feature_documentation_links_resolve(self):
        readme = (ci.ROOT / 'README.md').read_text(encoding='utf-8')
        for relative in ('docs/windows_file_entry.md', 'docs/file_streaming_tests.md'):
            self.assertIn(f']({relative})', readme)
            self.assertTrue((ci.ROOT / relative).is_file())

    def test_runner_treats_every_nonzero_status_as_failure_without_shadowing(self):
        runner = (ci.ROOT / 'packaging/run-tests.cmd').read_text(encoding='utf-8')
        self.assertIn('setlocal EnableExtensions DisableDelayedExpansion\nset "ERRORLEVEL="\n', runner)
        self.assertNotIn('if errorlevel 1', runner.lower())
        lines = runner.split('\n:syntax_fallback\n', 1)[0].splitlines()
        commands = [index for index, line in enumerate(lines)
                    if (re.match(r'^[a-z_]+\.exe(?: |$)|^call :syntax_fallback ', line) or
                        line == 'cmd /d /c "set RU_GC_THRESHOLD=64&&set RU_GC_STATS=1&&markdown_direct_native.exe" >>test-results.txt 2>&1')]
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
        (binary / 'ru_syntax_native.exe').write_bytes(b'synthetic Ru executable')
        (binary / 'Scintilla.dll').write_bytes(b'synthetic editor DLL')
        (binary / 'Lexilla.dll').write_bytes(b'synthetic correct lexer DLL')
        (binary / ci.portable.NATIVE_HELPER_NAME).write_bytes(b'synthetic correct native scanner DLL')
        (binary / ci.portable.NATIVE_WRONG_ABI_NAME).write_bytes(b'synthetic wrong ABI scanner DLL')
        events = []
        def preflight(api, library, expected_hash):
            events.append('preflight')
            self.assertEqual(library.read_bytes(), (binary / ci.portable.NATIVE_HELPER_NAME).read_bytes())
            self.assertEqual(ci.sha(library), expected_hash)
            return dict(loadable=True, createlexer_missing=True, released=True, library_sha256=expected_hash)
        def console(api, name, *args, **kwargs):
            events.append(name)
            return {'passed': True}
        with patch.object(ci, 'run_console', side_effect=console) as run, \
             patch.object(ci, 'preflight_wrong_lexer', side_effect=preflight) as probe:
            results = ci.run_syntax_fallbacks(NoDialogs(), binary, fixtures, evidence)
        self.assertEqual(len(results), 6)
        self.assertEqual(events, ['syntax_missing_lexilla', 'preflight', *[case[0] for case in ci.SYNTAX_FALLBACK_TESTS[1:]]])
        probe.assert_called_once()
        self.assertEqual(results[1]['fixture_preflight']['library_sha256'], ci.sha(binary / ci.portable.NATIVE_HELPER_NAME))
        for call, (name, argument, bad) in zip(run.call_args_list, ci.SYNTAX_FALLBACK_TESTS):
            isolated = fixtures / name
            executable = ci.SYNTAX_FALLBACK_EXECUTABLES.get(name, 'syntax_native.exe')
            self.assertEqual(call.kwargs['cwd'], isolated)
            self.assertEqual(call.kwargs['expected_assertions'], 8)
            self.assertEqual(call.args[2], [str(isolated / executable), argument])
            self.assertEqual((isolated / executable).read_bytes(), (binary / executable).read_bytes())
            self.assertEqual((isolated / 'Scintilla.dll').read_bytes(), (binary / 'Scintilla.dll').read_bytes())
            layout = ci.syntax_fallback_layout(name)
            self.assertEqual({path.name for path in isolated.iterdir()}, set(layout))
            for target, source in layout.items():
                self.assertEqual((isolated / target).read_bytes(), (binary / source).read_bytes())

    def test_wrong_lexer_layout_avoids_window_registration_and_matches_portable_runner(self):
        layout = ci.syntax_fallback_layout('syntax_bad_lexer')
        self.assertEqual(layout['Lexilla.dll'], ci.portable.NATIVE_HELPER_NAME)
        self.assertEqual(layout['Scintilla.dll'], 'Scintilla.dll')
        self.assertEqual(layout[ci.portable.NATIVE_HELPER_NAME], ci.portable.NATIVE_HELPER_NAME)
        runner = (ci.ROOT / 'packaging/run-tests.cmd').read_text(encoding='utf-8')
        copies = [line for line in runner.splitlines() if line.startswith('if "%~1"=="bad-lexer" copy /b ')]
        self.assertEqual(copies, ['if "%~1"=="bad-lexer" copy /b "RuSyntax.dll" "%FALLBACKDIR%\\Lexilla.dll" >nul || exit /b 1'])
        source = (ci.ROOT / 'tests/syntax_native.ru').read_text(encoding='utf-8')
        self.assertEqual(source.count(ci.WRONG_LEXER_PREFLIGHT_MARKER), 1)
        self.assertIn("确认 (警告 其 含 'does not export CreateLexer') 'actual wrong DLL is caught before native symbol binding'.", source)
        self.assertNotIn('Production warning:', source)
        self.assertIn("Production import-time preflight has already run", source)
        self.assertIn("若 策 其 含词 参数 '--expect-bad-lexer' 则 验错误词法库. 然", source)
        self.assertEqual(ci.expected_assertions('syntax_bad_lexer'), 8)

    def test_wrong_lexer_loader_preflight_secure_path_lifetime_and_hash(self):
        library = self.root / 'Lexilla.dll'
        library.write_bytes(b'synthetic exact helper bytes')
        digest = ci.sha(library)
        for mode in ('good', 'load-fails', 'export-present', 'release-fails', 'lookup-raises', 'changed'):
            with self.subTest(mode=mode):
                library.write_bytes(b'synthetic exact helper bytes')
                api = Mock()
                api.kernel.LoadLibraryExW.return_value = 0 if mode == 'load-fails' else 17
                api.kernel.GetProcAddress.return_value = 123 if mode == 'export-present' else 0
                api.kernel.FreeLibrary.return_value = 0 if mode == 'release-fails' else 1
                if mode == 'lookup-raises':
                    api.kernel.GetProcAddress.side_effect = RuntimeError('synthetic lookup failure')
                if mode == 'changed':
                    def mutate(_):
                        library.write_bytes(b'changed')
                        return 1
                    api.kernel.FreeLibrary.side_effect = mutate
                if mode in {'lookup-raises', 'changed'}:
                    with self.assertRaises(RuntimeError):
                        ci.preflight_wrong_lexer(api, library, digest)
                else:
                    record = ci.preflight_wrong_lexer(api, library, digest)
                    self.assertEqual(record, dict(loadable=mode != 'load-fails',
                        createlexer_missing=mode not in {'load-fails', 'export-present'},
                        released=mode not in {'load-fails', 'release-fails'}, library_sha256=digest))
                    if mode == 'good': ci.validate_wrong_lexer_preflight(record, digest)
                    else:
                        with self.assertRaises(RuntimeError): ci.validate_wrong_lexer_preflight(record, digest)
                expected = [call.LoadLibraryExW(str(library.resolve()), None, 2304)]
                if mode != 'load-fails':
                    expected += [call.GetProcAddress(17, b'CreateLexer'), call.FreeLibrary(17)]
                self.assertEqual(api.kernel.mock_calls, expected)
        api = Mock()
        with self.assertRaisesRegex(RuntimeError, 'before its loader preflight'):
            ci.preflight_wrong_lexer(api, library, digest)
        self.assertEqual(api.kernel.mock_calls, [])

    def test_wrong_lexer_preflight_failure_never_launches_target(self):
        for mode in ('loadable', 'createlexer_missing', 'released', 'exception'):
            with self.subTest(mode=mode):
                root = self.root / mode
                binary, fixtures, evidence = (root / name for name in ('bin', 'fixtures', 'evidence'))
                for folder in (binary, fixtures, evidence): folder.mkdir(parents=True)
                for name in set(ci.syntax_fallback_layout('syntax_bad_lexer').values()):
                    (binary / name).write_bytes(name.encode())
                record = dict(loadable=True, createlexer_missing=True, released=True,
                              library_sha256=ci.sha(binary / ci.portable.NATIVE_HELPER_NAME))
                if mode != 'exception': record[mode] = False
                with patch.object(ci, 'SYNTAX_FALLBACK_TESTS', (('syntax_bad_lexer', '--expect-bad-lexer', True),)), \
                     patch.object(ci, 'preflight_wrong_lexer', return_value=record,
                         side_effect=RuntimeError('synthetic private-path sentinel') if mode == 'exception' else None), \
                     patch.object(ci, 'run_console') as run:
                    result, = ci.run_syntax_fallbacks(NoDialogs(), binary, fixtures, evidence)
                run.assert_not_called()
                self.assertIs(result['passed'], False)
                self.assertIs(result['executed'], False)
                self.assertEqual(result['error'], 'Wrong-lexer fixture OS preflight failed')
                self.assertNotIn('private-path', json.dumps(result))
                if mode != 'exception': self.assertEqual(result['fixture_preflight'], record)

    def test_wrong_lexer_native_marker_is_exact_unique_and_exclusive(self):
        marker = ci.WRONG_LEXER_PREFLIGHT_MARKER
        cases = [('good', 'syntax_bad_lexer', marker, ''),
                 ('missing', 'syntax_bad_lexer', '', ''),
                 ('duplicate', 'syntax_bad_lexer', marker + '\n' + marker, ''),
                 ('false', 'syntax_bad_lexer', marker.replace('released=1', 'released=0'), ''),
                 ('stderr', 'syntax_bad_lexer', marker, marker),
                 ('wrong-case', 'syntax_missing_lexilla', marker, ''),
                 ('prefixed', 'syntax_missing_lexilla', 'extra ' + marker, '')]
        for label, name, text, error in cases:
            with self.subTest(label=label):
                evidence = self.root / label
                evidence.mkdir()
                stdout = text + '\n' + 'PASS: synthetic\n' * 8 + 'TOTAL PASS: 8\n'
                code = f'import sys; print({stdout!r}); sys.stderr.write({error!r})'
                with patch.object(ci, 'cleanup_process', side_effect=kill_synthetic):
                    result = ci.run_console(NoDialogs(), name, [sys.executable, '-c', code],
                        evidence, r'^TOTAL PASS: 8\s*$', expected_assertions=8)
                self.assertEqual(result['passed'], label == 'good')
                self.assertEqual(result.get('native_fixture_preflight'), True if label == 'good' else None)

    def test_acceptance_requires_both_wrong_lexer_preflights_and_exact_hash(self):
        for field in ('loadable', 'createlexer_missing', 'released', 'library_sha256', 'native_fixture_preflight'):
            for mutation in ('missing', 'false', 'integer'):
                with self.subTest(field=field, mutation=mutation):
                    summary = self.acceptance()
                    record = next(item for item in summary['tests'] if item['name'] == 'syntax_bad_lexer')
                    target = record if field == 'native_fixture_preflight' else record['fixture_preflight']
                    if mutation == 'missing': target.pop(field)
                    else: target[field] = False if mutation == 'false' else 1
                    with self.assertRaisesRegex(RuntimeError, '[Ww]rong-lexer'):
                        ci.validate_acceptance(summary)
        for field in ('fixture_preflight', 'native_fixture_preflight'):
            summary = self.acceptance()
            target = next(item for item in summary['tests'] if item['name'] == 'syntax_missing_lexilla')
            target[field] = True
            with self.assertRaisesRegex(RuntimeError, 'Unexpected wrong-lexer'):
                ci.validate_acceptance(summary)

    def acceptance(self):
        summary = {'acl_requested': True, 'tests': [],
                   'tested_binary_sha256': {name: name + '-hash' for name in ci.BINARY_NAMES}}
        summary['scanner_preflight'] = self.scanner_record(ci.ROOT, summary['tested_binary_sha256'])
        names = [name for name, _ in ci.NATIVE_CONSOLE_TESTS] + [case[0] for case in ci.SYNTAX_FALLBACK_TESTS] + ['file_codec_security', *sorted(ci.GUI_NAMES)]
        for name in names:
            result = {'name': name, 'passed': True, 'executed': True, 'cleanup_killed': False,
                      'exit_code': 0, 'skips': []}
            if name in ci.GUI_NAMES:
                result.update(main_hwnd_seen=True, close_posted=True, detached_from_console=True)
            else:
                result['assertions_passed'] = ci.expected_assertions(name)
            if name == 'markdown_direct_native':
                result['gc_stress'] = {'threshold': 64, 'stats_enabled': True,
                                       'live': 0, 'freed': 100, 'collections': 4}
                result['bulk_route_metrics'] = markdown_route_metrics()
            if name == 'ru_syntax_native':
                result['performance'] = [{'size': size, 'initial_read_bytes': size,
                    'edit_read_bytes': 1024, 'reused_bytes': size - 1024, 'max_read': 1024,
                    'initial_ms': 100.0, 'edit_ms': 2.0, 'max_tick_ms': 3.0, 'max_chunk_ms': 1.0}
                    for size in ci.RU_PERFORMANCE_SIZES]
            if name in ci.RU_GUI_CONSOLE_MEASUREMENTS:
                marker, key = ci.RU_GUI_CONSOLE_MEASUREMENTS[name]
                result[key] = ci.parse_ru_gui_measurement(self.ru_gui_measurement_text(marker), marker)
            if name in {case[0] for case in ci.SYNTAX_FALLBACK_TESTS}:
                result['fixture_binary_sha256'] = {target: summary['tested_binary_sha256'][source]
                                                  for target, source in ci.syntax_fallback_layout(name).items()}
            if name == 'syntax_bad_lexer':
                result['fixture_preflight'] = dict(loadable=True, createlexer_missing=True, released=True,
                    library_sha256=summary['tested_binary_sha256'][ci.portable.NATIVE_HELPER_NAME])
                result['native_fixture_preflight'] = True
            if name == 'main-gui-markdown':
                result.update({key: True for key in ci.GUI_MARKDOWN_CHECKS})
                result['markdown_performance'] = markdown_evidence()
                result['fixture_binary_sha256'] = {binary: summary['tested_binary_sha256'][binary]
                    for binary in ci.portable.RUNTIME_NAMES}
            if name in {'main-gui-file-entry', 'main-gui-ru-syntax'}:
                checks = ci.GUI_FILE_CHECKS if name == 'main-gui-file-entry' else ci.GUI_RU_CHECKS
                result.update({key: True for key in checks})
                result['fixture_binary_sha256'] = {binary: summary['tested_binary_sha256'][binary]
                                                  for binary in ci.portable.RUNTIME_NAMES}
            if name == 'main-gui-ru-syntax':
                data, probes = ci.gui_ru_timer_fixture()
                result['timer_performance'] = {'size': len(data), 'wall_ms': 100.0,
                    'first_head_style_ms': 10.0, 'max_response_ms': 2.0, 'probes': 3,
                    'source_sha256': hashlib.sha256(data).hexdigest(), 'style_probes': probes,
                    'responsiveness': {'measurement': ci.GUI_RU_RESPONSE_MEASUREMENT,
                        'navigation': [dict(step, wall_ms=1.0, while_styling=True) for step in ci.GUI_RU_NAVIGATION],
                        'paint': {'invalidations': 1, 'pending_observed': True, 'already_serviced': False,
                                  'cleared': True, 'wall_ms': 2.0, 'while_styling': True}},
                    'last_probe': {'opened': True, 'length': len(data), 'clean': True,
                        'end_styled': len(data), 'status': 'Ln 1    UTF-8    Ru',
                        'style_matches': {name: True for name in probes}}}
                result['timer_performance'].update(observer_evidence())
                edit_data, edit_probes, edit_folds, _ = ci.gui_ru_edit_fixture()
                result['edit_performance'] = {'size': len(edit_data), 'source_sha256': hashlib.sha256(edit_data).hexdigest(),
                    'style_probes': edit_probes, 'fold_probes': edit_folds, 'undo_commands': 6,
                    'measurement': ci.GUI_RU_EDIT_MEASUREMENT,
                    'operations': [dict(operation, wall_ms=100.0, max_response_ms=1.0, probes=2)
                                   for operation in ci.gui_ru_edit_operations()]}
            summary['tests'].append(result)
        return summary

    def scanner_record(self, root, hashes):
        sources = ci.scanner_preflight_sources(root)
        return {'name': ci.portable.SCANNER_PREFLIGHT_NAME, 'passed': True, 'executed': True,
                'cleanup_killed': False, 'exit_code': 0, 'source_sha256': sources,
                'report': {'cases': 157, 'chunk_checks': 942, 'ru_assertions_per_backend': 0, 'sanitizer': None,
                    'library_sha256': hashes[ci.portable.NATIVE_HELPER_NAME],
                    'source_sha256': sources['native/ru_scan.c']}}

    def test_scanner_preflight_is_mandatory_and_binds_exact_counts_dll_and_sources(self):
        for mutation in ('missing', 'failed', 'unexecuted', 'killed', 'exit', 'wrong-cases',
                         'wrong-chunks', 'unexpected-differential', 'wrong-dll', 'wrong-source',
                         'wrong-script', 'missing-report', 'extra-report', 'host-sanitizer'):
            with self.subTest(mutation=mutation):
                summary = self.acceptance()
                record = summary['scanner_preflight']
                if mutation == 'missing': summary.pop('scanner_preflight')
                if mutation == 'failed': record['passed'] = False
                if mutation == 'unexecuted': record['executed'] = False
                if mutation == 'killed': record['cleanup_killed'] = True
                if mutation == 'exit': record['exit_code'] = 1
                if mutation == 'wrong-cases': record['report']['cases'] = 156
                if mutation == 'wrong-chunks': record['report']['chunk_checks'] = 941
                if mutation == 'unexpected-differential': record['report']['ru_assertions_per_backend'] = 314
                if mutation == 'wrong-dll': record['report']['library_sha256'] = 'different'
                if mutation == 'wrong-source': record['report']['source_sha256'] = 'different'
                if mutation == 'wrong-script': record['source_sha256']['tools/test_ru_scan.py'] = 'different'
                if mutation == 'missing-report': record.pop('report')
                if mutation == 'extra-report': record['report']['unreviewed'] = True
                if mutation == 'host-sanitizer': record['report']['sanitizer'] = ci.SCANNER_SANITIZER_SUCCESS
                with self.assertRaisesRegex(RuntimeError, 'scanner preflight'):
                    ci.validate_acceptance(summary)

    def scanner_preflight(self, mode='normal'):
        for relative in (*ci.SCANNER_PREFLIGHT_SOURCES, 'native/ru_scan.c',
                         'native/ru_wrong_abi.c', 'native/ru_scan.h', 'native/ru_unicode_data.h',
                         'native/ru_markdown_fold.c', 'native/ru_markdown_fold.h'):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('synthetic fixture\n')
        binary, evidence = self.root / 'bin', self.root / 'evidence'
        binary.mkdir(); evidence.mkdir()
        library = binary / ci.portable.NATIVE_HELPER_NAME
        library.write_bytes(b'synthetic DLL')
        record = self.scanner_record(self.root, {ci.portable.NATIVE_HELPER_NAME: ci.sha(library)})
        code = "import sys\nassert sys.argv[1:] == " + repr(['--library', str(library), '--fuzz', '100']) + '\n'
        if mode == 'wrong-count': record['report']['chunk_checks'] -= 1
        if mode == 'wrong-dll': record['report']['library_sha256'] = 'different'
        if mode == 'malformed': code += "print('not JSON')\n"
        elif mode == 'overflow': code += f"print('x' * {ci.MAX_LOG_BYTES + 1})\n"
        else: code += 'print(' + repr(json.dumps(record['report'])) + ')\n'
        if mode == 'stderr': code += "print('unexpected diagnostic', file=sys.stderr)\n"
        if mode == 'exit': code += 'sys.exit(1)\n'
        if mode == 'changed-source':
            code += 'from pathlib import Path\nPath(' + repr(str(self.root / 'native/ru_scan.h')) + ").write_text('changed')\n"
        if mode == 'timeout': code += 'import time\ntime.sleep(120)\n'
        (self.root / 'tools/test_ru_scan.py').write_text(code)
        with patch.object(ci, 'ROOT', self.root), patch.object(ci, 'cleanup_process', side_effect=kill_synthetic):
            if mode == 'timeout':
                with patch.object(ci.time, 'perf_counter', side_effect=iter((0, 181, 182))):
                    result = ci.run_scanner_preflight(NoDialogs(), binary, evidence)
            else:
                result = ci.run_scanner_preflight(NoDialogs(), binary, evidence)
        return result, library, evidence

    def test_scanner_preflight_runs_exact_library_and_collects_bounded_outputs(self):
        result, library, evidence = self.scanner_preflight()
        self.assertTrue(result['passed'], result.get('error'))
        ci.validate_scanner_preflight(result, {ci.portable.NATIVE_HELPER_NAME: ci.sha(library)}, self.root)
        for stream in ('stdout', 'stderr'):
            self.assertTrue((evidence / (ci.portable.SCANNER_PREFLIGHT_NAME + '.' + stream + '.log')).is_file())

    def test_scanner_preflight_fails_closed_for_report_exit_timeout_mutation_and_output_errors(self):
        for mode in ('wrong-count', 'wrong-dll', 'malformed', 'overflow', 'stderr', 'exit',
                     'changed-source', 'timeout'):
            with self.subTest(mode=mode):
                for path in self.root.iterdir():
                    if path.is_dir(): shutil.rmtree(path)
                    else: path.unlink()
                result, _, evidence = self.scanner_preflight(mode)
                self.assertFalse(result['passed'])
                self.assertIn('error', result)
                for path in evidence.iterdir(): self.assertLessEqual(path.stat().st_size, ci.MAX_LOG_BYTES)
                if mode == 'timeout': self.assertTrue(result['cleanup_killed'])

    def helper_policy_fixture(self):
        directory = self.root / 'build/logs/014/ru-scan'
        inputs = {'ru_commit': ci.HELPER_POLICY_COMMIT, 'ru_tree': ci.HELPER_POLICY_TREE,
                  'baseline_commit': ci.POLICY_PREFIX_BASELINE_COMMIT,
                  'baseline_tree': ci.POLICY_PREFIX_BASELINE_TREE,
                  'baseline_source_sha256': ci.POLICY_PREFIX_BASELINE_SHA256,
                  'source_sha256': {'native/ru_scan.c': 'c' * 64, 'tools/test_ru_scan.py': 'd' * 64,
                      'src/ru_lexical.ru': 'e' * 64,
                      **{name: 'f' * 64 for name in ci.POLICY_PREFIX_SOURCES}}}
        proof_dir = self.root / 'build/policy-fast'
        proof_dir.mkdir(parents=True)
        for name in ci.POLICY_PREFIX_EVIDENCE_LIMITS:
            (proof_dir / name).write_text('{}\n', encoding='utf-8', newline='\n')
        # This suite tests the outer orchestration contract. The proof verifier
        # has its own real ordered-transcript/manifest negative controls.
        import verify_ru_policy_fast_outputs as policy_proof
        self.prefix_validator = self.enterContext(patch.object(
            policy_proof, 'validate_public_evidence', return_value={'status': 'passed'}, create=True))
        with patch.object(ci, 'helper_policy_inputs', return_value=inputs):
            ci.helper_policy_action('prepare', self.root)
        (directory / 'libRuSyntax.so').write_bytes(b'synthetic host library')
        report = {'cases': 157, 'chunk_checks': 942, 'ru_assertions_per_backend': 314,
                  'sanitizer': ci.SCANNER_SANITIZER_SUCCESS,
                  'source_sha256': inputs['source_sha256']['native/ru_scan.c'],
                  'library_sha256': ci.sha(directory / 'libRuSyntax.so')}
        for name in ci.HELPER_POLICY_EVIDENCE_FILES:
            (directory / name).write_text('')
        for name in ('report.json', 'helper-policy.stdout.log'):
            (directory / name).write_text(json.dumps(report))
        for name in ('differential-python.log', 'differential-c.log'):
            (directory / name).write_text('PASS: fixture\n' * 314 + 'TOTAL PASS: 314\n')
        (directory / 'sanitize.log').write_text(ci.SCANNER_SANITIZER_SUCCESS + '\n')
        (directory / 'cleanup-control.stdout.log').write_text(
            'BACKEND: python\n' + 'PASS: fixture\n' * 8 + 'TOTAL PASS: 8\n' +
            'BACKEND: c\n' + 'PASS: fixture\n' * 8 + 'TOTAL PASS: 8\n' +
            'PASS: production cleanup rescue bodies and original scalar negative controls in both Ru backends\n')
        (directory / 'timer-corpus.stdout.log').write_text(''.join(
            f'PASS: {backend} {fixture} exact UTF-8 corpus\n'
            for fixture in ('ru_syntax_native', 'app_ru_native') for backend in ('python', 'c')) +
            'RU_TIMER_CORPUS_PASS: 4\n')
        import test_syntax_diagnostics as diagnostic_control
        base = dict(zip(diagnostic_control.FIELDS, [1, 1, 9, 2, 1, 123, 124, 128, 0, 4, 5,
            1.5, 2.25, 0.75, 1.25, 7, 6, 8, 1, 3, 0, 0]))
        records = [base, {'seq': 2, 'ok': 0}, {**base, 'seq': 3, 'pending': 0}, {'seq': 1, 'ok': 0}]
        body = 'PASS: fixture\n' * 10 + ''.join('RU_GUI_SNAPSHOT ' +
            ' '.join(f'{key}={value}' for key, value in record.items()) + '\n' for record in records) + 'TOTAL PASS: 10\n'
        (directory / 'diagnostic-control.stdout.log').write_text('BACKEND: python\n' + body +
            'BACKEND: c\n' + body + 'RU_DIAGNOSTIC_PORTABLE_PASS: 2\n')
        bulk_body = ''.join(f'PASS: {label}\n' for label in ci.BULK_EVENT_CASES) + 'TOTAL PASS: 23\n'
        (directory / 'event-bulk.stdout.log').write_text('BACKEND: python\n' + bulk_body +
            'BACKEND: c\n' + bulk_body + 'RU_EVENT_BULK_PORTABLE_PASS: 2 backends, 23 assertions each\n')
        (directory / 'policy-prefix.stdout.log').write_text(ci.POLICY_PREFIX_EXECUTION_SUCCESS, encoding='utf-8', newline='\n')
        (directory / 'policy-prefix-order.stdout.log').write_text(ci.POLICY_PREFIX_ORDER_SUCCESS, encoding='utf-8', newline='\n')
        (directory / 'bridge-failure.stdout.log').write_text('RU_SYNTAX_FAILURE_PORTABLE_PASS: 6\n')
        (directory / 'bridge-failure.stderr.log').write_text('Ran 6 tests in 1.000s\n\nOK\n')
        return directory, inputs

    def test_linux_helper_policy_requires_clean_pinned_compiler_and_snapshots(self):
        for values in ((ci.HELPER_POLICY_COMMIT, ci.HELPER_POLICY_TREE, ''),
                       ('wrong', ci.HELPER_POLICY_TREE, ''),
                       (ci.HELPER_POLICY_COMMIT, 'wrong', ''),
                       (ci.HELPER_POLICY_COMMIT, ci.HELPER_POLICY_TREE, ' M compiler.py')):
            with self.subTest(values=values), \
                 patch.object(ci.subprocess, 'check_output', side_effect=values), \
                 patch.object(ci, 'scanner_preflight_sources', return_value={}), \
                 patch.object(ci, 'helper_policy_baseline', return_value={}):
                if values == (ci.HELPER_POLICY_COMMIT, ci.HELPER_POLICY_TREE, ''):
                    result = ci.helper_policy_inputs(ci.ROOT)
                    self.assertEqual(result['ru_commit'], ci.HELPER_POLICY_COMMIT)
                    self.assertIn('.github/workflows/windows.yml', result['source_sha256'])
                    self.assertIn('tools/test_ru_timer_corpus.py', result['source_sha256'])
                    self.assertIn('tests/app_ru_native.ru', result['source_sha256'])
                    self.assertIn('tests/ru_event_bulk_portable.py', result['source_sha256'])
                    self.assertIn('src/ru_native_syntax.ru', result['source_sha256'])
                    self.assertIn('tools/ru_cli_diagnostics.py', result['source_sha256'])
                    self.assertIn('tools/test_ru_cli_diagnostics.py', result['source_sha256'])
                else:
                    with self.assertRaisesRegex(RuntimeError, 'clean reviewed'):
                        ci.helper_policy_inputs(ci.ROOT)

    def test_linux_helper_policy_verifies_both_oracles_and_sanitizer_then_collects_only_bounded_logs(self):
        directory, inputs = self.helper_policy_fixture()
        with patch.object(ci, 'helper_policy_inputs', return_value=inputs):
            result = ci.helper_policy_action('verify', self.root)
            self.assertTrue(result['passed'])
            with self.assertRaises(FileExistsError):
                ci.helper_policy_action('prepare', self.root)
        for name in ('differential.ru', 'sanitize.c', 'private-source.txt'):
            (directory / name).write_text('DO NOT UPLOAD')
        (directory / 'helper-policy.stderr.log').write_bytes(b'x' * (ci.MAX_LOG_BYTES + 1))
        ci.helper_policy_action('collect', self.root)
        destination = self.root / 'build/helper-policy-evidence'
        expected = {*ci.HELPER_POLICY_EVIDENCE_FILES, 'helper-policy-inputs.json', 'helper-policy-acceptance.json',
                    *('policy-prefix-' + name for name in ci.POLICY_PREFIX_EVIDENCE_LIMITS),
                    'policy-prefix-collection.json'}
        self.assertEqual({path.name for path in destination.iterdir()}, expected)
        for path in destination.iterdir(): self.assertLessEqual(path.stat().st_size, ci.MAX_LOG_BYTES)

    def test_policy_prefix_fixture_preserves_linux_wrapper_bytes_under_windows_default_newlines(self):
        original_write_text = Path.write_text
        def windows_default_write(path, text, encoding=None, errors=None, newline=None):
            return original_write_text(path, text, encoding=encoding, errors=errors,
                                       newline='\r\n' if newline is None else newline)
        with patch.object(Path, 'write_text', windows_default_write):
            directory, _ = self.helper_policy_fixture()
        expected = {'policy-prefix.stdout.log': ci.POLICY_PREFIX_EXECUTION_SUCCESS,
                    'policy-prefix-order.stdout.log': ci.POLICY_PREFIX_ORDER_SUCCESS}
        for name, marker in expected.items():
            self.assertEqual((directory / name).read_bytes(), marker.encode('utf-8'))
        ci.helper_policy_action('collect', self.root)
        destination = self.root / 'build/helper-policy-evidence'
        record = json.loads((destination / 'policy-prefix-collection.json').read_text(encoding='utf-8'))
        self.assertTrue(record['complete_proof_verified'])
        for name in ci.POLICY_PREFIX_EVIDENCE_LIMITS:
            self.assertEqual((destination / ('policy-prefix-' + name)).read_bytes(),
                             (self.root / 'build/policy-fast' / name).read_bytes())
        # The original implicit Windows newline mutation remains rejected. The
        # collector must not normalize a noncanonical public wrapper to success.
        shutil.rmtree(destination)
        for name, marker in expected.items():
            (directory / name).write_bytes(marker.replace('\n', '\r\n').encode('utf-8'))
        ci.helper_policy_action('collect', self.root)
        record = json.loads((destination / 'policy-prefix-collection.json').read_text(encoding='utf-8'))
        self.assertFalse(record['complete_proof_verified'])
        for name in expected:
            self.assertEqual(record['wrappers'][name]['status'], 'withheld_invalid_output')
            self.assertFalse((destination / name).exists())
        for name in ci.POLICY_PREFIX_EVIDENCE_LIMITS:
            self.assertFalse((destination / ('policy-prefix-' + name)).exists())

    def test_policy_prefix_requires_exact_clean_public_baseline_and_source(self):
        baseline = self.root / '.ci/policy-baseline'
        (baseline / 'src').mkdir(parents=True)
        (baseline / 'src/ru_lexical.ru').write_text('synthetic policy', encoding='utf-8')
        good = (ci.POLICY_PREFIX_BASELINE_COMMIT, ci.POLICY_PREFIX_BASELINE_TREE, '')
        for values, digest in ((good, ci.POLICY_PREFIX_BASELINE_SHA256),
                               (('wrong', good[1], ''), ci.POLICY_PREFIX_BASELINE_SHA256),
                               ((good[0], 'wrong', ''), ci.POLICY_PREFIX_BASELINE_SHA256),
                               ((good[0], good[1], ' M src/ru_lexical.ru'), ci.POLICY_PREFIX_BASELINE_SHA256),
                               (good, '0' * 64)):
            with self.subTest(values=values, digest=digest), \
                 patch.object(ci.subprocess, 'check_output', side_effect=values), \
                 patch.object(ci, 'sha', return_value=digest):
                if values == good and digest == ci.POLICY_PREFIX_BASELINE_SHA256:
                    self.assertEqual(ci.helper_policy_baseline(self.root), {
                        'baseline_commit': good[0], 'baseline_tree': good[1],
                        'baseline_source_sha256': digest})
                else:
                    with self.assertRaisesRegex(RuntimeError, 'clean reviewed public baseline'):
                        ci.helper_policy_baseline(self.root)

    def test_policy_prefix_orchestration_binds_exact_sources_and_all_eight_files(self):
        directory, inputs = self.helper_policy_fixture()
        with patch.object(ci, 'helper_policy_inputs', return_value=inputs):
            result = ci.helper_policy_action('verify', self.root)
        self.assertEqual(result['policy_prefix'], {'status': 'passed'})
        self.prefix_validator.assert_called_once_with(
            self.root / 'build/policy-fast', ci.policy_prefix_expected_inputs(inputs))
        self.assertEqual(set(ci.policy_prefix_expected_inputs(inputs)), {
            'baseline_commit', 'baseline_tree', 'baseline_source_sha256',
            'toolchain_commit', 'toolchain_tree', 'candidate_sha256',
            'test_script_sha256', 'verifier_source_sha256', 'canonical_plan_sha256'})
        workflow = (ci.ROOT / '.github/workflows/windows.yml').read_text(encoding='utf-8')
        for required in ('ref: ' + ci.POLICY_PREFIX_BASELINE_COMMIT,
                         'path: .ci/policy-baseline',
                         'python -I tools/test_ru_policy_fast.py --baseline .ci/policy-baseline --ru-root .ci/ru-language',
                         'python -I tools/verify_ru_policy_fast_outputs.py'):
            self.assertIn(required, workflow)

    def test_policy_prefix_orchestration_rejects_missing_oversized_stderr_and_verifier_failure(self):
        for mutation in (*ci.POLICY_PREFIX_EVIDENCE_LIMITS, 'oversized', 'wrapper-oversized',
                         'stderr', 'order-stderr', 'verification-failed'):
            with self.subTest(mutation=mutation):
                shutil.rmtree(self.root / 'build', ignore_errors=True)
                directory, inputs = self.helper_policy_fixture()
                if mutation in ci.POLICY_PREFIX_EVIDENCE_LIMITS:
                    (self.root / 'build/policy-fast' / mutation).unlink()
                elif mutation == 'oversized':
                    (self.root / 'build/policy-fast/report.json').write_bytes(b'x' * (64 * 1024 + 1))
                elif mutation == 'wrapper-oversized':
                    (directory / 'policy-prefix.stdout.log').write_bytes(b'x' * (64 * 1024 + 1))
                elif mutation == 'stderr':
                    (directory / 'policy-prefix.stderr.log').write_text('unexpected', encoding='utf-8')
                elif mutation == 'order-stderr':
                    (directory / 'policy-prefix-order.stderr.log').write_text('unexpected', encoding='utf-8')
                else:
                    self.prefix_validator.side_effect = ValueError('synthetic rejected transcript')
                with patch.object(ci, 'helper_policy_inputs', return_value=inputs), \
                     self.assertRaises((RuntimeError, ValueError, OSError)):
                    ci.helper_policy_action('verify', self.root)
                self.assertFalse((directory / 'helper-policy-acceptance.json').exists())

    def test_policy_prefix_collector_refuses_linked_or_oversized_proof_and_excludes_private_outputs(self):
        directory, inputs = self.helper_policy_fixture()
        proof = self.root / 'build/policy-fast'
        for name in ('differential-0', 'differential-0.c', 'private-source.ru'):
            (proof / name).write_text('DO NOT PUBLISH', encoding='utf-8')
        ci.helper_policy_action('collect', self.root)
        files = {p.name for p in (self.root / 'build/helper-policy-evidence').iterdir()}
        self.assertTrue(all('policy-prefix-' + name in files for name in ci.POLICY_PREFIX_EVIDENCE_LIMITS))
        self.assertFalse(any('differential' in name and name.startswith('policy-prefix-') for name in files))
        shutil.rmtree(self.root / 'build/helper-policy-evidence')
        (proof / 'report.json').write_bytes(b'x' * (64 * 1024 + 1))
        ci.helper_policy_action('collect', self.root)
        collection = json.loads((self.root / 'build/helper-policy-evidence/policy-prefix-collection.json').read_text(encoding='utf-8'))
        self.assertFalse(collection['complete_proof_verified'])
        self.assertEqual(collection['files']['report.json']['status'], 'invalid_or_over_budget')
        self.assertFalse((self.root / 'build/helper-policy-evidence/policy-prefix-report.json').exists())
        with self.assertRaisesRegex(RuntimeError, 'Unexpected'):
            ci.policy_prefix_evidence_file(self.root, '../private-source.ru')
        if os.name != 'nt':
            shutil.rmtree(proof)
            outside = self.root / 'outside-proof'
            outside.mkdir()
            (outside / 'report.json').write_text('{}', encoding='utf-8')
            proof.symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(RuntimeError, 'linked'):
                ci.policy_prefix_evidence_file(self.root, 'report.json')

    def test_policy_prefix_failed_compiler_text_is_withheld_from_public_artifact(self):
        directory, inputs = self.helper_policy_fixture()
        private = 'PRIVATE_COMPILER_SOURCE /workspace/private/source.ru:12 secret_fragment'
        (directory / 'policy-prefix.stderr.log').write_text(private, encoding='utf-8')
        (self.root / 'build/policy-fast/interpreter.log').write_text(private, encoding='utf-8')
        self.prefix_validator.side_effect = ValueError(private)
        ci.helper_policy_action('collect', self.root)
        destination = self.root / 'build/helper-policy-evidence'
        self.assertFalse((destination / 'policy-prefix.stderr.log').exists())
        self.assertFalse((destination / 'policy-prefix-interpreter.log').exists())
        for path in destination.iterdir():
            self.assertNotIn('PRIVATE_COMPILER_SOURCE', path.read_text(encoding='utf-8'))
            self.assertNotIn('/workspace/private', path.read_text(encoding='utf-8'))
        record = json.loads((destination / 'policy-prefix-collection.json').read_text(encoding='utf-8'))
        self.assertFalse(record['complete_proof_verified'])
        self.assertEqual(record['wrappers']['policy-prefix.stderr.log']['status'], 'withheld_invalid_output')
        self.assertEqual(record['files']['interpreter.log']['sha256'], hashlib.sha256(private.encode()).hexdigest())

    def test_policy_prefix_collection_bounds_reads_and_withholds_changed_snapshot(self):
        directory, inputs = self.helper_policy_fixture()
        with patch.object(Path, 'open', return_value=io.BytesIO(b'x' * (64 * 1024 + 1))):
            with self.assertRaisesRegex(RuntimeError, 'grew beyond'):
                ci.policy_prefix_evidence_bytes(self.root, 'report.json')
        def changed_after_validation(*args):
            (self.root / 'build/policy-fast/interpreter.log').write_text('changed', encoding='utf-8')
            return {'status': 'passed'}
        self.prefix_validator.side_effect = changed_after_validation
        ci.helper_policy_action('collect', self.root)
        destination = self.root / 'build/helper-policy-evidence'
        record = json.loads((destination / 'policy-prefix-collection.json').read_text(encoding='utf-8'))
        self.assertFalse(record['complete_proof_verified'])
        self.assertFalse((destination / 'policy-prefix-interpreter.log').exists())

    def test_policy_prefix_wrapper_failure_grammar_preserves_only_fixed_diagnostics(self):
        for name in ci.POLICY_PREFIX_WRAPPER_LOGS:
            success = ci.POLICY_PREFIX_ORDER_SUCCESS if '-order.' in name else ci.POLICY_PREFIX_EXECUTION_SUCCESS
            self.assertTrue(ci.policy_prefix_wrapper_valid(name, '' if 'stderr' in name else success, True))
            self.assertFalse(ci.policy_prefix_wrapper_valid(name, 'unexpected source text', False))
        error = 'POLICY_FAST_FAIL stage=host-c-0 code=command detail_sha256=' + 'a' * 64 + '\n'
        self.assertTrue(ci.policy_prefix_wrapper_valid('policy-prefix.stderr.log', error, False))
        self.assertFalse(ci.policy_prefix_wrapper_valid('policy-prefix.stderr.log', error, True))
        self.assertFalse(ci.policy_prefix_wrapper_valid('policy-prefix.stderr.log', error + error, False))
        self.assertFalse(ci.policy_prefix_wrapper_valid('policy-prefix.stdout.log', '', True))
        self.assertFalse(ci.policy_prefix_wrapper_valid('policy-prefix.stderr.log', error.replace('host-c-0', 'private-source-name'), False))
        self.assertFalse(ci.policy_prefix_wrapper_valid('policy-prefix-order.stderr.log', error.replace('POLICY_FAST_FAIL', 'POLICY_FAST_VERIFY_FAIL'), False))

    def test_linux_helper_policy_rejects_missing_or_partial_differential_sanitizer_and_source_results(self):
        for mutation in ('missing', 'wrong-count', 'wrong-library', 'wrong-source', 'changed-inputs',
                         'missing-sanitizer', 'partial-sanitizer', 'sanitizer-error', 'missing-python', 'missing-c',
                         'extra-total', 'failed-case', 'skipped-case', 'unexpected-stderr', 'oversize',
                         'missing-cleanup', 'partial-cleanup', 'cleanup-error',
                         'missing-bridge', 'partial-bridge', 'skipped-bridge',
                         'missing-corpus', 'partial-corpus', 'duplicate-corpus', 'corpus-stderr',
                         'wrong-corpus-backend', 'trailing-corpus'):
            with self.subTest(mutation=mutation):
                shutil.rmtree(self.root / 'build', ignore_errors=True)
                directory, inputs = self.helper_policy_fixture()
                report = json.loads((directory / 'report.json').read_text())
                if mutation == 'missing': (directory / 'report.json').unlink()
                if mutation == 'wrong-count': report['chunk_checks'] = 941
                if mutation == 'wrong-library': report['library_sha256'] = 'different'
                if mutation == 'wrong-source': report['source_sha256'] = 'different'
                if mutation == 'missing-sanitizer': report['sanitizer'] = None
                if mutation == 'partial-sanitizer':
                    report['sanitizer'] = ci.SCANNER_SANITIZER_SUCCESS + ' (LSan disabled by caller)'
                    (directory / 'sanitize.log').write_text(report['sanitizer'])
                if mutation == 'changed-inputs': inputs = dict(inputs, ru_tree='different')
                if mutation in ('wrong-count', 'wrong-library', 'wrong-source', 'missing-sanitizer', 'partial-sanitizer'):
                    for name in ('report.json', 'helper-policy.stdout.log'):
                        (directory / name).write_text(json.dumps(report))
                if mutation == 'sanitizer-error': (directory / 'sanitize.log').write_text('runtime error: bad memory\n' + ci.SCANNER_SANITIZER_SUCCESS)
                if mutation == 'missing-python': (directory / 'differential-python.log').write_text('TOTAL PASS: 314\n')
                if mutation == 'missing-c': (directory / 'differential-c.log').unlink()
                if mutation in ('extra-total', 'failed-case', 'skipped-case'):
                    with (directory / 'differential-python.log').open('a') as stream:
                        stream.write({'extra-total': 'TOTAL PASS: 314', 'failed-case': 'FAIL: fixture', 'skipped-case': 'SKIP: fixture'}[mutation] + '\n')
                if mutation == 'unexpected-stderr': (directory / 'helper-policy.stderr.log').write_text('error')
                if mutation == 'oversize': (directory / 'scanner-build.log').write_bytes(b'x' * (ci.MAX_LOG_BYTES + 1))
                if mutation == 'missing-cleanup': (directory / 'cleanup-control.stdout.log').unlink()
                if mutation == 'partial-cleanup': (directory / 'cleanup-control.stdout.log').write_text('TOTAL PASS: 8\n')
                if mutation == 'cleanup-error': (directory / 'cleanup-control.stderr.log').write_text('error')
                if mutation == 'missing-corpus': (directory / 'timer-corpus.stdout.log').unlink()
                if mutation == 'partial-corpus': (directory / 'timer-corpus.stdout.log').write_text('RU_TIMER_CORPUS_PASS: 4\n')
                if mutation == 'duplicate-corpus':
                    with (directory / 'timer-corpus.stdout.log').open('a') as stream: stream.write('RU_TIMER_CORPUS_PASS: 4\n')
                if mutation == 'corpus-stderr': (directory / 'timer-corpus.stderr.log').write_text('warning\n')
                if mutation == 'wrong-corpus-backend':
                    path = directory / 'timer-corpus.stdout.log'
                    path.write_text(path.read_text().replace('PASS: c ', 'PASS: python '))
                if mutation == 'trailing-corpus':
                    with (directory / 'timer-corpus.stdout.log').open('a') as stream: stream.write('SKIP: extra\n')
                if mutation == 'missing-bridge': (directory / 'bridge-failure.stdout.log').unlink()
                if mutation == 'partial-bridge': (directory / 'bridge-failure.stdout.log').write_text('RU_SYNTAX_FAILURE_PORTABLE_PASS: 5\n')
                if mutation == 'skipped-bridge': (directory / 'bridge-failure.stderr.log').write_text('Ran 6 tests in 1.000s\nOK (skipped=1)\n')
                with patch.object(ci, 'helper_policy_inputs', return_value=inputs), self.assertRaises(RuntimeError):
                    ci.helper_policy_action('verify', self.root)
                self.assertFalse((directory / 'helper-policy-acceptance.json').exists())

    def test_linux_bulk_event_gate_rejects_missing_partial_duplicate_or_changed_evidence(self):
        for mutation in ('missing', 'stderr', 'partial', 'duplicate', 'backend', 'case', 'count', 'skip', 'extra'):
            with self.subTest(mutation=mutation):
                shutil.rmtree(self.root / 'build', ignore_errors=True)
                directory, inputs = self.helper_policy_fixture()
                path = directory / 'event-bulk.stdout.log'
                text = path.read_text()
                if mutation == 'missing': path.unlink()
                elif mutation == 'stderr': (directory / 'event-bulk.stderr.log').write_text('warning')
                elif mutation == 'partial': path.write_text(text.split('BACKEND: c')[0])
                elif mutation == 'duplicate': path.write_text(text + text)
                elif mutation == 'extra': path.write_text(text + 'unexpected\n')
                else:
                    replacements = {'backend': ('BACKEND: c', 'BACKEND: python'),
                        'case': ('PASS: high word 131072', 'PASS: high word 131071'),
                        'count': ('TOTAL PASS: 23', 'TOTAL PASS: 22'),
                        'skip': ('PASS: zero event batch', 'SKIP: zero event batch')}
                    path.write_text(text.replace(*replacements[mutation]))
                with patch.object(ci, 'helper_policy_inputs', return_value=inputs), self.assertRaises(RuntimeError):
                    ci.helper_policy_action('verify', self.root)
                self.assertFalse((directory / 'helper-policy-acceptance.json').exists())

    def test_workflow_requires_linux_oracle_sanitizer_before_windows_or_package_artifacts(self):
        workflow = (ci.ROOT / '.github/workflows/windows.yml').read_text()
        helper = workflow.split('  helper-policy:\n', 1)[1].split('  windows-native:\n', 1)[0]
        windows = workflow.split('  windows-native:\n', 1)[1]
        self.assertIn('needs: helper-policy', windows)
        self.assertNotIn('continue-on-error', workflow)
        self.assertIn('python -I tools/test_ru_scan.py --ru-root .ci/ru-language --sanitize --fuzz 100', helper)
        self.assertIn('python -I tools/test_ru_timer_corpus.py --ru-root .ci/ru-language', helper)
        self.assertIn('python -I tests/ru_event_bulk_portable.py --ru-root .ci/ru-language', helper)
        self.assertIn('event-bulk.stdout.log', helper)
        self.assertIn('event-bulk.stderr.log', helper)
        for action in ('prepare', 'verify', 'collect'):
            self.assertIn('--helper-policy-action ' + action, helper)
        self.assertIn('ASAN_OPTIONS:', helper)
        self.assertIn('UBSAN_OPTIONS:', helper)
        self.assertIn('path: build/helper-policy-evidence/*', helper)
        self.assertNotIn('path: build/logs/', helper)
        self.assertIn('if: success()', windows)

    def test_acceptance_retains_previous_835_assertions_and_16_policy_additions(self):
        summary = self.acceptance()
        ci.validate_acceptance(summary)
        new = {'ru_lexical_policy', 'ru_syntax_native', 'app_ru_native', 'app_ru_timer_native',
               'ru_direct_styling_native', 'markdown_policy', 'markdown_selection_policy',
               'markdown_native', 'app_markdown_native', 'markdown_direct_native', 'main-gui-markdown',
               'ru_syntax_missing_lexilla', 'main-gui-ru-syntax', *ci.HELPER_FALLBACK_LAYOUTS}
        prior = [test for test in summary['tests'] if test['name'] not in new]
        self.assertEqual(len(prior), 23)
        self.assertEqual(sum(test.get('assertions_passed', 0) for test in prior), 835 + 16 + 90)

    def test_acceptance_preserves_original_33_groups_1487_assertions_and_adds_markdown(self):
        summary = self.acceptance()
        ci.validate_acceptance(summary)
        self.assertEqual(len(summary['tests']), 39)
        added = {'markdown_policy', 'markdown_selection_policy', 'markdown_native',
                 'app_markdown_native', 'markdown_direct_native', 'main-gui-markdown'}
        prior = [test for test in summary['tests'] if test['name'] not in added]
        self.assertEqual(len(prior), 33)
        self.assertEqual(sum(test.get('assertions_passed', 0) for test in prior), 1487 + 90)
        self.assertEqual(sum(test.get('assertions_passed', 0) for test in summary['tests']), 2071)

    def test_direct_style_fixture_is_built_packaged_and_required(self):
        name = 'ru_direct_styling_native'
        self.assertIn(name + '.exe', ci.portable.TEST_NAMES)
        self.assertEqual(ci.console_command(name, self.root, self.root),
                         [str(self.root / (name + '.exe'))])
        self.assertEqual(ci.CONSOLE_TIMEOUT_SECONDS[name], 120)
        script = (ci.ROOT / 'tools/windows_ci.ps1').read_text(encoding='utf-8')
        self.assertIn("'ru_direct_styling_native'", script)
        runner = (ci.ROOT / 'packaging/run-tests.cmd').read_text(encoding='utf-8')
        self.assertIn('ru_direct_styling_native.exe >>test-results.txt 2>&1\n'
                      'if not "%ERRORLEVEL%"=="0" set "FAILED=1"', runner)
        summary = self.acceptance()
        summary['tests'] = [case for case in summary['tests'] if case['name'] != name]
        with self.assertRaisesRegex(RuntimeError, 'inventory'):
            ci.validate_acceptance(summary)

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

    def test_file_entry_gui_requires_every_check_and_exact_runtime(self):
        for key in ci.GUI_FILE_CHECKS:
            with self.subTest(key=key):
                summary = self.acceptance()
                next(case for case in summary['tests'] if case['name'] == 'main-gui-file-entry')[key] = False
                with self.assertRaisesRegex(RuntimeError, 'required Unicode/drop/cancel'):
                    ci.validate_acceptance(summary)
        summary = self.acceptance()
        next(case for case in summary['tests'] if case['name'] == 'main-gui-file-entry')['fixture_binary_sha256']['ru_notepad.exe'] = 'different'
        with self.assertRaisesRegex(RuntimeError, 'packaged runtime'):
            ci.validate_acceptance(summary)

    def test_large_editor_mode_is_mandatory_with_explicit_time_and_disk_bound(self):
        marker = dict(ci.NATIVE_CONSOLE_TESTS)['editor_largefile_native']
        self.assertEqual(ci.console_command('editor_largefile_native', self.root, self.root),
                         [str(self.root / 'editor_streaming_native.exe'), str(self.root), '--large'])
        disk = type('Disk', (), {'free': ci.LARGE_FILE_MIN_FREE_BYTES})()
        with patch.object(ci.shutil, 'disk_usage', return_value=disk), \
             patch.object(ci, 'run_console', return_value={'passed': True}) as run:
            ci.run_native_console(NoDialogs(), 'editor_largefile_native', marker, self.root, self.root, self.root)
        self.assertEqual(run.call_args.kwargs['timeout'], 900)
        self.assertEqual(run.call_args.kwargs['expected_assertions'], 10)
        disk.free -= 1
        with patch.object(ci.shutil, 'disk_usage', return_value=disk), patch.object(ci, 'run_console') as run:
            result = ci.run_native_console(NoDialogs(), 'editor_largefile_native', marker, self.root, self.root, self.root)
        self.assertFalse(result['passed'])
        self.assertFalse(result['executed'])
        self.assertFalse(result.get('skips'))
        run.assert_not_called()

    def test_large_modes_and_fixture_arguments_are_explained_in_portable_runner(self):
        runner = (ci.ROOT / 'packaging/run-tests.cmd').read_text(encoding='utf-8')
        self.assertIn('3 GiB RAM, 2 GiB free disk, and 15 minutes', runner)
        self.assertIn('editor_streaming_native.exe "%TESTDIR%" --large >>test-results.txt 2>&1', runner)
        for name in ('file_streaming_native', 'editor_streaming_native'):
            self.assertEqual(ci.console_command(name, self.root, self.root),
                             [str(self.root / f'{name}.exe'), str(self.root)])
            self.assertEqual(ci.CONSOLE_TIMEOUT_SECONDS[name], 300)
        self.assertEqual(ci.console_command('app_streaming_native', self.root, self.root),
                         [str(self.root / 'app_streaming_native.exe'), str(self.root)])
        self.assertEqual(ci.CONSOLE_TIMEOUT_SECONDS['app_streaming_native'], 180)
        self.assertEqual(ci.console_command('app_ru_native', self.root, self.root),
                         [str(self.root / 'app_ru_native.exe'), str(self.root)])
        self.assertEqual(ci.CONSOLE_TIMEOUT_SECONDS['app_ru_native'], 180)
        self.assertIn('app_ru_native.exe "%TESTDIR%" >>test-results.txt 2>&1', runner)
        self.assertEqual(ci.console_command('app_ru_timer_native', self.root, self.root),
                         [str(self.root / 'app_ru_native.exe'), str(self.root), '--measure-ru-timer'])
        self.assertEqual(ci.CONSOLE_TIMEOUT_SECONDS['app_ru_timer_native'], 60)
        self.assertIn('app_ru_native.exe "%TESTDIR%" --measure-ru-timer >>test-results.txt 2>&1\n'
                      'if not "%ERRORLEVEL%"=="0" set "FAILED=1"', runner)
        workflow = (ci.ROOT / '.github/workflows/windows.yml').read_text(encoding='utf-8')
        self.assertIn('timeout-minutes: 60', workflow)
        self.assertIn('-RunAclTests', workflow)

    def test_gui_cancel_fixture_has_fixed_byte_budget_and_bounded_writes(self):
        writes = []
        class Stream:
            def __enter__(self): return self
            def __exit__(self, *_): pass
            def write(self, data):
                writes.append(len(data))
                return len(data)
        with patch.object(Path, 'open', return_value=Stream()):
            ci.write_gui_cancel_fixture(self.root / 'unused')
        self.assertEqual(sum(writes), 128 * 1024 * 1024)
        self.assertLessEqual(max(writes), 65536)

    def synthetic_drop_api(self, *, allocation=True, lock=True, posted=True):
        class Kernel:
            def __init__(self):
                self.freed = []
                self.allocations = []
            def GlobalAlloc(self, flags, size):
                self.allocations.append((flags, size))
                self.buffer = ci.ctypes.create_string_buffer(size)
                return 12345 if allocation else 0
            def GlobalLock(self, _):
                return ci.ctypes.addressof(self.buffer) if lock else 0
            def GlobalUnlock(self, _): return True
            def GlobalFree(self, handle): self.freed.append(handle)
        class User:
            def __init__(self): self.posts = []
            def PostMessageW(self, *arguments):
                self.posts.append(arguments)
                return posted
        api = object.__new__(ci.Windows)
        api.kernel, api.user, api.drop_handles = Kernel(), User(), []
        return api

    def test_successful_drop_never_frees_transferred_handle_again(self):
        api = self.synthetic_drop_api()
        paths = [self.root / 'Unicode 路径 😀.txt', self.root / 'second file.txt']
        api.drop(99, paths)
        self.assertEqual(api.user.posts, [(99, 0x0233, 12345, 0)])
        self.assertEqual(api.kernel.freed, [])
        self.assertEqual(api.drop_handles, [12345])
        payload = api.kernel.buffer.raw
        self.assertEqual(struct.unpack_from('<IiiII', payload), (20, 0, 0, 0, 1))
        self.assertEqual(payload[20:].decode('utf-16-le'), '\0'.join(map(str, paths)) + '\0\0')
        api.release_drops()
        self.assertEqual(api.drop_handles, [])
        self.assertEqual(api.kernel.freed, [])

    def test_ru_snapshot_post_has_only_fixed_numeric_message_and_zero_parameters(self):
        api = self.synthetic_drop_api()
        api.post_ru_snapshot(123)
        self.assertEqual(api.user.posts, [(123, 33671, 0, 0)])

    def test_cached_gui_handles_require_matching_live_visible_process(self):
        class User:
            def __init__(self, mode): self.mode, self.calls = mode, []
            def GetWindowThreadProcessId(self, hwnd, pointer):
                self.calls.append(hwnd)
                owner = ci.ctypes.cast(pointer, ci.ctypes.POINTER(ci.wintypes.DWORD)).contents
                owner.value = 999 if self.mode == 'other-process' else 123
                return 0 if self.mode == 'invalid' else 1
            def IsWindowVisible(self, hwnd): return self.mode != 'hidden'
        for mode in ('normal', 'other-process', 'invalid', 'hidden'):
            api = object.__new__(ci.Windows)
            api.user = User(mode)
            with self.subTest(mode=mode):
                if mode == 'normal':
                    api.verify_owned_handles(123, 456, 11)
                    self.assertEqual(api.user.calls, [456, 11])
                else:
                    with self.assertRaises(RuntimeError): api.verify_owned_handles(123, 456, 11)

    def test_navigation_posts_only_matched_scalar_child_extended_keys(self):
        api = self.synthetic_drop_api()
        api.post_navigation(456, 'RIGHT')
        api.post_navigation(456, 'LEFT')
        self.assertEqual(api.user.posts, [(456, 0x0100, 0x27, 0x014d0001),
            (456, 0x0101, 0x27, 0xc14d0001), (456, 0x0100, 0x25, 0x014b0001),
            (456, 0x0101, 0x25, 0xc14b0001)])
        with self.assertRaises(KeyError): api.post_navigation(456, 'CHAR')
        self.assertEqual(len(api.user.posts), 4)

    def test_paint_probe_requires_visible_nonempty_child_and_never_forces_paint(self):
        class User:
            def __init__(self, mode):
                self.mode, self.calls = mode, []
            def IsWindowVisible(self, hwnd): return self.mode != 'hidden'
            def GetClientRect(self, hwnd, pointer):
                rectangle = ci.ctypes.cast(pointer, ci.ctypes.POINTER(ci.wintypes.RECT)).contents
                rectangle.left = rectangle.top = 0
                rectangle.right, rectangle.bottom = (0 if self.mode == 'empty' else 200), 100
                return self.mode != 'bad-rectangle'
            def InvalidateRect(self, *args):
                self.calls.append(('invalidate', args))
                return self.mode != 'failed'
            def GetUpdateRect(self, *args):
                self.calls.append(('query', args))
                return self.mode != 'already-serviced'
        for mode in ('pending', 'already-serviced', 'hidden', 'empty', 'bad-rectangle', 'failed'):
            with self.subTest(mode=mode):
                api = object.__new__(ci.Windows)
                api.user = User(mode)
                with patch.object(ci.ctypes, 'get_last_error', return_value=5, create=True), \
                     patch.object(ci.ctypes, 'WinError', return_value=OSError('synthetic failure'), create=True):
                    if mode in ('hidden', 'empty', 'bad-rectangle'):
                        with self.assertRaises(RuntimeError): api.invalidate_for_paint(456)
                        self.assertEqual(api.user.calls, [])
                    elif mode == 'failed':
                        with self.assertRaises(OSError): api.invalidate_for_paint(456)
                        self.assertEqual(api.user.calls, [('invalidate', (456, None, False))])
                    else:
                        self.assertEqual(api.invalidate_for_paint(456), mode == 'pending')
                        self.assertEqual(api.user.calls, [('invalidate', (456, None, False)),
                                                         ('query', (456, None, False))])

    def test_failed_drop_and_lock_free_only_sender_owned_allocation(self):
        for failure in ('post', 'lock', 'allocation'):
            with self.subTest(failure=failure):
                api = self.synthetic_drop_api(allocation=failure != 'allocation',
                                              lock=failure != 'lock', posted=failure != 'post')
                with patch.object(ci.ctypes, 'get_last_error', return_value=5, create=True), \
                     patch.object(ci.ctypes, 'WinError', return_value=OSError('synthetic failure'), create=True):
                    with self.assertRaises(OSError):
                        api.drop(99, [self.root / 'synthetic.txt'])
                self.assertEqual(api.kernel.freed, [] if failure == 'allocation' else [12345])
                self.assertEqual(api.drop_handles, [])
                self.assertEqual(len(api.user.posts), int(failure == 'post'))

    def test_gui_drop_retention_is_bounded_before_allocation(self):
        api = self.synthetic_drop_api()
        api.drop_handles = [1] * ci.MAX_GUI_DROP_BATCHES
        with self.assertRaisesRegex(RuntimeError, 'bounded allocation budget'):
            api.drop(99, [self.root / 'synthetic.txt'])
        self.assertEqual(api.kernel.allocations, [])
        api.drop_handles.clear()
        with self.assertRaisesRegex(RuntimeError, 'bounded allocation budget'):
            api.drop(99, ['x' * ci.MAX_GUI_DROP_PAYLOAD_BYTES])
        self.assertEqual(api.kernel.allocations, [])

    def gui_file_entry(self, mode='normal'):
        binary, fixtures, evidence = (self.root / name for name in ('bin', 'fixtures', 'evidence'))
        for folder in (binary, fixtures, evidence):
            folder.mkdir()
        for name in ci.portable.RUNTIME_NAMES:
            (binary / name).write_bytes(b'synthetic ' + name.encode())
        process = type('Process', (), {'pid': 123, 'poll': lambda self: None})()
        class FakeWindows:
            def __init__(self):
                self.docs = [('Untitled 1', b'')]
                self.active = 0
                self.busy = False
                self.released = False
                self.commands = []
                self.drop_count = 0
                self.drop_targets = []
            def add(self, path):
                data = path.read_bytes()
                if data.startswith(b'\xff\xfe'):
                    data = data[2:].decode('utf-16-le').encode('utf-8')
                self.docs.append((path.name, data))
                self.active = len(self.docs) - 1
            def no_dialog(self, _): return []
            def responsive(self, _): pass
            def control(self, _, identifier): return identifier
            def scalar(self, _, message):
                if message != 0x1304: raise AssertionError('Unexpected synthetic query')
                return len(self.docs)
            def text(self, hwnd):
                if hwnd == 11:
                    return '  Opening: synthetic' if self.busy else 'Ready'
                return self.docs[self.active][0] + ' · ru_notepad'
            def editor_bytes(self, _):
                data = self.docs[self.active][1]
                return b'wrong' if mode == 'wrong-text' else data
            def editor(self, _): return 456
            def drop(self, hwnd, paths):
                self.drop_targets.append(hwnd)
                self.drop_count += 1
                if self.drop_count == 1:
                    for path in paths: self.add(path)
                else:
                    self.busy = True
                    self.queued = paths
            def command(self, _, identifier):
                self.commands.append(identifier)
                if identifier == 112:
                    self.active = (self.active + 1) % len(self.docs)
                elif identifier == 901:
                    self.busy = False
                    if mode == 'queued-after-cancel': self.add(self.queued[1])
                    if mode == 'partial-after-cancel': self.add(self.queued[0])
                else:
                    raise AssertionError('Unexpected synthetic GUI command')
            def release_drops(self): self.released = True
        api = FakeWindows()
        def launch(_, isolated, __, **kwargs):
            self.assertEqual(kwargs['name'], 'main-gui-file-entry')
            self.assertEqual(kwargs['log_prefix'], 'main-file-entry-launcher')
            for path in kwargs['arguments']:
                self.assertIn('😀', str(path.parent))
                api.add(path)
            try:
                return {'passed': True, **kwargs['exercise'](process, 123)}
            except RuntimeError as exc:
                return {'passed': False, 'error': str(exc)}
        ticks = [0.0]
        def perf_counter():
            ticks[0] += 0.1
            return ticks[0]
        with patch.object(ci, 'run_gui', side_effect=launch), \
             patch.object(ci, 'write_gui_cancel_fixture', side_effect=lambda path: path.write_bytes(b'small unit fixture')), \
             patch.object(ci.time, 'perf_counter', side_effect=perf_counter), patch.object(ci.time, 'sleep'):
            result = ci.run_gui_file_entry(api, binary, fixtures, evidence)
        self.assertTrue(api.released)
        return result, api

    def test_gui_file_entry_exercises_unicode_cli_drop_cancel_and_original_bytes(self):
        result, api = self.gui_file_entry()
        self.assertTrue(result['passed'])
        self.assertTrue(all(result[key] for key in ci.GUI_FILE_CHECKS))
        self.assertEqual(api.drop_count, 2)
        self.assertEqual(api.drop_targets, [456, 456], 'Drops must target the actual editor child, not its parent')
        self.assertIn(901, api.commands)
        self.assertEqual(set(result['fixture_binary_sha256']), set(ci.portable.RUNTIME_NAMES))

    def test_gui_file_entry_rejects_wrong_content(self):
        self.assertFalse(self.gui_file_entry('wrong-text')[0]['passed'])

    def test_gui_file_entry_rejects_retained_queue_after_cancel(self):
        self.assertFalse(self.gui_file_entry('queued-after-cancel')[0]['passed'])

    def test_gui_file_entry_rejects_partial_document_after_cancel(self):
        self.assertFalse(self.gui_file_entry('partial-after-cancel')[0]['passed'])

    def test_ru_gui_requires_every_check_and_exact_runtime(self):
        for key in ci.GUI_RU_CHECKS:
            with self.subTest(key=key):
                summary = self.acceptance()
                next(case for case in summary['tests'] if case['name'] == 'main-gui-ru-syntax')[key] = False
                with self.assertRaisesRegex(RuntimeError, 'required style/fold/visibility/clean-state'):
                    ci.validate_acceptance(summary)
        summary = self.acceptance()
        next(case for case in summary['tests'] if case['name'] == 'main-gui-ru-syntax')['fixture_binary_sha256']['Lexilla.dll'] = 'different'
        with self.assertRaisesRegex(RuntimeError, 'packaged runtime'):
            ci.validate_acceptance(summary)

    def test_ru_gui_fixture_uses_utf8_byte_offsets_and_nested_headers(self):
        source, probes, headers, children = ci.gui_ru_syntax_fixture()
        self.assertIn('中😀'.encode(), source)
        expected = {'keyword': ('作', 4), 'number': ('42', 3), 'quoted_keyword': ("'若 真 则'", 2)}
        self.assertEqual(set(probes), set(expected))
        for name, (token, style) in expected.items():
            probe = probes[name]
            self.assertEqual(probe['style'], style)
            self.assertEqual(source[probe['offset']:probe['offset'] + probe['length']], token.encode())
            self.assertGreater(probe['offset'], source.decode().index(token))
        self.assertEqual(headers, (1, 4))
        self.assertEqual(children, (2, 5))
        self.assertTrue(source.splitlines()[headers[0]].startswith('作'.encode()))
        self.assertTrue(source.splitlines()[headers[1]].lstrip().startswith('若'.encode()))

    def gui_ru_syntax(self, mode='normal'):
        binary, fixtures, evidence = (self.root / name for name in ('bin', 'fixtures', 'evidence'))
        for folder in (binary, fixtures, evidence):
            folder.mkdir()
        for name in ci.portable.RUNTIME_NAMES:
            (binary / name).write_bytes(b'synthetic ' + name.encode())
        original, probes, headers, children = ci.gui_ru_syntax_fixture()
        timer_data, timer_probes = ci.gui_ru_timer_fixture()
        process = type('Process', (), {'pid': 123, 'poll': lambda self: None})()
        class FakeWindows:
            def __init__(self):
                self.language = 'ru'
                self.collapsed = False
                self.commands = []
                self.queries = []
                self.ru_reselected = False
                self.large = False
                self.timer_rounds = 0
                self.drop_targets = []
                self.released = False
                self.caret = 0
                self.navigation = []
                self.queued_key = None
                self.invalidations = 0
                self.paint_queries = 0
                self.snapshot_posts = 0
                self.editor_lookups = 0
            def no_dialog(self, _): return []
            def responsive(self, _):
                if self.large:
                    self.timer_rounds += 1
                    if mode == 'timer-unresponsive': raise RuntimeError('WM_NULL failed')
            def control(self, _, identifier): return identifier
            def _text(self, hwnd):
                if hwnd == 11:
                    if mode == 'timer-empty-status': return ''
                    return 'Ru    Styling Ru...' if self.timer_rounds < (12 if mode == 'timer-slow' else 2) or mode == 'timer-stalled' else 'Ln 1    UTF-8    Ru'
                return self.source.name + ' · ru_notepad'
            def text(self, hwnd):
                self.scalar(hwnd, 0x000E)
                self.scalar(hwnd, 0x000D)
                return self._text(hwnd)
            def editor(self, _):
                self.editor_lookups += 1
                return 456
            def verify_owned_handles(self, process_id, *handles):
                if process_id != 123 or handles != (456, 11): raise AssertionError('Unexpected cached GUI controls')
                if mode == 'timer-wrong-owner' or (mode == 'timer-final-wrong-owner' and self.timer_rounds >= 2):
                    raise RuntimeError('Cached GUI control belongs to another process')
            def post_ru_snapshot(self, hwnd):
                if hwnd != 123: raise AssertionError('Diagnostic must target the main HWND')
                self.snapshot_posts += 1
                if mode == 'snapshot-post-failure': raise RuntimeError('PostMessage failed')
                if mode == 'snapshot-missing': return
                receipt = observer_evidence()['diagnostics']['receipts'][self.snapshot_posts - 1].copy()
                if self.large:
                    receipt['pending'] = int(self.timer_rounds < (12 if mode == 'timer-slow' else 2) or mode == 'timer-stalled')
                if mode == 'snapshot-error': receipt = {'seq': self.snapshot_posts, 'ok': 0}
                if mode == 'snapshot-wrong-generation' and self.snapshot_posts == 3: receipt['generation'] += 1
                if mode == 'snapshot-final-pending' and self.snapshot_posts == 3: receipt['pending'] = 1
                if mode == 'snapshot-final-short' and self.snapshot_posts == 3: receipt['bytes'] -= 1
                log = self.source.parent.parent / 'ru_notepad-unit.log'
                with log.open('a', encoding='utf-8') as out:
                    out.write('RU_GUI_SNAPSHOT ' + ' '.join(f'{key}={value}' for key, value in receipt.items()) + '\n')
            def editor_bytes(self, _):
                if self.large: raise AssertionError('Never fetch the 1 MB document byte by byte')
                return b'wrong' if mode == 'wrong-text' else original
            def drop(self, hwnd, paths):
                if len(paths) != 1: raise AssertionError('Expected one timer source')
                self.drop_targets.append(hwnd)
                self.source = paths[0]
                if self.source.read_bytes() != timer_data: raise AssertionError('Incorrect 1 MB fixture')
                self.large = True
                self.timer_query_start = len(self.queries)
                if mode == 'timer-changed-source': self.source.write_bytes(b'changed')
            def release_drops(self): self.released = True
            def post_navigation(self, hwnd, key):
                if hwnd != 456: raise AssertionError('Navigation must target only the synthetic editor')
                self.navigation.append(key)
                self.queued_key = key
                if mode == 'timer-navigation-post-failure': raise RuntimeError('PostMessage failed')
            def invalidate_for_paint(self, hwnd):
                if hwnd != 456: raise AssertionError('Paint must target only the synthetic editor')
                self.invalidations += 1
                if mode == 'timer-paint-invalidate-failure': raise RuntimeError('InvalidateRect failed')
                return mode != 'timer-paint-already-serviced'
            def paint_pending(self, hwnd):
                if hwnd != 456: raise AssertionError('Paint must target only the synthetic editor')
                self.paint_queries += 1
                return mode == 'timer-paint-stalled'
            def scalar(self, hwnd, message, wparam=0, lparam=0):
                self.queries.append((hwnd, message, wparam, lparam))
                if message == 0x000E: return len(self._text(hwnd))
                if message == 0x000D: return 1
                if message == 0x1304: return 3 if self.large else 2
                if hwnd != 456 or lparam != 0 or not isinstance(wparam, int):
                    raise AssertionError('Private GUI messages may carry only scalar values')
                if message == 2378:
                    return 8388607 if mode == ('timer-wrong-mask' if self.large else 'wrong-mask') else 3
                if self.large:
                    if message == 2008:
                        if self.queued_key is not None and mode != 'timer-navigation-stalled':
                            self.caret = 3 if self.queued_key == 'RIGHT' else 0
                            self.queued_key = None
                            if mode == 'timer-navigation-wrong-position': self.caret = 1
                            if mode == 'timer-navigation-after-complete': self.timer_rounds = 2
                        return self.caret
                    if message == 2006: return len(timer_data) - int(mode == 'timer-wrong-length')
                    if message == 2159: return int(mode == 'timer-dirty')
                    if message == 2028: return len(timer_data)
                    if message != 2010: raise AssertionError('No whole-document or line scans in timer stage')
                    return next((probe['style'] if mode != 'timer-wrong-' + label and
                                 not (label.startswith('tail') and self.timer_rounds < (12 if mode == 'timer-slow' else 2)) and
                                 not (mode == 'timer-head-regresses' and label.startswith('head') and self.timer_rounds >= 2) else 0
                                 for label, probe in timer_probes.items()
                                 if probe['offset'] <= wparam < probe['offset'] + probe['length']), 0)
                if message == 2154: return original.count(b'\n') + 1
                if message == 2159: return int(mode == 'dirty')
                if message == 2010:
                    if mode == 'wrong-style' or (mode == 'ru-no-restyle' and self.ru_reselected): return 0
                    if self.language == 'plain' and mode != 'plain-keeps-style': return 0
                    return next((probe['style'] for probe in probes.values()
                                 if probe['offset'] <= wparam < probe['offset'] + probe['length']), 0)
                if message == 2223:
                    if mode == 'no-fold' or (self.language == 'plain' and mode != 'plain-keeps-fold'): return 0x400
                    return 0x2400 if wparam in headers else 0x401
                if message == 2228:
                    return int(not self.collapsed or wparam not in
                               (range(1, 9) if mode == 'root-hidden' else range(2, 8)))
                raise AssertionError(f'Unexpected or pointer-bearing private message: {message}')
            def command(self, _, identifier):
                self.commands.append(identifier)
                if identifier == 505:
                    self.collapsed = mode != 'collapse-noop'
                    if mode == 'changed-source': self.source.write_bytes(b'modified by synthetic bug')
                elif identifier == 506:
                    self.collapsed = mode == 'expand-noop'
                elif identifier == 701:
                    self.language = 'plain'
                    self.collapsed = mode == 'plain-keeps-hidden'
                elif identifier == 704:
                    if self.language != 'ru':
                        self.ru_reselected = True
                        self.language = 'ru'
                        self.collapsed = mode == 'ru-keeps-hidden'
                    elif mode == 'same-ru-expands':
                        self.collapsed = False
                else:
                    raise AssertionError('Unexpected GUI Ru menu command')
        api = FakeWindows()
        def launch(_, isolated, __, **kwargs):
            self.assertEqual(kwargs['name'], 'main-gui-ru-syntax')
            self.assertEqual(kwargs['log_prefix'], 'main-ru-syntax-launcher')
            self.assertEqual(len(kwargs['arguments']), 1)
            api.source = kwargs['arguments'][0]
            (isolated / 'ru_notepad-unit.log').write_text('', encoding='utf-8')
            self.assertEqual(api.source.suffix, '.ru')
            self.assertIn('😀', str(api.source))
            self.assertEqual(api.source.read_bytes(), original)
            try:
                return {'passed': True, **kwargs['exercise'](process, 123)}
            except RuntimeError as exc:
                return {'passed': False, 'error': str(exc)}
        ticks = [0.0]
        def perf_counter():
            ticks[0] += 0.0001
            return ticks[0]
        def sleep(seconds):
            ticks[0] += seconds
        def edit_stage(_, child, hwnd, source, record):
            self.assertIs(child, process)
            self.assertEqual(hwnd, 123)
            self.assertEqual(source.read_bytes(), ci.gui_ru_edit_fixture()[0])
            record['operations'] = [dict(operation, wall_ms=100.0, max_response_ms=1.0, probes=2)
                                    for operation in ci.gui_ru_edit_operations()]
            record['undo_commands'] = 6
            return {name: True for name in ci.GUI_RU_EDIT_CHECKS}
        with patch.object(ci, 'run_gui', side_effect=launch), \
             patch.object(ci, 'run_gui_ru_edits', side_effect=edit_stage), \
             patch.object(ci.time, 'perf_counter', side_effect=perf_counter), patch.object(ci.time, 'sleep', side_effect=sleep):
            result = ci.run_gui_ru_syntax(api, binary, fixtures, evidence)
        return result, api

    def test_ru_gui_exercises_actual_style_fold_and_menu_scalar_contract(self):
        result, api = self.gui_ru_syntax()
        self.assertTrue(result['passed'], result.get('error'))
        self.assertTrue(all(result[key] for key in ci.GUI_RU_CHECKS))
        self.assertEqual(api.commands, [505, 704, 506, 505, 701, 704])
        self.assertEqual(set(result['fixture_binary_sha256']), set(ci.portable.RUNTIME_NAMES))
        self.assertEqual(set(query[1] for query in api.queries), {0x000E, 0x000D, 0x1304, 2006, 2008, 2028, 2154, 2159, 2010, 2223, 2228, 2378})
        self.assertTrue(all(query[3] == 0 for query in api.queries))
        self.assertEqual(api.drop_targets, [456])
        self.assertTrue(api.released)
        self.assertEqual(api.navigation, ['RIGHT', 'LEFT'])
        self.assertEqual(api.caret, 0)
        self.assertEqual(api.invalidations, 1)
        self.assertGreaterEqual(result['timer_performance']['probes'], 2)
        ci.validate_gui_ru_timer(result['timer_performance'])

    def test_ru_gui_fails_closed_for_wrong_style_fold_visibility_dirty_or_bytes(self):
        for mode in ('wrong-mask', 'wrong-text', 'wrong-style', 'no-fold', 'dirty', 'collapse-noop',
                     'root-hidden', 'expand-noop', 'same-ru-expands', 'plain-keeps-style',
                     'plain-keeps-fold', 'plain-keeps-hidden', 'ru-no-restyle',
                     'ru-keeps-hidden', 'changed-source'):
            with self.subTest(mode=mode):
                # Each isolated run owns fresh fixtures and launcher-log names.
                for name in ('bin', 'fixtures', 'evidence'):
                    shutil.rmtree(self.root / name, ignore_errors=True)
                result, _ = self.gui_ru_syntax(mode)
                self.assertFalse(result['passed'])
                self.assertIn('error', result)

    def test_ru_timer_rejects_unfinished_styles_status_length_dirty_source_and_response(self):
        for mode in ('timer-wrong-head_identifier', 'timer-wrong-head_keyword', 'timer-wrong-head_number',
                     'timer-wrong-tail_keyword', 'timer-wrong-tail_number',
                     'timer-stalled', 'timer-empty-status', 'timer-wrong-length',
                     'timer-dirty', 'timer-changed-source', 'timer-unresponsive', 'timer-wrong-mask',
                     'timer-wrong-owner', 'timer-final-wrong-owner'):
            with self.subTest(mode=mode):
                for name in ('bin', 'fixtures', 'evidence'):
                    shutil.rmtree(self.root / name, ignore_errors=True)
                result, api = self.gui_ru_syntax(mode)
                self.assertFalse(result['passed'])
                self.assertTrue(api.released)
                self.assertGreater(result['timer_performance']['wall_ms'], 0)
                if (mode.startswith('timer-wrong-') and mode not in ('timer-wrong-mask', 'timer-wrong-owner')) or mode in ('timer-stalled', 'timer-empty-status'):
                    self.assertIn('30 seconds', result['error'])

    def test_ru_timer_failure_retains_bounded_progress_without_treating_endstyled_as_completion(self):
        result, _ = self.gui_ru_syntax('timer-wrong-tail_number')
        self.assertFalse(result['passed'])
        self.assertIn('30 seconds', result['error'])
        last = result['timer_performance']['last_probe']
        self.assertEqual(last['length'], ci.GUI_RU_TIMER_BYTES)
        self.assertEqual(last['end_styled'], ci.GUI_RU_TIMER_BYTES)
        self.assertTrue(last['clean'])
        self.assertTrue(last['style_matches']['head_keyword'])
        self.assertFalse(last['style_matches']['tail_number'])
        self.assertLessEqual(len(last['status']), 512)

    def test_ru_timer_requires_real_queued_navigation_and_natural_paint_service_while_pending(self):
        for mode in ('timer-navigation-post-failure', 'timer-navigation-stalled',
                     'timer-navigation-wrong-position', 'timer-navigation-after-complete',
                     'timer-paint-invalidate-failure', 'timer-paint-stalled'):
            with self.subTest(mode=mode):
                for name in ('bin', 'fixtures', 'evidence'):
                    shutil.rmtree(self.root / name, ignore_errors=True)
                result, api = self.gui_ru_syntax(mode)
                self.assertFalse(result['passed'])
                self.assertTrue(api.released)
                self.assertIn('error', result)
                self.assertGreater(result['timer_performance']['wall_ms'], 0)
                self.assertLessEqual(api.invalidations, 1)

    def test_ru_timer_accepts_already_serviced_paint_without_inventing_pending_observation(self):
        result, api = self.gui_ru_syntax('timer-paint-already-serviced')
        self.assertTrue(result['passed'], result.get('error'))
        paint = result['timer_performance']['responsiveness']['paint']
        self.assertFalse(paint['pending_observed'])
        self.assertTrue(paint['already_serviced'])
        self.assertTrue(paint['cleared'])
        self.assertTrue(paint['while_styling'])
        self.assertEqual(api.invalidations, 1)
        ci.validate_gui_ru_timer(result['timer_performance'])

    def test_ru_timer_responsiveness_schema_is_strict_finite_and_bounded(self):
        import copy
        good = next(case for case in self.acceptance()['tests']
                    if case['name'] == 'main-gui-ru-syntax')['timer_performance']
        mutations = [lambda value: value['responsiveness'].clear(),
            lambda value: value['responsiveness']['navigation'].pop(),
            lambda value: value['responsiveness'].update(unexpected=1)]
        for field, bad in [('before', True), ('after', 1), ('while_styling', False),
                           ('wall_ms', float('nan')), ('wall_ms', float('inf')),
                           ('wall_ms', -1), ('wall_ms', 101), ('wall_ms', True)]:
            mutations.append(lambda value, f=field, b=bad: value['responsiveness']['navigation'][0].update({f: b}))
        for field, bad in [('invalidations', True), ('invalidations', 0), ('invalidations', 2),
                           ('pending_observed', 1), ('already_serviced', True), ('cleared', False),
                           ('while_styling', False), ('wall_ms', float('nan')), ('wall_ms', -1), ('wall_ms', 101)]:
            mutations.append(lambda value, f=field, b=bad: value['responsiveness']['paint'].update({f: b}))
        for index, mutate in enumerate(mutations):
            record = copy.deepcopy(good)
            mutate(record)
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                ci.validate_gui_ru_timer(record)
        for field in ('navigation', 'paint'):
            record = copy.deepcopy(good)
            record['wall_ms'] = 10000
            target = record['responsiveness'][field]
            if field == 'navigation': target = target[0]
            target['wall_ms'] = ci.GUI_RU_RESPONSE_TIMEOUT_MS + 1
            with self.subTest(over_5_seconds=field), self.assertRaises(RuntimeError):
                ci.validate_gui_ru_timer(record)

    def test_ru_timer_final_diagnostic_snapshot_is_strictly_validated(self):
        import copy
        good = next(case for case in self.acceptance()['tests']
                    if case['name'] == 'main-gui-ru-syntax')['timer_performance']
        for field, value in [('opened', False), ('clean', False), ('length', 999999),
                             ('end_styled', -1), ('end_styled', True), ('end_styled', 1000001),
                             ('status', 'Styling Ru...'), ('status', ''), ('status', '   '), ('status', 'x' * 513),
                             ('style_matches', {}), ('style_matches', {'head_keyword': True})]:
            record = copy.deepcopy(good)
            record['last_probe'][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(RuntimeError):
                ci.validate_gui_ru_timer(record)

    def test_performance_clock_records_actual_bounded_metadata(self):
        info = ci.time.get_clock_info('perf_counter')
        record = ci.performance_clock_record()
        self.assertEqual(record, {'clock_name': 'perf_counter', 'implementation': info.implementation,
                                 'resolution': info.resolution, 'monotonic': info.monotonic,
                                 'adjustable': info.adjustable})
        self.assertEqual(set(record), ci.PERFORMANCE_CLOCK_FIELDS)
        self.assertLess(len(json.dumps(record)), 300)
        ci.validate_performance_clock(record)
        self.assertIn('not physical input or paint accuracy', ci.PERFORMANCE_CLOCK_MEASUREMENT)

    def test_performance_clock_metadata_rejects_malformed_nonfinite_or_coarse_windows_receipts(self):
        good = observer_evidence()['clock']
        ci.validate_performance_clock(good, require_windows=True)
        mutations = [('clock_name', 'monotonic'), ('implementation', ''),
                     ('implementation', 'x' * 129), ('implementation', 'bad\nclock'),
                     ('implementation', None), ('resolution', 0), ('resolution', -1),
                     ('resolution', True), ('resolution', '0.0000001'),
                     ('resolution', float('nan')), ('resolution', float('inf')),
                     ('resolution', float('-inf')), ('monotonic', False), ('monotonic', 1),
                     ('adjustable', True), ('adjustable', 0)]
        for field, value in mutations:
            with self.subTest(field=field, value=value), self.assertRaises(RuntimeError):
                ci.validate_performance_clock(dict(good, **{field: value}))
        for record in (None, [], {}, dict(good, extra=1),
                       {key: value for key, value in good.items() if key != 'resolution'}):
            with self.subTest(record=record), self.assertRaises(RuntimeError):
                ci.validate_performance_clock(record)
        for implementation in ('GetTickCount64()', 'clock_gettime(CLOCK_MONOTONIC)',
                               'QueryPerformanceCounter', 'QueryPerformanceCounter() forged'):
            with self.subTest(implementation=implementation), self.assertRaisesRegex(RuntimeError, 'QueryPerformanceCounter'):
                ci.validate_performance_clock(dict(good, implementation=implementation), require_windows=True)
        info = type('ClockInfo', (), dict(good, resolution=float('nan')))()
        with patch.object(ci.time, 'get_clock_info', return_value=info) as get_info:
            with self.assertRaises(RuntimeError): ci.performance_clock_record()
            get_info.assert_called_once_with('perf_counter')

    def test_performance_clock_is_local_and_rejects_nonfinite_or_backwards_samples(self):
        for bad in (float('nan'), float('inf'), float('-inf'), True, None, '1'):
            with self.subTest(value=bad), patch.object(ci.time, 'perf_counter', return_value=bad):
                with self.assertRaisesRegex(RuntimeError, 'nonfinite or moved backwards'):
                    ci.PerformanceClock()()
        with patch.object(ci.time, 'perf_counter', side_effect=[1.0, 1.0, 1.0002, 1.0001]):
            clock = ci.PerformanceClock()
            self.assertEqual(clock(), 1.0)
            self.assertEqual(clock(), 1.0)  # Identical ticks remain valid, not invented elapsed time.
            self.assertEqual(clock(), 1.0002)
            with self.assertRaisesRegex(RuntimeError, 'moved backwards'): clock()
        original = ci.time.perf_counter
        with patch.object(ci.time, 'perf_counter', return_value=1e15):
            self.assertEqual(ci.PerformanceClock()(), 1e15)
        self.assertIs(ci.time.perf_counter, original)
        restored = ci.PerformanceClock()
        first, second = restored(), restored()
        self.assertGreaterEqual(second, first)
        with patch.object(ci.time, 'perf_counter', return_value=1.0):
            for previous in (2.0, float('nan'), True):
                with self.subTest(previous=previous), self.assertRaises(RuntimeError):
                    ci.PerformanceClock(previous)()

    def test_ru_observer_uses_precise_costs_when_monotonic_is_coarse(self):
        class Fake:
            def scalar(self, *args): return 1
            def responsive(self, *args): return None
        api = Fake()
        scalar, responsive = api.scalar, api.responsive
        record = ci.gui_ru_observer_record()
        with patch.object(ci.time, 'monotonic', return_value=0.0) as coarse, \
             patch.object(ci.time, 'perf_counter', side_effect=[.001, .002, .0024, .003, .1, .1003]):
            with ci.GuiRuObserver(api, record, 0.0) as observer:
                self.assertTrue(observer.snapshot(lambda: api.scalar(123, 2006)))
                api.responsive(123)
            coarse.assert_not_called()
        self.assertEqual(record['query_wall_ms'], .7)
        self.assertEqual(record['max_query_ms'], .4)
        self.assertEqual(record['snapshot_wall_ms'], 2.0)
        self.assertEqual(record['snapshots'][0]['wall_ms'], 2.0)
        self.assertEqual(record['sendmessage_calls'], 2)
        self.assertEqual(record['response_starts_ms'], [100.0])
        self.assertEqual(api.scalar, scalar)
        self.assertEqual(api.responsive, responsive)
        ci.validate_gui_ru_observer(record, 101.0, 1)

    def test_ru_diagnostic_post_and_log_costs_use_same_precise_clock(self):
        class Fake:
            def post_ru_snapshot(self, hwnd): pass
        (self.root / 'ru_notepad-unit.log').write_text('RU_GUI_SNAPSHOT seq=1 ok=0\n')
        record = {}
        diagnostics = ci.GuiRuDiagnostics(Fake(), 123, self.root, record)
        with patch.object(ci.time, 'monotonic', return_value=0.0) as coarse, \
             patch.object(ci.time, 'perf_counter', side_effect=[1, 1.0004, 2, 2.0001, 2.0008, 2.0009, 2.001]):
            diagnostics.request('baseline')
            diagnostics.capture(1)
            coarse.assert_not_called()
        self.assertEqual(record['post_wall_ms'], .4)
        self.assertEqual(record['log_read_wall_ms'], .7)
        self.assertEqual(record['max_log_read_ms'], .7)
        self.assertEqual(record['captures'], [{'phase': 'baseline', 'wall_ms': 1.0, 'log_reads': 1}])
        self.assertEqual(record['receipts'], [{'seq': 1, 'ok': 0}])

    def test_ru_observer_clock_failure_keeps_partial_counts_and_restores_wrappers(self):
        class Fake:
            def scalar(self, *args): return 1
            def responsive(self, *args): return None
        for bad, final in ((.19, .3), (.19, .19), (float('nan'), .3),
                           (float('nan'), float('nan')), (float('inf'), .3), (float('inf'), float('inf'))):
            api = Fake()
            record = ci.gui_ru_observer_record()
            with self.subTest(value=bad), \
                 patch.object(ci.time, 'perf_counter', side_effect=[.1, .2, bad, final]):
                with self.assertRaisesRegex(RuntimeError, 'nonfinite or moved backwards'):
                    with ci.GuiRuObserver(api, record, 0.0) as observer:
                        observer.snapshot(lambda: api.scalar(123, 2006))
            self.assertEqual(record['scalar_calls'], 1)
            self.assertEqual(record['sendmessage_calls'], 1)
            self.assertEqual(record['snapshot_count'], 1)
            self.assertEqual(record['snapshots'][0]['messages'], 1)
            self.assertFalse(record['snapshots'][0]['final'])
            self.assertNotIn('scalar', api.__dict__)
            self.assertNotIn('responsive', api.__dict__)
            self.assertIsNone(observer.current)

    def test_ru_observer_measures_nested_text_calls_and_restores_wrappers_after_failure(self):
        class Fake:
            def scalar(self, *args): return 1
            def responsive(self, *args): return None
            def text(self, hwnd):
                self.scalar(hwnd, 14)
                self.scalar(hwnd, 13)
                return 'bounded'
        api = Fake()
        record = ci.gui_ru_observer_record()
        original = api.scalar
        with self.assertRaisesRegex(RuntimeError, 'synthetic failure'):
            with ci.GuiRuObserver(api, record, ci.time.perf_counter()) as observer:
                observer.snapshot(lambda: api.text(123) == 'bounded')
                api.responsive(123)
                raise RuntimeError('synthetic failure')
        self.assertEqual(api.scalar, original)
        self.assertNotIn('scalar', api.__dict__)
        self.assertNotIn('responsive', api.__dict__)
        self.assertEqual(record['scalar_calls'], 2)
        self.assertEqual(record['wm_null_calls'], 1)
        self.assertEqual(record['sendmessage_calls'], 3)
        self.assertEqual(record['snapshots'][0]['messages'], 2)
        self.assertGreaterEqual(record['query_wall_ms'], 0)

    def test_ru_observer_blocks_33rd_actual_snapshot_message_and_preserves_costs(self):
        class Fake:
            def scalar(self, *args): return 1
            def responsive(self, *args): return None
        api = Fake()
        record = ci.gui_ru_observer_record()
        with ci.GuiRuObserver(api, record, ci.time.perf_counter()) as observer:
            with self.assertRaisesRegex(RuntimeError, '32 synchronous'):
                observer.snapshot(lambda: [api.scalar(123, 2006) for _ in range(33)])
        self.assertEqual(record['scalar_calls'], 32)
        self.assertEqual(record['snapshots'][0]['messages'], 32)
        self.assertFalse(record['snapshots'][0]['final'])
        self.assertNotIn('scalar', api.__dict__)

    def test_ru_observer_caches_open_handles_and_head_but_rechecks_final_16_bytes(self):
        result, api = self.gui_ru_syntax('timer-slow')
        self.assertTrue(result['passed'], result.get('error'))
        record = result['timer_performance']
        measured = record['observer']
        self.assertGreaterEqual(measured['snapshot_count'], 3)
        self.assertEqual(measured['scalar_calls'], len(api.queries) - api.timer_query_start)
        self.assertEqual(api.snapshot_posts, 3)
        self.assertLessEqual(measured['max_snapshot_messages'], 32)
        for probe in record['style_probes'].values():
            for position in range(probe['offset'], probe['offset'] + probe['length']):
                reads = [query for query in api.queries[api.timer_query_start:] if query[1:3] == (2010, position)]
                self.assertGreaterEqual(len(reads), 2)
                if probe['offset'] < 16: self.assertEqual(len(reads), 2)
        self.assertNotIn('scalar', api.__dict__)
        self.assertNotIn('responsive', api.__dict__)
        self.assertEqual(measured['snapshots'][-1]['messages'], 25)
        self.assertTrue(all(right - left >= 50 for left, right in
                            zip(measured['response_starts_ms'], measured['response_starts_ms'][1:])))

    def test_ru_observer_rejects_regressed_cached_head_styles(self):
        result, api = self.gui_ru_syntax('timer-head-regresses')
        self.assertFalse(result['passed'])
        self.assertIsNotNone(result['timer_performance']['first_head_style_ms'])
        self.assertFalse(result['timer_performance']['last_probe']['style_matches']['head_identifier'])
        self.assertNotIn('scalar', api.__dict__)

    def test_ru_observer_receipt_schema_and_frequency_are_fail_closed(self):
        import copy
        good = next(case for case in self.acceptance()['tests'] if case['name'] == 'main-gui-ru-syntax')['timer_performance']
        cases = [('response_interval_ms', 1), ('snapshot_interval_ms', 1), ('snapshot_message_limit', 33),
                 ('scalar_calls', True), ('wm_null_calls', 4), ('sendmessage_calls', 999),
                 ('query_wall_ms', float('nan')), ('query_wall_ms', 101), ('max_query_ms', 99),
                 ('snapshot_count', 122), ('max_snapshot_messages', 33), ('max_snapshot_ms', 1),
                 ('snapshot_wall_ms', 1), ('response_starts_ms', [0, 1, 2]), ('snapshots', [])]
        for field, value in cases:
            with self.subTest(field=field):
                record = copy.deepcopy(good)
                record['observer'][field] = value
                with self.assertRaises(RuntimeError): ci.validate_gui_ru_timer(record)
        for field, value in [('messages', 33), ('wall_ms', float('inf')), ('start_ms', -1), ('final', False), ('final', 1)]:
            record = copy.deepcopy(good)
            record['observer']['snapshots'][0][field] = value
            with self.subTest(snapshot=field), self.assertRaises(RuntimeError): ci.validate_gui_ru_timer(record)

    def test_ru_snapshot_parser_rejects_duplicate_missing_unsafe_or_unbounded_records(self):
        good = observer_evidence()['diagnostics']['receipts']
        def encode(records):
            return ''.join('RU_GUI_SNAPSHOT ' + ' '.join(f'{key}={value}' for key, value in row.items()) + '\n'
                           for row in records)
        text = encode(good)
        self.assertEqual(ci.parse_gui_ru_snapshots('ordinary startup\n' + text), good)
        self.assertEqual(ci.parse_gui_ru_snapshots('RU_GUI_SNAPSHOT seq=1 ok=0\n'), [{'seq': 1, 'ok': 0}])
        self.assertEqual(ci.parse_gui_ru_snapshots(text.rstrip('\n')), good[:2])
        for broken in (text.replace('seq=1', 'seq=2', 1), text.replace('seq=1', 'seq=1 seq=1', 1),
                       text.replace('ok=1', 'ok=0', 1), text.replace('ok=1', 'ok=true', 1),
                       text.replace('revision=0', 'revision=9007199254740992', 1),
                       text.replace('revision=0', 'revision=1.0', 1), text.replace('work_ms=0', 'work_ms=nan', 1),
                       text.replace('work_ms=0', 'work_ms=1e999', 1), text.replace('bytes=100 ', 'bytes=-1 ', 1),
                       text.replace(' pending=0', '', 1), text + encode([good[0]]),
                       text.replace('RU_GUI_SNAPSHOT ', 'prefix RU_GUI_SNAPSHOT ', 1),
                       text.replace('ok=1', 'ok=1 private=body', 1)):
            with self.subTest(broken=broken[:120]), self.assertRaises(RuntimeError): ci.parse_gui_ru_snapshots(broken)

    def test_ru_snapshot_receipts_validate_fixed_phases_generation_and_completion(self):
        import copy
        good = observer_evidence()['diagnostics']
        for index, field, value in [(0, 'seq', True), (1, 'pending', 0), (1, 'revision', 1),
                                  (2, 'generation', 3), (2, 'pending', 1), (2, 'bytes', 999999),
                                  (2, 'feed', 0), (2, 'read_bytes', 1000001), (2, 'restart', 1024),
                                  (2, 'style_notifications', 1), (2, 'fold_notifications', 1),
                                  (2, 'ticks', -1), (2, 'work_ms', float('inf')),
                                  (1, 'bytes', 101), (1, 'feed', 101), (1, 'read_bytes', 1000001),
                                  (1, 'continuation_ticks', 1), (1, 'max_tick_ms', 1), (1, 'max_gap_ms', 1),
                                  (1, 'chunks', 1), (1, 'work_ms', 1), (1, 'posts', 1)]:
            record = copy.deepcopy(good)
            record['receipts'][index][field] = value
            with self.subTest(index=index, field=field), self.assertRaises(RuntimeError):
                ci.validate_gui_ru_diagnostics(record)
        baseline_unavailable = copy.deepcopy(good)
        baseline_unavailable['receipts'][0] = {'seq': 1, 'ok': 0}
        ci.validate_gui_ru_diagnostics(baseline_unavailable)
        for field, value in [('phase', 'pending'), ('wall_ms', 1001), ('log_reads', 23)]:
            record = copy.deepcopy(good)
            record['captures'][1][field] = value
            with self.subTest(capture=field), self.assertRaises(RuntimeError): ci.validate_gui_ru_diagnostics(record)

    def test_ru_snapshot_failures_cannot_bless_timer_success_and_keep_partial_costs(self):
        for mode in ('snapshot-post-failure', 'snapshot-missing', 'snapshot-error',
                     'snapshot-wrong-generation', 'snapshot-final-pending', 'snapshot-final-short'):
            for name in ('bin', 'fixtures', 'evidence'): shutil.rmtree(self.root / name, ignore_errors=True)
            result, api = self.gui_ru_syntax(mode)
            with self.subTest(mode=mode):
                self.assertFalse(result['passed'])
                self.assertIn('error', result)
                self.assertLessEqual(api.snapshot_posts, 3)
                self.assertLessEqual(result['timer_performance']['diagnostics']['log_reads'], 44)
                self.assertNotIn('scalar', api.__dict__)

    def test_ru_snapshot_timeout_collection_never_extends_timer_success_window(self):
        result, api = self.gui_ru_syntax('timer-wrong-tail_number')
        record = result['timer_performance']
        self.assertFalse(result['passed'])
        self.assertGreater(record['wall_ms'], 30000)
        self.assertEqual(api.snapshot_posts, 3)
        self.assertEqual(len(record['diagnostics']['receipts']), 3)
        self.assertFalse(record['observer']['snapshots'][-1]['final'])
        self.assertNotIn('scalar', api.__dict__)

    def test_linux_diagnostic_control_rejects_missing_changed_private_or_partial_outputs(self):
        for mutation in ('missing', 'stderr', 'marker', 'backend', 'fields', 'private', 'skip', 'extra'):
            shutil.rmtree(self.root / 'build', ignore_errors=True)
            directory, inputs = self.helper_policy_fixture()
            path = directory / 'diagnostic-control.stdout.log'
            text = path.read_text()
            if mutation == 'missing': path.unlink()
            elif mutation == 'stderr': (directory / 'diagnostic-control.stderr.log').write_text('warning')
            else:
                replacements = {'marker': ('RU_DIAGNOSTIC_PORTABLE_PASS: 2', 'RU_DIAGNOSTIC_PORTABLE_PASS: 1'),
                    'backend': ('BACKEND: c', 'BACKEND: python'), 'fields': ('generation=9', 'generation=8'),
                    'private': ('PASS: fixture', 'PASS: PRIVATE_BODY_SENTINEL'),
                    'skip': ('PASS: fixture', 'SKIP: fixture'), 'extra': ('TOTAL PASS: 10', 'TOTAL PASS: 10\nunexpected')}
                path.write_text(text.replace(*replacements[mutation]))
            with patch.object(ci, 'helper_policy_inputs', return_value=inputs), self.subTest(mutation=mutation), self.assertRaises((RuntimeError, FileNotFoundError)):
                ci.helper_policy_action('verify', self.root)

    def test_ru_timer_fixture_is_exact_unicode_megabyte_with_bounded_head_tail_probes(self):
        data, probes = ci.gui_ru_timer_fixture()
        self.assertEqual(len(data), 1000000)
        self.assertTrue(data.decode('utf-8').startswith('值 取 1.\n'))
        self.assertTrue(data.decode('utf-8').endswith('显 987654.\n'))
        self.assertEqual(sum(probe['length'] for probe in probes.values()), 16)
        for label, token in (('head_identifier', '值'), ('head_keyword', '取'), ('head_number', '1'),
                             ('tail_keyword', '显'), ('tail_number', '987654')):
            probe = probes[label]
            self.assertEqual(data[probe['offset']:probe['offset'] + probe['length']], token.encode())
            self.assertTrue(probe['offset'] < 16 if label.startswith('head') else probe['offset'] > 999980)

    def test_ru_timer_acceptance_requires_exact_source_probe_schema_and_real_finite_metrics(self):
        good = next(case for case in self.acceptance()['tests'] if case['name'] == 'main-gui-ru-syntax')['timer_performance']
        import copy
        for field, value in [('size', 999999), ('source_sha256', 'different'),
                             ('style_probes', {}), ('probes', 0), ('probes', True),
                             ('wall_ms', 30001), ('wall_ms', float('nan')),
                             ('first_head_style_ms', -1), ('first_head_style_ms', 101),
                             ('first_head_style_ms', None),
                             ('max_response_ms', float('inf')), ('max_response_ms', -1),
                             ('max_response_ms', 101)]:
            record = copy.deepcopy(good)
            record[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(RuntimeError):
                ci.validate_gui_ru_timer(record)
        for field in good:
            record = copy.deepcopy(good)
            record.pop(field)
            with self.subTest(missing=field), self.assertRaises(RuntimeError):
                ci.validate_gui_ru_timer(record)
        summary = self.acceptance()
        next(case for case in summary['tests'] if case['name'] == 'main-gui-ru-syntax').pop('timer_performance')
        with self.assertRaisesRegex(RuntimeError, 'timer performance'):
            ci.validate_acceptance(summary)

    def ru_gui_measurement_text(self, marker):
        if marker == 'RU_GUI_SYNC':
            return ('RU_GUI_SYNC size=1000000 source_chars=636370 wall_ms=100 read_bytes=1000000 '
                    'max_read=1024 max_tick_ms=3 max_chunk_ms=1 chunks=1000')
        return ('RU_GUI_TIMER size=1000000 source_chars=636370 wall_ms=100 ticks=10 '
                'work_ms=40 gap_ms=50 max_tick_ms=4 max_gap_ms=6 read_bytes=1000000 '
                'max_read=1024 chunks=1000 feed=1000000 bytes=1000000 pending=0 '
                'text_notifications=0 style_notifications=0 fold_notifications=0 '
                'posts=9 continuation_ticks=8 queue_yields=2 stale_messages=0')

    def ru_performance_text(self):
        return '\n'.join(f'PERF_RU size={size} initial_ms=100 edit_ms=2 '
                         f'initial_read_bytes={size} edit_read_bytes=1024 '
                         f'reused_bytes={size - 1024} max_read=1024 max_tick_ms=3 max_chunk_ms=1'
                         for size in ci.RU_PERFORMANCE_SIZES)

    def gui_ru_edits(self, mode='normal'):
        original, probes, folds, positions = ci.gui_ru_edit_fixture()
        source = self.root / '代表源码 😀.ru'
        source.write_bytes(original)
        record = {'size': len(original), 'source_sha256': ci.sha(source), 'style_probes': probes,
                  'fold_probes': folds, 'measurement': ci.GUI_RU_EDIT_MEASUREMENT,
                  'operations': [], 'undo_commands': 0}
        process = type('Process', (), {'pid': 123, 'poll': lambda self: None})()
        class EditWindows:
            def __init__(self):
                self.data = original
                self.inserted = None
                self.history = []
                self.caret = 0
                self.input_count = 0
                self.rounds = 2
                self.inputs = []
                self.commands = []
                self.drops = []
                self.byte_queries = []
            def editor(self, _): return 456
            def control(self, _, identifier): return identifier
            def no_dialog(self, _): return []
            def responsive(self, _):
                self.rounds += 1
                if mode == 'unresponsive' and self.input_count: raise RuntimeError('WM_NULL timed out')
            def drop(self, target, paths):
                self.drops.append((target, paths))
            def text(self, hwnd):
                if hwnd == 11:
                    return 'Ru Styling Ru...' if self.rounds < 2 or (mode == 'pending' and self.input_count) else 'UTF-8 Ru'
                return source.name + ' · ru_notepad'
            def active_probes(self):
                shifted = {name: dict(probe, offset=probe['offset'] + int(self.inserted is not None and probe['offset'] >= self.inserted))
                           for name, probe in probes.items()}
                if self.inserted is not None:
                    shifted['new'] = {'offset': self.inserted, 'length': 1,
                                      'style': 1 if self.inserted == len(original) else 8}
                return shifted
            def scalar(self, hwnd, message, wparam=0, lparam=0):
                if message == 0x1304: return 4
                if hwnd != 456: raise AssertionError('Edit messages must target the actual child')
                if message == 2025:
                    if lparam: raise AssertionError('Caret position must be scalar')
                    self.caret = wparam
                    return 0
                if message == 2008: return self.caret + int(mode == 'wrong-caret')
                if message in (0x0102, 0x0100):
                    if lparam != 1: raise AssertionError('Expected a scalar real key repeat count')
                    self.history.append((self.data, self.inserted))
                    self.inputs.append((message, wparam, self.caret))
                    self.input_count += 1
                    self.rounds = 0
                    if message == 0x0102:
                        if wparam != ord('x'): raise AssertionError('Only the reviewed ASCII edit is permitted')
                        self.inserted = self.caret
                        self.data = self.data[:self.caret] + (b'y' if mode == 'wrong-context' else b'x') + self.data[self.caret:]
                        self.caret += 1
                    else:
                        if wparam != 8: raise AssertionError('Delete must use actual Backspace')
                        self.data = self.data[:self.caret - 1] + self.data[self.caret:]
                        self.caret -= 1
                        self.inserted = None
                    return 0
                if message == 0x0101:
                    if (wparam, lparam) != (8, 0xc0000001): raise AssertionError('Expected Backspace release')
                    return 0
                if lparam: raise AssertionError('No pointer-bearing editor query is allowed')
                if message == 2006: return len(self.data) + int(mode == 'wrong-length' and self.input_count > 0)
                if message == 2159:
                    if mode == 'lost-dirty' and self.input_count: return 0
                    if mode == 'undo-dirty' and self.input_count: return 1
                    return int(bool(self.history))
                if message == 2028: return len(self.data) - int(mode == 'endstyled-only' and self.input_count > 0)
                if message == 2174: return int(bool(self.history) and mode != 'lost-undo')
                if message == 2010:
                    if mode == 'wrong-style' and self.input_count: return 0
                    return next((probe['style'] for probe in self.active_probes().values()
                                 if probe['offset'] <= wparam < probe['offset'] + probe['length']), 0)
                if message == 2223:
                    if mode == 'wrong-fold' and self.input_count: return 0x400
                    return next((probe['level'] for probe in folds if probe['line'] == wparam), 0x400)
                if message == 2007:
                    self.byte_queries.append(wparam)
                    return self.data[wparam]
                raise AssertionError(f'Unexpected private message {message}')
            def command(self, _, identifier):
                self.commands.append(identifier)
                if identifier == 504:
                    if mode == 'changed-source': source.write_bytes(b'changed')
                elif identifier == 201:
                    if mode != 'undo-noop':
                        self.data, self.inserted = self.history.pop()
                    self.rounds = 2
                else: raise AssertionError('Unexpected edit menu command')
        api = EditWindows()
        ticks = [0.0]
        def perf_counter():
            ticks[0] += 0.1
            return ticks[0]
        with patch.object(ci.time, 'perf_counter', side_effect=perf_counter), patch.object(ci.time, 'sleep'):
            try:
                checks = ci.run_gui_ru_edits(api, process, 123, source, record)
                result = {'passed': True, **checks}
            except RuntimeError as exc:
                result = {'passed': False, 'error': str(exc)}
        return result, api, record

    def test_real_gui_edit_stage_uses_six_scalar_child_inputs_exact_context_and_bounded_undo(self):
        result, api, record = self.gui_ru_edits()
        self.assertTrue(result['passed'], result.get('error'))
        self.assertTrue(all(result[name] for name in ci.GUI_RU_EDIT_CHECKS))
        ci.validate_gui_ru_edits(record)
        self.assertEqual(api.input_count, 6)
        self.assertEqual(api.commands, [504] * 6 + [201] * 6)
        self.assertEqual(api.drops[0][0], 456)
        self.assertEqual(api.history, [])
        self.assertEqual(api.data, ci.gui_ru_edit_fixture()[0])
        self.assertLessEqual(len(api.byte_queries), 6 * 16)
        for actual, expected in zip(api.inputs, ci.gui_ru_edit_operations()):
            self.assertEqual(actual[2], expected['position'] + int(expected['operation'] == 'delete'))
            self.assertEqual(actual[0], 0x0102 if expected['operation'] == 'insert' else 0x0100)
        self.assertTrue(all(item['probes'] == 2 for item in record['operations']))

    def test_real_gui_edits_reject_wrong_bytes_styles_folds_pending_dirty_length_caret_and_undo(self):
        for mode in ('unresponsive', 'pending', 'wrong-context', 'wrong-length', 'wrong-caret',
                     'lost-dirty', 'endstyled-only', 'wrong-style', 'wrong-fold', 'changed-source',
                     'lost-undo', 'undo-noop', 'undo-dirty'):
            with self.subTest(mode=mode):
                result, api, record = self.gui_ru_edits(mode)
                self.assertFalse(result['passed'])
                self.assertIn('error', result)
                self.assertLessEqual(record['undo_commands'], 6)
                if mode in ('pending', 'wrong-context', 'wrong-length', 'lost-dirty',
                            'endstyled-only', 'wrong-style', 'wrong-fold'):
                    self.assertIn('30 seconds', result['error'])
                    self.assertGreater(record['operations'][-1]['wall_ms'], 30000)

    def test_edit_performance_requires_exact_fixture_all_six_operations_and_finite_deadlines(self):
        import copy
        good = next(case for case in self.acceptance()['tests'] if case['name'] == 'main-gui-ru-syntax')['edit_performance']
        ci.validate_gui_ru_edits(good)
        for mutation in ('size', 'source', 'style', 'fold', 'measurement', 'missing', 'extra', 'order',
                         'position', 'before', 'after', 'timeout', 'nan', 'response', 'probes', 'undo'):
            with self.subTest(mutation=mutation):
                record = copy.deepcopy(good)
                if mutation == 'size': record['size'] = 99999
                if mutation == 'source': record['source_sha256'] = 'different'
                if mutation == 'style': record['style_probes']['head_keyword']['style'] = 0
                if mutation == 'fold': record['fold_probes'][0]['level'] = 0x400
                if mutation == 'measurement': record['measurement'] = 'wrong metric definition'
                if mutation == 'missing': record['operations'].pop()
                if mutation == 'extra': record['operations'].append(record['operations'][-1])
                if mutation == 'order': record['operations'].reverse()
                if mutation == 'position': record['operations'][0]['position'] = 1
                if mutation == 'before': record['operations'][0]['before_size'] = 99999
                if mutation == 'after': record['operations'][0]['after_size'] = 100000
                if mutation == 'timeout': record['operations'][0]['wall_ms'] = 30001
                if mutation == 'nan': record['operations'][0]['wall_ms'] = float('nan')
                if mutation == 'response': record['operations'][0]['max_response_ms'] = 101
                if mutation == 'probes': record['operations'][0]['probes'] = 0
                if mutation == 'undo': record['undo_commands'] = 7
                with self.assertRaises(RuntimeError): ci.validate_gui_ru_edits(record)
        summary = self.acceptance()
        next(case for case in summary['tests'] if case['name'] == 'main-gui-ru-syntax').pop('edit_performance')
        with self.assertRaisesRegex(RuntimeError, 'edit performance'):
            ci.validate_acceptance(summary)

    def test_same_source_measurements_require_exact_finite_fixture_bound_records(self):
        data, _ = ci.gui_ru_timer_fixture()
        for marker in ci.RU_GUI_MEASUREMENTS:
            with self.subTest(marker=marker):
                record = ci.parse_ru_gui_measurement(self.ru_gui_measurement_text(marker), marker)
                self.assertEqual(record['size'], 1000000)
                self.assertEqual(record['source_chars'], 636370)
                self.assertEqual(record['source_sha256'], hashlib.sha256(data).hexdigest())
                self.assertEqual(set(record), set.union(*ci.RU_GUI_MEASUREMENTS[marker]) | {'source_sha256'})
        # The synchronous comparison has no invented hardware-independent SLA.
        record = ci.parse_ru_gui_measurement(self.ru_gui_measurement_text('RU_GUI_SYNC'), 'RU_GUI_SYNC')
        record['wall_ms'] = 123456
        ci.validate_ru_gui_measurement(record, 'RU_GUI_SYNC')

    def test_same_source_parser_rejects_missing_duplicate_malformed_nonfinite_and_wrong_fixture(self):
        for marker in ci.RU_GUI_MEASUREMENTS:
            valid = self.ru_gui_measurement_text(marker)
            variants = ['', valid + '\n' + valid, valid.replace(marker, marker + '_BAD'),
                valid.replace('size=1000000', 'size=999999'),
                valid.replace('source_chars=636370', 'source_chars=1000000'),
                valid.replace('source_chars=636370 ', ''),
                valid.replace('wall_ms=100', 'wall_ms=NaN'),
                valid.replace('wall_ms=100', 'wall_ms=inf'),
                valid.replace('wall_ms=100', 'wall_ms=-1'),
                valid.replace('max_read=1024', 'max_read=1025'),
                valid.replace('max_read=1024', 'max_read=0'),
                valid.replace('max_read=1024', 'max_read=1024.0'),
                valid.replace('max_read=1024', 'max_read=bad'),
                valid.replace('max_read=1024', 'max_read=1024=1024'),
                valid.replace('max_read=1024', 'max_read'),
                valid.replace('max_read=1024', 'max_read=1024 max_read=1024'),
                valid.replace('max_read=1024', 'unexpected=1024'),
                valid.replace('read_bytes=1000000', 'read_bytes=999999'),
                valid.replace('read_bytes=1000000', 'read_bytes=1000001'),
                valid.replace('chunks=1000', 'chunks=0')]
            for output in variants:
                with self.subTest(marker=marker, output=output), self.assertRaises(RuntimeError):
                    ci.parse_ru_gui_measurement(output, marker)

    def test_same_source_timer_requires_complete_30s_bounded_production_notification_work(self):
        marker = 'RU_GUI_TIMER'
        valid = self.ru_gui_measurement_text(marker)
        for old, new in [('wall_ms=100', 'wall_ms=30001'), ('ticks=10', 'ticks=0'),
                         ('work_ms=40', 'work_ms=101'), ('gap_ms=50', 'gap_ms=101'),
                         ('max_tick_ms=4', 'max_tick_ms=0'),
                         ('max_tick_ms=4', 'max_tick_ms=41'), ('max_gap_ms=6', 'max_gap_ms=51'),
                         ('work_ms=40', 'work_ms=NaN'), ('gap_ms=50', 'gap_ms=inf'),
                         ('feed=1000000', 'feed=999999'), ('bytes=1000000', 'bytes=999999'),
                         ('pending=0', 'pending=1'), ('pending=0', 'pending=2'),
                         ('text_notifications=0', 'text_notifications=-1'),
                         ('style_notifications=0', 'style_notifications=1'),
                         ('fold_notifications=0', 'fold_notifications=1'),
                         ('posts=9', 'posts=0'), ('posts=9', 'posts=7'),
                         ('continuation_ticks=8', 'continuation_ticks=0'),
                         ('continuation_ticks=8', 'continuation_ticks=11'),
                         ('queue_yields=2', 'queue_yields=-1'),
                         ('stale_messages=0', 'stale_messages=-1')]:
            with self.subTest(old=old, new=new), self.assertRaises(RuntimeError):
                ci.parse_ru_gui_measurement(valid.replace(old, new), marker)
        # A genuine text callback is legal; styling/folding callbacks are excluded.
        ci.parse_ru_gui_measurement(valid.replace('text_notifications=0', 'text_notifications=1'), marker)

    def test_acceptance_rechecks_every_same_source_field_and_rejects_incomplete_progress(self):
        import copy
        for name, (marker, key) in ci.RU_GUI_CONSOLE_MEASUREMENTS.items():
            good = self.acceptance()
            test = next(item for item in good['tests'] if item['name'] == name)
            for field in test[key]:
                for mutation in ('missing', 'wrong-type'):
                    with self.subTest(name=name, field=field, mutation=mutation):
                        summary = copy.deepcopy(good)
                        record = next(item for item in summary['tests'] if item['name'] == name)[key]
                        if mutation == 'missing': record.pop(field)
                        elif field == 'source_sha256': record[field] = 'different'
                        else: record[field] = True
                        with self.assertRaises(RuntimeError): ci.validate_acceptance(summary)
            summary = copy.deepcopy(good)
            next(item for item in summary['tests'] if item['name'] == name).pop(key)
            with self.assertRaises(RuntimeError): ci.validate_acceptance(summary)

    def test_timer_console_records_diagnostics_before_nonzero_failure_without_blessing_it(self):
        marker = 'RU_GUI_TIMER'
        complete = self.ru_gui_measurement_text(marker)
        partial = (complete.replace('wall_ms=100', 'wall_ms=30001')
                   .replace('read_bytes=1000000', 'read_bytes=471040')
                   .replace('feed=1000000', 'feed=470180').replace('bytes=1000000', 'bytes=470180')
                   .replace('pending=0', 'pending=1'))
        zero_record = ci.parse_ru_gui_measurement(complete, marker)
        for field in ci.RU_GUI_TIMER_INTEGER_FIELDS | ci.RU_GUI_TIMER_TIME_FIELDS:
            if field not in {'size', 'source_chars'}: zero_record[field] = 0
        zero_record.update(pending=1, wall_ms=30001)
        zero = marker + ' ' + ' '.join(f'{field}={value}' for field, value in zero_record.items()
                                     if field != 'source_sha256')
        for label, measurement, exit_code in [('success', complete, 0), ('complete-nonzero', complete, 7),
                                               ('partial-nonzero', partial, 7), ('partial-zero', partial, 0),
                                               ('zero-nonzero', zero, 7), ('zero-zero', zero, 0),
                                               ('no-measurement', '', 0), ('duplicate', complete + '\n' + complete, 0)]:
            with self.subTest(label=label):
                evidence = self.root / label
                evidence.mkdir()
                output = 'PASS: fixture\n' * 8 + measurement + '\nTOTAL PASS: 8\n'
                with patch.object(ci, 'cleanup_process', side_effect=kill_synthetic):
                    result = ci.run_console(NoDialogs(), 'app_ru_timer_native',
                        [sys.executable, '-c', f'print({output!r}); raise SystemExit({exit_code})'],
                        evidence, r'^TOTAL PASS: 8\s*$', expected_assertions=8)
                self.assertEqual(result['passed'], label == 'success')
                self.assertEqual(result['exit_code'], exit_code)
                if measurement and label != 'duplicate':
                    self.assertIn('timer_performance', result)
                if exit_code:
                    self.assertIn('nonzero exit status', result['error'])
                if label.startswith('zero'):
                    self.assertEqual(result['timer_performance']['ticks'], 0)
                    self.assertEqual(result['timer_performance']['bytes'], 0)
                    self.assertEqual(result['timer_performance']['pending'], 1)
                if label.startswith('partial'):
                    self.assertEqual(result['timer_performance']['feed'], 470180)
                    self.assertEqual(result['timer_performance']['read_bytes'], 471040)
                    self.assertEqual(result['timer_performance']['bytes'], 470180)
                    self.assertEqual(result['timer_performance']['pending'], 1)

    def test_timer_console_retains_flushed_partial_measurement_after_outer_timeout(self):
        evidence = self.root / 'timeout'
        evidence.mkdir()
        partial = (self.ru_gui_measurement_text('RU_GUI_TIMER')
                   .replace('read_bytes=1000000', 'read_bytes=1024')
                   .replace('feed=1000000', 'feed=1000').replace('bytes=1000000', 'bytes=1000')
                   .replace('pending=0', 'pending=1'))
        code = f'import time; print({partial!r}, flush=True); time.sleep(10)'
        with patch.object(ci, 'cleanup_process', side_effect=kill_synthetic):
            result = ci.run_console(NoDialogs(), 'app_ru_timer_native', [sys.executable, '-c', code],
                evidence, r'^TOTAL PASS: 8\s*$', timeout=0.3, expected_assertions=8)
        self.assertFalse(result['passed'])
        self.assertTrue(result['cleanup_killed'])
        self.assertEqual(result['timer_performance']['pending'], 1)
        self.assertIn('execution deadline', result['error'])

    def test_ru_performance_requires_both_sizes_with_exact_finite_fields(self):
        records = ci.parse_ru_performance(self.ru_performance_text())
        self.assertEqual([record['size'] for record in records], [100000, 1000000])
        for record in records:
            self.assertEqual(set(record), ci.RU_PERFORMANCE_FIELDS)
            self.assertEqual(record['initial_read_bytes'], record['size'])
            self.assertEqual(record['max_read'], 1024)
        # Large measured times are reported, not silently discarded or assigned
        # a fabricated hardware-independent latency requirement.
        records[0]['initial_ms'] = 123456.25
        ci.validate_ru_performance(records)

    def test_ru_performance_rejects_missing_duplicate_and_unbounded_records(self):
        valid = self.ru_performance_text()
        variants = [
            '', valid.splitlines()[0], valid + '\n' + valid.splitlines()[0],
            valid.replace('size=1000000 ', 'size=100000 '),
            valid.replace('initial_ms=100', 'initial_ms=NaN'),
            valid.replace('edit_ms=2', 'edit_ms=inf'),
            valid.replace('max_tick_ms=3', 'max_tick_ms=-1'),
            valid.replace('max_chunk_ms=1', 'max_chunk_ms=NaN'),
            valid.replace('max_read=1024', 'max_read=1025'),
            valid.replace('max_read=1024', 'max_read=0'),
            valid.replace('edit_read_bytes=1024', 'edit_read_bytes=65537'),
            valid.replace('edit_read_bytes=1024', 'edit_read_bytes=0'),
            valid.replace('initial_read_bytes=100000 ', 'initial_read_bytes=99999 '),
            valid.replace('reused_bytes=98976', 'reused_bytes=0'),
            valid.replace('reused_bytes=98976', 'reused_bytes=100001'),
            valid.replace('max_read=1024', 'max_read=1024.0'),
            valid.replace('max_read=1024', 'max_read=1024 max_read=1024'),
            valid.replace('max_read=1024', 'unexpected=1024'),
            valid.replace('max_read=1024', 'max_read=bad'),
            valid.replace('max_read=1024', 'max_read=1024=1024'),
            valid.replace('max_read=1024', 'max_read'),
            valid.replace('PERF_RU ', 'PERF_RU_BAD '),
        ]
        for text in variants:
            with self.subTest(text=text):
                with self.assertRaisesRegex(RuntimeError, 'Ru performance'):
                    ci.parse_ru_performance(text)

    def test_acceptance_revalidates_ru_performance_records(self):
        for mutation in ('missing', 'oversized-read', 'no-convergence', 'nonfinite-time'):
            with self.subTest(mutation=mutation):
                summary = self.acceptance()
                result = next(test for test in summary['tests'] if test['name'] == 'ru_syntax_native')
                if mutation == 'missing': result.pop('performance')
                if mutation == 'oversized-read': result['performance'][0]['max_read'] = 1025
                if mutation == 'no-convergence': result['performance'][0]['reused_bytes'] = 0
                if mutation == 'nonfinite-time': result['performance'][0]['max_tick_ms'] = float('nan')
                with self.assertRaisesRegex(RuntimeError, 'Ru performance'):
                    ci.validate_acceptance(summary)

    def test_ru_console_requires_measurements_in_addition_to_exact_assertions(self):
        for measured in (True, False):
            with self.subTest(measured=measured):
                evidence = self.root / str(measured)
                evidence.mkdir()
                output = 'PASS: synthetic\nTOTAL PASS: 1\n'
                if measured:
                    output += self.ru_performance_text() + '\n' + self.ru_gui_measurement_text('RU_GUI_SYNC')
                with patch.object(ci, 'cleanup_process', side_effect=kill_synthetic):
                    result = ci.run_console(NoDialogs(), 'ru_syntax_native',
                        [sys.executable, '-c', f'print({output!r})'], evidence,
                        r'^TOTAL PASS: 1\s*$', expected_assertions=1)
                self.assertEqual(result['passed'], measured)
                if measured:
                    self.assertEqual(len(result['performance']), 2)
                else:
                    self.assertIn('Ru performance', result['error'])

    def native_build_fixture(self):
        for relative in (*ci.portable.NATIVE_BUILD_DRIVERS,
                         *(source for sources in ci.portable.NATIVE_COMPILE_SOURCES.values() for source in sources),
                         'native/ru_scan.h', 'native/ru_unicode_data.h'):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('synthetic native input: ' + relative, encoding='utf-8')
        compiler = self.root / 'synthetic-cc'
        compiler.write_bytes(b'synthetic compiler binary')
        def compile_fixture(command, **kwargs):
            self.assertEqual(kwargs['cwd'], self.root)
            destination = Path(command[command.index('-o') + 1])
            destination.write_bytes(('synthetic DLL ' + destination.stem).encode())
        return compiler, compile_fixture

    def test_native_helper_cache_requires_exact_inputs_compiler_flags_and_dll_bytes(self):
        compiler, compile_fixture = self.native_build_fixture()
        build_dir = self.root / 'build'
        with patch.object(builder, 'ROOT', self.root), \
             patch.object(builder.subprocess, 'check_output', return_value=b'synthetic compiler version'), \
             patch.object(builder, 'run', side_effect=compile_fixture) as run:
            first = builder.build_native_helpers(str(compiler), build_dir)
            self.assertEqual(run.call_count, 2)
            self.assertEqual(builder.build_native_helpers(str(compiler), build_dir), first)
            self.assertEqual(run.call_count, 2, 'Unchanged inputs must reuse exact cached bytes')
            (build_dir / 'native-helper' / ci.portable.NATIVE_HELPER_NAME).write_bytes(b'tampered cached DLL')
            builder.build_native_helpers(str(compiler), build_dir)
            self.assertEqual(run.call_count, 3, 'Tampered DLL must rebuild, never bless its changed bytes')
            for relative in ('native/ru_unicode_data.h', 'native/ru_scan.h', 'native/ru_wrong_abi.c', 'tools/build.py'):
                with self.subTest(changed=relative):
                    before = run.call_count
                    with (self.root / relative).open('a') as stream: stream.write('\nchanged')
                    builder.build_native_helpers(str(compiler), build_dir)
                    self.assertEqual(run.call_count, before + 2)
            before = run.call_count
            compiler.write_bytes(b'changed compiler binary')
            builder.build_native_helpers(str(compiler), build_dir)
            self.assertEqual(run.call_count, before + 2)
            before = run.call_count
            with patch.object(builder, 'NATIVE_CFLAGS', builder.NATIVE_CFLAGS + ('-DSYNTHETIC=1',)):
                builder.build_native_helpers(str(compiler), build_dir)
            self.assertEqual(run.call_count, before + 2)

    def test_native_helper_changed_input_during_compilation_never_publishes_receipt(self):
        compiler, compile_fixture = self.native_build_fixture()
        def mutate(command, **kwargs):
            compile_fixture(command, **kwargs)
            (self.root / 'native/ru_unicode_data.h').write_text('changed during compilation')
        with patch.object(builder, 'ROOT', self.root), \
             patch.object(builder.subprocess, 'check_output', return_value=b'synthetic compiler version'), \
             patch.object(builder, 'run', side_effect=mutate):
            with self.assertRaisesRegex(RuntimeError, 'inputs changed during compilation'):
                builder.build_native_helpers(str(compiler), self.root / 'build')
        self.assertEqual(list((self.root / 'build/native-helper').iterdir()), [])

    def test_native_helper_copy_preserves_both_exact_dlls_and_receipts(self):
        compiler, compile_fixture = self.native_build_fixture()
        build_dir = self.root / 'build'
        destination = self.root / 'bin'
        destination.mkdir()
        with patch.object(builder, 'ROOT', self.root), \
             patch.object(builder.subprocess, 'check_output', return_value=b'synthetic compiler version'), \
             patch.object(builder, 'run', side_effect=compile_fixture):
            builder.build_native_helpers(str(compiler), build_dir)
            builder.copy_native_helpers(build_dir, destination)
        expected = {filename for name in ci.portable.NATIVE_COMPILE_SOURCES
                    for filename in (name, Path(name).stem + '.native-build.json')}
        self.assertEqual({path.name for path in destination.iterdir()}, expected)
        for name in expected:
            self.assertEqual((destination / name).read_bytes(), (build_dir / 'native-helper' / name).read_bytes())

    def test_helper_failure_layouts_keep_lexilla_and_isolate_only_helper(self):
        for name, mode in ci.HELPER_FALLBACK_LAYOUTS.items():
            with self.subTest(name=name):
                layout = ci.syntax_fallback_layout(name)
                self.assertEqual(layout['Lexilla.dll'], 'Lexilla.dll')
                self.assertEqual(layout['Scintilla.dll'], 'Scintilla.dll')
                if mode == 'missing':
                    self.assertNotIn(ci.portable.NATIVE_HELPER_NAME, layout)
                else:
                    expected = 'Scintilla.dll' if mode == 'bad-exports' else ci.portable.NATIVE_WRONG_ABI_NAME
                    self.assertEqual(layout[ci.portable.NATIVE_HELPER_NAME], expected)
        for name in ('syntax_missing_lexilla', 'syntax_bad_lexer', 'ru_syntax_missing_lexilla'):
            self.assertEqual(ci.syntax_fallback_layout(name)[ci.portable.NATIVE_HELPER_NAME], ci.portable.NATIVE_HELPER_NAME)

    def test_receipt_paths_are_portable_on_windows(self):
        build = (ci.ROOT / 'tools/build.py').read_text(encoding='utf-8')
        self.assertNotIn('str(p.relative_to(ROOT))', build)
        self.assertNotIn('str(source.relative_to(ROOT))', build)
        self.assertEqual(build.count('p.relative_to(ROOT).as_posix()'), 1)
        self.assertIn('source.relative_to(ROOT).as_posix()', build)

    def test_build_snapshot_includes_imported_test_helpers(self):
        for folder in ('src', 'tests'):
            (self.root / folder).mkdir()
        (self.root / 'src/main.ru').write_text('main source')
        (self.root / 'tests/entry.ru').write_text('test entry')
        helper = self.root / 'tests/imported_helper.ru'
        helper.write_text('helper source')
        for relative in ('native/ru_scan.c', 'native/ru_wrong_abi.c', 'native/ru_scan.h', 'native/ru_unicode_data.h',
                         'native/ru_markdown_fold.c', 'native/ru_markdown_fold.h'):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('native input')
        with patch.object(builder, 'ROOT', self.root):
            before = builder.source_snapshot()
            self.assertEqual(set(before), {'src/main.ru', 'tests/entry.ru', 'tests/imported_helper.ru',
                'native/ru_scan.c', 'native/ru_wrong_abi.c', 'native/ru_scan.h', 'native/ru_unicode_data.h',
                'native/ru_markdown_fold.c', 'native/ru_markdown_fold.h'})
            helper.write_text('changed helper source')
            after = builder.source_snapshot()
        self.assertNotEqual(before['tests/imported_helper.ru'], after['tests/imported_helper.ru'])
        self.assertTrue(all('\\' not in name and ':' not in name for name in after))

    def test_acceptance_rejects_each_missing_or_duplicated_required_group(self):
        complete = self.acceptance()
        for name in (case['name'] for case in complete['tests']):
            with self.subTest(name=name):
                summary = self.acceptance()
                summary['tests'] = [case for case in summary['tests'] if case['name'] != name]
                with self.assertRaisesRegex(RuntimeError, 'inventory'):
                    ci.validate_acceptance(summary)
                summary['tests'].append(summary['tests'][0])
                with self.assertRaisesRegex(RuntimeError, 'inventory'):
                    ci.validate_acceptance(summary)

    def test_acceptance_rejects_skip_kill_and_unexecuted_each_required_group(self):
        complete = self.acceptance()
        for name in (case['name'] for case in complete['tests']):
            for key, value in (('skips', ['SKIP: case']), ('cleanup_killed', True), ('executed', False)):
                with self.subTest(name=name, key=key):
                    summary = self.acceptance()
                    next(case for case in summary['tests'] if case['name'] == name)[key] = value
                    with self.assertRaisesRegex(RuntimeError, 'did not pass normally'):
                        ci.validate_acceptance(summary)

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

    def test_console_conflicting_streaming_total_fails(self):
        self.assertFalse(self.console("print('PASS: one'); print('FILE_STREAMING_TESTS_PASS=1'); print('TOTAL PASS: 1')")['passed'])

    def test_console_accepts_unique_streaming_marker_with_exact_assertions(self):
        with patch.object(ci, 'cleanup_process', side_effect=kill_synthetic):
            result = ci.run_console(NoDialogs(), 'fixture', [sys.executable, '-c',
                "print('PASS: synthetic'); print('FILE_STREAMING_TESTS_PASS=1')"], self.root,
                r'^FILE_STREAMING_TESTS_PASS=1\s*$', expected_assertions=1)
        self.assertTrue(result['passed'])

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

    def gui(self, mode='normal', bad_clock=None):
        binary = self.root / 'bin'
        evidence = self.root / 'evidence'
        binary.mkdir()
        evidence.mkdir()
        process = type('SyntheticProcess', (), {'pid': 12345, 'finished': mode == 'early',
            'returncode': 0, 'poll': lambda self: self.returncode if self.finished else None})()
        clock = [0.0]
        def perf_counter():
            clock[0] += 0.2
            if bad_clock is not None and clock[0] > 0.8:
                return bad_clock
            return clock[0]
        def launch(*_, **__):
            if mode != 'missing-log':
                lines = ['[launcher] Starting Ru program.', '[startup] menu installed',
                         '[startup] initial document ready', '[startup] main window shown',
                         '[launcher] Ru program returned with status 0.']
                if mode == 'bad-log':
                    lines[-1] = '[launcher] Ru program exited before returning to the launcher.'
                if mode == 'fold-metric-log':
                    lines.append(markdown_route_markers())
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
             patch.object(ci.time, 'perf_counter', side_effect=perf_counter), \
             patch.object(ci.time, 'sleep'):
            result = ci.run_gui(FakeWindows(), binary, evidence)
        return result, start

    def test_gui_persistent_bad_clock_preserves_failure_and_process_cleanup_evidence(self):
        for bad in (float('nan'), 0.0):
            for name in ('bin', 'evidence'): shutil.rmtree(self.root / name, ignore_errors=True)
            result, launch = self.gui(bad_clock=bad)
            with self.subTest(value=bad):
                self.assertFalse(result['passed'])
                self.assertTrue(result['executed'])
                self.assertTrue(result['cleanup_killed'])
                self.assertIn('performance clock', result['error'])
                self.assertIn('performance clock', result['clock_error'])
                self.assertIsNone(result['seconds'])
                self.assertGreaterEqual(result['last_good_seconds'], 0)
                self.assertEqual(launch.call_count, 1)
                self.assertTrue((self.root / 'evidence/main-launcher-0.log').is_file())

    def test_console_persistent_bad_final_clock_keeps_original_error_and_cleanup(self):
        failed = [False]
        class FailingApi:
            def no_dialog(self, pid):
                failed[0] = True
                raise RuntimeError('original synthetic dialog failure')
        def counter(): return float('nan') if failed[0] else 1.0
        with patch.object(ci, 'cleanup_process', side_effect=kill_synthetic), \
             patch.object(ci.time, 'perf_counter', side_effect=counter):
            result = ci.run_console(FailingApi(), 'bad-clock',
                [sys.executable, '-c', 'import time; time.sleep(5)'], self.root,
                r'^TOTAL PASS: 1\s*$', timeout=3, expected_assertions=1)
        self.assertFalse(result['passed'])
        self.assertTrue(result['executed'])
        self.assertTrue(result['cleanup_killed'])
        self.assertEqual(result['error'], 'original synthetic dialog failure')
        self.assertIn('performance clock', result['clock_error'])
        self.assertIsNone(result['seconds'])
        self.assertEqual(result['last_good_seconds'], 0.0)
        self.assertTrue((self.root / 'bad-clock.stdout.log').is_file())
        self.assertTrue((self.root / 'bad-clock.stderr.log').is_file())

    def test_final_clock_failure_never_keeps_success_or_loses_partial_fields(self):
        record = {'passed': True, 'executed': True, 'cleanup_killed': False, 'partial_bytes': 123}
        with patch.object(ci.time, 'perf_counter', side_effect=[2.0, float('nan')]):
            clock = ci.PerformanceClock()
            started = clock()
            ci.finish_result_clock(record, clock, started)
        self.assertFalse(record['passed'])
        self.assertEqual(record['partial_bytes'], 123)
        self.assertTrue(record['executed'])
        self.assertFalse(record['cleanup_killed'])
        self.assertIsNone(record['seconds'])
        self.assertFalse(record['seconds_valid'])
        self.assertEqual(record['last_good_seconds'], 0.0)
        self.assertEqual(record['error'], record['clock_error'])

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

    def test_bounded_fold_helper_is_mandatory_before_native_acceptance_and_not_packaged(self):
        script = (ci.ROOT / 'tools/windows_ci.ps1').read_text(encoding='utf-8')
        workflow = (ci.ROOT / '.github/workflows/windows.yml').read_text(encoding='utf-8')
        call = "Invoke-Checked $Python @('-I','tools/test_markdown_fold_helper.py',"
        self.assertEqual(script.count(call), 1)
        self.assertLess(script.index(call), script.index("$AcceptArgs = @('tools/windows_ci.py'"))
        block = script[script.index(call):script.index("    foreach ($test", script.index(call))]
        self.assertIn("'--runtime-dir',$Output", block)
        self.assertIn("'--cc',(Join-Path $Bin 'gcc.exe')", block)
        self.assertIn("'markdown-bulk-helper-controls.json'", block)
        self.assertIn('python -I tools/test_markdown_fold_helper.py --cc gcc --sanitize', workflow)
        self.assertIn("ASAN_OPTIONS: 'detect_leaks=1:halt_on_error=1:abort_on_error=1'", workflow)
        self.assertIn('mkdir -p build/markdown-fold-helper-evidence', workflow)
        self.assertIn('build/markdown-fold-helper-evidence/markdown-bulk-helper-controls.json', workflow)
        self.assertEqual(ci.portable.NATIVE_COMPILE_SOURCES['RuSyntax.dll'],
                         ('native/ru_scan.c', 'native/ru_markdown_fold.c'))
        self.assertIn('user32', ci.portable.NATIVE_LINK_LIBRARIES)
        for name in ('markdown_fold_windows.exe', 'markdown_fold_host.exe'):
            self.assertNotIn(name, ci.BINARY_NAMES)
            self.assertNotIn(name, ci.portable.TEST_NAMES)

    def test_optional_markdown_studies_are_separate_from_product_acceptance(self):
        script = (ci.ROOT / 'tools/windows_ci.ps1').read_text(encoding='utf-8')
        self.assertIn("[ValidateSet('native-baseline','cpu-profile')]", script)
        self.assertIn("$Stage = 'host_controls'", script)
        self.assertIn("$Stage = 'execution'", script)
        self.assertIn("measurement_claimed = $false", script)
        self.assertIn('$global:LASTEXITCODE = $SavedExit', script)
        self.assertIn('$global:LASTEXITCODE = $ProductExit', script)
        self.assertIn("Write-Host 'MARKDOWN_OPTIONAL_STUDY_EVIDENCE_UNAVAILABLE=1'", script)
        tail = script[script.index('    } else {\n        try {\n            Invoke-Checked $Python $AcceptArgs'):]
        self.assertLess(tail.index('Invoke-Checked $Python $AcceptArgs'), tail.index('Invoke-OptionalMarkdownStudy'))
        for name in ('native_baseline', 'cpu_profile'):
            self.assertIn('tools/test_markdown_' + name + '.py', tail)
            self.assertIn('tools/run_markdown_' + name + '.py', tail)
        self.assertNotIn('markdown_baseline.exe', ci.BINARY_NAMES)
        self.assertNotIn('markdown_baseline.exe', ci.portable.TEST_NAMES)

    def test_optional_markdown_powershell_preserves_product_exit_and_original_exception(self):
        pwsh = shutil.which('pwsh')
        if not pwsh:
            if os.name == 'nt':
                self.fail('Required Windows PowerShell optional-diagnostic control is unavailable')
            self.skipTest('PowerShell 7 unavailable on this non-Windows host')
        source = (ci.ROOT / 'tools/windows_ci.ps1').read_text(encoding='utf-8')
        match = re.search(r'^function Invoke-OptionalMarkdownStudy\(.*?^}', source, re.M | re.S)
        self.assertIsNotNone(match)
        script = self.root / 'optional-control.ps1'
        destination = str(self.root / 'study-evidence').replace("'", "''")
        script.write_text("$ErrorActionPreference='Stop'\nSet-StrictMode -Version Latest\n" +
            "function Invoke-Checked([string]$Command,[string[]]$Arguments) { " +
            "$global:Calls.Add($Arguments[0]); $global:LASTEXITCODE=0; " +
            "if ($Arguments[0] -like '*fail*') {$global:LASTEXITCODE=9; throw 'controlled command'} }\n" +
            match.group(0) + "\n$Evidence='" + destination + "'\n" +
            "New-Item -ItemType Directory -Path $Evidence | Out-Null\n" +
            "foreach($mode in @('success','controls-fail','run-fail','write-fail')) {\n" +
            "$global:Calls=[System.Collections.Generic.List[string]]::new(); $global:LASTEXITCODE=73\n" +
            "$c=if($mode -eq 'controls-fail'){'controls-fail'}else{'controls'}\n" +
            "$r=if($mode -in @('run-fail','write-fail')){'run-fail'}else{'run'}\n" +
            "$d=$Evidence; if($mode -eq 'write-fail') {$d=Join-Path $Evidence 'regular'; Set-Content -LiteralPath $d -Value x}\n" +
            "try { try {throw 'original product failure'} finally {\n" +
            "Invoke-OptionalMarkdownStudy 'unused' @($c) @($r) $d 'native-baseline'\n" +
            "} } catch {if($_.Exception.Message -ne 'original product failure'){throw 'product exception replaced'}}\n" +
            "if($global:LASTEXITCODE -ne 73){throw 'product exit changed'}\n" +
            "$expected=if($mode -eq 'controls-fail'){1}else{2}; if($global:Calls.Count -ne $expected){throw 'wrong command coverage'}\n" +
            "}\nWrite-Output 'OPTIONAL_DIAGNOSTICS_CONTROLS_PASSED'\n", encoding='utf-8', newline='\n')
        result = subprocess.run([pwsh, '-NoProfile', '-NonInteractive', '-File', str(script)],
                                capture_output=True, timeout=30, check=False)
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', errors='replace'))
        self.assertIn(b'OPTIONAL_DIAGNOSTICS_CONTROLS_PASSED', result.stdout)
        self.assertEqual(result.stderr, b'')

    def test_markdown_direct_gate_retains_original_inventory_and_requires_gc(self):
        summary = self.acceptance()
        direct = next(t for t in summary['tests'] if t['name'] == 'markdown_direct_native')
        prior = [t for t in summary['tests'] if t['name'] != 'markdown_direct_native']
        self.assertEqual(len(prior), 38)
        self.assertEqual(sum(t.get('assertions_passed', 0) for t in prior), 1867 + 90)
        self.assertEqual(direct['assertions_passed'], 114)
        self.assertEqual(ci.console_command('markdown_direct_native', self.root, self.root),
                         [str(self.root / 'markdown_direct_native.exe')])
        self.assertEqual(ci.CONSOLE_TIMEOUT_SECONDS['markdown_direct_native'], 180)
        self.assertIn('markdown_direct_native.exe', ci.portable.TEST_NAMES)
        self.assertNotIn('markdown_direct_native.exe', ci.portable.RUNTIME_NAMES)
        self.assertIn("'markdown_direct_native'", (ci.ROOT / 'tools/windows_ci.ps1').read_text(encoding='utf-8'))
        command = 'cmd /d /c "set RU_GC_THRESHOLD=64&&set RU_GC_STATS=1&&markdown_direct_native.exe"'
        self.assertIn(command + ' >>test-results.txt 2>&1\nif not "%ERRORLEVEL%"=="0" set "FAILED=1"',
                      (ci.ROOT / 'packaging/run-tests.cmd').read_text(encoding='utf-8'))
        for value in (None, {}, {'threshold': 64, 'stats_enabled': True, 'live': 0, 'freed': 0, 'collections': 1}):
            with self.subTest(value=value), self.assertRaisesRegex(RuntimeError, 'GC-stress'):
                direct['gc_stress'] = value
                ci.validate_acceptance(summary)

    def test_markdown_direct_gc_record_requires_actual_collection_and_exact_types(self):
        good = {'threshold': 64, 'stats_enabled': True, 'live': 0, 'freed': 100, 'collections': 4}
        ci.validate_markdown_direct_gc(good)
        for ending in ('\n', '\r\n'):
            self.assertEqual(ci.parse_markdown_direct_gc('RU_GC live=0 freed=100 collections=4' + ending), good)
        for field, value in (('threshold', 63), ('threshold', True), ('stats_enabled', 1),
                             ('live', -1), ('live', 2**53), ('freed', 0), ('freed', True),
                             ('collections', 1), ('collections', 2.0)):
            with self.subTest(field=field, value=value), self.assertRaises(RuntimeError):
                ci.validate_markdown_direct_gc(dict(good, **{field: value}))
        for text in ('', 'RU_GC live=0 freed=100 collections=4',
                     'RU_GC live=0 freed=100 collections=4\r',
                     'RU_GC live=0 freed=100 collections=1\n',
                     'RU_GC live=0 freed=100 collections=4\nextra\n',
                     'RU_GC live=0 freed=100 collections=4\n' * 2):
            with self.subTest(text=text), self.assertRaises(RuntimeError):
                ci.parse_markdown_direct_gc(text)

    def test_markdown_route_metric_parser_requires_exact_measured_three_route_shape(self):
        good, output = markdown_route_metrics(), markdown_route_markers()
        for text in (output, output.replace('\n', '\r\n')):
            self.assertEqual(ci.parse_markdown_route_metrics(text), good)
        for mutation in ('missing', 'duplicate', 'order', 'unknown', 'truncated', 'private',
                         'negative', 'float', 'leading-zero', 'overflow', 'no-bulk', 'line-bound',
                         'buffer', 'plan', 'mixed', 'no-fallback', 'no-perline', 'invalid-clock'):
            text = output
            if mutation == 'missing': text = ''.join(text.splitlines(keepends=True)[1:])
            elif mutation == 'duplicate': text += text.splitlines(keepends=True)[0]
            elif mutation == 'order': text = ''.join(reversed(text.splitlines(keepends=True)))
            elif mutation == 'unknown': text = text.replace('bulkCalls=', 'unknown=')
            elif mutation == 'truncated': text = text[:-1]
            elif mutation == 'private': text += 'FOLD_METRICS_PRIVATE_SENTINEL\n'
            elif mutation == 'negative': text = text.replace('bulkCalls=1', 'bulkCalls=-1')
            elif mutation == 'float': text = text.replace('bulkCalls=1', 'bulkCalls=1.0')
            elif mutation == 'leading-zero': text = text.replace('bulkCalls=1', 'bulkCalls=01')
            elif mutation == 'overflow': text = text.replace('bulkCalls=1', 'bulkCalls=9007199254740992')
            elif mutation == 'no-bulk': text = text.replace('bulkCalls=1', 'bulkCalls=0')
            elif mutation == 'line-bound': text = text.replace('bulkLines=1', 'bulkLines=65')
            elif mutation == 'buffer': text = text.replace('ownedBufferBytes=1088', 'ownedBufferBytes=1089')
            elif mutation == 'plan': text = text.replace('maxPlanBytes=48', 'maxPlanBytes=1057')
            elif mutation == 'mixed': text = text.replace('fallbackBatches=0', 'fallbackBatches=1', 1)
            elif mutation == 'no-fallback': text = text.replace('fallbackBatches=1', 'fallbackBatches=0')
            elif mutation == 'no-perline': text = text.replace('directCalls=1', 'directCalls=0')
            elif mutation == 'invalid-clock': text = text.replace('metric_valid=1', 'metric_valid=0')
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeError):
                ci.parse_markdown_route_metrics(text)
        for key in ci.FOLD_ROUTE_METRIC_FIELDS:
            for value in (-1, True, 1.5, '1', 2**53):
                records = json.loads(json.dumps(good))
                records[1][key] = value
                with self.subTest(key=key, value=value), self.assertRaises(RuntimeError):
                    ci.validate_markdown_route_metrics(records)
            records = json.loads(json.dumps(good))
            records[1].pop(key)
            with self.subTest(missing=key), self.assertRaises(RuntimeError):
                ci.validate_markdown_route_metrics(records)

    def test_markdown_route_metric_acceptance_binding_forbids_missing_or_other_groups(self):
        summary = self.acceptance()
        direct = next(row for row in summary['tests'] if row['name'] == 'markdown_direct_native')
        direct.pop('bulk_route_metrics')
        with self.assertRaisesRegex(RuntimeError, 'route metrics'):
            ci.validate_acceptance(summary)
        direct['bulk_route_metrics'] = markdown_route_metrics()
        other = next(row for row in summary['tests'] if row['name'] == 'document_policy')
        other['bulk_route_metrics'] = markdown_route_metrics()
        with self.assertRaisesRegex(RuntimeError, 'Unexpected Markdown'):
            ci.validate_acceptance(summary)

    def test_markdown_route_metric_console_forbids_foreign_marker(self):
        result = self.console('print("PASS: control");print("TOTAL PASS: 1");print(' + repr(markdown_route_markers()) + ')')
        self.assertFalse(result['passed'])
        self.assertIn('Unexpected Markdown route metric marker', result['error'])

    def test_markdown_route_metric_gui_forbids_foreign_marker(self):
        result, _ = self.gui(mode='fold-metric-log')
        self.assertFalse(result['passed'])
        self.assertIn('Unexpected Markdown route metric marker', result['error'])

    def test_markdown_route_metric_console_rejects_missing_current_stdout_receipt(self):
        code = "import sys;print('PASS: control');print('TOTAL PASS: 1');sys.stderr.write('RU_GC live=0 freed=100 collections=4\\n')"
        result = ci.run_console(NoDialogs(), 'markdown_direct_native', [sys.executable, '-c', code],
            self.root, r'^TOTAL PASS: 1\s*$', expected_assertions=1)
        self.assertFalse(result['passed'])
        self.assertIn('route metric marker', result['error'])
        self.assertNotIn('bulk_route_metrics', result)

    def test_markdown_direct_child_gc_environment_is_fixed_and_required(self):
        code = ("import os,sys\n"
                "assert os.environ['RU_GC_THRESHOLD'] == '64'\n"
                "assert os.environ['RU_GC_STATS'] == '1'\n"
                "print('PASS: child fixed GC environment')\nprint('TOTAL PASS: 1')\n"
                f'print({markdown_route_markers()!r}, end="")\n'
                "sys.stderr.write('RU_GC live=0 freed=100 collections=4\\n')\n")
        before = dict(os.environ)
        with patch.dict(os.environ, {'RU_GC_THRESHOLD': '999999', 'RU_GC_STATS': '0'}):
            result = ci.run_console(NoDialogs(), 'markdown_direct_native',
                                    [sys.executable, '-c', code], self.root,
                                    r'^TOTAL PASS: 1\s*$', expected_assertions=1)
            self.assertTrue(result['passed'], result)
            self.assertEqual(result['gc_stress']['collections'], 4)
            self.assertEqual(result['bulk_route_metrics'], markdown_route_metrics())
            self.assertEqual(os.environ['RU_GC_THRESHOLD'], '999999')
            self.assertEqual(os.environ['RU_GC_STATS'], '0')
        self.assertEqual(dict(os.environ), before)

    def test_callback_history_dispatch_is_literal_and_normal_product_is_separate(self):
        workflow = (ci.ROOT / '.github/workflows/windows.yml').read_text(encoding='utf-8')
        source = (ci.ROOT / 'tools/windows_ci.ps1').read_text(encoding='utf-8')
        historical = "d47b1836930c896fec29207e957880dd90c774c6"
        checkout = ("ref: ${{ github.event_name == 'workflow_dispatch' && "
                    "inputs.historical_callback && '" + historical + "' || github.sha }}")
        self.assertEqual(workflow.count(checkout), 2)
        self.assertIn('historical_callback:', workflow)
        self.assertIn('type: boolean', workflow)
        self.assertIn('default: false', workflow)
        self.assertNotIn('inputs.ref', workflow)
        baseline = workflow.split('      - name: Check out fixed pre-root-list research compiler', 1)[1]
        baseline = baseline.split('      - name:', 1)[0]
        self.assertIn("if: github.event_name == 'workflow_dispatch' && inputs.historical_callback", baseline)
        self.assertIn('ref: 95ee638f705f0fd75292da7eda150559dbe8fc3a', baseline)
        self.assertIn('[switch]$RunCallbackResearch', source)
        self.assertNotIn('-RunCallbackResearch', workflow)
        control_start = source.index('    if ($RunCallbackResearch) {')
        control_end = source.index("    Invoke-Checked $Python @('tools/test_markdown_portable.py'", control_start)
        self.assertIn("'tools/test_markdown_callback_cost.py'", source[control_start:control_end])
        execution = source[source.index('    if ($RunCallbackResearch) {', control_end):]
        self.assertIn('Invoke-ResearchThenAcceptance $Python $ResearchArgs $AcceptArgs', execution)
        self.assertIn('    } else {\n        try {\n            Invoke-Checked $Python $AcceptArgs\n        } finally {', execution)
        self.assertIn('-source-${{', workflow)
        self.assertIn('-trigger-${{ github.sha }}', workflow)
        # Historical runners and their exact source/parent checks are retained.
        runner = (ci.ROOT / 'tools/run_markdown_callback_cost.py').read_text(encoding='utf-8')
        self.assertIn("BASE_COMMIT = 'ce2ff998e778d9991462a78f245bd17cec32f940'", runner)
        self.assertIn("BASE_TREE = '115c353c5206967854d58d726afe280d5b4350c2'", runner)
        self.assertIn("'candidate_parent_mismatch'", runner)

    def test_markdown_gate_preserves_old_counts_and_requires_exact_new_counts(self):
        expected = {'markdown_policy': 221, 'markdown_selection_policy': 31,
                    'markdown_native': 58, 'app_markdown_native': 70, 'markdown_direct_native': 114}
        self.assertEqual({name: ci.expected_assertions(name) for name in expected}, expected)
        self.assertEqual(ci.console_command('app_markdown_native', self.root, self.root),
                         [str(self.root / 'app_markdown_native.exe'), str(self.root)])
        for name in [*expected, 'main-gui-markdown']:
            summary = self.acceptance()
            summary['tests'] = [case for case in summary['tests'] if case['name'] != name]
            with self.subTest(name=name), self.assertRaisesRegex(RuntimeError, 'inventory'):
                ci.validate_acceptance(summary)

    def test_markdown_selection_invalidates_native_prefix_and_requires_natural_paint(self):
        syntax = (ci.ROOT / 'src/syntax.ru').read_text(encoding='utf-8')
        selection = syntax.split('算 _选择 态 柄, 语言 为 句:', 1)[1].split('算 选择 柄 语言 为 句:', 1)[0]
        reset = '_发设 态 柄 2032 0 0.'
        self.assertEqual(selection.count(reset), 1)
        self.assertLess(selection.index('_清样式 态 柄.'), selection.index(reset))
        self.assertLess(selection.index(reset), selection.index('已选 取 标语 其 选择 柄.'))
        self.assertIn("若 语言 == 'markdown' 则\n        # CLEARDOCUMENTSTYLE", selection)
        self.assertNotIn('4003', selection)
        fixture = (ci.ROOT / 'tests/app_markdown_native.ru').read_text(encoding='utf-8')
        natural = fixture.split('作 验自然配色 主 柄 页:', 1)[1].split('作 验选择重入 主:', 1)[0]
        self.assertIn('2028 0 0) 其 数 == 0', natural)
        self.assertLess(natural.index('窗 其 发送 主 273 701 0.'), natural.index('窗 其 发送 主 273 705 0.'))
        self.assertLess(natural.index('窗 其 发送 主 273 705 0.'), natural.index('2028 0 0) 其 数 == 0'))
        self.assertLess(natural.index('2028 0 0) 其 数 == 0'), natural.index('PeekMessageW'))
        self.assertIn('_InvalidateRect 其 调用 [柄,空,0]', natural)
        self.assertIn('PeekMessageW', natural)
        self.assertIn('DispatchMessageW', natural)
        self.assertIn("_选测['paints'] > 0", natural)
        self.assertNotIn('4003', natural)
        self.assertNotIn('UpdateWindow', natural)
        self.assertIn('试 语 其 _发设 旧 柄 2032 0 0.', fixture)
        self.assertIn('stale Markdown invalidation cannot reset a replacement document styled prefix', fixture)
        callback = fixture.split('算 选择子过程 柄 消息 宽 长 号 引:', 1)[1].split('次数 取 [0].', 1)[0]
        self.assertIn("若 码 == 2031 或 码 == 2032 或 码 == 4005 则 _选测 其 增 'writes' (_选测['writes']+1). 然", callback)
        self.assertIn("若 码 == 2032 则 _选测 其 增 'styleStarts' (_选测['styleStarts']+1). 然", callback)
        self.assertEqual(callback.count("_选测 其 增 'styleStarts'"), 1)
        self.assertIn("_选测 其 增 'styleStarts' 0. _选测 其 增 'action' 'replace'.", fixture)
        replacement_check = next(line for line in fixture.splitlines()
            if 'stale Markdown invalidation cannot reset a replacement document styled prefix' in line)
        self.assertIn("拒[0] 且 _选测['styleStarts'] == 0", replacement_check)
        self.assertNotIn("_选测['writes']", replacement_check)
        self.assertEqual(fixture.count('窗 其 发送 柄 4003 0 (-1).'), 1)
        self.assertLess(fixture.index('    验自然配色 主 柄 页.'), fixture.index('窗 其 发送 柄 4003 0 (-1).'))

    def test_markdown_replacement_counter_contract_rejects_contamination_and_missing_detection(self):
        # Source-contract controls, not native callback execution evidence.
        path = ci.ROOT / 'tests/app_markdown_native.ru'
        source = path.read_text(encoding='utf-8')
        original_read_text = Path.read_text
        mutations = (
            ("若 码 == 2032 则 _选测 其 增 'styleStarts'", "若 码 == 2031 或 码 == 2032 则 _选测 其 增 'styleStarts'"),
            ("若 码 == 2032 则 _选测 其 增 'styleStarts'", "若 码 == 2031 则 _选测 其 增 'styleStarts'"),
            ("拒[0] 且 _选测['styleStarts'] == 0", "拒[0] 且 _选测['writes'] == 0"),
            ("_选测 其 增 'styleStarts' 0. _选测 其 增 'action' 'replace'.", "_选测 其 增 'action' 'replace'."),
        )
        for before, after in mutations:
            with self.subTest(mutation=after):
                self.assertEqual(source.count(before), 1)
                mutated = source.replace(before, after)
                def read_text(actual, *args, **kwargs):
                    return mutated if actual == path else original_read_text(actual, *args, **kwargs)
                with patch.object(Path, 'read_text', read_text), self.assertRaises(AssertionError):
                    self.test_markdown_selection_invalidates_native_prefix_and_requires_natural_paint()

    def test_markdown_publisher_keeps_reviewed_full_guards_and_prepared_expansion(self):
        # Reviewed source contract only. Actual callback/contraction behavior is
        # separately required from markdown_native and the detached GUI cases.
        source = (ci.ROOT / 'src/markdown_syntax.ru').read_text(encoding='utf-8')
        expected = {'_本态': '8a5ac21dfaed5a7acd9633c5ee30aed02517b6da4e61edd6724bb9da154653fe', '_须本态': 'ad619e1b49326aeb41de2f838a49662358aae6827f3f9603b16945ad224dd37e', '_护': 'd09426159fc731acf23725021e04cb93ad33dbe58526e9741f5806adf93d5445', '_讯': '5b1cac1da67dd9bf65ae91029f5622121301b70a03056a52d72e96ccd41ec9e2', '_全显': 'a2facd577a3085e305284e6e205a9c0d014773f06ef00070f51da71e8289cbf7', '_发布': 'f31481eadda2b032e94434f1fcb1739c41e2d81e9e07a1391f95d3e4d3a5c053', '_须直属': '8105e93a67e66078a2ccf57a377687c3d134626b74b11e627985cd7255f74bab', '登记直属': 'd528efc0163c27444df666080dd6522a7de514b626223bf0ce6c6fbf2e9acccd', '撤销直属': '11a975a7a865fc61009d3a6b5cdf0c2455b4e4355d47d9a1773567acee14ba3b', '_直护': '1196e2af8d48e4a4f37b07baf4059b8be846956e8cd9e55556b0d0724db28c7d', '_直发布': 'aca4265d0f732a9f63c5cfc4815d3d4b05fc7e6d79219a05bf770c704565d701', '_批移位': '92922d737d210319ee19b50aaf68d26840a1ed15c5bbb56f6aa1ccc69a0bfeb1', '_写批计划': '68d92c84edc831a296a616569d92d3911fce0f8552d0cc0fafe6271f2a0afef8', '_验批果': '699c0a3c5ff2192219f5c22f6880be40d36fcf7fd4d7ce941a2c2e23e100d063', '_批发布': '2a175bb7efff6a5af78b2e405e3b550ae70f92012a2bac5685e7ce9f57836e16', '_统计': 'f31451b38baa49c039a772bc0d5aaa04e0d2d32d57c68ac23bca3a7f16b91f94', '_统计时刻': '55ec9489e7c0421b0617e70b5953c732d3bfbdb3d0bc882153e3d0607e51bbf5', '_统计耗时': '1e51b386ebba4ebb1613196a14c9bdd64cacbade50eb8ab029ef596c3ddcd4aa', '_丢弃': '9a0ff8228817367569a13c16929e1917f42bbd5967c766fa7ffdbe3c33d52845', '状态': 'a1789ccfe386ad090afa5a6097bb58ee9928346122f2d964c5d0705deb9e3eab'}
        for name, digest in expected.items():
            functions = re.findall(r'^算 ' + re.escape(name) + r'(?=[ \n])[^\n]*\n(.*?)^法$',
                                   source, re.MULTILINE | re.DOTALL)
            self.assertEqual(len(functions), 1, name)
            code = '\n'.join(line.strip() for line in functions[0].splitlines()
                             if line.strip() and not line.lstrip().startswith('#'))
            self.assertEqual(hashlib.sha256(code.encode('utf-8')).hexdigest(), digest, name)
        binding_blocks = {'_批库态 取': ('_批统计们 取', '01bd6f4bd7eedd46d287845b9dc2a7731e85e5f8a1ff7d089ddce2a6940d75ab'), '_批路径 取': ('_范围型 取', '70872c2451f22776d2d6d58756ceffa041ece2eaadfbc81709762b7a78637f03')}
        for begin, (end, digest) in binding_blocks.items():
            block = source.split(begin, 1)[1].split(end, 1)[0]
            code = '\n'.join(line.strip() for line in block.splitlines()
                if line.strip() and not line.lstrip().startswith('#'))
            self.assertEqual(hashlib.sha256(code.encode('utf-8')).hexdigest(), digest, begin)
        for name in ('折叠', '全折'):
            function = re.findall(r'^算 ' + name + r'[^\n]*\n(.*?)^法$', source,
                                  re.MULTILINE | re.DOTALL)
            self.assertEqual(len(function), 1)
            self.assertIn("或 态['pending']", function[0].splitlines()[1])
        fixture = (ci.ROOT / 'tests/markdown_native.ru').read_text(encoding='utf-8')
        self.assertIn('窗 其 发送 柄 2230 行 0', fixture)
        self.assertIn('后查们 取 [2357,2183,2383]', fixture)
        self.assertIn("新态 其 增 'ranges' ([[0,64,0,假]])", fixture)
        self.assertIn("甲计 其 增 'invalidateAt' (写前+64)", fixture)
        self.assertIn("甲计 其 增 'invalidateAt' (写前+65)", fixture)

    def test_markdown_publisher_source_guard_contract_rejects_unsafe_mutations(self):
        path = ci.ROOT / 'src/markdown_syntax.ru'
        source = path.read_text(encoding='utf-8')
        read_original = Path.read_text
        mutations = (
            ('    若 柄 == 空 则 得 假. 然\n    撤销直属 柄.', '    撤销直属 柄.'),
            ("        _须直属 柄 态 权.\n        若 非 (借 其 为空) 且 _直接策略['enabled']", "        若 非 (借 其 为空) 且 _直接策略['enabled']"),
            ("            _护 柄 态.\n            _须直属 柄 态 权.\n            果 取 结果存", "            _须直属 柄 态 权.\n            果 取 结果存"),
            ("若 状码 != 0 且 状码 != 1 则 卒", "若 假 则 卒"),
            ("字节数 取 _写批计划 计划 态 范围们 位 偏.", "字节数 取 32."),
            ("_批版本 == 65536", "_批版本 == 1"),
            ("['status',窗 其 U],['attempted',窗 其 U]", "['status',窗 其 U],['attempted',窗 其 IP]"),
            ("    _护 柄 态.\n    范围们 取 态['ranges'].", "    范围们 取 态['ranges']."),
            ('            窗 其 发送 柄 2222 行 层.\n            _护 柄 态.',
             '            窗 其 发送 柄 2222 行 层.'),
            ('            数量 取 数量+1.\n            偏 取 偏+1.',
             '            窗 其 发送 柄 2383 0 0.\n            数量 取 数量+1.\n            偏 取 偏+1.'),
            ("态['phase'] != 'scan' 或 非 态['pending']", "态['phase'] != 'scan'"),
            ('    _讯 柄 态 2662 1 0.', '    _讯 柄 态 2226 0 0.'),
            ('    _讯 柄 态 2663 0 0.', '    _讯 柄 态 2663 5 0.'),
            ("若 文档 != 态['document'] 则 卒 'Stale Markdown document.'.", "若 假 则 卒 'Stale Markdown document.'."),
            ("若 长 != 态['length'] 则 卒 'Markdown text changed without invalidation.'.", "若 假 则 卒 'Markdown text changed without invalidation.'."),
            ('借 取 窗 其 发送 柄 2185 0 0.\n        _须直属 柄 态 权.\n        若 非 (借 其 为空) 则',
             '借 取 窗 其 发送 柄 2185 0 0.\n        若 非 (借 其 为空) 则'),
            ('                    _直护 柄 态 直.\n                    # G0,M1',
             '                    # G0,M1'),
            ("    _须本态 柄 态.\n    若 文档 != 态['document'] 则 卒 'Stale Markdown direct document.'.",
             "    若 文档 != 态['document'] 则 卒 'Stale Markdown direct document.'."),
        )
        for before, after in mutations:
            with self.subTest(mutation=after):
                self.assertEqual(source.count(before), 1)
                changed = source.replace(before, after)
                def read_text(actual, *args, **kwargs):
                    return changed if actual == path else read_original(actual, *args, **kwargs)
                with patch.object(Path, 'read_text', read_text), self.assertRaises(AssertionError):
                    self.test_markdown_publisher_keeps_reviewed_full_guards_and_prepared_expansion()

    def test_markdown_gui_corpora_are_fixed_separate_shapes_and_sixteen_style_bytes(self):
        sizes = {'many-lines': 100000, 'singleline': 1000000, 'unclosed-fence': 1000000}
        for kind, size in sizes.items():
            data, probes, folds = ci.gui_markdown_fixture(kind)
            self.assertEqual(len(data), size)
            self.assertEqual(sum(probe['length'] for probe in probes), 16)
            self.assertEqual(probes[-1]['offset'] + probes[-1]['length'], len(data))
            self.assertLessEqual(len(folds), 2)
        self.assertEqual(ci.gui_markdown_fixture('many-lines')[0].count(b'\n'), 5000)
        self.assertNotIn(b'\n', ci.gui_markdown_fixture('singleline')[0])
        self.assertEqual(ci.gui_markdown_fixture('unclosed-fence')[0].count(b'~~~'), 1)
        self.assertEqual(ci.gui_markdown_fixture('unclosed-fence')[1][-1]['style'], 21)
        with self.assertRaises(RuntimeError): ci.gui_markdown_fixture('unknown')

    def test_markdown_gui_receipt_rejects_missing_malformed_unbounded_or_inferred_evidence(self):
        ci.validate_gui_markdown(markdown_evidence(), require_windows_clock=True)
        mutations = ['missing-case', 'duplicate-case', 'missing-stage', 'wrong-source', 'wrong-size', 'wrong-probe',
                     'wrong-fold', 'late', 'nonfinite', 'wrong-length', 'wrong-dirty', 'not-collapsed',
                     'not-expanded', 'style', 'fold', 'context', 'status', 'end-only', 'lexer', 'tail', 'phase-length', 'phase-feed',
                     'no-input', 'request-not-pending', 'paint-not-pending', 'not-cleared', 'slow-input',
                     'oversized-snapshot', 'no-final-proof', 'undo-count', 'clock']
        for mutation in mutations:
            record = markdown_evidence()
            case = record['cases'][0]
            stage = case['stages'][1]
            if mutation == 'missing-case': record['cases'].pop()
            elif mutation == 'duplicate-case': record['cases'][1] = case
            elif mutation == 'missing-stage': case['stages'].pop()
            elif mutation == 'wrong-source': case['source_sha256'] = '0' * 64
            elif mutation == 'wrong-size': case['size'] += 1
            elif mutation == 'wrong-probe': case['style_probes'][0]['length'] += 1
            elif mutation == 'wrong-fold': case['fold_probes'][0]['header'] = False
            elif mutation == 'late': stage['wall_ms'] = 30000.001
            elif mutation == 'nonfinite': stage['wall_ms'] = float('nan')
            elif mutation == 'wrong-length': stage['length'] += 1
            elif mutation == 'wrong-dirty': stage['dirty'] = False
            elif mutation == 'not-collapsed': stage['collapsed_before_edit'] = False
            elif mutation == 'not-expanded': stage['last_probe']['children_visible'] = False
            elif mutation in ('style', 'fold', 'context'): stage['last_probe'][{'style': 'styles_match', 'fold': 'folds_match', 'context': 'context_match'}[mutation]] = False
            elif mutation == 'status': stage['last_probe']['status_done'] = False
            elif mutation == 'end-only': stage['last_probe']['styles_match'] = False
            elif mutation == 'lexer': stage['last_probe']['lexer'] = 0
            elif mutation == 'tail': stage['last_probe']['tail_requested'] = False
            elif mutation == 'phase-length':
                stage['last_progress']['diagnostic']['length'] -= 1
                stage['last_progress']['diagnostic']['feed'] -= 1
            elif mutation == 'phase-feed': stage['last_progress']['diagnostic']['feed'] -= 1
            elif mutation == 'no-input': stage['responsiveness'] = {}
            elif mutation == 'request-not-pending': stage['responsiveness']['navigation'][0]['request_pending'] = False
            elif mutation == 'paint-not-pending': stage['responsiveness']['paint']['request_pending'] = False
            elif mutation == 'not-cleared': stage['responsiveness']['paint']['cleared'] = False
            elif mutation == 'slow-input': stage['responsiveness']['navigation'][0]['wall_ms'] = 5001
            elif mutation == 'oversized-snapshot': stage['observer']['snapshots'][0]['messages'] = 33
            elif mutation == 'no-final-proof': stage['observer']['snapshots'][0]['final'] = False
            elif mutation == 'undo-count': case['stages'][-1]['undo_commands'] = 3
            elif mutation == 'clock': record['clock']['implementation'] = 'monotonic()'
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeError):
                ci.validate_gui_markdown(record, require_windows_clock=True)

    def test_markdown_gui_requires_all_checks_and_exact_runtime(self):
        for key in (*ci.GUI_MARKDOWN_CHECKS, 'fixture_binary_sha256'):
            summary = self.acceptance()
            case = next(case for case in summary['tests'] if case['name'] == 'main-gui-markdown')
            case.pop(key)
            with self.subTest(key=key), self.assertRaises(RuntimeError): ci.validate_acceptance(summary)

    def test_markdown_gui_style_sample_schema_rejects_missing_forged_or_unbounded_values(self):
        for mutation in ('missing', 'extra', 'short', 'long', 'tuple', 'bool', 'negative',
                         'overflow', 'wrong-position', 'wrong-expected', 'mismatch-hidden-by-boolean'):
            record = markdown_evidence()
            last = record['cases'][0]['stages'][0]['last_probe']
            samples = last['style_samples']
            if mutation == 'missing': last.pop('style_samples')
            elif mutation == 'extra': samples['text'] = 'must not be collected'
            elif mutation == 'short': samples['actual'].pop()
            elif mutation == 'long': samples['actual'].append(0)
            elif mutation == 'tuple': samples['actual'] = tuple(samples['actual'])
            elif mutation == 'bool': samples['actual'][1] = False
            elif mutation == 'negative': samples['actual'][1] = -1
            elif mutation == 'overflow': samples['actual'][1] = 256
            elif mutation == 'wrong-position': samples['positions'][1] += 1
            elif mutation == 'wrong-expected': samples['expected'][1] = 17
            elif mutation == 'mismatch-hidden-by-boolean': samples['actual'][1] = 17
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeError):
                ci.validate_gui_markdown(record, require_windows_clock=True)

    def test_markdown_real_stage_preserves_actual_styles_when_mismatch_reaches_deadline(self):
        now = [0.0]
        with patch.object(ci.time, 'perf_counter', side_effect=lambda: now[0]), \
             patch.object(ci.time, 'sleep', side_effect=lambda seconds: now.__setitem__(0, now[0] + seconds)):
            self.run_markdown_stage_control(bad_style=True)

    def test_markdown_real_pending_stage_retains_numeric_progress_without_extra_queries(self):
        now = [0.0]
        with patch.object(ci.time, 'perf_counter', side_effect=lambda: now[0]), \
             patch.object(ci.time, 'sleep', side_effect=lambda seconds: now.__setitem__(0, now[0] + seconds)):
            self.run_markdown_stage_control(pending_forever=True)

    def test_markdown_real_stage_rejects_missing_phase_diagnostic_despite_ready_styles(self):
        now = [0.0]
        with patch.object(ci.time, 'perf_counter', side_effect=lambda: now[0]), \
             patch.object(ci.time, 'sleep', side_effect=lambda seconds: now.__setitem__(0, now[0] + seconds)):
            self.run_markdown_stage_control(missing_diagnostic=True)

    def test_markdown_real_stage_rejects_stale_pending_marker_despite_ready_styles(self):
        now = [0.0]
        with patch.object(ci.time, 'perf_counter', side_effect=lambda: now[0]), \
             patch.object(ci.time, 'sleep', side_effect=lambda seconds: now.__setitem__(0, now[0] + seconds)):
            self.run_markdown_stage_control(stale_pending_diagnostic=True)

    def markdown_marker(self, seq=9):
        record = dict(markdown_evidence()['cases'][0]['stages'][0]['last_progress']['diagnostic'], seq=seq)
        return ' [MDP2 ' + ' '.join(f'{name}={record[name]}' for name in ci.MARKDOWN_DIAGNOSTIC_FIELDS) + ']'

    def test_markdown_status_legacy_length_then_text_reproduces_truncated_marker(self):
        before, after = self.markdown_marker(9), self.markdown_marker(10)
        api = SyntheticWindowText(before, after)
        truncated = api.text(3)
        self.assertEqual(truncated, after[:-1])
        self.assertEqual([call[1] for call in api.calls], [0x000E, 0x000D])
        with self.assertRaisesRegex(RuntimeError, '^Markdown numeric phase marker is malformed$'):
            ci.parse_markdown_diagnostic(truncated)
        api = SyntheticWindowText(before, after)
        self.assertEqual(ci.parse_markdown_diagnostic(api.markdown_status(3))['seq'], 10)
        self.assertEqual(api.calls, [(3, 0x000D, 4098)])

    def test_markdown_status_single_read_accepts_growth_shrinkage_and_stable_markers(self):
        short, long = self.markdown_marker(9), self.markdown_marker(10)
        for before, after in ((short, long), (long, short), (long, long), ('', long)):
            with self.subTest(before=len(before), after=len(after)):
                api = SyntheticWindowText(before, after)
                self.assertEqual(api.markdown_status(3), after)
                ci.parse_markdown_diagnostic(after)
                self.assertEqual(api.calls, [(3, 0x000D, 4098)])

    def test_markdown_status_fixed_cap_preserves_utf16_boundary_and_rejects_overflow(self):
        for text in ('', 'x' * 4095, 'x' * 4096, '甲😀' + 'x' * 4093):
            with self.subTest(code_units=len(text.encode('utf-16-le')) // 2):
                api = SyntheticWindowText('', text)
                self.assertEqual(api.markdown_status(3).encode('utf-16-le', 'surrogatepass'), text.encode('utf-16-le'))
                self.assertEqual(api.calls, [(3, 0x000D, 4098)])
        for text in ('x' * 4097, 'x' * 8192, '甲😀' + 'x' * 4094):
            api = SyntheticWindowText('', text)
            with self.subTest(code_units=len(text.encode('utf-16-le')) // 2), self.assertRaisesRegex(RuntimeError, 'bounded inspection limit'):
                api.markdown_status(3)
            self.assertEqual(api.calls, [(3, 0x000D, 4098)])

    def test_markdown_status_copy_mismatch_and_timeout_fail_without_retry(self):
        for count in (-1, 0, 2, 4097):
            api = SyntheticWindowText('', 'x', reported_count=count)
            with self.subTest(count=count), self.assertRaises(RuntimeError):
                api.markdown_status(3)
            self.assertEqual(api.calls, [(3, 0x000D, 4098)])
        api = SyntheticWindowText('', 'x\0y')
        with self.assertRaisesRegex(RuntimeError, 'copy count is inconsistent'):
            api.markdown_status(3)
        self.assertEqual(api.calls, [(3, 0x000D, 4098)])
        api = SyntheticWindowText('', 'x')
        with patch.object(api, 'scalar', side_effect=RuntimeError('synthetic timeout')) as scalar:
            with self.assertRaisesRegex(RuntimeError, '^synthetic timeout$'):
                api.markdown_status(3)
        scalar.assert_called_once()

    def test_markdown_status_single_read_keeps_strict_parser_and_private_failure_shape(self):
        marker = self.markdown_marker()
        for malformed in (marker[:-1], marker + marker, marker.replace('seq=9', 'seq=9.0'),
                          marker.replace('seq=9', 'seq=9e0'), marker + '\r', marker + 'PRIVATE_TEXT_SENTINEL'):
            api = SyntheticWindowText('', 'PRIVATE_PATH_SENTINEL\\甲😀' + malformed)
            status = api.markdown_status(3)
            with self.subTest(marker=malformed), self.assertRaises(RuntimeError):
                ci.parse_markdown_diagnostic(status)
            failure = ci.markdown_diagnostic_failure(status)
            self.assertTrue(all(type(value) in (int, bool) for value in failure.values()))
            self.assertTrue(all(0 <= value <= 4096 for value in failure.values()))
            self.assertNotIn('PRIVATE', json.dumps(failure))
            self.assertEqual(failure['status_code_units'], len(status.encode('utf-16-le', 'surrogatepass')) // 2)
        failure = ci.markdown_diagnostic_failure(marker[:-1])
        self.assertEqual(failure['marker_occurrences'], 1)
        self.assertEqual(failure['opening_brackets'], 1)
        self.assertEqual(failure['closing_brackets'], 0)
        self.assertFalse(failure['ends_with_closing_bracket'])

    def test_markdown_real_stage_records_only_bounded_failure_structure(self):
        self.run_markdown_stage_control(malformed_diagnostic=True)

    def test_markdown_success_receipt_rejects_failure_diagnostics(self):
        record = markdown_evidence()
        stage = record['cases'][0]['stages'][0]
        stage['diagnostic_failure'] = ci.markdown_diagnostic_failure(self.markdown_marker()[:-1])
        with self.assertRaisesRegex(RuntimeError, 'bounded stage metadata'):
            ci.validate_gui_markdown(record, require_windows_clock=True)

    def test_markdown_numeric_phase_parser_rejects_unbounded_private_or_missing_fields(self):
        marker = ' [MDP2 seq=1 via=0 id=2 gen=3 rev=0 phase=2 pending=1 length=1000000 feed=470180 published=47104 tick=123 work_us=100000 gap_us=200000 bulkCalls=736 bulkLines=47104 fallbackBatches=0 directCalls=0 directLines=0 maxPlanBytes=1056 bulkUs=1234 ownedBufferBytes=1088 metric_valid=1]'
        result = ci.parse_markdown_diagnostic('PRIVATE_PATH_SENTINEL' + marker)
        self.assertEqual(result['phase'], 2)
        self.assertNotIn('PRIVATE', json.dumps(result))
        for bad in [marker + 'tail', marker.replace('seq=1', 'seq=0'), marker.replace('seq=1', 'seq=4097'),
                    marker.replace('via=0', 'via=2'), marker.replace('via=0', 'via=1'),
                    marker.replace('phase=2', 'phase=9'), marker.replace('phase=2', 'phase=4'),
                    marker.replace('feed=470180', 'feed=1000001'), marker.replace('tick=123', 'tick=true'),
                    marker.replace('tick=123', 'tick=01'), marker.replace('id=2', 'id=-1'),
                    marker.replace('rev=0 ', ''), marker.replace('gen=3', 'private=3'),
                    marker + marker, ' [MDP2 error=1]', marker.replace('gap_us=200000', 'gap_us=9999999999999999')]:
            with self.subTest(bad=bad), self.assertRaises(RuntimeError): ci.parse_markdown_diagnostic(bad)
        self.assertIsNone(ci.parse_markdown_diagnostic('ordinary Markdown status'))
        self.assertLessEqual(len(marker), ci.MARKDOWN_DIAGNOSTIC_MAX_CHARS)
        for field in ci.MARKDOWN_DIAGNOSTIC_FIELDS:
            for value in (-1, True, 1.5, '1', 9007199254740992):
                with self.subTest(field=field, value=value), self.assertRaises(RuntimeError):
                    ci.validate_markdown_diagnostic(dict(result, **{field: value}))
            missing = dict(result)
            missing.pop(field)
            with self.subTest(missing=field), self.assertRaises(RuntimeError):
                ci.validate_markdown_diagnostic(missing)
        for change in ({'bulkCalls': 0}, {'bulkLines': 47105}, {'directLines': 1},
                       {'maxPlanBytes': 1057}, {'maxPlanBytes': 1041}, {'ownedBufferBytes': 1089},
                       {'ownedBufferBytes': 0}, {'metric_valid': 0}):
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                ci.validate_markdown_diagnostic(dict(result, **change))
        terminal = dict(result, phase=4, pending=0)
        ci.validate_markdown_diagnostic(terminal)
        ci.validate_markdown_diagnostic(dict(terminal, bulkCalls=1, bulkLines=0,
            fallbackBatches=1, published=1, maxPlanBytes=48))  # Valid zero-write prewrite fallback.
        for change in ({'directCalls': 1}, {'published': 47103}, {'fallbackBatches': 47105}):
            with self.subTest(terminal=change), self.assertRaises(RuntimeError):
                ci.validate_markdown_diagnostic(dict(terminal, **change))
        for bad in (marker.replace('MDP2', 'MDP1'), marker.replace('MDP2', 'MDP3'),
                    marker.replace('bulkUs=1234', 'bulkUs=NaN'),
                    marker.replace('metric_valid=1', 'metric_valid=1 extra=1')):
            with self.subTest(marker=bad), self.assertRaises(RuntimeError):
                ci.parse_markdown_diagnostic(bad)

    def test_markdown_memory_schema_rejects_fabricated_unbounded_or_mislabeled_peak(self):
        baseline = markdown_evidence()['cases'][0]['stages'][0]
        ci.validate_markdown_memory(baseline['memory'], baseline['observer'], baseline['wall_ms'])
        for mutation in ('missing', 'type', 'overflow', 'zero', 'summary', 'cost', 'count',
                         'measurement', 'outside', 'below', 'unknown', 'unsampled'):
            stage = json.loads(json.dumps(baseline))
            memory = stage['memory']
            if mutation == 'missing': memory.pop('sampledWorkingSetPeak')
            elif mutation == 'type': memory['samples'][0]['workingSetBytes'] = True
            elif mutation == 'overflow': memory['samples'][0]['workingSetBytes'] = 9007199254740992
            elif mutation == 'zero': memory['samples'][0]['processPeakWorkingSetBytes'] = 0
            elif mutation == 'summary': memory['sampledWorkingSetPeak'] += 1
            elif mutation == 'cost': memory['query_wall_ms'] = 1.0
            elif mutation == 'count': memory['sample_count'] = 2
            elif mutation == 'measurement': memory['measurement'] = 'instantaneous stage peak'
            elif mutation == 'outside': memory['samples'][0]['start_ms'] = 40.0
            elif mutation == 'below': memory['samples'][0]['processPeakWorkingSetBytes'] = 1
            elif mutation == 'unknown': memory['samples'][0]['private'] = 'text'
            elif mutation == 'unsampled': memory['samples'] = []
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeError):
                ci.validate_markdown_memory(memory, stage['observer'], stage['wall_ms'])

    def test_markdown_fence_specific_fixture_requires_actual_bulk_calls(self):
        record = markdown_evidence()
        diagnostic = record['cases'][2]['stages'][0]['last_progress']['diagnostic']
        diagnostic.update(bulkCalls=0, bulkLines=0, bulkUs=0, maxPlanBytes=0,
                          ownedBufferBytes=0, fallbackBatches=1)
        ci.validate_markdown_diagnostic(diagnostic)  # Product fallback remains valid.
        with self.assertRaisesRegex(RuntimeError, 'did not actually use bulk'):
            ci.validate_gui_markdown(record)

    def test_markdown_memory_query_requires_windows_and_owned_handle(self):
        with patch.object(ci.sys, 'platform', 'linux'), self.assertRaisesRegex(RuntimeError, 'actual Windows'):
            ci.MarkdownProcessMemory(object(), ci.markdown_memory_record(), 0, lambda: 0)
        with patch.object(ci.sys, 'platform', 'win32'), self.assertRaisesRegex(RuntimeError, 'owned launcher handle'):
            ci.MarkdownProcessMemory(object(), ci.markdown_memory_record(), 0, lambda: 0)
        self.assertEqual(ctypes.sizeof(ci.MarkdownMemoryCounters), 72)

    def test_markdown_memory_api_records_real_return_values_and_separate_cost(self):
        def query(handle, pointer, size):
            self.assertEqual((handle, size), (456, 72))
            counters = ctypes.cast(pointer, ctypes.POINTER(ci.MarkdownMemoryCounters)).contents
            self.assertEqual(counters.cb, 72)
            counters.WorkingSetSize, counters.PeakWorkingSetSize = 123456, 234567
            return 1
        native = Mock(side_effect=query)
        kernel = SimpleNamespace(K32GetProcessMemoryInfo=native)
        record = ci.markdown_memory_record()
        clock = iter((0.1, 0.1002))
        with patch.object(ci.sys, 'platform', 'win32'), patch.object(ci.ctypes, 'WinDLL', return_value=kernel, create=True) as load:
            collector = ci.MarkdownProcessMemory(SimpleNamespace(_handle=456), record, 0, lambda: next(clock))
            collector.sample()
        load.assert_called_once_with('kernel32', use_last_error=True)
        self.assertEqual(native.call_count, 1)
        self.assertEqual(record['samples'], [{'start_ms': 100.0, 'query_wall_ms': 0.2,
            'workingSetBytes': 123456, 'processPeakWorkingSetBytes': 234567}])
        self.assertEqual(record['sampledWorkingSetPeak'], 123456)
        self.assertEqual(record['processPeakWorkingSet'], 234567)
        self.assertEqual(record['query_wall_ms'], 0.2)
        self.assertEqual(record['max_query_ms'], 0.2)
        ci.validate_markdown_memory(record, {'snapshot_count': 1,
            'snapshots': [{'start_ms': 100.0, 'wall_ms': 1.0}]}, 101.0)
        self.assertEqual(native.argtypes, [ci.wintypes.HANDLE, ctypes.POINTER(ci.MarkdownMemoryCounters), ci.wintypes.DWORD])

    def test_markdown_memory_success_can_report_trimmed_zero_current_set(self):
        def query(handle, pointer, size):
            counters = ctypes.cast(pointer, ctypes.POINTER(ci.MarkdownMemoryCounters)).contents
            counters.WorkingSetSize, counters.PeakWorkingSetSize = 0, 234567
            return 1
        kernel = SimpleNamespace(K32GetProcessMemoryInfo=Mock(side_effect=query))
        record = ci.markdown_memory_record()
        clock = iter((0.1, 0.1002))
        with patch.object(ci.sys, 'platform', 'win32'), patch.object(ci.ctypes, 'WinDLL', return_value=kernel, create=True):
            collector = ci.MarkdownProcessMemory(SimpleNamespace(_handle=456), record, 0, lambda: next(clock))
            collector.sample()
        self.assertEqual(record['sampledWorkingSetPeak'], 0)
        self.assertEqual(record['processPeakWorkingSet'], 234567)
        ci.validate_markdown_memory(record, {'snapshot_count': 1,
            'snapshots': [{'start_ms': 100.0, 'wall_ms': 1.0}]}, 101.0)

    def test_markdown_memory_api_failure_cannot_invent_zero_usage(self):
        for returned, working, peak in ((0, 0, 0), (1, 0, 0), (1, 2, 1)):
            def query(handle, pointer, size):
                counters = ctypes.cast(pointer, ctypes.POINTER(ci.MarkdownMemoryCounters)).contents
                counters.WorkingSetSize, counters.PeakWorkingSetSize = working, peak
                return returned
            kernel = SimpleNamespace(K32GetProcessMemoryInfo=Mock(side_effect=query))
            record = ci.markdown_memory_record()
            clock = iter((0.1, 0.1002))
            with patch.object(ci.sys, 'platform', 'win32'), patch.object(ci.ctypes, 'WinDLL', return_value=kernel, create=True):
                collector = ci.MarkdownProcessMemory(SimpleNamespace(_handle=456), record, 0, lambda: next(clock))
                with self.subTest(returned=returned, working=working, peak=peak), self.assertRaises(RuntimeError):
                    collector.sample()
            self.assertEqual(record['sample_count'], 0)
            self.assertEqual(record['samples'], [])
            self.assertEqual(record['query_wall_ms'], 0.2)

    def test_markdown_real_stage_uses_bounded_observer_and_pending_requests(self):
        self.run_markdown_stage_control()

    def test_markdown_real_stage_rejects_production_failure_warning_despite_ready_native_styles(self):
        self.run_markdown_stage_control(warning=True)

    def run_markdown_stage_control(self, warning=False, bad_style=False, pending_forever=False, missing_diagnostic=False, stale_pending_diagnostic=False, malformed_diagnostic=False):
        kind, operation = 'many-lines', 'insert'
        original = ci.gui_markdown_fixture(kind)[0]
        expected, probes, folds = ci.markdown_expected(kind, operation)
        path = self.root / 'many-lines.md'
        path.write_bytes(original)
        class Process:
            pid, _handle = 123, 456
            def poll(self): return None
        def memory_factory(process, record, started, clock):
            collector = object.__new__(ci.MarkdownProcessMemory)
            collector.process, collector.record = process, record
            collector.started, collector.clock = started, clock
            def query(handle, pointer, size):
                self.assertEqual((handle, size), (456, ctypes.sizeof(ci.MarkdownMemoryCounters)))
                counters = ctypes.cast(pointer, ctypes.POINTER(ci.MarkdownMemoryCounters)).contents
                counters.WorkingSetSize, counters.PeakWorkingSetSize = 1048576, 2097152
                return 1
            collector.query = query
            return collector
        original_memory = ci.MarkdownProcessMemory
        def mocked_memory(*args):
            # Constructor is patched, so retain the real class explicitly.
            with patch.object(ci, 'MarkdownProcessMemory', original_memory):
                return memory_factory(*args)
        memory_patch = patch.object(ci, 'MarkdownProcessMemory', side_effect=mocked_memory)
        memory_patch.start()
        self.addCleanup(memory_patch.stop)
        class Api(ci.Windows):
            def __init__(self):
                self.caret, self.visible, self.status_reads = 9, False, 0
                self.messages, self.navigation = [], []
            def editor(self, hwnd): return 2
            def control(self, hwnd, identifier): return 3
            def no_dialog(self, pid): return []
            def responsive(self, hwnd): pass
            def verify_owned_handles(self, pid, *handles): pass
            def text(self, hwnd):
                self.scalar(hwnd, 0x000E)
                self.scalar(hwnd, 0x000D)
                return self.window_text(hwnd)
            def window_text(self, hwnd):
                if hwnd == 1: return '* ' + path.name + ' · ru_notepad'
                self.status_reads += 1
                marker = (' [MDP2 seq=1 via=0 id=2 gen=3 rev=0 phase=1 pending=1 length=' + str(len(expected)) +
                          ' feed=470180 published=47104 tick=123 work_us=100000 gap_us=200000 bulkCalls=736 bulkLines=47104 fallbackBatches=0 directCalls=0 directLines=0 maxPlanBytes=1056 bulkUs=1234 ownedBufferBytes=1088 metric_valid=1]')
                # Use valid progress bounded to this smaller synthetic corpus.
                marker = marker.replace('feed=470180', 'feed=47018')
                if missing_diagnostic: marker = ''
                if malformed_diagnostic: marker = marker[:-1]
                if pending_forever or self.status_reads <= 2: return 'Folding Markdown...' + marker
                if warning: return 'Ln 1 UTF-8 Markdown folding was disabled: synthetic publication failure'
                if not stale_pending_diagnostic:
                    marker = marker.replace('seq=1 via=0', 'seq=2 via=1').replace('phase=1 pending=1', 'phase=4 pending=0')
                    marker = marker.replace('feed=47018 ', 'feed=' + str(len(expected)) + ' ')
                return 'Ln 1 UTF-8 Markdown' + marker
            def scalar(self, hwnd, message, wparam=0, lparam=0):
                self.messages.append((hwnd, message, wparam, lparam))
                if message == 0x000D and wparam:
                    text = self.window_text(hwnd)
                    buffer = ctypes.cast(lparam, ctypes.POINTER(ctypes.c_wchar))
                    count = min(len(text), wparam - 1)
                    for index, char in enumerate(text[:count]): buffer[index] = char
                    buffer[count] = '\0'
                    return count
                if message == 2006: return len(expected)
                if message == 2159: return 1
                if message == 2008: return self.caret
                if message == 2025: self.caret = wparam
                if message == 2228: return int(self.visible)
                if message == 2223: return 0x2400 if wparam == 0 else 0x400
                if message == 2010:
                    if bad_style and wparam == 2: return 17
                    return next((probe['style'] for probe in probes if probe['offset'] <= wparam < probe['offset'] + probe['length']), 0)
                if message == 2007: return expected[wparam]
                if message == 2028: return len(expected)
                if message == 4002: return 98
                if message == 0x0102: self.visible = True
                return 0
            def post_navigation(self, hwnd, key):
                self.navigation.append(key)
                self.caret += 1 if key == 'RIGHT' else -1
            def invalidate_for_paint(self, hwnd): return False
            def paint_pending(self, hwnd): return False
        api, stage = Api(), {}
        if malformed_diagnostic:
            with self.assertRaisesRegex(RuntimeError, '^Markdown numeric phase marker is malformed$'):
                ci.run_gui_markdown_stage(api, Process(), 1, path, kind, operation, stage,
                                         lambda: api.scalar(2, 0x0102, ord('x'), 1))
            failure = stage['diagnostic_failure']
            self.assertTrue(all(type(value) in (int, bool) and 0 <= value <= 4096 for value in failure.values()))
            self.assertEqual(failure['marker_occurrences'], 1)
            self.assertEqual(failure['closing_brackets'], 0)
            self.assertFalse(failure['ends_with_closing_bracket'])
            self.assertIsNone(stage['last_progress']['diagnostic'])
            self.assertFalse(stage['last_probe'])
            self.assertEqual([msg[1:3] for msg in api.messages if msg[0] == 3], [(0x000D, 4098)])
            self.assertFalse(any(item['final'] for item in stage['observer']['snapshots']))
            self.assertEqual(path.read_bytes(), original)
            return
        if pending_forever:
            with self.assertRaisesRegex(RuntimeError, '30-second deadline'):
                ci.run_gui_markdown_stage(api, Process(), 1, path, kind, operation, stage,
                                         lambda: api.scalar(2, 0x0102, ord('x'), 1))
            progress = json.loads(json.dumps(stage))['last_progress']
            ci.validate_markdown_progress(progress)
            self.assertEqual(progress['status'], 'folding')
            self.assertEqual(progress['diagnostic']['feed'], 47018)
            self.assertEqual(progress['diagnostic']['published'], 47104)
            self.assertEqual(progress['length'], len(expected))
            self.assertFalse(stage['last_probe'])
            self.assertFalse(any(item['final'] for item in stage['observer']['snapshots']))
            self.assertFalse(any(msg[1] in (2010, 2007, 2028, 4002) for msg in api.messages))
            self.assertLessEqual(stage['observer']['max_snapshot_messages'], 32)
            with self.assertRaisesRegex(RuntimeError, 'completion lacks'):
                ci.validate_markdown_progress(progress, complete=True, expected_length=len(expected), expected_dirty=True)
            return
        if missing_diagnostic or stale_pending_diagnostic:
            with self.assertRaisesRegex(RuntimeError, '30-second deadline'):
                ci.run_gui_markdown_stage(api, Process(), 1, path, kind, operation, stage,
                                         lambda: api.scalar(2, 0x0102, ord('x'), 1))
            if missing_diagnostic:
                self.assertIsNone(stage['last_progress']['diagnostic'])
            else:
                self.assertEqual(stage['last_progress']['diagnostic']['pending'], 1)
                with self.assertRaisesRegex(RuntimeError, 'completion lacks'):
                    ci.validate_markdown_progress(stage['last_progress'], complete=True,
                        expected_length=len(expected), expected_dirty=True)
            self.assertEqual(stage['last_progress']['status'], 'complete')
            self.assertTrue(all(stage['last_probe'][key] for key in
                ('status_done', 'styles_match', 'folds_match', 'context_match', 'children_visible')))
            self.assertFalse(any(item['final'] for item in stage['observer']['snapshots']))
            self.assertLessEqual(stage['observer']['max_snapshot_messages'], 32)
            self.assertEqual(path.read_bytes(), original)
            return
        if bad_style:
            with self.assertRaisesRegex(RuntimeError, '30-second deadline'):
                ci.run_gui_markdown_stage(api, Process(), 1, path, kind, operation, stage,
                                         lambda: api.scalar(2, 0x0102, ord('x'), 1))
            last = json.loads(json.dumps(stage))['last_probe']
            samples = last['style_samples']
            self.assertFalse(last['styles_match'])
            self.assertEqual(samples['positions'], [0, *range(2, 9), *range(len(expected) - 8, len(expected))])
            self.assertEqual(samples['expected'], [6] + [0] * 15)
            self.assertEqual(samples['actual'], [6, 17] + [0] * 14)
            self.assertTrue(all(last[key] for key in ('status_done', 'folds_match', 'context_match', 'children_visible')))
            self.assertFalse(any(item['final'] for item in stage['observer']['snapshots']))
            self.assertLessEqual(stage['observer']['max_snapshot_messages'], 32)
            self.assertGreaterEqual(stage['wall_ms'], 30000)
            self.assertEqual(sum(msg[1] == 2010 for msg in api.messages) % 16, 0)
            self.assertFalse(any(msg[1] in (2009, 2153, 2182, 4003) for msg in api.messages))
            self.assertEqual(path.read_bytes(), original)
            return
        if warning:
            # Exercise the real snapshot path with matching length, dirty flag,
            # lexer, styles and old headers. Only the production warning blocks
            # completion. Pending input/paint has already been requested.
            with self.assertRaisesRegex(RuntimeError, 'production folding failure'):
                ci.run_gui_markdown_stage(api, Process(), 1, path, kind, operation, stage,
                                         lambda: api.scalar(2, 0x0102, ord('x'), 1))
            self.assertEqual(api.scalar(2, 2028), len(expected))
            self.assertEqual(api.scalar(2, 4002), 98)
            self.assertTrue(api.scalar(2, 2223, 0) & 0x2000)
            self.assertTrue(all(api.scalar(2, 2010, position) == probe['style']
                for probe in probes for position in range(probe['offset'], probe['offset'] + probe['length'])))
            self.assertTrue(stage['responsiveness']['navigation'][0]['request_pending'])
            self.assertFalse(any(item['final'] for item in stage['observer']['snapshots']))
            self.assertLessEqual(stage['observer']['max_snapshot_messages'], 32)
            self.assertFalse(stage['last_probe'])
            return
        ci.run_gui_markdown_stage(api, Process(), 1, path, kind, operation, stage,
                                 lambda: api.scalar(2, 0x0102, ord('x'), 1))
        self.assertNotIn('diagnostic_failure', stage)
        self.assertTrue(any(msg[0] == 3 and msg[1:3] == (0x000D, 4098) for msg in api.messages))
        ci.validate_gui_ru_observer(stage['observer'], stage['wall_ms'], stage['probes'])
        ci.validate_gui_markdown_responsiveness(stage['responsiveness'], stage['wall_ms'])
        ci.validate_markdown_memory(stage['memory'], stage['observer'], stage['wall_ms'])
        self.assertEqual(stage['memory']['sample_count'], stage['observer']['snapshot_count'])
        self.assertEqual(stage['memory']['sampledWorkingSetPeak'], 1048576)
        self.assertEqual(stage['memory']['processPeakWorkingSet'], 2097152)
        self.assertTrue(stage['collapsed_before_edit'])
        self.assertTrue(stage['last_probe']['children_visible'])
        self.assertEqual(api.navigation, ['RIGHT', 'LEFT'])
        self.assertLessEqual(stage['observer']['max_snapshot_messages'], 32)
        self.assertEqual(sum(msg[1] == 2010 for msg in api.messages), 16)
        self.assertEqual(stage['last_probe']['style_samples']['actual'],
                         stage['last_probe']['style_samples']['expected'])
        self.assertEqual(sum(msg[1] == 2007 for msg in api.messages), 4)
        self.assertFalse(any(msg[1] in (2009, 2153, 2182, 4003) for msg in api.messages))
        self.assertEqual(path.read_bytes(), original)

    def test_markdown_pure_backend_gate_and_fixed_historical_workflow_are_mandatory(self):
        import test_markdown_portable as portable_policy
        portable_policy.controls()
        self.assertEqual(portable_policy.CASES, {'markdown_policy': 221, 'markdown_selection_policy': 31})
        workflow = (ci.ROOT / '.github/workflows/windows.yml').read_text()
        self.assertIn('python -I tools/test_markdown_portable.py --ru-root .ci/ru-language', workflow)
        self.assertIn('needs: helper-policy', workflow)
        self.assertIn('build/markdown-policy-evidence/report.json', workflow)
        script = (ci.ROOT / 'tools/windows_ci.ps1').read_text()
        self.assertIn("'tools/test_markdown_portable.py','--ru-root',$RuRoot", script)
        historical = (ci.ROOT / '.github/workflows/policy-prefix-benchmark.yml').read_text()
        fixed = 'f91d9e8d008c48b00f98b5a19000639c18a61518'
        self.assertIn('  workflow_dispatch:', historical)
        self.assertNotIn('  push:', historical)
        self.assertNotIn('  pull_request:', historical)
        self.assertIn('ref: ' + fixed, historical)
        self.assertIn('name: historical-policy8-' + fixed + '-run-${{ github.run_id }}', historical)
        self.assertNotIn('ref: ${{ github.sha }}', historical)
        self.assertNotIn("if: github.ref ==", historical)
        self.assertNotIn('prepare_source_archives', historical)
        self.assertNotIn('validate_source_archive_receipt', historical)
        self.assertIn('Invoke-WebRequest', historical)
        self.assertIn('import run_direct_style_benchmark as runner', historical)


    def test_compiler_diagnostic_controls_are_mandatory_and_private_logs_are_not_uploaded(self):
        workflow = (ci.ROOT / '.github/workflows/windows.yml').read_text(encoding='utf-8')
        controls = 'python -I tools/test_ru_cli_diagnostics.py --ru-root .ci/ru-language -v'
        self.assertEqual(workflow.count(controls), 1)
        self.assertLess(workflow.index(controls), workflow.index(
            'python -I tools/test_markdown_portable.py --ru-root .ci/ru-language'))
        script = (ci.ROOT / 'tools/windows_ci.ps1').read_text(encoding='utf-8')
        controls = "Invoke-Checked $Python @('-I','tools/test_ru_cli_diagnostics.py','--ru-root',$RuRoot,'-v')"
        self.assertEqual(script.count(controls), 1)
        self.assertLess(script.index(controls), script.index(
            "Invoke-Checked $Python @('tools/test_markdown_portable.py'"))
        for private in ('build/ru-cli-diagnostics-evidence', 'build/markdown-policy-private'):
            self.assertNotIn(private, workflow)
        self.assertFalse(any('compile' in name or 'ru-cli-diagnostics' in name
                            for name in ci.HELPER_POLICY_EVIDENCE_FILES))

    def test_markdown_portable_timeout_cleans_owned_process_tree_before_returning(self):
        import test_markdown_portable as gate
        events = []
        class Process:
            pid = 98765
            returncode = None
            def poll(self): return self.returncode
            def wait(self, timeout):
                if timeout == 5:
                    events.append('wait-cleanup')
                    self.returncode = -9
                    return self.returncode
                raise subprocess.TimeoutExpired('synthetic', timeout)
        process = Process()
        # This exercises the POSIX branch on every host, including Windows where
        # neither os.killpg nor signal.SIGKILL exists. Keep both mocks local to
        # this driver rather than changing the process-wide platform modules.
        posix_os = SimpleNamespace(name='posix',
            killpg=lambda pid, sig: events.append((pid, sig)))
        posix_signal = SimpleNamespace(SIGKILL=9)
        with patch.object(gate.subprocess, 'Popen', return_value=process) as launch, \
             patch.object(gate.time, 'monotonic', side_effect=[0.0, 2.0]), \
             patch.object(gate, 'os', posix_os), \
             patch.object(gate, 'signal', posix_signal):
            with self.assertRaisesRegex(RuntimeError, 'deadline'):
                gate.checked_run(['synthetic'], self.root, 'deadline', 1)
        self.assertTrue(launch.call_args.kwargs['start_new_session'])
        self.assertEqual(events, [(98765, 9), 'wait-cleanup'])

    def test_markdown_portable_posix_mock_is_independent_of_host_only_attributes(self):
        import test_markdown_portable as gate
        original_os, original_signal = gate.os, gate.signal
        windows_os, windows_signal = SimpleNamespace(name='nt'), SimpleNamespace()
        with patch.object(gate, 'os', windows_os), patch.object(gate, 'signal', windows_signal):
            self.assertFalse(hasattr(gate.os, 'killpg'))
            self.assertFalse(hasattr(gate.signal, 'SIGKILL'))
            self.test_markdown_portable_timeout_cleans_owned_process_tree_before_returning()
            self.assertIs(gate.os, windows_os)
            self.assertIs(gate.signal, windows_signal)
            self.assertFalse(hasattr(gate.os, 'killpg'))
            self.assertFalse(hasattr(gate.signal, 'SIGKILL'))
            # The POSIX mock must not leak into either Windows cleanup outcome.
            self.test_markdown_portable_windows_cleanup_targets_tree_and_fails_closed()
        self.assertIs(gate.os, original_os)
        self.assertIs(gate.signal, original_signal)

    def test_markdown_portable_windows_cleanup_targets_tree_and_fails_closed(self):
        import test_markdown_portable as gate
        process = SimpleNamespace(pid=98765, wait=unittest.mock.Mock(return_value=-9))
        with patch.object(gate.os, 'name', 'nt'), patch.object(gate.subprocess, 'run',
                return_value=SimpleNamespace(returncode=0)) as kill:
            gate.stop_process_tree(process)
        self.assertEqual(kill.call_args.args[0], ['taskkill', '/PID', '98765', '/T', '/F'])
        process.wait.assert_called_once_with(timeout=5)
        with patch.object(gate.os, 'name', 'nt'), patch.object(gate.subprocess, 'run',
                return_value=SimpleNamespace(returncode=1)):
            with self.assertRaisesRegex(RuntimeError, 'cleanup failed'): gate.stop_process_tree(process)



if __name__ == '__main__':
    unittest.main(verbosity=2)
