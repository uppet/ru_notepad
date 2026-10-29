# Independent HKCU DWORD. Saved changes apply to subsequent launches only.
密 取 外言 '如:密'.
策 取 外言 'single_instance_policy.ru'.
P 取 密 其 指针. U 取 密 其 u32. I 取 密 其 i32.
A 取 密 其 系统库 'advapi32.dll'.
_HKCU 取 P 其 值 '18446744071562067969'.
_数 取 密 其 结构 [['n',U]].
_柄 取 密 其 结构 [['h',P]].
_Get 取 A 其 绑定 'RegGetValueW' (密 其 签名 I ([P,P,P,U,P,P,P]) 'win64').
_Create 取 A 其 绑定 'RegCreateKeyExW' (密 其 签名 I ([P,P,U,P,U,U,P,P,P]) 'win64').
_Set 取 A 其 绑定 'RegSetValueExW' (密 其 签名 I ([P,P,U,U,P,U]) 'win64').
_Close 取 A 其 绑定 'RegCloseKey' (密 其 签名 I ([P]) 'win64').
_路径 取 'Software\\ru_notepad\\Preferences'.
K 取 密 其 系统库 'kernel32.dll'.
_GetEnvironment 取 K 其 绑定 'GetEnvironmentVariableW' (密 其 签名 U ([P,P,U]) 'win64').
_ValidateWide 取 K 其 绑定 'WideCharToMultiByte' (密 其 签名 I ([U,U,P,I,P,I,P,P]) 'win64').
算 测试路径 后缀 为 句:
    若 后缀 == '' 或 后缀 其 量 > 64 则 卒 'Invalid single-instance settings test suffix.'. 然
    位 取 0.
    循 后缀 其 量 次
        若 非 ('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' 其 含 后缀[位]) 则 卒 'Invalid single-instance settings test suffix.'. 然
        位 取 位+1.
    环
    得 'Software\\ru_notepad\\SingleInstanceTests\\'+后缀.
法
# Test routing is opt-in, bounded and isolated from real preferences/endpoints.
算 命名空间:
    名 取 密 其 UTF16 'RU_NOTEPAD_INSTANCE_TEST_KEY'. 存 取 密 其 缓冲 132.
    果 取 _GetEnvironment 其 调用 [名,存,66]. 名 其 关闭.
    长 取 (果 其 值) 其 数.
    若 长 == 0 且 果 其 错误码 == 203 则 存 其 关闭. 得 ''. 然
    若 长 < 1 或 长 > 64 则 存 其 关闭. 卒 'Invalid single-instance test environment.'. 然
    校 取 _ValidateWide 其 调用 [65001,128,存,长,空,0,空,空].
    若 (校 其 值) 其 为空 则 存 其 关闭. 卒 'Invalid single-instance test UTF16.'. 然
    文 取 存 其 解UTF16. 存 其 关闭.
    测试路径 文. 得 文.
法
算 _有效路径:
    后缀 取 命名空间.
    若 后缀 == '' 则 得 _路径. 然
    得 测试路径 后缀.
法
算 _读取 路 为 句:
    路存 取 密 其 UTF16 路. 名存 取 密 其 UTF16 'SingleInstance'.
    型 取 _数 其 新建. 长 取 _数 其 新建. 值 取 _数 其 新建.
    长 其 写 'n' 4. 型 其 写 'n' 0. 值 其 写 'n' 0.
    码 取 ((_Get 其 调用 [_HKCU,路存,名存,16,型,值,长]) 其 值) 其 数.
    果 取 策 其 设置结果 码 ((型 其 读 'n') 其 数) ((长 其 读 'n') 其 数) ((值 其 读 'n') 其 数).
    路存 其 关闭. 名存 其 关闭. 型 其 关闭. 长 其 关闭. 值 其 关闭.
    得 果.
法
算 _写入 路 为 句 开 为 事实:
    路存 取 密 其 UTF16 路. 名存 取 密 其 UTF16 'SingleInstance'.
    值 取 _数 其 新建. 柄存 取 _柄 其 新建.
    数 取 0. 若 开 则 数 取 1. 然
    值 其 写 'n' 数.
    码 取 ((_Create 其 调用 [_HKCU,路存,0,空,0,2,空,柄存,空]) 其 值) 其 数.
    若 码 == 0 则
        柄 取 柄存 其 读 'h'.
        码 取 ((_Set 其 调用 [柄,名存,0,4,值,4]) 其 值) 其 数.
        关码 取 ((_Close 其 调用 [柄]) 其 值) 其 数.
        若 码 == 0 则 码 取 关码. 然
    然
    路存 其 关闭. 名存 其 关闭. 值 其 关闭. 柄存 其 关闭. 得 码.
法
算 载入偏好:
    试 得 _读取 (_有效路径). 救 原因 得 {'enabled':假,'error':87}. 终
法
算 保存偏好 开 为 事实:
    试 得 _写入 (_有效路径) 开. 救 原因 得 87. 终
法
算 测试载入 后缀 为 句:
    得 _读取 (测试路径 后缀).
法
算 测试保存 后缀 为 句 开 为 事实:
    得 _写入 (测试路径 后缀) 开.
法
