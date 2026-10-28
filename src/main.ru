# ru_notepad 0.1.8 preview. Application behavior is compiled from Ru.
密 取 外言 '如:密'.
本地 取 外言 'i18n.ru'.
偏好 取 外言 'i18n_settings.ru'.
最近 取 外言 'recent_files.ru'.
近策 取 外言 'recent_files_policy.ru'.
关策 取 外言 'tab_close_policy.ru'.
页单 取 外言 'tab_context.ru'.
单例 取 外言 'single_instance.ru'.
单设 取 外言 'single_instance_settings.ru'.
布局策 取 外言 'i18n_layout.ru'.
窗 取 外言 'win32.ru'.
编 取 外言 'editor.ru'.
件编 取 外言 'file_codec.ru'.
模 取 外言 'document.ru'.
参 取 外言 'ui_arguments.ru'.
态 取 外言 'status.ru'.
键规 取 外言 'shortcuts.ru'.
语 取 外言 'syntax.ru'.
关联 取 外言 'associations.ru'.
拖放 取 外言 'file_drop.ru'.
修改头 取 密 其 结构 [['header',窗 其 NMHDR],['position',窗 其 IP],['ch',窗 其 I],['modifiers',窗 其 I],['modificationType',窗 其 I],['text',窗 其 PTR],['length',窗 其 IP],['linesAdded',窗 其 IP],['message',窗 其 I],['wParam',窗 其 UP],['lParam',窗 其 IP],['line',窗 其 IP],['foldLevelNow',窗 其 I],['foldLevelPrev',窗 其 I],['margin',窗 其 I]].
A 取 {'modalDepth':0,'openFinalizing':假,'handoffReject':假,'cleanupActive':假,'cleanupRetrying':假,'cleanupPending':假,'singlePreference':真,'singleState':空,'singleDeferredShow':假,'handoffPending':[],'closeRun':空,'tabMenuOpen':假,'recentItems':[],'recentError':0,'recentReader':空,'recentWriter':空,'window':空,'instance':空,'tabs':空,'status':空,'uiPreference':'system','docs':[],'active':-1,'ready':假,'search':假,'find':空,'replace':空,'previous':空,'whole':空,'searchWrap':空,'next':空,'one':空,'all':空,'case':空,'hide':空,'counter':0,'wrap':假,'busy':假,'shutdownBlocked':假,'visible':假,'syntaxWarning':'','cancel':空,'operation':空,'queue':[],'locks':[],'cancelRequested':假,'inTick':假,'closeIndex':-1,'errors':[],'lastOutcome':'','lastReader':空,'lastWriter':空,'ticks':0,'syntaxTimer':假,'syntaxGeneration':0,'syntaxQueued':0,'syntaxPosts':0,'syntaxContinuations':0,'syntaxYields':0,'syntaxStale':0,'syntaxTick':假,'syntaxNext':0,'syntaxTicks':0,'syntaxWorkMs':0,'syntaxMaxTickMs':0,'syntaxGapMs':0,'syntaxMaxGapMs':0,'syntaxLastEndMs':0,'syntaxTextNotifications':0,'syntaxStyleNotifications':0,'syntaxFoldNotifications':0,'syntaxSnapshots':0,'markdownDiagnosticEnabled':假,'markdownDiagnosticFailed':假,'markdownDiagnosticNext':0,'markdownDiagnosticSeq':0,'markdownDiagnosticIdentity':0,'markdownDiagnosticPending':真,'markdownDiagnosticText':'','statusBase':'','statusOwner':''}.

# Admission barrier across native modal loops. No unacknowledged raw pointers retained.
算 界面弹窗 主窗, 文 为 句, 标题 为 句, 类型 为 数:
    A 其 增 'modalDepth' ((A 其 查 'modalDepth')+1).
    结果盒 取 [0].
    试
        结果盒[0] 取 窗 其 弹窗 主窗 文 标题 类型.
    救 原因
        A 其 增 'modalDepth' ((A 其 查 'modalDepth')-1).
        卒 原因.
    终
    A 其 增 'modalDepth' ((A 其 查 'modalDepth')-1).
    得 结果盒[0].
法
算 界面文件对话 保存模式 为 事实, 原路 为 句:
    A 其 增 'modalDepth' ((A 其 查 'modalDepth')+1).
    结果盒 取 [''].
    试
        结果盒[0] 取 窗 其 文件对话 (A 其 查 'window') 保存模式 原路.
    救 原因
        A 其 增 'modalDepth' ((A 其 查 'modalDepth')-1).
        卒 原因.
    终
    A 其 增 'modalDepth' ((A 其 查 'modalDepth')-1).
    得 结果盒[0].
法

# Syntax work is deferred out of Scintilla callbacks, with one shared UI budget.
# Pure cache update shared by periodic sampling and an already-required final refresh.
算 缓存Markdown诊断 扫, 来源 为 数:
    若 非 (A 其 查 'markdownDiagnosticEnabled') 或 (A 其 查 'markdownDiagnosticFailed') 或 (A 其 查 'markdownDiagnosticSeq') >= 4096 或 扫 == 空 则 得 空. 然
    若 扫['language'] != 'markdown' 或 扫['length'] < 0 则 得 空. 然
    试
        序 取 (A 其 查 'markdownDiagnosticSeq')+1.
        A 其 增 'markdownDiagnosticSeq' 序.
        待 取 0. 若 扫['pending'] 则 待 取 1. 然
        工 取 (A 其 查 'syntaxWorkMs')*1000. 工 取 工-工%1.
        隙 取 (A 其 查 'syntaxGapMs')*1000. 隙 取 隙-隙%1.
        有效 取 0. 若 扫['bulkMetricsValid'] 则 有效 取 1. 然
        文 取 ' [MDP2 seq='+(序 为 句)+' via='+(来源 为 句)+' id='+(扫['identity'] 为 句)+' gen='+(扫['generation'] 为 句)+' rev='+(扫['revision'] 为 句)+' phase='+(扫['phaseCode'] 为 句)+' pending='+(待 为 句)+' length='+(扫['length'] 为 句)+' feed='+(扫['feed'] 为 句)+' published='+(扫['published'] 为 句)+' tick='+((A 其 查 'syntaxTicks') 为 句)+' work_us='+(工 为 句)+' gap_us='+(隙 为 句)+' bulkCalls='+(扫['bulkCalls'] 为 句)+' bulkLines='+(扫['bulkLines'] 为 句)+' fallbackBatches='+(扫['fallbackBatches'] 为 句)+' directCalls='+(扫['directCalls'] 为 句)+' directLines='+(扫['directLines'] 为 句)+' maxPlanBytes='+(扫['maxPlanBytes'] 为 句)+' bulkUs='+(扫['bulkUs'] 为 句)+' ownedBufferBytes='+(扫['ownedBufferBytes'] 为 句)+' metric_valid='+(有效 为 句)+']'.
        若 文 其 量 > 768 则 卒 'Bounded Markdown numeric marker overflow.'. 然
        A 其 增 'markdownDiagnosticIdentity' 扫['identity'].
        A 其 增 'markdownDiagnosticPending' 扫['pending'].
        A 其 增 'markdownDiagnosticText' 文.
    救 原因
        A 其 增 'markdownDiagnosticText' ' [MDP2 error=1]'.
        A 其 增 'markdownDiagnosticFailed' 真.
        显 'FAIL: Markdown numeric phase diagnostic failed.'.
    终
    得 空.
法
算 刷新Markdown诊断 语态:
    若 非 (A 其 查 'markdownDiagnosticEnabled') 或 (A 其 查 'markdownDiagnosticFailed') 或 语态 == 空 则 得 ''. 然
    若 语态['language'] != 'markdown' 则 得 ''. 然
    # A scan may finish within the preceding 250 ms slot. Use this existing
    # refresh's projection and status write; do not create another tick/message.
    若 非 语态['pending'] 且 ((A 其 查 'markdownDiagnosticIdentity') != 语态['identity'] 或 (A 其 查 'markdownDiagnosticPending')) 则 缓存Markdown诊断 语态 1. 然
    若 (A 其 查 'markdownDiagnosticFailed') 或 (A 其 查 'markdownDiagnosticIdentity') != 语态['identity'] 则 得 ''. 然
    # At the process cap, never present a stale pending record as terminal.
    若 非 语态['pending'] 且 (A 其 查 'markdownDiagnosticPending') 则 得 ''. 然
    得 A 其 查 'markdownDiagnosticText'.
法
# CI-only numeric projection. The ordinary UI leaves this disabled.
# Reuse the scheduler's existing QPC timestamp; at most one status write/250 ms.
# No document/native query or scan is performed. A status failure cannot abort work.
算 诊断Markdown 现在 为 数:
    若 非 (A 其 查 'markdownDiagnosticEnabled') 或 (A 其 查 'markdownDiagnosticFailed') 或 非 (A 其 查 'ready') 或 (A 其 查 'busy') 或 现在 < (A 其 查 'markdownDiagnosticNext') 或 (A 其 查 'markdownDiagnosticSeq') >= 4096 则 得 空. 然
    位 取 A 其 查 'active'.
    文们 取 A 其 查 'docs'.
    若 位 < 0 或 位 >= 文们 其 量 则 得 空. 然
    文档 取 文们[位].
    若 (文档 其 查 'language') != 'markdown' 或 (文档 其 查 'large') 或 (文档 其 查 'editor') 其 句 != (A 其 查 'statusOwner') 则 得 空. 然
    A 其 增 'markdownDiagnosticNext' (现在+250).
    试
        扫 取 语 其 状态 (文档 其 查 'editor').
        若 扫 == 空 或 扫['language'] != 'markdown' 或 扫['length'] < 0 则 得 空. 然
        缓存Markdown诊断 扫 0.
        若 (A 其 查 'markdownDiagnosticFailed') 或 (A 其 查 'markdownDiagnosticIdentity') != 扫['identity'] 则 得 空. 然
        窗 其 标题 (A 其 查 'status') ((A 其 查 'statusBase')+(A 其 查 'markdownDiagnosticText')).
    救 原因
        # Fixed failure marker only; never disclose paths, text or native errors.
        A 其 增 'markdownDiagnosticText' ' [MDP2 error=1]'.
        A 其 增 'markdownDiagnosticFailed' 真.
        # The existing launcher FAIL gate rejects even if an earlier marker
        # remains visible after a failed status write. Emit this fixed line once.
        显 'FAIL: Markdown numeric phase diagnostic failed.'.
    终
    得 空.
法
算 所属文档 柄:
    文们 取 A 其 查 'docs'.
    位 取 0.
    循 文们 其 量 次
        若 ((文们[位] 其 查 'editor') 其 句) == (柄 其 句) 则 得 文们[位]. 然
        位 取 位+1.
    环
    得 空.
法
# WM_APP+902 carries only a bounded burst token, never a document or pointer.
# Keep the physical queued token until that exact message is consumed, including
# across invalidation. A new burst cannot pile up messages behind an old one.
算 下一语法代:
    代 取 ((A 其 查 'syntaxGeneration')%2147483647)+1.
    若 代 == (A 其 查 'syntaxQueued') 则 代 取 (代%2147483647)+1. 然
    A 其 增 'syntaxGeneration' 代.
    得 空.
法
算 停止语法:
    下一语法代.
    若 A 其 查 'syntaxTimer' 则
        窗 其 结果 ((窗 其 KillTimer) 其 调用 [(A 其 查 'window'),902]).
        A 其 增 'syntaxTimer' 假.
    然
    得 空.
法
算 界面待办:
    # QS_INPUT includes raw/touch/pointer; also yield to paint, sent messages,
    # hotkeys, all posted messages (including WM_CHAR/commands), and timers.
    # The HIGH word is current queue state; the low word is only new arrivals.
    得 ((窗 其 结果 ((窗 其 GetQueueStatus) 其 调用 [7679])) 其 位段 16 16) != 0.
法
算 续投语法:
    若 非 (A 其 查 'ready') 或 非 (A 其 查 'syntaxTimer') 或 (A 其 查 'busy') 或 (A 其 查 'syntaxTick') 或 (A 其 查 'syntaxQueued') != 0 则 得 空. 然
    若 界面待办 则 A 其 增 'syntaxYields' ((A 其 查 'syntaxYields')+1). 得 空. 然
    代 取 A 其 查 'syntaxGeneration'.
    # Posting failure is recoverable: the existing 10ms timer remains armed.
    若 非 ((窗 其 结果 ((窗 其 PostMessageW) 其 调用 [(A 其 查 'window'),33670,代,0])) 其 为空) 则
        A 其 增 'syntaxQueued' 代.
        A 其 增 'syntaxPosts' ((A 其 查 'syntaxPosts')+1).
    然
    得 空.
法
算 安排语法:
    若 非 (A 其 查 'ready') 则 得 空. 然
    若 A 其 查 'syntaxTimer' 则 续投语法. 得 空. 然
    文们 取 A 其 查 'docs'.
    位 取 0.
    循 文们 其 量 次
        若 语 其 待办 (文们[位] 其 查 'editor') 则
            窗 其 成功 ((窗 其 SetTimer) 其 调用 [(A 其 查 'window'),902,10,空]) 'SetTimer(Ru syntax)'.
            下一语法代.
            A 其 增 'syntaxTimer' 真.
            # Do not count time between separate styling bursts as callback gaps.
            A 其 增 'syntaxLastEndMs' 0.
            续投语法.
            得 空.
        然
        位 取 位+1.
    环
    得 空.
法
算 语法消息 柄, 代 为 数:
    若 代 <= 0 或 代 > 2147483647 则 得 空. 然
    若 (柄 其 句) != ((A 其 查 'window') 其 句) 则 得 空. 然
    # An obsolete message may clear only its own physical queue occupancy.
    若 代 != (A 其 查 'syntaxQueued') 则 A 其 增 'syntaxStale' ((A 其 查 'syntaxStale')+1). 得 空. 然
    A 其 增 'syntaxQueued' 0.
    若 非 (A 其 查 'ready') 或 非 (A 其 查 'syntaxTimer') 则 得 空. 然
    若 代 != (A 其 查 'syntaxGeneration') 则 A 其 增 'syntaxStale' ((A 其 查 'syntaxStale')+1). 续投语法. 得 空. 然
    若 语法时钟 则 A 其 增 'syntaxContinuations' ((A 其 查 'syntaxContinuations')+1). 然
    得 空.
法
算 语法时钟:
    若 非 (A 其 查 'ready') 或 非 (A 其 查 'syntaxTimer') 或 (A 其 查 'busy') 或 (A 其 查 'syntaxTick') 则 得 假. 然
    若 界面待办 则 A 其 增 'syntaxYields' ((A 其 查 'syntaxYields')+1). 得 假. 然
    A 其 增 'syntaxTick' 真.
    试
        文们 取 A 其 查 'docs'.
        数量 取 文们 其 量.
        活动 取 A 其 查 'active'.
        起 取 语 其 时刻.
        后台 取 -1.
        若 数量 > 1 则
            位 取 (A 其 查 'syntaxNext')%数量.
            循 数量 次
                若 位 != 活动 且 (语 其 待办 (文们[位] 其 查 'editor')) 则 后台 取 位. 破. 然
                位 取 (位+1)%数量.
            环
            若 后台 >= 0 则 A 其 增 'syntaxNext' ((后台+1)%数量). 然
        然
        已有 取 假.
        若 活动 >= 0 且 活动 < 数量 则
            柄 取 文们[活动] 其 查 'editor'.
            已有 取 语 其 待办 柄.
            余时 取 8-((语 其 时刻)-起).
            若 后台 >= 0 且 余时 > 4 则 余时 取 4. 然
            若 已有 且 余时 > 0 则 语 其 推进 柄 余时. 然
        然
        若 后台 >= 0 则
            已用 取 (语 其 时刻)-起.
            若 已用 < 8 则 语 其 推进 (文们[后台] 其 查 'editor') (8-已用). 然
        然
        待续 取 假.
        位 取 0.
        循 数量 次
            若 语 其 待办 (文们[位] 其 查 'editor') 则 待续 取 真. 然
            位 取 位+1.
        环
        若 非 待续 则 停止语法. 然
        若 已有 且 活动 >= 0 且 非 (语 其 待办 (文们[活动] 其 查 'editor')) 则 刷新. 然
        # Scalar-only diagnostic totals: one extra QPC read per accepted tick.
        # Work includes the existing callback scheduling/refresh work; gaps are
        # previous callback end to next callback start while its timer is armed.
        终时 取 语 其 时刻.
        用时 取 终时-起.
        A 其 增 'syntaxTicks' ((A 其 查 'syntaxTicks')+1).
        A 其 增 'syntaxWorkMs' ((A 其 查 'syntaxWorkMs')+用时).
        若 用时 > (A 其 查 'syntaxMaxTickMs') 则 A 其 增 'syntaxMaxTickMs' 用时. 然
        前终 取 A 其 查 'syntaxLastEndMs'.
        若 前终 > 0 则
            间隔 取 起-前终.
            A 其 增 'syntaxGapMs' ((A 其 查 'syntaxGapMs')+间隔).
            若 间隔 > (A 其 查 'syntaxMaxGapMs') 则 A 其 增 'syntaxMaxGapMs' 间隔. 然
        然
        A 其 增 'syntaxLastEndMs' 终时.
        # Diagnostic status writes are outside measured work; their cost is
        # included in the next scheduler gap and the unchanged GUI wall deadline.
        诊断Markdown 终时.
    救 原因
        A 其 增 'syntaxTick' 假.
        停止语法.
        卒 原因.
    终
    A 其 增 'syntaxTick' 假.
    续投语法.
    得 真.
法
# A bounded diagnostic request writes numbers only to the existing launcher log.
# It never scans text, refreshes the UI, or exposes document/path contents.
算 诊断语法:
    若 非 (A 其 查 'ready') 或 (A 其 查 'busy') 或 (A 其 查 'syntaxTick') 则 得 空. 然
    活动 取 A 其 查 'active'.
    文们 取 A 其 查 'docs'.
    若 活动 < 0 或 活动 >= (文们 其 量) 或 (A 其 查 'syntaxSnapshots') >= 3 则 得 空. 然
    序 取 (A 其 查 'syntaxSnapshots')+1.
    # Reserve before the safe projection, so ordinary errors consume the cap too.
    A 其 增 'syntaxSnapshots' 序.
    试
        扫 取 语 其 状态 (文们[活动] 其 查 'editor').
        若 扫 == 空 则 卒 'No active Ru diagnostic projection.'. 然
        待办 取 0.
        若 扫['pending'] 则 待办 取 1. 然
        显 'RU_GUI_SNAPSHOT seq='+(序 为 句)+' ok=1 generation='+(扫['generation'] 为 句)+' revision='+(扫['revision'] 为 句)+' pending='+(待办 为 句)+' bytes='+(扫['bytes'] 为 句)+' feed='+(扫['feed'] 为 句)+' read_bytes='+(扫['readBytes'] 为 句)+' restart='+(扫['restart'] 为 句)+' chunks='+(扫['chunks'] 为 句)+' ticks='+((A 其 查 'syntaxTicks') 为 句)+' work_ms='+((A 其 查 'syntaxWorkMs') 为 句)+' gap_ms='+((A 其 查 'syntaxGapMs') 为 句)+' max_tick_ms='+((A 其 查 'syntaxMaxTickMs') 为 句)+' max_gap_ms='+((A 其 查 'syntaxMaxGapMs') 为 句)+' posts='+((A 其 查 'syntaxPosts') 为 句)+' continuation_ticks='+((A 其 查 'syntaxContinuations') 为 句)+' queue_yields='+((A 其 查 'syntaxYields') 为 句)+' stale_messages='+((A 其 查 'syntaxStale') 为 句)+' text_notifications='+((A 其 查 'syntaxTextNotifications') 为 句)+' style_notifications='+((A 其 查 'syntaxStyleNotifications') 为 句)+' fold_notifications='+((A 其 查 'syntaxFoldNotifications') 为 句).
    救 原因
        # Do not disclose an original exception or document data in diagnostics.
        显 'RU_GUI_SNAPSHOT seq='+(序 为 句)+' ok=0'.
    终
    得 空.
法
算 当前:
    得 (A 其 查 'docs')[A 其 查 'active'].
法
算 编辑柄:
    得 当前 其 查 'editor'.
法
算 提示 文 为 句:
    得 界面弹窗 (A 其 查 'window') 文 'ru_notepad' 64.
法
算 错误提示 文 为 句:
    (A 其 查 'errors') 其 增 文.
    若 A 其 查 'visible' 则 得 界面弹窗 (A 其 查 'window') (本地 其 格式 'error.body' ([文])) (本地 其 文本 'error.title') 16. 然
    显 '[operation] rejected: '+文.
    得 0.
法
算 报语法警告:
    警告 取 语 其 初始化.
    若 (A 其 查 'visible') 且 警告 != '' 且 警告 != (A 其 查 'syntaxWarning') 则
        A 其 增 'syntaxWarning' 警告.
        提示 警告.
    然
    得 空.
法
算 短名 路 为 句:
    得 模 其 短名 路.
法
算 脏 文档:
    得 模 其 有改 文档 (编 其 已变 (文档 其 查 'editor')).
法
算 编码名 编码:
    得 模 其 编码名 编码.
法
算 页标题 文档:
    名 取 文档 其 查 'name'.
    若 脏 文档 则 名 取 '* '+名. 然
    得 名.
法
算 任一已改:
    文们 取 A 其 查 'docs'.
    位 取 0.
    循 文们 其 量 次
        若 脏 文们[位] 则 得 真. 然
        位 取 位+1.
    环
    得 假.
法
算 关机会话:
    若 (A 其 查 'busy') 或 (A 其 查 'closeRun') != 空 或 任一已改 则
        文 取 密 其 UTF16 (本地 其 文本 'notice.shutdown_blocked').
        窗 其 结果 ((窗 其 ShutdownBlockReasonCreate) 其 调用 (参 其 窗口二参 A 文)).
        文 其 关闭.
        A 其 增 'shutdownBlocked' 真.
        得 0.
    然
    窗 其 结果 ((窗 其 ShutdownBlockReasonDestroy) 其 调用 [A 其 查 'window']).
    A 其 增 'shutdownBlocked' 假.
    得 1.
法
算 刷新:
    若 非 (A 其 查 'ready') 或 (A 其 查 'active') < 0 或 (A 其 查 'busy') 则 得 空. 然
    若 (A 其 查 'shutdownBlocked') 且 非 任一已改 则
        窗 其 结果 ((窗 其 ShutdownBlockReasonDestroy) 其 调用 [A 其 查 'window']).
        A 其 增 'shutdownBlocked' 假.
    然
    文档 取 当前.
    名 取 页标题 文档.
    若 名 != (文档 其 查 'label') 则
        存 取 密 其 UTF16 名.
        项 取 (窗 其 TCITEM) 其 新建.
        项 其 写 'mask' 1.
        项 其 写 'text' (存 其 地址).
        窗 其 发指 (A 其 查 'tabs') 4925 (A 其 查 'active') 项.
        项 其 关闭.
        存 其 关闭.
        文档 其 增 'label' 名.
        窗 其 标题 (A 其 查 'window') (名+' · ru_notepad').
    然
    编文 取 编码名 (文档 其 查 'encoding').
    若 文档 其 查 'bom' 则 编文 取 编文+' BOM'. 然
    模式文 取 ''.
    若 文档 其 查 'large' 则 模式文 取 '    '+(本地 其 文本 'status.large_file'). 然
    语言名 取 语 其 名称 (文档 其 查 'language').
    语态 取 语 其 状态 (文档 其 查 'editor').
    若 语态 != 空 则
        若 非 语态['enabled'] 则 语言名 取 语 其 名称 'plain'. 然
        若 语态['warning'] != '' 则 模式文 取 模式文+'    '+语态['warning']. 然
        若 语态['pending'] 则
            若 (文档 其 查 'language') == 'markdown' 则 模式文 取 模式文+'    '+(本地 其 文本 'status.folding_markdown').
            另 模式文 取 模式文+'    '+(本地 其 文本 'status.styling_ru'). 然
        然
        若 (文档 其 查 'language') == 'markdown' 且 非 (文档 其 查 'markdownFolds') 则 模式文 取 模式文+'    '+(本地 其 文本 'status.heading_folds_off'). 然
    然
    基文 取 '  '+(态 其 文本 (文档 其 查 'editor'))+'    '+编文+'    '+语言名+模式文.
    A 其 增 'statusBase' 基文.
    A 其 增 'statusOwner' ((文档 其 查 'editor') 其 句).
    诊文 取 ''.
    若 (文档 其 查 'language') == 'markdown' 则 诊文 取 刷新Markdown诊断 语态. 然
    窗 其 标题 (A 其 查 'status') (基文+诊文).
    得 空.
法
算 移控 柄, 横, 纵, 宽, 高:
    若 宽 < 1 则 宽 取 1. 然
    若 高 < 1 则 高 取 1. 然
    窗 其 结果 ((窗 其 MoveWindow) 其 调用 [柄,横,纵,宽,高,1]).
    得 空.
法
算 按钮宽 名 为 句:
    柄 取 A 其 查 名.
    宽 取 (窗 其 测文宽 柄 (窗 其 取文 柄))+26.
    若 名 == 'case' 或 名 == 'whole' 或 名 == 'searchWrap' 则 宽 取 宽+18. 然
    若 宽 < 64 则 宽 取 64. 然
    得 宽.
法
算 布局:
    若 非 (A 其 查 'ready') 则 得 空. 然
    矩 取 (窗 其 RECT) 其 新建.
    窗 其 成功 ((窗 其 GetClientRect) 其 调用 (参 其 窗口二参 A 矩)) 'GetClientRect'.
    宽 取 (矩 其 读 'right') 其 数.
    高 取 (矩 其 读 'bottom') 其 数.
    矩 其 关闭.
    寻高 取 0.
    位置 取 空.
    控们 取 ['case','whole','searchWrap','previous','next','one','all','hide'].
    若 A 其 查 'search' 则
        宽们 取 [].
        位 取 0.
        循 控们 其 量 次
            宽们 其 增 (按钮宽 控们[位]).
            位 取 位+1.
        环
        位置 取 布局策 其 寻栏布局 宽 宽们.
        寻高 取 位置['height'].
    然
    移控 (A 其 查 'tabs') 0 0 宽 30.
    状态宽 取 宽.
    取消宽 取 按钮宽 'cancel'.
    若 A 其 查 'busy' 则 状态宽 取 宽-取消宽-4. 然
    移控 (A 其 查 'status') 0 (高-25) 状态宽 25.
    移控 (A 其 查 'cancel') (宽-取消宽-2) (高-25) 取消宽 25.
    若 (A 其 查 'active') >= 0 则 移控 编辑柄 0 32 宽 (高-57-寻高). 然
    若 位置 == 空 则 得 空. 然
    栏纵 取 高-25-寻高.
    输入宽 取 位置['inputWidth'].
    移控 (A 其 查 'find') 8 (栏纵+5) 输入宽 26.
    移控 (A 其 查 'replace') (16+输入宽) (栏纵+5) 输入宽 26.
    按们 取 位置['buttons'].
    位 取 0.
    循 控们 其 量 次
        定位 取 按们[位].
        移控 (A 其 查 控们[位]) 定位[0] (栏纵+定位[1]) 定位[2] 定位[3].
        位 取 位+1.
    环
    得 空.
法
算 界面文字:
    标控们 取 ['cancel','case','whole','searchWrap','previous','next','one','all','hide'].
    标键们 取 ['search.cancel','search.case','search.whole','search.wrap','search.previous','search.next','search.replace','search.all','search.close'].
    位 取 0.
    循 标控们 其 量 次
        窗 其 标题 (A 其 查 标控们[位]) (本地 其 文本 标键们[位]).
        位 取 位+1.
    环
    控们 取 ['tabs','status','cancel','find','replace','case','whole','searchWrap','previous','next','one','all','hide'].
    位 取 0.
    循 控们 其 量 次
        窗 其 界面字体 (A 其 查 控们[位]).
        位 取 位+1.
    环
    窗 其 输入提示 (A 其 查 'find') (本地 其 文本 'search.find').
    窗 其 输入提示 (A 其 查 'replace') (本地 其 文本 'search.replace_with').
    得 空.
法
算 切界面 代码 为 句, 持久 为 事实:
    若 代码 != 'system' 且 非 (本地 其 有语言 代码) 则 代码 取 'en'. 然
    A 其 增 'uiPreference' 代码.
    本地 其 设置 (偏好 其 决定 代码 (偏好 其 系统语言)).
    界面文字.
    菜单.
    文们 取 A 其 查 'docs'.
    位 取 0.
    循 文们 其 量 次
        文档 取 文们[位].
        若 (文档 其 查 'path') == '' 则
            文档 其 增 'name' (本地 其 格式 'document.untitled' ([(文档 其 查 'untitledNumber')])).
            # Update every tab without activating it or changing editor state.
            存 取 密 其 UTF16 (页标题 文档).
            项 取 (窗 其 TCITEM) 其 新建.
            项 其 写 'mask' 1.
            项 其 写 'text' (存 其 地址).
            窗 其 发指 (A 其 查 'tabs') 4925 位 项.
            项 其 关闭.
            存 其 关闭.
            文档 其 增 'label' ''.
        然
        位 取 位+1.
    环
    布局.
    刷新.
    若 持久 则
        错 取 偏好 其 保存偏好 代码.
        若 错 != 0 则 错误提示 (本地 其 格式 'settings.persistence' ([错])). 然
    然
    得 空.
法
算 寻栏 显示 为 事实:
    A 其 增 'search' 显示.
    模式 取 0.
    若 显示 则 模式 取 5. 然
    控们 取 ['find','replace','case','whole','searchWrap','previous','next','one','all','hide'].
    位 取 0.
    循 控们 其 量 次
        窗 其 结果 ((窗 其 ShowWindow) 其 调用 (参 其 控件二参 A 控们[位] 模式)).
        位 取 位+1.
    环
    布局.
    若 显示 则
        窗 其 结果 ((窗 其 SetFocus) 其 调用 [A 其 查 'find']).
        窗 其 发送 (A 其 查 'find') 177 0 (-1).
    另
        窗 其 结果 ((窗 其 SetFocus) 其 调用 [编辑柄]).
    然
    得 空.
法
算 切页 索引:
    文们 取 A 其 查 'docs'.
    若 索引 < 0 或 索引 >= (文们 其 量) 则 得 空. 然
    旧 取 A 其 查 'active'.
    若 旧 >= 0 且 旧 < (文们 其 量) 则
        窗 其 结果 ((窗 其 ShowWindow) 其 调用 (参 其 控件二参 文们[旧] 'editor' 0)).
    然
    A 其 增 'active' 索引.
    窗 其 发送 (A 其 查 'tabs') 4876 索引 0.
    窗 其 结果 ((窗 其 ShowWindow) 其 调用 [编辑柄,5]).
    窗 其 结果 ((窗 其 SetFocus) 其 调用 [编辑柄]).
    当前 其 增 'label' ''.
    安排语法.
    布局.
    刷新.
    得 空.
法
# All app editors have one exclusive private document, this controlled parent,
# and only the known file_drop child subclass. Any future hook/shared-document
# path MUST revoke direct ownership before its first change.
# Selection discards prior capability; only this owning path opts back in.
算 选择语法 柄 语言 为 句:
    已选 取 语 其 选择 柄 语言.
    若 已选 == 'ru' 或 已选 == 'markdown' 则 语 其 登记直属 柄 (A 其 查 'window'). 然
    得 已选.
法
# Tab ownership is committed only after initialization and native insertion succeed.
算 登记页 柄, 路 为 句, 编码, BOM, 戳 为 句, 身份 为 句, 大型 为 事实:
    文们 取 A 其 查 'docs'.
    若 (文们 其 量) >= 64 则 卒 (本地 其 文本 'error.main.document_limit_remaining'). 然
    序 取 (A 其 查 'counter')+1.
    A 其 增 'counter' 序.
    名 取 短名 路.
    若 路 == '' 则 名 取 本地 其 格式 'document.untitled' ([序]). 然
    语言 取 'plain'.
    若 非 大型 则 语言 取 选择语法 柄 (语 其 识别 路). 然
    文档 取 {'editor':柄,'path':路,'untitledNumber':序,'name':名,'encoding':编码,'bom':BOM,'stamp':戳,'fileIdentity':身份,'encodingDirty':假,'label':'','wrap':假,'language':语言,'markdownFolds':真,'large':大型,'revision':0}.
    项 取 (窗 其 TCITEM) 其 新建.
    存 取 空.
    试
        存 取 密 其 UTF16 名.
        项 其 写 'mask' 1.
        项 其 写 'text' (存 其 地址).
        插位 取 (窗 其 发指 (A 其 查 'tabs') 4926 (文们 其 量) 项) 其 数.
        若 插位 == -1 则 卒 (本地 其 文本 'error.main.tab_create'). 然
    救 原因
        若 存 != 空 则 存 其 关闭. 然
        项 其 关闭.
        卒 原因.
    终
    存 其 关闭.
    项 其 关闭.
    文们 其 增 文档.
    得 文档.
法
算 配置修改通知 柄:
    # The application consumes insert/delete SCN_MODIFIED only. Scintilla still
    # owns style/fold updates and sends independent savepoint/UI notifications.
    窗 其 发送 柄 2359 3 0. # SCI_SETMODEVENTMASK: INSERTTEXT | DELETETEXT.
    编 其 检查状态 柄.
    若 (窗 其 发送 柄 2378 0 0) 其 数 != 3 则 卒 'Scintilla did not retain the text modification notification mask.'. 然
    得 空.
法
算 新页 路 为 句, 文 为 句, 编码, BOM, 戳 为 句:
    若 A 其 查 'busy' 则 卒 (本地 其 文本 'error.main.operation_busy'). 然
    若 ((A 其 查 'docs') 其 量) >= 64 则 卒 (本地 其 文本 'error.main.document_limit'). 然
    编 其 验文本 文.
    柄 取 编 其 创建 (A 其 查 'window') (A 其 查 'instance') (1001+(A 其 查 'counter')).
    试
        配置修改通知 柄.
        拖放 其 启用编辑器 柄 (A 其 查 'window').
        编 其 设文本 柄 文.
        文档 取 登记页 柄 路 编码 BOM 戳 '' 假.
    救 原因
        语 其 遗忘 柄.
        窗 其 结果 ((窗 其 DestroyWindow) 其 调用 [柄]).
        卒 原因.
    终
    切页 (((A 其 查 'docs') 其 量)-1).
    得 文档.
法
算 询大文件 大小 为 数:
    若 非 (A 其 查 'visible') 则 得 假. 然
    得 (界面弹窗 (A 其 查 'window') (本地 其 格式 'dialog.large_file' ([大小])) (本地 其 文本 'dialog.large_file.title') 292) == 6.
法
算 锁界面:
    文们 取 A 其 查 'docs'.
    锁们 取 A 其 查 'locks'.
    位 取 0.
    循 文们 其 量 次
        柄 取 文们[位] 其 查 'editor'.
        原 取 (窗 其 发送 柄 2140 0 0) 其 数.
        锁们 其 增 [柄,原].
        窗 其 发送 柄 2171 1 0.
        窗 其 结果 ((窗 其 EnableWindow) 其 调用 [柄,0]).
        位 取 位+1.
    环
    窗 其 结果 ((窗 其 EnableWindow) 其 调用 [(A 其 查 'tabs'),0]).
    窗 其 结果 ((窗 其 ShowWindow) 其 调用 [(A 其 查 'cancel'),5]).
    布局.
    得 空.
法
算 开始工作:
    若 A 其 查 'busy' 则 卒 (本地 其 文本 'error.main.operation_busy'). 然
    A 其 增 'busy' 真.
    A 其 增 'openFinalizing' 假.
    A 其 增 'handoffReject' 假.
    A 其 增 'cancelRequested' 假.
    A 其 增 'locks' ([]).
    试
        锁界面.
        窗 其 成功 ((窗 其 SetTimer) 其 调用 [(A 其 查 'window'),901,10,空]) 'SetTimer(file operation)'.
    救 原因
        结束工作.
        卒 原因.
    终
    得 空.
法
算 结束工作:
    若 A 其 查 'cleanupActive' 则 卒 (本地 其 文本 'error.main.operation_busy'). 然
    A 其 增 'cleanupActive' 真.
    试
        # Guard every native teardown call, including UI refresh after busy becomes false.
        若 非 (A 其 查 'openFinalizing') 则 A 其 增 'handoffReject' 真. 然
        窗 其 结果 ((窗 其 KillTimer) 其 调用 [(A 其 查 'window'),901]).
        锁们 取 A 其 查 'locks'.
        位 取 0.
        循 锁们 其 量 次
            锁 取 锁们[位].
            窗 其 发送 锁[0] 2171 锁[1] 0.
            窗 其 结果 ((窗 其 EnableWindow) 其 调用 [锁[0],1]).
            位 取 位+1.
        环
        A 其 增 'locks' ([]).
        A 其 增 'operation' 空.
        # Idle layout is visible, but routing remains guarded until all UI calls return.
        A 其 增 'busy' 假.
        A 其 增 'cancelRequested' 假.
        窗 其 结果 ((窗 其 EnableWindow) 其 调用 [(A 其 查 'tabs'),1]).
        窗 其 结果 ((窗 其 ShowWindow) 其 调用 [(A 其 查 'cancel'),0]).
        布局.
        刷新.
        若 (A 其 查 'active') >= 0 则 窗 其 结果 ((窗 其 SetFocus) 其 调用 [编辑柄]). 然
        A 其 增 'openFinalizing' 假.
        A 其 增 'handoffReject' 假.
        A 其 增 'cleanupPending' 假.
    救 原因
        A 其 增 'cleanupPending' 真.
        A 其 增 'handoffReject' 真.
        A 其 增 'openFinalizing' 假.
        A 其 增 'cleanupActive' 假.
        # A stable document transaction permits explicit menu/shortcut recovery.
        若 (A 其 查 'operation') == 空 且 ((A 其 查 'queue') 其 量) == 0 则 A 其 增 'busy' 假. 然
        卒 原因.
    终
    A 其 增 'cleanupActive' 假.
    得 空.
法
# Only an explicit rejected idle tail can be recovered; never recurse into live teardown.
算 恢复工作收尾:
    若 非 (A 其 查 'cleanupPending') 或 非 (A 其 查 'handoffReject') 或 (A 其 查 'operation') != 空 或 ((A 其 查 'queue') 其 量) != 0 或 (A 其 查 'cleanupActive') 或 (A 其 查 'cleanupRetrying') 则 得 假. 然
    A 其 增 'cleanupRetrying' 真.
    试
        结束工作.
    救 原因
        A 其 增 'cleanupRetrying' 假.
        卒 原因.
    终
    A 其 增 'cleanupRetrying' 假.
    得 真.
法
算 清操作:
    操 取 A 其 查 'operation'.
    若 操 == 空 则 得 空. 然
    A 其 增 'operation' 空.
    若 操['kind'] == 'open' 则
        件编 其 关闭读取 操['reader'].
        若 操['editor'] != 空 则
            语 其 遗忘 操['editor'].
            窗 其 结果 ((窗 其 DestroyWindow) 其 调用 [操['editor']]).
        然
    另
        件编 其 取消写入 操['writer'].
    然
    得 空.
法
算 取消工作:
    A 其 增 'cancelRequested' 真.
    A 其 增 'openFinalizing' 假.
    A 其 增 'queue' ([]).
    A 其 增 'closeIndex' (-1).
    A 其 增 'lastOutcome' 'cancelled'.
    显 '[operation] cancelled'.
    试
        清操作.
    救 原因
        结束工作.
        卒 原因.
    终
    结束工作.
    结束批关 真.
    得 空.
法
算 校验入队 路们 为 句 阵, 代码页 为 数:
    若 (路们 其 量) > 64 则 卒 (本地 其 文本 'error.main.batch_count'). 然
    队 取 [].
    总 取 0.
    位 取 0.
    循 路们 其 量 次
        路 取 路们[位].
        若 路 != '' 则
            若 (路 其 量) > 32000 则 卒 (本地 其 文本 'error.main.batch_path_length'). 然
            存 取 密 其 UTF16 路.
            长 取 ((存 其 大小)/2)-1.
            存 其 关闭.
            总 取 总+长+1.
            若 长 > 32000 或 总 > 2097152 则 卒 (本地 其 文本 'error.main.batch_queue'). 然
            队 其 增 [路,代码页].
        然
        位 取 位+1.
    环
    得 队.
法
算 入队 路们 为 句 阵, 代码页 为 数:
    恢复工作收尾.
    若 (A 其 查 'openFinalizing') 或 (A 其 查 'handoffReject') 则 卒 (本地 其 文本 'error.main.open_busy'). 然
    若 (A 其 查 'closeRun') != 空 或 (A 其 查 'tabMenuOpen') 则 卒 (本地 其 文本 'error.main.open_busy'). 然
    若 A 其 查 'busy' 则 卒 (本地 其 文本 'error.main.open_busy'). 然
    队 取 校验入队 路们 代码页.
    若 (队 其 量) == 0 则 得 假. 然
    A 其 增 'queue' 队.
    A 其 增 'lastOutcome' 'running'.
    试
        开始工作.
    救 原因
        A 其 增 'queue' ([]).
        若 (A 其 查 'cleanupPending') 且 (A 其 查 'operation') == 空 则 A 其 增 'busy' 假. 然
        卒 原因.
    终
    得 真.
法
算 交接待收尾:
    若 (A 其 查 'handoffReject') 或 (A 其 查 'cancelRequested') 或 (A 其 查 'modalDepth') > 0 或 (A 其 查 'closeIndex') >= 0 或 (A 其 查 'closeRun') != 空 或 (A 其 查 'tabMenuOpen') 则 得 假. 然
    得 (A 其 查 'openFinalizing') 且 (A 其 查 'operation') == 空 且 ((A 其 查 'queue') 其 量) == 0.
法
算 接收入队 路们 为 句 阵:
    若 (A 其 查 'handoffReject') 或 (A 其 查 'cancelRequested') 则 卒 (本地 其 文本 'error.main.open_busy'). 然
    若 非 (A 其 查 'busy') 则 得 入队 路们 0. 然
    若 (A 其 查 'closeRun') != 空 或 (A 其 查 'tabMenuOpen') 则 卒 (本地 其 文本 'error.main.open_busy'). 然
    操 取 A 其 查 'operation'.
    旧队 取 A 其 查 'queue'.
    # Only an active serial-open queue may be extended. Save/cancel/finalization
    # never ACKs a request that its completion path would discard.
    若 操 != 空 则
        若 操['kind'] != 'open' 则 卒 (本地 其 文本 'error.main.open_busy'). 然
    另
        若 (旧队 其 量) == 0 则 卒 (本地 其 文本 'error.main.open_busy'). 然
    然
    新队 取 校验入队 路们 0.
    所有路 取 []. 位 取 0.
    若 操 != 空 则 所有路 其 增 操['reader']['path']. 然
    循 旧队 其 量 次 所有路 其 增 旧队[位][0]. 位 取 位+1. 环
    位 取 0.
    循 新队 其 量 次 所有路 其 增 新队[位][0]. 位 取 位+1. 环
    校验入队 所有路 0.
    # Keep previous encoding choices; publish the whole validated list once.
    合队 取 []. 位 取 0.
    循 旧队 其 量 次 合队 其 增 旧队[位]. 位 取 位+1. 环
    位 取 0.
    循 新队 其 量 次 合队 其 增 新队[位]. 位 取 位+1. 环
    A 其 增 'queue' 合队.
    得 真.
法
# Only completed opens reach this hook. History is a best-effort preference,
# never part of the document transaction or a reason to discard its editor.
算 空最近:
    得 {'items':[],'error':0}.
法
算 不存最近 项们 为 阵:
    得 0.
法
算 持久最近:
    码盒 取 [0].
    试
        存近函数 取 A 其 查 'recentWriter'.
        若 存近函数 != 空 则 码盒[0] 取 存近函数 (A 其 查 'recentItems'). 然
    救 原因
        码盒[0] 取 13.
    终
    A 其 增 'recentError' 码盒[0].
    若 码盒[0] != 0 则 显 '[recent] preference write failed: '+(码盒[0] 为 句). 然
    得 码盒[0] == 0.
法
算 记最近 路 为 句, 编码 为 数:
    试
        A 其 增 'recentItems' (最近 其 更新 (A 其 查 'recentItems') 路 编码).
        持久最近.
        若 非 ((A 其 查 'window') 其 为空) 则 菜单. 然
    救 原因
        A 其 增 'recentError' 13.
        显 '[recent] preference update unavailable.'.
    终
    得 空.
法
算 清最近:
    A 其 增 'recentItems' ([]).
    持久最近.
    菜单.
    若 (A 其 查 'recentError') != 0 则 提示 (本地 其 文本 'recent.persistence_failed'). 然
    得 空.
法
算 打开 路 为 句, 代码页:
    得 入队 [路] 代码页.
法
算 下个文件:
    队 取 A 其 查 'queue'.
    若 (队 其 量) == 0 则 结束工作. 得 空. 然
    项 取 队[0].
    队 其 删 0.
    读态 取 件编 其 准备读取 项[0] 项[1].
    A 其 增 'lastReader' 读态.
    操 取 {'kind':'open','reader':读态,'editor':空,'load':空}.
    A 其 增 'operation' 操.
    A 其 增 'openFinalizing' 假.
    文们 取 A 其 查 'docs'.
    位 取 0.
    循 文们 其 量 次
        若 (文们[位] 其 查 'fileIdentity') == 读态['fileIdentity'] 则
            件编 其 关闭读取 读态.
            A 其 增 'operation' 空.
            切页 位.
            A 其 增 'lastOutcome' 'duplicate'.
            记最近 读态['path'] (文们[位] 其 查 'encoding').
            得 空.
        然
        位 取 位+1.
    环
    若 (文们 其 量) >= 64 则 卒 (本地 其 文本 'error.main.document_limit_tabs'). 然
    确认 取 A 其 查 'confirmLarge'.
    若 非 (件编 其 确认读取 读态 确认) 则
        A 其 增 'operation' 空.
        A 其 增 'lastOutcome' 'declined'.
        得 空.
    然
    柄 取 编 其 创建 (A 其 查 'window') (A 其 查 'instance') (1001+(A 其 查 'counter')).
    操 其 增 'editor' 柄.
    配置修改通知 柄.
    拖放 其 启用编辑器 柄 (A 其 查 'window').
    操 其 增 'load' (编 其 开始载入 柄 读态['size']).
    显 '[operation] open started'.
    得 空.
法
算 保存到 路 为 句, 戳 为 句, 后续 为 句:
    恢复工作收尾.
    若 (A 其 查 'openFinalizing') 或 (A 其 查 'handoffReject') 则 卒 (本地 其 文本 'error.main.operation_busy'). 然
    若 A 其 查 'busy' 则 卒 (本地 其 文本 'error.main.operation_busy'). 然
    文档 取 当前.
    A 其 增 'lastOutcome' 'running'.
    开始工作.
    试
        写态 取 件编 其 准备写入 路 (文档 其 查 'encoding') (文档 其 查 'bom') 戳.
        A 其 增 'lastWriter' 写态.
        操 取 {'kind':'save','writer':写态,'doc':文档,'revision':(文档 其 查 'revision'),'source':空,'after':后续}.
        A 其 增 'operation' 操.
        操 其 增 'source' (编 其 开始取文 (文档 其 查 'editor')).
    救 原因
        报错 取 [原因].
        # A nested rescue has its own bindings. Mutate the shared holder so
        # staging cleanup failures remain visible alongside the original error.
        试 清操作. 救 清因 报错[0] 取 报错[0]+'\n'+清因. 终
        结束工作.
        卒 报错[0].
    终
    得 真.
法
算 选保存路径 原路 为 句:
    得 界面文件对话 真 原路.
法
算 请求保存 另存 为 事实, 后续 为 句:
    若 A 其 查 'busy' 则 得 假. 然
    文档 取 当前.
    路 取 文档 其 查 'path'.
    戳 取 文档 其 查 'stamp'.
    若 另存 或 路 == '' 则
        选择路径 取 A 其 查 'chooseSavePath'.
        路 取 选择路径 路.
        若 路 == '' 则 得 假. 然
        路 取 件编 其 绝对路径 路.
        若 路 != (文档 其 查 'path') 则 戳 取 ''. 然
    然
    得 保存到 路 戳 后续.
法
算 保存 另存 为 事实:
    得 请求保存 另存 ''.
法
算 操作一步:
    操 取 A 其 查 'operation'.
    若 操 == 空 则 下个文件. 得 空. 然
    若 操['kind'] == 'open' 则
        读态 取 操['reader'].
        文 取 件编 其 读取一步 读态.
        若 文 != 空 则
            编 其 追加文本 操['load'] 文.
            窗 其 标题 (A 其 查 'status') ('  '+(本地 其 格式 'status.opening' ([(读态['position']),(读态['size'])]))).
            得 空.
        然
        编 其 完成载入 操['load'].
        文档 取 登记页 操['editor'] 读态['path'] 读态['encoding'] 读态['bom'] 读态['stamp'] 读态['fileIdentity'] (读态['size'] >= (编 其 大文件模式字节)).
        # The tab now owns the native editor. Never destroy it in error cleanup.
        操 其 增 'editor' 空.
        # Only a completed open enters this state; duplicate/declined remain NACK2.
        A 其 增 'openFinalizing' 真.
        A 其 增 'operation' 空.
        A 其 增 'lastOutcome' 'opened'.
        显 '[operation] open completed'.
        记最近 读态['path'] 读态['encoding'].
        柄 取 文档 其 查 'editor'.
        (A 其 查 'locks') 其 增 [柄,0].
        窗 其 发送 柄 2171 1 0.
        窗 其 结果 ((窗 其 EnableWindow) 其 调用 [柄,0]).
        切页 (((A 其 查 'docs') 其 量)-1).
        得 空.
    然
    文档 取 操['doc'].
    若 (文档 其 查 'revision') != 操['revision'] 则 卒 (本地 其 文本 'error.main.save_changed'). 然
    文 取 编 其 取文一步 操['source'].
    写态 取 操['writer'].
    若 文 != 空 则
        件编 其 写入一段 写态 文.
        窗 其 标题 (A 其 查 'status') ('  '+(本地 其 格式 'status.saving' ([(操['source']['position']),(操['source']['bytes'])]))).
        得 空.
    然
    # No message pumping occurs across the conflict check / atomic commit phase.
    新戳 取 件编 其 完成写入 写态.
    原路 取 文档 其 查 'path'.
    文档 其 增 'path' 写态['path'].
    文档 其 增 'name' (短名 写态['path']).
    文档 其 增 'stamp' 新戳.
    文档 其 增 'fileIdentity' 写态['fileIdentity'].
    文档 其 增 'encodingDirty' 假.
    编 其 记保存 (文档 其 查 'editor').
    后续 取 操['after'].
    A 其 增 'operation' 空.
    A 其 增 'lastOutcome' 'saved'.
    显 '[operation] save completed'.
    结束工作.
    若 原路 != 写态['path'] 且 非 (文档 其 查 'large') 则
        文档 其 增 'language' (选择语法 (文档 其 查 'editor') (语 其 识别 写态['path'])).
        若 (文档 其 查 'language') == 'markdown' 则 语 其 设置折叠 (文档 其 查 'editor') (文档 其 查 'markdownFolds'). 然
        安排语法.
    然
    刷新.
    若 后续 == 'batch' 则
        关程 取 A 其 查 'closeRun'.
        若 关程 != 空 则
            若 ((关程['saving'] 其 查 'editor') 其 句) != ((文档 其 查 'editor') 其 句) 或 (脏 文档) 则
                结束批关 真.
            另
                关程 其 增 'saving' 空.
                继续批关.
            然
        然
    然
    若 后续 == 'tab' 则 删除当前页. 然
    若 后续 == 'app' 则 继续关闭. 然
    得 空.
法
算 工作时钟:
    若 非 (A 其 查 'busy') 或 (A 其 查 'inTick') 或 (A 其 查 'cleanupActive') 或 (A 其 查 'cleanupRetrying') 则 得 空. 然
    A 其 增 'inTick' 真.
    A 其 增 'ticks' ((A 其 查 'ticks')+1).
    起 取 (窗 其 结果 ((窗 其 GetTickCount64) 其 调用 [])) 其 数.
    试
        循 4 次
            若 A 其 查 'cancelRequested' 则 取消工作. 破. 然
            操作一步.
            若 非 (A 其 查 'busy') 则 破. 然
            现 取 (窗 其 结果 ((窗 其 GetTickCount64) 其 调用 [])) 其 数.
            若 现-起 >= 8 则 破. 然
        环
    救 原因
        A 其 增 'handoffReject' 真.
        A 其 增 'openFinalizing' 假.
        报错 取 [原因].
        试
            操 取 A 其 查 'operation'.
            为保存 取 操 != 空 且 操['kind'] == 'save'.
            试 清操作. 救 清因 报错[0] 取 报错[0]+'\n'+清因. 终
            A 其 增 'lastOutcome' 'failed'.
            A 其 增 'closeIndex' (-1).
            若 为保存 则
                A 其 增 'queue' ([]).
                试 结束工作. 救 清因 报错[0] 取 报错[0]+'\n'+清因. 终
            然
            # One bounded automatic retry only for an idle, empty, rejected tail.
            试 恢复工作收尾. 救 清因 报错[0] 取 报错[0]+'\n'+清因. 终
            结束批关 真.
            错误提示 报错[0].
        救 处理因
            A 其 增 'inTick' 假.
            卒 (报错[0]+'\n'+处理因).
        终
    终
    A 其 增 'inTick' 假.
    得 空.
法
算 询问关闭 文档:
    得 界面弹窗 (A 其 查 'window') (本地 其 格式 'dialog.unsaved' ([(文档 其 查 'name')])) (本地 其 文本 'dialog.unsaved.title') 35.
法
算 删除当前页:
    # Invalidate before forgetting or destroying a document with queued work.
    停止语法.
    文们 取 A 其 查 'docs'.
    位 取 A 其 查 'active'.
    柄 取 编辑柄.
    A 其 增 'active' (-1).
    语 其 遗忘 柄.
    窗 其 成功 ((窗 其 DestroyWindow) 其 调用 [柄]) 'DestroyWindow(editor)'.
    文们 其 删 位.
    窗 其 发送 (A 其 查 'tabs') 4872 位 0.
    若 (文们 其 量) == 0 则
        新页 '' '' 65001 假 ''.
    另
        若 位 >= (文们 其 量) 则 位 取 (文们 其 量)-1. 然
        切页 位.
    然
    安排语法.
    得 真.
法
# Stable identity snapshot; save/confirm all before any destructive removal.
# Completed disk saves are intentionally not rolled back if a later prompt cancels.
算 文档位置 文档:
    若 文档 == 空 则 得 -1. 然
    文们 取 A 其 查 'docs'. 位 取 0.
    循 文们 其 量 次
        若 ((文们[位] 其 查 'editor') 其 句) == ((文档 其 查 'editor') 其 句) 则 得 位. 然
        位 取 位+1.
    环
    得 -1.
法
算 结束批关 恢复 为 事实:
    关程 取 A 其 查 'closeRun'.
    若 关程 == 空 则 得 空. 然
    A 其 增 'closeRun' 空.
    锁们 取 关程['locks']. 位 取 0.
    循 锁们 其 量 次
        锁 取 锁们[位].
        若 (文档位置 锁[0]) >= 0 则
            柄 取 锁[0] 其 查 'editor'.
            窗 其 发送 柄 2171 锁[1] 0.
            窗 其 结果 ((窗 其 EnableWindow) 其 调用 [柄,1]).
        然
        位 取 位+1.
    环
    窗 其 结果 ((窗 其 EnableWindow) 其 调用 [(A 其 查 'tabs'),1]).
    若 恢复 则
        原位 取 文档位置 关程['original'].
        若 原位 >= 0 则 切页 原位. 然
    然
    得 空.
法
算 继续批关:
    关程 取 A 其 查 'closeRun'.
    若 关程 == 空 则 得 假. 然
    项们 取 关程['items'].
    锁位 取 0.
    循 (关程['locks']) 其 量 次
        锁文 取 关程['locks'][锁位][0].
        若 (文档位置 锁文) >= 0 则 窗 其 结果 ((窗 其 EnableWindow) 其 调用 [(锁文 其 查 'editor'),0]). 然
        锁位 取 锁位+1.
    环
    窗 其 结果 ((窗 其 EnableWindow) 其 调用 [(A 其 查 'tabs'),0]).
    试
        循
            若 关程['next'] >= (项们 其 量) 则 破. 然
            位 取 关程['next']. 项 取 项们[位].
            索引 取 文档位置 项[0].
            若 索引 < 0 或 (项[0] 其 查 'revision') != 项[1] 则 卒 (本地 其 文本 'tab.close_changed'). 然
            切页 索引.
            若 脏 项[0] 则
                询关 取 A 其 查 'confirmClose'.
                选 取 询关 项[0].
                若 选 == 6 则
                    关程 其 增 'next' (位+1).
                    关程 其 增 'saving' 项[0].
                    若 非 (请求保存 假 'batch') 则 结束批关 真. 然
                    得 假.
                然
                若 选 != 7 则 结束批关 真. 得 假. 然
            然
            关程 其 增 'next' (位+1).
        环
        位 取 0.
        循 项们 其 量 次
            项 取 项们[位].
            若 (文档位置 项[0]) < 0 或 (项[0] 其 查 'revision') != 项[1] 则 卒 (本地 其 文本 'tab.close_changed'). 然
            位 取 位+1.
        环
        位 取 0.
        循 项们 其 量 次
            切页 (文档位置 项们[位][0]).
            删除当前页.
            位 取 位+1.
        环
        结束批关 真.
    救 原因
        结束批关 真. 卒 原因.
    终
    得 真.
法
算 批关 点击 为 数, 动作 为 句:
    若 (A 其 查 'busy') 或 (A 其 查 'closeRun') != 空 则 得 假. 然
    文们 取 A 其 查 'docs'. 脏们 取 []. 位 取 0.
    循 文们 其 量 次
        脏们 其 增 (脏 文们[位]). 位 取 位+1.
    环
    目标们 取 关策 其 目标 (文们 其 量) 点击 动作 脏们.
    若 (目标们 其 量) == 0 则 得 假. 然
    项们 取 []. 位 取 0.
    循 目标们 其 量 次
        文档 取 文们[目标们[位]].
        项们 其 增 [文档,(文档 其 查 'revision')].
        位 取 位+1.
    环
    关程 取 {'items':项们,'next':0,'saving':空,'original':当前,'locks':[]}.
    A 其 增 'closeRun' 关程.
    试
        位 取 0.
        循 文们 其 量 次
            柄 取 文们[位] 其 查 'editor'.
            (关程['locks']) 其 增 [文们[位],((窗 其 发送 柄 2140 0 0) 其 数)].
            窗 其 发送 柄 2171 1 0.
            窗 其 结果 ((窗 其 EnableWindow) 其 调用 [柄,0]).
            位 取 位+1.
        环
        窗 其 结果 ((窗 其 EnableWindow) 其 调用 [(A 其 查 'tabs'),0]).
        得 继续批关.
    救 原因
        结束批关 真. 卒 原因.
    终
法
算 页右键:
    若 (A 其 查 'busy') 或 (A 其 查 'closeRun') != 空 则 得 空. 然
    点击 取 页单 其 点击 (A 其 查 'tabs').
    文们 取 A 其 查 'docs'.
    若 点击 < 0 或 点击 >= (文们 其 量) 则 得 空. 然
    切页 点击.
    干净 取 假. 位 取 0.
    循 文们 其 量 次
        若 非 (脏 文们[位]) 则 干净 取 真. 然
        位 取 位+1.
    环
    A 其 增 'tabMenuOpen' 真.
    号盒 取 [0].
    试
        号盒[0] 取 页单 其 弹出 (A 其 查 'window') ([真,((文们 其 量)>1),(点击>0),(点击<(文们 其 量)-1),干净,真]).
    救 原因
        A 其 增 'tabMenuOpen' 假. 卒 原因.
    终
    A 其 增 'tabMenuOpen' 假.
    号 取 号盒[0].
    若 号 >= 1300 且 号 <= 1305 则 批关 点击 (['current','others','left','right','saved','all'][号-1300]). 然
    得 空.
法
算 关页:
    若 (A 其 查 'closeRun') != 空 或 (A 其 查 'tabMenuOpen') 则 得 假. 然
    若 A 其 查 'busy' 则 A 其 增 'cancelRequested' 真. 得 假. 然
    若 脏 当前 则
        询关 取 A 其 查 'confirmClose'.
        选 取 询关 当前.
        若 选 == 6 则 请求保存 假 'tab'. 得 假. 然
        若 选 != 7 则 得 假. 然
    然
    得 删除当前页.
法
算 继续关闭:
    文们 取 A 其 查 'docs'.
    循
        位 取 A 其 查 'closeIndex'.
        若 位 < 0 则 得 假. 然
        若 位 >= (文们 其 量) 则 破. 然
        切页 位.
        A 其 增 'closeIndex' (位+1).
        若 脏 当前 则
            询关 取 A 其 查 'confirmClose'.
        选 取 询关 当前.
            若 选 == 6 则
                若 非 (请求保存 假 'app') 则 A 其 增 'closeIndex' (-1). 然
                得 假.
            然
            若 选 != 7 则 A 其 增 'closeIndex' (-1). 得 假. 然
        然
    环
    A 其 增 'closeIndex' (-1).
    A 其 增 'ready' 假.
    停止语法.
    位 取 0.
    循 文们 其 量 次
        语 其 遗忘 (文们[位] 其 查 'editor').
        位 取 位+1.
    环
    窗 其 成功 ((窗 其 DestroyWindow) 其 调用 [A 其 查 'window']) 'DestroyWindow(main)'.
    得 真.
法
算 关程序:
    若 (A 其 查 'closeRun') != 空 或 (A 其 查 'tabMenuOpen') 则 得 假. 然
    若 A 其 查 'busy' 则 A 其 增 'cancelRequested' 真. 得 假. 然
    A 其 增 'closeIndex' 0.
    得 继续关闭.
法
算 命令 号:
    若 (A 其 查 'closeRun') != 空 且 号 != 901 则 得 空. 然
    若 A 其 查 'tabMenuOpen' 则 得 空. 然
    若 号 == 901 则
        若 A 其 查 'busy' 则 A 其 增 'cancelRequested' 真. 然
        得 空.
    然
    若 A 其 查 'busy' 则 得 空. 然
    若 号 >= 850 且 号 <= 857 则
        切界面 (['system','en','zh-CN','ja','ko','es','ru','it'][号-850]) 真.
        得 空.
    然
    若 号 >= 1200 且 号 < 1210 则
        项们 取 A 其 查 'recentItems'.
        位 取 号-1200.
        若 位 < (项们 其 量) 则 打开 项们[位][0] 项们[位][1]. 然
        得 空.
    然
    若 号 == 805 则
        新偏好 取 非 (A 其 查 'singlePreference').
        存码 取 单设 其 保存偏好 新偏好.
        若 存码 != 0 则
            错误提示 (本地 其 格式 'instance.save_failed' ([存码])).
        另
            A 其 增 'singlePreference' 新偏好.
            菜单.
            提示 (本地 其 文本 'instance.next_launch').
        然
        得 空.
    然
    若 号 == 113 则 打开待确认. 得 空. 然
    若 号 == 1210 则 清最近. 得 空. 然
    若 号 == 101 则 新页 '' '' 65001 假 ''. 得 空. 然
    若 号 == 102 或 号 == 108 或 号 == 109 则
        代码页 取 0.
        若 号 == 108 则 代码页 取 1252. 然
        若 号 == 109 则 代码页 取 936. 然
        打开 (界面文件对话 假 '') 代码页.
        报语法警告.
        得 空.
    然
    若 号 == 103 则 保存 假. 得 空. 然
    若 号 == 104 则 保存 真. 得 空. 然
    若 号 == 105 则 关页. 得 空. 然
    若 号 == 106 则 关程序. 得 空. 然
    若 号 == 111 或 号 == 112 则
        数量 取 (A 其 查 'docs') 其 量.
        目标 取 (A 其 查 'active')+1.
        若 号 == 111 则 目标 取 (A 其 查 'active')+数量-1. 然
        切页 (目标%数量).
        得 空.
    然
    若 号 == 201 则 窗 其 发送 编辑柄 2176 0 0. 然
    若 号 == 202 则 窗 其 发送 编辑柄 2011 0 0. 然
    若 号 == 203 则 窗 其 发送 编辑柄 2177 0 0. 然
    若 号 == 204 则 窗 其 发送 编辑柄 2178 0 0. 然
    若 号 == 205 则 窗 其 发送 编辑柄 2179 0 0. 然
    若 号 == 206 则 窗 其 发送 编辑柄 2013 0 0. 然
    若 号 == 301 或 号 == 302 则 寻栏 真. 得 空. 然
    若 号 == 307 则 寻栏 假. 得 空. 然
    若 号 == 303 或 号 == 304 或 号 == 305 或 号 == 308 则
        词 取 窗 其 取文 (A 其 查 'find').
        新文 取 窗 其 取文 (A 其 查 'replace').
        区分 取 非 ((窗 其 发送 (A 其 查 'case') 240 0 0) 其 为空).
        整词 取 非 ((窗 其 发送 (A 其 查 'whole') 240 0 0) 其 为空).
        循环 取 非 ((窗 其 发送 (A 其 查 'searchWrap') 240 0 0) 其 为空).
        若 词 == '' 则 寻栏 真. 得 空. 然
        若 号 == 303 或 号 == 308 则
            若 (编 其 寻找 编辑柄 词 区分 整词 循环 (号 == 308)) == -1 则 提示 (本地 其 文本 'search.no_match'). 然
        然
        若 号 == 304 则
            若 (编 其 换当前选项 编辑柄 词 新文 区分 整词 循环) == -1 则 提示 (本地 其 文本 'search.no_further_match'). 然
        然
        若 号 == 305 则
            次数 取 编 其 全换选项 编辑柄 词 新文 区分 整词.
            提示 (本地 其 格式 'search.replacements' ([次数])).
        然
    然
    若 号 >= 401 且 号 <= 405 则
        编码 取 65001.
        BOM 取 假.
        若 号 == 402 则 BOM 取 真. 然
        若 号 == 403 则 编码 取 1200. BOM 取 真. 然
        若 号 == 404 则 编码 取 1201. BOM 取 真. 然
        若 号 == 405 则 编码 取 1252. 然
        模 其 改编码 当前 编码 BOM.
    然
    若 号 == 406 则
        模 其 改编码 当前 936 假.
    然
    若 (号 == 501 或 (号 >= 702 且 号 <= 705)) 且 (当前 其 查 'large') 则 提示 (本地 其 文本 'notice.large_file_mode'). 得 空. 然
    若 号 >= 701 且 号 <= 705 则
        语言 取 'plain'.
        若 号 == 702 则 语言 取 'cpp'. 然
        若 号 == 703 则 语言 取 'json'. 然
        若 号 == 704 则 语言 取 'ru'. 然
        若 号 == 705 则 语言 取 'markdown'. 然
        若 语言 == (当前 其 查 'language') 则
            若 语言 != 'ru' 则 得 空. 然
            语态 取 语 其 状态 编辑柄.
            若 语态 != 空 且 语态['enabled'] 则 得 空. 然
        然
        当前 其 增 'language' (选择语法 编辑柄 语言).
        若 语言 == 'markdown' 则 语 其 设置折叠 编辑柄 (当前 其 查 'markdownFolds'). 然
        安排语法.
        报语法警告.
    然
    若 号 == 505 或 号 == 506 则
        若 ((当前 其 查 'language') == 'ru' 或 (当前 其 查 'language') == 'markdown' 或 (当前 其 查 'language') == 'cpp') 且 非 (当前 其 查 'large') 则
            若 语 其 待办 编辑柄 则 提示 (本地 其 文本 'notice.folds_pending'). 得 空. 然
            动作 取 0.
            若 号 == 506 则 动作 取 1. 然
            语 其 全折 编辑柄 动作.
        然
    然
    若 号 == 507 且 (当前 其 查 'language') == 'markdown' 且 非 (当前 其 查 'large') 则
        当前 其 增 'markdownFolds' (非 (当前 其 查 'markdownFolds')).
        语 其 设置折叠 编辑柄 (当前 其 查 'markdownFolds').
        安排语法.
    然
    若 号 == 501 则
        当前 其 增 'wrap' (非 (当前 其 查 'wrap')).
        选 取 0.
        若 当前 其 查 'wrap' 则 选 取 1. 然
        窗 其 发送 编辑柄 2268 选 0.
    然
    若 号 == 502 则 窗 其 发送 编辑柄 2333 0 0. 然
    若 号 == 503 则 窗 其 发送 编辑柄 2334 0 0. 然
    若 号 == 504 则 窗 其 发送 编辑柄 2373 0 0. 然
    若 号 == 801 则
        若 (界面弹窗 (A 其 查 'window') (本地 其 文本 'dialog.register') (本地 其 文本 'dialog.register.title') 292) == 6 则
            关联 其 注册.
            提示 (本地 其 文本 'association.registered').
        然
    然
    若 号 == 802 则 关联 其 打开设置 (A 其 查 'window'). 然
    若 号 == 803 则
        若 (界面弹窗 (A 其 查 'window') (本地 其 文本 'dialog.unregister') (本地 其 文本 'dialog.unregister.title') 292) == 6 则 关联 其 注销. 提示 (本地 其 文本 'association.unregistered'). 然
    然
    若 号 == 804 则 提示 (本地 其 格式 'association.status' ([(本地 其 文本 ('association.state.'+(关联 其 查询状态)))])). 然
    若 号 == 601 则 提示 (本地 其 格式 'about.body' (['0.1.8'])). 然
    刷新.
    得 空.
法
算 近期菜单 子:
    窗 其 菜单项 子 2048 0 ''.
    窗 其 菜单项 子 3 0 (本地 其 文本 'recent.heading').
    近们 取 A 其 查 'recentItems'.
    若 (近们 其 量) == 0 则 窗 其 菜单项 子 3 0 (本地 其 文本 'recent.empty'). 然
    近位 取 0.
    循 近们 其 量 次
        窗 其 菜单项 子 0 (1200+近位) (近策 其 标签 近们[近位][0]).
        近位 取 近位+1.
    环
    清旗 取 0. 若 (近们 其 量) == 0 则 清旗 取 3. 然
    窗 其 菜单项 子 清旗 1210 (本地 其 文本 'recent.clear').
    得 空.
法
算 菜单:
    # Parallel primitive arrays keep the pinned compiler's ABI analysis bounded.
    组键们 取 ['menu.file', 'menu.edit', 'menu.search', 'menu.encoding', 'menu.language', 'menu.view', 'menu.settings', 'menu.ui_language', 'menu.help'].
    组量们 取 [11, 6, 4, 6, 5, 7, 5, 8, 1].
    号们 取 [101, 102, 108, 109, 103, 104, 105, 111, 112, 113, 106, 201, 202, 203, 204, 205, 206, 301, 302, 303, 308, 401, 402, 403, 404, 405, 406, 701, 702, 703, 704, 705, 501, 502, 503, 504, 505, 506, 507, 801, 802, 803, 804, 805, 850, 851, 852, 853, 854, 855, 856, 857, 601].
    键们 取 ['command.new', 'command.open', 'command.open_windows1252', 'command.open_gbk', 'command.save', 'command.save_as', 'command.close_tab', 'command.previous_tab', 'command.next_tab', 'command.open_pending_shell', 'command.exit', 'command.undo', 'command.redo', 'command.cut', 'command.copy', 'command.paste', 'command.select_all', 'command.find', 'command.replace', 'command.find_next', 'command.find_previous', 'command.save_utf8', 'command.save_utf8_bom', 'command.save_utf16le', 'command.save_utf16be', 'command.save_windows1252', 'command.save_gbk', 'command.language_plain', 'command.language_cpp', 'command.language_json', 'command.language_ru', 'command.language_markdown', 'command.toggle_wrap', 'command.zoom_in', 'command.zoom_out', 'command.zoom_reset', 'command.fold_all', 'command.unfold_all', 'command.toggle_markdown_folds', 'command.register_association', 'command.default_apps', 'command.unregister_association', 'command.registration_status', 'command.single_instance', 'language.system', 'language.en', 'language.zh_cn', 'language.ja', 'language.ko', 'language.es', 'language.ru', 'language.it', 'command.about'].
    主 取 窗 其 成功 ((窗 其 CreateMenu) 其 调用 []) 'CreateMenu'.
    子 取 空.
    试
        组位 取 0.
        位 取 0.
        循 组键们 其 量 次
            子 取 窗 其 成功 ((窗 其 CreatePopupMenu) 其 调用 []) 'CreatePopupMenu'.
            循 组量们[组位] 次
                号 取 号们[位].
                标记 取 0.
                若 号 == 805 且 (A 其 查 'singlePreference') 则 标记 取 8. 然
                若 号 == 113 且 ((A 其 查 'handoffPending') 其 量) == 0 则 标记 取 3. 然
                若 号 >= 850 且 号 <= 857 则
                    选项 取 ['system','en','zh-CN','ja','ko','es','ru','it'][号-850].
                    若 选项 == (A 其 查 'uiPreference') 则 标记 取 8. 然
                然
                窗 其 菜单项 子 标记 号 (本地 其 文本 键们[位]).
                位 取 位+1.
            环
            若 组位 == 0 则 近期菜单 子. 然
            窗 其 菜单项 主 16 ((窗 其 UP) 其 重释 子) (本地 其 文本 组键们[组位]).
            # The root now owns this submenu; cleanup must not free it twice.
            子 取 空.
            组位 取 组位+1.
        环
        旧 取 窗 其 结果 ((窗 其 GetMenu) 其 调用 [(A 其 查 'window')]).
        窗 其 成功 ((窗 其 SetMenu) 其 调用 (参 其 菜单参数 A 主)) 'SetMenu'.
    救 原因
        若 子 != 空 则 窗 其 结果 ((窗 其 DestroyMenu) 其 调用 [子]). 然
        窗 其 结果 ((窗 其 DestroyMenu) 其 调用 [主]).
        卒 原因.
    终
    若 非 (旧 其 为空) 则 窗 其 结果 ((窗 其 DestroyMenu) 其 调用 [旧]). 然
    窗 其 结果 ((窗 其 DrawMenuBar) 其 调用 [(A 其 查 'window')]).
    得 空.
法
算 消息处理 柄, 号值, 宽参, 长参:
    号 取 号值 其 数.
    若 号 == 129 则 A 其 增 'window' 柄. 然
    若 号 == 36 则
        矩 取 (窗 其 MINMAXINFO) 其 新建.
        指 取 (窗 其 PTR) 其 重释 长参.
        窗 其 结果 ((窗 其 RtlMoveMemory) 其 调用 [矩,指,((窗 其 MINMAXINFO) 其 大小)]).
        矩 其 写 'minTrackX' 640.
        矩 其 写 'minTrackY' 400.
        窗 其 结果 ((窗 其 RtlMoveMemory) 其 调用 [指,矩,((窗 其 MINMAXINFO) 其 大小)]).
        矩 其 关闭.
        得 0.
    然
    若 号 == 2 则
        A 其 增 'ready' 假.
        停止语法.
        # This single main window is being destroyed; no queued slot may carry
        # over to another HWND, even if an embedding later initializes again.
        A 其 增 'syntaxQueued' 0.
        窗 其 结果 ((窗 其 PostQuitMessage) 其 调用 [0]).
        得 0.
    然
    若 A 其 查 'ready' 则
        试
            若 号 == 74 则
                若 (A 其 查 'singleState') == 空 或 (A 其 查 'handoffReject') 或 (A 其 查 'cancelRequested') 或 (A 其 查 'modalDepth') > 0 或 (A 其 查 'closeIndex') >= 0 或 (A 其 查 'closeRun') != 空 或 (A 其 查 'tabMenuOpen') 则 得 2. 然
                # Copy/validate the complete request before queuing; no pointer survives.
                试
                    交路 取 单例 其 接收 (A 其 查 'singleState') ((窗 其 PTR) 其 重释 宽参) ((窗 其 PTR) 其 重释 长参).
                    # BUSY3 proves zero admission only after full sender/packet validation.
                    若 (交路 其 量) > 0 且 (交接待收尾) 则 得 3. 然
                    若 (交路 其 量) > 0 则 接收入队 交路. 然
                救 原因
                    得 2.
                终
                单例 其 激活 (A 其 查 'window').
                得 1.
            然
            若 号 == 17 则 得 关机会话. 然
            若 号 == 275 且 (宽参 其 数) == 901 则 工作时钟. 得 0. 然
            若 号 == 275 且 (宽参 其 数) == 902 则 语法时钟. 得 0. 然
            若 号 == 33671 则
                若 (柄 其 句) == ((A 其 查 'window') 其 句) 且 (宽参 其 位段 0 32) == 0 且 (宽参 其 位段 32 32) == 0 且 (长参 其 位段 0 32) == 0 且 (长参 其 位段 32 32) == 0 则 诊断语法. 然
                得 0.
            然
            若 号 == 33670 则
                # Do not convert an arbitrary external uintptr to a Ru number.
                若 (宽参 其 位段 32 32) == 0 且 (长参 其 位段 0 32) == 0 且 (长参 其 位段 32 32) == 0 则
                    语法消息 柄 (宽参 其 位段 0 32).
                然
                得 0.
            然
            若 号 == 563 则
                路们 取 拖放 其 接收 ((窗 其 PTR) 其 重释 宽参).
                入队 路们 0.
                得 0.
            然
            若 号 == 5 则 布局. 得 0. 然
            若 号 == 16 则 关程序. 得 0. 然
            若 号 == 273 且 (宽参 其 位段 16 16) == 0 则
                命令 (宽参 其 位段 0 16).
                得 0.
            然
            若 号 == 78 则
                头 取 (窗 其 NMHDR) 其 新建.
                窗 其 结果 ((窗 其 RtlMoveMemory) 其 调用 [头,((窗 其 PTR) 其 重释 长参),(窗 其 NMHDR) 其 大小]).
                来源 取 头 其 读 'hwndFrom'.
                码 取 (头 其 读 'code') 其 数.
                头 其 关闭.
                文档 取 所属文档 来源.
                若 文档 != 空 且 (码 == 2008 或 码 == 2000 或 码 == 2010) 则
                    修改 取 修改头 其 新建.
                    窗 其 结果 ((窗 其 RtlMoveMemory) 其 调用 [修改,((窗 其 PTR) 其 重释 长参),(修改头 其 大小)]).
                    位置 取 (修改 其 读 'position') 其 数.
                    类型 取 修改 其 读 'modificationType'.
                    长度 取 (修改 其 读 'length') 其 数.
                    行变 取 (修改 其 读 'linesAdded') 其 数.
                    边栏 取 (修改 其 读 'margin') 其 数.
                    修改 其 关闭.
                    若 码 == 2008 则
                        若 (类型 其 位段 0 2) != 0 则 A 其 增 'syntaxTextNotifications' ((A 其 查 'syntaxTextNotifications')+1). 然
                        若 (类型 其 位段 2 1) != 0 则 A 其 增 'syntaxStyleNotifications' ((A 其 查 'syntaxStyleNotifications')+1). 然
                        若 (类型 其 位段 3 1) != 0 则 A 其 增 'syntaxFoldNotifications' ((A 其 查 'syntaxFoldNotifications')+1). 然
                    然
                    若 码 == 2008 且 (类型 其 位段 0 2) != 0 则
                        文档 其 增 'revision' ((文档 其 查 'revision')+1).
                        语 其 变化 来源 位置 长度 行变 (类型 其 数).
                        安排语法.
                    然
                    若 码 == 2000 则 语 其 请求 来源 位置. 安排语法. 然
                    若 码 == 2010 且 边栏 == 2 且 非 (A 其 查 'busy') 则 语 其 折叠 来源 位置. 然
                然
                若 (A 其 查 'busy') 或 (A 其 查 'closeRun') != 空 或 (A 其 查 'tabMenuOpen') 则 得 0. 然
                若 (来源 其 句) == ((A 其 查 'tabs') 其 句) 且 码 == 4294967291 则 页右键. 得 0. 然
                若 (来源 其 句) == ((A 其 查 'tabs') 其 句) 且 码 == 4294966745 则
                    切页 ((窗 其 发送 (A 其 查 'tabs') 4875 0 0) 其 数).
                然
                若 (A 其 查 'active') >= 0 且 (来源 其 句) == (编辑柄 其 句) 则
                    若 码 == 2002 或 码 == 2003 或 码 == 2007 则 刷新. 然
                然
                得 0.
            然
        救 原因
            错误提示 原因.
            得 0.
        终
    然
    得 窗 其 结果 ((窗 其 DefWindowProcW) 其 调用 [柄,号值,宽参,长参]).
法
算 快捷 消息:
    号 取 (消息 其 读 'message') 其 数.
    若 号 != 256 则 得 假. 然
    键 取 (消息 其 读 'wParam') 其 数.
    若 A 其 查 'busy' 则
        若 键 == 27 则 A 其 增 'cancelRequested' 真. 然
        得 真.
    然
    Ctrl 取 ((窗 其 结果 ((窗 其 GetKeyState) 其 调用 [17])) 其 位段 15 1) == 1.
    Shift 取 ((窗 其 结果 ((窗 其 GetKeyState) 其 调用 [16])) 其 位段 15 1) == 1.
    Alt 取 ((窗 其 结果 ((窗 其 GetKeyState) 其 调用 [18])) 其 位段 15 1) == 1.
    号令 取 键规 其 命令号 键 Ctrl Shift Alt (A 其 查 'search').
    若 号令 == 0 则 得 假. 然
    试
        命令 号令.
    救 原因
        错误提示 原因.
    终
    得 真.
法

算 初始化 参数 为 句 阵, 显示 为 事实:
    # Every dependency is loaded before WNDPROC can run.
    设 取 偏好 其 载入偏好.
    A 其 增 'uiPreference' 设['value'].
    若 设['value'] == '' 则 A 其 增 'uiPreference' 'system'. 然
    若 设['value'] != '' 且 设['value'] != 'system' 且 非 (本地 其 有语言 设['value']) 则 A 其 增 'uiPreference' 'en'. 然
    本地 其 设置 (偏好 其 决定 设['value'] (偏好 其 系统语言)).
    # Hidden native fixtures must not acquire new per-user persistence effects.
    # Explicit test readers/writers still permit isolated registry verification.
    若 (A 其 查 'recentReader') == 空 则
        若 显示 则 A 其 增 'recentReader' (算 最近 其 载入).
        另 A 其 增 'recentReader' (算 空最近). 然
    然
    若 (A 其 查 'recentWriter') == 空 则
        若 显示 则 A 其 增 'recentWriter' (算 最近 其 保存).
        另 A 其 增 'recentWriter' (算 不存最近). 然
    然
    试
        取近函数 取 A 其 查 'recentReader'.
        近果 取 取近函数().
        A 其 增 'recentItems' 近果['items'].
        A 其 增 'recentError' 近果['error'].
    救 原因
        A 其 增 'recentItems' ([]).
        A 其 增 'recentError' 13.
    终
    A 其 增 'visible' 显示.
    A 其 增 'confirmLarge' (算 询大文件).
    A 其 增 'confirmClose' (算 询问关闭).
    A 其 增 'chooseSavePath' (算 选保存路径).
    语 其 初始化.
    库路径 取 (窗 其 目录)+'Scintilla.dll'.
    路径存 取 密 其 UTF16 库路径.
    预载成果 取 (窗 其 LoadLibraryExW) 其 调用 [路径存,空,2304].
    路径存 其 关闭.
    预载 取 预载成果 其 值.
    若 预载 其 为空 则
        卒 (本地 其 格式 'error.main.scintilla_missing' ([((预载成果 其 错误码) 为 句)])).
    然
    原生编辑库 取 密 其 动态库 库路径.
    显 '[startup] Scintilla loaded'.
    窗 其 结果 ((窗 其 FreeLibrary) 其 调用 [预载]).
    实例 取 窗 其 成功 ((窗 其 GetModuleHandleW) 其 调用 [空]) 'GetModuleHandleW'.
    A 其 增 'instance' 实例.
    控初始化 取 (窗 其 INITCONTROLS) 其 新建.
    控初始化 其 写 'size' ((窗 其 INITCONTROLS) 其 大小).
    控初始化 其 写 'classes' 8.
    窗 其 成功 ((窗 其 InitCommonControlsEx) 其 调用 [控初始化]) 'InitCommonControlsEx'.
    控初始化 其 关闭.
    类名 取 密 其 UTF16 'RuNotepad.Main.0.1'.
    标题 取 密 其 UTF16 'ru_notepad'.
    回调 取 密 其 回调 (窗 其 WNDPROC) (算 消息处理) 0.
    回调 其 失败时 (窗 其 PostQuitMessage) ([1]).
    类 取 (窗 其 WNDCLASS) 其 新建.
    类 其 写 'size' ((窗 其 WNDCLASS) 其 大小).
    类 其 写 'proc' (回调 其 地址).
    类 其 写 'instance' 实例.
    类 其 写 'icon' (窗 其 结果 ((窗 其 LoadImageW) 其 调用 [实例,((窗 其 PTR) 其 值 1),1,32,32,32768])).
    类 其 写 'smallIcon' (窗 其 结果 ((窗 其 LoadImageW) 其 调用 [实例,((窗 其 PTR) 其 值 1),1,16,16,32768])).
    类 其 写 'name' (类名 其 地址).
    类 其 写 'cursor' (窗 其 结果 ((窗 其 LoadCursorW) 其 调用 [空,((窗 其 PTR) 其 值 32512)])).
    类 其 写 'background' (窗 其 结果 ((窗 其 GetSysColorBrush) 其 调用 [15])).
    窗 其 成功 ((窗 其 RegisterClassExW) 其 调用 [类]) 'RegisterClassExW'.
    类 其 关闭.
    显 '[startup] window class registered'.
    主窗 取 窗 其 成功 ((窗 其 CreateWindowExW) 其 调用 [0,类名,标题,13565952,-2147483648,-2147483648,1120,760,空,空,实例,空]) 'CreateWindowExW(main)'.
    标题 其 关闭.
    A 其 增 'window' 主窗.
    显 '[startup] main window created'.
    A 其 增 'tabs' (窗 其 控制 主窗 实例 'SysTabControl32' '' 1342242816 10).
    A 其 增 'status' (窗 其 控制 主窗 实例 'STATIC' '' 1342177280 11).
    A 其 增 'cancel' (窗 其 控制 主窗 实例 'BUTTON' '' 1073807360 901).
    A 其 增 'find' (窗 其 控制 主窗 实例 'EDIT' '' 1082196096 310).
    A 其 增 'replace' (窗 其 控制 主窗 实例 'EDIT' '' 1082196096 311).
    A 其 增 'case' (窗 其 控制 主窗 实例 'BUTTON' '' 1073807363 306).
    窗 其 发送 (A 其 查 'case') 241 1 0.
    A 其 增 'whole' (窗 其 控制 主窗 实例 'BUTTON' '' 1073807363 309).
    A 其 增 'searchWrap' (窗 其 控制 主窗 实例 'BUTTON' '' 1073807363 312).
    窗 其 发送 (A 其 查 'searchWrap') 241 1 0.
    A 其 增 'previous' (窗 其 控制 主窗 实例 'BUTTON' '' 1073807360 308).
    A 其 增 'next' (窗 其 控制 主窗 实例 'BUTTON' '' 1073807360 303).
    A 其 增 'one' (窗 其 控制 主窗 实例 'BUTTON' '' 1073807360 304).
    A 其 增 'all' (窗 其 控制 主窗 实例 'BUTTON' '' 1073807360 305).
    A 其 增 'hide' (窗 其 控制 主窗 实例 'BUTTON' '' 1073807360 307).
    显 '[startup] controls created'.
    界面文字.
    菜单.
    显 '[startup] menu installed'.
    A 其 增 'ready' 真.
    新页 '' '' 65001 假 ''.
    显 '[startup] initial document ready'.
    拖放 其 启用 主窗.
    若 显示 且 非 (A 其 查 'singleDeferredShow') 则
        窗 其 结果 ((窗 其 ShowWindow) 其 调用 [主窗,5]).
        窗 其 结果 ((窗 其 UpdateWindow) 其 调用 [主窗]).
        显 '[startup] main window shown'.
        报语法警告.
        若 设['error'] != 0 则 错误提示 (本地 其 格式 'settings.read_failure' ([设['error']])). 然
    然
    # Unicode argv, dialogs and HDROP all enter the same bounded queue.
    若 (参数 其 量) > 0 则
        试 入队 参数 0. 救 原因 错误提示 原因. 终
    然
    A 其 增 'className' 类名.
    A 其 增 'callback' 回调.
    A 其 增 'scintillaLibrary' 原生编辑库.
    得 主窗.
法

算 打开待确认:
    路们 取 A 其 查 'handoffPending'.
    若 (路们 其 量) == 0 则 得 假. 然
    若 (界面弹窗 (A 其 查 'window') (本地 其 文本 'instance.uncertain') (本地 其 文本 'instance.title') 308) != 6 则 得 假. 然
    入队 路们 0.
    A 其 增 'handoffPending' ([]).
    菜单.
    得 真.
法
算 元初 参数 为 句 阵:
    显 '[startup] Ru application modules loaded'.
    强制多窗 取 假.
    循
        若 (参数 其 量) == 0 则 破. 然
        若 参数[0] == '--markdown-phase-diagnostics' 则
            A 其 增 'markdownDiagnosticEnabled' 真.
            参数 取 参数[1:].
        另
            若 参数[0] == '--multi-instance' 则
                强制多窗 取 真.
                参数 取 参数[1:].
            另
                破.
            然
        然
    环
    # Freeze argv paths in the launching process's cwd, including uncertain delivery.
    绝路们 取 []. 参位 取 0.
    试
        循 参数 其 量 次
            若 参数[参位] != '' 则 绝路们 其 增 (件编 其 绝对路径 参数[参位]). 然
            参位 取 参位+1.
        环
    救 原因
        界面弹窗 空 (本地 其 格式 'error.body' ([原因])) (本地 其 文本 'startup.title') 16.
        得 1.
    终
    参数 取 绝路们.
    单偏 取 单设 其 载入偏好.
    A 其 增 'singlePreference' 单偏['enabled'].
    单态 取 单例 其 准备 (单偏['enabled'] 且 非 强制多窗).
    A 其 增 'singleState' 单态.
    A 其 增 'singleDeferredShow' 真.
    试
        初始化 ([]) 真.
        交果 取 单例 其 转交 单态 (A 其 查 'window') 参数.
        若 交果 == 'accepted' 则
            # No secondary window was shown. Only a confirmed receiver owns argv.
            关程原 取 A 其 查 'docs'. 交位 取 0.
            循 关程原 其 量 次
                语 其 遗忘 (关程原[交位] 其 查 'editor').
                交位 取 交位+1.
            环
            窗 其 成功 ((窗 其 DestroyWindow) 其 调用 [(A 其 查 'window')]) 'DestroyWindow(handoff)'.
            窗 其 成功 ((窗 其 UnregisterClassW) 其 调用 (参 其 注销类参数 A)) 'UnregisterClassW'.
            (A 其 查 'className') 其 关闭.
            (A 其 查 'callback') 其 关闭.
            单例 其 关闭 单态.
            得 0.
        然
        # Admit own argv before publishing/showing, so reentrant external opens cannot displace it.
        若 交果 == 'local' 且 (参数 其 量) > 0 则 入队 参数 0. 然
        若 单态['owner'] 且 非 (单例 其 发布 单态 (A 其 查 'window')) 则 单态 其 增 'error' 'Single-instance window publication failed.'. 然
        A 其 增 'singleDeferredShow' 假.
        窗 其 结果 ((窗 其 ShowWindow) 其 调用 [(A 其 查 'window'),5]).
        窗 其 结果 ((窗 其 UpdateWindow) 其 调用 [(A 其 查 'window')]).
        显 '[startup] main window shown'.
        报语法警告.
        若 单偏['error'] != 0 则 错误提示 (本地 其 格式 'instance.read_failed' ([单偏['error']])). 然
        若 单态['error'] != '' 则 错误提示 (本地 其 格式 'instance.failed' ([单态['error']])). 然
        若 交果 == 'uncertain' 则
            A 其 增 'handoffPending' 参数.
            菜单.
            打开待确认.
        然
    救 原因
        单例 其 关闭 单态.
        显 '[startup] initialization failed'.
        界面弹窗 空 (本地 其 格式 'error.body' ([原因])) (本地 其 文本 'startup.title') 16.
        得 1.
    终
    消息 取 (窗 其 MSG) 其 新建.
    退出码 取 0.
    试
        循
            成果 取 (窗 其 GetMessageW) 其 调用 [消息,空,0,0].
            码 取 (窗 其 结果 成果) 其 数.
            若 码 == -1 则 卒 (本地 其 格式 'error.native' (['GetMessageW',((成果 其 错误码) 为 句)])). 然
            若 码 == 0 则
                退出码 取 (消息 其 读 'wParam') 其 数.
                若 退出码 != 0 则 卒 (本地 其 文本 'error.main.callback_stopped'). 然
                破.
            然
            若 非 (快捷 消息) 则
                窗 其 结果 ((窗 其 TranslateMessage) 其 调用 [消息]).
                窗 其 结果 ((窗 其 DispatchMessageW) 其 调用 [消息]).
            然
        环
        消息 其 关闭.
        窗 其 成功 ((窗 其 UnregisterClassW) 其 调用 (参 其 注销类参数 A)) 'UnregisterClassW'.
        (A 其 查 'className') 其 关闭.
        (A 其 查 'callback') 其 关闭.
        单例 其 关闭 单态.
    救 原因
        单例 其 关闭 单态.
        # A native callback failure is contained, but application state cannot
        # be assumed resumable. Never silently overwrite files during recovery.
        A 其 增 'ready' 假.
        界面弹窗 空 (本地 其 格式 'fatal.body' ([原因])) (本地 其 文本 'fatal.title') 16.
        得 1.
    终
    得 退出码.
法
