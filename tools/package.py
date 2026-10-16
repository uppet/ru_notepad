#!/usr/bin/env python3
"""Build and verify separate portable runtime/test ZIPs from one binary snapshot.

The optional local CLI is deliberately labelled unverified. Only windows_ci.py
can supply real-Windows acceptance after executing the same binary hashes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import subprocess
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEPENDENCIES = {
    'Scintilla.dll': {'version': '5.6.7', 'archive': 'scintilla567.zip',
        'sha256': '2309181e59e7da4659f890dbc128db7451ccd094748770e7be674b830494587c',
        'folder': 'scintilla', 'license': 'Scintilla.txt'},
    'Lexilla.dll': {'version': '5.5.4', 'archive': 'lexilla554.zip',
        'sha256': '5e0a21356e4e2f19d6a38ecd1c8172d5a2b7b4542940568b023386080db90fe0',
        'folder': 'lexilla', 'license': 'Lexilla.txt'},
}
NATIVE_HELPER_NAME = 'RuSyntax.dll'
NATIVE_WRONG_ABI_NAME = 'RuSyntaxWrongAbi.dll'
NATIVE_COMPILE_SOURCES = {
    NATIVE_HELPER_NAME: ('native/ru_scan.c',),
    NATIVE_WRONG_ABI_NAME: ('native/ru_wrong_abi.c',),
}
NATIVE_SOURCE_SUFFIXES = {'.c', '.h', '.inc', '.inl', '.def'}
NATIVE_BUILD_DRIVERS = ('tools/build.py', 'tools/package.py')
NATIVE_CFLAGS = ('-std=c99', '-O2', '-Wall', '-Wextra', '-shared', '-static-libgcc',
                 '-Wl,--no-insert-timestamp', '-Wl,--kill-at', '-s',
                 '-Inative')
NATIVE_LINK_LIBRARIES = ()
RUNTIME_NAMES = ('ru_notepad.exe', *DEPENDENCIES, NATIVE_HELPER_NAME)
TEST_NAMES = ('document_policy.exe', 'ui_arguments.exe', 'file_codec_flags.exe',
              'editor_native.exe', 'app_native.exe', 'app_features_native.exe', 'file_codec_tests.exe',
              'file_codec_security_probe.exe', 'syntax_native.exe', 'syntax_policy.exe', 'shortcuts.exe', 'status_native.exe',
              'file_streaming_native.exe', 'editor_streaming_native.exe',
              'associations_policy.exe', 'associations_native.exe', 'file_drop_native.exe', 'app_streaming_native.exe',
              'ru_lexical_policy.exe', 'ru_syntax_native.exe', 'app_ru_native.exe')
TEST_SUPPORT_DLL_NAMES = (NATIVE_WRONG_ABI_NAME,)
SCANNER_PREFLIGHT_NAME = 'ru-scanner-preflight'
BINARY_NAMES = (*RUNTIME_NAMES, *TEST_NAMES, *TEST_SUPPORT_DLL_NAMES)
RESOURCE_INPUTS = ('packaging/app.rc', 'packaging/app.manifest', 'assets/app-icon.ico', 'VERSION')
SYSTEM_DLLS = {'advapi32.dll', 'gdi32.dll', 'imm32.dll', 'kernel32.dll',
    'msvcrt.dll', 'ole32.dll', 'oleaut32.dll', 'user32.dll', 'comctl32.dll',
    'comdlg32.dll', 'shell32.dll', 'shlwapi.dll', 'version.dll', 'winmm.dll',
    'ntdll.dll', 'uxtheme.dll', 'dwmapi.dll'}
MAX_LOG_BYTES = 1024 * 1024
GUI_EVIDENCE_PREFIXES = {'main-gui-smoke': 'main-launcher',
                         'main-gui-file-entry': 'main-file-entry-launcher',
                         'main-gui-ru-syntax': 'main-ru-syntax-launcher'}
UNICODE_LICENSE_SHA256 = 'e7a93b009565cfce55919a381437ac4db883e9da2126fa28b91d12732bc53d96'
RUNTIME_FILES = {
    'VERSION': 'VERSION', 'packaging/README-preview.txt': 'README.txt',
    'packaging/开始前请读.txt': '开始前请读.txt', 'CHANGELOG.md': 'CHANGELOG.md',
    'THIRD_PARTY_NOTICES.md': 'THIRD_PARTY_NOTICES.md',
    'assets/README.md': 'licenses/Artwork-provenance.md',
    'packaging/licenses/Unicode.txt': 'licenses/Unicode.txt',
}
TEST_FILES = {
    'packaging/run-tests.cmd': 'run-tests.cmd',
    'packaging/OPTIONAL-ACL-TESTS.txt': 'OPTIONAL-ACL-TESTS.txt',
    'tests/file_codec_security_tests.ps1': 'optional-acl-tests.ps1',
}


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def checked_file(path):
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f'Missing or linked package input: {path.name}')
    return path


def source_file(root, relative):
    path = PurePosixPath(relative)
    if path.is_absolute() or '..' in path.parts or '\\' in relative or ':' in relative:
        raise RuntimeError('Unsafe source path in build receipt')
    candidate = root / path
    if root.resolve() not in candidate.resolve().parents:
        raise RuntimeError('Source path escapes the application checkout')
    return checked_file(candidate)


def native_source_snapshot(root):
    required = {source for sources in NATIVE_COMPILE_SOURCES.values() for source in sources}
    for relative in required:
        source_file(root, relative)
    return {path.relative_to(root).as_posix(): sha(source_file(root, path.relative_to(root).as_posix()))
            for path in sorted((root / 'native').rglob('*'))
            if path.suffix.lower() in NATIVE_SOURCE_SUFFIXES and (path.is_file() or path.is_symlink())}


def native_build_key(inputs):
    return hashlib.sha256(json.dumps(inputs, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()


def validate_native_helper_receipts(root, binary_dir, pe):
    sources = native_source_snapshot(root)
    drivers = {relative: sha(source_file(root, relative)) for relative in NATIVE_BUILD_DRIVERS}
    result = {}
    for name, compile_sources in NATIVE_COMPILE_SOURCES.items():
        receipt = json.loads(checked_file(binary_dir / (Path(name).stem + '.native-build.json')).read_text(encoding='utf-8'))
        inputs = receipt.get('build_inputs', {})
        if (receipt.get('name') != name or receipt.get('dll_sha256') != pe[name]['sha256'] or
                inputs.get('source_sha256') != sources or inputs.get('driver_sha256') != drivers or
                inputs.get('compile_sources') != list(compile_sources) or
                inputs.get('output_name') != name or inputs.get('compiler_flags') != list(NATIVE_CFLAGS) or
                inputs.get('link_libraries') != list(NATIVE_LINK_LIBRARIES) or
                receipt.get('build_key') != native_build_key(inputs)):
            raise RuntimeError(f'Native helper build receipt/source mismatch: {name}')
        if not all(re.fullmatch(r'[a-f0-9]{64}', inputs.get(key, '')) for key in
                   ('compiler_sha256', 'compiler_version_sha256')):
            raise RuntimeError(f'Native helper compiler identity is missing: {name}')
        result[name] = {'dll_sha256': receipt['dll_sha256'], 'build_key': receipt['build_key'],
                        'source_sha256': sources, 'driver_sha256': drivers,
                        'compiler_sha256': inputs['compiler_sha256'],
                        'compiler_version_sha256': inputs['compiler_version_sha256'],
                        'compiler_flags': inputs['compiler_flags'],
                        'compile_sources': inputs['compile_sources'],
                        'link_libraries': inputs['link_libraries']}
    return result


def inspect_pe(path, objdump):
    data = checked_file(path).read_bytes()
    if len(data) < 64 or data[:2] != b'MZ':
        raise RuntimeError(f'{path.name}: missing PE header')
    offset = struct.unpack_from('<I', data, 60)[0]
    if offset > len(data) - 24 or data[offset:offset + 4] != b'PE\0\0' or struct.unpack_from('<H', data, offset + 4)[0] != 0x8664:
        raise RuntimeError(f'{path.name}: not a Windows x64 executable')
    output = subprocess.check_output([str(objdump), '-p', str(path)], text=True, timeout=30)
    imports = re.findall(r'DLL Name:\s*(\S+)', output)
    bundled = set(DEPENDENCIES) | {NATIVE_HELPER_NAME}
    allowed = SYSTEM_DLLS if path.name in NATIVE_COMPILE_SOURCES else SYSTEM_DLLS | {name.lower() for name in bundled}
    unexpected = {name.lower() for name in imports} - allowed
    if unexpected:
        raise RuntimeError(f'{path.name}: unpackaged non-system DLL imports: {sorted(unexpected)}')
    for imported in imports:
        match = next((name for name in bundled if name.lower() == imported.lower()), None)
        if match:
            checked_file(path.parent / match)
    return {'sha256': sha(path), 'bytes': len(data), 'machine': 'AMD64', 'imports': imports}


def validate_dependency_sources(root):
    """Verify the official pins and exact license bytes, including local packaging."""
    unicode_license = source_file(root, 'packaging/licenses/Unicode.txt')
    if sha(unicode_license) != UNICODE_LICENSE_SHA256:
        raise RuntimeError('Unicode data license differs from the reviewed official notice')
    for dependency in DEPENDENCIES.values():
        archive = checked_file(root / 'vendor/downloads' / dependency['archive'])
        if sha(archive) != dependency['sha256']:
            raise RuntimeError(f'Official {dependency["folder"]} archive hash mismatch')
        relative = dependency['folder'] + '/License.txt'
        with zipfile.ZipFile(archive) as source:
            expected = source.read(relative)
        if checked_file(root / 'vendor' / relative).read_bytes() != expected:
            raise RuntimeError(f'{dependency["folder"]} license differs from the pinned source')


def binary_snapshot(binary_dir):
    return {name: sha(checked_file(binary_dir / name)) for name in BINARY_NAMES}


def validate_receipts(root, binary_dir, objdump):
    version = (root / 'VERSION').read_text(encoding='utf-8').strip()
    pe = {name: inspect_pe(binary_dir / name, objdump) for name in BINARY_NAMES}
    app = json.loads(checked_file(binary_dir / 'ru_notepad.build.json').read_text(encoding='utf-8'))
    receipts = validate_native_helper_receipts(root, binary_dir, pe)
    helper = receipts[NATIVE_HELPER_NAME]
    for name in (RUNTIME_NAMES[0], *TEST_NAMES):
        receipt = json.loads(checked_file(binary_dir / Path(name).with_suffix('.build.json')).read_text(encoding='utf-8'))
        if receipt['app_version'] != version or receipt['exe_sha256'] != pe[name]['sha256']:
            raise RuntimeError(f'Build receipt/version does not match {name}')
        if (receipt.get('native_helper_sha256') != helper['dll_sha256'] or
                receipt.get('native_helper_build_key') != helper['build_key'] or
                any(receipt.get('source_sha256', {}).get(path) != digest
                    for path, digest in helper['source_sha256'].items())):
            raise RuntimeError(f'Native helper differs from the executable source/receipt: {name}')
        for dll, dependency in DEPENDENCIES.items():
            prefix = dependency['folder']
            field = 'dll_sha256' if dll == 'Scintilla.dll' else 'lexilla_dll_sha256'
            if (receipt[field] != pe[dll]['sha256'] or
                    receipt[prefix + '_version'] != dependency['version'] or
                    receipt[prefix + '_archive_sha256'] != dependency['sha256']):
                raise RuntimeError(f'Dependency build receipt does not match {name}: {dll}')
        if receipt['source_sha256'] != app['source_sha256'] or receipt['ru_tree'] != app['ru_tree'] or receipt['ru_commit'] != app['ru_commit']:
            raise RuntimeError(f'Source/compiler snapshot mismatch for {name}')
        if not set(RESOURCE_INPUTS) <= receipt.get('build_input_sha256', {}).keys():
            raise RuntimeError(f'{name}: requires hash-verified common-controls manifest/resource inputs')
        for relative, digest in {**receipt['source_sha256'], **receipt.get('build_input_sha256', {}),
                                 receipt['entry_source']: receipt['entry_sha256']}.items():
            if sha(source_file(root, relative)) != digest:
                raise RuntimeError(f'Source changed since building {name}: {relative}')
        if name == 'ru_notepad.exe' and 'packaging/diagnostic_launcher.c' not in receipt.get('build_input_sha256', {}):
            raise RuntimeError('The GUI requires a hash-verified diagnostic launcher')
        # Never publish compiler argv, absolute machine paths, or full raw receipts.
        receipts[name] = {key: receipt[key] for key in (
            'entry_source', 'entry_sha256', 'generated_c_sha256', 'translation_unit_sha256',
            'build_input_sha256', 'exe_sha256', 'dll_sha256', 'lexilla_dll_sha256',
            'native_helper_sha256', 'native_helper_build_key')}
    return app, receipts, pe


def evidence_names(test_names):
    return {'msys2-packages.log', 'native-acceptance.json',
            *(f'{SCANNER_PREFLIGHT_NAME}.{stream}.log' for stream in ('stdout', 'stderr')),
            *(f'{name}.{stream}.log' for name in test_names for stream in ('stdout', 'stderr')),
            *(f'{prefix}-{number}.log' for prefix in GUI_EVIDENCE_PREFIXES.values()
              for number in range(4))}


def required_evidence_names(summary):
    required = {'msys2-packages.log', 'native-acceptance.json',
                *(f'{SCANNER_PREFLIGHT_NAME}.{stream}.log' for stream in ('stdout', 'stderr'))}
    for test in summary['tests']:
        name = test['name']
        if name in GUI_EVIDENCE_PREFIXES:
            required.add(GUI_EVIDENCE_PREFIXES[name] + '-0.log')
        else:
            required.update(f'{name}.{stream}.log' for stream in ('stdout', 'stderr'))
    return required


def validate_native_evidence(evidence, summary, allowed_names):
    required = required_evidence_names(summary)
    if evidence is None or not required <= set(allowed_names):
        raise RuntimeError('Native evidence allowlist omits required test outputs')
    for name in required:
        path = checked_file(evidence / name)
        if path.stat().st_size > MAX_LOG_BYTES:
            raise RuntimeError(f'{name}: synthetic evidence exceeds 1 MiB limit')


def copy_evidence(evidence, destination, allowed_names):
    destination.mkdir()
    for name in sorted(allowed_names):
        source = evidence / name
        if not source.exists() and not source.is_symlink():
            continue
        checked_file(source)
        if source.stat().st_size > MAX_LOG_BYTES:
            raise RuntimeError(f'{name}: synthetic evidence exceeds 1 MiB limit')
        shutil.copyfile(source, destination / name)


def write_archive(stage, destination):
    inventory = {path.relative_to(stage).as_posix(): sha(checked_file(path))
                 for path in sorted(stage.rglob('*')) if path.is_file() or path.is_symlink()}
    (stage / 'SHA256SUMS.txt').write_text(''.join(
        f'{digest}  {name}\n' for name, digest in inventory.items()), encoding='utf-8')
    archive = destination / f'{stage.name}.zip'
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        for path in sorted(stage.rglob('*')):
            if path.is_file():
                output.write(path, f'{stage.name}/{path.relative_to(stage).as_posix()}')
    verify_archive(archive)
    archive.with_suffix('.zip.sha256').write_text(f'{sha(archive)}  {archive.name}\n', encoding='utf-8')
    return {'name': archive.name, 'sha256': sha(archive), 'bytes': archive.stat().st_size}


def verify_archive(archive):
    """Read every file back: CRC, safe inventory, manifest coverage and hashes."""
    with zipfile.ZipFile(archive) as check:
        if check.testzip() is not None:
            raise RuntimeError('Portable ZIP failed CRC verification')
        members = check.namelist()
        if len(members) != len(set(members)):
            raise RuntimeError('Duplicate ZIP inventory entry')
        prefix = archive.stem + '/'
        files = {}
        for member in members:
            relative = member.removeprefix(prefix)
            path = PurePosixPath(relative)
            if not member.startswith(prefix) or path.is_absolute() or '..' in path.parts or '\\' in relative or ':' in relative or not relative or member.endswith('/'):
                raise RuntimeError('Unsafe or unexpected ZIP inventory entry')
            files[relative] = check.read(member)
        lines = files.pop('SHA256SUMS.txt').decode('utf-8').splitlines()
        expected = {}
        for line in lines:
            match = re.fullmatch(r'([a-f0-9]{64})  (.+)', line)
            if not match or match[2] in expected:
                raise RuntimeError('Invalid hash manifest')
            expected[match[2]] = match[1]
        actual = {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
        if actual != expected:
            raise RuntimeError('ZIP hash manifest mismatch or incomplete inventory')
        build = json.loads(files['BUILD.json'])
        if build['package_kind'] not in ('runtime', 'tests') or set(build['runtime_binary_sha256']) != set(RUNTIME_NAMES):
            raise RuntimeError('Invalid package kind or runtime hash inventory')
        for name, digest in build['runtime_binary_sha256'].items():
            if actual.get(name) != digest:
                raise RuntimeError('Runtime binary differs from BUILD manifest')
        executable_names = {name for name in files if name.lower().endswith(('.exe', '.dll'))}
        required = set(RUNTIME_NAMES if build['package_kind'] == 'runtime' else BINARY_NAMES)
        if executable_names != required:
            raise RuntimeError('Incorrect runtime/test executable inventory')
        if build['package_kind'] == 'runtime' and any(
                name.startswith('native-test-evidence/') or name.lower().endswith(('.cmd', '.ps1', '.log'))
                for name in files):
            raise RuntimeError('Test scripts or evidence leaked into the runtime ZIP')
        return files


def verify_package_pair(runtime, tests):
    runtime_files, test_files = verify_archive(runtime), verify_archive(tests)
    runtime_build, test_build = (json.loads(files['BUILD.json']) for files in (runtime_files, test_files))
    if runtime_build['package_kind'] != 'runtime' or test_build['package_kind'] != 'tests':
        raise RuntimeError('Expected one runtime ZIP and one tests ZIP')
    if runtime_build['runtime_binary_sha256'] != test_build['runtime_binary_sha256']:
        raise RuntimeError('Runtime manifests disagree across the two ZIPs')
    for name in RUNTIME_NAMES:
        if runtime_files[name] != test_files[name]:
            raise RuntimeError(f'Runtime bytes differ across the two ZIPs: {name}')


def _create_packages(root, binary_dir, destination, evidence, objdump, summary,
                    copy_licenses, metadata, allowed_evidence=()):
    version = (root / 'VERSION').read_text(encoding='utf-8').strip()
    if not re.fullmatch(r'[0-9A-Za-z.+-]+', version):
        raise RuntimeError('Unsafe version for portable archive name')
    validate_dependency_sources(root)
    app, receipts, pe = validate_receipts(root, binary_dir, objdump)
    hashes = {name: entry['sha256'] for name, entry in pe.items()}
    native = summary.get('platform') == 'native-windows-x64'
    if native and (not summary.get('passed') or not summary.get('native_tests_passed') or
                   summary.get('tested_binary_sha256') != hashes):
        raise RuntimeError('Native acceptance must cover the exact packaged binary snapshot')
    if native:
        # Defend the packaging boundary too: booleans and matching hashes alone
        # cannot bless a missing, skipped, or force-killed mandatory test group.
        from windows_ci import validate_acceptance
        validate_acceptance(summary, root)
        validate_native_evidence(evidence, summary, allowed_evidence)
    if not native and summary.get('passed'):
        raise RuntimeError('Cross-built packages cannot claim native acceptance')
    artifacts = {}
    for kind in ('runtime', 'tests'):
        suffix = '' if kind == 'runtime' else '-tests'
        stage = destination / f'ru_notepad-{version}-windows-x64{suffix}'
        stage.mkdir()
        (stage / 'licenses').mkdir()
        selected = RUNTIME_NAMES if kind == 'runtime' else BINARY_NAMES
        for name in selected:
            shutil.copyfile(checked_file(binary_dir / name), stage / name)
            if sha(stage / name) != hashes[name]:
                raise RuntimeError(f'Binary changed during packaging: {name}')
        for source, target in {**RUNTIME_FILES, **(TEST_FILES if kind == 'tests' else {})}.items():
            shutil.copyfile(source_file(root, source), stage / target)
        for dependency in DEPENDENCIES.values():
            shutil.copyfile(root / 'vendor' / dependency['folder'] / 'License.txt',
                            stage / 'licenses' / dependency['license'])
        samples = root / 'packaging/samples'
        for path in sorted(samples.rglob('*')):
            if path.is_file() or path.is_symlink():
                target = stage / 'samples' / path.relative_to(samples)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(checked_file(path), target)
        copy_licenses(stage / 'licenses')
        if kind == 'tests' and evidence is not None:
            copy_evidence(evidence, stage / 'native-test-evidence', allowed_evidence)
        status = ('native Windows automated acceptance passed; preview, not full manual acceptance'
                  if native else 'cross-built; native Windows acceptance NOT RUN')
        build = {'schema': 2, 'version': version, 'package_kind': kind, 'status': status,
            'packaged_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            **metadata, 'ru_commit': app['ru_commit'], 'ru_tree': app['ru_tree'],
            'dependencies': DEPENDENCIES, 'source_sha256': app['source_sha256'],
            'runtime_binary_sha256': {name: hashes[name] for name in RUNTIME_NAMES},
            'binaries': {name: pe[name] for name in selected},
            'build_entries': {name: receipts[name] for name in selected if name.endswith('.exe')},
            'native_helpers': {name: receipts[name] for name in selected if name in NATIVE_COMPILE_SOURCES},
            'native_acceptance': summary if kind == 'tests' else {
                'platform': summary.get('platform'), 'passed': summary.get('passed', False),
                'tests': [{'name': test['name'], 'passed': test['passed'],
                           'assertions_passed': test.get('assertions_passed')}
                          for test in summary.get('tests', [])]},
            'remaining_manual_gates': ['Windows user interaction, accessibility, DPI, IME and dialogs',
                'Broader ACL/reparse/race/fallback acceptance beyond synthetic cases',
                'Crash recovery, large-file performance and full Notepad++ parity are not claimed']}
        save_json(stage / 'BUILD.json', build)
        artifacts[kind] = write_archive(stage, destination)
    verify_package_pair(*(destination / artifacts[kind]['name'] for kind in ('runtime', 'tests')))
    return {'schema': 2, 'runtime_binary_sha256': {name: hashes[name] for name in RUNTIME_NAMES},
            'packages': artifacts, 'runtime_byte_identity_verified': True}


def create_packages(root, binary_dir, destination, evidence, objdump, summary,
                    copy_licenses, metadata, allowed_evidence=()):
    # A failed verification must not leave a half-published pair. Existing
    # artifacts are never removed or overwritten, including older previews.
    # Acquire this directory atomically before accepting cleanup ownership.
    destination.mkdir(parents=True, exist_ok=False)
    try:
        return _create_packages(root, binary_dir, destination, evidence, objdump,
                                summary, copy_licenses, metadata, allowed_evidence)
    except Exception:
        if destination.exists():
            shutil.rmtree(destination)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--objdump', required=True)
    parser.add_argument('--unverified-preview', action='store_true')
    args = parser.parse_args()
    if not args.unverified_preview:
        parser.error('Use native Windows CI for tested packages. Local packaging requires --unverified-preview.')
    if subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain'], text=True).strip():
        raise SystemExit('Commit the reviewed local project snapshot before packaging.')
    version = (ROOT / 'VERSION').read_text().strip()
    def licenses(destination):
        for source, target in (
            (ROOT / '.tools/root/usr/share/doc/gcc-mingw-w64-base/copyright', 'GCC-runtime.txt'),
            (ROOT / '.tools/root/usr/share/doc/mingw-w64-x86-64-dev/copyright', 'MinGW-w64.txt'),
            (Path('/usr/share/common-licenses/GPL-3'), 'GPL-3.txt')):
            shutil.copyfile(checked_file(source), destination / target)
    summary = {'platform': 'cross-built-unverified', 'passed': False,
               'native_tests_passed': False, 'tests': [],
               'not_run': 'All native Windows application, editor, syntax, codec, ACL and GUI acceptance'}
    result = create_packages(ROOT, ROOT / 'build', ROOT / 'dist' / f'unverified-{version}',
        None, args.objdump, summary, licenses,
        {'app_commit': subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()})
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
