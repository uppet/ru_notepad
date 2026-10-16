#!/usr/bin/env python3
"""Host-only contract/negative controls; these never claim native profiling."""
from __future__ import annotations
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import run_ru_syntax_profile as runner
import test_windows_ci as existing_tests


def profile(row):
    result = {'schema': 1, 'path': row['path'], 'mode': row['mode'], 'instrumentation': row['instrumentation'],
              'counter_interval': None, 'valid': True, 'started': None, 'complete': None, 'failure': None,
              'generation': None, 'corpus': runner.PROFILE_CORPUS.copy(), 'sampling': None, 'stages': None,
              'counters': None, 'trace': None, 'raw_style_trace': None, 'callbacks': None}
    if row['instrumentation'] != 'off':
        sampled = row['instrumentation'] == 'sampled'
        result.update(counter_interval='first_batch_to_last_batch', started=True, complete=True, generation=3,
                      counters={name: 0 for name in runner.COUNTER_FIELDS},
                      trace={'algorithm': 'fnv1a64_le_u32_v1', 'value': '0123456789abcdef', 'batches': 8798,
                             'last_bytes': 1000000, 'last_line': 90909, 'last_done': 1},
                      stages={name: {'calls': 8798, 'sampled_calls': 137 if sampled else 0,
                                     'sampled_ns': 100000 if sampled else 0} for name in runner.STAGES},
                      sampling={'stride': 64, 'origin': 'one_based_batch_divisible_by_64',
                                'sample_batches': 137 if sampled else 0, 'clock_calls': 1096 if sampled else 0,
                                'frequency_hz': 10000000 if sampled else 0,
                                'total_clock_calls': 1352 if sampled else 0,
                                'calibration': {'pairs': 128, 'clock_calls': 256, 'valid': True, 'min_ns': 1,
                                                'median_ns': 2, 'p95_ns': 3, 'max_ns': 4} if sampled else None},
                      raw_style_trace={'algorithm': 'fnv1a64_bytes_v1', 'value': runner.expected_style_checksum(True), 'bytes': 1000000, 'calls': 8798}, callbacks=[])
        result['counters'].update(batches=8798, decoded_events=454540, style_bytes=1000000, feed_bytes=1000000,
                                  snapshot_words=1818160, fold_rows=90910 if row['mode'] == 'full' else 0,
                                  token_calls=363631 if row['mode'] == 'full' else 0,
                                  suffix_copy_bytes=None, suffix_validate_bytes=None)
    return result


def success_summary():
    # Reuse existing synthetic, valid native-receipt fixtures; no native code
    # is run and these records never escape the unit-test process.
    existing = existing_tests.HarnessTests().acceptance()['tests']
    by_name = {entry['name']: entry for entry in existing}
    rows = []
    for item in runner.matrix():
        name = {'gui': 'main-gui-ru-syntax', 'cooperative_console': 'app_ru_timer_native',
                'console_pipeline': 'ru_syntax_native'}[item['path']]
        native = dict(copy.deepcopy(by_name[name]), seconds=42.125)
        outcome = runner.public_outcome(native, item)
        if item['path'] == 'console_pipeline':
            outcome['sync_performance'] = by_name[name]['gui_sync_performance'].copy()
            outcome['assertions_passed'] = 6
        if item['path'] != 'gui':
            measured = outcome['sync_performance'] if item['path'] == 'console_pipeline' else outcome['timer_performance']
            measured.update(chunks=8798, max_read=1023)
        else:
            outcome['timer_performance']['diagnostics']['receipts'][-1]['chunks'] = 8798
        row = dict(item, passed=True, error_code=None, profile=profile(item), output_check={'schema': 1,
                   'input_bytes': 1000000, 'style_bytes': 1000000, 'input_preserved': True,
                   'full_output_checked': True, 'expected_style_match': True, 'algorithm': 'fnv1a64_bytes_v1',
                   'input_checksum': runner.expected_input_checksum(), 'style_checksum': runner.expected_style_checksum(item['mode'] == 'lex_transport')}, outcome=outcome)
        if item['instrumentation'] != 'off' and item['path'] in ('gui', 'cooperative_console'):
            row['profile']['callbacks'] = [{'kind': 'child_subclass', 'depth': 1, 'in_tick': True,
                                            'phase': 'publish', 'calls': 10, 'heap_entries': 50, 'roots': 8}]
        if item['instrumentation'] != 'off' and item['path'] == 'gui':
            row['profile']['generation'] = outcome['timer_performance']['diagnostics']['receipts'][-1]['generation']
        rows.append(row)
    return {'schema': 1, 'corpus': runner.CORPUS, 'matrix': runner.matrix(), 'runs': rows,
            'complete': True, 'passed': True, 'preflight_passed': True,
            'preflight': [{'instrumentation': level, 'passed': True, 'error_code': None,
                'outcome': {'passed': True, 'executed': True, 'cleanup_killed': False, 'exit_code': 0,
                            'error_code': None, 'assertions_passed': 1,
                            'elapsed_seconds': 0.125, 'elapsed_seconds_status': 'valid'},
                'boundary_check': {'schema': 1, 'instrumentation': level, 'passed': True,
                                   'first_longjmp': 2, 'second_longjmp': 1, 'trap_oom': 1}} for level in runner.LEVELS],
            'counter_interval_excluded': ['file_open_before_first_batch',
            'initial_outer_callback_snapshot', 'refresh_after_last_batch'], 'product_acceptance': {'separate': True, 'status': 'not_claimed'}}


class OutcomeElapsedTests(unittest.TestCase):
    def test_acceptance_seconds_are_preserved_for_every_path(self):
        summary = success_summary()
        for row in summary['runs']:
            with self.subTest(path=row['path']):
                self.assertEqual(row['outcome']['elapsed_seconds'], 42.125)
                self.assertEqual(row['outcome']['elapsed_seconds_status'], 'valid')
                self.assertNotEqual(row['outcome']['elapsed_seconds'], runner.primary_wall(row) / 1000)
        for flag in ({}, {'seconds_valid': True}):
            for seconds in (0, 0.125, 99999.5):
                source = dict(passed=True, executed=True, cleanup_killed=False, exit_code=0,
                              seconds=seconds, elapsed_seconds=987654, **flag)
                outcome = runner.public_outcome(source, {'path': 'preflight'})
                self.assertEqual(outcome['elapsed_seconds'], seconds)
                self.assertEqual(outcome['elapsed_seconds_status'], 'valid')
                runner.validate_outcome_elapsed(outcome)

    def test_missing_seconds_are_explicitly_unavailable_without_backfill(self):
        for source in ({}, {'seconds': None}, {'elapsed_seconds': 55, 'wall_ms': 1000},
                       {'last_good_seconds': 12}):
            with self.subTest(source=source):
                outcome = runner.public_outcome(dict(source, passed=False), {'path': 'console_pipeline'})
                self.assertIsNone(outcome['elapsed_seconds'])
                self.assertEqual(outcome['elapsed_seconds_status'], 'unavailable')
                runner.validate_outcome_elapsed(outcome)

    def test_invalid_clock_values_and_flags_cannot_keep_success(self):
        invalid_sources = [{'seconds': value} for value in
                           (-1, True, '2.5', float('nan'), float('inf'), float('-inf'))]
        invalid_sources += [{'seconds': 1, 'seconds_valid': flag} for flag in (False, 0, 1, 'true', None)]
        invalid_sources += [{'seconds': None, 'seconds_valid': False}, {'seconds_valid': True}]
        for source in invalid_sources:
            for path in ('preflight', 'console_pipeline', 'cooperative_console', 'gui'):
                with self.subTest(source=source, path=path):
                    outcome = runner.public_outcome(dict(source, passed=True, executed=True,
                        cleanup_killed=True, exit_code=0, clock_error='private diagnostic'), {'path': path})
                    self.assertFalse(outcome['passed'])
                    self.assertTrue(outcome['executed'])
                    self.assertTrue(outcome['cleanup_killed'])
                    self.assertIsNone(outcome['elapsed_seconds'])
                    self.assertEqual(outcome['elapsed_seconds_status'], 'invalid')
                    self.assertEqual(outcome['error_code'], 'native_run_failed')
                    self.assertNotIn('clock_error', outcome)
                    runner.validate_outcome_elapsed(outcome)
                    runner.check_public_tree(outcome)

    def test_real_acceptance_final_clock_contract_is_mapped(self):
        for final in (3.25, float('nan'), 0.5):
            source = {'passed': True, 'executed': True, 'cleanup_killed': False}
            with patch.object(runner.acceptance.time, 'perf_counter', side_effect=[1.0, final]):
                clock = runner.acceptance.PerformanceClock()
                started = clock()
                runner.acceptance.finish_result_clock(source, clock, started)
            outcome = runner.public_outcome(source, {'path': 'console_pipeline'})
            if final == 3.25:
                self.assertNotIn('seconds_valid', source)
                self.assertEqual(outcome['elapsed_seconds'], 2.25)
                self.assertEqual(outcome['elapsed_seconds_status'], 'valid')
            else:
                self.assertFalse(source['seconds_valid'])
                self.assertFalse(outcome['passed'])
                self.assertIsNone(outcome['elapsed_seconds'])
                self.assertEqual(outcome['elapsed_seconds_status'], 'invalid')
        source = {'passed': False, 'executed': False}
        runner.acceptance.finish_result_clock(source, None, None)
        outcome = runner.public_outcome(source, {'path': 'preflight'})
        self.assertIsNone(outcome['elapsed_seconds'])
        self.assertEqual(outcome['elapsed_seconds_status'], 'unavailable')

    def test_new_complete_success_requires_valid_elapsed_for_preflight_and_matrix(self):
        for group in ('preflight', 'runs'):
            summary = success_summary()
            outcome = summary[group][0]['outcome']
            outcome.update(elapsed_seconds=None, elapsed_seconds_status='unavailable')
            runner.validate_results_receipt(summary)  # Collectible missing data is not invented zero.
            with self.assertRaisesRegex(runner.ProfileError, 'process_elapsed_unavailable_or_invalid'):
                runner.verify_results(summary)
            outcome.update(elapsed_seconds_status='invalid', passed=False, error_code='native_run_failed')
            runner.validate_results_receipt(summary)
            with self.assertRaises(runner.ProfileError):
                runner.verify_results(summary)

    def test_elapsed_receipt_states_are_closed_and_coherent(self):
        for group in ('preflight', 'runs'):
            for change in ('missing_value', 'missing_status', 'invalid_pass', 'unavailable_number',
                           'valid_null', 'valid_nan', 'valid_bool', 'valid_negative', 'unknown_status'):
                summary = success_summary()
                outcome = summary[group][0]['outcome']
                if change == 'missing_value':
                    del outcome['elapsed_seconds']
                elif change == 'missing_status':
                    del outcome['elapsed_seconds_status']
                elif change == 'invalid_pass':
                    outcome.update(elapsed_seconds=None, elapsed_seconds_status='invalid')
                elif change == 'unavailable_number':
                    outcome['elapsed_seconds_status'] = 'unavailable'
                elif change == 'unknown_status':
                    outcome['elapsed_seconds_status'] = 'unknown'
                else:
                    outcome['elapsed_seconds'] = {'valid_null': None, 'valid_nan': float('nan'),
                                                  'valid_bool': True, 'valid_negative': -1}[change]
                with self.subTest(group=group, change=change), self.assertRaisesRegex(
                        runner.ProfileError, 'outcome_elapsed_(missing|invalid)'):
                    runner.validate_results_receipt(summary)

    def test_whole_process_elapsed_does_not_change_styling_comparisons_or_thresholds(self):
        summary = success_summary()
        original = runner.verify_results(summary)
        for row in summary['runs']:
            row['outcome']['elapsed_seconds'] = 99999.5
        self.assertEqual(runner.verify_results(summary), original)
        summary['runs'][0]['outcome']['sync_performance']['wall_ms'] = 30001
        with self.assertRaisesRegex(runner.ProfileError, 'invalid_primary_wall'):
            runner.verify_results(summary)

    def test_collection_keeps_failed_or_unavailable_elapsed_without_raw_clock_errors(self):
        for source, status in (({}, 'unavailable'), ({'seconds': None, 'seconds_valid': False}, 'invalid')):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                work = root / 'build/profile'
                work.mkdir(parents=True)
                summary = success_summary()
                summary.update(complete=False, passed=False)
                summary['runs'] = summary['runs'][:1]
                row = summary['runs'][0]
                row.update(passed=False, profile=None, output_check=None, error_code='native_run_failed',
                           outcome=runner.public_outcome(dict(source, passed=False, executed=True,
                               clock_error='private diagnostic', last_good_seconds=3), row))
                runner.save_json(work / 'results.json', summary)
                with patch.object(runner, 'ROOT', root):
                    runner.collect()
                collected = root / 'build/ru-syntax-profile-evidence/results.json'
                published = runner.read_json(collected)
                outcome = published['runs'][0]['outcome']
                self.assertEqual(outcome['elapsed_seconds_status'], status)
                self.assertIsNone(outcome['elapsed_seconds'])
                self.assertFalse(outcome['passed'])
                self.assertFalse(published['passed'])
                self.assertNotIn(b'private diagnostic', collected.read_bytes())


class PlanTests(unittest.TestCase):
    def test_exact_twenty_rows(self):
        plan = runner.matrix()
        self.assertEqual(len(plan), 20)
        self.assertEqual(len({r['id'] for r in plan}), 20)
        for path, mode in runner.UNITS:
            subset = [r for r in plan if r['path'] == path and r['mode'] == mode]
            self.assertEqual([r['instrumentation'] for r in subset].count('off'), 2)
            self.assertEqual([r['instrumentation'] for r in subset].count('counts'), 1)
            self.assertEqual([r['instrumentation'] for r in subset].count('sampled'), 1)
        self.assertTrue(all(r['mode'] == 'full' for r in plan if r['path'] != 'console_pipeline'))

    def test_exact_original_corpus(self):
        self.assertEqual(runner.verify_corpus(), runner.CORPUS)

    def test_unchanged_deadline_and_cadence(self):
        for attribute, value in [('GUI_RU_TIMER_TIMEOUT_SECONDS', 31), ('GUI_RU_RESPONSE_INTERVAL_MS', 49),
                                 ('GUI_RU_SNAPSHOT_INTERVAL_MS', 249), ('GUI_RU_SNAPSHOT_MESSAGE_LIMIT', 33)]:
            with self.subTest(attribute=attribute), patch.object(runner.acceptance, attribute, value):
                with self.assertRaises(runner.ProfileError):
                    runner.verify_corpus()

    def test_no_linux_native_run(self):
        with patch.object(runner.sys, 'platform', 'linux'):
            with self.assertRaisesRegex(runner.ProfileError, 'real_windows_x64_required'):
                runner.native_windows()

    def test_reconstruct_baseline_without_old_commit_objects(self):
        # Uses current source bytes. The baseline may be shallow and have only
        # the two exact reviewed README/streaming-fixture corrections plus five profiling files.
        hashes = runner.production_tree(ROOT)
        self.assertEqual(len(hashes), 109)
        self.assertIn('src/main.ru', hashes)
        self.assertNotIn('native/profile_counters.h', hashes)

    def test_workflow_is_separate_and_narrow(self):
        workflow = (ROOT / '.github/workflows/ru-syntax-profile.yml').read_text(encoding='utf-8')
        self.assertIn('branches: [wip]', workflow)
        self.assertIn('workflow_dispatch:', workflow)
        for name in runner.OWNED:
            self.assertIn('      - ' + name, workflow)
        self.assertNotIn('pull_request:', workflow)
        self.assertNotIn('build/windows-ci/dist', workflow)
        self.assertNotIn('*.exe', workflow)
        self.assertNotIn('*.dll', workflow)
        self.assertIn('build/ru-syntax-profile-evidence/*.json', workflow)
        self.assertIn('build/ru-syntax-profile-evidence/*.log', workflow)
        self.assertIn('timeout-minutes: 45', workflow)
        self.assertEqual(workflow.count('$env:PATH = "$env:MSYS2_ROOT/mingw64/bin;$env:PATH"'), 2)
        self.assertEqual(runner.BUILD_BUDGET_SECONDS, 1200)
        self.assertEqual(runner.COMPILE_TIMEOUT_SECONDS, 180)
        self.assertEqual(runner.STYLE_TIMEOUT_SECONDS, 30)


class StreamingFixtureIdentityTests(unittest.TestCase):
    def test_only_exact_reviewed_fixture_is_substituted_without_old_git_objects(self):
        entries = runner.subprocess.check_output(['git', '-C', str(ROOT), 'ls-files', '--stage', '-z'], timeout=30)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for entry in entries.split(b'\0'):
                if not entry:
                    continue
                name = entry.split(b'\t', 1)[1].decode('utf-8')
                if name in runner.OWNED:
                    continue
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / name).read_bytes())
            with patch.object(runner.subprocess, 'check_output', return_value=entries) as git_index:
                hashes = runner.production_tree(root)
                self.assertEqual(len(hashes), 109)
                self.assertEqual(hashes['tests/app_streaming_native.ru'], runner.sha(ROOT / 'tests/app_streaming_native.ru'))
                for mutation, expected in (('third_fixture', 'unreviewed_streaming_fixture'),
                                           ('missing_fixture', 'missing_owned_file'),
                                           ('other_file', 'production_source_tree_changed')):
                    target = root / ('src/main.ru' if mutation == 'other_file' else 'tests/app_streaming_native.ru')
                    original = target.read_bytes()
                    try:
                        if mutation == 'missing_fixture':
                            target.unlink()
                        else:
                            target.write_bytes(original + b'\n# unreviewed third version\n')
                        with self.subTest(mutation=mutation), self.assertRaisesRegex(runner.ProfileError, expected):
                            runner.production_tree(root)
                    finally:
                        target.write_bytes(original)
                self.assertTrue(all(call.args[0][3:] == ['ls-files', '--stage', '-z'] for call in git_index.call_args_list))

    def test_generator_pin_and_three_profile_entries_are_exact(self):
        generator = runner.load_generator()
        self.assertEqual(generator.PINNED['tests/app_streaming_native.ru'], runner.REVIEWED_STREAMING_FIXTURE_SHA256)
        for name, expected in {
            'src/main.ru': '7ac0852b07072301bafaddfc0b4585044d7a9a931ce742165ad4e1d20d596adf',
            'tests/app_ru_native.ru': 'e3edfa66bdf06381500d6148f08dd3833a4cad69c35acc9448ba842c61c63d8e',
            'tests/ru_syntax_native.ru': '6bd86a28410354cdbefd89c6649d64f7aefa83fa6e681d97892e2367f1e1740c',
        }.items():
            with self.subTest(source=name):
                self.assertEqual(generator.PINNED[name], expected)
                self.assertEqual(runner.sha(ROOT / name), expected)

    def test_actual_fixture_hash_is_required_in_closed_identity(self):
        compiler = ROOT / 'unused-test-compiler'
        def fake_git(root, *args):
            if args == ('status', '--porcelain'):
                return ''
            if root == compiler:
                return runner.RU_COMMIT if args[-1] == 'HEAD' else runner.RU_TREE
            return '1' * 40 if args[-1] == 'HEAD' else '2' * 40
        with patch.object(runner, 'git', side_effect=fake_git):
            identity = runner.source_identity(ROOT, compiler)
        self.assertEqual(identity['streaming_fixture_sha256'], runner.sha(ROOT / 'tests/app_streaming_native.ru'))
        receipt = {'schema': 1, 'prepared': False, 'error_code': 'synthetic_host_control', 'corpus': runner.CORPUS,
                   'matrix': runner.matrix(), 'builds': [], 'commands': [], 'preflight_builds': [],
                   'build_budget_seconds': runner.BUILD_BUDGET_SECONDS, 'compile_timeout_seconds': runner.COMPILE_TIMEOUT_SECONDS,
                   'initial_build_estimate_seconds': [120, 240], 'elapsed_seconds': 0, 'estimate_exceeded': False,
                   'identity': identity}
        runner.validate_prepare_receipt(receipt)
        identity['streaming_fixture_sha256'] = '0' * 64
        with self.assertRaisesRegex(runner.ProfileError, 'streaming_fixture_hash_mismatch'):
            runner.validate_prepare_receipt(receipt)
        del identity['streaming_fixture_sha256']
        with self.assertRaisesRegex(runner.ProfileError, 'identity_shape_mismatch'):
            runner.validate_prepare_receipt(receipt)


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.row = next(r for r in runner.matrix() if r['instrumentation'] == 'counts')

    def test_off_is_truly_unobserved(self):
        row = runner.matrix()[0]
        value = profile(row)
        runner.validate_profile(value, row)
        value['trace'] = {}
        with self.assertRaisesRegex(runner.ProfileError, 'off_contains_hot_recording'):
            runner.validate_profile(value, row)

    def test_complete_counts_and_samples(self):
        for row in runner.matrix():
            runner.validate_profile(profile(row), row)

    def test_unknown_field_rejected(self):
        value = profile(self.row)
        value['raw_source'] = 'synthetic forbidden field'
        with self.assertRaisesRegex(runner.ProfileError, 'profile_shape_mismatch'):
            runner.validate_profile(value, self.row)

    def test_nonfinite_negative_bool_counter_rejected(self):
        for invalid in (True, -1, 1.2, float('nan'), float('inf'), 2**64):
            with self.subTest(value=invalid):
                value = profile(self.row)
                value['counters']['gc_freed'] = invalid
                with self.assertRaises(runner.ProfileError):
                    runner.validate_profile(value, self.row)

    def test_missing_publish_entry_cannot_report_zero_cost(self):
        for level in ('counts', 'sampled'):
            row = next(row for row in runner.matrix() if row['instrumentation'] == level)
            value = profile(row)
            value['stages']['publish'] = {'calls': 0, 'sampled_calls': 0, 'sampled_ns': 0}
            with self.assertRaisesRegex(runner.ProfileError, 'stage_entry_evidence_missing'):
                runner.validate_profile(value, row)

    def test_counts_has_no_hot_clocks(self):
        value = profile(self.row)
        value['sampling']['clock_calls'] = 1
        with self.assertRaisesRegex(runner.ProfileError, 'counts_contains_hot_clocks'):
            runner.validate_profile(value, self.row)

    def test_sampling_origin_and_count_fixed(self):
        row = next(r for r in runner.matrix() if r['instrumentation'] == 'sampled')
        for field, invalid in [('origin', 'random'), ('stride', 63), ('sample_batches', 138)]:
            value = profile(row)
            value['sampling'][field] = invalid
            with self.assertRaises(runner.ProfileError):
                runner.validate_profile(value, row)

    def test_partial_zero_progress_preserved_not_passed(self):
        value = profile(self.row)
        value.update(started=True, complete=False)
        value['counters'] = {name: 0 for name in runner.COUNTER_FIELDS}
        value['counters'].update(suffix_copy_bytes=None, suffix_validate_bytes=None)
        value['trace'].update(batches=0, last_bytes=0, last_line=0, last_done=0)
        runner.validate_profile(value, self.row, require_complete=False)
        with self.assertRaisesRegex(runner.ProfileError, 'profile_incomplete_or_invalid'):
            runner.validate_profile(value, self.row)

    def test_invalid_phase_scope_preserved_not_passed(self):
        value = profile(self.row)
        value.update(valid=False, complete=False, failure='unbalanced_interval_end')
        runner.validate_profile(value, self.row, require_complete=False)
        with self.assertRaises(runner.ProfileError):
            runner.validate_profile(value, self.row)

    def test_callback_kind_depth_tick_buckets(self):
        value = profile(self.row)
        bucket = {'kind': 'child_subclass', 'depth': 1, 'in_tick': True, 'phase': 'publish', 'calls': 10, 'heap_entries': 50, 'roots': 8}
        value['callbacks'] = [bucket]
        runner.validate_profile(value, self.row)
        for field, invalid in [('kind', 'any_callback'), ('depth', 9), ('in_tick', 1), ('roots', -1)]:
            broken = copy.deepcopy(value)
            broken['callbacks'][0][field] = invalid
            with self.assertRaises(runner.ProfileError):
                runner.validate_profile(broken, self.row)
        value['callbacks'].append(bucket.copy())
        with self.assertRaisesRegex(runner.ProfileError, 'invalid_callback_bucket'):
            runner.validate_profile(value, self.row)

    def test_progress_and_event_count_match_real_corpus(self):
        for group, field, invalid in [('trace', 'last_bytes', 999999), ('trace', 'batches', 8797),
                                      ('counters', 'decoded_events', 454539), ('counters', 'style_bytes', 999999)]:
            value = profile(self.row)
            value[group][field] = invalid
            with self.assertRaisesRegex(runner.ProfileError, 'production_trace_counts_mismatch'):
                runner.validate_profile(value, self.row)

    def test_duplicate_profile_lines_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'runtime.log'
            line = runner.PROFILE_PREFIX + json.dumps(profile(self.row)) + '\n'
            path.write_text(line * 2, encoding='utf-8')
            with self.assertRaisesRegex(runner.ProfileError, 'exactly_one_profile_record_required'):
                runner.profile_from_logs([path], self.row)

    def test_partial_profile_from_log_is_retained(self):
        value = profile(self.row)
        value['complete'] = False
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'runtime.log'
            path.write_text(runner.PROFILE_PREFIX + json.dumps(value) + '\n', encoding='utf-8')
            self.assertFalse(runner.profile_from_logs([path], self.row)['complete'])


class VerificationTests(unittest.TestCase):
    def test_twenty_complete_rows_report_overhead_not_speedup(self):
        result = runner.verify_results(success_summary())
        self.assertEqual(len(result['comparisons']), 5)
        self.assertFalse(result['nested_callback_times_additive'])
        self.assertFalse(result['sampled_stage_times_extrapolated'])
        self.assertEqual(result['product_acceptance']['status'], 'not_claimed')
        self.assertTrue(all(not r['speedup_claim'] for r in result['comparisons']))

    def test_incomplete_duplicate_missing_or_reordered_rows_fail(self):
        for change in ('incomplete', 'missing', 'duplicate', 'reordered'):
            value = success_summary()
            if change == 'incomplete':
                value['complete'] = False
            elif change == 'missing':
                value['runs'].pop()
            elif change == 'duplicate':
                value['runs'][1] = value['runs'][0]
            else:
                value['runs'].reverse()
            with self.subTest(change=change), self.assertRaises(runner.ProfileError):
                runner.verify_results(value)

    def test_failed_timeout_or_killed_rows_fail(self):
        for field in ('passed', 'cleanup_killed'):
            value = success_summary()
            if field == 'passed':
                value['runs'][0]['passed'] = False
            else:
                value['runs'][0]['outcome']['cleanup_killed'] = True
            with self.assertRaises(runner.ProfileError):
                runner.verify_results(value)
        value = success_summary()
        value['runs'][0]['outcome']['sync_performance']['wall_ms'] = 30001
        with self.assertRaisesRegex(runner.ProfileError, 'invalid_primary_wall'):
            runner.verify_results(value)

    def test_trace_mismatch_fails(self):
        value = success_summary()
        row = next(r for r in value['runs'] if r['instrumentation'] == 'counts')
        row['profile']['trace']['value'] = '0000000000000000'
        with self.assertRaisesRegex(runner.ProfileError, 'native_trace_mismatch'):
            runner.verify_results(value)

    def test_missing_complete_byte_styles_fail(self):
        value = success_summary()
        value['runs'][0]['output_check'] = None
        with self.assertRaisesRegex(runner.ProfileError, 'complete_byte_style_evidence_missing'):
            runner.verify_results(value)


class OutputAndCollectionTests(unittest.TestCase):
    def test_all_byte_check_is_independent_of_instrumentation(self):
        summary = success_summary()
        row = summary['runs'][0]
        self.assertEqual(row['instrumentation'], 'off')
        runner.validate_output_check(row['output_check'])
        for key in ('input_preserved', 'full_output_checked', 'expected_style_match'):
            bad = copy.deepcopy(row['output_check'])
            bad[key] = False
            runner.validate_output_check(bad, require_success=False)
            with self.assertRaises(runner.ProfileError):
                runner.validate_output_check(bad)

    def test_no_folding_requires_exact_full_styles(self):
        summary = success_summary()
        row = next(row for row in summary['runs'] if row['mode'] == 'ru_no_folding')
        row['output_check']['style_checksum'] = 'ffffffffffffffff'
        with self.assertRaisesRegex(runner.ProfileError, 'expected_complete_styles_mismatch'):
            runner.verify_results(summary)

    def test_raw_native_style_trace_mismatch_rejected(self):
        summary = success_summary()
        row = next(row for row in summary['runs'] if row['instrumentation'] == 'counts')
        row['profile']['raw_style_trace']['value'] = 'ffffffffffffffff'
        with self.assertRaisesRegex(runner.ProfileError, 'raw_style_trace_mismatch'):
            runner.verify_results(summary)

    def test_gui_normal_close_and_generation_are_required(self):
        for mutation in ('close', 'generation', 'callbacks'):
            summary = success_summary()
            row = next(row for row in summary['runs'] if row['path'] == 'gui' and row['instrumentation'] == 'counts')
            if mutation == 'close':
                row['outcome']['close_posted'] = False
            elif mutation == 'generation':
                row['profile']['generation'] += 1
            else:
                row['profile']['callbacks'] = []
            with self.subTest(mutation=mutation), self.assertRaises(runner.ProfileError):
                runner.verify_results(summary)

    def test_partial_record_rejects_hidden_calibration_fields(self):
        row = next(row for row in runner.matrix() if row['instrumentation'] == 'sampled')
        record = profile(row)
        record['complete'] = False
        record['sampling']['calibration']['raw_source'] = 'private generated source'
        with self.assertRaisesRegex(runner.ProfileError, 'calibration_shape_mismatch'):
            runner.validate_profile(record, row, require_complete=False)

    def test_unknown_nested_outcome_fields_rejected(self):
        summary = success_summary()
        summary['runs'][0]['outcome']['raw_source'] = 'private generated source'
        with self.assertRaisesRegex(runner.ProfileError, 'outcome_shape_mismatch'):
            runner.validate_results_receipt(summary)

    def test_collect_only_closed_json_and_numeric_logs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            work = root / 'build/profile'
            work.mkdir(parents=True)
            summary = success_summary()
            runner.save_json(work / 'results.json', summary)
            runner.save_json(work / 'verification.json', runner.verify_results(summary))
            row = summary['runs'][0]
            logs = work / 'runs' / row['id'] / 'logs'
            logs.mkdir(parents=True)
            (logs / 'profile_pipeline.stdout.log').write_text('TOTAL PASS: 6\nprivate generated source snippet\n', encoding='utf-8')
            (work / 'private.c').write_text('forbidden generated source', encoding='utf-8')
            (work / 'private.exe').write_bytes(b'forbidden executable')
            with patch.object(runner, 'ROOT', root):
                runner.collect()
            published = root / 'build/ru-syntax-profile-evidence'
            self.assertTrue(published.is_dir())
            self.assertEqual({p.suffix for p in published.iterdir()}, {'.json', '.log'})
            contents = b''.join(p.read_bytes() for p in published.iterdir())
            self.assertNotIn(b'private generated source', contents)
            self.assertNotIn(b'forbidden', contents)
            self.assertIn(b'OMITTED_LINE_SHA256', contents)
            self.assertIn(b'not_claimed', contents)
            collection = runner.read_json(published / 'collection.json')
            self.assertFalse(collection['passed'])  # A missing preparation cannot grant success.
            self.assertEqual(collection['error_code'], 'profile_evidence_incomplete')
            results = runner.read_json(published / 'results.json')
            self.assertTrue(all(row['outcome']['elapsed_seconds'] == 42.125
                                and row['outcome']['elapsed_seconds_status'] == 'valid' for row in results['runs']))

    def test_collect_retains_failed_zero_progress_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            work = root / 'build/profile'
            work.mkdir(parents=True)
            summary = success_summary()
            summary.update(complete=False, passed=False)
            summary['runs'] = summary['runs'][:1]
            row = summary['runs'][0]
            row.update(passed=False, profile=None, output_check=None, outcome=None, error_code='native_run_failed')
            runner.save_json(work / 'results.json', summary)
            with patch.object(runner, 'ROOT', root):
                runner.collect()
            published = runner.read_json(root / 'build/ru-syntax-profile-evidence/results.json')
            self.assertFalse(published['complete'])
            self.assertFalse(published['passed'])
            self.assertEqual(published['runs'][0]['error_code'], 'native_run_failed')

    def test_compile_timeout_records_failure_without_running_native_code(self):
        import time
        with tempfile.TemporaryDirectory() as directory:
            private = Path(directory)
            with patch.object(runner.acceptance, 'cleanup_process', side_effect=existing_tests.kill_synthetic), \
                    self.assertRaisesRegex(runner.ProfileError, 'compile_or_build_deadline_exceeded'):
                runner.build_command([sys.executable, '-c', 'import time; time.sleep(2)'], private,
                                     'generate', time.monotonic() + 0.05)
            receipt = runner.read_json(private / 'generate.json')
            self.assertEqual(receipt['error_code'], 'compile_or_build_deadline_exceeded')
            self.assertGreater(receipt['elapsed_seconds'], 0)
            self.assertTrue(receipt['cleanup_killed'])
            self.assertFalse(receipt['cleanup_failed'])
            self.assertIsInstance(receipt['exit_code'], int)


class GeneratorPathTests(unittest.TestCase):
    def test_pinned_compiler_octal_windows_paths_decode(self):
        generator = runner.load_generator()
        for path in (r'C:\work\src\ru_syntax.ru', r'C:\工作目录\src\ru_syntax.ru',
                     '/work/src/ru_syntax.ru', '/工作目录/src/ru_syntax.ru', 'C:/quoted"path/src/ru_syntax.ru'):
            with self.subTest(path=path):
                self.assertEqual(generator.decode_c_source_path(generator.octal(path)), path.replace(chr(92), '/'))

    def test_unpinned_or_invalid_c_escapes_are_rejected(self):
        generator = runner.load_generator()
        for literal in (r'C:\work\src', r'C:\134work\8', r'C:\400work', r'C:\134\101',
                        r'C:\13', r'C:\377', r'C:\000', r'C:\q', 'C:/工作目录'):
            with self.subTest(literal=literal), self.assertRaises(ValueError):
                generator.decode_c_source_path(literal)

    def test_generated_function_locations_keep_windows_module_identity(self):
        generator = runner.load_generator()
        names = [('ru_native_syntax.ru', '扫描'), ('ru_native_syntax.ru', '_解事件'),
                 ('ru_lexical.ru', '批处理'), ('ru_syntax.ru', '_施样'), ('ru_syntax.ru', '_一步'),
                 ('ru_lexical.ru', '_记词'), ('main.ru', '消息处理'), ('file_drop.ru', '_编辑子过程'),
                 ('main.ru', '语法时钟')]
        code = ''
        for index, (name, function) in enumerate(names):
            source = generator.octal('C:/工作目录/src/'.replace('/', chr(92)) + name)
            code += ('static RuFunction ru_function_%d_descriptor = {"%s",0};\n' % (index, generator.octal(function)))
            code += ('static Val ru_function_%d(Env *global, Val self, int call_line, Val *args) {\n'
                     '    ru_source = "%s";\n}\n' % (index, source))
        functions = generator.generated_functions(code)
        self.assertEqual(len(functions), 9)
        self.assertEqual([(entry[1], entry[2].rsplit('/', 1)[-1]) for entry in functions],
                         [(generator.octal(function), name) for name, function in names])


class GeneratedContractTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('RU_SYNTAX_PROFILE_CONTRACT_DIR'),
                         'Set RU_SYNTAX_PROFILE_CONTRACT_DIR to a fresh prepare output for generation-only integration.')
    def test_current_prepare_output_validates(self):
        generated = Path(os.environ['RU_SYNTAX_PROFILE_CONTRACT_DIR']).resolve()
        manifest = runner.read_json(generated / 'manifest.json')
        units = runner.validate_manifest(manifest, generated)
        self.assertEqual(len(units), 5)
        self.assertEqual(manifest['baseline_inputs']['tests/app_streaming_native.ru'], runner.REVIEWED_STREAMING_FIXTURE_SHA256)
        for unit in units:
            self.assertNotIn('app_streaming_native.ru', [Path(name).name for name in unit['graph_sha256']])
            self.assertNotIn('app_streaming_native.ru', (generated / unit['generated_c']).read_text(encoding='utf-8'))
        runner.validate_preflight_manifest(manifest['preflight'], generated)
        missing = copy.deepcopy(manifest)
        del missing['preflight']
        with self.assertRaisesRegex(runner.ProfileError, 'invalid_generator_manifest'):
            runner.validate_manifest(missing, generated)
        wrong = dict(manifest['preflight'], bridge_origin_sha256='0' * 64)
        with self.assertRaisesRegex(runner.ProfileError, 'preflight_manifest_identity_mismatch'):
            runner.validate_preflight_manifest(wrong, generated)


    @unittest.skipUnless(os.environ.get('RU_SYNTAX_PROFILE_CONTRACT_DIR'),
                         'Fresh generated C needed for Windows-anchor instrumentation integration.')
    def test_windows_octal_anchors_and_missing_publish(self):
        import re
        generated = Path(os.environ['RU_SYNTAX_PROFILE_CONTRACT_DIR']).resolve()
        manifest = runner.read_json(generated / 'manifest.json')
        unit = next(unit for unit in manifest['units'] if unit['path'] == 'gui')
        generator = runner.load_generator()
        original = (generated / unit['generated_c']).read_text(encoding='utf-8')
        def windows_source(match):
            basename = generator.decode_c_source_path(match[1]).rsplit('/', 1)[-1]
            return 'ru_source = "' + generator.octal('C:/工作目录/src/'.replace('/', chr(92)) + basename) + '";'
        code = re.sub(r'^    ru_source = "([^"\n]*)";', windows_source, original, flags=re.M)
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / 'input.c', Path(directory) / 'output.c'
            source.write_text(code, encoding='utf-8')
            for level in runner.LEVELS:
                audit = generator.instrument(input_c=source, output_c=output, instrumentation=level, path='gui', mode='full')
                self.assertEqual(sorted(audit['function_kinds'].values()), [1, 2, 3, 4, 5, 6, 8, 9, 10])
                self.assertIn('expected_byte_check', audit['anchors'])
            broken = code.replace('{"' + generator.octal('_施样') + '",', '{"missing_publish",')
            self.assertNotEqual(code, broken)
            source.write_text(broken, encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Missing or duplicate stage anchor: 4'):
                generator.instrument(input_c=source, output_c=output, instrumentation='sampled', path='gui', mode='full')


class RunIsolationTests(unittest.TestCase):
    def test_repeated_gui_off_has_fresh_binary_and_launcher_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'build-bin'
            source.mkdir()
            files = {}
            for name in ('ru_notepad.exe', 'Scintilla.dll', 'Lexilla.dll', 'RuSyntax.dll'):
                (source / name).write_bytes(b'host-only fixture; never executed')
                files[name] = runner.sha(source / name)
            build = {'files': files}
            first = runner.stage_run_binaries(build, source, root / 'first-bin')
            (first / 'ru_notepad-previous.log').write_text('preserved previous evidence', encoding='utf-8')
            second = runner.stage_run_binaries(build, source, root / 'second-bin')
            self.assertEqual({p.name for p in second.iterdir()}, set(files))
            self.assertEqual(list(second.glob('ru_notepad-*.log')), [])
            self.assertTrue((first / 'ru_notepad-previous.log').exists())
            with self.assertRaisesRegex(runner.ProfileError, 'fresh_run_binary_directory_required'):
                runner.stage_run_binaries(build, source, first)
            (source / 'ru_notepad.exe').write_bytes(b'changed')
            with self.assertRaisesRegex(runner.ProfileError, 'variant_binary_changed'):
                runner.stage_run_binaries(build, source, root / 'bad-bin')


class PreflightTests(unittest.TestCase):
    def test_native_command_uses_owned_absolute_bridge_argument(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('profile_boundary.exe', 'profile_bridge.dll'):
                (root / name).write_bytes(b'host-only fixture; never executed')
            self.assertEqual(runner.preflight_command(root),
                             [str((root / name).resolve()) for name in ('profile_boundary.exe', 'profile_bridge.dll')])

    def test_exact_boundary_counts(self):
        check = success_summary()['preflight'][0]['boundary_check']
        runner.validate_preflight_check(check, 'off')
        for key, value in (('first_longjmp', 1), ('second_longjmp', 0), ('trap_oom', 0)):
            broken = dict(check, **{key: value})
            with self.subTest(key=key), self.assertRaisesRegex(runner.ProfileError, 'preflight_boundary_unproven'):
                runner.validate_preflight_check(broken, 'off')

    def test_missing_preflight_rejects_otherwise_successful_matrix(self):
        summary = success_summary()
        summary.update(preflight=[], preflight_passed=False)
        with self.assertRaisesRegex(runner.ProfileError, 'native_preflight_missing'):
            runner.verify_results(summary)

    def test_failed_preflight_rejects_otherwise_successful_matrix(self):
        summary = success_summary()
        summary['preflight'][1]['passed'] = False
        with self.assertRaisesRegex(runner.ProfileError, 'native_preflight_failed'):
            runner.verify_results(summary)

    def test_generation_failure_codes_preserved(self):
        source = (ROOT / 'tools/profile_ru_syntax.py').read_text(encoding='utf-8') + (ROOT / 'native/profile_counters.h').read_text(encoding='utf-8')
        import re
        observed = set(re.findall(r'rp_invalid\("([a-z_]+)"\)', source))
        self.assertTrue(observed <= runner.FAILURES, observed - runner.FAILURES)


class ExplicitEncodingTests(unittest.TestCase):
    def test_owned_text_io_declares_utf8_without_locale_defaults(self):
        import ast
        import textwrap
        sources = [(name, (ROOT / name).read_text(encoding='utf-8')) for name in
                   ('tools/run_ru_syntax_profile.py', 'tools/test_ru_syntax_profile.py')]
        workflow = (ROOT / '.github/workflows/ru-syntax-profile.yml').read_text(encoding='utf-8')
        sources.append(('workflow_python', textwrap.dedent(workflow.split("@'\n", 1)[1].split("          '@ |", 1)[0])))
        for name, source in sources:
            for node in ast.walk(ast.parse(source)):
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                    continue
                if node.func.attr in ('read_text', 'write_text'):
                    encoding = next((item.value for item in node.keywords if item.arg == 'encoding'), None)
                    with self.subTest(source=name, line=node.lineno):
                        self.assertIsInstance(encoding, ast.Constant)
                        self.assertEqual(encoding.value, 'utf-8')
                elif node.func.attr in ('encode', 'decode'):
                    with self.subTest(source=name, line=node.lineno):
                        self.assertTrue(node.args or any(item.arg == 'encoding' for item in node.keywords))

    def test_source_scan_survives_forced_cp1252_default(self):
        import io
        # Reproduce Windows' non-UTF-8 default deterministically, independent
        # of PYTHONUTF8 (which isolated Python intentionally ignores).
        data = (ROOT / 'tools/profile_ru_syntax.py').read_bytes()
        with self.assertRaises(UnicodeDecodeError):
            data.decode('cp1252')
        def cp1252_default(encoding, stacklevel=2):
            return 'cp1252' if encoding is None or encoding == 'locale' else encoding
        with patch.object(io, 'text_encoding', side_effect=cp1252_default):
            with self.assertRaises(UnicodeDecodeError):
                (ROOT / 'tools/profile_ru_syntax.py').read_bytes().decode(io.text_encoding(None))
            PreflightTests().test_generation_failure_codes_preserved()
            PlanTests().test_workflow_is_separate_and_narrow()


class OfficialDependencyAcquisitionTests(unittest.TestCase):
    def test_workflow_uses_existing_official_powershell_client_and_guards(self):
        workflow = (ROOT / '.github/workflows/ru-syntax-profile.yml').read_text(encoding='utf-8')
        product = (ROOT / 'tools/windows_ci.ps1').read_text(encoding='utf-8')
        for item in runner.portable.DEPENDENCIES.values():
            self.assertIn("Invoke-WebRequest -Uri 'https://www.scintilla.org/" + item['archive'] + "'", product)
            self.assertIn("('" + item['archive'] + "', '" + item['sha256'] + "')", workflow)
        self.assertIn("$env:PROFILE_PWSH = Join-Path $PSHOME 'pwsh.exe'", workflow)
        self.assertIn("Invoke-WebRequest -Uri 'https://www.scintilla.org/", workflow)
        self.assertIn("'-Command', download", workflow)
        self.assertIn('-TimeoutSec 120', workflow)
        self.assertNotIn('urllib', workflow)
        self.assertNotIn('-UserAgent', workflow)
        self.assertNotIn('-Headers', workflow)
        self.assertLess(workflow.index('archive.stat().st_size <= 32 * 1024 * 1024'), workflow.index('archive.read_bytes()'))
        self.assertLess(workflow.index('hashlib.sha256(content).hexdigest() == checksum'), workflow.index('zipfile.ZipFile(archive)'))
        self.assertIn("'..' not in pathlib.PurePosixPath(item.filename).parts", workflow)

    def test_workflow_rejects_oversize_and_bad_hash_before_zip_access(self):
        import textwrap
        import types
        import zipfile
        from unittest.mock import Mock
        workflow = (ROOT / '.github/workflows/ru-syntax-profile.yml').read_text(encoding='utf-8')
        script = textwrap.dedent(workflow.split("@'\n", 1)[1].split("          '@ |", 1)[0])
        for invalid in ('oversize', 'bad_hash'):
            with self.subTest(invalid=invalid), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "owner's workspace"
                root.mkdir()
                calls = []
                def download(command, private, label, deadline):
                    calls.append(label)
                    self.assertEqual(label, 'dependency-download-scintilla567')
                    self.assertEqual(command[0], 'selected-powershell.exe')
                    self.assertIn("Invoke-WebRequest -Uri 'https://www.scintilla.org/scintilla567.zip'", command[-1])
                    self.assertIn("owner''s workspace", command[-1])
                    archive = root / 'vendor/downloads/scintilla567.zip'
                    if invalid == 'oversize':
                        with archive.open('wb') as output:
                            output.truncate(32 * 1024 * 1024 + 1)
                    else:
                        archive.write_bytes(b'not the pinned official archive')
                stub = types.SimpleNamespace(build_command=download, read_json=runner.read_json)
                opened_zip = Mock(side_effect=AssertionError('ZIP must not be reached'))
                with patch.object(Path, 'cwd', return_value=root), patch.dict(os.environ, {'PROFILE_PWSH': 'selected-powershell.exe'}), \
                        patch.dict(sys.modules, {'run_ru_syntax_profile': stub}), patch.object(sys, 'path', sys.path.copy()), \
                        patch.object(zipfile, 'ZipFile', opened_zip), self.assertRaises(AssertionError):
                    exec(compile(script, 'dependency_workflow', 'exec'), {})
                self.assertEqual(calls, ['dependency-download-scintilla567'])
                opened_zip.assert_not_called()
                self.assertFalse(runner.read_json(root / 'build/dependency-profile-setup.json')['passed'])

    def test_download_failure_receipt_is_preserved_without_success_or_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'build').mkdir()
            setup = {'schema': 1, 'passed': False, 'commands': [{'stage': 'dependency-download-scintilla567',
                     'elapsed_seconds': 0.5, 'exit_code': 1, 'error_code': 'build_command_failed',
                     'cleanup_killed': False, 'cleanup_failed': False}], 'elapsed_seconds': 0.6}
            runner.save_json(root / 'build/dependency-profile-setup.json', setup)
            with patch.object(runner, 'ROOT', root):
                self.assertFalse(runner.collect()['passed'])
            evidence = root / 'build/ru-syntax-profile-evidence'
            self.assertEqual(runner.read_json(evidence / 'dependency-setup.json'), setup)
            collected = runner.read_json(evidence / 'collection.json')
            for key in ('passed', 'profile_verified', 'native_execution_recorded',
                        'prepare_receipt_present', 'results_receipt_present'):
                self.assertIs(collected[key], False)
            self.assertEqual(collected['error_code'], 'profile_evidence_missing')


class EarlyCollectionTests(unittest.TestCase):
    def test_empty_root_yields_explicit_failure_receipt_and_nonzero_cli(self):
        import contextlib
        import io
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = io.StringIO()
            self.assertFalse((root / 'build').exists())
            with patch.object(runner, 'ROOT', root), patch.object(sys, 'argv', ['runner', '--action', 'collect']), \
                    contextlib.redirect_stdout(output):
                self.assertEqual(runner.main(), 1)
            self.assertIn('RU_SYNTAX_PROFILE_COLLECT=FAIL', output.getvalue())
            evidence = root / 'build/ru-syntax-profile-evidence'
            self.assertEqual([path.name for path in evidence.iterdir()], ['collection.json'])
            receipt = runner.read_json(evidence / 'collection.json')
            self.assertEqual(receipt['files'], [])
            self.assertEqual(receipt['error_code'], 'profile_evidence_missing')
            for key in ('prepare_receipt_present', 'results_receipt_present', 'native_execution_recorded',
                        'profile_verified', 'passed', 'binaries_uploaded', 'generated_sources_uploaded'):
                self.assertIs(receipt[key], False)
            self.assertEqual(receipt['product_acceptance'], {'separate': True, 'status': 'not_claimed'})
            self.assertFalse((root / 'build/profile').exists())

    def test_linked_build_parent_is_rejected_before_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'root'
            outside = Path(directory) / 'outside'
            root.mkdir()
            outside.mkdir()
            try:
                (root / 'build').symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest('Host cannot create symlinks; Windows reparse checks remain required.')
            with patch.object(runner, 'ROOT', root), self.assertRaisesRegex(runner.ProfileError, 'linked_owned_path'):
                runner.collect()
            self.assertEqual(list(outside.iterdir()), [])


class EvidenceSafetyTests(unittest.TestCase):
    def test_duplicate_json_and_nonfinite_json_rejected(self):
        for text in ('{"a":1,"a":2}', '{"x":NaN}', '{"x":Infinity}', '{broken}'):
            with self.subTest(text=text), self.assertRaises(runner.ProfileError):
                runner.strict_json(text)

    def test_relative_paths_reject_traversal_unc_and_drive(self):
        with tempfile.TemporaryDirectory() as directory:
            for name in ('../source.c', '/tmp/source.c', 'C:/source.c', 'C:\\source.c', '\\\\host\\share', 'a/../b', 'a//b', './a'):
                with self.subTest(name=name), self.assertRaises(runner.ProfileError):
                    runner.relative_file(Path(directory), name, must_exist=False)

    def test_symlink_and_linked_parent_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'real').mkdir()
            (root / 'real/file.log').write_text('test', encoding='utf-8')
            try:
                (root / 'linked').symlink_to(root / 'real', target_is_directory=True)
            except OSError:
                self.skipTest('Host cannot create a symlink; reparse-path check remains required on Windows')
            with self.assertRaisesRegex(runner.ProfileError, 'linked_owned_path'):
                runner.relative_file(root, 'linked/file.log')

    def test_private_paths_and_nonfinite_public_data_rejected(self):
        for value in ('C:\\Users\\someone\\code.c', '/workspace/private/code.c', '/home/user/file', float('inf')):
            with self.subTest(value=value), self.assertRaises(runner.ProfileError):
                runner.check_public_tree({'value': value})

    def test_raw_generated_source_and_private_paths_never_copied(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'runtime.log'
            path.write_text('C:\\private\\generated.c: source snippet\nint secret = 42;\n'
                            'RU_GUI_SYNC size=1000000 wall_ms=1.2\nTOTAL PASS: 8\n', encoding='utf-8')
            content, omitted = runner.sanitize_runtime_log(path)
            self.assertEqual(omitted, 2)
            self.assertNotIn(b'private', content)
            self.assertNotIn(b'secret', content)
            self.assertIn(b'RU_GUI_SYNC size=1000000 wall_ms=1.2', content)
            self.assertIn(b'TOTAL PASS: 8', content)

    def test_atomic_json_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'receipt.json'
            runner.save_json(path, {'schema': 1, 'complete': False})
            self.assertEqual(runner.read_json(path), {'schema': 1, 'complete': False})
            self.assertFalse(path.with_suffix('.json.pending').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
