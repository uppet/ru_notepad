#!/usr/bin/env python3
"""Execute the unchanged pure Markdown policy and selection fixtures in both Ru backends.

No native capability, rewritten source, platform override, downloaded input or
native-Windows acceptance claim is involved. Public output contains only bounded
synthetic assertion lines and source hashes; compiler diagnostics stay private.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
CASES = {'markdown_policy': 199, 'markdown_selection_policy': 31}
LIMIT = 1024 * 1024


def verify_output(data, count):
    if not isinstance(data, bytes) or len(data) > LIMIT or not data.endswith(b'\n'):
        raise RuntimeError('Markdown policy output is missing or exceeds its fixed bound')
    text = data.decode('utf-8', 'strict').replace('\r\n', '\n')
    lines = text.splitlines()
    if (len(lines) != count + 1 or lines[-1] != f'TOTAL PASS: {count}' or
            any(not re.fullmatch(r'PASS: [^\r\n\x00-\x1f]+', line) for line in lines[:-1])):
        raise RuntimeError('Markdown policy exact assertion output mismatch')
    return text


def source_snapshot(root):
    # Follow precisely the ordinary literal-import graph of these two fixtures.
    # Unrelated native GUI edits do not invalidate a pure-policy receipt.
    root = root.resolve()
    pending = [root / 'tests' / (name + '.ru') for name in CASES]
    snapshot = {}
    while pending:
        path = pending.pop()
        if path.is_symlink() or not path.is_file() or root not in path.resolve().parents:
            raise RuntimeError('Markdown policy source is missing, linked or outside its checkout')
        relative = path.resolve().relative_to(root).as_posix()
        if relative in snapshot:
            continue
        data = path.read_bytes()
        snapshot[relative] = hashlib.sha256(data).hexdigest()
        for imported in re.findall(r"外言\s+'([^']+)'", data.decode('utf-8')):
            if imported.startswith('如:'):
                raise RuntimeError('Pure Markdown policy graph must not import native or external modules')
            pending.append(path.parent / imported)
    snapshot['tools/test_markdown_portable.py'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return snapshot


class CleanupError(RuntimeError):
    pass


def stop_process_tree(process):
    # Each compiler/backend owns a fresh process group. Never target a shared
    # terminal group, scan other processes, or leave compiler children running
    # while their private files are removed.
    if os.name == 'nt':
        result = subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
        if result.returncode:
            raise CleanupError('Markdown backend process-tree cleanup failed')
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    process.wait(timeout=5)


def checked_run(command, directory, label, timeout):
    out, err = directory / (label + '.stdout'), directory / (label + '.stderr')
    process = None
    with out.open('xb') as stdout, err.open('xb') as stderr:
        options = {'creationflags': 0x00000200} if os.name == 'nt' else {'start_new_session': True}
        process = subprocess.Popen(command, stdout=stdout, stderr=stderr, **options)
        started = time.monotonic()
        try:
            while True:
                if out.stat().st_size > LIMIT or err.stat().st_size > LIMIT:
                    raise RuntimeError('Markdown backend output exceeded its fixed acceptance bound')
                remaining = timeout - (time.monotonic() - started)
                if remaining <= 0:
                    raise RuntimeError('Markdown backend exceeded its execution deadline')
                try:
                    process.wait(timeout=min(0.05, remaining))
                    break
                except subprocess.TimeoutExpired:
                    pass
            if (time.monotonic() - started > timeout or process.returncode or
                    err.stat().st_size or out.stat().st_size > LIMIT):
                raise RuntimeError('Markdown backend failed: ' + label)
        except BaseException:
            # Even if the parent just exited, its compiler group may still be
            # alive. POSIX killpg targets that owned group, not only its leader.
            if os.name != 'nt' or process.poll() is None:
                try:
                    stop_process_tree(process)
                except Exception:
                    raise CleanupError('Markdown backend process-tree cleanup failed') from None
            raise
    return out.read_bytes()


def controls():
    valid = b'PASS: synthetic\nTOTAL PASS: 1\n'
    verify_output(valid, 1)
    for invalid in (b'', valid + valid, valid.replace(b'1', b'2'),
                    b'SKIP: synthetic\nTOTAL PASS: 1\n', b'PASS: \x00\nTOTAL PASS: 1\n',
                    b'x' * (LIMIT + 1)):
        try:
            verify_output(invalid, 1)
        except (RuntimeError, UnicodeError):
            continue
        raise RuntimeError('Markdown output negative control was admitted')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ru-root', type=Path)
    parser.add_argument('--cc', default='gcc')
    parser.add_argument('--controls-only', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/markdown-policy-evidence')
    args = parser.parse_args()
    controls()
    if args.controls_only:
        print('MARKDOWN_PORTABLE_CONTROLS_PASS')
        return 0
    if args.ru_root is None:
        parser.error('--ru-root is required for actual backend execution')
    ru = args.ru_root.resolve()
    before = source_snapshot(ROOT)
    if any('tests/' + name + '.ru' not in before for name in CASES):
        raise RuntimeError('A mandatory Markdown pure fixture is missing or linked')
    # Bind fixture imports too, including the production selection policy.
    for name in CASES:
        if '如:密' in (ROOT / 'tests' / (name + '.ru')).read_text(encoding='utf-8'):
            raise RuntimeError('Pure Markdown fixture unexpectedly imports native capability')
    args.output.mkdir(parents=True, exist_ok=False)
    report = {'schema': 1, 'passed': False, 'source_sha256': before, 'cases': []}
    try:
        private = Path(tempfile.mkdtemp(prefix='ru-markdown-portable-'))
        cleanup_allowed = True
        try:
            for name, count in CASES.items():
                source = ROOT / 'tests' / (name + '.ru')
                code = ('import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); '
                        'from rulang.frontend import parse; from rulang.interpreter import Interpreter; '
                        'p=Path(sys.argv[2]); Interpreter().execute(parse(p.read_text(encoding="utf-8")),source_path=p)')
                outputs = {}
                outputs['interpreter'] = checked_run([sys.executable, '-I', '-c', code, str(ru), str(source)],
                                                     private, name + '-interpreter', 120)
                executable = private / (name + ('.exe' if os.name == 'nt' else ''))
                checked_run([sys.executable, str(ru / 'ru'), 'build', '--cc', args.cc,
                             str(source), '-o', str(executable)], private, name + '-build', 120)
                outputs['host-c'] = checked_run([str(executable)], private, name + '-host-c', 30)
                if verify_output(outputs['interpreter'], count) != verify_output(outputs['host-c'], count):
                    raise RuntimeError('Markdown backend assertion outputs disagree')
                for backend, output in outputs.items():
                    text = verify_output(output, count)
                    (args.output / (name + '-' + backend + '.log')).write_text(text, encoding='utf-8', newline='\n')
                    report['cases'].append({'fixture': name, 'backend': backend, 'assertions': count})
            if source_snapshot(ROOT) != before:
                raise RuntimeError('Markdown policy sources changed during backend verification')
        except CleanupError:
            cleanup_allowed = False
            raise
        finally:
            if cleanup_allowed:
                shutil.rmtree(private)
        report['passed'] = True
    finally:
        (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('MARKDOWN_PORTABLE_PASS ' + ' '.join(f'{name}={count}x2' for name, count in CASES.items()))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.SubprocessError, OSError, UnicodeError):
        print('MARKDOWN_PORTABLE_FAILED', file=sys.stderr)
        raise SystemExit(1)
