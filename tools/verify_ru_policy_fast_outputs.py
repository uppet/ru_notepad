#!/usr/bin/env python3
"""Verify full local execution, then expose a bounded read-only public receipt gate.

The public validator reads exactly eight files. It does not execute tests, replace
local artifact checks, or accept a report without the complete ordered raw output.
"""
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import stat
import traceback
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'build/policy-fast'
BASE_COMMIT = 'a5f5fd825767cd5af662cba792f5ce352991c21e'
BASE_TREE = 'e8a402fb3eb551bfe416b8aee0aaaf942d2d4f4a'
BASE_POLICY_BLOB = '876a99f76db706cfd76427b9341ee5f05180ce0d'
BASE_SOURCE_SHA256 = 'f78589e247186890855526f7bb3624d34e4004bb8fbc69587c96d38c826a602c'
GRAMMAR_ADAPTATION = 'ru-0.23.0-elif-v1'
ADAPTED_BASE_SOURCE_SHA256 = '1887d1daceeb71f6c046c962142ef1b99ffe3a0b73770686dd4f9b3025e9b8ae'
RU_COMMIT = '85c7821fda35aa79deeaf67b4d430f24ddd7f07f'
RU_TREE = 'a770e367e84d87a0d2fcb6d49ea6f06da2dbe4ba'
CANONICAL_PLAN_SHA256 = 'a712c3b5c70e5bfe4ae09900d928f594c2c88bb49448d40ca15422b09a015e90'
PLAN_CONTENT_SHA256 = '0183679cfac0583d3a160e7ab7549967fe6b53b87b605647f2da3ce09c171616'
TOTALS = {'cases':196,'batches':19627,'events':2554,'context_transitions':21504}
SCOPE = 'Actual interpreter and ordinary generated host C, with the same explicit Ru 0.23.0 elif grammar adaptation on the historical baseline. Not the original historical baseline output; no Windows/GUI speed claim.'
LOG_NAMES = ('interpreter.log',)+tuple(f'host-c-{i}.log' for i in range(4))
PUBLIC_FILE_LIMITS = {'report.json':64*1024,'fixture-manifest.json':256*1024,
                      'ordered-output-validation.json':16*1024,
                      **{name:64*1024 for name in LOG_NAMES}}
EXPECTED_INPUT_KEYS = frozenset(('baseline_commit','baseline_tree','baseline_source_sha256',
    'toolchain_commit','toolchain_tree','candidate_sha256','test_script_sha256',
    'verifier_source_sha256','canonical_plan_sha256'))
REPORT_KEYS = frozenset(('schema_version','status','grammar_adaptation','baseline_adapted_source_sha256','baseline_commit','baseline_tree','baseline_policy_blob',
    'toolchain_commit','toolchain_tree','baseline_source_sha256','candidate_sha256','probe_sha256',
    'test_script_sha256','fixture_manifest_sha256','canonical_plan_sha256','plan_content_sha256',
    'host_c_shards','totals_per_backend','timings','edit_replay_cases','boundary_cases','boundary_count',
    'boundary_main_calls','boundary_failure_calls','source_guard_negative_cases','fixture_compaction','scope',
    'verifier_source_sha256','local_generated_artifacts_verified','ordered_output_validation',
    'validator_negative_controls'))
SHARD_KEYS = frozenset(('shard','totals','build_seconds','execute_seconds','generated_c_bytes',
                        'generated_c_sha256','probe_sha256','executable_sha256'))
STAGE = 'startup'
OUTPUT_CHECKED = False


CONTROL_NAMES = (
    'changed-candidate','changed-test-script','changed-verifier','changed-baseline',
    'changed-adapted-baseline','changed-grammar-adaptation','changed-toolchain','changed-plan-hash','pending-report','extra-report-field',
    'missing-report-field','wrong-total','bool-count','false-artifact-flag',
    'integer-compaction-flag','nan-timing','negative-timing','reordered-shards',
    'missing-shard','extra-shard','wrong-shard-count','integer-order-boolean',
    'changed-order-log-hash','changed-plan-content','missing-log','oversized-log',
    'empty-log','reordered-raw-cases','missing-raw-case','extra-raw-case',
    'unsafe-raw-tail','crlf-log','duplicate-json-key','unknown-expected-input',
    'missing-expected-input','changed-expected-source','leaf-symlink',
    'directory-symlink','ancestor-symlink','directory-reparse')


def control_receipt():
    return {'passed':True,'count':len(CONTROL_NAMES),'cases':list(CONTROL_NAMES)}


def require(condition, code):
    if not condition:
        raise ValueError(code)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(path):
    return sha(path.read_bytes())


def fields(value, keys, code):
    require(type(value) is dict and set(value) == set(keys), code)


def natural(value):
    return type(value) is int and value >= 0


def hash256(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}',value) is not None


def counts(actual, expected):
    fields(actual,expected,'count-fields')
    require(all(natural(value) for value in actual.values()) and actual == expected,'counts')


def metric(value):
    require(type(value) in (int,float) and math.isfinite(value) and value >= 0,'metric')


def summary(count):
    return (f"POLICY_FAST_PASS batches={count['batches']} events={count['events']} "
            f"cases={count['cases']} transitions={count['context_transitions']}")


def strict_json(data):
    def pairs(items):
        result = {}
        for key,value in items:
            require(key not in result,'duplicate-json-key')
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('nonfinite-json')
    return json.loads(data.decode('utf-8'),object_pairs_hook=pairs,parse_constant=invalid)


def checked_path(path, regular=False):
    # Inspect lexical ancestors, without resolving through links or junctions.
    path = path.absolute()
    chain = (path,)+tuple(path.parents)
    require(len(chain) <= 128,'path-depth')
    for index,item in enumerate(chain):
        info = item.lstat()
        require(not stat.S_ISLNK(info.st_mode) and not (getattr(info,'st_file_attributes',0) & 0x400),
                'linked-public-path')
        require(stat.S_ISREG(info.st_mode) if index == 0 and regular else stat.S_ISDIR(info.st_mode),
                'public-path-kind')
    return path


def read_public(directory):
    directory = checked_path(directory)
    result = {}
    for name,limit in PUBLIC_FILE_LIMITS.items():
        path = checked_path(directory/name,regular=True)
        require(0 < path.stat().st_size <= limit,'public-file-size')
        with path.open('rb') as stream:
            data = stream.read(limit+1)
        require(0 < len(data) <= limit,'public-file-size')
        result[name] = data
    return result


def expected_inputs_from_source():
    return {'baseline_commit':BASE_COMMIT,'baseline_tree':BASE_TREE,
            'baseline_source_sha256':BASE_SOURCE_SHA256,'toolchain_commit':RU_COMMIT,'toolchain_tree':RU_TREE,
            'candidate_sha256':digest(ROOT/'src/ru_lexical.ru'),
            'test_script_sha256':digest(ROOT/'tools/test_ru_policy_fast.py'),
            'verifier_source_sha256':digest(Path(__file__)),
            'canonical_plan_sha256':digest(ROOT/'tests/fixtures/ru_policy_fast_plan.json')}


def verify_inputs(expected):
    fields(expected,EXPECTED_INPUT_KEYS,'expected-input-fields')
    pins = {'baseline_commit':BASE_COMMIT,'baseline_tree':BASE_TREE,'baseline_source_sha256':BASE_SOURCE_SHA256,
            'toolchain_commit':RU_COMMIT,'toolchain_tree':RU_TREE,'canonical_plan_sha256':CANONICAL_PLAN_SHA256}
    require(all(expected[key] == value for key,value in pins.items()),'expected-pins')
    require(all(hash256(expected[key]) for key in ('candidate_sha256','test_script_sha256',
                'verifier_source_sha256','baseline_source_sha256','canonical_plan_sha256')),'expected-hashes')


def inspect_outputs(data, report, manifest, verifier_sha):
    """Reconstruct each complete case in original order; no multiset shortcut."""
    case_lines = ['PASS CASE: '+item['case'] for item in manifest['cases']]
    edits = ['PASS EDIT: '+item['case'] for item in manifest['edits']]
    boundaries = ['PASS BOUNDARY: '+item['case'] for item in manifest['boundaries']]
    require(len(case_lines) == len(set(case_lines)) == 196,'case-identities')
    require(len(edits) == 4 and len(boundaries) == 13,'extra-identities')
    expected = case_lines+edits+boundaries+[summary(TOTALS)]
    require(data['interpreter.log'] == ('\n'.join(expected)+'\n').encode('utf-8'),'interpreter-order')
    require(type(report['host_c_shards']) is list and len(report['host_c_shards']) == 4,'shard-count')
    recovered = {}
    recovered_extras = []
    aggregate = {key:0 for key in TOTALS}
    for shard,entry in enumerate(report['host_c_shards']):
        fields(entry,SHARD_KEYS,'shard-fields')
        require(type(entry['shard']) is int and entry['shard'] == shard,'shard-order')
        indices = list(range(shard,len(case_lines),4))
        expected_counts = {'cases':len(indices),
            'batches':sum(manifest['cases'][i]['original_batch_count'] for i in indices),
            'events':sum(manifest['cases'][i]['events'] for i in indices),
            'context_transitions':21504 if shard == 3 else 0}
        counts(entry['totals'],expected_counts)
        metric(entry['build_seconds'])
        metric(entry['execute_seconds'])
        require(natural(entry['generated_c_bytes']) and entry['generated_c_bytes'] > 0,'generated-c-size')
        require(all(hash256(entry[key]) for key in ('generated_c_sha256','probe_sha256','executable_sha256')),'shard-hashes')
        lines = [case_lines[i] for i in indices]+(edits+boundaries if shard == 3 else [])+[summary(expected_counts)]
        actual = data[f'host-c-{shard}.log']
        require(actual == ('\n'.join(lines)+'\n').encode('utf-8'),'shard-output-order')
        actual_lines = actual.decode('utf-8').splitlines()
        for index,line in zip(indices,actual_lines[:len(indices)]):
            require(index not in recovered,'repeated-case')
            recovered[index] = line
        if shard == 3:
            recovered_extras = actual_lines[len(indices):-1]
        for key in aggregate:
            aggregate[key] += entry['totals'][key]
    counts(aggregate,TOTALS)
    reconstructed = ('\n'.join([recovered[i] for i in range(196)]+recovered_extras+[summary(aggregate)])+'\n').encode('utf-8')
    require(reconstructed == data['interpreter.log'],'reassembled-order')
    return {'status':'passed','case_count':196,'edit_count':4,'boundary_count':13,
            'each_shard_identity_and_order_exact':True,'original_order_reassembled_exact':True,
            'aggregate_counts_exact':True,'verifier_source_sha256':verifier_sha,
            'interpreter_stdout_sha256':sha(data['interpreter.log']),
            'reassembled_stdout_sha256':sha(reconstructed),
            'raw_stdout_sha256':{name:sha(data[name]) for name in LOG_NAMES}}


def validate_public_evidence(directory, expected_inputs):
    """Read only the eight bounded files; reject stale, partial or unknown evidence.

    expected_inputs must contain exactly EXPECTED_INPUT_KEYS and bind the actual
    prepared source bytes. canonical_plan_sha256 is the tracked JSON byte SHA,
    while plan_content_sha256 is a separately named semantic serialization SHA.
    Other build artifacts may coexist, but this function never reads them.
    """
    verify_inputs(expected_inputs)
    data = read_public(Path(directory))
    report = strict_json(data['report.json'])
    manifest = strict_json(data['fixture-manifest.json'])
    order = strict_json(data['ordered-output-validation.json'])
    fields(report,REPORT_KEYS,'report-fields')
    require(type(report['schema_version']) is int and report['schema_version'] == 2,'report-schema')
    require(report['status'] == 'passed','report-status')
    require(report['grammar_adaptation'] == GRAMMAR_ADAPTATION and
            report['baseline_adapted_source_sha256'] == ADAPTED_BASE_SOURCE_SHA256, 'adapted-baseline')
    require(all(report[key] == value for key,value in expected_inputs.items()),'source-bindings')
    require(report['baseline_policy_blob'] == BASE_POLICY_BLOB,'baseline-blob')
    require(report['fixture_manifest_sha256'] == sha(data['fixture-manifest.json']) == CANONICAL_PLAN_SHA256,'manifest-bytes')
    content = json.dumps(manifest,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
    require(report['plan_content_sha256'] == sha(content) == PLAN_CONTENT_SHA256,'manifest-content')
    require(hash256(report['probe_sha256']),'probe-hash')
    counts(report['totals_per_backend'],TOTALS)
    counts({key:report[key] for key in ('edit_replay_cases','boundary_count','boundary_main_calls',
        'boundary_failure_calls','source_guard_negative_cases')}, {'edit_replay_cases':4,'boundary_count':13,
        'boundary_main_calls':39,'boundary_failure_calls':6,'source_guard_negative_cases':12})
    require(report['boundary_cases'] == [item['case'] for item in manifest['boundaries']],'boundary-order')
    compaction = report['fixture_compaction']
    fields(compaction,('original_batches','encoded_records','python_exact_roundtrip',
                      'canonical_input_plan_matched','ru_per_case_input_checksum'),'compaction-fields')
    counts({key:compaction[key] for key in ('original_batches','encoded_records')},
           {'original_batches':19627,'encoded_records':2812})
    require(all(compaction[key] is True for key in ('python_exact_roundtrip',
                  'canonical_input_plan_matched','ru_per_case_input_checksum')),'compaction-checks')
    require(report['local_generated_artifacts_verified'] is True and report['scope'] == SCOPE,'local-scope')
    require(json.dumps(report['validator_negative_controls'],sort_keys=True) ==
            json.dumps(control_receipt(),sort_keys=True),'validator-controls')
    fields(report['timings'],('interpreter_seconds','build_seconds','host_c_seconds'),'timing-fields')
    for value in report['timings'].values():
        metric(value)
    expected_order = inspect_outputs(data,report,manifest,expected_inputs['verifier_source_sha256'])
    # Canonical JSON comparison also distinguishes booleans from integer 1.
    encoded = lambda value: json.dumps(value,sort_keys=True,separators=(',',':'))
    require(encoded(order) == encoded(expected_order) == encoded(report['ordered_output_validation']),'order-receipt')
    require(math.isclose(report['timings']['build_seconds'],sum(x['build_seconds'] for x in report['host_c_shards']),abs_tol=1e-9),'build-timing-total')
    require(math.isclose(report['timings']['host_c_seconds'],sum(x['execute_seconds'] for x in report['host_c_shards']),abs_tol=1e-9),'execution-timing-total')
    return report



def verify_negative_controls(data, expected):
    """Reproducible fail-closed tests on the actual run's staged public receipt."""
    from types import SimpleNamespace
    from unittest.mock import patch
    tested = []
    def encode(value):
        return (json.dumps(value,indent=2)+'\n').encode('utf-8')
    with tempfile.TemporaryDirectory(prefix='receipt-controls-',dir=OUT/'evidence') as temporary:
        root = Path(temporary)
        directory = root/'receipt'
        directory.mkdir()
        def reset(blobs):
            for path in directory.iterdir():
                path.unlink()
            for name,blob in blobs.items():
                (directory/name).write_bytes(blob)
        def reject(name, blobs=None, inputs=None, path=None):
            if blobs is not None:
                reset(blobs)
            before = {p.name:sha(p.read_bytes()) for p in directory.iterdir() if not p.is_symlink()}
            try:
                validate_public_evidence(path or directory, expected if inputs is None else inputs)
            except (ValueError,OSError,UnicodeError):
                pass
            else:
                raise ValueError('negative-control-accepted')
            after = {p.name:sha(p.read_bytes()) for p in directory.iterdir() if not p.is_symlink()}
            require(before == after,'validator-mutated-evidence')
            tested.append(name)
        reset(data)
        validate_public_evidence(directory,expected)
        edits = [
            ('changed-candidate','report.json',('candidate_sha256',),'0'*64),
            ('changed-test-script','report.json',('test_script_sha256',),'0'*64),
            ('changed-verifier','report.json',('verifier_source_sha256',),'0'*64),
            ('changed-baseline','report.json',('baseline_commit',),'0'*40),
            ('changed-adapted-baseline','report.json',('baseline_adapted_source_sha256',),'0'*64),
            ('changed-grammar-adaptation','report.json',('grammar_adaptation',),'unreviewed'),
            ('changed-toolchain','report.json',('toolchain_tree',),'0'*40),
            ('changed-plan-hash','report.json',('canonical_plan_sha256',),'0'*64),
            ('pending-report','report.json',('status',),'pending_order_verification'),
            ('extra-report-field','report.json',('unknown',),True),
            ('missing-report-field','report.json',('scope',),None),
            ('wrong-total','report.json',('totals_per_backend','events'),2553),
            ('bool-count','report.json',('boundary_count',),True),
            ('false-artifact-flag','report.json',('local_generated_artifacts_verified',),False),
            ('integer-compaction-flag','report.json',('fixture_compaction','python_exact_roundtrip'),1),
            ('nan-timing','report.json',('timings','build_seconds'),float('nan')),
            ('negative-timing','report.json',('timings','build_seconds'),-1),
            ('reordered-shards','report.json',('host_c_shards',),list(reversed(strict_json(data['report.json'])['host_c_shards']))),
            ('missing-shard','report.json',('host_c_shards',),strict_json(data['report.json'])['host_c_shards'][:-1]),
            ('extra-shard','report.json',('host_c_shards',),strict_json(data['report.json'])['host_c_shards']*2),
            ('wrong-shard-count','report.json',('host_c_shards',0,'totals','batches'),7030),
            ('integer-order-boolean','ordered-output-validation.json',('aggregate_counts_exact',),1),
            ('changed-order-log-hash','ordered-output-validation.json',('raw_stdout_sha256','host-c-0.log'),'0'*64),
            ('changed-plan-content','fixture-manifest.json',('cases',0,'events'),999)]
        for name,filename,keys,value in edits:
            blobs = dict(data)
            obj = strict_json(blobs[filename])
            target = obj
            for key in keys[:-1]:
                target = target[key]
            if value is None:
                del target[keys[-1]]
            else:
                target[keys[-1]] = value
            blobs[filename] = encode(obj)
            reject(name,blobs)
        raw = data['host-c-0.log']
        lines = raw.splitlines(keepends=True)
        changes = [
            ('missing-log','host-c-0.log',None),
            ('oversized-log','host-c-0.log',b'x'*65537),
            ('empty-log','host-c-0.log',b''),
            ('reordered-raw-cases','host-c-0.log',b''.join([lines[1],lines[0]]+lines[2:])),
            ('missing-raw-case','host-c-0.log',b''.join(lines[1:])),
            ('extra-raw-case','host-c-0.log',raw+lines[0]),
            ('unsafe-raw-tail','host-c-0.log',raw+b'/private/example/source.c: diagnostic\n'),
            ('crlf-log','host-c-0.log',raw.replace(b'\n',b'\r\n')),
            ('duplicate-json-key','report.json',data['report.json'].replace(b'{',b'{"status":"passed",',1))]
        for name,filename,value in changes:
            blobs = dict(data)
            if value is None:
                del blobs[filename]
            else:
                blobs[filename] = value
            reject(name,blobs)
        for name,key,value in (('unknown-expected-input','unknown','x'),
                               ('missing-expected-input','candidate_sha256',None),
                               ('changed-expected-source','candidate_sha256','0'*64)):
            inputs = dict(expected)
            if value is None:
                del inputs[key]
            else:
                inputs[key] = value
            reject(name,dict(data),inputs)
        reset(data)
        leaf = directory/'host-c-0.log'
        leaf.rename(directory/'original-log')
        leaf.symlink_to('original-log')
        reject('leaf-symlink')
        reset(data)
        link = root/'linked-receipt'
        link.symlink_to('receipt',target_is_directory=True)
        reject('directory-symlink',path=link)
        parent_link = root/'linked-parent'
        parent_link.symlink_to('.',target_is_directory=True)
        reject('ancestor-symlink',path=parent_link/'receipt')
        original_lstat = Path.lstat
        def reparse(path,*args,**kwargs):
            info = original_lstat(path,*args,**kwargs)
            return (SimpleNamespace(st_mode=info.st_mode,st_file_attributes=0x400)
                    if path == directory.absolute() else info)
        with patch.object(Path,'lstat',reparse):
            reject('directory-reparse')
    require(tested == list(CONTROL_NAMES),'negative-control-inventory')
    return control_receipt()


def main():
    global STAGE, OUTPUT_CHECKED
    require(len(sys.argv) == 1,'arguments')
    STAGE = 'local-artifacts'
    checked_path(OUT)
    checked_path(OUT/'evidence')
    OUTPUT_CHECKED = True
    report_path = checked_path(OUT/'report.json',regular=True)
    original_report = report_path.read_bytes()
    # A failed re-verification must not leave a previously successful report.
    report_path.unlink()
    (OUT/'ordered-output-validation.json').unlink(missing_ok=True)
    report = strict_json(original_report)
    require(report['status'] == 'pending_order_verification','fresh-execution-report')
    expected = expected_inputs_from_source()
    verify_inputs(expected)
    require(all(report[key] == value for key,value in expected.items() if key != 'verifier_source_sha256'),'local-source-bindings')
    require(digest(OUT/'differential.ru') == report['probe_sha256'],'local-probe')
    require(digest(OUT/'baseline.ru') == report['baseline_adapted_source_sha256'] == ADAPTED_BASE_SOURCE_SHA256, 'local-adapted-baseline')
    require(report['grammar_adaptation'] == GRAMMAR_ADAPTATION, 'local-grammar-adaptation')
    require(digest(OUT/'fixture-manifest.json') == CANONICAL_PLAN_SHA256,'local-plan')
    manifest = strict_json((OUT/'fixture-manifest.json').read_bytes())
    for shard,entry in enumerate(report['host_c_shards']):
        require(entry['shard'] == shard,'local-shard-order')
        probe = OUT/f'differential-{shard}.ru'
        generated = OUT/f'differential-{shard}-generated.c'
        require(digest(probe) == entry['probe_sha256'],'local-shard-probe')
        require(digest(generated) == entry['generated_c_sha256'] and generated.stat().st_size == entry['generated_c_bytes'],'local-generated-c')
        require(digest(OUT/f'differential-{shard}') == entry['executable_sha256'],'local-executable')
        indices = [int(i) for i in re.findall(r'^案(\d+)\.$',probe.read_text(encoding='utf-8'),re.M)]
        require(indices == list(range(shard,196,4)),'local-probe-order')
    data = {name:(OUT/name).read_bytes() for name in LOG_NAMES}
    result = inspect_outputs(data,report,manifest,expected['verifier_source_sha256'])
    report.update(status='passed',verifier_source_sha256=expected['verifier_source_sha256'],
                  local_generated_artifacts_verified=True,ordered_output_validation=result,
                  validator_negative_controls=control_receipt())
    (OUT/'evidence/host-proof-before-order-verification.json').write_bytes(original_report)
    STAGE = 'validator-controls'
    public_data = {**data,'fixture-manifest.json':(OUT/'fixture-manifest.json').read_bytes(),
        'report.json':(json.dumps(report,indent=2)+'\n').encode('utf-8'),
        'ordered-output-validation.json':(json.dumps(result,indent=2)+'\n').encode('utf-8')}
    require(verify_negative_controls(public_data,expected) == report['validator_negative_controls'],'controls')
    require(expected_inputs_from_source() == expected,'source-drift')
    STAGE = 'public-evidence'
    (OUT/'ordered-output-validation.json').write_bytes(public_data['ordered-output-validation.json'])
    report_path.write_bytes(public_data['report.json'])
    validate_public_evidence(OUT,expected)
    print('POLICY_FAST_ORDER_PASS',flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        private = traceback.format_exc().encode('utf-8')
        if OUTPUT_CHECKED:
            (OUT/'report.json').unlink(missing_ok=True)
            (OUT/'ordered-output-validation.json').unlink(missing_ok=True)
            if (OUT/'evidence').is_dir():
                (OUT/'evidence/order-verification-failure.log').write_bytes(private)
        print('POLICY_FAST_VERIFY_FAIL stage='+STAGE+' code=validation detail_sha256='+sha(private),file=sys.stderr)
        sys.exit(1)
