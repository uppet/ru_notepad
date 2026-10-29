# Per-user UI preference only. No file associations, defaults or credentials.
# Missing preference follows Windows UI language; unknown saved codes use English.
密 取 外言 '如:密'.
本地 取 外言 'i18n.ru'.
_PTR 取 密 其 指针.
_U 取 密 其 u32.
_I 取 密 其 i32.
_内核 取 密 其 系统库 'kernel32.dll'.
_注册 取 密 其 系统库 'advapi32.dll'.
_HKCU 取 _PTR 其 值 '18446744071562067969'.
_数型 取 密 其 结构 [['n',_U]].
_柄型 取 密 其 结构 [['h',_PTR]].
_GetUserDefaultUILanguage 取 _内核 其 绑定 'GetUserDefaultUILanguage' (密 其 签名 (密 其 u16) ([]) 'win64').
_CompareStringOrdinal 取 _内核 其 绑定 'CompareStringOrdinal' (密 其 签名 _I ([_PTR,_I,_PTR,_I,_I]) 'win64').
_RegGetValueW 取 _注册 其 绑定 'RegGetValueW' (密 其 签名 _I ([_PTR,_PTR,_PTR,_U,_PTR,_PTR,_PTR]) 'win64').
_RegCreateKeyExW 取 _注册 其 绑定 'RegCreateKeyExW' (密 其 签名 _I ([_PTR,_PTR,_U,_PTR,_U,_U,_PTR,_PTR,_PTR]) 'win64').
_RegSetValueExW 取 _注册 其 绑定 'RegSetValueExW' (密 其 签名 _I ([_PTR,_PTR,_U,_U,_PTR,_U]) 'win64').
_RegCloseKey 取 _注册 其 绑定 'RegCloseKey' (密 其 签名 _I ([_PTR]) 'win64').
_路径 取 'Software\\ru_notepad\\Preferences'.
算 系统语言:
    得 本地 其 系统选择 (((_GetUserDefaultUILanguage 其 调用 []) 其 值) 其 数).
法
算 决定 保存 为 句, 系统 为 句:
    若 保存 == '' 或 保存 == 'system' 则 得 系统. 然
    若 本地 其 有语言 保存 则 得 保存. 然
    得 'en'.
法
# The optional test route is deliberately restricted to an isolated namespace.
算 测试路径 后缀 为 句:
    若 后缀 == '' 或 (后缀 其 量) > 64 则 卒 'Invalid i18n test suffix.'. 然
    位 取 0.
    循 后缀 其 量 次
        若 非 ('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' 其 含 后缀[位]) 则 卒 'Invalid i18n test suffix.'. 然
        位 取 位+1.
    环
    得 'Software\\ru_notepad\\I18nTests\\'+后缀.
法
算 _读取 路 为 句:
    路存 取 密 其 UTF16 路.
    名存 取 密 其 UTF16 'InterfaceLanguage'.
    存 取 密 其 缓冲 64.
    长存 取 _数型 其 新建.
    长存 其 写 'n' 64.
    码 取 ((_RegGetValueW 其 调用 [_HKCU,路存,名存,2,空,存,长存]) 其 值) 其 数.
    长 取 (长存 其 读 'n') 其 数.
    值 取 ''.
    # Compare a bounded canonical UTF-16 token. Do not decode untrusted registry
    # text through the runtime's fatal invalid-surrogate path.
    若 码 == 0 则
        值 取 'invalid'.
        候选们 取 ['system','en','zh-CN','ja','ko','es','ru','it'].
        位 取 0.
        循 候选们 其 量 次
            候选存 取 密 其 UTF16 候选们[位].
            若 长 == (候选存 其 大小) 且 (((_CompareStringOrdinal 其 调用 [存,长/2,候选存,长/2,0]) 其 值) 其 数) == 2 则 值 取 候选们[位]. 然
            候选存 其 关闭.
            位 取 位+1.
        环
    然
    路存 其 关闭.
    名存 其 关闭.
    存 其 关闭.
    长存 其 关闭.
    若 码 == 2 或 码 == 3 则 码 取 0. 然
    得 {'value':值,'error':码}.
法
算 _写入 路 为 句, 代码 为 句:
    若 代码 != 'system' 且 非 (本地 其 有语言 代码) 则 得 87. 然
    路存 取 密 其 UTF16 路.
    名存 取 密 其 UTF16 'InterfaceLanguage'.
    值存 取 密 其 UTF16 代码.
    柄存 取 _柄型 其 新建.
    码 取 ((_RegCreateKeyExW 其 调用 [_HKCU,路存,0,空,0,2,空,柄存,空]) 其 值) 其 数.
    若 码 == 0 则
        柄 取 柄存 其 读 'h'.
        码 取 ((_RegSetValueExW 其 调用 [柄,名存,0,1,值存,值存 其 大小]) 其 值) 其 数.
        关码 取 ((_RegCloseKey 其 调用 [柄]) 其 值) 其 数.
        若 码 == 0 则 码 取 关码. 然
    然
    路存 其 关闭.
    名存 其 关闭.
    值存 其 关闭.
    柄存 其 关闭.
    得 码.
法
算 载入偏好:
    得 _读取 _路径.
法
算 保存偏好 代码 为 句:
    得 _写入 _路径 代码.
法
