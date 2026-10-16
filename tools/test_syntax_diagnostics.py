#!/usr/bin/env python3
"""Execute the complete production numeric diagnostic with ordinary Ru stubs.

This checks control flow, fixed output and privacy in both Ru backends. It uses
no native import or platform override and does not claim Windows message proof.
"""
import argparse
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIELDS = ('seq ok generation revision pending bytes feed read_bytes restart chunks ticks '
          'work_ms gap_ms max_tick_ms max_gap_ms posts continuation_ticks queue_yields '
          'stale_messages text_notifications style_notifications fold_notifications').split()


def production_parts(ru_root):
    sys.path.insert(0, str(ru_root))
    from rulang.frontend import parse
    source = (ROOT / 'src/main.ru').read_text(encoding='utf-8')
    program = parse(source)
    matches = [i for i, node in enumerate(program)
               if node.kind == 'function' and node.data['name'] == '诊断语法']
    if len(matches) != 1:
        raise ValueError('Expected exactly one production diagnostic function')
    index = matches[0]
    start = program[index].token.line - 1
    stop = program[index + 1].token.line - 1
    function = ''.join(source.splitlines(keepends=True)[start:stop])
    if (function.count("语 其 状态") != 1 or function.count("显 'RU_GUI_SNAPSHOT seq='") != 2
            or function.count("A 其 增 'syntaxSnapshots' 序.") != 1):
        raise ValueError('Diagnostic extraction anchors changed; review the complete function')
    initial = re.findall(r'^A 取 \{.*\}\.\s*$', source, re.M)
    if len(initial) != 1 or len(parse(initial[0])) != 1:
        raise ValueError('Expected one standalone initial application state')
    return initial[0], function


STUB = """_调用 取 [0].
_方式 取 [0].
算 设置 方式 为 数: _方式[0] 取 方式. 得 空. 法
算 次数: 得 _调用[0]. 法
算 状态 柄:
    _调用[0] 取 _调用[0]+1.
    若 柄 != 17 则 卒 'unexpected handle'. 然
    若 _方式[0] == 1 则 卒 'PRIVATE_ERROR_SENTINEL'. 然
    若 _方式[0] == 2 则 得 空. 然
    得 {'generation':9,'revision':2,'pending':_方式[0] == 0,'bytes':123,'feed':124,'readBytes':128,'restart':0,'chunks':4,'warning':'PRIVATE_WARNING_SENTINEL','language':'PRIVATE_LANGUAGE_SENTINEL','body':'PRIVATE_BODY_SENTINEL'}.
法
"""
PROBE = """
次数 取 [0].
算 确认 条件 为 事实 文 为 句:
    若 非 条件 则 卒 ('FAIL: '+文). 然
    次数[0] 取 次数[0]+1.
    显 'PASS: '+文.
    得 空.
法
A 其 增 'docs' ([{'editor':17,'body':'PRIVATE_BODY_SENTINEL'}]).
A 其 增 'active' 0.
诊断语法.
A 其 增 'ready' 真. A 其 增 'busy' 真.
诊断语法.
A 其 增 'busy' 假. A 其 增 'syntaxTick' 真.
诊断语法.
A 其 增 'syntaxTick' 假. A 其 增 'active' (-1).
诊断语法.
A 其 增 'active' 1.
诊断语法.
确认 ((语 其 次数) == 0 且 (A 其 查 'syntaxSnapshots') == 0) 'all guards reject before projection or cap reservation'.
A 其 增 'active' 0.
A 其 增 'syntaxTicks' 5. A 其 增 'syntaxWorkMs' 1.5. A 其 增 'syntaxGapMs' 2.25.
A 其 增 'syntaxMaxTickMs' 0.75. A 其 增 'syntaxMaxGapMs' 1.25.
A 其 增 'syntaxPosts' 7. A 其 增 'syntaxContinuations' 6. A 其 增 'syntaxYields' 8.
A 其 增 'syntaxStale' 1. A 其 增 'syntaxTextNotifications' 3.
A 其 增 'syntaxStyleNotifications' 0. A 其 增 'syntaxFoldNotifications' 0.
诊断语法.
确认 ((语 其 次数) == 1 且 (A 其 查 'syntaxSnapshots') == 1) 'successful projection reserves exactly one slot'.
确认 ((A 其 查 'syntaxTicks') == 5 且 (A 其 查 'syntaxWorkMs') == 1.5 且 (A 其 查 'syntaxPosts') == 7) 'projection does not advance work counters'.
语 其 设置 1.
诊断语法.
确认 ((语 其 次数) == 2 且 (A 其 查 'syntaxSnapshots') == 2) 'ordinary projection failure consumes a slot and returns'.
确认 (((A 其 查 'errors') 其 量) == 0) 'diagnostic failure does not enter user error handling'.
语 其 设置 3.
诊断语法.
确认 ((语 其 次数) == 3 且 (A 其 查 'syntaxSnapshots') == 3) 'projection succeeds after an ordinary failure'.
诊断语法. 诊断语法.
确认 ((语 其 次数) == 3 且 (A 其 查 'syntaxSnapshots') == 3) 'fixed per-process cap stops further projection calls'.
确认 (((A 其 查 'docs')[0] 其 查 'body') == 'PRIVATE_BODY_SENTINEL') 'document model stays unchanged'.
# Separate synthetic state tests the ordinary empty-projection branch.
A 其 增 'syntaxSnapshots' 0. 语 其 设置 2.
诊断语法.
确认 ((语 其 次数) == 4 且 (A 其 查 'syntaxSnapshots') == 1) 'empty projection also consumes one bounded slot'.
确认 ((A 其 查 'ready') 且 非 (A 其 查 'busy') 且 非 (A 其 查 'syntaxTick') 且 ((A 其 查 'errors') 其 量) == 0) 'empty projection leaves ordinary application state available'.
显 'TOTAL PASS: '+(次数[0] 为 句).
"""


def validate(output):
    lines = [line for line in output.splitlines() if line.startswith('RU_GUI_SNAPSHOT ')]
    base = dict(zip(FIELDS, [1, 1, 9, 2, 1, 123, 124, 128, 0, 4, 5,
                            1.5, 2.25, 0.75, 1.25, 7, 6, 8, 1, 3, 0, 0]))
    expected = [base, {'seq': 2, 'ok': 0}, {**base, 'seq': 3, 'pending': 0}, {'seq': 1, 'ok': 0}]
    if len(lines) != 4:
        raise ValueError('Expected four bounded diagnostic lines from both synthetic states')
    for line, wanted in zip(lines, expected):
        fields = line.split()[1:]
        parsed = {}
        for field in fields:
            key, value = field.split('=')
            if key in parsed or not re.fullmatch(r'[0-9]+(?:\.[0-9]+)?', value):
                raise ValueError('Unexpected duplicate or nonnumeric diagnostic output')
            parsed[key] = float(value)
        if parsed != wanted or list(parsed) != list(wanted):
            raise ValueError(f'Diagnostic schema/value mismatch: {parsed}')
    if ('PRIVATE_' in output or re.search(r'^(FAIL:|SKIP:)', output, re.M)
            or len(re.findall(r'^PASS:', output, re.M)) != 10
            or re.findall(r'^TOTAL PASS: ([0-9]+)$', output, re.M) != ['10']):
        raise ValueError('Incomplete control-flow assertions or private diagnostic data')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ru-root', type=pathlib.Path, required=True)
    args = parser.parse_args()
    ru_root = args.ru_root.resolve()
    initial, function = production_parts(ru_root)
    directory = ROOT / 'build/diagnostic-control'
    directory.mkdir(parents=True, exist_ok=True)
    source = directory / 'production-diagnostic.ru'
    source.write_text("语 取 外言 './projection_stub.ru'.\n" + initial + '\n' + function + PROBE, encoding='utf-8')
    (directory / 'projection_stub.ru').write_text(STUB, encoding='utf-8')
    executable = directory / 'production-diagnostic'
    outputs = []
    for backend, command in (
        ('python', [sys.executable, str(ru_root / 'ru'), 'run', str(source)]),
        ('build', [sys.executable, str(ru_root / 'ru'), 'build', '--cc', 'gcc', str(source), '-o', str(executable)]),
        ('c', [str(executable)]),
    ):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=120 if backend == 'build' else 30)
        (directory / (backend + '.log')).write_text(result.stdout + result.stderr, encoding='utf-8')
        if result.returncode != 0 or result.stderr:
            raise RuntimeError(f'{backend} failed: {result.stdout}{result.stderr}')
        if backend != 'build':
            validate(result.stdout)
            outputs.append(result.stdout)
            print(f'BACKEND: {backend}\n{result.stdout}', end='')
    if outputs[0] != outputs[1]:
        raise ValueError('The two actual Ru backends disagree')
    print('RU_DIAGNOSTIC_PORTABLE_PASS: 2')


if __name__ == '__main__':
    main()
