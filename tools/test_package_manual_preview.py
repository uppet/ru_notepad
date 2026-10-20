#!/usr/bin/env python3
"""Portable fake-PE controls only. These never claim Windows execution."""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parent))
import package_manual_preview as preview
import package as portable
import test_package as fixtures
import windows_ci as ci
import test_markdown_fold_helper as helper


class ManualPreviewTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.PackageTests('runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.ci = self.root / preview.RUN_ROOT
        self.ci.mkdir(parents=True)
        self.binary = self.ci / 'bin'
        self.fixture.binary.rename(self.binary)
        shutil.rmtree(self.fixture.evidence)
        self.evidence = self.ci / 'evidence'
        self.evidence.mkdir()
        self.summary = copy.deepcopy(self.fixture.summary)
        self.summary.update(schema=1, synthetic_data_only=True)
        for relative in helper.SOURCES:
            path = self.root / relative
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('synthetic control source\n', encoding='utf-8')
        def identity(root):
            files = {p.relative_to(root).as_posix(): portable.sha(p) for p in root.rglob('*')
                     if p.is_file() and not p.relative_to(root).as_posix().startswith('build/')}
            return {'app_commit': '1' * 40, 'app_tree': '2' * 40, 'tracked_source_sha256': files}
        patch.object(preview, 'git_identity', side_effect=identity).start()
        controls = {'schema': 1, 'control': 'markdown_bounded_fold_v1', 'passed': True,
            'real_windows_runtime': True, 'sanitize': False,
            'sources': {name: {'bytes': (self.root / name).stat().st_size,
                'sha256': portable.sha(self.root / name)} for name in helper.SOURCES},
            'runtime_dlls': {name: {'bytes': (self.binary / name).stat().st_size,
                'sha256': portable.sha(self.binary / name)} for name in ('Scintilla.dll', 'RuSyntax.dll')},
            'stages': []}
        for key in ('windows_compiler', 'host_compiler', 'host_test_binary', 'windows_test_pe'):
            controls[key] = {'bytes': 128, 'sha256': '9' * 64}
        for name in preview.HELPER_STAGES:
            stage = {'stage': name, 'passed': True}
            if name in preview.HELPER_COMMANDS:
                empty = hashlib.sha256(b'').hexdigest()
                stage['owned_process'] = {'returncode': 0, 'cleanup_confirmed': True, 'wall_ms': 1.0,
                    'stdout_bytes': 0, 'stderr_bytes': 0, 'stdout_sha256': empty, 'stderr_sha256': empty}
                for stream in ('stdout', 'stderr'):
                    stage[stream] = {'bytes': 0, 'sha256': empty, 'file_bytes': 0, 'complete': True}
            elif name in ('strict_parser_controls', 'report_ownership_controls'):
                stage['checks'] = helper.parser_controls() if name == 'strict_parser_controls' else 3
            elif name == 'host_controls':
                stage.update(checks=helper.EXPECTED_HOST_CHECKS, real_windows_runtime=False,
                             qualification_boundaries=helper.EXPECTED_QUALIFICATION_BOUNDARIES)
            elif name == 'windows_controls':
                stage.update(checks=helper.EXPECTED_WINDOWS_CHECKS, real_windows_runtime=True, cross_thread=True)
            controls['stages'].append(stage)
        portable.save_json(self.evidence / 'markdown-bulk-helper-controls.json', controls)
        (self.evidence / 'source-archives.json').write_text('{}\n', encoding='utf-8')
        (self.evidence / 'msys2-packages.log').write_text('synthetic packages\n', encoding='utf-8')

    def logs(self):
        for test in self.summary['tests']:
            name = test['name']
            if name in ci.GUI_NAMES:
                lines = ['[launcher] Starting Ru program.', '[startup] menu installed',
                    '[startup] initial document ready', '[startup] main window shown',
                    '[operation] open started', '[operation] open completed', '[operation] cancelled']
                if test['passed']:
                    lines += ['[launcher] Ru program returned with status 0.']
                (self.evidence / (portable.GUI_EVIDENCE_PREFIXES[name] + '-0.log')).write_text(
                    '\n'.join(lines) + '\n', encoding='utf-8')
                continue
            count = ci.expected_assertions(name)
            marker = dict(ci.NATIVE_CONSOLE_TESTS).get(name, r'^TOTAL PASS: 8\s*$')
            marker = marker.removeprefix('^').removesuffix(r'\s*$')
            if name == 'file_codec_security':
                marker = 'FILE_CODEC_SECURITY_TESTS_PASS'
            stdout = 'PASS: synthetic assertion\n' * count + marker + '\n'
            stderr = ''
            if name == 'syntax_bad_lexer':
                stdout += ci.WRONG_LEXER_PREFLIGHT_MARKER + '\n'
            if name == 'markdown_direct_native':
                stderr = 'RU_GC live=0 freed=100 collections=4\n'
                for record in test['bulk_route_metrics']:
                    stdout += 'FOLD_METRICS1 route=' + record['route'] + ' ' + ' '.join(
                        f'{key}={record[key]}' for key in ci.FOLD_ROUTE_METRIC_FIELDS) + '\n'
            (self.evidence / (name + '.stdout.log')).write_text(stdout, encoding='utf-8')
            (self.evidence / (name + '.stderr.log')).write_text(stderr, encoding='utf-8')
        portable.save_json(self.evidence / (portable.SCANNER_PREFLIGHT_NAME + '.stdout.log'),
                           self.summary['scanner_preflight']['report'])
        (self.evidence / (portable.SCANNER_PREFLIGHT_NAME + '.stderr.log')).write_bytes(b'')
        portable.save_json(self.evidence / 'native-acceptance.json', self.summary)

    def markdown(self):
        return next(t for t in self.summary['tests'] if t['name'] == preview.MD_NAME)

    def timeout(self, case_index=0, stage_index=0):
        self.summary.update(passed=False, native_tests_passed=False, run_error=preview.RUN_ERROR)
        test = self.markdown()
        for name in ci.GUI_MARKDOWN_CHECKS:
            test.pop(name, None)
        test.pop('exit_code')
        test.update(passed=False, cleanup_killed=True, close_posted=False, source_bytes_preserved=True,
            error='Markdown GUI open/edit exceeded its original 30-second deadline')
        record = test['markdown_performance']
        record['cases'] = record['cases'][:case_index + 1]
        case = record['cases'][-1]
        case['stages'] = case['stages'][:stage_index + 1]
        stage = case['stages'][-1]
        stage.update(wall_ms=30000.5, last_probe={})
        stage['observer']['snapshots'][-1]['final'] = False
        stage['last_progress']['status'] = 'folding'
        stage['last_progress']['diagnostic'].update(phase=1, pending=1, feed=100,
            published=0, bulkCalls=0, bulkLines=0, fallbackBatches=0, directCalls=0,
            directLines=0, maxPlanBytes=0, bulkUs=0, ownedBufferBytes=0)
        return stage

    def prepare(self):
        return preview.prepare(self.root, 'fake-objdump')

    def create(self):
        def licenses(destination):
            target = destination / 'MSYS2/gcc/COPYING'
            target.parent.mkdir(parents=True)
            target.write_text('Synthetic GCC RUNTIME LIBRARY EXCEPTION, GNU GENERAL PUBLIC LICENSE, mingw\n', encoding='utf-8')
        return preview.create_preview(self.root, 'fake-objdump', licenses)

    def build(self):
        self.prepare()
        self.logs()
        return self.create()

    def assert_refused(self, action):
        with self.assertRaises((RuntimeError, OSError, KeyError, TypeError, ValueError)):
            action()
        self.assertFalse((self.ci / preview.OUTPUT_NAME).exists())

    def test_full_pass_produces_identical_runtime_and_fixed_fence_without_claiming_manual_acceptance(self):
        result = self.build()
        self.assertEqual(result['formal_acceptance'], 'passed')
        self.assertEqual(result['manual_acceptance'], 'not_run')
        self.assertEqual(result['required_test_groups'], 42)
        self.check_packages(result)

    def test_pending_timeout_preserves_failure_and_original_bytes(self):
        self.timeout()
        original = copy.deepcopy(self.summary)
        result = self.build()
        self.assertEqual(self.summary, original)
        self.assertEqual(result['formal_acceptance'], 'failed')
        self.assertEqual(result['markdown_performance'], 'performance_not_passed')
        self.assertFalse(result['original_acceptance_passed'])
        self.check_packages(result)
        with self.assertRaises(RuntimeError):
            ci.validate_acceptance(self.summary, self.root)

    def check_packages(self, result):
        output = self.ci / preview.OUTPUT_NAME
        records = {}
        for kind in ('runtime', 'tests'):
            artifact = result['packages'][kind]
            path = output / artifact['name']
            with zipfile.ZipFile(path) as archive:
                files = {n.removeprefix(path.stem + '/'): archive.read(n) for n in archive.namelist()}
            preview.verify_archive(path, files)
            self.assertEqual(files['LICENSE'], (self.root / 'LICENSE').read_bytes())
            self.assertEqual(files['licenses/ru-language-MIT.txt'],
                             (self.root / 'packaging/licenses/ru-language-MIT.txt').read_bytes())
            records[kind] = files
            self.assertEqual(files[preview.SAMPLE_NAME], ci.gui_markdown_fixture('unclosed-fence')[0])
            self.assertEqual(len(files[preview.SAMPLE_NAME]), 1000000)
            self.assertEqual(hashlib.sha256(files[preview.SAMPLE_NAME]).hexdigest(), preview.SAMPLE_SHA256)
            self.assertFalse(any(n.endswith('.zip') or n.startswith('vendor/') for n in files))
            self.assertIn('人工体验预览', files['开始前请读.txt'].decode('utf-8'))
            self.assertNotIn(b'PRIVATE_WORKSPACE', files['BUILD.json'])
        self.assertEqual({n for n in records['runtime'] if n.endswith(('.exe', '.dll'))}, set(portable.RUNTIME_NAMES))
        self.assertFalse(any(n.endswith(('.log', '.cmd', '.ps1')) for n in records['runtime']))
        self.assertEqual(records['tests']['native-test-evidence/native-acceptance.json'],
                         (self.evidence / 'native-acceptance.json').read_bytes())
        for name in portable.RUNTIME_NAMES:
            self.assertEqual(records['runtime'][name], records['tests'][name])

    def test_all_completed_prefix_positions_are_checked(self):
        for case_index in range(3):
            for stage_index in range(4):
                original = copy.deepcopy(self.summary)
                self.timeout(case_index, stage_index)
                preview.validate_summary(self.summary, self.root, self.summary['tested_binary_sha256'])
                if case_index or stage_index:
                    prior = self.markdown()['markdown_performance']['cases'][0]['stages'][0]
                    prior['last_probe']['styles_match'] = False
                    with self.assertRaises(RuntimeError):
                        preview.validate_summary(self.summary, self.root, self.summary['tested_binary_sha256'])
                self.summary = original

    def test_first_undo_pending_allows_only_the_exact_intermediate_state(self):
        stage = self.timeout(2, 3)
        stage['undo_commands'] = 1
        progress = stage['last_progress']
        progress.update(length=stage['length'] + 1, dirty=True, tail_requested=False)
        progress['diagnostic']['length'] = progress['length']
        preview.validate_summary(self.summary, self.root, self.summary['tested_binary_sha256'])
        original = copy.deepcopy(self.summary)
        for change in ({'length': stage['length'] + 2}, {'dirty': False}, {'tail_requested': True}):
            summary = copy.deepcopy(original)
            test = next(t for t in summary['tests'] if t['name'] == preview.MD_NAME)
            test['markdown_performance']['cases'][-1]['stages'][-1]['last_progress'].update(change)
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                preview.validate_summary(summary, self.root, summary['tested_binary_sha256'])
        stage['undo_commands'] = 2
        with self.assertRaises(RuntimeError):
            preview.validate_summary(self.summary, self.root, self.summary['tested_binary_sha256'])

    def test_rejects_missing_duplicate_acl_failed_native_and_other_gui_groups(self):
        mutations = [lambda s: s['tests'].pop(), lambda s: s['tests'].append(s['tests'][0]),
            lambda s: s.update(acl_requested=False), lambda s: s['tests'][0].update(passed=False),
            lambda s: s['tests'][0].update(assertions_passed=1),
            lambda s: next(t for t in s['tests'] if t['name'] == 'main-gui-smoke').update(cleanup_killed=True),
            lambda s: s['scanner_preflight'].update(passed=False)]
        for change in mutations:
            summary = copy.deepcopy(self.summary)
            change(summary)
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                preview.validate_summary(summary, self.root, self.summary['tested_binary_sha256'])

    def test_rejects_forged_timeout_states_errors_and_schema(self):
        self.timeout()
        original = copy.deepcopy(self.summary)
        mutations = [lambda s,t,p: s.update(run_error='some deadline'),
            lambda s,t,p: s.update(native_tests_passed=True),
            lambda s,t,p: t.update(error='Markdown style mismatch deadline'),
            lambda s,t,p: t.update(executed=False), lambda s,t,p: t.update(source_bytes_preserved=False),
            lambda s,t,p: t.pop('source_bytes_preserved'), lambda s,t,p: t.update(exit_code=0),
            lambda s,t,p: t.update(main_hwnd_seen=False), lambda s,t,p: t.update(cleanup_killed=False),
            lambda s,t,p: p.update(wall_ms=100), lambda s,t,p: p.update(wall_ms=float('nan')),
            lambda s,t,p: p.update(diagnostic_failure={}), lambda s,t,p: p.update(last_probe={'styles_match': False}),
            lambda s,t,p: p['last_progress'].update(status='failure'),
            lambda s,t,p: p['last_progress'].update(status='complete'),
            lambda s,t,p: p['last_progress']['diagnostic'].update(metric_valid=0),
            lambda s,t,p: p['last_progress']['diagnostic'].update(pending=0),
            lambda s,t,p: p['observer']['snapshots'][0].update(final=True),
            lambda s,t,p: p['observer'].update(scalar_calls=0),
            lambda s,t,p: p['memory'].update(sample_count=2),
            lambda s,t,p: t['markdown_performance']['cases'][0]['stages'].append(copy.deepcopy(p)),
            lambda s,t,p: s.update(unknown=True)]
        for change in mutations:
            summary = copy.deepcopy(original)
            test = next(t for t in summary['tests'] if t['name'] == preview.MD_NAME)
            stage = test['markdown_performance']['cases'][0]['stages'][0]
            change(summary, test, stage)
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                preview.validate_summary(summary, self.root, summary['tested_binary_sha256'])

    def test_rejects_stale_acceptance_and_seal_at_prepare(self):
        (self.evidence / 'native-acceptance.json').write_text('{}', encoding='utf-8')
        self.assert_refused(self.prepare)
        (self.evidence / 'native-acceptance.json').unlink()
        self.prepare()
        self.assert_refused(self.prepare)

    def test_rejects_receipt_or_binary_or_source_changed_after_prepare(self):
        self.prepare()
        self.logs()
        for path in (self.binary / 'ru_notepad.exe', self.binary / 'ru_notepad.build.json', self.root / 'src/main.ru'):
            original = path.read_bytes()
            path.write_bytes(original + b'\n')
            self.assert_refused(self.create)
            path.write_bytes(original)

    def test_rejects_wrong_acceptance_hash_and_missing_receipts(self):
        self.prepare()
        self.logs()
        self.summary['tested_binary_sha256']['ru_notepad.exe'] = '0' * 64
        portable.save_json(self.evidence / 'native-acceptance.json', self.summary)
        self.assert_refused(self.create)

    def test_rejects_unknown_or_unbounded_evidence(self):
        self.prepare()
        self.logs()
        unexpected = self.evidence / 'private.log'
        unexpected.write_text('do not collect', encoding='utf-8')
        self.assert_refused(self.create)
        unexpected.unlink()
        target = self.evidence / 'document_policy.stdout.log'
        target.write_bytes(b'x' * (preview.MAX_JSON_BYTES + 1))
        self.assert_refused(self.create)

    def test_rejects_log_claim_disagreement_and_private_failure(self):
        self.prepare()
        self.logs()
        for name, changed in [('document_policy.stdout.log', b'TOTAL PASS: 23\n'),
            ('main-markdown-launcher-0.log', b'fatal\n'),
            ('ru-scanner-preflight.stdout.log', b'{}\n')]:
            path = self.evidence / name
            original = path.read_bytes()
            path.write_bytes(changed)
            self.assert_refused(self.create)
            path.write_bytes(original)

    def test_rejects_duplicate_json_and_nonfinite_and_schema(self):
        for data in (b'{"a":1,"a":2}', b'{"x":NaN}', b'{"x":Infinity}', b'\xff'):
            with self.subTest(data=data), self.assertRaises(RuntimeError):
                preview.strict_json(data)
        self.prepare()
        self.logs()
        self.summary['schema'] = True
        portable.save_json(self.evidence / 'native-acceptance.json', self.summary)
        self.assert_refused(self.create)

    def test_rejects_noncanonical_paths_and_links(self):
        for name in ('../outside', '/outside', 'build//windows-ci', 'build/./windows-ci', 'build\\windows-ci', 'C:outside'):
            with self.subTest(name=name), self.assertRaises(RuntimeError):
                preview.safe_path(self.root, name)
        link = self.root / 'linked'
        try:
            link.symlink_to(self.binary, target_is_directory=True)
        except OSError:
            # Windows may deny creation to an unprivileged process. The same
            # component lstat rejection is still exercised, not skipped.
            original = Path.lstat
            def linked_info(path):
                if path == self.binary:
                    class Info:
                        st_mode = 0o120777
                        st_file_attributes = 0
                    return Info()
                return original(path)
            with patch.object(Path, 'lstat', linked_info), self.assertRaises(RuntimeError):
                preview.safe_path(self.root, preview.RUN_ROOT + '/bin/ru_notepad.exe')
            return
        with self.assertRaises(RuntimeError):
            preview.safe_path(self.root, 'linked/ru_notepad.exe')

    def test_rejects_fake_windows_reparse_attribute(self):
        original = Path.lstat
        def fake(path):
            value = original(path)
            if path == self.binary / 'ru_notepad.exe':
                class Info:
                    st_mode = value.st_mode
                    st_file_attributes = 0x400
                return Info()
            return value
        with patch.object(Path, 'lstat', fake), self.assertRaises(RuntimeError):
            preview.safe_path(self.root, preview.RUN_ROOT + '/bin/ru_notepad.exe')

    def test_rejects_license_callback_test_exe_and_source_zip_leaks(self):
        self.prepare()
        self.logs()
        for name in ('unexpected.exe', 'official.zip'):
            def leak(target):
                (target / name).write_bytes(b'not allowed')
            self.assert_refused(lambda: preview.create_preview(self.root, 'fake-objdump', leak))

    def test_archive_verifier_rejects_case_duplicate_and_path_escape(self):
        result = self.build()
        output = self.ci / preview.OUTPUT_NAME
        source = output / result['packages']['runtime']['name']
        with zipfile.ZipFile(source) as archive:
            expected = {n.removeprefix(source.stem + '/'): archive.read(n) for n in archive.namelist()}
        for bad_name in ('RU_NOTEPAD.EXE', '../escape', 'vendor/official.zip'):
            with zipfile.ZipFile(source, 'w') as archive:
                for name, data in expected.items():
                    archive.writestr(source.stem + '/' + name, data)
                archive.writestr(source.stem + '/' + bad_name, b'bad')
            with self.subTest(name=bad_name), self.assertRaises(RuntimeError):
                preview.verify_archive(source, expected)

    def test_wrong_sample_is_refused(self):
        with patch.object(preview, 'SAMPLE_SHA256', '0' * 64):
            self.assert_refused(self.build)

    def test_failed_helper_or_missing_controls_refuses_prepare(self):
        path = self.evidence / 'markdown-bulk-helper-controls.json'
        record = json.loads(path.read_text(encoding='utf-8'))
        record['real_windows_runtime'] = False
        portable.save_json(path, record)
        self.assert_refused(self.prepare)

    def test_every_helper_stage_inventory_and_receipt_is_mandatory(self):
        path = self.evidence / 'markdown-bulk-helper-controls.json'
        original = json.loads(path.read_text(encoding='utf-8'))
        for index in range(len(original['stages'])):
            for action in ('missing', 'duplicate', 'failed', 'skip', 'unknown'):
                record = copy.deepcopy(original)
                if action == 'missing':
                    record['stages'].pop(index)
                elif action == 'duplicate':
                    record['stages'].append(record['stages'][index])
                elif action == 'failed':
                    record['stages'][index]['passed'] = False
                elif action == 'skip':
                    record['stages'][index]['status'] = 'skipped'
                else:
                    record['stages'][index]['failure'] = 'unexpected'
                portable.save_json(path, record)
                with self.subTest(index=index, action=action):
                    self.assert_refused(self.prepare)
        for change in ('host_checks', 'windows_checks', 'no_cleanup', 'wrong_stdio', 'wrong_compiler'):
            record = copy.deepcopy(original)
            stages = {s['stage']: s for s in record['stages']}
            if change == 'host_checks': stages['host_controls']['checks'] -= 1
            elif change == 'windows_checks': stages['windows_controls']['checks'] -= 1
            elif change == 'no_cleanup': stages['run_windows_fixture']['owned_process']['cleanup_confirmed'] = False
            elif change == 'wrong_stdio': stages['run_host_fixture']['owned_process']['stdout_bytes'] = 1
            else: record['windows_compiler']['sha256'] = 'invalid'
            portable.save_json(path, record)
            with self.subTest(change=change): self.assert_refused(self.prepare)

    def test_extra_gui_launcher_log_refuses_preview(self):
        self.prepare()
        self.logs()
        path = self.evidence / 'main-markdown-launcher-1.log'
        path.write_text('fatal secondary launcher\n', encoding='utf-8')
        self.assert_refused(self.create)

    def test_actual_markdown_producer_always_reports_source_preservation(self):
        class Api:
            def release_drops(self): pass
        for alter in (False, True):
            fixtures = self.root / ('producer-alter' if alter else 'producer-clean')
            fixtures.mkdir()
            def run_gui(api, isolated, evidence, **kwargs):
                if alter:
                    (isolated / 'unclosed-fence.md').write_bytes(b'changed')
                return {'name': preview.MD_NAME, 'passed': False,
                    'error': 'Markdown GUI open/edit exceeded its original 30-second deadline'}
            with patch.object(ci, 'run_gui', side_effect=run_gui):
                result = ci.run_gui_markdown(Api(), self.binary, fixtures, self.evidence)
            self.assertIs(result['source_bytes_preserved'], not alter)
            self.assertFalse(result['passed'])
            if alter:
                self.assertEqual(result['error'], 'Markdown normal-close flow changed synthetic source bytes')

    def test_missing_seal_or_stale_output_refuses_without_overwrite(self):
        self.assert_refused(self.create)
        result = self.build()
        artifact = self.ci / preview.OUTPUT_NAME / 'preview-artifact.json'
        before = artifact.read_bytes()
        with self.assertRaises(RuntimeError):
            self.create()
        self.assertEqual(artifact.read_bytes(), before)

    def test_original_formal_packager_not_relaxed(self):
        source = (Path(__file__).parent / 'package.py').read_text(encoding='utf-8')
        self.assertIn('validate_acceptance(summary, root)', source)
        self.assertIn("not summary.get('passed')", source)
        self.assertNotIn('manual-preview', source)

    def test_windows_plumbing_preserves_failure_and_uploads_only_separate_preview(self):
        root = Path(__file__).resolve().parents[1]
        script = (root / 'tools/windows_ci.ps1').read_text(encoding='utf-8')
        workflow = (root / '.github/workflows/windows.yml').read_text(encoding='utf-8')
        self.assertLess(script.index("'tools/test_package_manual_preview.py'"), script.index("'tools/build.py'"))
        self.assertIn("'tools/package_manual_preview.py','prepare'", script)
        self.assertIn("'tools/package_manual_preview.py','package'", script)
        self.assertIn('$global:LASTEXITCODE = $ProductExit', script)
        self.assertIn('build/windows-ci/manual-preview/*.zip', workflow)
        self.assertIn('build/windows-ci/manual-preview/preview-artifact.json', workflow)
        self.assertIn('if: success()', workflow)

    def test_actual_powershell_prepare_and_finally_preserve_original_acceptance(self):
        pwsh = shutil.which('pwsh')
        if not pwsh:
            if os.name == 'nt':
                self.fail('PowerShell 7 is mandatory on the Windows preview host')
            self.skipTest('PowerShell 7 unavailable on this non-Windows host')
        source = (Path(__file__).parent / 'windows_ci.ps1').read_text(encoding='utf-8')
        start = source.index('    # Reserve the fresh-run identity')
        end = source.index('    if ($RunCallbackResearch) {', start)
        prepare = source[start:end]
        match = re.search(r'    } else {\n(        try {\n            Invoke-Checked \$Python \$AcceptArgs.*)\n    }\n} finally {',
                          source, re.S)
        self.assertIsNotNone(match)
        script = self.root / 'preview-finally-control.ps1'
        script.write_text("""$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Invoke-Checked([string]$Command,[string[]]$Arguments) {
    $action=if($Arguments[0] -eq 'acceptance'){'acceptance'}else{$Arguments[1]}
    $global:Calls.Add($action)
    $global:LASTEXITCODE=0
    $fail=($action -eq 'prepare' -and $PrepareFail) -or ($action -eq 'package' -and $PackageFail) -or
        ($action -eq 'acceptance' -and $ProductFail)
    if($fail){
        if($action -eq 'acceptance'){$global:LASTEXITCODE=73;throw 'original-product-failure'}
        $global:LASTEXITCODE=9;throw 'controlled-preview-failure'
    }
}
function Invoke-OptionalMarkdownStudy { $global:LASTEXITCODE=0 }
$Python='unused';$Bin=Join-Path $PSScriptRoot 'fake-bin';$MinGW=$PSScriptRoot
$Output=$PSScriptRoot;$Evidence=$PSScriptRoot;$AcceptArgs=@('acceptance');$RunCallbackResearch=$false
foreach($PrepareFail in @($false,$true)) { foreach($ProductFail in @($false,$true)) {
foreach($PackageFail in @($false,$true)) {
    $global:Calls=[System.Collections.Generic.List[string]]::new()
    $global:LASTEXITCODE=0
    $Caught=''
    try {
""" + prepare + match.group(1) + """
    } catch { $Caught=$_.Exception.Message }
    if($ProductFail){
        if($Caught -ne 'original-product-failure'){throw 'Original product exception changed'}
        if($global:LASTEXITCODE -ne 73){throw 'Original product exit changed'}
    } else {
        $Expected=if(-not $PrepareFail -and $PackageFail){'controlled-preview-failure'}else{''}
        if($Caught -ne $Expected){throw 'Unexpected preview exception propagation'}
        if($global:LASTEXITCODE -ne 0){throw 'Original successful product exit changed'}
    }
    if(@($global:Calls | Where-Object {$_ -eq 'acceptance'}).Count -ne 1){throw 'Acceptance not executed exactly once'}
    if(@($global:Calls | Where-Object {$_ -eq 'prepare'}).Count -ne 1){throw 'Preparation not executed exactly once'}
    $ExpectedPackages=if($PrepareFail){0}else{1}
    if(@($global:Calls | Where-Object {$_ -eq 'package'}).Count -ne $ExpectedPackages){throw 'Package ran without prepare'}
}}}
Write-Output 'MANUAL_PREVIEW_POWERSHELL_CONTROLS_PASSED=8'
""", encoding='utf-8', newline='\n')
        result = subprocess.run([pwsh, '-NoProfile', '-NonInteractive', '-File', str(script)],
                                capture_output=True, timeout=30, check=False)
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', errors='replace'))
        self.assertIn(b'MANUAL_PREVIEW_POWERSHELL_CONTROLS_PASSED=8', result.stdout)
        self.assertEqual(result.stderr, b'')


if __name__ == '__main__':
    unittest.main()
