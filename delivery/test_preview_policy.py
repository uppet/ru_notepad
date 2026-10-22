#!/usr/bin/env python3
"""Offline synthetic negative controls; no Windows execution claim."""
import atexit
import faulthandler
import sys

# Bound only this synthetic control process; never alter native acceptance.
# Traceback contains code locations, not locals, environment values or file data.
faulthandler.dump_traceback_later(60, repeat=False, exit=False)
atexit.register(faulthandler.cancel_dump_traceback_later)
print('[preview-policy-controls] imports begin', flush=True)
import argparse
import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument('--product-root', type=Path, required=True)
args, rest = parser.parse_known_args()
sys.path.insert(0, str(args.product_root.absolute() / 'tools'))
sys.path.insert(0, str(Path(__file__).absolute().parent))
import package_manual_preview as p
import test_package_manual_preview as fixtures
import preview_policy as policy
print('[preview-policy-controls] imports complete', flush=True)


class ExactPolicyTests(unittest.TestCase):
    def setUp(self):
        print('[preview-policy-controls] fixture begin: ' + self._testMethodName, flush=True)
        self.f = fixtures.ManualPreviewTests('runTest')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.addCleanup(patch.stopall)
        old_identity = p.git_identity
        def identity(root):
            record = old_identity(root)
            return dict(record, app_commit=policy.PRODUCT_COMMIT, app_tree=policy.PRODUCT_TREE)
        patch.object(p, 'git_identity', side_effect=identity).start()
        for path in self.f.binary.glob('*.build.json'):
            value = json.loads(path.read_text())
            value['ru_commit'] = policy.COMPILER_COMMIT
            value['ru_tree'] = policy.COMPILER_TREE
            path.write_text(json.dumps(value), encoding='utf-8')
        self.source = {'app_commit': policy.PRODUCT_COMMIT, 'app_tree': policy.PRODUCT_TREE}
        self.app = {'ru_commit': policy.COMPILER_COMMIT, 'ru_tree': policy.COMPILER_TREE}
        self.guard = policy.Eligibility(p, self.source, self.app)
        print('[preview-policy-controls] fixture complete: ' + self._testMethodName, flush=True)

    def known(self):
        stage = self.f.timeout(case_index=1, stage_index=3)
        stage['undo_commands'] = 2
        self.f.markdown()['error'] = policy.GENERIC_ERROR
        return stage

    def validate(self):
        with self.guard.installed():
            return p.validate_summary(self.f.summary, self.f.root, self.f.summary['tested_binary_sha256'])

    def test_known_observer_deadline_retains_error_failed_status_and_entire_summary(self):
        self.known()
        before = copy.deepcopy(self.f.summary)
        error_names = p.DEADLINES
        result = self.validate()
        self.assertEqual(result['formal_acceptance'], 'failed')
        self.assertEqual(result['timeout']['kind'], 'singleline')
        self.assertEqual(result['timeout']['operation'], 'undo')
        self.assertEqual(self.f.summary, before)
        self.assertIs(p.DEADLINES, error_names)
        self.assertEqual(self.f.markdown()['error'], policy.GENERIC_ERROR)
        with self.assertRaises(RuntimeError):
            self.guard.original_timeout(self.f.markdown(), self.f.summary)
        with self.assertRaises(RuntimeError):
            p.ci.validate_acceptance(self.f.summary, self.f.root)

    def test_product_and_compiler_identity_negative_controls(self):
        for label in ('commit', 'tree', 'compiler', 'compiler_tree'):
            with self.subTest(label=label):
                source, app = copy.deepcopy(self.source), copy.deepcopy(self.app)
                if label == 'commit': source['app_commit'] = '1' * 40
                if label == 'tree': source['app_tree'] = '2' * 40
                if label == 'compiler': app['ru_commit'] = '4' * 40
                if label == 'compiler_tree': app['ru_tree'] = 'unknown'
                with self.assertRaises(RuntimeError): policy.Eligibility(p, source, app)

    def test_all_unknown_and_contradictory_records_fail_closed(self):
        self.known()
        original = copy.deepcopy(self.f.summary)
        def md(s): return next(t for t in s['tests'] if t['name'] == 'main-gui-markdown')
        def stage(s): return md(s)['markdown_performance']['cases'][-1]['stages'][-1]
        mutations = {
            'unknown-error': lambda s: md(s).update(error='Unexpected runtime error'),
            'wrong-gui': lambda s: md(s).update(name='main-gui-other'),
            'missing-group': lambda s: s['tests'].pop(0),
            'additional-failure': lambda s: s['tests'][0].update(passed=False),
            'native-status-forged': lambda s: s.update(native_tests_passed=True),
            'formal-status-forged': lambda s: s.update(passed=True),
            'wrong-run-error': lambda s: s.update(run_error='Different failure'),
            'wrong-case': lambda s: md(s)['markdown_performance']['cases'][-1].update(kind='unclosed-fence'),
            'missing-case-prefix': lambda s: md(s)['markdown_performance']['cases'].pop(0),
            'missing-stage-prefix': lambda s: md(s)['markdown_performance']['cases'][0]['stages'].pop(1),
            'wrong-operation': lambda s: stage(s).update(operation='insert'),
            'one-undo': lambda s: stage(s).update(undo_commands=1),
            'three-undos': lambda s: stage(s).update(undo_commands=3),
            'bool-undo': lambda s: stage(s).update(undo_commands=True),
            'wrong-length': lambda s: stage(s).update(length=999999),
            'dirty': lambda s: stage(s).update(dirty=True),
            'progress-dirty': lambda s: stage(s)['last_progress'].update(dirty=True),
            'no-tail-request': lambda s: stage(s)['last_progress'].update(tail_requested=False),
            'not-preserved': lambda s: md(s).update(source_bytes_preserved=False),
            'false-final-proof': lambda s: stage(s).update(last_probe={'styles_match': True}),
            'not-pending': lambda s: stage(s)['last_progress']['diagnostic'].update(pending=0),
            'wrong-phase': lambda s: stage(s)['last_progress']['diagnostic'].update(phase=4),
            'no-feed': lambda s: stage(s)['last_progress']['diagnostic'].update(feed=0),
            'short-deadline': lambda s: stage(s).update(wall_ms=30000),
            'long-deadline': lambda s: stage(s).update(wall_ms=60001),
            'bad-prefix-styles': lambda s: md(s)['markdown_performance']['cases'][0]['stages'][0]['last_probe'].update(styles_match=False),
            'bad-clock': lambda s: md(s)['markdown_performance']['clock'].update(monotonic=False),
            'wrong-binary': lambda s: md(s)['fixture_binary_sha256'].update({'ru_notepad.exe': '0' * 64}),
            'cleanup-unconfirmed': lambda s: md(s).update(cleanup_killed=False),
            'source-changed': lambda s: md(s)['markdown_performance']['cases'][-1].update(source_sha256='0' * 64),
        }
        for label, mutation in mutations.items():
            with self.subTest(label=label):
                self.f.summary = copy.deepcopy(original)
                mutation(self.f.summary)
                before = copy.deepcopy(self.f.summary)
                error_names = p.DEADLINES
                with self.assertRaises((RuntimeError, KeyError, TypeError, ValueError)):
                    self.validate()
                self.assertEqual(self.f.summary, before)
                self.assertIs(p.DEADLINES, error_names)

    def test_existing_explicit_deadline_policy_and_passed_case_are_not_relaxed(self):
        self.assertEqual(self.validate()['formal_acceptance'], 'passed')
        self.f.timeout(0, 0)
        self.assertEqual(self.validate()['formal_acceptance'], 'failed')

    def test_fake_pe_package_retains_original_evidence_and_delivery_inventory(self):
        self.known()
        before = copy.deepcopy(self.f.summary)
        with self.guard.installed():
            result = self.f.build()
        self.assertEqual(self.f.summary, before)
        self.assertFalse(result['original_acceptance_passed'])
        self.assertFalse(result['original_native_tests_passed'])
        native = self.f.evidence / 'native-acceptance.json'
        self.assertEqual(json.loads(native.read_text()), before)
        record = result['packages']['runtime']
        archive = self.f.ci / p.OUTPUT_NAME / record['name']
        provenance = {'workflow_commit': '9' * 40, 'files_sha256': {'synthetic': '8' * 64}}
        dest = self.f.root / 'delivery-test'
        delivered = policy.delivery_archive(p, archive, record, result, provenance, dest)
        with zipfile.ZipFile(dest / delivered['file_name']) as z:
            prefix = Path(delivered['file_name']).stem + '/'
            files = {n[len(prefix):]: z.read(n) for n in z.namelist()}
        self.assertEqual({n for n in files if n.endswith(('.exe', '.dll'))}, set(p.portable.RUNTIME_NAMES))
        self.assertFalse(any(n.endswith(('.log', '.ru', '.c', '.ps1')) for n in files))
        self.assertIn('正式自动验收失败', files['README.txt'].decode())
        self.assertIn(policy.PRODUCT_COMMIT, files['README.txt'].decode())
        self.assertEqual(json.loads(files['BUILD.json'])['formal_acceptance'], 'failed')
        self.assertFalse(json.loads(files['PREVIEW-POLICY.json'])['evidence_rewritten'])
        self.assertFalse(json.loads(files['PREVIEW-POLICY.json'])['acceptance_rerun'])
        self.assertEqual(hashlib.sha256((dest / delivered['file_name']).read_bytes()).hexdigest(), delivered['sha256'])

    def test_unknown_post_acceptance_evidence_is_rejected_before_clone(self):
        self.f.prepare()
        self.f.logs()
        (self.f.evidence / 'unknown-evidence.json').write_text('{}')
        with patch.object(policy.subprocess, 'run') as clone:
            with self.assertRaisesRegex(RuntimeError, 'Unknown evidence'):
                policy.stage_sealed_snapshot(p, self.f.root, self.f.root / 'copy', 'fake-objdump')
            clone.assert_not_called()


class DeliveryWorkflowTests(unittest.TestCase):
    def test_only_independent_preview_branch_runs_exact_product_and_original_acceptance(self):
        root = Path(__file__).absolute().parents[1]
        workflow = (root / '.github/workflows/windows.yml').read_text()
        self.assertIn('on:\n  push:\n    branches: [' + policy.BRANCH + ']\n', workflow)
        self.assertNotIn('  pull_request:', workflow)
        self.assertNotIn('  workflow_dispatch:', workflow)
        self.assertNotIn('continue-on-error', workflow)
        self.assertEqual(workflow.count("ref: ${{ '" + policy.PRODUCT_COMMIT + "' }}"), 2)
        self.assertEqual(workflow.count('ref: ' + policy.COMPILER_COMMIT), 2)
        self.assertIn('needs: helper-policy', workflow)
        self.assertIn('ref: ${{ github.sha }}\n          path: .ci/preview-policy', workflow)
        product = workflow.index('      - name: Build, run native tests, smoke the GUI, and package tested binaries')
        delivery = workflow.index('      - name: Package only the original sealed d964 snapshot')
        evidence = workflow.index('      - name: Upload bounded synthetic acceptance evidence')
        self.assertLess(product, delivery)
        self.assertLess(delivery, evidence)
        self.assertIn('./tools/windows_ci.ps1', workflow[product:delivery])
        self.assertIn('-RunAclTests', workflow[product:delivery])
        self.assertIn('if: always()', workflow[delivery:evidence])
        self.assertIn('build/windows-ci/delivery-preview/*.zip', workflow)
        self.assertIn('      - name: Require delivery policy negative controls\n        timeout-minutes: 3\n', workflow)
        self.assertNotIn('build/windows-ci/bin/*', workflow)
        self.assertNotIn('git push', workflow)

    def test_readme_does_not_misreport_unclosed_execution_or_manual_acceptance(self):
        provenance = {'workflow_commit': '9' * 40}
        result = {'timeout': {'kind': 'singleline', 'operation': 'undo', 'wall_ms': 30001}}
        text = policy.readme(result, provenance)
        self.assertIn('后续未闭合围栏用例未执行', text)
        result['timeout']['kind'] = 'unclosed-fence'
        self.assertNotIn('后续未闭合围栏用例未执行', policy.readme(result, provenance))
        self.assertIn('未闭合围栏用例未完成', policy.readme(result, provenance))
        self.assertIn('人工验收尚未完成', policy.readme({'timeout': None}, provenance))


if __name__ == '__main__':
    print('[preview-policy-controls] tests begin', flush=True)
    try:
        result = unittest.main(argv=[sys.argv[0], *rest], verbosity=2, exit=False)
        print('[preview-policy-controls] tests complete', flush=True)
        raise SystemExit(0 if result.result.wasSuccessful() else 1)
    finally:
        faulthandler.cancel_dump_traceback_later()
        print('[preview-policy-controls] traceback timer cancelled; exiting', flush=True)
