"""Portable receipt consumer controls, not Windows execution evidence."""
from copy import deepcopy
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import verify_bootstrap_product_windows as product
import verify_recent_files_windows as recent
import test_gui_instance_tabs as samples
from bootstrap_provenance import InvalidProvenance

class InstanceProductContract(unittest.TestCase):
    def record(self):
        return dict(schema=product.SCHEMA,status='passed',
            all_native_console_tests_bootstrap_compiled=False,full_release_acceptance=False,
            runtime_sha256=dict(samples.HASHES),gui_results=[],scanner_preflight={},
            recent_files={},instance_tabs=samples.receipt())

    def validate(self,record):
        ci=SimpleNamespace(portable=SimpleNamespace(RUNTIME_NAMES=tuple(samples.HASHES)),
            validate_scanner_preflight=lambda *a:None)
        with patch.object(product,'validate_gui_results'),patch.object(recent,'validate_recent_files_result'):
            product.validate_product(record,ci)

    def test_valid_complete_new_contract(self):
        self.validate(self.record())

    def test_old_or_missing_new_feature_receipt_cannot_pass(self):
        r=self.record();r['schema']='ru-notepad-bootstrap-product-preview-v1'
        with self.assertRaises(InvalidProvenance):self.validate(r)
        r=self.record();del r['instance_tabs']
        with self.assertRaises(ValueError):self.validate(r)

    def test_new_feature_verdict_and_identity_remain_required(self):
        mutations=[lambda x:x.update(passed=False),lambda x:x['checks'].pop(next(iter(x['checks']))),
            lambda x:x['phases'].pop(),lambda x:x['secondary_processes'].pop(),
            lambda x:x.update(fixture_binary_sha256={}),
            lambda x:x['phases'][0].update(cleanup_killed=True)]
        for mutate in mutations:
            r=self.record();mutate(r['instance_tabs'])
            with self.assertRaises(ValueError):self.validate(r)

if __name__=='__main__':unittest.main()
