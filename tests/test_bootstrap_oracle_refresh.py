"""Fail-closed pin and source controls; no synthetic analysis acceptance."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import refresh_language_native_oracle as oracle

class RefreshOracleTests(unittest.TestCase):
    def test_exact_commit_tree_cleanliness_and_analyzer_are_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'rulang').mkdir()
            (root/'rulang/native_c.py').write_bytes(b'analyzer')
            with patch.object(oracle,'ANALYZER_SHA256',oracle.sha(b'analyzer')):
                good=[oracle.CORE_COMMIT,oracle.CORE_TREE,'']
                with patch.object(oracle.subprocess,'check_output',side_effect=good):
                    oracle.verify_compiler(root)
                for answers in (["0"*40], [oracle.CORE_COMMIT,"0"*40],
                                [oracle.CORE_COMMIT,oracle.CORE_TREE,'?? unexpected.py']):
                    with self.subTest(answers=answers),patch.object(oracle.subprocess,'check_output',side_effect=answers):
                        with self.assertRaises(ValueError):oracle.verify_compiler(root)
                (root/'rulang/native_c.py').write_bytes(b'tampered')
                with patch.object(oracle.subprocess,'check_output',side_effect=good):
                    with self.assertRaisesRegex(ValueError,'analyzer pin'):oracle.verify_compiler(root)

    def test_source_change_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'main.ru';source.write_bytes(b'original')
            inputs={str(source):oracle.sha(source.read_bytes())}
            oracle.verify_sources(inputs)
            source.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'source changed'):oracle.verify_sources(inputs)

    def test_default_first_explicit_fallback_and_limit_restoration(self):
        # Resolve the host drive on Windows before checking source containment.
        root=Path(tempfile.gettempdir()).resolve()/'oracle-app'
        core=Path(tempfile.gettempdir()).resolve()/'oracle-core'
        class AnalysisError(Exception):
            source_name=str(root/'src/main.ru');line=3;col=5
        def scenario(allowed, fail_retry=False, message='原生签名静态分析超过复杂度上限'):
            calls=[]
            native=SimpleNamespace(MAX_ANALYSIS_STEPS=oracle.DEFAULT_BUDGET)
            def plan(graph, *, diagnostics):
                limit=native.MAX_ANALYSIS_STEPS;calls.append(limit)
                complete=limit==oracle.DEVELOPMENT_BUDGET and not fail_retry
                diagnostics({'completed':complete, 'steps':300000 if complete else limit+1,
                             'step_limit':limit, 'modules':1,'signatures':1,
                             'function_evaluations':2,'summary_hits':3})
                if not complete:raise AnalysisError(message)
                return SimpleNamespace(_steps=300000)
            native.NativeCPlan=plan
            try:
                result=oracle.analyze(native,{},root,core,AnalysisError,allowed)
                self.assertEqual(result[1]['source'],'src/main.ru')
                self.assertEqual(result[2],oracle.DEVELOPMENT_BUDGET)
            finally:
                self.assertEqual(native.MAX_ANALYSIS_STEPS,oracle.DEFAULT_BUDGET)
                self.assertEqual(calls,[oracle.DEFAULT_BUDGET,oracle.DEVELOPMENT_BUDGET]
                                 if allowed and message.startswith('原生签名静态分析超过复杂度上限')
                                 else [oracle.DEFAULT_BUDGET])
        scenario(True)
        with self.assertRaises(AnalysisError):scenario(False)
        with self.assertRaises(AnalysisError):scenario(True,fail_retry=True)
        with self.assertRaises(ValueError):scenario(True,message='unresolved ABI')

    def test_scope_and_pin_match_consumers(self):
        import verify_bootstrap_application_oracle as validator
        import compile_bootstrap_native as native
        self.assertEqual(oracle.SCOPE,validator.SCOPE)
        self.assertEqual(oracle.DEFAULT_SCOPE,validator.DEFAULT_SCOPE)
        self.assertEqual((oracle.CORE_COMMIT,oracle.CORE_TREE),(native.CORE_COMMIT,native.CORE_TREE))
        self.assertEqual(oracle.DEFAULT_BUDGET,200000)

if __name__=='__main__':unittest.main()
