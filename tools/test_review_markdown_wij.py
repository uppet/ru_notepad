#!/usr/bin/env python3
"""Offline negative controls for the development review wrapper, not native proof."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('wij_review', HERE / 'review_markdown_wij.py')
review = importlib.util.module_from_spec(spec); spec.loader.exec_module(review)

spec = importlib.util.spec_from_file_location('ordinary_review', HERE / 'review_markdown_ordinary_pair.py')
ordinary = importlib.util.module_from_spec(spec); spec.loader.exec_module(ordinary)


class ReviewContracts(unittest.TestCase):
    def native_fixture(self, timeout=180, ordinary_mode=False, stdout='NATIVE_ALL_FOLDS 42\nINCREMENTAL_NATIVE_PASS\n'):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        out = Path(directory.name)
        module = types.SimpleNamespace(SOURCE="(折 其 _密扫描策略) 其 增 'enabled' 真.")
        def main():
            module.subprocess.run([str(out / 'program.exe')], timeout=timeout)
            (out / 'result.json').write_text(json.dumps({'passed': True, 'gc_live_zero': True, 'stdout': stdout}))
        module.main = main
        fake_spec = types.SimpleNamespace(loader=types.SimpleNamespace(exec_module=lambda _: None))
        with patch.object(review.importlib.util, 'spec_from_file_location', return_value=fake_spec), \
             patch.object(review.importlib.util, 'module_from_spec', return_value=module), \
             patch.object(review.subprocess, 'run', return_value=types.SimpleNamespace(returncode=0)) as run, \
             patch.object(sys, 'argv', ['negative-controls']):
            review.native_child(out, out, out, ordinary_mode)
            self.assertEqual(module.SOURCE.endswith("假."), ordinary_mode)
            return run.call_args

    def test_native_helper_is_tightened_to_exact_120(self):
        self.assertEqual(self.native_fixture().kwargs['timeout'], 120)

    def test_changed_historical_timeout_contract_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'timeout contract'):
            self.native_fixture(timeout=240)

    def test_missing_or_changed_case_inventory_is_rejected(self):
        for stdout in ('INCREMENTAL_NATIVE_PASS\n', 'NATIVE_ALL_FOLDS 41\nINCREMENTAL_NATIVE_PASS\n'):
            with self.subTest(stdout=stdout), self.assertRaisesRegex(RuntimeError, 'inventory'):
                self.native_fixture(stdout=stdout)

    def test_workflow_keeps_development_separate_and_uploads_only_receipts(self):
        text = (HERE.parent / '.github/workflows/wij-development.yml').read_text()
        self.assertIn('ref: ' + review.COMPILER, text)
        self.assertIn('fetch-depth: 0', text)
        self.assertIn('path: build/wij-development/evidence/*.json', text)
        self.assertNotIn('package.py', text)
        self.assertNotIn('release', text.replace('ZIP release', ''))
        product = (HERE.parent / '.github/workflows/windows.yml').read_text()
        self.assertIn('ref: 85c7821fda35aa79deeaf67b4d430f24ddd7f07f', product)

    def test_ordinary_native_changes_only_dense_activation(self):
        self.assertEqual(self.native_fixture(ordinary_mode=True).kwargs['timeout'], 120)

    def test_timeout_classification_is_exact_not_generic_failure(self):
        for error in ordinary.TIMEOUT_ERRORS:
            result = {'passed': False, 'error': error, 'executed': True, 'source_bytes_preserved': True,
                      'markdown_performance': {'cases': [{'stages': [{'wall_ms': 30001}]}]}}
            self.assertEqual(ordinary.classification(result), 'original_30s_timeout')
            result['clock_error'] = 'backwards'
            self.assertEqual(ordinary.classification(result), 'correctness_or_other_failure')
        for error in ('No visible main HWND within 30 seconds', 'fold mismatch', 'LLVM timeout', ''):
            self.assertEqual(ordinary.classification({'passed': False, 'error': error}), 'correctness_or_other_failure')

    def test_success_requires_all_fixed_stages_inside_original_gate(self):
        result = {'passed': True, 'markdown_performance': {'cases': [
            {'kind': case, 'stages': [{'operation': op, 'wall_ms': 100} for op in ordinary.OPERATIONS]}
            for case in ordinary.CASES]}}
        self.assertEqual(ordinary.classification(result), 'complete')
        result['markdown_performance']['cases'][0]['stages'][0]['wall_ms'] = 30001
        with self.assertRaises(AssertionError): ordinary.classification(result)
        result['markdown_performance']['cases'][0]['stages'].pop()
        with self.assertRaises(AssertionError): ordinary.classification(result)

    def test_evidence_collection_is_allowlisted_and_captures_failed_dense_result(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory); evidence = out / 'evidence'; evidence.mkdir()
            failed = out / 'benchmark/control-1/result.json'; failed.parent.mkdir(parents=True)
            failed.write_text('{"passed":false}')
            (failed.parent / 'private.log').write_text('not uploaded')
            native = out / 'native-helper/RuSyntax.native-build.json'; native.parent.mkdir()
            native.write_text('{}')
            review.collect_evidence(out, evidence)
            self.assertEqual({p.name for p in evidence.iterdir()},
                             {'benchmark-control-1.json', 'native-source-build.json'})
            self.assertEqual((evidence / 'benchmark-control-1.json').read_bytes(), failed.read_bytes())
            with failed.open('wb') as stream: stream.truncate(16 * 1024 * 1024 + 1)
            with self.assertRaisesRegex(RuntimeError, 'per-file'): review.collect_evidence(out, evidence)

    def test_diagnostic_tail_reads_only_bounded_suffix(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'owned.log'; path.write_bytes(b'a' * 10000 + b'end')
            tail = review.bounded_tail(path)
            self.assertEqual(len(tail), 4096)
            self.assertTrue(tail.endswith('end'))

    def test_production_flags_remain_false(self):
        text = (HERE.parent / 'src/markdown_syntax.ru').read_text()
        for name in ('_密扫描策略', '_增量策略'):
            self.assertEqual(text.count(name + " 取 {'enabled':假}."), 1)


if __name__ == '__main__':
    unittest.main()
