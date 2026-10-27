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
    'tests/bootstrap_pipeline/dll_abi_probe.ru',
    'tools/verify_bootstrap_product_windows.py', 'tools/package_bootstrap_preview.py',
    'tools/prepare_bootstrap_preview.py', 'packaging/bootstrap-preview-inputs.json',
    '.github/workflows/bootstrap-preview.yml', 'tests/test_bootstrap_preview.py', 'tools/verify_bootstrap_recent_policies.py'))
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
    """Require the old baseline plus an exact externally reviewed feature delta.

    The caller trusts the full app commit/tree AND this before/after manifest.
    The manifest is not an attestation: it must be frozen after review, never
    synthesized from a dirty build checkout to make an unexpected change pass.
    Omitting it preserves B11's original pipeline-only contract.
    """
    require(re.fullmatch('[0-9a-f]{40}', pin['commit']) is not None
            and re.fullmatch('[0-9a-f]{40}', pin['tree']) is not None, 'full app baseline pins required')
    require(git(root, 'rev-parse', pin['commit']+'^{tree}') == pin['tree'], 'app baseline tree mismatch')
    subprocess.run(['git', '-C', str(root), 'merge-base', '--is-ancestor', pin['commit'], 'HEAD'], check=True)
    names = git(root, 'ls-tree', '-rz', '--name-only', pin['commit']).split('\0')
    baseline = {name for name in names if name}
    require(baseline <= set(current), 'baseline app file deleted')
    reviewed = pin.get('reviewed_changes', {})
    require(isinstance(reviewed, dict), 'invalid reviewed feature manifest')
    for name, row in reviewed.items():
        require(isinstance(name, str) and name not in ADDITIONS, 'pipeline additions are separately reviewed')
        checked(root, name)
        require(isinstance(row, dict) and set(row) == {'before', 'after'}, 'invalid feature delta record')
        require(row['before'] is None or isinstance(row['before'], str)
                and re.fullmatch('[0-9a-f]{64}', row['before']), 'invalid previous feature hash')
        require(isinstance(row['after'], str) and re.fullmatch('[0-9a-f]{64}', row['after']), 'invalid new feature hash')
        require(row['before'] != row['after'], 'unchanged feature entry')
    actual = {}
    for name in sorted(baseline):
        content = subprocess.check_output(['git', '-C', str(root), 'show', pin['commit']+':'+name])
        before = hashlib.sha256(content).hexdigest()
        if before != current[name]:
            actual[name] = {'before': before, 'after': current[name]}
    for name in sorted(set(current)-baseline-ADDITIONS):
        actual[name] = {'before': None, 'after': current[name]}
    require(ADDITIONS <= set(current)-baseline, 'missing pipeline additions')
    require(actual == reviewed, 'app feature delta differs from reviewed before/after manifest')
    return {'commit': pin['commit'], 'tree': pin['tree'],
            'unchanged_files': len(baseline)-sum(name in baseline for name in actual),
            'reviewed_changes': reviewed,
            'pipeline_additions': {name: current[name] for name in sorted(ADDITIONS)}}


def identity(path):
    path = Path(path)
    require(path.is_file() and not any(p.is_symlink() for p in [path, *path.parents]), 'missing/linked file')
    return {'path': str(path.resolve()), 'sha256': sha(path), 'size': path.stat().st_size}


def bytes_digest(data):
    return hashlib.sha256(data).hexdigest()


def explicit_linker_flags(record):
    path = Path(record['path'])
    return ['-fuse-ld='+path.name, '-B'+str(path.parent)]


def parse_linker_trace(raw):
    """LLVM 14 Command::Print/printArg, not shell or Windows command parsing.

    -### quotes every argument and escapes only quote, backslash and dollar.
    This gate accepts only one pure-object link command, never response files.
    """
    if not isinstance(raw, bytes) or len(raw) > 1024 * 1024:
        raise ValueError('invalid or oversized linker trace')
    commands, header = [], []
    for line in raw.decode('utf-8', errors='strict').splitlines():
        line = line.strip()
        if not line.startswith('"'):
            if line:
                header.append(line)
            continue
        args = []
        while line:
            if not line.startswith('"'):
                raise ValueError('unquoted linker trace argument')
            value, pos = '', 1
            while pos < len(line) and line[pos] != '"':
                char = line[pos]
                if char == '\\':
                    pos += 1
                    if pos >= len(line) or line[pos] not in ('"', '\\', '$'):
                        raise ValueError('unknown linker trace escape')
                    char = line[pos]
                if ord(char) < 32 or ord(char) == 127:
                    raise ValueError('control character in linker trace')
                value += char
                pos += 1
            if pos >= len(line):
                raise ValueError('unterminated linker trace argument')
            if value.startswith('@'):
                raise ValueError('response files not supported by pinned linker gate')
            args.append(value)
            line = line[pos+1:]
            if line and not line.startswith(' '):
                raise ValueError('invalid linker trace argument boundary')
            line = line.lstrip(' ')
        commands.append(args)
    if (len(header) != 4 or not re.fullmatch(r'clang version 14\.[^\r\n]+', header[0])
            or not re.fullmatch(r'Target: x86_64-pc-windows-msvc(?:[0-9]+(?:\.[0-9]+)*)?', header[1])
            or header[2] not in ('Thread model: posix', 'Thread model: win32')
            or not header[3].startswith('InstalledDir: ') or not header[3][14:]):
        raise ValueError('unexpected clang14 dry-run diagnostics/header')
    if len(commands) != 1 or not commands[0] or not commands[0][0]:
        raise ValueError('expected exactly one pure-object linker command')
    return commands[0]


def inspect_linker_command(command, record, environment, cwd, expected_triple=None):
    command = list(map(str, command))
    flags = explicit_linker_flags(record)
    selectors = [arg for arg in command if arg.startswith(('-fuse-ld', '--ld-path', '-B'))]
    if selectors != flags or '-###' in command or any(arg.startswith('@') for arg in command):
        raise ValueError('conflicting or implicit linker selection')
    if identity(record['path']) != record:
        raise RuntimeError('linker input changed before dry run')
    probe = subprocess.run(command+['-###'], capture_output=True, env=environment,
                           cwd=cwd, timeout=120)
    if probe.returncode:
        raise RuntimeError('linker dry run failed: '+probe.stderr.decode('utf-8', errors='replace'))
    selected = parse_linker_trace(probe.stderr)
    if expected_triple is not None and ('Target: '+expected_triple) not in probe.stderr.decode('utf-8').splitlines():
        raise ValueError('linker dry-run target differs from compilation target')
    path = Path(selected[0])
    if (not path.is_absolute() or path.resolve() != Path(record['path'])
            or identity(path) != record):
        raise ValueError('clang selected a different linker; fallback forbidden: '+json.dumps(selected, ensure_ascii=False))
    if identity(record['path']) != record:
        raise RuntimeError('linker input changed during dry run')
    return {'schema': 'ru-pinned-linker-selection-v1', 'command': command,
            'dry_run_command': command+['-###'], 'selected_command': selected,
            'linker': record, 'cwd': str(Path(cwd).resolve()),
            'environment_sha256': bytes_digest(json.dumps(sorted(environment.items()), ensure_ascii=False).encode('utf-8')),
            'dry_run_stderr_utf8': probe.stderr.decode('utf-8', errors='strict'),
            'dry_run_stderr_sha256': bytes_digest(probe.stderr),
            'scope': 'driver dry-run selection; same argv/env/cwd execution and pre/post file identity; not OS process tracing or ABA protection'}


def verify_linker_selection(selection, tools, *, expected_command=None, triple=None):
    require(isinstance(selection, dict) and selection.get('schema') == 'ru-pinned-linker-selection-v1', 'missing linker selection evidence')
    record = identity(tools['linker'])
    command = selection.get('command')
    require(isinstance(command, list) and command and command[0] == tools['clang']
            and all(isinstance(arg, str) for arg in command), 'wrong linker driver argv')
    require(expected_command is None or command == expected_command, 'linker evidence bound to different command')
    require(selection.get('dry_run_command') == command+['-###'], 'dry-run argv differs from actual link')
    require([arg for arg in command if arg.startswith(('-fuse-ld', '--ld-path', '-B'))] == explicit_linker_flags(record)
            and '-###' not in command and not any(arg.startswith('@') for arg in command), 'linker selectors changed')
    try:
        raw = selection['dry_run_stderr_utf8'].encode('utf-8', errors='strict')
        selected = parse_linker_trace(raw)
    except (KeyError, TypeError, AttributeError, ValueError, UnicodeError):
        require(False, 'invalid linker dry-run bytes')
    require(selection.get('dry_run_stderr_sha256') == bytes_digest(raw)
            and selection.get('selected_command') == selected, 'linker trace bytes differ from selected argv')
    path = Path(selected[0])
    require(path.is_absolute() and path.resolve() == Path(record['path'])
            and identity(path) == record and selection.get('linker') == record, 'selected linker identity mismatch')
    require(triple is None or ('Target: '+triple) in raw.decode('utf-8').splitlines(), 'linker dry-run target mismatch')
    require(isinstance(selection.get('cwd'), str) and Path(selection['cwd']).is_absolute()
            and re.fullmatch('[0-9a-f]{64}', selection.get('environment_sha256','')) is not None, 'missing execution context')
    require(selection.get('scope') == 'driver dry-run selection; same argv/env/cwd execution and pre/post file identity; not OS process tracing or ABA protection', 'overstated linker identity scope')
    return selection


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
        require(actual.get('link_flags') == explicit_linker_flags(identity(tools['linker'])), 'host linker not explicitly pinned')
        require(proof.get('linker') == identity(tools['linker']), 'host linker identity missing or changed')
        selection = verify_linker_selection(proof.get('linker_selection'), tools, triple=triple)
        require(len(selection['command']) == 7 and selection['command'][1] == '--target='+triple
                and selection['command'][3] == '-o', 'host link was not explicitly targeted pure object to EXE')
        names = ('clang', 'llvm-as', 'llvm-link', 'opt', 'llvm-dis', 'llc')
        executables = proof.get('tool_executables')
        require(isinstance(executables, dict) and set(executables) == set(names),
                'exact native tool executable inventory required')
        host_inputs = proof.get('host_inputs')
        require(isinstance(host_inputs, list), 'missing host inputs')
        for name in names:
            record = executables[name]
            require(isinstance(record, dict) and type(record.get('size')) is int
                    and record == identity(tools[name]), 'native tool executable identity mismatch: ' + name)
            require(record['path'] in frozen and record['sha256'] == frozen[record['path']],
                    'native tool executable differs from frozen input: ' + name)
            require(sum(item == record for item in host_inputs) == 1,
                    'native tool executable missing or duplicated in host inputs: ' + name)
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
         '-o', str(stage/'ru_notepad.exe'), *explicit_linker_flags({'path': tools['linker']}), '-Xlinker', '/SUBSYSTEM:WINDOWS',
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


def verify_linker_probe(probe, tools, triple, directory):
    require(isinstance(probe, dict) and probe.get('exit_code') == 0
            and probe.get('scope') == 'fixed C toolchain probe only; not Ru frontend or GUI acceptance', 'missing fixed-C linker probe')
    paths = {key: directory/('link probe 汉😀$'+suffix) for key, suffix in
             [('source', '.c'), ('object', '.obj'), ('binary', '.exe')]}
    require(all(probe.get(key) == identity(path) for key, path in paths.items()), 'linker probe artifacts changed')
    require(paths['source'].read_bytes() == b'int main(void) { return 0; }\n', 'linker probe source changed')
    command = [tools['clang'], '--target='+triple, str(paths['object']), '-o', str(paths['binary']),
               *explicit_linker_flags(identity(tools['linker']))]
    verify_linker_selection(probe.get('linker_selection'), tools, expected_command=command, triple=triple)


def linker_preflight(tools, stage, triple, environment, run, linker_record):
    # Fixed C tests the toolchain, never processes application Ru source.
    source = stage/'link probe 汉😀$.c'
    obj, binary = source.with_suffix('.obj'), source.with_suffix('.exe')
    source.write_bytes(b'int main(void) { return 0; }\n')
    inputs = {'source': identity(source)}
    require(inputs['source']['sha256'] == bytes_digest(b'int main(void) { return 0; }\n'), 'fixed linker probe source differs')
    run([tools['clang'], '--target='+triple, '-c', str(source), '-o', str(obj)])
    require(identity(source) == inputs['source'], 'linker probe source changed during compilation')
    inputs['object'] = identity(obj)
    command = [tools['clang'], '--target='+triple, str(obj), '-o', str(binary),
               *explicit_linker_flags(linker_record)]
    selection = inspect_linker_command(command, linker_record, environment, str(stage), triple)
    run(command, cwd=stage)
    verify_linker_selection(selection, tools, expected_command=command, triple=triple)
    require(inputs == {key: identity(record['path']) for key, record in inputs.items()}, 'linker probe input changed during linking')
    before = {**inputs, 'binary': identity(binary)}
    run([str(binary)], cwd=stage, timeout=60)
    require(before == {key: identity(record['path']) for key, record in before.items()}, 'linker probe artifacts changed')
    return {**before, 'linker_selection': selection, 'exit_code': 0,
            'scope': 'fixed C toolchain probe only; not Ru frontend or GUI acceptance'}


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
    linker_record = identity(tools['linker'])
    require(linker_record['sha256'] == config['tool_sha256']['linker'], 'linker changed after tool validation')
    environment_spec = importlib.util.spec_from_file_location('_trusted_llvm_environment', ru/'rulang/toolchain_environment.py')
    environment_module = importlib.util.module_from_spec(environment_spec)
    environment_spec.loader.exec_module(environment_module)
    environment = environment_module.llvm_environment()
    require(not any(environment.get(k) for k in ('CL', '_CL_', 'LINK', '_LINK_')), 'ambient compiler/linker flag injection forbidden')
    commands = []
    def run(argv, **kwargs):
        argv = list(map(str, argv))
        commands.append(argv)
        return subprocess.run(argv, check=True, capture_output=True, text=True, encoding='utf-8', timeout=kwargs.pop('timeout', 600), env=environment, **kwargs).stdout
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
    linker_probe = linker_preflight(tools, staging, triple, environment, run, linker_record)
    verify_linker_probe(linker_probe, tools, triple, staging)
    diagnostic = {'schema': 'ru-notepad-linker-probe-diagnostic-v1',
                  'status': 'diagnostic-only-not-application-or-gui-acceptance',
                  'target_triple': triple, 'probe': linker_probe}
    with (staging/'linker-probe-diagnostic.json').open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(diagnostic, ensure_ascii=False, indent=2)+'\n')
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
    final_linker_selection = None
    plan = link_commands(tools, ir, wrapper, app, staging, triple)
    for index, command in enumerate(plan):
        require(sha(ir) == proof['standalone_ir_sha256'], 'IR changed before link step')
        if index == len(plan)-1:
            final_link_inputs = {p.name: identity(p) for p in (staging/'application.obj', staging/'launcher.obj', staging/'application.res')}
        if index == len(plan)-1:
            final_linker_selection = inspect_linker_command(command, linker_record, environment, str(app/'packaging'), triple)
        run(command, cwd=app/'packaging')
        if index == len(plan)-1:
            verify_linker_selection(final_linker_selection, tools, expected_command=command, triple=triple)
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
    verify_linker_probe(linker_probe, tools, triple, staging)
    receipt = {'schema': SCHEMA, 'status': 'built-not-runtime-accepted-not-publishable',
        'bootstrap': bootstrap, 'bootstrap_verification': identity(report),
        'toolchain_identity_scopes': {
            'bootstrap': 'existing M4 LLVM14/target/fixedpoint; bootstrap linker identity not recorded or locked',
            'application': 'explicit config-hash toolchain/linker',
        },
        'source_pins': {k: config[k] for k in ('ru_source', 'app_source')},
        'app_baseline': baseline, 'entry_source': entry,
        'source_sha256': sources, 'tool_paths': tools, 'tool_sha256': config['tool_sha256'], 'driver_inputs': local_inputs,
        'linker_probe': linker_probe, 'commands': commands, 'target_triple': triple, 'data_layout': layout,
        'sdk_crt_environment': {k: v for k, v in environment.items() if k.upper() in
            {'PATH', 'INCLUDE', 'LIB', 'LIBPATH', 'WINDOWSSDKDIR', 'WINDOWSSDKVERSION', 'VCTOOLSINSTALLDIR', 'VCTOOLSVERSION'}},
        'compile_proof_sha256': sha(proof_path), 'standalone_ir_sha256': sha(ir),
        'linked_inputs': final_link_inputs, 'final_linker_selection': final_linker_selection, 'host_python': identity(sys.executable),
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
