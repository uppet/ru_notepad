模 取 外言 '../src/single_instance_policy.ru'.
次数 取 [0].
作 确认 条件 为 事实 文 为 句:
    若 非 条件 则 卒 ('FAIL: '+文). 然
    次数[0] 取 次数[0]+1. 显 'PASS: '+文.
为
作 拒绝 文 为 句:
    拒 取 [假]. 试 模 其 解包 文. 救 原因 拒[0] 取 真. 终
    确认 拒[0] 'reject malformed complete request'.
为
路们 取 ['C:\\文档\\a b.txt','D:/emoji😀.md','\\\\server\\share\\日本語.ru'].
文 取 模 其 编包 路们.
解 取 模 其 解包 文.
确认 ((解 其 量) == 3) 'all three paths retained'.
位 取 0. 循 3 次 确认 (解[位] == 路们[位]) 'Unicode absolute path roundtrip'. 位 取 位+1. 环
确认 (((模 其 解包 (模 其 编包 ([]))) 其 量) == 0) 'empty request means activate'.
确认 ((模 其 宽数 'aé中😀') == 5) 'UTF16 accounting includes surrogate pair'.
拒绝 ''. 拒绝 'RNP2\n'. 拒绝 'RNP1\nrelative.txt\n'. 拒绝 'RNP1\nC:relative.txt\n'.
拒绝 'RNP1\nC:\\a.txt'. 拒绝 'RNP1\n\n'. 拒绝 'RNP1\nC:\\a\t.txt\n'.
拒绝 'RNP1\n\\\\?\\C:\\a\n'. 拒绝 'RNP1\n\\\\.\\pipe\\x\n'.
拒绝 'RNP1\nC:\\a:stream\n'. 拒绝 'RNP1\nC:\\a*.txt\n'.
确认 ((模 其 结果 真 1) == 'accepted') 'only affirmative ACK permits exit'.
确认 ((模 其 结果 真 2) == 'local') 'explicit rejection permits local open'.
确认 ((模 其 结果 真 0) == 'uncertain') 'zero ACK is not assumed rejection'.
确认 ((模 其 结果 真 4) == 'uncertain') 'unknown ACK never opens automatically'.
确认 ((模 其 结果 假 0) == 'uncertain') 'timeout retains uncertainty'.
确认 ((模 其 结果 假 1) == 'uncertain') 'timeout dominates stale result'.
多 取 []. 循 64 次 多 其 增 'C:\\a'. 环
确认 (((模 其 解包 (模 其 编包 多)) 其 量) == 64) '64 paths boundary'.
多 其 增 'C:\\extra'. 拒 取 [假]. 试 模 其 编包 多. 救 原因 拒[0] 取 真. 终
确认 拒[0] '65 paths rejected, never truncated'.
长路 取 'C:\\'. 循 32000 次 长路 取 长路+'x'. 环
拒 取 [假]. 试 模 其 编包 ([长路]). 救 原因 拒[0] 取 真. 终
确认 拒[0] 'overlong path rejected'.
长路 取 'C:\\'. 循 30000 次 长路 取 长路+'x'. 环
拒 取 [假]. 试 模 其 编包 ([长路,长路,长路,长路,长路]). 救 原因 拒[0] 取 真. 终
确认 拒[0] 'aggregate byte bound rejected before transport'.
设 取 模 其 设置结果 2 0 0 0. 确认 (设['enabled'] 且 设['error'] == 0) 'missing value defaults on'.
设 取 模 其 设置结果 3 0 0 0. 确认 (设['enabled'] 且 设['error'] == 0) 'missing key defaults on'.
设 取 模 其 设置结果 0 4 4 1. 确认 (设['enabled'] 且 设['error'] == 0) 'valid on DWORD'.
设 取 模 其 设置结果 0 4 4 0. 确认 (非 设['enabled'] 且 设['error'] == 0) 'valid off DWORD'.
设 取 模 其 设置结果 5 4 4 1. 确认 (非 设['enabled'] 且 设['error'] == 5) 'read failure reports and stays local'.
设 取 模 其 设置结果 0 1 4 1. 确认 (非 设['enabled'] 且 设['error'] == 87) 'wrong registry type rejected'.
设 取 模 其 设置结果 0 4 8 1. 确认 (非 设['enabled'] 且 设['error'] == 87) 'wrong registry size rejected'.
设 取 模 其 设置结果 0 4 4 2. 确认 (非 设['enabled'] 且 设['error'] == 87) 'noncanonical DWORD rejected'.
确认 ((模 其 发现结果 真 0) == 'local') 'new mutex owner may open locally'.
确认 ((模 其 发现结果 假 4999) == 'wait') 'existing slow owner still gets discovery grace'.
确认 ((模 其 发现结果 假 5000) == 'uncertain') 'live unpublished owner never triggers automatic second open'.
确认 ((模 其 发现结果 假 6000) == 'uncertain') 'late startup remains explicit user decision'.
确认 ((模 其 结果 真 3) == 'busy') 'explicit zero-admission busy permits bounded retry'.
确认 ((模 其 结果 假 3) == 'uncertain') 'timeout overrides stale busy receipt'.
显 'TOTAL PASS: '+(次数[0] 为 句).
