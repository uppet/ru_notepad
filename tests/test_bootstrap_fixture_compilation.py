"""Portable scheduling/process controls, never Windows compilation evidence."""
from concurrent.futures import CancelledError
from copy import deepcopy
from pathlib import Path
import inspect
import json
from contextlib import ExitStack
from types import SimpleNamespace
import tempfile
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import verify_bootstrap_recent_policies as fixtures
from bootstrap_provenance import InvalidProvenance

class FixtureCompilation(unittest.TestCase):
    def result(self, name, code=0):
        return subprocess.CompletedProcess([name],code,name.encode(),b'')

    def test_two_workers_and_all_compiles_precede_serial_execution(self):
        lock=threading.Lock();barrier=threading.Barrier(2)
        state={'active':0,'maximum':0};events=[];recorded=[]
        caller=threading.get_ident()
        def compile_one(name):
            with lock:
                state['active']+=1;state['maximum']=max(state['maximum'],state['active'])
                events.append(('start',name))
            barrier.wait(timeout=2)
            time.sleep(.005 if name%2 else .01)
            with lock:
                state['active']-=1;events.append(('end',name))
            return self.result(str(name))
        def record(name,result):
            self.assertEqual(threading.get_ident(),caller)
            recorded.append(name)
        fixtures.compile_fixture_jobs(list(range(6)),compile_one,record)
        self.assertEqual(state,{'active':0,'maximum':2})
        self.assertEqual(recorded,list(range(6)))
        for name in range(6):events.append(('execute',name))
        self.assertEqual([e[0] for e in events[-6:]],['execute']*6)
        self.assertEqual(len([e for e in events[:-6] if e[0]=='end']),6)

    def test_failure_stops_following_waves_and_joins_running_peer(self):
        barrier=threading.Barrier(2);finished=[];records=[]
        def compile_one(name):
            barrier.wait(timeout=2)
            if name=='b':time.sleep(.02)
            finished.append(name)
            return self.result(name,1 if name=='a' else 0)
        with self.assertRaises(InvalidProvenance):
            fixtures.compile_fixture_jobs(list('abcdef'),compile_one,lambda n,r:records.append(n))
        self.assertEqual(set(finished),{'a','b'})
        self.assertEqual(records,['a','b'])

    def test_worker_exception_and_timeout_are_fail_closed(self):
        for error in (ValueError('failure'),subprocess.TimeoutExpired(['a'],600,output=b'partial')):
            started=[];records=[]
            def compile_one(name):
                started.append(name)
                if name=='a':raise error
                return self.result(name)
            with self.assertRaises(InvalidProvenance):
                fixtures.compile_fixture_jobs(list('abcdef'),compile_one,lambda n,r:records.append((n,r)))
            self.assertTrue(set(started)<=set('ab'))
            self.assertEqual([n for n,r in records],['a','b'])
            self.assertIs(records[0][1],error)

    def test_queued_peer_cancellation_and_no_later_submission(self):
        first=Mock();first.result.return_value=self.result('a',1)
        second=Mock();second.result.side_effect=CancelledError()
        pool=Mock();pool.submit.side_effect=[first,second]
        executor=Mock();executor.__enter__=Mock(return_value=pool);executor.__exit__=Mock(return_value=False)
        records=[]
        with patch.object(fixtures,'ThreadPoolExecutor',return_value=executor) as factory:
            with self.assertRaises(InvalidProvenance):
                fixtures.compile_fixture_jobs(list('abcdef'),Mock(),lambda n,r:records.append(n))
        factory.assert_called_once_with(max_workers=2)
        self.assertEqual(pool.submit.call_count,2)
        second.cancel.assert_called()
        executor.__exit__.assert_called_once()
        self.assertEqual(records,['a','b'])

    def test_process_uses_same_environment_cwd_and_six_hundred_seconds(self):
        process=Mock(returncode=0);process.communicate.return_value=(b'out',b'err')
        env={'PATH':'fixed'}
        with patch.object(fixtures.subprocess,'Popen',return_value=process) as popen:
            result=fixtures.run_compile_process(['fixed','arguments'],cwd=Path('compiler'),env=env)
        popen.assert_called_once_with(['fixed','arguments'],cwd=Path('compiler'),env=env,
                                     stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        process.communicate.assert_called_once_with(timeout=600)
        self.assertEqual((result.returncode,result.stdout,result.stderr),(0,b'out',b'err'))

    def test_timeout_kills_tree_and_reaps_wrapper_preserving_output(self):
        timeout=subprocess.TimeoutExpired(['compiler'],600)
        process=Mock(pid=123,returncode=-1)
        process.communicate.side_effect=[timeout,(b'partial',b'diagnostic')]
        process.poll.return_value=None
        with patch.object(fixtures.subprocess,'Popen',return_value=process),patch.object(fixtures.subprocess,'run',return_value=self.result('taskkill')) as kill:
            with self.assertRaises(subprocess.TimeoutExpired) as caught:
                fixtures.run_compile_process(['compiler'],cwd='same',env={})
        kill.assert_called_once_with(['taskkill','/PID','123','/T','/F'],capture_output=True,timeout=30)
        process.kill.assert_called_once()
        self.assertEqual(process.communicate.call_args.kwargs,{'timeout':30})
        self.assertEqual((caught.exception.output,caught.exception.stderr),(b'partial',b'diagnostic'))

    def test_cleanup_failure_or_timeout_never_becomes_success(self):
        for cleanup in (self.result('taskkill',1),subprocess.TimeoutExpired(['taskkill'],30)):
            process=Mock(pid=123)
            process.poll.return_value=None
            process.communicate.side_effect=[subprocess.TimeoutExpired(['compiler'],600),(b'',b'')]
            kwargs={'side_effect':cleanup} if isinstance(cleanup,Exception) else {'return_value':cleanup}
            with patch.object(fixtures.subprocess,'Popen',return_value=process),patch.object(fixtures.subprocess,'run',**kwargs):
                with self.assertRaisesRegex(RuntimeError,'cleanup unconfirmed'):
                    fixtures.run_compile_process(['compiler'],cwd='same',env={})
            process.kill.assert_called_once()
            self.assertEqual(process.communicate.call_count,2)

    def test_policy_missing_extra_or_changed_budget_is_rejected(self):
        fixtures.validate_compile_policy(dict(fixtures.COMPILE_POLICY))
        variants=[None,{},dict(fixtures.COMPILE_POLICY,extra=1)]
        for key,value in fixtures.COMPILE_POLICY.items():
            for bad in (value+1,str(value),True):
                variants.append(dict(fixtures.COMPILE_POLICY,**{key:bad}))
        for bad in variants:
            with self.assertRaises(InvalidProvenance):fixtures.validate_compile_policy(bad)

    def test_passed_compile_receipt_rejects_contradictions_and_changed_timing(self):
        valid={'compile_returncode':0,'compile_timeout':False,
               'compile_timing':{'started':1.0,'finished':2.0,'elapsed_seconds':1.0}}
        fixtures.validate_compile_result(valid)
        for key in valid:
            bad=deepcopy(valid);del bad[key]
            with self.subTest(missing=key),self.assertRaises(InvalidProvenance):fixtures.validate_compile_result(bad)
        for key,values in {'compile_returncode':(1,-1,False,0.0,'0',None),
                           'compile_timeout':(True,0,None),
                           'compile_error':('',None,'failed'),
                           'compile_cleanup':(None,{}, {'returncode':0})}.items():
            for value in values:
                bad=deepcopy(valid);bad[key]=value
                with self.subTest(field=key,value=value),self.assertRaises(InvalidProvenance):fixtures.validate_compile_result(bad)
        for key in valid['compile_timing']:
            for value in (True,None,'1',-1,float('nan'),float('inf'),-float('inf')):
                bad=deepcopy(valid);bad['compile_timing'][key]=value
                with self.subTest(field=key,value=value),self.assertRaises(InvalidProvenance):fixtures.validate_compile_result(bad)
            bad=deepcopy(valid);del bad['compile_timing'][key]
            with self.assertRaises(InvalidProvenance):fixtures.validate_compile_result(bad)
        for timing in ({},None,dict(valid['compile_timing'],extra=1),
                       {'started':3,'finished':2,'elapsed_seconds':1},
                       {'started':1,'finished':2,'elapsed_seconds':2}):
            bad=deepcopy(valid);bad['compile_timing']=timing
            with self.assertRaises(InvalidProvenance):fixtures.validate_compile_result(bad)
        # Startup/cleanup overhead is not a new wall-time gate; communicate owns 600 seconds.
        fixtures.validate_compile_result(dict(valid,compile_timing={'started':0,'finished':601,'elapsed_seconds':601}))
        self.assertIn('validate_compile_result(row)',inspect.getsource(fixtures.validate_report))

    def test_timing_covers_actual_worker_execution_and_failure(self):
        for error in (None,ValueError('failed')):
            def compile_one(job):
                if error:raise error
                return self.result(job)
            with patch.object(fixtures.time,'monotonic',side_effect=[10.0,12.0]):
                if error:
                    with self.assertRaises(ValueError):fixtures.timed_compile(compile_one,'a')
                    result=error
                else:result=fixtures.timed_compile(compile_one,'a')
            self.assertEqual(result.compile_timing,dict(started=10.0,finished=12.0,elapsed_seconds=2.0))

    def test_keyboard_interrupt_is_recorded_after_peer_join_before_propagation(self):
        barrier=threading.Barrier(2);finished=[];records=[]
        def compile_one(name):
            barrier.wait(timeout=2)
            if name=='a':raise KeyboardInterrupt('cancel')
            time.sleep(.01);finished.append(name)
            return self.result(name)
        with self.assertRaises(KeyboardInterrupt):
            fixtures.compile_fixture_jobs(list('abcd'),compile_one,lambda n,r:records.append((n,r)))
        self.assertEqual(finished,['b'])
        self.assertEqual([n for n,r in records],['a','b'])
        self.assertIsInstance(records[0][1],KeyboardInterrupt)

    def test_already_exited_pid_is_not_tree_killed_and_original_timeout_output_survives(self):
        process=Mock(pid=123,returncode=0)
        process.poll.return_value=0
        process.communicate.side_effect=[subprocess.TimeoutExpired(['compiler'],600,output=b'original out',stderr=b'original err'),(b'',b'')]
        with patch.object(fixtures.subprocess,'Popen',return_value=process),patch.object(fixtures.subprocess,'run') as kill:
            with self.assertRaises(subprocess.TimeoutExpired) as caught:
                fixtures.run_compile_process(['compiler'],cwd='same',env={})
        kill.assert_not_called();process.kill.assert_not_called()
        self.assertEqual((caught.exception.output,caught.exception.stderr),(b'original out',b'original err'))
        self.assertEqual(caught.exception.cleanup,{'pid':123,'attempted':False,'returncode':None})

    def test_second_cleanup_timeout_preserves_partial_bytes_and_cleanup_error(self):
        process=Mock(pid=123);process.poll.return_value=None
        process.communicate.side_effect=[subprocess.TimeoutExpired(['compiler'],600,output=b'original'),
                                         subprocess.TimeoutExpired(['compiler'],30,stderr=b'cleanup')]
        with patch.object(fixtures.subprocess,'Popen',return_value=process),patch.object(fixtures.subprocess,'run',return_value=self.result('taskkill')):
            with self.assertRaisesRegex(RuntimeError,'cleanup did not finish') as caught:
                fixtures.run_compile_process(['compiler'],cwd='same',env={})
        self.assertEqual(caught.exception.stdout,b'original')
        self.assertEqual(caught.exception.stderr,b'cleanup')
        self.assertIn('error',caught.exception.cleanup)

    def test_actual_verify_compile_failure_never_calls_native_process(self):
        with tempfile.TemporaryDirectory() as directory,ExitStack() as stack:
            root=Path(directory)
            app={'source_pins':{'app_source':{'path':str(root/'app')},'ru_source':{'path':str(root/'ru')}},
                 'source_sha256':{'app_source':{},'ru_source':{}},'bootstrap':{'stage3_sha256':'fixed'},
                 'tool_paths':{},'tool_sha256':{}}
            config={'dependencies_receipt':str(root/'deps.json'),'app_receipt':str(root/'app.json')}
            stack.enter_context(patch.object(fixtures.sys,'platform','win32'))
            stack.enter_context(patch.object(fixtures.smoke,'validate_receipts',return_value={'app_receipt':app}))
            stack.enter_context(patch.object(fixtures,'validate_receipt',return_value={}))
            stack.enter_context(patch.object(fixtures.smoke,'read_json',return_value={'compiler':{'path':str(root/'stage3')}}))
            stack.enter_context(patch.object(fixtures,'sha',return_value='fixed'))
            stack.enter_context(patch.object(fixtures,'install_runtime_dependencies',return_value={}))
            spec=SimpleNamespace(loader=SimpleNamespace(exec_module=lambda module:None))
            stack.enter_context(patch.object(fixtures.importlib.util,'spec_from_file_location',return_value=spec))
            stack.enter_context(patch.object(fixtures.importlib.util,'module_from_spec',return_value=SimpleNamespace(llvm_environment=lambda:{})))
            stack.enter_context(patch.object(fixtures,'native_compile_command',side_effect=lambda ru,source,*args:['compile',str(source)]))
            process=Mock(returncode=1);process.communicate.return_value=(b'failure out',b'failure err')
            popen=stack.enter_context(patch.object(fixtures.subprocess,'Popen',return_value=process))
            native=stack.enter_context(patch.object(fixtures.subprocess,'run'))
            report=fixtures.verify(config,root/'out')
            native.assert_not_called()
            self.assertEqual(report['status'],'failed')
            self.assertLessEqual(popen.call_count,2)
            self.assertEqual(list(report['results']),list(fixtures.CASES))
            self.assertTrue(all(r['executed'] is False for r in report['results'].values()))
            saved=json.loads((root/'out/recent-fixtures.json').read_text())
            self.assertEqual(saved,report)
            self.assertEqual((root/'out/recent_files_policy.build.stderr.log').read_bytes(),b'failure err')

    def test_actual_verify_success_compiles_all_and_verifies_all_before_serial_native(self):
        with tempfile.TemporaryDirectory() as directory,ExitStack() as stack:
            root=Path(directory);out=root/'out';events=[];lock=threading.Lock()
            app={'source_pins':{'app_source':{'path':str(root/'app')},'ru_source':{'path':str(root/'ru')}},
                 'source_sha256':{'app_source':{},'ru_source':{}},'bootstrap':{'stage3_sha256':'fixed'},
                 'tool_paths':{},'tool_sha256':{},'target_triple':'fixed','data_layout':'fixed'}
            config={'dependencies_receipt':str(root/'deps.json'),'app_receipt':str(root/'app.json')}
            stack.enter_context(patch.object(fixtures.sys,'platform','win32'))
            stack.enter_context(patch.object(fixtures.smoke,'validate_receipts',return_value={'app_receipt':app}))
            stack.enter_context(patch.object(fixtures,'validate_receipt',return_value={}))
            stack.enter_context(patch.object(fixtures.smoke,'read_json',return_value={'compiler':{'path':str(root/'stage3')}}))
            stack.enter_context(patch.object(fixtures,'sha',return_value='fixed'))
            stack.enter_context(patch.object(fixtures,'install_runtime_dependencies',return_value={}))
            stack.enter_context(patch.object(fixtures,'validate_runtime_dependencies'))
            stack.enter_context(patch.object(fixtures,'validate_toolchain'))
            stack.enter_context(patch.object(fixtures,'validate_report'))
            spec=SimpleNamespace(loader=SimpleNamespace(exec_module=lambda module:None))
            stack.enter_context(patch.object(fixtures.importlib.util,'spec_from_file_location',return_value=spec))
            stack.enter_context(patch.object(fixtures.importlib.util,'module_from_spec',return_value=SimpleNamespace(llvm_environment=lambda:{})))
            stack.enter_context(patch.object(fixtures,'native_compile_command',side_effect=lambda ru,source,*args:['compile',str(source)]))
            def popen(command,**kwargs):
                name=Path(command[1]).stem
                process=Mock(returncode=0)
                def communicate(timeout):
                    self.assertEqual(timeout,600)
                    for suffix in ('.exe','.ll','.proof.json'):(out/(name+suffix)).write_bytes(name.encode())
                    with lock:events.append(('compiled',name))
                    return b'',b''
                process.communicate.side_effect=communicate
                return process
            stack.enter_context(patch.object(fixtures.subprocess,'Popen',side_effect=popen))
            def proof(*args,**kwargs):events.append(('proof',kwargs['source'].stem))
            stack.enter_context(patch.object(fixtures,'verify_proof',side_effect=proof))
            def native(command,**kwargs):
                name=Path(command[0]).stem
                self.assertEqual(kwargs['timeout'],60)
                self.assertEqual(len([e for e in events if e[0]=='compiled']),16)
                self.assertEqual(len([e for e in events if e[0]=='proof']),16)
                events.append(('execute',name))
                count=fixtures.CASES[name]
                return subprocess.CompletedProcess(command,0,('PASS: synthetic\n'*count+'TOTAL PASS: '+str(count)+'\n').encode(),b'')
            stack.enter_context(patch.object(fixtures.subprocess,'run',side_effect=native))
            report=fixtures.verify(config,out)
            self.assertEqual(report['status'],'passed',report.get('error'))
            self.assertEqual([name for kind,name in events if kind=='execute'],list(fixtures.CASES))
            self.assertTrue(all(row['executed'] for row in report['results'].values()))
            self.assertTrue(all('compile_timing' in row for row in report['results'].values()))

    def test_unique_outputs_fixed_inventory_and_unchanged_native_budget(self):
        source=inspect.getsource(fixtures.verify)
        self.assertIn('timeout=EXECUTE_TIMEOUT',source)
        self.assertEqual((fixtures.COMPILE_WORKERS,fixtures.COMPILE_TIMEOUT,fixtures.EXECUTE_TIMEOUT),(2,600,60))
        self.assertEqual(fixtures.SCHEMA,'ru-notepad-bootstrap-editor-fixtures-v7')
        self.assertEqual(len(fixtures.CASES),16)
        self.assertEqual(sum(fixtures.CASES.values()),2772)
        outputs=[]
        for name in fixtures.CASES:
            outputs.extend(name+suffix for suffix in ('.exe','.ll','.proof.json','.exe.metadata.c','.exe.frontend.ll','.exe.native-wrapper.json'))
        self.assertEqual(len(outputs),len(set(outputs)))
        compile_at=source.index('compile_fixture_jobs(jobs,compile_one,record_one)')
        proof_at=source.index('verify_proof(proof_data',compile_at)
        execute_at=source.index('ran=subprocess.run',proof_at)
        self.assertLess(compile_at,proof_at);self.assertLess(proof_at,execute_at)
        self.assertIn('for job in jobs:',source[proof_at:execute_at])
        self.assertIn('for key in (\'binary\',\'ir\',\'proof\'):smoke.verify_identity(row[key])',source)

if __name__=='__main__':unittest.main()
