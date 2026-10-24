#!/usr/bin/env python3
"""Package only the exact GUI-tested bootstrap editor as a labelled preview.

This does not call or fabricate the old all-native release validator. Independent
C-native CI remains a separate prerequisite for delivery, not a claim about these
bootstrap binaries. Source/proof/GUI identity is rechecked before and after ZIP.
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
import verify_bootstrap_editor_windows as smoke
import verify_bootstrap_product_windows as product
from prepare_bootstrap_dependencies import validate_receipt
import package as legacy_package

ROOT = Path(__file__).resolve().parents[1]


def verify_zip(path, files):
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        require(len(infos) == len(files) and {i.filename for i in infos} == set(files), 'ZIP inventory differs')
        import hashlib
        for info in infos:
            require(not info.is_dir() and info.file_size == files[info.filename]['size'], 'ZIP size mismatch')
            require(hashlib.sha256(archive.read(info)).hexdigest() == files[info.filename]['sha256'], 'ZIP byte identity mismatch')


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
                    compiler_from_receipt(receipts['app_receipt'], config['app_receipt']))
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
        for name in ('bootstrap-llvm-preview.md', 'recent-files.md'):
            shutil.copyfile(ROOT/'docs'/name, stage/'docs'/name)
        (stage/'README.txt').write_text(
            'ru_notepad — bootstrap LLVM Windows x64 PREVIEW\n\n'
            'The included editor was compiled by the native bootstrap compiler through LLVM IR.\n'
            'The same EXE and DLL bytes passed B7 functional smoke, the four existing product GUI\n'
            'gates (unchanged budgets), and recent-file menu/persistence GUI checks.\n'
            'This is NOT the historical full all-native release acceptance. Console fixtures in\n'
            'the separate C-backend CI are independent regression evidence, not bootstrap tests.\n'
            'Use sample files or copies. Experimental wij folding/kernel switches remain off.\n'
            'See docs/bootstrap-llvm-preview.md and preview-provenance.json for scope and pins.\n', encoding='utf-8')
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
            'gui_gates': sorted(product.GUI_NAMES), 'recent_files_gui': True,
            'stage3_recent_fixtures': dict(CASES),
            'recent_fixtures_receipt_sha256': inputs['recent_fixtures_receipt']['sha256'],
            'experimental_wij_enabled': False}
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
    smoke.validate_receipts(config)
    validate_receipt(Path(config['dependencies_receipt']))
    require(not output.exists(), 'preview ZIP destination appeared during verification')
    pending.replace(output)
    result = {'schema': 'ru-notepad-bootstrap-preview-package-receipt-v1',
              'preview': True, 'full_release_acceptance': False,
              'zip': identity(output), 'files': files, 'runtime_sha256': expected, 'evidence': inputs}
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
