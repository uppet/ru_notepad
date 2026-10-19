#!/usr/bin/env python3
"""Separate, fail-closed manual preview. Never changes formal acceptance.

Run prepare in the fresh Windows CI directory immediately before acceptance,
then package in its finally block. Only the named pending Markdown deadline
may be excepted. The same already-tested binaries are copied, never rebuilt.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import stat
import subprocess
import sys
import time
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parent))
import package as portable
import windows_ci as ci

ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = 'build/windows-ci'
SEAL_NAME = 'manual-preview-run.json'
OUTPUT_NAME = 'manual-preview'
SAMPLE_NAME = 'samples/fence.md'
SAMPLE_SIZE = 1000000
SAMPLE_SHA256 = '2d9f79ee715b217c00792cf18a67485cdec96a14ea2ac86689156941a022c719'
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_JSON_BYTES = 1024 * 1024
MD_NAME = 'main-gui-markdown'
DEADLINES = {'Markdown GUI open/edit exceeded its original 30-second deadline',
             'Markdown GUI final proof exceeded its original 30-second deadline'}
RUN_ERROR = 'Native acceptance test did not pass normally: main-gui-markdown'
FIXED_FILES = {'VERSION': 'VERSION', 'THIRD_PARTY_NOTICES.md': 'THIRD_PARTY_NOTICES.md',
    'packaging/licenses/Unicode.txt': 'licenses/Unicode.txt',
    'assets/README.md': 'licenses/Artwork-provenance.md'}
PREEXISTING_EVIDENCE = {'msys2-packages.log', 'source-archives.json', 'markdown-bulk-helper-controls.json'}
HELPER_STAGES = ('strict_parser_controls', 'report_ownership_controls', 'selected_compiler_target',
    'windows_compiler_version', 'host_compiler_version', 'compile_host_fixture', 'run_host_fixture',
    'host_controls', 'compile_windows_fixture', 'run_windows_fixture', 'windows_controls',
    'runtime_inputs_unchanged', 'source_and_compiler_inputs_unchanged')
HELPER_COMMANDS = {'selected_compiler_target', 'windows_compiler_version', 'host_compiler_version',
    'compile_host_fixture', 'run_host_fixture', 'compile_windows_fixture', 'run_windows_fixture'}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def safe_path(root, relative, *, directory=False, absent=False):
    """Reject links (including Windows reparse points) at every component."""
    rel = PurePosixPath(relative)
    require(isinstance(relative, str) and relative == rel.as_posix() and
            not rel.is_absolute() and relative and not any(p in ('', '.', '..') for p in rel.parts)
            and not any(c in relative for c in '\\:<>"|?*') and
            not any(ord(c) < 32 or ord(c) == 127 for c in relative) and
            all(p.rstrip(' .') == p for p in rel.parts), 'Unsafe preview path')
    root = Path(root).absolute()
    # Inspect ancestors too; resolving a link first would hide the link.
    for part in reversed((root, *root.parents)):
        info = part.lstat()
        require(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400,
                'Linked preview root')
    candidate = root
    for index, component in enumerate(rel.parts):
        candidate /= component
        final = index == len(rel.parts) - 1
        if final and absent:
            require(not candidate.exists() and not candidate.is_symlink(), 'Preview output already exists')
            return candidate
        info = candidate.lstat()
        require(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400,
                'Linked preview input')
        require(stat.S_ISDIR(info.st_mode) if not final or directory else stat.S_ISREG(info.st_mode),
                'Preview input is not an ordinary directory/file')
        if final and not directory:
            require(info.st_nlink == 1 and info.st_size <= MAX_FILE_BYTES, 'Linked or oversized preview file')
    return candidate


def read_bytes(root, relative, limit=MAX_FILE_BYTES):
    path = safe_path(root, relative)
    with path.open('rb') as stream:
        data = stream.read(limit + 1)
    require(len(data) <= limit, 'Oversized preview input')
    return data


def digest(data):
    return hashlib.sha256(data).hexdigest()


def strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'Duplicate JSON field')
            result[key] = value
        return result
    def constant(_):
        raise RuntimeError('Non-finite JSON number')
    try:
        return json.loads(data.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise RuntimeError('Invalid bounded UTF-8 JSON') from exc


def write_json(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as output:
        json.dump(value, output, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        output.write('\n')


def names():
    return {name for name, _ in ci.NATIVE_CONSOLE_TESTS} | ci.GUI_NAMES | {
        case[0] for case in ci.SYNTAX_FALLBACK_TESTS} | {'file_codec_security'}


def allowed_evidence():
    return portable.evidence_names(names() - ci.GUI_NAMES)


def git_identity(root):
    def git(*arguments):
        return subprocess.check_output(['git', '-C', str(root), *arguments], timeout=30).decode('utf-8')
    require(not git('status', '--porcelain').strip(), 'Preview requires a committed, clean source snapshot')
    commit, tree = git('rev-parse', 'HEAD').strip(), git('rev-parse', 'HEAD^{tree}').strip()
    require(all(re.fullmatch('[0-9a-f]{40}', v) for v in (commit, tree)), 'Invalid source identity')
    files = git('ls-files', '-z').split('\0')[:-1]
    require(0 < len(files) <= 4096 and len(files) == len(set(files)), 'Invalid tracked source inventory')
    return {'app_commit': commit, 'app_tree': tree,
            'tracked_source_sha256': {p: digest(read_bytes(root, p)) for p in files}}


def snapshot(root, objdump):
    binary = safe_path(root, RUN_ROOT + '/bin', directory=True)
    # Validate every receipt with strict JSON before existing receipt validation.
    receipt_names = [Path(name).with_suffix('.build.json').name
                     for name in (portable.RUNTIME_NAMES[0], *portable.TEST_NAMES)]
    receipt_names += [Path(name).stem + '.native-build.json' for name in portable.NATIVE_COMPILE_SOURCES]
    receipt_hashes = {}
    for name in receipt_names:
        raw = read_bytes(root, RUN_ROOT + '/bin/' + name, MAX_JSON_BYTES)
        strict_json(raw)
        receipt_hashes[name] = digest(raw)
    for name in portable.BINARY_NAMES:
        safe_path(root, RUN_ROOT + '/bin/' + name)
    portable.validate_dependency_sources(root)
    app, receipts, pe = portable.validate_receipts(root, binary, objdump)
    identity = git_identity(root)
    # This also binds docs, gate implementations, build scripts and all test sources.
    return {'source': identity, 'build_receipt_sha256': receipt_hashes,
            'tested_binary_sha256': {name: entry['sha256'] for name, entry in pe.items()}}, app, receipts, pe


def validate_helper_controls(root, binaries):
    import test_markdown_fold_helper as controls
    relative = RUN_ROOT + '/evidence/markdown-bulk-helper-controls.json'
    raw = read_bytes(root, relative, MAX_JSON_BYTES)
    record = strict_json(raw)
    require(isinstance(record, dict) and set(record) == {'schema', 'control', 'passed', 'real_windows_runtime',
        'sanitize', 'sources', 'stages', 'windows_compiler', 'host_compiler', 'host_test_binary',
        'windows_test_pe', 'runtime_dlls'} and type(record['schema']) is int and
            record.get('schema') == 1 and record.get('control') == 'markdown_bounded_fold_v1'
            and record.get('passed') is True and record.get('real_windows_runtime') is True
            and record.get('sanitize') is False, 'Actual Windows bulk-helper controls are required')
    require(record.get('runtime_dlls') == {name: {'bytes': safe_path(root, RUN_ROOT + '/bin/' + name).stat().st_size,
        'sha256': binaries[name]} for name in ('Scintilla.dll', 'RuSyntax.dll')}, 'Bulk-helper DLL binding mismatch')
    require(record.get('sources') == {name: {'bytes': len(read_bytes(root, name)),
        'sha256': digest(read_bytes(root, name))} for name in controls.SOURCES}, 'Bulk-helper source binding mismatch')
    stages = record.get('stages')
    require(isinstance(stages, list) and all(isinstance(s, dict) and s.get('passed') is True for s in stages) and
            [s.get('stage') for s in stages] == list(HELPER_STAGES),
            'Bulk-helper controls failed or skipped')
    for key in ('windows_compiler', 'host_compiler', 'host_test_binary', 'windows_test_pe'):
        value = record[key]
        require(isinstance(value, dict) and set(value) == {'bytes', 'sha256'} and type(value['bytes']) is int
            and 0 < value['bytes'] <= MAX_FILE_BYTES and isinstance(value['sha256'], str)
            and re.fullmatch('[a-f0-9]{64}', value['sha256']), 'Invalid helper compiler/test identity')
    for stage in stages:
        name = stage['stage']
        if name in HELPER_COMMANDS:
            require(set(stage) == {'stage', 'passed', 'owned_process', 'stdout', 'stderr'}, 'Missing owned helper command')
            owned = stage['owned_process']
            require(isinstance(owned, dict) and set(owned) == {'returncode', 'cleanup_confirmed', 'wall_ms',
                'stdout_bytes', 'stderr_bytes', 'stdout_sha256', 'stderr_sha256'} and
                type(owned['returncode']) is int and owned['returncode'] == 0 and owned['cleanup_confirmed'] is True
                and ci.finite_nonnegative(owned['wall_ms']), 'Helper command did not finish/clean normally')
            for stream in ('stdout', 'stderr'):
                measured = stage[stream]
                require(isinstance(measured, dict) and set(measured) == {'bytes', 'sha256', 'file_bytes', 'complete'} and
                    type(measured['bytes']) is int and 0 <= measured['bytes'] <= MAX_JSON_BYTES and
                    type(measured['file_bytes']) is int and measured['file_bytes'] == measured['bytes'] and
                    measured['complete'] is True and isinstance(measured['sha256'], str) and
                    re.fullmatch('[a-f0-9]{64}', measured['sha256']) and
                    type(owned[stream + '_bytes']) is int and owned[stream + '_bytes'] == measured['bytes'] and
                    owned[stream + '_sha256'] == measured['sha256'], 'Incomplete helper command output receipt')
            require(stage['stderr']['bytes'] == 0 and stage['stderr']['sha256'] == digest(b''),
                    'Helper command wrote unexpected errors')
        elif name in ('strict_parser_controls', 'report_ownership_controls'):
            expected = controls.parser_controls() if name == 'strict_parser_controls' else 3
            require(set(stage) == {'stage', 'passed', 'checks'} and type(stage['checks']) is int
                    and stage['checks'] == expected, 'Missing helper parser/ownership checks')
        elif name == 'host_controls':
            require(set(stage) == {'stage', 'passed', 'checks', 'real_windows_runtime', 'qualification_boundaries'} and
                type(stage['checks']) is int and stage['checks'] == controls.EXPECTED_HOST_CHECKS and
                stage['real_windows_runtime'] is False and type(stage['qualification_boundaries']) is int and
                stage['qualification_boundaries'] == controls.EXPECTED_QUALIFICATION_BOUNDARIES,
                'Missing shared-core helper checks')
        elif name == 'windows_controls':
            require(set(stage) == {'stage', 'passed', 'checks', 'real_windows_runtime', 'cross_thread'} and
                type(stage['checks']) is int and stage['checks'] == controls.EXPECTED_WINDOWS_CHECKS and
                stage['real_windows_runtime'] is True and stage['cross_thread'] is True,
                'Missing actual Windows/foreign-owner helper checks')
        else:
            require(set(stage) == {'stage', 'passed'}, 'Missing helper unchanged-input verification')
    return digest(raw)


def prepare(root, objdump):
    safe_path(root, RUN_ROOT, directory=True)
    safe_path(root, RUN_ROOT + '/evidence', directory=True)
    seal_path = safe_path(root, RUN_ROOT + '/' + SEAL_NAME, absent=True)
    safe_path(root, RUN_ROOT + '/' + OUTPUT_NAME, absent=True)
    # Only prebuild controls/MSYS2 evidence may preexist. Native outputs must be fresh.
    for name in allowed_evidence() - {'msys2-packages.log'}:
        safe_path(root, RUN_ROOT + '/evidence/' + name, absent=True)
    require({p.name for p in safe_path(root, RUN_ROOT + '/evidence', directory=True).iterdir()} ==
            PREEXISTING_EVIDENCE, 'Unexpected or missing pre-acceptance evidence')
    current, _, _, _ = snapshot(root, objdump)
    controls = validate_helper_controls(root, current['tested_binary_sha256'])
    preexisting = {p.name: digest(read_bytes(root, RUN_ROOT + '/evidence/' + p.name, MAX_JSON_BYTES))
                   for p in safe_path(root, RUN_ROOT + '/evidence', directory=True).iterdir()}
    seal = {'schema': 1, 'purpose': 'manual-preview-fresh-acceptance', 'run_id': secrets.token_hex(16),
            'prepared_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'snapshot': current, 'preexisting_evidence_sha256': preexisting,
            'bulk_helper_controls_sha256': controls}
    write_json(seal_path, seal)
    return {'run_id': seal['run_id'], 'status': 'prepared'}


def validate_other_test(test, summary):
    """The formal gate's existing subvalidators, without inventing a passing record."""
    name = test['name']
    require(test.get('passed') is True and test.get('executed') is True and
            test.get('cleanup_killed') is False and type(test.get('exit_code')) is int and
            test['exit_code'] == 0 and not test.get('skips') and 'error' not in test and
            'clock_error' not in test and test.get('seconds_valid', True) is True,
            'Non-Markdown acceptance group did not pass normally: ' + name)
    if name not in ci.GUI_NAMES:
        require(type(test.get('assertions_passed')) is int and test['assertions_passed'] == ci.expected_assertions(name),
                'Native assertion count mismatch')
    if name == 'markdown_direct_native':
        ci.validate_markdown_direct_gc(test.get('gc_stress'))
        ci.validate_markdown_route_metrics(test.get('bulk_route_metrics'))
    else:
        require('gc_stress' not in test and 'bulk_route_metrics' not in test, 'Unexpected native metrics')
    if name == 'ru_syntax_native':
        ci.validate_ru_performance(test.get('performance'))
    if name in ci.RU_GUI_CONSOLE_MEASUREMENTS:
        marker, key = ci.RU_GUI_CONSOLE_MEASUREMENTS[name]
        ci.validate_ru_gui_measurement(test.get(key), marker)
    if name in {case[0] for case in ci.SYNTAX_FALLBACK_TESTS}:
        require(test.get('fixture_binary_sha256') == {target: summary['tested_binary_sha256'][source]
            for target, source in ci.syntax_fallback_layout(name).items()}, 'Fallback binary binding mismatch')
    if name == 'syntax_bad_lexer':
        ci.validate_wrong_lexer_preflight(test.get('fixture_preflight'),
            summary['tested_binary_sha256'][portable.NATIVE_HELPER_NAME])
        require(test.get('native_fixture_preflight') is True, 'Native wrong-ABI fixture preflight missing')
    else:
        require('fixture_preflight' not in test and 'native_fixture_preflight' not in test, 'Unexpected fixture preflight')
    if name in ci.GUI_NAMES:
        require(all(test.get(k) is True for k in ('main_hwnd_seen', 'close_posted', 'detached_from_console')),
                'Ordinary GUI startup/close proof missing')
    if name == 'main-gui-ru-syntax':
        require(all(test.get(k) is True for k in ci.GUI_RU_CHECKS), 'Ru GUI checks missing')
        ci.validate_gui_ru_timer(test.get('timer_performance'), require_windows_clock=True)
        ci.validate_gui_ru_edits(test.get('edit_performance'))
    if name == 'main-gui-file-entry':
        require(all(test.get(k) is True for k in ci.GUI_FILE_CHECKS), 'File-entry safety checks missing')
    if name in {'main-gui-file-entry', 'main-gui-ru-syntax'}:
        require(test.get('fixture_binary_sha256') == {n: summary['tested_binary_sha256'][n]
            for n in portable.RUNTIME_NAMES}, 'GUI binary binding mismatch')


def validate_complete_stage(stage, kind, operation, source_hash):
    expected, styles, _ = ci.markdown_expected(kind, operation)
    validate_stage_metadata(stage, kind, operation, source_hash, timeout=False)
    ci.validate_markdown_progress(stage['last_progress'], complete=True,
                                  expected_length=len(expected), expected_dirty=stage['dirty'])
    last = stage['last_probe']
    require(isinstance(last, dict) and set(last) == {'length', 'dirty', 'end_styled', 'status_done',
        'styles_match', 'style_samples', 'folds_match', 'context_match', 'lexer', 'tail_requested', 'children_visible'},
        'Incomplete prior Markdown probe')
    require(type(last['length']) is int and last['length'] == len(expected) and
        last['dirty'] is stage['dirty'] and type(last['end_styled']) is int and last['end_styled'] == len(expected)
        and type(last['lexer']) is int and last['lexer'] == 98 and all(last[k] is True for k in
        ('status_done', 'styles_match', 'folds_match', 'context_match', 'tail_requested', 'children_visible')),
        'Prior Markdown style/fold/text probe failed')
    samples = last['style_samples']
    positions = [p for probe in styles for p in range(probe['offset'], probe['offset'] + probe['length'])]
    values = [probe['style'] for probe in styles for _ in range(probe['length'])]
    require(isinstance(samples, dict) and set(samples) == {'positions', 'expected', 'actual'} and
        all(isinstance(samples[k], list) and len(samples[k]) == 16 and all(type(v) is int for v in samples[k])
            for k in samples) and samples == {'positions': positions, 'expected': values, 'actual': values},
        'Prior Markdown fixed style samples mismatched')
    if kind == 'unclosed-fence' and operation == 'open':
        diagnostic = stage['last_progress']['diagnostic']
        require(diagnostic['bulkCalls'] >= 1 and diagnostic['bulkLines'] >= 1, 'Missing actual fence bulk route')
    if stage['dirty']:
        ci.validate_gui_markdown_responsiveness(stage['responsiveness'], stage['wall_ms'])
    else:
        require(stage['responsiveness'] == {}, 'Unexpected Markdown responsiveness')


def validate_stage_metadata(stage, kind, operation, source_hash, *, timeout):
    expected = ci.markdown_expected(kind, operation)[0]
    dirty = operation in ('insert', 'backspace')
    require(isinstance(stage, dict) and set(stage) == ci.GUI_MARKDOWN_STAGE_FIELDS,
            'Markdown stage schema changed or diagnostic failure recorded')
    require(stage['operation'] == operation and type(stage['length']) is int and stage['length'] == len(expected)
        and stage['dirty'] is dirty and stage['collapsed_before_edit'] is (kind == 'many-lines' and dirty)
        and stage['source_sha256'] == source_hash and ci.finite_nonnegative(stage['wall_ms'])
        and (30000 < stage['wall_ms'] <= 60000 if timeout else stage['wall_ms'] <= 30000)
        and type(stage['probes']) is int and stage['probes'] >= 1 and type(stage['undo_commands']) is int
        and (1 <= stage['undo_commands'] <= 2 if operation == 'undo' else stage['undo_commands'] == 0),
        'Invalid Markdown stage metadata/deadline')
    if timeout:
        validate_pending_observer(stage['observer'], stage['wall_ms'], stage['probes'])
    else:
        ci.validate_gui_ru_observer(stage['observer'], stage['wall_ms'], stage['probes'])
    ci.validate_markdown_memory(stage['memory'], stage['observer'], stage['wall_ms'])


def validate_pending_observer(record, wall_ms, probes):
    """Strict partial observer: no successful final snapshot is invented."""
    require(isinstance(record, dict) and set(record) == set(ci.gui_ru_observer_record()),
            'Pending observer schema mismatch')
    for field, value in [('response_interval_ms', 50), ('snapshot_interval_ms', 250), ('snapshot_message_limit', 32)]:
        require(type(record[field]) is int and record[field] == value, 'Pending observer policy changed')
    for field in ('scalar_calls', 'wm_null_calls', 'sendmessage_calls', 'snapshot_count', 'max_snapshot_messages'):
        require(type(record[field]) is int and record[field] >= 1, 'Pending observer missing actual calls')
    for field in ('query_wall_ms', 'max_query_ms', 'snapshot_wall_ms', 'max_snapshot_ms'):
        require(ci.finite_nonnegative(record[field]) and record[field] <= wall_ms + 0.01,
                'Pending observer cost invalid')
    require(record['wm_null_calls'] == probes and record['sendmessage_calls'] == record['scalar_calls'] + probes
        and record['max_query_ms'] <= record['query_wall_ms'] + 0.01, 'Pending observer calls disagree')
    starts = record['response_starts_ms']
    require(isinstance(starts, list) and len(starts) == probes and 1 <= len(starts) <= 601 and
        all(ci.finite_nonnegative(v) and v <= wall_ms for v in starts) and
        all(b - a >= 49.999 for a, b in zip(starts, starts[1:])), 'Pending observer frequency invalid')
    snapshots = record['snapshots']
    require(isinstance(snapshots, list) and 1 <= len(snapshots) <= 121 and
        record['snapshot_count'] == len(snapshots), 'Pending observer snapshot count invalid')
    for entry in snapshots:
        require(isinstance(entry, dict) and set(entry) == {'start_ms', 'wall_ms', 'messages', 'final'}
            and ci.finite_nonnegative(entry['start_ms']) and ci.finite_nonnegative(entry['wall_ms'])
            and entry['start_ms'] + entry['wall_ms'] <= wall_ms + 0.01 and entry['final'] is False
            and type(entry['messages']) is int and 1 <= entry['messages'] <= 32,
            'Pending observer snapshot invalid or contradictory completion')
    require(all(b['start_ms'] - a['start_ms'] >= 249.999 for a, b in zip(snapshots, snapshots[1:])) and
        record['max_snapshot_messages'] == max(s['messages'] for s in snapshots) and
        record['max_snapshot_ms'] == max(s['wall_ms'] for s in snapshots) and
        abs(record['snapshot_wall_ms'] - sum(s['wall_ms'] for s in snapshots)) <= 0.01 and
        sum(s['messages'] for s in snapshots) <= record['scalar_calls'], 'Pending observer totals disagree')


def validate_timeout(test, summary):
    require(summary.get('run_error') == RUN_ERROR and summary['passed'] is False and
        summary['native_tests_passed'] is False and test.get('passed') is False and
        test.get('executed') is True and test.get('main_hwnd_seen') is True and
        test.get('detached_from_console') is True and test.get('cleanup_killed') is True and
        test.get('close_posted') is False and 'exit_code' not in test and not test.get('skips') and
        test.get('error') in DEADLINES and test.get('source_bytes_preserved') is True and
        test.get('seconds_valid', True) is True and 'clock_error' not in test,
        'Only the explicitly measured pending Markdown deadline is preview-eligible')
    require(test.get('fixture_binary_sha256') == {n: summary['tested_binary_sha256'][n]
        for n in portable.RUNTIME_NAMES}, 'Markdown fixture binary binding mismatch')
    record = test.get('markdown_performance')
    require(isinstance(record, dict) and set(record) == {'measurement', 'clock', 'cases'} and
        record['measurement'] == ci.GUI_MARKDOWN_MEASUREMENT and isinstance(record['cases'], list)
        and 1 <= len(record['cases']) <= 3, 'Invalid timeout case prefix')
    ci.validate_performance_clock(record['clock'], require_windows=True)
    for case_index, case in enumerate(record['cases']):
        kind = ('many-lines', 'singleline', 'unclosed-fence')[case_index]
        data, probes, folds = ci.gui_markdown_fixture(kind)
        require(isinstance(case, dict) and set(case) == {'kind', 'size', 'source_sha256', 'style_probes', 'fold_probes', 'stages'}
            and case['kind'] == kind and type(case['size']) is int and case['size'] == len(data)
            and case['source_sha256'] == digest(data) and case['style_probes'] == probes and case['fold_probes'] == folds
            and all(type(p[k]) is int for p in case['style_probes'] for k in ('offset', 'length', 'style'))
            and all(type(p['line']) is int and type(p['header']) is bool for p in case['fold_probes'])
            and isinstance(case['stages'], list) and 1 <= len(case['stages']) <= 4, 'Invalid Markdown timeout corpus')
        final_case = case_index == len(record['cases']) - 1
        require(final_case or len(case['stages']) == 4, 'Incomplete stage before timeout case')
        for stage_index, stage in enumerate(case['stages']):
            operation = ('open', 'insert', 'backspace', 'undo')[stage_index]
            final = final_case and stage_index == len(case['stages']) - 1
            if not final:
                validate_complete_stage(stage, kind, operation, case['source_sha256'])
                continue
            validate_stage_metadata(stage, kind, operation, case['source_sha256'], timeout=True)
            progress = stage['last_progress']
            ci.validate_markdown_progress(progress)
            # Undo first restores the inserted byte (dirty), then the second
            # native undo restores clean source bytes. Both share the original
            # deadline; the producer sends the second only after first completion.
            first_undo_pending = (operation == 'undo' and stage['undo_commands'] == 1 and
                progress['length'] == stage['length'] + 1 and progress['dirty'] is True and
                progress['tail_requested'] is False)
            final_bytes_pending = (progress['length'] == stage['length'] and
                progress['dirty'] is stage['dirty'] and progress['tail_requested'] is True)
            require(progress['opened'] is True and (first_undo_pending or final_bytes_pending) and
                progress['status'] == 'folding' and isinstance(progress['diagnostic'], dict),
                'Deadline lacks actual opened pending progress')
            diagnostic = progress['diagnostic']
            require(diagnostic['pending'] == 1 and diagnostic['length'] == progress['length'] and
                diagnostic['tick'] > 0 and diagnostic['feed'] > 0 and diagnostic['phase'] in (1, 2, 3),
                'Deadline does not prove bounded pending work')
            # A final-probe record exists only after status complete. Its presence
            # on a pending deadline is inconsistent, even if individual flags pass.
            require(stage['last_probe'] == {}, 'Timeout includes contradictory final/style/fold evidence')
            if stage['dirty']:
                ci.validate_gui_markdown_responsiveness(stage['responsiveness'], stage['wall_ms'])
            else:
                require(stage['responsiveness'] == {}, 'Unexpected timeout responsiveness')
    return {'kind': kind, 'operation': operation, 'wall_ms': stage['wall_ms'],
            'pending_phase': diagnostic['phase'], 'feed_bytes': diagnostic['feed']}


def validate_summary(summary, root, binaries):
    require(isinstance(summary, dict) and set(summary) in ({'schema', 'platform', 'passed', 'synthetic_data_only',
        'tests', 'acl_requested', 'native_tests_passed', 'tested_binary_sha256', 'scanner_preflight'},
        {'schema', 'platform', 'passed', 'synthetic_data_only', 'tests', 'acl_requested', 'native_tests_passed',
         'tested_binary_sha256', 'scanner_preflight', 'run_error'}), 'Unexpected native acceptance schema')
    require(type(summary['schema']) is int and summary['schema'] == 1 and
        summary['platform'] == 'native-windows-x64' and summary['synthetic_data_only'] is True and
        summary['acl_requested'] is True and type(summary['passed']) is bool and
        type(summary['native_tests_passed']) is bool and summary['tested_binary_sha256'] == binaries,
        'Real Windows, mandatory ACL and exact binary receipt are required')
    tests = summary['tests']
    require(isinstance(tests, list) and len(tests) == len(names()) and
        all(isinstance(t, dict) and isinstance(t.get('name'), str) for t in tests) and
        {t['name'] for t in tests} == names(), 'Complete native/ACL/GUI inventory required')
    ci.validate_scanner_preflight(summary['scanner_preflight'], binaries, root)
    for test in tests:
        if test['name'] != MD_NAME:
            validate_other_test(test, summary)
    markdown = next(t for t in tests if t['name'] == MD_NAME)
    if summary['passed']:
        require(summary['native_tests_passed'] is True and 'run_error' not in summary,
                'Contradictory formal acceptance status')
        validate_other_test(markdown, summary)
        ci.validate_acceptance(summary, root)
        return {'formal_acceptance': 'passed', 'markdown_performance': 'passed', 'timeout': None}
    timeout = validate_timeout(markdown, summary)
    return {'formal_acceptance': 'failed', 'markdown_performance': 'performance_not_passed', 'timeout': timeout}


def validate_logs(root, summary):
    evidence = safe_path(root, RUN_ROOT + '/evidence', directory=True)
    portable.validate_native_evidence(evidence, summary, allowed_evidence())
    output = {}
    for name in sorted(allowed_evidence()):
        path = evidence / name
        if not path.exists() and not path.is_symlink():
            continue
        output[name] = read_bytes(root, RUN_ROOT + '/evidence/' + name, MAX_JSON_BYTES)
    scanner = portable.SCANNER_PREFLIGHT_NAME
    require(strict_json(output[scanner + '.stdout.log']) == summary['scanner_preflight']['report'] and
        not output[scanner + '.stderr.log'].strip(), 'Scanner log/receipt disagreement')
    for test in summary['tests']:
        name = test['name']
        if name in ci.GUI_NAMES:
            prefix = portable.GUI_EVIDENCE_PREFIXES[name]
            require(not any(prefix + '-' + str(i) + '.log' in output for i in range(1, 4)),
                    'GUI must have exactly one fresh launcher log')
            text = output[portable.GUI_EVIDENCE_PREFIXES[name] + '-0.log'].decode('utf-8', errors='strict')
            required = ['[launcher] Starting Ru program.', '[startup] menu installed',
                '[startup] initial document ready', '[startup] main window shown']
            if name != 'main-gui-smoke':
                required += ['[operation] open started', '[operation] open completed']
            if name == 'main-gui-file-entry':
                required += ['[operation] cancelled']
            if test['passed']:
                required += ['[launcher] Ru program returned with status 0.']
            require(all(marker in text for marker in required) and not re.search(
                r'initialization failed|exited before returning|fatal|FAIL:|FOLD_METRICS', text, re.I),
                'GUI log contains missing startup or a non-performance failure')
            continue
        stdout = output[name + '.stdout.log'].decode('utf-8', errors='strict')
        stderr = output[name + '.stderr.log'].decode('utf-8', errors='strict')
        marker = (r'^FILE_CODEC_SECURITY_TESTS_PASS\s*$' if name == 'file_codec_security' else
            dict(ci.NATIVE_CONSOLE_TESTS).get(name, r'^TOTAL PASS: 8\s*$'))
        require(len(re.findall(r'^PASS:', stdout, re.M)) == ci.expected_assertions(name) and
            len(re.findall(marker, stdout, re.M)) == 1 and
            len(re.findall(r'^(?:TOTAL PASS:|[A-Z][A-Z0-9_]*_TESTS_PASS(?:=|\b)).*$', stdout, re.M)) == 1 and
            'FAIL:' not in stdout + stderr and not re.search(r'^SKIP:', stdout + stderr, re.M),
            'Native log does not corroborate exact assertion receipt')
        if name == 'markdown_direct_native':
            require(ci.parse_markdown_direct_gc(stderr) == test['gc_stress'] and
                ci.parse_markdown_route_metrics(stdout) == test['bulk_route_metrics'], 'Native route/GC log mismatch')
        if name == 'syntax_bad_lexer':
            require(stdout.count(ci.WRONG_LEXER_PREFLIGHT_MARKER) == 1, 'Missing logged wrong-lexer ABI preflight')
    return output


def manual_text(eligibility):
    outcome = ('本轮完整 Windows 自动化验收通过；这仍是供人工体验的预览版。' if
        eligibility['formal_acceptance'] == 'passed' else
        '已知问题：本轮 Markdown 大文件任务超过原定 30 秒时限，正式验收失败。\n'
        '其余必需原生、文件安全、ABI 和 GUI 组通过；超时 GUI 被测试工具强制清理，不能称为正常退出。\n'
        '超时后的 Markdown 阶段没有完成，也不能视为通过。实际等待时间可能更长。')
    return ('ru_notepad Windows x64 人工体验预览\n\n' + outcome + '\n\n'
        '1. 完整解压 ZIP，保持 ru_notepad.exe 和三个 DLL 在同一目录，再运行程序。\n'
        '2. 用 Ctrl+O 打开 samples/fence.md；它是同一验收使用的 1,000,000 字节未闭合围栏样本。\n'
        '3. 观察打开及折叠等待时间；尝试移动光标、输入、退格、撤销和标题折叠。\n'
        '4. 仅用样本或文件副本测试。不要覆盖唯一的重要文件；没有崩溃恢复保证。\n'
        '5. 关闭时若提示保存样本，选择不保存。报告是否卡顿、出错及等待多久即可。\n\n'
        '程序未签名；不要关闭系统安全保护。中文输入法、高 DPI、无障碍与广泛日常使用仍需人工验证。\n'
        'BUILD.json 记录原始验收状态；独立 tests ZIP 保存本轮原始 JSON/日志，运行包不含测试 EXE 或源码包。\n'
        '本预览不改变 CI 的原始失败状态，也不等于人工验收通过。\n')


def zip_files(stage):
    files = {}
    for path in stage.rglob('*'):
        relative = path.relative_to(stage).as_posix()
        if path.is_dir() and not path.is_symlink():
            safe_path(stage, relative, directory=True)
        else:
            files[relative] = read_bytes(stage, relative)
    require(len(files) <= 512 and len({p.casefold() for p in files}) == len(files), 'Ambiguous ZIP inventory')
    return files


def verify_archive(path, expected):
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        require(len(entries) == len(expected) and len({i.filename.casefold() for i in entries}) == len(entries),
                'Duplicate or incorrect manual-preview ZIP inventory')
        prefix = path.stem + '/'
        actual = {}
        for entry in entries:
            require(entry.filename.startswith(prefix), 'Unexpected ZIP root')
            name = entry.filename[len(prefix):]
            rel = PurePosixPath(name)
            require(name == rel.as_posix() and not rel.is_absolute() and '..' not in rel.parts and
                '\\' not in name and ':' not in name and not entry.is_dir() and
                not stat.S_ISLNK(entry.external_attr >> 16) and entry.file_size <= MAX_FILE_BYTES,
                'Unsafe manual-preview ZIP entry')
            require(not name.lower().endswith('.zip') and not name.startswith(('vendor/', 'third_party/')),
                    'Source archive leaked into manual preview')
            actual[name] = archive.read(entry)
        require(actual == expected and archive.testzip() is None, 'Manual-preview ZIP readback mismatch')
    build = strict_json(actual['BUILD.json'])
    selected = portable.RUNTIME_NAMES if build['package_kind'] == 'manual-preview-runtime' else portable.BINARY_NAMES
    require(build['package_kind'] in ('manual-preview-runtime', 'manual-preview-tests') and
        {n for n in actual if n.lower().endswith(('.exe', '.dll'))} == set(selected), 'Executable inventory mismatch')
    require(actual[SAMPLE_NAME] == ci.gui_markdown_fixture('unclosed-fence')[0] and
        len(actual[SAMPLE_NAME]) == SAMPLE_SIZE and digest(actual[SAMPLE_NAME]) == SAMPLE_SHA256,
        'Manual-preview sample mismatch')
    if build['package_kind'] == 'manual-preview-runtime':
        require(not any(n.startswith('native-test-evidence/') or n.endswith(('.log', '.cmd', '.ps1')) for n in actual),
                'Test evidence leaked into runtime')
    return actual


def write_archive(stage, destination):
    files = zip_files(stage)
    sums = ''.join(f'{digest(value)}  {name}\n' for name, value in sorted(files.items()))
    (stage / 'SHA256SUMS.txt').write_text(sums, encoding='utf-8', newline='\n')
    files['SHA256SUMS.txt'] = sums.encode('utf-8')
    archive = destination / (stage.name + '.zip')
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as target:
        for name, value in sorted(files.items()):
            target.writestr(stage.name + '/' + name, value)
    verify_archive(archive, files)
    with archive.with_suffix('.zip.sha256').open('x', encoding='utf-8', newline='\n') as output:
        output.write(f'{portable.sha(archive)}  {archive.name}\n')
    return {'name': archive.name, 'sha256': portable.sha(archive), 'bytes': archive.stat().st_size,
            'inventory_sha256': {n: digest(v) for n, v in files.items()}}


def create_preview(root, objdump, copy_licenses):
    destination = safe_path(root, RUN_ROOT + '/' + OUTPUT_NAME, absent=True)
    seal_raw = read_bytes(root, RUN_ROOT + '/' + SEAL_NAME, MAX_JSON_BYTES)
    seal = strict_json(seal_raw)
    require(isinstance(seal, dict) and set(seal) == {'schema', 'purpose', 'run_id', 'prepared_utc', 'snapshot',
        'preexisting_evidence_sha256', 'bulk_helper_controls_sha256'} and seal['schema'] == 1 and
        seal['purpose'] == 'manual-preview-fresh-acceptance' and re.fullmatch('[a-f0-9]{32}', seal['run_id']),
        'Invalid fresh-run seal')
    current, app, receipts, pe = snapshot(root, objdump)
    require(current == seal['snapshot'], 'Source, build receipt or binary changed after preview prepare')
    require(validate_helper_controls(root, current['tested_binary_sha256']) == seal['bulk_helper_controls_sha256'],
            'Bulk-helper evidence changed during acceptance')
    evidence = safe_path(root, RUN_ROOT + '/evidence', directory=True)
    existing = seal['preexisting_evidence_sha256']
    require(isinstance(existing, dict) and set(existing) == PREEXISTING_EVIDENCE and
        set(p.name for p in evidence.iterdir()) <=
        set(existing) | allowed_evidence() | {'portable-artifact.json'}, 'Unexpected same-run evidence file')
    for name, expected in existing.items():
        require('/' not in name and digest(read_bytes(root, RUN_ROOT + '/evidence/' + name, MAX_JSON_BYTES)) == expected,
                'Preexisting evidence changed during acceptance')
    raw = read_bytes(root, RUN_ROOT + '/evidence/native-acceptance.json', MAX_JSON_BYTES)
    summary = strict_json(raw)
    eligibility = validate_summary(summary, root, current['tested_binary_sha256'])
    logs = validate_logs(root, summary)
    version = read_bytes(root, 'VERSION', 128).decode('utf-8').strip()
    require(re.fullmatch('[0-9A-Za-z.+-]+', version), 'Unsafe preview version')
    sample = ci.gui_markdown_fixture('unclosed-fence')[0]
    require(len(sample) == SAMPLE_SIZE and digest(sample) == SAMPLE_SHA256, 'Fixed sample changed')
    manifest = {'schema': 1, 'status': 'manual-preview', 'manual_acceptance': 'not_run', **eligibility,
        'run_id': seal['run_id'], 'run_seal_sha256': digest(seal_raw), 'source': current['source'],
        'build_receipt_sha256': current['build_receipt_sha256'],
        'tested_binary_sha256': current['tested_binary_sha256'], 'native_acceptance_sha256': digest(raw),
        'original_acceptance_passed': summary['passed'], 'original_native_tests_passed': summary['native_tests_passed'],
        'required_test_groups': len(names()), 'native_assertions': sum(ci.expected_assertions(n) for n in names() - ci.GUI_NAMES),
        'sample': {'name': SAMPLE_NAME, 'bytes': SAMPLE_SIZE, 'sha256': SAMPLE_SHA256},
        'runtime_binary_sha256': {n: current['tested_binary_sha256'][n] for n in portable.RUNTIME_NAMES}}
    destination.mkdir()
    try:
        artifacts = {}
        for kind in ('runtime', 'tests'):
            stage = destination / (
                f'ru_notepad-{version}-windows-x64-manual-preview' + ('-tests' if kind == 'tests' else ''))
            stage.mkdir()
            (stage / 'licenses').mkdir()
            selected = portable.RUNTIME_NAMES if kind == 'runtime' else portable.BINARY_NAMES
            for name in selected:
                data = read_bytes(root, RUN_ROOT + '/bin/' + name)
                require(digest(data) == current['tested_binary_sha256'][name], 'Binary changed during packaging')
                (stage / name).write_bytes(data)
            for source, name in FIXED_FILES.items():
                target = stage / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(read_bytes(root, source))
            for dependency in portable.DEPENDENCIES.values():
                (stage / 'licenses' / dependency['license']).write_bytes(
                    read_bytes(root, 'vendor/' + dependency['folder'] + '/License.txt'))
            copy_licenses(stage / 'licenses')
            (stage / 'samples').mkdir()
            (stage / SAMPLE_NAME).write_bytes(sample)
            (stage / '开始前请读.txt').write_text(manual_text(eligibility), encoding='utf-8', newline='\n')
            build = dict(manifest, package_kind='manual-preview-' + kind, ru_commit=app['ru_commit'], ru_tree=app['ru_tree'],
                         binaries={n: pe[n] for n in selected})
            write_json(stage / 'BUILD.json', build)
            if kind == 'tests':
                (stage / 'native-test-evidence').mkdir()
                for name, data in logs.items():
                    (stage / 'native-test-evidence' / name).write_bytes(data)
                for source, name in portable.TEST_FILES.items():
                    (stage / name).write_bytes(read_bytes(root, source))
            # Never trust a license callback to expand the executable/source set.
            files = zip_files(stage)
            mandatory = {*selected, *FIXED_FILES.values(), '开始前请读.txt', 'BUILD.json', SAMPLE_NAME,
                         *(f'licenses/{d["license"]}' for d in portable.DEPENDENCIES.values())}
            if kind == 'tests':
                mandatory |= {*portable.TEST_FILES.values(), *(f'native-test-evidence/{n}' for n in logs)}
            require(mandatory <= files.keys() and all(n in mandatory or n.startswith('licenses/MSYS2/') for n in files),
                    'Unexpected manual-preview file inventory')
            artifacts[kind] = write_archive(stage, destination)
        # Both ZIPs have already been read back; enforce runtime byte identity.
        require(all(artifacts[k]['inventory_sha256'][n] == manifest['runtime_binary_sha256'][n]
            for k in artifacts for n in portable.RUNTIME_NAMES), 'Runtime ZIP byte identity failed')
        require(read_bytes(root, RUN_ROOT + '/evidence/native-acceptance.json', MAX_JSON_BYTES) == raw and
            snapshot(root, objdump)[0] == current, 'Acceptance or source/binary changed during packaging')
        result = dict(manifest, packages=artifacts, runtime_byte_identity_verified=True)
        write_json(destination / 'preview-artifact.json', result)
        # The seal is retained for auditing; destination existence prevents reuse.
        return result
    except Exception:
        shutil.rmtree(destination)
        raise


def copy_checked_runtime_licenses(mingw, destination):
    source = safe_path(mingw, 'share/licenses', directory=True)
    for folder in source.iterdir():
        if folder.is_dir() and re.search(r'gcc|cc-libs|libstdc|libgcc|mingw|winpthread|crt|headers', folder.name, re.I):
            safe_path(mingw, folder.relative_to(mingw).as_posix(), directory=True)
            for path in folder.rglob('*'):
                safe_path(mingw, path.relative_to(mingw).as_posix(), directory=path.is_dir())
                if path.is_file():
                    require(path.stat().st_size <= MAX_JSON_BYTES, 'Oversized runtime license')
    ci.copy_runtime_licenses(mingw, destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'package'))
    parser.add_argument('--objdump', type=Path, required=True)
    parser.add_argument('--mingw-root', type=Path)
    args = parser.parse_args()
    if sys.platform != 'win32':
        parser.error('Manual preview requires the actual Windows acceptance host')
    if args.action == 'package' and args.mingw_root is None:
        parser.error('--mingw-root is required to preserve runtime licenses')
    try:
        if args.action == 'prepare':
            result = prepare(ROOT, args.objdump)
        else:
            result = create_preview(ROOT, args.objdump,
                lambda target: copy_checked_runtime_licenses(args.mingw_root, target))
        print(json.dumps({'status': result['status'], 'run_id': result['run_id']}, sort_keys=True))
    except Exception as exc:
        # Fixed public failure text avoids publishing arbitrary source/private paths.
        print('Manual preview refused: safety, freshness, evidence or inventory check failed.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
