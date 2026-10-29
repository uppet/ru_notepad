#!/usr/bin/env python3
"""Compile and execute twelve reviewed editor fixtures with stage3.

These are additional native feature tests, not the historical 39-fixture C
acceptance. All input, emitted IR, linked binary and executed binary identities
remain pinned to the same application/compiler/tool snapshot as B11.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

# Resolve only this reviewed tools directory, including under Python -I.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from bootstrap_provenance import require, sha, validate_toolchain
from build_bootstrap_release import identity, verify_proof, native_compile_command
from prepare_bootstrap_dependencies import validate_receipt
import verify_bootstrap_editor_windows as smoke

CASES = {'recent_files_policy':25, 'recent_files_native':22, 'recent_files_callbacks':10,
         'ru_lexical_policy':422, 'markdown_policy':221, 'tab_close_policy':16,
         'single_instance_policy':41, 'single_instance_settings_native':11, 'app_tabs_native':53, 'single_instance_native':18, 'single_instance_busy_native':23, 'language_catalog_native':678}
SCHEMA = 'ru-notepad-bootstrap-editor-fixtures-v5'


def exact_assertions(stdout, stderr, returncode, count):
    require(returncode == 0 and not stderr, 'recent fixture failed or wrote stderr')
    text=stdout.decode('utf-8',errors='strict')
    require(re.findall(r'^TOTAL PASS: ([0-9]+)\r?$',text,re.M) == [str(count)]
            and len(re.findall(r'^PASS: ',text,re.M)) == count
            and not re.search(r'^(?:FAIL:|SKIP:)',text,re.M), 'recent fixture assertion inventory differs')


def compiler_from_receipt(app, app_receipt):
    proof_path = Path(app_receipt).parent/'compile-proof.json'
    require(sha(proof_path) == app['compile_proof_sha256'], 'app proof changed')
    proof = smoke.read_json(proof_path)
    compiler = Path(proof['compiler']['path'])
    require(identity(compiler) == proof['compiler']
            and sha(compiler) == app['bootstrap']['stage3_sha256'], 'app stage3 identity mismatch')
    return compiler


def validate_runtime_dependencies(report, app, dependencies, directory=None):
    require(dependencies.get('app_source') == app['source_pins']['app_source']
            and dependencies.get('source_sha256') == app['source_sha256']['app_source'],
            'fixture dependency source mismatch')
    records = report.get('runtime_dependencies')
    require(isinstance(records, dict) and set(records) == set(smoke.DLLS),
            'fixture runtime dependency inventory mismatch')
    parents = set()
    for name in smoke.DLLS:
        original = dependencies['binaries'][name]
        smoke.verify_identity(original)
        copied = smoke.verify_identity(records[name])
        require(copied.name == name and records[name]['sha256'] == original['sha256']
                and records[name]['size'] == original['size'], 'fixture runtime DLL differs from dependency snapshot')
        parents.add(copied.parent.resolve())
        if directory is not None:
            require(copied.resolve() == (directory/name).resolve(), 'fixture DLL is not beside executed binary')
    require(len(parents) == 1, 'fixture DLLs are not colocated')


def install_runtime_dependencies(output, app, dependencies):
    require(dependencies.get('app_source') == app['source_pins']['app_source']
            and dependencies.get('source_sha256') == app['source_sha256']['app_source'],
            'fixture dependency source mismatch')
    records = {}
    for name in smoke.DLLS:
        original = dependencies['binaries'][name]
        source = smoke.verify_identity(original)
        destination = output/name
        require(not destination.exists() and not destination.is_symlink(), 'fixture DLL destination exists')
        shutil.copyfile(source, destination)
        smoke.verify_identity(original)
        records[name] = identity(destination)
    validate_runtime_dependencies({'runtime_dependencies':records}, app, dependencies, output)
    return records


def validate_report(report, app, compiler, dependencies):
    require(report.get('schema') == SCHEMA and report.get('status') == 'passed'
            and report.get('source_pins') == app['source_pins'], 'recent fixture report mismatch')
    require(report.get('stage3_sha256') == app['bootstrap']['stage3_sha256']
            and sha(compiler) == app['bootstrap']['stage3_sha256'], 'recent fixture used another stage3')
    require(set(report.get('results',{})) == set(CASES), 'recent native fixture missing')
    validate_runtime_dependencies(report, app, dependencies)
    frozen = {str((Path(pin['path'])/name).resolve()):digest for key,pin in app['source_pins'].items()
              for name,digest in app['source_sha256'][key].items()}
    frozen[str(compiler.resolve())] = app['bootstrap']['stage3_sha256']
    frozen.update({str(Path(path).resolve()):app['tool_sha256'][name] for name,path in app['tool_paths'].items()})
    validate_toolchain(app['tool_paths'], app['tool_sha256'])
    root = Path(app['source_pins']['app_source']['path'])
    for name,count in CASES.items():
        row=report['results'][name]
        require(row.get('returncode') == 0 and row.get('assertions') == count
                and row.get('executed') is True and row.get('timeout') is False, 'recent native fixture not normally passed')
        for key in ('binary','ir','proof','stdout','stderr'):
            smoke.verify_identity(row[key])
        validate_runtime_dependencies(report, app, dependencies, Path(row['binary']['path']).parent)
        exact_assertions(Path(row['stdout']['path']).read_bytes(),Path(row['stderr']['path']).read_bytes(),row['returncode'],count)
        verify_proof(smoke.read_json(Path(row['proof']['path'])), source=root/'tests'/(name+'.ru'),
                     compiler=compiler, ir=Path(row['ir']['path']), binary=Path(row['binary']['path']),
                     triple=app['target_triple'], layout=app['data_layout'], frozen=frozen, tools=app['tool_paths'], proof_path=Path(row['proof']['path']))


def verify(config, output):
    require(sys.platform == 'win32', 'real Windows required for recent native fixtures')
    receipts=smoke.validate_receipts(config);app=receipts['app_receipt']
    dependencies=validate_receipt(Path(config['dependencies_receipt']))
    require(not output.exists() and not any(p.is_symlink() for p in output.parents), 'fresh fixture output required')
    for pin in app['source_pins'].values():
        require(not output.resolve().is_relative_to(Path(pin['path']).resolve()), 'fixture output cannot dirty source')
    output.mkdir(parents=True)
    report={'schema':SCHEMA,'status':'failed','source_pins':app['source_pins'],
            'stage3_sha256':app['bootstrap']['stage3_sha256'],'results':{}}
    save=lambda:(output/'recent-fixtures.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    save()
    ru=Path(app['source_pins']['ru_source']['path']);root=Path(app['source_pins']['app_source']['path'])
    tools=app['tool_paths']
    proof=smoke.read_json(Path(config['app_receipt']).parent/'compile-proof.json')
    compiler=Path(proof['compiler']['path'])
    require(sha(compiler) == app['bootstrap']['stage3_sha256'],'stage3 changed')
    frozen={str((Path(pin['path'])/name).resolve()):digest for key,pin in app['source_pins'].items()
            for name,digest in app['source_sha256'][key].items()}
    frozen[str(compiler.resolve())]=app['bootstrap']['stage3_sha256']
    frozen.update({str(Path(path).resolve()):app['tool_sha256'][name] for name,path in tools.items()})
    spec=importlib.util.spec_from_file_location('_recent_llvm_environment',ru/'rulang/toolchain_environment.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    env=module.llvm_environment()
    try:
        report['runtime_dependencies']=install_runtime_dependencies(output, app, dependencies);save()
        for name,count in CASES.items():
            source=root/'tests'/(name+'.ru');binary=output/(name+'.exe');ir=output/(name+'.ll');proof_path=output/(name+'.proof.json')
            command=list(map(str,native_compile_command(ru,source,compiler,root,tools,proof_path,ir,binary)))
            row={'executed':False,'timeout':False,'command':command};report['results'][name]=row;save()
            built=subprocess.run(command,cwd=ru,env=env,capture_output=True,timeout=600)
            (output/(name+'.build.stdout.log')).write_bytes(built.stdout)
            (output/(name+'.build.stderr.log')).write_bytes(built.stderr)
            require(built.returncode == 0,'recent fixture compile failed')
            proof_data=smoke.read_json(proof_path)
            verify_proof(proof_data,source=source,compiler=compiler,ir=ir,binary=binary,
                         triple=app['target_triple'],layout=app['data_layout'],frozen=frozen,tools=tools,proof_path=proof_path)
            row.update(binary=identity(binary),ir=identity(ir),proof=identity(proof_path));save()
            validate_runtime_dependencies(report, app, dependencies, output)
            ran=subprocess.run([str(binary)],cwd=output,env=env,capture_output=True,timeout=60)
            out=output/(name+'.stdout.log');err=output/(name+'.stderr.log')
            out.write_bytes(ran.stdout);err.write_bytes(ran.stderr)
            row.update(executed=True,returncode=ran.returncode,stdout=identity(out),stderr=identity(err));save()
            exact_assertions(ran.stdout,ran.stderr,ran.returncode,count)
            for key in ('binary','ir','proof'):smoke.verify_identity(row[key])
            validate_runtime_dependencies(report, app, dependencies, output)
            row['assertions']=count;save()
        smoke.validate_receipts(config)
        validate_toolchain(tools,app['tool_sha256'])
        dependencies=validate_receipt(Path(config['dependencies_receipt']))
        report['status']='passed';validate_report(report,app,compiler,dependencies)
    except subprocess.TimeoutExpired as exc:
        row['timeout']=True
        (output/(name+'.timeout.stdout.log')).write_bytes(exc.stdout or b'')
        (output/(name+'.timeout.stderr.log')).write_bytes(exc.stderr or b'')
        report['error']='recent fixture timed out';report['status']='failed'
    except Exception as exc:
        report['error']=str(exc);report['status']='failed'
    save();return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=verify(smoke.read_json(args.config),args.output.absolute())
    return 0 if result['status']=='passed' else 1


if __name__=='__main__':raise SystemExit(main())
