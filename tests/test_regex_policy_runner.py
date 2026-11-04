"""The oracle and chunk adapter have independent, cheap unit coverage."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import call, patch

SPEC = importlib.util.spec_from_file_location('regex_policy_runner', Path(__file__).resolve().parents[1] / 'tools/test_regex_policy.py')
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)
BRIDGE_SPEC = importlib.util.spec_from_file_location(
    'regex_bridge_runner', Path(__file__).resolve().parent / 'test_regex_search_bridge.py')
bridge = importlib.util.module_from_spec(BRIDGE_SPEC)
BRIDGE_SPEC.loader.exec_module(bridge)
RUNNERS = (runner, bridge)


class RegexOracleTests(unittest.TestCase):
    def test_utf8_context_is_document_context(self):
        self.assertEqual(runner.feeds('x😀\r\na', 1, 4, (2, 3)),
                         [['😀', 1, 'x', '\r', False],
                          ['\r', 5, '😀', '\n', False],
                          ['\n', 6, '\r', 'a', True]])

    def test_empty_scope_keeps_both_neighbors(self):
        self.assertEqual(runner.feeds('a😀b', 1, 1, ()), [['', 1, 'a', '😀', True]])

    def test_priority_and_saved_end_oracle(self):
        rows = {r[0]: r for r in runner.cases()}
        self.assertEqual(rows['first-arm-s0-b1'][9:], [0, 1])
        self.assertEqual(rows['long-arm-s0-b1'][9:], [0, 2])
        self.assertEqual(rows['saved-end-s0-b1'][9:], [0, 1])
        self.assertEqual(rows['unicode-offset-s0-b1'][9:], [3, 11])
        self.assertEqual(rows['no-normalize-s0-b1'][8:], ['no-match', -1, -1])

    def test_every_case_has_unique_name(self):
        rows = runner.cases()
        self.assertEqual(len(rows), len({r[0] for r in rows}))
        for row in rows:
            if not row[8].startswith('compile-') and not row[0].startswith('feed-'):
                self.assertLessEqual(max(len(feed[0]) for feed in row[5]), 256)

    def test_no_implicit_python_multiline_or_dot_policy(self):
        rows = {r[0]: r for r in runner.cases()}
        self.assertEqual(rows['dot-no-cr-s0-b1'][8], 'no-match')
        self.assertEqual(rows['cr-start-s0-b1'][9:], [2, 3])
        self.assertEqual(rows['crlf-no-middle-start-s0-b1'][8], 'no-match')
        self.assertEqual(rows['scope-not-start-s0-b1'][8], 'no-match')

    def test_compiler_exact_pins_and_clean_source_are_accepted(self):
        expected_commit = 'c3bb177c6a15e90821e5495cc74b0fdfc39b893a'
        expected_tree = '5dedbf06f9fb6e00fbfe779b33f172aa35b61334'
        root = Path('compiler-source')
        for module in RUNNERS:
            with self.subTest(runner=module.__name__):
                self.assertEqual(module.PIN, expected_commit)
                self.assertEqual(module.TREE, expected_tree)
                with patch.object(module.subprocess, 'check_output', side_effect=[
                        expected_commit + '\n', expected_tree + '\n', '']) as git:
                    self.assertEqual(module.verify_compiler(root), expected_commit)
                self.assertEqual(git.call_args_list, [
                    call(['git', '-C', str(root), 'rev-parse', 'HEAD'],
                         text=True, encoding='utf-8'),
                    call(['git', '-C', str(root), 'rev-parse', 'HEAD^{tree}'],
                         text=True, encoding='utf-8'),
                    call(['git', '-C', str(root), 'status', '--porcelain=v1',
                          '--untracked-files=all'], text=True, encoding='utf-8'),
                ])

    def test_compiler_rejects_prefix_only_or_wrong_full_commit(self):
        root = Path('compiler-source')
        for module in RUNNERS:
            # Same seven-character prefix must not authorize a different SHA.
            for wrong in (module.PIN[:7], module.PIN[:7] + '0' * 33):
                with self.subTest(runner=module.__name__, commit=wrong):
                    with patch.object(module.subprocess, 'check_output',
                                      side_effect=[wrong, module.TREE]):
                        with self.assertRaisesRegex(RuntimeError, 'Wrong compiler identity'):
                            module.verify_compiler(root)

    def test_compiler_rejects_wrong_tree(self):
        root = Path('compiler-source')
        for module in RUNNERS:
            with self.subTest(runner=module.__name__):
                with patch.object(module.subprocess, 'check_output',
                                  side_effect=[module.PIN, '0' * 40]):
                    with self.assertRaisesRegex(RuntimeError, 'Wrong compiler identity'):
                        module.verify_compiler(root)

    def test_compiler_rejects_modified_staged_or_untracked_source(self):
        root = Path('compiler-source')
        for module in RUNNERS:
            for status in (' M ru\n', 'M  rulang/cli.py\n', '?? injected.py\n'):
                with self.subTest(runner=module.__name__, status=status):
                    with patch.object(module.subprocess, 'check_output',
                                      side_effect=[module.PIN, module.TREE, status]):
                        with self.assertRaisesRegex(RuntimeError, 'Compiler source must be clean'):
                            module.verify_compiler(root)

    def test_executable_suffix_is_explicit_on_windows(self):
        # Construct Path before mocking os.name: pathlib itself shares os.
        root = Path('output')
        for module in RUNNERS:
            for platform, filename in (('nt', 'fixture.exe'), ('posix', 'fixture')):
                with self.subTest(runner=module.__name__, platform=platform):
                    with patch.object(module.os, 'name', platform):
                        self.assertEqual(module.executable_path(root, 'fixture'), root / filename)

    def test_gcc_resolution_requires_an_available_compiler(self):
        for module in RUNNERS:
            with self.subTest(runner=module.__name__):
                with patch.object(module.shutil, 'which', return_value='toolchain/gcc.exe') as which:
                    self.assertEqual(module.gcc_path(), 'toolchain/gcc.exe')
                    which.assert_called_once_with('gcc')
                with patch.object(module.shutil, 'which', return_value=None):
                    with self.assertRaisesRegex(RuntimeError, 'gcc C compiler must be available'):
                        module.gcc_path()

    def test_runtime_output_accepts_clean_output(self):
        for module in RUNNERS:
            with self.subTest(runner=module.__name__):
                self.assertIsNone(module.runtime_output('PASS: example\nTOTAL PASS: 1\n', '', 'runtime'))

    def test_runtime_output_rejects_any_stderr(self):
        for module in RUNNERS:
            for stderr in ('warning\n', ' ', 'FAIL: hidden diagnostic\n'):
                with self.subTest(runner=module.__name__, stderr=stderr):
                    with self.assertRaisesRegex(AssertionError, 'unexpected runtime stderr'):
                        module.runtime_output('PASS: example\nTOTAL PASS: 1\n', stderr, 'runtime')

    def test_runtime_output_rejects_failure_and_skip_markers(self):
        for module in RUNNERS:
            for marker in ('FAIL: example', 'SKIP: unavailable', 'fail: example',
                           'skip: unavailable', 'diagnostic FAIL inside a line'):
                with self.subTest(runner=module.__name__, marker=marker):
                    with self.assertRaisesRegex(AssertionError, 'failure or skip marker'):
                        module.runtime_output('PASS: example\n' + marker + '\nTOTAL PASS: 1\n',
                                              '', 'runtime')


if __name__ == '__main__':
    unittest.main()
