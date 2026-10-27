"""Portable policy/negative controls; not Windows acceptance evidence."""
import copy
from contextlib import nullcontext
import hashlib
import json
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import build_bootstrap_release as build
import verify_bootstrap_product_windows as product
import package_bootstrap_preview as package
import prepare_bootstrap_preview as prepare
import verify_bootstrap_recent_policies as recent_fixtures
from bootstrap_provenance import InvalidProvenance


class PreviewContracts(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()

    def test_preview_package_documents_instance_tabs_acceptance(self):
        self.assertEqual(package.PREVIEW_DOCS,('bootstrap-llvm-preview.md','recent-files.md','single-instance-and-tabs.md'))
        for name in package.PREVIEW_DOCS:
            self.assertTrue((package.ROOT/'docs'/name).is_file())
        source=Path(package.__file__).read_text()
        for text in ('instance_tabs GUI gate','--multi-instance','pending shell files',"'instance_tabs_gui': True"):
            self.assertIn(text,source)
        self.assertIn("validate_result(report.get('instance_tabs'), hashes)",Path(product.__file__).read_text())

    def test_native_package_evidence_exact_inventory_and_fail_closed(self):
        expected={'application.metadata.c','native-wrapper.json','application-native-oracle.json',
                  'application-oracle-validation.json','compile-proof.json'}
        self.assertEqual(set(package.NATIVE_EVIDENCE_LIMITS),expected)
        app_root=self.root/'app';app_root.mkdir();(app_root/'packaging').mkdir()
        binary=self.root/'intermediate-console.exe'
        meta=binary.with_name(binary.name+'.metadata.c');meta.write_text('synthetic metadata')
        wrapper=binary.with_name(binary.name+'.native-wrapper.json');wrapper.write_text('{}')
        (app_root/package.ORACLE_PATH).write_text('{}')
        result={'status':'passed'}
        (self.root/'application-oracle-validation.json').write_text(json.dumps(result))
        proof={'compiler':{'path':str(self.root/'compiler.exe')},'source_ir_sha256':'a'*64}
        proof_path=self.root/'compile-proof.json';proof_path.write_text(json.dumps(proof))
        app={'compile_proof_sha256':build.sha(proof_path),'native_wrapper':build.identity(wrapper),
             'native_metadata':build.identity(meta),'application_oracle':result,'frontend_ir_sha256':'a'*64,
             'source_pins':{'app_source':{'path':str(app_root)},'ru_source':{'path':str(self.root/'core')}},
             'source_sha256':{'app_source':{}}}
        config={'app_receipt':str(self.root/'build-receipt.json')}
        with patch.object(package,'validate_wrapper_receipt',return_value=build.identity(wrapper)), \
             patch.object(package,'verify_application_oracle',return_value=result):
            self.assertEqual(set(package.collect_native_evidence(config,app)),expected)
            for key in ('compile_proof_sha256','native_wrapper','native_metadata','application_oracle','frontend_ir_sha256'):
                bad=copy.deepcopy(app);bad[key]='wrong'
                with self.subTest(key=key),self.assertRaises(InvalidProvenance):package.collect_native_evidence(config,bad)
            with patch.dict(package.NATIVE_EVIDENCE_LIMITS,{'application.metadata.c':1}):
                with self.assertRaises(InvalidProvenance):package.collect_native_evidence(config,app)
            (self.root/'application-oracle-validation.json').write_text('{}')
            with self.assertRaises(InvalidProvenance):package.collect_native_evidence(config,app)

    def test_workflow_job_env_contexts_and_runtime_output_initialization(self):
        workflow=(Path(__file__).resolve().parents[1]/'.github/workflows/bootstrap-preview.yml').read_text()
        def check_job_env(text):
            # This workflow uses a block mapping at fixed job indentation; fail
            # closed if its structure changes instead of silently skipping it.
            blocks=re.findall(r'^    env:\n((?:^      .*\n)+)',text,re.M)
            self.assertEqual(len(blocks),1)
            allowed={'github','needs','strategy','matrix','vars','secrets','inputs'}
            for expression in re.findall(r'\$\{\{(.*?)\}\}',blocks[0]):
                roots=re.findall(r'\b([A-Za-z_][A-Za-z_0-9]*)\s*(?:\.|\[)',expression)
                self.assertTrue(set(roots)<=allowed,expression)
            self.assertNotIn('PREVIEW_OUTPUT:',blocks[0])
        check_job_env(workflow)
        for context in ('runner.temp','steps.pins.outputs.compiler_commit','env.TEMP','job.status'):
            invalid=workflow.replace('    env:\n','    env:\n      INVALID: ${{ '+context+' }}\n',1)
            with self.assertRaises(AssertionError):check_job_env(invalid)
        first_step=workflow.split('    steps:\n',1)[1].split('      - ',2)[1]
        self.assertIn("Join-Path $env:RUNNER_TEMP 'ru-bootstrap-preview'",first_step)
        self.assertIn('"PREVIEW_OUTPUT=$previewOutput" >> $env:GITHUB_ENV',first_step)
        self.assertIn('${{ runner.temp }}/ru-bootstrap-preview/',workflow)

    def test_failed_markdown_still_collects_mru_but_never_passes_product(self):
        import verify_recent_files_windows as recent_gui
        names=['main-gui-smoke','main-gui-file-entry','main-gui-ru-syntax','main-gui-markdown']
        events=[]
        functions=[]
        for name in names:
            def run(*args, name=name):
                events.append(name)
                return {'name':name,'passed':name!='main-gui-markdown','executed':True,
                    'cleanup_killed':False,'exit_code':0,'main_hwnd_seen':True,
                    'close_posted':True,'detached_from_console':True,'fixture_binary_sha256':{}}
            functions.append(run)
        ci=SimpleNamespace(**dict(zip(('run_gui','run_gui_file_entry','run_gui_ru_syntax','run_gui_markdown'),functions)))
        ci.GUI_FILE_CHECKS=();ci.GUI_RU_CHECKS=();ci.GUI_MARKDOWN_CHECKS=()
        ci.validate_gui_ru_timer=Mock();ci.validate_gui_ru_edits=Mock()
        ci.validate_gui_markdown=Mock();ci.portable=SimpleNamespace(RUNTIME_NAMES=())
        report={'gui_results':[]}
        snapshots=[]
        def run_recent(*args):
            events.append('recent-files')
            return {'passed':True}
        with patch.object(recent_gui,'isolated_recent_settings',side_effect=lambda:nullcontext()), \
                patch.object(recent_gui,'run_recent_files',side_effect=run_recent):
            product.collect_product_gui(ci,None,self.root,self.root,self.root,report,
                lambda:snapshots.append(copy.deepcopy(report)))
        self.assertEqual(events,names+['recent-files'])
        self.assertEqual(len(snapshots),5)
        self.assertFalse(snapshots[-1]['gui_results'][-1]['passed'])
        self.assertTrue(snapshots[-1]['recent_files']['passed'])
        # Collection cannot turn the original failed verdict into acceptance.
        with self.assertRaises(InvalidProvenance):product.validate_gui_results(ci,report['gui_results'],{})
        report.update(schema=product.SCHEMA,status='passed',runtime_sha256={},
            all_native_console_tests_bootstrap_compiled=False,full_release_acceptance=False)
        with self.assertRaises(InvalidProvenance):product.validate_product(report,ci)

    def test_diagnostic_runtime_is_bounded_whitelist_not_acceptance(self):
        config={};root=self.root
        for key in ('app_receipt','argv_probe_receipt','dll_probe_receipt','dependencies_receipt','smoke_receipt','recent_fixtures_receipt'):
            path=root/(key+'.json');path.write_text('{}');config[key]=str(path)
        proof=root/'compile-proof.json';proof.write_text('{"proof":"test"}')
        runtime=root/'runtime';runtime.mkdir()
        for name in product.DIAGNOSTIC_FILES:(runtime/name).write_bytes(name.encode())
        (runtime/'private-config.json').write_text('must not be copied')
        hashes={name:build.sha(runtime/name) for name in product.DIAGNOSTIC_FILES}
        app={'source_pins':{'app_source':{'commit':'fixed'}},'source_sha256':{'app_source':{}},
             'final_binary':build.identity(runtime/'ru_notepad.exe'),'compile_proof_sha256':build.sha(proof),
             'bootstrap':{'stage3_sha256':'a'*64}}
        dependencies={'app_source':app['source_pins']['app_source'],'source_sha256':{},
             'binaries':{name:build.identity(runtime/name) for name in product.smoke.DLLS},'tool_paths':{'objdump':'fixed'}}
        report={'schema':product.SCHEMA,'status':'failed','source_pins':app['source_pins'],
             'runtime_directory':str(runtime),'runtime_sha256':hashes,
             'build_receipts':{key:build.identity(Path(config[key])) for key in
                ('app_receipt','argv_probe_receipt','dll_probe_receipt','dependencies_receipt')},
             'smoke_receipt':build.identity(Path(config['smoke_receipt'])),
             'recent_fixtures_receipt':build.identity(Path(config['recent_fixtures_receipt']))}
        receipt=root/'product.json';receipt.write_text(json.dumps(report))
        with patch.object(product.smoke,'validate_receipts',return_value={'app_receipt':app}), \
             patch.object(product,'validate_receipt',return_value=dependencies), \
             patch.object(package.legacy_package,'validate_dependency_sources'), \
             patch.object(package.legacy_package,'inspect_pe',return_value={'imports':['kernel32.dll']}) as pe:
            output=root/'diagnostic'
            marker=product.collect_diagnostic_runtime(config,receipt,output)
            self.assertEqual(marker['status'],'NOT_ACCEPTED');self.assertFalse(marker['user_delivery_authorized'])
            self.assertEqual(marker['product_status'],'failed')
            self.assertEqual({p.name for p in output.iterdir()},product.DIAGNOSTIC_FILES|{'compile-proof.json','NOT_ACCEPTED.json'})
            self.assertEqual(pe.call_count,4)
            self.assertFalse(list(root.rglob('*.zip')))
            with self.assertRaises(InvalidProvenance):product.validate_product(marker,None)
            pe.side_effect=InvalidProvenance('non-whitelisted PE dependency')
            with self.assertRaises(InvalidProvenance):product.collect_diagnostic_runtime(config,receipt,root/'bad-pe')
            self.assertFalse((root/'bad-pe').exists());pe.side_effect=None
            for name in ('ru_notepad.exe','Scintilla.dll'):
                file=runtime/name;original=file.read_bytes();file.write_bytes(b'changed')
                with self.assertRaises(InvalidProvenance):product.collect_diagnostic_runtime(config,receipt,root/'bad-bytes')
                self.assertFalse((root/'bad-bytes').exists());file.write_bytes(original)
            original=(runtime/'ru_notepad.exe').read_bytes()
            calls=[0]
            def changed_after_copy(_):
                calls[0]+=1
                if calls[0]==2:(runtime/'ru_notepad.exe').write_bytes(b'post-copy mutation')
                return {'app_receipt':app}
            with patch.object(product.smoke,'validate_receipts',side_effect=changed_after_copy):
                with self.assertRaises(InvalidProvenance):product.collect_diagnostic_runtime(config,receipt,root/'changed-after-copy')
            self.assertFalse((root/'changed-after-copy').exists())
            (runtime/'ru_notepad.exe').write_bytes(original)
            calls=[0]
            def changed_stage_after_copy(_):
                calls[0]+=1
                if calls[0]==2:
                    stages=list(root.glob('not-accepted-*/ru_notepad.exe'))
                    self.assertEqual(len(stages),1)
                    stages[0].write_bytes(b'changed staged executable')
                return {'app_receipt':app}
            with patch.object(product.smoke,'validate_receipts',side_effect=changed_stage_after_copy):
                with self.assertRaises(InvalidProvenance):product.collect_diagnostic_runtime(config,receipt,root/'changed-stage')
            self.assertFalse((root/'changed-stage').exists())
            original_identity=product.identity
            def oversized_identity(path):
                record=original_identity(path)
                if Path(path)==runtime/'ru_notepad.exe':record['size']=32*1024*1024+1
                return record
            with patch.object(product,'identity',side_effect=oversized_identity):
                with self.assertRaises(InvalidProvenance):product.collect_diagnostic_runtime(config,receipt,root/'oversized')
            self.assertFalse((root/'oversized').exists())
            report['runtime_sha256']['private-config.json']=build.sha(runtime/'private-config.json')
            receipt.write_text(json.dumps(report))
            with self.assertRaises(InvalidProvenance):product.collect_diagnostic_runtime(config,receipt,root/'bad-inventory')
            self.assertFalse((root/'bad-inventory').exists())

    def test_reviewed_delta_requires_exact_before_after_and_every_change(self):
        def git(*args):
            return subprocess.check_output(['git','-C',str(self.root),*args],text=True,stderr=subprocess.DEVNULL).strip()
        git('init'); (self.root/'original.ru').write_text('original')
        git('add','.'); git('-c','user.name=T','-c','user.email=t@t','commit','-m','base')
        pin={'commit':git('rev-parse','HEAD'),'tree':git('rev-parse','HEAD^{tree}')}
        for name in build.ADDITIONS:
            p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('pipeline')
        (self.root/'original.ru').write_text('reviewed update')
        (self.root/'recent.ru').write_text('reviewed new file')
        git('add','.');git('-c','user.name=T','-c','user.email=t@t','commit','-m','feature')
        current=build.snapshot(self.root,git('rev-parse','HEAD'),git('rev-parse','HEAD^{tree}'))
        pin['reviewed_changes']={
            'original.ru':{'before':hashlib.sha256(b'original').hexdigest(),'after':current['original.ru']},
            'recent.ru':{'before':None,'after':current['recent.ru']}}
        result=build.verify_app_baseline(self.root,pin,current)
        self.assertEqual(result['reviewed_changes'],pin['reviewed_changes'])
        # Recorded receipts revalidate using the same exact manifest, not a new diff.
        self.assertEqual(result,build.verify_app_baseline(self.root,result,current))
        for name,field,value in [('original.ru','before','0'*64),('original.ru','after','0'*64),
                                 ('recent.ru','before','0'*64)]:
            bad=copy.deepcopy(pin);bad['reviewed_changes'][name][field]=value
            with self.assertRaises(InvalidProvenance):build.verify_app_baseline(self.root,bad,current)
        bad=copy.deepcopy(pin);del bad['reviewed_changes']['recent.ru']
        with self.assertRaises(InvalidProvenance):build.verify_app_baseline(self.root,bad,current)
        changed=dict(current);del changed['original.ru']
        with self.assertRaises(InvalidProvenance):build.verify_app_baseline(self.root,pin,changed)
        changed=dict(current);changed['recent.ru']='0'*64
        with self.assertRaises(InvalidProvenance):build.verify_app_baseline(self.root,pin,changed)
        bad=copy.deepcopy(pin);bad['reviewed_changes']['../escape']={'before':None,'after':'0'*64}
        with self.assertRaises(InvalidProvenance):build.verify_app_baseline(self.root,bad,current)

    def gui_rows(self):
        hashes={'ru_notepad.exe':'a'*64}
        rows=[{'name':name,'passed':True,'executed':True,'cleanup_killed':False,'exit_code':0,
               'main_hwnd_seen':True,'close_posted':True,'detached_from_console':True,
               'fixture_binary_sha256':hashes,'file_gate':True,'ru_gate':True,'md_gate':True,
               'timer_performance':{},'edit_performance':{},'markdown_performance':{}}
              for name in sorted(product.GUI_NAMES)]
        ci=SimpleNamespace(GUI_FILE_CHECKS=['file_gate'],GUI_RU_CHECKS=['ru_gate'],GUI_MARKDOWN_CHECKS=['md_gate'],
                           validate_gui_ru_timer=Mock(),validate_gui_ru_edits=Mock(),validate_gui_markdown=Mock())
        return ci,rows,hashes

    def test_product_reuses_original_gui_validators_without_changing_budget(self):
        ci,rows,hashes=self.gui_rows();product.validate_gui_results(ci,rows,hashes)
        ci.validate_gui_ru_timer.assert_called_once_with({},require_windows_clock=True)
        ci.validate_gui_ru_edits.assert_called_once_with({})
        ci.validate_gui_markdown.assert_called_once_with({},require_windows_clock=True)
        ci.validate_gui_markdown.side_effect=RuntimeError('original deadline failed')
        with self.assertRaisesRegex(RuntimeError,'original deadline'):product.validate_gui_results(ci,rows,hashes)

    def test_product_cannot_pass_missing_duplicate_failed_or_other_binary_gui(self):
        ci,rows,hashes=self.gui_rows()
        variants=[rows[:-1],rows[:-1]+[rows[0]]]
        for key,value in [('passed',False),('executed',False),('cleanup_killed',True),('exit_code',1),
                          ('close_posted',False),('skips',['missing']),('error','failure')]:
            bad=copy.deepcopy(rows);bad[0][key]=value;variants.append(bad)
        bad=copy.deepcopy(rows)
        next(r for r in bad if r['name']!='main-gui-smoke')['fixture_binary_sha256']={'ru_notepad.exe':'b'*64}
        variants.append(bad)
        for bad in variants:
            with self.assertRaises(InvalidProvenance):product.validate_gui_results(ci,bad,hashes)

    def test_preview_cannot_claim_original_all_native_release(self):
        ci,rows,hashes=self.gui_rows()
        for key in ('all_native_console_tests_bootstrap_compiled','full_release_acceptance'):
            record={'schema':product.SCHEMA,'status':'passed',
                    'all_native_console_tests_bootstrap_compiled':False,'full_release_acceptance':False}
            record[key]=True
            with self.assertRaises(InvalidProvenance):product.validate_product(record,ci)

    def test_zip_verifies_actual_bytes_inventory_and_duplicate_members(self):
        path=self.root/'preview.zip';data=b'exact tested binary'
        files={'ru_notepad.exe':{'size':len(data),'sha256':hashlib.sha256(data).hexdigest()}}
        with zipfile.ZipFile(path,'w') as z:z.writestr('ru_notepad.exe',data)
        package.verify_zip(path,files)
        for name,body in [('other.exe',data),('ru_notepad.exe',b'changed')]:
            with zipfile.ZipFile(path,'w') as z:z.writestr(name,body)
            with self.assertRaises(InvalidProvenance):package.verify_zip(path,files)
        with zipfile.ZipFile(path,'w') as z:
            z.writestr('ru_notepad.exe',data);z.writestr('extra',b'')
        with self.assertRaises(InvalidProvenance):package.verify_zip(path,files)

    def test_package_entry_refuses_changed_receipts_runtime_or_failed_gui_before_zip(self):
        runtime=self.root/'runtime';runtime.mkdir()
        names=('ru_notepad.exe','Scintilla.dll','Lexilla.dll','RuSyntax.dll')
        for name in names:(runtime/name).write_bytes(('tested '+name).encode())
        hashes={name:build.sha(runtime/name) for name in names}
        config={}
        for key in ('app_receipt','argv_probe_receipt','dll_probe_receipt','dependencies_receipt','smoke_receipt','recent_fixtures_receipt'):
            file=self.root/(key+'.json');file.write_text('{}');config[key]=str(file)
        source_pins={'app_source':{'commit':'a'*40},'ru_source':{'commit':'b'*40}}
        report={'source_pins':source_pins, 'runtime_directory':str(runtime),'runtime_sha256':hashes,
                'build_receipts':{key:build.identity(Path(value)) for key,value in config.items() if key!='smoke_receipt'},
                'smoke_receipt':build.identity(Path(config['smoke_receipt'])),
                'recent_fixtures_receipt':build.identity(Path(config['recent_fixtures_receipt']))}
        receipts={'app_receipt':{'source_pins':source_pins,'final_binary':build.identity(runtime/'ru_notepad.exe')}}
        dependency={'binaries':{name:{'sha256':hashes[name]} for name in names[1:]}}
        output=self.root/'preview.zip'
        from contextlib import ExitStack
        with ExitStack() as stack:
            stack.enter_context(patch.object(package.smoke,'validate_receipts',return_value=receipts))
            stack.enter_context(patch.object(package,'validate_receipt',return_value=dependency))
            reader=stack.enter_context(patch.object(package.smoke,'read_json',return_value=report))
            stack.enter_context(patch.object(package.smoke,'load_windows_harness',return_value=object()))
            stack.enter_context(patch.object(recent_fixtures,'validate_report'))
            stack.enter_context(patch.object(recent_fixtures,'compiler_from_receipt',return_value=self.root/'stage3.exe'))
            validator=stack.enter_context(patch.object(package.product,'validate_product'))
            validator.side_effect=RuntimeError('original GUI budget failed')
            with self.assertRaisesRegex(RuntimeError,'original GUI budget'):
                package.package(config,self.root/'product.json',output,self.root/'mingw')
            self.assertFalse(output.exists());validator.side_effect=None
            bad=copy.deepcopy(report);bad['build_receipts']['app_receipt']['sha256']='0'*64;reader.return_value=bad
            with self.assertRaises(InvalidProvenance):
                package.package(config,self.root/'product.json',output,self.root/'mingw')
            self.assertFalse(output.exists());reader.return_value=report
            for name in ('ru_notepad.exe','Scintilla.dll'):
                old=(runtime/name).read_bytes();(runtime/name).write_bytes(b'changed after test')
                with self.assertRaises(InvalidProvenance):
                    package.package(config,self.root/'product.json',output,self.root/'mingw')
                self.assertFalse(output.exists());(runtime/name).write_bytes(old)

    def test_recent_report_rechecks_stage3_fixed_entry_and_proof_artifact_binding(self):
        root=self.root.resolve();(root/'tests').mkdir()
        compiler=root/'stage3.exe';compiler.write_bytes(b'trusted stage3')
        host=root/'host.py';host.write_bytes(b'trusted host')
        app={'source_pins':{'app_source':{'path':str(root)},'ru_source':{'path':str(root)}},
             'bootstrap':{'stage3_sha256':build.sha(compiler)},
             'source_sha256':{'app_source':{},'ru_source':{'host.py':build.sha(host)}},
             'tool_paths':{},'tool_sha256':{},'target_triple':'triple','data_layout':'layout'}
        report={'schema':recent_fixtures.SCHEMA,'status':'passed','source_pins':app['source_pins'],
                'stage3_sha256':build.sha(compiler),'results':{}}
        originals={}
        for name,count in recent_fixtures.CASES.items():
            source=root/'tests'/(name+'.ru');source.write_text(name)
            app['source_sha256']['app_source']['tests/'+name+'.ru']=build.sha(source)
            binary=root/(name+'.exe');binary.write_bytes(name.encode())
            ir=root/(name+'.ll');ir.write_text('IR '+name)
            proof={'schema':'ru-bootstrap-build-proof-v1','native_protocol':'bootstrap-native-v1',
                   'source':str(source),'compiler':build.identity(compiler),'target_triple':'triple','data_layout':'layout',
                   'source_inventory':[build.identity(source)],'dependencies':[build.identity(source)],
                   'host_inputs':[build.identity(host)],
                   'artifacts':{'standalone_ir':{'path':str(ir),'sha256':build.sha(ir)},
                                'binary':{'path':str(binary),'sha256':build.sha(binary)}},
                   'standalone_ir_sha256':build.sha(ir),'binary_sha256':build.sha(binary)}
            proof_path=root/(name+'.json');proof_path.write_text(json.dumps(proof));originals[name]=proof
            out=root/(name+'.stdout');out.write_text('PASS: item\n'*count+'TOTAL PASS: '+str(count)+'\n')
            err=root/(name+'.stderr');err.write_bytes(b'')
            report['results'][name]={'executed':True,'timeout':False,'returncode':0,'assertions':count,
                **{key:build.identity(path) for key,path in [('binary',binary),('ir',ir),('proof',proof_path),('stdout',out),('stderr',err)]}}
        dependency_directory=root/'dependency-source';dependency_directory.mkdir()
        binaries={}
        for dll in recent_fixtures.smoke.DLLS:
            file=dependency_directory/dll;file.write_bytes(('pinned '+dll).encode())
            binaries[dll]=build.identity(file)
        dependencies={'app_source':app['source_pins']['app_source'],
                      'source_sha256':app['source_sha256']['app_source'],'binaries':binaries}
        report['runtime_dependencies']=recent_fixtures.install_runtime_dependencies(root,app,dependencies)
        def verify_fields(proof,**kwargs):
            self.assertEqual(kwargs.pop('tools'),app['tool_paths'])
            return build.verify_proof(proof,**kwargs)
        with patch.object(recent_fixtures,'validate_toolchain'),patch.object(recent_fixtures,'verify_proof',side_effect=verify_fields) as verifier:
            recent_fixtures.validate_report(report,app,compiler,dependencies)
            self.assertEqual(recent_fixtures.CASES, {'recent_files_policy':25, 'recent_files_native':22, 'recent_files_callbacks':10, 'ru_lexical_policy':422, 'markdown_policy':221, 'tab_close_policy':16, 'single_instance_policy':39, 'single_instance_settings_native':11, 'app_tabs_native':53, 'single_instance_native':15})
            self.assertEqual(verifier.call_count,10)
            for schema in ('ru-notepad-bootstrap-editor-fixtures-v1', 'ru-notepad-bootstrap-editor-fixtures-v2'):
                bad=copy.deepcopy(report);bad['schema']=schema
                with self.assertRaises(InvalidProvenance):recent_fixtures.validate_report(bad,app,compiler,dependencies)
            for mutation in ('missing-runtime', 'missing-dll', 'extra-dll', 'changed-dll', 'rehashed-dll', 'relocated-dll', 'wrong-dependency-source'):
                bad=copy.deepcopy(report);dep=copy.deepcopy(dependencies)
                path=root/'Scintilla.dll';data=path.read_bytes()
                if mutation=='missing-runtime':del bad['runtime_dependencies']
                elif mutation=='missing-dll':del bad['runtime_dependencies']['Scintilla.dll']
                elif mutation=='extra-dll':bad['runtime_dependencies']['extra.dll']=build.identity(path)
                elif mutation=='changed-dll':path.write_bytes(data+b'changed')
                elif mutation=='rehashed-dll':
                    path.write_bytes(data+b'changed');bad['runtime_dependencies']['Scintilla.dll']=build.identity(path)
                elif mutation=='relocated-dll':bad['runtime_dependencies']['Scintilla.dll']=binaries['Scintilla.dll']
                else:dep['source_sha256']={}
                try:
                    with self.subTest(mutation=mutation),self.assertRaises(InvalidProvenance):
                        recent_fixtures.validate_report(bad,app,compiler,dep)
                finally:path.write_bytes(data)
            for missing in recent_fixtures.CASES:
                bad=copy.deepcopy(report);del bad['results'][missing]
                with self.assertRaises(InvalidProvenance):recent_fixtures.validate_report(bad,app,compiler,dependencies)
            bad=copy.deepcopy(report);bad['stage3_sha256']='0'*64
            with self.assertRaises(InvalidProvenance):recent_fixtures.validate_report(bad,app,compiler,dependencies)
            for name in recent_fixtures.CASES:
                proof_path=Path(report['results'][name]['proof']['path'])
                for mutate in ('source','compiler','binary'):
                    wrong=copy.deepcopy(originals[name])
                    if mutate=='source':wrong['source']=str(root/'tests/not-the-fixed-entry.ru')
                    elif mutate=='compiler':wrong['compiler']=build.identity(host)
                    else:wrong['artifacts']['binary']={'path':str(host),'sha256':build.sha(host)}
                    proof_path.write_text(json.dumps(wrong));bad=copy.deepcopy(report)
                    bad['results'][name]['proof']=build.identity(proof_path)
                    with self.assertRaises(InvalidProvenance):recent_fixtures.validate_report(bad,app,compiler,dependencies)
                proof_path.write_text(json.dumps(originals[name]))

    def test_cheap_contract_checks_precede_self_compilation_and_check_each_exit(self):
        workflow=(Path(__file__).resolve().parents[1]/'.github/workflows/bootstrap-preview.yml').read_text()
        start=workflow.index('      - name: Fail-closed cheap contract preflight')
        end=workflow.index('      - name: Fresh three-stage',start)
        body=workflow[start:end]
        for command in ("python -m unittest discover -s editor/tests -p 'test_bootstrap*.py' -v",
                        'python editor/tools/test_windows_ci.py -v',
                        'python editor/tools/test_package.py -v',
                        'python editor/tools/test_gui_instance_tabs.py -v',
                        'python editor/tools/test_i18n.py --catalog-only',
                        'python editor/tools/test_i18n_models.py',
                        'python editor/tools/test_single_instance_state.py --ru-root language --output "$env:PREVIEW_OUTPUT/instance-state-controls"'):
            self.assertIn(command+'\n          if ($LASTEXITCODE) { exit $LASTEXITCODE }',body)
        self.assertEqual(body.count('if ($LASTEXITCODE)'),7)

    def test_recent_fixtures_require_exact_individual_assertions_and_total(self):
        good=b'PASS: a\nPASS: b\nTOTAL PASS: 2\n'
        recent_fixtures.exact_assertions(good,b'',0,2)
        for stdout,stderr,rc in [(good,b'unexpected',0),(good,b'',1),
                (good.replace(b'PASS: a\n',b''),b'',0),(good+b'TOTAL PASS: 2\n',b'',0),
                (good+b'SKIP: x\n',b'',0)]:
            with self.assertRaises(InvalidProvenance):recent_fixtures.exact_assertions(stdout,stderr,rc,2)

    def native_preflight_tree(self):
        root=self.root/'language'
        for name in prepare.NATIVE_PREFLIGHT_FILES:
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('# fixture\n')
        help_text='usage: bootstrap.py build ...\n\noptions:\n'+''.join(
            '  '+flag+(' '+argument if argument else '')+'\n'
            for flag,argument in prepare.NATIVE_BUILD_OPTIONS.items())
        return root,help_text

    def test_native_preflight_accepts_exact_options_without_building_source(self):
        root,help_text=self.native_preflight_tree()
        with patch.object(prepare.subprocess,'run',return_value=SimpleNamespace(
                returncode=0,stdout=help_text,stderr='')) as run:
            prepare.native_preflight(root)
        run.assert_called_once_with(
            [sys.executable,str(root/'tools/bootstrap.py'),'build','--help'],
            cwd=root,capture_output=True,text=True,encoding='utf-8',errors='strict',
            timeout=30,check=False)

    def test_native_preflight_rejects_each_missing_file_before_execution(self):
        root,_=self.native_preflight_tree()
        with patch.object(prepare.subprocess,'run') as run:
            for name in prepare.NATIVE_PREFLIGHT_FILES:
                path=root/name;data=path.read_bytes();path.unlink()
                with self.subTest(name=name), self.assertRaisesRegex(InvalidProvenance,'missing input'):
                    prepare.native_preflight(root)
                path.write_bytes(data)
        run.assert_not_called()

    def test_native_preflight_rejects_linked_file_and_ancestor(self):
        root,_=self.native_preflight_tree()
        target=root/'bootstrap/native_emit.ru';original=target.read_bytes();target.unlink()
        replacement=self.root/'real-native.ru';replacement.write_bytes(original)
        target.symlink_to(replacement)
        with patch.object(prepare.subprocess,'run') as run:
            with self.assertRaisesRegex(InvalidProvenance,'linked input'):prepare.native_preflight(root)
            target.unlink();target.write_bytes(original)
            linked=self.root/'linked-language';linked.symlink_to(root,target_is_directory=True)
            with self.assertRaisesRegex(InvalidProvenance,'linked input'):prepare.native_preflight(linked)
        run.assert_not_called()

    def test_native_preflight_requires_complete_option_declarations(self):
        root,help_text=self.native_preflight_tree()
        for flag,argument in prepare.NATIVE_BUILD_OPTIONS.items():
            declaration='  '+flag+(' '+argument if argument else '')
            for invalid in ('', '  '+flag+'-extra', '  '+flag+'=True',
                    'description mentions '+flag, '                          ['+flag+']'):
                text=help_text.replace(declaration+'\n',invalid+'\n')
                with self.subTest(flag=flag,invalid=invalid), patch.object(prepare.subprocess,'run',
                        return_value=SimpleNamespace(returncode=0,stdout=text,stderr='')):
                    with self.assertRaisesRegex(InvalidProvenance,'missing native bootstrap option'):
                        prepare.native_preflight(root)
        for invalid in ('  --allow-native BOOL','  --allow-native True','  --allow-native=false'):
            with patch.object(prepare.subprocess,'run',return_value=SimpleNamespace(returncode=0,
                    stdout=help_text.replace('  --allow-native\n',invalid+'\n'),stderr='')):
                with self.assertRaises(InvalidProvenance):prepare.native_preflight(root)

    def test_native_preflight_rejects_failed_noisy_or_invalid_help(self):
        root,help_text=self.native_preflight_tree()
        for rc,stdout,stderr in ((1,help_text,''),(False,help_text,''),(0,help_text,'warning'),
                                (0,True,''),(0,'x'*65537,'')):
            with self.subTest(rc=rc,stderr=stderr), patch.object(prepare.subprocess,'run',
                    return_value=SimpleNamespace(returncode=rc,stdout=stdout,stderr=stderr)):
                with self.assertRaises(InvalidProvenance):prepare.native_preflight(root)
        with patch.object(prepare.subprocess,'run',side_effect=subprocess.TimeoutExpired('help',30)):
            with self.assertRaises(subprocess.TimeoutExpired):prepare.native_preflight(root)

    def test_prepare_checks_pinned_snapshot_before_native_preflight_and_toolchain(self):
        root,_=self.native_preflight_tree();app=self.root/'app';app.mkdir()
        events=[]
        value={'compiler':{'commit':'a'*40,'tree':'b'*40}}
        def snapshot(path,commit,tree):events.append(('snapshot',path,commit,tree));return {}
        def fail_preflight(path):
            events.append(('preflight',path));raise InvalidProvenance('missing native capability')
        with patch.object(prepare,'ROOT',app), patch.object(prepare,'manifest',return_value=value), \
                patch.dict(prepare.os.environ,{'GITHUB_SHA':'c'*40}), \
                patch.object(prepare,'git',return_value='d'*40), \
                patch.object(prepare,'snapshot',side_effect=snapshot), \
                patch.object(prepare,'native_preflight',side_effect=fail_preflight), \
                patch.object(prepare,'verify_app_baseline') as baseline:
            with self.assertRaisesRegex(InvalidProvenance,'missing native capability'):
                prepare.prepare(root,self.root/'output',self.root/'mingw')
        self.assertEqual(events,[('snapshot',app,'c'*40,'d'*40),
                                 ('snapshot',root,'a'*40,'b'*40),('preflight',root)])
        baseline.assert_not_called()
        self.assertFalse((self.root/'output').exists())

    def test_unfrozen_manifest_never_resolves_dynamic_branch_or_latest_artifact(self):
        file=self.root/'inputs.json'
        value={'schema':'ru-notepad-reviewed-preview-inputs-v1','compiler':{'commit':None,'tree':None},
               'baseline':{'commit':'a'*40,'tree':'b'*40},'reviewed_changes':{}}
        with patch.object(prepare,'MANIFEST',file):
            for commit in (None,'main','wip','latest','a'*39):
                value['compiler']['commit']=commit;file.write_text(json.dumps(value))
                with self.assertRaises(InvalidProvenance):prepare.manifest()
            value['compiler']={'commit':'c'*40,'tree':'d'*40};file.write_text(json.dumps(value))
            self.assertEqual(prepare.manifest(),value)


if __name__=='__main__':unittest.main()
