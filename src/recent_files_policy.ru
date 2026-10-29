# Pure, bounded recent-file policy. Paths are data, never commands or shortcuts.
上限 取 10.
路径上限 取 32000.
算 有路径 路 为 句:
    若 路 == '' 或 路 其 量 > 路径上限 则 得 假. 然
    位 取 0.
    循 路 其 量 次
        若 路[位] < ' ' 则 得 假. 然
        位 取 位+1.
    环
    得 真.
法
算 有绝对路径 路 为 句:
    若 非 (有路径 路) 或 路 其 量 < 3 则 得 假. 然
    若 路[:2] == '\\\\' 则 得 真. 然
    得 ('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ' 其 含 路[0]) 且 路[1] == ':' 且 (路[2] == '\\' 或 路[2] == '/').
法
算 代码 编码 为 数:
    若 编码 == 1252 或 编码 == 936 则 得 编码. 然
    得 0.
法
算 标签 路 为 句:
    # Bound menu width and escape ampersands; tabs cannot inject shortcut text.
    文 取 路.
    若 文 其 量 > 100 则 文 取 '…'+文[(文 其 量)-100:]. 然
    果 取 ''.
    位 取 0.
    循 文 其 量 次
        字 取 文[位].
        若 字 == '&' 则 果 取 果+'&&'.
        另 若 字 < ' ' 或 字 == '' 则 果 取 果+' '.
        另 果 取 果+字. 然 然
        位 取 位+1.
    环
    得 果.
法
算 编列 项们 为 阵:
    若 项们 其 量 > 上限 则 卒 'Recent-file list exceeds its bound.'. 然
    文 取 'RU_RECENT_1\n'.
    位 取 0.
    循 项们 其 量 次
        项 取 项们[位].
        若 非 (有路径 项[0]) 则 卒 'Invalid recent-file path.'. 然
        文 取 文+((代码 项[1]) 为 句)+'\n'+项[0]+'\n'.
        位 取 位+1.
    环
    得 文.
法
算 解列 文 为 句:
    若 文 其 量 < 12 或 文 其 量 > 320100 则 得 []. 然
    若 文[:12] != 'RU_RECENT_1\n' 则 得 []. 然
    # Require complete pairs and a terminal newline. Reject the whole record
    # rather than accepting a truncated prefix after registry corruption.
    行们 取 [].
    起 取 12.
    位 取 12.
    循 (文 其 量)-12 次
        字 取 文[位].
        若 字 == '\n' 则
            若 行们 其 量 >= 20 则 得 []. 然
            行们 其 增 文[起:位]. 起 取 位+1.
        然
        位 取 位+1.
    环
    若 起 != 文 其 量 或 (行们 其 量)%2 != 0 或 行们 其 量 > 20 则 得 []. 然
    果 取 [].
    位 取 0.
    循 (行们 其 量)/2 次
        码 取 -1.
        若 行们[位] == '0' 则 码 取 0. 然
        若 行们[位] == '1252' 则 码 取 1252. 然
        若 行们[位] == '936' 则 码 取 936. 然
        路 取 行们[位+1].
        若 码 < 0 或 非 (有路径 路) 则 得 []. 然
        果 其 增 [路,码].
        位 取 位+2.
    环
    得 果.
法
