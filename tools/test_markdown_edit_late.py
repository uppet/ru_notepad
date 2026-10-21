#!/usr/bin/env python3
"""Portable exact-source diagnostic deadline adapter tests, not Windows evidence."""
import inspect
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import windows_ci as ci
import run_markdown_edit_profile as edit

class LateControls(unittest.TestCase):
    def run_stage(self,finish,*,hard=120,error=None,final_cost=0,real_observer=False):
        gate={'product_gate_failed':False};now=[0.0];stage={};kind='unclosed-fence';operation='open'
        original=ci.gui_markdown_fixture(kind)[0];expected,probes,folds=ci.markdown_expected(kind,operation)
        class Memory:
            def __init__(self,*args):pass
            def sample(self):pass
        class Observer:
            def __init__(self,*args):pass
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def snapshot(self,callback):
                complete=callback()
                if complete:now[0]+=final_cost
                return complete
        class Api:
            def editor(self,h):return 2
            def control(self,h,i):return 3
            def no_dialog(self,p):
                if now[0]>=hard:raise RuntimeError('owned_hard_deadline')
                if error:raise RuntimeError(error)
            def responsive(self,h):pass
            def verify_owned_handles(self,*args):pass
            def text(self,h):return path.name+' · ru_notepad'
            def markdown_status(self,h):
                done=now[0]>=finish
                return ('Ln 1 UTF-8 Markdown' if done else 'Folding Markdown...')+(
                  ' [MDP2 seq=2 via=%d id=2 gen=3 rev=0 phase=%d pending=%d length=%d feed=%d published=47104 tick=123 work_us=100000 gap_us=200000 bulkCalls=736 bulkLines=47104 fallbackBatches=0 directCalls=0 directLines=0 maxPlanBytes=1056 bulkUs=1234 ownedBufferBytes=1088 metric_valid=1]' %
                  (1 if done else 0,4 if done else 1,0 if done else 1,len(expected),len(expected) if done else 47018))
            def scalar(self,h,msg,wparam=0,lparam=0):
                if msg in (2006,2028):return len(expected)
                if msg==2159:return 0
                if msg==2010:return next((p['style'] for p in probes if p['offset']<=wparam<p['offset']+p['length']),0)
                if msg==2223:return 0x2000 if next((p['header'] for p in folds if p['line']==wparam),False) else 0
                if msg==2007:return expected[wparam]
                if msg==4002:return 98
                return 0
        def sleep(seconds):
            if real_observer:now[0]+=seconds
            else:now[0]=min(finish,31,hard) if now[0]==0 else (hard if finish==float('inf') else now[0]+.25)
        from markdown_edit_observers import adapted
        observer_type=adapted(ci)['GuiRuObserver'] if real_observer else Observer
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'fixture.md';path.write_bytes(original)
            with patch.object(ci,'PerformanceClock',return_value=lambda:now[0]),patch('markdown_edit_observers.adapted',return_value={'MarkdownProcessMemory':Memory,'GuiRuObserver':observer_type}),patch.object(ci.time,'sleep',side_effect=sleep):
                adapted=edit.diagnostic_stage(ci,gate)
                try:adapted(Api(),SimpleNamespace(pid=123,poll=lambda:None),1,path,kind,operation,stage,lambda:None)
                except RuntimeError as exc:return gate,stage,str(exc)
        return gate,stage,None
    def test_full_stage_with_real_adapted_observer_finishes_late(self):
        gate,stage,error=self.run_stage(31,real_observer=True)
        self.assertIsNone(error);self.assertTrue(gate['product_gate_failed'])
        self.assertGreater(stage['observer']['scalar_calls'],0)
        self.assertGreater(stage['observer']['snapshot_count'],121)
        self.assertEqual(stage['observer']['wm_null_calls'],stage['probes'])
        self.assertTrue(stage['observer']['snapshots'][-1]['final'])
        from markdown_edit_observers import adapted
        adapted(ci)['validate_gui_ru_observer'](stage['observer'],stage['wall_ms'],stage['probes'])

    def test_exact_30_boundary_not_failed(self):
        gate,stage,error=self.run_stage(30)
        self.assertIsNone(error);self.assertFalse(gate['product_gate_failed']);self.assertEqual(stage['wall_ms'],30000)
    def test_31_late_complete_keeps_product_failure(self):
        gate,stage,error=self.run_stage(31)
        self.assertIsNone(error);self.assertTrue(gate['product_gate_failed']);self.assertEqual(stage['wall_ms'],31000)
        self.assertEqual(stage['last_progress']['diagnostic']['pending'],0)
    def test_final_proof_alone_crosses_gate(self):
        gate,stage,error=self.run_stage(30,final_cost=1)
        self.assertIsNone(error);self.assertTrue(gate['product_gate_failed']);self.assertEqual(stage['wall_ms'],31000)
    def test_120_incomplete_hard_bound(self):
        gate,stage,error=self.run_stage(float('inf'))
        self.assertEqual(error,'owned_hard_deadline');self.assertTrue(gate['product_gate_failed'])
        # The hard guard terminates before any later probe can manufacture completion.
        self.assertEqual(stage['wall_ms'],120000);self.assertEqual(stage['last_progress']['diagnostic']['pending'],1)
    def test_non_deadline_error_preserved(self):
        gate,stage,error=self.run_stage(31,error='synthetic_native_failure')
        self.assertEqual(error,'synthetic_native_failure');self.assertFalse(gate['product_gate_failed'])
    def test_source_file_hash_drift(self):
        with patch.object(edit.base,'digest',return_value='0'*64),self.assertRaisesRegex(Exception,'edit_stage_source_changed'):
            edit.diagnostic_stage(ci,{})
    def test_replacement_count_drift(self):
        source=inspect.getsource(ci.run_gui_markdown_stage)
        source=source.replace('Markdown GUI final proof exceeded its original 30-second deadline','changed failure')
        with patch('inspect.getsource',return_value=source),self.assertRaisesRegex(Exception,'edit_stage_adapter_mismatch'):
            edit.diagnostic_stage(ci,{})
    def test_same_messages_function_body_drift(self):
        source=inspect.getsource(ci.run_gui_markdown_stage).replace("next_response = next_snapshot = 0.0", "next_response = next_snapshot = 1.0")
        with patch('inspect.getsource',return_value=source),self.assertRaisesRegex(Exception,'edit_stage_function_changed'):
            edit.diagnostic_stage(ci,{})
    def test_product_function_untouched(self):
        source=inspect.getsource(ci.run_gui_markdown_stage);edit.diagnostic_stage(ci,{})
        self.assertEqual(inspect.getsource(ci.run_gui_markdown_stage),source);self.assertEqual(ci.GUI_MARKDOWN_TIMEOUT_SECONDS,30)

if __name__=='__main__':unittest.main(verbosity=2)
