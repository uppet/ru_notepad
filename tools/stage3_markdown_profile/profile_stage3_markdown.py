"""Fixed pure-policy stage3 diagnostic. Not GUI acceptance or a compiler fallback.

The caller compiles both generated entries with the reviewed native wrapper and
validates its exact compiler/tool/source/proof identities BEFORE measure(). This
module does not compile or infer acceptance from process output.
"""
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

POLICY_SHA = '940c13d2be718f00e4b471d7389bb5f57cb10b714de8e610e0eaf0f3f116f782'
INPUT_SHA = '2d9f79ee715b217c00792cf18a67485cdec96a14ea2ac86689156941a022c719'
ORDER = ('policy', 'control', 'policy', 'control', 'policy', 'control')
PROCESS_TIMEOUT = 60  # Diagnostic process bound, NOT a change to GUI's 30 seconds.
SOURCE_NAMES = ('markdown_policy.ru', 'policy.ru', 'control.ru')
SCHEMA = 'ru-notepad-stage3-markdown-diagnostic-v1'


def digest(data): return hashlib.sha256(data).hexdigest()


def identity(path):
    path = Path(path)
    if not path.is_file() or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('missing or linked diagnostic file')
    return {'path': str(path.resolve()), 'sha256': digest(path.read_bytes()), 'size': path.stat().st_size}


def fixture():
    head, tail, fill = b'# Heading\n\n~~~\n', b'codebody', b'code text\n'
    count = 1000000 - len(head) - len(tail)
    data = head + (fill * (count // len(fill) + 1))[:count] + tail
    if digest(data) != INPUT_SHA or len(data) != 1000000:
        raise ValueError('original fixture changed')
    return data


CONTROL_BODY = """
总 取 0. 校 取 0. 位 取 0.
循 序们 其 量 次
    文 取 块们[序们[位]].
    总 取 总+文 其 量.
    校 取 (校*31+文 其 量)%1000000007.
    位 取 位+1.
环
若 总 != 1000000 或 位 != 977 则 卒 'control input mismatch'. 然
显 'CONTROL bytes='+(总 为 句)+' scalars='+(总 为 句)+' chunks='+(位 为 句)+' checksum='+(校 为 句).
"""

POLICY_BODY = "态 取 模 其 新状态. 序位 取 0. 校 取 0. 批数 取 0. 早 取 0.\n循 序们 其 量 次\n    文 取 块们[序们[序位]]. 位 取 0.\n    循\n        入 取 文[位:]. 果 取 模 其 喂入 态 入 (序位+1 == 序们 其 量).\n        列 取 果['folds']. 行 取 0.\n        循 列 其 量 次\n            项 取 列[行]. 头 取 0. 若 项[3] 则 头 取 1. 然\n            校 取 (校*31+项[0]*7+项[1]*11+项[2]*13+头)%1000000007.\n            行 取 行+1.\n        环\n        批数 取 批数+1.\n        若 果['used'] < 入 其 量 则 早 取 早+1. 然\n        位 取 位+果['used'].\n        若 位 == 文 其 量 则 破. 然\n        若 果['used'] == 0 且 列 其 量 == 0 则 卒 'no progress'. 然\n    环\n    序位 取 序位+1.\n环\n若 非 态[2] 或 态[23] != 1000000 则 卒 'not complete'. 然\n显 'checksum='+ (校 为 句)+' batches='+(批数 为 句)+' early='+(早 为 句).\n项 取 0.\n循 24 次\n    若 项 == 3 则\n        栈 取 态[3]. 显 'stack='+(栈 其 量 为 句). 层 取 0.\n        循 栈 其 量 次\n            格 取 0. 循 4 次 显 栈[层][格]. 格 取 格+1. 环\n            层 取 层+1.\n        环\n    另\n        若 项 == 19 则\n            格 取 0. 循 5 次 显 态[19][格]. 格 取 格+1. 环\n        另\n            显 态[项].\n        然\n    然\n    项 取 项+1.\n环\n"
POLICY_EXPECTED = 'checksum=290728946 batches=977 early=0\n100000\n假\n真\nstack=1\n1\n0\n0\n真\n-1\n假\n~\n3\n\n0\n假\ncode tecodebody\n15\nc\n1\n真\n假\n假\n tecodebody\n假\n假\n假\n假\n假\n真\n假\n假\n1000000\n'


def generated_entries():
    data = fixture()
    chunks = [data[i:i+1024].decode('ascii') for i in range(0, len(data), 1024)]
    unique = list(dict.fromkeys(chunks))
    indices = [unique.index(c) for c in chunks]
    # Same literal input, module initialization and chunk lookup for both entries.
    shared = "模 取 外言 'markdown_policy.ru'.\n块们 取 [" + ','.join(repr(c) for c in unique) + "].\n序们 取 " + str(indices) + ".\n"
    return {'policy.ru': shared + POLICY_BODY, 'control.ru': shared + CONTROL_BODY}


def expected_output(kind):
    if kind == 'policy': return POLICY_EXPECTED.encode('utf-8')
    if kind != 'control': raise ValueError('unknown scenario')
    data = fixture(); checksum = 0
    for i in range(0, len(data), 1024): checksum = (checksum * 31 + len(data[i:i+1024])) % 1000000007
    return f'CONTROL bytes=1000000 scalars=1000000 chunks=977 checksum={checksum}\n'.encode('ascii')


def prepare(policy, output):
    output = Path(output)
    record = identity(policy)
    if record['sha256'] != POLICY_SHA: raise ValueError('policy is not exact 940c baseline')
    output.mkdir(parents=True, exist_ok=False)
    (output/'markdown_policy.ru').write_bytes(Path(policy).read_bytes())
    for name, content in generated_entries().items():
        (output/name).write_text(content, encoding='utf-8', newline='\n')
    records = validate_sources(output)
    manifest = {'schema': SCHEMA, 'status': 'NOT_ACCEPTED', 'accepted': False,
                'input_sha256': INPUT_SHA, 'input_bytes': 1000000, 'feed_limit': 1024,
                'chunks': 977, 'sources': records,
                'expected_stdout_sha256': {k:digest(expected_output(k)) for k in ('policy','control')}}
    (output/'prepared.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    return manifest


def validate_sources(directory):
    directory = Path(directory)
    records = {name:identity(directory/name) for name in SOURCE_NAMES}
    if records['markdown_policy.ru']['sha256'] != POLICY_SHA:
        raise ValueError('production policy bytes changed')
    for name, content in generated_entries().items():
        if (directory/name).read_bytes() != content.encode('utf-8'):
            raise ValueError('generated harness bytes changed')
    return records


def validate_output(kind, stdout, stderr, returncode):
    if returncode != 0 or stderr or len(stdout) > 65536:
        raise ValueError('diagnostic process failed or output exceeded bound')
    # Windows stdout can use CRLF. No other whitespace/content normalization.
    if stdout.replace(b'\r\n', b'\n') != expected_output(kind):
        raise ValueError('full independent expected output mismatch')


def process_cpu(process):
    # Popen retains this owned handle after wait. Never reopen or close it here.
    try:
        if sys.platform != 'win32' or not getattr(process, '_handle', None):
            raise RuntimeError('owned Windows process handle required')
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        query = kernel.GetProcessTimes
        query.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
        query.restype = wintypes.BOOL
        values = [wintypes.FILETIME() for _ in range(4)]
        if not query(int(process._handle), *(ctypes.byref(v) for v in values)):
            raise RuntimeError('GetProcessTimes unavailable')
        ticks = lambda value: (int(value.dwHighDateTime) << 32) | int(value.dwLowDateTime)
        k, u = ticks(values[2]), ticks(values[3])
        return {'available': True, 'kernel_100ns': k, 'user_100ns': u, 'total_cpu_ms': (k+u)/10000}
    except Exception as exc:
        return {'available': False, 'error_type': type(exc).__name__}


def run_one(kind, binary, directory):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=False)
    stdout_path, stderr_path = directory/'stdout.log', directory/'stderr.log'
    env = {k:v for k,v in os.environ.items() if k.upper() not in ('GH_TOKEN','GITHUB_TOKEN')}
    record = {'kind': kind, 'completed': False, 'validated': False, 'timeout_seconds': PROCESS_TIMEOUT}
    start = time.perf_counter(); process = None
    try:
        with stdout_path.open('xb') as out, stderr_path.open('xb') as err:
            process = subprocess.Popen([str(binary)], cwd=str(directory), env=env, stdout=out, stderr=err)
            try:
                process.wait(timeout=PROCESS_TIMEOUT)
                record['completed'] = True
            except subprocess.TimeoutExpired:
                record['timed_out'] = True
                process.kill(); process.wait(timeout=5)
            record['wall_seconds'] = time.perf_counter()-start
            record['cpu'] = process_cpu(process)
            record['returncode'] = process.returncode
        record['stdout_size'] = stdout_path.stat().st_size
        record['stderr_size'] = stderr_path.stat().st_size
        if record['stdout_size'] > 65536 or record['stderr_size'] > 65536:
            raise ValueError('diagnostic output exceeds bound')
        record['stdout'] = identity(stdout_path); record['stderr'] = identity(stderr_path)
        if not record['completed']: raise RuntimeError('diagnostic process timeout')
        validate_output(kind, stdout_path.read_bytes(), stderr_path.read_bytes(), process.returncode)
        record['validated'] = True
    except Exception as exc:
        record['error_type'] = type(exc).__name__
    finally:
        if process is not None and process.poll() is None:
            process.kill(); process.wait(timeout=5)
    return record


def measure(prepared, binaries, evidence, build_evidence):
    if sys.platform != 'win32': raise RuntimeError('actual Windows required for stage3 measurement')
    if set(binaries) != {'policy','control'} or set(build_evidence) != {'policy','control'}:
        raise ValueError('exact two prevalidated build records required')
    # Caller records the actual strong build validation; this is not a substitute.
    for kind in binaries:
        if build_evidence[kind].get('binary') != identity(binaries[kind]):
            raise ValueError('prevalidated binary identity mismatch')
        if build_evidence[kind].get('native_wrapper_validated') is not True:
            raise ValueError('caller native wrapper validation required')
    evidence = Path(evidence); evidence.mkdir(parents=True, exist_ok=False)
    sources = validate_sources(prepared)
    before = {k:identity(v) for k,v in binaries.items()}
    report = {'schema': SCHEMA, 'status': 'NOT_ACCEPTED', 'accepted': False,
              'diagnostic_completed': False, 'all_outputs_validated': False,
              'fixed_order': list(ORDER), 'process_timeout_seconds': PROCESS_TIMEOUT,
              'scope': 'Fresh process full policy versus startup/input control, no per-line timers. Not GUI acceptance. Do not subtract control or another GUI process to attribute precise parser/GUI costs.',
              'timing_scope': 'Process startup, input initialization, execution and stdout/exit. CPU is whole-process kernel+user via retained owned handle; unavailable is not zero. Compilation must be complete and no other task load running before this function.',
              'sources': sources, 'binaries': before, 'build_evidence': build_evidence, 'runs': []}
    try:
        for index, kind in enumerate(ORDER):
            if validate_sources(prepared) != sources or {k:identity(v) for k,v in binaries.items()} != before:
                raise ValueError('source/binary identity drift before sample')
            row = run_one(kind, Path(binaries[kind]).resolve(), evidence/f'{index+1}-{kind}')
            report['runs'].append(row)
            if not row['validated']: raise RuntimeError('sample failed; no replacement or extra sample')
        report['diagnostic_completed'] = True
        report['all_outputs_validated'] = True
    except Exception as exc:
        report['error_type'] = type(exc).__name__
    finally:
        try:
            report['sources_unchanged'] = validate_sources(prepared) == sources
            report['binaries_unchanged'] = {k:identity(v) for k,v in binaries.items()} == before
        except Exception:
            report['sources_unchanged'] = False; report['binaries_unchanged'] = False
        if not report['sources_unchanged'] or not report['binaries_unchanged']:
            report['diagnostic_completed'] = False; report['all_outputs_validated'] = False
            report['error_type'] = 'IdentityDrift'
        (evidence/'diagnostic.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    return report
