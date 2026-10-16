# ru_notepad 0.1.1 preview. Application behavior is compiled from Ru.
密 取 外言 '如:密'.
窗 取 外言 'win32.ru'.
编 取 外言 'editor.ru'.
件编 取 外言 'file_codec.ru'.
模 取 外言 'document.ru'.
参 取 外言 'ui_arguments.ru'.
A 取 {'window':空,'instance':空,'tabs':空,'status':空,'docs':[],'active':-1,'ready':假,'search':假,'find':空,'replace':空,'next':空,'one':空,'all':空,'case':空,'hide':空,'counter':0,'wrap':假,'busy':假,'shutdownBlocked':假}.

算 当前:
    得 (A 其 查 'docs')[A 其 查 'active'].
法
算 编辑柄:
    得 当前 其 查 'editor'.
法
算 提示 文 为 句:
    得 窗 其 弹窗 (A 其 查 'window') 文 'ru_notepad' 64.
法
算 错误提示 文 为 句:
    得 窗 其 弹窗 (A 其 查 'window') 文 'ru_notepad · could not finish' 16.
法
算 短名 路 为 句:
    得 模 其 短名 路.
法
算 脏 文档:
    得 模 其 有改 文档 (编 其 已变 (文档 其 查 'editor')).
法
算 编码名 编码:
    得 模 其 编码名 编码.
法
算 页标题 文档:
    名 取 文档 其 查 'name'.
    若 脏 文档 则 名 取 '* '+名. 然
    得 名.
法
算 任一已改:
    文们 取 A 其 查 'docs'.
    位 取 0.
    循 文们 其 量 次
        若 脏 文们[位] 则 得 真. 然
        位 取 位+1.
    环
    得 假.
法
算 关机会话:
    若 任一已改 则
        文 取 密 其 UTF16 'ru_notepad has unsaved documents. Save or close them before signing out.'.
        窗 其 结果 ((窗 其 ShutdownBlockReasonCreate) 其 调用 (参 其 窗口二参 A 文)).
        文 其 关闭.
        A 其 增 'shutdownBlocked' 真.
        得 0.
    然
    窗 其 结果 ((窗 其 ShutdownBlockReasonDestroy) 其 调用 [A 其 查 'window']).
    A 其 增 'shutdownBlocked' 假.
    得 1.
法
算 刷新:
    若 非 (A 其 查 'ready') 或 (A 其 查 'active') < 0 则 得 空. 然
    若 (A 其 查 'shutdownBlocked') 且 非 任一已改 则
        窗 其 结果 ((窗 其 ShutdownBlockReasonDestroy) 其 调用 [A 其 查 'window']).
        A 其 增 'shutdownBlocked' 假.
    然
    文档 取 当前.
    名 取 页标题 文档.
    若 名 != (文档 其 查 'label') 则
        存 取 密 其 UTF16 名.
        项 取 (窗 其 TCITEM) 其 新建.
        项 其 写 'mask' 1.
        项 其 写 'text' (存 其 地址).
        窗 其 发指 (A 其 查 'tabs') 4925 (A 其 查 'active') 项.
        项 其 关闭.
        存 其 关闭.
        文档 其 增 'label' 名.
        窗 其 标题 (A 其 查 'window') (名+' · ru_notepad').
    然
    编文 取 编码名 (文档 其 查 'encoding').
    若 文档 其 查 'bom' 则 编文 取 编文+' BOM'. 然
    窗 其 标题 (A 其 查 'status') ('  '+(编 其 状态 (文档 其 查 'editor'))+'    '+编文+'    Preview · 4 MiB file limit').
    得 空.
法
算 移控 柄, 横, 纵, 宽, 高:
    若 宽 < 1 则 宽 取 1. 然
    若 高 < 1 则 高 取 1. 然
    窗 其 结果 ((窗 其 MoveWindow) 其 调用 [柄,横,纵,宽,高,1]).
    得 空.
法
算 布局:
    若 非 (A 其 查 'ready') 则 得 空. 然
    矩 取 (窗 其 RECT) 其 新建.
    窗 其 成功 ((窗 其 GetClientRect) 其 调用 (参 其 窗口二参 A 矩)) 'GetClientRect'.
    宽 取 (矩 其 读 'right') 其 数.
    高 取 (矩 其 读 'bottom') 其 数.
    矩 其 关闭.
    寻高 取 0.
    若 A 其 查 'search' 则 寻高 取 38. 然
    移控 (A 其 查 'tabs') 0 0 宽 30.
    移控 (A 其 查 'status') 0 (高-25) 宽 25.
    若 (A 其 查 'active') >= 0 则 移控 编辑柄 0 32 宽 (高-57-寻高). 然
    栏纵 取 高-25-38.
    输入宽 取 (宽-390)/2.
    若 输入宽 < 80 则 输入宽 取 80. 然
    # Window dimensions must be integer machine values.
    输入宽 取 输入宽-输入宽%1.
    移控 (A 其 查 'find') 8 (栏纵+5) 输入宽 26.
    移控 (A 其 查 'replace') (16+输入宽) (栏纵+5) 输入宽 26.
    起 取 24+输入宽*2.
    移控 (A 其 查 'case') 起 (栏纵+5) 48 26.
    移控 (A 其 查 'next') (起+50) (栏纵+5) 65 26.
    移控 (A 其 查 'one') (起+120) (栏纵+5) 74 26.
    移控 (A 其 查 'all') (起+199) (栏纵+5) 75 26.
    移控 (A 其 查 'hide') (起+279) (栏纵+5) 40 26.
    得 空.
法
算 寻栏 显示 为 事实:
    A 其 增 'search' 显示.
    模式 取 0.
    若 显示 则 模式 取 5. 然
    控们 取 ['find','replace','case','next','one','all','hide'].
    位 取 0.
    循 控们 其 量 次
        窗 其 结果 ((窗 其 ShowWindow) 其 调用 (参 其 控件二参 A 控们[位] 模式)).
        位 取 位+1.
    环
    布局.
    若 显示 则
        窗 其 结果 ((窗 其 SetFocus) 其 调用 [A 其 查 'find']).
        窗 其 发送 (A 其 查 'find') 177 0 (-1).
    另
        窗 其 结果 ((窗 其 SetFocus) 其 调用 [编辑柄]).
    然
    得 空.
法
算 切页 索引:
    文们 取 A 其 查 'docs'.
    若 索引 < 0 或 索引 >= (文们 其 量) 则 得 空. 然
    旧 取 A 其 查 'active'.
    若 旧 >= 0 且 旧 < (文们 其 量) 则
        窗 其 结果 ((窗 其 ShowWindow) 其 调用 (参 其 控件二参 文们[旧] 'editor' 0)).
    然
    A 其 增 'active' 索引.
    窗 其 发送 (A 其 查 'tabs') 4876 索引 0.
    窗 其 结果 ((窗 其 ShowWindow) 其 调用 [编辑柄,5]).
    窗 其 结果 ((窗 其 SetFocus) 其 调用 [编辑柄]).
    当前 其 增 'label' ''.
    布局.
    刷新.
    得 空.
法
算 新页 路 为 句, 文 为 句, 编码, BOM, 戳 为 句:
    文们 取 A 其 查 'docs'.
    若 (文们 其 量) >= 64 则 卒 'This preview supports up to 64 open documents.'. 然
    # Validate expansion limits before creating any native child or tab.
    编 其 验文本 文.
    序 取 (A 其 查 'counter')+1.
    A 其 增 'counter' 序.
    名 取 短名 路.
    若 路 == '' 则 名 取 'Untitled '+(序 为 句). 然
    柄 取 空.
    项 取 空.
    存 取 空.
    试
        柄 取 编 其 创建 (A 其 查 'window') (A 其 查 'instance') (1000+序).
        编 其 设文本 柄 文.
        项 取 (窗 其 TCITEM) 其 新建.
        存 取 密 其 UTF16 名.
        项 其 写 'mask' 1.
        项 其 写 'text' (存 其 地址).
        插位 取 (窗 其 发指 (A 其 查 'tabs') 4926 (文们 其 量) 项) 其 数.
        若 插位 == -1 则 卒 'Windows could not create the document tab.'. 然
    救 原因
        若 存 != 空 则 存 其 关闭. 然
        若 项 != 空 则 项 其 关闭. 然
        若 柄 != 空 则 窗 其 结果 ((窗 其 DestroyWindow) 其 调用 [柄]). 然
        卒 原因.
    终
    存 其 关闭.
    项 其 关闭.
    文档 取 {'editor':柄,'path':路,'name':名,'encoding':编码,'bom':BOM,'stamp':戳,'encodingDirty':假,'label':'','wrap':假}.
    文们 其 增 文档.
    切页 ((文们 其 量)-1).
    得 文档.
法
算 打开 路 为 句, 代码页:
    若 路 == '' 则 得 空. 然
    路 取 件编 其 绝对路径 路.
    文们 取 A 其 查 'docs'.
    位 取 0.
    循 文们 其 量 次
        若 (文们[位] 其 查 'path') == 路 则
            切页 位.
            得 文们[位].
        然
        位 取 位+1.
    环
    成果 取 件编 其 读文件 路 代码页.
    得 新页 路 (成果 其 查 'text') (成果 其 查 'encoding') (成果 其 查 'bom') (成果 其 查 'stamp').
法
算 保存 另存 为 事实:
    文档 取 当前.
    路 取 文档 其 查 'path'.
    戳 取 文档 其 查 'stamp'.
    若 另存 或 路 == '' 则
        路 取 窗 其 文件对话 (A 其 查 'window') 真 路.
        若 路 == '' 则 得 假. 然
        路 取 件编 其 绝对路径 路.
        # Native Save As dialog has already confirmed replacing an existing target.
        若 路 != (文档 其 查 'path') 则 戳 取 ''. 然
    然
    模 其 保存文档 文档 路 (编 其 文本 (文档 其 查 'editor')) 戳 (算 件编 其 写文件).
    编 其 记保存 (文档 其 查 'editor').
    刷新.
    得 真.
法
算 询问关闭 文档:
    得 窗 其 弹窗 (A 其 查 'window') ('Save changes to '+(文档 其 查 'name')+'?') 'ru_notepad · unsaved changes' 35.
法
算 关闭前保存 文档:
    得 保存 假.
法
算 关确认:
    得 模 其 可以关闭 当前 (编 其 已变 编辑柄) (算 询问关闭) (算 关闭前保存).
法
算 关页:
    若 非 关确认 则 得 假. 然
    文们 取 A 其 查 'docs'.
    位 取 A 其 查 'active'.
    柄 取 编辑柄.
    A 其 增 'active' (-1).
    窗 其 成功 ((窗 其 DestroyWindow) 其 调用 [柄]) 'DestroyWindow(editor)'.
    文们 其 删 位.
    窗 其 发送 (A 其 查 'tabs') 4872 位 0.
    若 (文们 其 量) == 0 则
        新页 '' '' 65001 假 ''.
    另
        若 位 >= (文们 其 量) 则 位 取 (文们 其 量)-1. 然
        切页 位.
    然
    得 真.
法
算 关程序:
    文们 取 A 其 查 'docs'.
    位 取 0.
    循 文们 其 量 次
        切页 位.
        若 非 关确认 则 得 假. 然
        位 取 位+1.
    环
    A 其 增 'ready' 假.
    窗 其 成功 ((窗 其 DestroyWindow) 其 调用 [A 其 查 'window']) 'DestroyWindow(main)'.
    得 真.
法
算 命令 号:
    若 号 == 101 则 新页 '' '' 65001 假 ''. 得 空. 然
    若 号 == 102 或 号 == 108 或 号 == 109 则
        代码页 取 0.
        若 号 == 108 则 代码页 取 1252. 然
        若 号 == 109 则 代码页 取 936. 然
        打开 (窗 其 文件对话 (A 其 查 'window') 假 '') 代码页.
        得 空.
    然
    若 号 == 103 则 保存 假. 得 空. 然
    若 号 == 104 则 保存 真. 得 空. 然
    若 号 == 105 则 关页. 得 空. 然
    若 号 == 106 则 关程序. 得 空. 然
    若 号 == 201 则 窗 其 发送 编辑柄 2176 0 0. 然
    若 号 == 202 则 窗 其 发送 编辑柄 2011 0 0. 然
    若 号 == 203 则 窗 其 发送 编辑柄 2177 0 0. 然
    若 号 == 204 则 窗 其 发送 编辑柄 2178 0 0. 然
    若 号 == 205 则 窗 其 发送 编辑柄 2179 0 0. 然
    若 号 == 206 则 窗 其 发送 编辑柄 2013 0 0. 然
    若 号 == 301 或 号 == 302 则 寻栏 真. 得 空. 然
    若 号 == 307 则 寻栏 假. 得 空. 然
    若 号 == 303 或 号 == 304 或 号 == 305 则
        词 取 窗 其 取文 (A 其 查 'find').
        新文 取 窗 其 取文 (A 其 查 'replace').
        区分 取 非 ((窗 其 发送 (A 其 查 'case') 240 0 0) 其 为空).
        若 词 == '' 则 寻栏 真. 得 空. 然
        若 号 == 303 则
            若 (编 其 下个 编辑柄 词 区分) == -1 则 提示 'No match found.'. 然
        然
        若 号 == 304 则
            若 (编 其 换当前 编辑柄 词 新文 区分) == -1 则 提示 'No further match found.'. 然
        然
        若 号 == 305 则
            次数 取 编 其 全换 编辑柄 词 新文 区分.
            提示 ((次数 为 句)+' replacements. Undo restores the entire operation.').
        然
    然
    若 号 >= 401 且 号 <= 405 则
        编码 取 65001.
        BOM 取 假.
        若 号 == 402 则 BOM 取 真. 然
        若 号 == 403 则 编码 取 1200. BOM 取 真. 然
        若 号 == 404 则 编码 取 1201. BOM 取 真. 然
        若 号 == 405 则 编码 取 1252. 然
        模 其 改编码 当前 编码 BOM.
    然
    若 号 == 406 则
        模 其 改编码 当前 936 假.
    然
    若 号 == 501 则
        当前 其 增 'wrap' (非 (当前 其 查 'wrap')).
        选 取 0.
        若 当前 其 查 'wrap' 则 选 取 1. 然
        窗 其 发送 编辑柄 2268 选 0.
    然
    若 号 == 502 则 窗 其 发送 编辑柄 2333 0 0. 然
    若 号 == 503 则 窗 其 发送 编辑柄 2334 0 0. 然
    若 号 == 601 则 提示 'ru_notepad 0.1.1 preview\n\nWindows x64 · application logic compiled from Ru\nScintilla native editor component\n\nTabs, safe text saves, undo/redo, literal find/replace.\n4 MiB per file, 64 tabs. Not full Notepad++ parity yet.\nNo Python runtime. No telemetry. No network features.'. 然
    刷新.
    得 空.
法
算 菜单:
    主 取 窗 其 成功 ((窗 其 CreateMenu) 其 调用 []) 'CreateMenu'.
    组们 取 [
        ['&File',[[101,'&New\tCtrl+N'],[102,'&Open...\tCtrl+O'],[108,'Open as Windows-1252...'],[109,'Open as GBK (CP936)...'],[103,'&Save\tCtrl+S'],[104,'Save &As...\tCtrl+Shift+S'],[105,'&Close tab\tCtrl+W'],[106,'E&xit']]],
        ['&Edit',[[201,'&Undo\tCtrl+Z'],[202,'&Redo\tCtrl+Y'],[203,'Cu&t\tCtrl+X'],[204,'&Copy\tCtrl+C'],[205,'&Paste\tCtrl+V'],[206,'Select &All\tCtrl+A']]],
        ['&Search',[[301,'&Find...\tCtrl+F'],[302,'&Replace...\tCtrl+H'],[303,'Find &Next\tF3']]],
        ['E&ncoding',[[401,'Save as UTF-8'],[402,'Save as UTF-8 with BOM'],[403,'Save as UTF-16 LE'],[404,'Save as UTF-16 BE'],[405,'Save as Windows-1252'],[406,'Save as GBK (CP936)']]],
        ['&View',[[501,'Toggle word &wrap'],[502,'Zoom &in'],[503,'Zoom &out']]],
        ['&Help',[[601,'&About ru_notepad']]]
    ].
    组位 取 0.
    循 组们 其 量 次
        组 取 组们[组位].
        子 取 窗 其 成功 ((窗 其 CreatePopupMenu) 其 调用 []) 'CreatePopupMenu'.
        项位 取 0.
        项们 取 组[1].
        循 项们 其 量 次
            项 取 项们[项位].
            窗 其 菜单项 子 0 项[0] 项[1].
            项位 取 项位+1.
        环
        窗 其 菜单项 主 16 ((窗 其 UP) 其 重释 子) 组[0].
        组位 取 组位+1.
    环
    窗 其 成功 ((窗 其 SetMenu) 其 调用 (参 其 菜单参数 A 主)) 'SetMenu'.
    得 空.
法
算 消息处理 柄, 号值, 宽参, 长参:
    号 取 号值 其 数.
    若 号 == 129 则 A 其 增 'window' 柄. 然
    若 号 == 2 则
        窗 其 结果 ((窗 其 PostQuitMessage) 其 调用 [0]).
        得 0.
    然
    若 A 其 查 'ready' 则
        试
            若 号 == 17 则 得 关机会话. 然
            若 号 == 5 则 布局. 得 0. 然
            若 号 == 16 则 关程序. 得 0. 然
            若 号 == 273 且 (宽参 其 位段 16 16) == 0 则
                命令 (宽参 其 位段 0 16).
                得 0.
            然
            若 号 == 78 则
                头 取 (窗 其 NMHDR) 其 新建.
                窗 其 结果 ((窗 其 RtlMoveMemory) 其 调用 [头,((窗 其 PTR) 其 重释 长参),(窗 其 NMHDR) 其 大小]).
                来源 取 头 其 读 'hwndFrom'.
                码 取 (头 其 读 'code') 其 数.
                头 其 关闭.
                若 (来源 其 句) == ((A 其 查 'tabs') 其 句) 且 码 == 4294966745 则
                    切页 ((窗 其 发送 (A 其 查 'tabs') 4875 0 0) 其 数).
                然
                若 码 == 2002 或 码 == 2003 或 码 == 2007 则 刷新. 然
                得 0.
            然
        救 原因
            错误提示 原因.
            得 0.
        终
    然
    得 窗 其 结果 ((窗 其 DefWindowProcW) 其 调用 [柄,号值,宽参,长参]).
法
算 快捷 消息:
    号 取 (消息 其 读 'message') 其 数.
    若 号 != 256 则 得 假. 然
    键 取 (消息 其 读 'wParam') 其 数.
    Ctrl 取 ((窗 其 结果 ((窗 其 GetKeyState) 其 调用 [17])) 其 位段 15 1) == 1.
    Shift 取 ((窗 其 结果 ((窗 其 GetKeyState) 其 调用 [16])) 其 位段 15 1) == 1.
    号令 取 0.
    若 Ctrl 则
        若 键 == 78 则 号令 取 101. 然
        若 键 == 79 则 号令 取 102. 然
        若 键 == 83 则
            号令 取 103.
            若 Shift 则 号令 取 104. 然
        然
        若 键 == 87 则 号令 取 105. 然
        若 键 == 70 则 号令 取 301. 然
        若 键 == 72 则 号令 取 302. 然
        若 键 == 9 则
            文们 取 A 其 查 'docs'.
            切页 (((A 其 查 'active')+1)%(文们 其 量)).
            得 真.
        然
    然
    若 键 == 114 则 号令 取 303. 然
    若 键 == 27 且 (A 其 查 'search') 则 号令 取 307. 然
    若 号令 == 0 则 得 假. 然
    试
        命令 号令.
    救 原因
        错误提示 原因.
    终
    得 真.
法

算 初始化 参数 为 句 阵, 显示 为 事实:
    # Every dependency is loaded before WNDPROC can run.
    库路径 取 (窗 其 目录)+'Scintilla.dll'.
    路径存 取 密 其 UTF16 库路径.
    预载成果 取 (窗 其 LoadLibraryExW) 其 调用 [路径存,空,2304].
    路径存 其 关闭.
    预载 取 预载成果 其 值.
    若 预载 其 为空 则
        卒 ('Cannot load Scintilla.dll (Windows error '+((预载成果 其 错误码) 为 句)+'). Extract the complete Windows x64 package and keep its DLL beside ru_notepad.exe.').
    然
    原生编辑库 取 密 其 动态库 库路径.
    显 '[startup] Scintilla loaded'.
    窗 其 结果 ((窗 其 FreeLibrary) 其 调用 [预载]).
    实例 取 窗 其 成功 ((窗 其 GetModuleHandleW) 其 调用 [空]) 'GetModuleHandleW'.
    A 其 增 'instance' 实例.
    控初始化 取 (窗 其 INITCONTROLS) 其 新建.
    控初始化 其 写 'size' ((窗 其 INITCONTROLS) 其 大小).
    控初始化 其 写 'classes' 8.
    窗 其 成功 ((窗 其 InitCommonControlsEx) 其 调用 [控初始化]) 'InitCommonControlsEx'.
    控初始化 其 关闭.
    类名 取 密 其 UTF16 'RuNotepad.Main.0.1'.
    标题 取 密 其 UTF16 'ru_notepad'.
    回调 取 密 其 回调 (窗 其 WNDPROC) (算 消息处理) 0.
    回调 其 失败时 (窗 其 PostQuitMessage) ([1]).
    类 取 (窗 其 WNDCLASS) 其 新建.
    类 其 写 'size' ((窗 其 WNDCLASS) 其 大小).
    类 其 写 'proc' (回调 其 地址).
    类 其 写 'instance' 实例.
    类 其 写 'icon' (窗 其 结果 ((窗 其 LoadImageW) 其 调用 [实例,((窗 其 PTR) 其 值 1),1,32,32,32768])).
    类 其 写 'smallIcon' (窗 其 结果 ((窗 其 LoadImageW) 其 调用 [实例,((窗 其 PTR) 其 值 1),1,16,16,32768])).
    类 其 写 'name' (类名 其 地址).
    类 其 写 'cursor' (窗 其 结果 ((窗 其 LoadCursorW) 其 调用 [空,((窗 其 PTR) 其 值 32512)])).
    类 其 写 'background' (窗 其 结果 ((窗 其 GetSysColorBrush) 其 调用 [15])).
    窗 其 成功 ((窗 其 RegisterClassExW) 其 调用 [类]) 'RegisterClassExW'.
    类 其 关闭.
    显 '[startup] window class registered'.
    主窗 取 窗 其 成功 ((窗 其 CreateWindowExW) 其 调用 [0,类名,标题,13565952,-2147483648,-2147483648,1120,760,空,空,实例,空]) 'CreateWindowExW(main)'.
    标题 其 关闭.
    A 其 增 'window' 主窗.
    显 '[startup] main window created'.
    A 其 增 'tabs' (窗 其 控制 主窗 实例 'SysTabControl32' '' 1342242816 10).
    A 其 增 'status' (窗 其 控制 主窗 实例 'STATIC' '' 1342177280 11).
    A 其 增 'find' (窗 其 控制 主窗 实例 'EDIT' '' 1082196096 310).
    A 其 增 'replace' (窗 其 控制 主窗 实例 'EDIT' '' 1082196096 311).
    A 其 增 'case' (窗 其 控制 主窗 实例 'BUTTON' 'Aa' 1073807363 306).
    窗 其 发送 (A 其 查 'case') 241 1 0.
    A 其 增 'next' (窗 其 控制 主窗 实例 'BUTTON' 'Next' 1073807360 303).
    A 其 增 'one' (窗 其 控制 主窗 实例 'BUTTON' 'Replace' 1073807360 304).
    A 其 增 'all' (窗 其 控制 主窗 实例 'BUTTON' 'All' 1073807360 305).
    A 其 增 'hide' (窗 其 控制 主窗 实例 'BUTTON' 'X' 1073807360 307).
    显 '[startup] controls created'.
    菜单.
    显 '[startup] menu installed'.
    A 其 增 'ready' 真.
    新页 '' '' 65001 假 ''.
    显 '[startup] initial document ready'.
    # Command-line paths are opened without modifying them.
    位 取 0.
    循 参数 其 量 次
        试
            打开 参数[位] 0.
        救 原因
            错误提示 原因.
        终
        位 取 位+1.
    环
    若 显示 则
        窗 其 结果 ((窗 其 ShowWindow) 其 调用 [主窗,5]).
        窗 其 结果 ((窗 其 UpdateWindow) 其 调用 [主窗]).
        显 '[startup] main window shown'.
    然
    A 其 增 'className' 类名.
    A 其 增 'callback' 回调.
    A 其 增 'scintillaLibrary' 原生编辑库.
    得 主窗.
法

算 元初 参数 为 句 阵:
    显 '[startup] Ru application modules loaded'.
    试
        初始化 参数 真.
    救 原因
        显 '[startup] initialization failed'.
        窗 其 弹窗 空 原因 'ru_notepad · startup failed' 16.
        得 1.
    终
    消息 取 (窗 其 MSG) 其 新建.
    退出码 取 0.
    试
        循
            成果 取 (窗 其 GetMessageW) 其 调用 [消息,空,0,0].
            码 取 (窗 其 结果 成果) 其 数.
            若 码 == -1 则 卒 'GetMessageW failed.'. 然
            若 码 == 0 则
                退出码 取 (消息 其 读 'wParam') 其 数.
                若 退出码 != 0 则 卒 'The native callback failure handler stopped the event loop.'. 然
                破.
            然
            若 非 (快捷 消息) 则
                窗 其 结果 ((窗 其 TranslateMessage) 其 调用 [消息]).
                窗 其 结果 ((窗 其 DispatchMessageW) 其 调用 [消息]).
            然
        环
        消息 其 关闭.
        窗 其 成功 ((窗 其 UnregisterClassW) 其 调用 (参 其 注销类参数 A)) 'UnregisterClassW'.
        (A 其 查 'className') 其 关闭.
        (A 其 查 'callback') 其 关闭.
    救 原因
        # A native callback failure is contained, but application state cannot
        # be assumed resumable. Never silently overwrite files during recovery.
        A 其 增 'ready' 假.
        窗 其 弹窗 空 ('A fatal internal error stopped ru_notepad. Unsaved changes may be lost; this preview has no crash recovery. No emergency save will be attempted. If this happened during Save, check the target and any temporary/recovery files.\n\n'+原因) 'ru_notepad · fatal error' 16.
        得 1.
    终
    得 退出码.
法
