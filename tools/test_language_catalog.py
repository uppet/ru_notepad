#!/usr/bin/env python3
"""Fail-closed catalog/menu/source coverage and fixed lexical-oracle checks."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from generate_syntax_catalog import generate, quote
from generate_language_samples import render

ROOT=Path(__file__).resolve().parents[1]
DATA=json.loads((ROOT/'syntax/languages.json').read_text(encoding='utf-8'))
ROWS=DATA['languages']; BY_ID={r['id']:r for r in ROWS}
BASELINE=json.loads((ROOT/'syntax/notepadpp-baseline.json').read_text(encoding='utf-8'))
SAMPLES=json.loads((ROOT/'tests/language_samples.json').read_text(encoding='utf-8'))

class CatalogTests(unittest.TestCase):
    def test_exact_inventory_and_generated_sources(self):
        self.assertEqual(len(ROWS),95); self.assertEqual(len(BY_ID),95)
        baseline=[r['source'].get('npp_mode') for r in ROWS if 'npp_mode' in r['source']]
        self.assertEqual(len(baseline),93); self.assertEqual(len(set(baseline)),93)
        self.assertEqual(DATA['baseline'],'Notepad++ v8.9.8.1')
        official={r['id']:r for r in BASELINE['languages']}
        self.assertEqual(BASELINE['tag'],'v8.9.8.1')
        self.assertEqual(BASELINE['mode_count'],93)
        self.assertEqual(len(BASELINE['languages']),93)
        self.assertEqual(len(official),93)
        self.assertEqual(set(baseline),set(official))
        self.assertEqual({r['id'] for r in ROWS if 'npp_mode' not in r['source']}, {'ru','markdown'})
        display_aliases={'normal':'Plain text','ini':'INI','json':'JSON',
                         'registry':'Registry','json5':'JSON5','mssql':'MS SQL'}
        for row in ROWS:
            mode=row['source'].get('npp_mode')
            if mode is None:continue
            with self.subTest(npp_mode=mode):
                expected=official[mode]
                self.assertEqual(row['id'],'plain' if mode=='normal' else mode)
                self.assertEqual(row['name'],display_aliases.get(mode,expected['name']))
                self.assertEqual(row['lexer'],expected['lexer'])
                self.assertEqual(row['extensions'],expected['extensions'])
        for source in BASELINE['sources']:
            self.assertTrue(source['url'].endswith('/v8.9.8.1/'+source['path']))
            self.assertRegex(source['sha256'],r'^[0-9a-f]{64}$')
        self.assertEqual((ROOT/'src/syntax_catalog.ru').read_text(),generate(DATA))
        self.assertEqual((ROOT/'tests/language_samples.ru').read_text(),render(SAMPLES))
    def test_config_types_and_palettes(self):
        for p in ROWS:
            with self.subTest(language=p['id']):
                self.assertEqual(len(p['style_ids']),len(p['style_colors']))
                self.assertEqual(p['style_ids'],sorted(set(p['style_ids'])))
                self.assertTrue(all(0<=i<256 and not 32<=i<=39 for i in p['style_ids']))
                self.assertTrue(all(type(c) is int and 0<=c<=0xFFFFFF for c in p['style_colors']))
                self.assertEqual(len(p['properties'])%2,0)
                self.assertLessEqual(len(p['keywords']),16)
                self.assertTrue(all(isinstance(k,str) and '\0' not in k and '$(' not in k for k in p['keywords']))
                self.assertTrue(all(isinstance(k,str) and '\0' not in k for k in p['properties']))
    def test_legacy_configs_match_preserved_runtime(self):
        source=(ROOT/'src/syntax.ru').read_text(encoding='utf-8')
        for language in ('cpp','json','markdown'):
            with self.subTest(language=language):
                block=source.split("若 语言 == '"+language+"' 则\n",1)[1].split('\n    另',1)[0]
                keywords=re.findall(r"_发文设 态 柄 4005 (\d+) '([^']*)'",block)
                self.assertEqual([int(slot) for slot,_ in keywords],list(range(len(keywords))))
                self.assertEqual(BY_ID[language]['keywords'],[word for _,word in keywords])
                properties=re.findall(r"_性质 态 柄 '([^']*)' '([^']*)'",block)
                self.assertEqual(BY_ID[language]['properties'],[v for pair in properties for v in pair])
                self.assertEqual(BY_ID[language]['fold'],language=='cpp')
                for key,var in [('style_ids','色号们'),('style_colors','色值们')]:
                    self.assertEqual(BY_ID[language][key],json.loads(re.search(var+r' 取 (\[[^\n]+\])',block)[1]))
    def test_each_mode_visible_in_menu(self):
        for p in ROWS:
            if p['id'] in ('plain','cpp','json','ru','markdown'):continue
            first=p['name'][0].lower()
            self.assertEqual(sum(first in group for group in ('abcd','efgh','ijkl','mnop','qrst','uvwxyz')),1,p['id'])
        main=(ROOT/'src/main.ru').read_text()
        self.assertIn("语策 其 从命令 号",main)
        self.assertIn('若 组位 == 4 则 扩展语法菜单 子. 然',main)
        self.assertIn("语选 != '' 且 语选 != 'plain'",main)
    def test_detection_precedence_and_extra_legacy_suffixes(self):
        for ext,language in DATA['extensions'].items():
            self.assertIn(language,BY_ID);self.assertEqual(ext,ext.lower())
        self.assertEqual(DATA['extensions']['tex'],'tex')
        self.assertEqual(DATA['extensions']['m'],'matlab')
        for ext in ('c++','h++','inl'):self.assertEqual(DATA['extensions'][ext],'cpp')
        self.assertEqual(DATA['extensions']['c'],'c')
        self.assertEqual(DATA['extensions']['jsonc'],'json5')
        self.assertEqual(DATA['filenames']['cmakelists.txt'],'cmake')
    def test_keywords_dialects_and_missing_lexer(self):
        self.assertIn('echo',BY_ID['php']['keywords'][4].split())
        self.assertTrue(all(not x for x in BY_ID['php']['keywords'][:4]))
        self.assertIn('interface',BY_ID['typescript']['keywords'][0].split())
        self.assertIn('const',BY_ID['javascript.js']['keywords'][0].split())
        self.assertNotIn('class',BY_ID['c']['keywords'][0].split())
        self.assertEqual(BY_ID['objc']['lexer_id'],151)
        self.assertEqual(BY_ID['objc']['lexer'],'objc')
        self.assertIn('func',BY_ID['gdscript']['keywords'][0].split())
        self.assertIn('select',BY_ID['mssql']['keywords'][0].lower().split())
    def test_fixed_token_oracles_cover_every_mode(self):
        self.assertEqual({x['id'] for x in SAMPLES},set(BY_ID))
        self.assertEqual(len(SAMPLES),95)
        for row in SAMPLES:
            with self.subTest(language=row['id']):
                if row['style']<0:
                    self.assertIn(row['id'],('plain','nfo','ru','markdown'));continue
                self.assertGreater(row['length'],0)
                self.assertGreater(row['style'],0)
                raw=row['text'].encode('utf-8')
                self.assertEqual(raw[row['position']:row['position']+row['length']],row['marker'].encode('utf-8'))
                colors=dict(zip(BY_ID[row['id']]['style_ids'],BY_ID[row['id']]['style_colors']))
                self.assertIn(row['style'],colors)
                self.assertNotEqual(colors[row['style']],0x1F1F1F)
    def test_all_three_legacy_palettes_remain_exact(self):
        source=(ROOT/'src/syntax.ru').read_text()
        for lang in ('cpp','json','markdown'):
            block=source.split("若 语言 == '"+lang+"' 则",1)[1].split('另',1)[0]
            self.assertEqual(BY_ID[lang]['style_ids'],json.loads(re.search(r'色号们 取 (\[[^\n]+\])',block)[1]))
            self.assertEqual(BY_ID[lang]['style_colors'],json.loads(re.search(r'色值们 取 (\[[^\n]+\])',block)[1]))

def portable(root):
    # Exercise actual shared Ru policy. Expected answers come from frozen JSON,
    # not from invoking the policy to generate its own expected output.
    lines=["策 取 外言 "+quote(str(ROOT/'src/syntax_policy.ru'))+'.', '数们 取 [0].',
           '作 确认 条件 为 事实:',"    若 非 条件 则 卒 'catalog policy mismatch'. 然",
           '    数们[0] 取 数们[0]+1.','为']
    count=0
    def add(expr):
        nonlocal count
        lines.append('确认 ('+expr+').');count+=1
    for row in ROWS:
        key=quote(row['id'])
        add('(策 其 从命令 (策 其 命令 '+key+')) == '+key)
        if row['id']!='plain':add('(策 其 名称 '+key+') == '+quote(row['name']))
    for ext,key in DATA['extensions'].items():
        for e in (ext,ext.upper()):add('(策 其 识别 '+quote('C:/甲😀/file.'+e)+') == '+quote(key))
    for name,key in DATA['filenames'].items():
        add('(策 其 识别 '+quote('C:\\path\\'+name.upper())+') == '+quote(key))
    for path in ('C:/folder.cpp/README','C:\\folder.py\\README','data.py.bak','data.pythonx','file.py ','file.py\n'):
        add('(策 其 识别 '+quote(path)+") == 'plain'")
    lines.append("显 'CATALOG POLICY PASS: '+(数们[0] 为 句).")
    with tempfile.TemporaryDirectory(prefix='ru-language-catalog-') as tmp:
        path=Path(tmp)/'policy.ru';path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
        proc=subprocess.run([sys.executable,str(root/'ru'),'run',str(path)],capture_output=True,text=True,timeout=120)
        if proc.returncode or proc.stdout.strip()!=f'CATALOG POLICY PASS: {count}':
            raise RuntimeError(proc.stdout+'\n'+proc.stderr)
        print(proc.stdout.strip())

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--ru-root',type=Path);args,remaining=parser.parse_known_args()
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CatalogTests))
    if not result.wasSuccessful():raise SystemExit(1)
    if args.ru_root:portable(args.ru_root.resolve())
