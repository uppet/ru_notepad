#!/usr/bin/env python3
"""Portable packaging regressions use fake PE files; no Windows pass is claimed."""
import hashlib
import json
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import package as package


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ru-package-unit-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.binary = self.root / 'bin'
        self.binary.mkdir()
        self.evidence = self.root / 'evidence'
        self.evidence.mkdir()
        for relative in {*package.RUNTIME_FILES, *package.TEST_FILES, 'src/main.ru',
                         'packaging/diagnostic_launcher.c', 'packaging/samples/example.txt'}:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('synthetic source\n', encoding='utf-8')
        (self.root / 'VERSION').write_text('0.1.2', encoding='utf-8')
        self.dependencies = {name: dict(value) for name, value in package.DEPENDENCIES.items()}
        for dependency in self.dependencies.values():
            source = self.root / 'vendor' / dependency['folder'] / 'License.txt'
            source.parent.mkdir(parents=True)
            source.write_text('Synthetic permissive license\n', encoding='utf-8')
            archive = self.root / 'vendor/downloads' / dependency['archive']
            archive.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(archive, 'w') as output:
                output.write(source, dependency['folder'] + '/License.txt')
            dependency['sha256'] = package.sha(archive)
        self.addCleanup(patch.stopall)
        patch.object(package, 'DEPENDENCIES', self.dependencies).start()
        patch.object(package.subprocess, 'check_output', return_value='DLL Name: KERNEL32.dll\nDLL Name: msvcrt.dll\n').start()
        for name in package.BINARY_NAMES:
            data = bytearray(128)
            data[:2] = b'MZ'
            struct.pack_into('<I', data, 60, 64)
            data[64:68] = b'PE\0\0'
            struct.pack_into('<H', data, 68, 0x8664)
            (self.binary / name).write_bytes(data + name.encode())
        for name in (package.RUNTIME_NAMES[0], *package.TEST_NAMES):
            source = 'src/main.ru' if name == 'ru_notepad.exe' else f'tests/{Path(name).stem}.ru'
            entry = self.root / source
            entry.parent.mkdir(parents=True, exist_ok=True)
            if not entry.exists():
                entry.write_text('synthetic test source\n', encoding='utf-8')
            receipt = {'app_version': '0.1.2', 'exe_sha256': package.sha(self.binary / name),
                'dll_sha256': package.sha(self.binary / 'Scintilla.dll'),
                'lexilla_dll_sha256': package.sha(self.binary / 'Lexilla.dll'),
                'source_sha256': {'src/main.ru': package.sha(self.root / 'src/main.ru')},
                'entry_source': source, 'entry_sha256': package.sha(entry),
                'generated_c_sha256': 'c' * 64, 'translation_unit_sha256': 'd' * 64,
                'build_input_sha256': {'packaging/diagnostic_launcher.c': package.sha(self.root / 'packaging/diagnostic_launcher.c')},
                'ru_tree': 'a' * 40, 'ru_commit': 'b' * 40,
                'compiler_command': ['PRIVATE_WORKSPACE/home/private/compiler', 'PRIVATE_SECRET'],
            }
            for dependency in self.dependencies.values():
                receipt[dependency['folder'] + '_version'] = dependency['version']
                receipt[dependency['folder'] + '_archive_sha256'] = dependency['sha256']
            package.save_json(self.binary / Path(name).with_suffix('.build.json'), receipt)
        self.summary = {'platform': 'native-windows-x64', 'passed': True,
                        'native_tests_passed': True, 'tests': [],
                        'tested_binary_sha256': package.binary_snapshot(self.binary)}
        package.save_json(self.evidence / 'native-acceptance.json', self.summary)
        (self.evidence / 'msys2-packages.log').write_text('synthetic packages\n')
        (self.evidence / 'document_policy.stdout.log').write_text('synthetic results\n')
        (self.evidence / 'private-unrelated.txt').write_text('DO NOT COLLECT')
        (self.evidence / 'nested').mkdir()
        (self.evidence / 'nested/private.json').write_text('DO NOT COLLECT')

    def create(self, destination='dist'):
        def licenses(target):
            (target / 'GCC.txt').write_text('Synthetic GCC runtime notice')
        return package.create_packages(self.root, self.binary, self.root / destination,
            self.evidence, 'fake-objdump', self.summary, licenses, {'app_commit': 'e' * 40},
            package.evidence_names(['document_policy']))

    def archives(self, result, destination='dist'):
        return [self.root / destination / result['packages'][kind]['name'] for kind in ('runtime', 'tests')]

    def modify_receipt(self, name, change):
        path = self.binary / Path(name).with_suffix('.build.json')
        receipt = json.loads(path.read_text())
        change(receipt)
        package.save_json(path, receipt)

    def rewrite_zip(self, archive, change):
        with zipfile.ZipFile(archive) as source:
            entries = {info.filename: source.read(info.filename) for info in source.infolist()}
        change(entries)
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as output:
            for name, data in entries.items():
                output.writestr(name, data)

    def test_both_inventories_hashes_crc_and_exact_runtime_identity(self):
        result = self.create()
        runtime, tests = self.archives(result)
        package.verify_package_pair(runtime, tests)
        self.assertTrue(result['runtime_byte_identity_verified'])
        for archive, kind in ((runtime, 'runtime'), (tests, 'tests')):
            files = package.verify_archive(archive)
            build = json.loads(files['BUILD.json'])
            self.assertEqual(build['package_kind'], kind)
            self.assertEqual(build['runtime_binary_sha256'], result['runtime_binary_sha256'])
            self.assertIn('licenses/Lexilla.txt', files)
            self.assertIn('licenses/Scintilla.txt', files)
            self.assertEqual(archive.with_suffix('.zip.sha256').read_text(), f'{package.sha(archive)}  {archive.name}\n')
            if kind == 'runtime':
                self.assertFalse(set(package.TEST_NAMES) & files.keys())
                self.assertFalse(any(name.endswith(('.log', '.cmd', '.ps1')) for name in files))
            else:
                self.assertTrue(set(package.BINARY_NAMES) <= files.keys())
                self.assertIn('run-tests.cmd', files)
                self.assertIn('native-test-evidence/native-acceptance.json', files)
                self.assertIn('native-test-evidence/document_policy.stdout.log', files)

    def test_only_allowlisted_synthetic_evidence_is_collected(self):
        tests = self.archives(self.create())[1]
        files = package.verify_archive(tests)
        self.assertFalse(any('private' in name or 'nested' in name for name in files))
        self.assertNotIn('PRIVATE_WORKSPACE', files['BUILD.json'].decode())
        self.assertNotIn('PRIVATE_SECRET', files['BUILD.json'].decode())
        self.assertNotIn(str(self.root), files['BUILD.json'].decode())

    def test_missing_lexilla_blocks_both_packages(self):
        (self.binary / 'Lexilla.dll').unlink()
        with self.assertRaisesRegex(RuntimeError, 'Missing'):
            self.create()
        self.assertFalse((self.root / 'dist').exists())

    def test_incorrect_lexilla_blocks_both_packages(self):
        with (self.binary / 'Lexilla.dll').open('ab') as output:
            output.write(b'tampered')
        with self.assertRaisesRegex(RuntimeError, 'Dependency build receipt'):
            self.create()

    def test_dependency_receipt_version_is_checked(self):
        self.modify_receipt('ru_notepad.exe', lambda r: r.update(lexilla_version='WRONG'))
        with self.assertRaisesRegex(RuntimeError, 'Dependency build receipt'):
            self.create()

    def test_wrong_official_dependency_pin_blocks_packaging(self):
        archive = self.root / 'vendor/downloads/lexilla554.zip'
        with archive.open('ab') as output:
            output.write(b'changed')
        with self.assertRaisesRegex(RuntimeError, 'archive hash mismatch'):
            self.create()

    def test_wrong_dependency_license_blocks_packaging(self):
        (self.root / 'vendor/lexilla/License.txt').write_text('wrong license')
        with self.assertRaisesRegex(RuntimeError, 'license differs'):
            self.create()

    def test_changed_test_binary_blocks_packaging(self):
        with (self.binary / 'syntax_native.exe').open('ab') as output:
            output.write(b'changed')
        with self.assertRaisesRegex(RuntimeError, 'Build receipt/version'):
            self.create()

    def test_matching_new_receipts_cannot_replace_tested_binary_snapshot(self):
        path = self.binary / 'syntax_native.exe'
        with path.open('ab') as output:
            output.write(b'changed')
        self.modify_receipt('syntax_native.exe', lambda r: r.update(exe_sha256=package.sha(path)))
        with self.assertRaisesRegex(RuntimeError, 'exact packaged binary snapshot'):
            self.create()

    def test_missing_native_acceptance_blocks_packaging(self):
        self.summary['native_tests_passed'] = False
        with self.assertRaisesRegex(RuntimeError, 'Native acceptance'):
            self.create()

    def test_cross_build_remains_explicitly_unverified(self):
        self.summary.update(platform='cross-built-unverified', passed=False, native_tests_passed=False)
        for archive in self.archives(self.create()):
            build = json.loads(package.verify_archive(archive)['BUILD.json'])
            self.assertIn('NOT RUN', build['status'])
            self.assertFalse(build['native_acceptance']['passed'])

    def test_cross_build_cannot_claim_acceptance(self):
        self.summary['platform'] = 'cross-built-unverified'
        with self.assertRaisesRegex(RuntimeError, 'cannot claim'):
            self.create()

    def test_source_and_version_changes_block_packaging(self):
        (self.root / 'VERSION').write_text('9.9.9')
        with self.assertRaisesRegex(RuntimeError, 'receipt/version'):
            self.create()

    def test_unsafe_receipt_source_path_is_rejected(self):
        self.modify_receipt('ru_notepad.exe', lambda r: r.update(entry_source='../outside'))
        with self.assertRaisesRegex(RuntimeError, 'Unsafe source path'):
            self.create()

    def test_oversized_evidence_is_rejected(self):
        (self.evidence / 'document_policy.stdout.log').write_bytes(b'x' * (package.MAX_LOG_BYTES + 1))
        with self.assertRaisesRegex(RuntimeError, 'exceeds 1 MiB'):
            self.create()
        self.assertFalse((self.root / 'dist').exists(), 'No partial package pair may remain')

    def test_existing_destination_is_never_overwritten(self):
        self.create()
        with self.assertRaises(FileExistsError):
            self.create()

    def test_destination_creation_race_never_deletes_another_output(self):
        destination = self.root / 'dist'
        original_mkdir = Path.mkdir
        def raced_mkdir(path, *args, **kwargs):
            if path == destination:
                original_mkdir(path, *args, **kwargs)
                (path / 'someone-elses-output.txt').write_text('preserve')
                raise FileExistsError('Another writer won destination creation')
            return original_mkdir(path, *args, **kwargs)
        with patch.object(Path, 'mkdir', raced_mkdir):
            with self.assertRaises(FileExistsError):
                self.create()
        self.assertEqual((destination / 'someone-elses-output.txt').read_text(), 'preserve')

    def test_hash_manifest_detects_changed_payload(self):
        runtime = self.archives(self.create())[0]
        self.rewrite_zip(runtime, lambda entries: entries.update({runtime.stem + '/README.txt': b'changed'}))
        with self.assertRaisesRegex(RuntimeError, 'hash manifest mismatch'):
            package.verify_archive(runtime)

    def test_hash_manifest_detects_missing_payload(self):
        runtime = self.archives(self.create())[0]
        self.rewrite_zip(runtime, lambda entries: entries.pop(runtime.stem + '/Lexilla.dll'))
        with self.assertRaisesRegex(RuntimeError, 'hash manifest mismatch'):
            package.verify_archive(runtime)

    def test_zip_crc_corruption_is_rejected(self):
        runtime = self.archives(self.create())[0]
        with zipfile.ZipFile(runtime) as archive:
            entry = next(info for info in archive.infolist() if info.filename.endswith('/README.txt'))
        with runtime.open('r+b') as output:
            output.seek(entry.header_offset)
            header = output.read(30)
            name_length, extra_length = struct.unpack_from('<HH', header, 26)
            offset = entry.header_offset + 30 + name_length + extra_length
            output.seek(offset)
            byte = output.read(1)
            output.seek(offset)
            output.write(bytes([byte[0] ^ 0xFF]))
        with self.assertRaises(Exception):
            package.verify_archive(runtime)

    def test_pair_detects_independently_rehashed_runtime_change(self):
        runtime, tests = self.archives(self.create())
        prefix = tests.stem + '/'
        def change(entries):
            entries[prefix + 'Lexilla.dll'] += b'changed'
            build = json.loads(entries[prefix + 'BUILD.json'])
            build['runtime_binary_sha256']['Lexilla.dll'] = hashlib.sha256(entries[prefix + 'Lexilla.dll']).hexdigest()
            entries[prefix + 'BUILD.json'] = json.dumps(build).encode()
            entries[prefix + 'SHA256SUMS.txt'] = ''.join(
                f'{hashlib.sha256(data).hexdigest()}  {name.removeprefix(prefix)}\n'
                for name, data in sorted(entries.items()) if not name.endswith('/SHA256SUMS.txt')).encode()
        self.rewrite_zip(tests, change)
        package.verify_archive(tests)
        with self.assertRaisesRegex(RuntimeError, 'manifests disagree'):
            package.verify_package_pair(runtime, tests)

    def test_pe_import_gate_requires_bundled_dependency(self):
        (self.binary / 'Lexilla.dll').unlink()
        with patch.object(package.subprocess, 'check_output', return_value='DLL Name: Lexilla.dll'):
            with self.assertRaisesRegex(RuntimeError, 'Missing'):
                package.inspect_pe(self.binary / 'ru_notepad.exe', 'fake-objdump')

    def test_pe_import_gate_rejects_hidden_compiler_runtime(self):
        with patch.object(package.subprocess, 'check_output', return_value='DLL Name: libwinpthread-1.dll'):
            with self.assertRaisesRegex(RuntimeError, 'unpackaged'):
                package.inspect_pe(self.binary / 'Lexilla.dll', 'fake-objdump')

    def test_truncated_pe_is_rejected(self):
        (self.binary / 'Lexilla.dll').write_bytes(b'MZ')
        with self.assertRaisesRegex(RuntimeError, 'PE header'):
            package.inspect_pe(self.binary / 'Lexilla.dll', 'fake-objdump')


if __name__ == '__main__':
    unittest.main(verbosity=2)
