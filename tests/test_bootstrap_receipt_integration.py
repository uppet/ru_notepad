"""Portable receipt-chain integration; fake compiler/PE bytes are NOT native proof.

Only external Git/PE/tool-execution boundaries are substituted. The production
receipt entry, proof validator, wrapper identities and main oracle all execute.
"""
import ast
import copy
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import build_bootstrap_release as build
import compile_bootstrap_native as native
import verify_bootstrap_application_oracle as oracle
import verify_bootstrap_editor_windows as smoke
import package_bootstrap_preview as package
import verify_bootstrap_recent_policies as recent
from bootstrap_provenance import InvalidProvenance


class ReceiptIntegration(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name).resolve();self.app=self.root/'editor';self.core=self.root/'core'
        self.app.mkdir();self.core.mkdir()
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.entries=('src/main.ru','tests/bootstrap_pipeline/argv_probe.ru','tests/bootstrap_pipeline/dll_abi_probe.ru')
        self.fixture_entries=tuple('tests/'+name+'.ru' for name in recent.CASES)
        for entry in (*self.entries,*self.fixture_entries):
            p=self.app/entry;p.parent.mkdir(parents=True,exist_ok=True)
            p.write_bytes((smoke.ROOT/entry).read_bytes())
        marker=self.core/'marker';marker.write_text('synthetic core snapshot')
        self.compiler=self.root/'stage3.exe';self.compiler.write_text('synthetic compiler')
        verification=self.root/'verification.json';verification.write_text('{}')
        self.tools={n:str(self.root/(n+'.exe')) for n in ('clang','llvm-as','llvm-link','opt','llvm-dis','llc','linker')}
        for name,path in self.tools.items():Path(path).write_text(name)
        main=self.app/self.entries[0];data=main.read_bytes()
        expected={'schema':oracle.SCHEMA,'scope':oracle.SCOPE,'application_base_commit':oracle.APPLICATION_BASE_COMMIT,
                  'compiler_commit':native.CORE_COMMIT,'compiler_tree':native.CORE_TREE,'entry':'src/main.ru',
                  'modules':[{'scope':'app','path':'src/main.ru','sha256':build.sha(main),
                              'git_blob':hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()}],
                  'shapes':[{'result':'intptr','parameters':['指针']}],'callbacks':[]}
        op=self.app/oracle.ORACLE_PATH;op.parent.mkdir();op.write_text(json.dumps(expected))
        # Relocate the actual wrapper bytes to the synthetic app snapshot.
        # Only its module-location boundary changes, never validator behavior.
        original_driver=Path(native.__file__).resolve();driver=self.app/'tools/compile_bootstrap_native.py'
        driver.parent.mkdir();driver.write_bytes(original_driver.read_bytes())
        self.stack.enter_context(patch.object(native,'__file__',str(driver)))
        self.pins={'app_source':{'path':str(self.app),'commit':'a'*40,'tree':'b'*40},
                   'ru_source':{'path':str(self.core),'commit':native.CORE_COMMIT,'tree':native.CORE_TREE}}
        self.hashes={'app_source':{p:build.sha(self.app/p) for p in (*self.entries,*self.fixture_entries,oracle.ORACLE_PATH,'tools/compile_bootstrap_native.py')},
                     'ru_source':{'marker':build.sha(marker)}}
        frozen={str((Path(pin['path'])/name).resolve()):digest for key,pin in self.pins.items() for name,digest in self.hashes[key].items()}
        self.config={};self.receipts={}
        for key,entry in zip(('app_receipt','argv_probe_receipt','dll_probe_receipt'),self.entries):
            directory=self.root/key;directory.mkdir();binary=directory/'intermediate-console.exe';binary.write_text('synthetic binary')
            ir=directory/'application.ll';ir.write_text('synthetic IR')
            metadata=binary.with_name(binary.name+'.metadata.c');metadata.write_text(
                'typedef intptr_t (*RuNativeCall_0)(void*);\nstatic Val boot_m_0_init(void) {\n'
                'if (ru_native_callback_depth) fail();\nboot_m_0_state=1;\n'
                'ru_native_builtins(ru_practical_builtins());\nboot_m_0_state=2; return value;\n}\n')
            frontend=binary.with_name(binary.name+'.frontend.ll');frontend.write_text('synthetic frontend IR')
            source=self.app/entry;linker=build.identity(self.tools['linker']);triple='x86_64-pc-windows-msvc'
            command=[self.tools['clang'],'--target='+triple,str(directory/'p.obj'),'-o',str(directory/'p.exe'),*build.explicit_linker_flags(linker)]
            selected=[self.tools['linker'],'-out:p.exe']
            trace=('clang version 14.0.6\nTarget: '+triple+'\nThread model: posix\nInstalledDir: fixture\n '+
                   ' '.join('"'+s.replace('\\','\\\\').replace('"','\\"')+'"' for s in selected)+'\n')
            selection={'schema':'ru-pinned-linker-selection-v1','command':command,'dry_run_command':command+['-###'],
                       'selected_command':selected,'linker':linker,'cwd':str(directory),'environment_sha256':'0'*64,
                       'dry_run_stderr_utf8':trace,'dry_run_stderr_sha256':hashlib.sha256(trace.encode()).hexdigest(),
                       'scope':'driver dry-run selection; same argv/env/cwd execution and pre/post file identity; not OS process tracing or ABA protection'}
            tools6={n:build.identity(self.tools[n]) for n in ('clang','llvm-as','llvm-link','opt','llvm-dis','llc')}
            proof={'schema':'ru-bootstrap-build-proof-v1','native_protocol':'bootstrap-native-v1','source':str(source.resolve()),
                   'compiler':build.identity(self.compiler),'target_triple':triple,'data_layout':'layout',
                   'source_inventory':[build.identity(source)],'dependencies':[build.identity(source)],
                   'host_inputs':list(tools6.values()),'tool_executables':tools6,'linker':linker,'linker_selection':selection,
                   'toolchain':{'clang':[self.tools['clang']],'tools':{n:self.tools[n] for n in ('llvm-as','llvm-link','opt','llvm-dis','llc')},'link_flags':build.explicit_linker_flags(linker)},
                   'artifacts':{},'standalone_ir_sha256':build.sha(ir),'binary_sha256':build.sha(binary),
                   'metadata_sha256':build.sha(metadata),'source_ir_sha256':build.sha(frontend)}
            for name,p in (('standalone_ir',ir),('binary',binary),('metadata',metadata),('frontend_ir',frontend)):
                proof['artifacts'][name]={'path':str(p.resolve()),'sha256':build.sha(p)}
            proof_path=directory/'compile-proof.json';proof_path.write_text(json.dumps(proof))
            wrapper={'schema':native.SCHEMA,'compiler_commit':native.CORE_COMMIT,'compiler_tree':native.CORE_TREE,
                     'poison_entries':list(native.POISON_ENTRIES),'python_frontend_attempts':[],
                     **{name:build.identity(p) for name,p in (('source',source),('compiler',self.compiler),('driver',driver),('proof',proof_path),('metadata',metadata),('frontend_ir',frontend))}}
            wrapper_path=binary.with_name(binary.name+'.native-wrapper.json');wrapper_path.write_text(json.dumps(wrapper))
            result=oracle.verify_application_oracle(proof,self.app,self.core,self.hashes,binary) if entry=='src/main.ru' else None
            if result:(directory/'application-oracle-validation.json').write_text(json.dumps(result))
            linked={}
            for name in ('application.obj','launcher.obj','application.res'):
                p=directory/name;p.write_text(name);linked[name]=build.identity(p)
            receipt={'schema':'ru-notepad-bootstrap-llvm-build-v1','status':'built-not-runtime-accepted-not-publishable','native_acceptance':False,
                     'entry_source':entry,'bootstrap':{'stage3_sha256':build.sha(self.compiler),'verification_sha256':build.sha(verification)},
                     'source_pins':self.pins,'source_sha256':self.hashes,'tool_paths':self.tools,
                     'tool_sha256':{n:build.sha(Path(p)) for n,p in self.tools.items()},'app_baseline':{'synthetic':True},
                     'toolchain_identity_scopes':{'bootstrap':'existing M4 LLVM14/target/fixedpoint; bootstrap linker identity not recorded or locked','application':'explicit config-hash toolchain/linker'},
                     'target_triple':triple,'data_layout':'layout','final_binary':build.identity(binary),'driver_inputs':{str(driver):build.sha(driver)},
                     'compile_proof_sha256':build.sha(proof_path),'commands':[command],'final_linker_selection':selection,'linker_probe':{},
                     'standalone_ir_sha256':build.sha(ir),'linked_inputs':linked,'bootstrap_verification':build.identity(verification),
                     'native_metadata':build.identity(metadata),'native_wrapper':build.identity(wrapper_path),'frontend_ir_sha256':build.sha(frontend),'application_oracle':result}
            path=directory/'build-receipt.json';self.config[key]=str(path);self.receipts[key]=receipt;path.write_text(json.dumps(receipt))
        # External acceptance boundaries only: no proof/wrapper/oracle substitution.
        for name in ('verify_gui_pe','validate_toolchain','verify_app_baseline','verify_linker_probe'):
            self.stack.enter_context(patch.object(smoke,name))
        def snapshot(root,commit,tree):
            key=next(k for k,p in self.pins.items() if p['path']==str(root))
            return {n:build.sha(root/n) for n in self.hashes[key]}
        self.stack.enter_context(patch.object(smoke,'snapshot',side_effect=snapshot))

    def test_all_three_real_receipt_consumers_execute_strict_chain(self):
        self.assertEqual(smoke.validate_receipts(self.config),self.receipts)

    def test_package_collects_same_bundle_with_real_wrapper_and_oracle(self):
        smoke.validate_receipts(self.config)
        app=self.receipts['app_receipt']
        records=package.collect_native_evidence(self.config,app)
        self.assertEqual(set(records),set(package.NATIVE_EVIDENCE_LIMITS))
        for name,record in records.items():
            self.assertEqual(record,build.identity(record['path']))
        for field in ('compile_proof_sha256','native_metadata','native_wrapper','frontend_ir_sha256','application_oracle'):
            bad=copy.deepcopy(app);bad[field]='wrong'
            with self.subTest(field=field),self.assertRaises(InvalidProvenance):package.collect_native_evidence(self.config,bad)

    def test_twelve_fixture_report_uses_real_six_tools_and_wrapper_chain(self):
        app=self.receipts['app_receipt'];output=self.root/'fixtures';output.mkdir()
        template_dir=Path(self.config['app_receipt']).parent
        template=json.loads((template_dir/'compile-proof.json').read_text())
        wrapper_template=json.loads((template_dir/'intermediate-console.exe.native-wrapper.json').read_text())
        deps={'app_source':app['source_pins']['app_source'],'source_sha256':app['source_sha256']['app_source'],'binaries':{}}
        originals=self.root/'deps';originals.mkdir()
        for name in smoke.DLLS:
            p=originals/name;p.write_text('synthetic '+name);deps['binaries'][name]=build.identity(p)
        report={'schema':recent.SCHEMA,'status':'passed','source_pins':app['source_pins'],
                'stage3_sha256':app['bootstrap']['stage3_sha256'],'results':{},
                'runtime_dependencies':recent.install_runtime_dependencies(output,app,deps)}
        wrappers={}
        for name,count in recent.CASES.items():
            binary=output/(name+'.exe');ir=output/(name+'.ll');proof_path=output/(name+'.json')
            metadata=binary.with_name(binary.name+'.metadata.c');frontend=binary.with_name(binary.name+'.frontend.ll')
            source=self.app/'tests'/(name+'.ru');proof=copy.deepcopy(template)
            proof.update(source=str(source.resolve()),source_inventory=[build.identity(source)],dependencies=[build.identity(source)])
            for key,path,digest in (('binary',binary,'binary_sha256'),('standalone_ir',ir,'standalone_ir_sha256'),
                                    ('metadata',metadata,'metadata_sha256'),('frontend_ir',frontend,'source_ir_sha256')):
                path.write_text('synthetic fixture '+name+' '+key)
                proof['artifacts'][key]={'path':str(path.resolve()),'sha256':build.sha(path)};proof[digest]=build.sha(path)
            proof_path.write_text(json.dumps(proof));wrapper=copy.deepcopy(wrapper_template)
            for key,path in (('source',source),('proof',proof_path),('metadata',metadata),('frontend_ir',frontend)):
                wrapper[key]=build.identity(path)
            wp=binary.with_name(binary.name+'.native-wrapper.json');wp.write_text(json.dumps(wrapper));wrappers[name]=wp
            stdout=output/(name+'.stdout');stdout.write_text('PASS: fixture\n'*count+'TOTAL PASS: '+str(count)+'\n')
            stderr=output/(name+'.stderr');stderr.write_text('')
            report['results'][name]={'executed':True,'timeout':False,'returncode':0,'assertions':count,
                **{key:build.identity(path) for key,path in (('binary',binary),('ir',ir),('proof',proof_path),('stdout',stdout),('stderr',stderr))}}
        with patch.object(recent,'validate_toolchain'): # external executable discovery only
            recent.validate_report(report,app,self.compiler,deps)
            for mutation in ('old-schema','missing-busy','old-policy-count','old-lifecycle-count'):
                stale=copy.deepcopy(report)
                if mutation=='old-schema':stale['schema']='ru-notepad-bootstrap-editor-fixtures-v3'
                elif mutation=='missing-busy':del stale['results']['single_instance_busy_native']
                elif mutation=='old-policy-count':stale['results']['single_instance_policy']['assertions']=39
                else:stale['results']['single_instance_native']['assertions']=15
                with self.subTest(stale=mutation),self.assertRaises(InvalidProvenance):
                    recent.validate_report(stale,app,self.compiler,deps)
            for name,path in wrappers.items():
                original=path.read_bytes();bad=json.loads(original);bad['python_frontend_attempts']=['frontend.parse'];path.write_text(json.dumps(bad))
                with self.subTest(fixture=name),self.assertRaisesRegex(InvalidProvenance,'poison proof'):
                    recent.validate_report(report,app,self.compiler,deps)
                path.write_bytes(original)
            # Rehash outer file records so the actual six-tool validator, not
            # a stale JSON identity, must reject the missing compiler tool.
            row=report['results'][next(iter(recent.CASES))];pp=Path(row['proof']['path']);bad=json.loads(pp.read_text())
            del bad['tool_executables']['llc'];pp.write_text(json.dumps(bad));row['proof']=build.identity(pp)
            wp=wrappers[next(iter(recent.CASES))];w=json.loads(wp.read_text());w['proof']=build.identity(pp);wp.write_text(json.dumps(w))
            with self.assertRaisesRegex(InvalidProvenance,'tool executable inventory'):
                recent.validate_report(report,app,self.compiler,deps)

    def test_retained_fields_each_missing_or_replaced_rejected(self):
        for key in self.receipts:
            for field in ('native_metadata','native_wrapper','frontend_ir_sha256','application_oracle'):
                for mutation in ('missing','changed'):
                    bad=copy.deepcopy(self.receipts[key]);bad.pop(field) if mutation=='missing' else bad.update({field:'wrong'})
                    Path(self.config[key]).write_text(json.dumps(bad))
                    with self.subTest(key=key,field=field,mutation=mutation),self.assertRaises(InvalidProvenance):smoke.validate_receipts(self.config)
                    Path(self.config[key]).write_text(json.dumps(self.receipts[key]))

    def test_real_entry_rejects_missing_proof_path_even_with_valid_bundle(self):
        original=smoke.verify_proof
        def missing(*args,**kwargs):
            kwargs.pop('proof_path',None);return original(*args,**kwargs)
        with patch.object(smoke,'verify_proof',side_effect=missing),self.assertRaisesRegex(InvalidProvenance,'proof path required'):
            smoke.validate_receipts(self.config)

    def test_wrapper_and_oracle_corruption_rejected_by_real_entry(self):
        directory=Path(self.config['app_receipt']).parent
        for name in ('intermediate-console.exe.native-wrapper.json','application-oracle-validation.json'):
            p=directory/name;original=p.read_bytes();p.write_text('{}')
            with self.subTest(name=name),self.assertRaises(InvalidProvenance):smoke.validate_receipts(self.config)
            p.write_bytes(original)

    def test_production_callsite_inventory_requires_explicit_native_inputs(self):
        expected={'build_bootstrap_release.py':2,'verify_bootstrap_recent_policies.py':2,'verify_bootstrap_editor_windows.py':1}
        found={}
        for path in (smoke.ROOT/'tools').glob('*.py'):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='verify_proof':
                    found[path.name]=found.get(path.name,0)+1
                    self.assertTrue({'tools','proof_path'} <= {k.arg for k in node.keywords},(path.name,node.lineno))
        self.assertEqual(found,expected)

    def test_wrapper_oracle_and_downstream_consumer_callsite_matrix(self):
        expected={
            'validate_wrapper_receipt':{'build_bootstrap_release.py':1,'package_bootstrap_preview.py':1},
            'verify_application_oracle':{'build_bootstrap_release.py':2,'package_bootstrap_preview.py':1,'verify_bootstrap_editor_windows.py':1},
            'validate_receipts':{'verify_bootstrap_product_windows.py':4,'package_bootstrap_preview.py':2,
                                 'verify_bootstrap_editor_windows.py':2,'verify_bootstrap_recent_policies.py':2}}
        for target,inventory in expected.items():
            found={}
            for path in (smoke.ROOT/'tools').glob('*.py'):
                if target=='validate_receipts' and path.name in {'package.py','package_manual_preview.py','windows_ci.py'}:
                    continue # independently reviewed C-baseline API, not bootstrap receipt consumer
                for node in ast.walk(ast.parse(path.read_text())):
                    if isinstance(node,ast.Call) and getattr(node.func,'id',getattr(node.func,'attr',None))==target:
                        found[path.name]=found.get(path.name,0)+1
                        self.assertEqual(len(node.args),{'validate_wrapper_receipt':6,'verify_application_oracle':5,'validate_receipts':1}[target])
            self.assertEqual(found,inventory)


if __name__=='__main__':unittest.main()
