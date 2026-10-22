import io
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
import acquire_npp as a


def zipped(entries):
    b = io.BytesIO()
    with zipfile.ZipFile(b, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, content in entries:
            z.writestr(name, content)
    return b.getvalue()


class AcquisitionTests(unittest.TestCase):
    def test_failure_diagnostics_are_closed_numeric_enums(self):
        self.assertEqual(a.failure_diagnostics(ValueError('private-secret-path'), 4), (4,99,0))
        self.assertEqual(a.failure_diagnostics(ValueError('asset_digest_or_size_mismatch'), 1), (1,103,0))
        self.assertEqual(a.failure_diagnostics(a.urllib.error.HTTPError('private-url',403,'private-body',{},None),1), (1,1,403))
        self.assertEqual(a.failure_diagnostics(a.urllib.error.URLError('private-reason'),1), (1,2,0))
        self.assertEqual(a.failure_diagnostics(RuntimeError('private-path'),{'private':1}), (0,99,0))

    def test_marker_metadata_only_fixed_numeric_hash(self):
        data = zipped([('notepad++.exe',b'fake'),('doLocalConf.xml',b'official-like-content'),('other-private-name',b'secret')])
        self.assertEqual(a.marker_metadata(data), [(0,1,21,a.digest(b'official-like-content')),(1,0,0,'0'*64)])

    def test_hash_and_size(self):
        a.verify(b'abc', 3, a.digest(b'abc'))
        for size, sha in ((4, a.digest(b'abc')), (3, '0'*64)):
            with self.assertRaises(ValueError): a.verify(b'abc', size, sha)

    def test_checksums_exact_filename_and_unique(self):
        good = a.digest(b'a') + '  archive.zip\n'
        a.verify_checksums(good.encode(), 'archive.zip', a.digest(b'a'))
        for data in (good+good, good.replace('archive.zip', 'different.zip'), good.replace(a.digest(b'a'), '0'*64)):
            with self.assertRaises(ValueError): a.verify_checksums(data.encode(), 'archive.zip', a.digest(b'a'))

    def test_hosts(self):
        self.assertTrue(a.trusted_url(a.BASE+'x'))
        for url in ('http://github.com/x', 'https://github.com.evil/x', 'https://user@github.com/x', 'https://github.com:444/x'):
            self.assertFalse(a.trusted_url(url))

    def test_mock_download_hash_and_redirect(self):
        class Response(io.BytesIO):
            url = 'https://release-assets.githubusercontent.com/file'
        class Opener:
            def open(self, request, timeout): return Response(b'abc')
        with patch.object(a.urllib.request, 'build_opener', return_value=Opener()):
            self.assertEqual(a.download(a.BASE+'x', 3, a.digest(b'abc')), b'abc')
            with self.assertRaises(ValueError): a.download(a.BASE+'x', 3, '0'*64)
            Response.url = 'https://evil.invalid/file'
            with self.assertRaises(ValueError): a.download(a.BASE+'x', 3, a.digest(b'abc'))
        with self.assertRaises(ValueError):
            a.SafeRedirect().redirect_request(None, None, 302, '', {}, 'http://evil.invalid')

    def test_safe_extract_and_markers(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp)/'new'
            receipt = a.extract(zipped([('notepad++.exe', b'fake-not-executed'), ('themes/test.xml', b'x')]), dest)
            self.assertFalse(receipt['executed'])
            self.assertEqual(receipt['file_count'], 4)
            self.assertEqual((dest/'disableNppAutoUpdate.xml').read_bytes(), b'')
            with self.assertRaises(FileExistsError): a.extract(zipped([('notepad++.exe', b'x')]), dest)
            self.assertEqual((dest/'notepad++.exe').read_bytes(), b'fake-not-executed')

    def test_unsafe_names(self):
        for name in ('../out', '/absolute', 'C:/drive', 'x:ads', 'a\\b', 'a/../b', 'a//b', 'CON', 'a.','a /b'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                dest=Path(temp)/'new'
                with self.assertRaises(ValueError): a.extract(zipped([(name,b'x')]),dest)
                self.assertFalse(dest.exists())

    def test_duplicate_and_file_parent(self):
        for entries in ([('A',b'a'),('a',b'b')], [('a',b'a'),('a/b',b'b')]):
            with self.assertRaises(ValueError):
                with zipfile.ZipFile(io.BytesIO(zipped(entries))) as z: a.safe_members(z)

    def test_symlink_reparse_encryption(self):
        for attr, flag in ((stat.S_IFLNK << 16,0), (0x400,0), (stat.S_IFREG << 16,1)):
            info=zipfile.ZipInfo('x'); info.external_attr=attr; info.flag_bits=flag
            class Fake:
                def infolist(self): return [info]
            with self.assertRaises(ValueError): a.safe_members(Fake())

    def test_expansion_limit(self):
        with patch.object(a, 'MAX_MEMBER', 2):
            with zipfile.ZipFile(io.BytesIO(zipped([('x',b'abc')]))) as z:
                with self.assertRaises(ValueError): a.safe_members(z)

    def test_cleanup_missing_executable(self):
        with tempfile.TemporaryDirectory() as temp:
            dest=Path(temp)/'new'
            with self.assertRaises(ValueError): a.extract(zipped([('x',b'x')]),dest)
            self.assertFalse(dest.exists())

    def test_config_marker_nonempty_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            dest=Path(temp)/'new'
            with self.assertRaises(ValueError): a.extract(zipped([('notepad++.exe',b'x'),('doLocalConf.xml',b'content')]),dest)
            self.assertFalse(dest.exists())

    def test_symlink_parent(self):
        with tempfile.TemporaryDirectory() as temp:
            parent=Path(temp); (parent/'target').mkdir()
            try: (parent/'link').symlink_to(parent/'target',target_is_directory=True)
            except OSError: self.skipTest('host cannot create symlinks')
            with self.assertRaises(ValueError): a.extract(zipped([('notepad++.exe',b'x')]),parent/'link'/'new')

if __name__=='__main__': unittest.main()
