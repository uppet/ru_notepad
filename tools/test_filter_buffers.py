#!/usr/bin/env python3
"""Run the extracted production filter constructor with real owned memory.

POSIX uses the pinned compiler's existing portable test artifact adapter and a
single test-owned library loader. Neither production nor compiler is patched.
The bridge's unit/cluster traversal models are NOT User32 CharNextW or Windows
ABI/dialog acceptance. Windows GUI acceptance still uses actual User32.

NUL cannot be written in Ru source. Its negative control injects only the input:
Python replaces one parsed string node; C replaces one emitted sentinel with a
length-explicit string. Both then execute the actual constructor/UTF16 guard.
Detailed sources, build logs, outcomes and hashes stay in --output. Stdout is a
fixed-count summary suitable for private CI controls without localized output.
"""
import argparse
import ast
from contextlib import ExitStack
import ctypes as C
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ('en', 'zh-CN', 'ja', 'ko', 'es', 'ru', 'it')
NUL_SENTINEL = 'FILTER_PROBE_NUL_SENTINEL_64c32d'
NUL_TEXT = 'bad\0label'
FIELD_LIMIT = '结构需要 1 至 128 个字段的阵'
NUL_LIMIT = '原生文本需要不含 NUL 的句'
CLOSED = '原生缓冲已关闭'
EXPECTED_CASES = 27
EXPECTED_ASSERTIONS = 330


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def literal(value):
    return json.dumps(value, ensure_ascii=False)


def function(source, name):
    matches = list(re.finditer(r'^算 ' + re.escape(name) + r'(?=[ \t:])[^\n]*:\n.*?^法\n', source, re.M | re.S))
    if len(matches) != 1:
        raise AssertionError('Expected exactly one source function: ' + name)
    return matches[0].group(0)


def inject_python_nul(program):
    count = 0

    def visit(value):
        nonlocal count
        if isinstance(value, (list, tuple)):
            for item in value:
                visit(item)
        elif isinstance(value, dict):
            for item in value.values():
                visit(item)
        elif hasattr(value, 'kind') and hasattr(value, 'data'):
            if value.kind == 'string' and value.data['value'] == NUL_SENTINEL:
                value.data['value'] = NUL_TEXT
                count += 1
            visit(value.data)

    visit(program)
    assert count == 1, 'NUL input injection must replace exactly one string node'


def inject_c_nul(generated):
    target = 'v_str(' + literal(NUL_SENTINEL) + ')'
    assert generated.count(target) == 1, 'NUL input injection must replace exactly one emitted sentinel'
    # The marker is a top-level argument, and its generated call is in a module
    # initializer before main. Place the helper before the first module function.
    helper = '''\nstatic Val filter_probe_nul(void) {
    Val value = ru_string_alloc(9, 0);
    memcpy(value.s->data, "bad\\0label", 9);
    return value;
}\n'''
    position = generated.index(target)
    # Generated Ru function declarations follow the complete runtime, so the
    # test-only input factory can use Val/ru_string_alloc without altering them.
    anchor = re.search(r'^static Val ru_function_[0-9]+\(', generated, re.M)
    if not anchor or anchor.start() > position:
        raise AssertionError('Cannot place the test-only NUL-input factory')
    generated = generated[:anchor.start()] + helper + generated[anchor.start():]
    return generated.replace(target, 'filter_probe_nul()')



def oracle(parts, name, constructor):
    raw = ('\0'.join(parts) + '\0\0').encode('utf-16-le')
    words = [raw[i] + 256 * raw[i + 1] for i in range(0, len(raw), 2)]
    return f'''滤 取 {constructor}.
确认 ((滤 其 大小) == {len(raw)}) {literal(name + ' exact UTF16 allocation')}.
预期 取 {literal(words)}.
相同 取 真. 零数 取 0. 段数 取 0. 段长 取 0. 位 取 0.
循 预期 其 量 次
    实 取 (结果 (读字 其 调用 [滤,(滤 其 大小),位])) 其 数.
    若 实 != 预期[位] 则 相同 取 假. 然
    若 实 == 0 则
        零数 取 零数+1.
        若 段长 > 0 则 段数 取 段数+1. 然
        段长 取 0.
    另 段长 取 段长+1. 然
    位 取 位+1.
环
确认 相同 {literal(name + ' independent every-WCHAR byte oracle')}.
确认 (零数 == {len(parts)+1} 且 段数 == {len(parts)} 且 段长 == 0) {literal(name + ' exact label-pattern and NUL counts')}.
确认 (((结果 (读字 其 调用 [滤,(滤 其 大小),{len(words)-2}])) 其 数) == 0 且 ((结果 (读字 其 调用 [滤,(滤 其 大小),{len(words)-1}])) 其 数) == 0) {literal(name + ' final double NUL')}.
滤 其 关闭.
'''


def encoding_controls(executable, out):
    """Real child processes: old default decoding must fail, explicit UTF8 wins.

    POSIX additionally uses a real ASCII locale with UTF8/coercion disabled.
    The isolated cp1252 process overrides only locale.getencoding(), which is
    subprocess's default-codepage lookup. It does not alter the runner/runtime.
    The sole intentionally implicit text capture below is the old-behavior
    negative control. All production-path captures specify their encoding.
    """
    parent = r"""
import json, locale, subprocess, sys
mode, executable, expected_hex = sys.argv[1:]
assert not sys.flags.utf8_mode
if mode == 'cp1252-default':
    locale.getencoding = lambda: 'cp1252'
encoding = locale.getencoding()
assert encoding.lower().replace('-', '') not in ('utf8', 'utf_8'), encoding
expected = bytes.fromhex(expected_hex).decode('utf-8')
legacy = None
try:
    # Deliberately preserve the previous bug as a real-process negative control.
    result = subprocess.run([executable], capture_output=True, text=True, timeout=120)
    assert result.returncode != 0
    assert expected not in result.stdout + result.stderr
    legacy = 'decoded-message-mismatch'
except UnicodeDecodeError:
    legacy = 'UnicodeDecodeError'
fixed = subprocess.run([executable], capture_output=True, text=True,
                       encoding='utf-8', errors='strict', timeout=120)
assert fixed.returncode != 0 and expected in fixed.stdout + fixed.stderr
strict = False
try:
    subprocess.run([sys.executable, '-c', 'import os; os.write(2, bytes([255]))'],
                   capture_output=True, text=True, encoding='utf-8',
                   errors='strict', timeout=120)
except UnicodeDecodeError:
    strict = True
assert strict
print(json.dumps({'parent_encoding': encoding, 'legacy_failure': legacy,
                  'fixed_error_matched': True, 'invalid_utf8_rejected': strict}))
"""
    environment = {**os.environ, 'PYTHONUTF8': '0', 'PYTHONCOERCECLOCALE': '0',
                   'PYTHONIOENCODING': 'ascii', 'LC_ALL': 'C', 'LANG': 'C'}
    modes = ['cp1252-default']
    if os.name == 'posix':
        modes.insert(0, 'actual-ascii-locale')
    results = []
    for mode in modes:
        executed = subprocess.run([sys.executable, '-c', parent, mode,
                                   str(executable), FIELD_LIMIT.encode('utf-8').hex()],
                                  capture_output=True, text=True, encoding='utf-8',
                                  errors='strict', timeout=120, env=environment)
        path = out / ('encoding-' + mode + '.log')
        path.write_text(executed.stdout + executed.stderr, encoding='utf-8')
        if executed.returncode:
            raise AssertionError('Non-UTF8 parent control failed; see private encoding log')
        result = json.loads(executed.stdout)
        result.update({'mode': mode, 'log_sha256': digest(path)})
        results.append(result)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ru-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cc', default='gcc')
    args = parser.parse_args()
    compiler = args.ru_root.resolve()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    sys.path[:0] = [str(compiler), str(compiler / 'tests')]
    from rulang.frontend import parse, RuError
    from rulang.interpreter import Interpreter
    from rulang.compiler import Compiler
    from rulang import native_runtime as native
    if os.name == 'posix':
        from test_native_c_runtime import portable_test_source

    source_path = ROOT / 'src' / 'win32.ru'
    source = source_path.read_text(encoding='utf-8')
    body = function(source, '文件过滤缓冲') + function(source, '文件过滤')
    (out / 'extracted-filter-body.ru').write_text(body, encoding='utf-8')
    word_type = re.findall(r'^_过滤字 取 .*$', source, re.M)
    assert len(word_type) == 1
    ui = json.loads((ROOT / 'locales' / 'ui.json').read_text(encoding='utf-8'))
    catalog_source = (ROOT / 'src' / 'i18n_catalog.ru').read_text(encoding='utf-8')
    error_match = re.search(r"'en:error.win32.filter_invalid':('(?:[^'\\]|\\.)*')", catalog_source)
    assert error_match
    error = ast.literal_eval(error_match.group(1))
    keys = ['file.filter.all', 'file.filter.text', 'file.filter.ru', 'file.filter.markdown']
    catalog = {lang + ':' + key: ui[key][lang] for lang in LANGUAGES for key in keys}
    # Avoid silently testing stale JSON instead of the embedded runtime catalog.
    for key, value in catalog.items():
        match = re.search(r"'" + re.escape(key) + r"':('(?:[^'\\]|\\.)*')", catalog_source)
        assert match and ast.literal_eval(match.group(1)) == value, 'Embedded filter catalog differs from JSON: ' + key
    catalog['en:error.win32.filter_invalid'] = error
    tiny_catalog = out / 'catalog.ru'
    tiny_catalog.write_text('目录 取 ' + literal(catalog) + ".\n选择 取 ['en'].\n算 设置 代码: 选择[0] 取 代码. 得 代码. 法\n算 文本 键: 得 目录 其 查 (选择[0]+':'+键). 法\n", encoding='utf-8')
    parts_by_language = {lang: [ui[keys[0]][lang], '*.*', ui[keys[1]][lang], '*.txt', ui[keys[2]][lang], '*.ru', ui[keys[3]][lang], '*.md;*.markdown'] for lang in LANGUAGES}
    bridge_source = ROOT / 'tests' / 'fixtures' / 'filter_memory_bridge.c'
    bridge = out / ('filter_memory_bridge.dll' if os.name == 'nt' else 'filter_memory_bridge.so')
    command = [args.cc, '-std=c99', '-O2', '-Wall', '-Wextra', '-Werror', '-pedantic', '-shared']
    if os.name == 'posix':
        command.append('-fPIC')
    built = subprocess.run(command + [str(bridge_source), '-o', str(bridge)], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
    (out / 'bridge-build.log').write_text(built.stdout + built.stderr, encoding='utf-8')
    if built.returncode:
        raise RuntimeError('Owned bridge compilation failed; see private bridge-build.log')

    def preamble(model):
        return f'''密 取 外言 '如:密'.
本地 取 外言 {literal(str(tiny_catalog))}.
PTR 取 密 其 指针. W 取 密 其 u16. U 取 密 其 u32. UP 取 密 其 uintptr. V 取 密 其 无值.
测试库 取 密 其 动态库 {literal(str(bridge))}.
RtlMoveMemory 取 测试库 其 绑定 'copy_memory' (密 其 签名 V ([PTR,PTR,UP]) 'cdecl').
读字 取 测试库 其 绑定 'read_u16' (密 其 签名 U ([PTR,UP,UP]) 'cdecl').
CharNextW 取 测试库 其 绑定 {literal('next_' + model)} (密 其 签名 PTR ([PTR]) 'cdecl').
算 结果 成果:
    若 成果 其 回调错误 != 空 则 卒 (成果 其 回调错误). 然
    得 成果 其 值.
法
次数 取 [0].
作 确认 条件 名:
    若 非 条件 则 卒 'FAIL: '+名. 然
    次数[0] 取 次数[0]+1. 显 'PASS: '+名.
为
{word_type[0]}
{body}
'''

    results = []
    gc_results = []

    def run(name, text, passes, failure=None, nul=False, gc=False, track_cleanup=False):
        script = out / (name + '.ru')
        script.write_text(text, encoding='utf-8')
        output = io.StringIO()
        program = parse(text)
        if nul:
            inject_python_nul(program)
        memories = []
        original_init = native.NativeMemory.__init__

        def tracking_init(memory, *values, **options):
            original_init(memory, *values, **options)
            memories.append(memory)

        def owned_loader(path, **options):
            assert Path(path).resolve() == bridge
            return C.CDLL(path, use_last_error=True)

        code = 0
        with ExitStack() as stack:
            if os.name == 'posix':
                stack.enter_context(patch.object(native, '_supported', return_value=True))
                stack.enter_context(patch.object(C, 'WinDLL', owned_loader, create=True))
            if track_cleanup:
                stack.enter_context(patch.object(native.NativeMemory, '__init__', tracking_init))
            try:
                Interpreter(allow_native=True, stdout=output).execute(program, source_path=str(script))
            except RuError as exc:
                code = 1
                output.write(str(exc))
        python_output = output.getvalue()
        python_log = out / (name + '-python.log')
        python_log.write_text(python_output, encoding='utf-8')
        if (code != 0) != (failure is not None) or (failure and failure not in python_output):
            raise AssertionError(name + ': Python outcome mismatch; see private log')
        assert sum(line.startswith('PASS:') for line in python_output.splitlines()) == passes
        if track_cleanup:
            assert len(memories) == 3 and all(memory.closed for memory in memories), name + ': owned cleanup incomplete'
        generated = portable_test_source(text, str(script)) if os.name == 'posix' else Compiler(parse(text), str(script), allow_native=True).compile()
        if nul:
            generated = inject_c_nul(generated)
        cfile = out / (name + '.c')
        cfile.write_text(generated, encoding='utf-8')
        executable = out / (name + ('.exe' if os.name == 'nt' else ''))
        command = [args.cc, '-std=c99', '-O1', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function', '-pedantic', str(cfile), '-o', str(executable), '-lm']
        if os.name == 'posix':
            command += ['-ldl', '-pthread']
        built = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
        (out / (name + '-build.log')).write_text(built.stdout + built.stderr, encoding='utf-8')
        if built.returncode:
            raise AssertionError(name + ': C build failed; see private build log')
        executed = subprocess.run([str(executable)], capture_output=True, text=True, encoding='utf-8', errors='strict', timeout=120)
        c_output = executed.stdout + executed.stderr
        c_log = out / (name + '-c.log')
        c_log.write_text(c_output, encoding='utf-8')
        if (executed.returncode != 0) != (failure is not None) or (failure and failure not in c_output):
            raise AssertionError(name + ': C outcome mismatch; see private log')
        assert sum(line.startswith('PASS:') for line in c_output.splitlines()) == passes
        result = {'name': name, 'expected_failure': failure, 'python_exit': code, 'c_exit': executed.returncode, 'assertions_per_backend': passes, 'source_sha256': digest(script), 'python_log_sha256': digest(python_log), 'c_log_sha256': digest(c_log)}
        if track_cleanup:
            result['python_owned_allocations_closed'] = len(memories)
        results.append(result)
        if gc:
            executed = subprocess.run([str(executable)], capture_output=True, text=True, encoding='utf-8', errors='strict', timeout=120, env={**os.environ, 'RU_GC_THRESHOLD': '64', 'RU_GC_STATS': '1'})
            gc_output = executed.stdout + executed.stderr
            gc_log = out / (name + '-c-gc.log')
            gc_log.write_text(gc_output, encoding='utf-8')
            assert executed.returncode == 0
            assert sum(line.startswith('PASS:') for line in gc_output.splitlines()) == passes
            stats = re.search(r'RU_GC live=0 freed=\d+ collections=[1-9]\d*', gc_output)
            assert stats, 'GC stress did not finish with no live objects'
            gc_results.append({'name': name, 'stats': stats.group(0), 'log_sha256': digest(gc_log)})

    cases = {
        'long-translation': ['A' * 300 + '😀中e\u0301', '*.long', '日本語 한국어 Русский', '*.txt'],
        'supplementary-combining': ['😀e\u0301中\U0001d11e', '*.😀', '\u0301start a\u0301\u0308 end', '*.txt'],
        'leading-combining-after-separators': ['\u0301\u0308中😀', '\u0301*.a', '\u0301\U0001d11e', '\u0301*.b'],
        'ten-filter-pairs': sum(([f'Label {i} 中😀', f'*.x{i}'] for i in range(10)), []),
    }
    for units in (127, 128, 129, 138, 256, 257):
        cases['units-' + str(units)] = ['x' * (units - 4), '*']
    rejected = {'empty-array': [], 'odd-segments': ['label', '*', 'extra'], 'empty-label': ['', '*'], 'empty-pattern': ['label', ''], 'pipe-label': ['bad|label', '*'], 'embedded-nul': [NUL_SENTINEL, '*']}
    for model in ('unit', 'cluster'):
        header = preamble(model)
        text = header
        for lang, parts in parts_by_language.items():
            text += f'本地 其 设置 {literal(lang)}.\n' + oracle(parts, lang, '文件过滤')
        run(model + '-seven-languages', text, 28)
        text = header
        for name, parts in cases.items():
            text += oracle(parts, name, '文件过滤缓冲 (' + literal(parts) + ')')
        run(model + '-long-unicode-boundaries', text, 40)
        for name, parts in rejected.items():
            text = header + '滤 取 文件过滤缓冲 (' + literal(parts) + ").\n显 'unexpectedly accepted'.\n"
            run(model + '-reject-' + name, text, 0, NUL_LIMIT if name == 'embedded-nul' else error, nul=name == 'embedded-nul')
        for name, access in {'buffer': '存 其 大小.', 'anchored-pointer': '指 其 句.'}.items():
            text = header + "存 取 文件过滤缓冲 (['label','*']). 指 取 存 其 地址. 存 其 关闭. " + access + "\n显 'unexpectedly accepted'.\n"
            run(model + '-closed-' + name, text, 0, CLOSED)
        parts = cases['long-translation']
        text = oracle(parts, 'lifetime', '文件过滤缓冲 (' + literal(parts) + ')')
        # Preserve the returned owner through unrelated allocation churn before
        # reading it. Also exercise helper-local borrowed pointers under C GC.
        text = text.replace('预期 取 ', "循 32 次 垃圾 取 ['a','b','c','d']. 环\n预期 取 ", 1)
        run(model + '-lifetime', header + '循 24 次\n' + text + '环\n', 96, gc=True)
    for count in (127, 128, 129):
        text = preamble('unit') + f'''字段们 取 []. 位 取 0.
循 {count} 次 字段们 其 增 [('u'+(位 为 句)),W]. 位 取 位+1. 环
型 取 密 其 结构 字段们. 存 取 型 其 新建.
确认 ((存 其 大小) == {count*2}) 'unchanged native structure cap'. 存 其 关闭.
'''
        run('native-field-limit-' + str(count), text, 0 if count == 129 else 1, FIELD_LIMIT if count == 129 else None)
    for model in ('stuck', 'null'):
        run('reject-next-' + model, preamble(model) + "存 取 文件过滤缓冲 (['label','*']).\n", 0, error, track_cleanup=True)
    assert len(results) == EXPECTED_CASES
    assert sum(result['assertions_per_backend'] for result in results) == EXPECTED_ASSERTIONS
    decoding = encoding_controls(out / ('native-field-limit-129' + ('.exe' if os.name == 'nt' else '')), out)
    receipt = {'encoding_controls': decoding, 'mode': 'Owned-memory traversal models; POSIX platform adapter when applicable; NOT Windows ABI or User32/dialog acceptance', 'case_count': len(results), 'assertions_per_backend': EXPECTED_ASSERTIONS, 'body_sha256': digest(out / 'extracted-filter-body.ru'), 'inputs_sha256': {'win32.ru': hashlib.sha256(source.encode('utf-8')).hexdigest(), 'bridge': digest(bridge_source), 'runner': digest(Path(__file__)), 'i18n_catalog.ru': digest(ROOT / 'src/i18n_catalog.ru'), 'ui.json': digest(ROOT / 'locales/ui.json'), 'native_runtime.py': digest(compiler / 'rulang/native_runtime.py'), 'native_runtime.h': digest(compiler / 'rulang/native_runtime.h')}, 'nul_injection': 'Python single parsed string node; C single emitted sentinel to ru_string_alloc(9) plus exact bytes; production body and native guard unchanged', 'results': results, 'gc': gc_results}
    (out / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('FILTER_BUFFERS_PASSED=' + str(EXPECTED_CASES))
    print('FILTER_BUFFERS_ASSERTIONS_PER_BACKEND=' + str(EXPECTED_ASSERTIONS))


if __name__ == '__main__':
    main()
