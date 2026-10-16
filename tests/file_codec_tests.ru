# Native Windows x64 integration tests. Pass a disposable existing directory.
# These tests create/remove only files prefixed ru-codec-test- inside that folder.
文件库 取 外言 '../src/file_codec.ru'.
密 取 外言 '如:密'.
U8 取 密 其 u8.
U32 取 密 其 u32.
I32 取 密 其 i32.
I64 取 密 其 i64.
PTR 取 密 其 指针.
系统 取 密 其 系统库 'kernel32.dll'.
Open 取 系统 其 绑定 'CreateFileW' (密 其 签名 PTR ([PTR,U32,U32,PTR,U32,U32,PTR]) 'win64').
Close 取 系统 其 绑定 'CloseHandle' (密 其 签名 I32 ([PTR]) 'win64').
Read 取 系统 其 绑定 'ReadFile' (密 其 签名 I32 ([PTR,PTR,U32,PTR,PTR]) 'win64').
Write 取 系统 其 绑定 'WriteFile' (密 其 签名 I32 ([PTR,PTR,U32,PTR,PTR]) 'win64').
Delete 取 系统 其 绑定 'DeleteFileW' (密 其 签名 I32 ([PTR]) 'win64').
Size 取 系统 其 绑定 'GetFileSizeEx' (密 其 签名 I32 ([PTR,PTR]) 'win64').
SetPointer 取 系统 其 绑定 'SetFilePointerEx' (密 其 签名 I32 ([PTR,I64,PTR,U32]) 'win64').
SetAttributes 取 系统 其 绑定 'SetFileAttributesW' (密 其 签名 I32 ([PTR,U32]) 'win64').
CreateHardLink 取 系统 其 绑定 'CreateHardLinkW' (密 其 签名 I32 ([PTR,PTR,PTR]) 'win64').
SetEnd 取 系统 其 绑定 'SetEndOfFile' (密 其 签名 I32 ([PTR]) 'win64').
计数型 取 密 其 结构 [['n',U32]].
大小型 取 密 其 结构 [['n',I64]].
统计 取 {'pass':0}.

作 断言 条件 为 事实 名称 为 句:
    若 非 条件 则 卒 'FAIL: ' + 名称. 然
    统计 其 增 'pass' (统计['pass'] + 1).
    显 'PASS: ' + 名称.
为

作 必须成功 成果 名称 为 句:
    若 (成果 其 值) 其 为空 则 卒 名称 + ' Win32=' + (成果 其 错误码 为 句). 然
为

算 打开 路径 为 句 访问 为 数 模式 为 数:
    路径存 取 密 其 UTF16 路径.
    成果 取 Open 其 调用 [路径存,访问,1,空,模式,128,空].
    路径存 其 关闭.
    句柄 取 成果 其 值.
    若 句柄 其 句 == '18446744073709551615' 则 卒 'fixture open failed: ' + (成果 其 错误码 为 句). 然
    得 句柄.
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

作 写原字节 路径 为 句 字节们 为 阵:
    句柄 取 打开 路径 1073741824 2.
    数据 取 字节结构 字节们.
    数存 取 计数型 其 新建.
    成果 取 Write 其 调用 [句柄,数据,字节们 其 量,数存,空].
    Close 其 调用 [句柄].
    数据 其 关闭.
    写长 取 (数存 其 读 'n') 其 数.
    数存 其 关闭.
    必须成功 成果 'fixture write'.
    若 写长 != 字节们 其 量 则 卒 'short fixture write'. 然
为

作 验字节 路径 为 句 预期 为 阵 名称 为 句:
    句柄 取 打开 路径 2147483648 3.
    长存 取 大小型 其 新建.
    成果 取 Size 其 调用 [句柄,长存].
    必须成功 成果 'fixture size'.
    长 取 (长存 其 读 'n') 其 数.
    长存 其 关闭.
    数据 取 字节结构 预期.
    数存 取 计数型 其 新建.
    成果 取 Read 其 调用 [句柄,数据,预期 其 量,数存,空].
    Close 其 调用 [句柄].
    必须成功 成果 'fixture read'.
    相同 取 长 == 预期 其 量 且 (数存 其 读 'n') 其 数 == 预期 其 量.
    位 取 0.
    循 预期 其 量 次
        若 (数据 其 读 ('b' + (位 为 句))) 其 数 != 预期[位] 则 相同 取 假. 然
        位 取 位 + 1.
    环
    数据 其 关闭.
    数存 其 关闭.
    断言 相同 名称.
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

作 编码往返 路径 为 句 文本 为 句 编码 为 数 BOM 为 事实 预期 为 阵:
    戳 取 文件库 其 写文件 路径 文本 编码 BOM ''.
    打开编码 取 编码.
    若 BOM 或 编码 == 65001 则 打开编码 取 0. 然
    文档 取 文件库 其 读文件 路径 打开编码.
    断言 (文档['text'] == 文本 且 文档['encoding'] == 编码 且 文档['bom'] == BOM 且 文档['stamp'] == 戳 且 文档['path'] == (文件库 其 绝对路径 路径)) ('round trip ' + (编码 为 句) + ' BOM=' + (BOM 为 句)).
    验字节 路径 预期 ('exact bytes ' + (编码 为 句) + ' BOM=' + (BOM 为 句)).
为

作 原字节拒绝 路径 为 句 字节们 为 阵 编码 为 数 名称 为 句:
    写原字节 路径 字节们.
    应失败 (算: 得 文件库 其 读文件 路径 编码. 法) 名称.
为

算 元初 外参 为 句 阵:
    若 外参 其 量 != 1 则
        显 'Usage: file_codec_tests.exe EXISTING_DISPOSABLE_DIRECTORY'.
        得 2.
    然
    根 取 外参[0] + '\\ru-codec-test-'.
    路径 取 根 + '内容-😀.txt'.
    原样 取 根 + 'raw.bin'.
    边界 取 根 + 'boundary.txt'.
    锁定路径 取 根 + 'locked.txt'.
    链接路径 取 根 + 'hardlink.txt'.
    文件们 取 [路径,原样,边界,锁定路径].
    试
        编码往返 路径 'A中😀\r\n' 65001 假 ([65,228,184,173,240,159,152,128,13,10]).
        编码往返 路径 'A中😀\r\n' 65001 真 ([239,187,191,65,228,184,173,240,159,152,128,13,10]).
        编码往返 路径 'A中😀\r\n' 1200 真 ([255,254,65,0,45,78,61,216,0,222,13,0,10,0]).
        编码往返 路径 'A中😀\r\n' 1201 真 ([254,255,0,65,78,45,216,61,222,0,0,13,0,10]).
        编码往返 路径 'A中😀\r\n' 1200 假 ([65,0,45,78,61,216,0,222,13,0,10,0]).
        编码往返 路径 'A中😀\r\n' 1201 假 ([0,65,78,45,216,61,222,0,0,13,0,10]).
        编码往返 路径 'Ø' 1201 真 ([254,255,0,216]).
        编码往返 路径 'Ü' 1201 真 ([254,255,0,220]).
        编码往返 路径 'Café €\r\n' 1252 假 ([67,97,102,233,32,128,13,10]).
        编码往返 路径 '中文\r\n' 936 假 ([214,208,206,196,13,10]).
        编码往返 路径 '' 65001 假 ([]).
        编码往返 路径 '' 65001 真 ([239,187,191]).
        编码往返 路径 '' 1200 真 ([255,254]).
        编码往返 路径 '' 1201 真 ([254,255]).
        编码往返 路径 '' 1252 假 ([]).
        编码往返 路径 '' 936 假 ([]).
        原字节拒绝 原样 ([192,175]) 0 'reject overlong UTF-8'.
        原字节拒绝 原样 ([240,159,152]) 0 'reject truncated UTF-8'.
        原字节拒绝 原样 ([237,160,128]) 0 'reject UTF-8 encoded surrogate'.
        原字节拒绝 原样 ([65,0,66]) 0 'reject UTF-8 embedded NUL'.
        原字节拒绝 原样 ([255,254,65]) 0 'reject odd UTF-16LE'.
        原字节拒绝 原样 ([254,255,0]) 0 'reject odd UTF-16BE'.
        原字节拒绝 原样 ([255,254,0,216]) 0 'reject lone high surrogate LE'.
        原字节拒绝 原样 ([255,254,0,220]) 0 'reject lone low surrogate LE'.
        原字节拒绝 原样 ([254,255,216,0]) 0 'reject lone high surrogate BE'.
        原字节拒绝 原样 ([254,255,220,0]) 0 'reject lone low surrogate BE'.
        原字节拒绝 原样 ([255,254,65,0,0,0,66,0]) 0 'reject UTF-16 embedded NUL'.
        原字节拒绝 原样 ([255,254,0,0,65,0,0,0]) 0 'reject UTF-32LE BOM'.
        原字节拒绝 原样 ([0,0,254,255,0,0,0,65]) 0 'reject UTF-32BE BOM'.
        原字节拒绝 原样 ([214]) 936 'reject dangling CP936 lead byte'.
        原字节拒绝 原样 ([65,0,66]) 1252 'reject CP1252 NUL'.
        写原字节 原样 ([67,97,102,233]).
        应失败 (算: 得 文件库 其 读文件 原样 0. 法) 'legacy is never guessed'.
        文档 取 文件库 其 读文件 原样 1252.
        断言 (文档['text'] == 'Café') 'explicit CP1252 recovers legacy file'.
        戳 取 文件库 其 写文件 路径 'original' 65001 假 ''.
        应失败 (算: 得 文件库 其 写文件 路径 '😀' 1252 假 戳. 法) 'reject lossy CP1252 save'.
        应失败 (算: 得 文件库 其 写文件 路径 '∞' 1252 假 戳. 法) 'reject CP1252 best-fit infinity'.
        应失败 (算: 得 文件库 其 写文件 路径 '😀' 936 假 戳. 法) 'reject lossy CP936 save'.
        应失败 (算: 得 文件库 其 写文件 路径 'hello' 936 真 戳. 法) 'reject legacy BOM'.
        文档 取 文件库 其 读文件 路径 0.
        断言 (文档['text'] == 'original' 且 文档['stamp'] == 戳) 'failed conversion preserves original'.
        写原字节 路径 ([99,104,97,110,103,101,100]).
        应失败 (算: 得 文件库 其 写文件 路径 'mine' 65001 假 戳. 法) 'detect external modification'.
        验字节 路径 ([99,104,97,110,103,101,100]) 'external bytes preserved on conflict'.
        文档 取 文件库 其 读文件 路径 0.
        新戳 取 文件库 其 写文件 路径 'updated' 65001 假 文档['stamp'].
        文档 取 文件库 其 读文件 路径 0.
        断言 (文档['text'] == 'updated' 且 文档['stamp'] == 新戳) 'save returns stamp of replacement'.
        保留名们 取 ['NUL.txt','CON','cOm1.log','LPT³.tmp','NUL        .txt','CONOUT$.txt','bad.','bad '].
        名位 取 0.
        循 保留名们 其 量 次
            名 取 保留名们[名位].
            应失败 (算: 文件库 其 _检查路径段 名. 得 空. 法) ('reject reserved path component ' + 名).
            名位 取 名位 + 1.
        环
        应失败 (算: 得 文件库 其 读文件 '' 0. 法) 'empty path is recoverable'.
        应失败 (算: 得 文件库 其 读文件 'x' 7. 法) 'unsupported codepage is recoverable'.
        应失败 (算: 得 文件库 其 读文件 (路径 + ':stream') 0. 法) 'reject alternate data streams'.
        大文 取 'a'.
        循 22 次 大文 取 大文 + 大文. 环
        戳 取 文件库 其 写文件 边界 大文 65001 假 ''.
        文档 取 文件库 其 读文件 边界 0.
        断言 (文档['text'] == 大文 且 文档['stamp'] == 戳) 'exact 4 MiB ASCII boundary'.
        应失败 (算: 得 文件库 其 写文件 边界 大文 65001 真 戳. 法) 'BOM counts toward 4 MiB save cap'.
        应失败 (算: 得 文件库 其 写文件 边界 (大文 + 'a') 65001 假 戳. 法) 'reject save over 4 MiB'.
        句柄 取 打开 边界 1073741824 3.
        成果 取 SetPointer 其 调用 [句柄,4194305,空,0].
        必须成功 成果 'fixture seek'.
        成果 取 SetEnd 其 调用 [句柄].
        Close 其 调用 [句柄].
        必须成功 成果 'fixture extend'.
        应失败 (算: 得 文件库 其 读文件 边界 0. 法) 'reject read over 4 MiB'.
        文件库 其 写文件 锁定路径 'locked' 65001 假 ''.
        句柄 取 打开 锁定路径 1073741824 3.
        应失败 (算: 得 文件库 其 读文件 锁定路径 0. 法) 'reject concurrently open writer'.
        Close 其 调用 [句柄].
        文档 取 文件库 其 读文件 锁定路径 0.
        路存 取 密 其 UTF16 锁定路径.
        成果 取 SetAttributes 其 调用 [路存,1].
        必须成功 成果 'set read-only fixture'.
        应失败 (算: 得 文件库 其 写文件 锁定路径 'oops' 65001 假 文档['stamp']. 法) 'reject read-only destination'.
        成果 取 SetAttributes 其 调用 [路存,128].
        必须成功 成果 'restore writable fixture'.
        链存 取 密 其 UTF16 链接路径.
        成果 取 CreateHardLink 其 调用 [链存,路存,空].
        若 非 (成果 其 值) 其 为空 则
            文件们 其 增 链接路径.
            应失败 (算: 得 文件库 其 写文件 锁定路径 'oops' 65001 假 文档['stamp']. 法) 'reject hard-linked destination'.
        另
            显 'SKIP: hard-link fixture unsupported by this filesystem'.
        然
        链存 其 关闭.
        路存 其 关闭.
        短路径 取 文件库 其 _绝对路径 'x'.
        断言 (短路径[短路径 其 量 - 1] == 'x') 'short relative path has no slicing error'.
        应失败 (算: 得 文件库 其 读文件 (根 + 'missing') 0. 法) 'missing file is recoverable'.
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
        必须成功 成果 'delete test fixture'.
        位 取 位 + 1.
    环
    显 'FILE_CODEC_TESTS_PASS=' + (统计['pass'] 为 句).
    得 0.
法
