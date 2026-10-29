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
    # Literal search options operate in UTF-8 byte positions in either direction.
    编 其 设文本 甲 原文.
    窗 其 发送 甲 2160 25 20.
    确认 ((编 其 寻找 甲 'alpha' 真 假 假 真) == 8) 'previous uses selection start even for reverse selection'.
    确认 ((窗 其 发送 甲 2143 0 0) 其 数 == 8) 'previous match starts at complete UTF-8 boundary'.
    确认 ((窗 其 发送 甲 2145 0 0) 其 数 == 13) 'previous match ends at complete UTF-8 boundary'.
    确认 ((编 其 寻找 甲 'alpha' 真 假 假 真) == -1) 'previous without wrap stops at start'.
    确认 ((窗 其 发送 甲 2143 0 0) 其 数 == 8) 'failed previous preserves selection start'.
    确认 ((窗 其 发送 甲 2145 0 0) 其 数 == 13) 'failed previous preserves selection end'.
    确认 ((编 其 寻找 甲 'alpha' 真 假 真 真) == 20) 'previous wraps to final match'.
    确认 ((编 其 寻找 甲 'alpha' 真 假 假 假) == -1) 'next without wrap stops at end'.
    确认 ((编 其 寻找 甲 'alpha' 真 假 真 假) == 8) 'next with wrap retains legacy behavior'.
    窗 其 发送 甲 2160 13 8.
    确认 ((编 其 寻找 甲 'alpha' 真 假 假 假) == 20) 'next uses selection end for reverse selection'.
    窗 其 发送 甲 2160 25 20.
    确认 ((编 其 寻找 甲 'missing' 真 假 真 真) == -1) 'previous no match returns minus one'.
    确认 ((窗 其 发送 甲 2008 0 0) 其 数 == 20) 'failed search preserves reverse caret'.
    确认 ((窗 其 发送 甲 2009 0 0) 其 数 == 25) 'failed search preserves reverse anchor'.
    确认 ((编 其 文本 甲) == 原文) 'direction and wrap searches preserve mixed EOL bytes'.
    确认 (非 (编 其 已变 甲)) 'direction and wrap searches preserve clean savepoint'.
    确认 ((窗 其 发送 甲 2174 0 0) 其 数 == 0) 'search does not add undo history'.
    空拒 取 [假].
    试 编 其 寻找 甲 '' 真 假 真 真. 救 原因 空拒[0] 取 真. 终
    确认 空拒[0] 'empty search is rejected'.
    确认 ((窗 其 发送 甲 2008 0 0) 其 数 == 20) 'empty rejection preserves caret'.
    确认 ((窗 其 发送 甲 2009 0 0) 其 数 == 25) 'empty rejection preserves anchor'.
    确认 ((编 其 文本 甲) == 原文) 'empty rejection preserves exact bytes'.
    编 其 设文本 甲 ''.
    确认 ((编 其 寻找 甲 'alpha' 真 真 真 真) == -1) 'empty document backward search terminates'.
    确认 ((编 其 寻找 甲 'alpha' 真 真 真 假) == -1) 'empty document forward search terminates'.
    编 其 设文本 甲 'alpha'.
    窗 其 发送 甲 2160 0 5.
    确认 ((编 其 寻找 甲 'alpha' 真 假 真 假) == 0) 'single occurrence forward wrap reselects current match'.
    确认 ((编 其 寻找 甲 'alpha' 真 假 真 真) == 0) 'single occurrence backward wrap reselects current match'.
    确认 ((编 其 寻找 甲 'alpha' 真 假 假 假) == -1) 'single occurrence forward without wrap does not reselect'.
    确认 ((编 其 寻找 甲 'alpha' 真 假 假 真) == -1) 'single occurrence backward without wrap does not reselect'.
    窗 其 发送 甲 2160 5 5.
    确认 ((编 其 寻找 甲 'alpha' 真 假 假 假) == -1) 'EOF caret forward without wrap reports no match'.
    确认 ((窗 其 发送 甲 2008 0 0) 其 数 == 5) 'EOF miss retains EOF caret'.
    确认 ((编 其 寻找 甲 'alpha' 真 假 假 真) == 0) 'EOF caret backward without wrap finds preceding word'.
    窗 其 发送 甲 2160 5 5.
    确认 ((编 其 寻找 甲 'alpha' 真 假 真 假) == 0) 'EOF caret forward with wrap finds first word'.
    窗 其 发送 甲 2160 0 0.
    确认 ((编 其 寻找 甲 'alpha' 真 假 假 真) == -1) 'start caret backward without wrap reports no match'.
    确认 ((窗 其 发送 甲 2008 0 0) 其 数 == 0) 'start miss retains start caret'.
    确认 ((编 其 寻找 甲 'alpha' 真 假 真 真) == 0) 'start caret backward with wrap finds final word'.
    窗 其 发送 甲 2160 0 0.
    确认 ((编 其 寻找 甲 'alpha' 真 假 假 假) == 0) 'start caret forward without wrap finds first word'.
    编 其 设文本 甲 'a anything [a].* z'.
    窗 其 发送 甲 2160 0 0.
    确认 ((编 其 寻找 甲 '[a].*' 真 假 假 假) == 11) 'regex-looking pattern is searched literally'.
    确认 ((窗 其 发送 甲 2145 0 0) 其 数 == 16) 'literal regex-looking match has exact five-byte extent'.
    确认 ((编 其 全换选项 甲 '[a].*' '$1' 真 假) == 1) 'regex-looking replacement counts one literal match'.
    确认 ((编 其 文本 甲) == 'a anything $1 z') 'replacement dollar expression remains literal'.
    窗 其 发送 甲 2176 0 0.
    确认 ((编 其 文本 甲) == 'a anything [a].* z') 'literal-pattern replacement remains one undo operation'.
    编 其 设文本 甲 'é 😀 é'.
    窗 其 发送 甲 2160 0 0.
    确认 ((编 其 寻找 甲 'é' 真 假 假 假) == 0) 'combining-sequence first match starts at byte zero'.
    确认 ((编 其 寻找 甲 'é' 真 假 假 假) == 9) 'combining-sequence next match uses byte offset'.
    确认 ((编 其 寻找 甲 'é' 真 假 假 真) == 0) 'combining-sequence previous match preserves complete sequence'.
    确认 ((编 其 寻找 甲 '😀' 真 假 假 假) == 4) 'emoji search locates a complete four-byte scalar'.
    确认 ((窗 其 发送 甲 2145 0 0) 其 数 == 8) 'emoji selection does not split its UTF-8 bytes'.
    词文 取 'alpha alphabet alpha_beta beta-alpha ALPHA alpha'.
    编 其 设文本 甲 词文.
    窗 其 发送 甲 2160 0 0.
    确认 ((编 其 寻找 甲 'alpha' 真 真 假 假) == 0) 'whole-word includes word at start'.
    确认 ((编 其 寻找 甲 'alpha' 真 真 假 假) == 31) 'whole-word skips alphabet and underscore word but accepts punctuation boundary'.
    确认 ((编 其 寻找 甲 'alpha' 真 真 假 假) == 43) 'whole-word case-sensitive skips uppercase and includes EOF'.
    确认 ((编 其 寻找 甲 'alpha' 假 真 假 真) == 37) 'whole-word backward honors case-insensitive option'.
    确认 ((编 其 寻找 甲 'alpha' 真 真 假 真) == 31) 'whole-word backward honors case-sensitive option'.
    窗 其 发送 甲 2160 5 0.
    确认 ((编 其 全换选项 甲 'alpha' 'Ω' 真 真) == 3) 'whole-word replace-all only replaces three eligible matches'.
    确认 ((编 其 文本 甲) == 'Ω alphabet alpha_beta beta-Ω ALPHA Ω') 'whole-word replace-all preserves partial words and case'.
    窗 其 发送 甲 2176 0 0.
    确认 ((编 其 文本 甲) == 词文) 'one undo restores whole-word replace-all'.
    确认 (非 (编 其 已变 甲)) 'whole-word replace-all undo restores savepoint'.
    确认 ((编 其 文本 乙) == 'independent') 'search options and replacement leave other document unchanged'.
    确认 ((编 其 全换选项 甲 'missing' 'X' 真 真) == 0) 'no-match replace-all reports zero'.
    确认 (非 (编 其 已变 甲)) 'no-match replace-all preserves savepoint'.
    空拒[0] 取 假.
    试 编 其 全换选项 甲 '' 'X' 真 真. 救 原因 空拒[0] 取 真. 终
    确认 空拒[0] 'empty replace-all pattern is rejected'.
    确认 ((编 其 文本 甲) == 词文) 'empty replace-all rejection preserves bytes'.
    窗 其 发送 甲 2160 6 11.
    确认 ((编 其 换当前选项 甲 'alpha' 'X' 真 真 假) == 31) 'whole-word replace-current refuses partial word and finds next'.
    确认 ((编 其 文本 甲) == 词文) 'refused partial-word replacement preserves bytes'.
    确认 ((编 其 换当前选项 甲 'alpha' 'X' 真 真 假) == 39) 'replace-current applies whole-word match and advances without wrap'.
    确认 ((编 其 文本 甲) == 'alpha alphabet alpha_beta beta-X ALPHA alpha') 'replace-current changes only selected whole word'.
    窗 其 发送 甲 2176 0 0.
    确认 ((编 其 文本 甲) == 词文) 'replace-current is undoable'.
    编 其 设文本 甲 'a a'.
    确认 ((编 其 全换选项 甲 'a' 'aa' 真 真) == 2) 'whole-word expanding replace-all does not revisit insertion'.
    确认 ((编 其 文本 甲) == 'aa aa') 'whole-word expanding replacement exact bytes'.
    窗 其 发送 甲 2176 0 0.
    确认 ((编 其 文本 甲) == 'a a') 'expanding whole-word replacement has one undo group'.
    确认 ((编 其 全换选项 甲 'a' '' 真 真) == 2) 'whole-word deletion replacement terminates'.
    确认 ((编 其 文本 甲) == ' ') 'whole-word deletion preserves separator'.
    编 其 设文本 甲 'head\nneedle\nend'.
    窗 其 发送 甲 2222 0 9216. # SC_FOLDLEVELBASE | SC_FOLDLEVELHEADERFLAG
    窗 其 发送 甲 2222 1 1025.
    窗 其 发送 甲 2222 2 1024.
    窗 其 发送 甲 2229 0 0.
    窗 其 发送 甲 2227 1 1.
    确认 ((窗 其 发送 甲 2228 1 0) 其 数 == 0) 'search fixture begins with hidden fold child'.
    窗 其 发送 甲 2160 0 0.
    确认 ((编 其 寻找 甲 'needle' 真 假 假 假) == 5) 'forward search finds hidden fold child'.
    确认 ((窗 其 发送 甲 2228 1 0) 其 数 == 1) 'forward match expands its hidden fold child'.
    窗 其 发送 甲 2229 0 0.
    窗 其 发送 甲 2227 1 1.
    窗 其 发送 甲 2160 15 15.
    确认 ((编 其 寻找 甲 'needle' 真 假 假 真) == 5) 'backward search finds hidden fold child'.
    确认 ((窗 其 发送 甲 2228 1 0) 其 数 == 1) 'backward match expands its hidden fold child'.
    确认 ((编 其 文本 甲) == 'head\nneedle\nend') 'search visibility changes preserve text bytes'.
    确认 (非 (编 其 已变 甲)) 'search visibility changes preserve clean savepoint'.
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
