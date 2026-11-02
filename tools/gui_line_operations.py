#!/usr/bin/env python3
"""Real application line commands, exact saves and fresh-process reopen.

Only synthetic fixtures; text mutation is exclusively through WM_COMMAND.
The portable validator is not a substitute for executing this gate on Windows.
"""
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import windows_ci as ci
from gui_instance_tabs import isolated_settings, _copy_runtime
from gui_fold_commands import activate_source, LARGE_BYTES
from gui_eol_conversion import save_and_verify

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ('en', 'zh-CN', 'ja', 'ko', 'es', 'ru', 'it')
COMMANDS = ((210, 'duplicate_lines'), (211, 'move_lines_up'),
            (212, 'move_lines_down'), (213, 'trim_line_ends'))
EOLS = (('crlf', b'\r\n', 0), ('lf', b'\n', 2), ('cr', b'\r', 1))
LINES = tuple(s.encode() for s in ('首 \t', '汉😀 \t', '中\u3000\t ', '尾 \t'))
CASE_CHECKS = ('command_exact', 'unicode_selection', 'no_implicit_save',
               'rejection_notice', 'undo_clean', 'redo', 'changed_save', 'undo_save', 'redo_save', 'fresh_reopen')
CHECKS = ('seven_localized_menus', 'large_mode_guard', 'tab_isolation', 'boundary_cases', 'readonly_guard', 'rectangular_selection_guard', 'seven_localized_rejections')


def matrix_case(command, eol_name, eol, mode, reverse):
    source = eol.join(LINES)
    a = len(LINES[0]) + len(eol) + 3  # inside line, immediately before emoji
    b = len(eol.join(LINES[:3])) + len(eol)  # next line start is excluded
    indices = {210: (0, 1, 2, 1, 2, 3), 211: (1, 2, 0, 3), 212: (0, 3, 1, 2)}
    target = eol.join(LINES[i] for i in indices[command]) if command != 213 else eol.join(
        line.rstrip(b' \t') if i in (1, 2) else line for i, line in enumerate(LINES))
    block = eol.join(LINES[1:3])
    selection = (b - 4, a) if reverse else (a, b - 4)
    if command != 213:
        begin = {210: len(eol.join(LINES[:3])) + len(eol), 211: 0,
                 212: len(eol.join((LINES[0], LINES[3]))) + len(eol)}[command]
        selection = (begin + len(block), begin) if reverse else (begin, begin + len(block))
    return dict(id=f'{command}-{eol_name}-'+('reverse' if reverse else 'forward'),
                command=command, source=source, target=target, anchor=b if reverse else a,
                caret=a if reverse else b, mode=mode, selection=selection)


CASES = tuple(matrix_case(command, name, eol, mode, reverse)
              for command, _ in COMMANDS for name, eol, mode in EOLS for reverse in (False, True))
# Boundaries are data, not computed using the implementation under test.
BOUNDARIES = (
    dict(id='first-up', command=211, source='汉😀\n尾'.encode(), target='汉😀\n尾'.encode(), anchor=0, caret=0, mode=2),
    dict(id='last-down', command=212, source='首\r\n尾😀'.encode(), target='首\r\n尾😀'.encode(), anchor=5, caret=5, mode=0),
    dict(id='empty-up', command=211, source=b'', target=b'', anchor=0, caret=0, mode=0),
    dict(id='empty-down', command=212, source=b'', target=b'', anchor=0, caret=0, mode=0),
    dict(id='empty-trim', command=213, source=b'', target=b'', anchor=0, caret=0, mode=0),
    dict(id='clean-trim', command=213, source='汉😀\u3000\r尾'.encode(), target='汉😀\u3000\r尾'.encode(), anchor=0, caret=0, mode=1),
    dict(id='current-trim', command=213, source='首 \t\n汉😀 \t\n尾 \t'.encode(), target='首 \t\n汉😀\n尾 \t'.encode(), anchor=6, caret=6, mode=2),
    dict(id='last-trim', command=213, source='首\r尾😀 \t'.encode(), target='首\r尾😀'.encode(), anchor=4, caret=4, mode=1),
)
BOUNDARIES += (
    dict(id='empty-duplicate', command=210, source=b'', target=b'', anchor=0, caret=0, mode=0),
    dict(id='last-duplicate', command=210, source='首\r尾😀'.encode(), target='首\r尾😀\r尾😀'.encode(), anchor=4, caret=4, mode=1),
    dict(id='single-duplicate', command=210, source='汉😀'.encode(), target='汉😀\r\n汉😀'.encode(), anchor=0, caret=0, mode=0),
    dict(id='empty-last-duplicate', command=210, source=b'a\n', target=b'a\n\n', anchor=2, caret=2, mode=2),
    dict(id='empty-last-up', command=211, source=b'a\n', target=b'a\n', anchor=2, caret=2, mode=2),
    dict(id='terminated-last-down', command=212, source=b'a\r\nb\r\n', target=b'a\r\nb\r\n', anchor=3, caret=3, mode=0),
    dict(id='last-up', command=211, source='首\r尾😀'.encode(), target='尾😀\r首'.encode(), anchor=4, caret=4, mode=1),
    dict(id='equal-content-down', command=212, source=b'a\na', target=b'a\na', anchor=0, caret=0, mode=2),
    dict(id='equal-empty-down', command=212, source=b'\n\nx', target=b'\n\nx', anchor=0, caret=0, mode=2),
    dict(id='mixed-up', command=211, source=b'a\r\nb\rc\nd', target=b'b\rc\r\na\nd', anchor=3, caret=7, mode=0),
    dict(id='mixed-down', command=212, source=b'a\r\nb\rc\nd', target=b'a\r\nd\nb\rc', anchor=3, caret=7, mode=0),
)
REJECTIONS = (
    dict(id='reject-crlf-move', command=211, source=b'\ra\nb', target=b'\ra\nb', anchor=1, caret=1, mode=2, expect_rejected=True),
    dict(id='reject-crlf-duplicate', command=210, source=b'\na\rz', target=b'\na\rz', anchor=0, caret=3, mode=2, expect_rejected=True),
    dict(id='reject-crlf-trim', command=213, source=b'\r \nb', target=b'\r \nb', anchor=1, caret=1, mode=2, expect_rejected=True),
)
ALL_CASES = tuple(dict(c, expect_rejected=c.get('expect_rejected', False)) for c in CASES + BOUNDARIES + REJECTIONS)


def detected_mode(data):
    return 0 if b'\r\n' in data else 2 if b'\n' in data else 1 if b'\r' in data else 0


def expected_cases():
    return [dict(id=c['id'], command=c['command'], expect_rejected=c['expect_rejected'], checks=dict.fromkeys(CASE_CHECKS, True)) for c in ALL_CASES]


def validate_result(record, hashes):
    if not isinstance(record, dict) or record.get('schema') != 'ru-notepad-line-operations-gui-v1':
        raise ValueError('Line GUI receipt identity differs')
    for row, name in ((record, 'main-gui-line-operations'), (record.get('reopen'), 'main-gui-line-reopen')):
        if not isinstance(row, dict) or row.get('name') != name: raise ValueError('Line GUI phase missing')
        for key, value in (('passed', True), ('executed', True), ('cleanup_killed', False),
                           ('main_hwnd_seen', True), ('close_posted', True), ('detached_from_console', True)):
            if row.get(key) is not value: raise ValueError('Line GUI lifecycle differs')
        if type(row.get('exit_code')) is not int or row['exit_code'] != 0 or row.get('error') or row.get('skips'):
            raise ValueError('Line GUI failed or skipped')
        if row.get('fixture_binary_sha256') != hashes: raise ValueError('Line GUI runtime differs')
    if record.get('languages') != list(LANGUAGES): raise ValueError('Line GUI languages differ')
    if record.get('checks') != dict.fromkeys(CHECKS, True) or any(v is not True for v in record['checks'].values()):
        raise ValueError('Line GUI global checks incomplete')
    if record.get('cases') != expected_cases(): raise ValueError('Line GUI case inventory incomplete')
    for row in record['cases']:
        if type(row.get('command')) is not int or type(row.get('expect_rejected')) is not bool or any(v is not True for v in row['checks'].values()):
            raise ValueError('Line GUI case types differ')
    return True


def run(api, binary_dir, fixtures, evidence):
    binary_dir, fixtures, evidence = map(Path, (binary_dir, fixtures, evidence))
    hashes = {n: ci.sha(binary_dir/n) for n in ci.portable.RUNTIME_NAMES}
    paths = []
    progress = [dict(id=c['id'], command=c['command'], expect_rejected=c['expect_rejected'], checks={}) for c in ALL_CASES]
    for case in ALL_CASES:
        path = fixtures/('lines-'+case['id']+'.txt')
        path.write_bytes(case['source']); paths.append(path)
    large = fixtures/'lines-large.txt'; large.write_bytes(b'a \t\r\n'+b'x'*(LARGE_BYTES-5))
    large_hash = ci.sha(large)
    opened = paths + [large]

    def loaded(process, hwnd, last):
        api.user.IsWindowEnabled.argtypes = [wintypes.HWND]; api.user.IsWindowEnabled.restype = wintypes.BOOL
        ci.wait_gui(api, process, lambda: api.text(hwnd) == last.name+' · ru_notepad' and
                    api.scalar(api.editor(hwnd), 2140) == 0 and
                    bool(api.user.IsWindowEnabled(api.control(hwnd, 10))) and
                    not api.user.IsWindowVisible(api.control(hwnd, 901)), 'Line CLI batch did not finish')

    def state(hwnd, expected, mode, dirty):
        editor = api.editor(hwnd)
        if api.editor_bytes(hwnd) != expected: raise RuntimeError('Line command exact text differs')
        if (api.scalar(editor, 2030), api.scalar(editor, 2159)) != (mode, dirty):
            raise RuntimeError('Line command Enter/savepoint differs')
        for message in (2008, 2009):
            position = api.scalar(editor, message)
            if not 0 <= position <= len(expected): raise RuntimeError('Line caret outside text')
            expected[:position].decode('utf-8')
        return editor

    def exercise(process, hwnd):
        loaded(process, hwnd, large)
        catalog = json.loads((ROOT/'locales/ui.json').read_text(encoding='utf-8'))
        u = api.user
        u.GetMenu.argtypes = [wintypes.HWND]; u.GetMenu.restype = ctypes.c_void_p
        u.GetMenuStringW.argtypes = [ctypes.c_void_p, ctypes.c_uint, wintypes.LPWSTR, ctypes.c_int, ctypes.c_uint]
        u.GetMenuStringW.restype = ctypes.c_int
        rejection = REJECTIONS[0]
        rejection_path = paths[len(CASES)+len(BOUNDARIES)]
        activate_source(api, hwnd, rejection_path, len(opened))
        for index, language in enumerate(LANGUAGES):
            api.command(hwnd, 851+index)
            for command, key in COMMANDS:
                buffer = ctypes.create_unicode_buffer(256)
                if not u.GetMenuStringW(u.GetMenu(hwnd), command, buffer, 256, 0): raise RuntimeError('Line menu missing')
                if buffer.value != catalog['command.'+key][language]: raise RuntimeError('Line menu translation differs')
            editor = api.editor(hwnd)
            api.scalar(editor, 2160, rejection['anchor'], rejection['caret'])
            api.command(hwnd, rejection['command'])
            state(hwnd, rejection['source'], rejection['mode'], 0)
            if api.scalar(editor, 2174): raise RuntimeError('Localized rejection introduced Undo')
            if catalog['lines.mixed_eol_rejected'][language] not in api.text(api.control(hwnd, 11)):
                raise RuntimeError('Localized line rejection missing')
            api.no_dialog(process.pid)
        api.command(hwnd, 851)
        for index, (path, case) in enumerate(zip(paths, ALL_CASES)):
            checks = progress[index]['checks']; source = case['source']; target = case['target']
            changed = int(source != target)
            activate_source(api, hwnd, path, len(opened)); editor = state(hwnd, source, case['mode'], 0)
            api.scalar(editor, 2160, case['anchor'], case['caret'])
            before = tuple(api.scalar(editor, m) for m in (2008, 2009, 2174))
            api.scalar(editor, 2422, 1)  # fixture setup only: rectangular selection is unsupported
            try:
                api.command(hwnd, case['command']); state(hwnd, source, case['mode'], 0)
                if before != tuple(api.scalar(editor, m) for m in (2008, 2009, 2174)):
                    raise RuntimeError('Line rectangular guard changed selection/Undo')
            finally:
                api.scalar(editor, 2422, 0)
                api.scalar(editor, 2160, case['anchor'], case['caret'])
            api.scalar(editor, 2171, 1)
            try:
                api.command(hwnd, case['command']); state(hwnd, source, case['mode'], 0)
                if before != tuple(api.scalar(editor, m) for m in (2008, 2009, 2174)):
                    raise RuntimeError('Line readonly guard changed selection/Undo')
            finally:
                api.scalar(editor, 2171, 0)
            api.command(hwnd, case['command']); state(hwnd, target, case['mode'], changed)
            if case.get('selection') is not None:
                actual = (api.scalar(editor, 2009), api.scalar(editor, 2008))
                if actual != case['selection']: raise RuntimeError('Line whole-block selection/direction differs')
            notice = catalog['lines.mixed_eol_rejected']['en'] in api.text(api.control(hwnd, 11))
            if notice is not case['expect_rejected']: raise RuntimeError('Line rejection/no-op feedback differs')
            api.no_dialog(process.pid)
            checks['rejection_notice'] = True
            checks['command_exact'] = checks['unicode_selection'] = True
            if path.read_bytes() != source: raise RuntimeError('Line command implicitly saved')
            checks['no_implicit_save'] = True
            if not changed:
                if api.scalar(editor, 2174): raise RuntimeError('Line no-op created Undo')
                if (api.scalar(editor, 2009), api.scalar(editor, 2008)) != (case['anchor'], case['caret']):
                    raise RuntimeError('Line no-op changed selection')
            api.command(hwnd, 201); state(hwnd, source, case['mode'], 0)
            if api.scalar(editor, 2174): raise RuntimeError('Line command was not one Undo group')
            checks['undo_clean'] = True
            api.command(hwnd, 202); state(hwnd, target, case['mode'], changed); checks['redo'] = True
            save_and_verify(api, process, hwnd, path, target); checks['changed_save'] = True
            api.command(hwnd, 201); state(hwnd, source, case['mode'], changed)
            save_and_verify(api, process, hwnd, path, source); checks['undo_save'] = True
            api.command(hwnd, 202); state(hwnd, target, case['mode'], changed)
            save_and_verify(api, process, hwnd, path, target); checks['redo_save'] = True
            print('Line command and three exact saves passed: '+case['id'], flush=True)
        activate_source(api, hwnd, large, len(opened)); editor = api.editor(hwnd)
        before = tuple(api.scalar(editor, m) for m in (2006, 2030, 2159, 2174, 2008, 2009))
        for command, _ in COMMANDS: api.command(hwnd, command)
        if before != tuple(api.scalar(editor, m) for m in (2006, 2030, 2159, 2174, 2008, 2009)):
            raise RuntimeError('Line large-file guard changed editor state')
        if ci.sha(large) != large_hash: raise RuntimeError('Line large source changed')
        return {'checks': dict.fromkeys(CHECKS, True), 'languages': list(LANGUAGES)}

    def reopen(process, hwnd):
        loaded(process, hwnd, paths[-1])
        for index, (path, case) in enumerate(zip(paths, ALL_CASES)):
            activate_source(api, hwnd, path, len(paths)); state(hwnd, case['target'], detected_mode(case['target']), 0)
            if path.read_bytes() != case['target']: raise RuntimeError('Line reopen disk bytes differ')
            progress[index]['checks']['fresh_reopen'] = True
            print('Line fresh-process reopen passed: '+case['id'], flush=True)
        return {}

    target = fixtures/'line-runtime'; _copy_runtime(binary_dir, target, hashes)
    with isolated_settings():
        result = ci.run_gui(api, target, evidence, name='main-gui-line-operations', arguments=opened, exercise=exercise, log_prefix='line-operations')
        result.update(schema='ru-notepad-line-operations-gui-v1', fixture_binary_sha256=hashes, cases=progress)
        if result['passed']:
            target = fixtures/'line-reopen-runtime'; _copy_runtime(binary_dir, target, hashes)
            result['reopen'] = ci.run_gui(api, target, evidence, name='main-gui-line-reopen', arguments=paths, exercise=reopen, log_prefix='line-reopen')
            result['reopen']['fixture_binary_sha256'] = hashes
            if result['reopen']['passed']: validate_result(result, hashes)
            else:
                result['passed'] = False
                result['error'] = 'Line fresh-process reopen failed; see nested receipt'
    return result
