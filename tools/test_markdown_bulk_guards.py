#!/usr/bin/env python3
"""Execute complete production bulk publication/guards with controlled FFI boundaries.

Pure Ru semantic evidence only. The fake helper models rejection/partial-result
boundaries; it does not certify native pointer safety or Windows performance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from ru_cli_diagnostics import prepare_compile_diagnostics, validate_stderr
BASELINE_ELIGIBILITY = '    _须直属 柄 态 权.\n    _护 柄 态.\n    掩码 取 (_讯 柄 态 2378 0 0) 其 数.\n    自动 取 (_讯 柄 态 2664 0 0) 其 数.\n    _须直属 柄 态 权.\n'
CANDIDATE_ELIGIBILITY = '    _须直属 柄 态 权.\n    # Share only adjacent complete post/pre guards. Each guard may reenter;\n    # every original owner/document/length check inside it remains unchanged.\n    _护 柄 态.\n    掩码果 取 窗 其 发送 柄 2378 0 0.\n    _护 柄 态.\n    掩码 取 掩码果 其 数.\n    自动果 取 窗 其 发送 柄 2664 0 0.\n    _护 柄 态.\n    自动 取 自动果 其 数.\n    _须直属 柄 态 权.\n'
HEAD = "窗 取 外言 'boundary.ru'.\n_GetCurrentThreadId 取 窗 其 CurrentThread.\n_GetWindowThreadProcessId 取 窗 其 WindowThread.\n_IsWindow 取 窗 其 IsWindow.\n_GetParent 取 窗 其 Parent.\n_FoldApply 取 窗 其 Apply.\n_编辑们 取 窗 其 Editors. _直属们 取 窗 其 Caps.\n_直接策略 取 窗 其 Route. _直库态 取 窗 其 Direct. _批库态 取 窗 其 Bulk.\n_批计划型 取 窗 其 Plan. _批果型 取 窗 其 Result.\n_批范围名 取 []. 位号 取 0.\n循 64 次 _批范围名 其 增 ('range'+(位号 为 句)). 位号 取 位号+1. 环\n算 _直发布 柄 态 范围们 位 为 数 偏 为 数: 卒 'unexpected perline route'. 法\n算 _统计 柄 态: 得 窗 其 Metrics. 法\n算 _统计时刻 计: 得 1. 法\n算 _统计耗时 计 始 为 数: 得 空. 法\n"
NAMES = ['_线程', '_同线程', '_本态', '_须本态', '_护', '_讯', '_须直属', '_验范围', '_批移位', '_写批计划', '_验批果', '_批发布', '_检查', '_发布']
BOUNDARY = "控 取 {'send':0,'native':0,'trigger':0,'action':'','fired':假,'alive':真,'length':100,'document':'doc','parent':'parent','mask':3,'auto':0,'apply':0,'writes':0,'active':0,'closes':0,'convert':0,'result':[],'trace':[],'conversions':[],'mode':'success'}.\nEditors 取 {}. Caps 取 {}. Route 取 {'enabled':真,'route':'bulk'}.\nDirect 取 {'ready':真,'module':'module'}. Bulk 取 {'ready':真,'abi':65536}.\nMetrics 取 {'maxPlanBytes':0,'ownedBufferBytes':0,'bulkCalls':0,'bulkLines':0}.\n算 改动:\n    控 其 增 'fired' 真. 动 取 控['action'].\n    若 动 == 'panic' 则 卒 'injected callback error'. 然\n    若 动 == 'replace' 或 动 == 'generation' 则 Editors 其 增 'editor' ({'identity':2,'alive':真,'hwnd':'editor','generation':8,'revision':1,'document':'doc','thread':'thread'}). 然\n    若 动 == 'close' 则 控 其 增 'alive' 假. Editors 其 除 'editor'. 然\n    若 动 == 'length' 则 控 其 增 'length' 101. 然\n    若 动 == 'document' 则 控 其 增 'document' 'other'. 然\n    若 动 == 'revoke' 则 Caps 其 除 'editor'. 然\n    若 动 == 'capability' 则 Caps 其 增 'editor' ({}). 然\n    若 动 == 'reparent' 则 控 其 增 'parent' 'other'. 然\n    若 动 == 'reselect' 则 (Editors 其 查 'editor') 其 增 'language' 'plain'. 然\n    若 动 == 'route' 则 Route 其 增 'route' 'perline'. 然\n    若 动 == 'mask' 则 控 其 增 'mask' 0. 然\n    若 动 == 'auto' 则 控 其 增 'auto' 1. 然\n    若 动 == 'direct' 则 Direct 其 增 'ready' 假. 然\n    若 动 == 'abi' 则 Bulk 其 增 'abi' 0. 然\n    得 空.\n法\n形 标量:\n    值 为 数. 文 为 句. 消息 为 数.\n    算 数:\n        (控['conversions']) 其 增 (其 消息).\n        若 控['convert'] != 0 且 控['convert'] == 其 消息 则 卒 'injected scalar conversion'. 然\n        得 其 值.\n    法\n    算 句: 得 其 文. 法\n    算 为空: 得 其 值 == 0. 法\n象\n算 值 数值 为 数 文值 为 句 号 为 数:\n    得 新 标量 值:数值 文:文值 消息:号.\n法\n算 结果 果: 得 果. 法\n算 发送 柄 号 为 数 宽 长:\n    控 其 增 'send' (控['send']+1). 控 其 增 'native' (控['native']+1).\n    (控['trace']) 其 增 号.\n    若 控['send'] == 控['trigger'] 则 改动. 然\n    若 号 == 2357 则 得 值 23 控['document'] 号. 然\n    若 号 == 2183 则 得 值 控['length'] '' 号. 然\n    若 号 == 2378 则 得 值 控['mask'] '' 号. 然\n    若 号 == 2664 则 得 值 控['auto'] '' 号. 然\n    若 号 == 2383 则 得 值 0 '' 号. 然\n    若 号 == 2222 则 控 其 增 'writes' (控['writes']+1). 得 值 0 '' 号. 然\n    若 号 == 2185 则 得 值 99 'pointer' 号. 然\n    卒 'unexpected message'.\n法\n形 指针型:\n    算 重释 原: 得 原. 法\n象\nPTR 取 新 指针型.\n形 原口:\n    名 为 句.\n    算 调用 参数:\n        控 其 增 'native' (控['native']+1).\n        若 其 名 == 'current' 或 其 名 == 'thread' 则 得 值 7 'thread' 0. 然\n        若 其 名 == 'window' 则 若 控['alive'] 则 得 值 1 '' 0. 然 得 值 0 '' 0. 然\n        若 其 名 == 'parent' 则 得 值 18 控['parent'] 0. 然\n        若 其 名 == 'apply' 则\n            控 其 增 'apply' (控['apply']+1).\n            # Model only the reviewed helper's rejection boundary, NOT its C implementation.\n            若 控['document'] != 'doc' 或 控['length'] != 100 或 非 控['alive'] 则\n                控 其 增 'result' ([2,0,0,0,0,0,0,0]). 得 值 2 '' 0.\n            然\n            若 控['mask'] != 3 或 控['auto'] != 0 则\n                控 其 增 'result' ([1,0,0,0,0,0,0,0]). 得 值 1 '' 0.\n            然\n            若 控['mode'] == 'partial' 则\n                控 其 增 'writes' 1. 控 其 增 'result' ([4,2,1,0,2,5,0,0]). 得 值 4 '' 0.\n            然\n            控 其 增 'writes' 64. 控 其 增 'result' ([0,64,64,0,64,0,0,0]). 得 值 0 '' 0.\n        然\n        卒 'unexpected native call'.\n    法\n象\nCurrentThread 取 新 原口 名:'current'. WindowThread 取 新 原口 名:'thread'.\nIsWindow 取 新 原口 名:'window'. Parent 取 新 原口 名:'parent'. Apply 取 新 原口 名:'apply'.\n形 缓冲:\n    大小 为 数. 根 为 事实.\n    算 写 名 为 句 内容: 得 空. 法\n    算 读 名 为 句: 得 新 缓冲 大小:0 根:假. 法\n    算 读U32LE阵 起 为 数 数量 为 数:\n        若 起 != 0 或 数量 != 8 则 卒 'result bounds'. 然\n        得 控['result'].\n    法\n    算 关闭:\n        若 其 根 则 控 其 增 'active' (控['active']-1). 控 其 增 'closes' (控['closes']+1). 然\n        得 空.\n    法\n象\n形 工厂:\n    长 为 数.\n    算 新建:\n        控 其 增 'active' (控['active']+1).\n        得 新 缓冲 大小:其 长 根:真.\n    法\n象\nPlan 取 新 工厂 长:1056. Result 取 新 工厂 长:32.\n算 重置:\n    控 其 增 'send' 0. 控 其 增 'native' 0. 控 其 增 'trigger' 0. 控 其 增 'action' ''. 控 其 增 'fired' 假.\n    控 其 增 'alive' 真. 控 其 增 'length' 100. 控 其 增 'document' 'doc'. 控 其 增 'parent' 'parent'.\n    控 其 增 'mask' 3. 控 其 增 'auto' 0. 控 其 增 'apply' 0. 控 其 增 'writes' 0.\n    控 其 增 'active' 0. 控 其 增 'closes' 0. 控 其 增 'convert' 0.\n    控 其 增 'result' ([]). 控 其 增 'trace' ([]). 控 其 增 'conversions' ([]). 控 其 增 'mode' 'success'.\n    Route 其 增 'enabled' 真. Route 其 增 'route' 'bulk'. Direct 其 增 'ready' 真. Bulk 其 增 'ready' 真. Bulk 其 增 'abi' 65536.\n    Metrics 其 增 'maxPlanBytes' 0. Metrics 其 增 'bulkCalls' 0. Metrics 其 增 'bulkLines' 0.\n    态 取 {'identity':1,'alive':真,'hwnd':'editor','generation':7,'revision':0,'document':'doc','thread':'thread','length':100,'lines':100,'language':'markdown','registered':真,'phase':'scan','pending':真,'foldEnabled':真,'ranges':[[0,100,0,假]],'rangeIndex':0,'rangeOffset':0,'published':0,'maxPublish':0}.\n    Editors 其 增 'editor' 态.\n    Caps 其 增 'editor' ({'ready':真,'token':1,'generation':7,'document':'doc','thread':'thread','parent':(值 18 'parent' 0)}).\n    得 态.\n法\n"

COMPACT_PROBE = "作 确认 条件 为 事实 文 为 句:\n    若 非 条件 则 卒 ('FAIL: '+文). 然\n    次数[0] 取 次数[0]+1. 显 'PASS: '+文.\n为\n算 执行:\n    态 取 边 其 Editors 其 查 'editor'. 范围们 取 [[0,100,0,假]].\n    得 模 其 _批发布 (边 其 值 17 'editor' 0) 态 范围们 0 0.\n法\n控 取 边 其 控.\n边 其 重置. 果 取 执行.\n确认 (果[0] == 0 且 果[1] == 64 且 果[2] == 64 且 控['apply'] == 1 且 控['writes'] == 64 且 控['active'] == 0 且 控['closes'] == 2) 'healthy result and resource lifetime unchanged'.\n确认 (控['send'] == 总数 且 控['native'] == 原生数) 'exact healthy message and native call inventory'.\n显 'TRACE '+(控['trace'] 为 句).\n动作们 取 ['panic','replace','generation','close','length','document','revoke','capability','reparent','reselect','route','mask','auto','direct','abi'].\n原因们 取 {'replace':'Stale Markdown owner.','generation':'Stale Markdown owner.','close':'Stale Markdown owner.','length':'Markdown text changed without invalidation.','document':'Stale Markdown document.','revoke':'Stale Markdown direct capability.','capability':'Stale Markdown direct capability.','reparent':'Reparented Markdown direct editor.','reselect':'Markdown direct owner is not selected.','panic':'injected callback error'}.\n边位 取 1.\n循 前数 次\n    动位 取 0.\n    循 动作们 其 量 次\n        动 取 动作们[动位]. 边 其 重置. 控 其 增 'trigger' 边位. 控 其 增 'action' 动. 错 取 ['']. 果盒 取 [空].\n        试 果盒[0] 取 执行. 救 原因 错[0] 取 原因. 终\n        理由符 取 真.\n        若 边位 == 1 且 ((原因们 其 查 动) != 空) 则 理由符 取 错[0] == 原因们[动]. 然\n        确认 (理由符 且 控['fired'] 且 控['writes'] == 0 且 控['apply'] <= 1 且 控['active'] == 0 且 (错[0] != '' 或 果盒[0] == 空)) ('preapply boundary '+(边位 为 句)+' '+动+' rejects without writes or unsafe success').\n        动位 取 动位+1.\n    环\n    边位 取 边位+1.\n环\n后动作们 取 ['panic','replace','close','length','document','revoke','capability','reparent','reselect'].\n边位 取 前数+1.\n循 2 次\n    动位 取 0.\n    循 后动作们 其 量 次\n        动 取 后动作们[动位].\n        若 非 (边位 == 总数 且 动 == 'document') 则\n            边 其 重置. 控 其 增 'trigger' 边位. 控 其 增 'action' 动. 错 取 [''].\n            试 执行. 救 原因 错[0] 取 原因. 终\n            确认 (控['fired'] 且 控['apply'] == 1 且 控['writes'] == 64 且 控['active'] == 0 且 错[0] != '') ('postapply boundary '+(边位 为 句)+' '+动+' propagates and cannot replay').\n        然\n        动位 取 动位+1.\n    环\n    边位 取 边位+1.\n环\n边 其 重置. 控 其 增 'trigger' (总数+2). 控 其 增 'action' 'document'. 态 取 边 其 Editors 其 查 'editor'. 错 取 [''].\n试 模 其 _发布 (边 其 值 17 'editor' 0) 态. 救 原因 错[0] 取 原因. 终\n确认 (控['fired'] 且 控['apply'] == 1 且 控['writes'] == 64 且 控['active'] == 0 且 态['published'] == 0 且 错[0] == 'Stale Markdown document.') 'outer unchanged postguard catches late document change before cursor commit without replay'.\n消息们 取 [2378,2664]. 后位们 取 [首后,次后]. 位 取 0.\n循 2 次\n    消 取 消息们[位]. 后位 取 后位们[位].\n    边 其 重置. 控 其 增 'convert' 消. 错 取 [''].\n    试 执行. 救 原因 错[0] 取 原因. 终\n    确认 (错[0] == 'injected scalar conversion' 且 控['apply'] == 0 且 控['active'] == 0 且 控['send'] == 后位+1) ('conversion '+(消 为 句)+' occurs only after complete postguard').\n    边 其 重置. 控 其 增 'convert' 消. 控 其 增 'trigger' 后位. 控 其 增 'action' 'replace'. 错 取 [''].\n    试 执行. 救 原因 错[0] 取 原因. 终\n    确认 (错[0] == 'Stale Markdown owner.' 且 控['apply'] == 0 且 控['active'] == 0) ('postguard owner error precedes conversion '+(消 为 句)).\n    位 取 位+1.\n环\n边 其 重置. 控 其 增 'mode' 'partial'. 错 取 [''].\n试 执行. 救 原因 错[0] 取 原因. 终\n确认 (错[0] == 'Markdown bulk publication failed with status 4.' 且 控['apply'] == 1 且 控['writes'] == 1 且 控['active'] == 0) 'partial native failure is never ordinary fallback or replay'.\n边 其 重置. 态 取 边 其 Editors 其 查 'editor'. 错 取 ['']. 坏范围们 取 [[0,101,0,假]].\n试 模 其 _批发布 (边 其 值 17 'editor' 0) 态 坏范围们 0 0. 救 原因 错[0] 取 原因. 终\n确认 (错[0] == 'Invalid Markdown fold assignment.' 且 控['apply'] == 0 且 控['active'] == 0 且 控['closes'] == 2) 'invalid plan retains exact error and owned resource cleanup'.\n显 'TOTAL PASS: '+(次数[0] 为 句).\n"

def probe_text(variant):
    total,pre,native,m1post,m2post = {"baseline":(20,18,159,6,11),"candidate":(16,14,131,4,7)}[variant]
    return "模 取 外言 '"+variant+"-module.ru'.\n边 取 外言 'boundary.ru'.\n次数 取 [0].\n"+f"总数 取 {total}. 前数 取 {pre}. 原生数 取 {native}. 首后 取 {m1post}. 次后 取 {m2post}.\n"+COMPACT_PROBE


def identity(path):
    path=Path(path)
    return {'path':str(path.resolve()),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'size':path.stat().st_size}


def prepare(source,directory,core):
    sys.path.insert(0,str(core))
    from rulang.frontend import parse
    text=source.read_text(encoding='utf-8');nodes=parse(text);bodies={}
    for i,node in enumerate(nodes):
        if node.kind=='function' and node.data['name'] in NAMES:
            end=nodes[i+1].token.line-1
            bodies[node.data['name']]=''.join(text.splitlines(keepends=True)[node.token.line-1:end])
    if set(bodies)!=set(NAMES) or bodies['_批发布'].count(CANDIDATE_ELIGIBILITY)!=1:
        raise ValueError('reviewed complete production dependency/body inventory changed')
    for variant in ('baseline','candidate'):
        module=HEAD+''.join(bodies[n].replace(CANDIDATE_ELIGIBILITY,BASELINE_ELIGIBILITY) if variant=='baseline' and n=='_批发布' else bodies[n] for n in NAMES)
        (directory/(variant+'-module.ru')).write_text(module,encoding='utf-8',newline='\n')
        (directory/(variant+'-probe.ru')).write_text(probe_text(variant),encoding='utf-8',newline='\n')
    (directory/'boundary.ru').write_text(BOUNDARY,encoding='utf-8',newline='\n')
    return {n:hashlib.sha256(body.encode('utf-8')).hexdigest() for n,body in bodies.items()}


def validate_output(text,variant):
    count={'baseline':296,'candidate':236}[variant]
    trace={'baseline':[2357,2183,2357,2183,2378,2357,2183,2357,2183,2664,2357,2183,2357,2183,2357,2357,2183,2185,2357,2183],
           'candidate':[2357,2183,2378,2357,2183,2664,2357,2183,2357,2183,2357,2357,2183,2185,2357,2183]}[variant]
    lines=text.splitlines()
    if (len(lines)!=count+2 or sum(line.startswith('PASS: ') for line in lines)!=count or
        lines[2]!='TRACE '+str(trace) or lines[-1]!=f'TOTAL PASS: {count}'):
        raise ValueError('complete guard boundary assertion/trace inventory mismatch')
    return count


def negative_controls(directory,core):
    original=(directory/'candidate-module.ru').read_text(encoding='utf-8')
    anchor="    掩码果 取 窗 其 发送 柄 2378 0 0.\n    _护 柄 态.\n    掩码 取 掩码果 其 数."
    if original.count(anchor)!=1:raise ValueError('negative guard anchor changed')
    variants={'positive':original,
              'missing-middle-guard':original.replace(anchor,"    掩码果 取 窗 其 发送 柄 2378 0 0.\n    掩码 取 掩码果 其 数.",1),
              'early-conversion':original.replace(anchor,"    掩码果 取 窗 其 发送 柄 2378 0 0.\n    掩码 取 掩码果 其 数.\n    _护 柄 态.",1)}
    probe="""模 取 外言 'negative-module.ru'.
边 取 外言 'boundary.ru'.
态 取 边 其 重置. 控 取 边 其 控.
控 其 增 'trigger' 3. 控 其 增 'action' 'replace'. 控 其 增 'convert' 2378.
错 取 ['']. 范围们 取 [[0,100,0,假]].
试 模 其 _批发布 (边 其 值 17 'editor' 0) 态 范围们 0 0. 救 原因 错[0] 取 原因. 终
若 错[0] != 'Stale Markdown owner.' 或 控['send'] != 3 或 控['apply'] != 0 或 控['active'] != 0 则 卒 'NEGATIVE_GUARD_ORDER_DETECTED'. 然
显 'GUARD_ORDER_PASS'.
"""
    entry=directory/'negative-probe.ru';entry.write_text(probe,encoding='utf-8',newline='\n');rows=[]
    for name,module in variants.items():
        (directory/'negative-module.ru').write_text(module,encoding='utf-8',newline='\n')
        cmd=[sys.executable,str(core/'ru'),'run',str(entry)]
        result=subprocess.run(cmd,capture_output=True,timeout=30)
        row={'name':name,'command':cmd,'returncode':result.returncode}
        for key,data in [('stdout',result.stdout),('stderr',result.stderr)]:
            path=directory/(name+'.'+key);path.write_bytes(data);row[key]=identity(path)
        if name=='positive':
            if result.returncode!=0 or result.stderr or result.stdout.replace(b'\r\n',b'\n')!=b'GUARD_ORDER_PASS\n':raise ValueError('guard order positive failed')
        elif result.returncode==0 or b'NEGATIVE_GUARD_ORDER_DETECTED' not in result.stderr:
            raise ValueError('unsafe guard mutation was not detected')
        rows.append(row)
    return rows


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--ru-root',type=Path,required=True)
    p.add_argument('--source',type=Path,default=ROOT/'src/markdown_syntax.ru')
    p.add_argument('--output',type=Path,default=ROOT/'build/markdown-bulk-guard-controls')
    a=p.parse_args();core=a.ru_root.resolve();source=a.source.resolve();directory=a.output.resolve()
    directory.mkdir(parents=True,exist_ok=True)
    bound={str(path):identity(path) for path in (source,Path(__file__).resolve(),ROOT/'tools/ru_cli_diagnostics.py')}
    report={'schema':'ru-notepad-markdown-bulk-guards-v1','passed':False,'source_files':bound,'commands':[],
            'compiler_entry':identity(core/'ru'),'scope':'Controlled pure Ru FFI-boundary evidence; not native Windows acceptance or performance'}
    try:
        report['production_bodies']=prepare(source,directory,core)
        report['generated_sources']={path.name:identity(path) for path in sorted(directory.glob('*.ru'))}
        for variant in ('baseline','candidate'):
            entry=directory/(variant+'-probe.ru');exe=directory/(variant+('.exe' if sys.platform=='win32' else ''))
            outputs=[]
            for backend,command in [('interpreter',[sys.executable,str(core/'ru'),'run',str(entry)]),('build',[sys.executable,str(core/'ru'),'build','--cc','gcc',str(entry),'-o',str(exe)]),('GCC',[str(exe)])]:
                diagnostics=prepare_compile_diagnostics(command,core,entry) if backend=='build' else None
                row={'variant':variant,'backend':backend,'command':command,'returncode':None,'passed':False,'assertions':0};report['commands'].append(row)
                try:
                    result=subprocess.run(command,capture_output=True,timeout=120 if backend=='build' else 30)
                    out,err=result.stdout,result.stderr;row['returncode']=result.returncode
                except subprocess.TimeoutExpired as error:
                    out,err=error.stdout or b'',error.stderr or b'';row['timed_out']=True
                prefix=variant+'-'+backend
                for name,data in [('stdout',out),('stderr',err)]:
                    path=directory/(prefix+'.'+name);path.write_bytes(data);row[name]=identity(path)
                if row['returncode']!=0:raise RuntimeError(prefix+' failed')
                validate_stderr(command,result.returncode,err,diagnostics)
                if backend!='build':
                    text=out.decode('utf-8','strict').replace('\r\n','\n');row['assertions']=validate_output(text,variant);outputs.append(text)
                row['passed']=True
            if outputs[0]!=outputs[1]:raise ValueError('backend trace outputs differ')
        report['guard_order_controls']=negative_controls(directory,core)
        report['sources_unchanged']={str(path):identity(path) for path in (source,Path(__file__).resolve(),ROOT/'tools/ru_cli_diagnostics.py')}==bound
        if not report['sources_unchanged']:raise ValueError('source drift')
        report['passed']=True
        print('MARKDOWN_BULK_GUARDS_PORTABLE_PASS baseline=296x2 candidate=236x2')
    except Exception as error:
        report['error_type']=type(error).__name__;raise
    finally:
        (directory/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')

if __name__=='__main__':main()
