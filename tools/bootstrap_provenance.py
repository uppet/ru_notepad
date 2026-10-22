"""Read-only bootstrap evidence validation. NOT an editor build/release entry point.

Reports are evidence, not signed attestations. The caller must independently pin
and trust the source commit and acquisition of these artifacts. Never execute
code from a report or accept a report's boolean instead of checking its files.
"""
import ast
import hashlib
import json
from pathlib import Path, PureWindowsPath
import re
import struct
import subprocess


class InvalidProvenance(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise InvalidProvenance(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked(root, relative):
    path = Path(relative)
    require(not path.is_absolute() and not PureWindowsPath(relative).is_absolute()
            and '..' not in path.parts and '\\' not in relative, 'unsafe relative input')
    result = root / path
    require(not any(p.is_symlink() for p in [result, *result.parents]), 'linked input')
    require(result.is_file(), 'missing input: ' + relative)
    return result


def expected_cases(root):
    module = ast.parse(checked(root, 'tests/test_bootstrap.py').read_text(encoding='utf-8'))
    base = next(n for n in module.body if isinstance(n, ast.ClassDef) and n.name == 'BootstrapTests')
    cases = [n.name for n in base.body if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')]
    practical = json.loads(checked(root, 'bootstrap/validation/practical.json').read_text(encoding='utf-8'))
    cases += ['test_practical_' + item['name'] for item in practical]
    require(len(cases) >= 35 and len(set(cases)) == len(cases), 'incomplete or duplicate pinned suite')
    return sorted(cases)


def source_inputs(root):
    paths = [p for p in (root / 'rulang').rglob('*') if p.suffix in ('.py', '.h', '.ru')]
    paths += list((root / 'bootstrap').rglob('*.ru'))
    paths += list((root / 'bootstrap/validation').glob('*.json'))
    paths += list((root / 'tools').glob('bootstrap*.py'))
    paths += [root / 'tests/test_bootstrap.py']
    return {p.relative_to(root).as_posix(): sha(checked(root, p.relative_to(root).as_posix())) for p in paths}


def validate_suite(report, cases):
    gates = {'source_ir_and_abi_fixed_point', 'native_binary_fixed_point',
             'same_nonempty_suite_for_each_stage', 'every_planned_case_ran',
             'every_case_passed_without_skips', 'test_runner_success_without_skips',
             'inputs_unchanged', 'artifacts_unchanged_during_tests'}
    require(report.get('format') == 1 and report.get('milestone') == 'M4', 'unsupported verification format')
    require(report.get('m4_complete') is True and set(report.get('gates', {})) == gates
            and all(v is True for v in report['gates'].values()), 'verification gates failed')
    require(report.get('tests_run') == 3 * len(cases), 'incorrect total test count')
    require(all(type(report.get(k)) is int and report[k] == 0 for k in ('failures', 'errors', 'skipped')), 'failed or skipped tests')
    require(set(report.get('planned_cases_by_stage', {})) == {'1', '2', '3'}
            and set(report.get('stages', {})) == {'1', '2', '3'}, 'missing stage')
    ids = set()
    for stage in ('1', '2', '3'):
        require(report['planned_cases_by_stage'][stage] == cases, 'suite differs from pinned source')
        rows = report['stages'][stage]
        require(sorted(row.get('case', '') for row in rows) == cases, 'missing/duplicate test case')
        for row in rows:
            require(type(row.get('stage')) is int and row['stage'] == int(stage)
                    and row.get('status') == 'passed', 'invalid stage result')
            require(isinstance(row.get('id'), str) and row['id'] not in ids, 'duplicate or missing test identity')
            ids.add(row['id'])


def artifact_files(report, directory):
    names = {'stage1.exe', 'stage2.exe', 'stage3.exe', 'stage2.ll', 'stage3.ll'}
    names |= {f'stage{i}.exe.{suffix}' for i in (2, 3) for suffix in ('frontend.ll', 'metadata.c')}
    found = {}
    # The upstream v1 format records host absolute paths. Map only the exact
    # nine allowed basenames; reject collisions rather than trusting their path.
    for original, digest in report.get('artifact_sha256', {}).items():
        name = PureWindowsPath(original).name
        require(name in names and name not in found, 'unknown or colliding artifact')
        path = checked(directory, name)
        require(sha(path) == digest, 'artifact hash mismatch: ' + name)
        found[name] = path
    require(set(found) == names, 'incomplete stage artifacts')
    for name in ('stage1.exe', 'stage2.exe', 'stage3.exe'):
        content = found[name].read_bytes()
        require(content[:2] == b'MZ' and len(content) >= 64, 'not Windows PE')
        offset = struct.unpack_from('<I', content, 60)[0]
        require(offset + 26 <= len(content) and content[offset:offset+4] == b'PE\0\0', 'invalid PE')
        require(struct.unpack_from('<H', content, offset+4)[0] == 0x8664
                and struct.unpack_from('<H', content, offset+24)[0] == 0x20b, 'not Windows x64 PE32+')
    return found


def validate_toolchain(tool_paths, expected_hashes):
    """Verify independently acquired tool hashes, not hashes claimed by a report.

    Version/triple/layout probes belong to the forthcoming build driver; hashes
    alone neither execute a probe nor establish availability of Windows SDK libs.
    """
    names = {'clang', 'llvm-as', 'llvm-link', 'opt', 'llvm-dis', 'llc', 'linker', 'resource-compiler'}
    require(set(tool_paths) == names and set(expected_hashes) == names, 'incomplete toolchain identity')
    for name in names:
        path = Path(tool_paths[name])
        require(path.is_file() and not any(p.is_symlink() for p in [path, *path.parents]), 'missing or linked tool')
        require(re.fullmatch('[0-9a-f]{64}', expected_hashes[name]) is not None
                and sha(path) == expected_hashes[name], 'tool hash mismatch: ' + name)
    return dict(expected_hashes)


def validate(root, directory, report_path, expected_commit, expected_tree, compare_native,
             *, expected_triple, expected_data_layout):
    """compare_native must be an independently trusted upstream comparator.

    The release caller, not report content, supplies this function. This module
    intentionally does not import or execute a compiler from an evidence bundle.
    """
    root, directory, report_path = map(Path, (root, directory, report_path))
    def git(*args):
        return subprocess.check_output(['git', '-C', str(root), *args], text=True, encoding='utf-8').strip()
    require(re.fullmatch('[0-9a-f]{40}', expected_commit) is not None
            and re.fullmatch('[0-9a-f]{40}', expected_tree) is not None, 'full source pins required')
    require(git('rev-parse', 'HEAD') == expected_commit and git('rev-parse', 'HEAD^{tree}') == expected_tree, 'source pin mismatch')
    require(not git('status', '--porcelain'), 'dirty source checkout')
    tracked = set(git('ls-files', '-z').split('\0'))
    require(set(source_inputs(root)) <= tracked, 'untracked or ignored executable source input')
    require(not report_path.is_symlink(), 'linked verification report')
    report_bytes = report_path.read_bytes()
    report = json.loads(report_bytes)
    validate_suite(report, expected_cases(root))
    require(report.get('platform') == 'win32', 'wrong report platform')
    require(report.get('input_sha256') == source_inputs(root), 'source input inventory mismatch')
    cycle = report.get('bootstrap', {})
    require(cycle.get('platform') == 'win32' and cycle.get('fixed_point') is True, 'wrong bootstrap platform/fixed point')
    triple = cycle.get('triple', '')
    require(re.fullmatch(r'x86_64-[\w.-]*windows-msvc[\w.-]*', triple) is not None, 'wrong target ABI')
    require(triple == expected_triple and bool(expected_data_layout), 'target differs from trusted toolchain probe')
    require(re.match(r'clang version 14\.', cycle.get('llvm', '')) is not None, 'wrong LLVM version')
    require(cycle.get('source_sha256') == sha(root / 'bootstrap/compiler.ru'), 'compiler source hash mismatch')
    files = artifact_files(report, directory)
    for name in ('stage2.ll', 'stage3.ll', 'stage2.exe.frontend.ll', 'stage3.exe.frontend.ll'):
        ir = files[name].read_text(encoding='utf-8')
        require(re.findall(r'^target triple = "([^"]+)"', ir, re.M) == [expected_triple]
                and re.findall(r'^target datalayout = "([^"]+)"', ir, re.M) == [expected_data_layout],
                'artifact target triple/data layout mismatch: ' + name)
    stages = cycle.get('stages', [])
    require(len(stages) == 2, 'missing bootstrap generation')
    for i, stage in zip((2, 3), stages):
        for key, name in [('source_ir_sha256', f'stage{i}.exe.frontend.ll'),
                          ('metadata_sha256', f'stage{i}.exe.metadata.c'), ('binary_sha256', f'stage{i}.exe')]:
            require(stage.get(key) == sha(files[name]), 'generation hash mismatch')
    for suffix in ('frontend.ll', 'metadata.c'):
        require(files[f'stage2.exe.{suffix}'].read_bytes() == files[f'stage3.exe.{suffix}'].read_bytes(), 'IR/ABI fixed point mismatch')
    comparison = compare_native(files['stage2.exe'].read_bytes(), files['stage3.exe'].read_bytes())
    require(comparison.get('normalized_equal') is True and report.get('native_comparison') == comparison, 'native fixed point mismatch')
    require(report_path.read_bytes() == report_bytes and report.get('input_sha256') == source_inputs(root), 'inputs changed during validation')
    artifact_files(report, directory)
    require(git('rev-parse', 'HEAD') == expected_commit and git('rev-parse', 'HEAD^{tree}') == expected_tree
            and not git('status', '--porcelain'), 'source checkout changed during validation')
    return {'status': 'bootstrap-evidence-validated-not-editor-build', 'ru_commit': expected_commit,
            'ru_tree': expected_tree, 'stage3_sha256': sha(files['stage3.exe']),
            'verification_sha256': hashlib.sha256(report_bytes).hexdigest(), 'target_triple': triple,
            'data_layout': expected_data_layout, 'tests_run': report['tests_run']}
