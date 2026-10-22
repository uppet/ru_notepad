#!/usr/bin/env python3
"""Synthetic controls only; no desktop/process launch or speed evidence."""
import os,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import run_markdown_dense_ab as a
import run_markdown_edit_profile as edit
import run_markdown_phase_profile as base
import test_markdown_edit_profile as fixtures
import windows_ci as ci
P=SimpleNamespace(edit=edit,base=base)
def seal():return {'identity':{'job':{'run_id':'123','run_attempt':'1','source_commit':'a'*40},'source_sha256':'b'*64,'compiler_commit':'c'*40,'compiler_tree':'d'*40},'build_receipt_sha256':['a'*64,'b'*64],'activation_receipt_sha256':['c'*64,'d'*64],'manifest_sha256':'e'*64,'native_origin_sha256':'f'*64,'compiler_binary_sha256':'9'*64,'fixture_sha256':base.FIXTURE_SHA256,'fixture_bytes':base.FIXTURE_SIZE,'runtime_sha256':[{n:'2'*64 for n in base.RUNTIME_NAMES} for _ in range(2)]}
def blank():
    v={'schema':1,'diagnostic_only':1,'product_acceptance_claimed':0,'windows_executed':0,'stage_deadline_seconds':30,'process_deadline_seconds':120,'seal':seal(),'order':list(a.ORDER),'attempted':[0]*8,'verified':[0]*8,'results':[edit.blank_public() for _ in a.ORDER]};a.recompute(v);return v
class Controls(unittest.TestCase):
    def run_case(self,late=False,stop=None,key='cleanup_unconfirmed',drift=None):
        with tempfile.TemporaryDirectory() as t:
            top=Path(t);roots=(top/'ordinary',top/'dense');output=top/'public';s=seal();calls=[];checks=[0]
            def check():
                checks[0]+=1
                if checks[0]==drift:raise ValueError('private')
                return s
            def run(root,expected,out,p,c):
                n=roots.index(root);i=len(calls);calls.append(n);x=fixtures.summary(late);x['runs']=x['runs'][:1];x['passed']=False;x['receipt_sha256']=s['build_receipt_sha256'][n];raw=x['runs'][0]
                if i==stop:raw.update({key:True,'diagnostic_complete':False,'passed':False})
                return raw,edit.public_projection(x,'d'*64,ci)
            error=None
            with patch.object(base,'ensure_local_launcher_directory'):
                try:v=a.measure(roots,s,output,P,check,runner=run,ci=ci)
                except ValueError as e:error=e;v=a.read(output/'markdown-dense-ab.json')
            self.assertEqual(v,a.read(output/'markdown-dense-ab.json'));a.validate_public(v,P)
            return v,calls,checks[0],error
    def test_blank_roundtrip(self):
        v=blank();self.assertLess(len(a.validate_public(v,P)),a.LIMIT)
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'out.json';a.save(p,v,P);a.save(p,v,P);self.assertEqual(v,a.read(p))
    def test_complete_eight_same_order(self):
        v,c,n,e=self.run_case();self.assertIsNone(e);self.assertEqual(c,list(a.ORDER));self.assertEqual(n,16);self.assertEqual(v['pair_complete'],[1]*4);self.assertEqual(v['passed'],1);self.assertEqual(v['pair_ratios'],[[1.0]*4]*4)
    def test_late_keeps_raw_never_complete_speed_pair(self):
        v,c,_,e=self.run_case(late=True);self.assertIsNone(e);self.assertEqual(len(c),8);self.assertEqual((v['diagnostic_complete'],v['passed'],v['product_gate_failed']),(1,0,1));self.assertEqual(v['pair_complete'],[0]*4);self.assertEqual(v['pair_ratios'],[[0]*4]*4);self.assertGreater(v['results'][0]['runs'][0]['stages'][-1]['wall_ms'],30000)
    def test_each_cleanup_failure_stops(self):
        for key in ('cleanup_unconfirmed','retained_output_unconfirmed','drop_cleanup_failed'):
            with self.subTest(key=key):
                v,c,_,e=self.run_case(stop=2,key=key);self.assertIsNone(e);self.assertEqual(len(c),3);self.assertEqual(v['verified'],[1,1,0,0,0,0,0,0]);self.assertEqual(v['pair_complete'],[1,0,0,0])
    def test_incomplete_without_cleanup_problem_stops(self):self.assertTrue(a.must_stop({'diagnostic_complete':False}))
    def test_post_run_drift_preserves_partial(self):
        v,c,_,e=self.run_case(drift=2);self.assertIsNotNone(e);self.assertEqual(c,[0]);self.assertEqual(v['results'][0]['runs'][0]['executed'],1);self.assertEqual(v['verified'],[0]*8)
    def test_pre_run_drift_no_false_execution(self):
        v,c,_,e=self.run_case(drift=1);self.assertIsNotNone(e);self.assertEqual(c,[]);self.assertEqual(v['windows_executed'],0)
    def test_public_mutations_rejected(self):
        mutations=[lambda v:v.update(raw='private'),lambda v:v.update(passed=True),lambda v:v.update(stage_deadline_seconds=31),lambda v:v.update(process_deadline_seconds=121),lambda v:v.update(order=[1]*8),lambda v:v['attempted'].__setitem__(1,1),lambda v:v['verified'].__setitem__(0,1),lambda v:v['pair_ratios'][0].__setitem__(0,float('nan')),lambda v:v['seal'].update(raw='private'),lambda v:v['pair_complete'].__setitem__(0,False),lambda v:v['pair_ratios'].__setitem__(0,[0]),lambda v:v['seal']['identity']['job'].update(run_id='private'),lambda v:v['seal']['runtime_sha256'][0].update(extra='a'*64),lambda v:v['seal']['runtime_sha256'][0].update(**{'RuSyntax.dll':'7'*64}),lambda v:v['seal'].update(activation_receipt_sha256=['bad']*2)]
        for change in mutations:
            v=blank();change(v)
            with self.subTest(change=change),self.assertRaises(Exception):a.validate_public(v,P)
    def test_wrong_arm_receipt_rejected(self):
        v,_,_,_=self.run_case();v['results'][0]['receipt_sha256']='b'*64
        with self.assertRaises(Exception):a.validate_public(v,P)
    def test_duplicate_json_and_links(self):
        with tempfile.TemporaryDirectory() as t:
            r=Path(t);p=r/'a';p.write_text('{"x":1,"x":2}')
            with self.assertRaises(Exception):a.read(p)
            q=r/'hard';os.link(p,q)
            with self.assertRaises(Exception):a.plain(q)
            q.unlink();q.symlink_to(p)
            with self.assertRaises(Exception):a.plain(q)
    def test_source_and_compiler_relation(self):
        with tempfile.TemporaryDirectory() as t:
            roots=tuple(Path(t)/n for n in ('ordinary','dense'));cc=Path(t)/'compiler'
            for r in (*roots,cc):r.mkdir()
            good={'src/main.ru':'b'*64}
            with patch.object(a,'checkout',side_effect=[good,good,{}]),patch.object(a,'git',return_value='d'*40),patch.object(a,'job',return_value={}):a.verify_sources(roots,cc,'a'*40,'c'*40,'d'*40)
            for values,tree in [([good,{},{}],'d'*40),([good,good,{}],'e'*40)]:
                with patch.object(a,'checkout',side_effect=values),patch.object(a,'git',return_value=tree),patch.object(a,'job',return_value={}),self.assertRaises(Exception):a.verify_sources(roots,cc,'a'*40,'c'*40,'d'*40)
            with self.assertRaises(Exception):a.verify_sources((roots[0],roots[0]),cc,'a'*40,'c'*40,'d'*40)
    def test_same_job(self):
        env={'GITHUB_RUN_ID':'123','GITHUB_RUN_ATTEMPT':'1','GITHUB_SHA':'a'*40}
        with patch.dict(os.environ,env):self.assertEqual(a.job('a'*40)['run_id'],'123')
        for key in env:
            bad=dict(env);bad[key]=''
            with patch.dict(os.environ,bad),self.assertRaises(Exception):a.job('a'*40)
    def test_debug_normalization_assignment_only(self):
        with tempfile.TemporaryDirectory() as t:
            roots=[Path(t)/x for x in ('a','b')]
            for i,r in enumerate(roots):
                (r/'src').mkdir(parents=True);(r/'build').mkdir();(r/'src/main.ru').write_text('');(r/'build/main.c').write_text('ru_source = "'+str(r/'src/main.ru')+'";\nv_fact('+str(i)+');\n')
            a.check_generated_pair(roots);p=roots[1]/'build/main.c';p.write_text(p.read_text()+'unrelated();\n')
            with self.assertRaises(Exception):a.check_generated_pair(roots)
            code='f("'+str(roots[0]/'src/main.ru')+'");\nru_source = "'+str(roots[0]/'src/main.ru')+'";';normalized,_=a.diagnostic_paths(code,roots[0]);self.assertIn('f("'+str(roots[0]),normalized)
    def test_verified_barrier(self):
        v,_,_,_=self.run_case();v['verified'][0]=0;a.recompute(v)
        with self.assertRaises(Exception):a.validate_public(v,P)
    def test_workflow_and_powershell_contract(self):
        root=Path(a.__file__).resolve().parents[1];w=(root/'.github/workflows/markdown-dense-ab.yml').read_text();ps=(root/'tools/run_markdown_dense_ci.ps1').read_text()
        self.assertIn('needs: linux-correctness',w);self.assertIn('branches: [mi-perf-prototype]',w);self.assertIn('cancel-in-progress: false',w)
        self.assertEqual(w.count('persist-credentials: false'),7);self.assertEqual(w.count('uses: actions/upload-artifact@'),1)
        self.assertIn('path: dense/build/markdown-dense-ab-public/markdown-dense-ab.json',w);self.assertIn('if: always()',w)
        self.assertIn('d78a29d51844acf23ee0a49129d0211c006ac737',w);self.assertIn('a853464d36d70dc358537e76dee7711ec6dbfecf',ps)
        self.assertIn('--experimental-markdown-dense',ps);self.assertIn('--experimental-mi-manifest',ps)
        self.assertEqual(w.count('-Stage controls -Arm '),2);self.assertEqual(w.count('-Stage application -Arm '),2)
        self.assertLess(w.index('sync-dlls --ordinary'),w.index('name: Build dense arm'))
        self.assertLess(w.index('check-built --ordinary'),w.index('name: Eight fresh owned'))
        self.assertNotIn('85c7821f',w+ps);self.assertNotIn('run_markdown_edit_ci.ps1',w)
    def test_no_old_prepare_pin(self):
        code=Path(a.__file__).read_text()
        for forbidden in ('85c7821f','6aa535d6','owned.prepare'):self.assertNotIn(forbidden,code)
if __name__=='__main__':unittest.main()
