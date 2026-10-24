# HKCU product preference only. One bounded REG_SZ snapshot is committed per
# update; no file associations, default apps, document contents or auto-open.
密 取 外言 '如:密'.
策 取 外言 'recent_files_policy.ru'.
件编 取 外言 'file_codec.ru'.
_PTR 取 密 其 指针.
_U 取 密 其 u32.
_I 取 密 其 i32.
_K 取 密 其 系统库 'kernel32.dll'.
_R 取 密 其 系统库 'advapi32.dll'.
_HKCU 取 _PTR 其 值 '18446744071562067969'.
_数型 取 密 其 结构 [['n',_U]].
_柄型 取 密 其 结构 [['h',_PTR]].
_Compare 取 _K 其 绑定 'CompareStringOrdinal' (密 其 签名 _I ([_PTR,_I,_PTR,_I,_I]) 'win64').
_GetEnvironment 取 _K 其 绑定 'GetEnvironmentVariableW' (密 其 签名 _U ([_PTR,_PTR,_U]) 'win64').
_Length 取 _K 其 绑定 'lstrlenW' (密 其 签名 _I ([_PTR]) 'win64').
_Validate 取 _K 其 绑定 'WideCharToMultiByte' (密 其 签名 _I ([_U,_U,_PTR,_I,_PTR,_I,_PTR,_PTR]) 'win64').
_Get 取 _R 其 绑定 'RegGetValueW' (密 其 签名 _I ([_PTR,_PTR,_PTR,_U,_PTR,_PTR,_PTR]) 'win64').
_Create 取 _R 其 绑定 'RegCreateKeyExW' (密 其 签名 _I ([_PTR,_PTR,_U,_PTR,_U,_U,_PTR,_PTR,_PTR]) 'win64').
_Set 取 _R 其 绑定 'RegSetValueExW' (密 其 签名 _I ([_PTR,_PTR,_U,_U,_PTR,_U]) 'win64').
_Close 取 _R 其 绑定 'RegCloseKey' (密 其 签名 _I ([_PTR]) 'win64').
_路径 取 'Software\\ru_notepad\\Preferences'.
_最大字节 取 1280512.
算 测试路径 后缀 为 句:
    若 后缀 == '' 或 后缀 其 量 > 64 则 卒 'Invalid recent-file test suffix.'. 然
    位 取 0.
    循 后缀 其 量 次
        若 非 ('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' 其 含 后缀[位]) 则 卒 'Invalid recent-file test suffix.'. 然
        位 取 位+1.
    环
    得 'Software\\ru_notepad\\RecentTests\\'+后缀.
法
算 同路径 左 为 句, 右 为 句:
    左存 取 密 其 UTF16 左.
    右存 取 密 其 UTF16 右.
    果 取 ((_Compare 其 调用 [左存,-1,右存,-1,1]) 其 值) 其 数.
    左存 其 关闭. 右存 其 关闭.
    若 果 == 0 则 卒 'Recent-file ordinal path comparison failed.'. 然
    得 果 == 2.
法
算 更新 项们 为 阵, 路 为 句, 编码 为 数:
    若 非 (策 其 有路径 路) 则 得 项们. 然
    果 取 [[路,(策 其 代码 编码)]].
    位 取 0.
    循 项们 其 量 次
        项 取 项们[位].
        若 (果 其 量) < 10 且 非 (同路径 项[0] 路) 则 果 其 增 项. 然
        位 取 位+1.
    环
    得 果.
法
算 _读取 路 为 句:
    路存 取 密 其 UTF16 路.
    名存 取 密 其 UTF16 'RecentFilesV1'.
    存 取 密 其 缓冲 (_最大字节+2).
    长存 取 _数型 其 新建.
    长存 其 写 'n' _最大字节.
    码 取 ((_Get 其 调用 [_HKCU,路存,名存,2,空,存,长存]) 其 值) 其 数.
    长 取 (长存 其 读 'n') 其 数.
    文 取 ''.
    # Validate length, termination and surrogate pairs BEFORE 解UTF16.
    若 码 == 0 则
        若 长 < 2 或 长 > _最大字节 或 长%2 != 0 则 码 取 13.
        另
            字数 取 长/2-1.
            若 ((_Length 其 调用 [存]) 其 值) 其 数 != 字数 则 码 取 13.
            另
                若 字数 > 0 且 (((_Validate 其 调用 [65001,128,存,字数,空,0,空,空]) 其 值) 其 数) == 0 则 码 取 13.
                另 文 取 存 其 解UTF16. 然
            然
        然
    然
    路存 其 关闭. 名存 其 关闭. 存 其 关闭. 长存 其 关闭.
    若 码 == 2 或 码 == 3 则 码 取 0. 然
    果盒 取 [[]].
    若 码 == 0 则
        项们 取 策 其 解列 文.
        位 取 (项们 其 量)-1.
        循 项们 其 量 次
            项 取 项们[位].
            # Canonical lexical resolution only: no content read, file probing
            # or automatic document open while loading history.
            试
                若 非 (策 其 有绝对路径 项[0]) 则 卒 'Relative persisted history is not trusted.'. 然
                标准 取 件编 其 绝对路径 项[0].
                果盒[0] 取 更新 果盒[0] 标准 项[1].
            救 原因
                # One invalid persisted path cannot block application startup.
            终
            位 取 位-1.
        环
    然
    得 {'items':果盒[0],'error':码}.
法
算 _写入 路 为 句, 项们 为 阵:
    文 取 策 其 编列 项们.
    路存 取 密 其 UTF16 路.
    名存 取 密 其 UTF16 'RecentFilesV1'.
    值存 取 密 其 UTF16 文.
    柄存 取 _柄型 其 新建.
    码 取 ((_Create 其 调用 [_HKCU,路存,0,空,0,2,空,柄存,空]) 其 值) 其 数.
    若 码 == 0 则
        柄 取 柄存 其 读 'h'.
        码 取 ((_Set 其 调用 [柄,名存,0,1,值存,值存 其 大小]) 其 值) 其 数.
        关码 取 ((_Close 其 调用 [柄]) 其 值) 其 数.
        若 码 == 0 则 码 取 关码. 然
    然
    路存 其 关闭. 名存 其 关闭. 值存 其 关闭. 柄存 其 关闭.
    得 码.
法
# Optional CI isolation is limited to the validated product test namespace.
# It cannot name an arbitrary registry key or alter file associations.
算 当前路径:
    名 取 密 其 UTF16 'RU_NOTEPAD_RECENT_TEST_KEY'.
    值 取 密 其 缓冲 132.
    长 取 ((_GetEnvironment 其 调用 [名,值,66]) 其 值) 其 数.
    名 其 关闭.
    若 长 == 0 则 值 其 关闭. 得 _路径. 然
    若 长 > 64 则 值 其 关闭. 卒 'Invalid recent-file test environment.'. 然
    验证 取 ((_Validate 其 调用 [65001,128,值,长,空,0,空,空]) 其 值) 其 数.
    若 验证 == 0 则 值 其 关闭. 卒 'Invalid recent-file test environment.'. 然
    后缀 取 值 其 解UTF16.
    值 其 关闭.
    得 测试路径 后缀.
法
算 载入:
    得 _读取 (当前路径).
法
算 保存 项们 为 阵:
    得 _写入 (当前路径) 项们.
法
