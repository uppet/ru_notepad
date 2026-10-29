#!/usr/bin/env python3
"""Portable production-body reentrancy probe; OS seams are not Windows evidence."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from test_single_instance_state import function
FUNCTIONS=('校验入队','入队','接收入队','交接待收尾','开始工作','结束工作','清操作','取消工作','工作时钟','恢复工作收尾','保存到')
EXPECTED=155

def prepare(out,source):
 out.mkdir(parents=True,exist_ok=True)
 modules={'control':"回调 取 [空].\n算 探 名: 若 回调[0] != 空 则 得 回调[0] 名. 然 得 1. 法\n",
 'native':"形 存形: 大小 为 数. 算 关闭: 得 空. 法 象\n算 UTF16 文: 得 新 存形 大小:((文 其 量)+1)*2. 法\n",'i18n':"算 文本 键: 得 键. 法\n"}
 for name in ('KillTimer','EnableWindow','ShowWindow','SetFocus','SetTimer'):
  modules[name]="控 取 外言 './control.ru'. 算 调用 参数: 得 控 其 探 '"+name+"'. 法\n"
 modules['EnableWindow']="控 取 外言 './control.ru'. 算 调用 参数: 若 参数[0] == 4 则 得 控 其 探 'EarlyEnableWindow'. 然 得 控 其 探 'EnableWindow'. 法\n"
 modules['win']="控 取 外言 './control.ru'.\n"+'\n'.join(n+" 取 外言 './"+n+".ru'." for n in ('KillTimer','EnableWindow','ShowWindow','SetFocus','SetTimer'))+"\n算 结果 果: 得 果. 法\n算 成功 果 名: 得 果. 法\n算 发送 柄 号 甲 乙: 得 控 其 探 'Send'. 法\n"
 modules['tickvalue']="数 取 1.\n"
 modules['GetTickCount64']="值 取 外言 './tickvalue.ru'. 算 调用 参数: 得 值. 法\n"
 modules['win']+="GetTickCount64 取 外言 './GetTickCount64.ru'.\n"
 modules['unused']="算 关闭读取 参数: 得 空. 法 算 取消写入 参数: 得 空. 法 算 遗忘 参数: 得 空. 法 算 准备写入 路 码 标 戳: 得 {}. 法 算 开始取文 柄: 得 []. 法\n"
 for n,t in modules.items():(out/(n+'.ru')).write_text(t)
 header="""窗 取 外言 './win.ru'. 密 取 外言 './native.ru'. 本地 取 外言 './i18n.ru'. 控 取 外言 './control.ru'.
件编 取 外言 './unused.ru'. 语 取 外言 './unused.ru'. 编 取 外言 './unused.ru'.
算 结束批关 取消: 得 空. 法
算 操作一步: 若 恢复控[7] 则 结束工作. 得 空. 然 卒 'injected operation failure'. 法
算 错误提示 文: 恢复控[4] 取 文. 若 恢复控[6] 则 卒 'injected error-dialog failure'. 然 得 空. 法
文档 取 {'encoding':65001,'bom':假,'revision':17,'editor':4,'text':'unchanged dirty document','dirty':真}.
算 当前: 得 文档. 法
恢复控 取 [假,'',0,0,'',真,假,假].
A 取 {}. 次数 取 [0]. 观察 取 [假,0,'',0,0].
作 确认 条件 为 事实 文 为 句:
    若 非 条件 则 卒 ('FAIL: '+文). 然
    次数[0] 取 次数[0]+1. 显 'PASS: '+文.
为
算 锁界面: 得 空. 法
算 布局: 得 控 其 探 'Layout'. 法
算 刷新: 得 控 其 探 'Refresh'. 法
算 编辑柄: 得 4. 法
算 模拟接收:
    # Mirrors the early WM74 admission filter; wire parsing is a native fixture.
    若 (A 其 查 'handoffReject') 或 (A 其 查 'cancelRequested') 或 (A 其 查 'modalDepth') > 0 或 (A 其 查 'closeIndex') >= 0 或 (A 其 查 'closeRun') != 空 或 (A 其 查 'tabMenuOpen') 则 得 2. 然
    若 交接待收尾 则 得 3. 然
    试 接收入队 (['C:/synthetic/second.txt']). 救 原因 得 2. 终
    得 1.
法
算 重置 模式:
    A 取 {'busy':真,'operation':空,'queue':[],'openFinalizing':模式 == 0,'handoffReject':模式 == 3,'cancelRequested':模式 == 2,'modalDepth':0,'closeIndex':-1,'closeRun':空,'tabMenuOpen':假,'locks':[[4,0]],'active':0,'window':1,'tabs':2,'cancel':3,'docs':[],'inTick':假,'ticks':0,'lastOutcome':'','cleanupActive':假,'cleanupRetrying':假,'cleanupPending':假}.
    得 空.
法
算 探测 名:
    若 名 == 'SetTimer' 则 观察[4] 取 观察[4]+1. 然
    若 恢复控[0] 则
        若 A['cleanupActive'] 或 A['cleanupRetrying'] 则
            旧时钟 取 A['ticks']. 工作时钟. 若 A['ticks'] != 旧时钟 则 恢复控[5] 取 假. 然
        然
        若 名 == 'KillTimer' 则 恢复控[3] 取 恢复控[3]+1. 然
        若 非 A['busy'] 且 A['cleanupActive'] 则
            若 恢复工作收尾 则 恢复控[5] 取 假. 然
            拒开 取 [假]. 拒存 取 [假].
            试 入队 (['C:/reentrant.txt']) 0. 救 原因 拒开[0] 取 真. 终
            试 保存到 'C:/reentrant-save.txt' '' ''. 救 原因 拒存[0] 取 真. 终
            若 非 拒开[0] 或 非 拒存[0] 或 非 A['cleanupActive'] 或 (A['queue'] 其 量) != 0 则 恢复控[5] 取 假. 然
        然
        故障点 取 名.
        若 故障点 == 恢复控[1] 且 恢复控[2] > 0 则
            恢复控[2] 取 恢复控[2]-1. 卒 ('injected tail failure '+故障点).
        然
        得 1.
    然
    若 非 观察[0] 则 得 1. 然
    观察[3] 取 观察[3]+1.
    若 观察[2] != '' 且 观察[3] == 观察[1] 则 卒 'injected native teardown failure'. 然
    若 观察[2] == '' 则
        回 取 模拟接收.
        确认 (回 == 观察[1] 且 (A['queue'] 其 量) == 0 且 观察[4] == 0) ('guarded native teardown '+名).
    然
    得 1.
法
(控 其 回调)[0] 取 算 探测.
"""
 # Ru assignment inside a function is local: reset the existing global dictionary.
 header=header.replace("    A 取 {'busy':", "    初 取 {'busy':")
 header=header.replace("    得 空.\n法\n算 探测", "    键们 取 ['busy','operation','queue','openFinalizing','handoffReject','cancelRequested','modalDepth','closeIndex','closeRun','tabMenuOpen','locks','active','window','tabs','cancel','docs','inTick','ticks','lastOutcome','cleanupActive','cleanupRetrying','cleanupPending'].\n    位 取 0. 循 键们 其 量 次 A 其 增 键们[位] 初[键们[位]]. 位 取 位+1. 环\n    得 空.\n法\n算 探测")
 checks="""
模式 取 0.
循 4 次
    重置 模式. 观察[0] 取 真. 观察[1] 取 2. 若 模式 == 0 则 观察[1] 取 3. 然
    观察[2] 取 ''. 观察[3] 取 0. 观察[4] 取 0.
    结束工作.
    观察[0] 取 假.
    确认 (观察[3] == 8 且 非 A['busy'] 且 非 A['openFinalizing'] 且 非 A['handoffReject'] 且 非 A['cancelRequested']) 'complete teardown publishes idle and clears guards only at end'.
    确认 ((模拟接收) == 1) 'same request can be admitted after teardown returns'.
    确认 (A['busy'] 且 (A['queue'] 其 量) == 1 且 观察[4] == 1) 'post-teardown request restarts exactly one work timer'.
    模式 取 模式+1.
环
模式 取 0.
循 2 次
    点 取 1.
    循 8 次
        重置 模式. 观察[0] 取 真. 观察[1] 取 点. 观察[2] 取 'fault'. 观察[3] 取 0. 观察[4] 取 0. 捕 取 [假].
        试 结束工作. 救 原因 捕[0] 取 真. 终
        观察[0] 取 假.
        回 取 模拟接收.
        确认 (捕[0] 且 回 != 1 且 (A['queue'] 其 量) == 0 且 观察[4] == 0) 'teardown exception remains guarded with no admitted work'.
        点 取 点+1.
    环
    模式 取 模式+1.
环

重置 0. 观察[0] 取 真. 观察[1] 取 2. 观察[2] 取 ''. 观察[3] 取 0. 观察[4] 取 0.
取消工作.
观察[0] 取 假.
确认 (观察[3] == 8 且 非 A['busy'] 且 非 A['openFinalizing'] 且 非 A['handoffReject'] 且 非 A['cancelRequested']) 'actual cancel clears all guards after protected cleanup'.
确认 ((A['queue'] 其 量) == 0 且 观察[4] == 0 且 A['lastOutcome'] == 'cancelled') 'actual cancel never starts new work'.
重置 0. 观察[0] 取 假.
工作时钟.
确认 (A['busy'] 且 A['handoffReject'] 且 非 A['openFinalizing'] 且 A['lastOutcome'] == 'failed' 且 非 A['inTick']) 'actual error path blocks handoff before cleanup and clears finalizing'.
观察[0] 取 真. 观察[1] 取 2. 观察[2] 取 ''. 观察[3] 取 0. 观察[4] 取 0.
结束工作.
观察[0] 取 假.
确认 (观察[3] == 8 且 非 A['busy'] 且 非 A['handoffReject'] 且 非 A['cleanupPending'] 且 非 A['openFinalizing']) 'error cleanup clears guards only after last native call'.
确认 ((模拟接收) == 1) 'completed error cleanup can admit future request'.

重置 0. A 其 增 'queue' ([['C:/synthetic/first.txt',65001]]).
确认 ((模拟接收) == 1 且 (A['queue'] 其 量) == 2 且 A['queue'][0][0] == 'C:/synthetic/first.txt') 'nonempty serial queue retains original atomic append behavior'.
重置 0. A 其 增 'operation' ({'kind':'save'}).
确认 ((模拟接收) == 2 且 (A['queue'] 其 量) == 0) 'save operation cannot be misclassified as retryable open'.
重置 0. A 其 增 'openFinalizing' 假. A 其 增 'lastOutcome' 'opened'.
确认 ((模拟接收) == 2 且 (A['queue'] 其 量) == 0) 'stale opened outcome is not a finalization capability'.
重置 0. A 其 增 'cancelRequested' 真.
确认 ((模拟接收) == 2 且 (A['queue'] 其 量) == 0) 'cancel rejection wins over open finalization'.
重置 0. A 其 增 'handoffReject' 真.
确认 ((模拟接收) == 2 且 (A['queue'] 其 量) == 0) 'error rejection wins over open finalization'.

尾点 取 ['KillTimer','Send','EarlyEnableWindow','EnableWindow','ShowWindow','Layout','Refresh','SetFocus']. 索 取 0.
循 8 次
    重置 0. 观察[0] 取 假. 观察[4] 取 0.
    恢复控[0] 取 真. 恢复控[1] 取 尾点[索]. 恢复控[2] 取 1. 恢复控[3] 取 0. 恢复控[4] 取 ''. 恢复控[5] 取 真. 恢复控[6] 取 假. 恢复控[7] 取 真.
    工作时钟.
    确认 (非 A['busy'] 且 非 A['handoffReject'] 且 非 A['cleanupPending'] 且 非 A['openFinalizing'] 且 非 A['cleanupActive'] 且 非 A['cleanupRetrying'] 且 非 A['inTick'] 且 恢复控[3] == 2 且 (恢复控[4] 其 含 'injected tail failure')) 'one tail failure recovers once but original error is reported'.
    确认 (恢复控[5] 且 文档['dirty'] 且 文档['text'] == 'unchanged dirty document') 'local reentrant save/open cannot recurse or alter document'.
    确认 ((保存到 'C:/saved.txt' '' '') 且 A['operation']['kind'] == 'save' 且 观察[4] == 1) 'save works after successful automatic tail recovery'.
    重置 0. 观察[4] 取 0. 恢复控[2] 取 3. 恢复控[3] 取 0. 恢复控[4] 取 ''. 恢复控[5] 取 真.
    工作时钟.
    确认 (非 A['busy'] 且 A['handoffReject'] 且 A['cleanupPending'] 且 非 A['cleanupActive'] 且 非 A['cleanupRetrying'] 且 非 A['inTick'] 且 恢复控[3] == 2 且 (A['queue'] 其 量) == 0 且 (模拟接收) == 2 且 恢复控[4] == ('injected tail failure '+尾点[索]+'\n'+'injected tail failure '+尾点[索])) 'persistent failure stops after one automatic recovery with zero admission'.
    拒 取 [假]. 试 入队 (['C:/later.txt']) 0. 救 原因 拒[0] 取 真. 终
    确认 (拒[0] 且 恢复控[3] == 3 且 A['handoffReject'] 且 非 A['cleanupRetrying'] 且 (A['queue'] 其 量) == 0) 'explicit open attempts cleanup once and reports persistent failure'.
    确认 ((保存到 'C:/saved.txt' '' '') 且 恢复控[3] == 4 且 非 A['handoffReject'] 且 A['operation']['kind'] == 'save' 且 观察[4] == 1) 'later explicit save recovers and resumes real work'.
    确认 (恢复控[5] 且 文档['dirty'] 且 文档['revision'] == 17 且 文档['text'] == 'unchanged dirty document') 'repeated failure and recovery preserve dirty source document'.
    重置 0. 观察[4] 取 0. 恢复控[2] 取 2. 恢复控[3] 取 0. 恢复控[4] 取 ''.
    工作时钟.
    确认 ((入队 (['C:/recovered-open.txt']) 0) 且 恢复控[3] == 3 且 A['busy'] 且 非 A['handoffReject'] 且 (A['queue'] 其 量) == 1 且 A['queue'][0][0] == 'C:/recovered-open.txt' 且 观察[4] == 1) 'explicit later open recovers once and queues exactly one new request'.
    索 取 索+1.
环
重置 0. 观察[4] 取 0. 恢复控[1] 取 'ShowWindow'. 恢复控[2] 取 1. 恢复控[3] 取 0. 恢复控[6] 取 真. 捕 取 [''].
试 工作时钟. 救 原因 捕[0] 取 原因. 终
确认 (非 A['inTick'] 且 非 A['cleanupActive'] 且 非 A['cleanupRetrying'] 且 (捕[0] 其 含 'injected tail failure') 且 (捕[0] 其 含 'injected error-dialog failure')) 'error dialog failure clears tick lock and retains original cause'.
重置 1. A 其 增 'operation' ({'kind':'save','writer':{}}). 恢复控[7] 取 假. 恢复控[6] 取 假. 恢复控[2] 取 1. 恢复控[3] 取 0. 恢复控[4] 取 ''.
工作时钟.
确认 (非 A['inTick'] 且 非 A['busy'] 且 非 A['handoffReject'] 且 非 A['cleanupPending'] 且 非 A['cleanupActive'] 且 非 A['cleanupRetrying'] 且 恢复控[3] == 2 且 (恢复控[4] 其 含 'injected operation failure') 且 (恢复控[4] 其 含 'injected tail failure')) 'save rescue secondary cleanup failure recovers with full diagnostic chain'.
恢复控[0] 取 假.

重置 1. A 其 增 'handoffReject' 真. A 其 增 'cleanupPending' 真. 恢复控[0] 取 真. 恢复控[2] 取 0. 恢复控[3] 取 0. 恢复控[5] 取 真.
确认 ((恢复工作收尾) 且 非 A['busy'] 且 非 A['handoffReject'] 且 非 A['cleanupPending'] 且 恢复控[3] == 1 且 恢复控[5] 且 A['ticks'] == 0) 'known failed cleanup can recover busy state without timer reentrancy'.
重置 1. A 其 增 'handoffReject' 真. A 其 增 'cleanupPending' 真. A 其 增 'operation' ({'kind':'save'}). 恢复控[3] 取 0.
确认 (非 (恢复工作收尾) 且 A['busy'] 且 A['cleanupPending'] 且 恢复控[3] == 0) 'pending cleanup never overrides a live operation'.
A 其 增 'operation' 空. A 其 增 'queue' ([['C:/queued.txt',0]]).
确认 (非 (恢复工作收尾) 且 (A['queue'] 其 量) == 1 且 A['cleanupPending'] 且 恢复控[3] == 0) 'pending cleanup never discards a queued request'.
恢复控[0] 取 假.
显 'TOTAL PASS: '+(次数[0] 为 句).
"""
 body=''.join(function(source,n) for n in FUNCTIONS);p=out/'admission.ru';p.write_text(header+body+checks);return p,body

def execute(ru,out,source,negative=False):
 p,body=prepare(out,source);rows=[]
 for label,cmd in [('interpreter',[sys.executable,str(ru/'ru'),'run',str(p)]),('build',[sys.executable,str(ru/'ru'),'build','--cc','gcc',str(p),'-o',str(out/'admission')]),('c',[str(out/'admission')])]:
  r=subprocess.run(cmd,capture_output=True,text=True,timeout=120);log=r.stdout+r.stderr;(out/(label+'.log')).write_text(log)
  if label=='build':assert r.returncode==0,log
  elif negative:assert r.returncode!=0 and 'FAIL: guarded native teardown EnableWindow' in log,log
  else:assert r.returncode==0 and f'TOTAL PASS: {EXPECTED}' in log and log.count('PASS: ')==EXPECTED+1,log
  rows.append({'backend':label,'exit':r.returncode,'log_sha256':hashlib.sha256(log.encode()).hexdigest()})
 return {'functions':{n:hashlib.sha256(function(source,n).encode()).hexdigest() for n in FUNCTIONS},'probe_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'runs':rows}

def run(ru,out):
 commit=subprocess.check_output(['git','-C',str(ru),'rev-parse','HEAD'],text=True).strip()
 if subprocess.run(['git','-C',str(ru),'diff','--quiet','HEAD','--']).returncode:raise ValueError('Compiler tracked files changed')
 source=(ROOT/'src/main.ru').read_text();receipt={'scope':__doc__,'compiler_commit':commit,'compiler_entry_sha256':hashlib.sha256((ru/'ru').read_bytes()).hexdigest(),'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'positive':execute(ru,out,source)}
 marker="        A 其 增 'busy' 假."
 early=source.replace(marker,marker+"\n        A 其 增 'openFinalizing' 假.\n        A 其 增 'handoffReject' 假.",1)
 receipt['negative_early_guard_clear']=execute(ru,out/'early-clear',early,True)
 (out/'receipt.json').write_text(json.dumps(receipt,indent=2))
 saved=json.loads((out/'receipt.json').read_text());assert saved==receipt
 assert saved['source_sha256']==hashlib.sha256((ROOT/'src/main.ru').read_bytes()).hexdigest()
 assert saved['positive']['probe_sha256']==hashlib.sha256((out/'admission.ru').read_bytes()).hexdigest()
 for name in FUNCTIONS:assert saved['positive']['functions'][name]==hashlib.sha256(function(source,name).encode()).hexdigest()
 print(f'ADMISSION_PORTABLE_PASS {EXPECTED} each backend; early-clear negative rejected; not Windows evidence')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--ru-root',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();run(a.ru_root.resolve(),a.output.resolve())
