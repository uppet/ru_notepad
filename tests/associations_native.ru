# Actual Win32 registry fixture, scoped to one newly created synthetic HKCU key.
# Real Applications, RegisteredApplications, FileExts and defaults are untouched.
密 取 外言 '如:密'.
联 取 外言 '../src/associations.ru'.
策 取 外言 '../src/associations_policy.ru'.
_PTR 取 密 其 指针.
_U32 取 密 其 u32.
_I32 取 密 其 i32.
_内核 取 密 其 系统库 'kernel32.dll'.
_注册 取 密 其 系统库 'advapi32.dll'.
_GetCurrentProcessId 取 _内核 其 绑定 'GetCurrentProcessId' (密 其 签名 _U32 ([]) 'win64').
_GetTickCount64 取 _内核 其 绑定 'GetTickCount64' (密 其 签名 (密 其 uintptr) ([]) 'win64').
_RegDeleteTreeW 取 _注册 其 绑定 'RegDeleteTreeW' (密 其 签名 _I32 ([_PTR,_PTR]) 'win64').
_RegSetValueExW 取 _注册 其 绑定 'RegSetValueExW' (密 其 签名 _I32 ([_PTR,_PTR,_U32,_U32,_PTR,_U32]) 'win64').
_RegCloseKey 取 _注册 其 绑定 'RegCloseKey' (密 其 签名 _I32 ([_PTR]) 'win64').
_坏型 取 密 其 结构 [['surrogate',(密 其 u16)],['zero',(密 其 u16)]].
次数 取 [0].
作 确认 条件 为 事实, 文 为 句:
    若 非 条件 则 卒 'FAIL: '+文. 然
    次数[0] 取 次数[0]+1.
    显 'PASS: '+文.
为
作 应失败 工作 为 算, 文 为 句:
    失败 取 [假].
    试 工作(). 救 原因 失败[0] 取 真. 终
    确认 失败[0] 文.
为
算 文等 配, 键 为 句, 名 为 句, 文 为 句:
    值 取 联 其 查询值 配 键 名.
    得 (值 其 查 'exists') 且 (值 其 查 'valid') 且 (值 其 查 'type') == 1 且 (值 其 查 'text') == 文.
法
算 已删 配, 键 为 句, 名 为 句:
    值 取 联 其 查询值 配 键 名.
    得 非 (值 其 查 'exists').
法
作 写坏值 配, 单元 为 数:
    柄 取 联 其 _打开 配 (策 其 应用键) 3.
    名 取 密 其 UTF16 'RuNotepadOwner'.
    存 取 _坏型 其 新建.
    存 其 写 'surrogate' 单元.
    果 取 _RegSetValueExW 其 调用 [柄,名,0,1,存,存 其 大小].
    存 其 关闭.
    名 其 关闭.
    _RegCloseKey 其 调用 [柄].
    若 (果 其 值) 其 数 != 0 则 卒 'malformed registry fixture write failed'. 然
为
作 清理 前缀 为 句:
    策 其 测试前缀 前缀.
    名 取 密 其 UTF16 前缀.
    果 取 _RegDeleteTreeW 其 调用 [(_PTR 其 值 '18446744071562067969'),名].
    名 其 关闭.
    码 取 (果 其 值) 其 数.
    若 码 != 0 且 码 != 2 则 卒 'isolated registry fixture cleanup failed'. 然
为
作 检验 配, 别配, 执行 为 句:
    确认 ((联 其 配置状态 配) == 'none') 'new isolated prefix has no candidate registration'.
    确认 ((联 其 程序路径()) 其 量 > 3) 'production executable discovery returns current absolute module path'.
    # Synthetic defaults are tripwires; the production plan must never touch them.
    默认键 取 'Software\\Classes\\.txt'.
    用户选择 取 'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\FileExts\\.txt\\UserChoice'.
    开启键 取 'Software\\Classes\\.txt\\OpenWithProgids'.
    联 其 _写值 配 默认键 '' 'Foreign.Text' 1.
    联 其 _写值 配 用户选择 'ProgId' 'Foreign.Text' 1.
    联 其 _写值 配 用户选择 'Hash' 'synthetic-do-not-touch' 1.
    联 其 _写值 配 开启键 'Foreign.Text' '' 0.
    联 其 配置注册 配.
    确认 ((联 其 配置状态 配) == 'registered') 'all candidate values register under isolated HKCU prefix'.
    项们 取 策 其 计划 执行.
    全同 取 真.
    位 取 0.
    循 项们 其 量 次
        项 取 项们[位].
        值 取 联 其 查询值 配 项[0] 项[1].
        若 非 (联 其 _相同 值 项[2] 项[3]) 则 全同 取 假. 然
        位 取 位+1.
    环
    确认 全同 'all 56 exact typed values match the production registration plan'.
    确认 (文等 配 ((策 其 应用键)+'\\shell\\open\\command') '' ('"'+执行+'" "%1"')) 'actual registry preserves quoted Unicode executable and percent-one'.
    确认 (文等 配 默认键 '' 'Foreign.Text') 'extension default remains unchanged by registration'.
    确认 ((文等 配 用户选择 'ProgId' 'Foreign.Text') 且 (文等 配 用户选择 'Hash' 'synthetic-do-not-touch')) 'UserChoice ProgId and hash remain unchanged by registration'.
    确认 (非 (已删 配 开启键 'Foreign.Text')) 'foreign OpenWithProgids candidate survives registration'.
    联 其 配置注册 配.
    确认 ((联 其 配置状态 配) == 'registered') 'same-executable registration is idempotent'.
    确认 ((联 其 配置状态 别配) == 'otherowner') 'second portable copy detects ownership conflict'.
    应失败 (算: 联 其 配置注册 别配. 得 空. 法) 'second portable copy cannot overwrite owner'.
    应失败 (算: 联 其 配置注销 别配. 得 空. 法) 'second portable copy cannot unregister owner'.
    确认 ((联 其 配置状态 配) == 'registered') 'rejected second-copy changes preserve full original registration'.
    联 其 _写值 配 (策 其 应用键) 'FriendlyAppName' 'User custom label' 1.
    确认 ((联 其 配置状态 配) == 'partial') 'customized non-owner value is reported as partial'.
    应失败 (算: 联 其 配置注册 配. 得 空. 法) 'registration preflights every value before overwriting anything'.
    确认 (文等 配 (策 其 应用键) 'FriendlyAppName' 'User custom label') 'customized friendly name survives rejected registration'.
    确认 (文等 配 ((策 其 类型键)+'\\shell\\open\\command') '' (策 其 命令 执行)) 'preflight conflict preserves existing command'.
    联 其 _写值 配 (策 其 应用键) 'FriendlyAppName' 'ru_notepad' 1.
    写坏值 配 55296.
    值 取 联 其 查询值 配 (策 其 应用键) 'RuNotepadOwner'.
    确认 (非 (值 其 查 'valid')) 'unpaired high surrogate REG_SZ is invalid without decoder abort'.
    确认 ((联 其 配置状态 配) == 'otherowner') 'malformed high surrogate owner is treated as foreign'.
    应失败 (算: 联 其 配置注册 配. 得 空. 法) 'invalid owner cannot be overwritten by registration'.
    应失败 (算: 联 其 配置注销 配. 得 空. 法) 'invalid owner cannot authorize unregister'.
    写坏值 配 56320.
    值 取 联 其 查询值 配 (策 其 应用键) 'RuNotepadOwner'.
    确认 (非 (值 其 查 'valid')) 'unpaired low surrogate REG_SZ is invalid without decoder abort'.
    确认 ((联 其 配置状态 配) == 'otherowner') 'malformed low surrogate owner is treated as foreign'.
    联 其 _写值 配 (策 其 应用键) 'RuNotepadOwner' 执行 1.
    联 其 配置注销 配.
    确认 ((联 其 配置状态 配) == 'none') 'normal unregister removes all owned candidate values'.
    联 其 配置注册 配.
    确认 ((联 其 配置状态 配) == 'registered') 'registration works again after clean unregister'.
    子键 取 (策 其 应用键)+'\\ForeignChild'.
    联 其 _写值 配 子键 'Keep' 'foreign child data' 1.
    联 其 _写值 配 (策 其 应用键) 'FriendlyAppName' 'User custom label' 1.
    联 其 配置注销 配.
    确认 (已删 配 ((策 其 应用键)+'\\shell\\open\\command') '') 'unregister removes matching application command'.
    确认 (已删 配 ((策 其 类型键)+'\\shell\\open\\command') '') 'unregister removes matching ProgID command'.
    确认 (已删 配 (策 其 注册应用键) 'ru_notepad') 'unregister removes matching RegisteredApplications value'.
    确认 (已删 配 开启键 (策 其 程序标识)) 'unregister removes only its own OpenWithProgids candidate'.
    确认 (非 (已删 配 开启键 'Foreign.Text')) 'unregister preserves other OpenWithProgids candidates'.
    确认 (文等 配 默认键 '' 'Foreign.Text') 'unregister preserves extension default'.
    确认 ((文等 配 用户选择 'ProgId' 'Foreign.Text') 且 (文等 配 用户选择 'Hash' 'synthetic-do-not-touch')) 'unregister preserves UserChoice and hash'.
    确认 (文等 配 子键 'Keep' 'foreign child data') 'unregister preserves foreign child keys and values'.
    确认 (文等 配 (策 其 应用键) 'FriendlyAppName' 'User custom label') 'unregister preserves user-modified value'.
    确认 (已删 配 (策 其 应用键) 'RuNotepadOwner') 'unregister removes only the matching current-executable owner marker'.
为
算 元初 参数 为 句 阵:
    号 取 ((_GetCurrentProcessId 其 调用 []) 其 值) 其 句.
    时 取 ((_GetTickCount64 其 调用 []) 其 值) 其 句.
    前缀 取 'Software\\RuNotepad.Tests\\native-'+号+'-'+时.
    执行 取 'C:\\synthetic editor 中文😀\\ru_notepad.exe'.
    配 取 联 其 测试配置 前缀 执行.
    别配 取 联 其 测试配置 前缀 'D:\\other portable copy\\ru_notepad.exe'.
    若 联 其 _有键 配 '' 则 卒 'fixture prefix unexpectedly exists; not touching it'. 然
    试 检验 配 别配 执行. 救 原因 清理 前缀. 卒 原因. 终
    清理 前缀.
    确认 (非 (联 其 _有键 配 '')) 'exact isolated registry subtree is cleaned after tests'.
    显 'TOTAL PASS: '+(次数[0] 为 句).
    得 0.
法
