"""Standalone full receipt tamper tests; only compiler --version is mocked."""
import hashlib, importlib.util, json, subprocess, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import build_baseline as a
HERE=Path(__file__).resolve().parent
candidates=[HERE.parent/'public-recovery-20261021/markdown_edit_profile',HERE.parent.parent/'baseline']
ROOT=next((p for p in candidates if (p/'tools/package.py').is_file()),None)
if ROOT is None:raise RuntimeError('fixed baseline source required for receipt controls')
spec=importlib.util.spec_from_file_location('_comparison_receipt_package',ROOT/'tools/package.py')
receipt_package=importlib.util.module_from_spec(spec);spec.loader.exec_module(receipt_package)
receipt_base=SimpleNamespace(RUNTIME_NAMES=('ru_notepad.exe','Scintilla.dll','Lexilla.dll','RuSyntax.dll'))
class FullReceiptFixture:
    VERSION = b'synthetic compiler version 1\n'
    def __init__(self):
        self.temp = tempfile.TemporaryDirectory(prefix='width-full-receipt-')
        self.home = Path(self.temp.name).resolve()
        self.root = self.home / 'application'
        self.binary = self.home / 'binary'
        self.binary.mkdir()
        self.cc = self.home / 'gcc.exe'
        self.cc.write_bytes(b'synthetic compiler identity; never executed')
        self.p = SimpleNamespace(package=receipt_package, base=receipt_base)
        paths = {'src/main.ru', 'src/unselected.ru', 'tests/extra-policy.ru',
                 'locales/test.json', 'tools/generate_i18n.py',
                 'native/nested/extra.h', 'build/main.c', 'build/main-gui.c',
                 'build/app-resource.o', 'packaging/diagnostic_launcher.c',
                 *receipt_package.RESOURCE_INPUTS, *receipt_package.NATIVE_BUILD_DRIVERS}
        paths.update(source for sources in receipt_package.NATIVE_COMPILE_SOURCES.values() for source in sources)
        for relative in paths:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(('synthetic:' + relative).encode())
        for name in receipt_base.RUNTIME_NAMES:
            (self.binary / name).write_bytes(('runtime:' + name).encode())
        native = dict(output_name='RuSyntax.dll',
                      source_sha256=receipt_package.native_source_snapshot(self.root),
                      driver_sha256={rel: a.sha(self.root / rel) for rel in receipt_package.NATIVE_BUILD_DRIVERS},
                      compile_sources=list(receipt_package.NATIVE_COMPILE_SOURCES['RuSyntax.dll']),
                      compiler_flags=list(receipt_package.NATIVE_CFLAGS),
                      link_libraries=list(receipt_package.NATIVE_LINK_LIBRARIES),
                      compiler_path=str(self.cc), compiler_sha256=a.sha(self.cc),
                      compiler_version_sha256=hashlib.sha256(self.VERSION).hexdigest())
        self.helper = dict(schema=1, name='RuSyntax.dll', build_inputs=native,
                           build_key=receipt_package.native_build_key(native),
                           dll_sha256=a.sha(self.binary / 'RuSyntax.dll'))
        self.receipt = dict(schema=1, ru_commit=a.COMPILER, ru_tree=a.COMPILER_TREE,
                            entry_source='src/main.ru', entry_sha256=a.sha(self.root / 'src/main.ru'),
                            source_sha256=a.source_snapshot(self.root, self.p),
                            build_input_sha256={rel: a.sha(self.root / rel) for rel in (*receipt_package.RESOURCE_INPUTS, 'packaging/diagnostic_launcher.c')},
                            generated_c_sha256=a.sha(self.root / 'build/main.c'),
                            translation_unit_sha256=a.sha(self.root / 'build/main-gui.c'),
                            native_helper_build_key=self.helper['build_key'],
                            compiler_command=[str(self.cc), '-std=c99', '-O2', '-Wall', '-Wextra', '-Wno-unused-function', '-static-libgcc',
                                              str(self.root / 'build/main-gui.c'), '-o', str(self.binary / 'ru_notepad.exe'), '-lm',
                                              str(self.root / 'build/app-resource.o'), '-mwindows', '-lshell32', '-luser32'])
        for name, key in zip(receipt_base.RUNTIME_NAMES, ('exe_sha256', 'dll_sha256', 'lexilla_dll_sha256', 'native_helper_sha256')):
            self.receipt[key] = a.sha(self.binary / name)
        self.write()
    def write(self):
        (self.binary / 'ru_notepad.build.json').write_text(json.dumps(self.receipt))
        (self.binary / 'RuSyntax.native-build.json').write_text(json.dumps(self.helper))
    def reseal_native_key(self):
        self.helper['build_key'] = receipt_package.native_build_key(self.helper['build_inputs'])
        self.receipt['native_helper_build_key'] = self.helper['build_key']
    def verify(self, *, version=None, returncode=0):
        def compiler_version(command, **kwargs):
            if command != [str(self.cc), '--version']:
                raise AssertionError('unexpected external command')
            return subprocess.CompletedProcess(command, returncode, self.VERSION if version is None else version, b'')
        # Only the version subprocess is mocked: all receipts, source scanning,
        # hashes, constants, source/layout checks and native build keys are real.
        with patch.object(a.subprocess, 'run', side_effect=compiler_version):
            return a.full_receipt(self.root, self.binary, self.cc, self.p)
    def close(self):
        self.temp.cleanup()


class Controls(unittest.TestCase):
    def fresh(self):
        f=FullReceiptFixture();self.addCleanup(f.close);return f
    def reject(self,change):
        f=self.fresh();change(f);f.write()
        with self.assertRaises(ValueError):f.verify()
    def test_valid(self):self.fresh().verify()
    def test_generated(self):
        for name in ('build/main.c','build/main-gui.c'):
            with self.subTest(name=name):self.reject(lambda f:(f.root/name).write_bytes(b'changed'))
    def test_runtime(self):
        for name in receipt_base.RUNTIME_NAMES:
            with self.subTest(name=name):self.reject(lambda f:(f.binary/name).write_bytes(b'changed'))
    def test_source(self):self.reject(lambda f:(f.root/'src/unselected.ru').write_bytes(b'changed'))
    def test_flags(self):self.reject(lambda f:f.receipt['compiler_command'].__setitem__(2,'-O0'))
    def test_compiler(self):self.reject(lambda f:f.cc.write_bytes(b'changed'))
    def test_compiler_version(self):
        with self.assertRaises(ValueError):self.fresh().verify(version=b'wrong')
    def test_native_flags_resealed(self):
        def change(f):
            f.helper['build_inputs']['compiler_flags']=['-O0'];f.reseal_native_key()
        self.reject(change)
    def test_native_driver_resealed(self):
        def change(f):
            f.helper['build_inputs']['driver_sha256']['tools/build.py']='0'*64;f.reseal_native_key()
        self.reject(change)
if __name__=='__main__':unittest.main()
