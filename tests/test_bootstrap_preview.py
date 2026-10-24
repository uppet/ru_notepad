"""Portable policy/negative controls; not Windows acceptance evidence."""
import copy
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
        self.root=Path(self.tmp.name)

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
        def verify_fields(proof,**kwargs):
            self.assertEqual(kwargs.pop('tools'),app['tool_paths'])
            return build.verify_proof(proof,**kwargs)
        with patch.object(recent_fixtures,'validate_toolchain'),patch.object(recent_fixtures,'verify_proof',side_effect=verify_fields) as verifier:
            recent_fixtures.validate_report(report,app,compiler)
            self.assertEqual(verifier.call_count,2)
            bad=copy.deepcopy(report);bad['stage3_sha256']='0'*64
            with self.assertRaises(InvalidProvenance):recent_fixtures.validate_report(bad,app,compiler)
            name='recent_files_policy';proof_path=Path(report['results'][name]['proof']['path'])
            for mutate in ('source','compiler','binary'):
                wrong=copy.deepcopy(originals[name])
                if mutate=='source':wrong['source']=str(root/'tests/recent_files_native.ru')
                elif mutate=='compiler':wrong['compiler']=build.identity(host)
                else:wrong['artifacts']['binary']={'path':str(root/'recent_files_native.exe'),'sha256':build.sha(root/'recent_files_native.exe')}
                proof_path.write_text(json.dumps(wrong));bad=copy.deepcopy(report)
                bad['results'][name]['proof']=build.identity(proof_path)
                with self.assertRaises(InvalidProvenance):recent_fixtures.validate_report(bad,app,compiler)
            proof_path.write_text(json.dumps(originals[name]))

    def test_recent_fixtures_require_exact_individual_assertions_and_total(self):
        good=b'PASS: a\nPASS: b\nTOTAL PASS: 2\n'
        recent_fixtures.exact_assertions(good,b'',0,2)
        for stdout,stderr,rc in [(good,b'unexpected',0),(good,b'',1),
                (good.replace(b'PASS: a\n',b''),b'',0),(good+b'TOTAL PASS: 2\n',b'',0),
                (good+b'SKIP: x\n',b'',0)]:
            with self.assertRaises(InvalidProvenance):recent_fixtures.exact_assertions(stdout,stderr,rc,2)

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
