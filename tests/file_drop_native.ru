# GetWindowSubclass requires the Common Controls v6 application manifest.
# Build this console fixture with the same embedded app.rc/app.manifest as the GUI.
密 取 外言 '如:密'.
窗 取 外言 '../src/win32.ru'.
拖 取 外言 '../src/file_drop.ru'.
夹 取 外言 './drop_fixture.ru'.
_GetWindowLongW 取 (窗 其 用户) 其 绑定 'GetWindowLongW' (密 其 签名 (窗 其 I) ([(窗 其 PTR),(窗 其 I)]) 'win64').
_GetWindowSubclass 取 (窗 其 控件) 其 绑定 'GetWindowSubclass' (密 其 签名 (窗 其 I) ([(窗 其 PTR),(窗 其 PTR),(窗 其 UP),(窗 其 PTR)]) 'win64').
_引用型 取 密 其 结构 [['parent',(窗 其 UP)]].
次数 取 [0].
状态 取 {'paths':[],'messages':0,'error':''}.
作 确认 条件 为 事实, 文 为 句:
    若 非 条件 则 卒 'FAIL: '+文. 然
    次数[0] 取 次数[0]+1.
    显 'PASS: '+文.
为
算 过程 柄, 消息, 宽, 长:
    若 消息 其 数 == 563 则
        状态 其 增 'messages' ((状态 其 查 'messages')+1).
        试
            状态 其 增 'paths' (拖 其 接收 ((窗 其 PTR) 其 重释 宽)).
        救 原因
            状态 其 增 'error' 原因.
        终
        得 0.
    然
    得 窗 其 结果 ((窗 其 DefWindowProcW) 其 调用 [柄,消息,宽,长]).
法
作 应拒绝 柄, 名 为 句:
    拒绝 取 [假].
    试 拖 其 接收 柄. 救 原因 拒绝[0] 取 真. 终
    确认 拒绝[0] 名.
    确认 (夹 其 已释放 柄) (名+' releases the owned HDROP').
为
算 元初 参数 为 句 阵:
    编辑库 取 密 其 动态库 ((窗 其 目录)+'Scintilla.dll').
    类名 取 密 其 UTF16 'RuNotepad.DropFixture'.
    实例 取 窗 其 成功 ((窗 其 GetModuleHandleW) 其 调用 [空]) 'instance'.
    回调 取 密 其 回调 (窗 其 WNDPROC) (算 过程) 0.
    类 取 (窗 其 WNDCLASS) 其 新建.
    类 其 写 'size' ((窗 其 WNDCLASS) 其 大小).
    类 其 写 'proc' (回调 其 地址).
    类 其 写 'instance' 实例.
    类 其 写 'name' (类名 其 地址).
    窗 其 成功 ((窗 其 RegisterClassExW) 其 调用 [类]) 'RegisterClassExW'.
    主 取 窗 其 控制 空 实例 'RuNotepad.DropFixture' 'synthetic file-drop fixture' 13565952 0.
    拖 其 启用 主.
    风格 取 (窗 其 结果 (_GetWindowLongW 其 调用 [主,-20])) 其 数.
    确认 ((风格 % 32) >= 16) 'DragAcceptFiles enables WS_EX_ACCEPTFILES on real HWND'.
    长路 取 'C:\\'.
    循 200 次 长路 取 长路+'folder segment\\'. 环
    长路 取 长路+'超过MAX_PATH.txt'.
    路们 取 ['C:\\文档 with spaces\\甲😀.txt','C:\\source\\two.ru',长路].
    柄 取 夹 其 创建 路们.
    确认 (非 (夹 其 已释放 柄)) 'synthetic HDROP owns live movable global memory'.
    窗 其 发送 主 563 ((窗 其 UP) 其 重释 柄) 0.
    收到 取 状态 其 查 'paths'.
    确认 ((状态 其 查 'messages') == 1) 'real WM_DROPFILES dispatch reaches the receiving HWND'.
    确认 ((状态 其 查 'error') == '') 'Unicode multiple-path drop decodes without error'.
    确认 ((收到 其 量) == 3) 'all dropped paths are retained in original order'.
    确认 (收到[0] == 路们[0]) 'Unicode astral characters and spaces preserved exactly'.
    确认 (收到[1] == 路们[1]) 'second dropped path preserved exactly'.
    确认 (收到[2] == 长路) 'dynamic path buffer handles paths longer than MAX_PATH'.
    确认 (夹 其 已释放 柄) 'successful WM_DROPFILES releases HDROP before caller opens files'.
    柄 取 夹 其 创建 [].
    空列 取 拖 其 接收 柄.
    确认 ((空列 其 量) == 0) 'empty shell drop returns an empty path list'.
    确认 (夹 其 已释放 柄) 'empty shell drop releases its global allocation'.
    应拒绝 (夹 其 无效编码 55296) 'unpaired high surrogate is rejected without partial paths'.
    应拒绝 (夹 其 无效编码 56320) 'unpaired low surrogate is rejected without partial paths'.
    多路 取 [].
    循 65 次 多路 其 增 'C:\\one.txt'. 环
    应拒绝 (夹 其 创建 多路) 'more than 64 paths is rejected as one whole drop'.
    过长 取 'x'.
    循 15 次 过长 取 过长+过长. 环
    过长 取 过长[:32001].
    应拒绝 (夹 其 创建 [过长]) 'path longer than 32000 UTF-16 units is rejected'.
    边界 取 过长[:32000].
    柄 取 夹 其 创建 [边界].
    收到 取 拖 其 接收 柄.
    确认 (收到[0] == 边界) '32000 UTF-16-unit boundary is retained exactly'.
    确认 (夹 其 已释放 柄) 'boundary-length path releases its allocation'.
    全释放 取 真.
    循 32 次
        柄 取 夹 其 创建 路们.
        拖 其 接收 柄.
        若 非 (夹 其 已释放 柄) 则 全释放 取 假. 然
    环
    确认 全释放 'repeated multi-path drops leave no owned global allocations'.
    # A real Scintilla child has an OLE text-only drop target registered during
    # WM_CREATE. Verify its removal and the child HWND route, not only top-level.
    子 取 窗 其 控制 主 实例 'Scintilla' '' 1073807360 71.
    撤销 取 拖 其 启用编辑器 子 主.
    确认 (撤销 == 0) 'real Scintilla OLE text target is successfully revoked'.
    风格 取 (窗 其 结果 (_GetWindowLongW 其 调用 [子,-20])) 其 数.
    确认 ((风格 % 32) >= 16) 'Scintilla editor body enables legacy shell file drops'.
    子回调址 取 ((拖 其 _子回调)[0]) 其 地址.
    父存 取 _引用型 其 新建.
    有钩 取 (窗 其 结果 (_GetWindowSubclass 其 调用 [子,子回调址,(拖 其 _子类编号),父存])) 其 数.
    确认 (有钩 == 1) 'shared file-drop subclass is installed on real editor HWND'.
    确认 (((父存 其 读 'parent') 其 句) == (((窗 其 UP) 其 重释 主) 其 句)) 'subclass reference retains the exact owning parent HWND'.
    撤销 取 拖 其 启用编辑器 子 主.
    确认 (撤销 == -2147221248) 'repeat enable accepts only the already-unregistered OLE state'.
    拒绝 取 [假].
    试 拖 其 启用编辑器 子 子. 救 原因 拒绝[0] 取 真. 终
    确认 拒绝[0] 'child routing rejects a window other than its actual parent'.
    窗 其 发文 子 2181 0 'unchanged'.
    柄 取 夹 其 创建 路们.
    窗 其 发送 子 563 ((窗 其 UP) 其 重释 柄) 0.
    收到 取 状态 其 查 'paths'.
    确认 ((状态 其 查 'messages') == 2) 'editor-body WM_DROPFILES forwards synchronously to parent exactly once'.
    确认 ((收到 其 量) == 3 且 收到[0] == 路们[0] 且 收到[2] == 长路) 'child forwarding preserves the complete Unicode and long-path list'.
    确认 ((状态 其 查 'error') == '') 'child route does not report a callback failure'.
    确认 (夹 其 已释放 柄) 'parent alone consumes the HDROP forwarded from the editor body'.
    确认 ((窗 其 发送 子 2183 0 0) 其 数 == 9) 'file drops do not insert text and ordinary Scintilla messages still work'.
    柄 取 夹 其 无效编码 55296.
    窗 其 发送 子 563 ((窗 其 UP) 其 重释 柄) 0.
    确认 ((状态 其 查 'messages') == 3 且 (状态 其 查 'error') != '') 'malformed child drop reaches normal parent error handling'.
    确认 (夹 其 已释放 柄) 'malformed child drop is consumed without a leaked global allocation'.
    状态 其 增 'error' ''.
    柄 取 夹 其 创建 路们.
    窗 其 发送 子 563 ((窗 其 UP) 其 重释 柄) 0.
    确认 ((状态 其 查 'messages') == 4 且 (状态 其 查 'error') == '' 且 (夹 其 已释放 柄)) 'child forwarding remains usable after a rejected drop'.
    窗 其 成功 ((窗 其 DestroyWindow) 其 调用 [子]) 'DestroyWindow editor'.
    有钩 取 (窗 其 结果 (_GetWindowSubclass 其 调用 [子,子回调址,(拖 其 _子类编号),父存])) 其 数.
    确认 (有钩 == 0) 'destroyed editor retains no queryable file-drop subclass'.
    子 取 窗 其 控制 主 实例 'Scintilla' '' 1073807360 72.
    拖 其 启用编辑器 子 主.
    柄 取 夹 其 创建 路们.
    窗 其 发送 子 563 ((窗 其 UP) 其 重释 柄) 0.
    确认 ((状态 其 查 'messages') == 5 且 (夹 其 已释放 柄)) 'new editor after destruction uses the retained shared callback safely'.
    父存 其 关闭.
    窗 其 成功 ((窗 其 DestroyWindow) 其 调用 [主]) 'DestroyWindow'.
    窗 其 成功 ((窗 其 UnregisterClassW) 其 调用 [类名,实例]) 'UnregisterClassW'.
    回调 其 关闭.
    类 其 关闭.
    类名 其 关闭.
    显 'TOTAL PASS: '+(次数[0] 为 句).
    得 0.
法
