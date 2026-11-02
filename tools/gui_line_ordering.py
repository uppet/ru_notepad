#!/usr/bin/env python3
"""Real application line commands, exact saves and fresh-process reopen.

Only synthetic fixtures; text mutation is exclusively through WM_COMMAND.
The portable validator is not a substitute for executing this gate on Windows.
"""
import ctypes
import functools
import hashlib
from ctypes import wintypes
import json
from pathlib import Path
import windows_ci as ci
from gui_instance_tabs import isolated_settings, _copy_runtime
from gui_fold_commands import activate_source, LARGE_BYTES
from gui_eol_conversion import save_and_verify

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ('en', 'zh-CN', 'ja', 'ko', 'es', 'ru', 'it')
COMMANDS = ((214, 'sort_selected_ascending'), (215, 'sort_selected_descending'),
            (216, 'deduplicate_selected_lines'), (217, 'sort_all_ascending'),
            (218, 'sort_all_descending'), (219, 'deduplicate_all_lines'))
EOLS = (('crlf', b'\r\n', 0), ('lf', b'\n', 2), ('cr', b'\r', 1))
LINES = tuple(s.encode() for s in ('z😀', 'A', 'e\u0301', 'é', 'z😀', '汉'))
CASE_CHECKS = ('command_exact', 'unicode_selection', 'no_implicit_save',
               'rejection_notice', 'undo_clean', 'redo', 'changed_save', 'undo_save', 'redo_save', 'fresh_reopen')
CHECKS = ('seven_localized_menus', 'large_mode_guard', 'tab_isolation', 'boundary_cases',
          'readonly_guard', 'rectangular_selection_guard', 'multiple_selection_guard',
          'seven_localized_rejections', 'no_selection_disabled', 'selection_enabled', 'seven_localized_resource_rejections')


def matrix_case(command, eol_name, eol, mode, reverse):
    selected = command < 217
    operation = (command-214) % 3
    indices = ((1, 2, 0, 4, 3, 5), (5, 3, 0, 4, 2, 1), (0, 1, 2, 3, 5))[operation]
    prefix = '外'.encode()+eol if selected else b''
    suffix = '尾'.encode() if selected else b''
    source = prefix+eol.join(LINES)+eol+suffix
    content = eol.join(LINES[i] for i in indices)
    target = prefix+content+eol+suffix
    a, b = (len(prefix)+1, len(source)-len(suffix)) if selected else (0, len(source))
    if not selected and not reverse: a=b=0
    selection = (len(prefix), len(prefix)+len(content))
    if reverse: selection=selection[::-1]
    return dict(id=f'{command}-{eol_name}-'+('reverse' if reverse else 'forward'),
                command=command, source=source, target=target, anchor=b if reverse else a,
                caret=a if reverse else b, mode=mode, selection=selection)


CASES = tuple(matrix_case(command, name, eol, mode, reverse)
              for command, _ in COMMANDS for name, eol, mode in EOLS for reverse in (False, True))

def case(name, command, source, target=None, anchor=0, caret=0, rejected=False):
    selection = None
    if target is not None and target != source and command >= 217:
        final_eol = 2 if target.endswith(b'\r\n') else 1 if target.endswith((b'\r', b'\n')) else 0
        selection = (0, len(target)-final_eol)
        if caret < anchor: selection = selection[::-1]
    if name == 'selected-mixed-dedup-boundary': selection = (2,5)
    if name == 'selected-excludes-virtual': selection = (0,3)
    return dict(id=name, command=command, source=source, target=source if target is None else target,
                selection=selection, anchor=anchor, caret=caret, mode=0 if b'\r\n' in source else 2 if b'\n' in source else 1 if b'\r' in source else 0,
                expect_rejected=rejected)

# Explicit independent byte expectations, not the application algorithm.
BOUNDARIES = (
    *(case('no-selection-'+str(c), c, b'b\na') for c in (214,215,216)),
    *(case('empty-'+str(c), c, b'') for c in (217,218,219)),
    case('already-ascending',217,b'A\na\nz\n'),
    case('already-descending',218,b'z\na\nA'),
    case('already-unique',219,b'z\na\nA'),
    *(case('single-'+str(c), c, '汉😀'.encode()) for c in (217,218,219)),
    case('mixed-sort-up',217,b'c\ra\nb\r\n',b'a\rb\nc\r\n'),
    case('mixed-sort-down',218,b'a\rc\nb',b'c\rb\na'),
    case('mixed-dedup-terminated',219,b'b\ra\nb\r\nc\ra\n',b'b\ra\nc\n'),
    case('mixed-dedup-unterminated',219,b'b\ra\nb\r\na',b'b\ra'),
    case('empty-entities-sort',217,b'z\n\n\n',b'\n\nz\n'),
    case('empty-entities-dedup',219,b'\n\n',b'\n'),
    case('terminal-virtual-only',219,b'\n'),
    case('codepoint-not-natural',217,b'a2\na10\nA\na',b'A\na\na10\na2'),
    case('selected-mixed-dedup-boundary',216,b'P\ra\nb\ra\r\nQ',b'P\ra\nb\r\nQ',2,9),
    case('selected-excludes-virtual',214,b'b\na\n',b'a\nb\n',0,4),
    case('combining-not-normalized',219,'é\né\né'.encode(),'é\né'.encode()),
)
REJECTIONS = (
    case('reject-ascending-crlf-fusion',217,b'z\rx\n\n\n',rejected=True),
    case('reject-descending-crlf-fusion',218,b'\nx\rz\n',rejected=True),
    case('reject-dedup-crlf-fusion',219,b'a\r\ra\n',rejected=True),
)
ALL_CASES = tuple(dict(c, expect_rejected=c.get('expect_rejected', False)) for c in CASES + BOUNDARIES + REJECTIONS)


def detected_mode(data):
    return 0 if b'\r\n' in data else 2 if b'\n' in data else 1 if b'\r' in data else 0


def expected_cases():
    return [dict(id=c['id'], command=c['command'], expect_rejected=c['expect_rejected'], checks=dict.fromkeys(CASE_CHECKS, True)) for c in ALL_CASES]


def validate_result(record, hashes):
    if not isinstance(record, dict) or record.get('schema') != 'ru-notepad-line-ordering-gui-v1':
        raise ValueError('Ordering GUI receipt identity differs')
    for row, name in ((record, 'main-gui-line-ordering'), (record.get('reopen'), 'main-gui-ordering-reopen')):
        if not isinstance(row, dict) or row.get('name') != name: raise ValueError('Ordering GUI phase missing')
        for key, value in (('passed', True), ('executed', True), ('cleanup_killed', False),
                           ('main_hwnd_seen', True), ('close_posted', True), ('detached_from_console', True)):
            if row.get(key) is not value: raise ValueError('Ordering GUI lifecycle differs')
        if type(row.get('exit_code')) is not int or row['exit_code'] != 0 or row.get('error') or row.get('skips'):
            raise ValueError('Ordering GUI failed or skipped')
        if row.get('fixture_binary_sha256') != hashes: raise ValueError('Ordering GUI runtime differs')
    if record.get('languages') != list(LANGUAGES): raise ValueError('Ordering GUI languages differ')
    if record.get('checks') != dict.fromkeys(CHECKS, True) or any(v is not True for v in record['checks'].values()):
        raise ValueError('Ordering GUI global checks incomplete')
    if record.get('cases') != expected_cases(): raise ValueError('Ordering GUI case inventory incomplete')
    for row in record['cases']:
        if type(row.get('command')) is not int or type(row.get('expect_rejected')) is not bool or any(v is not True for v in row['checks'].values()):
            raise ValueError('Ordering GUI case types differ')
    validate_resources(record.get('resources'))
    return True

ROW_LIMIT = 10000
BYTE_LIMIT = 4194304
RESOURCE_CHECKS = ('exact_bytes', 'notice', 'selection', 'dirty_undo', 'one_undo_redo', 'disk_unchanged')
RESOURCE_IDS = ('over-row-limit', 'over-byte-limit', 'at-row-limit-sort', 'at-row-limit-dedup', 'at-byte-limit-prefix-sort')


@functools.cache
def resource_cases():
    rows=b'b\n'*(ROW_LIMIT//2)+b'a\n'*(ROW_LIMIT//2)
    unique=b''.join(f'{i:05d}\n'.encode() for i in range(ROW_LIMIT-1,-1,-1))
    ascending=b''.join(f'{i:05d}\n'.encode() for i in range(ROW_LIMIT))
    prefix=b'x'*(BYTE_LIMIT//2-2)
    return (
        ('over-row-limit',217,b'a\n'*(ROW_LIMIT+1),None),
        ('over-byte-limit',217,b'b\n'+b'a'*(BYTE_LIMIT-1),None),
        ('at-row-limit-sort',217,unique,ascending),
        ('at-row-limit-dedup',219,rows,b'b\na\n'),
        ('at-byte-limit-prefix-sort',217,prefix+b'b\n'+prefix+b'a\n',prefix+b'a\n'+prefix+b'b\n'),
    )


def _fixture_buffer(api, process, hwnd, data=None):
    """Bounded remote storage for setup/readback, never the command under test.

    No process-local pointers are passed to private Scintilla messages. A timed
    out send leaves storage process-owned until the harness terminates it.
    """
    editor=api.editor(hwnd); api.verify_owned_handles(process.pid,editor)
    k=api.kernel
    k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]; k.OpenProcess.restype=wintypes.HANDLE
    k.VirtualAllocEx.argtypes=[wintypes.HANDLE,ctypes.c_void_p,ctypes.c_size_t,wintypes.DWORD,wintypes.DWORD]; k.VirtualAllocEx.restype=ctypes.c_void_p
    for name in ('ReadProcessMemory','WriteProcessMemory'):
        fn=getattr(k,name); fn.argtypes=[wintypes.HANDLE,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)]; fn.restype=wintypes.BOOL
    k.VirtualFreeEx.argtypes=[wintypes.HANDLE,ctypes.c_void_p,ctypes.c_size_t,wintypes.DWORD]; k.VirtualFreeEx.restype=wintypes.BOOL
    k.CloseHandle.argtypes=[wintypes.HANDLE]; k.CloseHandle.restype=wintypes.BOOL
    size=(len(data) if data is not None else api.scalar(editor,2006))+1
    if not 1 <= size <= BYTE_LIMIT+2: raise RuntimeError('Resource fixture remote buffer exceeds bound')
    handle=k.OpenProcess(0x8|0x10|0x20,False,process.pid)
    if not handle: raise ctypes.WinError(ctypes.get_last_error())
    remote=None; completed=False
    try:
        remote=k.VirtualAllocEx(handle,None,size,0x3000,4)
        if not remote: raise ctypes.WinError(ctypes.get_last_error())
        buffer=ctypes.create_string_buffer(size); copied=ctypes.c_size_t()
        if data is not None:
            buffer.raw=data+b'\0'
            if not k.WriteProcessMemory(handle,remote,buffer,size,ctypes.byref(copied)) or copied.value != size:
                raise RuntimeError('Resource fixture setup write incomplete')
            api.scalar(editor,2181,0,remote)  # SCI_SETTEXT: fixture setup only
            completed=True
            api.scalar(editor,2175)  # clear setup undo
            api.scalar(editor,2014)  # independent clean savepoint, no disk write
            api.scalar(editor,2160,0,0)
        else:
            if api.scalar(editor,2182,size,remote) != size-1: raise RuntimeError('Resource fixture read length differs')
            completed=True
            if not k.ReadProcessMemory(handle,remote,buffer,size,ctypes.byref(copied)) or copied.value != size:
                raise RuntimeError('Resource fixture read incomplete')
            return buffer.raw[:-1]
    finally:
        if remote and completed: k.VirtualFreeEx(handle,remote,0,0x8000)
        k.CloseHandle(handle)


def run_resources(api, process, hwnd, catalog, path):
    import time
    disk=path.read_bytes(); rows=[]
    editor=api.editor(hwnd)
    try:
        for name,command,source,target in resource_cases():
            _fixture_buffer(api,process,hwnd,source)
            if _fixture_buffer(api,process,hwnd) != source:
                raise RuntimeError('Resource fixture seeded bytes differ')
            before=tuple(api.scalar(editor,m) for m in (2008,2009,2159,2174,2030))
            started=time.perf_counter(); api.command(hwnd,command); duration=time.perf_counter()-started
            if duration >= 5: raise RuntimeError('Ordering resource command exceeded 5-second budget')
            expected=source if target is None else target
            if _fixture_buffer(api,process,hwnd) != expected: raise RuntimeError('Ordering resource bytes differ')
            notice=catalog['lines.ordering_limit']['en'] in api.text(api.control(hwnd,11))
            if notice != (target is None): raise RuntimeError('Ordering resource notice differs')
            if target is None:
                if before != tuple(api.scalar(editor,m) for m in (2008,2009,2159,2174,2030)):
                    raise RuntimeError('Ordering resource rejection changed state')
            else:
                final_eol=2 if target.endswith(b'\r\n') else 1 if target.endswith((b'\n',b'\r')) else 0
                if tuple(api.scalar(editor,m) for m in (2009,2008,2159,2174)) != (0,len(target)-final_eol,1,1):
                    raise RuntimeError('Ordering resource selection/savepoint/Undo differs')
                api.command(hwnd,201)
                if _fixture_buffer(api,process,hwnd) != source or api.scalar(editor,2174) or api.scalar(editor,2159):
                    raise RuntimeError('Ordering resource one-step Undo differs')
                api.command(hwnd,202)
                if _fixture_buffer(api,process,hwnd) != target: raise RuntimeError('Ordering resource Redo differs')
            if path.read_bytes() != disk: raise RuntimeError('Ordering resource operation implicitly saved')
            rows.append(dict(id=name,command=command,source_bytes=len(source),source_sha256=hashlib.sha256(source).hexdigest(),
                             result_sha256=hashlib.sha256(expected).hexdigest(),duration_seconds=duration,checks=dict.fromkeys(RESOURCE_CHECKS,True)))
        for index,language in enumerate(LANGUAGES):
            _fixture_buffer(api,process,hwnd,b'a\n'*(ROW_LIMIT+1))
            api.command(hwnd,851+index); api.command(hwnd,217)
            if catalog['lines.ordering_limit'][language] not in api.text(api.control(hwnd,11)):
                raise RuntimeError('Localized ordering resource notice missing')
            if api.scalar(editor,2159) or api.scalar(editor,2174): raise RuntimeError('Localized resource guard mutated document')
            api.no_dialog(process.pid)
        return rows
    finally:
        api.command(hwnd,851)
        _fixture_buffer(api,process,hwnd,disk)


@functools.cache
def expected_resources():
    return tuple(dict(id=name,command=command,source_bytes=len(source),source_sha256=hashlib.sha256(source).hexdigest(),
                      result_sha256=hashlib.sha256(source if target is None else target).hexdigest(),
                      checks=dict.fromkeys(RESOURCE_CHECKS,True)) for name,command,source,target in resource_cases())


def validate_resources(rows):
    import math
    if not isinstance(rows,list) or len(rows)!=len(RESOURCE_IDS): raise ValueError('Ordering resource cases missing')
    for row,expected in zip(rows,expected_resources()):
        if not isinstance(row,dict) or set(row)!=set(expected)|{'duration_seconds'}: raise ValueError('Ordering resource fields differ')
        if any(row[k]!=v for k,v in expected.items()) or any(v is not True for v in row['checks'].values()):
            raise ValueError('Ordering resource evidence differs')
        if type(row['command']) is not int or type(row['source_bytes']) is not int: raise ValueError('Ordering resource field type differs')
        duration=row['duration_seconds']
        if type(duration) not in (int,float) or not math.isfinite(duration) or not 0 <= duration < 5:
            raise ValueError('Ordering resource 5-second budget not met')
    return True


def run(api, binary_dir, fixtures, evidence):
    binary_dir, fixtures, evidence = map(Path, (binary_dir, fixtures, evidence))
    hashes = {n: ci.sha(binary_dir/n) for n in ci.portable.RUNTIME_NAMES}
    paths = []
    progress = [dict(id=c['id'], command=c['command'], expect_rejected=c['expect_rejected'], checks={}) for c in ALL_CASES]
    for case in ALL_CASES:
        path = fixtures/('ordering-'+case['id']+'.txt')
        path.write_bytes(case['source']); paths.append(path)
    large = fixtures/'ordering-large.txt'; large.write_bytes(b'a \t\r\n'+b'x'*(LARGE_BYTES-5))
    large_hash = ci.sha(large)
    opened = paths + [large]

    def loaded(process, hwnd, last):
        api.user.IsWindowEnabled.argtypes = [wintypes.HWND]; api.user.IsWindowEnabled.restype = wintypes.BOOL
        ci.wait_gui(api, process, lambda: api.text(hwnd) == last.name+' · ru_notepad' and
                    api.scalar(api.editor(hwnd), 2140) == 0 and
                    bool(api.user.IsWindowEnabled(api.control(hwnd, 10))) and
                    not api.user.IsWindowVisible(api.control(hwnd, 901)), 'Ordering CLI batch did not finish')

    def state(hwnd, expected, mode, dirty):
        editor = api.editor(hwnd)
        if api.editor_bytes(hwnd) != expected: raise RuntimeError('Ordering command exact text differs')
        if (api.scalar(editor, 2030), api.scalar(editor, 2159)) != (mode, dirty):
            raise RuntimeError('Ordering command Enter/savepoint differs')
        for message in (2008, 2009):
            position = api.scalar(editor, message)
            if not 0 <= position <= len(expected): raise RuntimeError('Ordering caret outside text')
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
                if not u.GetMenuStringW(u.GetMenu(hwnd), command, buffer, 256, 0): raise RuntimeError('Ordering menu missing')
                if buffer.value != catalog['command.'+key][language]: raise RuntimeError('Ordering menu translation differs')
            editor = api.editor(hwnd)
            api.scalar(editor, 2160, rejection['anchor'], rejection['caret'])
            api.command(hwnd, rejection['command'])
            state(hwnd, rejection['source'], rejection['mode'], 0)
            if api.scalar(editor, 2174): raise RuntimeError('Localized rejection introduced Undo')
            if catalog['lines.mixed_eol_rejected'][language] not in api.text(api.control(hwnd, 11)):
                raise RuntimeError('Localized line rejection missing')
            api.no_dialog(process.pid)
        api.command(hwnd, 851)
        u.GetMenuState.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint]
        u.GetMenuState.restype = ctypes.c_uint
        editor=api.editor(hwnd)
        api.scalar(editor,2160,0,0)
        # WM_INITMENUPOPUP refreshes enable states without mutating the document.
        api.scalar(hwnd,279,u.GetMenu(hwnd),0)
        for command in (214,215,216):
            if not (u.GetMenuState(u.GetMenu(hwnd),command,0)&3):
                raise RuntimeError('Selected-line command enabled without selection')
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
                    raise RuntimeError('Ordering rectangular guard changed selection/Undo')
            finally:
                api.scalar(editor, 2422, 0)
                api.scalar(editor, 2160, case['anchor'], case['caret'])
            if source:
                api.scalar(editor,2160,0,0)
                api.scalar(editor,2573,len(source),len(source))  # distinct UTF-8-safe carets, setup only
                if api.scalar(editor,2570) != 2:
                    raise RuntimeError('Ordering multiple-selection fixture setup failed')
                multiple_before=tuple(api.scalar(editor,m) for m in (2008,2009,2174,2570))
                try:
                    api.command(hwnd,case['command']); state(hwnd,source,case['mode'],0)
                    if multiple_before != tuple(api.scalar(editor,m) for m in (2008,2009,2174,2570)):
                        raise RuntimeError('Ordering multiple-selection guard changed state')
                finally:
                    api.scalar(editor,2571)
                    api.scalar(editor,2160,case['anchor'],case['caret'])
            if case['command'] < 217 and case['anchor'] != case['caret']:
                api.scalar(hwnd,279,u.GetMenu(hwnd),0)
                if u.GetMenuState(u.GetMenu(hwnd),case['command'],0)&3:
                    raise RuntimeError('Selected-line command disabled with stream selection')
            api.scalar(editor, 2171, 1)
            try:
                api.command(hwnd, case['command']); state(hwnd, source, case['mode'], 0)
                if before != tuple(api.scalar(editor, m) for m in (2008, 2009, 2174)):
                    raise RuntimeError('Ordering readonly guard changed selection/Undo')
            finally:
                api.scalar(editor, 2171, 0)
            api.command(hwnd, case['command']); state(hwnd, target, case['mode'], changed)
            if case.get('selection') is not None:
                actual = (api.scalar(editor, 2009), api.scalar(editor, 2008))
                if actual != case['selection']: raise RuntimeError('Ordering whole-block selection/direction differs')
            notice = catalog['lines.mixed_eol_rejected']['en'] in api.text(api.control(hwnd, 11))
            if notice is not case['expect_rejected']: raise RuntimeError('Ordering rejection/no-op feedback differs')
            api.no_dialog(process.pid)
            checks['rejection_notice'] = True
            checks['command_exact'] = checks['unicode_selection'] = True
            if path.read_bytes() != source: raise RuntimeError('Ordering command implicitly saved')
            checks['no_implicit_save'] = True
            if not changed:
                if api.scalar(editor, 2174): raise RuntimeError('Ordering no-op created Undo')
                if (api.scalar(editor, 2009), api.scalar(editor, 2008)) != (case['anchor'], case['caret']):
                    raise RuntimeError('Ordering no-op changed selection')
            api.command(hwnd, 201); state(hwnd, source, case['mode'], 0)
            if api.scalar(editor, 2174): raise RuntimeError('Ordering command was not one Undo group')
            checks['undo_clean'] = True
            api.command(hwnd, 202); state(hwnd, target, case['mode'], changed); checks['redo'] = True
            save_and_verify(api, process, hwnd, path, target); checks['changed_save'] = True
            api.command(hwnd, 201); state(hwnd, source, case['mode'], changed)
            save_and_verify(api, process, hwnd, path, source); checks['undo_save'] = True
            api.command(hwnd, 202); state(hwnd, target, case['mode'], changed)
            save_and_verify(api, process, hwnd, path, target); checks['redo_save'] = True
            print('Ordering command and three exact saves passed: '+case['id'], flush=True)
        resources=run_resources(api,process,hwnd,catalog,paths[-1])
        activate_source(api, hwnd, large, len(opened)); editor = api.editor(hwnd)
        before = tuple(api.scalar(editor, m) for m in (2006, 2030, 2159, 2174, 2008, 2009))
        for command, _ in COMMANDS: api.command(hwnd, command)
        if before != tuple(api.scalar(editor, m) for m in (2006, 2030, 2159, 2174, 2008, 2009)):
            raise RuntimeError('Ordering large-file guard changed editor state')
        if ci.sha(large) != large_hash: raise RuntimeError('Ordering large source changed')
        return {'checks': dict.fromkeys(CHECKS, True), 'languages': list(LANGUAGES), 'resources': resources}

    def reopen(process, hwnd):
        loaded(process, hwnd, paths[-1])
        for index, (path, case) in enumerate(zip(paths, ALL_CASES)):
            activate_source(api, hwnd, path, len(paths)); state(hwnd, case['target'], detected_mode(case['target']), 0)
            if path.read_bytes() != case['target']: raise RuntimeError('Ordering reopen disk bytes differ')
            progress[index]['checks']['fresh_reopen'] = True
            print('Ordering fresh-process reopen passed: '+case['id'], flush=True)
        return {}

    target = fixtures/'ordering-runtime'; _copy_runtime(binary_dir, target, hashes)
    with isolated_settings():
        result = ci.run_gui(api, target, evidence, name='main-gui-line-ordering', arguments=opened, exercise=exercise, log_prefix='line-ordering')
        result.update(schema='ru-notepad-line-ordering-gui-v1', fixture_binary_sha256=hashes, cases=progress)
        if result['passed']:
            target = fixtures/'ordering-reopen-runtime'; _copy_runtime(binary_dir, target, hashes)
            result['reopen'] = ci.run_gui(api, target, evidence, name='main-gui-ordering-reopen', arguments=paths, exercise=reopen, log_prefix='ordering-reopen')
            result['reopen']['fixture_binary_sha256'] = hashes
            if result['reopen']['passed']: validate_result(result, hashes)
            else:
                result['passed'] = False
                result['error'] = 'Ordering fresh-process reopen failed; see nested receipt'
    return result
