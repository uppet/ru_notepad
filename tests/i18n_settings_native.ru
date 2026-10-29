# Actual Windows registry tests. Only this process's isolated I18nTests key is used.
# Never call production preference wrappers or read/write the Preferences key.
密 取 外言 '如:密'.
设 取 外言 '../src/i18n_settings.ru'.
本地 取 外言 '../src/i18n.ru'.
_PTR 取 密 其 指针.
_U 取 密 其 u32.
_I 取 密 其 i32.
_内核 取 密 其 系统库 'kernel32.dll'.
_注册 取 密 其 系统库 'advapi32.dll'.
_HKCU 取 _PTR 其 值 '18446744071562067969'.
_柄型 取 密 其 结构 [['h',_PTR]].
_双型 取 密 其 结构 [['a',(密 其 u16)],['b',(密 其 u16)]].
_三型 取 密 其 结构 [['a',(密 其 u16)],['b',(密 其 u16)],['c',(密 其 u16)]].
_六型 取 密 其 结构 [['a',(密 其 u16)],['b',(密 其 u16)],['c',(密 其 u16)],['d',(密 其 u16)],['e',(密 其 u16)],['f',(密 其 u16)]].
_GetCurrentProcessId 取 _内核 其 绑定 'GetCurrentProcessId' (密 其 签名 _U ([]) 'win64').
_GetTickCount64 取 _内核 其 绑定 'GetTickCount64' (密 其 签名 (密 其 uintptr) ([]) 'win64').
_RegOpenKeyExW 取 _注册 其 绑定 'RegOpenKeyExW' (密 其 签名 _I ([_PTR,_PTR,_U,_U,_PTR]) 'win64').
_RegSetValueExW 取 _注册 其 绑定 'RegSetValueExW' (密 其 签名 _I ([_PTR,_PTR,_U,_U,_PTR,_U]) 'win64').
_RegCloseKey 取 _注册 其 绑定 'RegCloseKey' (密 其 签名 _I ([_PTR]) 'win64').
_RegDeleteTreeW 取 _注册 其 绑定 'RegDeleteTreeW' (密 其 签名 _I ([_PTR,_PTR]) 'win64').
次数 取 [0].
作 确认 条件 为 事实 文 为 句:
    若 非 条件 则 卒 'FAIL: '+文. 然
    次数[0] 取 次数[0]+1.
    显 'PASS: '+文.
为
作 应拒路径 后缀 为 句 文 为 句:
    拒 取 [假].
    试 设 其 测试路径 后缀. 救 原因 拒[0] 取 真. 终
    确认 拒[0] 文.
为
# Every helper resolves its path through the production isolated test validator.
算 存在 后缀 为 句:
    路 取 密 其 UTF16 (设 其 测试路径 后缀).
    盒 取 _柄型 其 新建.
    码 取 ((_RegOpenKeyExW 其 调用 [_HKCU,路,0,1,盒]) 其 值) 其 数.
    路 其 关闭.
    柄 取 盒 其 读 'h'.
    盒 其 关闭.
    若 码 == 2 或 码 == 3 则 得 假. 然
    若 码 != 0 则 卒 'isolated i18n key query failed: '+(码 为 句). 然
    关码 取 ((_RegCloseKey 其 调用 [柄]) 其 值) 其 数.
    若 关码 != 0 则 卒 'isolated i18n key close failed: '+(关码 为 句). 然
    得 真.
法
作 清理 后缀 为 句:
    路 取 密 其 UTF16 (设 其 测试路径 后缀).
    码 取 ((_RegDeleteTreeW 其 调用 [_HKCU,路]) 其 值) 其 数.
    路 其 关闭.
    若 码 != 0 且 码 != 2 且 码 != 3 则 卒 'isolated i18n cleanup failed: '+(码 为 句). 然
为
作 原始写 后缀 为 句 型 为 数 存 长 为 数:
    路 取 密 其 UTF16 (设 其 测试路径 后缀).
    名 取 密 其 UTF16 'InterfaceLanguage'.
    盒 取 _柄型 其 新建.
    码 取 ((_RegOpenKeyExW 其 调用 [_HKCU,路,0,2,盒]) 其 值) 其 数.
    路 其 关闭.
    柄 取 盒 其 读 'h'.
    盒 其 关闭.
    若 码 != 0 则 名 其 关闭. 卒 'isolated i18n fixture open failed: '+(码 为 句). 然
    码 取 ((_RegSetValueExW 其 调用 [柄,名,0,型,存,长]) 其 值) 其 数.
    名 其 关闭.
    关码 取 ((_RegCloseKey 其 调用 [柄]) 其 值) 其 数.
    若 码 != 0 则 卒 'isolated i18n fixture write failed: '+(码 为 句). 然
    若 关码 != 0 则 卒 'isolated i18n fixture close failed: '+(关码 为 句). 然
为
作 查无效 路 为 句 文 为 句:
    果 取 设 其 _读取 路.
    确认 (果['error'] == 0) (文+' remains a readable REG_SZ without fatal decoding').
    确认 (果['value'] == 'invalid') (文+' is rejected as a noncanonical token').
    确认 ((设 其 决定 果['value'] 'ja') == 'en') (文+' falls back to English rather than the system language').
为
作 检验 后缀 为 句:
    路 取 设 其 测试路径 后缀.
    确认 (非 (存在 后缀)) 'isolated i18n key initially does not exist'.
    缺 取 设 其 _读取 路.
    确认 (缺['error'] == 0) 'missing preference is not a registry error'.
    确认 (缺['value'] == '') 'missing preference returns an empty value'.
    确认 ((设 其 决定 缺['value'] 'ja') == 'ja') 'missing preference follows the supplied system language'.
    确认 (非 (存在 后缀)) 'reading a missing preference does not create a key'.
    语言们 取 ['en','zh-CN','ja','ko','es','ru','it'].
    位 取 0.
    循 语言们 其 量 次
        语言 取 语言们[位].
        确认 ((设 其 _写入 路 语言) == 0) ('write canonical preference '+语言).
        果 取 设 其 _读取 路.
        确认 (果['error'] == 0) ('read canonical preference without error '+语言).
        确认 (果['value'] == 语言) ('round-trip exact canonical preference '+语言).
        确认 ((设 其 决定 果['value'] 'en') == 语言) ('explicit preference overrides the supplied system language '+语言).
        位 取 位+1.
    环
    确认 ((设 其 _写入 路 'system') == 0) 'write system preference'.
    果 取 设 其 _读取 路.
    确认 (果['error'] == 0) 'read system preference without error'.
    确认 (果['value'] == 'system') 'system preference round-trips exactly'.
    确认 ((设 其 决定 果['value'] 'ko') == 'ko') 'system preference resolves to the supplied system language'.
    确认 ((设 其 _写入 路 'de') == 87) 'unsupported preference write returns ERROR_INVALID_PARAMETER'.
    确认 ((设 其 _读取 路)['value'] == 'system') 'unsupported preference write preserves the previous value'.
    确认 ((设 其 _写入 路 '') == 87) 'empty preference write returns ERROR_INVALID_PARAMETER'.
    确认 ((设 其 _读取 路)['value'] == 'system') 'empty preference write preserves the previous value'.
    # Allocate all malformed fixture buffers inside one cleanup holder.
    内存们 取 [].
    试
        未知 取 密 其 UTF16 'de'.
        内存们 其 增 未知.
        原始写 后缀 1 未知 (未知 其 大小).
        查无效 路 'unknown stored language'.
        双 取 _双型 其 新建.
        内存们 其 增 双.
        双 其 写 'a' 101. 双 其 写 'b' 110.
        原始写 后缀 4 双 (双 其 大小).
        果 取 设 其 _读取 路.
        确认 (果['error'] != 0) 'REG_DWORD preference preserves a nonzero Windows type error'.
        确认 (果['value'] == '') 'REG_DWORD preference does not become a language token'.
        原始写 后缀 3 未知 (未知 其 大小).
        果 取 设 其 _读取 路.
        确认 (果['error'] != 0) 'REG_BINARY preference preserves a nonzero Windows type error'.
        确认 (果['value'] == '') 'REG_BINARY preference does not become a language token'.
        六 取 _六型 其 新建.
        内存们 其 增 六.
        六 其 写 'a' 101. 六 其 写 'b' 110. 六 其 写 'c' 0.
        六 其 写 'd' 106. 六 其 写 'e' 97. 六 其 写 'f' 0.
        原始写 后缀 1 六 (六 其 大小).
        查无效 路 'embedded-NUL language followed by another token'.
        三 取 _三型 其 新建.
        内存们 其 增 三.
        三 其 写 'a' 55296. 三 其 写 'b' 110. 三 其 写 'c' 0.
        原始写 后缀 1 三 (三 其 大小).
        查无效 路 'unpaired high-surrogate UTF-16'.
        三 其 写 'a' 101. 三 其 写 'b' 56320. 三 其 写 'c' 0.
        原始写 后缀 1 三 (三 其 大小).
        查无效 路 'unpaired low-surrogate UTF-16'.
        空文 取 密 其 UTF16 ''.
        内存们 其 增 空文.
        原始写 后缀 1 空文 (空文 其 大小).
        查无效 路 'empty stored REG_SZ'.
        长文 取 密 其 UTF16 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'.
        内存们 其 增 长文.
        原始写 后缀 1 长文 (长文 其 大小).
        果 取 设 其 _读取 路.
        确认 (果['error'] != 0) 'oversized registry preference retains a bounded-read error'.
        确认 (果['value'] == '') 'oversized registry preference cannot be truncated into a language token'.
    救 原因
        位 取 0.
        循 内存们 其 量 次 内存们[位] 其 关闭. 位 取 位+1. 环
        卒 原因.
    终
    位 取 0.
    循 内存们 其 量 次 内存们[位] 其 关闭. 位 取 位+1. 环
    确认 ((设 其 _写入 路 'zh-CN') == 0) 'valid preference can replace malformed registry data'.
    果 取 设 其 _读取 路.
    确认 (果['error'] == 0 且 果['value'] == 'zh-CN') 'repaired preference reads back without a fatal decoder path'.
    应拒路径 '' 'empty test suffix is rejected'.
    应拒路径 '..\\Preferences' 'test suffix cannot escape into production preferences'.
    应拒路径 'nested\\key' 'nested test suffix is rejected'.
    应拒路径 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abc' 'overlong test suffix is rejected'.
为
算 元初 参数 为 句 阵:
    号 取 ((_GetCurrentProcessId 其 调用 []) 其 值) 其 句.
    时 取 ((_GetTickCount64 其 调用 []) 其 值) 其 句.
    后缀 取 号+'_'+时.
    # Refuse to touch an existing key, including cleanup, before ownership begins.
    若 存在 后缀 则 卒 'isolated i18n fixture already exists; not touching it'. 然
    试 检验 后缀. 救 原因 清理 后缀. 卒 原因. 终
    清理 后缀.
    确认 (非 (存在 后缀)) 'exact isolated I18nTests subtree is fully removed'.
    若 次数[0] != 69 则 卒 'FAIL: unexpected i18n settings assertion count'. 然
    显 'TOTAL PASS: '+(次数[0] 为 句).
    得 0.
法
