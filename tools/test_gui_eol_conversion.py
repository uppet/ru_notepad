"""Portable fail-closed contracts, not Windows execution evidence."""
from copy import deepcopy
import unittest
import gui_eol_conversion as gui
HASHES = {'ru_notepad.exe':'a'*64}
def receipt(hashes=HASHES):
    row = dict(passed=True, executed=True, cleanup_killed=False, main_hwnd_seen=True,
               close_posted=True, detached_from_console=True, exit_code=0, fixture_binary_sha256=dict(hashes))
    return dict(row, schema='ru-notepad-eol-gui-v1', name='main-gui-eol-conversion',
                reopen=dict(row, name='main-gui-eol-reopen'), checks=dict.fromkeys(gui.CHECKS, True),
                encodings=[r[0] for r in gui.ENCODINGS], languages=list(gui.LANGUAGES))
class Contract(unittest.TestCase):
    def reject(self, record):
        with self.assertRaises(ValueError): gui.validate_result(record, HASHES)
    def test_complete(self): self.assertTrue(gui.validate_result(receipt(), HASHES))
    def test_all_fields_required(self):
        for key in receipt():
            r=receipt();del r[key];self.reject(r)
    def test_lifecycles(self):
        for phase in (None, 'reopen'):
            for key,value in [('passed',False),('executed',False),('cleanup_killed',True),
                              ('main_hwnd_seen',False),('close_posted',False),('detached_from_console',False),
                              ('exit_code',True),('exit_code',1),('error','bad'),('skips',['bad']),('fixture_binary_sha256',{})]:
                r=receipt();(r if phase is None else r[phase])[key]=value;self.reject(r)
    def test_checks(self):
        for key in gui.CHECKS:
            for value in (False,1,None):
                r=receipt();r['checks'][key]=value;self.reject(r)
            r=receipt();del r['checks'][key];self.reject(r)
    def test_exact_inventory(self):
        for field in ('languages','encodings'):
            r=receipt();r[field].reverse();self.reject(r)
            r=receipt();r[field].pop();self.reject(r)
    def test_unicode_reference(self):
        for _,_,eol in gui.MODES:
            data=gui.converted(gui.MIXED,eol)
            self.assertEqual(data.decode(),eol.decode().join(['汉😀','b','c','尾']))
            for p in (3,len(gui.MIXED)-3):data[:len(gui.converted(gui.MIXED[:p],eol))].decode()
    def test_no_direct_conversion_substitution_or_drop(self):
        import inspect
        source=inspect.getsource(gui.run)
        self.assertNotIn('api.drop(',source)
        self.assertNotIn('2029',source)
        self.assertNotIn('2031',source)
if __name__=='__main__':unittest.main()
