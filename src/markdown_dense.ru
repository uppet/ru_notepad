# Experimental ordinary->dense adapter. Existing _读块 has already decoded and
# closed its buffer: this deliberately makes ONE new UTF8 adaptation per eligible
# feed, including its allocation/copy/NUL, cleanup and ordinary boundary costs.
# The memory is neither a former _读块 pointer nor a cross-UI-yield borrowed view.
密 取 外言 '如:密'.
策 取 外言 'markdown_policy.ru'.
算 喂入 态 文 为 句 结束 为 事实:
    # Preserve the scalar-limit error before state access and finished ordering.
    若 文 其 量 > 1024 则 得 策 其 喂入 态 文 结束. 然
    若 态[2] 则 得 策 其 喂入 态 文 结束. 然
    # This native-only adapter accepts the _读块 input contract (no embedded NUL).
    # The unchanged ordinary pure entry remains available for all other inputs.
    若 态[6] == '' 或 态[8] != '' 或 (文 其 含 '>') 或 非 ((文 其 含 '\r') 或 (文 其 含 '\n')) 则
        得 策 其 喂入 态 文 结束.
    然
    存 取 密 其 UTF8 文.
    试
        果 取 策 其 喂入视图 态 文 结束 存 ((存 其 大小)-1).
    救 原因
        存 其 关闭.
        卒 原因.
    终
    存 其 关闭.
    得 果.
法
