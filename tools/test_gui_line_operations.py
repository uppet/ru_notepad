"""Portable fail-closed receipt contracts, not Windows execution evidence."""
import inspect
import unittest
import gui_line_operations as gui
HASHES = {'ru_notepad.exe': 'a'*64}


def receipt(hashes=HASHES):
    row = dict(passed=True, executed=True, cleanup_killed=False, main_hwnd_seen=True,
               close_posted=True, detached_from_console=True, exit_code=0, fixture_binary_sha256=dict(hashes))
    return dict(row, schema='ru-notepad-line-operations-gui-v1', name='main-gui-line-operations',
                reopen=dict(row, name='main-gui-line-reopen'), checks=dict.fromkeys(gui.CHECKS, True),
                languages=list(gui.LANGUAGES), cases=gui.expected_cases())


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
        self.assertEqual(len(gui.CASES),24)
        self.assertLessEqual(len(gui.ALL_CASES)+2,64)
        for index in range(len(gui.ALL_CASES)):
            for key in gui.CASE_CHECKS:
                for value in (False,1,None):
                    r=receipt(); r['cases'][index]['checks'][key]=value; self.reject(r)
                r=receipt(); del r['cases'][index]['checks'][key]; self.reject(r)
            r=receipt(); r['cases'].pop(index); self.reject(r)
    def test_collision_rejections_are_exact_and_distinct_from_noops(self):
        self.assertEqual(len(gui.ALL_CASES),46)
        rejected=[c for c in gui.ALL_CASES if c['expect_rejected']]
        self.assertEqual({c['command'] for c in rejected},{210,211,213})
        self.assertEqual([c['source'] for c in rejected],[b'\ra\nb',b'\na\rz',b'\r \nb'])
        self.assertTrue(all(c['source']==c['target'] for c in rejected))
        self.assertTrue(any(c['source']==c['target'] and not c['expect_rejected'] for c in gui.ALL_CASES))

    def test_equal_line_moves_are_clean_noops(self):
        cases={c['id']:c for c in gui.ALL_CASES}
        for name,source in [('equal-content-down',b'a\na'),('equal-empty-down',b'\n\nx')]:
            c=cases[name]
            self.assertEqual((c['source'],c['target'],c['command'],c['anchor'],c['caret']),
                             (source,source,212,0,0))
            self.assertIs(c['expect_rejected'],False)

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
    def test_unicode_space_is_not_trimmed_and_outside_lines_unchanged(self):
        for c in gui.CASES:
            if c['command']==213:
                eol=next(e for _,e,m in gui.EOLS if m==c['mode'])
                lines=c['target'].split(eol)
                self.assertEqual(lines[0],gui.LINES[0]); self.assertEqual(lines[-1],gui.LINES[-1])
                self.assertTrue(lines[2].endswith('\u3000'.encode()))

if __name__=='__main__': unittest.main()
