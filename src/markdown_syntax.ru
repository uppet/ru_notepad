# Stage A: Lexilla owns Markdown byte styles; Ru owns only heading fold metadata.
# Rebuilt independently in 2026-10-18. Edits restart at BOF. There are no whole-file
# line arrays/checkpoints: one <=1024-byte UTF-8 chunk, one <=64-range policy batch,
# and one range cursor. A publisher touches at most 64 lines before returning.
# The 8 ms timer budget is admission control, NOT preemption of a native call.
# FoldAll/ShowLines may synchronously traverse native document state. In particular
# stop/error visibility recovery cannot promise a hard 8 ms latency bound.
# OWNER CONTRACT: call 遗忘 before SETDOCPOINTER/DestroyWindow. A production
# subclass must not swap documents while forwarding a mutating Scintilla message.
本地 取 外言 'i18n.ru'.
密 取 外言 '如:密'.
窗 取 外言 'win32.ru'.
策 取 外言 'markdown_policy.ru'.
_编辑们 取 {}.
_序号 取 [0].
_身份 取 [0].
# Internal OWNER capability, not detection/enumeration of arbitrary comctl hooks.
# Only main's exclusive private document + known file_drop subclass may opt in.
# Revoke BEFORE adding any other hook, sharing/replacing a document or destroying
# its HWND. Same-document edits retain this capability but invalidate scan state.
# Never store a borrowed Scintilla pointer here or in the 33-field scan state.
_直属们 取 {}.
_权序 取 [0].
_直接策略 取 {'enabled':真,'route':'bulk'}. # Source-only paired fixture control, no UI setting.
_直库态 取 {'ready':假,'library':空,'module':空}.
_批库态 取 {'ready':假,'library':空,'abi':0}.
_批统计们 取 {}.
_GetProcAddress 取 (窗 其 内核) 其 绑定 'GetProcAddress' (密 其 签名 (窗 其 PTR) ([(窗 其 PTR),(窗 其 PTR)]) 'win64').
_GetParent 取 (窗 其 用户) 其 绑定 'GetParent' (密 其 签名 (窗 其 PTR) ([(窗 其 PTR)]) 'win64').
# The exact absolute-path DLL and named public export are preflighted before the
# typed binding. This strong module-lifetime library root outlives every segment.
_直路径 取 (窗 其 目录)+'Scintilla.dll'.
_直路径存 取 密 其 UTF16 _直路径.
_直预载 取 窗 其 结果 ((窗 其 LoadLibraryExW) 其 调用 [_直路径存,空,2304]).
_直路径存 其 关闭.
若 非 (_直预载 其 为空) 则
    _直名 取 密 其 UTF8 'Scintilla_DirectFunction'.
    _直出口 取 窗 其 结果 (_GetProcAddress 其 调用 [_直预载,_直名]).
    _直名 其 关闭.
    若 非 (_直出口 其 为空) 则
        _直库 取 密 其 动态库 _直路径.
        _DirectFunction 取 _直库 其 绑定 'Scintilla_DirectFunction' (密 其 签名 (窗 其 IP) ([(窗 其 PTR),(窗 其 U),(窗 其 UP),(窗 其 IP)]) 'win64').
        _直库态 其 增 'library' _直库.
        _直库态 其 增 'module' _直预载.
        _直库态 其 增 'ready' 真.
    然
    窗 其 结果 ((窗 其 FreeLibrary) 其 调用 [_直预载]).
然
# Optional app-private bounded helper: preflight BOTH exports before binding.
# An absent/old helper selects ordinary messages, never the per-line control.
_批路径 取 (窗 其 目录)+'RuSyntax.dll'.
_批路径存 取 密 其 UTF16 _批路径.
_批预载 取 窗 其 结果 ((窗 其 LoadLibraryExW) 其 调用 [_批路径存,空,2304]).
_批路径存 其 关闭.
若 非 (_批预载 其 为空) 则
    _批版本名 取 密 其 UTF8 'ru_markdown_fold_abi'.
    _批应用名 取 密 其 UTF8 'ru_markdown_fold_apply_v1'.
    _批版本口 取 窗 其 结果 (_GetProcAddress 其 调用 [_批预载,_批版本名]).
    _批应用口 取 窗 其 结果 (_GetProcAddress 其 调用 [_批预载,_批应用名]).
    _批版本名 其 关闭. _批应用名 其 关闭.
    若 非 (_批版本口 其 为空) 且 非 (_批应用口 其 为空) 则
        _批库 取 密 其 动态库 _批路径.
        _FoldABI 取 _批库 其 绑定 'ru_markdown_fold_abi' (密 其 签名 (窗 其 U) ([]) 'win64').
        _批版本 取 (窗 其 结果 (_FoldABI 其 调用 [])) 其 数.
        _批库态 其 增 'library' _批库.
        _批库态 其 增 'abi' _批版本.
        若 _批版本 == 65536 则
            _FoldApply 取 _批库 其 绑定 'ru_markdown_fold_apply_v1' (密 其 签名 (窗 其 U) ([(窗 其 PTR),(窗 其 PTR),(窗 其 PTR),(窗 其 PTR),(窗 其 PTR),(窗 其 IP),(窗 其 PTR),(窗 其 U),(窗 其 PTR),(窗 其 U)]) 'win64').
            _批库态 其 增 'ready' 真.
        然
    然
    窗 其 结果 ((窗 其 FreeLibrary) 其 调用 [_批预载]).
然
_批范围型 取 密 其 结构 [['start',窗 其 U],['count',窗 其 U],['depth',窗 其 U],['header',窗 其 U]].
_批字段 取 [['abi',窗 其 U],['rangeCount',窗 其 U],['rangeIndex',窗 其 U],['rangeOffset',窗 其 U],['expectedLines',窗 其 U],['maxLines',窗 其 U],['reserved0',窗 其 U],['reserved1',窗 其 U]].
_批范围名 取 []. _批字段位 取 0.
循 64 次
    _批字段名 取 'range'+(_批字段位 为 句).
    _批范围名 其 增 _批字段名.
    _批字段 其 增 [_批字段名,_批范围型].
    _批字段位 取 _批字段位+1.
环
# Fixed descriptors only; no plan/result buffer or borrowed pointer is retained.
_批计划型 取 密 其 结构 _批字段.
_批果型 取 密 其 结构 [['status',窗 其 U],['attempted',窗 其 U],['completed',窗 其 U],['nextIndex',窗 其 U],['nextOffset',窗 其 U],['scintillaStatus',窗 其 U],['reserved0',窗 其 U],['reserved1',窗 其 U]].
_范围型 取 密 其 结构 [['start',窗 其 IP],['end',窗 其 IP],['text',窗 其 PTR]].
_计数型 取 密 其 结构 [['value',密 其 i64]].
_GetCurrentThreadId 取 (窗 其 内核) 其 绑定 'GetCurrentThreadId' (密 其 签名 (窗 其 U) ([]) 'win64').
_GetWindowThreadProcessId 取 (窗 其 用户) 其 绑定 'GetWindowThreadProcessId' (密 其 签名 (窗 其 U) ([(窗 其 PTR),(窗 其 PTR)]) 'win64').
_IsWindow 取 (窗 其 用户) 其 绑定 'IsWindow' (密 其 签名 (窗 其 I) ([(窗 其 PTR)]) 'win64').
_QueryPerformanceCounter 取 (窗 其 内核) 其 绑定 'QueryPerformanceCounter' (密 其 签名 (窗 其 I) ([(窗 其 PTR)]) 'win64').
_QueryPerformanceFrequency 取 (窗 其 内核) 其 绑定 'QueryPerformanceFrequency' (密 其 签名 (窗 其 I) ([(窗 其 PTR)]) 'win64').
_频存 取 _计数型 其 新建.
窗 其 成功 (_QueryPerformanceFrequency 其 调用 [_频存]) 'QueryPerformanceFrequency'.
_频率 取 (_频存 其 读 'value') 其 数.
_频存 其 关闭.
_时存 取 _计数型 其 新建.

算 时刻:
    窗 其 成功 (_QueryPerformanceCounter 其 调用 [_时存]) 'QueryPerformanceCounter'.
    数值 取 _时存 其 读 'value'.
    得 ((数值 其 位段 32 32)*4294967296+(数值 其 位段 0 32))*1000/_频率.
法
算 _线程:
    得 (窗 其 结果 (_GetCurrentThreadId 其 调用 [])) 其 句.
法
算 _同线程 柄:
    线程 取 窗 其 结果 (_GetWindowThreadProcessId 其 调用 [柄,空]).
    得 非 (线程 其 为空) 且 线程 其 句 == (_线程).
法
算 _本态 柄 态:
    若 态 == 空 或 非 态['alive'] 或 态['hwnd'] != 柄 其 句 则 得 假. 然
    现 取 _编辑们 其 查 (柄 其 句).
    得 现 != 空 且 现['identity'] == 态['identity'] 且 现['generation'] == 态['generation'] 且 现['revision'] == 态['revision'] 且 现['document'] == 态['document'] 且 现['thread'] == 态['thread'].
法
算 _须本态 柄 态:
    # Win32 identity/thread queries do not send a window message. Foreign HWNDs
    # are rejected before the first Scintilla query or pointer is ever obtained.
    若 非 (_本态 柄 态) 或 态['thread'] != (_线程) 或 非 (_同线程 柄) 或 (窗 其 结果 (_IsWindow 其 调用 [柄])) 其 为空 则 卒 'Stale Markdown owner.'. 然
    得 空.
法
算 _护 柄 态:
    _须本态 柄 态.
    文档 取 (窗 其 发送 柄 2357 0 0) 其 句.
    _须本态 柄 态.
    若 文档 != 态['document'] 则 卒 'Stale Markdown document.'. 然
    长 取 (窗 其 发送 柄 2183 0 0) 其 数.
    _须本态 柄 态.
    若 长 != 态['length'] 则 卒 'Markdown text changed without invalidation.'. 然
    得 空.
法
算 _讯 柄 态 号 宽 长:
    _护 柄 态.
    果 取 窗 其 发送 柄 号 宽 长.
    _护 柄 态.
    得 果.
法
算 _检查 柄 态:
    若 (_讯 柄 态 2383 0 0) 其 数 != 0 则 卒 'Scintilla has an outstanding error or warning.'. 然
    得 空.
法
算 _尺寸 柄 态:
    # Initialization and recovery alone may refresh length. They may NEVER adopt
    # a different document pointer after the state's first document is captured.
    _须本态 柄 态.
    文档 取 (窗 其 发送 柄 2357 0 0) 其 句.
    _须本态 柄 态.
    若 态['document'] != '' 且 态['document'] != 文档 则 卒 'Replaced Markdown document.'. 然
    态 其 增 'document' 文档.
    长 取 (窗 其 发送 柄 2183 0 0) 其 数.
    _须本态 柄 态.
    态 其 增 'length' 长.
    _护 柄 态.
    态 其 增 'lines' ((_讯 柄 态 2154 0 0) 其 数).
    得 空.
法
算 _建态 柄 代 为 数 修 为 数 文档 为 句:
    _身份[0] 取 _身份[0]+1.
    得 {'identity':_身份[0],'generation':代,'revision':修,'hwnd':(柄 其 句),'thread':(_线程),'document':文档,'length':-1,'lines':0,'alive':真,'language':'markdown','foldEnabled':真,'registered':假,'warning':'','warningArgs':[],'warningRecovery':[],'pending':真,'inTick':假,'phase':'prepare','policy':(策 其 新状态),'feed':0,'readEnd':0,'chunk':'','ranges':[],'rangeIndex':0,'rangeOffset':0,'eof':假,'chunks':0,'readBytes':0,'published':0,'maxRead':0,'maxPublish':0,'maxRanges':0,'maxTickMs':0,'maxChunkMs':0,'restart':0}.
法
# One diagnostic record per live HWND/current identity, outside the 33 scan
# fields. ownedBufferBytes is peak per-call owned capacity, not live bytes.
# Old interrupted cleanup may never remove a replacement's counters.
算 _统计 柄 态:
    若 非 (_本态 柄 态) 则 得 空. 然
    计 取 _批统计们 其 查 (柄 其 句).
    若 计 == 空 或 计['identity'] != 态['identity'] 则
        计 取 {'identity':态['identity'],'bulkCalls':0,'bulkLines':0,'fallbackBatches':0,'directCalls':0,'directLines':0,'maxPlanBytes':0,'bulkUs':0,'ownedBufferBytes':0,'bulkMetricsValid':真}.
        _批统计们 其 增 (柄 其 句) 计.
    然
    得 计.
法
算 _统计时刻 计:
    值 取 0.
    试 值 取 时刻. 救 原因 计 其 增 'bulkMetricsValid' 假. 终
    得 值.
法
算 _统计耗时 计 起时 为 数:
    末时 取 _统计时刻 计.
    若 起时 > 0 且 末时 >= 起时 则
        微秒 取 (末时-起时)*1000+0.5.
        微秒 取 微秒-(微秒%1).
        计 其 增 'bulkUs' (计['bulkUs']+微秒).
    另
        计 其 增 'bulkMetricsValid' 假.
    然
    得 空.
法
算 _丢弃 柄 态:
    若 态 == 空 则 得 空. 然
    计 取 _批统计们 其 查 (柄 其 句).
    若 计 != 空 且 计['identity'] == 态['identity'] 则 _批统计们 其 除 (柄 其 句). 然
    若 _本态 柄 态 则 _编辑们 其 除 (柄 其 句). 然
    态 其 增 'alive' 假.
    态 其 增 'pending' 假.
    态 其 增 'policy' 空.
    态 其 增 'ranges' ([]).
    态 其 增 'chunk' ''.
    得 空.
法
算 撤销直属 柄:
    _直属们 其 除 (柄 其 句).
    得 空.
法
算 遗忘 柄:
    撤销直属 柄.
    # Invalidate first and do not send to a possibly closing/reused HWND.
    _丢弃 柄 (_编辑们 其 查 (柄 其 句)).
    得 空.
法
算 _全显 柄 态:
    # Native global expansion is intentionally explicit and non-preemptive.
    # Disable change/click automation before expanding old numeric levels.
    _讯 柄 态 2663 0 0.
    _讯 柄 态 2662 1 0.
    若 态['lines'] > 0 则 _讯 柄 态 2226 0 (态['lines']-1). 然
    得 空.
法
算 _可见完成 柄 态:
    # Visibility is a separate owned task, not a policy scan. Existing native
    # warning/error status must not turn this cleanup into an infinite retry.
    _尺寸 柄 态.
    _全显 柄 态.
    _讯 柄 态 2242 2 0.
    _护 柄 态.
    态 其 增 'phase' 'disabled'.
    态 其 增 'pending' 假.
    得 空.
法
算 停用 柄:
    撤销直属 柄.
    旧 取 _编辑们 其 查 (柄 其 句).
    若 旧 == 空 则 得 空. 然
    # A fresh tombstone invalidates an interrupted tick BEFORE cleanup. Its
    # guards prevent a nested selection from being expanded/hidden by this call.
    态 取 _建态 柄 旧['generation'] (旧['revision']+1) 旧['document'].
    _丢弃 柄 旧.
    态 其 增 'language' 'plain'.
    态 其 增 'pending' 假.
    _编辑们 其 增 (柄 其 句) 态.
    试
        _尺寸 柄 态.
        _全显 柄 态.
        _讯 柄 态 2242 2 0.
    救 原因
        # No cleanup retry: a callback may have installed another state.
        若 _本态 柄 态 则 态 其 增 'warningRecovery' ([(原因 为 句)]). 然
    终
    _丢弃 柄 态.
    得 空.
法
# Keep every diagnostic layer as a raw reason; translate the complete warning
# only when status is projected, without restarting policy work or native folds.
算 _警告 态:
    文 取 ''.
    若 态['warning'] != '' 则 文 取 本地 其 格式 (态['warning']) (态['warningArgs']). 然
    位 取 0.
    循 (态['warningRecovery']) 其 量 次
        文 取 本地 其 格式 'error.syntax.visibility_recovery' ([文,(态['warningRecovery'])[位]]).
        位 取 位+1.
    环
    得 文.
法
算 _失败 柄 态 原因 为 句:
    若 非 (_本态 柄 态) 则 得 空. 然
    撤销直属 柄.
    # Queue visibility before the first cleanup query. A same-document edit
    # creates a new disabled revision which inherits this unfinished obligation.
    态 其 增 'pending' 真.
    态 其 增 'phase' 'visibility'.
    若 非 态['registered'] 则 态 其 增 'language' 'plain'. 然
    态 其 增 'foldEnabled' 假.
    态 其 增 'warning' 'error.syntax.markdown_disabled'.
    态 其 增 'warningArgs' ([原因]).
    态 其 增 'warningRecovery' ([]).
    态 其 增 'policy' 空.
    态 其 增 'ranges' ([]).
    态 其 增 'chunk' ''.
    试
        _可见完成 柄 态.
    救 清理原因
        # No stale catch clears the replacement revision's visibility work.
        # A genuine same-owner cleanup failure stops here with a warning rather
        # than spinning forever on an unavailable native control.
        若 _本态 柄 态 则
            态 其 增 'pending' 假.
            态 其 增 'phase' 'disabled'.
            态 其 增 'warningRecovery' ([(清理原因 为 句)]).
        然
    终
    得 空.
法
算 _受限 柄 态:
    选项 取 (_讯 柄 态 2379 0 0) 其 数.
    得 态['length'] >= 32000000 或 选项 % 2 == 1.
法
算 _配折叠 柄 态:
    配置 取 [[2240,2,0],[2244,2,4261412864],[2246,2,1],[2242,2,16]].
    位 取 0.
    循 配置 其 量 次
        项 取 配置[位].
        _讯 柄 态 项[0] 项[1] 项[2].
        位 取 位+1.
    环
    符号们 取 [[25,13],[26,15],[27,11],[28,10],[29,9],[30,12],[31,14]].
    位 取 0.
    循 符号们 其 量 次
        项 取 符号们[位].
        _讯 柄 态 2040 项[0] 项[1].
        _讯 柄 态 2041 项[0] 16777215.
        _讯 柄 态 2042 项[0] 8947848.
        位 取 位+1.
    环
    得 空.
法
算 选择 柄:
    撤销直属 柄.
    若 非 (_同线程 柄) 则 得 'plain'. 然
    旧 取 _编辑们 其 查 (柄 其 句).
    _序号[0] 取 _序号[0]+1.
    态 取 _建态 柄 _序号[0] 0 ''.
    # Register the selection identity BEFORE the first synchronous query.
    # A nested select OR forget, including one that leaves no state, invalidates
    # this provisional state. No outer cleanup path can then register over it.
    _丢弃 柄 旧.
    _编辑们 其 增 (柄 其 句) 态.
    试
        _尺寸 柄 态.
        若 _受限 柄 态 则 卒 'Large-file mode disables folding.'. 然
        若 (_讯 柄 态 4002 0 0) 其 数 != 98 则 卒 'The Markdown lexer is not installed.'. 然
        态 其 增 'registered' 真.
    救 原因
        _失败 柄 态 (原因 为 句).
    终
    若 非 (_本态 柄 态) 则 得 'plain'. 然
    得 态['language'].
法
# Capability registration is explicit and fails closed. A provisional token
# prevents a reentrant registration from being overwritten by an older caller.
算 _须直属 柄 态 权:
    _须本态 柄 态.
    现 取 _直属们 其 查 (柄 其 句).
    若 现 == 空 或 现 != 权 或 现['token'] != 权['token'] 或 权['generation'] != 态['generation'] 或 权['document'] != 态['document'] 或 权['thread'] != 态['thread'] 则 卒 'Stale Markdown direct capability.'. 然
    若 非 (_同线程 权['parent']) 或 (窗 其 结果 (_GetParent 其 调用 [柄])) 其 句 != (权['parent']) 其 句 则 卒 'Reparented Markdown direct editor.'. 然
    若 态['language'] != 'markdown' 或 非 态['registered'] 则 卒 'Markdown direct owner is not selected.'. 然
    得 空.
法
算 登记直属 柄 父:
    # A null optional HWND has no capability key; reject before string conversion.
    若 柄 == 空 则 得 假. 然
    撤销直属 柄.
    若 非 _直库态['ready'] 或 非 (_同线程 柄) 或 非 (_同线程 父) 则 得 假. 然
    若 (窗 其 结果 (_GetParent 其 调用 [柄])) 其 句 != 父 其 句 则 得 假. 然
    态 取 _编辑们 其 查 (柄 其 句).
    若 态 == 空 或 态['language'] != 'markdown' 或 非 态['registered'] 或 态['inTick'] 则 得 假. 然
    若 _权序[0] >= 9007199254740990 则 得 假. 然
    _权序[0] 取 _权序[0]+1.
    权 取 {'token':_权序[0],'generation':态['generation'],'document':态['document'],'thread':态['thread'],'parent':父,'ready':假}.
    _直属们 其 增 (柄 其 句) 权.
    注册成功 取 [假].
    试
        _护 柄 态.
        掩码 取 (_讯 柄 态 2378 0 0) 其 数.
        _须直属 柄 态 权.
        若 掩码 == 3 则 权 其 增 'ready' 真. 注册成功[0] 取 真. 然
    救 原因
        # Ineligibility is optional; native callback errors/panics are not.
        # Drop only our provisional token and preserve the original exception.
        若 (_直属们 其 查 (柄 其 句)) == 权 则 撤销直属 柄. 然
        卒 原因.
    终
    若 非 注册成功[0] 且 (_直属们 其 查 (柄 其 句)) == 权 则 撤销直属 柄. 然
    得 注册成功[0].
法
算 变化 柄 位置 为 数 长度 为 数 加行 为 数 修改 为 数:
    旧 取 _编辑们 其 查 (柄 其 句).
    若 旧 == 空 或 旧['language'] != 'markdown' 或 修改 % 4 == 0 或 非 (_同线程 柄) 则 得 假. 然
    # Even inside a running tick, invalidate synchronously. No native messages
    # are sent from SCN_MODIFIED; the next timer snapshots size and expands.
    态 取 _建态 柄 旧['generation'] (旧['revision']+1) 旧['document'].
    态 其 增 'registered' 旧['registered'].
    态 其 增 'warning' 旧['warning'].
    态 其 增 'warningArgs' 旧['warningArgs'].
    态 其 增 'warningRecovery' 旧['warningRecovery'].
    态 其 增 'foldEnabled' 旧['foldEnabled'].
    若 非 旧['foldEnabled'] 则
        态 其 增 'policy' 空.
        态 其 增 'phase' 'disabled'.
        态 其 增 'pending' 假.
        若 旧['phase'] == 'visibility' 则
            态 其 增 'phase' 'visibility'.
            态 其 增 'pending' 真.
        然
    然
    _丢弃 柄 旧.
    _编辑们 其 增 (柄 其 句) 态.
    得 真.
法
算 设置折叠 柄 开启 为 事实:
    旧 取 _编辑们 其 查 (柄 其 句).
    若 旧 == 空 或 旧['language'] != 'markdown' 或 非 (_同线程 柄) 则 得 假. 然
    若 旧['foldEnabled'] == 开启 则 得 开启. 然
    态 取 _建态 柄 旧['generation'] (旧['revision']+1) 旧['document'].
    态 其 增 'registered' 真.
    态 其 增 'foldEnabled' 开启.
    若 非 开启 则 态 其 增 'policy' 空. 态 其 增 'phase' 'visibility'. 然
    _丢弃 柄 旧.
    _编辑们 其 增 (柄 其 句) 态.
    若 非 开启 则
        试 _可见完成 柄 态. 救 原因 _失败 柄 态 (原因 为 句). 终
    然
    得 (_本态 柄 态) 且 态['foldEnabled'].
法
算 _读块 柄 态 始 为 数 末 为 数:
    长 取 末-始.
    若 长 < 0 或 长 > 1024 则 卒 'Invalid bounded Markdown range.'. 然
    存 取 密 其 缓冲 (长+1).
    范围 取 _范围型 其 新建.
    试
        范围 其 写 'start' 始.
        范围 其 写 'end' 末.
        范围 其 写 'text' (存 其 地址).
        _护 柄 态.
        实长 取 (窗 其 发指 柄 2039 0 范围) 其 数.
        _护 柄 态.
        若 实长 != 长 则 卒 'Incomplete Markdown range.'. 然
        若 (窗 其 结果 ((窗 其 lstrlenA) 其 调用 [存])) 其 数 != 长 则 卒 'Embedded NUL is not supported by the Markdown fold scanner.'. 然
        若 长 > 0 则
            验 取 窗 其 结果 ((窗 其 MultiByteToWideChar) 其 调用 [65001,8,存,长,空,0]).
            若 验 其 为空 则 卒 'Invalid UTF-8 in the Markdown fold range.'. 然
        然
        文 取 存 其 解UTF8.
    救 原因
        范围 其 关闭.
        存 其 关闭.
        卒 原因.
    终
    范围 其 关闭.
    存 其 关闭.
    得 文.
法
算 _字节 文 为 句:
    存 取 密 其 UTF8 文.
    长 取 (存 其 大小)-1.
    存 其 关闭.
    得 长.
法
算 _验范围 态 范围们:
    若 范围们 其 量 > 64 则 卒 'Too many Markdown fold ranges.'. 然
    位 取 0.
    循 范围们 其 量 次
        项 取 范围们[位].
        若 项 其 量 != 4 或 项[0]%1 != 0 或 项[1]%1 != 0 或 项[2]%1 != 0 或 项[0] < 0 或 项[1] <= 0 或 项[0]+项[1] > 态['lines'] 或 项[2] < 0 或 项[2] > 6 或 (项[3] 且 项[1] != 1) 则 卒 'Invalid Markdown fold assignment.'. 然
        位 取 位+1.
    环
    得 空.
法
# This native-only guard preserves BOTH full owner checks. GETDOCPOINTER and
# GETLENGTH do not reenter; combining only their middle owner check is safe.
# The pinned runtime has no user destructors/native HWND finalizers during GC.
# No pointer is converted to a Ru number and every call uses typed 如:密 + 结果.
算 _直护 柄 态 直:
    _须本态 柄 态.
    文档 取 (窗 其 结果 (_DirectFunction 其 调用 [直,2357,0,0])) 其 句.
    长 取 (窗 其 结果 (_DirectFunction 其 调用 [直,2183,0,0])) 其 数.
    _须本态 柄 态.
    若 文档 != 态['document'] 则 卒 'Stale Markdown direct document.'. 然
    若 长 != 态['length'] 则 卒 'Markdown direct text changed without invalidation.'. 然
    得 空.
法
算 _直发布 柄 态 范围们 位 为 数 偏 为 数:
    # A false result is permitted ONLY before the first mutation. A stale owner
    # or revoked/replaced capability always throws; callers never replay it.
    若 非 _直接策略['enabled'] 或 _直接策略['route'] != 'perline' 或 非 _直库态['ready'] 则 得 空. 然
    权 取 _直属们 其 查 (柄 其 句).
    若 权 == 空 或 非 权['ready'] 则 得 空. 然
    _须直属 柄 态 权.
    _护 柄 态.
    掩码 取 (_讯 柄 态 2378 0 0) 其 数.
    自动 取 (_讯 柄 态 2664 0 0) 其 数.
    _须直属 柄 态 权.
    若 掩码 != 3 或 自动 != 0 则 得 空. 然
    # GETDIRECTPOINTER is deliberately the LAST window message before using
    # the pointer. It may synchronously edit/reselect/revoke/replace/close.
    # The immediate full state+capability check precedes EVERY direct call.
    直 取 空.
    借 取 空.
    数量 取 0.
    合格 取 假.
    试
        借 取 窗 其 发送 柄 2185 0 0.
        _须直属 柄 态 权.
        若 非 (借 其 为空) 则
            直 取 (窗 其 PTR) 其 重释 借.
            借 取 空.
            _直护 柄 态 直.
            # These read-only eligibility getters also cannot reenter. Recheck
            # them directly, since the 2185 callback could change configuration.
            掩码 取 (窗 其 结果 (_DirectFunction 其 调用 [直,2378,0,0])) 其 数.
            自动 取 (窗 其 结果 (_DirectFunction 其 调用 [直,2664,0,0])) 其 数.
            _须直属 柄 态 权.
            合格 取 掩码 == 3 且 自动 == 0 且 _直接策略['enabled'] 且 _直库态['ready'].
            若 合格 则
                _直护 柄 态 直.
                循
                    若 位 >= 范围们 其 量 或 数量 >= 64 则 破. 然
                    项 取 范围们[位].
                    行 取 项[0]+偏.
                    层 取 1024+项[2].
                    若 项[3] 则 层 取 层+8192. 然
                    # Only SETFOLDLEVEL is mutated. With one owned watcher,
                    # mask=3 and auto=0 it updates levels and invalidates paint;
                    # it cannot call application code or an external subclass.
                    计 取 _统计 柄 态.
                    计 其 增 'directCalls' (计['directCalls']+1).
                    窗 其 结果 (_DirectFunction 其 调用 [直,2222,行,层]).
                    _直护 柄 态 直.
                    # G0,M1,G1,M2,G2. Only built-in arithmetic occurs here;
                    # never carry this shared post/pre guard across a callback.
                    计 其 增 'directLines' (计['directLines']+1).
                    数量 取 数量+1.
                    偏 取 偏+1.
                    若 偏 >= 项[1] 则 位 取 位+1. 偏 取 0. 然
                环
            然
        然
        # Discard ALL borrowed native handles before status, return or recovery.
        直 取 空. 借 取 空.
    救 原因
        直 取 空. 借 取 空.
        卒 原因.
    终
    若 非 合格 则 得 空. 然
    得 [位,偏,数量].
法
# Advance a compressed cursor using only bounded Ru arithmetic. This is also
# the independent result validator; it never adopts a native diagnostic cursor.
算 _批移位 范围们 位 为 数 偏 为 数 上限 为 数:
    若 位%1 != 0 或 偏%1 != 0 或 位 < 0 或 位 > 范围们 其 量 或 偏 < 0 则 卒 'Invalid Markdown batch cursor.'. 然
    若 位 == 范围们 其 量 则
        若 偏 != 0 则 卒 'Invalid Markdown end cursor.'. 然
    另
        若 偏 >= 范围们[位][1] 则 卒 'Invalid Markdown range offset.'. 然
    然
    数量 取 0.
    循
        若 位 == 范围们 其 量 或 数量 == 上限 则 破. 然
        可用 取 范围们[位][1]-偏.
        若 可用 > 上限-数量 则 可用 取 上限-数量. 然
        偏 取 偏+可用. 数量 取 数量+可用.
        若 偏 == 范围们[位][1] 则 位 取 位+1. 偏 取 0. 然
    环
    得 [位,偏,数量].
法
算 _写批计划 存 态 范围们 位 为 数 偏 为 数:
    _验范围 态 范围们.
    _批移位 范围们 位 偏 64.
    若 态['lines']%1 != 0 或 态['lines'] < 1 或 态['lines'] > 4294967295 则 卒 'Invalid Markdown expected line count.'. 然
    存 其 写 'abi' 65536. 存 其 写 'rangeCount' (范围们 其 量).
    存 其 写 'rangeIndex' 位. 存 其 写 'rangeOffset' 偏.
    存 其 写 'expectedLines' 态['lines']. 存 其 写 'maxLines' 64.
    存 其 写 'reserved0' 0. 存 其 写 'reserved1' 0.
    索引 取 0.
    循 范围们 其 量 次
        项 取 范围们[索引].
        行存 取 存 其 读 _批范围名[索引].
        行存 其 写 'start' 项[0]. 行存 其 写 'count' 项[1]. 行存 其 写 'depth' 项[2].
        标志 取 0. 若 项[3] 则 标志 取 1. 然
        行存 其 写 'header' 标志. 行存 其 关闭.
        索引 取 索引+1.
    环
    得 32+16*(范围们 其 量).
法
算 _验批果 范围们 位 为 数 偏 为 数 状码 为 数 果:
    若 果 其 量 != 8 则 卒 'Invalid Markdown bulk result size.'. 然
    索引 取 0.
    循 8 次
        若 果[索引]%1 != 0 或 果[索引] < 0 或 果[索引] > 4294967295 则 卒 'Invalid Markdown bulk result word.'. 然
        索引 取 索引+1.
    环
    上限 取 _批移位 范围们 位 偏 64.
    # BAD_ARGUMENT5 may leave the result untouched; it is always fatal here.
    # BAD_PLAN before cursor decode may also fail this stricter validator.
    # Neither condition is eligible for replay or ordinary fallback.
    若 状码 < 0 或 状码 > 4 或 果[0] != 状码 或 果[6] != 0 或 果[7] != 0 或 果[1] > 上限[2] 或 果[2] > 果[1] 或 果[1]-果[2] > 1 则 卒 'Invalid Markdown bulk result envelope.'. 然
    预期 取 _批移位 范围们 位 偏 果[1].
    若 果[3] != 预期[0] 或 果[4] != 预期[1] 则 卒 'Invalid Markdown bulk result cursor.'. 然
    若 状码 == 0 且 (果[1] != 上限[2] 或 果[2] != 上限[2] 或 果[5] != 0) 则 卒 'Incomplete Markdown bulk publication.'. 然
    若 状码 == 1 且 (果[1] != 0 或 果[2] != 0 或 果[5] != 0) 则 卒 'Unsafe Markdown bulk fallback result.'. 然
    若 状码 == 3 且 (果[1] != 0 或 果[2] != 0) 则 卒 'Malformed Markdown bulk plan wrote data.'. 然
    若 状码 == 4 且 果[5] == 0 则 卒 'Missing Markdown bulk native error.'. 然
    若 状码 != 4 且 果[5] != 0 则 卒 'Unexpected Markdown bulk native status.'. 然
    得 预期.
法
算 _批发布 柄 态 范围们 位 为 数 偏 为 数:
    若 非 _直接策略['enabled'] 或 _直接策略['route'] != 'bulk' 或 非 _直库态['ready'] 或 非 _批库态['ready'] 或 _批库态['abi'] != 65536 则 得 空. 然
    权 取 _直属们 其 查 (柄 其 句).
    若 权 == 空 或 非 权['ready'] 则 得 空. 然
    _须直属 柄 态 权.
    _护 柄 态.
    掩码 取 (_讯 柄 态 2378 0 0) 其 数.
    自动 取 (_讯 柄 态 2664 0 0) 其 数.
    _须直属 柄 态 权.
    若 掩码 != 3 或 自动 != 0 则 得 空. 然
    计划 取 空. 结果存 取 空. 直 取 空. 借 取 空. 文档 取 空.
    位置果 取 空. 状码 取 1.
    试
        计划 取 _批计划型 其 新建.
        结果存 取 _批果型 其 新建.
        字节数 取 _写批计划 计划 态 范围们 位 偏.
        若 (计划 其 大小) != 1056 或 (结果存 其 大小) != 32 则 卒 'Invalid Markdown bulk ABI layout.'. 然
        计 取 _统计 柄 态.
        若 字节数 > 计['maxPlanBytes'] 则 计 其 增 'maxPlanBytes' 字节数. 然
        计 其 增 'ownedBufferBytes' 1088.
        # Expected document is a typed native2357 result, never rebuilt from
        # state['document'] text or a floating-point address. Full guards wrap it.
        _护 柄 态.
        文档 取 窗 其 发送 柄 2357 0 0.
        _护 柄 态.
        若 文档 其 句 != 态['document'] 则 卒 'Stale Markdown bulk document.'. 然
        文档 取 (窗 其 PTR) 其 重释 文档.
        _须直属 柄 态 权.
        # LAST window message: immediately check the complete owner capability.
        # Between2185 and apply there are only ownership/QPC/typed-buffer calls.
        借 取 窗 其 发送 柄 2185 0 0.
        _须直属 柄 态 权.
        若 非 (借 其 为空) 且 _直接策略['enabled'] 且 _直接策略['route'] == 'bulk' 且 _直库态['ready'] 且 _批库态['ready'] 且 _批库态['abi'] == 65536 则
            直 取 (窗 其 PTR) 其 重释 借. 借 取 空.
            起时 取 _统计时刻 计.
            计 其 增 'bulkCalls' (计['bulkCalls']+1).
            试
                状码 取 (窗 其 结果 (_FoldApply 其 调用 [柄,权['parent'],_直库态['module'],直,文档,态['length'],计划,字节数,结果存,32])) 其 数.
            救 原因
                _统计耗时 计 起时.
                卒 原因.
            终
            _统计耗时 计 起时.
            _须直属 柄 态 权.
            # Native code retains nothing; erase borrowed pointers before any
            # message-based postguard or recovery can reenter the application.
            直 取 空. 借 取 空. 文档 取 空.
            _护 柄 态.
            _须直属 柄 态 权.
            果 取 结果存 其 读U32LE阵 0 8.
            位置果 取 _验批果 范围们 位 偏 状码 果.
            计 其 增 'bulkLines' (计['bulkLines']+果[2]).
            若 状码 != 0 且 状码 != 1 则 卒 ('Markdown bulk publication failed with status '+(状码 为 句)+'.'). 然
        然
        直 取 空. 借 取 空. 文档 取 空.
        结果存 其 关闭. 结果存 取 空.
        计划 其 关闭. 计划 取 空.
    救 原因
        直 取 空. 借 取 空. 文档 取 空.
        若 结果存 != 空 则 结果存 其 关闭. 然
        若 计划 != 空 则 计划 其 关闭. 然
        卒 原因.
    终
    若 状码 == 1 则 得 空. 然
    得 位置果.
法
算 _发布 柄 态:
    # Only a prepared scan owns the all-visible/all-expanded invariant below.
    若 态['phase'] != 'scan' 或 非 态['pending'] 或 非 态['foldEnabled'] 或 态['language'] != 'markdown' 则 卒 'Markdown publication is not a prepared pending scan.'. 然
    _护 柄 态.
    范围们 取 态['ranges'].
    _验范围 态 范围们.
    位 取 态['rangeIndex'].
    偏 取 态['rangeOffset'].
    数量 取 0.
    直果 取 空.
    若 _直接策略['route'] == 'perline' 则
        直果 取 _直发布 柄 态 范围们 位 偏.
    另
        直果 取 _批发布 柄 态 范围们 位 偏.
    然
    若 直果 != 空 则
        位 取 直果[0]. 偏 取 直果[1]. 数量 取 直果[2].
    另
        # Ineligibility (including NULL/missing export) cannot weaken the
        # generic route. Its first write gets a fresh complete message guard.
        _护 柄 态.
        计 取 _统计 柄 态.
        计 其 增 'fallbackBatches' (计['fallbackBatches']+1).
        循
            若 位 >= 范围们 其 量 或 数量 >= 64 则 破. 然
            项 取 范围们[位].
            行 取 项[0]+偏.
            层 取 1024+项[2].
            若 项[3] 则 层 取 层+8192. 然
            # G0,M1,G1,M2,G2: only pure cursor arithmetic separates writes.
            窗 其 发送 柄 2222 行 层.
            _护 柄 态.
            数量 取 数量+1.
            偏 取 偏+1.
            若 偏 >= 项[1] 则 位 取 位+1. 偏 取 0. 然
        环
    然
    # prepare already expanded all old levels and disabled automatic folding.
    # Never repeat per-line FOLDLINE(Expand), which traverses native children.
    _检查 柄 态.
    态 其 增 'rangeIndex' 位.
    态 其 增 'rangeOffset' 偏.
    态 其 增 'published' (态['published']+数量).
    若 数量 > 态['maxPublish'] 则 态 其 增 'maxPublish' 数量. 然
    若 位 == 范围们 其 量 则
        态 其 增 'ranges' ([]).
        态 其 增 'rangeIndex' 0.
        态 其 增 'rangeOffset' 0.
    然
    得 空.
法
算 _一步 柄 态:
    # Cleanup remains eligible with folding disabled, large-file options or an
    # existing native warning. It never feeds or publishes an old policy range.
    若 态['phase'] == 'visibility' 则 _可见完成 柄 态. 得 空. 然
    若 态['length'] < 0 则 _尺寸 柄 态. 然
    _护 柄 态.
    若 _受限 柄 态 则 卒 'Large-file mode disables folding.'. 然
    若 态['phase'] == 'prepare' 则
        若 (_讯 柄 态 4002 0 0) 其 数 != 98 则 卒 'The Markdown lexer is no longer installed.'. 然
        态 其 增 'registered' 真.
        _全显 柄 态.
        _配折叠 柄 态.
        _检查 柄 态.
        态 其 增 'phase' 'scan'.
        得 空.
    然
    若 (态['ranges']) 其 量 > 0 则 _发布 柄 态. 得 空. 然
    若 态['eof'] 则
        # finished means EOF AND the entire last range batch has been published.
        若 态['feed'] != 态['length'] 或 态['chunk'] != '' 则 卒 'Premature Markdown EOF.'. 然
        _讯 柄 态 2663 5 0.
        _检查 柄 态.
        态 其 增 'pending' 假.
        得 空.
    然
    始 取 态['feed'].
    若 态['chunk'] == '' 且 始 < 态['length'] 则
        末 取 始+1024.
        若 末 >= 态['length'] 则 末 取 态['length']. 另 末 取 (_讯 柄 态 2417 (末+1) 0) 其 数. 然
        若 末 <= 始 或 末-始 > 1024 则 卒 'Invalid Markdown UTF-8 boundary.'. 然
        文 取 _读块 柄 态 始 末.
        态 其 增 'chunk' 文.
        态 其 增 'readEnd' 末.
        态 其 增 'readBytes' (态['readBytes']+末-始).
        若 末-始 > 态['maxRead'] 则 态 其 增 'maxRead' (末-始). 然
    然
    文 取 态['chunk'].
    果 取 策 其 喂入 态['policy'] 文 (态['readEnd'] == 态['length']).
    _护 柄 态.
    用 取 果['used'].
    若 用 < 0 或 用 > 文 其 量 则 卒 'Invalid Markdown consumed scalar count.'. 然
    末 取 始+(_字节 文[0:用]).
    若 果['bytes'] != 末 或 末 > 态['readEnd'] 或 (果['finished'] 且 (末 != 态['length'] 或 用 != 文 其 量)) 则 卒 'Invalid Markdown byte progress.'. 然
    _验范围 态 果['folds'].
    若 用 == 0 且 (果['folds']) 其 量 == 0 且 非 果['finished'] 则 卒 'Markdown scanner made no progress.'. 然
    态 其 增 'feed' 末.
    态 其 增 'chunk' 文[用:].
    态 其 增 'ranges' 果['folds'].
    态 其 增 'rangeIndex' 0.
    态 其 增 'rangeOffset' 0.
    态 其 增 'eof' 果['finished'].
    态 其 增 'chunks' (态['chunks']+1).
    若 (果['folds']) 其 量 > 态['maxRanges'] 则 态 其 增 'maxRanges' ((果['folds']) 其 量). 然
    # Read errors are not cleared at entry: preserve unrelated status/warnings.
    _检查 柄 态.
    得 空.
法
算 推进 柄 预算 为 数:
    态 取 _编辑们 其 查 (柄 其 句).
    若 态 == 空 或 非 态['pending'] 或 态['inTick'] 或 非 (_同线程 柄) 则 得 假. 然
    若 预算 <= 0 或 预算 > 8 则 预算 取 8. 然
    起时 取 0.
    态 其 增 'inTick' 真.
    试
        起时 取 时刻.
        循
            块始 取 时刻.
            _一步 柄 态.
            现在 取 时刻.
            若 现在-块始 > 态['maxChunkMs'] 则 态 其 增 'maxChunkMs' (现在-块始). 然
            若 非 态['pending'] 或 非 (_本态 柄 态) 或 现在-起时+(现在-块始) >= 预算 则 破. 然
        环
        耗时 取 (时刻)-起时.
        若 耗时 > 态['maxTickMs'] 则 态 其 增 'maxTickMs' 耗时. 然
    救 原因
        # Clear our own flag before recovery, even if QPC or recovery itself
        # fails. This never clears the replacement state's independent flag.
        态 其 增 'inTick' 假.
        _失败 柄 态 (原因 为 句).
    终
    态 其 增 'inTick' 假.
    得 待办 柄.
法
算 待办 柄:
    态 取 _编辑们 其 查 (柄 其 句).
    得 态 != 空 且 态['alive'] 且 态['pending'].
法
算 请求 柄 位置 为 数:
    # Lexilla, not this bridge, services SCN_STYLENEEDED. Never recurse here.
    得 待办 柄.
法
算 状态 柄:
    态 取 _编辑们 其 查 (柄 其 句).
    若 态 == 空 则 得 空. 然
    计 取 _统计 柄 态.
    # Fixed numeric observational phase; never advances scanner state.
    阶段 取 0.
    若 态['phase'] == 'scan' 则 阶段 取 1. 若 (态['ranges']) 其 量 > 0 则 阶段 取 2. 然 然
    若 态['phase'] == 'visibility' 则 阶段 取 3. 然
    若 非 态['pending'] 则 阶段 取 4. 然
    得 {'phaseCode':阶段,'enabled':(态['language'] == 'markdown'),'foldEnabled':态['foldEnabled'],'language':态['language'],'warning':(_警告 态),'pending':态['pending'],'generation':态['generation'],'revision':态['revision'],'identity':态['identity'],'feed':态['feed'],'bytes':态['feed'],'length':态['length'],'chunks':态['chunks'],'readBytes':态['readBytes'],'published':态['published'],'maxRead':态['maxRead'],'maxPublish':态['maxPublish'],'maxRanges':态['maxRanges'],'maxTickMs':态['maxTickMs'],'maxChunkMs':态['maxChunkMs'],'restart':0,'points':0,'eof':态['eof'],'queuedRanges':((态['ranges']) 其 量),'rangeIndex':态['rangeIndex'],'rangeOffset':态['rangeOffset'],'bulkCalls':计['bulkCalls'],'bulkLines':计['bulkLines'],'fallbackBatches':计['fallbackBatches'],'directCalls':计['directCalls'],'directLines':计['directLines'],'maxPlanBytes':计['maxPlanBytes'],'bulkUs':计['bulkUs'],'ownedBufferBytes':计['ownedBufferBytes'],'bulkMetricsValid':计['bulkMetricsValid']}.
法
算 排空 柄:
    # Acceptance-test helper only; production admits one tick per timer.
    循 若 非 (推进 柄 8) 则 破. 然 环
    得 状态 柄.
法
算 折叠 柄 位置 为 数:
    态 取 _编辑们 其 查 (柄 其 句).
    若 态 == 空 或 态['language'] != 'markdown' 或 非 态['foldEnabled'] 或 态['pending'] 则 得 假. 然
    成功 取 [假].
    试
        行 取 (_讯 柄 态 2166 位置 0) 其 数.
        层 取 (_讯 柄 态 2223 行 0) 其 数.
        若 层 % 16384 >= 8192 则 _讯 柄 态 2231 行 0. _检查 柄 态. 成功[0] 取 真. 然
    救 原因 _失败 柄 态 (原因 为 句). 终
    得 成功[0].
法
算 全折 柄 动作 为 数:
    态 取 _编辑们 其 查 (柄 其 句).
    若 态 == 空 或 态['language'] != 'markdown' 或 非 态['foldEnabled'] 或 态['pending'] 或 动作 < 0 或 动作 > 2 则 得 假. 然
    成功 取 [假].
    试 _讯 柄 态 2662 动作 0. _检查 柄 态. 成功[0] 取 真. 救 原因 _失败 柄 态 (原因 为 句). 终
    得 成功[0].
法
