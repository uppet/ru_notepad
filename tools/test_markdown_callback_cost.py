#!/usr/bin/env python3
"""Bounded host controls for the research driver, never Windows acceptance."""
from pathlib import Path
from contextlib import nullcontext, redirect_stdout
from copy import deepcopy
import math
import time
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
              'callback_entries': 310947 if mode == 'present' else 0,
              'heap_size': 32, 'live_peak': 250, 'live_samples': 3126, **research.PROOFS}
    values.update(updates)
    return '\n'.join(research.STARTUP_LINES) + '\nMD_CALLBACK_RESULT ' + ' '.join(
        f'{key}={value}' for key, value in values.items()) + '\n'


def approved():
    # Deliberately synthetic identities. Never written to the fixed configuration.
    return {'schema': 1, 'old': {'commit': research.OLD_COMMIT, 'tree': research.OLD_TREE},
            'new': {'commit': '1' * 40, 'tree': '2' * 40}, 'approval_commit': '3' * 40,
            'expected_heap_size': {'old': 32, 'new': 48},
            'replacements': [{'scope': 'runtime', 'old': 'int runtime_old;\n', 'new': 'int runtime_new;\n'},
                             {'scope': 'generator_banner', 'old': research.BANNER.format('0.22.0'),
                              'new': research.BANNER.format('0.22.1')}]}


def generated_pair():
    old = (research.BANNER.format('0.22.0') + '#define RU_ENABLE_MODULO 1\n' + research.RUNTIME_START +
           '#define RU_RUNTIME_H\nint runtime_old;\n#endif\n' + research.THUNKS_START +
           'typedef int (*RuNativeCall_0)(void);\n' + research.MODULE_START +
           'static Val ru_function_1(Env *global, Val self, int call_line, Val *args) {\nreturn v_num(123);\n}\n')
    new = old.replace('int runtime_old;', 'int runtime_new;').replace(research.BANNER.format('0.22.0'), research.BANNER.format('0.22.1'))
    return old, new


def sample_rows():
    rows = []
    for index, (compiler, mode) in enumerate(research.sample_order(), 1):
        binary = {'exe_sha256': ('4' if compiler == 'old' else '5') * 64,
                  'dependency_sha256': {name: '6' * 64 for name in ('Scintilla.dll', 'Lexilla.dll', 'RuSyntax.dll')}}
        result = research.parse_sample(sample_line(mode, heap_size=32 if compiler == 'old' else 48,
                                                 live_peak=200 + index), mode)
        rows.append({'order': index, 'compiler': compiler, 'mode': mode, 'status': 'passed',
                     'binary_before': binary, 'binary_after': deepcopy(binary), 'result': result,
                     'returncode': 0, 'timeout': False, 'output_bound': False, 'memory_bound': False,
                     'memory_error': False, 'killed': False, 'cleanup_confirmed': True, 'wall_ms': 1500.0,
                     'stdout_bytes': 900, 'stderr_bytes': 0, 'stdout_sha256': '7' * 64, 'stderr_sha256': '8' * 64,
                     'memory': {'limit_bytes': research.MEMORY_LIMIT_BYTES, 'interval_seconds': .25,
                                'sampling_calls': 2, 'valid_live_samples': 2, 'exit_race_reads': 0,
                                'last_success_elapsed_ms': 1000.0, 'sampling_elapsed_ms': .1,
                                'observed_max': {key: 5000 for key in research.MEMORY_METRICS}}})
    return rows


class ResultControls(unittest.TestCase):
    def test_sample_order_is_bounded_interleaving(self):
        self.assertEqual(research.sample_order(), [('old', 'present'), ('new', 'present'), ('new', 'absent'), ('old', 'absent'),
                                                   ('old', 'absent'), ('new', 'absent'), ('new', 'present'), ('old', 'present')])
        self.assertEqual((research.SAMPLE_SECONDS, research.TOTAL_SECONDS, research.RESEARCH_SECONDS), (120, 960, 1680))
        self.assertEqual((research.EMIT_SECONDS, research.RESOURCE_SECONDS, research.COMPILE_SECONDS), (120, 30, 180))

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
                'output_bound': False, 'memory_bound': False, 'memory_error': False, 'cleanup_confirmed': True}
        self.assertTrue(research.command_succeeded(good))
        for field in ('timeout', 'killed', 'output_bound', 'memory_bound', 'memory_error', 'cleanup_confirmed'):
            bad = dict(good, **{field: not good[field]})
            with self.subTest(field=field):
                self.assertFalse(research.command_succeeded(bad))


class EvidenceControls(unittest.TestCase):
    def test_failed_build_with_private_diagnostics_exposes_only_fixed_metadata(self):
        with tempfile.TemporaryDirectory(prefix='markdown-research-evidence-') as folder:
            root = Path(folder).resolve()
            evidence = root / 'evidence'
            sentinel = b'PRIVATE_SOURCE_SENTINEL /private/user/source.ru\n'
            def failed_emit(command, private, label, timeout):
                self.assertEqual(label, 'emit')
                (private / (label + '.stderr')).write_bytes(sentinel)
                return {'returncode': 17, 'timeout': False, 'output_bound': False,
                        'killed': False, 'memory_bound': False, 'memory_error': False, 'memory': None, 'cleanup_confirmed': True, 'wall_ms': 1.0,
                        'stdout_bytes': 0, 'stderr_bytes': len(sentinel),
                        'stdout_sha256': hashlib.sha256(b'').hexdigest(),
                        'stderr_sha256': hashlib.sha256(sentinel).hexdigest()}
            argv = ['probe', '--ru-root', str(root / 'product'), '--old-ru-root', str(root / 'old'), '--new-ru-root', str(root / 'new'), '--binary-dir', str(root / 'bin'),
                    '--evidence-dir', str(evidence), '--cc', 'gcc', '--windres', 'windres']
            with patch.object(research, 'ROOT', root), \
                 patch.object(research, 'os', SimpleNamespace(name='nt')), \
                 patch.dict(sys.modules, {'ctypes': SimpleNamespace(WinDLL=lambda _: object())}), \
                 patch.object(research, 'load_approval', return_value=approved()), \
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
            self.assertEqual(record['failure'], {'stage': 'old_emit', 'code': 'emit_failed'})
            self.assertEqual(record['samples'], [])
            self.assertEqual(record['build_attempts']['old']['emit']['stderr_sha256'], hashlib.sha256(sentinel).hexdigest())


class ApprovalAndDeltaControls(unittest.TestCase):
    versions = {'old': '0.22.0', 'new': '0.22.1'}

    def test_actual_fixed_configuration_matches_the_approved_language_freeze(self):
        value = research.load_approval()
        self.assertEqual(value['new'], {'commit': '85c7821fda35aa79deeaf67b4d430f24ddd7f07f',
                                       'tree': 'a770e367e84d87a0d2fcb6d49ea6f06da2dbe4ba'})
        self.assertEqual(value['approval_commit'], value['new']['commit'])
        self.assertEqual(value['expected_heap_size'], {'old': 32, 'new': 48})
        self.assertEqual(len(value['replacements']), 11)
        self.assertEqual(sum(pair['scope'] == 'runtime' for pair in value['replacements']), 10)
        self.assertEqual([pair for pair in value['replacements'] if pair['scope'] == 'generator_banner'],
                         [{'scope': 'generator_banner', 'old': research.BANNER.format('0.22.0'),
                           'new': research.BANNER.format('0.22.1')}])
        self.assertEqual((research.PRODUCT_COMMIT, research.PRODUCT_TREE),
                         (value['new']['commit'], value['new']['tree']))
        self.assertNotEqual(research.PRODUCT_COMMIT, research.OLD_COMMIT)

    def test_direct_application_parent_is_required_not_just_ancestry(self):
        with patch.object(research, 'git', side_effect=[research.BASE_TREE, research.BASE_COMMIT]):
            research.validate_application_parent()
        # A descendant whose parent is not BASE must fail even if BASE is an ancestor.
        with patch.object(research, 'git', side_effect=[research.BASE_TREE, '9'*40]), \
             self.assertRaisesRegex(research.ResearchError, 'candidate_parent_mismatch'):
            research.validate_application_parent()

    def test_missing_empty_identity_or_layout_or_unreviewed_deltas_fail_closed(self):
        changes = [('new', None), ('new', {'commit': '', 'tree': '2'*40}),
                   ('new', {'commit': '0'*40, 'tree': '2'*40}), ('approval_commit', ''),
                   ('replacements', []), ('replacements', None),
                   ('expected_heap_size', {'old': 32, 'new': None}),
                   ('expected_heap_size', {'old': 32, 'new': True}), ('extra', True)]
        for key, value in changes:
            control = approved(); control[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(research.ResearchError):
                research.validate_approval(control)

    def test_only_exact_nonoverlapping_runtime_and_full_banner_pairs_pass(self):
        result = research.validate_generated_delta(*generated_pair(), approved(), self.versions)
        self.assertTrue(result['exact_approved_delta'])
        self.assertTrue(result['application_and_thunks_identical'])
        self.assertEqual(result['replacement_count'], 2)

    def test_extra_missing_duplicate_identity_and_outside_scope_changes_fail(self):
        old, new = generated_pair()
        bad = []
        for pairs in ([], approved()['replacements'][:1], approved()['replacements']*2,
                      [{'scope':'runtime','old':'','new':'x'}],
                      [{'scope':'runtime','old':'int runtime_old;\n','new':'int runtime_old;\n'}],
                      [{'scope':'runtime','old':'runtime_.*','new':'runtime_new'}]):
            config = approved(); config['replacements'] = pairs
            bad.append((old, new, config))
        bad.extend((old, changed, approved()) for changed in (new+'extra\n', new.replace('v_num(123)', 'v_num(124)'),
                    new.replace('RuNativeCall_0', 'RuNativeCall_1'), new.replace('#define RU_ENABLE_MODULO 1', ''),
                    new.replace('int runtime_new;', 'int runtime_new;\nint added;'), new.replace('0.22.1', '0.22.2')))
        duplicate_old = old.replace('int runtime_old;\n', 'int runtime_old;\nint runtime_old;\n')
        bad.append((duplicate_old, new, approved()))
        for scope, literal_old, literal_new in (
                ('runtime', 'v_num(123)', 'v_num(124)'), ('runtime', 'RuNativeCall_0', 'RuNativeCall_1'),
                ('runtime', 'RU_ENABLE_MODULO 1', 'RU_ENABLE_MODULO 2'),
                ('generator_banner', '0.22.0', '0.22.1')):
            config = approved()
            if scope == 'generator_banner': config['replacements'].pop()
            config['replacements'].append({'scope': scope, 'old': literal_old, 'new': literal_new})
            bad.append((old, new.replace(literal_old, literal_new), config))
        overlapping = approved()
        overlapping['replacements'].append({'scope': 'runtime', 'old': 'runtime_old', 'new': 'runtime_new'})
        bad.append((old, new, overlapping))
        for source_old, source_new, config in bad:
            with self.subTest(config=config), self.assertRaises(research.ResearchError):
                research.validate_generated_delta(source_old, source_new, config, self.versions)

    def test_empty_or_ambiguous_region_identity_is_rejected(self):
        old, new = generated_pair()
        for source in ('', '/* arbitrary */\n'+old, old+research.THUNKS_START,
                       old.replace(research.RUNTIME_START, ''), old.replace(research.MODULE_START, '')):
            with self.assertRaises(research.ResearchError):
                research.validate_generated_delta(source, new, approved(), self.versions)

    def test_nested_compiler_roots_normalize_only_paths_and_keep_stdlib_hashes(self):
        with tempfile.TemporaryDirectory(prefix='markdown-graph-') as folder:
            # The graph loader resolves paths, including Windows 8.3 temp aliases.
            root=Path(folder).resolve(); app=root/'src/main.ru'; app.parent.mkdir()
            app.write_text('same app', encoding='utf-8', newline='\n')
            roots=[root/'.ci/old',root/'.ci/new']
            graphs=[]
            for compiler in roots:
                source=compiler/'rulang/stdlib/密.ru'; source.parent.mkdir(parents=True)
                source.write_text('same stdlib', encoding='utf-8', newline='\n')
                graphs.append({str(app):None,str(source):None})
            with patch.object(research,'ROOT',root):
                old=research.graph_identity(graphs[0],roots[0]); new=research.graph_identity(graphs[1],roots[1])
                self.assertEqual(old,new)
                self.assertEqual(set(old),{'app/src/main.ru','compiler-stdlib/密.ru'})
                (roots[1]/'rulang/stdlib/密.ru').write_text('changed stdlib', encoding='utf-8', newline='\n')
                self.assertNotEqual(old,research.graph_identity(graphs[1],roots[1]))

    def test_nested_graph_fixture_resolves_noncanonical_temporary_spelling(self):
        with tempfile.TemporaryDirectory(prefix='markdown-graph-alias-') as folder:
            root = Path(folder).resolve()
            (root / 'spelling').mkdir()
            alias = root / 'spelling' / '..'
            self.assertNotEqual(alias, alias.resolve())
            with patch.object(tempfile, 'TemporaryDirectory', return_value=nullcontext(str(alias))):
                self.test_nested_compiler_roots_normalize_only_paths_and_keep_stdlib_hashes()

    def test_graph_source_outside_the_exact_roots_still_fails(self):
        with tempfile.TemporaryDirectory(prefix='markdown-graph-outside-') as folder:
            root = Path(folder).resolve()
            compiler = root / '.ci/compiler'
            for relative in ('outside.ru', 'src-other/other.ru', '.ci/compiler/rulang/other.ru'):
                source = root / relative
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_text('outside', encoding='utf-8', newline='\n')
                with self.subTest(relative=relative), patch.object(research, 'ROOT', root), \
                     self.assertRaisesRegex(research.ResearchError, '^graph_source_outside_roots$'):
                    research.graph_identity({str(source): None}, compiler)

    def test_baseline_compiler_identity_and_version_when_local_pin_available(self):
        roots = (ROOT / '.ci/ru-research-baseline', ROOT / '.ci/research-baseline')
        root = next((path for path in roots if path.is_dir()), None)
        if root is None:
            if sys.platform == 'win32':
                self.fail('Windows requires the pinned research baseline checkout for its compiler-interface control')
            self.skipTest('Independent local baseline checkout is absent on this non-Windows host')
        value = research.compiler_identity(root, approved()['old'])
        self.assertEqual(value['version'], '0.22.0')
        specifications=research.compiler_source_prefix_maps(root)
        self.assertEqual(specifications,[str(root)+'=research-compiler'])
        # Exercise the frozen compiler's actual public mapping API without emission.
        script=("import sys; sys.path.insert(0,sys.argv[1]); "
                "from rulang.source_paths import SourcePathMapper; "
                "mapper=SourcePathMapper([sys.argv[1]+'=research-compiler']); "
                "assert mapper(sys.argv[1]+'/rulang/stdlib/密.ru')=='research-compiler/rulang/stdlib/密.ru'")
        result=subprocess.run([sys.executable,'-I','-c',script,str(root)],capture_output=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr.decode())


class MatrixControls(unittest.TestCase):
    def test_two_repeats_equal_proofs_and_no_callback_regression_are_explicit(self):
        rows = sample_rows()
        for row in rows:
            if row['compiler'] == 'new' and row['mode'] == 'absent': row['result']['elapsed_us'] += 1
        result = research.summarize_samples(rows, approved()['expected_heap_size'])
        self.assertTrue(result['no_callback_observed_regression'])
        self.assertFalse(result['general_speedup_claimed'])
        self.assertEqual(result['heap_layout_delta_bytes'], 16)
        self.assertEqual([v['layout_delta_model_bytes'] for v in result['live_diagnostics']],
                         [16*row['result']['live_peak'] for row in rows])

    def test_adjacent_pairs_expose_a_repeat_regression_hidden_by_median(self):
        rows=sample_rows()
        rows[2]['result']['elapsed_us'] += 10
        rows[5]['result']['elapsed_us'] -= 10
        result=research.summarize_samples(rows,approved()['expected_heap_size'])
        self.assertFalse(result['no_callback_observed_regression'])
        self.assertTrue(result['no_callback_any_pair_regression'])
        self.assertEqual([(p['old_order'],p['new_order']) for p in result['adjacent_pairs']],
                         [(1,2),(4,3),(5,6),(8,7)])

    def test_wrong_count_order_schema_proof_layout_and_changed_binaries_fail(self):
        cases = [sample_rows()[:-1], sample_rows()+[sample_rows()[0]]]
        rows = sample_rows(); rows[0], rows[1] = rows[1], rows[0]; cases.append(rows)
        for location, key, value in ((None,'compiler','new'),(None,'extra',1),('result','folds',0),
                                    ('result','callback_entries',0),('result','heap_size',33),('result','live_samples',3125),
                                    ('binary_after','exe_sha256','9'*64)):
            rows=sample_rows(); target=rows[0] if location is None else rows[0][location]
            target[key]=value; cases.append(rows)
        for rows in cases:
            with self.assertRaises(research.ResearchError): research.summarize_samples(rows, approved()['expected_heap_size'])

    def test_nonfinite_negative_noninteger_or_overbound_memory_is_rejected(self):
        for key, values in (('sampling_calls', [0, -1, True, 2.5, 9999]),
                            ('valid_live_samples', [0, -1, True, 99]),
                            ('sampling_elapsed_ms', [-1, math.nan, math.inf, 1501]),
                            ('last_success_elapsed_ms', [-1, math.nan, math.inf, 1501]),
                            ('limit_bytes', [0, research.MEMORY_LIMIT_BYTES+1]),
                            ('interval_seconds', [.1]), ('exit_race_reads', [-1, 2])):
            for value in values:
                rows=sample_rows(); rows[0]['memory'][key]=value
                with self.subTest(key=key,value=value), self.assertRaises(research.ResearchError):
                    research.summarize_samples(rows, approved()['expected_heap_size'])
        for value in (-1, .5, True, math.nan, math.inf, research.MEMORY_LIMIT_BYTES+1):
            rows=sample_rows(); rows[0]['memory']['observed_max']['private_commit_bytes']=value
            with self.subTest(value=value), self.assertRaises(research.ResearchError):
                research.summarize_samples(rows, approved()['expected_heap_size'])

    def test_shared_deadline_never_expands_a_process_or_aggregate_budget(self):
        with patch.object(research.time, 'monotonic', return_value=100):
            self.assertEqual(research.remaining_seconds(110, 120), 10)
            self.assertEqual(research.remaining_seconds(300, 120), 120)
            with self.assertRaises(research.ResearchError): research.remaining_seconds(100, 120)


class LiveDiagnosticControls(unittest.TestCase):
    @staticmethod
    def source():
        source = InstrumentControls.source().replace('#include <stdint.h>\n',
            '#include <stdint.h>\n#include <stddef.h>\n'
            'typedef double Val; typedef int Env; typedef struct { char value[32]; } RuHeap;\n'
            'static size_t ru_live;\nstatic Val v_num(double value) { return value; }\n')
        for ident in range(3, 7):
            source += f'static Val ru_function_{ident}(Env *global, Val self, int call_line, Val *args) {{\n    return v_num(-1);\n}}\n'
        return source

    def test_real_c_sampling_excludes_initial_read_and_rejects_overflow(self):
        cc=shutil.which('gcc'); self.assertIsNotNone(cc)
        ids={'reset':'ru_function_3','peak':'ru_function_4','size':'ru_function_5','samples':'ru_function_6'}
        code=research.instrument_generated(self.source(),'ru_function_1','ru_function_2',ids)
        code += r"""
int main(void) {
    ru_live=9999;
    if (ru_function_2(0,0,0,0)!=0 || ru_md_research_live_samples!=0) return 1;
    if (ru_function_3(0,0,0,0)!=0 || ru_function_3(0,0,0,0)!=-1) return 2;
    ru_live=8;
    for (int i=0;i<3125;i++) ru_function_2(0,0,0,0);
    if (ru_function_4(0,0,0,0)!=-1) return 3;
    ru_live=10; ru_function_2(0,0,0,0);
    if (ru_function_4(0,0,0,0)!=10 || ru_function_5(0,0,0,0)!=32 || ru_function_6(0,0,0,0)!=3126) return 4;
    ru_md_research_live_samples=UINT64_MAX; ru_function_2(0,0,0,0);
    if (ru_md_research_live_samples!=UINT64_MAX || !ru_md_research_live_overflow || ru_function_6(0,0,0,0)!=-1) return 5;
    ru_md_research_live_samples=0; ru_md_research_live_overflow=0;
    ru_live=UINT64_C(9007199254740992); ru_function_2(0,0,0,0);
    if (!ru_md_research_live_overflow || ru_function_4(0,0,0,0)!=-1 || ru_function_6(0,0,0,0)!=-1) return 6;
    return 0;
}
"""
        with tempfile.TemporaryDirectory(prefix='markdown-live-c-') as folder:
            src=Path(folder)/'control.c'; binary=Path(folder)/('control.exe' if sys.platform=='win32' else 'control')
            src.write_text(code, encoding='utf-8', newline='\n')
            build=subprocess.run([cc,'-std=c99','-O2',str(src),'-o',str(binary)],capture_output=True,timeout=30)
            self.assertEqual(build.returncode,0,build.stderr.decode())
            result=subprocess.run([str(binary)],capture_output=True,timeout=5)
            self.assertEqual(result.returncode,0)
            self.assertEqual(result.stdout+result.stderr,b'')

    def test_live_output_numeric_counts_and_bounds_fail_closed(self):
        for field, value in (('live_samples',3125),('live_samples',3127),('live_samples',-1),
                             ('live_peak',0),('live_peak',-1),('live_peak',9007199254740992),
                             ('heap_size',0),('heap_size',4097),('heap_size','nan')):
            with self.subTest(field=field,value=value), self.assertRaises(research.ResearchError):
                research.parse_sample(sample_line(**{field:value}),'present')

    def test_fixture_publication_loop_and_existing_proofs_are_byte_identical(self):
        current=(ROOT/research.SOURCE).read_text(encoding='utf-8')
        original=subprocess.check_output(['git','-C',str(ROOT),'show',research.BASE_COMMIT+':'+research.SOURCE],timeout=20).decode()
        begin='        起 取 折 其 时刻.\n'; end='        用时 取 (折 其 时刻)-起.\n'
        self.assertEqual(current[current.index(begin):current.index(end)+len(end)],
                         original[original.index(begin):original.index(end)+len(end)])
        self.assertEqual(hashlib.sha256((ROOT/research.SOURCE).read_bytes()).hexdigest(), research.FIXTURE_SHA256)
        self.assertEqual(current.count('前 取 研究计数.'),1)
        self.assertEqual(current.count('后 取 研究计数.'),1)
        self.assertLess(current.index("须 (研究堆重置 == 0)"),current.index(begin))
        self.assertGreater(current.index('堆峰 取 研究堆峰值.'),current.index(end))


class MemoryControls(unittest.TestCase):
    def run_child(self, reader, program='import time; time.sleep(.65)', timeout=3):
        with tempfile.TemporaryDirectory(prefix='markdown-memory-') as folder, \
             patch.object(research,'read_process_memory',side_effect=reader):
            return research.run_private([sys.executable,'-I','-c',program],Path(folder),'sample-memory',timeout,monitor_memory=True)

    def test_sampling_is_external_bounded_and_symmetric(self):
        moments=[]
        def read(process):
            self.assertIsNone(process.poll()); moments.append(time.monotonic())
            return {key:42 for key in research.MEMORY_METRICS}
        result=self.run_child(read)
        self.assertTrue(research.command_succeeded(result))
        self.assertGreaterEqual(result['memory']['valid_live_samples'],1)
        self.assertEqual(result['memory']['sampling_calls'],len(moments))
        self.assertTrue(all(b-a>=.25 for a,b in zip(moments,moments[1:])))
        self.assertGreaterEqual(result['memory']['sampling_elapsed_ms'],0)
        self.assertEqual(result['memory']['observed_max'],{key:42 for key in research.MEMORY_METRICS})

    def test_each_overbound_metric_or_invalid_read_stops_only_owned_child(self):
        for metric in research.MEMORY_METRICS:
            values={key:1 for key in research.MEMORY_METRICS}; values[metric]=research.MEMORY_LIMIT_BYTES+1
            result=self.run_child(lambda _:values,program='import time; time.sleep(20)')
            self.assertFalse(research.command_succeeded(result))
            self.assertTrue(result['memory_bound']); self.assertTrue(result['killed']); self.assertTrue(result['cleanup_confirmed'])
        for reader in (lambda _: (_ for _ in ()).throw(OSError('PRIVATE_MEMORY_ERROR')), lambda _: {'bad':1},
                       lambda _: {key:math.nan for key in research.MEMORY_METRICS}):
            result=self.run_child(reader,program='import time; time.sleep(20)')
            self.assertTrue(result['memory_error']); self.assertTrue(result['killed']); self.assertTrue(result['cleanup_confirmed'])
            self.assertNotIn('PRIVATE_MEMORY_ERROR',json.dumps(result))

    def test_only_api_failure_after_prior_live_read_can_be_an_exit_race(self):
        class FakeProcess:
            returncode = None
            pid = 123
            reads = 0
            def poll(self): return self.returncode
            def wait(self, timeout):
                if self.returncode is not None: return self.returncode
                now[0] += timeout
                raise subprocess.TimeoutExpired('synthetic-owned-child', timeout)
        for last_read, accepted in ((research.ProcessMemoryReadError('process_memory_read_failed'), True),
                                    (OSError('not an API false return'), False), ({'bad': 1}, False),
                                    ({key:-1 for key in research.MEMORY_METRICS}, False),
                                    ({key:math.nan for key in research.MEMORY_METRICS}, False)):
            now=[0.0]; process=FakeProcess()
            def read(owned):
                self.assertIs(owned, process); process.reads += 1
                if process.reads == 1: return {key: 1 for key in research.MEMORY_METRICS}
                process.returncode=0
                if isinstance(last_read, Exception): raise last_read
                return last_read
            with tempfile.TemporaryDirectory(prefix='markdown-memory-race-') as folder, \
                 patch.object(research.subprocess, 'Popen', return_value=process), \
                 patch.object(research, 'os', SimpleNamespace(name='nt')), \
                 patch.object(research.time, 'monotonic', side_effect=lambda: now[0]), \
                 patch.object(research, 'read_process_memory', side_effect=read):
                result=research.run_private(['synthetic'],Path(folder),'sample-race',3,monitor_memory=True)
            self.assertEqual(research.command_succeeded(result),accepted)
            self.assertEqual(result['memory']['valid_live_samples'],1)
            self.assertEqual(result['memory']['sampling_calls'],2)
            self.assertEqual(result['memory']['exit_race_reads'],int(accepted))
            self.assertEqual(result['memory_error'],not accepted)

    def test_windows_exited_root_overrun_does_not_claim_descendant_cleanup(self):
        class FinishedProcess:
            def poll(self): return 0
            def wait(self, timeout): return 0
        def spawn(*args, **kwargs):
            kwargs['stdout'].write(b'x'*(research.MAX_LOG_BYTES+1)); kwargs['stdout'].flush()
            return FinishedProcess()
        with tempfile.TemporaryDirectory(prefix='markdown-exit-cleanup-') as folder, \
             patch.object(research.subprocess,'Popen',side_effect=spawn), \
             patch.object(research,'os',SimpleNamespace(name='nt')):
            result=research.run_private(['synthetic'],Path(folder),'sample-exited',3)
        self.assertTrue(result['output_bound'])
        self.assertFalse(result['cleanup_confirmed'])
        self.assertFalse(result['killed'])
        self.assertFalse(research.command_succeeded(result))

    def test_api_failure_on_first_read_is_never_an_accepted_exit_race(self):
        result=self.run_child(lambda _: (_ for _ in ()).throw(research.ProcessMemoryReadError('process_memory_read_failed')))
        self.assertTrue(result['memory_error'])
        self.assertEqual(result['memory']['valid_live_samples'],0)
        self.assertEqual(result['memory']['exit_race_reads'],0)
        self.assertFalse(research.command_succeeded(result))

    def test_real_windows_quick_exit_and_low_cap_cleanup(self):
        if sys.platform!='win32': self.skipTest('Real GetProcessMemoryInfo requires Windows')
        with tempfile.TemporaryDirectory(prefix='markdown-windows-memory-') as folder:
            result=research.run_private([sys.executable,'-I','-c','pass'],Path(folder),'sample-fast',3,monitor_memory=True)
            self.assertTrue(research.command_succeeded(result))
            self.assertGreaterEqual(result['memory']['valid_live_samples'],1)
            with patch.object(research,'MEMORY_LIMIT_BYTES',1):
                result=research.run_private([sys.executable,'-I','-c','import time; time.sleep(20)'],
                                            Path(folder),'sample-cap',3,monitor_memory=True)
            self.assertTrue(result['memory_bound']); self.assertTrue(result['killed']); self.assertTrue(result['cleanup_confirmed'])
    def test_real_windows_timeout_cleans_explicitly_owned_descendant(self):
        if sys.platform!='win32': self.skipTest('Owned-tree Windows cleanup requires Windows')
        import ctypes
        from ctypes import wintypes
        program = "import subprocess,sys,time; p=subprocess.Popen([sys.executable,'-I','-c','import time; time.sleep(20)']); print(p.pid,flush=True); time.sleep(20)"
        with tempfile.TemporaryDirectory(prefix='markdown-descendant-') as folder:
            directory=Path(folder)
            result=research.run_private([sys.executable,'-I','-c',program],directory,'sample-descendant',1,monitor_memory=True)
            pid=int((directory/'sample-descendant.stdout').read_text(encoding='utf-8').strip())
            kernel=ctypes.WinDLL('kernel32',use_last_error=True)
            kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]; kernel.OpenProcess.restype=wintypes.HANDLE
            kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]; kernel.WaitForSingleObject.restype=wintypes.DWORD
            kernel.CloseHandle.argtypes=[wintypes.HANDLE]; kernel.CloseHandle.restype=wintypes.BOOL
            handle=kernel.OpenProcess(0x00100000,False,pid)
            if handle:
                try: state=kernel.WaitForSingleObject(handle,1000)
                finally: kernel.CloseHandle(handle)
                # Inspection only: never issue a late bare-PID kill after the
                # original root has exited, since a PID may have been reused.
                self.assertEqual(state,0,'Explicitly owned descendant survived cleanup')
            else:
                self.assertEqual(ctypes.get_last_error(),87,'Could not verify owned descendant exit')
            self.assertTrue(result['timeout']); self.assertTrue(result['killed']); self.assertTrue(result['cleanup_confirmed'])


class FullRunnerControls(unittest.TestCase):
    def exercise(self, failure=None):
        with tempfile.TemporaryDirectory(prefix='markdown-full-runner-') as temporary:
            root=Path(temporary).resolve(); binary=root/'bin'; binary.mkdir(); evidence=root/'evidence'
            dependencies={}
            for name in ('Scintilla.dll','Lexilla.dll','RuSyntax.dll'):
                (binary/name).write_bytes(name.encode()); dependencies[name]=research.sha(binary/name)
            identity={'research_compilers':{name:{'version':version} for name,version in research.COMPILER_VERSIONS.items()},
                      'dependency_sha256':dependencies}
            sample_calls=[]; build_calls=[]
            def fake_run(command, private, label, timeout, monitor_memory=False):
                self.assertGreater(timeout,0)
                role=private.name
                record={key:deepcopy(sample_rows()[0][key]) for key in research.RUN_FIELDS}
                record['memory']=None
                stdout=b''; stderr=b''
                if label=='emit':
                    build_calls.append((role,label)); self.assertLessEqual(timeout,120)
                    code=generated_pair()[role=='new']
                    for filename in ('original.c','instrumented.c'):
                        (private/filename).write_text(code, encoding='utf-8', newline='\n')
                    (private/'instrumentation.diff').write_text('SYNTHETIC_PRIVATE_DIFF', encoding='utf-8', newline='\n')
                    research.save(private/'emission.json',{'callback_function':'ru_function_1','reader_function':'ru_function_2',
                        'diagnostic_functions':{'reset':'ru_function_3','peak':'ru_function_4','size':'ru_function_5','samples':'ru_function_6'},
                        'full_application_graph':True,'module_count':21,'graph_source_sha256':{'app/src/main.ru':'9'*64},
                        'original_c_sha256':research.sha(private/'original.c'),'instrumented_c_sha256':research.sha(private/'instrumented.c'),
                        'instrumentation_diff_sha256':research.sha(private/'instrumentation.diff')})
                elif label=='resources':
                    build_calls.append((role,label)); self.assertLessEqual(timeout,30)
                    (private/'app-resource.o').write_bytes(b'synthetic-resource')
                elif label=='compile':
                    build_calls.append((role,label)); self.assertLessEqual(timeout,180)
                    (private/'markdown_callback_cost_native.exe').write_bytes(role.encode())
                else:
                    self.assertTrue(monitor_memory); self.assertLessEqual(timeout,120)
                    index=int(label.split('-')[1]); mode=command[-1]; sample_calls.append((role,mode))
                    record['memory']=deepcopy(sample_rows()[0]['memory'])
                    stdout=sample_line(mode,heap_size=32 if role=='old' else 48).encode()
                    if index==1 and failure:
                        record['memory_bound']=True; record['killed']=True
                        if failure=='cleanup': record['cleanup_confirmed']=False
                (private/(label+'.stdout')).write_bytes(stdout); (private/(label+'.stderr')).write_bytes(stderr)
                record.update(stdout_bytes=len(stdout),stderr_bytes=len(stderr),stdout_sha256=hashlib.sha256(stdout).hexdigest(),
                              stderr_sha256=hashlib.sha256(stderr).hexdigest())
                return record
            argv=['probe','--ru-root',str(root/'product'),'--old-ru-root',str(root/'old'),
                  '--new-ru-root',str(root/'new'),'--binary-dir',str(binary),'--evidence-dir',str(evidence),
                  '--cc',sys.executable,'--windres',sys.executable]
            with patch.object(research,'ROOT',root),patch.object(research,'os',SimpleNamespace(name='nt')), \
                 patch.dict(sys.modules,{'ctypes':SimpleNamespace(WinDLL=lambda _:object())}), \
                 patch.object(research,'load_approval',return_value=approved()), \
                 patch.object(research,'identities',return_value=identity), \
                 patch.object(research,'fixture_identity',return_value={'sha256':research.INPUT_SHA256}), \
                 patch.object(research,'run_private',side_effect=fake_run),patch.object(sys,'argv',argv),redirect_stdout(io.StringIO()):
                result=research.main()
            summary=json.loads((evidence/'markdown-callback-summary.json').read_text(encoding='utf-8'))
            for path in evidence.iterdir():
                self.assertNotIn(b'SYNTHETIC_PRIVATE_DIFF',path.read_bytes())
                self.assertNotIn(str(root).encode('utf-8'),path.read_bytes())
                self.assertNotIn(json.dumps(str(root), ensure_ascii=True)[1:-1].encode('utf-8'),path.read_bytes())
            return result,summary,sample_calls,build_calls

    def test_full_two_compiler_control_uses_eight_fresh_processes_and_sanitized_receipts(self):
        result,summary,samples,builds=self.exercise()
        self.assertEqual(result,0)
        self.assertEqual(samples,research.sample_order())
        self.assertEqual(builds,[('old','emit'),('new','emit'),('old','resources'),('old','compile'),('new','resources'),('new','compile')])
        self.assertEqual(summary['schema'],2)
        self.assertEqual(summary['status'],'passed')
        self.assertEqual(set(summary['final_binary_identity']),{'old','new'})
        self.assertFalse(summary['general_speedup_claimed'])
        self.assertTrue(all(row['binary_before']==row['binary_after'] for row in summary['samples']))
        self.assertIn('build_wall_ms',summary); self.assertIn('execution_wall_ms',summary); self.assertIn('research_wall_ms',summary)

    def test_fake_emission_is_exact_lf_under_windows_default_translation(self):
        original_write = Path.write_text
        c_writes = []
        def windows_write(path, data, encoding=None, errors=None, newline=None):
            result = original_write(path, data, encoding=encoding, errors=errors,
                                    newline='\r\n' if newline is None else newline)
            if path.name in ('original.c', 'instrumented.c'):
                c_writes.append(path.name)
                self.assertEqual(encoding, 'utf-8')
                self.assertEqual(path.read_bytes(), data.encode('utf-8'))
                self.assertNotIn(b'\r', path.read_bytes())
            return result
        with patch.object(Path, 'write_text', windows_write):
            result, summary, samples, builds = self.exercise()
        self.assertEqual(result, 0, summary.get('failure'))
        self.assertEqual(samples, research.sample_order())
        self.assertEqual(len(builds), 6)
        self.assertEqual(c_writes, ['original.c', 'instrumented.c'] * 2)
        # Fixture repair cannot make CRLF generated bytes pass the exact gate.
        old, new = generated_pair()
        with self.assertRaisesRegex(research.ResearchError, '^generator_banner_mismatch$'):
            research.validate_generated_delta(old.replace('\n', '\r\n'), new.replace('\n', '\r\n'),
                                              approved(), research.COMPILER_VERSIONS)

    def test_failed_sample_continues_only_with_confirmed_cleanup(self):
        result,summary,samples,_=self.exercise('memory')
        self.assertEqual(result,1); self.assertEqual(len(samples),8)
        self.assertEqual(summary['samples'][0]['failure_code'],'sample_memory_bound')
        self.assertEqual(summary['failure']['code'],'one_or_more_samples_failed')
        result,summary,samples,_=self.exercise('cleanup')
        self.assertEqual(result,1); self.assertEqual(len(samples),1)
        self.assertEqual(summary['failure']['code'],'sample_cleanup_unconfirmed')

    def test_unconfigured_file_still_prevents_any_process_launch(self):
        with tempfile.TemporaryDirectory(prefix='markdown-unconfigured-') as folder:
            config=Path(folder)/'unconfigured.json'
            value=research.load_approval()
            value.update(new=None,approval_commit=None,replacements=None,expected_heap_size={'old':32,'new':None})
            config.write_text(json.dumps(value), encoding='utf-8', newline='\n')
            with patch.object(research,'APPROVAL_FILE',config), \
                 patch.object(sys,'argv',['probe','--evidence-dir',folder]), \
                 patch.object(research,'run_private') as spawn, redirect_stdout(io.StringIO()):
                self.assertEqual(research.main(),1)
                spawn.assert_not_called()
                summary=json.loads((Path(folder)/'markdown-callback-summary.json').read_text(encoding='utf-8'))
                self.assertEqual(summary['failure']['code'],'new_compiler_not_approved')
                self.assertEqual(summary['samples'],[])


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

    def test_research_control_failure_is_caught_without_weakening_product_order(self):
        source=self.source()
        self.assertLess(source.index("'tools/test_windows_ci.py'"),source.index("'tools/test_package.py'"))
        self.assertLess(source.index("'tools/test_package.py'"),source.index('$ResearchControlsPassed = $false'))
        self.assertRegex(source,r"(?s)\$ResearchControlsPassed = \$false\s+try \{\s+Invoke-Checked \$Python @\('tools/test_markdown_callback_cost.py'\)\s+\$ResearchControlsPassed = \$true\s+\} catch \{")
        self.assertIn("failure = @{ stage = 'host_controls'; code = 'research_controls_failed' }",source)
        self.assertLess(source.index("'tools/test_markdown_callback_cost.py'"),source.index("'tools/check_static.py'"))
        self.assertLess(source.index("'tools/check_static.py'"),source.index('$BuildArgs ='))
        self.assertIn('Invoke-ResearchThenAcceptance $Python $ResearchArgs $AcceptArgs -ControlsPassed $ResearchControlsPassed',source)

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
            for research, product, controls in ((0,0,True),(7,0,True),(0,9,True),(7,9,True),
                                                  (0,0,False),(0,9,False)):
                with self.subTest(research=research, product=product, controls=controls):
                    marker = root / f'{research}-{product}-{controls}.log'
                    script = root / f'{research}-{product}-{controls}.ps1'
                    script.write_text(
                        "Set-StrictMode -Version Latest\n$ErrorActionPreference = 'Stop'\n" +
                        '\n'.join(functions) + '\n' +
                        '$Research = @(' + ','.join(map(quote, [child, marker, 'research', research])) + ')\n' +
                        '$Acceptance = @(' + ','.join(map(quote, [child, marker, 'product', product])) + ')\n' +
                        'Invoke-ResearchThenAcceptance ' + quote(sys.executable) +
                        ' $Research $Acceptance -ControlsPassed $' + str(controls).lower() + '\n', encoding='utf-8', newline='\n')
                    result = subprocess.run([pwsh, '-NoLogo', '-NoProfile', '-NonInteractive',
                                             '-File', str(script)], capture_output=True, timeout=20)
                    self.assertEqual(marker.read_text(encoding='utf-8').splitlines(),
                                     ['research','product'] if controls else ['product'])
                    self.assertEqual(result.returncode == 0, controls and research == product == 0)
                    self.assertEqual(b'MARKDOWN_CALLBACK_RESEARCH_FAILED=1' in result.stdout, controls and research != 0)
                    self.assertEqual(b'MARKDOWN_CALLBACK_RESEARCH_CONTROLS_FAILED=1' in result.stdout, not controls)


if __name__ == '__main__':
    unittest.main()
