#!/usr/bin/env python3
"""Actual production step/timing control flow with deterministic pure Ru boundaries.
No Win32 emulation/native-performance claim; native fixture separately covers real windows.
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
NAMES=('_统计','_步微秒','推进')


def extract(core):
    sys.path.insert(0,str(core))
    from rulang.frontend import parse
    source=(ROOT/'src/markdown_syntax.ru').read_text(encoding='utf-8');nodes=parse(source)
    result={}
    for i,n in enumerate(nodes):
        if n.kind=='function' and n.data['name'] in NAMES:
            end=nodes[i+1].token.line-1 if i+1<len(nodes) else len(source.splitlines())
            result[n.data['name']]=''.join(source.splitlines(keepends=True)[n.token.line-1:end])
    if set(result)!=set(NAMES):raise ValueError('exact production function inventory changed')
    body=result['推进']
    if (body.count('取 时刻.')!=3 or body.count('(时刻)-起时')!=1 or
        body.count('_一步 柄 态.')!=1 or '现在-起时+(现在-块始) >= 预算' not in body or
        '预算 <= 0 或 预算 > 8' not in body):raise ValueError('original QPC or budget sequence changed')
    main=(ROOT/'src/main.ru').read_text(encoding='utf-8')
    if main.count('若 界面待办 则')!=2 or main.count('GetQueueStatus) 其 调用 [7679]')!=1:
        raise ValueError('queue query call inventory changed')
    return '\n'.join(result[n] for n in NAMES)

STUB=r"""柄 取 外言 'handle.ru'.
_编辑们 取 {}. _批统计们 取 {}.
控 取 {'qpc':0,'fail':0,'negative':假,'action':'','calls':0,'failures':0,'reentered':假,'replacement':空}.
算 _同线程 柄: 得 真. 法
算 _本态 柄 态: 得 (_编辑们 其 查 (柄 其 句)) == 态. 法
算 时刻:
    控 其 增 'qpc' (控['qpc']+1).
    若 控['qpc'] == 控['fail'] 则 卒 'QPC failure'. 然
    若 控['negative'] 且 控['qpc'] == 3 则 得 0. 然
    得 控['qpc']*0.25.
法
算 待办 柄: 得 (_编辑们 其 查 (柄 其 句))['pending']. 法
算 _失败 柄 态 原因 为 句:
    若 态['inTick'] 则 卒 'inTick not cleared before recovery'. 然
    控 其 增 'failures' (控['failures']+1).
    态 其 增 'pending' 假.
    得 空.
法
算 _一步 柄 态:
    控 其 增 'calls' (控['calls']+1).
    若 控['action'] == 'panic' 则 卒 'step failure'. 然
    若 控['action'] == 'reenter' 则
        若 推进 柄 8 则 卒 'reentrant step admitted'. 然
        控 其 增 'reentered' 真.
    然
    若 控['action'] == 'replace' 则
        新态值 取 控['replacement'].
        _编辑们 其 增 (柄 其 句) 新态值.
        _统计 柄 新态值.
    然
    态 其 增 'pending' 假.
    得 空.
法
算 新态 号 为 数:
    得 {'identity':号,'pending':真,'inTick':假,'phase':'scan','ranges':[],'eof':假,'maxChunkMs':0,'maxTickMs':0}.
法
算 重置:
    控 其 增 'qpc' 0. 控 其 增 'fail' 0. 控 其 增 'negative' 假.
    控 其 增 'calls' 0. 控 其 增 'failures' 0. 控 其 增 'action' ''. 控 其 增 'reentered' 假.
    _编辑们 其 增 (柄 其 句) (新态 1). _批统计们 其 除 (柄 其 句).
    得 空.
法
次数 取 [0].
作 确认 值 为 事实 文 为 句:
    若 非 值 则 卒 ('FAIL: '+文). 然
    次数[0] 取 次数[0]+1. 显 'PASS: '+文.
为
"""
PROBE=r"""
类别 取 ['feed','publish','lifecycle','visibility'].
位 取 0.
循 4 次
    重置. 态 取 _编辑们 其 查 (柄 其 句).
    若 位 == 1 则 态 其 增 'ranges' ([[0,1,0,假]]). 然
    若 位 == 2 则 态 其 增 'phase' 'prepare'. 然
    若 位 == 3 则 态 其 增 'phase' 'visibility'. 态 其 增 'ranges' ([[0,1,0,假]]). 然
    推进 柄 8. 计 取 _统计 柄 态. 类 取 类别[位].
    确认 (计[类+'StepCount'] == 1 且 计[类+'StepMs'] == 0.25 且 计['stepMetricValid'] 且 计['stepErrors'] == 0) (类+' interval uses existing endpoint pair').
    确认 (计['feedStepCount']+计['publishStepCount']+计['lifecycleStepCount']+计['visibilityStepCount'] == 1 且 控['qpc'] == 4 且 控['calls'] == 1 且 非 态['inTick']) (类+' mutually exclusive and unchanged four-QPC tick').
    位 取 位+1.
环
重置. 态 取 _编辑们 其 查 (柄 其 句). 态 其 增 'eof' 真. 推进 柄 8. 计 取 _统计 柄 态.
确认 (计['lifecycleStepCount'] == 1 且 计['feedStepCount'] == 0) 'EOF completion is lifecycle not feed'.
重置. 态 取 _编辑们 其 查 (柄 其 句). 态 其 增 'eof' 真. 态 其 增 'ranges' ([[0,1,0,假]]). 推进 柄 8. 计 取 _统计 柄 态.
确认 (计['publishStepCount'] == 1 且 计['lifecycleStepCount'] == 0) 'pending ranges precede EOF completion'.
位 取 1.
循 4 次
    重置. 态 取 _编辑们 其 查 (柄 其 句). 控 其 增 'fail' 位. 推进 柄 8. 计 取 _统计 柄 态.
    应错 取 0. 若 位 == 3 则 应错 取 1. 然
    应成 取 0. 若 位 == 4 则 应成 取 1. 然
    确认 (非 计['stepMetricValid'] 且 计['stepErrors'] == 应错 且 计['feedStepCount'] == 应成 且 控['qpc'] == 位 且 控['failures'] == 1 且 非 态['inTick']) ('QPC failure boundary '+(位 为 句)+' has no invented endpoint').
    位 取 位+1.
环
重置. 态 取 _编辑们 其 查 (柄 其 句). 控 其 增 'action' 'panic'. 推进 柄 8. 计 取 _统计 柄 态.
确认 (控['qpc'] == 2 且 控['failures'] == 1 且 计['stepErrors'] == 1 且 计['feedStepCount'] == 0 且 计['feedStepMs'] == 0 且 非 计['stepMetricValid']) 'step panic has no rescue QPC or fabricated duration'.
重置. 态 取 _编辑们 其 查 (柄 其 句). 控 其 增 'negative' 真. 推进 柄 8. 计 取 _统计 柄 态.
确认 (计['feedStepCount'] == 1 且 计['feedStepMs'] == 0 且 非 计['stepMetricValid'] 且 计['stepErrors'] == 0) 'nonmonotonic endpoint invalidates instead of adding negative duration'.
重置. 态 取 _编辑们 其 查 (柄 其 句). 控 其 增 'action' 'reenter'. 推进 柄 8. 计 取 _统计 柄 态.
确认 (控['reentered'] 且 控['calls'] == 1 且 控['qpc'] == 4 且 计['feedStepCount'] == 1) 'reentrant callback cannot double count or query QPC'.
重置. 旧 取 _编辑们 其 查 (柄 其 句). 旧计 取 _统计 柄 旧. 新态值 取 新态 2.
控 其 增 'replacement' 新态值. 控 其 增 'action' 'replace'. 推进 柄 8. 新计 取 _统计 柄 新态值.
确认 (旧计['feedStepCount'] == 1 且 新计['feedStepCount'] == 0 且 新计['identity'] == 2 且 新计['stepMetricValid']) 'replacement identity never receives old completed interval'.
确认 (旧计 != 新计 且 (_统计 柄 旧) == 空) 'stale sidecar cannot replace current identity record'.
确认 ((_步微秒 0.0006+0.0006) == 1) 'projection rounds accumulated wall time only once'.
显 'TOTAL PASS: '+(次数[0] 为 句).
"""


def file_record(path):
    path=Path(path)
    return {'path':str(path.resolve()),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'size':path.stat().st_size}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--ru-root',type=Path,required=True)
    p.add_argument('--output',type=Path,default=ROOT/'build/markdown-step-controls')
    args=p.parse_args()
    core=args.ru_root.resolve();directory=args.output.resolve()
    if any(path.is_symlink() for path in (args.output,*args.output.parents)):
        raise ValueError('linked output directory is not allowed')
    directory.mkdir(parents=True,exist_ok=True)
    bound_sources=[ROOT/'src/main.ru',ROOT/'src/markdown_syntax.ru',Path(__file__),ROOT/'tools/ru_cli_diagnostics.py']
    before={str(path.relative_to(ROOT)):file_record(path) for path in bound_sources}
    report={'schema':'ru-notepad-markdown-step-portable-v1','passed':False,
            'scope':'Pure Ru boundary controls, not native Windows or performance evidence',
            'source_files':before,'compiler_root':str(core),'compiler_entry':file_record(core/'ru'),
            'expected_assertions_per_backend':20,'backends':[]}
    try:
        extracted=extract(core)
        report['extracted_functions_sha256']=hashlib.sha256(extracted.encode('utf-8')).hexdigest()
        source=directory/'probe.ru'
        source.write_text(STUB+extracted+PROBE,encoding='utf-8',newline='\n')
        (directory/'handle.ru').write_text("句 取 'owned-handle'.\n",encoding='utf-8',newline='\n')
        report['generated_sources']={name:file_record(directory/name) for name in ('probe.ru','handle.ru')}
        exe=directory/('probe.exe' if sys.platform=='win32' else 'probe');outputs=[]
        for label,cmd in [('interpreter',[sys.executable,str(core/'ru'),'run',str(source)]),('build',[sys.executable,str(core/'ru'),'build','--cc','gcc',str(source),'-o',str(exe)]),('GCC',[str(exe)])]:
            diagnostics=prepare_compile_diagnostics(cmd,core,source) if label=='build' else None
            row={'backend':label,'command':cmd,'returncode':None,'passed':False,'timeout_seconds':120,'assertions':0}
            report['backends'].append(row)
            try:
                result=subprocess.run(cmd,capture_output=True,timeout=120)
                stdout,stderr=result.stdout,result.stderr;row['returncode']=result.returncode
            except subprocess.TimeoutExpired as error:
                stdout,stderr=error.stdout or b'',error.stderr or b'';row['timed_out']=True
            out=directory/(label+'.stdout');err=directory/(label+'.stderr')
            out.write_bytes(stdout);err.write_bytes(stderr)
            row['stdout']=file_record(out);row['stderr']=file_record(err)
            if row['returncode']!=0:raise RuntimeError(label+' failed or timed out')
            validate_stderr(cmd,result.returncode,stderr,diagnostics)
            if label!='build':
                text=stdout.decode('utf-8','strict').replace('\r\n','\n')
                if stderr or len(re.findall(r'^PASS:',text,re.M))!=20 or not text.endswith('TOTAL PASS: 20\n'):
                    raise ValueError('exact twenty assertions required')
                row['assertions']=20;outputs.append(text);print(label+' 20 PASS')
            else:report['binary']=file_record(exe)
            row['passed']=True
        if outputs[0]!=outputs[1]:raise ValueError('two backend outputs differ')
        report['sources_unchanged']={str(path.relative_to(ROOT)):file_record(path) for path in bound_sources}==before
        if not report['sources_unchanged']:raise ValueError('source identity drift')
        report['passed']=True
        print('MARKDOWN_STEP_METRICS_PORTABLE_PASS')
    except Exception as error:
        report['error_type']=type(error).__name__
        raise
    finally:
        (directory/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')

if __name__=='__main__':main()
