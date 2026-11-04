# Real Scintilla fixture: compile/run on Windows with pinned dependencies.
# Static checks or portable mocks are NOT Windows execution evidence.
# Expected exact output: 41 individual PASS lines; TOTAL PASS: 41.
密 取 外言 '如:密'.
窗 取 外言 '../src/win32.ru'.
编 取 外言 '../src/editor.ru'.
译 取 外言 '../src/regex_compile.ru'.
搜 取 外言 '../src/regex_search.ru'.
次数 取 [0].
程们 取 {}.
作 确认 条件 为 事实 名 为 句:
    若 非 条件 则 卒 'FAIL: '+名. 然
    次数[0] 取 次数[0]+1. 显 'PASS: '+名.
为
算 文档 柄 号:
    得 {'editor':柄,'untitledNumber':号,'revision':0,'name':'regex fixture','path':''}.
法
算 完成 态 文:
    步 取 0.
    循
        若 态['status'] != 'running' 则 破. 然
        搜 其 步进 态 文.
        若 态['lastOperations'] > 8192 或 态['lastCopiedBytes'] > 2048 或 态['lastReadBytes'] > 192 或 态['lastVMOperations'] > 4096 或 态['operations'] > 态['totalBudget'] 则 卒 'Unbounded regex tick.'. 然
        步 取 步+1.
        若 步 > 100000 则 卒 'Regex fixture did not terminate.'. 然
    环
    得 态.
法
算 新态 文 词 为 句 始 为 数 末 为 数 方向 为 句 回绕 为 事实 零:
    得 搜 其 新建 文 程们[词] (始 为 数) (末 为 数) (方向 为 句) (回绕 为 事实) 零.
法
算 找 文 词 为 句 始 为 数 末 为 数 方向 为 句 回绕 为 事实:
    得 完成 (新态 文 词 始 末 方向 回绕 空) 文.
法
算 中 态 始 为 数 末 为 数:
    得 态['status'] == 'match' 且 态['start'] == 始 且 态['end'] == 末.
法
算 元初 参数 为 句 阵:
    词们 取 ['😀|aa','aa','(abc|a)|b','^b','^\n','\r$','\\Ab','b\\z','^b$','a$','()','x😀Z','a*','z','a','needle'].
    索 取 0.
    循 词们 其 量 次
        词 取 词们[索]. 程们 其 增 词 (译 其 编译 词). 索 取 索+1.
    环
    库 取 密 其 动态库 ((窗 其 目录)+'Scintilla.dll').
    实例 取 窗 其 成功 ((窗 其 GetModuleHandleW) 其 调用 [空]) 'instance'.
    父 取 窗 其 控制 空 实例 'STATIC' 'regex fixture' 13565952 0.
    柄 取 编 其 创建 父 实例 1. 文 取 文档 柄 101.
    另柄 取 编 其 创建 父 实例 2. 另文 取 文档 另柄 102.
    长文 取 ''. 循 255 次 长文 取 长文+'x'. 环
    贪文 取 ''. 循 600 次 贪文 取 贪文+'a'. 环
    # Each row: text, pattern, scope, invocation selection, direction/wrap,
    # scenario, expected status/span, descriptive assertion name.
    案们 取 [
        ['甲😀 aa aa','😀|aa',0,13,0,0,'next',假,'preserve','match',3,7,'Unicode read-only scan preserves native state'],
        ['甲😀 aa aa','aa',0,13,3,7,'next',假,'normal','match',8,10,'next begins at selection end'],
        ['甲😀 aa aa','aa',0,13,8,10,'next',假,'normal','match',11,13,'next advances to later match'],
        ['甲😀 aa aa','aa',0,13,11,13,'next',假,'normal','no-match',-1,-1,'no wrap stops at document end'],
        ['甲😀 aa aa','aa',0,13,11,13,'next',真,'normal','match',8,10,'next wraps at most once'],
        ['甲😀 aa aa','aa',0,13,11,13,'previous',假,'normal','match',8,10,'previous stops at selection start'],
        ['甲😀 aa aa','aa',0,13,0,0,'previous',真,'normal','match',11,13,'previous wrap retains final nonoverlapping match'],
        ['aaaaa','aa',0,5,5,5,'previous',假,'normal','match',2,4,'previous uses forward nonoverlap not rightmost overlap'],
        ['abx','(abc|a)|b',0,3,3,3,'previous',假,'normal','match',1,2,'greedy fallback restarts at accepted end not read cursor'],
        ['a\r\nb\rc\nd','^b',0,8,0,0,'next',假,'normal','match',3,4,'multiline anchor after CRLF'],
        ['a\r\nb\rc\nd','^\n',2,3,0,0,'next',假,'normal','no-match',-1,-1,'CRLF interior is not line start'],
        ['a\r\nb\rc\nd','\r$',1,2,0,0,'next',假,'normal','no-match',-1,-1,'CRLF interior is not line end'],
        ['a\r\nb\rc\nd','\\Ab',3,4,0,0,'next',假,'normal','no-match',-1,-1,'absolute start uses document not selection'],
        ['a\r\nb\rc\nd','b\\z',3,4,0,0,'next',假,'normal','no-match',-1,-1,'absolute end uses document not selection'],
        ['a\r\nb\rc\nd','^b$',3,4,0,0,'next',假,'normal','match',3,4,'captured scope retains real anchor context'],
        ['ab','a$',0,1,0,0,'next',假,'normal','no-match',-1,-1,'scope edge never invents line end'],
        ['ab','^b',1,2,0,0,'next',假,'normal','no-match',-1,-1,'scope edge never invents line start'],
        ['😀\r\n','()',0,6,0,0,'next',真,'zero','match',0,0,'repeated empty matches advance Unicode and separate CRLF'],
        ['','()',0,0,0,0,'next',真,'zero-empty','match',0,0,'empty document repeat excludes EOF through wrap'],
        ['abc','()',0,3,3,3,'previous',真,'zero-previous','match',3,3,'previous repeated empty excludes original position'],
        [长文+'😀Z','x😀Z',0,260,0,0,'next',假,'normal','match',254,260,'match crosses bounded UTF-8 chunk boundary'],
        [贪文+'x','a*',0,601,0,0,'next',假,'normal','match',0,600,'greedy match spans several feeds'],
        ['abc','z',0,3,0,0,'next',真,'cancel','cancelled',-1,-1,'cancel rejects result activation'],
        ['abc','a',0,3,0,0,'next',真,'limit','limit',-1,-1,'work limit leaves selection unchanged'],
        [贪文+'x','a',0,601,601,601,'previous',假,'previous-limit','limit',-1,-1,'previous never publishes provisional result on limit'],
        ['abc','a',0,3,0,0,'next',假,'caret','stale',-1,-1,'manual caret cancels scan'],
        ['abc','a',0,3,0,0,'next',假,'final-caret','match',0,1,'completed result cannot overwrite newer caret'],
        ['abc','a',0,3,0,0,'next',假,'dirty','match',0,1,'search preserves dirty text and undo state'],
        ['abc','a',0,3,0,0,'next',假,'edit','stale',-1,-1,'same-length native edit invalidates job'],
        ['abc','a',0,3,0,0,'next',假,'undo','stale',-1,-1,'native undo restoring original content still invalidates job'],
        ['abc','a',0,3,0,0,'next',假,'revision','stale',-1,-1,'edit or undo revision invalidates same-length content'],
        ['abc','a',0,3,0,0,'next',假,'length','stale',-1,-1,'length catches missed revision notification'],
        ['abc','a',0,3,0,0,'next',假,'identity','stale',-1,-1,'reopened document rejects reused HWND'],
        ['abc','a',0,3,0,0,'next',假,'tab','stale',-1,-1,'active tab switch cancels scan'],
        ['abc','a',0,3,0,0,'next',假,'handle','stale',-1,-1,'changed handle under same document id is stale'],
        ['head\nneedle\ntail','needle',0,16,0,0,'next',假,'fold','match',5,11,'explicit navigation reveals folded endpoint'],
        ['a','a',0,1,0,0,'next',假,'close','stale',-1,-1,'closed removed document is not dereferenced']
    ].
    零 取 {'query':'','scopeStart':0,'scopeEnd':0,'direction':'','untitledNumber':0,'editorIdentity':'','revision':0,'length':0,'position':0}.
    索 取 0.
    循 案们 其 量 次
        案 取 案们[索]. 场 取 案[8]. 当前 取 文.
        窗 其 发送 柄 2171 0 0. 编 其 设文本 柄 案[0].
        文 其 增 'revision' 0. 窗 其 发送 柄 2160 案[4] 案[5].
        窗 其 发送 柄 2190 0 0. 窗 其 发送 柄 2192 案[3] 0. 窗 其 发送 柄 2198 4 0.
        若 场 == 'dirty' 则 窗 其 发文 柄 2181 0 案[0]. 然
        若 场 == 'preserve' 则 窗 其 发送 柄 2171 1 0. 然
        若 场 == 'fold' 则
            窗 其 发送 柄 2222 0 9216. 窗 其 发送 柄 2222 1 1025.
            窗 其 发送 柄 2222 2 1024. 窗 其 发送 柄 2229 0 0. 窗 其 发送 柄 2227 1 1.
        然
        撤 取 (窗 其 发送 柄 2174 0 0) 其 数. 重 取 (窗 其 发送 柄 2016 0 0) 其 数.
        态 取 新态 文 案[1] 案[2] 案[3] 案[6] 案[7] 空.
        若 态['status'] != 'running' 或 态['copiedBytes'] != 0 或 态['vm'] != 空 则 卒 'Construction scanned synchronously.'. 然
        若 场 == 'cancel' 则 搜 其 取消 态.
        另若 场 == 'limit' 则 态 其 增 'totalBudget' (态['operations']+100).
        另若 场 == 'previous-limit' 则
            循
                若 态['status'] != 'running' 或 态['candidateStart'] >= 0 则 破. 然
                搜 其 步进 态 文.
            环
            若 态['candidateStart'] < 0 则 卒 'Missing provisional previous result.'. 然
            态 其 增 'totalBudget' 态['operations'].
        另若 场 == 'caret' 则 窗 其 发送 柄 2160 1 1.
        另若 场 == 'edit' 或 场 == 'undo' 则
            窗 其 发送 柄 2160 0 1. 窗 其 发文 柄 2170 0 'z'.
            文 其 增 'revision' 1.
            若 场 == 'undo' 则 窗 其 发送 柄 2176 0 0. 文 其 增 'revision' 2. 然
            窗 其 发送 柄 2160 0 0.
        另若 场 == 'revision' 则 文 其 增 'revision' 1.
        另若 场 == 'length' 则 编 其 设文本 柄 'changed length'.
        另若 场 == 'identity' 则 当前 取 文档 柄 999.
        另若 场 == 'tab' 则 当前 取 另文.
        另若 场 == 'handle' 则 当前 取 文档 另柄 101.
        另若 场 == 'close' 则
            窗 其 结果 ((窗 其 DestroyWindow) 其 调用 [柄]). 当前 取 空.
        然
        完成 态 当前.
        若 态['status'] != 案[9] 或 态['start'] != 案[10] 或 态['end'] != 案[11] 则 卒 'Unexpected result: '+案[12]+' '+态['status']. 然
        若 场 != 'caret' 且 场 != 'length' 且 场 != 'close' 则
            若 (窗 其 发送 柄 2009 0 0) 其 数 != 案[4] 或 (窗 其 发送 柄 2008 0 0) 其 数 != 案[5] 则 卒 'Scan or failure changed invocation selection.'. 然
        然
        若 场 == 'preserve' 则
            确认 ((编 其 文本 柄) == 案[0] 且 非 (编 其 已变 柄) 且 (窗 其 发送 柄 2174 0 0) 其 数 == 撤 且 (窗 其 发送 柄 2016 0 0) 其 数 == 重 且 (窗 其 发送 柄 2140 0 0) 其 数 == 1) 'text savepoint undo redo readonly preserved'.
            确认 ((窗 其 发送 柄 2191 0 0) 其 数 == 0 且 (窗 其 发送 柄 2193 0 0) 其 数 == 13 且 (窗 其 发送 柄 2199 0 0) 其 数 == 4) 'target and search flags preserved'.
            确认 ((窗 其 发送 柄 2009 0 0) 其 数 == 0 且 (窗 其 发送 柄 2008 0 0) 其 数 == 0) 'scan never selects provisionally'.
            确认 ((搜 其 定位 态 文) 且 (窗 其 发送 柄 2009 0 0) 其 数 == 3 且 (窗 其 发送 柄 2008 0 0) 其 数 == 7 且 非 (搜 其 定位 态 文)) 'explicit activation selects exactly once'.
        另若 场 == 'dirty' 则
            若 非 (编 其 已变 柄) 或 (编 其 文本 柄) != 案[0] 或 (窗 其 发送 柄 2174 0 0) 其 数 != 撤 或 (窗 其 发送 柄 2016 0 0) 其 数 != 重 则 卒 'Dirty document state changed.'. 然
        另若 场 == 'zero' 或 场 == 'zero-empty' 或 场 == 'zero-previous' 则
            位们 取 [4,5,6,0].
            若 场 == 'zero-empty' 则 位们 取 [-1]. 然
            若 场 == 'zero-previous' 则 位们 取 [2,1,0,3]. 然
            子 取 0.
            循 位们 其 量 次
                若 非 (搜 其 定位 态 文) 则 卒 'Zero activation failed.'. 然
                # A stable primitive marker avoids an abstract provenance chain
                # in the pinned compiler when this test loops through jobs.
                标记 取 搜 其 零标记 态.
                零 其 增 'query' (标记['query'] 为 句). 零 其 增 'direction' (标记['direction'] 为 句).
                零 其 增 'editorIdentity' (标记['editorIdentity'] 为 句).
                零 其 增 'scopeStart' (标记['scopeStart'] 为 数). 零 其 增 'scopeEnd' (标记['scopeEnd'] 为 数).
                零 其 增 'untitledNumber' (标记['untitledNumber'] 为 数). 零 其 增 'revision' (标记['revision'] 为 数).
                零 其 增 'length' (标记['length'] 为 数). 零 其 增 'position' (标记['position'] 为 数).
                态 取 完成 (新态 文 案[1] 案[2] 案[3] 案[6] 案[7] 零) 文.
                若 位们[子] < 0 则
                    若 态['status'] != 'no-match' 则 卒 'EOF repeated forever.'. 然
                另
                    若 非 (中 态 位们[子] 位们[子]) 则 卒 'Incorrect scalar zero progress.'. 然
                然
                子 取 子+1.
            环
        另若 场 == 'final-caret' 则
            窗 其 发送 柄 2160 2 2.
            若 (搜 其 定位 态 文) 或 态['status'] != 'stale' 或 (窗 其 发送 柄 2008 0 0) 其 数 != 2 则 卒 'Overwrote newer caret.'. 然
        另若 场 == 'fold' 则
            若 (窗 其 发送 柄 2228 1 0) 其 数 != 0 则 卒 'Scan revealed hidden line.'. 然
            若 非 (搜 其 定位 态 文) 或 (窗 其 发送 柄 2228 1 0) 其 数 != 1 则 卒 'Navigation failed to reveal line.'. 然
        另若 场 == 'revision' 则
            文 其 增 'revision' 0. 搜 其 步进 态 文.
            若 态['status'] != 'stale' 或 (搜 其 定位 态 文) 则 卒 'Staleness was not sticky.'. 然
        另若 态['status'] != 'match' 则
            若 搜 其 定位 态 当前 则 卒 'Failure allowed navigation.'. 然
        然
        确认 真 案[12]. 索 取 索+1.
    环
    窗 其 结果 ((窗 其 DestroyWindow) 其 调用 [父]).
    显 'TOTAL PASS: '+(次数[0] 为 句).
    得 0.
法
