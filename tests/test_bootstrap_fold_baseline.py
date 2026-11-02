"""Fail-closed fixed-artifact baseline transport; not Windows evidence."""
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import verify_fold_baseline as baseline

class FixedBaseline(unittest.TestCase):
    def test_pin_is_not_a_moving_branch(self):
        self.assertEqual(baseline.ARTIFACT,12880829425)
        self.assertEqual(baseline.BASELINE_COMMIT,'87189d2e36b282bf08bcf781be6a73570c2a22b0')
        self.assertEqual(baseline.PREVIEW_SHA,'5216b8a7ae700df6ce506000ca57f0fedff6e8dd3ee465d44fcb23c2a17870dc')
    def test_old_artifact_is_only_a_pinned_wip_transition_dependency(self):
        workflow=(Path(__file__).resolve().parents[1]/'.github/workflows/bootstrap-preview.yml').read_text()
        self.assertIn("if: github.event_name == 'push' && github.ref == 'refs/heads/wip' && github.event.before == '"+baseline.BASELINE_COMMIT+"'",workflow)
        self.assertLess(workflow.index('Fail-closed cheap contract preflight'),workflow.index('Reproduce fold-command defect'))
        self.assertLess(workflow.index('Reproduce fold-command defect'),workflow.index('Fresh three-stage self-compilation'))
    def test_wrong_archive_never_creates_destination(self):
        with tempfile.TemporaryDirectory() as root:
            target=Path(root)/'runtime'
            with self.assertRaises(ValueError):baseline.unpack(b'wrong',target)
            self.assertFalse(target.exists())
    def test_download_is_bounded(self):
        with patch.object(baseline,'LIMIT',8):
            self.assertEqual(baseline.bounded(io.BytesIO(b'12345678')),b'12345678')
            with self.assertRaises(ValueError):baseline.bounded(io.BytesIO(b'123456789'))
    def test_no_token_no_network(self):
        with patch.object(baseline.urllib.request,'build_opener') as opener:
            with self.assertRaises(ValueError):baseline.download('')
            opener.assert_not_called()
    def test_redirect_does_not_reuse_authorized_request(self):
        self.assertIsNone(baseline.NoRedirect().redirect_request(None,None,302,'',{},'https://example.invalid'))

if __name__=='__main__':unittest.main()
