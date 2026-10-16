# Real Win32/Scintilla/Lexilla acceptance tests. Compiled Windows x64 only.
密 取 外言 '如:密'.
窗 取 外言 '../src/win32.ru'.
编 取 外言 '../src/editor.ru'.
语法 取 外言 '../src/syntax.ru'.
策 取 外言 '../src/syntax_policy.ru'.
次数 取 [0].
作 确认 条件 为 事实, 文 为 句:
    若 非 条件 则 卒 ('FAIL: '+文). 然
    次数[0] 取 次数[0]+1.
    显 'PASS: '+文.
为
算 样式 柄, 位 为 数:
    得 (窗 其 发送 柄 2038 位 0) 其 数.
法
作 验样式 柄, 始 为 数, 长 为 数, 预期 为 数, 文 为 句:
    位 取 始.
    合格 取 真.
    循 长 次
        若 (样式 柄 位) != 预期 则 合格 取 假. 然
        位 取 位+1.
    环
    确认 合格 文.
为
算 元初 参数 为 句 阵:
    编辑库 取 密 其 动态库 ((窗 其 目录)+'Scintilla.dll').
    实例 取 窗 其 成功 ((窗 其 GetModuleHandleW) 其 调用 [空]) 'instance'.
    父 取 窗 其 控制 空 实例 'STATIC' 'ru_notepad syntax tests' 13565952 0.
    甲 取 编 其 创建 父 实例 1.
    乙 取 编 其 创建 父 实例 2.
    警告 取 语法 其 初始化.
    若 (策 其 含词 参数 '--expect-missing') 或 (策 其 含词 参数 '--expect-bad-lexer') 则
        确认 (警告 != '') 'dependency failure reports a visible-warning message'.
        若 策 其 含词 参数 '--expect-missing' 则
            确认 (警告 其 含 'could not be loaded') 'actual absent Lexilla DLL is caught before managed loading'.
        另
            确认 (警告 其 含 'does not export CreateLexer') 'actual wrong DLL is caught before native symbol binding'.
        然
        编 其 设文本 甲 'int 甲 = 42;\n'.
        确认 ((语法 其 选择 甲 'cpp') == 'plain') 'missing dependency selects plain text'.
        确认 ((编 其 文本 甲) == 'int 甲 = 42;\n') 'missing dependency never discards UTF-8 text'.
        确认 (非 (编 其 已变 甲)) 'missing dependency preserves initial savepoint'.
        窗 其 发文 甲 2282 1 'x'.
        确认 (编 其 已变 甲) 'plain-text fallback remains editable'.
        窗 其 发送 甲 2176 0 0.
        确认 ((编 其 文本 甲) == 'int 甲 = 42;\n') 'fallback edit remains undoable'.
        确认 (非 (编 其 已变 甲)) 'fallback undo returns to savepoint'.
        窗 其 成功 ((窗 其 DestroyWindow) 其 调用 [父]) 'DestroyWindow'.
        显 'TOTAL PASS: '+(次数[0] 为 句).
        得 0.
    然
    确认 (警告 == '') 'pinned Lexilla DLL loads and exports CreateLexer'.
    确认 ((语法 其 识别 'C:\\源码\\a.CpP') == 'cpp') 'mixed-case C++ suffix'.
    确认 ((语法 其 识别 'a.c') == 'cpp') 'C source uses actual C-family lexer'.
    确认 ((语法 其 识别 'a.HXX') == 'cpp') 'C++ header suffix'.
    确认 ((语法 其 识别 'a.c++') == 'cpp') 'C++ punctuation suffix'.
    确认 ((语法 其 识别 'C:/a.cpp/config.JsOn') == 'json') 'mixed-case JSON suffix'.
    确认 ((语法 其 识别 'C:/a.cpp/README') == 'plain') 'directory suffix does not choose a lexer'.
    确认 ((语法 其 识别 'C:\\a.json\\README') == 'plain') 'Windows directory suffix does not choose a lexer'.
    确认 ((语法 其 识别 'source.ru') == 'plain') 'Ru is truthfully plain text, never borrowed C++'.
    确认 ((语法 其 识别 'data.json.bak') == 'plain') 'unknown final suffix falls back'.
    确认 ((语法 其 识别 '') == 'plain') 'untitled text defaults to plain'.
    确认 ((语法 其 名称 'cpp') == 'C / C++') 'C-family status label'.
    确认 ((语法 其 名称 'json') == 'JSON') 'JSON status label'.
    确认 ((语法 其 名称 'ru') == 'Plain text') 'unsupported status label is truthful'.

    原文 取 '// 甲😀\nint answer = 42;\nconst char *s = "甲😀";\n/* note */ return true;\n'.
    编 其 设文本 甲 原文.
    窗 其 发送 甲 2160 3 10.
    确认 ((语法 其 选择 甲 'cpp') == 'cpp') 'C/C++ lexer attached'.
    确认 ((窗 其 发送 甲 4002 0 0) 其 数 == 3) 'native lexer identifier is SCLEX_CPP'.
    确认 ((窗 其 发送 甲 2693 0 0) 其 数 == 1) 'visible-range idle styling configured'.
    窗 其 发送 甲 4003 0 (-1).
    验样式 甲 0 10 2 'C++ comment including every Han/emoji UTF-8 byte'.
    验样式 甲 11 3 5 'C++ keyword after multibyte comment uses byte offsets'.
    验样式 甲 15 6 11 'C++ identifier style'.
    验样式 甲 24 2 4 'C++ number style'.
    验样式 甲 28 5 5 'C++ const keyword style'.
    验样式 甲 34 4 5 'C++ char keyword style'.
    验样式 甲 44 9 6 'C++ string including every Han/emoji UTF-8 byte'.
    验样式 甲 55 10 1 'C++ block comment style'.
    验样式 甲 66 6 5 'C++ return keyword style'.
    验样式 甲 73 4 5 'C++ true keyword style'.
    确认 ((编 其 文本 甲) == 原文) 'highlighting preserves exact text and line endings'.
    确认 (非 (编 其 已变 甲)) 'highlighting does not dirty a clean document'.
    确认 ((窗 其 发送 甲 2174 0 0) 其 为空) 'highlighting creates no undo step'.
    确认 ((窗 其 发送 甲 2009 0 0) 其 数 == 3) 'highlighting preserves anchor'.
    确认 ((窗 其 发送 甲 2008 0 0) 其 数 == 10) 'highlighting preserves caret at UTF-8 boundary'.
    确认 ((窗 其 发送 甲 2030 0 0) 其 数 == 2) 'highlighting preserves LF insertion mode'.
    确认 ((窗 其 发送 甲 2481 33 0) 其 数 == 8947848) 'highlighting preserves line-number foreground'.

    JSON文 取 '{"名字":"甲😀", "ok":true, "n":-12.5, "x":null, "s":"a\\nb"}\n'.
    编 其 设文本 乙 JSON文.
    确认 ((语法 其 选择 乙 'json') == 'json') 'independent JSON lexer attached'.
    确认 ((窗 其 发送 乙 4002 0 0) 其 数 == 120) 'native lexer identifier is SCLEX_JSON'.
    窗 其 发送 乙 4003 0 (-1).
    验样式 乙 0 1 8 'JSON operator style'.
    验样式 乙 1 8 4 'JSON property including every UTF-8 byte'.
    验样式 乙 10 9 2 'JSON string including every Han/emoji UTF-8 byte'.
    验样式 乙 21 4 4 'JSON property after UTF-8 uses byte offsets'.
    验样式 乙 26 4 11 'JSON true keyword style'.
    验样式 乙 36 5 1 'JSON signed decimal number style'.
    验样式 乙 47 4 11 'JSON null keyword style'.
    验样式 乙 59 2 5 'JSON escape sequence style'.
    确认 ((编 其 文本 乙) == JSON文) 'JSON highlighting preserves exact UTF-8 source'.
    确认 (非 (编 其 已变 乙)) 'JSON highlighting is clean'.
    验样式 甲 11 3 5 'styling JSON does not replace another editor lexer'.

    窗 其 发文 甲 2282 1 ' '.
    确认 (编 其 已变 甲) 'pre-switch edit is dirty'.
    确认 ((语法 其 选择 甲 'json') == 'json') 'C++ to JSON lexer replacement'.
    窗 其 发送 甲 4003 0 (-1).
    确认 ((窗 其 发送 甲 4002 0 0) 其 数 == 120) 'replacement reports new lexer identifier'.
    确认 ((编 其 文本 甲) == 原文+' ') 'lexer replacement does not modify dirty text'.
    确认 (编 其 已变 甲) 'lexer replacement preserves dirty state'.
    确认 ((窗 其 发送 甲 2009 0 0) 其 数 == 3) 'lexer replacement preserves anchor'.
    确认 ((窗 其 发送 甲 2008 0 0) 其 数 == 10) 'lexer replacement preserves caret'.
    确认 (非 ((窗 其 发送 甲 2174 0 0) 其 为空)) 'lexer replacement preserves existing undo'.
    窗 其 发送 甲 2176 0 0.
    确认 ((编 其 文本 甲) == 原文) 'single undo still restores pre-edit text'.
    确认 (非 (编 其 已变 甲)) 'single undo still reaches original savepoint'.
    确认 ((语法 其 选择 甲 'unknown') == 'plain') 'unknown language explicitly clears lexer'.
    确认 ((窗 其 发送 甲 4002 0 0) 其 数 == 0) 'plain text has no borrowed native lexer'.
    验样式 甲 0 79 0 'plain fallback clears all prior token style bytes'.
    确认 ((窗 其 发送 甲 2481 5 0) 其 数 == 2039583) 'plain fallback resets prior keyword colour'.
    窗 其 发送 甲 2011 0 0.
    确认 ((编 其 文本 甲) == 原文+' ') 'plain fallback preserves redo history'.
    确认 (编 其 已变 甲) 'redo after fallback preserves dirty tracking'.
    确认 ((编 其 文本 乙) == JSON文) 'switching first editor preserves second text'.
    验样式 乙 26 4 11 'switching first editor preserves second styles'.

    编 其 设文本 甲 'integer trueish return_value'.
    语法 其 选择 甲 'cpp'.
    窗 其 发送 甲 4003 0 (-1).
    验样式 甲 0 7 11 'keyword prefix does not colour an identifier as keyword'.
    验样式 甲 8 7 11 'boolean prefix does not colour an identifier as keyword'.
    验样式 甲 16 12 11 'underscore identifier is not a keyword'.
    编 其 设文本 甲 '/* 甲\n😀 */\nint x;'.
    窗 其 发送 甲 4003 0 (-1).
    验样式 甲 0 14 1 'native multiline comment state spans UTF-8 and newline'.
    验样式 甲 15 3 5 'keyword resumes after multiline comment'.

    # Exact 4 MiB document. Selection is lazy, and edits request a bounded range.
    大文 取 '//x\n'.
    循 20 次 大文 取 大文+大文. 环
    编 其 设文本 甲 大文.
    始时 取 (窗 其 结果 ((窗 其 GetTickCount64) 其 调用 [])) 其 数.
    语法 其 选择 甲 'cpp'.
    确认 ((窗 其 发送 甲 2183 0 0) 其 数 == 4194304) 'exact 4 MiB document remains intact'.
    确认 ((窗 其 发送 甲 2028 0 0) 其 数 == 0) 'lexer selection does not eagerly scan a 4 MiB document'.
    窗 其 发送 甲 4003 0 4.
    验样式 甲 0 3 2 'bounded large-document range is styled correctly'.
    确认 ((窗 其 发送 甲 2028 0 0) 其 数 < 4194304) 'bounded styling does not force whole-document scan'.
    窗 其 发送 甲 2160 0 3.
    窗 其 发文 甲 2170 0 '//z'.
    窗 其 发送 甲 4003 0 4.
    验样式 甲 0 3 2 'incremental edit in large document keeps token styles'.
    确认 ((窗 其 发送 甲 2183 0 0) 其 数 == 4194304) 'large edit stays within byte limit'.
    确认 ((窗 其 发送 甲 2028 0 0) 其 数 < 4194304) 'incremental edit does not restyle all 4 MiB'.
    窗 其 发送 甲 2176 0 0.
    确认 ((窗 其 发送 甲 2007 2 0) 其 数 == 120) 'large document undo restores changed byte'.
    确认 (非 (编 其 已变 甲)) 'large document undo returns to savepoint'.
    末时 取 (窗 其 结果 ((窗 其 GetTickCount64) 其 调用 [])) 其 数.
    显 'TIMING: large-document select/range/edit/undo '+((末时-始时) 为 句)+' ms (diagnostic, not a speed claim)'.
    # Repeated replacement releases old lexer objects; destruction must not unload
    # Lexilla while another editor still owns one of its objects.
    编 其 设文本 甲 'int x = 1;'.
    循 16 次
        语法 其 选择 甲 'cpp'.
        语法 其 选择 甲 'json'.
        语法 其 选择 甲 'plain'.
    环
    确认 ((编 其 文本 甲) == 'int x = 1;') 'repeated lexer replacements preserve text'.
    确认 (非 (编 其 已变 甲)) 'repeated lexer replacements remain clean'.
    语法 其 选择 甲 'cpp'.
    窗 其 成功 ((窗 其 DestroyWindow) 其 调用 [甲]) 'destroy first editor with live lexer'.
    窗 其 发送 乙 4003 0 (-1).
    验样式 乙 26 4 11 'surviving editor can still call Lexilla after sibling destruction'.
    窗 其 成功 ((窗 其 DestroyWindow) 其 调用 [父]) 'DestroyWindow'.
    显 'TOTAL PASS: '+(次数[0] 为 句).
    得 0.
法
