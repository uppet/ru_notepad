#!/usr/bin/env python3
"""Source/tool/runtime-bound Windows directory transport gate.

The production DLL is never rebuilt here. Only the test host and an isolated,
non-shipped fault-injection DLL are compiled using the locked dependency tool.
"""
import json
from pathlib import Path
import subprocess
import sys

from bootstrap_provenance import require, sha
from build_bootstrap_release import identity
from prepare_bootstrap_dependencies import dependency_environment, validate_tools
import test_directory_io as suite

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'ru-notepad-directory-io-windows-v1'
INPUTS = ('native/ru_directory_io.c', 'native/ru_directory_io.h',
          'tests/directory_io_host.c', 'tests/directory_io_faults.h',
          'tools/test_directory_io.py', 'tools/verify_directory_io_windows.py')
LIMITATIONS = [
    'Controlled read stall is not a real kernel/device hang.',
    'Remote/offline/recall tests inject OS-call outcomes; no real cloud hydration or network provider is exercised.',
    'Ancestor swaps exercise concurrent races but do not claim exhaustive scheduling or mapped-writer snapshot immutability.',
]


def validate_result(report, hashes):
    require(isinstance(report, dict) and report.get('schema') == SCHEMA
            and report.get('status') == 'passed' and report.get('platform') == 'win32',
            'directory I/O Windows evidence not passed')
    require(report.get('runtime_sha256') == hashes, 'directory I/O used different runtime')
    require(report.get('source_sha256') == {name: sha(ROOT/name) for name in INPUTS},
            'directory I/O test/source inputs changed')
    require(report.get('fault_dll_shipped') is False, 'fault injection DLL must not ship')
    for name in ('compiler', 'host', 'fault_dll', 'suite_receipt'):
        record = report.get(name)
        require(isinstance(record, dict) and identity(record['path']) == record,
                'directory I/O evidence file changed: '+name)
    result = json.loads(Path(report['suite_receipt']['path']).read_text(encoding='utf-8'))
    require(result == report.get('result'), 'directory I/O suite receipt changed')
    require(result.get('status') == 'pass' and result.get('skipped') == []
            and not result.get('error'), 'directory I/O case failed/skipped')
    require(result.get('required_case_ids') == list(suite.REQUIRED_CASE_IDS)
            and result.get('cases') == [{'id': name, 'status': 'pass'} for name in suite.REQUIRED_CASE_IDS],
            'directory I/O exact case inventory differs')
    require(result.get('limitations') == LIMITATIONS, 'directory I/O coverage limitation omitted')
    require(isinstance(result.get('invocations'), list) and result['invocations'],
            'directory I/O process observations missing')
    require(all(type(row.get('returncode')) is int and row.get('status') != 'timeout'
                and isinstance(row.get('stdout'), str) and isinstance(row.get('stderr'), str)
                for row in result['invocations']), 'directory I/O invocation incomplete')
    builds = report.get('builds')
    require(isinstance(builds, list) and len(builds) == 2, 'directory I/O host/fault builds missing')
    for row, name in zip(builds, ('host', 'fault_dll')):
        require(row.get('returncode') == 0 and row.get('timeout') is False
                and row.get('command') == command_for(name, report['compiler']['path'], report[name]['path']),
                'directory I/O test build differs')
        for key in ('stdout', 'stderr'):
            record = row[key]
            require(identity(record['path']) == record, 'directory I/O compiler log changed')
    return report


def command_for(name, cc, output):
    common = [str(cc), '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror']
    if name == 'host':
        return common+['-municode', str(ROOT/'tests/directory_io_host.c'), '-o', str(output)]
    require(name == 'fault_dll', 'unknown directory test build')
    return common+['-shared', '-DRU_DIR_TESTING', str(ROOT/'native/ru_directory_io.c'),
                   '-lshell32', '-lole32', '-o', str(output)]


def run(runtime, evidence, dependencies):
    require(sys.platform == 'win32', 'directory I/O requires actual Windows execution')
    runtime, evidence = Path(runtime), Path(evidence)/'directory-io'
    require(not evidence.exists(), 'fresh directory I/O evidence required')
    evidence.mkdir()
    validate_tools(dependencies['tool_paths'], dependencies['tool_sha256'])
    cc = dependencies['tool_paths']['cc']
    import os
    environment = dependency_environment(dependencies['tool_paths'], os.environ)
    from package import RUNTIME_NAMES
    hashes = {name: sha(runtime/name) for name in RUNTIME_NAMES}
    sources = {name: sha(ROOT/name) for name in INPUTS}
    record = {'schema': SCHEMA, 'status': 'failed', 'platform': sys.platform,
              'runtime_sha256': hashes, 'source_sha256': sources,
              'compiler': identity(cc), 'fault_dll_shipped': False, 'builds': []}
    def save():
        (evidence/'receipt.json').write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
    save()
    try:
        for name, filename in (('host','directory-host.exe'), ('fault_dll','directory-fault.dll')):
            output = evidence/filename
            command = command_for(name, cc, output)
            stdout, stderr = evidence/(name+'.stdout'), evidence/(name+'.stderr')
            row = {'command': command, 'returncode': None, 'timeout': False}
            record['builds'].append(row)
            with stdout.open('wb') as out, stderr.open('wb') as err:
                try:
                    process = subprocess.run(command, cwd=ROOT, env=environment,
                                             stdout=out, stderr=err, timeout=120)
                    row['returncode'] = process.returncode
                except subprocess.TimeoutExpired:
                    row['timeout'] = True
                    raise
                finally:
                    row['stdout'], row['stderr'] = identity(stdout), identity(stderr)
            require(process.returncode == 0, 'directory test build failed: '+name)
            record[name] = identity(output)
            save()
        suite_path = evidence/'suite.json'
        record['result'] = suite.run_windows(runtime/'RuSyntax.dll', record['host']['path'],
                                            record['fault_dll']['path'], suite_path)
        record['suite_receipt'] = identity(suite_path)
        require(sources == {name: sha(ROOT/name) for name in INPUTS}, 'directory inputs changed during test')
        require(hashes == {name: sha(runtime/name) for name in RUNTIME_NAMES}, 'runtime changed during directory test')
        validate_tools(dependencies['tool_paths'], dependencies['tool_sha256'])
        record['status'] = 'passed'
        validate_result(record, hashes)
    except Exception as error:
        record['status'] = 'failed'
        record['error'] = str(error)
    save()
    return record
