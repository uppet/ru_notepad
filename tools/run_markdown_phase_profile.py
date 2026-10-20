#!/usr/bin/env python3
"""One owned release/profile Windows GUI pair. Never an acceptance gate.

No attach, OpenProcess, PID-based termination, fallback-log search, text editing,
whole-document colourise, sampling, or Windows GUI launch on non-Windows hosts.
The application and fixed synthetic input are private inputs, not public output.
"""
from __future__ import annotations

import argparse
import contextlib
import ctypes
from ctypes import wintypes
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import threading
import time

RUNTIME_NAMES = ('ru_notepad.exe', 'Scintilla.dll', 'Lexilla.dll', 'RuSyntax.dll')
FIXTURE_SHA256 = '2d9f79ee715b217c00792cf18a67485cdec96a14ea2ac86689156941a022c719'
FIXTURE_SIZE = 1000000
FIXTURE_NEWLINES = 100000
LIMIT = 64 * 1024
TOTAL_LIMIT = 256 * 1024
HARD_SECONDS = 120.0
POLL_SECONDS = 0.05
SNAPSHOT_SECONDS = 0.25
PREFIX = 'RU_MARKDOWN_PHASE_PROFILE '
MAIN_CLASS = 'RuNotepad.Main.0.1'
PHASES = ('timer_root', 'bridge_advance', 'pure_feed', 'bridge_publish', 'bulk_prepare',
          'native_other', 'native_bulk', 'callback')
REQUIRED_SOURCES = {'src/main.ru', 'src/markdown_syntax.ru', 'src/markdown_policy.ru',
                    'src/file_drop.ru', 'packaging/diagnostic_launcher.c',
                    'tools/windows_ci.py', 'tools/package.py'}


class StudyError(RuntimeError):
    """Fixed error codes only: do not copy paths or runtime messages to output."""


def fail(code):
    raise StudyError(code)


def checked_path(path, *, directory=False):
    """Reject a link/reparse point at every existing path component."""
    path = Path(os.path.abspath(path))
    for component in reversed((path, *path.parents)):
        info = component.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            fail('unsafe_link_or_reparse')
    info = path.lstat()
    if directory:
        if not stat.S_ISDIR(info.st_mode):
            fail('expected_directory')
    elif not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        fail('expected_single_link_regular_file')
    return path


@contextlib.contextmanager
def safe_open(path, mode='rb'):
    """Read the checked object, with no-follow open and identity verification.

    Windows OPEN_REPARSE_POINT prevents dereferencing the final component. The
    launcher allows FILE_SHARE_READ; readers must allow its existing writer.
    Ancestors are rechecked after opening. No arbitrary path is ever truncated.
    """
    path = checked_path(path)
    before = path.stat(follow_symlinks=False)
    if mode not in ('rb', 'r+b'):
        fail('unsafe_open_mode')
    writing = mode == 'r+b'
    if sys.platform == 'win32':
        import msvcrt
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                      ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.CreateFileW(str(path), 0xc0000000 if writing else 0x80000000, 3, None, 3, 0x00200000, None)
        if handle == ctypes.c_void_p(-1).value:
            fail('file_open_failed')
        try:
            fd = msvcrt.open_osfhandle(handle, (os.O_RDWR if writing else os.O_RDONLY) | os.O_BINARY)
        except BaseException:
            kernel.CloseHandle(handle)
            raise
    else:
        fd = os.open(path, (os.O_RDWR if writing else os.O_RDONLY) | getattr(os, 'O_NOFOLLOW', 0))
    with os.fdopen(fd, mode) as stream:
        actual = os.fstat(stream.fileno())
        checked_path(path)
        if (before.st_dev, before.st_ino) != (actual.st_dev, actual.st_ino):
            fail('file_identity_changed')
        if not stat.S_ISREG(actual.st_mode) or actual.st_nlink != 1:
            fail('unsafe_opened_file')
        yield stream


def digest(path):
    value = hashlib.sha256()
    with safe_open(path) as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def bounded_read(path, maximum=LIMIT):
    with safe_open(path) as stream:
        if os.fstat(stream.fileno()).st_size > maximum:
            fail('output_overflow')
        data = stream.read(maximum + 1)
        if len(data) > maximum:
            fail('output_overflow')
        return data


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail('duplicate_json_key')
        result[key] = value
    return result


def json_decode(data):
    try:
        return json.loads(data, object_pairs_hook=unique_object,
                          parse_constant=lambda _: fail('nonfinite_json'))
    except (ValueError, UnicodeError):
        fail('malformed_json')


def json_bytes(value):
    data = (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
    if len(data) > LIMIT:
        fail('output_overflow')
    return data


def write_new(path, data):
    checked_path(Path(path).parent, directory=True)
    with open(path, 'xb') as stream:
        stream.write(data)
    checked_path(path)


def relative_file(root, name):
    if (not isinstance(name, str) or not name or '\\' in name or ':' in name or
            '\x00' in name or PurePosixPath(name).is_absolute() or
            any(part in ('', '.', '..') for part in name.split('/'))):
        fail('unsafe_relative_path')
    return checked_path(Path(root).joinpath(*name.split('/')))


def check_hash(value):
    if not isinstance(value, str) or re.fullmatch('[0-9a-f]{64}', value) is None:
        fail('invalid_sha256')


def verify_hash(path, expected):
    check_hash(expected)
    if digest(path) != expected:
        fail('hash_mismatch')


def runtime_inventory(directory):
    found = set()
    for path in Path(directory).iterdir():
        if path.name not in RUNTIME_NAMES or path.name in found:
            fail('runtime_inventory')
        checked_path(path)
        found.add(path.name)
    if found != set(RUNTIME_NAMES):
        fail('runtime_inventory')


def verify_manifest(receipt, source_root, release_dir, profile_dir):
    """All receipt paths are relative to an explicit root, never a fallback."""
    receipt = checked_path(receipt)
    source_root = checked_path(source_root, directory=True)
    manifest = json_decode(bounded_read(receipt))
    fields = {'schema', 'compiler_commit', 'source_sha256', 'runtime_sha256', 'artifacts'}
    if not isinstance(manifest, dict) or set(manifest) != fields or type(manifest['schema']) is not int or manifest['schema'] != 1:
        fail('manifest_schema')
    if not isinstance(manifest['compiler_commit'], str) or re.fullmatch('[0-9a-f]{40}', manifest['compiler_commit']) is None:
        fail('compiler_identity')
    sources = manifest['source_sha256']
    if not isinstance(sources, dict) or not REQUIRED_SOURCES <= sources.keys() or len(sources) > 512:
        fail('source_inventory')
    for name, expected in sources.items():
        verify_hash(relative_file(source_root, name), expected)
    runtime = manifest['runtime_sha256']
    if not isinstance(runtime, dict) or set(runtime) != {'release', 'profile'}:
        fail('runtime_manifest_schema')
    for variant, directory in (('release', release_dir), ('profile', profile_dir)):
        directory = checked_path(directory, directory=True)
        runtime_inventory(directory)
        if not isinstance(runtime[variant], dict) or set(runtime[variant]) != set(RUNTIME_NAMES):
            fail('runtime_hash_inventory')
        for name, expected in runtime[variant].items():
            verify_hash(directory / name, expected)
    if runtime['release']['ru_notepad.exe'] == runtime['profile']['ru_notepad.exe']:
        fail('identical_release_profile_exe')
    if any(runtime['release'][name] != runtime['profile'][name] for name in RUNTIME_NAMES[1:]):
        fail('runtime_dll_mismatch')
    artifacts = manifest['artifacts']
    if not isinstance(artifacts, dict) or set(artifacts) != {'release_tu', 'profile_tu', 'source_map'}:
        fail('artifact_inventory')
    for record in artifacts.values():
        if not isinstance(record, dict) or set(record) != {'path', 'sha256'}:
            fail('artifact_schema')
        verify_hash(relative_file(receipt.parent, record['path']), record['sha256'])
    if artifacts['release_tu']['sha256'] == artifacts['profile_tu']['sha256']:
        fail('identical_translation_units')
    return manifest


def load_ci(source_root):
    path = checked_path(Path(source_root) / 'tools/windows_ci.py')
    spec = importlib.util.spec_from_file_location('_owned_markdown_windows_ci', path)
    module = importlib.util.module_from_spec(spec)
    # These are reviewed, manifest-hashed source files, not arbitrary plugins.
    previous_bytecode = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous_bytecode
    if Path(module.portable.__file__).resolve() != (path.parent / 'package.py').resolve():
        fail('unexpected_packaging_module')
    return module


def fixture_bytes(ci):
    data, styles, folds = ci.gui_markdown_fixture('unclosed-fence')
    verify_fixture(data)
    return data, styles, folds


def verify_fixture(data):
    if (len(data) != FIXTURE_SIZE or data.count(b'\n') != FIXTURE_NEWLINES or
            hashlib.sha256(data).hexdigest() != FIXTURE_SHA256):
        fail('fixture_identity')


class Deadline:
    def __init__(self, started, clock=time.monotonic, seconds=HARD_SECONDS):
        if not math.isfinite(started) or seconds <= 0 or seconds > HARD_SECONDS:
            fail('clock_invalid')
        self.started, self.end, self.clock, self.previous = started, started + seconds, clock, started
        self.lock = threading.Lock()

    def now(self):
        with self.lock:
            now = self.clock()
            if not math.isfinite(now) or now < self.previous:
                fail('clock_invalid')
            self.previous = now
            return now

    def remaining(self):
        remaining = self.end - self.now()
        if remaining <= 0:
            fail('hard_deadline')
        return remaining

    def message_timeout_ms(self):
        # Floor, never ceil: a blocking message must fit in the same envelope.
        result = min(5000, int(self.remaining() * 1000))
        if result < 1:
            fail('hard_deadline')
        return result

    def sleep(self, sleeper=time.sleep, seconds=POLL_SECONDS):
        sleeper(min(seconds, self.remaining()))
        self.remaining()


class OwnedGuard:
    """Independent timeout/output guard holding only the exact Popen object."""
    def __init__(self, process, deadline, logs):
        self.process, self.deadline, self.logs = process, deadline, logs
        self.error = None
        self.killed = False
        self.kill_lock = threading.Lock()
        self.stopped = threading.Event()
        self.thread = threading.Thread(target=self.watch, daemon=True)
        self.thread.start()

    def watch(self):
        while not self.stopped.is_set():
            try:
                self.deadline.remaining()
                self.logs.inspect()
            except (StudyError, OSError) as exc:
                self.error = str(exc) if isinstance(exc, StudyError) else 'log_inspection_failed'
                self.kill()
                return
            if self.process.poll() is not None:
                return
            self.stopped.wait(min(POLL_SECONDS, max(0, self.deadline.end - self.deadline.clock())))

    def kill(self):
        with self.kill_lock:
            if self.killed or self.process.poll() is not None:
                return
            self.killed = True
            try:
                # subprocess on Windows uses its retained handle, not a PID reopen.
                self.process.kill()
            except OSError:
                self.error = self.error or 'owned_termination_failed'

    def stop(self):
        self.stopped.set()
        # No post-deadline wait extension. The watcher never waits on the child.
        self.thread.join(timeout=0)


class OwnedLog:
    def __init__(self, directory, pid):
        if type(pid) is not int or not 0 < pid <= 0xffffffff:
            fail('invalid_owned_pid')
        self.directory = checked_path(directory, directory=True)
        self.pid = pid
        self.path = None
        self.identity = None
        self.pattern = re.compile(r'ru_notepad-' + f'{pid:08x}' + r'-[0-9a-f]{16}-[0-9]{2}\.log')

    def inspect(self, required=False):
        checked_path(self.directory, directory=True)
        matches = []
        for count, entry in enumerate(self.directory.iterdir(), 1):
            if count > len(RUNTIME_NAMES) + 1:
                fail('duplicate_or_extra_owned_log')
            if entry.name in RUNTIME_NAMES:
                checked_path(entry)
            elif self.pattern.fullmatch(entry.name):
                checked_path(entry)
                matches.append(entry)
            else:
                fail('unexpected_owned_directory_entry')
        if len(matches) > 1:
            fail('duplicate_launcher_log')
        if not matches:
            if required or self.path is not None:
                fail('missing_owned_launcher_log')
            return
        path = matches[0]
        info = path.stat(follow_symlinks=False)
        identity = (info.st_dev, info.st_ino)
        if self.path is not None and (path != self.path or identity != self.identity):
            fail('launcher_log_identity_changed')
        self.path, self.identity = path, identity
        if info.st_size > LIMIT:
            fail('output_overflow')

    def cap_after_exit(self, process):
        # Only this process's previously observed exact log can be truncated.
        # This bounds retention, not instantaneous writes by the unchanged launcher.
        if process.poll() is None or self.path is None:
            fail('log_cleanup_unconfirmed')
        checked_path(self.path)
        with safe_open(self.path, 'r+b') as stream:
            info = os.fstat(stream.fileno())
            if (info.st_dev, info.st_ino) != self.identity:
                fail('launcher_log_identity_changed')
            if info.st_size > LIMIT:
                stream.truncate(LIMIT)
            if os.fstat(stream.fileno()).st_size > LIMIT:
                fail('log_cleanup_unconfirmed')

    def read(self):
        self.inspect(required=True)
        data = bounded_read(self.path)
        self.inspect(required=True)
        try:
            return data.decode('utf-8')
        except UnicodeError:
            fail('launcher_log_encoding')


def windows_api(ci, process, deadline):
    class BoundedWindows(ci.Windows):
        def scalar(self, hwnd, message, wparam=0, lparam=0):
            self.verify_owned_handles(process.pid, hwnd)
            timeout = deadline.message_timeout_ms()
            result = ctypes.c_size_t()
            if not self.user.SendMessageTimeoutW(hwnd, message, wparam, lparam, 3, timeout,
                                                 ctypes.byref(result)):
                fail('bounded_gui_message_failed')
            deadline.remaining()
            return result.value

        def responsive(self, hwnd):
            self.scalar(hwnd, 0)

        def close(self, hwnd):
            deadline.remaining()
            self.verify_owned_handles(process.pid, hwnd)
            super().close(hwnd)
            deadline.remaining()
    return BoundedWindows()


def process_cpu(process):
    if sys.platform != 'win32' or not getattr(process, '_handle', None):
        fail('owned_process_handle_missing')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    query = kernel.GetProcessTimes
    query.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    query.restype = wintypes.BOOL
    creation, exit_time, system, user = (wintypes.FILETIME() for _ in range(4))
    if not query(int(process._handle), ctypes.byref(creation), ctypes.byref(exit_time),
                 ctypes.byref(system), ctypes.byref(user)):
        fail('process_cpu_query_failed')
    units = lambda value: (value.dwHighDateTime << 32) | value.dwLowDateTime
    return {'user_100ns': units(user), 'kernel_100ns': units(system),
            'scope': 'whole_owned_process_lifetime', 'source': 'retained_popen_handle'}


def validate_process_cpu(record):
    if (not isinstance(record, dict) or set(record) != {'user_100ns', 'kernel_100ns', 'scope', 'source'} or
            not uint64(record['user_100ns']) or not uint64(record['kernel_100ns']) or
            record['scope'] != 'whole_owned_process_lifetime' or record['source'] != 'retained_popen_handle'):
        fail('invalid_process_cpu')


def validate_launcher(text, profile):
    required = ('[launcher] Starting Ru program.', '[startup] menu installed',
                '[startup] initial document ready', '[startup] main window shown',
                '[operation] open started', '[operation] open completed',
                '[launcher] Ru program returned with status 0.')
    if any(text.count(marker) != 1 for marker in required):
        fail('launcher_lifecycle_incomplete')
    if re.search(r'initialization failed|exited before returning|fatal|FAIL:', text, re.I):
        fail('launcher_runtime_error')
    lines = [line for line in text.splitlines() if PREFIX.rstrip() in line]
    if len(lines) != int(profile):
        fail('phase_record_count')
    if profile:
        if not lines[0].startswith(PREFIX):
            fail('phase_record_prefix')
        return json_decode(lines[0][len(PREFIX):])
    return None


def perform_gui(ci, api, process, deadline, source, styles, folds, logs, guard, sleeper):
    def check():
        deadline.remaining()
        if guard.error:
            fail(guard.error)
        logs.inspect()
        if process.poll() is not None:
            fail('premature_gui_exit')
        return api.no_dialog(process.pid)

    hwnd = None
    while hwnd is None:
        windows = check()
        main = [handle for handle, name, visible in windows if name == MAIN_CLASS and visible]
        if len(main) > 1:
            fail('duplicate_main_window')
        if main:
            hwnd = main[0]
            api.verify_owned_handles(process.pid, hwnd)
            break
        deadline.sleep(sleeper)
    # CLI opens exactly the one generated file, no drop/navigation/edit sequence.
    editor = status_handle = None
    tail_requested = False
    snapshots = 0
    identity = None
    next_snapshot = deadline.now()
    while True:
        check()
        if deadline.now() < next_snapshot:
            deadline.sleep(sleeper)
            continue
        snapshots += 1
        if snapshots > 481:
            fail('snapshot_count_overflow')
        api.responsive(hwnd)
        if api.text(hwnd) != source.name + ' · ru_notepad':
            next_snapshot = deadline.now() + SNAPSHOT_SECONDS
            continue
        editor, status_handle = api.editor(hwnd), api.control(hwnd, 11)
        api.verify_owned_handles(process.pid, hwnd, editor, status_handle)
        length, dirty = api.scalar(editor, 2006), bool(api.scalar(editor, 2159))
        if dirty:
            fail('document_dirty')
        status = api.markdown_status(status_handle)
        diagnostic = ci.parse_markdown_diagnostic(status)
        if diagnostic is not None:
            current = tuple(diagnostic[key] for key in ('id', 'gen', 'rev'))
            if identity is not None and current != identity:
                fail('diagnostic_identity_changed')
            identity = current
        if length == FIXTURE_SIZE and not tail_requested:
            # Same ordinary native offscreen-styling request as the existing GUI
            # observer. No SCI_COLOURISE, edit, undo or forced paint.
            api.scalar(editor, 2025, length)
            api.scalar(editor, 2169)
            tail_requested = True
        elif tail_requested and ci.markdown_status_complete(status):
            if (diagnostic is None or diagnostic['pending'] != 0 or diagnostic['phase'] != 4 or
                    diagnostic['feed'] != FIXTURE_SIZE or diagnostic['length'] != FIXTURE_SIZE or
                    diagnostic['bulkCalls'] < 1 or diagnostic['metric_valid'] != 1):
                fail('final_route_incomplete')
            positions = [n for probe in styles for n in range(probe['offset'], probe['offset'] + probe['length'])]
            expected = [probe['style'] for probe in styles for _ in range(probe['length'])]
            actual = [api.scalar(editor, 2010, position) for position in positions]
            actual_folds = [bool(api.scalar(editor, 2223, probe['line']) & 0x2000) for probe in folds]
            if actual != expected or actual_folds != [probe['header'] for probe in folds]:
                fail('bounded_style_fold_mismatch')
            if (api.scalar(editor, 2028) != FIXTURE_SIZE or api.scalar(editor, 4002) != 98 or
                    api.scalar(editor, 2006) != FIXTURE_SIZE or api.scalar(editor, 2159) != 0):
                fail('final_editor_state')
            api.verify_owned_handles(process.pid, hwnd, editor, status_handle)
            verify_fixture(bounded_read(source, FIXTURE_SIZE))
            deadline.remaining()
            return hwnd, {'snapshots': snapshots, 'route': diagnostic,
                          'styles': {'positions': positions, 'expected': expected, 'actual': actual},
                          'folds': actual_folds, 'length': FIXTURE_SIZE, 'dirty': False,
                          'tail_requested': True, 'source_sha256': FIXTURE_SHA256}
        next_snapshot = deadline.now() + SNAPSHOT_SECONDS


def ensure_local_launcher_directory(path):
    if sys.platform != 'win32':
        return
    # Mirror the unchanged launcher's local-drive policy before it could fall
    # back to a user Temp directory. No fallback-directory discovery is allowed.
    value = str(Path(path))
    if not re.match(r'^[A-Za-z]:\\', value):
        fail('launcher_requires_local_drive_path')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetDriveTypeW.argtypes = [wintypes.LPCWSTR]
    kernel.GetDriveTypeW.restype = wintypes.UINT
    if kernel.GetDriveTypeW(value[:3]) not in (2, 3, 6):
        fail('launcher_requires_local_drive')


def copy_runtime(source, destination, expected):
    destination.mkdir(mode=0o700)  # exclusive; no exist_ok
    checked_path(destination, directory=True)
    runtime_inventory(source)
    for name in RUNTIME_NAMES:
        verify_hash(Path(source) / name, expected[name])
        with safe_open(Path(source) / name) as original, open(destination / name, 'xb') as output:
            for block in iter(lambda: original.read(1024 * 1024), b''):
                output.write(block)
        verify_hash(destination / name, expected[name])


def run_owned(variant, directory, source, ci, styles, folds, *,
              spawn=subprocess.Popen, api_factory=windows_api, cpu_query=process_cpu,
              clock=time.monotonic, sleeper=time.sleep, guard_factory=OwnedGuard, environment=None):
    """The only function authorized to create or terminate an application."""
    result = {'variant': variant, 'executed': False, 'passed': False,
              'cleanup_killed': False, 'cleanup_unconfirmed': False}
    process = guard = logs = deadline = None
    try:
        verify_fixture(bounded_read(source, FIXTURE_SIZE))
        runtime_inventory(directory)
        # Starting before Popen is conservative: launch latency consumes budget.
        started = clock()
        deadline = Deadline(started, clock)
        process = spawn([str(directory / 'ru_notepad.exe'), '--markdown-phase-diagnostics', str(source)],
                        cwd=directory, creationflags=0x00000008,
                        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        close_fds=True, env=dict(os.environ if environment is None else environment))
        result['executed'] = True
        result['owned_pid'] = process.pid
        logs = OwnedLog(directory, process.pid)
        guard = guard_factory(process, deadline, logs)
        deadline.remaining()
        api = api_factory(ci, process, deadline)
        hwnd, probes = perform_gui(ci, api, process, deadline, source, styles, folds, logs, guard, sleeper)
        result['probes'] = probes
        api.close(hwnd)
        result['close_posted'] = True
        while process.poll() is None:
            deadline.remaining()
            if guard.error:
                fail(guard.error)
            api.no_dialog(process.pid)
            logs.inspect()
            deadline.sleep(sleeper)
        deadline.remaining()
        result['exit_code'] = process.returncode
        if process.returncode != 0:
            fail('nonzero_exit')
        if guard.error:
            fail(guard.error)
        result['scenario_wall_ms'] = round((deadline.now() - started) * 1000, 6)
        result['process_cpu'] = cpu_query(process)
        validate_process_cpu(result['process_cpu'])
        text = logs.read()
        result['post_exit_route_log_count'] = validate_log_route(ci, text, probes['route'])
        record = validate_launcher(text, variant == 'profile')
        if record is not None:
            validate_phase_record(record, probes['route'])
            result['phase_profile'] = record
        verify_fixture(bounded_read(source, FIXTURE_SIZE))
        # The child has already exited; validation does not extend its lifetime.
        result['passed'] = True
    except Exception as exc:
        result['failure'] = str(exc) if isinstance(exc, StudyError) else 'runner_exception'
    finally:
        if process is not None:
            if guard is not None:
                if process.poll() is None:
                    guard.kill()
                result['cleanup_killed'] = guard.killed
                guard.stop()
            elif process.poll() is None:
                result['cleanup_killed'] = True
                try:
                    process.kill()
                except OSError:
                    pass
            # No second grace period after 120s and no PID-based kill fallback.
            result['cleanup_unconfirmed'] = process.poll() is None
            if result['cleanup_killed'] or result['cleanup_unconfirmed']:
                result['passed'] = False
            if process.poll() is not None:
                result.setdefault('exit_code', process.returncode)
                if 'process_cpu' not in result:
                    try:
                        result['process_cpu'] = cpu_query(process)
                    except Exception:
                        result['process_cpu_unavailable'] = True
            if logs is not None:
                try:
                    logs.inspect()
                except StudyError as exc:
                    if str(exc) == 'output_overflow':
                        result['passed'] = False
                        result['output_overflow'] = True
                        try:
                            logs.cap_after_exit(process)
                            result['retained_log_capped'] = True
                        except Exception:
                            result['retained_output_unconfirmed'] = True
                    else:
                        result['passed'] = False
                        result.setdefault('failure', str(exc))
                        if str(exc) != 'missing_owned_launcher_log':
                            result['retained_output_unconfirmed'] = True
            if deadline is not None:
                result['last_observed_wall_ms'] = round(max(0, clock() - deadline.started) * 1000, 6)
    return result


def uint64(value):
    return type(value) is int and 0 <= value <= 0xffffffffffffffff


def validate_phase_record(record, route):
    fixed = {'schema': 1, 'record': 'markdown_phase_profile', 'diagnostic_only': True,
             'product_acceptance': 'separate_not_claimed', 'timing_kind': 'nested_qpc_wall',
             'cpu_kind': 'outer_timer_thread_only', 'cpu_bounds': 'slightly_enclose_qpc_root',
             'sampling': False, 'whole_process_hotspots': False, 'valid': True,
             'raw_counts_trusted': True}
    integers = {'failure_code', 'foreign_thread_invalid', 'started', 'completion_requested',
                'complete', 'closed', 'depth', 'qpc_frequency', 'root_count', 'no_step_root_count',
                'step_count', 'outermost_root_ticks', 'root_user_100ns', 'root_kernel_100ns',
                'inter_root_gap_ticks', 'inter_root_gap_max_ticks', 'raw_native_other_entries',
                'raw_native_bulk_entries'}
    expected = set(fixed) | integers | {'hot_names', 'hot_totals', 'phases', 'progress'}
    if not isinstance(record, dict) or set(record) != expected:
        fail('phase_schema')
    if any(type(record[key]) is not type(value) or record[key] != value for key, value in fixed.items()):
        fail('phase_claim_or_validity')
    if any(not uint64(record[key]) for key in integers):
        fail('phase_integer')
    if any(record[key] != 0 for key in ('failure_code', 'foreign_thread_invalid', 'depth')) or any(
            record[key] != 1 for key in ('started', 'completion_requested', 'complete', 'closed')):
        fail('phase_not_complete_valid_closed')
    if (record['qpc_frequency'] == 0 or record['outermost_root_ticks'] == 0 or
            record['root_count'] == 0 or record['step_count'] == 0 or
            record['no_step_root_count'] >= record['root_count'] or
            record['step_count'] < record['root_count'] - record['no_step_root_count'] or
            record['inter_root_gap_max_ticks'] > record['inter_root_gap_ticks']):
        fail('phase_root_bounds')
    if record['hot_names'] != ['v_index', 'env_get', 'heap_new', 'v_call']:
        fail('phase_hot_names')
    totals = record['hot_totals']
    phases = record['phases']
    if (not isinstance(totals, list) or len(totals) != 4 or not all(map(uint64, totals)) or
            not isinstance(phases, list) or len(phases) != len(PHASES)):
        fail('phase_counter_schema')
    for phase, name in zip(phases, PHASES):
        if (not isinstance(phase, dict) or set(phase) != {'name', 'entries', 'inclusive_ticks', 'exclusive_ticks', 'hot'} or
                phase['name'] != name or any(not uint64(phase[key]) for key in ('entries', 'inclusive_ticks', 'exclusive_ticks')) or
                not isinstance(phase['hot'], list) or len(phase['hot']) != 4 or not all(map(uint64, phase['hot'])) or
                phase['exclusive_ticks'] > phase['inclusive_ticks']):
            fail('phase_partition_schema')
        if phase['entries'] == 0 and (phase['inclusive_ticks'] or phase['exclusive_ticks'] or any(phase['hot'])):
            fail('phase_unentered_counters')
    if sum(phase['exclusive_ticks'] for phase in phases) != record['outermost_root_ticks']:
        fail('phase_exclusive_partition')
    if any(sum(phase['hot'][index] for phase in phases) != totals[index] for index in range(4)):
        fail('phase_hot_partition')
    by_name = dict(zip(PHASES, phases))
    if (by_name['timer_root']['entries'] < record['root_count'] or
            by_name['timer_root']['inclusive_ticks'] < record['outermost_root_ticks'] or
            any(by_name[name]['entries'] < 1 for name in ('pure_feed', 'bridge_publish', 'bulk_prepare', 'native_bulk')) or
            not 1 <= record['raw_native_bulk_entries'] <= by_name['native_bulk']['entries'] or
            record['raw_native_other_entries'] > by_name['native_other']['entries']):
        fail('phase_required_coverage')
    if (route['pending'] != 0 or route['length'] != FIXTURE_SIZE or route['feed'] != FIXTURE_SIZE or
            route['metric_valid'] != 1 or route['bulkCalls'] != record['raw_native_bulk_entries']):
        fail('phase_final_route_disagreement')
    progress = record['progress']
    progress_keys = {'identity', 'generation', 'revision', 'feed', 'length', 'range_count',
                     'range_index', 'range_offset', 'eof', 'pending'}
    if (not isinstance(progress, dict) or set(progress) != progress_keys or
            any(not uint64(value) for value in progress.values()) or
            any(progress[key] != 0 for key in ('range_count', 'range_index', 'range_offset', 'pending')) or
            progress['eof'] != 1 or progress['feed'] != FIXTURE_SIZE or progress['length'] != FIXTURE_SIZE or
            progress['identity'] != route['id'] or progress['generation'] != route['gen'] or
            progress['revision'] != route['rev']):
        fail('phase_progress_route_disagreement')
    return record


def validate_log_route(ci, text, expected):
    # The current launcher normally has no MDP2 log lines; the final status
    # snapshot is the existing route proof. If log projections are present,
    # validate all, use the last record, and require it to agree after exit.
    records = []
    for line in text.splitlines():
        if '[MDP' in line:
            record = ci.parse_markdown_diagnostic(line)
            if record is None:
                fail('log_route_malformed')
            if (tuple(record[k] for k in ('id', 'gen', 'rev')) !=
                    tuple(expected[k] for k in ('id', 'gen', 'rev'))):
                fail('log_route_identity_changed')
            if records and record['seq'] < records[-1]['seq']:
                fail('log_route_sequence_regressed')
            records.append(record)
    if records:
        keys = ('id', 'gen', 'rev', 'feed', 'length', 'pending', 'phase', 'bulkCalls',
                'bulkLines', 'fallbackBatches', 'directCalls', 'directLines', 'metric_valid')
        if any(records[-1][key] != expected[key] for key in keys):
            fail('log_final_route_disagreement')
    return len(records)


def run_pair(receipt, source_root, release_dir, profile_dir, output, *, ci=None, run=run_owned):
    manifest = verify_manifest(receipt, source_root, release_dir, profile_dir)
    output = Path(os.path.abspath(output))
    checked_path(output.parent, directory=True)
    output.mkdir(mode=0o700)  # fresh private destination only
    checked_path(output, directory=True)
    receipt_summary = {'schema': 1, 'compiler_commit': manifest['compiler_commit'],
                       'receipt_sha256': digest(receipt), 'runtime_sha256': manifest['runtime_sha256'],
                       'artifact_sha256': {k: v['sha256'] for k, v in manifest['artifacts'].items()},
                       'source_manifest_sha256': hashlib.sha256(json_bytes(manifest['source_sha256'])).hexdigest(),
                       'source_file_count': len(manifest['source_sha256'])}
    summary = {'schema': 1, 'diagnostic_only': True, 'product_acceptance': 'separate_not_claimed',
               'timing_kind': 'nested_qpc_wall', 'cpu_kind': 'outer_timer_thread_only',
               'sampling': False, 'whole_process_hotspots': False, 'passed': False,
               'fixture': {'bytes': FIXTURE_SIZE, 'newlines': FIXTURE_NEWLINES,
                           'physical_lines': FIXTURE_NEWLINES + 1, 'sha256': FIXTURE_SHA256},
               'deadline_seconds': HARD_SECONDS, 'runs': [], 'receipt': receipt_summary,
               'measurement': 'Whole scenario wall and whole process CPU are separate from nested phase wall and outer-root thread CPU. Fixed head/tail probes are not whole-content style proof.',
               'output_policy': 'Limits: 64 KiB per process log, summary, and receipt; 256 KiB aggregate diagnostic output. Overflow fails; retention is unconfirmed if exit or path identity cannot be confirmed. Runtime copies and fixed fixture are private inputs. No fallback logs.'}
    try:
        ensure_local_launcher_directory(output)
        write_new(output / 'receipt.json', json_bytes(receipt_summary))
        ci = ci or load_ci(source_root)
        data, styles, folds = fixture_bytes(ci)
        source = output / 'unclosed-fence.md'
        write_new(source, data)
        environment = os.environ.copy()
        for variant, original in (('release', release_dir), ('profile', profile_dir)):
            # A changed source, runtime, generated TU or map blocks the next launch.
            verify_manifest(receipt, source_root, release_dir, profile_dir)
            directory = output / variant
            copy_runtime(original, directory, manifest['runtime_sha256'][variant])
            result = run(variant, directory, source, ci, styles, folds, environment=environment)
            summary['runs'].append(result)
            if not result['passed']:
                break
        if len(summary['runs']) == 2 and all(item['passed'] for item in summary['runs']):
            release, profile = summary['runs']
            if release['scenario_wall_ms'] <= 0:
                fail('zero_release_wall')
            summary['observed_wall_ratio'] = profile['scenario_wall_ms'] / release['scenario_wall_ms']
            summary['overhead_interpretation'] = 'One serial release/profile pair, not a calibrated constant or confidence interval. Instrumentation may change timer admission and root counts; no phase subtraction.'
            summary['passed'] = True
    except Exception as exc:
        summary['failure'] = str(exc) if isinstance(exc, StudyError) else 'setup_failed'
        summary['passed'] = False
    summary['output_retention_confirmed'] = not any(item.get('retained_output_unconfirmed', False) or item.get('cleanup_unconfirmed', False) for item in summary['runs'])
    write_new(output / 'markdown-owned-profile.json', json_bytes(summary))
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source-root', 'release-dir', 'profile-dir', 'receipt', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--validate-only', action='store_true', help='Hash checks only; no output directory or process')
    args = parser.parse_args(argv)
    try:
        if args.validate_only:
            verify_manifest(args.receipt, args.source_root, args.release_dir, args.profile_dir)
            print('MARKDOWN_PHASE_INPUTS_VALID')
            return 0
        if sys.platform != 'win32':
            fail('native_windows_required_no_launch')
        summary = run_pair(args.receipt, args.source_root, args.release_dir, args.profile_dir, args.output)
        print('MARKDOWN_PHASE_STUDY_' + ('PASS' if summary['passed'] else 'FAIL'))
        return 0 if summary['passed'] else 1
    except Exception as exc:
        print('MARKDOWN_PHASE_STUDY_UNAVAILABLE ' +
              (str(exc) if isinstance(exc, StudyError) else 'setup_failed'), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
