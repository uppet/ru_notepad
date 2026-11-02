"""Portable fail-closed contracts, not Windows execution evidence."""
from copy import deepcopy
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import gui_eol_conversion as gui
HASHES = {'ru_notepad.exe':'a'*64}
def receipt(hashes=HASHES):
    row = dict(passed=True, executed=True, cleanup_killed=False, main_hwnd_seen=True,
               close_posted=True, detached_from_console=True, exit_code=0, fixture_binary_sha256=dict(hashes))
    return dict(row, schema='ru-notepad-eol-gui-v1', name='main-gui-eol-conversion',
                reopen=dict(row, name='main-gui-eol-reopen'), checks=dict.fromkeys(gui.CHECKS, True),
                encodings=[r[0] for r in gui.ENCODINGS], languages=list(gui.LANGUAGES), cases=gui.expected_cases())
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
    def test_full_matrix_and_each_completed_stage_required(self):
        self.assertEqual(len(gui.CASES),24)
        self.assertLessEqual(len(gui.CASES)+3+1+1,64)  # possible initial untitled too
        for index in range(24):
            for key in gui.CASE_CHECKS:
                for value in (False,1,None):
                    r=receipt();r['cases'][index]['checks'][key]=value;self.reject(r)
                r=receipt();del r['cases'][index]['checks'][key];self.reject(r)
            r=receipt();r['cases'].pop(index);self.reject(r)
        r=receipt();r['cases'].reverse();self.reject(r)
        r=receipt();r['cases'][0]['reverse']=0;self.reject(r)

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
class SaveObservation(unittest.TestCase):
    def setup_api(self):
        state=dict(readonly=0,enabled=True,cancel=False,dirty=0)
        api=SimpleNamespace(editor=lambda hwnd:2, control=lambda hwnd,n:n,
            scalar=lambda hwnd,n:state['readonly' if n==2140 else 'dirty'],
            user=SimpleNamespace(IsWindowEnabled=lambda hwnd:state['enabled'],IsWindowVisible=lambda hwnd:state['cancel']),
            command=lambda hwnd,n:self.assertEqual(n,103),responsive=lambda hwnd:None)
        return api,state
    def test_each_busy_signal_blocks_readiness(self):
        api,state=self.setup_api();self.assertTrue(gui.save_ready(api,1))
        for key,value in [('readonly',1),('enabled',False),('cancel',True),('dirty',1)]:
            old=state[key];state[key]=value;self.assertFalse(gui.save_ready(api,1));state[key]=old
    def test_no_disk_read_until_idle_and_exactly_one_final_read(self):
        api,state=self.setup_api();reads=[]
        path=SimpleNamespace(read_bytes=lambda:(reads.append(True),b'exact')[1])
        def wait(api_arg,process,predicate,message):
            for key,value in [('readonly',1),('enabled',False),('cancel',True),('dirty',1)]:
                old=state[key];state[key]=value;self.assertFalse(predicate());self.assertFalse(reads);state[key]=old
            self.assertTrue(predicate());self.assertFalse(reads)
        with patch.object(gui.ci,'wait_gui',side_effect=wait):gui.save_and_verify(api,None,1,path,b'exact')
        self.assertEqual(reads,[True])
    def test_final_permission_error_and_wrong_bytes_remain_failures(self):
        api,_=self.setup_api()
        def wait(*args):self.assertTrue(args[2]())
        def denied():raise PermissionError('still denied after idle')
        with patch.object(gui.ci,'wait_gui',side_effect=wait):
            with self.assertRaises(PermissionError):gui.save_and_verify(api,None,1,SimpleNamespace(read_bytes=denied),b'exact')
            with self.assertRaises(RuntimeError):gui.save_and_verify(api,None,1,SimpleNamespace(read_bytes=lambda:b'wrong'),b'exact')
    def test_original_wait_failure_propagates_without_disk_read(self):
        api,_=self.setup_api()
        def read():self.fail('read after failed wait')
        with patch.object(gui.ci,'wait_gui',side_effect=RuntimeError('original 30 second wait failed')):
            with self.assertRaisesRegex(RuntimeError,'30 second'):gui.save_and_verify(api,None,1,SimpleNamespace(read_bytes=read),b'exact')

if __name__=='__main__':unittest.main()
