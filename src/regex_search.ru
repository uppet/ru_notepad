# Current-buffer FIND bridge. No regex native engine, disk IO, retained pointer,
# whole-buffer copy, target/search-flag mutation, or speculative navigation.
# direction: next/previous. Bounds are captured UTF-8 scalar boundaries.
# Previous enumerates NONOVERLAPPING forward matches and retains the last.
# Each tick batches <=16 phases, copy <=2048 bytes, byte probes <=192,
# VM <=4096 microsteps, combined work <=8192. Total survives restarts.
# Counters are work units, not wall-clock promises. Native calls are bounded
# but OS scheduling and allocator latency are not claimed to be time bounded.
窗 取 外言 'win32.ru'.
编 取 外言 'editor.ru'.
机 取 外言 'regex_vm.ru'.
每步工作上限 取 8192.
每步复制上限 取 2048.
总工作上限 取 67108864.

算 _费 态 数量 为 数:
    若 态['operations']+数量 > 态['totalBudget'] 则
        态 其 增 'status' 'limit'. 卒 'Regex search work limit.'.
    然
    态 其 增 'operations' (态['operations']+数量).
    态 其 增 'lastOperations' (态['lastOperations']+数量).
    得 真.
法
# Metadata is checked before ANY native access, including validation reads.
# Callers supply only the current active document, or 空 after closing it.
算 _有效 态 文:
    若 态['status'] == 'stale' 则 得 假. 然
    若 文 == 空 则 态 其 增 'status' 'stale'. 得 假. 然
    若 文['untitledNumber'] != 态['untitledNumber'] 或 (文['editor'] 其 句) != 态['editorIdentity'] 或 文['revision'] != 态['revision'] 则
        态 其 增 'status' 'stale'. 得 假.
    然
    柄 取 文['editor'].
    若 (窗 其 发送 柄 2183 0 0) 其 数 != 态['length'] 则 态 其 增 'status' 'stale'. 得 假. 然
    若 (窗 其 发送 柄 2009 0 0) 其 数 != 态['anchor'] 则 态 其 增 'status' 'stale'. 得 假. 然
    若 (窗 其 发送 柄 2008 0 0) 其 数 != 态['caret'] 则 态 其 增 'status' 'stale'. 得 假. 然
    得 真.
法
算 _守 态 文:
    _费 态 32.
    若 非 (_有效 态 文) 则 卒 'Stale regex search.'. 然
    得 真.
法
算 _字节 态 文 位 为 数:
    若 位 < 0 或 位 >= 态['length'] 或 位%1 != 0 则 卒 'Invalid byte position.'. 然
    _守 态 文.
    果 取 (窗 其 发送 文['editor'] 2007 位 0) 其 数.
    态 其 增 'lastReadBytes' (态['lastReadBytes']+1).
    若 果 < 0 则 果 取 果+256. 然
    若 果 < 0 或 果 > 255 则 卒 'Invalid UTF-8 byte.'. 然
    得 果.
法
算 _边界 态 文 位 为 数:
    若 位 < 0 或 位 > 态['length'] 或 位%1 != 0 则 得 假. 然
    若 位 == 0 或 位 == 态['length'] 则 得 真. 然
    字 取 _字节 态 文 位.
    得 字 < 128 或 字 >= 192.
法
# Explicit scalar progress: POSITIONAFTER/POSITIONBEFORE coalesce CRLF.
算 _后位 态 文 位 为 数:
    若 位 == 态['length'] 则 得 位. 然
    字 取 _字节 态 文 位. 宽 取 1.
    若 字 >= 240 且 字 <= 244 则 宽 取 4.
    另若 字 >= 224 且 字 <= 239 则 宽 取 3.
    另若 字 >= 194 且 字 <= 223 则 宽 取 2.
    另若 字 >= 128 则 卒 'Invalid UTF-8 lead byte.'. 然
    若 位+宽 > 态['length'] 则 卒 'Truncated UTF-8 scalar.'. 然
    索 取 1.
    循 宽-1 次
        字 取 _字节 态 文 (位+索).
        若 字 < 128 或 字 >= 192 则 卒 'Invalid UTF-8 continuation.'. 然
        索 取 索+1.
    环
    得 位+宽.
法
算 _前位 态 文 位 为 数:
    若 位 <= 0 则 得 0. 然
    果 取 位-1.
    循 4 次
        字 取 _字节 态 文 果.
        若 字 < 128 或 字 >= 192 则 得 果. 然
        果 取 果-1.
        若 果 < 0 则 卒 'Invalid UTF-8 boundary.'. 然
    环
    卒 'Invalid UTF-8 boundary.'.
法
算 _文本 态 文 始 为 数 末 为 数:
    若 始 < 0 或 末 < 始 或 末 > 态['length'] 或 末-始 > 256 则 卒 'Unbounded regex copy.'. 然
    _费 态 ((末-始)*4+32).
    _守 态 文.
    态 其 增 'copiedBytes' (态['copiedBytes']+末-始).
    态 其 增 'lastCopiedBytes' (态['lastCopiedBytes']+末-始).
    得 编 其 _范围文本 文['editor'] 始 末.
法
算 _重启 态 始 为 数:
    _费 态 64.
    态 其 增 'scanStart' 始.
    态 其 增 'vm' (机 其 新建 态['program'] (始 为 数) (态['legEnd'] 为 数) (态['length'] 为 数) (态['totalBudget']-态['operations'])).
    得 态.
法
算 新建 文 程 域始 为 数 域末 为 数 方向 为 句 回绕 为 事实 上零:
    态 取 {'status':'running','error':'','program':程,'scopeStart':域始,'scopeEnd':域末,'direction':方向,'wrap':回绕,'wrapped':假,'start':-1,'end':-1,'candidateStart':-1,'candidateEnd':-1,'vm':空,'scanStart':0,'legEnd':0,'originalStart':0,'operations':0,'lastOperations':0,'copiedBytes':0,'lastCopiedBytes':0,'lastReadBytes':0,'lastVMOperations':0,'totalBudget':总工作上限,'excludeZero':-1,'positioned':假,'untitledNumber':-1,'editorIdentity':'','revision':-1,'length':0,'anchor':0,'caret':0}.
    若 文 == 空 或 程['status'] != 'ok' 或 (方向 != 'next' 且 方向 != 'previous') 则
        态 其 增 'status' 'error'. 态 其 增 'error' 'Invalid regex search arguments.'. 得 态.
    然
    试
        # Only construction trusts the supplied current live document. No scan.
        柄 取 文['editor'].
        态 其 增 'untitledNumber' 文['untitledNumber']. 态 其 增 'editorIdentity' (柄 其 句).
        态 其 增 'revision' 文['revision'].
        态 其 增 'length' ((窗 其 发送 柄 2183 0 0) 其 数).
        态 其 增 'anchor' ((窗 其 发送 柄 2009 0 0) 其 数).
        态 其 增 'caret' ((窗 其 发送 柄 2008 0 0) 其 数).
        _费 态 96.
        若 域始 > 域末 或 非 (_边界 态 文 域始) 或 非 (_边界 态 文 域末) 则 卒 'Invalid regex scope.'. 然
        起 取 态['anchor']. 尾 取 态['caret'].
        若 起 > 尾 则 换 取 起. 起 取 尾. 尾 取 换. 然
        若 方向 == 'next' 则 始 取 尾. 另 始 取 起. 然
        若 始 < 域始 则 始 取 域始. 然
        若 始 > 域末 则 始 取 域末. 然
        若 非 (_边界 态 文 始) 则 卒 'Invalid regex selection boundary.'. 然
        态 其 增 'originalStart' 始.
        若 方向 == 'next' 则 态 其 增 'scanStart' 始. 态 其 增 'legEnd' 域末.
        另 态 其 增 'scanStart' 域始. 态 其 增 'legEnd' 始. 然
        若 上零 != 空 则
            若 上零['query'] == 程['query'] 且 上零['scopeStart'] == 域始 且 上零['scopeEnd'] == 域末 且 上零['direction'] == 方向 且 上零['untitledNumber'] == 态['untitledNumber'] 且 上零['editorIdentity'] == 态['editorIdentity'] 且 上零['revision'] == 态['revision'] 且 上零['length'] == 态['length'] 且 上零['position'] == 态['anchor'] 且 上零['position'] == 态['caret'] 则
                态 其 增 'excludeZero' 上零['position'].
            然
        然
    救 原因
        若 态['status'] == 'running' 则 态 其 增 'status' 'error'. 态 其 增 'error' 原因. 然
    终
    得 态.
法
算 取消 态:
    若 态['status'] == 'running' 或 态['status'] == 'match' 则 态 其 增 'status' 'cancelled'. 然
    得 态.
法
算 _结束段 态:
    若 态['candidateStart'] >= 0 则
        态 其 增 'start' 态['candidateStart']. 态 其 增 'end' 态['candidateEnd'].
        态 其 增 'status' 'match'. 得 态.
    然
    若 态['wrap'] 且 非 态['wrapped'] 则
        态 其 增 'wrapped' 真. 态 其 增 'vm' 空.
        若 态['direction'] == 'next' 则
            态 其 增 'scanStart' 态['scopeStart']. 态 其 增 'legEnd' 态['originalStart'].
        另
            态 其 增 'scanStart' 态['originalStart']. 态 其 增 'legEnd' 态['scopeEnd'].
        然
    另 态 其 增 'status' 'no-match'. 然
    得 态.
法
算 _喂 态 文:
    内 取 态['vm']. 始 取 内['cursor'] 为 数. 末 取 始+256.
    若 末 > 态['legEnd'] 则 末 取 态['legEnd']. 然
    # At most three continuation bytes can be dropped from a valid UTF-8 cut.
    循 4 次
        若 _边界 态 文 末 则 破. 然
        末 取 末-1.
    环
    若 末 < 始 或 (末 == 始 且 始 != 态['legEnd']) 则 卒 'Invalid regex chunk.'. 然
    前 取 ''. 后 取 ''.
    若 始 > 0 则 前位 取 _前位 态 文 始. 前 取 _文本 态 文 前位 始. 然
    若 末 < 态['length'] 则 后位 取 _后位 态 文 末. 后 取 _文本 态 文 末 后位. 然
    文块 取 _文本 态 文 始 末.
    _费 态 64.
    机 其 喂入 内 文块 始 前 后 (末 == 态['legEnd']).
    得 态.
法
算 _一步 态 文:
    若 态['status'] != 'running' 则 得 态. 然
    试
        _守 态 文.
        若 态['vm'] == 空 则 得 _重启 态 (态['scanStart'] 为 数). 然
        内 取 态['vm'].
        若 内['status'] == 'need-input' 则 得 _喂 态 文. 然
        若 内['status'] == 'running' 则
            额 取 态['totalBudget']-态['operations'].
            剩步 取 4096-态['lastVMOperations'].
            若 额 > 剩步 则 额 取 剩步. 然
            剩计 取 每步工作上限-态['lastOperations'].
            若 额 > 剩计 则 额 取 剩计. 然
            若 额 <= 0 则 态 其 增 'status' 'limit'. 得 态. 然
            机 其 步进 内 额.
            _费 态 内['lastOperations'].
            态 其 增 'lastVMOperations' (态['lastVMOperations']+内['lastOperations']).
            得 态.
        然
        若 内['status'] == 'limit' 或 内['status'] == 'error' 则
            态 其 增 'status' 内['status']. 态 其 增 'error' 内['error']. 得 态.
        然
        若 内['status'] == 'no-match' 则 得 _结束段 态. 然
        若 内['status'] != 'match' 则 卒 'Invalid regex VM status.'. 然
        始 取 内['start'] 为 数. 末 取 内['end'] 为 数.
        若 始 < 态['scanStart'] 或 末 < 始 或 末 > 态['legEnd'] 则 卒 'Invalid regex match span.'. 然
        排除 取 始 == 末 且 始 == 态['excludeZero'].
        若 非 排除 则
            若 态['direction'] == 'next' 则
                态 其 增 'start' 始. 态 其 增 'end' 末. 态 其 增 'status' 'match'. 得 态.
            然
            态 其 增 'candidateStart' 始. 态 其 增 'candidateEnd' 末.
        然
        # Restart at accepted END, never the possibly much later readCursor.
        若 始 == 末 则
            若 末 >= 态['legEnd'] 则 得 _结束段 态. 然
            末 取 _后位 态 文 末.
        然
        若 末 > 态['legEnd'] 则 得 _结束段 态. 然
        得 _重启 态 末.
    救 原因
        若 态['status'] == 'running' 则 态 其 增 'status' 'error'. 态 其 增 'error' 原因. 然
    终
    得 态.
法
# Budget is shared across every feed/restart in the batch, never per chunk.
算 步进 态 文:
    若 态['status'] != 'running' 则 得 态. 然
    态 其 增 'lastOperations' 0. 态 其 增 'lastCopiedBytes' 0.
    态 其 增 'lastReadBytes' 0. 态 其 增 'lastVMOperations' 0.
    循 16 次
        若 态['status'] != 'running' 或 态['lastVMOperations'] >= 4096 或 态['lastOperations'] > 每步工作上限-2048 或 态['lastCopiedBytes'] > 每步复制上限-264 则 破. 然
        _一步 态 文.
    环
    得 态.
法
# Explicit activation only. A fresh guard rejects edits, undo, tab switches,
# reused handles and manual caret changes even after matching has completed.
算 定位 态 文:
    若 态['status'] != 'match' 或 态['positioned'] 则 得 假. 然
    试
        若 非 (_有效 态 文) 则 得 假. 然
        始 取 态['start'] 为 数. 末 取 态['end'] 为 数.
        若 始 < 态['scopeStart'] 或 末 < 始 或 末 > 态['scopeEnd'] 则 卒 'Invalid accepted span.'. 然
        柄 取 文['editor'].
        若 非 (_有效 态 文) 则 得 假. 然
        起行 取 (窗 其 发送 柄 2166 始 0) 其 数.
        若 非 (_有效 态 文) 则 得 假. 然
        末行 取 (窗 其 发送 柄 2166 末 0) 其 数.
        若 非 (_有效 态 文) 则 得 假. 然
        窗 其 发送 柄 2232 起行 0.
        若 非 (_有效 态 文) 则 得 假. 然
        窗 其 发送 柄 2232 末行 0.
        若 非 (_有效 态 文) 则 得 假. 然
        窗 其 发送 柄 2160 始 末.
        态 其 增 'positioned' 真.
        窗 其 发送 柄 2169 0 0.
        得 真.
    救 原因
        态 其 增 'status' 'error'. 态 其 增 'error' 原因.
    终
    得 假.
法
算 零标记 态:
    若 态['status'] != 'match' 或 非 态['positioned'] 或 态['start'] != 态['end'] 则 得 空. 然
    得 {'query':(态['program']['query'] 为 句),'scopeStart':(态['scopeStart'] 为 数),'scopeEnd':(态['scopeEnd'] 为 数),'direction':(态['direction'] 为 句),'untitledNumber':(态['untitledNumber'] 为 数),'editorIdentity':(态['editorIdentity'] 为 句),'revision':(态['revision'] 为 数),'length':(态['length'] 为 数),'position':(态['start'] 为 数)}.
法
