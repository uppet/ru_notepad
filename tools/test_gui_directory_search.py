"""Portable positive/negative receipt controls. Never Windows GUI evidence."""
import inspect
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import gui_directory_search as gui
from test_gui_open_search import layouts as open_layouts

HASHES = dict.fromkeys(gui.ci.portable.RUNTIME_NAMES, 'a' * 64)


def layouts():
    rows = open_layouts()
    for row in rows:
        row['rectangles']['320'] = [0, 150, 600, 190]
        row['rectangles']['327'] = [0, 190, 600, 220]
        row.update(list_client_height=38, details_readonly=True, details_scrollable=True,
                   details_client_height=28, details_font_height=16, details_lines=9,
                   summary_minimum_width=200, navigation_disabled=True)
    return rows


def lifecycle(name):
    return dict(name=name, passed=True, executed=True, cleanup_killed=False, main_hwnd_seen=True,
                close_posted=True, detached_from_console=True, exit_code=0, fixture_binary_sha256=dict(HASHES))


def receipt():
    return dict(lifecycle('main-gui-directory-search'), schema='ru-notepad-directory-search-gui-v1',
                close_running=dict(lifecycle('main-gui-directory-close-running'), running_seen=True, close_seconds=.1),
                fixtures=gui.inventory(), cases=gui.expected_cases(), checks=dict.fromkeys(gui.CHECKS, True),
                engine_gates=list(gui.ENGINE_GATES), disclosures=list(gui.DISCLOSURES),
                query_boundary=dict(scalars=256, utf8_bytes=768, rows=1),
                row_cap=dict(rows=2000, status='limited', reason_visible=True),
                picker=dict(unicode_path=True, owned_modal=True, edit_readback=True, cancelled=True),
                cancellations=[dict(action=a, running_seen=True, stable=True, restart_succeeded=True,
                                    seconds=.1, retire_seconds=.2, draining_seen=False, busy_rejections=0) for a in gui.CANCEL_ACTIONS],
                responses=[dict(action=a, seconds=.1, running_after=True) for a in ('query', 'tab', 'caret')],
                labels=[dict(language=l, menu_verified=True, details_verified=True) for l in gui.LANGUAGES],
                layouts=layouts())


class Contract(unittest.TestCase):
    def reject(self, row):
        with self.assertRaises(ValueError): gui.validate_result(row, HASHES)

    def test_complete_contract_is_not_execution(self):
        self.assertTrue(gui.validate_result(receipt(), HASHES))
        self.assertIn('do not execute Windows', gui.DISCLOSURES[0])

    def test_required_fields(self):
        for key in receipt():
            with self.subTest(key=key):
                row = receipt(); del row[key]; self.reject(row)

    def test_lifecycle_requires_normal_owned_exit(self):
        for target in ('main', 'close_running'):
            for key, value in (('passed', 1), ('executed', False), ('executed', 1), ('cleanup_killed', True),
                               ('cleanup_killed', 0), ('main_hwnd_seen', False), ('close_posted', False),
                               ('detached_from_console', False), ('exit_code', True), ('exit_code', 1),
                               ('error', 'failure'), ('skips', ['anything']), ('fixture_binary_sha256', {}),
                               ('name', 'other')):
                row = receipt(); (row if target == 'main' else row[target])[key] = value; self.reject(row)
            for key in lifecycle('irrelevant'):
                row = receipt(); del (row if target == 'main' else row[target])[key]; self.reject(row)

    def test_close_must_really_interrupt_running_work_within_bound(self):
        for key, value in (('running_seen', False), ('running_seen', 1), ('close_seconds', None),
                           ('close_seconds', True), ('close_seconds', -1), ('close_seconds', float('nan')),
                           ('close_seconds', gui.RETIRE_SECONDS)):
            row = receipt(); row['close_running'][key] = value; self.reject(row)

    def test_full_current_runtime_hash_inventory_required(self):
        for hashes in ({}, {'ru_notepad.exe': 'a' * 64}, dict(HASHES, unexpected='a' * 64),
                       dict(HASHES, **{'ru_notepad.exe': 'A' * 64}), dict(HASHES, **{'RuSyntax.dll': 'z' * 64})):
            row = receipt(); row['fixture_binary_sha256'] = hashes; row['close_running']['fixture_binary_sha256'] = hashes
            with self.assertRaises(ValueError): gui.validate_result(row, hashes)
        row = receipt(); row['fixture_binary_sha256']['RuSyntax.dll'] = 'b' * 64; self.reject(row)
        other = dict.fromkeys(HASHES, 'b' * 64); row = receipt()
        row['fixture_binary_sha256'] = other; row['close_running']['fixture_binary_sha256'] = other
        self.assertTrue(gui.validate_result(row, other))

    def test_inventory_order_and_values(self):
        for field in ('fixtures', 'cases', 'engine_gates', 'disclosures', 'cancellations', 'responses', 'labels', 'layouts'):
            row = receipt(); row[field].reverse(); self.reject(row)
            row = receipt(); row[field].pop(); self.reject(row)
        row = receipt(); row['fixtures'][0]['sha256'] = 'b' * 64; self.reject(row)
        row = receipt(); row['cases'][0]['rows'][0]['column'] += 1; self.reject(row)
        row = receipt(); row['cases'][0]['rows'][0]['path'] = 'same.txt'; self.reject(row)
        row = receipt(); row['cases'][0]['rows'][0]['preview'] += 'x'; self.reject(row)

    def test_every_check_is_explicit_observation_and_never_truthy(self):
        source = inspect.getsource(gui.run)
        self.assertNotIn('dict.fromkeys(CHECKS', source)
        for key in gui.CHECKS:
            self.assertIn("['" + key + "'] = True", source)
            for value in (False, 1, None, 'true'):
                row = receipt(); row['checks'][key] = value; self.reject(row)
            row = receipt(); del row['checks'][key]; self.reject(row)
        row = receipt(); row['checks']['unobserved'] = True; self.reject(row)

    def test_types_not_equality_alone(self):
        for field in ('query_boundary', 'row_cap', 'picker'):
            for key, value in receipt()[field].items():
                row = receipt(); del row[field][key]; self.reject(row)
                if type(value) is bool:
                    row = receipt(); row[field][key] = int(value); self.reject(row)
                elif type(value) is int:
                    row = receipt(); row[field][key] = float(value); self.reject(row)
        row = receipt(); row['cases'][0]['rows'][0]['line'] = True; self.reject(row)
        row = receipt(); row['cases'][0]['files'] = 10.0; self.reject(row)
        row = receipt(); row['cases'][0]['skipped'] = 8.0; self.reject(row)
        row = receipt(); row['fixtures'][0]['bytes'] = float(row['fixtures'][0]['bytes']); self.reject(row)

    def test_cancellations_never_skip_or_claim_unobserved_draining(self):
        for index in range(len(gui.CANCEL_ACTIONS)):
            for key in receipt()['cancellations'][index]:
                row = receipt(); del row['cancellations'][index][key]; self.reject(row)
            for value in (True, -1, 101, 1.0):
                row = receipt(); row['cancellations'][index]['busy_rejections'] = value; self.reject(row)
            for key in ('running_seen', 'stable', 'restart_succeeded', 'draining_seen'):
                row = receipt(); row['cancellations'][index][key] = 1; self.reject(row)
            for key, maximum in (('seconds', gui.RESPONSE_SECONDS), ('retire_seconds', gui.RETIRE_SECONDS)):
                for value in (True, -1, float('nan'), float('inf'), maximum):
                    row = receipt(); row['cancellations'][index][key] = value; self.reject(row)
        # No flaky claim that a millisecond-long retiring state is always seen.
        row = receipt(); row['cancellations'][0]['draining_seen'] = True
        self.assertTrue(gui.validate_result(row, HASHES))
        self.assertIn('native_blocked_io_cancellation_and_retirement', gui.ENGINE_GATES)
        self.assertIn('before observation', gui.DISCLOSURES[2])

    def test_responses_require_real_observation_and_finite_bound(self):
        for index in range(3):
            for key, value in (('running_after', False), ('running_after', 1), ('seconds', True),
                               ('seconds', -1), ('seconds', gui.RESPONSE_SECONDS), ('seconds', float('nan'))):
                row = receipt(); row['responses'][index][key] = value; self.reject(row)
            for key in ('action', 'seconds', 'running_after'):
                row = receipt(); del row['responses'][index][key]; self.reject(row)

    def test_all_languages_require_native_geometry_and_translation(self):
        self.assertEqual(len(receipt()['layouts']), 28)
        for index in range(28):
            for field in ('details_readonly', 'details_scrollable', 'navigation_disabled'):
                for value in (False, 1):
                    row = receipt(); row['layouts'][index][field] = value; self.reject(row)
            for field, value in (('details_client_height', 15), ('details_client_height', 31),
                                 ('details_font_height', 0), ('details_font_height', True),
                                 ('details_lines', 5), ('summary_minimum_width', 601)):
                row = receipt(); row['layouts'][index][field] = value; self.reject(row)
            for rect in ([0, 189, 600, 220], [-1, 190, 600, 220], [0, 190, 2000, 220], [0, 190, 600, 240], [0, 190, 600, 190]):
                row = receipt(); row['layouts'][index]['rectangles']['327'] = rect; self.reject(row)
            row = receipt(); del row['layouts'][index]['rectangles']['327']; self.reject(row)
        for index in range(7):
            for key in ('menu_verified', 'details_verified'):
                row = receipt(); row['labels'][index][key] = 1; self.reject(row)

    def test_fixture_policy_covers_strict_encodings_and_malformed_tail(self):
        data = gui.fixtures()
        self.assertTrue(data['semantic/utf16-le.txt'].startswith(b'\xff\xfe'))
        self.assertTrue(data['semantic/utf16-be.txt'].startswith(b'\xfe\xff'))
        self.assertTrue(data['semantic/utf8-bom.txt'].startswith(b'\xef\xbb\xbf'))
        self.assertEqual(len(data['semantic/excluded/oversize.txt']), gui.MAX_FILE_BYTES + 1)
        self.assertLess(gui.STRESS_BYTES, 1024 * 1024)
        for name, value in data.items():
            if name.startswith('semantic/excluded/'):
                self.assertIn(b'cat' if 'utf16' not in name and 'utf32' not in name else b'c', value)
        self.assertEqual(sum(len(d) for n, d in data.items() if n.startswith('semantic/') and len(d) <= gui.MAX_FILE_BYTES), 1287)
        self.assertEqual([len(c['rows']) for c in gui.expected_cases()], [15, 3, 1, 2, 1, 1, 1, 0])
        first = gui.expected_cases()[0]['rows']
        self.assertTrue(any(r['path'] == 'left/same.txt' for r in first))
        self.assertTrue(any(r['path'] == 'right/same.txt' for r in first))
        self.assertFalse(any(r['path'].startswith('excluded/') for r in first))

    def test_scalar_coordinates_and_crlf_terminators(self):
        self.assertEqual(gui.text_rows('x', '😀cat', 'cat')[0], dict(path='x', line=1, column=2, preview='😀cat'))
        for source, query, line, column in (('x\r\ny', '\r\n', 1, 2), ('x\r\ny', '\n', 1, 3),
                                          ('x\r\ny', 'y', 2, 1), ('x\ry', 'y', 2, 1), ('x\ny', 'y', 2, 1),
                                          ('e\u0301cat', 'cat', 1, 3)):
            row = gui.text_rows('x', source, query)[0]
            self.assertEqual((row['line'], row['column']), (line, column))
        with self.assertRaises(ValueError): gui.text_rows('x', '', '')
        self.assertEqual(gui.text_rows('x', 'ababa', 'aba'), [dict(path='x', line=1, column=1, preview='aba')])
        self.assertEqual(gui.text_rows('x', 'a'*33+'q', 'q')[0]['preview'], '…' + 'a'*32 + 'q')
        self.assertEqual(gui.text_rows('x', '界'*256, '界'*256)[0]['preview'], '界'*64+'…')
        self.assertEqual(gui.escaped('a\t\u202eb'), 'a��b')
        self.assertEqual(gui.detail_escaped('a\t\r\n\u202eb'), 'a␉␍␊�b')

    def test_list_result_parser_rejects_foreign_root_and_missing_coordinates(self):
        with patch.object(gui, 'Path') as path:
            path.return_value.resolve.return_value = 'C:\\fake'
            self.assertEqual(gui.observed_rows(['C:\\fake\\左\\same.txt : 2:3 : 😀cat'], 'unused'),
                             [dict(path='左/same.txt', line=2, column=3, preview='😀cat')])
            for label in ('C:\\else\\same.txt : 2:3 : cat', 'C:\\fake\\same.txt : 0:3 : cat',
                          'C:\\fake\\same.txt : 1:0 : cat', 'no coordinates'):
                with self.assertRaises(RuntimeError): gui.observed_rows([label], 'unused')

    def test_picker_uses_owned_real_modal_controls_and_system_messages_only(self):
        source = inspect.getsource(gui.choose_folder)
        for token in ('_post_command(api, hwnd, START)', 'picker_shape(', 'set_text(api, edit, value)',
                      'api.verify_owned_handles', 'PostMessageW(button, 0xF5', 'root is not None else 2'):
            self.assertIn(token, source)
        for token in ('BFFM_SETSELECTION', 'WriteProcessMemory', 'SendInput', '0x400', 'GetClipboardData'):
            self.assertNotIn(token, source)
        shape = inspect.getsource(gui.picker_shape)
        for token in ('u.GetWindow(dialog, 4) != owner', 'u.IsWindowEnabled(owner)', 'pid.value != process.pid',
                      "c == 'Edit'", "c == 'SysTreeView32'"):
            self.assertIn(token, shape)

    def test_unverified_picker_cannot_receive_text_or_click(self):
        api = SimpleNamespace(user=SimpleNamespace(PostMessageW=Mock(return_value=True),
                                                   IsWindowVisible=Mock(return_value=True)),
                              windows=Mock(return_value=[(200, '#32770', True)]))
        process = SimpleNamespace(pid=77)
        def wait(_api, _process, predicate, *_args, **_kwargs): predicate()
        with patch.object(gui, '_post_command'), patch.object(gui, '_wait', side_effect=wait), \
                patch.object(gui, 'picker_shape', side_effect=RuntimeError('unowned')), patch.object(gui, 'set_text') as text:
            with self.assertRaisesRegex(RuntimeError, 'unowned'): gui.choose_folder(api, process, 100, Path('fake'))
            text.assert_not_called(); api.user.PostMessageW.assert_not_called()

    def picker_api(self):
        state = {'visible': False, 'clicked': []}
        def post(_api, _hwnd, _command): state['visible'] = True
        def click(handle, message, wparam, lparam):
            state['clicked'].append((handle, message)); state['visible'] = False; return True
        api = SimpleNamespace(user=SimpleNamespace(PostMessageW=Mock(side_effect=click),
              IsWindowVisible=Mock(side_effect=lambda _: state['visible']), IsWindowEnabled=Mock(return_value=True)),
              windows=Mock(side_effect=lambda _: [(200, '#32770', True)] if state['visible'] else []),
              scalar=Mock(), verify_owned_handles=Mock())
        def wait(_api, _process, predicate, *_args, **_kwargs):
            if not predicate(): raise RuntimeError('Mock expected condition did not occur')
        return api, state, post, wait

    def test_picker_unicode_readback_then_owned_ok_and_cancel(self):
        for root, button in ((Path('目录😀'), 211), (None, 212)):
            api, state, post, wait = self.picker_api()
            with patch.object(gui, '_post_command', side_effect=post), patch.object(gui, '_wait', side_effect=wait), \
                    patch.object(gui.ci, 'wait_gui', side_effect=wait), patch.object(gui, 'picker_shape', return_value=(201, {1:211, 2:212})), \
                    patch.object(gui, 'set_text') as text:
                self.assertEqual(gui.choose_folder(api, SimpleNamespace(pid=77), 100, root), 0)
                if root is None:
                    text.assert_not_called(); api.scalar.assert_not_called()
                else:
                    text.assert_called_once_with(api, 201, str(root.resolve()))
                    api.scalar.assert_called_once_with(200, 0x28, 201, 1)
            self.assertEqual(state['clicked'], [(button, 0xF5)])
            api.verify_owned_handles.assert_called_with(77, 100, 200, 201, button)

    def test_retiring_retry_only_dismisses_exact_owned_busy_information(self):
        api, state, post, wait = self.picker_api()
        with patch.object(gui, '_post_command', side_effect=post) as command, patch.object(gui, '_wait', side_effect=wait), \
                patch.object(gui.ci, 'wait_gui', side_effect=wait), patch.object(gui, 'set_text'), \
                patch.object(gui, 'picker_shape', side_effect=[RuntimeError('information'), (201, {1:211, 2:212})]), \
                patch.object(gui, '_information_dialog', return_value={'verified': 'shape'}), \
                patch.object(gui, '_information_shape', return_value=399) as shape, patch.object(gui.time, 'sleep'):
            self.assertEqual(gui.choose_folder(api, SimpleNamespace(pid=77), 100, Path('folder'), busy_body='exact busy body'), 1)
            shape.assert_called_once_with({'verified': 'shape'}, 100, {'exact busy body'})
            self.assertEqual(command.call_count, 2)
        self.assertEqual(state['clicked'], [(399, 0xF5), (211, 0xF5)])
        api, state, post, wait = self.picker_api()
        with patch.object(gui, '_post_command', side_effect=post), patch.object(gui, '_wait', side_effect=wait), \
                patch.object(gui, 'picker_shape', side_effect=RuntimeError('information')), \
                patch.object(gui, '_information_dialog', return_value={}), patch.object(gui, '_information_shape', return_value=None):
            with self.assertRaisesRegex(RuntimeError, 'Unexpected dialog'):
                gui.choose_folder(api, SimpleNamespace(pid=77), 100, Path('folder'), busy_body='expected')
        self.assertEqual(state['clicked'], [])

    def test_progress_records_only_completed_observations(self):
        progress = dict(checks={'owned_unicode_picker': True}, cases=[], cancellations=[], responses=[])
        with tempfile.TemporaryDirectory() as directory:
            gui.write_progress(directory, progress, 'semantic-unicode')
            saved = json.loads((Path(directory) / 'directory-search-progress.json').read_text())
        self.assertEqual(saved['phase'], 'semantic-unicode')
        self.assertNotIn('passed', saved)
        self.assertNotIn('seven_language_layout', saved['checks'])

    def test_real_runner_keeps_prior_gates_and_ordinary_shutdown(self):
        source = inspect.getsource(gui.run)
        for token in ('isolated_settings()', '_copy_runtime(', 'ci.run_gui(', 'choose_folder(',
                      'api.post_navigation(', 'api.verify_owned_handles(', 'api.command(hwnd, 317)',
                      'api.command(hwnd, OPEN)', '0x203', 'api.command(hwnd, 201)', 'close_started',
                      'validate_result(result, hashes)', 'progress=progress'):
            self.assertIn(token, source)
        for token in ('TerminateThread', 'TerminateProcess', 'WriteProcessMemory', 'SCI_SETTEXT', 'subprocess'):
            self.assertNotIn(token, source)
        self.assertEqual(gui.RESPONSE_SECONDS, 2)
        self.assertEqual(gui.MAX_ROWS, 2000)
        self.assertEqual(gui.STRESS_BYTES, 128 * 1024)


if __name__ == '__main__': unittest.main()
