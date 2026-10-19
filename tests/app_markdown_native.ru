# Fresh real-window Markdown Stage A integration; no renderer or Enter hook.
应用 取 外言 '../src/main.ru'.
窗 取 外言 '../src/win32.ru'.
编 取 外言 '../src/editor.ru'.
语 取 外言 '../src/syntax.ru'.
折 取 外言 '../src/markdown_syntax.ru'.
件编 取 外言 '../src/file_codec.ru'.
密 取 外言 '如:密'.
Sleep 取 (窗 其 内核) 其 绑定 'Sleep' (密 其 签名 (窗 其 V) ([(窗 其 U)]) 'win64').
Delete 取 (窗 其 内核) 其 绑定 'DeleteFileW' (密 其 签名 (窗 其 I) ([(窗 其 PTR)]) 'win64').
_SetWindowSubclass 取 (窗 其 控件) 其 绑定 'SetWindowSubclass' (密 其 签名 (窗 其 I) ([(窗 其 PTR),(窗 其 PTR),(窗 其 UP),(窗 其 UP)]) 'win64').
_RemoveWindowSubclass 取 (窗 其 控件) 其 绑定 'RemoveWindowSubclass' (密 其 签名 (窗 其 I) ([(窗 其 PTR),(窗 其 PTR),(窗 其 UP)]) 'win64').
_DefSubclassProc 取 (窗 其 控件) 其 绑定 'DefSubclassProc' (密 其 签名 (窗 其 IP) ([(窗 其 PTR),(窗 其 U),(窗 其 UP),(窗 其 IP)]) 'win64').
_InvalidateRect 取 (窗 其 用户) 其 绑定 'InvalidateRect' (密 其 签名 (窗 其 I) ([(窗 其 PTR),(窗 其 PTR),(窗 其 I)]) 'win64').
_子型 取 密 其 签名 (窗 其 IP) ([(窗 其 PTR),(窗 其 U),(窗 其 UP),(窗 其 IP),(窗 其 UP),(窗 其 UP)]) 'win64'.
_选测 取 {'action':'','writes':0,'styleStarts':0,'fired':假,'paints':0}.
算 选择子过程 柄 消息 宽 长 号 引:
    码 取 消息 其 数.
    若 码 == 2031 或 码 == 2032 或 码 == 4005 则 _选测 其 增 'writes' (_选测['writes']+1). 然
    若 码 == 2032 则 _选测 其 增 'styleStarts' (_选测['styleStarts']+1). 然
    若 码 == 15 则 _选测 其 增 'paints' (_选测['paints']+1). 然
    动作 取 ''.
    若 码 == 2357 且 _选测['action'] != '' 则
        动作 取 _选测['action'].
        _选测 其 增 'action' ''.
        _选测 其 增 'fired' 真.
        若 动作 == 'plain' 则 语 其 选择 柄 'plain'. 然
        若 动作 == 'forget' 则 语 其 遗忘 柄. 然
        若 动作 == 'replace' 则
            # The supported owner invalidates before replacing its document.
            语 其 遗忘 柄.
            编 其 _新文档 柄 假.
            编 其 设文本 柄 '# replacement\nbody'.
            语 其 选择 柄 'plain'.
        然
    然
    果 取 窗 其 结果 (_DefSubclassProc 其 调用 [柄,消息,宽,长]).
    若 动作 == 'close' 则
        # Query returned first; owner invalidates before native destruction.
        语 其 遗忘 柄.
        窗 其 成功 ((窗 其 DestroyWindow) 其 调用 [柄]) 'Destroy query fixture'.
    然
    得 果.
法
次数 取 [0].
源 取 '# 标题😀\r\nbody\r\n## Child\r\nitem\r\n# Next\r\nend\r\n'.
作 确认 条件 为 事实 名 为 句:
    若 非 条件 则 卒 'FAIL: '+名. 然
    次数[0] 取 次数[0]+1.
    显 'PASS: '+名.
为
作 泵 预算 为 数:
    消 取 (窗 其 MSG) 其 新建.
    起 取 语 其 时刻.
    试
        循
            态 取 应用 其 A.
            若 非 (态 其 查 'busy') 且 非 (态 其 查 'syntaxTimer') 则 破. 然
            若 (语 其 时刻)-起 > 预算 则 卒 'Markdown integration work exceeded its bounded deadline.'. 然
            若 非 ((窗 其 结果 ((窗 其 PeekMessageW) 其 调用 [消,空,0,0,1])) 其 为空) 则
                若 (消 其 读 'message') 其 数 == 18 则 卒 'Unexpected quit while Markdown work is pending.'. 然
                窗 其 结果 ((窗 其 TranslateMessage) 其 调用 [消]).
                窗 其 结果 ((窗 其 DispatchMessageW) 其 调用 [消]).
            另 Sleep 其 调用 [1]. 然
        环
    救 原因 消 其 关闭. 卒 原因. 终
    消 其 关闭.
为
算 可见 柄 行 为 数:
    得 非 ((窗 其 发送 柄 2228 行 0) 其 为空).
法
作 删 路 为 句:
    存 取 密 其 UTF16 路.
    试 窗 其 成功 (Delete 其 调用 [存]) 'Delete owned Markdown fixture'. 救 原因 存 其 关闭. 卒 原因. 终
    存 其 关闭.
为
作 验自然配色 主 柄 页:
    # Reinitialize through the real menus while hidden. Check immediately,
    # before pumping: a previously posted native insertion-idle message may
    # otherwise legitimately consume the invalid prefix even without paint.
    窗 其 发送 主 273 701 0.
    窗 其 发送 主 273 705 0.
    确认 ((窗 其 发送 柄 2028 0 0) 其 数 == 0) 'hidden Markdown reinitialization invalidates the cleared prefix before pumping'.
    回调 取 密 其 回调 _子型 (算 选择子过程) 0.
    消 取 (窗 其 MSG) 其 新建.
    窗 其 成功 (_SetWindowSubclass 其 调用 [柄,回调 其 地址,9982,0]) 'Subclass natural paint fixture'.
    _选测 其 增 'paints' 0.
    起 取 语 其 时刻.
    试
        窗 其 结果 ((窗 其 ShowWindow) 其 调用 [主,5]).
        窗 其 成功 (_InvalidateRect 其 调用 [柄,空,0]) 'Invalidate natural paint fixture'.
        循
            若 _选测['paints'] > 0 且 (窗 其 发送 柄 2010 0 0) 其 数 == 6 则 破. 然
            若 (语 其 时刻)-起 > 5000 则 卒 'Natural Markdown paint did not colour the heading within five seconds.'. 然
            若 非 ((窗 其 结果 ((窗 其 PeekMessageW) 其 调用 [消,空,0,0,1])) 其 为空) 则
                若 (消 其 读 'message') 其 数 == 18 则 卒 'Unexpected quit during natural Markdown paint.'. 然
                窗 其 结果 ((窗 其 TranslateMessage) 其 调用 [消]).
                窗 其 结果 ((窗 其 DispatchMessageW) 其 调用 [消]).
            另 Sleep 其 调用 [1]. 然
        环
        确认 (_选测['paints'] > 0 且 (窗 其 发送 柄 2028 0 0) 其 数 > 0 且 (窗 其 发送 柄 2010 0 0) 其 数 == 6) 'ordinary message pumping paints a coloured Markdown heading without COLOURISE'.
        确认 ((编 其 文本 柄) == 源 且 非 (应用 其 脏 页) 且 (页 其 查 'revision') == 0 且 (窗 其 发送 柄 2174 0 0) 其 为空) 'natural initial colouring preserves text savepoint revision and undo'.
    救 原因
        窗 其 结果 ((窗 其 ShowWindow) 其 调用 [主,0]).
        窗 其 成功 (_RemoveWindowSubclass 其 调用 [柄,回调 其 地址,9982]) 'Remove natural paint fixture'.
        消 其 关闭. 回调 其 关闭.
        卒 原因.
    终
    窗 其 结果 ((窗 其 ShowWindow) 其 调用 [主,0]).
    窗 其 成功 (_RemoveWindowSubclass 其 调用 [柄,回调 其 地址,9982]) 'Remove natural paint fixture'.
    消 其 关闭. 回调 其 关闭.
    泵 30000.
为
作 验选择重入 主:
    柄 取 编 其 创建 主 ((应用 其 A) 其 查 'instance') 9981.
    编 其 设文本 柄 '# fixture\nbody'.
    回调 取 密 其 回调 _子型 (算 选择子过程) 0.
    窗 其 成功 (_SetWindowSubclass 其 调用 [柄,回调 其 地址,9981,0]) 'Subclass selection fixture'.
    拒 取 [假].
    _选测 其 增 'action' 'plain'.
    试 语 其 选择 柄 'markdown'. 救 原因 拒[0] 取 真. 终
    确认 (拒[0] 且 _选测['fired'] 且 (窗 其 发送 柄 4002 0 0) 其 数 == 0) 'selection initialization cannot overwrite a nested Plain choice'.
    旧 取 语 其 _新选择 柄.
    _选测 其 增 'writes' 0. _选测 其 增 'action' 'plain'. 拒[0] 取 假.
    试 语 其 _发设 旧 柄 2031 1 0. 救 原因 拒[0] 取 真. 终
    确认 (拒[0] 且 _选测['writes'] == 0 且 (窗 其 发送 柄 2030 0 0) 其 数 == 2) 'guard query invalidation rejects a numeric setup before its mutation'.
    旧 取 语 其 _新选择 柄.
    _选测 其 增 'writes' 0. _选测 其 增 'action' 'forget'. 拒[0] 取 假.
    试 语 其 _发文设 旧 柄 4005 0 'keyword'. 救 原因 拒[0] 取 真. 终
    确认 (拒[0] 且 _选测['writes'] == 0) 'guard query forgetting rejects text setup before its mutation'.
    旧 取 语 其 _新选择 柄.
    原文档 取 (窗 其 发送 柄 2357 0 0) 其 句.
    # Replacement text setup legitimately sends SETEOLMODE (2031). Only the
    # stale STARTSTYLING (2032) would reset its freshly cleared styled prefix.
    _选测 其 增 'writes' 0. _选测 其 增 'styleStarts' 0. _选测 其 增 'action' 'replace'. 拒[0] 取 假.
    试 语 其 _发设 旧 柄 2032 0 0. 救 原因 拒[0] 取 真. 终
    确认 (拒[0] 且 _选测['styleStarts'] == 0 且 (窗 其 发送 柄 2357 0 0) 其 句 != 原文档 且 (编 其 文本 柄) == '# replacement\nbody' 且 (窗 其 发送 柄 2028 0 0) 其 数 == (窗 其 发送 柄 2183 0 0) 其 数) 'stale Markdown invalidation cannot reset a replacement document styled prefix'.
    旧 取 语 其 _新选择 柄.
    _选测 其 增 'writes' 0. _选测 其 增 'action' 'close'. 拒[0] 取 假.
    试 语 其 _发设 旧 柄 2031 1 0. 救 原因 拒[0] 取 真. 终
    确认 (拒[0] 且 _选测['writes'] == 0 且 (语 其 状态 柄) == 空) 'query-return destruction cannot authorize subsequent setup'.
    回调 其 关闭.
为
作 验阶段诊断 柄 页:
    状 取 应用 其 A.
    文 取 编 其 文本 柄.
    选始 取 (窗 其 发送 柄 2009 0 0) 其 数.
    选末 取 (窗 其 发送 柄 2008 0 0) 其 数.
    原次 取 状 其 查 'syntaxTicks'.
    原工 取 状 其 查 'syntaxWorkMs'.
    原隙 取 状 其 查 'syntaxGapMs'.
    原条 取 窗 其 取文 (状 其 查 'status').
    应用 其 诊断Markdown 1000.
    确认 ((状 其 查 'markdownDiagnosticSeq') == 0 且 (窗 其 取文 (状 其 查 'status')) == 原条) 'Markdown phase diagnostics are disabled in ordinary application startup'.
    状 其 增 'markdownDiagnosticEnabled' 真.
    应用 其 诊断Markdown 1000.
    条 取 窗 其 取文 (状 其 查 'status').
    确认 ((状 其 查 'markdownDiagnosticSeq') == 1 且 (条 其 含 ' [MDP1 seq=1 ') 且 (条 其 含 ' phase=4 pending=0 ') 且 (条 其 含 ' work_us=')) 'enabled numeric status projection contains fixed completed-stage fields'.
    应用 其 诊断Markdown 1000. 应用 其 诊断Markdown 1249.
    确认 ((状 其 查 'markdownDiagnosticSeq') == 1 且 (窗 其 取文 (状 其 查 'status')) == 条) 'phase status writes remain capped to one per250 milliseconds'.
    应用 其 诊断Markdown 1250.
    确认 ((状 其 查 'markdownDiagnosticSeq') == 2 且 (窗 其 取文 (状 其 查 'status')) 其 含 ' [MDP1 seq=2 ') 'phase status becomes eligible exactly at its next bounded slot'.
    旧投影 取 语 其 状态 柄.
    # Exercise the real revision notification without modifying document bytes.
    语 其 变化 柄 0 0 0 1.
    应用 其 刷新.
    确认 (非 ((窗 其 取文 (状 其 查 'status')) 其 含 '[MDP1') 且 (状 其 查 'markdownDiagnosticSeq') == 2) 'a new pending identity cannot reuse the earlier diagnostic marker'.
    语 其 排空 柄.
    应用 其 刷新.
    新投影 取 语 其 状态 柄.
    确认 (新投影['identity'] != 旧投影['identity'] 且 新投影['revision'] == 旧投影['revision']+1 且 (状 其 查 'markdownDiagnosticSeq') == 3 且 (状 其 查 'markdownDiagnosticNext') == 1500 且 ((窗 其 取文 (状 其 查 'status')) 其 含 ' via=1 ') 且 ((窗 其 取文 (状 其 查 'status')) 其 含 ' phase=4 pending=0 ')) 'completion inside a reserved rate slot attaches its new identity to the existing refresh'.
    # Same identity already has a periodic pending sample; finish before its
    # next slot and require the existing refresh to replace that exact cache.
    语 其 变化 柄 0 0 0 1.
    # Exactly one real prepare step initializes length while remaining pending.
    同态 取 (折 其 _编辑们) 其 查 (柄 其 句).
    折 其 _一步 柄 同态. 应用 其 刷新.
    同投影 取 语 其 状态 柄.
    应用 其 诊断Markdown 1500.
    确认 (同投影['pending'] 且 (状 其 查 'markdownDiagnosticSeq') == 4 且 (状 其 查 'markdownDiagnosticIdentity') == 同投影['identity'] 且 (状 其 查 'markdownDiagnosticPending') 且 ((窗 其 取文 (状 其 查 'status')) 其 含 ' pending=1 ')) 'a current identity retains an actual periodic pending marker before completion'.
    语 其 排空 柄. 应用 其 刷新.
    同终 取 语 其 状态 柄. 终条 取 窗 其 取文 (状 其 查 'status').
    确认 (同终['identity'] == 同投影['identity'] 且 非 同终['pending'] 且 (状 其 查 'markdownDiagnosticSeq') == 5 且 (状 其 查 'markdownDiagnosticNext') == 1750 且 非 (状 其 查 'markdownDiagnosticPending') 且 (终条 其 含 'seq=5 via=1 ') 且 (终条 其 含 ' phase=4 pending=0 ')) 'same identity completion replaces its pending marker inside the reserved250 millisecond slot'.
    应用 其 刷新.
    确认 ((状 其 查 'markdownDiagnosticSeq') == 5 且 (窗 其 取文 (状 其 查 'status')) == 终条) 'repeated completion refresh does not consume another diagnostic sequence'.
    状 其 增 'busy' 真. 应用 其 诊断Markdown 1750. 状 其 增 'busy' 假.
    原位 取 状 其 查 'active'. 状 其 增 'active' (-1). 应用 其 诊断Markdown 1750. 状 其 增 'active' 原位.
    状 其 增 'ready' 假. 应用 其 诊断Markdown 1750. 状 其 增 'ready' 真.
    确认 ((状 其 查 'markdownDiagnosticSeq') == 5) 'busy missing-active and not-ready states cannot reserve a diagnostic slot'.
    所属 取 状 其 查 'statusOwner'. 状 其 增 'statusOwner' 'other-document'. 应用 其 诊断Markdown 1750. 状 其 增 'statusOwner' 所属.
    确认 ((状 其 查 'markdownDiagnosticSeq') == 5) 'a status base owned by another editor rejects the numeric projection'.
    状 其 增 'markdownDiagnosticSeq' 4096. 应用 其 诊断Markdown 1750.
    确认 ((状 其 查 'markdownDiagnosticSeq') == 4096) 'phase diagnostics stop at the fixed4096 process cap'.
    状 其 增 'markdownDiagnosticEnabled' 假. 应用 其 刷新.
    确认 (非 ((窗 其 取文 (状 其 查 'status')) 其 含 '[MDP1') 且 (编 其 文本 柄) == 文 且 非 (应用 其 脏 页) 且 (窗 其 发送 柄 2009 0 0) 其 数 == 选始 且 (窗 其 发送 柄 2008 0 0) 其 数 == 选末 且 (窗 其 发送 柄 2174 0 0) 其 为空 且 (状 其 查 'syntaxTicks') == 原次 且 (状 其 查 'syntaxWorkMs') == 原工 且 (状 其 查 'syntaxGapMs') == 原隙) 'diagnostics preserve bytes savepoint selection undo and scanner timing counters'.
    状 其 增 'markdownDiagnosticSeq' 0. 状 其 增 'markdownDiagnosticNext' 0. 状 其 增 'markdownDiagnosticIdentity' 0. 状 其 增 'markdownDiagnosticPending' 真. 状 其 增 'markdownDiagnosticText' ''.
为
算 元初 参数 为 句 阵:
    若 参数 其 量 != 1 则 显 'Usage: app_markdown_native.exe EXISTING_DISPOSABLE_DIRECTORY'. 得 2. 然
    入路 取 参数[0]+'\\markdown-stage-a-甲😀.MARKDOWN'.
    出路 取 参数[0]+'\\markdown-stage-a-save.md'.
    大路 取 参数[0]+'\\markdown-stage-a-large.md'.
    件编 其 写文件 入路 源 1200 真 ''.
    主 取 应用 其 初始化 [入路] 假.
    态 取 应用 其 A.
    确认 (态 其 查 'busy') 'Markdown CLI open uses asynchronous file work'.
    泵 30000.
    页 取 应用 其 当前.
    柄 取 应用 其 编辑柄.
    确认 ((页 其 查 'language') == 'markdown') 'mixed-case Markdown extension selects Markdown'.
    确认 ((窗 其 发送 柄 4002 0 0) 其 数 == 98) 'actual Lexilla Markdown lexer installed'.
    确认 ((页 其 查 'encoding') == 1200 且 (页 其 查 'bom')) 'UTF16LE source encoding and BOM retained'.
    确认 ((编 其 文本 柄) == 源) 'decoded Unicode and CRLF source is exact'.
    确认 (非 (应用 其 脏 页)) 'initial highlighting and folding preserve savepoint'.
    确认 ((页 其 查 'revision') == 0) 'initial style and fold work creates no text revision'.
    确认 ((窗 其 发送 柄 2030 0 0) 其 数 == 0) 'CRLF insertion mode retained'.
    确认 ((窗 其 发送 柄 2174 0 0) 其 为空) 'fold publication creates no undo action'.
    确认 ((窗 其 发送 柄 2223 0 0) 其 数 == 9216) 'H1 owns actual fold header'.
    确认 ((窗 其 发送 柄 2223 2 0) 其 数 == 9217) 'H2 nests beneath H1'.
    确认 ((窗 其 发送 柄 2223 4 0) 其 数 == 9216) 'following H1 closes earlier section'.
    确认 ((窗 其 取文 (态 其 查 'status')) 其 含 'Markdown') 'status names Markdown mode'.
    确认 ((语 其 状态 柄)['maxRead'] <= 1024 且 (语 其 状态 柄)['maxPublish'] <= 64) 'real timer respects byte and publication admission caps'.
    验阶段诊断 柄 页.
    验自然配色 主 柄 页.
    # Explicit lexing verifies lexer output only; it cannot detect the initial
    # cleared-prefix lifecycle bug covered by the natural-paint checks above.
    窗 其 发送 柄 4003 0 (-1).
    确认 ((窗 其 发送 柄 2010 0 0) 其 数 == 6) 'native Markdown heading style is visible'.
    窗 其 发送 柄 2160 2 12.
    窗 其 发送 主 273 505 0.
    确认 (非 (可见 柄 1) 且 非 (可见 柄 3)) 'real collapse menu hides heading children'.
    窗 其 发送 主 273 506 0.
    确认 ((可见 柄 1) 且 (可见 柄 3)) 'real expand menu restores heading children'.
    确认 ((窗 其 发送 柄 2009 0 0) 其 数 == 2 且 (窗 其 发送 柄 2008 0 0) 其 数 == 12) 'fold menu preserves UTF8 selection'.
    窗 其 发送 主 273 507 0.
    确认 (非 (页 其 查 'markdownFolds') 且 非 (语 其 状态 柄)['foldEnabled']) 'heading fold option disables document-local folding'.
    确认 (非 (语 其 待办 柄) 且 (可见 柄 1) 且 (窗 其 发送 柄 2243 2 0) 其 数 == 0) 'disabled folding expands lines and hides its margin'.
    确认 ((窗 其 发送 柄 4002 0 0) 其 数 == 98) 'fold option retains Markdown colors'.
    窗 其 发送 柄 2160 0 0.
    窗 其 发文 柄 2170 0 'X'.
    确认 ((应用 其 脏 页) 且 非 (语 其 待办 柄)) 'editing with folds disabled stays editable without scanning'.
    窗 其 发送 柄 2176 0 0.
    确认 ((编 其 文本 柄) == 源 且 非 (应用 其 脏 页)) 'single undo after disabled folds restores exact text and savepoint'.
    窗 其 发送 主 273 507 0.
    确认 ((页 其 查 'markdownFolds') 且 (语 其 待办 柄)) 're-enabling heading folds queues bounded work'.
    泵 30000.
    确认 ((窗 其 发送 柄 2223 0 0) 其 数 == 9216) 're-enabled folds converge to heading structure'.
    窗 其 发送 主 273 701 0.
    确认 ((页 其 查 'language') == 'plain' 且 (语 其 状态 柄) == 空) 'Plain selection forgets pending Markdown ownership'.
    确认 ((窗 其 发送 柄 4002 0 0) 其 数 == 0 且 (窗 其 发送 柄 2481 6 0) 其 数 == 2039583) 'Plain resets lexer and old heading palette'.
    窗 其 发送 主 273 702 0.
    确认 ((页 其 查 'language') == 'cpp' 且 (窗 其 发送 柄 4002 0 0) 其 数 == 3) 'C++ selection still installs original lexer'.
    窗 其 发送 主 273 705 0.
    确认 ((页 其 查 'language') == 'markdown' 且 (语 其 待办 柄)) 'manual Markdown menu schedules its own folder'.
    泵 30000.
    确认 ((编 其 文本 柄) == 源 且 非 (应用 其 脏 页)) 'language switches preserve content and savepoint'.
    应用 其 新页 'second.md' '# Other\ntext\n' 65001 假 ''.
    另柄 取 应用 其 编辑柄.
    另页 取 应用 其 当前.
    确认 ((另页 其 查 'markdownFolds') 且 (语 其 待办 另柄)) 'second Markdown document owns independent pending state'.
    应用 其 切页 1.
    窗 其 发送 主 273 507 0.
    确认 (非 (页 其 查 'markdownFolds') 且 (另页 其 查 'markdownFolds')) 'fold option does not change another tab'.
    泵 30000.
    确认 ((窗 其 发送 另柄 2223 0 0) 其 数 == 9216 且 (编 其 文本 另柄) == '# Other\ntext\n') 'background document reaches its own exact fold result'.
    应用 其 新页 '' 源 65001 假 ''.
    存柄 取 应用 其 编辑柄.
    确认 (((应用 其 当前) 其 查 'language') == 'plain') 'untitled source stays Plain until an explicit choice or successful Save As'.
    态 其 增 'chooseSavePath' (算 原路: 得 出路. 法).
    确认 (应用 其 保存 真) 'Save As starts existing safe asynchronous writer'.
    泵 30000.
    确认 (((应用 其 当前) 其 查 'language') == 'markdown' 且 (窗 其 发送 存柄 4002 0 0) 其 数 == 98) 'successful .md Save As chooses Markdown and schedules folds'.
    确认 (非 (应用 其 脏 (应用 其 当前)) 且 (窗 其 发送 存柄 2223 0 0) 其 数 == 9216) 'Save As reaches savepoint with correct folds'.
    读回 取 件编 其 读文件 出路 0.
    确认 (读回['text'] == 源 且 读回['encoding'] == 65001) 'saved Markdown contains only original source bytes'.
    应用 其 新页 'close-pending.md' 源 65001 假 ''.
    旧柄 取 应用 其 编辑柄.
    确认 (语 其 待办 旧柄) 'new Markdown page starts pending'.
    应用 其 删除当前页.
    确认 ((语 其 状态 旧柄) == 空) 'closing pending page forgets its generation before destruction'.
    泵 30000.
    确认 ((编 其 文本 存柄) == 源 且 非 (应用 其 脏 (应用 其 当前))) 'late work cannot modify surviving tab'.
    # A real >=32MB file follows the existing no-style streaming path.
    块 取 'x'. 循 16 次 块 取 块+块. 环
    写态 取 件编 其 准备写入 大路 65001 假 ''.
    循 489 次 件编 其 写入一段 写态 块. 环
    件编 其 完成写入 写态.
    应用 其 打开 大路 0.
    泵 120000.
    大页 取 应用 其 当前.
    大柄 取 应用 其 编辑柄.
    确认 ((大页 其 查 'large') 且 (大页 其 查 'language') == 'plain') 'real32MB Markdown file uses mandatory plain mode'.
    确认 ((窗 其 发送 大柄 2183 0 0) 其 数 == 32047104) 'large Markdown load preserves complete file byte count'.
    确认 ((窗 其 发送 大柄 2379 0 0) 其 数 % 2 == 1 且 (窗 其 发送 大柄 4002 0 0) 其 数 == 0) 'large document disables style allocation and native lexer'.
    确认 ((窗 其 发送 大柄 2269 0 0) 其 数 == 0 且 (语 其 状态 大柄) == 空) 'large mode keeps wrap and Markdown folding inactive'.
    确认 (非 (应用 其 脏 大页)) 'large Markdown open keeps clean savepoint'.
    验选择重入 主.
    确认 (((态 其 查 'errors') 其 量) == 0) 'Markdown normal lifecycle leaves no operation errors'.
    确认 (应用 其 关程序) 'all clean Markdown and plain documents close normally'.
    确认 (非 (态 其 查 'ready') 且 (语 其 状态 柄) == 空 且 (语 其 状态 另柄) == 空) 'shutdown discards every remaining Markdown task'.
    删 入路. 删 出路. 删 大路.
    显 'TOTAL PASS: '+(次数[0] 为 句).
    得 0.
法
