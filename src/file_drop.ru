# Windows x64 shell file drops. 接收 takes ownership of one real HDROP.
# Decode the complete list before the caller opens files or shows any dialog.
本地 取 外言 'i18n.ru'.
密 取 外言 '如:密'.
_PTR 取 密 其 指针.
_U32 取 密 其 u32.
_I32 取 密 其 i32.
_UP 取 密 其 uintptr.
_IP 取 密 其 intptr.
_VOID 取 密 其 无值.
_壳 取 密 其 系统库 'shell32.dll'.
_内核 取 密 其 系统库 'kernel32.dll'.
_用户 取 密 其 系统库 'user32.dll'.
_控件 取 密 其 系统库 'comctl32.dll'.
_OLE 取 密 其 系统库 'ole32.dll'.
_WideCharToMultiByte 取 _内核 其 绑定 'WideCharToMultiByte' (密 其 签名 _I32 ([_U32,_U32,_PTR,_I32,_PTR,_I32,_PTR,_PTR]) 'win64').
_DragAcceptFiles 取 _壳 其 绑定 'DragAcceptFiles' (密 其 签名 _VOID ([_PTR,_I32]) 'win64').
_DragQueryFileW 取 _壳 其 绑定 'DragQueryFileW' (密 其 签名 _U32 ([_PTR,_U32,_PTR,_U32]) 'win64').
_DragFinish 取 _壳 其 绑定 'DragFinish' (密 其 签名 _VOID ([_PTR]) 'win64').
_RevokeDragDrop 取 _OLE 其 绑定 'RevokeDragDrop' (密 其 签名 _I32 ([_PTR]) 'win64').
_SetWindowSubclass 取 _控件 其 绑定 'SetWindowSubclass' (密 其 签名 _I32 ([_PTR,_PTR,_UP,_UP]) 'win64').
_RemoveWindowSubclass 取 _控件 其 绑定 'RemoveWindowSubclass' (密 其 签名 _I32 ([_PTR,_PTR,_UP]) 'win64').
_DefSubclassProc 取 _控件 其 绑定 'DefSubclassProc' (密 其 签名 _IP ([_PTR,_U32,_UP,_IP]) 'win64').
_SendMessageW 取 _用户 其 绑定 'SendMessageW' (密 其 签名 _IP ([_PTR,_U32,_UP,_IP]) 'win64').
_GetParent 取 _用户 其 绑定 'GetParent' (密 其 签名 _PTR ([_PTR]) 'win64').
_GetWindowThreadProcessId 取 _用户 其 绑定 'GetWindowThreadProcessId' (密 其 签名 _U32 ([_PTR,_PTR]) 'win64').
_GetCurrentThreadId 取 _内核 其 绑定 'GetCurrentThreadId' (密 其 签名 _U32 ([]) 'win64').
_PostQuitMessage 取 _用户 其 绑定 'PostQuitMessage' (密 其 签名 _VOID ([_I32]) 'win64').
_子过程型 取 密 其 签名 _IP ([_PTR,_U32,_UP,_IP,_UP,_UP]) 'win64'.
_子类编号 取 1381323854.
_子回调 取 [空].

算 _编辑子过程 窗口, 消息, 宽, 长, 编号, 父引用:
    若 消息 其 数 == 563 则
        父 取 _PTR 其 重释 父引用.
        实父 取 (_GetParent 其 调用 [窗口]) 其 值.
        若 (实父 其 为空) 或 (实父 其 句) != (父 其 句) 则
            # Ownership never transfers to an unverified/reparented window.
            _DragFinish 其 调用 [(_PTR 其 重释 宽)].
            卒 (本地 其 文本 'error.drop.expired').
        然
        # The same-thread parent consumes the HDROP synchronously exactly once.
        # Never finish it here after dispatch, even if the parent reports error.
        果 取 _SendMessageW 其 调用 [父,消息,宽,长].
        若 果 其 回调错误 != 空 则 卒 (果 其 回调错误). 然
        得 果 其 值.
    然
    若 消息 其 数 == 130 则
        果 取 _RemoveWindowSubclass 其 调用 [窗口,(_子回调[0] 其 地址),编号].
        若 (果 其 值) 其 为空 则 _PostQuitMessage 其 调用 [1]. 然
    然
    果 取 _DefSubclassProc 其 调用 [窗口,消息,宽,长].
    若 果 其 回调错误 != 空 则 卒 (果 其 回调错误). 然
    得 果 其 值.
法

# One strong module-lifetime callback; do not close it while any editor exists.
_子回调[0] 取 密 其 回调 _子过程型 (算 _编辑子过程) 0.
_子回调[0] 其 失败时 _PostQuitMessage ([1]).

作 启用 窗口:
    _DragAcceptFiles 其 调用 [窗口,1].
为

算 启用编辑器 编辑器, 父窗口:
    实父 取 (_GetParent 其 调用 [编辑器]) 其 值.
    若 (实父 其 为空) 或 (实父 其 句) != (父窗口 其 句) 则 卒 (本地 其 文本 'error.drop.parent'). 然
    本线程 取 ((_GetCurrentThreadId 其 调用 []) 其 值) 其 数.
    子线程 取 ((_GetWindowThreadProcessId 其 调用 [编辑器,空]) 其 值) 其 数.
    父线程 取 ((_GetWindowThreadProcessId 其 调用 [父窗口,空]) 其 值) 其 数.
    若 子线程 != 本线程 或 父线程 != 本线程 则 卒 (本地 其 文本 'error.drop.thread'). 然
    果 取 _SetWindowSubclass 其 调用 [编辑器,(_子回调[0] 其 地址),_子类编号,(_UP 其 重释 父窗口)].
    若 (果 其 值) 其 为空 则 卒 (本地 其 文本 'error.drop.install'). 然
    # Scintilla registers an OLE text-only target. Revoke it so Explorer's OLE
    # CF_HDROP source can use the documented legacy WM_DROPFILES fallback.
    # External OLE text drops into the editor are intentionally unavailable.
    码 取 ((_RevokeDragDrop 其 调用 [编辑器]) 其 值) 其 数.
    若 码 != 0 且 码 != -2147221248 则
        _RemoveWindowSubclass 其 调用 [编辑器,(_子回调[0] 其 地址),_子类编号].
        卒 (本地 其 格式 'error.drop.enable' ([(码 为 句)])).
    然
    _DragAcceptFiles 其 调用 [编辑器,1].
    得 码.
法

算 _解码 拖柄:
    数量 取 ((_DragQueryFileW 其 调用 [拖柄,4294967295,空,0]) 其 值) 其 数.
    若 数量 > 64 则 卒 (本地 其 文本 'error.drop.count'). 然
    路径们 取 [].
    位 取 0.
    总长 取 0.
    循 数量 次
        长 取 ((_DragQueryFileW 其 调用 [拖柄,位,空,0]) 其 值) 其 数.
        若 长 == 0 或 长 > 32000 则 卒 (本地 其 文本 'error.drop.path_length'). 然
        总长 取 总长+长+1.
        若 总长 > 2097152 则 卒 (本地 其 文本 'error.drop.total_length'). 然
        存 取 密 其 缓冲 ((长+1)*2).
        试
            实长 取 ((_DragQueryFileW 其 调用 [拖柄,位,存,长+1]) 其 值) 其 数.
            若 实长 != 长 则 卒 (本地 其 文本 'error.drop.path_incomplete'). 然
            # Strict Win32 validation precedes the native decoder, whose invalid
            # UTF-16 failure is not a catchable Ru exception in this runtime.
            验 取 (_WideCharToMultiByte 其 调用 [65001,128,存,长,空,0,空,空]) 其 值.
            若 验 其 为空 则 卒 (本地 其 文本 'error.drop.path_utf16'). 然
            路 取 存 其 解UTF16.
            路径们 其 增 路.
        救 原因
            存 其 关闭.
            卒 原因.
        终
        存 其 关闭.
        位 取 位+1.
    环
    得 路径们.
法

算 接收 拖柄:
    # There is exactly one DragFinish on both success and every exception path.
    # Do not pass this HDROP to DefWindowProc or finish it again in the caller.
    路径们 取 [].
    试
        路径们 取 _解码 拖柄.
    救 原因
        _DragFinish 其 调用 [拖柄].
        卒 原因.
    终
    _DragFinish 其 调用 [拖柄].
    得 路径们.
法
