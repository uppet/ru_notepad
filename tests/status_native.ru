# Real Scintilla status queries; compiled and executed on Windows CI.
密 取 外言 '如:密'.
窗 取 外言 '../src/win32.ru'.
编 取 外言 '../src/editor.ru'.
态 取 外言 '../src/status.ru'.
次数 取 [0].
作 确认 条件 为 事实 名 为 句:
    若 非 条件 则 卒 'FAIL: '+名. 然
    次数[0] 取 次数[0]+1.
    显 'PASS: '+名.
为
算 元初 参数 为 句 阵:
    库 取 密 其 动态库 ((窗 其 目录)+'Scintilla.dll').
    实例 取 窗 其 成功 ((窗 其 GetModuleHandleW) 其 调用 [空]) 'instance'.
    父 取 窗 其 控制 空 实例 'STATIC' 'status tests' 13565952 0.
    柄 取 编 其 创建 父 实例 1.
    原文 取 '\t甲😀x\r\nlf\ncr\rtail'.
    编 其 设文本 柄 原文.
    窗 其 发送 柄 2160 9 9.
    值 取 态 其 信息 柄.
    确认 ((值 其 查 'line') == 1) 'first line is one-based'.
    确认 ((值 其 查 'column') == 8) 'tab-expanded column counts Han and emoji once each'.
    确认 ((值 其 查 'bytes') == 21) 'byte count is distinct from Unicode column'.
    确认 ((值 其 查 'lineEol') == 'CRLF') 'current first line ends CRLF'.
    确认 ((值 其 查 'insertEol') == 'CRLF') 'Enter mode initially CRLF'.
    窗 其 发送 柄 2160 11 11.
    值 取 态 其 信息 柄.
    确认 ((值 其 查 'line') == 2) 'LF line number'.
    确认 ((值 其 查 'column') == 1) 'new line starts at column one'.
    确认 ((值 其 查 'lineEol') == 'LF') 'mixed file current LF is not mislabeled CRLF'.
    确认 ((值 其 查 'insertEol') == 'CRLF') 'line EOL does not imply Enter mode'.
    窗 其 发送 柄 2160 14 14.
    值 取 态 其 信息 柄.
    确认 ((值 其 查 'line') == 3) 'CR line number'.
    确认 ((值 其 查 'lineEol') == 'CR') 'current CR terminator'.
    窗 其 发送 柄 2160 17 17.
    值 取 态 其 信息 柄.
    确认 ((值 其 查 'line') == 4) 'last unterminated line number'.
    确认 ((值 其 查 'lineEol') == 'None (EOF)') 'last line without terminator is explicit'.
    窗 其 发送 柄 2160 21 21.
    确认 (((态 其 信息 柄) 其 查 'column') == 5) 'EOF column'.
    窗 其 发送 柄 2031 2 0.
    值 取 态 其 信息 柄.
    确认 ((值 其 查 'insertEol') == 'LF') 'Enter mode change reported'.
    确认 ((值 其 查 'lineEol') == 'None (EOF)') 'Enter mode never fabricates a line terminator'.
    确认 ((编 其 文本 柄) == 原文) 'status queries preserve exact mixed-EOL text'.
    确认 (非 (编 其 已变 柄)) 'status and Enter-mode queries leave savepoint clean'.
    确认 ((态 其 文本 柄) 其 含 'Line EOL: None (EOF)') 'formatted status labels current line EOL'.
    确认 ((态 其 文本 柄) 其 含 'Enter: LF') 'formatted status labels insertion mode separately'.
    编 其 设文本 柄 '\t甲😀é'.
    窗 其 发送 柄 2160 11 11.
    确认 (((态 其 信息 柄) 其 查 'column') == 9) 'combining codepoint is separate, not a grapheme or pixel column'.
    窗 其 成功 ((窗 其 DestroyWindow) 其 调用 [父]) 'DestroyWindow'.
    显 'TOTAL PASS: '+(次数[0] 为 句).
    得 0.
法
