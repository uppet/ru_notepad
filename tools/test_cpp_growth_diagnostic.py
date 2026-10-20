#!/usr/bin/env python3
"""Parser rejection and manual workflow isolation controls; no Windows claims."""
import unittest
import itertools
import ast
import zipfile
from pathlib import Path
from run_cpp_growth_diagnostic import validate_measurements, validate_trigger, ONE_SHOT_TITLE

ROOT = Path(__file__).resolve().parents[1]
class Controls(unittest.TestCase):
    def setUp(self):
        keys = {(c, s, i) for c in (1, 2) for s in range(7) for i in (1,2,3,4,5,6,7,8,10)}
        keys |= {(c, 1, 9) for c in (1,2)}
        keys |= {(c, s, 11) for c in (1,2) for s in (0,1,3,4,5,6)}
        keys |= {(c, 4, i) for c in (1,2) for i in (12,13)}
        self.rows = [f'GROWTH {c} {s} {i} 0' for c,s,i in sorted(keys)]
        self.text = '\n'.join(self.rows + ['GROWTH_COMPLETE 2']) + '\n'
    def test_complete_measurements(self):
        self.assertEqual(len(validate_measurements(self.text, '')), 144)
    def test_missing_field(self):
        with self.assertRaises(RuntimeError): validate_measurements('\n'.join(self.rows[1:] + ['GROWTH_COMPLETE 2']), '')
    def test_duplicate_field(self):
        with self.assertRaises(RuntimeError): validate_measurements(self.rows[0]+'\n'+self.text, '')
    def test_extra_field(self):
        with self.assertRaises(RuntimeError): validate_measurements('GROWTH 1 1 99 0\n'+self.text, '')
    def test_non_numeric(self):
        with self.assertRaises(RuntimeError): validate_measurements(self.text.replace(self.rows[0], 'GROWTH 1 0 1 NaN'), '')
    def test_bad_terminator(self):
        with self.assertRaises(RuntimeError): validate_measurements(self.text.replace('GROWTH_COMPLETE 2', 'GROWTH_COMPLETE 1'), '')
    def test_stderr_rejected(self):
        with self.assertRaises(RuntimeError): validate_measurements(self.text, 'error')
    def test_manual_isolation(self):
        workflow = (ROOT/'.github/workflows/windows.yml').read_text()
        job = workflow.split('  cpp-growth-diagnostic:\n', 1)[1]
        mode = "((github.event_name == 'workflow_dispatch' && inputs.syntax_growth_diagnostic) || (github.event_name == 'push' && github.ref == 'refs/heads/wip' && github.event.head_commit.message == '测量自有折叠增长夹具状态【诊断20261020】'))"
        self.assertIn('if: ${{ ' + mode + ' }}', job)
        self.assertIn("'-cpp-growth-diagnostic'", workflow)
        self.assertEqual(workflow.count('if: ${{ !(' + mode + ') }}'), 2)
        self.assertIn('if: ${{ inputs.historical_callback }}', job)
        self.assertIn("throw 'Select only one diagnostic mode.'", job)
        self.assertNotIn('*.zip', job)
        self.assertNotIn('package.py', job)
        self.assertIn('if: always()', job)
        self.assertIn('build/cpp-growth-diagnostic/*.log', job)
        self.assertIn('default: false', workflow.split('syntax_growth_diagnostic:',1)[1].split('historical_callback:',1)[0])

    def test_exact_one_shot_trigger_truth_table(self):
        workflow = (ROOT/'.github/workflows/windows.yml').read_text()
        line = workflow.split('  cpp-growth-diagnostic:\n',1)[1].splitlines()[0].strip()
        expression = line.removeprefix('if: ${{ ').removesuffix(' }}')
        title = '测量自有折叠增长夹具状态【诊断20261020】'
        for event, ref, message, manual in itertools.product(('push','pull_request','workflow_dispatch'), ('refs/heads/wip','refs/heads/main','refs/heads/wip-other'), (title, title+'\n', title+' extra', 'normal change'), (False,True)):
            text = expression
            for name, value in [('github.event.head_commit.message',message),('github.event_name',event),('github.ref',ref),('inputs.syntax_growth_diagnostic',manual)]:
                text = text.replace(name,repr(value))
            result = eval(text.replace('&&',' and ').replace('||',' or '), {'__builtins__': {}}, {})
            expected = event == 'workflow_dispatch' and manual or event == 'push' and ref == 'refs/heads/wip' and message == title
            self.assertEqual(result, expected, (event,ref,message,manual))

    def test_strict_trigger_guard(self):
        validate_trigger('push', 'refs/heads/wip', {'head_commit': {'message': ONE_SHOT_TITLE}})
        validate_trigger('workflow_dispatch', 'refs/heads/wip', {'inputs': {'syntax_growth_diagnostic':'true', 'historical_callback':'false'}})
        for event, ref, payload in [
            ('push','refs/heads/WIP',{'head_commit':{'message':ONE_SHOT_TITLE}}),
            ('push','refs/heads/wip',{'head_commit':{'message':ONE_SHOT_TITLE+'\n'}}),
            ('push','refs/heads/wip',{}),
            ('pull_request','refs/heads/wip',{'head_commit':{'message':ONE_SHOT_TITLE}}),
            ('workflow_dispatch','refs/heads/wip',{'inputs':{'syntax_growth_diagnostic':'false'}}),
            ('workflow_dispatch','refs/heads/wip',{'inputs':{'syntax_growth_diagnostic':'true','historical_callback':'true'}}),
        ]:
            with self.assertRaises(RuntimeError): validate_trigger(event,ref,payload)
        # GitHub == treats refs case-insensitively; this strict guard must fail
        # before measurement for a matching-title case-variant branch.
        self.assertEqual('refs/heads/WIP'.casefold(), 'refs/heads/wip'.casefold())

    def test_lexilla_platform_matches_product_builder(self):
        # Capture the actual runner's literal command, not a second command copy.
        runner = ast.parse((ROOT/'tools/run_cpp_growth_diagnostic.py').read_text())
        calls = [n for n in ast.walk(runner) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id == 'run' and n.args and isinstance(n.args[0],ast.Constant) and n.args[0].value == 'lexilla']
        self.assertEqual(len(calls), 1)
        constants = [n.value for n in ast.walk(calls[0].args[1]) if isinstance(n,ast.Constant) and isinstance(n.value,str)]
        self.assertIn('../bin/lexilla.dll', constants)
        self.assertEqual(constants.count('windir=C:/Windows'), 1)
        product = (ROOT/'tools/build.py').read_text()
        self.assertIn("'windir=C:/Windows'", product)
        with zipfile.ZipFile(ROOT/'third_party/source_archives/lexilla554.zip') as archive:
            makefile = archive.read('lexilla/src/makefile').decode().replace('\r\n','\n')
        # Without the lower-case windir make variable this exact pinned file
        # selects liblexilla.so, so the .dll target must be paired with it.
        self.assertIn('ifdef windir\n    SHARED_NAME = lexilla\n    SHAREDEXTENSION = dll', makefile)
        self.assertIn('SHARED_NAME = liblexilla', makefile)
        self.assertIn('SHAREDEXTENSION = so', makefile)
        def require_windows_target(args):
            if '../bin/lexilla.dll' not in args or args.count('windir=C:/Windows') != 1:
                raise ValueError('Windows target requires explicit lower-case windir')
        require_windows_target(constants)
        with self.assertRaises(ValueError):
            require_windows_target([x for x in constants if x != 'windir=C:/Windows'])
        with self.assertRaises(ValueError):
            require_windows_target([x.replace('windir=', 'WINDIR=') for x in constants])

if __name__ == '__main__': unittest.main()
