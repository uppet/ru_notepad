#!/usr/bin/env python3
"""Host-side negative controls for the i18n and warning evidence runners.

No native-window claim: synthetic child processes exercise the real bounded
runner, receipt/publication path and failure cleanup. --ru-root additionally
checks the exact compiler identity and real production-function extraction.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack, contextmanager, redirect_stdout
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import test_i18n as runner
from ru_cli_diagnostics import CompileDiagnostics

spec = importlib.util.spec_from_file_location('warning_runner_controls', ROOT / 'tests/syntax_warning_portable.py')
warning = importlib.util.module_from_spec(spec)
spec.loader.exec_module(warning)

PARSER = argparse.ArgumentParser(description=__doc__)
PARSER.add_argument('--ru-root', type=Path)
ARGS, REMAINING = PARSER.parse_known_args()
PIN = {'commit': runner.RU_COMMIT, 'tree': runner.RU_TREE, 'status': ''}


def assertion_output(names):
    return ('\n'.join('PASS: ' + name for name in names) + f'\nTOTAL PASS: {len(names)}\n').encode()


def command_arguments(data):
    """Read argv semantically: JSON escapes are not filesystem path bytes."""
    command = json.loads(data)
    if type(command) is not list or not command or any(type(arg) is not str for arg in command):
        raise ValueError('Expected a nonempty string argv')
    return command


def json_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from json_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from json_strings(item)


def assert_public_hides_paths(test, data, suffix, paths):
    """Inspect decoded JSON keys/values, and raw or escaped text in log files."""
    values = list(json_strings(json.loads(data))) if suffix == '.json' else [data.decode('utf-8')]
    for private in paths:
        forms = {str(private)}
        if suffix != '.json':
            forms.update(json.dumps(str(private), ensure_ascii=ascii_only)[1:-1]
                         for ascii_only in (False, True))
        for value in values:
            for form in forms:
                test.assertNotIn(form, value)


class ChildContracts(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='i18n-runner-controls-')
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name).resolve()

    def command(self, code):
        return [sys.executable, '-I', '-c', code]

    def run_child(self, code, label='probe', **kwargs):
        return runner.checked_run(self.command(code), self.directory, label, 5, **kwargs)

    def test_success_receipt_hashes_original_bytes_and_hides_command(self):
        records = []
        code = "import sys; sys.stdout.buffer.write('中文\\n'.encode())"
        data = self.run_child(code, records=records)
        record, = records
        self.assertEqual(data, '中文\n'.encode())
        self.assertEqual(record['stdout_sha256'], hashlib.sha256(data).hexdigest())
        self.assertEqual(record['stderr_sha256'], hashlib.sha256(b'').hexdigest())
        self.assertEqual(record['stdout_bytes'], len(data))
        self.assertEqual(record['stderr_bytes'], 0)
        self.assertEqual(record['exit_code'], 0)
        raw = command_arguments((self.directory / 'probe.command.json').read_bytes())
        self.assertEqual(raw, self.command(code))
        self.assertEqual(record['command_sha256'], hashlib.sha256(json.dumps(raw).encode()).hexdigest())
        assert_public_hides_paths(self, json.dumps(record).encode(), '.json', [sys.executable])
        self.assertNotIn('command', record)

    def test_both_wrappers_reject_runtime_stderr_and_nonzero_exit(self):
        for which in ('i18n', 'warnings'):
            for index, (status, stderr) in enumerate(((0, 'private diagnostic'), (7, ''), (7, 'private diagnostic'))):
                code = f'import sys; sys.stderr.write({stderr!r}); sys.exit({status})'
                label = f'{which}-{index}'
                with self.subTest(which=which, status=status, stderr=stderr), self.assertRaises(RuntimeError):
                    if which == 'i18n':
                        self.run_child(code, label)
                    else:
                        warning.checked(self.command(code), log=self.directory / label)
                self.assertEqual((self.directory / (label + '.stderr')).read_bytes(), stderr.encode())

    def test_genuine_compile_diagnostics_require_exact_bytes_and_inputs(self):
        source = self.directory / 'source 中文.ru'
        source.write_bytes('显 1.\n'.encode())
        stderr = str(source) + ':1:1: warning: synthetic exact style hint\n'
        code = f'import sys; sys.stderr.buffer.write({stderr.encode()!r})'
        command = self.command(code)
        expectation = CompileDiagnostics(tuple(command), stderr, ((str(source), runner.file_sha256(source)),))
        self.run_child(code, compile_diagnostics=expectation)
        for index, changed in enumerate((stderr + '\n', stderr.replace('warning', 'error'), '')):
            other = self.command(f'import sys; sys.stderr.buffer.write({changed.encode()!r})')
            contract = CompileDiagnostics(tuple(other), stderr, expectation.inputs)
            with self.subTest(changed=changed), self.assertRaises(RuntimeError):
                runner.checked_run(other, self.directory, f'changed-{index}', 5, compile_diagnostics=contract)
        source.write_bytes(b'# modified after preparation\n')
        with self.assertRaises(RuntimeError):
            self.run_child(code, 'source-changed', compile_diagnostics=expectation)

    def test_invalid_utf8_stderr_fails_closed(self):
        with self.assertRaises(UnicodeError):
            self.run_child("import sys; sys.stderr.buffer.write(b'\\xff')")

    def test_both_output_streams_have_fixed_bounds(self):
        for stream in ('stdout', 'stderr'):
            with self.subTest(stream=stream), self.assertRaises(RuntimeError):
                self.run_child(f'import sys; sys.{stream}.buffer.write(b"x" * {runner.LIMIT + 1})', stream)
            self.assertGreater((self.directory / (stream + '.' + stream)).stat().st_size, runner.LIMIT)

    def test_timeout_cleans_owned_process_tree_and_retains_raw_streams(self):
        records = []
        with patch.object(runner, 'stop_process_tree', wraps=runner.stop_process_tree) as stop:
            with self.assertRaises(RuntimeError):
                runner.checked_run(self.command('import sys, time; sys.stdout.buffer.write(b"partial\\n"); '
                                                 'sys.stdout.flush(); time.sleep(10)'),
                                   self.directory, 'timeout', .5, records)
            stop.assert_called_once()
        self.assertEqual((self.directory / 'timeout.stdout').read_bytes(), b'partial\n')
        self.assertNotEqual(records[0]['exit_code'], 0)

    def test_late_success_still_fails_wall_deadline(self):
        process = types.SimpleNamespace(pid=12345, returncode=0, wait=lambda **_: 0, poll=lambda: 0)
        with patch.object(runner.subprocess, 'Popen', return_value=process), \
                patch.object(runner.time, 'monotonic', side_effect=[0, 0, 2, 2]), \
                patch.object(runner, 'stop_process_tree'):
            with self.assertRaises(RuntimeError):
                runner.checked_run(['synthetic'], self.directory, 'late', 1)

    def test_cleanup_failure_is_distinct_and_cannot_be_masked_by_receipt_failure(self):
        process = types.SimpleNamespace(pid=12345, returncode=None, wait=lambda **_: None, poll=lambda: None)
        with patch.object(runner.subprocess, 'Popen', return_value=process), \
                patch.object(runner.time, 'monotonic', side_effect=[0, 2, 2]), \
                patch.object(runner, 'stop_process_tree', side_effect=OSError('private path')), \
                patch.object(runner, 'file_sha256', side_effect=OSError('private log path')):
            with self.assertRaises(runner.CleanupError):
                runner.checked_run(['synthetic'], self.directory, 'cleanup', 1)

    def test_command_receipt_write_failure_still_cleans_child(self):
        with patch.object(Path, 'write_text', side_effect=OSError('write failed')), \
                patch.object(runner, 'stop_process_tree', wraps=runner.stop_process_tree) as stop:
            with self.assertRaises(OSError):
                self.run_child('import time; time.sleep(10)')
            stop.assert_called_once()


class SourceContracts(unittest.TestCase):
    def test_compiler_pin_requires_exact_commit_tree_and_clean_status(self):
        for field in ('commit', 'tree', 'status'):
            bad = dict(PIN, **{field: 'changed'})
            with self.subTest(field=field), patch.object(runner.subprocess, 'check_output',
                    side_effect=[bad[key].encode() for key in ('commit', 'tree', 'status')]):
                with self.assertRaises(RuntimeError):
                    runner.compiler_snapshot(Path('synthetic-compiler'))
        with patch.object(runner.subprocess, 'check_output',
                          side_effect=[PIN[key].encode() for key in ('commit', 'tree', 'status')]):
            self.assertEqual(runner.compiler_snapshot(Path('synthetic-compiler')), PIN)

    def test_policy_oracle_rejects_reordered_or_path_bearing_passes(self):
        names = runner.policy_assertion_names()
        self.assertEqual(len(names), 289)
        runner.verify_output(assertion_output(names), 289, names)
        for changed in ([*reversed(names)], ['/private/source.ru', *names[1:]]):
            with self.subTest(changed=changed[:1]), self.assertRaises(RuntimeError):
                runner.verify_output(assertion_output(changed), 289, names)

    def test_snapshot_closes_both_literal_import_styles_and_every_consumed_file(self):
        with sandbox() as fixture:
            initial = runner.source_snapshot()
            self.assertIn('src/i18n.ru', initial)
            self.assertIn('src/i18n_catalog.ru', initial)
            self.assertIn('tools/ru_cli_diagnostics.py', initial)
            self.assertIn('locales/errors.json', initial)
            warning_initial = warning.source_snapshot()
            for relative in sorted(set(initial) | set(warning_initial)):
                path = fixture.root / relative
                original = path.read_bytes()
                path.write_bytes(original + b'\n# changed\n')
                with self.subTest(relative=relative):
                    if relative in initial:
                        self.assertNotEqual(runner.source_snapshot(), initial)
                    if relative in warning_initial:
                        self.assertNotEqual(warning.source_snapshot(), warning_initial)
                path.write_bytes(original)
            policy = fixture.root / 'tests/i18n_policy.ru'
            for imported in ('../../../outside.ru', '如:密'):
                policy.write_text('甲 取 外言 ' + json.dumps(imported, ensure_ascii=False) + '.\n', encoding='utf-8')
                with self.subTest(imported=imported), self.assertRaises(RuntimeError):
                    runner.source_snapshot()

    @unittest.skipUnless(ARGS.ru_root, 'pass --ru-root for real pinned frontend extraction')
    def test_real_extraction_is_utf8_lf_and_keeps_complete_production_bodies(self):
        compiler = ARGS.ru_root.resolve()
        self.assertEqual(runner.compiler_snapshot(compiler), PIN)
        with patch.object(sys, 'path', [str(compiler), *sys.path]):
            from rulang.frontend import parse
            for kind in ('ru', 'md'):
                with tempfile.TemporaryDirectory() as temporary:
                    directory = Path(temporary).resolve()
                    source = warning.prepare(directory, kind, parse)
                    self.assertEqual(source.parent, directory)
                    for path in directory.glob('*.ru'):
                        data = path.read_bytes()
                        self.assertEqual(data.decode('utf-8').encode('utf-8'), data)
                        if path.name in ('i18n.ru', 'i18n_catalog.ru', 'markdown_policy.ru'):
                            self.assertEqual(data, (ROOT / 'src' / path.name).read_bytes())
                        else:
                            self.assertNotIn(b'\r', data)
                    text = source.read_text(encoding='utf-8')
                    production = ROOT / ('src/ru_syntax.ru' if kind == 'ru' else 'src/markdown_syntax.ru')
                    for name in (('选择', '状态', '_失败') if kind == 'ru' else ('_统计', '撤销直属', '变化', '状态')):
                        self.assertIn(warning.function_source(production, name, parse), text)
                    parse(text)


@contextmanager
def sandbox():
    """Exercise real orchestration, file writes and receipts with tiny child tools."""
    with tempfile.TemporaryDirectory(prefix='i18n-proof-controls-') as temporary, ExitStack() as stack:
        root = Path(temporary).resolve()
        for name in ('src', 'tools', 'tests', 'locales', 'compiler/rulang'):
            (root / name).mkdir(parents=True, exist_ok=True)
        for name in ('i18n.ru', 'i18n_catalog.ru', 'markdown_policy.ru', 'ru_native_syntax.ru',
                     'ru_syntax.ru', 'markdown_syntax.ru'):
            (root / 'src' / name).write_text('# 中文 synthetic source\n', encoding='utf-8', newline='\n')
        (root / 'src/i18n.ru').write_text('甲 取 外言 "./i18n_catalog.ru".\n', encoding='utf-8', newline='\n')
        (root / 'tests/i18n_policy.ru').write_text("甲 取 外言 '../src/i18n.ru'.\n", encoding='utf-8', newline='\n')
        for name in ('tools/test_i18n.py', 'tools/generate_i18n.py', 'tools/ru_cli_diagnostics.py',
                     'tests/syntax_warning_portable.py'):
            shutil.copyfile(ROOT / name, root / name)
        catalog = {'synthetic.value': dict.fromkeys(runner.LANGUAGES, '中文 value')}
        (root / 'locales/ui.json').write_text(json.dumps(catalog), encoding='utf-8')
        (root / 'locales/errors.json').write_text('{}\n', encoding='utf-8')
        (root / 'compiler/ru').write_text('# synthetic CLI\n')
        (root / 'compiler/rulang/interpreter.py').write_text('# synthetic interpreter\n')
        fixture = types.SimpleNamespace(root=root, outputs={}, commands=[], prepared=[], on_command=None)
        for module in (runner, warning):
            stack.enter_context(patch.object(module, 'ROOT', root))
            stack.enter_context(patch.object(module, 'compiler_snapshot', return_value=dict(PIN)))
        stack.enter_context(patch.object(runner.platform, 'platform', return_value='synthetic-host'))
        stack.enter_context(patch.object(runner, '__file__', str(root / 'tools/test_i18n.py')))
        original_mkdtemp = tempfile.mkdtemp
        def lexical_mkdtemp(*args, **kwargs):
            path = Path(original_mkdtemp(*args, **kwargs))
            # A lexical noncanonical spelling tests resolve without symlink privileges.
            return str(path.parent / '.' / path.name / '..' / path.name)
        stack.enter_context(patch.object(tempfile, 'mkdtemp', side_effect=lexical_mkdtemp))
        frontend = types.ModuleType('rulang.frontend')
        frontend.parse = lambda text: []
        stack.enter_context(patch.dict(sys.modules, {'rulang': types.ModuleType('rulang'), 'rulang.frontend': frontend}))
        def prepare(directory, kind, parse):
            if directory != directory.resolve():
                raise AssertionError('Fixture directory was not canonicalized')
            source = directory / 'probe.ru'
            source.write_text('# 中文 generated fixture\n', encoding='utf-8', newline='\n')
            fixture.outputs[str(directory)] = f'{kind}|0|en|synthetic\nASSERTIONS: 3\n'.encode()
            fixture.prepared.append(source)
            return source
        stack.enter_context(patch.object(warning, 'prepare', side_effect=prepare))
        stack.enter_context(patch.object(warning, 'expected_output', side_effect=lambda kind: f'{kind}|0|en|synthetic\nASSERTIONS: 3\n'))
        def diagnostics(command, compiler, source):
            return CompileDiagnostics(tuple(map(str, command)), str(source) + ':1:1: warning: PRIVATE_DIAGNOSTIC\n',
                                      ((str(source), runner.file_sha256(source)),))
        for module in (runner, warning):
            stack.enter_context(patch.object(module, 'prepare_compile_diagnostics', side_effect=diagnostics))
        original_popen = subprocess.Popen
        def popen(command, **kwargs):
            command = list(map(str, command))
            fixture.commands.append(command)
            if fixture.on_command:
                fixture.on_command(command)
            stdout, stderr, extra = b'', b'', ''
            if '--version' in command:
                stdout = (str(root) + ' PRIVATE_COMPILER_VERSION\n').encode()
            elif 'build' in command:
                source = Path(command[command.index('--cc') + 2])
                if source != source.resolve():
                    raise AssertionError('Compiled source path was not canonicalized')
                stderr = (str(source) + ':1:1: warning: PRIVATE_DIAGNOSTIC\n').encode()
                generated = command[command.index('--emit-c') + 1]
                extra = f'from pathlib import Path; Path({generated!r}).write_bytes(b"/* synthetic C */\\n"); '
            else:
                source = Path(command[-1] if '-c' in command or 'run' in command else command[0])
                if source.name.startswith('i18n_policy'):
                    stdout = assertion_output(runner.policy_assertion_names())
                elif source.name.startswith('catalog_exact'):
                    stdout = assertion_output([language + '/synthetic.value' for language in runner.LANGUAGES])
                else:
                    stdout = fixture.outputs[str(source.parent)]
            code = extra + f'import sys; sys.stdout.buffer.write({stdout!r}); sys.stderr.buffer.write({stderr!r})'
            return original_popen([sys.executable, '-I', '-c', code], **kwargs)
        stack.enter_context(patch.object(subprocess, 'Popen', side_effect=popen))
        yield fixture


class PublicationContracts(unittest.TestCase):
    def run_fixture(self, fixture, which):
        output = fixture.root / ('public-' + which)
        with redirect_stdout(io.StringIO()):
            if which == 'i18n':
                runner.run_backends(fixture.root / 'compiler' / '..' / 'compiler', 'synthetic-cc', output)
            else:
                with patch.object(sys, 'argv', ['syntax_warning_portable.py', '--ru-root',
                        str(fixture.root / 'compiler' / '..' / 'compiler'), '--output', str(output)]):
                    warning.main()
        return output

    def test_both_public_receipts_close_sources_commands_and_private_logs(self):
        for which in ('i18n', 'warnings'):
            with self.subTest(which=which), sandbox() as fixture:
                public = self.run_fixture(fixture, which)
                report = json.loads((public / 'report.json').read_text())
                self.assertTrue(report['passed'])
                self.assertFalse(report['native_windows_ui_executed'])
                self.assertEqual(len(report['cases']), 4)
                self.assertEqual(len(report['commands']), 7 if which == 'i18n' else 6)
                for name, digest in report['source_sha256'].items():
                    self.assertEqual(digest, runner.file_sha256(fixture.root / name))
                private_root = fixture.root / 'build' / ('i18n-policy-private' if which == 'i18n' else 'syntax-warning-private')
                private_commands = []
                for index, record in enumerate(report['commands']):
                    command_file, = private_root.glob('*/' + record['stage'] + '.command.json')
                    command = command_arguments(command_file.read_bytes())
                    private_commands.append(command)
                    self.assertEqual(command, fixture.commands[index])
                    self.assertEqual(record['command_sha256'], hashlib.sha256(json.dumps(command).encode()).hexdigest())
                    for stream in ('stdout', 'stderr'):
                        path = command_file.with_name(record['stage'] + '.' + stream)
                        self.assertEqual(record[stream + '_sha256'], runner.file_sha256(path))
                        self.assertEqual(record[stream + '_bytes'], path.stat().st_size)
                private_bytes = b''.join(path.read_bytes() for path in private_root.rglob('*') if path.is_file())
                self.assertIn(b'PRIVATE_DIAGNOSTIC', private_bytes)
                self.assertEqual(private_commands, fixture.commands)
                self.assertTrue(any(command[:3] == [sys.executable,
                    str(fixture.root / 'compiler' / 'ru'), 'build'] for command in private_commands))
                private_paths = [fixture.root, sys.executable]
                for source in fixture.prepared:
                    private_paths.extend((source, source.parent))
                for command in private_commands:
                    for arg in command:
                        path = Path(arg)
                        if path.is_absolute():
                            private_paths.append(path)
                            if path.suffix == '.ru':
                                private_paths.append(path.parent)
                for path in public.iterdir():
                    self.assertIn(path.suffix, ('.json', '.log'))
                    data = path.read_bytes()
                    self.assertNotIn(b'PRIVATE_', data)
                    assert_public_hides_paths(self, data, path.suffix, private_paths)
                    self.assertNotIn(b'\r', data)
                if which == 'i18n':
                    source, = private_root.glob('*/catalog_exact.ru')
                    self.assertEqual(report['catalog_exact_source_sha256'], runner.file_sha256(source))
                    self.assertIn('中文', source.read_text(encoding='utf-8'))
                    self.assertNotIn(b'\r', source.read_bytes())
                else:
                    for kind, hashes in report['fixture_source_sha256'].items():
                        record = next(item for item in report['commands'] if item['stage'] == kind + '-interpreter')
                        command_file, = private_root.glob('*/' + record['stage'] + '.command.json')
                        for name, digest in hashes.items():
                            self.assertEqual(digest, runner.file_sha256(command_file.parent / 'fixture' / name))

    def test_both_runners_reject_source_mutation_and_do_not_publish_pass(self):
        for which in ('i18n', 'warnings'):
            with self.subTest(which=which), sandbox() as fixture:
                def mutate(command):
                    if 'build' in command:
                        path = fixture.root / 'src/i18n_catalog.ru'
                        path.write_bytes(path.read_bytes() + b'# changed\n')
                fixture.on_command = mutate
                with self.assertRaises(RuntimeError):
                    self.run_fixture(fixture, which)
                report = json.loads((fixture.root / ('public-' + which) / 'report.json').read_text())
                self.assertFalse(report['passed'])
                self.assertIn('error', report)

    def test_both_runners_reject_changed_compiler_receipt(self):
        for which, module in (('i18n', runner), ('warnings', warning)):
            with self.subTest(which=which), sandbox() as fixture, \
                    patch.object(module, 'compiler_snapshot', side_effect=[PIN, dict(PIN, tree='changed')]):
                with self.assertRaises(RuntimeError):
                    self.run_fixture(fixture, which)
                report = json.loads((fixture.root / ('public-' + which) / 'report.json').read_text())
                self.assertFalse(report['passed'])

    def test_generated_fixture_hashes_cannot_change_after_compilation(self):
        for which in ('i18n', 'warnings'):
            with self.subTest(which=which), sandbox() as fixture:
                def mutate(command):
                    executable = Path(command[0])
                    if len(command) == 1 and executable.stem in ('catalog_exact', 'probe'):
                        source = executable.with_suffix('.ru')
                        source.write_bytes(source.read_bytes() + b'# changed after compilation\n')
                fixture.on_command = mutate
                with self.assertRaises(RuntimeError):
                    self.run_fixture(fixture, which)
                report = json.loads((fixture.root / ('public-' + which) / 'report.json').read_text())
                self.assertFalse(report['passed'])

    def test_cleanup_failure_preserves_active_fixture_for_both_runners(self):
        for which in ('i18n', 'warnings'):
            with self.subTest(which=which), sandbox() as fixture:
                active = fixture.root / 'active-fixture'
                active.mkdir()
                with patch.object(tempfile, 'mkdtemp', return_value=str(active)), \
                        patch.object(runner, 'checked_run', side_effect=runner.CleanupError('cleanup failed')), \
                        patch.object(warning, 'checked_run', side_effect=runner.CleanupError('cleanup failed')):
                    with self.assertRaises(runner.CleanupError):
                        self.run_fixture(fixture, which)
                self.assertTrue(active.is_dir())
                self.assertTrue(list(active.glob('*.ru')))
                report = json.loads((fixture.root / ('public-' + which) / 'report.json').read_text())
                self.assertFalse(report['passed'])

    def test_workflow_uploads_only_validated_public_receipts_and_assertions(self):
        workflow = (ROOT / '.github/workflows/windows.yml').read_text(encoding='utf-8')
        for private in ('i18n-policy-private', 'syntax-warning-private', 'syntax-warning-evidence/*.stdout',
                        'syntax-warning-evidence/*.stderr', 'i18n-policy-evidence/catalog_exact.ru'):
            self.assertNotIn(private, workflow)
        for public in ('build/i18n-policy-evidence', 'build/windows-ci/i18n-policy-evidence'):
            self.assertIn(public + '/report.json', workflow)
            self.assertIn(public + '/*.log', workflow)
            self.assertNotIn(public + '/*\n', workflow)
            self.assertNotIn(public + '/**', workflow)

    def test_cli_failures_never_echo_unhandled_private_source_paths(self):
        with tempfile.TemporaryDirectory(prefix='PRIVATE_PATH_SENTINEL-') as temporary:
            missing = str(Path(temporary) / 'missing-compiler')
            for name in ('tools/test_i18n.py', 'tests/syntax_warning_portable.py'):
                with self.subTest(name=name):
                    result = subprocess.run([sys.executable, '-I', '-B', str(ROOT / name),
                                             '--ru-root', missing], capture_output=True, timeout=30)
                    self.assertEqual(result.returncode, 1)
                    self.assertNotIn(b'PRIVATE_PATH_SENTINEL', result.stdout + result.stderr)
                    self.assertNotIn(str(ROOT).encode(), result.stdout + result.stderr)
                    self.assertNotIn(b'Traceback', result.stderr)

    def test_preexisting_public_directory_is_rejected_without_overwriting(self):
        for which in ('i18n', 'warnings'):
            with self.subTest(which=which), sandbox() as fixture:
                public = fixture.root / ('public-' + which)
                public.mkdir()
                (public / 'report.json').write_text('existing receipt\n')
                with self.assertRaises(FileExistsError):
                    self.run_fixture(fixture, which)
                self.assertEqual((public / 'report.json').read_text(), 'existing receipt\n')


class SerializationContracts(unittest.TestCase):
    PATHS = (
        r'C:\Users\测试 User 📝\private work',
        r'\\server\共享 Folder\private work',
        '/tmp/测试 User/private work',
    )

    def test_private_argv_roundtrips_windows_unicode_spaces_and_json_newlines(self):
        for root in self.PATHS:
            expected = [r'C:\Program Files\Python\python.exe', root + r'\compiler\ru',
                        'build', root + r'\源文件 with spaces.ru']
            for ascii_only in (False, True):
                for newline in ('\n', '\r\n'):
                    with self.subTest(root=root, ascii_only=ascii_only, newline=newline):
                        data = (json.dumps(expected, ensure_ascii=ascii_only, indent=2) + '\n')
                        data = data.replace('\n', newline).encode('utf-8')
                        self.assertEqual(command_arguments(data), expected)
        for invalid in ('{}', 'null', '[]', '["tool", 123]', '["tool", true]'):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                command_arguments(invalid)

    def test_public_json_rejects_escaped_private_paths_in_nested_values_and_keys(self):
        for root in self.PATHS:
            for ascii_only in (False, True):
                for newline in ('\n', '\r\n'):
                    for leaked in ({'commands': [{'argv': [root + r'\源文件.ru']}]},
                                   {root + r'\private key': {'passed': True}}):
                        data = (json.dumps(leaked, ensure_ascii=ascii_only, indent=2) + '\n')
                        data = data.replace('\n', newline).encode('utf-8')
                        with self.subTest(root=root, ascii_only=ascii_only, newline=newline), \
                                self.assertRaises(AssertionError):
                            assert_public_hides_paths(self, data, '.json', [root])
            assert_public_hides_paths(self, b'{"source":"src/i18n.ru","passed":true}\n', '.json', [root])

    def test_public_logs_reject_raw_and_json_escaped_private_paths(self):
        for root in self.PATHS:
            for text in (root, json.dumps(root, ensure_ascii=True), json.dumps(root, ensure_ascii=False)):
                with self.subTest(root=root, text=text), self.assertRaises(AssertionError):
                    assert_public_hides_paths(self, ('PASS: ' + text + '\n').encode(), '.log', [root])
            assert_public_hides_paths(self, b'PASS: synthetic assertion\n', '.log', [root])

    def test_both_report_writers_disable_windows_newline_translation(self):
        original = Path.write_text
        for which in ('i18n', 'warnings'):
            with self.subTest(which=which), sandbox() as fixture:
                observed = []
                def windows_write_text(path, text, *args, **kwargs):
                    if path.name == 'report.json':
                        observed.append(kwargs.get('newline'))
                        if kwargs.get('newline') is None:
                            text = text.replace('\n', '\r\n')
                        # Emulate Windows default translation on any host without
                        # translating twice when this control itself runs there.
                        kwargs['newline'] = ''
                    return original(path, text, *args, **kwargs)
                with patch.object(Path, 'write_text', autospec=True, side_effect=windows_write_text):
                    public = PublicationContracts().run_fixture(fixture, which)
                data = (public / 'report.json').read_bytes()
                self.assertEqual(observed, ['\n'])
                self.assertNotIn(b'\r', data)
                self.assertTrue(json.loads(data)['passed'])


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0], *REMAINING])
