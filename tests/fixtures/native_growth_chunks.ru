# Real native UTF8 allocation, matching syntax_native's 1 MiB x 32 growth.
# This verifies buffer limits on both runtimes, not Scintilla's Windows undo.
密 取 外言 '如:密'.
填文 取 'x'.
循 20 次 填文 取 填文+填文. 环
累计 取 0.
循 32 次
    存 取 密 其 UTF8 填文.
    若 (存 其 大小) != 1048577 则 卒 'FAIL: chunk allocation size includes terminator'. 然
    若 (存 其 解UTF8) != 填文 则 卒 'FAIL: chunk payload changed'. 然
    累计 取 累计+((存 其 大小)-1).
    存 其 关闭.
    显 'PASS: real 1 MiB UTF8 chunk round-trips and closes'.
环
若 累计 != 33554432 则 卒 'FAIL: total real payload is not 32 MiB'. 然
显 'PASS: 32 chunks contain exactly 33554432 payload bytes'.
显 'TOTAL PASS: 33'.
