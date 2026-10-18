#!/usr/bin/env python3
"""Host-only policy-pair controls; synthetic receipts never claim native success.

Historical identity/workflow tests remain tied to their fixed accepted replay.
Shared safety controls are explicitly rerun here; no selected test may skip.
"""
from __future__ import annotations

import ast
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import run_policy_prefix_benchmark as runner
import test_direct_style_benchmark as previous
import test_ru_syntax_profile as historical


def success_summary():
    source = previous.success_summary()
    result = runner.empty_results()
    result.update(complete=True, passed=True, preflight_passed=True, preflight=source['preflight'])
    for planned, original in zip(runner.matrix(), source['runs']):
        row = copy.deepcopy(original)
        del row['route']
        row.update(planned, route_check=previous.route_evidence('direct'),
            command_sha256=runner.command_digest(runner.runtime_command(planned, runner.work_root() / 'runs' / planned['id'])))
        result['runs'].append(row)
    return result


class PolicyTests(unittest.TestCase):
    def test_exact_blobs_and_sole_policy_delta(self):
        self.assertEqual(runner.BASELINE_PUBLIC_COMMIT, 'a5f5fd825767cd5af662cba792f5ce352991c21e')
        self.assertEqual(len(runner.tracked(ROOT, runner.BASELINE_TREE)), 120)
        for path in runner.PATHS:
            _, left = runner.variant_sources(path, 'baseline')
            _, right = runner.variant_sources(path, 'prefix')
            runner.assert_policy_graphs(left, right)
            for policy, files in zip(runner.POLICIES, (left, right)):
                self.assertEqual(runner.digest(files[runner.LEXICAL].encode()), runner.POLICY_SHA256[policy])
                self.assertEqual(files['src/ru_syntax.ru'], (ROOT / 'src/ru_syntax.ru').read_text(encoding='utf-8'))
                self.assertIn(runner.execution.ROUTE_ON, files['src/ru_syntax.ru'])
                self.assertNotIn(runner.execution.ROUTE_OFF, files['src/ru_syntax.ru'])
                self.assertEqual(files['src/profile_check.ru'], runner.execution.check_module())

    def test_modified_baseline_and_extra_policy_change_rejected(self):
        _, left = runner.variant_sources('gui', 'baseline')
        _, right = runner.variant_sources('gui', 'prefix')
        for name in (runner.LEXICAL, 'src/main.ru', 'src/ru_syntax.ru'):
            bad = dict(right); bad[name] += '\n# extra\n'
            with self.subTest(name=name), self.assertRaises(runner.Error): runner.assert_policy_graphs(left, bad)
        with self.assertRaises(runner.Error): runner.assert_policy_graphs(right, right)
        with patch.dict(runner.POLICY_SHA256, baseline='0' * 64), self.assertRaises(runner.Error): runner.policy_source('baseline')

    def test_eight_interleaved_ab_ba_rows(self):
        self.assertEqual([row['policy'] for row in runner.matrix()], ['prefix', 'baseline', 'baseline', 'prefix', 'prefix', 'baseline', 'baseline', 'prefix'])
        self.assertEqual(len({row['id'] for row in runner.matrix()}), 8)
        self.assertEqual(runner.shared.verify_corpus()['sha256'], 'ecf8dca884444a5e54e1f40dc6af01cf5e7830ed6fe902d3adf6fdf255f9b3fa')
        self.assertEqual(runner.STYLE_TIMEOUT_SECONDS, 30)
        for path in runner.PATHS:
            self.assertEqual([row['policy'] for row in runner.matrix() if row['path'] == path],
                ['prefix', 'baseline', 'baseline', 'prefix'] if path == 'gui' else ['baseline', 'prefix', 'prefix', 'baseline'])

    def test_dirty_or_untracked_candidate_cannot_prepare(self):
        with self.assertRaisesRegex(runner.Error, 'dirty_candidate_checkout'):
            with patch.object(runner, 'git', return_value=' M src/main.ru'): runner.candidate_sources(ROOT)
        accepted = runner.baseline_sources(ROOT)
        real_git = runner.git
        def clean(*args, root=ROOT):
            return '' if args[0] == 'status' else real_git(*args, root=root)
        with patch.object(runner, 'git', side_effect=clean), patch.object(runner, 'tracked', return_value=list(accepted) + ['unreviewed.ru']):
            with self.assertRaises(runner.Error): runner.candidate_sources(ROOT)

    def test_reviewed_closed_delta_matches_checkout_exactly(self):
        accepted = runner.baseline_sources(ROOT)
        names = set(accepted) | set(runner.OWNED) | set(runner.NEW_INPUTS)
        actual = set(runner.tracked(ROOT)) | set(subprocess.check_output(
            ['git', '-C', str(ROOT), 'ls-files', '--others', '--exclude-standard', '-z'], timeout=30).decode().rstrip('\0').split('\0'))
        actual.discard('')
        self.assertEqual(actual, names)
        candidate = dict(accepted_commit=runner.BASELINE_PUBLIC_COMMIT, accepted_tree=runner.BASELINE_TREE,
            candidate_commit=runner.git('rev-parse', 'HEAD', root=ROOT), candidate_tree=runner.git('rev-parse', 'HEAD^{tree}', root=ROOT),
            accepted_source_sha256=accepted, source_sha256={name: runner.sha(runner.relative_file(ROOT, name)) for name in names},
            reviewed_changes=sorted(runner.REVIEWED_CHANGED_SHA256), harness_inputs=list(runner.OWNED))
        runner.validate_candidate_identity(candidate, ROOT)
        for changed in ('hash', 'extra', 'missing', 'baseline'):
            bad = copy.deepcopy(candidate)
            if changed == 'hash': bad['source_sha256'][runner.LEXICAL] = '0' * 64
            elif changed == 'extra': bad['source_sha256']['unreviewed.ru'] = '0' * 64
            elif changed == 'missing': del bad['source_sha256']['src/main.ru']
            else: bad['accepted_source_sha256']['src/main.ru'] = '0' * 64
            with self.subTest(changed=changed), self.assertRaises(runner.Error): runner.validate_candidate_identity(bad, ROOT)

    def test_common_tampering_cannot_pass_canonical_graph_validator(self):
        value = runner.generated_header()
        value['preflights'] = [{'id': 'direct_native'}, {'id': 'boundary'}]
        for path in runner.PATHS:
            for policy in runner.POLICIES:
                entry, files = runner.variant_sources(path, policy)
                files['src/main.ru'] += '\n# shared unauthorized modification\n'
                value['units'].append(dict(id=runner.variant_id(path, policy), path=path, policy=policy, entry=entry,
                    source_sha256={name: runner.digest(text.encode()) for name, text in files.items()}))
        with tempfile.TemporaryDirectory() as directory, patch.object(runner.execution, 'compiler_identity'):
            with self.assertRaisesRegex(runner.Error, 'generated_graph_not_current_candidate'):
                runner.validate_generated(value, Path(directory), Path(directory))

    def test_loaded_graph_must_equal_complete_reconstructed_closure(self):
        # A claimed map cannot omit lexical policy, add an unknown module, or
        # substitute both variants with the same fake digest.
        value = runner.generated_header()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for path in runner.PATHS:
                for policy in runner.POLICIES:
                    entry, files = runner.variant_sources(path, policy)
                    folder = root / runner.variant_id(path, policy)
                    runner.write_sources(folder, files)
                    value['units'].append(dict(id=folder.name, path=path, policy=policy, entry=entry,
                        source_sha256={name: runner.sha(folder / name) for name in files},
                        loaded_modules_sha256={'src/main.ru': '0' * 64},
                        original_c_sha256='a' * 64, generated_c_sha256='b' * 64, checker=True))
            value['preflights'] = [{'id': 'direct_native'}, {'id': 'boundary'}]
            for changed in ({}, {'unowned.ru': 'a' * 64}, {runner.LEXICAL: '0' * 64}):
                value['units'][0]['loaded_modules_sha256'] = changed
                with patch.object(runner.execution, 'compiler_identity'), patch.object(runner, 'canonical_loaded_modules', return_value={runner.LEXICAL: runner.POLICY_SHA256['baseline']}):
                    with self.assertRaisesRegex(runner.Error, 'loaded_graph_not_canonical'):
                        runner.validate_generated(value, root, root)

    def test_loaded_local_module_outside_closed_source_map_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); folder = root / 'sources'; compiler = root / 'compiler'
            folder.mkdir(); compiler.mkdir()
            source = folder / 'main.ru'; source.write_bytes(b'1.\n')
            extra = folder / 'undeclared.ru'; extra.write_bytes(b'2.\n')
            graph = SimpleNamespace(root=str(source), sources={str(source): '1.\n', str(extra): '2.\n'})
            modules = {'rulang.frontend': SimpleNamespace(parse=lambda text: None),
                       'rulang.modules': SimpleNamespace(load_module_graph=lambda *args: graph)}
            with patch.dict(sys.modules, modules), patch.object(runner, 'tracked', return_value=[]):
                with self.assertRaisesRegex(runner.Error, 'loaded_module_outside_source_inventory'):
                    runner.canonical_loaded_modules('main.ru', folder, compiler, {'main.ru': runner.sha(source)})
                with self.assertRaisesRegex(runner.Error, 'loaded_module_source_hash_changed'):
                    runner.canonical_loaded_modules('main.ru', folder, compiler, {'main.ru': '0' * 64, 'undeclared.ru': runner.sha(extra)})

    def test_all_generated_ru_writes_are_explicit_lf_utf8(self):
        source = (ROOT / 'tools/run_policy_prefix_benchmark.py').read_text(encoding='utf-8')
        calls = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Attribute) and node.func.attr == 'write_text']
        self.assertTrue(calls)
        for node in calls:
            keywords = {item.arg: item.value.value for item in node.keywords if isinstance(item.value, ast.Constant)}
            self.assertEqual(keywords.get('encoding'), 'utf-8')
            self.assertEqual(keywords.get('newline'), '\n')
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / 'sources'
            runner.write_sources(folder, {'src/test.ru': '变量 取 1.\n'})
            self.assertEqual((folder / 'src/test.ru').read_bytes(), '变量 取 1.\n'.encode())

    def test_unknown_and_hostile_paths_are_rejected(self):
        for bad in ('../source.ru', '/source.ru', 'C:/source.ru', 'src\\source.ru'):
            with tempfile.TemporaryDirectory() as directory, self.assertRaises(runner.Error):
                runner.write_sources(Path(directory) / 'sources', {bad: 'x'})
        if os.name != 'nt':
            with tempfile.TemporaryDirectory() as directory:
                base = Path(directory); (base / 'real').mkdir(); (base / 'linked').symlink_to(base / 'real', target_is_directory=True)
                with self.assertRaises(runner.Error): runner.write_sources(base / 'linked/sources', {'test.ru': 'x'})


class EvidenceTests(unittest.TestCase):
    def test_success_shape_is_host_only(self):
        runner.validate_results(success_summary(), complete=True)

    def test_both_policies_require_actual_direct_eligibility(self):
        for index in range(8):
            for field in ('eligible', 'enabled', 'registered', 'ready', 'owner', 'parent', 'document', 'pointer'):
                value = success_summary(); value['runs'][index]['route_check'][0][field] = 0
                with self.subTest(index=index, field=field), self.assertRaises(runner.Error): runner.validate_results(value, complete=True)

    def test_both_policies_preserve_lifecycle_edits_clock_and_byte_checks(self):
        for index in range(8):
            for key, changed in (('cleanup_killed', True), ('skipped', True), ('exit_code', 1), ('executed', False),
                                 ('elapsed_seconds', None), ('elapsed_seconds', float('nan'))):
                value = success_summary(); value['runs'][index]['outcome'][key] = changed
                with self.subTest(index=index, key=key), self.assertRaises((runner.Error, RuntimeError)): runner.validate_results(value, complete=True)
            for key in ('input_preserved', 'full_output_checked', 'expected_style_match'):
                value = success_summary(); value['runs'][index]['output_check'][key] = False
                with self.assertRaises(runner.Error): runner.validate_results(value, complete=True)
            value = success_summary(); value['runs'][index]['outcome']['timer_performance']['wall_ms'] = 30000.01
            with self.assertRaises((runner.Error, RuntimeError)): runner.validate_results(value, complete=True)
        for index in (0, 2, 5, 7):
            for key in ('close_posted', 'main_hwnd_seen', 'detached_from_console'):
                value = success_summary(); value['runs'][index]['outcome'][key] = False
                with self.assertRaises(runner.Error): runner.validate_results(value, complete=True)
            value = success_summary(); value['runs'][index]['outcome']['edit_performance']['operations'].pop()
            with self.assertRaises((runner.Error, RuntimeError)): runner.validate_results(value, complete=True)
            for key in ('timer_queued_navigation', 'timer_paint_region_serviced'):
                value = success_summary(); value['runs'][index]['outcome']['full_gui_checks'][key] = False
                with self.assertRaises(runner.Error): runner.validate_results(value, complete=True)

    def test_preflight_counts_and_positive_negative_route_controls_mandatory(self):
        for index in range(3):
            value = success_summary(); value['preflight'].pop(index)
            with self.assertRaises(runner.Error): runner.validate_results(value, complete=True)
            value = success_summary(); value['preflight'][index]['outcome']['skipped'] = True
            with self.assertRaises(runner.Error): runner.validate_results(value, complete=True)
        for field in ('three_message_positive_control', 'three_message_direct_proof'):
            value = success_summary(); value['preflight'][2]['check'][field] = False
            with self.assertRaises(runner.Error): runner.validate_results(value, complete=True)
        for field in ('cases', 'chunk_checks'):
            value = success_summary(); value['preflight'][0]['check']['report'][field] += 1
            with self.assertRaises(runner.Error): runner.validate_results(value, complete=True)
        for field in ('first_longjmp', 'second_longjmp', 'trap_oom'):
            value = success_summary(); value['preflight'][1]['check'][field] += 1
            with self.assertRaises(runner.Error): runner.validate_results(value, complete=True)

    def test_duplicate_reordered_and_changed_runtime_commands_rejected(self):
        for change in ('duplicate', 'reorder', 'missing', 'command'):
            value = success_summary()
            if change == 'duplicate': value['runs'][1] = value['runs'][0]
            elif change == 'reorder': value['runs'].reverse()
            elif change == 'missing': value['runs'].pop()
            else: value['runs'][0]['command_sha256'] = '0' * 64
            with self.assertRaises(runner.Error): runner.validate_results(value, complete=True)

    def test_pair_report_and_policy_binary_substitution(self):
        summary = success_summary()
        prepared = {'identity': {'candidate': {}}, 'builds': [], 'generated': {'units': []}, 'dependencies': {'RuSyntax.dll': 'a' * 64}}
        for index, identifier in enumerate(runner.variants(), 1):
            unit = {'id': identifier, 'source_sha256': {runner.LEXICAL: str(index) * 64}, 'generated_c_sha256': str(index) * 64}
            build = {'id': identifier, 'exe_sha256': str(index + 4) * 64, 'generated_c_sha256': unit['generated_c_sha256']}
            prepared['builds'].append(build); prepared['generated']['units'].append(unit)
            for row in summary['runs']:
                if runner.variant_id(row['path'], row['policy']) == identifier:
                    row.update(binary_sha256=build['exe_sha256'], generated_c_sha256=build['generated_c_sha256'],
                        graph_sha256=runner.digest(json.dumps(unit['source_sha256'], sort_keys=True).encode()))
        with patch.object(runner, 'validate_prepare', return_value=prepared), patch.object(runner, 'candidate_sources', return_value={}):
            report = runner.verify_results(summary, prepared)
            self.assertEqual(len(report['pairs']), 4)
            self.assertTrue(report['direct_route']); self.assertFalse(report['statistical_confidence_claim'])
            self.assertIsNone(report['performance_success_threshold'])
            for pair in report['pairs']:
                self.assertEqual(pair['prefix_minus_baseline_ms'], pair['prefix_wall_ms'] - pair['baseline_wall_ms'])
                self.assertEqual(pair['prefix_process_seconds'], 42.125)
            for field in ('binary_sha256', 'generated_c_sha256', 'graph_sha256'):
                bad = copy.deepcopy(summary); bad['runs'][0][field] = bad['runs'][2][field]
                with self.assertRaisesRegex(runner.Error, 'row_policy_or_binary_substitution'):
                    runner.verify_results(bad, prepared)
            with patch.object(runner, 'candidate_sources', return_value={'changed': True}), self.assertRaisesRegex(runner.Error, 'candidate_changed_after_build'):
                runner.verify_results(summary, prepared)

    def test_partial_prepare_is_closed_and_never_complete(self):
        value = dict(schema=1, prepared=False, error_code='prepare_failed', identity=None, environment=None,
            corpus=runner.CORPUS, matrix=runner.matrix(), build_budget_seconds=900, compile_timeout_seconds=180,
            elapsed_seconds=0.25, builds=[], commands=[], command_sha256={}, command_measurement=runner.COMMAND_MEASUREMENT, generated=None,
            toolchain=None, dependencies=None, resource_sha256=None)
        runner.validate_prepare(value)
        with self.assertRaises(runner.Error): runner.validate_prepare(value, require_complete=True)
        for key in ('raw_c', 'private_path'):
            bad = dict(value, **{key: '/private/source.c'})
            with self.assertRaises(runner.Error): runner.validate_prepare(bad)
        for builds in ([{'id': 'unexpected'}], [{'id': 'boundary'}], [{'id': x} for x in runner.variants()] + [{'id': 'direct_native'}, {'id': 'boundary'}, {'id': 'extra'}]):
            bad = dict(value, builds=builds)
            with self.assertRaisesRegex(runner.Error, 'build_inventory_invalid'): runner.validate_prepare(bad)
        bad = dict(value, command_sha256={'unreviewed-command': 'a' * 64})
        with self.assertRaisesRegex(runner.Error, 'command_hash_inventory_invalid'): runner.validate_prepare(bad)

    def test_native_platform_guard_remains_required(self):
        with patch.object(runner.shared.sys, 'platform', 'linux'), self.assertRaisesRegex(runner.Error, 'real_windows_x64_required'):
            runner.prepare(Path('missing'), Path('missing'))
        with patch.object(runner.shared.sys, 'platform', 'linux'), self.assertRaisesRegex(runner.Error, 'real_windows_x64_required'):
            runner.run_matrix()

    def test_preflight_directory_failure_has_explicit_failed_record(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / 'runs').mkdir()
            (root / 'runs/preflight-scanner').mkdir()
            records = list(runner.execution.run_native_preflights(None, root, {}))
            self.assertEqual([item['id'] for item in records], list(runner.PREFLIGHTS))
            self.assertTrue(all(not item['passed'] and item['error_code'] for item in records))

    def test_rows_never_start_after_failed_preflight(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(runner, 'ROOT', Path(directory)):
            root = runner.work_root(); root.mkdir(parents=True)
            runner.save_json(root / 'prepare.json', {})
            prepared = {'identity': {'candidate': {}}, 'generated': {}, 'builds': []}
            failed = [dict(id=name, passed=False) for name in runner.PREFLIGHTS]
            with patch.object(runner.shared, 'native_windows', return_value=None), patch.object(runner, 'validate_prepare', return_value=prepared), \
                 patch.object(runner, 'candidate_sources', return_value={}), patch.object(runner, 'validate_generated'), \
                 patch.object(runner.execution, 'run_native_preflights', return_value=iter(failed)), \
                 patch.object(runner.acceptance, 'run_gui_ru_syntax') as gui:
                result = runner.run_matrix()
            self.assertEqual(result['runs'], [])
            self.assertEqual(result['error_code'], 'native_preflight_failed')
            gui.assert_not_called()

    def test_missing_pre_generation_artifacts_yield_sanitized_failure(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(runner, 'ROOT', Path(directory)):
            value = runner.collect()
            self.assertFalse(value['verified'])
            self.assertIn('missing_prepare_receipt', value['errors'])
            self.assertIn('missing_results_receipt', value['errors'])
            self.assertEqual({p.name for p in (Path(directory) / 'build/policy-prefix-evidence').iterdir()}, {'collection.json'})

    def test_partial_logs_and_early_dependency_failure_remain_bounded(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(runner, 'ROOT', Path(directory)):
            root = runner.work_root(); logs = root / 'runs' / runner.matrix()[0]['id'] / 'logs'; logs.mkdir(parents=True)
            (logs / 'main-ru-syntax-launcher-0.log').write_text('private /workspace/data.c\nTOTAL PASS: 8\n', encoding='utf-8')
            (root / 'raw.c').write_text('private C', encoding='utf-8'); (root / 'raw.exe').write_bytes(b'MZ private')
            setup = dict(schema=1, passed=False, error_code='dependency_setup_failed', elapsed_seconds=0.25, commands=[dict(stage='source-archives',
                elapsed_seconds=0.25, exit_code=1, error_code='build_command_failed', cleanup_killed=False, cleanup_failed=False)])
            runner.save_json(Path(directory) / 'build/dependency-policy-prefix-setup.json', setup)
            value = runner.collect(); self.assertFalse(value['verified'])
            self.assertIn('dependency_setup_failed', value['errors'])
            target = Path(directory) / 'build/policy-prefix-evidence'
            content = b''.join(p.read_bytes() for p in target.iterdir())
            self.assertNotIn(b'/workspace/data.c', content); self.assertNotIn(b'private C', content); self.assertNotIn(b'MZ private', content)
            self.assertIn(b'OMITTED_LINE_SHA256', content)
            self.assertLessEqual(sum(p.stat().st_size for p in target.iterdir()), runner.MAX_PUBLIC_BYTES)

    def test_collection_budget_fresh_and_linked_paths_rejected(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(runner, 'ROOT', Path(directory)):
            root = runner.work_root(); logs = root / 'runs' / runner.matrix()[0]['id'] / 'logs'; logs.mkdir(parents=True)
            (logs / 'main-ru-syntax-launcher-0.log').write_text('private\n' * 2000, encoding='utf-8')
            with patch.object(runner, 'MAX_PUBLIC_BYTES', 40000): result = runner.collect()
            self.assertIn('public_evidence_size_exceeded', result['errors'])
            self.assertFalse(list((Path(directory) / 'build/policy-prefix-evidence').glob('*.log')))
            with self.assertRaises(runner.Error): runner.collect()
        if os.name != 'nt':
            with tempfile.TemporaryDirectory() as directory, patch.object(runner, 'ROOT', Path(directory)):
                root = Path(directory); (root / 'real').mkdir(); (root / 'build').symlink_to(root / 'real', target_is_directory=True)
                with self.assertRaises(runner.Error): runner.collect()

def source_archive_receipt(*, passed=True):
    value = {'schema_version': 1, 'implementation': 'reconstructed-offline-v1', 'passed': passed,
             'error_code': None if passed else 'source_failed', 'receipt_error_code': None, 'dependencies': []}
    for identifier, filename, size, checksum in runner.SOURCE_ARCHIVES:
        observation = {'actual_bytes': size if passed else None, 'actual_sha256': checksum if passed else None,
                       'verified': passed, 'error_code': None if passed else 'not_checked'}
        value['dependencies'].append({'id': identifier, 'expected_bytes': size, 'expected_sha256': checksum,
            'source': dict(observation), 'target': dict(observation), 'status': 'copied' if passed else 'failed'})
    return value


def dependency_setup_receipt(*, passed=True):
    return {'schema': 1, 'passed': passed, 'error_code': None if passed else 'dependency_setup_failed',
        'commands': [{'stage': name, 'elapsed_seconds': 0.25, 'exit_code': 0 if passed else 1,
            'error_code': None if passed else 'build_command_failed', 'cleanup_killed': False, 'cleanup_failed': False}
            for name in sorted(runner.DEPENDENCY_STAGES)], 'elapsed_seconds': 1.0}


class OfflineDependencyTests(unittest.TestCase):
    def workflow(self):
        import textwrap
        source = (ROOT / '.github/workflows/policy-prefix-benchmark.yml').read_text(encoding='utf-8')
        return source, textwrap.dedent(source.split("@'\n", 1)[1].split("          '@ |", 1)[0])

    def test_same_source_pins_product_helper_policy_and_historical_contract(self):
        import prepare_source_archives as offline
        self.assertEqual(runner.SOURCE_ARCHIVE_ERRORS, offline.ERROR_CODES)
        self.assertEqual(runner.SOURCE_ARCHIVES,
            tuple((spec.id, spec.filename, spec.bytes, spec.sha256) for spec in offline.ARCHIVES))
        product = (ROOT / 'tools/windows_ci.ps1').read_text(encoding='utf-8')
        workflow, _ = self.workflow()
        for identifier, filename, size, checksum in runner.SOURCE_ARCHIVES:
            self.assertEqual(runner.sha(ROOT / 'third_party/source_archives' / filename), checksum)
            dependency = next(item for item in runner.portable.DEPENDENCIES.values() if item['archive'] == filename)
            self.assertEqual(dependency['sha256'], checksum)
            self.assertIn(f"-ExpectedSize {size} -ExpectedSha256 '{checksum}'", product)
            self.assertIn(f"('{filename}', {size}, '{checksum}')", workflow)
        for source in (product, workflow):
            self.assertNotRegex(source, r'(?i)Invoke-WebRequest|Start-BitsTransfer|urllib|curl|wget|https?://')
        self.assertLess(workflow.index('source-archive-tests'), workflow.index("private, 'source-archives'"))
        self.assertLess(workflow.index('require_passed=True'), workflow.index('source.extractall'))
        self.assertLess(workflow.index('source.extractall'), workflow.index("['mingw32-make.exe'"))
        self.assertLess(workflow.index('source-archive-tests'), workflow.index('python -I tests/ru_direct_fixture_portable.py'))
        self.assertIn('content = stream.read(size + 1)', workflow)
        self.assertIn('zipfile.ZipFile(io.BytesIO(content))', workflow)
        self.assertNotIn('zipfile.ZipFile(archive)', workflow)
        windows = (ROOT / '.github/workflows/windows.yml').read_text(encoding='utf-8')
        self.assertIn('run: python -I tools/test_source_archives.py', windows.split('  windows-native:', 1)[0])

    def test_source_receipt_closed_fields_actual_hashes_and_failure_codes(self):
        value = source_archive_receipt()
        runner.validate_source_archive_receipt(value, require_passed=True)
        failed = source_archive_receipt(passed=False)
        runner.validate_source_archive_receipt(failed)
        with self.assertRaises(runner.Error): runner.validate_source_archive_receipt(failed, require_passed=True)
        for change in ('missing', 'extra', 'order', 'sha', 'size', 'source', 'target', 'status', 'error', 'private', 'bool_size'):
            bad = copy.deepcopy(value)
            if change == 'missing': bad['dependencies'].pop()
            elif change == 'extra': bad['dependencies'].append(copy.deepcopy(bad['dependencies'][0]))
            elif change == 'order': bad['dependencies'].reverse()
            elif change == 'sha': bad['dependencies'][0]['source']['actual_sha256'] = '0' * 64
            elif change == 'size': bad['dependencies'][0]['target']['actual_bytes'] += 1
            elif change in ('source', 'target'):
                bad['dependencies'][0][change].update(verified=False, error_code='not_checked')
            elif change == 'status': bad['dependencies'][0]['status'] = 'pending'
            elif change == 'error': bad['error_code'] = 'private_exception_text'
            elif change == 'private': bad['private'] = '/workspace/private'
            else: bad['dependencies'][0]['source']['actual_bytes'] = True
            with self.subTest(change=change), self.assertRaises(runner.Error):
                runner.validate_source_archive_receipt(bad, require_passed=True)
        bad = source_archive_receipt(passed=False)
        bad['dependencies'][0]['source']['error_code'] = 'some_private_text'
        with self.assertRaises(runner.Error): runner.validate_source_archive_receipt(bad)

    def test_dependency_receipt_requires_both_real_successful_helper_commands(self):
        value = dependency_setup_receipt()
        runner.validate_dependency_setup(value, require_passed=True)
        for change in ('missing', 'old_download', 'exit', 'error', 'cleanup', 'duplicate', 'oversize_time', 'extra'):
            bad = copy.deepcopy(value)
            if change == 'missing': bad['commands'].pop()
            elif change == 'old_download': bad['commands'][0]['stage'] = 'dependency-download-scintilla567'
            elif change == 'exit': bad['commands'][0]['exit_code'] = 17
            elif change == 'error': bad['commands'][0]['error_code'] = 'private_exception_text'
            elif change == 'cleanup': bad['commands'][0]['cleanup_failed'] = True
            elif change == 'duplicate': bad['commands'][0] = bad['commands'][1]
            elif change == 'oversize_time': bad['elapsed_seconds'] = 601
            else: bad['private'] = '/workspace/private'
            with self.subTest(change=change), self.assertRaises(runner.Error): runner.validate_dependency_setup(bad, require_passed=True)
        with self.assertRaises(runner.Error): runner.validate_dependency_setup(dependency_setup_receipt(passed=False), require_passed=True)
        # Historical replay accepts its own exact schema, never the new one.
        with self.assertRaises(runner.Error): runner.execution.validate_dependency_setup(value)

    def test_workflow_runs_real_helper_and_never_extracts_or_builds_after_failed_admission(self):
        import shutil
        import socket
        import zipfile
        _, script = self.workflow()
        for failure in ('tests', 'helper', 'nonzero_after_pass', 'missing_receipt', 'false_claim',
                        'target_size', 'target_hash', None):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "owner's workspace"; root.mkdir()
                (root / 'tools').mkdir()
                for name in ('prepare_source_archives.py', 'test_source_archives.py'):
                    shutil.copyfile(ROOT / 'tools' / name, root / 'tools' / name)
                archives = root / 'third_party/source_archives'; archives.mkdir(parents=True)
                for _, name, _, _ in runner.SOURCE_ARCHIVES:
                    shutil.copyfile(ROOT / 'third_party/source_archives' / name, archives / name)
                if failure == 'helper':
                    (archives / 'scintilla567.zip').write_bytes(b'bad source')
                calls = []
                def execute(command, private, stage, deadline):
                    calls.append(stage)
                    rc = 0
                    if stage == 'source-archive-tests':
                        if failure == 'tests': rc = 9
                        elif failure is None:
                            completed = subprocess.run(list(map(str, command)), capture_output=True, text=True, timeout=120)
                            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
                    elif stage == 'source-archives':
                        if failure == 'missing_receipt': pass
                        elif failure == 'false_claim':
                            fake = source_archive_receipt()
                            fake['dependencies'][0]['target'].update(verified=False, error_code='not_checked')
                            runner.save_json(Path(command[-1]), fake)
                        else:
                            completed = subprocess.run(list(map(str, command)), capture_output=True, text=True, timeout=30)
                            rc = completed.returncode
                            self.assertEqual(completed.stderr, '')
                            if failure == 'nonzero_after_pass':
                                self.assertEqual(rc, 0)
                                rc = 17
                            if failure in ('target_size', 'target_hash'):
                                self.assertEqual(rc, 0)
                                target = root / 'vendor/downloads/scintilla567.zip'
                                raw = target.read_bytes()
                                target.write_bytes(raw + b'x' if failure == 'target_size' else b'X' + raw[1:])
                    else:
                        self.assertIsNone(failure, 'Build started after failed admission')
                        self.assertTrue((root / 'vendor/scintilla/include/Scintilla.h').is_file())
                        self.assertTrue((root / 'vendor/lexilla/src/Lexilla.cxx').is_file())
                    record = {'stage': stage, 'elapsed_seconds': 0.25, 'exit_code': rc,
                        'error_code': 'build_command_failed' if rc else None, 'cleanup_killed': False, 'cleanup_failed': False}
                    runner.save_json(private / (stage + '.json'), record)
                    runner.require(rc == 0, 'build_command_failed')
                    return record
                with patch.object(Path, 'cwd', return_value=root), patch.object(sys, 'path', sys.path.copy()), \
                     patch.object(runner.execution, 'build_command', side_effect=execute), \
                     patch.object(socket, 'create_connection', side_effect=AssertionError('Network forbidden')):
                    if failure:
                        with patch.object(zipfile.ZipFile, 'extractall', side_effect=AssertionError('Extraction forbidden')) as extract:
                            with self.assertRaises((runner.Error, FileNotFoundError)):
                                exec(compile(script, 'offline_dependency_workflow', 'exec'), {})
                            extract.assert_not_called()
                    else:
                        exec(compile(script, 'offline_dependency_workflow', 'exec'), {})
                setup = runner.validate_dependency_setup(runner.read_json(root / 'build/dependency-policy-prefix-setup.json'))
                self.assertEqual(setup['passed'], failure is None)
                self.assertEqual(calls[:1], ['source-archive-tests'])
                self.assertEqual(calls, ['source-archive-tests'] if failure == 'tests' else
                    ['source-archive-tests', 'source-archives'] if failure else
                    ['source-archive-tests', 'source-archives', 'dependency-scintilla', 'dependency-lexilla'])
                if failure:
                    self.assertFalse((root / 'vendor/scintilla').exists())
                    self.assertFalse((root / 'vendor/lexilla').exists())
                else:
                    verified = runner.validate_source_archive_receipt(runner.read_source_archive_receipt(
                        root / 'build/dependency-policy-prefix-source-archives.json'), require_passed=True)
                    self.assertTrue(verified['passed'])
                    for _, name, _, checksum in runner.SOURCE_ARCHIVES:
                        self.assertEqual(runner.sha(root / 'vendor/downloads' / name), checksum)

    def test_policy_prepare_blocks_every_build_until_both_receipts_pass(self):
        for failure in ('source_missing', 'source_failed', 'setup_missing', 'setup_failed'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory, patch.object(runner, 'ROOT', Path(directory)):
                root = Path(directory); (root / 'build').mkdir()
                if failure != 'source_missing':
                    runner.save_json(root / 'build/dependency-policy-prefix-source-archives.json',
                        source_archive_receipt(passed=failure != 'source_failed'))
                if failure != 'setup_missing':
                    runner.save_json(root / 'build/dependency-policy-prefix-setup.json',
                        dependency_setup_receipt(passed=failure != 'setup_failed'))
                with patch.object(runner.shared, 'native_windows'), patch.object(runner, 'source_identity', return_value={}), \
                     patch.object(runner.execution, 'build_command') as build:
                    with self.assertRaises((runner.Error, FileNotFoundError)):
                        runner.prepare(root / 'no-compiler', root / 'no-mingw')
                    build.assert_not_called()
                result = runner.read_json(runner.work_root() / 'prepare.json')
                self.assertFalse(result['prepared'])
                self.assertEqual(result['commands'], [])
                self.assertEqual(result['builds'], [])

    def test_collection_preserves_safe_source_and_setup_failure_without_success(self):
        for passed in (False, True):
            with self.subTest(passed=passed), tempfile.TemporaryDirectory() as directory, patch.object(runner, 'ROOT', Path(directory)):
                root = Path(directory); (root / 'build').mkdir()
                source = source_archive_receipt(passed=passed)
                setup = dependency_setup_receipt(passed=False)
                runner.save_json(root / 'build/dependency-policy-prefix-source-archives.json', source)
                runner.save_json(root / 'build/dependency-policy-prefix-setup.json', setup)
                result = runner.collect()
                evidence = root / 'build/policy-prefix-evidence'
                self.assertEqual(runner.read_json(evidence / 'source-archives.json'), source)
                self.assertEqual(runner.read_json(evidence / 'dependency-setup.json'), setup)
                self.assertFalse(result['verified'])
                self.assertIn('dependency_setup_failed', result['errors'])
                if not passed: self.assertIn('source_archive_preparation_failed', result['errors'])

    def test_missing_hostile_oversize_or_linked_source_receipt_never_publishes(self):
        for change in ('missing', 'private', 'oversize', 'hardlink', 'duplicate_key'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory, patch.object(runner, 'ROOT', Path(directory)):
                root = Path(directory); (root / 'build').mkdir()
                path = root / 'build/dependency-policy-prefix-source-archives.json'
                if change != 'missing':
                    value = source_archive_receipt()
                    if change == 'private': value['private_path'] = '/workspace/private-file'
                    runner.save_json(path, value)
                    if change == 'oversize': path.write_bytes(b' ' * 8193)
                    if change == 'hardlink': os.link(path, root / 'alias.json')
                    if change == 'duplicate_key': path.write_bytes(b'{"passed":true,"passed":false}')
                runner.save_json(root / 'build/dependency-policy-prefix-setup.json', dependency_setup_receipt())
                result = runner.collect()
                self.assertFalse(result['verified'])
                self.assertFalse((root / 'build/policy-prefix-evidence/source-archives.json').exists())
                content = b''.join(item.read_bytes() for item in (root / 'build/policy-prefix-evidence').iterdir())
                self.assertNotIn(b'/workspace/private-file', content)

    def test_full_fixed_log_inventory_and_source_receipt_fit_exact_public_count(self):
        self.assertEqual(runner.MAX_PUBLIC_FILES, 36)
        self.assertEqual(runner.execution.MAX_PUBLIC_FILES, 35)
        self.assertEqual(runner.MAX_PUBLIC_BYTES, runner.execution.MAX_PUBLIC_BYTES)
        for limit in (35, 36):
            with self.subTest(limit=limit), tempfile.TemporaryDirectory() as directory, \
                 patch.object(runner, 'ROOT', Path(directory)), patch.object(runner, 'MAX_PUBLIC_FILES', limit):
                root = runner.work_root(); root.mkdir(parents=True)
                for row in runner.matrix():
                    folder = root / 'runs' / row['id'] / 'logs'; folder.mkdir(parents=True)
                    names = [f'main-ru-syntax-launcher-{index}.log' for index in range(4)] if row['path'] == 'gui' else \
                        ['app_ru_timer_native.stdout.log', 'app_ru_timer_native.stderr.log']
                    for name in names: (folder / name).write_bytes(b'TOTAL PASS: 1\n')
                for name, program in (('scanner', runner.portable.SCANNER_PREFLIGHT_NAME),
                                      ('boundary', 'profile_boundary'), ('direct_native', 'ru_direct_styling_native')):
                    folder = root / 'runs' / ('preflight-' + name); folder.mkdir()
                    for stream in ('stdout', 'stderr'): (folder / (program + '.' + stream + '.log')).write_bytes(b'TOTAL PASS: 1\n')
                self.assertEqual(len(runner.runtime_logs(root)), 30)
                runner.save_json(Path(directory) / 'build/dependency-policy-prefix-source-archives.json', source_archive_receipt())
                runner.save_json(Path(directory) / 'build/dependency-policy-prefix-setup.json', dependency_setup_receipt())
                for name in ('prepare', 'results'): runner.save_json(root / (name + '.json'), {'schema': 1})
                # Synthetic validators isolate file-count accounting; no native pass is asserted.
                with patch.object(runner, 'validate_prepare', side_effect=lambda value: value), \
                     patch.object(runner, 'validate_results', side_effect=lambda value: value), \
                     patch.object(runner, 'verify_results', return_value={'schema': 1, 'synthetic': True}):
                    result = runner.collect()
                self.assertEqual(result['verified'], limit == 36)
                if limit == 35: self.assertIn('public_file_count_exceeded', result['errors'])
                else: self.assertEqual(len(list((Path(directory) / 'build/policy-prefix-evidence').iterdir())), 36)

    def test_source_inputs_and_helper_receipt_never_enter_either_product_zip(self):
        import shutil
        import test_package
        fixture = test_package.PackageTests()
        fixture.setUp()
        try:
            archives = fixture.root / 'third_party/source_archives'; archives.mkdir(parents=True)
            for _, name, _, _ in runner.SOURCE_ARCHIVES:
                shutil.copyfile(ROOT / 'third_party/source_archives' / name, archives / name)
            (fixture.evidence / 'source-archives.json').write_text(json.dumps(source_archive_receipt()), encoding='utf-8')
            result = fixture.create()
            for archive in fixture.archives(result):
                files = test_package.package.verify_archive(archive)
                self.assertFalse(any(name.startswith('third_party/') or name.endswith('.zip') or
                    name.endswith('source-archives.json') for name in files))
                self.assertTrue({'Scintilla.dll', 'Lexilla.dll', 'RuSyntax.dll'} <= files.keys())
        finally:
            fixture.doCleanups()



class WorkflowTests(unittest.TestCase):
    def test_current_comparison_and_fixed_historical_replay_are_distinct(self):
        current = (ROOT / '.github/workflows/policy-prefix-benchmark.yml').read_text(encoding='utf-8')
        old = (ROOT / '.github/workflows/direct-style-benchmark.yml').read_text(encoding='utf-8')
        self.assertIn('branches: [wip]', current)
        self.assertIn("if: github.ref == 'refs/heads/wip'", current)
        self.assertIn('ref: ${{ github.sha }}', current)
        self.assertIn('python -I tools/test_policy_prefix_benchmark.py', current)
        self.assertIn('python -I tests/ru_direct_fixture_portable.py', current)
        for action in ('prepare', 'run', 'verify', 'collect'): self.assertIn('tools/run_policy_prefix_benchmark.py --action ' + action, current)
        for action in ('prepare', 'run', 'verify'):
            blocks = [block for block in current.split('      - name:') if 'tools/run_policy_prefix_benchmark.py --action ' + action in block]
            self.assertEqual(len(blocks), 1)
            self.assertNotIn('if:', blocks[0])
            self.assertNotIn('continue-on-error:', blocks[0])
        self.assertNotIn('  push:', old); self.assertNotIn('inputs:', old)
        self.assertIn('workflow_dispatch:', old)
        self.assertIn('ref: ' + runner.BASELINE_PUBLIC_COMMIT, old)
        self.assertIn('historical-direct-' + runner.BASELINE_PUBLIC_COMMIT + '-run-${{ github.run_id }}', old)
        self.assertNotIn('direct-style-evidence-${{ github.sha }}', old)
        for workflow in (current, old):
            self.assertNotIn('*.exe', workflow); self.assertNotIn('*.dll', workflow)
            self.assertIn('persist-credentials: false', workflow)
            self.assertIn('PYTHONUTF8:', workflow)
            self.assertIn('git config --global core.autocrlf false', workflow)
            self.assertIn('ref: ' + runner.execution.RU_COMMIT, workflow)

    def test_no_runtime_monkeypatch_or_product_switch(self):
        source = (ROOT / 'tools/run_policy_prefix_benchmark.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                self.assertFalse(any(isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name)
                    and t.value.id in ('execution', 'shared', 'acceptance') for t in targets))
        for flag in ('--allow-platform', '--timeout', '--route', '--baseline-ref', '--policy-ref'): self.assertNotIn(flag, source)
        self.assertIn('execution.validate_prepare_execution(record, expected_ids', source)
        self.assertIn("expected_ids = variants() + ['direct_native', 'boundary']", source)


def suite():
    loader = unittest.defaultTestLoader
    result = unittest.TestSuite(loader.loadTestsFromModule(sys.modules[__name__]))
    for name in ('MatrixTests', 'RouteTests', 'CollectionTests', 'FinalContractTests'):
        result.addTests(loader.loadTestsFromTestCase(getattr(previous, name)))
    for name in ('test_native_platform_guard_cannot_be_bypassed', 'test_timeout_kills_and_preserves_nonzero_failure_record',
                 'test_successful_process_after_deadline_is_still_failure', 'test_fast_oversize_log_fails_before_private_cap',
                 'test_cleanup_failure_remains_a_failed_bounded_receipt', 'test_variant_binary_hash_mismatch_cannot_stage'):
        result.addTest(previous.BuildAndIdentityTests(name))
    for name in ('OutcomeElapsedTests', 'ProfileTests', 'VerificationTests', 'OutputAndCollectionTests',
                 'GeneratorPathTests', 'RunIsolationTests', 'PreflightTests',
                 'OfficialDependencyAcquisitionTests', 'EarlyCollectionTests', 'EvidenceSafetyTests'):
        result.addTests(loader.loadTestsFromTestCase(getattr(historical, name)))
    return result


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(suite())
    if result.skipped: print('FAIL: required host controls were skipped')
    raise SystemExit(0 if result.wasSuccessful() and not result.skipped else 1)
