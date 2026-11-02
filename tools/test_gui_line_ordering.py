"""Portable fail-closed receipt contracts, not Windows execution evidence."""
import inspect
from copy import deepcopy
import unittest
import gui_line_ordering as gui
HASHES = {'ru_notepad.exe': 'a'*64}


def receipt(hashes=HASHES):
    row = dict(passed=True, executed=True, cleanup_killed=False, main_hwnd_seen=True,
               close_posted=True, detached_from_console=True, exit_code=0, fixture_binary_sha256=dict(hashes))
    return dict(row, schema='ru-notepad-line-ordering-gui-v1', name='main-gui-line-ordering',
                reopen=dict(row, name='main-gui-ordering-reopen'), checks=dict.fromkeys(gui.CHECKS, True),
                languages=list(gui.LANGUAGES), cases=gui.expected_cases(),
                resources=[dict(deepcopy(row),duration_seconds=0.1) for row in gui.expected_resources()])


class Contract(unittest.TestCase):
    def reject(self, record):
        with self.assertRaises(ValueError): gui.validate_result(record, HASHES)
    def test_complete(self): self.assertTrue(gui.validate_result(receipt(), HASHES))
    def test_all_fields_required(self):
        for key in receipt():
            r=receipt(); del r[key]; self.reject(r)
    def test_lifecycles(self):
        for phase in (None, 'reopen'):
            for key,value in [('passed',False),('executed',False),('cleanup_killed',True),
                              ('main_hwnd_seen',False),('close_posted',False),('detached_from_console',False),
                              ('exit_code',True),('exit_code',1),('error','bad'),('skips',['bad']),('fixture_binary_sha256',{})]:
                r=receipt(); (r if phase is None else r[phase])[key]=value; self.reject(r)
    def test_checks(self):
        for key in gui.CHECKS:
            for value in (False,1,None):
                r=receipt(); r['checks'][key]=value; self.reject(r)
            r=receipt(); del r['checks'][key]; self.reject(r)
    def test_exact_inventory(self):
        r=receipt(); r['languages'].reverse(); self.reject(r)
        r=receipt(); r['languages'].pop(); self.reject(r)
        r=receipt(); r['cases'].reverse(); self.reject(r)
        r=receipt(); r['cases'][0]['command']=True; self.reject(r)
        for index in range(len(gui.ALL_CASES)):
            for value in (None, 0, 1, not gui.ALL_CASES[index]['expect_rejected']):
                r=receipt(); r['cases'][index]['expect_rejected']=value; self.reject(r)
            r=receipt(); del r['cases'][index]['expect_rejected']; self.reject(r)
    def test_full_matrix_and_each_stage_required(self):
        self.assertEqual(len(gui.CASES),36)
        self.assertLessEqual(len(gui.ALL_CASES)+2,64)
        for index in range(len(gui.ALL_CASES)):
            for key in gui.CASE_CHECKS:
                for value in (False,1,None):
                    r=receipt(); r['cases'][index]['checks'][key]=value; self.reject(r)
                r=receipt(); del r['cases'][index]['checks'][key]; self.reject(r)
            r=receipt(); r['cases'].pop(index); self.reject(r)
    def test_collision_rejections_are_exact_and_distinct_from_noops(self):
        self.assertEqual(len(gui.ALL_CASES),62)
        rejected=[c for c in gui.ALL_CASES if c['expect_rejected']]
        self.assertEqual({c['command'] for c in rejected},{217,218,219})
        self.assertTrue(all(c['source']==c['target'] for c in rejected))
        self.assertTrue(any(c['source']==c['target'] and not c['expect_rejected'] for c in gui.ALL_CASES))

    def test_no_selection_and_virtual_terminal_are_explicit(self):
        cases={c['id']:c for c in gui.ALL_CASES}
        for command in (214,215,216):
            c=cases['no-selection-'+str(command)]
            self.assertEqual(c['source'],c['target'])
            self.assertEqual(c['anchor'],c['caret'])
        self.assertEqual(cases['empty-entities-dedup']['target'],b'\n')
        self.assertEqual(cases['terminal-virtual-only']['target'],b'\n')
        self.assertEqual(cases['selected-excludes-virtual']['target'],b'a\nb\n')

    def test_fixture_integrity_and_unicode_boundaries(self):
        self.assertEqual(len({c['id'] for c in gui.ALL_CASES}),len(gui.ALL_CASES))
        for c in gui.ALL_CASES:
            c['source'].decode(); c['target'].decode()
            self.assertEqual(c['mode'],gui.detected_mode(c['source']))
            for p in (c['anchor'],c['caret']):
                self.assertTrue(0 <= p <= len(c['source'])); c['source'][:p].decode()
            for p in c.get('selection') or ():
                self.assertTrue(0 <= p <= len(c['target'])); c['target'][:p].decode()
    def test_no_direct_mutation_substitution_or_drop(self):
        source=inspect.getsource(gui.run)
        for token in ('api.drop(', '2404', '2620', '2621', '2170', '2194', '2196', 'api.type_text('):
            self.assertNotIn(token,source)
        self.assertIn("api.command(hwnd, case['command'])",source)
    def test_resources_are_mandatory_and_duration_is_finite_under_five_seconds(self):
        for index in range(len(gui.RESOURCE_IDS)):
            r=receipt();r['resources'].pop(index);self.reject(r)
            for value in (True,False,None,-1,5,6,float('inf'),float('nan')):
                r=receipt();r['resources'][index]['duration_seconds']=value;self.reject(r)
            for key in gui.RESOURCE_CHECKS:
                for value in (False,1,None):
                    r=receipt();r['resources'][index]['checks'][key]=value;self.reject(r)
            for key in ('source_sha256','result_sha256','source_bytes','command'):
                r=receipt();r['resources'][index][key]=None;self.reject(r)
        r=receipt();r['resources'].reverse();self.reject(r)
    def test_resource_boundary_fixture_sizes_and_setup_are_distinct_from_edit(self):
        rows=gui.resource_cases()
        self.assertEqual(len(rows[0][2].splitlines()),gui.ROW_LIMIT+1)
        self.assertEqual(len(rows[1][2]),gui.BYTE_LIMIT+1)
        self.assertEqual(len(rows[2][2].splitlines()),gui.ROW_LIMIT)
        self.assertEqual(len(set(rows[2][2].splitlines())),gui.ROW_LIMIT)
        self.assertEqual(rows[2][2].splitlines(),sorted(rows[2][2].splitlines(),reverse=True))
        self.assertEqual(len(rows[4][2]),gui.BYTE_LIMIT)
        source=inspect.getsource(gui.run_resources)
        self.assertIn('api.command(hwnd,command)',source)
        self.assertNotIn('2170',source)
        setup=inspect.getsource(gui._fixture_buffer)
        self.assertIn('verify_owned_handles',setup)
        self.assertIn('api.scalar(editor,2181,0,remote)',setup)
        self.assertNotIn('api.scalar(editor,2170',setup)
        self.assertIn('api.scalar(editor,2182,size,remote) != size-1',setup)
        self.assertIn('WriteProcessMemory(handle,remote,buffer,size',setup)
        self.assertIn('ReadProcessMemory(handle,remote,buffer,size',setup)
        self.assertIn('Resource fixture seeded bytes differ',source)

    def test_mixed_ending_policy_and_non_normalized_unicode(self):
        cases={c['id']:c for c in gui.ALL_CASES}
        self.assertEqual(cases['mixed-sort-up']['target'],b'a\rb\nc\r\n')
        self.assertEqual(cases['mixed-dedup-terminated']['target'],b'b\ra\nc\n')
        self.assertEqual(cases['mixed-dedup-unterminated']['target'],b'b\ra')
        self.assertEqual(cases['combining-not-normalized']['target'],'é\né'.encode())

if __name__=='__main__': unittest.main()
