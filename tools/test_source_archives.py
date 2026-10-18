#!/usr/bin/env python3
"""Execute the offline helper against official bytes and hostile fixtures.

Use --archives DIR for a read-only fixture directory containing the two official
ZIPs. The default is this checkout's third_party/source_archives. Nothing is
downloaded, extracted, compiled, or published. All writable fixtures are temporary.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from dataclasses import replace
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import struct
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
import warnings
import zipfile

sys.path.insert(0, str(Path(__file__).absolute().parent))
import prepare_source_archives as helper


FIXTURES = Path(__file__).absolute().parents[1] / 'third_party' / 'source_archives'


def synthetic(entries=None, *, compression=zipfile.ZIP_STORED):
    stream = io.BytesIO()
    entries = [('fixture/file.txt', b'hello offline')] if entries is None else entries
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)
        with zipfile.ZipFile(stream, 'w', compression=compression) as archive:
            for name, data in entries:
                archive.writestr(name, data)
    data = stream.getvalue()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        members = archive.infolist()
        expanded = sum(member.file_size for member in members)
    spec = helper.ArchiveSpec('fixture', 'fixture.zip', len(data), hashlib.sha256(data).hexdigest(),
                              len(entries), expanded, 'fixture')
    return data, spec


def rebound(data, spec):
    return replace(spec, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


class ArchiveTest(unittest.TestCase):
    def verify(self, data, spec):
        observation = helper._observation()
        helper._verify_bytes(data, spec, observation)
        self.assertTrue(observation['verified'])
        return observation

    def reject(self, code, data, spec):
        with self.assertRaises(helper.Rejected) as caught:
            self.verify(data, spec)
        self.assertEqual(code, caught.exception.code)

    def test_fixed_official_contract(self):
        self.assertEqual([(s.id, s.bytes, s.members, s.expanded_bytes) for s in helper.ARCHIVES], [
            ('scintilla567', 1904249, 271, 5906269), ('lexilla554', 1598324, 1003, 5035224)])
        self.assertEqual(helper.ARCHIVES[0].sha256, '2309181e59e7da4659f890dbc128db7451ccd094748770e7be674b830494587c')
        self.assertEqual(helper.ARCHIVES[1].sha256, '5e0a21356e4e2f19d6a38ecd1c8172d5a2b7b4542940568b023386080db90fe0')

    def test_valid_synthetic_stored_and_deflated(self):
        for compression in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
            with self.subTest(compression=compression):
                self.verify(*synthetic(compression=compression))

    def test_bad_size_before_hash_or_zip(self):
        data, spec = synthetic()
        with mock.patch.object(helper, '_verify_zip', side_effect=AssertionError('ZIP must not run')):
            self.reject('size_mismatch', data[:-1], spec)

    def test_bad_hash_before_zip(self):
        data, spec = synthetic()
        with mock.patch.object(helper, '_verify_zip', side_effect=AssertionError('ZIP must not run')):
            self.reject('hash_mismatch', b'X' + data[1:], spec)

    def test_non_zip_even_with_matching_hash(self):
        data, spec = synthetic()
        data = b'<html>PRIVATE ERROR PAGE</html>'
        self.reject('zip_invalid', data, rebound(data, spec))

    def test_truncated_zip_matching_hash(self):
        data, spec = synthetic()
        data = data[:-12]
        self.reject('zip_invalid', data, rebound(data, spec))

    def test_bad_crc_matching_hash(self):
        data, spec = synthetic()
        data = data.replace(b'hello offline', b'jello offline')
        self.reject('zip_payload_invalid', data, rebound(data, spec))

    def test_empty_member_bad_crc(self):
        data, spec = synthetic([('fixture/empty', b'')])
        data = bytearray(data)
        central = data.index(b'PK\x01\x02')
        struct.pack_into('<I', data, 14, 1)
        struct.pack_into('<I', data, central + 16, 1)
        data = bytes(data)
        self.reject('zip_payload_invalid', data, rebound(data, spec))

    def test_count_limit(self):
        data, spec = synthetic()
        self.reject('zip_member_count', data, replace(spec, members=0))

    def test_expanded_total_too_large(self):
        data, spec = synthetic()
        self.reject('zip_expanded_size', data, replace(spec, expanded_bytes=spec.expanded_bytes - 1))

    def test_expanded_total_too_small(self):
        data, spec = synthetic()
        self.reject('zip_expanded_size', data, replace(spec, expanded_bytes=spec.expanded_bytes + 1))

    def test_member_expansion_limit(self):
        data, spec = synthetic([('fixture/bomb', b'a' * (helper.MAX_MEMBER_BYTES + 1))],
                               compression=zipfile.ZIP_DEFLATED)
        self.reject('zip_member_size', data, spec)

    def test_absolute_traversal_and_windows_paths(self):
        names = ['/file', '../file', 'fixture/../file', 'fixture/./file', 'fixture//file',
                 'C:/file', 'fixture/C:/file', 'fixture\\file', 'fixture/CON.txt',
                 'fixture/LPT1', 'fixture/com¹.txt', 'fixture/file.', 'fixture/file ',
                 'fixture/file:stream', 'fixture/line\nfeed', 'other/file',
                 'fixture/file?x', 'fixture/file|x', 'fixture/directory//', 'fixture/con .txt']
        for name in names:
            with self.subTest(name=name):
                data, spec = synthetic([(name, b'x')])
                self.reject('zip_member_path', data, spec)

    def test_embedded_nul_filename(self):
        data, spec = synthetic([('fixture/fileXtxt', b'x')])
        data = data.replace(b'fileXtxt', b'file\x00txt')
        self.reject('zip_member_path', data, rebound(data, spec))

    def test_duplicate_and_case_alias(self):
        for second in ('fixture/file', 'fixture/FILE'):
            with self.subTest(second=second):
                data, spec = synthetic([('fixture/file', b'a'), (second, b'b')])
                self.reject('zip_member_duplicate', data, spec)

    def test_unicode_normalization_alias(self):
        data, spec = synthetic([('fixture/caf\u00e9', b'a'), ('fixture/cafe\u0301', b'b')])
        self.reject('zip_member_duplicate', data, spec)

    def test_file_directory_collision(self):
        data, spec = synthetic([('fixture/file', b'a'), ('fixture/file/', b'')])
        self.reject('zip_member_duplicate', data, spec)

    def test_file_parent_collision(self):
        data, spec = synthetic([('fixture/file', b'a'), ('fixture/file/child', b'b')])
        self.reject('zip_member_path', data, spec)

    def test_symbolic_member(self):
        member = zipfile.ZipInfo('fixture/link')
        member.create_system = 3
        member.external_attr = (stat.S_IFLNK | 0o777) << 16
        self.reject('zip_member_type', *synthetic([(member, b'target')]))

    def test_special_member(self):
        member = zipfile.ZipInfo('fixture/fifo')
        member.create_system = 3
        member.external_attr = (stat.S_IFIFO | 0o600) << 16
        self.reject('zip_member_type', *synthetic([(member, b'')]))

    def test_reparse_member(self):
        member = zipfile.ZipInfo('fixture/reparse')
        member.external_attr = (stat.S_IFREG | 0o600) << 16 | 0x400
        self.reject('zip_member_type', *synthetic([(member, b'x')]))

    def test_nonempty_directory(self):
        self.reject('zip_member_size', *synthetic([('fixture/directory/', b'x')]))

    def test_unsupported_compression(self):
        data, spec = synthetic()
        data = bytearray(data)
        central = data.index(b'PK\x01\x02')
        struct.pack_into('<H', data, 8, 99)
        struct.pack_into('<H', data, central + 10, 99)
        data = bytes(data)
        self.reject('zip_compression', data, rebound(data, spec))

    def test_encrypted_member(self):
        data, spec = synthetic()
        data = bytearray(data)
        central = data.index(b'PK\x01\x02')
        struct.pack_into('<H', data, 6, 1)
        struct.pack_into('<H', data, central + 8, 1)
        data = bytes(data)
        self.reject('zip_encrypted', data, rebound(data, spec))

    def test_compressed_size_larger_than_archive(self):
        data, spec = synthetic()
        data = bytearray(data)
        central = data.index(b'PK\x01\x02')
        struct.pack_into('<I', data, central + 20, len(data) + 1)
        data = bytes(data)
        self.reject('zip_member_size', data, rebound(data, spec))

    def test_windows_reparse_attribute_rejected_portably(self):
        info = SimpleNamespace(st_mode=stat.S_IFREG, st_file_attributes=0x400, st_nlink=1)
        with self.assertRaises(helper.Rejected) as caught:
            helper._regular(info)
        self.assertEqual(caught.exception.code, 'link_rejected')


class PrepareTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.originals = {}
        for spec in helper.ARCHIVES:
            path = FIXTURES / spec.filename
            # Missing official bytes is a real failure, never a synthetic pass.
            data = path.read_bytes()
            observation = helper._observation()
            helper._verify_bytes(data, spec, observation)
            cls.originals[spec.id] = data

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='offline-source-tests-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / 'repo'
        self.source = self.root / 'third_party' / 'source_archives'
        self.source.mkdir(parents=True)
        self.target = self.root / 'vendor' / 'downloads'
        for spec in helper.ARCHIVES:
            (self.source / spec.filename).write_bytes(self.originals[spec.id])
        self.receipt = self.base / 'receipt.json'

    def prepare(self, receipt=None):
        return helper.prepare(self.root, receipt or self.receipt)

    def assert_failed(self, report, code=None):
        self.assertFalse(report['passed'])
        self.assertIn(report['error_code'], helper.ERROR_CODES)
        if code is not None:
            self.assertEqual(code, report['error_code'])
        self.assertLess(len(json.dumps(report)), helper.MAX_RECEIPT_BYTES)
        for item in report['dependencies']:
            for side in ('source', 'target'):
                self.assertIn(item[side]['error_code'], helper.ERROR_CODES | {None})
        self.assertNotIn(str(self.base), json.dumps(report))

    def assert_receipt(self, report):
        self.assertEqual(report, json.loads(self.receipt.read_text(encoding='ascii')))

    def symlink(self, source, target, directory=False):
        try:
            target.symlink_to(source, target_is_directory=directory)
        except (OSError, NotImplementedError) as exc:
            self.skipTest('Symlink fixture unavailable on this platform: ' + type(exc).__name__)

    def test_original_copy_exact_independent_bytes(self):
        report = self.prepare()
        self.assertTrue(report['passed'], report)
        self.assert_receipt(report)
        self.assertEqual([x['status'] for x in report['dependencies']], ['copied', 'copied'])
        for spec, item in zip(helper.ARCHIVES, report['dependencies']):
            source, target = self.source / spec.filename, self.target / spec.filename
            self.assertEqual(target.read_bytes(), self.originals[spec.id])
            self.assertEqual(source.read_bytes(), self.originals[spec.id])
            self.assertEqual(target.stat().st_nlink, 1)
            self.assertNotEqual((source.stat().st_dev, source.stat().st_ino),
                                (target.stat().st_dev, target.stat().st_ino))
            for side in ('source', 'target'):
                self.assertEqual(item[side], {'actual_bytes': spec.bytes, 'actual_sha256': spec.sha256,
                                             'verified': True, 'error_code': None})
        self.assertFalse((self.root / 'scintilla').exists())
        self.assertFalse((self.root / 'lexilla').exists())

    def test_original_reuse_without_writes(self):
        self.assertTrue(self.prepare()['passed'])
        before = {p.name: (p.stat().st_ino, p.stat().st_mtime_ns, p.read_bytes()) for p in self.target.iterdir()}
        report = self.prepare(self.base / 'reuse.json')
        self.assertTrue(report['passed'], report)
        self.assertEqual([x['status'] for x in report['dependencies']], ['reused', 'reused'])
        after = {p.name: (p.stat().st_ino, p.stat().st_mtime_ns, p.read_bytes()) for p in self.target.iterdir()}
        self.assertEqual(before, after)

    def test_network_and_extraction_are_never_used(self):
        with ExitStack() as stack:
            for target in ('socket.socket', 'socket.create_connection', 'urllib.request.urlopen',
                           'zipfile.ZipFile.extract', 'zipfile.ZipFile.extractall'):
                stack.enter_context(mock.patch(target, side_effect=AssertionError('forbidden operation')))
            report = self.prepare()
        self.assertTrue(report['passed'], report)

    def test_missing_source_does_not_fallback(self):
        (self.source / helper.ARCHIVES[0].filename).unlink()
        report = self.prepare()
        self.assert_failed(report, 'source_failed')
        self.assertEqual(report['dependencies'][0]['source']['error_code'], 'path_missing')
        self.assertTrue(report['dependencies'][1]['source']['verified'])
        self.assertFalse(self.target.exists())
        self.assert_receipt(report)

    def test_source_bad_size_bounded_no_hash(self):
        path = self.source / helper.ARCHIVES[0].filename
        path.write_bytes(b'<html>PRIVATE BODY AND PATH</html>')
        report = self.prepare()
        self.assert_failed(report, 'source_failed')
        observed = report['dependencies'][0]['source']
        self.assertEqual(observed['error_code'], 'size_mismatch')
        self.assertIsNone(observed['actual_sha256'])
        self.assertNotIn('PRIVATE', json.dumps(report))
        self.assert_receipt(report)

    def test_source_bad_hash(self):
        path = self.source / helper.ARCHIVES[0].filename
        data = path.read_bytes()
        path.write_bytes(b'X' + data[1:])
        report = self.prepare()
        self.assert_failed(report, 'source_failed')
        observed = report['dependencies'][0]['source']
        self.assertEqual(observed['error_code'], 'hash_mismatch')
        self.assertEqual(observed['actual_sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertFalse(self.target.exists())

    def test_large_sparse_source_not_read(self):
        path = self.source / helper.ARCHIVES[0].filename
        with path.open('wb') as stream:
            stream.truncate(100000000)
        real_read = helper.os.read
        def bounded(fd, count):
            self.assertLessEqual(os.fstat(fd).st_size, max(spec.bytes for spec in helper.ARCHIVES))
            self.assertLessEqual(count, helper.CHUNK_BYTES)
            return real_read(fd, count)
        with mock.patch.object(helper.os, 'read', side_effect=bounded):
            report = self.prepare()
        self.assert_failed(report, 'source_failed')
        self.assertEqual(report['dependencies'][0]['source']['actual_bytes'], 100000000)
        self.assertIsNone(report['dependencies'][0]['source']['actual_sha256'])

    def test_existing_drift_never_clobbered_or_other_archive_copied(self):
        self.target.mkdir(parents=True)
        victim = self.target / helper.ARCHIVES[1].filename
        victim.write_bytes(b'keep these existing bytes')
        report = self.prepare()
        self.assert_failed(report, 'target_failed')
        self.assertEqual(victim.read_bytes(), b'keep these existing bytes')
        self.assertFalse((self.target / helper.ARCHIVES[0].filename).exists())
        self.assert_receipt(report)

    def test_existing_same_size_bad_hash_never_clobbered(self):
        self.target.mkdir(parents=True)
        spec = helper.ARCHIVES[0]
        victim = self.target / spec.filename
        data = b'X' + self.originals[spec.id][1:]
        victim.write_bytes(data)
        report = self.prepare()
        self.assert_failed(report, 'target_failed')
        self.assertEqual(victim.read_bytes(), data)
        self.assertEqual(report['dependencies'][0]['target']['error_code'], 'hash_mismatch')

    def test_source_hardlink_rejected(self):
        source = self.source / helper.ARCHIVES[0].filename
        os.link(source, self.base / 'alias.zip')
        report = self.prepare()
        self.assert_failed(report, 'source_failed')
        self.assertEqual(report['dependencies'][0]['source']['error_code'], 'hardlink_rejected')
        self.assertFalse(self.target.exists())

    def test_target_hardlink_rejected(self):
        self.target.mkdir(parents=True)
        spec = helper.ARCHIVES[0]
        outside = self.base / 'outside.zip'
        outside.write_bytes(self.originals[spec.id])
        os.link(outside, self.target / spec.filename)
        report = self.prepare()
        self.assert_failed(report, 'target_failed')
        self.assertEqual(report['dependencies'][0]['target']['error_code'], 'hardlink_rejected')
        self.assertEqual(outside.read_bytes(), self.originals[spec.id])

    def test_source_symlink_rejected(self):
        source = self.source / helper.ARCHIVES[0].filename
        outside = self.base / 'original.zip'
        source.rename(outside)
        self.symlink(outside, source)
        report = self.prepare()
        self.assert_failed(report, 'source_failed')
        self.assertEqual(report['dependencies'][0]['source']['error_code'], 'link_rejected')

    def test_target_symlink_rejected(self):
        self.target.mkdir(parents=True)
        victim = self.base / 'victim.zip'
        victim.write_bytes(b'outside remains')
        self.symlink(victim, self.target / helper.ARCHIVES[0].filename)
        report = self.prepare()
        self.assert_failed(report, 'target_failed')
        self.assertEqual(victim.read_bytes(), b'outside remains')

    def test_dangling_target_symlink_rejected(self):
        self.target.mkdir(parents=True)
        missing = self.base / 'missing.zip'
        self.symlink(missing, self.target / helper.ARCHIVES[0].filename)
        report = self.prepare()
        self.assert_failed(report, 'target_failed')
        self.assertFalse(missing.exists())

    def test_source_directory_rejected(self):
        source = self.source / helper.ARCHIVES[0].filename
        source.unlink()
        source.mkdir()
        report = self.prepare()
        self.assert_failed(report, 'source_failed')
        self.assertEqual(report['dependencies'][0]['source']['error_code'], 'not_regular')

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'POSIX FIFO fixture')
    def test_source_fifo_rejected_without_blocking(self):
        source = self.source / helper.ARCHIVES[0].filename
        source.unlink()
        os.mkfifo(source)
        report = self.prepare()
        self.assert_failed(report, 'source_failed')
        self.assertEqual(report['dependencies'][0]['source']['error_code'], 'not_regular')

    def test_target_directory_rejected(self):
        (self.target / helper.ARCHIVES[0].filename).mkdir(parents=True)
        report = self.prepare()
        self.assert_failed(report, 'target_failed')
        self.assertEqual(report['dependencies'][0]['target']['error_code'], 'not_regular')

    def test_source_ancestor_symlink_rejected(self):
        directory = self.root / 'third_party'
        moved = self.base / 'moved-sources'
        directory.rename(moved)
        self.symlink(moved, directory, True)
        report = self.prepare()
        self.assert_failed(report, 'link_rejected')
        self.assertFalse(self.target.exists())

    def test_target_ancestor_symlink_rejected(self):
        outside = self.base / 'outside'
        outside.mkdir()
        self.symlink(outside, self.root / 'vendor', True)
        report = self.prepare()
        self.assert_failed(report, 'link_rejected')
        self.assertEqual(list(outside.iterdir()), [])

    def test_repository_root_symlink_rejected(self):
        alias = self.base / 'alias'
        self.symlink(self.root, alias, True)
        report = helper.prepare(alias, self.receipt)
        self.assert_failed(report, 'link_rejected')

    def test_ancestor_above_repository_symlink_rejected(self):
        alias = self.base / 'alias'
        self.symlink(self.base, alias, True)
        report = helper.prepare(alias / 'repo', self.receipt)
        self.assert_failed(report, 'link_rejected')

    def test_parent_traversal_rejected(self):
        report = helper.prepare(self.root / '..' / 'repo', self.receipt)
        self.assert_failed(report, 'unsafe_path')

    def test_receipt_starts_failed_before_copy(self):
        original = helper._copy_exclusive
        seen = []
        def checked(*args):
            snapshot = json.loads(self.receipt.read_text(encoding='ascii'))
            self.assertFalse(snapshot['passed'])
            seen.append(snapshot['error_code'])
            return original(*args)
        with mock.patch.object(helper, '_copy_exclusive', side_effect=checked):
            report = self.prepare()
        self.assertTrue(report['passed'])
        self.assertEqual(seen, ['in_progress', 'in_progress'])

    def test_existing_receipt_not_overwritten(self):
        self.receipt.write_bytes(b'existing receipt, do not modify')
        report = self.prepare()
        self.assert_failed(report, 'receipt_error')
        self.assertEqual(report['receipt_error_code'], 'already_exists')
        self.assertEqual(self.receipt.read_bytes(), b'existing receipt, do not modify')
        self.assertFalse(self.target.exists())

    def test_receipt_symlink_rejected(self):
        victim = self.base / 'victim'
        victim.write_bytes(b'untouched')
        self.symlink(victim, self.receipt)
        report = self.prepare()
        self.assert_failed(report, 'receipt_error')
        self.assertEqual(report['receipt_error_code'], 'link_rejected')
        self.assertEqual(victim.read_bytes(), b'untouched')

    def test_receipt_hardlink_rejected(self):
        victim = self.base / 'victim'
        victim.write_bytes(b'untouched')
        os.link(victim, self.receipt)
        report = self.prepare()
        self.assert_failed(report, 'receipt_error')
        self.assertEqual(report['receipt_error_code'], 'hardlink_rejected')
        self.assertEqual(victim.read_bytes(), b'untouched')

    def test_receipt_ancestor_symlink_rejected(self):
        alias = self.base / 'alias'
        self.symlink(self.base, alias, True)
        report = helper.prepare(self.root, alias / 'receipt.json')
        self.assert_failed(report, 'receipt_error')
        self.assertEqual(report['receipt_error_code'], 'link_rejected')
        self.assertFalse(self.receipt.exists())
        self.assertFalse(self.target.exists())

    def test_missing_receipt_parent_fails_before_output(self):
        report = self.prepare(self.base / 'absent' / 'receipt.json')
        self.assert_failed(report, 'receipt_error')
        self.assertEqual(report['receipt_error_code'], 'path_missing')
        self.assertFalse(self.target.exists())

    def test_receipt_windows_aliases_rejected(self):
        for name in ('receipt:stream', 'CON', 'nul.txt', 'COM1.json', 'LPT¹.txt',
                     'con .txt', 'receipt.', 'receipt ', 'bad?name', 'bad\\name'):
            with self.subTest(name=name):
                report = self.prepare(self.base / name)
                self.assert_failed(report, 'receipt_error')
                self.assertEqual(report['receipt_error_code'], 'unsafe_path')
                self.assertFalse(self.target.exists())

    def test_non_ascii_and_interior_spaces_accepted(self):
        new_root = self.base / '中文 repo'
        self.root.rename(new_root)
        self.root = new_root
        report = self.prepare(self.base / '结果 receipt.json')
        self.assertTrue(report['passed'], report)

    def test_unexpected_exception_never_leaks_body_or_path(self):
        private = '<html>PRIVATE ' + str(self.base) + '</html>'
        with mock.patch.object(helper, '_run', side_effect=RuntimeError(private)):
            report = self.prepare()
        self.assert_failed(report, 'internal_error')
        self.assertNotIn('PRIVATE', self.receipt.read_text())
        self.assert_receipt(report)

    def test_copy_io_error_has_failed_receipt(self):
        with mock.patch.object(helper, '_copy_exclusive', side_effect=OSError('PRIVATE BODY')):
            report = self.prepare()
        self.assert_failed(report, 'target_failed')
        self.assertEqual(report['dependencies'][0]['target']['error_code'], 'io_error')
        self.assertNotIn('PRIVATE', self.receipt.read_text())
        self.assert_receipt(report)

    def test_initial_receipt_sync_error_prevents_copy(self):
        with mock.patch.object(helper.os, 'fsync', side_effect=OSError('PRIVATE STORAGE ERROR')):
            report = self.prepare()
        self.assert_failed(report, 'receipt_error')
        self.assertEqual(report['receipt_error_code'], 'io_error')
        self.assertFalse(self.target.exists())
        self.assert_receipt(report)

    def test_final_receipt_sync_failure_rewrites_failed_state(self):
        original = helper.os.fsync
        receipt_syncs = 0
        def fail_once(fd):
            nonlocal receipt_syncs
            if os.fstat(fd).st_size < helper.MAX_RECEIPT_BYTES:
                receipt_syncs += 1
                if receipt_syncs == 2:
                    raise OSError('PRIVATE FINAL SYNC ERROR')
            original(fd)
        with mock.patch.object(helper.os, 'fsync', side_effect=fail_once):
            report = self.prepare()
        self.assert_failed(report, 'receipt_error')
        self.assertEqual(report['receipt_error_code'], 'io_error')
        self.assertGreaterEqual(receipt_syncs, 3)
        self.assert_receipt(report)

    def test_partial_copy_retained_and_never_overwritten(self):
        original = helper._write_all
        def fail_copy(fd, data):
            if len(data) > helper.MAX_RECEIPT_BYTES:
                os.write(fd, data[:100])
                raise OSError('PRIVATE failure')
            return original(fd, data)
        with mock.patch.object(helper, '_write_all', side_effect=fail_copy):
            report = self.prepare()
        self.assert_failed(report, 'target_failed')
        partial = self.target / helper.ARCHIVES[0].filename
        self.assertEqual(partial.read_bytes(), self.originals[helper.ARCHIVES[0].id][:100])
        self.assert_receipt(report)
        retry = self.prepare(self.base / 'retry.json')
        self.assert_failed(retry, 'target_failed')
        self.assertEqual(partial.stat().st_size, 100)

    @unittest.skipIf(os.name == 'nt', 'POSIX replacement; Windows held file denies rename')
    def test_failed_copy_does_not_delete_replacement(self):
        original = helper._write_all
        victim = self.target / helper.ARCHIVES[0].filename
        def fail_copy(fd, data):
            if len(data) > helper.MAX_RECEIPT_BYTES:
                os.write(fd, data[:100])
                victim.unlink()
                victim.write_bytes(b'replacement owner bytes')
                raise OSError('simulated write failure')
            return original(fd, data)
        with mock.patch.object(helper, '_write_all', side_effect=fail_copy):
            report = self.prepare()
        self.assert_failed(report, 'target_failed')
        self.assertEqual(victim.read_bytes(), b'replacement owner bytes')

    def test_racing_existing_target_never_overwritten(self):
        original = helper._copy_exclusive
        def race(directory, spec, data):
            (directory.path / spec.filename).write_bytes(b'race owner content')
            return original(directory, spec, data)
        with mock.patch.object(helper, '_copy_exclusive', side_effect=race):
            report = self.prepare()
        self.assert_failed(report, 'target_failed')
        self.assertEqual((self.target / helper.ARCHIVES[0].filename).read_bytes(), b'race owner content')

    def test_source_changed_after_copy_detected(self):
        original = helper._copy_exclusive
        def changed(directory, spec, data):
            original(directory, spec, data)
            if spec == helper.ARCHIVES[1]:
                source = self.source / helper.ARCHIVES[0].filename
                data = source.read_bytes()
                source.write_bytes(b'X' + data[1:])
        with mock.patch.object(helper, '_copy_exclusive', side_effect=changed):
            report = self.prepare()
        self.assert_failed(report)
        self.assertEqual(report['dependencies'][0]['source']['error_code'], 'hash_mismatch')
        self.assert_receipt(report)

    def test_target_changed_before_final_check_detected(self):
        original = helper._copy_exclusive
        def changed(directory, spec, data):
            original(directory, spec, data)
            if spec == helper.ARCHIVES[1]:
                target = directory.path / helper.ARCHIVES[0].filename
                data = target.read_bytes()
                target.write_bytes(b'X' + data[1:])
        with mock.patch.object(helper, '_copy_exclusive', side_effect=changed):
            report = self.prepare()
        self.assert_failed(report, 'target_failed')
        self.assertEqual(report['dependencies'][0]['target']['error_code'], 'hash_mismatch')
        self.assert_receipt(report)

    @unittest.skipIf(os.name == 'nt', 'POSIX descriptor-relative race; Windows pins directory names')
    def test_ancestor_replacement_detected(self):
        original = helper._copy_exclusive
        def changed(directory, spec, data):
            directory.path.rename(directory.path.with_name('moved'))
            directory.path.mkdir()
            return original(directory, spec, data)
        with mock.patch.object(helper, '_copy_exclusive', side_effect=changed):
            report = self.prepare()
        self.assert_failed(report, 'target_failed')
        self.assertEqual(report['dependencies'][0]['target']['error_code'], 'path_changed')
        self.assertEqual(list(self.target.iterdir()), [])

    def test_cli_success_and_failure_json_only(self):
        command = [sys.executable, '-B', str(Path(helper.__file__).absolute()),
                   '--root', str(self.root), '--receipt', str(self.receipt)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout)
        report = json.loads(result.stdout)
        self.assertTrue(report['passed'])
        self.assertEqual(result.stderr, '')
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 1)
        self.assert_failed(json.loads(result.stdout), 'receipt_error')
        self.assertEqual(result.stderr, '')

    def test_cli_bad_arguments_do_not_echo_private_text(self):
        command = [sys.executable, '-B', str(Path(helper.__file__).absolute()),
                   '--PRIVATE-<html>-argument']
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assert_failed(report, 'invalid_arguments')
        self.assertNotIn('PRIVATE', result.stdout + result.stderr)

    @unittest.skipUnless(os.name == 'nt', 'Native Windows directory-sharing proof')
    def test_windows_pinned_directories_reject_rename(self):
        with helper.SafeDir(self.source):
            for path in (self.source, self.source.parent, self.root):
                with self.subTest(level=path.name):
                    with self.assertRaises(OSError) as caught:
                        path.rename(path.with_name(path.name + '-moved'))
                    self.assertIn(caught.exception.winerror, (5, 32))
        # The same operation succeeds after all handles are closed.
        moved = self.source.with_name('renamed')
        self.source.rename(moved)
        moved.rename(self.source)

    @unittest.skipUnless(os.name == 'nt', 'Native Windows directory-write exclusion proof')
    def test_windows_pinned_directory_rejects_write_handle(self):
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        create = kernel.CreateFileW
        create.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                           wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
        create.restype = wintypes.HANDLE
        close = kernel.CloseHandle
        close.argtypes = (wintypes.HANDLE,)
        close.restype = wintypes.BOOL
        def write_handle():
            # GENERIC_WRITE is needed for FSCTL_SET_REPARSE_POINT. Share all
            # modes here, so only the helper's denied write-sharing blocks us.
            return create(str(self.source), 0x40000000, 7, None, 3, 0x02200000, None)
        invalid = wintypes.HANDLE(-1).value
        with helper.SafeDir(self.source):
            handle = write_handle()
            error = ctypes.get_last_error()
            if handle != invalid:
                close(handle)
                self.fail('Pinned directory unexpectedly allowed a write handle')
            self.assertEqual(error, 32)
        handle = write_handle()
        self.assertNotEqual(handle, invalid, 'Write must be available when helper is not holding directory')
        close(handle)

    @unittest.skipUnless(os.name == 'nt', 'Native Windows file-sharing proof')
    def test_windows_read_source_denies_write_and_rename(self):
        spec = helper.ARCHIVES[0]
        path = self.source / spec.filename
        with helper.SafeDir(self.source) as source:
            fd = source.open(spec.filename)
            try:
                with self.assertRaises(OSError) as caught:
                    with path.open('r+b'):
                        self.fail('Read source unexpectedly allowed a writer')
                self.assertIn(caught.exception.winerror, (5, 32))
                with self.assertRaises(OSError):
                    path.rename(path.with_suffix('.moved'))
            finally:
                os.close(fd)
        with path.open('r+b'):
            pass

    def junction(self, link, destination):
        # Directory junction creation needs no symlink privilege. This is a
        # required Windows fixture: inability to create it is a test FAILURE.
        result = subprocess.run(['cmd.exe', '/d', '/c', 'mklink', '/J', str(link), str(destination)],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, 'Required native junction fixture failed')
        self.assertTrue(link.lstat().st_file_attributes & 0x400)

    @unittest.skipUnless(os.name == 'nt', 'Native Windows source-junction proof')
    def test_windows_source_junction_rejected(self):
        original = self.root / 'third_party'
        moved = self.base / 'moved-source'
        original.rename(moved)
        self.junction(original, moved)
        report = self.prepare()
        self.assert_failed(report, 'link_rejected')
        self.assertFalse(self.target.exists())

    @unittest.skipUnless(os.name == 'nt', 'Native Windows target-junction proof')
    def test_windows_target_junction_rejected(self):
        outside = self.base / 'outside'
        outside.mkdir()
        self.junction(self.root / 'vendor', outside)
        report = self.prepare()
        self.assert_failed(report, 'link_rejected')
        self.assertEqual(list(outside.iterdir()), [])

    @unittest.skipUnless(os.name == 'nt', 'Native Windows receipt-junction proof')
    def test_windows_receipt_junction_rejected(self):
        alias = self.base / 'alias'
        self.junction(alias, self.base)
        report = self.prepare(alias / 'receipt.json')
        self.assert_failed(report, 'receipt_error')
        self.assertEqual(report['receipt_error_code'], 'link_rejected')
        self.assertFalse(self.target.exists())
        self.assertFalse(self.receipt.exists())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archives', type=Path, default=FIXTURES)
    args, remaining = parser.parse_known_args()
    FIXTURES = args.archives
    unittest.main(argv=[sys.argv[0], *remaining], verbosity=2)
