# Scintilla owns its native text buffer, rendering, selection and undo history.
# This Ru module owns editor policy and search/replace command behavior.
本地 取 外言 'i18n.ru'.
密 取 外言 '如:密'.
窗 取 外言 'win32.ru'.
_范围型 取 密 其 结构 [['start',窗 其 IP],['end',窗 其 IP],['text',窗 其 PTR]].
_块长 取 65536.
大文件模式字节 取 32000000.

算 创建 父, 实例, 号:
    柄 取 窗 其 控制 父 实例 'Scintilla' '' 1073807360 号.
    试
        _新文档 柄 假.
        窗 其 发送 柄 2037 65001 0. # SCI_SETCODEPAGE UTF-8
        窗 其 发文 柄 2056 32 'Consolas'.
        窗 其 发送 柄 2055 32 11.
        窗 其 发送 柄 2051 32 2039583. # charcoal foreground
        窗 其 发送 柄 2052 32 16777215.
        窗 其 发送 柄 2050 0 0. # STYLECLEARALL
        窗 其 发送 柄 2240 0 1. # line-number margin
        窗 其 发送 柄 2242 0 56.
        窗 其 发送 柄 2051 33 8947848.
        窗 其 发送 柄 2052 33 16448250.
        窗 其 发送 柄 2036 4 0.
        窗 其 发送 柄 2124 0 0. # spaces for indentation
        窗 其 发送 柄 2132 1 0. # indentation guides
        窗 其 发送 柄 2122 4 0.
        窗 其 发送 柄 2031 0 0. # CRLF for new lines
        窗 其 发送 柄 2563 0 0. # no multiple selection yet
    救 原因
        窗 其 结果 ((窗 其 DestroyWindow) 其 调用 [柄]).
        卒 原因.
    终
    得 柄.
法
算 检查状态 柄:
    码 取 (窗 其 发送 柄 2383 0 0) 其 数.
    若 码 != 0 则 卒 (本地 其 格式 'error.editor.status' ([(码 为 句)])). 然
    得 空.
法
算 _新文档 柄 大文件 为 事实:
    选项 取 256. # SC_DOCUMENTOPTION_TEXT_LARGE: 64-bit text positions.
    若 大文件 则 选项 取 257. 然 # additionally STYLES_NONE
    窗 其 发送 柄 2382 0 0.
    文档 取 窗 其 发送 柄 2375 0 选项.
    若 文档 其 为空 则 卒 (本地 其 文本 'error.editor.memory'). 然
    试
        窗 其 发送 柄 2358 0 文档.
        检查状态 柄.
        若 (窗 其 发送 柄 2357 0 0) 其 句 != 文档 其 句 则 卒 (本地 其 文本 'error.editor.attach'). 然
    救 原因
        窗 其 发送 柄 2377 0 文档.
        卒 原因.
    终
    # CREATEDOCUMENT grants one ref; SETDOCPOINTER grants the window another.
    窗 其 发送 柄 2377 0 文档.
    窗 其 发送 柄 2037 65001 0.
    得 空.
法

算 开始载入 柄 大小 为 数:
    _新文档 柄 (大小 >= 大文件模式字节).
    窗 其 发送 柄 2160 0 0.
    窗 其 发送 柄 2012 0 0. # no undo copies for the uncommitted hidden document
    窗 其 发送 柄 2382 0 0.
    得 {'editor':柄,'bytes':0,'crlf':假,'lf':假,'cr':假,'tailCR':假,'done':假}.
法

算 _范围文本 柄 始 为 数 末 为 数:
    长 取 末-始.
    若 长 < 0 或 长 > _块长*4 则 卒 'Invalid bounded editor text range.'. 然
    存 取 密 其 缓冲 (长+1).
    范围 取 _范围型 其 新建.
    试
        范围 其 写 'start' 始.
        范围 其 写 'end' 末.
        范围 其 写 'text' (存 其 地址).
        窗 其 发送 柄 2382 0 0.
        实长 取 (窗 其 发指 柄 2039 0 范围) 其 数.
        若 实长 != 长 则 卒 (本地 其 文本 'error.editor.incomplete_text'). 然
        检查状态 柄.
        零长 取 (窗 其 结果 ((窗 其 lstrlenA) 其 调用 [存])) 其 数.
        若 零长 != 长 则 卒 (本地 其 文本 'error.editor.nul'). 然
        若 长 > 0 则
            验 取 窗 其 结果 ((窗 其 MultiByteToWideChar) 其 调用 [65001,8,存,长,空,0]).
            若 验 其 为空 则 卒 (本地 其 文本 'error.editor.invalid_utf8'). 然
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

算 追加文本 流态 文 为 句:
    若 流态['done'] 则 卒 'The pending document is already complete.'. 然
    若 文 其 量 > _块长 则 卒 'An editor load chunk exceeds the bounded streaming contract.'. 然
    若 文 == '' 则 得 空. 然
    柄 取 流态['editor'].
    旧长 取 流态['bytes'].
    若 (窗 其 发送 柄 2183 0 0) 其 数 != 旧长 则 卒 (本地 其 文本 'error.editor.load_changed'). 然
    存 取 密 其 UTF8 文.
    长 取 (存 其 大小)-1.
    试
        窗 其 发送 柄 2382 0 0.
        窗 其 发指 柄 2001 长 存.
        检查状态 柄.
    救 原因
        存 其 关闭.
        卒 原因.
    终
    存 其 关闭.
    若 (窗 其 发送 柄 2183 0 0) 其 数 != 旧长+长 则 卒 (本地 其 文本 'error.editor.load_incomplete'). 然
    若 (_范围文本 柄 旧长 (旧长+长)) != 文 则 卒 (本地 其 文本 'error.editor.load_mismatch'). 然
    流态 其 增 'bytes' (旧长+长).
    若 (文 其 含 '\r\n') 或 (流态['tailCR'] 且 文[0] == '\n') 则 流态 其 增 'crlf' 真. 然
    若 文 其 含 '\n' 则 流态 其 增 'lf' 真. 然
    若 文 其 含 '\r' 则 流态 其 增 'cr' 真. 然
    流态 其 增 'tailCR' (文[文 其 量-1] == '\r').
    得 空.
法

算 完成载入 流态:
    若 流态['done'] 则 得 流态. 然
    柄 取 流态['editor'].
    检查状态 柄.
    若 (窗 其 发送 柄 2183 0 0) 其 数 != 流态['bytes'] 则 卒 (本地 其 文本 'error.editor.commit_changed'). 然
    模式 取 0.
    若 非 流态['crlf'] 则
        若 流态['lf'] 则 模式 取 2. 另
            若 流态['cr'] 则 模式 取 1. 然
        然
    然
    窗 其 发送 柄 2031 模式 0.
    窗 其 发送 柄 2175 0 0.
    窗 其 发送 柄 2012 1 0.
    窗 其 发送 柄 2014 0 0.
    窗 其 发送 柄 2160 0 0.
    检查状态 柄.
    流态 其 增 'done' 真.
    得 流态.
法

算 开始取文 柄:
    检查状态 柄.
    得 {'editor':柄,'bytes':(窗 其 发送 柄 2183 0 0) 其 数,'position':0,'document':(窗 其 发送 柄 2357 0 0) 其 句,'done':假}.
法

算 取文一步 流态:
    若 流态['done'] 则 得 空. 然
    柄 取 流态['editor'].
    长 取 流态['bytes'].
    若 (窗 其 发送 柄 2183 0 0) 其 数 != 长 或 (窗 其 发送 柄 2357 0 0) 其 句 != 流态['document'] 则 卒 (本地 其 文本 'error.editor.save_changed'). 然
    始 取 流态['position'].
    若 始 == 长 则 流态 其 增 'done' 真. 得 空. 然
    末 取 始+_块长.
    若 末 >= 长 则
        末 取 长.
    另
        # PositionBefore(end+1) rounds down at a UTF-8/CRLF boundary.
        末 取 (窗 其 发送 柄 2417 (末+1) 0) 其 数.
    然
    若 末 <= 始 或 末-始 > _块长 则 卒 'The editor returned an invalid text boundary.'. 然
    文 取 _范围文本 柄 始 末.
    流态 其 增 'position' 末.
    得 文.
法

算 流文本 柄:
    流态 取 开始取文 柄.
    得 算: 得 取文一步 流态. 法.
法

算 验文本 文 为 句:
    位 取 0.
    循
        若 位 >= 文 其 量 则 破. 然
        末 取 位+_块长.
        若 末 > 文 其 量 则 末 取 文 其 量. 然
        存 取 密 其 UTF8 文[位:末].
        存 其 关闭.
        位 取 末.
    环
    得 空.
法

算 文本 柄:
    # Explicit SMALL compatibility API, never the production document save path.
    若 (窗 其 发送 柄 2183 0 0) 其 数 > 1048576 则 卒 'Whole-string text extraction is only for small callers; use the bounded editor cursor.'. 然
    流态 取 开始取文 柄.
    文 取 ''.
    循
        段 取 取文一步 流态.
        若 段 == 空 则 破. 然
        文 取 文+段.
    环
    得 文.
法

算 设文本 柄 文 为 句:
    # Compatibility setter preserves this document's lexer and configuration.
    # Production opening uses a distinct hidden document via 开始载入 instead.
    验文本 文.
    窗 其 发送 柄 2382 0 0.
    窗 其 发送 柄 2012 0 0.
    流态 取 {'editor':柄,'bytes':0,'crlf':假,'lf':假,'cr':假,'tailCR':假,'done':假}.
    试
        窗 其 发送 柄 2004 0 0.
        检查状态 柄.
        窗 其 发送 柄 2160 0 0.
        位 取 0.
        循
            若 位 >= 文 其 量 则 破. 然
            末 取 位+_块长.
            若 末 > 文 其 量 则 末 取 文 其 量. 然
            追加文本 流态 文[位:末].
            位 取 末.
        环
        完成载入 流态.
    救 原因
        窗 其 发送 柄 2012 1 0.
        卒 原因.
    终
    得 空.
法
算 已变 柄:
    得 非 ((窗 其 发送 柄 2159 0 0) 其 为空).
法
算 记保存 柄:
    窗 其 发送 柄 2014 0 0.
    得 空.
法
算 搜区 柄, 词 为 句, 始 为 数, 末 为 数, 区分 为 事实:
    得 搜区选项 柄 词 始 末 区分 假.
法
算 搜区选项 柄, 词 为 句, 始 为 数, 末 为 数, 区分 为 事实, 整词 为 事实:
    若 词 == '' 则 卒 (本地 其 文本 'error.editor.find_empty'). 然
    存 取 密 其 UTF8 词.
    窗 其 发送 柄 2382 0 0.
    标记 取 0.
    若 区分 则 标记 取 4. 然
    若 整词 则 标记 取 标记+2. 然 # SCFIND_WHOLEWORD; native word-character rules.
    窗 其 发送 柄 2198 标记 0.
    窗 其 发送 柄 2190 始 0.
    窗 其 发送 柄 2192 末 0.
    位 取 (窗 其 发指 柄 2197 ((存 其 大小)-1) 存) 其 数.
    存 其 关闭.
    检查状态 柄.
    得 位.
法
# Existing callers retain forward, wrapping, non-whole-word behavior.
算 下个 柄, 词 为 句, 区分 为 事实:
    得 寻找 柄 词 区分 假 真 假.
法
算 寻找 柄, 词 为 句, 区分 为 事实, 整词 为 事实, 循环 为 事实, 向后 为 事实:
    始 取 (窗 其 发送 柄 2145 0 0) 其 数. # GETSELECTIONEND
    长 取 (窗 其 发送 柄 2183 0 0) 其 数.
    末界 取 长.
    若 向后 则
        始 取 (窗 其 发送 柄 2143 0 0) 其 数. # GETSELECTIONSTART, independent of selection direction.
        末界 取 0.
    然
    位 取 搜区选项 柄 词 始 末界 区分 整词.
    若 位 == -1 且 循环 则
        若 向后 则
            若 始 < 长 则 位 取 搜区选项 柄 词 长 始 区分 整词. 然
        另
            若 始 > 0 则 位 取 搜区选项 柄 词 0 始 区分 整词. 然
        然
    然
    若 位 != -1 则
        末 取 (窗 其 发送 柄 2193 0 0) 其 数.
        # Unfold both endpoints before scrolling. Searching never edits text.
        行 取 (窗 其 发送 柄 2166 位 0) 其 数.
        终行 取 (窗 其 发送 柄 2166 末 0) 其 数.
        窗 其 发送 柄 2232 行 0. # ENSUREVISIBLE
        窗 其 发送 柄 2232 终行 0.
        窗 其 发送 柄 2160 位 末.
        窗 其 发送 柄 2169 0 0.
    然
    得 位.
法
算 换当前 柄, 词 为 句, 新文 为 句, 区分 为 事实:
    得 换当前选项 柄 词 新文 区分 假 真.
法
算 换当前选项 柄, 词 为 句, 新文 为 句, 区分 为 事实, 整词 为 事实, 循环 为 事实:
    始 取 (窗 其 发送 柄 2143 0 0) 其 数.
    末 取 (窗 其 发送 柄 2145 0 0) 其 数.
    命中 取 搜区选项 柄 词 始 末 区分 整词.
    若 命中 == 始 且 ((窗 其 发送 柄 2193 0 0) 其 数) == 末 则
        存 取 密 其 UTF8 新文.
        窗 其 发送 柄 2382 0 0.
        已换 取 (窗 其 发指 柄 2194 ((存 其 大小)-1) 存) 其 数.
        预换 取 (存 其 大小)-1.
        存 其 关闭.
        检查状态 柄.
        若 已换 != 预换 则 卒 (本地 其 文本 'error.editor.replace_incomplete'). 然
        新末 取 (窗 其 发送 柄 2193 0 0) 其 数.
        窗 其 发送 柄 2160 新末 新末.
    然
    得 寻找 柄 词 区分 整词 循环 假.
法
算 全换 柄, 词 为 句, 新文 为 句, 区分 为 事实:
    得 全换选项 柄 词 新文 区分 假.
法
算 全换选项 柄, 词 为 句, 新文 为 句, 区分 为 事实, 整词 为 事实:
    若 词 == '' 则 卒 (本地 其 文本 'error.editor.find_empty'). 然
    存 取 密 其 UTF8 新文.
    # Native allocation errors remain checked; there is no document-size cap.
    次数 取 0.
    始 取 0.
    窗 其 发送 柄 2078 0 0.
    试
        循
            长 取 (窗 其 发送 柄 2183 0 0) 其 数.
            若 始 > 长 则 破. 然
            位 取 搜区选项 柄 词 始 长 区分 整词.
            若 位 == -1 则 破. 然
            已换 取 (窗 其 发指 柄 2194 ((存 其 大小)-1) 存) 其 数.
            检查状态 柄.
            若 已换 != (存 其 大小)-1 则 卒 (本地 其 文本 'error.editor.replace_result'). 然
            始 取 (窗 其 发送 柄 2193 0 0) 其 数.
            次数 取 次数+1.
        环
    救 原因
        窗 其 发送 柄 2079 0 0.
        存 其 关闭.
        卒 (本地 其 格式 'error.editor.replace_partial' ([原因])).
    终
    窗 其 发送 柄 2079 0 0.
    存 其 关闭.
    得 次数.
法
算 状态 柄:
    位 取 (窗 其 发送 柄 2008 0 0) 其 数.
    行 取 (窗 其 发送 柄 2166 位 0) 其 数.
    列 取 (窗 其 发送 柄 2129 位 0) 其 数.
    长 取 (窗 其 发送 柄 2183 0 0) 其 数.
    得 'Ln '+((行+1) 为 句)+'  Col '+((列+1) 为 句)+'    '+(长 为 句)+' bytes'.
法
