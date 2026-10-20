# Win32 declarations owned by ru_notepad; ABI is Windows x64 only.
本地 取 外言 'i18n.ru'.
密 取 外言 '如:密'.
PTR 取 密 其 指针.
I 取 密 其 i32.
U 取 密 其 u32.
W 取 密 其 u16.
UP 取 密 其 uintptr.
IP 取 密 其 intptr.
V 取 密 其 无值.
用户 取 密 其 系统库 'user32.dll'.
内核 取 密 其 系统库 'kernel32.dll'.
对话 取 密 其 系统库 'comdlg32.dll'.
控件 取 密 其 系统库 'comctl32.dll'.
图形 取 密 其 系统库 'gdi32.dll'.
POINT 取 密 其 结构 [['x',I],['y',I]].
RECT 取 密 其 结构 [['left',I],['top',I],['right',I],['bottom',I]].
MINMAXINFO 取 密 其 结构 [['reservedX',I],['reservedY',I],['maxSizeX',I],['maxSizeY',I],['maxPositionX',I],['maxPositionY',I],['minTrackX',I],['minTrackY',I],['maxTrackX',I],['maxTrackY',I]].
MSG 取 密 其 结构 [['hwnd',PTR],['message',U],['wParam',UP],['lParam',IP],['time',U],['pt',POINT],['lPrivate',U]].
WNDCLASS 取 密 其 结构 [['size',U],['style',U],['proc',PTR],['classExtra',I],['windowExtra',I],['instance',PTR],['icon',PTR],['cursor',PTR],['background',PTR],['menu',PTR],['name',PTR],['smallIcon',PTR]].
WNDPROC 取 密 其 签名 IP ([PTR,U,UP,IP]) 'win64'.
NMHDR 取 密 其 结构 [['hwndFrom',PTR],['idFrom',UP],['code',U]].
TCITEM 取 密 其 结构 [['mask',U],['state',U],['stateMask',U],['text',PTR],['textMax',I],['image',I],['param',IP]].
OPENFILE 取 密 其 结构 [['size',U],['owner',PTR],['instance',PTR],['filter',PTR],['customFilter',PTR],['maxCustomFilter',U],['filterIndex',U],['file',PTR],['maxFile',U],['fileTitle',PTR],['maxFileTitle',U],['initialDir',PTR],['title',PTR],['flags',U],['fileOffset',W],['fileExtension',W],['defaultExt',PTR],['customData',IP],['hook',PTR],['template',PTR],['reserved',PTR],['reserved2',U],['flagsEx',U]].
INITCONTROLS 取 密 其 结构 [['size',U],['classes',U]].
RegisterClassExW 取 用户 其 绑定 'RegisterClassExW' (密 其 签名 W ([PTR]) 'win64').
UnregisterClassW 取 用户 其 绑定 'UnregisterClassW' (密 其 签名 I ([PTR,PTR]) 'win64').
CreateWindowExW 取 用户 其 绑定 'CreateWindowExW' (密 其 签名 PTR ([U,PTR,PTR,U,I,I,I,I,PTR,PTR,PTR,PTR]) 'win64').
DefWindowProcW 取 用户 其 绑定 'DefWindowProcW' (密 其 签名 IP ([PTR,U,UP,IP]) 'win64').
ShowWindow 取 用户 其 绑定 'ShowWindow' (密 其 签名 I ([PTR,I]) 'win64').
UpdateWindow 取 用户 其 绑定 'UpdateWindow' (密 其 签名 I ([PTR]) 'win64').
GetMessageW 取 用户 其 绑定 'GetMessageW' (密 其 签名 I ([PTR,PTR,U,U]) 'win64').
TranslateMessage 取 用户 其 绑定 'TranslateMessage' (密 其 签名 I ([PTR]) 'win64').
DispatchMessageW 取 用户 其 绑定 'DispatchMessageW' (密 其 签名 IP ([PTR]) 'win64').
EnableWindow 取 用户 其 绑定 'EnableWindow' (密 其 签名 I ([PTR,I]) 'win64').
PeekMessageW 取 用户 其 绑定 'PeekMessageW' (密 其 签名 I ([PTR,PTR,U,U,U]) 'win64').
GetQueueStatus 取 用户 其 绑定 'GetQueueStatus' (密 其 签名 U ([U]) 'win64').
PostQuitMessage 取 用户 其 绑定 'PostQuitMessage' (密 其 签名 V ([I]) 'win64').
DestroyWindow 取 用户 其 绑定 'DestroyWindow' (密 其 签名 I ([PTR]) 'win64').
SetWindowTextW 取 用户 其 绑定 'SetWindowTextW' (密 其 签名 I ([PTR,PTR]) 'win64').
GetWindowTextW 取 用户 其 绑定 'GetWindowTextW' (密 其 签名 I ([PTR,PTR,I]) 'win64').
GetWindowTextLengthW 取 用户 其 绑定 'GetWindowTextLengthW' (密 其 签名 I ([PTR]) 'win64').
LoadCursorW 取 用户 其 绑定 'LoadCursorW' (密 其 签名 PTR ([PTR,PTR]) 'win64').
GetSysColorBrush 取 用户 其 绑定 'GetSysColorBrush' (密 其 签名 PTR ([I]) 'win64').
SendMessageW 取 用户 其 绑定 'SendMessageW' (密 其 签名 IP ([PTR,U,UP,IP]) 'win64').
PostMessageW 取 用户 其 绑定 'PostMessageW' (密 其 签名 I ([PTR,U,UP,IP]) 'win64').
MoveWindow 取 用户 其 绑定 'MoveWindow' (密 其 签名 I ([PTR,I,I,I,I,I]) 'win64').
GetClientRect 取 用户 其 绑定 'GetClientRect' (密 其 签名 I ([PTR,PTR]) 'win64').
SetFocus 取 用户 其 绑定 'SetFocus' (密 其 签名 PTR ([PTR]) 'win64').
MessageBoxW 取 用户 其 绑定 'MessageBoxW' (密 其 签名 I ([PTR,PTR,PTR,U]) 'win64').
CreateMenu 取 用户 其 绑定 'CreateMenu' (密 其 签名 PTR ([]) 'win64').
CreatePopupMenu 取 用户 其 绑定 'CreatePopupMenu' (密 其 签名 PTR ([]) 'win64').
AppendMenuW 取 用户 其 绑定 'AppendMenuW' (密 其 签名 I ([PTR,U,UP,PTR]) 'win64').
SetMenu 取 用户 其 绑定 'SetMenu' (密 其 签名 I ([PTR,PTR]) 'win64').
DrawMenuBar 取 用户 其 绑定 'DrawMenuBar' (密 其 签名 I ([PTR]) 'win64').
GetMenu 取 用户 其 绑定 'GetMenu' (密 其 签名 PTR ([PTR]) 'win64').
DestroyMenu 取 用户 其 绑定 'DestroyMenu' (密 其 签名 I ([PTR]) 'win64').
GetDC 取 用户 其 绑定 'GetDC' (密 其 签名 PTR ([PTR]) 'win64').
ReleaseDC 取 用户 其 绑定 'ReleaseDC' (密 其 签名 I ([PTR,PTR]) 'win64').
GetStockObject 取 图形 其 绑定 'GetStockObject' (密 其 签名 PTR ([I]) 'win64').
SelectObject 取 图形 其 绑定 'SelectObject' (密 其 签名 PTR ([PTR,PTR]) 'win64').
GetTextExtentPoint32W 取 图形 其 绑定 'GetTextExtentPoint32W' (密 其 签名 I ([PTR,PTR,I,PTR]) 'win64').
GetKeyState 取 用户 其 绑定 'GetKeyState' (密 其 签名 W ([I]) 'win64').
IsDialogMessageW 取 用户 其 绑定 'IsDialogMessageW' (密 其 签名 I ([PTR,PTR]) 'win64').
SetTimer 取 用户 其 绑定 'SetTimer' (密 其 签名 UP ([PTR,UP,U,PTR]) 'win64').
KillTimer 取 用户 其 绑定 'KillTimer' (密 其 签名 I ([PTR,UP]) 'win64').
LoadImageW 取 用户 其 绑定 'LoadImageW' (密 其 签名 PTR ([PTR,PTR,U,I,I,U]) 'win64').
GetModuleHandleW 取 内核 其 绑定 'GetModuleHandleW' (密 其 签名 PTR ([PTR]) 'win64').
GetModuleFileNameW 取 内核 其 绑定 'GetModuleFileNameW' (密 其 签名 U ([PTR,PTR,U]) 'win64').
RtlMoveMemory 取 内核 其 绑定 'RtlMoveMemory' (密 其 签名 V ([PTR,PTR,UP]) 'win64').
GetTickCount64 取 内核 其 绑定 'GetTickCount64' (密 其 签名 UP ([]) 'win64').
GetOpenFileNameW 取 对话 其 绑定 'GetOpenFileNameW' (密 其 签名 I ([PTR]) 'win64').
GetSaveFileNameW 取 对话 其 绑定 'GetSaveFileNameW' (密 其 签名 I ([PTR]) 'win64').
CommDlgExtendedError 取 对话 其 绑定 'CommDlgExtendedError' (密 其 签名 U ([]) 'win64').
InitCommonControlsEx 取 控件 其 绑定 'InitCommonControlsEx' (密 其 签名 I ([PTR]) 'win64').

lstrlenA 取 内核 其 绑定 'lstrlenA' (密 其 签名 I ([PTR]) 'win64').
MultiByteToWideChar 取 内核 其 绑定 'MultiByteToWideChar' (密 其 签名 I ([U,U,PTR,I,PTR,I]) 'win64').
WideCharToMultiByte 取 内核 其 绑定 'WideCharToMultiByte' (密 其 签名 I ([U,U,PTR,I,PTR,I,PTR,PTR]) 'win64').
lstrlenW 取 内核 其 绑定 'lstrlenW' (密 其 签名 I ([PTR]) 'win64').

ShutdownBlockReasonCreate 取 用户 其 绑定 'ShutdownBlockReasonCreate' (密 其 签名 I ([PTR,PTR]) 'win64').
ShutdownBlockReasonDestroy 取 用户 其 绑定 'ShutdownBlockReasonDestroy' (密 其 签名 I ([PTR]) 'win64').

LoadLibraryExW 取 内核 其 绑定 'LoadLibraryExW' (密 其 签名 PTR ([PTR,PTR,U]) 'win64').
FreeLibrary 取 内核 其 绑定 'FreeLibrary' (密 其 签名 I ([PTR]) 'win64').

算 结果 成果:
    若 成果 其 回调错误 != 空 则 卒 (本地 其 格式 'error.win32.callback' ([(成果 其 回调错误)])). 然
    得 成果 其 值.
法
算 成功 成果, 名 为 句:
    值 取 结果 成果.
    若 值 其 为空 则 卒 (本地 其 格式 'error.win32.api' ([名,((成果 其 错误码) 为 句)])). 然
    得 值.
法
算 发送 柄, 号, 宽, 长:
    得 结果 (SendMessageW 其 调用 [柄,号,宽,长]).
法
算 发指 柄, 号, 宽, 内存:
    得 发送 柄 号 宽 (IP 其 重释 (内存 其 地址)).
法
算 发文 柄, 号, 宽, 文 为 句:
    存 取 密 其 UTF8 文.
    得值 取 发指 柄 号 宽 存.
    存 其 关闭.
    得 得值.
法
算 标题 柄, 文 为 句:
    存 取 密 其 UTF16 文.
    值 取 成功 (SetWindowTextW 其 调用 [柄,存]) 'SetWindowTextW'.
    存 其 关闭.
    得 值.
法
# Validate foreign UTF-16 before invoking the native runtime decoder. Its own
# malformed-input failure is fatal, while this rejection is an ordinary 卒.
算 解宽 存, 长 为 数:
    若 长 < 0 或 长 > 1048576 则 卒 (本地 其 文本 'error.win32.external_too_long'). 然
    若 (结果 (lstrlenW 其 调用 [存])) 其 数 != 长 则 卒 (本地 其 文本 'error.win32.external_nul'). 然
    若 长 == 0 则 得 ''. 然
    验 取 结果 (WideCharToMultiByte 其 调用 [65001,128,存,长,空,0,空,空]).
    若 验 其 为空 则 卒 (本地 其 文本 'error.win32.external_utf16'). 然
    得 存 其 解UTF16.
法
算 取文 柄:
    长 取 (结果 (GetWindowTextLengthW 其 调用 [柄])) 其 数.
    若 长 > 1048576 则 卒 (本地 其 文本 'error.win32.input_too_long'). 然
    存 取 密 其 缓冲 ((长+2)*2).
    试
        实长 取 (结果 (GetWindowTextW 其 调用 [柄,存,长+1])) 其 数.
        文 取 解宽 存 实长.
    救 原因
        存 其 关闭.
        卒 原因.
    终
    存 其 关闭.
    得 文.
法
算 弹窗 柄, 文 为 句, 标 为 句, 标记 为 数:
    内容 取 密 其 UTF16 文.
    标题存 取 密 其 UTF16 标.
    值 取 (结果 (MessageBoxW 其 调用 [柄,内容,标题存,标记])) 其 数.
    内容 其 关闭.
    标题存 其 关闭.
    得 值.
法
算 控制 父, 实例, 类 为 句, 文 为 句, 风格 为 数, 编号 为 数:
    类存 取 密 其 UTF16 类.
    文存 取 密 其 UTF16 文.
    成果 取 CreateWindowExW 其 调用 [0,类存,文存,风格,0,0,100,30,父,(PTR 其 值 编号),实例,空].
    类存 其 关闭.
    文存 其 关闭.
    得 成功 成果 'CreateWindowExW'.
法
算 菜单项 菜单, 标记, 号, 文 为 句:
    存 取 密 其 UTF16 文.
    成功 (AppendMenuW 其 调用 [菜单,标记,号,存]) 'AppendMenuW'.
    存 其 关闭.
    得 空.
法
算 目录:
    存 取 密 其 缓冲 65538.
    长 取 (结果 (GetModuleFileNameW 其 调用 [空,存,32768])) 其 数.
    若 长 == 0 或 长 >= 32768 则 存 其 关闭. 卒 (本地 其 文本 'error.win32.app_directory'). 然
    试
        全 取 解宽 存 长.
    救 原因
        存 其 关闭.
        卒 原因.
    终
    存 其 关闭.
    位 取 全 其 量.
    循
        若 位 <= 0 则 破. 然
        位 取 位-1.
        若 全[位] == '\\' 或 全[位] == '/' 则 得 全[0:位+1]. 然
    环
    卒 (本地 其 文本 'error.win32.no_directory').
法
# Wide-only labels and measurements. Windows handles font fallback for glyphs.
算 界面字体 柄:
    字体 取 结果 (GetStockObject 其 调用 [17]).
    若 非 (字体 其 为空) 则 发送 柄 48 (UP 其 重释 字体) 1. 然
    得 空.
法
算 输入提示 柄, 文 为 句:
    存 取 密 其 UTF16 文.
    发指 柄 5377 1 存.
    存 其 关闭.
    得 空.
法
算 测文宽 柄, 文 为 句:
    存 取 密 其 UTF16 文.
    大小 取 POINT 其 新建.
    画 取 成功 (GetDC 其 调用 [柄]) 'GetDC'.
    字体 取 发送 柄 49 0 0.
    旧 取 空.
    若 非 (字体 其 为空) 则 旧 取 结果 (SelectObject 其 调用 [画,(PTR 其 重释 字体)]). 然
    果 取 GetTextExtentPoint32W 其 调用 [画,存,((存 其 大小)/2-1),大小].
    宽 取 (大小 其 读 'x') 其 数.
    若 旧 != 空 且 非 (旧 其 为空) 则 结果 (SelectObject 其 调用 [画,旧]). 然
    结果 (ReleaseDC 其 调用 [柄,画]).
    大小 其 关闭.
    存 其 关闭.
    成功 果 'GetTextExtentPoint32W'.
    得 宽.
法
# Native filters are a sequence of NUL-terminated UTF-16 fields plus final NUL.
# Build owned WCHAR fields, replacing only our ASCII separators, never user paths.
算 文件过滤:
    文 取 (本地 其 文本 'file.filter.all')+'|*.*|'+(本地 其 文本 'file.filter.text')+'|*.txt|'+(本地 其 文本 'file.filter.ru')+'|*.ru|'+(本地 其 文本 'file.filter.markdown')+'|*.md;*.markdown|'.
    存 取 密 其 UTF16 文.
    数量 取 (存 其 大小)/2.
    字段们 取 [].
    位 取 0.
    循 数量 次
        字段们 其 增 [('u'+(位 为 句)),W].
        位 取 位+1.
    环
    类型 取 密 其 结构 字段们.
    滤 取 类型 其 新建.
    结果 (RtlMoveMemory 其 调用 [滤,存,(存 其 大小)]).
    存 其 关闭.
    位 取 0.
    循 数量 次
        名 取 'u'+(位 为 句).
        若 ((滤 其 读 名) 其 数) == 124 则 滤 其 写 名 0. 然
        位 取 位+1.
    环
    得 滤.
法
算 文件对话 父, 保存 为 事实, 原名 为 句:
    存 取 密 其 缓冲 65538.
    若 原名 != '' 则
        旧 取 密 其 UTF16 原名.
        若 旧 其 大小 > 65536 则 旧 其 关闭. 存 其 关闭. 卒 (本地 其 文本 'error.win32.path_too_long'). 然
        结果 (RtlMoveMemory 其 调用 [存,旧,旧 其 大小]).
        旧 其 关闭.
    然
    滤 取 文件过滤.
    标题文 取 本地 其 文本 'file.dialog.open'.
    若 保存 则 标题文 取 本地 其 文本 'file.dialog.save'. 然
    标题存 取 密 其 UTF16 标题文.
    配 取 OPENFILE 其 新建.
    配 其 写 'size' (OPENFILE 其 大小).
    配 其 写 'owner' 父.
    配 其 写 'title' (标题存 其 地址).
    配 其 写 'filter' (滤 其 地址).
    配 其 写 'filterIndex' 1.
    配 其 写 'file' (存 其 地址).
    配 其 写 'maxFile' 32768.
    # OFN_EXPLORER | NOCHANGEDIR | PATHMUSTEXIST | (OVERWRITEPROMPT or FILEMUSTEXIST)
    标志 取 524296+2048.
    若 保存 则 标志 取 标志+2. 另 标志 取 标志+4096. 然
    配 其 写 'flags' 标志.
    结果值 取 0.
    若 保存 则
        结果值 取 (结果 (GetSaveFileNameW 其 调用 [配])) 其 数.
    另
        结果值 取 (结果 (GetOpenFileNameW 其 调用 [配])) 其 数.
    然
    路 取 ''.
    试
        若 结果值 != 0 则 路 取 解宽 存 ((结果 (lstrlenW 其 调用 [存])) 其 数). 然
    救 原因
        存 其 关闭.
        配 其 关闭.
        滤 其 关闭.
        标题存 其 关闭.
        卒 原因.
    终
    存 其 关闭.
    配 其 关闭.
    滤 其 关闭.
    标题存 其 关闭.
    若 结果值 == 0 则
        错 取 (结果 (CommDlgExtendedError 其 调用 [])) 其 数.
        若 错 != 0 则 卒 (本地 其 格式 'error.win32.file_dialog' ([(错 为 句)])). 然
    然
    得 路.
法
