#!/usr/bin/env python3
"""Layered preview product gate for the actual bootstrap LLVM editor.

B7 remains functional smoke. This runner separately executes the original four
product GUI gates with unchanged validators/budgets plus the recent-file gate.
It is not the original all-console native acceptance and cannot mint its receipt.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile

# Resolve only this reviewed tools directory, including under Python -I.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from bootstrap_provenance import require, sha
from build_bootstrap_release import identity
import verify_bootstrap_editor_windows as smoke
from prepare_bootstrap_dependencies import validate_receipt

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'ru-notepad-bootstrap-product-preview-v1'
GUI_NAMES = {'main-gui-smoke', 'main-gui-file-entry', 'main-gui-ru-syntax', 'main-gui-markdown'}


def validate_gui_results(ci, results, hashes):
    require(len(results) == 4 and {row.get('name') for row in results} == GUI_NAMES,
            'incomplete/duplicate original product GUI inventory')
    for row in results:
        require(row.get('passed') is True and row.get('executed') is True
                and row.get('cleanup_killed') is False and row.get('exit_code') == 0
                and not row.get('skips') and not row.get('error'), 'product GUI failed')
        require(all(row.get(key) is True for key in
                    ('main_hwnd_seen', 'close_posted', 'detached_from_console')),
                'missing visible detached normal GUI lifecycle')
        name = row['name']
        if name != 'main-gui-smoke':
            require(row.get('fixture_binary_sha256') == hashes, 'GUI ran another binary snapshot')
        if name == 'main-gui-file-entry':
            require(all(row.get(key) for key in ci.GUI_FILE_CHECKS), 'file-entry GUI check missing')
        elif name == 'main-gui-ru-syntax':
            require(all(row.get(key) for key in ci.GUI_RU_CHECKS), 'Ru syntax GUI check missing')
            ci.validate_gui_ru_timer(row.get('timer_performance'), require_windows_clock=True)
            ci.validate_gui_ru_edits(row.get('edit_performance'))
        elif name == 'main-gui-markdown':
            require(all(row.get(key) is True for key in ci.GUI_MARKDOWN_CHECKS), 'Markdown GUI check missing')
            ci.validate_gui_markdown(row.get('markdown_performance'), require_windows_clock=True)


def validate_product(report, ci):
    require(report.get('schema') == SCHEMA and report.get('status') == 'passed', 'product preview not passed')
    require(report.get('all_native_console_tests_bootstrap_compiled') is False
            and report.get('full_release_acceptance') is False, 'overstated coverage')
    hashes = report['runtime_sha256']
    require(set(hashes) == set(ci.portable.RUNTIME_NAMES), 'runtime inventory mismatch')
    validate_gui_results(ci, report['gui_results'], hashes)
    ci.validate_scanner_preflight(report['scanner_preflight'], hashes, ROOT)
    from verify_recent_files_windows import validate_recent_files_result
    validate_recent_files_result(report['recent_files'], hashes)


def verify(config, output):
    require(sys.platform == 'win32', 'native Windows product testing required')
    receipts = smoke.validate_receipts(config)
    dependencies = validate_receipt(Path(config['dependencies_receipt']))
    app = receipts['app_receipt']
    require(dependencies['app_source'] == app['source_pins']['app_source']
            and dependencies['source_sha256'] == app['source_sha256']['app_source'], 'different dependency source')
    smoke_path = Path(config['smoke_receipt'])
    smoke_report = smoke.read_json(smoke_path)
    from verify_bootstrap_recent_policies import validate_report, compiler_from_receipt
    recent_fixture_path = Path(config['recent_fixtures_receipt'])
    validate_report(smoke.read_json(recent_fixture_path), app, compiler_from_receipt(app, config['app_receipt']))
    require(smoke_report.get('schema') == smoke.SCHEMA and smoke_report.get('status') == 'passed'
            and smoke.all_passed(smoke_report.get('results', {})), 'B7 smoke did not pass')
    for key in ('app_receipt', 'argv_probe_receipt', 'dll_probe_receipt', 'dependencies_receipt'):
        require(smoke_report['inputs'][key] == identity(Path(config[key])), 'smoke tested other build receipts')
    for item in smoke_report['runtime_copies']:
        smoke.verify_identity(item)
    smoke.verify_log_records(smoke_report['results'])
    ci = smoke.load_windows_harness(ROOT)
    api = ci.Windows()
    output = Path(output).absolute()
    require(not output.exists() and not any(p.is_symlink() for p in output.parents), 'fresh unlinked product directory required')
    require(not output.is_relative_to(ROOT), 'product evidence must not dirty pinned source')
    output.mkdir(parents=True)
    runtime, evidence = output/'runtime', output/'evidence'
    runtime.mkdir(); evidence.mkdir()
    sources = {'ru_notepad.exe': smoke.verify_identity(app['final_binary'])}
    sources.update({name: smoke.verify_identity(dependencies['binaries'][name]) for name in smoke.DLLS})
    for name, source in sources.items():
        shutil.copyfile(source, runtime/name)
        require(sha(runtime/name) == sha(source), 'runtime staging mismatch')
    hashes = {name: sha(path) for name, path in sources.items()}
    report = {'schema': SCHEMA, 'status': 'failed', 'platform': sys.platform,
              'source_pins': app['source_pins'], 'runtime_sha256': hashes,
              'runtime_directory': str(runtime), 'build_receipts': {key: identity(Path(config[key])) for key in
                  ('app_receipt', 'argv_probe_receipt', 'dll_probe_receipt', 'dependencies_receipt')},
              'smoke_receipt': identity(smoke_path), 'recent_fixtures_receipt': identity(recent_fixture_path), 'gui_results': [],
              'all_native_console_tests_bootstrap_compiled': False, 'full_release_acceptance': False,
              'coverage': 'Original four GUI product gates plus recent-file GUI; independent C-native baseline is separate'}
    def save():
        (output/'product-preview.json').write_text(json.dumps(report, indent=2, ensure_ascii=True)+'\n', encoding='utf-8')
    save()
    try:
        report['scanner_preflight'] = ci.run_scanner_preflight(api, runtime, evidence)
        ci.validate_scanner_preflight(report['scanner_preflight'], hashes, ROOT)
        save()
        with tempfile.TemporaryDirectory(prefix='ru-bootstrap-product-') as fixtures:
            for function in (ci.run_gui, ci.run_gui_file_entry, ci.run_gui_ru_syntax, ci.run_gui_markdown):
                args = (api, runtime, evidence) if function is ci.run_gui else (api, runtime, fixtures, evidence)
                from verify_recent_files_windows import isolated_recent_settings
                with isolated_recent_settings():
                    report['gui_results'].append(function(*args))
                save()
            validate_gui_results(ci, report['gui_results'], hashes)
            from verify_recent_files_windows import run_recent_files, validate_recent_files_result
            report['recent_files'] = run_recent_files(api, runtime, fixtures, evidence)
            validate_recent_files_result(report['recent_files'], hashes)
        smoke.validate_receipts(config)
        validate_receipt(Path(config['dependencies_receipt']))
        require(identity(smoke_path) == report['smoke_receipt'], 'smoke receipt changed')
        require(identity(recent_fixture_path) == report['recent_fixtures_receipt'], 'recent fixture receipt changed')
        validate_report(smoke.read_json(recent_fixture_path), app, compiler_from_receipt(app, config['app_receipt']))
        require({name: sha(runtime/name) for name in sources} == hashes, 'runtime changed during product tests')
        report['status'] = 'passed'
        validate_product(report, ci)
    except Exception as exc:
        report['error'] = str(exc)
        report['status'] = 'failed'
    save()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = verify(smoke.read_json(args.config), args.output)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
