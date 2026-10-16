# Real hidden Win32 application/control test, no Python runtime or mock DLL.
应用 取 外言 '../src/main.ru'.
窗 取 外言 '../src/win32.ru'.
编 取 外言 '../src/editor.ru'.
次数 取 [0].
作 确认 条件 为 事实, 文 为 句:
    若 非 条件 则 卒 ('FAIL: '+文). 然
    次数[0] 取 次数[0]+1.
    显 'PASS: '+文.
为
算 元初 参数 为 句 阵:
    主 取 应用 其 初始化 [] 假.
    状态 取 应用 其 A.
    确认 (((状态 其 查 'docs') 其 量) == 1) 'startup owns one untitled document'.
    确认 ((状态 其 查 'active') == 0) 'first tab active'.
    确认 (非 (应用 其 脏 (应用 其 当前))) 'new document clean'.
    第一 取 应用 其 编辑柄.
    窗 其 发文 第一 2181 0 'first'.
    确认 (应用 其 脏 (应用 其 当前)) 'native edit marks active document dirty'.
    确认 ((窗 其 发送 主 17 0 0) 其 数 == 0) 'unsaved document vetoes orderly end-session'.
    应用 其 新页 '' 'second' 65001 假 ''.
    第二 取 应用 其 编辑柄.
    确认 (((状态 其 查 'docs') 其 量) == 2) 'second tab created'.
    确认 ((编 其 文本 第二) == 'second') 'second document exact text'.
    确认 ((编 其 文本 第一) == 'first') 'first document retained'.
    应用 其 切页 0.
    确认 (((应用 其 编辑柄) 其 句) == (第一 其 句)) 'switch returns first native editor'.
    窗 其 发送 第一 2176 0 0.
    确认 ((编 其 文本 第一) == '') 'first editor retains independent undo history'.
    确认 (非 (应用 其 脏 (应用 其 当前))) 'undo to initial savepoint is clean'.
    应用 其 切页 1.
    确认 ((编 其 文本 第二) == 'second') 'undo in first never changes second'.
    应用 其 命令 501.
    确认 ((窗 其 发送 第二 2269 0 0) 其 数 == 1) 'wrap enabled for current document'.
    确认 ((窗 其 发送 第一 2269 0 0) 其 数 == 0) 'wrap is document-local'.
    应用 其 寻栏 真.
    确认 (状态 其 查 'search') 'search bar opens'.
    应用 其 寻栏 假.
    确认 (非 (状态 其 查 'search')) 'search bar closes'.
    确认 (应用 其 关页) 'clean tab closes without prompt'.
    确认 (((状态 其 查 'docs') 其 量) == 1) 'one tab remains'.
    确认 (应用 其 关页) 'last clean tab closes'.
    确认 (((状态 其 查 'docs') 其 量) == 1) 'closing last tab creates clean untitled'.
    确认 (非 (应用 其 脏 (应用 其 当前))) 'replacement untitled clean'.
    确认 ((窗 其 发送 主 17 0 0) 其 数 == 1) 'clean documents allow orderly end-session'.
    确认 (应用 其 关程序) 'clean app shutdown'.
    显 'TOTAL PASS: '+(次数[0] 为 句).
    得 0.
法
