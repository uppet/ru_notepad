"""Portable receipt rejection tests, never Windows execution evidence."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import verify_directory_io_windows as gate
from bootstrap_provenance import InvalidProvenance


class DirectoryIoReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name)
        def file(name, data=b'synthetic unit-test bytes'):
            p=root/name;p.write_bytes(data);return gate.identity(p)
        result={'status':'pass','required_case_ids':list(gate.suite.REQUIRED_CASE_IDS),
                'cases':[{'id':x,'status':'pass'} for x in gate.suite.REQUIRED_CASE_IDS],
                'skipped':[],'limitations':list(gate.LIMITATIONS),
                'invocations':[{'returncode':0,'stdout':'synthetic unit test','stderr':''}]}
        self.hashes={'RuSyntax.dll':'synthetic-hash'}
        self.report={'schema':gate.SCHEMA,'status':'passed','platform':'win32',
                     'runtime_sha256':self.hashes,'source_sha256':{n:gate.sha(gate.ROOT/n) for n in gate.INPUTS},
                     'fault_dll_shipped':False,'compiler':file('cc.exe'),
                     'host':file('host.exe'),'fault_dll':file('fault.dll'),
                     'result':result,'suite_receipt':file('suite.json',json.dumps(result).encode()),'builds':[]}
        for name in ('host','fault_dll'):
            self.report['builds'].append({'returncode':0,'timeout':False,
                'command':gate.command_for(name,self.report['compiler']['path'],self.report[name]['path']),
                'stdout':file(name+'.stdout',b''),'stderr':file(name+'.stderr',b'')})

    def write_suite(self,report):
        p=Path(report['suite_receipt']['path']);p.write_text(json.dumps(report['result']))
        report['suite_receipt']=gate.identity(p)

    def test_complete_synthetic_receipt_structure(self):
        gate.validate_result(self.report,self.hashes)
        self.assertEqual(len(gate.suite.REQUIRED_CASE_IDS),20)

    def test_missing_failed_duplicate_and_extra_case(self):
        for mode in ('missing','failed','duplicate','extra'):
            r=copy.deepcopy(self.report)
            if mode=='missing':r['result']['cases'].pop()
            elif mode=='failed':r['result']['cases'][0]['status']='fail'
            elif mode=='duplicate':r['result']['cases'][1]=r['result']['cases'][0]
            else:r['result']['cases'].append({'id':'invented','status':'pass'})
            self.write_suite(r)
            with self.subTest(mode=mode),self.assertRaises(InvalidProvenance):gate.validate_result(r,self.hashes)

    def test_skips_timeouts_limits_and_result_mismatch(self):
        for mode in ('skip','timeout','limitation','status','missing-invocations','no-returncode'):
            r=copy.deepcopy(self.report)
            if mode=='skip':r['result']['skipped']=['unavailable']
            elif mode=='timeout':r['result']['invocations'][0]['status']='timeout'
            elif mode=='limitation':r['result']['limitations'].pop()
            elif mode=='status':r['result']['status']='fail'
            elif mode=='missing-invocations':r['result']['invocations']=[]
            else:r['result']['invocations'][0]['returncode']=None
            self.write_suite(r)
            with self.subTest(mode=mode),self.assertRaises(InvalidProvenance):gate.validate_result(r,self.hashes)

    def test_wrong_source_runtime_platform_build_or_shipping(self):
        for mode in ('source','runtime','platform','build','shipping','failed'):
            r=copy.deepcopy(self.report)
            if mode=='source':r['source_sha256']['native/ru_directory_io.c']='wrong'
            elif mode=='runtime':r['runtime_sha256']={}
            elif mode=='platform':r['platform']='linux'
            elif mode=='build':r['builds'][1]['command'].remove('-DRU_DIR_TESTING')
            elif mode=='shipping':r['fault_dll_shipped']=True
            else:r['builds'][0]['returncode']=1
            with self.subTest(mode=mode),self.assertRaises(InvalidProvenance):gate.validate_result(r,self.hashes)

    def test_modified_evidence_rejected(self):
        for name in ('compiler','host','fault_dll','suite_receipt'):
            p=Path(self.report[name]['path']);old=p.read_bytes();p.write_bytes(old+b'changed')
            try:
                with self.subTest(name=name),self.assertRaises(InvalidProvenance):gate.validate_result(self.report,self.hashes)
            finally:p.write_bytes(old)

    def test_non_windows_never_becomes_native_acceptance(self):
        with patch.object(gate.sys,'platform','linux'),self.assertRaises(InvalidProvenance):
            gate.run('runtime','evidence',{})

    def test_product_and_package_require_both_directory_gates(self):
        product=(ROOT/'tools/verify_bootstrap_product_windows.py').read_text()
        for key in ('directory_io','directory_search'):
            self.assertIn("report.get('"+key+"')",product)
            self.assertIn("report['"+key+"'] = run_"+key,product)
        package=(ROOT/'tools/package_bootstrap_preview.py').read_text()
        self.assertIn("'directory_search_gui': True",package)
        self.assertIn("'directory_io_windows': True",package)
        self.assertIn('directory-search.md',package)

if __name__=='__main__':unittest.main()
