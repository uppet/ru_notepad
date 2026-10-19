#!/usr/bin/env python3
"""Read-only Windows profiler capability check; never starts a profile or app.

The official CLI's target PID does not establish collection scope or safe
ownership after a partial session start. Until both contracts and a hotspot
export route are verified, every result is explicitly profile_unavailable.
This diagnostic never grants, replaces, or changes product acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_NAMES = ('ru_notepad.exe', 'Scintilla.dll', 'Lexilla.dll', 'RuSyntax.dll')
TOOL_NAMES = ('vswhere', 'collector', 'config')
TOTAL_SECONDS = 30
PREFLIGHT_SECONDS = 20
MAX_RUNTIME_BYTES = 64 * 1024 * 1024
MAX_OUTPUT_BYTES = 64 * 1024
REASONS = frozenset(('not_windows', 'tool_absent', 'tool_untrusted',
    'preflight_timeout', 'preflight_failed', 'preflight_invalid',
    'runtime_unavailable', 'scope_and_session_ownership_unverified',
    'path_rejected', 'private_workspace_exists', 'preflight_cleanup_unconfirmed'))
CAPABILITIES = ('vswhere_verified', 'collector_verified', 'config_read',
    'collection_scope_verified', 'session_ownership_verified',
    'unattended_hotspot_export_verified')

# Deliberately no collector invocation: only the existing signed discovery tool
# runs. No installation, security setting, application, session, or trace action.
PREFLIGHT_SCRIPT = r'''
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$result = @{ schema = 1; reason = 'preflight_failed';
    hashes = @{ vswhere = $null; collector = $null; config = $null };
    verified = @{ vswhere = $false; collector = $false; config = $false } }
function Assert-PlainFile([string]$Path, [long]$Limit) {
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    if ($item.PSIsContainer -or $item.Length -gt $Limit) { throw 'invalid_file' }
    $current = $item
    while ($null -ne $current) {
        if (($current.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw 'linked_path'
        }
        if ($current -is [IO.FileInfo]) { $current = $current.Directory }
        else { $current = $current.Parent }
    }
    return $item.FullName
}
function Test-MicrosoftSignature([string]$Path) {
    $signature = Get-AuthenticodeSignature -LiteralPath $Path
    return ($signature.Status -eq 'Valid' -and $null -ne $signature.SignerCertificate -and
        $signature.SignerCertificate.Subject -match '(^|,\s*)O=Microsoft Corporation(,|$)')
}
function Hash([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}
try {
    $vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
    if (-not (Test-Path -LiteralPath $vswhere -PathType Leaf)) {
        $result.reason = 'tool_absent'
    } else {
        $vswhere = Assert-PlainFile $vswhere 67108864
        $before = Hash $vswhere
        if (-not (Test-MicrosoftSignature $vswhere)) {
            $result.reason = 'tool_untrusted'
        } else {
            $result.hashes.vswhere = $before
            $result.verified.vswhere = $true
            $installations = @(& $vswhere -latest -products '*' -property installationPath)
            $code = $LASTEXITCODE
            if ((Hash $vswhere) -cne $before) { throw 'discovery_changed' }
            if ($code -ne 0 -or $installations.Count -eq 0) {
                $result.reason = 'tool_absent'
            } elseif ($installations.Count -ne 1) {
                throw 'ambiguous_installation'
            } else {
                $installation = [IO.Path]::GetFullPath([string]$installations[0])
                $allowed = $false
                foreach ($base in @($env:ProgramFiles, ${env:ProgramFiles(x86)})) {
                    if ($base) {
                        $prefix = [IO.Path]::GetFullPath((Join-Path $base 'Microsoft Visual Studio')) + '\'
                        if ($installation.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) { $allowed = $true }
                    }
                }
                if (-not $allowed) { throw 'unexpected_installation' }
                $collector = Join-Path $installation 'Team Tools\DiagnosticsHub\Collector\VSDiagnostics.exe'
                $config = Join-Path (Split-Path -Parent $collector) 'AgentConfigs\CPUUsageLow.json'
                if (-not (Test-Path -LiteralPath $collector -PathType Leaf) -or
                    -not (Test-Path -LiteralPath $config -PathType Leaf)) {
                    $result.reason = 'tool_absent'
                } else {
                    $collector = Assert-PlainFile $collector 67108864
                    $config = Assert-PlainFile $config 1048576
                    $before = Hash $collector
                    if (-not (Test-MicrosoftSignature $collector)) {
                        $result.reason = 'tool_untrusted'
                    } else {
                        $result.hashes.collector = $before
                        $result.verified.collector = $true
                        $null = Get-Content -LiteralPath $config -Raw | ConvertFrom-Json
                        $result.hashes.config = Hash $config
                        $result.verified.config = $true
                        if ((Hash $collector) -cne $before) { throw 'collector_changed' }
                        $result.reason = 'scope_and_session_ownership_unverified'
                    }
                }
            }
        }
    }
} catch {
    # Do not expose exception strings, paths, command output, or machine data.
    $result.reason = 'preflight_failed'
}
$result | ConvertTo-Json -Depth 4 -Compress
'''


class PreflightError(RuntimeError):
    pass


def plain_path(path, *, exists=True):
    path = Path(path).absolute()
    for item in (path, *path.parents):
        try:
            metadata = item.lstat()
        except FileNotFoundError:
            if exists and item == path:
                raise PreflightError('path_rejected')
            continue
        if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, 'st_file_attributes', 0) & 0x400:
            raise PreflightError('path_rejected')
    return path


def file_hash(path, deadline):
    path = plain_path(path)
    if not path.is_file() or path.stat().st_size > MAX_RUNTIME_BYTES:
        raise PreflightError('runtime_unavailable')
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(65536), b''):
            if time.monotonic() >= deadline:
                raise PreflightError('preflight_timeout')
            digest.update(block)
    return digest.hexdigest()


def blank_report():
    return {'schema': 1, 'status': 'profile_unavailable', 'reason': 'preflight_failed',
        'product_acceptance': 'separate_not_claimed', 'native_profile_executed': False,
        'hotspots_available': False, 'raw_trace_created': False,
        'discovery_cleanup': 'not_needed',
        'runtime_sha256': {name: None for name in RUNTIME_NAMES},
        'tool_sha256': {name: None for name in TOOL_NAMES},
        'capabilities': {name: False for name in CAPABILITIES},
        'counts': {'preflight_processes': 0, 'application_launches': 0,
                   'profiler_start_calls': 0, 'profiler_stop_calls': 0},
        'elapsed_ms': 0}


def digest_or_none(value):
    return value is None or type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def validate_report(report):
    expected = blank_report()
    if type(report) is not dict or set(report) != set(expected):
        raise PreflightError('preflight_invalid')
    for name in ('schema', 'status', 'product_acceptance', 'native_profile_executed',
                 'hotspots_available', 'raw_trace_created'):
        if type(report[name]) is not type(expected[name]) or report[name] != expected[name]:
            raise PreflightError('preflight_invalid')
    if report['reason'] not in REASONS or type(report['elapsed_ms']) is not int or not 0 <= report['elapsed_ms'] <= 120000:
        raise PreflightError('preflight_invalid')
    if report['discovery_cleanup'] not in ('not_needed', 'confirmed', 'unconfirmed'):
        raise PreflightError('preflight_invalid')
    if (report['discovery_cleanup'] == 'unconfirmed') != (report['reason'] == 'preflight_cleanup_unconfirmed'):
        raise PreflightError('preflight_invalid')
    for field, names in (('runtime_sha256', RUNTIME_NAMES), ('tool_sha256', TOOL_NAMES)):
        if type(report[field]) is not dict or set(report[field]) != set(names) or not all(map(digest_or_none, report[field].values())):
            raise PreflightError('preflight_invalid')
    caps, counts = report['capabilities'], report['counts']
    if type(caps) is not dict or set(caps) != set(CAPABILITIES) or any(type(x) is not bool for x in caps.values()):
        raise PreflightError('preflight_invalid')
    if any(caps[name] for name in CAPABILITIES[3:]):
        raise PreflightError('preflight_invalid')
    if (caps['collector_verified'] and not caps['vswhere_verified'] or
            caps['config_read'] and not caps['collector_verified'] or
            report['reason'] == 'scope_and_session_ownership_unverified' and
            not all(caps[name] for name in CAPABILITIES[:3])):
        raise PreflightError('preflight_invalid')
    if type(counts) is not dict or set(counts) != set(expected['counts']) or any(type(x) is not int for x in counts.values()):
        raise PreflightError('preflight_invalid')
    if counts['preflight_processes'] not in (0, 1) or any(counts[name] != 0 for name in counts if name != 'preflight_processes'):
        raise PreflightError('preflight_invalid')
    for capability, tool in zip(CAPABILITIES[:3], TOOL_NAMES):
        if caps[capability] != (report['tool_sha256'][tool] is not None):
            raise PreflightError('preflight_invalid')
    return report


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise PreflightError('preflight_invalid')
            result[key] = value
        return result
    try:
        return json.loads(text, object_pairs_hook=pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(PreflightError('preflight_invalid')))
    except (ValueError, TypeError) as exc:
        raise PreflightError('preflight_invalid') from exc


def apply_preflight(report, raw):
    if (type(raw) is not dict or set(raw) != {'schema', 'reason', 'hashes', 'verified'} or
            type(raw['schema']) is not int or raw['schema'] != 1 or
            raw['reason'] not in {'tool_absent', 'tool_untrusted', 'preflight_failed',
                                  'scope_and_session_ownership_unverified'}):
        raise PreflightError('preflight_invalid')
    hashes, verified = raw['hashes'], raw['verified']
    if (type(hashes) is not dict or set(hashes) != set(TOOL_NAMES) or
            not all(map(digest_or_none, hashes.values())) or type(verified) is not dict or
            set(verified) != set(TOOL_NAMES) or any(type(x) is not bool for x in verified.values()) or
            any(verified[name] != (hashes[name] is not None) for name in TOOL_NAMES)):
        raise PreflightError('preflight_invalid')
    if raw['reason'] == 'scope_and_session_ownership_unverified' and not all(verified.values()):
        raise PreflightError('preflight_invalid')
    if verified['collector'] and not verified['vswhere'] or verified['config'] and not verified['collector']:
        raise PreflightError('preflight_invalid')
    report['reason'] = raw['reason']
    report['tool_sha256'] = hashes.copy()
    for capability, tool in zip(CAPABILITIES[:3], TOOL_NAMES):
        report['capabilities'][capability] = verified[tool]


def invoke_preflight(private, deadline, report):
    if time.monotonic() >= deadline - 5:
        raise PreflightError('preflight_timeout')
    system = plain_path(Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe')
    output, error = private / 'preflight.stdout.json', private / 'preflight.stderr.log'
    process = None
    try:
        with output.open('xb') as stdout, error.open('xb') as stderr:
            process = subprocess.Popen([str(system), '-NoLogo', '-NoProfile', '-NonInteractive',
                '-Command', PREFLIGHT_SCRIPT], cwd=private, stdin=subprocess.DEVNULL,
                stdout=stdout, stderr=stderr)
            report['counts']['preflight_processes'] = 1
            limit = min(deadline - 5, time.monotonic() + PREFLIGHT_SECONDS)
            while process.poll() is None:
                if time.monotonic() >= limit:
                    raise PreflightError('preflight_timeout')
                if any(path.stat().st_size > MAX_OUTPUT_BYTES for path in (output, error)):
                    raise PreflightError('preflight_invalid')
                time.sleep(0.05)
            if process.returncode != 0:
                raise PreflightError('preflight_failed')
        if any(path.stat().st_size > MAX_OUTPUT_BYTES for path in (output, error)):
            raise PreflightError('preflight_invalid')
        return strict_json(output.read_text(encoding='utf-8-sig'))
    finally:
        if process is not None and process.poll() is None:
            # Only this freshly launched, read-only discovery subprocess tree.
            tree_terminated = False
            try:
                cleanup = subprocess.run([str(Path(os.environ['SystemRoot']) / 'System32/taskkill.exe'),
                    '/PID', str(process.pid), '/T', '/F'], stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3)
                tree_terminated = cleanup.returncode == 0
            except (OSError, subprocess.TimeoutExpired):
                pass
            try:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired):
                tree_terminated = False
            report['discovery_cleanup'] = 'confirmed' if tree_terminated else 'unconfirmed'
            if not tree_terminated:
                raise PreflightError('preflight_cleanup_unconfirmed')


def run(runtime_dir, output, *, root=ROOT):
    started = time.monotonic()
    deadline = started + TOTAL_SECONDS
    report = blank_report()
    root = plain_path(root)
    expected = root / 'build/windows-ci/evidence/markdown-cpu-profile.json'
    output = plain_path(output, exists=False)
    if output != expected:
        raise PreflightError('path_rejected')
    output.parent.mkdir(parents=True, exist_ok=True)
    # Reserve this run's public file before launching anything. Retain the same
    # exclusive descriptor; never replace a prior report or follow a new link.
    with output.open('x', encoding='utf-8') as stream:
        owned = os.fstat(stream.fileno())
        try:
            if sys.platform != 'win32':
                report['reason'] = 'not_windows'
            else:
                runtime = plain_path(runtime_dir)
                if runtime != root / 'build/windows-ci/bin':
                    raise PreflightError('path_rejected')
                for name in RUNTIME_NAMES:
                    report['runtime_sha256'][name] = file_hash(runtime / name, deadline)
                private = plain_path(root / 'build/windows-ci/private-cpu-profile', exists=False)
                if private.exists():
                    raise PreflightError('private_workspace_exists')
                private.mkdir()
                apply_preflight(report, invoke_preflight(private, deadline, report))
        except PreflightError as exc:
            report['reason'] = str(exc) if str(exc) in REASONS else 'preflight_failed'
        except Exception:
            report['reason'] = 'preflight_failed'
        report['elapsed_ms'] = round((time.monotonic() - started) * 1000)
        if report['elapsed_ms'] >= TOTAL_SECONDS * 1000 and report['discovery_cleanup'] != 'unconfirmed':
            report['reason'] = 'preflight_timeout'
        validate_report(report)
        current = plain_path(output).stat()
        if (current.st_dev, current.st_ino) != (owned.st_dev, owned.st_ino):
            raise PreflightError('path_rejected')
        json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        report = run(args.runtime_dir, args.output)
    except Exception:
        # A diagnostic write failure must not leak paths or mask acceptance.
        print('MARKDOWN_CPU_PROFILE_REPORT_UNAVAILABLE')
        return 0
    print(json.dumps(report, sort_keys=True, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
