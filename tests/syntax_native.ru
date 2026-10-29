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
算 验错误词法库:
    # Production import-time preflight has already run. This independent check
    # proves the staged wrong-export fixture is loadable in this same process.
    # It also runs from the portable CMD runner, before the unchanged 8 assertions.
    路径存 取 密 其 UTF16 ((窗 其 目录)+'Lexilla.dll').
    成果 取 (窗 其 LoadLibraryExW) 其 调用 [路径存,空,2304].
    路径存 其 关闭.
    库 取 窗 其 结果 成果.
    若 库 其 为空 则 卒 'Wrong-lexer fixture could not be loaded.'. 然
    缺出口 取 [假].
    名存们 取 [空].
    试
        名存们[0] 取 密 其 UTF8 'CreateLexer'.
        导出 取 窗 其 结果 ((语法 其 GetProcAddress) 其 调用 [库,名存们[0]]).
        (名存们[0]) 其 关闭.
        名存们[0] 取 空.
        缺出口[0] 取 导出 其 为空.
    救 原因
        若 名存们[0] != 空 则 (名存们[0]) 其 关闭. 然
        窗 其 结果 ((窗 其 FreeLibrary) 其 调用 [库]).
        卒 原因.
    终
    窗 其 成功 ((窗 其 FreeLibrary) 其 调用 [库]) 'wrong-lexer fixture FreeLibrary'.
    若 非 缺出口[0] 则 卒 'Wrong-lexer fixture unexpectedly exports CreateLexer.'. 然
    显 'WRONG_LEXER_FIXTURE_PREFLIGHT loadable=1 createlexer_missing=1 released=1'.
    得 空.
法
算 元初 参数 为 句 阵:
    若 策 其 含词 参数 '--expect-bad-lexer' 则 验错误词法库. 然
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
    确认 ((语法 其 识别 'source.ru') == 'ru') 'Ru selects its own container lexer, never borrowed C++'.
    确认 ((语法 其 识别 'data.json.bak') == 'plain') 'unknown final suffix falls back'.
    确认 ((语法 其 识别 '') == 'plain') 'untitled text defaults to plain'.
    确认 ((语法 其 名称 'cpp') == 'C / C++') 'C-family status label'.
    确认 ((语法 其 名称 'json') == 'JSON') 'JSON status label'.
    确认 ((语法 其 名称 'ru') == 'Ru / 如言') 'Ru-owned status label is explicit'.

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

    # C++ folding shares the production margin/menu API, including packed levels.
    折文 取 'namespace N {\nint f() {\nconst char *s = "{ }";\nif (true) {\nreturn 1;\n}\n}\n}\n/* comment\nbody\n*/\n#if FLAG\nint x;\n#endif\n'.
    编 其 设文本 甲 折文.
    确认 ((语法 其 选择 甲 'cpp') == 'cpp') 'C++ fold fixture selects native lexer'.
    确认 ((窗 其 发送 甲 2243 2 0) 其 数 == 16) 'C++ fold margin is visible'.
    确认 ((窗 其 发送 甲 2247 2 0) 其 数 == 1) 'C++ fold margin emits click notifications'.
    确认 ((窗 其 发送 甲 2664 0 0) 其 数 == 5) 'C++ automatic folding uses show/change without double-click handling'.
    确认 ((窗 其 发送 甲 2028 0 0) 其 数 == 0) 'C++ fold setup remains lazy'.
    确认 (语法 其 全折 甲 0) 'C++ collapse-all works before explicit colouring'.
    确认 ((窗 其 发送 甲 2228 1 0) 其 数 == 0) 'C++ namespace body is hidden'.
    确认 (语法 其 全折 甲 1) 'C++ expand-all succeeds'.
    确认 ((窗 其 发送 甲 2228 1 0) 其 数 == 1) 'C++ expand-all restores body'.
    层 取 (窗 其 发送 甲 2223 0 0) 其 数.
    确认 ((策 其 是折头 层)) 'namespace is a fold header'.
    层 取 (窗 其 发送 甲 2223 1 0) 其 数.
    确认 ((策 其 是折头 层)) 'function is a nested fold header'.
    层 取 (窗 其 发送 甲 2223 3 0) 其 数.
    确认 ((策 其 是折头 层)) 'conditional brace is a nested fold header'.
    层 取 (窗 其 发送 甲 2223 8 0) 其 数.
    确认 ((策 其 是折头 层)) 'multiline C++ comment is foldable'.
    层 取 (窗 其 发送 甲 2223 11 0) 其 数.
    确认 ((策 其 是折头 层)) 'preprocessor conditional is foldable without branch evaluation'.
    普位 取 (窗 其 发送 甲 2167 2 0) 其 数.
    确认 (非 (语法 其 折叠 甲 普位)) 'packed next-level bits and string braces are not fold headers'.
    确认 (非 (语法 其 折叠 甲 (-1))) 'negative C++ margin position is rejected'.
    确认 (非 (语法 其 全折 甲 3)) 'invalid C++ fold action is rejected'.
    窗 其 发送 甲 2160 3 9.
    确认 (语法 其 折叠 甲 0) 'C++ margin route collapses namespace'.
    确认 ((窗 其 发送 甲 2228 1 0) 其 数 == 0) 'C++ margin collapse hides children'.
    确认 (非 (编 其 已变 甲)) 'C++ folds preserve savepoint'.
    确认 ((窗 其 发送 甲 2174 0 0) 其 为空) 'C++ folds create no undo record'.
    确认 ((窗 其 发送 甲 2009 0 0) 其 数 == 3) 'C++ folds preserve selection anchor'.
    确认 ((窗 其 发送 甲 2008 0 0) 其 数 == 9) 'C++ folds preserve selection caret'.
    确认 ((编 其 文本 甲) == 折文) 'C++ folds preserve exact source'.
    确认 ((窗 其 发送 乙 2243 2 0) 其 数 == 0) 'C++ folding does not enable JSON sibling margin'.
    确认 (非 (语法 其 全折 乙 0)) 'JSON sibling rejects unsupported fold command'.
    语法 其 全折 甲 1.
    窗 其 发文 甲 2003 0 '// edit\n'.
    # Production text notifications invalidate selection tokens; native routing
    # must still function after an edit instead of depending on that token.
    语法 其 变化 甲 0 8 1 1.
    窗 其 发送 甲 4003 0 (-1).
    确认 (语法 其 全折 甲 0) 'C++ folding remains usable after text-change invalidation'.
    确认 ((窗 其 发送 甲 2228 2 0) 其 数 == 0) 'C++ edited fold levels move with inserted line'.
    语法 其 全折 甲 1.
    窗 其 发送 甲 2176 0 0.
    窗 其 发送 甲 4003 0 (-1).
    确认 ((编 其 文本 甲) == 折文) 'C++ fold edit has exactly one undo step'.
    确认 (非 (编 其 已变 甲)) 'C++ fold edit undo restores savepoint'.
    语法 其 全折 甲 0.
    确认 ((语法 其 选择 甲 'json') == 'json') 'collapsed C++ can switch to JSON'.
    确认 ((窗 其 发送 甲 2228 1 0) 其 数 == 1) 'language switch restores hidden C++ body'.
    确认 ((窗 其 发送 甲 2243 2 0) 其 数 == 0) 'JSON switch hides C++ fold margin'.
    语法 其 选择 甲 'cpp'.
    语法 其 全折 甲 0.
    确认 ((语法 其 选择 甲 'plain') == 'plain') 'collapsed C++ switches to plain'.
    确认 ((窗 其 发送 甲 2228 1 0) 其 数 == 1) 'plain switch restores hidden C++ body'.
    确认 (非 (语法 其 折叠 甲 0)) 'plain text cannot toggle stale native fold levels'.

    # Delete a genuinely collapsed header, then let Lexilla recompute levels.
    # No SETFOLDLEVEL calls or fabricated fold metadata are used in this fixture.
    删文 取 'int f() {\nreturn 1;\n}\n'.
    编 其 设文本 甲 删文.
    语法 其 选择 甲 'cpp'.
    语法 其 全折 甲 0.
    确认 ((窗 其 发送 甲 2228 1 0) 其 数 == 0) 'delete-header fixture starts with a collapsed real C++ body'.
    窗 其 发送 甲 2645 0 10.
    语法 其 变化 甲 0 10 (-1) 2.
    窗 其 发送 甲 4003 0 (-1).
    确认 ((编 其 文本 甲) == 'return 1;\n}\n') 'deleting collapsed C++ header preserves remaining source'.
    确认 ((窗 其 发送 甲 2236 0 0) 其 数 == 1) 'deleting C++ header restores every hidden child through native fold maintenance'.
    层 取 (窗 其 发送 甲 2223 0 0) 其 数.
    确认 (非 (策 其 是折头 层)) 'deleted C++ header is removed by Lexilla recomputation'.
    窗 其 发送 甲 2176 0 0.
    窗 其 发送 甲 4003 0 (-1).
    层 取 (窗 其 发送 甲 2223 0 0) 其 数.
    确认 ((编 其 文本 甲) == 删文 且 (策 其 是折头 层) 且 非 (编 其 已变 甲)) 'one undo restores C++ header, native fold level and original savepoint'.

    # Replace the collapsed document using the actual production large-mode
    # constructor. Its byte count is genuinely small, its STYLES_NONE flag real.
    语法 其 全折 甲 0.
    语法 其 遗忘 甲.
    流 取 编 其 开始载入 甲 32000000.
    编 其 追加文本 流 删文.
    编 其 完成载入 流.
    确认 ((窗 其 发送 甲 2379 0 0) 其 数 == 257) 'C++ replacement document really has TEXT_LARGE and STYLES_NONE'.
    确认 ((语法 其 选择 甲 'cpp') == 'plain') 'STYLES_NONE refuses C++ even below the byte threshold'.
    确认 ((窗 其 发送 甲 4002 0 0) 其 数 == 0 且 (窗 其 发送 甲 2243 2 0) 其 数 == 0) 'STYLES_NONE leaves no C++ lexer or fold margin'.
    确认 ((编 其 文本 甲) == 删文 且 (窗 其 发送 甲 2236 0 0) 其 数 == 1 且 非 (编 其 已变 甲)) 'no-style replacement preserves source and clean savepoint with every line visible'.
    确认 (非 (语法 其 全折 甲 0) 且 非 (语法 其 折叠 甲 0)) 'no-style replacement rejects stale C++ folding commands'.
    语法 其 遗忘 甲.
    流 取 编 其 开始载入 甲 1.
    编 其 追加文本 流 删文.
    编 其 完成载入 流.
    确认 ((语法 其 选择 甲 'cpp') == 'cpp' 且 (语法 其 全折 甲 0)) 'normal styled replacement restores functional C++ folding'.
    语法 其 全折 甲 1.

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
    # Native SHOW expands a folded trailing blank line before an append.
    # Preserve the original 22-byte fixture as a distinct regression.
    编 其 设文本 甲 删文.
    语法 其 选择 甲 'cpp'.
    语法 其 全折 甲 0.
    确认 ((窗 其 发送 甲 2228 1 0) 其 数 == 0 且 (窗 其 发送 甲 2228 3 0) 其 数 == 0) 'trailing blank EOF is inside the collapsed C++ fold'.
    窗 其 发文 甲 2282 1 'x'.
    确认 ((窗 其 发送 甲 2183 0 0) 其 数 == 23 且 (窗 其 发送 甲 2379 0 0) 其 数 == 256) 'append at hidden EOF retains real bytes and styled document options'.
    确认 ((窗 其 发送 甲 2230 0 0) 其 数 == 1 且 (窗 其 发送 甲 2236 0 0) 其 数 == 1) 'native SHOW automatically expands a hidden EOF before append'.
    窗 其 发送 甲 2176 0 0.
    确认 ((编 其 文本 甲) == 删文 且 非 (编 其 已变 甲)) 'hidden-EOF append single undo restores original 22-byte clean text'.
    确认 ((语法 其 全折 甲 0) 且 (窗 其 发送 甲 2228 1 0) 其 数 == 0) 'folding resumes after hidden-EOF append undo'.
    # Actually grow a styled, folded document beyond 32 MB. One long ASCII
    # padding line avoids fabricating GETLENGTH or millions of fixture lines.
    填文 取 'x'.
    循 20 次 填文 取 填文+填文. 环
    增长文 取 删文+'int padding;'.
    编 其 设文本 甲 增长文.
    语法 其 选择 甲 'cpp'.
    语法 其 全折 甲 0.
    确认 ((窗 其 发送 甲 2228 3 0) 其 数 == 1 且 (窗 其 发送 甲 2228 1 0) 其 数 == 0 且 (窗 其 发送 甲 2230 0 0) 其 数 == 0) 'growth starts with visible code at EOF outside the collapsed function'.
    # UTF8 includes a terminator and native buffers are capped at 16 MiB.
    # Real 1 MiB chunks share one Scintilla undo transaction.
    窗 其 发送 甲 2078 0 0.
    循 32 次 窗 其 发文 甲 2282 1048576 填文. 环
    窗 其 发送 甲 2079 0 0.
    确认 ((窗 其 发送 甲 2183 0 0) 其 数 == 33554466) 'C++ growth fixture contains real 32 MiB padding plus original 34 bytes'.
    显 'GROWTH_STATE options='+(((窗 其 发送 甲 2379 0 0) 其 数) 为 句)+' expanded='+(((窗 其 发送 甲 2230 0 0) 其 数) 为 句)+' header='+(((窗 其 发送 甲 2223 0 0) 其 数) 为 句)+' bodyVisible='+(((窗 其 发送 甲 2228 1 0) 其 数) 为 句)+' length='+(((窗 其 发送 甲 2183 0 0) 其 数) 为 句).
    确认 ((窗 其 发送 甲 2379 0 0) 其 数 == 256 且 (窗 其 发送 甲 2230 0 0) 其 数 == 0 且 (窗 其 发送 甲 2228 1 0) 其 数 == 0) 'growth retains styled document and its collapsed header'.
    确认 (非 (语法 其 全折 甲 0)) 'grown C++ document refuses another collapse-all above threshold'.
    确认 (语法 其 折叠 甲 0) 'grown C++ document still permits margin expansion'.
    确认 ((窗 其 发送 甲 2236 0 0) 其 数 == 1) 'margin expansion makes all grown-document lines reachable'.
    确认 (非 (语法 其 折叠 甲 0)) 'grown expanded C++ header cannot be collapsed again'.
    确认 (语法 其 全折 甲 1) 'grown C++ document always permits expand-all'.
    窗 其 发送 甲 2176 0 0.
    确认 ((编 其 文本 甲) == 增长文 且 非 (编 其 已变 甲)) 'one undo removes real growth and restores original C++ savepoint'.
    确认 (语法 其 全折 甲 0) 'C++ folding resumes after undo returns below threshold'.
    填文 取 ''.
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
