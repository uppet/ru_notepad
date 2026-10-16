参 取 外言 '../src/ui_arguments.ru'.
次数 取 [0].
作 确认 条件 为 事实, 文 为 句:
    若 非 条件 则 卒 ('FAIL: '+文). 然
    次数[0] 取 次数[0]+1.
    显 'PASS: '+文.
为
状态 取 {'window':101,'find':202,'editor':303,'className':'Class','instance':404}.
菜单 取 505.
# This calls the exact helper used immediately before SetMenu in the GUI.
参数 取 参 其 菜单参数 状态 菜单.
确认 ((参数 其 量) == 2) 'SetMenu receives two arguments'.
确认 (参数[0] == 101) 'SetMenu first argument is main HWND'.
确认 (参数[1] == 505) 'SetMenu second argument is HMENU'.
参数 取 参 其 窗口二参 状态 'reason'.
确认 ((参数 其 量) == 2) 'shutdown reason receives two arguments'.
确认 (参数[0] == 101) 'shutdown reason receives HWND'.
确认 (参数[1] == 'reason') 'shutdown reason receives buffer'.
参数 取 参 其 窗口二参 状态 606.
确认 ((参数 其 量) == 2) 'GetClientRect receives two arguments'.
确认 (参数[0] == 101) 'GetClientRect receives HWND'.
确认 (参数[1] == 606) 'GetClientRect receives output rectangle'.
参数 取 参 其 控件二参 状态 'find' 5.
确认 ((参数 其 量) == 2) 'search ShowWindow receives two arguments'.
确认 (参数[0] == 202) 'search ShowWindow selects correct control'.
确认 (参数[1] == 5) 'search ShowWindow preserves show mode'.
参数 取 参 其 控件二参 状态 'editor' 0.
确认 ((参数 其 量) == 2) 'old-tab ShowWindow receives two arguments'.
确认 (参数[0] == 303) 'old-tab ShowWindow selects correct editor'.
确认 (参数[1] == 0) 'old-tab ShowWindow preserves hide mode'.
参数 取 参 其 注销类参数 状态.
确认 ((参数 其 量) == 2) 'UnregisterClassW receives two arguments'.
确认 (参数[0] == 'Class') 'UnregisterClassW preserves class name'.
确认 (参数[1] == 404) 'UnregisterClassW preserves instance'.
显示状态 取 状态 其 查 'window'.
确认 (显示状态 == 101) 'argument construction does not modify application state'.
显 'TOTAL PASS: '+(次数[0] 为 句).
