# Ru-owned close selection. N++ behavior reference, no copied implementation.
算 目标 数量 为 数, 点击 为 数, 动作 为 句, 已改 为 阵:
    得们 取 [].
    若 数量 < 1 或 点击 < 0 或 点击 >= 数量 或 (已改 其 量) != 数量 则 得 得们. 然
    位 取 数量-1.
    循 数量 次
        选 取 假.
        若 动作 == 'all' 则 选 取 真. 然
        若 动作 == 'current' 则 选 取 位 == 点击. 然
        若 动作 == 'others' 则 选 取 位 != 点击. 然
        若 动作 == 'left' 则 选 取 位 < 点击. 然
        若 动作 == 'right' 则 选 取 位 > 点击. 然
        若 动作 == 'saved' 则 选 取 非 已改[位]. 然
        若 选 则 得们 其 增 位. 然
        位 取 位-1.
    环
    得 得们.
法
