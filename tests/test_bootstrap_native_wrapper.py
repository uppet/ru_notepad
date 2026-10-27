"""Negative controls for native-only wrapper and independent metadata validator.

Synthetic metadata below tests validation only, never claims a native build.
"""
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import compile_bootstrap_native as native
import verify_bootstrap_application_oracle as oracle
from bootstrap_provenance import InvalidProvenance


def native_api(compiler,source,output,toolchain,*,emit_llvm=None,keep_frontend=False,
               interpreter_host=False,allow_native=False,proof=None,source_roots=(),linker=None):pass


def metadata(callback=True):
    text='typedef intptr_t (*RuNativeCall_0)(void *);\n'
    if callback:
        text+=''.join(f'static intptr_t ru_native_callback_0_{i}(void * a0) {{\n}}\n' for i in range(1024))
        text+='static RuNativeCall_0 const ru_native_callbacks_0[1024] = {\n};\n'
    text+='static Val boot_m_0_init(void) {\nif (ru_native_callback_depth) fail();\nboot_m_0_state=1;\nru_native_builtins(ru_practical_builtins());\nboot_m_0_state=2; return value;\n}\n'
    return text


class NativeWrapperTests(unittest.TestCase):
    def test_exact_reviewed_api_and_changed_signature_rejected(self):
        native.verify_api(native_api)
        with self.assertRaises(InvalidProvenance):native.verify_api(lambda compiler,source:None)

    def targets(self):
        return tuple((label,SimpleNamespace(**{label.rsplit('.',1)[1]:lambda:None}),label.rsplit('.',1)[1])
                     for label in native.POISON_ENTRIES)

    def test_all_seven_poisoned_even_if_caller_catches_failure(self):
        for index,label in enumerate(native.POISON_ENTRIES):
            targets=self.targets()
            with self.subTest(label=label),self.assertRaises(InvalidProvenance):
                with native.poison_frontends(targets):
                    _,owner,name=targets[index]
                    with self.assertRaisesRegex(RuntimeError,'Python application frontend forbidden'):
                        getattr(owner,name)()
        with self.assertRaises(InvalidProvenance):
            with native.poison_frontends(self.targets()[:-1]):pass

    def test_poison_restores_and_covers_native_emit_alias(self):
        targets=self.targets();owner=targets[3][1];original=owner.emit_c;owner.source=original
        with self.assertRaises(InvalidProvenance):
            with native.poison_frontends(targets):
                with self.assertRaises(RuntimeError):owner.source()
        self.assertIs(owner.emit_c,original);self.assertIs(owner.source,original)
        with native.poison_frontends(targets) as attempts:self.assertEqual(attempts,[])

    def test_retained_metadata_and_frontend_ir_exact_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp).resolve()/'app.exe';proof={'artifacts':{}}
            for name,suffix,digest in [('metadata','.metadata.c','metadata_sha256'),('frontend_ir','.frontend.ll','source_ir_sha256')]:
                path=output.with_name(output.name+suffix);path.write_text(name)
                proof['artifacts'][name]={'path':str(path.resolve()),'sha256':native.sha(path)};proof[digest]=native.sha(path)
            native.validate_retained(proof,output)
            for name in ('metadata','frontend_ir'):
                wrong=copy.deepcopy(proof);del wrong['artifacts'][name]
                with self.assertRaises(InvalidProvenance):native.validate_retained(wrong,output)
                wrong=copy.deepcopy(proof);wrong['artifacts'][name]['sha256']='0'*64
                with self.assertRaises(InvalidProvenance):native.validate_retained(wrong,output)
                # Same existing file via an unresolved parent alias is not the
                # canonical producer identity. This test exercises a .. alias;
                # Windows short-path aliases likewise require canonicalization.
                original=Path(proof['artifacts'][name]['path'])
                alias=original.parent/original.parent.name/'..'/original.name
                (original.parent/original.parent.name).mkdir(exist_ok=True)
                self.assertEqual(alias.resolve(),original)
                wrong=copy.deepcopy(proof);wrong['artifacts'][name]['path']=str(alias)
                with self.assertRaises(InvalidProvenance):native.validate_retained(wrong,output)

    def test_wrapper_receipt_requires_exact_poison_and_all_retained_identities(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();binary=root/'app.exe'
            paths={key:root/name for key,name in {'source':'main.ru','compiler':'stage3.exe','proof':'proof.json',
                   'metadata':'app.exe.metadata.c','frontend_ir':'app.exe.frontend.ll'}.items()}
            for path in paths.values():path.write_text('synthetic bytes')
            paths['driver']=Path(native.__file__).resolve()
            proof={'artifacts':{},'metadata_sha256':native.sha(paths['metadata']),'source_ir_sha256':native.sha(paths['frontend_ir'])}
            for key in ('metadata','frontend_ir'):
                proof['artifacts'][key]={'path':str(paths[key].resolve()),'sha256':native.sha(paths[key])}
            receipt={'schema':native.SCHEMA,'compiler_commit':native.CORE_COMMIT,'compiler_tree':native.CORE_TREE,
                     'poison_entries':list(native.POISON_ENTRIES),'python_frontend_attempts':[],
                     **{key:native.identity(path) for key,path in paths.items()}}
            target=root/'app.exe.native-wrapper.json';frozen={str(paths['driver']):native.sha(paths['driver'])}
            def verify(record):
                target.write_text(json.dumps(record))
                return native.validate_wrapper_receipt(proof,paths['source'],paths['compiler'],binary,paths['proof'],frozen)
            self.assertEqual(verify(receipt),native.identity(target))
            for key in receipt:
                bad=copy.deepcopy(receipt);del bad[key]
                with self.subTest(missing=key),self.assertRaises(InvalidProvenance):verify(bad)
            for key in ('source','compiler','driver','proof','metadata','frontend_ir'):
                bad=copy.deepcopy(receipt);bad[key]['sha256']='0'*64
                with self.subTest(changed=key),self.assertRaises(InvalidProvenance):verify(bad)
            for key,value in (('poison_entries',list(native.POISON_ENTRIES[:-1])),('python_frontend_attempts',['frontend.parse']),('extra',1)):
                bad=copy.deepcopy(receipt);bad[key]=value
                with self.subTest(changed=key),self.assertRaises(InvalidProvenance):verify(bad)
            frozen.clear()
            with self.assertRaises(InvalidProvenance):verify(receipt)

    def test_complete_metadata_sets_and_each_malformed_inventory_rejected(self):
        good=metadata();expected={('intptr_t',('void*',))}
        self.assertEqual(oracle.metadata_sets(good,1),(expected,expected))
        mutations=[good.replace('boot_m_0','boot_m_1'),good+good.splitlines()[0]+'\n',good.replace('RuNativeCall_0)(','RuNativeCall_1)('),
            good.replace('boot_m_0_state=1;','boot_m_0_state=1;\nboot_m_0_state=1;'),
            good.replace('if (ru_native_callback_depth) fail();\n',''),
            good.replace('if (ru_native_callback_depth) fail();\nboot_m_0_state=1;','boot_m_0_state=1;\nif (ru_native_callback_depth) fail();'),
            good.replace('ru_native_callback_0_1023(','ru_native_callback_0_1022('),
            good.replace('ru_native_callbacks_0[1024]','ru_native_callbacks_1[1024]'),
            good.replace('ru_native_builtins(ru_practical_builtins())','ru_practical_builtins()')]
        for bad in mutations:
            with self.subTest(mutation=mutations.index(bad)),self.assertRaises(InvalidProvenance):oracle.metadata_sets(bad,1)
        with self.assertRaises(InvalidProvenance):oracle.metadata_sets(good,2)

    def test_independent_oracle_binds_complete_dependencies_and_frozen_bytes(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();app=root/'app';core=root/'core';app.mkdir();core.mkdir()
            source=app/'src/main.ru';source.parent.mkdir();source.write_text('source fixture')
            oracle_path=app/oracle.ORACLE_PATH;oracle_path.parent.mkdir()
            data=source.read_bytes()
            row={'scope':'app','path':'src/main.ru','sha256':native.sha(source),
                 'git_blob':hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()}
            expected={'schema':oracle.SCHEMA,'scope':oracle.SCOPE,'application_base_commit':oracle.APPLICATION_BASE_COMMIT,
                      'compiler_commit':native.CORE_COMMIT,'compiler_tree':native.CORE_TREE,'entry':'src/main.ru',
                      'modules':[row],'shapes':[{'result':'intptr','parameters':['指针']}],
                      'callbacks':[{'result':'intptr','parameters':['指针']}]}
            oracle_path.write_text(json.dumps(expected))
            frozen={'app_source':{'src/main.ru':native.sha(source),oracle.ORACLE_PATH:native.sha(oracle_path)},'ru_source':{}}
            binary=root/'fixture.exe';meta=root/'fixture.exe.metadata.c';frontend=root/'fixture.exe.frontend.ll'
            meta.write_text(metadata());frontend.write_text('synthetic IR')
            proof={'source':str(source.resolve()),'dependencies':[native.identity(source)],
                   'metadata_sha256':native.sha(meta),'source_ir_sha256':native.sha(frontend),
                   'artifacts':{'metadata':{'path':str(meta.resolve()),'sha256':native.sha(meta)},
                                'frontend_ir':{'path':str(frontend.resolve()),'sha256':native.sha(frontend)}}}
            result=oracle.verify_application_oracle(proof,app,core,frozen,binary)
            self.assertEqual((result['modules'],result['shapes'],result['callbacks']),(1,1,1))
            for mutation in ('missing','extra','duplicate','hash','wrong-entry','metadata'):
                bad=copy.deepcopy(proof)
                if mutation=='missing':bad['dependencies']=[]
                elif mutation in ('extra','duplicate'):bad['dependencies'].append(dict(bad['dependencies'][0]))
                elif mutation=='hash':bad['dependencies'][0]['sha256']='0'*64
                elif mutation=='wrong-entry':bad['source']=str(app/'tests/probe.ru')
                else:bad['metadata_sha256']='0'*64
                with self.subTest(mutation=mutation),self.assertRaises(InvalidProvenance):
                    oracle.verify_application_oracle(bad,app,core,frozen,binary)
            original=source.read_bytes();source.write_bytes(original+b'changed')
            with self.assertRaises(InvalidProvenance):oracle.verify_application_oracle(proof,app,core,frozen,binary)
            source.write_bytes(original)
            wrong_anchor=copy.deepcopy(expected);wrong_anchor['application_base_commit']='b'*40
            oracle_path.write_text(json.dumps(wrong_anchor));frozen['app_source'][oracle.ORACLE_PATH]=native.sha(oracle_path)
            with self.assertRaises(InvalidProvenance):oracle.verify_application_oracle(proof,app,core,frozen,binary)
            altered=copy.deepcopy(expected);altered['shapes'][0]['result']='u32';oracle_path.write_text(json.dumps(altered))
            with self.assertRaises(InvalidProvenance):oracle.verify_application_oracle(proof,app,core,frozen,binary)
            frozen['app_source'][oracle.ORACLE_PATH]=native.sha(oracle_path)
            with self.assertRaises(InvalidProvenance):oracle.verify_application_oracle(proof,app,core,frozen,binary)

    def test_oracle_duplicate_keys_shapes_and_unknown_primitives_rejected(self):
        with self.assertRaises(InvalidProvenance):oracle.unique_json('{"schema":1,"schema":2}')
        row={'result':'intptr','parameters':['指针']}
        self.assertEqual(oracle.shapes([row]),{('intptr_t',('void*',))})
        for rows in ([row,row],[{'result':'bad','parameters':[]}],[{'result':'无值','parameters':['无值']}]):
            with self.assertRaises(InvalidProvenance):oracle.shapes(rows)


if __name__=='__main__':unittest.main()
