#!/usr/bin/env python3
"""Actual buffer controls; POSIX uses compiler test adapters, NOT Windows ABI proof.

Neither production native code nor its buffer cap is patched. The Python adapter
only overrides the platform predicate in this process; the C adapter is the
pinned compiler's existing test-only replacement in an emitted test artifact.
On Windows, both fixtures use the ordinary unmodified CLI/backends.
"""
import argparse
import io
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ru-root', required=True, type=Path)
    ap.add_argument('--output', required=True, type=Path)
    a = ap.parse_args()
    compiler = a.ru_root.resolve()
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    sys.path[:0] = [str(compiler), str(compiler / 'tests')]
    from rulang.frontend import parse, RuError
    from rulang.interpreter import Interpreter
    from rulang import native_runtime
    if os.name == 'posix':
        from test_native_c_runtime import portable_test_source
    print('MODE: ' + ('POSIX test adapters; real memory controls, NOT Windows ABI' if os.name == 'posix' else 'Windows unmodified CLI/backends'), flush=True)
    for name, expected in [('native_growth_chunks', 0), ('oversized_growth_buffer', 1)]:
        source = ROOT / 'tests' / 'fixtures' / (name + '.ru')
        text = source.read_text(encoding='utf-8')
        for backend in ('python', 'c'):
            if os.name == 'posix' and backend == 'python':
                buf = io.StringIO()
                code = 0
                with patch.object(native_runtime, '_supported', return_value=True):
                    try:
                        Interpreter(allow_native=True, stdout=buf).execute(parse(text))
                    except RuError as error:
                        code = 1
                        buf.write(str(error))
                output = buf.getvalue()
            else:
                if backend == 'python':
                    cmd = [sys.executable, str(compiler / 'ru'), 'run', '--allow-native', str(source)]
                else:
                    exe = out / (name + ('.exe' if os.name == 'nt' else ''))
                    if os.name == 'posix':
                        cfile = out / (name + '.c')
                        cfile.write_text(portable_test_source(text, str(source)), encoding='utf-8')
                        cmd = ['gcc', '-std=c99', '-O1', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function', '-pedantic', str(cfile), '-o', str(exe), '-lm', '-ldl', '-pthread']
                    else:
                        cmd = [sys.executable, str(compiler / 'ru'), 'build', '--allow-native', '--cc', 'gcc', str(source), '-o', str(exe)]
                    built = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                    (out / (name + '-build.log')).write_text(built.stdout + built.stderr, encoding='utf-8')
                    if built.returncode:
                        raise RuntimeError(built.stdout + built.stderr)
                    cmd = [str(exe)]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                code, output = result.returncode, result.stdout + result.stderr
            (out / (name + '-' + backend + '.log')).write_text(output, encoding='utf-8')
            assert code == expected, (name, backend, code, output)
            if expected:
                reason = '原生文本超过缓冲上限' if backend == 'python' else '原生缓冲大小须为 1 至 16777216 字节'
                assert reason in output, output
                assert 'unexpectedly accepted' not in output, output
            else:
                assert output.count('PASS: real 1 MiB') == 32, output
                assert sum(line.startswith('PASS:') for line in output.splitlines()) == 33, output
                assert output.endswith('TOTAL PASS: 33\n'), output
                assert 'FAIL:' not in output, output
            print('PASS: ' + name + ' ' + backend, flush=True)

if __name__ == '__main__':
    main()
