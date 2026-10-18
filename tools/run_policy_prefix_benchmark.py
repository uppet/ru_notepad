#!/usr/bin/env python3
"""Same-run Windows comparison of exactly two reviewed Ru lexical policies.

Both policies use the current candidate's direct style route. Only the copied
src/ru_lexical.ru bytes differ. This benchmark is never product acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import run_direct_style_benchmark as execution

shared, generator = execution.shared, execution.generator
acceptance, portable = execution.acceptance, execution.portable
Error, require, exact = execution.Error, execution.require, execution.exact
sha, digest = execution.sha, execution.digest
save_json, read_json = execution.save_json, execution.read_json
relative_file, unlinked = execution.relative_file, execution.unlinked
number, hex_digest = execution.number, execution.hex_digest
code, git, tracked = execution.code, execution.git, execution.tracked
CORPUS, PATHS, PREFLIGHTS = execution.CORPUS, execution.PATHS, execution.PREFLIGHTS
PRODUCT_STATUS = execution.PRODUCT_STATUS
BUILD_BUDGET_SECONDS, COMPILE_TIMEOUT_SECONDS = 900, 180
STYLE_TIMEOUT_SECONDS = 30
COMMAND_MEASUREMENT = 'predeclared_argv_sha256_v1'
BASELINE_PUBLIC_COMMIT = 'a5f5fd825767cd5af662cba792f5ce352991c21e'
BASELINE_TREE = 'e8a402fb3eb551bfe416b8aee0aaaf942d2d4f4a'
LEXICAL = 'src/ru_lexical.ru'
POLICIES = ('baseline', 'prefix')
POLICY_SHA256 = {'baseline': 'f78589e247186890855526f7bb3624d34e4004bb8fbc69587c96d38c826a602c',
                 'prefix': 'deb5629333f2e76125b396bfe640b327ea6f1fd42f95f24277c86c5209fb12ec'}
OWNED = ('tools/run_policy_prefix_benchmark.py', 'tools/test_policy_prefix_benchmark.py',
         '.github/workflows/policy-prefix-benchmark.yml', 'tools/run_direct_style_benchmark.py',
         '.github/workflows/direct-style-benchmark.yml', 'benchmarks/README.md')
NEW_INPUTS = (
    'docs/ru-policy-fastpath-experiment.md',
    'tools/test_ru_policy_fast.py',
    'tools/benchmark_ru_policy_fast.py',
    'tools/verify_ru_policy_fast_outputs.py',
    'tests/fixtures/ru_policy_fast_plan.json',
    'tools/prepare_source_archives.py',
    'tools/test_source_archives.py',
    'third_party/source_archives/README.md',
    'third_party/source_archives/scintilla567.zip',
    'third_party/source_archives/lexilla554.zip',
    'third_party/source_archives/Scintilla-Lexilla-License.txt',
    'third_party/source_archives/Boost-License.txt',
    'third_party/source_archives/Mako-AUTHORS.txt',
    'third_party/source_archives/Mako-LICENSE.txt',
    'third_party/source_archives/NixOS-samples-MIT.txt',
    'third_party/source_archives/Nixpkgs-COPYING.txt',
    'third_party/source_archives/Unicode-2016.txt',
    'third_party/source_archives/Unicode-V3.txt',
)
# Final independently reviewed non-harness hashes are filled only at source freeze.
# An unfinished or extra delta fails closed; no inventory is learned at runtime.
REVIEWED_CHANGED_SHA256 = {
    ".github/workflows/windows.yml": "9568cdf3d37a6f09a36a1146652d1ce3483c3c02c83a06c67ffad07f94c5c8cc",
    "CHANGELOG.md": "e6be7327cc6cba80fdd3ae20ca503a4902ea92b35884df82b14207864983fc4d",
    "README.md": "cf5cb27568d8b393e030cd13313605dec31fbeb913cd5b2ce5ddce2bd679469c",
    "THIRD_PARTY_NOTICES.md": "1446314a3148870aa76cbcfd58cf04ecc83ce69a732b71c0b26d0b9a3a5225ec",
    "VERSION": "cf2dab38106cba47d35071879d2d9063a7c27391879cf15f4f2062e0761a3347",
    "docs/build-provenance.md": "f3465536312f72b0b580e1a1839dac947afa04ff994b89b6520d7f2c4f38a674",
    "docs/direct-style-publication.md": "55f2c27ed9c85ecadd171519e4a7704f24703d0d8295b40d8a8a79a727797dc8",
    "docs/preview-validation.md": "96a1dacec6be26e7536ea96c8a01f061e0f2451bc32c29955299c549d05b4e27",
    "docs/ru-language-syntax.md": "ddffdc487c2f95b94ce8756949afaf5e2f0c81bc284f497966f789f86eed5820",
    "docs/ru-policy-fastpath-experiment.md": "775536db8c7046faa6e71978b07935595fdb999cadd11ebe7134fb2e23982bc9",
    "docs/status-and-shortcuts.md": "c773e6bb019277693438d42740d5f20e950c533e910b04985be74bf15ea710fc",
    "docs/syntax-highlighting.md": "5f1f9c98e3ffcea324372b0a870ab917ac20e5db8868cd55983c2e58bd5cf8f9",
    "packaging/README-preview.txt": "525a2cfefba7b31c853ae72bfc5d965e36ddbe3f2e61c7e0fcabbc3d8c77b2ee",
    "packaging/app.rc": "cd12c1cee077cc96c1cf726a84b90f21c01a5432e1560bfa37898addf97a0a10",
    "packaging/开始前请读.txt": "ef5eaabacd30ad2d3e13f4c1c6118c4c94518e83d5c6ac001f6c9439e7401d27",
    "src/main.ru": "aad60f9974b4450436e91557239e981946cb84fcf5b9fb5431e3414f7a161897",
    "src/ru_lexical.ru": "deb5629333f2e76125b396bfe640b327ea6f1fd42f95f24277c86c5209fb12ec",
    "tests/fixtures/ru_policy_fast_plan.json": "a712c3b5c70e5bfe4ae09900d928f594c2c88bb49448d40ca15422b09a015e90",
    "third_party/source_archives/Boost-License.txt": "beb8e42e9d6b4284e03304d05a81a0755200a965fc8d0a5e0aea1e84cf805d6e",
    "third_party/source_archives/Mako-AUTHORS.txt": "228d95c3bd268d84bbc85714b89c6120688c510b7c15626ec628b0c945b55918",
    "third_party/source_archives/Mako-LICENSE.txt": "8c1d171bc5d341ad9cd33d5e2c39b96a82c7bd49b3ae89a470c37e5822232054",
    "third_party/source_archives/NixOS-samples-MIT.txt": "88175d5fdd42c291bed5dbfe3fe0f7710d043b9c980b9669ac0012936a9172fe",
    "third_party/source_archives/Nixpkgs-COPYING.txt": "c9cf0650a6820b589f96a92060e0eb937102b808f48cd5e3f35dcba449ea0a41",
    "third_party/source_archives/README.md": "29f84d542121413977c3ec917d8000ceb11e6f99a3ea96d99309d9c13171f888",
    "third_party/source_archives/Scintilla-Lexilla-License.txt": "185c5a37521316e940ead89cbf0b1ba5862d810c7c966e6c6a14a4a515b23625",
    "third_party/source_archives/Unicode-2016.txt": "eeba269c94183d337cbbbf16b75ef2869feaf4b722b04586055c13171e68cfb9",
    "third_party/source_archives/Unicode-V3.txt": "e7a93b009565cfce55919a381437ac4db883e9da2126fa28b91d12732bc53d96",
    "third_party/source_archives/lexilla554.zip": "5e0a21356e4e2f19d6a38ecd1c8172d5a2b7b4542940568b023386080db90fe0",
    "third_party/source_archives/scintilla567.zip": "2309181e59e7da4659f890dbc128db7451ccd094748770e7be674b830494587c",
    "tools/benchmark_ru_policy_fast.py": "08f1f86e0dec120dd0e6f7a10dccdacfcfa0483bda03d3a54882b87677612b59",
    "tools/prepare_source_archives.py": "319a931294c9969f77fa32735c406ce0a3b1589230a676caebfc152af3d8de97",
    "tools/test_ru_policy_fast.py": "2d2af5d851cfa5086e678b3150f4c20f7440f4a57eca78d4439d1b29f59fd1ef",
    "tools/test_ru_syntax_profile.py": "301a55c4180d79d4d44556e5d1c6a85a5e868aeaf3c5cf7c9a9bccae835b88cb",
    "tools/test_source_archives.py": "b290d522def148510fe116bf1b0e31a162a815549d603979f4c365a7f663141b",
    "tools/test_windows_ci.py": "ca791e49dfde3684f7927597468aac533a4e7abfe3d597853e3df8ef1fae694f",
    "tools/verify_ru_policy_fast_outputs.py": "fb8401c520ed4f44c572c1638731d364c1c7e53bc4a708f1e5955847fb818de4",
    "tools/windows_ci.ps1": "4b7986ca5706d9817558f22a10e2d8cdd68b52971e8658f960f917728a9de652",
    "tools/windows_ci.py": "e6d697e776a659b9c78bb5032d298b9caeea807e63a48dbbe053570495e1bc0c",
    "vendor/README.md": "0dcc213708069b3e68bf0acd35fef7c37387e32b06404ff64d259822fb436ee5"
}
GRAPH_NOTES = ('Both policies use the same current candidate, direct route, compiler, roots, '
               'resources and untimed full-byte checker. Only src/ru_lexical.ru differs.')
BRIDGE_SHA256 = '45689caba1b8552424a87dd6fd061818dbf1daab57d066461e7d91d93ea7e65f'
MAX_PUBLIC_BYTES = execution.MAX_PUBLIC_BYTES
# One additional closed source receipt; historical replay limits stay unchanged.
MAX_PUBLIC_FILES = execution.MAX_PUBLIC_FILES + 1
SOURCE_ARCHIVES = (
    ('scintilla567', 'scintilla567.zip', 1904249,
     '2309181e59e7da4659f890dbc128db7451ccd094748770e7be674b830494587c'),
    ('lexilla554', 'lexilla554.zip', 1598324,
     '5e0a21356e4e2f19d6a38ecd1c8172d5a2b7b4542940568b023386080db90fe0'),
)
SOURCE_ARCHIVE_ERRORS = frozenset({
    'in_progress', 'not_checked', 'invalid_arguments', 'unsafe_path',
    'path_missing', 'not_directory', 'link_rejected', 'not_regular',
    'hardlink_rejected', 'path_changed', 'already_exists', 'size_mismatch',
    'hash_mismatch', 'zip_invalid', 'zip_member_count', 'zip_member_path',
    'zip_member_type', 'zip_member_duplicate', 'zip_member_size',
    'zip_expanded_size', 'zip_compression', 'zip_encrypted', 'zip_payload_invalid',
    'io_error', 'internal_error', 'receipt_error', 'source_failed', 'target_failed',
})
DEPENDENCY_STAGES = frozenset({'source-archive-tests', 'source-archives',
                             'dependency-scintilla', 'dependency-lexilla'})
DEPENDENCY_COMMAND_ERRORS = frozenset({'build_budget_exceeded', 'build_log_limit_exceeded',
    'build_overrun', 'build_command_failed', 'build_process_failed', 'build_cleanup_failed',
    'build_cleanup_invalid'})


def read_source_archive_receipt(path):
    """Read a bounded ordinary receipt, never helper stdout or private logs."""
    import prepare_source_archives as offline
    path = unlinked(path)
    with offline.SafeDir(path.parent) as directory:
        fd = directory.open(path.name)
        try:
            require(os.fstat(fd).st_size <= 8192, 'source_archive_receipt_oversize')
            data = b''
            while len(data) <= 8192:
                chunk = os.read(fd, 8193 - len(data))
                if not chunk: break
                data += chunk
            require(len(data) <= 8192, 'source_archive_receipt_oversize')
            directory.validate(path.name, fd)
        finally:
            os.close(fd)
    return shared.strict_json(data.decode('utf-8'))


def validate_source_archive_receipt(value, *, require_passed=False):
    """Independent closed schema: a helper's claimed pass is insufficient."""
    exact(value, ('schema_version', 'implementation', 'passed', 'error_code',
                  'receipt_error_code', 'dependencies'), 'source_archive_receipt_shape')
    require(type(value['schema_version']) is int and value['schema_version'] == 1
        and value['implementation'] == 'reconstructed-offline-v1' and type(value['passed']) is bool
        and (value['error_code'] is None or type(value['error_code']) is str and value['error_code'] in SOURCE_ARCHIVE_ERRORS)
        and (value['receipt_error_code'] is None or type(value['receipt_error_code']) is str and value['receipt_error_code'] in SOURCE_ARCHIVE_ERRORS)
        and type(value['dependencies']) is list and len(value['dependencies']) == 2,
        'source_archive_receipt_invalid')
    require((value['passed'] and value['error_code'] is None and value['receipt_error_code'] is None)
        or (not value['passed'] and value['error_code'] is not None), 'source_archive_receipt_status')
    if value['receipt_error_code'] is not None:
        require(value['error_code'] == 'receipt_error', 'source_archive_receipt_status')
    for item, (identifier, filename, size, checksum) in zip(value['dependencies'], SOURCE_ARCHIVES):
        exact(item, ('id', 'expected_bytes', 'expected_sha256', 'source', 'target', 'status'),
              'source_archive_dependency_shape')
        require(item['id'] == identifier and type(item['expected_bytes']) is int
            and item['expected_bytes'] == size and item['expected_sha256'] == checksum
            and item['status'] in ('pending', 'copied', 'reused', 'failed'), 'source_archive_identity_invalid')
        for side in ('source', 'target'):
            observation = item[side]
            exact(observation, ('actual_bytes', 'actual_sha256', 'verified', 'error_code'),
                  'source_archive_observation_shape')
            require((observation['actual_bytes'] is None or shared.uint(observation['actual_bytes']))
                and (observation['actual_sha256'] is None or hex_digest(observation['actual_sha256']))
                and type(observation['verified']) is bool
                and (observation['error_code'] is None or type(observation['error_code']) is str and observation['error_code'] in SOURCE_ARCHIVE_ERRORS),
                'source_archive_observation_invalid')
            if observation['verified']:
                require(observation['actual_bytes'] == size and observation['actual_sha256'] == checksum
                    and observation['error_code'] is None, 'source_archive_observation_unproven')
            else:
                require(observation['error_code'] is not None, 'source_archive_observation_unproven')
        if value['passed']:
            require(item['status'] in ('copied', 'reused') and item['source']['verified']
                and item['target']['verified'], 'source_archive_receipt_unproven')
    if require_passed:
        require(value['passed'], 'source_archive_preparation_failed')
    shared.check_public_tree(value)
    return value


def validate_dependency_setup(value, *, require_passed=False):
    """Current offline workflow only; historical replay validators stay fixed."""
    exact(value, ('schema', 'passed', 'error_code', 'commands', 'elapsed_seconds'), 'dependency_setup_shape')
    require(type(value['schema']) is int and value['schema'] == 1 and type(value['passed']) is bool
        and value['error_code'] in (None, 'dependency_setup_failed')
        and number(value['elapsed_seconds']) and value['elapsed_seconds'] <= 86400
        and type(value['commands']) is list and len(value['commands']) <= 4, 'dependency_setup_invalid')
    require((value['passed'] and value['error_code'] is None)
        or (not value['passed'] and value['error_code'] == 'dependency_setup_failed'), 'dependency_setup_status')
    seen = set()
    for command in value['commands']:
        exact(command, ('stage', 'elapsed_seconds', 'exit_code', 'error_code', 'cleanup_killed', 'cleanup_failed'),
              'dependency_command_shape')
        require(type(command['stage']) is str and command['stage'] in DEPENDENCY_STAGES and command['stage'] not in seen
            and number(command['elapsed_seconds']) and command['elapsed_seconds'] <= 86400
            and (command['exit_code'] is None or type(command['exit_code']) is int and -(2**32) <= command['exit_code'] < 2**32)
            and (command['error_code'] is None or type(command['error_code']) is str and command['error_code'] in DEPENDENCY_COMMAND_ERRORS)
            and type(command['cleanup_killed']) is bool and type(command['cleanup_failed']) is bool,
            'dependency_command_invalid')
        seen.add(command['stage'])
        if value['passed']:
            require(command['exit_code'] == 0 and command['error_code'] is None and not command['cleanup_killed']
                and not command['cleanup_failed'] and command['elapsed_seconds'] <= COMPILE_TIMEOUT_SECONDS,
                'dependency_command_failed')
    if value['passed']:
        require(seen == DEPENDENCY_STAGES and value['elapsed_seconds'] <= 600, 'dependency_setup_incomplete')
    if require_passed:
        require(value['passed'], 'dependency_setup_failed')
    shared.check_public_tree(value)
    return value


def work_root():
    return ROOT / 'build/policy-prefix'


def matrix():
    plan = [('gui', 'prefix', 1), ('cooperative_console', 'baseline', 1),
            ('gui', 'baseline', 1), ('cooperative_console', 'prefix', 1),
            ('cooperative_console', 'prefix', 2), ('gui', 'baseline', 2),
            ('cooperative_console', 'baseline', 2), ('gui', 'prefix', 2)]
    return [dict(id=f'{order:02d}-{path}-{policy}-{repeat}', order=order,
                 path=path, policy=policy, repeat=repeat)
            for order, (path, policy, repeat) in enumerate(plan, 1)]


def variant_id(path, policy):
    require(path in PATHS and policy in POLICIES, 'unknown_variant')
    return path + '-' + policy


def variants():
    return [variant_id(path, policy) for path in PATHS for policy in POLICIES]


def baseline_sources(root):
    original = tracked(root, BASELINE_TREE)
    require(len(original) == len(set(original)) == 120, 'accepted_source_inventory_mismatch')
    return {name: digest(subprocess.check_output(
        ['git', '-C', str(root), 'show', BASELINE_TREE + ':' + name], timeout=30)) for name in original}


def validate_candidate_identity(candidate, root):
    exact(candidate, ('accepted_commit', 'accepted_tree', 'candidate_commit', 'candidate_tree',
                     'accepted_source_sha256', 'source_sha256', 'reviewed_changes', 'harness_inputs'), 'candidate_identity_shape')
    accepted = baseline_sources(root)
    require(candidate['accepted_commit'] == BASELINE_PUBLIC_COMMIT and candidate['accepted_tree'] == BASELINE_TREE
            and candidate['accepted_source_sha256'] == accepted
            and candidate['reviewed_changes'] == sorted(REVIEWED_CHANGED_SHA256)
            and candidate['harness_inputs'] == list(OWNED)
            and all(type(candidate[key]) is str and re.fullmatch('[0-9a-f]{40}', candidate[key])
                    for key in ('candidate_commit', 'candidate_tree')), 'candidate_identity_invalid')
    hashes = candidate['source_sha256']
    execution.validate_hash_map(hashes, names=set(accepted) | set(OWNED) | set(NEW_INPUTS))
    delta = {name for name in hashes if name not in OWNED and hashes[name] != accepted.get(name)}
    require(delta == set(REVIEWED_CHANGED_SHA256)
            and all(hashes[name] == value for name, value in REVIEWED_CHANGED_SHA256.items()),
            'reviewed_candidate_hash_mismatch')
    require(hashes[LEXICAL] == POLICY_SHA256['prefix'] and accepted[LEXICAL] == POLICY_SHA256['baseline'],
            'policy_identity_mismatch')
    return candidate


def candidate_sources(root):
    require(git('status', '--porcelain', '--untracked-files=all', root=root) == '', 'dirty_candidate_checkout')
    accepted = baseline_sources(root)
    names = tracked(root)
    require(set(names) == set(accepted) | set(OWNED) | set(NEW_INPUTS), 'candidate_source_inventory_mismatch')
    hashes = {name: sha(relative_file(root, name)) for name in names}
    require(set(p.relative_to(root).as_posix() for p in (root / 'src').glob('*.ru')) ==
            {name for name in names if name.startswith('src/') and name.endswith('.ru')}, 'untracked_source_module')
    return validate_candidate_identity({'accepted_commit': BASELINE_PUBLIC_COMMIT, 'accepted_tree': BASELINE_TREE,
        'candidate_commit': git('rev-parse', 'HEAD', root=root), 'candidate_tree': git('rev-parse', 'HEAD^{tree}', root=root),
        'accepted_source_sha256': accepted, 'source_sha256': hashes,
        'reviewed_changes': sorted(REVIEWED_CHANGED_SHA256), 'harness_inputs': list(OWNED)}, root)


def source_identity(root, ru_root):
    return {'candidate': candidate_sources(root), 'compiler': execution.compiler_identity(ru_root)}


def policy_source(policy):
    require(policy in POLICIES, 'unknown_policy')
    raw = (subprocess.check_output(['git', '-C', str(ROOT), 'show', BASELINE_TREE + ':' + LEXICAL], timeout=30)
           if policy == 'baseline' else relative_file(ROOT, LEXICAL).read_bytes())
    require(digest(raw) == POLICY_SHA256[policy], 'policy_source_hash_mismatch')
    require(b'\r' not in raw and not raw.startswith(b'\xef\xbb\xbf'), 'policy_source_encoding_mismatch')
    return raw.decode('utf-8')


def variant_sources(path, policy):
    entry, files = execution.verification_sources(path)
    # Checking, never flipping, the route is part of every graph's canonical form.
    require(execution.substitute_route(files['src/ru_syntax.ru'], 'direct') == files['src/ru_syntax.ru'],
            'direct_route_required')
    files[LEXICAL] = policy_source(policy)
    return entry, files


def assert_policy_graphs(left, right):
    require(type(left) is dict and type(right) is dict and set(left) == set(right), 'policy_graph_inventory_mismatch')
    require([name for name in left if left[name] != right[name]] == [LEXICAL], 'policy_graph_has_extra_difference')
    for policy, files in zip(POLICIES, (left, right)):
        require(files[LEXICAL] == policy_source(policy), 'policy_graph_substitution_mismatch')
        execution.substitute_route(files['src/ru_syntax.ru'], 'direct')


def preflight_sources(identifier):
    if identifier == 'direct_native':
        return 'tests/ru_direct_styling_native.ru', {
            p.relative_to(ROOT).as_posix(): p.read_text(encoding='utf-8-sig')
            for folder in ('src', 'tests') for p in sorted((ROOT / folder).glob('*.ru'))}
    require(identifier == 'boundary', 'unknown_preflight')
    return 'profile_boundary.ru', {'profile_boundary.ru': generator.PREFLIGHT_SOURCE}


def generated_header():
    return {'schema': 1, 'units': [], 'preflights': [], 'graph_contract': GRAPH_NOTES,
            'policy_sha256': dict(POLICY_SHA256), 'direct_route': True,
            'check_module_sha256': digest(execution.check_module().encode('utf-8')),
            'check_c_sha256': digest(generator.CHECK_C.encode('utf-8'))}


def write_sources(folder, files):
    unlinked(folder, must_exist=False).mkdir(parents=True)
    for name, content in files.items():
        target = relative_file(folder, name, must_exist=False)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8', newline='\n')


def generate(ru_root, output):
    execution.compiler_identity(ru_root)
    require(not unlinked(output, must_exist=False).exists(), 'fresh_generated_directory_required')
    output.mkdir(parents=True)
    manifest = generated_header()
    for path in PATHS:
        paired = {}
        for policy in POLICIES:
            entry, files = variant_sources(path, policy)
            folder = output / variant_id(path, policy)
            write_sources(folder, files)
            unit = execution.emit_graph(entry, folder, ru_root, checker=True)
            unit.update(id=variant_id(path, policy), path=path, policy=policy,
                        source_sha256={name: sha(folder / name) for name in files})
            manifest['units'].append(unit)
            paired[policy] = files
        assert_policy_graphs(paired['baseline'], paired['prefix'])
    for identifier in ('direct_native', 'boundary'):
        entry, files = preflight_sources(identifier)
        folder = output / identifier
        write_sources(folder, files)
        unit = execution.emit_graph(entry, folder, ru_root, full_runtime=identifier == 'boundary')
        if identifier == 'boundary':
            generator.instrument(folder / 'original.c', folder / 'checked.c', instrumentation='off', path='preflight', mode='full')
            unit['generated_c_sha256'] = sha(folder / 'checked.c')
            bridge = relative_file(ru_root, 'tests/fixtures/native/c_backend_bridge.c')
            require(sha(bridge) == BRIDGE_SHA256, 'boundary_bridge_source_mismatch')
            shutil.copyfile(bridge, folder / 'profile_bridge.c')
            files['profile_bridge.c'] = bridge.read_text(encoding='utf-8')
        unit.update(id=identifier, source_sha256={name: sha(folder / name) for name in files})
        manifest['preflights'].append(unit)
    save_json(output / 'manifest.json', manifest)
    return manifest


def canonical_loaded_modules(entry, folder, ru_root, expected_sources):
    """Reconstruct the complete pinned module closure, not just pair equality."""
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(ru_root))
    from rulang.frontend import parse
    from rulang.modules import load_module_graph
    source = relative_file(folder, entry)
    content = source.read_text(encoding='utf-8')
    graph = load_module_graph(str(source), parse(content))
    graph.sources[graph.root] = content
    hashes = {}
    compiler_files = set(tracked(ru_root))
    for key, text in graph.sources.items():
        item = unlinked(Path(key))
        if folder.resolve() in item.resolve().parents:
            name = item.resolve().relative_to(folder.resolve()).as_posix()
            require(name in expected_sources, 'loaded_module_outside_source_inventory')
            require(digest(text.encode('utf-8')) == expected_sources[name], 'loaded_module_source_hash_changed')
        else:
            require(ru_root.resolve() in item.resolve().parents, 'module_outside_closed_graph')
            name = item.resolve().relative_to(ru_root.resolve()).as_posix()
            require(name in compiler_files, 'untracked_compiler_module')
            name = 'compiler/' + name
        require(text.encode('utf-8') == item.read_bytes(), 'loaded_module_encoding_or_source_changed')
        hashes[name] = digest(text.encode('utf-8'))
    return hashes


def validate_generated(manifest, directory, ru_root=None):
    header = generated_header()
    exact(manifest, header, 'generated_manifest_shape')
    require(all(manifest[name] == header[name] for name in header if name not in ('units', 'preflights')),
            'generated_contract_mismatch')
    require(type(manifest['units']) is list and type(manifest['preflights']) is list
            and [u.get('id') for u in manifest['units']] == variants()
            and [u.get('id') for u in manifest['preflights']] == ['direct_native', 'boundary'], 'generated_inventory_mismatch')
    ru_root = unlinked(ru_root or ROOT / '.ci/ru-language')
    execution.compiler_identity(ru_root)
    for unit in manifest['units'] + manifest['preflights']:
        measured = unit in manifest['units']
        entry, files = (variant_sources(unit.get('path'), unit.get('policy')) if measured else preflight_sources(unit['id']))
        expected = {name: digest(content.encode('utf-8')) for name, content in files.items()}
        if unit['id'] == 'boundary': expected['profile_bridge.c'] = BRIDGE_SHA256
        require(unit.get('entry') == entry and unit.get('source_sha256') == expected, 'generated_graph_not_current_candidate')
        exact(unit, {'entry', 'loaded_modules_sha256', 'original_c_sha256', 'generated_c_sha256', 'checker', 'id',
                     'source_sha256'} | ({'path', 'policy'} if measured else set()), 'generated_unit_shape')
        folder = unlinked(directory / unit['id'])
        for name, checksum in expected.items():
            require(sha(relative_file(folder, name)) == checksum, 'generated_source_changed')
        require(unit['loaded_modules_sha256'] == canonical_loaded_modules(entry, folder, ru_root, expected), 'loaded_graph_not_canonical')
        if measured:
            require(unit['loaded_modules_sha256'].get(LEXICAL) == POLICY_SHA256[unit['policy']]
                    and unit['id'] == variant_id(unit['path'], unit['policy']) and unit['checker'] is True,
                    'variant_policy_identity_mismatch')
        else:
            require(unit['checker'] is False, 'preflight_checker_changed')
        require(sha(relative_file(folder, 'original.c')) == unit['original_c_sha256']
                and sha(relative_file(folder, 'checked.c')) == unit['generated_c_sha256'], 'generated_c_changed')
        if measured:
            require(execution.checker_only((folder / 'original.c').read_text(encoding='utf-8')) ==
                    (folder / 'checked.c').read_text(encoding='utf-8'), 'checked_c_source_substituted')
    for path in PATHS:
        maps = [{name: (directory / variant_id(path, policy) / name).read_text(encoding='utf-8')
                 for name in next(u for u in manifest['units'] if u['id'] == variant_id(path, policy))['source_sha256']}
                for policy in POLICIES]
        assert_policy_graphs(*maps)
        loaded = [next(u for u in manifest['units'] if u['id'] == variant_id(path, policy))['loaded_modules_sha256']
                  for policy in POLICIES]
        require(set(loaded[0]) == set(loaded[1]) and [name for name in loaded[0] if loaded[0][name] != loaded[1][name]] == [LEXICAL],
                'loaded_policy_graph_has_extra_difference')
    return manifest


def command_digest(command):
    return digest(json.dumps(list(map(str, command)), ensure_ascii=True, separators=(',', ':')).encode('utf-8'))


def prepare(ru_root, mingw_root):
    shared.native_windows()
    root = unlinked(work_root(), must_exist=False)
    require(not root.exists(), 'fresh_benchmark_directory_required')
    root.mkdir(parents=True)
    private = root / 'private'; private.mkdir()
    started = time.monotonic()
    receipt = {'schema': 1, 'prepared': False, 'error_code': None, 'identity': None,
        'environment': None, 'corpus': shared.verify_corpus(), 'matrix': matrix(),
        'build_budget_seconds': BUILD_BUDGET_SECONDS, 'compile_timeout_seconds': COMPILE_TIMEOUT_SECONDS,
        'elapsed_seconds': None, 'builds': [], 'commands': [], 'command_sha256': {},
        'command_measurement': COMMAND_MEASUREMENT, 'generated': None,
        'toolchain': None, 'dependencies': None, 'resource_sha256': None}
    deadline = started + BUILD_BUDGET_SECONDS
    def execute(command, label):
        receipt['command_sha256'][label] = command_digest(command)
        return execution.build_command(command, private, label, deadline)
    try:
        receipt['identity'] = source_identity(ROOT, ru_root)
        validate_source_archive_receipt(read_source_archive_receipt(
            ROOT / 'build/dependency-policy-prefix-source-archives.json'), require_passed=True)
        validate_dependency_setup(read_json(ROOT / 'build/dependency-policy-prefix-setup.json'), require_passed=True)
        receipt['environment'] = shared.environment_record()
        compiler, windres, objdump = [relative_file(unlinked(mingw_root / 'bin'), name + '.exe')
                                     for name in ('gcc', 'windres', 'objdump')]
        receipt['toolchain'] = {'gcc_sha256': sha(compiler), 'windres_sha256': sha(windres),
            'objdump_sha256': sha(objdump), 'flags': list(execution.FLAGS), 'version_log_sha256': None}
        execute([compiler, '--version'], 'compiler-version')
        receipt['toolchain']['version_log_sha256'] = sha(private / 'compiler-version.stdout.log')
        dlls = execution.dependencies()
        resource = root / 'app-resource.o'
        execute([windres, '-I', ROOT / 'packaging', ROOT / 'packaging/app.rc', resource], 'resource')
        receipt['resource_sha256'] = sha(resource)
        helper = root / 'RuSyntax.dll'
        execute([compiler, *portable.NATIVE_CFLAGS, ROOT / 'native/ru_scan.c', '-o', helper], 'native-helper')
        dlls['RuSyntax.dll'] = helper
        receipt['dependencies'] = {name: sha(path) for name, path in dlls.items()}
        generated = root / 'generated'
        execute([sys.executable, '-I', ROOT / 'tools/run_policy_prefix_benchmark.py', '--action', 'generate',
                 '--ru-root', ru_root], 'generate')
        manifest = validate_generated(read_json(generated / 'manifest.json'), generated, ru_root)
        receipt['generated'] = manifest
        bridge = root / 'profile_bridge.dll'
        execute([compiler, '-std=c99', '-O2', '-shared', '-static-libgcc',
                 generated / 'boundary/profile_bridge.c', '-o', bridge], 'boundary-bridge')
        # Record the exact predeclared argv, without publishing machine-local paths.
        # Stage receipts distinguish executed commands from later unattempted builds.
        for unit in manifest['units'] + manifest['preflights']:
            identifier, gui = unit['id'], unit.get('path') == 'gui'
            exe = 'ru_notepad.exe' if gui else 'app_ru_native.exe' if unit.get('path') == 'cooperative_console' else \
                  'ru_direct_styling_native.exe' if identifier == 'direct_native' else 'profile_boundary.exe'
            translation = root / (identifier + '-gui.c') if gui else generated / identifier / 'checked.c'
            command = [compiler, *execution.FLAGS, '-I', ROOT / 'native', translation, '-o', root / 'bin' / identifier / exe, '-lm', resource]
            if gui: command += ['-mwindows', '-lshell32', '-luser32']
            receipt['command_sha256'][identifier] = command_digest(command)
        for build in execution.build_variants(root, generated, manifest, compiler, objdump, dlls, resource, bridge, private, deadline):
            receipt['builds'].append(build)
            save_json(root / 'prepare.json', receipt)
        require(receipt['identity'] == source_identity(ROOT, ru_root), 'sources_changed_during_build')
        validate_generated(manifest, generated, ru_root)
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


def validate_prepare(record, *, require_complete=False):
    exact(record, ('schema', 'prepared', 'error_code', 'identity', 'environment', 'corpus', 'matrix',
        'build_budget_seconds', 'compile_timeout_seconds', 'elapsed_seconds', 'builds', 'commands',
        'command_sha256', 'command_measurement', 'generated', 'toolchain', 'dependencies', 'resource_sha256'), 'prepare_shape_mismatch')
    require(record['schema'] == 1 and type(record['prepared']) is bool
        and (record['error_code'] is None or re.fullmatch('[a-z_]{1,80}', record['error_code']))
        and record['corpus'] == CORPUS and record['matrix'] == matrix()
        and record['command_measurement'] == COMMAND_MEASUREMENT
        and record['build_budget_seconds'] == BUILD_BUDGET_SECONDS and record['compile_timeout_seconds'] == COMPILE_TIMEOUT_SECONDS
        and (record['elapsed_seconds'] is None or number(record['elapsed_seconds'])), 'prepare_identity_invalid')
    if record['identity'] is not None:
        exact(record['identity'], ('candidate', 'compiler'), 'identity_shape')
        require(record['identity']['compiler'] == {'commit': execution.RU_COMMIT, 'tree': execution.RU_TREE}, 'compiler_identity_invalid')
        validate_candidate_identity(record['identity']['candidate'], ROOT)
    expected_ids = variants() + ['direct_native', 'boundary']
    require(type(record['builds']) is list and len(record['builds']) <= 6
            and [build.get('id') for build in record['builds']] == expected_ids[:len(record['builds'])],
            'build_inventory_invalid')
    stages = execution.validate_prepare_execution(record, expected_ids, require_complete=require_complete)
    expected_stages = set(expected_ids) | {'compiler-version', 'resource', 'native-helper', 'generate', 'boundary-bridge'}
    hashes = record['command_sha256']
    require(type(hashes) is dict and set(hashes) <= expected_stages and stages <= set(hashes)
            and all(hex_digest(value) for value in hashes.values()), 'command_hash_inventory_invalid')
    if record['generated'] is not None:
        validate_generated(record['generated'], work_root() / 'generated')
        units = {unit['id']: unit for unit in record['generated']['units'] + record['generated']['preflights']}
        for build in record['builds']:
            require(build['generated_c_sha256'] == units[build['id']]['generated_c_sha256'], 'build_generated_hash_mismatch')
    if require_complete:
        require(record['prepared'] and record['error_code'] is None and len(record['builds']) == 6
            and all(record[key] is not None for key in ('identity', 'environment', 'toolchain', 'dependencies', 'resource_sha256', 'generated'))
            and hex_digest(record['toolchain']['version_log_sha256']) and number(record['elapsed_seconds'])
            and record['elapsed_seconds'] <= BUILD_BUDGET_SECONDS and stages == set(hashes) == expected_stages, 'prepare_incomplete')
    shared.check_public_tree(record)
    return record


def empty_results():
    return {'schema': 1, 'complete': False, 'passed': False, 'error_code': None,
            'preflight': [], 'preflight_passed': False, 'runs': [], 'matrix': matrix(),
            'corpus': CORPUS, 'product_acceptance': PRODUCT_STATUS, 'command_measurement': COMMAND_MEASUREMENT}


def runtime_command(row, run_dir):
    if row['path'] == 'gui':
        isolated = run_dir / 'fixtures/gui-ru-syntax'
        return [isolated / 'ru_notepad.exe', isolated / 'Ru 源码路径 😀/语法 折叠 😀.ru']
    return acceptance.console_command('app_ru_timer_native', run_dir / 'bin', run_dir / 'fixtures')


def run_matrix():
    api = shared.native_windows()
    root = unlinked(work_root())
    require(not (root / 'runs').exists(), 'fresh_matrix_directory_required')
    (root / 'runs').mkdir()
    summary = empty_results()
    try:
        prepared = validate_prepare(read_json(root / 'prepare.json'), require_complete=True)
        require(candidate_sources(ROOT) == prepared['identity']['candidate'], 'candidate_changed_after_build')
        validate_generated(prepared['generated'], root / 'generated')
        builds = {item['id']: item for item in prepared['builds']}
        for record in execution.run_native_preflights(api, root, builds):
            summary['preflight'].append(record)
            save_json(root / 'results.json', summary)
        summary['preflight_passed'] = len(summary['preflight']) == len(PREFLIGHTS) and all(row['passed'] for row in summary['preflight'])
        require(summary['preflight_passed'], 'native_preflight_failed')
        for row in matrix():
            record = dict(row, passed=False, error_code=None, outcome=None, output_check=None, route_check=None,
                          binary_sha256=None, generated_c_sha256=None, graph_sha256=None, command_sha256=None)
            summary['runs'].append(record)
            run_dir = root / 'runs' / row['id']; run_dir.mkdir()
            logs, fixtures = run_dir / 'logs', run_dir / 'fixtures'; logs.mkdir(); fixtures.mkdir()
            try:
                identifier = variant_id(row['path'], row['policy'])
                build = builds[identifier]
                unit = next(item for item in prepared['generated']['units'] if item['id'] == identifier)
                source = shared.stage_run_binaries(build, root / 'bin' / identifier, run_dir / 'bin')
                record.update(binary_sha256=build['exe_sha256'], generated_c_sha256=build['generated_c_sha256'],
                    graph_sha256=digest(json.dumps(unit['source_sha256'], sort_keys=True).encode('utf-8')),
                    command_sha256=command_digest(runtime_command(row, run_dir)))
                result = (acceptance.run_gui_ru_syntax(api, source, fixtures, logs) if row['path'] == 'gui' else
                          acceptance.run_native_console(api, 'app_ru_timer_native', r'^TOTAL PASS: 8\s*$', source, fixtures, logs))
                record['outcome'] = execution.outcome(result, row['path'])
                paths = sorted(logs.glob('*.log'))
                record['output_check'] = execution.parse_output(paths)
                record['route_check'] = execution.route_checks(paths, 'direct', require_complete=False)
                validate_row(record, complete=True)
                record['passed'] = True
            except Exception as exc:
                record['error_code'] = code(exc, 'run_failed')
            finally:
                save_json(run_dir / 'receipt.json', record)
                save_json(root / 'results.json', summary)
        require(candidate_sources(ROOT) == prepared['identity']['candidate'], 'candidate_changed_during_run')
        validate_generated(prepared['generated'], root / 'generated')
        summary['complete'] = True
        require(all(row['passed'] for row in summary['runs']), 'matrix_failed')
        summary['passed'] = True
    except Exception as exc:
        summary['error_code'] = code(exc, 'matrix_failed')
    finally:
        save_json(root / 'results.json', summary)
    return summary


def validate_row(row, *, complete=False):
    hashes = ('binary_sha256', 'generated_c_sha256', 'graph_sha256', 'command_sha256')
    exact(row, set(matrix()[0]) | {'passed', 'error_code', 'outcome', 'output_check', 'route_check'} | set(hashes), 'row_shape_mismatch')
    require(type(row['passed']) is bool and (row['error_code'] is None or re.fullmatch('[a-z_]{1,80}', row['error_code'])), 'row_status_invalid')
    require(all(row[key] is None or hex_digest(row[key]) for key in hashes), 'row_hash_invalid')
    require(row['policy'] in POLICIES and row['path'] in PATHS, 'row_variant_invalid')
    if row['outcome'] is not None: execution.validate_outcome(row['outcome'], row['path'], complete=complete)
    if row['output_check'] is not None: shared.validate_output_check(row['output_check'], require_success=complete)
    if row['route_check'] is not None: execution.validate_route_checks(row['route_check'], 'direct', require_complete=complete)
    if complete:
        require(all(row[key] is not None for key in ('outcome', 'route_check', 'output_check'))
                and all(hex_digest(row[key]) for key in hashes), 'row_evidence_missing')
        require(row['output_check']['style_checksum'] == shared.expected_style_checksum(), 'complete_style_checksum_mismatch')
        require(row['outcome']['elapsed_seconds'] * 1000 >= shared.primary_wall(row), 'process_time_less_than_styling')
        require(row['command_sha256'] == command_digest(runtime_command(row, work_root() / 'runs' / row['id'])), 'runtime_command_changed')
    shared.check_public_tree(row)
    return row


def validate_results(summary, *, complete=False):
    exact(summary, ('schema', 'complete', 'passed', 'error_code', 'preflight', 'preflight_passed', 'runs',
                    'matrix', 'corpus', 'product_acceptance', 'command_measurement'), 'results_shape_mismatch')
    require(summary['schema'] == 1 and summary['matrix'] == matrix() and summary['corpus'] == CORPUS
            and summary['product_acceptance'] == PRODUCT_STATUS and summary['command_measurement'] == COMMAND_MEASUREMENT
            and all(type(summary[key]) is bool for key in ('complete', 'passed', 'preflight_passed'))
            and (summary['error_code'] is None or re.fullmatch('[a-z_]{1,80}', summary['error_code'])), 'results_identity_invalid')
    require(type(summary['preflight']) is list and len(summary['preflight']) <= len(PREFLIGHTS), 'preflight_inventory_invalid')
    for name, record in zip(PREFLIGHTS, summary['preflight']):
        exact(record, ('id', 'passed', 'error_code', 'outcome', 'check'), 'preflight_shape')
        require(record['id'] == name and type(record['passed']) is bool
                and (record['error_code'] is None or re.fullmatch('[a-z_]{1,80}', record['error_code'])), 'preflight_identity_invalid')
        if record['outcome'] is not None:
            execution.validate_outcome(record['outcome'], 'preflight', complete=complete)
        if record['check'] is not None:
            check = record['check']
            if name == 'boundary':
                shared.validate_preflight_check(check, 'off', require_success=complete)
            elif name == 'direct_native':
                exact(check, ('assertions', 'three_message_positive_control', 'three_message_direct_proof'), 'direct_proof_shape')
                require((check['assertions'] is None or execution.uint(check['assertions']))
                        and type(check['three_message_positive_control']) is bool
                        and type(check['three_message_direct_proof']) is bool, 'direct_proof_value_invalid')
                if complete:
                    require(check['assertions'] == execution.DIRECT_ASSERTIONS and execution.DIRECT_ASSERTIONS > 0
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
                require(record['outcome'].get('assertions_passed') == (1 if name == 'boundary' else execution.DIRECT_ASSERTIONS),
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
    require(candidate_sources(ROOT) == prepared['identity']['candidate'], 'candidate_changed_after_build')
    builds = {item['id']: item for item in prepared['builds']}
    units = {item['id']: item for item in prepared['generated']['units']}
    for row in summary['runs']:
        identifier = variant_id(row['path'], row['policy'])
        build, unit = builds[identifier], units[identifier]
        require(row['binary_sha256'] == build['exe_sha256']
            and row['generated_c_sha256'] == build['generated_c_sha256'] == unit['generated_c_sha256']
            and row['graph_sha256'] == digest(json.dumps(unit['source_sha256'], sort_keys=True).encode('utf-8')),
            'row_policy_or_binary_substitution')
    require(summary['preflight'][0]['check']['report']['library_sha256'] == prepared['dependencies']['RuSyntax.dll'], 'preflight_dll_mismatch')
    pairs = []
    for path in PATHS:
        for repeat in (1, 2):
            pair = {row['policy']: row for row in summary['runs'] if row['path'] == path and row['repeat'] == repeat}
            base, prefix = pair['baseline'], pair['prefix']
            bw, pw = shared.primary_wall(base), shared.primary_wall(prefix)
            pairs.append({'path': path, 'repeat': repeat, 'baseline_run': base['id'], 'prefix_run': prefix['id'],
                'baseline_wall_ms': bw, 'prefix_wall_ms': pw, 'prefix_minus_baseline_ms': pw - bw,
                'prefix_over_baseline_ratio': pw / bw,
                'baseline_process_seconds': base['outcome']['elapsed_seconds'],
                'prefix_process_seconds': prefix['outcome']['elapsed_seconds'],
                'baseline_process_minus_styling_ms': base['outcome']['elapsed_seconds'] * 1000 - bw,
                'prefix_process_minus_styling_ms': prefix['outcome']['elapsed_seconds'] * 1000 - pw})
    return {'schema': 1, 'verified': True, 'pairs': pairs, 'policy_sha256': POLICY_SHA256,
        'direct_route': True, 'product_acceptance': PRODUCT_STATUS, 'command_measurement': COMMAND_MEASUREMENT,
        'statistical_confidence_claim': False, 'performance_success_threshold': None,
        'measurement_notes': [
            'Two interleaved pairs per path are observations on one runner, not a statistical significance or broad speed claim.',
            'Both policies use the current candidate and direct route; this is not the earlier message-route comparison.',
            'Fresh processes share compiler, dependencies, resources, harness and corpus; OS cache state is uncontrolled.',
            'No profiling hot counters run. Common complete-byte checker and route endpoints can affect GC and roots equally.',
            'Process-minus-styling includes setup, all other probes, verification, edits and normal close; it is not isolated checker overhead.',
            'Initial route endpoint queries are included in styling wall; final eligibility and full-byte checks follow completion.']}


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
    root = unlinked(work_root(), must_exist=False)
    target = unlinked(ROOT / 'build/policy-prefix-evidence', must_exist=False)
    require(not target.exists(), 'fresh_evidence_directory_required')
    target.mkdir(parents=True)
    errors, emitted = [], []
    total = 0
    def publish(name, content):
        nonlocal total
        require(len(emitted) + 1 < MAX_PUBLIC_FILES, 'public_file_count_exceeded')
        require(total + len(content) + execution.PUBLIC_RECEIPT_RESERVE <= MAX_PUBLIC_BYTES, 'public_evidence_size_exceeded')
        relative_file(target, name, must_exist=False).write_bytes(content)
        total += len(content)
        emitted.append(name)
    def publish_json(name, record):
        shared.check_public_tree(record)
        content = (json.dumps(record, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + '\n').encode('utf-8')
        require(len(content) <= shared.MAX_JSON_BYTES, 'oversize_json')
        publish(name, content)
    try:
        source = validate_source_archive_receipt(read_source_archive_receipt(
            ROOT / 'build/dependency-policy-prefix-source-archives.json'))
        publish_json('source-archives.json', source)
        if not source['passed']: errors.append('source_archive_preparation_failed')
    except Exception as exc:
        errors.append(code(exc, 'source_archive_receipt_missing_or_invalid'))
    try:
        setup = validate_dependency_setup(read_json(ROOT / 'build/dependency-policy-prefix-setup.json'))
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
    require(len(encoded) <= execution.PUBLIC_RECEIPT_RESERVE and total + len(encoded) <= MAX_PUBLIC_BYTES
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
            unlinked(args.ru_root)
        if args.action == 'generate':
            source_identity(ROOT, args.ru_root)
            result = generate(args.ru_root.resolve(), work_root() / 'generated')
            print(json.dumps({'schema': 1, 'generated': len(result['units']) == 4, 'native_execution': False}))
        elif args.action == 'prepare':
            require(args.mingw_root is not None, 'mingw_root_required')
            unlinked(args.mingw_root)
            result = prepare(args.ru_root.resolve(), args.mingw_root.resolve())
            print(json.dumps({'schema': 1, 'prepared': result['prepared']}))
        elif args.action == 'run':
            result = run_matrix()
            print(json.dumps({'schema': 1, 'complete': result['complete'], 'passed': result['passed']}))
            return 0 if result['passed'] else 1
        elif args.action == 'verify':
            result = verify_results(read_json(work_root() / 'results.json'), read_json(work_root() / 'prepare.json'))
            save_json(work_root() / 'verification.json', result)
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
