#!/usr/bin/env python3
"""NOT ACCEPTED: numeric-only independent root probe, never product acceptance."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ('native/ru_directory_io.c', 'native/ru_directory_io.h',
          'tests/directory_root_diagnostic.c', 'tools/run_directory_root_diagnostic.py',
          '.github/workflows/diagnose-directory-root.yml')
PRODUCTION = {
    'native/ru_directory_io.c': '04d887d7112532dfe175e328612789e96479c1e5efaac94bf3c466fe7519aa3a',
    'native/ru_directory_io.h': 'd1b825798a13485bbfea21d5255e5bdc07107c93b9c939b67b2839a562aa9637',
}
FIELDS = {'api', 'component', 'result', 'win32_valid', 'win32_code', 'nt_valid',
          'nt_code', 'mapping', 'attributes', 'same_volume', 'handle_present'}


def require(condition, label):
    if not condition:
        raise ValueError(label)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate(value, instrumented):
    require(type(value) is dict and set(value) == {'schema', 'root_established',
            'trace_overflow', 'instrumented', 'trace'}, 'observation fields')
    require(value['schema'] == 'ru-directory-root-observation-v1', 'schema')
    require(type(value['root_established']) is bool and value['trace_overflow'] is False
            and value['instrumented'] is instrumented, 'observation flags')
    trace = value['trace']
    require(type(trace) is list and len(trace) <= 128, 'trace bound')
    require(bool(trace) is instrumented, 'instrumentation presence')
    for row in trace:
        require(type(row) is dict and set(row) == FIELDS, 'numeric-only fields')
        require(all(type(v) is int and 0 <= v <= 0xffffffff for v in row.values()), 'u32 observations')
        require(1 <= row['api'] <= 5 and row['component'] <= 32 and row['mapping'] <= 3,
                'stage bounds')
        require(all(row[k] in (0, 1) for k in ('win32_valid', 'nt_valid', 'same_volume', 'handle_present')), 'flag bounds')
        require(not row['nt_valid'] or row['api'] == 3, 'NT source')
        require(not row['win32_valid'] or row['api'] in (2, 4, 5), 'Win32 source')
    return value


def classify(value):
    if value['root_established']:
        return {'stage': 'root-established'}
    row = value['trace'][-1]
    stage = {1:'fixed-drive', 2:'device-mapping', 3:'nt-directory-open',
             4:'handle-type', 5:'directory-information'}[row['api']]
    if row['api'] == 5 and row['result']:
        if row['attributes'] & (0x400|0x1000|0x40000|0x400000):
            stage = 'forbidden-directory-attributes'
        elif not row['attributes'] & 0x10:
            stage = 'not-directory'
        elif not row['same_volume']:
            stage = 'volume-mismatch'
    if row['api'] == 3 and row['nt_code'] < 0x80000000 and not row['handle_present']:
        stage = 'null-handle-after-nt-success'
    return {'stage':stage, 'component':row['component'], 'observation':row}



def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True).strip()


def execute(args):
    require(sys.platform == 'win32', 'actual Windows required')
    require(args.expected_source_commit == git('rev-parse', 'HEAD'), 'source commit')
    require(not git('status', '--porcelain', '--untracked-files=all'), 'clean source')
    sources = {name: sha(ROOT/name) for name in INPUTS}
    require(all(sources[name] == value for name, value in PRODUCTION.items()), 'production source changed')
    output = Path(args.output).absolute()
    require(not output.exists() and not output.is_relative_to(ROOT), 'fresh external output')
    output.mkdir(parents=True)
    report = {'schema':'ru-directory-root-diagnostic-v1', 'acceptance': False,
              'status':'NOT_ACCEPTED-running', 'source_commit': args.expected_source_commit,
              'source_sha256':sources, 'cases': [], 'builds': [], 'probe_processes': [],
              'scope':'Recreated controlled paths on this runner; unchanged source, not original DLL/worker or product acceptance'}
    destination = output/'NOT_ACCEPTED-directory-root.json'
    def save():
        destination.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    save()
    try:
        cc = Path(args.cc).resolve(strict=True)
        report['compiler_sha256'] = sha(cc)
        binaries = {}
        for label, flags in (('control',['-DRU_DIR_ROOT_CONTROL']), ('instrumented', [])):
            binary = output/(label+'.exe')
            command = [str(cc), '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-municode',
                       *flags, str(ROOT/'tests/directory_root_diagnostic.c'), '-lshell32', '-lole32', '-o', str(binary)]
            report['phase'] = 'build-'+label;save()
            build = subprocess.run(command, capture_output=True, timeout=120)
            report['builds'].append({'variant':label, 'returncode':build.returncode,
                'stdout_sha256':hashlib.sha256(build.stdout).hexdigest(),
                'stderr_sha256':hashlib.sha256(build.stderr).hexdigest()})
            save()
            require(build.returncode == 0, 'probe build failed')
            binaries[label] = binary
            report['builds'][-1]['binary_sha256'] = sha(binary)
        # Recreate the failing fixture's relative layout, only under this job's
        # fresh private runner temp. Never inspect arbitrary user directories.
        temp = Path(os.environ['RUNNER_TEMP']).absolute()
        fixture = temp/'ru-bootstrap-preview'/'recent-fixtures'/'directory-fixture'
        require(not fixture.exists(), 'fresh controlled fixture required')
        fixture.mkdir(parents=True)
        # A second independently owned ordinary profile temp root distinguishes
        # layout-specific rejection from a wider drive/root-open problem. It is
        # not called verified until the unchanged guards actually accept it.
        local_temp = Path(os.environ['LOCALAPPDATA'])/'Temp'
        require(local_temp.is_dir(), 'ordinary temp base unavailable')
        ordinary = Path(tempfile.mkdtemp(prefix='ru-directory-root-', dir=local_temp))
        fixture_hash = hashlib.sha256('a😀a'.encode()).hexdigest()
        for fixture_label, fixture_path in (('preview-layout', fixture), ('ordinary-temp', ordinary)):
            payload = fixture_path/'utf8.txt';payload.write_bytes('a😀a'.encode())
            require(sha(payload) == fixture_hash, 'fixture creation')
            previous = None
            for repetition in range(2):
                pair = {}
                for label in ('control', 'instrumented'):
                    binary = binaries[label];before = sha(binary)
                    report['phase'] = 'probe-'+fixture_label+'-'+label;save()
                    result = subprocess.run([str(binary), str(fixture_path)], capture_output=True, timeout=15)
                    report['probe_processes'].append({'fixture':fixture_label, 'variant':label,
                        'repetition':repetition, 'returncode':result.returncode,
                        'stdout_bytes':len(result.stdout), 'stderr_bytes':len(result.stderr)})
                    save()
                    require(result.returncode == 0 and result.stderr == b'', 'probe process failed')
                    require(len(result.stdout) <= 65536, 'probe output bound')
                    observation = validate(json.loads(result.stdout), label == 'instrumented')
                    require(sha(binary) == before, 'probe binary changed')
                    pair[label] = observation
                require(pair['control']['root_established'] == pair['instrumented']['root_established'],
                        'control and instrumented outcomes differ')
                diagnosis = classify(pair['instrumented'])
                report['cases'].append({'fixture':fixture_label, 'repetition':repetition,
                                        **pair, 'diagnosis':diagnosis})
                save()
                require(previous is None or previous == diagnosis, 'unstable observation')
                previous = diagnosis
            require(sha(payload) == fixture_hash, 'fixture changed')
        report['fixture_sha256'] = fixture_hash
        require(sources == {name:sha(ROOT/name) for name in INPUTS} and sha(cc) == report['compiler_sha256'],
                'source or tool changed')
        report['status'] = 'NOT_ACCEPTED-observed';report['phase'] = 'complete'
    except Exception as error:
        # Fixed labels only; exceptions can include machine paths, so never log
        # their raw text or child output in the public report.
        report['status'] = 'NOT_ACCEPTED-diagnostic-failed'
        report['error_type'] = type(error).__name__
        save()
        raise SystemExit('Root diagnostic failed; numeric evidence is NOT ACCEPTED') from None
    save()
    print(json.dumps({'status': report['status'], 'acceptance':False,
                      'diagnoses': [{'fixture':c['fixture'], 'diagnosis':c['diagnosis']}
                                    for c in report['cases'] if c['repetition'] == 1]}))


class Controls(unittest.TestCase):
    def sample(self):
        row = dict.fromkeys(FIELDS, 0);row.update(api=3, nt_valid=1, nt_code=0xc0000022, result=0xc0000022)
        return {'schema':'ru-directory-root-observation-v1', 'root_established':False,
                'trace_overflow':False, 'instrumented':True, 'trace':[row]}
    def test_nt_code(self):
        value=validate(self.sample(), True)
        self.assertEqual(classify(value)['stage'], 'nt-directory-open')
        self.assertEqual(classify(value)['observation']['nt_code'], 0xc0000022)
    def test_control(self):
        value=self.sample();value.update(instrumented=False, trace=[])
        validate(value, False)
    def test_no_arbitrary_fields(self):
        value=self.sample();value['trace'][0]['path']='private'
        with self.assertRaises(ValueError):validate(value, True)
    def test_no_strings(self):
        value=self.sample();value['trace'][0]['nt_code']='private'
        with self.assertRaises(ValueError):validate(value, True)
    def test_bounds(self):
        for field, number in (('api',6), ('component',33), ('nt_code',-1), ('mapping',4)):
            value=self.sample();value['trace'][0][field]=number
            with self.subTest(field=field), self.assertRaises(ValueError):validate(value, True)
    def test_overflow(self):
        value=self.sample();value['trace_overflow']=True
        with self.assertRaises(ValueError):validate(value, True)
    def test_not_accepted_flag(self):
        value=self.sample();value['acceptance']=True
        with self.assertRaises(ValueError):validate(value, True)
    def test_null_success_handle(self):
        value=self.sample();value['trace'][0].update(nt_code=0,result=0)
        self.assertEqual(classify(validate(value,True))['stage'], 'null-handle-after-nt-success')
    def test_file_type_error(self):
        value=self.sample();value['trace'][0].update(api=4,nt_valid=0,nt_code=0,result=0,win32_valid=1,win32_code=6)
        self.assertEqual(classify(validate(value,True))['stage'], 'handle-type')
    def test_attribute_causes(self):
        for attrs,same,expected in ((0x410,1,'forbidden-directory-attributes'),(0,1,'not-directory'),(0x10,0,'volume-mismatch')):
            value=self.sample();value['trace'][0].update(api=5,nt_valid=0,nt_code=0,result=1,attributes=attrs,same_volume=same)
            self.assertEqual(classify(validate(value,True))['stage'],expected)
    def test_win32_stage(self):
        value=self.sample();value['trace'][0].update(api=2, nt_valid=0, nt_code=0, win32_valid=1, win32_code=5, result=0)
        self.assertEqual(classify(validate(value,True))['stage'], 'device-mapping')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--cc');parser.add_argument('--output');parser.add_argument('--expected-source-commit')
    args=parser.parse_args()
    if args.self_test:
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
        raise SystemExit(not result.wasSuccessful())
    require(args.cc and args.output and args.expected_source_commit, 'missing explicit inputs')
    execute(args)

if __name__ == '__main__':
    main()
