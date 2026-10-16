# Synthetic shell HDROP construction for native Windows tests only.
# No filesystem path is opened and ownership transfers to the receiver.
密 取 外言 '如:密'.
_PTR 取 密 其 指针.
_UP 取 密 其 uintptr.
_U32 取 密 其 u32.
_I32 取 密 其 i32.
_VOID 取 密 其 无值.
_内核 取 密 其 系统库 'kernel32.dll'.
_GlobalAlloc 取 _内核 其 绑定 'GlobalAlloc' (密 其 签名 _PTR ([_U32,_UP]) 'win64').
_GlobalLock 取 _内核 其 绑定 'GlobalLock' (密 其 签名 _PTR ([_PTR]) 'win64').
_GlobalUnlock 取 _内核 其 绑定 'GlobalUnlock' (密 其 签名 _I32 ([_PTR]) 'win64').
_GlobalFree 取 _内核 其 绑定 'GlobalFree' (密 其 签名 _PTR ([_PTR]) 'win64').
_GlobalFlags 取 _内核 其 绑定 'GlobalFlags' (密 其 签名 _U32 ([_PTR]) 'win64').
_RtlMoveMemory 取 _内核 其 绑定 'RtlMoveMemory' (密 其 签名 _VOID ([_PTR,_PTR,_UP]) 'win64').
_头型 取 密 其 结构 [['offset',_U32],['x',_I32],['y',_I32],['nonclient',_I32],['wide',_I32]].
_坏型 取 密 其 结构 [['surrogate',(密 其 u16)],['zero',(密 其 u16)]].

算 _打包 存们 为 阵:
    大小 取 (_头型 其 大小)+4.
    位 取 0.
    循 存们 其 量 次
        大小 取 大小+(存们[位] 其 大小).
        位 取 位+1.
    环
    头 取 _头型 其 新建.
    头 其 写 'offset' (_头型 其 大小).
    头 其 写 'wide' 1.
    柄 取 (_GlobalAlloc 其 调用 [66,大小]) 其 值.
    若 柄 其 为空 则 头 其 关闭. 卒 'HDROP fixture GlobalAlloc failed'. 然
    址 取 (_GlobalLock 其 调用 [柄]) 其 值.
    若 址 其 为空 则
        _GlobalFree 其 调用 [柄].
        头 其 关闭.
        卒 'HDROP fixture GlobalLock failed'.
    然
    试
        _RtlMoveMemory 其 调用 [址,头,头 其 大小].
        偏 取 头 其 大小.
        位 取 0.
        循 存们 其 量 次
            目标 取 _PTR 其 值 ((址 其 数)+偏).
            存 取 存们[位].
            _RtlMoveMemory 其 调用 [目标,存,存 其 大小].
            偏 取 偏+(存 其 大小).
            位 取 位+1.
        环
    救 原因
        _GlobalUnlock 其 调用 [柄].
        _GlobalFree 其 调用 [柄].
        头 其 关闭.
        卒 原因.
    终
    _GlobalUnlock 其 调用 [柄].
    头 其 关闭.
    得 柄.
法

算 创建 路径们 为 阵:
    存们 取 [].
    柄 取 空.
    位 取 0.
    试
        循 路径们 其 量 次
            存们 其 增 (密 其 UTF16 路径们[位]).
            位 取 位+1.
        环
        柄 取 _打包 存们.
    救 原因
        位 取 0.
        循 存们 其 量 次 存们[位] 其 关闭. 位 取 位+1. 环
        卒 原因.
    终
    位 取 0.
    循 存们 其 量 次 存们[位] 其 关闭. 位 取 位+1. 环
    得 柄.
法

算 无效编码 单元 为 数:
    存 取 _坏型 其 新建.
    存 其 写 'surrogate' 单元.
    柄 取 空.
    试 柄 取 _打包 [存]. 救 原因 存 其 关闭. 卒 原因. 终
    存 其 关闭.
    得 柄.
法

算 已释放 柄:
    得 ((_GlobalFlags 其 调用 [柄]) 其 值) 其 数 == 32768.
法
