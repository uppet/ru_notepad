# Windows native lifecycle: real SID/session, mutex, HWND property and cleanup.
# Process-local unique namespace; no normal preference or owner is touched.
模 取 外言 '../src/single_instance.ru'.
窗 取 外言 '../src/win32.ru'.
密 取 外言 '如:密'.
P 取 密 其 指针. U 取 密 其 u32. I 取 密 其 i32.
K 取 密 其 系统库 'kernel32.dll'. W 取 密 其 系统库 'user32.dll'.
PID 取 K 其 绑定 'GetCurrentProcessId' (密 其 签名 U ([]) 'win64').
时钟 取 K 其 绑定 'GetTickCount64' (密 其 签名 (密 其 u64) ([]) 'win64').
设环境 取 K 其 绑定 'SetEnvironmentVariableW' (密 其 签名 I ([P,P]) 'win64').
取属性 取 W 其 绑定 'GetPropW' (密 其 签名 P ([P,P]) 'win64').
次数 取 [0].
作 确认 条件 为 事实 文 为 句:
    若 非 条件 则 卒 ('FAIL: '+文). 然
    次数[0] 取 次数[0]+1. 显 'PASS: '+文.
为
后缀 取 'native-instance-'+(((((PID 其 调用 []) 其 值) 其 数)) 为 句)+'-'+(((((时钟 其 调用 []) 其 值) 其 数)) 为 句).
环境名 取 密 其 UTF16 'RU_NOTEPAD_INSTANCE_TEST_KEY'. 环境值 取 密 其 UTF16 后缀.
类名 取 密 其 UTF16 'STATIC'. 标题 取 密 其 UTF16 'ru_notepad isolated native instance fixture'.
态 取 空. 次态 取 空. 三态 取 空. 柄 取 空. 属性名 取 空.
试
    窗 其 成功 (设环境 其 调用 [环境名,环境值]) 'SetEnvironmentVariableW(test namespace)'.
    关态 取 模 其 准备 假.
    确认 (非 关态['enabled'] 且 非 关态['owner'] 且 关态['mutex'] == 空) 'disabled native preparation avoids mutex'.
    模 其 关闭 关态.
    确认 (非 关态['owner'] 且 关态['window'] == 空) 'disabled native close is safe'.
    态 取 模 其 准备 真.
    确认 (态['enabled'] 且 态['error'] == '') 'enabled native preparation has no error'.
    确认 (态['owner'] 且 态['mutex'] != 空) 'enabled native preparation owns real mutex'.
    确认 (态['identity'] != '' 且 (态['property'] 其 含 后缀)) 'native SID session and isolated property recorded'.
    柄 取 窗 其 成功 ((窗 其 CreateWindowExW) 其 调用 [0,类名,标题,0,0,0,1,1,空,空,空,空]) 'CreateWindowExW(isolated STATIC)'.
    # Independent wrappers compare exact uintptr strings, never heap identity/double.
    同柄 取 P 其 重释 ((密 其 uintptr) 其 重释 柄).
    确认 ((同柄 其 句) == (柄 其 句)) 'independent native HWND wrappers preserve exact address'.
    确认 (((P 其 值 1) 其 句) != ((P 其 值 2) 其 句)) 'different native addresses are not equal'.
    确认 ((模 其 _窗口进程 同柄) == (((PID 其 调用 []) 其 值) 其 数)) 'rewrapped real HWND retains owning PID'.
    确认 (模 其 发布 态 柄) 'native owner publishes hidden window'.
    确认 (态['window'] == 柄) 'native publication writes window state'.
    属性名 取 密 其 UTF16 态['property'].
    确认 (非 (((取属性 其 调用 [柄,属性名]) 其 值) 其 为空)) 'published native HWND property exists'.
    次态 取 模 其 准备 真.
    确认 (次态['enabled'] 且 非 次态['owner'] 且 次态['mutex'] == 空) 'second native preparation does not claim existing owner'.
    确认 (非 (模 其 发布 次态 柄)) 'nonowner cannot publish property'.
    模 其 关闭 次态.
    模 其 关闭 态.
    确认 (非 态['owner'] 且 态['mutex'] == 空 且 态['window'] == 空) 'native close clears dictionary lifecycle state'.
    确认 (((取属性 其 调用 [柄,属性名]) 其 值) 其 为空) 'native close removes HWND property'.
    模 其 关闭 态.
    确认 (态['mutex'] == 空 且 态['window'] == 空) 'repeated native close is safe'.
    三态 取 模 其 准备 真.
    确认 (三态['owner'] 且 三态['error'] == '') 'released mutex can be claimed again'.
    模 其 关闭 三态.
    坏名 取 密 其 UTF16 'invalid/namespace'.
    窗 其 成功 (设环境 其 调用 [环境名,坏名]) 'SetEnvironmentVariableW(invalid test)'. 坏名 其 关闭.
    坏态 取 模 其 准备 真.
    确认 (非 坏态['enabled'] 且 非 坏态['owner'] 且 坏态['error'] != '') 'native preparation catch safely records invalid namespace'.
    模 其 关闭 坏态.
救 原因
    若 三态 != 空 则 模 其 关闭 三态. 然
    若 次态 != 空 则 模 其 关闭 次态. 然
    若 态 != 空 则 模 其 关闭 态. 然
    若 属性名 != 空 则 属性名 其 关闭. 然
    若 柄 != 空 则 (窗 其 DestroyWindow) 其 调用 [柄]. 然
    设环境 其 调用 [环境名,空].
    环境名 其 关闭. 环境值 其 关闭. 类名 其 关闭. 标题 其 关闭.
    卒 原因.
终
属性名 其 关闭.
窗 其 成功 ((窗 其 DestroyWindow) 其 调用 [柄]) 'DestroyWindow(isolated STATIC)'.
窗 其 成功 (设环境 其 调用 [环境名,空]) 'SetEnvironmentVariableW(clear test)'.
环境名 其 关闭. 环境值 其 关闭. 类名 其 关闭. 标题 其 关闭.
显 'TOTAL PASS: '+(次数[0] 为 句).
