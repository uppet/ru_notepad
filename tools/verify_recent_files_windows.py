#!/usr/bin/env python3
"""Actual same-binary GUI recent-file acceptance; synthetic files/HKCU only.

This supplements (never substitutes for) the product's existing GUI/native gates.
No global input, user's documents or Preferences value is modified.
"""
from __future__ import annotations
import ctypes
from contextlib import contextmanager
from ctypes import wintypes
import json
import os
from pathlib import Path
import shutil
import time
import uuid
from unittest.mock import patch

import windows_ci as ci

CHECKS = (
    'successful_open_only', 'ten_item_bound', 'unicode_space_ampersand_menu',
    'case_insensitive_dedup', 'ordinal_distinguishes_sharp_s', 'duplicate_tab_preserved', 'failed_open_not_promoted',
    'missing_keeps_dirty_text', 'cancel_not_promoted', 'restart_restores_order',
    'recent_command_opens_exact_file', 'clear_persisted', 'restart_after_clear_empty',
    'persistence_error_keeps_document', 'synthetic_sources_unchanged',
    'isolated_registry_cleaned',
)
PHASES = ('initial', 'restart', 'cleared', 'persistence-failure')


@contextmanager
def isolated_recent_settings():
    """Limit every child app's recent history to one fresh product test key."""
    import winreg
    token = 'preview_' + uuid.uuid4().hex
    path = 'Software\\ru_notepad\\RecentTests\\' + token
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path):
            raise RuntimeError('Refusing existing recent-file test namespace')
    except FileNotFoundError:
        pass
    # The random token is generated here, never accepted from caller input.
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE):
        pass
    try:
        with patch.dict(os.environ, {'RU_NOTEPAD_RECENT_TEST_KEY': token}):
            yield token
    finally:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path):
                raise RuntimeError('Recent-file test namespace survived cleanup')
        except FileNotFoundError:
            pass


def validate_recent_files_result(record, runtime_hashes):
    if not isinstance(record, dict) or record.get('name') != 'main-gui-recent-files':
        raise ValueError('Missing recent-file product evidence')
    if record.get('passed') is not True or record.get('executed') is not True:
        raise ValueError('Recent-file GUI did not execute and pass')
    if record.get('cleanup_killed') is not False or record.get('exit_code') != 0:
        raise ValueError('Recent-file GUI lacks normal process termination')
    if record.get('fixture_binary_sha256') != runtime_hashes:
        raise ValueError('Recent-file GUI binary identity differs from package')
    checks = record.get('checks')
    if not isinstance(checks, dict) or set(checks) != set(CHECKS) or any(v is not True for v in checks.values()):
        raise ValueError('Recent-file checks are incomplete or non-boolean')
    phases = record.get('phases')
    if not isinstance(phases, list) or len(phases) != len(PHASES):
        raise ValueError('Recent-file restart evidence is incomplete')
    for expected, phase in zip(PHASES, phases):
        if (phase.get('phase') != expected or phase.get('passed') is not True or
                phase.get('executed') is not True or phase.get('cleanup_killed') is not False or
                phase.get('exit_code') != 0 or phase.get('fixture_binary_sha256') != runtime_hashes):
            raise ValueError('Recent-file phase lacks exact-binary normal lifecycle')
    return True


def _menu(api, hwnd):
    u = api.user
    u.GetMenu.argtypes = [wintypes.HWND]
    u.GetMenu.restype = wintypes.HMENU
    u.GetSubMenu.argtypes = [wintypes.HMENU, ctypes.c_int]
    u.GetSubMenu.restype = wintypes.HMENU
    u.GetMenuStringW.argtypes = [wintypes.HMENU, wintypes.UINT, wintypes.LPWSTR, ctypes.c_int, wintypes.UINT]
    u.GetMenuStringW.restype = ctypes.c_int
    menu = u.GetSubMenu(u.GetMenu(hwnd), 0)
    if not menu:
        raise RuntimeError('Actual File menu is absent')
    result = []
    for command in range(1200, 1210):
        text = ctypes.create_unicode_buffer(256)
        length = u.GetMenuStringW(menu, command, text, len(text), 0)
        if length:
            if length >= 255:
                raise RuntimeError('Recent-file menu inspection exceeded bound')
            result.append(text.value)
    return result


def _label(path):
    text = str(path)
    if len(text) > 100:
        text = '…' + text[-100:]
    return ''.join('&&' if c == '&' else ' ' if ord(c) < 32 or ord(c) == 127 else c for c in text)


def _error_dialog(api, process, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError('GUI exited while awaiting deliberate missing-file error')
        dialogs = [h for h, cls, visible in api.windows(process.pid) if cls == '#32770' and visible]
        if len(dialogs) == 1:
            dialog = dialogs[0]
            buttons = []

            @api.callback_type
            def visit(child, _):
                name = ctypes.create_unicode_buffer(64)
                api.user.GetClassNameW(child, name, len(name))
                if name.value == 'Button' and api.user.IsWindowVisible(child):
                    buttons.append(child)
                return True

            if not api.user.EnumChildWindows(dialog, visit, 0) or len(buttons) != 1:
                raise RuntimeError('Missing-file dialog does not have one actual acknowledgement button')
            button = buttons[0]
            api.user.GetDlgCtrlID.argtypes = [wintypes.HWND]
            api.user.GetDlgCtrlID.restype = ctypes.c_int
            identifier = api.user.GetDlgCtrlID(button)
            if identifier not in (1, 2) or not api.text(button):
                raise RuntimeError('Missing-file acknowledgement control is not a standard labelled button')
            api.verify_owned_handles(process.pid, dialog, button)
            # Click the discovered real control, not a guessed WM_COMMAND ID.
            if not api.user.PostMessageW(button, 0x00F5, 0, 0):  # BM_CLICK
                raise ctypes.WinError(ctypes.get_last_error())
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError('GUI exited before the error dialog was dismissed')
                remaining = [h for h, cls, visible in api.windows(process.pid)
                             if cls == '#32770' and visible]
                if not remaining:
                    return
                if remaining != [dialog]:
                    raise RuntimeError('Unexpected dialog appeared during acknowledgement')
                time.sleep(.01)
            raise RuntimeError('Missing-file acknowledgement did not dismiss its dialog')
        if len(dialogs) > 1:
            raise RuntimeError('Unexpected second missing-file dialog')
        time.sleep(.01)
    raise RuntimeError('Missing recent-file attempt did not report an error')


def run_recent_files(api, binary_dir, fixtures, evidence):
    import winreg
    binary_dir, fixtures, evidence = map(Path, (binary_dir, fixtures, evidence))
    name = 'preview_' + uuid.uuid4().hex
    registry_path = 'Software\\ru_notepad\\RecentTests\\' + name
    root = fixtures / 'recent-files-gui'
    root.mkdir()
    inputs = root / 'Unicode 空格 & 😀'
    inputs.mkdir()
    paths = [inputs / f'历史 {n:02d} & 文.txt' for n in range(12)]
    paths[-2:] = [inputs / 'straße & 文.txt', inputs / 'strasse & 文.txt']
    for n, path in enumerate(paths):
        path.write_bytes(f'original {n} 中文😀\r\n'.encode('utf-8'))
    large = inputs / 'cancelled.txt'
    ci.write_gui_cancel_fixture(large)
    originals = {str(p): ci.sha(p) for p in paths + [large]}
    expected_hashes = {n: ci.sha(binary_dir / n) for n in ci.portable.RUNTIME_NAMES}
    result = {'name': 'main-gui-recent-files', 'passed': False, 'executed': False,
              'cleanup_killed': False, 'exit_code': None, 'checks': {}, 'phases': [],
              'fixture_binary_sha256': expected_hashes}
    checks = result['checks']
    recent = list(reversed(paths[-10:]))

    def stored():
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_path, 0, winreg.KEY_READ) as key:
            value, kind = winreg.QueryValueEx(key, 'RecentFilesV1')
        if kind != winreg.REG_SZ or not value.startswith('RU_RECENT_1\n'):
            raise RuntimeError('Recent-file persistence is not the versioned string snapshot')
        lines = value.split('\n')
        if lines[-1] != '' or (len(lines)-2) % 2:
            raise RuntimeError('Recent-file persistence contains partial pairs')
        return [(lines[i+1], lines[i]) for i in range(1, len(lines)-1, 2)]

    def phase(label, exercise, arguments=(), env_key=name):
        isolated = root / label
        isolated.mkdir()
        for filename, digest in expected_hashes.items():
            shutil.copyfile(binary_dir / filename, isolated / filename)
            if ci.sha(isolated / filename) != digest:
                raise RuntimeError('Recent-file phase binary identity changed')
        with patch.dict(os.environ, {'RU_NOTEPAD_RECENT_TEST_KEY': env_key}):
            item = ci.run_gui(api, isolated, evidence, name='main-gui-recent-' + label,
                              arguments=arguments, exercise=exercise, log_prefix='recent-' + label)
        item['phase'] = label
        item['fixture_binary_sha256'] = dict(expected_hashes)
        result['phases'].append(item)
        result['executed'] = result['executed'] or item['executed']
        result['cleanup_killed'] |= item['cleanup_killed']
        if not item['passed']:
            raise RuntimeError(f'Recent-file {label} failed: {item.get("error")}')
        api.release_drops()
        return isolated

    def initial(process, hwnd):
        tabs = lambda: api.scalar(api.control(hwnd, 10), 0x1304)
        ci.wait_gui(api, process, lambda: tabs() == 13 and len(_menu(api, hwnd)) == 10,
                    'Initial successful files did not reach recent-file menu')
        if _menu(api, hwnd) != list(map(_label, recent)):
            raise RuntimeError('Recent-file menu order/Unicode/escaping is incorrect')
        if [x[0] for x in stored()] != list(map(str, recent)):
            raise RuntimeError('Successful file order was not committed')
        checks.update(successful_open_only=True, ten_item_bound=True, unicode_space_ampersand_menu=True,
                      ordinal_distinguishes_sharp_s=True)
        duplicate = Path(str(paths[3]).upper())
        api.drop(api.editor(hwnd), [duplicate])
        ci.wait_gui(api, process, lambda: _menu(api, hwnd)[0] == _label(duplicate),
                    'Case-insensitive duplicate was not promoted')
        recent[:] = [duplicate] + [p for p in recent if p != paths[3]]
        if len(_menu(api, hwnd)) != 10 or tabs() != 13:
            raise RuntimeError('Duplicate opening duplicated history or tabs')
        checks.update(case_insensitive_dedup=True, duplicate_tab_preserved=True)
        before = _menu(api, hwnd)
        editor = api.editor(hwnd)
        original = api.editor_bytes(hwnd)
        api.scalar(editor, 0x0102, ord('X'))  # bounded synthetic WM_CHAR, not global input
        ci.wait_gui(api, process, lambda: api.scalar(editor, 2159) == 1,
                    'Synthetic edit did not make the active document dirty')
        dirty = api.editor_bytes(hwnd)
        api.drop(editor, [inputs / 'deliberately missing.txt'])
        _error_dialog(api, process)
        ci.wait_gui(api, process, lambda: not ci.status_startswith(api.text(api.control(hwnd, 11)), 'status.opening'),
                    'Missing-file operation did not finish')
        if tabs() != 13 or api.editor_bytes(hwnd) != dirty or api.scalar(editor, 2159) != 1:
            raise RuntimeError('Missing file changed or discarded dirty document')
        if _menu(api, hwnd) != before:
            raise RuntimeError('Failed file was promoted to recent list')
        checks.update(failed_open_not_promoted=True, missing_keeps_dirty_text=True)
        api.command(hwnd, 201)
        ci.wait_gui(api, process, lambda: api.editor_bytes(hwnd) == original and api.scalar(editor, 2159) == 0,
                    'Undo did not restore the synthetic clean document')
        api.drop(api.editor(hwnd), [large])
        busy = lambda: ci.status_startswith(api.text(api.control(hwnd, 11)), 'status.opening')
        ci.wait_gui(api, process, busy, 'Cancellation fixture never entered busy state')
        api.command(hwnd, 901)
        ci.wait_gui(api, process, lambda: not busy(), 'Cancellation did not finish')
        if tabs() != 13 or _menu(api, hwnd) != before:
            raise RuntimeError('Cancelled file was promoted or left a partial tab')
        checks['cancel_not_promoted'] = True
        return {}

    def restart(process, hwnd):
        if _menu(api, hwnd) != list(map(_label, recent)):
            raise RuntimeError('Restart did not restore the exact recent-file order')
        checks['restart_restores_order'] = True
        api.command(hwnd, 1200)
        ci.wait_gui(api, process, lambda: api.scalar(api.control(hwnd, 10), 0x1304) == 2,
                    'Recent-file command did not open its stored path')
        if api.editor_bytes(hwnd) != paths[3].read_bytes():
            raise RuntimeError('Recent-file command opened wrong bytes')
        checks['recent_command_opens_exact_file'] = True
        api.command(hwnd, 1210)
        if _menu(api, hwnd) or stored():
            raise RuntimeError('Clear did not clear both menu and durable snapshot')
        checks['clear_persisted'] = True
        return {}

    def cleared(process, hwnd):
        if _menu(api, hwnd) or stored():
            raise RuntimeError('Cleared history reappeared after restart')
        checks['restart_after_clear_empty'] = True
        return {}

    def persistence_failure(process, hwnd):
        ci.wait_gui(api, process, lambda: api.scalar(api.control(hwnd, 10), 0x1304) == 2,
                    'Persistence failure prevented successful file opening')
        if api.editor_bytes(hwnd) != paths[0].read_bytes() or _menu(api, hwnd) != [_label(paths[0])]:
            raise RuntimeError('Persistence failure changed the opened document or in-memory list')
        return {}

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_path):
            raise RuntimeError('Refusing an existing recent-file test registry namespace')
    except FileNotFoundError:
        pass
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, registry_path, 0, winreg.KEY_SET_VALUE):
        pass
    try:
        phase('initial', initial, paths)
        phase('restart', restart)
        phase('cleared', cleared)
        failure_dir = phase('persistence-failure', persistence_failure, [paths[0]], 'invalid/slash')
        logs = list(failure_dir.glob('ru_notepad-*.log'))
        if len(logs) != 1 or '[recent] preference write failed: 13' not in ci.bounded_text(logs[0]):
            raise RuntimeError('No evidence that the persistence-failure path actually ran')
        checks['persistence_error_keeps_document'] = True
        if any(ci.sha(Path(path)) != digest for path, digest in originals.items()):
            raise RuntimeError('Recent-file test modified a synthetic source')
        checks['synthetic_sources_unchanged'] = True
    except Exception as exc:
        result['error'] = str(exc)
    finally:
        api.release_drops()
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, registry_path)
        except FileNotFoundError:
            pass
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_path):
                raise RuntimeError('Isolated recent-file registry cleanup failed')
        except FileNotFoundError:
            checks['isolated_registry_cleaned'] = True
    result['exit_code'] = 0 if len(result['phases']) == 4 and all(p.get('exit_code') == 0 for p in result['phases']) else None
    result['passed'] = set(checks) == set(CHECKS) and all(checks.values()) and 'error' not in result
    if result['passed']:
        validate_recent_files_result(result, expected_hashes)
    (evidence / 'recent-files.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    return result
