# Compiled by stage3 LLVM and linked through the exact production GUI wrapper.
算 元初 参数 为 句 阵:
    显 'BOOTSTRAP_ARGV_ENTERED'.
    期望 取 ['', 'space value', 'quote"slash\\tail\\', '汉😀'].
    若 (参数 其 量) != (期望 其 量) 则 卒 'FAIL: argv count'. 然
    位 取 0.
    循 期望 其 量 次
        若 参数[位] != 期望[位] 则 卒 'FAIL: UTF16 UTF8 argv roundtrip'. 然
        位 取 位+1.
    环
    显 'BOOTSTRAP_ARGV_PASS'.
    得 0.
法
