import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import windows_smoke as s


class Smoke(unittest.TestCase):
    def test_only_initialize_windows_no_launch_or_input(self):
        with tempfile.TemporaryDirectory() as temp, contextlib.ExitStack() as stack:
            root=Path(temp)
            receipt=dict(archive_sha256=s.n.PINS['npp.8.9.8.1.portable.x64.zip'][1],executed=False,
                         files={'notepad++.exe':'a'*64,'doLocalConf.xml':'a'*64,'disableNppAutoUpdate.xml':'a'*64},
                         file_count=3,executable_sha256='a'*64)
            api=Mock()
            stack.enter_context(patch.object(s.sys,'argv',['windows_smoke.py',*sum(([flag,str(root)] for flag in ('--baseline','--compiler','--npp','--receipt')),[]),'--future-output',str(root/'future')]))
            for name in ('host_guard','checkout','verify_compiler','load_protocol'):
                stack.enter_context(patch.object(s.b,name))
            stack.enter_context(patch.object(s.b,'plain',side_effect=lambda p,**kw:p))
            stack.enter_context(patch.object(s.b,'under',side_effect=lambda p,n:p/n))
            stack.enter_context(patch.object(s.b,'sha',return_value='a'*64))
            stack.enter_context(patch.object(s.b,'read',return_value=receipt))
            stack.enter_context(patch.object(s.f,'closed_manifest'))
            stack.enter_context(patch.object(s.f,'load_ci',return_value=SimpleNamespace(Windows=api)))
            popen=stack.enter_context(patch.object(s.f.subprocess,'Popen',side_effect=AssertionError('no launch')))
            output=io.StringIO()
            with contextlib.redirect_stdout(output): s.main()
            api.assert_called_once_with()
            self.assertEqual(api.return_value.mock_calls,[])
            popen.assert_not_called()
            self.assertEqual(output.getvalue(),'COMPARISON_WINDOWS_SMOKE=1\n')
