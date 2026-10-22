import ast, hashlib, json, shutil, tempfile, unittest
from pathlib import Path
import build_baseline as b
import feasibility as f
import acquire_npp as n
from test_full_receipt import FullReceiptFixture, ROOT


class BuildInventory(unittest.TestCase):
    def fresh(self):
        x=FullReceiptFixture();self.addCleanup(x.close)
        cache=x.root/'build/native-helper';cache.mkdir(parents=True)
        inputs=dict(x.helper['build_inputs']);inputs.update(output_name=b.NONRUNTIME_NAMES[0],compile_sources=['native/ru_wrong_abi.c'])
        (cache/b.NONRUNTIME_NAMES[0]).write_bytes(b'negative control never executed')
        negative=dict(schema=1,name=b.NONRUNTIME_NAMES[0],build_inputs=inputs,build_key=x.p.package.native_build_key(inputs),
                      dll_sha256=b.sha(cache/b.NONRUNTIME_NAMES[0]),
                      compiler_command=[inputs['compiler_path'],*inputs['compiler_flags'],*inputs['compile_sources'],'-o',str(cache/'RuSyntaxWrongAbi.pending.dll'),*('-l'+v for v in inputs['link_libraries'])])
        (cache/b.NONRUNTIME_NAMES[1]).write_text(json.dumps(negative))
        for name in ('RuSyntax.dll','RuSyntax.native-build.json'):
            shutil.copyfile(x.binary/name,cache/name)
        # Execute only the pinned pure copy function, never the build CLI/binary.
        code=(ROOT/'tools/build.py').read_bytes()
        self.assertEqual(hashlib.sha1(b'blob '+str(len(code)).encode()+b'\0'+code).hexdigest(),'6bdd9c88c8887255be6a64ca637fdaf3b39df9cf')
        node=next(v for v in ast.parse(code).body if isinstance(v,ast.FunctionDef) and v.name=='copy_native_helpers')
        namespace={'Path':Path,'shutil':shutil,'NATIVE_COMPILE_SOURCES':x.p.package.NATIVE_COMPILE_SOURCES}
        exec(compile(ast.Module(body=[node],type_ignores=[]),'<fixed-copy-helper>','exec'),namespace)
        namespace['copy_native_helpers'](x.root/'build',x.binary)
        (x.binary/'comparison-build.json').write_bytes(b'private build provenance')
        x.verify()
        return x
    def receipt(self,x):
        npp=x.home/'npp';npp.mkdir()
        for name in ('notepad++.exe','doLocalConf.xml','disableNppAutoUpdate.xml'):(npp/name).write_bytes(name.encode())
        files={p.name:b.sha(p) for p in npp.iterdir()}
        r=dict(baseline_commit=b.BASELINE,compiler_commit=b.COMPILER,compiler_tree=b.COMPILER_TREE,
               runtime={'ru':{name:b.sha(x.binary/name) for name in x.p.base.RUNTIME_NAMES},'npp':files},
               npp_all_files_sha256=files,npp_archive_sha256=n.PINS['npp.8.9.8.1.portable.x64.zip'][1],
               nonruntime_build_sha256=b.nonruntime_build(x.root,x.binary,x.p))
        for filename,key in [('ru_notepad.build.json','build_receipt_sha256'),('comparison-build.json','build_provenance_sha256'),('RuSyntax.native-build.json','native_receipt_sha256')]:r[key]=b.sha(x.binary/filename)
        return r,npp
    def test_fixed_copy_has_nine_build_entries_but_four_runtime(self):
        x=self.fresh();r,npp=self.receipt(x)
        self.assertEqual(len(list(x.binary.iterdir())),9)
        f.verify_receipt(r,x.binary,npp)
        stage=x.home/'runtime';f.copy_runtime(x.binary,stage,r['runtime']['ru'])
        self.assertEqual(set(p.name for p in stage.iterdir()),set(x.p.base.RUNTIME_NAMES))
        self.assertFalse(any('WrongAbi' in p.name for p in stage.iterdir()))
        shutil.copyfile(x.binary/b.NONRUNTIME_NAMES[0],stage/b.NONRUNTIME_NAMES[0])
        with self.assertRaises(ValueError):f.closed_manifest(stage,r['runtime']['ru'])
    def test_missing_changed_or_tenth_build_entry_rejected(self):
        for action in ('missing','changed','extra'):
            with self.subTest(action=action):
                x=self.fresh();r,npp=self.receipt(x);p=x.binary/b.NONRUNTIME_NAMES[0]
                if action=='missing':p.unlink()
                elif action=='changed':p.write_bytes(b'changed')
                else:(x.binary/'unexpected.dll').write_bytes(b'extra')
                with self.assertRaises(ValueError):f.verify_receipt(r,x.binary,npp)
    def test_wrong_copy_origin_or_recipe_rejected(self):
        for action in ('origin','recipe','link'):
            with self.subTest(action=action):
                x=self.fresh();cache=x.root/'build/native-helper'
                if action=='origin':(cache/b.NONRUNTIME_NAMES[0]).write_bytes(b'changed')
                elif action=='recipe':
                    p=cache/b.NONRUNTIME_NAMES[1];v=json.loads(p.read_text());v['build_inputs']['compile_sources']=['private/other.c'];p.write_text(json.dumps(v));shutil.copyfile(p,x.binary/p.name)
                else:
                    p=x.binary/b.NONRUNTIME_NAMES[0];p.unlink()
                    try:p.symlink_to(cache/p.name)
                    except OSError:self.skipTest('host lacks symlink privilege')
                with self.assertRaises(ValueError):b.nonruntime_build(x.root,x.binary,x.p)
