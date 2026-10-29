#!/usr/bin/env python3
"""Portable controls only: no GUI, real child process, attach, or termination."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

import run_markdown_phase_profile as runner

SOURCE = Path(os.environ.get('MARKDOWN_PROFILE_SOURCE_ROOT', str(Path(__file__).resolve().parents[1])))


def fixture():
    head, tail, fill = b'# Heading\n\n~~~\n', b'codebody', b'code text\n'
    count = runner.FIXTURE_SIZE - len(head) - len(tail)
    return head + (fill * (count // len(fill) + 1))[:count] + tail


def route():
    return {'id': 4, 'gen': 2, 'rev': 0, 'pending': 0, 'phase': 4,
            'length': 1000000, 'feed': 1000000, 'bulkCalls': 1, 'metric_valid': 1,
            'feedStepCount': 1, 'feedStepUs': 1, 'publishStepCount': 1, 'publishStepUs': 1,
            'lifecycleStepCount': 1, 'lifecycleStepUs': 0, 'visibilityStepCount': 0, 'visibilityStepUs': 0,
            'stepErrors': 0, 'stepMetricValid': 1, 'entry_yields': 0, 'post_yields': 0}


def profile_record():
    result = {'schema': 1, 'record': 'markdown_phase_profile', 'diagnostic_only': True,
              'product_acceptance': 'separate_not_claimed', 'timing_kind': 'nested_qpc_wall',
              'cpu_kind': 'outer_timer_thread_only', 'cpu_bounds': 'slightly_enclose_qpc_root',
              'sampling': False, 'whole_process_hotspots': False, 'valid': True,
              'raw_counts_trusted': True, 'failure_code': 0, 'foreign_thread_invalid': 0,
              'started': 1, 'completion_requested': 1, 'complete': 1, 'closed': 1, 'depth': 0,
              'qpc_frequency': 1000000, 'root_count': 2, 'no_step_root_count': 1,
              'step_count': 1, 'outermost_root_ticks': 80, 'root_user_100ns': 100,
              'root_kernel_100ns': 20, 'inter_root_gap_ticks': 20, 'inter_root_gap_max_ticks': 20,
              'raw_native_other_entries': 1, 'raw_native_bulk_entries': 1,
              'progress': {'identity': 4, 'generation': 2, 'revision': 0, 'feed': 1000000, 'length': 1000000,
                           'range_count': 0, 'range_index': 0, 'range_offset': 0, 'eof': 1, 'pending': 0},
              'hot_names': ['v_index', 'env_get', 'heap_new', 'v_call'],
              'hot_totals': [8, 16, 24, 32],
              'phases': [{'name': name, 'entries': 2, 'inclusive_ticks': 80 if index == 0 else 10,
                          'exclusive_ticks': 10, 'hot': [1, 2, 3, 4]}
                         for index, name in enumerate(runner.PHASES)]}
    return result


def lifecycle(profile=False):
    markers = ['[launcher] Starting Ru program.', '[startup] menu installed',
               '[startup] initial document ready', '[startup] main window shown',
               '[operation] open started', '[operation] open completed',
               '[launcher] Ru program returned with status 0.']
    if profile:
        markers.append(runner.PREFIX + json.dumps(profile_record()))
    return '\n'.join(markers) + '\n'


class Clock:
    def __init__(self):
        self.value = 0.0
    def __call__(self):
        return self.value
    def sleep(self, seconds):
        self.value += seconds


class Process:
    def __init__(self, clock, pid=125, exit_delay=0, unkillable=False, crash=False):
        self.clock, self.pid = clock, pid
        self.returncode = 7 if crash else None
        self.exit_at, self.exit_delay = None, exit_delay
        self.kills = 0
        self.unkillable = unkillable
        self._handle = object()
    def poll(self):
        if self.exit_at is not None and self.clock() >= self.exit_at:
            self.returncode = 0
        return self.returncode
    def close(self):
        self.exit_at = self.clock() + self.exit_delay
    def kill(self):
        self.kills += 1
        if not self.unkillable:
            self.returncode = -9


class Guard:
    def __init__(self, process, deadline, logs):
        self.process, self.deadline, self.logs = process, deadline, logs
        self.killed, self.error = False, None
    def kill(self):
        if self.process.poll() is None:
            self.killed = True
            self.process.kill()
    def stop(self):
        pass


class API:
    def __init__(self, process, deadline, *, discovery_at=0, per_message=0, wrong_owner=False, dirty=False):
        self.process, self.deadline = process, deadline
        self.discovery_at, self.per_message = discovery_at, per_message
        self.wrong_owner, self.dirty = wrong_owner, dirty
        self.messages = []
    def no_dialog(self, pid):
        if self.deadline.clock() < self.discovery_at:
            return []
        return [(1, runner.MAIN_CLASS, True)]
    def verify_owned_handles(self, pid, *handles):
        if self.wrong_owner or pid != self.process.pid or any(x not in (1, 2, 3) for x in handles):
            runner.fail('wrong_hwnd_owner')
    def responsive(self, hwnd):
        self.scalar(hwnd, 0)
    def text(self, hwnd):
        self.scalar(hwnd, 0x000D)
        return 'unclosed-fence.md · ru_notepad'
    def editor(self, hwnd):
        return 2
    def control(self, hwnd, number):
        return 3
    def markdown_status(self, hwnd):
        self.scalar(hwnd, 0x000D)
        return 'Markdown complete'
    def scalar(self, hwnd, msg, wparam=0, lparam=0):
        self.verify_owned_handles(self.process.pid, hwnd)
        timeout = self.deadline.message_timeout_ms()
        self.messages.append((msg, timeout))
        self.deadline.clock.sleep(min(self.per_message, timeout / 1000))
        self.deadline.remaining()
        if self.per_message > timeout / 1000:
            runner.fail('bounded_gui_message_failed')
        return {2006: 1000000, 2159: int(self.dirty), 2028: 1000000, 4002: 98,
                2223: 0x2000 if wparam == 0 else 0, 2010: 6 if wparam == 0 else 21 if wparam >= 999992 else 0}.get(msg, 0)
    def close(self, hwnd):
        self.deadline.remaining()
        self.process.close()


class Controls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.directory = self.base / 'owned'
        self.directory.mkdir()
        for name in runner.RUNTIME_NAMES:
            (self.directory / name).write_bytes(b'fixture-runtime')
        self.source = self.base / 'unclosed-fence.md'
        self.source.write_bytes(fixture())
        self.styles = [{'offset': 0, 'length': 1, 'style': 6}, {'offset': 2, 'length': 7, 'style': 0},
                       {'offset': 999992, 'length': 8, 'style': 21}]
        self.folds = [{'line': 0, 'header': True}, {'line': 2, 'header': False}]
        self.ci = types.SimpleNamespace(parse_markdown_diagnostic=lambda status: route(),
                                        markdown_status_complete=lambda status: True,
                                        gui_markdown_fixture=lambda kind: (fixture(), self.styles, self.folds))
    def tearDown(self):
        self.temp.cleanup()
    def log_name(self, pid=125, suffix='00'):
        return f'ru_notepad-{pid:08x}-0123456789abcdef-{suffix}.log'
    def run_fake(self, variant='release', *, discovery_at=0, per_message=0, exit_delay=0,
                 wrong_owner=False, dirty=False, log=True, bad_pid=False, crash=False,
                 overflow=False, duplicate=False, unkillable=False, spawn_delay=0):
        clock = Clock()
        process = Process(clock, exit_delay=exit_delay, crash=crash, unkillable=unkillable)
        calls = []
        apis = []
        def spawn(command, **kwargs):
            calls.append((command, kwargs))
            clock.sleep(spawn_delay)
            if log:
                (self.directory / self.log_name(999 if bad_pid else process.pid)).write_text(
                    lifecycle(variant == 'profile') + ('x' * runner.LIMIT if overflow else ''))
            if duplicate:
                (self.directory / self.log_name(process.pid, '01')).write_text(lifecycle())
            return process
        def api_factory(ci, owned, deadline):
            api = API(owned, deadline, discovery_at=discovery_at, per_message=per_message,
                      wrong_owner=wrong_owner, dirty=dirty)
            apis.append(api)
            return api
        result = runner.run_owned(variant, self.directory, self.source, self.ci, self.styles, self.folds,
                                  spawn=spawn, api_factory=api_factory,
                                  cpu_query=lambda owned: {'user_100ns': 300, 'kernel_100ns': 40,
                                                           'scope': 'whole_owned_process_lifetime',
                                                           'source': 'retained_popen_handle'},
                                  clock=clock, sleeper=clock.sleep, guard_factory=Guard)
        return result, process, clock, calls, apis

    def test_fixture_matches_actual_helper(self):
        runner.verify_fixture(fixture())
        if (SOURCE / 'tools/windows_ci.py').is_file():
            data, _, _ = runner.load_ci(SOURCE).gui_markdown_fixture('unclosed-fence')
            self.assertEqual(data, fixture())
        self.assertEqual(fixture().count(b'\n') + 1, 100001)

    def test_exact_release_and_profile_run(self):
        release, proc, clock, calls, apis = self.run_fake()
        self.assertTrue(release['passed'], release)
        self.assertEqual(len(calls), 1)
        self.assertEqual(proc.kills, 0)
        self.assertEqual(calls[0][0], [str(self.directory / 'ru_notepad.exe'), '--markdown-phase-diagnostics', str(self.source)])
        self.assertEqual(calls[0][1]['cwd'], self.directory)
        self.assertEqual(calls[0][1]['creationflags'], 8)
        self.assertEqual(release['process_cpu']['user_100ns'], 300)
        self.assertNotIn('phase_profile', release)
        self.assertFalse(set(msg for msg, _ in apis[0].messages) & {2176, 2177, 2178, 4003})
        (self.directory / self.log_name()).unlink()
        profile, proc, *_ = self.run_fake('profile')
        self.assertTrue(profile['passed'], profile)
        self.assertEqual(profile['phase_profile']['root_user_100ns'], 100)

    def test_absolute_deadline_includes_discovery(self):
        result, proc, clock, *_ = self.run_fake(discovery_at=121)
        self.assertFalse(result['passed'])
        self.assertEqual(result['failure'], 'hard_deadline')
        self.assertLessEqual(clock(), 120)
        self.assertEqual(proc.kills, 1)

    def test_absolute_deadline_includes_popen_latency(self):
        result, proc, clock, *_ = self.run_fake(spawn_delay=120)
        self.assertEqual(result['failure'], 'hard_deadline')
        self.assertEqual(proc.kills, 1)

    def test_no_new_deadline_for_probe_or_shutdown(self):
        result, proc, clock, _, apis = self.run_fake(discovery_at=119.8, per_message=0.2)
        self.assertFalse(result['passed'])
        self.assertLessEqual(clock(), 120)
        self.assertTrue(any(timeout < 5000 for _, timeout in apis[0].messages))
        self.assertEqual(proc.kills, 1)
        (self.directory / self.log_name()).unlink()
        result, proc, clock, *_ = self.run_fake(exit_delay=130)
        self.assertFalse(result['passed'])
        self.assertEqual(result['failure'], 'hard_deadline')
        self.assertLessEqual(clock(), 120)
        self.assertEqual(proc.kills, 1)

    def test_cleanup_unconfirmed_no_pid_reopen_or_second_grace(self):
        result, proc, clock, calls, _ = self.run_fake(discovery_at=121, unkillable=True)
        self.assertTrue(result['cleanup_unconfirmed'])
        self.assertTrue(result['cleanup_killed'])
        self.assertEqual(proc.kills, 1)
        self.assertEqual(len(calls), 1)
        self.assertLessEqual(clock(), 120)

    def test_wrong_hwnd_rejected(self):
        result, proc, *_ = self.run_fake(wrong_owner=True)
        self.assertEqual(result['failure'], 'wrong_hwnd_owner')
        self.assertEqual(proc.kills, 1)

    def test_wrong_pid_log_rejected(self):
        result, proc, *_ = self.run_fake(bad_pid=True)
        self.assertEqual(result['failure'], 'unexpected_owned_directory_entry')
        self.assertEqual(proc.kills, 1)

    def test_missing_log_no_fallback(self):
        other = self.base / 'ru_notepad-0000007d-0123456789abcdef-00.log'
        other.write_text(lifecycle())
        result, proc, *_ = self.run_fake(log=False)
        self.assertEqual(result['failure'], 'missing_owned_launcher_log')
        self.assertEqual(other.read_text(), lifecycle())

    def test_duplicate_launcher_log_rejected(self):
        result, proc, *_ = self.run_fake(duplicate=True)
        self.assertIn(result['failure'], ('duplicate_launcher_log', 'duplicate_or_extra_owned_log'))

    def test_crash_rejected(self):
        result, proc, *_ = self.run_fake(crash=True)
        self.assertEqual(result['failure'], 'premature_gui_exit')
        self.assertFalse(result['passed'])

    def test_dirty_document_rejected(self):
        result, proc, *_ = self.run_fake(dirty=True)
        self.assertEqual(result['failure'], 'document_dirty')

    def test_overflow_failed_and_owned_log_capped(self):
        result, proc, *_ = self.run_fake(overflow=True)
        self.assertFalse(result['passed'])
        self.assertTrue(result['output_overflow'])
        self.assertTrue(result['retained_log_capped'])
        self.assertEqual((self.directory / self.log_name()).stat().st_size, runner.LIMIT)
        self.assertEqual(proc.kills, 1)

    def test_overflow_no_truncate_when_exit_unconfirmed(self):
        result, proc, *_ = self.run_fake(overflow=True, unkillable=True)
        self.assertTrue(result['retained_output_unconfirmed'])
        self.assertTrue(result['cleanup_unconfirmed'])
        self.assertGreater((self.directory / self.log_name()).stat().st_size, runner.LIMIT)

    def test_fixture_mismatch_prevents_launch(self):
        self.source.write_bytes(b'bad')
        result, proc, clock, calls, _ = self.run_fake()
        self.assertEqual(result['failure'], 'fixture_identity')
        self.assertEqual(calls, [])
        self.assertEqual(proc.kills, 0)

    def test_extra_runtime_file_prevents_launch(self):
        (self.directory / 'old.log').write_text('stale')
        result, proc, clock, calls, _ = self.run_fake()
        self.assertEqual(result['failure'], 'runtime_inventory')
        self.assertEqual(calls, [])

    def test_symlink_and_ancestor_link_rejected(self):
        target = self.base / 'actual'
        target.write_bytes(b'never truncate')
        link = self.directory / self.log_name()
        try:
            link.symlink_to(target)
        except OSError:
            self.skipTest('symlink creation unsupported')
        with self.assertRaisesRegex(runner.StudyError, 'unsafe_link_or_reparse'):
            runner.OwnedLog(self.directory, 125).read()
        link.unlink()
        ancestor = self.base / 'linked'
        ancestor.symlink_to(self.directory, target_is_directory=True)
        with self.assertRaisesRegex(runner.StudyError, 'unsafe_link_or_reparse'):
            runner.checked_path(ancestor / 'ru_notepad.exe')
        self.assertEqual(target.read_bytes(), b'never truncate')

    def test_reparse_attribute_rejected_portably(self):
        original = Path.lstat
        def mocked(path):
            value = original(path)
            if path == self.source:
                return types.SimpleNamespace(st_mode=value.st_mode, st_file_attributes=0x400)
            return value
        with patch.object(Path, 'lstat', mocked):
            with self.assertRaisesRegex(runner.StudyError, 'unsafe_link_or_reparse'):
                runner.checked_path(self.source)

    def test_hardlink_rejected(self):
        other = self.base / 'hardlink'
        os.link(self.source, other)
        with self.assertRaisesRegex(runner.StudyError, 'single_link'):
            runner.bounded_read(self.source)

    def test_log_replacement_rejected(self):
        path = self.directory / self.log_name()
        path.write_text(lifecycle())
        log = runner.OwnedLog(self.directory, 125)
        log.inspect()
        moved = self.base / 'old-owned-log'
        path.rename(moved)
        path.write_text('replacement')
        with self.assertRaisesRegex(runner.StudyError, 'identity_changed'):
            log.read()

    def test_phase_schema_counts_partition_and_claims(self):
        good = profile_record()
        runner.validate_phase_record(good, route())
        changes = [('valid', False), ('sampling', True), ('whole_process_hotspots', True),
                   ('product_acceptance', 'passed_30s'), ('depth', 1), ('complete', 0),
                   ('failure_code', 1), ('root_count', True), ('root_count', 0),
                   ('raw_native_bulk_entries', 2), ('unexpected', 1)]
        for key, value in changes:
            with self.subTest(key=key):
                bad = copy.deepcopy(good)
                bad[key] = value
                with self.assertRaises(runner.StudyError):
                    runner.validate_phase_record(bad, route())
        for key, value in [('identity', 5), ('generation', 3), ('revision', 1), ('eof', 0), ('pending', 1), ('feed', 999999), ('range_count', 1)]:
            with self.subTest(progress=key):
                bad = copy.deepcopy(good)
                bad['progress'][key] = value
                with self.assertRaisesRegex(runner.StudyError, 'progress_route_disagreement'):
                    runner.validate_phase_record(bad, route())
        bad = copy.deepcopy(good)
        bad['phases'][3]['exclusive_ticks'] = 9
        with self.assertRaisesRegex(runner.StudyError, 'exclusive_partition'):
            runner.validate_phase_record(bad, route())
        bad = copy.deepcopy(good)
        bad['hot_totals'][2] += 1
        with self.assertRaisesRegex(runner.StudyError, 'hot_partition'):
            runner.validate_phase_record(bad, route())

    def test_missing_duplicate_or_malformed_profile_json(self):
        for data in [lifecycle(), lifecycle(True) + runner.PREFIX + '{}\n',
                     lifecycle() + runner.PREFIX + '{"schema":1,"schema":1}\n',
                     lifecycle() + runner.PREFIX + '{"x":NaN}\n']:
            with self.assertRaises(runner.StudyError):
                runner.validate_launcher(data, True)
        with self.assertRaisesRegex(runner.StudyError, 'phase_record_count'):
            runner.validate_launcher(lifecycle(True), False)

    def test_json_output_cap(self):
        with self.assertRaisesRegex(runner.StudyError, 'output_overflow'):
            runner.json_bytes({'value': 'x' * runner.LIMIT})

    def test_clock_regression_and_cap(self):
        clock = Clock()
        deadline = runner.Deadline(0, clock)
        self.assertEqual(deadline.message_timeout_ms(), 5000)
        clock.value = 119.9995
        with self.assertRaisesRegex(runner.StudyError, 'hard_deadline'):
            deadline.message_timeout_ms()
        clock.value = -1
        with self.assertRaisesRegex(runner.StudyError, 'clock_invalid'):
            deadline.remaining()

    def test_retained_log_not_truncated_after_replacement(self):
        path = self.directory / self.log_name()
        path.write_text('x' * (runner.LIMIT + 1))
        log = runner.OwnedLog(self.directory, 125)
        with self.assertRaises(runner.StudyError):
            log.inspect()
        path.rename(self.base / 'old')
        path.write_text('untouched replacement')
        process = Process(Clock(), crash=True)
        with self.assertRaisesRegex(runner.StudyError, 'identity_changed'):
            log.cap_after_exit(process)
        self.assertEqual(path.read_text(), 'untouched replacement')

    def test_final_log_route_uses_last_and_checks_identity(self):
        final = dict(route(), seq=2, bulkLines=3, fallbackBatches=0, directCalls=0, directLines=0)
        earlier = dict(final, seq=1, pending=1, phase=1)
        ci = types.SimpleNamespace(parse_markdown_diagnostic=lambda line: json.loads(line.split('[MDP ', 1)[1]))
        line = lambda value: ' [MDP ' + json.dumps(value) + '\n'
        self.assertEqual(runner.validate_log_route(ci, line(earlier) + line(final), final), 2)
        for key in ('feedStepCount','publishStepUs','stepErrors','stepMetricValid','entry_yields','post_yields'):
            with self.subTest(key=key),self.assertRaisesRegex(runner.StudyError,'final_route_disagreement'):
                runner.validate_log_route(ci,line(dict(final,**{key:final[key]+1})),final)
        with self.assertRaisesRegex(runner.StudyError, 'sequence_regressed'):
            runner.validate_log_route(ci, line(final) + line(earlier), final)
        with self.assertRaisesRegex(runner.StudyError, 'identity_changed'):
            runner.validate_log_route(ci, line(dict(final, id=5)), final)
        with self.assertRaisesRegex(runner.StudyError, 'final_route_disagreement'):
            runner.validate_log_route(ci, line(earlier), final)

    def test_no_pid_or_handle_termination_fallback_exists(self):
        source = Path(runner.__file__).read_text()
        self.assertNotIn('taskkill.exe', source)
        self.assertNotIn('OpenProcess(', source)
        self.assertNotIn('os.kill(', source)
        self.assertNotIn('process.wait(', source)

    def make_manifest(self):
        root = self.base / 'source'
        root.mkdir()
        sources = {}
        for name in runner.REQUIRED_SOURCES:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(('source:' + name).encode())
            sources[name] = runner.digest(path)
        release, profile = self.base / 'release-input', self.base / 'profile-input'
        runtime = {}
        for variant, path in [('release', release), ('profile', profile)]:
            path.mkdir()
            runtime[variant] = {}
            for name in runner.RUNTIME_NAMES:
                file = path / name
                file.write_text(name + (variant if name.endswith('.exe') else 'identical'))
                runtime[variant][name] = runner.digest(file)
        artifacts = {}
        for name in ['release_tu', 'profile_tu', 'source_map']:
            path = self.base / (name + '.data')
            path.write_text(name)
            artifacts[name] = {'path': path.name, 'sha256': runner.digest(path)}
        receipt = self.base / 'manifest.json'
        value = {'schema': 1, 'compiler_commit': 'a' * 40, 'source_sha256': sources,
                 'runtime_sha256': runtime, 'artifacts': artifacts}
        receipt.write_bytes(runner.json_bytes(value))
        return receipt, root, release, profile, value

    def test_manifest_hash_source_inventory_and_runtime(self):
        receipt, source, release, profile, value = self.make_manifest()
        runner.verify_manifest(receipt, source, release, profile)
        (source / 'src/main.ru').write_text('stale')
        with self.assertRaisesRegex(runner.StudyError, 'hash_mismatch'):
            runner.verify_manifest(receipt, source, release, profile)

    def test_manifest_relative_path_escape(self):
        receipt, source, release, profile, value = self.make_manifest()
        value['source_sha256']['../outside'] = 'a' * 64
        receipt.write_bytes(runner.json_bytes(value))
        with self.assertRaisesRegex(runner.StudyError, 'unsafe_relative_path'):
            runner.verify_manifest(receipt, source, release, profile)

    def test_serial_pair_and_no_profile_after_release_failure(self):
        receipt, source, release, profile, _ = self.make_manifest()
        calls = []
        def run(variant, directory, fixture_path, ci, styles, folds, **kwargs):
            calls.append(variant)
            self.assertEqual(set(x.name for x in directory.iterdir()), set(runner.RUNTIME_NAMES))
            return {'variant': variant, 'passed': True, 'scenario_wall_ms': 10 if variant == 'release' else 20}
        output = self.base / 'study'
        summary = runner.run_pair(receipt, source, release, profile, output, ci=self.ci, run=run)
        self.assertTrue(summary['passed'])
        self.assertEqual(calls, ['release', 'profile'])
        self.assertEqual(summary['observed_wall_ratio'], 2)
        self.assertLessEqual(sum((output / name).stat().st_size for name in ['receipt.json', 'markdown-owned-profile.json']), runner.TOTAL_LIMIT)
        with self.assertRaises(FileExistsError):
            runner.run_pair(receipt, source, release, profile, output, ci=self.ci, run=run)
        calls.clear()
        def fail_release(variant, *args, **kwargs):
            calls.append(variant)
            return {'variant': variant, 'passed': False}
        summary = runner.run_pair(receipt, source, release, profile, self.base / 'failed', ci=self.ci, run=fail_release)
        self.assertEqual(calls, ['release'])
        self.assertFalse(summary['passed'])

    def test_failure_after_reservation_emits_summary(self):
        receipt, source, release, profile, _ = self.make_manifest()
        bad_ci = types.SimpleNamespace(gui_markdown_fixture=lambda kind: (b'bad', [], []))
        output = self.base / 'failed-setup'
        result = runner.run_pair(receipt, source, release, profile, output, ci=bad_ci)
        self.assertFalse(result['passed'])
        self.assertEqual(result['failure'], 'fixture_identity')
        self.assertEqual(result['runs'], [])
        written = json.loads((output / 'markdown-owned-profile.json').read_text())
        self.assertEqual(written['failure'], 'fixture_identity')
        self.assertNotIn(str(self.base), json.dumps(written))

    def test_source_mismatch_prevents_entire_pair(self):
        receipt, source, release, profile, _ = self.make_manifest()
        (source / 'src/main.ru').write_text('changed')
        calls = []
        with self.assertRaisesRegex(runner.StudyError, 'hash_mismatch'):
            runner.run_pair(receipt, source, release, profile, self.base / 'none', ci=self.ci,
                            run=lambda *args: calls.append(args))
        self.assertEqual(calls, [])
        self.assertFalse((self.base / 'none').exists())

    def test_non_windows_cli_never_launches(self):
        if os.name == 'nt':
            self.skipTest('non-Windows gate')
        with patch.object(runner, 'run_pair', side_effect=AssertionError('must not launch')):
            self.assertEqual(runner.main(['--source-root', '.', '--release-dir', '.', '--profile-dir', '.',
                                          '--receipt', 'absent', '--output', 'absent']), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
