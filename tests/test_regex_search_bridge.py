#!/usr/bin/env python3
"""Execute the actual bridge and native fixture against a bounded UTF-8 mock.

This is portable bridge-control-flow evidence, NOT real Scintilla/Windows proof.
Only the native boundary modules and their scalar result adapters are replaced;
regex_compile.ru and regex_vm.ru execute unmodified. The native fixture itself
is shared, including its exact PASS count. Native identity uses numeric handles
here; native pointer .句/.数 adapters are replaced with explicit conversions.
"""
import argparse
import hashlib
import os
import shutil
from pathlib import Path
import re
import subprocess
import sys
import tempfile

PIN = 'c3bb177c6a15e90821e5495cc74b0fdfc39b893a'
TREE = '5dedbf06f9fb6e00fbfe779b33f172aa35b61334'


def verify_compiler(root):
    def git(*arguments):
        return subprocess.check_output(
            ['git', '-C', str(root), *arguments], text=True, encoding='utf-8').strip()
    commit, tree = git('rev-parse', 'HEAD'), git('rev-parse', 'HEAD^{tree}')
    if commit != PIN or tree != TREE:
        raise RuntimeError(f'Wrong compiler identity: commit={commit}, tree={tree}')
    if git('status', '--porcelain=v1', '--untracked-files=all'):
        raise RuntimeError('Compiler source must be clean, including untracked files')
    return commit


def runtime_output(stdout, stderr, label):
    if stderr:
        raise AssertionError(f'{label}: unexpected runtime stderr:\n{stderr}')
    if re.search(r'\b(?:FAIL|SKIP)\b', stdout, re.IGNORECASE):
        raise AssertionError(f'{label}: failure or skip marker in runtime output')


def executable_path(directory, stem):
    return directory / (stem + ('.exe' if os.name == 'nt' else ''))


def gcc_path():
    compiler = shutil.which('gcc')
    if not compiler:
        raise RuntimeError('A gcc C compiler must be available on PATH')
    return compiler


def ru(value):
    if value is None:
        return '空'
    if isinstance(value, bool):
        return '真' if value else '假'
    if isinstance(value, str):
        escaped = (value.replace('\\', '\\\\').replace("'", "\\'")
                   .replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t'))
        return "'" + escaped + "'"
    if isinstance(value, list):
        return '[' + ','.join(ru(item) for item in value) + ']'
    if isinstance(value, dict):
        return '{' + ','.join(ru(key) + ':' + ru(item) for key, item in value.items()) + '}'
    return str(value)


def run(args, root):
    source = Path(__file__).resolve().parents[1]
    verify_compiler(args.ru_root)
    compiler = gcc_path()
    executable = executable_path(root, 'native_mock')
    environment = dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
    inputs = [source / 'src' / name for name in ['regex_compile.ru', 'regex_vm.ru', 'regex_search.ru']]
    inputs += [source / 'tests/regex_native.ru', Path(__file__).resolve()]
    hashes = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}
    for name in ['regex_compile.ru', 'regex_vm.ru', 'regex_search.ru']:
        s = (source / 'src' / name).read_text(encoding='utf-8')
        if name == 'regex_search.ru':
            s = s.replace('柄 其 句', '柄 为 句').replace("文['editor'] 其 句", "文['editor'] 为 句")
            s = re.sub(r'\((窗 其 发送 [^)]*)\) 其 数', r'((\1) 为 数)', s)
        (root / name).write_text(s, encoding='utf-8')
    s=(source/'tests/regex_native.ru').read_text(encoding='utf-8').replace("密 取 外言 '如:密'.\n",'').replace("'../src/","'")
    s=s.replace("    库 取 密 其 动态库 ((窗 其 目录)+'Scintilla.dll').",'')
    s=s.replace("    实例 取 窗 其 成功 ((窗 其 GetModuleHandleW) 其 调用 [空]) 'instance'.","    实例 取 0.")
    s=s.replace("    父 取 窗 其 控制 空 实例 'STATIC' 'regex fixture' 13565952 0.","    父 取 0.")
    s=s.replace("窗 其 结果 ((窗 其 DestroyWindow) 其 调用 [柄])","窗 其 销毁 柄").replace("窗 其 结果 ((窗 其 DestroyWindow) 其 调用 [父])","窗 其 销毁 父");s=re.sub(r'\((窗 其 发送 [^)]*)\) 其 数',r'((\1) 为 数)',s)
    (root/'native_mock.ru').write_text(s, encoding='utf-8')
    chars=set((source/'tests/regex_native.ru').read_text(encoding='utf-8'))|set('changed lengthzabc\r\n\t')
    lookup={c:[v-256 if v>=128 else v for v in c.encode()] for c in chars}
    (root/'win32.ru').write_text('字典 取 '+ru(lookup)+'.\n'+'''文们 取 [].
    算 创建:
        号 取 文们 其 量.
        文们 其 增 {'length':0,'anchor':0,'caret':0,'bytes':[],'parts':[],'text':'','old':'','dirty':假,'undo':0,'redo':0,'hidden':0,'targetStart':0,'targetEnd':0,'flags':0,'readonly':0,'closed':假}.
        得 号.
    法
    算 载入 柄 文本 脏:
        文 取 文们[柄]. 字们 取 []. 段们 取 []. 位 取 0.
        循 文本 其 量 次
            字 取 文本[位]. 码们 取 字典[字]. 子 取 0.
            循 码们 其 量 次
                字们 其 增 码们[子].
                若 子 == 0 则 段们 其 增 字. 另 段们 其 增 ''. 然
                子 取 子+1.
            环
            位 取 位+1.
        环
        文 其 增 'text' 文本. 文 其 增 'length' (字们 其 量).
        文 其 增 'bytes' 字们. 文 其 增 'parts' 段们. 文 其 增 'anchor' 0. 文 其 增 'caret' 0.
        文 其 增 'dirty' 脏. 文 其 增 'undo' 0. 文 其 增 'redo' 0.
        得 0.
    法
    算 销毁 柄:
        文们[柄] 其 增 'closed' 真. 得 0.
    法
    算 发文 柄 号 甲 文本:
        文 取 文们[柄].
        若 号 == 2181 则 得 载入 柄 文本 真. 然
        若 号 == 2170 则
            旧 取 文['text']. 后 取 文本+旧[1:].
            载入 柄 后 真. 文 其 增 'old' 旧. 文 其 增 'undo' 1.
        然
        得 0.
    法
    算 发送 柄 号 甲 乙:
        文 取 文们[柄].
        若 文['closed'] 则 卒 'Read after close.'. 然
        若 号 == 2183 则 得 文['length']. 然
        若 号 == 2009 则 得 文['anchor']. 然
        若 号 == 2008 则 得 文['caret']. 然
        若 号 == 2007 则 得 文['bytes'][甲]. 然
        若 号 == 2160 则 文 其 增 'anchor' 甲. 文 其 增 'caret' 乙. 然
        若 号 == 2166 则 得 1. 然
        若 号 == 2174 则 得 文['undo']. 然
        若 号 == 2016 则 得 文['redo']. 然
        若 号 == 2140 则 得 文['readonly']. 然
        若 号 == 2171 则 文 其 增 'readonly' 甲. 然
        若 号 == 2190 则 文 其 增 'targetStart' 甲. 然
        若 号 == 2192 则 文 其 增 'targetEnd' 甲. 然
        若 号 == 2198 则 文 其 增 'flags' 甲. 然
        若 号 == 2191 则 得 文['targetStart']. 然
        若 号 == 2193 则 得 文['targetEnd']. 然
        若 号 == 2199 则 得 文['flags']. 然
        若 号 == 2176 则 载入 柄 文['old'] 假. 文 其 增 'redo' 1. 然
        若 号 == 2227 则 文 其 增 'hidden' 1. 然
        若 号 == 2232 则 文 其 增 'hidden' 0. 然
        若 号 == 2228 则 得 1-文['hidden']. 然
        得 0.
    法
    ''', encoding='utf-8')
    (root/'editor.ru').write_text('''窗 取 外言 'win32.ru'.
    算 创建 父 实例 号:
        得 窗 其 创建.
    法
    算 设文本 柄 文:
        得 窗 其 载入 柄 文 假.
    法
    算 文本 柄:
        得 窗 其 文们[柄]['text'].
    法
    算 已变 柄:
        得 窗 其 文们[柄]['dirty'].
    法
    算 _范围文本 柄 始 末:
        文 取 窗 其 文们[柄]. 果 取 ''. 位 取 始.
        若 文['closed'] 则 卒 'Copy after close.'. 然
        循 末-始 次
            果 取 果+文['parts'][位]. 位 取 位+1.
        环
        得 果.
    法
    ''', encoding='utf-8')

    fixture = root / 'native_mock.ru'
    expected = 41
    logs = {}
    commands = [
        ('interpreter', [sys.executable, str(args.ru_root / 'ru'), 'run', str(fixture)]),
        ('build', [sys.executable, str(args.ru_root / 'ru'), 'build', '--cc', compiler,
                   str(fixture), '-o', str(executable)]),
        ('c', [str(executable)]),
    ]
    for label, command in commands:
        result = subprocess.run(command, text=True, encoding='utf-8', capture_output=True, timeout=120, env=environment)
        if result.returncode:
            raise RuntimeError(f'{label} failed:\n{result.stdout}\n{result.stderr}')
        if label != 'build':
            runtime_output(result.stdout, result.stderr, label)
            if any(not line.startswith(('PASS: ', 'TOTAL PASS: ')) for line in result.stdout.splitlines()):
                raise AssertionError(f'{label}: unexpected runtime output line')
            passes = [line for line in result.stdout.splitlines() if line.startswith('PASS: ')]
            totals = [line for line in result.stdout.splitlines() if line.startswith('TOTAL PASS: ')]
            if len(passes) != expected or len(set(passes)) != expected or totals != [f'TOTAL PASS: {expected}']:
                raise AssertionError(f'{label}: unexpected fixture count\n{result.stdout}')
            logs[label] = result.stdout
            print(f'{label}: {expected} portable mocked bridge assertions passed')
    if logs['interpreter'] != logs['c']:
        raise AssertionError('Interpreter/C bridge output differs')
    verify_compiler(args.ru_root)
    if hashes != {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}:
        raise AssertionError('Sources changed during bridge acceptance; rerun required')
    print('Portable mocked bridge only; no real Scintilla execution was performed.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ru-root', type=Path, required=True)
    args = parser.parse_args()
    args.ru_root = args.ru_root.resolve()
    with tempfile.TemporaryDirectory(prefix='regex-bridge-') as directory:
        run(args, Path(directory))


if __name__ == '__main__':
    main()
