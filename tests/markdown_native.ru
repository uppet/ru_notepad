# Windows x64 acceptance SOURCE, not a claim of execution under Linux/Wine.
# Uses actual Scintilla and Lexilla, but deliberately avoids importing the large
# application/Ru scanner graph. Parent syntax/main integration has separate gates.
密 取 外言 '如:密'.
窗 取 外言 '../src/win32.ru'.
编 取 外言 '../src/editor.ru'.
折 取 外言 '../src/markdown_syntax.ru'.
次数 取 [0].
路由 取 {}.
替文 取 '# Replacement\nbody\n'.
通知型 取 密 其 结构 [['header',窗 其 NMHDR],['position',窗 其 IP],['ch',窗 其 I],['modifiers',窗 其 I],['modificationType',窗 其 I],['text',窗 其 PTR],['length',窗 其 IP],['linesAdded',窗 其 IP]].
_SetWindowSubclass 取 (窗 其 控件) 其 绑定 'SetWindowSubclass' (密 其 签名 (窗 其 I) ([(窗 其 PTR),(窗 其 PTR),(窗 其 UP),(窗 其 UP)]) 'win64').
_RemoveWindowSubclass 取 (窗 其 控件) 其 绑定 'RemoveWindowSubclass' (密 其 签名 (窗 其 I) ([(窗 其 PTR),(窗 其 PTR),(窗 其 UP)]) 'win64').
_DefSubclassProc 取 (窗 其 控件) 其 绑定 'DefSubclassProc' (密 其 签名 (窗 其 IP) ([(窗 其 PTR),(窗 其 U),(窗 其 UP),(窗 其 IP)]) 'win64').
_子型 取 密 其 签名 (窗 其 IP) ([(窗 其 PTR),(窗 其 U),(窗 其 UP),(窗 其 IP),(窗 其 UP),(窗 其 UP)]) 'win64'.
词法库 取 密 其 动态库 ((窗 其 目录)+'Lexilla.dll').
CreateLexer 取 词法库 其 绑定 'CreateLexer' (密 其 签名 (窗 其 PTR) ([(窗 其 PTR)]) 'win64').
作 确认 条件 为 事实 文 为 句:
    若 非 条件 则 卒 ('FAIL: '+文). 然
    次数[0] 取 次数[0]+1.
    显 'PASS: '+文.
为
算 过程 柄 消息 宽 长:
    若 消息 其 数 == 78 则
        项 取 通知型 其 新建.
        窗 其 结果 ((窗 其 RtlMoveMemory) 其 调用 [项,((窗 其 PTR) 其 重释 长),通知型 其 大小]).
        头 取 项 其 读 'header'.
        若 (头 其 读 'code') 其 数 == 2008 则
            类 取 (项 其 读 'modificationType') 其 数.
            若 类 % 4 != 0 则 折 其 变化 (头 其 读 'hwndFrom') ((项 其 读 'position') 其 数) ((项 其 读 'length') 其 数) ((项 其 读 'linesAdded') 其 数) 类. 然
        然
        项 其 关闭.
        得 0.
    然
    得 窗 其 结果 ((窗 其 DefWindowProcW) 其 调用 [柄,消息,宽,长]).
法
算 安装 柄:
    名存 取 密 其 UTF8 'markdown'.
    词法器 取 窗 其 结果 (CreateLexer 其 调用 [名存]).
    名存 其 关闭.
    若 词法器 其 为空 则 卒 'Pinned Lexilla lacks Markdown.'. 然
    窗 其 发送 柄 4033 0 ((窗 其 IP) 其 重释 词法器).
    键 取 密 其 UTF8 'fold'.
    值 取 密 其 UTF8 '0'.
    窗 其 发指 柄 4004 ((窗 其 UP) 其 重释 (键 其 地址)) 值.
    键 其 关闭. 值 其 关闭.
    窗 其 发送 柄 2692 1 0.
    得 折 其 选择 柄.
法
算 准备 柄 文 为 句:
    折 其 停用 柄.
    编 其 设文本 柄 文.
    得 安装 柄.
法
算 计数 柄:
    计 取 {'fold':0,'foldLine':0,'fullLine':0,'query':0,'target':0,'action':'','fired':假,'replaceStopFold':0,'invalidateAt':0,'postTarget':2357}.
    路由 其 增 (柄 其 句) 计.
    得 计.
法
算 子过程 柄 消息 宽 长 号 引:
    计 取 路由 其 查 (柄 其 句).
    码 取 消息 其 数.
    若 计 != 空 则
        若 码 == 2222 则 计 其 增 'fold' (计['fold']+1). 然
        若 码 == 2237 则 计 其 增 'foldLine' (计['foldLine']+1). 然
        若 码 == 2153 则 计 其 增 'fullLine' (计['fullLine']+1). 然
        若 码 == 2357 或 码 == 2183 或 码 == 2154 或 码 == 2039 或 码 == 2417 则 计 其 增 'query' (计['query']+1). 然
        若 码 == 计['target'] 且 计['action'] != '' 则
            动作 取 计['action'].
            计 其 增 'action' ''.
            计 其 增 'fired' 真.
            # Injection is confined to READ messages. No fixture or production
            # subclass swaps the document while forwarding a mutating message.
            若 动作 == 'replace' 则
                折 其 遗忘 柄.
                流 取 编 其 开始载入 柄 0.
                编 其 追加文本 流 替文.
                编 其 完成载入 流.
                安装 柄.
                折 其 排空 柄.
                折 其 全折 柄 0.
                计 其 增 'replaceStopFold' 计['fold'].
            然
            若 动作 == 'language' 则
                折 其 停用 柄.
                窗 其 发送 柄 4033 0 0.
            然
            若 动作 == 'edit' 则
                窗 其 发送 柄 2160 0 0.
                窗 其 发文 柄 2170 0 '# inserted\n'.
            然
        然
    然
    果 取 窗 其 结果 (_DefSubclassProc 其 调用 [柄,消息,宽,长]).
    若 计 != 空 且 码 == 2222 且 计['action'] == 'replace-after-fold-query' 则
        # Arm the next READ only after the native fold mutation returned.
        计 其 增 'target' 计['postTarget'].
        计 其 增 'action' 'replace'.
    然
    若 计 != 空 且 码 == 2222 且 计['action'] == 'invalidate-after-fold' 且 (计['invalidateAt'] == 0 或 计['fold'] == 计['invalidateAt']) 则
        计 其 增 'action' ''.
        计 其 增 'fired' 真.
        # The native mutation has returned. Invalidate memory only; do not swap
        # a document from inside any mutating window-message dispatch.
        折 其 遗忘 柄.
    然
    得 果.
法
算 全显 柄:
    行数 取 (窗 其 发送 柄 2154 0 0) 其 数.
    行 取 0.
    循 行数 次
        若 (窗 其 发送 柄 2228 行 0) 其 数 != 1 则 得 假. 然
        行 取 行+1.
    环
    得 真.
法
算 全展开 柄:
    行数 取 (窗 其 发送 柄 2154 0 0) 其 数.
    行 取 0.
    循 行数 次
        若 (窗 其 发送 柄 2230 行 0) 其 数 != 1 则 得 假. 然
        行 取 行+1.
    环
    得 真.
法
算 同折 甲 乙:
    若 (编 其 文本 甲) != (编 其 文本 乙) 则 得 假. 然
    行数 取 (窗 其 发送 甲 2154 0 0) 其 数.
    若 (窗 其 发送 乙 2154 0 0) 其 数 != 行数 则 得 假. 然
    行 取 0.
    循 行数 次
        若 (窗 其 发送 甲 2223 行 0) 其 数 != (窗 其 发送 乙 2223 行 0) 其 数 则 得 假. 然
        行 取 行+1.
    环
    得 真.
法
作 验层 柄 层们 名 为 句:
    合 取 (窗 其 发送 柄 2154 0 0) 其 数 == 层们 其 量.
    位 取 0.
    循 层们 其 量 次
        若 (窗 其 发送 柄 2223 位 0) 其 数 != 层们[位] 则 合 取 假. 然
        位 取 位+1.
    环
    确认 合 名.
为
作 拒旧 柄 旧 计 名 为 句:
    前 取 计['fold'].
    拒 取 [假].
    试 折 其 _发布 柄 旧. 救 原因 拒[0] 取 真. 终
    确认 (拒[0] 且 计['fold'] == 前) 名.
为
算 元初 参数 为 句 阵:
    库 取 密 其 动态库 ((窗 其 目录)+'Scintilla.dll').
    实例 取 窗 其 成功 ((窗 其 GetModuleHandleW) 其 调用 [空]) 'instance'.
    类名 取 密 其 UTF16 'RuNotepad.MarkdownFixture'.
    回调 取 密 其 回调 (窗 其 WNDPROC) (算 过程) 0.
    子回调 取 密 其 回调 _子型 (算 子过程) 0.
    类 取 (窗 其 WNDCLASS) 其 新建.
    类 其 写 'size' ((窗 其 WNDCLASS) 其 大小).
    类 其 写 'proc' (回调 其 地址).
    类 其 写 'instance' 实例.
    类 其 写 'name' (类名 其 地址).
    窗 其 成功 ((窗 其 RegisterClassExW) 其 调用 [类]) 'register Markdown fixture'.
    父 取 窗 其 控制 空 实例 'RuNotepad.MarkdownFixture' 'Markdown acceptance' 13565952 0.
    甲 取 编 其 创建 父 实例 1.
    乙 取 编 其 创建 父 实例 2.
    窗 其 成功 (_SetWindowSubclass 其 调用 [甲,子回调 其 地址,918,0]) 'subclass first editor'.
    窗 其 成功 (_SetWindowSubclass 其 调用 [乙,子回调 其 地址,918,0]) 'subclass second editor'.
    甲计 取 计数 甲. 乙计 取 计数 乙.
    文 取 '# 甲😀\nbody\n## next\nchild\n'.
    确认 ((准备 甲 文) == 'markdown') 'Markdown lexer and independent fold owner register'.
    窗 其 发送 甲 2160 2 9.
    态 取 折 其 排空 甲.
    # Explicit full colourisation is test-only. The bridge never calls it.
    窗 其 发送 甲 4003 0 (-1).
    确认 ((窗 其 发送 甲 4002 0 0) 其 数 == 98 且 (窗 其 发送 甲 2038 0 0) 其 数 == 6 且 (窗 其 发送 甲 2038 2 0) 其 数 == 0 且 (窗 其 发送 甲 2038 8 0) 其 数 == 0) 'pinned default Lexilla styles the heading marker and keeps Unicode body bytes default'.
    验层 甲 ([9216,1025,9217,1026,1026]) 'ATX nesting assigns every native fold line including trailing empty line'.
    确认 (态['enabled'] 且 态['foldEnabled'] 且 非 态['pending'] 且 态['eof'] 且 态['queuedRanges'] == 0 且 态['feed'] == (折 其 _字节 文)) 'pending clears only after EOF and all publication ranges drain'.
    确认 ((编 其 文本 甲) == 文 且 非 (编 其 已变 甲) 且 (窗 其 发送 甲 2174 0 0) 其 为空 且 (窗 其 发送 甲 2009 0 0) 其 数 == 2 且 (窗 其 发送 甲 2008 0 0) 其 数 == 9) 'folding preserves exact Unicode bytes, clean savepoint, empty undo and byte selection'.
    确认 (折 其 折叠 甲 15) 'UTF-8 byte position15 toggles the second heading'.
    确认 ((窗 其 发送 甲 2228 3 0) 其 数 == 0 且 (编 其 文本 甲) == 文) 'native collapsed children retain all source text'.
    折 其 全折 甲 1.
    确认 (全显 甲) 'native expand restores all logical lines'.

    设文 取 'title\r\nsecond\r\n---\r\nbody\r\n# stop\r\nx'.
    准备 甲 设文. 折 其 排空 甲.
    验层 甲 ([9216,1025,1025,1025,9216,1025]) 'multiline Setext retroheader and CRLF assign all native lines'.
    隔文 取 '# top\n```\n# fake\n```\n<!--\n# fake\n-->\n# next\nbody'.
    准备 甲 隔文. 折 其 排空 甲.
    验层 甲 ([9216,1025,1025,1025,1025,1025,1025,9216,1025]) 'fence and HTML headings never become native fold headers'.

    长行 取 '甲😀'.
    循 14 次 长行 取 长行+长行. 环
    大文 取 '# H\n'+长行+'\n## Z\nx\n'.
    准备 甲 大文.
    折 其 推进 甲 0.001.
    中 取 折 其 状态 甲.
    确认 (中['pending'] 且 非 (折 其 折叠 甲 0)) 'long-line work is queued and pending folds cannot be toggled'.
    态 取 折 其 排空 甲.
    确认 (态['enabled'] 且 态['foldEnabled'] 且 态['warning'] == '' 且 态['maxRead'] <= 1024 且 态['maxPublish'] <= 64 且 态['maxRanges'] <= 64 且 态['points'] == 0 且 甲计['fullLine'] == 0 且 (编 其 文本 甲) == 大文) '114688-byte Unicode line uses bounded scalar-aligned reads and no GETLINE or checkpoints'.
    验层 甲 ([9216,1025,9217,1026,1026]) 'headings following a long Unicode line have exact folds'.

    # Dense paragraphs require ranges much larger than one64-line publisher.
    段 取 'body\n'. 循 10 次 段 取 段+段. 环
    密文 取 段+'---\nlast'.
    准备 甲 密文.
    见尾 取 假.
    循
        若 非 (折 其 待办 甲) 则 破. 然
        折 其 推进 甲 0.001.
        中 取 折 其 状态 甲.
        若 中['eof'] 且 中['pending'] 且 中['queuedRanges'] > 0 则 见尾 取 真. 然
    环
    态 取 折 其 状态 甲.
    确认 (见尾 且 态['maxPublish'] == 64 且 态['maxRanges'] <= 64 且 非 态['pending'] 且 (窗 其 发送 甲 2223 0 0) 其 数 == 9216 且 (窗 其 发送 甲 2223 1023 0) 其 数 == 1025) 'EOF stays pending while a long retroactive Setext range drains in64-line slices'.

    准备 甲 大文.
    准备 乙 '# independent\r\ntext\r\n'.
    循
        若 非 (折 其 待办 甲) 且 非 (折 其 待办 乙) 则 破. 然
        折 其 推进 甲 0.001.
        折 其 推进 乙 0.001.
    环
    确认 ((编 其 文本 甲) == 大文 且 (编 其 文本 乙) == '# independent\r\ntext\r\n' 且 (折 其 状态 甲)['generation'] != (折 其 状态 乙)['generation']) 'two HWND/document states advance interleaved without cross-contamination'.
    验层 乙 ([9216,1025,1025]) 'independent CRLF document retains its own complete fold levels'.

    # A real equal-byte replacement changes the fold structure while length is
    # unchanged. Revision/identity guards, rather than only a length check, must
    # reject the already-captured publisher.
    准备 甲 大文.
    折 其 推进 甲 0.001. 折 其 推进 甲 0.001.
    旧 取 (折 其 _编辑们) 其 查 (甲 其 句).
    旧长 取 (窗 其 发送 甲 2183 0 0) 其 数.
    窗 其 发送 甲 2190 0 0. # SCI_SETTARGETSTART
    窗 其 发送 甲 2192 1 0. # SCI_SETTARGETEND
    窗 其 发文 甲 2194 1 ' '. # SCI_REPLACETARGET: replace one '#' byte
    拒旧 甲 旧 甲计 'equal-byte replacement invalidates the old publisher without any fold write'.
    态 取 折 其 排空 甲.
    准备 乙 (' '+大文[1:]). 折 其 排空 乙.
    确认 ((窗 其 发送 甲 2183 0 0) 其 数 == 旧长 且 态['generation'] == 旧['generation'] 且 态['revision'] > 旧['revision'] 且 (同折 甲 乙) 且 (编 其 已变 甲) 且 (窗 其 发送 甲 2223 0 0) 其 数 == 1024) 'equal-length structural edit advances revision and matches independent BOF text and every fold'.

    # Unequal insertion during pending work also preserves exact undo/redo.
    准备 甲 大文.
    折 其 推进 甲 0.001. 折 其 推进 甲 0.001.
    旧 取 (折 其 _编辑们) 其 查 (甲 其 句).
    窗 其 发送 甲 2160 0 0.
    窗 其 发文 甲 2170 0 '# inserted\n'.
    拒旧 甲 旧 甲计 'edited revision rejects an old publisher before any fold write'.
    选始 取 (窗 其 发送 甲 2009 0 0) 其 数.
    选末 取 (窗 其 发送 甲 2008 0 0) 其 数.
    态 取 折 其 排空 甲.
    准备 乙 ('# inserted\n'+大文). 折 其 排空 乙.
    确认 (态['revision'] > 0 且 (同折 甲 乙) 且 (编 其 已变 甲) 且 (窗 其 发送 甲 2009 0 0) 其 数 == 选始 且 (窗 其 发送 甲 2008 0 0) 其 数 == 选末) 'pending edit equals independent BOF scan for all text/fold lines and retains dirty selection'.
    窗 其 发送 甲 2176 0 0. 折 其 排空 甲.
    准备 乙 大文. 折 其 排空 乙.
    确认 ((同折 甲 乙) 且 非 (编 其 已变 甲)) 'fold publication adds no undo step and original savepoint remains reachable'.
    窗 其 发送 甲 2011 0 0. 折 其 排空 甲.
    确认 ((编 其 文本 甲) == '# inserted\n'+大文 且 (编 其 已变 甲)) 'redo restores exactly the user edit'.

    准备 甲 大文.
    折 其 推进 甲 0.001.
    旧 取 (折 其 _编辑们) 其 查 (甲 其 句).
    确认 (非 (折 其 设置折叠 甲 假)) 'fold-off invalidates a pending scan'.
    拒旧 甲 旧 甲计 'fold-off rejects the prior batch identity'.
    态 取 折 其 状态 甲.
    窗 其 发文 甲 2282 1 'x'.
    态 取 折 其 状态 甲.
    确认 (态['enabled'] 且 态['language'] == 'markdown' 且 非 态['foldEnabled'] 且 非 态['pending'] 且 (全显 甲) 且 (窗 其 发送 甲 4002 0 0) 其 数 == 98) 'fold-off survives edits while Markdown lexing stays enabled and lines remain visible'.
    确认 (折 其 设置折叠 甲 真) 'fold-on schedules a fresh bounded BOF scan'.
    折 其 排空 甲.
    确认 ((折 其 状态 甲)['foldEnabled'] 且 (编 其 文本 甲) == 大文+'x' 且 (编 其 已变 甲)) 'fold-on preserves the dirty edit'.

    # Each query can synchronously re-enter, replace the document, then complete
    # the replacement fold task. An old catch must not reveal its collapsed body.
    准备 甲 大文.
    甲计 其 增 'target' 2357. 甲计 其 增 'action' 'replace'.
    外选 取 折 其 选择 甲.
    态 取 折 其 状态 甲.
    确认 (外选 == 'plain' 且 态 != 空 且 态['enabled'] 且 非 态['pending'] 且 态['warning'] == '' 且 (编 其 文本 甲) == 替文 且 (窗 其 发送 甲 2228 1 0) 其 数 == 0) 'nested selection during initial snapshot retains the new owner and collapsed result'.
    查询们 取 [2357,2183,2039,2417].
    位 取 0.
    循 查询们 其 量 次
        准备 甲 大文.
        折 其 推进 甲 0.001.
        甲计 其 增 'target' 查询们[位].
        甲计 其 增 'action' 'replace'.
        甲计 其 增 'fired' 假.
        折 其 推进 甲 8.
        态 取 折 其 状态 甲.
        确认 (甲计['fired'] 且 态 != 空 且 态['enabled'] 且 态['foldEnabled'] 且 态['warning'] == '' 且 非 态['pending'] 且 (编 其 文本 甲) == 替文 且 (窗 其 发送 甲 2228 1 0) 其 数 == 0) ('query'+(查询们[位] 为 句)+' replacement rejects stale work and stale error recovery').
        位 取 位+1.
    环
    准备 甲 大文. 折 其 推进 甲 0.001.
    甲计 其 增 'target' 2183. 甲计 其 增 'action' 'edit'.
    折 其 推进 甲 8. 折 其 排空 甲.
    准备 乙 ('# inserted\n'+大文). 折 其 排空 乙.
    确认 ((同折 甲 乙) 且 (折 其 状态 甲)['revision'] > 0) 'text notification during a query invalidates an inTick revision and rescans the final text'.
    准备 甲 大文. 折 其 推进 甲 0.001.
    甲计 其 增 'target' 2183. 甲计 其 增 'action' 'language'.
    折 其 推进 甲 8.
    确认 ((折 其 状态 甲) == 空 且 非 (折 其 待办 甲) 且 (窗 其 发送 甲 4002 0 0) 其 数 == 0 且 (全显 甲)) 'language change inside a synchronous query cannot revive or mutate the old task'.

    准备 甲 文.
    甲计 其 增 'target' 0. 甲计 其 增 'action' 'invalidate-after-fold'.
    甲计 其 增 'fired' 假.
    写前 取 甲计['fold'].
    折 其 排空 甲.
    确认 (甲计['fired'] 且 甲计['fold'] == 写前+1 且 (折 其 状态 甲) == 空) 'post-fold-write invalidation prevents every subsequent write or stale cleanup'.

    # Preparation, not per-line SCI_FOLDLINE, owns the expansion invariant.
    # Deliberately seed old header AND nonheader collapsed bits/hidden children.
    准备 甲 文.
    新态 取 (折 其 _编辑们) 其 查 (甲 其 句).
    拒旧 甲 新态 甲计 'publication rejects an unprepared owner before any fold mutation'.
    窗 其 发送 甲 2222 0 9216. 窗 其 发送 甲 2222 1 1024. 窗 其 发送 甲 2222 2 1024.
    窗 其 发送 甲 2229 0 0. 窗 其 发送 甲 2229 1 0. 窗 其 发送 甲 2229 2 0.
    窗 其 发送 甲 2227 1 3.
    初种 取 (窗 其 发送 甲 2223 0 0) 其 数 == 9216 且 (窗 其 发送 甲 2223 1 0) 其 数 == 1024 且 (窗 其 发送 甲 2223 2 0) 其 数 == 1024 且 (窗 其 发送 甲 2230 2 0) 其 数 == 0 且 (窗 其 发送 甲 2230 0 0) 其 数 == 0 且 (窗 其 发送 甲 2230 1 0) 其 数 == 0 且 非 (全显 甲).
    折 其 _一步 甲 新态.
    确认 (初种 且 新态['phase'] == 'scan' 且 新态['pending'] 且 (全显 甲) 且 (全展开 甲) 且 (窗 其 发送 甲 2664 0 0) 其 数 == 0) 'prepare expands every old header and nonheader bit before bounded publication'.
    确认 (非 (折 其 折叠 甲 0) 且 非 (折 其 全折 甲 0) 且 非 (折 其 全折 甲 1) 且 非 (折 其 全折 甲 2) 且 (全显 甲) 且 (全展开 甲)) 'all public fold actions reject pending work without changing prepared visibility'.
    展前 取 甲计['foldLine'].
    折 其 排空 甲.
    确认 (甲计['foldLine'] == 展前 且 (全显 甲) 且 (全展开 甲) 且 (窗 其 发送 甲 2223 0 0) 其 数 == 9216 且 (窗 其 发送 甲 2223 2 0) 其 数 == 9217 且 (编 其 文本 甲) == 文 且 非 (编 其 已变 甲) 且 (窗 其 发送 甲 2174 0 0) 其 为空) 'new headers publish with exact levels and no per-line FoldLine or text undo changes'.
    折 其 全折 甲 0.
    确认 (非 (全显 甲)) 'completed headings remain collapsible after redundant FoldLine removal'.
    完态 取 (折 其 _编辑们) 其 查 (甲 其 句).
    写前 取 甲计['fold']. 拒 取 [假].
    试 折 其 _发布 甲 完态. 救 原因 拒[0] 取 真. 终
    确认 (拒[0] 且 甲计['fold'] == 写前 且 非 (全显 甲)) 'publication rejects a completed owner and preserves its user-collapsed state'.
    窗 其 发送 甲 2190 0 0. 窗 其 发送 甲 2192 1 0.
    窗 其 发文 甲 2194 1 ' '.
    新态 取 (折 其 _编辑们) 其 查 (甲 其 句).
    折 其 _一步 甲 新态.
    确认 (新态['pending'] 且 (全显 甲) 且 (全展开 甲)) 'editing a collapsed header creates a prepared all-visible expanded revision'.
    展前 取 甲计['foldLine'].
    折 其 排空 甲.
    准备 乙 (' '+文[1:]). 折 其 排空 乙.
    等价 取 (同折 甲 乙) 且 (全显 甲) 且 (全展开 甲) 且 甲计['foldLine'] == 展前 且 (编 其 已变 甲).
    窗 其 发送 甲 2176 0 0. 折 其 排空 甲.
    确认 (等价 且 (编 其 文本 甲) == 文 且 非 (编 其 已变 甲)) 'removed collapsed header matches independent folds and keeps the original one-step undo'.

    # Restore the sibling used by the unchanged late-close isolation check.
    准备 乙 ('# inserted\n'+大文). 折 其 排空 乙.

    # Re-entry after a mutation is checked by the shared full post/pre guard.
    # The status query is deliberately reached only after the whole range.
    后查们 取 [2357,2183,2383]. 后位 取 0.
    循 后查们 其 量 次
        准备 甲 文.
        新态 取 (折 其 _编辑们) 其 查 (甲 其 句).
        折 其 _一步 甲 新态.
        新态 其 增 'ranges' ([[0,2,0,假]]).
        甲计 其 增 'postTarget' 后查们[后位].
        甲计 其 增 'target' 0. 甲计 其 增 'action' 'replace-after-fold-query'.
        甲计 其 增 'fired' 假.
        折 其 推进 甲 8.
        态 取 折 其 状态 甲.
        确认 (甲计['fired'] 且 甲计['fold'] == 甲计['replaceStopFold'] 且 新态['published'] == 0 且 新态['rangeOffset'] == 0 且 态 != 空 且 态['identity'] != 新态['identity'] 且 非 态['pending'] 且 态['warning'] == '' 且 (编 其 文本 甲) == 替文 且 (窗 其 发送 甲 2228 1 0) 其 数 == 0) ('post-mutation query'+(后查们[后位] 为 句)+' rejects stale publication and leaves replacement folds collapsed').

        后位 取 后位+1.
    环

    边界文 取 '# boundary\n'. 循 70 次 边界文 取 边界文+'body\n'. 环
    准备 甲 边界文.
    新态 取 (折 其 _编辑们) 其 查 (甲 其 句).
    折 其 _一步 甲 新态.
    新态 其 增 'ranges' ([[0,65,0,假]]).
    写前 取 甲计['fold']. 展前 取 甲计['foldLine'].
    折 其 _发布 甲 新态.
    确认 (甲计['fold'] == 写前+64 且 甲计['foldLine'] == 展前 且 新态['rangeOffset'] == 64 且 新态['published'] == 64 且 新态['maxPublish'] == 64 且 (全显 甲) 且 (全展开 甲)) 'shared guards keep the exact64-line publication cap and resume cursor'.
    # No proof is carried across calls: invalidate after the next call's first
    # (and final) mutation, before its cursor/status tail can commit.
    甲计 其 增 'target' 0. 甲计 其 增 'action' 'invalidate-after-fold'.
    甲计 其 增 'invalidateAt' (写前+65). 甲计 其 增 'fired' 假.
    拒 取 [假].
    试 折 其 _发布 甲 新态. 救 原因 拒[0] 取 真. 终
    确认 (拒[0] 且 甲计['fired'] 且 甲计['fold'] == 写前+65 且 (折 其 状态 甲) == 空 且 新态['published'] == 64 且 新态['rangeOffset'] == 64) 'final mutation invalidation rejects the shared post-guard before cursor completion'.
    甲计 其 增 'invalidateAt' 0.
    准备 甲 边界文.
    新态 取 (折 其 _编辑们) 其 查 (甲 其 句).
    折 其 _一步 甲 新态.
    新态 其 增 'ranges' ([[0,64,0,假]]).
    写前 取 甲计['fold'].
    甲计 其 增 'target' 0. 甲计 其 增 'action' 'invalidate-after-fold'.
    甲计 其 增 'invalidateAt' (写前+64). 甲计 其 增 'fired' 假.
    拒 取 [假].
    试 折 其 _发布 甲 新态. 救 原因 拒[0] 取 真. 终
    确认 (拒[0] 且 甲计['fired'] 且 甲计['fold'] == 写前+64 且 (折 其 状态 甲) == 空 且 新态['published'] == 0 且 新态['rangeOffset'] == 0) 'the64th mutation retains its complete post-guard before any batch cursor commit'.
    甲计 其 增 'invalidateAt' 0.

    # A cleanup query may deliver a real same-document edit. The disabled new
    # revision must inherit visibility work instead of leaving old folds hidden.
    准备 甲 文. 折 其 排空 甲. 折 其 全折 甲 0.
    原隐 取 非 (全显 甲).
    前态 取 折 其 状态 甲.
    甲计 其 增 'target' 2183. 甲计 其 增 'action' 'edit'.
    甲计 其 增 'fired' 假.
    折 其 设置折叠 甲 假.
    队态 取 折 其 状态 甲.
    态 取 折 其 排空 甲.
    确认 (原隐 且 甲计['fired'] 且 队态['pending'] 且 队态['revision'] > 前态['revision'] 且 态['identity'] == 队态['identity'] 且 态['generation'] == 前态['generation'] 且 态['enabled'] 且 非 态['foldEnabled'] 且 非 态['pending'] 且 (全显 甲) 且 (编 其 已变 甲) 且 (编 其 文本 甲) == '# inserted\n'+文) 'fold-off query edit retains the new owner and drains inherited visibility cleanup'.

    准备 甲 文. 折 其 排空 甲. 折 其 全折 甲 0.
    原隐 取 非 (全显 甲).
    前态 取 折 其 状态 甲.
    窗 其 发送 甲 2382 1000 0.
    甲计 其 增 'target' 2183. 甲计 其 增 'action' 'edit'.
    甲计 其 增 'fired' 假.
    # Inject the failure boundary, then exercise actual Scintilla cleanup and a
    # real SCN_MODIFIED callback; no native query or edit is replaced by a mock.
    折 其 _失败 甲 ((折 其 _编辑们) 其 查 (甲 其 句)) 'injected recovery boundary'.
    队态 取 折 其 状态 甲.
    态 取 折 其 排空 甲.
    原码 取 (窗 其 发送 甲 2383 0 0) 其 数.
    窗 其 发送 甲 2382 0 0. # Fixture resets only its own injected native warning.
    确认 (原隐 且 甲计['fired'] 且 队态['pending'] 且 队态['revision'] > 前态['revision'] 且 态['identity'] == 队态['identity'] 且 态['generation'] == 前态['generation'] 且 态['enabled'] 且 非 态['foldEnabled'] 且 非 态['pending'] 且 态['warning'] != '' 且 原码 == 1000 且 (全显 甲) 且 (编 其 已变 甲) 且 (编 其 文本 甲) == '# inserted\n'+文) 'failure query edit retains warning and new revision while completing visibility cleanup'.

    # Existing status warnings remain intact; only the fold feature is disabled.
    准备 甲 文. 折 其 排空 甲. 折 其 全折 甲 0.
    窗 其 发送 甲 2160 2 9.
    窗 其 发文 甲 2170 0 '乙😀'.
    窗 其 发送 甲 2382 1000 0.
    选始 取 (窗 其 发送 甲 2009 0 0) 其 数.
    选末 取 (窗 其 发送 甲 2008 0 0) 其 数.
    态 取 折 其 排空 甲.
    确认 (态['enabled'] 且 非 态['foldEnabled'] 且 态['warning'] != '' 且 非 态['pending'] 且 (窗 其 发送 甲 2383 0 0) 其 数 == 1000 且 (全显 甲) 且 (窗 其 发送 甲 2009 0 0) 其 数 == 选始 且 (窗 其 发送 甲 2008 0 0) 其 数 == 选末) 'fold failure keeps native warnings, all visible lines and exact dirty selection'.
    窗 其 发送 甲 2382 0 0. # Fixture explicitly resets its own injected warning.
    确认 ((编 其 文本 甲) == '# 乙😀\nbody\n## next\nchild\n' 且 (编 其 已变 甲)) 'recovery never rewrites user text or its savepoint'.
    窗 其 发送 甲 2176 0 0.
    确认 ((编 其 文本 甲) == 文 且 非 (编 其 已变 甲)) 'undo remains one edit after fold failure'.

    # A STYLES_NONE document exercises refusal without allocating32MB text.
    折 其 遗忘 甲.
    流 取 编 其 开始载入 甲 32000000.
    编 其 追加文本 流 '# retained\ntext'.
    编 其 完成载入 流.
    确认 ((安装 甲) == 'plain' 且 非 (折 其 待办 甲) 且 (编 其 文本 甲) == '# retained\ntext') 'bridge independently refuses large-file document options without losing text'.

    临 取 编 其 创建 父 实例 3.
    临计 取 计数 临.
    窗 其 成功 (_SetWindowSubclass 其 调用 [临,子回调 其 地址,918,0]) 'subclass closing editor'.
    准备 临 大文. 折 其 推进 临 0.001.
    旧 取 (折 其 _编辑们) 其 查 (临 其 句).
    折 其 遗忘 临.
    窗 其 成功 ((窗 其 DestroyWindow) 其 调用 [临]) 'destroy pending editor'.
    拒旧 临 旧 临计 'close invalidates before DestroyWindow and rejects every late fold write'.
    确认 (非 (折 其 推进 临 8) 且 (折 其 状态 临) == 空 且 (编 其 文本 乙) == '# inserted\n'+大文) 'late closed-editor tick is inert and sibling remains intact'.
    确认 (甲计['fullLine'] == 0 且 乙计['fullLine'] == 0) 'all native acceptance paths avoid unbounded GETLINE'.
    折 其 遗忘 甲. 折 其 遗忘 乙.
    窗 其 成功 (_RemoveWindowSubclass 其 调用 [甲,子回调 其 地址,918]) 'remove first subclass'.
    窗 其 成功 (_RemoveWindowSubclass 其 调用 [乙,子回调 其 地址,918]) 'remove second subclass'.
    窗 其 成功 ((窗 其 DestroyWindow) 其 调用 [父]) 'destroy fixture'.
    窗 其 成功 ((窗 其 UnregisterClassW) 其 调用 [类名,实例]) 'unregister fixture'.
    类 其 关闭. 类名 其 关闭. 子回调 其 关闭. 回调 其 关闭.
    显 'TOTAL PASS: '+(次数[0] 为 句).
    得 0.
法
