"""Portable fail-closed receipt tests; not Windows execution evidence."""
from copy import deepcopy
import unittest
import gui_language_catalog as gui
HASHES={'ru_notepad.exe':'a'*64}
def receipt(hashes=HASHES):
    return dict(schema='ru-notepad-language-gui-v1',name='main-gui-language-catalog',passed=True,executed=True,cleanup_killed=False,main_hwnd_seen=True,close_posted=True,detached_from_console=True,exit_code=0,fixture_binary_sha256=dict(hashes),checks={k:True for k in gui.CHECKS},menu_commands=sorted(gui.COMMANDS.values()),modes=[{'language':r['id'],'command':gui.COMMANDS[r['id']],'lexer':0 if r['id'] in ('plain','ru') else r['lexer_id']} for r in gui.ROWS])
class Contract(unittest.TestCase):
    def test_complete(self):self.assertTrue(gui.validate_result(receipt(),HASHES))
    def test_missing_each_field(self):
        for key in receipt():
            r=receipt();del r[key]
            with self.subTest(key=key),self.assertRaises(ValueError):gui.validate_result(r,HASHES)
    def test_lifecycle_mutations(self):
        for key,value in [('passed',False),('executed',False),('cleanup_killed',True),('exit_code',True),('exit_code',1),('fixture_binary_sha256',{}),('error','failed'),('skips',['skipped'])]:
            r=receipt();r[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):gui.validate_result(r,HASHES)
    def test_each_check_required(self):
        for key in gui.CHECKS:
            r=receipt();r['checks'][key]=False
            with self.subTest(key=key),self.assertRaises(ValueError):gui.validate_result(r,HASHES)
    def test_all_modes_and_menu_exact(self):
        for index in range(95):
            for field in ('modes','menu_commands'):
                r=receipt();r[field].pop(index)
                with self.subTest(index=index,field=field),self.assertRaises(ValueError):gui.validate_result(r,HASHES)
        for key in ('language','command','lexer'):
            r=receipt();r['modes'][5][key]='wrong'
            with self.assertRaises(ValueError):gui.validate_result(r,HASHES)
        r=receipt();r['menu_commands'].append(r['menu_commands'][0])
        with self.assertRaises(ValueError):gui.validate_result(r,HASHES)
if __name__=='__main__':unittest.main()
