# Experimental immutable UTF8 adapter; the ordinary sentence owns its bytes.
# NativeMemory and its stricter callback/reentry contract are not involved.
_密核 取 外言 'markdown_ascii_kernel.ru'.
策 取 外言 'markdown_policy.ru'.
算 喂入 态 文 为 句 结束 为 事实:
    # Preserve the scalar-limit error before state access and finished ordering.
    若 文 其 量 > 1024 则 得 策 其 喂入 态 文 结束. 然
    若 态[2] 则 得 策 其 喂入 态 文 结束. 然
    # This native-only adapter accepts the _读块 input contract (no embedded NUL).
    # The unchanged ordinary pure entry remains available for all other inputs.
    若 文 == '' 则 得 策 其 喂入 态 文 结束. 然
    # A fresh first chunk uses the ordinary entry until the full bounded prefix
    # exists; later single-line feeds can use the exact-state uniform-run path.
    围栏 取 态[6] != '' 且 态[8] == '' 且 非 (文 其 含 '>') 且 ((文 其 含 '\r') 或 (文 其 含 '\n')).
    长行 取 非 态[10] 且 (态[11] 其 量) == 32.
    若 非 围栏 且 非 长行 则 得 策 其 喂入 态 文 结束. 然
    # Explicit immutable UTF8 borrowing; no native address, allocation/copy or
    # borrow survives this synchronous call, callback boundary or UI yield.
    字节末 取 _密核 其 字节量 文.
    得 策 其 喂入视图 态 文 结束 文 字节末.
法
