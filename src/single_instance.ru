# Same-user/session routing filters, NOT authentication of the actual sender.
# WM_COPYDATA wParam is caller-supplied; its window token is only a routing check.
# Keep default desktop/UIPI/mutex ACLs; no filter relaxation, elevation or shell.
# Hold the creation mutex handle only in the publishing owner. Retry only explicit BUSY3 zero-admission receipts.
密 取 外言 '如:密'.
窗 取 外言 'win32.ru'.
策 取 外言 'single_instance_policy.ru'.
件编 取 外言 'file_codec.ru'.
设 取 外言 'single_instance_settings.ru'.
P 取 密 其 指针. U 取 密 其 u32. I 取 密 其 i32.
UP 取 密 其 uintptr. IP 取 密 其 intptr. V 取 密 其 无值.
K 取 密 其 系统库 'kernel32.dll'.
A 取 密 其 系统库 'advapi32.dll'.
W 取 密 其 系统库 'user32.dll'.
_数 取 密 其 结构 [['n',U]].
_柄 取 密 其 结构 [['h',P]].
_回执 取 密 其 结构 [['n',UP]].
_令牌 取 密 其 结构 [['sid',P],['attributes',U]].
_包 取 密 其 结构 [['tag',UP],['bytes',U],['data',P]].
_CreateMutexW 取 K 其 绑定 'CreateMutexW' (密 其 签名 P ([P,I,P]) 'win64').
_CloseHandle 取 K 其 绑定 'CloseHandle' (密 其 签名 I ([P]) 'win64').
_GetCurrentProcessId 取 K 其 绑定 'GetCurrentProcessId' (密 其 签名 U ([]) 'win64').
_ProcessIdToSessionId 取 K 其 绑定 'ProcessIdToSessionId' (密 其 签名 I ([U,P]) 'win64').
_OpenProcess 取 K 其 绑定 'OpenProcess' (密 其 签名 P ([U,I,U]) 'win64').
_OpenProcessToken 取 A 其 绑定 'OpenProcessToken' (密 其 签名 I ([P,U,P]) 'win64').
_GetTokenInformation 取 A 其 绑定 'GetTokenInformation' (密 其 签名 I ([P,I,P,U,P]) 'win64').
_ConvertSidToStringSidW 取 A 其 绑定 'ConvertSidToStringSidW' (密 其 签名 I ([P,P]) 'win64').
_LocalFree 取 K 其 绑定 'LocalFree' (密 其 签名 P ([P]) 'win64').
_Copy 取 K 其 绑定 'RtlMoveMemory' (密 其 签名 V ([P,P,UP]) 'win64').
_Sleep 取 K 其 绑定 'Sleep' (密 其 签名 V ([U]) 'win64').
_Tick 取 K 其 绑定 'GetTickCount64' (密 其 签名 (密 其 u64) ([]) 'win64').
_Find 取 W 其 绑定 'FindWindowExW' (密 其 签名 P ([P,P,P,P]) 'win64').
_PID 取 W 其 绑定 'GetWindowThreadProcessId' (密 其 签名 U ([P,P]) 'win64').
_GetProp 取 W 其 绑定 'GetPropW' (密 其 签名 P ([P,P]) 'win64').
_SetProp 取 W 其 绑定 'SetPropW' (密 其 签名 I ([P,P,P]) 'win64').
_RemoveProp 取 W 其 绑定 'RemovePropW' (密 其 签名 P ([P,P]) 'win64').
_Send 取 W 其 绑定 'SendMessageTimeoutW' (密 其 签名 IP ([P,U,UP,IP,U,U,P]) 'win64').
_名称 取 'RuNotepad.SingleInstance.v1'.

作 _释放 存们 柄们:
    位 取 0. 循 柄们 其 量 次 _CloseHandle 其 调用 [柄们[位]]. 位 取 位+1. 环
    位 取 0. 循 存们 其 量 次 存们[位] 其 关闭. 位 取 位+1. 环
为
算 _身份 进程号 为 数:
    存们 取 []. 柄们 取 []. 文 取 ''.
    试
        会话 取 _数 其 新建. 存们 其 增 会话.
        窗 其 成功 (_ProcessIdToSessionId 其 调用 [进程号,会话]) 'ProcessIdToSessionId'.
        进程 取 窗 其 成功 (_OpenProcess 其 调用 [4096,0,进程号]) 'OpenProcess'. 柄们 其 增 进程.
        柄存 取 _柄 其 新建. 存们 其 增 柄存.
        窗 其 成功 (_OpenProcessToken 其 调用 [进程,8,柄存]) 'OpenProcessToken'.
        令牌 取 柄存 其 读 'h'. 柄们 其 增 令牌.
        存 取 密 其 缓冲 512. 存们 其 增 存.
        长 取 _数 其 新建. 存们 其 增 长.
        窗 其 成功 (_GetTokenInformation 其 调用 [令牌,1,存,512,长]) 'GetTokenInformation'.
        头 取 _令牌 其 新建. 存们 其 增 头.
        _Copy 其 调用 [头,存,(_令牌 其 大小)].
        窗 其 成功 (_ConvertSidToStringSidW 其 调用 [(头 其 读 'sid'),柄存]) 'ConvertSidToStringSidW'.
        SID文 取 柄存 其 读 'h'.
        长度 取 (((窗 其 lstrlenW) 其 调用 [SID文]) 其 值) 其 数.
        输出 取 密 其 缓冲 512. 存们 其 增 输出.
        若 长度 > 0 且 长度 < 200 则 _Copy 其 调用 [输出,SID文,(长度+1)*2]. 然
        _LocalFree 其 调用 [SID文].
        若 长度 <= 0 或 长度 >= 200 则 卒 'Invalid process SID.'. 然
        文 取 (输出 其 解UTF16)+'-'+((会话 其 读 'n') 其 数 为 句).
    救 原因
        _释放 存们 柄们. 卒 原因.
    终
    _释放 存们 柄们. 得 文.
法
算 _窗口进程 窗口:
    存 取 _数 其 新建.
    果 取 _PID 其 调用 [窗口,存].
    号 取 (存 其 读 'n') 其 数. 存 其 关闭.
    若 (果 其 值) 其 为空 或 号 == 0 则 卒 'Invalid single-instance window.'. 然
    得 号.
法
算 _窗口身份 窗口:
    得 _身份 (_窗口进程 窗口).
法
算 _占用 态:
    名 取 密 其 UTF16 ('Local\\'+态['property']+'.'+态['identity']).
    果 取 _CreateMutexW 其 调用 [空,0,名]. 名 其 关闭.
    柄 取 窗 其 结果 果.
    若 柄 其 为空 则 态 其 增 'error' ('Single-instance mutex unavailable: '+((果 其 错误码) 为 句)). 得 假. 然
    若 果 其 错误码 == 183 则 _CloseHandle 其 调用 [柄]. 得 假. 然
    态 其 增 'mutex' 柄. 态 其 增 'owner' 真. 得 真.
法
算 准备 启用 为 事实:
    态 取 {'enabled':启用,'owner':假,'mutex':空,'identity':'','window':空,'error':'','property':_名称}.
    若 非 启用 则 得 态. 然
    试
        后缀 取 设 其 命名空间.
        若 后缀 != '' 则 态 其 增 'property' (_名称+'.test.'+后缀). 然
        态 其 增 'identity' (_身份 (((_GetCurrentProcessId 其 调用 []) 其 值) 其 数)).
        _占用 态.
    救 原因
        态 其 增 'enabled' 假. 态 其 增 'error' (原因 为 句).
    终
    得 态.
法
算 发布 态 窗口:
    若 非 态['owner'] 则 得 假. 然
    名 取 密 其 UTF16 态['property'].
    果 取 _SetProp 其 调用 [窗口,名,(P 其 值 1)]. 名 其 关闭.
    若 (果 其 值) 其 为空 则 得 假. 然
    态 其 增 'window' 窗口. 得 真.
法
作 关闭 态:
    若 非 (态['window'] == 空) 则
        名 取 密 其 UTF16 态['property']. _RemoveProp 其 调用 [态['window'],名]. 名 其 关闭.
        态 其 增 'window' 空.
    然
    若 非 (态['mutex'] == 空) 则 _CloseHandle 其 调用 [态['mutex']]. 态 其 增 'mutex' 空. 然
    态 其 增 'owner' 假.
为
算 _目标 态:
    类 取 密 其 UTF16 'RuNotepad.Main.0.1'. 名 取 密 其 UTF16 态['property'].
    后 取 空. 找 取 空.
    试
        循 64 次
            后 取 (_Find 其 调用 [空,后,类,空]) 其 值.
            若 后 其 为空 则 破. 然
            若 非 (((_GetProp 其 调用 [后,名]) 其 值) 其 为空) 则
                试 若 (_窗口身份 后) == 态['identity'] 则 找 取 后. 破. 然 救 原因 终
            然
        环
    救 原因
        类 其 关闭. 名 其 关闭. 卒 原因.
    终
    类 其 关闭. 名 其 关闭. 得 找.
法
# local = no delivery or explicit NACK; uncertain must NOT open paths by itself.
算 转交 态 窗口 路们 为 句 阵:
    若 非 态['enabled'] 或 态['owner'] 则 得 'local'. 然
    绝对们 取 []. 位 取 0.
    循 路们 其 量 次 绝对们 其 增 (件编 其 绝对路径 路们[位]). 位 取 位+1. 环
    文 取 策 其 编包 绝对们.
    起 取 ((_Tick 其 调用 []) 其 值) 其 数. 目标 取 空.
    循
        目标 取 _目标 态.
        若 非 (目标 == 空) 则 破. 然
        # A live owner that has not published is not permission for a second
        # automatic open. Wait at most 5s, then retain the request as uncertain.
        等待 取 策 其 发现结果 (_占用 态) ((((_Tick 其 调用 []) 其 值) 其 数)-起).
        若 等待 != 'wait' 则 得 等待. 然
        _Sleep 其 调用 [25].
    环
    存 取 密 其 UTF16 文. 包 取 _包 其 新建. 回 取 _回执 其 新建.
    包 其 写 'tag' 1380864049. 包 其 写 'bytes' (存 其 大小). 包 其 写 'data' (存 其 地址).
    状 取 'uncertain'.
    试
        原进程 取 _窗口进程 目标.
        # Immutable packet; never redirect a retry to a replacement owner.
        循 16 次
            现目标 取 _目标 态.
            若 现目标 == 空 或 (现目标 其 句) != (目标 其 句) 或 (_窗口进程 目标) != 原进程 则 破. 然
            剩 取 6000-((((_Tick 其 调用 []) 其 值) 其 数)-起).
            若 剩 <= 0 则 破. 然
            等 取 1000. 若 等 > 剩 则 等 取 剩. 然
            回 其 写 'n' 0.
            果 取 _Send 其 调用 [目标,74,(UP 其 重释 窗口),(IP 其 重释 (包 其 地址)),3,等,回].
            状 取 策 其 结果 (非 ((果 其 值) 其 为空)) ((回 其 读 'n') 其 数).
            若 状 != 'busy' 则 破. 然
            # BUSY3 guarantees no enqueue; timeout/unknown never reaches this loop.
            状 取 'uncertain'.
            剩 取 6000-((((_Tick 其 调用 []) 其 值) 其 数)-起).
            若 剩 <= 0 则 破. 然
            暂 取 25. 若 暂 > 剩 则 暂 取 剩. 然
            _Sleep 其 调用 [暂].
        环
    救 原因
        状 取 'uncertain'.
    终
    存 其 关闭. 包 其 关闭. 回 其 关闭. 得 状.
法
# Caller returns 1 after enqueue, 2 for reject, 3 only for validated zero-admission open finalization.
# Never retain the COPYDATA pointer beyond this synchronous call.
算 接收 态 发送窗 参数:
    若 非 态['enabled'] 或 非 态['owner'] 或 (_窗口身份 (P 其 重释 发送窗)) != 态['identity'] 则 卒 'Single-instance sender identity mismatch.'. 然
    若 (P 其 重释 参数) 其 为空 则 卒 'Missing single-instance payload.'. 然
    包 取 _包 其 新建. 存 取 空. 文 取 ''.
    试
        _Copy 其 调用 [包,(P 其 重释 参数),(_包 其 大小)].
        长 取 (包 其 读 'bytes') 其 数.
        若 (包 其 读 'tag') 其 数 != 1380864049 或 长 < 12 或 长 > 262144 或 长 % 2 != 0 或 ((包 其 读 'data') 其 为空) 则 卒 'Invalid single-instance payload.'. 然
        # Native buffers are zero-initialized; the extra WCHAR bounds lstrlenW
        # even if the declared packet omits its final terminator.
        存 取 密 其 缓冲 (长+2).
        _Copy 其 调用 [存,(包 其 读 'data'),长].
        实长 取 (((窗 其 lstrlenW) 其 调用 [存]) 其 值) 其 数.
        若 实长 != 长/2-1 则 卒 'Single-instance payload contains hidden or missing terminator.'. 然
        果 取 (窗 其 WideCharToMultiByte) 其 调用 [65001,128,存,实长,空,0,空,空].
        若 (果 其 值) 其 为空 则 卒 'Invalid single-instance UTF16.'. 然
        文 取 存 其 解UTF16.
    救 原因
        若 非 (存 == 空) 则 存 其 关闭. 然
        包 其 关闭. 卒 原因.
    终
    存 其 关闭. 包 其 关闭. 得 策 其 解包 文.
法

_IsIconic 取 W 其 绑定 'IsIconic' (密 其 签名 I ([P]) 'win64').
_Foreground 取 W 其 绑定 'SetForegroundWindow' (密 其 签名 I ([P]) 'win64').
算 激活 窗口:
    若 非 (((_IsIconic 其 调用 [窗口]) 其 值) 其 为空) 则
        (窗 其 ShowWindow) 其 调用 [窗口,9].
    然
    # Respect Windows foreground restrictions; do not attach threads or spoof input.
    得 非 (((_Foreground 其 调用 [窗口]) 其 值) 其 为空).
法
