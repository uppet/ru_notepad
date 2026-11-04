#!/usr/bin/env python3
"""Complete Python ABI analysis; optional, disclosed development-only budget.

The pinned compiler files, production 200000-step limit and all other analysis
limits remain unchanged. This tool is not a C-build or Windows acceptance gate.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
import sys
import subprocess
import time

ORACLE='packaging/application-native-oracle.json'
DEFAULT_BUDGET=200000
DEVELOPMENT_BUDGET=2000000
CORE_COMMIT='c3bb177c6a15e90821e5495cc74b0fdfc39b893a'
CORE_TREE='5dedbf06f9fb6e00fbfe779b33f172aa35b61334'
ANALYZER_SHA256='feb931b4990e19c93fc680bb50385ab8736aee9e52925214a13aed17989bf454'
DEFAULT_SCOPE='independent Python development oracle with unmodified 200000-step default analysis budget, not C/stage3/LLVM/Windows evidence'
SCOPE='independent Python development oracle with isolated 2000000-step analysis budget, not default-limit C/stage3/LLVM/Windows evidence'

def require(condition, message):
    if not condition:
        raise ValueError(message)

def verify_compiler(core):
    def git(*args):
        return subprocess.check_output(['git','-C',str(core),*args],text=True).strip()
    require(git('rev-parse','HEAD')==CORE_COMMIT, 'core commit differs from reviewed pin')
    require(git('rev-parse','HEAD^{tree}')==CORE_TREE, 'core tree differs from reviewed pin')
    require(not git('status','--porcelain'), 'core must be clean')
    require(sha((core/'rulang/native_c.py').read_bytes())==ANALYZER_SHA256, 'core analyzer pin differs')

def verify_sources(inputs):
    require(inputs=={path:sha(Path(path).read_bytes()) for path in inputs},
            'module source changed during analysis')

def sha(data): return hashlib.sha256(data).hexdigest()

def public_failure(data):
    """Keep diagnostic facts, replacing only the machine-specific path prefix."""
    text=data.decode('utf-8')
    lines=text.splitlines(keepends=True)
    if not lines:
        raise ValueError('Missing default-limit diagnostic')
    marker='src/file_codec.ru:'
    first=lines[0].replace('\\','/')
    position=first.find(marker)
    if position < 0:
        raise ValueError('Unexpected diagnostic source identity')
    lines[0]=first[position:]
    result=''.join(lines)
    if not re.match(r'^src/file_codec\.ru:\d+:\d+: error:',result):
        raise ValueError('Unexpected diagnostic format')
    if any(part in result for part in ('/workspace/', '/tmp/', '/home/', 'C:/', 'D:/')):
        raise ValueError('Diagnostic contains an unexpected local path')
    return result.encode('utf-8')

def analyze(native_c, graph, root, core, error_type, development_budget=False):
    diagnostics=[]
    current_failure=None
    budget=DEFAULT_BUDGET
    started=time.monotonic()
    try:
        plan=native_c.NativeCPlan(graph, diagnostics=diagnostics.append)
    except error_type as error:
        # Only the exact default step-budget exhaustion permits the explicit
        # development retry. Other analyzer failures must still stop refresh.
        require(len(diagnostics)==1 and diagnostics[0]['completed'] is False
                and diagnostics[0]['steps']==DEFAULT_BUDGET+1
                and diagnostics[0]['step_limit']==DEFAULT_BUDGET
                and str(error).startswith('原生签名静态分析超过复杂度上限'),
                'default analysis failed for a reason other than step exhaustion')
        if not development_budget:
            raise
        location=Path(error.source_name).resolve()
        require(location.is_relative_to(root) or location.is_relative_to(core),
                'default diagnostic outside reviewed source')
        current_failure={'compiler_commit':CORE_COMMIT, 'compiler_tree':CORE_TREE,
                         'source':location.relative_to(root if location.is_relative_to(root) else core).as_posix(),
                         'line':error.line, 'column':error.col, 'message':str(error),
                         'steps':diagnostics[0]['steps'], 'step_limit':DEFAULT_BUDGET,
                         'modules':diagnostics[0]['modules'], 'signatures':diagnostics[0]['signatures'],
                         'function_evaluations':diagnostics[0]['function_evaluations'],
                         'summary_hits':diagnostics[0]['summary_hits']}
        budget=DEVELOPMENT_BUDGET
        try:
            native_c.MAX_ANALYSIS_STEPS=budget
            plan=native_c.NativeCPlan(graph, diagnostics=diagnostics.append)
        finally:
            native_c.MAX_ANALYSIS_STEPS=DEFAULT_BUDGET
    elapsed=time.monotonic()-started
    require(native_c.MAX_ANALYSIS_STEPS==DEFAULT_BUDGET, 'production limit not restored')
    require(plan._steps<=budget, 'analysis budget exceeded')
    require(len(diagnostics)==(2 if current_failure else 1) and diagnostics[-1]['completed'] is True
            and diagnostics[-1]['step_limit']==budget
            and diagnostics[-1]['steps']==plan._steps, 'incomplete analysis diagnostics')
    return plan, current_failure, budget, elapsed

def refresh(root, core, write=False, development_budget=False):
    verify_compiler(core)
    compiler_inputs={str(p):sha(p.read_bytes()) for p in sorted((core/'rulang').rglob('*.py'))}
    sys.path.insert(0,str(core))
    from rulang.frontend import parse, RuError
    from rulang.modules import load_module_graph
    import rulang.native_c as native_c
    from rulang.native_c import NativeCPlan, MAX_ANALYSIS_STEPS
    require(MAX_ANALYSIS_STEPS==DEFAULT_BUDGET, "unexpected production analysis limit")
    for name,module in tuple(sys.modules.items()):
        if name=="rulang" or name.startswith("rulang."):
            require(Path(module.__file__).resolve().is_relative_to(core), "compiler import outside pinned checkout")
    source=core/'rulang/native_c.py'
    source_hash=sha(source.read_bytes())
    require(source_hash==ANALYZER_SHA256, 'core analyzer pin differs')
    graph=load_module_graph(str(root/'src/main.ru'),parse((root/'src/main.ru').read_text()))
    source_inputs={path:sha(Path(path).read_bytes()) for path in graph}
    for path,text in graph.sources.items():
        require(sha(text.encode('utf-8'))==source_inputs[path], 'source changed while parsing')
    plan, current_failure, budget, elapsed=analyze(native_c, graph, root, core, RuError, development_budget)
    verify_compiler(core)
    require(compiler_inputs=={str(p):sha(p.read_bytes()) for p in sorted((core/'rulang').rglob('*.py'))}, 'compiler inputs changed during analysis')
    verify_sources(source_inputs)
    old={'schema':'ru-notepad-application-native-oracle-v1', 'scope':SCOPE if current_failure else DEFAULT_SCOPE,
         'application_base_commit':'b79baa824b0a48f564ad95447e4ce64cc5b5911b',
         'compiler_commit':CORE_COMMIT, 'compiler_tree':CORE_TREE, 'entry':'src/main.ru'}
    rows=[]
    for path in graph:
        path=Path(path);data=path.read_bytes()
        scope='app' if path.is_relative_to(root) else 'compiler'
        relative=path.relative_to(root if scope=='app' else core).as_posix()
        rows.append({'scope':scope,'path':relative,'sha256':sha(data),
                     'git_blob':hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()})
    def shapes(values):
        return [{'result':s.result,'parameters':list(s.params)} for s in sorted(values,key=lambda s:(s.result,s.params))]
    old['modules']=rows;old['shapes']=shapes(plan.signatures);old['callbacks']=shapes(plan.callback_signatures)
    failure=root/'packaging/application-native-oracle-default-failure.txt'
    failure_bytes=public_failure(failure.read_bytes())
    require('原生签名静态分析超过复杂度上限' in failure_bytes.decode('utf-8'), 'unexpected historical diagnostic')
    proof={'schema':'ru-notepad-development-native-oracle-v1',
           'method':'Complete independent Python NativeCPlan over every current module and dormant function; no retained shapes reused.',
           'scope':'Development oracle only; not a production C build or stage3/LLVM/Windows acceptance result.',
           'compiler_commit':old['compiler_commit'],'compiler_tree':old['compiler_tree'],
           'analyzer_source_sha256':source_hash,'compiler_python_sources_sha256':{str(Path(p).relative_to(core)):h for p,h in compiler_inputs.items()},'production_default_step_limit':DEFAULT_BUDGET,
           'default_limit_result':('Current pinned compiler failed on the final source at the unmodified 200000-step production default; current_default_limit_failure records this run. Complete ABI oracle uses an isolated development budget.' if current_failure else 'Current pinned compiler completed the final source at the unmodified 200000-step production default.'),
           'default_limit_failure':{'historical':True,'compiler_commit':'b93b23dd545e5e392544b4c411db30e9c2d7d15a','path':str(failure.relative_to(root)),'sha256':sha(failure_bytes),'command':'python3 <b93>/ru check --allow-native src/main.ru','path_redaction':'Machine-specific prefix removed; source-relative path, line, column and diagnostic retained.'},
           'current_default_limit_failure':current_failure,
           'isolated_development_step_limit':DEVELOPMENT_BUDGET if current_failure else None,'analysis_step_limit':budget,'actual_steps':plan._steps,
           'elapsed_seconds':round(elapsed,6),'other_analysis_limits':'unchanged',
           'compiler_files_modified':False,'modules':len(rows),'shapes':len(old['shapes']),'callbacks':len(old['callbacks']),
           'module_sha256':{r['scope']+':'+r['path']:r['sha256'] for r in rows}}
    oracle_bytes=(json.dumps(old,ensure_ascii=False,indent=2)+'\n').encode()
    proof['oracle_sha256']=sha(oracle_bytes)
    verify_sources(source_inputs)
    if write:
        failure.write_bytes(failure_bytes)
        (root/ORACLE).write_bytes(oracle_bytes)
        (root/'packaging/application-native-oracle-development.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
    return proof

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--core',type=Path,required=True)
    p.add_argument('--write',action='store_true')
    p.add_argument('--development-budget',action='store_true', help='Allow an isolated 2000000-step retry after verified default-budget exhaustion; not production acceptance')
    a=p.parse_args();proof=refresh(a.root.resolve(),a.core.resolve(),a.write,a.development_budget)
    print(json.dumps(proof,indent=2))
