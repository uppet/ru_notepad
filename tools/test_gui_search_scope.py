"""Portable fail-closed search receipt contracts, not Windows runtime evidence."""
from copy import deepcopy
import inspect
import unittest
import gui_search_scope as gui
HASHES={'ru_notepad.exe':'a'*64}


def layouts():
    return [dict(language=language,scope=scope,requested=list(size),outer=list(size),client=[size[0]-16,size[1]-60],
                 rectangles={str(n):[0,i*20,100,i*20+18] for i,n in enumerate(gui.LAYOUT_CONTROLS)},
                 minimum_widths={str(n):80 for n in gui.SEARCH_CONTROLS},scope_disabled=True)
            for language in gui.LANGUAGES for scope in ('selection','invalid','document') for size in gui.LAYOUT_SIZES]


def receipt(hashes=HASHES):
    row=dict(passed=True,executed=True,cleanup_killed=False,main_hwnd_seen=True,
             close_posted=True,detached_from_console=True,exit_code=0,fixture_binary_sha256=dict(hashes))
    return dict(row,schema='ru-notepad-search-scope-gui-v1',name='main-gui-search-scope',
                reopen=dict(row,name='main-gui-search-reopen'),checks=dict.fromkeys(gui.CHECKS,True),
                languages=list(gui.LANGUAGES),cases=gui.expected_cases(),layouts=layouts(),large_bytes=gui.LARGE_BYTES,large_search_seconds=.1)


class Contract(unittest.TestCase):
    def reject(self,row):
        with self.assertRaises(ValueError):gui.validate_result(row,HASHES)
    def test_complete(self):self.assertTrue(gui.validate_result(receipt(),HASHES))
    def test_all_fields_required(self):
        for key in receipt():
            row=receipt();del row[key];self.reject(row)
    def test_lifecycle(self):
        for phase in (None,'reopen'):
            for key,value in (('passed',False),('executed',False),('cleanup_killed',True),('main_hwnd_seen',False),
                              ('close_posted',False),('detached_from_console',False),('exit_code',True),('exit_code',1),
                              ('error','bad'),('skips',['bad']),('fixture_binary_sha256',{})):
                row=receipt();(row if phase is None else row[phase])[key]=value;self.reject(row)
    def test_checks(self):
        for key in gui.CHECKS:
            for value in (False,1,None):
                row=receipt();row['checks'][key]=value;self.reject(row)
            row=receipt();del row['checks'][key];self.reject(row)
    def test_case_checks_required(self):
        for i in range(len(gui.ALL_CASES)):
            for key in gui.CASE_CHECKS:
                for value in (False,1,None):
                    row=receipt();row['cases'][i]['checks'][key]=value;self.reject(row)
                row=receipt();del row['cases'][i]['checks'][key];self.reject(row)
            row=receipt();del row['cases'][i];self.reject(row)
            row=receipt();row['cases'][i]['source_sha256']='0'*64;self.reject(row)
    def test_exact_inventory(self):
        for field in ('languages','cases'):
            row=receipt();row[field].reverse();self.reject(row)
            row=receipt();row[field].pop();self.reject(row)
        self.assertEqual(len(gui.ALL_CASES),24)
        self.assertEqual(len(set(c['id'] for c in gui.ALL_CASES)),24)
    def test_layout_native_coverage_and_fail_closed_geometry(self):
        self.assertEqual(len(layouts()),42)
        for index in range(42):
            for key,value in (('scope_disabled',False),('outer',[639,400]),('requested',[0,0]),('client',[0,0])):
                row=receipt();row['layouts'][index][key]=value;self.reject(row)
            for identifier in gui.LAYOUT_CONTROLS:
                row=receipt();del row['layouts'][index]['rectangles'][str(identifier)];self.reject(row)
            row=receipt();row['layouts'][index]['rectangles']['310']=[0,0,100,100];self.reject(row)
            row=receipt();row['layouts'][index]['minimum_widths']['316']=101;self.reject(row)
            row=receipt();row['layouts'][index]['minimum_widths']['316']=True;self.reject(row)
            row=receipt();row['layouts'].pop(index);self.reject(row)
    def test_wide_native_maxtrack_clamp_is_recorded_not_overridden(self):
        row=receipt()
        for item in row['layouts']:
            if item['requested']==[1120,760]:item['outer']=[1044,760];item['client']=[1028,700]
        self.assertTrue(gui.validate_result(row,HASHES))
        source=inspect.getsource(gui.native_layout)
        for token in ('MoveWindow','GetWindowRect','ClientToScreen','GetClientRect','GetTextExtentPoint32W','SelectObject','ReleaseDC'):
            self.assertIn(token,source)
        self.assertNotIn('Subclass',source)
    def test_large_mode_fixture_identity(self):
        for value in (True,False,None,2097152,gui.LARGE_BYTES-1):
            row=receipt();row['large_bytes']=value;self.reject(row)
    def test_five_second_bound(self):
        for value in (True,False,None,-1,5,6,float('inf'),float('nan')):
            row=receipt();row['large_search_seconds']=value;self.reject(row)
    def test_unicode_fixture_bounds(self):
        for c in gui.ALL_CASES:
            source=c['source'];source.decode()
            self.assertTrue(0<=c['low']<c['high']<=len(source))
            for p in (c['low'],c['high'],c['caret']):source[:p].decode()
            if c['expected']:
                a,b=c['expected'];self.assertTrue(c['low']<=a<b<=c['high'])
                for p in (a,b):source[:p].decode()
                if c['case']:self.assertEqual(source[a:b],c['pattern'].encode())
                else:self.assertEqual(source[a:b].lower(),c['pattern'].encode().lower())
    def test_matrix_has_both_directions_and_options(self):
        unicode=[c for c in gui.ALL_CASES if c['id'].startswith('unicode')]
        self.assertEqual(len(unicode),16)
        self.assertEqual({(c['backwards'],c['reverse'],c['wrap'],c['caret'] in (0,len(c['source']))) for c in unicode},
                         {(a,b,c,d) for a in (False,True) for b in (False,True) for c in (False,True) for d in (False,True)})
        self.assertEqual(sum(c['expected'] is None for c in gui.ALL_CASES),2)
        self.assertEqual(sum('\r\n' in c['pattern'] for c in gui.ALL_CASES),2)
    def test_search_commands_not_private_mutation_substitutes(self):
        source=inspect.getsource(gui.run)
        for token in ('2194','2196','2181','SendInput','WriteProcessMemory'):
            self.assertNotIn(token,source)
        for token in ('api.command(hwnd,313)','api.command(hwnd,314)','api.command(hwnd,315)',
                      'api.command(hwnd,308 if',"name='main-gui-search-reopen'",'save_and_verify(',
                      'u.PostMessageW(api.control(hwnd,310),0x100,0x72,1)'):
            self.assertIn(token,source)
    def test_checks_are_recorded_only_after_execution(self):
        source=inspect.getsource(gui.run)
        self.assertNotIn('dict.fromkeys(CHECKS,True)',source)
        for key in gui.CHECKS:self.assertIn("['"+key+"']=True",source)
        self.assertEqual(source.count('api.drop(hwnd,[paths[0]])'),1)
        self.assertIn("api.command(hwnd,105);invalid(hwnd)",source)
        self.assertIn("_information_shape(shape,hwnd,{expected})",source)
    def test_input_marshalling_is_system_message(self):
        source=inspect.getsource(gui.set_text)
        self.assertIn('api.scalar(handle,12,0,ctypes.addressof(buffer))',source)
        self.assertIn('api.text(handle)!=value',source)
    def test_fail_closed_runtime_and_names(self):
        row=receipt();row['name']='wrong';self.reject(row)
        row=receipt();row['reopen']['name']='wrong';self.reject(row)
        row=receipt();row['schema']='wrong';self.reject(row)
        row=receipt();row['checks']['unexpected']=True;self.reject(row)

if __name__=='__main__':unittest.main()
