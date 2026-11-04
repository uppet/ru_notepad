#!/usr/bin/env python3
"""Compile and execute fourteen reviewed editor fixtures with stage3.

These are additional native feature tests, not the historical 39-fixture C
acceptance. All input, emitted IR, linked binary and executed binary identities
remain pinned to the same application/compiler/tool snapshot as B11.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

# Resolve only this reviewed tools directory, including under Python -I.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from bootstrap_provenance import require, sha, validate_toolchain
from build_bootstrap_release import identity, verify_proof, native_compile_command
from prepare_bootstrap_dependencies import validate_receipt
import verify_bootstrap_editor_windows as smoke

CASES = {'recent_files_policy':25, 'recent_files_native':22, 'recent_files_callbacks':10,
         'ru_lexical_policy':422, 'markdown_policy':221, 'tab_close_policy':16,
         'single_instance_policy':41, 'single_instance_settings_native':11, 'app_tabs_native':709, 'single_instance_native':18, 'single_instance_busy_native':23, 'language_catalog_native':678, 'editor_native':141, 'open_search_native':29}
SCHEMA = 'ru-notepad-bootstrap-editor-fixtures-v6'


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
    validate_compile_policy(report.get('compile_policy'))
    validate_runtime_dependencies(report, app, dependencies)
    frozen = {str((Path(pin['path'])/name).resolve()):digest for key,pin in app['source_pins'].items()
              for name,digest in app['source_sha256'][key].items()}
    frozen[str(compiler.resolve())] = app['bootstrap']['stage3_sha256']
    frozen.update({str(Path(path).resolve()):app['tool_sha256'][name] for name,path in app['tool_paths'].items()})
    validate_toolchain(app['tool_paths'], app['tool_sha256'])
    root = Path(app['source_pins']['app_source']['path'])
    for name,count in CASES.items():
        row=report['results'][name]
        validate_compile_result(row)
        require(row.get('returncode') == 0 and row.get('assertions') == count
                and row.get('executed') is True and row.get('timeout') is False, 'recent native fixture not normally passed')
        for key in ('binary','ir','proof','stdout','stderr'):
            smoke.verify_identity(row[key])
        validate_runtime_dependencies(report, app, dependencies, Path(row['binary']['path']).parent)
        exact_assertions(Path(row['stdout']['path']).read_bytes(),Path(row['stderr']['path']).read_bytes(),row['returncode'],count)
        verify_proof(smoke.read_json(Path(row['proof']['path'])), source=root/'tests'/(name+'.ru'),
                     compiler=compiler, ir=Path(row['ir']['path']), binary=Path(row['binary']['path']),
                     triple=app['target_triple'], layout=app['data_layout'], frozen=frozen, tools=app['tool_paths'], proof_path=Path(row['proof']['path']))



# Only independent compile processes overlap. No application/native fixture runs
# until every compilation and proof has passed. Two-item waves avoid a backlog
# of already-submitted jobs after failure; all report writes stay on this thread.
COMPILE_WORKERS = 2
COMPILE_TIMEOUT = 600
EXECUTE_TIMEOUT = 60
CLEANUP_TIMEOUT = 30
COMPILE_POLICY = {'max_workers':COMPILE_WORKERS,'compile_timeout_seconds':COMPILE_TIMEOUT,
                  'execute_timeout_seconds':EXECUTE_TIMEOUT,'cleanup_timeout_seconds':CLEANUP_TIMEOUT}


def validate_compile_policy(policy):
    require(policy == COMPILE_POLICY and all(type(value) is int for value in policy.values()),
            'fixture compile policy changed')



def validate_compile_result(row):
    require(type(row.get('compile_returncode')) is int and row['compile_returncode'] == 0
            and row.get('compile_timeout') is False
            and 'compile_error' not in row and 'compile_cleanup' not in row,
            'fixture compilation did not normally pass')
    timing = row.get('compile_timing')
    require(isinstance(timing,dict) and set(timing) == {'started','finished','elapsed_seconds'},
            'fixture compile timing missing or changed')
    require(all(type(value) in (int,float) and math.isfinite(value) and value >= 0
                for value in timing.values()), 'fixture compile timing is not finite nonnegative numeric')
    require(timing['finished'] >= timing['started']
            and timing['elapsed_seconds'] == timing['finished']-timing['started'],
            'fixture compile timing is inconsistent')


def timed_compile(compile_one, job):
    started = time.monotonic()
    try:
        result = compile_one(job)
    except BaseException as exc:
        finished = time.monotonic()
        exc.compile_timing = {'started':started,'finished':finished,'elapsed_seconds':finished-started}
        raise
    finished = time.monotonic()
    result.compile_timing = {'started':started,'finished':finished,'elapsed_seconds':finished-started}
    return result



def run_compile_process(command, *, cwd, env):
    process = subprocess.Popen(command, cwd=cwd, env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        stdout, stderr = process.communicate(timeout=COMPILE_TIMEOUT)
    except BaseException as cause:
        # The wrapper launches stage3/clang/linker children. Killing just the
        # Python wrapper (subprocess.run's default) could orphan those children.
        cleanup_error = None
        cleanup_record = {'pid':process.pid,'attempted':False,'returncode':None}
        try:
            if process.poll() is None:
                cleanup_record['attempted'] = True
                cleanup = subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                                         capture_output=True, timeout=CLEANUP_TIMEOUT)
                cleanup_record['returncode'] = cleanup.returncode
                if cleanup.returncode != 0:
                    cleanup_error = RuntimeError('compile process-tree cleanup failed')
        except Exception as exc:
            cleanup_error = exc
            cleanup_record['error'] = str(exc)
        finally:
            if process.poll() is None:
                process.kill()
            try:
                stdout, stderr = process.communicate(timeout=CLEANUP_TIMEOUT)
            except subprocess.TimeoutExpired as exc:
                error=RuntimeError('compile process-tree cleanup did not finish')
                cleanup_record['error']=str(exc)
                error.stdout=getattr(exc,'output',None) or getattr(cause,'output',None) or b''
                error.stderr=getattr(exc,'stderr',None) or getattr(cause,'stderr',None) or b''
                error.cleanup=cleanup_record
                raise error from exc
        stdout = stdout or getattr(cause,'output',None) or b''
        stderr = stderr or getattr(cause,'stderr',None) or b''
        if cleanup_error is not None:
            error = RuntimeError('compile process-tree cleanup unconfirmed: '+str(cleanup_error))
            error.stdout, error.stderr, error.cleanup = stdout, stderr, cleanup_record
            raise error from cause
        cause.cleanup = cleanup_record
        cause.stdout, cause.stderr = stdout, stderr
        if isinstance(cause, subprocess.TimeoutExpired):
            cause.output, cause.stderr = stdout, stderr
        raise
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


def compile_fixture_jobs(jobs, compile_one, record_one):
    """Bounded waves; callbacks consuming results run only on the caller thread.

    In-flight jobs retain their original 600-second per-process deadline. On any
    failure cancel unstarted work, join running work, record the entire wave in
    CASES order, and reject before submitting another wave or executing natives.
    """
    with ThreadPoolExecutor(max_workers=COMPILE_WORKERS) as pool:
        for start in range(0, len(jobs), COMPILE_WORKERS):
            wave = jobs[start:start+COMPILE_WORKERS]
            futures = [pool.submit(timed_compile, compile_one, job) for job in wave]
            results = []
            failed = False
            fatal = None
            for future in futures:
                try:
                    result = future.result()
                    if result.returncode != 0:
                        failed = True
                except BaseException as exc:
                    result = exc
                    failed = True
                    if not isinstance(exc,Exception):fatal = exc
                results.append(result)
                if failed:
                    for pending in futures:
                        pending.cancel()
            for job, result in zip(wave, results):
                record_one(job, result)
            if fatal is not None:raise fatal
            require(not failed, 'recent fixture compile wave failed; native execution not started')


def verify(config, output):
    require(sys.platform == 'win32', 'real Windows required for recent native fixtures')
    receipts=smoke.validate_receipts(config);app=receipts['app_receipt']
    dependencies=validate_receipt(Path(config['dependencies_receipt']))
    require(not output.exists() and not any(p.is_symlink() for p in output.parents), 'fresh fixture output required')
    for pin in app['source_pins'].values():
        require(not output.resolve().is_relative_to(Path(pin['path']).resolve()), 'fixture output cannot dirty source')
    output.mkdir(parents=True)
    report={'schema':SCHEMA,'status':'failed','source_pins':app['source_pins'],
            'stage3_sha256':app['bootstrap']['stage3_sha256'],'compile_policy':dict(COMPILE_POLICY),'results':{}}
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
        jobs=[]
        for name,count in CASES.items():
            source=root/'tests'/(name+'.ru');binary=output/(name+'.exe');ir=output/(name+'.ll');proof_path=output/(name+'.proof.json')
            command=list(map(str,native_compile_command(ru,source,compiler,root,tools,proof_path,ir,binary)))
            report['results'][name]={'executed':False,'timeout':False,'command':command}
            jobs.append(dict(name=name,count=count,source=source,binary=binary,ir=ir,proof=proof_path,command=command))
        save()
        def compile_one(job):
            return run_compile_process(job['command'],cwd=ru,env=env)
        def record_one(job,result):
            row=report['results'][job['name']]
            stdout=getattr(result,'stdout',None) or b''
            stderr=getattr(result,'stderr',None) or b''
            (output/(job['name']+'.build.stdout.log')).write_bytes(stdout)
            (output/(job['name']+'.build.stderr.log')).write_bytes(stderr)
            row['compile_timeout']=isinstance(result,subprocess.TimeoutExpired)
            row['compile_returncode']=getattr(result,'returncode',None)
            if isinstance(result,BaseException):row['compile_error']=type(result).__name__+': '+str(result)
            if hasattr(result,'cleanup'):row['compile_cleanup']=result.cleanup
            if hasattr(result,'compile_timing'):row['compile_timing']=result.compile_timing
            save()
        compile_fixture_jobs(jobs,compile_one,record_one)
        # Validate every output before allowing the first native executable.
        for job in jobs:
            name=job['name'];source=job['source'];binary=job['binary'];ir=job['ir'];proof_path=job['proof']
            row=report['results'][name]
            proof_data=smoke.read_json(proof_path)
            verify_proof(proof_data,source=source,compiler=compiler,ir=ir,binary=binary,
                         triple=app['target_triple'],layout=app['data_layout'],frozen=frozen,tools=tools,proof_path=proof_path)
            row.update(binary=identity(binary),ir=identity(ir),proof=identity(proof_path));save()
        for job in jobs:
            name=job['name'];count=job['count'];binary=job['binary'];row=report['results'][name]
            validate_runtime_dependencies(report, app, dependencies, output)
            for key in ('binary','ir','proof'):smoke.verify_identity(row[key])
            ran=subprocess.run([str(binary)],cwd=output,env=env,capture_output=True,timeout=EXECUTE_TIMEOUT)
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
