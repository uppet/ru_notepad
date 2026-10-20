# Ru-owned guarded selection; Lexilla colours C/C++, JSON and Markdown.
# Markdown folds use a separate bounded Ru policy, never lexer style heuristics.
# Import/initialise this module before registering any native window callback.
密 取 外言 '如:密'.
窗 取 外言 'win32.ru'.
策 取 外言 'syntax_policy.ru'.
如语 取 外言 'ru_syntax.ru'.
标语 取 外言 'markdown_syntax.ru'.
_选择们 取 {}.
_选择序 取 [0].
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
    词法状态 其 增 'warning' ('C/C++, JSON and Markdown syntax highlighting is unavailable: Lexilla.dll could not be loaded (Windows error '+((预载成果 其 错误码) 为 句)+'). Those formats remain editable as plain text; Ru highlighting uses its separate RuSyntax.dll helper. Extract the complete Windows x64 package and keep Lexilla.dll beside ru_notepad.exe.').
另
    导出名 取 密 其 UTF8 'CreateLexer'.
    导出 取 窗 其 结果 (GetProcAddress 其 调用 [预载,导出名]).
    导出名 其 关闭.
    若 导出 其 为空 则
        词法状态 其 增 'warning' 'C/C++, JSON and Markdown syntax highlighting is unavailable: Lexilla.dll does not export CreateLexer. Those formats remain editable as plain text; Ru highlighting uses its separate RuSyntax.dll helper. Restore Lexilla.dll from the complete Windows x64 package.'.
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
    文 取 词法状态 其 查 'warning'.
    如警告 取 如语 其 初始化.
    若 如警告 != '' 则
        若 文 != '' 则 文 取 文+'\n\n'. 然
        文 取 文+如警告.
    然
    得 文.
法
算 名称 语言 为 句:
    得 策 其 名称 语言.
法
算 识别 路 为 句:
    得 策 其 识别 路.
法
# The owner must call 遗忘 before replacing a document or destroying its HWND.
# Checks stop later calls after a callback invalidates selection; no claim is made
# that an arbitrary subclass may swap documents while forwarding a mutation.
算 _验选择 态 柄:
    当前 取 _选择们 其 查 (柄 其 句).
    若 当前 == 空 或 当前['token'] != 态['token'] 则 卒 'Syntax selection was superseded.'. 然
    若 非 (如语 其 _存在 柄) 或 非 (如语 其 _同线程 柄) 则 卒 'Syntax editor is unavailable.'. 然
    文档 取 (窗 其 发送 柄 2357 0 0) 其 句.
    当前 取 _选择们 其 查 (柄 其 句).
    若 当前 == 空 或 当前['token'] != 态['token'] 或 文档 != 态['document'] 则 卒 'Syntax document changed during selection.'. 然
    若 非 (如语 其 _存在 柄) 或 非 (如语 其 _同线程 柄) 则 卒 'Syntax editor closed during selection.'. 然
    得 空.
法
算 _新选择 柄:
    若 非 (如语 其 _存在 柄) 或 非 (如语 其 _同线程 柄) 则 卒 'Syntax selection requires a live owned-thread editor.'. 然
    若 _选择序[0] >= 9007199254740990 则 卒 'Syntax selection counter exhausted.'. 然
    _选择序[0] 取 _选择序[0]+1.
    态 取 {'token':_选择序[0],'document':''}.
    _选择们 其 增 (柄 其 句) 态.
    文档 取 (窗 其 发送 柄 2357 0 0) 其 句.
    当前 取 _选择们 其 查 (柄 其 句).
    若 当前 == 空 或 当前['token'] != 态['token'] 则 卒 'Syntax selection was superseded.'. 然
    态 其 增 'document' 文档.
    _验选择 态 柄.
    得 态.
法
算 _发设 态 柄 号 为 数 宽 为 数 长 为 数:
    _验选择 态 柄.
    果 取 窗 其 发送 柄 号 宽 长.
    _验选择 态 柄.
    得 果.
法
算 _发文设 态 柄 号 为 数 宽 为 数 文 为 句:
    _验选择 态 柄.
    果 取 窗 其 发文 柄 号 宽 文.
    _验选择 态 柄.
    得 果.
法
算 _性质 态 柄 键 为 句 值 为 句:
    键存 取 密 其 UTF8 键.
    值存 取 密 其 UTF8 值.
    试
        _验选择 态 柄.
        窗 其 发指 柄 4004 ((窗 其 UP) 其 重释 (键存 其 地址)) 值存.
        _验选择 态 柄.
    救 原因
        键存 其 关闭.
        值存 其 关闭.
        卒 原因.
    终
    键存 其 关闭.
    值存 其 关闭.
    得 空.
法
算 _配色 态 柄 样式 为 数 色 为 数:
    _发设 态 柄 2051 样式 色.
    得 空.
法
算 _清样式 态 柄:
    位 取 0.
    循 32 次
        _发设 态 柄 2051 位 2039583.
        _发设 态 柄 2052 位 16777215.
        _发设 态 柄 2053 位 0.
        _发设 态 柄 2054 位 0.
        位 取 位+1.
    环
    _发设 态 柄 2005 0 0.
    得 空.
法
算 _停止折叠 态 柄:
    如语 其 遗忘 柄.
    标语 其 遗忘 柄.
    _发设 态 柄 2662 1 0.
    行数 取 (_发设 态 柄 2154 0 0) 其 数.
    若 行数 > 0 则 _发设 态 柄 2226 0 (行数-1). 然
    _发设 态 柄 2663 0 0.
    _发设 态 柄 2242 2 0.
    得 空.
法
算 _纯文 态 柄:
    # Internal: _选择 already invalidated both folders before this branch.
    _发设 态 柄 4033 0 0.
    _清样式 态 柄.
    得 'plain'.
法
算 _选择 态 柄, 语言 为 句:
    _停止折叠 态 柄.
    若 语言 == 'ru' 则
        _清样式 态 柄.
        _验选择 态 柄.
        结果 取 如语 其 选择 柄.
        _验选择 态 柄.
        得 结果.
    然
    若 语言 != 'cpp' 且 语言 != 'json' 且 语言 != 'markdown' 则 得 _纯文 态 柄. 然
    若 非 (词法状态 其 查 'ready') 则 得 _纯文 态 柄. 然
    若 (如语 其 _受限 柄) 则 得 _纯文 态 柄. 然
    _发设 态 柄 2382 0 0.
    名存 取 密 其 UTF8 语言.
    词法器 取 窗 其 结果 (CreateLexer 其 调用 [名存]).
    若 词法器 其 为空 则
        名存 其 关闭.
        词法状态 其 增 'warning' ('Syntax highlighting is unavailable for '+语言+'. Your document remains editable as plain text. Restore Lexilla.dll from the complete Windows x64 package.').
        得 _纯文 态 柄.
    然
    # Transfer ownership immediately: do not free or reuse this pointer. Each
    # editor gets a fresh object. The pointer is explicitly reinterpreted as LPARAM.
    窗 其 发送 柄 4033 0 ((窗 其 IP) 其 重释 词法器).
    名存 其 关闭.
    _验选择 态 柄.
    _清样式 态 柄.
    # Native incremental lexing handles edits. Never COLOURISE(0,-1) on each edit.
    _发设 态 柄 2692 1 0. # SC_IDLESTYLING_TOVISIBLE
    色板 取 [].
    若 语言 == 'cpp' 则
        _发文设 态 柄 4005 0 'alignas alignof and and_eq asm atomic_cancel atomic_commit atomic_noexcept auto bitand bitor bool break case catch char char8_t char16_t char32_t class compl concept const consteval constexpr constinit const_cast continue co_await co_return co_yield decltype default delete do double dynamic_cast else enum explicit export extern false float for friend goto if inline int long mutable namespace new noexcept not not_eq nullptr operator or or_eq private protected public register reinterpret_cast requires return short signed sizeof static static_assert static_cast struct switch template this thread_local throw true try typedef typeid typename union unsigned using virtual void volatile wchar_t while xor xor_eq _Alignas _Alignof _Atomic _Bool _Complex _Generic _Imaginary _Noreturn _Static_assert _Thread_local'.
        _性质 态 柄 'lexer.cpp.track.preprocessor' '0'.
        _性质 态 柄 'lexer.cpp.escape.sequence' '1'.
        # Lexilla defaults fold to false. Native syntax, comments and conditional
        # directives supply levels; Scintilla owns incremental fold maintenance.
        _性质 态 柄 'fold' '1'.
        _性质 态 柄 'fold.comment' '1'.
        _性质 态 柄 'fold.preprocessor' '1'.
        色板 取 [[1,3573283],[2,3573283],[3,3573283],[4,12665455],[5,12934144],[6,1381795],[7,1381795],[9,12665455],[10,4473924],[12,3023567],[15,3573283],[17,3573283],[18,3023567],[20,1381795],[23,3573283],[24,3573283],[27,12665455]].
    另 若 语言 == 'json' 则
        _发文设 态 柄 4005 0 'true false null'.
        _性质 态 柄 'lexer.json.allow.comments' '0'.
        _性质 态 柄 'lexer.json.escape.sequence' '1'.
        色板 取 [[1,12665455],[2,1381795],[3,3023567],[4,2514553],[5,12665455],[8,4473924],[9,1381795],[10,1381795],[11,12934144],[12,12934144],[13,3023567]].
    另
        色板 取 [[2,12934144],[3,12934144],[4,12665455],[5,12665455],[6,12934144],[7,12934144],[8,12934144],[9,12934144],[10,12934144],[11,12934144],[13,2514553],[14,2514553],[15,3573283],[16,8421504],[17,4473924],[18,12665455],[19,1381795],[20,1381795],[21,1381795]].
    然 然
    # Apply one literal palette through a shared loop rather than specializing
    # the native wrapper separately for every style/colour combination.
    位 取 0.
    循 色板 其 量 次
        项 取 色板[位].
        _配色 态 柄 项[0] 项[1].
        位 取 位+1.
    环
    预期 取 3.
    若 语言 == 'json' 则 预期 取 120. 然
    若 语言 == 'markdown' 则 预期 取 98. 然
    若 ((_发设 态 柄 2383 0 0) 其 数) != 0 或 ((_发设 态 柄 4002 0 0) 其 数) != 预期 则
        词法状态 其 增 'warning' ('Syntax highlighting could not be configured for '+语言+'. Your document remains editable as plain text.').
        # The object was already adopted above; SETILEXER(NULL) releases it.
        得 _纯文 态 柄.
    然
    若 语言 == 'cpp' 则
        如语 其 _配折叠 柄.
        _验选择 态 柄.
    然
    若 语言 == 'markdown' 则
        # CLEARDOCUMENTSTYLE above writes zero styles through EOF. Markdown has
        # no keyword/property update to invalidate that prefix: reset only the
        # styling cursor so ordinary paint can request native Lexilla colouring.
        _发设 态 柄 2032 0 0.
        已选 取 标语 其 选择 柄.
        _验选择 态 柄.
        若 已选 != 'markdown' 则 得 _纯文 态 柄. 然
    然
    # Invalidate only; Scintilla requests native styling for visible text on paint.
    得 语言.
法

算 选择 柄 语言 为 句:
    态 取 _新选择 柄.
    得 _选择 态 柄 语言.
法
算 纯文 柄:
    得 选择 柄 'plain'.
法

算 登记直属 柄 父:
    若 (标语 其 状态 柄) != 空 则 得 标语 其 登记直属 柄 父. 然
    得 如语 其 登记直属 柄 父.
法

# Container requests always carry the originating HWND, never the active tab.
算 遗忘 柄:
    _选择们 其 除 (柄 其 句).
    标语 其 遗忘 柄.
    得 如语 其 遗忘 柄.
法
算 请求 柄 位置 为 数:
    得 如语 其 请求 柄 位置.
法
算 变化 柄 位置 为 数 长度 为 数 加行 为 数 修改 为 数:
    若 修改 % 4 != 0 则 _选择们 其 除 (柄 其 句). 然
    标语 其 变化 柄 位置 长度 加行 修改.
    得 如语 其 变化 柄 位置 长度 加行 修改.
法
算 推进 柄 预算 为 数:
    若 (标语 其 状态 柄) != 空 则 得 标语 其 推进 柄 预算. 然
    得 如语 其 推进 柄 预算.
法
算 待办 柄:
    若 (标语 其 状态 柄) != 空 则 得 标语 其 待办 柄. 然
    得 如语 其 待办 柄.
法
算 状态 柄:
    若 (标语 其 状态 柄) != 空 则 得 标语 其 状态 柄. 然
    得 如语 其 状态 柄.
法
算 排空 柄:
    若 (标语 其 状态 柄) != 空 则 得 标语 其 排空 柄. 然
    得 如语 其 排空 柄.
法
# Query the actual lexer, not selection tokens (text edits invalidate those).
# Margin width also rejects a disabled or partially configured lexer.
算 _原生折叠 柄:
    若 非 (如语 其 _存在 柄) 或 非 (如语 其 _同线程 柄) 则 得 假. 然
    得 ((窗 其 发送 柄 4002 0 0) 其 数 == 3) 且 ((窗 其 发送 柄 2243 2 0) 其 数 > 0).
法
算 折叠 柄 位置 为 数:
    若 _原生折叠 柄 则
        态 取 _新选择 柄.
        若 位置 < 0 或 位置 > ((_发设 态 柄 2183 0 0) 其 数) 则 得 假. 然
        行 取 (_发设 态 柄 2166 位置 0) 其 数.
        层 取 (_发设 态 柄 2223 行 0) 其 数.
        # Native levels also pack the NEXT level in the upper 16 bits.
        若 非 (策 其 是折头 层) 则 得 假. 然
        若 (如语 其 _受限 柄) 且 ((_发设 态 柄 2230 行 0) 其 数 != 0) 则 得 假. 然
        _发设 态 柄 2231 行 0.
        得 真.
    然
    若 (标语 其 状态 柄) != 空 则 得 标语 其 折叠 柄 位置. 然
    得 如语 其 折叠 柄 位置.
法
算 全折 柄 动作 为 数:
    若 _原生折叠 柄 则
        若 动作 < 0 或 动作 > 2 或 动作 % 1 != 0 则 得 假. 然
        # Expansion stays available if an edited document grows past 32 MB.
        若 动作 != 1 且 (如语 其 _受限 柄) 则 得 假. 然
        态 取 _新选择 柄.
        # Explicit collapse-all lets Scintilla EnsureStyledTo(EOF) once; normal
        # selection, painting and text edits keep the existing lazy native path.
        _发设 态 柄 2662 动作 0.
        得 真.
    然
    若 (标语 其 状态 柄) != 空 则 得 标语 其 全折 柄 动作. 然
    得 如语 其 全折 柄 动作.
法

算 时刻:
    得 如语 其 时刻.
法

算 设置折叠 柄 开启 为 事实:
    得 标语 其 设置折叠 柄 开启.
法
