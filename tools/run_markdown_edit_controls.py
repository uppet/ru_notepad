#!/usr/bin/env python3
"""Run fixed control suites; only numeric failure metadata leaves the private log."""
import argparse
import importlib
import io
from pathlib import Path
import unittest

MODULES = ('test_markdown_edit_ci', 'test_markdown_control_markers',
           'test_markdown_owned_workflow', 'test_markdown_edit_transform',
           'test_markdown_edit_profile', 'test_markdown_edit_late',
           'test_markdown_edit_observers')
ROOT = Path(__file__).resolve().parent

class Result(unittest.TextTestResult):
    def __init__(self, *args, module_number, **kwargs):
        super().__init__(*args, **kwargs)
        self.module_number=module_number; self.case=0; self.rows=[]
    def startTest(self,test):
        self.case+=1; super().startTest(test)
    def note(self,err,status):
        kind=1 if issubclass(err[0],AssertionError) else 2 if issubclass(err[0],OSError) else 3
        line=0; tb=err[2]
        while tb:
            # Only a line in the selected, fixed checked-in module is projected.
            if Path(tb.tb_frame.f_code.co_filename).resolve()==ROOT/(MODULES[self.module_number-1]+'.py'):
                line=tb.tb_lineno
            tb=tb.tb_next
        self.rows.append((self.case,status,min(line,99999),kind))
    def addFailure(self,test,err): self.note(err,1);super().addFailure(test,err)
    def addError(self,test,err): self.note(err,2);super().addError(test,err)
    def addSubTest(self,test,subtest,err):
        if err:self.note(err,1 if issubclass(err[0],AssertionError) else 2)
        super().addSubTest(test,subtest,err)

def main():
    p=argparse.ArgumentParser();p.add_argument('--module',choices=MODULES,required=True);a=p.parse_args()
    module=importlib.import_module(a.module); number=MODULES.index(a.module)+1
    suite=unittest.defaultTestLoader.loadTestsFromModule(module)
    result=unittest.TextTestRunner(verbosity=2,resultclass=lambda *x,**kw:Result(*x,module_number=number,**kw)).run(suite)
    for case,status,line,kind in result.rows[:100]:
        print(f'MI_EDIT_CONTROL module={number} case={case} status={status} line={line} exception={kind}',flush=True)
    print(f'MI_EDIT_CONTROL module={number} cases={result.testsRun} failed={len(result.failures)} errors={len(result.errors)} skipped={len(result.skipped)}',flush=True)
    return 0 if result.wasSuccessful() else 1
if __name__=='__main__':raise SystemExit(main())
