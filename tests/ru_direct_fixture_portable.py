#!/usr/bin/env python3
"""Exact direct-fixture call-boundary regressions on both ordinary Ru backends.

No native imports or platform overrides. Actual Win32 route/lifetime acceptance
remains the separate 36-assertion ru_direct_styling_native executable.
"""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--ru-root', type=Path, required=True)
parser.add_argument('--cc', default='gcc')
args = parser.parse_args()
ROOT = Path(__file__).resolve().parents[1]
RU_ROOT = args.ru_root.resolve()
sys.path.insert(0, str(RU_ROOT))
from rulang.frontend import parse

ORIGINAL_SPAN = "果 其 增 'spans' [[0,65,4]]."
ORIGINAL_FOLD = "果 其 增 'folds' [[999999,0,假]]."
BASE = "果 取 {'spans':[[0,3,4]],'folds':[[0,0,假]],'styleLength':87}.\n"


def exact_line(source, prefix):
    matches = [line.strip() for line in source.splitlines()
               if line.strip().startswith(prefix)]
    if len(matches) != 1:
        raise AssertionError(f'Expected one fixture statement: {prefix}')
    return matches[0]


def function_source(path, name):
    source = path.read_text(encoding='utf-8')
    program = parse(source)
    matches = [i for i, n in enumerate(program)
               if n.kind == 'function' and n.data['name'] == name]
    if len(matches) != 1:
        raise AssertionError(f'Expected one production function: {name}')
    i = matches[0]
    start = program[i].token.line - 1
    end = program[i + 1].token.line - 1 if i + 1 < len(program) else None
    return ''.join(source.splitlines(keepends=True)[start:end])


def verify_setter(statement, key, original):
    expected = original.replace(' [[', ' ([[').replace(']].', ']]).')
    if statement != expected:
        raise AssertionError('Current native fixture must retain the minimal parenthesized correction')
    member = parse(statement)[0].data['expr']
    if member.kind != 'member' or member.data['name'] != '增':
        raise AssertionError('Expected actual dictionary setter')
    values = [item[1] for item in member.data['args']]
    if len(values) != 2 or values[0].kind != 'string' or values[0].data['value'] != key or values[1].kind != 'array':
        raise AssertionError('Fixture setter must parse as separate literal key and array value')


def corrected_probe():
    fixture = (ROOT / 'tests/ru_direct_styling_native.ru').read_text(encoding='utf-8')
    span = exact_line(fixture, "果 其 增 'spans' (")
    fold = exact_line(fixture, "果 其 增 'folds' (")
    verify_setter(span, 'spans', ORIGINAL_SPAN)
    verify_setter(fold, 'folds', ORIGINAL_FOLD)
    source = function_source(ROOT / 'src/ru_syntax.ru', '_施样')
    end_anchor = '    若 非 (_存在 柄)'
    if source.count(end_anchor) != 1:
        raise AssertionError('Expected unique end of production validation region')
    fold_end = source.index(end_anchor)
    validation = source[:fold_end]
    anchors = ("    段们 取 结果['spans'].\n", "    折们 取 结果['folds'].\n", '    位 取 0.\n    循 折们')
    if any(validation.count(anchor) != 1 for anchor in anchors):
        raise AssertionError('Production span/fold validation anchors must be unique')
    start, middle, fold_start = [validation.index(anchor) for anchor in anchors]
    if not start < middle < fold_start < fold_end:
        raise AssertionError('Production span/fold guard order changed')
    # These exact blocks contain ordinary bounds policy only. The caller passes
    # modeled document length/line count; no HWND or native buffer is emulated.
    validator = ('算 验批 结果 长 为 数 行数 为 数:\n'
                 + source[start:middle] + "    折们 取 结果['folds'].\n"
                 + source[fold_start:fold_end] + '    得 真.\n法\n')
    if '窗 其' in validator or '如:密' in validator:
        raise AssertionError('Portable extraction must remain strictly ordinary Ru')
    before_span = '\n'.join(exact_line(fixture, prefix) for prefix in (
        "真长 取 果['styleLength'].", "果 其 增 'styleLength' (真长+1).",
        "果 其 增 'styleLength' 真长.", "原段 取 果['spans']."))
    restore_span = exact_line(fixture, "果 其 增 'spans' 原段.")
    before_fold = exact_line(fixture, "原折 取 果['folds'].")
    restore_fold = exact_line(fixture, "果 其 增 'folds' 原折.")
    check = """作 确认 条件 为 事实 文 为 句:
    若 非 条件 则 卒 文. 然
    显 'PASS: '+文.
为
"""
    return validator + check + BASE + before_span + '\n' + span + """
拒 取 [假].
试 验批 果 87 8. 救 原因 拒[0] 取 (原因 为 句) 其 含 'invalid byte-style correction'. 终
确认 (拒[0] 且 ((果['spans']) 其 量) == 1 且 (果['spans'])[0][0] == 0 且 (果['spans'])[0][1] == 65 且 (果['spans'])[0][2] == 4) 'actual production span guard rejects the exact stored length65 value ordinarily'.
""" + restore_span + """
确认 ((验批 果 87 8) 且 果['styleLength'] == 真长 且 (果['spans'])[0][1] == 3) 'actual fixture restoration preserves original span and styleLength'.
""" + before_fold + '\n' + fold + """
拒[0] 取 假.
试 验批 果 87 8. 救 原因 拒[0] 取 (原因 为 句) 其 含 'invalid fold level'. 终
确认 (拒[0] 且 ((果['folds']) 其 量) == 1 且 (果['folds'])[0][0] == 999999 且 (果['folds'])[0][1] == 0 且 非 (果['folds'])[0][2]) 'actual production fold guard rejects the exact stored line999999 value ordinarily'.
""" + restore_fold + """
确认 ((验批 果 87 8) 且 (果['folds'])[0][0] == 0) 'actual fixture restoration preserves original fold'.
"""


def run_source(source, native_c):
    with tempfile.TemporaryDirectory(prefix='ru-direct-call-') as directory:
        path = Path(directory) / 'probe.ru'
        path.write_text(source, encoding='utf-8', newline='\n')
        if native_c:
            executable = path.with_suffix('.exe' if sys.platform == 'win32' else '')
            build = subprocess.run([sys.executable, str(RU_ROOT / 'ru'), 'build',
                                    '--cc', args.cc, str(path), '-o', str(executable)],
                                   capture_output=True, text=True, encoding='utf-8', timeout=120)
            if build.returncode:
                raise AssertionError('host_compile_failed')
            command = [str(executable)]
        else:
            command = [sys.executable, str(RU_ROOT / 'ru'), 'run', str(path)]
        return subprocess.run(command, capture_output=True, text=True, encoding='utf-8', timeout=30)


def original(statement, native_c):
    result = run_source(BASE + statement + '\n', native_c)
    expected = '索引须为非负整数' if native_c else '索引须为整数'
    if result.returncode != 1 or result.stdout != '' or expected not in result.stderr:
        raise AssertionError('original_integer_index_failure_not_observed')


def corrected(native_c):
    result = run_source(corrected_probe(), native_c)
    if result.returncode != 0 or result.stderr != '':
        raise AssertionError('corrected_actual_statements_failed')
    expected = [
        'PASS: actual production span guard rejects the exact stored length65 value ordinarily',
        'PASS: actual fixture restoration preserves original span and styleLength',
        'PASS: actual production fold guard rejects the exact stored line999999 value ordinarily',
        'PASS: actual fixture restoration preserves original fold',
    ]
    if result.stdout.splitlines() != expected:
        raise AssertionError('four_actual_assertions_required')


def main():
    cases = [
        ('original span integer-index rejection in interpreter', lambda: original(ORIGINAL_SPAN, False)),
        ('original span integer-index rejection in generated C', lambda: original(ORIGINAL_SPAN, True)),
        ('original fold integer-index rejection in interpreter', lambda: original(ORIGINAL_FOLD, False)),
        ('original fold integer-index rejection in generated C', lambda: original(ORIGINAL_FOLD, True)),
        ('four actual fixture guard/restoration assertions in interpreter', lambda: corrected(False)),
        ('four actual fixture guard/restoration assertions in generated C', lambda: corrected(True)),
    ]
    passed = 0
    for label, case in cases:
        try:
            case()
        except Exception:
            # CI evidence contains only fixed synthetic labels, never raw paths,
            # compiler output, source text, or exception messages.
            print('FAIL: ' + label)
            return 1
        print('PASS: ' + label)
        passed += 1
    if passed != 6:
        print('FAIL: six direct-fixture regression cases are required')
        return 1
    print('RU_DIRECT_FIXTURE_PORTABLE_PASS: 6')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
