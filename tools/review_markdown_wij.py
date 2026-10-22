#!/usr/bin/env python3
"""Development-only Windows wij review. Never packages or releases a product."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
COMPILER = 'b8a0e2b6b4a71408d518ae04c77b9dcbc36b4ae5'
COMPILER_TREE = 'dceae0fc22b6d834e0aa1c49cde28ff3ddda373d'
BASE = 'd964ea9f7e27065aa5bbcced8d6c7526a6224dd1'
DLLS = ('Scintilla.dll', 'Lexilla.dll', 'RuSyntax.dll')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], timeout=30).decode().strip()


def tracked(root):
    paths = subprocess.check_output(['git', '-C', str(root), 'ls-files', '-z'], timeout=30)
    return {p: sha(root / p) for p in paths.decode().split('\0') if p}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def check_inputs(ru, expected):
    require(git(ROOT, 'rev-parse', 'HEAD') == expected, 'application commit mismatch')
    require(not git(ROOT, 'status', '--porcelain', '--untracked-files=no'), 'application modified')
    require(git(ru, 'rev-parse', 'HEAD') == COMPILER, 'development compiler commit mismatch')
    require(git(ru, 'rev-parse', 'HEAD^{tree}') == COMPILER_TREE, 'development compiler tree mismatch')
    require(not git(ru, 'status', '--porcelain', '--untracked-files=no'), 'development compiler modified')
    syntax = (ROOT / 'src/markdown_syntax.ru').read_text(encoding='utf-8')
    for name in ('_密扫描策略', '_增量策略'):
        require(syntax.count(name + " 取 {'enabled':假}.") == 1, 'default experiment flag changed')
    gate = subprocess.check_output(['git', '-C', str(ROOT), 'show', BASE + ':tools/windows_ci.py'], timeout=30)
    require(gate == (ROOT / 'tools/windows_ci.py').read_bytes(), 'original 30-second GUI gate changed')


def native_child(ru, runtime, output, ordinary=False):
    # Import the exact pinned helper, changing only its outer functional timeout.
    # LLVM subprocesses keep their original individual 120-second deadlines.
    script = ru / 'experiments/notepad_undo/check_incremental_native.py'
    spec = importlib.util.spec_from_file_location('wij_native_review', script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if ordinary:
        activation = "(折 其 _密扫描策略) 其 增 'enabled' 真."
        require(module.SOURCE.count(activation) == 1, 'native dense activation contract changed')
        module.SOURCE = module.SOURCE.replace(activation, activation.replace('真.', '假.'))
    calls = []
    def bounded_run(command, **kwargs):
        require(command == [str(output / 'program.exe')], 'unexpected native helper command')
        require(kwargs.get('timeout') == 180, 'pinned native helper timeout contract changed')
        kwargs['timeout'] = 120  # New stricter functional limit, NOT the GUI performance gate.
        calls.append(120)
        return subprocess.run(command, **kwargs)
    module.subprocess = types.SimpleNamespace(run=bounded_run)
    sys.argv = [str(script), '--app-root', str(ROOT), '--runtime', str(runtime), '--output', str(output)]
    module.main()
    require(calls == [120], 'native functional timeout not exercised')
    result = json.loads((output / 'result.json').read_text())
    require(result.get('passed') is True and result.get('gc_live_zero') is True, 'native result failed')
    require(result.get('stdout') == 'NATIVE_ALL_FOLDS 42\nINCREMENTAL_NATIVE_PASS\n', 'native case inventory changed')


def bounded_tail(path, limit=4096):
    """Only a failed stage's own synthetic-build log; never search user logs."""
    with path.open('rb') as stream:
        stream.seek(max(0, path.stat().st_size - limit))
        return stream.read(limit).decode('utf-8', errors='replace')


def collect_evidence(out, evidence):
    paths = {
        'dense-policy': 'dense-policy/result.json', 'native-on-off': 'native-on-off/result.json',
        'native-ordinary-on-off': 'native-ordinary-on-off/result.json',
        'ordinary-benchmark': 'ordinary-benchmark/summary.json', 'ordinary-runs': 'ordinary-benchmark/runs.json',
        'benchmark': 'benchmark/summary.json', 'dense-runs': 'benchmark/runs.json',
        'build-pair': 'benchmark/build-pair-proof.json', 'control-build': 'control/experiment-build.json',
        'incremental-build': 'incremental/experiment-build.json',
        'native-source-build': 'native-helper/RuSyntax.native-build.json',
        'source-archives': 'archive-receipt.json',
    }
    # An original fail-fast dense run can have a failed per-run result absent
    # from runs.json. Preserve it without restarting or completing its samples.
    for group in ('benchmark', 'ordinary-benchmark'):
        for arm in ('control', 'incremental'):
            for sample in (1, 2, 3):
                name = f'{group}-{arm}-{sample}'
                paths[name] = f'{group}/{arm}-{sample}/result.json'
    selected = [(name, out / relative) for name, relative in paths.items() if (out / relative).is_file()]
    require(all(not p.is_symlink() and p.stat().st_size <= 16 * 1024 * 1024 for _, p in selected),
            'development JSON exceeds per-file upload bound or is linked')
    require(sum(p.stat().st_size for _, p in selected) <= 32 * 1024 * 1024,
            'development JSON exceeds total upload bound')
    for name, path in selected:
        shutil.copyfile(path, evidence / (name + '.json'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ru-root', required=True, type=Path)
    parser.add_argument('--msys-root', type=Path)
    parser.add_argument('--expected-source')
    parser.add_argument('--native-child', action='store_true')
    parser.add_argument('--ordinary', action='store_true')
    parser.add_argument('--runtime', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    require(sys.platform == 'win32', 'actual Windows required')
    ru = args.ru_root.resolve()
    if args.native_child:
        native_child(ru, args.runtime.resolve(), args.output.resolve(), args.ordinary)
        return
    require(args.expected_source and args.msys_root, 'expected source and MSYS root required')
    check_inputs(ru, args.expected_source)
    source, compiler = tracked(ROOT), tracked(ru)
    out = ROOT / 'build/wij-development'
    out.mkdir(parents=True, exist_ok=False)
    evidence = out / 'evidence'; evidence.mkdir()
    receipt = {'schema': 1, 'passed': False, 'development_only': True,
               'bootstrap': False, 'full_product_acceptance': False, 'default_flags': False,
               'source_commit': args.expected_source, 'compiler_commit': COMPILER,
               'compiler_tree': COMPILER_TREE, 'source_sha256': source,
               'compiler_source_sha256': compiler, 'native_functional_timeout_seconds': 120,
               'original_gui_performance_timeout_seconds': 30, 'commands': []}
    def save():
        (evidence / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    def run(label, command, timeout=600):
        record = {'stage': label, 'timeout_seconds': timeout, 'passed': False}
        receipt['commands'].append(record); save()
        # Separate private logs from the bounded JSON uploaded by the workflow.
        path = out / (label + '.log')
        try:
            with path.open('wb') as log:
                process = subprocess.Popen(list(map(str, command)), stdout=log, stderr=subprocess.STDOUT)
                try:
                    process.wait(timeout=timeout)
                except BaseException:
                    subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15, check=True)
                    process.wait(timeout=5)
                    raise
            record['exit_code'] = process.returncode
            require(process.returncode == 0, 'development stage failed: ' + label)
            record['passed'] = True
        finally:
            if path.is_file():
                record['log_sha256'] = sha(path)
                record['log_bytes'] = path.stat().st_size
                if not record['passed']:
                    record['diagnostic_tail_limit_bytes'] = 4096
                    record['diagnostic_tail'] = bounded_tail(path)
            save()
    try:
        bin_dir = args.msys_root.resolve() / 'mingw64/bin'
        os.environ['PATH'] = str(bin_dir) + os.pathsep + os.environ['PATH']
        cc, cxx, windres, ar, ranlib = [bin_dir / (name + '.exe') for name in ('gcc', 'g++', 'windres', 'ar', 'ranlib')]
        for tool in (cc, cxx, windres, ar, ranlib):
            require(tool.is_file(), 'missing MinGW tool')
        run('archives', [sys.executable, ROOT / 'tools/prepare_source_archives.py', '--root', ROOT,
                         '--receipt', out / 'archive-receipt.json'], 120)
        common = ['CXX=' + str(cxx), 'WINDRES=' + str(windres), 'AR=' + str(ar), 'RANLIB=' + str(ranlib)]
        run('scintilla', [bin_dir / 'mingw32-make.exe', '-j2', '-C', ROOT / 'vendor/scintilla/win32', '../bin/Scintilla.dll', *common])
        run('lexilla', [bin_dir / 'mingw32-make.exe', '-j2', '-C', ROOT / 'vendor/lexilla/src', '../bin/lexilla.dll',
                        'windir=C:/Windows', *common, 'LDFLAGS=-shared -static -mwindows -Wl,--kill-at -s'])
        sys.path.insert(0, str(ROOT / 'tools'))
        import build
        runtime = out / 'runtime'; runtime.mkdir()
        build.build_native_helpers(str(cc), out)
        shutil.copyfile(ROOT / 'vendor/scintilla/bin/Scintilla.dll', runtime / 'Scintilla.dll')
        shutil.copyfile(ROOT / 'vendor/lexilla/bin/lexilla.dll', runtime / 'Lexilla.dll')
        shutil.copyfile(out / 'native-helper/RuSyntax.dll', runtime / 'RuSyntax.dll')
        dlls = {name: sha(runtime / name) for name in DLLS}
        # Minimal test dependency receipt consumed by the pinned experimental builder.
        # Not a product BUILD.json and never packaged or uploaded as a runtime.
        (runtime / 'BUILD.json').write_text(json.dumps({'development_only': True,
            'binaries': {n: {'sha256': h} for n, h in dlls.items()},
            'source': {'tracked_source_sha256': {n: h for n, h in source.items() if n.startswith('native/')}}}) + '\n')
        receipt['dll_sha256'] = dlls
        sys.path.insert(0, str(ru))
        from rulang.llvm_toolchain import LLVMToolchain
        llvm = LLVMToolchain()
        receipt['llvm'] = {'version': llvm.version, 'triple': llvm.triple,
                           'tools_sha256': {n: sha(p) for n, p in llvm.tools.items()}, 'clang_sha256': sha(llvm.clang[0])}
        save()
        scripts = ru / 'experiments/notepad_undo'
        run('dense-policy', [sys.executable, scripts / 'check_policy.py', '--app-root', ROOT,
                            '--output', out / 'dense-policy', '--target', 'c-llvm'])
        run('native-on-off', [sys.executable, Path(__file__), '--native-child', '--ru-root', ru,
                             '--runtime', runtime, '--output', out / 'native-on-off'])
        run('native-ordinary-on-off', [sys.executable, Path(__file__), '--native-child', '--ordinary', '--ru-root', ru,
                                      '--runtime', runtime, '--output', out / 'native-ordinary-on-off'])
        for arm in ('control', 'incremental', 'ordinary-control', 'ordinary-incremental'):
            command = [sys.executable, scripts / 'build.py', '--app-root', ROOT, '--runtime', runtime,
                       '--output', out / arm, '--arm', 'ordinary' if arm.startswith('ordinary-') else 'dense', '--target', 'c-llvm', '--gcc', cc, '--windres', windres]
            if arm.endswith('incremental'): command.append('--incremental')
            run('build-' + arm, command)
        run('ordinary-original-gate', [sys.executable, ROOT / 'tools/review_markdown_ordinary_pair.py',
            '--app-root', ROOT, '--ru-root', ru, '--control', out / 'ordinary-control',
            '--incremental', out / 'ordinary-incremental', '--output', out / 'ordinary-benchmark'], 3600)
        run('benchmark-original-gate', [sys.executable, scripts / 'benchmark_incremental.py', '--app-root', ROOT,
            '--control', out / 'control', '--incremental', out / 'incremental', '--output', out / 'benchmark'], 3600)
        check_inputs(ru, args.expected_source)
        require(source == tracked(ROOT) and compiler == tracked(ru), 'source changed during review')
        require(dlls == {n: sha(runtime / n) for n in DLLS}, 'runtime dependencies changed')
        # The pinned historical runner writes remote_ci_executed:false. Do not
        # rewrite its raw evidence; this wrapper records the real current context.
        receipt['remote_ci_executed'] = os.environ.get('GITHUB_ACTIONS') == 'true'
        receipt['passed'] = True
    except BaseException as error:
        receipt['failure_type'] = type(error).__name__
        receipt['failure_summary'] = str(error)[-4096:]
        raise
    finally:
        # Preserve completed and failed bounded synthetic results, never executables,
        # generated code or unrestricted child logs. Failure is not a pass receipt.
        collect_evidence(out, evidence)
        save()
    print('WIJ_DEVELOPMENT_PASS')


if __name__ == '__main__':
    main()
