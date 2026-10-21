#!/usr/bin/env python3
"""Real adapted observer methods with fake clocks/native calls; not Windows proof."""
import copy, ctypes, inspect, unittest, sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import windows_ci as ci
import markdown_edit_observers as adapter

class Controls(unittest.TestCase):
    def setUp(self):self.objects=adapter.adapted(ci)
    def observer(self,now):
        api=SimpleNamespace(scalar=lambda *a:0,responsive=lambda *a:None)
        record=ci.gui_ru_observer_record()
        return api,record,self.objects['GuiRuObserver'](api,record,0,lambda:now[0])
    def test_late_and_hard_bound_actual_wrap(self):
        now=[31.];api,r,o=self.observer(now)
        with o:
            api.scalar(1,2);now[0]=120.;api.scalar(1,2);now[0]=120.001
            with self.assertRaisesRegex(RuntimeError,'120 seconds'):api.scalar(1,2)
        self.assertEqual(r['scalar_calls'],2)
    def test_actual_481_snapshots_and_32_messages(self):
        now=[0.];api,r,o=self.observer(now)
        with o:
            for i in range(481):
                now[0]=i*.25;o.snapshot(lambda:api.scalar(1,2))
            now[0]=120.25
            with self.assertRaisesRegex(RuntimeError,'snapshot count'):o.snapshot(lambda:False)
        self.assertEqual(r['snapshot_count'],481)
        now=[31.];api,r,o=self.observer(now)
        with o:
            def too_many():
                for _ in range(33):api.scalar(1,2)
            with self.assertRaisesRegex(RuntimeError,'32 synchronous'):o.snapshot(too_many)
        self.assertEqual(r['max_snapshot_messages'],32)
    def test_actual_sampling_frequency_unchanged(self):
        now=[31.];api,r,o=self.observer(now)
        with o:
            api.responsive(1);now[0]+=.049
            with self.assertRaisesRegex(RuntimeError,'fixed frequency'):api.responsive(1)
            o.snapshot(lambda:api.scalar(1,2));now[0]+=.249
            with self.assertRaisesRegex(RuntimeError,'fixed frequency'):o.snapshot(lambda:False)
    def records(self):
        now=[0.];api,r,o=self.observer(now)
        memory=object.__new__(self.objects['MarkdownProcessMemory']);memory.record=ci.markdown_memory_record()
        memory.process=SimpleNamespace(_handle=123);memory.started=0;memory.clock=lambda:now[0]
        def query(handle,pointer,size):
            c=ctypes.cast(pointer,ctypes.POINTER(ci.MarkdownMemoryCounters)).contents
            c.WorkingSetSize=100;c.PeakWorkingSetSize=200;return 1
        memory.query=query
        with o:
            for i in range(2401):
                now[0]=i*.05;api.responsive(1)
                if i%5==0:
                    def snapshot():memory.sample();api.scalar(1,2);return i==2400
                    o.snapshot(snapshot)
        return r,memory
    def test_real_capacity_records_and_validators(self):
        r,m=self.records();self.assertEqual(len(m.record['samples']),481)
        self.objects['validate_gui_ru_observer'](r,120000,2401)
        self.objects['validate_markdown_memory'](m.record,r,120000)
        with self.assertRaisesRegex(RuntimeError,'snapshot count'):m.sample()
        with self.assertRaises(RuntimeError):ci.validate_gui_ru_observer(r,120000,2401)
        with self.assertRaises(RuntimeError):ci.validate_markdown_memory(m.record,r,120000)
        too=copy.deepcopy(r);too['snapshots'].append(too['snapshots'][-1]);too['snapshot_count']+=1
        with self.assertRaises(RuntimeError):self.objects['validate_gui_ru_observer'](too,120000,2401)
        too=copy.deepcopy(r);too['response_starts_ms'].append(120050);too['wm_null_calls']+=1;too['sendmessage_calls']+=1
        with self.assertRaises(RuntimeError):self.objects['validate_gui_ru_observer'](too,120050,2402)
        too=copy.deepcopy(m.record);too['samples'].append(too['samples'][-1]);too['sample_count']+=1
        with self.assertRaises(RuntimeError):self.objects['validate_markdown_memory'](too,r,120000)
    def test_source_object_drift(self):
        with patch('inspect.getsource',return_value='class GuiRuObserver: pass'),self.assertRaisesRegex(ValueError,'object_changed'):
            adapter.adapted(ci)
    def test_module_drift(self):
        with patch.object(adapter,'MODULE_SHA256','0'*64),self.assertRaisesRegex(ValueError,'module_changed'):
            adapter.adapted(ci)
    def test_whitelist_count_drift(self):
        with patch.dict(adapter.POLICY,GuiRuObserver={'snapshot':2}),self.assertRaisesRegex(ValueError,'replacement_mismatch'):
            adapter.adapted(ci)
    def test_original_objects_unchanged(self):
        for name in adapter.OBJECT_SHA256:
            self.assertIsNot(self.objects[name],getattr(ci,name))
        self.assertEqual(ci.GUI_RU_TIMER_TIMEOUT_SECONDS,30)
        self.assertEqual(ci.GUI_RU_SNAPSHOT_MESSAGE_LIMIT,32)

class OwnedLoaderControls(unittest.TestCase):
    def load(self):
        import run_markdown_phase_profile as base
        return base.load_ci(Path(ci.__file__).resolve().parents[1])
    def test_real_loader_adapter_and_stage_construction(self):
        import run_markdown_edit_profile as edit
        for _ in range(2):
            owned=self.load();name=owned.__name__
            self.assertNotIn(name,sys.modules)
            original={key:getattr(owned,key) for key in adapter.OBJECT_SHA256}
            objects=adapter.adapted(owned)
            stage=edit.diagnostic_stage(owned,{'product_gate_failed':False})
            self.assertTrue(callable(stage));self.assertEqual(set(objects),set(adapter.OBJECT_SHA256))
            self.assertNotIn(name,sys.modules)
            self.assertTrue(all(getattr(owned,key) is value for key,value in original.items()))
            self.assertEqual(owned.GUI_MARKDOWN_TIMEOUT_SECONDS,30)
    def test_collision_never_overwrites_existing_module(self):
        owned=self.load();sentinel=object()
        with patch.dict(sys.modules,{owned.__name__:sentinel}):
            with self.assertRaisesRegex(ValueError,'module_collision'):adapter.adapted(owned)
            self.assertIs(sys.modules[owned.__name__],sentinel)
    def test_inspection_failure_removes_temporary_registration(self):
        owned=self.load()
        with patch('inspect.getsource',side_effect=TypeError('PRIVATE')):
            with self.assertRaises(TypeError):adapter.adapted(owned)
        self.assertNotIn(owned.__name__,sys.modules)
    def test_same_registered_module_preserved(self):
        owned=self.load()
        with patch.dict(sys.modules,{owned.__name__:owned}):
            adapter.adapted(owned)
            self.assertIs(sys.modules[owned.__name__],owned)
    def test_registration_replacement_is_not_deleted(self):
        owned=self.load();sentinel=object()
        def replace(original):
            sys.modules[owned.__name__]=sentinel
            return 'PRIVATE'
        with patch.dict(sys.modules):
            with patch('inspect.getsource',side_effect=replace):
                with self.assertRaisesRegex(ValueError,'module_replaced'):adapter.adapted(owned)
            self.assertIs(sys.modules[owned.__name__],sentinel)
    def test_unrelated_object_identity_rejected(self):
        owned=self.load();owned.GuiRuObserver=ci.GuiRuObserver
        with self.assertRaisesRegex(ValueError,'module_identity'):adapter.adapted(owned)
        self.assertNotIn(owned.__name__,sys.modules)

if __name__=='__main__':unittest.main(verbosity=2)
