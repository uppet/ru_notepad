#!/usr/bin/env python3
"""Fail-closed experiment activation controls; no compiler/GUI processes."""
import argparse,copy,importlib.util,json,shutil,sys,tempfile,unittest
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
        self.graph[key]=self.parse((self.root/build.SYNTAX).read_text())
        self.graph.sources={key:(self.root/build.SYNTAX).read_text()}
        self.manifest=self.root/build.MANIFEST
    def prepare(self,arm='dense'):return build.prepare_graph(self.root,self.graph,self.manifest,arm)
    def rejected(self,fn):
        with self.assertRaises((ValueError,OSError)):fn()
    def test_both_arms_are_explicit(self):
        a=build.expected_receipt(self.root,self.manifest,'ordinary')[0];b=self.prepare();
        self.assertFalse(a['enabled']);self.assertTrue(b['enabled']);self.assertEqual(a['input_sha256'],b['input_sha256'])
        self.assertEqual(a['manifest'],b['manifest']);self.assertEqual(b['source_patch_count'],1)
        self.assertIn(build.ON,self.graph.sources[self.key]);self.assertIn(build.OFF,(self.root/build.SYNTAX).read_text())
        build.verify_receipt(self.root,self.manifest,'dense',b)
    def test_ordinary_no_source_patch(self):
        r=self.prepare('ordinary');self.assertEqual(r['source_patch_count'],0);self.assertEqual(self.graph.sources[self.key],(self.root/build.SYNTAX).read_text())
    def test_repeat_rejected(self):self.prepare();self.rejected(self.prepare)
    def test_bad_arm(self):self.rejected(lambda:self.prepare('auto'))
    def test_manifest_elsewhere(self):
        p=self.root/'other.json';shutil.copyfile(self.manifest,p);self.rejected(lambda:build.prepare_graph(self.root,self.graph,p,'dense'))
    def test_manifest_drift(self):self.manifest.write_text(self.manifest.read_text()+' ');self.rejected(self.prepare)
    def test_each_input_drift(self):
        for rel in build.EXPECTED:
            with self.subTest(rel=rel):
                p=self.root/rel;old=p.read_bytes();p.write_bytes(old+b'\n');self.rejected(self.prepare);p.write_bytes(old)
    def test_source_already_enabled(self):
        p=self.root/build.SYNTAX;p.write_text(p.read_text().replace(build.OFF,build.ON));self.rejected(self.prepare)
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
        r=self.prepare();p=self.root/build.DRIVER;p.write_text(p.read_text()+'\n');self.rejected(lambda:build.verify_receipt(self.root,self.manifest,'dense',r))
    def test_receipt_arm_swap(self):
        r=self.prepare();self.rejected(lambda:build.verify_receipt(self.root,self.manifest,'ordinary',r))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--ru-root',type=Path,required=True);a,rest=ap.parse_known_args();sys.path.insert(0,str(a.ru_root.resolve()));unittest.main(argv=[sys.argv[0],*rest])
