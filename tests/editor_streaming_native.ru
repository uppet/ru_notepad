# Real Windows x64 Scintilla acceptance. Existing disposable directory required.
# Optional --large runs the mandatory separate >500,000,000-byte acceptance mode.
密 取 外言 '如:密'.
窗 取 外言 '../src/win32.ru'.
编 取 外言 '../src/editor.ru'.
文件库 取 外言 '../src/file_codec.ru'.
辅 取 外言 './file_streaming_native.ru'.
统计 取 [0].

作 确认 条件 为 事实 文 为 句:
    若 非 条件 则 卒 'FAIL: '+文. 然
    统计[0] 取 统计[0]+1.
    显 'PASS: '+文.
为

算 接受 大小 为 数:
    得 真.
法

作 删除 路 为 句:
    存 取 密 其 UTF16 路.
    (辅 其 Delete) 其 调用 [存].
    存 其 关闭.
为

算 载入 柄 路 为 句 确认函 为 算:
    读态 取 文件库 其 准备读取 路 0.
    试
        若 非 (文件库 其 确认读取 读态 确认函) 则 得 空. 然
        载态 取 编 其 开始载入 柄 读态['size'].
        循
            文 取 文件库 其 读取一步 读态.
            若 文 == 空 则 破. 然
            编 其 追加文本 载态 文.
        环
        编 其 完成载入 载态.
    救 原因
        文件库 其 关闭读取 读态.
        卒 原因.
    终
    得 读态.
法

算 保存 柄 路 为 句 预期 为 句:
    写态 取 文件库 其 准备写入 路 65001 假 预期.
    源 取 编 其 开始取文 柄.
    窗 其 发送 柄 2171 1 0.
    试
        循
            文 取 编 其 取文一步 源.
            若 文 == 空 则 破. 然
            文件库 其 写入一段 写态 文.
        环
        戳 取 文件库 其 完成写入 写态.
    救 原因
        窗 其 发送 柄 2171 0 0.
        文件库 其 取消写入 写态.
        卒 原因.
    终
    窗 其 发送 柄 2171 0 0.
    编 其 记保存 柄.
    得 {'stamp':戳,'bytes':写态['bytes'],'chunks':写态['chunks']}.
法

作 基础测试 父 实例 根 为 句:
    柄 取 编 其 创建 父 实例 1.
    其他 取 编 其 创建 父 实例 2.
    编 其 设文本 其他 'unchanged document'.
    尾 取 (窗 其 发送 其他 2183 0 0) 其 数.
    窗 其 发送 其他 2160 尾 尾.
    窗 其 发文 其他 2001 1 '!'.
    流 取 编 其 开始载入 柄 0.
    编 其 追加文本 流 '甲😀x\r'.
    编 其 追加文本 流 '\ny'.
    编 其 完成载入 流.
    确认 ((编 其 文本 柄) == '甲😀x\r\ny') 'stream load preserves supplementary Unicode and CR|LF'.
    确认 ((窗 其 发送 柄 2030 0 0) 其 数 == 0) 'split CRLF selects CRLF insertion mode'.
    确认 ((窗 其 发送 柄 2379 0 0) 其 数 == 256) 'normal document uses 64-bit TEXT_LARGE positions'.
    确认 (非 (编 其 已变 柄)) 'completed streaming load is clean'.
    确认 ((窗 其 发送 柄 2019 0 0) 其 数 == 1) 'completed streaming load restores undo collection'.
    确认 ((编 其 文本 其他) == 'unchanged document!' 且 (编 其 已变 其他)) 'other tab content and dirty state survive streaming load'.
    填 取 辅 其 重复 'a' 65535.
    文 取 填+'😀终'.
    编 其 设文本 柄 文.
    源 取 编 其 开始取文 柄.
    首 取 编 其 取文一步 源.
    次文 取 编 其 取文一步 源.
    确认 (首 == 填 且 次文 == '😀终') 'GETTEXTRANGEFULL rounds down across four-byte UTF-8 boundary'.
    确认 ((编 其 取文一步 源) == 空) 'bounded editor producer ends exactly at EOF'.
    源 取 编 其 开始取文 柄.
    窗 其 发文 柄 2001 1 '!'.
    拒 取 [假].
    试 编 其 取文一步 源. 救 原因 拒[0] 取 真. 终
    确认 拒[0] 'producer refuses changed document length'.
    确认 (编 其 已变 柄) 'producer failure retains dirty state'.
    # 16,908,288 bytes: both historical 4 MiB and FFI 16 MiB boundaries exceeded.
    路 取 根+'normal-source.txt'.
    出 取 根+'normal-saved.txt'.
    首块 取 填+'\r'.
    次块 取 '\n'+填.
    首存 取 密 其 UTF8 首块.
    次存 取 密 其 UTF8 次块.
    段们 取 [(辅 其 原段 首存 65536 1),(辅 其 原段 次存 65536 257)].
    辅 其 写原生段 路 段们.
    已读 取 载入 柄 路 (算 接受).
    确认 (已读['size'] == 16908288 且 已读['textBytes'] == 16908288) 'real editor loads a file larger than 16 MiB'.
    确认 ((窗 其 发送 柄 2183 0 0) 其 数 == 16908288) 'native Scintilla owns every large-file byte'.
    确认 ((窗 其 发送 柄 2030 0 0) 其 数 == 0) '64 KiB file boundary CR|LF remains CRLF'.
    确认 (非 (编 其 已变 柄)) 'large streamed load is clean'.
    已存 取 保存 柄 出 ''.
    确认 (已存['bytes'] == 16908288 且 已存['chunks'] > 256) 'real editor saves more than 16 MiB through bounded ranges'.
    辅 其 验原生段 出 段们 'every >16 MiB native-editor output byte matches input'.
    确认 (非 (编 其 已变 柄)) 'successful streamed save reaches savepoint'.
    确认 ((编 其 文本 其他) == 'unchanged document!' 且 (编 其 已变 其他)) 'other document survives large save unchanged'.
    # Inject a NUL directly into Scintilla; failed save must not replace original.
    编 其 设文本 柄 'new'.
    零存 取 辅 其 字节结构 ([0]).
    窗 其 发指 柄 2001 1 零存.
    零存 其 关闭.
    拒[0] 取 假.
    试 保存 柄 出 已存['stamp']. 救 原因 拒[0] 取 真. 终
    确认 拒[0] 'native NUL refuses streamed save'.
    确认 (编 其 已变 柄) 'failed streamed save retains editor dirty state'.
    辅 其 验原生段 出 段们 'failed native-editor save preserves every original byte'.
    首存 其 关闭.
    次存 其 关闭.
    删除 路.
    删除 出.
为

作 超大测试 父 实例 根 为 句:
    柄 取 编 其 创建 父 实例 3.
    路 取 根+'large-source.txt'.
    出 取 根+'large-saved.txt'.
    # Real text, not a sparse NUL hole: all 500,039,680 bytes are read and saved.
    块 取 (辅 其 重复 'a' 65535)+'\n'.
    存 取 密 其 UTF8 块.
    段们 取 [(辅 其 原段 存 65536 7630)].
    辅 其 写原生段 路 段们.
    确认 (65536*7630 > 500000000) 'large fixture exceeds the decimal 500 MB warning threshold'.
    探 取 文件库 其 准备读取 路 0.
    确认 (探['readCalls'] == 0 且 探['readBytes'] == 0 且 探['bufferBytes'] == 0) 'large editor preflight has no body read or data buffer'.
    询 取 [0].
    批准 取 算 大小 为 数:
        若 大小 != 500039680 则 卒 'unexpected large fixture size'. 然
        若 探['readCalls'] != 0 则 卒 'body read before confirmation'. 然
        询[0] 取 询[0]+1.
        得 真.
    法.
    确认 (文件库 其 确认读取 探 批准) 'approved >500 MB operation proceeds'.
    确认 (询[0] == 1 且 探['readCalls'] == 0) 'large warning is exactly once and precedes ReadFile'.
    流 取 编 其 开始载入 柄 探['size'].
    确认 ((窗 其 发送 柄 2379 0 0) 其 数 == 257) 'large native document uses TEXT_LARGE plus STYLES_NONE'.
    循
        文 取 文件库 其 读取一步 探.
        若 文 == 空 则 破. 然
        编 其 追加文本 流 文.
    环
    编 其 完成载入 流.
    确认 (探['done'] 且 探['closed'] 且 探['textBytes'] == 500039680) 'approved real >500 MB load completes its snapshot and EOF checks'.
    确认 ((窗 其 发送 柄 2183 0 0) 其 数 == 500039680 且 非 (编 其 已变 柄)) 'complete >500 MB Scintilla document is retained clean'.
    已存 取 保存 柄 出 ''.
    确认 (已存['bytes'] == 500039680 且 已存['chunks'] >= 7630) 'complete >500 MB document saves through bounded native ranges'.
    辅 其 验原生段 出 段们 'every accepted >500 MB editor roundtrip byte matches'.
    确认 (非 (编 其 已变 柄)) 'accepted >500 MB save commits the savepoint'.
    存 其 关闭.
    删除 路.
    删除 出.
为

算 元初 参数 为 句 阵:
    若 参数 其 量 < 1 或 参数 其 量 > 2 则 显 'Usage: editor_streaming_native.exe EXISTING_DISPOSABLE_DIRECTORY [--large]'. 得 2. 然
    大 取 参数 其 量 == 2.
    若 大 且 参数[1] != '--large' 则 卒 'Unknown editor streaming test mode.'. 然
    编辑库 取 密 其 动态库 ((窗 其 目录)+'Scintilla.dll').
    实例 取 窗 其 成功 ((窗 其 GetModuleHandleW) 其 调用 [空]) 'instance'.
    父 取 窗 其 控制 空 实例 'STATIC' 'ru_notepad streaming editor tests' 13565952 0.
    根 取 参数[0]+'\\ru-editor-stream-'.
    试
        若 大 则 超大测试 父 实例 根. 另 基础测试 父 实例 根. 然
    救 原因
        窗 其 结果 ((窗 其 DestroyWindow) 其 调用 [父]).
        删除 (根+'normal-source.txt').
        删除 (根+'normal-saved.txt').
        删除 (根+'large-source.txt').
        删除 (根+'large-saved.txt').
        卒 原因.
    终
    窗 其 成功 ((窗 其 DestroyWindow) 其 调用 [父]) 'DestroyWindow'.
    总 取 统计[0]+(辅 其 统计)[0].
    若 大 则 显 'EDITOR_LARGEFILE_TESTS_PASS='+(总 为 句). 另 显 'EDITOR_STREAMING_TESTS_PASS='+(总 为 句). 然
    得 0.
法
