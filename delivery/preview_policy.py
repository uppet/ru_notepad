#!/usr/bin/env python3
"""Exact-d964 delivery policy; never changes formal acceptance or its evidence.

The product and original package module remain a clean d964 checkout. A separate
copy receives the original fresh-run seal, identical binaries and the original
acceptance bytes. Only named post-acceptance diagnostics stay in the original
checkout. A new, explicitly named eligibility rule extends the manual-preview
policy for the shared observer's *unchanged* error on the exact known Undo case.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

PRODUCT_COMMIT = 'd964ea9f7e27065aa5bbcced8d6c7526a6224dd1'
PRODUCT_TREE = '2522d03114c808480e42911be850b75e0ae14206'
COMPILER_COMMIT = '85c7821fda35aa79deeaf67b4d430f24ddd7f07f'
COMPILER_TREE = 'a770e367e84d87a0d2fcb6d49ea6f06da2dbe4ba'
ORIGINAL_POLICY_SHA256 = 'ca2dc35586d1642debf6a5111fa282d881bad43cee4d55138427ad90d954939e'
BRANCH = 'preview/wip-download-d964-20261022'
GENERIC_ERROR = 'GUI 1 MB open and Ru timer styling exceeded 30 seconds'
POLICY_NAME = 'd964-singleline-double-undo-observer-deadline-v1'
POLICY_FILES = ('delivery/preview_policy.py', 'delivery/test_preview_policy.py', '.github/workflows/windows.yml')
OPTIONAL_DIAGNOSTICS = {'markdown-native-baseline.json', 'markdown-cpu-profile.json',
                        'markdown-native-baseline-runner-failure.json', 'markdown-cpu-profile-runner-failure.json'}


def require(value, message):
    if not value:
        raise RuntimeError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], timeout=60).decode('utf-8').strip()


def validate_product_identity(source, app):
    require(source.get('app_commit') == PRODUCT_COMMIT and source.get('app_tree') == PRODUCT_TREE,
            'Only the exact requested d964 product commit/tree is eligible')
    require(app.get('ru_commit') == COMPILER_COMMIT, 'Unexpected product compiler commit')
    require(app.get('ru_tree') == COMPILER_TREE, 'Unexpected product compiler tree')


class Eligibility:
    """Extra rule, not a forged original-guard pass and not an acceptance pass."""
    def __init__(self, preview, source, app):
        validate_product_identity(source, app)
        self.preview = preview
        self.original_timeout = preview.validate_timeout
        self.source = source
        self.app = app

    def validate_timeout(self, test, summary):
        validate_product_identity(self.source, self.app)
        if test.get('error') != GENERIC_ERROR:
            return self.original_timeout(test, summary)
        require(test.get('name') == 'main-gui-markdown', 'Generic deadline is not a Markdown result')
        cases = test.get('markdown_performance', {}).get('cases', [])
        require(isinstance(cases, list) and len(cases) == 2 and
                [c.get('kind') for c in cases] == ['many-lines', 'singleline'] and
                all(isinstance(c.get('stages'), list) and len(c['stages']) == 4 for c in cases),
                'Generic observer deadline needs the exact completed case prefix')
        stage = cases[-1]['stages'][-1]
        require(stage.get('operation') == 'undo' and type(stage.get('undo_commands')) is int and
                stage['undo_commands'] == 2, 'Generic deadline requires exactly two native Undo commands')
        progress = stage.get('last_progress', {})
        require(stage.get('length') == 1000000 and stage.get('dirty') is False and
                progress.get('length') == 1000000 and progress.get('dirty') is False and
                progress.get('tail_requested') is True,
                'Generic deadline must have restored the exact clean source bytes')
        # Only this explicitly classified record receives the extra error spelling.
        # Neither test nor summary is copied, normalized or edited. All existing
        # deadline, clock, prior-stage, style/fold, memory, observer, pending-work,
        # binary, cleanup and source-preservation predicates execute unchanged.
        original_names = self.preview.DEADLINES
        before = json.dumps(summary, sort_keys=True, ensure_ascii=False)
        try:
            self.preview.DEADLINES = original_names | {GENERIC_ERROR}
            result = self.original_timeout(test, summary)
        finally:
            self.preview.DEADLINES = original_names
        require(json.dumps(summary, sort_keys=True, ensure_ascii=False) == before,
                'Eligibility must not modify original acceptance evidence')
        require(result['kind'] == 'singleline' and result['operation'] == 'undo',
                'Unexpected qualified deadline')
        return result

    @contextmanager
    def installed(self):
        original = self.preview.validate_timeout
        require(original is self.original_timeout, 'Unexpected eligibility hook')
        self.preview.validate_timeout = self.validate_timeout
        try:
            yield
        finally:
            self.preview.validate_timeout = original


def policy_identity(root, preview):
    require(os.environ.get('GITHUB_REPOSITORY') == 'uppet/ru_notepad' and
            os.environ.get('GITHUB_REF') == 'refs/heads/' + BRANCH and
            os.environ.get('GITHUB_EVENT_NAME') == 'push', 'Wrong delivery workflow invocation')
    expected = os.environ.get('GITHUB_SHA', '')
    require(re.fullmatch('[0-9a-f]{40}', expected) is not None and git(root, 'rev-parse', 'HEAD') == expected,
            'Delivery checkout differs from the exact workflow commit')
    require(not git(root, 'status', '--porcelain'), 'Delivery policy checkout must remain clean')
    return {'policy': POLICY_NAME, 'workflow_commit': expected,
            'workflow_tree': git(root, 'rev-parse', 'HEAD^{tree}'),
            'files_sha256': {n: sha(preview.read_bytes(root, n)) for n in POLICY_FILES},
            'github_run_id': os.environ.get('GITHUB_RUN_ID'),
            'github_run_attempt': os.environ.get('GITHUB_RUN_ATTEMPT')}


def copy_file(preview, source, destination, relative):
    data = preview.read_bytes(source, relative)
    target = destination / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    require(not target.exists(), 'A staged input already exists')
    with target.open('xb') as stream:
        stream.write(data)
    require(preview.read_bytes(destination, relative) == data, 'Staged input readback differs')


def stage_sealed_snapshot(preview, root, destination, objdump):
    run = preview.RUN_ROOT
    seal_bytes = preview.read_bytes(root, run + '/' + preview.SEAL_NAME, preview.MAX_JSON_BYTES)
    seal = preview.strict_json(seal_bytes)
    snapshot, app, _, _ = preview.snapshot(root, objdump)
    validate_product_identity(snapshot['source'], app)
    require(snapshot == seal.get('snapshot'), 'Original snapshot differs from its fresh-run seal')
    evidence = preview.safe_path(root, run + '/evidence', directory=True)
    present = {p.name for p in evidence.iterdir()}
    allowed = preview.allowed_evidence() | preview.PREEXISTING_EVIDENCE | {'portable-artifact.json'}
    require(present <= allowed | OPTIONAL_DIAGNOSTICS,
            'Unknown evidence may not be silently excluded from preview')
    # Read every original evidence file, including diagnostics, before copying.
    # The complete original directory stays in place and is checked again later.
    original_evidence = {n: sha(preview.read_bytes(root, run + '/evidence/' + n)) for n in present}
    require(not destination.exists(), 'Refuse to reuse a preview staging checkout')
    subprocess.run(['git', 'clone', '--no-local', '--no-hardlinks', '--no-checkout', str(root), str(destination)],
                   check=True, timeout=180, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(['git', '-C', str(destination), 'config', 'core.autocrlf', 'false'], check=True, timeout=30)
    subprocess.run(['git', '-C', str(destination), 'checkout', '--detach', PRODUCT_COMMIT],
                   check=True, timeout=60, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    for name in (*preview.portable.BINARY_NAMES, *snapshot['build_receipt_sha256']):
        copy_file(preview, root, destination, run + '/bin/' + name)
    for n in sorted(present & allowed):
        copy_file(preview, root, destination, run + '/evidence/' + n)
    copy_file(preview, root, destination, run + '/' + preview.SEAL_NAME)
    for dependency in preview.portable.DEPENDENCIES.values():
        for relative in ('vendor/downloads/' + dependency['archive'], 'vendor/' + dependency['folder'] + '/License.txt'):
            copy_file(preview, root, destination, relative)
    require(preview.read_bytes(destination, run + '/' + preview.SEAL_NAME) == seal_bytes,
            'Original seal bytes changed')
    require(preview.snapshot(destination, objdump)[0] == snapshot and preview.snapshot(root, objdump)[0] == snapshot,
            'Staging must preserve the entire original source/binary/receipt snapshot')
    return snapshot, app, seal_bytes, original_evidence


def readme(build, provenance):
    timeout = build['timeout']
    result = ('正式自动验收失败：Markdown 性能未通过。已知失败为 ' +
              f"{timeout['kind']} / {timeout['operation']}，{timeout['wall_ms']} ms 后仍在 folding。\n" +
              ('后续未闭合围栏用例未执行，不能声称已通过。\n' if timeout['kind'] != 'unclosed-fence' else
               '未闭合围栏用例未完成；超时后的阶段也不能视为通过。\n')) if timeout else (
              '本轮自动验收通过；人工验收尚未完成，仍是实验预览。\n')
    return ('ru_notepad 0.1.8-preview · 当前 wip Windows x64 预览\n\n'
        '【重要】这不是正式发布或完整验收版本。仅用样本、文件副本体验。\n' + result + '\n'
        f'产品提交：{PRODUCT_COMMIT}\n产品树：{PRODUCT_TREE}\n'
        f'编译器提交：{COMPILER_COMMIT}\n打包策略提交：{provenance["workflow_commit"]}\n\n'
        '运行：完整解压 ZIP 至可写目录，保持 ru_notepad.exe、Scintilla.dll、Lexilla.dll、\n'
        'RuSyntax.dll 在同一目录，双击 ru_notepad.exe。不需要 Python、如言编译器或管理员权限。\n'
        '程序未签名；不要关闭系统安全保护。Ctrl+O 可打开文件。\n\n'
        'samples/fence.md 是既有 1,000,000 字节样本；它仅供手动体验，不表示本轮用例已执行。\n'
        '重要限制：大段或长行 Markdown 撤销后可能等待超过 30 秒；此包不修复该问题。\n'
        '没有自动保存或崩溃恢复保证。请勿覆盖唯一的重要文件。中文输入法、高 DPI、\n'
        '无障碍及广泛 Windows 10/11 交互兼容性仍待人工验证。\n'
        '不包含尚未合入的键盘导航修复、mi 借用实验或 Notepad++ 对照实验。\n\n'
        'BUILD.json 保留原打包器记录的原始验收状态和产品源码身份；PREVIEW-POLICY.json\n'
        '记录外置规则和 workflow 身份。原始失败及 error 未修改，正式 CI 失败仍保留。\n'
        '原 ZIP 的 SHA256SUMS.txt 保留；DELIVERY-SHA256SUMS.txt 额外覆盖交付说明和策略记录。\n')


def delivery_archive(preview, original_zip, record, result, provenance, destination):
    require(not destination.exists(), 'Delivery output already exists')
    require(sha(original_zip.read_bytes()) == record['sha256'], 'Original guarded ZIP hash mismatch')
    with zipfile.ZipFile(original_zip) as source:
        expected = {name[len(original_zip.stem) + 1:]: source.read(name) for name in source.namelist()}
    require({n: sha(v) for n, v in expected.items()} == record['inventory_sha256'],
            'Guarded runtime inventory differs from its receipt')
    preview.verify_archive(original_zip, expected)
    original_build = expected['BUILD.json']
    build = preview.strict_json(original_build)
    validate_product_identity(build['source'], build)
    require(build['package_kind'] == 'manual-preview-runtime' and build['manual_acceptance'] == 'not_run',
            'Only the guarded runtime package is deliverable')
    receipt = dict(provenance, product_commit=PRODUCT_COMMIT, product_tree=PRODUCT_TREE,
                   compiler_commit=COMPILER_COMMIT, original_guarded_archive_sha256=record['sha256'],
                   original_native_acceptance_sha256=result['native_acceptance_sha256'],
                   formal_acceptance=result['formal_acceptance'],
                   original_acceptance_passed=result['original_acceptance_passed'],
                   evidence_rewritten=False, acceptance_rerun=False)
    require(not {'README.txt', 'PREVIEW-POLICY.json', 'DELIVERY-SHA256SUMS.txt'} & expected.keys(),
            'Delivery metadata must not replace product files')
    expected['README.txt'] = readme(build, provenance).encode('utf-8')
    expected['PREVIEW-POLICY.json'] = (json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()
    expected['DELIVERY-SHA256SUMS.txt'] = ''.join(f'{sha(v)}  {n}\n' for n, v in sorted(expected.items())).encode()
    require(expected['BUILD.json'] == original_build, 'Original build evidence changed')
    destination.mkdir()
    archive = destination / 'ru_notepad-wip-d964ea9f-windows-x64-preview.zip'
    prefix = archive.stem + '/'
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as output:
        for name, data in sorted(expected.items()):
            output.writestr(prefix + name, data)
    with zipfile.ZipFile(archive) as check:
        require(check.testzip() is None and check.namelist() == [prefix + n for n in sorted(expected)] and
                all(check.read(prefix + n) == data for n, data in expected.items()), 'Delivery ZIP readback failed')
    digest = sha(archive.read_bytes())
    (destination / (archive.name + '.sha256')).write_text(f'{digest}  {archive.name}\n', encoding='utf-8')
    return {'file_name': archive.name, 'sha256': digest, 'bytes': archive.stat().st_size,
            'runtime_binary_sha256': result['runtime_binary_sha256'], 'provenance': receipt}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--product-root', type=Path, required=True)
    parser.add_argument('--objdump', type=Path, required=True)
    parser.add_argument('--mingw-root', type=Path, required=True)
    args = parser.parse_args()
    require(sys.platform == 'win32', 'Delivery requires the original real Windows acceptance host')
    root = args.product_root.absolute()
    require(git(root, 'rev-parse', 'HEAD') == PRODUCT_COMMIT and
            git(root, 'rev-parse', 'HEAD^{tree}') == PRODUCT_TREE and not git(root, 'status', '--porcelain'),
            'Product checkout is not clean exact d964')
    require(sha((root / 'tools/package_manual_preview.py').read_bytes()) == ORIGINAL_POLICY_SHA256,
            'Original product policy has changed')
    sys.path.insert(0, str(root / 'tools'))
    preview = importlib.import_module('package_manual_preview')
    policy_root = Path(__file__).absolute().parents[1]
    provenance = policy_identity(policy_root, preview)
    destination = root / preview.RUN_ROOT / 'delivery-preview'
    staging = root / preview.RUN_ROOT / 'delivery-staging'
    snapshot, app, seal_bytes, evidence = stage_sealed_snapshot(preview, root, staging, args.objdump)
    policy = Eligibility(preview, snapshot['source'], app)
    with policy.installed():
        result = preview.create_preview(staging, args.objdump,
            lambda target: preview.copy_checked_runtime_licenses(args.mingw_root, target))
    require(preview.snapshot(root, args.objdump)[0] == snapshot and
            preview.read_bytes(root, preview.RUN_ROOT + '/' + preview.SEAL_NAME) == seal_bytes and
            {p.name for p in (root / preview.RUN_ROOT / 'evidence').iterdir()} == set(evidence) and
            all(sha(preview.read_bytes(root, preview.RUN_ROOT + '/evidence/' + n)) == digest for n, digest in evidence.items()),
            'Original source, seal, binaries or evidence changed during preview')
    require(policy_identity(policy_root, preview) == provenance, 'Delivery policy changed while packaging')
    record = result['packages']['runtime']
    original = staging / preview.RUN_ROOT / preview.OUTPUT_NAME / record['name']
    original_acceptance = preview.strict_json(preview.read_bytes(root, preview.RUN_ROOT + '/evidence/native-acceptance.json'))
    markdown = next(t for t in original_acceptance['tests'] if t['name'] == 'main-gui-markdown')
    delivery_provenance = dict(provenance, original_markdown_error=markdown.get('error'),
        original_run_error=original_acceptance.get('run_error'), original_evidence_sha256=evidence)
    require(not destination.exists(), 'Refuse to replace any prior delivery')
    try:
        final = delivery_archive(preview, original, record, result, delivery_provenance, destination)
        (destination / 'delivery-artifact.json').write_text(json.dumps(final, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    except Exception:
        if destination.exists():
            shutil.rmtree(destination)
        raise
    print(json.dumps(final, sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # No private path, arbitrary exception, or user data enters public output.
        print('Exact-d964 preview refused: identity, safety, freshness, evidence or inventory check failed.', file=sys.stderr)
        raise SystemExit(1)
