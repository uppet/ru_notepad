#!/usr/bin/env python3
"""Numeric diagnostic controls; mocked child commands never execute."""
import contextlib, io, subprocess, types, unittest
from unittest.mock import patch
import test_markdown_owned_profile as controls

class Controls(unittest.TestCase):
    def run_case(self, fail_at=None, error=None, success=True):
        out=io.StringIO(); calls=[]
        def run(args,**kwargs):
            calls.append(args)
            if len(calls)==fail_at: raise error
        result=types.SimpleNamespace(wasSuccessful=lambda:success)
        with patch.object(controls,'os',types.SimpleNamespace(name='nt')), patch.object(controls.unittest,'TextTestRunner') as runner, patch.object(controls.subprocess,'run',side_effect=run), patch.object(controls.subprocess,'check_output',return_value='RU_MARKDOWN_PHASE_PROFILE {"valid":true,"complete":1,"depth":0}\n'), patch('sys.argv',['controls']), contextlib.redirect_stdout(out):
            runner.return_value.run.return_value=result
            code=controls.main()
        return code,out.getvalue()
    def test_full_stages(self):
        code,text=self.run_case();self.assertEqual(code,0)
        for n in range(1,8): self.assertIn(f'MARKDOWN_OWNED_CONTROL_STAGE={n}\n',text)
        self.assertIn('MARKDOWN_OWNED_CONTROL_COMPLETE=8\n',text)
    def test_python_failure(self):
        code,text=self.run_case(success=False);self.assertEqual(code,1)
        self.assertEqual(text,'MARKDOWN_OWNED_CONTROL_STAGE=1\nMARKDOWN_OWNED_CONTROL_EXIT=1\n')
    def test_native_failure_stages(self):
        for call,stage in ((1,2),(2,3),(3,5),(4,6),(5,7)):
            with self.subTest(stage=stage):
                code,text=self.run_case(call,subprocess.CalledProcessError(7,'PRIVATE_PATH'))
                self.assertEqual(code,1);self.assertTrue(text.endswith(f'MARKDOWN_OWNED_CONTROL_STAGE={stage}\nMARKDOWN_OWNED_CONTROL_EXIT=7\n'))
                self.assertNotIn('PRIVATE',text)
    def test_timeout(self):
        code,text=self.run_case(1,subprocess.TimeoutExpired('PRIVATE',1))
        self.assertEqual(code,1);self.assertTrue(text.endswith('EXIT=124\n'));self.assertNotIn('PRIVATE',text)
    def test_unknown_exception(self):
        code,text=self.run_case(1,ValueError('PRIVATE'))
        self.assertEqual(code,1);self.assertTrue(text.endswith('EXIT=125\n'));self.assertNotIn('PRIVATE',text)
    def test_windows_unsigned_crash_exit(self):
        code,text=self.run_case(4,subprocess.CalledProcessError(3221225477,'PRIVATE'))
        self.assertEqual(code,1);self.assertTrue(text.endswith('EXIT=3221225477\n'))

if __name__=='__main__':unittest.main()
