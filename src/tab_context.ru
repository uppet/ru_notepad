# Narrow Win32 mechanics; policy and document lifetime remain in Ru.
密 取 外言 '如:密'.
窗 取 外言 'win32.ru'.
本地 取 外言 'i18n.ru'.
_GetCursorPos 取 (窗 其 用户) 其 绑定 'GetCursorPos' (密 其 签名 (窗 其 I) ([(窗 其 PTR)]) 'win64').
_ScreenToClient 取 (窗 其 用户) 其 绑定 'ScreenToClient' (密 其 签名 (窗 其 I) ([(窗 其 PTR),(窗 其 PTR)]) 'win64').
_TrackPopupMenu 取 (窗 其 用户) 其 绑定 'TrackPopupMenu' (密 其 签名 (窗 其 I) ([(窗 其 PTR),(窗 其 U),(窗 其 I),(窗 其 I),(窗 其 I),(窗 其 PTR),(窗 其 PTR)]) 'win64').
_命中型 取 密 其 结构 [['x',窗 其 I],['y',窗 其 I],['flags',窗 其 U]].
算 点击 标签:
    点 取 (窗 其 POINT) 其 新建.
    命中 取 _命中型 其 新建.
    位盒 取 [-1].
    试
        窗 其 成功 (_GetCursorPos 其 调用 [点]) 'GetCursorPos'.
        窗 其 成功 (_ScreenToClient 其 调用 [标签,点]) 'ScreenToClient'.
        命中 其 写 'x' (点 其 读 'x').
        命中 其 写 'y' (点 其 读 'y').
        位盒[0] 取 (窗 其 发指 标签 4877 0 命中) 其 数.
    救 原因
        点 其 关闭. 命中 其 关闭. 卒 原因.
    终
    点 其 关闭. 命中 其 关闭.
    得 位盒[0].
法
算 弹出 主窗, 可用 为 阵:
    菜 取 窗 其 成功 ((窗 其 CreatePopupMenu) 其 调用 []) 'CreatePopupMenu(tab)'.
    点 取 (窗 其 POINT) 其 新建.
    号盒 取 [0].
    试
        键们 取 ['tab.close_current','tab.close_others','tab.close_left','tab.close_right','tab.close_saved','tab.close_all'].
        位 取 0.
        循 6 次
            旗 取 0. 若 非 可用[位] 则 旗 取 3. 然
            窗 其 菜单项 菜 旗 (1300+位) (本地 其 文本 键们[位]).
            位 取 位+1.
        环
        窗 其 成功 (_GetCursorPos 其 调用 [点]) 'GetCursorPos'.
        # TPM_RETURNCMD | TPM_NONOTIFY | TPM_RIGHTBUTTON.
        号盒[0] 取 (窗 其 结果 (_TrackPopupMenu 其 调用 [菜,386,((点 其 读 'x') 其 数),((点 其 读 'y') 其 数),0,主窗,空])) 其 数.
    救 原因
        点 其 关闭. 窗 其 结果 ((窗 其 DestroyMenu) 其 调用 [菜]). 卒 原因.
    终
    点 其 关闭.
    窗 其 结果 ((窗 其 DestroyMenu) 其 调用 [菜]).
    得 号盒[0].
法
