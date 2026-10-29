#!/usr/bin/env python3
"""Development-only complete Python ABI analysis with a disclosed isolated budget.

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

def refresh(root, core, write=False):
    expected_tree='a15bc85adafdb512af53b4ead8e33be3b48ed70a'
    tree=subprocess.check_output(['git','-C',str(core),'rev-parse','HEAD^{tree}'],text=True).strip()
    assert tree==expected_tree, 'core tree differs from b93'
    subprocess.run(['git','-C',str(core),'diff','--exit-code','HEAD','--'],check=True,stdout=subprocess.DEVNULL)
    compiler_inputs={str(p):sha(p.read_bytes()) for p in sorted((core/'rulang').rglob('*.py'))}
    sys.path.insert(0,str(core))
    from rulang.frontend import parse
    from rulang.modules import load_module_graph
    from rulang.native_c import NativeCPlan
    source=core/'rulang/native_c.py'
    source_hash=sha(source.read_bytes())
    assert source_hash=='6b7ea8302508bd375b715a61e2896a38c8766c09dc01f17fdd552c48d03057d5', 'core analyzer pin differs'
    graph=load_module_graph(str(root/'src/main.ru'),parse((root/'src/main.ru').read_text()))
    source_inputs={path:sha(Path(path).read_bytes()) for path in graph}
    for path,text in graph.sources.items():
        assert sha(text.encode('utf-8'))==source_inputs[path], 'source changed while parsing'
    original=NativeCPlan._expr.__code__
    assert original.co_consts.count(DEFAULT_BUDGET)==1, 'unexpected analyzer budget bytecode'
    assert DEVELOPMENT_BUDGET not in original.co_consts
    started=time.monotonic()
    try:
        NativeCPlan._expr.__code__=original.replace(co_consts=tuple(
            DEVELOPMENT_BUDGET if type(x) is int and x==DEFAULT_BUDGET else x
            for x in original.co_consts))
        plan=NativeCPlan(graph)
    finally:
        NativeCPlan._expr.__code__=original
    elapsed=time.monotonic()-started
    assert sha(source.read_bytes())==source_hash, 'compiler file changed'
    assert plan._steps<=DEVELOPMENT_BUDGET
    assert compiler_inputs=={str(p):sha(p.read_bytes()) for p in sorted((core/'rulang').rglob('*.py'))}, 'compiler inputs changed during analysis'
    assert source_inputs=={path:sha(Path(path).read_bytes()) for path in graph}, 'module source changed during analysis'
    old=json.loads((root/ORACLE).read_text())
    assert old['compiler_commit']=='b93b23dd545e5e392544b4c411db30e9c2d7d15a'
    assert old['compiler_tree']==expected_tree
    rows=[]
    for path in graph:
        path=Path(path);data=path.read_bytes()
        scope='app' if path.is_relative_to(root) else 'compiler'
        relative=path.relative_to(root if scope=='app' else core).as_posix()
        rows.append({'scope':scope,'path':relative,'sha256':sha(data),
                     'git_blob':hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()})
    def shapes(values):
        return [{'result':s.result,'parameters':list(s.params)} for s in sorted(values,key=lambda s:(s.result,s.params))]
    old['scope']='independent Python development oracle with isolated 2000000-step analysis budget, not default-limit C/stage3/LLVM/Windows evidence'
    old['modules']=rows;old['shapes']=shapes(plan.signatures);old['callbacks']=shapes(plan.callback_signatures)
    failure=root/'packaging/application-native-oracle-default-failure.txt'
    failure_bytes=public_failure(failure.read_bytes())
    assert '原生签名静态分析超过复杂度上限' in failure_bytes.decode('utf-8')
    proof={'schema':'ru-notepad-development-native-oracle-v1',
           'method':'Complete independent Python NativeCPlan over every current module and dormant function; no retained shapes reused.',
           'scope':'Development oracle only; not a production C build or stage3/LLVM/Windows acceptance result.',
           'compiler_commit':old['compiler_commit'],'compiler_tree':old['compiler_tree'],
           'analyzer_source_sha256':source_hash,'compiler_python_sources_sha256':{str(Path(p).relative_to(core)):h for p,h in compiler_inputs.items()},'production_default_step_limit':DEFAULT_BUDGET,
           'default_limit_result':'Earlier development candidate failed at 200000 steps; retained diagnostic is not represented as a rerun of the final source.',
           'default_limit_failure':{'path':str(failure.relative_to(root)),'sha256':sha(failure_bytes),'command':'python3 <b93>/ru check --allow-native src/main.ru','path_redaction':'Machine-specific prefix removed; source-relative path, line, column and diagnostic retained.'},
           'isolated_development_step_limit':DEVELOPMENT_BUDGET,'actual_steps':plan._steps,
           'elapsed_seconds':round(elapsed,6),'other_analysis_limits':'unchanged',
           'compiler_files_modified':False,'modules':len(rows),'shapes':len(old['shapes']),'callbacks':len(old['callbacks']),
           'module_sha256':{r['scope']+':'+r['path']:r['sha256'] for r in rows}}
    oracle_bytes=(json.dumps(old,ensure_ascii=False,indent=2)+'\n').encode()
    proof['oracle_sha256']=sha(oracle_bytes)
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
    a=p.parse_args();proof=refresh(a.root.resolve(),a.core.resolve(),a.write)
    print(json.dumps(proof,indent=2))
