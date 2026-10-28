import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('profile',ROOT/'profile_stage3_markdown.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
POLICY=ROOT/'markdown_policy.ru'

class Contracts(unittest.TestCase):
    def test_fixed_input_and_full_expected(self):
        data=m.fixture(); self.assertEqual(len(data),1000000)
        self.assertEqual(m.digest(data),m.INPUT_SHA)
        self.assertEqual(m.digest(m.expected_output('policy')),'552792717ae705dc700f06d052b4754cd2eaa54e25f756860ce404940ff11f26')
        entries=m.generated_entries()
        self.assertEqual(entries['policy.ru'].split('态 取 模')[0],entries['control.ru'].split('总 取 0')[0].removesuffix('\n'))
        self.assertIn("模 其 喂入",entries['policy.ru']);self.assertNotIn('其 喂入',entries['control.ru'])
        self.assertEqual(m.ORDER,('policy','control')*3);self.assertEqual(m.PROCESS_TIMEOUT,60)

    def test_strict_outputs(self):
        for kind in ('policy','control'):
            expected=m.expected_output(kind)
            m.validate_output(kind,expected,b'',0)
            m.validate_output(kind,expected.replace(b'\n',b'\r\n'),b'',0)
            for bad in (expected[:-1],expected+b'x',expected.replace(b'1000000',b'1000001'),b''):
                with self.assertRaises(ValueError):m.validate_output(kind,bad,b'',0)
            with self.assertRaises(ValueError):m.validate_output(kind,expected,b'warning',0)
            with self.assertRaises(ValueError):m.validate_output(kind,expected,b'',1)
        with self.assertRaises(ValueError):m.expected_output('extra')

    def test_prepare_identity_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); policy=root/'policy';policy.write_bytes(POLICY.read_bytes())
            manifest=m.prepare(policy,root/'prepared')
            self.assertFalse(manifest['accepted']);self.assertEqual(manifest['status'],'NOT_ACCEPTED')
            self.assertEqual(m.validate_sources(root/'prepared'),manifest['sources'])
            with self.assertRaises(FileExistsError):m.prepare(policy,root/'prepared')
            for name in m.SOURCE_NAMES:
                p=root/'prepared'/name;raw=p.read_bytes();p.write_bytes(raw+b' ')
                with self.assertRaises(ValueError):m.validate_sources(root/'prepared')
                p.write_bytes(raw)
            policy.write_bytes(b'changed')
            with self.assertRaises(ValueError):m.prepare(policy,root/'wrong')
            link=root/'link';link.symlink_to(root/'prepared/policy.ru')
            with self.assertRaises(ValueError):m.identity(link)

    def test_cpu_unavailable_not_zero(self):
        with patch.object(m.sys,'platform','linux'):
            result=m.process_cpu(object())
        self.assertFalse(result['available']);self.assertNotIn('total_cpu_ms',result)

    def test_cpu_owned_handle_filetime_units(self):
        class Query:
            def __call__(self,handle,*values):
                self.handle=handle
                for target,value in zip(values,[999,888,10000,20000]):
                    target._obj.dwLowDateTime=value;target._obj.dwHighDateTime=0
                return 1
        q=Query();kernel=type('Kernel',(),{'GetProcessTimes':q})();process=type('Process',(),{'_handle':123})()
        with patch.object(m.sys,'platform','win32'),patch.object(m.ctypes,'WinDLL',return_value=kernel,create=True):
            row=m.process_cpu(process)
        self.assertEqual(q.handle,123);self.assertEqual(row['total_cpu_ms'],3)
        self.assertEqual(row['kernel_100ns'],10000);self.assertEqual(row['user_100ns'],20000)

    def test_run_one_success_and_wrong_output(self):
        class Fake:
            returncode=0
            def wait(self,timeout):return 0
            def poll(self):return 0
        for valid in (True,False):
            with tempfile.TemporaryDirectory() as t:
                def popen(*args,**kwargs):
                    kwargs['stdout'].write(m.expected_output('policy') if valid else b'wrong')
                    kwargs['stdout'].flush()
                    return Fake()
                with patch.object(m.subprocess,'Popen',side_effect=popen),patch.object(m,'process_cpu',return_value={'available':False}):
                    row=m.run_one('policy',Path(t)/'fake.exe',Path(t)/'out')
                self.assertTrue(row['completed']);self.assertEqual(row['validated'],valid)
                self.assertIn('wall_seconds',row);self.assertNotIn('total_cpu_ms',row['cpu'])

    def test_oversized_output_is_not_hashed(self):
        class Fake:
            returncode=0
            def wait(self,timeout):return 0
            def poll(self):return 0
        with tempfile.TemporaryDirectory() as t:
            def popen(*args,**kwargs):
                kwargs['stdout'].write(b'x'*65537);kwargs['stdout'].flush();return Fake()
            with patch.object(m.subprocess,'Popen',side_effect=popen),patch.object(m,'process_cpu',return_value={'available':False}),patch.object(m,'identity',side_effect=AssertionError('must check size before hash')):
                row=m.run_one('policy',Path(t)/'fake.exe',Path(t)/'out')
            self.assertFalse(row['validated']);self.assertEqual(row['stdout_size'],65537)
            self.assertEqual(row['error_type'],'ValueError');self.assertNotIn('stdout',row)

    def bundle(self,t):
        root=Path(t);prepared=root/'prepared';m.prepare(POLICY,prepared)
        binaries={k:root/(k+'.exe') for k in ('policy','control')}
        for p in binaries.values():p.write_bytes(b'unit mock EXE boundary')
        builds={k:{'binary':m.identity(p),'native_wrapper_validated':True} for k,p in binaries.items()}
        return root,prepared,binaries,builds

    def test_fixed_six_runs_no_acceptance(self):
        with tempfile.TemporaryDirectory() as t:
            root,prepared,binaries,builds=self.bundle(t)
            def row(kind,*a):return {'kind':kind,'validated':True,'completed':True,'cpu':{'available':False}}
            with patch.object(m.sys,'platform','win32'),patch.object(m,'run_one',side_effect=row) as run:
                report=m.measure(prepared,binaries,root/'evidence',builds)
            self.assertEqual([c.args[0] for c in run.call_args_list],list(m.ORDER))
            self.assertTrue(report['diagnostic_completed']);self.assertTrue(report['all_outputs_validated'])
            self.assertFalse(report['accepted']);self.assertEqual(report['status'],'NOT_ACCEPTED')
            self.assertTrue((root/'evidence/diagnostic.json').exists())

    def test_failure_stops_without_resample(self):
        with tempfile.TemporaryDirectory() as t:
            root,prepared,binaries,builds=self.bundle(t)
            with patch.object(m.sys,'platform','win32'),patch.object(m,'run_one',return_value={'validated':False,'timed_out':True}) as run:
                report=m.measure(prepared,binaries,root/'evidence',builds)
            self.assertEqual(run.call_count,1);self.assertFalse(report['diagnostic_completed']);self.assertEqual(len(report['runs']),1)

    def test_identity_drift_and_build_precondition(self):
        with tempfile.TemporaryDirectory() as t:
            root,prepared,binaries,builds=self.bundle(t)
            builds['policy']['native_wrapper_validated']=False
            with patch.object(m.sys,'platform','win32'),self.assertRaises(ValueError):m.measure(prepared,binaries,root/'bad',builds)
            builds['policy']['native_wrapper_validated']=True
            def mutate(*args):binaries['policy'].write_bytes(b'changed');return {'validated':True}
            with patch.object(m.sys,'platform','win32'),patch.object(m,'run_one',side_effect=mutate) as run:
                report=m.measure(prepared,binaries,root/'evidence',builds)
            self.assertEqual(run.call_count,1);self.assertFalse(report['binaries_unchanged']);self.assertFalse(report['all_outputs_validated'])

    def test_owned_process_timeout_cleanup_and_env(self):
        class Fake:
            returncode=None
            def wait(self,timeout):
                if self.returncode is None:raise subprocess.TimeoutExpired('mock',timeout)
                return self.returncode
            def kill(self):self.returncode=-9
            def poll(self):return self.returncode
        process=Fake()
        with tempfile.TemporaryDirectory() as t,patch.dict(m.os.environ,{'GH_TOKEN':'not-secret-unit','GITHUB_TOKEN':'not-secret-unit'}),patch.object(m.subprocess,'Popen',return_value=process) as popen,patch.object(m,'process_cpu',return_value={'available':False}):
            record=m.run_one('policy',Path(t)/'fake.exe',Path(t)/'out')
            self.assertTrue(record['timed_out']);self.assertFalse(record['validated']);self.assertEqual(process.returncode,-9)
            self.assertNotIn('GH_TOKEN',popen.call_args.kwargs['env']);self.assertNotIn('GITHUB_TOKEN',popen.call_args.kwargs['env'])

if __name__=='__main__':unittest.main()
