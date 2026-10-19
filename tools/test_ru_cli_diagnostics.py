#!/usr/bin/env python3
"""Real Ru CLI style-hint agreement and fail-closed stderr negative controls."""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from ru_cli_diagnostics import prepare_compile_diagnostics, validate_stderr

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--ru-root', type=Path, required=True)
parser.add_argument('--cc', default='gcc')
parser.add_argument('--output', type=Path, default=ROOT / 'build/ru-cli-diagnostics-evidence')
args, remaining = parser.parse_known_args()
COMPILER = args.ru_root.resolve()


class CliDiagnosticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='ru-cli-style-')
        cls.directory = Path(cls.temporary.name)
        cls.source = cls.directory / 'source 中文.ru'
        cls.imported = cls.directory / 'helper.ru'
        cls.imported.write_text('算 值:\n    得 7.\n法\n', encoding='utf-8')
        cls.source.write_text("甲 取 外言 './helper.ru'.\n乙 取 外言 './helper.ru'.\n"
                              '算 主:\n    得 甲 其 值.\n法\n显 主.\n', encoding='utf-8')
        cls.command = [sys.executable, str(COMPILER / 'ru'), 'check',
                       '--target', 'c', str(cls.source)]
        cls.expected = prepare_compile_diagnostics(cls.command, COMPILER, cls.source)
        cls.lines = cls.expected.stderr.splitlines(keepends=True)
        if len(cls.lines) != 2:
            raise AssertionError('Expected exactly one imported and one root style hint')
        args.output.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def reject(self, stderr, *, code=0, command=None, expectation=None):
        with self.assertRaises((RuntimeError, UnicodeError)):
            validate_stderr(self.command if command is None else command, code, stderr,
                            self.expected if expectation is None else expectation)

    def run_cli(self, command, label):
        result = subprocess.run(command, capture_output=True, timeout=120)
        (args.output / (label + '.stdout.log')).write_bytes(result.stdout)
        (args.output / (label + '.stderr.log')).write_bytes(result.stderr)
        return result

    def test_actual_check_matches_all_source_derived_hints(self):
        result = self.run_cli(self.command, 'actual-check')
        validate_stderr(self.command, result.returncode, result.stderr, self.expected)
        self.assertEqual(result.stderr.decode('utf-8').replace('\r\n', '\n'), self.expected.stderr)
        self.assertEqual(set(dict(self.expected.inputs)) & {str(self.source), str(self.imported)},
                         {str(self.source), str(self.imported)})

    def test_actual_build_and_runtime_are_separate(self):
        executable = self.directory / ('probe.exe' if sys.platform == 'win32' else 'probe')
        command = [sys.executable, str(COMPILER / 'ru'), 'build', '--cc', args.cc,
                   str(self.source), '-o', str(executable)]
        expected = prepare_compile_diagnostics(command, COMPILER, self.source)
        built = self.run_cli(command, 'actual-build')
        validate_stderr(command, built.returncode, built.stderr, expected)
        ran = self.run_cli([str(executable)], 'actual-runtime')
        validate_stderr([str(executable)], ran.returncode, ran.stderr)
        self.assertEqual(ran.stdout.replace(b'\r\n', b'\n'), b'7\n')

    def test_crlf_transport_is_the_only_normalization(self):
        validate_stderr(self.command, 0, self.expected.stderr.replace('\n', '\r\n'), self.expected)
        self.reject(self.expected.stderr.replace('\n', '\r'))

    def test_missing_hint_is_rejected(self):
        self.reject(''.join(self.lines[1:]))
        self.reject('')

    def test_duplicated_hint_is_rejected(self):
        self.reject(self.expected.stderr + self.lines[0])

    def test_reordered_hints_are_rejected(self):
        self.reject(''.join(reversed(self.lines)))

    def test_forged_source_path_is_rejected(self):
        self.reject(self.expected.stderr.replace(str(self.imported), str(self.source)))

    def test_forged_line_or_column_is_rejected(self):
        self.reject(self.expected.stderr.replace(':3:2:', ':3:3:'))
        self.reject(self.expected.stderr.replace(':3:2:', ':4:2:'))

    def test_modified_message_is_rejected(self):
        self.reject(self.expected.stderr.replace('建议', '必须'))

    def test_extra_nonstyle_warning_is_rejected(self):
        self.reject(self.expected.stderr + 'warning: synthetic C compiler warning\n')

    def test_error_severity_is_rejected(self):
        self.reject(self.expected.stderr.replace(': warning:', ': error:'))

    def test_nonzero_exit_is_rejected_even_with_exact_hints(self):
        for code in (1, -9, None):
            with self.subTest(code=code):
                self.reject(self.expected.stderr, code=code)

    def test_missing_final_newline_and_extra_blank_are_rejected(self):
        self.reject(self.expected.stderr.rstrip('\n'))
        self.reject(self.expected.stderr + '\n')

    def test_invalid_utf8_is_rejected(self):
        self.reject(self.expected.stderr.encode('utf-8') + b'\xff')

    def test_runtime_rejects_even_genuine_style_hints(self):
        with self.assertRaises(RuntimeError):
            validate_stderr(['synthetic-runtime'], 0, self.expected.stderr)
        with self.assertRaises(RuntimeError):
            validate_stderr(['synthetic-runtime'], 1, '')
        validate_stderr(['synthetic-runtime'], 0, '')

    def test_expectation_cannot_be_reused_for_runtime_or_other_command(self):
        self.reject(self.expected.stderr, command=['synthetic-runtime'])
        self.reject(self.expected.stderr, command=[*self.command, '--allow-native'])

    def test_prepare_rejects_run_or_unrelated_executable(self):
        for command in ([sys.executable, str(COMPILER / 'ru'), 'run', str(self.source)],
                        ['synthetic-runtime', str(self.source)],
                        [sys.executable, str(self.directory / 'ru'), 'check', str(self.source)]):
            with self.subTest(command=command), self.assertRaises(RuntimeError):
                prepare_compile_diagnostics(command, COMPILER, self.source)

    def test_prepare_rejects_wrong_source_or_options(self):
        for command in ([*self.command[:-1], str(self.imported)],
                        [*self.command, '--strict-style'], [*self.command, '--unknown'],
                        [*self.command, '--target']):
            with self.subTest(command=command), self.assertRaises(RuntimeError):
                prepare_compile_diagnostics(command, COMPILER, self.source)

    def test_root_source_changes_are_rejected(self):
        before = self.source.read_bytes()
        try:
            self.source.write_bytes(before + b'# changed after expectation\n')
            self.reject(self.expected.stderr)
        finally:
            self.source.write_bytes(before)

    def test_imported_source_changes_are_rejected(self):
        before = self.imported.read_bytes()
        try:
            self.imported.write_bytes(before + b'# changed after expectation\n')
            self.reject(self.expected.stderr)
        finally:
            self.imported.write_bytes(before)

    def test_style_clean_source_requires_empty_stderr(self):
        source = self.directory / 'clean.ru'
        source.write_text('显 1.\n', encoding='utf-8')
        command = [sys.executable, str(COMPILER / 'ru'), 'check', str(source)]
        expected = prepare_compile_diagnostics(command, COMPILER, source)
        self.assertEqual(expected.stderr, '')
        result = self.run_cli(command, 'actual-clean-check')
        validate_stderr(command, result.returncode, result.stderr, expected)
        with self.assertRaises(RuntimeError):
            validate_stderr(command, 0, self.expected.stderr, expected)


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0], *remaining])
