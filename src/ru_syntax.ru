# Ru's own incremental container styler. Scintilla owns all text/undo/selection.
# No Lexilla dependency and no whole-document extraction. Feed <=1024 UTF-8 bytes;
# independent lexical snapshots every 32 KiB bound restart distance below 64 KiB.
密 取 外言 '如:密'.
窗 取 外言 'win32.ru'.
词 取 外言 'ru_native_syntax.ru'.
_编辑们 取 {}.
_序号 取 [0].
_范围型 取 密 其 结构 [['start',窗 其 IP],['end',窗 其 IP],['text',窗 其 PTR]].
_计数型 取 密 其 结构 [['value',密 其 i64]].
_IsWindow 取 (窗 其 用户) 其 绑定 'IsWindow' (密 其 签名 (窗 其 I) ([(窗 其 PTR)]) 'win64').
_QueryPerformanceCounter 取 (窗 其 内核) 其 绑定 'QueryPerformanceCounter' (密 其 签名 (窗 其 I) ([(窗 其 PTR)]) 'win64').
_QueryPerformanceFrequency 取 (窗 其 内核) 其 绑定 'QueryPerformanceFrequency' (密 其 签名 (窗 其 I) ([(窗 其 PTR)]) 'win64').
_频率存 取 _计数型 其 新建.
窗 其 成功 (_QueryPerformanceFrequency 其 调用 [_频率存]) 'QueryPerformanceFrequency'.
_频率 取 (_频率存 其 读 'value') 其 数.
_频率存 其 关闭.
_时存 取 _计数型 其 新建. # UI-thread-only QPC call never invokes application callbacks.

算 初始化:
    得 词 其 初始化.
法
算 _时刻:
    窗 其 成功 (_QueryPerformanceCounter 其 调用 [_时存]) 'QueryPerformanceCounter'.
    计数 取 _时存 其 读 'value'.
    # Counter uptime may exceed the exact native-to-Ru integer conversion range.
    # Split first; timing deliberately uses a floating millisecond value.
    数值 取 (计数 其 位段 32 32)*4294967296+(计数 其 位段 0 32).
    得 数值*1000/_频率.
法
算 时刻:
    得 _时刻.
法
算 _存在 柄:
    得 非 ((窗 其 结果 (_IsWindow 其 调用 [柄])) 其 为空).
法
算 _放点 点们:
    位 取 0.
    循 点们 其 量 次
        词 其 释放 点们[位][1].
        位 取 位+1.
    环
    得 空.
法
算 _放候 态:
    _放点 态['candidates'].
    态 其 增 'candidates' ([]).
    得 空.
法
算 _放态 态:
    若 态 == 空 则 得 空. 然
    词 其 释放 态['lexical'].
    态 其 增 'lexical' 空.
    _放点 态['points'].
    态 其 增 'points' ([]).
    _放候 态.
    得 空.
法
算 _状态 柄:
    态 取 _编辑们 其 查 (柄 其 句).
    若 态 == 空 则 得 空. 然
    若 非 (_存在 柄) 则
        _放态 态.
        _编辑们 其 除 (柄 其 句).
        得 空.
    然
    若 (窗 其 发送 柄 2357 0 0) 其 句 != 态['document'] 则
        # The queued generation belongs to the released/replaced document.
        _放态 态.
        _编辑们 其 除 (柄 其 句).
        得 空.
    然
    得 态.
法
算 _受限 柄:
    选项 取 (窗 其 发送 柄 2379 0 0) 其 数.
    得 (选项 % 2 == 1) 或 ((窗 其 发送 柄 2183 0 0) 其 数 >= 32000000).
法
算 _全显 柄:
    若 非 (_存在 柄) 则 得 空. 然
    # Show first, before clearing old levels: collapsed children must be reachable.
    窗 其 发送 柄 2662 1 0.
    行数 取 (窗 其 发送 柄 2154 0 0) 其 数.
    若 行数 > 0 则 窗 其 发送 柄 2226 0 (行数-1). 然
    窗 其 发送 柄 2663 0 0.
    窗 其 发送 柄 2242 2 0.
    得 空.
法
算 遗忘 柄:
    # Required before DestroyWindow / SETDOCPOINTER; no stale HWND retained.
    _放态 (_编辑们 其 查 (柄 其 句)).
    _编辑们 其 除 (柄 其 句).
    得 空.
法
算 停用 柄:
    遗忘 柄.
    _全显 柄.
    得 空.
法
算 _失败 柄 态 原因 为 句:
    态 其 增 'pending' 假.
    态 其 增 'language' 'plain'.
    态 其 增 'warning' ('Ru syntax highlighting was disabled: '+原因+' Your document remains editable as plain text.').
    _放态 态.
    _全显 柄.
    窗 其 发送 柄 4033 0 0.
    窗 其 发送 柄 2005 0 0.
    得 空.
法
算 _配折叠 柄:
    # Only SHOW/CHANGE automation. Clicks route through our owning-document API.
    窗 其 发送 柄 2663 5 0.
    窗 其 发送 柄 2240 2 0.
    窗 其 发送 柄 2244 2 4261412864.
    窗 其 发送 柄 2246 2 1.
    窗 其 发送 柄 2242 2 16.
    符号们 取 [[25,13],[26,15],[27,11],[28,10],[29,9],[30,12],[31,14]].
    位 取 0.
    循 符号们 其 量 次
        项 取 符号们[位].
        窗 其 发送 柄 2040 项[0] 项[1].
        窗 其 发送 柄 2041 项[0] 16777215.
        窗 其 发送 柄 2042 项[0] 8947848.
        位 取 位+1.
    环
    得 空.
法
算 _初始化失败 初 原因 为 句:
    # Rescue has its own binding scope. Mutate one shared holder so a failed
    # checkpoint copy cannot leave a released context or hide the warning.
    词 其 释放 初['lexical'].
    初 其 增 'lexical' 空.
    初 其 增 'points' ([]).
    初 其 增 'warning' ('Ru scanner initialization failed: '+原因+'. Your document remains editable as plain text.').
    得 空.
法
算 选择 柄:
    停用 柄.
    若 非 (_存在 柄) 或 (_受限 柄) 则 得 'plain'. 然
    窗 其 发送 柄 4033 0 0. # SCLEX_CONTAINER, no external ILexer5.
    窗 其 发送 柄 2005 0 0.
    窗 其 发送 柄 2692 0 0. # Our timer owns bounded work even while wrapping.
    _序号[0] 取 _序号[0]+1.
    初 取 {'lexical':空,'points':[],'warning':(词 其 初始化)}.
    若 词 其 可用 则
        试
            初 其 增 'lexical' (词 其 新状态).
            (初['points']) 其 增 [0,(词 其 复制状态 初['lexical']),假].
        救 原因
            _初始化失败 初 (原因 为 句).
        终
    然
    态 取 {'document':(窗 其 发送 柄 2357 0 0) 其 句,'generation':_序号[0], 'revision':0,'language':'ru','warning':'','feed':0,'readEnd':0,'bytes':0,'lexical':初['lexical'],'points':初['points'],'pending':真,'inTick':假,'requested':0,'chunks':0,'readBytes':0,'restart':0,'maxRead':0,'maxTickMs':0,'maxChunkMs':0,'candidates':[],'candidateIndex':0,'delta':0,'lineDelta':0,'dirtyEnd':0,'reuseComplete':假,'reusedBytes':0,'editReadBytes':0,'converged':假}.
    _编辑们 其 增 (柄 其 句) 态.
    若 初['lexical'] == 空 则
        态 其 增 'pending' 假.
        态 其 增 'language' 'plain'.
        态 其 增 'warning' 初['warning'].
        得 'plain'.
    然
    _配折叠 柄.
    色板 取 [[1,3573283],[2,1381795],[3,12665455],[4,12934144],[5,12665455],[6,3023567],[7,4473924],[8,2039583],[9,255]].
    位 取 0.
    循 色板 其 量 次
        项 取 色板[位].
        窗 其 发送 柄 2051 项[0] 项[1].
        位 取 位+1.
    环
    得 'ru'.
法
算 _读块 柄 始 为 数 末 为 数:
    长 取 末-始.
    若 长 < 0 或 长 > 1024 则 卒 'Invalid bounded Ru styling range.'. 然
    存 取 密 其 缓冲 (长+1).
    范围 取 _范围型 其 新建.
    试
        范围 其 写 'start' 始.
        范围 其 写 'end' 末.
        范围 其 写 'text' (存 其 地址).
        实长 取 (窗 其 发指 柄 2039 0 范围) 其 数.
        若 实长 != 长 则 卒 'Scintilla returned an incomplete styling range.'. 然
        若 (窗 其 结果 ((窗 其 lstrlenA) 其 调用 [存])) 其 数 != 长 则 卒 'The source contains an embedded NUL byte.'. 然
        若 长 > 0 则
            验 取 窗 其 结果 ((窗 其 MultiByteToWideChar) 其 调用 [65001,8,存,长,空,0]).
            若 验 其 为空 则 卒 'The source contains invalid UTF-8.'. 然
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
算 请求 柄 位置 为 数:
    态 取 _状态 柄.
    若 态 == 空 或 态['language'] != 'ru' 则 得 假. 然
    # Notification is synchronous; queue only, never recurse into styling here.
    若 位置 > 态['requested'] 则 态 其 增 'requested' 位置. 然
    得 态['pending'].
法
算 变化 柄 位置 为 数 长度 为 数 加行 为 数 修改 为 数:
    态 取 _状态 柄.
    若 态 == 空 或 态['language'] != 'ru' 或 态['inTick'] 或 修改 % 4 == 0 则 得 假. 然
    若 _受限 柄 则 _失败 柄 态 'Large-file mode disables byte styles and folding.'. 得 假. 然
    若 位置 < 0 则 位置 取 0. 然
    # Preserve only an already-complete suffix. Deletion/insertion notifications
    # may coalesce into a same-byte, same-line edit before the next timer tick.
    若 非 态['pending'] 则
        _放候 态.
        候们 取 态['points'].
        候位 取 0.
        循 候们 其 量 次
            词 其 保留 候们[候位][1].
            候位 取 候位+1.
        环
        态 其 增 'candidates' 候们.
        态 其 增 'delta' 0.
        态 其 增 'lineDelta' 0.
        态 其 增 'dirtyEnd' 位置.
        态 其 增 'reuseComplete' 真.
    然
    偏移 取 0.
    若 修改 % 2 == 1 则 偏移 取 长度. 另 偏移 取 0-长度. 然
    态 其 增 'delta' (态['delta']+偏移).
    态 其 增 'lineDelta' (态['lineDelta']+加行).
    # This conservative high-water bound stays beyond every changed byte even
    # for several insert/delete operations at differing positions in one tick.
    脏末 取 态['dirtyEnd']+长度.
    # A prior timer may already have published styles from an intermediate
    # edit generation beyond the next old checkpoint. Revisit all of that
    # region before reusing the untouched completed suffix.
    若 态['pending'] 且 态['feed']+长度 > 脏末 则 脏末 取 态['feed']+长度. 然
    若 位置+长度 > 脏末 则 脏末 取 位置+长度. 然
    态 其 增 'dirtyEnd' 脏末.
    态 其 增 'candidateIndex' 0.
    态 其 增 'editReadBytes' 0.
    态 其 增 'reusedBytes' 0.
    态 其 增 'converged' 假.
    点们 取 态['points'].
    位 取 (点们 其 量)-1.
    循
        若 位 <= 0 则 破. 然
        点验 取 点们[位].
        若 点验[0] <= 位置 且 非 点验[2] 则 破. 然
        位 取 位-1.
    环
    点 取 点们[位].
    _放点 点们[位+1:].
    态 其 增 'points' 点们[0:位+1].
    态 其 增 'feed' 点[0].
    态 其 增 'readEnd' 点[0].
    态 其 增 'restart' 点[0].
    态 其 增 'bytes' 点[0].
    新词态 取 词 其 复制状态 点[1].
    词 其 释放 态['lexical'].
    态 其 增 'lexical' 新词态.
    态 其 增 'pending' 真.
    态 其 增 'revision' (态['revision']+1).
    # Expand only the edited fold. Other collapsed headers retain their flags.
    行 取 (窗 其 发送 柄 2166 位置 0) 其 数.
    窗 其 发送 柄 2232 行 0.
    窗 其 发送 柄 2237 行 1.
    得 真.
法
算 _施样 柄 态 结果 长 为 数:
    # Validate the ENTIRE batch before the first style/fold mutation. No caller
    # can supply an arbitrary Scintilla message or an unchecked native pointer.
    若 非 (_存在 柄) 或 (窗 其 发送 柄 2357 0 0) 其 句 != 态['document'] 或 (窗 其 发送 柄 2183 0 0) 其 数 != 长 则 卒 'The styling batch belongs to a stale document.'. 然
    始 取 结果['styleStart'].
    色长 取 结果['styleLength'].
    色存 取 结果['styleBuffer'].
    若 始 < 0 或 色长 < 0 或 色长 > 色存 其 大小 或 始+色长 != 结果['bytes'] 或 始+色长 > 长 则 卒 'The Ru scanner returned an invalid contiguous style buffer.'. 然
    段们 取 结果['spans'].
    位 取 0.
    循 段们 其 量 次
        段 取 段们[位].
        若 段[0] < 0 或 段[1] < 0 或 段[1] > 64 或 段[0]+段[1] > 长 或 段[2] < 0 或 段[2] > 9 则 卒 'The Ru scanner returned an invalid byte-style correction.'. 然
        位 取 位+1.
    环
    折们 取 结果['folds'].
    行数 取 0.
    若 折们 其 量 > 0 则 行数 取 (窗 其 发送 柄 2154 0 0) 其 数. 然
    位 取 0.
    循 折们 其 量 次
        项 取 折们[位].
        若 项[0] < 0 或 项[0] >= 行数 或 项[1] < 0 或 项[1] > 3071 则 卒 'The Ru scanner returned an invalid fold level.'. 然
        位 取 位+1.
    环
    若 色长 > 0 则
        窗 其 发送 柄 2032 始 0.
        窗 其 发指 柄 2073 色长 色存. # SCI_SETSTYLINGEX copies synchronously.
    另
        窗 其 发送 柄 2032 结果['bytes'] 0.
    然
    # This owned container is the only style publisher; successful SETSTYLINGEX
    # advances endStyled exactly by the validated length (pinned Document.cxx).
    样末 取 结果['bytes'].
    位 取 0.
    循 段们 其 量 次
        段 取 段们[位].
        若 样末 != 段[0] 则 窗 其 发送 柄 2032 段[0] 0. 然
        窗 其 发送 柄 2033 段[1] 段[2].
        样末 取 段[0]+段[1].
        位 取 位+1.
    环
    # Corrections may precede this batch. Never leave endStyled behind the
    # validated contiguous prefix or mark an unanalysed suffix complete.
    若 样末 < 结果['bytes'] 则 窗 其 发送 柄 2032 结果['bytes'] 0. 然
    位 取 0.
    循 折们 其 量 次
        项 取 折们[位].
        层 取 1024+项[1].
        若 项[2] 则 层 取 层+8192. 然
        # Base levels are already known on an initial cleared document. On
        # edits they must be published to remove stale nesting. SetLevel itself
        # suppresses unchanged notifications and preserves expanded flags.
        若 态['revision'] != 0 或 层 != 1024 则 窗 其 发送 柄 2222 项[0] 层. 然
        位 取 位+1.
    环
    得 空.
法
算 _一步 柄 态:
    长 取 (窗 其 发送 柄 2183 0 0) 其 数.
    始 取 态['feed'].
    若 始 > 长 则 卒 'The document changed without a styling invalidation.'. 然
    候点 取 空.
    若 态['reuseComplete'] 且 态['delta'] == 0 且 态['lineDelta'] == 0 则
        候们 取 态['candidates'].
        候位 取 态['candidateIndex'].
        循
            若 候位 >= 候们 其 量 则 破. 然
            候 取 候们[候位].
            若 候[0] > 始 且 候[0] > 态['dirtyEnd'] 则 候点 取 候. 破. 然
            候位 取 候位+1.
        环
        态 其 增 'candidateIndex' 候位.
    然
    文 取 ''.
    读长 取 0.
    若 始 == 态['readEnd'] 则
        读末 取 始+1024.
        若 候点 != 空 且 候点[0] < 读末 则 读末 取 候点[0]. 然
        若 读末 >= 长 则 读末 取 长. 另 读末 取 (窗 其 发送 柄 2417 (读末+1) 0) 其 数. 然
        若 读末 < 始 或 (读末 == 始 且 始 < 长) 则 卒 'Scintilla returned an invalid UTF-8 boundary.'. 然
        文 取 _读块 柄 始 读末.
        读长 取 读末-始.
        态 其 增 'readEnd' 读末.
    然
    限 取 -1.
    若 候点 != 空 则 限 取 候点[0]-始. 然
    结果 取 词 其 扫描 态['lexical'] 文 (态['readEnd'] == 长) 限.
    末 取 始+结果['consumed'].
    若 末 > 态['readEnd'] 或 结果['bytes'] > 末 或 (结果['done'] 且 (末 != 长 或 结果['bytes'] != 长)) 则 卒 'The Ru scanner returned an invalid feed/processed position.'. 然
    _施样 柄 态 结果 长.
    态 其 增 'feed' 末.
    态 其 增 'bytes' 结果['bytes'].
    态 其 增 'chunks' (态['chunks']+1).
    态 其 增 'readBytes' (态['readBytes']+读长).
    态 其 增 'editReadBytes' (态['editReadBytes']+读长).
    若 读长 > 态['maxRead'] 则 态 其 增 'maxRead' 读长. 然
    若 候点 != 空 且 末 == 候点[0] 且 (词 其 等价 态['lexical'] 候点[1]) 则
        # Exact complete context equality plus alignment proves the previously
        # styled suffix reusable. dirtyEnd also includes intermediate publishes.
        点们 取 态['points'].
        候们 取 态['candidates'].
        候位 取 态['candidateIndex'].
        循
            若 候位 >= 候们 其 量 则 破. 然
            词 其 保留 候们[候位][1].
            点们 其 增 候们[候位].
            候位 取 候位+1.
        环
        终点 取 候们[(候们 其 量)-1].
        新词态 取 词 其 复制状态 终点[1].
        词 其 释放 态['lexical'].
        态 其 增 'lexical' 新词态.
        _放候 态.
        态 其 增 'pending' 假.
        态 其 增 'feed' 长.
        态 其 增 'readEnd' 长.
        态 其 增 'bytes' 长.
        态 其 增 'reusedBytes' (长-末).
        态 其 增 'converged' 真.
        窗 其 发送 柄 2032 长 0.
    另
        若 结果['done'] 则
            _放候 态.
            态 其 增 'pending' 假.
            (态['points']) 其 增 [末,(词 其 复制状态 态['lexical']),真].
        另
            点们 取 态['points'].
            末点 取 点们[(点们 其 量)-1].
            # Canonical window boundaries make lookahead state independent of
            # the event-capacity splits inside a native batch.
            若 末 == 态['readEnd'] 且 末-末点[0] >= 32768 则 点们 其 增 [末,(词 其 复制状态 态['lexical']),假]. 然
        然
    然
    若 (窗 其 发送 柄 2383 0 0) 其 数 != 0 则 卒 'Scintilla rejected a styling operation.'. 然
    得 空.
法
算 推进 柄 预算 为 数:
    态 取 _状态 柄.
    若 态 == 空 或 非 态['pending'] 或 态['inTick'] 则 得 假. 然
    若 _受限 柄 则 _失败 柄 态 'Large-file mode disables byte styles and folding.'. 得 假. 然
    若 预算 <= 0 或 预算 > 8 则 预算 取 8. 然
    起时 取 _时刻.
    态 其 增 'inTick' 真.
    窗 其 发送 柄 2382 0 0.
    试
        循
            块始 取 _时刻.
            _一步 柄 态.
            现在 取 _时刻.
            若 现在-块始 > 态['maxChunkMs'] 则 态 其 增 'maxChunkMs' (现在-块始). 然
            # Admit another non-preemptive chunk only if the latest measured
            # chunk cost still fits the remaining timer budget.
            若 非 态['pending'] 或 现在-起时+(现在-块始) >= 预算 则 破. 然
        环
    救 原因
        _失败 柄 态 (原因 为 句).
    终
    耗时 取 (_时刻)-起时.
    若 耗时 > 态['maxTickMs'] 则 态 其 增 'maxTickMs' 耗时. 然
    态 其 增 'inTick' 假.
    得 态['pending'].
法
算 待办 柄:
    态 取 _状态 柄.
    若 态 == 空 则 得 假. 然
    得 态['pending'].
法
算 状态 柄:
    态 取 _状态 柄.
    若 态 == 空 则 得 空. 然
    # Diagnostic projection: never expose the mutable scanner/checkpoint objects.
    得 {'enabled':(态['language'] == 'ru'),'language':态['language'],'warning':态['warning'],'pending':态['pending'],'generation':态['generation'],'revision':态['revision'],'feed':态['feed'],'bytes':态['bytes'],'points':(态['points'] 其 量),'chunks':态['chunks'],'readBytes':态['readBytes'],'restart':态['restart'],'maxRead':态['maxRead'],'maxTickMs':态['maxTickMs'],'maxChunkMs':态['maxChunkMs'],'editReadBytes':态['editReadBytes'],'reusedBytes':态['reusedBytes'],'converged':态['converged']}.
法
算 排空 柄:
    # Test hook only. Production calls 推进 once per timer message.
    循
        若 非 (推进 柄 8) 则 破. 然
    环
    得 状态 柄.
法
算 折叠 柄 位置 为 数:
    态 取 _状态 柄.
    若 态 == 空 或 态['language'] != 'ru' 或 态['pending'] 则 得 假. 然
    行 取 (窗 其 发送 柄 2166 位置 0) 其 数.
    层 取 (窗 其 发送 柄 2223 行 0) 其 数.
    若 层 < 8192 则 得 假. 然
    窗 其 发送 柄 2231 行 0.
    得 真.
法
算 全折 柄 动作 为 数:
    态 取 _状态 柄.
    若 态 == 空 或 态['language'] != 'ru' 或 态['pending'] 则 得 假. 然
    若 动作 < 0 或 动作 > 2 则 得 假. 然
    窗 其 发送 柄 2662 动作 0.
    得 真.
法

# Native fixture lifecycle hook; counts live application roots, not GC bytes.
算 存活上下文:
    得 词 其 存活上下文.
法
