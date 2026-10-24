# Exact production callback blocks are checked by test_recent_files.py.
# Type errors intentionally remain fatal; only explicit 卒 is recoverable.
A 取 {'recentReader':空,'recentWriter':空,'recentItems':[],'recentError':0}.
计 取 [0].
算 验 条件 为 事实, 名 为 句:
    若 非 条件 则 卒 'FAIL: '+名. 然
    计[0] 取 计[0]+1.
    显 'PASS: '+名.
    得 真.
法
调用们 取 [0,0].
算 正常读取:
    调用们[0] 取 调用们[0]+1.
    得 {'items':[['C:\\文 & 件.txt',936]],'error':0}.
法
算 空读取: 得 {'items':[],'error':0}. 法
算 失败读取: 卒 'registry read failed'. 法
算 正常写入 项们 为 阵:
    调用们[1] 取 调用们[1]+1.
    验 (项们[0][0] == 'C:\\文 & 件.txt') 'writer receives unchanged items'.
    得 0.
法
算 拒绝写入 项们 为 阵: 得 5. 法
算 失败写入 项们 为 阵: 卒 'registry write failed'. 法
算 读取最近回归:
    试
        取近函数 取 A 其 查 'recentReader'.
        近果 取 取近函数().
        A 其 增 'recentItems' 近果['items'].
        A 其 增 'recentError' 近果['error'].
    救 原因
        A 其 增 'recentItems' ([]).
        A 其 增 'recentError' 13.
    终
    得 真.
法
算 持久最近:
    码盒 取 [0].
    试
        存近函数 取 A 其 查 'recentWriter'.
        若 存近函数 != 空 则 码盒[0] 取 存近函数 (A 其 查 'recentItems'). 然
    救 原因
        码盒[0] 取 13.
    终
    A 其 增 'recentError' 码盒[0].
    若 码盒[0] != 0 则 显 '[recent] preference write failed: '+(码盒[0] 为 句). 然
    得 码盒[0] == 0.
法
A 其 增 'recentReader' (算 正常读取).
读取最近回归.
验 (调用们[0] == 1) 'zero argument callback really invoked once'.
验 ((A 其 查 'recentItems')[0][0] == 'C:\\文 & 件.txt') 'reader exact path loaded'.
验 ((A 其 查 'recentItems')[0][1] == 936 且 (A 其 查 'recentError') == 0) 'reader encoding and success'.
A 其 增 'recentWriter' (算 正常写入).
验 (持久最近) 'writer callback succeeds'.
验 (调用们[1] == 1) 'writer invoked once'.
A 其 增 'recentWriter' (算 拒绝写入).
验 (非 (持久最近) 且 (A 其 查 'recentError') == 5) 'write API error retained'.
A 其 增 'recentWriter' (算 失败写入).
验 (非 (持久最近) 且 (A 其 查 'recentError') == 13) 'write panic recovered'.
A 其 增 'recentReader' (算 空读取).
读取最近回归.
验 ((A 其 查 'recentItems') 其 量 == 0 且 (A 其 查 'recentError') == 0) 'empty reader succeeds'.
A 其 增 'recentReader' (算 失败读取).
读取最近回归.
验 ((A 其 查 'recentItems') 其 量 == 0 且 (A 其 查 'recentError') == 13) 'read panic recovered'.
显 'TOTAL PASS: '+(计[0] 为 句).
