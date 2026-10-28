# Pure Ru policy: bounded complete requests, never partial delivery or auto retry.
# All transport paths are absolute before serialization; no receiver cwd use.
算 宽数 文 为 句:
    数 取 0. 位 取 0. 窗始 取 0. 窗末 取 0. 窗文 取 ''.
    循 文 其 量 次
        若 位 >= 窗末 则 窗始 取 位. 窗末 取 位+256. 若 窗末 > 文 其 量 则 窗末 取 文 其 量. 然 窗文 取 文[窗始:窗末]. 然
        数 取 数+1. 若 窗文[位-窗始] >= '𐀀' 则 数 取 数+1. 然
        位 取 位+1.
    环
    得 数.
法
算 验路 路 为 句:
    长 取 路 其 量.
    若 长 < 3 或 (宽数 路) > 32000 则 卒 'Invalid single-instance path length.'. 然
    盘 取 (('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz' 其 含 路[0]) 且 路[1] == ':' 且 (路[2] == '\\' 或 路[2] == '/')).
    网 取 路[0:2] == '\\\\' 且 长 > 4 且 路[2] != '?' 且 路[2] != '.'.
    若 非 盘 且 非 网 则 卒 'Single-instance path must be absolute.'. 然
    位 取 0. 窗始 取 0. 窗末 取 0. 窗文 取 ''.
    循 长 次
        若 位 >= 窗末 则 窗始 取 位. 窗末 取 位+256. 若 窗末 > 长 则 窗末 取 长. 然 窗文 取 路[窗始:窗末]. 然
        字 取 窗文[位-窗始].
        若 字 < ' ' 或 字 == '"' 或 字 == '*' 或 字 == '?' 或 字 == '<' 或 字 == '>' 或 字 == '|' 或 (字 == ':' 且 位 != 1) 则 卒 'Invalid single-instance path character.'. 然
        位 取 位+1.
    环
    得 路.
法
算 编包 路们 为 句 阵:
    若 路们 其 量 > 64 则 卒 'Single-instance request exceeds 64 paths.'. 然
    文 取 'RNP1\n'. 位 取 0.
    循 路们 其 量 次
        文 取 文+(验路 路们[位])+'\n'. 位 取 位+1.
        若 (宽数 文)+1 > 131072 则 卒 'Single-instance request exceeds 256 KiB.'. 然
    环
    得 文.
法
算 解包 文 为 句:
    若 文 其 量 < 5 或 文[0:5] != 'RNP1\n' 或 (宽数 文)+1 > 131072 则 卒 'Invalid single-instance protocol.'. 然
    路们 取 []. 始 取 5. 位 取 5. 窗始 取 5. 窗末 取 5. 窗文 取 ''.
    循 (文 其 量)-5 次
        若 位 >= 窗末 则 窗始 取 位. 窗末 取 位+256. 若 窗末 > 文 其 量 则 窗末 取 文 其 量. 然 窗文 取 文[窗始:窗末]. 然
        若 窗文[位-窗始] == '\n' 则
            若 路们 其 量 >= 64 则 卒 'Single-instance request exceeds 64 paths.'. 然
            路们 其 增 (验路 文[始:位]). 始 取 位+1.
        然
        位 取 位+1.
    环
    若 始 != 文 其 量 则 卒 'Truncated single-instance request.'. 然
    得 路们.
法
算 结果 已投递 为 事实 回执 为 数:
    若 非 已投递 则 得 'uncertain'. 然
    若 回执 == 1 则 得 'accepted'. 然
    若 回执 == 2 则 得 'local'. 然
    若 回执 == 3 则 得 'busy'. 然
    # Zero/unknown is not proof that the receiver did not enqueue the request.
    得 'uncertain'.
法
# Registry DWORD decoding: missing defaults ON, corrupt/unreadable fails local.
算 设置结果 码 为 数 型 为 数 长 为 数 值 为 数:
    若 码 == 2 或 码 == 3 则 得 {'enabled':真,'error':0}. 然
    若 码 != 0 则 得 {'enabled':假,'error':码}. 然
    若 型 != 4 或 长 != 4 或 (值 != 0 且 值 != 1) 则 得 {'enabled':假,'error':87}. 然
    得 {'enabled':值 == 1,'error':0}.
法
# Startup discovery is a routing wait budget, not an editor performance gate.
算 发现结果 已占有 为 事实 已过 为 数:
    若 已占有 则 得 'local'. 然
    若 已过 >= 5000 则 得 'uncertain'. 然
    得 'wait'.
法
