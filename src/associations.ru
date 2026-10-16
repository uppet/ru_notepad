# Opt-in HKCU candidate registration. Importing this module performs no writes.
# Windows owns defaults: no UserChoice/hash, extension default or HKLM changes.
密 取 外言 '如:密'.
策略 取 外言 './associations_policy.ru'.
_PTR 取 密 其 指针.
_U32 取 密 其 u32.
_I32 取 密 其 i32.
_VOID 取 密 其 无值.
_注册库 取 密 其 系统库 'advapi32.dll'.
_内核 取 密 其 系统库 'kernel32.dll'.
_壳 取 密 其 系统库 'shell32.dll'.
_HKCU 取 _PTR 其 值 '18446744071562067969'.
_句柄型 取 密 其 结构 [['h',_PTR]].
_数型 取 密 其 结构 [['n',_U32]].
_RegOpenKeyExW 取 _注册库 其 绑定 'RegOpenKeyExW' (密 其 签名 _I32 ([_PTR,_PTR,_U32,_U32,_PTR]) 'win64').
_RegCreateKeyExW 取 _注册库 其 绑定 'RegCreateKeyExW' (密 其 签名 _I32 ([_PTR,_PTR,_U32,_PTR,_U32,_U32,_PTR,_PTR,_PTR]) 'win64').
_RegCloseKey 取 _注册库 其 绑定 'RegCloseKey' (密 其 签名 _I32 ([_PTR]) 'win64').
_RegQueryValueExW 取 _注册库 其 绑定 'RegQueryValueExW' (密 其 签名 _I32 ([_PTR,_PTR,_PTR,_PTR,_PTR,_PTR]) 'win64').
_RegSetValueExW 取 _注册库 其 绑定 'RegSetValueExW' (密 其 签名 _I32 ([_PTR,_PTR,_U32,_U32,_PTR,_U32]) 'win64').
_RegDeleteValueW 取 _注册库 其 绑定 'RegDeleteValueW' (密 其 签名 _I32 ([_PTR,_PTR]) 'win64').
_RegDeleteKeyW 取 _注册库 其 绑定 'RegDeleteKeyW' (密 其 签名 _I32 ([_PTR,_PTR]) 'win64').
_RegQueryInfoKeyW 取 _注册库 其 绑定 'RegQueryInfoKeyW' (密 其 签名 _I32 ([_PTR,_PTR,_PTR,_PTR,_PTR,_PTR,_PTR,_PTR,_PTR,_PTR,_PTR,_PTR]) 'win64').
_GetModuleFileNameW 取 _内核 其 绑定 'GetModuleFileNameW' (密 其 签名 _U32 ([_PTR,_PTR,_U32]) 'win64').
_WideCharToMultiByte 取 _内核 其 绑定 'WideCharToMultiByte' (密 其 签名 _I32 ([_U32,_U32,_PTR,_I32,_PTR,_I32,_PTR,_PTR]) 'win64').
_ShellExecuteW 取 _壳 其 绑定 'ShellExecuteW' (密 其 签名 _PTR ([_PTR,_PTR,_PTR,_PTR,_PTR,_I32]) 'win64').
_SHChangeNotify 取 _壳 其 绑定 'SHChangeNotify' (密 其 签名 _VOID ([_I32,_U32,_PTR,_PTR]) 'win64').

作 _检查 码 为 数:
    若 码 != 0 则 卒 '无法更新打开方式候选项（Windows 错误 '+(码 为 句)+'）。'. 然
为

算 程序路径:
    容量 取 512.
    循
        存 取 密 其 缓冲 (容量*2).
        长 取 ((_GetModuleFileNameW 其 调用 [空,存,容量]) 其 值) 其 数.
        若 长 == 0 则 存 其 关闭. 卒 '无法取得当前程序的完整路径。'. 然
        若 长 < 容量 则
            验 取 (_WideCharToMultiByte 其 调用 [65001,128,存,长,空,0,空,空]) 其 值.
            若 验 其 为空 或 长 > 32000 则 存 其 关闭. 卒 '当前程序路径无效或过长。'. 然
            路 取 存 其 解UTF16.
            存 其 关闭.
            策略 其 命令 路.
            得 路.
        然
        存 其 关闭.
        容量 取 容量*2.
        若 容量 > 65536 则 卒 '当前程序路径过长。'. 然
    环
法

算 _生产配置:
    得 {'prefix':'','exe':程序路径()}.
法

算 测试配置 前缀 为 句, 可执行 为 句:
    # Public fixture seam cannot name live association keys.
    前 取 策略 其 测试前缀 前缀.
    策略 其 命令 可执行.
    得 {'prefix':前,'exe':可执行}.
法

算 _打开 配, 键 为 句, 访问 为 数:
    路存 取 密 其 UTF16 ((配 其 查 'prefix')+键).
    出 取 _句柄型 其 新建.
    码 取 ((_RegOpenKeyExW 其 调用 [_HKCU,路存,0,访问,出]) 其 值) 其 数.
    柄 取 出 其 读 'h'.
    路存 其 关闭.
    出 其 关闭.
    若 码 == 2 或 码 == 3 则 得 空. 然
    _检查 码.
    得 柄.
法

算 _有键 配, 键 为 句:
    柄 取 _打开 配 键 1.
    若 柄 == 空 则 得 假. 然
    _RegCloseKey 其 调用 [柄].
    得 真.
法

算 _读柄 柄, 名 为 句:
    名存 取 密 其 UTF16 名.
    型存 取 _数型 其 新建.
    长存 取 _数型 其 新建.
    存 取 空.
    果 取 {'exists':假,'type':0,'text':'','size':0,'valid':假}.
    试
        码 取 ((_RegQueryValueExW 其 调用 [柄,名存,空,型存,空,长存]) 其 值) 其 数.
        若 码 != 2 则
            _检查 码.
            型 取 (型存 其 读 'n') 其 数.
            长 取 (长存 其 读 'n') 其 数.
            果 其 增 'exists' 真.
            果 其 增 'type' 型.
            果 其 增 'size' 长.
            若 型 == 0 且 长 == 0 则 果 其 增 'valid' 真. 然
            若 型 == 1 且 长 >= 2 且 长 <= 131072 且 长 % 2 == 0 则
                存 取 密 其 缓冲 (长+2).
                长存 其 写 'n' 长.
                码 取 ((_RegQueryValueExW 其 调用 [柄,名存,空,型存,存,长存]) 其 值) 其 数.
                _检查 码.
                若 (型存 其 读 'n') 其 数 == 1 且 (长存 其 读 'n') 其 数 == 长 则
                    验码 取 (_WideCharToMultiByte 其 调用 [65001,128,存,长/2,空,0,空,空]) 其 值.
                    若 非 (验码 其 为空) 则
                        文 取 存 其 解UTF16.
                        验 取 密 其 UTF16 文.
                        合 取 (验 其 大小) == 长.
                        验 其 关闭.
                        果 其 增 'valid' 合.
                        果 其 增 'text' 文.
                    然
                然
            然
        然
    救 原因
        若 存 != 空 则 存 其 关闭. 然
        名存 其 关闭.
        型存 其 关闭.
        长存 其 关闭.
        卒 原因.
    终
    若 存 != 空 则 存 其 关闭. 然
    名存 其 关闭.
    型存 其 关闭.
    长存 其 关闭.
    得 果.
法

算 查询值 配, 键 为 句, 名 为 句:
    柄 取 _打开 配 键 1.
    若 柄 == 空 则 得 {'exists':假,'type':0,'text':'','size':0,'valid':假}. 然
    果 取 空.
    试
        果 取 _读柄 柄 名.
    救 原因
        _RegCloseKey 其 调用 [柄].
        卒 原因.
    终
    _RegCloseKey 其 调用 [柄].
    得 果.
法

算 _相同 值, 文 为 句, 型 为 数:
    得 (值 其 查 'exists') 且 (值 其 查 'valid') 且 (值 其 查 'type') == 型 且 (值 其 查 'text') == 文.
法

算 _根状态 配, 根 为 句, 有命令 为 事实:
    若 非 (_有键 配 根) 则 得 'missing'. 然
    拥 取 查询值 配 根 'RuNotepadOwner'.
    若 非 (_相同 拥 (配 其 查 'exe') 1) 则 得 'foreign'. 然
    若 有命令 则
        值 取 查询值 配 (根+'\\shell\\open\\command') ''.
        若 (值 其 查 'exists') 且 非 (_相同 值 (策略 其 命令 (配 其 查 'exe')) 1) 则 得 'foreign'. 然
    然
    得 'owned'.
法

算 _根们 配:
    得 [(_根状态 配 (策略 其 应用键) 真),(_根状态 配 (策略 其 类型键) 真),(_根状态 配 (策略 其 能力键) 假)].
法

算 配置状态 配:
    根们 取 _根们 配.
    若 根们[0] == 'foreign' 或 根们[1] == 'foreign' 或 根们[2] == 'foreign' 则 得 'otherowner'. 然
    项们 取 策略 其 计划 (配 其 查 'exe').
    相同数 取 0.
    有数 取 0.
    位 取 0.
    循 项们 其 量 次
        项 取 项们[位].
        值 取 查询值 配 项[0] 项[1].
        若 值 其 查 'exists' 则 有数 取 有数+1. 然
        若 _相同 值 项[2] 项[3] 则 相同数 取 相同数+1. 然
        位 取 位+1.
    环
    若 相同数 == 项们 其 量 则 得 'registered'. 然
    若 有数 == 0 且 根们[0] == 'missing' 且 根们[1] == 'missing' 且 根们[2] == 'missing' 则 得 'none'. 然
    得 'partial'.
法

算 查询状态:
    得 配置状态 (_生产配置()).
法

作 _写值 配, 键 为 句, 名 为 句, 文 为 句, 型 为 数:
    路存 取 密 其 UTF16 ((配 其 查 'prefix')+键).
    名存 取 密 其 UTF16 名.
    文存 取 密 其 UTF16 文.
    出 取 _句柄型 其 新建.
    柄 取 空.
    试
        码 取 ((_RegCreateKeyExW 其 调用 [_HKCU,路存,0,空,0,3,空,出,空]) 其 值) 其 数.
        _检查 码.
        柄 取 出 其 读 'h'.
        若 型 == 0 则
            码 取 ((_RegSetValueExW 其 调用 [柄,名存,0,0,空,0]) 其 值) 其 数.
        另
            码 取 ((_RegSetValueExW 其 调用 [柄,名存,0,1,文存,文存 其 大小]) 其 值) 其 数.
        然
        _检查 码.
    救 原因
        若 柄 != 空 则 _RegCloseKey 其 调用 [柄]. 然
        路存 其 关闭.
        名存 其 关闭.
        文存 其 关闭.
        出 其 关闭.
        卒 原因.
    终
    _RegCloseKey 其 调用 [柄].
    路存 其 关闭.
    名存 其 关闭.
    文存 其 关闭.
    出 其 关闭.
为

作 配置注册 配:
    根们 取 _根们 配.
    若 根们[0] == 'foreign' 或 根们[1] == 'foreign' 或 根们[2] == 'foreign' 则
        卒 '已有其他位置的程序或用户设置占用这些候选项；未覆盖。请先在原程序中移除注册。'.
    然
    项们 取 策略 其 计划 (配 其 查 'exe').
    # Complete conflict preflight before the first mutation.
    位 取 0.
    循 项们 其 量 次
        项 取 项们[位].
        值 取 查询值 配 项[0] 项[1].
        若 (值 其 查 'exists') 且 非 (_相同 值 项[2] 项[3]) 则
            卒 '打开方式候选项已被修改；为保护现有设置，本次没有覆盖。'.
        然
        位 取 位+1.
    环
    位 取 0.
    循 项们 其 量 次
        项 取 项们[位].
        _写值 配 项[0] 项[1] 项[2] 项[3].
        位 取 位+1.
    环
为

作 _删匹配 配, 项:
    柄 取 _打开 配 项[0] 3.
    若 柄 == 空 则 完. 然
    名存 取 密 其 UTF16 项[1].
    试
        值 取 _读柄 柄 项[1].
        若 _相同 值 项[2] 项[3] 则
            码 取 ((_RegDeleteValueW 其 调用 [柄,名存]) 其 值) 其 数.
            若 码 != 2 则 _检查 码. 然
        然
    救 原因
        名存 其 关闭.
        _RegCloseKey 其 调用 [柄].
        卒 原因.
    终
    名存 其 关闭.
    _RegCloseKey 其 调用 [柄].
为

作 _删空键 配, 键 为 句:
    柄 取 _打开 配 键 1.
    若 柄 == 空 则 完. 然
    子存 取 _数型 其 新建.
    值存 取 _数型 其 新建.
    码 取 ((_RegQueryInfoKeyW 其 调用 [柄,空,空,空,子存,空,空,值存,空,空,空,空]) 其 值) 其 数.
    空键 取 (子存 其 读 'n') 其 数 == 0 且 (值存 其 读 'n') 其 数 == 0.
    子存 其 关闭.
    值存 其 关闭.
    _RegCloseKey 其 调用 [柄].
    _检查 码.
    若 空键 则
        路存 取 密 其 UTF16 ((配 其 查 'prefix')+键).
        码 取 ((_RegDeleteKeyW 其 调用 [_HKCU,路存]) 其 值) 其 数.
        路存 其 关闭.
        若 码 != 2 且 码 != 3 则 _检查 码. 然
    然
为

算 _属于 键 为 句, 根 为 句:
    得 键 == 根 或 ((键 其 量) > (根 其 量) 且 键[:(根 其 量)+1] == 根+'\\').
法

作 配置注销 配:
    根们 取 _根们 配.
    若 根们[0] == 'foreign' 或 根们[1] == 'foreign' 或 根们[2] == 'foreign' 则
        卒 '候选项不属于当前程序位置；未删除其他程序或用户的设置。'.
    然
    项们 取 策略 其 计划 (配 其 查 'exe').
    位 取 项们 其 量.
    循 项们 其 量 次
        位 取 位-1.
        项 取 项们[位].
        允许 取 假.
        自有键 取 真.
        若 _属于 项[0] (策略 其 应用键) 则 允许 取 根们[0] == 'owned'.
        另 若 _属于 项[0] (策略 其 类型键) 则 允许 取 根们[1] == 'owned'.
        另 若 _属于 项[0] (策略 其 能力键) 则 允许 取 根们[2] == 'owned'.
        另
            自有键 取 假.
            若 项[0] == (策略 其 注册应用键) 则 允许 取 根们[2] == 'owned'.
            另 允许 取 根们[1] == 'owned'. 然
        然 然 然
        若 允许 则
            _删匹配 配 项.
            # Only prune the exact leaf after a zero-values/zero-children query.
            若 自有键 则 _删空键 配 项[0]. 然
        然
    环
    位 取 0.
    根键们 取 [(策略 其 应用键),(策略 其 类型键),(策略 其 能力键)].
    循 3 次
        若 根们[位] == 'owned' 则
            根 取 根键们[位].
            _删空键 配 (根+'\\shell\\open').
            _删空键 配 (根+'\\shell').
            _删空键 配 根.
        然
        位 取 位+1.
    环
为

作 注册:
    配置注册 (_生产配置()).
    _SHChangeNotify 其 调用 [134217728,0,空,空].
为

作 注销:
    配置注销 (_生产配置()).
    _SHChangeNotify 其 调用 [134217728,0,空,空].
为

作 打开设置 窗口:
    # Universal documented Settings URI; Windows presents the actual choice.
    动 取 密 其 UTF16 'open'.
    路 取 密 其 UTF16 'ms-settings:defaultapps'.
    果 取 _ShellExecuteW 其 调用 [窗口,动,路,空,空,1].
    动 其 关闭.
    路 其 关闭.
    若 (果 其 值) 其 数 <= 32 则 卒 '无法打开 Windows 默认应用设置，请从系统设置中手动选择。'. 然
为
