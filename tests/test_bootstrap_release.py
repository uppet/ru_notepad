import json
import re
from pathlib import Path
import shutil
import subprocess
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import build_bootstrap_release as b
import prepare_bootstrap_dependencies as dependencies
from bootstrap_provenance import InvalidProvenance


def link_trace(args):
    def quote(arg):
        return '"'+''.join(('\\'+c if c in ('"','\\','$') else c) for c in arg)+'"'
    return ('clang version 14.0.6\nTarget: x86_64-pc-windows-msvc\nThread model: posix\nInstalledDir: fixture\n '+
            ' '.join(quote(arg) for arg in args)+'\r\n').encode('utf-8')


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.files = {key: self.root/key for key in ('source', 'compiler', 'ir', 'binary', 'host')}
        for key, path in self.files.items():
            path.write_text(key)
        self.frozen = {str(path): b.sha(path) for path in self.files.values()}
        self.proof = {'schema': 'ru-bootstrap-build-proof-v1', 'native_protocol': 'bootstrap-native-v1',
            'source': str(self.files['source']), 'compiler': b.identity(self.files['compiler']),
            'target_triple': 'triple', 'data_layout': 'layout',
            'source_inventory': [b.identity(self.files['source'])],
            'dependencies': [b.identity(self.files['source'])], 'host_inputs': [b.identity(self.files['host'])],
            'artifacts': {k: {'path': str(self.files[n]), 'sha256': b.sha(self.files[n])}
                          for k, n in [('standalone_ir', 'ir'), ('binary', 'binary')]},
            'standalone_ir_sha256': b.sha(self.files['ir']), 'binary_sha256': b.sha(self.files['binary'])}

    def verify(self):
        return b.verify_proof(self.proof, **{k: self.files[k] for k in ('source','compiler','ir','binary')},
                              triple='triple', layout='layout', frozen=self.frozen)

    def test_fixture_normalizes_short_temp_alias_before_use(self):
        # Portable model of Windows RUNNER~1: no symlink privileges required.
        canonical = self.root / 'long-temporary-path'
        canonical.mkdir()
        class ShortAlias:
            def resolve(alias_self):
                return canonical
            def __truediv__(alias_self, child):
                raise AssertionError('short alias used before canonicalization')
        original = Path
        alias = 'RUNNER~1/temporary'
        def paths(value):
            return ShortAlias() if value == alias else original(value)
        fixture = ReleaseTests(methodName='runTest')
        temporary = SimpleNamespace(name=alias, cleanup=lambda: None)
        try:
            with patch.object(tempfile, 'TemporaryDirectory', return_value=temporary), \
                    patch.object(sys.modules[__name__], 'Path', side_effect=paths):
                fixture.setUp()
            self.assertEqual(fixture.root, canonical)
            self.assertEqual(fixture.root, fixture.root.resolve())
        finally:
            fixture.doCleanups()

    def test_proof_valid_fixture(self):
        self.verify()

    def test_dependency_make_environment_rejects_ambient_flags(self):
        tools = {'cc': str(self.root/'gcc.exe')}
        good = dependencies.dependency_environment(tools, {'PATH': 'old', 'CC': 'gcc', 'VPATH': 'foreign'})
        self.assertEqual(good['CC'], 'gcc.exe')
        self.assertNotIn('VPATH', good)
        for name in dependencies.INJECTION_ENV:
            with self.subTest(name=name):
                self.assertRaises(InvalidProvenance, dependencies.dependency_environment,
                                  tools, {name: 'injected'})

    def test_dependency_tool_names_cannot_inject_make_shell(self):
        for name in ('bad name.exe', 'bad&name.exe', 'bad"name.exe', '-option.exe'):
            with self.subTest(name=name):
                paths = {key: str(self.root/name) for key in dependencies.TOOL_NAMES}
                self.assertRaises(InvalidProvenance, dependencies.validate_tools,
                                  paths, {key: '0'*64 for key in paths})

    def test_legacy_python_proof_rejected(self):
        del self.proof['native_protocol']
        self.assertRaises(InvalidProvenance, self.verify)

    def test_ir_tamper_rejected(self):
        self.files['ir'].write_text('other frontend')
        self.assertRaises(InvalidProvenance, self.verify)

    def test_stale_console_proof_rejected(self):
        self.files['binary'].write_text('old exe')
        self.assertRaises(InvalidProvenance, self.verify)

    def test_compiler_changed_even_if_proof_updated(self):
        # The outer bootstrap identity gate freezes the stage3 hash; host_inputs
        # must also stay within that frozen source/compiler inventory.
        self.proof['host_inputs'].append(b.identity(self.files['compiler']))
        self.files['compiler'].write_text('different compiler')
        self.proof['compiler'] = b.identity(self.files['compiler'])
        self.proof['host_inputs'][-1] = b.identity(self.files['compiler'])
        self.assertRaises(InvalidProvenance, self.verify)

    def test_dependency_outside_inventory(self):
        self.proof['dependencies'].append(b.identity(self.files['host']))
        self.assertRaises(InvalidProvenance, self.verify)

    def test_source_changed_even_if_proof_updated(self):
        self.files['source'].write_text('different source')
        self.proof['source_inventory'] = [b.identity(self.files['source'])]
        self.proof['dependencies'] = [b.identity(self.files['source'])]
        self.assertRaises(InvalidProvenance, self.verify)

    def test_wrong_target(self):
        self.proof['data_layout'] = 'wrong'
        self.assertRaises(InvalidProvenance, self.verify)

    def test_actual_host_toolchain_must_match_locked_paths(self):
        tools = {name: '/locked/'+name for name in ('clang','llvm-as','llvm-link','opt','llvm-dis','llc','linker')}
        tools['linker'] = str(self.files['host'])
        args = {k: self.files[k] for k in ('source','compiler','ir','binary')}
        args.update(triple='triple', layout='layout', frozen=self.frozen, tools=tools)
        self.proof['toolchain'] = {'clang': [tools['clang']],
            'tools': {k: tools[k] for k in ('llvm-as','llvm-link','opt','llvm-dis','llc')},
            'link_flags': b.explicit_linker_flags(b.identity(tools['linker']))}
        self.proof['linker'] = b.identity(tools['linker'])
        triple = 'x86_64-pc-windows-msvc'
        args['triple'] = self.proof['target_triple'] = triple
        command = [tools['clang'], str(self.root/'p.obj'), '-o', str(self.root/'p.exe'), *b.explicit_linker_flags(self.proof['linker'])]
        with patch.object(b.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout=b'', stderr=link_trace([tools['linker'], '-out:p.exe']))):
            self.proof['linker_selection'] = b.inspect_linker_command(command, self.proof['linker'], {}, str(self.root))
        b.verify_proof(self.proof, **args)
        self.proof['toolchain']['tools']['llc'] = '/PATH/other-llc'
        self.assertRaises(InvalidProvenance, b.verify_proof, self.proof, **args)

    def test_implicit_linker_refused(self):
        tools = {name: '/locked/'+name for name in ('clang','llvm-as','llvm-link','opt','llvm-dis','llc','linker')}
        self.proof['toolchain'] = {'clang': [tools['clang']],
            'tools': {k: tools[k] for k in ('llvm-as','llvm-link','opt','llvm-dis','llc')}, 'link_flags': []}
        args = {k: self.files[k] for k in ('source','compiler','ir','binary')}
        args.update(triple='triple', layout='layout', frozen=self.frozen, tools=tools)
        self.assertRaises(InvalidProvenance, b.verify_proof, self.proof, **args)

    def test_link_plan_uses_proven_ir_and_gui_crt(self):
        tools = {k: '/tools/'+k for k in ('llc', 'clang', 'resource-compiler', 'linker')}
        commands = b.link_commands(tools, self.files['ir'], Path('/fixed/wrapper.c'), Path('/app'), self.root, 'x86_64-pc-windows-msvc')
        self.assertIn(str(self.files['ir']), commands[0])
        self.assertIn('/ENTRY:wWinMainCRTStartup', commands[-1])
        self.assertIn('/SUBSYSTEM:WINDOWS', commands[-1])
        self.assertIn(str(self.root/'application.res'), commands[-1])
        self.assertNotIn(str(self.files['binary']), commands[-1])

    def test_nonwindows_refuses_before_build(self):
        if sys.platform == 'win32':
            return
        self.assertRaises(InvalidProvenance, b.build, {}, self.root/'staging')
        self.assertFalse((self.root/'staging').exists())

    def test_macro_bridge_calls_original_main_not_itself(self):
        cc = shutil.which('cc')
        if not cc:
            self.fail('C preprocessor required for bridge test')
        source = Path(__file__).resolve().parents[1]/'packaging/bootstrap_gui_launcher.c'
        wrapper = self.root/'bootstrap_gui_launcher.c'
        shutil.copyfile(source, wrapper)
        # Quote includes first search beside the wrapper. Isolate both portable
        # models so an installed/real diagnostic_launcher.c cannot shadow them.
        forms = [
            'int main(int argc, char **argv) { return ru_program_main(argc, argv); }\n',
            'int main(int argc, char **argv) { int status = ru_program_main(argc, argv); return status; }\n',
        ]
        cases = []
        for index, form in enumerate(forms):
            (self.root/'diagnostic_launcher.c').write_text(form, encoding='utf-8')
            output = subprocess.check_output([cc, '-E', '-P', '-DRU_BOOTSTRAP_BRIDGE_TEST', str(wrapper)], text=True)
            cases.append(('portable-'+str(index), output, False))
        if sys.platform == 'win32':
            # Exercise the actual checked-in Windows diagnostic source AND
            # wWinMain, not a substituted one-line stub or weaker assertion.
            self.assertTrue((source.parent/'diagnostic_launcher.c').is_file())
            output = subprocess.check_output([cc, '-E', '-P', str(source)], text=True)
            cases.append(('real-windows', output, True))
        def check_graph(output, windows):
            self.assertRegex(output, r'extern int main\(int argc, char \*\*argv\);')
            self.assertRegex(output, r'static int ru_bootstrap_main_bridge\(int argc, char \*\*argv\)\s*\{\s*return main\(argc, argv\);\s*\}')
            self.assertIn('int ru_bootstrap_diagnostic_main(int argc, char **argv)', output)
            self.assertEqual(output.count('ru_bootstrap_main_bridge(argc, argv)'), 1)
            self.assertNotIn('ru_bootstrap_diagnostic_main(argc, argv)', output)
            self.assertNotRegex(output, r'\bint main\([^;]*\)\s*\{')
            if windows:
                self.assertIn('wWinMain(', output)
                self.assertEqual(output.count('ru_bootstrap_diagnostic_main(argc, utf8)'), 1)
        for label, output, windows in cases:
            with self.subTest(form=label):
                check_graph(output, windows)
                # Both macro-order recursion and diagnostic self-recursion
                # must fail the same contract in each preprocessed form.
                with self.assertRaises(AssertionError):
                    check_graph(output.replace('return main(argc, argv);', 'return ru_bootstrap_main_bridge(argc, argv);', 1), windows)
                with self.assertRaises(AssertionError):
                    check_graph(output.replace('ru_bootstrap_main_bridge(argc, argv)', 'ru_bootstrap_diagnostic_main(argc, argv)'), windows)
                compiled = self.root/(label+'.o')
                subprocess.run([cc, '-c', '-x', 'c', '-', '-o', str(compiled)], input=output, text=True, check=True)
                self.assertTrue(compiled.is_file())

    def test_final_gui_pe_not_console(self):
        pe = bytearray(256)
        pe[:2] = b'MZ'
        struct.pack_into('<I', pe, 60, 64)
        pe[64:68] = b'PE\0\0'
        struct.pack_into('<H', pe, 68, 0x8664)
        struct.pack_into('<H', pe, 88, 0x20b)
        struct.pack_into('<H', pe, 156, 2)
        output = self.root/'final.exe'
        output.write_bytes(pe)
        b.verify_gui_pe(output)
        struct.pack_into('<H', pe, 156, 3)
        output.write_bytes(pe)
        self.assertRaises(InvalidProvenance, b.verify_gui_pe, output)

    def test_baseline_all_original_bytes_and_only_approved_additions(self):
        repo = self.root/'repo'
        repo.mkdir()
        def git(*args):
            return subprocess.check_output(['git','-C',str(repo),*args], text=True, stderr=subprocess.DEVNULL).strip()
        git('init')
        (repo/'original.ru').write_text('original')
        git('add','.')
        git('-c','user.name=Test','-c','user.email=t@example.test','commit','-m','base')
        pin = {'commit':git('rev-parse','HEAD'), 'tree':git('rev-parse','HEAD^{tree}')}
        for name in b.ADDITIONS:
            file = repo/name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text('pipeline only')
        git('add','.')
        git('-c','user.name=Test','-c','user.email=t@example.test','commit','-m','pipeline')
        current = b.snapshot(repo,git('rev-parse','HEAD'),git('rev-parse','HEAD^{tree}'))
        self.assertEqual(b.verify_app_baseline(repo,pin,current)['unchanged_files'],1)
        changed = dict(current)
        changed['original.ru'] = '0'*64
        self.assertRaises(InvalidProvenance,b.verify_app_baseline,repo,pin,changed)
        changed = dict(current)
        changed['src/unapproved.ru'] = '0'*64
        self.assertRaises(InvalidProvenance,b.verify_app_baseline,repo,pin,changed)

    def test_pinned_archive_extract_and_exact_source_recheck(self):
        root = self.root/'app'
        download = root/'vendor/downloads'
        download.mkdir(parents=True)
        archive = download/'fixture.zip'
        with zipfile.ZipFile(archive,'w') as bundle:
            bundle.writestr('fixture/file.c','fixed C')
        dependency = {'archive':'fixture.zip','sha256':b.sha(archive),'folder':'fixture'}
        dependencies.extract_sources(root,dependency)
        dependencies.verify_dependency_bytes(root,{'Fixture.dll':dependency})
        self.assertRaises(InvalidProvenance,dependencies.extract_sources,root,dependency)
        (root/'vendor/fixture/file.c').write_text('changed')
        self.assertRaises(InvalidProvenance,dependencies.verify_dependency_bytes,root,{'Fixture.dll':dependency})

    def test_archive_traversal_rejected_even_if_hash_matches(self):
        root = self.root/'app'
        download = root/'vendor/downloads'
        download.mkdir(parents=True)
        archive = download/'fixture.zip'
        with zipfile.ZipFile(archive,'w') as bundle:
            bundle.writestr('fixture/../../escape.c','bad')
        dependency = {'archive':'fixture.zip','sha256':b.sha(archive),'folder':'fixture'}
        self.assertRaises(InvalidProvenance,dependencies.extract_sources,root,dependency)
        self.assertFalse((root/'escape.c').exists())



class LinkerSelectionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.linker = self.root/'sp ace 汉😀$'/'link.exe';self.linker.parent.mkdir();self.linker.write_bytes(b'linker')
        self.tools = {'clang': '/locked/clang', 'linker': str(self.linker)}
        self.record = b.identity(self.linker)
        self.command = [self.tools['clang'],str(self.root/'a.obj'),'-o',str(self.root/'a.exe'),*b.explicit_linker_flags(self.record)]
        self.raw = link_trace([str(self.linker), '-out:a.exe'])
        with patch.object(b.subprocess, 'run', return_value=SimpleNamespace(returncode=0,stdout=b'',stderr=self.raw)):
            self.selection = b.inspect_linker_command(self.command,self.record,{'OWNED':'yes'},str(self.root))

    def test_complete_selection_validates_raw_bytes_and_exact_actual_command(self):
        b.verify_linker_selection(self.selection,self.tools,expected_command=self.command,triple='x86_64-pc-windows-msvc')
        self.assertEqual(self.selection['dry_run_stderr_utf8'].encode(),self.raw)
        for field, value in [('command',self.command+['-other']), ('selected_command',[str(self.linker),'different']),
                ('dry_run_stderr_sha256','0'*64), ('dry_run_command',self.command),
                ('dry_run_stderr_utf8',self.raw.decode()+'clang: error: bad\n'), ('scope','OS process tracing')]:
            candidate = dict(self.selection);candidate[field]=value
            with self.subTest(field=field),self.assertRaises(InvalidProvenance):
                b.verify_linker_selection(candidate,self.tools,expected_command=self.command,triple='x86_64-pc-windows-msvc')

    def test_wrong_linker_path_is_not_rescued_by_expected_path_in_arguments(self):
        other=self.root/'other'/'link.exe';other.parent.mkdir();other.write_bytes(b'linker')
        for selected in (str(other),'x86_64-pc-windows-msvc-'+str(self.linker),'link.exe'):
            candidate=dict(self.selection);raw=link_trace([selected,str(self.linker)])
            candidate.update(dry_run_stderr_utf8=raw.decode(),dry_run_stderr_sha256=b.bytes_digest(raw),selected_command=[selected,str(self.linker)])
            with self.subTest(selected=selected),self.assertRaises(InvalidProvenance):
                b.verify_linker_selection(candidate,self.tools)

    def test_trace_negative_grammar_and_diagnostics(self):
        raw=self.raw
        for invalid in (b'',raw+raw.splitlines()[-1]+b'\n',raw+b'clang: error: bad\n',
                raw.replace(b'"-out:a.exe"',b'"@args.rsp"'),raw.replace(b'"-out:a.exe"',b'"bad\\n"'),
                raw.replace(b'"-out:a.exe"',b'"broken'),raw+b'unknown diagnostic\n'):
            with self.subTest(invalid=invalid[-50:]),self.assertRaises(ValueError):
                b.parse_linker_trace(invalid)

    def test_probe_runs_same_owned_unicode_object_link_and_revalidates_receipt(self):
        calls=[]
        def run(command,**kwargs):
            calls.append((command,kwargs))
            if '-c' in command:
                Path(command[-1]).write_bytes(b'obj')
            elif '-o' in command:
                Path(command[command.index('-o')+1]).write_bytes(b'MZprobe')
            return ''
        def dry(command,**kwargs):
            self.assertEqual(kwargs['cwd'],str(self.root))
            self.assertEqual(kwargs['env'],{'OWNED':'yes'})
            return SimpleNamespace(returncode=0,stdout=b'',stderr=link_trace([str(self.linker),str(self.root/'link probe 汉😀$.obj')]))
        with patch.object(b.subprocess,'run',side_effect=dry):
            receipt=b.linker_preflight(self.tools,self.root,'x86_64-pc-windows-msvc',{'OWNED':'yes'},run,self.record)
        self.assertEqual(len(calls),3)
        self.assertEqual(calls[-1][0],[str(self.root/'link probe 汉😀$.exe')])
        b.verify_linker_probe(receipt,self.tools,'x86_64-pc-windows-msvc',self.root)
        (self.root/'link probe 汉😀$.exe').write_bytes(b'changed')
        self.assertRaises(InvalidProvenance,b.verify_linker_probe,receipt,self.tools,'x86_64-pc-windows-msvc',self.root)

    def test_probe_mutations_cannot_be_resampled_as_new_baseline(self):
        for phase in ('source', 'object', 'binary'):
            with self.subTest(phase=phase):
                calls=[]
                def run(command,**kwargs):
                    calls.append(command)
                    if '-c' in command:
                        Path(command[-1]).write_bytes(b'obj')
                        if phase=='source':
                            (self.root/'link probe 汉😀$.c').write_bytes(b'changed')
                    elif '-o' in command:
                        Path(command[command.index('-o')+1]).write_bytes(b'MZprobe')
                        if phase=='object':
                            (self.root/'link probe 汉😀$.obj').write_bytes(b'changed')
                    elif phase=='binary':
                        Path(command[0]).write_bytes(b'changed')
                    return ''
                with patch.object(b.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=b'',stderr=link_trace([str(self.linker)]))):
                    with self.assertRaises(InvalidProvenance):
                        b.linker_preflight(self.tools,self.root,'x86_64-pc-windows-msvc',{},run,self.record)
                self.assertEqual(len(calls),{'source':1,'object':2,'binary':3}[phase])


if __name__ == '__main__':
    unittest.main()
