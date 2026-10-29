"""Portable supplemental-source checks; the native all-language gate runs on Windows."""
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import prepare_lexilla_languages as extra


class SupplementalLexillaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ru-lexilla-extra-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for relative in extra.INPUTS:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
        with zipfile.ZipFile(ROOT / 'third_party/source_archives/lexilla554.zip') as archive:
            self.original = {item.filename: archive.read(item) for item in archive.infolist() if not item.is_dir()}
            archive.extractall(self.root / 'vendor')

    def test_reproducible_separate_catalogue_keeps_every_original_byte(self):
        report = extra.prepare(self.root)
        self.assertEqual(report, extra.prepare(self.root))
        self.assertEqual(report, extra.verify(self.root))
        for name, data in self.original.items():
            self.assertEqual((self.root / 'vendor' / name).read_bytes(), data, name)
        generated = (self.root / 'vendor/lexilla/src/LexillaRu.cxx').read_bytes()
        self.assertEqual(generated.count(b'extern const LexerModule lmObjC;'), 1)
        self.assertEqual(generated.count(b'&lmObjC,'), 1)
        objc = (self.root / 'vendor/lexilla/lexers/LexObjC.cxx').read_bytes()
        self.assertTrue(objc.endswith((self.root / extra.SOURCE).read_bytes()))
        self.assertIn(b'#define SCLEX_OBJC 151', objc)

    def test_modified_source_license_and_original_are_rejected(self):
        for relative in (extra.SOURCE, extra.LICENSE, 'vendor/lexilla/src/Lexilla.cxx'):
            file = self.root / relative
            before = file.read_bytes()
            file.write_bytes(before + b'changed')
            with self.assertRaises(RuntimeError):
                extra.prepare(self.root)
            file.write_bytes(before)

    def test_modified_generated_file_is_never_overwritten_or_accepted(self):
        extra.prepare(self.root)
        for relative in extra.expected_files(self.root):
            file = self.root / relative
            before = file.read_bytes()
            file.write_bytes(before + b'changed')
            with self.assertRaises(RuntimeError):
                extra.prepare(self.root)
            with self.assertRaises(RuntimeError):
                extra.verify(self.root)
            self.assertTrue(file.read_bytes().endswith(b'changed'))
            file.write_bytes(before)

    def test_symlink_output_is_rejected(self):
        target = self.root / 'vendor/lexilla/src/LexillaRu.cxx'
        try:
            target.symlink_to(self.root / extra.SOURCE)
        except OSError:
            self.skipTest('host does not permit symbolic links')
        with self.assertRaises(RuntimeError):
            extra.prepare(self.root)

    def test_both_build_paths_use_the_same_catalogue(self):
        build = (ROOT / 'tools/build.py').read_text()
        bootstrap = (ROOT / 'tools/prepare_bootstrap_dependencies.py').read_text()
        for text in (build, bootstrap):
            self.assertIn('lexilla_languages.prepare(', text)
            self.assertIn('lexilla_languages.MAKE_OBJECT', text)
            self.assertIn('lexilla_languages.verify(', text)
            self.assertIn("'lexilla_extra'", text)


if __name__ == '__main__':
    unittest.main()
