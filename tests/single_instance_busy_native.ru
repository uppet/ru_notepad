# Real hidden Windows application: a genuine open-completion callback observes
# WM_COPYDATA BUSY3, then the same intact packet is accepted after teardown.
# No busy/finalizing flag is fabricated; this is not a two-process GUI test.
应用 取 外言 '../src/main.ru'.
单例 取 外言 '../src/single_instance.ru'.
策略 取 外言 '../src/single_instance_policy.ru'.
窗 取 外言 '../src/win32.ru'.
件库 取 外言 '../src/file_codec.ru'.
编 取 外言 '../src/editor.ru'.
密 取 外言 '如:密'.
P 取 密 其 指针. U 取 密 其 u32. I 取 密 其 i32. UP 取 密 其 uintptr.
K 取 密 其 系统库 'kernel32.dll'.
PID 取 K 其 绑定 'GetCurrentProcessId' (密 其 签名 U ([]) 'win64').
时钟 取 K 其 绑定 'GetTickCount64' (密 其 签名 (密 其 u64) ([]) 'win64').
设环境 取 K 其 绑定 'SetEnvironmentVariableW' (密 其 签名 I ([P,P]) 'win64').
删文件 取 K 其 绑定 'DeleteFileW' (密 其 签名 I ([P]) 'win64').
包型 取 密 其 结构 [['tag',UP],['bytes',U],['data',P]].
次数 取 [0]. 主盒 取 [空]. 包盒 取 [空].
观察 取 {'calls':0,'busy':假,'finalizing':假,'operationEmpty':假,'queueBefore':-1,'good':0,'bad':0,'queueAfter':-1}.
作 确认 条件 为 事实 文 为 句:
    若 非 条件 则 卒 ('FAIL: '+文). 然
    次数[0] 取 次数[0]+1. 显 'PASS: '+文.
为
算 观察收尾 项们:
    观察 其 增 'calls' ((观察 其 查 'calls')+1).
    若 (观察 其 查 'calls') == 1 则
        态 取 应用 其 A.
        观察 其 增 'busy' (态 其 查 'busy').
        观察 其 增 'finalizing' (态 其 查 'openFinalizing').
        观察 其 增 'operationEmpty' ((态 其 查 'operation') == 空).
        观察 其 增 'queueBefore' ((态 其 查 'queue') 其 量).
        观察 其 增 'good' ((窗 其 发指 主盒[0] 74 (UP 其 重释 主盒[0]) 包盒[0]) 其 数).
        包盒[0] 其 写 'tag' 0.
        观察 其 增 'bad' ((窗 其 发指 主盒[0] 74 (UP 其 重释 主盒[0]) 包盒[0]) 其 数).
        包盒[0] 其 写 'tag' 1380864049.
        观察 其 增 'queueAfter' ((态 其 查 'queue') 其 量).
    然
    得 0.
法
作 完成工作:
    起 取 (((时钟 其 调用 []) 其 值) 其 数).
    循
        若 非 ((应用 其 A) 其 查 'busy') 则 破. 然
        应用 其 工作时钟.
        若 (((时钟 其 调用 []) 其 值) 其 数)-起 > 30000 则 卒 'native busy fixture deadline'. 然
    环
为
算 元初 参数 为 句 阵:
    后缀 取 'busy-native-'+((((PID 其 调用 []) 其 值) 其 数) 为 句)+'-'+((((时钟 其 调用 []) 其 值) 其 数) 为 句).
    近环境名 取 密 其 UTF16 'RU_NOTEPAD_RECENT_TEST_KEY'.
    环境名 取 密 其 UTF16 'RU_NOTEPAD_INSTANCE_TEST_KEY'. 环境值 取 密 其 UTF16 后缀.
    首路 取 (窗 其 目录)+后缀+'-first.txt'. 次路 取 (窗 其 目录)+后缀+'-second.txt'.
    首文 取 'first 中文😀'. 次文 取 'second 中文😀'.
    首存 取 密 其 UTF16 首路. 次存 取 密 其 UTF16 次路.
    线文 取 策略 其 编包 ([次路]). 线存 取 密 其 UTF16 线文.
    包盒[0] 取 包型 其 新建.
    包盒[0] 其 写 'tag' 1380864049. 包盒[0] 其 写 'bytes' (线存 其 大小). 包盒[0] 其 写 'data' (线存 其 地址).
    单态 取 空.
    试
        窗 其 成功 (设环境 其 调用 [环境名,环境值]) 'SetEnvironmentVariableW(busy fixture)'.
        窗 其 成功 (设环境 其 调用 [近环境名,环境值]) 'SetEnvironmentVariableW(recent isolation)'.
        件库 其 写文件 首路 首文 65001 假 ''.
        件库 其 写文件 次路 次文 65001 假 ''.
        主盒[0] 取 应用 其 初始化 ([]) 假.
        态 取 应用 其 A.
        单态 取 单例 其 准备 真.
        确认 (单态['enabled'] 且 单态['owner'] 且 单态['error'] == '') 'isolated native owner acquired'.
        确认 (单例 其 发布 单态 主盒[0]) 'actual hidden main publishes owner property'.
        态 其 增 'singleState' 单态.
        态 其 增 'recentWriter' (算 观察收尾).
        确认 (应用 其 入队 ([首路]) 0) 'real first file starts serial opening'.
        完成工作.
        确认 ((观察 其 查 'calls') == 1) 'real open completion invokes observer exactly once'.
        确认 ((观察 其 查 'busy') 且 (观察 其 查 'finalizing')) 'observer runs in genuine open finalization'.
        确认 (观察 其 查 'operationEmpty') 'document owns editor before finalization observer'.
        确认 ((观察 其 查 'queueBefore') == 0) 'original serial queue exhausted before observation'.
        确认 ((观察 其 查 'good') == 3) 'validated actual WM_COPYDATA receives BUSY3'.
        确认 ((观察 其 查 'bad') == 2) 'malformed packet remains rejected during finalization'.
        确认 ((观察 其 查 'queueAfter') == 0) 'BUSY3 and malformed rejection enqueue nothing'.
        确认 ((态 其 查 'recentError') == 0) 'observer completed without swallowed MRU error'.
        确认 (非 (态 其 查 'busy') 且 非 (态 其 查 'openFinalizing') 且 非 (态 其 查 'handoffReject')) 'normal teardown clears all routing guards'.
        确认 (((态 其 查 'docs') 其 量) == 2) 'BUSY3 has not opened second file'.
        确认 ((编 其 文本 (应用 其 编辑柄)) == 首文) 'first file exact Unicode bytes remain visible'.
        确认 ((线存 其 解UTF16) == 线文) 'original packet text retained unchanged after rejection'.
        确认 ((窗 其 发指 主盒[0] 74 (UP 其 重释 主盒[0]) 包盒[0]) 其 数 == 1) 'same intact packet is ACKed after stable teardown'.
        确认 ((态 其 查 'busy') 且 ((态 其 查 'queue') 其 量) == 1) 'ACK publishes exactly one queued request and active work'.
        完成工作.
        确认 (((态 其 查 'docs') 其 量) == 3) 'second request creates exactly one additional document'.
        确认 ((编 其 文本 (应用 其 编辑柄)) == 次文) 'second file has exact Unicode content'.
        确认 ((观察 其 查 'calls') == 2) 'second real open completes only once'.
        确认 (非 (态 其 查 'busy') 且 非 (态 其 查 'openFinalizing') 且 非 (态 其 查 'handoffReject')) 'second completion clears routing guards again'.
        确认 ((件库 其 读文件 首路 0)['text'] == 首文 且 (件库 其 读文件 次路 0)['text'] == 次文) 'fixture source texts remain unchanged'.
        单例 其 关闭 单态.
        态 其 增 'singleState' 空.
        确认 (应用 其 关程序) 'native busy fixture shuts down cleanly'.
        主盒[0] 取 空.
    救 原因
        若 单态 != 空 则 单例 其 关闭 单态. 然
        若 主盒[0] != 空 则
            试 应用 其 取消工作. 救 忽略 终
            试 应用 其 关程序. 救 忽略 终
        然
        删文件 其 调用 [首存]. 删文件 其 调用 [次存].
        设环境 其 调用 [环境名,空]. 设环境 其 调用 [近环境名,空].
        包盒[0] 其 关闭. 线存 其 关闭. 首存 其 关闭. 次存 其 关闭. 环境名 其 关闭. 近环境名 其 关闭. 环境值 其 关闭.
        卒 原因.
    终
    窗 其 成功 (删文件 其 调用 [首存]) 'DeleteFileW(first fixture)'.
    窗 其 成功 (删文件 其 调用 [次存]) 'DeleteFileW(second fixture)'.
    窗 其 成功 (设环境 其 调用 [环境名,空]) 'SetEnvironmentVariableW(clear busy fixture)'.
    窗 其 成功 (设环境 其 调用 [近环境名,空]) 'SetEnvironmentVariableW(clear recent isolation)'.
    包盒[0] 其 关闭. 线存 其 关闭. 首存 其 关闭. 次存 其 关闭. 环境名 其 关闭. 近环境名 其 关闭. 环境值 其 关闭.
    显 'TOTAL PASS: '+(次数[0] 为 句).
    得 0.
法
