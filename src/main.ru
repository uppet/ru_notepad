# ru_notepad 0.1.4 preview. Application behavior is compiled from Ru.
密 取 外言 '如:密'.
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
A 取 {'window':空,'instance':空,'tabs':空,'status':空,'docs':[],'active':-1,'ready':假,'search':假,'find':空,'replace':空,'next':空,'one':空,'all':空,'case':空,'hide':空,'counter':0,'wrap':假,'busy':假,'shutdownBlocked':假,'visible':假,'syntaxWarning':'','cancel':空,'operation':空,'queue':[],'locks':[],'cancelRequested':假,'inTick':假,'closeIndex':-1,'errors':[],'lastOutcome':'','lastReader':空,'lastWriter':空,'ticks':0,'syntaxTimer':假,'syntaxTick':假,'syntaxNext':0,'syntaxTicks':0,'syntaxWorkMs':0,'syntaxMaxTickMs':0,'syntaxGapMs':0,'syntaxMaxGapMs':0,'syntaxLastEndMs':0,'syntaxTextNotifications':0,'syntaxStyleNotifications':0,'syntaxFoldNotifications':0}.

# Syntax work is deferred out of Scintilla callbacks, with one shared UI budget.
算 所属文档 柄:
    文们 取 A 其 查 'docs'.
    位 取 0.
    循 文们 其 量 次
        若 ((文们[位] 其 查 'editor') 其 句) == (柄 其 句) 则 得 文们[位]. 然
        位 取 位+1.
    环
    得 空.
法
算 安排语法:
    若 非 (A 其 查 'ready') 或 (A 其 查 'syntaxTimer') 则 得 空. 然
    文们 取 A 其 查 'docs'.
    位 取 0.
    循 文们 其 量 次
        若 语 其 待办 (文们[位] 其 查 'editor') 则
            窗 其 成功 ((窗 其 SetTimer) 其 调用 [(A 其 查 'window'),902,10,空]) 'SetTimer(Ru syntax)'.
            A 其 增 'syntaxTimer' 真.
            # Do not count time between separate styling bursts as callback gaps.
            A 其 增 'syntaxLastEndMs' 0.
            得 空.
        然
        位 取 位+1.
    环
    得 空.
法
算 语法时钟:
    若 非 (A 其 查 'ready') 或 (A 其 查 'busy') 或 (A 其 查 'syntaxTick') 则 得 空. 然
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
        若 非 待续 则
            窗 其 结果 ((窗 其 KillTimer) 其 调用 [(A 其 查 'window'),902]).
            A 其 增 'syntaxTimer' 假.
        然
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
    救 原因
        A 其 增 'syntaxTick' 假.
        窗 其 结果 ((窗 其 KillTimer) 其 调用 [(A 其 查 'window'),902]).
        A 其 增 'syntaxTimer' 假.
        卒 原因.
    终
    A 其 增 'syntaxTick' 假.
    得 空.
法
算 当前:
    得 (A 其 查 'docs')[A 其 查 'active'].
法
算 编辑柄:
    得 当前 其 查 'editor'.
法
算 提示 文 为 句:
    得 窗 其 弹窗 (A 其 查 'window') 文 'ru_notepad' 64.
法
算 错误提示 文 为 句:
    (A 其 查 'errors') 其 增 文.
    若 A 其 查 'visible' 则 得 窗 其 弹窗 (A 其 查 'window') 文 'ru_notepad · could not finish' 16. 然
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
    若 (A 其 查 'busy') 或 任一已改 则
        文 取 密 其 UTF16 'ru_notepad has unsaved documents. Save or close them before signing out.'.
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
    若 文档 其 查 'large' 则 模式文 取 '    Large file · plain text'. 然
    语言名 取 语 其 名称 (文档 其 查 'language').
    语态 取 语 其 状态 (文档 其 查 'editor').
    若 语态 != 空 则
        若 非 语态['enabled'] 则 语言名 取 语 其 名称 'plain'. 然
        若 语态['warning'] != '' 则 模式文 取 模式文+'    '+语态['warning']. 然
        若 语态['pending'] 则 模式文 取 模式文+'    Styling Ru...'. 然
    然
    窗 其 标题 (A 其 查 'status') ('  '+(态 其 文本 (文档 其 查 'editor'))+'    '+编文+'    '+语言名+模式文).
    得 空.
法
算 移控 柄, 横, 纵, 宽, 高:
    若 宽 < 1 则 宽 取 1. 然
    若 高 < 1 则 高 取 1. 然
    窗 其 结果 ((窗 其 MoveWindow) 其 调用 [柄,横,纵,宽,高,1]).
    得 空.
法
算 布局:
    若 非 (A 其 查 'ready') 则 得 空. 然
    矩 取 (窗 其 RECT) 其 新建.
    窗 其 成功 ((窗 其 GetClientRect) 其 调用 (参 其 窗口二参 A 矩)) 'GetClientRect'.
    宽 取 (矩 其 读 'right') 其 数.
    高 取 (矩 其 读 'bottom') 其 数.
    矩 其 关闭.
    寻高 取 0.
    若 A 其 查 'search' 则 寻高 取 38. 然
    移控 (A 其 查 'tabs') 0 0 宽 30.
    状态宽 取 宽.
    若 A 其 查 'busy' 则 状态宽 取 宽-110. 然
    移控 (A 其 查 'status') 0 (高-25) 状态宽 25.
    移控 (A 其 查 'cancel') (宽-108) (高-25) 106 25.
    若 (A 其 查 'active') >= 0 则 移控 编辑柄 0 32 宽 (高-57-寻高). 然
    栏纵 取 高-25-38.
    输入宽 取 (宽-390)/2.
    若 输入宽 < 80 则 输入宽 取 80. 然
    # Window dimensions must be integer machine values.
    输入宽 取 输入宽-输入宽%1.
    移控 (A 其 查 'find') 8 (栏纵+5) 输入宽 26.
    移控 (A 其 查 'replace') (16+输入宽) (栏纵+5) 输入宽 26.
    起 取 24+输入宽*2.
    移控 (A 其 查 'case') 起 (栏纵+5) 48 26.
    移控 (A 其 查 'next') (起+50) (栏纵+5) 65 26.
    移控 (A 其 查 'one') (起+120) (栏纵+5) 74 26.
    移控 (A 其 查 'all') (起+199) (栏纵+5) 75 26.
    移控 (A 其 查 'hide') (起+279) (栏纵+5) 40 26.
    得 空.
法
算 寻栏 显示 为 事实:
    A 其 增 'search' 显示.
    模式 取 0.
    若 显示 则 模式 取 5. 然
    控们 取 ['find','replace','case','next','one','all','hide'].
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
# Tab ownership is committed only after initialization and native insertion succeed.
算 登记页 柄, 路 为 句, 编码, BOM, 戳 为 句, 身份 为 句, 大型 为 事实:
    文们 取 A 其 查 'docs'.
    若 (文们 其 量) >= 64 则 卒 'Up to 64 documents can be open. Close a tab and retry the remaining files.'. 然
    序 取 (A 其 查 'counter')+1.
    A 其 增 'counter' 序.
    名 取 短名 路.
    若 路 == '' 则 名 取 'Untitled '+(序 为 句). 然
    语言 取 'plain'.
    若 非 大型 则 语言 取 语 其 选择 柄 (语 其 识别 路). 然
    文档 取 {'editor':柄,'path':路,'name':名,'encoding':编码,'bom':BOM,'stamp':戳,'fileIdentity':身份,'encodingDirty':假,'label':'','wrap':假,'language':语言,'large':大型,'revision':0}.
    项 取 (窗 其 TCITEM) 其 新建.
    存 取 空.
    试
        存 取 密 其 UTF16 名.
        项 其 写 'mask' 1.
        项 其 写 'text' (存 其 地址).
        插位 取 (窗 其 发指 (A 其 查 'tabs') 4926 (文们 其 量) 项) 其 数.
        若 插位 == -1 则 卒 'Windows could not create the document tab.'. 然
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
    若 A 其 查 'busy' 则 卒 'Finish or cancel the current file operation first.'. 然
    若 ((A 其 查 'docs') 其 量) >= 64 则 卒 'Up to 64 documents can be open. Close a tab and retry.'. 然
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
    得 (窗 其 弹窗 (A 其 查 'window') ('This file is '+(大小 为 句)+' bytes, over 500 MB (500,000,000 bytes). Opening it may require several times its size in memory. It will use plain-text large-file mode. Continue?\n\nCancel stops between I/O chunks; a slow individual disk operation may still take time.') 'ru_notepad · large file' 292) == 6.
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
    若 A 其 查 'busy' 则 卒 'Finish or cancel the current file operation first.'. 然
    A 其 增 'busy' 真.
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
    A 其 增 'busy' 假.
    A 其 增 'cancelRequested' 假.
    窗 其 结果 ((窗 其 EnableWindow) 其 调用 [(A 其 查 'tabs'),1]).
    窗 其 结果 ((窗 其 ShowWindow) 其 调用 [(A 其 查 'cancel'),0]).
    布局.
    刷新.
    若 (A 其 查 'active') >= 0 则 窗 其 结果 ((窗 其 SetFocus) 其 调用 [编辑柄]). 然
    得 空.
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
    得 空.
法
算 入队 路们 为 句 阵, 代码页 为 数:
    若 A 其 查 'busy' 则 卒 'A file operation is already running. Finish or cancel it, then drop or open the files again.'. 然
    若 (路们 其 量) > 64 则 卒 'Select at most 64 paths at a time. No paths from this batch were opened.'. 然
    队 取 [].
    总 取 0.
    位 取 0.
    循 路们 其 量 次
        路 取 路们[位].
        若 路 != '' 则
            若 (路 其 量) > 32000 则 卒 'A selected path exceeds32000 characters. No files from this batch were opened.'. 然
            存 取 密 其 UTF16 路.
            长 取 ((存 其 大小)/2)-1.
            存 其 关闭.
            总 取 总+长+1.
            若 长 > 32000 或 总 > 2097152 则 卒 'The selected paths exceed the bounded path queue. No files from this batch were opened.'. 然
            队 其 增 [路,代码页].
        然
        位 取 位+1.
    环
    若 (队 其 量) == 0 则 得 假. 然
    A 其 增 'queue' 队.
    A 其 增 'lastOutcome' 'running'.
    试
        开始工作.
    救 原因
        A 其 增 'queue' ([]).
        卒 原因.
    终
    得 真.
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
    文们 取 A 其 查 'docs'.
    位 取 0.
    循 文们 其 量 次
        若 (文们[位] 其 查 'fileIdentity') == 读态['fileIdentity'] 则
            件编 其 关闭读取 读态.
            A 其 增 'operation' 空.
            切页 位.
            A 其 增 'lastOutcome' 'duplicate'.
            得 空.
        然
        位 取 位+1.
    环
    若 (文们 其 量) >= 64 则 卒 'Up to 64 documents can be open. Close tabs and retry the remaining files.'. 然
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
    若 A 其 查 'busy' 则 卒 'Finish or cancel the current file operation first.'. 然
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
    得 窗 其 文件对话 (A 其 查 'window') 真 原路.
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
            窗 其 标题 (A 其 查 'status') ('  Opening: '+(读态['position'] 为 句)+' / '+(读态['size'] 为 句)+' bytes · Cancel between chunks').
            得 空.
        然
        编 其 完成载入 操['load'].
        文档 取 登记页 操['editor'] 读态['path'] 读态['encoding'] 读态['bom'] 读态['stamp'] 读态['fileIdentity'] (读态['size'] >= (编 其 大文件模式字节)).
        # The tab now owns the native editor. Never destroy it in error cleanup.
        操 其 增 'editor' 空.
        A 其 增 'operation' 空.
        A 其 增 'lastOutcome' 'opened'.
        显 '[operation] open completed'.
        柄 取 文档 其 查 'editor'.
        (A 其 查 'locks') 其 增 [柄,0].
        窗 其 发送 柄 2171 1 0.
        窗 其 结果 ((窗 其 EnableWindow) 其 调用 [柄,0]).
        切页 (((A 其 查 'docs') 其 量)-1).
        得 空.
    然
    文档 取 操['doc'].
    若 (文档 其 查 'revision') != 操['revision'] 则 卒 'The document changed during saving. The staged save was cancelled.'. 然
    文 取 编 其 取文一步 操['source'].
    写态 取 操['writer'].
    若 文 != 空 则
        件编 其 写入一段 写态 文.
        窗 其 标题 (A 其 查 'status') ('  Saving: '+(操['source']['position'] 为 句)+' / '+(操['source']['bytes'] 为 句)+' UTF-8 bytes · Cancel between chunks').
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
        文档 其 增 'language' (语 其 选择 (文档 其 查 'editor') (语 其 识别 写态['path'])).
        安排语法.
    然
    刷新.
    若 后续 == 'tab' 则 删除当前页. 然
    若 后续 == 'app' 则 继续关闭. 然
    得 空.
法
算 工作时钟:
    若 非 (A 其 查 'busy') 或 (A 其 查 'inTick') 则 得 空. 然
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
        操 取 A 其 查 'operation'.
        为保存 取 操 != 空 且 操['kind'] == 'save'.
        报错 取 [原因].
        试 清操作. 救 清因 报错[0] 取 报错[0]+'\n'+清因. 终
        A 其 增 'lastOutcome' 'failed'.
        A 其 增 'closeIndex' (-1).
        若 为保存 则
            A 其 增 'queue' ([]).
            结束工作.
        然
        错误提示 报错[0].
    终
    A 其 增 'inTick' 假.
    得 空.
法
算 询问关闭 文档:
    得 窗 其 弹窗 (A 其 查 'window') ('Save changes to '+(文档 其 查 'name')+'?') 'ru_notepad · unsaved changes' 35.
法
算 删除当前页:
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
    得 真.
法
算 关页:
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
    窗 其 结果 ((窗 其 KillTimer) 其 调用 [(A 其 查 'window'),902]).
    A 其 增 'syntaxTimer' 假.
    位 取 0.
    循 文们 其 量 次
        语 其 遗忘 (文们[位] 其 查 'editor').
        位 取 位+1.
    环
    窗 其 成功 ((窗 其 DestroyWindow) 其 调用 [A 其 查 'window']) 'DestroyWindow(main)'.
    得 真.
法
算 关程序:
    若 A 其 查 'busy' 则 A 其 增 'cancelRequested' 真. 得 假. 然
    A 其 增 'closeIndex' 0.
    得 继续关闭.
法
算 命令 号:
    若 号 == 901 则
        若 A 其 查 'busy' 则 A 其 增 'cancelRequested' 真. 然
        得 空.
    然
    若 A 其 查 'busy' 则 得 空. 然
    若 号 == 101 则 新页 '' '' 65001 假 ''. 得 空. 然
    若 号 == 102 或 号 == 108 或 号 == 109 则
        代码页 取 0.
        若 号 == 108 则 代码页 取 1252. 然
        若 号 == 109 则 代码页 取 936. 然
        打开 (窗 其 文件对话 (A 其 查 'window') 假 '') 代码页.
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
    若 号 == 303 或 号 == 304 或 号 == 305 则
        词 取 窗 其 取文 (A 其 查 'find').
        新文 取 窗 其 取文 (A 其 查 'replace').
        区分 取 非 ((窗 其 发送 (A 其 查 'case') 240 0 0) 其 为空).
        若 词 == '' 则 寻栏 真. 得 空. 然
        若 号 == 303 则
            若 (编 其 下个 编辑柄 词 区分) == -1 则 提示 'No match found.'. 然
        然
        若 号 == 304 则
            若 (编 其 换当前 编辑柄 词 新文 区分) == -1 则 提示 'No further match found.'. 然
        然
        若 号 == 305 则
            次数 取 编 其 全换 编辑柄 词 新文 区分.
            提示 ((次数 为 句)+' replacements. Undo restores the entire operation.').
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
    若 (号 == 501 或 (号 >= 702 且 号 <= 704)) 且 (当前 其 查 'large') 则 提示 'Large-file mode keeps wrapping and syntax colouring disabled to bound memory and layout cost.'. 得 空. 然
    若 号 >= 701 且 号 <= 704 则
        语言 取 'plain'.
        若 号 == 702 则 语言 取 'cpp'. 然
        若 号 == 703 则 语言 取 'json'. 然
        若 号 == 704 则 语言 取 'ru'. 然
        若 语言 == (当前 其 查 'language') 则
            若 语言 != 'ru' 则 得 空. 然
            语态 取 语 其 状态 编辑柄.
            若 语态 != 空 且 语态['enabled'] 则 得 空. 然
        然
        当前 其 增 'language' (语 其 选择 编辑柄 语言).
        安排语法.
        报语法警告.
    然
    若 号 == 505 或 号 == 506 则
        若 (当前 其 查 'language') == 'ru' 且 非 (当前 其 查 'large') 则
            若 语 其 待办 编辑柄 则 提示 'Ru syntax is still being updated. Folding will be available when styling finishes.'. 得 空. 然
            动作 取 0.
            若 号 == 506 则 动作 取 1. 然
            语 其 全折 编辑柄 动作.
        然
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
        若 (窗 其 弹窗 (A 其 查 'window') 'Register this portable copy as an Open With / Default Apps candidate for this Windows user? Windows will still ask you to choose defaults. Unregister at the old location before moving, then register the new copy.' 'ru_notepad · register candidate' 292) == 6 则
            关联 其 注册.
            提示 'Registered this copy. Open Settings > Default apps to choose the file types you want. Before moving the portable folder, unregister this copy; register again at the new location.'.
        然
    然
    若 号 == 802 则 关联 其 打开设置 (A 其 查 'window'). 然
    若 号 == 803 则
        若 (窗 其 弹窗 (A 其 查 'window') 'Remove this copy from Open With / Default Apps candidates? Your Windows default choices will not be overwritten.' 'ru_notepad · unregister candidate' 292) == 6 则 关联 其 注销. 提示 'Candidate entries owned by this copy were removed.'. 然
    然
    若 号 == 804 则 提示 ('Registration status: '+(关联 其 查询状态)+'\nregistered = this copy; none = not registered; partial = incomplete; otherowner = another portable location. Unregister at the old location before moving, then register the new copy.'). 然
    若 号 == 601 则 提示 'ru_notepad 0.1.4 preview\n\nWindows x64 · application logic compiled from Ru\nScintilla + Lexilla native editor components\n\nTabs, safe text saves, undo/redo, literal find/replace.\nBounded streaming, 64 tabs; over 500 MB asks first. Not full Notepad++ parity yet.\nNo Python runtime. No telemetry. No network features.'. 然
    刷新.
    得 空.
法
算 菜单:
    主 取 窗 其 成功 ((窗 其 CreateMenu) 其 调用 []) 'CreateMenu'.
    组们 取 [
        ['&File',[[101,'&New\tCtrl+N'],[102,'&Open...\tCtrl+O'],[108,'Open as Windows-1252...'],[109,'Open as GBK (CP936)...'],[103,'&Save\tCtrl+S'],[104,'Save &As...\tCtrl+Shift+S'],[105,'&Close tab\tCtrl+W'],[111,'Previous tab\tCtrl+Shift+Tab'],[112,'Next tab\tCtrl+Tab'],[106,'E&xit']]],
        ['&Edit',[[201,'&Undo\tCtrl+Z'],[202,'&Redo\tCtrl+Y'],[203,'Cu&t\tCtrl+X'],[204,'&Copy\tCtrl+C'],[205,'&Paste\tCtrl+V'],[206,'Select &All\tCtrl+A']]],
        ['&Search',[[301,'&Find...\tCtrl+F'],[302,'&Replace...\tCtrl+H'],[303,'Find &Next\tF3']]],
        ['E&ncoding',[[401,'Save as UTF-8'],[402,'Save as UTF-8 with BOM'],[403,'Save as UTF-16 LE'],[404,'Save as UTF-16 BE'],[405,'Save as Windows-1252'],[406,'Save as GBK (CP936)']]],
        ['&Language',[[701,'Plain text'],[702,'C / C++'],[703,'JSON'],[704,'Ru / 如言']]],
        ['&View',[[501,'Toggle word &wrap'],[502,'Zoom &in\tCtrl++'],[503,'Zoom &out\tCtrl+-'],[504,'Reset zoom\tCtrl+0'],[505,'Collapse all Ru folds\tCtrl+Shift+['],[506,'Expand all Ru folds\tCtrl+Shift+]']]],
        ['&Settings',[[801,'Register Open With candidate...'],[802,'Choose defaults in Windows Settings...'],[803,'Unregister this copy...'],[804,'Registration status']]],
        ['&Help',[[601,'&About ru_notepad']]]
    ].
    组位 取 0.
    循 组们 其 量 次
        组 取 组们[组位].
        子 取 窗 其 成功 ((窗 其 CreatePopupMenu) 其 调用 []) 'CreatePopupMenu'.
        项位 取 0.
        项们 取 组[1].
        循 项们 其 量 次
            项 取 项们[项位].
            窗 其 菜单项 子 0 项[0] 项[1].
            项位 取 项位+1.
        环
        窗 其 菜单项 主 16 ((窗 其 UP) 其 重释 子) 组[0].
        组位 取 组位+1.
    环
    窗 其 成功 ((窗 其 SetMenu) 其 调用 (参 其 菜单参数 A 主)) 'SetMenu'.
    得 空.
法
算 消息处理 柄, 号值, 宽参, 长参:
    号 取 号值 其 数.
    若 号 == 129 则 A 其 增 'window' 柄. 然
    若 号 == 2 则
        窗 其 结果 ((窗 其 PostQuitMessage) 其 调用 [0]).
        得 0.
    然
    若 A 其 查 'ready' 则
        试
            若 号 == 17 则 得 关机会话. 然
            若 号 == 275 且 (宽参 其 数) == 901 则 工作时钟. 得 0. 然
            若 号 == 275 且 (宽参 其 数) == 902 则 语法时钟. 得 0. 然
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
                若 A 其 查 'busy' 则 得 0. 然
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
        卒 ('Cannot load Scintilla.dll (Windows error '+((预载成果 其 错误码) 为 句)+'). Extract the complete Windows x64 package and keep its DLL beside ru_notepad.exe.').
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
    A 其 增 'cancel' (窗 其 控制 主窗 实例 'BUTTON' 'Cancel (Esc)' 1073807360 901).
    A 其 增 'find' (窗 其 控制 主窗 实例 'EDIT' '' 1082196096 310).
    A 其 增 'replace' (窗 其 控制 主窗 实例 'EDIT' '' 1082196096 311).
    A 其 增 'case' (窗 其 控制 主窗 实例 'BUTTON' 'Aa' 1073807363 306).
    窗 其 发送 (A 其 查 'case') 241 1 0.
    A 其 增 'next' (窗 其 控制 主窗 实例 'BUTTON' 'Next' 1073807360 303).
    A 其 增 'one' (窗 其 控制 主窗 实例 'BUTTON' 'Replace' 1073807360 304).
    A 其 增 'all' (窗 其 控制 主窗 实例 'BUTTON' 'All' 1073807360 305).
    A 其 增 'hide' (窗 其 控制 主窗 实例 'BUTTON' 'X' 1073807360 307).
    显 '[startup] controls created'.
    菜单.
    显 '[startup] menu installed'.
    A 其 增 'ready' 真.
    新页 '' '' 65001 假 ''.
    显 '[startup] initial document ready'.
    拖放 其 启用 主窗.
    若 显示 则
        窗 其 结果 ((窗 其 ShowWindow) 其 调用 [主窗,5]).
        窗 其 结果 ((窗 其 UpdateWindow) 其 调用 [主窗]).
        显 '[startup] main window shown'.
        报语法警告.
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

算 元初 参数 为 句 阵:
    显 '[startup] Ru application modules loaded'.
    试
        初始化 参数 真.
    救 原因
        显 '[startup] initialization failed'.
        窗 其 弹窗 空 原因 'ru_notepad · startup failed' 16.
        得 1.
    终
    消息 取 (窗 其 MSG) 其 新建.
    退出码 取 0.
    试
        循
            成果 取 (窗 其 GetMessageW) 其 调用 [消息,空,0,0].
            码 取 (窗 其 结果 成果) 其 数.
            若 码 == -1 则 卒 'GetMessageW failed.'. 然
            若 码 == 0 则
                退出码 取 (消息 其 读 'wParam') 其 数.
                若 退出码 != 0 则 卒 'The native callback failure handler stopped the event loop.'. 然
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
    救 原因
        # A native callback failure is contained, but application state cannot
        # be assumed resumable. Never silently overwrite files during recovery.
        A 其 增 'ready' 假.
        窗 其 弹窗 空 ('A fatal internal error stopped ru_notepad. Unsaved changes may be lost; this preview has no crash recovery. No emergency save will be attempted. If this happened during Save, check the target and any temporary/recovery files.\n\n'+原因) 'ru_notepad · fatal error' 16.
        得 1.
    终
    得 退出码.
法
