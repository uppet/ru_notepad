# Ordinary Ru source is the only algorithm definition. Explicit build manifest
# may lower this function's AST to typed readonly-u8 IR; no handwritten C kernel.
# Without opt-in this is an ordinary number-array oracle, not NativeMemory access.
算 ASCII段 字节 始 终:
    位 取 始.
    循 (终-始) 次
        值 取 字节[位].
        若 值 >= 128 或 值 == 13 或 值 == 10 或 值 == 62 则 破. 然
        位 取 位+1.
    环
    得 位-始.
法
