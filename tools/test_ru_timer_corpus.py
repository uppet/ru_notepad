#!/usr/bin/env python3
"""Execute both native fixtures' pure corpus builders in both Ru backends.

Only the unique, parameter-free function is extracted. No native imports or
platform overrides are used. Its complete UTF-8 output must equal the existing
detached-GUI fixture, not just its size or selected style probes.
"""
import argparse
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import hashlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import windows_ci as ci

SOURCES = ('tests/ru_syntax_native.ru', 'tests/app_ru_native.ru')
EXPECTED_SHA256 = 'ecf8dca884444a5e54e1f40dc6af01cf5e7830ed6fe902d3adf6fdf255f9b3fa'


def extract_builder(path, parse):
    source = path.read_text(encoding='utf-8')
    nodes = parse(source)
    matches = [index for index, node in enumerate(nodes)
               if node.kind == 'function' and node.data['name'] == '计时源码']
    if len(matches) != 1:
        raise ValueError('Expected one actual 计时源码 function in ' + path.name)
    index = matches[0]
    first = nodes[index].token.line - 1
    last = nodes[index + 1].token.line - 1 if index + 1 < len(nodes) else None
    result = ''.join(source.splitlines(keepends=True)[first:last])
    # Do not pull in top-level fixture initialization or hidden native imports.
    extracted = parse(result)
    if (len(extracted) != 1 or extracted[0].kind != 'function' or
            extracted[0].data['params']):
        raise ValueError('Corpus extraction is not exactly one function')
    return result + '\n显 计时源码.\n'


def check_output(output, expected, label):
    if not output.endswith(b'\n') or output[:-1] != expected:
        raise AssertionError(label + ': full corpus bytes differ from the GUI fixture')
    print('PASS: ' + label + ' exact UTF-8 corpus')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ru-root', type=Path, required=True)
    parser.add_argument('--cc', default='gcc')
    args = parser.parse_args()
    ru = args.ru_root.resolve()
    sys.path.insert(0, str(ru))
    from rulang.frontend import parse
    from rulang.interpreter import Interpreter
    expected, _ = ci.gui_ru_timer_fixture()
    if (len(expected) != 1_000_000 or len(expected.decode('utf-8')) != 636_370 or
            hashlib.sha256(expected).hexdigest() != EXPECTED_SHA256):
        raise AssertionError('The original GUI timing corpus changed')
    with tempfile.TemporaryDirectory(prefix='ru-timer-corpus-') as directory:
        directory = Path(directory)
        for name in SOURCES:
            source = extract_builder(ROOT / name, parse)
            path = directory / Path(name).name
            path.write_text(source, encoding='utf-8')
            output = io.StringIO()
            Interpreter(stdout=output).execute(parse(source), source_path=path)
            check_output(output.getvalue().encode('utf-8'), expected, 'python ' + Path(name).stem)
            executable = directory / Path(name).stem
            built = subprocess.run([sys.executable, str(ru / 'ru'), 'build', '--cc', args.cc,
                                    str(path), '-o', str(executable)],
                                   capture_output=True, timeout=120)
            if built.returncode != 0:
                raise RuntimeError(built.stdout.decode('utf-8', 'replace') +
                                   built.stderr.decode('utf-8', 'replace'))
            ran = subprocess.run([str(executable)], capture_output=True, timeout=30)
            if ran.returncode != 0 or ran.stderr:
                raise RuntimeError('Generated corpus program failed: ' +
                                   ran.stderr.decode('utf-8', 'replace'))
            check_output(ran.stdout, expected, 'c ' + Path(name).stem)
    print('RU_TIMER_CORPUS_PASS: 4')


if __name__ == '__main__':
    main()
