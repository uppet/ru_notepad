"""Portable fail-closed receipt contracts, NOT evidence of Windows execution."""
import inspect
import unittest
import gui_open_search as gui

HASHES = {'ru_notepad.exe': 'a'*64}


def layouts():
    rows=[]
    for language in gui.LANGUAGES:
        for size in gui.LAYOUT_SIZES:
            for bar in (False,True):
                rects={'10':[0,0,600,20], '0':[0,20,600,150], '11':[0,310,600,330],
                       '320':[0,150,600,220], '321':[0,220,600,240],
                       '322':[0,240,100,260], '318':[100,240,200,260], '319':[200,240,300,260]}
                if bar:
                    for i,n in enumerate(gui.SEARCH_CONTROLS):
                        rects[str(n)]=[(i%6)*100,270+(i//6)*12,(i%6+1)*100,280+(i//6)*12]
                rows.append(dict(language=language,requested=list(size),search_bar=bar,
                                 outer=list(size),client=[size[0]-16,size[1]-60],rectangles=rects,
                                 minimum_widths={str(n):80 for n in (gui.OPEN,gui.STOP,gui.HIDE)},
                                 list_item_height=18,list_client_height=68))
    return rows


def receipt(hashes=HASHES):
    return dict(schema='ru-notepad-open-search-gui-v1',name='main-gui-open-search',
                passed=True,executed=True,cleanup_killed=False,main_hwnd_seen=True,
                close_posted=True,detached_from_console=True,exit_code=0,
                fixture_binary_sha256=dict(hashes),fixtures=gui.inventory(),
                checks=dict.fromkeys(gui.CHECKS,True),cases=[c[0] for c in gui.cases()],
                layouts=layouts(),engine_gates=list(gui.ENGINE_GATES),manual_gates=list(gui.MANUAL_GATES))


class Contract(unittest.TestCase):
    def reject(self,row):
        with self.assertRaises(ValueError):gui.validate_result(row,HASHES)
    def test_complete_contract_not_execution(self):
        self.assertTrue(gui.validate_result(receipt(),HASHES))
        other={'ru_notepad.exe':'b'*64}
        self.assertTrue(gui.validate_result(receipt(other),other))
    def test_all_fields_required(self):
        for key in receipt():
            with self.subTest(key=key):
                row=receipt();del row[key];self.reject(row)
    def test_native_lifecycle_fail_closed(self):
        for key,value in (('passed',False),('passed',1),('executed',False),('executed',1),
                          ('cleanup_killed',True),('cleanup_killed',0),('main_hwnd_seen',False),
                          ('close_posted',False),('detached_from_console',False),('exit_code',True),
                          ('exit_code',1),('error','failure'),('skips',['case']),('fixture_binary_sha256',{}),
                          ('schema','other'),('name','other')):
            row=receipt();row[key]=value;self.reject(row)
    def test_checks_never_accept_truthy_substitutes(self):
        for key in gui.CHECKS:
            for value in (False,1,None,'true'):
                row=receipt();row['checks'][key]=value;self.reject(row)
            row=receipt();del row['checks'][key];self.reject(row)
        row=receipt();row['checks']['unobserved_extra']=True;self.reject(row)
    def test_inventory_and_companion_gates_required(self):
        for field in ('fixtures','cases','engine_gates','manual_gates'):
            row=receipt();row[field].reverse();self.reject(row)
            row=receipt();row[field].pop();self.reject(row)
        row=receipt();row['fixtures'][0]['sha256']='0'*64;self.reject(row)
        self.assertEqual(len(gui.fixtures()),8)
        self.assertEqual(len(gui.cases()),12)
    def test_layout_inventory(self):
        self.assertEqual(len(layouts()),28)
        for index in range(28):
            row=receipt();row['layouts'].pop(index);self.reject(row)
            for key,value in (('outer',[639,400]),('client',[700,900]),('requested',[640,399]),
                              ('language','unknown'),('search_bar',1)):
                row=receipt();row['layouts'][index][key]=value;self.reject(row)
            for control in gui.RESULT_CONTROLS:
                row=receipt();del row['layouts'][index]['rectangles'][str(control)];self.reject(row)
            if index%2:
                for control in gui.SEARCH_CONTROLS:
                    row=receipt();del row['layouts'][index]['rectangles'][str(control)];self.reject(row)
    def test_geometry_overlap_and_translation_clipping(self):
        for rect in ([0,0,600,220],[-1,150,600,220],[0,150,700,220],[0,150,600,150],[False,150,600,220]):
            row=receipt();row['layouts'][0]['rectangles']['320']=rect;self.reject(row)
        for minimum in (True,0,-1,101):
            row=receipt();row['layouts'][0]['minimum_widths']['322']=minimum;self.reject(row)
        row=receipt();row['layouts'][1]['rectangles']['310']=[0,100,100,120];self.reject(row)
        for field in ('rectangles','minimum_widths'):
            row=receipt();row['layouts'][0][field]=None;self.reject(row)
    def test_list_requires_complete_native_row_excluding_border(self):
        for index in range(28):
            for field,value in (('list_item_height',0),('list_item_height',True),('list_item_height',-1),
                                ('list_item_height',69),('list_client_height',17),('list_client_height',True),
                                ('list_client_height',71)):
                row=receipt();row['layouts'][index][field]=value;self.reject(row)
            row=receipt();row['layouts'][index]['list_client_height']=18
            self.assertTrue(gui.validate_result(row,HASHES))
            for field in ('list_item_height','list_client_height'):
                row=receipt();del row['layouts'][index][field];self.reject(row)
    def test_native_maxtrack_clamp_recorded(self):
        row=receipt()
        for layout in row['layouts']:
            if layout['requested']==[1120,760]:layout['outer']=[1044,760];layout['client']=[1028,700]
        self.assertTrue(gui.validate_result(row,HASHES))
    def test_fixture_oracle_counts_and_utf8_ranges(self):
        sources=gui.fixtures()
        for _,query,case,whole,total in gui.cases():
            found=[]
            for name,data in sources.items():
                for a,b in gui.expected_ranges(data,query,case,whole):
                    self.assertTrue(0<=a<b<=len(data));data[:a].decode();data[:b].decode()
                    found.append((name,a,b))
            self.assertEqual(len(found),total,query)
        data=sources['boundary.txt'];a,b=gui.expected_ranges(data,'汉😀edge',True,False)[0]
        self.assertLess(a,65536);self.assertGreater(b,65536)
        a,b=gui.expected_ranges(sources['casefold.txt'],'STRASSE',False,False)[0]
        self.assertLess(a,65536);self.assertGreater(b,65536)
        self.assertEqual(sum(len(gui.expected_ranges(d,'capword',True,False)) for d in sources.values()),2001)
        with self.assertRaises(ValueError):gui.expected_ranges(b'abc','',True,False)
    def test_distinct_duplicate_basenames_and_mixed_eol(self):
        sources=gui.fixtures()
        self.assertNotEqual(sources['left/same.txt'],sources['right/same.txt'])
        self.assertIn(b'\r\n',sources['left/same.txt']);self.assertNotIn(b'\r',sources['right/same.txt'])
        self.assertIn(b'\r',sources['cr.txt']);self.assertNotIn(b'\n',sources['cr.txt'])
    def test_budget_contract_not_false_gui_proof(self):
        self.assertEqual((gui.STARTS_PER_TICK,gui.HITS_PER_TICK,gui.TIMER_MS,gui.MAX_ROWS),(65536,16,20,2000))
        self.assertIn('reorder_preserves_identity',gui.ENGINE_GATES)
        self.assertNotIn('reorder_preserves_identity',gui.CHECKS)
        self.assertIn('failed_status_and_cleanup',gui.ENGINE_GATES)
        self.assertIn('No tab-reorder UI exists',gui.MANUAL_GATES[0])
        self.assertIn('No native allocation-failure injection',gui.MANUAL_GATES[1])
    def test_only_observed_checks_recorded(self):
        source=inspect.getsource(gui.run)
        self.assertNotIn('dict.fromkeys(CHECKS,True)',source)
        for key in set(gui.CHECKS)-{'cancel','hide_cancels'}:
            self.assertIn("checks['"+key+"']=True",source)
        self.assertIn("((STOP,'cancel'),(HIDE,'hide_cancels'))",source)
        self.assertIn('checks[key]=True',source)
    def test_native_ui_and_owned_lifecycle(self):
        source=inspect.getsource(gui.run)
        for token in ('isolated_settings()', 'ci.run_gui(', '_copy_runtime(', 'api.command(hwnd,START)',
                      'api.command(hwnd,OPEN)', 'api.command(hwnd,105)', 'api.drop(hwnd,[paths[\'cr.txt\']])',
                      'snapshot()!=before', 'native_layout(', "ROOT/'locales/open_search.json'", 'api.command(hwnd,505)',
                      "key='search.results_'+status",'api.scalar(result_list,0x202,0,5|(5<<16))'):
            self.assertIn(token,source)
        for token in ('WriteProcessMemory','SCI_SETTEXT','SendInput','subprocess','set(range(length))'):
            self.assertNotIn(token,source)
        self.assertLess(source.index("start('absent-acceptance-needle');finish();api.responsive(hwnd)"),source.index('for name,query,case,whole,total in cases():'))
    def test_native_layout_measurement(self):
        source=inspect.getsource(gui.native_layout)
        for token in ('MoveWindow','GetWindowRect','GetClientRect','ClientToScreen','GetTextExtentPoint32W','SelectObject','ReleaseDC',
                      'LB_GETITEMHEIGHT','list_client.bottom-list_client.top'):
            self.assertIn(token,source)
        self.assertNotIn('Subclass',source)

if __name__=='__main__':unittest.main()
