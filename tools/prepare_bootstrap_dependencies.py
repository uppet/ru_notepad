#!/usr/bin/env python3
"""Build only pinned native DLL dependencies; never compile Ru or package ZIPs."""
import argparse
import importlib.util
import json
import os
import re
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import zipfile

from bootstrap_provenance import require, checked, sha
from build_bootstrap_release import snapshot, verify_app_baseline, identity
import prepare_lexilla_languages as lexilla_languages

TOOL_NAMES = {'cc', 'cxx', 'make', 'windres', 'ar', 'ranlib', 'objdump'}
DLL_NAMES = {'Scintilla.dll', 'Lexilla.dll', 'RuSyntax.dll', 'RuSyntaxWrongAbi.dll'}
INJECTION_ENV = {'MAKEFLAGS', 'MFLAGS', 'GNUMAKEFLAGS', 'MAKEOVERRIDES', 'MAKEFILES', 'MAKELEVEL',
    'CFLAGS', 'CXXFLAGS', 'CPPFLAGS', 'LDFLAGS', 'LDLIBS', 'LIBS', 'CXX', 'CPP', 'LD', 'AR',
    'RANLIB', 'WINDRES', 'SHELL', 'MAKESHELL', 'SHELLFLAGS', '.SHELLFLAGS',
    'GCC_EXEC_PREFIX', 'COMPILER_PATH', 'LIBRARY_PATH', 'CPATH', 'C_INCLUDE_PATH',
    'CPLUS_INCLUDE_PATH', 'OBJC_INCLUDE_PATH'}
BUILD_ENV = {'PATH', 'SYSTEMROOT', 'WINDIR', 'SYSTEMDRIVE', 'COMSPEC', 'TMP', 'TEMP',
             'PATHEXT', 'NUMBER_OF_PROCESSORS', 'PROCESSOR_ARCHITECTURE'}
RECORDED_ENV = BUILD_ENV | {'CC'}


def load_helpers(root):
    # Only the pinned fixed-C helper function is called. build.main(), Ru parse,
    # module discovery and Compiler.compile are never invoked by this driver.
    def load(name, relative):
        spec = importlib.util.spec_from_file_location(name, checked(root, relative))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    package = load('_bootstrap_dependency_package', 'tools/package.py')
    previous = sys.modules.get('package')
    sys.modules['package'] = package
    try:
        build = load('_bootstrap_dependency_fixed_c_build', 'tools/build.py')
    finally:
        if previous is None:
            sys.modules.pop('package', None)
        else:
            sys.modules['package'] = previous
    return package, build


def validate_tools(paths, hashes):
    require(set(paths) == TOOL_NAMES and set(hashes) == TOOL_NAMES, 'incomplete MinGW tool identity')
    for name in TOOL_NAMES:
        require(re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.+-]*', Path(paths[name]).name) is not None,
                'unsafe MinGW make tool basename: '+name)
        require(identity(paths[name])['sha256'] == hashes[name], 'MinGW tool hash mismatch: '+name)
    require(len({Path(path).parent for path in paths.values()}) == 1, 'MinGW tools must share one locked bin directory')


def dependency_environment(tools, source):
    require(not any(value for key, value in source.items() if key.upper() in INJECTION_ENV),
            'ambient make/compiler options are forbidden')
    # GNU make imports arbitrary environment names as variables (e.g. VPATH).
    # Pass only OS process essentials, not the CI environment or unknown flags.
    environment = {key.upper(): value for key, value in source.items() if key.upper() in BUILD_ENV}
    # CC is an existing workflow default; replace it with the locked compiler.
    environment['CC'] = Path(tools['cc']).name
    environment['PATH'] = str(Path(tools['cc']).parent)+os.pathsep+environment.get('PATH', '')
    return environment


def recorded_environment(environment):
    return {key.upper(): value for key, value in environment.items() if key.upper() in RECORDED_ENV}


def extract_sources(root, dependency):
    archive = checked(root, 'vendor/downloads/'+dependency['archive'])
    require(sha(archive) == dependency['sha256'], 'official archive hash mismatch')
    target = root/'vendor'/dependency['folder']
    require(not target.exists() and not target.is_symlink(), 'dependency extraction requires fresh source directory')
    with zipfile.ZipFile(archive) as bundle:
        for item in bundle.infolist():
            path = PurePosixPath(item.filename)
            require(not path.is_absolute() and '..' not in path.parts and '\\' not in item.filename
                    and ':' not in item.filename and path.parts[0] == dependency['folder'], 'unsafe archive member')
            destination = root/'vendor'/Path(*path.parts)
            require(not any(p.is_symlink() for p in [destination, *destination.parents]), 'linked extraction path')
            if item.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open('xb') as output:
                    output.write(bundle.read(item))


def verify_dependency_bytes(root, dependencies):
    for dependency in dependencies.values():
        archive = checked(root, 'vendor/downloads/'+dependency['archive'])
        require(sha(archive) == dependency['sha256'], 'dependency archive changed')
        with zipfile.ZipFile(archive) as bundle:
            for item in bundle.infolist():
                if not item.is_dir():
                    require(checked(root, 'vendor/'+item.filename).read_bytes() == bundle.read(item),
                            'dependency original source changed: '+item.filename)


def validate_dependencies_receipt(receipt_path, app_root):
    """Recheck actual files/source/tool identities; never trust receipt booleans."""
    receipt_path, app_root = Path(receipt_path), Path(app_root).resolve()
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    require(receipt.get('schema') == 'ru-notepad-bootstrap-dependencies-v1', 'wrong dependency schema')
    pin = receipt['app_source']
    current = snapshot(app_root, pin['commit'], pin['tree'])
    require(current == receipt['source_sha256'], 'dependency app source snapshot mismatch')
    verify_app_baseline(app_root, receipt['app_baseline'], current)
    validate_tools(receipt['tool_paths'], receipt['tool_sha256'])
    environment = receipt['build_environment']
    require(set(environment) <= RECORDED_ENV, 'unrecorded dependency build environment')
    require(not any(value for key, value in environment.items() if key.upper() in INJECTION_ENV),
            'dependency receipt contains injected make/compiler options')
    require(environment['CC'] == Path(receipt['tool_paths']['cc']).name, 'dependency CC identity mismatch')
    package, _ = load_helpers(app_root)
    require(receipt['dependencies'] == package.DEPENDENCIES, 'dependency pins differ from source')
    verify_dependency_bytes(app_root, package.DEPENDENCIES)
    require(receipt.get('lexilla_extra') == lexilla_languages.verify(app_root),
            'supplemental Lexilla compilation inputs differ from receipt')
    require(set(receipt.get('binaries', {})) == DLL_NAMES, 'incomplete dependency binary set')
    directories = set()
    pe = {}
    for name, record in receipt['binaries'].items():
        file = Path(record['path'])
        require(file.name == name and identity(file) == record, 'dependency binary changed')
        directories.add(file.parent)
        pe[name] = package.inspect_pe(file, receipt['tool_paths']['objdump'])
    require(len(directories) == 1, 'dependency files must share owned output directory')
    directory = next(iter(directories))
    require(sha(checked(directory, 'archive-receipt.json')) == receipt['archive_receipt_sha256'], 'archive preparation receipt changed')
    helper = package.validate_native_helper_receipts(app_root, directory, pe)
    require(helper == receipt['native_helpers'], 'helper receipt mismatch')
    require(all(item['compiler_sha256'] == receipt['tool_sha256']['cc'] for item in helper.values()),
            'helper used a different native C compiler')
    return receipt


def validate_receipt(receipt_path):
    receipt = json.loads(Path(receipt_path).read_text(encoding='utf-8'))
    return validate_dependencies_receipt(receipt_path, receipt['app_source']['path'])


def prepare(config, output):
    require(sys.platform == 'win32', 'real Windows dependency build required')
    root = Path(config['app_source']['path']).resolve()
    require(Path(__file__).resolve().parents[1] == root, 'run dependency driver from pinned app feature checkout')
    pin = config['app_source']
    before = snapshot(root, pin['commit'], pin['tree'])
    baseline = verify_app_baseline(root, config['app_baseline'], before)
    tools = {k: str(Path(v).resolve()) for k, v in config['mingw_tool_paths'].items()}
    hashes = config['mingw_tool_sha256']
    validate_tools(tools, hashes)
    require(not output.exists() and not output.is_symlink(), 'dependency output must be fresh')
    require(not output.resolve().is_relative_to(root), 'dependency output cannot modify source tree')
    output.mkdir(parents=True, exist_ok=False)
    package, build = load_helpers(root)
    environment = dependency_environment(tools, os.environ)
    commands = []
    def run(command):
        command = list(map(str, command))
        commands.append(command)
        subprocess.run(command, cwd=root, env=environment, check=True, timeout=900)
    run([sys.executable, '-I', '-B', root/'tools/prepare_source_archives.py', '--root', root,
         '--receipt', output/'archive-receipt.json'])
    archive_receipt = json.loads((output/'archive-receipt.json').read_text(encoding='utf-8'))
    require(archive_receipt.get('passed') is True, 'offline source archive preparation failed')
    for dependency in package.DEPENDENCIES.values():
        extract_sources(root, dependency)
    verify_dependency_bytes(root, package.DEPENDENCIES)
    lexilla_extra = lexilla_languages.prepare(root)
    # Official makefiles interpolate command variables into a command line.
    # Use basename under a pinned single-bin PATH, not an unquoted spaced path.
    common = ['CC='+Path(tools['cc']).name, 'CXX='+Path(tools['cxx']).name, 'WINDRES='+Path(tools['windres']).name,
              'AR='+Path(tools['ar']).name, 'RANLIB='+Path(tools['ranlib']).name]
    run([tools['make'], '-j2', '-C', root/'vendor/scintilla/win32', '../bin/Scintilla.dll', *common])
    run([tools['make'], '-j2', '-C', root/'vendor/lexilla/src', '../bin/lexilla.dll', 'windir=C:/Windows',
         *common, lexilla_languages.MAKE_OBJECT, 'LDFLAGS=-shared -static -mwindows -Wl,--kill-at -s'])
    # Reuse the original reviewed source/flags/cache receipt contract, not a
    # second implementation of the native-helper build system.
    original_run = build.run
    def fixed_helper_run(command, **kwargs):
        command = list(map(str, command))
        commands.append(command)
        kwargs['env'] = environment
        return subprocess.run(command, check=True, **kwargs)
    build.run = fixed_helper_run
    try:
        build.build_native_helpers(tools['cc'], output)
    finally:
        build.run = original_run
    build.copy_native_helpers(output, output)
    shutil.copyfile(root/'vendor/scintilla/bin/Scintilla.dll', output/'Scintilla.dll')
    shutil.copyfile(root/'vendor/lexilla/bin/lexilla.dll', output/'Lexilla.dll')
    verify_dependency_bytes(root, package.DEPENDENCIES)
    require(lexilla_languages.verify(root) == lexilla_extra, 'supplemental Lexilla inputs changed during DLL build')
    require(snapshot(root, pin['commit'], pin['tree']) == before, 'app inputs changed during DLL build')
    validate_tools(tools, hashes)
    pe = {name: package.inspect_pe(output/name, tools['objdump']) for name in DLL_NAMES}
    receipt = {'schema': 'ru-notepad-bootstrap-dependencies-v1', 'status': 'built-not-runtime-accepted',
        'app_source': pin, 'app_baseline': baseline, 'source_sha256': before,
        'tool_paths': tools, 'tool_sha256': hashes, 'commands': commands,
        'build_environment': recorded_environment(environment),
        'dependencies': package.DEPENDENCIES, 'archive_receipt_sha256': sha(output/'archive-receipt.json'),
        'lexilla_extra': lexilla_extra,
        'binaries': {name: identity(output/name) for name in sorted(DLL_NAMES)},
        'native_helpers': package.validate_native_helper_receipts(root, output, pe), 'runtime_accepted': False}
    pending = output/'dependencies-receipt.pending.json'
    pending.write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
    os.replace(pending, output/'dependencies-receipt.json')
    validate_dependencies_receipt(output/'dependencies-receipt.json', root)
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    prepare(json.loads(args.config.read_text(encoding='utf-8')), args.output.resolve())
