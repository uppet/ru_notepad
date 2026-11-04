#!/usr/bin/env python3
"""Run today's regex harness on one immutable failed-build runtime, NOT acceptance.

Uses the supported GitHub Actions artifact REST endpoint in this repository.
Only the read-only job token reaches api.github.com; it is never forwarded to
artifact storage. No arbitrary artifact, runtime, compiler, or download URL is
accepted. This does not rebuild the application or issue a product receipt.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'uppet/ru_notepad'
REPOSITORY_ID = 1421718936
RUN_ID = 41832860414
ARTIFACT_ID = 13329823677
APP_COMMIT = '19ad6042ca13b64564e3982743896637de79a8f2'
APP_TREE = '9476571f7e37ce4cc89fcfc6aa7635a00498153e'
COMPILER_COMMIT = 'c3bb177c6a15e90821e5495cc74b0fdfc39b893a'
COMPILER_TREE = '5dedbf06f9fb6e00fbfe779b33f172aa35b61334'
STAGE3_SHA256 = 'd543d9114b78b499a3ac66d0b7ba1c09a618a248a42b83e7fdabc0e354bf9ced'
ARTIFACT_NAME = 'NOT-ACCEPTED-diagnostic-runtime-' + APP_COMMIT
ARCHIVE_SHA256 = '8a3579c1a00e94349fea428f22c45951b4ffa638e06cb3b00a8eb55bb3ad36e4'
ARCHIVE_BYTES = 4835815
PRODUCT_RECEIPT_SHA256 = '3421a88c5833dce019fc2054a1ab2330e5e37fd801b18782f03ae66ff8723750'
FILES = {
    'ru_notepad.exe': {'size': 10759168, 'sha256': '17fc6c8850e04dc76e3b059b55b71e96e6dc588c7794ecf79765b44a49f4fa48'},
    'Scintilla.dll': {'size': 2256384, 'sha256': 'ad9bb05d472420fba69be2b954f78be9ca957ba43603c0d977abb431e832ffc2'},
    'Lexilla.dll': {'size': 2878976, 'sha256': '01f3d5cdcb5f3696bcd7541a4a4a0904a001d15e49862e06b7fe761794754d57'},
    'RuSyntax.dll': {'size': 32256, 'sha256': 'd381c2069403c2b8823c6e857de40390a607c7e6c30bfae1bcc58f86a4bfd8af'},
    'compile-proof.json': {'size': 41440, 'sha256': 'ba1553db4a95d4672b49ea320b6b1e30b808f48aa1f27e380777bfd023614ae0'},
    'NOT_ACCEPTED.json': {'size': 2082, 'sha256': '10b9d310ba88853b20da955e6651a5423e30151d4812597624c8a9e1d53f4ca4'},
}
RUNTIME_NAMES = ('ru_notepad.exe', 'Scintilla.dll', 'Lexilla.dll', 'RuSyntax.dll')
LIMIT = 32 * 1024 * 1024
SCHEMA = 'ru-notepad-regex-gui-diagnostic-v1'
NOTICE = ('NOT ACCEPTED: diagnostic evidence only. The application is the saved failed '
          '19ad6042 build, not a build of the current harness commit. A passing regex '
          'diagnostic is not product, packaging, preview, or release acceptance. '
          'Fresh source-bound full bootstrap and product gates remain mandatory.')
API_URL = f'https://api.github.com/repos/{REPOSITORY}/actions/artifacts/{ARTIFACT_ID}'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def bounded(response, limit=LIMIT):
    data = response.read(limit + 1)
    require(len(data) <= limit, 'Fixed artifact response exceeds size bound')
    return data


def validate_metadata(record):
    require(isinstance(record, dict), 'Artifact metadata is not an object')
    for key, expected in (('id', ARTIFACT_ID), ('name', ARTIFACT_NAME),
                          ('size_in_bytes', ARCHIVE_BYTES), ('expired', False),
                          ('digest', 'sha256:' + ARCHIVE_SHA256), ('url', API_URL),
                          ('archive_download_url', API_URL + '/zip')):
        require(type(record.get(key)) is type(expected) and record[key] == expected,
                'Fixed artifact metadata differs: ' + key)
    run = record.get('workflow_run', {})
    for key, expected in (('id', RUN_ID), ('repository_id', REPOSITORY_ID),
                          ('head_repository_id', REPOSITORY_ID),
                          ('head_branch', 'wip'), ('head_sha', APP_COMMIT)):
        require(type(run.get(key)) is type(expected) and run[key] == expected,
                'Fixed artifact source run differs: ' + key)
    return record


def download(token, repository):
    require(repository == REPOSITORY, 'Diagnostic must run in its own pinned repository')
    require(bool(token), 'Read-only Actions job token required')
    opener = urllib.request.build_opener(NoRedirect)
    headers = {'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
               'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'ru-notepad-regex-diagnostic'}
    try:
        with opener.open(urllib.request.Request(API_URL, headers=headers), timeout=60) as response:
            metadata = validate_metadata(json.loads(bounded(response, 1024 * 1024)))
        try:
            with opener.open(urllib.request.Request(API_URL + '/zip', headers=headers), timeout=60) as response:
                return bounded(response, ARCHIVE_BYTES), metadata
        except urllib.error.HTTPError as error:
            if error.code != 302:
                raise
            location = error.headers.get('Location', '')
        parsed = urllib.parse.urlsplit(location)
        require(parsed.scheme == 'https' and parsed.hostname and not parsed.username
                and not parsed.password and parsed.port in (None, 443) and not parsed.fragment,
                'Invalid fixed artifact HTTPS redirect')
        # Fresh request: no token, cookies, or original Authorization header.
        # Do not follow another redirect, particularly not an HTTPS downgrade.
        with opener.open(urllib.request.Request(location), timeout=60) as response:
            return bounded(response, ARCHIVE_BYTES), metadata
    except urllib.error.HTTPError as error:
        raise RuntimeError('Fixed Actions artifact download failed: HTTP ' + str(error.code)) from None
    except urllib.error.URLError:
        # Do not serialize signed storage URLs or request headers into evidence.
        raise RuntimeError('Fixed Actions artifact download failed: network error') from None


def validate_manifest(marker, proof):
    require(isinstance(marker, dict) and marker.get('schema') == 'ru-notepad-not-accepted-runtime-v1'
            and marker.get('status') == 'NOT_ACCEPTED' and marker.get('user_delivery_authorized') is False
            and marker.get('product_status') == 'failed', 'Saved runtime must remain NOT ACCEPTED')
    require(marker.get('product_receipt_sha256') == PRODUCT_RECEIPT_SHA256,
            'Saved product receipt identity differs')
    require(marker.get('stage3_sha256') == STAGE3_SHA256, 'Saved stage3 identity differs')
    pins = marker.get('source_pins', {})
    require(set(pins) == {'app_source', 'ru_source'}, 'Saved source inventory differs')
    for key, commit, tree in (('app_source', APP_COMMIT, APP_TREE),
                              ('ru_source', COMPILER_COMMIT, COMPILER_TREE)):
        require(pins[key].get('commit') == commit and pins[key].get('tree') == tree,
                'Saved source pin differs: ' + key)
    require(marker.get('files') == {name: record for name, record in FILES.items()
                                   if name != 'NOT_ACCEPTED.json'}, 'Saved runtime manifest differs')
    require(isinstance(proof, dict) and proof.get('schema') == 'ru-bootstrap-build-proof-v1'
            and proof.get('native_protocol') == 'bootstrap-native-v1'
            and proof.get('compiler', {}).get('sha256') == STAGE3_SHA256,
            'Saved compile proof identity differs')


def validate_archive(data):
    require(len(data) == ARCHIVE_BYTES and sha(data) == ARCHIVE_SHA256,
            'Fixed diagnostic archive size or SHA256 differs')
    payloads = {}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        require(len(entries) == len(FILES) and {item.filename for item in entries} == set(FILES),
                'Fixed diagnostic archive inventory differs')
        for item in entries:
            require(not item.is_dir() and not stat.S_ISLNK(item.external_attr >> 16)
                    and not (item.flag_bits & 1), 'Linked, encrypted, or directory archive member')
            require(item.file_size == FILES[item.filename]['size'] and item.file_size <= LIMIT,
                    'Fixed diagnostic archive member size differs: ' + item.filename)
            payload = archive.read(item)
            require(sha(payload) == FILES[item.filename]['sha256'],
                    'Fixed diagnostic archive member SHA256 differs: ' + item.filename)
            payloads[item.filename] = payload
    validate_manifest(json.loads(payloads['NOT_ACCEPTED.json']), json.loads(payloads['compile-proof.json']))
    return payloads


def source_identity(expected_commit):
    require(re.fullmatch('[0-9a-f]{40}', expected_commit) is not None, 'Full harness source commit required')
    def git(*args):
        return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True,
                                       encoding='utf-8', timeout=30).strip()
    commit, tree = git('rev-parse', 'HEAD'), git('rev-parse', 'HEAD^{tree}')
    require(commit == expected_commit and not git('status', '--porcelain'),
            'Harness must be the clean exact workflow source commit')
    return {'commit': commit, 'tree': tree, 'clean': True,
            'regex_harness_sha256': sha((ROOT / 'tools/gui_regex_search.py').read_bytes()),
            'diagnostic_runner_sha256': sha(Path(__file__).read_bytes())}


def verify_runtime(runtime):
    require({path.name for path in runtime.iterdir()} == set(RUNTIME_NAMES), 'Staged runtime inventory differs')
    hashes = {}
    for name in RUNTIME_NAMES:
        path = runtime / name
        require(path.is_file() and not path.is_symlink(), 'Missing or linked staged runtime: ' + name)
        require(path.stat().st_size == FILES[name]['size'] and sha(path.read_bytes()) == FILES[name]['sha256'],
                'Staged runtime identity differs: ' + name)
        hashes[name] = FILES[name]['sha256']
    return hashes


def fresh_output(output):
    output = Path(output).absolute()
    require(not output.exists() and not any(path.is_symlink() for path in [output, *output.parents]),
            'Fresh unlinked diagnostic output required')
    require(not output.is_relative_to(ROOT), 'Diagnostic output must not dirty harness checkout')
    output.mkdir(parents=True)
    return output


def run(output, expected_commit):
    require(sys.platform == 'win32', 'Actual Windows regex diagnostic execution required')
    output = fresh_output(output)
    report = {'schema': SCHEMA, 'status': 'NOT_ACCEPTED', 'diagnostic_result': 'failed',
              'notice': NOTICE, 'platform': sys.platform, 'rebuilt_application': False,
              'full_release_acceptance': False, 'product_acceptance': False,
              'packaging_acceptance': False, 'user_delivery_authorized': False,
              'application_source': {'commit': APP_COMMIT, 'tree': APP_TREE},
              'compiler_source': {'commit': COMPILER_COMMIT, 'tree': COMPILER_TREE},
              'source_artifact': {'repository': REPOSITORY, 'run_id': RUN_ID, 'artifact_id': ARTIFACT_ID,
                                  'name': ARTIFACT_NAME, 'sha256': ARCHIVE_SHA256, 'bytes': ARCHIVE_BYTES},
              'workflow_run': {'id': os.environ.get('GITHUB_RUN_ID'), 'attempt': os.environ.get('GITHUB_RUN_ATTEMPT')}}
    def save():
        (output / 'NOT_ACCEPTED-regex-gui-diagnostic.json').write_text(
            json.dumps(report, indent=2, ensure_ascii=True) + '\n', encoding='utf-8')
    save()
    try:
        report['harness_source'] = source_identity(expected_commit)
        save()
        data, metadata = download(os.environ.pop('GH_TOKEN', ''), os.environ.get('GITHUB_REPOSITORY', ''))
        payloads = validate_archive(data)
        report['source_artifact']['metadata'] = metadata
        evidence, fixtures, runtime = output / 'evidence', output / 'fixtures', output / 'runtime'
        for directory in (evidence, fixtures, runtime):
            directory.mkdir()
        for name in RUNTIME_NAMES:
            (runtime / name).write_bytes(payloads[name])
        for name in ('compile-proof.json', 'NOT_ACCEPTED.json'):
            (evidence / name).write_bytes(payloads[name])
        (evidence / 'artifact-metadata.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
        hashes = verify_runtime(runtime)
        report['runtime_sha256'] = hashes
        report['archive_and_runtime_verified'] = True
        save()
        import windows_ci as ci
        import gui_regex_search as regex
        require(set(ci.portable.RUNTIME_NAMES) == set(RUNTIME_NAMES), 'Harness runtime inventory differs')
        # The unmodified current harness owns all keyboard safety, response budgets,
        # registry isolation, fixture copies, cases, cancellation, and cleanup gates.
        report['regex_search'] = regex.run(ci.Windows(), runtime, fixtures, evidence)
        save()  # Preserve failed lifecycle evidence before invoking the strict validator.
        regex.validate_result(report['regex_search'], hashes)
        require(verify_runtime(runtime) == hashes, 'Runtime changed during regex diagnostic')
        require(source_identity(expected_commit) == report['harness_source'], 'Harness source changed during diagnostic')
        report['diagnostic_result'] = 'passed'
    except Exception as error:
        report['error'] = str(error)
    save()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-harness-commit', required=True)
    args = parser.parse_args()
    report = run(args.output, args.expected_harness_commit)
    print(NOTICE)
    print('Regex diagnostic: ' + report['diagnostic_result'])
    if report.get('error'):
        print(report['error'], file=sys.stderr)
    return 0 if report['diagnostic_result'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
