# Shared fixed native fixture utilities; no codec import, counters or entry point.
# Both full streaming suites retain their own native descriptors and assertions.
密 取 外言 '如:密'.
U8 取 密 其 u8.
U32 取 密 其 u32.
I32 取 密 其 i32.
I64 取 密 其 i64.
PTR 取 密 其 指针.
系统 取 密 其 系统库 'kernel32.dll'.
Open 取 系统 其 绑定 'CreateFileW' (密 其 签名 PTR ([PTR,U32,U32,PTR,U32,U32,PTR]) 'win64').
Close 取 系统 其 绑定 'CloseHandle' (密 其 签名 I32 ([PTR]) 'win64').
Write 取 系统 其 绑定 'WriteFile' (密 其 签名 I32 ([PTR,PTR,U32,PTR,PTR]) 'win64').
Delete 取 系统 其 绑定 'DeleteFileW' (密 其 签名 I32 ([PTR]) 'win64').
SetPointer 取 系统 其 绑定 'SetFilePointerEx' (密 其 签名 I32 ([PTR,I64,PTR,U32]) 'win64').
SetEnd 取 系统 其 绑定 'SetEndOfFile' (密 其 签名 I32 ([PTR]) 'win64').
DeviceControl 取 系统 其 绑定 'DeviceIoControl' (密 其 签名 I32 ([PTR,U32,PTR,U32,PTR,U32,PTR,PTR]) 'win64').
计数型 取 密 其 结构 [['n',U32]].

作 必须成功 成果 名称 为 句:
    若 (成果 其 值) 其 为空 则 卒 名称 + ' Win32=' + (成果 其 错误码 为 句). 然
为

算 打开 路径 为 句 访问 为 数 模式 为 数:
    路存 取 密 其 UTF16 路径.
    成果 取 Open 其 调用 [路存,访问,1,空,模式,128,空].
    路存 其 关闭.
    句柄 取 成果 其 值.
    若 句柄 其 句 == '18446744073709551615' 则 卒 'fixture open failed: ' + (成果 其 错误码 为 句). 然
    得 句柄.
法

算 重复 文 为 句 倍数 为 数:
    结果 取 ''.
    块 取 文.
    余 取 倍数.
    循
        若 余 == 0 则 破. 然
        若 余 % 2 == 1 则 结果 取 结果 + 块. 然
        余 取 (余 - 余 % 2) / 2.
        若 余 > 0 则 块 取 块 + 块. 然
    环
    得 结果.
法

算 字节结构 字节们 为 阵:
    字段 取 [].
    位 取 0.
    循 字节们 其 量 次
        字段 其 增 [('b' + (位 为 句)),U8].
        位 取 位 + 1.
    环
    若 字节们 其 量 == 0 则 字段 其 增 ['empty',U8]. 然
    布局 取 密 其 结构 字段.
    内存 取 布局 其 新建.
    位 取 0.
    循 字节们 其 量 次
        内存 其 写 ('b' + (位 为 句)) 字节们[位].
        位 取 位 + 1.
    环
    得 内存.
法

作 稀疏文件 路径 为 句 长 为 数:
    句柄 取 打开 路径 1073741824 2.
    数存 取 计数型 其 新建.
    成果 取 DeviceControl 其 调用 [句柄,590020,空,0,空,0,数存,空].
    必须成功 成果 'FSCTL_SET_SPARSE (test folder must support sparse files)'.
    数据 取 密 其 UTF8 (重复 'a' 16384).
    循 4 次
        成果 取 Write 其 调用 [句柄,数据,16384,数存,空].
        必须成功 成果 'sparse prefix write'.
        若 (数存 其 读 'n') 其 数 != 16384 则 卒 'short sparse prefix'. 然
    环
    成果 取 SetPointer 其 调用 [句柄,长,空,0].
    必须成功 成果 'sparse seek'.
    成果 取 SetEnd 其 调用 [句柄].
    必须成功 成果 'sparse extend'.
    Close 其 调用 [句柄].
    数存 其 关闭.
    数据 其 关闭.
为
