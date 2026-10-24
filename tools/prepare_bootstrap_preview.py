#!/usr/bin/env python3
"""Freeze reviewed preview pins/tools and drive the three proven B11 builds.

The tracked manifest is filled only after review; this tool never invents its
allowed source delta from the checkout it is supposed to validate.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

# Resolve only this reviewed tools directory, including under Python -I.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from bootstrap_provenance import require, sha
from build_bootstrap_release import build, snapshot, verify_app_baseline

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT/'packaging/bootstrap-preview-inputs.json'


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True, encoding='utf-8').strip()


def manifest():
    value = json.loads(MANIFEST.read_text(encoding='utf-8'))
    require(value.get('schema') == 'ru-notepad-reviewed-preview-inputs-v1', 'unknown preview manifest')
    for kind in ('compiler', 'baseline'):
        for key in ('commit', 'tree'):
            require(isinstance(value[kind][key], str) and re.fullmatch('[0-9a-f]{40}', value[kind][key]), 'unfrozen '+kind+' '+key)
    require(isinstance(value.get('reviewed_changes'), dict), 'missing reviewed delta')
    return value


def prepare(ru, output, mingw):
    value = manifest()
    require(not output.exists() and not any(p.is_symlink() for p in output.parents), 'private fresh output required')
    require(not output.resolve().is_relative_to(ROOT) and not output.resolve().is_relative_to(ru), 'output must be outside source')
    expected_app = os.environ['GITHUB_SHA']
    require(re.fullmatch('[0-9a-f]{40}', expected_app), 'full CI application commit required')
    app_pin = {'path': str(ROOT), 'commit': expected_app, 'tree': git(ROOT, 'rev-parse', 'HEAD^{tree}')}
    ru_pin = {'path': str(ru), **value['compiler']}
    app_sources = snapshot(ROOT, app_pin['commit'], app_pin['tree'])
    snapshot(ru, ru_pin['commit'], ru_pin['tree'])
    baseline = {**value['baseline'], 'reviewed_changes': value['reviewed_changes']}
    verify_app_baseline(ROOT, baseline, app_sources)
    sys.path.insert(0, str(ru))
    from rulang.llvm_toolchain import LLVMToolchain
    compiler = LLVMToolchain()
    require(len(compiler.clang) == 1, 'unexpected compiler argv')
    tools = {'clang': str(Path(compiler.clang[0]).resolve()),
             **{key: str(Path(path).resolve()) for key, path in compiler.tools.items()},
             'linker': str((Path(os.environ['VCToolsInstallDir'])/'bin/Hostx64/x64/link.exe').resolve()),
             'resource-compiler': str((Path(os.environ['WindowsSdkDir'])/'bin'/os.environ['WindowsSDKVersion'].rstrip('\\/')/'x64/rc.exe').resolve())}
    native = {key: str((mingw/'bin'/name).resolve()) for key, name in
              {'cc':'gcc.exe','cxx':'g++.exe','make':'mingw32-make.exe','windres':'windres.exe',
               'ar':'ar.exe','ranlib':'ranlib.exe','objdump':'objdump.exe'}.items()}
    def hashes(paths):
        result = {}
        for name, path in paths.items():
            p = Path(path)
            require(p.is_file() and not p.is_symlink(), 'invalid tool')
            result[name] = sha(p)
        return result
    directory = ru/'bin/bootstrap/preview-ci'
    config = {'schema':'ru-notepad-bootstrap-llvm-config-v1', 'ru_source':ru_pin, 'app_source':app_pin,
              'app_baseline':baseline, 'bootstrap_directory':str(directory),
              'verification':str(directory/'verification.json'), 'tool_paths':tools, 'tool_sha256':hashes(tools),
              'mingw_tool_paths':native, 'mingw_tool_sha256':hashes(native)}
    output.mkdir(parents=True)
    (output/'base-config.json').write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8')
    with open(os.environ['GITHUB_ENV'], 'a', encoding='utf-8') as env:
        env.write('RU_LLVM_CLANG='+tools['clang']+'\n')
        env.write('PATH='+str(mingw/'bin')+';'+os.environ['PATH']+'\n')


def builds(output):
    config = json.loads((output/'base-config.json').read_text(encoding='utf-8'))
    for name, entry in [('app','src/main.ru'), ('argv','tests/bootstrap_pipeline/argv_probe.ru'),
                        ('dll','tests/bootstrap_pipeline/dll_abi_probe.ru')]:
        current = {**config, 'entry_source':entry}
        (output/(name+'-config.json')).write_text(json.dumps(current,indent=2)+'\n',encoding='utf-8')
        try:
            build(current, output/name)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
            def text(value):
                return value.decode('utf-8','replace') if isinstance(value,bytes) else (value or '')
            (output/(name+'-build-failure.log')).write_text(
                json.dumps({'command':error.cmd,'returncode':getattr(error,'returncode',None),
                            'timeout':isinstance(error,subprocess.TimeoutExpired)},default=str)+'\n'+
                text(error.stdout)+'\n'+text(error.stderr),encoding='utf-8')
            raise
    gate = {key:str(output/name/'build-receipt.json') for key,name in
            [('app_receipt','app'),('argv_probe_receipt','argv'),('dll_probe_receipt','dll')]}
    gate.update(dependencies_receipt=str(output/'dependencies/dependencies-receipt.json'),
                owned_root=str(output/'smoke-runtime'), smoke_receipt=str(output/'smoke-acceptance.json'),
                recent_fixtures_receipt=str(output/'recent-fixtures/recent-fixtures.json'))
    (output/'gate-config.json').write_text(json.dumps(gate,indent=2)+'\n',encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('pins','prepare','build'))
    parser.add_argument('--ru-root', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--mingw-root', type=Path)
    args=parser.parse_args()
    if args.action=='pins':
        pin=manifest()['compiler']
        with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as stream:
            stream.write('compiler_commit='+pin['commit']+'\n')
    elif args.action=='prepare':
        require(args.ru_root and args.output and args.mingw_root, 'prepare paths required')
        prepare(args.ru_root.resolve(), args.output.absolute(), args.mingw_root.resolve())
    else:
        require(args.output, 'build output required')
        builds(args.output.absolute())


if __name__=='__main__':
    main()
