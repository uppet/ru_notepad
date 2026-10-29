# Windows native acceptance uses only a unique RecentTests key, never Preferences.
密 取 外言 '如:密'.
近 取 外言 '../src/recent_files.ru'.
策 取 外言 '../src/recent_files_policy.ru'.
_K 取 密 其 系统库 'kernel32.dll'.
_R 取 密 其 系统库 'advapi32.dll'.
_PTR 取 密 其 指针.
_U 取 密 其 u32.
_I 取 密 其 i32.
_HKCU 取 _PTR 其 值 '18446744071562067969'.
_GetPid 取 _K 其 绑定 'GetCurrentProcessId' (密 其 签名 _U ([]) 'win64').
_GetTick 取 _K 其 绑定 'GetTickCount64' (密 其 签名 (密 其 uintptr) ([]) 'win64').
_Delete 取 _R 其 绑定 'RegDeleteTreeW' (密 其 签名 _I ([_PTR,_PTR]) 'win64').
_Open 取 _R 其 绑定 'RegOpenKeyExW' (密 其 签名 _I ([_PTR,_PTR,_U,_U,_PTR]) 'win64').
_Set 取 _R 其 绑定 'RegSetValueExW' (密 其 签名 _I ([_PTR,_PTR,_U,_U,_PTR,_U]) 'win64').
_Close 取 _R 其 绑定 'RegCloseKey' (密 其 签名 _I ([_PTR]) 'win64').
_柄型 取 密 其 结构 [['h',_PTR]].
_嵌零型 取 密 其 结构 [['a',(密 其 u16)],['b',(密 其 u16)],['c',(密 其 u16)],['d',(密 其 u16)]].
_坏字型 取 密 其 结构 [['a',(密 其 u16)],['b',(密 其 u16)]].
次数 取 [0].
作 确认 条件 为 事实, 文 为 句:
    若 非 条件 则 卒 'FAIL: '+文. 然
    次数[0] 取 次数[0]+1.
    显 'PASS: '+文.
为
后缀 取 'native_'+(((_GetPid 其 调用 []) 其 值) 其 句)+'_'+(((_GetTick 其 调用 []) 其 值) 其 句).
路径 取 近 其 测试路径 后缀.
路存 取 密 其 UTF16 路径.
柄存 取 _柄型 其 新建.
存在码 取 ((_Open 其 调用 [_HKCU,路存,0,1,柄存]) 其 值) 其 数.
若 存在码 == 0 则
    _Close 其 调用 [柄存 其 读 'h'].
    卒 'FAIL: refusing existing test namespace'.
然
确认 (存在码 == 2 或 存在码 == 3) 'fresh isolated registry namespace'.
柄存 其 关闭.
试
    确认 (近 其 同路径 'C:\\Dir\\FILE.txt' 'c:\\dir\\file.TXT') 'Windows ordinal case dedup'.
    确认 (非 (近 其 同路径 'C:\\straße.txt' 'C:\\strasse.txt')) 'ordinal comparison does not casefold sharp s'.
    原项们 取 [['C:\\synthetic\\0.txt',0],['C:\\synthetic\\1.txt',0],['C:\\synthetic\\2.txt',0],['C:\\synthetic\\3.txt',0],['C:\\synthetic\\4.txt',0],['C:\\synthetic\\5.txt',0],['C:\\synthetic\\6.txt',0],['C:\\synthetic\\7.txt',0],['C:\\synthetic\\8.txt',0],['C:\\synthetic\\9.txt',0]].
    项们 取 近 其 更新 原项们 'C:\\synthetic\\extra.txt' 0.
    确认 ((项们 其 量) == 10) 'history retains at most ten entries'.
    项们 取 近 其 更新 项们 'c:\\SYNTHETIC\\5.TXT' 936.
    确认 ((项们 其 量) == 10) 'duplicate does not grow history'.
    确认 (项们[0][0] == 'c:\\SYNTHETIC\\5.TXT' 且 项们[0][1] == 936) 'duplicate moves to front with current encoding'.
    确认 ((近 其 _写入 路径 项们) == 0) 'single registry snapshot saved'.
    果 取 近 其 _读取 路径.
    确认 (果['error'] == 0 且 (果['items'] 其 量) == 10) 'bounded snapshot reloads'.
    确认 (果['items'][0][0] == 项们[0][0] 且 果['items'][0][1] == 936) 'snapshot preserves path and codepage'.
    确认 ((近 其 _写入 路径 ([])) == 0) 'clear writes empty snapshot'.
    果 取 近 其 _读取 路径.
    确认 (果['error'] == 0 且 (果['items'] 其 量) == 0) 'cleared snapshot remains empty'.
    确认 ((近 其 _写入 路径 ([['relative.txt',0]])) == 0) 'write isolated relative path record'.
    果 取 近 其 _读取 路径.
    确认 ((果['items'] 其 量) == 0) 'relative record cannot depend on startup cwd'.
    # REG_SZ with an unpaired surrogate must be rejected before 解UTF16.
    柄盒 取 _柄型 其 新建.
    确认 (((_Open 其 调用 [_HKCU,路存,0,2,柄盒]) 其 值) 其 数 == 0) 'open isolated malformed-value fixture'.
    柄 取 柄盒 其 读 'h'.
    名 取 密 其 UTF16 'RecentFilesV1'.
    坏 取 _坏字型 其 新建.
    坏 其 写 'a' 55296. 坏 其 写 'b' 0.
    确认 (((_Set 其 调用 [柄,名,0,1,坏,4]) 其 值) 其 数 == 0) 'write isolated invalid surrogate'.
    坏 其 关闭.
    果 取 近 其 _读取 路径.
    确认 (果['error'] == 13 且 (果['items'] 其 量) == 0) 'invalid surrogate fails safely'.
    零 取 _嵌零型 其 新建.
    零 其 写 'a' 65. 零 其 写 'b' 0. 零 其 写 'c' 66. 零 其 写 'd' 0.
    确认 (((_Set 其 调用 [柄,名,0,1,零,8]) 其 值) 其 数 == 0) 'write isolated embedded NUL'.
    零 其 关闭.
    果 取 近 其 _读取 路径.
    确认 (果['error'] == 13 且 (果['items'] 其 量) == 0) 'embedded NUL cannot truncate history'.
    大 取 密 其 缓冲 1280514.
    确认 (((_Set 其 调用 [柄,名,0,1,大,1280514]) 其 值) 其 数 == 0) 'write isolated oversized snapshot'.
    大 其 关闭.
    果 取 近 其 _读取 路径.
    确认 (果['error'] != 0 且 (果['items'] 其 量) == 0) 'oversized registry snapshot rejected'.
    _Close 其 调用 [柄].
    柄盒 其 关闭. 名 其 关闭.
    拒 取 [假].
    试 近 其 测试路径 '../Preferences'. 救 原因 拒[0] 取 真. 终
    确认 拒[0] 'test namespace cannot escape fixed parent'.
救 原因
    _Delete 其 调用 [_HKCU,路存].
    路存 其 关闭.
    卒 原因.
终
确认 (((_Delete 其 调用 [_HKCU,路存]) 其 值) 其 数 == 0) 'isolated registry key removed'.
路存 其 关闭.
显 'TOTAL PASS: '+(次数[0] 为 句).
