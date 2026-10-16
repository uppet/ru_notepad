# Bounded UTF-8 primitive scanner. Ru owns keyword configuration and all folding.
# The helper retains no pointers; buffers and snapshot copies are caller-owned.
密 取 外言 '如:密'.
窗 取 外言 'win32.ru'.
策 取 外言 'ru_lexical.ru'.
_存活数 取 [0].
_库态 取 {'ready':假,'warning':'','library':空,'config':空,'stateSize':0}.
_事件型 取 密 其 结构 [['head',密 其 u64],['tail',密 其 u64]].
_事件名 取 [].
_事件域 取 [].
_位 取 0.
循 64 次
    _名 取 'e'+(_位 为 句).
    _事件名 其 增 _名.
    _事件域 其 增 [_名,_事件型].
    _位 取 _位+1.
环
_事件批型 取 密 其 结构 _事件域.
_结果型 取 密 其 结构 [['status',窗 其 U],['consumed',窗 其 U],['styled',窗 其 U],['events',窗 其 U],['line',窗 其 U],['done',窗 其 U],['start',密 其 u64],['bytes',密 其 u64]].
_GetProcAddress 取 (窗 其 内核) 其 绑定 'GetProcAddress' (密 其 签名 (窗 其 PTR) ([(窗 其 PTR),(窗 其 PTR)]) 'win64').
算 _有导出 句柄 名 为 句:
    文 取 密 其 UTF8 名.
    址 取 窗 其 结果 (_GetProcAddress 其 调用 [句柄,文]).
    文 其 关闭.
    得 非 (址 其 为空).
法
_路径 取 (窗 其 目录)+'RuSyntax.dll'.
_路径存 取 密 其 UTF16 _路径.
_预载 取 窗 其 结果 ((窗 其 LoadLibraryExW) 其 调用 [_路径存,空,2304]).
_路径存 其 关闭.
若 _预载 其 为空 则
    _库态 其 增 'warning' 'Ru highlighting is unavailable: RuSyntax.dll could not be loaded. Extract the complete package. Your documents remain editable as plain text.'.
另
    试
        若 非 (_有导出 _预载 'ru_scan_abi') 则 卒 'RuSyntax.dll does not export the required scanner API.'. 然
        _库 取 密 其 动态库 _路径.
        _库态 其 增 'library' _库.
        _ABI 取 _库 其 绑定 'ru_scan_abi' (密 其 签名 (窗 其 U) ([]) 'win64').
        若 (窗 其 结果 (_ABI 其 调用 [])) 其 数 != 65536 则 卒 'RuSyntax.dll has an incompatible ABI version.'. 然
        _出口们 取 ['ru_scan_config_size','ru_scan_state_size','ru_scan_config_init','ru_scan_state_init','ru_scan_state_copy','ru_scan_state_equal','ru_scan_feed'].
        _位 取 0.
        循 _出口们 其 量 次
            若 非 (_有导出 _预载 _出口们[_位]) 则 卒 'RuSyntax.dll does not export the required scanner API.'. 然
            _位 取 _位+1.
        环
        _ConfigSize 取 _库 其 绑定 'ru_scan_config_size' (密 其 签名 (窗 其 U) ([]) 'win64').
        _StateSize 取 _库 其 绑定 'ru_scan_state_size' (密 其 签名 (窗 其 U) ([]) 'win64').
        _ConfigInit 取 _库 其 绑定 'ru_scan_config_init' (密 其 签名 (窗 其 U) ([(窗 其 PTR),(窗 其 U),(窗 其 PTR),(窗 其 U)]) 'win64').
        _StateInit 取 _库 其 绑定 'ru_scan_state_init' (密 其 签名 (窗 其 U) ([(窗 其 PTR),(窗 其 U)]) 'win64').
        _StateCopy 取 _库 其 绑定 'ru_scan_state_copy' (密 其 签名 (窗 其 U) ([(窗 其 PTR),(窗 其 PTR),(窗 其 U)]) 'win64').
        _StateEqual 取 _库 其 绑定 'ru_scan_state_equal' (密 其 签名 (窗 其 U) ([(窗 其 PTR),(窗 其 PTR)]) 'win64').
        _Feed 取 _库 其 绑定 'ru_scan_feed' (密 其 签名 (窗 其 U) ([(窗 其 PTR),(窗 其 PTR),(窗 其 PTR),(窗 其 U),(窗 其 U),(窗 其 U),(窗 其 PTR),(窗 其 U),(窗 其 PTR),(窗 其 U),(窗 其 PTR)]) 'win64').
        _配长 取 (窗 其 结果 (_ConfigSize 其 调用 [])) 其 数.
        _态长 取 (窗 其 结果 (_StateSize 其 调用 [])) 其 数.
        若 _配长 <= 0 或 _配长 > 65536 或 _态长 <= 0 或 _态长 > 4096 或 (_事件批型 其 大小) != 1024 或 (_结果型 其 大小) != 40 则 卒 'RuSyntax.dll has an incompatible structure size.'. 然
        _配置 取 密 其 缓冲 _配长.
        _词存 取 密 其 UTF8 (策 其 词表配置).
        _配码 取 (窗 其 结果 (_ConfigInit 其 调用 [_配置,_配长,_词存,(_词存 其 大小)-1])) 其 数.
        _词存 其 关闭.
        若 _配码 != 0 则 _配置 其 关闭. 卒 'RuSyntax.dll rejected the Ru-owned keyword configuration.'. 然
        _库态 其 增 'config' _配置.
        _库态 其 增 'stateSize' _态长.
        _库态 其 增 'ready' 真.
    救 原因
        _库态 其 增 'warning' ('Ru highlighting is unavailable: '+(原因 为 句)+' Restore RuSyntax.dll from the complete package. Your documents remain editable as plain text.').
    终
    窗 其 结果 ((窗 其 FreeLibrary) 其 调用 [_预载]).
然
算 初始化:
    得 _库态['warning'].
法
算 可用:
    得 _库态['ready'].
法
算 _容器 存 折态:
    # Work buffers are lazy and never copied into a lexical checkpoint.
    _存活数[0] 取 _存活数[0]+1.
    得 {'references':1,'processed':0,'received':0,'line':0,'native':存,'policy':折态,'input':空,'inputLength':0,'offset':0,'eof':假,'styles':空,'events':空,'result':空}.
法
算 新状态:
    若 非 _库态['ready'] 则 卒 _库态['warning']. 然
    存 取 密 其 缓冲 _库态['stateSize'].
    若 (窗 其 结果 (_StateInit 其 调用 [存,_库态['stateSize']])) 其 数 != 0 则 存 其 关闭. 卒 'The Ru scanner could not initialize its bounded state.'. 然
    得 _容器 存 (策 其 新状态).
法
算 复制状态 态:
    存 取 密 其 缓冲 _库态['stateSize'].
    若 (窗 其 结果 (_StateCopy 其 调用 [存,态['native'],_库态['stateSize']])) 其 数 != 0 则 存 其 关闭. 卒 'The Ru scanner could not copy a checkpoint.'. 然
    副本 取 _容器 存 (策 其 复制状态 态['policy']).
    副本 其 增 'processed' 态['processed'].
    副本 其 增 'received' 态['received'].
    副本 其 增 'line' 态['line'].
    得 副本.
法
# Explicit root ownership, including shared immutable suffix checkpoints.
算 保留 态:
    若 态 == 空 或 态['references'] <= 0 则 卒 'Cannot retain a released Ru scanner checkpoint.'. 然
    态 其 增 'references' (态['references']+1).
    得 空.
法
算 释放 态:
    若 态 == 空 或 态['references'] <= 0 则 得 空. 然
    数量 取 态['references']-1.
    态 其 增 'references' 数量.
    若 数量 == 0 则
        _存活数[0] 取 _存活数[0]-1.
        键们 取 ['native','input','styles','events','result'].
        位 取 0.
        循 键们 其 量 次
            存 取 态[键们[位]].
            若 存 != 空 则 存 其 关闭. 态 其 增 键们[位] 空. 然
            位 取 位+1.
        环
        态 其 增 'policy' 空.
    然
    得 空.
法
算 存活上下文:
    得 _存活数[0].
法
算 等价 左 右:
    若 (窗 其 结果 (_StateEqual 其 调用 [左['native'],右['native']])) 其 数 != 1 则 得 假. 然
    得 策 其 等价 左['policy'] 右['policy'].
法
算 _头数 头:
    # Styling is capped below 32 MB, hence metadata+start occupies at most49bits.
    # Never convert the full u64. Checked low49 is an exact Ru integer.
    若 (头 其 位段 49 15) != 0 则 卒 'Ru scanner returned oversized event head bits.'. 然
    得 头 其 位段 0 49.
法
算 _解事件 存 项数 为 数 始 为 数 字节 为 数 行 为 数:
    # One detached little-endian snapshot of the existing 1024-byte event ABI.
    # Reject bits49..63 before combining two exact u32 words into a <2^49 head.
    若 项数 < 0 或 项数 > 64 或 项数 % 1 != 0 则 卒 'Ru scanner returned an invalid batch size.'. 然
    事件们 取 [].
    字们 取 存 其 读U32LE阵 0 (项数*4).
    项位 取 0.
    字位 取 0.
    循 项数 次
        高 取 字们[字位+1].
        若 高 >= 131072 则 卒 'Ru scanner returned oversized event head bits.'. 然
        头数 取 字们[字位]+高*4294967296.
        元码 取 头数 % 16777216.
        项始 取 (头数-元码)/16777216.
        种 取 元码 % 256.
        码色 取 (元码-种)/256.
        码 取 码色 % 256.
        色 取 (码色-码)/256.
        项长 取 字们[字位+2].
        项行 取 字们[字位+3].
        若 种 < 1 或 种 > 7 或 色 > 9 或 项长 == 0 或 项始+项长 > 字节 或 项行 > 行 或 (种 != 1 且 项始 < 始) 或 (种 == 1 且 色 != 8 且 项长 > 64) 则 卒 'Ru scanner returned an invalid lexical event.'. 然
        若 项位 > 0 且 项始 < 事件们[项位-1][3] 则 卒 'Ru scanner returned unordered lexical events.'. 然
        事件们 其 增 [种,码,色,项始,项长,项行].
        项位 取 项位+1.
        字位 取 字位+4.
    环
    得 事件们.
法
算 扫描 态 文 为 句 结束 为 事实 上限 为 数:
    若 态['references'] <= 0 则 卒 'Cannot resume a released Ru scanner checkpoint.'. 然
    若 态['input'] == 空 或 态['offset'] >= 态['inputLength'] 则
        若 态['input'] != 空 则 (态['input']) 其 关闭. 然
        存 取 密 其 UTF8 文.
        长 取 (存 其 大小)-1.
        若 长 > 1024 则 存 其 关闭. 卒 'Ru scanner input exceeds the bounded editor window.'. 然
        态 其 增 'input' 存.
        态 其 增 'inputLength' 长.
        态 其 增 'offset' 0.
        态 其 增 'eof' 结束.
    另
        若 文 != '' 则 卒 'Ru scanner still owns unconsumed input.'. 然
    然
    若 态['styles'] == 空 则
        态 其 增 'styles' (密 其 缓冲 1040).
        态 其 增 'events' (_事件批型 其 新建).
        态 其 增 'result' (_结果型 其 新建).
    然
    长 取 态['inputLength'].
    位 取 态['offset'].
    若 上限 >= 0 且 位+上限 < 长 则 长 取 位+上限. 然
    末标 取 0.
    若 态['eof'] 且 长 == 态['inputLength'] 则 末标 取 1. 然
    码 取 (窗 其 结果 (_Feed 其 调用 [_库态['config'],态['native'],态['input'],长,位,末标,态['styles'],1040,态['events'],64,态['result']])) 其 数.
    果 取 态['result'].
    已取 取 (果 其 读 'consumed') 其 数.
    已色 取 (果 其 读 'styled') 其 数.
    项数 取 (果 其 读 'events') 其 数.
    已毕 取 (果 其 读 'done') 其 数.
    若 (码 != 0 且 码 != 1) 或 (果 其 读 'status') 其 数 != 码 则 卒 ('Ru UTF-8 scanner rejected a batch (status '+(码 为 句)+').'). 然
    若 已取 > 长-位 或 已色 > 1040 或 项数 > 64 或 已毕 > 1 则 卒 'Ru scanner returned an invalid batch size.'. 然
    若 已取 == 0 且 已色 == 0 且 项数 == 0 且 已毕 == 0 则 卒 'Ru scanner made no progress.'. 然
    始值 取 果 其 读 'start'.
    末值 取 果 其 读 'bytes'.
    若 (始值 其 位段 32 32) != 0 或 (末值 其 位段 32 32) != 0 则 卒 'Ru scanner byte coordinates exceed the bounded document range.'. 然
    始 取 始值 其 位段 0 32.
    字节 取 末值 其 位段 0 32.
    行 取 (果 其 读 'line') 其 数.
    收到 取 态['received']+已取.
    若 始 != 态['processed'] 或 始+已色 != 字节 或 字节 > 收到 或 收到-字节 > 16 或 收到 > 32000000 或 行 < 态['line'] 或 行 > 字节 或 (已毕 == 1 且 (末标 != 1 或 位+已取 != 长 或 字节 != 收到)) 则 卒 'Ru scanner returned inconsistent byte or line coordinates.'. 然
    态 其 增 'offset' (位+已取).
    事件们 取 _解事件 态['events'] 项数 始 字节 行.
    态 其 增 'processed' 字节.
    态 其 增 'received' 收到.
    态 其 增 'line' 行.
    成果 取 策 其 批处理 态['policy'] 事件们 字节 行 (已毕 == 1).
    成果 其 增 'styleBuffer' 态['styles'].
    成果 其 增 'styleStart' 始.
    成果 其 增 'styleLength' 已色.
    成果 其 增 'consumed' 已取.
    成果 其 增 'done' (已毕 == 1).
    得 成果.
法
