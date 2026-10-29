# Pure Ru / Win32 file codec. Import this module before entering native callbacks.
# Public: 读文件 / 写文件 and 文件.读取 / 文件.写入. See docs/file_codec.md.
本地 取 外言 'i18n.ru'.
密 取 外言 '如:密'.
_属性位 取 外言 './file_codec_flags.ru'.
流块字节 取 65536.
大文件提示字节 取 500000000.
最大段字符 取 65536.
UTF8 取 65001.
UTF16LE 取 1200.
UTF16BE 取 1201.
CP1252 取 1252.
CP936 取 936.
_I32 取 密 其 i32.
_U32 取 密 其 u32.
_U8 取 密 其 u8.
_U16 取 密 其 u16.
_I64 取 密 其 i64.
_UPTR 取 密 其 uintptr.
_PTR 取 密 其 指针.
_VOID 取 密 其 无值.
_内核 取 密 其 系统库 'kernel32.dll'.
_安全库 取 密 其 系统库 'advapi32.dll'.
_CreateFileW 取 _内核 其 绑定 'CreateFileW' (密 其 签名 _PTR ([_PTR,_U32,_U32,_PTR,_U32,_U32,_PTR]) 'win64').
_CloseHandle 取 _内核 其 绑定 'CloseHandle' (密 其 签名 _I32 ([_PTR]) 'win64').
_ReadFile 取 _内核 其 绑定 'ReadFile' (密 其 签名 _I32 ([_PTR,_PTR,_U32,_PTR,_PTR]) 'win64').
_WriteFile 取 _内核 其 绑定 'WriteFile' (密 其 签名 _I32 ([_PTR,_PTR,_U32,_PTR,_PTR]) 'win64').
_SetFilePointerEx 取 _内核 其 绑定 'SetFilePointerEx' (密 其 签名 _I32 ([_PTR,_I64,_PTR,_U32]) 'win64').
_GetFileInformationByHandle 取 _内核 其 绑定 'GetFileInformationByHandle' (密 其 签名 _I32 ([_PTR,_PTR]) 'win64').
_GetFileType 取 _内核 其 绑定 'GetFileType' (密 其 签名 _U32 ([_PTR]) 'win64').
_GetFileAttributesW 取 _内核 其 绑定 'GetFileAttributesW' (密 其 签名 _U32 ([_PTR]) 'win64').
_FlushFileBuffers 取 _内核 其 绑定 'FlushFileBuffers' (密 其 签名 _I32 ([_PTR]) 'win64').
_MoveFileExW 取 _内核 其 绑定 'MoveFileExW' (密 其 签名 _I32 ([_PTR,_PTR,_U32]) 'win64').
_ReplaceFileW 取 _内核 其 绑定 'ReplaceFileW' (密 其 签名 _I32 ([_PTR,_PTR,_PTR,_U32,_PTR,_PTR]) 'win64').
_DeleteFileW 取 _内核 其 绑定 'DeleteFileW' (密 其 签名 _I32 ([_PTR]) 'win64').
_GetFullPathNameW 取 _内核 其 绑定 'GetFullPathNameW' (密 其 签名 _U32 ([_PTR,_U32,_PTR,_PTR]) 'win64').
_GetCurrentProcessId 取 _内核 其 绑定 'GetCurrentProcessId' (密 其 签名 _U32 ([]) 'win64').
_MultiByteToWideChar 取 _内核 其 绑定 'MultiByteToWideChar' (密 其 签名 _I32 ([_U32,_U32,_PTR,_I32,_PTR,_I32]) 'win64').
_WideCharToMultiByte 取 _内核 其 绑定 'WideCharToMultiByte' (密 其 签名 _I32 ([_U32,_U32,_PTR,_I32,_PTR,_I32,_PTR,_PTR]) 'win64').
_LCMapStringW 取 _内核 其 绑定 'LCMapStringW' (密 其 签名 _I32 ([_U32,_U32,_PTR,_I32,_PTR,_I32]) 'win64').
_RtlMoveMemory 取 _内核 其 绑定 'RtlMoveMemory' (密 其 签名 _VOID ([_PTR,_PTR,_UPTR]) 'win64').
_GetFileSizeEx 取 _内核 其 绑定 'GetFileSizeEx' (密 其 签名 _I32 ([_PTR,_PTR]) 'win64').
_大小型 取 密 其 结构 [['n',_I64]].
_lstrlenW 取 _内核 其 绑定 'lstrlenW' (密 其 签名 _I32 ([_PTR]) 'win64').
_GetFileSecurityW 取 _安全库 其 绑定 'GetFileSecurityW' (密 其 签名 _I32 ([_PTR,_U32,_PTR,_U32,_PTR]) 'win64').
_MakeAbsoluteSD 取 _安全库 其 绑定 'MakeAbsoluteSD' (密 其 签名 _I32 ([_PTR,_PTR,_PTR,_PTR,_PTR,_PTR,_PTR,_PTR,_PTR,_PTR,_PTR]) 'win64').
_SetSecurityDescriptorControl 取 _安全库 其 绑定 'SetSecurityDescriptorControl' (密 其 签名 _I32 ([_PTR,_U16,_U16]) 'win64').
_IsValidSecurityDescriptor 取 _安全库 其 绑定 'IsValidSecurityDescriptor' (密 其 签名 _I32 ([_PTR]) 'win64').
_安全属性型 取 密 其 结构 [['length',_U32],['descriptor',_PTR],['inherit',_I32]].
_四字节 取 密 其 结构 [['a',_U8],['b',_U8],['c',_U8],['d',_U8]].
_计数型 取 密 其 结构 [['n',_U32]].
_文件信息型 取 密 其 结构 [
    ['attr',_U32],['createLo',_U32],['createHi',_U32],
    ['accessLo',_U32],['accessHi',_U32],['writeLo',_U32],['writeHi',_U32],
    ['volume',_U32],['sizeHi',_U32],['sizeLo',_U32],['links',_U32],
    ['idHi',_U32],['idLo',_U32]
].
_状态 取 {'sequence':0}.

作 _失败 操作 为 句 成果:
    卒 (本地 其 格式 'error.windows_operation' ([操作,(成果 其 错误码 为 句)])).
为

作 _检查成功 成果 操作 为 句:
    若 (成果 其 值) 其 为空 则
        _失败 操作 成果.
    然
为

算 _无效句柄 句柄:
    得 句柄 其 句 == '18446744073709551615'.
法

作 _关句柄 句柄:
    若 句柄 != 空 则
        _CloseHandle 其 调用 [句柄].
    然
为

作 _清内存 内存们 为 阵:
    位 取 0.
    循 内存们 其 量 次
        内存们[位] 其 关闭.
        位 取 位 + 1.
    环
为

作 _检查编码 编码 为 数 自动 为 事实:
    若 自动 且 编码 == 0 则 完. 然
    若 编码 != UTF8 且 编码 != UTF16LE 且 编码 != UTF16BE 且 编码 != CP1252 且 编码 != CP936 则
        卒 (本地 其 文本 'error.codec.unsupported_encoding').
    然
为

作 _检查路径段 段文 为 句:
    若 段文 == '' 或 段文 == '.' 或 段文 == '..' 则 完. 然
    末字 取 段文[段文 其 量 - 1].
    若 末字 == ' ' 或 末字 == '.' 则 卒 (本地 其 文本 'error.path.trailing_character'). 然
    点位 取 0.
    循 段文 其 量 次
        若 段文[点位] == '.' 则 破. 然
        点位 取 点位 + 1.
    环
    基础名 取 段文[:点位].
    循
        若 基础名 == '' 则 破. 然
        若 基础名[基础名 其 量 - 1] != ' ' 则 破. 然
        基础名 取 基础名[:基础名 其 量 - 1].
    环
    若 基础名 其 量 > 8 则 完. 然
    原名 取 基础名.
    基础名 取 ''.
    位 取 0.
    小写 取 'abcdefghijklmnopqrstuvwxyz'.
    大写 取 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.
    循 原名 其 量 次
        字 取 原名[位].
        字位 取 0.
        循 26 次
            若 字 == 小写[字位] 则 字 取 大写[字位]. 破. 然
            字位 取 字位 + 1.
        环
        基础名 取 基础名 + 字.
        位 取 位 + 1.
    环
    若 基础名 == 'CON' 或 基础名 == 'PRN' 或 基础名 == 'AUX' 或 基础名 == 'NUL' 或 基础名 == 'CONIN$' 或 基础名 == 'CONOUT$' 或 基础名 == 'CLOCK$' 则
        卒 (本地 其 文本 'error.path.reserved_device').
    然
    若 基础名 其 量 == 4 则
        若 (基础名[:3] == 'COM' 或 基础名[:3] == 'LPT') 且 ('0123456789¹²³' 其 含 基础名[3]) 则
            卒 (本地 其 文本 'error.path.reserved_device').
        然
    然
为

作 _检查所有路径段 路径 为 句:
    位 取 0.
    段始 取 0.
    循 路径 其 量 次
        若 路径[位] == '\\' 或 路径[位] == '/' 则
            _检查路径段 路径[段始:位].
            段始 取 位 + 1.
        然
        位 取 位 + 1.
    环
    _检查路径段 路径[段始:].
为

算 _命名空间路径 路径 为 句:
    若 路径 其 量 < 4 则 得 假. 然
    得 (路径[0] == '\\' 或 路径[0] == '/') 且
        (路径[1] == '\\' 或 路径[1] == '/') 且
        (路径[2] == '.' 或 路径[2] == '?') 且
        (路径[3] == '\\' 或 路径[3] == '/').
法

算 _绝对路径 路径 为 句:
    若 路径 == '' 或 路径 其 量 > 32000 则 卒 (本地 其 文本 'error.path.empty_or_long'). 然
    # Device namespaces and alternate streams are intentionally unsupported.
    若 _命名空间路径 路径 则
        卒 (本地 其 文本 'error.path.device_namespace').
    然
    位 取 0.
    循 路径 其 量 次
        字 取 路径[位].
        若 字 < ' ' 则 卒 (本地 其 文本 'error.path.control_character'). 然
        若 字 == '*' 或 字 == '?' 或 字 == '"' 或 字 == '<' 或 字 == '>' 或 字 == '|' 则
            卒 (本地 其 文本 'error.path.unsupported_character').
        然
        若 字 == ':' 且 位 != 1 则 卒 (本地 其 文本 'error.path.alternate_stream'). 然
        位 取 位 + 1.
    环
    _检查所有路径段 路径.
    输入 取 密 其 UTF16 路径.
    输出 取 密 其 缓冲 65536.
    成果 取 _GetFullPathNameW 其 调用 [输入,32768,输出,空].
    长 取 (成果 其 值) 其 数.
    输入 其 关闭.
    若 长 == 0 或 长 >= 32768 则
        输出 其 关闭.
        _失败 (本地 其 文本 'error.path.resolve') 成果.
    然
    验证 取 _WideCharToMultiByte 其 调用 [UTF8,128,输出,长,空,0,空,空].
    若 (验证 其 值) 其 为空 则
        输出 其 关闭.
        卒 (本地 其 文本 'error.path.invalid_utf16').
    然
    文 取 输出 其 解UTF16.
    输出 其 关闭.
    若 文 其 量 > 32000 或 文[文 其 量 - 1] == '\\' 或 文[文 其 量 - 1] == '/' 则 卒 (本地 其 文本 'error.path.regular_file'). 然
    若 _命名空间路径 文 则 卒 (本地 其 文本 'error.path.normalized_namespace'). 然
    _检查所有路径段 文.
    得 文.
法

算 绝对路径 路径 为 句:
    得 _绝对路径 路径.
法

算 _检查属性 路径内存 缺失可 为 事实:
    成果 取 _GetFileAttributesW 其 调用 [路径内存].
    属性 取 成果 其 值.
    若 属性 其 数 == 4294967295 则
        码 取 成果 其 错误码.
        若 缺失可 且 (码 == 2 或 码 == 3) 则 得 假. 然
        _失败 (本地 其 文本 'error.file.access') 成果.
    然
    若 _属性位 其 已设 属性 4 则 卒 (本地 其 文本 'error.file.directory'). 然
    若 _属性位 其 已设 属性 10 则 卒 (本地 其 文本 'error.file.reparse_point'). 然
    得 真.
法

算 _取信息 句柄:
    类 取 _GetFileType 其 调用 [句柄].
    若 (类 其 值) 其 数 != 1 则 卒 (本地 其 文本 'error.file.disk_only'). 然
    信息 取 _文件信息型 其 新建.
    成果 取 _GetFileInformationByHandle 其 调用 [句柄,信息].
    若 (成果 其 值) 其 为空 则
        信息 其 关闭.
        _失败 (本地 其 文本 'error.file.status') 成果.
    然
    若 _属性位 其 已设 (信息 其 读 'attr') 4 则
        信息 其 关闭.
        卒 (本地 其 文本 'error.file.regular_only').
    然
    得 信息.
法

算 _信息戳 信息:
    得 (信息 其 读 'volume') 其 句 + ':' +
        (信息 其 读 'idHi') 其 句 + ':' + (信息 其 读 'idLo') 其 句 + ':' +
        (信息 其 读 'writeHi') 其 句 + ':' + (信息 其 读 'writeLo') 其 句 + ':' +
        (信息 其 读 'sizeHi') 其 句 + ':' + (信息 其 读 'sizeLo') 其 句.
法

算 _句柄戳 句柄:
    信息 取 _取信息 句柄.
    戳 取 _信息戳 信息.
    信息 其 关闭.
    得 戳.
法

算 _打开读 路径内存:
    _检查属性 路径内存 假.
    # FILE_SHARE_READ: no writer or replacer can coexist with this snapshot.
    成果 取 _CreateFileW 其 调用 [路径内存,2147483648,1,空,3,128,空].
    句柄 取 成果 其 值.
    若 _无效句柄 句柄 则 _失败 (本地 其 文本 'error.file.open') 成果. 然
    得 句柄.
法

算 _宽文 内存 字数 为 数:
    # Caller owns a zero-filled buffer with at least one extra UTF-16 NUL.
    长成果 取 _lstrlenW 其 调用 [内存].
    若 (长成果 其 值) 其 数 != 字数 则 卒 (本地 其 文本 'error.codec.nul'). 然
    若 字数 > 0 则
        验证 取 _WideCharToMultiByte 其 调用 [UTF8,128,内存,字数,空,0,空,空].
        若 (验证 其 值) 其 为空 则 卒 (本地 其 文本 'error.codec.invalid_utf16'). 然
    然
    得 内存 其 解UTF16.
法

算 _解码 数据 字节数 为 数 编码 为 数:
    若 字节数 == 0 则 得 ''. 然
    内存们 取 [].
    文 取 ''.
    试
        若 编码 == UTF16LE 或 编码 == UTF16BE 则
            若 字节数 % 2 != 0 则 卒 (本地 其 文本 'error.codec.utf16_length'). 然
            字数 取 字节数 / 2.
            若 编码 == UTF16BE 则
                宽 取 密 其 缓冲 (字节数 + 2).
                内存们 其 增 宽.
                成果 取 _LCMapStringW 其 调用 [127,2048,数据,字数,宽,字数].
                若 (成果 其 值) 其 数 != 字数 则 _失败 (本地 其 文本 'error.codec.utf16be_swap') 成果. 然
                文 取 _宽文 宽 字数.
            另
                文 取 _宽文 数据 字数.
            然
        另
            成果 取 _MultiByteToWideChar 其 调用 [编码,8,数据,字节数,空,0].
            字数 取 (成果 其 值) 其 数.
            若 字数 == 0 则
                若 编码 == UTF8 则
                    卒 (本地 其 文本 'error.codec.invalid_utf8').
                然
                _失败 (本地 其 文本 'error.codec.invalid_selected') 成果.
            然
            宽 取 密 其 缓冲 ((字数 + 1) * 2).
            内存们 其 增 宽.
            成果 取 _MultiByteToWideChar 其 调用 [编码,8,数据,字节数,宽,字数].
            若 (成果 其 值) 其 数 != 字数 则 _失败 (本地 其 文本 'error.codec.decode') 成果. 然
            文 取 _宽文 宽 字数.
        然
    救 原因
        _清内存 内存们.
        卒 原因.
    终
    _清内存 内存们.
    得 文.
法

# A reader owns one locked file snapshot. Preparing never reads a body/header.
算 准备读取 路径 为 句 代码页 为 数:
    _检查编码 代码页 真.
    路径文 取 _绝对路径 路径.
    状态 取 {'path':路径文,'encoding':代码页,'bom':假,'stamp':'','fileIdentity':'','size':0,'bytes':0,'textBytes':0,'position':0,'readCalls':0,'readBytes':0,'bufferBytes':0,'approved':假,'started':假,'done':假,'closed':假,'handle':空,'memory':[]}.
    试
        路径存 取 密 其 UTF16 路径文.
        状态['memory'] 其 增 路径存.
        句柄 取 _打开读 路径存.
        状态 其 增 'handle' 句柄.
        信息 取 _取信息 句柄.
        状态['memory'] 其 增 信息.
        长存 取 _大小型 其 新建.
        状态['memory'] 其 增 长存.
        _检查成功 (_GetFileSizeEx 其 调用 [句柄,长存]) (本地 其 文本 'error.file.size_read').
        # Guard BEFORE native->Ru numeric conversion (which is a fatal type
        # error for out-of-range integers), preserving existing dirty tabs.
        高 取 (信息 其 读 'sizeHi') 其 数.
        低 取 (信息 其 读 'sizeLo') 其 数.
        若 高 > 2097151 则 卒 (本地 其 文本 'error.file.size_range'). 然
        实际 取 长存 其 读 'n'.
        若 (实际 其 位段 32 32) != 高 或 (实际 其 位段 0 32) != 低 则 卒 (本地 其 文本 'error.file.size_changed'). 然
        大小 取 高*4294967296+低.
        状态 其 增 'size' 大小.
        状态 其 增 'bytes' 大小.
        状态 其 增 'stamp' (_信息戳 信息).
        状态 其 增 'fileIdentity' ((信息 其 读 'volume') 其 句 + ':' + (信息 其 读 'idHi') 其 句 + ':' + (信息 其 读 'idLo') 其 句).
    救 原因
        关闭读取 状态.
        卒 原因.
    终
    得 状态.
法

算 关闭读取 状态:
    若 非 状态['closed'] 则
        _关句柄 状态['handle'].
        状态 其 增 'handle' 空.
        _清内存 状态['memory'].
        状态 其 增 'memory' ([]).
        状态 其 增 'closed' 真.
    然
    得 空.
法

算 确认读取 状态 确认 为 算:
    若 状态['closed'] 则 卒 (本地 其 文本 'error.file.read_closed'). 然
    若 状态['approved'] 则 得 真. 然
    试
        若 状态['size'] > 大文件提示字节 则
            若 非 (确认 状态['size']) 则
                关闭读取 状态.
                得 假.
            然
        然
        状态 其 增 'approved' 真.
    救 原因
        关闭读取 状态.
        卒 原因.
    终
    得 真.
法

作 _读入 状态 数据 长 为 数 计数:
    状态 其 增 'readCalls' (状态['readCalls']+1).
    成果 取 _ReadFile 其 调用 [状态['handle'],数据,长,计数,空].
    _检查成功 成果 (本地 其 文本 'error.file.read').
    状态 其 增 'readBytes' (状态['readBytes']+(计数 其 读 'n') 其 数).
为

作 _开始读取正文 状态:
    头 取 _四字节 其 新建.
    计数 取 _计数型 其 新建.
    状态['memory'] 其 增 头.
    状态['memory'] 其 增 计数.
    状态 其 增 'count' 计数.
    头长 取 4.
    总长 取 状态['size'].
    若 总长 < 4 则 头长 取 总长. 然
    若 头长 > 0 则
        _读入 状态 头 头长 计数.
        若 (计数 其 读 'n') 其 数 != 头长 则 卒 (本地 其 文本 'error.file.header_incomplete'). 然
    然
    a 取 (头 其 读 'a') 其 数.
    b 取 (头 其 读 'b') 其 数.
    c 取 (头 其 读 'c') 其 数.
    d 取 (头 其 读 'd') 其 数.
    若 总长 >= 4 且 ((a == 255 且 b == 254 且 c == 0 且 d == 0) 或 (a == 0 且 b == 0 且 c == 254 且 d == 255)) 则 卒 (本地 其 文本 'error.codec.utf32'). 然
    编码 取 状态['encoding'].
    若 编码 == 0 则 编码 取 UTF8. 然
    跳过 取 0.
    若 总长 >= 3 且 a == 239 且 b == 187 且 c == 191 则 编码 取 UTF8. 跳过 取 3. 然
    若 总长 >= 2 且 a == 255 且 b == 254 则 编码 取 UTF16LE. 跳过 取 2. 然
    若 总长 >= 2 且 a == 254 且 b == 255 则 编码 取 UTF16BE. 跳过 取 2. 然
    状态 其 增 'encoding' 编码.
    状态 其 增 'bom' (跳过 > 0).
    状态 其 增 'position' 跳过.
    状态 其 增 'started' 真.
    _检查成功 (_SetFilePointerEx 其 调用 [状态['handle'],跳过,空,0]) (本地 其 文本 'error.file.seek_body').
为

算 _解码前缀 数据 长 为 数 编码 为 数:
    # Copy only the chosen prefix; the extra two zero bytes are owned terminators.
    副本 取 密 其 缓冲 (长+2+长%2).
    试
        _RtlMoveMemory 其 调用 [副本,数据,长].
        文 取 _解码 副本 长 编码.
    救 原因
        副本 其 关闭.
        卒 原因.
    终
    副本 其 关闭.
    得 文.
法

算 _解码流块 数据 长 为 数 编码 为 数 末块 为 事实:
    # First accept a complete valid chunk. Only an invalid nonfinal suffix may
    # be carried by rereading up to three bytes from the SAME guarded handle.
    结果 取 {'text':空,'bytes':长,'error':''}.
    最多 取 0.
    若 非 末块 则
        若 编码 == UTF8 或 编码 == UTF16LE 或 编码 == UTF16BE 则 最多 取 3. 然
        若 编码 == CP936 则 最多 取 1. 然
    然
    缩短 取 0.
    循 (最多+1) 次
        若 长-缩短 <= 0 则 破. 然
        试
            文 取 _解码前缀 数据 (长-缩短) 编码.
            结果 其 增 'text' 文.
            结果 其 增 'bytes' (长-缩短).
        救 原因
            若 缩短 == 0 则 结果 其 增 'error' 原因. 然
        终
        若 结果['text'] != 空 则 得 结果. 然
        缩短 取 缩短+1.
    环
    卒 结果['error'].
法

算 读取一步 状态:
    若 状态['done'] 则 得 空. 然
    若 状态['closed'] 或 非 状态['approved'] 则 卒 (本地 其 文本 'error.file.read_unavailable'). 然
    数据 取 空.
    试
        若 非 状态['started'] 则 _开始读取正文 状态. 然
        剩余 取 状态['size']-状态['position'].
        长 取 流块字节.
        若 剩余 < 长 则 长 取 剩余. 然
        数据 取 密 其 缓冲 (长+2+长%2).
        状态 其 增 'bufferBytes' (流块字节+4).
        计数 取 状态['count'].
        若 长 == 0 则
            # A final bounded probe detects unexpected growth as well as truncation.
            _读入 状态 数据 1 计数.
            若 (计数 其 读 'n') 其 数 != 0 则 卒 (本地 其 文本 'error.file.grew_during_read'). 然
            若 (_句柄戳 状态['handle']) != 状态['stamp'] 则 卒 (本地 其 文本 'error.file.changed_during_read'). 然
            数据 其 关闭.
            数据 取 空.
            状态 其 增 'done' 真.
            关闭读取 状态.
            得 空.
        然
        _读入 状态 数据 长 计数.
        若 (计数 其 读 'n') 其 数 != 长 则 卒 (本地 其 文本 'error.file.read_incomplete'). 然
        块 取 _解码流块 数据 长 状态['encoding'] (长 == 剩余).
        数据 其 关闭.
        数据 取 空.
        状态 其 增 'position' (状态['position']+块['bytes']).
        若 块['bytes'] != 长 则
            _检查成功 (_SetFilePointerEx 其 调用 [状态['handle'],状态['position'],空,0]) (本地 其 文本 'error.file.seek_chunk').
        然
        文存 取 密 其 UTF8 块['text'].
        状态 其 增 'textBytes' (状态['textBytes']+(文存 其 大小)-1).
        文存 其 关闭.
    救 原因
        若 数据 != 空 则 数据 其 关闭. 然
        关闭读取 状态.
        卒 原因.
    终
    得 块['text'].
法

算 流读文件 路径 为 句 代码页 为 数 确认 为 算 接收 为 算:
    状态 取 准备读取 路径 代码页.
    试
        若 非 (确认读取 状态 确认) 则 得 空. 然
        循
            文 取 读取一步 状态.
            若 文 == 空 则 破. 然
            接收 文.
        环
    救 原因
        关闭读取 状态.
        卒 原因.
    终
    得 状态.
法

算 读文件 路径 为 句 代码页 为 数:
    # Explicit SMALL compatibility API only; document opening has no such cap.
    状态 取 准备读取 路径 代码页.
    文本 取 ''.
    试
        若 状态['size'] > 1048576 则 卒 '整句兼容读取仅供不超过 1 MiB 的小文本；请使用准备读取/读取一步流式接口'. 然
        确认读取 状态 (算 大小: 得 假. 法).
        循
            文 取 读取一步 状态.
            若 文 == 空 则 破. 然
            文本 取 文本+文.
        环
    救 原因
        关闭读取 状态.
        卒 原因.
    终
    状态 其 增 'text' 文本.
    得 状态.
法

算 _文本宽存 文本 为 句:
    若 文本 其 量 > 最大段字符 则 卒 '单个保存块超过 65536 字符；请使用有界流式生产器'. 然
    得 密 其 UTF16 文本.
法

算 _编码数据 文本 为 句 编码 为 数 BOM 为 事实:
    _检查编码 编码 假.
    若 BOM 且 (编码 == CP1252 或 编码 == CP936) 则 卒 (本地 其 文本 'error.codec.legacy_bom'). 然
    内存们 取 [].
    数据 取 空.
    长 取 0.
    头长 取 0.
    若 BOM 则
        头长 取 2.
        若 编码 == UTF8 则 头长 取 3. 然
    然
    试
        宽 取 _文本宽存 文本.
        内存们 其 增 宽.
        宽长 取 (宽 其 大小 - 2) / 2.
        若 编码 == UTF16LE 或 编码 == UTF16BE 则
            长 取 宽长 * 2.
            # A separate output buffer avoids ownership/cleanup ambiguities.
            数据 取 密 其 缓冲 (长 + 2).
            若 长 > 0 则
                若 编码 == UTF16BE 则
                    成果 取 _LCMapStringW 其 调用 [127,2048,宽,宽长,数据,宽长].
                    若 (成果 其 值) 其 数 != 宽长 则 _失败 (本地 其 文本 'error.codec.utf16be_swap') 成果. 然
                另
                    # Re-encode through a managed UTF16 owner; no raw pointer math.
                    数据 其 关闭.
                    数据 取 密 其 UTF16 文本.
                然
            然
        另
            标志 取 1024.
            默认标志 取 _计数型 其 新建.
            内存们 其 增 默认标志.
            默认指针 取 默认标志.
            若 编码 == UTF8 则 标志 取 128. 默认指针 取 空. 然
            若 宽长 > 0 则
                成果 取 _WideCharToMultiByte 其 调用 [编码,标志,宽,宽长,空,0,空,默认指针].
                长 取 (成果 其 值) 其 数.
                若 长 == 0 则 _失败 (本地 其 文本 'error.codec.encode') 成果. 然
                若 编码 != UTF8 且 (默认标志 其 读 'n') 其 数 != 0 则
                    卒 (本地 其 文本 'error.codec.lossless_required').
                然
            然
            数据 取 密 其 缓冲 (长 + 1).
            若 长 > 0 则
                默认标志 其 写 'n' 0.
                成果 取 _WideCharToMultiByte 其 调用 [编码,标志,宽,宽长,数据,长,空,默认指针].
                若 (成果 其 值) 其 数 != 长 则 _失败 (本地 其 文本 'error.codec.encode') 成果. 然
                若 编码 != UTF8 则
                    若 (默认标志 其 读 'n') 其 数 != 0 则 卒 (本地 其 文本 'error.codec.loss_cancelled'). 然
                    若 (_解码 数据 长 编码) != 文本 则 卒 (本地 其 文本 'error.codec.roundtrip_cancelled'). 然
                然
            然
        然
    救 原因
        若 数据 != 空 则 数据 其 关闭. 然
        _清内存 内存们.
        卒 原因.
    终
    _清内存 内存们.
    得 {'data':数据,'bytes':长,'headerBytes':头长}.
法

作 _写完整 句柄 数据 字节数 为 数 计数:
    若 字节数 == 0 则 完. 然
    成果 取 _WriteFile 其 调用 [句柄,数据,字节数,计数,空].
    _检查成功 成果 (本地 其 文本 'error.file.temp_write').
    若 (计数 其 读 'n') 其 数 != 字节数 则 卒 (本地 其 文本 'error.file.temp_incomplete'). 然
为

算 _确认目标 路径内存 预期stamp 为 句:
    存在 取 _检查属性 路径内存 (预期stamp == '').
    若 非 存在 则 得 空. 然
    句柄 取 _打开读 路径内存.
    试
        信息 取 _取信息 句柄.
        属性 取 信息 其 读 'attr'.
        链接数 取 (信息 其 读 'links') 其 数.
        戳 取 _信息戳 信息.
        信息 其 关闭.
        若 _属性位 其 已设 属性 14 则 卒 (本地 其 文本 'error.file.efs'). 然
        若 _属性位 其 已设 属性 0 则 卒 (本地 其 文本 'error.file.read_only'). 然
        若 链接数 != 1 则 卒 (本地 其 文本 'error.file.hard_links'). 然
        若 预期stamp != '' 且 戳 != 预期stamp 则
            卒 (本地 其 文本 'error.file.conflict').
        然
    救 原因
        _关句柄 句柄.
        卒 原因.
    终
    # Caller owns this guard handle; close only immediately before replacement.
    得 句柄.
法

算 _安全分配 长存 内存们 为 阵:
    长 取 (长存 其 读 'n') 其 数.
    若 长 == 0 则 得 空. 然
    若 长 > 16777216 则 卒 (本地 其 文本 'error.security.descriptor_limit'). 然
    存 取 密 其 缓冲 长.
    内存们 其 增 存.
    得 存.
法

算 _复制安全属性 路径内存 内存们 为 阵:
    # Capture DACL while the caller still holds the existing-file guard.
    需要 取 _计数型 其 新建.
    内存们 其 增 需要.
    成果 取 _GetFileSecurityW 其 调用 [路径内存,4,空,0,需要].
    若 非 (成果 其 值) 其 为空 或 成果 其 错误码 != 122 则
        _失败 (本地 其 文本 'error.security.dacl_size') 成果.
    然
    长 取 (需要 其 读 'n') 其 数.
    若 长 < 20 或 长 > 16777216 则 卒 (本地 其 文本 'error.security.descriptor_size'). 然
    相对 取 _安全分配 需要 内存们.
    成果 取 _GetFileSecurityW 其 调用 [路径内存,4,相对,长,需要].
    _检查成功 成果 (本地 其 文本 'error.security.dacl_read').
    成果 取 _IsValidSecurityDescriptor 其 调用 [相对].
    _检查成功 成果 (本地 其 文本 'error.security.original_invalid').
    # MakeAbsoluteSD provides owned destinations for every pointer-bearing part.
    主长 取 _计数型 其 新建.
    自主长 取 _计数型 其 新建.
    系统长 取 _计数型 其 新建.
    所有长 取 _计数型 其 新建.
    组长 取 _计数型 其 新建.
    内存们 其 增 主长. 内存们 其 增 自主长. 内存们 其 增 系统长.
    内存们 其 增 所有长. 内存们 其 增 组长.
    成果 取 _MakeAbsoluteSD 其 调用 [相对,空,主长,空,自主长,空,系统长,空,所有长,空,组长].
    若 非 (成果 其 值) 其 为空 或 成果 其 错误码 != 122 则
        _失败 (本地 其 文本 'error.security.layout_compute') 成果.
    然
    绝对 取 _安全分配 主长 内存们.
    若 绝对 == 空 则 卒 (本地 其 文本 'error.security.layout_empty'). 然
    自主 取 _安全分配 自主长 内存们.
    系统存 取 _安全分配 系统长 内存们.
    所有 取 _安全分配 所有长 内存们.
    组 取 _安全分配 组长 内存们.
    成果 取 _MakeAbsoluteSD 其 调用 [相对,绝对,主长,自主,自主长,系统存,系统长,所有,所有长,组,组长].
    _检查成功 成果 (本地 其 文本 'error.security.convert').
    # Only this owned in-memory copy changes; the original file is untouched.
    # SE_DACL_PROTECTED prevents parent ACEs from broadening staging access.
    成果 取 _SetSecurityDescriptorControl 其 调用 [绝对,4096,4096].
    _检查成功 成果 (本地 其 文本 'error.security.inheritance').
    成果 取 _IsValidSecurityDescriptor 其 调用 [绝对].
    _检查成功 成果 (本地 其 文本 'error.security.temporary_invalid').
    属性 取 _安全属性型 其 新建.
    内存们 其 增 属性.
    属性 其 写 'length' (_安全属性型 其 大小).
    属性 其 写 'descriptor' (绝对 其 地址).
    属性 其 写 'inherit' 0.
    得 属性.
法

# Cleanup is shared by begin/step/commit errors and explicit cancellation.
# Recovery-phase failures retain files exactly as the original safe-save path did.
算 _清写状态 状态 原因 为 句:
    若 状态['closed'] 则 得 原因. 然
    _关句柄 状态['tempHandle'].
    _关句柄 状态['targetHandle'].
    状态 其 增 'tempHandle' 空.
    状态 其 增 'targetHandle' 空.
    若 状态['recovery'] 则
        若 状态['tempExists'] 则 原因 取 (本地 其 格式 'error.file.pending_path' ([原因,状态['tempPath']])). 然
        若 状态['backupExists'] 则 原因 取 (本地 其 格式 'error.file.recovery_path' ([原因,状态['backupPath']])). 然
    另
        若 状态['tempExists'] 则
            成果 取 _DeleteFileW 其 调用 [状态['tempMemory']].
            若 (成果 其 值) 其 为空 则
                原因 取 (本地 其 格式 'error.file.temp_cleanup' ([原因,状态['tempPath']])).
            另
                状态 其 增 'tempExists' 假.
            然
        然
        若 状态['backupExists'] 则
            成果 取 _DeleteFileW 其 调用 [状态['backupMemory']].
            若 (成果 其 值) 其 为空 则
                原因 取 (本地 其 格式 'error.file.reserved_cleanup' ([原因,状态['backupPath']])).
            另
                状态 其 增 'backupExists' 假.
            然
        然
    然
    _清内存 状态['memory'].
    状态 其 增 'memory' ([]).
    状态 其 增 'closed' 真.
    得 原因.
法

算 取消写入 状态:
    原因 取 _清写状态 状态 ''.
    若 原因 != '' 则 卒 原因. 然
    得 空.
法

算 准备写入 路径 为 句 编码 为 数 BOM 为 事实 预期stamp 为 句:
    _检查编码 编码 假.
    若 BOM 且 (编码 == CP1252 或 编码 == CP936) 则 卒 (本地 其 文本 'error.codec.legacy_bom'). 然
    路径文 取 _绝对路径 路径.
    状态 取 {'path':路径文,'encoding':编码,'bom':BOM,'expected':预期stamp,'memory':[],'tempHandle':空,'targetHandle':空,'tempMemory':空,'backupMemory':空,'tempPath':'','backupPath':'','tempExists':假,'backupExists':假,'recovery':假,'closed':假,'committed':假,'bytes':0,'chunks':0,'fileIdentity':''}.
    试
        路径存 取 密 其 UTF16 路径文.
        状态['memory'] 其 增 路径存.
        状态 其 增 'pathMemory' 路径存.
        句柄 取 _确认目标 路径存 预期stamp.
        状态 其 增 'targetHandle' 句柄.
        初存 取 句柄 != 空.
        状态 其 增 'originalExists' 初存.
        若 初存 且 预期stamp == '' 则 状态 其 增 'expected' (_句柄戳 句柄). 然
        安全 取 空.
        若 初存 则 安全 取 _复制安全属性 路径存 状态['memory']. 然
        状态 其 增 'security' 安全.
        _关句柄 句柄.
        状态 其 增 'targetHandle' 空.
        进程 取 _GetCurrentProcessId 其 调用 [].
        进程文 取 (进程 其 值) 其 句.
        循 64 次
            _状态 其 增 'sequence' (_状态['sequence']+1).
            临时文 取 路径文+'.ru-notepad-'+进程文+'-'+(_状态['sequence'] 为 句)+'.tmp'.
            候选 取 密 其 UTF16 临时文.
            成果 取 _CreateFileW 其 调用 [候选,1073741824,0,安全,1,128,空].
            句柄 取 成果 其 值.
            若 非 (_无效句柄 句柄) 则
                状态 其 增 'tempHandle' 句柄.
                状态 其 增 'tempMemory' 候选.
                状态 其 增 'tempPath' 临时文.
                状态 其 增 'tempExists' 真.
                状态['memory'] 其 增 候选.
                破.
            然
            候选 其 关闭.
            若 成果 其 错误码 != 80 且 成果 其 错误码 != 183 则 _失败 (本地 其 文本 'error.file.temp_create') 成果. 然
        环
        若 状态['tempHandle'] == 空 则 卒 (本地 其 文本 'error.file.temp_unique'). 然
        计数 取 _计数型 其 新建.
        头 取 _四字节 其 新建.
        状态['memory'] 其 增 计数.
        状态['memory'] 其 增 头.
        状态 其 增 'count' 计数.
        头长 取 0.
        若 BOM 则
            头长 取 2.
            若 编码 == UTF8 则
                头长 取 3.
                头 其 写 'a' 239. 头 其 写 'b' 187. 头 其 写 'c' 191.
            另
                若 编码 == UTF16LE 则
                    头 其 写 'a' 255. 头 其 写 'b' 254.
                另
                    头 其 写 'a' 254. 头 其 写 'b' 255.
                然
            然
        然
        _写完整 状态['tempHandle'] 头 头长 计数.
        状态 其 增 'bytes' 头长.
    救 原因
        卒 (_清写状态 状态 原因).
    终
    得 状态.
法

算 写入一段 状态 文本 为 句:
    若 状态['closed'] 则 卒 (本地 其 文本 'error.file.save_closed'). 然
    数据 取 空.
    试
        编码后 取 _编码数据 文本 状态['encoding'] 假.
        数据 取 编码后['data'].
        _写完整 状态['tempHandle'] 数据 编码后['bytes'] 状态['count'].
        状态 其 增 'bytes' (状态['bytes']+编码后['bytes']).
        状态 其 增 'chunks' (状态['chunks']+1).
        数据 其 关闭.
        数据 取 空.
    救 原因
        若 数据 != 空 则 数据 其 关闭. 然
        卒 (_清写状态 状态 原因).
    终
    得 空.
法

算 完成写入 状态:
    若 状态['closed'] 则 卒 (本地 其 文本 'error.file.save_closed'). 然
    新戳 取 ''.
    试
        _检查成功 (_FlushFileBuffers 其 调用 [状态['tempHandle']]) (本地 其 文本 'error.file.temp_flush').
        成果 取 _CloseHandle 其 调用 [状态['tempHandle']].
        状态 其 增 'tempHandle' 空.
        _检查成功 成果 (本地 其 文本 'error.file.temp_close').
        若 状态['originalExists'] 则
            循 64 次
                _状态 其 增 'sequence' (_状态['sequence']+1).
                候选文 取 状态['tempPath']+'-'+(_状态['sequence'] 为 句)+'.bak'.
                候选 取 密 其 UTF16 候选文.
                成果 取 _CreateFileW 其 调用 [候选,1073741824,0,状态['security'],1,128,空].
                句柄 取 成果 其 值.
                若 非 (_无效句柄 句柄) 则
                    状态 其 增 'backupMemory' 候选.
                    状态 其 增 'backupPath' 候选文.
                    状态 其 增 'backupExists' 真.
                    状态['memory'] 其 增 候选.
                    _关句柄 句柄.
                    破.
                然
                候选 其 关闭.
                若 成果 其 错误码 != 80 且 成果 其 错误码 != 183 则 _失败 (本地 其 文本 'error.file.backup_reserve') 成果. 然
            环
            若 非 状态['backupExists'] 则 卒 (本地 其 文本 'error.file.backup_unique'). 然
            句柄 取 _确认目标 状态['pathMemory'] 状态['expected'].
            状态 其 增 'targetHandle' 句柄.
            _关句柄 句柄.
            状态 其 增 'targetHandle' 空.
            # Same original check/replace race and recovery contract; never fallback.
            成果 取 _ReplaceFileW 其 调用 [状态['pathMemory'],状态['tempMemory'],状态['backupMemory'],0,空,空].
            若 (成果 其 值) 其 为空 则
                状态 其 增 'recovery' 真.
                _失败 (本地 其 文本 'error.file.replace_recovery') 成果.
            然
        另
            若 _检查属性 状态['pathMemory'] 真 则 卒 (本地 其 文本 'error.file.target_created'). 然
            _检查成功 (_MoveFileExW 其 调用 [状态['tempMemory'],状态['pathMemory'],8]) (本地 其 文本 'error.file.target_create').
        然
        状态 其 增 'tempExists' 假.
        状态 其 增 'recovery' 真.
        状态 其 增 'committed' 真.
        试
            句柄 取 _打开读 状态['pathMemory'].
            状态 其 增 'targetHandle' 句柄.
            新戳 取 _句柄戳 句柄.
            信息 取 _取信息 句柄.
            状态['memory'] 其 增 信息.
            状态 其 增 'fileIdentity' ((信息 其 读 'volume') 其 句+':'+(信息 其 读 'idHi') 其 句+':'+(信息 其 读 'idLo') 其 句).
        救 原因
            卒 (本地 其 格式 'error.file.saved_status' ([原因])).
        终
        若 状态['backupExists'] 则
            成果 取 _DeleteFileW 其 调用 [状态['backupMemory']].
            若 (成果 其 值) 其 为空 则 卒 (本地 其 文本 'error.file.backup_cleanup'). 然
            状态 其 增 'backupExists' 假.
        然
        状态 其 增 'recovery' 假.
        状态 其 增 'stamp' 新戳.
    救 原因
        卒 (_清写状态 状态 原因).
    终
    _清写状态 状态 ''.
    得 新戳.
法

算 流写文件 路径 为 句 生产 为 算 编码 为 数 BOM 为 事实 预期stamp 为 句:
    状态 取 准备写入 路径 编码 BOM 预期stamp.
    试
        循
            文 取 生产().
            若 文 == 空 则 破. 然
            写入一段 状态 文.
        环
        新戳 取 完成写入 状态.
    救 原因
        卒 (_清写状态 状态 原因).
    终
    得 新戳.
法

算 写文件 路径 为 句 文本 为 句 编码 为 数 BOM 为 事实 预期stamp 为 句:
    # Compatibility string adapter; no native allocation scales with text length.
    位置 取 [0].
    生产 取 算:
        若 位置[0] >= 文本 其 量 则 得 空. 然
        末 取 位置[0]+最大段字符.
        若 末 > 文本 其 量 则 末 取 文本 其 量. 然
        文 取 文本[位置[0]:末].
        位置[0] 取 末.
        得 文.
    法.
    得 流写文件 路径 生产 编码 BOM 预期stamp.
法

形 文件接口:
    算 读取 路径 为 句 代码页 为 数:
        得 读文件 路径 代码页.
    法
    算 写入 路径 为 句 文本 为 句 编码 为 数 BOM 为 事实 预期stamp 为 句:
        得 写文件 路径 文本 编码 BOM 预期stamp.
    法
象
文件 取 新 文件接口.
