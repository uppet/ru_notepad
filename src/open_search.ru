# Read-only literal search of the current open buffers. All positions are UTF-8
# bytes. No retained native pointers, whole-document copies, or disk reads.
密 取 外言 '如:密'.
窗 取 外言 'win32.ru'.
编 取 外言 'editor.ru'.
标 取 外言 'search_history.ru'.
_查型 取 密 其 结构 [['start',窗 其 IP],['end',窗 其 IP],['text',窗 其 PTR],['foundStart',窗 其 IP],['foundEnd',窗 其 IP]].
候选上限 取 65536.
每步上限 取 16.
结果上限 取 2000.
词上限 取 1024.

算 新建 文档们, 词 为 句, 区分 为 事实, 整词 为 事实:
    态 取 {'status':'running','results':[],'processed':0,'documentCount':(文档们 其 量),'documents':[],'documentIndex':0,'position':0,'query':词,'flags':0,'overlap':4096,'error':'','lastCandidateBytes':0,'lastResultCount':0}.
    若 词 == '' 或 (词 其 量) > 词上限 则
        态 其 增 'status' 'failed'. 态 其 增 'error' 'Query must contain 1 to 1024 Unicode scalars.'. 得 态.
    然
    # FINDTEXTFULL takes a NUL-terminated UTF-8 string; never truncate a query.
    位 取 0.
    循 词 其 量 次
        若 词[位] < '' 则 态 其 增 'status' 'failed'. 态 其 增 'error' 'NUL is not supported in a search query.'. 得 态. 然
        位 取 位+1.
    环
    标记 取 0.
    若 区分 则 标记 取 4.
    另 态 其 增 'overlap' 12288. 然
    若 整词 则 标记 取 标记+2. 然
    态 其 增 'flags' 标记.
    试
        位 取 0.
        循 文档们 其 量 次
            文 取 文档们[位]. 柄 取 文['editor'].
            长 取 (窗 其 发送 柄 2183 0 0) 其 数.
            编 其 检查状态 柄.
            态['documents'] 其 增 {'untitledNumber':文['untitledNumber'],'editorIdentity':(柄 其 句),'revision':文['revision'],'length':长,'name':文['name'],'path':文['path']}.
            位 取 位+1.
        环
        若 (文档们 其 量) == 0 则 态 其 增 'status' 'complete'. 然
    救 原因
        态 其 增 'status' 'failed'. 态 其 增 'error' 'Open-buffer search could not continue.'.
    终
    得 态.
法

# Check the entire buffer set before dereferencing ANY live native handle.
# Reordering is harmless. Add/remove/reopen/edit invalidates the whole snapshot.
算 _位置 快照 文档们:
    位 取 0.
    循 文档们 其 量 次
        文 取 文档们[位].
        若 文['untitledNumber'] == 快照['untitledNumber'] 且 (文['editor'] 其 句) == 快照['editorIdentity'] 则 得 位. 然
        位 取 位+1.
    环
    得 -1.
法
算 _有效 态 文档们:
    若 态['status'] == 'stale' 则 得 假. 然
    若 (文档们 其 量) != 态['documentCount'] 则 态 其 增 'status' 'stale'. 得 假. 然
    位们 取 []. 位 取 0.
    循 态['documentCount'] 次
        快照 取 态['documents'][位]. 索引 取 _位置 快照 文档们.
        若 索引 < 0 则 态 其 增 'status' 'stale'. 得 假. 然
        若 文档们[索引]['revision'] != 快照['revision'] 则 态 其 增 'status' 'stale'. 得 假. 然
        位们 其 增 索引. 位 取 位+1.
    环
    位 取 0.
    循 态['documentCount'] 次
        柄 取 文档们[位们[位]]['editor'].
        若 (窗 其 发送 柄 2183 0 0) 其 数 != 态['documents'][位]['length'] 则 态 其 增 'status' 'stale'. 得 假. 然
        编 其 检查状态 柄.
        位 取 位+1.
    环
    得 真.
法
算 取消 态:
    若 态['status'] == 'running' 则 态 其 增 'status' 'cancelled'. 然
    得 态.
法
算 _边界 柄 位 长:
    若 位 >= 长 则 得 长. 然
    得 (窗 其 发送 柄 2417 (位+1) 0) 其 数.
法
算 _搜 柄 词 标记 始 末:
    存 取 空. 范围 取 空.
    试
        存 取 密 其 UTF8 词.
        范围 取 _查型 其 新建.
        范围 其 写 'start' 始. 范围 其 写 'end' 末.
        范围 其 写 'text' (存 其 地址).
        位 取 (窗 其 发指 柄 2196 标记 范围) 其 数.
        编 其 检查状态 柄.
        尾 取 -1.
        若 位 >= 0 则 尾 取 (范围 其 读 'foundEnd') 其 数. 然
    救 原因
        若 范围 != 空 则 范围 其 关闭. 然
        若 存 != 空 则 存 其 关闭. 然
        卒 原因.
    终
    范围 其 关闭. 存 其 关闭.
    得 [位,尾].
法
算 _下一文档 态:
    态 其 增 'processed' (态['processed']+1).
    态 其 增 'documentIndex' (态['documentIndex']+1).
    态 其 增 'position' 0.
    若 态['processed'] == 态['documentCount'] 则 态 其 增 'status' 'complete'. 然
    得 态.
法
算 步进 态 文档们:
    若 态['status'] != 'running' 则 得 态. 然
    态 其 增 'lastCandidateBytes' 0. 态 其 增 'lastResultCount' 0.
    试
        若 非 (_有效 态 文档们) 则 得 态. 然
        快照 取 态['documents'][态['documentIndex']].
        索引 取 _位置 快照 文档们. 柄 取 文档们[索引]['editor'].
        长 取 快照['length']. 始 取 态['position'].
        若 始 >= 长 则 得 _下一文档 态. 然
        界 取 _边界 柄 (始+候选上限) 长.
        # Pinned Scintilla CaseConvert.cxx folds each scalar into 1..3 scalars.
        # Each document scalar folds to >=1 scalar, hence a 1024-scalar query
        # can match <=3072 document scalars, <=12288 UTF-8 bytes. Case-sensitive
        # literals need only 4096. Never assume folded match length equals query.
        末 取 _边界 柄 (界+态['overlap']) 长.
        态 其 增 'lastCandidateBytes' (界-始).
        循 每步上限 次
            中 取 _搜 柄 态['query'] 态['flags'] 始 末.
            若 中[0] < 0 或 中[0] >= 界 则 态 其 增 'position' 界. 破. 然
            若 中[0] < 始 或 中[1] <= 中[0] 或 中[1] > 末 则 卒 'Invalid native search result.'. 然
            行 取 (窗 其 发送 柄 2166 中[0] 0) 其 数.
            预末 取 _边界 柄 (中[0]+240) 长.
            预览 取 _标签 (编 其 _范围文本 柄 中[0] 预末).
            态['results'] 其 增 {'untitledNumber':快照['untitledNumber'],'editorIdentity':快照['editorIdentity'],'revision':快照['revision'],'start':中[0],'end':中[1],'line':(行+1),'preview':预览,'name':快照['name'],'path':快照['path']}.
            态 其 增 'lastResultCount' (态['lastResultCount']+1).
            始 取 中[1]. 态 其 增 'position' 始.
            若 (态['results'] 其 量) >= 结果上限 则 态 其 增 'status' 'limited'. 破. 然
            若 始 >= 界 则 破. 然
        环
        若 态['status'] == 'running' 且 态['position'] >= 长 则 _下一文档 态. 然
    救 原因
        态 其 增 'status' 'failed'. 态 其 增 'error' 'Open-buffer search could not continue.'.
    终
    得 态.
法

# Called only by an explicit result activation, never by a timer or rendering.
算 定位 态 结果索引 文档们:
    若 态['status'] == 'stale' 或 态['status'] == 'failed' 则 得 -1. 然
    若 结果索引 < 0 或 结果索引 >= (态['results'] 其 量) 则 得 -1. 然
    试
        若 非 (_有效 态 文档们) 则 得 -1. 然
        项 取 态['results'][结果索引]. 索引 取 _位置 项 文档们.
        若 索引 < 0 则 态 其 增 'status' 'stale'. 得 -1. 然
        柄 取 文档们[索引]['editor'].
        起行 取 (窗 其 发送 柄 2166 项['start'] 0) 其 数.
        末行 取 (窗 其 发送 柄 2166 项['end'] 0) 其 数.
        窗 其 发送 柄 2232 起行 0.
        窗 其 发送 柄 2232 末行 0.
        窗 其 发送 柄 2160 项['start'] 项['end'].
        窗 其 发送 文档们[索引]['editor'] 2169 0 0.
        得 索引.
    救 原因
        态 其 增 'status' 'failed'. 态 其 增 'error' 'Open-buffer search could not continue.'.
    终
    得 -1.
法
# LISTBOX is not a mnemonic surface: undo only the menu-specific ampersand
# doubling while retaining the shared bounded control/bidi escaping policy.
算 _标签 文:
    转 取 标 其 标签 文. 果 取 ''. 位 取 0.
    循
        若 位 >= (转 其 量) 则 破. 然
        字 取 转[位].
        若 字 == ' ' 或 字 == ' ' 则 果 取 果+'␊'.
        另 果 取 果+字. 然
        位 取 位+1.
        若 字 == '&' 则 位 取 位+1. 然
    环
    得 果.
法
算 行标签 项:
    名 取 (_标签 项['name'])+' ['+(项['untitledNumber'] 为 句)+']'.
    若 项['path'] != '' 则 名 取 名+' ('+(_标签 项['path'])+')'. 然
    得 名+' : '+(项['line'] 为 句)+' : '+项['preview'].
法
