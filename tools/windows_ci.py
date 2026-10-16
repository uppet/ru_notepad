#!/usr/bin/env python3
"""Real-Windows acceptance and portable CI packaging; never emulates a pass.

Only fresh synthetic outputs from --bin-dir are collected. No Temp scan, user
logs, home directories, screenshots, environment dumps, or developer receipts.
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
# Resolve only our adjacent reviewed packaging module, including under -I in
# the Linux policy job; never rely on the caller's PYTHONPATH or current dir.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import package as portable

ROOT = Path(__file__).resolve().parents[1]
MAX_LOG_BYTES = 1024 * 1024
MAIN_CLASS = 'RuNotepad.Main.0.1'
BINARY_NAMES = list(portable.BINARY_NAMES)
# Each required console executable must run and report its exact assertion count.
NATIVE_CONSOLE_TESTS = (
    ('document_policy', r'^TOTAL PASS: 23\s*$'),
    ('ui_arguments', r'^TOTAL PASS: 19\s*$'),
    ('file_codec_flags', r'^TOTAL PASS: 80\s*$'),
    ('editor_native', r'^TOTAL PASS: 27\s*$'),
    ('app_native', r'^TOTAL PASS: 23\s*$'),
    ('app_features_native', r'^TOTAL PASS: 23\s*$'),
    ('app_streaming_native', r'^APP_STREAMING_TESTS_PASS=63\s*$'),
    ('file_codec_tests', r'^FILE_CODEC_TESTS_PASS=73\s*$'),
    ('file_streaming_native', r'^FILE_STREAMING_TESTS_PASS=99\s*$'),
    ('editor_streaming_native', r'^EDITOR_STREAMING_TESTS_PASS=21\s*$'),
    ('editor_largefile_native', r'^EDITOR_LARGEFILE_TESTS_PASS=10\s*$'),
    ('associations_policy', r'^TOTAL PASS: 19\s*$'),
    ('associations_native', r'^TOTAL PASS: 36\s*$'),
    ('file_drop_native', r'^TOTAL PASS: 38\s*$'),
    ('shortcuts', r'^TOTAL PASS: 42\s*$'),
    ('syntax_policy', r'^TOTAL PASS: 108\s*$'),
    ('status_native', r'^TOTAL PASS: 21\s*$'),
    ('syntax_native', r'^TOTAL PASS: 82\s*$'),
    ('app_ru_native', r'^TOTAL PASS: 39\s*$'),
    ('ru_lexical_policy', r'^TOTAL PASS: 338\s*$'),
    ('ru_syntax_native', r'^TOTAL PASS: 119\s*$'),
)
SYNTAX_FALLBACK_TESTS = (
    ('syntax_missing_lexilla', '--expect-missing', False),
    ('syntax_bad_lexer', '--expect-bad-lexer', True),
    ('ru_syntax_missing_lexilla', '--expect-missing-lexilla', False),
    ('ru_syntax_missing_helper', '--expect-missing-helper', False),
    ('ru_syntax_bad_helper', '--expect-bad-helper', False),
    ('ru_syntax_wrong_helper_abi', '--expect-wrong-helper-abi', False),
)
SYNTAX_FALLBACK_EXECUTABLES = {name: 'ru_syntax_native.exe' for name, _, _ in
                               SYNTAX_FALLBACK_TESTS if name.startswith('ru_syntax_')}
HELPER_FALLBACK_LAYOUTS = {'ru_syntax_missing_helper': 'missing',
                          'ru_syntax_bad_helper': 'bad-exports',
                          'ru_syntax_wrong_helper_abi': 'wrong-abi'}
# These limits apply only to the named synthetic suites, never to user files.
# The >500 MB test is mandatory: low disk or timeout fails instead of skipping.
CONSOLE_EXECUTABLES = {'editor_largefile_native': 'editor_streaming_native'}
FIXTURE_ARGUMENT_TESTS = {'file_codec_tests', 'file_streaming_native', 'app_streaming_native',
                        'editor_streaming_native', 'editor_largefile_native', 'app_ru_native'}
CONSOLE_TIMEOUT_SECONDS = {'file_streaming_native': 300, 'app_streaming_native': 180,
                           'editor_streaming_native': 300,
                           'editor_largefile_native': 900, 'app_ru_native': 180}
LARGE_FILE_MIN_FREE_BYTES = 2 * 1024 * 1024 * 1024
GUI_FILE_CHECKS = ('cli_unicode_paths', 'cli_exact_text', 'drop_unicode_paths',
                   'drop_exact_text', 'child_drop_routed', 'busy_observed', 'busy_responsive',
                   'cancel_no_partial_tab', 'cancel_queue_cleared', 'source_bytes_preserved')
GUI_RU_CHECKS = ('cli_unicode_path', 'cli_exact_text', 'automatic_ru_styles',
                 'actual_fold_headers', 'collapse_hides_children', 'same_ru_preserves_collapse',
                 'expand_restores_visibility',
                 'plain_clears_styles_folds', 'plain_restores_visibility',
                 'ru_restores_styles_folds', 'ru_restores_visibility',
                 'document_clean', 'text_bytes_preserved', 'source_bytes_preserved',
                 'timer_child_drop_routed', 'timer_exact_length', 'timer_document_clean',
                 'timer_head_styles', 'timer_tail_styles', 'timer_status_cleared',
                 'timer_source_bytes_preserved', 'edit_fixture_loaded', 'edit_all_operations',
                 'edit_style_fold_probes', 'edit_dirty_transitions', 'edit_source_bytes_preserved',
                 'edit_undo_clean')
GUI_NAMES = {'main-gui-smoke', 'main-gui-file-entry', 'main-gui-ru-syntax'}
# Byte/work bounds are deterministic acceptance limits. Elapsed time is
# measured and reported, not compared with an invented hardware-independent SLA.
RU_PERFORMANCE_SIZES = (100000, 1000000)
RU_PERFORMANCE_INTEGER_FIELDS = ('size', 'initial_read_bytes', 'edit_read_bytes',
                                 'reused_bytes', 'max_read')
RU_PERFORMANCE_TIME_FIELDS = ('initial_ms', 'edit_ms', 'max_tick_ms', 'max_chunk_ms')
RU_PERFORMANCE_FIELDS = set(RU_PERFORMANCE_INTEGER_FIELDS + RU_PERFORMANCE_TIME_FIELDS)
GUI_RU_TIMER_BYTES = 1000000
GUI_RU_TIMER_TIMEOUT_SECONDS = 30
GUI_RU_EDIT_BYTES = 100000
GUI_RU_EDIT_CHECKS = ('edit_fixture_loaded', 'edit_all_operations', 'edit_style_fold_probes',
                     'edit_dirty_transitions', 'edit_source_bytes_preserved', 'edit_undo_clean')
GUI_RU_EDIT_MEASUREMENT = ('Real child WM_CHAR/Backspace length-changing input; wall time includes '
    'production Reset Zoom 504 status refresh and WM_NULL polling; bounded style/fold/context probes.')
GUI_RU_TIMER_FIELDS = {'size', 'wall_ms', 'first_head_style_ms', 'max_response_ms', 'probes',
                       'source_sha256', 'style_probes', 'last_probe'}
SCANNER_PREFLIGHT_SOURCES = ('tools/test_ru_scan.py', 'src/ru_lexical.ru',
                            'tests/ru_lexical_policy.ru')
SCANNER_PREFLIGHT_REPORT_FIELDS = {'cases', 'chunk_checks', 'ru_assertions_per_backend',
                                  'library_sha256', 'source_sha256', 'sanitizer'}
SCANNER_SANITIZER_SUCCESS = 'PASS: 20000 ASan/UBSan bounded random buffer cases'
HELPER_POLICY_EVIDENCE_FILES = ('helper-policy.stdout.log', 'helper-policy.stderr.log',
    'cleanup-control.stdout.log', 'cleanup-control.stderr.log',
    'bridge-failure.stdout.log', 'bridge-failure.stderr.log',
    'scanner-build.log', 'differential-python.log', 'differential-build.log',
    'differential-c.log', 'sanitize-build.log', 'sanitize.log', 'report.json')
HELPER_POLICY_COMMIT = 'dd6cb81b52a426408f7076d82a84c2fdfb644263'
HELPER_POLICY_TREE = '346d9f3f19c64f50f25b9f47ce92df1ea804bdb8'
GUI_CANCEL_FIXTURE_BYTES = 128 * 1024 * 1024
MAX_GUI_DROP_BATCHES = 4
MAX_GUI_DROP_PAYLOAD_BYTES = 65536
SYSTEM_DLLS = portable.SYSTEM_DLLS


def sha(path):
    return portable.sha(path)


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def bounded_text(path):
    if path.stat().st_size > MAX_LOG_BYTES:
        raise RuntimeError(f'{path.name}: synthetic log exceeds 1 MiB limit')
    return path.read_text(encoding='utf-8', errors='replace')


def cap_log(path):
    """Bound only this run's own output before any evidence upload."""
    if path.is_file() and path.stat().st_size > MAX_LOG_BYTES:
        with path.open('r+b') as stream:
            stream.truncate(MAX_LOG_BYTES)


class Windows:
    def __init__(self):
        if hasattr(ctypes.WinDLL('ntdll'), 'wine_get_version'):
            raise RuntimeError('Wine cannot produce native Windows acceptance evidence')
        self.user = ctypes.WinDLL('user32', use_last_error=True)
        self.callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        self.user.EnumWindows.argtypes = [self.callback_type, wintypes.LPARAM]
        self.user.EnumWindows.restype = wintypes.BOOL
        self.user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        self.user.GetWindowThreadProcessId.restype = wintypes.DWORD
        self.user.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.user.GetClassNameW.restype = ctypes.c_int
        self.user.IsWindowVisible.argtypes = [wintypes.HWND]
        self.user.IsWindowVisible.restype = wintypes.BOOL
        self.user.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        self.user.PostMessageW.restype = wintypes.BOOL
        self.user.SendMessageTimeoutW.argtypes = [wintypes.HWND, wintypes.UINT,
            wintypes.WPARAM, wintypes.LPARAM, wintypes.UINT, wintypes.UINT,
            ctypes.POINTER(ctypes.c_size_t)]
        self.user.SendMessageTimeoutW.restype = wintypes.LPARAM
        self.user.EnumChildWindows.argtypes = [wintypes.HWND, self.callback_type, wintypes.LPARAM]
        self.user.EnumChildWindows.restype = wintypes.BOOL
        self.user.GetDlgItem.argtypes = [wintypes.HWND, ctypes.c_int]
        self.user.GetDlgItem.restype = wintypes.HWND
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
        self.kernel.GlobalAlloc.restype = wintypes.HGLOBAL
        self.kernel.GlobalLock.argtypes = [wintypes.HGLOBAL]
        self.kernel.GlobalLock.restype = ctypes.c_void_p
        self.kernel.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
        self.kernel.GlobalUnlock.restype = wintypes.BOOL
        self.kernel.GlobalFree.argtypes = [wintypes.HGLOBAL]
        self.kernel.GlobalFree.restype = wintypes.HGLOBAL
        self.drop_handles = []

    def windows(self, process_id):
        matches = []
        @self.callback_type
        def visit(hwnd, _):
            owner = wintypes.DWORD()
            self.user.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
            if owner.value == process_id:
                name = ctypes.create_unicode_buffer(256)
                self.user.GetClassNameW(hwnd, name, len(name))
                matches.append((hwnd, name.value, bool(self.user.IsWindowVisible(hwnd))))
            return True
        if not self.user.EnumWindows(visit, 0):
            raise ctypes.WinError(ctypes.get_last_error())
        return matches

    def no_dialog(self, process_id):
        windows = self.windows(process_id)
        if any(name == '#32770' and visible for _, name, visible in windows):
            raise RuntimeError('Unexpected modal dialog in synthetic native test')
        return windows

    def responsive(self, hwnd):
        result = ctypes.c_size_t()
        if not self.user.SendMessageTimeoutW(hwnd, 0, 0, 0, 3, 5000, ctypes.byref(result)):
            raise RuntimeError('Visible main HWND did not respond to WM_NULL within 5 seconds')

    def close(self, hwnd):
        if not self.user.PostMessageW(hwnd, 0x0010, 0, 0):  # WM_CLOSE, ordinary app shutdown
            raise ctypes.WinError(ctypes.get_last_error())

    def scalar(self, hwnd, message, wparam=0, lparam=0):
        result = ctypes.c_size_t()
        if not self.user.SendMessageTimeoutW(hwnd, message, wparam, lparam, 3, 5000,
                                             ctypes.byref(result)):
            raise RuntimeError('Synthetic GUI query did not respond within 5 seconds')
        return result.value

    def text(self, hwnd):
        # WM_GETTEXT is a system message with cross-process marshalling. Never
        # pass a local pointer to a private Scintilla/WM_USER message.
        length = self.scalar(hwnd, 0x000E)
        if length > 4096:
            raise RuntimeError('Synthetic GUI text exceeds the bounded inspection limit')
        buffer = ctypes.create_unicode_buffer(length + 1)
        self.scalar(hwnd, 0x000D, length + 1, ctypes.addressof(buffer))
        return buffer.value

    def control(self, hwnd, identifier):
        child = self.user.GetDlgItem(hwnd, identifier)
        if not child:
            raise RuntimeError('Required native GUI control is missing')
        return child

    def editor(self, hwnd):
        matches = []
        @self.callback_type
        def visit(child, _):
            name = ctypes.create_unicode_buffer(256)
            self.user.GetClassNameW(child, name, len(name))
            if name.value == 'Scintilla' and self.user.IsWindowVisible(child):
                matches.append(child)
            return True
        self.user.EnumChildWindows(hwnd, visit, 0)
        if len(matches) != 1:
            raise RuntimeError('Expected exactly one visible native editor')
        return matches[0]

    def editor_bytes(self, hwnd):
        editor = self.editor(hwnd)
        length = self.scalar(editor, 2006)  # SCI_GETLENGTH, no pointer argument
        if length > 4096:
            raise RuntimeError('Small GUI fixture unexpectedly exceeds inspection limit')
        return bytes(self.scalar(editor, 2007, index) & 255 for index in range(length))

    def command(self, hwnd, identifier):
        self.scalar(hwnd, 0x0111, identifier)  # actual WM_COMMAND routing

    def drop(self, hwnd, paths):
        # DROPFILES is five fixed-width fields followed by a double-NUL UTF-16
        # list. Windows marshals this documented system message to the target.
        # After a successful post, do not assume the original HGLOBAL remains
        # sender-owned: the receiver calls DragFinish. Bound test-only retained
        # allocations to four 64 KiB blocks; process exit reclaims any sender
        # allocation Windows retained. No clipboard or real user data changes.
        payload = struct.pack('<IiiII', 20, 0, 0, 0, 1) + (
            '\0'.join(map(str, paths)) + '\0\0').encode('utf-16-le')
        if len(self.drop_handles) >= MAX_GUI_DROP_BATCHES or len(payload) > MAX_GUI_DROP_PAYLOAD_BYTES:
            raise RuntimeError('Synthetic GUI drop exceeds its bounded allocation budget')
        handle = self.kernel.GlobalAlloc(0x0042, len(payload))  # GMEM_MOVEABLE | ZEROINIT
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        pointer = self.kernel.GlobalLock(handle)
        if not pointer:
            self.kernel.GlobalFree(handle)
            raise ctypes.WinError(ctypes.get_last_error())
        ctypes.memmove(pointer, payload, len(payload))
        self.kernel.GlobalUnlock(handle)
        if not self.user.PostMessageW(hwnd, 0x0233, handle, 0):  # WM_DROPFILES
            self.kernel.GlobalFree(handle)
            raise ctypes.WinError(ctypes.get_last_error())
        self.drop_handles.append(handle)

    def release_drops(self):
        # Successfully posted handles may have been consumed by Windows. Never
        # free them again; discard only our bookkeeping after the target exits.
        self.drop_handles.clear()


def cleanup_process(process):
    if process.poll() is not None:
        return False
    # Cleanup is never success. /T covers the optional PowerShell ACL probe child.
    try:
        subprocess.run(['taskkill.exe', '/PID', str(process.pid), '/T', '/F'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=10)
    return True


def validate_ru_performance(records):
    if not isinstance(records, list) or len(records) != len(RU_PERFORMANCE_SIZES):
        raise RuntimeError('Ru performance requires exactly two size-specific measurements')
    sizes = []
    for record in records:
        if not isinstance(record, dict) or set(record) != RU_PERFORMANCE_FIELDS:
            raise RuntimeError('Ru performance fields are missing or unexpected')
        for key in RU_PERFORMANCE_INTEGER_FIELDS:
            if type(record[key]) is not int:
                raise RuntimeError('Ru performance byte counts must be integers')
        for key in RU_PERFORMANCE_TIME_FIELDS:
            value = record[key]
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise RuntimeError('Ru performance times must be finite nonnegative measurements')
        size = record['size']
        sizes.append(size)
        if (record['initial_read_bytes'] != size or not 0 < record['edit_read_bytes'] <= 65536 or
                not 0 < record['reused_bytes'] <= size or not 0 < record['max_read'] <= 1024):
            raise RuntimeError('Ru performance violates the mandatory bounded-read/convergence limits')
    if sorted(sizes) != list(RU_PERFORMANCE_SIZES):
        raise RuntimeError('Ru performance requires one 100 KB and one 1 MB measurement')


def parse_ru_performance(stdout):
    records = []
    for line in stdout.splitlines():
        if not line.startswith('PERF_RU'):
            continue
        fields = line.split()
        if fields[0] != 'PERF_RU':
            raise RuntimeError('Ru performance marker has an invalid prefix')
        record = {}
        for field in fields[1:]:
            if field.count('=') != 1:
                raise RuntimeError('Ru performance marker has a malformed measurement')
            key, value = field.split('=')
            if key in record or key not in RU_PERFORMANCE_FIELDS:
                raise RuntimeError('Ru performance marker has duplicate or unexpected fields')
            try:
                record[key] = int(value) if key in RU_PERFORMANCE_INTEGER_FIELDS else float(value)
            except ValueError as exc:
                raise RuntimeError('Ru performance marker has a nonnumeric measurement') from exc
        records.append(record)
    validate_ru_performance(records)
    return records


def run_console(api, name, command, evidence, marker, timeout=120, expected_assertions=None, cwd=None):
    out, err = evidence / f'{name}.stdout.log', evidence / f'{name}.stderr.log'
    result = {'name': name, 'passed': False, 'executed': False, 'cleanup_killed': False}
    started = time.monotonic()
    process = None
    try:
        with out.open('xb') as stdout, err.open('xb') as stderr:
            process = subprocess.Popen(command, cwd=cwd or ROOT, stdout=stdout, stderr=stderr)
            result['executed'] = True
            deadline = time.monotonic() + timeout
            while process.poll() is None:
                api.no_dialog(process.pid)
                if time.monotonic() >= deadline:
                    raise RuntimeError(f'{name}: exceeded {timeout}-second execution deadline')
                if out.stat().st_size > MAX_LOG_BYTES or err.stat().st_size > MAX_LOG_BYTES:
                    raise RuntimeError(f'{name}: exceeded synthetic log size limit')
                time.sleep(0.1)
            result['exit_code'] = process.returncode
        stdout_text, stderr_text = bounded_text(out), bounded_text(err)
        result['assertions_passed'] = len(re.findall(r'^PASS:', stdout_text, re.M))
        result['skips'] = re.findall(r'^SKIP:.*$', stdout_text + stderr_text, re.M)
        if result['skips']:
            raise RuntimeError(f'{name}: required native gate skipped a case: {result["skips"]}')
        if process.returncode != 0:
            raise RuntimeError(f'{name}: nonzero exit status {process.returncode}')
        totals = re.findall(r'^(?:TOTAL PASS:|[A-Z][A-Z0-9_]*_TESTS_PASS(?:=|\b)).*$', stdout_text, re.M)
        if len(totals) != 1 or len(re.findall(marker, stdout_text, re.M)) != 1 or 'FAIL:' in stdout_text + stderr_text:
            raise RuntimeError(f'{name}: exact unique success marker missing or failure reported')
        if expected_assertions is not None and result['assertions_passed'] != expected_assertions:
            raise RuntimeError(f'{name}: expected {expected_assertions} individual PASS lines, got {result["assertions_passed"]}')
        if name == 'ru_syntax_native':
            result['performance'] = parse_ru_performance(stdout_text)
        result['passed'] = True
    except Exception as exc:
        result['error'] = str(exc)
    finally:
        if process is not None:
            result['cleanup_killed'] = cleanup_process(process)
            if result['cleanup_killed']:
                result['passed'] = False
        for path in (out, err):
            cap_log(path)
        result['seconds'] = round(time.monotonic() - started, 3)
    return result


def scanner_preflight_sources(root):
    return portable.native_source_snapshot(root) | {
        name: sha(portable.source_file(root, name)) for name in SCANNER_PREFLIGHT_SOURCES}


def helper_policy_inputs(root):
    compiler = root / '.ci/ru-language'
    def git(*args):
        return subprocess.check_output(['git', '-C', str(compiler), *args], text=True, timeout=30).strip()
    commit, tree = git('rev-parse', 'HEAD'), git('rev-parse', 'HEAD^{tree}')
    if commit != HELPER_POLICY_COMMIT or tree != HELPER_POLICY_TREE or git('status', '--porcelain'):
        raise RuntimeError('Helper-policy gate requires the clean reviewed Ru compiler commit/tree')
    return {'ru_commit': commit, 'ru_tree': tree, 'source_sha256': scanner_preflight_sources(root) | {
        name: sha(portable.source_file(root, name))
        for name in ('tools/windows_ci.py', '.github/workflows/windows.yml',
                     'tools/test_cleanup_paths.py', 'tests/ru_syntax_failure_portable.py',
                     'src/main.ru', 'src/ru_syntax.ru', 'tests/ru_syntax_native.ru')}}


def helper_policy_action(action, root):
    directory = root / 'build/logs/014/ru-scan'
    if action == 'prepare':
        inputs = helper_policy_inputs(root)
        directory.mkdir(parents=True, exist_ok=False)  # no stale successes
        save_json(directory / 'helper-policy-inputs.json', inputs)
        return {'prepared': True}
    if action == 'collect':
        destination = root / 'build/helper-policy-evidence'
        destination.mkdir(parents=True, exist_ok=False)
        names = (*HELPER_POLICY_EVIDENCE_FILES, 'helper-policy-inputs.json', 'helper-policy-acceptance.json')
        for name in names:
            path = directory / name
            if path.exists() or path.is_symlink():
                portable.checked_file(path)
                cap_log(path)
                shutil.copyfile(path, destination / name)
        return {'collected': sorted(path.name for path in destination.iterdir())}
    inputs = helper_policy_inputs(root)
    recorded = json.loads(bounded_text(portable.checked_file(directory / 'helper-policy-inputs.json')))
    if recorded != inputs:
        raise RuntimeError('Helper-policy source/compiler inputs changed during testing')
    texts = {name: bounded_text(portable.checked_file(directory / name))
             for name in HELPER_POLICY_EVIDENCE_FILES}
    report = json.loads(texts['report.json'])
    if (not isinstance(report, dict) or set(report) != SCANNER_PREFLIGHT_REPORT_FIELDS or
            any(type(report[key]) is not int or report[key] != count for key, count in
                (('cases', 157), ('chunk_checks', 942), ('ru_assertions_per_backend', 314))) or
            report['sanitizer'] != SCANNER_SANITIZER_SUCCESS):
        raise RuntimeError('Linux helper policy lacks exact differential/fuzz/sanitizer success')
    if (json.loads(texts['helper-policy.stdout.log']) != report or texts['helper-policy.stderr.log'].strip() or
            report['source_sha256'] != inputs['source_sha256']['native/ru_scan.c'] or
            report['library_sha256'] != sha(portable.checked_file(directory / 'libRuSyntax.so'))):
        raise RuntimeError('Linux helper-policy transcript/DLL/source identity mismatch')
    for name in ('differential-python.log', 'differential-c.log'):
        text = texts[name]
        if (re.findall(r'^TOTAL PASS: ([0-9]+)\s*$', text, re.M) != ['314'] or
                len(re.findall(r'^PASS:', text, re.M)) != 314 or
                re.search(r'^(FAIL:|SKIP:)', text, re.M)):
            raise RuntimeError('Linux helper policy lacks 314 full style/fold assertions in each real backend')
    if texts['sanitize.log'].strip() != SCANNER_SANITIZER_SUCCESS:
        raise RuntimeError('Linux helper policy lacks the real clean ASan/UBSan execution marker')
    cleanup = texts['cleanup-control.stdout.log']
    if (re.findall(r'^TOTAL PASS: ([0-9]+)\s*$', cleanup, re.M) != ['8', '8'] or
            re.findall(r'^BACKEND: (.+)$', cleanup, re.M) != ['python', 'c'] or
            len(re.findall(r'^PASS:', cleanup, re.M)) != 17 or
            re.search(r'^(FAIL:|SKIP:)', cleanup, re.M) or
            not cleanup.endswith('PASS: production cleanup rescue bodies and original scalar negative controls in both Ru backends\n') or
            texts['cleanup-control.stderr.log'].strip()):
        raise RuntimeError('Linux cleanup control requires eight real assertions in each backend and both negative controls')
    failure_text = texts['bridge-failure.stderr.log']
    if (texts['bridge-failure.stdout.log'].strip() != 'RU_SYNTAX_FAILURE_PORTABLE_PASS: 6' or
            not re.search(r'^Ran 6 tests in [0-9.]+s$', failure_text, re.M) or
            not re.search(r'^OK$', failure_text, re.M) or
            re.search(r'^(FAILED|ERROR:|FAIL:|OK \(skipped=)', failure_text, re.M)):
        raise RuntimeError('Linux bridge failure controls require all six ordinary Ru tests without skips')
    result = {'passed': True, 'executed': True, 'report': report, **inputs}
    save_json(directory / 'helper-policy-acceptance.json', result)
    return result


def validate_scanner_preflight(record, binary_hashes, root):
    if (not isinstance(record, dict) or record.get('name') != portable.SCANNER_PREFLIGHT_NAME or
            record.get('passed') is not True or record.get('executed') is not True or
            record.get('cleanup_killed') is not False or record.get('exit_code') != 0):
        raise RuntimeError('Exact-DLL scanner preflight did not pass normally')
    report = record.get('report')
    if not isinstance(report, dict) or set(report) != SCANNER_PREFLIGHT_REPORT_FIELDS:
        raise RuntimeError('Exact-DLL scanner preflight report is missing or malformed')
    expected = {'cases': 157, 'chunk_checks': 942, 'ru_assertions_per_backend': 0}
    if any(type(report[key]) is not int or report[key] != value for key, value in expected.items()):
        raise RuntimeError('Exact-DLL scanner preflight did not execute all deterministic boundary/fuzz cases')
    if report['sanitizer'] is not None:
        raise RuntimeError('Windows scanner preflight must not substitute a host sanitizer claim')
    sources = scanner_preflight_sources(root)
    if (record.get('source_sha256') != sources or
            report['source_sha256'] != sources['native/ru_scan.c'] or
            report['library_sha256'] != binary_hashes[portable.NATIVE_HELPER_NAME]):
        raise RuntimeError('Exact-DLL scanner preflight DLL or source snapshot mismatch')


def run_scanner_preflight(api, binary_dir, evidence):
    name = portable.SCANNER_PREFLIGHT_NAME
    out, err = evidence / (name + '.stdout.log'), evidence / (name + '.stderr.log')
    result = {'name': name, 'passed': False, 'executed': False, 'cleanup_killed': False,
              'source_sha256': scanner_preflight_sources(ROOT)}
    library = binary_dir / portable.NATIVE_HELPER_NAME
    binary_hashes = {portable.NATIVE_HELPER_NAME: sha(library)}
    # Isolated mode ignores PYTHONOPTIMIZE/PYTHONPATH so the scanner script's
    # assertions cannot be disabled or shadowed by the host environment.
    command = [sys.executable, '-I', str(ROOT / 'tools/test_ru_scan.py'),
               '--library', str(library), '--fuzz', '100']
    process = None
    started = time.monotonic()
    try:
        with out.open('xb') as stdout, err.open('xb') as stderr:
            process = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr)
            result['executed'] = True
            while process.poll() is None:
                api.no_dialog(process.pid)
                if time.monotonic() - started >= 180:
                    raise RuntimeError('Exact-DLL scanner preflight exceeded 180 seconds')
                if out.stat().st_size > MAX_LOG_BYTES or err.stat().st_size > MAX_LOG_BYTES:
                    raise RuntimeError('Exact-DLL scanner preflight exceeded synthetic log size limit')
                time.sleep(0.1)
            result['exit_code'] = process.returncode
        if process.returncode != 0:
            raise RuntimeError(f'Exact-DLL scanner preflight exited with status {process.returncode}')
        result['report'] = json.loads(bounded_text(out))
        if bounded_text(err).strip():
            raise RuntimeError('Exact-DLL scanner preflight reported unexpected stderr')
        if sha(library) != binary_hashes[portable.NATIVE_HELPER_NAME]:
            raise RuntimeError('Scanner DLL changed during the exact-DLL preflight')
        result['passed'] = True
        validate_scanner_preflight(result, binary_hashes, ROOT)
    except Exception as exc:
        result.update(passed=False, error=str(exc))
    finally:
        if process is not None:
            result['cleanup_killed'] = cleanup_process(process)
            if result['cleanup_killed']:
                result['passed'] = False
        for path in (out, err):
            cap_log(path)
        result['seconds'] = round(time.monotonic() - started, 3)
    return result


def run_gui(api, binary_dir, evidence, *, name='main-gui-smoke', arguments=(),
            exercise=None, log_prefix='main-launcher'):
    result = {'name': name, 'passed': False, 'executed': False,
              'main_hwnd_seen': False, 'close_posted': False, 'cleanup_killed': False,
              'detached_from_console': True}
    started = time.monotonic()
    process = None
    # The dedicated bin dir was just built by this CI run; reject stale logs.
    if list(binary_dir.glob('ru_notepad-*.log')):
        result['error'] = 'Refusing stale launcher logs in fresh test binary directory'
        return result
    try:
        process = subprocess.Popen([str(binary_dir / 'ru_notepad.exe'), *map(str, arguments)], cwd=binary_dir,
                                   creationflags=0x00000008)  # DETACHED_PROCESS
        result['executed'] = True
        deadline = time.monotonic() + 30
        hwnd = None
        while hwnd is None:
            windows = api.no_dialog(process.pid)
            if process.poll() is not None:
                raise RuntimeError(f'GUI exited before a visible main HWND: {process.returncode}')
            visible_main = [handle for handle, name, visible in windows
                            if name == MAIN_CLASS and visible]
            if len(visible_main) == 1:
                hwnd = visible_main[0]
            elif len(visible_main) > 1:
                raise RuntimeError('More than one main HWND belongs to the application')
            if time.monotonic() >= deadline:
                raise RuntimeError('No visible main HWND within 30 seconds')
            time.sleep(0.1)
        result['main_hwnd_seen'] = True
        result['window_class'] = MAIN_CLASS
        # Let queued startup work run, then prove that the actual event loop responds.
        settle_until = time.monotonic() + 1
        while time.monotonic() < settle_until:
            api.no_dialog(process.pid)
            if process.poll() is not None:
                raise RuntimeError('GUI terminated while checking startup stability')
            time.sleep(0.1)
        api.responsive(hwnd)
        api.no_dialog(process.pid)
        if exercise is not None:
            result.update(exercise(process, hwnd))
        api.close(hwnd)
        result['close_posted'] = True
        deadline = time.monotonic() + 15
        while process.poll() is None:
            api.no_dialog(process.pid)
            if time.monotonic() >= deadline:
                raise RuntimeError('GUI did not exit normally within 15 seconds after WM_CLOSE')
            time.sleep(0.1)
        result['exit_code'] = process.returncode
        if process.returncode != 0:
            raise RuntimeError(f'GUI exited with status {process.returncode}')
        logs = list(binary_dir.glob('ru_notepad-*.log'))
        if len(logs) != 1:
            raise RuntimeError('Expected exactly one fresh launcher log beside the application')
        text = bounded_text(logs[0])
        required = ('[launcher] Starting Ru program.', '[startup] menu installed',
                    '[startup] initial document ready', '[startup] main window shown',
                    '[launcher] Ru program returned with status 0.')
        if name in {'main-gui-file-entry', 'main-gui-ru-syntax'}:
            required += ('[operation] open started', '[operation] open completed')
        if name == 'main-gui-file-entry':
            required += ('[operation] cancelled',)
        if any(marker not in text for marker in required):
            raise RuntimeError('Launcher log does not prove full startup and normal return 0')
        if re.search(r'initialization failed|exited before returning|fatal|FAIL:', text, re.I):
            raise RuntimeError('Launcher log records an error despite the exit code')
        result['passed'] = True
    except Exception as exc:
        result['error'] = str(exc)
    finally:
        if process is not None:
            result['cleanup_killed'] = cleanup_process(process)
            if result['cleanup_killed']:
                result['passed'] = False
        # Copy only logs newly produced in this isolated binary directory. Never
        # search fallback Temp, collect user logs, or dereference arbitrary paths.
        logs = sorted(binary_dir.glob('ru_notepad-*.log'))
        for index, path in enumerate(logs[:4]):
            cap_log(path)
            shutil.copyfile(path, evidence / f'{log_prefix}-{index}.log')
        result['seconds'] = round(time.monotonic() - started, 3)
    return result


def wait_gui(api, process, predicate, failure, timeout=30):
    deadline = time.monotonic() + timeout
    while True:
        api.no_dialog(process.pid)
        if process.poll() is not None:
            raise RuntimeError('GUI exited while checking synthetic file operations')
        if predicate():
            return
        if time.monotonic() >= deadline:
            raise RuntimeError(failure)
        time.sleep(0.01)


def verify_gui_documents(api, hwnd, expected):
    # The initial untitled document is retained. Cycle via the real command
    # router, checking every opened file's visible title and every UTF-8 byte.
    count = api.scalar(api.control(hwnd, 10), 0x1304)  # TCM_GETITEMCOUNT
    if count != len(expected) + 1:
        raise RuntimeError('GUI has missing or duplicated file tabs')
    remaining = dict(expected)
    for _ in range(count):
        title = api.text(hwnd)
        matches = [name for name in remaining if title == name + ' · ru_notepad']
        if matches:
            name = matches[0]
            if api.editor_bytes(hwnd) != remaining.pop(name):
                raise RuntimeError('GUI editor content differs from the synthetic Unicode input')
        api.command(hwnd, 112)  # next tab, through production WM_COMMAND
    if remaining:
        raise RuntimeError('GUI did not display every synthetic file with its exact Unicode name')


def write_gui_cancel_fixture(path):
    chunk = (b'cancel synthetic text\r\n' * 4096)[:65536]
    with path.open('xb') as stream:
        remaining = GUI_CANCEL_FIXTURE_BYTES
        while remaining:
            written = min(remaining, len(chunk))
            if stream.write(chunk[:written]) != written:
                raise RuntimeError('Short write creating synthetic GUI cancellation fixture')
            remaining -= written


def run_gui_file_entry(api, binary_dir, fixtures, evidence):
    isolated = Path(fixtures) / 'gui-file-entry'
    isolated.mkdir()
    fixture_hashes = {}
    for name in portable.RUNTIME_NAMES:
        shutil.copyfile(binary_dir / name, isolated / name)
        fixture_hashes[name] = sha(isolated / name)
        if fixture_hashes[name] != sha(binary_dir / name):
            raise RuntimeError('GUI file-entry fixture differs from the tested runtime binaries')
    inputs = isolated / 'Unicode 路径 😀'
    inputs.mkdir()
    cli = [inputs / '命令行 一 😀.txt', inputs / '命令行 二 文本.txt']
    dropped = [inputs / '拖放 三 😀.txt', inputs / '拖放 四 空格.txt']
    texts = ['CLI 中😀\r\nfirst\n', 'UTF16 文😀\r\nsecond',
             'DROP 中😀\r\nthird', 'DROP fourth\n最后😀']
    expected = {path.name: text.encode('utf-8') for path, text in zip(cli + dropped, texts)}
    for index, (path, text) in enumerate(zip(cli + dropped, texts)):
        path.write_bytes(b'\xff\xfe' + text.encode('utf-16-le') if index == 1 else text.encode('utf-8'))
    # A bounded 128 MiB real ASCII fixture makes cancellation observable without
    # triggering the separate >500,000,000-byte confirmation workflow.
    large = inputs / '取消读取 大文件.txt'
    write_gui_cancel_fixture(large)
    queued = inputs / '取消后不得打开.txt'
    queued.write_bytes(b'queued synthetic file must remain unopened')
    originals = {path: sha(path) for path in (*cli, *dropped, large, queued)}

    def exercise(process, hwnd):
        checks = {}
        tab_count = lambda: api.scalar(api.control(hwnd, 10), 0x1304)
        status = lambda: api.text(api.control(hwnd, 11))
        busy = lambda: status().lstrip().startswith('Opening:')
        wait_gui(api, process, lambda: tab_count() == 3 and not busy(),
                 'Unicode command-line files did not finish opening')
        verify_gui_documents(api, hwnd, {path.name: expected[path.name] for path in cli})
        checks.update(cli_unicode_paths=True, cli_exact_text=True)
        # Target the actual visible Scintilla child, where users drop files.
        # This proves native child-message routing; it is not an Explorer mouse
        # gesture or a complete OLE drag-and-drop interaction test.
        api.drop(api.editor(hwnd), dropped)
        wait_gui(api, process, lambda: tab_count() == 5 and not busy(),
                 'Unicode multi-file WM_DROPFILES did not finish opening')
        verify_gui_documents(api, hwnd, expected)
        checks.update(drop_unicode_paths=True, drop_exact_text=True)
        api.drop(api.editor(hwnd), [large, queued])
        wait_gui(api, process, busy, 'Large GUI open did not expose responsive busy state')
        checks['child_drop_routed'] = True
        checks['busy_observed'] = True
        api.responsive(hwnd)
        checks['busy_responsive'] = True
        api.command(hwnd, 901)  # actual user-facing Cancel operation command
        wait_gui(api, process, lambda: not busy(), 'GUI cancel operation did not complete')
        # Give an incorrectly retained queued path enough event-loop turns to
        # expose itself before checking exact final tabs and original contents.
        until = time.monotonic() + 0.5
        while time.monotonic() < until:
            api.no_dialog(process.pid)
            api.responsive(hwnd)
            time.sleep(0.01)
        verify_gui_documents(api, hwnd, expected)
        checks.update(cancel_no_partial_tab=True, cancel_queue_cleared=True)
        if any(sha(path) != digest for path, digest in originals.items()):
            raise RuntimeError('GUI open/drop/cancel modified a synthetic source file')
        checks['source_bytes_preserved'] = True
        return checks

    try:
        result = run_gui(api, isolated, evidence, name='main-gui-file-entry', arguments=cli,
                         exercise=exercise, log_prefix='main-file-entry-launcher')
    finally:
        api.release_drops()
    result['fixture_binary_sha256'] = fixture_hashes
    return result


def gui_ru_syntax_fixture():
    # Valid pinned Ru grammar. Byte positions are derived from UTF-8 source,
    # never character offsets; the non-BMP prefix catches accidental confusion.
    text = ("# Unicode 中😀\n"
            "作 演示:\n"
            "    数值 取 42.\n"
            "    文字 取 '若 真 则'.\n"
            "    若 真 则\n"
            "        显 文字.\n"
            "    然\n"
            "为\n"
            "显 7.\n")
    data = text.encode('utf-8')
    probes = {}
    for label, token, style in (('keyword', '作', 4), ('number', '42', 3),
                                ('quoted_keyword', "'若 真 则'", 2)):
        encoded = token.encode('utf-8')
        offset = data.index(encoded)
        probes[label] = {'offset': offset, 'length': len(encoded), 'style': style}
    return data, probes, (1, 4), (2, 5)


def gui_ru_timer_fixture():
    # Exact 1 MB, valid UTF-8 and pinned Ru grammar; the short final comment
    # fills the remainder without splitting a scalar or changing the tail.
    line, tail = '值 取 1.\n'.encode('utf-8'), '显 987654.\n'.encode('utf-8')
    repetitions = (GUI_RU_TIMER_BYTES - len(tail) - 2) // len(line)
    padding = GUI_RU_TIMER_BYTES - repetitions * len(line) - len(tail)
    data = line * repetitions + b'#' + b' ' * (padding - 2) + b'\n' + tail
    probes = {}
    for label, token, style, offset in (
            ('head_identifier', '值', 8, 0),
            ('head_keyword', '取', 4, data.index('取'.encode('utf-8'))),
            ('head_number', '1', 3, data.index(b'1')),
            ('tail_keyword', '显', 4, len(data) - len(tail)),
            ('tail_number', '987654', 3, data.rindex(b'987654'))):
        probes[label] = {'offset': offset, 'length': len(token.encode('utf-8')), 'style': style}
    return data, probes


def validate_gui_ru_timer(record):
    data, probes = gui_ru_timer_fixture()
    if not isinstance(record, dict) or set(record) != GUI_RU_TIMER_FIELDS:
        raise RuntimeError('GUI Ru timer performance record is missing or malformed')
    if (type(record['size']) is not int or record['size'] != len(data) or
            record['source_sha256'] != hashlib.sha256(data).hexdigest() or
            record['style_probes'] != probes or
            any(type(value) is not int for probe in record['style_probes'].values()
                for value in probe.values())):
        raise RuntimeError('GUI Ru timer source hash or head/tail probe shape differs from its fixture')
    # Diagnostic scalar snapshot is independent of the complete-style gate.
    # GETENDSTYLED alone can already be EOF after CLEARDOCUMENTSTYLE.
    last = record['last_probe']
    if (not isinstance(last, dict) or set(last) !=
            {'opened', 'length', 'clean', 'end_styled', 'status', 'style_matches'} or
            last['opened'] is not True or last['clean'] is not True or
            type(last['length']) is not int or last['length'] != len(data) or
            type(last['end_styled']) is not int or not 0 <= last['end_styled'] <= len(data) or
            not isinstance(last['status'], str) or not last['status'].strip() or len(last['status']) > 512 or
            'Styling Ru' in last['status'] or last['status'].lstrip().startswith('Opening:') or
            not isinstance(last['style_matches'], dict) or set(last['style_matches']) != set(probes) or
            any(value is not True for value in last['style_matches'].values())):
        raise RuntimeError('GUI Ru timer final bounded diagnostic probe is incomplete or malformed')
    if type(record['probes']) is not int or record['probes'] < 1:
        raise RuntimeError('GUI Ru timer lacks actual WM_NULL response probes')
    for field in ('wall_ms', 'first_head_style_ms', 'max_response_ms'):
        value = record[field]
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise RuntimeError('GUI Ru timer metrics must be finite nonnegative numbers')
    if (record['wall_ms'] > GUI_RU_TIMER_TIMEOUT_SECONDS * 1000 or
            record['first_head_style_ms'] > record['wall_ms'] or
            record['max_response_ms'] > record['wall_ms']):
        raise RuntimeError('GUI Ru timer exceeded its unchanged 30-second execution deadline')


def gui_ru_edit_fixture():
    prefix = '值 取 1.\n'.encode('utf-8')
    block = ("作 演示:\n    数值 取 42.\n    文字 取 '若 真 则'.\n"
             "    若 真 则\n        显 文字.\n    然\n为\n").encode('utf-8')
    tail = b'# EOF'
    repetitions = (GUI_RU_EDIT_BYTES - len(prefix) - len(tail) - 2) // len(block)
    padding = GUI_RU_EDIT_BYTES - len(prefix) - repetitions * len(block) - len(tail)
    data = prefix + block * repetitions + b'#' + b' ' * (padding - 2) + b'\n' + tail
    middle_block = repetitions // 2
    middle = len(prefix) + middle_block * len(block)
    probes = {}
    for label, token, style, offset in (
            ('head_identifier', '值', 8, 0), ('head_keyword', '作', 4, len(prefix)),
            ('quoted_keyword', "'若 真 则'", 2, data.index("'若 真 则'".encode('utf-8'))),
            ('middle_identifier', '文字', 8, middle + block.index('文字'.encode('utf-8'))),
            ('middle_number', '42', 3, middle + block.index(b'42')),
            ('tail_comment', 'EOF', 1, len(data) - 3)):
        probes[label] = {'offset': offset, 'length': len(token.encode('utf-8')), 'style': style}
    folds = [{'line': 1 + index * 7 + relative, 'level': level}
             for index in (0, middle_block, repetitions - 1)
             for relative, level in ((0, 0x2400), (3, 0x2401), (4, 0x402))]
    positions = {'bof': 0, 'middle': probes['middle_identifier']['offset'], 'eof': len(data)}
    return data, probes, folds, positions


def gui_ru_edit_operations():
    data, _, _, positions = gui_ru_edit_fixture()
    return [{'location': location, 'operation': operation, 'position': position,
             'before_size': len(data) + int(operation == 'delete'),
             'after_size': len(data) + int(operation == 'insert')}
            for location, position in positions.items() for operation in ('insert', 'delete')]


def validate_gui_ru_edits(record):
    data, probes, folds, _ = gui_ru_edit_fixture()
    fields = {'size', 'source_sha256', 'style_probes', 'fold_probes', 'operations', 'undo_commands', 'measurement'}
    if not isinstance(record, dict) or set(record) != fields:
        raise RuntimeError('GUI Ru edit performance record is missing or malformed')
    if (record['measurement'] != GUI_RU_EDIT_MEASUREMENT or
            type(record['size']) is not int or record['size'] != len(data) or
            record['source_sha256'] != hashlib.sha256(data).hexdigest() or
            record['style_probes'] != probes or record['fold_probes'] != folds or
            any(type(value) is not int for probe in record['style_probes'].values() for value in probe.values()) or
            any(type(value) is not int for probe in record['fold_probes'] for value in probe.values()) or
            type(record['undo_commands']) is not int or not 1 <= record['undo_commands'] <= 6):
        raise RuntimeError('GUI Ru edit fixture/probes or bounded Undo evidence is invalid')
    operations = record['operations']
    expected = gui_ru_edit_operations()
    if not isinstance(operations, list) or len(operations) != len(expected):
        raise RuntimeError('GUI Ru editing requires six BOF/middle/EOF insert/delete measurements')
    for actual, wanted in zip(operations, expected):
        if (not isinstance(actual, dict) or set(actual) != set(wanted) | {'wall_ms', 'max_response_ms', 'probes'} or
                any(actual.get(key) != value for key, value in wanted.items()) or
                any(type(actual[key]) is not int for key in ('position', 'before_size', 'after_size', 'probes')) or
                actual['probes'] < 1):
            raise RuntimeError('GUI Ru edit operation shape or real response probes are invalid')
        for key in ('wall_ms', 'max_response_ms'):
            if type(actual[key]) not in (int, float) or not math.isfinite(actual[key]) or actual[key] < 0:
                raise RuntimeError('GUI Ru edit timings must be finite nonnegative measurements')
        if actual['wall_ms'] > 30000 or actual['max_response_ms'] > actual['wall_ms']:
            raise RuntimeError('GUI Ru edit exceeded its unchanged 30-second execution deadline')


def run_gui_ru_edits(api, process, hwnd, source, record):
    original, probes, folds, _ = gui_ru_edit_fixture()
    source_sha = hashlib.sha256(original).hexdigest()
    def status_done():
        status = api.text(api.control(hwnd, 11))
        return bool(status.strip()) and 'Styling Ru' not in status and not status.lstrip().startswith('Opening:')
    def expected_data(operation):
        position = operation['position']
        inserted = operation['operation'] == 'insert'
        data = original[:position] + b'x' + original[position:] if inserted else original
        shifted = {name: dict(probe, offset=probe['offset'] + int(inserted and probe['offset'] >= position))
                   for name, probe in probes.items()}
        if inserted:
            shifted['inserted_character'] = {'offset': position, 'length': 1,
                                             'style': 1 if position == len(original) else 8}
        return data, shifted
    def state_matches(data, style_probes, dirty, context=None):
        editor = api.editor(hwnd)
        if api.scalar(editor, 2006) != len(data) or bool(api.scalar(editor, 2159)) != dirty:
            return False
        # ENDSTYLED is only an additional completion guard. Actual UTF-8 styles,
        # folds and production status must also match; no end-styled-only pass.
        if api.scalar(editor, 2028) != len(data) or not status_done():
            return False
        if not all(api.scalar(editor, 2010, pos) == probe['style'] for probe in style_probes.values()
                   for pos in range(probe['offset'], probe['offset'] + probe['length'])):
            return False
        if not all(api.scalar(editor, 2223, probe['line']) & 0x2fff == probe['level'] for probe in folds):
            return False
        if context is not None:
            start, end = max(0, context - 6), min(len(data), context + 10)
            if bytes(api.scalar(editor, 2007, pos) & 255 for pos in range(start, end)) != data[start:end]:
                return False
        return True
    api.drop(api.editor(hwnd), [source])
    def opened():
        api.responsive(hwnd)
        return (api.scalar(api.control(hwnd, 10), 0x1304) == 4 and
                api.text(hwnd) == source.name + ' · ru_notepad' and state_matches(original, probes, False))
    wait_gui(api, process, opened,
             'Representative 100 KB Ru edit fixture did not finish opening/styling')
    dirty = False
    previous_data, previous_probes = original, probes
    for operation in gui_ru_edit_operations():
        if not state_matches(previous_data, previous_probes, dirty):
            raise RuntimeError('Ru editor state changed before the next real input operation')
        data, shifted = expected_data(operation)
        editor = api.editor(hwnd)
        position = operation['position']
        caret = position + int(operation['operation'] == 'delete')
        api.scalar(editor, 2025, caret)  # SCI_GOTOPOS, scalar byte position
        if api.scalar(editor, 2008) != caret:
            raise RuntimeError('Ru GUI edit caret did not reach the requested byte position')
        metrics = dict(operation, wall_ms=0.0, max_response_ms=0.0, probes=0)
        record['operations'].append(metrics)
        started = time.monotonic()
        finished = None
        try:
            if operation['operation'] == 'insert':
                api.scalar(editor, 0x0102, ord('x'), 1)  # actual child WM_CHAR
            else:
                api.scalar(editor, 0x0100, 8, 1)  # actual Backspace key down/up
                api.scalar(editor, 0x0101, 8, 0xc0000001)
            api.command(hwnd, 504)  # production Reset Zoom also refreshes pending status
            while True:
                api.no_dialog(process.pid)
                if process.poll() is not None:
                    raise RuntimeError('GUI exited during a real length-changing Ru edit')
                response = time.monotonic()
                api.responsive(hwnd)
                metrics['max_response_ms'] = max(metrics['max_response_ms'], (time.monotonic() - response) * 1000)
                metrics['probes'] += 1
                complete = state_matches(data, shifted, True, position)
                elapsed = time.monotonic() - started
                if elapsed > 30:
                    raise RuntimeError('Real length-changing Ru edit exceeded 30 seconds')
                if complete:
                    finished = elapsed
                    break
                time.sleep(0.01)
        finally:
            metrics['wall_ms'] = round((finished if finished is not None else time.monotonic() - started) * 1000, 3)
            metrics['max_response_ms'] = round(metrics['max_response_ms'], 3)
        if sha(source) != source_sha:
            raise RuntimeError('Real Ru GUI editing changed the source file without a save')
        dirty, previous_data, previous_probes = True, data, shifted
    # Six user inputs create at most six undo actions. Coalescing may reduce
    # that number; stop only at the original clean savepoint, never loop forever.
    for _ in range(6):
        if api.scalar(api.editor(hwnd), 2159) == 0:
            break
        if not api.scalar(api.editor(hwnd), 2174):
            raise RuntimeError('Ru GUI edits lost their required undo history')
        api.command(hwnd, 201)
        record['undo_commands'] += 1
        wait_gui(api, process, lambda: status_done() and api.scalar(api.editor(hwnd), 2028) ==
                 api.scalar(api.editor(hwnd), 2006), 'Ru GUI Undo styling did not finish within 30 seconds')
    if not state_matches(original, probes, False) or sha(source) != source_sha:
        raise RuntimeError('Bounded production Undo did not restore the clean original Ru document')
    validate_gui_ru_edits(record)
    return {name: True for name in GUI_RU_EDIT_CHECKS}


def run_gui_ru_syntax(api, binary_dir, fixtures, evidence):
    isolated = Path(fixtures) / 'gui-ru-syntax'
    isolated.mkdir()
    fixture_hashes = {}
    for name in portable.RUNTIME_NAMES:
        shutil.copyfile(binary_dir / name, isolated / name)
        fixture_hashes[name] = sha(isolated / name)
        if fixture_hashes[name] != sha(binary_dir / name):
            raise RuntimeError('GUI Ru fixture differs from the tested runtime binaries')
    inputs = isolated / 'Ru 源码路径 😀'
    inputs.mkdir()
    source = inputs / '语法 折叠 😀.ru'
    original, probes, headers, children = gui_ru_syntax_fixture()
    source.write_bytes(original)
    original_sha = sha(source)
    timer_source = inputs / '真实计时 一百万字节 😀.ru'
    timer_data, timer_probes = gui_ru_timer_fixture()
    timer_source.write_bytes(timer_data)
    timer_sha = sha(timer_source)
    timer_record = {'size': len(timer_data), 'wall_ms': 0.0, 'first_head_style_ms': None, 'max_response_ms': 0.0,
                    'probes': 0, 'source_sha256': timer_sha, 'style_probes': timer_probes, 'last_probe': None}
    edit_source = inputs / '真实编辑 十万字节 😀.ru'
    edit_data, edit_probes, edit_folds, _ = gui_ru_edit_fixture()
    edit_source.write_bytes(edit_data)
    edit_sha = sha(edit_source)
    edit_record = {'size': len(edit_data), 'source_sha256': edit_sha, 'style_probes': edit_probes,
                   'measurement': GUI_RU_EDIT_MEASUREMENT,
                   'fold_probes': edit_folds, 'operations': [], 'undo_commands': 0}

    def exercise(process, hwnd):
        checks = {}
        tab_count = lambda: api.scalar(api.control(hwnd, 10), 0x1304)
        wait_gui(api, process, lambda: tab_count() == 2 and
                 api.text(hwnd) == source.name + ' · ru_notepad',
                 'Unicode Ru command-line file did not finish opening')
        checks['cli_unicode_path'] = True
        editor = api.editor(hwnd)
        if api.editor_bytes(hwnd) != original:
            raise RuntimeError('GUI Ru editor bytes differ from the Unicode fixture')
        checks['cli_exact_text'] = True
        lines = api.scalar(editor, 2154)  # SCI_GETLINECOUNT
        if lines != original.count(b'\n') + 1:
            raise RuntimeError('GUI Ru fixture line count differs from its source')
        # Only scalar Scintilla messages cross the process boundary. No local
        # pointers, remote allocations or synthetic WM_NOTIFY are involved.
        def styles_match(plain=False):
            return all(api.scalar(editor, 2010, position) == (0 if plain else probe['style'])
                       for probe in probes.values()
                       for position in range(probe['offset'], probe['offset'] + probe['length']))
        def fold_headers():
            return all(api.scalar(editor, 2223, line) & 0x2000 for line in headers)
        def all_visible():
            return all(api.scalar(editor, 2228, line) for line in range(lines))
        def clean_exact():
            if api.scalar(editor, 2159) != 0 or api.editor_bytes(hwnd) != original:
                raise RuntimeError('Ru styling/folding changed text or made the document dirty')
        wait_gui(api, process, lambda: styles_match() and fold_headers(),
                 'Automatic Ru styles and actual fold headers did not become available')
        checks.update(automatic_ru_styles=True, actual_fold_headers=True)
        clean_exact()
        api.command(hwnd, 505)  # actual View > Collapse all command
        wait_gui(api, process, lambda: all(not api.scalar(editor, 2228, line) for line in children),
                 'Collapse all did not hide actual Ru child lines')
        if not all(api.scalar(editor, 2228, line) for line in (0, 1, 8)):
            raise RuntimeError('Collapse all hid a root/header line of the Ru fixture')
        checks['collapse_hides_children'] = True
        clean_exact()
        api.command(hwnd, 704)  # reselecting Ru must preserve the chosen collapse
        api.responsive(hwnd)
        if not all(not api.scalar(editor, 2228, line) for line in children):
            raise RuntimeError('Repeated Ru selection unexpectedly expanded collapsed lines')
        checks['same_ru_preserves_collapse'] = True
        api.command(hwnd, 506)  # actual View > Expand all command
        wait_gui(api, process, all_visible, 'Expand all did not restore every Ru line')
        checks['expand_restores_visibility'] = True
        api.command(hwnd, 505)
        wait_gui(api, process, lambda: all(not api.scalar(editor, 2228, line) for line in children),
                 'Repeated Collapse all did not hide actual Ru child lines')
        api.command(hwnd, 701)  # actual Language > Plain text command
        wait_gui(api, process, lambda: styles_match(plain=True) and
                 all(not (api.scalar(editor, 2223, line) & 0x2000) for line in headers),
                 'Plain-text menu did not clear Ru styles and fold headers')
        wait_gui(api, process, all_visible, 'Plain-text menu left Ru lines hidden')
        checks.update(plain_clears_styles_folds=True, plain_restores_visibility=True)
        clean_exact()
        api.command(hwnd, 704)  # actual Language > Ru command
        wait_gui(api, process, lambda: styles_match() and fold_headers(),
                 'Ru language menu did not restore actual styles and fold headers')
        wait_gui(api, process, all_visible, 'Ru language menu did not restore every line')
        checks.update(ru_restores_styles_folds=True, ru_restores_visibility=True)
        clean_exact()
        if sha(source) != original_sha:
            raise RuntimeError('Ru GUI commands modified the source file')
        checks.update(document_clean=True, text_bytes_preserved=True, source_bytes_preserved=True)
        checks['style_probes'] = probes
        checks['fold_header_lines'] = list(headers)
        checks['collapsed_child_lines'] = list(children)
        # This is the production timer path, in the same detached process.
        # Inspect only 16 token bytes, never fetch or scan the 1 MB document
        # cross-process. The native suite independently checks complete bytes.
        started = time.monotonic()
        finished_elapsed = None
        try:
            api.drop(api.editor(hwnd), [timer_source])
            checks['timer_child_drop_routed'] = True
            while True:
                api.no_dialog(process.pid)
                if process.poll() is not None:
                    raise RuntimeError('GUI exited during the 1 MB Ru timer stage')
                response_started = time.monotonic()
                api.responsive(hwnd)  # actual WM_NULL, unchanged 5-second limit
                timer_record['max_response_ms'] = max(timer_record['max_response_ms'],
                    (time.monotonic() - response_started) * 1000)
                timer_record['probes'] += 1
                opened = (tab_count() == 3 and
                          api.text(hwnd) == timer_source.name + ' · ru_notepad')
                complete = False
                last_probe = {'opened': opened, 'length': None, 'clean': None,
                              'end_styled': None, 'status': '', 'style_matches': {}}
                timer_record['last_probe'] = last_probe
                if opened:
                    active = api.editor(hwnd)
                    length = api.scalar(active, 2006)
                    length_ok = length == len(timer_data)
                    clean = api.scalar(active, 2159) == 0
                    last_probe.update(length=length, clean=clean, end_styled=api.scalar(active, 2028))
                    if not clean:
                        raise RuntimeError('GUI timer styling made the 1 MB document dirty')
                    matched = {}
                    if length_ok:
                        for group in ('head', 'tail'):
                            matched.update({label: all(api.scalar(active, 2010, position) == probe['style']
                                for position in range(probe['offset'], probe['offset'] + probe['length']))
                                for label, probe in timer_probes.items() if label.startswith(group)})
                            if group == 'head' and all(matched.values()) and timer_record['first_head_style_ms'] is None:
                                # First matching head-token styles, not a claim
                                # about a painted first screen or all lines.
                                timer_record['first_head_style_ms'] = round((time.monotonic() - started) * 1000, 3)
                    status = api.text(api.control(hwnd, 11))
                    last_probe.update(status=status[:512], style_matches=matched)
                    status_done = bool(status.strip()) and 'Styling Ru' not in status and not status.lstrip().startswith('Opening:')
                    complete = length_ok and clean and all(matched.values()) and status_done
                elapsed = time.monotonic() - started
                if elapsed > GUI_RU_TIMER_TIMEOUT_SECONDS:
                    raise RuntimeError('GUI 1 MB open and Ru timer styling exceeded 30 seconds')
                if complete:
                    finished_elapsed = elapsed
                    checks.update(timer_exact_length=True, timer_document_clean=True,
                                  timer_head_styles=True, timer_tail_styles=True, timer_status_cleared=True)
                    break
                time.sleep(0.01)
            if sha(timer_source) != timer_sha:
                raise RuntimeError('GUI timer styling modified the 1 MB source file')
            checks['timer_source_bytes_preserved'] = True
        finally:
            timer_record['wall_ms'] = round((finished_elapsed if finished_elapsed is not None
                                            else time.monotonic() - started) * 1000, 3)
            timer_record['max_response_ms'] = round(timer_record['max_response_ms'], 3)
        validate_gui_ru_timer(timer_record)
        checks.update(run_gui_ru_edits(api, process, hwnd, edit_source, edit_record))
        return checks

    try:
        result = run_gui(api, isolated, evidence, name='main-gui-ru-syntax', arguments=[source],
                         exercise=exercise, log_prefix='main-ru-syntax-launcher')
    finally:
        api.release_drops()
    result['fixture_binary_sha256'] = fixture_hashes
    result['timer_performance'] = timer_record
    result['edit_performance'] = edit_record
    if sha(source) != original_sha:
        result.update(passed=False, source_bytes_preserved=False,
                      error='GUI normal-close flow modified the Ru source file')
    if sha(timer_source) != timer_sha:
        result.update(passed=False, timer_source_bytes_preserved=False,
                      error='GUI normal-close flow modified the 1 MB Ru source file')
    if sha(edit_source) != edit_sha:
        result.update(passed=False, edit_source_bytes_preserved=False,
                      error='GUI normal-close flow modified the 100 KB Ru source file')
    return result


def inspect_pe(path, objdump):
    return portable.inspect_pe(path, objdump)


def copy_runtime_licenses(mingw, destination):
    source = mingw / 'share' / 'licenses'
    folders = [path for path in source.iterdir() if path.is_dir()
               and re.search(r'gcc|cc-libs|libstdc|libgcc|mingw|winpthread|crt|headers', path.name, re.I)]
    if not folders:
        raise RuntimeError('MSYS2 runtime license directories are missing')
    collected = []
    for folder in folders:
        for path in sorted(folder.rglob('*')):
            if path.is_file():
                if path.is_symlink() or path.stat().st_size > MAX_LOG_BYTES:
                    raise RuntimeError('Unexpected runtime license link or size')
                target = destination / 'MSYS2' / path.relative_to(source)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
                collected.append(path.read_text(encoding='utf-8', errors='replace'))
    combined = '\n'.join(collected)
    if 'GCC RUNTIME LIBRARY EXCEPTION' not in combined or 'GNU GENERAL PUBLIC LICENSE' not in combined:
        raise RuntimeError('GCC GPL and Runtime Library Exception notices must accompany the binaries')
    if 'mingw' not in combined.lower():
        raise RuntimeError('MinGW-w64 license notices are missing')


def console_command(name, binary_dir, fixtures):
    executable = CONSOLE_EXECUTABLES.get(name, name)
    command = [str(binary_dir / f'{executable}.exe')]
    if name in FIXTURE_ARGUMENT_TESTS:
        command.append(str(fixtures))
    if name == 'editor_largefile_native':
        command.append('--large')
    return command


def run_native_console(api, name, marker, binary_dir, fixtures, evidence):
    if name == 'editor_largefile_native' and shutil.disk_usage(fixtures).free < LARGE_FILE_MIN_FREE_BYTES:
        return {'name': name, 'passed': False, 'executed': False, 'cleanup_killed': False,
                'error': 'Mandatory >500 MB editor test requires at least 2 GiB free synthetic-fixture disk'}
    return run_console(api, name, console_command(name, binary_dir, fixtures), evidence, marker,
                       timeout=CONSOLE_TIMEOUT_SECONDS.get(name, 120),
                       expected_assertions=expected_assertions(name))


def syntax_fallback_layout(name):
    executable = SYNTAX_FALLBACK_EXECUTABLES.get(name, 'syntax_native.exe')
    layout = {executable: executable, 'Scintilla.dll': 'Scintilla.dll'}
    if name == 'syntax_bad_lexer':
        # A real loadable DLL without CreateLexer, never a mock failure flag.
        layout['Lexilla.dll'] = 'Scintilla.dll'
    if name in HELPER_FALLBACK_LAYOUTS:
        layout['Lexilla.dll'] = 'Lexilla.dll'
    helper_mode = HELPER_FALLBACK_LAYOUTS.get(name)
    if helper_mode != 'missing':
        layout[portable.NATIVE_HELPER_NAME] = (
            'Scintilla.dll' if helper_mode == 'bad-exports' else
            portable.NATIVE_WRONG_ABI_NAME if helper_mode == 'wrong-abi' else portable.NATIVE_HELPER_NAME)
    return layout


def run_syntax_fallbacks(api, binary_dir, fixtures, evidence):
    results = []
    for name, argument, _ in SYNTAX_FALLBACK_TESTS:
        isolated = Path(fixtures) / name
        isolated.mkdir()
        executable = SYNTAX_FALLBACK_EXECUTABLES.get(name, 'syntax_native.exe')
        layout = syntax_fallback_layout(name)
        fixture_hashes = {}
        for target, source in layout.items():
            shutil.copyfile(binary_dir / source, isolated / target)
            fixture_hashes[target] = sha(isolated / target)
            if fixture_hashes[target] != sha(binary_dir / source):
                raise RuntimeError('Syntax fallback fixture differs from the tested binaries')
        result = dict(run_console(api, name, [str(isolated / executable), argument],
            evidence, r'^TOTAL PASS: 8\s*$', expected_assertions=8, cwd=isolated))
        result['fixture_binary_sha256'] = fixture_hashes
        results.append(result)
    return results


def expected_assertions(name):
    if name in {case[0] for case in SYNTAX_FALLBACK_TESTS}:
        return 8
    if name == 'file_codec_security':
        return 28
    marker = dict(NATIVE_CONSOLE_TESTS)[name]
    return int(re.search(r'(?:PASS: |PASS=)([0-9]+)', marker)[1])


def validate_acceptance(summary, root=None):
    validate_scanner_preflight(summary.get('scanner_preflight'), summary['tested_binary_sha256'],
                               ROOT if root is None else root)
    expected = {name for name, _ in NATIVE_CONSOLE_TESTS} | GUI_NAMES | {case[0] for case in SYNTAX_FALLBACK_TESTS}
    if summary['acl_requested']:
        expected.add('file_codec_security')
    results = summary['tests']
    if len(results) != len(expected) or {test['name'] for test in results} != expected:
        raise RuntimeError('Native acceptance test inventory is incomplete or duplicated')
    for test in results:
        if not test['passed'] or not test['executed'] or test['cleanup_killed'] or test.get('exit_code') != 0 or test.get('skips'):
            raise RuntimeError(f'Native acceptance test did not pass normally: {test["name"]}')
        if test['name'] not in GUI_NAMES and test.get('assertions_passed') != expected_assertions(test['name']):
            raise RuntimeError(f'Native acceptance assertion count mismatch: {test["name"]}')
        if test['name'] == 'ru_syntax_native':
            validate_ru_performance(test.get('performance'))
        if test['name'] in {case[0] for case in SYNTAX_FALLBACK_TESTS}:
            expected_hashes = {target: summary['tested_binary_sha256'][source]
                               for target, source in syntax_fallback_layout(test['name']).items()}
            if test.get('fixture_binary_sha256') != expected_hashes:
                raise RuntimeError('Syntax fallback fixture does not match the packaged test binaries')
        if test['name'] in GUI_NAMES and not all(test.get(key) for key in
                ('main_hwnd_seen', 'close_posted', 'detached_from_console')):
            raise RuntimeError('GUI acceptance lacks ordinary visible-window startup/close')
        if test['name'] == 'main-gui-ru-syntax':
            if not all(test.get(key) for key in GUI_RU_CHECKS):
                raise RuntimeError('GUI Ru acceptance lacks a required style/fold/visibility/clean-state check')
            validate_gui_ru_timer(test.get('timer_performance'))
            validate_gui_ru_edits(test.get('edit_performance'))
        if test['name'] == 'main-gui-file-entry':
            if not all(test.get(key) for key in GUI_FILE_CHECKS):
                raise RuntimeError('GUI file-entry acceptance lacks a required Unicode/drop/cancel check')
        if test['name'] in {'main-gui-file-entry', 'main-gui-ru-syntax'}:
            hashes = {name: summary['tested_binary_sha256'][name] for name in portable.RUNTIME_NAMES}
            if test.get('fixture_binary_sha256') != hashes:
                raise RuntimeError('GUI fixture does not match the packaged runtime binaries')


def package(binary_dir, evidence, mingw, objdump, summary):
    validate_acceptance(summary)
    # Only this run's named bounded synthetic files enter the tests ZIP.
    allowed = portable.evidence_names([name for name, _ in NATIVE_CONSOLE_TESTS] +
                                      [case[0] for case in SYNTAX_FALLBACK_TESTS] +
                                      (['file_codec_security'] if summary['acl_requested'] else []))
    return portable.create_packages(ROOT, binary_dir, evidence.parent / 'dist', evidence,
        objdump, summary, lambda destination: copy_runtime_licenses(mingw, destination),
        {'app_commit': subprocess.check_output(
            ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()}, allowed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--helper-policy-action', choices=('prepare', 'verify', 'collect'))
    parser.add_argument('--bin-dir', type=Path)
    parser.add_argument('--evidence-dir', type=Path)
    parser.add_argument('--mingw-root', type=Path)
    parser.add_argument('--objdump', type=Path)
    parser.add_argument('--acl', action='store_true', help='Run synthetic NTFS ACL replacement cases')
    args = parser.parse_args()
    if args.helper_policy_action:
        if any((args.bin_dir, args.evidence_dir, args.mingw_root, args.objdump, args.acl)):
            parser.error('Helper-policy evidence actions cannot substitute for Windows acceptance')
        try:
            print(json.dumps(helper_policy_action(args.helper_policy_action, ROOT)), flush=True)
        except Exception as exc:
            print(str(exc), file=sys.stderr)
            return 1
        return 0
    if not all((args.bin_dir, args.evidence_dir, args.mingw_root, args.objdump)):
        parser.error('--bin-dir, --evidence-dir, --mingw-root and --objdump are required for Windows acceptance')
    if sys.platform != 'win32':
        parser.error('Real Windows is required; Linux/Wine cannot produce a native acceptance receipt')
    binary_dir, evidence = args.bin_dir.resolve(), args.evidence_dir.resolve()
    api = Windows()
    summary = {'schema': 1, 'platform': 'native-windows-x64', 'passed': False,
               'synthetic_data_only': True, 'tests': [], 'acl_requested': args.acl,
               'native_tests_passed': False}
    try:
        portable.validate_dependency_sources(ROOT)
        portable.validate_receipts(ROOT, binary_dir, args.objdump)
        summary['tested_binary_sha256'] = portable.binary_snapshot(binary_dir)
        summary['scanner_preflight'] = run_scanner_preflight(api, binary_dir, evidence)
        save_json(evidence / 'native-acceptance.json', summary)
        print(json.dumps(summary['scanner_preflight']), flush=True)
        validate_scanner_preflight(summary['scanner_preflight'], summary['tested_binary_sha256'], ROOT)
        with tempfile.TemporaryDirectory(prefix='ru-notepad-ci-') as fixtures:
            for name, marker in NATIVE_CONSOLE_TESTS:
                result = run_native_console(api, name, marker, binary_dir, fixtures, evidence)
                summary['tests'].append(result)
                save_json(evidence / 'native-acceptance.json', summary)
                print(json.dumps(result), flush=True)
            for result in run_syntax_fallbacks(api, binary_dir, fixtures, evidence):
                summary['tests'].append(result)
                save_json(evidence / 'native-acceptance.json', summary)
                print(json.dumps(result), flush=True)
            if args.acl:
                command = ['pwsh', '-NoProfile', '-NonInteractive', '-File',
                           str(ROOT / 'tests/file_codec_security_tests.ps1'), '-ProbeExe',
                           str(binary_dir / 'file_codec_security_probe.exe'), '-TestDirectory', fixtures]
                result = run_console(api, 'file_codec_security', command, evidence,
                                     r'^FILE_CODEC_SECURITY_TESTS_PASS\s*$', timeout=120, expected_assertions=28)
                summary['tests'].append(result)
                print(json.dumps(result), flush=True)
            result = run_gui(api, binary_dir, evidence)
            summary['tests'].append(result)
            print(json.dumps(result), flush=True)
            result = run_gui_file_entry(api, binary_dir, fixtures, evidence)
            summary['tests'].append(result)
            print(json.dumps(result), flush=True)
            result = run_gui_ru_syntax(api, binary_dir, fixtures, evidence)
            summary['tests'].append(result)
            print(json.dumps(result), flush=True)
        validate_acceptance(summary)
        summary['passed'] = True
        summary['native_tests_passed'] = summary['passed']
        save_json(evidence / 'native-acceptance.json', summary)
        if not summary['passed']:
            raise RuntimeError('One or more native Windows acceptance tests failed; no portable ZIP published')
        artifact = package(binary_dir, evidence, args.mingw_root.resolve(), args.objdump, summary)
        save_json(evidence / 'portable-artifact.json', artifact)
        print(json.dumps(artifact), flush=True)
    except Exception as exc:
        summary['passed'] = False
        summary['run_error'] = str(exc)
        save_json(evidence / 'native-acceptance.json', summary)
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
