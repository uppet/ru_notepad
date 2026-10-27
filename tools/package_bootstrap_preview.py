#!/usr/bin/env python3
"""Package only the exact GUI-tested bootstrap editor as a labelled preview.

This does not call or fabricate the old all-native release validator. Independent
C-native CI remains separate baseline evidence, not substituted by these
preview gates or a claim about these bootstrap binaries. Source/proof/GUI identity is rechecked before and after ZIP.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

# Resolve only this reviewed tools directory, including under Python -I.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from bootstrap_provenance import require, sha
from build_bootstrap_release import identity
from compile_bootstrap_native import validate_wrapper_receipt
from verify_bootstrap_application_oracle import verify_application_oracle, ORACLE_PATH
import verify_bootstrap_editor_windows as smoke
import verify_bootstrap_product_windows as product
from prepare_bootstrap_dependencies import validate_receipt
import package as legacy_package

ROOT = Path(__file__).resolve().parents[1]
PREVIEW_DOCS = ('bootstrap-llvm-preview.md', 'recent-files.md', 'single-instance-and-tabs.md')


def verify_zip(path, files):
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        require(len(infos) == len(files) and {i.filename for i in infos} == set(files), 'ZIP inventory differs')
        import hashlib
        for info in infos:
            require(not info.is_dir() and info.file_size == files[info.filename]['size'], 'ZIP size mismatch')
            require(hashlib.sha256(archive.read(info)).hexdigest() == files[info.filename]['sha256'], 'ZIP byte identity mismatch')


NATIVE_EVIDENCE_LIMITS = {
    'application.metadata.c':16*1024*1024, 'native-wrapper.json':128*1024,
    'application-native-oracle.json':512*1024, 'application-oracle-validation.json':16*1024,
    'compile-proof.json':8*1024*1024,
}


def collect_native_evidence(config, app):
    directory=Path(config['app_receipt']).parent
    binary=directory/'intermediate-console.exe';proof_path=directory/'compile-proof.json'
    require(sha(proof_path)==app['compile_proof_sha256'],'packaged compile proof changed')
    proof=smoke.read_json(proof_path)
    app_root=Path(app['source_pins']['app_source']['path']);ru_root=Path(app['source_pins']['ru_source']['path'])
    compiler=Path(proof['compiler']['path'])
    frozen={str((app_root/name).resolve()):digest for name,digest in app['source_sha256']['app_source'].items()}
    wrapper=validate_wrapper_receipt(proof,app_root/'src/main.ru',compiler,binary,proof_path,frozen)
    require(wrapper==app['native_wrapper'] and identity(binary.with_name(binary.name+'.metadata.c'))==app['native_metadata'],
            'packaged native evidence differs from build receipt')
    checked=verify_application_oracle(proof,app_root,ru_root,app['source_sha256'],binary)
    require(checked==app['application_oracle'],'packaged oracle differs from build receipt')
    paths={'application.metadata.c':binary.with_name(binary.name+'.metadata.c'),
           'native-wrapper.json':binary.with_name(binary.name+'.native-wrapper.json'),
           'application-native-oracle.json':app_root/ORACLE_PATH,
           'application-oracle-validation.json':directory/'application-oracle-validation.json',
           'compile-proof.json':proof_path}
    require(smoke.read_json(paths['application-oracle-validation.json'])==checked,'oracle validation artifact changed')
    records={name:identity(path) for name,path in paths.items()}
    require(all(0<row['size']<=NATIVE_EVIDENCE_LIMITS[name] for name,row in records.items()),
            'native package evidence exceeds explicit size limit')
    require(proof['source_ir_sha256']==app['frontend_ir_sha256'],'frontend IR hash differs from build receipt')
    return records


def package(config, product_receipt, output, mingw_root):
    pending = output.with_name(output.name + '.pending')
    require(not output.exists() and not pending.exists(), 'refuse overwrite preview ZIP or pending output')
    receipts = smoke.validate_receipts(config)
    dependencies = validate_receipt(Path(config['dependencies_receipt']))
    report = smoke.read_json(product_receipt)
    ci = smoke.load_windows_harness(ROOT)
    product.validate_product(report, ci)
    require(report['source_pins'] == receipts['app_receipt']['source_pins'], 'product tested another source')
    for key, record in report['build_receipts'].items():
        require(record == identity(Path(config[key])), 'product build receipt changed')
    require(report['smoke_receipt'] == identity(Path(config['smoke_receipt'])), 'smoke receipt changed')
    require(report['recent_fixtures_receipt'] == identity(Path(config['recent_fixtures_receipt'])), 'recent fixtures receipt changed')
    from verify_bootstrap_recent_policies import CASES, validate_report, compiler_from_receipt
    validate_report(smoke.read_json(Path(config['recent_fixtures_receipt'])), receipts['app_receipt'],
                    compiler_from_receipt(receipts['app_receipt'], config['app_receipt']), dependencies)
    runtime = Path(report['runtime_directory'])
    expected = report['runtime_sha256']
    require({name: sha(smoke.verify_identity(identity(runtime/name))) for name in expected} == expected, 'tested runtime changed')
    require(sha(Path(receipts['app_receipt']['final_binary']['path'])) == expected['ru_notepad.exe'], 'packaged EXE is not final bootstrap EXE')
    require(all(dependencies['binaries'][name]['sha256'] == expected[name] for name in smoke.DLLS), 'packaged DLL differs from build')
    legacy_package.validate_dependency_sources(ROOT)
    pe = {name: legacy_package.inspect_pe(runtime/name, dependencies['tool_paths']['objdump'])
          for name in expected}
    inputs = {'product_receipt': identity(product_receipt), 'smoke_receipt': identity(Path(config['smoke_receipt'])),
              'recent_fixtures_receipt': identity(Path(config['recent_fixtures_receipt']))}
    native_evidence=collect_native_evidence(config,receipts['app_receipt'])
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ru-bootstrap-package-', dir=output.parent) as temp:
        stage = Path(temp)
        for name in expected:
            shutil.copyfile(runtime/name, stage/name)
        for source, destination in legacy_package.RUNTIME_FILES.items():
            if destination == 'README.txt':
                continue
            source_path = legacy_package.source_file(ROOT, source)
            target = stage/destination
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_path, target)
        for entry in legacy_package.DEPENDENCIES.values():
            shutil.copyfile(ROOT/'vendor'/entry['folder']/'License.txt', stage/'licenses'/entry['license'])
        for source in sorted((ROOT/'packaging/samples').rglob('*')):
            if source.is_file() or source.is_symlink():
                target = stage/'samples'/source.relative_to(ROOT/'packaging/samples')
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(legacy_package.checked_file(source), target)
        ci.copy_runtime_licenses(mingw_root, stage/'licenses')
        for name in PREVIEW_DOCS:
            shutil.copyfile(ROOT/'docs'/name, stage/'docs'/name)
        (stage/'README.txt').write_text(
            'ru_notepad — bootstrap LLVM Windows x64 PREVIEW\n\n'
            'The included editor was compiled by the native bootstrap compiler through LLVM IR.\n'
            'The same EXE and DLL bytes passed B7 functional smoke, the four existing product GUI\n'
            'gates (unchanged budgets), recent-file checks, and the instance_tabs GUI gate.\n'
            'Single-instance routing is configurable in Settings; changes affect later launches.\n'
            'Shell opens create tabs in the existing owner; --multi-instance bypasses once.\n'
            'Right-click a tab for Close, Others, Left, Right, Unmodified, or All.\n'
            'Timeouts never silently retry: pending shell files require your explicit choice.\n'
            'This is NOT the historical full all-native release acceptance. Console fixtures in\n'
            'the separate C-backend CI are independent regression evidence, not bootstrap tests.\n'
            'Use sample files or copies. Experimental wij folding/kernel switches remain off.\n'
            'See docs/single-instance-and-tabs.md for behavior, limits and acceptance coverage.\n'
            'See docs/bootstrap-llvm-preview.md and preview-provenance.json for scope and pins.\n', encoding='utf-8')
        (stage/'evidence').mkdir()
        for name,record in native_evidence.items():
            shutil.copyfile(smoke.verify_identity(record),stage/'evidence'/name)
            require(sha(stage/'evidence'/name)==record['sha256'],'native evidence copy changed')
        provenance = {'schema': 'ru-notepad-bootstrap-preview-package-v1', 'preview': True,
            'full_release_acceptance': False, 'all_native_console_tests_bootstrap_compiled': False,
            'delivery_requires_independent_C_baseline_CI_review': True,
            'app_commit': report['source_pins']['app_source']['commit'],
            'app_tree': report['source_pins']['app_source']['tree'],
            'compiler_commit': report['source_pins']['ru_source']['commit'],
            'compiler_tree': report['source_pins']['ru_source']['tree'],
            'stage3_sha256': receipts['app_receipt']['bootstrap']['stage3_sha256'],
            'runtime_sha256': expected, 'pe_imports': {name: row['imports'] for name, row in pe.items()},
            'product_receipt_sha256': inputs['product_receipt']['sha256'],
            'smoke_receipt_sha256': inputs['smoke_receipt']['sha256'],
            'gui_gates': sorted(product.GUI_NAMES), 'recent_files_gui': True, 'instance_tabs_gui': True,
            'stage3_recent_fixtures': dict(CASES),
            'recent_fixtures_receipt_sha256': inputs['recent_fixtures_receipt']['sha256'],
            'experimental_wij_enabled': False,
            'native_evidence_sha256':{name:row['sha256'] for name,row in native_evidence.items()},
            'frontend_ir_sha256':receipts['app_receipt']['frontend_ir_sha256'],
            'frontend_ir_delivery':'retained in CI evidence; SHA-bound here, not duplicated in ZIP'}
        (stage/'preview-provenance.json').write_text(json.dumps(provenance, indent=2)+'\n', encoding='utf-8')
        files = {p.relative_to(stage).as_posix(): {'sha256': sha(p), 'size': p.stat().st_size}
                 for p in sorted(stage.rglob('*')) if p.is_file()}
        with zipfile.ZipFile(pending, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name in files:
                archive.write(stage/name, name)
        verify_zip(pending, files)
    require({name: sha(runtime/name) for name in expected} == expected, 'tested runtime changed during ZIP')
    for record in inputs.values():
        smoke.verify_identity(record)
    require(collect_native_evidence(config,receipts['app_receipt'])==native_evidence,'native package evidence changed during ZIP')
    smoke.validate_receipts(config)
    validate_receipt(Path(config['dependencies_receipt']))
    require(not output.exists(), 'preview ZIP destination appeared during verification')
    pending.replace(output)
    result = {'schema': 'ru-notepad-bootstrap-preview-package-receipt-v1',
              'preview': True, 'full_release_acceptance': False,
              'zip': identity(output), 'files': files, 'runtime_sha256': expected, 'evidence': inputs, 'native_evidence':native_evidence,
              'frontend_ir_sha256':receipts['app_receipt']['frontend_ir_sha256']}
    output.with_suffix('.receipt.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    output.with_suffix(output.suffix+'.sha256').write_text(sha(output)+'  '+output.name+'\n', encoding='ascii')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--product-receipt', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mingw-root', type=Path, required=True)
    args = parser.parse_args()
    package(smoke.read_json(args.config), args.product_receipt, args.output, args.mingw_root)


if __name__ == '__main__':
    main()
