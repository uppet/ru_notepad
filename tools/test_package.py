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
import windows_ci as ci


def observer_evidence():
    """Synthetic receipt data only; never native or GUI execution evidence."""
    observer = ci.gui_ru_observer_record()
    observer.update(scalar_calls=24, wm_null_calls=3, sendmessage_calls=27,
        query_wall_ms=20.0, max_query_ms=2.0, snapshot_count=1, snapshot_wall_ms=50.0,
        max_snapshot_ms=50.0, max_snapshot_messages=24,
        snapshots=[{'start_ms': 10.0, 'wall_ms': 50.0, 'messages': 24, 'final': True}],
        response_starts_ms=[0.0, 50.0, 100.0])
    receipts = []
    for seq in range(1, 4):
        receipt = dict.fromkeys(ci.GUI_RU_SNAPSHOT_INTEGER_FIELDS | ci.GUI_RU_SNAPSHOT_TIME_FIELDS, 0)
        receipt.update(seq=seq, ok=1, generation=1 if seq == 1 else 2,
            pending=int(seq == 2), bytes=1000000 if seq == 3 else 100,
            feed=1000000 if seq == 3 else 100, read_bytes=1000000 if seq == 3 else 100)
        receipts.append(receipt)
    diagnostics = {'message': ci.GUI_RU_DIAGNOSTIC_MESSAGE, 'capture_limit_ms': 1000,
        'requests': [{'phase': phase, 'post_wall_ms': 0.1, 'accepted': True}
                     for phase in ('baseline', 'pending', 'final')],
        'receipts': receipts, 'post_wall_ms': 0.3, 'log_reads': 2,
        'captures': [{'phase': phase, 'wall_ms': 0.2, 'log_reads': 1} for phase in ('baseline', 'final')],
        'log_read_wall_ms': 0.2, 'max_log_read_ms': 0.1}
    return {'observer': observer, 'diagnostics': diagnostics,
            'head_style_measurement': ci.GUI_RU_HEAD_MEASUREMENT}


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
                         *ci.SCANNER_PREFLIGHT_SOURCES,
                         *package.RESOURCE_INPUTS, *package.NATIVE_BUILD_DRIVERS,
                         *(source for sources in package.NATIVE_COMPILE_SOURCES.values() for source in sources),
                         'native/ru_scan.h', 'native/ru_unicode_data.h',
                         'packaging/diagnostic_launcher.c', 'packaging/samples/example.txt',
                         'packaging/samples/example.ru'}:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('synthetic source\n', encoding='utf-8')
        (self.root / 'VERSION').write_text('0.1.4', encoding='utf-8')
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
        patch.object(package, 'UNICODE_LICENSE_SHA256', package.sha(self.root / 'packaging/licenses/Unicode.txt')).start()
        patch.object(package.subprocess, 'check_output', return_value='DLL Name: KERNEL32.dll\nDLL Name: msvcrt.dll\n').start()
        for name in package.BINARY_NAMES:
            data = bytearray(128)
            data[:2] = b'MZ'
            struct.pack_into('<I', data, 60, 64)
            data[64:68] = b'PE\0\0'
            struct.pack_into('<H', data, 68, 0x8664)
            (self.binary / name).write_bytes(data + name.encode())
        self.native_receipts = {}
        for name, compile_sources in package.NATIVE_COMPILE_SOURCES.items():
            inputs = {'output_name': name, 'compile_sources': list(compile_sources),
                'source_sha256': package.native_source_snapshot(self.root),
                'driver_sha256': {relative: package.sha(self.root / relative) for relative in package.NATIVE_BUILD_DRIVERS},
                'compiler_path': 'PRIVATE_WORKSPACE/home/private/compiler',
                'compiler_sha256': 'f' * 64, 'compiler_version_sha256': 'e' * 64,
                'compiler_flags': list(package.NATIVE_CFLAGS), 'link_libraries': list(package.NATIVE_LINK_LIBRARIES)}
            receipt = {'name': name, 'build_inputs': inputs, 'build_key': package.native_build_key(inputs),
                       'dll_sha256': package.sha(self.binary / name)}
            package.save_json(self.binary / (Path(name).stem + '.native-build.json'), receipt)
            self.native_receipts[name] = receipt
        for name in (package.RUNTIME_NAMES[0], *package.TEST_NAMES):
            source = 'src/main.ru' if name == 'ru_notepad.exe' else f'tests/{Path(name).stem}.ru'
            entry = self.root / source
            entry.parent.mkdir(parents=True, exist_ok=True)
            if not entry.exists():
                entry.write_text('synthetic test source\n', encoding='utf-8')
            receipt = {'app_version': '0.1.4', 'exe_sha256': package.sha(self.binary / name),
                'dll_sha256': package.sha(self.binary / 'Scintilla.dll'),
                'lexilla_dll_sha256': package.sha(self.binary / 'Lexilla.dll'),
                'source_sha256': {'src/main.ru': package.sha(self.root / 'src/main.ru')} | package.native_source_snapshot(self.root),
                'native_helper_sha256': package.sha(self.binary / package.NATIVE_HELPER_NAME),
                'native_helper_build_key': self.native_receipts[package.NATIVE_HELPER_NAME]['build_key'],
                'entry_source': source, 'entry_sha256': package.sha(entry),
                'generated_c_sha256': 'c' * 64, 'translation_unit_sha256': 'd' * 64,
                'build_input_sha256': {relative: package.sha(self.root / relative)
                    for relative in (*package.RESOURCE_INPUTS, 'packaging/diagnostic_launcher.c')},
                'ru_tree': 'a' * 40, 'ru_commit': 'b' * 40,
                'compiler_command': ['PRIVATE_WORKSPACE/home/private/compiler', 'PRIVATE_SECRET'],
            }
            for dependency in self.dependencies.values():
                receipt[dependency['folder'] + '_version'] = dependency['version']
                receipt[dependency['folder'] + '_archive_sha256'] = dependency['sha256']
            package.save_json(self.binary / Path(name).with_suffix('.build.json'), receipt)
        self.summary = {'platform': 'native-windows-x64', 'passed': True,
                        'native_tests_passed': True, 'acl_requested': True, 'tests': [],
                        'tested_binary_sha256': package.binary_snapshot(self.binary)}
        sources = ci.scanner_preflight_sources(self.root)
        self.summary['scanner_preflight'] = {'name': package.SCANNER_PREFLIGHT_NAME,
            'passed': True, 'executed': True, 'cleanup_killed': False, 'exit_code': 0,
            'source_sha256': sources, 'report': {'cases': 157, 'chunk_checks': 942,
                'ru_assertions_per_backend': 0, 'sanitizer': None,
                'library_sha256': self.summary['tested_binary_sha256'][package.NATIVE_HELPER_NAME],
                'source_sha256': sources['native/ru_scan.c']}}
        names = [name for name, _ in ci.NATIVE_CONSOLE_TESTS] + [case[0] for case in ci.SYNTAX_FALLBACK_TESTS] + ['file_codec_security', *sorted(ci.GUI_NAMES)]
        for name in names:
            result = {'name': name, 'passed': True, 'executed': True, 'cleanup_killed': False,
                      'exit_code': 0, 'skips': []}
            if name in ci.GUI_NAMES:
                result.update(main_hwnd_seen=True, close_posted=True, detached_from_console=True)
            else:
                result['assertions_passed'] = ci.expected_assertions(name)
            if name == 'ru_syntax_native':
                result['performance'] = [{'size': size, 'initial_read_bytes': size,
                    'edit_read_bytes': 1024, 'reused_bytes': size - 1024, 'max_read': 1024,
                    'initial_ms': 100.0, 'edit_ms': 2.0, 'max_tick_ms': 3.0, 'max_chunk_ms': 1.0}
                    for size in ci.RU_PERFORMANCE_SIZES]
            if name == 'ru_syntax_native':
                result['gui_sync_performance'] = {'size': 1000000, 'source_chars': 636370,
                    'wall_ms': 100, 'read_bytes': 1000000, 'max_read': 1024, 'max_tick_ms': 3,
                    'max_chunk_ms': 1, 'chunks': 1000,
                    'source_sha256': hashlib.sha256(ci.gui_ru_timer_fixture()[0]).hexdigest()}
            if name == 'app_ru_timer_native':
                result['timer_performance'] = {'size': 1000000, 'source_chars': 636370,
                    'wall_ms': 100, 'ticks': 10, 'work_ms': 40, 'gap_ms': 50, 'max_tick_ms': 4,
                    'max_gap_ms': 6, 'read_bytes': 1000000, 'max_read': 1024, 'chunks': 1000,
                    'feed': 1000000, 'bytes': 1000000, 'pending': 0, 'text_notifications': 0,
                    'style_notifications': 0, 'fold_notifications': 0,
                    'posts': 9, 'continuation_ticks': 8, 'queue_yields': 2, 'stale_messages': 0,
                    'source_sha256': hashlib.sha256(ci.gui_ru_timer_fixture()[0]).hexdigest()}
            if name in {case[0] for case in ci.SYNTAX_FALLBACK_TESTS}:
                result['fixture_binary_sha256'] = {target: self.summary['tested_binary_sha256'][source]
                                                  for target, source in ci.syntax_fallback_layout(name).items()}
            if name in {'main-gui-file-entry', 'main-gui-ru-syntax'}:
                checks = ci.GUI_FILE_CHECKS if name == 'main-gui-file-entry' else ci.GUI_RU_CHECKS
                result.update({key: True for key in checks})
                result['fixture_binary_sha256'] = {binary: self.summary['tested_binary_sha256'][binary]
                                                  for binary in package.RUNTIME_NAMES}
            if name == 'main-gui-ru-syntax':
                data, probes = ci.gui_ru_timer_fixture()
                result['timer_performance'] = {'size': len(data), 'wall_ms': 100.0,
                    'first_head_style_ms': 10.0, 'max_response_ms': 2.0, 'probes': 3,
                    'source_sha256': hashlib.sha256(data).hexdigest(), 'style_probes': probes,
                    'responsiveness': {'measurement': ci.GUI_RU_RESPONSE_MEASUREMENT,
                        'navigation': [dict(step, wall_ms=1.0, while_styling=True) for step in ci.GUI_RU_NAVIGATION],
                        'paint': {'invalidations': 1, 'pending_observed': True, 'already_serviced': False,
                                  'cleared': True, 'wall_ms': 2.0, 'while_styling': True}},
                    'last_probe': {'opened': True, 'length': len(data), 'clean': True,
                        'end_styled': len(data), 'status': 'Ln 1    UTF-8    Ru',
                        'style_matches': {name: True for name in probes}}}
                result['timer_performance'].update(observer_evidence())
                edit_data, edit_probes, edit_folds, _ = ci.gui_ru_edit_fixture()
                result['edit_performance'] = {'size': len(edit_data), 'source_sha256': hashlib.sha256(edit_data).hexdigest(),
                    'style_probes': edit_probes, 'fold_probes': edit_folds, 'undo_commands': 6,
                    'measurement': ci.GUI_RU_EDIT_MEASUREMENT,
                    'operations': [dict(operation, wall_ms=100.0, max_response_ms=1.0, probes=2)
                                   for operation in ci.gui_ru_edit_operations()]}
            self.summary['tests'].append(result)
        for name in package.required_evidence_names(self.summary):
            (self.evidence / name).write_text('synthetic required evidence\n', encoding='utf-8')
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
            package.evidence_names([test['name'] for test in self.summary['tests']
                                    if test['name'] not in ci.GUI_NAMES]))

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
            self.assertEqual(len(build['runtime_binary_sha256']), 4)
            self.assertEqual(build['native_helpers'][package.NATIVE_HELPER_NAME]['dll_sha256'],
                             package.sha(self.binary / package.NATIVE_HELPER_NAME))
            self.assertIn('licenses/Lexilla.txt', files)
            self.assertIn('licenses/Scintilla.txt', files)
            self.assertEqual(files['licenses/Unicode.txt'], (self.root / 'packaging/licenses/Unicode.txt').read_bytes())
            self.assertEqual(files['samples/example.ru'], (self.root / 'packaging/samples/example.ru').read_bytes())
            self.assertEqual(archive.with_suffix('.zip.sha256').read_text(), f'{package.sha(archive)}  {archive.name}\n')
            if kind == 'runtime':
                self.assertFalse(set((*package.TEST_NAMES, *package.TEST_SUPPORT_DLL_NAMES)) & files.keys())
                self.assertFalse(any(name.endswith(('.log', '.cmd', '.ps1')) for name in files))
            else:
                self.assertTrue(set(package.BINARY_NAMES) <= files.keys())
                self.assertIn('run-tests.cmd', files)
                self.assertIn('native-test-evidence/native-acceptance.json', files)
                self.assertTrue({f'native-test-evidence/{name}' for name in
                                 package.required_evidence_names(self.summary)} <= files.keys())

    def test_only_allowlisted_synthetic_evidence_is_collected(self):
        tests = self.archives(self.create())[1]
        files = package.verify_archive(tests)
        self.assertFalse(any('private' in name or 'nested' in name for name in files))
        self.assertNotIn('PRIVATE_WORKSPACE', files['BUILD.json'].decode())
        self.assertNotIn('PRIVATE_SECRET', files['BUILD.json'].decode())
        self.assertNotIn(str(self.root), files['BUILD.json'].decode())

    def test_code_caches_and_unrelated_inputs_never_enter_either_zip(self):
        private_inputs = ('src/private-source.c', 'tests/private-fixture.ru',
                          'tools/__pycache__/private.pyc', '.tools/private-compiler.exe',
                          'build/private-generated.c', 'build/private.build.json')
        for relative in private_inputs:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('DO NOT DISTRIBUTE THIS SOURCE OR CACHE', encoding='utf-8')
        for archive in self.archives(self.create()):
            files = package.verify_archive(archive)
            self.assertFalse(set(private_inputs) & files.keys())
            self.assertFalse(any(name.startswith(('src/', 'tests/', 'tools/', 'build/', '.tools/'))
                                 or '__pycache__' in name or name.endswith(('.pyc', '.pyo'))
                                 for name in files))
            self.assertFalse(any(b'DO NOT DISTRIBUTE THIS SOURCE OR CACHE' in data for data in files.values()))

    def test_ru_gui_evidence_is_allowlisted_but_unrelated_gui_logs_are_not(self):
        (self.evidence / 'main-ru-syntax-launcher-0.log').write_text('synthetic Ru GUI receipt')
        (self.evidence / 'main-ru-syntax-launcher-private.log').write_text('DO NOT COLLECT')
        files = package.verify_archive(self.archives(self.create())[1])
        self.assertEqual(files['native-test-evidence/main-ru-syntax-launcher-0.log'], b'synthetic Ru GUI receipt')
        self.assertNotIn('native-test-evidence/main-ru-syntax-launcher-private.log', files)

    def test_missing_or_changed_unicode_notice_blocks_both_packages(self):
        notice = self.root / 'packaging/licenses/Unicode.txt'
        original = notice.read_bytes()
        notice.unlink()
        with self.assertRaisesRegex(RuntimeError, 'Missing'):
            self.create()
        self.assertFalse((self.root / 'dist').exists())
        notice.write_bytes(original + b'changed')
        with self.assertRaisesRegex(RuntimeError, 'Unicode data license'):
            self.create()
        self.assertFalse((self.root / 'dist').exists())

    def test_every_native_helper_dll_and_receipt_is_mandatory(self):
        for name in package.NATIVE_COMPILE_SOURCES:
            for filename in (name, Path(name).stem + '.native-build.json'):
                with self.subTest(filename=filename):
                    path = self.binary / filename
                    original = path.read_bytes()
                    path.unlink()
                    with self.assertRaisesRegex(RuntimeError, 'Missing'):
                        self.create()
                    self.assertFalse((self.root / 'dist').exists())
                    path.write_bytes(original)

    def test_native_helper_changed_dll_inputs_driver_or_receipt_blocks_packaging(self):
        cases = ('dll', 'table', 'header', 'driver', 'receipt-source', 'receipt-key', 'compiler-identity', 'flags')
        for case in cases:
            with self.subTest(case=case):
                name = package.NATIVE_HELPER_NAME
                receipt_path = self.binary / (Path(name).stem + '.native-build.json')
                path = {'dll': self.binary / name, 'table': self.root / 'native/ru_unicode_data.h',
                        'header': self.root / 'native/ru_scan.h', 'driver': self.root / 'tools/build.py'}.get(case, receipt_path)
                original = path.read_bytes()
                if case in ('dll', 'table', 'header', 'driver'):
                    path.write_bytes(original + b'changed')
                else:
                    receipt = json.loads(original)
                    if case == 'receipt-source': receipt['build_inputs']['source_sha256'].pop('native/ru_unicode_data.h')
                    if case == 'receipt-key': receipt['build_key'] = '0' * 64
                    if case == 'compiler-identity': receipt['build_inputs']['compiler_sha256'] = 'not a digest'
                    if case == 'flags': receipt['build_inputs']['compiler_flags'] = []
                    if case != 'receipt-key': receipt['build_key'] = package.native_build_key(receipt['build_inputs'])
                    package.save_json(path, receipt)
                with self.assertRaisesRegex(RuntimeError, 'Native helper'):
                    self.create()
                self.assertFalse((self.root / 'dist').exists())
                path.write_bytes(original)

    def test_every_executable_receipt_requires_matching_native_helper_and_source(self):
        for field in ('native_helper_sha256', 'native_helper_build_key', 'source_sha256'):
            with self.subTest(field=field):
                name = 'ru_notepad.exe'
                path = self.binary / Path(name).with_suffix('.build.json')
                original = path.read_bytes()
                if field == 'source_sha256':
                    self.modify_receipt(name, lambda receipt: receipt['source_sha256'].pop('native/ru_unicode_data.h'))
                else:
                    self.modify_receipt(name, lambda receipt: receipt.update({field: 'wrong'}))
                with self.assertRaisesRegex(RuntimeError, 'Native helper differs'):
                    self.create()
                path.write_bytes(original)

    def test_native_helper_dlls_allow_only_system_imports(self):
        for name in package.NATIVE_COMPILE_SOURCES:
            for imported in ('Lexilla.dll', 'Scintilla.dll', 'libgcc_s_seh-1.dll'):
                with self.subTest(name=name, imported=imported):
                    with patch.object(package.subprocess, 'check_output', return_value=f'DLL Name: {imported}'):
                        with self.assertRaisesRegex(RuntimeError, 'unpackaged non-system'):
                            package.inspect_pe(self.binary / name, 'fake-objdump')

    def test_native_build_receipts_and_sources_never_enter_archives(self):
        for archive in self.archives(self.create()):
            files = package.verify_archive(archive)
            self.assertFalse(any(name.endswith('.native-build.json') or name.startswith('native/') for name in files))
            self.assertNotIn('compiler_path', files['BUILD.json'].decode())
            self.assertNotIn('PRIVATE_WORKSPACE', files['BUILD.json'].decode())

    def test_missing_lexilla_blocks_both_packages(self):
        (self.binary / 'Lexilla.dll').unlink()
        with self.assertRaisesRegex(RuntimeError, 'Missing'):
            self.create()
        self.assertFalse((self.root / 'dist').exists())

    def test_every_executable_requires_common_manifest_build_receipt(self):
        for name in ('ru_notepad.exe', *package.TEST_NAMES):
            with self.subTest(name=name):
                path = self.binary / Path(name).with_suffix('.build.json')
                original = path.read_bytes()
                self.modify_receipt(name, lambda r: r['build_input_sha256'].pop('packaging/app.manifest'))
                with self.assertRaisesRegex(RuntimeError, 'common-controls manifest'):
                    self.create()
                path.write_bytes(original)

    def test_changed_manifest_invalidates_existing_executable_receipts(self):
        (self.root / 'packaging/app.manifest').write_text('changed manifest')
        with self.assertRaisesRegex(RuntimeError, 'Source changed since building'):
            self.create()

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

    def test_native_flags_and_hashes_cannot_bypass_required_results(self):
        self.summary['tests'] = []
        with self.assertRaisesRegex(RuntimeError, 'inventory'):
            self.create()
        self.assertFalse((self.root / 'dist').exists())

    def test_native_packaging_rejects_every_missing_mandatory_result(self):
        complete = list(self.summary['tests'])
        for result in complete:
            with self.subTest(name=result['name']):
                self.summary['tests'] = [case for case in complete if case['name'] != result['name']]
                with self.assertRaisesRegex(RuntimeError, 'inventory'):
                    self.create()
                self.assertFalse((self.root / 'dist').exists())

    def test_native_packaging_rechecks_ru_performance_and_gui_contracts(self):
        for mutation in ('missing-performance', 'unbounded-performance', 'missing-gui-style', 'wrong-gui-hash',
                         'missing-timer', 'wrong-timer-source', 'wrong-timer-probes', 'timer-timeout',
                         'missing-responsiveness', 'navigation-after-style', 'navigation-no-return',
                         'navigation-timeout', 'paint-not-cleared', 'paint-inconsistent-observation',
                         'missing-edit', 'wrong-edit-source', 'missing-edit-operation', 'edit-timeout',
                         'missing-observer', 'fast-observer', 'uncounted-observer', 'oversize-snapshot',
                         'missing-diagnostics', 'wrong-snapshot-generation', 'incomplete-final-snapshot',
                         'missing-snapshot-receipt', 'extended-diagnostic-capture'):
            with self.subTest(mutation=mutation):
                original = json.loads(json.dumps(self.summary))
                core = next(case for case in self.summary['tests'] if case['name'] == 'ru_syntax_native')
                gui = next(case for case in self.summary['tests'] if case['name'] == 'main-gui-ru-syntax')
                if mutation == 'missing-performance': core.pop('performance')
                if mutation == 'unbounded-performance': core['performance'][0]['edit_read_bytes'] = 65537
                if mutation == 'missing-gui-style': gui['automatic_ru_styles'] = False
                if mutation == 'wrong-gui-hash': gui['fixture_binary_sha256']['ru_notepad.exe'] = 'different'
                if mutation == 'missing-timer': gui.pop('timer_performance')
                if mutation == 'wrong-timer-source': gui['timer_performance']['source_sha256'] = 'different'
                if mutation == 'wrong-timer-probes': gui['timer_performance']['style_probes']['tail_keyword']['style'] = 0
                if mutation == 'timer-timeout': gui['timer_performance']['wall_ms'] = 30001
                if mutation == 'missing-observer': gui['timer_performance'].pop('observer')
                if mutation == 'fast-observer': gui['timer_performance']['observer']['response_interval_ms'] = 1
                if mutation == 'uncounted-observer': gui['timer_performance']['observer']['scalar_calls'] = 0
                if mutation == 'oversize-snapshot': gui['timer_performance']['observer']['snapshots'][0]['messages'] = 33
                if mutation == 'missing-diagnostics': gui['timer_performance'].pop('diagnostics')
                if mutation == 'wrong-snapshot-generation': gui['timer_performance']['diagnostics']['receipts'][2]['generation'] = 9
                if mutation == 'incomplete-final-snapshot': gui['timer_performance']['diagnostics']['receipts'][2]['pending'] = 1
                if mutation == 'missing-snapshot-receipt': gui['timer_performance']['diagnostics']['receipts'].pop()
                if mutation == 'extended-diagnostic-capture': gui['timer_performance']['diagnostics']['captures'][1]['wall_ms'] = 1001
                if mutation == 'missing-responsiveness': gui['timer_performance'].pop('responsiveness')
                if mutation == 'navigation-after-style': gui['timer_performance']['responsiveness']['navigation'][0]['while_styling'] = False
                if mutation == 'navigation-no-return': gui['timer_performance']['responsiveness']['navigation'][1]['after'] = 3
                if mutation == 'navigation-timeout': gui['timer_performance']['responsiveness']['navigation'][0]['wall_ms'] = 5001
                if mutation == 'paint-not-cleared': gui['timer_performance']['responsiveness']['paint']['cleared'] = False
                if mutation == 'paint-inconsistent-observation': gui['timer_performance']['responsiveness']['paint']['already_serviced'] = True
                if mutation == 'missing-edit': gui.pop('edit_performance')
                if mutation == 'wrong-edit-source': gui['edit_performance']['source_sha256'] = 'different'
                if mutation == 'missing-edit-operation': gui['edit_performance']['operations'].pop()
                if mutation == 'edit-timeout': gui['edit_performance']['operations'][0]['wall_ms'] = 30001
                with self.assertRaises(RuntimeError):
                    self.create()
                self.assertFalse((self.root / 'dist').exists())
                self.summary = original

    def test_native_packaging_rechecks_same_source_sync_and_production_timer_measurements(self):
        for name, key in (('ru_syntax_native', 'gui_sync_performance'),
                          ('app_ru_timer_native', 'timer_performance')):
            for mutation in ('missing', 'source', 'characters', 'incomplete', 'unbounded', 'nonfinite',
                             'extra-field', 'timer-pending', 'timer-timeout', 'timer-style', 'timer-fold',
                             'timer-no-posts', 'timer-no-continuations', 'timer-inconsistent-continuations',
                             'timer-negative-yields', 'timer-negative-stale'):
                if mutation.startswith('timer-') and name != 'app_ru_timer_native':
                    continue
                with self.subTest(name=name, mutation=mutation):
                    original = json.loads(json.dumps(self.summary))
                    result = next(case for case in self.summary['tests'] if case['name'] == name)
                    record = result[key]
                    if mutation == 'missing': result.pop(key)
                    if mutation == 'source': record['source_sha256'] = 'different'
                    if mutation == 'characters': record['source_chars'] = 1000000
                    if mutation == 'incomplete': record['read_bytes'] = 999999
                    if mutation == 'unbounded': record['max_read'] = 1025
                    if mutation == 'nonfinite': record['wall_ms'] = float('nan')
                    if mutation == 'extra-field': record['unexpected'] = 1
                    if mutation == 'timer-pending': record['pending'] = 1
                    if mutation == 'timer-timeout': record['wall_ms'] = 30001
                    if mutation == 'timer-style': record['style_notifications'] = 1
                    if mutation == 'timer-fold': record['fold_notifications'] = 1
                    if mutation == 'timer-no-posts': record['posts'] = 0
                    if mutation == 'timer-no-continuations': record['continuation_ticks'] = 0
                    if mutation == 'timer-inconsistent-continuations': record['continuation_ticks'] = record['ticks'] + 1
                    if mutation == 'timer-negative-yields': record['queue_yields'] = -1
                    if mutation == 'timer-negative-stale': record['stale_messages'] = -1
                    with self.assertRaises(RuntimeError): self.create()
                    self.assertFalse((self.root / 'dist').exists())
                    self.summary = original

    def test_native_packaging_rejects_cleanup_kill_even_with_true_flags(self):
        self.summary['tests'][0]['cleanup_killed'] = True
        with self.assertRaisesRegex(RuntimeError, 'did not pass normally'):
            self.create()

    def test_native_packaging_requires_exact_dll_scanner_preflight_and_unchanged_test_script(self):
        for mutation in ('missing', 'wrong-dll', 'changed-script'):
            with self.subTest(mutation=mutation):
                original = json.loads(json.dumps(self.summary))
                script = self.root / 'tools/test_ru_scan.py'
                original_script = script.read_bytes()
                if mutation == 'missing': self.summary.pop('scanner_preflight')
                if mutation == 'wrong-dll': self.summary['scanner_preflight']['report']['library_sha256'] = 'different'
                if mutation == 'changed-script': script.write_bytes(b'changed test script')
                with self.assertRaisesRegex(RuntimeError, 'scanner preflight'):
                    self.create()
                self.assertFalse((self.root / 'dist').exists())
                self.summary = original
                script.write_bytes(original_script)

    def test_all_test_executables_and_receipts_are_required(self):
        for name in package.TEST_NAMES:
            with self.subTest(name=name):
                path = self.binary / name
                original = path.read_bytes()
                path.unlink()
                with self.assertRaisesRegex(RuntimeError, 'Missing'):
                    self.create()
                path.write_bytes(original)
                receipt = path.with_suffix('.build.json')
                original = receipt.read_bytes()
                receipt.unlink()
                with self.assertRaisesRegex(RuntimeError, 'Missing'):
                    self.create()
                receipt.write_bytes(original)

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

    def test_every_required_native_output_must_exist_and_be_allowlisted(self):
        for name in package.required_evidence_names(self.summary):
            with self.subTest(name=name):
                path = self.evidence / name
                original = path.read_bytes()
                path.unlink()
                with self.assertRaisesRegex(RuntimeError, 'Missing'):
                    self.create()
                self.assertFalse((self.root / 'dist').exists())
                path.write_bytes(original)
        allowed = package.evidence_names([test['name'] for test in self.summary['tests']
                                          if test['name'] not in ci.GUI_NAMES])
        for name in package.required_evidence_names(self.summary):
            with self.subTest(allowlist_omits=name):
                with self.assertRaisesRegex(RuntimeError, 'allowlist omits'):
                    package.validate_native_evidence(self.evidence, self.summary, allowed - {name})

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
