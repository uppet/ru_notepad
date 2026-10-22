#!/usr/bin/env python3
"""Isolated bootstrap+LLVM GUI build candidate. Never packages or publishes.

Use a reviewed config file with exact remote source pins and independently
acquired tool hashes. Requires Windows/LLVM14/MSVC SDK. Successful compilation
is NOT GUI/FFI acceptance: receipt explicitly retains mandatory runtime gates.
"""
import argparse
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import struct
import subprocess
import sys

from bootstrap_provenance import require, checked, sha, validate, validate_toolchain

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'ru-notepad-bootstrap-llvm-build-v1'
ADDITIONS = frozenset(('tools/bootstrap_provenance.py', 'tools/build_bootstrap_release.py',
    'packaging/bootstrap_gui_launcher.c', 'schema/build-config.schema.json',
    'tests/test_bootstrap_provenance.py', 'tests/test_bootstrap_release.py',
    'tools/prepare_bootstrap_dependencies.py', 'tools/verify_bootstrap_editor_windows.py',
    'tests/test_bootstrap_editor_windows.py', 'tests/bootstrap_pipeline/argv_probe.ru',
    'tests/bootstrap_pipeline/dll_abi_probe.ru'))
ENTRIES = ('src/main.ru', 'tests/bootstrap_pipeline/argv_probe.ru', 'tests/bootstrap_pipeline/dll_abi_probe.ru')


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True, encoding='utf-8').strip()


def snapshot(root, commit, tree):
    require(re.fullmatch('[0-9a-f]{40}', commit) is not None
            and re.fullmatch('[0-9a-f]{40}', tree) is not None, 'full remote source pins required')
    require(git(root, 'rev-parse', 'HEAD') == commit and git(root, 'rev-parse', 'HEAD^{tree}') == tree
            and not git(root, 'status', '--porcelain'), 'source pin mismatch or dirty checkout')
    return {name: sha(checked(root, name)) for name in git(root, 'ls-files', '-z').split('\0') if name}


def verify_app_baseline(root, pin, current):
    """Feature adds only reviewed pipeline files; every baseline byte survives."""
    require(re.fullmatch('[0-9a-f]{40}', pin['commit']) is not None
            and re.fullmatch('[0-9a-f]{40}', pin['tree']) is not None, 'full app baseline pins required')
    require(git(root, 'rev-parse', pin['commit']+'^{tree}') == pin['tree'], 'app baseline tree mismatch')
    subprocess.run(['git', '-C', str(root), 'merge-base', '--is-ancestor', pin['commit'], 'HEAD'], check=True)
    baseline = git(root, 'ls-tree', '-rz', '--name-only', pin['commit']).split('\0')
    baseline = {name for name in baseline if name}
    require(set(current)-baseline == ADDITIONS and baseline <= set(current), 'unexpected app feature delta')
    for name in sorted(baseline):
        content = subprocess.check_output(['git', '-C', str(root), 'show', pin['commit']+':'+name])
        require(hashlib.sha256(content).hexdigest() == current[name], 'baseline app input changed: '+name)
    return {'commit': pin['commit'], 'tree': pin['tree'], 'unchanged_files': len(baseline),
            'pipeline_additions': {name: current[name] for name in sorted(ADDITIONS)}}


def identity(path):
    path = Path(path)
    require(path.is_file() and not any(p.is_symlink() for p in [path, *path.parents]), 'missing/linked file')
    return {'path': str(path.resolve()), 'sha256': sha(path), 'size': path.stat().st_size}


def verify_proof(proof, *, source, compiler, ir, binary, triple, layout, frozen, tools=None):
    require(proof.get('schema') == 'ru-bootstrap-build-proof-v1'
            and proof.get('native_protocol') == 'bootstrap-native-v1', 'native bootstrap proof required')
    require(proof.get('source') == str(source.resolve()) and proof.get('compiler') == identity(compiler), 'source/compiler proof mismatch')
    require(proof.get('target_triple') == triple and proof.get('data_layout') == layout, 'proof target mismatch')
    require(str(compiler.resolve()) in frozen and sha(compiler) == frozen[str(compiler.resolve())], 'compiler differs from bootstrap')
    if tools is not None:
        actual = proof.get('toolchain', {})
        require(actual.get('clang') == [tools['clang']], 'host selected different clang or flags')
        require(actual.get('tools') == {k: tools[k] for k in ('llvm-as', 'llvm-link', 'opt', 'llvm-dis', 'llc')}, 'host selected different LLVM tools')
        require(actual.get('link_flags') == ['-fuse-ld='+tools['linker']], 'host linker not explicitly pinned')
        require(proof.get('linker') == identity(tools['linker']), 'host linker identity missing or changed')
    for key, file, digest_key in [('standalone_ir', ir, 'standalone_ir_sha256'), ('binary', binary, 'binary_sha256')]:
        require(proof.get('artifacts', {}).get(key) == {'path': str(file.resolve()), 'sha256': sha(file)}
                and proof.get(digest_key) == sha(file), 'proof artifact mismatch: ' + key)
    inventory = proof.get('source_inventory')
    dependencies = proof.get('dependencies')
    require(isinstance(inventory, list) and bool(inventory) and isinstance(dependencies, list)
            and bool(dependencies), 'missing source inventory/dependencies')
    paths = set()
    for record in inventory:
        name = record.get('path')
        require(name in frozen and name not in paths and record == identity(name)
                and record['sha256'] == frozen[name], 'source inventory mismatch')
        paths.add(name)
    require(str(source.resolve()) in paths, 'entry absent from source inventory')
    for record in dependencies:
        require(record.get('path') in paths and record == identity(record['path']), 'dependency absent or changed')
    require(isinstance(proof.get('host_inputs'), list) and bool(proof['host_inputs']), 'missing host inputs')
    for record in proof['host_inputs']:
        name = record.get('path')
        require(name in frozen and record == identity(name) and record['sha256'] == frozen[name], 'host input mismatch')


def link_commands(tools, ir, wrapper, app, stage, triple):
    return [
        [tools['llc'], '-filetype=obj', '-relocation-model=pic', str(ir), '-o', str(stage/'application.obj')],
        [tools['clang'], '--target='+triple, '-std=c99', '-O2', '-c', str(wrapper), '-I', str(app/'packaging'), '-o', str(stage/'launcher.obj')],
        [tools['resource-compiler'], '/nologo', '/fo', str(stage/'application.res'), str(app/'packaging/app.rc')],
        [tools['clang'], '--target='+triple, str(stage/'application.obj'), str(stage/'launcher.obj'), str(stage/'application.res'),
         '-o', str(stage/'ru_notepad.exe'), '-fuse-ld='+tools['linker'], '-Xlinker', '/SUBSYSTEM:WINDOWS',
         '-Xlinker', '/ENTRY:wWinMainCRTStartup', '-Xlinker', '/MACHINE:X64', '-lshell32', '-luser32']]


def verify_gui_pe(path):
    content = Path(path).read_bytes()
    require(len(content) >= 64 and content[:2] == b'MZ', 'final output is not PE')
    offset = struct.unpack_from('<I', content, 60)[0]
    require(offset + 94 <= len(content) and content[offset:offset+4] == b'PE\0\0', 'truncated/invalid final PE')
    require(struct.unpack_from('<H', content, offset+4)[0] == 0x8664
            and struct.unpack_from('<H', content, offset+24)[0] == 0x20b
            and struct.unpack_from('<H', content, offset+24+68)[0] == 2,
            'final PE must be Windows x64 PE32+ GUI subsystem')


def build(config, staging):
    require(sys.platform == 'win32' and platform.machine() in ('AMD64', 'x86_64'), 'Windows x64 build host required')
    require(config.get('schema') == 'ru-notepad-bootstrap-llvm-config-v1', 'unsupported build config')
    ru, app = (Path(config[key]['path']).resolve() for key in ('ru_source', 'app_source'))
    require(ROOT.resolve() == app, 'run the driver from the exact pinned app feature checkout')
    sources = {}
    for key, root in [('ru_source', ru), ('app_source', app)]:
        pin = config[key]
        sources[key] = snapshot(root, pin['commit'], pin['tree'])
    baseline = verify_app_baseline(app, config['app_baseline'], sources['app_source'])
    entry = config.get('entry_source', 'src/main.ru')
    require(entry in ENTRIES, 'unreviewed build entry')
    tools = {name: str(Path(path).resolve()) for name, path in config['tool_paths'].items()}
    validate_toolchain(tools, config['tool_sha256'])
    environment_spec = importlib.util.spec_from_file_location('_trusted_llvm_environment', ru/'rulang/toolchain_environment.py')
    environment_module = importlib.util.module_from_spec(environment_spec)
    environment_spec.loader.exec_module(environment_module)
    environment = environment_module.llvm_environment()
    require(not any(environment.get(k) for k in ('CL', '_CL_', 'LINK', '_LINK_')), 'ambient compiler/linker flag injection forbidden')
    commands = []
    def run(argv, **kwargs):
        argv = list(map(str, argv))
        commands.append(argv)
        return subprocess.run(argv, check=True, capture_output=True, text=True, encoding='utf-8', timeout=600, env=environment, **kwargs).stdout
    version = run([tools['clang'], '--version'])
    require(re.match(r'clang version 14\.', version) is not None, 'LLVM14 clang required')
    for name in ('llc', 'llvm-as', 'llvm-link', 'opt', 'llvm-dis'):
        require(re.search(r'LLVM version 14\.', run([tools[name], '--version'])) is not None, 'mixed LLVM tool versions')
    probe = run([tools['clang'], '-S', '-emit-llvm', '-x', 'c', '-', '-o', '-'], input='')
    triples = re.findall(r'^target triple = "([^"]+)"', probe, re.M)
    layouts = re.findall(r'^target datalayout = "([^"]+)"', probe, re.M)
    require(len(triples) == len(layouts) == 1 and re.fullmatch(r'x86_64-pc-windows-msvc(?:[0-9]+(?:\.[0-9]+)*)?', triples[0]) is not None, 'unsupported MSVC target')
    triple, layout = triples[0], layouts[0]
    spec = importlib.util.spec_from_file_location('_trusted_bootstrap_compare', ru/'tools/bootstrap_compare.py')
    comparator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(comparator)
    directory = Path(config['bootstrap_directory']).resolve()
    report = Path(config['verification']).resolve()
    bootstrap = validate(ru, directory, report, config['ru_source']['commit'], config['ru_source']['tree'],
                         comparator.compare_native, expected_triple=triple, expected_data_layout=layout)
    compiler = directory/'stage3.exe'
    source = checked(app, entry)
    wrapper = checked(ROOT, 'packaging/bootstrap_gui_launcher.c')
    local_inputs = {str(path): sha(path) for path in (wrapper, Path(__file__), ROOT/'tools/bootstrap_provenance.py')}
    require(not staging.exists(), 'staging must be a fresh private directory')
    require(not any(staging.resolve().is_relative_to(root) for root in (ru, app, directory)), 'staging cannot modify source/bootstrap trees')
    staging.mkdir(parents=True, exist_ok=False)
    # A failed build keeps diagnostics in its private directory but no success
    # receipt. Nothing here copies binaries into dist or invokes packaging.
    ir, intermediate, proof_path = staging/'application.ll', staging/'intermediate-console.exe', staging/'compile-proof.json'
    frozen = {str((root/name).resolve()): digest for key, root in [('ru_source', ru), ('app_source', app)]
              for name, digest in sources[key].items()}
    frozen[str(compiler.resolve())] = bootstrap['stage3_sha256']
    frozen.update({str(Path(path).resolve()): config['tool_sha256'][name] for name, path in tools.items()})
    run([sys.executable, '-I', '-B', ru/'tools/bootstrap.py', '--llvm-clang', tools['clang'], 'build', source,
         '--compiler', compiler, '--allow-native', '--source-root', app, '--proof', proof_path,
         '--linker', tools['linker'], '--emit-llvm', ir, '-o', intermediate], cwd=ru)
    proof_bytes = proof_path.read_bytes()
    proof = json.loads(proof_bytes)
    verify_proof(proof, source=source, compiler=compiler, ir=ir, binary=intermediate,
                 triple=triple, layout=layout, frozen=frozen, tools=tools)
    final_link_inputs = None
    plan = link_commands(tools, ir, wrapper, app, staging, triple)
    for index, command in enumerate(plan):
        require(sha(ir) == proof['standalone_ir_sha256'], 'IR changed before link step')
        if index == len(plan)-1:
            final_link_inputs = {p.name: identity(p) for p in (staging/'application.obj', staging/'launcher.obj', staging/'application.res')}
        run(command, cwd=app/'packaging')
    require(final_link_inputs == {name: identity(staging/name) for name in final_link_inputs}, 'link inputs changed during final link')
    for key, root in [('ru_source', ru), ('app_source', app)]:
        pin = config[key]
        require(snapshot(root, pin['commit'], pin['tree']) == sources[key], 'source changed during build')
    require(all(sha(Path(path)) == digest for path, digest in local_inputs.items()), 'driver/wrapper changed during build')
    validate_toolchain(tools, config['tool_sha256'])
    require(proof_path.read_bytes() == proof_bytes, 'proof changed during linking')
    require(sha(report) == bootstrap['verification_sha256'], 'bootstrap verification changed during build')
    verify_proof(proof, source=source, compiler=compiler, ir=ir, binary=intermediate,
                 triple=triple, layout=layout, frozen=frozen, tools=tools)
    verify_gui_pe(staging/'ru_notepad.exe')
    receipt = {'schema': SCHEMA, 'status': 'built-not-runtime-accepted-not-publishable',
        'bootstrap': bootstrap, 'bootstrap_verification': identity(report),
        'toolchain_identity_scopes': {
            'bootstrap': 'existing M4 LLVM14/target/fixedpoint; bootstrap linker identity not recorded or locked',
            'application': 'explicit config-hash toolchain/linker',
        },
        'source_pins': {k: config[k] for k in ('ru_source', 'app_source')},
        'app_baseline': baseline, 'entry_source': entry,
        'source_sha256': sources, 'tool_paths': tools, 'tool_sha256': config['tool_sha256'], 'driver_inputs': local_inputs,
        'commands': commands, 'target_triple': triple, 'data_layout': layout,
        'sdk_crt_environment': {k: v for k, v in environment.items() if k.upper() in
            {'PATH', 'INCLUDE', 'LIB', 'LIBPATH', 'WINDOWSSDKDIR', 'WINDOWSSDKVERSION', 'VCTOOLSINSTALLDIR', 'VCTOOLSVERSION'}},
        'compile_proof_sha256': sha(proof_path), 'standalone_ir_sha256': sha(ir),
        'linked_inputs': final_link_inputs, 'host_python': identity(sys.executable),
        'final_binary': identity(staging/'ru_notepad.exe'), 'native_acceptance': False,
        'required_gates': ['GUI CRT startup and diagnostics', 'UTF16/UTF8 argv edge cases',
            'icon/version/common-controls manifest', 'exact Scintilla/Lexilla/RuSyntax DLL identity and MSVC-host ABI callbacks',
            'full native editor acceptance bound to this final EXE and DLL snapshot'],
        'intermediate_console_publishable': False}
    pending = staging/'build-receipt.pending.json'
    pending.write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
    os.replace(pending, staging/'build-receipt.json')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--staging', type=Path, required=True)
    args = parser.parse_args()
    build(json.loads(args.config.read_text(encoding='utf-8')), args.staging.resolve())


if __name__ == '__main__':
    main()
