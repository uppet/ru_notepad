#!/usr/bin/env python3
"""Actual WM_COMMAND conversion/save/reopen, bounded scalar-only observations.

All files are synthetic. No direct SCI_CONVERTEOLS/SETEOLMODE is substituted
for commands. Save writes are examined byte-for-byte outside the editor.
"""
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import windows_ci as ci
from gui_instance_tabs import isolated_settings, _copy_runtime
from gui_fold_commands import activate_source, LARGE_BYTES

ROOT = Path(__file__).resolve().parents[1]
MODES = ((207, 0, b'\r\n'), (208, 2, b'\n'), (209, 1, b'\r'))
MIXED = '汉😀\r\nb\rc\n尾'.encode()
ENCODINGS = (('utf8', 'utf-8', b'', 'UTF-8'),
             ('utf8bom', 'utf-8', b'\xef\xbb\xbf', 'UTF-8 BOM'),
             ('utf16le', 'utf-16-le', b'\xff\xfe', 'UTF-16 LE'),
             ('utf16be', 'utf-16-be', b'\xfe\xff', 'UTF-16 BE'))
CHECKS = ('all_modes_exact', 'single_undo_redo', 'clean_savepoint', 'enter_independent',
          'forward_reverse_selection', 'unicode_caret_boundaries', 'no_implicit_save',
          'converted_save_bytes', 'undo_save_bytes', 'redo_save_bytes', 'encoding_status',
          'line_eol_status', 'no_final_newline', 'tab_isolation', 'noops',
          'large_mode_guard', 'seven_localized_menus', 'reopen_bytes_encoding_mode')
LANGUAGES = ('en', 'zh-CN', 'ja', 'ko', 'es', 'ru', 'it')
CASES = tuple((name, codec, bom, label, command, mode, eol, reverse)
              for name, codec, bom, label in ENCODINGS
              for command, mode, eol in MODES for reverse in (False, True))
CASE_CHECKS = ('conversion_selection', 'undo_clean', 'redo', 'converted_save',
               'undo_save', 'redo_save', 'fresh_reopen')


def case_identity(case):
    name, _, _, _, command, mode, _, reverse = case
    return {'encoding': name, 'command': command, 'mode': mode, 'reverse': reverse}


def expected_cases():
    return [dict(case_identity(case), checks=dict.fromkeys(CASE_CHECKS, True)) for case in CASES]


def save_ready(api, hwnd):
    # Never inspect a file while the asynchronous writer may own its handle.
    editor = api.editor(hwnd)
    return (api.scalar(editor, 2140) == 0 and
            bool(api.user.IsWindowEnabled(api.control(hwnd, 10))) and
            not api.user.IsWindowVisible(api.control(hwnd, 901)) and
            api.scalar(editor, 2159) == 0)


def save_and_verify(api, process, hwnd, path, expected):
    api.command(hwnd, 103)
    ci.wait_gui(api, process, lambda: save_ready(api, hwnd), 'EOL save did not finish and unlock')
    # A single final read; permission errors and wrong bytes remain fatal.
    if path.read_bytes() != expected:
        raise RuntimeError('EOL completed save has incorrect disk bytes')
    api.responsive(hwnd)


def converted(data, eol):
    return data.replace(b'\r\n', b'\n').replace(b'\r', b'\n').replace(b'\n', eol)


def encoded(data, codec, bom):
    return bom + data.decode('utf-8').encode(codec)


def validate_result(record, hashes):
    if not isinstance(record, dict) or record.get('schema') != 'ru-notepad-eol-gui-v1':
        raise ValueError('EOL GUI receipt missing or wrong schema')
    for row, name in ((record, 'main-gui-eol-conversion'), (record.get('reopen'), 'main-gui-eol-reopen')):
        if not isinstance(row, dict) or row.get('name') != name: raise ValueError('EOL GUI phase missing')
        for key, value in (('passed', True), ('executed', True), ('cleanup_killed', False),
                           ('main_hwnd_seen', True), ('close_posted', True), ('detached_from_console', True)):
            if row.get(key) is not value: raise ValueError('EOL GUI lifecycle differs')
        if type(row.get('exit_code')) is not int or row['exit_code'] != 0 or row.get('error') or row.get('skips'):
            raise ValueError('EOL GUI failed or skipped')
        if row.get('fixture_binary_sha256') != hashes: raise ValueError('EOL runtime differs')
    if record.get('checks') != dict.fromkeys(CHECKS, True) or any(v is not True for v in record['checks'].values()):
        raise ValueError('EOL check inventory differs')
    if record.get('encodings') != [r[0] for r in ENCODINGS] or record.get('languages') != list(LANGUAGES):
        raise ValueError('EOL encoding/language inventory differs')
    if record.get('cases') != expected_cases(): raise ValueError('EOL exact 24-case matrix incomplete')
    for row in record['cases']:
        if type(row.get('command')) is not int or type(row.get('mode')) is not int or type(row.get('reverse')) is not bool:
            raise ValueError('EOL case identity types differ')
        if any(v is not True for v in row['checks'].values()): raise ValueError('EOL case check not boolean')
    return True


def run(api, binary_dir, fixtures, evidence):
    binary_dir, fixtures, evidence = map(Path, (binary_dir, fixtures, evidence))
    hashes = {n: ci.sha(binary_dir/n) for n in ci.portable.RUNTIME_NAMES}
    paths = []
    progress = [dict(case_identity(case), checks={}) for case in CASES]
    for case in CASES:
        name, codec, bom, _, command, _, _, reverse = case
        path = fixtures/('eol-'+name+'-'+str(command)+('-reverse' if reverse else '-forward')+'.txt')
        path.write_bytes(encoded(MIXED, codec, bom)); paths.append(path)
    noop_data = (b'', '汉😀'.encode(), b'a\nb\n')
    noops = []
    for i, data in enumerate(noop_data):
        path = fixtures/('eol-noop-'+str(i)+'.txt'); path.write_bytes(data); noops.append(path)
    large = fixtures/'eol-large.txt'; large.write_bytes(b'a\r\n'+b'x'*(LARGE_BYTES-3))
    large_hash = ci.sha(large)
    opened = paths + noops + [large]

    def wait_loaded(process, hwnd, last):
        api.user.IsWindowEnabled.argtypes = [wintypes.HWND]; api.user.IsWindowEnabled.restype = wintypes.BOOL
        ci.wait_gui(api, process, lambda: api.text(hwnd) == last.name+' · ru_notepad' and
                    api.scalar(api.editor(hwnd), 2140) == 0 and
                    api.user.IsWindowEnabled(api.control(hwnd, 10)) and
                    not api.user.IsWindowVisible(api.control(hwnd, 901)), 'EOL CLI batch did not finish')

    def state(hwnd, expected, mode, dirty):
        editor = api.editor(hwnd)
        if api.editor_bytes(hwnd) != expected: raise RuntimeError('EOL exact text differs')
        if (api.scalar(editor, 2030), api.scalar(editor, 2159)) != (mode, dirty):
            raise RuntimeError('EOL Enter/savepoint differs')
        for message in (2008, 2009):
            position = api.scalar(editor, message)
            if not 0 <= position <= len(expected): raise RuntimeError('EOL caret outside text')
            expected[:position].decode('utf-8')  # caret must not split a Unicode codepoint
        return editor

    def exercise(process, hwnd):
        wait_loaded(process, hwnd, large)
        api.command(hwnd, 851)  # English status assertions; isolated settings restored afterwards.
        catalog = json.loads((ROOT/'locales/ui.json').read_text(encoding='utf-8'))
        u = api.user
        u.GetMenu.argtypes = [wintypes.HWND]; u.GetMenu.restype = ctypes.c_void_p
        u.GetMenuStringW.argtypes = [ctypes.c_void_p, ctypes.c_uint, wintypes.LPWSTR, ctypes.c_int, ctypes.c_uint]
        u.GetMenuStringW.restype = ctypes.c_int
        u.GetMenuState.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint]; u.GetMenuState.restype = ctypes.c_uint
        for index, language in enumerate(LANGUAGES):
            api.command(hwnd, 851+index)
            for command, key in ((207, 'crlf'), (208, 'lf'), (209, 'cr')):
                buffer = ctypes.create_unicode_buffer(256)
                if not u.GetMenuStringW(u.GetMenu(hwnd), command, buffer, 256, 0): raise RuntimeError('Missing EOL menu')
                if buffer.value != catalog['command.eol_'+key][language]: raise RuntimeError('EOL menu translation differs')
                if u.GetMenuState(u.GetMenu(hwnd), command, 0) & 8: raise RuntimeError('EOL command falsely asserts uniform document state')
        api.command(hwnd, 851)
        for index, (path, case) in enumerate(zip(paths, CASES)):
            name, codec, bom, status_encoding, command, mode, eol, reverse = case
            checks = progress[index]['checks']
            activate_source(api, hwnd, path, len(opened)); editor = state(hwnd, MIXED, 0, 0)
            original = path.read_bytes(); target = converted(MIXED, eol)
            start, end = 3, len(MIXED)-3  # emoji and last Han character boundaries
            anchor, caret = (end, start) if reverse else (start, end)
            api.scalar(editor, 2160, anchor, caret)
            api.command(hwnd, command); state(hwnd, target, mode, 1)
            actual = (api.scalar(editor, 2009), api.scalar(editor, 2008))
            expected = tuple(len(converted(MIXED[:p], eol)) for p in (anchor, caret))
            if actual != expected: raise RuntimeError('EOL selection lost text positions/direction')
            if path.read_bytes() != original: raise RuntimeError('EOL command implicitly saved')
            checks['conversion_selection'] = True
            api.command(hwnd, 201); state(hwnd, MIXED, mode, 0)
            if api.scalar(editor, 2174) != 0: raise RuntimeError('EOL conversion not one Undo group')
            checks['undo_clean'] = True
            api.command(hwnd, 202); state(hwnd, target, mode, 1); checks['redo'] = True
            eol_label = {0:'CRLF', 1:'CR', 2:'LF'}[mode]
            api.scalar(editor, 2160, 0, 0)
            ci.wait_gui(api, process, lambda: ('Line EOL: '+eol_label) in api.text(api.control(hwnd, 11)) and
                        ('Enter: '+eol_label) in api.text(api.control(hwnd, 11)), 'Converted status did not settle')
            if status_encoding not in api.text(api.control(hwnd, 11)): raise RuntimeError('Converted encoding status differs')
            save_and_verify(api, process, hwnd, path, encoded(target, codec, bom))
            checks['converted_save'] = True
            api.command(hwnd, 201); state(hwnd, MIXED, mode, 1)
            api.scalar(editor, 2160, 0, 0)
            ci.wait_gui(api, process, lambda: 'Line EOL: CRLF' in api.text(api.control(hwnd, 11)) and
                        ('Enter: '+eol_label) in api.text(api.control(hwnd, 11)), 'Undo status did not settle')
            save_and_verify(api, process, hwnd, path, original); checks['undo_save'] = True
            api.command(hwnd, 202); state(hwnd, target, mode, 1)
            save_and_verify(api, process, hwnd, path, encoded(target, codec, bom)); checks['redo_save'] = True
            print('EOL conversion and three exact saves passed: '+path.stem, flush=True)
        for path, data in zip(noops, noop_data):
            activate_source(api, hwnd, path, len(opened)); editor = api.editor(hwnd)
            api.command(hwnd, 208); state(hwnd, data, 2, 0)
            if api.scalar(editor, 2174) or path.read_bytes() != data: raise RuntimeError('EOL no-op introduced Undo/save')
        activate_source(api, hwnd, large, len(opened)); editor = api.editor(hwnd)
        for command, _, _ in MODES: api.command(hwnd, command)
        if tuple(api.scalar(editor, m) for m in (2006, 2030, 2159, 2174)) != (LARGE_BYTES, 0, 0, 0):
            raise RuntimeError('EOL large-file guard changed state')
        if ci.sha(large) != large_hash: raise RuntimeError('EOL large source changed')
        return {'checks': dict.fromkeys(CHECKS[:-1], True), 'encodings': [r[0] for r in ENCODINGS], 'languages': list(LANGUAGES)}

    def reopen(process, hwnd):
        wait_loaded(process, hwnd, paths[-1]); api.command(hwnd, 851)
        for index, (path, case) in enumerate(zip(paths, CASES)):
            _, codec, bom, status_encoding, _, mode, eol, _ = case
            activate_source(api, hwnd, path, len(paths)); expected = converted(MIXED, eol)
            state(hwnd, expected, mode, 0)
            if path.read_bytes() != encoded(expected, codec, bom): raise RuntimeError('Reopen disk bytes differ')
            if status_encoding not in api.text(api.control(hwnd, 11)): raise RuntimeError('Reopen encoding/BOM differs')
            progress[index]['checks']['fresh_reopen'] = True
            print('EOL fresh-process reopen passed: '+path.stem, flush=True)
        return {}

    target = fixtures/'eol-runtime'; _copy_runtime(binary_dir, target, hashes)
    with isolated_settings():
        result = ci.run_gui(api, target, evidence, name='main-gui-eol-conversion', arguments=opened, exercise=exercise, log_prefix='eol-conversion')
        result.update(schema='ru-notepad-eol-gui-v1', fixture_binary_sha256=hashes, cases=progress)
        if result['passed']:
            target = fixtures/'eol-reopen-runtime'; _copy_runtime(binary_dir, target, hashes)
            result['reopen'] = ci.run_gui(api, target, evidence, name='main-gui-eol-reopen', arguments=paths, exercise=reopen, log_prefix='eol-reopen')
            result['reopen']['fixture_binary_sha256'] = hashes
            if result['reopen']['passed']:
                result['checks'][CHECKS[-1]] = True
                validate_result(result, hashes)
            else:
                result['passed'] = False
                result['error'] = 'EOL fresh-process reopen phase failed; see nested receipt'
    return result
