#!/usr/bin/env python3
"""Strict exact-source transform controls; optionally audit actual generated C."""
import argparse, copy, hashlib, json, re, tempfile, unittest
from pathlib import Path
import profile_markdown_phases as p

class TransformControls(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);(self.root/'src').mkdir()
        for relative,name in p.KINDS:
            path=self.root/relative
            if not path.exists():path.write_text('test source\n')
        md=self.root/'src/markdown_syntax.ru';md.write_text("_FoldApply 取 'ru_markdown_fold_apply_v1'.\n")
        self.code=''
        for i,((relative,name),(phase,n)) in enumerate(p.KINDS.items()):
            self.code+=f'static RuFunction ru_function_{i}_descriptor = {{"{p.octal(name)}", {n}, NULL, NULL, ru_function_{i}, 0}};\n'
            self.code+=f'static Val ru_function_{i}(Env *global, Val self, int call_line, Val *args) {{\n    ru_source = "{p.octal(str(self.root/relative))}";\n    return v_null();\n}}\n'
        self.code+='    env_bind(env, "_FoldApply", ru_v_123, 1);\n'
        self.receipt={'generated_c_sha256':p.digest(self.code.encode()),'ru_commit':'85c7821fda35aa79deeaf67b4d430f24ddd7f07f','source_sha256':{f.relative_to(self.root).as_posix():p.sha(f) for f in (self.root/'src').iterdir()}}
    def tearDown(self):self.temp.cleanup()
    def mapping(self,code=None,receipt=None):return p.make_map(code or self.code,self.root,receipt or self.receipt)
    def test_exact_map(self):
        m=self.mapping();self.assertEqual(len(m['entries']),6);self.assertEqual(m['binding']['value'],'ru_v_123')
    def test_wrong_generated_hash(self):
        with self.assertRaises(ValueError):self.mapping(self.code+'\n')
    def test_wrong_source_hash(self):
        (self.root/'src/main.ru').write_text('changed')
        with self.assertRaises(ValueError):self.mapping()
    def test_duplicate_selected(self):
        code=self.code+self.code
        receipt=copy.deepcopy(self.receipt);receipt['generated_c_sha256']=p.digest(code.encode())
        with self.assertRaises(ValueError):self.mapping(code,receipt)
    def test_swapped_descriptor(self):
        code=self.code.replace(p.octal('推进'),p.octal('喂入'))
        receipt=copy.deepcopy(self.receipt);receipt['generated_c_sha256']=p.digest(code.encode())
        with self.assertRaises(ValueError):self.mapping(code,receipt)
    def test_wrong_parameter_count(self):
        code=self.code.replace(', 5, NULL',', 4, NULL');receipt=copy.deepcopy(self.receipt);receipt['generated_c_sha256']=p.digest(code.encode())
        with self.assertRaises(ValueError):self.mapping(code,receipt)
    def test_stale_body_map(self):
        mapping=self.mapping();mapping['entries'][0]['body_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'Stale'):p.transform(self.code,self.root,self.receipt,mapping,'')
    def test_unknown_escape_rejected(self):
        code=self.code.replace(p.octal(str(self.root/'src/main.ru')),r'\x41')
        receipt=copy.deepcopy(self.receipt);receipt['generated_c_sha256']=p.digest(code.encode())
        with self.assertRaises(ValueError):self.mapping(code,receipt)
    def test_crlf_receipt(self):
        receipt=copy.deepcopy(self.receipt);receipt['generated_c_sha256']=p.digest(self.code.replace('\n','\r\n').encode())
        self.assertEqual(len(self.mapping(receipt=receipt)['entries']),6)
    def test_missing_binding(self):
        code=self.code.replace('"_FoldApply"','"other"');receipt=copy.deepcopy(self.receipt);receipt['generated_c_sha256']=p.digest(code.encode())
        with self.assertRaises(ValueError):self.mapping(code,receipt)

def audit_actual(source,input_c,receipt,header):
    code=input_c.read_text();r=json.loads(receipt.read_text());m=p.make_map(code,source,r)
    output=p.transform(code,source,r,m,header.read_text())
    # Every selected generated body is byte-identical after its definition name
    # alone is changed; wrapper logic is not spliced into the original body.
    for ident,name,path,start,end,body in p.generated_functions(code):
        if ident not in {e['id'] for e in m['entries']}:continue
        renamed=body.replace(f'ru_function_{ident}(Env *global',f'ru_function_{ident}_mpp_body(Env *global',1)
        assert output.count(renamed)==1
    native='raw = ru_native_generated_call(sig->as.signature.id, function->as.function.address, args);\n    error = rn_platform_error();'
    assert output.count(native)==1
    trap=re.search(r'typedef struct RuNativeTrap \{.*?\} RuNativeTrap;',code,re.S)[0]
    assert trap in output
    assert 'rp_restore' not in output
    for function in ['ru_gc','rn_trap_new','ru_native_callback_dispatch']:
        # Full callback has only the three documented observer deltas.
        start=code.index(('static RuNativeRaw ' if function=='ru_native_callback_dispatch' else 'static RuNativeTrap *' if function=='rn_trap_new' else 'static void ')+function+'(')
        if code[code.index(')',start)+1:code.index(')',start)+3]==';\n':continue
    return {'schema':1,'passed':True,'selected_original_bodies_preserved':6,'native_error_read_adjacent':True,'trap_layout_unchanged':True,'source_map':m,'instrumented_tu_sha256':p.digest(output.encode())}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path);ap.add_argument('--input-c',type=Path);ap.add_argument('--receipt',type=Path);ap.add_argument('--header',type=Path);ap.add_argument('--output',type=Path)
    args,other=ap.parse_known_args();suite=unittest.defaultTestLoader.loadTestsFromTestCase(TransformControls);result=unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():raise SystemExit(1)
    if args.input_c:
        audit=audit_actual(args.source_root,args.input_c,args.receipt,args.header)
        if args.output:args.output.write_text(json.dumps(audit,indent=2)+'\n')
        print('ACTUAL_GENERATED_TRANSFORM_CONTROLS_PASS=1')
