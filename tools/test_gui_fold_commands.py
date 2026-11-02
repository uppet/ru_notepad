"""Portable fail-closed contracts; deliberately not native execution evidence."""
from copy import deepcopy
import ctypes
import unittest
import gui_fold_commands as gui

HASHES = {'ru_notepad.exe': 'a'*64}
def receipt(hashes=HASHES):
    return dict(schema='ru-notepad-fold-commands-gui-v1', name='main-gui-fold-commands',
                passed=True, executed=True, cleanup_killed=False, main_hwnd_seen=True,
                close_posted=True, detached_from_console=True, exit_code=0,
                fixture_binary_sha256=dict(hashes), large_bytes=gui.LARGE_BYTES,
                safety={key: True for key in gui.SAFETY},
                cases=[dict(language=name, command=gui.COMMANDS[name], header=header, child=child,
                            bytes=len(data), checks={key: True for key in gui.CHECKS})
                       for name, _, data, header, child in gui.CASES])

class TabSelection(unittest.TestCase):
    class API:
        def __init__(self, titles): self.titles=titles; self.index=0; self.commands=[]
        def text(self, hwnd): return self.titles[self.index]
        def command(self, hwnd, command):
            self.commands.append(command); self.index=(self.index+1)%len(self.titles)
        def responsive(self, hwnd): pass
    def test_cli_batch_tabs_reachable_without_drop_allocations(self):
        from pathlib import Path
        titles=['Untitled · ru_notepad']+[str(i)+'.c · ru_notepad' for i in range(9)]
        api=self.API(titles)
        for i in reversed(range(9)):
            gui.activate_source(api,1,Path(str(i)+'.c'),9)
            self.assertEqual(api.text(1),str(i)+'.c · ru_notepad')
        self.assertTrue(all(c==112 for c in api.commands))
    def test_cli_open_waits_for_busy_readonly_to_clear(self):
        import inspect
        source=inspect.getsource(gui.run)
        self.assertIn('api.scalar(api.editor(hwnd), 2140) == 0',source)
        self.assertIn('api.user.IsWindowEnabled(api.control(hwnd, 10))',source)
        self.assertIn('not api.user.IsWindowVisible(api.control(hwnd, 901))',source)
        self.assertNotIn('api.drop(',source)
    def test_missing_cli_tab_fails_boundedly(self):
        from pathlib import Path
        api=self.API(['Untitled · ru_notepad'])
        with self.assertRaises(RuntimeError):gui.activate_source(api,1,Path('missing.c'),9)
        self.assertEqual(len(api.commands),10)


class Contract(unittest.TestCase):
    def reject(self, record):
        with self.assertRaises(ValueError): gui.validate_result(record, HASHES)
    def test_complete(self): self.assertTrue(gui.validate_result(receipt(), HASHES))
    def test_missing_fields(self):
        for key in receipt():
            r=receipt(); del r[key]
            with self.subTest(key=key): self.reject(r)
    def test_lifecycle(self):
        for key, value in [('passed', False), ('executed', False), ('cleanup_killed', True),
                           ('main_hwnd_seen', False), ('close_posted', False), ('detached_from_console', False),
                           ('exit_code', True), ('exit_code', 1), ('fixture_binary_sha256', {}),
                           ('error', 'failed'), ('skips', ['skipped']), ('large_bytes', 31999999)]:
            r=receipt(); r[key]=value
            with self.subTest(key=key): self.reject(r)
    def test_every_case_required_and_ordered(self):
        for i in range(len(gui.CASES)):
            r=receipt(); r['cases'].pop(i); self.reject(r)
        r=receipt(); r['cases'].reverse(); self.reject(r)
        r=receipt(); r['cases'].append(deepcopy(r['cases'][0])); self.reject(r)
    def test_case_identity(self):
        for i in range(len(gui.CASES)):
            for key in ('language','command','header','child','bytes'):
                r=receipt(); r['cases'][i][key]='wrong'; self.reject(r)
            for key in ('header','child'):
                r=receipt(); r['cases'][i][key]=bool(r['cases'][i][key]); self.reject(r)
    def test_all_checks_required_and_boolean(self):
        for i in range(len(gui.CASES)):
            for key in gui.CHECKS:
                for value in (False, 1, None):
                    r=receipt(); r['cases'][i]['checks'][key]=value; self.reject(r)
                r=receipt(); del r['cases'][i]['checks'][key]; self.reject(r)
        for key in gui.SAFETY:
            for value in (False, 1, None):
                r=receipt(); r['safety'][key]=value; self.reject(r)
            r=receipt(); del r['safety'][key]; self.reject(r)
    def test_large_fixture_exact_boundary(self):
        self.assertEqual(gui.LARGE_BYTES, 32000000)
        self.assertEqual(len(b'int main() {\n')+gui.LARGE_BYTES-16+len(b'\n}\n'), gui.LARGE_BYTES)
    def test_win32_input_layout(self):
        self.assertEqual(ctypes.sizeof(gui._Input), 40 if ctypes.sizeof(ctypes.c_void_p)==8 else 28)
        self.assertEqual(gui._Input.value.offset, 8 if ctypes.sizeof(ctypes.c_void_p)==8 else 4)
    def test_fixture_shape(self):
        self.assertEqual(tuple(row[0] for row in gui.CASES), ('c','java','python','xml','cpp','ru','markdown'))
        for _, _, data, header, child in gui.CASES:
            self.assertLess(len(data),4096); self.assertLess(header,child)
            self.assertLess(child,len(data.splitlines()))

class BaselineContract(unittest.TestCase):
    def receipt(self):
        r=receipt(); r.pop('cases'); r.pop('safety'); r.pop('large_bytes')
        r.update(schema='ru-notepad-fold-baseline-gui-v1', name='main-gui-fold-baseline',
                 checks={key: True for key in gui.BASELINE_CHECKS})
        return r
    def test_complete(self): self.assertTrue(gui.validate_baseline_result(self.receipt(), HASHES))
    def test_all_baseline_evidence_required(self):
        for key in self.receipt():
            r=self.receipt(); del r[key]
            with self.assertRaises(ValueError): gui.validate_baseline_result(r,HASHES)
        for key in gui.BASELINE_CHECKS:
            for value in (False, 1, None):
                r=self.receipt(); r['checks'][key]=value
                with self.assertRaises(ValueError): gui.validate_baseline_result(r,HASHES)
    def test_failure_is_not_negative_control_success(self):
        for key,value in [('passed',False),('error','timeout'),('exit_code',1),('cleanup_killed',True),('skips',['no GUI'])]:
            r=self.receipt(); r[key]=value
            with self.assertRaises(ValueError): gui.validate_baseline_result(r,HASHES)

if __name__=='__main__': unittest.main()
