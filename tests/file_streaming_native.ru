# Native Windows streaming integration tests. Pass an existing disposable folder.
# All data buffers and text producers are bounded; no whole large-file string exists.
# Every fixture is prefixed ru-stream-test-. No external tools or codec DLLs needed.
文件库 取 外言 '../src/file_codec.ru'.
密 取 外言 '如:密'.
U8 取 密 其 u8.
U32 取 密 其 u32.
I32 取 密 其 i32.
I64 取 密 其 i64.
UPTR 取 密 其 uintptr.
PTR 取 密 其 指针.
系统 取 密 其 系统库 'kernel32.dll'.
内核 取 密 其 系统库 'ntdll.dll'.
Open 取 系统 其 绑定 'CreateFileW' (密 其 签名 PTR ([PTR,U32,U32,PTR,U32,U32,PTR]) 'win64').
Close 取 系统 其 绑定 'CloseHandle' (密 其 签名 I32 ([PTR]) 'win64').
Read 取 系统 其 绑定 'ReadFile' (密 其 签名 I32 ([PTR,PTR,U32,PTR,PTR]) 'win64').
Write 取 系统 其 绑定 'WriteFile' (密 其 签名 I32 ([PTR,PTR,U32,PTR,PTR]) 'win64').
Delete 取 系统 其 绑定 'DeleteFileW' (密 其 签名 I32 ([PTR]) 'win64').
Size 取 系统 其 绑定 'GetFileSizeEx' (密 其 签名 I32 ([PTR,PTR]) 'win64').
SetPointer 取 系统 其 绑定 'SetFilePointerEx' (密 其 签名 I32 ([PTR,I64,PTR,U32]) 'win64').
SetEnd 取 系统 其 绑定 'SetEndOfFile' (密 其 签名 I32 ([PTR]) 'win64').
DeviceControl 取 系统 其 绑定 'DeviceIoControl' (密 其 签名 I32 ([PTR,U32,PTR,U32,PTR,U32,PTR,PTR]) 'win64').
Compare 取 内核 其 绑定 'RtlCompareMemory' (密 其 签名 UPTR ([PTR,PTR,UPTR]) 'win64').
计数型 取 密 其 结构 [['n',U32]].
大小型 取 密 其 结构 [['n',I64]].
统计 取 [0].

作 断言 条件 为 事实 名称 为 句:
    若 非 条件 则 卒 'FAIL: ' + 名称. 然
    统计[0] 取 统计[0] + 1.
    显 'PASS: ' + 名称.
为

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

算 文段 文 为 句 次数 为 数:
    得 {'text':文,'repeat':次数}.
法

算 原段 内存 长 为 数 次数 为 数:
    得 {'data':内存,'bytes':长,'repeat':次数}.
法

算 新生产 段们 为 阵:
    状态 取 [0,0].
    得 算:
        循
            若 状态[0] >= 段们 其 量 则 得 空. 然
            段 取 段们[状态[0]].
            若 状态[1] < 段['repeat'] 则
                状态[1] 取 状态[1] + 1.
                得 段['text'].
            然
            状态[0] 取 状态[0] + 1.
            状态[1] 取 0.
        环
    法.
法

算 新接收 段们 为 阵 记录:
    状态 取 [0,0,0].
    得 算 文 为 句:
        若 文 其 量 > 65536 则 卒 'unbounded decoded chunk'. 然
        记录 其 增 'calls' (记录['calls'] + 1).
        记录 其 增 'chars' (记录['chars'] + 文 其 量).
        位 取 0.
        循
            若 位 >= 文 其 量 则 破. 然
            循
                若 状态[0] >= 段们 其 量 则 卒 'unexpected trailing decoded text'. 然
                段 取 段们[状态[0]].
                若 状态[1] < 段['repeat'] 则 破. 然
                状态[0] 取 状态[0] + 1.
                状态[1] 取 0.
            环
            预期 取 段们[状态[0]]['text'].
            长 取 预期 其 量 - 状态[2].
            若 长 > 文 其 量 - 位 则 长 取 文 其 量 - 位. 然
            若 文[位:位 + 长] != 预期[状态[2]:状态[2] + 长] 则 卒 'decoded chunk text differs'. 然
            位 取 位 + 长.
            状态[2] 取 状态[2] + 长.
            若 状态[2] == 预期 其 量 则
                状态[2] 取 0.
                状态[1] 取 状态[1] + 1.
            然
        环
        得 空.
    法.
法

# This independent raw reader compares every byte with bounded expected buffers.
# Expected UTF-8 / UTF-16LE buffers use the runtime encoder, not the file codec.
作 验原生段 路径 为 句 段们 为 阵 名称 为 句:
    句柄 取 打开 路径 2147483648 3.
    长存 取 大小型 其 新建.
    数存 取 计数型 其 新建.
    数据 取 密 其 缓冲 65536.
    成果 取 Size 其 调用 [句柄,长存].
    必须成功 成果 'fixture size'.
    预期长 取 0.
    相同 取 真.
    位 取 0.
    循 段们 其 量 次
        段 取 段们[位].
        长 取 段['bytes'].
        若 长 > 65536 则 卒 'test expected buffer exceeds bound'. 然
        预期长 取 预期长 + 长 * 段['repeat'].
        循 段['repeat'] 次
            若 长 > 0 则
                成果 取 Read 其 调用 [句柄,数据,长,数存,空].
                必须成功 成果 'independent raw read'.
                若 (数存 其 读 'n') 其 数 != 长 则 相同 取 假. 然
                比较 取 Compare 其 调用 [数据,段['data'],长].
                若 (比较 其 值) 其 数 != 长 则 相同 取 假. 然
            然
        环
        位 取 位 + 1.
    环
    相同 取 相同 且 (长存 其 读 'n') 其 数 == 预期长.
    成果 取 Read 其 调用 [句柄,数据,1,数存,空].
    必须成功 成果 'independent EOF read'.
    相同 取 相同 且 (数存 其 读 'n') 其 数 == 0.
    Close 其 调用 [句柄].
    长存 其 关闭.
    数存 其 关闭.
    数据 其 关闭.
    断言 相同 名称.
为

作 写原生段 路径 为 句 段们 为 阵:
    句柄 取 打开 路径 1073741824 2.
    数存 取 计数型 其 新建.
    位 取 0.
    循 段们 其 量 次
        段 取 段们[位].
        循 段['repeat'] 次
            成果 取 Write 其 调用 [句柄,段['data'],段['bytes'],数存,空].
            必须成功 成果 'fixture write'.
            若 (数存 其 读 'n') 其 数 != 段['bytes'] 则 卒 'short fixture write'. 然
        环
        位 取 位 + 1.
    环
    Close 其 调用 [句柄].
    数存 其 关闭.
为

作 应失败 工作 为 算 名称 为 句:
    失败 取 [假].
    试
        工作().
    救 原因
        失败[0] 取 真.
        显 '  rejected: ' + 原因.
    终
    断言 失败[0] 名称.
为

算 不询问 长 为 数:
    卒 'unexpected large-file prompt'.
法

算 忽略 文 为 句:
    得 空.
法

作 验流文 路径 为 句 段们 为 阵 编码 为 数 BOM 为 事实 字节数 为 数 戳 为 句 名称 为 句:
    记录 取 {'calls':0,'chars':0}.
    接收 取 新接收 段们 记录.
    代码页 取 编码.
    若 BOM 或 编码 == 65001 则 代码页 取 0. 然
    结果 取 文件库 其 流读文件 路径 代码页 (算 不询问) 接收.
    预期字数 取 0.
    预期UTF8 取 0.
    位 取 0.
    循 段们 其 量 次
        预期字数 取 预期字数 + (段们[位]['text'] 其 量) * 段们[位]['repeat'].
        文存 取 密 其 UTF8 段们[位]['text'].
        预期UTF8 取 预期UTF8 + (文存 其 大小 - 1) * 段们[位]['repeat'].
        文存 其 关闭.
        位 取 位 + 1.
    环
    断言 (记录['chars'] == 预期字数) (名称 + ': exact decoded text').
    断言 (结果['bytes'] == 字节数 且 结果['textBytes'] == 预期UTF8 且 结果['encoding'] == 编码 且 结果['bom'] == BOM) (名称 + ': source / decoded byte counts and encoding metadata').
    断言 (结果['stamp'] == 戳 且 结果['path'] == (文件库 其 绝对路径 路径)) (名称 + ': identity metadata').
    若 字节数 > 65536 则
        断言 (记录['calls'] > 1 且 结果['readCalls'] > 1) (名称 + ': multiple bounded reads').
    然
为

作 大文件往返 路径 为 句 编码 为 数 BOM 为 事实 次数 为 数 名称 为 句:
    模式 取 重复 'A中😀\r\n' 2048.
    段们 取 [(文段 模式 次数)].
    生产 取 新生产 段们.
    戳 取 文件库 其 流写文件 路径 生产 编码 BOM ''.
    原存 取 空.
    若 编码 == 65001 则 原存 取 密 其 UTF8 模式. 另 原存 取 密 其 UTF16 模式. 然
    块长 取 原存 其 大小 - 1.
    若 编码 == 1200 则 块长 取 原存 其 大小 - 2. 然
    字节段 取 [].
    头存 取 字节结构 ([239,187,191]).
    头长 取 0.
    若 BOM 则
        头长 取 3.
        若 编码 == 1200 则
            头存 其 关闭.
            头存 取 字节结构 ([255,254]).
            头长 取 2.
        然
        字节段 其 增 (原段 头存 头长 1).
    然
    字节段 其 增 (原段 原存 块长 次数).
    验原生段 路径 字节段 (名称 + ': every encoded byte').
    验流文 路径 段们 编码 BOM (块长 * 次数 + 头长) 戳 名称.
    原存 其 关闭.
    头存 其 关闭.
为

作 边界往返 路径 为 句 编码 为 数 前数 为 数 尾文 为 句 尾字节 为 阵 名称 为 句:
    块 取 重复 'a' 16384.
    整 取 (前数 - 前数 % 16384) / 16384.
    余 取 前数 % 16384.
    段们 取 [(文段 块 整)].
    若 余 > 0 则 段们 其 增 (文段 (块[:余]) 1). 然
    段们 其 增 (文段 尾文 1).
    生产 取 新生产 段们.
    戳 取 文件库 其 流写文件 路径 生产 编码 假 ''.
    前存 取 密 其 UTF8 块.
    倍 取 1.
    若 编码 == 1200 或 编码 == 1201 则
        前存 其 关闭.
        倍 取 2.
        若 编码 == 1200 则 前存 取 密 其 UTF16 块.
        另 前存 取 密 其 UTF16 (重复 '愀' 16384). 然
    然
    尾存 取 字节结构 尾字节.
    字节段 取 [(原段 前存 (16384 * 倍) 整)].
    若 余 > 0 则 字节段 其 增 (原段 前存 (余 * 倍) 1). 然
    字节段 其 增 (原段 尾存 (尾字节 其 量) 1).
    验原生段 路径 字节段 (名称 + ': boundary bytes').
    验流文 路径 段们 编码 假 (前数 * 倍 + 尾字节 其 量) 戳 名称.
    前存 其 关闭.
    尾存 其 关闭.
为

作 拒绝原字节 路径 为 句 字节们 为 阵 编码 为 数 名称 为 句:
    数据 取 字节结构 字节们.
    写原生段 路径 ([(原段 数据 (字节们 其 量) 1)]).
    数据 其 关闭.
    应失败 (算: 得 文件库 其 流读文件 路径 编码 (算 不询问) (算 忽略). 法) 名称.
为

作 拒绝边界尾 路径 为 句 编码 为 数 前数 为 数 尾字节 为 阵 名称 为 句:
    块 取 重复 'a' 16384.
    前存 取 密 其 UTF8 块.
    倍 取 1.
    若 编码 == 1200 或 编码 == 1201 则
        前存 其 关闭.
        倍 取 2.
        若 编码 == 1200 则 前存 取 密 其 UTF16 块.
        另 前存 取 密 其 UTF16 (重复 '愀' 16384). 然
    然
    尾存 取 字节结构 尾字节.
    整 取 (前数 - 前数 % 16384) / 16384.
    余 取 前数 % 16384.
    段们 取 [(原段 前存 (16384 * 倍) 整)].
    若 余 > 0 则 段们 其 增 (原段 前存 (余 * 倍) 1). 然
    段们 其 增 (原段 尾存 (尾字节 其 量) 1).
    写原生段 路径 段们.
    前存 其 关闭.
    尾存 其 关闭.
    应失败 (算: 得 文件库 其 流读文件 路径 编码 (算 不询问) (算 忽略). 法) 名称.
为

作 空流往返 路径 为 句 编码 为 数 BOM 为 事实 字节们 为 阵:
    生产 取 新生产 ([]).
    戳 取 文件库 其 流写文件 路径 生产 编码 BOM ''.
    名称 取 'empty stream ' + (编码 为 句) + ' BOM=' + (BOM 为 句).
    数据 取 字节结构 字节们.
    验原生段 路径 ([(原段 数据 (字节们 其 量) 1)]) (名称 + ': bytes').
    数据 其 关闭.
    验流文 路径 ([]) 编码 BOM (字节们 其 量) 戳 名称.
为

# A sparse NTFS fixture has only 64 KiB of real data. SetEndOfFile supplies the size.
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

作 阈值验证 路径 为 句:
    稀疏文件 路径 500000000.
    状态 取 文件库 其 准备读取 路径 0.
    断言 (状态['size'] == 500000000 且 状态['readCalls'] == 0 且 状态['bufferBytes'] == 0) '500MB prepare reads metadata only'.
    许可 取 文件库 其 确认读取 状态 (算 不询问).
    断言 许可 'exactly 500000000 bytes needs no confirmation'.
    首文 取 文件库 其 读取一步 状态.
    断言 (首文 != 空 且 首文 其 量 > 0 且 首文 其 量 <= 65536 且 首文 == (重复 'a' (首文 其 量))) '500MB exact threshold starts bounded decoding'.
    文件库 其 关闭读取 状态.
    文件库 其 关闭读取 状态.
    稀疏文件 路径 500000001.
    状态 取 文件库 其 准备读取 路径 0.
    应失败 (算: 得 文件库 其 读取一步 状态. 法) 'unapproved cursor refuses body reads'.
    次数 取 [0].
    拒绝 取 算 长 为 数:
        次数[0] 取 次数[0] + 1.
        若 长 != 500000001 则 卒 'wrong confirmation size'. 然
        若 状态['readCalls'] != 0 或 状态['bufferBytes'] != 0 则 卒 'data touched before confirmation'. 然
        得 假.
    法.
    许可 取 文件库 其 确认读取 状态 拒绝.
    断言 (非 许可 且 次数[0] == 1 且 状态['readCalls'] == 0 且 状态['bufferBytes'] == 0) '500000001 cancel occurs before ReadFile and chunk allocation'.
    文件库 其 关闭读取 状态.
    # An independent write-open proves cancellation released the share-read guard.
    句柄 取 打开 路径 1073741824 3.
    Close 其 调用 [句柄].
    状态 取 文件库 其 准备读取 路径 0.
    同意 取 算 长 为 数:
        次数[0] 取 次数[0] + 1.
        若 长 != 500000001 或 状态['readCalls'] != 0 或 状态['bufferBytes'] != 0 则 卒 'approval must precede reads and buffers'. 然
        得 真.
    法.
    许可 取 文件库 其 确认读取 状态 同意.
    首文 取 文件库 其 读取一步 状态.
    断言 (许可 且 次数[0] == 2 且 状态['readCalls'] > 0 且 状态['bufferBytes'] > 0 且 状态['bufferBytes'] <= 65540 且 首文 != 空 且 首文 其 量 > 0 且 首文 其 量 <= 65536) 'accepted >500MB reads a bounded first chunk without giant allocation'.
    文件库 其 关闭读取 状态.
    包装次 取 [0,0].
    取消 取 算 长 为 数: 包装次[0] 取 包装次[0] + 1. 得 假. 法.
    接收 取 算 文 为 句: 包装次[1] 取 包装次[1] + 1. 得 空. 法.
    结果 取 文件库 其 流读文件 路径 0 取消 接收.
    断言 (结果 == 空 且 包装次[0] == 1 且 包装次[1] == 0) 'cancelled streaming wrapper returns null without delivering text'.
    状态 取 文件库 其 准备读取 路径 0.
    确认失败 取 算 长 为 数: 卒 'intentional confirmation failure'. 法.
    应失败 (算: 得 文件库 其 确认读取 状态 确认失败. 法) 'confirmation failure closes pending reader'.
    断言 (状态['closed'] 且 状态['readCalls'] == 0 且 状态['bufferBytes'] == 0) 'failed confirmation leaves body untouched'.
    句柄 取 打开 路径 1073741824 3.
    Close 其 调用 [句柄].
    稀疏文件 路径 4294967297.
    状态 取 文件库 其 准备读取 路径 0.
    确认长 取 [0].
    拒绝巨型 取 算 长 为 数: 确认长[0] 取 长. 得 假. 法.
    许可 取 文件库 其 确认读取 状态 拒绝巨型.
    断言 (非 许可 且 确认长[0] == 4294967297 且 状态['readCalls'] == 0 且 状态['bufferBytes'] == 0) '64-bit file size above 4GiB is confirmed precisely before reading'.
    文件库 其 关闭读取 状态.
为

算 元初 外参 为 句 阵:
    若 外参 其 量 != 1 则
        显 'Usage: file_streaming_native.exe EXISTING_DISPOSABLE_DIRECTORY'.
        得 2.
    然
    根 取 外参[0] + '\\ru-stream-test-'.
    路径 取 根 + '内容-😀.txt'.
    原样 取 根 + 'raw.bin'.
    稀疏 取 根 + 'sparse.txt'.
    文件们 取 [路径,原样,稀疏].
    试
        大文件往返 路径 65001 真 257 'UTF-8 >4MiB'.
        大文件往返 路径 65001 假 821 'UTF-8 >16MiB'.
        大文件往返 路径 1200 真 172 'UTF-16LE >4MiB'.
        边界往返 路径 65001 65535 '中😀' ([228,184,173,240,159,152,128]) 'UTF-8 three-byte sequence crosses 64KiB'.
        边界往返 路径 65001 65534 '😀中' ([240,159,152,128,228,184,173]) 'UTF-8 four-byte sequence crosses 64KiB'.
        边界往返 路径 1200 32767 '😀中' ([61,216,0,222,45,78]) 'UTF-16LE surrogate pair crosses 64KiB'.
        边界往返 路径 1201 32767 '😀中' ([216,61,222,0,78,45]) 'UTF-16BE surrogate pair crosses 64KiB'.
        边界往返 路径 936 65535 '中文' ([214,208,206,196]) 'CP936 double-byte sequence crosses 64KiB'.
        边界往返 路径 1252 65535 'é€\r\n' ([233,128,13,10]) 'CP1252 exact legacy bytes across 64KiB'.
        拒绝原字节 原样 ([192,175]) 0 'reject overlong UTF-8 stream'.
        拒绝原字节 原样 ([240,159,152]) 0 'reject partial UTF-8 stream'.
        拒绝原字节 原样 ([237,160,128]) 0 'reject UTF-8 surrogate stream'.
        拒绝原字节 原样 ([65,0,66]) 0 'reject UTF-8 NUL stream'.
        拒绝原字节 原样 ([255,254,65]) 0 'reject odd UTF-16LE stream'.
        拒绝原字节 原样 ([254,255,0]) 0 'reject odd UTF-16BE stream'.
        拒绝原字节 原样 ([255,254,0,216]) 0 'reject lone UTF-16LE high surrogate'.
        拒绝原字节 原样 ([254,255,220,0]) 0 'reject lone UTF-16BE low surrogate'.
        拒绝原字节 原样 ([255,254,65,0,0,0,66,0]) 0 'reject UTF-16 NUL stream'.
        拒绝原字节 原样 ([255,254,0,0,65,0,0,0]) 0 'reject UTF-32LE stream'.
        拒绝原字节 原样 ([0,0,254,255,0,0,0,65]) 0 'reject UTF-32BE stream'.
        拒绝原字节 原样 ([214]) 936 'reject dangling GBK lead byte'.
        拒绝原字节 原样 ([65,0,66]) 1252 'reject CP1252 NUL stream'.
        空流往返 路径 65001 假 ([]).
        空流往返 路径 65001 真 ([239,187,191]).
        空流往返 路径 1200 真 ([255,254]).
        空流往返 路径 1201 真 ([254,255]).
        拒绝边界尾 原样 65001 65535 ([192,175]) 'reject malformed UTF-8 crossing 64KiB'.
        拒绝边界尾 原样 65001 65535 ([0,66]) 'reject NUL crossing 64KiB'.
        拒绝边界尾 原样 936 65535 ([214]) 'reject incomplete GBK at 64KiB EOF'.
        拒绝边界尾 原样 1200 32767 ([61,216]) 'reject incomplete UTF-16LE pair at 64KiB EOF'.
        拒绝边界尾 原样 1201 32767 ([216,61]) 'reject incomplete UTF-16BE pair at 64KiB EOF'.
        # Partial tails are rejected after real full-sized chunks, not just at byte zero.
        前存 取 密 其 UTF8 (重复 'a' 16384).
        尾存 取 字节结构 ([240,159,152]).
        写原生段 原样 ([(原段 前存 16384 4),(原段 尾存 3 1)]).
        应失败 (算: 得 文件库 其 流读文件 原样 0 (算 不询问) (算 忽略). 法) 'reject partial UTF-8 after a complete 64KiB chunk'.
        前存 其 关闭. 尾存 其 关闭.
        戳 取 文件库 其 写文件 路径 'original' 65001 假 ''.
        次数 取 [0].
        坏生产 取 算:
            次数[0] 取 次数[0] + 1.
            若 次数[0] == 1 则 得 重复 'a' 16384. 然
            卒 'intentional producer failure after first staged chunk'.
        法.
        应失败 (算: 得 文件库 其 流写文件 路径 坏生产 65001 假 戳. 法) 'producer failure aborts staged save'.
        文档 取 文件库 其 读文件 路径 0.
        断言 (次数[0] == 2 且 文档['text'] == 'original' 且 文档['stamp'] == 戳) 'producer failure preserves original bytes and stamp'.
        原存 取 密 其 UTF8 'original'.
        验原生段 路径 ([(原段 原存 8 1)]) 'producer failure preserves every original byte'.
        原存 其 关闭.
        有损生产 取 新生产 ([(文段 'staged ASCII' 1),(文段 '😀' 1)]).
        应失败 (算: 得 文件库 其 流写文件 路径 有损生产 1252 假 戳. 法) 'late unrepresentable legacy chunk aborts staged save'.
        文档 取 文件库 其 读文件 路径 0.
        断言 (文档['text'] == 'original' 且 文档['stamp'] == 戳) 'late encoding failure preserves original'.
        巨段生产 取 新生产 ([(文段 (重复 'a' 65537) 1)]).
        应失败 (算: 得 文件库 其 流写文件 路径 巨段生产 65001 假 戳. 法) 'reject producer chunks over 65536 codepoints'.
        文档 取 文件库 其 读文件 路径 0.
        断言 (文档['text'] == 'original' 且 文档['stamp'] == 戳) 'oversized producer preserves original'.
        # Direct cancellation after writing a chunk must also retain the original.
        写态 取 文件库 其 准备写入 路径 65001 假 戳.
        文件库 其 写入一段 写态 'replacement that is never committed'.
        文件库 其 取消写入 写态.
        文件库 其 取消写入 写态.
        文档 取 文件库 其 读文件 路径 0.
        断言 (文档['text'] == 'original' 且 文档['stamp'] == 戳) 'cursor cancellation preserves original'.
        # Failure followed by success proves stage cleanup did not poison later saves.
        生产 取 新生产 ([(文段 'updated' 1)]).
        新戳 取 文件库 其 流写文件 路径 生产 65001 假 戳.
        文档 取 文件库 其 读文件 路径 0.
        断言 (文档['text'] == 'updated' 且 文档['stamp'] == 新戳) 'streaming save succeeds after cancellation and producer failure'.
        阈值验证 稀疏.
    救 原因
        显 原因.
        显 'Fixtures retained in: ' + 外参[0].
        得 1.
    终
    位 取 0.
    循 文件们 其 量 次
        路存 取 密 其 UTF16 文件们[位].
        成果 取 Delete 其 调用 [路存].
        路存 其 关闭.
        必须成功 成果 'delete streaming fixture'.
        位 取 位 + 1.
    环
    显 'FILE_STREAMING_TESTS_PASS=' + (统计[0] 为 句).
    得 0.
法
