#!/usr/bin/env python3
"""Run the unchanged production event decoder with ordinary Ru word snapshots.

This is arithmetic/control-flow evidence in the interpreter and host C backend.
The memory snapshot is an ordinary Ru module; no native import or platform guard
is replaced. Real owned-memory/member dispatch and old-u64 equality are covered
by tests/ru_syntax_native.ru and must execute on native Windows x64.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from ru_cli_diagnostics import prepare_compile_diagnostics, validate_stderr
BULK_EVENT_CASES = (
    'all 384 fields of the full batch',
    'near-32-MB exact metadata',
    'zero event batch',
    'delayed long identifier',
    'delayed 64-byte keyword',
    'equal event positions',
    'high word 131072',
    'high word 2147483648',
    'high word 4294967295',
    'last event high bits',
    'invalid count -1',
    'invalid count 0.5',
    'invalid count 65',
    'kind zero',
    'kind eight',
    'style ten',
    'zero length',
    'full unsigned length',
    'full unsigned line',
    'end beyond bytes',
    'non-token before start',
    'keyword length 65',
    'decreasing positions',
)


def function_source(path, name, parse):
    source = path.read_text(encoding='utf-8')
    program = parse(source)
    matches = [i for i, node in enumerate(program)
               if node.kind == 'function' and node.data['name'] == name]
    if len(matches) != 1:
        raise ValueError(f'Expected exactly one {name} in {path}')
    index = matches[0]
    first = program[index].token.line - 1
    last = program[index + 1].token.line - 1 if index + 1 < len(program) else None
    return ''.join(source.splitlines(keepends=True)[first:last])


STUB = """_字们 取 [[]].
_次数 取 [0].
算 设置 字们:
    _字们[0] 取 字们. _次数[0] 取 0. 得 空.
法
算 次数: 得 _次数[0]. 法
算 读U32LE阵 字节偏移 为 数 个数 为 数:
    若 字节偏移 != 0 或 个数 != (_字们[0] 其 量) 则 卒 'wrong snapshot request'. 然
    _次数[0] 取 _次数[0]+1.
    得 _字们[0].
法
"""


def words(events):
    """Independent integer encoding of the unchanged head/tail event layout."""
    result = []
    for kind, code, style, start, length, line in events:
        head = (start << 24) | (style << 16) | (code << 8) | kind
        result.extend((head & 0xffffffff, head >> 32, length, line))
    return result


def literal(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def probe_source(parse):
    bridge = ROOT / 'src/ru_native_syntax.ru'
    decoder = function_source(bridge, '_解事件', parse)
    scan = function_source(bridge, '扫描', parse)
    if decoder.count('存 其 读U32LE阵 0 (项数*4)') != 1:
        raise ValueError('Expected one production bulk snapshot call')
    if scan.count("事件们 取 _解事件 态['events'] 项数 始 字节 行.") != 1:
        raise ValueError('Production scanner must call the tested bulk decoder')
    if decoder.count("若 高 >= 131072 则 卒 'Ru scanner returned oversized event head bits.'. 然") != 1:
        raise ValueError('Expected exact high-word rejection before reconstruction')
    if decoder.index('若 高 >= 131072') > decoder.index('头数 取 字们[字位]+高*4294967296'):
        raise ValueError('High-word guard follows potentially lossy reconstruction')
    fixture = ROOT / 'tests/ru_syntax_native.ru'
    source = ("存 取 外言 './snapshot_words.ru'.\n次数 取 [0].\n" + decoder
              + function_source(fixture, '同事件', parse)
              + function_source(fixture, '确认', parse))
    full = [[i % 7 + 1, i * 47 % 256, i % 10, i * 128, i % 63 + 1, i]
            for i in range(64)]
    valid = [
        ('all 384 fields of the full batch', full, 0, 8192, 64),
        ('near-32-MB exact metadata', [[7, 255, 9, 31999999, 1, 0]], 0, 32000000, 0),
        ('zero event batch', [], 0, 0, 0),
        ('delayed long identifier', [[1, 0, 8, 0, 100, 0]], 32, 100, 0),
        ('delayed 64-byte keyword', [[1, 0, 4, 0, 64, 0]], 32, 100, 0),
        ('equal event positions', [[2, 0, 0, 10, 1, 0], [3, 0, 0, 10, 1, 0]], 0, 100, 0),
    ]
    for label, events, start, end, line in valid:
        source += f"存 其 设置 ({literal(words(events))}).\n"
        source += f"成果 取 _解事件 存 {len(events)} {start} {end} {line}.\n"
        source += f"确认 ((同事件 成果 ({literal(events)})) 且 (存 其 次数) == 1) '{label}'.\n"
    invalid = []
    for high in (131072, 2147483648, 4294967295):
        invalid.append((f'high word {high}', [1, high, 1, 0], 1, 0, 32000000, 0, 'oversized event head bits', 1))
    last = words(full)
    last[-3] = 131072
    invalid.append(('last event high bits', last, 64, 0, 8192, 64, 'oversized event head bits', 1))
    for count in (-1, 0.5, 65):
        invalid.append((f'invalid count {count}', [], count, 0, 8192, 64, 'invalid batch size', 0))
    for label, event, start in (
        ('kind zero', [0, 0, 0, 0, 1, 0], 0),
        ('kind eight', [8, 0, 0, 0, 1, 0], 0),
        ('style ten', [2, 0, 10, 0, 1, 0], 0),
        ('zero length', [2, 0, 0, 0, 0, 0], 0),
        ('full unsigned length', [2, 0, 0, 0, 4294967295, 0], 0),
        ('full unsigned line', [2, 0, 0, 0, 1, 4294967295], 0),
        ('end beyond bytes', [2, 0, 0, 100, 1, 0], 0),
        ('non-token before start', [2, 0, 0, 0, 1, 0], 1),
        ('keyword length 65', [1, 0, 4, 0, 65, 0], 0),
    ):
        invalid.append((label, words([event]), 1, start, 100, 0, 'invalid lexical event', 1))
    invalid.append(('decreasing positions', words([[2, 0, 0, 10, 1, 0], [2, 0, 0, 9, 1, 0]]),
                    2, 0, 100, 0, 'unordered lexical events', 1))
    for label, snapshot, count, start, end, line, message, calls in invalid:
        source += f"存 其 设置 ({literal(snapshot)}).\n拒 取 [假].\n"
        source += f"试 _解事件 存 ({count}) {start} {end} {line}.\n"
        source += f"救 原因 拒[0] 取 (原因 为 句) 其 含 '{message}'. 终\n"
        source += f"确认 (拒[0] 且 (存 其 次数) == {calls}) '{label}'.\n"
    total = len(valid) + len(invalid)
    source += "显 'TOTAL PASS: '+(次数[0] 为 句).\n"
    return source, total


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ru-root', type=Path, required=True)
    parser.add_argument('--cc', default='gcc')
    args = parser.parse_args()
    ru_root = args.ru_root.resolve()
    sys.path.insert(0, str(ru_root))
    from rulang.frontend import parse
    source, count = probe_source(parse)
    directory = ROOT / 'build/bulk-candidate/portable'
    directory.mkdir(parents=True, exist_ok=True)
    probe = directory / 'production-event-decoder.ru'
    probe.write_text(source, encoding='utf-8')
    (directory / 'snapshot_words.ru').write_text(STUB, encoding='utf-8')
    executable = directory / 'production-event-decoder'
    outputs = []
    for backend, command in (
        ('python', [sys.executable, str(ru_root / 'ru'), 'run', str(probe)]),
        ('build', [sys.executable, str(ru_root / 'ru'), 'build', '--cc', args.cc, str(probe), '-o', str(executable)]),
        ('c', [str(executable)]),
    ):
        diagnostics = (prepare_compile_diagnostics(command, ru_root, probe)
                       if backend == 'build' else None)
        result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=120)
        (directory / (backend + '.stdout.log')).write_bytes(result.stdout)
        (directory / (backend + '.stderr.log')).write_bytes(result.stderr)
        (directory / (backend + '.log')).write_bytes(result.stdout + result.stderr)
        validate_stderr(command, result.returncode, result.stderr, diagnostics)
        stdout = result.stdout.decode('utf-8', 'strict').replace('\r\n', '\n')
        if backend != 'build':
            expected = ''.join(f'PASS: {label}\n' for label in BULK_EVENT_CASES) + 'TOTAL PASS: 23\n'
            if count != 23 or stdout != expected:
                raise ValueError(f'{backend}: incomplete or unexpected production decoder assertions')
            outputs.append(stdout)
            print(f'BACKEND: {backend}\n{stdout}', end='')
    if outputs[0] != outputs[1]:
        raise ValueError('Interpreter and host C output differ')
    print(f'RU_EVENT_BULK_PORTABLE_PASS: 2 backends, {count} assertions each')


if __name__ == '__main__':
    main()
