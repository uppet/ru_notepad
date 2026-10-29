#!/usr/bin/env python3
"""Offline bounded Windows native baseline. Never application acceptance.

Three fresh processes, each with three fresh editors. The native-host final fold
levels are a predetermined corpus oracle, not a Markdown parser implementation.
All diagnostics contain fixed codes, public hashes and bounded numeric data.
"""
from __future__ import annotations
import argparse
import ast
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import statistics
import subprocess
import sys
import tempfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'benchmarks/markdown_baseline.c'
INPUT_SHA256 = '2d9f79ee715b217c00792cf18a67485cdec96a14ea2ac86689156941a022c719'
STYLE_FNV = 'f3e8304ab5c43d36'
FOLD_FNV = {'untouched_default': '08c4ea94396a8f49', 'predetermined_final': '14a0b025819607a9'}
COMPONENTS = ('colourise', 'fold_writes', 'read_to_paint')
TICK_FIELDS = ('read_ticks', 'setup_ticks', 'load_ticks', 'style_ticks', 'fold_ticks', 'paint_ticks')
BUILD_SECONDS, SAMPLE_SECONDS, TOTAL_SECONDS = 60, 15, 120
REPETITIONS, MAX_LOG_BYTES, MAX_REPORT_BYTES = 3, 16384, 65536
JOB_MEMORY_BYTES = 512 * 1024 * 1024
FLAGS = ('-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-static-libgcc')
ARCHIVES = {
    'scintilla567.zip': '2309181e59e7da4659f890dbc128db7451ccd094748770e7be674b830494587c',
    'lexilla554.zip': '5e0a21356e4e2f19d6a38ecd1c8172d5a2b7b4542940568b023386080db90fe0'}
DEPENDENCIES = {'Scintilla.dll': 'vendor/scintilla/bin/Scintilla.dll',
                'Lexilla.dll': 'vendor/lexilla/bin/lexilla.dll'}
HEADERS = ('Scintilla.h', 'Sci_Position.h')
PRESENTATION = {'client_width': 960, 'client_height': 640, 'dpi': 96, 'font': 'Consolas',
                'font_points': 11, 'wrap': 'none', 'scrollbars': False, 'technology': 'gdi'}
PROOFS = {'verified_bytes': 1000000, 'verified_lines': 100001, 'style_fnv1a64': STYLE_FNV,
          'dirty': False, 'anchor': 2, 'caret': 19, 'can_undo': False, 'can_redo': False,
          'undo_collection': True, 'all_visible': True, 'all_expanded': True, 'end_styled': 1000000}
ERRORS = frozenset(('arguments', 'windows_required', 'unsafe_path', 'file_type', 'file_bounds',
    'file_changed', 'output_exists', 'corpus_definition', 'corpus_identity', 'archive_identity',
    'dependency_identity', 'process_launch', 'process_job', 'process_resume', 'process_wait',
    'process_timeout', 'process_output_bound', 'process_cleanup', 'process_failed',
    'process_stderr', 'sample_json', 'sample_schema', 'sample_identity', 'sample_ticks',
    'sample_proof', 'summary_schema', 'summary_statistics', 'budget', 'io_error', 'internal_error'))

class BaselineError(Exception):
    pass


def require(condition, code):
    if not condition:
        raise BaselineError(code)


def safe_path(value, *, directory=False, missing=False, trusted_compiler=False):
    path = Path(value)
    require('\0' not in str(path) and '..' not in path.parts, 'unsafe_path')
    path = path.absolute()
    if os.name == 'nt':
        require(path.drive and not path.drive.startswith('\\\\') and ':' not in str(path)[2:], 'unsafe_path')
        reserved = {'con', 'prn', 'aux', 'nul'} | {name + str(i) for name in ('com', 'lpt') for i in range(1, 10)}
        require(all(part.rstrip(' .') == part and not any(c in part for c in '<>:\"|?*') and
                    part.split('.')[0].casefold() not in reserved for part in path.parts[1:]), 'unsafe_path')
    chain = list(reversed(path.parents)) + [path]
    for item in chain:
        if missing and item == path and not item.exists():
            continue
        info = item.lstat()
        require(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400,
                'unsafe_path')
        if item != path or directory:
            require(stat.S_ISDIR(info.st_mode), 'file_type')
        else:
            require(stat.S_ISREG(info.st_mode) and (info.st_nlink == 1 or trusted_compiler), 'file_type')
    return path


def digest_file(path, maximum=64 * 1024 * 1024, *, trusted_compiler=False):
    path = safe_path(path, trusted_compiler=trusted_compiler)
    before = path.stat()
    require(0 < before.st_size <= maximum, 'file_bounds')
    digest = hashlib.sha256()
    total = 0
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(65536), b''):
            total += len(block)
            require(total <= maximum, 'file_bounds')
            digest.update(block)
    after = path.stat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), 'file_changed')
    return digest.hexdigest()


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, 'sample_json')
        value[key] = item
    return value


def exact(value, expected):
    return type(value) is type(expected) and value == expected


def strict_equal(value, expected):
    if type(value) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(value) == set(expected) and all(strict_equal(value[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return len(value) == len(expected) and all(strict_equal(a, b) for a, b in zip(value, expected))
    return value == expected


def fixture():
    """Extract only the existing corpus function, not the application CI module."""
    with safe_path(ROOT / 'tools/windows_ci.py').open('rb') as stream:
        encoded = stream.read(1024 * 1024 + 1)
    require(0 < len(encoded) <= 1024 * 1024, 'file_bounds')
    source = encoded.decode('utf-8')
    nodes = ast.parse(source).body
    functions = [n for n in nodes if isinstance(n, ast.FunctionDef) and n.name == 'gui_markdown_fixture']
    sizes = [n for n in nodes if isinstance(n, ast.Assign) and any(
        isinstance(t, ast.Name) and t.id == 'GUI_MARKDOWN_BYTES' for t in n.targets)]
    require(len(functions) == len(sizes) == 1 and ast.literal_eval(sizes[0].value) == 1000000,
            'corpus_definition')
    scope = {'GUI_MARKDOWN_BYTES': 1000000}
    exec(compile(ast.Module(body=functions, type_ignores=[]), 'fixed_corpus', 'exec'), scope)
    data, _, _ = scope['gui_markdown_fixture']('unclosed-fence')
    expected = b'# Heading\n\n~~~\n' + (b'code text\n' * 100000)[:999977] + b'codebody'
    require(type(data) is bytes and data == expected and len(data) == 1000000 and
            data.count(b'\n') == 100000 and hashlib.sha256(data).hexdigest() == INPUT_SHA256,
            'corpus_identity')
    return data


def parse_sample(raw, run):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_LOG_BYTES, 'sample_json')
    try:
        sample = json.loads(raw.decode('ascii'), object_pairs_hook=unique_object,
                            parse_constant=lambda _: (_ for _ in ()).throw(BaselineError('sample_json')))
    except (ValueError, UnicodeError):
        raise BaselineError('sample_json') from None
    require(type(sample) is dict and set(sample) ==
            {'schema', 'run', 'qpc_frequency', 'cleanup', 'components'} | set(PRESENTATION), 'sample_schema')
    require(exact(sample['schema'], 1) and exact(sample['run'], run) and exact(sample['cleanup'], True),
            'sample_identity')
    require(all(exact(sample[k], v) for k, v in PRESENTATION.items()), 'sample_identity')
    frequency = sample['qpc_frequency']
    require(type(frequency) is int and 0 < frequency <= 1000000000, 'sample_ticks')
    rows = sample['components']
    require(type(rows) is list and len(rows) == 3, 'sample_schema')
    previous_end = 0
    for index, (name, row) in enumerate(zip(COMPONENTS, rows)):
        require(type(row) is dict and set(row) == {'component', 'qpc_start', 'qpc_end', 'fold_mode',
                'fold_fnv1a64', 'fold_writes', 'paint_count'} | set(TICK_FIELDS) | set(PROOFS), 'sample_schema')
        require(row['component'] == name, 'sample_identity')
        start, end = row['qpc_start'], row['qpc_end']
        require(type(start) is int and type(end) is int and 0 <= previous_end < start < end < 2**63,
                'sample_ticks')
        require(end - start <= frequency * SAMPLE_SECONDS, 'sample_ticks')
        previous_end = end
        require(all(type(row[k]) is int and 0 <= row[k] <= frequency * SAMPLE_SECONDS for k in TICK_FIELDS),
                'sample_ticks')
        require(sum(row[k] for k in TICK_FIELDS) == end - start, 'sample_ticks')
        active = ('style_ticks',) if index == 0 else ('fold_ticks',) if index == 1 else TICK_FIELDS
        require(all((row[k] > 0) == (k in active) for k in TICK_FIELDS), 'sample_ticks')
        mode = 'untouched_default' if index == 0 else 'predetermined_final'
        expected = {**PROOFS, 'fold_mode': mode, 'fold_fnv1a64': FOLD_FNV[mode],
                    'fold_writes': 0 if index == 0 else 100001, 'paint_count': 1 if index == 2 else 0}
        require(all(exact(row[k], v) for k, v in expected.items()), 'sample_proof')
    require(rows[-1]['qpc_end'] - rows[0]['qpc_start'] <= frequency * SAMPLE_SECONDS, 'sample_ticks')
    return sample


def statistics_for(samples):
    require(type(samples) is list and len(samples) == REPETITIONS, 'summary_schema')
    checked = [parse_sample(json.dumps(sample, allow_nan=False).encode('ascii'), run)
               for run, sample in enumerate(samples, 1)]
    stats = {}
    for index, component in enumerate(COMPONENTS):
        timings = [(s['components'][index]['qpc_end'] - s['components'][index]['qpc_start']) *
                   1000 / s['qpc_frequency'] for s in checked]
        stats[component] = {'min_ms': min(timings), 'median_ms': statistics.median(timings),
                            'max_ms': max(timings), 'samples_ms': timings}
    return stats


def run_owned_process(arguments, cwd, seconds, log_prefix):
    """Suspended CreateProcess -> private job -> ResumeThread, no launch race.

    The job owns all compiler descendants. Only the three chosen I/O handles are
    inherited. Every failure path terminates the job (or its suspended process
    if assignment failed), waits, verifies zero active processes, then closes it.
    No taskkill, shell command, process search, or global process mutation.
    """
    require(os.name == 'nt', 'windows_required')
    import ctypes as C
    from ctypes import wintypes as W
    import msvcrt
    kernel = C.WinDLL('kernel32', use_last_error=True)
    SIZE = C.c_size_t
    class STARTUPINFO(C.Structure):
        _fields_ = [('cb', W.DWORD), ('reserved', W.LPWSTR), ('desktop', W.LPWSTR), ('title', W.LPWSTR),
            ('x', W.DWORD), ('y', W.DWORD), ('cx', W.DWORD), ('cy', W.DWORD), ('charsx', W.DWORD),
            ('charsy', W.DWORD), ('fill', W.DWORD), ('flags', W.DWORD), ('show', W.WORD),
            ('reserved2size', W.WORD), ('reserved2', C.c_void_p), ('stdin', W.HANDLE),
            ('stdout', W.HANDLE), ('stderr', W.HANDLE)]
    class STARTUPINFOEX(C.Structure):
        _fields_ = [('base', STARTUPINFO), ('attributes', C.c_void_p)]
    class PROCESSINFO(C.Structure):
        _fields_ = [('process', W.HANDLE), ('thread', W.HANDLE), ('pid', W.DWORD), ('tid', W.DWORD)]
    class BASICLIMIT(C.Structure):
        _fields_ = [('user', C.c_longlong), ('jobuser', C.c_longlong), ('flags', W.DWORD),
            ('minwork', SIZE), ('maxwork', SIZE), ('active', W.DWORD), ('affinity', SIZE),
            ('priority', W.DWORD), ('scheduling', W.DWORD)]
    class IOLIMIT(C.Structure):
        _fields_ = [(name, C.c_ulonglong) for name in ('readops','writeops','otherops','read','write','other')]
    class LIMIT(C.Structure):
        _fields_ = [('basic', BASICLIMIT), ('io', IOLIMIT), ('processmem', SIZE), ('jobmem', SIZE),
                    ('peakprocess', SIZE), ('peakjob', SIZE)]
    class ACCOUNTING(C.Structure):
        _fields_ = [(name, C.c_longlong) for name in ('user','kernel','perioduser','periodkernel')] + [
            ('faults', W.DWORD), ('total', W.DWORD), ('active', W.DWORD), ('terminated', W.DWORD)]
    signatures = {
        'CreateJobObjectW': ([C.c_void_p, W.LPCWSTR], W.HANDLE),
        'SetInformationJobObject': ([W.HANDLE, C.c_int, C.c_void_p, W.DWORD], W.BOOL),
        'QueryInformationJobObject': ([W.HANDLE, C.c_int, C.c_void_p, W.DWORD, C.c_void_p], W.BOOL),
        'AssignProcessToJobObject': ([W.HANDLE, W.HANDLE], W.BOOL),
        'TerminateJobObject': ([W.HANDLE, W.UINT], W.BOOL),
        'TerminateProcess': ([W.HANDLE, W.UINT], W.BOOL),
        'WaitForSingleObject': ([W.HANDLE, W.DWORD], W.DWORD),
        'GetExitCodeProcess': ([W.HANDLE, C.POINTER(W.DWORD)], W.BOOL),
        'ResumeThread': ([W.HANDLE], W.DWORD),
        'CloseHandle': ([W.HANDLE], W.BOOL),
        'InitializeProcThreadAttributeList': ([C.c_void_p, W.DWORD, W.DWORD, C.POINTER(SIZE)], W.BOOL),
        'UpdateProcThreadAttribute': ([C.c_void_p, W.DWORD, SIZE, C.c_void_p, SIZE, C.c_void_p, C.c_void_p], W.BOOL),
        'DeleteProcThreadAttributeList': ([C.c_void_p], None),
        'CreateProcessW': ([W.LPCWSTR, W.LPWSTR, C.c_void_p, C.c_void_p, W.BOOL, W.DWORD,
                            C.c_void_p, W.LPCWSTR, C.c_void_p, C.POINTER(PROCESSINFO)], W.BOOL)}
    for name, (args, result) in signatures.items():
        function = getattr(kernel, name); function.argtypes = args; function.restype = result
    job, info, assigned, initialized = None, PROCESSINFO(), False, False
    attribute_buffer = None
    out_path, err_path = Path(str(log_prefix) + '.stdout'), Path(str(log_prefix) + '.stderr')
    start = time.monotonic()
    error, returncode = None, None
    def active():
        value = ACCOUNTING()
        require(kernel.QueryInformationJobObject(job, 1, C.byref(value), C.sizeof(value), None), 'process_job')
        return value.active
    with ExitStack() as stack:
        stdout = stack.enter_context(out_path.open('xb'))
        stderr = stack.enter_context(err_path.open('xb'))
        stdin = stack.enter_context(open(os.devnull, 'rb'))
        handles = [msvcrt.get_osfhandle(stream.fileno()) for stream in (stdin, stdout, stderr)]
        try:
            job = kernel.CreateJobObjectW(None, None)
            require(job, 'process_job')
            limits = LIMIT(); limits.basic.flags = 0x2000 | 0x8 | 0x200
            limits.basic.active = 16; limits.jobmem = JOB_MEMORY_BYTES
            require(kernel.SetInformationJobObject(job, 9, C.byref(limits), C.sizeof(limits)), 'process_job')
            length = SIZE()
            kernel.InitializeProcThreadAttributeList(None, 1, 0, C.byref(length))
            require(0 < length.value <= 65536, 'process_launch')
            attribute_buffer = C.create_string_buffer(length.value)
            require(kernel.InitializeProcThreadAttributeList(attribute_buffer, 1, 0, C.byref(length)), 'process_launch')
            initialized = True
            inherited = (W.HANDLE * 3)(*handles)
            require(kernel.UpdateProcThreadAttribute(attribute_buffer, 0, 0x20002, inherited,
                    C.sizeof(inherited), None, None), 'process_launch')
            startup = STARTUPINFOEX(); startup.base.cb = C.sizeof(startup)
            startup.base.flags = 0x100
            startup.base.stdin, startup.base.stdout, startup.base.stderr = handles
            startup.attributes = C.cast(attribute_buffer, C.c_void_p)
            for handle in handles: os.set_handle_inheritable(handle, True)
            command = C.create_unicode_buffer(subprocess.list2cmdline([str(a) for a in arguments]))
            require(kernel.CreateProcessW(str(arguments[0]), command, None, None, True,
                    0x00000004 | 0x00080000 | 0x08000000, None, str(cwd), C.byref(startup), C.byref(info)),
                    'process_launch')
            for handle in handles: os.set_handle_inheritable(handle, False)
            require(kernel.AssignProcessToJobObject(job, info.process), 'process_job')
            assigned = True
            require(kernel.ResumeThread(info.thread) != 0xffffffff, 'process_resume')
            while True:
                require(max(out_path.stat().st_size, err_path.stat().st_size) <= MAX_LOG_BYTES,
                        'process_output_bound')
                elapsed = time.monotonic() - start
                require(elapsed <= seconds, 'process_timeout')
                state = kernel.WaitForSingleObject(info.process, 0)
                require(state in (0, 258), 'process_wait')
                if state == 0 and active() == 0:
                    code = W.DWORD()
                    require(kernel.GetExitCodeProcess(info.process, C.byref(code)), 'process_wait')
                    returncode = code.value
                    break
                time.sleep(0.02)
        except BaselineError as exc:
            error = str(exc)
        finally:
            cleanup_ok = True
            for handle in handles:
                try:
                    os.set_handle_inheritable(handle, False)
                except OSError:
                    cleanup_ok = False
            try:
                if info.process:
                    if assigned:
                        cleanup_ok = bool(kernel.TerminateJobObject(job, 1)) and cleanup_ok
                    else:
                        cleanup_ok = bool(kernel.TerminateProcess(info.process, 1)) and cleanup_ok
                    cleanup_ok = kernel.WaitForSingleObject(info.process, 5000) == 0 and cleanup_ok
                    if assigned:
                        finish = time.monotonic() + 5
                        while active() and time.monotonic() < finish:
                            time.sleep(0.02)
                        cleanup_ok = active() == 0 and cleanup_ok
            except Exception:
                cleanup_ok = False
            finally:
                # Job close remains the final kill-on-close backstop even if an
                # accounting query fails. A failed query can never report pass.
                if info.thread: cleanup_ok = bool(kernel.CloseHandle(info.thread)) and cleanup_ok
                if info.process: cleanup_ok = bool(kernel.CloseHandle(info.process)) and cleanup_ok
                if initialized: kernel.DeleteProcThreadAttributeList(attribute_buffer)
                if job: cleanup_ok = bool(kernel.CloseHandle(job)) and cleanup_ok
            if not cleanup_ok: error = 'process_cleanup'
        require(error is None, error or 'internal_error')
    # Never read more than the fixed cap even after a process has exited.
    with out_path.open('rb') as stream: output = stream.read(MAX_LOG_BYTES + 1)
    with err_path.open('rb') as stream: errors = stream.read(MAX_LOG_BYTES + 1)
    require(max(len(output), len(errors)) <= MAX_LOG_BYTES, 'process_output_bound')
    receipt = {'returncode': returncode, 'cleanup_confirmed': True,
        'wall_ms': round((time.monotonic() - start) * 1000, 3),
        'stdout_bytes': len(output), 'stderr_bytes': len(errors),
        'stdout_sha256': hashlib.sha256(output).hexdigest(), 'stderr_sha256': hashlib.sha256(errors).hexdigest()}
    require(returncode == 0, 'process_failed')
    require(not errors, 'process_stderr')
    return output, receipt


def identities(cc, runtime):
    versions = {'Scintilla.dll': '5.6.7', 'Lexilla.dll': '5.5.4'}
    archives = {name: digest_file(ROOT / 'third_party/source_archives' / name) for name in ARCHIVES}
    require(archives == ARCHIVES, 'archive_identity')
    with zipfile.ZipFile(ROOT / 'third_party/source_archives/scintilla567.zip') as archive:
        for name in HEADERS:
            info = archive.getinfo('scintilla/include/' + name)
            require(0 < info.file_size <= 262144, 'archive_identity')
            require(hashlib.sha256(archive.read(info)).hexdigest() ==
                    digest_file(ROOT / 'vendor/scintilla/include' / name, 262144), 'archive_identity')
    dlls = {}
    for name, vendor in DEPENDENCIES.items():
        installed, built = digest_file(runtime / name), digest_file(ROOT / vendor)
        require(installed == built, 'dependency_identity')
        dlls[name] = {'version': versions[name], 'sha256': installed}
    return {'native_source_sha256': digest_file(SOURCE, 262144),
        'runner_source_sha256': digest_file(Path(__file__), 262144),
        'corpus_source_sha256': digest_file(ROOT / 'tools/windows_ci.py', 1024 * 1024),
        'compiler_sha256': digest_file(cc, trusted_compiler=True), 'archives': archives,
        'headers': {name: digest_file(ROOT / 'vendor/scintilla/include' / name) for name in HEADERS},
        'dependencies': dlls, 'flags': list(FLAGS)}


def remaining(start, cap):
    seconds = min(cap, TOTAL_SECONDS - (time.monotonic() - start))
    require(seconds > 0, 'budget')
    return seconds


def execute(cc, runtime, work):
    require(os.name == 'nt', 'windows_required')
    start = time.monotonic()
    cc, runtime = safe_path(cc, trusted_compiler=True), safe_path(runtime, directory=True)
    before = identities(cc, runtime)
    data = fixture()
    (work / 'fixture.md').write_bytes(data)
    for name in DEPENDENCIES:
        shutil.copyfile(runtime / name, work / name)
        require(digest_file(work / name) == before['dependencies'][name]['sha256'], 'dependency_identity')
    exe = work / 'markdown_native_baseline.exe'
    arguments = [str(cc), *FLAGS, '-I', str(ROOT / 'vendor/scintilla/include'), str(SOURCE),
                 '-o', str(exe), '-luser32', '-lgdi32']
    _, build = run_owned_process(arguments, work, remaining(start, BUILD_SECONDS), work / 'build')
    executable_hash = digest_file(exe)
    samples, receipts = [], []
    for run in range(1, REPETITIONS + 1):
        require(identities(cc, runtime) == before and digest_file(exe) == executable_hash, 'file_changed')
        for name in DEPENDENCIES:
            require(digest_file(work / name) == before['dependencies'][name]['sha256'], 'dependency_identity')
        require(digest_file(work / 'fixture.md') == INPUT_SHA256, 'corpus_identity')
        raw, receipt = run_owned_process([str(exe), '--run', str(run)], work,
            remaining(start, SAMPLE_SECONDS), work / ('sample-' + str(run)))
        samples.append(parse_sample(raw, run)); receipts.append(receipt)
    require(identities(cc, runtime) == before and digest_file(exe) == executable_hash, 'file_changed')
    require(digest_file(work / 'fixture.md') == INPUT_SHA256, 'corpus_identity')
    for name in DEPENDENCIES:
        require(digest_file(work / name) == before['dependencies'][name]['sha256'], 'dependency_identity')
    require(time.monotonic() - start < TOTAL_SECONDS, 'budget')
    return {'schema': 1, 'status': 'passed', 'scope': 'native_host_only_not_product_acceptance',
        'corpus': {'kind': 'unclosed-fence', 'bytes': 1000000, 'lf_count': 100000,
                   'document_lines': 100001, 'sha256': INPUT_SHA256},
        'budgets': {'build_seconds': BUILD_SECONDS, 'process_seconds': SAMPLE_SECONDS,
                    'total_seconds': TOTAL_SECONDS, 'repetitions': REPETITIONS,
                    'max_log_bytes': MAX_LOG_BYTES, 'job_memory_bytes': JOB_MEMORY_BYTES},
        'identity': {**before, 'executable_sha256': executable_hash}, 'build': build,
        'processes': receipts, 'samples': samples, 'statistics': statistics_for(samples)}


def validate_summary(value):
    require(type(value) is dict and set(value) == {'schema', 'status', 'scope', 'corpus', 'budgets',
            'identity', 'build', 'processes', 'samples', 'statistics'}, 'summary_schema')
    require(exact(value['schema'], 1) and value['status'] == 'passed' and
            value['scope'] == 'native_host_only_not_product_acceptance', 'summary_schema')
    require(strict_equal(value['corpus'], {'kind': 'unclosed-fence', 'bytes': 1000000, 'lf_count': 100000,
            'document_lines': 100001, 'sha256': INPUT_SHA256}), 'summary_schema')
    require(strict_equal(value['budgets'], {'build_seconds': BUILD_SECONDS, 'process_seconds': SAMPLE_SECONDS,
            'total_seconds': TOTAL_SECONDS, 'repetitions': REPETITIONS,
            'max_log_bytes': MAX_LOG_BYTES, 'job_memory_bytes': JOB_MEMORY_BYTES}), 'summary_schema')
    identity = value['identity']
    require(type(identity) is dict and set(identity) == {'native_source_sha256', 'runner_source_sha256',
            'corpus_source_sha256', 'compiler_sha256', 'archives', 'headers', 'dependencies',
            'flags', 'executable_sha256'}, 'summary_schema')
    is_sha = lambda v: type(v) is str and re.fullmatch('[a-f0-9]{64}', v) is not None and v != '0' * 64
    require(all(is_sha(identity[k]) for k in ('native_source_sha256', 'runner_source_sha256',
            'corpus_source_sha256', 'compiler_sha256', 'executable_sha256')) and
            identity['archives'] == ARCHIVES and identity['flags'] == list(FLAGS), 'summary_schema')
    require(type(identity['headers']) is dict and set(identity['headers']) == set(HEADERS) and
            all(is_sha(v) for v in identity['headers'].values()), 'summary_schema')
    deps = identity['dependencies']
    require(type(deps) is dict and set(deps) == set(DEPENDENCIES), 'summary_schema')
    for name, version in (('Scintilla.dll', '5.6.7'), ('Lexilla.dll', '5.5.4')):
        require(type(deps[name]) is dict and set(deps[name]) == {'version', 'sha256'} and
                deps[name]['version'] == version and is_sha(deps[name]['sha256']), 'summary_schema')
    require(type(value['processes']) is list and len(value['processes']) == REPETITIONS, 'summary_schema')
    for index, row in enumerate([value['build'], *value['processes']]):
        require(type(row) is dict and set(row) == {'returncode', 'cleanup_confirmed', 'wall_ms',
            'stdout_bytes', 'stderr_bytes', 'stdout_sha256', 'stderr_sha256'}, 'summary_schema')
        require(exact(row['returncode'], 0) and exact(row['cleanup_confirmed'], True) and
            type(row['wall_ms']) in (int, float) and 0 <= row['wall_ms'] <=
            ((BUILD_SECONDS if index == 0 else SAMPLE_SECONDS) + 10) * 1000 and
            type(row['stdout_bytes']) is int and 0 <= row['stdout_bytes'] <= MAX_LOG_BYTES and
            exact(row['stderr_bytes'], 0) and is_sha(row['stdout_sha256']) and
            row['stderr_sha256'] == hashlib.sha256(b'').hexdigest(), 'summary_schema')
    require(strict_equal(value['statistics'], statistics_for(value['samples'])), 'summary_statistics')
    for process, sample in zip(value['processes'], value['samples']):
        span_ms = (sample['components'][-1]['qpc_end'] - sample['components'][0]['qpc_start']) * 1000 / sample['qpc_frequency']
        require(span_ms <= process['wall_ms'] + 0.001, 'summary_schema')
    require(sum(row['wall_ms'] for row in [value['build'], *value['processes']]) <= TOTAL_SECONDS * 1000,
            'summary_schema')
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc', required=True)
    parser.add_argument('--runtime-dir', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    output, report = None, None
    result = None
    try:
        output = safe_path(args.output, missing=True)
        require(not output.exists(), 'output_exists')
        # Reserve a new report before work. Existing artifacts are never replaced.
        report = output.open('x+', encoding='utf-8', newline='\n')
        report.write('{"schema":1,"status":"failed","error":"in_progress"}\n')
        report.flush()
        with tempfile.TemporaryDirectory(prefix='ru-notepad-native-private-') as temporary:
            work = safe_path(temporary, directory=True)
            result = validate_summary(execute(args.cc, args.runtime_dir, work))
    except Exception as exc:
        code = str(exc) if isinstance(exc, BaselineError) and str(exc) in ERRORS else (
            'io_error' if isinstance(exc, OSError) else 'internal_error')
        result = {'schema': 1, 'status': 'failed', 'error': code}
    payload = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n'
    if report is not None:
        try:
            require(len(payload.encode('utf-8')) <= MAX_REPORT_BYTES, 'file_bounds')
            actual, owned = safe_path(output).stat(), os.fstat(report.fileno())
            require((actual.st_dev, actual.st_ino) == (owned.st_dev, owned.st_ino), 'file_changed')
            report.seek(0); report.write(payload); report.truncate(); report.flush()
        except Exception:
            print('MD_NATIVE_BASELINE_FAILED report_write')
            return 1
        finally:
            report.close()
    print('MD_NATIVE_BASELINE_' + ('PASSED' if result['status'] == 'passed' else 'FAILED ' + result['error']))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
