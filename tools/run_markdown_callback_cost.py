#!/usr/bin/env python3
"""Four bounded real-Windows callback-cost samples; never product acceptance.

Production Ru and compiler/runtime stay unchanged. Two exact generated-C hooks
count entry to the production file_drop callback and read that integer from one
fixture-only stub. Same instrumented PE for ABBA fresh processes. Private C,
patch, build receipts and raw logs stay outside the uploaded evidence directory.
"""
from __future__ import annotations
import argparse
import ast
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
BASE_COMMIT = '133623e26ec13e294a5fac16bf28d7194d16bfea'
BASE_TREE = 'b796e7513caa2f06c2af2752e1bbdb27d6251f8d'
RU_COMMIT = 'a2f6faa0f914781dea74cb6f0a7574f1dd6808ce'
RU_TREE = '7b4331d51bc6ab2ec95fec1f8368465343fcd5af'
SOURCE = 'tests/markdown_callback_cost_native.ru'
INPUT_SHA256 = '2d9f79ee715b217c00792cf18a67485cdec96a14ea2ac86689156941a022c719'
SAMPLE_SECONDS = 120
TOTAL_SECONDS = 480
MAX_LOG_BYTES = 65536
MAX_BUILD_LOG_BYTES = 1024 * 1024
FLAGS = ['-std=c99', '-O2', '-Wall', '-Wextra', '-Wno-unused-function', '-static-libgcc']

class ResearchError(Exception):
    pass

def require(condition, code):
    if not condition:
        raise ResearchError(code)

def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()

def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8', newline='\n')

def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], timeout=20).decode().strip()

def sample_order():
    return ['present', 'absent', 'absent', 'present']

def instrument_generated(code: str, callback_id: str, reader_id: str) -> str:
    """Only insert callback-entry count and replace the fixture's exact stub."""
    for name in (callback_id, reader_id):
        require(re.fullmatch(r'ru_function_[0-9]+', name) is not None, 'invalid_function_id')
    require(callback_id != reader_id, 'duplicate_function_id')
    require('ru_md_research_' not in code, 'already_instrumented')
    header = lambda name: f'static Val {name}(Env *global, Val self, int call_line, Val *args) {{\n'
    require(code.count(header(callback_id)) == 1, 'callback_definition_mismatch')
    require(code.count(header(reader_id)) == 1, 'reader_definition_mismatch')
    require(code.count('#include <stdint.h>\n') == 1, 'stdint_include_mismatch')
    # No calls, allocation, timing or Win32 LastError access in this hook.
    declarations = ('static uint64_t ru_md_research_entries;\n'
                    'static int ru_md_research_overflow;\n')
    result = code.replace('#include <stdint.h>\n', '#include <stdint.h>\n' + declarations, 1)
    entry = ('    if (ru_md_research_entries == UINT64_MAX) ru_md_research_overflow = 1;\n'
             '    else ++ru_md_research_entries;\n')
    result = result.replace(header(callback_id), header(callback_id) + entry, 1)
    pattern = re.escape(header(reader_id)) + r'.*?^}\n'
    matches = list(re.finditer(pattern, result, re.MULTILINE | re.DOTALL))
    require(len(matches) == 1, 'reader_body_mismatch')
    body = (header(reader_id) + '    (void)global; (void)self; (void)call_line; (void)args;\n'
            '    if (ru_md_research_overflow || ru_md_research_entries > UINT64_C(9007199254740991))\n'
            '        return v_num(-1.0);\n'
            '    return v_num((double)ru_md_research_entries);\n}\n')
    match = matches[0]
    patched = result[:match.start()] + body + result[match.end():]
    restored = patched.replace(body, match.group(0), 1)
    restored = restored.replace(header(callback_id) + entry, header(callback_id), 1)
    restored = restored.replace('#include <stdint.h>\n' + declarations, '#include <stdint.h>\n', 1)
    require(restored == code, 'instrumentation_not_exactly_reversible')
    return patched

STARTUP_LINES = ['[startup] Scintilla loaded', '[startup] window class registered',
                 '[startup] main window created', '[startup] controls created',
                 '[startup] menu installed', '[startup] initial document ready']

PROOFS = {'assignments': 100002, 'batches': 1563, 'verified_lines': 100001,
          'verified_bytes': 1000000, 'state_checks': 1563, 'route_restored': 1,
          'initial_route_untouched': 1, 'text': 1, 'folds': 1, 'visible': 1,
          'expanded': 1, 'dirty': 1, 'selection': 1, 'undo': 1, 'teardown': 1}

def parse_sample(stdout: str, mode: str) -> dict:
    require(mode in ('present', 'absent'), 'invalid_mode')
    require(len(stdout.encode('utf-8')) <= MAX_LOG_BYTES, 'sample_output_bound')
    require('FAIL:' not in stdout, 'sample_failure_marker')
    lines = [line for line in stdout.splitlines() if line.startswith('MD_CALLBACK_RESULT ')]
    require(len(lines) == 1, 'sample_result_count')
    require(stdout.splitlines() == STARTUP_LINES + lines, 'sample_unexpected_output')
    fields = lines[0].split()[1:]
    require(all(re.fullmatch(r'[a-z_]+=[a-z0-9]+', item) for item in fields), 'sample_result_syntax')
    data = dict(item.split('=', 1) for item in fields)
    require(len(data) == len(fields), 'sample_duplicate_field')
    require(set(data) == set(PROOFS) | {'mode', 'elapsed_us', 'callback_entries'}, 'sample_result_fields')
    require(data.pop('mode') == mode, 'sample_mode_mismatch')
    require(all(re.fullmatch(r'0|[1-9][0-9]*', value) for value in data.values()), 'sample_number_syntax')
    values = {key: int(value) for key, value in data.items()}
    require(all(values[key] == value for key, value in PROOFS.items()), 'sample_proof_mismatch')
    require(0 < values['elapsed_us'] <= SAMPLE_SECONDS * 1000000, 'sample_time_bound')
    require(values['callback_entries'] == (310947 if mode == 'present' else 0), 'sample_callback_count')
    return {'mode': mode, **values}

def canonical(node):
    if hasattr(node, 'kind') and hasattr(node, 'data'):
        return [node.kind, canonical(node.data)]
    if isinstance(node, dict):
        return {k: canonical(v) for k, v in node.items()}
    if isinstance(node, (tuple, list)):
        return [canonical(v) for v in node]
    return node

def emit(ru_root, private):
    sys.path.insert(0, str(ru_root))
    from rulang.frontend import parse
    from rulang.modules import load_module_graph
    from rulang.compiler import Compiler
    source = ROOT / SOURCE
    program = parse(source.read_text(encoding='utf-8'))
    graph = load_module_graph(str(source), program)
    main_graph = load_module_graph(str(ROOT / 'src/main.ru'))
    require(set(graph) == set(main_graph) | {str(source.resolve())}, 'full_application_graph_mismatch')
    compiler = Compiler(program, graph.root, modules=graph, allow_native=True)
    callback_path = str((ROOT / 'src/file_drop.ru').resolve())
    callback = compiler.declarations[callback_path]['_编辑子过程']
    reader = compiler.declarations[graph.root]['研究计数']
    require(len(callback.data['params']) == 6, 'callback_ast_mismatch')
    stub = parse('算 研究计数:\n 得 -1.\n法\n')[0]
    require(canonical(reader) == canonical(stub), 'reader_ast_mismatch')
    callback_id = compiler.function_ids[id(callback)]
    reader_id = compiler.function_ids[id(reader)]
    code = compiler.compile()
    instrumented = instrument_generated(code, callback_id, reader_id)
    (private / 'original.c').write_text(code, encoding='utf-8', newline='\n')
    (private / 'instrumented.c').write_text(instrumented, encoding='utf-8', newline='\n')
    (private / 'instrumentation.diff').write_text(''.join(difflib.unified_diff(
        code.splitlines(True), instrumented.splitlines(True), fromfile='original.c', tofile='instrumented.c')), encoding='utf-8', newline='\n')
    save(private / 'emission.json', {'callback_function': callback_id, 'reader_function': reader_id,
         'full_application_graph': True, 'module_count': len(graph),
         'original_c_sha256': sha(private / 'original.c'), 'instrumented_c_sha256': sha(private / 'instrumented.c'),
         'instrumentation_diff_sha256': sha(private / 'instrumentation.diff')})

def fixture_identity():
    # Extract only the existing fixed corpus function; do not import the CI app.
    code = (ROOT / 'tools/windows_ci.py').read_text(encoding='utf-8')
    nodes = ast.parse(code).body
    functions = [n for n in nodes if isinstance(n, ast.FunctionDef) and n.name == 'gui_markdown_fixture']
    sizes = [n for n in nodes if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'GUI_MARKDOWN_BYTES' for t in n.targets)]
    require(len(functions) == len(sizes) == 1, 'corpus_definition_mismatch')
    require(ast.literal_eval(sizes[0].value) == 1000000, 'corpus_size_mismatch')
    scope = {'GUI_MARKDOWN_BYTES': 1000000}
    exec(compile(ast.Module(body=functions, type_ignores=[]), 'existing_corpus', 'exec'), scope)
    data, _, _ = scope['gui_markdown_fixture']('unclosed-fence')
    own = b'# Heading\n\n~~~\n' + (b'code text\n' * 131072)[:999977] + b'codebody'
    require(data == own and hashlib.sha256(data).hexdigest() == INPUT_SHA256 and data.count(b'\n') == 100000, 'corpus_bytes_mismatch')
    return {'kind': 'unclosed-fence', 'bytes': len(data), 'physical_lines': 100001,
            'sha256': INPUT_SHA256, 'policy_feed_calls': 977, 'policy_ranges': 979,
            'coalesced_ranges': 3, 'ordered_assignments': 100002}

def run_private(command, private, label, timeout):
    # Reuse the existing reviewed owned-process-tree cleanup. New session/group,
    # fixed file bounds, no PID search and no termination of unrelated tasks.
    from test_markdown_portable import stop_process_tree
    start = time.monotonic()
    out = private / (label + '.stdout')
    err = private / (label + '.stderr')
    limit = MAX_LOG_BYTES if label.startswith('sample-') else MAX_BUILD_LOG_BYTES
    timed_out = output_bound = killed = cleanup_failed = False
    options = {'creationflags': 0x00000200} if os.name == 'nt' else {'start_new_session': True}
    with out.open('xb') as stdout, err.open('xb') as stderr:
        process = subprocess.Popen(list(map(str, command)), cwd=ROOT, stdout=stdout, stderr=stderr, **options)
        try:
            while True:
                if out.stat().st_size > limit or err.stat().st_size > limit:
                    output_bound = True
                    break
                remaining = timeout - (time.monotonic() - start)
                if remaining <= 0:
                    timed_out = True
                    break
                try:
                    process.wait(timeout=min(0.05, remaining))
                    break
                except subprocess.TimeoutExpired:
                    pass
        except BaseException:
            if os.name != 'nt' or process.poll() is None:
                stop_process_tree(process)
            raise
        # A child can exceed a limit and exit between polling intervals.
        # Recheck even after wait reports zero, before admitting build output.
        timed_out = timed_out or time.monotonic() - start > timeout
        output_bound = output_bound or out.stat().st_size > limit or err.stat().st_size > limit
        if (timed_out or output_bound) and (os.name != 'nt' or process.poll() is None):
            killed = True
            try:
                stop_process_tree(process)
            except Exception:
                cleanup_failed = True
        code = process.poll()
    return {'returncode': code, 'timeout': timed_out, 'output_bound': output_bound,
            'killed': killed, 'cleanup_confirmed': not cleanup_failed,
            'wall_ms': round((time.monotonic()-start)*1000, 3),
            'stdout_sha256': sha(out), 'stderr_sha256': sha(err),
            'stdout_bytes': out.stat().st_size, 'stderr_bytes': err.stat().st_size}


def command_succeeded(record):
    return (record['returncode'] == 0 and not record['timeout'] and not record['killed']
            and not record['output_bound'] and record['cleanup_confirmed'])

def private_dependencies(private, expected):
    require(all((private / name).is_file() and not (private / name).is_symlink() for name in expected),
            'private_dependency_missing_or_linked')
    actual = {name: sha(private / name) for name in expected}
    require(actual == expected, 'private_dependency_changed')
    return actual

def identities(ru_root, binary_dir):
    require(git(ru_root, 'rev-parse', 'HEAD') == RU_COMMIT and
            git(ru_root, 'rev-parse', 'HEAD^{tree}') == RU_TREE and
            git(ru_root, 'status', '--porcelain') == '', 'compiler_pin_mismatch')
    require(git(ROOT, 'rev-parse', BASE_COMMIT + '^{tree}') == BASE_TREE, 'baseline_tree_mismatch')
    require(git(ROOT, 'rev-parse', 'HEAD^') == BASE_COMMIT, 'candidate_parent_mismatch')
    paths = git(ROOT, 'ls-tree', '-r', '--name-only', BASE_COMMIT, '--', 'src').splitlines()
    actual_paths = {p.relative_to(ROOT).as_posix() for p in (ROOT / 'src').rglob('*') if p.is_file()}
    require(actual_paths == set(paths), 'production_inventory_changed')
    require(all(not (ROOT / p).is_symlink() for p in paths), 'linked_production_source')
    production = {}
    for relative in paths:
        original = subprocess.check_output(['git', '-C', str(ROOT), 'show', BASE_COMMIT + ':' + relative], timeout=20)
        require((ROOT / relative).read_bytes() == original, 'production_source_changed')
        production[relative] = sha(ROOT / relative)
    import build
    snapshot = build.source_snapshot()
    receipt = json.loads((binary_dir / 'ru_notepad.build.json').read_text(encoding='utf-8'))
    require(receipt['ru_commit'] == RU_COMMIT and receipt['ru_tree'] == RU_TREE and
            receipt['entry_source'] == 'src/main.ru' and receipt['source_sha256'] == snapshot and
            receipt['exe_sha256'] == sha(binary_dir / 'ru_notepad.exe'), 'application_receipt_mismatch')
    require(receipt['build_input_sha256'] == {p: sha(ROOT / p) for p in build.build_input_paths(False)}, 'application_resource_mismatch')
    dependencies = {'Scintilla.dll': receipt['dll_sha256'], 'Lexilla.dll': receipt['lexilla_dll_sha256'],
                    'RuSyntax.dll': receipt['native_helper_sha256']}
    require(all(sha(binary_dir / name) == value for name, value in dependencies.items()), 'dependency_receipt_mismatch')
    return {'baseline_commit': BASE_COMMIT, 'baseline_tree': BASE_TREE, 'app_commit': git(ROOT, 'rev-parse', 'HEAD'),
            'ru_commit': RU_COMMIT, 'ru_tree': RU_TREE, 'production_sha256': production,
            'source_snapshot': snapshot, 'dependency_sha256': dependencies,
            'fixture_sha256': sha(ROOT / SOURCE), 'runner_sha256': sha(Path(__file__)),
            'application_receipt_sha256': sha(binary_dir / 'ru_notepad.build.json')}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ru-root', type=Path, required=True)
    parser.add_argument('--binary-dir', type=Path)
    parser.add_argument('--evidence-dir', type=Path)
    parser.add_argument('--cc')
    parser.add_argument('--windres')
    parser.add_argument('--_emit-child', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args._emit_child:
        emit(args.ru_root.resolve(), args._emit_child.resolve())
        return 0
    require(all((args.binary_dir, args.evidence_dir, args.cc, args.windres)), 'missing_runner_arguments')
    evidence = args.evidence_dir.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    private = ROOT / 'build/markdown-callback-private'
    summary = {'schema': 1, 'research_only': True, 'product_acceptance': 'not_claimed',
               'status': 'failed', 'sample_order': sample_order(), 'sample_timeout_seconds': SAMPLE_SECONDS,
               'total_execution_timeout_seconds': TOTAL_SECONDS, 'samples': [],
               'measurement': 'QPC around coalesced publication loop including fixed-size per-batch Ru checks and two counter reads; excludes policy feed, initialization and final full-state verification.',
               'counter': 'Actual entries into production file_drop Ru callback body, after the unchanged native callback trap; no per-entry allocation, QPC or LastError access.'}
    stage = 'preflight'
    try:
        require(os.name == 'nt', 'real_windows_required')
        import ctypes
        require(not hasattr(ctypes.WinDLL('ntdll'), 'wine_get_version'), 'wine_not_accepted')
        require(not private.exists(), 'fresh_private_build_required')
        private.mkdir(parents=True)
        identity = identities(args.ru_root.resolve(), args.binary_dir.resolve())
        summary['identity'] = identity
        summary['corpus'] = fixture_identity()
        save(private / 'identity-before.json', identity)
        stage = 'emit'
        emitted = run_private([sys.executable, Path(__file__).resolve(), '--ru-root', args.ru_root,
                               '--_emit-child', private], private, 'emit', 120)
        summary['build_attempts'] = {'emit': emitted}
        require(command_succeeded(emitted), 'emit_failed')
        metadata = json.loads((private / 'emission.json').read_text(encoding='utf-8'))
        stage = 'resources'
        resources = run_private([args.windres, '-I', ROOT / 'packaging', ROOT / 'packaging/app.rc',
                                 private / 'app-resource.o'], private, 'resources', 30)
        summary['build_attempts']['resources'] = resources
        require(command_succeeded(resources), 'resources_failed')
        stage = 'compile'
        exe = private / 'markdown_callback_cost_native.exe'
        command = [args.cc, *FLAGS, private / 'instrumented.c', '-o', exe, '-lm', private / 'app-resource.o']
        compiled = run_private(command, private, 'compile', 180)
        summary['build_attempts']['compile'] = compiled
        require(command_succeeded(compiled), 'compile_failed')
        for name, expected in identity['dependency_sha256'].items():
            shutil.copy2(args.binary_dir / name, private / name)
            require(sha(private / name) == expected, 'copied_dependency_mismatch')
        require(identities(args.ru_root.resolve(), args.binary_dir.resolve()) == identity, 'build_identity_changed')
        binary_sha = sha(exe)
        receipt = {'schema': 1, 'instrumented_research_binary': True, 'runtime_tested': False,
                   'exe_sha256': binary_sha, 'exe_bytes': exe.stat().st_size, **metadata,
                   'cc_sha256': sha(Path(shutil.which(args.cc) or args.cc).resolve()),
                   'windres_sha256': sha(Path(shutil.which(args.windres) or args.windres).resolve()),
                   'identity': identity, 'compiler_command': list(map(str, command)),
                   'build_logs': {'emit': emitted, 'resources': resources, 'compile': compiled}}
        save(private / 'research-build.json', receipt)
        summary['build'] = {k: v for k, v in receipt.items() if k not in ('compiler_command', 'identity')}
        summary['build']['private_receipt_sha256'] = sha(private / 'research-build.json')
        execution_start = time.monotonic()
        deadline = execution_start + TOTAL_SECONDS
        for index, mode in enumerate(sample_order(), 1):
            stage = 'sample_' + str(index)
            remaining = deadline - time.monotonic()
            require(remaining > 0, 'total_execution_timeout')
            require(sha(exe) == binary_sha, 'research_binary_changed')
            dependencies = private_dependencies(private, identity['dependency_sha256'])
            label = f'sample-{index:02d}-{mode}'
            record = run_private([exe, mode], private, label, min(SAMPLE_SECONDS, remaining))
            row = {'order': index, 'mode': mode, 'status': 'failed', 'exe_sha256': binary_sha,
                   'research_dependency_sha256': dependencies, **record}
            summary['samples'].append(row)
            # Public logs contain only a fixed schema, never raw native errors,
            # generated source, private paths, or compiler diagnostics.
            public_out = evidence / ('markdown-callback-' + label + '.stdout.log')
            public_err = evidence / ('markdown-callback-' + label + '.stderr.log')
            public_out.write_text(f'sample={index} mode={mode} status=failed\n', encoding='utf-8', newline='\n')
            public_err.write_text('details=private raw_sha256=' + record['stderr_sha256'] + '\n', encoding='utf-8', newline='\n')
            try:
                require(record['cleanup_confirmed'], 'sample_cleanup_unconfirmed')
                require(not record['timeout'], 'sample_timeout')
                require(command_succeeded(record), 'sample_nonzero_exit_or_kill')
                require(record['stdout_bytes'] <= MAX_LOG_BYTES and record['stderr_bytes'] == 0, 'sample_log_contract')
                result = parse_sample((private / (label + '.stdout')).read_text(encoding='utf-8-sig'), mode)
                require(result['elapsed_us'] <= record['wall_ms'] * 1000 + 2000, 'sample_qpc_exceeds_process_time')
                require(time.monotonic() <= deadline, 'total_execution_timeout')
                row['result'] = result
                row['status'] = 'passed'
                public_out.write_text(json.dumps(result, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
            except (ResearchError, UnicodeError) as exc:
                row['failure_code'] = str(exc) if isinstance(exc, ResearchError) else 'sample_encoding_invalid'
            save(evidence / 'markdown-callback-summary.json', summary)
            # A failed sample does not suppress independent remaining samples;
            # unconfirmed owned-process cleanup does stop further spawning.
            require(record['cleanup_confirmed'], 'sample_cleanup_unconfirmed')
        require(len(summary['samples']) == 4 and all(row['status'] == 'passed' for row in summary['samples']), 'one_or_more_samples_failed')
        require(identities(args.ru_root.resolve(), args.binary_dir.resolve()) == identity, 'final_identity_changed')
        require(sha(exe) == binary_sha, 'research_binary_changed')
        summary['research_dependency_sha256'] = private_dependencies(private, identity['dependency_sha256'])
        summary['execution_wall_ms'] = round((time.monotonic()-execution_start)*1000, 3)
        require(time.monotonic() <= deadline, 'total_execution_timeout')
        summary['median_elapsed_us'] = {mode: statistics.median(row['result']['elapsed_us'] for row in summary['samples'] if row['mode'] == mode)
                                        for mode in ('present', 'absent')}
        summary['status'] = 'passed'
        summary['all_samples_same_binary'] = True
        summary['complete_expected_state_match'] = True
        summary['full_windows_product_gates_unchanged'] = True
    except Exception as exc:
        if 'execution_start' in locals():
            summary['execution_wall_ms'] = round((time.monotonic()-execution_start)*1000, 3)
        summary['failure'] = {'stage': stage, 'code': str(exc) if isinstance(exc, ResearchError) else 'unexpected_research_failure'}
    save(evidence / 'markdown-callback-summary.json', summary)
    print('Markdown callback research: ' + summary['status'] + '; product acceptance remains separate.', flush=True)
    return 0 if summary['status'] == 'passed' else 1

if __name__ == '__main__':
    sys.exit(main())
