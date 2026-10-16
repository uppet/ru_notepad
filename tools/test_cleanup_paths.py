#!/usr/bin/env python3
"""Run actual application rescue bodies with synthetic portable cleanup stubs.

This proves Ru control flow only, not native Windows resource cleanup.
"""
import argparse
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def rescue_body(source, function):
    starts = list(re.finditer(r'^算 ' + re.escape(function) + r'(?=\s|:)', source, re.M))
    if len(starts) != 1:
        raise ValueError('Expected one production function: ' + function)
    tail = source[starts[0].start():]
    end = re.search(r'^法\s*$', tail, re.M)
    if end is None:
        raise ValueError('Missing production function terminator')
    function_source = tail[:end.start()]
    marker = '    救 原因\n'
    if function_source.count(marker) != 1:
        raise ValueError('Expected one outer rescue in ' + function)
    body = function_source.split(marker)[1]
    ends = list(re.finditer(r'^    终\s*$', body, re.M))
    if len(ends) != 1:
        raise ValueError('Ambiguous production rescue terminator')
    body = body[:ends[0].start()]
    if body.count('报错 取 [原因].') != 1 or body.count('试 清操作. 救 清因') != 1:
        raise ValueError('Production cleanup structure changed; review extraction')
    return body


def fixture(source):
    parts = ["""# Generated from complete current production rescue bodies; no Win32 imports.
次数 取 [0].
调用数 取 [0,0].
结果 取 [''].
A 取 {'operation':{'kind':'save'},'lastOutcome':'','closeIndex':0,'queue':[]}.
作 确认 条件 为 事实 文 为 句:
    若 非 条件 则 卒 ('FAIL: '+文). 然
    次数[0] 取 次数[0]+1.
    显 'PASS: '+文.
为
算 清操作:
    调用数[0] 取 调用数[0]+1.
    卒 'cleanup'.
法
算 结束工作:
    调用数[1] 取 调用数[1]+1.
    得 空.
法
算 错误提示 文 为 句:
    结果[0] 取 文.
    得 空.
法
"""]
    for index, function in enumerate(('保存到', '工作时钟')):
        body = rescue_body(source, function)
        mutant = re.sub(r'^        报错 取 \[原因\]\.\n', '', body, flags=re.M).replace('报错[0]', '原因')
        if mutant == body or '报错' in mutant or "救 清因 原因 取 原因+'\\n'+清因." not in mutant:
            raise ValueError('Scalar negative control no longer matches original failure')
        for suffix, text in (('正', body), ('旧', mutant)):
            parts.append(f"算 路径{index}{suffix}:\n    试\n        卒 'primary'.\n    救 原因\n{text}    终\n    得 空.\n法\n")
        for suffix, expected in (('正', "primary\\ncleanup"), ('旧', 'primary')):
            parts.append(f"""调用数[0] 取 0. 调用数[1] 取 0. 结果[0] 取 ''.
试
    路径{index}{suffix}.
救 捕获原因
    结果[0] 取 捕获原因.
终
确认 (结果[0] == '{expected}') '{function} {suffix} exact primary and cleanup diagnostic contract'.
""")
            if suffix == '正':
                parts.append(f"确认 (调用数[0] == 1) '{function} cleanup runs exactly once'.\n确认 (调用数[1] == 1) '{function} unlock runs exactly once'.\n")
    parts.append("显 'TOTAL PASS: '+(次数[0] 为 句).\n")
    return ''.join(parts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ru-root', type=pathlib.Path, required=True)
    args = parser.parse_args()
    directory = ROOT / 'build/cleanup-control'
    directory.mkdir(parents=True, exist_ok=True)
    source = directory / 'production-cleanup.ru'
    source.write_text(fixture((ROOT / 'src/main.ru').read_text(encoding='utf-8')), encoding='utf-8')
    executable = directory / 'production-cleanup'
    compiler = args.ru_root.resolve() / 'ru'
    for name, command, assertions in (
        ('python', [sys.executable, str(compiler), 'run', str(source)], 8),
        ('build', [sys.executable, str(compiler), 'build', '--cc', 'gcc', str(source), '-o', str(executable)], None),
        ('c', [str(executable)], 8),
    ):
        result = subprocess.run(command, cwd=ROOT, text=True, encoding='utf-8',
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
        (directory / (name + '.log')).write_text(result.stdout, encoding='utf-8')
        if result.returncode != 0:
            raise RuntimeError(f'{name} failed: {result.stdout}')
        if assertions is not None:
            if (re.findall(r'^TOTAL PASS: ([0-9]+)\s*$', result.stdout, re.M) != ['8'] or
                    len(re.findall(r'^PASS:', result.stdout, re.M)) != 8 or
                    re.search(r'^(FAIL:|SKIP:)', result.stdout, re.M)):
                raise RuntimeError(f'{name} did not execute all eight control-flow assertions')
            print(f'BACKEND: {name}\n{result.stdout}', end='')
    print('PASS: production cleanup rescue bodies and original scalar negative controls in both Ru backends')


if __name__ == '__main__':
    main()
