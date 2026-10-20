# Real hidden-window i18n acceptance. Never dispatch850-857 or persist a choice.
# One existing disposable directory is required. Only an exclusively created
# synthetic child directory and its two files are written or removed.
应用 取 外言 '../src/main.ru'.
窗 取 外言 '../src/win32.ru'.
编 取 外言 '../src/editor.ru'.
件编 取 外言 '../src/file_codec.ru'.
本地 取 外言 '../src/i18n.ru'.
资源 取 外言 '../src/i18n_catalog.ru'.
状态文 取 外言 '../src/status.ru'.
密 取 外言 '如:密'.
_GetMenuStringW 取 (窗 其 用户) 其 绑定 'GetMenuStringW' (密 其 签名 (窗 其 I) ([(窗 其 PTR),(窗 其 U),(窗 其 PTR),(窗 其 I),(窗 其 U)]) 'win64').
_GetSubMenu 取 (窗 其 用户) 其 绑定 'GetSubMenu' (密 其 签名 (窗 其 PTR) ([(窗 其 PTR),(窗 其 I)]) 'win64').
_GetMenuItemCount 取 (窗 其 用户) 其 绑定 'GetMenuItemCount' (密 其 签名 (窗 其 I) ([(窗 其 PTR)]) 'win64').
_GetMenuState 取 (窗 其 用户) 其 绑定 'GetMenuState' (密 其 签名 (窗 其 U) ([(窗 其 PTR),(窗 其 U),(窗 其 U)]) 'win64').
_IsMenu 取 (窗 其 用户) 其 绑定 'IsMenu' (密 其 签名 (窗 其 I) ([(窗 其 PTR)]) 'win64').
_IsWindowVisible 取 (窗 其 用户) 其 绑定 'IsWindowVisible' (密 其 签名 (窗 其 I) ([(窗 其 PTR)]) 'win64').
_GetWindowRect 取 (窗 其 用户) 其 绑定 'GetWindowRect' (密 其 签名 (窗 其 I) ([(窗 其 PTR),(窗 其 PTR)]) 'win64').
_ClientToScreen 取 (窗 其 用户) 其 绑定 'ClientToScreen' (密 其 签名 (窗 其 I) ([(窗 其 PTR),(窗 其 PTR)]) 'win64').
_GetGuiResources 取 (窗 其 用户) 其 绑定 'GetGuiResources' (密 其 签名 (窗 其 U) ([(窗 其 PTR),(窗 其 U)]) 'win64').
_GetCurrentProcess 取 (窗 其 内核) 其 绑定 'GetCurrentProcess' (密 其 签名 (窗 其 PTR) ([]) 'win64').
_GetCurrentProcessId 取 (窗 其 内核) 其 绑定 'GetCurrentProcessId' (密 其 签名 (窗 其 U) ([]) 'win64').
_CreateDirectoryW 取 (窗 其 内核) 其 绑定 'CreateDirectoryW' (密 其 签名 (窗 其 I) ([(窗 其 PTR),(窗 其 PTR)]) 'win64').
_RemoveDirectoryW 取 (窗 其 内核) 其 绑定 'RemoveDirectoryW' (密 其 签名 (窗 其 I) ([(窗 其 PTR)]) 'win64').
_DeleteFileW 取 (窗 其 内核) 其 绑定 'DeleteFileW' (密 其 签名 (窗 其 I) ([(窗 其 PTR)]) 'win64').
_GetFileAttributesW 取 (窗 其 内核) 其 绑定 'GetFileAttributesW' (密 其 签名 (窗 其 U) ([(窗 其 PTR)]) 'win64').
_Sleep 取 (窗 其 内核) 其 绑定 'Sleep' (密 其 签名 (窗 其 V) ([(窗 其 U)]) 'win64').
# Test-owned only. CI's 1024px desktop defaults maxTrackX to 1044; allowing
# this hidden fixture to exceed the monitor preserves the exact 1600px test.
# The production WM_GETMINMAXINFO handler is always called first and untouched.
_SetWindowSubclass 取 (窗 其 控件) 其 绑定 'SetWindowSubclass' (密 其 签名 (窗 其 I) ([(窗 其 PTR),(窗 其 PTR),(窗 其 UP),(窗 其 UP)]) 'win64').
_RemoveWindowSubclass 取 (窗 其 控件) 其 绑定 'RemoveWindowSubclass' (密 其 签名 (窗 其 I) ([(窗 其 PTR),(窗 其 PTR),(窗 其 UP)]) 'win64').
_DefSubclassProc 取 (窗 其 控件) 其 绑定 'DefSubclassProc' (密 其 签名 (窗 其 IP) ([(窗 其 PTR),(窗 其 U),(窗 其 UP),(窗 其 IP)]) 'win64').
_布局型 取 密 其 签名 (窗 其 IP) ([(窗 其 PTR),(窗 其 U),(窗 其 UP),(窗 其 IP),(窗 其 UP),(窗 其 UP)]) 'win64'.
_布局钩 取 {'window':空,'callback':空,'calls':0,'maxX':0,'maxY':0}.
算 布局上限 宽 为 数 高 为 数:
    若 宽 < 4096 则 宽 取 4096. 然
    若 高 < 4096 则 高 取 4096. 然
    得 [宽,高].
法
算 布局子过程 柄 消息 宽 长 号 引:
    果 取 窗 其 结果 (_DefSubclassProc 其 调用 [柄,消息,宽,长]).
    若 消息 其 数 == 36 则
        若 (柄 其 句) != ((_布局钩 其 查 'window') 其 句) 则 卒 'Layout fixture owner mismatch.'. 然
        若 非 ((窗 其 结果 (_IsWindowVisible 其 调用 [柄])) 其 为空) 则 卒 'Layout fixture must stay hidden.'. 然
        矩 取 (窗 其 MINMAXINFO) 其 新建.
        试
            指 取 (窗 其 PTR) 其 重释 长.
            窗 其 结果 ((窗 其 RtlMoveMemory) 其 调用 [矩,指,((窗 其 MINMAXINFO) 其 大小)]).
            若 (矩 其 读 'minTrackX') 其 数 != 640 或 (矩 其 读 'minTrackY') 其 数 != 400 则 卒 'Production minimum tracking policy changed.'. 然
            限 取 布局上限 ((矩 其 读 'maxTrackX') 其 数) ((矩 其 读 'maxTrackY') 其 数).
            矩 其 写 'maxTrackX' 限[0]. 矩 其 写 'maxTrackY' 限[1].
            窗 其 结果 ((窗 其 RtlMoveMemory) 其 调用 [指,矩,((窗 其 MINMAXINFO) 其 大小)]).
            _布局钩 其 增 'calls' ((_布局钩 其 查 'calls')+1).
            _布局钩 其 增 'maxX' 限[0]. _布局钩 其 增 'maxY' 限[1].
        救 原因 矩 其 关闭. 卒 原因. 终
        矩 其 关闭.
    然
    得 果.
法
作 装布局钩 主:
    若 非 ((窗 其 结果 (_IsWindowVisible 其 调用 [主])) 其 为空) 则 卒 'Layout fixture must start hidden.'. 然
    回调 取 密 其 回调 _布局型 (算 布局子过程) 0.
    回调 其 失败时 (窗 其 PostQuitMessage) ([1]).
    _布局钩 其 增 'window' 主. _布局钩 其 增 'callback' 回调.
    试
        窗 其 成功 (_SetWindowSubclass 其 调用 [主,(回调 其 地址),9931,0]) 'Install test-owned layout guard'.
    救 原因
        _布局钩 其 增 'window' 空. _布局钩 其 增 'callback' 空.
        回调 其 关闭.
        卒 原因.
    终
为
算 卸布局钩:
    主 取 _布局钩 其 查 'window'.
    若 主 == 空 则 得 空. 然
    回调 取 _布局钩 其 查 'callback'.
    窗 其 成功 (_RemoveWindowSubclass 其 调用 [主,(回调 其 地址),9931]) 'Remove test-owned layout guard'.
    _布局钩 其 增 'window' 空. _布局钩 其 增 'callback' 空.
    回调 其 关闭.
    得 空.
法
次数 取 [0].
关闭询问 取 [0].
语言们 取 ['en','zh-CN','ja','ko','es','ru','it'].
源 取 'English 中😀 日本語 한국어 Español Русский Italiano\r\nsecond\tline\r\n'.
草稿 取 'draft 中😀\r\nline'.
文件名 取 '保留 {0} файл 日本語 한국어 español 😀.txt'.
菜单名 取 ['menu.file','menu.edit','menu.search','menu.encoding','menu.language','menu.view','menu.settings','menu.ui_language','menu.help'].
菜单数 取 [10,6,4,6,5,7,4,8,1].
命令号 取 [101,102,108,109,103,104,105,111,112,106,201,202,203,204,205,206,301,302,303,308,401,402,403,404,405,406,701,702,703,704,705,501,502,503,504,505,506,507,801,802,803,804,850,851,852,853,854,855,856,857,601].
命令键 取 ['command.new','command.open','command.open_windows1252','command.open_gbk','command.save','command.save_as','command.close_tab','command.previous_tab','command.next_tab','command.exit','command.undo','command.redo','command.cut','command.copy','command.paste','command.select_all','command.find','command.replace','command.find_next','command.find_previous','command.save_utf8','command.save_utf8_bom','command.save_utf16le','command.save_utf16be','command.save_windows1252','command.save_gbk','command.language_plain','command.language_cpp','command.language_json','command.language_ru','command.language_markdown','command.toggle_wrap','command.zoom_in','command.zoom_out','command.zoom_reset','command.fold_all','command.unfold_all','command.toggle_markdown_folds','command.register_association','command.default_apps','command.unregister_association','command.registration_status','language.system','language.en','language.zh_cn','language.ja','language.ko','language.es','language.ru','language.it','command.about'].
按钮名 取 ['cancel','case','whole','searchWrap','previous','next','one','all','hide'].
按钮键 取 ['search.cancel','search.case','search.whole','search.wrap','search.previous','search.next','search.replace','search.all','search.close'].
# Fixed synthetic progress only. These numeric enums identify a failed native
# operation before its assertion without publishing labels, paths, or exceptions.
作 记阶段 阶段 为 数 语言 为 数 宽 为 数:
    显 'I18N_STAGE stage='+(阶段 为 句)+' language='+(语言 为 句)+' width='+(宽 为 句)+' next='+((次数[0]+1) 为 句).
为
作 确认 条件 为 事实 名 为 句:
    若 非 条件 则 卒 'FAIL: '+名. 然
    次数[0] 取 次数[0]+1.
    显 'PASS: '+名.
为
算 词 代码 为 句 键 为 句:
    值 取 (资源 其 目录) 其 查 (代码+':'+键).
    若 值 == 空 或 值 == '' 则 卒 'Missing independent catalog expectation: '+代码+':'+键. 然
    得 值.
法
算 计时:
    得 (窗 其 结果 ((窗 其 GetTickCount64) 其 调用 [])) 其 数.
法
作 泵:
    消 取 (窗 其 MSG) 其 新建.
    起 取 计时.
    试
        循
            若 非 ((应用 其 A) 其 查 'busy') 则 破. 然
            若 计时-起 > 30000 则 卒 'i18n synthetic file operation exceeded30s.'. 然
            若 非 ((窗 其 结果 ((窗 其 PeekMessageW) 其 调用 [消,空,0,0,1])) 其 为空) 则
                若 (消 其 读 'message') 其 数 == 18 则 卒 'Unexpected WM_QUIT during i18n file operation.'. 然
                窗 其 结果 ((窗 其 TranslateMessage) 其 调用 [消]).
                窗 其 结果 ((窗 其 DispatchMessageW) 其 调用 [消]).
            另 _Sleep 其 调用 [1]. 然
        环
    救 原因 消 其 关闭. 卒 原因. 终
    消 其 关闭.
为
算 菜单字 柄 号 为 数 标志 为 数:
    存 取 密 其 缓冲 8192.
    试
        长 取 (窗 其 结果 (_GetMenuStringW 其 调用 [柄,号,存,4096,标志])) 其 数.
        若 长 <= 0 或 长 >= 4095 则 卒 'Native menu label is missing or truncated.'. 然
        文 取 窗 其 解宽 存 长.
    救 原因 存 其 关闭. 卒 原因. 终
    存 其 关闭.
    得 文.
法
算 页签字 位 为 数:
    存 取 密 其 缓冲 8192.
    项 取 (窗 其 TCITEM) 其 新建.
    试
        项 其 写 'mask' 1.
        项 其 写 'text' (存 其 地址).
        项 其 写 'textMax' 4096.
        若 (窗 其 发指 ((应用 其 A) 其 查 'tabs') 4924 位 项) 其 为空 则 卒 'TCM_GETITEMW failed.'. 然
        长 取 (窗 其 结果 ((窗 其 lstrlenW) 其 调用 [存])) 其 数.
        文 取 窗 其 解宽 存 长.
    救 原因 项 其 关闭. 存 其 关闭. 卒 原因. 终
    项 其 关闭. 存 其 关闭.
    得 文.
法
算 提示字 柄:
    存 取 密 其 缓冲 8192.
    试
        若 (窗 其 发送 柄 5378 ((窗 其 UP) 其 重释 (存 其 地址)) 4096) 其 为空 则 卒 'EM_GETCUEBANNER failed.'. 然
        长 取 (窗 其 结果 ((窗 其 lstrlenW) 其 调用 [存])) 其 数.
        文 取 窗 其 解宽 存 长.
    救 原因 存 其 关闭. 卒 原因. 终
    存 其 关闭.
    得 文.
法
算 外矩 柄:
    矩 取 (窗 其 RECT) 其 新建.
    试
        窗 其 成功 (_GetWindowRect 其 调用 [柄,矩]) 'GetWindowRect(i18n fixture)'.
        果 取 [((矩 其 读 'left') 其 数),((矩 其 读 'top') 其 数),((矩 其 读 'right') 其 数),((矩 其 读 'bottom') 其 数)].
    救 原因 矩 其 关闭. 卒 原因. 终
    矩 其 关闭.
    得 果.
法
算 客矩 主:
    矩 取 (窗 其 RECT) 其 新建.
    点 取 (窗 其 POINT) 其 新建.
    试
        窗 其 成功 ((窗 其 GetClientRect) 其 调用 [主,矩]) 'GetClientRect(i18n fixture)'.
        点 其 写 'x' 0. 点 其 写 'y' 0.
        窗 其 成功 (_ClientToScreen 其 调用 [主,点]) 'ClientToScreen(i18n fixture)'.
        横 取 (点 其 读 'x') 其 数. 纵 取 (点 其 读 'y') 其 数.
        果 取 [横,纵,横+((矩 其 读 'right') 其 数),纵+((矩 其 读 'bottom') 其 数)].
    救 原因 点 其 关闭. 矩 其 关闭. 卒 原因. 终
    点 其 关闭. 矩 其 关闭.
    得 果.
法
算 不交 一 为 阵 二 为 阵:
    得 一[2] <= 二[0] 或 二[2] <= 一[0] 或 一[3] <= 二[1] 或 二[3] <= 一[1].
法
算 内含 一 为 阵 二 为 阵:
    得 一[0] >= 二[0] 且 一[1] >= 二[1] 且 一[2] <= 二[2] 且 一[3] <= 二[3] 且 一[2] > 一[0] 且 一[3] > 一[1].
法
作 验布局 主 宽 为 数 代码 为 句:
    态 取 应用 其 A.
    # Account for real nonclient borders and menu wrapping, keeping client width exact.
    循 2 次
        外 取 外矩 主. 内 取 客矩 主.
        窗 其 成功 ((窗 其 MoveWindow) 其 调用 [主,40,40,宽+外[2]-外[0]-内[2]+内[0],720+外[3]-外[1]-内[3]+内[1],1]) 'Resize hidden i18n fixture'.
    环
    应用 其 布局.
    内 取 客矩 主.
    前 取 代码+' '+(宽 为 句)+'px '.
    确认 (内[2]-内[0] == 宽 且 内[3]-内[1] >= 400 且 (_布局钩 其 查 'calls') > 0 且 (_布局钩 其 查 'maxX') >= 4096 且 (_布局钩 其 查 'maxY') >= 4096) (前+'actual client width and usable height').
    控们 取 ['find','replace','case','whole','searchWrap','previous','next','one','all','hide'].
    矩们 取 [].
    位 取 0.
    循 控们 其 量 次
        名 取 控们[位].
        矩 取 外矩 (态 其 查 名).
        矩们 其 增 矩.
        最小宽 取 80.
        若 位 >= 2 则 最小宽 取 应用 其 按钮宽 名. 然
        确认 ((内含 矩 内) 且 矩[2]-矩[0] >= 最小宽) (前+名+' remains within client with measured width').
        位 取 位+1.
    环
    相离 取 真.
    位 取 0.
    循 矩们 其 量 次
        另位 取 位+1.
        循
            若 另位 >= (矩们 其 量) 则 破. 然
            若 非 (不交 矩们[位] 矩们[另位]) 则 相离 取 假. 然
            另位 取 另位+1.
        环
        位 取 位+1.
    环
    确认 相离 (前+'all search control rectangles are pairwise disjoint').
    位 取 0.
    循 按钮名 其 量 次
        名 取 按钮名[位].
        矩 取 外矩 (态 其 查 名).
        确认 (矩[2]-矩[0] == (应用 其 按钮宽 名)) (前+名+' actual native width equals measured layout width').
        位 取 位+1.
    环
    编辑矩 取 外矩 (应用 其 编辑柄).
    状态矩 取 外矩 (态 其 查 'status').
    页矩 取 外矩 (态 其 查 'tabs').
    分开 取 (内含 编辑矩 内) 且 (内含 状态矩 内) 且 (内含 页矩 内) 且 页矩[3] <= 编辑矩[1].
    位 取 0.
    循 矩们 其 量 次
        矩 取 矩们[位].
        若 矩[1] < 编辑矩[3] 或 矩[3] > 状态矩[1] 则 分开 取 假. 然
        位 取 位+1.
    环
    确认 分开 (前+'search rows never cover editor tabs or status').
    # Exercise the existing busy layout without starting I/O or changing text.
    态 其 增 'busy' 真.
    应用 其 布局.
    状态矩 取 外矩 (态 其 查 'status').
    取消矩 取 外矩 (态 其 查 'cancel').
    态 其 增 'busy' 假.
    应用 其 布局.
    确认 ((内含 状态矩 内) 且 (内含 取消矩 内) 且 (不交 状态矩 取消矩)) (前+'localized cancel button does not cover busy status').
为
算 快照 文档:
    柄 取 文档 其 查 'editor'.
    得 {'text':(编 其 文本 柄),'anchor':((窗 其 发送 柄 2009 0 0) 其 数),'caret':((窗 其 发送 柄 2008 0 0) 其 数),'undo':((窗 其 发送 柄 2174 0 0) 其 数),'redo':((窗 其 发送 柄 2016 0 0) 其 数),'encoding':(文档 其 查 'encoding'),'bom':(文档 其 查 'bom'),'encodingDirty':(文档 其 查 'encodingDirty'),'dirty':(应用 其 脏 文档),'path':(文档 其 查 'path'),'language':(文档 其 查 'language'),'lexer':((窗 其 发送 柄 4002 0 0) 其 数),'revision':(文档 其 查 'revision'),'wrap':((窗 其 发送 柄 2269 0 0) 其 数),'pointer':((窗 其 发送 柄 2357 0 0) 其 句),'readonly':((窗 其 发送 柄 2140 0 0) 其 数),'eol':((窗 其 发送 柄 2030 0 0) 其 数)}.
法
作 验文档 文档 旧 代码 为 句:
    现照 取 快照 文档.
    确认 (现照['text'] == 旧['text']) (代码+' exact multilingual document body unchanged').
    确认 (现照['anchor'] == 旧['anchor'] 且 现照['caret'] == 旧['caret']) (代码+' forward or reverse UTF8 selection unchanged').
    确认 (现照['undo'] == 旧['undo'] 且 现照['redo'] == 旧['redo']) (代码+' undo and redo availability unchanged').
    确认 (现照['encoding'] == 旧['encoding'] 且 现照['bom'] == 旧['bom'] 且 现照['encodingDirty'] == 旧['encodingDirty']) (代码+' file encoding BOM and encoding-dirty flag unchanged').
    确认 (现照['dirty'] == 旧['dirty']) (代码+' clean or dirty savepoint unchanged').
    确认 (现照['path'] == 旧['path']) (代码+' exact document path unchanged').
    确认 (现照['language'] == 旧['language'] 且 现照['lexer'] == 旧['lexer']) (代码+' syntax identity and actual lexer unchanged').
    确认 (现照['revision'] == 旧['revision']) (代码+' text revision unchanged').
    确认 (现照['wrap'] == 旧['wrap'] 且 现照['pointer'] == 旧['pointer'] 且 现照['readonly'] == 旧['readonly'] 且 现照['eol'] == 旧['eol']) (代码+' native document wrap readonly and insertion EOL unchanged').
为
作 验全部文档 旧们 为 阵 活 为 数 代码 为 句:
    态 取 应用 其 A.
    文们 取 态 其 查 'docs'.
    确认 ((文们 其 量) == 3) (代码+' document count unchanged').
    确认 ((态 其 查 'active') == 活) (代码+' active document index unchanged').
    确认 ((窗 其 发送 (态 其 查 'tabs') 4875 0 0) 其 数 == 活) (代码+' native selected tab unchanged').
    位 取 0.
    循 3 次
        验文档 文们[位] 旧们[位] (代码+' tab'+(位 为 句)).
        位 取 位+1.
    环
为
作 切换 主 代码 为 句:
    旧 取 窗 其 结果 ((窗 其 GetMenu) 其 调用 [主]).
    应用 其 切界面 代码 假.
    确认 ((窗 其 结果 (_IsMenu 其 调用 [旧])) 其 为空) (代码+' replaced native menu is destroyed immediately').
为
作 验菜单 主 代码 为 句:
    菜 取 窗 其 成功 ((窗 其 GetMenu) 其 调用 [主]) 'GetMenu(i18n fixture)'.
    确认 ((窗 其 结果 (_GetMenuItemCount 其 调用 [菜])) 其 数 == 9) (代码+' all nine top-level menus exist').
    位 取 0. 总位 取 0.
    循 菜单名 其 量 次
        键 取 菜单名[位].
        确认 ((菜单字 菜 位 1024) == (词 代码 键)) (代码+' native '+键+' matches catalog').
        子 取 窗 其 成功 (_GetSubMenu 其 调用 [菜,位]) 'GetSubMenu(i18n fixture)'.
        确认 ((窗 其 结果 (_GetMenuItemCount 其 调用 [子])) 其 数 == 菜单数[位]) (代码+' native '+键+' preserves all command entries').
        循 菜单数[位] 次
            确认 ((菜单字 子 命令号[总位] 0) == (词 代码 命令键[总位])) (代码+' command '+(命令号[总位] 为 句)+' has exact catalog text and shortcut').
            总位 取 总位+1.
        环
        位 取 位+1.
    环
    子 取 窗 其 成功 (_GetSubMenu 其 调用 [菜,7]) 'GetSubMenu(interface language)'.
    候选 取 ['system','en','zh-CN','ja','ko','es','ru','it'].
    位 取 0.
    循 8 次
        标记 取 (窗 其 结果 (_GetMenuState 其 调用 [子,850+位,0])) 其 数.
        已选 取 标记%16 >= 8.
        确认 (标记 != 4294967295 且 已选 == (候选[位] == 代码)) (代码+' native language checkmark '+候选[位]).
        位 取 位+1.
    环
为
# Independent fixture-only reader: bounded nested blocks avoid mirroring the
# former production WCHAR-per-field structure limit. No production buffer write.
算 过滤读型 数量 为 数:
    若 数量 < 2 或 数量 > 8192 则 卒 'Filter fixture reader bounds.'. 然
    块们 取 []. 起位 取 0. 块位 取 0.
    循
        若 起位 >= 数量 则 破. 然
        字段们 取 []. 位 取 0.
        循
            若 位 >= 64 或 起位+位 >= 数量 则 破. 然
            字段们 其 增 [('u'+(位 为 句)),(窗 其 W)].
            位 取 位+1.
        环
        块们 其 增 [('b'+(块位 为 句)),(密 其 结构 字段们)].
        起位 取 起位+位. 块位 取 块位+1.
    环
    得 密 其 结构 块们.
法
算 过滤读字 存 位 为 数:
    块位 取 (位-位%64)/64.
    块 取 存 其 读 ('b'+(块位 为 句)).
    值 取 (块 其 读 ('u'+((位%64) 为 句))) 其 数.
    块 其 关闭.
    得 值.
法
作 验过滤 代码 为 句:
    滤 取 窗 其 文件过滤.
    文字 取 (词 代码 'file.filter.all')+'|*.*|'+(词 代码 'file.filter.text')+'|*.txt|'+(词 代码 'file.filter.ru')+'|*.ru|'+(词 代码 'file.filter.markdown')+'|*.md;*.markdown|'.
    存 取 密 其 UTF16 文字.
    数量 取 (存 其 大小)/2.
    型 取 过滤读型 数量.
    预期 取 型 其 新建. 实存 取 型 其 新建.
    试
        窗 其 结果 ((窗 其 RtlMoveMemory) 其 调用 [预期,存,(存 其 大小)]).
        确认 ((滤 其 大小) == (存 其 大小) 且 (型 其 大小) == (存 其 大小)) (代码+' filter allocation has the exact UTF16 size').
        窗 其 结果 ((窗 其 RtlMoveMemory) 其 调用 [实存,滤,(滤 其 大小)]).
        相同 取 真. 零数 取 0. 段数 取 0. 段长 取 0.
        位 取 0.
        循 数量 次
            应 取 过滤读字 预期 位.
            若 应 == 124 则 应 取 0. 然
            实 取 过滤读字 实存 位.
            若 实 != 应 则 相同 取 假. 然
            若 实 == 0 则
                零数 取 零数+1.
                若 段长 > 0 则 段数 取 段数+1. 然
                段长 取 0.
            另 段长 取 段长+1. 然
            位 取 位+1.
        环
        确认 相同 (代码+' filter WCHAR fields exactly match localized labels and invariant wildcards').
        确认 (零数 == 9 且 段数 == 8 且 段长 == 0) (代码+' filter has four nonempty label-pattern pairs and no extra fields').
        确认 ((过滤读字 实存 (数量-2)) == 0 且 (过滤读字 实存 (数量-1)) == 0) (代码+' filter ends with exactly the required double NUL').
    救 原因 实存 其 关闭. 预期 其 关闭. 存 其 关闭. 滤 其 关闭. 卒 原因. 终
    实存 其 关闭. 预期 其 关闭. 存 其 关闭. 滤 其 关闭.
为
作 验文字 主 代码 为 句:
    态 取 应用 其 A.
    位 取 0.
    循 按钮名 其 量 次
        名 取 按钮名[位].
        柄 取 态 其 查 名.
        文 取 词 代码 按钮键[位].
        确认 ((窗 其 取文 柄) == 文) (代码+' native '+名+' label matches catalog').
        量宽 取 窗 其 测文宽 柄 文.
        留白 取 26.
        若 名 == 'case' 或 名 == 'whole' 或 名 == 'searchWrap' 则 留白 取 44. 然
        确认 (量宽 > 0 且 (应用 其 按钮宽 名) >= 量宽+留白) (代码+' native font measurement fits '+名+' label').
        位 取 位+1.
    环
    确认 ((提示字 (态 其 查 'find')) == (词 代码 'search.find')) (代码+' native find cue banner matches catalog').
    确认 ((提示字 (态 其 查 'replace')) == (词 代码 'search.replace_with')) (代码+' native replace cue banner matches catalog').
    确认 ((窗 其 取文 (态 其 查 'find')) == 'English 中😀') (代码+' search input is user text and remains unchanged').
    确认 ((窗 其 取文 (态 其 查 'replace')) == '日本語 한국어 {0}') (代码+' replacement input remains exact Unicode').
    确认 ((窗 其 发送 (态 其 查 'case') 240 0 0) 其 数 == 0) (代码+' match-case choice remains unchanged').
    确认 ((窗 其 发送 (态 其 查 'whole') 240 0 0) 其 数 == 1) (代码+' whole-word choice remains unchanged').
    确认 ((窗 其 发送 (态 其 查 'searchWrap') 240 0 0) 其 数 == 0) (代码+' search-wrap choice remains unchanged').
    文们 取 态 其 查 'docs'.
    未位们 取 [0,2].
    位 取 0.
    循 2 次
        页位 取 未位们[位].
        页 取 文们[页位].
        名 取 本地 其 格式 'document.untitled' ([(页 其 查 'untitledNumber')]).
        确认 ((页 其 查 'name') == 名) (代码+' untitled metadata '+(页位 为 句)+' is translated').
        若 应用 其 脏 页 则 名 取 '* '+名. 然
        确认 ((页签字 页位) == 名) (代码+' real active or background untitled tab '+(页位 为 句)+' is translated').
        位 取 位+1.
    环
    页 取 文们[1].
    确认 ((页 其 查 'name') == 文件名) (代码+' real Unicode filename is never translated or brace-expanded').
    确认 ((页签字 1) == '* '+文件名) (代码+' named dirty native tab keeps its exact filename').
    确认 ((应用 其 短名 (页 其 查 'path')) == 文件名) (代码+' original Unicode basename is retained').
    当前 取 应用 其 当前.
    确认 ((窗 其 取文 主) == (应用 其 页标题 当前)+' · ru_notepad') (代码+' native main title follows active named or untitled tab').
    信息 取 状态文 其 信息 (应用 其 编辑柄).
    行尾 取 信息['lineEol'].
    若 行尾 == 'None (EOF)' 则 行尾 取 词 代码 'status.eof'. 然
    若 行尾 == 'Unknown' 则 行尾 取 词 代码 'status.unknown'. 然
    位置文 取 本地 其 格式 'status.position' ([信息['line'],信息['column'],信息['bytes'],行尾,信息['insertEol']]).
    编码文 取 应用 其 编码名 (当前 其 查 'encoding').
    若 当前 其 查 'bom' 则 编码文 取 编码文+' BOM'. 然
    确认 ((窗 其 取文 (态 其 查 'status')) == '  '+位置文+'    '+编码文+'    '+(词 代码 'syntax.plain')) (代码+' native status is translated with exact position encoding and syntax').
为
作 检验 根 为 句 入路 为 句 出路 为 句:
    记阶段 0 7 0.
    件编 其 写文件 入路 源 1200 真 ''.
    主 取 应用 其 初始化 [入路] 假.
    态 取 应用 其 A.
    装布局钩 主.
    态 其 增 'confirmClose' (算 页: 关闭询问[0] 取 关闭询问[0]+1. 得 2. 法).
    确认 ((态 其 查 'ready') 且 非 (态 其 查 'visible') 且 (窗 其 结果 (_IsWindowVisible 其 调用 [主])) 其 为空) 'real application initializes with a hidden main window'.
    确认 (态 其 查 'busy') 'Unicode CLI fixture begins asynchronous loading'.
    泵.
    文们 取 态 其 查 'docs'.
    确认 ((文们 其 量) == 2) 'Unicode CLI fixture commits one named document'.
    页 取 文们[1].
    确认 ((页 其 查 'path') == 入路 且 (页 其 查 'name') == 文件名 且 (页 其 查 'encoding') == 1200 且 (页 其 查 'bom')) 'Unicode path UTF16LE and BOM survive actual filesystem open'.
    确认 ((编 其 文本 (页 其 查 'editor')) == 源) 'actual file decodes all seven-language sample text exactly'.
    确认 (非 (应用 其 脏 页)) 'actual file initially has a clean savepoint'.
    确认 ((编 其 文本 (文们[0] 其 查 'editor')) == '' 且 非 (应用 其 脏 文们[0])) 'initial untitled page remains a separate clean document'.
    柄 取 页 其 查 'editor'.
    窗 其 发文 柄 2282 1 '!'.
    窗 其 发送 柄 2160 7 0.
    应用 其 新页 '' 草稿 65001 假 ''.
    草柄 取 应用 其 编辑柄.
    窗 其 发文 草柄 2282 1 '?'.
    窗 其 发送 草柄 2160 0 5.
    确认 ((应用 其 脏 页) 且 (应用 其 脏 (应用 其 当前))) 'named and untitled fixtures have real dirty undo actions'.
    应用 其 寻栏 真.
    窗 其 标题 (态 其 查 'find') 'English 中😀'.
    窗 其 标题 (态 其 查 'replace') '日本語 한국어 {0}'.
    窗 其 发送 (态 其 查 'case') 241 0 0.
    窗 其 发送 (态 其 查 'whole') 241 1 0.
    窗 其 发送 (态 其 查 'searchWrap') 241 0 0.
    旧们 取 [(快照 文们[0]),(快照 文们[1]),(快照 文们[2])].
    位 取 0.
    循 语言们 其 量 次
        代码 取 语言们[位].
        活 取 位%3.
        记阶段 1 位 0.
        应用 其 切页 活.
        切换 主 代码.
        确认 ((本地 其 当前语言) == 代码) (代码+' active catalog matches explicit nonpersistent choice').
        确认 ((态 其 查 'uiPreference') == 代码) (代码+' in-memory language preference matches choice').
        记阶段 2 位 0. 验菜单 主 代码.
        记阶段 3 位 0. 验文字 主 代码.
        记阶段 4 位 0. 验全部文档 旧们 活 代码.
        记阶段 5 位 0. 验过滤 代码.
        记阶段 6 位 640. 验布局 主 640 代码.
        记阶段 6 位 900. 验布局 主 900 代码.
        记阶段 6 位 1600. 验布局 主 1600 代码.
        位 取 位+1.
    环
    记阶段 7 7 0.
    # Every language and font has been warmed before bounded resource comparison.
    进程 取 窗 其 结果 (_GetCurrentProcess 其 调用 []).
    用户前 取 (窗 其 结果 (_GetGuiResources 其 调用 [进程,1])) 其 数.
    图形前 取 (窗 其 结果 (_GetGuiResources 其 调用 [进程,0])) 其 数.
    确认 (用户前 > 0 且 图形前 > 0) 'resource probes observe actual USER and GDI allocations'.
    循 4 次
        位 取 0.
        循 语言们 其 量 次 切换 主 语言们[位]. 位 取 位+1. 环
    环
    确认 ((窗 其 结果 (_GetGuiResources 其 调用 [进程,1])) 其 数 <= 用户前) 'twenty-eight repeated switches do not grow USER object count'.
    确认 ((窗 其 结果 (_GetGuiResources 其 调用 [进程,0])) 其 数 <= 图形前) 'twenty-eight repeated switches release measurement DC and GDI objects'.
    验全部文档 旧们 0 'repeated switches'.
    记阶段 8 7 0.
    # Verify real undo/redo behavior after every UI rebuild, not only CANUNDO.
    窗 其 发送 柄 2176 0 0.
    确认 ((编 其 文本 柄) == 源 且 非 (应用 其 脏 页)) 'one named-document undo restores exact original text and savepoint'.
    窗 其 发送 柄 2011 0 0.
    确认 ((编 其 文本 柄) == 源+'!' 且 (应用 其 脏 页)) 'named-document redo retains its original single action'.
    窗 其 发送 柄 2176 0 0.
    窗 其 发送 草柄 2176 0 0.
    确认 ((编 其 文本 草柄) == 草稿 且 非 (应用 其 脏 文们[2])) 'untitled undo history and savepoint survive all switches'.
    原读 取 件编 其 读文件 入路 0.
    确认 (原读['text'] == 源 且 原读['encoding'] == 1200 且 原读['bom']) 'source file bytes decode unchanged after switches and edits'.
    态 其 增 'chooseSavePath' (算 原路: 得 出路. 法).
    应用 其 切页 1.
    确认 (应用 其 保存 真) 'localized UI uses the real asynchronous Save As pipeline'.
    泵.
    读回 取 件编 其 读文件 出路 0.
    确认 (读回['text'] == 源 且 读回['encoding'] == 1200 且 读回['bom']) 'saved Unicode filename round-trips exact multilingual UTF16LE text and BOM'.
    确认 ((页 其 查 'path') == 出路 且 非 (应用 其 脏 页)) 'successful Unicode Save As keeps the named document clean'.
    确认 (((态 其 查 'errors') 其 量) == 0) 'real language switches and file operations report no application errors'.
    记阶段 9 7 0.
    卸布局钩.
    确认 (应用 其 关程序) 'all clean localized documents close without prompting'.
    确认 (关闭询问[0] == 0 且 非 (态 其 查 'ready')) 'shutdown requires no dirty prompt and releases the real window'.
为
作 删除拥有 路 为 句 必须 为 事实:
    存 取 密 其 UTF16 路.
    果 取 _DeleteFileW 其 调用 [存].
    存 其 关闭.
    若 必须 则 窗 其 成功 果 'Delete owned i18n file'. 然
为
作 删除目录 根 为 句 必须 为 事实:
    存 取 密 其 UTF16 根.
    果 取 _RemoveDirectoryW 其 调用 [存].
    存 其 关闭.
    若 必须 则 窗 其 成功 果 'Remove owned i18n directory'. 然
为
算 元初 参数 为 句 阵:
    若 (参数 其 量) != 1 则 显 'Usage: app_i18n_native.exe EXISTING_DISPOSABLE_DIRECTORY'. 得 2. 然
    号 取 (窗 其 结果 (_GetCurrentProcessId 其 调用 [])) 其 句.
    根 取 参数[0]+'\\ru-i18n-owned-'+号+'-'+(计时 为 句)+'-甲😀'.
    存 取 密 其 UTF16 根.
    创建 取 _CreateDirectoryW 其 调用 [存,空].
    存 其 关闭.
    # A collision fails before any owned-file write or cleanup can occur.
    窗 其 成功 创建 'Create exclusively owned i18n fixture directory'.
    入路 取 根+'\\'+文件名.
    出路 取 根+'\\另存 日本語 한국어 русский italiano 😀.txt'.
    试
        检验 根 入路 出路.
    救 原因
        试 应用 其 清操作. 救 清因 显 'Fixture pending-operation cleanup failed: '+清因. 终
        试 卸布局钩. 救 清因 显 'Fixture layout-guard cleanup failed: '+清因. 终
        态 取 应用 其 A.
        若 态 其 查 'ready' 则
            态 其 增 'ready' 假.
            窗 其 结果 ((窗 其 DestroyWindow) 其 调用 [(态 其 查 'window')]).
        然
        删除拥有 入路 假. 删除拥有 出路 假. 删除目录 根 假.
        卒 原因.
    终
    记阶段 10 7 0.
    删除拥有 入路 真. 删除拥有 出路 真. 删除目录 根 真.
    存 取 密 其 UTF16 根.
    属性 取 (窗 其 结果 (_GetFileAttributesW 其 调用 [存])) 其 数.
    存 其 关闭.
    确认 (属性 == 4294967295) 'owned synthetic Unicode fixture directory is fully removed'.
    # 8 setup +7*(1 switch+2 choices+78 menu+34 UI+30 state+4 filter+3*23 layout)
    # +61 warmed resource/state checks +10 undo/save/shutdown +1 cleanup =1606.
    若 次数[0] != 1606 则 卒 'FAIL: unexpected app i18n assertion count: '+(次数[0] 为 句). 然
    显 'TOTAL PASS: '+(次数[0] 为 句).
    得 0.
法
