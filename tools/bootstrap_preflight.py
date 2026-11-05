"""Source-bound receipt for the required cheap-preflight job; not native acceptance."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from bootstrap_provenance import require
from prepare_bootstrap_preview import git, manifest, ROOT

BLOCK_SHA256 = "3604cebba0923a9ca34f323ddc10b9f9ad198d5549c39d9d587d2c0dbecea4ca"

def block_hash():
    text = (ROOT / '.github/workflows/bootstrap-preview.yml').read_text(encoding='utf-8')
    start = text.index('      - name: Fail-closed cheap contract preflight')
    end = text.index('      - name: Record successful source-bound preflight', start)
    return hashlib.sha256(text[start:end].encode()).hexdigest()

def validate(value, pins, run_id, attempt):
    expected = {'schema': 'ru-notepad-cheap-preflight-v1', 'passed': True,
                'job': 'cheap-preflight', 'run_id': str(run_id), 'run_attempt': str(attempt),
                'block_sha256': BLOCK_SHA256,
                'sources': {key: {field: pins[key][field] for field in ('commit', 'tree')}
                            for key in ('app_source', 'ru_source')}}
    require(type(value) is dict and value == expected and value.get('passed') is True,
            'cheap preflight source/run/result differs')
    require(block_hash() == BLOCK_SHA256, 'cheap preflight command block differs')
    require(str(run_id).isdigit() and str(attempt).isdigit(), 'CI run identity required')
    return value

def require_tracked_clean(root):
    require(not git(root, 'diff', '--name-only') and not git(root, 'diff', '--cached', '--name-only'),
            'preflight tracked source changed during tests')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ru-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(os.environ['GITHUB_JOB'] == 'cheap-preflight', 'only required preflight job may emit receipt')
    app = {'commit': git(ROOT, 'rev-parse', 'HEAD'), 'tree': git(ROOT, 'rev-parse', 'HEAD^{tree}')}
    ru = {field: git(args.ru_root, 'rev-parse', revision) for field, revision in
          [('commit', 'HEAD'), ('tree', 'HEAD^{tree}')]}
    require(app['commit'] == os.environ['GITHUB_SHA'] and ru == manifest()['compiler'], 'preflight checkout differs')
    require_tracked_clean(ROOT)
    require_tracked_clean(args.ru_root)
    value = {'schema': 'ru-notepad-cheap-preflight-v1', 'passed': True, 'job': 'cheap-preflight',
             'run_id': os.environ['GITHUB_RUN_ID'], 'run_attempt': os.environ['GITHUB_RUN_ATTEMPT'],
             'block_sha256': BLOCK_SHA256, 'sources': {'app_source': app, 'ru_source': ru}}
    validate(value, value['sources'], value['run_id'], value['run_attempt'])
    encoded = json.dumps(value, sort_keys=True)
    args.output.write_text(encoded + '\n', encoding='utf-8')
    with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as stream:
        stream.write('receipt=' + encoded + '\n')

if __name__ == '__main__':
    main()
