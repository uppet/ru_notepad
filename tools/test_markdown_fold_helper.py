#!/usr/bin/env python3
"""Bounded C controls; real Windows DLL checks are mandatory on Windows.

Public JSON contains only fixed stages, hashes/sizes, counters and outcomes.
Compiler/runtime output is captured in a private local temporary directory.
The test executables and this runner are never distributed with the product.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_markdown_native_baseline as native_process
import test_markdown_portable as portable_process

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    'native/ru_markdown_fold.c', 'native/ru_markdown_fold.h',
    'tests/ru_markdown_fold_test_backend.h', 'tests/markdown_fold_host.c',
    'tests/markdown_fold_windows.c', 'tools/test_markdown_fold_helper.py',
    'tools/run_markdown_native_baseline.py', 'tools/test_markdown_portable.py',
    'tools/ru_cli_diagnostics.py',
)
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_LOG_BYTES = portable_process.LIMIT
EXPECTED_HOST_CHECKS = 1976
EXPECTED_WINDOWS_CHECKS = 744
EXPECTED_QUALIFICATION_BOUNDARIES = 88


def digest(data: bytes) -> dict:
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def fingerprint(path: Path, maximum: int = MAX_FILE_BYTES, *, compiler=False) -> dict:
    sha = native_process.digest_file(path, maximum, trusted_compiler=compiler)
    return {'bytes': path.stat().st_size, 'sha256': sha}


def read_bounded(path: Path, maximum: int) -> bytes:
    native_process.safe_path(path)
    with path.open('rb') as stream:
        value = stream.read(maximum + 1)
    if len(value) > maximum:
        raise ControlFailure('file_bounds')
    return value


def parse_result(output: bytes, real: bool) -> dict:
    if not output or len(output) > 1024 or not output.endswith(b'\n'):
        raise ControlFailure('runtime_shape')
    value = json.loads(output.decode('ascii'), object_pairs_hook=native_process.unique_object)
    expected = ({'kind': 'windows_runtime', 'checks': EXPECTED_WINDOWS_CHECKS,
                 'cross_thread': True, 'real_windows_runtime': True, 'ok': True}
                if real else
                {'kind': 'host_fake_backend', 'checks': EXPECTED_HOST_CHECKS,
                 'qualification_boundaries': EXPECTED_QUALIFICATION_BOUNDARIES,
                 'real_windows_runtime': False, 'ok': True})
    if (type(value) is not dict or value.keys() != expected.keys() or
            any(type(value[key]) is not type(wanted) or value[key] != wanted
                for key, wanted in expected.items())):
        raise ControlFailure('runtime_shape')
    return value


def parser_controls() -> int:
    checks = 0
    for real in (False, True):
        value = ({'kind': 'windows_runtime', 'checks': EXPECTED_WINDOWS_CHECKS,
                  'cross_thread': True, 'real_windows_runtime': True, 'ok': True}
                 if real else
                 {'kind': 'host_fake_backend', 'checks': EXPECTED_HOST_CHECKS,
                  'qualification_boundaries': EXPECTED_QUALIFICATION_BOUNDARIES,
                  'real_windows_runtime': False, 'ok': True})
        raw = json.dumps(value).encode('ascii') + b'\n'
        parse_result(raw, real); checks += 1
        invalid = [b'', raw + raw, raw[:-1], b'\xff\n', b'x' * 1025,
                   raw.replace(b'"ok": true', b'"ok": true, "ok": true'),
                   json.dumps({**value, 'extra': 0}).encode('ascii') + b'\n']
        for key in value:
            changed = dict(value); del changed[key]
            invalid.append(json.dumps(changed).encode('ascii') + b'\n')
            changed = dict(value); changed[key] = None
            invalid.append(json.dumps(changed).encode('ascii') + b'\n')
        for sample in invalid:
            try:
                parse_result(sample, real)
            except (ControlFailure, native_process.BaselineError, ValueError, UnicodeError):
                checks += 1
                continue
            raise ControlFailure('parser_negative')
    return checks


def executable(value: str) -> Path:
    found = shutil.which(value)
    return Path(found or value).resolve(strict=True)


def verify_report_owner(path: Path, stream) -> None:
    actual = native_process.safe_path(path).stat()
    owned = os.fstat(stream.fileno())
    if (actual.st_dev, actual.st_ino) != (owned.st_dev, owned.st_ino):
        raise ControlFailure('report_identity')


def report_ownership_controls(private: Path) -> int:
    original, replacement = private / 'owned-report-control', private / 'other-report-control'
    replacement.write_bytes(b'unchanged')
    with original.open('x+', encoding='ascii') as stream:
        verify_report_owner(original, stream)
        try:
            verify_report_owner(replacement, stream)
        except ControlFailure:
            pass
        else:
            raise ControlFailure('report_identity_negative')
        if replacement.read_bytes() != b'unchanged':
            raise ControlFailure('report_identity_negative')
    return 3


class ControlFailure(Exception):
    pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--cc', required=True, help='Native GCC, or Windows x64 GCC for cross controls')
    parser.add_argument('--cross-cc', help='Optional Windows x64 cross compiler on POSIX')
    parser.add_argument('--runtime-dir', type=Path, help='Required on Windows for actual DLL controls')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args()
    report = {'schema': 1, 'control': 'markdown_bounded_fold_v1', 'passed': False,
              'real_windows_runtime': False, 'sanitize': args.sanitize,
              'sources': {}, 'stages': []}
    if args.sanitize:
        report['leak_detection_requested'] = not bool(re.search(
            r'(?:^|:)detect_leaks=(?:0|false)(?::|$)', os.environ.get('ASAN_OPTIONS', '')))
    private_owner = tempfile.TemporaryDirectory(prefix='ru-markdown-fold-controls-')
    private = Path(private_owner.name)
    stage = 'source_inputs'
    output_stream = None

    def command(case_id: str, argv: list[str], timeout: int) -> bytes:
        nonlocal stage
        stage = case_id
        passed, receipt = False, None
        try:
            if os.name == 'nt':
                stdout, receipt = native_process.run_owned_process(argv, ROOT, timeout, private / case_id)
            else:
                stdout = portable_process.checked_run(argv, private, case_id, timeout)
            passed = True
            return stdout
        finally:
            record = {'stage': case_id, 'passed': passed}
            if receipt is not None:
                record['owned_process'] = receipt
            for name in ('stdout', 'stderr'):
                path = private / (case_id + '.' + name)
                if path.is_file():
                    with path.open('rb') as stream:
                        data = stream.read(MAX_LOG_BYTES + 1)
                    record[name] = {**digest(data), 'file_bytes': path.stat().st_size,
                                    'complete': len(data) == path.stat().st_size}
            report['stages'].append(record)

    def runtime_result(case_id: str, output: bytes, real: bool) -> None:
        nonlocal stage
        stage = case_id
        decoded = parse_result(output, real)
        record = {'stage': case_id, 'passed': True, 'checks': decoded['checks'],
                  'real_windows_runtime': real}
        if real:
            record['cross_thread'] = True
        else:
            record['qualification_boundaries'] = decoded['qualification_boundaries']
        report['stages'].append(record)

    try:
        if args.output:
            stage = 'reserve_evidence'
            output = native_process.safe_path(args.output, missing=True)
            output_stream = output.open('x+', encoding='utf-8', newline='\n')
            output_stream.write('{"passed":false,"failure_stage":"in_progress"}\n')
            output_stream.flush()
        stage = 'source_inputs'
        report['sources'] = {name: fingerprint(ROOT / name, 1024*1024) for name in SOURCES}
        report['stages'].append({'stage': 'strict_parser_controls', 'passed': True,
                                 'checks': parser_controls()})
        report['stages'].append({'stage': 'report_ownership_controls', 'passed': True,
                                 'checks': report_ownership_controls(private)})
        stage = 'compiler_inputs'
        cc = executable(args.cc)
        target = command('selected_compiler_target', [str(cc), '-dumpmachine'], 30).decode('ascii').strip()
        if not re.fullmatch(r'[A-Za-z0-9_.+-]+', target):
            raise ControlFailure('selected_compiler_target')
        selected_windows = 'mingw' in target.lower() or 'windows' in target.lower()
        host_cc = cc
        windows_cc = cc if (os.name == 'nt' or selected_windows) else None
        if os.name != 'nt' and selected_windows:
            host_cc = executable('cc')
        if args.cross_cc:
            windows_cc = executable(args.cross_cc)
        if windows_cc:
            report['windows_compiler'] = fingerprint(windows_cc, compiler=True)
            command('windows_compiler_version', [str(windows_cc), '--version'], 30)
        report['host_compiler'] = fingerprint(host_cc, compiler=True)
        command('host_compiler_version', [str(host_cc), '--version'], 30)
        if args.sanitize and os.name == 'nt':
            stage = 'sanitizer_platform'; raise ControlFailure(stage)
        host = private / ('markdown_fold_host.exe' if os.name == 'nt' else 'markdown_fold_host')
        flags = ['-std=c99', '-O1' if args.sanitize else '-O2', '-Wall', '-Wextra', '-Werror']
        if args.sanitize:
            flags += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
        command('compile_host_fixture', [str(host_cc), *flags,
                str(ROOT / 'tests/markdown_fold_host.c'), '-o', str(host)], 120)
        report['host_test_binary'] = fingerprint(host)
        runtime_result('host_controls', command('run_host_fixture', [str(host)], 120), False)

        windows = private / 'markdown_fold_windows.exe'
        if windows_cc:
            command('compile_windows_fixture', [str(windows_cc), '-std=c99', '-O2', '-Wall', '-Wextra',
                    '-Werror', '-static-libgcc', '-Wl,--no-insert-timestamp', '-municode',
                    str(ROOT / 'tests/markdown_fold_windows.c'), '-o', str(windows), '-luser32'], 120)
            stage = 'windows_test_pe'
            binary = read_bounded(windows, MAX_FILE_BYTES)
            if len(binary) < 64 or binary[:2] != b'MZ':
                raise ControlFailure(stage)
            offset = struct.unpack_from('<I', binary, 0x3c)[0]
            if offset > len(binary)-6 or binary[offset:offset+4] != b'PE\0\0' or \
                    struct.unpack_from('<H', binary, offset+4)[0] != 0x8664:
                raise ControlFailure(stage)
            report['windows_test_pe'] = digest(binary)
        else:
            report['stages'].append({'stage': 'compile_windows_fixture', 'status': 'skipped',
                                     'reason': 'no_windows_compiler'})
        runtime, before = None, None
        if args.runtime_dir:
            stage = 'runtime_inputs'
            runtime = native_process.safe_path(args.runtime_dir, directory=True)
            before = {name: fingerprint(runtime / name) for name in ('Scintilla.dll', 'RuSyntax.dll')}
            report['runtime_dlls'] = before
        if os.name == 'nt':
            if runtime is None or windows_cc is None:
                stage = 'runtime_inputs_required'; raise ControlFailure(stage)
            runtime_result('windows_controls', command('run_windows_fixture',
                           [str(windows), str(runtime)], 120), True)
            report['real_windows_runtime'] = True
        else:
            report['stages'].append({'stage': 'windows_controls', 'status': 'skipped',
                                     'reason': 'requires_windows', 'real_windows_runtime': False})
        if runtime is not None:
            stage = 'runtime_inputs_unchanged'
            after = {name: fingerprint(runtime / name) for name in before}
            if before != after:
                raise ControlFailure(stage)
            report['stages'].append({'stage': stage, 'passed': True})
        stage = 'source_and_compiler_inputs_unchanged'
        if ({name: fingerprint(ROOT / name, 1024*1024) for name in SOURCES} != report['sources'] or
                fingerprint(host_cc, compiler=True) != report['host_compiler'] or
                (windows_cc and fingerprint(windows_cc, compiler=True) != report['windows_compiler']) or
                fingerprint(host) != report['host_test_binary'] or
                (windows_cc and fingerprint(windows) != report['windows_test_pe'])):
            raise ControlFailure(stage)
        report['stages'].append({'stage': stage, 'passed': True})
        report['passed'] = True
    except Exception as error:
        report['failure_stage'] = stage
        report['failure_kind'] = 'control_failed'
        report['failure_detail'] = digest(str(error).encode('utf-8', errors='replace'))
    try:
        private_owner.cleanup()
    except OSError:
        report['passed'] = False
        report['failure_stage'] = 'private_cleanup'
    encoded = json.dumps(report, sort_keys=True, indent=2) + '\n'
    if output_stream is not None:
        try:
            if len(encoded.encode('utf-8')) > 65536:
                raise ControlFailure('report_bounds')
            verify_report_owner(output, output_stream)
            output_stream.seek(0)
            output_stream.write(encoded)
            output_stream.truncate()
            output_stream.flush()
        except Exception:
            print(json.dumps({'control': report['control'], 'passed': False,
                              'failure_stage': 'write_evidence'}))
            return 1
        finally:
            output_stream.close()
    print(encoded, end='')
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
