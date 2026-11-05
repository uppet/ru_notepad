#!/usr/bin/env python3
"""Real Windows list-only disk-search acceptance; portable tests are NOT GUI proof.

Only freshly created synthetic files, isolated settings and owned HWNDs are used.
The real command-326 shell picker is driven through its visible Unicode edit and
OK/Cancel buttons. There is no production test protocol or pointer WM_USER call.
Native host gates separately prove reparse traversal, blocked I/O and DLL lifetime.
"""
import ctypes
from ctypes import wintypes
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import re
import time
import windows_ci as ci
import gui_open_search as open_gui
from gui_instance_tabs import (isolated_settings, _copy_runtime, _post_command,
                               _information_dialog, _information_shape, _wait)
from gui_search_scope import set_text, disjoint, SEARCH_CONTROLS

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = open_gui.LANGUAGES
LAYOUT_SIZES = open_gui.LAYOUT_SIZES
START, STOP, HIDE, LIST, SUMMARY, OPEN, DETAILS = 326, 318, 319, 320, 321, 322, 327
MAX_ROWS, MAX_FILE_BYTES, STRESS_BYTES = 2000, 8 * 1024 * 1024, 128 * 1024
RESPONSE_SECONDS, RETIRE_SECONDS, COMPLETE_SECONDS = 2.0, 10.0, 90.0
CHECKS = ('owned_unicode_picker', 'recursive_encoding_matrix', 'exact_paths_scalar_columns',
          'malformed_tail_no_provisional_rows', 'exclusions_visible', 'captured_root_query',
          'literal_preferences_preserved', 'invalid_query_preserves', 'picker_cancel_preserves',
          'dirty_same_path_preserved', 'disabled_navigation', 'query_tab_edit_independent',
          'running_restart_blocked', 'stop_cancels', 'hide_cleanup_restart',
          'mode_switch_cleanup', 'input_responsiveness', 'row_cap', 'query_boundary',
          'seven_language_layout', 'close_running_normal_exit', 'disk_unchanged')
CANCEL_ACTIONS = ('stop', 'hide', 'mode')
ENGINE_GATES = ('strict_decoder_all_splits_and_malformed_tail_commit',
                'bounded_4096_raw_8192_work_16_rows_per_tick',
                'native_single_active_or_retiring_worker',
                'native_blocked_io_cancellation_and_retirement',
                'native_relative_handle_reparse_and_identity_checks',
                'native_limits_queue_and_dll_lifetime')
DISCLOSURES = ('Portable receipt tests do not execute Windows.',
               'GUI samples cover seven languages at two sizes, not universal DPI coverage.',
               'A transient draining state may retire before observation; prolonged blocked-I/O retirement is a mandatory native-host gate.',
               'No allocation-failure or blocked-I/O fault injection is performed by this GUI harness.')


def valid_texts():
    return {
        'left/same.txt': 'A|CAT scatter _cat cat\r\n汉😀 e\u0301 café\r\n尾cat',
        'right/same.txt': 'B|cat Cat cat_\n😀汉😀\ncat.*\n',
        'utf8-bom.txt': 'bom cat\r猫😀cat\r\n',
        'utf16-le.txt': '甲😀cat\r\ncat\rXcat',
        'utf16-be.txt': '甲cat\n😀cat',
        'normalization.txt': 'e\u0301 é E\u0301\n',
        'boundary.txt': 'x' * 509 + '汉😀edge',
        'controls.txt': 'abc\t\u202ecat\r\n',
        'empty.txt': '',
        'bom-only.txt': '',
    }


@lru_cache(maxsize=1)
def _fixture_bytes():
    result = {}
    for name, text in valid_texts().items():
        encoding = 'utf-16-le' if name == 'utf16-le.txt' else 'utf-16-be' if name == 'utf16-be.txt' else 'utf-8'
        prefix = b'\xff\xfe' if encoding == 'utf-16-le' else b'\xfe\xff' if encoding == 'utf-16-be' else b'\xef\xbb\xbf' if name in ('utf8-bom.txt', 'bom-only.txt') else b''
        result['semantic/' + name] = prefix + text.encode(encoding)
    result.update({
        'semantic/excluded/utf8-tail.txt': b'cat ' + b'x' * 513 + b'\xf0\x9f',
        'semantic/excluded/utf8-overlong.txt': b'cat\xc0\xaf',
        'semantic/excluded/utf16-le-tail.txt': b'\xff\xfe' + 'cat'.encode('utf-16-le') + b'\x00\xd8',
        'semantic/excluded/utf16-be-tail.txt': b'\xfe\xff' + 'cat'.encode('utf-16-be') + b'\xdc\x00',
        'semantic/excluded/nul-tail.txt': b'cat\x00',
        'semantic/excluded/utf32-le.txt': b'\xff\xfe\x00\x00' + 'cat'.encode('utf-32-le'),
        'semantic/excluded/utf32-be.txt': b'\x00\x00\xfe\xff' + 'cat'.encode('utf-32-be'),
        'semantic/excluded/oversize.txt': b'cat' + b'x' * (MAX_FILE_BYTES - 2),
        'stress/slow.txt': b'x' * STRESS_BYTES,
        'cap/hits.txt': b'x' * (MAX_ROWS + 1),
        'query-boundary/query.txt': ('界' * 256).encode(),
        'outside.txt': b'outside-only clean document\n',
    })
    return result


def fixtures():
    return dict(_fixture_bytes())


def inventory():
    return [dict(id=name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
            for name, data in _fixture_bytes().items()]


def escaped(text):
    return ''.join('\ufffd' if ord(c) < 32 or 127 <= ord(c) < 160 or 8232 <= ord(c) <= 8238 or
                   8294 <= ord(c) <= 8297 or ord(c) in (1564, 8206, 8207) else c for c in text)


def detail_escaped(text):
    return ''.join({'\t': '␉', '\r': '␍', '\n': '␊'}.get(c, escaped(c)) for c in text)


def text_rows(name, text, query):
    """Small known-valid fixture oracle, independent of production decoding."""
    if not query:
        raise ValueError('The fixture oracle requires a nonempty query')
    coordinates = []; line = column = 1; line_start = 0; previous = ''
    for index, char in enumerate(text):
        if previous == '\n' or previous == '\r' and char != '\n':
            line += 1; column = 1; line_start = index
        coordinates.append((line, column, line_start)); column += 1; previous = char
    rows = []; offset = 0
    while True:
        at = text.find(query, offset)
        if at < 0:
            return rows
        line, column, start = coordinates[at]; leading = max(start, at - 32)
        preview = ('…' if leading > start else '') + escaped(text[leading:at] + query[:64]) + ('…' if len(query) > 64 else '')
        rows.append(dict(path=name, line=line, column=column, preview=preview))
        offset = at + len(query)


def cases():
    return (('case-substrings', 'cat'), ('unicode', '汉😀'), ('literal-not-regex', 'cat.*'),
            ('no-normalization', 'é'), ('exact-uppercase', 'CAT'),
            ('crlf', 'cat\r\ncat'), ('decoder-boundary', '汉😀edge'), ('no-match', 'missing-needle'))


def expected_cases():
    return [dict(id=name, query=query, rows=sorted(
        [r for path, text in valid_texts().items() for r in text_rows(path, text, query)],
        key=lambda r: (r['path'], r['line'], r['column'])),
        files=len(valid_texts()), skipped=8, status='limited') for name, query in cases()]


def _seconds(value, maximum, description):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value < maximum:
        raise ValueError(description + ' timing is invalid or exceeds its bound')


def _lifecycle(row, name, hashes):
    if not isinstance(row, dict) or row.get('name') != name:
        raise ValueError('Directory GUI phase identity differs')
    for key, value in (('passed', True), ('executed', True), ('cleanup_killed', False),
                       ('main_hwnd_seen', True), ('close_posted', True), ('detached_from_console', True)):
        if row.get(key) is not value:
            raise ValueError('Directory GUI lifecycle failed')
    if type(row.get('exit_code')) is not int or row['exit_code'] != 0 or row.get('error') or row.get('skips'):
        raise ValueError('Directory GUI failed or skipped')
    if row.get('fixture_binary_sha256') != hashes:
        raise ValueError('Directory GUI runtime identity differs')


def validate_layouts(rows):
    if not isinstance(rows, list) or len(rows) != len(LANGUAGES) * len(LAYOUT_SIZES) * 2:
        raise ValueError('Directory layout inventory differs')
    stripped = []
    extras = {'details_readonly', 'details_scrollable', 'details_client_height', 'details_font_height',
              'details_lines', 'summary_minimum_width', 'navigation_disabled'}
    for row in rows:
        if not isinstance(row, dict) or not extras <= set(row):
            raise ValueError('Directory detail geometry missing')
        if any(row[k] is not True for k in ('details_readonly', 'details_scrollable', 'navigation_disabled')):
            raise ValueError('Directory list-only detail control contract differs')
        for k in ('details_client_height', 'details_font_height', 'details_lines', 'summary_minimum_width'):
            if type(row[k]) is not int or row[k] <= 0:
                raise ValueError('Directory native detail measurement invalid')
        if row['details_lines'] < 6 or row['details_client_height'] < row['details_font_height']:
            raise ValueError('Directory details cannot display a complete text line')
        rects = row.get('rectangles'); rect = rects.get(str(DETAILS)) if isinstance(rects, dict) else None
        if not isinstance(rect, list) or len(rect) != 4 or any(type(n) is not int for n in rect):
            raise ValueError('Directory details rectangle invalid')
        client = row.get('client')
        if not isinstance(client, list) or len(client) != 2 or any(type(n) is not int for n in client):
            raise ValueError('Directory client dimensions invalid')
        if not (0 <= rect[0] < rect[2] <= client[0] and 0 <= rect[1] < rect[3] <= client[1]):
            raise ValueError('Directory details outside client')
        if row['details_client_height'] > rect[3] - rect[1]:
            raise ValueError('Directory details client exceeds its rectangle')
        if any(not disjoint(rect, other) for key, other in rects.items() if key != str(DETAILS)):
            raise ValueError('Directory details overlap another control')
        summary = rects.get(str(SUMMARY), [0, 0, 0, 0])
        if summary[2] - summary[0] < row['summary_minimum_width']:
            raise ValueError('Directory translated summary clipped')
        copy = {k: v for k, v in row.items() if k not in extras}
        copy['rectangles'] = {k: v for k, v in rects.items() if k != str(DETAILS)}
        stripped.append(copy)
    open_gui.validate_layouts(stripped)
    return True


def validate_result(report, runtime_hashes):
    if not isinstance(runtime_hashes, dict) or set(runtime_hashes) != set(ci.portable.RUNTIME_NAMES) or any(
            not isinstance(v, str) or re.fullmatch('[0-9a-f]{64}', v) is None for v in runtime_hashes.values()):
        raise ValueError('Directory runtime hash inventory invalid')
    if not isinstance(report, dict) or report.get('schema') != 'ru-notepad-directory-search-gui-v1':
        raise ValueError('Directory GUI schema differs')
    _lifecycle(report, 'main-gui-directory-search', runtime_hashes)
    _lifecycle(report.get('close_running'), 'main-gui-directory-close-running', runtime_hashes)
    close = report['close_running']
    if close.get('running_seen') is not True:
        raise ValueError('Window close did not interrupt a running directory job')
    _seconds(close.get('close_seconds'), RETIRE_SECONDS, 'Window close')
    for key, expected in (('fixtures', inventory()), ('cases', expected_cases()),
                          ('engine_gates', list(ENGINE_GATES)), ('disclosures', list(DISCLOSURES))):
        if report.get(key) != expected:
            raise ValueError('Directory inventory differs: ' + key)
    for item in report['fixtures']:
        if type(item['bytes']) is not int:
            raise ValueError('Directory fixture byte types differ')
    for case in report['cases']:
        if type(case['files']) is not int or type(case['skipped']) is not int or any(
                type(row[k]) is not int for row in case['rows'] for k in ('line', 'column')):
            raise ValueError('Directory semantic integer types differ')
    if report.get('checks') != dict.fromkeys(CHECKS, True) or any(v is not True for v in report['checks'].values()):
        raise ValueError('Directory checks incomplete')
    for field, expected in (('query_boundary', dict(scalars=256, utf8_bytes=768, rows=1)),
                            ('row_cap', dict(rows=MAX_ROWS, status='limited', reason_visible=True)),
                            ('picker', dict(unicode_path=True, owned_modal=True, edit_readback=True, cancelled=True))):
        if report.get(field) != expected or any(type(report[field][k]) is not type(v) for k, v in expected.items()):
            raise ValueError('Directory observed evidence differs: ' + field)
    cancellations = report.get('cancellations')
    if not isinstance(cancellations, list) or len(cancellations) != len(CANCEL_ACTIONS):
        raise ValueError('Directory cancellation inventory differs')
    fields = {'action', 'running_seen', 'stable', 'restart_succeeded', 'seconds', 'retire_seconds', 'draining_seen', 'busy_rejections'}
    for item, action in zip(cancellations, CANCEL_ACTIONS):
        if not isinstance(item, dict) or set(item) != fields or item['action'] != action or any(
                item[k] is not True for k in ('running_seen', 'stable', 'restart_succeeded')) or type(item['draining_seen']) is not bool:
            raise ValueError('Directory cancellation was not observed')
        if type(item['busy_rejections']) is not int or not 0 <= item['busy_rejections'] <= 100:
            raise ValueError('Directory draining rejection observation invalid')
        _seconds(item['seconds'], RESPONSE_SECONDS, 'Directory logical cancellation')
        _seconds(item['retire_seconds'], RETIRE_SECONDS, 'Directory cleanup/restart')
    responses = report.get('responses')
    if not isinstance(responses, list) or len(responses) != 3:
        raise ValueError('Directory responsiveness observations missing')
    for item, action in zip(responses, ('query', 'tab', 'caret')):
        if not isinstance(item, dict) or set(item) != {'action', 'seconds', 'running_after'} or item['action'] != action or item['running_after'] is not True:
            raise ValueError('Directory real input response not observed')
        _seconds(item['seconds'], RESPONSE_SECONDS, 'Directory input response')
    labels = report.get('labels')
    if not isinstance(labels, list) or len(labels) != len(LANGUAGES):
        raise ValueError('Directory translated labels missing')
    for item, language in zip(labels, LANGUAGES):
        if item != dict(language=language, menu_verified=True, details_verified=True) or any(
                item[k] is not True for k in ('menu_verified', 'details_verified')):
            raise ValueError('Directory localized text was not verified')
    validate_layouts(report.get('layouts'))
    return True


def picker_shape(api, process, owner, dialog):
    """Only a native owned folder picker, not a generic dialog or message box."""
    u = api.user
    u.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]; u.GetWindow.restype = wintypes.HWND
    u.GetDlgCtrlID.argtypes = [wintypes.HWND]; u.GetDlgCtrlID.restype = ctypes.c_int
    api.verify_owned_handles(process.pid, owner, dialog)
    if u.GetWindow(dialog, 4) != owner or u.IsWindowEnabled(owner):
        raise RuntimeError('Folder picker is not owned modal UI')
    controls = []; errors = []
    @api.callback_type
    def visit(child, _):
        try:
            if len(controls) >= 128:
                raise RuntimeError('Folder picker control inventory exceeds bound')
            pid = wintypes.DWORD(); u.GetWindowThreadProcessId(child, ctypes.byref(pid))
            if pid.value != process.pid:
                raise RuntimeError('Foreign folder picker control')
            cls = ctypes.create_unicode_buffer(128)
            if not u.GetClassNameW(child, cls, len(cls)):
                raise RuntimeError('Cannot inspect folder picker child')
            if u.IsWindowVisible(child):
                controls.append((int(child), cls.value, u.GetDlgCtrlID(child), bool(u.IsWindowEnabled(child))))
            return True
        except Exception as exc:
            errors.append(exc); return False
    u.EnumChildWindows(dialog, visit, 0)
    if errors:
        raise errors[0]
    edits = [h for h, c, _, enabled in controls if c == 'Edit' and enabled]
    trees = [h for h, c, _, enabled in controls if c == 'SysTreeView32' and enabled]
    buttons = {i: h for h, c, i, _ in controls if c == 'Button' and i in (1, 2)}
    if len(edits) != 1 or len(trees) != 1 or set(buttons) != {1, 2} or not u.IsWindowEnabled(buttons[2]):
        raise RuntimeError('Owned shell picker lacks one editable path, tree, OK and Cancel: ' + repr([(c, i, e) for _, c, i, e in controls]))
    return edits[0], buttons


def choose_folder(api, process, hwnd, root=None, *, busy_body=None):
    """Real WM_COMMAND opens the modal picker; WM_SETTEXT is system-marshalled.

    A bounded cleanup restart may encounter the actual localized busy dialog.
    Dismiss only that exact owned informational box and retry the same user
    command. No synthetic app protocol polls or skips the retiring-worker guard.
    """
    deadline = time.monotonic() + RETIRE_SECONDS; rejected = 0
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or rejected > 100:
            raise RuntimeError('Folder request could not pass normal retirement guard within bound')
        _post_command(api, hwnd, START)
        found = []
        def ready():
            dialogs = [h for h, c, v in api.windows(process.pid) if c == '#32770' and v]
            if len(dialogs) > 1:
                raise RuntimeError('More than one owned dialog during folder selection')
            if not dialogs:
                return False
            try:
                edit, buttons = picker_shape(api, process, hwnd, dialogs[0])
                found[:] = [dialogs[0], edit, buttons, False]
            except RuntimeError:
                if busy_body is None:
                    raise
                shape = _information_dialog(api, process, dialogs[0], deadline)
                button = _information_shape(shape, hwnd, {busy_body})
                if button is None:
                    raise RuntimeError('Unexpected dialog while waiting for directory retirement')
                found[:] = [dialogs[0], None, {1: button}, True]
            return True
        _wait(api, process, ready, 'Owned folder picker did not appear', remaining, dialogs=True)
        dialog, edit, buttons, busy = found
        if busy:
            button = buttons[1]
            api.verify_owned_handles(process.pid, hwnd, dialog, button)
        else:
            if root is not None:
                value = str(Path(root).resolve())
                set_text(api, edit, value)
                # Standard WM_NEXTDLGCTL transfers focus on the dialog's own thread.
                api.scalar(dialog, 0x28, edit, 1)
            button = buttons[1 if root is not None else 2]
            api.verify_owned_handles(process.pid, hwnd, dialog, edit, button)
            _wait(api, process, lambda: bool(api.user.IsWindowEnabled(button)),
                  'Folder picker action remains disabled after path entry',
                  max(.01, deadline - time.monotonic()), dialogs=True)
        if not api.user.PostMessageW(button, 0xF5, 0, 0):
            raise ctypes.WinError(ctypes.get_last_error())
        _wait(api, process, lambda: not api.user.IsWindowVisible(dialog),
              'Folder picker did not accept typed Unicode path or cancel',
              max(.01, deadline - time.monotonic()), dialogs=True)
        ci.wait_gui(api, process, lambda: bool(api.user.IsWindowEnabled(hwnd)),
                    'Folder picker left owner disabled', timeout=max(.01, deadline - time.monotonic()))
        if not busy:
            return rejected
        rejected += 1
        time.sleep(.03)


def information(api, process, hwnd, command, expected_body):
    _post_command(api, hwnd, command); found = []; deadline = time.monotonic() + 10
    def ready():
        dialogs = [h for h, c, v in api.windows(process.pid) if c == '#32770' and v]
        if len(dialogs) != 1:
            return False
        shape = _information_dialog(api, process, dialogs[0], deadline)
        button = _information_shape(shape, hwnd, {expected_body})
        if button is None:
            raise RuntimeError('Directory informational dialog body or shape differs')
        found[:] = [dialogs[0], button]; return True
    _wait(api, process, ready, 'Directory expected information absent', 10, dialogs=True)
    api.verify_owned_handles(process.pid, hwnd, *found)
    if not api.user.PostMessageW(found[1], 0xF5, 0, 0):
        raise ctypes.WinError(ctypes.get_last_error())
    _wait(api, process, lambda: not api.user.IsWindowVisible(found[0]), 'Directory information not dismissed', 10, dialogs=True)


def list_labels(api, hwnd):
    handle = api.control(hwnd, LIST); count = api.scalar(handle, 0x18B)
    if not 0 <= count <= MAX_ROWS:
        raise RuntimeError('Directory native list count exceeds bound')
    labels = []
    for index in range(count):
        length = api.scalar(handle, 0x18A, index)
        if not 0 <= length <= 1024:
            raise RuntimeError('Directory result label exceeds bound')
        buffer = ctypes.create_unicode_buffer(length + 1)
        # LB_GETTEXT is a standard system-marshalled LISTBOX message (<WM_USER).
        if api.scalar(handle, 0x189, index, ctypes.addressof(buffer)) != length:
            raise RuntimeError('Directory list text readback differs')
        labels.append(buffer.value)
    return labels


def observed_rows(labels, root):
    prefix = str(Path(root).resolve()) + '\\'; rows = []
    for label in labels:
        match = re.fullmatch(r'(.+) : ([1-9][0-9]*):([1-9][0-9]*) : (.*)', label)
        if match is None or not match[1].startswith(prefix):
            raise RuntimeError('Directory row path or scalar coordinates malformed: ' + repr(label))
        rows.append(dict(path=match[1][len(prefix):].replace('\\', '/'), line=int(match[2]), column=int(match[3]), preview=match[4]))
    return sorted(rows, key=lambda r: (r['path'], r['line'], r['column']))


def native_layout(api, hwnd, language, size, bar):
    base = open_gui.native_layout(api, hwnd, language, size, bar)
    u = api.user; gdi = ctypes.WinDLL('gdi32', use_last_error=True)
    gdi.SelectObject.argtypes = [wintypes.HDC, wintypes.HANDLE]; gdi.SelectObject.restype = wintypes.HANDLE
    gdi.GetTextExtentPoint32W.argtypes = [wintypes.HDC, wintypes.LPCWSTR, ctypes.c_int, ctypes.POINTER(wintypes.SIZE)]; gdi.GetTextExtentPoint32W.restype = wintypes.BOOL
    u.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]; u.GetWindowLongPtrW.restype = ctypes.c_ssize_t
    handle = api.control(hwnd, DETAILS); origin = wintypes.POINT(); rect = wintypes.RECT(); client = wintypes.RECT()
    if not u.IsWindowVisible(handle) or not u.ClientToScreen(hwnd, ctypes.byref(origin)) or not u.GetWindowRect(handle, ctypes.byref(rect)) or not u.GetClientRect(handle, ctypes.byref(client)):
        raise RuntimeError('Directory details native geometry unavailable')
    def extent(target, text):
        dc = u.GetDC(target); font = api.scalar(target, 0x31); previous = None
        if not dc or not font:
            raise RuntimeError('Directory native font unavailable')
        try:
            previous = gdi.SelectObject(dc, font); size = wintypes.SIZE()
            if not previous or previous == ctypes.c_void_p(-1).value:
                raise RuntimeError('Directory native font select failed')
            if not gdi.GetTextExtentPoint32W(dc, text, len(text.encode('utf-16-le')) // 2, ctypes.byref(size)):
                raise ctypes.WinError(ctypes.get_last_error())
            return size.cx, size.cy
        finally:
            if previous and previous != ctypes.c_void_p(-1).value:
                gdi.SelectObject(dc, previous)
            u.ReleaseDC(target, dc)
    style = u.GetWindowLongPtrW(handle, -16)
    base['rectangles'][str(DETAILS)] = [rect.left-origin.x, rect.top-origin.y, rect.right-origin.x, rect.bottom-origin.y]
    base.update(details_readonly=bool(style & 0x800), details_scrollable=bool(style & 0x200000),
                details_client_height=client.bottom-client.top, details_font_height=extent(handle, 'Ag')[1],
                details_lines=api.scalar(handle, 0xBA), summary_minimum_width=extent(api.control(hwnd, SUMMARY), api.text(api.control(hwnd, SUMMARY)))[0] + 4,
                navigation_disabled=not bool(u.IsWindowEnabled(api.control(hwnd, OPEN))))
    return base


def write_progress(evidence, progress, phase):
    progress['phase'] = phase
    ci.save_json(Path(evidence) / 'directory-search-progress.json', progress)


def run(api, runtime, fixtures_dir, evidence):
    runtime, fixtures_dir, evidence = map(Path, (runtime, fixtures_dir, evidence))
    sources = fixtures(); root = fixtures_dir / 'directory-search-目录😀'; paths = {}
    for name, data in sources.items():
        path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data); paths[name] = path
    hashes = {name: ci.sha(runtime / name) for name in ci.portable.RUNTIME_NAMES}
    target = fixtures_dir / 'directory-search-runtime'; _copy_runtime(runtime, target, hashes)
    catalog = json.loads((ROOT / 'locales/directory_search.json').read_text(encoding='utf-8'))
    progress = dict(checks={}, cases=[], cancellations=[], responses=[])
    evidence.mkdir(parents=True, exist_ok=True)
    def phase(name):
        write_progress(evidence, progress, name)
    u = api.user
    u.IsWindowEnabled.argtypes = [wintypes.HWND]; u.IsWindowEnabled.restype = wintypes.BOOL
    u.GetMenu.argtypes = [wintypes.HWND]; u.GetMenu.restype = ctypes.c_void_p
    u.GetMenuStringW.argtypes = [ctypes.c_void_p, ctypes.c_uint, wintypes.LPWSTR, ctypes.c_int, ctypes.c_uint]; u.GetMenuStringW.restype = ctypes.c_int
    u.GetMenuState.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint]; u.GetMenuState.restype = ctypes.c_uint
    def tr(key, language='en', *values):
        text = catalog['directory.' + key][language]
        for index, value in enumerate(values):
            text = text.replace('{' + str(index) + '}', str(value))
        return text
    opened = [paths['semantic/left/same.txt'], paths['outside.txt']]
    def exercise(process, hwnd):
        checks = progress['checks']; results = progress['cases']; cancellations = progress['cancellations']; responses = progress['responses']; layouts = []; labels = []
        ci.wait_gui(api, process, lambda: api.text(hwnd) == opened[-1].name + ' · ru_notepad' and not u.IsWindowVisible(api.control(hwnd, 901)), 'Directory GUI documents did not load')
        api.command(hwnd, 851); api.command(hwnd, 301)
        # Cache actual owned editor HWNDs before making one caption dirty.
        handles = []; tab_count = api.scalar(api.control(hwnd, 10), 0x1304); dirty = None
        if tab_count != 3:
            raise RuntimeError('Directory test requires exactly two opened files and initial untitled tab')
        for _ in range(tab_count):
            editor = api.editor(hwnd); api.verify_owned_handles(process.pid, hwnd, editor)
            handles.append(editor)
            if api.editor_bytes(hwnd) == sources['semantic/left/same.txt']:
                dirty = editor
            api.command(hwnd, 112)
        if len(set(handles)) != tab_count or dirty is None:
            raise RuntimeError('Directory synthetic editor identities ambiguous')
        def activate(handle):
            for _ in range(tab_count):
                if api.editor(hwnd) == handle:
                    api.verify_owned_handles(process.pid, hwnd, handle); return
                api.command(hwnd, 112)
            raise RuntimeError('Cached directory fixture editor is no longer reachable')
        def documents():
            state = {}
            for handle in handles:
                length = api.scalar(handle, 2006)
                if length > 4096:
                    raise RuntimeError('Unexpected large editor in directory test')
                data = bytes(api.scalar(handle, 2007, n) & 255 for n in range(length))
                state[str(handle)] = (data,) + tuple(api.scalar(handle, m) for m in (2008, 2009, 2159, 2174, 2016, 2140, 2137))
            return api.editor(hwnd), api.scalar(api.control(hwnd, 10), 0x1304), state
        def summary(): return api.text(api.control(hwnd, SUMMARY))
        def details(): return api.text(api.control(hwnd, DETAILS))
        def count(): return api.scalar(api.control(hwnd, LIST), 0x18B)
        def running(): return bool(u.IsWindowEnabled(api.control(hwnd, STOP))) and tr('status_running') in summary()
        def query(value): set_text(api, api.control(hwnd, 310), value)
        def start(folder, value, *, cleanup=False):
            query(value)
            return choose_folder(api, process, hwnd, root / folder, busy_body=tr('busy') if cleanup else None)
        def terminal(status, total=None, files=None):
            text = summary()
            if tr('retiring') in text or tr('status_' + status) not in text or u.IsWindowEnabled(api.control(hwnd, STOP)):
                return False
            return (total is None or count() == total) and (files is None or text == tr('summary', 'en', tr('status_' + status), total, files))
        def finish(status, total=None, files=None):
            ci.wait_gui(api, process, lambda: terminal(status, total, files), 'Directory search did not finish as ' + status + ': ' + summary(), timeout=COMPLETE_SECONDS)
        def preferences():
            return tuple(api.scalar(api.control(hwnd, n), 240) for n in (306, 309)) + tuple(bool(u.GetMenuState(u.GetMenu(hwnd), n, 0) & 8) for n in (323, 324))
        def captured(folder, value, language='en'):
            body = details()
            for expected in (tr('root', language, str((root / folder).resolve())), tr('query', language, detail_escaped(value)),
                             tr('policy', language), tr('exclusions', language), tr('limits', language)):
                if expected not in body:
                    raise RuntimeError('Directory captured scope/policy missing: ' + expected)
        # Open panels before comparisons so viewport resize is not a text mutation.
        activate(dirty); api.scalar(dirty, 2160, 0, 0)
        for char in 'dirty-only ': api.scalar(dirty, 0x102, ord(char), 1)
        api.command(hwnd, 323); api.scalar(api.control(hwnd, 306), 241, 0); api.scalar(api.control(hwnd, 309), 241, 1)
        literal_preferences = preferences(); api.command(hwnd, 324); regex_preferences = preferences()
        if not api.scalar(dirty, 2159): raise RuntimeError('Directory dirty-path fixture is not dirty')
        for expected in expected_cases():
            phase('semantic-' + expected['id']); before = documents()
            start('semantic', expected['query']); finish('limited', len(expected['rows']), expected['files'])
            rows = observed_rows(list_labels(api, hwnd), root / 'semantic')
            if rows != expected['rows'] or documents() != before or preferences() != regex_preferences:
                raise RuntimeError('Directory semantic/preservation mismatch: ' + expected['id'])
            captured('semantic', expected['query'])
            body = details(); raw = sum(len(data) for name, data in sources.items() if name.startswith('semantic/') and len(data) <= MAX_FILE_BYTES)
            if tr('counts', 'en', 8, 0, raw) not in body:
                raise RuntimeError('Directory exact exclusion/read counters differ')
            for reason, total in (('utf8', 2), ('utf16', 2), ('bom', 2), ('nul', 1), ('size', 1)):
                if tr('reason_' + reason) + ': ' + str(total) not in body:
                    raise RuntimeError('Directory exclusion reason missing: ' + reason)
            results.append(dict(id=expected['id'], query=expected['query'], rows=rows, files=expected['files'], skipped=8, status='limited'))
        checks['owned_unicode_picker'] = True; checks['recursive_encoding_matrix'] = True; checks['exact_paths_scalar_columns'] = True
        checks['malformed_tail_no_provisional_rows'] = True; checks['exclusions_visible'] = True; checks['captured_root_query'] = True
        checks['dirty_same_path_preserved'] = True
        phase('retained-results'); start('semantic', 'cat'); finish('limited', len(expected_cases()[0]['rows']), len(valid_texts()))
        retained = (list_labels(api, hwnd), summary(), details()); before = documents()
        for invalid in ('', '界' * 257):
            query(invalid); information(api, process, hwnd, START, tr('query_invalid'))
            if (list_labels(api, hwnd), summary(), details()) != retained or documents() != before:
                raise RuntimeError('Invalid directory query discarded prior results')
        checks['invalid_query_preserves'] = True
        query('picker-cancel'); choose_folder(api, process, hwnd)
        if (list_labels(api, hwnd), summary(), details()) != retained or documents() != before:
            raise RuntimeError('Folder picker Cancel changed previous directory results')
        checks['picker_cancel_preserves'] = True
        query('edited-query'); api.command(hwnd, 112); activate(dirty); api.scalar(dirty, 0x102, ord('Z'), 1)
        api.responsive(hwnd)
        if (list_labels(api, hwnd), summary(), details()) != retained:
            raise RuntimeError('Query/tab/document edit made disk results stale')
        api.command(hwnd, 201)
        if (list_labels(api, hwnd), summary(), details()) != retained or not api.scalar(dirty, 2159):
            raise RuntimeError('Undo invalidated disk results or lost the dirty buffer')
        checks['query_tab_edit_independent'] = True
        phase('disabled-navigation'); result_list = api.control(hwnd, LIST); api.scalar(result_list, 0x186, 0)
        if u.IsWindowEnabled(api.control(hwnd, OPEN)): raise RuntimeError('Directory result navigation enabled')
        before = documents(); api.command(hwnd, OPEN)
        api.verify_owned_handles(process.pid, hwnd, dirty, result_list)
        if not u.PostMessageW(result_list, 0x100, 13, 1): raise ctypes.WinError(ctypes.get_last_error())
        api.responsive(hwnd)
        api.scalar(result_list, 0x197, 0)
        try: api.scalar(result_list, 0x203, 1, 5 | (5 << 16))
        finally: api.scalar(result_list, 0x202, 0, 5 | (5 << 16))
        api.responsive(hwnd)
        if documents() != before or (list_labels(api, hwnd), summary(), details()) != retained:
            raise RuntimeError('Directory command/Enter/double-click navigated or mutated documents')
        checks['disabled_navigation'] = True
        api.command(hwnd, 323)
        if preferences() != literal_preferences: raise RuntimeError('Directory search changed saved literal options')
        phase('literal-options-independent'); before = documents()
        start('semantic', 'cat'); finish('limited', len(expected_cases()[0]['rows']), len(valid_texts()))
        if observed_rows(list_labels(api, hwnd), root / 'semantic') != expected_cases()[0]['rows'] or preferences() != literal_preferences or documents() != before:
            raise RuntimeError('Directory search inherited literal case/whole preferences')
        checks['literal_preferences_preserved'] = True
        phase('independent-open-mode'); query('dirty-only'); api.command(hwnd, 317)
        ci.wait_gui(api, process, lambda: not u.IsWindowEnabled(api.control(hwnd, STOP)), 'Open-buffer mode did not complete')
        if count() != 1 or u.IsWindowVisible(api.control(hwnd, DETAILS)) or not u.IsWindowEnabled(api.control(hwnd, OPEN)):
            raise RuntimeError('Shared results panel did not restore independent open-buffer mode')
        phase('query-boundary'); start('query-boundary', '界' * 256); finish('complete', 1, 1)
        expected = text_rows('query.txt', '界' * 256, '界' * 256)
        if observed_rows(list_labels(api, hwnd), root / 'query-boundary') != expected: raise RuntimeError('Directory 256-scalar boundary query differs')
        checks['query_boundary'] = True
        phase('row-cap'); start('cap', 'x'); finish('limited', MAX_ROWS, 1)
        cap_rows = observed_rows(list_labels(api, hwnd), root / 'cap')
        if cap_rows != text_rows('hits.txt', 'x' * (MAX_ROWS + 1), 'x')[:MAX_ROWS] or tr('reason_rows') + ': 1' not in details():
            raise RuntimeError('Directory row cap or exact scalar positions differ')
        checks['row_cap'] = True
        for action in CANCEL_ACTIONS:
            phase('interrupt-' + action); start('stress', 'missing-stress-needle')
            if not running(): raise RuntimeError('Directory interruption fixture was not observed running')
            if action == 'stop':
                old = (summary(), details(), count()); query('busy-new-query')
                information(api, process, hwnd, START, tr('busy'))
                if not running() or count() != old[2]: raise RuntimeError('Running restart replaced the active worker/results')
                captured('stress', 'missing-stress-needle'); checks['running_restart_blocked'] = True
                for input_action in ('query', 'tab', 'caret'):
                    began = time.perf_counter()
                    if input_action == 'query': query('while-running')
                    elif input_action == 'tab': api.command(hwnd, 112)
                    else:
                        editor = api.editor(hwnd); api.scalar(editor, 2160, 0, 0)
                        # Do not select the initial empty tab for a real caret move.
                        if api.scalar(editor, 2006) == 0: activate(dirty); editor = dirty; api.scalar(editor, 2160, 0, 0)
                        api.verify_owned_handles(process.pid, hwnd, editor); api.post_navigation(editor, 'RIGHT')
                        ci.wait_gui(api, process, lambda: api.scalar(editor, 2008) == 1, 'Directory job blocked real editor navigation', timeout=RESPONSE_SECONDS)
                    api.responsive(hwnd); elapsed = time.perf_counter() - began
                    if elapsed >= RESPONSE_SECONDS or not running(): raise RuntimeError('Directory running input bound failed')
                    responses.append(dict(action=input_action, seconds=elapsed, running_after=True))
                checks['input_responsiveness'] = True
            began = time.perf_counter()
            if action == 'mode': query('dirty-only'); api.command(hwnd, 317)
            else: api.command(hwnd, STOP if action == 'stop' else HIDE)
            if action != 'mode':
                ci.wait_gui(api, process, lambda: not u.IsWindowEnabled(api.control(hwnd, STOP)) and tr('status_cancelled') in summary(), 'Directory Stop/Close did not logically cancel', timeout=RESPONSE_SECONDS)
            else:
                ci.wait_gui(api, process, lambda: not u.IsWindowVisible(api.control(hwnd, DETAILS)), 'Directory mode did not switch', timeout=RESPONSE_SECONDS)
            elapsed = time.perf_counter() - began
            if elapsed >= RESPONSE_SECONDS: raise RuntimeError('Directory cancellation exceeded response bound')
            draining = tr('retiring') in summary() if action != 'mode' else False
            stable_count = count(); before = documents()
            # Wait through a bounded real timer interval, then use a normal new
            # folder request to establish that hidden/superseded retirement ran.
            time.sleep(.12); api.responsive(hwnd)
            if action != 'mode' and count() != stable_count: raise RuntimeError('Cancelled directory job appended stale rows')
            if documents() != before: raise RuntimeError('Cancelled directory job mutated live documents')
            if action == 'hide' and u.IsWindowVisible(api.control(hwnd, LIST)): raise RuntimeError('Directory Close did not hide shared results')
            if action == 'mode':
                ci.wait_gui(api, process, lambda: not u.IsWindowEnabled(api.control(hwnd, STOP)), 'Open mode did not complete after directory cancellation')
                if count() != 1: raise RuntimeError('Open mode reused directory rows')
            busy_rejections = start('query-boundary', '界' * 256, cleanup=True)
            retired = time.perf_counter() - began
            if retired >= RETIRE_SECONDS: raise RuntimeError('Directory hidden/mode cleanup restart exceeded bound')
            finish('complete', 1, 1)
            cancellations.append(dict(action=action, running_seen=True, stable=True, restart_succeeded=True,
                                      seconds=elapsed, retire_seconds=retired, draining_seen=draining, busy_rejections=busy_rejections))
        checks['stop_cancels'] = True; checks['hide_cleanup_restart'] = True; checks['mode_switch_cleanup'] = True
        phase('layouts'); start('semantic', 'cat'); finish('limited', len(expected_cases()[0]['rows']), len(valid_texts()))
        for index, language in enumerate(LANGUAGES):
            api.command(hwnd, 851 + index); captured('semantic', 'cat', language)
            buf = ctypes.create_unicode_buffer(512); u.GetMenuStringW(u.GetMenu(hwnd), START, buf, len(buf), 0)
            if buf.value != tr('find', language): raise RuntimeError('Directory menu translation differs')
            if summary() != tr('summary', language, tr('status_limited', language), len(expected_cases()[0]['rows']), len(valid_texts())):
                raise RuntimeError('Directory translated summary differs')
            for size in LAYOUT_SIZES:
                api.command(hwnd, 307); layouts.append(native_layout(api, hwnd, language, size, False))
                api.command(hwnd, 301); layouts.append(native_layout(api, hwnd, language, size, True))
            labels.append(dict(language=language, menu_verified=True, details_verified=True))
        validate_layouts(layouts); checks['seven_language_layout'] = True
        activate(dirty)
        while api.scalar(dirty, 2174): api.command(hwnd, 201)
        if api.editor_bytes(hwnd) != sources['semantic/left/same.txt']: raise RuntimeError('Directory dirty buffer undo history was altered')
        if any(ci.sha(path) != hashlib.sha256(sources[name]).hexdigest() for name, path in paths.items()): raise RuntimeError('Directory search wrote synthetic disk sources')
        checks['disk_unchanged'] = True
        return dict(checks=checks, cases=results, cancellations=cancellations, responses=responses, layouts=layouts, labels=labels,
                    picker=dict(unicode_path=True, owned_modal=True, edit_readback=True, cancelled=True),
                    query_boundary=dict(scalars=256, utf8_bytes=768, rows=1), row_cap=dict(rows=MAX_ROWS, status='limited', reason_visible=True))
    with isolated_settings():
        result = ci.run_gui(api, target, evidence, name='main-gui-directory-search', arguments=opened, exercise=exercise, log_prefix='directory-search')
        result.update(schema='ru-notepad-directory-search-gui-v1', fixture_binary_sha256=hashes, fixtures=inventory(),
                      engine_gates=list(ENGINE_GATES), disclosures=list(DISCLOSURES), progress=progress)
        if result['passed']:
            phase('close-running'); close_target = fixtures_dir / 'directory-close-runtime'; _copy_runtime(runtime, close_target, hashes); close_started = []
            def close_running(process, hwnd):
                api.command(hwnd, 851); api.command(hwnd, 301)
                set_text(api, api.control(hwnd, 310), 'missing-stress-needle')
                choose_folder(api, process, hwnd, root / 'stress')
                if not u.IsWindowEnabled(api.control(hwnd, STOP)) or tr('status_running') not in api.text(api.control(hwnd, SUMMARY)):
                    raise RuntimeError('Close-window fixture did not start a real directory job')
                close_started.append(time.perf_counter())
                return dict(running_seen=True)
            closed = ci.run_gui(api, close_target, evidence, name='main-gui-directory-close-running', exercise=close_running, log_prefix='directory-close')
            closed['fixture_binary_sha256'] = hashes
            closed['close_seconds'] = time.perf_counter() - close_started[0] if close_started else None
            result['close_running'] = closed
            if closed['passed'] and closed['close_seconds'] < RETIRE_SECONDS:
                result['checks']['close_running_normal_exit'] = True
            else:
                result['passed'] = False; result['error'] = 'Directory close-running phase failed or exceeded bound'
        if result['passed']:
            try: validate_result(result, hashes)
            except ValueError as exc: result['passed'] = False; result['error'] = str(exc)
        phase('complete' if result['passed'] else 'failed-' + progress.get('phase', 'startup'))
    return result
