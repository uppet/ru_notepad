# Real main-window Ru container styling, fold commands and lifecycle tests.
应用 取 外言 '../src/main.ru'.
窗 取 外言 '../src/win32.ru'.
编 取 外言 '../src/editor.ru'.
语 取 外言 '../src/syntax.ru'.
件编 取 外言 '../src/file_codec.ru'.
密 取 外言 '如:密'.
Sleep 取 (窗 其 内核) 其 绑定 'Sleep' (密 其 签名 (窗 其 V) ([(窗 其 U)]) 'win64').
Delete 取 (窗 其 内核) 其 绑定 'DeleteFileW' (密 其 签名 (窗 其 I) ([(窗 其 PTR)]) 'win64').
次数 取 [0].
源 取 '算 加 左 为 数, 右 为 数:\n    得 左+右.\n法\n显 加 1 2.\n'.
作 确认 条件 为 事实 名 为 句:
    若 非 条件 则 卒 'FAIL: '+名. 然
    次数[0] 取 次数[0]+1.
    显 'PASS: '+名.
为
算 计时:
    得 (窗 其 结果 ((窗 其 GetTickCount64) 其 调用 [])) 其 数.
法
作 泵:
    消 取 (窗 其 MSG) 其 新建.
    起 取 计时.
    循
        状 取 应用 其 A.
        若 非 (状 其 查 'busy') 且 非 (状 其 查 'syntaxTimer') 则 破. 然
        若 计时-起 > 30000 则 消 其 关闭. 卒 'Ru UI styling did not finish within30s.'. 然
        若 非 ((窗 其 结果 ((窗 其 PeekMessageW) 其 调用 [消,空,0,0,1])) 其 为空) 则
            若 (消 其 读 'message') 其 数 == 18 则 消 其 关闭. 卒 'Unexpected WM_QUIT during Ru styling.'. 然
            窗 其 结果 ((窗 其 TranslateMessage) 其 调用 [消]).
            窗 其 结果 ((窗 其 DispatchMessageW) 其 调用 [消]).
        另 Sleep 其 调用 [1]. 然
    环
    消 其 关闭.
为
算 可见 柄 行 为 数:
    得 非 ((窗 其 发送 柄 2228 行 0) 其 为空).
法
作 点折叠 柄:
    # Real Scintilla hit testing generates SCN_MARGINCLICK for the parent.
    横 取 ((窗 其 发送 柄 2243 0 0) 其 数)+((窗 其 发送 柄 2243 1 0) 其 数)+8.
    高 取 (窗 其 发送 柄 2279 0 0) 其 数.
    纵 取 ((窗 其 发送 柄 2165 0 0) 其 数)+高/2.
    纵 取 纵-纵%1.
    坐标 取 纵*65536+横.
    窗 其 发送 柄 513 1 坐标.
    窗 其 发送 柄 514 0 坐标.
为
作 删 路 为 句:
    存 取 密 其 UTF16 路.
    窗 其 成功 (Delete 其 调用 [存]) 'Delete synthetic Ru file'.
    存 其 关闭.
为
算 计时源码:
    # Exactly gui_ru_timer_fixture(): 90,907*11 +11 +12 UTF-8 bytes.
    # Keep this pure producer identical in app_ru_native for portable SHA checks.
    文 取 '值 取 1.\n'.
    循 17 次 文 取 文+文. 环
    得 文[0:90907*7]+'#         \n显 987654.\n'.
法
算 计时样式 柄:
    探针们 取 [[0,3,8],[4,3,4],[8,1,3],[999988,3,4],[999992,6,3]].
    位 取 0.
    循 探针们 其 量 次
        探针 取 探针们[位].
        偏 取 0.
        循 探针[1] 次
            若 (窗 其 发送 柄 2010 (探针[0]+偏) 0) 其 数 != 探针[2] 则 得 假. 然
            偏 取 偏+1.
        环
        位 取 位+1.
    环
    得 真.
法
算 计时泵 起 为 数:
    消 取 (窗 其 MSG) 其 新建.
    完成 取 假.
    循
        若 (语 其 时刻)-起 > 30000 则 破. 然
        状 取 应用 其 A.
        若 非 (状 其 查 'busy') 且 非 (状 其 查 'syntaxTimer') 则 完成 取 真. 破. 然
        若 非 ((窗 其 结果 ((窗 其 PeekMessageW) 其 调用 [消,空,0,0,1])) 其 为空) 则
            若 (消 其 读 'message') 其 数 == 18 则 破. 然
            窗 其 结果 ((窗 其 TranslateMessage) 其 调用 [消]).
            窗 其 结果 ((窗 其 DispatchMessageW) 其 调用 [消]).
        另 Sleep 其 调用 [1]. 然
    环
    消 其 关闭.
    得 完成.
法
算 计时原生 目录 为 句:
    路 取 目录+'\\真实计时 一百万字节 😀.ru'.
    文 取 计时源码.
    件编 其 写文件 路 文 65001 假 ''.
    主 取 应用 其 初始化 [] 真.
    状 取 应用 其 A.
    # This separate mode owns only disposable synthetic data, including on error.
    状 其 增 'confirmClose' (算 文档: 得 7. 法).
    试
        起 取 语 其 时刻.
        应用 其 打开 路 0.
        完成 取 计时泵 起.
        用时 取 (语 其 时刻)-起.
        柄 取 应用 其 编辑柄.
        扫 取 语 其 状态 柄.
        若 扫 == 空 则 扫 取 {'readBytes':0,'maxRead':0,'chunks':0,'feed':0,'bytes':0,'pending':真,'enabled':假}. 然
        待办 取 0.
        若 扫['pending'] 则 待办 取 1. 然
        # Print the bounded snapshot before assertions, including the 30s failure.
        显 'RU_GUI_TIMER size=1000000 source_chars='+(文 其 量 为 句)+' wall_ms='+(用时 为 句)+' ticks='+((状 其 查 'syntaxTicks') 为 句)+' work_ms='+((状 其 查 'syntaxWorkMs') 为 句)+' gap_ms='+((状 其 查 'syntaxGapMs') 为 句)+' max_tick_ms='+((状 其 查 'syntaxMaxTickMs') 为 句)+' max_gap_ms='+((状 其 查 'syntaxMaxGapMs') 为 句)+' read_bytes='+(扫['readBytes'] 为 句)+' max_read='+(扫['maxRead'] 为 句)+' chunks='+(扫['chunks'] 为 句)+' feed='+(扫['feed'] 为 句)+' bytes='+(扫['bytes'] 为 句)+' pending='+(待办 为 句)+' text_notifications='+((状 其 查 'syntaxTextNotifications') 为 句)+' style_notifications='+((状 其 查 'syntaxStyleNotifications') 为 句)+' fold_notifications='+((状 其 查 'syntaxFoldNotifications') 为 句).
        确认 (完成 且 用时 <= 30000) 'actual main timer finishes the exact GUI corpus within the unchanged thirty-second gate'.
        确认 ((状 其 查 'syntaxTicks') > 0 且 (状 其 查 'syntaxWorkMs') > 0 且 (状 其 查 'syntaxWorkMs') <= 用时 且 (状 其 查 'syntaxMaxTickMs') > 0 且 (状 其 查 'syntaxGapMs') >= 0 且 (状 其 查 'syntaxMaxGapMs') >= 0) 'actual timer exposes bounded scalar work and callback-gap measurements'.
        确认 ((窗 其 发送 柄 2378 0 0) 其 数 == 3 且 (状 其 查 'syntaxStyleNotifications') == 0 且 (状 其 查 'syntaxFoldNotifications') == 0 且 扫['enabled'] 且 非 扫['pending'] 且 扫['feed'] == 1000000 且 扫['readBytes'] == 1000000 且 扫['maxRead'] > 0 且 扫['maxRead'] <= 1024 且 扫['chunks'] > 0) 'filtered production timer completes bounded scanning without style or fold notifications'.
        确认 ((文 其 量) == 636370 且 (窗 其 发送 柄 2183 0 0) 其 数 == 1000000 且 (窗 其 发送 柄 2154 0 0) 其 数 == 90910 且 (编 其 文本 柄) == 文) 'timer styling preserves the exact Unicode megabyte and all source lines'.
        确认 (计时样式 柄) 'actual timer matches all sixteen GUI head and tail style bytes'.
        确认 (非 (应用 其 脏 (应用 其 当前)) 且 ((应用 其 当前) 其 查 'revision') == 0 且 ((状 其 查 'errors') 其 量) == 0) 'timer styling preserves the clean savepoint and reports no text revision or errors'.
        读回 取 件编 其 读文件 路 0.
        确认 (读回['text'] == 文) 'timer measurement preserves the complete disposable source file'.
        确认 (应用 其 关程序) 'timer measurement closes its real main window normally'.
    救 原因
        若 状 其 查 'busy' 则 应用 其 取消工作. 然
        若 状 其 查 'ready' 则 应用 其 关程序. 然
        删 路.
        卒 原因.
    终
    删 路.
    显 'TOTAL PASS: '+(次数[0] 为 句).
    得 0.
法
算 元初 参数 为 句 阵:
    若 (参数 其 量) == 2 且 参数[1] == '--measure-ru-timer' 则 得 计时原生 参数[0]. 然
    若 (参数 其 量) != 1 则 显 'Usage: app_ru_native.exe EXISTING_DISPOSABLE_DIRECTORY'. 得 2. 然
    入路 取 参数[0]+'\\如言 source 😀.ru'.
    出路 取 参数[0]+'\\另存 source.RU'.
    件编 其 写文件 入路 源 65001 假 ''.
    主 取 应用 其 初始化 [入路] 假.
    泵.
    状 取 应用 其 A.
    第一 取 应用 其 编辑柄.
    文一 取 应用 其 当前.
    初页 取 (状 其 查 'docs')[0].
    确认 ((窗 其 发送 (初页 其 查 'editor') 2378 0 0) 其 数 == 3) 'new-page creation subscribes only to text insert and delete modifications'.
    确认 ((窗 其 发送 第一 2378 0 0) 其 数 == 3) 'hidden streaming-open creation retains the production text-only notification mask'.
    确认 ((文一 其 查 'language') == 'ru') 'Unicode CLI .ru selects the actual Ru container'.
    确认 ((编 其 文本 第一) == 源) 'initial background styling preserves complete text'.
    确认 (非 (应用 其 脏 文一)) 'initial background styling preserves savepoint'.
    确认 ((窗 其 发送 第一 4002 0 0) 其 数 == 0) 'Ru does not borrow a Lexilla language identifier'.
    确认 ((窗 其 发送 第一 2010 0 0) 其 数 == 4) 'real timer colors the first Ru keyword byte'.
    确认 ((窗 其 发送 第一 2010 2 0) 其 数 == 4) 'all UTF8 bytes of the keyword receive its style'.
    确认 ((窗 其 发送 第一 2223 0 0) 其 数 == 9216) 'function opener has actual Scintilla fold-header level'.
    确认 ((窗 其 发送 第一 2243 2 0) 其 数 > 0) 'dedicated fold margin is visible'.
    确认 ((窗 其 取文 (状 其 查 'status')) 其 含 'Ru / 如言') 'status names the Ru-owned language mode'.
    确认 ((文一 其 查 'revision') == 0) 'style and fold notifications do not become text revisions'.
    # Prove the counter path sees real native notifications before filtering.
    窗 其 发送 第一 2359 8388607 0.
    样前 取 状 其 查 'syntaxStyleNotifications'.
    折前 取 状 其 查 'syntaxFoldNotifications'.
    旧修订 取 文一 其 查 'revision'.
    窗 其 发送 主 273 701 0.
    窗 其 发送 主 273 704 0.
    泵.
    确认 ((窗 其 发送 第一 2378 0 0) 其 数 == 8388607 且 (状 其 查 'syntaxStyleNotifications') > 样前 且 (状 其 查 'syntaxFoldNotifications') > 折前 且 (文一 其 查 'revision') == 旧修订) 'default-all control receives real style and fold modifications without a text revision'.
    应用 其 配置修改通知 第一.
    样前 取 状 其 查 'syntaxStyleNotifications'.
    折前 取 状 其 查 'syntaxFoldNotifications'.
    窗 其 发送 主 273 701 0.
    窗 其 发送 主 273 704 0.
    泵.
    确认 ((状 其 查 'syntaxStyleNotifications') == 样前 且 (状 其 查 'syntaxFoldNotifications') == 折前 且 (文一 其 查 'revision') == 旧修订 且 (窗 其 发送 第一 2010 0 0) 其 数 == 4 且 (窗 其 发送 第一 2223 0 0) 其 数 == 9216) 'text-only subscription suppresses style/fold callbacks while real byte styles and folds still update'.
    旧行数 取 (窗 其 发送 第一 2154 0 0) 其 数.
    文前 取 状 其 查 'syntaxTextNotifications'.
    窗 其 发送 第一 2160 0 0.
    窗 其 发文 第一 2170 0 '# line test\n'.
    泵.
    确认 ((状 其 查 'syntaxTextNotifications') > 文前 且 (文一 其 查 'revision') > 旧修订 且 (窗 其 发送 第一 2154 0 0) 其 数 == 旧行数+1 且 (编 其 文本 第一) == '# line test\n'+源 且 (应用 其 脏 文一)) 'filtered insert notification retains line-count, revision and dirty-state updates'.
    文前 取 状 其 查 'syntaxTextNotifications'.
    旧修订 取 文一 其 查 'revision'.
    窗 其 发送 第一 2176 0 0.
    泵.
    确认 ((状 其 查 'syntaxTextNotifications') > 文前 且 (文一 其 查 'revision') > 旧修订 且 (窗 其 发送 第一 2154 0 0) 其 数 == 旧行数 且 (编 其 文本 第一) == 源 且 非 (应用 其 脏 文一)) 'filtered undo-delete notification restores source lines and original savepoint'.
    文前 取 状 其 查 'syntaxTextNotifications'.
    旧修订 取 文一 其 查 'revision'.
    窗 其 发送 第一 2011 0 0.
    泵.
    确认 ((状 其 查 'syntaxTextNotifications') > 文前 且 (文一 其 查 'revision') > 旧修订 且 (窗 其 发送 第一 2154 0 0) 其 数 == 旧行数+1 且 (编 其 文本 第一) == '# line test\n'+源 且 (应用 其 脏 文一)) 'filtered redo-insert notification restores the changed lines, revision and dirty state'.
    文前 取 状 其 查 'syntaxTextNotifications'.
    旧修订 取 文一 其 查 'revision'.
    窗 其 发送 第一 2176 0 0.
    泵.
    确认 ((状 其 查 'syntaxTextNotifications') > 文前 且 (文一 其 查 'revision') > 旧修订 且 (窗 其 发送 第一 2154 0 0) 其 数 == 旧行数 且 (编 其 文本 第一) == 源 且 非 (应用 其 脏 文一)) 'undo after redo again restores the complete original source and clean savepoint'.
    窗 其 发送 主 273 505 0.
    确认 (非 (可见 第一 1)) 'collapse-all command hides function body'.
    窗 其 发送 主 273 704 0.
    确认 (非 (可见 第一 1)) 'reselecting the same Ru mode preserves collapsed state'.
    应用 其 新页 'other.txt' 'other text' 65001 假 ''.
    第二 取 应用 其 编辑柄.
    确认 (可见 第二 0) 'another plain document has no inherited hidden lines'.
    应用 其 切页 1.
    确认 (非 (可见 第一 1)) 'switching tabs preserves this document fold state'.
    窗 其 发送 主 273 506 0.
    确认 (可见 第一 1) 'expand-all command restores function body'.
    点折叠 第一.
    确认 (非 (可见 第一 1)) 'native Scintilla margin click reaches owning main callback'.
    点折叠 第一.
    确认 (可见 第一 1) 'second native margin click expands the same fold'.
    确认 ((编 其 文本 第一) == 源 且 非 (应用 其 脏 文一)) 'fold UI changes neither bytes nor dirty state'.
    窗 其 发送 主 273 505 0.
    窗 其 发送 主 273 701 0.
    确认 (可见 第一 1) 'plain transition cannot leave formerly collapsed content hidden'.
    确认 ((窗 其 发送 第一 2010 0 0) 其 数 == 0) 'plain transition clears container byte styles'.
    确认 ((窗 其 发送 第一 2243 2 0) 其 数 == 0) 'plain transition hides the dedicated fold margin'.
    窗 其 发送 主 273 704 0.
    泵.
    确认 ((窗 其 发送 第一 2010 0 0) 其 数 == 4 且 可见 第一 1) 'manual Ru selection rebuilds styles with content visible'.
    旧修订 取 文一 其 查 'revision'.
    改数 取 编 其 全换 第一 '左' '甲' 真.
    确认 (改数 == 2) 'same-byte identifier edits use the real grouped replacement command'.
    泵.
    确认 (应用 其 脏 文一) 'background restyling preserves edited dirty state'.
    确认 ((文一 其 查 'revision') > 旧修订) 'only actual text modifications advance revision'.
    窗 其 发送 第一 2176 0 0.
    泵.
    确认 ((编 其 文本 第一) == 源 且 非 (应用 其 脏 文一)) 'one undo restores original bytes and savepoint after restyling'.
    确认 ((窗 其 发送 第一 2223 0 0) 其 数 == 9216) 'undo restores correct function fold structure'.
    应用 其 新页 '' 源 65001 假 ''.
    另柄 取 应用 其 编辑柄.
    确认 (((应用 其 当前) 其 查 'language') == 'plain') 'untitled documents stay plain until language is known or selected'.
    状 其 增 'chooseSavePath' (算 原路: 得 出路. 法).
    确认 (应用 其 保存 真) 'Save As starts the same asynchronous safe file writer'.
    泵.
    确认 (((应用 其 当前) 其 查 'language') == 'ru') 'successful Save As .RU selects Ru automatically'.
    确认 ((窗 其 发送 另柄 2010 0 0) 其 数 == 4) 'Save As schedules actual Ru styling work'.
    确认 (非 (应用 其 脏 (应用 其 当前))) 'Save As plus styling retains successful savepoint'.
    读回 取 件编 其 读文件 出路 0.
    确认 (读回['text'] == 源) 'Save As writes the complete unstyled source bytes'.
    确认 (可见 第一 1) 'another document stays expanded after Save As'.
    应用 其 新页 'queued.ru' 源 65001 假 ''.
    待柄 取 应用 其 编辑柄.
    确认 (语 其 待办 待柄) 'new Ru document owns pending incremental work'.
    应用 其 删除当前页.
    确认 ((语 其 状态 待柄) == 空) 'closing a pending document releases its styling generation'.
    泵.
    确认 ((编 其 文本 另柄) == 源) 'queued timer cannot mutate another document after close'.
    确认 (((状 其 查 'errors') 其 量) == 0) 'ordinary Ru styling/folding lifecycle reports no errors'.
    确认 (应用 其 关程序) 'Ru integration fixture closes normally without dirty prompts'.
    删 入路.
    删 出路.
    显 'TOTAL PASS: '+(次数[0] 为 句).
    得 0.
法
