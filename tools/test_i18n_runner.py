#!/usr/bin/env python3
"""Host-side negative controls for the i18n and warning evidence runners.

No native-window claim: synthetic child processes exercise the real bounded
runner, receipt/publication path and failure cleanup. --ru-root additionally
checks the exact compiler identity, real production-function extraction and the
Markdown constructor/native-fixture field predicate in Python and generated C.
"""
from __future__ import annotations

import argparse
import ast
from contextlib import ExitStack, contextmanager, redirect_stdout
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
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
            self.assertIn('src/markdown_ascii_kernel.ru', warning_initial)
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

    def test_warning_snapshot_rejects_missing_kernel_dependency(self):
        with sandbox() as fixture:
            (fixture.root / 'src/markdown_ascii_kernel.ru').unlink()
            with self.assertRaises(RuntimeError):
                warning.source_snapshot()

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
                    self.assertTrue((directory / 'markdown_ascii_kernel.ru').is_file())
                    for path in directory.glob('*.ru'):
                        data = path.read_bytes()
                        self.assertEqual(data.decode('utf-8').encode('utf-8'), data)
                        if path.name in ('i18n.ru', 'i18n_catalog.ru', 'markdown_policy.ru',
                                         'markdown_ascii_kernel.ru'):
                            self.assertEqual(data, (ROOT / 'src' / path.name).read_bytes())
                        else:
                            self.assertNotIn(b'\r', data)
                    text = source.read_text(encoding='utf-8')
                    production = ROOT / ('src/ru_syntax.ru' if kind == 'ru' else 'src/markdown_syntax.ru')
                    for name in (('选择', '状态', '_失败') if kind == 'ru' else ('_统计', '撤销直属', '变化', '状态')):
                        self.assertIn(warning.function_source(production, name, parse), text)
                    parse(text)


# Independent approved constructor values, not inferred from the source under test.
# The policy's two nested arrays are deliberately checked element by element.
MARKDOWN_INITIAL_STATE = {
    'alive': True, 'chunk': '', 'chunks': 0, 'document': 'modeled-document',
    'eof': False, 'feed': 0, 'foldEnabled': True, 'generation': 37,
    'hwnd': 'synthetic-editor', 'identity': 1, 'inTick': False,
    'language': 'markdown', 'length': -1, 'lines': 0, 'maxChunkMs': 0,
    'maxPublish': 0, 'maxRanges': 0, 'maxRead': 0, 'maxTickMs': 0,
    'pending': True, 'phase': 'prepare',
    'policy': [0, False, False, [], -1, False, '', 0, '', 0, True, '', 0, '', 0,
               False, True, False, '', [False, False, False, False, False],
               False, True, False, 0],
    'published': 0, 'rangeIndex': 0, 'rangeOffset': 0, 'ranges': [],
    'readBytes': 0, 'readEnd': 0, 'registered': False, 'restart': 0,
    'revision': 4, 'thread': 'modeled-thread', 'warning': '',
    'warningArgs': [], 'warningRecovery': [],
}


def markdown_schema_keys(source):
    """Review the native fixture's fixed whitelist without deriving its oracle."""
    match = re.findall(r'^\s*期望键 取 (\[.*\])\.\s*$', source, re.M)
    if len(match) != 1:
        raise ValueError('Expected exactly one fixed Markdown field whitelist')
    keys = ast.literal_eval(match[0])
    expected = list(MARKDOWN_INITIAL_STATE)
    if keys != expected or len(keys) != 35 or len(set(keys)) != 35 or keys != sorted(keys):
        raise ValueError('Markdown field whitelist differs from the reviewed 35-field schema')
    return keys


def markdown_state_probe():
    """Exercise the native fixture's exact predicate on real constructed states."""
    names, lines = [], []

    def confirm(expression, name):
        names.append(name)
        lines.append(f"确认 ({expression}) '{name}'.")

    def initial_value(expression, value, label):
        if isinstance(value, list):
            confirm(f'{expression} 其 量 == {len(value)}', label + ' size')
            for index, item in enumerate(value):
                initial_value(f'({expression})[{index}]', item, label + f' item {index}')
        else:
            literal = ('真' if value else '假') if type(value) is bool else repr(value)
            confirm(f'{expression} == {literal}', label)

    lines.append("态 取 _建态 柄 37 4 'modeled-document'.")
    confirm('扫描字段完整 态', 'complete real constructor schema')
    for key, value in MARKDOWN_INITIAL_STATE.items():
        initial_value(f"态['{key}']", value, 'initial ' + key)
    # Build the same map in reverse insertion order; comparison must sort keys
    # rather than depending on hash buckets, insertion order or value identity.
    lines.append('反序 取 {}.')
    for key in reversed(MARKDOWN_INITIAL_STATE):
        lines.append(f"反序 其 增 '{key}' 态['{key}'].")
    confirm('扫描字段完整 反序', 'reverse insertion order is accepted')
    # Null is a legitimate value after cleanup. The schema is key membership,
    # not a non-null lookup test, and must never mutate the observed values.
    lines.append("反序 其 增 'policy' 空.")
    confirm("(扫描字段完整 反序) 且 反序['policy'] == 空",
            'null value retains a present key')
    for key in MARKDOWN_INITIAL_STATE:
        lines.append(f"原值 取 态['{key}']. 态 其 除 '{key}'.")
        confirm('非 (扫描字段完整 态)', 'missing key ' + key)
        lines.append("态 其 增 'unexpectedCapability' 原值.")
        confirm('态 其 量 == 35 且 非 (扫描字段完整 态)',
                'same-size foreign-key replacement ' + key)
        lines.append(f"态 其 增 '{key}' 原值.")
        confirm('非 (扫描字段完整 态)', 'extra key beside ' + key)
        lines.append("态 其 除 'unexpectedCapability'.")
        confirm('扫描字段完整 态', 'restored key ' + key)
    # Each constructor owns fresh arrays; warning roots must not leak across
    # revisions, and capability/metric data must not be smuggled into the state.
    lines.append("另一 取 _建态 柄 37 5 'modeled-document'.")
    confirm("另一['identity'] == 2 且 另一['revision'] == 5 且 (扫描字段完整 另一)",
            'second constructor has fresh identity and same exact schema')
    for key in ('warningArgs', 'warningRecovery', 'ranges', 'policy'):
        confirm(f"态['{key}'] != 另一['{key}']", 'fresh array ' + key)
    lines.append("显 'TOTAL PASS: '+(次数[0] 为 句).")
    return '\n'.join(lines) + '\n', names


class MarkdownStateContracts(unittest.TestCase):
    def test_native_whitelist_is_exact_sorted_and_preserves_original_bounds(self):
        source = (ROOT / 'tests/markdown_direct_native.ru').read_text(encoding='utf-8')
        keys = markdown_schema_keys(source)
        self.assertEqual(keys, list(MARKDOWN_INITIAL_STATE))
        self.assertIn("且 态['maxRead'] <= 1024 且 态['maxPublish'] <= 64 且 态['maxRanges'] <= 64)",
                      source)
        self.assertIn("(扫描字段完整 ((折 其 _编辑们) 其 查 (甲 其 句)))", source)

    def test_every_whitelist_missing_extra_duplicate_replacement_and_reordering_fails(self):
        source = (ROOT / 'tests/markdown_direct_native.ru').read_text(encoding='utf-8')
        keys = markdown_schema_keys(source)
        for index, key in enumerate(keys):
            for mode in ('missing', 'extra', 'duplicate', 'replacement', 'reordered'):
                changed = list(keys)
                if mode == 'missing':
                    del changed[index]
                elif mode == 'extra':
                    changed.insert(index, 'unexpectedCapability')
                elif mode == 'duplicate':
                    changed[index] = keys[(index + 1) % len(keys)]
                elif mode == 'replacement':
                    changed[index] = 'unexpectedCapability'
                else:
                    following = (index + 1) % len(keys)
                    changed[index], changed[following] = changed[following], changed[index]
                mutated = re.sub(r'^(\s*期望键 取 )\[.*\](\.\s*)$',
                                 lambda match: match[1] + repr(changed) + match[2], source, flags=re.M)
                with self.subTest(key=key, mode=mode), self.assertRaises(ValueError):
                    markdown_schema_keys(mutated)

    @unittest.skipUnless(ARGS.ru_root, 'pass --ru-root for actual constructor Python/C execution')
    def test_actual_constructor_and_native_schema_predicate_in_both_backends(self):
        compiler = ARGS.ru_root.resolve()
        self.assertEqual(runner.compiler_snapshot(compiler), PIN)
        inputs = (ROOT / 'src/markdown_syntax.ru', ROOT / 'src/markdown_policy.ru',
                  ROOT / 'tests/markdown_direct_native.ru', Path(__file__).resolve(),
                  ROOT / 'src/markdown_ascii_kernel.ru')
        before = {str(path): runner.file_sha256(path) for path in inputs}
        with patch.object(sys, 'path', [str(compiler), *sys.path]):
            from rulang.frontend import parse
            constructor = warning.function_source(inputs[0], '_建态', parse)
            schema = warning.function_source(inputs[2], '扫描字段完整', parse)
        markdown_schema_keys(schema)
        probe, names = markdown_state_probe()
        directory = Path(tempfile.mkdtemp(prefix='markdown-state-private-')).resolve()
        cleanup_allowed = True
        passed = False
        commands = []
        try:
            shutil.copyfile(inputs[1], directory / 'markdown_policy.ru')
            shutil.copyfile(inputs[4], directory / 'markdown_ascii_kernel.ru')
            (directory / 'handle_stub.ru').write_text("句 取 'synthetic-editor'.\n",
                                                    encoding='utf-8', newline='\n')
            source = directory / 'probe.ru'
            source.write_text(
                "策 取 外言 './markdown_policy.ru'.\n柄 取 外言 './handle_stub.ru'.\n"
                "_身份 取 [0]. 次数 取 [0].\n算 _线程: 得 'modeled-thread'. 法\n"
                "作 确认 条件 为 事实 文 为 句:\n"
                "    若 非 条件 则 卒 ('FAIL: '+文). 然\n"
                "    次数[0] 取 次数[0]+1. 显 'PASS: '+文.\n为\n" +
                constructor + schema + probe, encoding='utf-8', newline='\n')
            executable = directory / ('probe.exe' if os.name == 'nt' else 'probe')
            build = [sys.executable, str(compiler / 'ru'), 'build', '--cc', 'gcc',
                     str(source), '--emit-c', str(directory / 'probe.c'), '-o', str(executable)]
            outputs = []
            outputs.append(runner.checked_run(
                [sys.executable, str(compiler / 'ru'), 'run', str(source)],
                directory, 'interpreter', 30, commands))
            contract = runner.prepare_compile_diagnostics(build, compiler, source)
            runner.checked_run(build, directory, 'build', 120, commands,
                               compile_diagnostics=contract)
            outputs.append(runner.checked_run([str(executable)], directory, 'host-c', 30, commands))
            for output in outputs:
                runner.verify_output(output, len(names), names)
            self.assertEqual(outputs[0].replace(b'\r\n', b'\n'),
                             outputs[1].replace(b'\r\n', b'\n'))
            self.assertEqual(before, {str(path): runner.file_sha256(path) for path in inputs})
            self.assertEqual(runner.compiler_snapshot(compiler), PIN)
            passed = True
        except runner.CleanupError:
            cleanup_allowed = False
            raise
        finally:
            # Retain actual generated source/C and raw execution evidence only in
            # the private ignored build tree, never a public upload allowlist.
            evidence = ROOT / 'build/markdown-state-private' / directory.name
            shutil.copytree(directory, evidence)
            receipt = {
                'passed': passed,
                'compiler': dict(PIN),
                'source_sha256': {Path(path).relative_to(ROOT).as_posix(): digest
                                  for path, digest in before.items()},
                'evidence_sha256': {path.name: runner.file_sha256(path)
                                    for path in sorted(directory.iterdir()) if path.is_file()},
                'assertions_per_backend': len(names),
                'commands': commands,
                'native_windows_executed': False,
            }
            (evidence / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n',
                                                  encoding='utf-8', newline='\n')
            if cleanup_allowed:
                shutil.rmtree(directory)


def validate_layout_fixture(source):
    callback = source.split('算 布局子过程 ', 1)[1].split('\n法', 1)[0]
    forward = "果 取 窗 其 结果 (_DefSubclassProc 其 调用 [柄,消息,宽,长])."
    if callback.count(forward) != 1 or callback.index(forward) > callback.index("若 消息 其 数 == 36 则"):
        raise ValueError('The production window procedure must run first')
    required = (
        "(柄 其 句) != ((_布局钩 其 查 'window') 其 句)",
        "(_IsWindowVisible 其 调用 [柄])",
        "(矩 其 读 'minTrackX') 其 数 != 640",
        "(矩 其 读 'minTrackY') 其 数 != 400",
        "布局上限 ((矩 其 读 'maxTrackX') 其 数) ((矩 其 读 'maxTrackY') 其 数)",
        "((窗 其 RtlMoveMemory) 其 调用 [指,矩,((窗 其 MINMAXINFO) 其 大小)])",
        "得 果.",
    )
    if any(fragment not in callback for fragment in required):
        raise ValueError('Missing test-owned hidden-window guard or native forwarding')
    if re.findall(r"矩 其 写 '([^']+)'", callback) != ['maxTrackX', 'maxTrackY']:
        raise ValueError('Only maximum tracking dimensions may be changed')
    install = source.split('作 装布局钩 ', 1)[1].split('\n为', 1)[0]
    remove = source.split('算 卸布局钩:', 1)[1].split('\n法', 1)[0]
    if ("(_IsWindowVisible 其 调用 [主])" not in install or
            install.index("_布局钩 其 增 'callback' 回调") > install.index('_SetWindowSubclass') or
            "窗 其 成功 (_SetWindowSubclass" not in install or
            "窗 其 成功 (_RemoveWindowSubclass" not in remove or
            remove.index('_RemoveWindowSubclass') > remove.index('回调 其 关闭.')):
        raise ValueError('Missing callback lifetime or installation/removal checks')
    if any(f'验布局 主 {width} 代码.' not in source for width in (640, 900, 1600)):
        raise ValueError('Original exact layout widths must remain covered')
    if "内[2]-内[0] == 宽 且 内[3]-内[1] >= 400" not in source or "若 次数[0] != 1606" not in source:
        raise ValueError('Native dimensions and assertion count may not be weakened')
    if "    卸布局钩.\n    确认 (应用 其 关程序)" not in source or "试 卸布局钩. 救 清因" not in source:
        raise ValueError('Both ordinary and failure cleanup must detach the callback')


class LayoutFixtureContracts(unittest.TestCase):
    def test_fixture_is_hidden_owned_forwarded_and_keeps_all_dimensions(self):
        validate_layout_fixture((ROOT / 'tests/app_i18n_native.ru').read_text(encoding='utf-8'))
        production = (ROOT / 'src/main.ru').read_text(encoding='utf-8')
        self.assertNotIn("矩 其 写 'maxTrackX'", production)
        self.assertNotIn("矩 其 写 'maxTrackY'", production)

    def test_weakened_scope_fields_lifetime_and_widths_are_rejected(self):
        source = (ROOT / 'tests/app_i18n_native.ru').read_text(encoding='utf-8')
        changes = (
            ("矩 其 写 'maxTrackX' 限[0]", "矩 其 写 'minTrackX' 限[0]"),
            ("矩 其 写 'maxTrackY' 限[1]", "矩 其 写 'minTrackY' 限[1]"),
            ("(_IsWindowVisible 其 调用 [柄])", "(_IsWindowVisible 其 调用 [空])"),
            ("(柄 其 句) != ((_布局钩 其 查 'window') 其 句)", "假"),
            ("其 数 != 640", "其 数 != 600"),
            ("其 数 != 400", "其 数 != 300"),
            ("_布局钩 其 增 'callback' 回调.", "_布局钩 其 增 'other' 回调."),
            ("窗 其 成功 (_RemoveWindowSubclass", "窗 其 结果 (_RemoveWindowSubclass"),
            ("验布局 主 1600 代码.", "验布局 主 1000 代码."),
            ("内[2]-内[0] == 宽", "内[2]-内[0] <= 宽"),
            ("若 次数[0] != 1606", "若 次数[0] != 182"),
            ("    卸布局钩.\n    确认 (应用 其 关程序)", "    确认 (应用 其 关程序)"),
        )
        for before, after in changes:
            with self.subTest(before=before), self.assertRaises(ValueError):
                validate_layout_fixture(source.replace(before, after))
        forward = "    果 取 窗 其 结果 (_DefSubclassProc 其 调用 [柄,消息,宽,长]).\n"
        delayed = source.replace(forward, '').replace("    得 果.\n法\n作 装布局钩", forward + "    得 果.\n法\n作 装布局钩")
        with self.assertRaises(ValueError):
            validate_layout_fixture(delayed)

    @unittest.skipUnless(ARGS.ru_root, 'pass --ru-root for actual fixture maximum-track policy execution')
    def test_actual_fixture_maximum_policy_in_both_backends(self):
        compiler = ARGS.ru_root.resolve()
        self.assertEqual(runner.compiler_snapshot(compiler), PIN)
        fixture = ROOT / 'tests/app_i18n_native.ru'
        before = runner.file_sha256(fixture)
        with patch.object(sys, 'path', [str(compiler), *sys.path]):
            from rulang.frontend import parse
            policy = warning.function_source(fixture, '布局上限', parse)
        cases = ((1044, 788), (4095, 4095), (4096, 4096), (4097, 4097),
                 (9000, 16000), (100, 9000), (16000, 100), (0, 0), (-1, 1))
        lines = ["次数 取 [0].", "作 确认 条件 为 事实 文 为 句:",
                 "    若 非 条件 则 卒 ('FAIL: '+文). 然",
                 "    次数[0] 取 次数[0]+1. 显 'PASS: '+文.", "为"]
        names = []
        for index, (width, height) in enumerate(cases):
            name = f'maximum tracking policy case {index}'
            names.append(name)
            lines.extend((f'果 取 布局上限 ({width}) ({height}).',
                          f"确认 (果[0] == {max(width, 4096)} 且 果[1] == {max(height, 4096)}) '{name}'."))
        lines.append("显 'TOTAL PASS: '+(次数[0] 为 句).")
        directory = Path(tempfile.mkdtemp(prefix='i18n-layout-private-')).resolve()
        commands = []
        passed = False
        cleanup_allowed = True
        try:
            source = directory / 'probe.ru'
            source.write_text(policy + '\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
            executable = directory / ('probe.exe' if os.name == 'nt' else 'probe')
            build = [sys.executable, str(compiler / 'ru'), 'build', '--cc', 'gcc',
                     str(source), '--emit-c', str(directory / 'probe.c'), '-o', str(executable)]
            outputs = [runner.checked_run([sys.executable, str(compiler / 'ru'), 'run', str(source)],
                                          directory, 'interpreter', 30, commands)]
            contract = runner.prepare_compile_diagnostics(build, compiler, source)
            runner.checked_run(build, directory, 'build', 120, commands, compile_diagnostics=contract)
            outputs.append(runner.checked_run([str(executable)], directory, 'host-c', 30, commands))
            for output in outputs:
                runner.verify_output(output, len(names), names)
            self.assertEqual(before, runner.file_sha256(fixture))
            passed = True
        except runner.CleanupError:
            cleanup_allowed = False
            raise
        finally:
            evidence = ROOT / 'build/i18n-layout-private' / directory.name
            shutil.copytree(directory, evidence)
            (evidence / 'receipt.json').write_text(json.dumps({
                'passed': passed, 'assertions_per_backend': len(names),
                'fixture_sha256': before, 'compiler': dict(PIN), 'commands': commands,
                'evidence_sha256': {path.name: runner.file_sha256(path) for path in directory.iterdir() if path.is_file()},
                'native_windows_executed': False,
            }, indent=2) + '\n', encoding='utf-8', newline='\n')
            if cleanup_allowed:
                shutil.rmtree(directory)


@contextmanager
def sandbox():
    """Exercise real orchestration, file writes and receipts with tiny child tools."""
    with tempfile.TemporaryDirectory(prefix='i18n-proof-controls-') as temporary, ExitStack() as stack:
        root = Path(temporary).resolve()
        for name in ('src', 'tools', 'tests', 'locales', 'compiler/rulang'):
            (root / name).mkdir(parents=True, exist_ok=True)
        for name in ('i18n.ru', 'i18n_catalog.ru', 'markdown_policy.ru', 'markdown_ascii_kernel.ru',
                     'ru_native_syntax.ru',
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
        for private in ('i18n-policy-private', 'syntax-warning-private', 'markdown-state-private',
                        'syntax-warning-evidence/*.stdout',
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
