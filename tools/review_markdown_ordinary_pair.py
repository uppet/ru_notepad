#!/usr/bin/env python3
"""Six fixed ordinary-path GUI samples; never replace a timeout with a ratio."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys

ORDER = ('control', 'incremental', 'incremental', 'control', 'control', 'incremental')
CASES = ('many-lines', 'singleline', 'unclosed-fence')
OPERATIONS = ('open', 'insert', 'backspace', 'undo')
TIMEOUT_ERRORS = frozenset(('Markdown GUI open/edit exceeded its original 30-second deadline',
                           'Markdown GUI final proof exceeded its original 30-second deadline'))


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pair_proof(builds):
    receipts = {arm: json.loads((p / 'experiment-build.json').read_text(encoding='utf-8')) for arm, p in builds.items()}
    a, b = receipts['control'], receipts['incremental']
    assert a['incremental'] is False and b['incremental'] is True
    assert a['arm'] == b['arm'] == 'ordinary' and a['target'] == b['target'] == 'c-llvm'
    for key in ('source_sha256', 'compiler_input_sha256', 'manifest_sha256', 'dependencies'):
        assert a[key] == b[key], key
    x, y = [(p / 'runtime.c').read_bytes() for p in builds.values()]
    changes = [i for i, (u, v) in enumerate(zip(x, y)) if u != v]
    assert len(x) == len(y) and len(changes) == 1
    i = changes[0]
    assert x[i-7:i+2] == b'v_fact(0)' and y[i-7:i+2] == b'v_fact(1)'
    assert (builds['control'] / 'program.ll').read_bytes() == (builds['incremental'] / 'program.ll').read_bytes()
    return receipts


def classification(result):
    if result.get('passed') is True:
        cases = result['markdown_performance']['cases']
        assert [c['kind'] for c in cases] == list(CASES)
        for case in cases:
            assert [s['operation'] for s in case['stages']] == list(OPERATIONS)
            assert all(0 <= s['wall_ms'] <= 30000 for s in case['stages'])
        return 'complete'
    if result.get('error') in TIMEOUT_ERRORS:
        stages = [s for c in result.get('markdown_performance', {}).get('cases', []) for s in c.get('stages', [])]
        elapsed = stages[-1].get('wall_ms') if stages else None
        if (result.get('source_bytes_preserved') is True and result.get('executed') is True
                and not result.get('clock_error') and result.get('seconds_valid') is not False
                and isinstance(elapsed, (int, float)) and math.isfinite(elapsed) and elapsed > 30000):
            return 'original_30s_timeout'
    return 'correctness_or_other_failure'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--app-root', type=Path, required=True)
    p.add_argument('--ru-root', type=Path, required=True)
    p.add_argument('--control', type=Path, required=True)
    p.add_argument('--incremental', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    assert sys.platform == 'win32'
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    builds = {'control': args.control.resolve(), 'incremental': args.incremental.resolve()}
    receipts = pair_proof(builds)
    counts = dict.fromkeys(builds, 0); runs = []
    for arm in ORDER:
        counts[arm] += 1; name = arm + '-' + str(counts[arm]); work = out / name
        command = [sys.executable, str(args.ru_root.resolve() / 'experiments/notepad_undo/run_gui.py'),
                   '--app-root', str(args.app_root.resolve()), '--binary-dir', str(builds[arm]), '--output', str(work)]
        with (out / (name + '.log')).open('wb') as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
            try:
                process.wait(timeout=600)
            except BaseException:
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15, check=True)
                process.wait(timeout=5)
                raise
        # An infrastructure failure lacking an original-gate result is not a censored sample.
        result = json.loads((work / 'result.json').read_text(encoding='utf-8'))
        assert result['runtime_sha256']['ru_notepad.exe'] == receipts[arm]['exe_sha256'] == sha(builds[arm] / 'ru_notepad.exe')
        assert all(result['runtime_sha256'][n] == h for n, h in receipts[arm]['dependencies'].items())
        status = classification(result)
        assert (process.returncode == 0) == (status == 'complete')
        runs.append({'name': name, 'arm': arm, 'classification': status, 'result': result})
        (out / 'runs.json').write_text(json.dumps(runs, indent=2) + '\n', encoding='utf-8')
    candidate_pass = all(r['classification'] == 'complete' for r in runs if r['arm'] == 'incremental')
    baseline_valid = all(r['classification'] in ('complete', 'original_30s_timeout') for r in runs if r['arm'] == 'control')
    complete = all(r['classification'] == 'complete' for r in runs)
    comparison = []
    # No partial/censored ratios or medians, and no replacement runs.
    if complete:
        for case in CASES:
            for operation in OPERATIONS:
                row = {'case': case, 'operation': operation}
                for arm in builds:
                    values = [s['wall_ms'] for r in runs if r['arm'] == arm
                              for c in r['result']['markdown_performance']['cases'] if c['kind'] == case
                              for s in c['stages'] if s['operation'] == operation]
                    assert len(values) == 3
                    row[arm] = {'wall_ms': values, 'median_ms': statistics.median(values)}
                comparison.append(row)
    summary = {'passed': candidate_pass and baseline_valid, 'candidate_all_original_gates_passed': candidate_pass,
               'baseline_contains_only_complete_or_exact_timeout_results': baseline_valid,
               'comparison_complete': complete, 'samples_per_arm': 3, 'order': [r['name'] for r in runs],
               'original_timeout_seconds': 30, 'default_enable_decision': 'requires_review_and_full_product_acceptance',
               'statistical_significance_claim': False, 'bootstrap': False, 'full_product_acceptance': False,
               'builds': receipts, 'comparison': comparison,
               'sample_status': [{k: r[k] for k in ('name', 'arm', 'classification')} for r in runs]}
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: summary[k] for k in ('passed', 'comparison_complete', 'sample_status')}))
    raise SystemExit(0 if summary['passed'] else 1)


if __name__ == '__main__': main()
