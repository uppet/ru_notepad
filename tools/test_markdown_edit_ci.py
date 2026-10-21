#!/usr/bin/env python3
"""Fail-closed experiment wiring and disassembly parser controls (no GUI)."""
from pathlib import Path
import unittest
from test_markdown_edit_windows import inspect_counter, HARNESS
ROOT=Path(__file__).resolve().parents[1]
class Controls(unittest.TestCase):
    def setUp(self):
        self.ps=(ROOT/'tools/run_markdown_edit_ci.ps1').read_text()
        self.workflow=(ROOT/'.github/workflows/mi-perf-prototype.yml').read_text()
    def test_trigger_scope(self):
        self.assertIn('branches: [mi-perf-prototype]',self.workflow)
        for value in ("$env:GITHUB_EVENT_NAME -cne 'push'", "$env:GITHUB_REF -cne 'refs/heads/mi-perf-prototype'", "$env:GITHUB_REPOSITORY -cne 'uppet/ru_notepad'"):
            self.assertIn(value,self.ps)
        self.assertNotIn('workflow_dispatch:',self.workflow)
        self.assertNotIn('pull_request:',self.workflow)
    def test_no_guard_reuse_or_mutation(self):
        self.assertNotIn('guard_markdown_owned_profile',self.ps)
        self.assertNotIn('$env:GITHUB_REF =',self.ps)
        self.assertNotIn('RunMarkdownOwnedProfile',self.ps)
    def test_product_pin_and_clean(self):
        self.assertIn('85c7821fda35aa79deeaf67b4d430f24ddd7f07f',self.workflow)
        self.assertIn('85c7821fda35aa79deeaf67b4d430f24ddd7f07f',self.ps)
        self.assertIn('a770e367e84d87a0d2fcb6d49ea6f06da2dbe4ba',self.ps)
        self.assertIn('status --porcelain',self.ps)
    def test_archive_functions_identical(self):
        original=(ROOT/'tools/windows_ci.ps1').read_text()
        expected=original[original.index('function Resolve-Application'):original.index('$Root = Split-Path')]
        self.assertIn(expected,self.ps)
    def test_controls_precede_build_and_pair(self):
        self.assertLess(self.ps.index('test_markdown_edit_windows.py'),self.ps.index('prepare_source_archives.py'))
        self.assertLess(self.ps.index('test_markdown_edit_late.py'),self.ps.index('tools/build.py'))
        self.assertLess(self.ps.index('tools/build.py'),self.ps.index('run_markdown_edit_profile.py'))
    def test_private_logs_and_no_packages(self):
        self.assertIn('& $Command @Arguments *> $Log',self.ps)
        self.assertNotIn('package.py',self.ps)
        self.assertNotIn('package_manual_preview',self.ps)
        self.assertIn("$Arguments[0] -ceq (Join-Path $PSScriptRoot 'run_markdown_edit_controls.py')",self.ps)
        self.assertIn("'^MI_EDIT_CONTROL module=[1-7]",self.ps)
        self.assertIn("if ($LASTEXITCODE -ne 0) { throw 'MI_EDIT_DIAGNOSTIC_OR_PRODUCT_GATE_FAILED=1' }",self.ps)
    def test_upload_allowlist(self):
        self.assertEqual(self.workflow.count('uses: actions/upload-artifact@'),1)
        self.assertIn('path: application/build/markdown-edit-experiment/measurements/markdown-edit-profile.json',self.workflow)
        self.assertNotIn('*.log',self.workflow)
        self.assertNotIn('continue-on-error',self.workflow)
        self.assertIn('if: always()',self.workflow)
        self.assertIn('contents: read',self.workflow)
    def test_real_header_included(self):
        self.assertIn('#include "markdown_edit_profile.h"',HARNESS)
        self.assertNotIn('MPP_CUSTOM_BACKEND',HARNESS)
        for s in ('CreateThread','WaitForSingleObject','preserved()','--four','--five','--foreign'):
            self.assertIn(s,HARNESS)
    def test_compiler_checkout_is_outside_application_root(self):
        self.assertIn('working-directory: application',self.workflow)
        self.assertIn('working-directory: ${{ github.workspace }}',self.workflow)
        self.assertIn('path: application',self.workflow)
        self.assertIn('path: .ci/ru-language',self.workflow)
        self.assertEqual(self.workflow.count('-RuRoot "$env:GITHUB_WORKSPACE/.ci/ru-language"'),4)
    def test_stages_are_ordered_and_bound_to_same_commit(self):
        stages=('controls','dependencies','application','measure')
        positions=[self.workflow.index('-Stage '+stage) for stage in stages]
        self.assertEqual(positions,sorted(positions))
        self.assertIn("[ValidateSet('controls','dependencies','application','measure')]",self.ps)
        self.assertIn("dependencies='controls'; application='dependencies'; measure='application'",self.ps)
        self.assertIn("$env:GITHUB_SHA + '|' + $Previous",self.ps)
        self.assertIn("$env:GITHUB_SHA + '|' + $Stage",self.ps)
        self.assertIn("$env:GITHUB_SHA -cnotmatch '^[0-9a-f]{40}$'",self.ps)
        self.assertLess(self.ps.index('MI_EDIT_STAGE_ORDER_REJECTED'),self.ps.index('Invoke-Checked $Python'))
    def test_failure_projection_is_numeric_only(self):
        import io
        from run_markdown_edit_controls import Result
        def bad(): raise AssertionError('PRIVATE_PATH=C:/private/input.md')
        result=unittest.TextTestRunner(stream=io.StringIO(),resultclass=lambda *a,**k:Result(*a,module_number=1,**k)).run(unittest.FunctionTestCase(bad))
        self.assertEqual(len(result.rows),1)
        self.assertTrue(all(type(x) is int for x in result.rows[0]))
        self.assertEqual(result.rows[0][1],1)
        self.assertNotIn('PRIVATE',repr(result.rows))
    def test_disassembly_inline(self):
        self.assertTrue(inspect_counter('0001 <checked_hot_counter>:\n  1: mov %gs:0x58,%rax\n  2: ret\n'))
    def test_disassembly_tail(self):
        self.assertTrue(inspect_counter('0001 <checked_hot_counter>:\n  1: jmp 3 <mpp_count>\n0003 <mpp_count>:\n  3: mov %gs:0x58,%rax\n  4: ret\n'))
    def test_disassembly_negative(self):
        for s in ('call 4 <bad>', 'jmp 4 <bad>', '__emutls_get_address', '__imp_GetLastError'):
            with self.subTest(s=s),self.assertRaises(ValueError):
                inspect_counter('0001 <checked_hot_counter>:\n  1: mov %gs:0x58,%rax\n  2: '+s+'\n')
        for s in ('', '0001 <checked_hot_counter>:\n  1: ret\n'):
            with self.assertRaises(ValueError): inspect_counter(s)
if __name__=='__main__': unittest.main(verbosity=2)
