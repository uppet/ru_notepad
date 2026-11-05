# Private owned-memory adapter. Import loads declarations but never starts a worker.
密 取 外言 '如:密'.
窗 取 外言 'win32.ru'.
_态 取 {'ready':假,'attempted':假,'error':'directory-helper-unavailable','library':空,'generation':0}.
_字型 取 密 其 结构 [['a',密 其 u16],['b',密 其 u16],['z',密 其 u32]].
# Loading the helper is allowed at import; no start/poll/worker call occurs here.
_GetProcAddress 取 (窗 其 内核) 其 绑定 'GetProcAddress' (密 其 签名 (窗 其 PTR) ([(窗 其 PTR),(窗 其 PTR)]) 'win64').
_路 取 (窗 其 目录)+'RuSyntax.dll'.
_存 取 密 其 UTF16 _路.
_载 取 窗 其 结果 ((窗 其 LoadLibraryExW) 其 调用 [_存,空,2304]). _存 其 关闭.
若 非 (_载 其 为空) 则
    试
        _名们 取 ['ru_dir_abi','ru_dir_event_size','ru_dir_start','ru_dir_poll','ru_dir_cancel','ru_dir_release','ru_dir_status','ru_dir_abandon','ru_dir_pick_folder'].
        _全有 取 真. _位 取 0.
        循 _名们 其 量 次
            _名存 取 密 其 UTF8 _名们[_位].
            _址 取 窗 其 结果 (_GetProcAddress 其 调用 [_载,_名存]). _名存 其 关闭.
            若 _址 其 为空 则 _全有 取 假. 然.
            _位 取 _位+1.
        环.
        若 非 _全有 则 卒 'directory-helper-exports'. 然.
        _库 取 密 其 动态库 _路. _态 其 增 'library' _库.
        _ABI 取 _库 其 绑定 'ru_dir_abi' (密 其 签名 (窗 其 U) ([]) 'win64').
        _Size 取 _库 其 绑定 'ru_dir_event_size' (密 其 签名 (窗 其 U) ([]) 'win64').
        _Start 取 _库 其 绑定 'ru_dir_start' (密 其 签名 (窗 其 U) ([(窗 其 U),(窗 其 U),(窗 其 PTR),(窗 其 U)]) 'win64').
        _Poll 取 _库 其 绑定 'ru_dir_poll' (密 其 签名 (窗 其 U) ([(窗 其 U),(窗 其 U),(窗 其 PTR),(窗 其 U)]) 'win64').
        _Cancel 取 _库 其 绑定 'ru_dir_cancel' (密 其 签名 (窗 其 U) ([(窗 其 U),(窗 其 U)]) 'win64').
        _Release 取 _库 其 绑定 'ru_dir_release' (密 其 签名 (窗 其 U) ([(窗 其 U),(窗 其 U)]) 'win64').
        _Status 取 _库 其 绑定 'ru_dir_status' (密 其 签名 (窗 其 U) ([(窗 其 U)]) 'win64').
        _Abandon 取 _库 其 绑定 'ru_dir_abandon' (密 其 签名 (窗 其 U) ([(窗 其 U),(窗 其 U)]) 'win64').
        _Pick 取 _库 其 绑定 'ru_dir_pick_folder' (密 其 签名 (窗 其 U) ([(密 其 u64),(窗 其 PTR),(窗 其 U)]) 'win64').
        若 (窗 其 结果 (_ABI 其 调用 [])) 其 数 != 65536 或 (窗 其 结果 (_Size 其 调用 [])) 其 数 != 8192 则 卒 'directory-helper-abi'. 然.
        _态 其 增 'ready' 真. _态 其 增 'error' ''.
    救 因
        _态 其 增 'error' (因 为 句).
    终.
    窗 其 结果 ((窗 其 FreeLibrary) 其 调用 [_载]).
然.
算 初始化: 得 _态['error']. 法.
算 可用: 得 _态['ready']. 法.
算 文本 点们:
    若 (点们 其 量) > 1024 则 卒 'directory-text-limit'. 然.
    果 取 ''. 位 取 0. 存 取 _字型 其 新建.
    试
        循 点们 其 量 次
            点 取 点们[位].
            若 点 < 1 或 点 > 1114111 或 点%1 != 0 或 (点 >= 55296 且 点 <= 57343) 则 卒 'directory-invalid-scalar'. 然.
            若 点 < 65536 则 存 其 写 'a' 点. 存 其 写 'b' 0.
            另 数 取 点-65536. 低 取 数%1024. 存 其 写 'a' (55296+(数-低)/1024). 存 其 写 'b' (56320+低). 然.
            果 取 果+(存 其 解UTF16). 位 取 位+1.
        环.
    救 因
        存 其 关闭. 卒 因.
    终.
    存 其 关闭. 得 果.
法.
算 转点 文:
    若 (文 其 量) > 256 则 卒 'invalid-query'. 然.
    果 取 []. 位 取 0.
    循 文 其 量 次
        存 取 密 其 UTF16 文[位].
        # One scalar occupies 2 or 4 bytes plus its terminator.
        若 (存 其 大小) == 4 则
            字 取 存 其 读U32LE阵 0 1. 果 其 增 字[0].
        另
            字 取 存 其 读U32LE阵 0 1. 低 取 字[0]%65536. 高 取 (字[0]-低)/65536.
            果 其 增 (65536+(低-55296)*1024+高-56320).
        然.
        存 其 关闭. 位 取 位+1.
    环.
    得 果.
法.
算 选目录 主 标题:
    初始化.
    若 非 可用 则 得 {'status':'error','path':'','error':_态['error']}. 然.
    存 取 密 其 缓冲 2048.
    试
        码 取 (窗 其 结果 (_Pick 其 调用 [((密 其 u64) 其 重释 主),存,1024])) 其 数.
        若 码 == 7 则 存 其 关闭. 得 {'status':'cancelled','path':'','error':''}. 然.
        若 码 != 0 则 卒 'directory-picker-failed'. 然.
        路 取 存 其 解UTF16. 存 其 关闭.
        得 {'status':'chosen','path':路,'error':''}.
    救 因
        存 其 关闭. 得 {'status':'error','path':'','error':(因 为 句)}.
    终.
法.
算 开始 代 路:
    若 非 可用 则 得 4. 然.
    若 (路 其 量) > 1023 或 路 == '' 则 得 3. 然.
    存 取 密 其 UTF16 路. 长 取 (存 其 大小)/2-1.
    若 长 > 1023 则 存 其 关闭. 得 3. 然.
    码 取 (窗 其 结果 (_Start 其 调用 [65536,代,存,长])) 其 数. 存 其 关闭. 得 码.
法.
算 生命周期:
    若 非 可用 则 得 0. 然.
    得 (窗 其 结果 (_Status 其 调用 [65536])) 其 数.
法.
算 取消 代: 得 (窗 其 结果 (_Cancel 其 调用 [65536,代])) 其 数. 法.
算 释放 代: 得 (窗 其 结果 (_Release 其 调用 [65536,代])) 其 数. 法.
算 放弃 代:
    若 非 可用 则 得 0. 然.
    得 (窗 其 结果 (_Abandon 其 调用 [65536,代])) 其 数.
法.
算 _半 字们 位:
    字 取 字们[28+(位-位%2)/2].
    若 位%2 == 0 则 得 字%65536. 然.
    得 (字-字%65536)/65536.
法.
算 _身份 字们 位:
    得 (字们[位] 为 句)+':'+(字们[位+1] 为 句).
法.
算 解事件 字们:
    若 (字们 其 量) != 2048 则 卒 'directory-event-size'. 然.
    若 字们[0] != 65536 或 字们[1] != 8192 或 字们[2] < 1 或 字们[2] > 6 或 字们[3] > 12 或 字们[7] > 6 或 字们[8] > 1023 或 字们[9] > 4096 或 字们[10] > 10000 或 字们[11] > 2000 或 字们[14] > 12 或 字们[15] != 0 则 卒 'directory-event-header'. 然.
    若 字们[17] != 0 或 字们[19] != 0 或 字们[27] != 0 或 字们[16] > 8388608 或 字们[18] > 8388608 或 字们[26] > 268435456 则 卒 'directory-event-range'. 然.
    种 取 字们[2].
    若 字们[4] == 0 或 字们[5] == 0 或 字们[6] > 字们[10] 或 字们[12] > 24004 或 字们[13] > 字们[12] 则 卒 'directory-event-counters'. 然.
    若 (种 == 4 或 种 == 5) 且 字们[7] >= 4 则
        若 字们[6] != 0 则 卒 'directory-event-scope-counter'. 然.
    另 若 字们[6] != 字们[10] 则 卒 'directory-event-file-counter'. 然. 然.
    若 ((种 == 1 或 种 == 2 或 种 == 3) 且 字们[3] != 0) 或 ((种 == 4 或 种 == 5) 且 字们[3] == 0) 或 (种 == 6 且 字们[3] != 字们[14]) 或 (种 != 6 且 字们[14] != 0) 则 卒 'directory-event-reason'. 然.
    若 (种 == 2 且 字们[9] == 0) 或 (种 != 2 且 字们[9] != 0) 或 (种 == 1 且 字们[8] == 0) 则 卒 'directory-event-payload'. 然.
    若 (种 == 3 且 字们[7] != 1) 或 ((种 == 1 或 种 == 2 或 种 == 6) 且 字们[7] != 0) 或 (种 == 4 且 字们[7] != 0 且 字们[7] != 4) 或 (种 == 5 且 字们[7]%2 != 0) 则 卒 'directory-event-flags'. 然.
    若 种 == 1 且 字们[16] != 0 则 卒 'directory-event-start-offset'. 然.
    若 种 == 4 或 种 == 5 或 种 == 6 则
        位 取 16. 循 10 次
            若 字们[位] != 0 则 卒 'directory-event-unused-metadata'. 然.
            位 取 位+1.
        环.
    然.
    路点 取 []. 位 取 0.
    循
        若 位 >= 字们[8] 则 破. 然.
        点 取 _半 字们 位. 位 取 位+1.
        若 点 >= 55296 且 点 <= 56319 则
            若 位 >= 字们[8] 则 卒 'directory-event-path'. 然.
            低 取 _半 字们 位. 位 取 位+1.
            若 低 < 56320 或 低 > 57343 则 卒 'directory-event-path'. 然.
            点 取 65536+(点-55296)*1024+低-56320.
        然.
        若 点 == 0 或 (点 >= 56320 且 点 <= 57343) 则 卒 'directory-event-path'. 然.
        路点 其 增 点.
    环.
    若 (_半 字们 字们[8]) != 0 则 卒 'directory-event-terminator'. 然.
    位 取 字们[8].
    循 1024-位 次
        若 (_半 字们 位) != 0 则 卒 'directory-event-path-padding'. 然.
        位 取 位+1.
    环.
    位 取 (字们[9]-字们[9]%4)/4.
    若 字们[9]%4 != 0 则
        除 取 1. 循 字们[9]%4 次 除 取 除*256. 环.
        若 字们[540+位] >= 除 则 卒 'directory-event-data-padding'. 然.
        位 取 位+1.
    然.
    循 1024-位 次
        若 字们[540+位] != 0 则 卒 'directory-event-data-padding'. 然.
        位 取 位+1.
    环.
    位 取 1564.
    循 484 次
        若 字们[位] != 0 则 卒 'directory-event-padding'. 然.
        位 取 位+1.
    环.
    得 {'kind':种,'reason':字们[3],'generation':字们[4],'sequence':字们[5],'fileSequence':字们[6],'flags':字们[7],'path':(文本 路点),'length':字们[9],'files':字们[10],'dirs':字们[11],'skipped':字们[12],'errors':字们[13],'status':字们[14],'offset':字们[16],'rawSize':字们[18],'identity':((_身份 字们 20)+'/'+(_身份 字们 22)),'stamp':(_身份 字们 24),'readBytes':字们[26],'words':字们}.
法.
算 数据 事 位:
    长 取 事['length']-位. 若 长 > 512 则 长 取 512. 然.
    若 位 < 0 或 长 < 1 或 位%1 != 0 则 卒 'directory-data-cursor'. 然.
    果 取 [].
    循 长 次
        字位 取 (位-位%4)/4. 字 取 事['words'][540+字位].
        除 取 1. 循 位%4 次 除 取 除*256. 环.
        低 取 字%除. 数 取 (字-低)/除. 果 其 增 (数%256). 位 取 位+1.
    环.
    得 果.
法.
算 轮询 代:
    存 取 密 其 缓冲 8192.
    试
        码 取 (窗 其 结果 (_Poll 其 调用 [65536,代,存,8192])) 其 数.
        若 码 == 1 或 码 == 2 则 存 其 关闭. 得 空. 然.
        若 码 != 0 则 卒 'directory-poll-failed'. 然.
        字们 取 存 其 读U32LE阵 0 2048. 存 其 关闭.
        得 解事件 字们.
    救 因
        存 其 关闭. 卒 因.
    终.
法.
