#!/usr/bin/env python3
"""Portable hostile-output/publication controls, never native acceptance."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('window_size_diagnostic', Path(__file__).with_name('run_window_size_diagnostic.py'))
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def synthetic():
    system = {'screen': [1024, 768], 'virtual_screen': [0, 0, 1024, 768],
              'work': [0, 0, 1024, 728], 'max_track': [1040, 784],
              'min_track': [112, 27], 'maximized': [1040, 744],
              'dpi_aware': 1, 'device_dpi': [96, 96], 'pointer_bits': 64,
              'compiled_style': runner.STYLE, 'override_max_track': [4096, 4096]}
    modes = []
    for policy in range(2):
        before = [0, 0, 1040, 744, -8, -8, 112, 27, 1040, 784]
        after = before.copy()
        after[6:8] = [640, 400]
        if policy:
            after[8:10] = [4096, 4096]
        events = [{'stage': n, 'before': before.copy(), 'after': after.copy()} for n in (0, 2, 3, 4, 5, 6, 7)]
        states = []
        for stage in range(8):
            target = 0 if stage < 2 else (640, 900, 1600)[(stage - 2) // 2]
            if stage == 0:
                request = [1120, 760]
            elif stage == 1:
                request = [0, 0]
            else:
                old = states[-1]
                request = [target + old['outer'][2] - old['outer'][0] - old['client'][2],
                           720 + old['outer'][3] - old['outer'][1] - old['client'][3]]
            width = min(1120 if stage < 2 else request[0], 1040 if policy == 0 else 4096)
            height = 760 if stage < 2 else request[1]
            x, y = (48, 48) if stage < 2 else (40, 40)
            top = 31 if stage == 0 else 51
            states.append({'stage': stage, 'target_width': target,
                           'target_height': 0 if stage < 2 else 720,
                           'iteration': 0 if stage < 2 else (stage - 2) % 2 + 1,
                           'requested_outer': request, 'outer': [x, y, x + width, y + height],
                           'client': [0, 0, width - 16, height - top - 8],
                           'client_screen': [x + 8, y + top], 'style': runner.STYLE,
                           'exstyle': 256, 'visible': 0, 'dpi': 96,
                           'menu_count': 0 if stage == 0 else 9,
                           'callback_count': sum(e['stage'] <= stage for e in events),
                           'monitor': [0, 0, 1024, 768], 'work': [0, 0, 1024, 728]})
        modes.append({'policy': policy, 'states': states, 'minmax': events})
    return {'schema': 1, 'system': system, 'modes': modes}


def encoded(data):
    return json.dumps(data, separators=(',', ':')).encode('ascii')


def report():
    return runner.make_report(synthetic(), {k: 'a' * 64 for k in runner.SOURCE_PATHS}, 'b' * 64)


class SchemaTests(unittest.TestCase):
    def reject(self, data):
        with self.assertRaises((ValueError, TypeError, UnicodeError)):
            runner.validate_measurements(encoded(data), b'')

    def test_clamped_result_is_evidence_not_failure(self):
        data = runner.validate_measurements(encoded(synthetic()), b'')
        self.assertEqual(data['modes'][0]['states'][7]['client'][2], 1024)
        self.assertEqual(data['modes'][1]['states'][7]['client'][2], 1600)

    def test_unclamped_both_is_also_valid(self):
        data = synthetic()
        data['modes'][0]['states'] = copy.deepcopy(data['modes'][1]['states'])
        runner.validate_measurements(encoded(data), b'')

    def test_os_added_style_bits_are_retained(self):
        data = synthetic()
        for mode in data['modes']:
            for state in mode['states']:
                state['style'] |= 0x04000000
        result = runner.validate_measurements(encoded(data), b'')
        self.assertEqual(result['modes'][0]['states'][7]['style'], runner.STYLE | 0x04000000)

    def test_reject_missing_extra_or_private_fields(self):
        for mutate in (
            lambda d: d.update(path='private'),
            lambda d: d['system'].pop('work'),
            lambda d: d['modes'][0]['states'][0].update(title='private'),
            lambda d: d['modes'][0]['minmax'][0].update(handle=1234),
        ):
            with self.subTest(mutate=mutate):
                data = synthetic(); mutate(data); self.reject(data)

    def test_reject_duplicate_keys_non_ascii_trailing_output_stderr(self):
        good = encoded(synthetic())
        for bad in (b'{"schema":1,' + good[1:], good + b'\nnoise', b'\xff', good + b'x' * 65536, b''):
            with self.subTest(bad=bad[:30]):
                with self.assertRaises((ValueError, UnicodeError)):
                    runner.validate_measurements(bad, b'')
        with self.assertRaises(ValueError):
            runner.validate_measurements(good, b'private diagnostic')

    def test_reject_wrong_integer_types_and_ranges(self):
        for value in (True, 1.0, None, '1', float('nan'), float('inf'), -1, 1000001):
            with self.subTest(value=value):
                data = synthetic(); data['schema'] = value; self.reject(data)
        data = synthetic(); data['system']['work'][0] = -1000001; self.reject(data)

    def test_reject_missing_reordered_or_extra_states_and_modes(self):
        for mutate in (
            lambda d: d['modes'].reverse(),
            lambda d: d['modes'].append(d['modes'][0]),
            lambda d: d['modes'][0]['states'].pop(),
            lambda d: d['modes'][0]['states'].reverse(),
            lambda d: d['modes'][0]['states'].append(d['modes'][0]['states'][0]),
        ):
            data = synthetic(); mutate(data); self.reject(data)

    def test_reject_non_matching_native_policy_or_geometry_contract(self):
        mutations = (
            lambda d: d['system'].update(dpi_aware=0),
            lambda d: d['system'].update(compiled_style=0),
            lambda d: d['modes'][0]['states'][2].update(style=0),
            lambda d: d['modes'][0]['states'][2].update(style=runner.STYLE | 0x10000000),
            lambda d: d['modes'][0]['states'][2].update(visible=1),
            lambda d: d['modes'][0]['states'][2].update(target_width=639),
            lambda d: d['modes'][0]['states'][2].update(target_height=400),
            lambda d: d['modes'][0]['states'][2].update(requested_outer=[640, 720]),
            lambda d: d['modes'][0]['states'][2].update(menu_count=8),
            lambda d: d['modes'][0]['states'][2].update(callback_count=63),
            lambda d: d['modes'][0]['minmax'][0]['after'].__setitem__(8, 4096),
            lambda d: d['modes'][1]['minmax'][0]['after'].__setitem__(8, 1040),
            lambda d: d['modes'][0]['minmax'][0]['after'].__setitem__(2, 999),
            lambda d: d['modes'][0]['minmax'].clear(),
            lambda d: d['modes'][0].update(minmax=d['modes'][0]['minmax'] * 10),
        )
        for mutate in mutations:
            data = synthetic(); mutate(data); self.reject(data)

    def test_hash_bindings_are_fixed_and_complete(self):
        valid = {key: 'a' * 64 for key in runner.SOURCE_PATHS}
        for sources, digest in (({}, 'a' * 64), (dict(valid, path='secret'), 'b' * 64),
                                (valid, 'x' * 64), (valid, 'a' * 63), (valid, True)):
            with self.assertRaises(ValueError):
                runner.make_report(synthetic(), sources, digest)


class PublicationTests(unittest.TestCase):
    def test_only_validated_public_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); private = root / 'private'; private.mkdir()
            public = root / 'public'
            runner.publish_report(private, public, report())
            self.assertEqual([p.name for p in public.iterdir()], ['measurements.json'])
            self.assertEqual(json.loads((public / 'measurements.json').read_text()), report())
            with self.assertRaises(FileExistsError):
                runner.publish_report(private, public, report())

    def test_existing_public_directory_or_symlink_is_never_reused(self):
        for link in (False, True):
            with self.subTest(link=link), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); private = root / 'private'; private.mkdir()
                public = root / 'public'; other = root / 'other'; other.mkdir()
                if link:
                    try: public.symlink_to(other, target_is_directory=True)
                    except OSError: continue  # Windows may lack symlink privilege.
                else:
                    public.mkdir()
                sentinel = public / 'keep'; sentinel.write_bytes(b'unchanged')
                with self.assertRaises(FileExistsError):
                    runner.publish_report(private, public, report())
                self.assertEqual(sentinel.read_bytes(), b'unchanged')
                self.assertFalse((public / 'measurements.json').exists())

    def test_atomic_link_refuses_destination_race(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); private = root / 'private'; private.mkdir()
            public = root / 'public'; real_link = runner.os.link
            def race(source, dest):
                dest.write_bytes(b'original')
                real_link(source, dest)
            with patch.object(runner.os, 'link', side_effect=race):
                with self.assertRaises(FileExistsError):
                    runner.publish_report(private, public, report())
            self.assertEqual((public / 'measurements.json').read_bytes(), b'original')

    def test_short_write_flush_or_fsync_failure_has_no_public_directory(self):
        real_open = Path.open
        for failure in ('short_write', 'flush', 'fsync'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); private = root / 'private'; private.mkdir()
                class Writer:
                    def __init__(self, stream): self.stream = stream
                    def __enter__(self): return self
                    def __exit__(self, *args): return self.stream.__exit__(*args)
                    def write(self, value):
                        if failure == 'short_write': return self.stream.write(value[:-1])
                        return self.stream.write(value)
                    def flush(self):
                        if failure == 'flush': raise OSError('injected')
                        return self.stream.flush()
                    def fileno(self): return self.stream.fileno()
                def open_stream(path, mode='r', *args, **kwargs):
                    stream = real_open(path, mode, *args, **kwargs)
                    return Writer(stream) if mode == 'xb' else stream
                with patch.object(Path, 'open', open_stream), patch.object(runner.os, 'fsync', side_effect=OSError('injected') if failure == 'fsync' else None):
                    with self.assertRaises((ValueError, OSError)):
                        runner.publish_report(private, root / 'public', report())
                self.assertFalse((root / 'public').exists())

    def test_link_failure_cannot_publish_final_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); private = root / 'private'; private.mkdir()
            with patch.object(runner.os, 'link', side_effect=OSError('injected')):
                with self.assertRaises(OSError):
                    runner.publish_report(private, root / 'public', report())
            self.assertFalse((root / 'public/measurements.json').exists())

    def test_corrupted_temporary_is_rejected_before_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); private = root / 'private'; private.mkdir()
            with patch.object(runner, 'read_bounded', return_value=b'corrupt'):
                with self.assertRaises(ValueError):
                    runner.publish_report(private, root / 'public', report())
            self.assertFalse((root / 'public').exists())

    def test_final_corruption_is_checked_and_owned_link_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); private = root / 'private'; private.mkdir()
            real_link = runner.os.link
            def corrupt(source, dest):
                real_link(source, dest)
                dest.write_bytes(b'corrupt')
            with patch.object(runner.os, 'link', side_effect=corrupt):
                with self.assertRaises(ValueError):
                    runner.publish_report(private, root / 'public', report())
            self.assertFalse((root / 'public/measurements.json').exists())

    def test_invalid_public_report_produces_no_public_directory(self):
        for mutate in (lambda r: r.update(log='secret'),
                       lambda r: r.update(windows_executed=True),
                       lambda r: r['measurements']['system'].update(user='secret')):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); private = root / 'private'; private.mkdir()
                data = report(); mutate(data)
                with self.assertRaises(ValueError):
                    runner.publish_report(private, root / 'public', data)
                self.assertFalse((root / 'public').exists())


if __name__ == '__main__':
    unittest.main()
