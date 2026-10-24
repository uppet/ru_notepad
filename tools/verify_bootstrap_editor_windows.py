#!/usr/bin/env python3
"""Real Windows bootstrap GUI functional gate; never release permission.

Each child has a 60-second functional deadline, NOT a performance acceptance
budget. Existing 30s/120s product budgets are untouched. Linux unit tests of
this module are policy tests, never evidence of native acceptance.
"""
import argparse
import ctypes
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import stat
import struct
import subprocess
import sys
import time
import threading
import uuid
import zlib

from bootstrap_provenance import require, sha, validate_toolchain
from build_bootstrap_release import identity, snapshot, verify_gui_pe, verify_proof, verify_app_baseline, verify_linker_selection, verify_linker_probe

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'ru-notepad-bootstrap-gui-acceptance-v1'
DEADLINE_SECONDS = 60
ARGV = ['', 'space value', 'quote"slash\\tail\\', '汉😀']
CASES = ('pe-resources', 'argv', 'invalid-surrogate', 'dll-editor', 'dll-ru', 'dll-markdown', 'editor-unicode-open-close')
DLLS = ('Scintilla.dll', 'Lexilla.dll', 'RuSyntax.dll')
ABI_ASSERTIONS = {
    'editor': 'PASS: Unicode and mixed EOL exact text',
    'ru': 'PASS: real native insert/delete notifications reached owning bridge',
    'markdown': 'PASS: all native acceptance paths avoid unbounded GETLINE',
}


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def verify_identity(record):
    require(record == identity(record['path']), 'artifact identity changed')
    return Path(record['path'])


def validate_receipts(config):
    receipts = {key: read_json(config[key]) for key in ('app_receipt', 'argv_probe_receipt', 'dll_probe_receipt')}
    app = receipts['app_receipt']
    require(app.get('toolchain_identity_scopes') == {
        'bootstrap': 'existing M4 LLVM14/target/fixedpoint; bootstrap linker identity not recorded or locked',
        'application': 'explicit config-hash toolchain/linker'}, 'toolchain scope missing or overstated')
    entries = ('src/main.ru', 'tests/bootstrap_pipeline/argv_probe.ru', 'tests/bootstrap_pipeline/dll_abi_probe.ru')
    for (key, receipt), entry in zip(receipts.items(), entries):
        require(receipt.get('schema') == 'ru-notepad-bootstrap-llvm-build-v1', 'wrong build receipt')
        require(receipt.get('status') == 'built-not-runtime-accepted-not-publishable'
                and receipt.get('native_acceptance') is False, 'unexpected build status')
        require(receipt.get('entry_source') == entry, 'wrong stage3 fixture entry')
        for field in ('bootstrap', 'source_pins', 'source_sha256', 'tool_paths', 'tool_sha256', 'toolchain_identity_scopes', 'app_baseline', 'target_triple', 'data_layout'):
            require(receipt.get(field) == app.get(field) and bool(receipt.get(field)), 'build receipts differ: '+field)
        verify_gui_pe(verify_identity(receipt['final_binary']))
        for name, pin in receipt['source_pins'].items():
            require(snapshot(Path(pin['path']), pin['commit'], pin['tree']) == receipt['source_sha256'][name], 'source changed')
        for name, digest in receipt['driver_inputs'].items():
            require(sha(Path(name)) == digest, 'build driver changed')
        proof = Path(config[key]).parent/'compile-proof.json'
        require(sha(proof) == receipt['compile_proof_sha256'], 'build proof changed')
        validate_toolchain(receipt['tool_paths'], receipt['tool_sha256'])
        verify_linker_selection(receipt.get('final_linker_selection'), receipt['tool_paths'],
            expected_command=receipt['commands'][-1], triple=receipt['target_triple'])
        verify_linker_probe(receipt.get('linker_probe'), receipt['tool_paths'],
            receipt['target_triple'], Path(config[key]).parent)
        app_root = Path(receipt['source_pins']['app_source']['path'])
        verify_app_baseline(app_root, receipt['app_baseline'], receipt['source_sha256']['app_source'])
        proof_data = read_json(proof)
        require(receipt['standalone_ir_sha256'] == proof_data['standalone_ir_sha256'], 'final link IR differs from proof')
        require(set(receipt['linked_inputs']) == {'application.obj', 'launcher.obj', 'application.res'}, 'incomplete final link inputs')
        for name, record in receipt['linked_inputs'].items():
            require(verify_identity(record).resolve() == (Path(config[key]).parent/name).resolve(), 'final link input outside build directory')
        verification = verify_identity(receipt['bootstrap_verification'])
        require(sha(verification) == receipt['bootstrap']['verification_sha256'], 'bootstrap verification changed')
        compiler = Path(proof_data['compiler']['path'])
        frozen = {str((Path(pin['path'])/name).resolve()): digest
            for key, pin in receipt['source_pins'].items()
            for name, digest in receipt['source_sha256'][key].items()}
        frozen[str(compiler.resolve())] = receipt['bootstrap']['stage3_sha256']
        frozen.update({str(Path(path).resolve()): receipt['tool_sha256'][name] for name, path in receipt['tool_paths'].items()})
        verify_proof(proof_data, source=app_root/entry, compiler=compiler,
            ir=Path(proof_data['artifacts']['standalone_ir']['path']),
            binary=Path(proof_data['artifacts']['binary']['path']),
            triple=receipt['target_triple'], layout=receipt['data_layout'], frozen=frozen, tools=receipt['tool_paths'])
    # Probe sources are reviewed gate inputs, not arbitrary programs bearing a marker.
    source_root = Path(app['source_pins']['app_source']['path'])
    for entry in entries[1:]:
        require(sha(source_root/entry) == sha(ROOT/entry), 'fixture differs from reviewed gate')
    return receipts


def read_log_bytes(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'invalid launcher log')
    resolved = path.resolve()
    with path.open('rb') as stream:
        raw = stream.read(1024*1024 + 1)
    require(len(raw) <= 1024*1024, 'oversized launcher log')
    require(path.is_file() and not path.is_symlink() and path.resolve() == resolved, 'launcher log path changed')
    return raw, {'path': str(resolved), 'sha256': hashlib.sha256(raw).hexdigest(), 'size': len(raw)}


def verify_log_records(results):
    # Re-read only to compare with the original validated bytes, never to
    # replace their identity with a later version of the file.
    for row in results.values():
        if 'log' in row:
            _, current = read_log_bytes(row['log']['path'])
            require(current == row['log'], 'validated launcher log changed')


def successful_log(directory, marker):
    logs = list(directory.glob('ru_notepad-*.log'))
    require(len(logs) == 1, 'exactly one owned launcher log required')
    raw, record = read_log_bytes(logs[0])
    text = raw.decode('utf-8', errors='strict')
    for value in ('[launcher] Starting Ru program.', '[launcher] Ru program returned with status 0.', marker):
        require(text.count(value) == 1, 'missing/duplicate lifecycle marker: '+value)
    if marker.startswith('BOOTSTRAP_DLL_ABI_PASS:'):
        route = marker.split(':', 1)[1]
        totals = re.findall(r'^TOTAL PASS: ([0-9]+)\r?$', text, re.M)
        require(len(totals) == 1 and int(totals[0]) >= 20
                and text.count(ABI_ASSERTIONS[route]) == 1, 'native ABI assertions not executed')
    if marker == '[operation] open completed':
        require(all(text.count(value) == 1 for value in ('[startup] menu installed',
            '[startup] initial document ready', '[startup] main window shown', '[operation] open started')),
            'incomplete GUI startup/open lifecycle')
    require(not re.search(r'FAIL:|initialization failed|exited before returning|fatal', text, re.I), 'diagnostic failure')
    verify_log_records({'current': {'log': record}})
    return record


def dialog_functions(api):
    from ctypes import wintypes as w
    for name, args, result in (
            ('IsWindow', [w.HWND], w.BOOL),
            ('IsChild', [w.HWND, w.HWND], w.BOOL),
            ('IsWindowEnabled', [w.HWND], w.BOOL),
            ('GetParent', [w.HWND], w.HWND),
            ('GetDlgCtrlID', [w.HWND], ctypes.c_int)):
        function = getattr(api.user, name)
        function.argtypes, function.restype = args, result
    return api.user


def owned_dialog_diagnostic(api, pid, hwnd, process_alive):
    """Bounded read-only snapshot of this dialog's owned children, even on failure."""
    from ctypes import wintypes as w
    user = None
    result = {'pid': pid, 'hwnd': hwnd, 'children': [], 'limit': 32,
              'text_limit_utf16': 256, 'text_timeout_ms': 100, 'truncated': False}
    def record(handle):
        owner = w.DWORD()
        thread = user.GetWindowThreadProcessId(handle, ctypes.byref(owner))
        require(thread and owner.value == pid, 'diagnostic HWND no longer owned')
        require(process_alive(), 'owned process exited during diagnostic')
        require(handle == hwnd or user.IsChild(hwnd, handle), 'diagnostic child left owned dialog')
        name = ctypes.create_unicode_buffer(256)
        require(user.GetClassNameW(handle, name, len(name)), 'diagnostic class unavailable')
        row = {'hwnd': handle, 'class': name.value, 'control_id': user.GetDlgCtrlID(handle),
               'parent': int(user.GetParent(handle) or 0), 'visible': bool(user.IsWindowVisible(handle)),
               'enabled': bool(user.IsWindowEnabled(handle))}
        # WM_GETTEXT is a system message; no private-control pointer messages.
        require(user.GetWindowThreadProcessId(handle, ctypes.byref(owner)) and owner.value == pid,
                'diagnostic ownership changed before text query')
        buffer = ctypes.create_unicode_buffer(257)
        copied = ctypes.c_size_t()
        sent = user.SendMessageTimeoutW(handle, 0x000D, len(buffer), ctypes.addressof(buffer),
                                        3, 100, ctypes.byref(copied))
        row.update(text_dispatch_completed=bool(sent), text_result=int(copied.value))
        if sent:
            require(copied.value <= 256, 'diagnostic text result exceeds bound')
            row.update(text=buffer.value, text_may_be_truncated=copied.value == 256)
        require(user.GetWindowThreadProcessId(handle, ctypes.byref(owner)) and owner.value == pid,
                'diagnostic ownership changed after text query')
        require(handle == hwnd or user.IsChild(hwnd, handle), 'diagnostic child moved after text query')
        return row
    try:
        user = dialog_functions(api)
        result['dialog'] = record(hwnd)
        result['getdlgitem_idok_now'] = int(user.GetDlgItem(hwnd, 1) or 0)
        @api.callback_type
        def visit(child, _):
            if len(result['children']) >= 32:
                result['truncated'] = True
                return False
            try:
                result['children'].append(record(child))
            except Exception as exc:
                result['error'] = str(exc)
                return False
            return True
        result['enumeration_result'] = bool(user.EnumChildWindows(hwnd, visit, 0))
    except Exception as exc:
        result['error'] = str(exc)
    result['process_alive_after'] = bool(process_alive())
    return result


def capture_missing_control(api, pid, state, process_alive, elapsed):
    """One read-only snapshot after 1s NULL, inside the unchanged watchdog."""
    if (not state.get('found') or state.get('idok_lookup_result') != 0
            or state.get('request_attempted') or not process_alive()):
        return
    since = state.setdefault('control_missing_since', elapsed)
    if 'early_control_diagnostic' in state or elapsed-since < 1.0:
        return
    # Preserve this observation independently of late cleanup diagnostics.
    state['early_control_diagnostic'] = {
        'observed_elapsed_seconds': elapsed, 'trigger': 'owned-IDOK-still-null-after-1s',
        'snapshot': owned_dialog_diagnostic(api, pid, state['hwnd'], process_alive)}



def owned_ok_control(api, pid, hwnd):
    """Select only the one observed MB_OK button, not a MessageBox return code."""
    user = dialog_functions(api)
    buttons, errors, seen = [], [], []
    @api.callback_type
    def visit(child, _):
        try:
            require(len(seen) < 32, 'startup child enumeration exceeds bound')
            seen.append(child)
            api.verify_owned_handles(pid, hwnd, child)
            name = ctypes.create_unicode_buffer(64)
            require(user.GetClassNameW(child, name, len(name)), 'startup child class unavailable')
            if name.value == 'Button':
                require(user.GetParent(child) == hwnd, 'startup button is not a direct child')
                identifier = user.GetDlgCtrlID(child)
                require(identifier in (1, 2), 'unobserved startup button ID')
                require(user.IsWindowVisible(child) and user.IsWindowEnabled(child),
                        'startup button is not visible and enabled')
                require(api.text(child) == 'OK', 'unexpected startup button caption')
                require(user.GetDlgItem(hwnd, identifier) == child, 'startup button lookup mismatch')
                api.verify_owned_handles(pid, hwnd, child)
                require(user.GetParent(child) == hwnd and user.GetDlgCtrlID(child) == identifier,
                        'startup button changed during selection')
                buttons.append((child, identifier))
        except Exception as exc:
            errors.append(str(exc))
            return False
        return True
    user.EnumChildWindows(hwnd, visit, 0)
    require(not errors, 'startup control enumeration: '+('; '.join(errors)))
    require(len(buttons) <= 1, 'ambiguous startup buttons')
    return buttons[0] if buttons else None


def owned_dialog(api, pid, state):
    """Wait for the unique owned OK control within the existing child deadline."""
    user = dialog_functions(api)
    if state['found']:
        hwnd = state['hwnd']
        if not user.IsWindow(hwnd):
            state['destroyed'] = True
            return
        api.verify_owned_handles(pid, hwnd)
        require([h for h, name, visible in api.windows(pid) if name == '#32770' and visible] == [hwnd],
                'owned startup dialog identity changed')
        require(api.text(hwnd) == 'Ru Notepad startup error', 'startup title changed while waiting')
        require(user.GetParent(hwnd) == state['dialog_parent'], 'startup parent changed while waiting')
        if state['dispatch_completed']:
            return
        require(not state['request_attempted'], 'startup notification already attempted')
    else:
        dialogs = [h for h, name, visible in api.windows(pid) if name == '#32770' and visible]
        require(len(dialogs) <= 1, 'unexpected multiple startup dialogs')
        if not dialogs:
            return
        hwnd = dialogs[0]
        api.verify_owned_handles(pid, hwnd)
        require(api.text(hwnd) == 'Ru Notepad startup error', 'unexpected startup dialog')
        state.update(found=True, hwnd=hwnd, dialog_parent=user.GetParent(hwnd))
    selected = owned_ok_control(api, pid, hwnd)
    state['idok_lookup_result'] = int(user.GetDlgItem(hwnd, 1) or 0)
    if selected is None:
        state['control_wait_polls'] = state.get('control_wait_polls', 0) + 1
        return  # The existing 60s watchdog owns this wait.
    button, identifier = selected
    api.verify_owned_handles(pid, hwnd, button)
    require(api.text(hwnd) == 'Ru Notepad startup error'
            and user.GetParent(hwnd) == state['dialog_parent'], 'startup dialog changed before dispatch')
    require(owned_ok_control(api, pid, hwnd) == selected, 'startup control changed before dispatch')
    api.verify_owned_handles(pid, hwnd, button)
    require(api.text(hwnd) == 'Ru Notepad startup error'
            and user.GetParent(hwnd) == state['dialog_parent']
            and user.GetParent(button) == hwnd and user.GetDlgCtrlID(button) == identifier
            and user.GetDlgItem(hwnd, identifier) == button
            and api.text(button) == 'OK' and user.IsWindowVisible(button)
            and user.IsWindowEnabled(button), 'startup identity changed at dispatch')
    state.update(button=button, button_control_id=identifier, request_attempted=True)
    state['message_result'] = api.scalar(hwnd, 0x0111, identifier, button)
    state['dispatch_completed'] = True
    state['destroyed'] = not bool(user.IsWindow(hwnd))


def loaded_dlls(pid):
    """Read only the child module snapshot; record actual loader paths, not guesses."""
    from ctypes import wintypes as w
    class Module(ctypes.Structure):
        _fields_ = [('dwSize', w.DWORD), ('th32ModuleID', w.DWORD),
            ('th32ProcessID', w.DWORD), ('GlblcntUsage', w.DWORD),
            ('ProccntUsage', w.DWORD), ('modBaseAddr', ctypes.c_void_p),
            ('modBaseSize', w.DWORD), ('hModule', w.HMODULE),
            ('szModule', w.WCHAR * 256), ('szExePath', w.WCHAR * 260)]
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.CreateToolhelp32Snapshot.argtypes = [w.DWORD, w.DWORD]
    k.CreateToolhelp32Snapshot.restype = w.HANDLE
    for name in ('Module32FirstW', 'Module32NextW'):
        getattr(k, name).argtypes = [w.HANDLE, ctypes.POINTER(Module)]
        getattr(k, name).restype = w.BOOL
    k.CloseHandle.argtypes = [w.HANDLE]
    k.CloseHandle.restype = w.BOOL
    handle = k.CreateToolhelp32Snapshot(0x18, pid)
    if handle == ctypes.c_void_p(-1).value:
        # Process exit can race observation; the caller still demands each DLL
        # was positively observed during the owned process lifetime.
        return {}
    found = {}
    try:
        record = Module()
        record.dwSize = ctypes.sizeof(Module)
        more = k.Module32FirstW(handle, ctypes.byref(record))
        while more:
            for name in DLLS:
                if record.szModule.casefold() == name.casefold():
                    found[name] = identity(Path(record.szExePath))
            more = k.Module32NextW(handle, ctypes.byref(record))
    finally:
        k.CloseHandle(handle)
    return found


class ProbeHandshake:
    """One unpredictable, owned kernel event; closed on every returning path."""
    def __init__(self):
        from ctypes import wintypes as w
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.CreateEventW.argtypes = [ctypes.c_void_p, w.BOOL, w.BOOL, w.LPCWSTR]
        self.kernel.CreateEventW.restype = w.HANDLE
        self.kernel.SetEvent.argtypes = [w.HANDLE]
        self.kernel.SetEvent.restype = w.BOOL
        self.kernel.CloseHandle.argtypes = [w.HANDLE]
        self.kernel.CloseHandle.restype = w.BOOL
        self.name = 'Local\\RuNotepadBootstrap-' + uuid.uuid4().hex
        ctypes.set_last_error(0)
        self.handle = self.kernel.CreateEventW(None, True, False, self.name)
        require(self.handle, 'cannot create owned probe handshake')
        if ctypes.get_last_error() == 183:  # Never adopt an existing event.
            self.close()
            raise RuntimeError('probe event already exists')
    def signal(self):
        require(self.kernel.SetEvent(self.handle), 'cannot acknowledge actual DLL identities')
    def close(self):
        return bool(self.kernel.CloseHandle(self.handle))


class FunctionalDeadlineError(ValueError):
    pass


def await_owned_deadline(deadline, cancelled):
    """A timer notification is not proof the original monotonic deadline passed."""
    while not cancelled.is_set():
        now = time.monotonic()
        if now >= deadline:
            return now
        cancelled.wait(deadline-now)
    return None


def run_child(api, binary, arguments, *, marker=None, invalid=False, gui=None, required_dlls=()):
    directory = binary.parent
    require(not list(directory.glob('ru_notepad-*.log')), 'stale launcher logs')
    started = time.monotonic()
    deadline = started + DEADLINE_SECONDS
    cancelled = threading.Event()
    process = None
    watchdog = None
    expired = threading.Event()
    handshake = None
    result = {'passed': False, 'executed': False, 'cleanup_killed': False}
    observation = {'schema': 'ru-notepad-child-observation-v2',
                   'clock': {'started_monotonic': started, 'deadline_monotonic': deadline,
                             'budget_seconds': DEADLINE_SECONDS}, 'deadline_events': [],
                   'first_error': None, 'nondeadline_errors': [], 'cleanup': {'pid': None, 'errors': [],
                   'process_reaped': None, 'exit_code': None, 'windows_remaining': None,
                   'handshake_closed': None, 'watchdog_stopped': None}}
    result['observation'] = observation
    phase = 'prepare'
    observation_lock = threading.RLock()
    def record_error(exc, code='exception'):
        with observation_lock:
            now = time.monotonic()
            row = {'code': code, 'phase': phase, 'observed_monotonic': now, 'elapsed_seconds': now-started,
                   'exception_type': type(exc).__name__, 'message': str(exc)}
            if code != 'deadline':
                observation['nondeadline_errors'].append(row)
            if observation['first_error'] is None:
                observation['first_error'] = row
            result.setdefault('error', str(exc))
    def deadline_event(source, now):
        observation['deadline_events'].append({'source': source, 'observed_monotonic': now,
            'budget_seconds': DEADLINE_SECONDS, 'elapsed_seconds': now-started})
    def cleanup_error(operation, exc):
        observation['cleanup']['errors'].append({'operation': operation,
            'exception_type': type(exc).__name__, 'message': str(exc)})
        result['passed'] = False
        record_error(exc)
    try:
        if required_dlls and not gui:
            handshake = ProbeHandshake()
            arguments = [*arguments, handshake.name]
        process = subprocess.Popen([str(binary), *arguments], cwd=directory, creationflags=0x00000008)
        result.update(executed=True, pid=process.pid)
        observation['cleanup']['pid'] = process.pid
        phase = 'runtime'
        def stop_owned_child():
            now = await_owned_deadline(deadline, cancelled)
            if now is None:
                return
            with observation_lock:
                if cancelled.is_set():
                    return
                deadline_event('watchdog', now)
                record_error(FunctionalDeadlineError('owned watchdog reached 60s functional deadline'), 'deadline')
                expired.set()
            try:
                if process.poll() is None:
                    process.kill()
            except Exception as exc:
                cleanup_error('watchdog-kill', exc)
        watchdog = threading.Timer(max(0, deadline-time.monotonic()), stop_owned_child)
        watchdog.daemon = True
        watchdog.start()
        dialog_state = dict(found=False, request_attempted=False, dispatch_completed=False, destroyed=False, process_exited=False)
        if invalid:
            result['owned_startup_dialog'] = dialog_state
        closed = False
        observed = {}
        while process.poll() is None:
            poll_time = time.monotonic()
            if poll_time >= deadline:
                deadline_event('poll-loop', poll_time)
                raise FunctionalDeadlineError('60s functional smoke deadline exceeded (not performance)')
            if required_dlls:
                for name, record in loaded_dlls(process.pid).items():
                    require(Path(record['path']).resolve() == (directory/name).resolve(), 'DLL loaded from outside owned snapshot')
                    require(record == identity(directory/name), 'loaded DLL differs from snapshot')
                    observed[name] = record
                if handshake and set(required_dlls) <= set(observed):
                    handshake.signal()
            if invalid:
                owned_dialog(api, process.pid, dialog_state)
                capture_missing_control(api, process.pid, dialog_state, lambda: process.poll() is None, poll_time-started)
            else:
                windows = api.no_dialog(process.pid)
                if gui and not closed:
                    handles = [h for h, name, visible in windows if name == gui['class'] and visible]
                    require(len(handles) <= 1, 'multiple application windows')
                    if handles:
                        hwnd = handles[0]
                        api.verify_owned_handles(process.pid, hwnd)
                        if (set(required_dlls) <= set(observed) and gui['filename'] in api.text(hwnd)
                                and api.editor_bytes(hwnd) == gui['bytes']):
                            api.responsive(hwnd)
                            api.close(hwnd)
                            closed = True
            time.sleep(0.05)
        if expired.is_set():
            raise FunctionalDeadlineError('owned watchdog reached 60s functional deadline')
        phase = 'acceptance'
        result['exit_code'] = process.returncode
        if invalid:
            dialog_state['process_exited'] = True
            if dialog_state['found']:
                dialog_state['destroyed'] = not bool(dialog_functions(api).IsWindow(dialog_state['hwnd']))
            require(process.returncode != 0 and all(dialog_state[key] for key in
                    ('found', 'request_attempted', 'dispatch_completed', 'destroyed', 'process_exited')),
                    'invalid UTF16 rejection/dialog lifecycle not confirmed')
            require(not list(directory.glob('ru_notepad-*.log')), 'invalid UTF16 reached diagnostic/Ru side effect')
        else:
            require(process.returncode == 0, 'child returned failure')
            if gui:
                require(closed, 'Unicode file not observed in owned editor or ordinary close missing')
            result['log'] = successful_log(directory, marker)
        require(set(required_dlls) <= set(observed), 'required actual DLL load not observed')
        result['loaded_dlls'] = observed
        require(not api.windows(process.pid), 'owned windows remain after exit')
        result['passed'] = True
    except Exception as exc:
        record_error(exc, 'deadline' if isinstance(exc, FunctionalDeadlineError) else 'exception')
        if invalid and process is not None:
            state = result.get('owned_startup_dialog', {})
            state['process_returncode_before_cleanup'] = process.poll()
            if state.get('found') and state.get('hwnd'):
                state['failure_diagnostic'] = owned_dialog_diagnostic(api, process.pid, state['hwnd'],
                    lambda: process.poll() is None)
            state['process_returncode_after_diagnostic'] = process.poll()
    finally:
        phase = 'cleanup'
        cancelled.set()
        cleanup = observation['cleanup']
        if watchdog is not None:
            try:
                watchdog.cancel()
                watchdog.join()
                cleanup['watchdog_stopped'] = not watchdog.is_alive()
                require(cleanup['watchdog_stopped'], 'owned watchdog stop not confirmed')
            except Exception as exc:
                cleanup_error('watchdog-stop', exc)
        else:
            cleanup['watchdog_stopped'] = True
        if handshake is not None:
            try:
                cleanup['handshake_closed'] = handshake.close() is True
                require(cleanup['handshake_closed'], 'owned handshake close not confirmed')
            except Exception as exc:
                cleanup_error('handshake-close', exc)
        else:
            cleanup['handshake_closed'] = True
        if expired.is_set():
            result.update(passed=False, cleanup_killed=True)
            record_error(FunctionalDeadlineError('owned watchdog reached 60s functional deadline'), 'deadline')
        if process is not None:
            try:
                if process.poll() is None:
                    process.kill()  # Only this owned Popen handle.
                    result.update(cleanup_killed=True, passed=False)
                exit_code = process.wait(timeout=5)
                cleanup['exit_code'] = exit_code
                cleanup['process_reaped'] = isinstance(exit_code, int) and process.poll() is not None
                require(cleanup['process_reaped'], 'owned process reap not confirmed')
            except Exception as exc:
                cleanup_error('process-reap', exc)
            try:
                windows = api.windows(process.pid)
                cleanup['windows_remaining'] = [int(row[0]) for row in windows]
                require(not windows, 'owned windows remain after cleanup')
            except Exception as exc:
                cleanup_error('windows-gone', exc)
        finished = time.monotonic()
        observation['clock']['finished_monotonic'] = finished
        result['seconds'] = finished - started
        if finished > deadline:
            deadline_event('elapsed-postcheck', finished)
            result['passed'] = False
            record_error(FunctionalDeadlineError('60s functional smoke deadline exceeded (not performance)'), 'deadline')
    return result


class ResourceEvidenceError(ValueError):
    def __init__(self, message, diagnostic):
        super().__init__(message)
        self.diagnostic = diagnostic


def icon_resource_diagnostic(icon, group, image, languages):
    """Bounded descriptions only; never canonicalize bytes or grant acceptance."""
    require(len(icon) <= 1024*1024 and len(group) <= 1024*1024, 'resource diagnostic size cap')
    result = {'scope': 'diagnostic-only; original exact resource gates unchanged',
              'source_ico_sha256': hashlib.sha256(icon).hexdigest(), 'source_ico_size': len(icon),
              'group_sha256': hashlib.sha256(group).hexdigest(), 'group_size': len(group),
              'group_languages': languages(14, 1), 'entries': []}
    if len(icon) < 6 or len(group) < 6:
        result['description_error'] = 'truncated directory header'
        return result
    source_count, group_count = struct.unpack_from('<H', icon, 4)[0], struct.unpack_from('<H', group, 4)[0]
    result.update(source_header_hex=icon[:6].hex(), group_header_hex=group[:6].hex(),
                  source_count=source_count, group_count=group_count)
    require(max(source_count, group_count) <= 64, 'resource diagnostic entry cap')
    for index in range(max(source_count, group_count)):
        entry = {'index': index}
        i, g = 6+16*index, 6+14*index
        if index < source_count and i+16 <= len(icon):
            values = struct.unpack_from('<BBBBHHII', icon, i)
            source = dict(zip(('width_raw','height_raw','colors','reserved','planes','bit_count','byte_length','offset'), values))
            source.update(width=values[0] or 256,height=values[1] or 256,raw_hex=icon[i:i+16].hex())
            end = values[7]+values[6]
            if end <= len(icon):
                payload=icon[values[7]:end]
                source.update(payload_sha256=hashlib.sha256(payload).hexdigest(),payload_size=len(payload),prefix_hex=payload[:32].hex())
            else: source['payload_error']='outside source ICO'
            entry['source']=source
        if index < group_count and g+14 <= len(group):
            values=struct.unpack_from('<BBBBHHIH', group, g)
            actual=dict(zip(('width_raw','height_raw','colors','reserved','planes','bit_count','byte_length','resource_id'),values))
            actual.update(width=values[0] or 256,height=values[1] or 256,raw_hex=group[g:g+14].hex(),languages=languages(3,values[7]))
            try:
                payload=image(values[7])
                actual.update(payload_sha256=hashlib.sha256(payload).hexdigest(),payload_size=len(payload),prefix_hex=payload[:32].hex())
            except Exception as exc:
                actual['payload_error']=str(exc)[:500]
            entry['group']=actual
        result['entries'].append(entry)
    return result


def verify_png_icon_entry(source_entry, group_entry, source_image, resource_image):
    """Only the observed SDK PNG planes 0->1 canonicalization is permitted.

    This identifies the pinned RGBA8 PNG header, not a general PNG decoder.
    The whole image must still equal the exact trusted source bytes and hash.
    """
    require(len(source_entry)==16 and len(group_entry)==14, 'truncated icon entry')
    require(len(source_image)>=33 and source_image[:8]==b'\x89PNG\r\n\x1a\n'
            and source_image[8:16]==b'\x00\x00\x00\x0dIHDR', 'unsupported non-PNG icon')
    width,height=struct.unpack_from('>II',source_image,16)
    require((width,height)==(source_entry[0] or 256,source_entry[1] or 256)
            and source_image[24:29]==bytes((8,6,0,0,0)), 'unsupported PNG dimensions or RGBA8 header')
    require(struct.unpack_from('>I',source_image,29)[0]==zlib.crc32(source_image[12:29]), 'PNG IHDR CRC differs')
    source_planes,source_bits=struct.unpack_from('<HH',source_entry,4)
    output_planes=struct.unpack_from('<H',group_entry,4)[0]
    require(source_planes in (0,1) and output_planes==1 and source_bits==32, 'icon metadata differs: unsupported planes/bitcount')
    expected=bytearray(source_entry[:12])
    expected[4:6]=b'\x01\x00'
    require(group_entry[:12]==expected, 'icon metadata differs')
    require(len(source_image)==struct.unpack_from('<I',source_entry,8)[0]
            and resource_image==source_image
            and hashlib.sha256(resource_image).digest()==hashlib.sha256(source_image).digest(), 'icon image differs')


def verify_icon_languages_and_members(diagnostic, ids):
    require(len(ids)==len(diagnostic['entries']) and all(number>0 for number in ids)
            and len(ids)==len(set(ids)), 'icon members duplicate or invalid')
    records=[diagnostic['group_languages']]+[entry['group']['languages'] for entry in diagnostic['entries']]
    require(all(record.get('available_langids')==[1033] and record.get('selected_langid')==1033 for record in records),
            'icon resource language differs or unknown')


def resource_snapshot_stable(diagnostic, path, icon_path):
    for key, file in [('pe',path),('source_ico',icon_path)]:
        try:
            current=identity(file)
            diagnostic[key+'_after']=current
            require(current == diagnostic[key], 'resource '+key+' identity changed')
        except Exception:
            diagnostic['identity_stable']=False
            raise
    diagnostic['identity_stable']=True


def verify_resources(path, app):
    """Read resource bytes from final PE (datafile mapping never executes DllMain)."""
    pe_identity=identity(path)
    verify_gui_pe(path)
    icon_path=app/'assets/app-icon.ico'
    with icon_path.open('rb') as stream:
        icon=stream.read(1024*1024+1)
    require(len(icon)<=1024*1024,'source icon diagnostic size cap')
    diagnostic={'schema':'ru-notepad-resource-diagnostic-v1', 'scope':'diagnostic-only-not-runtime-acceptance',
                'pe':pe_identity, 'source_ico':{'path':str(icon_path.resolve()),'sha256':hashlib.sha256(icon).hexdigest(),'size':len(icon)}}
    from ctypes import wintypes as w
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.LoadLibraryExW.argtypes = [w.LPCWSTR, w.HANDLE, w.DWORD]
    kernel.LoadLibraryExW.restype = w.HMODULE
    kernel.FindResourceW.argtypes = [w.HMODULE, ctypes.c_void_p, ctypes.c_void_p]
    kernel.FindResourceW.restype = w.HRSRC
    kernel.SizeofResource.argtypes = [w.HMODULE, w.HRSRC]
    kernel.SizeofResource.restype = w.DWORD
    kernel.LoadResource.argtypes = [w.HMODULE, w.HRSRC]
    kernel.LoadResource.restype = w.HGLOBAL
    kernel.LockResource.argtypes = [w.HGLOBAL]
    kernel.LockResource.restype = ctypes.c_void_p
    kernel.FreeLibrary.argtypes = [w.HMODULE]
    kernel.FreeLibrary.restype = w.BOOL
    module = kernel.LoadLibraryExW(str(path), None, 0x22)
    require(module, 'cannot map final resources')
    cache={}
    def resource(kind, name):
        key=(kind,name)
        if key in cache: return cache[key]
        found = kernel.FindResourceW(module, name, kind)
        require(found, 'missing PE resource')
        size = kernel.SizeofResource(module, found)
        pointer = kernel.LockResource(kernel.LoadResource(module, found))
        require(pointer and 0 < size <= 1024*1024, 'invalid resource bytes')
        require(sum(map(len,cache.values()))+size <= 16*1024*1024, 'resource snapshot aggregate cap')
        cache[key]=ctypes.string_at(pointer, size)
        return cache[key]
    def languages(kind,name):
        # FindResourceW selects a language implicitly. Only a unique enumerated
        # language identifies that selection; otherwise report it as unknown.
        result={'available_langids':None,'selected_langid':None}
        try:
            callback_type=ctypes.WINFUNCTYPE(w.BOOL,w.HMODULE,ctypes.c_void_p,ctypes.c_void_p,w.WORD,ctypes.c_ssize_t)
            values=[]
            def collect(module,kind,name,lang,param):
                if len(values)>=32: return False
                values.append(int(lang)); return True
            callback=callback_type(collect)
            function=kernel.EnumResourceLanguagesW
            function.argtypes=[w.HMODULE,ctypes.c_void_p,ctypes.c_void_p,callback_type,ctypes.c_ssize_t]
            function.restype=w.BOOL
            ok=function(module,kind,name,callback,0)
            if ok and len(values)==len(set(values)) and values:
                result.update(available_langids=sorted(values),selected_langid=values[0] if len(values)==1 else None)
                if len(values)>1: result['selection_reason']='multiple languages; FindResourceW selection not exposed'
            else: result['unknown_reason']='enumeration failed, empty, duplicate, or bounded out'
        except Exception as exc:
            result['unknown_reason']=str(exc)[:300]
        return result
    try:
        group=resource(14,1)
        diagnostic['icon']=icon_resource_diagnostic(icon,group,lambda name:resource(3,name),languages)
        require(resource(24, 1) == (app/'packaging/app.manifest').read_bytes(), 'manifest differs from source')
        version = resource(16, 1)
        fixed = struct.pack('<13I', 0xFEEF04BD, 0x10000, 1, 8 << 16, 1, 8 << 16,
                            0x3f, 2, 0x40004, 1, 0, 0, 0)
        require(version.count(fixed) == 1 and all(value.encode('utf-16-le') in version
            for value in ('FileDescription', 'ru_notepad preview', 'FileVersion', '0.1.8-preview',
                          'InternalName', 'OriginalFilename', 'ru_notepad.exe', 'ProductName',
                          'ProductVersion', '040904B0')), 'incorrect version resource')
        group = resource(14, 1)  # Same cached bytes described above.
        require(len(group) >= 6 and group[:6] == icon[:6], 'icon group differs')
        count = struct.unpack_from('<H', group, 4)[0]
        require(count > 0 and len(group) == 6+14*count and len(icon) >= 6+16*count, 'truncated icon group')
        ids=[struct.unpack_from('<H',group,6+14*index+12)[0] for index in range(count)]
        verify_icon_languages_and_members(diagnostic['icon'],ids)
        for index in range(count):
            g, i = 6+14*index, 6+16*index
            size, offset = struct.unpack_from('<II', icon, i+8)
            require(offset+size <= len(icon), 'icon image differs')
            verify_png_icon_entry(icon[i:i+16],group[g:g+14],icon[offset:offset+size],resource(3,ids[index]))
    except Exception as exc:
        try: resource_snapshot_stable(diagnostic,path,icon_path)
        except Exception as changed: diagnostic['identity_error']=str(changed)[:500]
        raise ResourceEvidenceError(str(exc),diagnostic) from exc
    finally:
        kernel.FreeLibrary(module)
    try: resource_snapshot_stable(diagnostic,path,icon_path)
    except Exception as exc: raise ResourceEvidenceError(str(exc),diagnostic) from exc
    return {'passed': True, 'executed': True, 'cleanup_killed': False, 'resource_diagnostics':diagnostic}


def load_windows_harness(app):
    spec = importlib.util.spec_from_file_location('_bootstrap_windows_ci', app/'tools/windows_ci.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def all_passed(results):
    return (set(results) == set(CASES) and all(r.get('passed') is True and r.get('executed') is True
            and r.get('cleanup_killed') is False and not r.get('skipped') and not r.get('error') for r in results.values()))


def verify(config):
    require(sys.platform == 'win32' and platform.machine() in ('AMD64', 'x86_64'), 'real Windows x64 required; portable tests are not acceptance')
    from verify_recent_files_windows import isolated_recent_settings
    with isolated_recent_settings():
        return _verify_isolated(config)


def _verify_isolated(config):
    require(sys.platform == 'win32' and platform.machine() in ('AMD64', 'x86_64'), 'real Windows x64 required; portable tests are not acceptance')
    require(ctypes.sizeof(ctypes.c_void_p) == 8, '64-bit Python required')
    receipts = validate_receipts(config)
    from prepare_bootstrap_dependencies import validate_receipt
    dependencies = validate_receipt(Path(config['dependencies_receipt']))
    app_receipt = receipts['app_receipt']
    require(dependencies['app_source'] == app_receipt['source_pins']['app_source']
            and dependencies['source_sha256'] == app_receipt['source_sha256']['app_source']
            and dependencies['app_baseline'] == app_receipt['app_baseline'], 'DLLs and app are not same-source')
    app = Path(app_receipt['source_pins']['app_source']['path'])
    require(ROOT.resolve() == app.resolve(), 'runner must execute from pinned application checkout')
    ci = load_windows_harness(app)
    api = ci.Windows()  # Also rejects Wine.
    owned = Path(config['owned_root']).absolute()
    require(not owned.exists() and not any(p.is_symlink() for p in owned.parents), 'owned_root must be fresh and unlinked')
    require(not any(owned.resolve().is_relative_to(Path(pin['path']).resolve())
            for pin in app_receipt['source_pins'].values()), 'owned runtime cannot modify source trees')
    # The launcher must log beside our EXE, never fall back to a user Temp scan.
    require(re.fullmatch(r'[A-Za-z]:', owned.drive) is not None
            and all(part and part[-1] not in '. ' for part in owned.parts[1:]), 'owned runtime requires a local ordinary Windows path')
    from ctypes import wintypes as w
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetDriveTypeW.argtypes = [w.LPCWSTR]
    kernel.GetDriveTypeW.restype = w.UINT
    require(kernel.GetDriveTypeW(owned.anchor) == 3, 'owned runtime must be on a fixed local drive')
    for parent in owned.parents:
        if parent.exists():
            require(not (parent.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT), 'reparse runtime parent forbidden')
    owned.mkdir(parents=True, exist_ok=False)
    inputs = {key: identity(Path(config[key])) for key in ('app_receipt', 'argv_probe_receipt', 'dll_probe_receipt', 'dependencies_receipt')}
    for name in ('verify_bootstrap_editor_windows.py', 'bootstrap_provenance.py', 'build_bootstrap_release.py', 'prepare_bootstrap_dependencies.py'):
        inputs[name] = identity(ROOT/'tools'/name)
    inputs['python'] = identity(Path(sys.executable))
    copies = []
    def stage(name, receipt):
        directory = owned/name
        directory.mkdir()
        for source in [verify_identity(receipt['final_binary']), *[verify_identity(dependencies['binaries'][dll]) for dll in (*DLLS, 'RuSyntaxWrongAbi.dll')]]:
            destination = directory/('ru_notepad.exe' if source == Path(receipt['final_binary']['path']) else source.name)
            shutil.copyfile(source, destination)
            require(sha(destination) == sha(source), 'runtime copy mismatch')
            copies.append(identity(destination))
        return directory/'ru_notepad.exe'
    results = {}
    final = verify_identity(receipts['app_receipt']['final_binary'])
    results['pe-resources'] = verify_resources(final, app)
    results['argv'] = run_child(api, stage('argv', receipts['argv_probe_receipt']), ARGV, marker='BOOTSTRAP_ARGV_PASS')
    results['invalid-surrogate'] = run_child(api, stage('surrogate', receipts['argv_probe_receipt']), ['\ud800'], invalid=True)
    for route in ('editor', 'ru', 'markdown'):
        results['dll-'+route] = run_child(api, stage('dll-'+route, receipts['dll_probe_receipt']), [route], marker='BOOTSTRAP_DLL_ABI_PASS:'+route, required_dlls=DLLS)
    binary = stage('editor', receipts['app_receipt'])
    fixture = binary.parent/'汉 字😀.txt'
    raw = 'bootstrap 汉😀\r\n'.encode('utf-8')
    fixture.write_bytes(raw)
    results['editor-unicode-open-close'] = run_child(api, binary, [str(fixture)], marker='[operation] open completed', gui={'class': ci.MAIN_CLASS, 'filename': fixture.name, 'bytes': raw}, required_dlls=('Scintilla.dll',))
    require(fixture.read_bytes() == raw, 'editor modified clean fixture')
    validate_receipts(config)
    validate_receipt(Path(config['dependencies_receipt']))
    for record in [*inputs.values(), *copies]:
        verify_identity(record)
    verify_log_records(results)
    return {'schema': SCHEMA, 'platform': sys.platform, 'status': 'passed' if all_passed(results) else 'failed',
        'functional_smoke_only': True, 'deadline_seconds_per_child': DEADLINE_SECONDS,
        'toolchain_identity_scopes': app_receipt['toolchain_identity_scopes'],
        'performance_acceptance': False, 'release_permission': False, 'runtime_zip_upload': False,
        'inputs': inputs, 'runtime_copies': copies, 'results': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    require(not args.output.exists(), 'refuse overwrite evidence')
    try:
        result = verify(read_json(args.config))
        verify_log_records(result['results'])  # Last check before publishing the receipt.
    except Exception as exc:
        result = {'schema': SCHEMA, 'status': 'failed', 'release_permission': False, 'error': str(exc)}
        if isinstance(exc,ResourceEvidenceError): result['resource_diagnostics']=exc.diagnostic
    with args.output.open('x', encoding='utf-8') as output:
        json.dump(result, output, indent=2, ensure_ascii=True)
        output.write('\n')
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
