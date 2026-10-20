#!/usr/bin/env python3
"""Manual owned-fixture Windows measurement; never package or certify a release."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_source_archives import ARCHIVES

ROOT = Path(__file__).resolve().parents[1]
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def validate_measurements(stdout, stderr):
    lines = stdout.splitlines()
    if not lines or lines[-1] != 'GROWTH_COMPLETE 2' or stderr:
        raise RuntimeError('Incomplete native diagnostic or unexpected stderr')
    values = {}
    for line in lines[:-1]:
        match = re.fullmatch(r'GROWTH ([12]) ([0-6]) ([0-9]+) (-?[0-9]+)', line)
        if not match:
            raise RuntimeError('Unexpected diagnostic output')
        case, stage, item, value = map(int, match.groups())
        key = f'{case}/{stage}/{item}'
        if key in values:
            raise RuntimeError('Duplicate measurement')
        values[key] = value
    expected = {f'{case}/{stage}/{item}' for case in (1, 2) for stage in range(7) for item in (1, 2, 3, 4, 5, 6, 7, 8, 10)}
    expected |= {f'{case}/1/9' for case in (1, 2)}
    expected |= {f'{case}/{stage}/11' for case in (1, 2) for stage in (0, 1, 3, 4, 5, 6)}
    expected |= {f'{case}/4/{item}' for case in (1, 2) for item in (12, 13)}
    if set(values) != expected:
        raise RuntimeError('Missing or unexpected measurement fields')
    return values

def publish_measurements(path, report):
    pending = path.with_suffix('.json.pending')
    pending.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    pending.replace(path)

def validate_trigger(event_name, ref, event):
    if event_name == 'workflow_dispatch':
        inputs = event.get('inputs', {})
        allowed = inputs.get('syntax_growth_diagnostic') in (True, 'true') and all(inputs.get(key, False) in (False, 'false', '') for key in ('historical_callback', 'i18n_window_diagnostic', 'i18n_focused_diagnostic'))
    else:
        allowed = False
    if not allowed:
        raise RuntimeError('Strict diagnostic event guard rejected this invocation')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ru-root', type=Path)
    ap.add_argument('--msys-root', type=Path)
    ap.add_argument('--guard-only', action='store_true')
    a = ap.parse_args()
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text(encoding='utf-8'))
    validate_trigger(os.environ['GITHUB_EVENT_NAME'], os.environ['GITHUB_REF'], event)
    if a.guard_only:
        print('Strict diagnostic event guard accepted.')
        return
    if a.ru_root is None or a.msys_root is None:
        raise RuntimeError('Both compiler and MSYS roots are required')
    if os.name != 'nt':
        raise SystemExit('Requires real Windows; no host emulation is permitted.')
    output = ROOT / 'build/cpp-growth-diagnostic'
    output.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ)
    binpath = a.msys_root.resolve() / 'mingw64/bin'
    env['PATH'] = str(binpath) + os.pathsep + env['PATH']
    env['PYTHONUTF8'] = '1'
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['PYTHONOPTIMIZE'] = '0'
    def run(tag, command, timeout=600):
        with (output / (tag + '.stdout.log')).open('xb') as stdout, (output / (tag + '.stderr.log')).open('xb') as stderr:
            result = subprocess.run(list(map(str, command)), cwd=ROOT, env=env, stdout=stdout, stderr=stderr, timeout=timeout)
        if result.returncode:
            raise RuntimeError(tag + ' failed: ' + str(result.returncode))
    run('archives', [sys.executable, '-I', 'tools/prepare_source_archives.py', '--root', ROOT, '--receipt', output / 'source-archives.json'])
    for spec in ARCHIVES:
        archive = ROOT / 'vendor/downloads' / spec.filename
        if archive.stat().st_size != spec.bytes or sha(archive) != spec.sha256:
            raise RuntimeError('Official archive hash or size mismatch')
        if (ROOT / 'vendor' / spec.folder).exists():
            raise RuntimeError('Fresh checkout required')
        with zipfile.ZipFile(archive) as zipped:
            zipped.extractall(ROOT / 'vendor')  # exact pinned, validated offline archive
    make = binpath / 'mingw32-make.exe'
    common = ['CXX=g++.exe', 'WINDRES=windres.exe', 'AR=ar.exe', 'RANLIB=ranlib.exe']
    run('scintilla', [make, '-j2', '-C', ROOT / 'vendor/scintilla/win32', '../bin/Scintilla.dll', *common])
    run('lexilla', [make, '-j2', '-C', ROOT / 'vendor/lexilla/src', '../bin/lexilla.dll', *common, 'windir=C:/Windows', 'LDFLAGS=-shared -static -mwindows -Wl,--kill-at -s'])
    exe = output / 'cpp_growth_diagnostic.exe'
    source = 'tests/fixtures/cpp_growth_diagnostic.ru'
    run('build', [sys.executable, 'tools/build.py', '--ru-root', a.ru_root.resolve(), '--cc', binpath / 'gcc.exe', '--cxx', binpath / 'g++.exe', '--windres', binpath / 'windres.exe', '--ar', binpath / 'ar.exe', '--ranlib', binpath / 'ranlib.exe', '--skip-scintilla', '--skip-lexilla', '--source', source, '--output', exe, '--console'])
    receipt = json.loads(exe.with_suffix('.build.json').read_text())
    if receipt['entry_sha256'] != sha(ROOT / source) or receipt['exe_sha256'] != sha(exe):
        raise RuntimeError('Diagnostic artifact receipt mismatch')
    for name, digest in receipt['source_sha256'].items():
        if sha(ROOT / name) != digest:
            raise RuntimeError('Diagnostic source binding mismatch')
    run('native', [exe], timeout=120)
    stdout = (output / 'native.stdout.log').read_text(encoding='utf-8')
    stderr = (output / 'native.stderr.log').read_text(encoding='utf-8')
    values = validate_measurements(stdout, stderr)
    report = {'schema': 1, 'kind': 'measurement_only_not_acceptance', 'exe_sha256': sha(exe), 'entry_sha256': sha(ROOT / source), 'values': values}
    publish_measurements(output / 'measurements.json', report)
    print('Owned C++ growth measurements recorded; full acceptance remains required.')

if __name__ == '__main__':
    main()
