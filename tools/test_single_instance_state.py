#!/usr/bin/env python3
"""Execute unmodified IPC state functions with controlled portable FFI seams.

This checks Ru dictionary-write semantics, not Windows ABI/IPC acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
FUNCTIONS=('_占用','准备','发布','关闭','转交')
SCOPED=('src/main.ru','src/single_instance.ru','src/single_instance_policy.ru',
        'src/single_instance_settings.ru','src/tab_close_policy.ru','src/tab_context.ru')

BAD_WRITE=re.compile(r"\[\s*(['\"])(?:[^'\"\\]|\\.)*\1\s*\]\s*取")


def function(source,name):
    pattern=r'^(算|作) '+re.escape(name)+r'(?=[ :])[^\n]*\n.*?^(?:法|为)\s*$'
    matches=list(re.finditer(pattern,source,re.M|re.S))
    if len(matches)!=1:raise ValueError('expected complete production function: '+name)
    return matches[0].group(0)+'\n'


def walk(value):
    if hasattr(value, 'kind') and hasattr(value, 'data'):
        yield value
        yield from walk(value.data)
    elif isinstance(value, dict):
        for child in value.values(): yield from walk(child)
    elif isinstance(value, (list, tuple)):
        for child in value: yield from walk(child)


def check_ast(text, parse, label):
    for node in walk(parse(text)):
        if node.kind == 'assign' and node.data['target'].kind == 'index':
            if node.data['target'].data['index'].kind == 'string':
                raise ValueError(f'string-key index assignment forbidden: {label}:{node.token.line}')


def static_check(ru_root, root=ROOT):
    for name in SCOPED:
        if not (root/name).is_file(): raise ValueError('missing scoped product source: '+name)
    sys.path.insert(0,str(ru_root.resolve()))
    from rulang.frontend import parse
    files=sorted((root/'src').glob('*.ru'))
    if not files: raise ValueError('missing product sources')
    for path in files: check_ast(path.read_text(encoding='utf-8'),parse,str(path.relative_to(root)))
    # Static negative and positive controls: reject writes, not reads or numeric arrays.
    try: check_ast("态 取 {}. 态['x'] 取 1.",parse,'negative')
    except ValueError: pass
    else: raise AssertionError('AST guard accepted original dictionary-index write')
    check_ast("态 取 {'x':1}. 显 态['x']. 阵列 取 [0]. 阵列[0] 取 1.",parse,'positive')
    return {str(path.relative_to(root)):hashlib.sha256(path.read_bytes()).hexdigest() for path in files}


def prepare(output, source):
    output.mkdir(parents=True,exist_ok=True)
    modules={
      'control':"态 取 [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0].\n",
      'otherhandle':"句 取 '999'.\n",
      'handle':"为空 取 假. 数 取 123. 句 取 '123'.\n",
      'empty':"为空 取 真. 数 取 0.\n",
      'good':"值 取 外言 './handle.ru'. 错误码 取 0.\n",
      'exists':"值 取 外言 './handle.ru'. 错误码 取 183.\n",
      'failed':"值 取 外言 './empty.ru'. 错误码 取 5.\n",
      'memory':"控 取 外言 './control.ru'. 算 关闭: (控 其 态)[4] 取 (控 其 态)[4]+1. 得 空. 法\n",
      'native':"存 取 外言 './memory.ru'. 算 UTF16 文: 得 存. 法\n",
      'pointer':"算 值 数值: 得 数值. 法\n",
      'window':"算 结果 果: 得 果 其 值. 法\n",
      'settings':"控 取 外言 './control.ru'. 算 命名空间: 若 (控 其 态)[0] == 4 则 卒 'namespace rejected'. 然 得 'portable'. 法\n",
      'pid':"果 取 外言 './good.ru'. 算 调用 参数: 得 果. 法\n",
      'create':"控 取 外言 './control.ru'. 好 取 外言 './good.ru'. 在 取 外言 './exists.ru'. 坏 取 外言 './failed.ru'. 算 调用 参数: (控 其 态)[1] 取 (控 其 态)[1]+1. 若 (控 其 态)[0] == 1 则 得 在. 然 若 (控 其 态)[0] == 2 则 得 坏. 然 得 好. 法\n",
      'close':"控 取 外言 './control.ru'. 算 调用 参数: (控 其 态)[2] 取 (控 其 态)[2]+1. 得 空. 法\n",
      'setprop':"控 取 外言 './control.ru'. 好 取 外言 './good.ru'. 坏 取 外言 './failed.ru'. 算 调用 参数: 若 (控 其 态)[0] == 5 则 得 坏. 然 得 好. 法\n",
      'remove':"控 取 外言 './control.ru'. 算 调用 参数: (控 其 态)[3] 取 (控 其 态)[3]+1. 得 空. 法\n"}
    modules.update({
      'memory':"控 取 外言 './control.ru'. 大小 取 64. 地址 取 99. 算 关闭: (控 其 态)[4] 取 (控 其 态)[4]+1. 得 空. 法\n",
      'pointer':"算 值 数值: 得 数值. 法 算 重释 数值: 得 数值. 法\n",
      'file':"控 取 外言 './control.ru'. 算 绝对路径 路: (控 其 态)[9] 取 (控 其 态)[9]+1. 若 (控 其 态)[0] == 18 则 卒 'absolute conversion failed'. 然 得 'C:\\\\portable\\\\'+路. 法\n",
      'packet':"字段 取 {}. 地址 取 98. 算 写 键 值: 字段 其 增 键 值. 得 空. 法 算 关闭: 得 空. 法\n",
      'packettype':"存 取 外言 './packet.ru'. 算 新建: 得 存. 法\n",
      'receipt':"字段 取 {}. 形 数形: 数值 为 数. 算 数: 得 其 数值. 法 象 形 回形: 算 写 键 值: 字段 其 增 键 值. 得 空. 法 算 读 键: 得 新 数形 数值:(字段 其 查 键). 法 算 关闭: 得 空. 法 象 回物 取 新 回形.\n",
      'receipttype':"存 取 外言 './receipt.ru'. 算 新建: 得 存 其 回物. 法\n",
      'tickvalue':"控 取 外言 './control.ru'. 算 数: 得 (控 其 态)[5]. 法\n",
      'tickresult':"值 取 外言 './tickvalue.ru'.\n",
      'tick':"控 取 外言 './control.ru'. 果 取 外言 './tickresult.ru'. 算 调用 参数: (控 其 态)[5] 取 (控 其 态)[5]+1000. 得 果. 法\n",
      'sleep':"控 取 外言 './control.ru'. 算 调用 参数: 若 参数[0] != 25 则 卒 'unexpected sleep budget'. 然 (控 其 态)[7] 取 (控 其 态)[7]+1. 得 空. 法\n",
      'send':"控 取 外言 './control.ru'. 好 取 外言 './good.ru'. 坏 取 外言 './failed.ru'. 算 调用 参数: (控 其 态)[6] 取 (控 其 态)[6]+1. 若 参数[1] != 74 或 参数[4] != 3 或 参数[5] != 1000 则 卒 'send contract differs'. 然 参数[6] 其 写 'n' 1. 若 (控 其 态)[0] == 11 则 参数[6] 其 写 'n' 2. 然 若 (控 其 态)[0] == 13 则 参数[6] 其 写 'n' 0. 然 若 (控 其 态)[0] == 14 则 卒 'send failed'. 然 若 (控 其 态)[0] == 12 则 得 坏. 然 得 好. 法\n",
    })
    modules['tick']="控 取 外言 './control.ru'. 果 取 外言 './tickresult.ru'. 算 调用 参数: 步 取 1000. 若 (控 其 态)[0] >= 21 且 (控 其 态)[0] != 25 则 步 取 1. 然 (控 其 态)[5] 取 (控 其 态)[5]+步. 得 果. 法\n"
    modules['sleep']="控 取 外言 './control.ru'. 算 调用 参数: 若 参数[0] <= 0 或 参数[0] > 25 则 卒 'unexpected sleep budget'. 然 (控 其 态)[7] 取 (控 其 态)[7]+1. 若 (控 其 态)[0] >= 21 则 (控 其 态)[5] 取 (控 其 态)[5]+参数[0]. 然 得 空. 法\n"
    modules['send']="控 取 外言 './control.ru'. 好 取 外言 './good.ru'. 坏 取 外言 './failed.ru'. 算 调用 参数: (控 其 态)[6] 取 (控 其 态)[6]+1. 若 参数[1] != 74 或 参数[4] != 3 或 参数[5] <= 0 或 参数[5] > 1000 或 参数[3] != 98 则 卒 'send contract differs'. 然 (控 其 态)[12] 取 参数[5]. 模式 取 (控 其 态)[0]. 发送次 取 (控 其 态)[6]. 参数[6] 其 写 'n' 1. 若 模式 == 11 则 参数[6] 其 写 'n' 2. 然 若 模式 == 13 则 参数[6] 其 写 'n' 0. 然 若 模式 == 14 则 卒 'send failed'. 然 若 模式 == 12 则 得 坏. 然 若 模式 >= 21 则 参数[6] 其 写 'n' 3. 若 发送次 > 1 则 若 模式 == 21 则 参数[6] 其 写 'n' 1. 然 若 模式 == 22 则 参数[6] 其 写 'n' 2. 然 若 模式 == 23 则 得 坏. 然 若 模式 == 24 则 参数[6] 其 写 'n' 4. 然 然 然 得 好. 法\n"
    modules['create']=modules['create'].replace("若 (控 其 态)[0] == 1 则", "若 (控 其 态)[0] == 1 或 (控 其 态)[0] == 15 或 (控 其 态)[0] == 20 或 ((控 其 态)[0] == 16 且 (控 其 态)[1] < 2) 则")
    modules['setprop']=modules['setprop'].replace("算 调用 参数:", "算 调用 参数: (控 其 态)[11] 取 (控 其 态)[11]+1.")
    policy=(ROOT/'src/single_instance_policy.ru').read_text(encoding='utf-8')
    (output/'policy.ru').write_text(policy,encoding='utf-8')
    for name,text in modules.items():(output/(name+'.ru')).write_text(text,encoding='utf-8')
    header="""控 取 外言 './control.ru'.
密 取 外言 './native.ru'. 窗 取 外言 './window.ru'. 设 取 外言 './settings.ru'.
异柄 取 外言 './otherhandle.ru'.
P 取 外言 './pointer.ru'. 柄 取 外言 './handle.ru'.
_CreateMutexW 取 外言 './create.ru'. _CloseHandle 取 外言 './close.ru'.
_GetCurrentProcessId 取 外言 './pid.ru'. _SetProp 取 外言 './setprop.ru'. _RemoveProp 取 外言 './remove.ru'.
策 取 外言 './policy.ru'. 件编 取 外言 './file.ru'.
UP 取 外言 './pointer.ru'. IP 取 外言 './pointer.ru'.
_包 取 外言 './packettype.ru'. _回执 取 外言 './receipttype.ru'.
_Tick 取 外言 './tick.ru'. _Sleep 取 外言 './sleep.ru'. _Send 取 外言 './send.ru'.
算 _窗口进程 窗口:
    若 (控 其 态)[0] == 26 且 (控 其 态)[6] > 0 则 得 999. 然
    得 123.
法
算 _目标 态:
    (控 其 态)[8] 取 (控 其 态)[8]+1.
    若 (控 其 态)[0] == 17 则 卒 'target lookup failed'. 然
    若 (控 其 态)[0] == 15 或 (控 其 态)[0] == 16 则 得 空. 然
    若 (控 其 态)[0] == 20 且 (控 其 态)[8] < 3 则 得 空. 然
    若 (控 其 态)[0] == 27 且 (控 其 态)[6] > 0 则 得 异柄. 然
    若 (控 其 态)[0] == 28 且 (控 其 态)[6] > 0 则 得 空. 然
    得 柄.
法
算 重置 模式:
    位 取 0.
    循 16 次 (控 其 态)[位] 取 0. 位 取 位+1. 环
    (控 其 态)[0] 取 模式. 得 空.
法
算 接手态:
    得 {'enabled':真,'owner':假,'mutex':空,'identity':'SID-session','window':空,'error':'','property':_名称}.
法
_名称 取 'RuNotepad.SingleInstance.v1'.
算 _身份 号 为 数:
    若 (控 其 态)[0] == 3 则 卒 'identity unavailable'. 然
    得 'SID-session'.
法
次数 取 [0].
作 确认 条件 为 事实 文 为 句:
    若 非 条件 则 卒 ('FAIL: '+文). 然
    次数[0] 取 次数[0]+1. 显 'PASS: '+文.
为
"""
    body=''.join(function(source,name) for name in FUNCTIONS)
    probe="""
态 取 准备 假.
确认 (非 态['enabled'] 且 非 态['owner'] 且 (控 其 态)[1] == 0) 'disabled preparation never creates mutex'.
态 取 准备 真.
确认 (态['enabled'] 且 态['owner'] 且 态['mutex'] != 空) 'enabled preparation writes dictionary owner and mutex'.
确认 (态['identity'] == 'SID-session' 且 态['property'] == _名称+'.test.portable') 'identity and isolated property dictionary writes'.
确认 (发布 态 柄) 'owner publication succeeds'.
确认 (态['window'] == 柄) 'publication records window'.
关闭 态.
确认 (非 态['owner'] 且 态['mutex'] == 空 且 态['window'] == 空) 'close clears owner mutex and window'.
确认 ((控 其 态)[2] == 1 且 (控 其 态)[3] == 1) 'close invokes each resource release once'.
关闭 态.
确认 ((控 其 态)[2] == 1 且 (控 其 态)[3] == 1) 'repeat close is idempotent'.
(控 其 态)[0] 取 1. 态 取 准备 真.
确认 (态['enabled'] 且 非 态['owner'] 且 态['mutex'] == 空) 'existing mutex does not claim owner'.
确认 ((控 其 态)[2] == 2 且 非 (发布 态 柄)) 'nonowner handle closed and publication rejected'.
(控 其 态)[0] 取 2. 态 取 准备 真.
确认 (非 态['owner'] 且 态['error'] == 'Single-instance mutex unavailable: 5') 'mutex failure writes error without index assignment'.
(控 其 态)[0] 取 3. 态 取 准备 真.
确认 (非 态['enabled'] 且 态['error'] == 'identity unavailable') 'identity catch safely writes disabled and error'.
(控 其 态)[0] 取 4. 态 取 准备 真.
确认 (非 态['enabled'] 且 态['error'] == 'namespace rejected') 'namespace catch safely writes disabled and error'.
(控 其 态)[0] 取 0. 态 取 准备 真. (控 其 态)[0] 取 5.
确认 (非 (发布 态 柄) 且 态['window'] == 空) 'failed publication leaves window empty'.
关闭 态.
确认 (非 态['owner'] 且 态['mutex'] == 空) 'failed publication owner can release mutex'.
重置 10. 态 取 准备 假.
确认 ((转交 态 柄 (['中文.txt'])) == 'local' 且 (控 其 态)[6] == 0 且 (控 其 态)[9] == 0) 'disabled transfer does not normalize or send'.
重置 10. 态 取 准备 真.
确认 ((转交 态 柄 (['中文.txt'])) == 'local' 且 (控 其 态)[6] == 0) 'owner transfer remains local without send'.
重置 10. 态 取 接手态.
确认 ((转交 态 柄 (['中文 空格.txt','二.txt'])) == 'accepted') 'exact ACK accepts transfer'.
确认 ((控 其 态)[6] == 1 且 (控 其 态)[9] == 2) 'ACK sends one complete normalized batch once'.
确认 ((控 其 态)[4] == 1) 'ACK releases owned transport text'.
重置 11. 态 取 接手态.
确认 ((转交 态 柄 (['a.txt'])) == 'local' 且 (控 其 态)[6] == 1) 'explicit NACK permits local route once'.
重置 12. 态 取 接手态.
确认 ((转交 态 柄 (['a.txt'])) == 'uncertain' 且 (控 其 态)[6] == 1) 'timeout never silently opens or resends'.
重置 13. 态 取 接手态.
确认 ((转交 态 柄 (['a.txt'])) == 'uncertain') 'unknown reply remains uncertain'.
重置 14. 态 取 接手态.
确认 ((转交 态 柄 (['a.txt'])) == 'uncertain' 且 (控 其 态)[6] == 1) 'send exception preserves uncertainty'.
确认 ((控 其 态)[4] == 1) 'send exception releases transport text'.
重置 15. 态 取 接手态.
确认 ((转交 态 柄 (['a.txt'])) == 'uncertain' 且 非 态['owner']) 'unpublished live owner reaches uncertain not local'.
确认 ((控 其 态)[6] == 0 且 (控 其 态)[7] == 4 且 (控 其 态)[1] == 5) 'discovery is bounded and sends no request'.
重置 16. 态 取 准备 真.
确认 (非 态['owner']) 'later-claim begins as nonowner'.
确认 ((转交 态 柄 (['a.txt'])) == 'local' 且 态['owner'] 且 态['mutex'] != 空) 'abandoned namespace safely claims owner'.
确认 ((控 其 态)[6] == 0) 'successful later claim needs no transport'.
重置 20. 态 取 接手态.
确认 ((转交 态 柄 (['a.txt'])) == 'accepted') 'owner publication during discovery is accepted'.
确认 ((控 其 态)[7] == 2 且 (控 其 态)[6] == 1) 'discovery retries only lookup not request'.
重置 17. 态 取 接手态. 捕 取 [假].
试 转交 态 柄 (['a.txt']). 救 原因 捕[0] 取 原因 == 'target lookup failed'. 终
确认 (捕[0] 且 (控 其 态)[6] == 0) 'target lookup failure propagates without delivery'.
重置 18. 态 取 接手态. 捕 取 [假].
试 转交 态 柄 (['a.txt']). 救 原因 捕[0] 取 原因 == 'absolute conversion failed'. 终
确认 (捕[0] 且 (控 其 态)[6] == 0) 'normalization failure never delivers partial batch'.
重置 10. 态 取 接手态.
确认 ((转交 态 柄 ([])) == 'accepted' 且 (控 其 态)[6] == 1) 'empty request activates via one acknowledged send'.

重置 21. 态 取 接手态.
确认 ((转交 态 柄 (['中文.txt'])) == 'accepted' 且 (控 其 态)[6] == 2) 'BUSY3 then ACK retries exactly once'.
确认 ((控 其 态)[9] == 1 且 (控 其 态)[4] == 1 且 (控 其 态)[7] == 1) 'busy retry keeps one normalized immutable packet and releases it once'.
重置 22. 态 取 接手态.
确认 ((转交 态 柄 (['a.txt'])) == 'local' 且 (控 其 态)[6] == 2) 'BUSY3 then NACK keeps explicit local policy'.
重置 23. 态 取 接手态.
确认 ((转交 态 柄 (['a.txt'])) == 'uncertain' 且 (控 其 态)[6] == 2) 'BUSY3 then timeout never retries again'.
重置 24. 态 取 接手态.
确认 ((转交 态 柄 (['a.txt'])) == 'uncertain' 且 (控 其 态)[6] == 2) 'BUSY3 then unknown never retries again'.
重置 25. 态 取 接手态.
确认 ((转交 态 柄 (['a.txt'])) == 'uncertain' 且 (控 其 态)[6] == 3 且 (控 其 态)[12] == 950) 'busy deadline clamps final send to remaining original budget'.
重置 26. 态 取 接手态.
确认 ((转交 态 柄 (['a.txt'])) == 'uncertain' 且 (控 其 态)[6] == 1) 'owner PID change forbids retry'.
重置 27. 态 取 接手态.
确认 ((转交 态 柄 (['a.txt'])) == 'uncertain' 且 (控 其 态)[6] == 1) 'owner HWND change forbids redirect'.
重置 28. 态 取 接手态.
确认 ((转交 态 柄 (['a.txt'])) == 'uncertain' 且 (控 其 态)[6] == 1) 'owner property disappearance forbids retry'.
重置 29. 态 取 接手态.
确认 ((转交 态 柄 (['a.txt'])) == 'uncertain' 且 (控 其 态)[6] == 16) 'busy attempt bound includes initial send'.
显 'TOTAL PASS: '+(次数[0] 为 句).
"""
    path=output/'state-probe.ru';path.write_text(header+body+probe,encoding='utf-8');return path


API_BOUNDARIES=('_CloseHandle','_CreateMutexW','_GetCurrentProcessId','_RemoveProp','_Send','_SetProp','_Sleep','_Tick')
ALL_EXPORTS={
    'single_instance.ru':('_释放','_身份','_窗口进程','_窗口身份','_占用','准备','发布','关闭','_目标','转交','接收','激活'),
    'single_instance_policy.ru':('宽数','验路','编包','解包','结果','设置结果','发现结果'),
    'single_instance_settings.ru':('测试路径','命名空间','_有效路径','_读取','_写入','载入偏好','保存偏好','测试载入','测试保存'),
    'tab_close_policy.ru':('目标',),
    'tab_context.ru':('点击','弹出'),
}
EXPECTED_ASSERTIONS=45


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def execute(compiler,path,folder,expect_failure=False):
    rows=[]
    commands=[('python',[sys.executable,str(compiler),'run',str(path)]),
              ('build',[sys.executable,str(compiler),'build','--cc','gcc',str(path),'-o',str(folder/'state-probe')]),
              ('c',[str(folder/'state-probe')])]
    for label,cmd in commands:
        result=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=120)
        log=folder/(label+'.log');log.write_text(result.stdout+result.stderr,encoding='utf-8')
        if label=='build':
            if result.returncode: raise RuntimeError('Probe C compile failed: '+result.stderr)
        elif expect_failure:
            marker = ({'python':'只有阵元素可赋值','c':'只能修改阵的索引'}[label]
                      if expect_failure=='original-dictionary-write' else 'FAIL:')
            if result.returncode==0 or marker not in result.stdout+result.stderr:
                raise RuntimeError('Negative control was not rejected by assertions: '+label)
        else:
            if result.returncode: raise RuntimeError(label+' failed: '+result.stdout+result.stderr)
            if re.findall(r'^TOTAL PASS: (\d+)$',result.stdout,re.M)!=[str(EXPECTED_ASSERTIONS)] or len(re.findall(r'^PASS: ',result.stdout,re.M))!=EXPECTED_ASSERTIONS:
                raise RuntimeError('state assertion inventory mismatch')
        rows.append({'backend':label,'returncode':result.returncode,'log_sha256':sha(log)})
    return rows


def coverage_matrix(root):
    matrix={}
    for filename,expected in ALL_EXPORTS.items():
        path=root/'src'/filename
        text=path.read_text(encoding='utf-8')
        names=tuple(re.findall(r'^(?:算|作) ([^ \:]+)',text,re.M))
        if names!=expected: raise ValueError('Production export inventory changed: '+filename)
        entries={}
        for name in names:
            if filename=='single_instance.ru':
                route=('this: complete unchanged production body on interpreter and GCC with declared OS seams'
                       if name in FUNCTIONS else 'Windows native lifecycle / actual GUI; not executed by this portable state harness')
            elif filename=='single_instance_policy.ru':
                route='pure policy41 suite; transfer calls real 编包/宽数/验路/结果/发现结果 here; not native wire ABI'
            elif filename=='single_instance_settings.ru':
                route='settings11 Windows registry fixture; GUI persistence and isolated namespace; not executed here'
            elif filename=='tab_close_policy.ru':
                route='close-policy16 portable suite plus native app-close fixtures; not executed here'
            else:
                route='actual native GUI clicked-tab/context-menu stages; not executed here'
            entries[name]={'evidence_route':route,'body_sha256':hashlib.sha256(function(text,name).encode()).hexdigest()}
        matrix[filename]={'source_sha256':sha(path),'exports':entries}
    return matrix


def run(ru_root,output):
    ru_root=ru_root.resolve();compiler=ru_root/'ru'
    commit=subprocess.check_output(['git','-C',str(ru_root),'rev-parse','HEAD'],text=True).strip()
    clean=subprocess.run(['git','-C',str(ru_root),'diff','--quiet','HEAD','--'],capture_output=True)
    if clean.returncode:raise ValueError('Compiler tracked files differ from reported commit')
    hashes=static_check(ru_root)
    source=(ROOT/'src/single_instance.ru').read_text(encoding='utf-8')
    body=''.join(function(source,name) for name in FUNCTIONS)
    if tuple(sorted(set(re.findall(r'(_[A-Za-z0-9]+) 其 调用',body))))!=API_BOUNDARIES:
        raise ValueError('FFI boundary inventory changed; update explicit seam coverage')
    matrix=coverage_matrix(ROOT)
    path=prepare(output,source)
    (output/'unmodified-production-bodies.ru').write_text(body,encoding='utf-8')
    results=execute(compiler,path,output)
    dictionary_old="态 其 增 'owner' 真."
    response="状 取 策 其 结果 (非 ((果 其 值) 其 为空)) ((回 其 读 'n') 其 数)."
    discovery="若 等待 != 'wait' 则 得 等待. 然"
    for old in (dictionary_old,response,discovery):
        if source.count(old)!=1:raise ValueError('Negative mutation site inventory changed')
    mutations={
        'original-dictionary-write':source.replace(dictionary_old,"态['owner'] 取 真."),
        'nack-falsely-accepted':source.replace(response,response+" 若 ((回 其 读 'n') 其 数) == 2 则 状 取 'accepted'. 然"),
        'timeout-falsely-local':source.replace(response,response+" 若 (果 其 值) 其 为空 则 状 取 'local'. 然"),
        'discovery-falsely-local':source.replace(discovery,"若 等待 != 'wait' 则 得 'local'. 然"),
        'busy-falsely-accepted':source.replace(response,response+" 若 状 == 'busy' 则 状 取 'accepted'. 然"),
        'timeout-retried':source.replace(response,response+" 若 (果 其 值) 其 为空 则 状 取 'busy'. 然"),
    }
    negatives=[]
    for name,mutant in mutations.items():
        folder=output/name;probe=prepare(folder,mutant)
        negatives.append({'name':name,'mutated_source_sha256':hashlib.sha256(mutant.encode()).hexdigest(),
                          'results':execute(compiler,probe,folder,name)})
    generated={str(p.relative_to(output)):sha(p) for p in sorted(output.rglob('*.ru'))}
    receipt={'schema':'ru-notepad-portable-instance-state-v1','scope':__doc__,
             'compiler_commit':commit,'compiler_entry_sha256':sha(compiler),
             'source_sha256':hashlib.sha256(source.encode()).hexdigest(),
             'complete_production_functions':list(FUNCTIONS),'api_boundaries':list(API_BOUNDARIES),
             'additional_os_seams':['_身份 (token/session lookup)','_目标 (window discovery)','_窗口进程 (owned window PID)' ],
             'portable_ffi_seams':['owned text/packet/receipt values and allocation types','pointer conversions','absolute path conversion','test namespace'],
             'production_bodies_sha256':sha(output/'unmodified-production-bodies.ru'),
             'all_src_ast_scan':hashes,'coverage_matrix':matrix,'assertions_per_backend':EXPECTED_ASSERTIONS,
             'results':results,'negative_controls':negatives,'generated_sources':generated}
    (output/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'SINGLE_INSTANCE_STATE_PORTABLE_PASS {EXPECTED_ASSERTIONS} interpreter + {EXPECTED_ASSERTIONS} GCC; 6 negative controls each backend; not Windows evidence')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ru-root',type=Path,required=True)
    p.add_argument('--output',type=Path,default=ROOT.parent/'single-instance-state-evidence')
    a=p.parse_args();run(a.ru_root,a.output.resolve())
