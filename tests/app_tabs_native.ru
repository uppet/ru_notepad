# Native close transactions; actual visible popup tests are an additional gate.
应用 取 外言 '../src/main.ru'.
窗 取 外言 '../src/win32.ru'.
编 取 外言 '../src/editor.ru'.
本地 取 外言 '../src/i18n.ru'.
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
    # All line edits enter through actual WM_COMMAND; native direct messages
    # below only seed text/selection and observe results, never perform the edit.
    行尾们 取 ['\r\n','\n','\r'].
    行尾位 取 0.
    循 3 次
        行尾 取 行尾们[行尾位].
        行原 取 '前'+行尾+'汉😀  '+行尾+'二\t'+行尾+'尾'.
        行目标们 取 ['前'+行尾+'汉😀  '+行尾+'二\t'+行尾+'汉😀  '+行尾+'二\t'+行尾+'尾','汉😀  '+行尾+'二\t'+行尾+'前'+行尾+'尾','前'+行尾+'尾'+行尾+'汉😀  '+行尾+'二\t','前'+行尾+'汉😀'+行尾+'二'+行尾+'尾'].
        行新首们 取 [3,0,2,1].
        行新末们 取 [4,1,3,3].
        行逆位 取 0.
        循 2 次
            行号位 取 0.
            循 4 次
                编 其 设文本 尾柄 行原.
                行始 取 (窗 其 发送 尾柄 2167 1 0) 其 数.
                行末 取 (窗 其 发送 尾柄 2167 3 0) 其 数.
                若 行逆位 == 0 则 窗 其 发送 尾柄 2160 行始 行末.
                另 窗 其 发送 尾柄 2160 行末 行始. 然
                行入尾 取 (窗 其 发送 尾柄 2030 0 0) 其 数.
                窗 其 发送 主 273 (210+行号位) 0.
                确认 ((编 其 文本 尾柄) == 行目标们[行号位] 且 (窗 其 发送 尾柄 2030 0 0) 其 数 == 行入尾) 'line command exact Unicode CRLF/LF/CR bytes and unchanged Enter'.
                行新始 取 (窗 其 发送 尾柄 2167 行新首们[行号位] 0) 其 数.
                行新末 取 (窗 其 发送 尾柄 2136 行新末们[行号位] 0) 其 数.
                # Trim adjusts original endpoint (next-line start), while the
                # reordering commands select only the moved/copied content.
                若 行号位 == 3 则 行新末 取 (窗 其 发送 尾柄 2167 3 0) 其 数. 然
                行锚 取 (窗 其 发送 尾柄 2009 0 0) 其 数.
                行光 取 (窗 其 发送 尾柄 2008 0 0) 其 数.
                行选好 取 行锚 == 行新始 且 行光 == 行新末.
                若 行逆位 == 1 则 行选好 取 行锚 == 行新末 且 行光 == 行新始. 然
                确认 行选好 'line command preserves selection direction and excludes next-line-start endpoint'.
                窗 其 发送 主 273 201 0.
                确认 ((编 其 文本 尾柄) == 行原 且 非 (应用 其 脏 尾文) 且 (窗 其 发送 尾柄 2174 0 0) 其 数 == 0) 'one line-command Undo restores exact original clean text without another action'.
                窗 其 发送 主 273 202 0.
                确认 ((编 其 文本 尾柄) == 行目标们[行号位]) 'one line-command Redo restores exact output'.
                行号位 取 行号位+1.
            环
            行逆位 取 行逆位+1.
        环
        行尾位 取 行尾位+1.
    环
    # Explicit boundary cases use byte offsets (CJK 3, emoji 4), not Ru
    # codepoint indices. Mixed EOL separators must not be rewritten to Enter.
    界原们 取 ['a\r\n汉😀\nb\r尾','a\r\n汉😀\nb\r尾','a\r\n汉😀\nb\r尾','a\r\n汉😀\nb\r尾','汉😀','a\n','a\n尾','a\n尾',' a \t\n尾 \t','汉😀 \t \r\n尾  ','','a\nb','a\nb','a\nb','a\nb','a\nb','a\nb','','','','a\n','a\n'].
    界目们 取 ['汉😀\nb\r\na\r尾','a\r\nb\n汉😀\r尾','a\r\n汉😀\nb\r尾\r尾','a\r\n汉😀\n汉😀\nb\r尾','汉😀\r\n汉😀','a\n\n','尾\na','尾\na',' a\n尾 \t','汉😀 \r\n尾  ','','a\nb','a\nb','a\nb','a\nb','a\nb','a\nb','','','','a\n','a\n'].
    界号们 取 [211,212,210,210,210,210,211,212,213,213,210,211,212,213,211,212,213,211,212,213,211,212].
    界始们 取 [3,3,13,3,0,2,2,0,1,0,0,0,2,0,0,0,0,0,0,0,2,0].
    界末们 取 [13,11,13,10,0,2,2,0,1,0,0,0,2,0,3,3,3,0,0,0,2,0].
    界位 取 0.
    循 22 次
        编 其 设文本 尾柄 界原们[界位].
        # Single unterminated line has no source separator: use current Enter.
        若 界位 == 4 则 窗 其 发送 尾柄 2031 0 0. 然
        窗 其 发送 尾柄 2160 界始们[界位] 界末们[界位].
        窗 其 发送 主 273 界号们[界位] 0.
        确认 ((编 其 文本 尾柄) == 界目们[界位]) ('line boundary exact bytes case '+(界位 为 句)).
        若 界原们[界位] == 界目们[界位] 则
            确认 (非 (应用 其 脏 尾文) 且 (窗 其 发送 尾柄 2174 0 0) 其 数 == 0) 'boundary no-op preserves clean savepoint and empty Undo'.
        另
            窗 其 发送 主 273 201 0.
            确认 ((编 其 文本 尾柄) == 界原们[界位] 且 非 (应用 其 脏 尾文)) 'boundary Undo preserves original mixed EOL and EOF termination'.
        然
        窗 其 发送 主 273 202 0.
        确认 ((编 其 文本 尾柄) == 界目们[界位]) 'boundary Redo or no-op preserves exact bytes'.
        界位 取 界位+1.
    环
    同原们 取 ['a\na','\n\nx'].
    同位 取 0.
    循 2 次
        编 其 设文本 尾柄 同原们[同位].
        窗 其 发送 尾柄 2160 0 0.
        窗 其 发送 主 273 212 0.
        确认 ((编 其 文本 尾柄) == 同原们[同位] 且 非 (应用 其 脏 尾文) 且 (窗 其 发送 尾柄 2174 0 0) 其 数 == 0) 'moving equal adjacent lines is a clean undo-free no-op including empty lines'.
        同位 取 同位+1.
    环
    # Empty line content may expose a lone CR directly before a lone LF.
    # Reject the whole command before editing rather than merge two EOLs.
    拒原们 取 ['\ra\nb','\na\rz','\r \nb'].
    拒号们 取 [211,210,213].
    拒始们 取 [1,0,1].
    拒末们 取 [2,3,2].
    拒位 取 0.
    循 3 次
        拒反 取 0.
        循 2 次
            编 其 设文本 尾柄 拒原们[拒位].
            若 拒反 == 0 则 窗 其 发送 尾柄 2160 拒始们[拒位] 拒末们[拒位].
            另 窗 其 发送 尾柄 2160 拒末们[拒位] 拒始们[拒位]. 然
            拒前锚 取 (窗 其 发送 尾柄 2009 0 0) 其 数.
            拒前光 取 (窗 其 发送 尾柄 2008 0 0) 其 数.
            窗 其 发送 主 273 拒号们[拒位] 0.
            确认 ((编 其 文本 尾柄) == 拒原们[拒位] 且 非 (应用 其 脏 尾文) 且 (窗 其 发送 尾柄 2174 0 0) 其 数 == 0) 'mixed EOL collision rejects complete command without dirty text or Undo'.
            拒示 取 窗 其 取文 (状态 其 查 'status').
            确认 ((状态 其 查 'lineNotice') 且 (状态 其 查 'modalDepth') == 0 且 (拒示 其 含 (本地 其 文本 'lines.mixed_eol_rejected')) 且 (窗 其 发送 尾柄 2009 0 0) 其 数 == 拒前锚 且 (窗 其 发送 尾柄 2008 0 0) 其 数 == 拒前光) 'mixed EOL rejection is visible nonmodal and preserves forward or reverse selection'.
            拒反 取 拒反+1.
        环
        拒位 取 拒位+1.
    环
    编 其 设文本 尾柄 'a\r\nb'.
    窗 其 发送 尾柄 2160 3 3.
    窗 其 发送 主 273 211 0.
    拒示 取 窗 其 取文 (状态 其 查 'status').
    确认 ((编 其 文本 尾柄) == 'b\r\na' 且 非 (状态 其 查 'lineNotice') 且 非 (拒示 其 含 (本地 其 文本 'lines.mixed_eol_rejected'))) 'normal CRLF boundary moves successfully and clears earlier rejection notice'.
    行号位 取 0.
    循 4 次
        编 其 设文本 尾柄 '前\r\n汉😀 \t\n尾'.
        窗 其 发送 尾柄 2160 5 5.
        行护位 取 0.
        循 4 次
            状态 其 增 护键们[行护位] 护值们[行护位].
            窗 其 发送 主 273 (210+行号位) 0.
            状态 其 增 护键们[行护位] 还值们[行护位].
            确认 ((编 其 文本 尾柄) == '前\r\n汉😀 \t\n尾' 且 非 (应用 其 脏 尾文) 且 (窗 其 发送 尾柄 2174 0 0) 其 数 == 0) 'line commands honor busy modal tab-menu and close guards'.
            行护位 取 行护位+1.
        环
        尾文 其 增 'large' 真.
        窗 其 发送 主 273 (210+行号位) 0.
        尾文 其 增 'large' 假.
        确认 ((编 其 文本 尾柄) == '前\r\n汉😀 \t\n尾' 且 非 (应用 其 脏 尾文)) 'line commands reject initial large-file mode'.
        窗 其 发送 尾柄 2171 1 0.
        窗 其 发送 主 273 (210+行号位) 0.
        窗 其 发送 尾柄 2171 0 0.
        确认 ((编 其 文本 尾柄) == '前\r\n汉😀 \t\n尾' 且 非 (应用 其 脏 尾文)) 'line commands reject readonly editor'.
        行号位 取 行号位+1.
    环
    # A long leading whitespace run ending in a nonspace must stay unchanged.
    # This catches an unanchored [ \t]+$ retrying at every space (quadratic).
    编 其 设文本 尾柄 ''.
    前空 取 ' '.
    循 16 次 前空 取 前空+前空. 环
    前存 取 密 其 UTF8 前空.
    窗 其 发送 尾柄 2012 0 0.
    试
        窗 其 发指 尾柄 2282 65536 前存.
        窗 其 发文 尾柄 2282 1 'x'.
        编 其 检查状态 尾柄.
    救 原因
        前存 其 关闭.
        窗 其 发送 尾柄 2012 1 0.
        卒 原因.
    终
    前存 其 关闭.
    窗 其 发送 尾柄 2175 0 0.
    窗 其 发送 尾柄 2012 1 0.
    编 其 记保存 尾柄.
    窗 其 发送 尾柄 2160 0 0.
    窗 其 发送 主 273 213 0.
    确认 ((窗 其 发送 尾柄 2183 0 0) 其 数 == 65537 且 (窗 其 发送 尾柄 2007 0 0) 其 数 == 32 且 (窗 其 发送 尾柄 2007 65536 0) 其 数 == 120 且 非 (应用 其 脏 尾文) 且 (窗 其 发送 尾柄 2174 0 0) 其 数 == 0) 'long leading whitespace nontrim stays exact clean and undo-free within fixture budget'.
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
    行号位 取 0.
    循 4 次
        窗 其 发送 主 273 (210+行号位) 0.
        确认 ((窗 其 发送 尾柄 2183 0 0) 其 数 == 32000000 且 非 (应用 其 脏 尾文) 且 (窗 其 发送 尾柄 2174 0 0) 其 数 == 0) 'grown current-byte threshold rejects each line command without large flag'.
        行号位 取 行号位+1.
    环
    # Copying this selected 15,999,999-byte unterminated document would add
    # its own bytes plus CRLF, reaching exactly the 32 MB mutation fence.
    窗 其 发送 尾柄 2012 0 0.
    窗 其 发送 尾柄 2645 15999999 16000001.
    窗 其 发送 尾柄 2175 0 0.
    窗 其 发送 尾柄 2012 1 0.
    编 其 记保存 尾柄.
    窗 其 发送 尾柄 2160 0 15999999.
    窗 其 发送 主 273 210 0.
    确认 ((窗 其 发送 尾柄 2183 0 0) 其 数 == 15999999 且 非 (应用 其 脏 尾文) 且 (窗 其 发送 尾柄 2174 0 0) 其 数 == 0) 'duplicate rejects projected size exactly at 32 MB without partial edit'.
    编 其 设文本 尾柄 ''.
    确认 (应用 其 关程序) 'native fixture closes normally'.
    显 'TOTAL PASS: '+(次数[0] 为 句).
    得 0.
法
