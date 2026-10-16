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
算 元初 参数 为 句 阵:
    主 取 应用 其 初始化 [] 假.
    状态 取 应用 其 A.
    确认 ((窗 其 取文 (状态 其 查 'status')) 其 含 'Line EOL: None (EOF)') 'status bar reports untitled line EOL'.
    第一 取 应用 其 编辑柄.
    窗 其 发文 第一 2181 0 'first'.
    窗 其 发送 主 273 702 0.
    确认 (应用 其 脏 (应用 其 当前)) 'C++ styling preserves already-dirty state'.
    窗 其 发送 主 273 701 0.
    确认 (应用 其 脏 (应用 其 当前)) 'plain transition preserves already-dirty state'.
    确认 ((编 其 文本 第一) == 'first') 'dirty language changes preserve exact text'.
    应用 其 新页 'synthetic.cpp' 'second' 65001 假 ''.
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
    窗 其 发送 主 273 703 0.
    确认 (((应用 其 当前) 其 查 'language') == 'json') 'language menu selects JSON'.
    窗 其 发送 主 273 701 0.
    确认 (((应用 其 当前) 其 查 'language') == 'plain') 'language menu restores plain text'.
    确认 ((编 其 文本 第二) == 'second') 'language commands preserve exact text'.
    窗 其 发送 第一 2176 0 0.
    确认 ((编 其 文本 第一) == '') 'styling preserved the original undo history'.
    确认 (应用 其 关程序) 'feature fixture closes normally without dirty prompts'.
    显 'TOTAL PASS: '+(次数[0] 为 句).
    得 0.
法
