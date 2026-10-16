#!/usr/bin/env python3
"""Pure-Ru rescue-scope regressions extracted from the actual application.

Runs ordinary Ru in the pinned interpreter and host-generated C. No 如:密,
Win32 imports, platform-guard overrides, or foreign calls are used. Native u64
bit guards and real context ownership remain Windows fixture obligations.
"""
import argparse
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--ru-root', type=Path, required=True)
parser.add_argument('--cc', default='gcc')
args, remaining = parser.parse_known_args()
RU_ROOT = args.ru_root.resolve()
sys.path.insert(0, str(RU_ROOT))
from rulang.frontend import parse
from rulang.interpreter import Interpreter


def function_source(path, name):
    source = path.read_text(encoding='utf-8')
    program = parse(source)
    matches = [i for i, n in enumerate(program)
               if n.kind == 'function' and n.data['name'] == name]
    if len(matches) != 1:
        raise AssertionError(f'{path}: expected exactly one {name} declaration')
    index = matches[0]
    first = program[index].token.line - 1
    last = program[index + 1].token.line - 1 if index + 1 < len(program) else None
    return ''.join(source.splitlines(keepends=True)[first:last])


def run_ru(source):
    output = io.StringIO()
    # Native capability remains disabled, including imports hidden in functions.
    with tempfile.TemporaryDirectory(prefix='ru-init-policy-') as directory:
        path = Path(directory) / 'probe.ru'
        path.write_text(source, encoding='utf-8')
        (path.parent / 'scanner_stub.ru').write_text(SCANNER_STUB, encoding='utf-8')
        Interpreter(stdout=output).execute(parse(source), source_path=path)
    return output.getvalue()


def run_c(source):
    with tempfile.TemporaryDirectory(prefix='ru-init-recovery-') as directory:
        path = Path(directory) / 'probe.ru'
        executable = Path(directory) / 'probe'
        path.write_text(source, encoding='utf-8')
        (path.parent / 'scanner_stub.ru').write_text(SCANNER_STUB, encoding='utf-8')
        built = subprocess.run([sys.executable, str(RU_ROOT / 'ru'), 'build',
                                '--cc', args.cc, str(path), '-o', str(executable)],
                               capture_output=True, text=True, timeout=120)
        if built.returncode:
            raise AssertionError(built.stdout + built.stderr)
        ran = subprocess.run([str(executable)], capture_output=True, text=True, timeout=30)
        if ran.returncode:
            raise AssertionError(ran.stdout + ran.stderr)
        return ran.stdout


def initialization_source():
    path = ROOT / 'src/ru_syntax.ru'
    source = function_source(path, '选择')
    first_anchor = "    初 取 {'lexical':空,"
    last_anchor = "    态 取 {'document':"
    if source.count(first_anchor) != 1 or source.count(last_anchor) != 1:
        raise AssertionError('production initialization anchors must be unique')
    first = source.index(first_anchor)
    last = source.index(last_anchor, first)
    # Preserve the real selection try/rescue and its direct module calls. Only
    # the scanner module is an ordinary Ru ownership model in these host tests.
    return ("词 取 外言 './scanner_stub.ru'.\n" + function_source(path, '_初始化失败')
            + '算 初始化探针:\n' + source[first:last] + '    得 初.\n法\n')


INITIALIZE = initialization_source()
# This control reproduces the scope problem with an ordinary Ru error. It does
# not simulate or claim to verify the native packed-head conversion.
ORIGINAL_SCOPE = """拒 取 假.
试 卒 'controlled ordinary error'.
救 因 拒 取 (因 为 句) 其 含 'controlled ordinary error'. 显 拒. 终
显 拒."""
SCANNER_STUB = """
_活 取 [0].
_模式 取 [0].
_见 取 [空,假].
算 设置 模式 为 数:
    _模式[0] 取 模式.
    _见[0] 取 空. _见[1] 取 假.
    得 空.
法
算 可用: 得 真. 法
算 初始化: 得 ''. 法
算 新状态:
    若 _模式[0] == 1 则 卒 'first step failed'. 然
    _活[0] 取 _活[0]+1.
    得 {'references':1,'native':'modeled bounded state'}.
法
算 复制状态 态:
    _见[0] 取 态.
    _见[1] 取 _活[0] == 1 且 态['references'] == 1.
    若 _模式[0] == 2 则 卒 'second step failed'. 然
    得 新状态.
法
算 释放 态:
    若 态 == 空 则 得 空. 然
    若 态['references'] != 1 则 卒 'double release'. 然
    态 其 增 'references' 0.
    态 其 增 'native' 空.
    _活[0] 取 _活[0]-1.
    得 空.
法
算 活数: 得 _活[0]. 法
算 见态: 得 _见[0]. 法
算 第二步: 得 _见[1]. 法
"""
HELPER_PROBE = """
算 确认 条件 为 事实 文 为 句:
    若 非 条件 则 卒 文. 然
    显 文.
    得 空.
法
词 其 设置 1.
初 取 初始化探针.
确认 (初['lexical'] == 空 且 (初['points'] 其 量) == 0 且 (词 其 活数) == 0) 'first failure owns no context'.
确认 (初['warning'] 其 含 'first step failed') 'first failure warning survives rescue'.
词 其 设置 2.
初 取 初始化探针.
确认 ((词 其 第二步) 且 (词 其 见态)['references'] == 0 且 (词 其 见态)['native'] == 空 且 (词 其 活数) == 0) 'second failure releases its context once'.
确认 (初['lexical'] == 空 且 (初['points'] 其 量) == 0) 'second failure cannot publish a released context'.
确认 ((初['warning'] 其 含 'second step failed') 且 (初['warning'] 其 含 'editable as plain text')) 'second failure warning survives rescue'.
词 其 设置 0.
初 取 初始化探针.
确认 (初['lexical'] != 空 且 (初['points'] 其 量) == 1 且 (词 其 活数) == 2 且 初['warning'] == '') 'successful initialization owns both roots'.
词 其 释放 初['lexical'].
词 其 释放 (初['points'])[0][1].
确认 ((词 其 活数) == 0) 'successful roots release independently'.
"""


def actual_fixture_rescue():
    path = ROOT / 'tests/ru_syntax_native.ru'
    source = path.read_text(encoding='utf-8')
    first_anchor, last_anchor = '    拒头 取 ', '    活前 取 '
    if source.count(first_anchor) != 1 or source.count(last_anchor) != 1:
        raise AssertionError('native fixture rejection anchors must be unique')
    first = source.index(first_anchor)
    last = source.index(last_anchor, first)
    probe = source[first:last]
    foreign_call = "原桥 其 _头数 ((密 其 u64) 其 值 '18446744073709551615')."
    if probe.count(foreign_call) != 1:
        raise AssertionError('expected exactly one native corrupt-head call')
    # Only the error producer is substituted. The live fixture's holder, rescue
    # message check, and final assertion execute unchanged on both backends.
    probe = probe.replace(foreign_call, "卒 'Ru scanner returned oversized event head bits.'.")
    return '次数 取 [0].\n' + function_source(path, '确认') + probe


class FailureRegressions(unittest.TestCase):
    def test_original_scalar_rescue_scope_interpreter(self):
        self.assertEqual(run_ru(ORIGINAL_SCOPE), '真\n假\n')

    def test_original_scalar_rescue_scope_generated_c(self):
        self.assertEqual(run_c(ORIGINAL_SCOPE), '真\n假\n')

    def test_actual_fixture_rescue_with_ordinary_error_interpreter(self):
        output = run_ru(actual_fixture_rescue())
        self.assertEqual(output, 'PASS: corrupt high event bits fail ordinarily before any lossy native conversion\n')

    def test_actual_fixture_rescue_with_ordinary_error_generated_c(self):
        self.assertEqual(run_c(actual_fixture_rescue()), run_ru(actual_fixture_rescue()))

    def test_actual_initialization_helper_interpreter(self):
        self.assertEqual(len(run_ru(INITIALIZE + HELPER_PROBE).splitlines()), 7)

    def test_actual_initialization_helper_generated_c(self):
        expected = run_ru(INITIALIZE + HELPER_PROBE)
        self.assertEqual(run_c(INITIALIZE + HELPER_PROBE), expected)


if __name__ == '__main__':
    result = unittest.main(argv=[sys.argv[0], *remaining], exit=False).result
    if not result.wasSuccessful() or result.testsRun != 6 or result.skipped:
        raise SystemExit(1)
    print('RU_SYNTAX_FAILURE_PORTABLE_PASS: 6')
