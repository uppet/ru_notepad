#!/usr/bin/env python3
"""Execute exact production regex status functions with a recording window boundary.

Portable interpreter/C control-flow evidence, not Windows GUI acceptance.
"""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

from test_regex_search_bridge import verify_compiler, gcc_path, executable_path, runtime_output

ROOT = Path(__file__).resolve().parents[1]


def production_functions(source):
    return '\n'.join('算 ' + name + source.split('算 ' + name, 1)[1].split('\n法', 1)[0] + '\n法'
                     for name in ('正则状态文:', '正则状态:'))


def run(ru_root, legacy=False):
    verify_compiler(ru_root)
    source = (ROOT / 'src/main.ru').read_text(encoding='utf-8')
    with tempfile.TemporaryDirectory(prefix='regex-status-') as directory:
        root = Path(directory)
        (root / 'window.ru').write_text("""记录 取 {'text':'Opening: synthetic','writes':0}.
算 标题 柄 文:
    记录 其 增 'text' 文.
    记录 其 增 'writes' ((记录 其 查 'writes')+1).
    得 空.
法
""", encoding='utf-8')
        (root / 'local.ru').write_text("算 文本 键:\n    得 键.\n法\n", encoding='utf-8')
        expected = 'old document' if legacy else 'Opening: synthetic'
        writes = 1 if legacy else 0
        fixture = """窗 取 外言 'window.ru'.
本地 取 外言 'local.ru'.
A 取 {'ready':真,'busy':真,'regexNotice':'','status':11,'statusBase':'old document','markdownDiagnosticText':''}.
""" + production_functions(source) + f"""
正则状态.
若 (窗 其 记录['text']) != '{expected}' 则 卒 'Busy status ownership violated.'. 然
若 (窗 其 记录['writes']) != {writes} 则 卒 'Busy status write count differs.'. 然
显 'PASS: busy status ownership'.
A 其 增 'busy' 假.
A 其 增 'regexNotice' 'regex.cancelled'.
A 其 增 'markdownDiagnosticText' ' diagnostic'.
正则状态.
若 (窗 其 记录['text']) != 'regex.cancelled    old document diagnostic' 则 卒 'Idle regex status was not refreshed.'. 然
显 'PASS: idle regex notice refresh'.
A 其 增 'ready' 假.
A 其 增 'statusBase' 'not ready'.
正则状态.
若 (窗 其 记录['text']) != 'regex.cancelled    old document diagnostic' 则 卒 'Not-ready status was written.'. 然
显 'PASS: not-ready status preservation'.
显 'TOTAL PASS: 3'.
"""
        path = root / 'status.ru'
        path.write_text(fixture, encoding='utf-8')
        exe = executable_path(root, 'status')
        outputs = []
        for label, command in (
            ('interpreter', [sys.executable, str(ru_root / 'ru'), 'run', str(path)]),
            ('build', [sys.executable, str(ru_root / 'ru'), 'build', '--cc', gcc_path(), str(path), '-o', str(exe)]),
            ('c', [str(exe)]),
        ):
            result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', timeout=120)
            if result.returncode:
                raise RuntimeError(f'{label}: {result.stdout}\n{result.stderr}')
            if label != 'build':
                runtime_output(result.stdout, result.stderr, label)
                if result.stdout.splitlines() != ['PASS: busy status ownership', 'PASS: idle regex notice refresh',
                                                 'PASS: not-ready status preservation', 'TOTAL PASS: 3']:
                    raise AssertionError(result.stdout)
                outputs.append(result.stdout)
                print(f'{label}: 3 production status controls passed (legacy={legacy})')
        if outputs[0] != outputs[1]:
            raise AssertionError('Interpreter and C disagree')
    verify_compiler(ru_root)
    if source != (ROOT / 'src/main.ru').read_text(encoding='utf-8'):
        raise AssertionError('Production source changed during control')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ru-root', type=Path, required=True)
    parser.add_argument('--expect-legacy-clobber', action='store_true', help='Demonstrate the unfixed busy-status overwrite')
    args = parser.parse_args()
    run(args.ru_root.resolve(), args.expect_legacy_clobber)
