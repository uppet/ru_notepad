#!/usr/bin/env python3
"""Actual main command/keyboard folding; scalar-only editor observations.

Small sources are checked byte-for-byte. The 32 MB large-mode safety case uses
length, bounded byte probes, savepoint/undo state and unchanged source hash;
it does not claim a full cross-process hash of the large editor buffer.
"""
import ctypes
import json
from ctypes import wintypes
from pathlib import Path
import windows_ci as ci
from gui_language_catalog import COMMANDS, ROOT
from gui_instance_tabs import isolated_settings, _copy_runtime, _MouseInput, _GUIThreadInfo

CASES = (
    ('c', 'c', b'int main(void) {\n  return 0;\n}\n', 0, 1),
    ('java', 'java', b'class Example {\n  int value;\n}\n', 0, 1),
    ('python', 'py', b'def example():\n    return 42\n\nexample()\n', 0, 1),
    ('xml', 'xml', b'<root>\n  <child/>\n</root>\n', 0, 1),
    ('cpp', 'cpp', b'int main() {\n  return 0;\n}\n', 0, 1),
    ('ru', 'ru', ci.gui_ru_syntax_fixture()[0], 1, 2),
    ('markdown', 'md', b'# Heading\nbody\n## Child\ninside\n# Next\nlast\n', 0, 1),
)
CHECKS = ('command_collapse', 'command_expand', 'shortcut_collapse', 'shortcut_expand',
          'text_preserved', 'selection_preserved', 'savepoint_preserved', 'undo_preserved', 'source_unchanged')
SAFETY = ('plain_noop', 'json_capability_noop', 'markdown_disabled_noop', 'large_mode_noop')
LARGE_BYTES = 32000000
LARGE_STATUS = tuple(json.loads((ROOT/'locales/ui.json').read_text(encoding='utf-8'))['status.large_file'].values())

class _KeyboardInput(ctypes.Structure):
    _fields_ = [('wVk', ctypes.c_uint16), ('wScan', ctypes.c_uint16),
                ('dwFlags', ctypes.c_uint32), ('time', ctypes.c_uint32), ('dwExtraInfo', ctypes.c_size_t)]
class _InputValue(ctypes.Union):
    _fields_ = [('mi', _MouseInput), ('ki', _KeyboardInput)]
class _Input(ctypes.Structure):
    _fields_ = [('type', ctypes.c_uint32), ('value', _InputValue)]


def shortcut(api, process, hwnd, editor, expand):
    """Deliver real accelerator keys only to the verified owned foreground editor."""
    u = api.user
    for name, args, result in (
        ('GetForegroundWindow', [], wintypes.HWND),
        ('SetForegroundWindow', [wintypes.HWND], wintypes.BOOL),
        ('GetAsyncKeyState', [ctypes.c_int], ctypes.c_int16),
        ('GetGUIThreadInfo', [ctypes.c_uint32, ctypes.POINTER(_GUIThreadInfo)], wintypes.BOOL),
        ('SendInput', [ctypes.c_uint32, ctypes.POINTER(_Input), ctypes.c_int], ctypes.c_uint32)):
        fn = getattr(u, name); fn.argtypes = args; fn.restype = result
    keys = (17, 16, 221 if expand else 219)
    if any(u.GetAsyncKeyState(k) & 0x8000 for k in (*keys, 18, 91, 92)):
        raise RuntimeError('Refusing shortcut while pre-existing modifier/key is held')
    previous = u.GetForegroundWindow()
    pending = []
    def send(key, release=False):
        event = _Input(); event.type = 1; event.value.ki.wVk = key
        event.value.ki.dwFlags = 2 if release else 0
        if u.SendInput(1, ctypes.byref(event), ctypes.sizeof(event)) != 1:
            raise RuntimeError('SendInput did not deliver fixture shortcut event')
    try:
        u.SetForegroundWindow(hwnd)
        def focused():
            info = _GUIThreadInfo(); info.cbSize = ctypes.sizeof(info)
            thread = u.GetWindowThreadProcessId(hwnd, None)
            return (u.GetForegroundWindow() == hwnd and
                    u.GetGUIThreadInfo(thread, ctypes.byref(info)) and info.hwndFocus == editor)
        ci.wait_gui(api, process, focused, 'Owned fixture editor did not acquire keyboard focus')
        api.verify_owned_handles(process.pid, hwnd, editor)
        for key in keys:
            if not focused(): raise RuntimeError('Fixture lost foreground/focus before shortcut')
            send(key); pending.append(key)
        for key in reversed(keys):
            send(key, True); pending.remove(key)
        api.responsive(hwnd)
    finally:
        for key in reversed(pending): send(key, True)
        if previous and previous != hwnd: u.SetForegroundWindow(previous)


def validate_result(record, hashes):
    if not isinstance(record, dict) or record.get('schema') != 'ru-notepad-fold-commands-gui-v1' or record.get('name') != 'main-gui-fold-commands':
        raise ValueError('Fold GUI identity differs')
    for key, value in [('passed', True), ('executed', True), ('cleanup_killed', False),
                       ('main_hwnd_seen', True), ('close_posted', True), ('detached_from_console', True)]:
        if record.get(key) is not value: raise ValueError('Fold GUI lifecycle failed')
    if type(record.get('exit_code')) is not int or record['exit_code'] != 0 or record.get('fixture_binary_sha256') != hashes:
        raise ValueError('Fold GUI runtime/exit differs')
    if record.get('error') or record.get('skips'): raise ValueError('Fold GUI errored/skipped')
    rows = record.get('cases')
    if not isinstance(rows, list) or len(rows) != len(CASES): raise ValueError('Fold case inventory differs')
    for row, (name, _, data, header, child) in zip(rows, CASES):
        expected = {'language': name, 'command': COMMANDS[name], 'header': header, 'child': child,
                    'bytes': len(data), 'checks': {key: True for key in CHECKS}}
        if not isinstance(row, dict) or row != expected or any(type(row.get(k)) is not int for k in ('command', 'header', 'child', 'bytes')):
            raise ValueError('Fold case missing or changed')
        if any(value is not True for value in row['checks'].values()): raise ValueError('Fold case has non-boolean check')
    if record.get('safety') != {key: True for key in SAFETY} or any(value is not True for value in record['safety'].values()):
        raise ValueError('Fold safety checks incomplete')
    if type(record.get('large_bytes')) is not int or record['large_bytes'] != LARGE_BYTES:
        raise ValueError('Large-mode fixture threshold differs')
    return True


def run(api, binary_dir, fixtures, evidence):
    binary_dir, fixtures, evidence = map(Path, (binary_dir, fixtures, evidence))
    hashes = {name: ci.sha(binary_dir/name) for name in ci.portable.RUNTIME_NAMES}
    target = fixtures/'fold-command-runtime'; _copy_runtime(binary_dir, target, hashes)
    sources = {}
    for name, extension, data, _, _ in CASES:
        path = fixtures/('fold-command-'+name+'.'+extension); path.write_bytes(data); sources[name] = path
    json_data = b'{\n  "value": 42\n}\n'
    json_source = fixtures/'fold-command-json.json'; json_source.write_bytes(json_data)
    large = fixtures/'fold-command-large.c'
    # Few lines avoid introducing a separate line-count performance workload.
    large.write_bytes(b'int main() {\n' + b' '*(LARGE_BYTES-16) + b'\n}\n')
    assert large.stat().st_size == LARGE_BYTES
    original_hashes = {path: ci.sha(path) for path in [*sources.values(), json_source, large]}
    def exercise(process, hwnd):
        results = []; safety = {}
        for name, _, data, header, child in CASES:
            source = sources[name]
            api.drop(api.editor(hwnd), [source.resolve()])
            ci.wait_gui(api, process, lambda: api.text(hwnd) == source.name+' · ru_notepad', 'Fold source did not open: '+name)
            editor = api.editor(hwnd); api.verify_owned_handles(process.pid, hwnd, editor)
            api.command(hwnd, COMMANDS[name])
            def ready():
                if not api.scalar(editor, 2223, header) & 0x2000: return False
                status = api.text(api.control(hwnd, 11))
                if name == 'markdown': return ci.markdown_status_complete(status)
                return not ci.status_contains(status, 'status.styling_ru')
            ci.wait_gui(api, process, ready, 'Missing completed actual fold header: '+name)
            # Selection stays on visible first line even when descendants collapse.
            api.scalar(editor, 2160, 0, 1)
            lines = api.scalar(editor, 2154)
            baseline = tuple(api.scalar(editor, message) for message in (2008, 2009, 2159, 2174, 2016))
            if baseline != (1, 0, 0, 0, 0): raise RuntimeError('Unexpected fresh fold source state')
            def unchanged():
                if api.editor_bytes(hwnd) != data: raise RuntimeError('Folding changed source text: '+name)
                if tuple(api.scalar(editor, m) for m in (2008, 2009, 2159, 2174, 2016)) != baseline:
                    raise RuntimeError('Folding changed selection/savepoint/undo/redo: '+name)
            def all_visible(): return all(api.scalar(editor, 2228, line) == 1 for line in range(lines))
            checks = {}
            for keyboard in (False, True):
                for expand in (False, True):
                    if keyboard: shortcut(api, process, hwnd, editor, expand)
                    else: api.command(hwnd, 506 if expand else 505)
                    predicate = all_visible if expand else lambda: api.scalar(editor, 2228, child) == 0 and api.scalar(editor, 2228, header) == 1
                    ci.wait_gui(api, process, predicate, 'Fold route failed: '+name+(' expand' if expand else ' collapse'))
                    unchanged(); checks[('shortcut_' if keyboard else 'command_')+('expand' if expand else 'collapse')] = True
            if name == 'markdown':
                api.command(hwnd, 507)
                for expand in (False, True):
                    api.command(hwnd, 506 if expand else 505)
                    shortcut(api, process, hwnd, editor, expand)
                if not all_visible(): raise RuntimeError('Disabled Markdown folds hid lines')
                unchanged(); safety['markdown_disabled_noop'] = True
                api.command(hwnd, 507)
            api.command(hwnd, 701)
            for expand in (False, True):
                api.command(hwnd, 506 if expand else 505)
                shortcut(api, process, hwnd, editor, expand)
            if not all_visible() or api.scalar(editor, 4002) != 0: raise RuntimeError('Plain mode fold commands not safe')
            unchanged(); safety['plain_noop'] = True
            if ci.sha(source) != original_hashes[source]: raise RuntimeError('Fold source file modified')
            checks.update({key: True for key in CHECKS if key not in checks})
            results.append({'language': name, 'command': COMMANDS[name], 'header': header, 'child': child, 'bytes': len(data), 'checks': checks})
        # The shipped JSON configuration has no folding capability. Selecting a
        # native lexer is not enough to authorize collapse: this is a negative case.
        api.drop(api.editor(hwnd), [json_source.resolve()])
        ci.wait_gui(api, process, lambda: api.text(hwnd) == json_source.name+' · ru_notepad', 'JSON safety source did not open')
        editor = api.editor(hwnd); api.command(hwnd, COMMANDS['json'])
        if api.scalar(editor, 4002) != 120 or api.scalar(editor, 2243, 2) != 0:
            raise RuntimeError('JSON did not select configured non-folding capability')
        api.scalar(editor, 2160, 0, 1)
        for keyboard in (False, True):
            for expand in (False, True):
                if keyboard: shortcut(api, process, hwnd, editor, expand)
                else: api.command(hwnd, 506 if expand else 505)
                if (api.editor_bytes(hwnd) != json_data or
                    tuple(api.scalar(editor, m) for m in (2008, 2009, 2159, 2174, 2016)) != (1, 0, 0, 0, 0) or
                    any(api.scalar(editor, 2228, line) != 1 for line in range(4))):
                    raise RuntimeError('JSON non-folding route changed state')
        if ci.sha(json_source) != original_hashes[json_source]: raise RuntimeError('JSON source file modified')
        safety['json_capability_noop'] = True
        api.drop(api.editor(hwnd), [large.resolve()])
        ci.wait_gui(api, process, lambda: api.text(hwnd) == large.name+' · ru_notepad', 'Large fold source did not open')
        editor = api.editor(hwnd)
        if api.scalar(editor, 4002) != 0 or not any(label in api.text(api.control(hwnd, 11)) for label in LARGE_STATUS):
            raise RuntimeError('Large source did not enter actual plain large-file mode')
        probes = (0, 11, 12, LARGE_BYTES//2, LARGE_BYTES-4, LARGE_BYTES-3, LARGE_BYTES-2, LARGE_BYTES-1)
        with large.open('rb') as stream:
            expected = []
            for index in probes: stream.seek(index); expected.append(stream.read(1)[0])
        def large_state():
            return (api.scalar(editor, 2006), api.scalar(editor, 2159), api.scalar(editor, 2174), api.scalar(editor, 2016),
                    [api.scalar(editor, 2007, index)&255 for index in probes],
                    [api.scalar(editor, 2228, line) for line in range(4)])
        want = (LARGE_BYTES, 0, 0, 0, expected, [1]*4)
        if large_state() != want: raise RuntimeError('Large initial state differs')
        for expand in (False, True):
            api.command(hwnd, 506 if expand else 505)
            shortcut(api, process, hwnd, editor, expand)
            if large_state() != want: raise RuntimeError('Large-mode fold command changed bounded state')
        if ci.sha(large) != original_hashes[large]: raise RuntimeError('Large source file modified')
        safety['large_mode_noop'] = True
        return {'cases': results, 'safety': safety, 'large_bytes': LARGE_BYTES}
    with isolated_settings():
        result = ci.run_gui(api, target, evidence, name='main-gui-fold-commands', exercise=exercise, log_prefix='fold-commands')
    result.update(schema='ru-notepad-fold-commands-gui-v1', fixture_binary_sha256=hashes)
    if result['passed']: validate_result(result, hashes)
    return result

BASELINE_CHECKS = ('c_mode_selected', 'native_header_ready', 'command_505_noop',
                   'native_direct_collapse_works', 'command_506_noop',
                   'native_direct_expand_works', 'text_state_preserved', 'source_unchanged')

def validate_baseline_result(record, hashes):
    if not isinstance(record, dict) or record.get('schema') != 'ru-notepad-fold-baseline-gui-v1' or record.get('name') != 'main-gui-fold-baseline':
        raise ValueError('Fold baseline identity differs')
    for key, value in [('passed', True), ('executed', True), ('cleanup_killed', False),
                       ('main_hwnd_seen', True), ('close_posted', True), ('detached_from_console', True)]:
        if record.get(key) is not value: raise ValueError('Fold baseline lifecycle failed')
    if type(record.get('exit_code')) is not int or record['exit_code'] != 0 or record.get('fixture_binary_sha256') != hashes:
        raise ValueError('Fold baseline runtime/exit differs')
    if record.get('error') or record.get('skips'): raise ValueError('Fold baseline errored/skipped')
    checks = record.get('checks')
    if not isinstance(checks, dict) or set(checks) != set(BASELINE_CHECKS) or any(v is not True for v in checks.values()):
        raise ValueError('Fold baseline exact negative-control observations incomplete')
    return True


def run_baseline(api, binary_dir, fixtures, evidence):
    """Verify the specific old defect, never convert an arbitrary failure to PASS.

Caller must independently pin/verify the old artifact identity before invoking.
Direct SCI_FOLDALL is deliberately used ONLY as the baseline backend control;
the candidate acceptance above never substitutes it for application commands.
"""
    binary_dir, fixtures, evidence = map(Path, (binary_dir, fixtures, evidence))
    hashes = {name: ci.sha(binary_dir/name) for name in ci.portable.RUNTIME_NAMES}
    target = fixtures/'fold-baseline-runtime'; _copy_runtime(binary_dir, target, hashes)
    source = fixtures/'fold-baseline.c'; data = CASES[0][2]; source.write_bytes(data)
    def exercise(process, hwnd):
        ci.wait_gui(api, process, lambda: api.text(hwnd) == source.name+' · ru_notepad', 'Baseline C fixture did not open')
        editor = api.editor(hwnd); api.verify_owned_handles(process.pid, hwnd, editor)
        api.command(hwnd, COMMANDS['c'])
        if api.scalar(editor, 4002) != 3: raise RuntimeError('Baseline C lexer not active')
        ci.wait_gui(api, process, lambda: bool(api.scalar(editor, 2223, 0) & 0x2000), 'Baseline native fold header missing')
        lines = api.scalar(editor, 2154)
        def visible(): return all(api.scalar(editor, 2228, line) == 1 for line in range(lines))
        def unchanged():
            if api.editor_bytes(hwnd) != data or any(api.scalar(editor, m) for m in (2159, 2174, 2016)):
                raise RuntimeError('Baseline folding changed text/savepoint/undo')
        if not visible(): raise RuntimeError('Baseline did not begin expanded')
        api.command(hwnd, 505)
        if not visible(): raise RuntimeError('Expected old C 505 routing defect was not reproduced')
        unchanged()
        api.scalar(editor, 2662, 0)  # Independent proof that native backend CAN fold.
        ci.wait_gui(api, process, lambda: api.scalar(editor, 2228, 1) == 0, 'Baseline native backend itself cannot collapse')
        api.command(hwnd, 506)
        if api.scalar(editor, 2228, 1) != 0: raise RuntimeError('Expected old C 506 routing defect was not reproduced')
        unchanged()
        api.scalar(editor, 2662, 1)
        ci.wait_gui(api, process, visible, 'Baseline direct native expand failed')
        unchanged()
        if source.read_bytes() != data: raise RuntimeError('Baseline source changed')
        return {'checks': {key: True for key in BASELINE_CHECKS}}
    with isolated_settings():
        result = ci.run_gui(api, target, evidence, name='main-gui-fold-baseline', arguments=[source.resolve()],
                            exercise=exercise, log_prefix='fold-baseline')
    result.update(schema='ru-notepad-fold-baseline-gui-v1', fixture_binary_sha256=hashes)
    if result['passed']: validate_baseline_result(result, hashes)
    return result
