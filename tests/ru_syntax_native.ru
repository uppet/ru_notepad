# Native Windows x64 acceptance. No Wine: cross-compilation is not execution.
密 取 外言 '如:密'.
窗 取 外言 '../src/win32.ru'.
编 取 外言 '../src/editor.ru'.
语 取 外言 '../src/syntax.ru'.
如语 取 外言 '../src/ru_syntax.ru'.
原桥 取 外言 '../src/ru_native_syntax.ru'.
策 取 外言 '../src/syntax_policy.ru'.
通知型 取 密 其 结构 [['header',窗 其 NMHDR],['position',窗 其 IP],['ch',窗 其 I],['modifiers',窗 其 I],['modificationType',窗 其 I],['text',窗 其 PTR],['length',窗 其 IP],['linesAdded',窗 其 IP]].
# Pinned SCI_GETSTYLEDTEXTFULL (2778): Sci_TextRangeFull has two intptr
# positions and one pointer. Each bounded window returns 2*N bytes plus two NULs.
样范围型 取 密 其 结构 [['start',窗 其 IP],['end',窗 其 IP],['text',窗 其 PTR]].
# Two integer-only 1024-byte blocks, two terminator bytes, then a checked canary.
比较存型 取 密 其 结构 [['block0',原桥 其 _事件批型],['block1',原桥 其 _事件批型],['terminator',窗 其 W],['guard',窗 其 W]].
比较库 取 密 其 系统库 'msvcrt.dll'.
memcmp 取 比较库 其 绑定 'memcmp' (密 其 签名 (窗 其 I) ([(窗 其 PTR),(窗 其 PTR),(窗 其 UP)]) 'win64').
次数 取 [0].
通知 取 {'text':0,'needed':0,'other':0}.
初始化故障 取 [空,假].
算 故障复制 态:
    初始化故障[0] 取 态.
    初始化故障[1] 取 态['references'] == 1 且 态['native'] != 空.
    卒 'injected initial checkpoint copy failure'.
法
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
        源 取 头 其 读 'hwndFrom'.
        号 取 (头 其 读 'code') 其 数.
        若 号 == 2000 则
            通知 其 增 'needed' (通知['needed']+1).
            语 其 请求 源 ((项 其 读 'position') 其 数).
        然
        若 号 == 2008 则
            类 取 (项 其 读 'modificationType') 其 数.
            若 类 % 4 != 0 则
                通知 其 增 'text' (通知['text']+1).
                语 其 变化 源 ((项 其 读 'position') 其 数) ((项 其 读 'length') 其 数) ((项 其 读 'linesAdded') 其 数) 类.
            另 通知 其 增 'other' (通知['other']+1). 然
        然
        项 其 关闭.
        得 0.
    然
    得 窗 其 结果 ((窗 其 DefWindowProcW) 其 调用 [柄,消息,宽,长]).
法
算 样式 柄 位 为 数:
    得 (窗 其 发送 柄 2038 位 0) 其 数.
法
作 验样式 柄 始 为 数 长 为 数 色 为 数 文 为 句:
    合格 取 真.
    位 取 始.
    循 长 次
        若 (样式 柄 位) != 色 则 合格 取 假. 然
        位 取 位+1.
    环
    确认 合格 文.
为
算 重置 柄 文 为 句:
    语 其 选择 柄 'plain'.
    编 其 设文本 柄 文.
    语 其 选择 柄 'ru'.
    得 语 其 排空 柄.
法
算 全部相同 甲 乙:
    长 取 (窗 其 发送 甲 2183 0 0) 其 数.
    若 (窗 其 发送 乙 2183 0 0) 其 数 != 长 则 得 假. 然
    合格 取 真.
    若 (样范围型 其 大小) != 24 或 (比较存型 其 偏移 'guard') != 2050 则 得 假. 然
    # 如密 新建 zero-initializes storage; a nonzero guard follows capacity2050.
    甲存 取 比较存型 其 新建.
    乙存 取 比较存型 其 新建.
    甲存 其 写 'guard' 23130.
    乙存 其 写 'guard' 23130.
    甲域 取 样范围型 其 新建.
    乙域 取 样范围型 其 新建.
    试
        甲域 其 写 'text' (甲存 其 地址).
        乙域 其 写 'text' (乙存 其 地址).
        位 取 0.
        循
            若 位 >= 长 则 破. 然
            末 取 位+1024.
            若 末 > 长 则 末 取 长. 然
            甲域 其 写 'start' 位. 甲域 其 写 'end' 末.
            乙域 其 写 'start' 位. 乙域 其 写 'end' 末.
            双长 取 2*(末-位).
            若 (窗 其 发指 甲 2778 0 甲域) 其 数 != 双长 或 (窗 其 发指 乙 2778 0 乙域) 其 数 != 双长 则 合格 取 假. 破. 然
            若 (甲存 其 读 'guard') 其 数 != 23130 或 (乙存 其 读 'guard') 其 数 != 23130 则 合格 取 假. 破. 然
            若 (窗 其 结果 (memcmp 其 调用 [甲存,乙存,双长])) 其 数 != 0 则 合格 取 假. 破. 然
            位 取 末.
        环
    救 原因
        甲域 其 关闭. 乙域 其 关闭.
        甲存 其 关闭. 乙存 其 关闭.
        卒 原因.
    终
    甲域 其 关闭. 乙域 其 关闭.
    甲存 其 关闭. 乙存 其 关闭.
    若 非 合格 则 得 假. 然
    行数 取 (窗 其 发送 甲 2154 0 0) 其 数.
    若 (窗 其 发送 乙 2154 0 0) 其 数 != 行数 则 得 假. 然
    行 取 0.
    循 行数 次
        若 (窗 其 发送 甲 2223 行 0) 其 数 != (窗 其 发送 乙 2223 行 0) 其 数 则 得 假. 然
        行 取 行+1.
    环
    得 (窗 其 发送 甲 2236 0 0) 其 数 == 1 且 (窗 其 发送 乙 2236 0 0) 其 数 == 1.
法
作 矩阵一项 甲 乙 基文 为 句 始 为 数 末 为 数 替文 为 句 预期 为 句 标签 为 句:
    重置 甲 基文.
    前 取 语 其 状态 甲.
    窗 其 发送 甲 2160 始 末.
    窗 其 发文 甲 2170 0 替文.
    中 取 语 其 状态 甲.
    确认 (中['pending'] 且 中['revision'] > 前['revision'] 且 中['generation'] == 前['generation'] 且 (编 其 文本 甲) == 预期 且 (编 其 已变 甲)) (标签+' unequal edit queues its own revision and preserves exact dirty text').
    选始 取 (窗 其 发送 甲 2009 0 0) 其 数.
    选末 取 (窗 其 发送 甲 2008 0 0) 其 数.
    合 取 语 其 排空 甲.
    参 取 重置 乙 预期.
    # A late request/timer must not resurrect the previous edit revision.
    语 其 请求 甲 100000.
    语 其 推进 甲 8.
    确认 (合['enabled'] 且 参['enabled'] 且 非 (语 其 待办 甲) 且 (窗 其 发送 甲 2009 0 0) 其 数 == 选始 且 (窗 其 发送 甲 2008 0 0) 其 数 == 选末 且 (全部相同 甲 乙)) (标签+' incremental text/styles/all fold levels equal an independent fresh scan').
    窗 其 发送 甲 2176 0 0.
    合 取 语 其 排空 甲.
    确认 (合['enabled'] 且 (编 其 文本 甲) == 基文 且 非 (编 其 已变 甲)) (标签+' highlighting preserves one-edit undo and the original savepoint').
为
作 编辑矩阵 甲 乙 单文 为 句:
    # Fixed representative fixture: 512*87 = 44,544 UTF-8 bytes, including
    # nested folds, Han and emoji. Production never uses these whole-text copies.
    基文 取 单文.
    循 9 次 基文 取 基文+基文. 环
    中字 取 (单文 其 量)*256.
    插文 取 '批. matrix\n'.
    矩阵一项 甲 乙 基文 0 0 插文 (插文+基文) 'BOF insertion'.
    矩阵一项 甲 乙 基文 0 12 '' 基文[6:] 'BOF deletion'.
    矩阵一项 甲 乙 基文 22272 22272 插文 (基文[0:中字]+插文+基文[中字:]) 'middle insertion'.
    矩阵一项 甲 乙 基文 22272 22284 '' (基文[0:中字]+基文[中字+6:]) 'middle deletion'.
    尾文 取 "得 '尾😀'.\n".
    矩阵一项 甲 乙 基文 44544 44544 尾文 (基文+尾文) 'EOF insertion'.
    矩阵一项 甲 乙 基文 44540 44544 '' 基文[0:(基文 其 量)-2] 'EOF deletion'.
    重置 甲 基文.
    窗 其 发送 甲 2160 0 0.
    窗 其 发文 甲 2170 0 "'".
    语 其 推进 甲 0.001.
    中 取 语 其 状态 甲.
    确认 (中['pending'] 且 中['feed'] > 0) 'matrix multiline edit has published a bounded prefix while work remains pending'.
    # Edit the middle while the quote-state suffix is queued, then retract the
    # opener before it finishes. Only the final revision may survive.
    窗 其 发送 甲 2160 22273 22273.
    窗 其 发文 甲 2170 0 插文.
    窗 其 发送 甲 2160 0 1.
    窗 其 发文 甲 2170 0 ''.
    合 取 语 其 排空 甲.
    预期 取 基文[0:中字]+插文+基文[中字:].
    参 取 重置 乙 预期.
    语 其 请求 甲 100000.
    语 其 推进 甲 8.
    确认 (合['enabled'] 且 合['revision'] >= 3 且 参['enabled'] 且 (编 其 文本 甲) == 预期 且 (全部相同 甲 乙)) 'repeated edits during pending work discard old states and match every fresh byte style and fold level'.
为
作 性能 柄 大小 为 数:
    # 100 KB is one long line; 1 MB is 200,000 short lines. Both keep
    # the same byte footprint and exact full-state convergence assertions.
    文 取 'a=1.\n'.
    若 大小 == 100000 则 文 取 'a=1. '. 然
    循 18 次 文 取 文+文. 环
    文 取 文[0:大小].
    语 其 选择 柄 'plain'.
    编 其 设文本 柄 文.
    起时 取 如语 其 _时刻.
    语 其 选择 柄 'ru'.
    初 取 语 其 状态 柄.
    确认 (初['feed'] == 0 且 初['pending']) 'large Ru selection only queues work'.
    语 其 排空 柄.
    初时 取 (如语 其 _时刻)-起时.
    初 取 语 其 状态 柄.
    确认 (初['enabled'] 且 非 初['pending']) 'large Ru initial scan completes'.
    确认 (初['readBytes'] == 大小) 'initial scan reads source exactly once in bounded chunks'.
    确认 (初['maxRead'] > 0 且 初['maxRead'] <= 1024) 'no native range exceeds 1024 UTF-8 bytes'.
    窗 其 发送 柄 2160 0 1.
    起时 取 如语 其 _时刻.
    窗 其 发文 柄 2170 0 'b'.
    语 其 排空 柄.
    改时 取 (如语 其 _时刻)-起时.
    后 取 语 其 状态 柄.
    确认 (后['converged'] 且 后['reusedBytes'] > 0) 'same-byte edit proves full-state checkpoint convergence'.
    确认 (后['editReadBytes'] > 0 且 后['editReadBytes'] <= 65536) 'ordinary edit does not rescan the full document'.
    确认 ((窗 其 发送 柄 2183 0 0) 其 数 == 大小) 'performance edit preserves document length'.
    验样式 柄 0 1 8 'same-byte replacement retains Ru identifier byte style'.
    确认 (编 其 已变 柄) 'background styling preserves edited dirty state'.
    窗 其 发送 柄 2176 0 0.
    语 其 排空 柄.
    确认 (非 (编 其 已变 柄)) 'single undo after background scan reaches original savepoint'.
    显 'PERF_RU size='+(大小 为 句)+' initial_ms='+(初时 为 句)+' edit_ms='+(改时 为 句)+' initial_read_bytes='+(初['readBytes'] 为 句)+' edit_read_bytes='+(后['editReadBytes'] 为 句)+' reused_bytes='+(后['reusedBytes'] 为 句)+' max_read='+(后['maxRead'] 为 句)+' max_tick_ms='+(后['maxTickMs'] 为 句)+' max_chunk_ms='+(后['maxChunkMs'] 为 句).
    若 大小 == 100000 则
        窗 其 发送 柄 2160 0 1.
        窗 其 发文 柄 2170 0 'b'.
        窗 其 发送 柄 2160 50000 50001.
        窗 其 发文 柄 2170 0 'c'.
        合 取 语 其 排空 柄.
        确认 (合['converged'] 且 合['editReadBytes'] <= 65536) 'two distant coalesced replacements converge only after both changed ranges'.
        确认 ((样式 柄 0) == 8 且 (样式 柄 50000) == 8) 'both coalesced replacements receive correct byte styles'.
        窗 其 发送 柄 2176 0 0.
        窗 其 发送 柄 2176 0 0.
        语 其 排空 柄.
        确认 (非 (编 其 已变 柄)) 'two edits retain their original undo history through convergence'.
        窗 其 发送 柄 2160 0 0.
        窗 其 发文 柄 2170 0 'b'.
        窗 其 发送 柄 2160 2 3.
        窗 其 发文 柄 2170 0 ''.
        合 取 语 其 排空 柄.
        确认 (合['converged'] 且 合['reusedBytes'] > 0) 'insertion and deletion at different positions can safely converge'.
        验样式 柄 0 3 8 'net-zero shifted replacement has correct combined identifier style'.
        # Publish a temporary multiline state beyond an old checkpoint, then
        # restore the source. Reuse must not preserve those temporary styles.
        窗 其 发送 柄 2160 0 0.
        窗 其 发文 柄 2170 0 "'".
        循
            中态 取 语 其 状态 柄.
            若 非 中态['pending'] 或 中态['feed'] >= 40000 则 破. 然
            语 其 推进 柄 8.
        环
        窗 其 发送 柄 2160 0 1.
        窗 其 发文 柄 2170 0 ''.
        合 取 语 其 排空 柄.
        确认 ((窗 其 发送 柄 2183 0 0) 其 数 == 大小 且 (样式 柄 35000) == 8 且 合['editReadBytes'] >= 65536) 'net-zero edit revisits styles published beyond an intermediate checkpoint'.
    然
为
算 元初 参数 为 句 阵:
    库 取 密 其 动态库 ((窗 其 目录)+'Scintilla.dll').
    实例 取 窗 其 成功 ((窗 其 GetModuleHandleW) 其 调用 [空]) 'instance'.
    类名 取 密 其 UTF16 'RuNotepad.RuSyntaxFixture'.
    回调 取 密 其 回调 (窗 其 WNDPROC) (算 过程) 0.
    类 取 (窗 其 WNDCLASS) 其 新建.
    类 其 写 'size' ((窗 其 WNDCLASS) 其 大小).
    类 其 写 'proc' (回调 其 地址).
    类 其 写 'instance' 实例.
    类 其 写 'name' (类名 其 地址).
    窗 其 成功 ((窗 其 RegisterClassExW) 其 调用 [类]) 'register fixture'.
    父 取 窗 其 控制 空 实例 'RuNotepad.RuSyntaxFixture' 'Ru syntax native acceptance' 13565952 0.
    甲 取 编 其 创建 父 实例 1.
    乙 取 编 其 创建 父 实例 2.
    # Each isolated helper failure is real, separately classified, and ordinary.
    缺因 取 ''.
    若 策 其 含词 参数 '--expect-missing-helper' 则 缺因 取 'RuSyntax.dll could not be loaded'. 然
    若 策 其 含词 参数 '--expect-bad-helper' 则 缺因 取 'does not export the required scanner API'. 然
    若 策 其 含词 参数 '--expect-wrong-helper-abi' 则 缺因 取 'incompatible ABI version'. 然
    若 缺因 != '' 则
        确认 ((语 其 初始化) 其 含 缺因) ('actual helper preflight reports '+缺因).
        确认 ((语 其 选择 甲 'cpp') == 'cpp') 'helper failure leaves the independent Lexilla C++ lexer available'.
        文 取 '算 f:\n得 1.\n法\n'.
        编 其 设文本 甲 文.
        窗 其 发送 甲 2160 0 3.
        确认 ((语 其 选择 甲 'ru') == 'plain') 'failed helper selection explicitly returns plain'.
        语 其 请求 甲 100.
        语 其 推进 甲 8.
        态 取 语 其 状态 甲.
        确认 (非 态['enabled'] 且 非 态['pending'] 且 态['readBytes'] == 0 且 (态['warning'] 其 含 缺因)) 'failed helper exposes labelled disabled state without scheduling work'.
        验样式 甲 0 18 0 'failed helper leaves all source bytes in plain style'.
        确认 ((编 其 文本 甲) == 文 且 非 (编 其 已变 甲) 且 (窗 其 发送 甲 2174 0 0) 其 为空 且 (窗 其 发送 甲 2008 0 0) 其 数 == 3) 'helper fallback preserves exact source, clean state, undo and selection'.
        窗 其 发送 甲 2160 0 3.
        窗 其 发文 甲 2170 0 '得'.
        确认 ((编 其 已变 甲) 且 (编 其 文本 甲) != 文) 'plain fallback remains editable after helper failure'.
        窗 其 发送 甲 2176 0 0.
        确认 ((编 其 文本 甲) == 文 且 非 (编 其 已变 甲) 且 (窗 其 发送 甲 2236 0 0) 其 数 == 1 且 (窗 其 发送 甲 2243 2 0) 其 数 == 0) 'fallback undo restores clean text with all lines visible and folding disabled'.
        语 其 遗忘 甲.
        语 其 遗忘 乙.
        窗 其 成功 ((窗 其 DestroyWindow) 其 调用 [父]) 'destroy helper fallback fixture'.
        窗 其 成功 ((窗 其 UnregisterClassW) 其 调用 [类名,实例]) 'unregister helper fallback fixture'.
        类 其 关闭.
        类名 其 关闭.
        回调 其 关闭.
        显 'TOTAL PASS: '+(次数[0] 为 句).
        得 0.
    然
    若 策 其 含词 参数 '--expect-missing-lexilla' 则
        确认 ((语 其 初始化) 其 含 'could not be loaded') 'isolated run has genuinely missing Lexilla'.
        文 取 '算 f:\n得 1.\n法\n'.
        编 其 设文本 甲 文.
        确认 ((语 其 选择 甲 'ru') == 'ru') 'Ru selection succeeds without Lexilla'.
        态 取 语 其 排空 甲.
        确认 (态['enabled'] 且 态['warning'] == '') 'Ru scan succeeds without Lexilla'.
        验样式 甲 0 3 4 'Ru keyword bytes are styled without Lexilla'.
        确认 ((窗 其 发送 甲 2223 0 0) 其 数 == 9216) 'Ru fold header is generated without Lexilla'.
        语 其 全折 甲 0.
        确认 ((窗 其 发送 甲 2228 1 0) 其 数 == 0) 'Ru collapse hides native lines without Lexilla'.
        确认 ((语 其 选择 甲 'cpp') == 'plain' 且 (窗 其 发送 甲 2236 0 0) 其 数 == 1) 'only missing C++ lexer falls back and reveals folds'.
        确认 ((编 其 文本 甲) == 文 且 非 (编 其 已变 甲)) 'missing Lexilla never changes source or dirty state'.
        语 其 遗忘 甲.
        语 其 遗忘 乙.
        窗 其 成功 ((窗 其 DestroyWindow) 其 调用 [父]) 'destroy isolated fixture'.
        窗 其 成功 ((窗 其 UnregisterClassW) 其 调用 [类名,实例]) 'unregister isolated fixture'.
        类 其 关闭.
        类名 其 关闭.
        回调 其 关闭.
        显 'TOTAL PASS: '+(次数[0] 为 句).
        得 0.
    然
    边头 取 (密 其 u64) 其 值 '536870895877895'.
    边码 取 原桥 其 _头数 边头.
    确认 (边码 == 536870895877895 且 (边码-(边码 % 16777216))/16777216 == 31999999 且 边码 % 256 == 7 且 ((边码 % 65536)-(边码 % 256))/256 == 255 且 ((边码 % 16777216)-(边码 % 65536))/65536 == 9) 'checked low49 decoding preserves event coordinates near the 32 MB boundary'.
    拒头 取 [假].
    试
        原桥 其 _头数 ((密 其 u64) 其 值 '18446744073709551615').
    救 原因
        拒头[0] 取 (原因 为 句) 其 含 'oversized event head bits'.
    终
    确认 拒头[0] 'corrupt high event bits fail ordinarily before any lossy native conversion'.
    活前 取 原桥 其 存活上下文.
    失败初态 取 {'lexical':(原桥 其 新状态),'points':[],'warning':''}.
    试
        故障复制 失败初态['lexical'].
    救 原因
        如语 其 _初始化失败 失败初态 (原因 为 句).
    终
    确认 (初始化故障[1] 且 (初始化故障[0])['references'] == 0 且 (初始化故障[0])['native'] == 空 且 (原桥 其 存活上下文) == 活前) 'initial checkpoint failure releases the already-created native context exactly once'.
    确认 (失败初态['lexical'] == 空 且 (失败初态['points'] 其 量) == 0) 'failed initialization returns no released context or checkpoint to the plain fallback'.
    确认 ((失败初态['warning'] 其 含 'Ru scanner initialization failed:') 且 (失败初态['warning'] 其 含 'injected initial checkpoint copy failure') 且 (失败初态['warning'] 其 含 'editable as plain text')) 'initial checkpoint failure keeps its specific visible warning outside rescue scope'.
    初始化故障[0] 取 空.
    原文 取 "算 示范:\n    若 真 则\n        得 '甲😀'.\n    另\n        得 42.\n    然\n法\n".
    编 其 设文本 甲 原文.
    窗 其 发送 甲 2160 4 10.
    确认 ((语 其 选择 甲 'ru') == 'ru') 'Ru attaches independently of Lexilla availability'.
    确认 ((窗 其 发送 甲 4002 0 0) 其 数 == 0) 'Ru uses real SCLEX_CONTAINER instead of borrowed lexer'.
    前 取 语 其 状态 甲.
    确认 (前['feed'] == 0) 'selection never performs eager lexical scanning'.
    窗 其 发送 甲 4003 0 (-1).
    确认 (通知['needed'] > 0) 'real SCN_STYLENEEDED reaches the owning container bridge'.
    确认 ((语 其 状态 甲)['feed'] == 0) 'style-needed notification queues without synchronous rescanning'.
    初 取 语 其 排空 甲.
    确认 (初['enabled'] 且 初['warning'] == '' 且 非 初['pending']) 'container queue drains without fallback'.
    验样式 甲 0 3 4 'every UTF-8 byte of 算 is a keyword'.
    验样式 甲 4 6 8 'Han function name retains identifier style'.
    验样式 甲 40 9 2 'every Han and emoji byte in quoted string is styled'.
    验样式 甲 71 2 3 'number following multibyte source has correct byte offset'.
    确认 ((窗 其 发送 甲 2223 0 0) 其 数 == 9216) 'function header has base fold level and header flag'.
    确认 ((窗 其 发送 甲 2223 1 0) 其 数 == 9217) 'if header nests exactly once'.
    确认 ((窗 其 发送 甲 2223 2 0) 其 数 == 1026) 'function and if body has depth two'.
    确认 ((窗 其 发送 甲 2223 6 0) 其 数 == 1024) '法 closes matching function level'.
    确认 ((编 其 文本 甲) == 原文) 'styling and folding preserve exact UTF-8 text'.
    确认 (非 (编 其 已变 甲)) 'styling and folding never dirty a clean document'.
    确认 ((窗 其 发送 甲 2174 0 0) 其 为空) 'styling and folding create no undo entry'.
    确认 ((窗 其 发送 甲 2009 0 0) 其 数 == 4 且 (窗 其 发送 甲 2008 0 0) 其 数 == 10) 'styling preserves selection anchor and caret'.
    确认 ((窗 其 发送 甲 2481 33 0) 其 数 == 8947848) 'Ru palette preserves line-number style'.
    确认 ((窗 其 发送 甲 2243 2 0) 其 数 == 16) 'dedicated fold margin is visible'.
    确认 (语 其 折叠 甲 0) 'fold action accepts completed owning document'.
    确认 ((窗 其 发送 甲 2228 2 0) 其 数 == 0) 'collapse actually hides nested native lines'.
    确认 ((窗 其 发送 甲 2230 0 0) 其 数 == 0) 'collapse changes native expanded flag'.
    语 其 全折 甲 1.
    确认 ((窗 其 发送 甲 2228 2 0) 其 数 == 1) 'expand restores native line visibility'.
    语 其 全折 甲 0.
    语 其 选择 甲 'plain'.
    确认 ((窗 其 发送 甲 2236 0 0) 其 数 == 1) 'plain switch reveals every previously hidden line'.
    确认 ((窗 其 发送 甲 2223 0 0) 其 数 == 1024) 'plain switch clears old fold levels'.
    验样式 甲 0 87 0 'plain switch clears all Ru style bytes'.
    确认 ((语 其 状态 甲) == 空) 'plain switch cancels scanner state'.
    重置 甲 原文.
    语 其 全折 甲 0.
    语 其 选择 甲 'cpp'.
    确认 ((窗 其 发送 甲 2236 0 0) 其 数 == 1) 'C++ switch reveals every Ru fold even without Lexilla'.
    重置 甲 原文.
    语 其 全折 甲 0.
    语 其 选择 甲 'json'.
    确认 ((窗 其 发送 甲 2236 0 0) 其 数 == 1) 'JSON switch reveals every Ru fold even without Lexilla'.

    # Actual SCN_MODIFIED forwarding, including EOF checkpoints and undo/redo.
    重置 甲 ''.
    窗 其 发文 甲 2282 3 '算'.
    窗 其 发文 甲 2282 1 ' '.
    语 其 排空 甲.
    验样式 甲 0 3 4 'first typing into empty Ru document restarts a nonterminal checkpoint'.
    确认 ((语 其 状态 甲)['enabled']) 'EOF append never restores a finished scanner'.
    窗 其 发送 甲 2176 0 0.
    语 其 排空 甲.
    窗 其 发送 甲 2011 0 0.
    语 其 排空 甲.
    验样式 甲 0 3 4 'EOF undo and redo remain incrementally highlighted'.
    重置 甲 "'甲\n乙'\n得 1.\n".
    验样式 甲 1 3 2 'multiline quote initially styles Han bytes'.
    窗 其 发送 甲 2160 0 1.
    窗 其 发文 甲 2170 0 ''.
    语 其 排空 甲.
    验样式 甲 0 3 8 'deleting opening quote invalidates multiline lexical state'.
    窗 其 发送 甲 2176 0 0.
    语 其 排空 甲.
    验样式 甲 1 3 2 'undo restores multiline quote state'.
    重置 甲 '解.\n甲😀\n释.\n得 1.\n'.
    验样式 甲 5 7 1 'Ru block comment spans Han and emoji bytes'.
    验样式 甲 18 3 4 'Ru keyword resumes after the real 释. block-comment terminator'.
    窗 其 发送 甲 2160 0 4.
    窗 其 发文 甲 2170 0 'xx. '.
    语 其 排空 甲.
    验样式 甲 5 3 8 'same-length comment opener replacement invalidates lexical suffix'.
    窗 其 发送 甲 2176 0 0.
    语 其 排空 甲.
    验样式 甲 5 7 1 'undo restores Ru multiline comment state'.
    确认 (通知['text'] > 0) 'real native insert/delete notifications reached owning bridge'.
    确认 (通知['other'] > 0) 'style and fold notifications are observed without recursive text invalidation'.

    填充 取 ' '.
    循 15 次 填充 取 填充+填充. 环
    边文 取 填充[0:32760]+"'甲😀'\r\n得 1.\n".
    重置 甲 边文.
    验样式 甲 32760 9 2 'UTF-8 quote and emoji styles cross checkpoint boundary correctly'.
    窗 其 发送 甲 2160 32770 32771.
    窗 其 发文 甲 2170 0 ''.
    合 取 语 其 排空 甲.
    确认 (合['enabled'] 且 非 合['pending']) 'deleting LF from checkpoint-adjacent CRLF safely resumes lexical state'.
    验样式 甲 32770 3 4 'keyword offset adjusts correctly after CRLF partial deletion'.
    # Invalidate work that is still pending, then change multiline state at BOF.
    语 其 选择 甲 'plain'.
    编 其 设文本 甲 (填充+原文).
    语 其 选择 甲 'ru'.
    语 其 推进 甲 1.
    确认 (语 其 待办 甲) 'bounded timer returns before a large initial scan completes'.
    窗 其 发送 甲 2160 0 0.
    窗 其 发文 甲 2170 0 '解.\n'.
    合 取 语 其 排空 甲.
    确认 (合['enabled'] 且 非 合['converged']) 'edit during incomplete work invalidates suffix without unsafe reuse'.
    验样式 甲 32773 3 1 'unclosed BOF comment propagates through previously pending source'.
    重置 甲 原文+原文.
    语 其 全折 甲 0.
    窗 其 发送 甲 2160 0 0.
    窗 其 发文 甲 2170 0 '解.\n'.
    语 其 排空 甲.
    确认 ((窗 其 发送 甲 2236 0 0) 其 数 == 1) 'removing existing collapsed function headers with BOF comment reveals every old hidden line'.

    # Regression for retroactive fold corrections before the restart checkpoint.
    # A reference-call opener remains tentative across 32 KiB of whitespace.
    疑文 取 '算 回 值:\n1'+填充+填充[0:10000]+'.\n'.
    重置 甲 疑文.
    确认 ((窗 其 发送 甲 2223 0 0) 其 数 == 1024) 'tentative reference-call opener starts without a fold header'.
    窗 其 发送 甲 2160 35000 35000.
    窗 其 发文 甲 2170 0 '得 1.'.
    语 其 排空 甲.
    确认 ((窗 其 发送 甲 2223 0 0) 其 数 == 9216) 'temporary statement confirms an opener before the restart checkpoint'.
    语 其 全折 甲 0.
    窗 其 发送 甲 2160 35000 35006.
    窗 其 发文 甲 2170 0 ''.
    合 取 语 其 排空 甲.
    确认 (合['enabled'] 且 合['restart'] >= 32768 且 (窗 其 发送 甲 2223 0 0) 其 数 == 1024 且 (窗 其 发送 甲 2236 0 0) 其 数 == 1 且 (编 其 文本 甲) == 疑文) 'checkpoint restore retracts a previously published earlier header and reveals its lines'.

    编辑矩阵 甲 乙 原文.

    重置 甲 原文+原文.
    语 其 折叠 甲 0.
    重置 乙 '得 2.\n'.
    窗 其 发送 甲 2160 87 87.
    窗 其 发文 甲 2170 0 ' '.
    语 其 排空 甲.
    确认 ((窗 其 发送 甲 2230 0 0) 其 数 == 0 且 (窗 其 发送 甲 2228 2 0) 其 数 == 0) 'edit in later function preserves unaffected collapsed earlier fold'.
    验样式 乙 0 3 4 'editing one HWND preserves another document byte styles'.
    确认 ((语 其 状态 乙)['revision'] == 0) 'editing one HWND never invalidates another document generation'.
    旧态 取 语 其 状态 甲.
    编 其 开始载入 甲 1.
    确认 (非 (语 其 推进 甲 8) 且 (语 其 状态 甲) == 空) 'SETDOCPOINTER rejects queued stale document state'.
    语 其 选择 甲 'ru'.
    确认 ((语 其 状态 甲)['generation'] > 旧态['generation']) 'replacement document obtains a fresh generation'.
    语 其 遗忘 甲.
    确认 ((语 其 状态 甲) == 空) 'explicit release removes lifecycle state'.

    性能 甲 100000.
    性能 甲 1000000.
    语 其 遗忘 甲.
    编 其 开始载入 甲 32000000.
    确认 ((语 其 选择 甲 'ru') == 'plain') 'STYLES_NONE document suppresses Ru even when currently empty'.
    确认 (非 (语 其 待办 甲)) 'large-document mode schedules no scanning'.
    确认 ((窗 其 发送 甲 2379 0 0) 其 数 % 2 == 1) 'large-document styles storage remains disabled'.
    编 其 开始载入 甲 1.
    嵌文 取 ''.
    循 130 次 嵌文 取 嵌文+'{\n'. 环
    重置 甲 嵌文.
    故障 取 语 其 状态 甲.
    确认 (非 故障['enabled'] 且 故障['warning'] != '') 'unexpected structural complexity reports plain fallback'.
    确认 ((编 其 文本 甲) == 嵌文 且 非 (编 其 已变 甲)) 'complexity fallback preserves exact clean source'.
    确认 ((窗 其 发送 甲 2236 0 0) 其 数 == 1) 'complexity fallback leaves all lines visible'.
    验样式 甲 0 260 0 'complexity fallback clears partial style bytes'.
    语 其 遗忘 甲.
    窗 其 成功 ((窗 其 DestroyWindow) 其 调用 [甲]) 'destroy first editor'.
    确认 (非 (语 其 推进 甲 8)) 'destroyed HWND cannot resume a stale queue'.
    验样式 乙 0 3 4 'surviving editor remains independently styled after sibling destroy'.
    语 其 遗忘 乙.
    确认 ((如语 其 存活上下文) == 0) 'all current and shared checkpoint roots explicitly close and release at final teardown'.
    窗 其 成功 ((窗 其 DestroyWindow) 其 调用 [父]) 'destroy fixture'.
    窗 其 成功 ((窗 其 UnregisterClassW) 其 调用 [类名,实例]) 'unregister fixture'.
    类 其 关闭.
    类名 其 关闭.
    回调 其 关闭.
    显 'TOTAL PASS: '+(次数[0] 为 句).
    得 0.
法
