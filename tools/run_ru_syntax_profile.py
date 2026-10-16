#!/usr/bin/env python3
"""Bounded, synthetic, benchmark-only Windows styling evidence.

This does not package binaries or grant product acceptance. Production acceptance
stays in windows.yml. No emulation, platform override, or adjustable deadlines.
Private generated sources/build logs stay under build/profile; only collect's
schema-filtered JSON and numeric logs may be uploaded.
"""
from __future__ import annotations

import argparse
import hashlib
import functools
import importlib.util
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import windows_ci as acceptance
import package as portable

BASELINE_COMMIT = 'b525b47dab6a51494cde29a3aa468cfe2d14703a'
BASELINE_TREE = 'a1fb1a02abf76d80d3daf6f385edf29901264d73'
BASELINE_DOC_BLOB = 'df4d1d7af958f5f6518f6c47ede3c49a0ee2d346'
REVIEWED_DOC_SHA256 = '3d69bcaa9847d8d92d91f4b3a1ee432d2665efe97fce0e46638ef65bae5832af'
BASELINE_STREAMING_FIXTURE_BLOB = '6a205fbc1fd4f5a7449549dfcd3d26348a076a3d'
REVIEWED_STREAMING_FIXTURE_SHA256 = 'e31c4d389672d10a21d90113bb295907a977383fc527a4dbd2d1f589917d1b2e'
RU_COMMIT = acceptance.HELPER_POLICY_COMMIT
RU_TREE = acceptance.HELPER_POLICY_TREE
CORPUS_SHA256 = 'ecf8dca884444a5e54e1f40dc6af01cf5e7830ed6fe902d3adf6fdf255f9b3fa'
CORPUS = {'bytes': 1000000, 'scalars': 636370, 'newlines': 90909, 'sha256': CORPUS_SHA256}
OWNED = ('tools/profile_ru_syntax.py', 'native/profile_counters.h',
         'tools/run_ru_syntax_profile.py', 'tools/test_ru_syntax_profile.py',
         '.github/workflows/ru-syntax-profile.yml')
STAGES = ('scan_result', 'decoder', 'policy', 'publish')
KINDS = ('main_window', 'child_subclass', 'other')
LEVELS = ('off', 'counts', 'sampled')
UNITS = (('console_pipeline', 'full'), ('console_pipeline', 'ru_no_folding'),
         ('console_pipeline', 'lex_transport'), ('cooperative_console', 'full'), ('gui', 'full'))
BUILD_BUDGET_SECONDS = 1200
COMPILE_TIMEOUT_SECONDS = 180
STYLE_TIMEOUT_SECONDS = 30
MAX_PRIVATE_LOG_BYTES = 1024 * 1024
MAX_JSON_BYTES = 4 * 1024 * 1024
MAX_PUBLIC_BYTES = 32 * 1024 * 1024
MAX_SAFE_INTEGER = 9007199254740991
PROFILE_PREFIX = 'RU_SYNTAX_PROFILE '


class ProfileError(RuntimeError):
    """A stable, non-sensitive failure code suitable for public receipts."""


def require(ok, code):
    if not ok:
        raise ProfileError(code)


def sha(path):
    return portable.sha(path)


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate_json_key')
            result[key] = value
        return result
    def invalid(_):
        raise ProfileError('nonfinite_json_number')
    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid)
    except (ValueError, TypeError) as exc:
        raise ProfileError('invalid_json') from exc


def uint(value):
    return type(value) is int and 0 <= value <= MAX_SAFE_INTEGER


def number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def exact(obj, fields, code):
    require(type(obj) is dict and set(obj) == set(fields), code)


def unlinked(path, *, must_exist=True):
    """Reject symlinks and Windows junction/reparse paths, including parents."""
    path = Path(path).absolute()
    for part in (path, *path.parents):
        try:
            metadata = part.lstat()
        except FileNotFoundError:
            require(not must_exist or part != path, 'missing_owned_file')
            continue
        require(not stat.S_ISLNK(metadata.st_mode), 'linked_owned_path')
        require(not getattr(metadata, 'st_file_attributes', 0) & 0x400, 'reparse_owned_path')
    return path


def relative_file(root, name, *, must_exist=True):
    require(type(name) is str and 0 < len(name) <= 240, 'unsafe_relative_path')
    rel = PurePosixPath(name)
    require(not rel.is_absolute() and '..' not in rel.parts and '.' not in rel.parts
            and not any(x in name for x in ('\\', ':', '\x00')) and str(rel) == name,
            'unsafe_relative_path')
    root = unlinked(root)
    path = unlinked(root / rel, must_exist=must_exist)
    require(root in path.parents, 'outside_owned_root')
    if must_exist:
        require(path.is_file(), 'missing_owned_file')
    return path


def read_json(path):
    path = unlinked(path)
    require(path.is_file() and path.stat().st_size <= MAX_JSON_BYTES, 'oversize_json')
    return strict_json(path.read_text(encoding='utf-8'))


def save_json(path, data):
    path = unlinked(path, must_exist=False)
    encoded = (json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + '\n').encode('utf-8')
    require(len(encoded) <= MAX_JSON_BYTES, 'oversize_json')
    pending = unlinked(path.with_suffix(path.suffix + '.pending'), must_exist=False)
    with pending.open('xb') as out:
        out.write(encoded)
    os.replace(pending, path)


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], timeout=30).decode('utf-8').strip()


def matrix():
    """Off controls bookend the instrumented rows; every process is fresh."""
    rows = []
    schedule = [(p, m, 'off', 1) for p, m in UNITS]
    for index, (path, mode) in enumerate(reversed(UNITS)):
        for level in (('counts', 'sampled') if index % 2 == 0 else ('sampled', 'counts')):
            schedule.append((path, mode, level, 1))
    schedule += [(p, m, 'off', 2) for p, m in reversed(UNITS)]
    for index, (path, mode, level, repeat) in enumerate(schedule, 1):
        rows.append({'id': f'{index:02d}-{path}-{mode}-{level}-{repeat}',
                     'path': path, 'mode': mode, 'instrumentation': level,
                     'repeat': repeat, 'order': index})
    return rows


def verify_corpus():
    data, _ = acceptance.gui_ru_timer_fixture()
    actual = {'bytes': len(data), 'scalars': len(data.decode('utf-8')),
              'newlines': data.count(b'\n'), 'sha256': digest_bytes(data)}
    require(actual == CORPUS, 'corpus_identity_mismatch')
    require(acceptance.GUI_RU_TIMER_TIMEOUT_SECONDS == STYLE_TIMEOUT_SECONDS
            and acceptance.GUI_RU_RESPONSE_INTERVAL_MS == 50
            and acceptance.GUI_RU_SNAPSHOT_INTERVAL_MS == 250
            and acceptance.GUI_RU_SNAPSHOT_MESSAGE_LIMIT == 32,
            'production_deadline_or_observer_changed')
    return actual


def production_tree(root):
    """Recompute the frozen Git tree from current files; needs no old objects."""
    entries = subprocess.check_output(['git', '-C', str(root), 'ls-files', '--stage', '-z'], timeout=30)
    tree = {}
    hashes = {}
    for entry in entries.split(b'\0'):
        if not entry:
            continue
        metadata, raw_name = entry.split(b'\t', 1)
        mode, _, stage = metadata.decode('ascii').split()
        name = raw_name.decode('utf-8')
        require(stage == '0' and mode in ('100644', '100755'), 'unsupported_git_index_entry')
        if name in OWNED:
            continue
        data = relative_file(root, name).read_bytes()
        hashes[name] = digest_bytes(data)
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode('utf-8') + b'\0' + data).digest()
        if name == 'benchmarks/README.md':
            require(blob.hex() == BASELINE_DOC_BLOB or hashes[name] == REVIEWED_DOC_SHA256, 'unreviewed_benchmark_document')
            blob = bytes.fromhex(BASELINE_DOC_BLOB)
        if name == 'tests/app_streaming_native.ru':
            require(blob.hex() == BASELINE_STREAMING_FIXTURE_BLOB or hashes[name] == REVIEWED_STREAMING_FIXTURE_SHA256,
                    'unreviewed_streaming_fixture')
            blob = bytes.fromhex(BASELINE_STREAMING_FIXTURE_BLOB)
        node = tree
        parts = PurePosixPath(name).parts
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = (mode, blob)
    require(len(hashes) == 109, 'baseline_file_set_changed')
    def encode(node):
        contents = b''
        for name, value in sorted(node.items(), key=lambda item: (item[0] + ('/' if isinstance(item[1], dict) else '')).encode('utf-8')):
            mode, digest = ('40000', encode(value)) if isinstance(value, dict) else value
            contents += mode.encode('utf-8') + b' ' + name.encode('utf-8') + b'\0' + digest
        return hashlib.sha1(b'tree ' + str(len(contents)).encode('utf-8') + b'\0' + contents).digest()
    require(encode(tree).hex() == BASELINE_TREE, 'production_source_tree_changed')
    return hashes


def source_identity(root, ru_root):
    require(git(root, 'status', '--porcelain') == '', 'dirty_profile_checkout')
    require(git(ru_root, 'rev-parse', 'HEAD') == RU_COMMIT
            and git(ru_root, 'rev-parse', 'HEAD^{tree}') == RU_TREE, 'compiler_pin_mismatch')
    require(git(ru_root, 'status', '--porcelain') == '', 'dirty_compiler_checkout')
    hashes = production_tree(root)
    for name in OWNED:
        hashes[name] = sha(relative_file(root, name))
    return {'baseline_commit': BASELINE_COMMIT, 'baseline_tree': BASELINE_TREE,
            'profile_commit': git(root, 'rev-parse', 'HEAD'),
            'profile_tree': git(root, 'rev-parse', 'HEAD^{tree}'),
            'compiler_commit': RU_COMMIT, 'compiler_tree': RU_TREE, 'source_sha256': hashes,
            'reviewed_document_sha256': hashes['benchmarks/README.md'],
            'streaming_fixture_sha256': hashes['tests/app_streaming_native.ru']}


def native_windows():
    require(sys.platform == 'win32' and os.name == 'nt' and platform.machine().lower() in ('amd64', 'x86_64'),
            'real_windows_x64_required')
    return acceptance.Windows()  # Also rejects wine_get_version; no bypass flag.


def environment_record():
    return {'platform': 'native-windows-x64', 'os_version': platform.version(),
            'architecture': platform.machine(), 'logical_cpus': os.cpu_count(),
            'python_version': platform.python_version(), 'cpu': platform.processor()[:200],
            'cold_warm': 'fresh_process_os_cache_uncontrolled'}


def build_command(command, private, label, deadline):
    remaining = deadline - time.monotonic()
    require(remaining > 0, 'build_budget_exceeded')
    started = time.monotonic()
    out = unlinked(private / (label + '.stdout.log'), must_exist=False)
    err = unlinked(private / (label + '.stderr.log'), must_exist=False)
    record = {'stage': label, 'elapsed_seconds': 0.0, 'exit_code': None, 'error_code': None, 'cleanup_killed': False, 'cleanup_failed': False}
    try:
        with out.open('xb') as stdout, err.open('xb') as stderr:
            process = subprocess.Popen(list(map(str, command)), cwd=ROOT, stdout=stdout, stderr=stderr)
            try:
                while process.poll() is None:
                    require(out.stat().st_size <= MAX_PRIVATE_LOG_BYTES and err.stat().st_size <= MAX_PRIVATE_LOG_BYTES,
                            'build_log_limit_exceeded')
                    if time.monotonic() - started >= min(COMPILE_TIMEOUT_SECONDS, remaining):
                        raise ProfileError('compile_or_build_deadline_exceeded')
                    time.sleep(0.1)
                record['exit_code'] = process.returncode
                require(process.returncode == 0, 'build_command_failed')
            finally:
                if process.poll() is None:
                    try:
                        record['cleanup_killed'] = acceptance.cleanup_process(process)
                    except Exception as exc:
                        record['cleanup_failed'] = True
                        raise ProfileError('build_cleanup_failed') from exc
                record['exit_code'] = process.returncode
    except ProfileError as exc:
        record['error_code'] = str(exc)
        raise
    except Exception as exc:
        record['error_code'] = 'build_process_failed'
        raise ProfileError('build_process_failed') from exc
    finally:
        record['elapsed_seconds'] = round(time.monotonic() - started, 6)
        for path in (out, err):
            if path.exists():
                acceptance.cap_log(path)
        save_json(private / (label + '.json'), record)
    return record


def load_generator():
    spec = importlib.util.spec_from_file_location('profile_ru_syntax', ROOT / 'tools/profile_ru_syntax.py')
    require(spec is not None and spec.loader is not None, 'generator_unavailable')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_manifest(manifest, generated):
    required = {'schema', 'baseline_commit', 'baseline_tree', 'compiler_commit', 'compiler_tree', 'corpus',
                'baseline_inputs', 'units', 'phase_contract', 'counter_contract', 'prepare_elapsed_seconds', 'preflight'}
    exact(manifest, required, 'invalid_generator_manifest')
    require(manifest['schema'] == 1 and manifest['baseline_commit'] == BASELINE_COMMIT
            and manifest['baseline_tree'] == BASELINE_TREE and manifest['compiler_commit'] == RU_COMMIT
            and manifest['compiler_tree'] == RU_TREE and manifest['corpus'] ==
            {'sha256': CORPUS_SHA256, 'bytes': 1000000, 'scalars': 636370, 'newline_bytes': 90909},
            'generator_manifest_identity_mismatch')
    require(number(manifest['prepare_elapsed_seconds']) and type(manifest['counter_contract']) is str
            and type(manifest['phase_contract']) is str, 'invalid_generator_contract')
    for name, expected in manifest['baseline_inputs'].items():
        require(sha(relative_file(ROOT, name)) == expected, 'generator_baseline_input_mismatch')
    units = manifest['units']
    require(type(units) is list and len(units) == len(UNITS), 'invalid_generator_units')
    seen = set()
    for unit in units:
        exact(unit, ('id', 'path', 'mode', 'source', 'generated_c', 'exe_name', 'console', 'source_sha256',
                     'generated_c_sha256', 'graph_sha256', 'expected_pass_count', 'baseline_source'), 'invalid_generator_unit')
        key = (unit['path'], unit['mode'])
        require(key in UNITS and key not in seen and unit['id'] == '_'.join(key), 'unexpected_or_duplicate_generator_unit')
        seen.add(key)
        path = relative_file(generated, unit['generated_c'])
        require(sha(path) == unit['generated_c_sha256'] and sha(relative_file(generated, unit['source'])) == unit['source_sha256'],
                'generated_source_hash_mismatch')
        require(type(unit['graph_sha256']) is dict and 1 <= len(unit['graph_sha256']) <= 100, 'invalid_generated_graph')
        for name, checksum in unit['graph_sha256'].items():
            require(sha(relative_file(generated, name)) == checksum, 'generated_graph_hash_mismatch')
        expected_exe = {'console_pipeline': 'ru_syntax_profile.exe', 'cooperative_console': 'app_ru_native.exe', 'gui': 'ru_notepad.exe'}[key[0]]
        expected_source = {'console_pipeline': 'tests/ru_syntax_native.ru', 'cooperative_console': 'tests/app_ru_native.ru', 'gui': 'src/main.ru'}[key[0]]
        expected_pass = {'console_pipeline': 6, 'cooperative_console': 8, 'gui': None}[key[0]]
        require(unit['exe_name'] == expected_exe and type(unit['console']) is bool
                and unit['console'] == (key[0] != 'gui') and unit['baseline_source'] == expected_source
                and unit['expected_pass_count'] == expected_pass, 'generator_execution_layout_mismatch')
    return units


def validate_preflight_manifest(record, generated):
    exact(record, ('source', 'source_sha256', 'generated_c', 'generated_c_sha256', 'bridge_c', 'bridge_sha256',
                   'bridge_origin', 'bridge_origin_sha256', 'exe_name', 'dll_name', 'expected_marker', 'expected_pass_count'),
          'preflight_manifest_shape_mismatch')
    require(record['exe_name'] == 'profile_boundary.exe' and record['dll_name'] == 'profile_bridge.dll'
            and record['bridge_origin'] == 'tests/fixtures/native/c_backend_bridge.c'
            and record['bridge_sha256'] == record['bridge_origin_sha256'] ==
            '45689caba1b8552424a87dd6fd061818dbf1daab57d066461e7d91d93ea7e65f'
            and record['expected_marker'] == 'RU_SYNTAX_PROFILE_PREFLIGHT_TESTS_PASS=1'
            and record['expected_pass_count'] == 1, 'preflight_manifest_identity_mismatch')
    for path_key, hash_key in (('source', 'source_sha256'), ('generated_c', 'generated_c_sha256'), ('bridge_c', 'bridge_sha256')):
        require(sha(relative_file(generated, record[path_key])) == record[hash_key], 'preflight_source_hash_mismatch')
    return record


def prepare(ru_root, mingw_root):
    native_windows()
    root = ROOT / 'build/profile'
    require(not root.exists(), 'fresh_profile_directory_required')
    root.mkdir(parents=True)
    private = root / 'private'
    private.mkdir()
    started = time.monotonic()
    receipt = {'schema': 1, 'prepared': False, 'error_code': None,
               'corpus': verify_corpus(), 'matrix': matrix(), 'builds': [], 'commands': [], 'preflight_builds': [],
               'build_budget_seconds': BUILD_BUDGET_SECONDS,
               'compile_timeout_seconds': COMPILE_TIMEOUT_SECONDS,
               'initial_build_estimate_seconds': [120, 240]}
    try:
        receipt['identity'] = source_identity(ROOT, ru_root)
        receipt['environment'] = environment_record()
        deadline = started + BUILD_BUDGET_SECONDS
        bin_dir = unlinked(mingw_root / 'bin')
        compiler = relative_file(bin_dir, 'gcc.exe')
        windres = relative_file(bin_dir, 'windres.exe')
        receipt['toolchain'] = {'gcc_sha256': sha(compiler), 'windres_sha256': sha(windres),
                                'flags': ['-std=c99', '-O2', '-Wall', '-Wextra', '-Wno-unused-function', '-static-libgcc']}
        receipt['commands'].append(build_command([compiler, '--version'], private, 'gcc-version', deadline))
        receipt['toolchain']['gcc_version_log_sha256'] = sha(private / 'gcc-version.stdout.log')
        version_line = (private / 'gcc-version.stdout.log').read_text(encoding='utf-8', errors='strict').splitlines()[0]
        require(len(version_line) <= 256 and version_line.isprintable(), 'invalid_compiler_version')
        safe_text(version_line)
        receipt['toolchain']['gcc_version'] = version_line
        for name, item in portable.DEPENDENCIES.items():
            archive = relative_file(ROOT, 'vendor/downloads/' + item['archive'])
            require(sha(archive) == item['sha256'], 'dependency_archive_hash_mismatch')
            with zipfile.ZipFile(archive) as pinned:
                for member in pinned.infolist():
                    if not member.is_dir():
                        actual = relative_file(ROOT, 'vendor/' + member.filename)
                        require(actual.read_bytes() == pinned.read(member), 'dependency_source_changed')
        dlls = {'Scintilla.dll': ROOT / 'vendor/scintilla/bin/Scintilla.dll',
                'Lexilla.dll': ROOT / 'vendor/lexilla/bin/lexilla.dll'}
        receipt['dependencies'] = {name: {'sha256': sha(unlinked(path)), 'version': portable.DEPENDENCIES[name]['version'],
                                             'archive_sha256': portable.DEPENDENCIES[name]['sha256']}
                                   for name, path in dlls.items()}
        resource = root / 'app-resource.o'
        receipt['commands'].append(build_command([windres, '-I', ROOT / 'packaging', ROOT / 'packaging/app.rc', resource],
                                                   private, 'resource', deadline))
        helper = root / 'RuSyntax.dll'
        receipt['commands'].append(build_command([compiler, *portable.NATIVE_CFLAGS, ROOT / 'native/ru_scan.c', '-o', helper],
                                                   private, 'native-helper', deadline))
        dlls['RuSyntax.dll'] = helper
        receipt['dependencies']['RuSyntax.dll'] = {'sha256': sha(helper)}
        generated = root / 'generated'
        generator = load_generator()
        generation_started = time.monotonic()
        receipt['commands'].append(build_command([sys.executable, '-I', ROOT / 'tools/profile_ru_syntax.py',
            'prepare', '--ru-root', ru_root, '--output-dir', generated], private, 'generate', deadline))
        manifest = read_json(generated / 'manifest.json')
        receipt['generation_seconds'] = round(time.monotonic() - generation_started, 6)
        units = validate_manifest(manifest, generated)
        save_json(root / 'generator-manifest.json', manifest)
        preflight = validate_preflight_manifest(manifest.get('preflight'), generated)
        preflight_shared = root / 'preflight-shared'
        preflight_shared.mkdir()
        bridge = preflight_shared / 'profile_bridge.dll'
        receipt['commands'].append(build_command([compiler, '-std=c99', '-O2', '-Wall', '-Wextra',
            '-shared', '-static-libgcc', relative_file(generated, preflight['bridge_c']), '-o', bridge],
            private, 'preflight-bridge', deadline))
        for level in LEVELS:
            identifier = 'preflight-' + level
            destination = root / 'bin' / identifier
            destination.mkdir(parents=True)
            translation = root / (identifier + '.c')
            info = generator.instrument(input_c=relative_file(generated, preflight['generated_c']), output_c=translation,
                                        instrumentation=level, path='preflight', mode='full')
            audit_path = root / (identifier + '.instrumentation.json')
            save_json(audit_path, info)
            output = destination / 'profile_boundary.exe'
            compilation = build_command([compiler, *receipt['toolchain']['flags'], '-I', ROOT / 'native', translation,
                                          '-o', output, '-lm', resource], private, identifier, deadline)
            receipt['commands'].append(compilation)
            shutil.copyfile(bridge, destination / 'profile_bridge.dll')
            receipt['preflight_builds'].append({'id': identifier, 'instrumentation': level,
                'exe_sha256': sha(output), 'bridge_sha256': sha(bridge), 'generated_c_sha256': sha(translation),
                'instrumentation_receipt_sha256': sha(audit_path), 'seconds': compilation['elapsed_seconds'],
                'bridge_origin_sha256': preflight['bridge_sha256']})
        for unit in units:
            for level in LEVELS:
                require(time.monotonic() < deadline, 'build_budget_exceeded')
                identifier = unit['path'] + '-' + unit['mode'] + '-' + level
                destination = root / 'bin' / identifier
                destination.mkdir(parents=True)
                translation = root / (identifier + '.c')
                info = generator.instrument(input_c=relative_file(generated, unit['generated_c']),
                                            output_c=translation, instrumentation=level,
                                            path=unit['path'], mode=unit['mode'])
                require(type(info) is dict, 'invalid_instrumentation_receipt')
                audit_path = root / (identifier + '.instrumentation.json')
                save_json(audit_path, info)
                if not unit['console']:
                    gui_translation = root / (identifier + '-gui.c')
                    launcher = (ROOT / 'packaging/diagnostic_launcher.c').read_text(encoding='utf-8')
                    gui_translation.write_text('#define main ru_program_main\n' + translation.read_text(encoding='utf-8') +
                                               '\n#undef main\n' + launcher, encoding='utf-8')
                    translation = gui_translation
                output = destination / unit['exe_name']
                command = [compiler, *receipt['toolchain']['flags'], '-I', ROOT / 'native', translation, '-o', output, '-lm', resource]
                if not unit['console']:
                    command += ['-mwindows', '-lshell32', '-luser32']
                compilation = build_command(command, private, identifier, deadline)
                receipt['commands'].append(compilation)
                for name, source in dlls.items():
                    shutil.copyfile(source, destination / name)
                receipt['builds'].append({'id': identifier, 'path': unit['path'], 'mode': unit['mode'], 'instrumentation': level,
                                          'exe_name': unit['exe_name'], 'exe_sha256': sha(output),
                                          'generated_c_sha256': sha(translation), 'instrumentation_receipt_sha256': sha(audit_path),
                                          'seconds': compilation['elapsed_seconds'],
                                          'files': {p.name: sha(p) for p in sorted(destination.iterdir())}})
                save_json(root / 'prepare.json', receipt)
        require(receipt['identity'] == source_identity(ROOT, ru_root), 'inputs_changed_during_build')
        receipt['prepared'] = True
    except Exception as exc:
        receipt['error_code'] = str(exc) if isinstance(exc, ProfileError) else 'prepare_failed'
        raise
    finally:
        recorded = {item['stage'] for item in receipt['commands']}
        for path in sorted(private.glob('*.json')):
            command = read_json(path)
            if command.get('stage') not in recorded:
                receipt['commands'].append(command)
        receipt['elapsed_seconds'] = round(time.monotonic() - started, 6)
        receipt['estimate_exceeded'] = receipt['elapsed_seconds'] > 240
        save_json(root / 'prepare.json', receipt)
    return receipt


# The generator owns the runtime record fields. This closed schema is shared
# deliberately: accepting arbitrary JSON would leak paths and weaken evidence.
PROFILE_FIELDS = {'schema', 'path', 'mode', 'instrumentation', 'counter_interval', 'valid',
                  'started', 'complete', 'failure', 'generation', 'corpus', 'sampling', 'stages',
                  'counters', 'trace', 'raw_style_trace', 'callbacks'}
COUNTER_FIELDS = {'batches', 'alloc_requests', 'alloc_successes', 'alloc_requested_bytes',
                  'realloc_requests', 'realloc_successes', 'realloc_requested_bytes', 'env_creates',
                  'binding_creates', 'env_comparisons', 'token_calls', 'empty_fastpath_hits', 'fold_rows',
                  'gc_collections', 'gc_heap_scans', 'gc_marked', 'gc_freed', 'gc_work', 'peak_live',
                  'decoded_events', 'snapshot_words', 'feed_bytes', 'style_bytes', 'suffix_copy_bytes',
                  'suffix_validate_bytes', 'callback_max_depth', 'restores'}
TRACE_FIELDS = {'algorithm', 'value', 'batches', 'last_bytes', 'last_line', 'last_done'}
FAILURES = {'counter_overflow', 'clock_failure', 'clock_reversed', 'bad_checkpoint',
            'phase_depth_overflow', 'phase_depth_underflow', 'tick_depth_overflow', 'tick_depth_underflow',
            'unbalanced_batch_entry', 'unbalanced_interval_end', 'callback_depth_overflow', 'bad_callback_phase',
            'clock_overflow', 'calibration_in_active_interval', 'calibration_invalid', 'raw_style_null', 'raw_style_unsupported',
            'allocation_size_overflow', 'invalid_numeric_observation', 'invalid_event_observation',
            'invalid_style_observation', 'step_panic', 'generation_changed', 'target_changed', 'unbalanced_batch_end'}
PROFILE_CORPUS = {key: CORPUS[key] for key in ('sha256', 'bytes', 'scalars')}


def validate_profile(record, row, *, require_complete=True):
    exact(record, PROFILE_FIELDS, 'profile_shape_mismatch')
    require(record['schema'] == 1 and all(record[key] == row[key] for key in ('path', 'mode', 'instrumentation')),
            'profile_identity_mismatch')
    require(type(record['valid']) is bool and record['failure'] in (None, *FAILURES), 'invalid_profile_validity')
    require(record['corpus'] == PROFILE_CORPUS, 'profile_corpus_mismatch')
    if row['instrumentation'] == 'off':
        require(record['valid'] is True and record['failure'] is None and all(record[key] is None for key in
                ('counter_interval', 'started', 'complete', 'generation', 'trace', 'raw_style_trace', 'stages', 'counters', 'callbacks', 'sampling')),
                'off_contains_hot_recording')
        return record
    require(record['counter_interval'] == 'first_batch_to_last_batch' and uint(record['generation'])
            and type(record['started']) is bool and type(record['complete']) is bool, 'invalid_profile_interval')
    if require_complete:
        require(record['valid'] is True and record['failure'] is None and record['started'] is True
                and record['complete'] is True, 'profile_incomplete_or_invalid')
    exact(record['trace'], TRACE_FIELDS, 'trace_shape_mismatch')
    trace = record['trace']
    require(trace['algorithm'] == 'fnv1a64_le_u32_v1', 'unknown_trace_algorithm')
    require(type(trace['value']) is str and re.fullmatch('[0-9a-f]{16}', trace['value']), 'invalid_trace_checksum')
    require(all(uint(trace[key]) for key in ('batches', 'last_bytes', 'last_line', 'last_done'))
            and trace['last_done'] in (0, 1), 'invalid_trace_count')
    exact(record['counters'], COUNTER_FIELDS, 'counter_shape_mismatch')
    counters = record['counters']
    require(all(uint(value) for key, value in counters.items() if key not in ('suffix_copy_bytes', 'suffix_validate_bytes'))
            and counters['suffix_copy_bytes'] is None and counters['suffix_validate_bytes'] is None, 'invalid_counter_value')
    require(counters['alloc_successes'] <= counters['alloc_requests']
            and counters['realloc_successes'] <= counters['realloc_requests']
            and counters['empty_fastpath_hits'] <= counters['token_calls'], 'counter_invariants_failed')
    if require_complete:
        require(trace['batches'] == counters['batches'] == 8798 and trace['last_bytes'] == CORPUS['bytes']
                and trace['last_line'] == 90909 and trace['last_done'] == 1
                and counters['decoded_events'] == 454540 and counters['snapshot_words'] == 1818160
                and counters['style_bytes'] == counters['feed_bytes'] == CORPUS['bytes'],
                'production_trace_counts_mismatch')
        require(counters['fold_rows'] == (90910 if row['mode'] == 'full' else 0), 'fold_row_semantics_mismatch')
        require((counters['token_calls'] > 0) if row['mode'] == 'full' else counters['token_calls'] == 0,
                'structural_token_semantics_mismatch')
    exact(record['stages'], STAGES, 'stage_shape_mismatch')
    for stage in record['stages'].values():
        exact(stage, ('calls', 'sampled_calls', 'sampled_ns'), 'stage_record_shape_mismatch')
        require(all(uint(value) for value in stage.values()) and stage['sampled_calls'] <= stage['calls'],
                'invalid_stage_value')
        if require_complete:
            require(stage['calls'] > 0, 'stage_entry_evidence_missing')
            if row['instrumentation'] == 'sampled':
                require(stage['sampled_calls'] > 0 and stage['sampled_ns'] > 0, 'stage_sample_evidence_missing')
    exact(record['sampling'], ('stride', 'origin', 'sample_batches', 'clock_calls', 'total_clock_calls', 'frequency_hz', 'calibration'), 'sampling_shape_mismatch')
    sample = record['sampling']
    require(sample['stride'] == 64 and sample['origin'] == 'one_based_batch_divisible_by_64', 'sampling_schedule_changed')
    require(all(uint(sample[key]) for key in ('sample_batches', 'clock_calls', 'total_clock_calls', 'frequency_hz')), 'invalid_sampling_value')
    calibration = sample['calibration']
    if calibration is not None:
        exact(calibration, ('pairs', 'clock_calls', 'valid', 'min_ns', 'median_ns', 'p95_ns', 'max_ns'), 'calibration_shape_mismatch')
        require(uint(calibration['pairs']) and calibration['pairs'] <= 128 and uint(calibration['clock_calls'])
                and calibration['clock_calls'] == 2 * calibration['pairs'] and type(calibration['valid']) is bool,
                'calibration_invalid')
        if calibration['valid']:
            require(all(uint(calibration[key]) for key in ('min_ns', 'median_ns', 'p95_ns', 'max_ns'))
                    and calibration['min_ns'] <= calibration['median_ns'] <= calibration['p95_ns'] <= calibration['max_ns'],
                    'calibration_invalid')
        else:
            require(all(calibration[key] is None for key in ('min_ns', 'median_ns', 'p95_ns', 'max_ns')), 'calibration_invalid')
    if row['instrumentation'] == 'counts':
        require(sample['sample_batches'] == sample['clock_calls'] == sample['total_clock_calls'] == sample['frequency_hz'] == 0
                and calibration is None
                and all(s['sampled_calls'] == s['sampled_ns'] == 0 for s in record['stages'].values()),
                'counts_contains_hot_clocks')
    elif require_complete:
        require(calibration is not None and calibration['pairs'] == 128 and calibration['clock_calls'] == 256
                and calibration['valid'] is True
                and sample['total_clock_calls'] >= sample['clock_calls'] + calibration['clock_calls'], 'calibration_invalid')
        require(sample['sample_batches'] == counters['batches'] // 64 and sample['clock_calls'] > 0
                and sample['frequency_hz'] > 0, 'sampled_clock_evidence_missing')
    if record['raw_style_trace'] is not None:
        raw = record['raw_style_trace']
        exact(raw, ('algorithm', 'value', 'bytes', 'calls'), 'raw_style_trace_shape_mismatch')
        require(raw['algorithm'] == 'fnv1a64_bytes_v1' and type(raw['value']) is str
                and re.fullmatch('[0-9a-f]{16}', raw['value']) and uint(raw['bytes']) and uint(raw['calls']), 'raw_style_trace_invalid')
        if require_complete:
            require(raw['bytes'] == CORPUS['bytes'] and raw['calls'] == 8798, 'raw_style_trace_counts_mismatch')
    elif require_complete:
        raise ProfileError('raw_style_trace_missing')
    require(type(record['callbacks']) is list and len(record['callbacks']) <= 270, 'callback_shape_mismatch')
    seen = set()
    for callback in record['callbacks']:
        exact(callback, ('kind', 'depth', 'in_tick', 'phase', 'calls', 'heap_entries', 'roots'), 'callback_record_shape_mismatch')
        key = tuple(callback[field] for field in ('kind', 'depth', 'in_tick', 'phase'))
        require(callback['kind'] in KINDS and uint(callback['depth']) and callback['depth'] <= 8
                and type(callback['in_tick']) is bool and callback['phase'] in ('residual', *STAGES)
                and key not in seen, 'invalid_callback_bucket')
        seen.add(key)
        require(all(uint(callback[field]) for field in ('calls', 'heap_entries', 'roots')), 'invalid_callback_value')
    return record


def profile_from_logs(paths, row):
    records = []
    for path in paths:
        path = unlinked(path)
        require(path.stat().st_size <= MAX_PRIVATE_LOG_BYTES, 'runtime_log_limit_exceeded')
        for line in path.read_text(encoding='utf-8', errors='strict').splitlines():
            if line.startswith(PROFILE_PREFIX):
                records.append(strict_json(line[len(PROFILE_PREFIX):]))
    require(len(records) == 1, 'exactly_one_profile_record_required')
    return validate_profile(records[0], row, require_complete=False)


def public_outcome(result, row):
    """Never publish arbitrary exception text, process IDs, paths or source."""
    out = {'passed': result.get('passed') is True, 'executed': result.get('executed') is True,
           'cleanup_killed': result.get('cleanup_killed') is True,
           'exit_code': result.get('exit_code'), 'error_code': None if result.get('passed') else 'native_run_failed'}
    for key in ('main_hwnd_seen', 'close_posted', 'detached_from_console', 'assertions_passed', 'elapsed_seconds'):
        if key in result and (type(result[key]) is bool or number(result[key])):
            out[key] = result[key]
    if row['path'] == 'cooperative_console' and 'timer_performance' in result:
        acceptance.validate_ru_gui_measurement(result['timer_performance'], 'RU_GUI_TIMER', require_complete=False)
        out['timer_performance'] = result['timer_performance']
    if row['path'] == 'gui' and result.get('passed'):
        acceptance.validate_gui_ru_timer(result['timer_performance'], require_windows_clock=True)
        # This validated record contains only predefined synthetic probe data.
        timer = dict(result['timer_performance'])
        timer['last_probe'] = dict(timer['last_probe'])
        timer['last_probe']['status'] = 'verified_complete_nonempty_status'
        out['timer_performance'] = timer
        out['full_gui_checks'] = {key: result.get(key) is True for key in acceptance.GUI_RU_CHECKS}
    if row['path'] == 'gui' and not result.get('passed'):
        timer = result.get('timer_performance') or {}
        out['partial_timer_performance'] = {key: timer[key] for key in
            ('size', 'wall_ms', 'first_head_style_ms', 'max_response_ms', 'probes')
            if key in timer and number(timer[key])}
    return out


def stage_run_binaries(build, source, destination):
    """Every repeat gets a fresh owned directory; original stale-log gates stay intact."""
    require(not destination.exists(), 'fresh_run_binary_directory_required')
    destination.mkdir()
    for name, expected in build['files'].items():
        original = relative_file(source, name)
        require(sha(original) == expected, 'variant_binary_changed')
        target = relative_file(destination, name, must_exist=False)
        shutil.copyfile(original, target)
        require(sha(target) == expected, 'staged_variant_binary_changed')
    return destination


def run_matrix():
    api = native_windows()
    root = unlinked(ROOT / 'build/profile')
    prepared = validate_prepare_receipt(read_json(root / 'prepare.json'))
    require(git(ROOT, 'status', '--porcelain') == '' and git(ROOT, 'rev-parse', 'HEAD') == prepared['identity']['profile_commit']
            and git(ROOT, 'rev-parse', 'HEAD^{tree}') == prepared['identity']['profile_tree'], 'profile_source_changed_after_build')
    hashes = production_tree(ROOT)
    hashes.update({name: sha(relative_file(ROOT, name)) for name in OWNED})
    require(hashes == prepared['identity']['source_sha256'], 'profile_source_changed_after_build')
    require(prepared.get('prepared') is True, 'profile_build_incomplete')
    require(prepared.get('corpus') == verify_corpus() and prepared.get('matrix') == matrix(), 'prepared_plan_mismatch')
    require(not (root / 'runs').exists(), 'fresh_matrix_directory_required')
    (root / 'runs').mkdir()
    summary = {'schema': 1, 'complete': False, 'passed': False, 'preflight': [], 'preflight_passed': False,
               'runs': [], 'matrix': matrix(),
               'corpus': CORPUS, 'counter_interval_excluded': ['file_open_before_first_batch',
                   'initial_outer_callback_snapshot', 'refresh_after_last_batch'],
               'product_acceptance': {'separate': True, 'status': 'not_claimed'}}
    builds = {item['id']: item for item in prepared['builds']}
    preflight_logs = root / 'preflight-logs'
    preflight_logs.mkdir()
    for build in prepared['preflight_builds']:
        level = build['instrumentation']
        source = root / 'bin' / build['id']
        record = {'instrumentation': level, 'passed': False, 'error_code': None, 'outcome': None, 'boundary_check': None}
        summary['preflight'].append(record)
        try:
            require(sha(relative_file(source, 'profile_boundary.exe')) == build['exe_sha256']
                    and sha(relative_file(source, 'profile_bridge.dll')) == build['bridge_sha256'], 'preflight_binary_changed')
            logs = preflight_logs / level
            logs.mkdir()
            result = acceptance.run_console(api, 'profile_boundary', preflight_command(source), logs,
                r'^RU_SYNTAX_PROFILE_PREFLIGHT_TESTS_PASS=1\s*$', timeout=30, expected_assertions=1, cwd=source)
            record['outcome'] = public_outcome(result, {'path': 'preflight'})
            record['boundary_check'] = preflight_check_from_logs(sorted(logs.glob('*.log')), level)
            require(result.get('passed') is True and not result.get('cleanup_killed'), 'preflight_native_failed')
            validate_preflight_check(record['boundary_check'], level)
            record['passed'] = True
        except Exception as exc:
            record['error_code'] = str(exc) if isinstance(exc, ProfileError) else 'preflight_run_failed'
        finally:
            save_json(root / 'results.json', summary)
    summary['preflight_passed'] = len(summary['preflight']) == 3 and all(record['passed'] for record in summary['preflight'])
    if not summary['preflight_passed']:
        save_json(root / 'results.json', summary)
        return summary
    for row in matrix():
        record = dict(row, passed=False, error_code=None, profile=None, outcome=None, output_check=None)
        summary['runs'].append(record)
        run_dir = root / 'runs' / row['id']
        run_dir.mkdir()
        logs = run_dir / 'logs'
        logs.mkdir()
        fixtures = run_dir / 'fixtures'
        fixtures.mkdir()
        try:
            build_id = '-'.join(row[key] for key in ('path', 'mode', 'instrumentation'))
            require(build_id in builds, 'missing_variant_build')
            build = builds[build_id]
            source = stage_run_binaries(build, root / 'bin' / build_id, run_dir / 'bin')
            record['binary_sha256'] = build['exe_sha256']
            record['generated_c_sha256'] = build['generated_c_sha256']
            if row['path'] == 'cooperative_console':
                result = acceptance.run_native_console(api, 'app_ru_timer_native', r'^TOTAL PASS: 8\s*$', source, fixtures, logs)
            elif row['path'] == 'gui':
                result = acceptance.run_gui_ru_syntax(api, source, fixtures, logs)
            else:
                result = acceptance.run_console(api, 'profile_pipeline', [str(source / build['exe_name'])], logs,
                                                r'^TOTAL PASS: 6\s*$', timeout=60, expected_assertions=6,
                                                cwd=source)
            record['outcome'] = public_outcome(result, row)
            log_paths = sorted(logs.glob('*.log'))
            record['profile'] = profile_from_logs(log_paths, row)
            record['output_check'] = output_check_from_logs(log_paths)
            validate_output_check(record['output_check'])
            validate_profile(record['profile'], row)
            if row['path'] == 'console_pipeline':
                stdout = (logs / 'profile_pipeline.stdout.log').read_text(encoding='utf-8')
                record['outcome']['sync_performance'] = acceptance.parse_ru_gui_measurement(stdout, 'RU_GUI_SYNC')
            require(result.get('passed') is True and not result.get('cleanup_killed'), 'native_run_failed')
            record['passed'] = True
        except Exception as exc:
            record['error_code'] = str(exc) if isinstance(exc, ProfileError) else 'run_or_validation_failed'
        finally:
            save_json(run_dir / 'receipt.json', record)
            save_json(root / 'results.json', summary)
    summary['complete'] = True
    summary['passed'] = all(row['passed'] for row in summary['runs'])
    save_json(root / 'results.json', summary)
    return summary


PREFLIGHT_PREFIX = 'RU_SYNTAX_PROFILE_PREFLIGHT '


def preflight_command(source):
    return [str(relative_file(source, name).resolve()) for name in ('profile_boundary.exe', 'profile_bridge.dll')]


def validate_preflight_check(record, level, *, require_success=True):
    exact(record, ('schema', 'instrumentation', 'passed', 'first_longjmp', 'second_longjmp', 'trap_oom'),
          'preflight_check_shape_mismatch')
    require(record['schema'] == 1 and record['instrumentation'] == level and type(record['passed']) is bool
            and all(uint(record[key]) for key in ('first_longjmp', 'second_longjmp', 'trap_oom')), 'preflight_check_invalid')
    if require_success:
        require(record['passed'] is True and record['first_longjmp'] == 2
                and record['second_longjmp'] == record['trap_oom'] == 1,
                'preflight_boundary_unproven')
    return record


def preflight_check_from_logs(paths, level):
    records = []
    for path in paths:
        path = unlinked(path)
        require(path.stat().st_size <= MAX_PRIVATE_LOG_BYTES, 'preflight_log_limit_exceeded')
        for line in path.read_text(encoding='utf-8', errors='strict').splitlines():
            if line.startswith(PREFLIGHT_PREFIX):
                records.append(strict_json(line[len(PREFLIGHT_PREFIX):]))
    require(len(records) == 1, 'exactly_one_preflight_check_required')
    return validate_preflight_check(records[0], level, require_success=False)


OUTPUT_CHECK_PREFIX = 'RU_SYNTAX_PROFILE_CHECK '
OUTPUT_CHECK_FIELDS = {'schema', 'input_bytes', 'input_preserved', 'input_checksum', 'style_bytes',
                       'style_checksum', 'full_output_checked', 'expected_style_match', 'algorithm'}


def fnv1a64(data):
    value = 14695981039346656037
    for byte in data:
        value = ((value ^ byte) * 1099511628211) & 0xffffffffffffffff
    return f'{value:016x}'


@functools.lru_cache(maxsize=1)
def expected_input_checksum():
    data, _ = acceptance.gui_ru_timer_fixture()
    return fnv1a64(data)


@functools.lru_cache(maxsize=2)
def expected_style_checksum(raw=False):
    body = bytes((8, 8, 8, 0, 8 if raw else 4, 8 if raw else 4, 8 if raw else 4, 0, 3, 7, 0))
    tail = bytes([1] * 10 + [0] + [8 if raw else 4] * 3 + [0] + [3] * 6 + [7, 0])
    styles = body * 90907 + tail
    require(len(styles) == CORPUS['bytes'], 'expected_style_length_mismatch')
    return fnv1a64(styles)


def validate_output_check(record, *, require_success=True):
    exact(record, OUTPUT_CHECK_FIELDS, 'output_check_shape_mismatch')
    require(record['schema'] == 1 and record['algorithm'] == 'fnv1a64_bytes_v1', 'output_check_identity_mismatch')
    require(uint(record['input_bytes']) and uint(record['style_bytes'])
            and all(type(record[key]) is bool for key in ('input_preserved', 'full_output_checked', 'expected_style_match')),
            'invalid_output_check_values')
    if require_success:
        require(record['input_bytes'] == record['style_bytes'] == CORPUS['bytes']
                and all(record[key] is True for key in ('input_preserved', 'full_output_checked', 'expected_style_match')),
                'complete_byte_style_check_failed')
    for key in ('input_checksum', 'style_checksum'):
        require(type(record[key]) is str and re.fullmatch('[0-9a-f]{16}', record[key]), 'invalid_output_checksum')
    if require_success:
        require(record['input_checksum'] == expected_input_checksum(), 'complete_input_checksum_mismatch')
    return record


def output_check_from_logs(paths):
    records = []
    for path in paths:
        for line in unlinked(path).read_text(encoding='utf-8', errors='strict').splitlines():
            if line.startswith(OUTPUT_CHECK_PREFIX):
                records.append(strict_json(line[len(OUTPUT_CHECK_PREFIX):]))
    require(len(records) == 1, 'exactly_one_output_check_required')
    return validate_output_check(records[0], require_success=False)


def primary_wall(row):
    outcome = row.get('outcome') or {}
    measured = outcome.get('timer_performance') or {}
    if row['path'] in ('gui', 'cooperative_console'):
        value = measured.get('wall_ms')
    else:
        value = (outcome.get('sync_performance') or {}).get('wall_ms')
    require(number(value) and value > 0 and value <= STYLE_TIMEOUT_SECONDS * 1000, 'invalid_primary_wall')
    return value


def verify_results(summary):
    validate_results_receipt(summary)
    require(summary.get('schema') == 1 and summary.get('corpus') == CORPUS
            and summary.get('matrix') == matrix(), 'results_identity_mismatch')
    require(summary['preflight_passed'] is True and len(summary['preflight']) == 3, 'native_preflight_missing')
    for result in summary['preflight']:
        require(result['passed'] is True, 'native_preflight_failed')
        validate_preflight_check(result['boundary_check'], result['instrumentation'])
        outcome = result['outcome'] or {}
        require(outcome.get('passed') is True and outcome.get('executed') is True and outcome.get('exit_code') == 0
                and not outcome.get('cleanup_killed') and outcome.get('assertions_passed') == 1, 'native_preflight_failed')
    runs = summary.get('runs')
    require(type(runs) is list and len(runs) == 20 and summary.get('complete') is True, 'matrix_incomplete')
    for expected, actual in zip(matrix(), runs):
        require(all(actual.get(key) == value for key, value in expected.items()), 'matrix_order_or_row_mismatch')
        require(actual.get('passed') is True, 'matrix_contains_failure')
        validate_profile(actual.get('profile'), actual)
        outcome = actual.get('outcome') or {}
        require(outcome.get('passed') is True and outcome.get('executed') is True and not outcome.get('cleanup_killed')
                and outcome.get('exit_code') == 0,
                'matrix_native_outcome_invalid')
        if actual['path'] == 'gui':
            require(all(outcome.get(key) is True for key in ('main_hwnd_seen', 'close_posted', 'detached_from_console')),
                    'gui_normal_close_unproven')
            acceptance.validate_gui_ru_timer(outcome.get('timer_performance'), require_windows_clock=True)
            require(outcome.get('full_gui_checks') == {key: True for key in acceptance.GUI_RU_CHECKS}, 'gui_checks_incomplete')
            if actual['instrumentation'] != 'off':
                final = outcome['timer_performance']['diagnostics']['receipts'][-1]
                require(actual['profile']['generation'] == final['generation'], 'gui_generation_mismatch')
            final = outcome['timer_performance']['diagnostics']['receipts'][-1]
            require(final['chunks'] == 8798 and final['read_bytes'] == 1000000, 'gui_batch_progress_mismatch')
        elif actual['path'] == 'cooperative_console':
            acceptance.validate_ru_gui_measurement(outcome.get('timer_performance'), 'RU_GUI_TIMER')
            require(outcome.get('assertions_passed') == 8, 'cooperative_assertion_count_mismatch')
        else:
            acceptance.validate_ru_gui_measurement(outcome.get('sync_performance'), 'RU_GUI_SYNC')
            require(outcome.get('assertions_passed') == 6, 'pipeline_assertion_count_mismatch')
        if actual['path'] != 'gui':
            measured = outcome['timer_performance'] if actual['path'] == 'cooperative_console' else outcome['sync_performance']
            require(measured['chunks'] == 8798 and measured['max_read'] == 1023, 'console_batch_progress_mismatch')
        if actual['path'] in ('gui', 'cooperative_console') and actual['instrumentation'] != 'off':
            require(any(item['kind'] == 'child_subclass' and item['in_tick'] and item['calls'] > 0
                        for item in actual['profile']['callbacks']), 'nested_child_callback_evidence_missing')
        primary_wall(actual)
    instrumented = [r['profile']['trace'] for r in runs if r['instrumentation'] != 'off']
    require(all(trace == instrumented[0] for trace in instrumented), 'native_trace_mismatch')
    raw_traces = [r['profile']['raw_style_trace'] for r in runs if r['instrumentation'] != 'off']
    require(all(trace == raw_traces[0] for trace in raw_traces), 'raw_style_trace_mismatch')
    require(raw_traces[0]['value'] == expected_style_checksum(True), 'expected_raw_styles_mismatch')
    full_styles = set()
    for row in runs:
        require(row.get('output_check') is not None, 'complete_byte_style_evidence_missing')
        check = validate_output_check(row['output_check'])
        require(check['style_checksum'] == expected_style_checksum(row['mode'] == 'lex_transport'), 'expected_complete_styles_mismatch')
        if row['mode'] in ('full', 'ru_no_folding'):
            full_styles.add(check['style_checksum'])
    require(len(full_styles) == 1, 'full_and_no_folding_styles_differ')
    comparisons = []
    for path, mode in UNITS:
        subset = [r for r in runs if r['path'] == path and r['mode'] == mode]
        off = [primary_wall(r) for r in subset if r['instrumentation'] == 'off']
        entry = {'path': path, 'mode': mode, 'off_wall_ms': off, 'off_range_ms': [min(off), max(off)],
                 'off_trace': 'unavailable_compiled_out', 'speedup_claim': False, 'overhead': {}}
        for level in ('counts', 'sampled'):
            elapsed = primary_wall(next(r for r in subset if r['instrumentation'] == level))
            entry['overhead'][level] = {'wall_ms': elapsed, 'delta_vs_off_ms': [elapsed - value for value in off],
                                        'ratio_vs_off': [elapsed / value for value in off]}
        comparisons.append(entry)
    return {'schema': 1, 'verified': True, 'product_acceptance': {'separate': True, 'status': 'not_claimed'},
            'comparisons': comparisons, 'nested_callback_times_additive': False,
            'sampled_stage_times_extrapolated': False, 'off_repetitions': 2,
            'shared_verification_scaffolding': 'Untimed full-byte check module exists at every level and may add persistent roots; off has no hot recording.',
            'native_scan_suffix_counters': 'unavailable_without_native_scanner_instrumentation',
            'measurement_notes': [
                'Sampled phase nanoseconds are exclusive nested observations and include count and trace-hash overhead; caller argument construction is outside the phase.',
                'Allocation requests include profiling checkpoint enlargement in native traps; requested bytes are not successful allocation bytes.',
                'Callback heap entries are derived as two times live heap entries for successful root snapshots and exclude OOM and restoration walks.',
                'GC heap scans count root and sweep entry visits. No sampled time is extrapolated or subtracted from original application wall time.']}


def safe_text(value):
    """Defense in depth for already schema-selected public strings."""
    require(type(value) is str and len(value) <= 512 and not any(c in value for c in ('\x00', '\r', '\n')), 'unsafe_public_string')
    require(not re.search(r'(?:[A-Za-z]:[\\/]|\\\\|/(?:workspace|home|Users|tmp|var)/)', value), 'private_path_in_public_data')
    return value


def check_public_tree(value):
    if type(value) is dict:
        for key, item in value.items():
            safe_text(key)
            check_public_tree(item)
    elif type(value) is list:
        for item in value:
            check_public_tree(item)
    elif type(value) is str:
        safe_text(value)
    else:
        require(value is None or type(value) is bool or (type(value) in (int, float) and math.isfinite(value)),
                'invalid_public_value')


def sanitize_runtime_log(path):
    """Preserve numeric raw records; unknown lines are represented only by hash."""
    path = unlinked(path)
    require(path.is_file() and path.stat().st_size <= MAX_PRIVATE_LOG_BYTES, 'runtime_log_limit_exceeded')
    output = []
    redacted = 0
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        if re.fullmatch(r'(?:RU_GUI_SYNC|RU_GUI_TIMER|RU_GUI_SNAPSHOT) (?:[a-z_]+=[0-9.eE+-]+ ?)+', line):
            output.append(line)
        elif re.fullmatch(r'(?:TOTAL PASS: [0-9]+|RU_SYNTAX_PROFILE_TESTS_PASS=[0-9]+|RU_SYNTAX_PROFILE_PREFLIGHT_TESTS_PASS=1)', line):
            output.append(line)
        elif line.startswith((PROFILE_PREFIX, OUTPUT_CHECK_PREFIX, PREFLIGHT_PREFIX)):
            # Profile is delivered separately only after closed-schema validation.
            output.append('PROFILE_RECORD_SHA256 ' + digest_bytes(line.encode('utf-8')))
        elif line:
            redacted += 1
            output.append('OMITTED_LINE_SHA256 ' + digest_bytes(line.encode('utf-8')))
    return ('\n'.join(output) + '\n').encode('utf-8'), redacted


def validate_prepare_receipt(record):
    required = {'schema', 'prepared', 'error_code', 'corpus', 'matrix', 'builds', 'commands',
                'build_budget_seconds', 'compile_timeout_seconds', 'initial_build_estimate_seconds',
                'elapsed_seconds', 'estimate_exceeded', 'preflight_builds'}
    optional = {'identity', 'environment', 'toolchain', 'dependencies', 'generation_seconds'}
    require(type(record) is dict and required <= set(record) <= required | optional, 'prepare_receipt_shape_mismatch')
    require(record['schema'] == 1 and type(record['prepared']) is bool and type(record['estimate_exceeded']) is bool
            and record['corpus'] == CORPUS and record['matrix'] == matrix()
            and record['build_budget_seconds'] == BUILD_BUDGET_SECONDS
            and record['compile_timeout_seconds'] == COMPILE_TIMEOUT_SECONDS
            and record['initial_build_estimate_seconds'] == [120, 240]
            and number(record['elapsed_seconds']), 'prepare_receipt_identity_mismatch')
    require(record['error_code'] is None or re.fullmatch('[a-z_]{1,80}', record['error_code']), 'invalid_error_code')
    if 'identity' in record:
        identity = record['identity']
        exact(identity, ('baseline_commit', 'baseline_tree', 'profile_commit', 'profile_tree', 'compiler_commit',
                         'compiler_tree', 'source_sha256', 'reviewed_document_sha256', 'streaming_fixture_sha256'), 'identity_shape_mismatch')
        require(identity['baseline_commit'] == BASELINE_COMMIT and identity['baseline_tree'] == BASELINE_TREE
                and identity['compiler_commit'] == RU_COMMIT and identity['compiler_tree'] == RU_TREE,
                'identity_pin_mismatch')
        for key in ('profile_commit', 'profile_tree'):
            require(type(identity[key]) is str and re.fullmatch('[0-9a-f]{40}', identity[key]), 'invalid_git_identity')
        require(type(identity['source_sha256']) is dict and len(identity['source_sha256']) == 114,
                'source_hash_set_invalid')
        for name, checksum in identity['source_sha256'].items():
            require(type(name) is str and len(name) <= 240 and name.isprintable()
                    and not any(char in name for char in ('\\', ':', '\x00'))
                    and not name.startswith('/') and '..' not in PurePosixPath(name).parts,
                    'source_hash_path_invalid')
            require(type(checksum) is str and re.fullmatch('[0-9a-f]{64}', checksum), 'source_hash_invalid')
        require(identity['reviewed_document_sha256'] == identity['source_sha256']['benchmarks/README.md'],
                'document_hash_mismatch')
        require(identity['streaming_fixture_sha256'] == identity['source_sha256']['tests/app_streaming_native.ru'],
                'streaming_fixture_hash_mismatch')
    if 'environment' in record:
        exact(record['environment'], ('platform', 'os_version', 'architecture', 'logical_cpus', 'python_version',
                                      'cpu', 'cold_warm'), 'environment_shape_mismatch')
        require(record['environment']['platform'] == 'native-windows-x64'
                and uint(record['environment']['logical_cpus']), 'environment_identity_invalid')
    if 'toolchain' in record:
        toolchain = record['toolchain']
        require(set(toolchain) <= {'gcc_sha256', 'windres_sha256', 'flags', 'gcc_version_log_sha256', 'gcc_version'}
                and {'gcc_sha256', 'windres_sha256', 'flags'} <= set(toolchain), 'toolchain_shape_mismatch')
        require(toolchain['flags'] == ['-std=c99', '-O2', '-Wall', '-Wextra', '-Wno-unused-function', '-static-libgcc'],
                'compiler_flags_changed')
        if 'gcc_version' in toolchain:
            safe_text(toolchain['gcc_version'])
        for key in set(toolchain) - {'flags', 'gcc_version'}:
            require(type(toolchain[key]) is str and re.fullmatch('[0-9a-f]{64}', toolchain[key]), 'toolchain_hash_invalid')
    if 'dependencies' in record:
        dependencies = record['dependencies']
        require(set(dependencies) <= {'Scintilla.dll', 'Lexilla.dll', 'RuSyntax.dll'}, 'dependency_set_invalid')
        for name, dependency in dependencies.items():
            exact(dependency, ('sha256',) if name == 'RuSyntax.dll' else ('sha256', 'version', 'archive_sha256'),
                  'dependency_shape_mismatch')
            require(type(dependency['sha256']) is str and re.fullmatch('[0-9a-f]{64}', dependency['sha256']), 'dependency_hash_invalid')
            if name != 'RuSyntax.dll':
                require(dependency['version'] == portable.DEPENDENCIES[name]['version']
                        and dependency['archive_sha256'] == portable.DEPENDENCIES[name]['sha256'], 'dependency_pin_mismatch')
    require(type(record['commands']) is list and len(record['commands']) <= 23, 'build_command_set_invalid')
    labels = {'gcc-version', 'resource', 'native-helper', 'generate', 'preflight-bridge', 'preflight-off', 'preflight-counts', 'preflight-sampled'} | {
        '-'.join((path, mode, level)) for path, mode in UNITS for level in LEVELS}
    for command in record['commands']:
        exact(command, ('stage', 'elapsed_seconds', 'exit_code', 'error_code', 'cleanup_killed', 'cleanup_failed'), 'build_command_shape_mismatch')
        require(command['stage'] in labels and number(command['elapsed_seconds'])
                and type(command['cleanup_killed']) is bool and type(command['cleanup_failed']) is bool
                and (command['exit_code'] is None or type(command['exit_code']) is int)
                and (command['error_code'] is None or re.fullmatch('[a-z_]{1,80}', command['error_code'])), 'build_command_invalid')
    require(type(record['builds']) is list and len(record['builds']) <= 15, 'variant_build_set_invalid')
    seen = set()
    for build in record['builds']:
        exact(build, ('id', 'path', 'mode', 'instrumentation', 'exe_name', 'exe_sha256', 'generated_c_sha256', 'instrumentation_receipt_sha256', 'seconds', 'files'),
              'variant_build_shape_mismatch')
        require((build['path'], build['mode']) in UNITS and build['instrumentation'] in LEVELS
                and build['id'] == '-'.join(build[key] for key in ('path', 'mode', 'instrumentation'))
                and build['id'] not in seen and number(build['seconds']), 'variant_build_identity_invalid')
        seen.add(build['id'])
        expected_exe = {'console_pipeline': 'ru_syntax_profile.exe', 'cooperative_console': 'app_ru_native.exe', 'gui': 'ru_notepad.exe'}[build['path']]
        require(build['exe_name'] == expected_exe and set(build['files']) == {expected_exe, 'Scintilla.dll', 'Lexilla.dll', 'RuSyntax.dll'},
                'variant_binary_set_invalid')
        for checksum in (build['exe_sha256'], build['generated_c_sha256'], build['instrumentation_receipt_sha256'], *build['files'].values()):
            require(type(checksum) is str and re.fullmatch('[0-9a-f]{64}', checksum), 'variant_hash_invalid')
    require(type(record['preflight_builds']) is list and len(record['preflight_builds']) <= 3, 'preflight_builds_invalid')
    for level, build in zip(LEVELS, record['preflight_builds']):
        exact(build, ('id', 'instrumentation', 'exe_sha256', 'bridge_sha256', 'generated_c_sha256', 'instrumentation_receipt_sha256',
                      'seconds', 'bridge_origin_sha256'), 'preflight_build_shape_mismatch')
        require(build['id'] == 'preflight-' + level and build['instrumentation'] == level and number(build['seconds']),
                'preflight_build_identity_mismatch')
        require(all(type(build[key]) is str and re.fullmatch('[0-9a-f]{64}', build[key])
                    for key in ('exe_sha256', 'bridge_sha256', 'generated_c_sha256', 'instrumentation_receipt_sha256', 'bridge_origin_sha256')),
                'preflight_build_hash_invalid')
    if record['prepared']:
        require(len(record['preflight_builds']) == 3, 'preflight_build_incomplete')
        require(len(record['builds']) == 15 and record['error_code'] is None and optional - {'generation_seconds'} <= set(record),
                'prepared_receipt_incomplete')
    check_public_tree(record)
    return record


def validate_results_receipt(summary):
    exact(summary, ('schema', 'complete', 'passed', 'runs', 'matrix', 'corpus', 'counter_interval_excluded', 'product_acceptance', 'preflight', 'preflight_passed'),
          'results_receipt_shape_mismatch')
    require(summary['schema'] == 1 and type(summary['complete']) is bool and type(summary['passed']) is bool
            and summary['matrix'] == matrix() and summary['corpus'] == CORPUS
            and summary['counter_interval_excluded'] == ['file_open_before_first_batch', 'initial_outer_callback_snapshot', 'refresh_after_last_batch']
            and summary['product_acceptance'] == {'separate': True, 'status': 'not_claimed'}, 'results_receipt_identity_invalid')
    require(type(summary['preflight_passed']) is bool and type(summary['preflight']) is list
            and len(summary['preflight']) <= 3, 'preflight_results_invalid')
    for level, result in zip(LEVELS, summary['preflight']):
        exact(result, ('instrumentation', 'passed', 'error_code', 'outcome', 'boundary_check'), 'preflight_result_shape_mismatch')
        require(result['instrumentation'] == level and type(result['passed']) is bool
                and (result['error_code'] is None or re.fullmatch('[a-z_]{1,80}', result['error_code'])), 'preflight_result_identity_invalid')
        if result['boundary_check'] is not None:
            validate_preflight_check(result['boundary_check'], level, require_success=False)
        if result['outcome'] is not None:
            outcome = result['outcome']
            require(set(outcome) <= {'passed', 'executed', 'cleanup_killed', 'exit_code', 'error_code', 'assertions_passed', 'elapsed_seconds'},
                    'preflight_outcome_shape_mismatch')
            require(all(type(outcome.get(key)) is bool for key in ('passed', 'executed', 'cleanup_killed'))
                    and (outcome.get('exit_code') is None or type(outcome['exit_code']) is int)
                    and outcome.get('error_code') in (None, 'native_run_failed')
                    and all(number(outcome[key]) for key in ('assertions_passed', 'elapsed_seconds') if key in outcome),
                    'preflight_outcome_invalid')
    require(type(summary['runs']) is list and len(summary['runs']) <= 20, 'result_rows_invalid')
    for expected, row in zip(matrix(), summary['runs']):
        base = set(expected) | {'passed', 'error_code', 'profile', 'outcome', 'output_check'}
        require(type(row) is dict and base <= set(row) <= base | {'binary_sha256', 'generated_c_sha256'}, 'result_row_shape_mismatch')
        require(all(row[key] == value for key, value in expected.items()) and type(row['passed']) is bool,
                'result_row_identity_mismatch')
        require(row['error_code'] is None or re.fullmatch('[a-z_]{1,80}', row['error_code']), 'invalid_error_code')
        for key in ('binary_sha256', 'generated_c_sha256'):
            if key in row:
                require(type(row[key]) is str and re.fullmatch('[0-9a-f]{64}', row[key]), 'result_hash_invalid')
        if row['profile'] is not None:
            validate_profile(row['profile'], row, require_complete=False)
        if row['output_check'] is not None:
            validate_output_check(row['output_check'], require_success=False)
        if row['outcome'] is not None:
            outcome = row['outcome']
            base_outcome = {'passed', 'executed', 'cleanup_killed', 'exit_code', 'error_code'}
            optional = {'main_hwnd_seen', 'close_posted', 'detached_from_console', 'assertions_passed', 'elapsed_seconds',
                        'timer_performance', 'sync_performance', 'partial_timer_performance', 'full_gui_checks'}
            require(base_outcome <= set(outcome) <= base_outcome | optional, 'outcome_shape_mismatch')
            require(all(type(outcome[key]) is bool for key in ('passed', 'executed', 'cleanup_killed'))
                    and (outcome['exit_code'] is None or type(outcome['exit_code']) is int)
                    and outcome['error_code'] in (None, 'native_run_failed'), 'outcome_values_invalid')
            for key in ('assertions_passed', 'elapsed_seconds'):
                if key in outcome:
                    require(number(outcome[key]), 'outcome_number_invalid')
            for key in ('main_hwnd_seen', 'close_posted', 'detached_from_console'):
                if key in outcome:
                    require(type(outcome[key]) is bool, 'outcome_boolean_invalid')
            if 'sync_performance' in outcome:
                acceptance.validate_ru_gui_measurement(outcome['sync_performance'], 'RU_GUI_SYNC', require_complete=False)
            if 'timer_performance' in outcome:
                if row['path'] == 'gui':
                    acceptance.validate_gui_ru_timer(outcome['timer_performance'], require_windows_clock=True)
                else:
                    acceptance.validate_ru_gui_measurement(outcome['timer_performance'], 'RU_GUI_TIMER', require_complete=False)
            if 'partial_timer_performance' in outcome:
                partial = outcome['partial_timer_performance']
                require(set(partial) <= {'size', 'wall_ms', 'first_head_style_ms', 'max_response_ms', 'probes'}
                        and all(number(value) for value in partial.values()), 'partial_timer_invalid')
            if 'full_gui_checks' in outcome:
                require(set(outcome['full_gui_checks']) == set(acceptance.GUI_RU_CHECKS)
                        and all(type(value) is bool for value in outcome['full_gui_checks'].values()), 'full_gui_checks_invalid')
    check_public_tree(summary)
    return summary


def collect():
    root = unlinked(ROOT / 'build/profile', must_exist=False)
    build = unlinked(ROOT / 'build', must_exist=False)
    if not build.exists():
        build.mkdir()
    require(unlinked(build).is_dir(), 'invalid_build_directory')
    destination = unlinked(build / 'ru-syntax-profile-evidence', must_exist=False)
    require(not destination.exists(), 'fresh_public_evidence_directory_required')
    destination.mkdir()
    unlinked(destination)
    files = []
    total = 0
    prepared = False
    verified = False
    native_execution_recorded = False
    prepare_present = (root / 'prepare.json').exists()
    results_present = (root / 'results.json').exists()
    def publish(name, value):
        nonlocal total
        check_public_tree(value)
        save_json(destination / name, value)
        path = destination / name
        total += path.stat().st_size
        require(total <= MAX_PUBLIC_BYTES, 'public_evidence_budget_exceeded')
        files.append({'name': name, 'bytes': path.stat().st_size, 'sha256': sha(path)})
    dependency_setup = ROOT / 'build/dependency-profile-setup.json'
    if dependency_setup.exists():
        setup = read_json(dependency_setup)
        exact(setup, ('schema', 'passed', 'commands', 'elapsed_seconds'), 'dependency_setup_shape_mismatch')
        require(setup['schema'] == 1 and type(setup['passed']) is bool and number(setup['elapsed_seconds']), 'dependency_setup_invalid')
        require(type(setup['commands']) is list and len(setup['commands']) <= 4, 'dependency_setup_invalid')
        for command in setup['commands']:
            exact(command, ('stage', 'elapsed_seconds', 'exit_code', 'error_code', 'cleanup_killed', 'cleanup_failed'),
                  'dependency_command_shape_mismatch')
            require(command['stage'] in ('dependency-scintilla', 'dependency-lexilla',
                                          'dependency-download-scintilla567', 'dependency-download-lexilla554')
                    and number(command['elapsed_seconds'])
                    and type(command['cleanup_killed']) is bool and type(command['cleanup_failed']) is bool
                    and (command['exit_code'] is None or type(command['exit_code']) is int)
                    and (command['error_code'] is None or re.fullmatch('[a-z_]{1,80}', command['error_code'])),
                    'dependency_command_invalid')
        publish('dependency-setup.json', setup)
    if (root / 'prepare.json').exists():
        receipt = read_json(root / 'prepare.json')
        # No raw generator manifest, command argv, stderr or generated sources.
        allow = {'schema', 'prepared', 'error_code', 'corpus', 'matrix', 'builds', 'commands', 'identity',
                 'environment', 'toolchain', 'dependencies', 'build_budget_seconds', 'compile_timeout_seconds',
                 'initial_build_estimate_seconds', 'elapsed_seconds', 'estimate_exceeded', 'generation_seconds', 'preflight_builds'}
        require(set(receipt) <= allow, 'unexpected_prepare_field')
        validate_prepare_receipt(receipt)
        prepared = receipt['prepared']
        publish('prepare.json', receipt)
    if (root / 'results.json').exists():
        summary = validate_results_receipt(read_json(root / 'results.json'))
        native_execution_recorded = any((row['outcome'] or {}).get('executed') is True
                                        for row in summary['preflight'] + summary['runs'])
        for row in summary.get('runs', []):
            if row.get('profile') is not None:
                validate_profile(row['profile'], row, require_complete=False)
            if row.get('output_check') is not None:
                validate_output_check(row['output_check'], require_success=False)
        publish('results.json', summary)
    if (root / 'verification.json').exists():
        verification = read_json(root / 'verification.json')
        require(verification == verify_results(read_json(root / 'results.json')), 'verification_receipt_mismatch')
        publish('verification.json', verification)
        verified = prepared and results_present
    for row in matrix():
        logs = root / 'runs' / row['id'] / 'logs'
        if not logs.exists():
            continue
        for path in sorted(unlinked(logs).glob('*.log')):
            # Fixed basename set, never arbitrary directory or Temp traversal.
            require(re.fullmatch(r'(?:profile_pipeline|app_ru_timer_native)\.(?:stdout|stderr)\.log|main-ru-syntax-launcher-[0-9]\.log', path.name),
                    'unexpected_runtime_log')
            content, redactions = sanitize_runtime_log(path)
            name = row['id'] + '-' + path.name
            total += len(content)
            require(total <= MAX_PUBLIC_BYTES, 'public_evidence_budget_exceeded')
            (destination / name).write_bytes(content)
            files.append({'name': name, 'bytes': len(content), 'sha256': digest_bytes(content),
                          'original_sha256': sha(path), 'omitted_lines': redactions})
    for level in LEVELS:
        logs = root / 'preflight-logs' / level
        if not logs.exists():
            continue
        for name in ('profile_boundary.stdout.log', 'profile_boundary.stderr.log'):
            path = logs / name
            if not path.exists():
                continue
            content, redactions = sanitize_runtime_log(path)
            published_name = 'preflight-' + level + '-' + name
            total += len(content)
            require(total <= MAX_PUBLIC_BYTES, 'public_evidence_budget_exceeded')
            (destination / published_name).write_bytes(content)
            files.append({'name': published_name, 'bytes': len(content), 'sha256': digest_bytes(content),
                          'original_sha256': sha(path), 'omitted_lines': redactions})
    publish('collection.json', {'schema': 1, 'synthetic_data_only': True, 'files': files.copy(),
                               'binaries_uploaded': False, 'generated_sources_uploaded': False,
                               'prepare_receipt_present': prepare_present, 'results_receipt_present': results_present,
                               'native_execution_recorded': native_execution_recorded, 'profile_verified': verified, 'passed': verified,
                               'error_code': None if verified else ('profile_evidence_incomplete' if prepare_present or results_present
                                                                    else 'profile_evidence_missing'),
                               'product_acceptance': {'separate': True, 'status': 'not_claimed'}})
    return {'files': len(files), 'bytes': total, 'passed': verified}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--action', required=True, choices=('prepare', 'run', 'verify', 'collect'))
    parser.add_argument('--ru-root', type=Path)
    parser.add_argument('--mingw-root', type=Path)
    args = parser.parse_args()
    if args.action == 'prepare':
        if not args.ru_root or not args.mingw_root:
            parser.error('prepare requires --ru-root and --mingw-root')
    elif args.ru_root or args.mingw_root:
        parser.error('build inputs are only valid for prepare')
    try:
        if args.action == 'prepare':
            result = prepare(args.ru_root.resolve(), args.mingw_root.resolve())
            ok = result['prepared']
        elif args.action == 'run':
            ok = run_matrix()['passed']
        elif args.action == 'verify':
            result = verify_results(read_json(ROOT / 'build/profile/results.json'))
            save_json(ROOT / 'build/profile/verification.json', result)
            ok = result['verified']
        else:
            ok = collect()['passed']
        print('RU_SYNTAX_PROFILE_' + args.action.upper() + '=' + ('PASS' if ok else 'FAIL'))
        return 0 if ok else 1
    except Exception as exc:
        code = str(exc) if isinstance(exc, ProfileError) else 'operation_failed'
        print('RU_SYNTAX_PROFILE_ERROR=' + code)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
