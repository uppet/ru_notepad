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
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
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
    ('shortcuts', r'^TOTAL PASS: 34\s*$'),
    ('syntax_policy', r'^TOTAL PASS: 100\s*$'),
    ('status_native', r'^TOTAL PASS: 21\s*$'),
    ('syntax_native', r'^TOTAL PASS: 82\s*$'),
)
SYNTAX_FALLBACK_TESTS = (
    ('syntax_missing_lexilla', '--expect-missing', False),
    ('syntax_bad_lexer', '--expect-bad-lexer', True),
)
# These limits apply only to the named synthetic suites, never to user files.
# The >500 MB test is mandatory: low disk or timeout fails instead of skipping.
CONSOLE_EXECUTABLES = {'editor_largefile_native': 'editor_streaming_native'}
FIXTURE_ARGUMENT_TESTS = {'file_codec_tests', 'file_streaming_native', 'app_streaming_native',
                        'editor_streaming_native', 'editor_largefile_native'}
CONSOLE_TIMEOUT_SECONDS = {'file_streaming_native': 300, 'app_streaming_native': 180,
                           'editor_streaming_native': 300,
                           'editor_largefile_native': 900}
LARGE_FILE_MIN_FREE_BYTES = 2 * 1024 * 1024 * 1024
GUI_FILE_CHECKS = ('cli_unicode_paths', 'cli_exact_text', 'drop_unicode_paths',
                   'drop_exact_text', 'child_drop_routed', 'busy_observed', 'busy_responsive',
                   'cancel_no_partial_tab', 'cancel_queue_cleared', 'source_bytes_preserved')
GUI_NAMES = {'main-gui-smoke', 'main-gui-file-entry'}
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
        if name == 'main-gui-file-entry':
            required += ('[operation] open started', '[operation] open completed',
                         '[operation] cancelled')
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


def run_syntax_fallbacks(api, binary_dir, fixtures, evidence):
    results = []
    for name, argument, bad_lexer in SYNTAX_FALLBACK_TESTS:
        isolated = Path(fixtures) / name
        isolated.mkdir()
        for binary in ('syntax_native.exe', 'Scintilla.dll'):
            shutil.copyfile(binary_dir / binary, isolated / binary)
        if bad_lexer:
            # A real loadable DLL with no CreateLexer export, never a mock flag.
            shutil.copyfile(binary_dir / 'Scintilla.dll', isolated / 'Lexilla.dll')
        fixture_hashes = {binary: sha(isolated / binary) for binary in ('syntax_native.exe', 'Scintilla.dll')}
        for binary, digest in fixture_hashes.items():
            if digest != sha(binary_dir / binary):
                raise RuntimeError('Syntax fallback fixture differs from the tested binaries')
        if bad_lexer:
            fixture_hashes['Lexilla.dll'] = sha(isolated / 'Lexilla.dll')
            if fixture_hashes['Lexilla.dll'] != fixture_hashes['Scintilla.dll']:
                raise RuntimeError('Bad-export fixture must contain the exact Scintilla DLL copy')
        result = dict(run_console(api, name, [str(isolated / 'syntax_native.exe'), argument],
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


def validate_acceptance(summary):
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
        if test['name'] in {case[0] for case in SYNTAX_FALLBACK_TESTS}:
            expected_hashes = {name: summary['tested_binary_sha256'][name]
                               for name in ('syntax_native.exe', 'Scintilla.dll')}
            if test['name'] == 'syntax_bad_lexer':
                expected_hashes['Lexilla.dll'] = expected_hashes['Scintilla.dll']
            if test.get('fixture_binary_sha256') != expected_hashes:
                raise RuntimeError('Syntax fallback fixture does not match the packaged test binaries')
        if test['name'] in GUI_NAMES and not all(test.get(key) for key in
                ('main_hwnd_seen', 'close_posted', 'detached_from_console')):
            raise RuntimeError('GUI acceptance lacks ordinary visible-window startup/close')
        if test['name'] == 'main-gui-file-entry':
            if not all(test.get(key) for key in GUI_FILE_CHECKS):
                raise RuntimeError('GUI file-entry acceptance lacks a required Unicode/drop/cancel check')
            hashes = {name: summary['tested_binary_sha256'][name] for name in portable.RUNTIME_NAMES}
            if test.get('fixture_binary_sha256') != hashes:
                raise RuntimeError('GUI file-entry fixture does not match the packaged runtime binaries')


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
    parser.add_argument('--bin-dir', required=True, type=Path)
    parser.add_argument('--evidence-dir', required=True, type=Path)
    parser.add_argument('--mingw-root', required=True, type=Path)
    parser.add_argument('--objdump', required=True, type=Path)
    parser.add_argument('--acl', action='store_true', help='Run synthetic NTFS ACL replacement cases')
    args = parser.parse_args()
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
