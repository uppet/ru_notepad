# 0.1.2 main-level integration through real WM_COMMAND/Win32 callback dispatch.
# Separate entry keeps this feature suite independent of baseline lifecycle.
应用 取 外言 '../src/main.ru'.
窗 取 外言 '../src/win32.ru'.
编 取 外言 '../src/editor.ru'.
次数 取 [0].
作 确认 条件 为 事实 名 为 句:
    若 非 条件 则 卒 'FAIL: '+名. 然
    次数[0] 取 次数[0]+1.
    显 'PASS: '+名.
为
作 点折叠 柄:
    # Real Scintilla hit testing generates SCN_MARGINCLICK for the parent.
    横 取 ((窗 其 发送 柄 2243 0 0) 其 数)+((窗 其 发送 柄 2243 1 0) 其 数)+8.
    高 取 (窗 其 发送 柄 2279 0 0) 其 数.
    纵 取 ((窗 其 发送 柄 2165 0 0) 其 数)+高/2.
    纵 取 纵-纵%1.
    坐标 取 纵*65536+横.
    窗 其 发送 柄 513 1 坐标.
    窗 其 发送 柄 514 0 坐标.
为
算 元初 参数 为 句 阵:
    主 取 应用 其 初始化 [] 假.
    应用 其 切界面 'en' 假. # Stable synthetic expectation; never writes preferences.
    状态 取 应用 其 A.
    确认 ((窗 其 取文 (状态 其 查 'status')) 其 含 'Line EOL: None (EOF)') 'status bar reports untitled line EOL'.
    第一 取 应用 其 编辑柄.
    窗 其 发文 第一 2181 0 'first'.
    窗 其 发送 主 273 702 0.
    确认 (应用 其 脏 (应用 其 当前)) 'C++ styling preserves already-dirty state'.
    窗 其 发送 主 273 701 0.
    确认 (应用 其 脏 (应用 其 当前)) 'plain transition preserves already-dirty state'.
    确认 ((编 其 文本 第一) == 'first') 'dirty language changes preserve exact text'.
    应用 其 新页 'synthetic.cpp' 'int f() {\nreturn 1;\n}\n' 65001 假 ''.
    第二 取 应用 其 编辑柄.
    确认 (((应用 其 当前) 其 查 'language') == 'cpp') 'new/open document path selects actual C++ mode'.
    窗 其 发送 主 273 111 0.
    确认 ((状态 其 查 'active') == 0) 'previous tab command'.
    窗 其 发送 主 273 111 0.
    确认 ((状态 其 查 'active') == 1) 'previous tab wraps'.
    窗 其 发送 主 273 112 0.
    确认 ((状态 其 查 'active') == 0) 'next tab wraps'.
    窗 其 发送 主 273 112 0.
    确认 ((状态 其 查 'active') == 1) 'next tab command'.
    窗 其 发送 主 273 502 0.
    确认 ((窗 其 发送 第二 2374 0 0) 其 数 == 1) 'zoom-in command'.
    窗 其 发送 主 273 503 0.
    确认 ((窗 其 发送 第二 2374 0 0) 其 数 == 0) 'zoom-out command'.
    窗 其 发送 主 273 502 0.
    窗 其 发送 主 273 504 0.
    确认 ((窗 其 发送 第二 2374 0 0) 其 数 == 0) 'reset zoom command'.
    确认 ((窗 其 发送 第一 2374 0 0) 其 数 == 0) 'zoom commands remain document-local'.
    确认 (非 (应用 其 脏 (应用 其 当前))) 'tab and zoom commands do not dirty document'.
    窗 其 发送 主 273 702 0.
    确认 (((应用 其 当前) 其 查 'language') == 'cpp') 'language menu selects C/C++'.
    确认 ((窗 其 发送 第二 4002 0 0) 其 数 == 3) 'language menu installs real CPP lexer'.
    确认 ((窗 其 发送 第一 4002 0 0) 其 数 != 3) 'language selection is document-local'.
    确认 (非 (应用 其 脏 (应用 其 当前))) 'language selection preserves savepoint'.
    窗 其 发送 主 273 505 0.
    确认 ((窗 其 发送 第二 2228 1 0) 其 数 == 0) 'C++ WM_COMMAND collapse-all hides function body'.
    窗 其 发送 主 273 111 0.
    确认 ((窗 其 发送 第一 2243 2 0) 其 数 == 0) 'C++ folds do not leak to plain tab'.
    窗 其 发送 主 273 112 0.
    确认 ((窗 其 发送 第二 2228 1 0) 其 数 == 0) 'C++ collapsed state survives tab switching'.
    窗 其 发送 主 273 506 0.
    确认 ((窗 其 发送 第二 2228 1 0) 其 数 == 1) 'C++ WM_COMMAND expand-all restores body'.
    点折叠 第二.
    确认 ((窗 其 发送 第二 2228 1 0) 其 数 == 0) 'C++ real margin click dispatch collapses exactly once'.
    点折叠 第二.
    确认 ((窗 其 发送 第二 2228 1 0) 其 数 == 1) 'C++ second real margin click expands exactly once'.
    确认 (非 (应用 其 脏 (应用 其 当前))) 'C++ application folding preserves clean savepoint'.
    窗 其 发送 主 273 505 0.
    窗 其 发送 主 273 703 0.
    确认 (((应用 其 当前) 其 查 'language') == 'json') 'language menu selects JSON'.
    确认 ((窗 其 发送 第二 2228 1 0) 其 数 == 1) 'C++ to JSON menu restores hidden body'.
    窗 其 发送 主 273 701 0.
    确认 (((应用 其 当前) 其 查 'language') == 'plain') 'language menu restores plain text'.
    确认 ((编 其 文本 第二) == 'int f() {\nreturn 1;\n}\n') 'language commands preserve exact text'.
    窗 其 发送 第一 2176 0 0.
    确认 ((编 其 文本 第一) == '') 'styling preserved the original undo history'.
    # Search integration uses actual WM_COMMAND dispatch, not direct policy calls.
    # Successful hits avoid modal no-match notices in this hidden-window fixture.
    应用 其 新页 'search.txt' 'alpha alphabet alpha' 65001 假 ''.
    搜柄 取 应用 其 编辑柄.
    确认 ((窗 其 发送 (状态 其 查 'case') 240 0 0) 其 数 == 1) 'search defaults to matching case'.
    确认 ((窗 其 发送 (状态 其 查 'whole') 240 0 0) 其 数 == 0) 'whole-word option defaults off'.
    确认 ((窗 其 发送 (状态 其 查 'searchWrap') 240 0 0) 其 数 == 1) 'search wrap defaults on'.
    窗 其 发送 主 273 301 0.
    确认 (状态 其 查 'search') 'find command opens search row'.
    窗 其 标题 (状态 其 查 'find') 'alpha'.
    窗 其 发送 搜柄 2160 0 0.
    窗 其 发送 主 273 303 0.
    确认 ((窗 其 发送 搜柄 2143 0 0) 其 数 == 0) 'next command finds first literal match'.
    窗 其 发送 主 273 303 0.
    确认 ((窗 其 发送 搜柄 2143 0 0) 其 数 == 6) 'legacy default still finds partial word'.
    窗 其 发送 主 273 308 0.
    确认 ((窗 其 发送 搜柄 2143 0 0) 其 数 == 0) 'previous WM_COMMAND moves to preceding match'.
    窗 其 发送 (状态 其 查 'whole') 241 1 0.
    窗 其 发送 主 273 303 0.
    确认 ((窗 其 发送 搜柄 2143 0 0) 其 数 == 15) 'whole-word checkbox skips partial word'.
    窗 其 发送 主 273 303 0.
    确认 ((窗 其 发送 搜柄 2143 0 0) 其 数 == 0) 'next command wraps when enabled'.
    窗 其 发送 主 273 308 0.
    确认 ((窗 其 发送 搜柄 2143 0 0) 其 数 == 15) 'previous command wraps when enabled'.
    窗 其 发送 (状态 其 查 'searchWrap') 241 0 0.
    窗 其 发送 主 273 308 0.
    确认 ((窗 其 发送 搜柄 2143 0 0) 其 数 == 0) 'previous without wrap finds eligible preceding match'.
    窗 其 发送 主 273 307 0.
    确认 (非 (状态 其 查 'search')) 'close command hides search row'.
    窗 其 发送 主 273 302 0.
    确认 (状态 其 查 'search') 'replace command reopens search row'.
    确认 ((窗 其 发送 (状态 其 查 'whole') 240 0 0) 其 数 == 1) 'whole-word survives search-row close and reopen'.
    确认 ((窗 其 发送 (状态 其 查 'searchWrap') 240 0 0) 其 数 == 0) 'wrap choice survives search-row close and reopen'.
    窗 其 发送 主 273 111 0.
    确认 ((状态 其 查 'active') == 1) 'search fixture switches away to previous document'.
    窗 其 发送 主 273 112 0.
    确认 ((状态 其 查 'active') == 2) 'search fixture returns to its document'.
    确认 ((窗 其 发送 (状态 其 查 'whole') 240 0 0) 其 数 == 1) 'whole-word choice is retained across tab switching'.
    确认 ((窗 其 发送 (状态 其 查 'searchWrap') 240 0 0) 其 数 == 0) 'wrap choice is retained across tab switching'.
    窗 其 标题 (状态 其 查 'replace') 'X'.
    窗 其 发送 搜柄 2160 0 5.
    窗 其 发送 主 273 304 0.
    确认 ((编 其 文本 搜柄) == 'X alphabet alpha') 'replace-current command honors whole-word option'.
    确认 ((窗 其 发送 搜柄 2143 0 0) 其 数 == 11) 'replace-current command advances to next whole-word match'.
    窗 其 发送 搜柄 2176 0 0.
    确认 ((编 其 文本 搜柄) == 'alpha alphabet alpha') 'application search replacement is undoable'.
    确认 (非 (应用 其 脏 (应用 其 当前))) 'search replacement undo restores clean document'.
    窗 其 标题 (状态 其 查 'find') ''.
    窗 其 发送 搜柄 2160 20 15.
    窗 其 发送 主 273 307 0.
    窗 其 发送 主 273 308 0.
    确认 (状态 其 查 'search') 'previous with empty field opens search instead of searching'.
    确认 ((窗 其 发送 搜柄 2008 0 0) 其 数 == 15) 'empty application search preserves document caret'.
    确认 ((窗 其 发送 搜柄 2009 0 0) 其 数 == 20) 'empty application search preserves document anchor'.
    确认 ((编 其 文本 搜柄) == 'alpha alphabet alpha') 'application search lifecycle preserves bytes'.
    确认 (非 (应用 其 脏 (应用 其 当前))) 'application search lifecycle preserves savepoint'.
    确认 (应用 其 关程序) 'feature fixture closes normally without dirty prompts'.
    显 'TOTAL PASS: '+(次数[0] 为 句).
    得 0.
法
