# Native close transactions; actual visible popup tests are an additional gate.
应用 取 外言 '../src/main.ru'.
窗 取 外言 '../src/win32.ru'.
编 取 外言 '../src/editor.ru'.
密 取 外言 '如:密'.
件库 取 外言 '../src/file_codec.ru'.
次数 取 [0]. 选择们 取 [7,2]. 选择位 取 [0]. 存路 取 [''].
作 确认 条件 为 事实 名 为 句:
    若 非 条件 则 卒 'FAIL: '+名. 然
    次数[0] 取 次数[0]+1. 显 'PASS: '+名.
为
算 答复 文档:
    值 取 选择们[选择位[0]]. 选择位[0] 取 选择位[0]+1. 得 值.
法
算 不另存 原路 为 句: 得 ''. 法
算 另存路径 原路 为 句: 得 存路[0]. 法
算 不保存 文档: 得 7. 法
算 要保存 文档: 得 6. 法
作 完成工作:
    起 取 ((窗 其 GetTickCount64) 其 调用 []) 其 值.
    循
        若 非 ((应用 其 A) 其 查 'busy') 则 破. 然
        应用 其 工作时钟.
        若 (((窗 其 GetTickCount64) 其 调用 []) 其 值) 其 数-(起 其 数) > 30000 则 卒 'close fixture save deadline'. 然
    环
为
算 元初 参数 为 句 阵:
    主 取 应用 其 初始化 ([]) 假.
    状态 取 应用 其 A.
    应用 其 切界面 'en' 假.
    原文 取 应用 其 当前.
    第一 取 应用 其 新页 '' 'one' 65001 假 ''.
    第二 取 应用 其 新页 '' 'two' 65001 假 ''.
    第三 取 应用 其 新页 '' 'three' 65001 假 ''.
    窗 其 发文 (第二 其 查 'editor') 2181 0 'two dirty'.
    窗 其 发文 (第三 其 查 'editor') 2181 0 'three dirty'.
    状态 其 增 'confirmClose' (算 答复).
    确认 (非 (应用 其 批关 0 'all')) 'cancel stops whole close batch'.
    确认 (((状态 其 查 'docs') 其 量) == 4) 'no tabs removed before all confirmations'.
    确认 ((状态 其 查 'closeRun') == 空) 'cancel releases transaction'.
    确认 ((应用 其 文档位置 第三) == (状态 其 查 'active')) 'cancel restores original selected identity'.
    确认 ((编 其 文本 (第二 其 查 'editor')) == 'two dirty') 'cancel preserves second dirty bytes'.
    确认 ((编 其 文本 (第三 其 查 'editor')) == 'three dirty') 'cancel preserves third dirty bytes'.
    确认 ((窗 其 发送 (第三 其 查 'editor') 2140 0 0) 其 数 == 0) 'cancel restores writable state'.
    状态 其 增 'confirmClose' (算 要保存).
    状态 其 增 'chooseSavePath' (算 不另存).
    确认 (非 (应用 其 批关 3 'current')) 'Save As cancel stops current close'.
    确认 (((状态 其 查 'docs') 其 量) == 4) 'Save As cancel removes no tabs'.
    确认 ((状态 其 查 'closeRun') == 空) 'Save As cancel clears transaction'.
    # Successful asynchronous disk save followed by a later Cancel: no tabs close.
    选择们[0] 取 6. 选择位[0] 取 0.
    存路[0] 取 (窗 其 目录)+'tab-batch-saved.txt'.
    状态 其 增 'chooseSavePath' (算 另存路径).
    状态 其 增 'confirmClose' (算 答复).
    确认 (非 (应用 其 批关 0 'all')) 'batch waits for asynchronous save'.
    确认 (状态 其 查 'busy') 'save really runs asynchronously'.
    确认 (((状态 其 查 'docs') 其 量) == 4) 'no removal while save pending'.
    完成工作.
    确认 (((状态 其 查 'docs') 其 量) == 4) 'later Cancel preserves all tabs after save'.
    确认 ((件库 其 读文件 存路[0] 0)['text'] == 'three dirty') 'completed disk save is not rolled back'.
    确认 (非 (应用 其 脏 第三)) 'successfully saved tab becomes clean'.
    确认 (应用 其 脏 第二) 'later cancelled tab remains dirty'.
    确认 ((状态 其 查 'closeRun') == 空) 'later Cancel releases transaction'.
    # Re-dirty then cancel a pending save through the real Cancel command path.
    窗 其 发文 (第三 其 查 'editor') 2181 0 'third pending save'.
    状态 其 增 'confirmClose' (算 要保存).
    确认 (非 (应用 其 批关 3 'current')) 'second close starts asynchronous save'.
    窗 其 发送 主 273 901 0.
    应用 其 工作时钟.
    确认 (((状态 其 查 'docs') 其 量) == 4) 'Cancel command preserves pending-save tab'.
    确认 ((状态 其 查 'closeRun') == 空 且 非 (状态 其 查 'busy')) 'Cancel command clears save and close state'.
    确认 ((窗 其 发送 (第三 其 查 'editor') 2140 0 0) 其 数 == 0) 'Cancel command restores readonly state'.
    确认 ((件库 其 读文件 存路[0] 0)['text'] == 'three dirty') 'cancelled second save keeps committed file bytes'.
    # Native save failure via revision change: writer closes without committing.
    确认 (非 (应用 其 批关 3 'current')) 'revision test starts pending save'.
    第三 其 增 'revision' ((第三 其 查 'revision')+1).
    应用 其 工作时钟.
    确认 ((状态 其 查 'lastOutcome') == 'failed') 'revision change fails actual writer'.
    确认 (((状态 其 查 'docs') 其 量) == 4) 'writer failure preserves all tab identities'.
    确认 ((状态 其 查 'closeRun') == 空 且 非 (状态 其 查 'busy')) 'writer failure releases locks and transaction'.
    确认 ((件库 其 读文件 存路[0] 0)['text'] == 'three dirty') 'failed save preserves committed file bytes'.
    确认 ((窗 其 发送 (第三 其 查 'editor') 2140 0 0) 其 数 == 0) 'writer failure restores editor writable state'.
    确认 (应用 其 批关 1 'current') 'nonactive clean target closes'.
    确认 (((状态 其 查 'docs') 其 量) == 3) 'only targeted tab removed'.
    确认 ((应用 其 文档位置 第一) == -1) 'target resolved by stable identity'.
    确认 ((应用 其 文档位置 第三) == (状态 其 查 'active')) 'non-target active identity preserved'.
    确认 (应用 其 批关 0 'saved') 'unmodified close succeeds'.
    确认 (((状态 其 查 'docs') 其 量) == 2) 'only dirty tabs survive unmodified close'.
    确认 ((应用 其 文档位置 原文) == -1) 'unmodified original closed'.
    确认 (应用 其 脏 第二) 'second remains dirty'.
    确认 (应用 其 脏 第三) 'third remains dirty'.
    # Two requests during an active serial-open queue append atomically, not a second window.
    应用 其 入队 ([存路[0]]) 0.
    确认 (状态 其 查 'busy') 'initial open queue is active'.
    确认 (应用 其 接收入队 ([存路[0]])) 'secondary batch appends to active open queue'.
    确认 (((状态 其 查 'queue') 其 量) == 2) 'both pending requests remain queued'.
    状态 其 增 'cancelRequested' 真.
    拒盒 取 [假].
    试 应用 其 接收入队 ([存路[0]]). 救 原因 拒盒[0] 取 真. 终
    确认 拒盒[0] 'pending Cancel rejects new batch before ACK'.
    确认 (((状态 其 查 'queue') 其 量) == 2) 'rejected batch does not mutate existing queue'.
    状态 其 增 'cancelRequested' 假.

    完成工作.
    确认 (((状态 其 查 'docs') 其 量) == 2) 'duplicate identities do not create more tabs'.
    确认 ((编 其 文本 (第三 其 查 'editor')) == 'third pending save') 'duplicate opening preserves dirty bytes'.
    状态 其 增 'singleState' ({'enabled':真,'owner':真}).
    状态 其 增 'modalDepth' 1.
    确认 ((窗 其 发送 主 74 0 0) 其 数 == 2) 'modal admission rejects before touching sender pointers'.
    状态 其 增 'modalDepth' 0.
    状态 其 增 'closeIndex' 0.
    确认 ((窗 其 发送 主 74 0 0) 其 数 == 2) 'application exit rejects before touching sender pointers'.
    状态 其 增 'closeIndex' (-1).
    状态 其 增 'singleState' 空.
    状态 其 增 'confirmClose' (算 不保存).
    确认 (应用 其 批关 0 'all') 'all confirmed tabs close'.
    确认 (((状态 其 查 'docs') 其 量) == 1) 'all creates exactly one blank tab'.
    确认 ((编 其 文本 (应用 其 编辑柄)) == '') 'replacement blank is empty'.
    确认 (非 (应用 其 脏 (应用 其 当前))) 'replacement blank remains clean'.
    确认 ((状态 其 查 'closeRun') == 空) 'successful batch releases transaction'.
    # EOL conversion is dispatched through the real window procedure, never a
    # direct SCI_CONVERTEOLS test substitution. Reuse this main-linked fixture.
    尾柄 取 应用 其 编辑柄.
    尾文 取 应用 其 当前.
    原尾 取 '汉😀\r\nb\rc\n尾'.
    目标们 取 ['汉😀\r\nb\r\nc\r\n尾','汉😀\nb\nc\n尾','汉😀\rb\rc\r尾'].
    模式们 取 [0,2,1].
    位尾 取 0.
    循 3 次
        编 其 设文本 尾柄 原尾.
        窗 其 发送 主 273 (207+位尾) 0.
        确认 ((编 其 文本 尾柄) == 目标们[位尾]) 'EOL command converts exact mixed Unicode bytes without final newline'.
        确认 ((窗 其 发送 尾柄 2030 0 0) 其 数 == 模式们[位尾]) 'EOL command sets independent Enter mode'.
        确认 (应用 其 脏 尾文) 'actual EOL text conversion dirties savepoint'.
        窗 其 发送 主 273 201 0.
        确认 ((编 其 文本 尾柄) == 原尾 且 非 (应用 其 脏 尾文)) 'one Undo restores original mixed bytes and clean savepoint'.
        确认 ((窗 其 发送 尾柄 2030 0 0) 其 数 == 模式们[位尾]) 'Undo preserves independently chosen Enter mode'.
        窗 其 发送 主 273 202 0.
        确认 ((编 其 文本 尾柄) == 目标们[位尾]) 'one Redo restores converted exact bytes'.
        位尾 取 位尾+1.
    环
    编 其 设文本 尾柄 '汉😀'.
    窗 其 发送 主 273 208 0.
    确认 ((编 其 文本 尾柄) == '汉😀' 且 非 (应用 其 脏 尾文)) 'newline-free conversion preserves text and clean state'.
    确认 ((窗 其 发送 尾柄 2174 0 0) 其 数 == 0 且 (窗 其 发送 尾柄 2030 0 0) 其 数 == 2) 'newline-free conversion sets Enter without empty Undo'.
    编 其 设文本 尾柄 ''.
    窗 其 发送 主 273 209 0.
    确认 ((编 其 文本 尾柄) == '' 且 非 (应用 其 脏 尾文)) 'empty conversion does not add a line or dirty state'.
    确认 ((窗 其 发送 尾柄 2174 0 0) 其 数 == 0 且 (窗 其 发送 尾柄 2030 0 0) 其 数 == 1) 'empty conversion sets Enter without empty Undo'.
    编 其 设文本 尾柄 'a\nb\n'.
    窗 其 发送 主 273 208 0.
    确认 (非 (应用 其 脏 尾文) 且 (窗 其 发送 尾柄 2174 0 0) 其 数 == 0) 'already normalized conversion is clean and undo-free'.
    # Guarded commands do not even change the insertion preference.
    护键们 取 ['busy','tabMenuOpen','modalDepth','closeRun'].
    护值们 取 [真,真,1,{}].
    还值们 取 [假,假,0,空].
    位尾 取 0.
    循 4 次
        状态 其 增 护键们[位尾] 护值们[位尾].
        窗 其 发送 主 273 207 0.
        状态 其 增 护键们[位尾] 还值们[位尾].
        确认 ((编 其 文本 尾柄) == 'a\nb\n' 且 (窗 其 发送 尾柄 2030 0 0) 其 数 == 2) 'busy/modal/tab-menu/close guard preserves bytes and Enter'.
        位尾 取 位尾+1.
    环
    尾文 其 增 'large' 真.
    窗 其 发送 主 273 207 0.
    尾文 其 增 'large' 假.
    确认 ((编 其 文本 尾柄) == 'a\nb\n' 且 (窗 其 发送 尾柄 2030 0 0) 其 数 == 2) 'large document guard preserves bytes and Enter'.
    窗 其 发送 尾柄 2171 1 0.
    窗 其 发送 主 273 207 0.
    窗 其 发送 尾柄 2171 0 0.
    确认 ((编 其 文本 尾柄) == 'a\nb\n' 且 (窗 其 发送 尾柄 2030 0 0) 其 数 == 2) 'readonly conversion preserves bytes and Enter'.
    窗 其 发送 主 273 403 0.
    确认 ((尾文 其 查 'encoding') == 1200 且 (尾文 其 查 'bom') 且 (应用 其 脏 尾文)) 'selected UTF16 BOM encoding is independently dirty'.
    窗 其 发送 主 273 207 0.
    窗 其 发送 主 273 201 0.
    确认 ((编 其 文本 尾柄) == 'a\nb\n' 且 (尾文 其 查 'encoding') == 1200 且 (尾文 其 查 'bom')) 'conversion Undo preserves selected encoding and BOM'.
    确认 (应用 其 脏 尾文) 'text Undo does not clear encoding-only dirty state'.
    窗 其 发送 主 273 401 0.
    尾文 其 增 'encodingDirty' 假. # fixture-only cleanup of intentionally unsaved encoding choice
    # A normally-created document can grow beyond the initial-open threshold.
    # Verify the current-byte guard independently of the per-document large flag.
    # Test setup only: never construct/slice a 32 MB Ru string or route that
    # artificial whole string through the compatibility setter. The command
    # still runs against a real 32,000,000-byte Scintilla document, not a mock.
    显 'SETUP: EOL current-byte guard bounded native append begins'.
    编 其 设文本 尾柄 'a\r\n'.
    块文 取 'x'.
    循 16 次 块文 取 块文+块文. 环
    块存 取 密 其 UTF8 块文.
    窗 其 发送 尾柄 2012 0 0.
    试
        若 (块存 其 大小)-1 != 65536 则 卒 'EOL guard setup requires one exact 65536-byte UTF8 chunk.'. 然
        循 488 次 窗 其 发指 尾柄 2282 65536 块存. 环 # SCI_APPENDTEXT, not caret-based ADDTEXT.
        窗 其 发指 尾柄 2282 18429 块存.
        编 其 检查状态 尾柄.
    救 原因
        块存 其 关闭.
        窗 其 发送 尾柄 2012 1 0.
        卒 原因.
    终
    块存 其 关闭.
    窗 其 发送 尾柄 2175 0 0.
    窗 其 发送 尾柄 2012 1 0.
    编 其 记保存 尾柄.
    显 'SETUP: EOL current-byte guard bounded native append complete'.
    确认 (非 (尾文 其 查 'large')) 'grown document retains false initial large-mode flag'.
    位尾 取 0.
    循 3 次
        窗 其 发送 主 273 (207+位尾) 0.
        确认 ((窗 其 发送 尾柄 2183 0 0) 其 数 == 32000000 且 (窗 其 发送 尾柄 2030 0 0) 其 数 == 0 且 非 (应用 其 脏 尾文) 且 (窗 其 发送 尾柄 2174 0 0) 其 数 == 0) 'current-byte threshold rejects conversion even without large flag'.
        位尾 取 位尾+1.
    环
    编 其 设文本 尾柄 ''.
    确认 (应用 其 关程序) 'native fixture closes normally'.
    显 'TOTAL PASS: '+(次数[0] 为 句).
    得 0.
法
