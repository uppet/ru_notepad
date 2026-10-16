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
    ('app_ru_native', r'^TOTAL PASS: 73\s*$'),
    ('app_ru_timer_native', r'^TOTAL PASS: 8\s*$'),
    ('ru_lexical_policy', r'^TOTAL PASS: 338\s*$'),
    ('ru_syntax_native', r'^TOTAL PASS: 149\s*$'),
    ('ru_direct_styling_native', r'^TOTAL PASS: 36\s*$'),
)
SYNTAX_FALLBACK_TESTS = (
    ('syntax_missing_lexilla', '--expect-missing', False),
    ('syntax_bad_lexer', '--expect-bad-lexer', True),
    ('ru_syntax_missing_lexilla', '--expect-missing-lexilla', False),
    ('ru_syntax_missing_helper', '--expect-missing-helper', False),
    ('ru_syntax_bad_helper', '--expect-bad-helper', False),
    ('ru_syntax_wrong_helper_abi', '--expect-wrong-helper-abi', False),
)
WRONG_LEXER_PREFLIGHT_MARKER = 'WRONG_LEXER_FIXTURE_PREFLIGHT loadable=1 createlexer_missing=1 released=1'
WRONG_LEXER_PREFLIGHT_FIELDS = {'loadable', 'createlexer_missing', 'released', 'library_sha256'}
SYNTAX_FALLBACK_EXECUTABLES = {name: 'ru_syntax_native.exe' for name, _, _ in
                               SYNTAX_FALLBACK_TESTS if name.startswith('ru_syntax_')}
HELPER_FALLBACK_LAYOUTS = {'ru_syntax_missing_helper': 'missing',
                          'ru_syntax_bad_helper': 'bad-exports',
                          'ru_syntax_wrong_helper_abi': 'wrong-abi'}
# These limits apply only to the named synthetic suites, never to user files.
# The >500 MB test is mandatory: low disk or timeout fails instead of skipping.
CONSOLE_EXECUTABLES = {'editor_largefile_native': 'editor_streaming_native',
                       'app_ru_timer_native': 'app_ru_native'}
FIXTURE_ARGUMENT_TESTS = {'file_codec_tests', 'file_streaming_native', 'app_streaming_native',
                        'editor_streaming_native', 'editor_largefile_native', 'app_ru_native',
                        'app_ru_timer_native'}
CONSOLE_TIMEOUT_SECONDS = {'file_streaming_native': 300, 'app_streaming_native': 180,
                           'editor_streaming_native': 300,
                           'editor_largefile_native': 900, 'app_ru_native': 180,
                           'app_ru_timer_native': 60, 'ru_direct_styling_native': 120}
LARGE_FILE_MIN_FREE_BYTES = 2 * 1024 * 1024 * 1024
GUI_FILE_CHECKS = ('cli_unicode_paths', 'cli_exact_text', 'drop_unicode_paths',
                   'drop_exact_text', 'child_drop_routed', 'busy_observed', 'busy_responsive',
                   'cancel_no_partial_tab', 'cancel_queue_cleared', 'source_bytes_preserved')
GUI_RU_CHECKS = ('initial_mod_event_mask', 'timer_mod_event_mask', 'cli_unicode_path',
                 'cli_exact_text', 'automatic_ru_styles',
                 'actual_fold_headers', 'collapse_hides_children', 'same_ru_preserves_collapse',
                 'expand_restores_visibility',
                 'plain_clears_styles_folds', 'plain_restores_visibility',
                 'ru_restores_styles_folds', 'ru_restores_visibility',
                 'document_clean', 'text_bytes_preserved', 'source_bytes_preserved',
                 'timer_child_drop_routed', 'timer_exact_length', 'timer_document_clean',
                 'timer_head_styles', 'timer_tail_styles', 'timer_status_cleared',
                 'timer_source_bytes_preserved', 'timer_queued_navigation', 'timer_paint_region_serviced',
                 'edit_fixture_loaded', 'edit_all_operations',
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
RU_GUI_SYNC_INTEGER_FIELDS = {'size', 'source_chars', 'read_bytes', 'max_read', 'chunks'}
RU_GUI_SYNC_TIME_FIELDS = {'wall_ms', 'max_tick_ms', 'max_chunk_ms'}
RU_GUI_TIMER_INTEGER_FIELDS = {'size', 'source_chars', 'ticks', 'read_bytes', 'max_read',
    'chunks', 'feed', 'bytes', 'pending', 'text_notifications', 'style_notifications', 'fold_notifications',
    'posts', 'continuation_ticks', 'queue_yields', 'stale_messages'}
RU_GUI_TIMER_TIME_FIELDS = {'wall_ms', 'work_ms', 'gap_ms', 'max_tick_ms', 'max_gap_ms'}
RU_GUI_MEASUREMENTS = {
    'RU_GUI_SYNC': (RU_GUI_SYNC_INTEGER_FIELDS, RU_GUI_SYNC_TIME_FIELDS),
    'RU_GUI_TIMER': (RU_GUI_TIMER_INTEGER_FIELDS, RU_GUI_TIMER_TIME_FIELDS),
}
RU_GUI_CONSOLE_MEASUREMENTS = {'ru_syntax_native': ('RU_GUI_SYNC', 'gui_sync_performance'),
                              'app_ru_timer_native': ('RU_GUI_TIMER', 'timer_performance')}
GUI_RU_EDIT_BYTES = 100000
GUI_RU_EDIT_CHECKS = ('edit_fixture_loaded', 'edit_all_operations', 'edit_style_fold_probes',
                     'edit_dirty_transitions', 'edit_source_bytes_preserved', 'edit_undo_clean')
GUI_RU_EDIT_MEASUREMENT = ('Real child WM_CHAR/Backspace length-changing input; wall time includes '
    'production Reset Zoom 504 status refresh and WM_NULL polling; bounded style/fold/context probes.')
GUI_RU_TIMER_FIELDS = {'size', 'wall_ms', 'first_head_style_ms', 'max_response_ms', 'probes',
                       'source_sha256', 'style_probes', 'last_probe', 'responsiveness',
                       'observer', 'diagnostics', 'head_style_measurement', 'clock', 'clock_measurement'}
GUI_RU_RESPONSE_TIMEOUT_MS = 5000
GUI_RU_RESPONSE_MEASUREMENT = ('Synthetic queued RIGHT/LEFT navigation and natural invalidated-region '
    'service while Ru styling remains pending; no text edits, forced paint or pixel-render claim. '
    'The existing 5-second response limit is a fail-stop upper bound, not a low-latency target.')
GUI_RU_NAVIGATION = ({'key': 'RIGHT', 'before': 0, 'after': 3},
                     {'key': 'LEFT', 'before': 3, 'after': 0})
SCANNER_PREFLIGHT_SOURCES = ('tools/test_ru_scan.py', 'src/ru_lexical.ru',
                            'tests/ru_lexical_policy.ru')
SCANNER_PREFLIGHT_REPORT_FIELDS = {'cases', 'chunk_checks', 'ru_assertions_per_backend',
                                  'library_sha256', 'source_sha256', 'sanitizer'}
SCANNER_SANITIZER_SUCCESS = 'PASS: 20000 ASan/UBSan bounded random buffer cases'
HELPER_POLICY_EVIDENCE_FILES = ('helper-policy.stdout.log', 'helper-policy.stderr.log',
    'cleanup-control.stdout.log', 'cleanup-control.stderr.log',
    'bridge-failure.stdout.log', 'bridge-failure.stderr.log',
    'timer-corpus.stdout.log', 'timer-corpus.stderr.log',
    'diagnostic-control.stdout.log', 'diagnostic-control.stderr.log',
    'event-bulk.stdout.log', 'event-bulk.stderr.log',
    'scanner-build.log', 'differential-python.log', 'differential-build.log',
    'differential-c.log', 'sanitize-build.log', 'sanitize.log', 'report.json')
HELPER_POLICY_COMMIT = 'a2f6faa0f914781dea74cb6f0a7574f1dd6808ce'
HELPER_POLICY_TREE = '7b4331d51bc6ab2ec95fec1f8368465343fcd5af'
BULK_EVENT_CASES = (
    'all 384 fields of the full batch',
    'near-32-MB exact metadata',
    'zero event batch',
    'delayed long identifier',
    'delayed 64-byte keyword',
    'equal event positions',
    'high word 131072',
    'high word 2147483648',
    'high word 4294967295',
    'last event high bits',
    'invalid count -1',
    'invalid count 0.5',
    'invalid count 65',
    'kind zero',
    'kind eight',
    'style ten',
    'zero length',
    'full unsigned length',
    'full unsigned line',
    'end beyond bytes',
    'non-token before start',
    'keyword length 65',
    'decreasing positions',
)
GUI_CANCEL_FIXTURE_BYTES = 128 * 1024 * 1024
MAX_GUI_DROP_BATCHES = 4
MAX_GUI_DROP_PAYLOAD_BYTES = 65536
SYSTEM_DLLS = portable.SYSTEM_DLLS
PERFORMANCE_CLOCK_FIELDS = {'clock_name', 'implementation', 'resolution', 'monotonic', 'adjustable'}
PERFORMANCE_CLOCK_MEASUREMENT = ('Python perf_counter elapsed time; reported clock resolution is not '
    'physical input or paint accuracy. Application tick quantization, polling cadence and measured '
    'observer costs still limit interpretation; milliseconds are rounded to three decimals.')


def validate_performance_clock(record, *, require_windows=False):
    if (not isinstance(record, dict) or set(record) != PERFORMANCE_CLOCK_FIELDS or
            record['clock_name'] != 'perf_counter' or
            not isinstance(record['implementation'], str) or
            not 1 <= len(record['implementation']) <= 128 or
            not record['implementation'].isprintable() or
            type(record['resolution']) not in (int, float) or
            not math.isfinite(record['resolution']) or record['resolution'] <= 0 or
            record['monotonic'] is not True or record['adjustable'] is not False):
        raise RuntimeError('CI performance clock metadata is missing or malformed')
    if require_windows and record['implementation'] != 'QueryPerformanceCounter()':
        raise RuntimeError('Native Windows CI performance clock must use QueryPerformanceCounter')


def performance_clock_record():
    info = time.get_clock_info('perf_counter')
    record = dict(clock_name='perf_counter', implementation=info.implementation,
                  resolution=info.resolution, monotonic=info.monotonic, adjustable=info.adjustable)
    validate_performance_clock(record, require_windows=sys.platform == 'win32')
    return record


class PerformanceClock:
    """One local elapsed-time domain; no global state survives mocked-clock restoration."""
    def __init__(self, previous=None):
        self.previous = previous

    def __call__(self):
        value = time.perf_counter()
        if (type(value) not in (int, float) or not math.isfinite(value) or
                (self.previous is not None and
                 (type(self.previous) not in (int, float) or not math.isfinite(self.previous) or
                  value < self.previous or not math.isfinite(value - self.previous)))):
            raise RuntimeError('CI performance clock is nonfinite or moved backwards')
        self.previous = value
        return value


def finish_result_clock(result, clock, started):
    """A failed final timestamp must not discard executed/cleanup/partial evidence."""
    if started is None:
        result['seconds'] = None
        return
    try:
        result['seconds'] = round(clock() - started, 3)
    except RuntimeError as exc:
        result.update(passed=False, seconds=None, seconds_valid=False, clock_error=str(exc))
        result.setdefault('error', str(exc))
        if clock.previous is not None:
            result['last_good_seconds'] = round(clock.previous - started, 3)


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
        self.user.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        self.user.GetClientRect.restype = wintypes.BOOL
        self.user.InvalidateRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT), wintypes.BOOL]
        self.user.InvalidateRect.restype = wintypes.BOOL
        self.user.GetUpdateRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT), wintypes.BOOL]
        self.user.GetUpdateRect.restype = wintypes.BOOL
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.LoadLibraryExW.argtypes = [wintypes.LPCWSTR, wintypes.HANDLE, wintypes.DWORD]
        self.kernel.LoadLibraryExW.restype = wintypes.HMODULE
        self.kernel.GetProcAddress.argtypes = [wintypes.HMODULE, wintypes.LPCSTR]
        self.kernel.GetProcAddress.restype = ctypes.c_void_p
        self.kernel.FreeLibrary.argtypes = [wintypes.HMODULE]
        self.kernel.FreeLibrary.restype = wintypes.BOOL
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

    def verify_owned_handles(self, process_id, *handles):
        # These direct user32 queries do not synchronously message the UI thread.
        # Recheck cached child handles before trusting their final scalar values.
        for handle in handles:
            owner = wintypes.DWORD()
            if (not self.user.GetWindowThreadProcessId(handle, ctypes.byref(owner)) or
                    owner.value != process_id or not self.user.IsWindowVisible(handle)):
                raise RuntimeError('Cached GUI Ru control is invalid, hidden, or belongs to another process')

    def editor_bytes(self, hwnd):
        editor = self.editor(hwnd)
        length = self.scalar(editor, 2006)  # SCI_GETLENGTH, no pointer argument
        if length > 4096:
            raise RuntimeError('Small GUI fixture unexpectedly exceeds inspection limit')
        return bytes(self.scalar(editor, 2007, index) & 255 for index in range(length))

    def command(self, hwnd, identifier):
        self.scalar(hwnd, 0x0111, identifier)  # actual WM_COMMAND routing

    def post_ru_snapshot(self, hwnd):
        if not self.user.PostMessageW(hwnd, GUI_RU_DIAGNOSTIC_MESSAGE, 0, 0):
            raise ctypes.WinError(ctypes.get_last_error())

    def post_navigation(self, hwnd, key):
        virtual_key, scan_code = {'RIGHT': (0x27, 0x4d), 'LEFT': (0x25, 0x4b)}[key]
        # Matched extended-key down/up posted to this synthetic Scintilla child
        # only; never global SendInput, focus changes or text-producing WM_CHAR.
        down = 1 | (scan_code << 16) | (1 << 24)
        for message, flags in ((0x0100, down), (0x0101, down | 0xc0000000)):
            if not self.user.PostMessageW(hwnd, message, virtual_key, flags):
                raise ctypes.WinError(ctypes.get_last_error())

    def paint_pending(self, hwnd):
        return bool(self.user.GetUpdateRect(hwnd, None, False))

    def invalidate_for_paint(self, hwnd):
        rectangle = wintypes.RECT()
        if (not self.user.IsWindowVisible(hwnd) or
                not self.user.GetClientRect(hwnd, ctypes.byref(rectangle)) or
                rectangle.right <= rectangle.left or rectangle.bottom <= rectangle.top):
            raise RuntimeError('Synthetic paint probe requires a visible nonempty editor child')
        if not self.user.InvalidateRect(hwnd, None, False):
            raise ctypes.WinError(ctypes.get_last_error())
        # The UI thread may naturally BeginPaint before this first read. Keep
        # that observation distinct; demanding an initial true would race.
        return self.paint_pending(hwnd)

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


def validate_ru_gui_measurement(record, marker, *, require_complete=True):
    integer_fields, time_fields = RU_GUI_MEASUREMENTS[marker]
    if not isinstance(record, dict) or set(record) != integer_fields | time_fields | {'source_sha256'}:
        raise RuntimeError(f'{marker}: same-source measurement fields are missing or unexpected')
    data, _ = gui_ru_timer_fixture()
    if (record['source_sha256'] != hashlib.sha256(data).hexdigest() or
            record['size'] != len(data) or record['source_chars'] != len(data.decode('utf-8'))):
        raise RuntimeError(f'{marker}: same-source measurement differs from the exact GUI fixture')
    if any(type(record[key]) is not int or record[key] < 0 for key in integer_fields):
        raise RuntimeError(f'{marker}: counts must be nonnegative integers')
    if any(type(record[key]) not in (int, float) or not math.isfinite(record[key]) or record[key] < 0
           for key in time_fields):
        raise RuntimeError(f'{marker}: times must be finite nonnegative measurements')
    if not 0 <= record['max_read'] <= 1024 or not 0 <= record['read_bytes'] <= len(data):
        raise RuntimeError(f'{marker}: same-source measurement exceeds bounded reads')
    if marker == 'RU_GUI_TIMER':
        if (not 0 <= record['bytes'] <= record['feed'] <= record['read_bytes'] <= len(data) or
                record['pending'] not in (0, 1) or record['work_ms'] > record['wall_ms'] or
                record['gap_ms'] > record['wall_ms'] or
                record['max_tick_ms'] > record['work_ms'] or record['max_gap_ms'] > record['gap_ms'] or
                record['continuation_ticks'] > record['ticks'] or record['continuation_ticks'] > record['posts']):
            raise RuntimeError(f'{marker}: timer work/gap or byte progress is inconsistent')
    if not require_complete:
        return
    if record['read_bytes'] != len(data) or record['max_read'] < 1 or record['chunks'] < 1:
        raise RuntimeError(f'{marker}: same-source scan did not finish all bounded reads')
    if marker == 'RU_GUI_TIMER' and (
            record['wall_ms'] > GUI_RU_TIMER_TIMEOUT_SECONDS * 1000 or record['ticks'] < 1 or
            record['work_ms'] <= 0 or record['max_tick_ms'] <= 0 or
            record['posts'] < 1 or record['continuation_ticks'] < 1 or
            record['feed'] != len(data) or record['bytes'] != len(data) or record['pending'] != 0 or
            record['style_notifications'] != 0 or record['fold_notifications'] != 0):
        raise RuntimeError(f'{marker}: production cooperative scheduler must complete within 30 seconds without style/fold callbacks')


def parse_ru_gui_measurement(stdout, marker, *, require_complete=True):
    integer_fields, time_fields = RU_GUI_MEASUREMENTS[marker]
    fields = integer_fields | time_fields
    lines = [line for line in stdout.splitlines() if line.startswith(marker)]
    if len(lines) != 1:
        raise RuntimeError(f'{marker}: exactly one same-source measurement is required')
    tokens = lines[0].split()
    if tokens[0] != marker:
        raise RuntimeError(f'{marker}: measurement marker has an invalid prefix')
    record = {}
    for token in tokens[1:]:
        if token.count('=') != 1:
            raise RuntimeError(f'{marker}: malformed measurement')
        key, value = token.split('=')
        if key in record or key not in fields:
            raise RuntimeError(f'{marker}: duplicate or unexpected measurement field')
        try:
            record[key] = int(value) if key in integer_fields else float(value)
        except ValueError as exc:
            raise RuntimeError(f'{marker}: nonnumeric measurement') from exc
    record['source_sha256'] = hashlib.sha256(gui_ru_timer_fixture()[0]).hexdigest()
    validate_ru_gui_measurement(record, marker, require_complete=require_complete)
    return record


def collect_ru_gui_measurement(result, stdout):
    """Keep a bounded partial measurement on failures; it can never grant a pass."""
    if result['name'] not in RU_GUI_CONSOLE_MEASUREMENTS:
        return
    marker, key = RU_GUI_CONSOLE_MEASUREMENTS[result['name']]
    try:
        result[key] = parse_ru_gui_measurement(stdout, marker, require_complete=False)
    except RuntimeError as exc:
        result['measurement_error'] = str(exc)


def run_console(api, name, command, evidence, marker, timeout=120, expected_assertions=None, cwd=None):
    clock = PerformanceClock()
    out, err = evidence / f'{name}.stdout.log', evidence / f'{name}.stderr.log'
    result = {'name': name, 'passed': False, 'executed': False, 'cleanup_killed': False}
    started = None
    process = None
    try:
        started = clock()
        with out.open('xb') as stdout, err.open('xb') as stderr:
            process = subprocess.Popen(command, cwd=cwd or ROOT, stdout=stdout, stderr=stderr)
            result['executed'] = True
            deadline = clock() + timeout
            while process.poll() is None:
                api.no_dialog(process.pid)
                if clock() >= deadline:
                    raise RuntimeError(f'{name}: exceeded {timeout}-second execution deadline')
                if out.stat().st_size > MAX_LOG_BYTES or err.stat().st_size > MAX_LOG_BYTES:
                    raise RuntimeError(f'{name}: exceeded synthetic log size limit')
                time.sleep(0.1)
            result['exit_code'] = process.returncode
        stdout_text, stderr_text = bounded_text(out), bounded_text(err)
        collect_ru_gui_measurement(result, stdout_text)
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
        fixture_markers = re.findall(r'^WRONG_LEXER_FIXTURE_PREFLIGHT[^\r\n]*', stdout_text, re.M)
        if name == 'syntax_bad_lexer':
            if (fixture_markers != [WRONG_LEXER_PREFLIGHT_MARKER] or
                    stdout_text.count('WRONG_LEXER_FIXTURE_PREFLIGHT') != 1 or
                    'WRONG_LEXER_FIXTURE_PREFLIGHT' in stderr_text):
                raise RuntimeError('Wrong-lexer native fixture preflight marker is missing or malformed')
            result['native_fixture_preflight'] = True
        elif 'WRONG_LEXER_FIXTURE_PREFLIGHT' in stdout_text + stderr_text:
            raise RuntimeError('Unexpected wrong-lexer fixture preflight marker')
        if name == 'ru_syntax_native':
            result['performance'] = parse_ru_performance(stdout_text)
        if name in RU_GUI_CONSOLE_MEASUREMENTS:
            measurement_marker, key = RU_GUI_CONSOLE_MEASUREMENTS[name]
            validate_ru_gui_measurement(result.get(key), measurement_marker)
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
        if name in RU_GUI_CONSOLE_MEASUREMENTS and out.is_file():
            collect_ru_gui_measurement(result, bounded_text(out))
        finish_result_clock(result, clock, started)
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
                     'src/main.ru', 'src/ru_syntax.ru', 'tests/ru_syntax_native.ru',
                     'tests/app_ru_native.ru', 'tools/test_ru_timer_corpus.py',
                     'tools/test_syntax_diagnostics.py', 'src/ru_native_syntax.ru',
                     'tests/ru_event_bulk_portable.py')}}


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
    corpus_lines = texts['timer-corpus.stdout.log'].splitlines()
    expected_corpus_lines = [f'PASS: {backend} {fixture} exact UTF-8 corpus'
        for fixture in ('ru_syntax_native', 'app_ru_native') for backend in ('python', 'c')]
    if (corpus_lines != expected_corpus_lines + ['RU_TIMER_CORPUS_PASS: 4'] or
            texts['timer-corpus.stderr.log']):
        raise RuntimeError('Linux timer corpus requires exact complete bytes in both fixtures and both real backends')
    # The exact reviewed production-diagnostic probe validates every numeric
    # projection, ordinary-error record, field order and privacy sentinel.
    import test_syntax_diagnostics as diagnostic_control
    diagnostic = texts['diagnostic-control.stdout.log']
    marker = 'RU_DIAGNOSTIC_PORTABLE_PASS: 2\n'
    if (texts['diagnostic-control.stderr.log'] or not diagnostic.endswith(marker) or
            diagnostic.count(marker) != 1):
        raise RuntimeError('Linux diagnostic control requires both real backends with empty stderr')
    sections = diagnostic[:-len(marker)].split('BACKEND: ')
    if len(sections) != 3 or sections[0] or not sections[1].startswith('python\n') or not sections[2].startswith('c\n'):
        raise RuntimeError('Linux diagnostic control is missing its exact backend sequence')
    bodies = [section.split('\n', 1)[1] for section in sections[1:]]
    if bodies[0] != bodies[1] or any(not line.startswith(('PASS: ', 'TOTAL PASS: ', 'RU_GUI_SNAPSHOT '))
                                    for line in bodies[0].splitlines()):
        raise RuntimeError('Linux diagnostic control has inconsistent or unexpected output')
    for body in bodies:
        try:
            diagnostic_control.validate(body)
        except ValueError as exc:
            raise RuntimeError('Linux diagnostic control lacks exact safe production projections') from exc
    bulk_body = ''.join(f'PASS: {label}\n' for label in BULK_EVENT_CASES) + 'TOTAL PASS: 23\n'
    bulk_expected = ('BACKEND: python\n' + bulk_body + 'BACKEND: c\n' + bulk_body +
                     'RU_EVENT_BULK_PORTABLE_PASS: 2 backends, 23 assertions each\n')
    if texts['event-bulk.stdout.log'] != bulk_expected or texts['event-bulk.stderr.log']:
        raise RuntimeError('Linux bulk-event control requires all 23 exact cases in both real backends with empty stderr')
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
    clock = PerformanceClock()
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
    started = None
    try:
        started = clock()
        with out.open('xb') as stdout, err.open('xb') as stderr:
            process = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr)
            result['executed'] = True
            while process.poll() is None:
                api.no_dialog(process.pid)
                if clock() - started >= 180:
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
        finish_result_clock(result, clock, started)
    return result


def run_gui(api, binary_dir, evidence, *, name='main-gui-smoke', arguments=(),
            exercise=None, log_prefix='main-launcher'):
    clock = PerformanceClock()
    result = {'name': name, 'passed': False, 'executed': False,
              'main_hwnd_seen': False, 'close_posted': False, 'cleanup_killed': False,
              'detached_from_console': True}
    started = None
    process = None
    # The dedicated bin dir was just built by this CI run; reject stale logs.
    if list(binary_dir.glob('ru_notepad-*.log')):
        result['error'] = 'Refusing stale launcher logs in fresh test binary directory'
        return result
    try:
        started = clock()
        process = subprocess.Popen([str(binary_dir / 'ru_notepad.exe'), *map(str, arguments)], cwd=binary_dir,
                                   creationflags=0x00000008)  # DETACHED_PROCESS
        result['executed'] = True
        deadline = clock() + 30
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
            if clock() >= deadline:
                raise RuntimeError('No visible main HWND within 30 seconds')
            time.sleep(0.1)
        result['main_hwnd_seen'] = True
        result['window_class'] = MAIN_CLASS
        # Let queued startup work run, then prove that the actual event loop responds.
        settle_until = clock() + 1
        while clock() < settle_until:
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
        deadline = clock() + 15
        while process.poll() is None:
            api.no_dialog(process.pid)
            if clock() >= deadline:
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
        finish_result_clock(result, clock, started)
    return result


def wait_gui(api, process, predicate, failure, timeout=30):
    clock = PerformanceClock()
    deadline = clock() + timeout
    while True:
        api.no_dialog(process.pid)
        if process.poll() is not None:
            raise RuntimeError('GUI exited while checking synthetic file operations')
        if predicate():
            return
        if clock() >= deadline:
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
    clock = PerformanceClock()
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
        until = clock() + 0.5
        while clock() < until:
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



# GUI observer settings are fixed acceptance policy, not command-line tunables.
GUI_RU_RESPONSE_INTERVAL_MS = 50
GUI_RU_SNAPSHOT_INTERVAL_MS = 250
GUI_RU_SNAPSHOT_MESSAGE_LIMIT = 32
GUI_RU_DIAGNOSTIC_MESSAGE = 33671
GUI_RU_DIAGNOSTIC_TIMEOUT_SECONDS = 1
GUI_RU_SNAPSHOT_TIME_FIELDS = {'work_ms', 'gap_ms', 'max_tick_ms', 'max_gap_ms'}
GUI_RU_SNAPSHOT_INTEGER_FIELDS = {'seq', 'ok', 'generation', 'revision', 'pending',
    'bytes', 'feed', 'read_bytes', 'restart', 'chunks', 'ticks', 'posts',
    'continuation_ticks', 'queue_yields', 'stale_messages', 'text_notifications',
    'style_notifications', 'fold_notifications'}
GUI_RU_HEAD_MEASUREMENT = ('First observed matching head-token styles are an upper bound; '
    'full scalar snapshots are sampled no more often than every 250 ms, not a paint measurement.')


def finite_nonnegative(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def gui_ru_observer_record():
    return {'response_interval_ms': GUI_RU_RESPONSE_INTERVAL_MS,
        'snapshot_interval_ms': GUI_RU_SNAPSHOT_INTERVAL_MS,
        'snapshot_message_limit': GUI_RU_SNAPSHOT_MESSAGE_LIMIT,
        'scalar_calls': 0, 'wm_null_calls': 0, 'sendmessage_calls': 0,
        'query_wall_ms': 0.0, 'max_query_ms': 0.0,
        'snapshot_count': 0, 'snapshot_wall_ms': 0.0, 'max_snapshot_ms': 0.0,
        'max_snapshot_messages': 0, 'snapshots': [], 'response_starts_ms': []}


class GuiRuObserver:
    """Count actual synchronous calls, including text()'s two scalar calls."""
    def __init__(self, api, record, started, clock=None):
        self.api, self.record, self.started = api, record, started
        self.clock = PerformanceClock(started) if clock is None else clock
        self.current = None
        self.originals = {}
        self.shadows = {}

    def __enter__(self):
        for name in ('scalar', 'responsive'):
            self.originals[name] = getattr(self.api, name)
            self.shadows[name] = self.api.__dict__.get(name)
            setattr(self.api, name, self.wrap(name))
        return self

    def wrap(self, name):
        def measured(*args, **kwargs):
            if self.current is not None and self.current['messages'] >= GUI_RU_SNAPSHOT_MESSAGE_LIMIT:
                raise RuntimeError('GUI Ru snapshot exceeded its 32 synchronous message limit')
            begin = self.clock()
            if begin - self.started > GUI_RU_TIMER_TIMEOUT_SECONDS:
                raise RuntimeError('GUI 1 MB open and Ru timer styling exceeded 30 seconds')
            if name == 'responsive':
                starts = self.record['response_starts_ms']
                offset = (begin - self.started) * 1000
                if starts and offset - starts[-1] < GUI_RU_RESPONSE_INTERVAL_MS - 0.001:
                    raise RuntimeError('GUI Ru WM_NULL sampling exceeded its fixed frequency')
                starts.append(round(offset, 3))
            key = 'scalar_calls' if name == 'scalar' else 'wm_null_calls'
            self.record[key] += 1
            self.record['sendmessage_calls'] += 1
            if self.current is not None:
                self.current['messages'] += 1
            try:
                return self.originals[name](*args, **kwargs)
            finally:
                elapsed = (self.clock() - begin) * 1000
                self.record['query_wall_ms'] += elapsed
                self.record['max_query_ms'] = max(self.record['max_query_ms'], elapsed)
        return measured

    def snapshot(self, callback):
        begin = self.clock()
        current = {'start_ms': round((begin - self.started) * 1000, 3),
                   'wall_ms': 0.0, 'messages': 0, 'final': False}
        previous = self.record['snapshots']
        if previous and current['start_ms'] - previous[-1]['start_ms'] < GUI_RU_SNAPSHOT_INTERVAL_MS - 0.001:
            raise RuntimeError('GUI Ru full snapshots exceeded their fixed frequency')
        if len(previous) >= 121:
            raise RuntimeError('GUI Ru exceeded its bounded snapshot count')
        previous.append(current)
        self.current = current
        try:
            current['final'] = bool(callback())
            return current['final']
        finally:
            self.current = None
            self.record['snapshot_count'] += 1
            self.record['max_snapshot_messages'] = max(self.record['max_snapshot_messages'], current['messages'])
            current['wall_ms'] = round((self.clock() - begin) * 1000, 3)
            self.record['snapshot_wall_ms'] += current['wall_ms']
            self.record['max_snapshot_ms'] = max(self.record['max_snapshot_ms'], current['wall_ms'])

    def __exit__(self, *unused):
        for name in self.originals:
            if self.shadows[name] is None:
                delattr(self.api, name)
            else:
                setattr(self.api, name, self.shadows[name])
        for field in ('query_wall_ms', 'max_query_ms', 'snapshot_wall_ms', 'max_snapshot_ms'):
            self.record[field] = round(self.record[field], 3)


def parse_gui_ru_snapshots(text):
    records = []
    fields = GUI_RU_SNAPSHOT_INTEGER_FIELDS | GUI_RU_SNAPSHOT_TIME_FIELDS
    lines = text.splitlines(keepends=True)
    for index, raw in enumerate(lines):
        line = raw.rstrip('\r\n')
        if 'RU_GUI_SNAPSHOT' not in line:
            continue
        # A concurrent append may expose an unfinished final line. Never
        # accept it; capture retries only within its separate fixed bound.
        if index == len(lines) - 1 and not raw.endswith('\n'):
            break
        if not line.startswith('RU_GUI_SNAPSHOT ') or len(records) >= 3:
            raise RuntimeError('GUI Ru diagnostic snapshot marker or count is malformed')
        values = {}
        for token in line.split()[1:]:
            if token.count('=') != 1:
                raise RuntimeError('GUI Ru diagnostic snapshot token is malformed')
            key, value = token.split('=')
            if key not in fields or key in values or not re.fullmatch(r'\d+(?:\.\d+)?(?:[eE][+-]?\d+)?', value):
                raise RuntimeError('GUI Ru diagnostic snapshot field is malformed or duplicated')
            if key in GUI_RU_SNAPSHOT_INTEGER_FIELDS:
                if not re.fullmatch(r'0|[1-9]\d*', value) or int(value) > 9007199254740991:
                    raise RuntimeError('GUI Ru diagnostic snapshot integer is unsafe')
                values[key] = int(value)
            else:
                values[key] = float(value)
                if not finite_nonnegative(values[key]):
                    raise RuntimeError('GUI Ru diagnostic snapshot time is not finite')
        expected = fields if values.get('ok') == 1 else {'seq', 'ok'}
        if (set(values) != expected or values.get('ok') not in (0, 1) or
                values.get('seq') != len(records) + 1 or
                (values.get('ok') == 1 and values['pending'] not in (0, 1))):
            raise RuntimeError('GUI Ru diagnostic snapshot shape or sequence is malformed')
        records.append(values)
    return records


class GuiRuDiagnostics:
    def __init__(self, api, hwnd, binary_dir, record, clock=None):
        self.api, self.hwnd, self.binary_dir, self.record = api, hwnd, binary_dir, record
        self.clock = PerformanceClock() if clock is None else clock
        record.update(message=GUI_RU_DIAGNOSTIC_MESSAGE, capture_limit_ms=1000,
                      requests=[], receipts=[], captures=[], post_wall_ms=0.0, log_reads=0,
                      log_read_wall_ms=0.0, max_log_read_ms=0.0)
        self.path = None

    def request(self, phase):
        if phase not in ('baseline', 'pending', 'final') or len(self.record['requests']) >= 3:
            raise RuntimeError('GUI Ru diagnostic request is outside its bounded phases')
        begin = self.clock()
        entry = {'phase': phase, 'post_wall_ms': 0.0, 'accepted': False}
        self.record['requests'].append(entry)
        try:
            self.api.post_ru_snapshot(self.hwnd)
            entry['accepted'] = True
        finally:
            entry['post_wall_ms'] = round((self.clock() - begin) * 1000, 3)
            self.record['post_wall_ms'] = round(sum(item['post_wall_ms'] for item in self.record['requests']), 3)

    def read(self):
        begin = self.clock()
        if self.record['log_reads'] >= 44:
            raise RuntimeError('GUI Ru diagnostic log reads exceeded their fixed bound')
        self.record['log_reads'] += 1
        try:
            if self.path is None:
                paths = list(self.binary_dir.glob('ru_notepad-*.log'))
                if len(paths) != 1 or paths[0].is_symlink():
                    raise RuntimeError('GUI Ru diagnostics require one fresh owned launcher log')
                self.path = paths[0]
            records = parse_gui_ru_snapshots(bounded_text(portable.checked_file(self.path)))
            if records[:len(self.record['receipts'])] != self.record['receipts']:
                raise RuntimeError('GUI Ru diagnostic log changed its accepted prefix')
            if len(records) > len(self.record['requests']):
                raise RuntimeError('GUI Ru diagnostic receipt has no matching request')
            self.record['receipts'] = records
            return len(records)
        finally:
            elapsed = (self.clock() - begin) * 1000
            self.record['log_read_wall_ms'] = round(self.record['log_read_wall_ms'] + elapsed, 3)
            self.record['max_log_read_ms'] = round(max(self.record['max_log_read_ms'], elapsed), 3)

    def capture(self, expected):
        begin = self.clock()
        first_read = self.record['log_reads']
        entry = {'phase': self.record['requests'][-1]['phase'], 'wall_ms': 0.0, 'log_reads': 0}
        self.record['captures'].append(entry)
        try:
            while True:
                count = self.read()
                elapsed = self.clock() - begin
                if elapsed > GUI_RU_DIAGNOSTIC_TIMEOUT_SECONDS:
                    raise RuntimeError('GUI Ru diagnostic receipt did not arrive within its separate 1-second limit')
                if count == expected:
                    return
                time.sleep(GUI_RU_RESPONSE_INTERVAL_MS / 1000)
        finally:
            entry['log_reads'] = self.record['log_reads'] - first_read
            entry['wall_ms'] = round((self.clock() - begin) * 1000, 3)


def validate_gui_ru_observer(record, wall_ms, probes):
    if not isinstance(record, dict) or set(record) != set(gui_ru_observer_record()):
        raise RuntimeError('GUI Ru observer cost record is missing or malformed')
    for field, fixed in [('response_interval_ms', 50), ('snapshot_interval_ms', 250), ('snapshot_message_limit', 32)]:
        if type(record[field]) is not int or record[field] != fixed:
            raise RuntimeError('GUI Ru observer sampling policy was changed')
    for field in ('scalar_calls', 'wm_null_calls', 'sendmessage_calls', 'snapshot_count', 'max_snapshot_messages'):
        if type(record[field]) is not int or record[field] < 1:
            raise RuntimeError('GUI Ru observer lacks actual message or snapshot counts')
    for field in ('query_wall_ms', 'max_query_ms', 'snapshot_wall_ms', 'max_snapshot_ms'):
        if not finite_nonnegative(record[field]) or record[field] > wall_ms + 0.01:
            raise RuntimeError('GUI Ru observer cost is not finite or exceeds its measured stage')
    if (record['wm_null_calls'] != probes or record['sendmessage_calls'] != record['scalar_calls'] + probes or
            record['max_query_ms'] > record['query_wall_ms'] + 0.01):
        raise RuntimeError('GUI Ru observer synchronous message counts or costs disagree')
    starts = record['response_starts_ms']
    if (not isinstance(starts, list) or len(starts) != probes or not 1 <= len(starts) <= 601 or
            any(not finite_nonnegative(value) or value > wall_ms for value in starts) or
            any(right - left < 49.999 for left, right in zip(starts, starts[1:]))):
        raise RuntimeError('GUI Ru WM_NULL frequency is unbounded or inconsistent')
    snapshots = record['snapshots']
    if not isinstance(snapshots, list) or not 1 <= len(snapshots) <= 121 or record['snapshot_count'] != len(snapshots):
        raise RuntimeError('GUI Ru full snapshot count is unbounded or inconsistent')
    for entry in snapshots:
        if (not isinstance(entry, dict) or set(entry) != {'start_ms', 'wall_ms', 'messages', 'final'} or
                not finite_nonnegative(entry['start_ms']) or not finite_nonnegative(entry['wall_ms']) or
                entry['start_ms'] + entry['wall_ms'] > wall_ms + 0.01 or type(entry['final']) is not bool or
                type(entry['messages']) is not int or not 1 <= entry['messages'] <= 32):
            raise RuntimeError('GUI Ru full snapshot duration or actual message bound is invalid')
    if (any(right['start_ms'] - left['start_ms'] < 249.999 for left, right in zip(snapshots, snapshots[1:])) or
            snapshots[-1]['final'] is not True or any(entry['final'] for entry in snapshots[:-1]) or
            record['max_snapshot_messages'] != max(entry['messages'] for entry in snapshots) or
            record['max_snapshot_ms'] != max(entry['wall_ms'] for entry in snapshots) or
            abs(record['snapshot_wall_ms'] - sum(entry['wall_ms'] for entry in snapshots)) > 0.01 or
            sum(entry['messages'] for entry in snapshots) > record['scalar_calls']):
        raise RuntimeError('GUI Ru snapshot frequencies, final proof, or cost totals disagree')


def validate_gui_ru_diagnostics(record):
    expected = {'message', 'capture_limit_ms', 'requests', 'receipts', 'captures', 'post_wall_ms',
                'log_reads', 'log_read_wall_ms', 'max_log_read_ms'}
    if (not isinstance(record, dict) or set(record) != expected or
            type(record['message']) is not int or record['message'] != GUI_RU_DIAGNOSTIC_MESSAGE or
            type(record['capture_limit_ms']) is not int or record['capture_limit_ms'] != 1000 or
            type(record['log_reads']) is not int or not 2 <= record['log_reads'] <= 44 or
            not isinstance(record['requests'], list) or len(record['requests']) != 3 or
            not isinstance(record['receipts'], list) or len(record['receipts']) != 3 or
            not isinstance(record['captures'], list) or len(record['captures']) != 2):
        raise RuntimeError('GUI Ru diagnostic capture record is missing or malformed')
    for entry, phase in zip(record['captures'], ('baseline', 'final')):
        if (not isinstance(entry, dict) or set(entry) != {'phase', 'wall_ms', 'log_reads'} or
                entry['phase'] != phase or not finite_nonnegative(entry['wall_ms']) or entry['wall_ms'] > 1000.01 or
                type(entry['log_reads']) is not int or not 1 <= entry['log_reads'] <= 22):
            raise RuntimeError('GUI Ru diagnostic capture phase or independent deadline is invalid')
    if sum(entry['log_reads'] for entry in record['captures']) != record['log_reads']:
        raise RuntimeError('GUI Ru diagnostic capture counts disagree')
    for field in ('post_wall_ms', 'log_read_wall_ms', 'max_log_read_ms'):
        if not finite_nonnegative(record[field]):
            raise RuntimeError('GUI Ru diagnostic cost must be finite and nonnegative')
    for request, phase in zip(record['requests'], ('baseline', 'pending', 'final')):
        if (not isinstance(request, dict) or set(request) != {'phase', 'post_wall_ms', 'accepted'} or
                request['phase'] != phase or request['accepted'] is not True or not finite_nonnegative(request['post_wall_ms'])):
            raise RuntimeError('GUI Ru diagnostic requests do not match their fixed phases')
    if (abs(sum(item['post_wall_ms'] for item in record['requests']) - record['post_wall_ms']) > 0.01 or
            record['max_log_read_ms'] > record['log_read_wall_ms'] + 0.01):
        raise RuntimeError('GUI Ru diagnostic post or log-read costs disagree')
    for index, receipt in enumerate(record['receipts']):
        if index == 0 and receipt == {'seq': 1, 'ok': 0} and all(type(value) is int for value in receipt.values()):
            continue
        if (not isinstance(receipt, dict) or set(receipt) != GUI_RU_SNAPSHOT_INTEGER_FIELDS | GUI_RU_SNAPSHOT_TIME_FIELDS or
                any(type(receipt[key]) is not int or not 0 <= receipt[key] <= 9007199254740991 for key in GUI_RU_SNAPSHOT_INTEGER_FIELDS) or
                any(not finite_nonnegative(receipt[key]) for key in GUI_RU_SNAPSHOT_TIME_FIELDS) or
                receipt['seq'] != index + 1 or receipt['ok'] != 1 or receipt['pending'] not in (0, 1)):
            raise RuntimeError('GUI Ru diagnostic receipt is incomplete or malformed')
        if (not 0 <= receipt['bytes'] <= receipt['feed'] <= receipt['read_bytes'] <= GUI_RU_TIMER_BYTES or
                receipt['continuation_ticks'] > min(receipt['ticks'], receipt['posts']) or
                receipt['max_tick_ms'] > receipt['work_ms'] + 0.000001 or
                receipt['max_gap_ms'] > receipt['gap_ms'] + 0.000001):
            raise RuntimeError('GUI Ru diagnostic partial-byte or cost invariants are invalid')
    baseline, pending, final = record['receipts']
    if ((baseline['ok'] == 1 and (baseline['pending'] != 0 or pending['generation'] <= baseline['generation'])) or pending['pending'] != 1 or
            final['generation'] != pending['generation'] or pending['revision'] != 0 or final['revision'] != 0 or
            final['pending'] != 0 or any(final[key] != GUI_RU_TIMER_BYTES for key in ('bytes', 'feed', 'read_bytes')) or
            final['restart'] != 0 or any(final[key] != 0 for key in ('style_notifications', 'fold_notifications')) or
            final['continuation_ticks'] > final['ticks']):
        raise RuntimeError('GUI Ru diagnostic receipts do not prove the same complete untouched timer document')
    monotonic_fields = (GUI_RU_SNAPSHOT_INTEGER_FIELDS | GUI_RU_SNAPSHOT_TIME_FIELDS) - {'seq', 'ok', 'generation', 'revision', 'pending'}
    if any(final[key] < pending[key] for key in monotonic_fields):
        raise RuntimeError('GUI Ru same-generation diagnostic counters moved backwards')


def validate_gui_ru_timer(record, *, require_windows_clock=False):
    data, probes = gui_ru_timer_fixture()
    if not isinstance(record, dict) or set(record) != GUI_RU_TIMER_FIELDS:
        raise RuntimeError('GUI Ru timer performance record is missing or malformed')
    validate_performance_clock(record['clock'], require_windows=require_windows_clock)
    if record['clock_measurement'] != PERFORMANCE_CLOCK_MEASUREMENT:
        raise RuntimeError('GUI Ru timing must disclose clock and observation limits')
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
    if record['head_style_measurement'] != GUI_RU_HEAD_MEASUREMENT:
        raise RuntimeError('GUI Ru first head-style timing must disclose its sampling upper bound')
    validate_gui_ru_observer(record['observer'], record['wall_ms'], record['probes'])
    validate_gui_ru_diagnostics(record['diagnostics'])
    validate_gui_ru_responsiveness(record['responsiveness'], record['wall_ms'])


def validate_gui_ru_responsiveness(record, wall_ms):
    if (not isinstance(record, dict) or set(record) != {'measurement', 'navigation', 'paint'} or
            record['measurement'] != GUI_RU_RESPONSE_MEASUREMENT or
            not isinstance(record['navigation'], list) or len(record['navigation']) != 2):
        raise RuntimeError('GUI Ru styling lacks bounded real queued navigation and paint-region evidence')
    def valid_time(value):
        return (type(value) in (int, float) and math.isfinite(value) and
                0 <= value <= min(GUI_RU_RESPONSE_TIMEOUT_MS, wall_ms))
    for actual, expected in zip(record['navigation'], GUI_RU_NAVIGATION):
        if (not isinstance(actual, dict) or set(actual) != set(expected) | {'wall_ms', 'while_styling'} or
                any(actual.get(key) != value for key, value in expected.items()) or
                any(type(actual[key]) is not int for key in ('before', 'after')) or
                actual['while_styling'] is not True or not valid_time(actual['wall_ms'])):
            raise RuntimeError('GUI Ru queued navigation did not prove bounded 0-to-3-to-0 caret movement while styling')
    paint = record['paint']
    if (not isinstance(paint, dict) or set(paint) !=
            {'invalidations', 'pending_observed', 'already_serviced', 'cleared', 'wall_ms', 'while_styling'} or
            type(paint['invalidations']) is not int or paint['invalidations'] != 1 or
            type(paint['pending_observed']) is not bool or type(paint['already_serviced']) is not bool or
            paint['pending_observed'] == paint['already_serviced'] or
            paint['cleared'] is not True or paint['while_styling'] is not True or not valid_time(paint['wall_ms'])):
        raise RuntimeError('GUI Ru invalidated region was not naturally serviced within its styling window')


def run_gui_ru_responsiveness(api, process, hwnd, editor, record, timer_started, still_styling, clock=None):
    # A single bounded interaction on the untouched 1 MB corpus. All waits use
    # the original timer-stage deadline; no new completion window is created.
    clock = PerformanceClock(timer_started) if clock is None else clock
    record.update(measurement=GUI_RU_RESPONSE_MEASUREMENT, navigation=[], paint={})
    if api.scalar(editor, 2008) != 0 or not still_styling():  # SCI_GETCURRENTPOS
        raise RuntimeError('GUI Ru responsiveness probe did not begin at BOF while styling was pending')
    input_started = clock()
    api.post_navigation(editor, 'RIGHT')
    paint_started = clock()
    initial_pending = api.invalidate_for_paint(editor)
    paint = record['paint']
    paint.update(invalidations=1, pending_observed=initial_pending,
                 already_serviced=not initial_pending, cleared=False, wall_ms=0.0, while_styling=False)
    while len(record['navigation']) < 2 or not paint['cleared']:
        api.no_dialog(process.pid)
        if process.poll() is not None:
            raise RuntimeError('GUI exited during pending-style input/paint probes')
        now = clock()
        if now - timer_started > GUI_RU_TIMER_TIMEOUT_SECONDS:
            raise RuntimeError('GUI 1 MB open and Ru timer styling exceeded 30 seconds')
        if len(record['navigation']) < 2:
            expected = GUI_RU_NAVIGATION[len(record['navigation'])]
            position = api.scalar(editor, 2008)
            input_ms = (clock() - input_started) * 1000
            if input_ms > GUI_RU_RESPONSE_TIMEOUT_MS:
                raise RuntimeError('GUI Ru queued navigation exceeded the existing 5-second response limit')
            if position == expected['after']:
                pending = still_styling()
                record['navigation'].append(dict(expected, wall_ms=round(input_ms, 3), while_styling=pending))
                if not pending:
                    raise RuntimeError('GUI Ru queued navigation was only observed after styling completed')
                if len(record['navigation']) == 1:
                    input_started = clock()
                    api.post_navigation(editor, 'LEFT')
            elif position != expected['before']:
                raise RuntimeError('GUI Ru queued navigation reached an unexpected UTF-8 caret position')
        if not paint['cleared']:
            pending_region = api.paint_pending(editor)
            paint_ms = (clock() - paint_started) * 1000
            paint['wall_ms'] = round(paint_ms, 3)
            if paint_ms > GUI_RU_RESPONSE_TIMEOUT_MS:
                raise RuntimeError('GUI Ru paint-region service exceeded the existing 5-second response limit')
            if not pending_region:
                paint.update(cleared=True, while_styling=still_styling())
                if not paint['while_styling']:
                    raise RuntimeError('GUI Ru paint region was only serviced after styling completed')
        if len(record['navigation']) < 2 or not paint['cleared']:
            time.sleep(GUI_RU_RESPONSE_INTERVAL_MS / 1000)
    if api.scalar(editor, 2008) != 0 or api.scalar(editor, 2159) != 0:
        raise RuntimeError('GUI Ru responsiveness probes changed the document or did not restore its caret')


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
    clock = PerformanceClock()
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
        started = clock()
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
                response = clock()
                api.responsive(hwnd)
                metrics['max_response_ms'] = max(metrics['max_response_ms'], (clock() - response) * 1000)
                metrics['probes'] += 1
                complete = state_matches(data, shifted, True, position)
                elapsed = clock() - started
                if elapsed > 30:
                    raise RuntimeError('Real length-changing Ru edit exceeded 30 seconds')
                if complete:
                    finished = elapsed
                    break
                time.sleep(0.01)
        finally:
            metrics['wall_ms'] = round((finished if finished is not None else clock() - started) * 1000, 3)
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
    clock = PerformanceClock()
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
                    'probes': 0, 'source_sha256': timer_sha, 'style_probes': timer_probes,
                    'last_probe': None, 'responsiveness': {}, 'observer': gui_ru_observer_record(),
                    'diagnostics': {}, 'head_style_measurement': GUI_RU_HEAD_MEASUREMENT,
                    'clock': {}, 'clock_measurement': PERFORMANCE_CLOCK_MEASUREMENT}
    edit_source = inputs / '真实编辑 十万字节 😀.ru'
    edit_data, edit_probes, edit_folds, _ = gui_ru_edit_fixture()
    edit_source.write_bytes(edit_data)
    edit_sha = sha(edit_source)
    edit_record = {'size': len(edit_data), 'source_sha256': edit_sha, 'style_probes': edit_probes,
                   'measurement': GUI_RU_EDIT_MEASUREMENT,
                   'fold_probes': edit_folds, 'operations': [], 'undo_commands': 0}

    def exercise(process, hwnd):
        timer_record['clock'] = performance_clock_record()
        checks = {}
        tab_count = lambda: api.scalar(api.control(hwnd, 10), 0x1304)
        wait_gui(api, process, lambda: tab_count() == 2 and
                 api.text(hwnd) == source.name + ' · ru_notepad',
                 'Unicode Ru command-line file did not finish opening')
        checks['cli_unicode_path'] = True
        editor = api.editor(hwnd)
        if api.scalar(editor, 2378) != 3:  # SCI_GETMODEVENTMASK
            raise RuntimeError('GUI Ru editor must use the production insert/delete notification mask')
        checks['initial_mod_event_mask'] = True
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
        diagnostics = GuiRuDiagnostics(api, hwnd, isolated, timer_record['diagnostics'], clock)
        diagnostics.request('baseline')
        diagnostics.capture(1)
        started = clock()
        finished_elapsed = None
        active = status_handle = None
        matched_head = {}
        needs_responsiveness = False
        next_response = next_snapshot = started

        def snapshot():
            nonlocal active, status_handle, matched_head, needs_responsiveness
            if active is None:
                opened = tab_count() == 3 and api.text(hwnd) == timer_source.name + ' · ru_notepad'
                if opened:
                    active, status_handle = api.editor(hwnd), api.control(hwnd, 11)
                    api.verify_owned_handles(process.pid, active, status_handle)
                    if api.scalar(active, 2378) != 3:
                        raise RuntimeError('GUI Ru timer child must use the production insert/delete notification mask')
                    checks['timer_mod_event_mask'] = True
            else:
                opened = True
            last = {'opened': opened, 'length': None, 'clean': None,
                    'end_styled': None, 'status': '', 'style_matches': {}}
            timer_record['last_probe'] = last
            if not opened:
                return False
            length, clean = api.scalar(active, 2006), api.scalar(active, 2159) == 0
            last.update(length=length, clean=clean, end_styled=api.scalar(active, 2028))
            if not clean:
                raise RuntimeError('GUI timer styling made the 1 MB document dirty')
            status = api.text(status_handle)
            status_done = bool(status.strip()) and 'Styling Ru' not in status and not status.lstrip().startswith('Opening:')
            matched = {}
            if length == len(timer_data):
                for label, probe in timer_probes.items():
                    if label.startswith('head') and matched_head.get(label) and not status_done:
                        matched[label] = True
                    else:
                        # Evaluate every byte even after a mismatch. At final
                        # completion none of the cached head results are used.
                        values = [api.scalar(active, 2010, position) == probe['style']
                                  for position in range(probe['offset'], probe['offset'] + probe['length'])]
                        matched[label] = all(values)
                matched_head = {label: value for label, value in matched.items() if label.startswith('head')}
                if all(matched_head.values()) and timer_record['first_head_style_ms'] is None:
                    timer_record['first_head_style_ms'] = round((clock() - started) * 1000, 3)
            last.update(status=status[:512], style_matches=matched)
            needs_responsiveness = (not timer_record['responsiveness'] and length == len(timer_data) and
                'Styling Ru' in status and not all(matched[name] for name in matched if name.startswith('tail')))
            if not (length == len(timer_data) and clean and all(matched.values()) and status_done):
                return False
            # The immutable <=30s success point follows all 16 fresh style
            # bytes AND a final length/clean/status recheck. Diagnostics never
            # establish or extend success after this point.
            length, clean = api.scalar(active, 2006), api.scalar(active, 2159) == 0
            status = api.text(status_handle)
            last.update(length=length, clean=clean, status=status[:512])
            api.verify_owned_handles(process.pid, active, status_handle)
            return (length == len(timer_data) and clean and bool(status.strip()) and
                    'Styling Ru' not in status and not status.lstrip().startswith('Opening:'))

        try:
            with GuiRuObserver(api, timer_record['observer'], started, clock) as observer:
                api.drop(editor, [timer_source])
                checks['timer_child_drop_routed'] = True
                while True:
                    api.no_dialog(process.pid)
                    if process.poll() is not None:
                        raise RuntimeError('GUI exited during the 1 MB Ru timer stage')
                    now = clock()
                    if now - started > GUI_RU_TIMER_TIMEOUT_SECONDS:
                        raise RuntimeError('GUI 1 MB open and Ru timer styling exceeded 30 seconds')
                    if now >= next_response:
                        response_started = clock()
                        try:
                            api.responsive(hwnd)
                        finally:
                            timer_record['probes'] = timer_record['observer']['wm_null_calls']
                            timer_record['max_response_ms'] = max(timer_record['max_response_ms'],
                                (clock() - response_started) * 1000)
                        next_response = clock() + GUI_RU_RESPONSE_INTERVAL_MS / 1000
                    complete = False
                    if clock() >= next_snapshot:
                        complete = observer.snapshot(snapshot)
                        next_snapshot = clock() + GUI_RU_SNAPSHOT_INTERVAL_MS / 1000
                    if needs_responsiveness:
                        needs_responsiveness = False
                        diagnostics.request('pending')
                        def still_styling():
                            return ('Styling Ru' in api.text(status_handle) and
                                not all(api.scalar(active, 2010, position) == probe['style']
                                    for label, probe in timer_probes.items() if label.startswith('tail')
                                    for position in range(probe['offset'], probe['offset'] + probe['length'])))
                        run_gui_ru_responsiveness(api, process, hwnd, active,
                            timer_record['responsiveness'], started, still_styling, clock)
                        checks.update(timer_queued_navigation=True, timer_paint_region_serviced=True)
                    elapsed = clock() - started
                    if elapsed > GUI_RU_TIMER_TIMEOUT_SECONDS:
                        raise RuntimeError('GUI 1 MB open and Ru timer styling exceeded 30 seconds')
                    if complete:
                        finished_elapsed = elapsed
                        checks.update(timer_exact_length=True, timer_document_clean=True,
                                      timer_head_styles=True, timer_tail_styles=True, timer_status_cleared=True)
                        break
                    # No busy spin or catch-up burst: the next send is due at
                    # least 50 ms after the last completed WM_NULL query.
                    delay = min(next_response, next_snapshot, started + GUI_RU_TIMER_TIMEOUT_SECONDS) - clock()
                    time.sleep(max(0.001, delay))
            if sha(timer_source) != timer_sha:
                raise RuntimeError('GUI timer styling modified the 1 MB source file')
            checks['timer_source_bytes_preserved'] = True
        finally:
            failing = sys.exc_info()[0] is not None
            clock_error = None
            try:
                timer_record['wall_ms'] = round((finished_elapsed if finished_elapsed is not None
                                                else clock() - started) * 1000, 3)
            except RuntimeError as exc:
                timer_record.update(wall_ms=None, clock_error=str(exc))
                clock_error = exc
            timer_record['max_response_ms'] = round(timer_record['max_response_ms'], 3)
            try:
                diagnostics.request('final')
                diagnostics.capture(len(timer_record['diagnostics']['requests']))
            except Exception as exc:
                timer_record['diagnostics']['error'] = str(exc)
                if not failing and clock_error is None:
                    raise
            if clock_error is not None and not failing:
                raise clock_error
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
    if name == 'app_ru_timer_native':
        command.append('--measure-ru-timer')
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
        # A real DLL without CreateLexer or process-global window registration.
        # A second renamed Scintilla can fail DllMain when the real one is loaded.
        layout['Lexilla.dll'] = portable.NATIVE_HELPER_NAME
    if name in HELPER_FALLBACK_LAYOUTS:
        layout['Lexilla.dll'] = 'Lexilla.dll'
    helper_mode = HELPER_FALLBACK_LAYOUTS.get(name)
    if helper_mode != 'missing':
        layout[portable.NATIVE_HELPER_NAME] = (
            'Scintilla.dll' if helper_mode == 'bad-exports' else
            portable.NATIVE_WRONG_ABI_NAME if helper_mode == 'wrong-abi' else portable.NATIVE_HELPER_NAME)
    return layout


def validate_wrong_lexer_preflight(record, expected_hash):
    if (not isinstance(record, dict) or set(record) != WRONG_LEXER_PREFLIGHT_FIELDS or
            any(record[field] is not True for field in ('loadable', 'createlexer_missing', 'released')) or
            record['library_sha256'] != expected_hash):
        raise RuntimeError('Wrong-lexer fixture preflight did not prove exact loadable missing-export bytes and release')


def preflight_wrong_lexer(api, library, expected_hash):
    """Probe the exact staged bytes before launching the native child; no symbol calls."""
    record = dict(loadable=False, createlexer_missing=False, released=False,
                  library_sha256=sha(library))
    if record['library_sha256'] != expected_hash:
        raise RuntimeError('Wrong-lexer fixture changed before its loader preflight')
    handle = api.kernel.LoadLibraryExW(str(library.resolve(strict=True)), None, 2304)
    if handle:
        record['loadable'] = True
        try:
            record['createlexer_missing'] = not bool(api.kernel.GetProcAddress(handle, b'CreateLexer'))
        finally:
            record['released'] = bool(api.kernel.FreeLibrary(handle))
    if sha(library) != expected_hash:
        raise RuntimeError('Wrong-lexer fixture changed during its loader preflight')
    return record


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
        preflight = None
        preflight_error = None
        try:
            if name == 'syntax_bad_lexer':
                preflight = preflight_wrong_lexer(api, isolated / 'Lexilla.dll', fixture_hashes['Lexilla.dll'])
                validate_wrong_lexer_preflight(preflight, fixture_hashes['Lexilla.dll'])
        except Exception:
            preflight_error = 'Wrong-lexer fixture OS preflight failed'
        if preflight_error is not None:
            result = dict(name=name, passed=False, executed=False, cleanup_killed=False, error=preflight_error)
        else:
            result = dict(run_console(api, name, [str(isolated / executable), argument],
                evidence, r'^TOTAL PASS: 8\s*$', expected_assertions=8, cwd=isolated))
        if preflight is not None:
            result['fixture_preflight'] = preflight
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
        if test['name'] in RU_GUI_CONSOLE_MEASUREMENTS:
            marker, key = RU_GUI_CONSOLE_MEASUREMENTS[test['name']]
            validate_ru_gui_measurement(test.get(key), marker)
        if test['name'] in {case[0] for case in SYNTAX_FALLBACK_TESTS}:
            expected_hashes = {target: summary['tested_binary_sha256'][source]
                               for target, source in syntax_fallback_layout(test['name']).items()}
            if test.get('fixture_binary_sha256') != expected_hashes:
                raise RuntimeError('Syntax fallback fixture does not match the packaged test binaries')
        if test['name'] == 'syntax_bad_lexer':
            validate_wrong_lexer_preflight(test.get('fixture_preflight'),
                                           summary['tested_binary_sha256'][portable.NATIVE_HELPER_NAME])
            if test.get('native_fixture_preflight') is not True:
                raise RuntimeError('Wrong-lexer native fixture preflight evidence is missing')
        elif 'fixture_preflight' in test or 'native_fixture_preflight' in test:
            raise RuntimeError('Unexpected wrong-lexer fixture preflight evidence')
        if test['name'] in GUI_NAMES and not all(test.get(key) for key in
                ('main_hwnd_seen', 'close_posted', 'detached_from_console')):
            raise RuntimeError('GUI acceptance lacks ordinary visible-window startup/close')
        if test['name'] == 'main-gui-ru-syntax':
            if not all(test.get(key) for key in GUI_RU_CHECKS):
                raise RuntimeError('GUI Ru acceptance lacks a required style/fold/visibility/clean-state check')
            validate_gui_ru_timer(test.get('timer_performance'), require_windows_clock=True)
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
