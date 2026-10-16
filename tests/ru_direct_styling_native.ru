# Windows-only direct-style acceptance. Real native controls, no C shim or Wine.
# Imported comparison helpers inspect every text/style byte and every fold level.
密 取 外言 '如:密'.
窗 取 外言 '../src/win32.ru'.
编 取 外言 '../src/editor.ru'.
语 取 外言 '../src/syntax.ru'.
如语 取 外言 '../src/ru_syntax.ru'.
词 取 外言 '../src/ru_native_syntax.ru'.
基 取 外言 'ru_syntax_native.ru'.
_SetWindowSubclass 取 (窗 其 控件) 其 绑定 'SetWindowSubclass' (密 其 签名 (窗 其 I) ([(窗 其 PTR),(窗 其 PTR),(窗 其 UP),(窗 其 UP)]) 'win64').
_RemoveWindowSubclass 取 (窗 其 控件) 其 绑定 'RemoveWindowSubclass' (密 其 签名 (窗 其 I) ([(窗 其 PTR),(窗 其 PTR),(窗 其 UP)]) 'win64').
_DefSubclassProc 取 (窗 其 控件) 其 绑定 'DefSubclassProc' (密 其 签名 (窗 其 IP) ([(窗 其 PTR),(窗 其 U),(窗 其 UP),(窗 其 IP)]) 'win64').
_SetParent 取 (窗 其 用户) 其 绑定 'SetParent' (密 其 签名 (窗 其 PTR) ([(窗 其 PTR),(窗 其 PTR)]) 'win64').
_GetDesktopWindow 取 (窗 其 用户) 其 绑定 'GetDesktopWindow' (密 其 签名 (窗 其 PTR) ([]) 'win64').
_子型 取 密 其 签名 (窗 其 IP) ([(窗 其 PTR),(窗 其 U),(窗 其 UP),(窗 其 IP),(窗 其 UP),(窗 其 UP)]) 'win64'.
次数 取 [0].
路由 取 {}.
源 取 "算 示范:\n    若 真 则\n        得 '甲😀'.\n    另\n        得 42.\n    然\n法\n".
作 确认 条件 为 事实 文 为 句:
    若 非 条件 则 卒 'FAIL: '+文. 然
    次数[0] 取 次数[0]+1.
    显 'PASS: '+文.
为
算 过程 柄 消息 宽 长:
    得 基 其 过程 柄 消息 宽 长.
法
算 子过程 柄 消息 宽 长 号 引:
    计 取 路由 其 查 (柄 其 句).
    若 计 != 空 则
        码 取 消息 其 数.
        计 其 增 'all' (计['all']+1).
        若 码 == 2032 或 码 == 2033 或 码 == 2073 则 计 其 增 'style' (计['style']+1). 然
        若 码 == 2032 则 计 其 增 'start' (计['start']+1). 然
        若 码 == 2033 则 计 其 增 'correction' (计['correction']+1). 然
        若 码 == 2073 则 计 其 增 'bulk' (计['bulk']+1). 然
        若 码 == 2222 则 计 其 增 'fold' (计['fold']+1). 然
        若 码 == 2378 且 计['mode'] == 'invalidate-mask-query' 则
            计 其 增 'mode' ''.
            语 其 选择 柄 'plain'.
        然
        若 码 == 2185 则
            计 其 增 'pointer' (计['pointer']+1).
            若 计['mode'] == 'null' 则 得 0. 然
            若 计['mode'] == 'invalidate' 则
                计 其 增 'mode' ''.
                语 其 选择 柄 'plain'.
            然
        然
    然
    得 窗 其 结果 (_DefSubclassProc 其 调用 [柄,消息,宽,长]).
法
算 清计 柄:
    计 取 {'all':0,'style':0,'start':0,'correction':0,'bulk':0,'pointer':0,'fold':0,'mode':''}.
    路由 其 增 (柄 其 句) 计.
    得 计.
法
算 准备 柄 文 为 句:
    语 其 选择 柄 'plain'.
    编 其 设文本 柄 文.
    语 其 选择 柄 'ru'.
    得 如语 其 _状态 柄.
法
算 新批 态 文 为 句:
    词态 取 词 其 新状态.
    果 取 词 其 扫描 词态 文 真 (-1).
    果 其 增 'batchGeneration' 态['generation'].
    果 其 增 'batchRevision' 态['revision'].
    得 [词态,果].
法
作 拒批 柄 态 果 长 为 数 名 为 句:
    计 取 清计 柄.
    拒 取 [假].
    试 如语 其 _施样 柄 态 果 长. 救 原因 拒[0] 取 真. 终
    确认 (拒[0] 且 计['style'] == 0 且 计['fold'] == 0 且 计['pointer'] == 0) 名.
为
作 验回退 柄 参 计 名 为 句:
    合 取 语 其 排空 柄.
    确认 (合['enabled'] 且 计['style'] > 0 且 计['pointer'] == 0 且 (基 其 全部相同 柄 参)) 名.
为
算 元初 参数 为 句 阵:
    库 取 密 其 动态库 ((窗 其 目录)+'Scintilla.dll').
    实例 取 窗 其 成功 ((窗 其 GetModuleHandleW) 其 调用 [空]) 'instance'.
    类名 取 密 其 UTF16 'RuNotepad.DirectStyleFixture'.
    回调 取 密 其 回调 (窗 其 WNDPROC) (算 过程) 0.
    子回调 取 密 其 回调 _子型 (算 子过程) 0.
    类 取 (窗 其 WNDCLASS) 其 新建.
    类 其 写 'size' ((窗 其 WNDCLASS) 其 大小).
    类 其 写 'proc' (回调 其 地址).
    类 其 写 'instance' 实例.
    类 其 写 'name' (类名 其 地址).
    窗 其 成功 ((窗 其 RegisterClassExW) 其 调用 [类]) 'register direct-style fixture'.
    父 取 窗 其 控制 空 实例 'RuNotepad.DirectStyleFixture' 'Direct style acceptance' 13565952 0.
    另父 取 窗 其 控制 空 实例 'RuNotepad.DirectStyleFixture' 'Other parent' 13565952 0.
    甲 取 编 其 创建 父 实例 1.
    乙 取 编 其 创建 父 实例 2.
    窗 其 成功 (_SetWindowSubclass 其 调用 [甲,子回调 其 地址,991,0]) 'subclass direct editor'.
    窗 其 成功 (_SetWindowSubclass 其 调用 [乙,子回调 其 地址,991,0]) 'subclass message editor'.
    确认 ((如语 其 _直库态)['ready']) 'the pinned DLL exports a securely preflighted ordinary Win64 direct binding'.
    # This is a real foreign-owner HWND front-door rejection test. It does not
    # claim to execute cross-thread Scintilla or send Scintilla codes to desktop.
    桌面 取 窗 其 结果 (_GetDesktopWindow 其 调用 []).
    所属 取 窗 其 结果 ((如语 其 _GetWindowThreadProcessId) 其 调用 [桌面,空]).
    本线程 取 窗 其 结果 ((如语 其 _GetCurrentThreadId) 其 调用 []).
    确认 (非 (所属 其 为空) 且 所属 其 句 != 本线程 其 句 且 非 (如语 其 登记直属 桌面 父)) 'actual foreign-owned desktop HWND is rejected before any Scintilla query'.
    确认 (非 (如语 其 登记直属 空 父) 且 非 (如语 其 登记直属 甲 另父)) 'null and wrong-parent registration are rejected'.

    准备 甲 源.
    准备 乙 源.
    确认 ((窗 其 发送 甲 2378 0 0) 其 数 != 3 且 非 (如语 其 登记直属 甲 父)) 'default-all notification fixture cannot acquire direct capability'.
    甲计 取 清计 甲.
    乙计 取 清计 乙.
    语 其 排空 乙.
    验回退 甲 乙 甲计 'default-all whole batch retains original messages and exact text/styles/folds'.
    确认 (甲计['start'] > 0 且 甲计['correction'] > 0 且 甲计['bulk'] > 0) 'original-route positive control observes all three2032/2033/2073 child subclass messages'.
    窗 其 发送 甲 2359 3 0.
    窗 其 发送 乙 2359 3 0.
    准备 甲 源.
    甲计 取 清计 甲.
    验回退 甲 乙 甲计 'mask3 without explicit exclusive-document registration still uses original messages'.

    准备 甲 源.
    确认 (如语 其 登记直属 甲 父) 'same-thread owned mask3 editor explicitly opts into direct styles'.
    甲计 取 清计 甲.
    语 其 排空 甲.
    确认 (甲计['pointer'] > 0 且 甲计['start'] == 0 且 甲计['correction'] == 0 且 甲计['bulk'] == 0 且 甲计['style'] == 0 且 甲计['fold'] > 0 且 (基 其 全部相同 甲 乙)) 'direct-route proof bypasses all three2032/2033/2073 child subclass messages while folds retain messages and all bytes match'.
    确认 ((编 其 文本 甲) == 源 且 非 (编 其 已变 甲) 且 (窗 其 发送 甲 2174 0 0) 其 为空) 'direct highlighting preserves source, clean savepoint and empty undo'.
    窗 其 发送 甲 2160 0 3.
    窗 其 发文 甲 2170 0 '批'.
    选始 取 (窗 其 发送 甲 2009 0 0) 其 数.
    选末 取 (窗 其 发送 甲 2008 0 0) 其 数.
    甲计 取 清计 甲.
    语 其 排空 甲.
    基 其 重置 乙 ('批'+源[1:]).
    确认 (甲计['pointer'] > 0 且 甲计['correction'] == 0 且 甲计['bulk'] == 0 且 (编 其 已变 甲) 且 (基 其 全部相同 甲 乙) 且 (窗 其 发送 甲 2009 0 0) 其 数 == 选始 且 (窗 其 发送 甲 2008 0 0) 其 数 == 选末) 'edited direct generation equals independent fresh styles/folds and preserves dirty selection'.
    窗 其 发送 甲 2176 0 0.
    语 其 排空 甲.
    基 其 重置 乙 源.
    确认 ((编 其 文本 甲) == 源 且 非 (编 其 已变 甲) 且 (基 其 全部相同 甲 乙)) 'direct styling does not add undo steps or disturb restored savepoint'.
    窗 其 发送 甲 2011 0 0.
    语 其 排空 甲.
    确认 ((编 其 文本 甲) == '批'+源[1:] 且 (编 其 已变 甲) 且 (编 其 文本 乙) == 源) 'redo remains text-only and a second editor stays independent'.

    大文 取 源.
    循 9 次 大文 取 大文+大文. 环
    准备 甲 大文.
    如语 其 登记直属 甲 父.
    甲计 取 清计 甲.
    语 其 推进 甲 0.001.
    中 取 语 其 状态 甲.
    确认 (中['pending'] 且 中['feed'] > 0 且 甲计['pointer'] > 0 且 甲计['style'] == 0) 'large direct document publishes a bounded prefix without pumping or completing the queued suffix'.
    窗 其 发送 甲 2160 22272 22272.
    窗 其 发文 甲 2170 0 '批. inserted\n'.
    预期 取 大文[0:(源 其 量)*256]+'批. inserted\n'+大文[(源 其 量)*256:].
    合 取 语 其 排空 甲.
    基 其 重置 乙 预期.
    确认 (合['enabled'] 且 甲计['pointer'] > 1 且 甲计['correction'] == 0 且 甲计['bulk'] == 0 且 (基 其 全部相同 甲 乙) 且 (编 其 文本 甲) == 预期) 'edit during pending multichunk direct work matches every fresh text/style byte and fold'.
    窗 其 发送 甲 2176 0 0.
    语 其 排空 甲.
    基 其 重置 乙 大文.
    确认 ((基 其 全部相同 甲 乙) 且 (编 其 文本 甲) == 大文 且 非 (编 其 已变 甲)) 'multichunk direct work and pending edits preserve one-step undo and all fold levels'.
    基 其 重置 乙 源.

    # Two genuine Scintilla views share one document; neither is registered.
    共享 取 编 其 创建 父 实例 4.
    窗 其 发送 共享 2358 0 (窗 其 发送 乙 2357 0 0).
    窗 其 发送 共享 2359 3 0.
    语 其 选择 共享 'ru'.
    窗 其 成功 (_SetWindowSubclass 其 调用 [共享,子回调 其 地址,991,0]) 'subclass shared view'.
    共计 取 清计 共享.
    语 其 排空 共享.
    确认 (共计['pointer'] == 0 且 共计['start'] > 0 且 共计['correction'] > 0 且 共计['bulk'] > 0 且 (基 其 全部相同 共享 乙)) 'unregistered shared-document view keeps all three original style messages'.
    语 其 遗忘 共享.
    窗 其 成功 (_RemoveWindowSubclass 其 调用 [共享,子回调 其 地址,991]) 'remove shared subclass'.
    窗 其 成功 ((窗 其 DestroyWindow) 其 调用 [共享]) 'destroy shared fixture view'.

    # Every selection creates a new state and discards the old capability.
    旧态 取 如语 其 _状态 甲.
    准备 甲 源.
    确认 (旧态['direct'] == 空 且 ((如语 其 _状态 甲)['direct']) == 空) 'language reselection revokes both old and new unregistered capabilities'.
    甲计 取 清计 甲.
    验回退 甲 乙 甲计 'reselected editor stays on original route until owning caller registers again'.
    准备 甲 源.
    如语 其 登记直属 甲 父.
    窗 其 发送 甲 2359 65535 0.
    甲计 取 清计 甲.
    验回退 甲 乙 甲计 'changed modification mask rejects direct eligibility before first batch mutation'.
    窗 其 发送 甲 2359 3 0.
    准备 甲 源.
    如语 其 登记直属 甲 父.
    窗 其 成功 (_SetParent 其 调用 [甲,另父]) 'move fixture to different parent'.
    甲计 取 清计 甲.
    验回退 甲 乙 甲计 'actual parent change selects complete original-message batch'.
    窗 其 成功 (_SetParent 其 调用 [甲,父]) 'restore fixture parent'.
    准备 甲 源.
    如语 其 登记直属 甲 父.
    (如语 其 _直库态) 其 增 'ready' 假.
    甲计 取 清计 甲.
    验回退 甲 乙 甲计 'injected unavailable-ready state safely retains original styles'.
    (如语 其 _直库态) 其 增 'ready' 真.
    准备 甲 源.
    如语 其 登记直属 甲 父.
    甲计 取 清计 甲.
    甲计 其 增 'mode' 'null'.
    合 取 语 其 排空 甲.
    确认 (合['enabled'] 且 甲计['pointer'] > 0 且 甲计['style'] > 0 且 (基 其 全部相同 甲 乙)) 'null direct context selects original batch before any direct mutation'.

    态 取 准备 甲 源.
    如语 其 登记直属 甲 父.
    批 取 新批 态 源.
    果 取 批[1].
    长 取 (窗 其 发送 甲 2183 0 0) 其 数.
    真长 取 果['styleLength'].
    果 其 增 'styleLength' (真长+1).
    拒批 甲 态 果 长 'invalid contiguous style bound rejects whole batch before pointer acquisition or writes'.
    果 其 增 'styleLength' 真长.
    原段 取 果['spans'].
    果 其 增 'spans' [[0,65,4]].
    拒批 甲 态 果 长 'invalid correction span rejects whole batch before pointer acquisition or writes'.
    果 其 增 'spans' 原段.
    原折 取 果['folds'].
    果 其 增 'folds' [[999999,0,假]].
    拒批 甲 态 果 长 'invalid fold rejects styles as well as folds before pointer acquisition'.
    果 其 增 'folds' 原折.
    果 其 增 'batchRevision' (态['revision']+1).
    拒批 甲 态 果 长 'stale batch revision is rejected on both routes without replay'.
    果 其 增 'batchRevision' 态['revision'].
    准备 甲 源.
    拒批 甲 态 果 长 'stale generation with same HWND and document cannot publish through fallback'.
    词 其 释放 批[0].

    准备 甲 源.
    如语 其 登记直属 甲 父.
    甲计 取 清计 甲.
    甲计 其 增 'mode' 'invalidate-mask-query'.
    语 其 推进 甲 8.
    确认 (甲计['pointer'] == 0 且 甲计['style'] == 0 且 (语 其 状态 甲) == 空 且 (编 其 文本 甲) == 源 且 非 (编 其 已变 甲)) 'eligibility-query callback invalidation cannot replay stale styles on fallback route'.

    # A synchronous subclass callback at GETDIRECTPOINTER may invalidate state.
    # The pure-Ru post-query guard must drop its borrowed pointer before writing.
    准备 甲 源.
    如语 其 登记直属 甲 父.
    甲计 取 清计 甲.
    甲计 其 增 'mode' 'invalidate'.
    语 其 推进 甲 8.
    确认 (甲计['pointer'] == 1 且 甲计['style'] == 0 且 (语 其 状态 甲) == 空 且 (编 其 文本 甲) == 源 且 非 (编 其 已变 甲)) 'pointer-query callback invalidation prevents direct writes and preserves editable source'.

    态 取 准备 甲 源.
    如语 其 登记直属 甲 父.
    编 其 开始载入 甲 1.
    确认 (非 (语 其 推进 甲 8) 且 (语 其 状态 甲) == 空 且 态['direct'] == 空) 'document replacement invalidates queued capability before next tick'.
    准备 甲 源.
    甲计 取 清计 甲.
    验回退 甲 乙 甲计 'replacement document receives no inherited direct capability'.
    如语 其 登记直属 甲 父.
    态 取 如语 其 _状态 甲.
    语 其 遗忘 甲.
    窗 其 成功 (_RemoveWindowSubclass 其 调用 [甲,子回调 其 地址,991]) 'remove first subclass'.
    窗 其 成功 ((窗 其 DestroyWindow) 其 调用 [甲]) 'destroy first editor'.
    确认 (态['direct'] == 空 且 非 (语 其 推进 甲 8) 且 (语 其 状态 甲) == 空) 'explicit close clears capability and destroyed HWND cannot resume'.
    丙 取 编 其 创建 父 实例 3.
    窗 其 发送 丙 2359 3 0.
    准备 丙 源.
    确认 (((如语 其 _状态 丙)['direct']) == 空 且 (如语 其 登记直属 丙 父)) 'recreated editor needs fresh explicit registration even if HWND value is recycled'.
    语 其 排空 丙.
    确认 ((基 其 全部相同 丙 乙) 且 非 (编 其 已变 丙) 且 (窗 其 发送 丙 2174 0 0) 其 为空) 'recreated direct editor independently preserves full output and undo'.
    语 其 遗忘 丙.
    语 其 遗忘 乙.
    窗 其 成功 (_RemoveWindowSubclass 其 调用 [乙,子回调 其 地址,991]) 'remove second subclass'.
    确认 ((如语 其 存活上下文) == 0) 'direct fixture releases every lexical checkpoint and capability'.
    窗 其 成功 ((窗 其 DestroyWindow) 其 调用 [父]) 'destroy fixture parent'.
    窗 其 成功 ((窗 其 DestroyWindow) 其 调用 [另父]) 'destroy other parent'.
    窗 其 成功 ((窗 其 UnregisterClassW) 其 调用 [类名,实例]) 'unregister direct fixture'.
    类 其 关闭. 类名 其 关闭. 回调 其 关闭. 子回调 其 关闭.
    显 'TOTAL PASS: '+(次数[0] 为 句).
    得 0.
法
