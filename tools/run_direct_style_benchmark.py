#!/usr/bin/env python3
"""Candidate-specific paired direct-style experiment, never product acceptance.

Four binaries and eight fresh real-Windows runs. No profiling counters or hot
runtime changes. The only route difference is one private copied-source bool.
Private generated C, binaries and unsanitized logs never enter public evidence.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import run_ru_syntax_profile as shared
import profile_ru_syntax as generator

acceptance = shared.acceptance
portable = shared.portable
Error = shared.ProfileError
require = shared.require
sha = shared.sha
save_json = shared.save_json
read_json = shared.read_json
relative_file = shared.relative_file
unlinked = shared.unlinked
number = shared.number
uint = shared.uint
exact = shared.exact

BASELINE_PUBLIC_COMMIT = 'e3256f0453b3b11dd26b671f38628cf411ab24e8'
BASELINE_TREE = 'a9636c81716f0788baa4a8ba505319d51b3775bc'
RU_COMMIT = 'a2f6faa0f914781dea74cb6f0a7574f1dd6808ce'
RU_TREE = '7b4331d51bc6ab2ec95fec1f8368465343fcd5af'
CORPUS = shared.CORPUS
ROUTE_ON = "_直接策略 取 {'enabled':真}. # Source-only paired benchmark control; no application setting."
ROUTE_OFF = ROUTE_ON.replace("'enabled':真", "'enabled':假")
PATHS = ('gui', 'cooperative_console')
ROUTES = ('direct', 'message')
OWNED = ('tools/run_direct_style_benchmark.py', 'tools/test_direct_style_benchmark.py',
         '.github/workflows/direct-style-benchmark.yml', '.github/workflows/ru-syntax-profile.yml',
         'benchmarks/README.md')
NEW_INPUTS = ('tests/ru_direct_styling_native.ru', 'tests/ru_direct_fixture_portable.py',
              'docs/direct-style-publication.md')
# Filled only after independent review of the final candidate delta. A missing
# reviewed digest fails closed; this is not the historical profiler's PINNED map.
REVIEWED_CHANGED_SHA256 = {
    "CHANGELOG.md": "689120e0a3b6f63c0e471cb82240a45930cd326c16f030bb7d081c1d21000425",
    "README.md": "eb57f865382716ec3150838b596af9d088a25d7d05873f11431f25b6b7a83df9",
    "VERSION": "ce31113c662a0d350a5aac4a8e554d4cbdf3556402b9eb1997fef4bb250ae156",
    "docs/build-provenance.md": "da8f9f3c859e106a3697e409d8f56e0c99ab0e74c85356cc17c100d00131fa31",
    "docs/direct-style-publication.md": "057e48634b29ed4303fd5132c2c00370fee9648090bf5ffbc3c8134ca12abef9",
    "docs/preview-validation.md": "d03b9ff6aea97f57a55b722c08b7d2636cedd94fc65464fc9d329a1a121ecd12",
    "docs/ru-language-syntax.md": "58c29b1467cc371c534f8470961b49904a1ed578f93751c9dbd510d00236c9cf",
    "docs/status-and-shortcuts.md": "00418609aaf35cbfd3fe12fd8d5a1428cab3700d1dbdb0e2ee8b0da19ecde61d",
    "docs/syntax-highlighting.md": "aef85b9971ec9437303823c20236bfdc06cdc61f640eca9edc1a7e4d8c6d37d9",
    "packaging/README-preview.txt": "d884b6d6e5ddb1817d29ac93d86ce9c329fa788f6ceff1631a3b3ef0697ce556",
    "packaging/app.rc": "f7e7910a803b732916380fbc420467790ff6942d226b24aa6a2c220f992b104d",
    "packaging/run-tests.cmd": "af5cb9b71e0b9c618f0f5e261278a803c3d465c371ee776752168993bbb4ad73",
    "packaging/开始前请读.txt": "981bbb5652e08aacd00e9b623992ae7fe04ec05ffc4eb3d961a0d5e9fb7891d8",
    "src/main.ru": "9583177061ffaf3b12dfadd7a79ca5fcce8a3e253aad701cfee62f7f2b2db335",
    "src/ru_syntax.ru": "8f23bb79ad9d8f36823272ff9bf1d55300aa3dce9e89ce82ff5a319111d812bf",
    "src/syntax.ru": "c1f9c6559c5fb7ad404aef38bffab025b946fbe3bc893312c5b2e1ef4e214e14",
    "tests/ru_direct_fixture_portable.py": "883b98219690d5fa759844201c9c26a38dfcb4af1b3e01e2c1091f76f68fd542",
    "tests/ru_direct_styling_native.ru": "530df39232952313bca7c5b3c4ed94af894ab6936ebd4fa9577c2eb6fd2e499c",
    "tests/syntax_native.ru": "9b26324f0fa2824881fc2d0e66ee47385c893388ff37d4bf23e668a68b1c9f36",
    "tools/package.py": "584b7ee1fc4f584aced77c824f156f24e1218b89b1cc392ff77d899f5841ed58",
    "tools/run_ru_syntax_profile.py": "8797a158214653ddb7c6dddb3d6fe8df6cc13eddff53a83d2485660d905850e3",
    "tools/test_package.py": "e575654e7c26ebd36ce90559cccf2727d92dd2ac5caa1a65f85aa7ee1dc8d0f4",
    "tools/test_ru_syntax_profile.py": "799aadee00f5fcf4f38ebe77797c7e82588c3775b7925ddc216889800d89ff14",
    "tools/test_windows_ci.py": "b25abdc83b57fa42737106fd2902fcb626332d30e4d8259ef5861efd8c7015c3",
    "tools/windows_ci.ps1": "c19497026fc33889762dfa04be4430bb9d6407ee76a0aa819cd7256a85d421b7",
    "tools/windows_ci.py": "adcd769863de108e43f51dc8cb7286d1f3438c4aa27f5fb9be8d63a1e0db7400"
}
BUILD_BUDGET_SECONDS = 900
COMPILE_TIMEOUT_SECONDS = 180
STYLE_TIMEOUT_SECONDS = 30
MAX_LOG_BYTES = 1024 * 1024
MAX_PUBLIC_BYTES = 32 * 1024 * 1024
FLAGS = ('-std=c99', '-O2', '-Wall', '-Wextra', '-Wno-unused-function', '-static-libgcc')
PREFLIGHTS = ('scanner', 'boundary', 'direct_native')
DIRECT_ASSERTIONS = 36
PRODUCT_STATUS = {'separate': True, 'status': 'not_claimed'}
GRAPH_NOTES = ('Both routes retain identical current initialization, GC roots, lexical/fold policy, '
               'resources and untimed full-byte verification. Only the copied private bool differs.')


def matrix():
    """Predeclared alternating AB/BA pairs, with paths interleaved."""
    plan = [('gui', 'direct', 1), ('cooperative_console', 'message', 1),
            ('gui', 'message', 1), ('cooperative_console', 'direct', 1),
            ('cooperative_console', 'direct', 2), ('gui', 'message', 2),
            ('cooperative_console', 'message', 2), ('gui', 'direct', 2)]
    return [dict(id=f'{order:02d}-{path}-{route}-{repeat}', order=order,
                 path=path, route=route, repeat=repeat)
            for order, (path, route, repeat) in enumerate(plan, 1)]


def variant_id(path, route):
    require(path in PATHS and route in ROUTES, 'unknown_variant')
    return path + '-' + route


def variants():
    return [variant_id(path, route) for path in PATHS for route in ROUTES]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def hex_digest(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def code(exc, fallback):
    # Never publish arbitrary exception text, paths, source, or native messages.
    value = str(exc)
    return value if isinstance(exc, Error) and re.fullmatch('[a-z_]{1,80}', value) else fallback


def git(*args, root=ROOT):
    return shared.git(root, *args)


def tracked(root, tree=None):
    args = ['git', '-C', str(root)]
    if tree:
        args += ['ls-tree', '-r', '--name-only', '-z', tree]
    else:
        args += ['ls-files', '-z']
    return subprocess.check_output(args, timeout=30).decode('utf-8').rstrip('\0').split('\0')


def compiler_identity(ru_root):
    require(git('rev-parse', 'HEAD', root=ru_root) == RU_COMMIT
            and git('rev-parse', 'HEAD^{tree}', root=ru_root) == RU_TREE
            and git('status', '--porcelain', root=ru_root) == '', 'compiler_identity_mismatch')
    return {'commit': RU_COMMIT, 'tree': RU_TREE}


def candidate_sources(root):
    require(git('status', '--porcelain', '--untracked-files=all', root=root) == '', 'dirty_candidate_checkout')
    original = tracked(root, BASELINE_TREE)
    require(len(original) == 114 and len(set(original)) == 114, 'accepted_source_inventory_mismatch')
    names = tracked(root)
    require(set(names) == set(original) | set(OWNED) | set(NEW_INPUTS), 'candidate_source_inventory_mismatch')
    hashes = {name: sha(relative_file(root, name)) for name in names}
    accepted = {}
    for name in original:
        accepted[name] = digest(subprocess.check_output(
            ['git', '-C', str(root), 'show', BASELINE_TREE + ':' + name], timeout=30))
    actual_delta = {name for name in names if name not in OWNED and hashes[name] != accepted.get(name)}
    require(actual_delta == set(REVIEWED_CHANGED_SHA256), 'unreviewed_candidate_delta')
    require(all(hashes[name] == expected for name, expected in REVIEWED_CHANGED_SHA256.items()),
            'reviewed_candidate_hash_mismatch')
    require(set(p.relative_to(root).as_posix() for p in (root / 'src').glob('*.ru')) ==
            {name for name in names if name.startswith('src/') and name.endswith('.ru')},
            'untracked_source_module')
    return {'accepted_commit': BASELINE_PUBLIC_COMMIT, 'accepted_tree': BASELINE_TREE,
            'candidate_commit': git('rev-parse', 'HEAD', root=root),
            'candidate_tree': git('rev-parse', 'HEAD^{tree}', root=root),
            'accepted_source_sha256': accepted, 'source_sha256': hashes,
            'reviewed_changes': sorted(REVIEWED_CHANGED_SHA256), 'harness_inputs': list(OWNED)}


def source_identity(root, ru_root):
    return {'candidate': candidate_sources(root), 'compiler': compiler_identity(ru_root)}


def substitute_route(text, route):
    require(route in ROUTES, 'unknown_route')
    require(text.count(ROUTE_ON) == 1 and ROUTE_OFF not in text, 'route_source_anchor_mismatch')
    # This exact source line is the entire permitted direct/message difference.
    return text if route == 'direct' else text.replace(ROUTE_ON, ROUTE_OFF, 1)


def verification_sources(path):
    require(path in PATHS, 'unknown_path')
    files = {p.relative_to(ROOT).as_posix(): p.read_text(encoding='utf-8-sig')
             for p in sorted((ROOT / 'src').glob('*.ru'))}
    files['src/profile_check.ru'] = check_module()
    files['src/main.ru'] = "档案 取 外言 './profile_check.ru'.\n" + generator.once(
        files['src/main.ru'], "    若 已选 == 'ru' 则 语 其 登记直属 柄 (A 其 查 'window'). 然",
        "    若 已选 == 'ru' 则 语 其 登记直属 柄 (A 其 查 'window'). 档案 其 路由 柄 0. 然")
    if path == 'gui':
        entry = 'src/main.ru'
        content = files[entry]
        anchors = [line for line in content.splitlines()
                   if "显 'RU_GUI_SNAPSHOT seq='" in line and 'ok=1' in line]
        require(len(anchors) == 1, 'gui_verification_anchor_mismatch')
        content = generator.once(content, anchors[0], anchors[0] +
            "\n        若 序 == 3 且 非 扫['pending'] 且 扫['bytes'] == 1000000 则 档案 其 检查 (文们[活动] 其 查 'editor'). 然")
        files[entry] = content
    else:
        entry = 'tests/app_ru_native.ru'
        content = (ROOT / entry).read_text(encoding='utf-8-sig')
        anchors = [line for line in content.splitlines() if "显 'RU_GUI_TIMER " in line]
        require(len(anchors) == 1, 'cooperative_verification_anchor_mismatch')
        files[entry] = "档案 取 外言 '../src/profile_check.ru'.\n" + generator.once(
            content, anchors[0], anchors[0] + '\n        档案 其 检查 柄.')
    return entry, files


def assert_route_graphs(left, right):
    require(type(left) is dict and type(right) is dict and set(left) == set(right), 'route_graph_inventory_mismatch')
    differences = [name for name in left if left[name] != right[name]]
    require(differences == ['src/ru_syntax.ru'], 'route_graph_has_extra_difference')
    require(substitute_route(left['src/ru_syntax.ru'], 'message') == right['src/ru_syntax.ru'],
            'route_graph_substitution_mismatch')


def checker_only(code_text):
    """One checked stub replacement; the complete native runtime stays byte-identical."""
    functions = generator.generated_functions(code_text)
    matches = [item for item in functions if item[2].endswith('/profile_check.ru')
               and item[1] == generator.octal('_档案核对')]
    require(len(matches) == 1, 'complete_checker_stub_missing')
    _, _, _, start, end, body = matches[0]
    # The Ru stub is parsed by the pinned compiler. Fail if its generated body
    # no longer corresponds to the exact three-argument false-return function.
    require(body.count('= v_fact(0);') == 1 and body.count('env_set(env, ') == 3 and 'args[3]' not in body,
            'complete_checker_stub_changed')
    replacement = body[:body.index('{') + 1] + (
        '\n    (void)global;(void)self;(void)call_line;return rp_expected_check(args[0],args[1],args[2]);\n}\n')
    changed = code_text[:start] + replacement + code_text[end:]
    first = re.search(r'^static Val ru_function_\d+\(Env \*global', changed, re.M)
    require(first is not None, 'generated_function_boundary_missing')
    # CHECK_C is the reviewed complete 1MB byte/style oracle at RP_LEVEL=0.
    # No profile header, atexit hook, phase/callback hooks or hot counters enter
    # a measured executable. Error preservation remains outside native guards.
    error_helpers = (ROOT / 'native/profile_counters.h').read_text(encoding='utf-8').split(
        '#if defined(_WIN32)\n', 1)[1].split('#else\n', 1)[0]
    require(error_helpers.count('typedef struct { DWORD win32; int crt; } RpError;') == 1, 'error_preservation_anchor_changed')
    prefix = ('#include <errno.h>\n#include <inttypes.h>\n#define RP_LEVEL 0\n#define RP_MODE "full"\n' + error_helpers)
    output = prefix + changed[:first.start()] + generator.CHECK_C + '\n' + changed[first.start():]
    # Removing only our known additions exactly recovers the compiler output.
    recovered = output[len(prefix):].replace(generator.CHECK_C + '\n', '', 1)
    recovered = recovered.replace(replacement, body, 1)
    require(recovered == code_text, 'native_runtime_changed')
    require(not any(token in output for token in ('atexit(rp_emit)', 'rp_call_enter(', 'rp_step_open(', 'rp_calibrate();')),
            'hot_instrumentation_forbidden')
    return output


def emit_graph(entry, folder, ru_root, *, checker=False, full_runtime=False):
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(ru_root))
    from rulang.frontend import parse
    from rulang.modules import load_module_graph
    from rulang.compiler import Compiler
    source = relative_file(folder, entry)
    content = source.read_text(encoding='utf-8')
    program = parse(content)
    graph = load_module_graph(str(source), program)
    graph.sources[graph.root] = content
    modules = {}
    for key, text in graph.sources.items():
        path = Path(key).resolve()
        if folder.resolve() in path.parents:
            name = path.relative_to(folder.resolve()).as_posix()
        else:
            require(ru_root.resolve() in path.parents, 'module_outside_closed_graph')
            relative = path.relative_to(ru_root.resolve()).as_posix()
            require(relative in tracked(ru_root), 'untracked_compiler_module')
            name = 'compiler/' + relative
        require(digest(text.encode('utf-8')) == digest(path.read_text(encoding='utf-8-sig').encode('utf-8')),
                'loaded_module_changed')
        modules[name] = digest(text.encode('utf-8'))
    output = Compiler(program, graph.root, modules=graph, allow_native=True, full_runtime=full_runtime).compile()
    raw = folder / 'original.c'
    raw.write_text(output, encoding='utf-8', newline='\n')
    emitted = folder / 'checked.c'
    emitted.write_text(checker_only(output) if checker else output, encoding='utf-8', newline='\n')
    return {'entry': entry, 'loaded_modules_sha256': modules, 'original_c_sha256': sha(raw),
            'generated_c_sha256': sha(emitted), 'checker': checker}


def generate(ru_root, output):
    compiler_identity(ru_root)
    require(not output.exists(), 'fresh_generated_directory_required')
    output.mkdir(parents=True)
    result = {'schema': 1, 'units': [], 'preflights': [], 'graph_contract': GRAPH_NOTES,
              'check_module_sha256': digest(check_module().encode('utf-8')),
              'check_c_sha256': digest(generator.CHECK_C.encode('utf-8')),
              'route_on_sha256': digest(ROUTE_ON.encode('utf-8')),
              'route_off_sha256': digest(ROUTE_OFF.encode('utf-8'))}
    for path in PATHS:
        entry, common = verification_sources(path)
        paired = {}
        for route in ROUTES:
            files = dict(common)
            files['src/ru_syntax.ru'] = substitute_route(files['src/ru_syntax.ru'], route)
            paired[route] = files
            folder = output / variant_id(path, route)
            for name, content in files.items():
                target = folder / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding='utf-8', newline='\n')
            unit = emit_graph(entry, folder, ru_root, checker=True)
            unit.update(id=variant_id(path, route), path=path, route=route,
                        source_sha256={name: sha(folder / name) for name in files})
            result['units'].append(unit)
        assert_route_graphs(paired['direct'], paired['message'])
    folder = output / 'direct_native'
    files = {p.relative_to(ROOT).as_posix(): p.read_text(encoding='utf-8-sig')
             for p in sorted((ROOT / 'src').glob('*.ru'))}
    # The real direct fixture imports the ordinary full comparison fixture.
    # Copy every current test module so local import closure cannot fall back outside this graph.
    files.update({p.relative_to(ROOT).as_posix(): p.read_text(encoding='utf-8-sig')
                  for p in sorted((ROOT / 'tests').glob('*.ru'))})
    for name, content in files.items():
        target = folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8', newline='\n')
    unit = emit_graph('tests/ru_direct_styling_native.ru', folder, ru_root)
    unit.update(id='direct_native', source_sha256={name: sha(folder / name) for name in files})
    result['preflights'].append(unit)
    folder = output / 'boundary'
    folder.mkdir()
    (folder / 'profile_boundary.ru').write_text(generator.PREFLIGHT_SOURCE, encoding='utf-8', newline='\n')
    unit = emit_graph('profile_boundary.ru', folder, ru_root, full_runtime=True)
    generator.instrument(folder / 'original.c', folder / 'checked.c', instrumentation='off', path='preflight', mode='full')
    unit['generated_c_sha256'] = sha(folder / 'checked.c')
    bridge = relative_file(ru_root, 'tests/fixtures/native/c_backend_bridge.c')
    require(sha(bridge) == '45689caba1b8552424a87dd6fd061818dbf1daab57d066461e7d91d93ea7e65f',
            'boundary_bridge_source_mismatch')
    shutil.copyfile(bridge, folder / 'profile_bridge.c')
    unit.update(id='boundary', source_sha256={'profile_boundary.ru': sha(folder / 'profile_boundary.ru'),
                                            'profile_bridge.c': sha(folder / 'profile_bridge.c')})
    result['preflights'].append(unit)
    save_json(output / 'manifest.json', result)
    return result


def validate_generated(manifest, directory):
    exact(manifest, ('schema', 'units', 'preflights', 'graph_contract', 'check_module_sha256', 'check_c_sha256',
                     'route_on_sha256', 'route_off_sha256'), 'generated_manifest_shape')
    require(manifest['schema'] == 1 and manifest['graph_contract'] == GRAPH_NOTES
            and manifest['check_module_sha256'] == digest(check_module().encode('utf-8'))
            and manifest['check_c_sha256'] == digest(generator.CHECK_C.encode('utf-8'))
            and manifest['route_on_sha256'] == digest(ROUTE_ON.encode('utf-8'))
            and manifest['route_off_sha256'] == digest(ROUTE_OFF.encode('utf-8')), 'generated_contract_mismatch')
    require([unit.get('id') for unit in manifest['units']] == variants()
            and [unit.get('id') for unit in manifest['preflights']] == ['direct_native', 'boundary'],
            'generated_inventory_mismatch')
    for unit in manifest['units'] + manifest['preflights']:
        if unit in manifest['units']:
            expected_entry, expected_sources = verification_sources(unit.get('path'))
            expected_sources['src/ru_syntax.ru'] = substitute_route(expected_sources['src/ru_syntax.ru'], unit.get('route'))
        elif unit['id'] == 'direct_native':
            expected_entry = 'tests/ru_direct_styling_native.ru'
            expected_sources = {p.relative_to(ROOT).as_posix(): p.read_text(encoding='utf-8-sig')
                                for folder in ('src', 'tests') for p in sorted((ROOT / folder).glob('*.ru'))}
        else:
            expected_entry, expected_sources = 'profile_boundary.ru', {'profile_boundary.ru': generator.PREFLIGHT_SOURCE}
        expected_hashes = {name: digest(value.encode('utf-8')) for name, value in expected_sources.items()}
        if unit['id'] == 'boundary':
            expected_hashes['profile_bridge.c'] = '45689caba1b8552424a87dd6fd061818dbf1daab57d066461e7d91d93ea7e65f'
        require(unit.get('entry') == expected_entry and unit.get('source_sha256') == expected_hashes,
                'generated_graph_not_current_candidate')
        fields = {'entry', 'loaded_modules_sha256', 'original_c_sha256', 'generated_c_sha256',
                  'checker', 'id', 'source_sha256'}
        exact(unit, fields | ({'path', 'route'} if unit in manifest['units'] else set()), 'generated_unit_shape')
        folder = unlinked(directory / unit['id'])
        require(sha(relative_file(folder, 'original.c')) == unit['original_c_sha256']
                and sha(relative_file(folder, 'checked.c')) == unit['generated_c_sha256'], 'generated_c_changed')
        for name, expected in unit['source_sha256'].items():
            require(sha(relative_file(folder, name)) == expected, 'generated_source_changed')
        require(type(unit['loaded_modules_sha256']) is dict and unit['loaded_modules_sha256']
                and all(hex_digest(value) for value in unit['loaded_modules_sha256'].values()), 'loaded_graph_invalid')
        for name in unit['loaded_modules_sha256']:
            if not name.startswith('compiler/'):
                require(name in unit['source_sha256'] and unit['source_sha256'][name] == unit['loaded_modules_sha256'][name],
                        'loaded_graph_source_mismatch')
        if unit in manifest['units']:
            require(unit['id'] == variant_id(unit['path'], unit['route']) and unit['checker'] is True,
                    'variant_route_identity_mismatch')
            original = (folder / 'original.c').read_text(encoding='utf-8')
            require(checker_only(original) == (folder / 'checked.c').read_text(encoding='utf-8'),
                    'checked_c_source_substituted')
    for path in PATHS:
        maps = [{name: (directory / variant_id(path, route) / name).read_text(encoding='utf-8')
                 for name in next(unit for unit in manifest['units'] if unit['id'] == variant_id(path, route))['source_sha256']}
                for route in ROUTES]
        assert_route_graphs(*maps)
    return manifest


def build_command(command, private, label, deadline):
    """Bound every child and its entire subprocess tree, including fast failures."""
    started = time.monotonic()
    remaining = deadline - started
    require(remaining > 0, 'build_budget_exceeded')
    limit = min(COMPILE_TIMEOUT_SECONDS, remaining)
    out = unlinked(private / (label + '.stdout.log'), must_exist=False)
    err = unlinked(private / (label + '.stderr.log'), must_exist=False)
    record = {'stage': label, 'elapsed_seconds': 0.0, 'exit_code': None, 'error_code': None,
              'cleanup_killed': False, 'cleanup_failed': False}
    process = None
    try:
        with out.open('xb') as stdout, err.open('xb') as stderr:
            process = subprocess.Popen(list(map(str, command)), cwd=ROOT, stdout=stdout, stderr=stderr)
            while process.poll() is None:
                require(out.stat().st_size <= MAX_LOG_BYTES and err.stat().st_size <= MAX_LOG_BYTES,
                        'build_log_limit_exceeded')
                require(time.monotonic() - started < limit, 'build_overrun')
                time.sleep(0.1)
            record['exit_code'] = process.returncode
        require(out.stat().st_size <= MAX_LOG_BYTES and err.stat().st_size <= MAX_LOG_BYTES,
                'build_log_limit_exceeded')
        require(time.monotonic() - started <= limit and time.monotonic() <= deadline, 'build_overrun')
        require(process.returncode == 0, 'build_command_failed')
    except Exception as exc:
        record['error_code'] = code(exc, 'build_process_failed')
        raise Error(record['error_code']) from exc
    finally:
        if process is not None:
            if process.poll() is None:
                try:
                    record['cleanup_killed'] = acceptance.cleanup_process(process)
                except Exception:
                    record.update(cleanup_failed=True, error_code='build_cleanup_failed')
            record['exit_code'] = process.returncode
        record['elapsed_seconds'] = round(time.monotonic() - started, 6)
        for path in (out, err):
            if path.exists(): acceptance.cap_log(path)
        save_json(private / (label + '.json'), record)
    require(not record['cleanup_failed'] and not record['cleanup_killed'], 'build_cleanup_invalid')
    return record


def pe_subsystem(path):
    data = unlinked(path).read_bytes()
    require(len(data) >= 64 and data[:2] == b'MZ', 'invalid_pe')
    offset = struct.unpack_from('<I', data, 60)[0]
    require(offset <= len(data) - 96 and data[offset:offset + 4] == b'PE\0\0'
            and struct.unpack_from('<H', data, offset + 4)[0] == 0x8664
            and struct.unpack_from('<H', data, offset + 24)[0] == 0x20b, 'invalid_pe_x64')
    return struct.unpack_from('<H', data, offset + 24 + 68)[0]


def dependencies():
    for name, item in portable.DEPENDENCIES.items():
        archive = relative_file(ROOT, 'vendor/downloads/' + item['archive'])
        require(sha(archive) == item['sha256'], 'dependency_archive_hash_mismatch')
        with zipfile.ZipFile(archive) as pinned:
            for member in pinned.infolist():
                if not member.is_dir():
                    require(relative_file(ROOT, 'vendor/' + member.filename).read_bytes() == pinned.read(member),
                            'dependency_source_changed')
    return {'Scintilla.dll': relative_file(ROOT, 'vendor/scintilla/bin/Scintilla.dll'),
            'Lexilla.dll': relative_file(ROOT, 'vendor/lexilla/bin/lexilla.dll')}


def build_variants(root, generated, manifest, compiler, objdump, dlls, resource, bridge, private, deadline):
    """Build already-validated graphs; source identity remains the caller's guard."""
    for unit in manifest['units'] + manifest['preflights']:
        identifier = unit['id']
        destination = root / 'bin' / identifier
        destination.mkdir(parents=True)
        gui = unit.get('path') == 'gui'
        exe_name = 'ru_notepad.exe' if gui else 'app_ru_native.exe' if unit.get('path') == 'cooperative_console' else \
                   'ru_direct_styling_native.exe' if identifier == 'direct_native' else 'profile_boundary.exe'
        translation = generated / identifier / 'checked.c'
        if gui:
            gui_translation = root / (identifier + '-gui.c')
            gui_translation.write_text('#define main ru_program_main\n' + translation.read_text(encoding='utf-8') +
                '\n#undef main\n' + (ROOT / 'packaging/diagnostic_launcher.c').read_text(encoding='utf-8'), encoding='utf-8', newline='\n')
            translation = gui_translation
        output = destination / exe_name
        command = [compiler, *FLAGS, '-I', ROOT / 'native', translation, '-o', output, '-lm', resource]
        if gui:
            command += ['-mwindows', '-lshell32', '-luser32']
        compilation = build_command(command, private, identifier, deadline)
        for name, source in (dict(dlls, **{'profile_bridge.dll': bridge}) if identifier == 'boundary' else dlls).items():
            shutil.copyfile(source, destination / name)
        pe = portable.inspect_pe(output, objdump)
        require(pe_subsystem(output) == (2 if gui else 3), 'variant_subsystem_mismatch')
        yield {'id': identifier, 'exe_name': exe_name, 'exe_sha256': sha(output),
            'generated_c_sha256': unit['generated_c_sha256'], 'linked_c_sha256': sha(translation),
            'resource_sha256': sha(resource), 'subsystem': 2 if gui else 3,
            'seconds': compilation['elapsed_seconds'], 'pe': pe,
            'files': {p.name: sha(p) for p in sorted(destination.iterdir())}}


def prepare(ru_root, mingw_root):
    shared.native_windows()
    root = unlinked(ROOT / 'build/direct-style', must_exist=False)
    require(not root.exists(), 'fresh_benchmark_directory_required')
    root.mkdir(parents=True)
    private = root / 'private'
    private.mkdir()
    started = time.monotonic()
    receipt = {'schema': 1, 'prepared': False, 'error_code': None, 'identity': None,
               'environment': None, 'corpus': shared.verify_corpus(), 'matrix': matrix(),
               'build_budget_seconds': BUILD_BUDGET_SECONDS, 'compile_timeout_seconds': COMPILE_TIMEOUT_SECONDS,
               'elapsed_seconds': None, 'builds': [], 'commands': [], 'generated': None,
               'toolchain': None, 'dependencies': None, 'resource_sha256': None}
    try:
        require(DIRECT_ASSERTIONS > 0, 'direct_fixture_count_unreviewed')
        receipt['identity'] = source_identity(ROOT, ru_root)
        receipt['environment'] = shared.environment_record()
        deadline = started + BUILD_BUDGET_SECONDS
        bin_dir = unlinked(mingw_root / 'bin')
        compiler = relative_file(bin_dir, 'gcc.exe')
        windres = relative_file(bin_dir, 'windres.exe')
        objdump = relative_file(bin_dir, 'objdump.exe')
        receipt['toolchain'] = {'gcc_sha256': sha(compiler), 'windres_sha256': sha(windres),
                                'objdump_sha256': sha(objdump), 'flags': list(FLAGS), 'version_log_sha256': None}
        build_command([compiler, '--version'], private, 'compiler-version', deadline)
        receipt['toolchain']['version_log_sha256'] = sha(private / 'compiler-version.stdout.log')
        dlls = dependencies()
        resource = root / 'app-resource.o'
        build_command([windres, '-I', ROOT / 'packaging', ROOT / 'packaging/app.rc', resource], private, 'resource', deadline)
        receipt['resource_sha256'] = sha(resource)
        helper = root / 'RuSyntax.dll'
        build_command([compiler, *portable.NATIVE_CFLAGS, ROOT / 'native/ru_scan.c', '-o', helper],
                      private, 'native-helper', deadline)
        dlls['RuSyntax.dll'] = helper
        receipt['dependencies'] = {name: sha(path) for name, path in dlls.items()}
        generated = root / 'generated'
        build_command([sys.executable, '-I', ROOT / 'tools/run_direct_style_benchmark.py', '--action', 'generate',
                       '--ru-root', ru_root], private, 'generate', deadline)
        manifest = validate_generated(read_json(generated / 'manifest.json'), generated)
        receipt['generated'] = manifest
        bridge = root / 'profile_bridge.dll'
        build_command([compiler, '-std=c99', '-O2', '-shared', '-static-libgcc',
                       generated / 'boundary/profile_bridge.c', '-o', bridge], private, 'boundary-bridge', deadline)
        for build in build_variants(root, generated, manifest, compiler, objdump, dlls, resource, bridge, private, deadline):
            receipt['builds'].append(build)
            save_json(root / 'prepare.json', receipt)
        require(receipt['identity'] == source_identity(ROOT, ru_root), 'sources_changed_during_build')
        validate_generated(manifest, generated)
        require(time.monotonic() <= deadline, 'build_overrun')
        receipt['prepared'] = True
    except Exception as exc:
        receipt['error_code'] = code(exc, 'prepare_failed')
        raise
    finally:
        receipt['commands'] = [read_json(path) for path in sorted(private.glob('*.json'))]
        receipt['elapsed_seconds'] = round(time.monotonic() - started, 6)
        save_json(root / 'prepare.json', receipt)
    return receipt


def outcome(result, path):
    value = shared.public_outcome(result, {'path': path})
    value['skipped'] = bool(result.get('skips'))
    if value['skipped']:
        value.update(passed=False, error_code='native_run_failed')
    if path == 'gui' and value['passed']:
        acceptance.validate_gui_ru_edits(result.get('edit_performance'))
        value['edit_performance'] = copy.deepcopy(result['edit_performance'])
    return value


def validate_outcome(value, path, *, complete=False):
    base = {'passed', 'executed', 'cleanup_killed', 'exit_code', 'error_code',
            'elapsed_seconds', 'elapsed_seconds_status', 'skipped'}
    optional = {'assertions_passed'}
    if path == 'gui':
        optional |= {'main_hwnd_seen', 'close_posted', 'detached_from_console', 'timer_performance',
                     'full_gui_checks', 'partial_timer_performance', 'edit_performance'}
    elif path == 'cooperative_console':
        optional |= {'timer_performance'}
    require(type(value) is dict and base <= set(value) <= base | optional, 'outcome_shape_mismatch')
    require(all(type(value[key]) is bool for key in ('passed', 'executed', 'cleanup_killed', 'skipped'))
            and (value['exit_code'] is None or type(value['exit_code']) is int)
            and value['error_code'] in (None, 'native_run_failed'), 'outcome_value_invalid')
    shared.validate_outcome_elapsed(value)
    for key in ('main_hwnd_seen', 'close_posted', 'detached_from_console'):
        if key in value:
            require(type(value[key]) is bool, 'outcome_boolean_invalid')
    if 'assertions_passed' in value:
        require(uint(value['assertions_passed']), 'outcome_assertions_invalid')
    if 'partial_timer_performance' in value:
        partial = value['partial_timer_performance']
        require(type(partial) is dict and set(partial) <= {'size', 'wall_ms', 'first_head_style_ms', 'max_response_ms', 'probes'}
                and all(number(item) for item in partial.values()), 'partial_timer_invalid')
    if 'timer_performance' in value:
        if path == 'gui':
            acceptance.validate_gui_ru_timer(value['timer_performance'], require_windows_clock=True)
        else:
            acceptance.validate_ru_gui_measurement(value['timer_performance'], 'RU_GUI_TIMER', require_complete=complete)
    if 'edit_performance' in value:
        acceptance.validate_gui_ru_edits(value['edit_performance'])
    if 'full_gui_checks' in value:
        exact(value['full_gui_checks'], acceptance.GUI_RU_CHECKS, 'gui_check_shape')
        require(all(type(item) is bool for item in value['full_gui_checks'].values()), 'gui_check_value')
    if complete:
        require(value['passed'] and value['executed'] and not value['cleanup_killed'] and not value['skipped']
                and value['exit_code'] == 0 and value['error_code'] is None, 'native_outcome_failed')
        require(value['elapsed_seconds_status'] == 'valid' and value['elapsed_seconds'] > 0,
                'process_clock_unavailable_or_invalid')
        if path == 'gui':
            require(all(value.get(key) is True for key in ('main_hwnd_seen', 'close_posted', 'detached_from_console')),
                    'gui_lifecycle_unproven')
            require(value.get('full_gui_checks') == {key: True for key in acceptance.GUI_RU_CHECKS}, 'gui_checks_incomplete')
            acceptance.validate_gui_ru_edits(value.get('edit_performance'))
            acceptance.validate_gui_ru_timer(value.get('timer_performance'), require_windows_clock=True)
            final = value['timer_performance']['diagnostics']['receipts'][-1]
            require(final['chunks'] == 8798 and final['read_bytes'] == 1000000, 'gui_batch_progress_mismatch')
        elif path == 'cooperative_console':
            require(value.get('assertions_passed') == 8, 'cooperative_assertion_count_mismatch')
            measured = value.get('timer_performance')
            acceptance.validate_ru_gui_measurement(measured, 'RU_GUI_TIMER')
            require(measured['chunks'] == 8798 and measured['max_read'] == 1023, 'cooperative_batch_progress_mismatch')
    shared.check_public_tree(value)
    return value


def parse_output(logs):
    for path in logs:
        require(unlinked(path).stat().st_size <= MAX_LOG_BYTES, 'runtime_log_limit_exceeded')
    return shared.output_check_from_logs(logs)


def empty_results():
    return {'schema': 1, 'complete': False, 'passed': False, 'error_code': None,
            'preflight': [], 'preflight_passed': False, 'runs': [], 'matrix': matrix(),
            'corpus': CORPUS, 'product_acceptance': PRODUCT_STATUS}


def run_native_preflights(api, root, builds):
    """Execute the fixed scanner, boundary and actual-route controls, in order."""
    for name in PREFLIGHTS:
        record = {'id': name, 'passed': False, 'error_code': None, 'outcome': None, 'check': None}
        logs = root / 'runs' / ('preflight-' + name)
        try:
            logs.mkdir()
            build = builds['direct_native' if name == 'scanner' else name]
            source = shared.stage_run_binaries(build, root / 'bin' / build['id'], logs / 'bin')
            if name == 'scanner':
                result = acceptance.run_scanner_preflight(api, source, logs)
                record['outcome'] = outcome(result, 'preflight')
                acceptance.validate_scanner_preflight(result, build['files'], ROOT)
                record['check'] = {'report': result['report'], 'source_sha256': result['source_sha256']}
            elif name == 'boundary':
                result = acceptance.run_console(api, 'profile_boundary', shared.preflight_command(source), logs,
                    r'^RU_SYNTAX_PROFILE_PREFLIGHT_TESTS_PASS=1\s*$', timeout=30, expected_assertions=1, cwd=source)
                record['outcome'] = outcome(result, 'preflight')
                record['check'] = shared.preflight_check_from_logs(sorted(logs.glob('*.log')), 'off')
                shared.validate_preflight_check(record['check'], 'off')
            else:
                result = acceptance.run_console(api, 'ru_direct_styling_native',
                    [str(source / 'ru_direct_styling_native.exe')], logs,
                    rf'^TOTAL PASS: {DIRECT_ASSERTIONS}\s*$', timeout=120, expected_assertions=DIRECT_ASSERTIONS, cwd=source)
                record['outcome'] = outcome(result, 'preflight')
                # Exact route positive/negative controls are part of the
                # fixture's executed PASS inventory, not a variant label.
                stdout = shared.relative_file(logs, 'ru_direct_styling_native.stdout.log').read_text(encoding='utf-8')
                record['check'] = {'assertions': result.get('assertions_passed'),
                    'three_message_positive_control': stdout.count('PASS: original-route positive control observes all three2032/2033/2073 child subclass messages\n') == 1,
                    'three_message_direct_proof': stdout.count('PASS: direct-route proof bypasses all three2032/2033/2073 child subclass messages while folds retain messages and all bytes match\n') == 1}
                require(record['check']['three_message_positive_control'] and record['check']['three_message_direct_proof'],
                        'native_route_proof_missing')
            validate_outcome(record['outcome'], 'preflight', complete=True)
            record['passed'] = True
        except Exception as exc:
            record['error_code'] = code(exc, 'preflight_failed')
        yield record


def run_matrix():
    api = shared.native_windows()
    root = unlinked(ROOT / 'build/direct-style')
    require(not (root / 'runs').exists(), 'fresh_matrix_directory_required')
    (root / 'runs').mkdir()
    summary = empty_results()
    try:
        prepared = validate_prepare(read_json(root / 'prepare.json'), require_complete=True)
        require(candidate_sources(ROOT) == prepared['identity']['candidate'], 'candidate_changed_after_build')
        validate_generated(prepared['generated'], root / 'generated')
        builds = {item['id']: item for item in prepared['builds']}
        for record in run_native_preflights(api, root, builds):
            summary['preflight'].append(record)
            save_json(root / 'results.json', summary)
        summary['preflight_passed'] = len(summary['preflight']) == len(PREFLIGHTS) and all(row['passed'] for row in summary['preflight'])
        require(summary['preflight_passed'], 'native_preflight_failed')
        for row in matrix():
            record = dict(row, passed=False, error_code=None, outcome=None, output_check=None, route_check=None,
                          binary_sha256=None, generated_c_sha256=None, graph_sha256=None)
            summary['runs'].append(record)
            run_dir = root / 'runs' / row['id']
            run_dir.mkdir()
            logs, fixtures = run_dir / 'logs', run_dir / 'fixtures'
            logs.mkdir(); fixtures.mkdir()
            try:
                identifier = variant_id(row['path'], row['route'])
                build = builds[identifier]
                unit = next(item for item in prepared['generated']['units'] if item['id'] == identifier)
                source = shared.stage_run_binaries(build, root / 'bin' / identifier, run_dir / 'bin')
                record.update(binary_sha256=build['exe_sha256'], generated_c_sha256=build['generated_c_sha256'],
                              graph_sha256=digest(json.dumps(unit['source_sha256'], sort_keys=True).encode('utf-8')))
                if row['path'] == 'gui':
                    result = acceptance.run_gui_ru_syntax(api, source, fixtures, logs)
                else:
                    result = acceptance.run_native_console(api, 'app_ru_timer_native', r'^TOTAL PASS: 8\s*$', source, fixtures, logs)
                record['outcome'] = outcome(result, row['path'])
                paths = sorted(logs.glob('*.log'))
                record['output_check'] = parse_output(paths)
                record['route_check'] = route_checks(paths, row['route'], require_complete=False)
                validate_row(record, complete=True)
                record['passed'] = True
            except Exception as exc:
                record['error_code'] = code(exc, 'run_failed')
            finally:
                save_json(run_dir / 'receipt.json', record)
                save_json(root / 'results.json', summary)
        summary['complete'] = True
        require(all(row['passed'] for row in summary['runs']), 'matrix_failed')
        summary['passed'] = True
    except Exception as exc:
        summary['error_code'] = code(exc, 'matrix_failed')
    finally:
        save_json(root / 'results.json', summary)
    return summary


def validate_row(row, *, complete=False):
    base = set(matrix()[0]) | {'passed', 'error_code', 'outcome', 'output_check', 'route_check',
                              'binary_sha256', 'generated_c_sha256', 'graph_sha256'}
    exact(row, base, 'row_shape_mismatch')
    require(type(row['passed']) is bool and (row['error_code'] is None or re.fullmatch('[a-z_]{1,80}', row['error_code'])),
            'row_status_invalid')
    for key in ('binary_sha256', 'generated_c_sha256', 'graph_sha256'):
        require(row[key] is None or hex_digest(row[key]), 'row_hash_invalid')
    if row['outcome'] is not None:
        validate_outcome(row['outcome'], row['path'], complete=complete)
    if row['output_check'] is not None:
        shared.validate_output_check(row['output_check'], require_success=complete)
    if row['route_check'] is not None:
        validate_route_checks(row['route_check'], row['route'], require_complete=complete)
    if complete:
        require(row['outcome'] is not None and row['route_check'] is not None and row['output_check'] is not None,
                'row_evidence_missing')
        require(all(hex_digest(row[key]) for key in ('binary_sha256', 'generated_c_sha256', 'graph_sha256')), 'row_identity_missing')
        require(row['output_check']['style_checksum'] == shared.expected_style_checksum(), 'complete_style_checksum_mismatch')
        wall = shared.primary_wall(row)
        require(row['outcome']['elapsed_seconds'] * 1000 >= wall, 'process_time_less_than_styling')
    shared.check_public_tree(row)
    return row


def validate_results(summary, *, complete=False):
    exact(summary, ('schema', 'complete', 'passed', 'error_code', 'preflight', 'preflight_passed', 'runs',
                    'matrix', 'corpus', 'product_acceptance'), 'results_shape_mismatch')
    require(summary['schema'] == 1 and summary['matrix'] == matrix() and summary['corpus'] == CORPUS
            and summary['product_acceptance'] == PRODUCT_STATUS
            and all(type(summary[key]) is bool for key in ('complete', 'passed', 'preflight_passed'))
            and (summary['error_code'] is None or re.fullmatch('[a-z_]{1,80}', summary['error_code'])), 'results_identity_invalid')
    require(type(summary['preflight']) is list and len(summary['preflight']) <= len(PREFLIGHTS), 'preflight_inventory_invalid')
    for name, record in zip(PREFLIGHTS, summary['preflight']):
        exact(record, ('id', 'passed', 'error_code', 'outcome', 'check'), 'preflight_shape')
        require(record['id'] == name and type(record['passed']) is bool
                and (record['error_code'] is None or re.fullmatch('[a-z_]{1,80}', record['error_code'])), 'preflight_identity_invalid')
        if record['outcome'] is not None:
            validate_outcome(record['outcome'], 'preflight', complete=complete)
        if record['check'] is not None:
            check = record['check']
            if name == 'boundary':
                shared.validate_preflight_check(check, 'off', require_success=complete)
            elif name == 'direct_native':
                exact(check, ('assertions', 'three_message_positive_control', 'three_message_direct_proof'), 'direct_proof_shape')
                require((check['assertions'] is None or uint(check['assertions']))
                        and type(check['three_message_positive_control']) is bool
                        and type(check['three_message_direct_proof']) is bool, 'direct_proof_value_invalid')
                if complete:
                    require(check['assertions'] == DIRECT_ASSERTIONS and DIRECT_ASSERTIONS > 0
                            and check['three_message_positive_control'] and check['three_message_direct_proof'], 'direct_proof_failed')
            else:
                exact(check, ('report', 'source_sha256'), 'scanner_proof_shape')
                exact(check['report'], acceptance.SCANNER_PREFLIGHT_REPORT_FIELDS, 'scanner_report_shape')
                require(check['source_sha256'] == acceptance.scanner_preflight_sources(ROOT), 'scanner_source_mismatch')
                report = check['report']
                require(report['cases'] == 157 and report['chunk_checks'] == 942 and report['ru_assertions_per_backend'] == 0
                        and report['sanitizer'] is None and hex_digest(report['library_sha256'])
                        and report['source_sha256'] == check['source_sha256']['native/ru_scan.c'], 'scanner_report_invalid')
        if complete:
            require(record['passed'] and record['error_code'] is None and record['outcome'] is not None and record['check'] is not None,
                    'preflight_failed')
            if name != 'scanner':
                require(record['outcome'].get('assertions_passed') == (1 if name == 'boundary' else DIRECT_ASSERTIONS),
                        'preflight_assertion_count_mismatch')
    require(type(summary['runs']) is list and len(summary['runs']) <= 8, 'result_inventory_invalid')
    for expected, row in zip(matrix(), summary['runs']):
        require(all(row.get(key) == value for key, value in expected.items()), 'matrix_order_mismatch')
        validate_row(row, complete=complete)
        if complete:
            require(row['passed'] and row['error_code'] is None, 'matrix_row_failed')
    if complete:
        require(summary['complete'] and summary['passed'] and summary['preflight_passed'] and summary['error_code'] is None
                and len(summary['runs']) == 8 and len(summary['preflight']) == len(PREFLIGHTS), 'matrix_incomplete')
    shared.check_public_tree(summary)
    return summary


def verify_results(summary, prepared):
    validate_prepare(prepared, require_complete=True)
    validate_results(summary, complete=True)
    builds = {item['id']: item for item in prepared['builds']}
    units = {item['id']: item for item in prepared['generated']['units']}
    for row in summary['runs']:
        identifier = variant_id(row['path'], row['route'])
        build, unit = builds[identifier], units[identifier]
        require(row['binary_sha256'] == build['exe_sha256']
                and row['generated_c_sha256'] == build['generated_c_sha256'] == unit['generated_c_sha256']
                and row['graph_sha256'] == digest(json.dumps(unit['source_sha256'], sort_keys=True).encode('utf-8')),
                'row_route_or_binary_substitution')
    scanner = summary['preflight'][0]['check']['report']
    require(scanner['library_sha256'] == prepared['dependencies']['RuSyntax.dll'], 'preflight_dll_mismatch')
    pairs = []
    for path in PATHS:
        for repeat in (1, 2):
            paired = {row['route']: row for row in summary['runs'] if row['path'] == path and row['repeat'] == repeat}
            direct, message = paired['direct'], paired['message']
            dw, mw = shared.primary_wall(direct), shared.primary_wall(message)
            pair = {'path': path, 'repeat': repeat, 'direct_run': direct['id'], 'message_run': message['id'],
                    'direct_wall_ms': dw, 'message_wall_ms': mw, 'direct_minus_message_ms': dw - mw,
                    'direct_over_message_ratio': dw / mw,
                    'direct_process_seconds': direct['outcome']['elapsed_seconds'],
                    'message_process_seconds': message['outcome']['elapsed_seconds'],
                    'direct_process_minus_styling_ms': direct['outcome']['elapsed_seconds'] * 1000 - dw,
                    'message_process_minus_styling_ms': message['outcome']['elapsed_seconds'] * 1000 - mw}
            pairs.append(pair)
    return {'schema': 1, 'verified': True, 'pairs': pairs, 'product_acceptance': PRODUCT_STATUS,
            'statistical_confidence_claim': False, 'performance_success_threshold': None,
            'measurement_notes': [
                'Two pairs per path are observations on one runner, not a statistical significance or broad speed claim.',
                'Fresh processes use the same binaries, dependencies and corpus; operating-system cache state is uncontrolled.',
                'Process seconds are measured acceptance intervals; missing or invalid clocks cannot pass and are never backfilled.',
                'Process-minus-styling includes setup, all other probes, verification, edits and close; it is not isolated checker overhead.',
                'No phase or callback counters run. Shared full-byte checker and endpoint scaffolding can affect roots and GC equally.',
                'Initial route endpoint queries are included in styling wall; final route/full-byte checks follow completion.',
                'Endpoint eligibility plus native route controls and unique source bool prove the selected experiment, not a per-batch dynamic trace.']}


ROUTE_PREFIX = 'RU_DIRECT_ROUTE '
ROUTE_FIELDS = ('phase', 'enabled', 'eligible', 'registered', 'ready', 'owner', 'parent',
                'document', 'generation', 'revision', 'length', 'mask', 'pointer', 'pending')
ROUTE_SOURCE = '''
如语 取 外言 './ru_syntax.ru'.
_证据 取 {'begin':0,'end':0,'document':'','generation':0}.
算 路由 柄 阶段 为 数:
    长 取 (窗 其 发送 柄 2183 0 0) 其 数.
    若 阶段 == 0 且 长 != 1000000 则 得 空. 然
    若 长 != 1000000 或 (阶段 != 0 且 阶段 != 1) 则 卒 'Invalid route endpoint target.'. 然
    态 取 如语 其 _状态 柄.
    若 态 == 空 或 态['language'] != 'ru' 或 态['inTick'] 或 态['revision'] != 0 则 卒 'Invalid route endpoint state.'. 然
    权 取 态['direct'].
    若 权 == 空 或 非 ((如语 其 _直库态)['ready']) 或 非 (如语 其 _同线程 柄) 或 非 (如语 其 _同线程 权['parent']) 则 卒 'Route endpoint is not registered on its owner thread.'. 然
    若 权['thread'] != (窗 其 结果 ((如语 其 _GetCurrentThreadId) 其 调用 [])) 其 句 或 (窗 其 结果 ((如语 其 _GetParent) 其 调用 [柄])) 其 句 != (权['parent']) 其 句 则 卒 'Route endpoint parent or owner changed.'. 然
    若 权['generation'] != 态['generation'] 或 权['document'] != 态['document'] 或 (窗 其 发送 柄 2357 0 0) 其 句 != 态['document'] 或 (窗 其 发送 柄 2378 0 0) 其 数 != 3 则 卒 'Route endpoint document or notification mask changed.'. 然
    启用 取 (如语 其 _直接策略)['enabled'].
    合格 取 如语 其 _直属合格 柄 态 长 态['generation'] 态['revision'].
    若 合格 != 启用 则 卒 'Route endpoint eligibility differs from its sole route selector.'. 然
    借 取 窗 其 发送 柄 2185 0 0.
    有针 取 非 (借 其 为空).
    借 取 空.
    若 非 有针 则 卒 'Route endpoint has no native direct context.'. 然
    现 取 如语 其 _状态 柄.
    若 现 == 空 或 现['generation'] != 态['generation'] 或 现['revision'] != 0 或 现['document'] != 态['document'] 或 现['direct'] != 权 则 卒 'Route endpoint changed during its final pointer query.'. 然
    若 阶段 == 0 则
        若 _证据['begin'] != 0 或 非 态['pending'] 则 卒 'Route initial endpoint is not unique and pending.'. 然
        _证据 其 增 'begin' 1.
        _证据 其 增 'document' 态['document'].
        _证据 其 增 'generation' 态['generation'].
    另
        若 _证据['begin'] != 1 或 _证据['end'] != 0 或 态['pending'] 或 _证据['document'] != 态['document'] 或 _证据['generation'] != 态['generation'] 则 卒 'Route final endpoint changed identity or is incomplete.'. 然
        _证据 其 增 'end' 1.
    然
    开 取 0. 待 取 0.
    若 启用 则 开 取 1. 然
    若 态['pending'] 则 待 取 1. 然
    显 'RU_DIRECT_ROUTE phase='+(阶段 为 句)+' enabled='+(开 为 句)+' eligible='+(开 为 句)+' registered=1 ready=1 owner=1 parent=1 document=1 generation='+(态['generation'] 为 句)+' revision=0 length=1000000 mask=3 pointer=1 pending='+(待 为 句).
    得 空.
法
'''


def check_module():
    original = generator.CHECK_MODULE
    anchor = "    若 态 == 空 或 态['pending'] 或 态['feed'] != 1000000 或 态['bytes'] != 1000000 则 卒 'Profile target is incomplete.'. 然"
    return generator.once(original, anchor, anchor + '\n    路由 柄 1.') + ROUTE_SOURCE


def validate_route_checks(records, route, *, require_complete=True):
    require(route in ROUTES and type(records) is list and (len(records) == 2 if require_complete else len(records) <= 2), 'route_endpoint_count')
    for phase, record in enumerate(records):
        exact(record, ROUTE_FIELDS, 'route_endpoint_shape')
        require(all(uint(value) for value in record.values()), 'route_endpoint_number')
        expected = dict(phase=phase, enabled=int(route == 'direct'), eligible=int(route == 'direct'),
                        registered=1, ready=1, owner=1, parent=1, document=1,
                        revision=0, length=1000000, mask=3, pointer=1, pending=1 - phase)
        require(all(record[key] == value for key, value in expected.items()) and record['generation'] > 0,
                'route_eligibility_unproven')
    if len(records) == 2:
        require(records[0]['generation'] == records[1]['generation'], 'route_generation_changed')
    return records


def route_checks(logs, route, *, require_complete=True):
    records = []
    for path in logs:
        require(unlinked(path).stat().st_size <= MAX_LOG_BYTES, 'runtime_log_limit_exceeded')
        for line in path.read_text(encoding='utf-8', errors='strict').splitlines():
            if line.startswith(ROUTE_PREFIX):
                tokens = line[len(ROUTE_PREFIX):].split(' ')
                require(len(tokens) == len(ROUTE_FIELDS), 'route_endpoint_shape')
                record = {}
                for token, key in zip(tokens, ROUTE_FIELDS):
                    require(re.fullmatch(re.escape(key) + r'=[0-9]+', token) is not None, 'route_endpoint_shape')
                    record[key] = int(token.split('=')[1])
                records.append(record)
    return validate_route_checks(records, route, require_complete=require_complete)


def validate_hash_map(value, *, names=None):
    require(type(value) is dict and 1 <= len(value) <= 300 and all(hex_digest(item) for item in value.values()), 'hash_map_invalid')
    if names is not None:
        require(set(value) == set(names), 'hash_map_inventory_invalid')
    for name in value:
        # Validate syntax without depending on the existence of generated paths.
        require(type(name) is str and len(name) <= 240 and '\\' not in name and ':' not in name and '\x00' not in name
                and not name.startswith('/') and all(part not in ('', '.', '..') for part in name.split('/')), 'hash_map_path_invalid')


def validate_prepare_execution(record, expected_ids, *, require_complete=False):
    """Only execution receipts; callers retain their own closed source/graph guards."""
    if record['environment'] is not None:
        exact(record['environment'], ('platform', 'os_version', 'architecture', 'logical_cpus', 'python_version', 'cpu', 'cold_warm'),
              'environment_shape')
        require(record['environment']['platform'] == 'native-windows-x64'
                and record['environment']['cold_warm'] == 'fresh_process_os_cache_uncontrolled', 'environment_invalid')
    if record['toolchain'] is not None:
        exact(record['toolchain'], ('gcc_sha256', 'windres_sha256', 'objdump_sha256', 'flags', 'version_log_sha256'), 'toolchain_shape')
        require(record['toolchain']['flags'] == list(FLAGS)
                and all(hex_digest(record['toolchain'][key]) for key in ('gcc_sha256', 'windres_sha256', 'objdump_sha256'))
                and (record['toolchain']['version_log_sha256'] is None or hex_digest(record['toolchain']['version_log_sha256'])),
                'toolchain_invalid')
    if record['dependencies'] is not None:
        validate_hash_map(record['dependencies'], names=('Scintilla.dll', 'Lexilla.dll', 'RuSyntax.dll'))
    require(record['resource_sha256'] is None or hex_digest(record['resource_sha256']), 'resource_hash_invalid')
    require(type(record['commands']) is list and len(record['commands']) <= 20, 'command_inventory_invalid')
    stages = set()
    for command in record['commands']:
        exact(command, ('stage', 'elapsed_seconds', 'exit_code', 'error_code', 'cleanup_killed', 'cleanup_failed'), 'command_shape')
        require(type(command['stage']) is str and re.fullmatch('[a-z_-]{1,80}', command['stage']) and command['stage'] not in stages
                and number(command['elapsed_seconds']) and (command['exit_code'] is None or type(command['exit_code']) is int)
                and (command['error_code'] is None or re.fullmatch('[a-z_]{1,80}', command['error_code']))
                and type(command['cleanup_killed']) is bool and type(command['cleanup_failed']) is bool, 'command_invalid')
        stages.add(command['stage'])
        if require_complete:
            require(command['exit_code'] == 0 and command['error_code'] is None and not command['cleanup_killed']
                    and not command['cleanup_failed'] and command['elapsed_seconds'] <= COMPILE_TIMEOUT_SECONDS, 'command_failed')
    require(type(record['builds']) is list and len(record['builds']) <= 6, 'build_inventory_invalid')
    for identifier, build in zip(expected_ids, record['builds']):
        exact(build, ('id', 'exe_name', 'exe_sha256', 'generated_c_sha256', 'linked_c_sha256', 'resource_sha256',
                      'subsystem', 'seconds', 'pe', 'files'), 'build_shape')
        expected_exe = 'ru_notepad.exe' if identifier.startswith('gui-') else 'app_ru_native.exe' if identifier.startswith('cooperative_console-') else \
                       'ru_direct_styling_native.exe' if identifier == 'direct_native' else 'profile_boundary.exe'
        require(build['id'] == identifier and build['exe_name'] == expected_exe and build['subsystem'] == (2 if identifier.startswith('gui-') else 3)
                and number(build['seconds']) and build['seconds'] <= COMPILE_TIMEOUT_SECONDS
                and all(hex_digest(build[key]) for key in ('exe_sha256', 'generated_c_sha256', 'linked_c_sha256', 'resource_sha256'))
                and build['resource_sha256'] == record['resource_sha256'], 'build_identity_invalid')
        names = {expected_exe, 'Scintilla.dll', 'Lexilla.dll', 'RuSyntax.dll'} | ({'profile_bridge.dll'} if identifier == 'boundary' else set())
        validate_hash_map(build['files'], names=names)
        require(build['files'][expected_exe] == build['exe_sha256']
                and all(build['files'][name] == checksum for name, checksum in record['dependencies'].items()), 'build_dependency_mismatch')
        exact(build['pe'], ('sha256', 'bytes', 'machine', 'imports'), 'pe_shape')
        require(build['pe']['sha256'] == build['exe_sha256'] and uint(build['pe']['bytes']) and build['pe']['bytes'] > 0
                and build['pe']['machine'] == 'AMD64' and type(build['pe']['imports']) is list
                and all(type(name) is str and re.fullmatch('[A-Za-z0-9_.-]+', name) for name in build['pe']['imports']), 'pe_identity_invalid')
    return stages


def validate_prepare(record, *, require_complete=False):
    fields = ('schema', 'prepared', 'error_code', 'identity', 'environment', 'corpus', 'matrix',
              'build_budget_seconds', 'compile_timeout_seconds', 'elapsed_seconds', 'builds', 'commands',
              'generated', 'toolchain', 'dependencies', 'resource_sha256')
    exact(record, fields, 'prepare_shape_mismatch')
    require(record['schema'] == 1 and type(record['prepared']) is bool
            and (record['error_code'] is None or re.fullmatch('[a-z_]{1,80}', record['error_code']))
            and record['corpus'] == CORPUS and record['matrix'] == matrix()
            and record['build_budget_seconds'] == BUILD_BUDGET_SECONDS
            and record['compile_timeout_seconds'] == COMPILE_TIMEOUT_SECONDS
            and (record['elapsed_seconds'] is None or number(record['elapsed_seconds'])), 'prepare_identity_invalid')
    if record['identity'] is not None:
        identity = record['identity']
        exact(identity, ('candidate', 'compiler'), 'identity_shape')
        require(identity['compiler'] == {'commit': RU_COMMIT, 'tree': RU_TREE}, 'compiler_identity_invalid')
        candidate = identity['candidate']
        exact(candidate, ('accepted_commit', 'accepted_tree', 'candidate_commit', 'candidate_tree',
                          'accepted_source_sha256', 'source_sha256', 'reviewed_changes', 'harness_inputs'), 'candidate_identity_shape')
        require(candidate['accepted_commit'] == BASELINE_PUBLIC_COMMIT and candidate['accepted_tree'] == BASELINE_TREE
                and candidate['reviewed_changes'] == sorted(REVIEWED_CHANGED_SHA256) and candidate['harness_inputs'] == list(OWNED)
                and all(type(candidate[key]) is str and re.fullmatch('[0-9a-f]{40}', candidate[key])
                        for key in ('candidate_commit', 'candidate_tree')), 'candidate_identity_invalid')
        original = tracked(ROOT, BASELINE_TREE)
        validate_hash_map(candidate['accepted_source_sha256'], names=original)
        validate_hash_map(candidate['source_sha256'], names=set(original) | set(OWNED) | set(NEW_INPUTS))
        actual_delta = {name for name, value in candidate['source_sha256'].items()
                        if name not in OWNED and value != candidate['accepted_source_sha256'].get(name)}
        require(actual_delta == set(REVIEWED_CHANGED_SHA256)
                and all(candidate['source_sha256'][name] == expected for name, expected in REVIEWED_CHANGED_SHA256.items()),
                'candidate_reviewed_delta_invalid')
        for name, checksum in candidate['accepted_source_sha256'].items():
            require(checksum == digest(subprocess.check_output(['git', '-C', str(ROOT), 'show', BASELINE_TREE + ':' + name], timeout=30)),
                    'accepted_identity_substituted')
    expected_ids = variants() + ['direct_native', 'boundary']
    stages = validate_prepare_execution(record, expected_ids, require_complete=require_complete)
    if record['generated'] is not None:
        validate_generated(record['generated'], ROOT / 'build/direct-style/generated')
        units = {unit['id']: unit for unit in record['generated']['units'] + record['generated']['preflights']}
        for build in record['builds']:
            require(build['generated_c_sha256'] == units[build['id']]['generated_c_sha256'], 'build_generated_hash_mismatch')
    if require_complete:
        require(record['prepared'] and record['error_code'] is None and len(record['builds']) == 6
                and all(record[key] is not None for key in ('identity', 'environment', 'toolchain', 'dependencies', 'resource_sha256', 'generated'))
                and hex_digest(record['toolchain']['version_log_sha256'])
                and number(record['elapsed_seconds']) and record['elapsed_seconds'] <= BUILD_BUDGET_SECONDS
                and stages == set(expected_ids) | {'compiler-version', 'resource', 'native-helper', 'generate', 'boundary-bridge'},
                'prepare_incomplete')
    shared.check_public_tree(record)
    return record


MAX_PUBLIC_FILES = 35
PUBLIC_RECEIPT_RESERVE = 16384
DEPENDENCY_STAGES = {'dependency-download-scintilla567', 'dependency-download-lexilla554',
                     'dependency-scintilla', 'dependency-lexilla'}


def validate_dependency_setup(value):
    exact(value, ('schema', 'passed', 'commands', 'elapsed_seconds'), 'dependency_setup_shape')
    require(value['schema'] == 1 and type(value['passed']) is bool and number(value['elapsed_seconds'])
            and type(value['commands']) is list and len(value['commands']) <= 4, 'dependency_setup_invalid')
    seen = set()
    for command in value['commands']:
        exact(command, ('stage', 'elapsed_seconds', 'exit_code', 'error_code', 'cleanup_killed', 'cleanup_failed'), 'dependency_command_shape')
        require(command['stage'] in DEPENDENCY_STAGES and command['stage'] not in seen
                and number(command['elapsed_seconds']) and (command['exit_code'] is None or type(command['exit_code']) is int)
                and (command['error_code'] is None or re.fullmatch('[a-z_]{1,80}', command['error_code']))
                and type(command['cleanup_killed']) is bool and type(command['cleanup_failed']) is bool, 'dependency_command_invalid')
        seen.add(command['stage'])
        if value['passed']:
            require(command['exit_code'] == 0 and command['error_code'] is None and not command['cleanup_killed']
                    and not command['cleanup_failed'] and command['elapsed_seconds'] <= COMPILE_TIMEOUT_SECONDS,
                    'dependency_command_failed')
    if value['passed']:
        require(seen == DEPENDENCY_STAGES and value['elapsed_seconds'] <= 600, 'dependency_setup_incomplete')
    shared.check_public_tree(value)
    return value


def runtime_logs(root):
    """Only predefined synthetic process-log directories; never recurse fixtures."""
    selected = []
    directories = [(root / 'runs' / row['id'] / 'logs',
        r'main-ru-syntax-launcher-[0-3]\.log' if row['path'] == 'gui' else r'app_ru_timer_native\.(?:stdout|stderr)\.log')
        for row in matrix()]
    directories += [(root / 'runs' / ('preflight-' + name),
        re.escape({'scanner': portable.SCANNER_PREFLIGHT_NAME, 'boundary': 'profile_boundary',
                   'direct_native': 'ru_direct_styling_native'}[name]) + r'\.(?:stdout|stderr)\.log')
        for name in PREFLIGHTS]
    for folder, pattern in directories:
        if not folder.exists(): continue
        for path in sorted(unlinked(folder).glob('*.log')):
            require(re.fullmatch(pattern, path.name) is not None, 'unexpected_runtime_log')
            selected.append(unlinked(path))
            require(len(selected) <= 30, 'runtime_log_count_exceeded')
    return selected


def collect():
    root = unlinked(ROOT / 'build/direct-style', must_exist=False)
    target = unlinked(ROOT / 'build/direct-style-evidence', must_exist=False)
    require(not target.exists(), 'fresh_evidence_directory_required')
    target.mkdir(parents=True)
    errors, emitted = [], []
    total = 0
    def publish(name, content):
        nonlocal total
        require(len(emitted) + 1 < MAX_PUBLIC_FILES, 'public_file_count_exceeded')
        require(total + len(content) + PUBLIC_RECEIPT_RESERVE <= MAX_PUBLIC_BYTES, 'public_evidence_size_exceeded')
        relative_file(target, name, must_exist=False).write_bytes(content)
        total += len(content)
        emitted.append(name)
    def publish_json(name, record):
        shared.check_public_tree(record)
        content = (json.dumps(record, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + '\n').encode('utf-8')
        require(len(content) <= shared.MAX_JSON_BYTES, 'oversize_json')
        publish(name, content)
    try:
        setup = validate_dependency_setup(read_json(ROOT / 'build/dependency-direct-style-setup.json'))
        publish_json('dependency-setup.json', setup)
        if not setup['passed']: errors.append('dependency_setup_failed')
    except Exception as exc:
        errors.append(code(exc, 'dependency_setup_missing_or_invalid'))
    for name, validator in (('prepare', validate_prepare), ('results', validate_results)):
        try:
            path = root / (name + '.json')
            require(path.is_file(), 'missing_' + name + '_receipt')
            record = validator(read_json(path))
            publish_json(name + '.json', record)
        except Exception as exc:
            errors.append(code(exc, 'invalid_' + name + '_receipt'))
    # Success proof is recalculated, never copied from an unvalidated JSON file.
    try:
        verified = verify_results(read_json(root / 'results.json'), read_json(root / 'prepare.json'))
        publish_json('verification.json', verified)
    except Exception as exc:
        errors.append(code(exc, 'verification_failed'))
    try:
        for index, path in enumerate(runtime_logs(root)):
            content, _ = shared.sanitize_runtime_log(path)
            publish(f'run-{index:03d}.log', content)
    except Exception as exc:
        errors.append(code(exc, 'runtime_log_collection_failed'))
    receipt = {'schema': 1, 'collected': True, 'verified': not errors, 'errors': sorted(set(errors)),
               'files': emitted, 'product_acceptance': PRODUCT_STATUS}
    encoded = (json.dumps(receipt, indent=2, sort_keys=True) + '\n').encode('utf-8')
    require(len(encoded) <= PUBLIC_RECEIPT_RESERVE and total + len(encoded) <= MAX_PUBLIC_BYTES
            and len(emitted) + 1 <= MAX_PUBLIC_FILES, 'collection_receipt_budget_exceeded')
    relative_file(target, 'collection.json', must_exist=False).write_bytes(encoded)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--action', choices=('generate', 'prepare', 'run', 'verify', 'collect'), required=True)
    parser.add_argument('--ru-root', type=Path)
    parser.add_argument('--mingw-root', type=Path)
    args = parser.parse_args()
    try:
        if args.action in ('generate', 'prepare'):
            require(args.ru_root is not None, 'compiler_root_required')
        if args.action == 'generate':
            source_identity(ROOT, args.ru_root)
            result = generate(args.ru_root.resolve(), ROOT / 'build/direct-style/generated')
            print(json.dumps({'schema': 1, 'generated': len(result['units']) == 4, 'native_execution': False}))
        elif args.action == 'prepare':
            require(args.mingw_root is not None, 'mingw_root_required')
            result = prepare(args.ru_root.resolve(), args.mingw_root.resolve())
            print(json.dumps({'schema': 1, 'prepared': result['prepared']}))
        elif args.action == 'run':
            result = run_matrix()
            print(json.dumps({'schema': 1, 'complete': result['complete'], 'passed': result['passed']}))
            return 0 if result['passed'] else 1
        elif args.action == 'verify':
            result = verify_results(read_json(ROOT / 'build/direct-style/results.json'), read_json(ROOT / 'build/direct-style/prepare.json'))
            save_json(ROOT / 'build/direct-style/verification.json', result)
            print(json.dumps({'schema': 1, 'verified': True}))
        else:
            result = collect()
            print(json.dumps(result))
            return 0 if result['verified'] else 1
        return 0
    except Exception as exc:
        print(json.dumps({'schema': 1, 'passed': False, 'error_code': code(exc, 'benchmark_failed')}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
