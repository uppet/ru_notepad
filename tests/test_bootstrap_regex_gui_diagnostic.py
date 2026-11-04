"""Fail-closed saved-runtime diagnostic contracts. NOT Windows execution proof."""
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import urllib.error
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import run_regex_gui_diagnostic as diagnostic


def metadata():
    return {'id': diagnostic.ARTIFACT_ID, 'name': diagnostic.ARTIFACT_NAME,
            'size_in_bytes': diagnostic.ARCHIVE_BYTES, 'expired': False,
            'digest': 'sha256:' + diagnostic.ARCHIVE_SHA256, 'url': diagnostic.API_URL,
            'archive_download_url': diagnostic.API_URL + '/zip',
            'workflow_run': {'id': diagnostic.RUN_ID, 'repository_id': diagnostic.REPOSITORY_ID,
                             'head_repository_id': diagnostic.REPOSITORY_ID,
                             'head_branch': 'wip', 'head_sha': diagnostic.APP_COMMIT}}


def manifest(files=None):
    return {'schema': 'ru-notepad-not-accepted-runtime-v1', 'status': 'NOT_ACCEPTED',
            'user_delivery_authorized': False, 'product_status': 'failed',
            'product_receipt_sha256': diagnostic.PRODUCT_RECEIPT_SHA256,
            'stage3_sha256': diagnostic.STAGE3_SHA256,
            'source_pins': {'app_source': {'commit': diagnostic.APP_COMMIT, 'tree': diagnostic.APP_TREE},
                            'ru_source': {'commit': diagnostic.COMPILER_COMMIT, 'tree': diagnostic.COMPILER_TREE}},
            'files': {name: value for name, value in (files or diagnostic.FILES).items()
                      if name != 'NOT_ACCEPTED.json'}}


def proof():
    return {'schema': 'ru-bootstrap-build-proof-v1', 'native_protocol': 'bootstrap-native-v1',
            'compiler': {'sha256': diagnostic.STAGE3_SHA256}}


def fake_bundle():
    payloads = {name: ('synthetic:' + name).encode() for name in diagnostic.RUNTIME_NAMES}
    payloads['compile-proof.json'] = json.dumps(proof()).encode()
    files = {name: {'size': len(data), 'sha256': diagnostic.sha(data)} for name, data in payloads.items()}
    payloads['NOT_ACCEPTED.json'] = json.dumps(manifest(files)).encode()
    files['NOT_ACCEPTED.json'] = {'size': len(payloads['NOT_ACCEPTED.json']),
                                'sha256': diagnostic.sha(payloads['NOT_ACCEPTED.json'])}
    return payloads, files


def make_zip(payloads):
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in payloads.items():
            archive.writestr(name, data)
    return out.getvalue()


def response(data):
    result = Mock()
    result.__enter__ = Mock(return_value=io.BytesIO(data))
    result.__exit__ = Mock(return_value=False)
    return result


class Pins(unittest.TestCase):
    def test_exact_failed_run_and_compiler_pins(self):
        self.assertEqual(diagnostic.REPOSITORY, 'uppet/ru_notepad')
        self.assertEqual(diagnostic.ARTIFACT_ID, 13329823677)
        self.assertEqual(diagnostic.RUN_ID, 41832860414)
        self.assertEqual(diagnostic.APP_COMMIT, '19ad6042ca13b64564e3982743896637de79a8f2')
        self.assertEqual(diagnostic.COMPILER_COMMIT, 'c3bb177c6a15e90821e5495cc74b0fdfc39b893a')
        self.assertEqual(diagnostic.ARCHIVE_SHA256, '8a3579c1a00e94349fea428f22c45951b4ffa638e06cb3b00a8eb55bb3ad36e4')
        self.assertEqual(diagnostic.ARCHIVE_BYTES, 4835815)
        self.assertEqual(set(diagnostic.FILES), set(diagnostic.RUNTIME_NAMES) | {'compile-proof.json', 'NOT_ACCEPTED.json'})

    def test_metadata_requires_every_pin_not_filename_alone(self):
        self.assertEqual(diagnostic.validate_metadata(metadata()), metadata())
        for key in metadata():
            bad = metadata()
            del bad[key]
            with self.subTest(key=key), self.assertRaises(ValueError):
                diagnostic.validate_metadata(bad)
        for key in metadata()['workflow_run']:
            bad = metadata()
            bad['workflow_run'][key] = 'wrong'
            with self.subTest(key=key), self.assertRaises(ValueError):
                diagnostic.validate_metadata(bad)
        for key in ('id', 'size_in_bytes', 'expired'):
            bad = metadata()
            bad[key] = str(bad[key])
            with self.subTest(key=key), self.assertRaises(ValueError):
                diagnostic.validate_metadata(bad)

    def test_manifest_rejects_acceptance_or_other_source(self):
        diagnostic.validate_manifest(manifest(), proof())
        for key, value in (('status', 'passed'), ('user_delivery_authorized', True),
                           ('product_status', 'passed'), ('product_receipt_sha256', '0' * 64),
                           ('stage3_sha256', '0' * 64), ('files', {}), ('source_pins', {})):
            bad = manifest()
            bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                diagnostic.validate_manifest(bad, proof())
        for source in ('app_source', 'ru_source'):
            for field in ('commit', 'tree'):
                bad = manifest()
                bad['source_pins'][source][field] = '0' * 40
                with self.subTest(source=source, field=field), self.assertRaises(ValueError):
                    diagnostic.validate_manifest(bad, proof())
        bad = proof()
        bad['compiler']['sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            diagnostic.validate_manifest(manifest(), bad)

    def test_archive_hash_is_checked_before_parsing(self):
        with patch.object(diagnostic.zipfile, 'ZipFile') as zip_file:
            with self.assertRaises(ValueError):
                diagnostic.validate_archive(b'not the pinned artifact')
            zip_file.assert_not_called()

    def test_complete_synthetic_archive_contract(self):
        payloads, files = fake_bundle()
        data = make_zip(payloads)
        with patch.multiple(diagnostic, FILES=files, ARCHIVE_BYTES=len(data), ARCHIVE_SHA256=diagnostic.sha(data)):
            self.assertEqual(diagnostic.validate_archive(data), payloads)

    def test_missing_unexpected_duplicate_or_traversing_archive_members_fail(self):
        payloads, files = fake_bundle()
        variants = [dict(payloads, **{'../escape.exe': b'bad'}),
                    {name: data for name, data in payloads.items() if name != 'RuSyntax.dll'},
                    dict(payloads, **{'other.dll': b'bad'})]
        for variant in variants:
            data = make_zip(variant)
            with self.subTest(names=list(variant)), patch.multiple(
                    diagnostic, FILES=files, ARCHIVE_BYTES=len(data), ARCHIVE_SHA256=diagnostic.sha(data)):
                with self.assertRaises(ValueError):
                    diagnostic.validate_archive(data)
        data = make_zip(payloads)
        out = io.BytesIO(data)
        with zipfile.ZipFile(out, 'a') as archive:
            # Duplicate fixed basename still must be rejected before extraction.
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)
                archive.writestr('ru_notepad.exe', payloads['ru_notepad.exe'])
        data = out.getvalue()
        with patch.multiple(diagnostic, FILES=files, ARCHIVE_BYTES=len(data), ARCHIVE_SHA256=diagnostic.sha(data)):
            with self.assertRaises(ValueError):
                diagnostic.validate_archive(data)

    def test_member_size_digest_and_symlink_are_rejected(self):
        payloads, files = fake_bundle()
        for mutation in ('size', 'digest', 'symlink'):
            changed = deepcopy(payloads)
            if mutation == 'size':
                changed['RuSyntax.dll'] += b'x'
            elif mutation == 'digest':
                changed['RuSyntax.dll'] = b'x' * len(changed['RuSyntax.dll'])
            out = io.BytesIO()
            with zipfile.ZipFile(out, 'w') as archive:
                for name, content in changed.items():
                    item = zipfile.ZipInfo(name)
                    if mutation == 'symlink' and name == 'RuSyntax.dll':
                        item.external_attr = 0o120777 << 16
                    archive.writestr(item, content)
            data = out.getvalue()
            with self.subTest(mutation=mutation), patch.multiple(
                    diagnostic, FILES=files, ARCHIVE_BYTES=len(data), ARCHIVE_SHA256=diagnostic.sha(data)):
                with self.assertRaises(ValueError):
                    diagnostic.validate_archive(data)


class Transport(unittest.TestCase):
    def test_response_bound_and_no_token_no_network(self):
        self.assertEqual(diagnostic.bounded(io.BytesIO(b'1234'), 4), b'1234')
        with self.assertRaises(ValueError):
            diagnostic.bounded(io.BytesIO(b'12345'), 4)
        with patch.object(diagnostic.urllib.request, 'build_opener') as opener:
            for token, repo in (('', diagnostic.REPOSITORY), ('token', 'another/repository')):
                with self.assertRaises(ValueError):
                    diagnostic.download(token, repo)
            opener.assert_not_called()

    def test_storage_request_never_receives_token_or_follows_another_redirect(self):
        opener = Mock()
        storage = 'https://example.blob.core.windows.net/artifact?signature=private'
        redirect = urllib.error.HTTPError(diagnostic.API_URL + '/zip', 302, 'Found', {'Location': storage}, None)
        opener.open.side_effect = [response(json.dumps(metadata()).encode()), redirect, response(b'archive')]
        with patch.object(diagnostic.urllib.request, 'build_opener', return_value=opener):
            data, actual = diagnostic.download('secret-test-token', diagnostic.REPOSITORY)
        self.assertEqual(data, b'archive')
        self.assertEqual(actual, metadata())
        calls = opener.open.call_args_list
        self.assertEqual(calls[0].args[0].full_url, diagnostic.API_URL)
        self.assertEqual(calls[1].args[0].full_url, diagnostic.API_URL + '/zip')
        self.assertEqual(calls[0].args[0].get_header('Authorization'), 'Bearer secret-test-token')
        self.assertEqual(calls[2].args[0].full_url, storage)
        self.assertEqual(calls[2].args[0].header_items(), [])
        self.assertIsNone(diagnostic.NoRedirect().redirect_request(None, None, 302, '', {}, storage))

    def test_bad_redirects_fail_before_storage_request(self):
        for location in ('http://example.com/a', 'https://user:pass@example.com/a',
                         'file:///tmp/a', 'https://example.com:444/a', 'https://example.com/a#fragment', ''):
            opener = Mock()
            opener.open.side_effect = [response(json.dumps(metadata()).encode()),
                urllib.error.HTTPError(diagnostic.API_URL + '/zip', 302, 'Found', {'Location': location}, None)]
            with self.subTest(location=location), patch.object(diagnostic.urllib.request, 'build_opener', return_value=opener):
                with self.assertRaises(ValueError):
                    diagnostic.download('token', diagnostic.REPOSITORY)
                self.assertEqual(opener.open.call_count, 2)

    def test_expired_metadata_stops_before_archive(self):
        bad = metadata()
        bad['expired'] = True
        opener = Mock()
        opener.open.return_value = response(json.dumps(bad).encode())
        with patch.object(diagnostic.urllib.request, 'build_opener', return_value=opener):
            with self.assertRaises(ValueError):
                diagnostic.download('token', diagnostic.REPOSITORY)
        self.assertEqual(opener.open.call_count, 1)

    def test_download_errors_do_not_disclose_signed_urls(self):
        opener = Mock()
        opener.open.side_effect = urllib.error.URLError('https://private.example/?secret=value')
        with patch.object(diagnostic.urllib.request, 'build_opener', return_value=opener):
            with self.assertRaisesRegex(RuntimeError, '^Fixed Actions artifact download failed: network error$'):
                diagnostic.download('token', diagnostic.REPOSITORY)


class Runner(unittest.TestCase):
    def test_output_must_be_fresh_unlinked_and_outside_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(ValueError):
                diagnostic.fresh_output(root)
            target = root / 'fresh'
            self.assertEqual(diagnostic.fresh_output(target), target)
            with self.assertRaises(ValueError):
                diagnostic.fresh_output(target)
        with self.assertRaises(ValueError):
            diagnostic.fresh_output(ROOT / 'forbidden-diagnostic-output')

    def test_nonwindows_cannot_create_diagnostic_execution_evidence(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(diagnostic.sys, 'platform', 'linux'):
            output = Path(temporary) / 'output'
            with self.assertRaises(ValueError):
                diagnostic.run(output, 'a' * 40)
            self.assertFalse(output.exists())

    def test_source_requires_exact_clean_commit(self):
        with patch.object(diagnostic.subprocess, 'check_output', side_effect=['a' * 40, 'b' * 40, '']):
            actual = diagnostic.source_identity('a' * 40)
            self.assertEqual(actual['commit'], 'a' * 40)
            self.assertEqual(actual['tree'], 'b' * 40)
        for responses in (['c' * 40, 'b' * 40], ['a' * 40, 'b' * 40, ' M tools/gui_regex_search.py']):
            with patch.object(diagnostic.subprocess, 'check_output', side_effect=responses):
                with self.assertRaises(ValueError):
                    diagnostic.source_identity('a' * 40)
        with self.assertRaises(ValueError):
            diagnostic.source_identity('wip')

    def test_saved_and_harness_source_cannot_be_conflated_or_acceptance_minted(self):
        # Mock only transport/native execution. This is portable orchestration,
        # not evidence that the Windows GUI ran or that any regex case passed.
        import gui_regex_search as regex
        import windows_ci as ci
        payloads, files = fake_bundle()
        data = make_zip(payloads)
        source = {'commit': 'a' * 40, 'tree': 'b' * 40, 'clean': True}
        for valid in (True, False):
            with tempfile.TemporaryDirectory() as temporary, patch.multiple(
                    diagnostic, FILES=files, ARCHIVE_BYTES=len(data), ARCHIVE_SHA256=diagnostic.sha(data)), \
                    patch.object(diagnostic.sys, 'platform', 'win32'), \
                    patch.object(diagnostic, 'source_identity', return_value=source), \
                    patch.object(diagnostic, 'download', return_value=(data, metadata())), \
                    patch.object(ci, 'Windows', return_value=object()), \
                    patch.object(regex, 'run', return_value={'portable_mock': True}) as run, \
                    patch.object(regex, 'validate_result', side_effect=None if valid else ValueError('missing required gate')) as validate, \
                    patch.dict(os.environ, {'GH_TOKEN': 'do-not-inherit', 'GITHUB_REPOSITORY': diagnostic.REPOSITORY}):
                output = Path(temporary) / 'output'
                report = diagnostic.run(output, 'a' * 40)
                self.assertNotIn('GH_TOKEN', os.environ)
                self.assertEqual(report['status'], 'NOT_ACCEPTED')
                self.assertEqual(report['diagnostic_result'], 'passed' if valid else 'failed')
                self.assertEqual(report['application_source']['commit'], diagnostic.APP_COMMIT)
                self.assertEqual(report['harness_source'], source)
                for key in ('rebuilt_application', 'full_release_acceptance', 'product_acceptance',
                            'packaging_acceptance', 'user_delivery_authorized'):
                    self.assertIs(report[key], False)
                run.assert_called_once()
                validate.assert_called_once()
                self.assertEqual(json.loads((output / 'NOT_ACCEPTED-regex-gui-diagnostic.json').read_text()), report)
                self.assertFalse((output / 'product-preview.json').exists())
                self.assertFalse((output / 'dist').exists())

    def test_runtime_tamper_prevents_pass(self):
        payloads, files = fake_bundle()
        with tempfile.TemporaryDirectory() as temporary, patch.object(diagnostic, 'FILES', files):
            runtime = Path(temporary)
            for name in diagnostic.RUNTIME_NAMES:
                (runtime / name).write_bytes(payloads[name])
            self.assertEqual(set(diagnostic.verify_runtime(runtime)), set(diagnostic.RUNTIME_NAMES))
            (runtime / 'RuSyntax.dll').write_bytes(b'changed')
            with self.assertRaises(ValueError):
                diagnostic.verify_runtime(runtime)

    def test_workflow_is_narrow_pinned_bounded_diagnostic_only(self):
        workflow = (ROOT / '.github/workflows/diagnose-regex-gui.yml').read_text()
        for text in ('workflow_dispatch:', 'branches: [wip]', 'timeout-minutes: 30',
                     'contents: read', 'actions: read', 'persist-credentials: false',
                     'ref: ${{ github.sha }}', "if: always()", 'NOT-ACCEPTED-regex-gui-diagnostic-',
                     "'tools/gui_regex_search.py'", "'tests/test_bootstrap_regex_gui_diagnostic.py'",
                     'python -I -B editor/tools/run_regex_gui_diagnostic.py'):
            self.assertIn(text, workflow)
        for line in workflow.splitlines():
            if 'uses:' in line:
                self.assertRegex(line, r'uses: actions/[a-z-]+@[a-f0-9]{40}$')
        self.assertNotIn('continue-on-error', workflow)
        self.assertNotIn('workflow_run:', workflow)
        self.assertNotIn('package_bootstrap', workflow)
        self.assertNotIn('bootstrap.py', workflow)
        self.assertNotIn('/runtime/', workflow)
        self.assertNotIn('write\n', workflow)


if __name__ == '__main__':
    unittest.main()
