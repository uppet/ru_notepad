# Scintilla status queries only. No document bytes or save state are changed.
窗 取 外言 'win32.ru'.
算 信息 柄:
    位 取 (窗 其 发送 柄 2008 0 0) 其 数.
    行 取 (窗 其 发送 柄 2166 位 0) 其 数.
    列 取 (窗 其 发送 柄 2129 位 0) 其 数.
    长 取 (窗 其 发送 柄 2183 0 0) 其 数.
    行末 取 (窗 其 发送 柄 2136 行 0) 其 数.
    行尾 取 'None (EOF)'.
    若 行末 < 长 则
        字 取 (窗 其 发送 柄 2007 行末 0) 其 数.
        行尾 取 'Unknown'.
        若 字 == 10 则 行尾 取 'LF'. 然
        若 字 == 13 则
            行尾 取 'CR'.
            若 行末+1 < 长 则
                若 ((窗 其 发送 柄 2007 (行末+1) 0) 其 数) == 10 则 行尾 取 'CRLF'. 然
            然
        然
    然
    模式 取 (窗 其 发送 柄 2030 0 0) 其 数.
    插入 取 'CRLF'.
    若 模式 == 1 则 插入 取 'CR'. 然
    若 模式 == 2 则 插入 取 'LF'. 然
    得 {'line':(行+1),'column':(列+1),'bytes':长,'lineEol':行尾,'insertEol':插入}.
法
算 文本 柄:
    值 取 信息 柄.
    得 'Ln '+((值 其 查 'line') 为 句)+'  Col '+((值 其 查 'column') 为 句)+
        '    '+((值 其 查 'bytes') 为 句)+' bytes    Line EOL: '+(值 其 查 'lineEol')+
        '    Enter: '+(值 其 查 'insertEol').
法
