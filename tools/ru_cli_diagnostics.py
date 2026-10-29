"""Accept only the selected Ru CLI's exact source-derived nonfatal style hints.

This does not suppress diagnostics. Callers retain raw build logs and continue
to reject every runtime stderr byte and every nonzero exit. Expectations are
computed before compilation from the complete ordinary module graph, in an
isolated process using the selected compiler's public frontend APIs. Neither
source nor compiler is rewritten, and no diagnostic is accepted by a regex.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess
import sys


LIMIT = 1024 * 1024
_PROBE = r'''
import hashlib, json, sys
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
from rulang.frontend import parse, style_issues
from rulang.modules import load_module_graph, read_source
from rulang.diagnostics import diagnostic
source = read_source(sys.argv[2])
modules = load_module_graph(sys.argv[2], parse(source))
modules.sources[modules.root] = source
lines = []
inputs = {}
for path, text in modules.sources.items():
    inputs[path] = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    for issue in style_issues(text):
        if issue.code != 'missing-statement-dot' or issue.category != '书写规范':
            raise RuntimeError('Unreviewed style diagnostic kind')
        lines.append(diagnostic(issue, path, severity='warning')['formatted'] + '\n')
for name in ('ru', 'rulang/frontend.py', 'rulang/modules.py',
             'rulang/diagnostics.py', 'rulang/cli.py'):
    path = str((Path(sys.argv[1]) / name).resolve())
    inputs[path] = hashlib.sha256(Path(path).read_bytes()).hexdigest()
print(json.dumps({'stderr': ''.join(lines), 'inputs': inputs}, ensure_ascii=True))
'''


def _compile_command(command, compiler, source):
    """Require the actual selected CLI, build/check, and one exact source path."""
    argv = tuple(map(str, command))
    if not argv or Path(argv[0]).resolve() != Path(sys.executable).resolve():
        raise RuntimeError('Style expectations require the selected Python Ru CLI')
    index = 1
    while index < len(argv) and argv[index] in ('-I', '-B'):
        index += 1
    if (len(argv) <= index + 2 or Path(argv[index]).resolve() != compiler / 'ru'
            or argv[index + 1] not in ('build', 'check')):
        raise RuntimeError('Style expectations apply only to Ru build/check')
    action = argv[index + 1]
    values = {'--target'}
    flags = {'--allow-native'}
    if action == 'build':
        values |= {'--cc', '-o', '--output', '--emit-c', '--source-prefix-map'}
        flags |= {'--full-runtime'}
    positional = []
    index += 2
    while index < len(argv):
        value = argv[index]
        if value in values:
            index += 2
            if index > len(argv):
                raise RuntimeError('Incomplete Ru compile option')
            continue
        if value in flags:
            index += 1
            continue
        if value.startswith('-'):
            raise RuntimeError('Unreviewed Ru compile option for style expectations')
        positional.append(Path(value).resolve())
        index += 1
    if positional != [source]:
        raise RuntimeError('Style expectations must match the exact compiled source')
    return argv


@dataclass(frozen=True)
class CompileDiagnostics:
    command: tuple[str, ...]
    stderr: str
    inputs: tuple[tuple[str, str], ...]


def prepare_compile_diagnostics(command, compiler, source):
    compiler, source = Path(compiler).resolve(), Path(source).resolve()
    argv = _compile_command(command, compiler, source)
    result = subprocess.run([sys.executable, '-I', '-B', '-c', _PROBE,
                             str(compiler), str(source)], capture_output=True,
                            timeout=30)
    if (result.returncode or result.stderr or len(result.stdout) > LIMIT):
        raise RuntimeError('Cannot derive exact Ru style diagnostics')
    record = json.loads(result.stdout.decode('utf-8', 'strict'))
    expected, inputs = record['stderr'], record['inputs']
    if (not isinstance(expected, str) or len(expected.encode('utf-8')) > LIMIT
            or not isinstance(inputs, dict) or str(source) not in inputs):
        raise RuntimeError('Invalid source-derived Ru style diagnostic record')
    return CompileDiagnostics(argv, expected, tuple(inputs.items()))


def validate_stderr(command, returncode, stderr, expectation=None):
    """Validate a completed stage; no expectation means strictly empty stderr."""
    if returncode != 0:
        raise RuntimeError('Ru stage returned a nonzero exit status')
    if isinstance(stderr, bytes):
        stderr = stderr.decode('utf-8', 'strict')
    if not isinstance(stderr, str) or len(stderr.encode('utf-8')) > LIMIT:
        raise RuntimeError('Ru stage stderr exceeds its fixed bound')
    if expectation is None:
        if stderr:
            raise RuntimeError('Unexpected runtime or non-compile stderr')
        return
    if tuple(map(str, command)) != expectation.command:
        raise RuntimeError('Style expectation belongs to a different compile command')
    for path, digest in expectation.inputs:
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest:
            raise RuntimeError('Ru diagnostic inputs changed during compilation')
    # Python text pipes normalize CRLF on Windows; raw-log callers do not.
    # This is the sole transport normalization. Order, duplicates and every
    # source path, position, severity, character and final newline remain exact.
    if stderr.replace('\r\n', '\n') != expectation.stderr:
        raise RuntimeError('Ru compile stderr differs from exact source-derived style hints')
