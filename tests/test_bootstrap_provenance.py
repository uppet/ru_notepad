import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import bootstrap_provenance as p


def compare(first, second):
    # Fixture bytes have no timestamp variance. Production must use the reviewed
    # upstream PE timestamp-only comparator, not this test-only equality helper.
    return {'normalized_equal': first == second}


class ProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / 'source'
        self.artifacts = self.base / 'artifacts'
        self.artifacts.mkdir()
        for folder in ('tests', 'bootstrap/validation', 'rulang', 'tools'):
            (self.root / folder).mkdir(parents=True, exist_ok=True)
        (self.root / 'tests/test_bootstrap.py').write_text('class BootstrapTests:\n' + ''.join(
            f'    def test_{i:02d}(self): pass\n' for i in range(35)))
        (self.root / 'bootstrap/validation/practical.json').write_text('[]')
        (self.root / 'bootstrap/compiler.ru').write_text('fixture')
        def git(*args):
            return subprocess.check_output(['git', '-C', str(self.root), *args], text=True, stderr=subprocess.DEVNULL).strip()
        git('init')
        git('add', '.')
        git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.test', 'commit', '-m', 'fixture')
        self.commit, self.tree = git('rev-parse', 'HEAD'), git('rev-parse', 'HEAD^{tree}')
        pe = bytearray(256)
        pe[:2] = b'MZ'
        struct.pack_into('<I', pe, 60, 64)
        pe[64:68] = b'PE\0\0'
        struct.pack_into('<H', pe, 68, 0x8664)
        struct.pack_into('<H', pe, 88, 0x20b)
        names = ['stage1.exe', 'stage2.exe', 'stage3.exe', 'stage2.ll', 'stage3.ll'] + [
            f'stage{i}.exe.{suffix}' for i in (2, 3) for suffix in ('frontend.ll', 'metadata.c')]
        for name in names:
            ir = b'target triple = "x86_64-pc-windows-msvc19.0"\ntarget datalayout = "e-m:w-p270:32:32"\n'
            (self.artifacts / name).write_bytes(bytes(pe) if name.endswith('.exe') else ir if name.endswith('.ll') else b'fixed-point')
        cases = p.expected_cases(self.root)
        gates = ['source_ir_and_abi_fixed_point', 'native_binary_fixed_point',
                 'same_nonempty_suite_for_each_stage', 'every_planned_case_ran',
                 'every_case_passed_without_skips', 'test_runner_success_without_skips',
                 'inputs_unchanged', 'artifacts_unchanged_during_tests']
        self.report = dict(format=1, milestone='M4', platform='win32', m4_complete=True,
            gates=dict.fromkeys(gates, True), tests_run=105, failures=0, errors=0, skipped=0,
            planned_cases_by_stage={s: cases for s in ('1', '2', '3')},
            stages={s: [dict(id=s+'.'+c, case=c, stage=int(s), status='passed') for c in cases] for s in ('1', '2', '3')},
            input_sha256=p.source_inputs(self.root),
            artifact_sha256={'C:\\build\\'+n: p.sha(self.artifacts/n) for n in names},
            native_comparison=compare(bytes(pe), bytes(pe)),
            bootstrap=dict(platform='win32', fixed_point=True, triple='x86_64-pc-windows-msvc19.0',
                llvm='clang version 14.0.6', source_sha256=p.sha(self.root/'bootstrap/compiler.ru'),
                stages=[dict(source_ir_sha256=p.sha(self.artifacts/f'stage{i}.exe.frontend.ll'),
                    metadata_sha256=p.sha(self.artifacts/f'stage{i}.exe.metadata.c'),
                    binary_sha256=p.sha(self.artifacts/f'stage{i}.exe')) for i in (2, 3)]))
        self.report_path = self.base / 'verification.json'

    def validate(self):
        self.report_path.write_text(json.dumps(self.report))
        return p.validate(self.root, self.artifacts, self.report_path, self.commit, self.tree, compare,
            expected_triple='x86_64-pc-windows-msvc19.0', expected_data_layout='e-m:w-p270:32:32')

    def test_fixture_normalizes_short_temp_alias_before_use(self):
        # Portable model of Windows RUNNER~1: no symlink privileges required.
        canonical = self.base / 'long-temporary-path'
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
        fixture = ProvenanceTests(methodName='runTest')
        temporary = SimpleNamespace(name=alias, cleanup=lambda: None)
        try:
            with patch.object(tempfile, 'TemporaryDirectory', return_value=temporary), \
                    patch.object(sys.modules[__name__], 'Path', side_effect=paths):
                fixture.setUp()
            self.assertEqual(fixture.base, canonical)
            self.assertEqual(fixture.base, fixture.base.resolve())
        finally:
            fixture.doCleanups()

    def test_complete_fixture_is_evidence_only(self):
        self.assertEqual(self.validate()['status'], 'bootstrap-evidence-validated-not-editor-build')

    def test_missing_gate(self):
        del self.report['gates']['native_binary_fixed_point']
        self.assertRaises(p.InvalidProvenance, self.validate)

    def test_false_gate(self):
        self.report['gates']['inputs_unchanged'] = False
        self.assertRaises(p.InvalidProvenance, self.validate)

    def test_duplicate_case(self):
        self.report['stages']['1'][0] = self.report['stages']['1'][1]
        self.assertRaises(p.InvalidProvenance, self.validate)

    def test_invented_smaller_suite(self):
        self.report['planned_cases_by_stage']['1'] = []
        self.assertRaises(p.InvalidProvenance, self.validate)

    def test_wrong_stage(self):
        self.report['stages']['3'][0]['stage'] = 2
        self.assertRaises(p.InvalidProvenance, self.validate)

    def test_skipped_case(self):
        self.report['stages']['2'][0]['status'] = 'skipped'
        self.assertRaises(p.InvalidProvenance, self.validate)

    def test_tampered_stage3(self):
        (self.artifacts/'stage3.exe').write_bytes(b'old executable')
        self.assertRaises(p.InvalidProvenance, self.validate)

    def test_artifact_collision(self):
        self.report['artifact_sha256']['D:\\other\\stage3.exe'] = p.sha(self.artifacts/'stage3.exe')
        self.assertRaises(p.InvalidProvenance, self.validate)

    def test_missing_artifact(self):
        (self.artifacts/'stage1.exe').unlink()
        self.assertRaises(p.InvalidProvenance, self.validate)

    def test_linked_artifact(self):
        (self.artifacts/'stage3.exe').unlink()
        (self.artifacts/'stage3.exe').symlink_to(self.artifacts/'stage2.exe')
        self.assertRaises(p.InvalidProvenance, self.validate)

    def test_dirty_source(self):
        (self.root/'bootstrap/compiler.ru').write_text('changed')
        self.assertRaises(p.InvalidProvenance, self.validate)

    def test_missing_source_inventory(self):
        del self.report['input_sha256']['tests/test_bootstrap.py']
        self.assertRaises(p.InvalidProvenance, self.validate)

    def test_wrong_abi(self):
        self.report['bootstrap']['triple'] = 'x86_64-w64-windows-gnu'
        self.assertRaises(p.InvalidProvenance, self.validate)

    def test_wrong_llvm(self):
        self.report['bootstrap']['llvm'] = 'clang version 17.0.0'
        self.assertRaises(p.InvalidProvenance, self.validate)

    def test_ir_fixed_point_independent_of_boolean(self):
        file = self.artifacts/'stage3.exe.frontend.ll'
        file.write_bytes(b'different')
        self.report['artifact_sha256']['C:\\build\\'+file.name] = p.sha(file)
        self.report['bootstrap']['stages'][1]['source_ir_sha256'] = p.sha(file)
        self.assertRaises(p.InvalidProvenance, self.validate)

    def test_native_comparison_not_just_boolean(self):
        self.report['native_comparison']['forged'] = True
        self.assertRaises(p.InvalidProvenance, self.validate)

    def test_wrong_layout_even_with_matching_hash(self):
        file = self.artifacts/'stage3.ll'
        file.write_bytes(file.read_bytes().replace(b'e-m:w', b'e-m:e'))
        self.report['artifact_sha256']['C:\\build\\stage3.ll'] = p.sha(file)
        self.assertRaises(p.InvalidProvenance, self.validate)

    def test_missing_tool_identity(self):
        self.assertRaises(p.InvalidProvenance, p.validate_toolchain, {}, {})

    def test_tool_identity_and_tamper(self):
        names = ('clang', 'llvm-as', 'llvm-link', 'opt', 'llvm-dis', 'llc', 'linker', 'resource-compiler')
        paths = {name: self.base/name for name in names}
        for name, path in paths.items():
            path.write_text(name)
        hashes = {name: p.sha(path) for name, path in paths.items()}
        self.assertEqual(p.validate_toolchain(paths, hashes), hashes)
        paths['linker'].write_text('changed')
        self.assertRaises(p.InvalidProvenance, p.validate_toolchain, paths, hashes)


if __name__ == '__main__':
    unittest.main()
