#!/usr/bin/env python3
"""Bounded host controls for the research driver, never Windows acceptance."""
from pathlib import Path
from contextlib import redirect_stdout
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import package as packaging
import windows_ci as acceptance
import run_markdown_callback_cost as research


def sample_line(mode='present', **updates):
    values = {'mode': mode, 'elapsed_us': 1234567,
              'callback_entries': 310947 if mode == 'present' else 0, **research.PROOFS}
    values.update(updates)
    return '\n'.join(research.STARTUP_LINES) + '\nMD_CALLBACK_RESULT ' + ' '.join(
        f'{key}={value}' for key, value in values.items()) + '\n'


class ResultControls(unittest.TestCase):
    def test_sample_order_is_bounded_interleaving(self):
        self.assertEqual(research.sample_order(), ['present', 'absent', 'absent', 'present'])
        self.assertEqual((research.SAMPLE_SECONDS, research.TOTAL_SECONDS), (120, 480))

    def test_both_routes_admit_only_their_actual_callback_count(self):
        for mode, expected in (('present', 310947), ('absent', 0)):
            result = research.parse_sample(sample_line(mode), mode)
            self.assertEqual(result['callback_entries'], expected)
            self.assertEqual(result['mode'], mode)
            with self.assertRaises(research.ResearchError):
                research.parse_sample(sample_line(mode, callback_entries=expected + 1), mode)

    def test_every_functional_proof_is_required(self):
        for field in research.PROOFS:
            with self.subTest(field=field), self.assertRaises(research.ResearchError):
                research.parse_sample(sample_line(**{field: 0}), 'present')

    def test_missing_duplicate_or_unrecognized_fields_are_rejected(self):
        line = sample_line()
        for invalid in (line + line, '', line.replace('folds=1 ', ''),
                        line.rstrip() + ' folds=1\n', line.rstrip() + ' unexpected=1\n',
                        line.replace('mode=present', 'mode=absent'),
                        'unrelated private output\n' + line):
            with self.subTest(invalid=invalid[:80]), self.assertRaises(research.ResearchError):
                research.parse_sample(invalid, 'present')

    def test_numbers_and_execution_bounds_fail_closed(self):
        for value in ('0', '-1', '+1', '01', '1.5', 'nan', 'inf', 'true', '120000001'):
            with self.subTest(value=value), self.assertRaises(research.ResearchError):
                research.parse_sample(sample_line(elapsed_us=value), 'present')
        for invalid in ('FAIL: synthetic\n' + sample_line(), 'x' * (research.MAX_LOG_BYTES + 1)):
            with self.assertRaises(research.ResearchError):
                research.parse_sample(invalid, 'present')

    def test_existing_corpus_identity_is_exact(self):
        value = research.fixture_identity()
        self.assertEqual(value['sha256'], research.INPUT_SHA256)
        self.assertEqual((value['bytes'], value['physical_lines'], value['ordered_assignments']),
                         (1000000, 100001, 100002))


class InstrumentControls(unittest.TestCase):
    @staticmethod
    def source():
        return ('#include <stdint.h>\n'
                'static Val ru_function_1(Env *global, Val self, int call_line, Val *args) {\n'
                '    return v_num(123);\n}\n'
                'static Val ru_function_2(Env *global, Val self, int call_line, Val *args) {\n'
                '    return v_num(-1);\n}\n')

    def test_hooks_are_counter_only_and_do_not_touch_callback_body(self):
        value = research.instrument_generated(self.source(), 'ru_function_1', 'ru_function_2')
        self.assertEqual(value.count('++ru_md_research_entries'), 1)
        self.assertEqual(value.count('return v_num(123);'), 1)
        self.assertIn('UINT64_MAX', value)
        self.assertIn('UINT64_C(9007199254740991)', value)
        for forbidden in ('GetLastError(', 'SetLastError(', 'QueryPerformanceCounter(',
                          'malloc(', 'rn_trap_new(', 'DefSubclassProc('):
            self.assertNotIn(forbidden, value)

    def test_exact_function_boundaries_are_required(self):
        original = self.source()
        for code, callback, reader in (
                (original, 'other', 'ru_function_2'),
                (original, 'ru_function_1', 'ru_function_1'),
                (original, 'ru_function_99', 'ru_function_2'),
                (original, 'ru_function_1', 'ru_function_99'),
                (original + original, 'ru_function_1', 'ru_function_2'),
                (original.replace('#include <stdint.h>\n', ''), 'ru_function_1', 'ru_function_2'),
                (original + 'ru_md_research_already_present\n', 'ru_function_1', 'ru_function_2')):
            with self.subTest(callback=callback, reader=reader), self.assertRaises(research.ResearchError):
                research.instrument_generated(code, callback, reader)

    def test_actual_c_counter_handles_entries_exact_limit_and_overflow(self):
        cc = shutil.which('gcc')
        if cc is None:
            self.fail('The controlled research build requires the configured GCC compiler')
        source = self.source().replace('#include <stdint.h>\n',
            '#include <stdint.h>\n'
            'typedef double Val; typedef int Env;\n'
            'static Val v_num(double number) { return number; }\n')
        code = research.instrument_generated(source, 'ru_function_1', 'ru_function_2')
        code += '''
int main(void) {
    if (ru_function_2(0,0,0,0) != 0) return 1;
    for (int i=0;i<3;i++) if (ru_function_1(0,0,0,0) != 123) return 2;
    if (ru_function_2(0,0,0,0) != 3) return 3;
    ru_md_research_entries=UINT64_C(9007199254740991);
    if (ru_function_2(0,0,0,0) != 9007199254740991.0) return 4;
    ru_function_1(0,0,0,0);
    if (ru_function_2(0,0,0,0) != -1) return 5;
    ru_md_research_entries=UINT64_MAX;
    ru_function_1(0,0,0,0);
    if (ru_md_research_entries != UINT64_MAX || !ru_md_research_overflow) return 6;
    if (ru_function_2(0,0,0,0) != -1) return 7;
    return 0;
}
'''
        with tempfile.TemporaryDirectory(prefix='markdown-counter-c-') as folder:
            source = Path(folder) / 'counter.c'
            binary = Path(folder) / ('counter.exe' if sys.platform == 'win32' else 'counter')
            source.write_text(code, encoding='utf-8', newline='\n')
            build = subprocess.run([cc, '-std=c99', '-O2', str(source), '-o', str(binary)],
                                   capture_output=True, timeout=30)
            self.assertEqual(build.returncode, 0, 'Counter C control did not compile')
            result = subprocess.run([str(binary)], capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, b'')
            self.assertEqual(result.stderr, b'')


class ProcessControls(unittest.TestCase):
    def run_child(self, program, label, timeout=5):
        with tempfile.TemporaryDirectory(prefix='markdown-research-process-') as folder:
            return research.run_private([sys.executable, '-I', '-c', program], Path(folder), label, timeout)

    def test_success_and_nonzero_exit_are_distinct(self):
        good = self.run_child("print('synthetic')", 'sample-good')
        self.assertTrue(research.command_succeeded(good))
        self.assertEqual(good['stderr_bytes'], 0)
        bad = self.run_child("print('synthetic'); raise SystemExit(3)", 'sample-bad')
        self.assertFalse(research.command_succeeded(bad))
        self.assertEqual(bad['returncode'], 3)
        self.assertFalse(bad['killed'])

    def test_completed_output_overrun_is_not_accepted(self):
        bad = self.run_child(f"import sys; sys.stdout.write('x'*{research.MAX_LOG_BYTES + 1})", 'sample-overrun')
        self.assertFalse(research.command_succeeded(bad))
        self.assertTrue(bad['output_bound'])
        self.assertGreater(bad['stdout_bytes'], research.MAX_LOG_BYTES)

    def test_timeout_stops_the_owned_process_and_retains_partial_metadata(self):
        bad = self.run_child("import time; print('partial', flush=True); time.sleep(20)", 'sample-timeout', .5)
        self.assertFalse(research.command_succeeded(bad))
        self.assertTrue(bad['timeout'])
        self.assertTrue(bad['killed'])
        self.assertTrue(bad['cleanup_confirmed'])
        self.assertIsNotNone(bad['returncode'])
        self.assertGreater(bad['stdout_bytes'], 0)
        self.assertRegex(bad['stdout_sha256'], r'^[a-f0-9]{64}$')

    def test_any_timeout_kill_bound_or_uncertain_cleanup_rejects_zero_exit(self):
        good = {'returncode': 0, 'timeout': False, 'killed': False,
                'output_bound': False, 'cleanup_confirmed': True}
        self.assertTrue(research.command_succeeded(good))
        for field in ('timeout', 'killed', 'output_bound', 'cleanup_confirmed'):
            bad = dict(good, **{field: not good[field]})
            with self.subTest(field=field):
                self.assertFalse(research.command_succeeded(bad))


class EvidenceControls(unittest.TestCase):
    def test_failed_build_with_private_diagnostics_exposes_only_fixed_metadata(self):
        with tempfile.TemporaryDirectory(prefix='markdown-research-evidence-') as folder:
            root = Path(folder)
            evidence = root / 'evidence'
            sentinel = b'PRIVATE_SOURCE_SENTINEL /private/user/source.ru\n'
            def failed_emit(command, private, label, timeout):
                self.assertEqual(label, 'emit')
                (private / (label + '.stderr')).write_bytes(sentinel)
                return {'returncode': 17, 'timeout': False, 'output_bound': False,
                        'killed': False, 'cleanup_confirmed': True, 'wall_ms': 1.0,
                        'stdout_bytes': 0, 'stderr_bytes': len(sentinel),
                        'stdout_sha256': hashlib.sha256(b'').hexdigest(),
                        'stderr_sha256': hashlib.sha256(sentinel).hexdigest()}
            argv = ['probe', '--ru-root', str(root), '--binary-dir', str(root / 'bin'),
                    '--evidence-dir', str(evidence), '--cc', 'gcc', '--windres', 'windres']
            with patch.object(research, 'ROOT', root), \
                 patch.object(research, 'os', SimpleNamespace(name='nt')), \
                 patch.dict(sys.modules, {'ctypes': SimpleNamespace(WinDLL=lambda _: object())}), \
                 patch.object(research, 'identities', return_value={'synthetic': True}), \
                 patch.object(research, 'fixture_identity', return_value={'synthetic': True}), \
                 patch.object(research, 'run_private', side_effect=failed_emit) as run, \
                 patch.object(sys, 'argv', argv), redirect_stdout(io.StringIO()) as output:
                self.assertEqual(research.main(), 1)
            self.assertEqual(run.call_count, 1)
            public = list(evidence.iterdir())
            self.assertEqual([path.name for path in public], ['markdown-callback-summary.json'])
            data = public[0].read_bytes()
            self.assertNotIn(b'PRIVATE_SOURCE_SENTINEL', data)
            self.assertNotIn(b'/private/user', data)
            self.assertNotIn('PRIVATE_SOURCE_SENTINEL', output.getvalue())
            record = json.loads(data)
            self.assertEqual(record['status'], 'failed')
            self.assertEqual(record['failure'], {'stage': 'emit', 'code': 'emit_failed'})
            self.assertEqual(record['samples'], [])
            self.assertEqual(record['build_attempts']['emit']['stderr_sha256'], hashlib.sha256(sentinel).hexdigest())


class PipelineControls(unittest.TestCase):
    def source(self):
        return (ROOT / 'tools/windows_ci.ps1').read_text(encoding='utf-8')

    def test_research_is_after_all_builds_and_before_unmodified_acceptance(self):
        source = self.source()
        self.assertLess(source.index("'tools/test_markdown_callback_cost.py'"),
                        source.index("'tools/check_static.py'"))
        self.assertLess(source.index('foreach ($test in @('), source.index('$ResearchArgs ='))
        self.assertIn("$AcceptArgs = @('tools/windows_ci.py','--bin-dir',$Output,'--evidence-dir',$Evidence,", source)
        self.assertIn("if ($RunAclTests) { $AcceptArgs += '--acl' }", source)
        self.assertIn('Invoke-ResearchThenAcceptance $Python $ResearchArgs $AcceptArgs', source)
        self.assertNotIn('markdown_callback_cost_native', source)

    def test_research_is_not_product_acceptance_or_a_distributed_executable(self):
        self.assertNotIn('markdown_callback_cost_native.exe', packaging.BINARY_NAMES)
        self.assertNotIn('markdown_callback_cost_native', dict(acceptance.NATIVE_CONSOLE_TESTS))
        names = packaging.evidence_names([name for name, _ in acceptance.NATIVE_CONSOLE_TESTS])
        self.assertFalse(any('callback-cost' in name for name in names))
        # The research does not add a workflow or alter automatic trigger scope.
        workflows = {p.name for p in (ROOT / '.github/workflows').glob('*.yml')}
        self.assertEqual(workflows, {'windows.yml', 'policy-prefix-benchmark.yml',
                                    'direct-style-benchmark.yml', 'ru-syntax-profile.yml'})

    def test_actual_powershell_research_failure_never_skips_product(self):
        pwsh = shutil.which('pwsh')
        if pwsh is None:
            if sys.platform == 'win32':
                self.fail('Windows must execute actual PowerShell research-order controls')
            self.skipTest('PowerShell is absent on this non-Windows host')
        source = self.source()
        functions = []
        for name in ('Invoke-Checked', 'Invoke-ResearchThenAcceptance'):
            match = re.search(r'(?ms)^function ' + name + r'\b.*?^}', source)
            self.assertIsNotNone(match)
            functions.append(match.group(0))
        quote = lambda text: "'" + str(text).replace("'", "''") + "'"
        with tempfile.TemporaryDirectory(prefix='markdown-research-order-') as folder:
            root = Path(folder)
            child = root / 'child.py'
            child.write_text(
                "from pathlib import Path\nimport sys\n"
                "with Path(sys.argv[1]).open('a', encoding='utf-8', newline='\\n') as log:\n"
                "    log.write(sys.argv[2] + '\\n')\n"
                "raise SystemExit(int(sys.argv[3]))\n", encoding='utf-8', newline='\n')
            for research, product in ((0, 0), (7, 0), (0, 9), (7, 9)):
                with self.subTest(research=research, product=product):
                    marker = root / f'{research}-{product}.log'
                    script = root / f'{research}-{product}.ps1'
                    script.write_text(
                        "Set-StrictMode -Version Latest\n$ErrorActionPreference = 'Stop'\n" +
                        '\n'.join(functions) + '\n' +
                        '$Research = @(' + ','.join(map(quote, [child, marker, 'research', research])) + ')\n' +
                        '$Acceptance = @(' + ','.join(map(quote, [child, marker, 'product', product])) + ')\n' +
                        'Invoke-ResearchThenAcceptance ' + quote(sys.executable) +
                        ' $Research $Acceptance\n', encoding='utf-8', newline='\n')
                    result = subprocess.run([pwsh, '-NoLogo', '-NoProfile', '-NonInteractive',
                                             '-File', str(script)], capture_output=True, timeout=20)
                    self.assertEqual(marker.read_text(encoding='utf-8').splitlines(), ['research', 'product'])
                    self.assertEqual(result.returncode == 0, research == product == 0)
                    self.assertEqual(b'MARKDOWN_CALLBACK_RESEARCH_FAILED=1' in result.stdout,
                                     research != 0)


if __name__ == '__main__':
    unittest.main()
