#!/usr/bin/env python3
"""Portable hostile-evidence controls, never real-Windows execution evidence."""
import ast
import copy
from contextlib import nullcontext
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_focused_native_diagnostic as runner


def metrics():
    return [dict(route='fallback', bulkCalls=0, bulkLines=0, fallbackBatches=1, directCalls=0,
                 directLines=0, maxPlanBytes=0, ownedBufferBytes=0, bulkUs=0, metric_valid=1),
            dict(route='bulk', bulkCalls=1, bulkLines=1, fallbackBatches=0, directCalls=0,
                 directLines=0, maxPlanBytes=48, ownedBufferBytes=1088, bulkUs=1, metric_valid=1),
            dict(route='perline', bulkCalls=0, bulkLines=0, fallbackBatches=0, directCalls=1,
                 directLines=1, maxPlanBytes=0, ownedBufferBytes=0, bulkUs=0, metric_valid=1)]


def streams(index):
    text = 'PASS: synthetic\n' * runner.COUNTS[index]
    if index == 1:
        text, passed = '', 0
        for stage, language, width, next_assertion in runner.I18N_STAGE_SEQUENCE:
            text += 'PASS: synthetic\n' * (next_assertion - 1 - passed)
            passed = next_assertion - 1
            text += f'I18N_STAGE stage={stage} language={language} width={width} next={next_assertion}\n'
        text += 'PASS: synthetic\n' * (runner.COUNTS[index] - passed)
    if index == 0:
        for row in metrics():
            text += 'FOLD_METRICS1 route=' + row['route'] + ''.join(' ' + key + '=' + str(row[key])
                for key in runner.ci.FOLD_ROUTE_METRIC_FIELDS) + '\n'
    return text + 'TOTAL PASS: ' + str(runner.COUNTS[index]) + '\n', (
        'RU_GC live=0 freed=100 collections=4\n' if index == 0 else '')


def result(index):
    value = dict(name=runner.TESTS[index], passed=True, executed=True, cleanup_killed=False,
                 exit_code=0, skips=[], assertions_passed=runner.COUNTS[index])
    if index == 0:
        value.update(gc_stress=dict(threshold=64, stats_enabled=True, live=0, freed=100, collections=4),
                     bulk_route_metrics=metrics())
    return value


def report():
    value = dict(schema=1, diagnostic_only=1, product_acceptance=0, windows_executed=1,
        source_commit='a' * 40, source_tree='b' * 40, source_sha256='c' * 64,
        compiler=dict(commit=runner.RU_COMMIT, tree=runner.RU_TREE, native_c_sha256='a' * 64,
                      cc_sha256='b' * 64, cc_version_sha256='c' * 64, analysis_limit=200000),
        archives={spec.id: spec.sha256 for spec in runner.archives.ARCHIVES},
        runtime={key: 'd' * 64 for key in ('scintilla', 'lexilla', 'helper', 'wrong_abi', 'helper_build_key', 'wrong_abi_build_key')}, tests=[])
    for i in range(2):
        row = dict(id=i + 1, assertions=runner.COUNTS[i], exit_code=0, executed=1, cleanup_killed=0,
            exe_bytes=128, generated_c_bytes=256, translation_unit_bytes=256)
        row.update({key: 'e' * 64 for key in ('entry_sha256', 'generated_c_sha256',
                   'translation_unit_sha256', 'exe_sha256', 'receipt_sha256')})
        if i == 0:
            row.update(gc=result(0)['gc_stress'] | {'stats_enabled': 1},
                       routes=[m | {'route': j} for j, m in enumerate(metrics())])
        value['tests'].append(row)
    return value


class RuntimeControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.logs = Path(self.temp.name)
        for i, name in enumerate(runner.TESTS):
            out, err = streams(i)
            (self.logs / (name + '.stdout.log')).write_text(out, encoding='utf-8')
            (self.logs / (name + '.stderr.log')).write_text(err, encoding='utf-8')

    def test_complete_original_counts_and_parsers(self):
        for i, name in enumerate(runner.TESTS):
            row = runner.validated_result(name, result(i), self.logs)
            self.assertEqual(row['assertions'], runner.COUNTS[i])
        self.assertEqual(runner.ci.MARKDOWN_DIRECT_GC_ENV, {'RU_GC_THRESHOLD': '64', 'RU_GC_STATS': '1'})
        # Preserve stable control IDs/count while testing both native line endings.
        name = runner.TESTS[1]
        for ending in ('\n', '\r\n'):
            out, err = streams(1)
            (self.logs / (name + '.stdout.log')).write_bytes(out.replace('\n', ending).encode('utf-8'))
            runner.validated_result(name, result(1), self.logs)
        for mutation in (
                lambda text: text.replace('I18N_STAGE stage=0 language=7 width=0 next=1\n', ''),
                lambda text: text.replace('stage=5 language=4 width=0 next=909', 'stage=5 language=4 width=0 next=908'),
                lambda text: text + 'I18N_STAGE private/path\n'):
            (self.logs / (name + '.stdout.log')).write_bytes(mutation(streams(1)[0]).encode('utf-8'))
            with self.assertRaises(ValueError):
                runner.validated_result(name, result(1), self.logs)

    def test_wrong_counts_totals_fail_skip_and_stderr(self):
        for i, name in enumerate(runner.TESTS):
            original, err = streams(i)
            for out, stderr in (
                (original.replace('PASS: synthetic\n', '', 1), err),
                (original + 'PASS: extra\n', err), (original + 'TOTAL PASS: 1\n', err),
                (original.replace('TOTAL PASS: ' + str(runner.COUNTS[i]), 'TOTAL PASS: 1'), err),
                (original + 'FAIL: private/path\n', err), (original + 'SKIP: private/path\n', err),
                (original, err + 'C:\\private\\source.ru: failure\n')):
                with self.subTest(name=name, out=out[-60:], stderr=stderr):
                    (self.logs / (name + '.stdout.log')).write_text(out, encoding='utf-8')
                    (self.logs / (name + '.stderr.log')).write_text(stderr, encoding='utf-8')
                    with self.assertRaises((ValueError, RuntimeError)):
                        runner.validated_result(name, result(i), self.logs)

    def test_missing_oversize_and_invalid_utf8_logs(self):
        name = runner.TESTS[1]
        path = self.logs / (name + '.stdout.log')
        path.unlink()
        with self.assertRaises(RuntimeError): runner.validated_result(name, result(1), self.logs)
        path.write_bytes(b'x' * (runner.ci.MAX_LOG_BYTES + 1))
        with self.assertRaises(ValueError): runner.validated_result(name, result(1), self.logs)
        path.write_bytes(b'\xff')
        with self.assertRaises(UnicodeError): runner.validated_result(name, result(1), self.logs)

    def test_timeout_exit_cleanup_unexecuted_and_receipt_counts(self):
        for mutation in (dict(passed=False, error='private timeout'), dict(exit_code=1),
                         dict(exit_code=True), dict(cleanup_killed=True), dict(executed=False),
                         dict(assertions_passed=1416), dict(skips=['private path']), dict(name='other')):
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                runner.validated_result(runner.TESTS[1], result(1) | mutation, self.logs)

    def test_gc_and_routes_must_be_current_real_logs(self):
        name = runner.TESTS[0]
        for stderr in ('', 'RU_GC live=0 freed=0 collections=4\n', 'RU_GC live=0 freed=100 collections=1\n',
                       streams(0)[1] * 2, 'RU_GC live=private freed=100 collections=4\n'):
            (self.logs / (name + '.stderr.log')).write_text(stderr)
            with self.assertRaises(RuntimeError): runner.validated_result(name, result(0), self.logs)
        (self.logs / (name + '.stderr.log')).write_text(streams(0)[1])
        for text in (streams(0)[0].replace('metric_valid=1', 'metric_valid=0', 1),
                     streams(0)[0].replace('FOLD_METRICS1 route=bulk', 'FOLD_METRICS1 route=fallback'),
                     'PASS: synthetic\n' * 114 + 'TOTAL PASS: 114\n'):
            (self.logs / (name + '.stdout.log')).write_text(text)
            with self.assertRaises(RuntimeError): runner.validated_result(name, result(0), self.logs)

    def test_actual_console_child_gc_environment_exit_and_timeout(self):
        class API:
            def no_dialog(self, pid): pass
        for mode in ('ok', 'exit', 'timeout'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                out, err = streams(0)
                code = 'import os,sys,time; assert os.environ["RU_GC_THRESHOLD"]=="64"; assert os.environ["RU_GC_STATS"]=="1"; '
                code += 'time.sleep(2)' if mode == 'timeout' else ('sys.stdout.write(' + repr(out) + '); sys.stderr.write(' + repr(err) + '); sys.exit(' + ('1' if mode == 'exit' else '0') + ')')
                def host_cleanup(process):
                    if process.poll() is not None: return False
                    process.kill(); process.wait(timeout=5); return True
                # Only adapt process-tree cleanup on POSIX. Windows exercises the
                # unchanged production taskkill path, including its timeout.
                cleanup = nullcontext() if os.name == 'nt' else patch.object(runner.ci, 'cleanup_process', side_effect=host_cleanup)
                with cleanup:
                    row = runner.ci.run_console(API(), runner.TESTS[0], [sys.executable, '-I', '-c', code],
                        Path(directory), dict(runner.ci.NATIVE_CONSOLE_TESTS)[runner.TESTS[0]],
                        expected_assertions=114, timeout=0.05 if mode == 'timeout' else 5)
                if mode == 'ok':
                    runner.validated_result(runner.TESTS[0], row, Path(directory))
                else:
                    with self.assertRaises(ValueError):
                        runner.validated_result(runner.TESTS[0], row, Path(directory))
                if mode == 'timeout': self.assertTrue(row['cleanup_killed'])


class ReceiptControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.binary = self.root / 'private/bin'; self.binary.mkdir(parents=True)
        self.cc = self.root / 'gcc.exe'; self.cc.write_bytes(b'synthetic compiler')
        paths = {*runner.DRIVERS, *runner.package.RESOURCE_INPUTS, 'tools/generate_i18n.py',
                 'src/main.ru', 'locales/test.json', *(f'tests/{n}.ru' for n in runner.TESTS),
                 *(p for files in runner.package.NATIVE_COMPILE_SOURCES.values() for p in files)}
        for relative in paths:
            path = self.root / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b'synthetic input')
        self.addCleanup(patch.stopall)
        patch.object(runner, 'ROOT', self.root).start()
        patch.object(runner.build, 'ROOT', self.root).start()
        # Only external tool output is synthetic. PE parsing, hashes, sources,
        # receipt schemas and helper validator run unchanged against real files.
        def tool(command, **kwargs):
            if '--version' in command: return b'synthetic version'
            return 'DLL Name: KERNEL32.dll\n'
        patch.object(runner.subprocess, 'check_output', side_effect=tool).start()
        self.compiler = dict(commit=runner.RU_COMMIT, tree=runner.RU_TREE, native_c_sha256='a' * 64,
            cc_sha256=runner.sha(self.cc), cc_version_sha256=hashlib.sha256(b'synthetic version').hexdigest(), analysis_limit=200000)
        for name in (*(n + '.exe' for n in runner.TESTS), *runner.package.DEPENDENCIES, *runner.package.NATIVE_COMPILE_SOURCES):
            data = bytearray(128); data[:2] = b'MZ'; struct.pack_into('<I', data, 60, 64)
            data[64:68] = b'PE\0\0'; struct.pack_into('<H', data, 68, 0x8664)
            (self.binary / name).write_bytes(data + name.encode())
        for name in runner.package.NATIVE_COMPILE_SOURCES:
            inputs = runner.build.native_build_inputs(str(self.cc), name)
            receipt = dict(schema=1, name=name, build_inputs=inputs, build_key=runner.package.native_build_key(inputs),
                dll_sha256=runner.sha(self.binary / name), compiler_command=[inputs['compiler_path'], *runner.package.NATIVE_CFLAGS,
                    *runner.package.NATIVE_COMPILE_SOURCES[name], '-o', str(self.root / 'build/native-helper' / (Path(name).stem + '.pending.dll')),
                    *('-l' + lib for lib in runner.package.NATIVE_LINK_LIBRARIES)])
            (self.binary / (Path(name).stem + '.native-build.json')).write_bytes(runner.canonical(receipt))
        helper = runner.json_read(self.binary / 'RuSyntax.native-build.json')
        for name in runner.TESTS:
            emitted = self.root / 'build' / (name + '.c'); emitted.parent.mkdir(exist_ok=True); emitted.write_bytes(b'generated C ' + name.encode())
            r = dict(schema=1, utc='2026-10-20T00:00:00Z', ru_commit=runner.RU_COMMIT, ru_tree=runner.RU_TREE,
                app_version='synthetic input', entry_source='tests/' + name + '.ru',
                entry_sha256=runner.sha(self.root / 'tests' / (name + '.ru')), source_sha256=runner.build.source_snapshot(),
                build_input_sha256={p: runner.sha(self.root / p) for p in runner.build.build_input_paths(True)},
                translation_unit_sha256=runner.sha(emitted), translation_unit_bytes=emitted.stat().st_size,
                generated_c_sha256=runner.sha(emitted), generated_c_bytes=emitted.stat().st_size,
                exe_sha256=runner.sha(self.binary / (name + '.exe')), exe_bytes=(self.binary / (name + '.exe')).stat().st_size,
                native_helper_sha256=helper['dll_sha256'], native_helper_build_key=helper['build_key'],
                seconds=1.0, runtime_tested=False, compiler_command=[str(self.cc), '-std=c99', '-O2', '-Wall', '-Wextra',
                    '-Wno-unused-function', '-static-libgcc', str(emitted), '-o', str(self.binary / (name + '.exe')),
                    '-lm', str(self.root / 'build/app-resource.o')])
            for dll, dependency in runner.package.DEPENDENCIES.items():
                r['dll_sha256' if dll == 'Scintilla.dll' else 'lexilla_dll_sha256'] = runner.sha(self.binary / dll)
                r[dependency['folder'] + '_version'] = dependency['version']
                r[dependency['folder'] + '_archive_sha256'] = dependency['sha256']
            (self.binary / (name + '.build.json')).write_bytes(runner.canonical(r))
        self.before = runner.source_snapshot()

    def verify(self):
        return runner.verify_receipts(self.binary, 'objdump', self.cc, self.compiler, self.before)

    def test_complete_source_bound_two_fixture_inventory(self):
        receipts, binaries, helpers = self.verify()
        self.assertEqual(len(receipts), 2); self.assertEqual(len(binaries), 6); self.assertEqual(len(helpers), 2)
        self.assertFalse((self.binary / 'ru_notepad.exe').exists())

    def test_receipt_fields_cannot_be_changed_or_omitted(self):
        path = self.binary / (runner.TESTS[0] + '.build.json'); original = runner.json_read(path)
        for key in original:
            for operation in ('remove', 'alter'):
                if key in ('utc', 'seconds') and operation == 'alter': continue
                changed = copy.deepcopy(original)
                if operation == 'remove': changed.pop(key)
                else: changed[key] = 'C:\\private\\forged'
                path.write_bytes(runner.canonical(changed))
                with self.subTest(key=key, operation=operation), self.assertRaises((ValueError, RuntimeError, TypeError, KeyError)):
                    self.verify()
        path.write_bytes(runner.canonical(original)); self.verify()

    def test_changed_source_generated_c_pe_compiler_and_helper_rejected(self):
        targets = [self.root / 'src/main.ru', self.root / 'tests' / (runner.TESTS[1] + '.ru'),
            self.root / 'packaging/app.manifest', self.root / 'native/ru_scan.c',
            self.root / 'build' / (runner.TESTS[0] + '.c'), self.binary / (runner.TESTS[0] + '.exe'),
            self.binary / 'Lexilla.dll', self.binary / 'RuSyntax.dll', self.cc]
        for path in targets:
            original = path.read_bytes(); path.write_bytes(original + b'changed')
            with self.subTest(path=path.name), self.assertRaises((ValueError, RuntimeError)):
                self.verify()
            path.write_bytes(original)

    def test_missing_receipt_and_added_exe_rejected(self):
        path = self.binary / (runner.TESTS[1] + '.build.json'); original = path.read_bytes(); path.unlink()
        with self.assertRaises(RuntimeError): self.verify()
        path.write_bytes(original)
        (self.binary / 'unexpected.exe').write_bytes(b'MZ')
        with self.assertRaises(ValueError): self.verify()

    def test_helper_actual_command_and_compiler_binding(self):
        path = self.binary / 'RuSyntax.native-build.json'; original = runner.json_read(path)
        for mutation in (dict(schema=2), dict(compiler_command=['private/other-compiler'])):
            path.write_bytes(runner.canonical(original | mutation))
            with self.assertRaises(ValueError): self.verify()
        altered = copy.deepcopy(original); altered['build_inputs']['compiler_path'] = 'other/compiler'
        altered['build_key'] = runner.package.native_build_key(altered['build_inputs'])
        path.write_bytes(runner.canonical(altered))
        with self.assertRaises(ValueError): self.verify()


class PublicationControls(unittest.TestCase):
    def test_literal_numeric_hash_only_tree(self):
        value = report(); runner.validate_report(value)
        def visit(node):
            if isinstance(node, dict):
                for item in node.values(): visit(item)
            elif isinstance(node, list):
                for item in node: visit(item)
            elif type(node) is str: self.assertRegex(node, r'^(?:[a-f0-9]{40}|[a-f0-9]{64})$')
            else: self.assertIs(type(node), int)
        visit(value)

    def test_arbitrary_fields_paths_wrong_counts_gc_and_types_rejected(self):
        for mutate in (
            lambda d: d.update(path='C:\\private'), lambda d: d['compiler'].update(command=['private']),
            lambda d: d['tests'][0].update(stdout='private'), lambda d: d['tests'][1].update(assertions=1416),
            lambda d: d['tests'][0].update(assertions=115), lambda d: d.update(product_acceptance=1),
            lambda d: d['compiler'].update(analysis_limit=400000), lambda d: d['compiler'].update(commit='a' * 40),
            lambda d: d['tests'][0]['gc'].update(collections=1), lambda d: d['tests'][0]['gc'].update(stats_enabled=True),
            lambda d: d['tests'][0]['routes'][0].update(route='fallback'), lambda d: d['runtime'].update(helper='private'),
            lambda d: d['tests'][1].update(exe_bytes=float('nan')), lambda d: d['tests'][1].update(executed=True),
            lambda d: d['tests'][1].update(translation_unit_sha256='f' * 64), lambda d: d['tests'].reverse()):
            value = report(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises((ValueError, RuntimeError)):
                runner.validate_report(value)

    def test_validated_atomic_noreplace_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); private = root / 'private'; private.mkdir(); public = root / 'public'
            runner.publish_report(private, public, report())
            self.assertEqual([p.name for p in public.iterdir()], ['measurements.json'])
            self.assertEqual(json.loads((public / 'measurements.json').read_bytes()), report())
            with self.assertRaises(ValueError): runner.publish_report(private, public, report())

    def test_public_path_directory_links_and_race_rejected(self):
        for kind in ('existing', 'public_link', 'private_link', 'parent_link', 'race'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); private = root / 'private'; private.mkdir(); public = root / 'public'
                if kind == 'existing': public.mkdir()
                if kind.endswith('link'):
                    other = root / 'other'; other.mkdir()
                    try:
                        if kind == 'public_link': public.symlink_to(other, target_is_directory=True)
                        elif kind == 'private_link': private.rmdir(); private.symlink_to(other, target_is_directory=True)
                        else:
                            link = root / 'link'; link.symlink_to(root, target_is_directory=True)
                            private, public = link / 'private', link / 'public'
                    except OSError: continue  # Windows may lack symlink privilege.
                real_link = runner.os.link
                def race(src, dst): dst.write_bytes(b'sentinel'); real_link(src, dst)
                with patch.object(runner.os, 'link', side_effect=race if kind == 'race' else real_link):
                    with self.assertRaises((ValueError, FileExistsError)):
                        runner.publish_report(private, public, report())
                if kind == 'race': self.assertEqual((public / 'measurements.json').read_bytes(), b'sentinel')
                else: self.assertFalse((public / 'measurements.json').exists())

    def test_write_fsync_and_link_failures_do_not_publish(self):
        for operation in ('fsync', 'link'):
            with self.subTest(operation=operation), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); private = root / 'private'; private.mkdir(); public = root / 'public'
                with patch.object(runner.os, operation, side_effect=OSError('private failure')):
                    with self.assertRaises(OSError): runner.publish_report(private, public, report())
                self.assertFalse((public / 'measurements.json').exists())

    def test_actual_cli_failure_is_numeric_and_private(self):
        with tempfile.TemporaryDirectory(prefix='private-path-') as tmp:
            event = Path(tmp) / 'event.json'; event.write_text('{}')
            env = dict(os.environ, GITHUB_EVENT_PATH=str(event), GITHUB_REF='refs/heads/wip', GITHUB_EVENT_NAME='push')
            result = subprocess.run([sys.executable, '-I', str(Path(runner.__file__)), '--private-invalid-argument'],
                                    env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.stdout, '')
            self.assertEqual(result.stderr, 'FOCUSED_NATIVE_DIAGNOSTIC code=1 markdown=0 i18n=0\n')
            self.assertEqual(result.returncode, 1)

    def test_actual_product_build_entry_accepts_current_parameters(self):
        command = [sys.executable, str(Path(runner.__file__).with_name('build.py')), '--help']
        result = subprocess.run(command, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--skip-scintilla', result.stdout)
        self.assertIn('--skip-lexilla', result.stdout)
        actual = runner.build_command(Path('ru'), Path('bin'), runner.TESTS[0], Path('output.exe'))
        self.assertNotIn('-I', actual[:3])

    def test_source_build_and_gc_contracts_are_reused(self):
        command = runner.build_command(Path('ru'), Path('mingw/bin'), runner.TESTS[0], Path('output.exe'))
        for flag in ('--cc', '--cxx', '--windres', '--ar', '--ranlib', '--skip-scintilla', '--skip-lexilla', '--console'):
            self.assertIn(flag, command)
        source = Path(runner.__file__).read_text(encoding='utf-8')
        self.assertIn('ci.run_native_console(', source)
        self.assertIn('ci.parse_markdown_direct_gc(', source)
        self.assertIn('ci.parse_markdown_route_metrics(', source)
        self.assertIn("prefix='七语-原生-診断-'", source)
        tree = ast.parse(source)
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                 and n.func.id == 'run' and n.args and isinstance(n.args[0], ast.Constant) and n.args[0].value == 'lexilla']
        constants = [n.value for n in ast.walk(calls[0]) if isinstance(n, ast.Constant)]
        self.assertEqual(constants.count('windir=C:/Windows'), 1)
        self.assertNotIn('create_packages(', source)


if __name__ == '__main__':
    unittest.main()
