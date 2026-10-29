# Windows-only isolated HKCU roundtrip; never touches Preferences.
模 取 外言 '../src/single_instance_settings.ru'.
密 取 外言 '如:密'.
P 取 密 其 指针. U 取 密 其 u32. I 取 密 其 i32.
K 取 密 其 系统库 'kernel32.dll'. A 取 密 其 系统库 'advapi32.dll'.
PID 取 K 其 绑定 'GetCurrentProcessId' (密 其 签名 U ([]) 'win64').
删 取 A 其 绑定 'RegDeleteTreeW' (密 其 签名 I ([P,P]) 'win64').
_HKCU 取 P 其 值 '18446744071562067969'.
次数 取 [0].
作 确认 条件 为 事实 文 为 句:
    若 非 条件 则 卒 ('FAIL: '+文). 然
    次数[0] 取 次数[0]+1. 显 'PASS: '+文.
为
后缀 取 'native-'+((((PID 其 调用 []) 其 值) 其 数) 为 句).
路 取 密 其 UTF16 (模 其 测试路径 后缀).
删 其 调用 [_HKCU,路].
试
    设 取 模 其 测试载入 后缀.
    确认 (设['enabled'] 且 设['error'] == 0) 'missing test preference defaults on'.
    确认 ((模 其 测试保存 后缀 假) == 0) 'persist isolated off DWORD'.
    设 取 模 其 测试载入 后缀.
    确认 (非 设['enabled'] 且 设['error'] == 0) 'read isolated off DWORD'.
    确认 ((模 其 测试保存 后缀 真) == 0) 'persist isolated on DWORD'.
    设 取 模 其 测试载入 后缀.
    确认 (设['enabled'] 且 设['error'] == 0) 'read isolated on DWORD'.
    坏们 取 ['','../Preferences','a\\b','a/b','a b']. 位 取 0.
    循 坏们 其 量 次
        拒 取 [假]. 试 模 其 测试路径 坏们[位]. 救 原因 拒[0] 取 真. 终
        确认 拒[0] 'invalid isolated namespace rejected'. 位 取 位+1.
    环
救 原因
    删 其 调用 [_HKCU,路]. 路 其 关闭. 卒 原因.
终
码 取 ((删 其 调用 [_HKCU,路]) 其 值) 其 数. 路 其 关闭.
确认 (码 == 0) 'isolated test key removed'.
显 'TOTAL PASS: '+(次数[0] 为 句).
