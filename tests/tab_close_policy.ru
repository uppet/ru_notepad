策 取 外言 '../src/tab_close_policy.ru'.
计数 取 [0].
作 确认 条件 为 事实, 文 为 句:
    若 非 条件 则 卒 'FAIL: '+文. 然
    计数[0] 取 计数[0]+1.
    显 'PASS: '+文.
为
算 同项 甲 为 阵, 乙 为 阵:
    若 (甲 其 量) != (乙 其 量) 则 得 假. 然
    位 取 0.
    循 甲 其 量 次
        若 甲[位] != 乙[位] 则 得 假. 然
        位 取 位+1.
    环
    得 真.
法
算 核 动作 为 句, 点击 为 数, 预期 为 阵:
    实际 取 策 其 目标 4 点击 动作 ([假,真,假,真]).
    确认 (同项 实际 预期) 动作.
    得 空.
法
核 'current' 1 ([1]).
核 'all' 1 ([3,2,1,0]).
核 'others' 1 ([3,2,0]).
核 'left' 2 ([1,0]).
核 'right' 1 ([3,2]).
核 'saved' 1 ([2,0]).
核 'left' 0 ([]).
核 'right' 3 ([]).
核 'unknown' 1 ([]).
核 'current' (-1) ([]).
核 'current' 4 ([]).
确认 (同项 (策 其 目标 0 0 'current' ([])) ([])) 'empty'.
确认 (同项 (策 其 目标 2 0 'current' ([假])) ([])) 'mismatched snapshot'.
确认 (同项 (策 其 目标 1 0 'others' ([真])) ([])) 'only tab others disabled'.
确认 (同项 (策 其 目标 2 0 'saved' ([真,真])) ([])) 'dirty documents excluded'.
确认 (同项 (策 其 目标 2 0 'saved' ([假,假])) ([1,0])) 'all clean included'.
显 'TOTAL PASS: '+(计数[0] 为 句).
