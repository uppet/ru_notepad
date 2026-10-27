"""Portable negative controls only; no Windows or accepted-runtime claim."""
import copy
import hashlib
import io
import json
import re
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile
import diagnose_instance_modal_windows as diagnostic


class DiagnosticTests(unittest.TestCase):
    def metadata(self):
        artifact={'id':diagnostic.ARTIFACT_ID,'name':diagnostic.ARTIFACT_NAME,'expired':False,
                  'size_in_bytes':diagnostic.ZIP_SIZE,'digest':'sha256:'+diagnostic.ZIP_SHA256,
                  'workflow_run':{'id':diagnostic.RUN_ID,'head_sha':diagnostic.HEAD,'repository_id':1421718936,'head_repository_id':1421718936}}
        run={'id':diagnostic.RUN_ID,'head_sha':diagnostic.HEAD,'status':'completed','conclusion':'failure',
             'repository':{'full_name':diagnostic.REPOSITORY}}
        return artifact,run

    def test_exact_metadata_and_every_binding_rejects_replacement(self):
        artifact,run=self.metadata();record=diagnostic.validate_metadata(artifact,run)
        self.assertEqual(record['zip_sha256'],'787408015a04193713f686030b88e79413754c87318e17f227017c65fd44dcf0')
        self.assertEqual(record['artifact_id'],12728275345)
        for key in artifact:
            bad=copy.deepcopy(artifact);bad[key]=None
            with self.subTest(artifact=key),self.assertRaises(ValueError):diagnostic.validate_metadata(bad,run)
        for key in artifact['workflow_run']:
            bad=copy.deepcopy(artifact);bad['workflow_run'][key]='wrong'
            with self.subTest(origin=key),self.assertRaises(ValueError):diagnostic.validate_metadata(bad,run)
        for key in run:
            bad=copy.deepcopy(run);bad[key]=None
            with self.subTest(run=key),self.assertRaises(ValueError):diagnostic.validate_metadata(artifact,bad)
        bad=copy.deepcopy(artifact);bad['expired']=True
        with self.assertRaises(ValueError):diagnostic.validate_metadata(bad,run)
        self.assertNotIn('archive_download_url',record)

    def test_zip_exact_inventory_rejects_escape_duplicate_link_and_oversize(self):
        entries=[]
        for name in sorted(diagnostic.MEMBERS):
            entry=zipfile.ZipInfo(name);entry.file_size=1;entry.compress_size=1;entry.external_attr=(stat.S_IFREG|0o600)<<16;entries.append(entry)
        def verify(items):diagnostic.validate_zip_inventory(SimpleNamespace(infolist=lambda:items))
        verify(entries)
        for mutation in ('missing','extra','duplicate','escape','absolute','backslash','symlink','directory','encrypted','oversize'):
            bad=copy.deepcopy(entries)
            if mutation=='missing':bad.pop()
            elif mutation=='extra':bad.append(zipfile.ZipInfo('extra.exe'))
            elif mutation=='duplicate':bad[-1]=copy.deepcopy(bad[0])
            elif mutation=='escape':bad[0].filename='../'+bad[0].filename
            elif mutation=='absolute':bad[0].filename='/'+bad[0].filename
            elif mutation=='backslash':bad[0].filename='x\\'+bad[0].filename
            elif mutation=='symlink':bad[0].external_attr=(stat.S_IFLNK|0o777)<<16
            elif mutation=='directory':bad[0].external_attr=(stat.S_IFDIR|0o777)<<16
            elif mutation=='encrypted':bad[0].flag_bits=1
            else:bad[0].file_size=9*1024*1024
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):verify(bad)

    def test_wrong_archive_fails_before_any_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();archive=root/'wrong.zip';archive.write_bytes(b'not the fixed artifact');destination=root/'runtime'
            with self.assertRaises(ValueError):diagnostic.extract_runtime(archive,destination)
            self.assertFalse(destination.exists())

    def test_not_accepted_marker_and_real_file_identities_are_mandatory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();files={}
            for name in diagnostic.FILES:
                data=('synthetic '+name).encode();(root/name).write_bytes(data);files[name]=(hashlib.sha256(data).hexdigest(),len(data))
            marker={'schema':'ru-notepad-not-accepted-runtime-v1','status':'NOT_ACCEPTED','user_delivery_authorized':False,
                    'product_status':'failed','product_receipt_sha256':diagnostic.PRODUCT_SHA256,
                    'source_pins':{'app_source':{'commit':diagnostic.HEAD,'tree':diagnostic.TREE}},
                    'files':{n:{'sha256':h,'size':s} for n,(h,s) in files.items()}}
            path=root/'NOT_ACCEPTED.json';path.write_text(json.dumps(marker))
            with patch.object(diagnostic,'FILES',files): # synthetic bytes only, no native evidence
                self.assertEqual(set(diagnostic.validate_runtime(root)),set(diagnostic.RUNTIME))
                for key in ('schema','status','user_delivery_authorized','product_status','product_receipt_sha256','source_pins','files'):
                    bad=copy.deepcopy(marker);bad[key]='wrong';path.write_text(json.dumps(bad))
                    with self.subTest(field=key),self.assertRaises((ValueError,AttributeError)):diagnostic.validate_runtime(root)
                path.write_text(json.dumps(marker));exe=root/'ru_notepad.exe';exe.write_bytes(b'changed')
                with self.assertRaises(ValueError):diagnostic.validate_runtime(root)

    def test_application_environment_excludes_downloader_and_runner_credentials(self):
        original={'PATH':'normal','TEMP':'tmp','GH_TOKEN':'private','GITHUB_TOKEN':'private2',
                  'ACTIONS_RUNTIME_TOKEN':'private3','CUSTOM_SECRET':'private4',
                  'RU_NOTEPAD_INSTANCE_TEST_KEY':'synthetic','PYTHONUTF8':'1'}
        self.assertEqual(diagnostic.child_environment(original),{'PATH':'normal','TEMP':'tmp',
                         'RU_NOTEPAD_INSTANCE_TEST_KEY':'synthetic','PYTHONUTF8':'1'})
        self.assertEqual(original['GH_TOKEN'],'private')

    def test_diagnostic_result_never_becomes_acceptance_and_failure_still_records(self):
        for failure in (False,True):
            with tempfile.TemporaryDirectory() as tmp:
                output=Path(tmp).resolve()/'diagnostic'
                with patch.object(diagnostic.sys,'argv',['diagnostic','--output',str(output)]), \
                     patch.object(diagnostic.sys,'platform','win32'), \
                     patch.object(diagnostic,'acquire',return_value=(output/'runtime',{},{})), \
                     patch.object(diagnostic,'diagnose',side_effect=RuntimeError('private signed URL must not be emitted') if failure else None,return_value=[]), \
                     patch.object(diagnostic,'validate_runtime'),patch('builtins.print'):
                    code=diagnostic.main()
                record=json.loads((output/'evidence/diagnostic.json').read_text())
                self.assertEqual(code,1 if failure else 0)
                self.assertEqual(record['status'],'NOT_ACCEPTED')
                self.assertIs(record['accepted'],False);self.assertIs(record['user_delivery_authorized'],False)
                self.assertIs(record['compiled'],False);self.assertIs(record['packaged'],False)
                self.assertIs(record['full_feature_ci_required'],True)
                self.assertNotIn('private',json.dumps(record));self.assertNotIn('signed URL',json.dumps(record))

    def test_diagnostic_branch_cannot_trigger_expensive_feature_lanes(self):
        workflows=Path(__file__).resolve().parents[1]/'.github/workflows'
        windows=(workflows/'windows.yml').read_text();bootstrap=(workflows/'bootstrap-preview.yml').read_text()
        def verify(c_native,boot):
            push=c_native.split('  push:\n',1)[1].split('  pull_request:',1)[0]
            ignored=re.findall(r'^    branches-ignore: \[(.*?)\]$',push,re.M)
            self.assertEqual(ignored,['diagnostic/notepad-instance-modal-20261027'])
            self.assertNotIn('branches:',push)
            matches=re.findall(r'^    branches: \[(.*?)\]$',boot,re.M)
            self.assertEqual(len(matches),1)
            branches=[x.strip() for x in matches[0].split(',')]
            self.assertIn('wip',branches)
            self.assertIn('feature/notepad-024-responsive-preview-20261026',branches)
            self.assertTrue(all(x=='wip' or x.startswith('feature/') for x in branches))
            self.assertNotIn('diagnostic/notepad-instance-modal-20261027',branches)
        verify(windows,bootstrap)
        for bad in (windows.replace('branches-ignore: [diagnostic/notepad-instance-modal-20261027]',
                                    'branches-ignore: [diagnostic/notepad-instance-modal-20261027, wip]'),
                    windows.replace('branches-ignore: [diagnostic/notepad-instance-modal-20261027]',
                                    'branches-ignore: [diagnostic/*]')):
            with self.assertRaises(AssertionError):verify(bad,bootstrap)
        with self.assertRaises(AssertionError):verify(windows,bootstrap.replace(', wip]',', wip, diagnostic/notepad-instance-modal-20261027]'))

    def test_workflow_only_fixed_diagnostic_branch_read_permissions_no_build_or_delivery(self):
        source=(Path(__file__).resolve().parents[1]/'.github/workflows/instance-modal-diagnostic.yml').read_text()
        self.assertIn('branches: [diagnostic/notepad-instance-modal-20261027]',source)
        self.assertIn("if: github.ref == 'refs/heads/diagnostic/notepad-instance-modal-20261027'",source)
        self.assertIn('contents: read\n  actions: read',source)
        self.assertIn('timeout-minutes: 10',source);self.assertIn('cancel-in-progress: false',source)
        self.assertIn('persist-credentials: false',source);self.assertIn('if: always()',source)
        self.assertIn('/evidence/',source)
        for forbidden in ('secrets.', 'contents: write','actions: write','gh release','build_bootstrap_release','package_bootstrap_preview','latest successful'):
            self.assertNotIn(forbidden,source)
        self.assertEqual(diagnostic.RUN_ID,40484690558)
        script=Path(diagnostic.__file__).read_text()
        self.assertIn("'status':'NOT_ACCEPTED','accepted':False",script)
        self.assertIn("'full_feature_ci_required':True",script)
        self.assertIn('child_environment(os.environ)',script)
        self.assertNotIn('timeout=30,observations',script)


if __name__=='__main__':unittest.main()
