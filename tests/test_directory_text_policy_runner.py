"""Independent oracle and acceptance-runner guard tests (no compiler needed)."""
import codecs
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('directory_text_policy_runner', Path(__file__).resolve().parents[1]/'tools/test_directory_text_policy.py')
r = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r)


class DirectoryTextOracleTests(unittest.TestCase):
    def test_boms_and_bom_free_offsets(self):
        for encoding,bom in [('utf-8',b''),('utf-8',codecs.BOM_UTF8),('utf-16le',codecs.BOM_UTF16_LE),('utf-16be',codecs.BOM_UTF16_BE)]:
            result=r.oracle(bom+'甲😀a'.encode(encoding),'a')
            self.assertEqual(result['rows'],[[7,8,1,3,[ord('甲'),ord('😀'),97],False,False]])
            self.assertEqual(result['utf8Bytes'],8)
            self.assertEqual(result['bom'],bool(bom))

    def test_crlf_terminators_share_preceding_line(self):
        self.assertEqual(r.oracle(b'a\r\nb','\n')['rows'][0][:4],[2,3,1,3])
        self.assertEqual(r.oracle(b'a\r\nb','b')['rows'][0][:4],[3,4,2,1])
        self.assertEqual(r.oracle(b'a\rb','b')['rows'][0][:4],[2,3,2,1])
        self.assertEqual(r.oracle(b'a\nb','b')['rows'][0][:4],[2,3,2,1])

    def test_nonoverlap_exact_case_no_normalization(self):
        self.assertEqual([x[:2] for x in r.oracle(b'aaaaa','aa')['rows']],[[0,2],[2,4]])
        self.assertEqual(r.oracle(b'A','a')['rows'],[])
        self.assertEqual(r.oracle('e\u0301'.encode(),'é')['rows'],[])

    def test_strict_decoding(self):
        for raw in (b'\xc0\xaf',b'\xed\xa0\x80',b'\xf4\x90\x80\x80',b'\xc2',b'\xe1\x80',b'\xf0\x90\x80',b'\x80'):
            self.assertEqual(r.decode(raw)[3],'invalid-utf8')
        for raw in (b'\xff\xfe\x00\xd8',b'\xfe\xff\xdc\x00',b'\xff\xfea'):
            self.assertEqual(r.decode(raw)[3],'invalid-utf16')
        for raw in (b'\xff\xfe\x00\x00',b'\x00\x00\xfe\xff'):
            self.assertEqual(r.decode(raw)[3],'unsupported-bom')
        self.assertEqual(r.decode(b'a\0')[3],'binary-nul')
        self.assertEqual(r.decode(b'a\0\xff')[3],'binary-nul')

    def test_empty_bom_only_and_no_guessing(self):
        for raw in (b'',codecs.BOM_UTF8,codecs.BOM_UTF16_LE,codecs.BOM_UTF16_BE):
            self.assertEqual(r.oracle(raw,'a')['status'],'complete')
        self.assertEqual(r.oracle(b'a\0','a')['reason'],'binary-nul')

    def test_preview_is_bounded_and_line_local(self):
        row=r.oracle(b'x'*100+b'a'*65,'a'*65)['rows'][0]
        self.assertEqual(row[4],[120]*32+[97]*64)
        self.assertEqual(row[5:],[True,True])
        self.assertEqual(r.oracle(b'xxxxxxxx\na','a')['rows'][0][4:],[ [97],False,False])

    def test_capacity_does_not_hide_late_invalid(self):
        self.assertEqual(r.oracle(b'aaa\xff','a',1)['rows'],[])
        self.assertEqual(r.oracle(b'aaa','a',0)['rows'],[])
        self.assertTrue(r.oracle(b'aaa','a',0)['capReached'])
        self.assertTrue(r.oracle(b'a','a',1)['capReached'])

    def test_unique_cases_full_budget_sweep_and_bounded_chunks(self):
        cases=r.cases(); names=[case[0] for case in cases]
        self.assertEqual(len(names),len(set(names)))
        runs=list(r.expected_runs(cases)); self.assertEqual(len(runs),len(set(name for name,_ in runs)))
        self.assertEqual(next(case[6] for case in cases if case[0]=='budget-sweep'),list(range(1,1025)))
        self.assertGreater(len(runs),4000)

    def test_pins_and_dirty_rejection(self):
        root=Path('compiler')
        with patch.object(r.subprocess,'check_output',side_effect=[r.PIN,r.TREE,'']): self.assertEqual(r.verify_compiler(root),r.PIN)
        for commit,tree in [(r.PIN[:7],r.TREE),(r.PIN,'0'*40)]:
            with patch.object(r.subprocess,'check_output',side_effect=[commit,tree]):
                with self.assertRaisesRegex(RuntimeError,'Wrong compiler identity'):r.verify_compiler(root)
        for dirty in (' M ru','?? rogue.py','M  ru'):
            with patch.object(r.subprocess,'check_output',side_effect=[r.PIN,r.TREE,dirty]):
                with self.assertRaisesRegex(RuntimeError,'must be clean'):r.verify_compiler(root)

    def test_output_is_exact_and_no_stderr_or_skip(self):
        for stdout,stderr in [('FAIL hidden',''),('SKIP hidden',''),('RESULT x','warning')]:
            with self.assertRaises(AssertionError): r.runtime_output(stdout,stderr,'test')
        rows=[['test',[97],[97],2000,'normal',False,[1],'complete||utf-8|0|1|0|0,1,1,1:97:0,0']]
        protocols=['invalid-queries']+[f'size-{i}' for i in range(6)]+[f'slots-{i}' for i in range(6)]+[f'bytes-{i}' for i in range(7)]
        protocols += ['chunk-limit','wrong-offset','declared-overrun','feed-running','eof-running','eof-nonboolean','eof-null']
        protocols += [f'budget-{i}' for i in range(7)]+[f'program-{i}' for i in range(6)]+['cancel-preview','cancel-commit','maximum-cap']+[f'metadata-{i}' for i in range(3)]
        output=''.join('PROTOCOL '+p+'\n' for p in protocols)+'RESULT test--1-1 '+rows[0][7]+'\nTOTAL PASS: 1\n'
        self.assertEqual(r.verify(output,rows),1)
        with self.assertRaises(AssertionError):r.verify(output.replace('0,1,1,1','1,2,1,2'),rows)
        with self.assertRaises(AssertionError):r.verify(output.replace('TOTAL PASS: 1','TOTAL PASS: 2'),rows)

    def test_canonical_fixture_is_not_generated_substitute(self):
        source=(r.ROOT/'tests/directory_text_policy.ru').read_text()
        start=source.index('# BEGIN CASES');end=source.index('# END CASES')
        self.assertEqual(source[start:end],'# BEGIN CASES\n'+r.table(r.cases()))


if __name__=='__main__': unittest.main()
