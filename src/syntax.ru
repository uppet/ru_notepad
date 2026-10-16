# Ru-owned selection, colours and lifetime policy; Lexilla owns C/C++ and JSON lexing.
# Import/initialise this module before registering any native window callback.
密 取 外言 '如:密'.
窗 取 外言 'win32.ru'.
词法状态 取 {'ready':假,'library':空,'warning':''}.
GetProcAddress 取 (窗 其 内核) 其 绑定 'GetProcAddress' (密 其 签名 (窗 其 PTR) ([(窗 其 PTR),(窗 其 PTR)]) 'win64').

# Preflight both loading and the export with ordinary Win32 result values. Missing
# dependencies must never reach a fatal native-library bind or discard a document.
库路径 取 (窗 其 目录)+'Lexilla.dll'.
路径存 取 密 其 UTF16 库路径.
预载成果 取 (窗 其 LoadLibraryExW) 其 调用 [路径存,空,2304].
路径存 其 关闭.
预载 取 窗 其 结果 预载成果.
若 预载 其 为空 则
    词法状态 其 增 'warning' ('Syntax highlighting is unavailable: Lexilla.dll could not be loaded (Windows error '+((预载成果 其 错误码) 为 句)+'). Your documents remain editable as plain text. Extract the complete Windows x64 package and keep Lexilla.dll beside ru_notepad.exe.').
另
    导出名 取 密 其 UTF8 'CreateLexer'.
    导出 取 窗 其 结果 (GetProcAddress 其 调用 [预载,导出名]).
    导出名 其 关闭.
    若 导出 其 为空 则
        词法状态 其 增 'warning' 'Syntax highlighting is unavailable: Lexilla.dll does not export CreateLexer. Your documents remain editable as plain text. Restore Lexilla.dll from the complete Windows x64 package.'.
    另
        词法库 取 密 其 动态库 库路径.
        CreateLexer 取 词法库 其 绑定 'CreateLexer' (密 其 签名 (窗 其 PTR) ([(窗 其 PTR)]) 'win64').
        # Keep the managed library alive for the process, including editor teardown.
        词法状态 其 增 'library' 词法库.
        词法状态 其 增 'ready' 真.
    然
    # Drop only our extra secure preload reference, never the managed library.
    窗 其 结果 ((窗 其 FreeLibrary) 其 调用 [预载]).
然

算 初始化:
    得 词法状态 其 查 'warning'.
法
算 名称 语言 为 句:
    若 语言 == 'cpp' 则 得 'C / C++'. 然
    若 语言 == 'json' 则 得 'JSON'. 然
    得 'Plain text'.
法
算 识别 路 为 句:
    位 取 路 其 量.
    后缀 取 ''.
    循
        若 位 <= 0 则 得 'plain'. 然
        位 取 位-1.
        字 取 路[位].
        若 字 == '/' 或 字 == '\\' 则 得 'plain'. 然
        若 字 == '.' 则 破. 然
        后缀 取 字+后缀.
        若 (后缀 其 量) > 4 则 得 'plain'. 然
    环
    小写 取 ''.
    大字 取 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.
    小字 取 'abcdefghijklmnopqrstuvwxyz'.
    位 取 0.
    循 后缀 其 量 次
        字 取 后缀[位].
        字位 取 0.
        循 26 次
            若 字 == 大字[字位] 则
                字 取 小字[字位].
                破.
            然
            字位 取 字位+1.
        环
        小写 取 小写+字.
        位 取 位+1.
    环
    若 小写 == 'json' 则 得 'json'. 然
    若 (['c','h','cc','hh','cpp','hpp','cxx','hxx','c++','h++','inl'] 其 含 小写) 则 得 'cpp'. 然
    得 'plain'.
法
算 性质 柄, 键 为 句, 值 为 句:
    键存 取 密 其 UTF8 键.
    值存 取 密 其 UTF8 值.
    窗 其 发指 柄 4004 ((窗 其 UP) 其 重释 (键存 其 地址)) 值存.
    键存 其 关闭.
    值存 其 关闭.
    得 空.
法
算 配色 柄, 样式 为 数, 色 为 数:
    窗 其 发送 柄 2051 样式 色.
    得 空.
法
算 清样式 柄:
    # Reset token colours only. STYLECLEARALL would also erase the line-number style.
    位 取 0.
    循 32 次
        窗 其 发送 柄 2051 位 2039583.
        窗 其 发送 柄 2052 位 16777215.
        窗 其 发送 柄 2053 位 0.
        窗 其 发送 柄 2054 位 0.
        位 取 位+1.
    环
    窗 其 发送 柄 2005 0 0. # SCI_CLEARDOCUMENTSTYLE, never text or undo.
    得 空.
法
算 纯文 柄:
    # Scintilla releases any prior ILexer5 when it replaces the lexer.
    窗 其 发送 柄 4033 0 0.
    清样式 柄.
    得 'plain'.
法
算 选择 柄, 语言 为 句:
    若 语言 != 'cpp' 且 语言 != 'json' 则 得 纯文 柄. 然
    若 非 (词法状态 其 查 'ready') 则 得 纯文 柄. 然
    名存 取 密 其 UTF8 语言.
    词法器 取 窗 其 结果 (CreateLexer 其 调用 [名存]).
    名存 其 关闭.
    若 词法器 其 为空 则
        词法状态 其 增 'warning' ('Syntax highlighting is unavailable for '+语言+'. Your document remains editable as plain text. Restore Lexilla.dll from the complete Windows x64 package.').
        得 纯文 柄.
    然
    # Transfer ownership immediately: do not free or reuse this pointer. Each
    # editor gets a fresh object. The pointer is explicitly reinterpreted as LPARAM.
    窗 其 发送 柄 2382 0 0. # clear any earlier Scintilla error before checked configuration
    窗 其 发送 柄 4033 0 ((窗 其 IP) 其 重释 词法器).
    清样式 柄.
    # Native incremental lexing handles edits. Never COLOURISE(0,-1) on each edit.
    窗 其 发送 柄 2692 1 0. # SC_IDLESTYLING_TOVISIBLE
    色板 取 [].
    若 语言 == 'cpp' 则
        窗 其 发文 柄 4005 0 'alignas alignof and and_eq asm atomic_cancel atomic_commit atomic_noexcept auto bitand bitor bool break case catch char char8_t char16_t char32_t class compl concept const consteval constexpr constinit const_cast continue co_await co_return co_yield decltype default delete do double dynamic_cast else enum explicit export extern false float for friend goto if inline int long mutable namespace new noexcept not not_eq nullptr operator or or_eq private protected public register reinterpret_cast requires return short signed sizeof static static_assert static_cast struct switch template this thread_local throw true try typedef typeid typename union unsigned using virtual void volatile wchar_t while xor xor_eq _Alignas _Alignof _Atomic _Bool _Complex _Generic _Imaginary _Noreturn _Static_assert _Thread_local'.
        性质 柄 'lexer.cpp.track.preprocessor' '0'.
        性质 柄 'lexer.cpp.escape.sequence' '1'.
        色板 取 [[1,3573283],[2,3573283],[3,3573283],[4,12665455],[5,12934144],[6,1381795],[7,1381795],[9,12665455],[10,4473924],[12,3023567],[15,3573283],[17,3573283],[18,3023567],[20,1381795],[23,3573283],[24,3573283],[27,12665455]].
    另
        窗 其 发文 柄 4005 0 'true false null'.
        性质 柄 'lexer.json.allow.comments' '0'.
        性质 柄 'lexer.json.escape.sequence' '1'.
        色板 取 [[1,12665455],[2,1381795],[3,3023567],[4,2514553],[5,12665455],[8,4473924],[9,1381795],[10,1381795],[11,12934144],[12,12934144],[13,3023567]].
    然
    # Apply one literal palette through a shared loop rather than specializing
    # the native wrapper separately for every style/colour combination.
    位 取 0.
    循 色板 其 量 次
        项 取 色板[位].
        配色 柄 项[0] 项[1].
        位 取 位+1.
    环
    预期 取 3.
    若 语言 == 'json' 则 预期 取 120. 然
    若 ((窗 其 发送 柄 2383 0 0) 其 数) != 0 或 ((窗 其 发送 柄 4002 0 0) 其 数) != 预期 则
        词法状态 其 增 'warning' ('Syntax highlighting could not be configured for '+语言+'. Your document remains editable as plain text.').
        # The object was already adopted above; SETILEXER(NULL) releases it.
        得 纯文 柄.
    然
    # Invalidate only; Scintilla requests native styling for visible text on paint.
    得 语言.
法
