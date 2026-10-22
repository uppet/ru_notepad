import json
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
            'link_flags': ['-fuse-ld='+tools['linker']]}
        self.proof['linker'] = b.identity(tools['linker'])
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
        (self.root/'diagnostic_launcher.c').write_text(
            'int main(int argc, char **argv) { return ru_program_main(argc, argv); }\n')
        wrapper = Path(__file__).resolve().parents[1]/'packaging/bootstrap_gui_launcher.c'
        output = subprocess.check_output([cc, '-E', '-P', '-DRU_BOOTSTRAP_BRIDGE_TEST',
            '-I', str(self.root), str(wrapper)], text=True)
        self.assertIn('return main(argc, argv);', output)
        self.assertIn('int ru_bootstrap_diagnostic_main(int argc, char **argv)', output)
        self.assertIn('return ru_bootstrap_main_bridge(argc, argv);', output)
        self.assertNotIn('return ru_bootstrap_diagnostic_main(argc, argv);', output)
        # Compile the preprocessed adapter as C too; the real LLVM main remains
        # an unresolved external for the final Windows linker, not recursion.
        compiled = self.root/'bridge.o'
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


if __name__ == '__main__':
    unittest.main()
