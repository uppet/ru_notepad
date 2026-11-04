# Real Scintilla integration fixture. Run as a compiled Windows executable.
密 取 外言 '如:密'.
窗 取 外言 '../src/win32.ru'.
编 取 外言 '../src/editor.ru'.
搜 取 外言 '../src/open_search.ru'.
次数 取 [0].
作 确认 条件 为 事实 名 为 句:
    若 非 条件 则 卒 'FAIL: '+名. 然
    次数[0] 取 次数[0]+1. 显 'PASS: '+名.
为
算 文档 柄 号 名:
    得 {'editor':柄,'untitledNumber':号,'name':名,'path':'','revision':0}.
法
算 重复 文 为 句 数量 为 数:
    果 取 ''. 块 取 文. 余 取 数量.
    循
        若 余 <= 0 则 破. 然
        若 余%2 == 1 则 果 取 果+块. 然
        余 取 (余-余%2)/2.
        若 余 > 0 则 块 取 块+块. 然
    环
    得 果.
法
算 完成 态 文们:
    步数 取 0.
    循
        若 态['status'] != 'running' 则 破. 然
        搜 其 步进 态 文们.
        若 态['lastCandidateBytes'] > 65536 或 态['lastResultCount'] > 16 则 卒 'Unbounded search tick.'. 然
        步数 取 步数+1.
        若 步数 > 1000 则 卒 'Search did not terminate.'. 然
    环
    得 态.
法
算 元初 参数 为 句 阵:
    编辑库 取 密 其 动态库 ((窗 其 目录)+'Scintilla.dll').
    实例 取 窗 其 成功 ((窗 其 GetModuleHandleW) 其 调用 [空]) 'instance'.
    父 取 窗 其 控制 空 实例 'STATIC' 'open search fixture' 13565952 0.
    甲 取 编 其 创建 父 实例 1. 乙 取 编 其 创建 父 实例 2.
    一 取 文档 甲 101 '未命名甲'. 二 取 文档 乙 102 '未命名乙'. 文们 取 [一,二].
    编 其 设文本 甲 '甲😀 alpha\r\nALPHA alphabet alpha\n'.
    编 其 设文本 乙 'unsaved alpha'.
    窗 其 发文 乙 2181 0 'dirty alpha'.
    窗 其 发送 甲 2160 13 8.
    窗 其 发送 甲 2190 3 0. 窗 其 发送 甲 2192 7 0. 窗 其 发送 甲 2198 4 0.
    撤甲 取 (窗 其 发送 甲 2174 0 0) 其 数. 撤乙 取 (窗 其 发送 乙 2174 0 0) 其 数.
    重甲 取 (窗 其 发送 甲 2016 0 0) 其 数. 重乙 取 (窗 其 发送 乙 2016 0 0) 其 数.
    态 取 搜 其 新建 文们 'alpha' 假 真.
    确认 (态['status'] == 'running' 且 (态['results'] 其 量) == 0 且 态['processed'] == 0) 'snapshot does not scan synchronously'.
    完成 态 文们.
    确认 (态['status'] == 'complete' 且 (态['results'] 其 量) == 4 且 态['processed'] == 2) 'all open dirty and untitled buffers native whole-word case folding'.
    首 取 态['results'][0].
    确认 (首['start'] == 8 且 首['end'] == 13 且 首['line'] == 1 且 首['untitledNumber'] == 101) 'exact UTF-8 offset and identity'.
    确认 (首['preview'] == 'alpha␍␊ALPHA alphabet alpha␊' 且 (搜 其 _标签 'a&b c d') == 'a&b␊c␊d') 'preview escapes mixed line endings into one bounded row'.
    确认 ((窗 其 发送 甲 2009 0 0) 其 数 == 13 且 (窗 其 发送 甲 2008 0 0) 其 数 == 8) 'ticks preserve reverse selection'.
    确认 ((窗 其 发送 甲 2191 0 0) 其 数 == 3 且 (窗 其 发送 甲 2193 0 0) 其 数 == 7 且 (窗 其 发送 甲 2199 0 0) 其 数 == 4) 'ticks preserve target and search flags'.
    确认 (非 (编 其 已变 甲) 且 (编 其 已变 乙) 且 (窗 其 发送 甲 2174 0 0) 其 数 == 撤甲 且 (窗 其 发送 乙 2174 0 0) 其 数 == 撤乙 且 (窗 其 发送 甲 2016 0 0) 其 数 == 重甲 且 (窗 其 发送 乙 2016 0 0) 其 数 == 重乙 且 (编 其 文本 甲) == '甲😀 alpha\r\nALPHA alphabet alpha\n' 且 (编 其 文本 乙) == 'dirty alpha') 'ticks preserve text undo redo and savepoints'.
    确认 ((搜 其 定位 态 0 ([二,一])) == 1) 'tab reorder resolves original identity'.
    确认 ((窗 其 发送 甲 2009 0 0) 其 数 == 8 且 (窗 其 发送 甲 2008 0 0) 其 数 == 13) 'only navigation selects match'.
    态 取 完成 (搜 其 新建 文们 'alpha' 真 假) 文们.
    确认 ((态['results'] 其 量) == 4) 'case-sensitive literal substring semantics'.
    编 其 设文本 甲 ((重复 'x' 65535)+'😀Z😀Z').
    态 取 搜 其 新建 ([一]) '😀Z' 真 假.
    搜 其 步进 态 ([一]).
    确认 ((态['results'] 其 量) == 0 且 态['position'] == 65535) 'candidate boundary rounds down inside supplementary UTF-8'.
    完成 态 ([一]).
    确认 ((态['results'] 其 量) == 2 且 态['results'][0]['start'] == 65535 且 态['results'][1]['start'] == 65540) 'boundary matches found exactly once'.
    编 其 设文本 甲 ((重复 'x' 65534)+'abcd').
    态 取 完成 (搜 其 新建 ([一]) 'abcd' 真 假) ([一]).
    确认 ((态['results'] 其 量) == 1 且 态['results'][0]['start'] == 65534) 'literal match crosses chunk boundary'.
    编 其 设文本 甲 ((重复 'x' 65535)+(重复 'ΐ' 1024)).
    态 取 完成 (搜 其 新建 ([一]) (重复 'ΐ' 1024) 假 假) ([一]).
    确认 ((态['results'] 其 量) == 1 且 态['results'][0]['start'] == 65535 且 态['results'][0]['end'] == 71679) 'full Unicode case-fold expansion crossing chunk boundary exceeds 4096 bytes'.
    编 其 设文本 甲 'aaaaa'.
    态 取 完成 (搜 其 新建 ([一]) 'aa' 真 假) ([一]).
    确认 ((态['results'] 其 量) == 2 且 态['results'][1]['start'] == 2) 'non-overlapping find all'.
    编 其 设文本 甲 (重复 'a' 2100).
    态 取 搜 其 新建 ([一]) 'a' 真 假. 搜 其 步进 态 ([一]).
    确认 ((态['results'] 其 量) == 16 且 态['status'] == 'running') 'dense tick yields after sixteen rows'.
    搜 其 取消 态. 搜 其 步进 态 ([一]).
    确认 (态['status'] == 'cancelled' 且 (态['results'] 其 量) == 16 且 (搜 其 定位 态 0 ([一])) == 0) 'cancel stops work and permits valid partial navigation'.
    态 取 完成 (搜 其 新建 ([一]) 'a' 真 假) ([一]).
    确认 (态['status'] == 'limited' 且 (态['results'] 其 量) == 2000 且 (搜 其 定位 态 1999 ([一])) == 0) 'global result cap and limited navigation'.
    一 其 增 'revision' 1.
    确认 ((搜 其 定位 态 0 ([一])) == -1 且 态['status'] == 'stale') 'revision change invalidates navigation'.
    一 其 增 'revision' 0.
    确认 ((搜 其 定位 态 0 ([一])) == -1) 'staleness is sticky even when revision restored'.
    态 取 搜 其 新建 ([一]) 'a' 真 假. 搜 其 步进 态 文们.
    确认 (态['status'] == 'stale' 且 (态['results'] 其 量) == 0) 'added buffer explicitly invalidates snapshot'.
    态 取 搜 其 新建 文们 'a' 真 假. 搜 其 步进 态 ([一]).
    确认 (态['status'] == 'stale') 'removed buffer invalidates before native access'.
    态 取 完成 (搜 其 新建 ([一]) 'a' 真 假) ([一]).
    重开 取 文档 甲 999 'reopened'.
    确认 ((搜 其 定位 态 0 ([重开])) == -1 且 态['status'] == 'stale') 'reused handle cannot navigate a reopened document'.
    态 取 搜 其 新建 ([一]) 'a' 真 假.
    编 其 设文本 甲 'longer changed buffer'. 搜 其 步进 态 ([一]).
    确认 (态['status'] == 'stale') 'length validation catches missing revision notification'.
    确认 ((搜 其 新建 ([]) '' 真 假)['status'] == 'failed') 'empty query rejected'.
    确认 ((搜 其 新建 ([]) (重复 '😀' 1025) 真 假)['status'] == 'failed') 'query cap counts Unicode scalars'.
    确认 ((搜 其 新建 ([]) (重复 '😀' 1024) 真 假)['status'] == 'complete') 'exact scalar cap accepted for empty document set'.
    态 取 搜 其 新建 ([一]) 'a' 真 假. 态 其 增 'documentIndex' 99.
    搜 其 步进 态 ([一]).
    确认 (态['status'] == 'failed' 且 态['error'] == 'Open-buffer search could not continue.' 且 (搜 其 定位 态 0 ([一])) == -1) 'caught engine failure stops work and rejects navigation'.
    丙 取 编 其 创建 父 实例 3. 三 取 文档 丙 103 'closed'.
    编 其 设文本 丙 'a'. 态 取 搜 其 新建 ([三]) 'a' 真 假.
    窗 其 结果 ((窗 其 DestroyWindow) 其 调用 [丙]).
    搜 其 步进 态 ([]).
    确认 (态['status'] == 'stale') 'destroyed removed handle is never dereferenced'.
    窗 其 结果 ((窗 其 DestroyWindow) 其 调用 [父]).
    显 'TOTAL PASS: '+(次数[0] 为 句).
    得 0.
法
