import ast
import copy
import hashlib
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
import zipfile
import run_stage3_markdown_windows as d


class DriverTests(unittest.TestCase):
    def metadata(self):
        return ({'id':d.RUN,'head_sha':d.CORE,'run_attempt':1,'status':'completed','conclusion':'success','repository':{'full_name':d.REPO}},
                {'id':d.ARTIFACT,'expired':False,'size_in_bytes':d.ZIP_SIZE,'digest':'sha256:'+d.ZIP_SHA,
                 'workflow_run':{'id':d.RUN,'head_sha':d.CORE},'archive_download_url':d.API+f'/actions/artifacts/{d.ARTIFACT}/zip'})

    def test_exact_metadata_and_negative_identity_controls(self):
        run,artifact=self.metadata();self.assertEqual(d.check_metadata(run,artifact)['sha256'],d.ZIP_SHA)
        for location,key,value in [('run','id',1),('run','head_sha','0'*40),('run','run_attempt',2),('run','conclusion','failure'),
                                   ('artifact','id',1),('artifact','expired',True),('artifact','size_in_bytes',1),('artifact','digest','sha256:'+'0'*64),
                                   ('artifact','archive_download_url','https://example.org/secret')]:
            a,b=copy.deepcopy(run),copy.deepcopy(artifact);(a if location=='run' else b)[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):d.check_metadata(a,b)
        for name in ('id','head_sha'):
            b=copy.deepcopy(artifact);b['workflow_run'][name]='wrong'
            with self.assertRaises(ValueError):d.check_metadata(run,b)

    def test_signed_destination_requires_exact_hostname_boundary(self):
        self.assertEqual(d.blob_destination('https://fixed.blob.core.windows.net/path?sig=private'),'https://fixed.blob.core.windows.net/path?sig=private')
        for value in ('http://fixed.blob.core.windows.net/x','https://fixed.blob.core.windows.net.evil.invalid/x',
                      'https://evilblob.core.windows.net/x','https://user:secret@fixed.blob.core.windows.net/x',
                      'https://fixed.blob.core.windows.net:444/x','https://github.com/x','file:///tmp/x'):
            with self.subTest(value=value),self.assertRaises(ValueError):d.blob_destination(value)
        self.assertIsNone(d.NoRedirect().redirect_request(None,None,None,None,None,None))

    def zip_fixture(self,directory,extra=None):
        path=Path(directory)/'test.zip'
        with zipfile.ZipFile(path,'w') as out:
            for name in ('stage3.exe','report.json','verification.json'):out.writestr(name,b'fixture')
            if extra:extra(out)
        return path

    def extract(self,archive,destination):
        with patch.object(d,'ZIP_SIZE',archive.stat().st_size),patch.object(d,'ZIP_SHA',d.sha(archive)):
            return d.extract_fixed(archive,destination)

    def test_zip_full_digest_required_before_any_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive=self.zip_fixture(tmp);target=Path(tmp)/'out'
            with self.assertRaises(ValueError):d.extract_fixed(archive,target)
            self.assertFalse(target.exists())
            self.extract(archive,target);self.assertEqual((target/'stage3.exe').read_bytes(),b'fixture')

    def test_unsafe_duplicate_and_linked_archive_members_rejected(self):
        variants=[('traversal','../escape',False),('absolute','/absolute',False),
                  ('drive','C:/drive',False),('backslash','dir\\escape',False),
                  ('case-collision','STAGE3.EXE',False),('symlink','link',True),
                  ('nul','bad\x00hidden',False)]
        # ZipInfo normalizes Windows separators on both write and read. Set raw
        # fields after construction so these fixtures really contain unsafe names.
        for variant,name,is_link in variants:
            for separator in ('/', '\\'):
                with self.subTest(variant=variant,zip_separator=separator), tempfile.TemporaryDirectory() as tmp:
                    def extra(z):
                        info=zipfile.ZipInfo('placeholder')
                        info.filename=name;info.orig_filename=name
                        if is_link:
                            info.create_system=3;info.external_attr=(stat.S_IFLNK|0o777)<<16
                        z.writestr(info,b'target' if is_link else b'x')
                    archive=self.zip_fixture(tmp,extra)
                    # Exercise Python's actual Windows normalization on Linux too.
                    with patch.object(zipfile.os,'sep',separator),patch.object(zipfile.os,'altsep','/' if separator=='\\' else None):
                        with zipfile.ZipFile(archive) as z:
                            actual=z.infolist()[-1]
                            self.assertEqual(actual.orig_filename,name)
                            if variant=='backslash':
                                self.assertEqual(actual.filename,'dir/escape' if separator=='\\' else name)
                            if is_link:self.assertEqual(stat.S_IFMT(actual.external_attr>>16),stat.S_IFLNK)
                        with self.assertRaises(ValueError):self.extract(archive,Path(tmp)/'out')
                    self.assertFalse((Path(tmp).parent/'escape').exists())

    def test_nested_stage3_is_not_a_fallback_for_missing_exact_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive=Path(tmp)/'nested.zip'
            with zipfile.ZipFile(archive,'w') as z:
                for name in ('stage3.exe','report.json','verification.json'):z.writestr('other/'+name,b'fixture')
            with self.assertRaises(ValueError):self.extract(archive,Path(tmp)/'out')

    def test_source_inventory_and_dependencies_are_exact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);entry=root/'policy.ru';policy=root/'markdown_policy.ru';core=root/'core'
            stdlib=core/'rulang/stdlib';stdlib.mkdir(parents=True);(stdlib/'base.ru').write_text('fixture')
            paths=[str((root/n).resolve()) for n in d.profile.SOURCE_NAMES]+[str((stdlib/'base.ru').resolve())]
            frozen=dict.fromkeys(paths,'fixture-hash')
            proof={'source_inventory':[{'path':p} for p in paths],
                   'dependencies':[{'path':str(p.resolve())} for p in (entry,policy)]}
            d.verify_generated_sources(proof,root,entry,core,frozen)
            for key in ('source_inventory','dependencies'):
                for mutate in (lambda rows:rows.pop(),lambda rows:rows.append(dict(rows[0])),lambda rows:rows[0].update(path='foreign.ru')):
                    candidate=copy.deepcopy(proof);mutate(candidate[key])
                    with self.assertRaises(ValueError):d.verify_generated_sources(candidate,root,entry,core,frozen)

            (stdlib/'untracked.ru').write_text('untracked')
            with self.assertRaises(ValueError):d.verify_generated_sources(proof,root,entry,core,frozen)

    def test_compilation_and_measurement_environment_removes_credentials(self):
        environment={'PATH':'tools','INCLUDE':'headers','LIB':'libs','GITHUB_TOKEN':'secret','GH_TOKEN':'secret',
                     'ACTIONS_RUNTIME_TOKEN':'secret','AZURE_CLIENT_SECRET':'secret','MY_PASSWORD':'secret','AWS_ACCESS_KEY_ID':'secret',
                     'SSH_AUTH_SOCK':'socket','GIT_ASKPASS':'helper'}
        self.assertEqual(d.clean_environment(environment),{'PATH':'tools','INCLUDE':'headers','LIB':'libs'})

    def test_http_failure_preserves_only_safe_stage_and_status(self):
        error=urllib.error.HTTPError('https://api.github.com/?secret=hidden',403,'private',{},None)
        with patch.object(d.urllib.request,'build_opener') as opener:
            opener.return_value.open.side_effect=error
            with self.assertRaises(d.ArtifactHTTPError) as raised:d.json_api('/fixed','do-not-log-token')
        self.assertEqual((raised.exception.stage,raised.exception.status),('metadata',403))
        self.assertNotIn('hidden',str(raised.exception));self.assertNotIn('token',str(raised.exception))

    def test_download_does_not_forward_authorization_to_signed_blob(self):
        payload=b'fixed-artifact';run,artifact=self.metadata()
        class Response(io.BytesIO):
            def __enter__(self):return self
            def __exit__(self,*args):self.close()
        calls=[]
        class Opener:
            def open(self,request,timeout):
                calls.append(request)
                if len(calls)==1:raise urllib.error.HTTPError(request.full_url,302,'redirect',{'Location':'https://fixed.blob.core.windows.net/a?sig=not-logged'},None)
                return Response(payload)
        with tempfile.TemporaryDirectory() as tmp,patch.dict(d.os.environ,{'GITHUB_TOKEN':'secret'}),patch.object(d,'json_api',side_effect=[run,artifact]),patch.object(d,'check_metadata',return_value={'fixed':True}),patch.object(d.urllib.request,'build_opener',return_value=Opener()),patch.object(d,'ZIP_SIZE',len(payload)),patch.object(d,'ZIP_SHA',hashlib.sha256(payload).hexdigest()):
            self.assertEqual(d.download_fixed(Path(tmp)/'artifact.zip'),{'fixed':True})
        self.assertEqual(calls[0].get_header('Authorization'),'Bearer secret');self.assertIsNone(calls[1].get_header('Authorization'))

    def test_driver_text_io_is_explicit_utf8_under_isolated_python(self):
        tree=ast.parse(Path(d.__file__).read_text(encoding='utf-8'))
        reads=[];writes=[]
        for node in ast.walk(tree):
            if not isinstance(node,ast.Call) or not isinstance(node.func,ast.Attribute):continue
            name=node.func.attr
            if name in ('read_text','write_text'):
                encoding=next((kw.value for kw in node.keywords if kw.arg=='encoding'),None)
                self.assertIsInstance(encoding,ast.Constant)
                self.assertEqual(encoding.value,'utf-8')
                (reads if name=='read_text' else writes).append(node)
            if name=='run' and any(kw.arg=='text' and isinstance(kw.value,ast.Constant) and kw.value.value is True for kw in node.keywords):
                self.assertTrue(any(kw.arg=='encoding' and isinstance(kw.value,ast.Constant) and kw.value.value=='utf-8' for kw in node.keywords))
        self.assertEqual(len(reads),4);self.assertEqual(len(writes),5)
        payload=json.dumps({'source':'如言 函数 丁'},ensure_ascii=False).encode('utf-8')
        with self.assertRaises(UnicodeDecodeError):payload.decode('cp1252')
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)
            for name in ('verification.json','report.json','proof.json','stdout.log'):
                (directory/name).write_bytes(payload)
            scope={'directory':directory,'proof_path':directory/'proof.json','stdout':directory/'stdout.log'}
            # Execute the actual four production read expressions, not a parallel reader.
            for expression in reads:
                value=eval(compile(ast.Expression(expression),'<production-read>','eval'),scope)
                self.assertEqual(json.loads(value),{'source':'如言 函数 丁'})
            d.checkpoint(directory,'核验')
            self.assertEqual(json.loads((directory/'driver-progress.json').read_bytes())['phase'],'核验')

    def test_workflow_has_only_fixed_diagnostic_scope(self):
        local=Path(__file__).parent/'stage3-markdown-diagnostic.yml'
        workflow=local if local.is_file() else Path(__file__).resolve().parents[2]/'.github/workflows/stage3-markdown-diagnostic.yml'
        text=workflow.read_text(encoding='utf-8')
        self.assertIn('diagnostic/notepad-instance-modal-20261027',text)
        self.assertIn(d.APP,text);self.assertIn(d.CORE,text)
        self.assertIn('NOT-ACCEPTED-stage3-markdown',text)
        self.assertNotIn('bootstrap.py verify',text)
        self.assertNotIn('secrets.',text)
        source=Path(d.__file__).read_text(encoding='utf-8')
        self.assertLess(source.index('build.verify_proof('),source.index('report=profile.measure('))
        self.assertIn('provenance.validate(',source)
        self.assertIn('cycle==verification[\'bootstrap\']',source)

if __name__=='__main__':unittest.main()
