#!/usr/bin/env python3
"""Host reproductions for Windows control portability; no native claims."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_focused_native_diagnostic as controls


class PortabilityControls(unittest.TestCase):
    def test_explicit_utf8_survives_ansi_default_and_original_fails(self):
        read_text = Path.read_text

        def ansi_default(path, *args, **kwargs):
            if not args and 'encoding' not in kwargs:
                kwargs['encoding'] = 'cp1252'
            return read_text(path, *args, **kwargs)

        control = controls.PublicationControls('test_source_build_and_gc_contracts_are_reused')
        with patch.object(Path, 'read_text', ansi_default):
            # Execute the original control body, including its Chinese assertion.
            control.test_source_build_and_gc_contracts_are_reused()

        def original_unspecified_encoding(path, *args, **kwargs):
            if path == Path(controls.runner.__file__):
                kwargs['encoding'] = 'cp1252'
            return read_text(path, *args, **kwargs)

        with patch.object(Path, 'read_text', original_unspecified_encoding):
            with self.assertRaises(AssertionError):
                control.test_source_build_and_gc_contracts_are_reused()

    def test_resolved_helper_command_survives_alias_and_original_fails(self):
        temporary_directory = tempfile.TemporaryDirectory
        with temporary_directory() as parent_name:
            parent = Path(parent_name)
            (parent / 'detour').mkdir()

            class AliasedTemporaryDirectory:
                def __init__(self):
                    self.actual = temporary_directory(dir=parent)
                    # Equivalent path spellings without symlink privileges. A
                    # Windows short path is likewise canonicalized by resolve.
                    self.name = str(parent / 'detour' / '..' / Path(self.actual.name).name)

                def cleanup(self):
                    self.actual.cleanup()

            control = controls.ReceiptControls('test_complete_source_bound_two_fixture_inventory')
            try:
                with patch.object(tempfile, 'TemporaryDirectory', AliasedTemporaryDirectory):
                    control.setUp()
                self.assertNotEqual(str(control.cc), str(control.cc.resolve()))
                control.test_complete_source_bound_two_fixture_inventory()

                path = control.binary / 'RuSyntax.native-build.json'
                receipt = json.loads(path.read_bytes())
                self.assertEqual(receipt['compiler_command'][0], receipt['build_inputs']['compiler_path'])
                receipt['compiler_command'][0] = str(control.cc)
                path.write_bytes(controls.runner.canonical(receipt))
                with self.assertRaises(ValueError):
                    control.verify()
            finally:
                control.doCleanups()


if __name__ == '__main__':
    unittest.main()
