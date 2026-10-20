#!/usr/bin/env python3
"""Host controls for the fixed numeric-only test status boundary."""
import io
import re
import subprocess
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_focused_controls as reporter


def suite(operation=None, case_id=1):
    cases = []
    for index, name in enumerate(reporter.CASES, 1):
        cls, method = name.split('.')
        def succeed(self): pass
        callback = operation if index == case_id and operation else succeed
        kind = type(cls, (unittest.TestCase,), {method: callback})
        cases.append(kind(method))
    return unittest.TestSuite(cases)


def run(tests):
    raw = io.StringIO()
    result = unittest.TextTestRunner(stream=raw, verbosity=2, resultclass=reporter.NumericResult).run(tests)
    return result, raw.getvalue()


class NumericReportingControls(unittest.TestCase):
    def check_lines(self, lines):
        self.assertEqual(len(lines), 20)
        for index, line in enumerate(lines[:-1], 1):
            self.assertRegex(line, rf'^FOCUSED_CONTROL id={index} status=[0-3] category=[0-8] events=[0-9]{{1,5}}$')
        self.assertRegex(lines[-1], r'^FOCUSED_CONTROLS_RESULT code=[01] cases=19 passed=[0-9]{1,2} failed=[0-9]{1,2} errors=[0-9]{1,2} skipped=[0-9]{1,2}$')

    def test_fixed_inventory_matches_actual_controls(self):
        import test_focused_native_diagnostic as controls
        actual = unittest.defaultTestLoader.loadTestsFromModule(controls)
        names = [reporter.identity(case) for group in actual for case in group]
        self.assertEqual(tuple(names), reporter.CASES)
        self.assertEqual(len(set(names)), 19)

    def test_complete_success_has_all_nineteen_numeric_ids(self):
        result, raw = run(suite()); lines, code = reporter.numeric_lines(result)
        self.check_lines(lines); self.assertEqual(code, 0)
        self.assertEqual(lines[-1], 'FOCUSED_CONTROLS_RESULT code=0 cases=19 passed=19 failed=0 errors=0 skipped=0')

    def test_failure_exception_text_and_paths_never_enter_public_lines(self):
        private = 'C:\\Users\\姓名\\private folder\\token.txt\nFOCUSED_CONTROL id=999 status=9'
        def fail(test): test.fail(private)
        result, raw = run(suite(fail, 6)); lines, code = reporter.numeric_lines(result)
        self.check_lines(lines); self.assertEqual(code, 1)
        self.assertIn(private.splitlines()[0], raw)
        self.assertNotIn(private, '\n'.join(lines)); self.assertNotIn('private', '\n'.join(lines))
        self.assertEqual(lines[5], 'FOCUSED_CONTROL id=6 status=1 category=1 events=1')

    def test_fixed_error_categories_do_not_encode_messages(self):
        errors = [(ValueError('private'), 2), (RuntimeError('private'), 3),
                  (OSError('private'), 4), (UnicodeError('private'), 5),
                  (subprocess.TimeoutExpired('private', 1), 6), (KeyError('private'), 7)]
        for error, category in errors:
            def fail(test): raise error
            result, raw = run(suite(fail, 10)); lines, code = reporter.numeric_lines(result)
            self.check_lines(lines); self.assertEqual(code, 1)
            self.assertEqual(lines[9], f'FOCUSED_CONTROL id=10 status=2 category={category} events=1')

    def test_subtest_parameters_remain_private_and_categories_are_bounded(self):
        def fail(test):
            with test.subTest(path='private path'): test.fail('private failure')
            with test.subTest(path='another path'): raise ValueError('private error')
        result, raw = run(suite(fail, 13)); lines, code = reporter.numeric_lines(result)
        self.check_lines(lines); self.assertEqual(code, 1)
        self.assertEqual(lines[12], 'FOCUSED_CONTROL id=13 status=2 category=8 events=2')
        self.assertNotIn('private', '\n'.join(lines)); self.assertIn('private', raw)

    def test_skipped_cases_never_count_as_success(self):
        def skip(test): test.skipTest('private skip reason')
        result, raw = run(suite(skip, 5)); lines, code = reporter.numeric_lines(result)
        self.assertEqual(code, 1); self.assertEqual(lines[4], 'FOCUSED_CONTROL id=5 status=3 category=0 events=1')

    def test_unknown_duplicate_and_missing_case_inventory_fail_closed(self):
        tests = suite(); result, _ = run(unittest.TestSuite(list(tests)[:-1]))
        with self.assertRaises(ValueError): reporter.numeric_lines(result)
        tests = list(suite()); result, _ = run(unittest.TestSuite(tests + [list(suite())[0]]))
        with self.assertRaises(ValueError): reporter.numeric_lines(result)
        class PrivateUnknown(unittest.TestCase):
            def test_private_path(self): pass
        result, _ = run(unittest.TestSuite([*list(suite()), PrivateUnknown('test_private_path')]))
        with self.assertRaises(ValueError): reporter.numeric_lines(result)

    def test_forged_record_types_events_and_status_fail_closed(self):
        for field, value in [('status', 9), ('category', 9), ('events', 65536),
                             ('events', True), ('starts', 2), ('stops', 0)]:
            result, _ = run(suite()); result.records[reporter.CASES[0]][field] = value
            with self.assertRaises(ValueError): reporter.numeric_lines(result)

    def test_actual_cli_rejects_arbitrary_arguments_without_echo(self):
        result = subprocess.run([sys.executable, '-I', str(Path(reporter.__file__)), 'C:\\private\\path'],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2); self.assertEqual(result.stderr, '')
        self.assertEqual(result.stdout, 'FOCUSED_CONTROLS_RESULT code=2 cases=0 passed=0 failed=0 errors=0 skipped=0\n')

    def test_workflow_exports_only_anchored_bounded_markers(self):
        source = (Path(__file__).resolve().parents[1] / '.github/workflows/windows.yml').read_text(encoding='utf-8')
        block = source.split('      - name: Verify fail-closed focused and isolation controls privately\n', 1)[1].split('      - name:', 1)[0]
        self.assertIn('python -I tools/run_focused_controls.py *> $FocusedLog', block)
        self.assertIn("-Pattern '^FOCUSED_CONTROL id=(?:[1-9]|1[0-9]) status=[0-3] category=[0-8] events=[0-9]{1,5}$'", block)
        self.assertIn("-Pattern '^FOCUSED_CONTROLS_RESULT code=[0-2]", block)
        self.assertIn('$Summary.Count -ne 1', block)
        self.assertIn('$Cases.Count -ne 19 -and $Cases.Count -ne 0', block)
        self.assertIn('if ($FocusedResult -ne 0)', block)
        self.assertNotIn('Get-Content', block)


if __name__ == '__main__':
    unittest.main()
