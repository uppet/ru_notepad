# Real Windows x64 catalog configuration and switch-isolation acceptance.
# Lexical sample coverage is a separate suite; this suite uses production syntax.
密 取 外言 '如:密'.
窗 取 外言 '../src/win32.ru'.
编 取 外言 '../src/editor.ru'.
语 取 外言 '../src/syntax.ru'.
谱 取 外言 '../src/syntax_catalog.ru'.
例 取 外言 './language_samples.ru'.
次数 取 [0].
作 确认 条件 为 事实, 文 为 句:
    若 非 条件 则 卒 ('FAIL: '+文). 然
    次数[0] 取 次数[0]+1.
    显 'PASS: '+文.
为
算 元初 参数 为 句 阵:
    编辑库 取 密 其 动态库 ((窗 其 目录)+'Scintilla.dll').
    实例 取 窗 其 成功 ((窗 其 GetModuleHandleW) 其 调用 [空]) 'instance'.
    父 取 窗 其 控制 空 实例 'STATIC' 'ru_notepad complete language catalog tests' 13565952 0.
    柄 取 编 其 创建 父 实例 1.
    确认 ((语 其 初始化) == '') 'all runtime syntax dependencies loaded'.
    原文 取 'alpha 42 "hello"\n// preserve 甲😀 text\n'.
    编 其 设文本 柄 原文.
    窗 其 发送 柄 2160 1 4.
    列 取 谱 其 语言们.
    位 取 0.
    循 列 其 量 次
        语言 取 列[位].
        预样 取 例 其 预期 语言.
        试文 取 原文.
        若 预样 >= 0 则 试文 取 例 其 文本 语言. 然
        编 其 设文本 柄 试文.
        窗 其 发送 柄 2160 1 4.
        已选 取 语 其 选择 柄 语言.
        确认 (已选 == 语言) ('catalog mode selected: '+语言).
        号 取 (窗 其 发送 柄 4002 0 0) 其 数.
        预期 取 谱 其 词法号 语言.
        若 语言 == 'plain' 或 语言 == 'ru' 则 预期 取 0. 然
        确认 (号 == 预期) ('actual native lexer identifier: '+语言).
        色号们 取 谱 其 色号 语言.
        色值们 取 谱 其 色值 语言.
        色对 取 (色号们 其 量) == (色值们 其 量).
        色位 取 0.
        循 色号们 其 量 次
            若 (窗 其 发送 柄 2481 色号们[色位] 0) 其 数 != 色值们[色位] 则 色对 取 假. 然
            色位 取 色位+1.
        环
        确认 色对 ('all configured native style colors: '+语言).
        样对 取 真.
        若 预样 >= 0 则
            # Explicit full colourise is bounded to this tiny synthetic sample,
            # never the production edit path or a large-document timing gate.
            窗 其 发送 柄 4003 0 (-1).
            标位 取 例 其 标位 语言.
            标长 取 例 其 标长 语言.
            若 标长 <= 0 则 样对 取 假. 然
            循 标长 次
                若 (窗 其 发送 柄 2038 标位 0) 其 数 != 预样 则 样对 取 假. 然
                标位 取 标位+1.
            环
        另
            样对 取 语言 == 'plain' 或 语言 == 'nfo' 或 语言 == 'ru' 或 语言 == 'markdown'.
        然
        确认 样对 ('actual language token bytes or explicit custom-mode coverage: '+语言).
        确认 ((编 其 文本 柄) == 试文) ('selection preserves exact UTF-8 text: '+语言).
        确认 (非 (编 其 已变 柄) 且 (窗 其 发送 柄 2174 0 0) 其 为空) ('selection stays clean without undo step: '+语言).
        确认 ((窗 其 发送 柄 2009 0 0) 其 数 == 1 且 (窗 其 发送 柄 2008 0 0) 其 数 == 4) ('selection preserves caret and anchor: '+语言).
        位 取 位+1.
    环
    编 其 设文本 柄 原文.
    # Deliberately contaminate styles outside the old 0..31 reset range.
    窗 其 发送 柄 2051 200 1193046.
    窗 其 发送 柄 2053 200 1.
    窗 其 发送 柄 2054 200 1.
    确认 ((语 其 选择 柄 'plain') == 'plain') 'high-style switch to plain'.
    确认 ((窗 其 发送 柄 2481 200 0) 其 数 == (窗 其 发送 柄 2481 32 0) 其 数) 'plain resets high-style foreground to default'.
    确认 ((窗 其 发送 柄 2483 200 0) 其 数 == 0 且 (窗 其 发送 柄 2484 200 0) 其 数 == 0) 'plain resets high-style bold and italic'.
    窗 其 发送 柄 2051 200 1193046.
    确认 ((语 其 选择 柄 'cpp') == 'cpp') 'high-style switch to C++'.
    确认 ((窗 其 发送 柄 2481 200 0) 其 数 == (窗 其 发送 柄 2481 32 0) 其 数) 'C++ resets old embedded language styles'.
    确认 ((窗 其 发送 柄 2481 33 0) 其 数 == 8947848 且 (窗 其 发送 柄 2482 33 0) 其 数 == 16448250) 'line-number UI colors survive all mode switches'.
    确认 ((窗 其 发送 柄 2485 32 0) 其 数 == 11) 'default editor font size survives all mode switches'.
    确认 ((编 其 文本 柄) == 原文 且 非 (编 其 已变 柄)) 'high-style reset preserves content and savepoint'.
    # Two profiles sharing SCLEX_CPP must not keep each other's word lists.
    编 其 设文本 柄 'package demo;'.
    确认 ((语 其 选择 柄 'java') == 'java') 'Java variant sharing cpp lexer selected'.
    窗 其 发送 柄 4003 0 (-1).
    确认 ((窗 其 发送 柄 2038 0 0) 其 数 == 5) 'Java-specific package keyword is coloured'.
    确认 ((语 其 选择 柄 'cpp') == 'cpp') 'same lexer switches back to C++'.
    窗 其 发送 柄 4003 0 (-1).
    确认 ((窗 其 发送 柄 2038 0 0) 其 数 == 11) 'Java package keyword does not leak into C++'.
    语 其 遗忘 柄.
    窗 其 成功 ((窗 其 DestroyWindow) 其 调用 [父]) 'DestroyWindow'.
    显 'TOTAL PASS: '+(次数[0] 为 句).
    得 0.
法
