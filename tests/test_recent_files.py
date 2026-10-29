"""Portable negative controls for recent-file evidence (not Windows acceptance)."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import verify_recent_files_windows as recent


class RecentEvidenceTests(unittest.TestCase):
    def test_callback_fixture_uses_exact_production_control_flow(self):
        root = Path(__file__).resolve().parents[1]
        main = (root / 'src/main.ru').read_text(encoding='utf-8')
        fixture = (root / 'tests/recent_files_callbacks.ru').read_text(encoding='utf-8')
        reader = main[main.index('    试\n        取近函数'):main.index("    A 其 增 'visible'")]
        writer = main[main.index('算 持久最近:'):main.index('算 记最近 ')]
        self.assertIn('近果 取 取近函数().', reader)
        self.assertEqual(fixture.count(reader), 1)
        self.assertEqual(fixture.count(writer), 1)

    def good(self):
        hashes = {n: 'a' * 64 for n in ('ru_notepad.exe', 'Scintilla.dll', 'Lexilla.dll', 'RuSyntax.dll')}
        record = {'name': 'main-gui-recent-files', 'passed': True, 'executed': True,
                  'cleanup_killed': False, 'exit_code': 0, 'fixture_binary_sha256': hashes,
                  'checks': {key: True for key in recent.CHECKS},
                  'phases': [{'phase': name, 'passed': True, 'executed': True,
                              'cleanup_killed': False, 'exit_code': 0,
                              'fixture_binary_sha256': hashes} for name in recent.PHASES]}
        return record, hashes

    def test_exact_complete_evidence(self):
        self.assertTrue(recent.validate_recent_files_result(*self.good()))

    def test_each_missing_or_failed_check_rejected(self):
        for key in recent.CHECKS:
            for bad in ('missing', False, 1):
                record, hashes = self.good()
                if bad == 'missing':
                    del record['checks'][key]
                else:
                    record['checks'][key] = bad
                with self.subTest(key=key, bad=bad), self.assertRaises(ValueError):
                    recent.validate_recent_files_result(record, hashes)

    def test_every_restart_must_finish_normally_and_match_binary(self):
        for index in range(4):
            for key, value in [('passed', False), ('executed', False), ('cleanup_killed', True),
                               ('exit_code', 9), ('fixture_binary_sha256', {}), ('phase', 'wrong')]:
                record, hashes = self.good()
                record['phases'][index][key] = value
                with self.subTest(index=index, key=key), self.assertRaises(ValueError):
                    recent.validate_recent_files_result(record, hashes)

    def test_missing_phase_or_different_package_rejected(self):
        record, hashes = self.good()
        record['phases'].pop()
        with self.assertRaises(ValueError):
            recent.validate_recent_files_result(record, hashes)
        record, hashes = self.good()
        with self.assertRaises(ValueError):
            recent.validate_recent_files_result(record, {})

    def dialog_api(self, sequence, identifier=2):
        api = Mock()
        api.callback_type = lambda fn: fn
        api.windows.side_effect = sequence
        api.user.GetClassNameW.side_effect = lambda hwnd, out, size: setattr(out, 'value', 'Button') or 6
        api.user.IsWindowVisible.return_value = True
        api.user.EnumChildWindows.side_effect = lambda hwnd, callback, extra: callback(99, 0)
        api.user.GetDlgCtrlID.return_value = identifier
        api.user.PostMessageW.return_value = True
        api.text.return_value = 'OK'
        process = Mock(pid=42)
        process.poll.return_value = None
        return api, process

    def test_dialog_acknowledges_actual_button_and_waits_for_disappearance(self):
        dialog = [(12, '#32770', True)]
        api, process = self.dialog_api([dialog, dialog, dialog, []])
        with patch.object(recent.time, 'sleep'):
            recent._error_dialog(api, process)
        api.user.PostMessageW.assert_called_once_with(99, 0x00F5, 0, 0)
        api.verify_owned_handles.assert_called_once_with(42, 12, 99)
        self.assertEqual(api.windows.call_count, 4)

    def test_undismissed_dialog_and_unknown_control_are_failures(self):
        dialog = [(12, '#32770', True)]
        api, process = self.dialog_api([dialog] * 20)
        with patch.object(recent.time, 'sleep'), patch.object(recent.time, 'monotonic', side_effect=range(20)):
            with self.assertRaisesRegex(RuntimeError, 'did not dismiss'):
                recent._error_dialog(api, process, timeout=4)
        api, process = self.dialog_api([dialog], identifier=8)
        with self.assertRaisesRegex(RuntimeError, 'standard labelled'):
            recent._error_dialog(api, process)
        api.user.PostMessageW.assert_not_called()

    def test_menu_label_is_presentation_only_and_bounded(self):
        path = 'C:\\中文 😀\\A&B\tline\nfile.txt'
        self.assertEqual(recent._label(path), 'C:\\中文 😀\\A&&B line file.txt')
        self.assertEqual(path, 'C:\\中文 😀\\A&B\tline\nfile.txt')
        self.assertEqual(len(recent._label('x'*200)), 101)


if __name__ == '__main__':
    unittest.main()
