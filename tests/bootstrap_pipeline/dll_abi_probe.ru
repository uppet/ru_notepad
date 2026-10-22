# Reuse exact application-owned C ABI pointer/callback acceptance fixtures.
# Each route runs in a fresh process against the three source-built DLLs.
密 取 外言 '如:密'.
内核 取 密 其 系统库 'kernel32.dll'.
开事件 取 内核 其 绑定 'OpenEventW' (密 其 签名 (密 其 指针) ([(密 其 u32),(密 其 i32),(密 其 指针)]) 'win64').
等事件 取 内核 其 绑定 'WaitForSingleObject' (密 其 签名 (密 其 u32) ([(密 其 指针),(密 其 u32)]) 'win64').
关事件 取 内核 其 绑定 'CloseHandle' (密 其 签名 (密 其 i32) ([(密 其 指针)]) 'win64').
窗 取 外言 '../../src/win32.ru'.
编辑 取 外言 '../editor_native.ru'.
如语 取 外言 '../ru_syntax_native.ru'.
段落 取 外言 '../markdown_native.ru'.
算 元初 参数 为 句 阵:
    若 (参数 其 量) != 2 则 卒 'FAIL: DLL ABI route count'. 然
    # Retain all three actual app-directory libraries through acknowledgement.
    编辑库 取 密 其 动态库 ((窗 其 目录)+'Scintilla.dll').
    词法库 取 密 其 动态库 ((窗 其 目录)+'Lexilla.dll').
    语法库 取 密 其 动态库 ((窗 其 目录)+'RuSyntax.dll').
    库们 取 [编辑库,词法库,语法库].
    路 取 参数[0].
    果 取 -1.
    若 路 == 'editor' 则 果 取 编辑 其 元初 []. 然
    若 路 == 'ru' 则 果 取 如语 其 元初 []. 然
    若 路 == 'markdown' 则 果 取 段落 其 元初 []. 然
    若 果 != 0 则 卒 'FAIL: native DLL ABI fixture'. 然
    # Keep the real DLLs mapped until the parent observes their exact paths and
    # hashes. The event is unique to this run; never wait indefinitely.
    名 取 密 其 UTF16 参数[1].
    事 取 开事件 其 调用 [1048576,0,名].
    若 事 其 为空 则 卒 'FAIL: owned handshake event'. 然
    等 取 等事件 其 调用 [事,50000].
    关 取 关事件 其 调用 [事].
    名 其 关闭.
    若 (等 其 数) != 0 或 (关 其 数) == 0 则 卒 'FAIL: DLL load acknowledgement'. 然
    若 (库们 其 量) != 3 则 卒 'FAIL: retained DLL set'. 然
    显 'BOOTSTRAP_DLL_ABI_PASS:'+路.
    得 0.
法
