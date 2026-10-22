#!/usr/bin/env python3
"""Fail-closed experiment activation controls; no compiler/GUI processes."""
import argparse,ast,codecs,copy,importlib.util,json,os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
import markdown_dense_build as build
ROOT=Path(__file__).resolve().parents[1]
class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rulang.frontend import parse
        from rulang.modules import load_module_graph
        cls.parse=staticmethod(parse);cls.load=staticmethod(load_module_graph)
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.root=Path(self.t.name)
        for rel in (*build.EXPECTED,build.DRIVER):
            p=self.root/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/rel,p)
        # A tiny real module graph suffices; only import-resolved syntax AST needs
        # this fixed flag, without requiring the Windows native module graph.
        from rulang.modules import ModuleGraph
        key=str((self.root/build.SYNTAX).resolve());self.key=key;self.graph=ModuleGraph(key)
        self.graph[key]=self.parse((self.root/build.SYNTAX).read_text(encoding='utf-8'))
        self.graph.sources={key:(self.root/build.SYNTAX).read_text(encoding='utf-8')}
        self.manifest=self.root/build.MANIFEST
    def prepare(self,arm='dense'):return build.prepare_graph(self.root,self.graph,self.manifest,arm)
    def rejected(self,fn):
        with self.assertRaises((ValueError,OSError)):fn()
    def test_both_arms_are_explicit(self):
        a=build.expected_receipt(self.root,self.manifest,'ordinary')[0];b=self.prepare();
        self.assertFalse(a['enabled']);self.assertTrue(b['enabled']);self.assertEqual(a['input_sha256'],b['input_sha256'])
        self.assertEqual(a['manifest'],b['manifest']);self.assertEqual(b['source_patch_count'],1)
        self.assertIn(build.ON,self.graph.sources[self.key]);self.assertIn(build.OFF,(self.root/build.SYNTAX).read_text(encoding='utf-8'))
        build.verify_receipt(self.root,self.manifest,'dense',b)
    def test_ordinary_no_source_patch(self):
        r=self.prepare('ordinary');self.assertEqual(r['source_patch_count'],0);self.assertEqual(self.graph.sources[self.key],(self.root/build.SYNTAX).read_text(encoding='utf-8'))
    def test_repeat_rejected(self):self.prepare();self.rejected(self.prepare)
    def test_bad_arm(self):self.rejected(lambda:self.prepare('auto'))
    def test_manifest_elsewhere(self):
        p=self.root/'other.json';shutil.copyfile(self.manifest,p);self.rejected(lambda:build.prepare_graph(self.root,self.graph,p,'dense'))
    def test_manifest_drift(self):self.manifest.write_text(self.manifest.read_text(encoding='utf-8')+' ',encoding='utf-8');self.rejected(self.prepare)
    def test_each_input_drift(self):
        for rel in build.EXPECTED:
            with self.subTest(rel=rel):
                p=self.root/rel;old=p.read_bytes();p.write_bytes(old+b'\n');self.rejected(self.prepare);p.write_bytes(old)
    def test_source_already_enabled(self):
        p=self.root/build.SYNTAX;p.write_text(p.read_text(encoding='utf-8').replace(build.OFF,build.ON),encoding='utf-8');self.rejected(self.prepare)
    def test_graph_text_drift(self):self.graph.sources[self.key]+='\n';self.rejected(self.prepare)
    def test_graph_flag_drift(self):
        for n in self.graph[self.key]:
            if n.kind=='bind' and n.data.get('name')=='_密扫描策略':n.data['expr'].data['entries'][0][1].data['value']=True
        self.rejected(self.prepare)
    def test_missing_graph(self):del self.graph[self.key];self.rejected(self.prepare)
    def test_symlink_input(self):
        p=self.root/'src/markdown_ascii_kernel.ru';data=p.read_bytes();p.unlink();target=self.root/'other.ru';target.write_bytes(data);p.symlink_to(target);self.rejected(self.prepare)
    def test_hardlink_input(self):
        import os
        p=self.root/'src/markdown_ascii_kernel.ru';os.link(p,self.root/'alias.ru');self.rejected(self.prepare)
    def test_receipt_tamper(self):
        r=self.prepare()
        for key in r:
            with self.subTest(key=key):
                x=copy.deepcopy(r);x[key]=None;self.rejected(lambda:build.verify_receipt(self.root,self.manifest,'dense',x))
    def test_receipt_after_driver_change(self):
        r=self.prepare();p=self.root/build.DRIVER;p.write_text(p.read_text(encoding='utf-8')+'\n',encoding='utf-8');self.rejected(lambda:build.verify_receipt(self.root,self.manifest,'dense',r))
    def test_receipt_arm_swap(self):
        r=self.prepare();self.rejected(lambda:build.verify_receipt(self.root,self.manifest,'ordinary',r))
    def check_utf8_io(self,source):
        calls=[n for n in ast.walk(ast.parse(source)) if isinstance(n,ast.Call) and
               isinstance(n.func,ast.Attribute) and n.func.attr in ('read_text','write_text')]
        self.assertTrue(calls)
        for n in calls:
            encoding=[k.value for k in n.keywords if k.arg=='encoding']
            self.assertEqual(len(encoding),1)
            self.assertIsInstance(encoding[0],ast.Constant)
            self.assertEqual(encoding[0].value,'utf-8')
    def test_dense_fixture_utf8_contract(self):
        from test_markdown_dense import INTERPRETER_CODE
        for name in ('check_markdown_dense_integration.py','run_markdown_dense_cost.py',
                     'test_markdown_dense.py','test_markdown_dense_ab.py',
                     'test_markdown_dense_build.py','test_markdown_dense_kernel.py'):
            with self.subTest(name=name):self.check_utf8_io((ROOT/'tools'/name).read_text(encoding='utf-8'))
        self.check_utf8_io(INTERPRETER_CODE)
        # Bind this check to the actual isolated caller, not a lookalike program.
        tree=ast.parse((ROOT/'tools/test_markdown_dense.py').read_text(encoding='utf-8'))
        commands=[n for n in ast.walk(tree) if isinstance(n,ast.List) and
                  any(isinstance(x,ast.Constant) and x.value=='-I' for x in n.elts)]
        self.assertEqual(len(commands),1)
        args=commands[0].elts;index=next(i for i,x in enumerate(args) if isinstance(x,ast.Constant) and x.value=='-c')
        self.assertIsInstance(args[index+1],ast.Name);self.assertEqual(args[index+1].id,'INTERPRETER_CODE')
        legacy=INTERPRETER_CODE.replace('read_text(encoding="utf-8")','read_text()')
        self.assertNotEqual(legacy,INTERPRETER_CODE)
        with self.assertRaises(AssertionError):self.check_utf8_io(legacy)
    def test_isolated_oracle_explicit_utf8(self):
        from test_markdown_dense import INTERPRETER_CODE
        source=self.root/'utf8-source.ru';source.write_text("# 变量\n显 'UTF8_IO_PASS'.\n",encoding='utf-8')
        ru=Path(sys.modules['rulang'].__file__).resolve().parents[1]
        env=dict(os.environ);env['PYTHONUTF8']='1'
        # Preserve a Unicode-capable filesystem, then switch only text locale.
        # Windows already uses wide filesystem APIs. Its ANSI codec may itself
        # be UTF-8, so enforce the missing-encoding contract independently of it.
        if sys.platform=='linux':env['LC_ALL']='C.UTF-8'
        prefix='import locale,sys; locale.setlocale(locale.LC_CTYPE,"C"); assert sys.flags.isolated and sys.flags.ignore_environment and sys.flags.utf8_mode==0; sys.stderr.write("TEXT_ENCODING="+locale.getencoding()+"\\n"); '
        legacy=INTERPRETER_CODE.replace('read_text(encoding="utf-8")','read_text()')
        strict=['-X','warn_default_encoding=1','-W','error::EncodingWarning']
        for name,code,flags in (('locale-implicit',legacy,[]),('implicit',legacy,strict),('explicit',INTERPRETER_CODE,strict)):
            with self.subTest(name=name):
                p=subprocess.run([sys.executable,'-I','-X','utf8=0',*flags,'-c',prefix+code,str(ru),str(source)],
                                 env=env,capture_output=True,timeout=10)
                self.assertTrue(p.stderr.startswith(b'TEXT_ENCODING='))
                codec=codecs.lookup(p.stderr.splitlines()[0].split(b'=',1)[1].decode('ascii')).name
                if name=='locale-implicit':
                    if codec=='utf-8':
                        self.assertEqual(p.returncode,0);self.assertEqual(p.stdout.replace(b'\r\n',b'\n'),b'UTF8_IO_PASS\n')
                    else:
                        self.assertNotEqual(p.returncode,0)
                        if codec in ('ascii','cp1252'):self.assertIn(b'UnicodeDecodeError',p.stderr)
                elif name=='implicit':
                    self.assertNotEqual(p.returncode,0);self.assertIn(b'EncodingWarning',p.stderr)
                else:
                    self.assertEqual(p.returncode,0);self.assertEqual(p.stdout.replace(b'\r\n',b'\n'),b'UTF8_IO_PASS\n')
                    print('UTF8_IO_CONTROL '+p.stderr.splitlines()[0].decode('ascii'))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--ru-root',type=Path,required=True);a,rest=ap.parse_known_args();sys.path.insert(0,str(a.ru_root.resolve()));unittest.main(argv=[sys.argv[0],*rest])
