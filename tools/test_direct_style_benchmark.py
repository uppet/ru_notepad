#!/usr/bin/env python3
"""Host-only negative controls. Synthetic receipts never claim native success.

The selected historical helper tests are still executed. Historical inventory
and workflow tests deliberately remain with their fixed historical checkout.
No required test is silently skipped in this suite.
"""
from __future__ import annotations
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import run_direct_style_benchmark as runner
import test_ru_syntax_profile as historical
import test_windows_ci as product_tests


def route_evidence(route):
    return [dict(phase=phase, enabled=int(route == 'direct'), eligible=int(route == 'direct'),
                 registered=1, ready=1, owner=1, parent=1, document=1, generation=3,
                 revision=0, length=1000000, mask=3, pointer=1, pending=1 - phase)
            for phase in (0, 1)]


def success_summary():
    native = {record['name']: record for record in product_tests.HarnessTests().acceptance()['tests']}
    result = runner.empty_results()
    result.update(complete=True, passed=True, preflight_passed=True)
    result['preflight'] = [dict(id=name, passed=True, error_code=None, check=None,
        outcome=runner.outcome(dict(passed=True, executed=True, cleanup_killed=False, exit_code=0,
            seconds=0.125, assertions_passed=runner.DIRECT_ASSERTIONS if name == 'direct_native' else 1), 'preflight'))
        for name in runner.PREFLIGHTS]
    sources = runner.acceptance.scanner_preflight_sources(ROOT)
    result['preflight'][0]['check'] = {'source_sha256': sources, 'report': {
        'cases': 157, 'chunk_checks': 942, 'ru_assertions_per_backend': 0, 'sanitizer': None,
        'source_sha256': sources['native/ru_scan.c'], 'library_sha256': 'a' * 64}}
    result['preflight'][1]['check'] = dict(schema=1, instrumentation='off', passed=True, first_longjmp=2, second_longjmp=1, trap_oom=1)
    result['preflight'][2]['check'] = dict(assertions=runner.DIRECT_ASSERTIONS,
        three_message_positive_control=True, three_message_direct_proof=True)
    for row in runner.matrix():
        original = copy.deepcopy(native['main-gui-ru-syntax' if row['path'] == 'gui' else 'app_ru_timer_native'])
        original['seconds'] = 42.125
        out = runner.outcome(original, row['path'])
        if row['path'] == 'gui':
            out['timer_performance']['diagnostics']['receipts'][-1]['chunks'] = 8798
        else:
            out['timer_performance'].update(chunks=8798, max_read=1023)
        result['runs'].append(dict(row, passed=True, error_code=None, outcome=out,
            output_check=dict(schema=1, input_bytes=1000000, style_bytes=1000000,
                input_preserved=True, full_output_checked=True, expected_style_match=True,
                algorithm='fnv1a64_bytes_v1', input_checksum=runner.shared.expected_input_checksum(),
                style_checksum=runner.shared.expected_style_checksum()),
            route_check=route_evidence(row['route']), binary_sha256='b' * 64,
            generated_c_sha256='c' * 64, graph_sha256='d' * 64))
    return result


class MatrixTests(unittest.TestCase):
    def test_fixed_eight_interleaved_rows_two_pairs_each(self):
        rows = runner.matrix()
        self.assertEqual(len(rows), 8)
        self.assertEqual(len({row['id'] for row in rows}), 8)
        self.assertEqual([row['path'] for row in rows], ['gui', 'cooperative_console', 'gui', 'cooperative_console',
                                                       'cooperative_console', 'gui', 'cooperative_console', 'gui'])
        for path in runner.PATHS:
            for repeat in (1, 2):
                self.assertEqual({row['route'] for row in rows if row['path'] == path and row['repeat'] == repeat}, {'direct', 'message'})
        self.assertEqual(runner.shared.verify_corpus()['sha256'], 'ecf8dca884444a5e54e1f40dc6af01cf5e7830ed6fe902d3adf6fdf255f9b3fa')
        self.assertEqual(runner.STYLE_TIMEOUT_SECONDS, 30)
        self.assertEqual(runner.COMPILE_TIMEOUT_SECONDS, 180)

    def test_valid_native_shaped_receipts_validate_host_only(self):
        runner.validate_results(success_summary(), complete=True)

    def test_missing_duplicate_reordered_and_unexecuted_rows_fail(self):
        for change in ('missing', 'duplicate', 'order', 'unexecuted', 'partial'):
            value = success_summary()
            if change == 'missing': value['runs'].pop()
            elif change == 'duplicate': value['runs'][1] = value['runs'][0]
            elif change == 'order': value['runs'].reverse()
            elif change == 'unexecuted': value['runs'][0]['outcome']['executed'] = False
            else: value['complete'] = False
            with self.subTest(change=change), self.assertRaises((runner.Error, RuntimeError)):
                runner.validate_results(value, complete=True)

    def test_all_native_preflights_are_mandatory(self):
        for index in range(3):
            for change in ('missing', 'skipped', 'unexecuted', 'cleanup', 'bad_proof'):
                value = success_summary()
                target = value['preflight'][index]
                if change == 'missing': value['preflight'].pop(index)
                elif change == 'skipped': target['outcome']['skipped'] = True
                elif change == 'unexecuted': target['outcome']['executed'] = False
                elif change == 'cleanup': target['outcome']['cleanup_killed'] = True
                else: target['check'] = None
                with self.subTest(index=index, change=change), self.assertRaises((runner.Error, RuntimeError)):
                    runner.validate_results(value, complete=True)

    def test_missing_bad_clock_zero_nan_and_no_inference_fail(self):
        for seconds, status in ((None, 'unavailable'), (None, 'invalid'), (0, 'valid'), (-1, 'valid'),
                                (float('nan'), 'valid'), (True, 'valid')):
            for index in (0, 1):
                value = success_summary()
                out = value['runs'][index]['outcome']
                out.update(elapsed_seconds=seconds, elapsed_seconds_status=status)
                with self.subTest(seconds=seconds, index=index), self.assertRaises((runner.Error, RuntimeError)):
                    runner.validate_results(value, complete=True)
        value = runner.outcome({'passed': False, 'wall_ms': 1, 'elapsed_seconds': 123}, 'preflight')
        self.assertIsNone(value['elapsed_seconds'])
        self.assertEqual(value['elapsed_seconds_status'], 'unavailable')

    def test_lifecycle_overrun_and_cleanup_cannot_pass(self):
        for key, changed in [('close_posted', False), ('main_hwnd_seen', False), ('detached_from_console', False),
                             ('exit_code', 3), ('cleanup_killed', True), ('skipped', True)]:
            value = success_summary()
            value['runs'][0]['outcome'][key] = changed
            with self.subTest(key=key), self.assertRaises((runner.Error, RuntimeError)):
                runner.validate_results(value, complete=True)
        for index in (0, 1):
            value = success_summary()
            value['runs'][index]['outcome']['timer_performance']['wall_ms'] = 30000.01
            with self.assertRaises((runner.Error, RuntimeError)):
                runner.validate_results(value, complete=True)

    def test_every_byte_and_expected_style_required(self):
        for key, changed in [('full_output_checked', False), ('expected_style_match', False), ('input_preserved', False),
                             ('style_checksum', '0' * 16), ('input_checksum', '0' * 16), ('style_bytes', 999999)]:
            value = success_summary()
            value['runs'][0]['output_check'][key] = changed
            with self.subTest(key=key), self.assertRaises((runner.Error, RuntimeError)):
                runner.validate_results(value, complete=True)

    def test_six_gui_edits_navigation_and_natural_paint_remain_required(self):
        for key in ('edit_performance', 'full_gui_checks'):
            value = success_summary()
            del value['runs'][0]['outcome'][key]
            with self.assertRaises((runner.Error, RuntimeError)):
                runner.validate_results(value, complete=True)
        value = success_summary()
        value['runs'][0]['outcome']['edit_performance']['operations'].pop()
        with self.assertRaises((runner.Error, RuntimeError)):
            runner.validate_results(value, complete=True)
        for key in ('timer_queued_navigation', 'timer_paint_region_serviced'):
            value = success_summary()
            value['runs'][0]['outcome']['full_gui_checks'][key] = False
            with self.assertRaises((runner.Error, RuntimeError)):
                runner.validate_results(value, complete=True)

    def test_unknown_output_data_and_private_paths_rejected(self):
        for field in ('private_path', 'arbitrary_source'):
            value = success_summary()
            value['runs'][0]['outcome'][field] = '/workspace/private/input.ru'
            with self.assertRaises(runner.Error):
                runner.validate_results(value)


class RouteTests(unittest.TestCase):
    def test_only_one_exact_bool_changes(self):
        original = (ROOT / 'src/ru_syntax.ru').read_text(encoding='utf-8')
        changed = runner.substitute_route(original, 'message')
        self.assertEqual(changed.replace(runner.ROUTE_OFF, runner.ROUTE_ON), original)
        self.assertEqual(runner.substitute_route(original, 'direct'), original)
        for bad in (original.replace(runner.ROUTE_ON, ''), original + runner.ROUTE_ON, changed):
            with self.assertRaises(runner.Error): runner.substitute_route(bad, 'message')
        direct = {'src/ru_syntax.ru': original, 'src/main.ru': 'same'}
        message = dict(direct, **{'src/ru_syntax.ru': changed})
        runner.assert_route_graphs(direct, message)
        message['src/main.ru'] = 'extra alteration'
        with self.assertRaises(runner.Error): runner.assert_route_graphs(direct, message)

    def test_real_endpoint_evidence_cannot_be_labels_only(self):
        for route in runner.ROUTES:
            runner.validate_route_checks(route_evidence(route), route)
            for field in runner.ROUTE_FIELDS:
                value = route_evidence(route)
                value[0][field] += 1
                with self.subTest(route=route, field=field), self.assertRaises(runner.Error):
                    runner.validate_route_checks(value, route)
            with self.assertRaises(runner.Error): runner.validate_route_checks(route_evidence(route)[:1], route)
            with self.assertRaises(runner.Error): runner.validate_route_checks(route_evidence(route) + route_evidence(route), route)

    def test_route_record_parser_rejects_duplicate_missing_unknown_and_noninteger(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'runtime.log'
            valid = ''.join(runner.ROUTE_PREFIX + ' '.join(f'{key}={value[key]}' for key in runner.ROUTE_FIELDS) + '\n'
                            for value in route_evidence('direct'))
            path.write_text(valid, encoding='utf-8')
            self.assertEqual(runner.route_checks([path], 'direct'), route_evidence('direct'))
            for bad in (valid + valid, valid.splitlines()[0] + '\n', valid.replace('mask=3', 'mask=3.0'),
                        valid.replace('parent=1', 'private=1'), valid.replace('eligible=1', 'eligible=0')):
                path.write_text(bad, encoding='utf-8')
                with self.assertRaises(runner.Error): runner.route_checks([path], 'direct')

    def test_current_graph_has_common_scaffolding_and_unchanged_policy(self):
        for path in runner.PATHS:
            entry, files = runner.verification_sources(path)
            self.assertIn(entry, files)
            self.assertEqual(files['src/ru_lexical.ru'], (ROOT / 'src/ru_lexical.ru').read_text(encoding='utf-8-sig'))
            self.assertEqual(files['src/ru_native_syntax.ru'], (ROOT / 'src/ru_native_syntax.ru').read_text(encoding='utf-8-sig'))
            self.assertEqual(files['src/ru_syntax.ru'], (ROOT / 'src/ru_syntax.ru').read_text(encoding='utf-8-sig'))
            self.assertEqual(files['src/profile_check.ru'], runner.check_module())
            self.assertIn('档案 其 路由 柄 0', files['src/main.ru'])
            self.assertIn('借 取 空.', runner.ROUTE_SOURCE)
            self.assertNotIn('其 增 \'pointer\'', runner.ROUTE_SOURCE)

    def test_checker_only_has_exact_reversible_stub_edit(self):
        source = runner.generator.octal('C:/fixture/src/profile_check.ru')
        name = runner.generator.octal('_档案核对')
        body = ('static RuFunction ru_function_1_descriptor = {"' + name + '",0};\n'
                'static Val ru_function_1(Env *global, Val self, int call_line, Val *args) {\n'
                '    ru_source = "' + source + '";\n'
                '    env_set(env, "x", args[0]);\n    env_set(env, "y", args[1]);\n    env_set(env, "z", args[2]);\n'
                '    Val ru_v_2 = v_fact(0);\n    return ru_v_2;\n}\n')
        checked = runner.checker_only(body)
        self.assertIn('rp_expected_check(args[0],args[1],args[2])', checked)
        self.assertIn(runner.generator.CHECK_C, checked)
        for forbidden in ('atexit(rp_emit)', 'rp_call_enter(', 'rp_step_open(', 'rp_calibrate();'):
            self.assertNotIn(forbidden, checked)
        for bad in (body.replace('v_fact(0)', 'v_fact(1)'), body + body, body.replace('profile_check.ru', 'other.ru')):
            with self.assertRaises(runner.Error): runner.checker_only(bad)


class BuildAndIdentityTests(unittest.TestCase):
    def test_native_platform_guard_cannot_be_bypassed(self):
        with patch.object(runner.shared.sys, 'platform', 'linux'):
            with self.assertRaisesRegex(runner.Error, 'real_windows_x64_required'):
                runner.prepare(Path('fake'), Path('fake'))
        source = (ROOT / 'tools/run_direct_style_benchmark.py').read_text(encoding='utf-8')
        self.assertNotIn('--allow-platform', source)
        self.assertNotIn('--timeout', source)

    def test_reviewed_delta_hashes_are_exact_and_old_locks_untouched(self):
        self.assertGreater(len(runner.REVIEWED_CHANGED_SHA256), 20)
        for name, expected in runner.REVIEWED_CHANGED_SHA256.items():
            self.assertEqual(runner.sha(ROOT / name), expected, name)
        self.assertEqual(runner.generator.BASELINE_COMMIT, 'b525b47dab6a51494cde29a3aa468cfe2d14703a')
        self.assertEqual(runner.generator.BASELINE_TREE, 'a1fb1a02abf76d80d3daf6f385edf29901264d73')
        self.assertNotEqual(runner.BASELINE_TREE, runner.generator.BASELINE_TREE)
        self.assertEqual(len(runner.tracked(ROOT, runner.BASELINE_TREE)), 114)

    def test_bad_source_inventory_and_hash_fail_closed(self):
        # Test actual candidate source identity while making only the local
        # clean/index boundary synthetic. No output becomes native evidence.
        names = sorted(set(runner.tracked(ROOT, runner.BASELINE_TREE)) | set(runner.OWNED) | set(runner.NEW_INPUTS))
        real_git = runner.git
        def clean(*args, root=ROOT):
            return '' if args[0] == 'status' else real_git(*args, root=root)
        real_tracked = runner.tracked
        def current(root, tree=None):
            return real_tracked(root, tree) if tree else names
        with patch.object(runner, 'git', side_effect=clean), patch.object(runner, 'tracked', side_effect=current):
            identity = runner.candidate_sources(ROOT)
            self.assertEqual(set(identity['source_sha256']), set(names))
            with patch.object(runner, 'REVIEWED_CHANGED_SHA256', dict(runner.REVIEWED_CHANGED_SHA256, **{'src/main.ru': '0' * 64})):
                with self.assertRaisesRegex(runner.Error, 'reviewed_candidate_hash_mismatch'): runner.candidate_sources(ROOT)
            with patch.object(runner, 'tracked', return_value=names + ['unexpected.ru']):
                with self.assertRaises(runner.Error): runner.candidate_sources(ROOT)

    def test_timeout_kills_and_preserves_nonzero_failure_record(self):
        with tempfile.TemporaryDirectory() as directory:
            private = Path(directory)
            with patch.object(runner.shared.acceptance, 'cleanup_process', side_effect=product_tests.kill_synthetic):
                with self.assertRaises(runner.Error):
                    runner.build_command([sys.executable, '-c', 'import time; time.sleep(2)'], private, 'build-control', time.monotonic() + 0.05)
            receipt = runner.read_json(private / 'build-control.json')
            self.assertTrue(receipt['cleanup_killed'])
            self.assertIsNotNone(receipt['error_code'])
            self.assertGreater(receipt['elapsed_seconds'], 0)

    def test_successful_process_after_deadline_is_still_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            private = Path(directory)
            process = Mock(returncode=0)
            process.poll.return_value = 0
            with patch.object(runner.subprocess, 'Popen', return_value=process), \
                 patch.object(runner.time, 'monotonic', side_effect=[0, 181, 181]):
                with self.assertRaisesRegex(runner.Error, 'build_overrun'):
                    runner.build_command([], private, 'build-control', 900)
            self.assertEqual(runner.read_json(private / 'build-control.json')['error_code'], 'build_overrun')

    def test_fast_oversize_log_fails_before_private_cap(self):
        with tempfile.TemporaryDirectory() as directory:
            private = Path(directory)
            with self.assertRaisesRegex(runner.Error, 'build_log_limit_exceeded'):
                runner.build_command([sys.executable, '-c', "print('x'*1048577)"], private, 'build-control', time.monotonic() + 30)
            self.assertEqual(runner.read_json(private / 'build-control.json')['error_code'], 'build_log_limit_exceeded')
            self.assertLessEqual((private / 'build-control.stdout.log').stat().st_size, runner.MAX_LOG_BYTES)

    def test_cleanup_failure_remains_a_failed_bounded_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            private = Path(directory)
            process = Mock(returncode=None)
            process.poll.return_value = None
            with patch.object(runner.subprocess, 'Popen', return_value=process), \
                 patch.object(runner.time, 'monotonic', side_effect=[0, 181, 182]), \
                 patch.object(runner.acceptance, 'cleanup_process', side_effect=RuntimeError('private path')):
                with self.assertRaises(runner.Error): runner.build_command([], private, 'build-control', 900)
            record = runner.read_json(private / 'build-control.json')
            self.assertTrue(record['cleanup_failed'])
            self.assertEqual(record['error_code'], 'build_cleanup_failed')
            self.assertNotIn('private path', json.dumps(record))

    def test_variant_binary_hash_mismatch_cannot_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'one.exe').write_bytes(b'host fixture')
            with self.assertRaisesRegex(runner.Error, 'variant_binary_changed'):
                runner.shared.stage_run_binaries({'files': {'one.exe': '0' * 64}}, root, root / 'staged')


class CollectionTests(unittest.TestCase):
    def test_no_results_yields_partial_error_json_and_no_false_success(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(runner, 'ROOT', Path(directory)):
            result = runner.collect()
            self.assertFalse(result['verified'])
            self.assertIn('missing_results_receipt', result['errors'])
            files = list((Path(directory) / 'build/direct-style-evidence').iterdir())
            self.assertTrue(files)
            self.assertTrue(all(path.suffix == '.json' for path in files))

    def test_partial_failed_rows_and_sanitized_logs_retained(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            work = root / 'build/direct-style'
            logs = work / 'runs' / runner.matrix()[0]['id'] / 'logs'
            logs.mkdir(parents=True)
            value = runner.empty_results()
            value['runs'] = [dict(runner.matrix()[0], passed=False, error_code='run_failed', outcome=None,
                                 output_check=None, route_check=None, binary_sha256=None, generated_c_sha256=None, graph_sha256=None)]
            runner.save_json(work / 'results.json', value)
            (logs / 'main-ru-syntax-launcher-1.log').write_text('private generated C /workspace/secret.c\nTOTAL PASS: 8\n', encoding='utf-8')
            (work / 'private.c').write_text('forbidden source', encoding='utf-8')
            (work / 'private.exe').write_bytes(b'forbidden binary')
            with patch.object(runner, 'ROOT', root): result = runner.collect()
            self.assertFalse(result['verified'])
            target = root / 'build/direct-style-evidence'
            combined = b''.join(path.read_bytes() for path in target.iterdir())
            self.assertNotIn(b'forbidden', combined)
            self.assertNotIn(b'/workspace/secret', combined)
            self.assertIn(b'OMITTED_LINE_SHA256', combined)
            self.assertIn(b'run_failed', combined)
            self.assertEqual({path.suffix for path in target.iterdir()}, {'.log', '.json'})

    def test_fresh_evidence_and_unlinked_paths_required(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(runner, 'ROOT', Path(directory)):
            runner.collect()
            with self.assertRaises(runner.Error): runner.collect()
        if os.name != 'nt':
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / 'real').mkdir(); (root / 'build').symlink_to(root / 'real', target_is_directory=True)
                with patch.object(runner, 'ROOT', root), self.assertRaises(runner.Error): runner.collect()


class FinalContractTests(unittest.TestCase):
    def test_both_route_policy_changes_fail_even_with_recomputed_hashes(self):
        manifest = dict(schema=1, units=[], preflights=[{'id': 'direct_native'}, {'id': 'boundary'}],
            graph_contract=runner.GRAPH_NOTES, check_module_sha256=runner.digest(runner.check_module().encode('utf-8')),
            check_c_sha256=runner.digest(runner.generator.CHECK_C.encode('utf-8')),
            route_on_sha256=runner.digest(runner.ROUTE_ON.encode('utf-8')),
            route_off_sha256=runner.digest(runner.ROUTE_OFF.encode('utf-8')))
        for path in runner.PATHS:
            entry, original = runner.verification_sources(path)
            for route in runner.ROUTES:
                files = dict(original)
                files['src/ru_syntax.ru'] = runner.substitute_route(files['src/ru_syntax.ru'], route)
                files['src/ru_lexical.ru'] += '\n# Same unauthorized modification in both routes.\n'
                manifest['units'].append(dict(id=runner.variant_id(path, route), path=path, route=route, entry=entry,
                    source_sha256={name: runner.digest(text.encode('utf-8')) for name, text in files.items()}))
        with tempfile.TemporaryDirectory() as directory, self.assertRaisesRegex(runner.Error, 'generated_graph_not_current_candidate'):
            runner.validate_generated(manifest, Path(directory))

    def test_windows_newline_translation_cannot_change_canonical_graph_bytes(self):
        import ast
        source = (ROOT / 'tools/run_direct_style_benchmark.py').read_text(encoding='utf-8')
        writers = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)
                   and isinstance(node.func, ast.Attribute) and node.func.attr == 'write_text']
        self.assertGreaterEqual(len(writers), 6)
        for node in writers:
            keyword = next((kw.value for kw in node.keywords if kw.arg == 'newline'), None)
            self.assertIsInstance(keyword, ast.Constant)
            self.assertEqual(keyword.value, '\n')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'source.ru'
            content = runner.check_module()
            real_write = Path.write_text
            def windows_write(self, text, **kwargs):
                if kwargs.get('newline') is None:
                    text = text.replace('\n', '\r\n')
                return real_write(self, text, **kwargs)
            with patch.object(Path, 'write_text', windows_write):
                path.write_text(content, encoding='utf-8', newline='\n')
            self.assertEqual(path.read_bytes(), content.encode('utf-8'))
            self.assertEqual(runner.sha(path), runner.digest(path.read_text(encoding='utf-8').encode('utf-8')))

    def test_pair_report_shows_values_and_rejects_route_binary_substitution(self):
        summary = success_summary()
        prepared = {'builds': [], 'generated': {'units': []}, 'dependencies': {'RuSyntax.dll': 'a' * 64}}
        for index, identifier in enumerate(runner.variants(), 1):
            unit = {'id': identifier, 'source_sha256': {'src/ru_syntax.ru': str(index) * 64},
                    'generated_c_sha256': str(index) * 64}
            build = {'id': identifier, 'exe_sha256': str(index + 4) * 64, 'generated_c_sha256': unit['generated_c_sha256']}
            prepared['builds'].append(build); prepared['generated']['units'].append(unit)
            for row in summary['runs']:
                if runner.variant_id(row['path'], row['route']) == identifier:
                    row.update(binary_sha256=build['exe_sha256'], generated_c_sha256=build['generated_c_sha256'],
                        graph_sha256=runner.digest(json.dumps(unit['source_sha256'], sort_keys=True).encode('utf-8')))
        with patch.object(runner, 'validate_prepare', return_value=prepared):
            report = runner.verify_results(summary, prepared)
            self.assertEqual(len(report['pairs']), 4)
            self.assertFalse(report['statistical_confidence_claim'])
            self.assertIsNone(report['performance_success_threshold'])
            for item in report['pairs']:
                self.assertEqual(item['direct_process_seconds'], 42.125)
                self.assertEqual(item['direct_minus_message_ms'], item['direct_wall_ms'] - item['message_wall_ms'])
            summary['runs'][0]['binary_sha256'] = summary['runs'][2]['binary_sha256']
            with self.assertRaisesRegex(runner.Error, 'row_route_or_binary_substitution'):
                runner.verify_results(summary, prepared)

    def test_early_dependency_failure_is_collectible_and_never_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / 'build').mkdir()
            setup = dict(schema=1, passed=False, elapsed_seconds=0.25, commands=[dict(
                stage='dependency-download-scintilla567', elapsed_seconds=0.25, exit_code=1,
                error_code='build_command_failed', cleanup_killed=False, cleanup_failed=False)])
            runner.save_json(root / 'build/dependency-direct-style-setup.json', setup)
            with patch.object(runner, 'ROOT', root): result = runner.collect()
            self.assertFalse(result['verified'])
            self.assertIn('dependency_setup_failed', result['errors'])
            self.assertEqual(runner.read_json(root / 'build/direct-style-evidence/dependency-setup.json'), setup)
            setup['commands'][0]['private_path'] = '/private/data'
            with self.assertRaises(runner.Error): runner.validate_dependency_setup(setup)

    def test_public_limit_checked_before_overlimit_log_is_written(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            logs = root / 'build/direct-style/runs' / runner.matrix()[0]['id'] / 'logs'; logs.mkdir(parents=True)
            (logs / 'main-ru-syntax-launcher-0.log').write_text('untrusted line\n' * 2000, encoding='utf-8')
            with patch.object(runner, 'ROOT', root), patch.object(runner, 'MAX_PUBLIC_BYTES', 40000): result = runner.collect()
            self.assertFalse(result['verified'])
            self.assertIn('public_evidence_size_exceeded', result['errors'])
            target = root / 'build/direct-style-evidence'
            self.assertFalse(list(target.glob('*.log')))
            self.assertLessEqual(sum(path.stat().st_size for path in target.iterdir()), 40000)

    def test_fixed_log_inventory_rejects_extras_and_does_not_recurse_fixtures(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            work = root / 'build/direct-style'
            logs = work / 'runs' / runner.matrix()[0]['id'] / 'logs'; logs.mkdir(parents=True)
            (logs / 'unexpected.log').write_text('private', encoding='utf-8')
            with self.assertRaisesRegex(runner.Error, 'unexpected_runtime_log'): runner.runtime_logs(work)
            (logs / 'unexpected.log').unlink()
            fixtures = logs.parent / 'fixtures'; fixtures.mkdir()
            (fixtures / 'private.log').write_text('not a process log', encoding='utf-8')
            self.assertEqual(runner.runtime_logs(work), [])


class WorkflowTests(unittest.TestCase):
    def test_wip_research_only_and_full_product_unchanged(self):
        paired = (ROOT / '.github/workflows/direct-style-benchmark.yml').read_text(encoding='utf-8')
        self.assertIn('branches: [wip]', paired)
        self.assertIn("if: github.ref == 'refs/heads/wip'", paired)
        self.assertIn('fetch-depth: 0', paired)
        self.assertIn('run: python -I tools/test_direct_style_benchmark.py', paired)
        self.assertNotIn('pull_request:', paired)
        self.assertNotIn('*.exe', paired)
        self.assertNotIn('*.dll', paired)
        self.assertIn('build/direct-style-evidence/*.json', paired)
        self.assertIn('build/direct-style-evidence/*.log', paired)
        product = (ROOT / '.github/workflows/windows.yml').read_bytes()
        accepted = subprocess.check_output(['git', '-C', str(ROOT), 'show', runner.BASELINE_TREE + ':.github/workflows/windows.yml'])
        self.assertEqual(product, accepted)

    def test_historical_manual_replay_always_checks_out_accepted_public_source(self):
        old = (ROOT / '.github/workflows/ru-syntax-profile.yml').read_text(encoding='utf-8')
        self.assertNotIn('  push:', old)
        self.assertIn('workflow_dispatch:', old)
        self.assertIn('ref: ' + runner.BASELINE_PUBLIC_COMMIT, old)
        self.assertNotIn('ru-syntax-profile-evidence-${{ github.sha }}', old)
        self.assertIn('historical-profile-' + runner.BASELINE_PUBLIC_COMMIT, old)
        self.assertNotIn('inputs:', old)

    def test_independent_dependency_deadline_and_official_hashes(self):
        paired = (ROOT / '.github/workflows/direct-style-benchmark.yml').read_text(encoding='utf-8')
        self.assertIn('Invoke-WebRequest', paired)
        self.assertIn('https://www.scintilla.org/', paired)
        self.assertIn('-TimeoutSec 120', paired)
        self.assertIn('started + 600', paired)
        self.assertIn('archive.stat().st_size <= 32 * 1024 * 1024', paired)
        self.assertLess(paired.index('hashlib.sha256(content).hexdigest() == checksum'), paired.index('zipfile.ZipFile(archive)'))
        for item in runner.portable.DEPENDENCIES.values(): self.assertIn(item['sha256'], paired)
        self.assertNotIn('urllib', paired)


def suite():
    loader = unittest.defaultTestLoader
    output = unittest.TestSuite(loader.loadTestsFromModule(sys.modules[__name__]))
    for name in ('OutcomeElapsedTests', 'ProfileTests', 'VerificationTests', 'OutputAndCollectionTests',
                 'GeneratorPathTests', 'RunIsolationTests', 'PreflightTests',
                 'OfficialDependencyAcquisitionTests', 'EarlyCollectionTests', 'EvidenceSafetyTests'):
        output.addTests(loader.loadTestsFromTestCase(getattr(historical, name)))
    return output


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(suite())
    if result.skipped:
        print('FAIL: required host controls were skipped')
    raise SystemExit(0 if result.wasSuccessful() and not result.skipped else 1)
