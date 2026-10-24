近 取 外言 '../src/recent_files_policy.ru'.
次数 取 [0].
作 确认 条件 为 事实, 文 为 句:
    若 非 条件 则 卒 'FAIL: '+文. 然
    次数[0] 取 次数[0]+1.
    显 'PASS: '+文.
为
确认 ((近 其 标签 'A&B\tC\nD') == 'A&&B C D') 'menu escapes mnemonic and shortcut controls'.
确认 ((近 其 标签 '中文 😀') == '中文 😀') 'menu preserves Unicode'.
确认 (非 (近 其 有路径 '')) 'empty path rejected'.
确认 (非 (近 其 有路径 'a\nb')) 'record delimiter rejected'.
确认 ((近 其 代码 936) == 936) 'GBK reopening retained'.
确认 ((近 其 代码 1252) == 1252) 'Windows1252 reopening retained'.
确认 ((近 其 代码 1200) == 0) 'Unicode reopening uses BOM detection'.
确认 ((近 其 代码 65001) == 0) 'UTF8 reopening uses automatic decoder'.
项们 取 [['C:\\文 😀 & 空格.txt',0],['D:\\legacy.txt',1252],['D:\\中文.txt',936]].
文 取 近 其 编列 项们.
解 取 近 其 解列 文.
确认 ((解 其 量) == 3) 'record roundtrip count'.
位 取 0.
循 3 次
    确认 (解[位][0] == 项们[位][0] 且 解[位][1] == 项们[位][1]) ('record path and encoding '+(位 为 句)).
    位 取 位+1.
环
确认 (((近 其 解列 'garbage') 其 量) == 0) 'wrong version rejected'.
确认 (((近 其 解列 'RU_RECENT_1\n0\npartial') 其 量) == 0) 'truncated record rejected'.
确认 (((近 其 解列 'RU_RECENT_1\n65001\na\n') 其 量) == 0) 'unknown persisted codepage rejected'.
确认 (((近 其 解列 'RU_RECENT_1\n0\na\n936\n') 其 量) == 0) 'odd record rejected'.
确认 (((近 其 解列 (近 其 编列 ([]))) 其 量) == 0) 'clear record roundtrip'.
多 取 [].
位 取 0.
循 10 次 多 其 增 [('C:\\'+(位 为 句)+'.txt'),0]. 位 取 位+1. 环
确认 (((近 其 解列 (近 其 编列 多)) 其 量) == 10) 'ten-item bound accepted'.
多 其 增 ['C:\\extra.txt',0].
拒 取 [假].
试 近 其 编列 多. 救 原因 拒[0] 取 真. 终
确认 拒[0] 'eleven items cannot be persisted'.
长 取 ''.
循 120 次 长 取 长+'a'. 环
确认 (((近 其 标签 长) 其 量) == 101) 'menu presentation length bounded'.
确认 ((近 其 标签 长)[0] == '…') 'long path labels marked as shortened'.
确认 (近 其 有绝对路径 'C:\\a.txt') 'drive absolute path accepted'.
确认 (近 其 有绝对路径 '\\\\server\\share\\a.txt') 'UNC absolute path accepted'.
确认 (非 (近 其 有绝对路径 'relative.txt')) 'relative persisted path rejected'.
确认 (非 (近 其 有绝对路径 'C:relative.txt')) 'drive relative persisted path rejected'.
显 'TOTAL PASS: '+(次数[0] 为 句).
