# Real Scintilla + Win32 integration test. Run only as a compiled Windows exe.
密 取 外言 '如:密'.
窗 取 外言 '../src/win32.ru'.
编 取 外言 '../src/editor.ru'.
次数 取 [0].
作 确认 条件 为 事实, 文 为 句:
    若 非 条件 则 卒 ('FAIL: '+文). 然
    次数[0] 取 次数[0]+1.
    显 'PASS: '+文.
为
算 元初 参数 为 句 阵:
    编辑库 取 密 其 动态库 ((窗 其 目录)+'Scintilla.dll').
    实例 取 窗 其 成功 ((窗 其 GetModuleHandleW) 其 调用 [空]) 'instance'.
    # A Windows-provided STATIC top-level parent avoids any fake native host.
    父 取 窗 其 控制 空 实例 'STATIC' 'ru_notepad editor tests' 13565952 0.
    甲 取 编 其 创建 父 实例 1.
    乙 取 编 其 创建 父 实例 2.
    原文 取 '甲😀 alpha\r\nbeta alpha\nfin\r'.
    编 其 设文本 甲 原文.
    编 其 设文本 乙 'independent'.
    确认 ((编 其 文本 甲) == 原文) 'Unicode and mixed EOL exact text'.
    确认 (非 (编 其 已变 甲)) 'load is clean'.
    确认 ((编 其 文本 乙) == 'independent') 'independent document text'.
    窗 其 发送 甲 2160 0 0.
    确认 ((编 其 下个 甲 'alpha' 真) == 8) 'UTF-8 byte offset after Han and emoji'.
    确认 ((窗 其 发送 甲 2145 0 0) 其 数 == 13) 'selection ends at byte boundary'.
    确认 ((编 其 下个 甲 'alpha' 真) == 20) 'find next occurrence'.
    确认 ((编 其 下个 甲 'alpha' 真) == 8) 'find wraps'.
    确认 ((编 其 下个 甲 'ALPHA' 真) == -1) 'case-sensitive no match'.
    确认 ((编 其 下个 甲 'ALPHA' 假) == 20) 'case-insensitive match'.
    确认 ((编 其 全换 甲 'alpha' 'Ω' 真) == 2) 'replace all count'.
    确认 ((编 其 文本 甲) == '甲😀 Ω\r\nbeta Ω\nfin\r') 'replace all exact result'.
    确认 (编 其 已变 甲) 'edit becomes dirty'.
    窗 其 发送 甲 2176 0 0.
    确认 ((编 其 文本 甲) == 原文) 'one undo restores entire replace-all'.
    确认 (非 (编 其 已变 甲)) 'undo to savepoint is clean'.
    窗 其 发送 甲 2011 0 0.
    确认 (编 其 已变 甲) 'redo becomes dirty'.
    编 其 记保存 甲.
    确认 (非 (编 其 已变 甲)) 'savepoint clears dirty'.
    确认 ((编 其 文本 乙) == 'independent') 'other document and undo stay unchanged'.
    编 其 设文本 甲 'aaa'.
    确认 ((编 其 全换 甲 'a' '' 真) == 3) 'deletion replacement terminates'.
    确认 ((编 其 文本 甲) == '') 'deletion replacement exact'.
    编 其 设文本 甲 'aa'.
    确认 ((编 其 全换 甲 'a' 'aa' 真) == 2) 'expanding replacement does not revisit insertions'.
    确认 ((编 其 文本 甲) == 'aaaa') 'expanding replacement exact'.
    编 其 设文本 甲 'x\ny'.
    确认 ((窗 其 发送 甲 2030 0 0) 其 数 == 2) 'LF insertion mode retained'.
    编 其 设文本 甲 'x\ry'.
    确认 ((窗 其 发送 甲 2030 0 0) 其 数 == 1) 'CR insertion mode retained'.
    编 其 设文本 甲 'x\r\ny'.
    确认 ((窗 其 发送 甲 2030 0 0) 其 数 == 0) 'CRLF insertion mode retained'.
    编 其 设文本 甲 ''.
    字节型 取 密 其 结构 [['a',密 其 u8],['b',密 其 u8],['c',密 其 u8]].
    零文 取 字节型 其 新建.
    零文 其 写 'a' 65.
    零文 其 写 'b' 0.
    零文 其 写 'c' 66.
    窗 其 发指 甲 2001 3 零文.
    零文 其 关闭.
    拒绝 取 [假].
    试
        编 其 文本 甲.
    救 原因
        拒绝[0] 取 真.
    终
    确认 拒绝[0] 'embedded NUL blocks extraction instead of truncating'.
    确认 ((窗 其 发送 甲 2183 0 0) 其 数 == 3) 'NUL rejection preserves full native document'.
    确认 (编 其 已变 甲) 'NUL rejection leaves document dirty'.
    窗 其 成功 ((窗 其 DestroyWindow) 其 调用 [父]) 'DestroyWindow'.
    显 'TOTAL PASS: '+(次数[0] 为 句).
    得 0.
法
