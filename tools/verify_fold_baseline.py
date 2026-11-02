#!/usr/bin/env python3
"""Reproduce the command-routing bug using one immutable, already-tested ZIP.

Read-only access to this repository's exact Actions artifact. The job token is
sent only to api.github.com, never forwarded to the signed storage redirect.
No rebuild, alternate baseline, or arbitrary download/execution is supported.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile

ARTIFACT = 12880829425
ARCHIVE_SHA = 'b49d043da4a084fee9b760964f8dabda28c05b586ef7c1ec4bf81529cc96270f'
PREVIEW_SHA = '5216b8a7ae700df6ce506000ca57f0fedff6e8dd3ee465d44fcb23c2a17870dc'
PREVIEW_NAME = 'ru_notepad-bootstrap-llvm-preview-windows-x64.zip'
BASELINE_COMMIT = '87189d2e36b282bf08bcf781be6a73570c2a22b0'
LIMIT = 16 * 1024 * 1024

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def bounded(response):
    data = response.read(LIMIT + 1)
    if len(data) > LIMIT: raise ValueError('Fixed baseline archive exceeds size bound')
    return data

def download(token):
    if not token: raise ValueError('Read-only Actions token required')
    url = f'https://api.github.com/repos/uppet/ru_notepad/actions/artifacts/{ARTIFACT}/zip'
    request = urllib.request.Request(url, headers={'Authorization': 'Bearer '+token,
        'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'})
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=60) as response:
            return bounded(response)
    except urllib.error.HTTPError as error:
        if error.code != 302: raise RuntimeError('Fixed baseline artifact download failed: HTTP '+str(error.code)) from None
        location = error.headers.get('Location', '')
    parsed = urllib.parse.urlsplit(location)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Invalid fixed artifact redirect')
    # No authorization header is reused on the signed download request.
    with urllib.request.urlopen(location, timeout=60) as response:
        return bounded(response)

def unpack(data, destination):
    if hashlib.sha256(data).hexdigest() != ARCHIVE_SHA: raise ValueError('Baseline archive identity differs')
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        if names.count(PREVIEW_NAME) != 1: raise ValueError('Fixed baseline preview missing/duplicate')
        info = archive.getinfo(PREVIEW_NAME)
        if info.file_size > LIMIT: raise ValueError('Baseline preview size exceeds bound')
        preview = archive.read(info)
    if hashlib.sha256(preview).hexdigest() != PREVIEW_SHA: raise ValueError('Baseline preview identity differs')
    import windows_ci as ci
    destination.mkdir()
    hashes = {}
    with zipfile.ZipFile(io.BytesIO(preview)) as archive:
        names = archive.namelist()
        for name in ci.portable.RUNTIME_NAMES:
            if names.count(name) != 1: raise ValueError('Baseline runtime missing/duplicate')
            info = archive.getinfo(name)
            if info.file_size > LIMIT: raise ValueError('Baseline runtime size exceeds bound')
            payload = archive.read(info)
            (destination/name).write_bytes(payload)
            hashes[name] = hashlib.sha256(payload).hexdigest()
    return hashes

def run(output):
    if sys.platform != 'win32': raise RuntimeError('Actual Windows baseline reproduction required')
    output = output.resolve()
    if output.exists() or any(p.is_symlink() for p in output.parents): raise ValueError('Fresh unlinked baseline output required')
    output.mkdir(parents=True)
    data = download(os.environ.get('GH_TOKEN', ''))
    (output/'baseline-artifact.zip').write_bytes(data)
    hashes = unpack(data, output/'runtime')
    import windows_ci as ci
    from gui_fold_commands import run_baseline, validate_baseline_result
    fixtures = output/'fixtures'; fixtures.mkdir()
    evidence = output/'evidence'; evidence.mkdir()
    result = run_baseline(ci.Windows(), output/'runtime', fixtures, evidence)
    record = {'schema':'ru-notepad-fixed-fold-baseline-v1', 'commit':BASELINE_COMMIT,
              'artifact_id':ARTIFACT, 'archive_sha256':ARCHIVE_SHA, 'preview_sha256':PREVIEW_SHA,
              'runtime_sha256':hashes, 'gui':result}
    (output/'baseline-reproduction.json').write_text(json.dumps(record, indent=2)+'\n')
    validate_baseline_result(result, hashes)
    return record

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.output)
    print('PASS: fixed 87189 baseline reproduces C command-routing defect; native folder works')
