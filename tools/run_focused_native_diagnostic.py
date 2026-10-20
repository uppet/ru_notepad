#!/usr/bin/env python3
"""Fresh real-Windows 114/1417 diagnostic only; no product acceptance or ZIP.

Build/execute only the two unchanged full fixtures. Raw commands, build receipts,
fixture paths and child streams remain private. Reuse production build parameters,
PE/helper/source validators and native console runner; this subset is deliberately
not a call to the full product acceptance validator.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build
import package
import prepare_source_archives as archives
import windows_ci as ci
from guard_focused_native_diagnostic import validate_environment

ROOT = Path(__file__).resolve().parents[1]
TESTS = ('markdown_direct_native', 'app_i18n_native')
COUNTS = (114, 1417)
RU_COMMIT = '85c7821fda35aa79deeaf67b4d430f24ddd7f07f'
RU_TREE = 'a770e367e84d87a0d2fcb6d49ea6f06da2dbe4ba'
PUBLIC_LIMIT = 16384
DRIVERS = ('tools/build.py', 'tools/package.py', 'tools/windows_ci.py',
           'tools/check_native_arguments.py', 'tools/prepare_source_archives.py',
           'tools/run_focused_native_diagnostic.py', 'tools/guard_focused_native_diagnostic.py',
           'tools/test_focused_native_diagnostic.py', 'tools/test_window_size_workflow.py',
           '.github/workflows/windows.yml')
RECEIPT_KEYS = set('schema utc ru_commit ru_tree app_version scintilla_version scintilla_archive_sha256 '
    'lexilla_version lexilla_archive_sha256 entry_source entry_sha256 source_sha256 build_input_sha256 '
    'translation_unit_sha256 translation_unit_bytes exe_sha256 exe_bytes dll_sha256 lexilla_dll_sha256 '
    'native_helper_sha256 native_helper_build_key generated_c_sha256 generated_c_bytes seconds '
    'runtime_tested compiler_command'.split())


def require(condition):
    if not condition:
        raise ValueError('Rejected focused diagnostic evidence')


def integer(value, low=0, high=2**53 - 1):
    require(type(value) is int and low <= value <= high)


def exact(value, keys):
    require(type(value) is dict and set(value) == set(keys.split()))


def digest(value, length=64):
    require(type(value) is str and re.fullmatch('[0-9a-f]{' + str(length) + '}', value) is not None)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def sha(path):
    return package.sha(package.checked_file(path))


def bounded(path, limit=ci.MAX_LOG_BYTES):
    package.checked_file(path)
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    require(len(raw) <= limit)
    return raw


def json_read(path):
    return json.loads(bounded(path).decode('utf-8'))


def source_snapshot():
    return build.source_snapshot() | {p: sha(package.source_file(ROOT, p))
        for p in (*package.RESOURCE_INPUTS, *DRIVERS)}


def safe_directory(path):
    for parent in (path, *path.parents):
        info = parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode)
                and not getattr(info, 'st_file_attributes', 0) & 0x400)


def compiler_identity(ru, cc):
    require(build.git(ru, 'rev-parse', 'HEAD') == RU_COMMIT)
    require(build.git(ru, 'rev-parse', 'HEAD^{tree}') == RU_TREE)
    require(build.git(ru, 'status', '--porcelain') == '')
    native = package.source_file(ru, 'rulang/native_c.py')
    require(native.read_text(encoding='utf-8').count('if self._steps > 200000:') == 1)
    version = subprocess.check_output([str(cc), '--version'], timeout=30, stderr=subprocess.PIPE)
    return {'commit': RU_COMMIT, 'tree': RU_TREE, 'native_c_sha256': sha(native),
            'cc_sha256': sha(cc), 'cc_version_sha256': hashlib.sha256(version).hexdigest(),
            'analysis_limit': 200000}


def verify_dependencies():
    package.validate_dependency_sources(ROOT)
    for spec in archives.ARCHIVES:
        archive = ROOT / 'vendor/downloads' / spec.filename
        require(archive.stat().st_size == spec.bytes and sha(archive) == spec.sha256)
        with zipfile.ZipFile(archive) as source:
            for member in source.infolist():
                if not member.is_dir():
                    require(package.source_file(ROOT / 'vendor', member.filename).read_bytes() == source.read(member))


def build_command(ru, binpath, name, output):
    require(name in TESTS)
    return [sys.executable, ROOT / 'tools/build.py', '--ru-root', ru,
            '--cc', binpath / 'gcc.exe', '--cxx', binpath / 'g++.exe',
            '--windres', binpath / 'windres.exe', '--ar', binpath / 'ar.exe',
            '--ranlib', binpath / 'ranlib.exe', '--skip-scintilla', '--skip-lexilla',
            '--console', '--source', ROOT / 'tests' / (name + '.ru'), '--output', output]


def verify_receipts(binary, objdump, cc, compiler, sources):
    """Complete explicit subset checks, using existing package primitives.

    No synthetic product receipt, inventory mutation, or full-acceptance claim.
    Production package.py/build.py/windows_ci.py remain unchanged.
    """
    names = (*(name + '.exe' for name in TESTS), *package.DEPENDENCIES, *package.NATIVE_COMPILE_SOURCES)
    require({p.name for p in binary.glob('*.exe')} == {name + '.exe' for name in TESTS})
    pe = {name: package.inspect_pe(binary / name, objdump) for name in names}
    helpers = package.validate_native_helper_receipts(ROOT, binary, pe)
    for name, helper in helpers.items():
        native = json_read(binary / (Path(name).stem + '.native-build.json'))
        expected_inputs = build.native_build_inputs(str(cc), name)
        require(type(native.get('schema')) is int and native['schema'] == 1
                and native.get('build_inputs') == expected_inputs)
        require(native.get('compiler_command') == [expected_inputs['compiler_path'], *package.NATIVE_CFLAGS,
            *package.NATIVE_COMPILE_SOURCES[name], '-o',
            str(ROOT / 'build/native-helper' / (Path(name).stem + '.pending.dll')),
            *('-l' + library for library in package.NATIVE_LINK_LIBRARIES)])
        require(helper['compiler_sha256'] == compiler['cc_sha256']
                and helper['compiler_version_sha256'] == compiler['cc_version_sha256'])
    helper = helpers[package.NATIVE_HELPER_NAME]
    snapshot = build.source_snapshot()
    require(all(sources.get(k) == v for k, v in snapshot.items()))
    resources = {p: sha(package.source_file(ROOT, p)) for p in build.build_input_paths(True)}
    results = []
    for name in TESTS:
        receipt_path = binary / (name + '.build.json')
        r = json_read(receipt_path)
        require(set(r) == RECEIPT_KEYS and type(r['schema']) is int and r['schema'] == 1)
        require(r['ru_commit'] == RU_COMMIT and r['ru_tree'] == RU_TREE)
        require(r['source_sha256'] == snapshot and r['build_input_sha256'] == resources)
        require(r['app_version'] == (ROOT / 'VERSION').read_text(encoding='utf-8').strip())
        require(r['entry_source'] == 'tests/' + name + '.ru'
                and r['entry_sha256'] == sha(package.source_file(ROOT, r['entry_source'])))
        require(r['runtime_tested'] is False and type(r['seconds']) in (int, float)
                and math.isfinite(r['seconds']) and r['seconds'] >= 0)
        require(type(r['utc']) is str and re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', r['utc']))
        emitted = ROOT / 'build' / (name + '.c')
        for prefix, path in (('exe', binary / (name + '.exe')),
                             ('generated_c', emitted), ('translation_unit', emitted)):
            require(r[prefix + '_sha256'] == sha(path))
            integer(r[prefix + '_bytes'], 1)
            require(r[prefix + '_bytes'] == path.stat().st_size)
        require(r['exe_sha256'] == pe[name + '.exe']['sha256'])
        require(r['native_helper_sha256'] == helper['dll_sha256']
                and r['native_helper_build_key'] == helper['build_key'])
        for dll, dependency in package.DEPENDENCIES.items():
            prefix = dependency['folder']
            field = 'dll_sha256' if dll == 'Scintilla.dll' else 'lexilla_dll_sha256'
            require(r[field] == pe[dll]['sha256'] and r[prefix + '_version'] == dependency['version']
                    and r[prefix + '_archive_sha256'] == dependency['sha256'])
        command = [str(cc), '-std=c99', '-O2', '-Wall', '-Wextra', '-Wno-unused-function',
                   '-static-libgcc', str(emitted), '-o', str(binary / (name + '.exe')),
                   '-lm', str(ROOT / 'build/app-resource.o')]
        require(r['compiler_command'] == command)
        results.append({key: r[key] for key in ('entry_sha256', 'generated_c_sha256',
            'translation_unit_sha256', 'exe_sha256', 'exe_bytes', 'generated_c_bytes', 'translation_unit_bytes')}
            | {'receipt_sha256': sha(receipt_path)})
    return results, {name: record['sha256'] for name, record in pe.items()}, helpers


def validated_result(name, result, logs):
    index = TESTS.index(name)
    require(result.get('name') == name and result.get('passed') is True
            and result.get('executed') is True and result.get('cleanup_killed') is False
            and type(result.get('exit_code')) is int and result['exit_code'] == 0
            and result.get('skips') == [] and result.get('assertions_passed') == COUNTS[index])
    out = bounded(logs / (name + '.stdout.log')).decode('utf-8')
    err = bounded(logs / (name + '.stderr.log')).decode('utf-8')
    # Recheck the actual private streams before publishing, never just a receipt.
    require(len(re.findall(r'^PASS:', out, re.M)) == COUNTS[index])
    require(re.findall(r'^TOTAL PASS: ([0-9]+)\s*$', out, re.M) == [str(COUNTS[index])])
    require('FAIL:' not in out + err and not re.search(r'^SKIP:', out + err, re.M))
    record = {'id': index + 1, 'assertions': COUNTS[index], 'exit_code': 0,
              'executed': 1, 'cleanup_killed': 0}
    if index == 0:
        gc = ci.parse_markdown_direct_gc(err)
        metrics = ci.parse_markdown_route_metrics(out)
        require(result.get('gc_stress') == gc and result.get('bulk_route_metrics') == metrics)
        record['gc'] = gc | {'stats_enabled': 1}
        record['routes'] = [{k: v for k, v in m.items() if k != 'route'} | {'route': i}
                            for i, m in enumerate(metrics)]
    else:
        require(err == '' and 'FOLD_METRICS' not in out and 'gc_stress' not in result
                and 'bulk_route_metrics' not in result)
    return record


def validate_report(report):
    exact(report, 'schema diagnostic_only product_acceptance windows_executed source_commit source_tree '
          'source_sha256 compiler archives runtime tests')
    for key in ('schema', 'diagnostic_only', 'windows_executed'):
        integer(report[key], 1, 1)
    integer(report['product_acceptance'], 0, 0)
    for key in ('source_commit', 'source_tree'):
        digest(report[key], 40)
    digest(report['source_sha256'])
    compiler = report['compiler']
    exact(compiler, 'commit tree native_c_sha256 cc_sha256 cc_version_sha256 analysis_limit')
    require(compiler['commit'] == RU_COMMIT and compiler['tree'] == RU_TREE)
    integer(compiler['analysis_limit'], 200000, 200000)
    for key in ('native_c_sha256', 'cc_sha256', 'cc_version_sha256'):
        digest(compiler[key])
    require(report['archives'] == {spec.id: spec.sha256 for spec in archives.ARCHIVES})
    exact(report['runtime'], 'scintilla lexilla helper wrong_abi helper_build_key wrong_abi_build_key')
    for value in report['runtime'].values():
        digest(value)
    require(type(report['tests']) is list and len(report['tests']) == 2)
    for i, row in enumerate(report['tests']):
        exact(row, 'id assertions exit_code executed cleanup_killed entry_sha256 generated_c_sha256 '
              'translation_unit_sha256 exe_sha256 exe_bytes generated_c_bytes translation_unit_bytes receipt_sha256'
              + (' gc routes' if i == 0 else ''))
        for key, value in (('id', i + 1), ('assertions', COUNTS[i]), ('exit_code', 0),
                           ('executed', 1), ('cleanup_killed', 0)):
            integer(row[key], value, value)
        for key in ('entry_sha256', 'generated_c_sha256', 'translation_unit_sha256', 'exe_sha256', 'receipt_sha256'):
            digest(row[key])
        for key in ('exe_bytes', 'generated_c_bytes', 'translation_unit_bytes'):
            integer(row[key], 1)
        require(row['generated_c_sha256'] == row['translation_unit_sha256']
                and row['generated_c_bytes'] == row['translation_unit_bytes'])
        if i == 0:
            exact(row['gc'], 'threshold stats_enabled live freed collections')
            integer(row['gc']['stats_enabled'], 1, 1)
            ci.validate_markdown_direct_gc(row['gc'] | {'stats_enabled': True})
            require(type(row['routes']) is list and len(row['routes']) == 3)
            metrics = []
            for j, route in enumerate(row['routes']):
                integer(route.get('route'), j, j)
                metrics.append(route | {'route': ci.FOLD_ROUTE_ORDER[j]})
            ci.validate_markdown_route_metrics(metrics)
    require(len(canonical(report)) < PUBLIC_LIMIT)


def publish_report(private, public, report):
    validate_report(report)
    safe_directory(private)
    require(private.parent == public.parent)
    safe_directory(public.parent)
    require(not public.exists() and not public.is_symlink())
    payload = canonical(report) + b'\n'
    temporary = private / 'measurements.validated.json'
    with temporary.open('xb') as stream:
        require(stream.write(payload) == len(payload))
        stream.flush()
        os.fsync(stream.fileno())
    require(bounded(temporary, PUBLIC_LIMIT) == payload)
    public.mkdir(exist_ok=False)
    final = public / 'measurements.json'
    os.link(temporary, final)  # Atomic no-replace; never rename over prior output.
    try:
        safe_directory(public)
        first, second = temporary.stat(), final.lstat()
        require(stat.S_ISREG(second.st_mode) and not stat.S_ISLNK(second.st_mode)
                and (first.st_dev, first.st_ino) == (second.st_dev, second.st_ino)
                and first.st_size == second.st_size == len(payload)
                and bounded(final, PUBLIC_LIMIT) == payload)
    except Exception:
        if final.exists() and not final.is_symlink() and os.path.samefile(temporary, final):
            final.unlink()
        raise


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError('Rejected diagnostic arguments')


def main():
    stage, counts = 1, [0, 0]
    try:
        validate_environment()
        parser = Parser(add_help=False)
        parser.add_argument('--ru-root', type=Path, required=True)
        parser.add_argument('--msys-root', type=Path, required=True)
        args = parser.parse_args()
        stage = 2
        require(os.name == 'nt')
        api = ci.Windows()  # Explicitly rejects Wine.
        stage = 3
        private = ROOT / 'build/focused-native-private'
        public = ROOT / 'build/focused-native-public'
        require(not public.exists() and not public.is_symlink())
        private.mkdir(parents=True, exist_ok=False)
        safe_directory(private)
        for relative in ('build/native-helper', 'build/app-resource.o', 'vendor/scintilla', 'vendor/lexilla',
                         *(f'build/{name}.c' for name in TESTS)):
            path = ROOT / relative
            require(not path.exists() and not path.is_symlink())
        binary = private / 'bin'; binary.mkdir()
        logs = private / 'logs'; logs.mkdir()
        ru = args.ru_root.resolve(strict=True)
        binpath = args.msys_root.resolve(strict=True) / 'mingw64/bin'
        for name in ('gcc.exe', 'g++.exe', 'windres.exe', 'ar.exe', 'ranlib.exe', 'objdump.exe', 'mingw32-make.exe'):
            package.checked_file(binpath / name)
        env = dict(os.environ, PATH=str(binpath) + os.pathsep + os.environ.get('PATH', ''),
                   PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1', PYTHONOPTIMIZE='0')
        # Never inherit GC overrides into the i18n fixture or compiler.
        for key in ('RU_GC_THRESHOLD', 'RU_GC_STATS'):
            env.pop(key, None)
            os.environ.pop(key, None)
        os.environ['PATH'] = env['PATH']

        def run(tag, command, timeout=900):
            with (logs / (tag + '.stdout.log')).open('xb') as out, (logs / (tag + '.stderr.log')).open('xb') as err:
                result = subprocess.run(list(map(str, command)), cwd=ROOT, env=env,
                                        stdout=out, stderr=err, timeout=timeout, check=False)
            require(result.returncode == 0)

        stage = 4
        compiler = compiler_identity(ru, binpath / 'gcc.exe')
        commit, tree = build.git(ROOT, 'rev-parse', 'HEAD'), build.git(ROOT, 'rev-parse', 'HEAD^{tree}')
        require(commit == os.environ['GITHUB_SHA'] and build.git(ROOT, 'status', '--porcelain') == '')
        before = source_snapshot()
        stage = 5
        run('archives', [sys.executable, '-I', ROOT / 'tools/prepare_source_archives.py',
                        '--root', ROOT, '--receipt', private / 'source-archives.json'])
        require(json_read(private / 'source-archives.json')['passed'] is True)
        for spec in archives.ARCHIVES:
            archive = ROOT / 'vendor/downloads' / spec.filename
            require(archive.stat().st_size == spec.bytes and sha(archive) == spec.sha256)
            with zipfile.ZipFile(archive) as zipped:
                zipped.extractall(ROOT / 'vendor')  # Exact bytes admitted by the existing offline validator.
        stage = 6
        common = ['CXX=g++.exe', 'WINDRES=windres.exe', 'AR=ar.exe', 'RANLIB=ranlib.exe']
        make = binpath / 'mingw32-make.exe'
        run('scintilla', [make, '-j2', '-C', ROOT / 'vendor/scintilla/win32', '../bin/Scintilla.dll', *common])
        run('lexilla', [make, '-j2', '-C', ROOT / 'vendor/lexilla/src', '../bin/lexilla.dll',
                       *common, 'windir=C:/Windows', 'LDFLAGS=-shared -static -mwindows -Wl,--kill-at -s'])
        stage = 7
        for name in TESTS:
            run('build-' + name, build_command(ru, binpath, name, binary / (name + '.exe')))
        stage = 8
        verify_dependencies()
        receipts, binaries, helpers = verify_receipts(binary, binpath / 'objdump.exe', binpath / 'gcc.exe', compiler, before)
        results = []
        with tempfile.TemporaryDirectory(prefix='七语-原生-診断-', dir=private) as fixtures:
            for i, name in enumerate(TESTS):
                stage = 9 + i
                result = ci.run_native_console(api, name, dict(ci.NATIVE_CONSOLE_TESTS)[name], binary, Path(fixtures), logs)
                # This raw receipt may include paths/error strings and is NEVER public.
                (private / (name + '.result.json')).write_bytes(canonical(result) + b'\n')
                count = result.get('assertions_passed', 0)
                counts[i] = count if type(count) is int and 0 <= count <= 2**53 - 1 else 0
                results.append(validated_result(name, result, logs) | receipts[i])
        stage = 11
        require(source_snapshot() == before and compiler_identity(ru, binpath / 'gcc.exe') == compiler)
        require(build.git(ROOT, 'rev-parse', 'HEAD') == commit and build.git(ROOT, 'status', '--porcelain') == '')
        verify_dependencies()
        require(verify_receipts(binary, binpath / 'objdump.exe', binpath / 'gcc.exe', compiler, before)
                == (receipts, binaries, helpers))
        runtime = {'scintilla': binaries['Scintilla.dll'], 'lexilla': binaries['Lexilla.dll'],
                   'helper': binaries[package.NATIVE_HELPER_NAME], 'wrong_abi': binaries[package.NATIVE_WRONG_ABI_NAME],
                   'helper_build_key': helpers[package.NATIVE_HELPER_NAME]['build_key'],
                   'wrong_abi_build_key': helpers[package.NATIVE_WRONG_ABI_NAME]['build_key']}
        report = {'schema': 1, 'diagnostic_only': 1, 'product_acceptance': 0, 'windows_executed': 1,
                  'source_commit': commit, 'source_tree': tree, 'source_sha256': hashlib.sha256(canonical(before)).hexdigest(),
                  'compiler': compiler, 'archives': {spec.id: spec.sha256 for spec in archives.ARCHIVES},
                  'runtime': runtime, 'tests': results}
        stage = 12
        publish_report(private, public, report)
    except Exception:
        # Numeric stages: trigger, platform, freshness, compiler, archives, DLLs,
        # fixtures, receipts, Markdown, i18n, stability, publication. No raw errors.
        print(f'FOCUSED_NATIVE_DIAGNOSTIC code={stage} markdown={counts[0]} i18n={counts[1]}', file=sys.stderr)
        return 1
    print('FOCUSED_NATIVE_DIAGNOSTIC code=0 markdown=114 i18n=1417')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
