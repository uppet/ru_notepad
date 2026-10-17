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
            setup = dict(schema=1, passed=False, elapsed_seconds=0.25, commands=[dict(stage='dependency-download-scintilla567',
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
