"""Fail-closed split-job source, execution and delivery contracts."""
import copy
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import bootstrap_preflight as preflight
from bootstrap_provenance import InvalidProvenance

class PreflightContracts(unittest.TestCase):
    def receipt(self):
        return {'schema': 'ru-notepad-cheap-preflight-v1', 'passed': True,
                'job': 'cheap-preflight', 'run_id': '123', 'run_attempt': '1',
                'block_sha256': preflight.BLOCK_SHA256,
                'sources': {'app_source': {'commit': 'a'*40, 'tree': 'b'*40},
                            'ru_source': {'commit': 'c'*40, 'tree': 'd'*40}}}

    def test_exact_source_run_and_success_required(self):
        value = self.receipt()
        self.assertEqual(preflight.validate(value, value['sources'], '123', '1'), value)
        variants = [None, {}, {**value, 'passed': 1}, {**value, 'passed': False},
                    {**value, 'extra': True}]
        for key in ('schema', 'job', 'run_id', 'run_attempt', 'block_sha256'):
            variants.append({**value, key: 'wrong'})
        for source in ('app_source', 'ru_source'):
            for field in ('commit', 'tree'):
                bad = copy.deepcopy(value); bad['sources'][source][field] = '0'*40
                variants.append(bad)
        for bad in variants:
            with self.subTest(bad=bad), self.assertRaises(InvalidProvenance):
                preflight.validate(bad, value['sources'], '123', '1')

    def test_tracked_source_drift_cannot_emit_success(self):
        with patch.object(preflight, 'git', side_effect=['', '']) as git:
            preflight.require_tracked_clean(Path('source'))
            self.assertEqual(git.call_count, 2)
        for observations in (['changed.ru'], ['', 'staged.ru']):
            with patch.object(preflight, 'git', side_effect=observations), self.assertRaises(InvalidProvenance):
                preflight.require_tracked_clean(Path('source'))

    def test_required_same_source_jobs_and_unchanged_gates(self):
        text = (preflight.ROOT/'.github/workflows/bootstrap-preview.yml').read_text()
        cheap, main = text.split('  windows-preview:\n')
        self.assertIn('    needs: cheap-preflight\n', main)
        for job, budget in ((cheap,60), (main,90)):
            self.assertIn(f'    timeout-minutes: {budget}\n', job)
            self.assertIn('          ref: ${{ github.sha }}\n          path: editor', job)
            self.assertIn('ref: ${{ steps.pins.outputs.compiler_commit }}', job)
            self.assertNotIn('continue-on-error', job)
        self.assertNotIn('    if:', main.split('    steps:')[0])
        self.assertNotIn('Fail-closed cheap contract preflight', main)
        self.assertEqual(preflight.block_hash(), preflight.BLOCK_SHA256)
        self.assertIn('receipt: ${{ steps.receipt.outputs.receipt }}', cheap)
        self.assertIn('PREFLIGHT_RECEIPT: ${{ needs.cheap-preflight.outputs.receipt }}', main)
        self.assertLess(cheap.index('Fail-closed cheap'), cheap.index('Record successful source-bound'))
        for command in ('verify_bootstrap_recent_policies.py', 'verify_bootstrap_editor_windows.py',
                        'verify_bootstrap_product_windows.py', 'package_bootstrap_preview.py'):
            self.assertIn(command, main)
            self.assertNotIn(command, cheap)

    def test_receipt_bound_to_prepare_gate_and_zip(self):
        prepare = (preflight.ROOT/'tools/prepare_bootstrap_preview.py').read_text()
        package = (preflight.ROOT/'tools/package_bootstrap_preview.py').read_text()
        self.assertIn("json.loads(os.environ['PREFLIGHT_RECEIPT'])", prepare)
        self.assertIn("preflight_receipt=str(output/'cheap-preflight.json')", prepare)
        self.assertIn("validate_preflight(smoke.read_json(preflight_path), report['source_pins']", package)
        self.assertIn("'preflight_receipt': identity(preflight_path)", package)
        self.assertIn("stage/'evidence/cheap-preflight.json'", package)
        self.assertIn("'cheap_preflight': preflight", package)

if __name__ == '__main__':
    unittest.main()
