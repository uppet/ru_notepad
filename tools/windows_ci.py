#!/usr/bin/env python3
"""Real-Windows acceptance and portable CI packaging; never emulates a pass.

Only fresh synthetic outputs from --bin-dir are collected. No Temp scan, user
logs, home directories, screenshots, environment dumps, or developer receipts.
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MAX_LOG_BYTES = 1024 * 1024
MAIN_CLASS = 'RuNotepad.Main.0.1'
BINARY_NAMES = ['ru_notepad.exe', 'Scintilla.dll', 'document_policy.exe',
                'ui_arguments.exe', 'editor_native.exe', 'app_native.exe',
                'file_codec_tests.exe', 'file_codec_security_probe.exe']
SYSTEM_DLLS = {'advapi32.dll', 'gdi32.dll', 'imm32.dll', 'kernel32.dll',
               'msvcrt.dll', 'ole32.dll', 'oleaut32.dll', 'user32.dll',
               'comctl32.dll', 'comdlg32.dll', 'shell32.dll', 'shlwapi.dll',
               'version.dll', 'winmm.dll', 'ntdll.dll', 'uxtheme.dll', 'dwmapi.dll'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def bounded_text(path):
    if path.stat().st_size > MAX_LOG_BYTES:
        raise RuntimeError(f'{path.name}: synthetic log exceeds 1 MiB limit')
    return path.read_text(encoding='utf-8', errors='replace')


def cap_log(path):
    """Bound only this run's own output before any evidence upload."""
    if path.is_file() and path.stat().st_size > MAX_LOG_BYTES:
        with path.open('r+b') as stream:
            stream.truncate(MAX_LOG_BYTES)


class Windows:
    def __init__(self):
        if hasattr(ctypes.WinDLL('ntdll'), 'wine_get_version'):
            raise RuntimeError('Wine cannot produce native Windows acceptance evidence')
        self.user = ctypes.WinDLL('user32', use_last_error=True)
        self.callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        self.user.EnumWindows.argtypes = [self.callback_type, wintypes.LPARAM]
        self.user.EnumWindows.restype = wintypes.BOOL
        self.user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        self.user.GetWindowThreadProcessId.restype = wintypes.DWORD
        self.user.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.user.GetClassNameW.restype = ctypes.c_int
        self.user.IsWindowVisible.argtypes = [wintypes.HWND]
        self.user.IsWindowVisible.restype = wintypes.BOOL
        self.user.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        self.user.PostMessageW.restype = wintypes.BOOL
        self.user.SendMessageTimeoutW.argtypes = [wintypes.HWND, wintypes.UINT,
            wintypes.WPARAM, wintypes.LPARAM, wintypes.UINT, wintypes.UINT,
            ctypes.POINTER(ctypes.c_size_t)]
        self.user.SendMessageTimeoutW.restype = wintypes.LPARAM

    def windows(self, process_id):
        matches = []
        @self.callback_type
        def visit(hwnd, _):
            owner = wintypes.DWORD()
            self.user.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
            if owner.value == process_id:
                name = ctypes.create_unicode_buffer(256)
                self.user.GetClassNameW(hwnd, name, len(name))
                matches.append((hwnd, name.value, bool(self.user.IsWindowVisible(hwnd))))
            return True
        if not self.user.EnumWindows(visit, 0):
            raise ctypes.WinError(ctypes.get_last_error())
        return matches

    def no_dialog(self, process_id):
        windows = self.windows(process_id)
        if any(name == '#32770' and visible for _, name, visible in windows):
            raise RuntimeError('Unexpected modal dialog in synthetic native test')
        return windows

    def responsive(self, hwnd):
        result = ctypes.c_size_t()
        if not self.user.SendMessageTimeoutW(hwnd, 0, 0, 0, 3, 5000, ctypes.byref(result)):
            raise RuntimeError('Visible main HWND did not respond to WM_NULL within 5 seconds')

    def close(self, hwnd):
        if not self.user.PostMessageW(hwnd, 0x0010, 0, 0):  # WM_CLOSE, ordinary app shutdown
            raise ctypes.WinError(ctypes.get_last_error())


def cleanup_process(process):
    if process.poll() is not None:
        return False
    # Cleanup is never success. /T covers the optional PowerShell ACL probe child.
    try:
        subprocess.run(['taskkill.exe', '/PID', str(process.pid), '/T', '/F'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=10)
    return True


def run_console(api, name, command, evidence, marker, timeout=120):
    out, err = evidence / f'{name}.stdout.log', evidence / f'{name}.stderr.log'
    result = {'name': name, 'passed': False, 'executed': False, 'cleanup_killed': False}
    started = time.monotonic()
    process = None
    try:
        with out.open('xb') as stdout, err.open('xb') as stderr:
            process = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr)
            result['executed'] = True
            deadline = time.monotonic() + timeout
            while process.poll() is None:
                api.no_dialog(process.pid)
                if time.monotonic() >= deadline:
                    raise RuntimeError(f'{name}: exceeded {timeout}-second execution deadline')
                if out.stat().st_size > MAX_LOG_BYTES or err.stat().st_size > MAX_LOG_BYTES:
                    raise RuntimeError(f'{name}: exceeded synthetic log size limit')
                time.sleep(0.1)
            result['exit_code'] = process.returncode
        stdout_text, stderr_text = bounded_text(out), bounded_text(err)
        result['assertions_passed'] = len(re.findall(r'^PASS:', stdout_text, re.M))
        result['skips'] = re.findall(r'^SKIP:.*$', stdout_text + stderr_text, re.M)
        if result['skips']:
            raise RuntimeError(f'{name}: required native gate skipped a case: {result["skips"]}')
        if process.returncode != 0:
            raise RuntimeError(f'{name}: nonzero exit status {process.returncode}')
        if not re.search(marker, stdout_text, re.M) or 'FAIL:' in stdout_text + stderr_text:
            raise RuntimeError(f'{name}: required success marker missing or failure reported')
        result['passed'] = True
    except Exception as exc:
        result['error'] = str(exc)
    finally:
        if process is not None:
            result['cleanup_killed'] = cleanup_process(process)
            if result['cleanup_killed']:
                result['passed'] = False
        for path in (out, err):
            cap_log(path)
        result['seconds'] = round(time.monotonic() - started, 3)
    return result


def run_gui(api, binary_dir, evidence):
    result = {'name': 'main-gui-smoke', 'passed': False, 'executed': False,
              'main_hwnd_seen': False, 'close_posted': False, 'cleanup_killed': False,
              'detached_from_console': True}
    started = time.monotonic()
    process = None
    # The dedicated bin dir was just built by this CI run; reject stale logs.
    if list(binary_dir.glob('ru_notepad-*.log')):
        result['error'] = 'Refusing stale launcher logs in fresh test binary directory'
        return result
    try:
        process = subprocess.Popen([str(binary_dir / 'ru_notepad.exe')], cwd=binary_dir,
                                   creationflags=0x00000008)  # DETACHED_PROCESS
        result['executed'] = True
        deadline = time.monotonic() + 30
        hwnd = None
        while hwnd is None:
            windows = api.no_dialog(process.pid)
            if process.poll() is not None:
                raise RuntimeError(f'GUI exited before a visible main HWND: {process.returncode}')
            visible_main = [handle for handle, name, visible in windows
                            if name == MAIN_CLASS and visible]
            if len(visible_main) == 1:
                hwnd = visible_main[0]
            elif len(visible_main) > 1:
                raise RuntimeError('More than one main HWND belongs to the application')
            if time.monotonic() >= deadline:
                raise RuntimeError('No visible main HWND within 30 seconds')
            time.sleep(0.1)
        result['main_hwnd_seen'] = True
        result['window_class'] = MAIN_CLASS
        # Let queued startup work run, then prove that the actual event loop responds.
        settle_until = time.monotonic() + 1
        while time.monotonic() < settle_until:
            api.no_dialog(process.pid)
            if process.poll() is not None:
                raise RuntimeError('GUI terminated while checking startup stability')
            time.sleep(0.1)
        api.responsive(hwnd)
        api.no_dialog(process.pid)
        api.close(hwnd)
        result['close_posted'] = True
        deadline = time.monotonic() + 15
        while process.poll() is None:
            api.no_dialog(process.pid)
            if time.monotonic() >= deadline:
                raise RuntimeError('GUI did not exit normally within 15 seconds after WM_CLOSE')
            time.sleep(0.1)
        result['exit_code'] = process.returncode
        if process.returncode != 0:
            raise RuntimeError(f'GUI exited with status {process.returncode}')
        logs = list(binary_dir.glob('ru_notepad-*.log'))
        if len(logs) != 1:
            raise RuntimeError('Expected exactly one fresh launcher log beside the application')
        text = bounded_text(logs[0])
        required = ('[launcher] Starting Ru program.', '[startup] menu installed',
                    '[startup] initial document ready', '[startup] main window shown',
                    '[launcher] Ru program returned with status 0.')
        if any(marker not in text for marker in required):
            raise RuntimeError('Launcher log does not prove full startup and normal return 0')
        if re.search(r'initialization failed|exited before returning|fatal|FAIL:', text, re.I):
            raise RuntimeError('Launcher log records an error despite the exit code')
        result['passed'] = True
    except Exception as exc:
        result['error'] = str(exc)
    finally:
        if process is not None:
            result['cleanup_killed'] = cleanup_process(process)
            if result['cleanup_killed']:
                result['passed'] = False
        # Copy only logs newly produced in this isolated binary directory. Never
        # search fallback Temp, collect user logs, or dereference arbitrary paths.
        logs = sorted(binary_dir.glob('ru_notepad-*.log'))
        for index, path in enumerate(logs[:4]):
            cap_log(path)
            shutil.copyfile(path, evidence / f'main-launcher-{index}.log')
        result['seconds'] = round(time.monotonic() - started, 3)
    return result


def inspect_pe(path, objdump):
    data = path.read_bytes()
    if len(data) < 64 or data[:2] != b'MZ':
        raise RuntimeError(f'{path.name}: missing PE header')
    offset = struct.unpack_from('<I', data, 60)[0]
    if data[offset:offset + 4] != b'PE\0\0' or struct.unpack_from('<H', data, offset + 4)[0] != 0x8664:
        raise RuntimeError(f'{path.name}: not a Windows x64 executable')
    output = subprocess.check_output([str(objdump), '-p', str(path)], text=True, timeout=30)
    imports = re.findall(r'DLL Name:\s*(\S+)', output)
    # MINGW64 targets msvcrt. No hidden compiler runtime DLL dependency is allowed.
    unexpected = {name.lower() for name in imports} - SYSTEM_DLLS
    if unexpected:
        raise RuntimeError(f'{path.name}: unpackaged non-system DLL imports: {sorted(unexpected)}')
    return {'sha256': sha(path), 'bytes': len(data), 'machine': 'AMD64', 'imports': imports}


def copy_runtime_licenses(mingw, destination):
    source = mingw / 'share' / 'licenses'
    folders = [path for path in source.iterdir() if path.is_dir()
               and re.search(r'gcc|cc-libs|libstdc|libgcc|mingw|winpthread|crt|headers', path.name, re.I)]
    if not folders:
        raise RuntimeError('MSYS2 runtime license directories are missing')
    collected = []
    for folder in folders:
        for path in sorted(folder.rglob('*')):
            if path.is_file():
                if path.is_symlink() or path.stat().st_size > MAX_LOG_BYTES:
                    raise RuntimeError('Unexpected runtime license link or size')
                target = destination / 'MSYS2' / path.relative_to(source)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
                collected.append(path.read_text(encoding='utf-8', errors='replace'))
    combined = '\n'.join(collected)
    if 'GCC RUNTIME LIBRARY EXCEPTION' not in combined or 'GNU GENERAL PUBLIC LICENSE' not in combined:
        raise RuntimeError('GCC GPL and Runtime Library Exception notices must accompany the binaries')
    if 'mingw' not in combined.lower():
        raise RuntimeError('MinGW-w64 license notices are missing')


def package(binary_dir, evidence, mingw, objdump, summary):
    version = (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
    if not re.fullmatch(r'[0-9A-Za-z.+-]+', version):
        raise RuntimeError('Unsafe version for portable archive name')
    destination = evidence.parent / 'dist'
    destination.mkdir()
    stage = destination / f'ru_notepad-{version}-windows-x64'
    stage.mkdir()
    licenses = stage / 'licenses'
    licenses.mkdir()
    pe = {name: inspect_pe(binary_dir / name, objdump) for name in BINARY_NAMES}
    app = json.loads((binary_dir / 'ru_notepad.build.json').read_text())
    receipts = {}
    for name in BINARY_NAMES:
        shutil.copyfile(binary_dir / name, stage / name)
        if name.endswith('.exe'):
            receipt = json.loads((binary_dir / Path(name).with_suffix('.build.json')).read_text())
            if receipt['exe_sha256'] != pe[name]['sha256'] or receipt['dll_sha256'] != pe['Scintilla.dll']['sha256']:
                raise RuntimeError(f'Build receipt does not match {name}')
            if receipt['source_sha256'] != app['source_sha256'] or receipt['ru_tree'] != app['ru_tree']:
                raise RuntimeError(f'Source/compiler snapshot mismatch for {name}')
            for relative, digest in {**receipt['source_sha256'], **receipt.get('build_input_sha256', {}),
                                     receipt['entry_source']: receipt['entry_sha256']}.items():
                if sha(ROOT / relative) != digest:
                    raise RuntimeError(f'Source changed since building {name}: {relative}')
            # Omit absolute build-machine paths and compiler argv from public receipt.
            receipts[name] = {key: receipt[key] for key in (
                'entry_source', 'entry_sha256', 'generated_c_sha256', 'translation_unit_sha256',
                'build_input_sha256', 'exe_sha256', 'dll_sha256')}
    files = {
        'VERSION': 'VERSION', 'packaging/README-preview.txt': 'README.txt',
        'THIRD_PARTY_NOTICES.md': 'THIRD_PARTY_NOTICES.md',
        'packaging/开始前请读.txt': '开始前请读.txt', 'packaging/run-tests.cmd': 'run-tests.cmd',
        'packaging/OPTIONAL-ACL-TESTS.txt': 'OPTIONAL-ACL-TESTS.txt',
        'tests/file_codec_security_tests.ps1': 'optional-acl-tests.ps1',
        'CHANGELOG.md': 'CHANGELOG.md', 'docs/notepadpp-parity-roadmap.md': 'ROADMAP.md',
        'docs/startup-fix-0.1.1.md': 'STARTUP-FIX.md',
        'vendor/scintilla/License.txt': 'licenses/Scintilla.txt',
        'assets/README.md': 'licenses/Artwork-provenance.md',
    }
    for source, target in files.items():
        shutil.copyfile(ROOT / source, stage / target)
    shutil.copytree(ROOT / 'packaging' / 'samples', stage / 'samples')
    copy_runtime_licenses(mingw, licenses)
    shutil.copyfile(evidence / 'msys2-packages.log', stage / 'MSYS2-PACKAGES.txt')
    # Tests use only synthetic data. Include bounded logs, never all of build/.
    shutil.copytree(evidence, stage / 'native-test-evidence')
    commit = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    build = {'schema': 1, 'version': version, 'app_commit': commit,
             'status': 'native Windows automated acceptance passed; preview, not full manual acceptance',
             'ru_commit': app['ru_commit'], 'ru_tree': app['ru_tree'],
             'scintilla_version': '5.6.7', 'scintilla_archive_sha256': app['scintilla_archive_sha256'],
             'source_sha256': app['source_sha256'], 'build_entries': receipts, 'binaries': pe,
             'native_acceptance': summary,
             'remaining_manual_gates': ['Windows user interaction, accessibility, DPI, IME and dialogs',
                'Broader ACL/reparse/race/fallback acceptance beyond the synthetic automated cases',
                'Crash recovery, performance, and full Notepad++ parity are not claimed']}
    save_json(stage / 'BUILD.json', build)
    (stage / 'NATIVE-CI.txt').write_text(
        'This ZIP contains the exact Windows-built binaries exercised by the attached native test evidence.\n'
        'BUILD.json records which tests passed. A forced kill or timeout never counts as a GUI pass.\n'
        'Earlier cross-build notes describe earlier evidence; this is still a limited preview.\n'
        'Back up important files before trying it. No user documents were used in CI.\n', encoding='utf-8')
    (stage / 'SHA256SUMS.txt').write_text(''.join(
        f'{sha(path)}  {path.relative_to(stage).as_posix()}\n'
        for path in sorted(stage.rglob('*')) if path.is_file()), encoding='utf-8')
    archive = destination / f'{stage.name}.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        for path in sorted(stage.rglob('*')):
            if path.is_file():
                output.write(path, path.relative_to(destination).as_posix())
    with zipfile.ZipFile(archive) as check:
        if check.testzip() is not None:
            raise RuntimeError('Portable ZIP failed CRC verification')
    archive.with_suffix('.zip.sha256').write_text(f'{sha(archive)}  {archive.name}\n', encoding='utf-8')
    return {'name': archive.name, 'sha256': sha(archive), 'bytes': archive.stat().st_size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bin-dir', required=True, type=Path)
    parser.add_argument('--evidence-dir', required=True, type=Path)
    parser.add_argument('--mingw-root', required=True, type=Path)
    parser.add_argument('--objdump', required=True, type=Path)
    parser.add_argument('--acl', action='store_true', help='Run synthetic NTFS ACL replacement cases')
    args = parser.parse_args()
    if sys.platform != 'win32':
        parser.error('Real Windows is required; Linux/Wine cannot produce a native acceptance receipt')
    binary_dir, evidence = args.bin_dir.resolve(), args.evidence_dir.resolve()
    api = Windows()
    summary = {'schema': 1, 'platform': 'native-windows-x64', 'passed': False,
               'synthetic_data_only': True, 'tests': [], 'acl_requested': args.acl,
               'native_tests_passed': False}
    try:
        with tempfile.TemporaryDirectory(prefix='ru-notepad-ci-') as fixtures:
            for name, marker in [('document_policy', r'^TOTAL PASS: 23\s*$'),
                                 ('ui_arguments', r'^TOTAL PASS: 19\s*$'),
                                 ('editor_native', r'^TOTAL PASS: 27\s*$'),
                                 ('app_native', r'^TOTAL PASS: 23\s*$'),
                                 ('file_codec_tests', r'^FILE_CODEC_TESTS_PASS=77\s*$')]:
                command = [str(binary_dir / f'{name}.exe')]
                if name == 'file_codec_tests':
                    command.append(fixtures)
                result = run_console(api, name, command, evidence, marker)
                summary['tests'].append(result)
                save_json(evidence / 'native-acceptance.json', summary)
                print(json.dumps(result), flush=True)
            if args.acl:
                command = ['pwsh', '-NoProfile', '-NonInteractive', '-File',
                           str(ROOT / 'tests/file_codec_security_tests.ps1'), '-ProbeExe',
                           str(binary_dir / 'file_codec_security_probe.exe'), '-TestDirectory', fixtures]
                result = run_console(api, 'file_codec_security', command, evidence,
                                     r'^FILE_CODEC_SECURITY_TESTS_PASS\s*$', timeout=120)
                summary['tests'].append(result)
                print(json.dumps(result), flush=True)
            result = run_gui(api, binary_dir, evidence)
            summary['tests'].append(result)
            print(json.dumps(result), flush=True)
        summary['passed'] = all(test['passed'] and test['executed'] and not test['cleanup_killed']
                                for test in summary['tests']) and len(summary['tests']) == (7 if args.acl else 6)
        summary['native_tests_passed'] = summary['passed']
        save_json(evidence / 'native-acceptance.json', summary)
        if not summary['passed']:
            raise RuntimeError('One or more native Windows acceptance tests failed; no portable ZIP published')
        artifact = package(binary_dir, evidence, args.mingw_root.resolve(), args.objdump, summary)
        save_json(evidence / 'portable-artifact.json', artifact)
        print(json.dumps(artifact), flush=True)
    except Exception as exc:
        summary['passed'] = False
        summary['run_error'] = str(exc)
        save_json(evidence / 'native-acceptance.json', summary)
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
