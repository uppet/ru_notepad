# Pure Ru language-selection policy, shared by production and portable tests.
# Ru's builtin 含 is string containment, not array membership. Compare whole
# string elements explicitly so suffixes and CLI flags never match substrings.
本地 取 外言 'i18n.ru'.
算 含词 列 为 句 阵, 词 为 句:
    位 取 0.
    循 列 其 量 次
        若 列[位] == 词 则 得 真. 然
        位 取 位+1.
    环
    得 假.
法
# Catalog is generated from the versioned, reviewed language configuration.
目 取 外言 'syntax_catalog.ru'.
算 名称 语言 为 句:
    若 语言 == 'plain' 或 非 (目 其 有语言 语言) 则 得 本地 其 文本 'syntax.plain'. 然
    得 目 其 名称 语言.
法
算 小写 文 为 句:
    果 取 ''.
    大字 取 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.
    小字 取 'abcdefghijklmnopqrstuvwxyz'.
    位 取 0.
    循 文 其 量 次
        字 取 文[位].
        字位 取 0.
        循 26 次
            若 字 == 大字[字位] 则 字 取 小字[字位]. 破. 然
            字位 取 字位+1.
        环
        果 取 果+字.
        位 取 位+1.
    环
    得 果.
法
算 识别 路 为 句:
    # Only the basename is inspected; dots in directories never select a lexer.
    位 取 路 其 量.
    名 取 ''.
    循
        若 位 <= 0 则 破. 然
        位 取 位-1.
        字 取 路[位].
        若 字 == '/' 或 字 == '\\' 则 破. 然
        名 取 字+名.
    环
    名 取 小写 名.
    特 取 目 其 文件名 名.
    若 特 != '' 则 得 特. 然
    位 取 名 其 量.
    后缀 取 ''.
    循
        若 位 <= 0 则 得 'plain'. 然
        位 取 位-1.
        字 取 名[位].
        若 字 == '.' 则 破. 然
        后缀 取 字+后缀.
    环
    得 目 其 后缀 后缀.
法
算 语言们:
    得 目 其 语言们.
法
算 命令 语言 为 句:
    若 语言 == 'plain' 则 得 701. 然
    若 语言 == 'cpp' 则 得 702. 然
    若 语言 == 'json' 则 得 703. 然
    若 语言 == 'ru' 则 得 704. 然
    若 语言 == 'markdown' 则 得 705. 然
    列 取 目 其 语言们.
    位 取 0.
    循 列 其 量 次
        若 列[位] == 语言 则 得 2000+位. 然
        位 取 位+1.
    环
    得 0.
法
算 从命令 号 为 数:
    若 号 == 701 则 得 'plain'. 然
    若 号 == 702 则 得 'cpp'. 然
    若 号 == 703 则 得 'json'. 然
    若 号 == 704 则 得 'ru'. 然
    若 号 == 705 则 得 'markdown'. 然
    列 取 目 其 语言们.
    位 取 号-2000.
    若 位 < 0 或 位 >= (列 其 量) 或 位%1 != 0 则 得 ''. 然
    得 列[位].
法

# SCI_GETFOLDLEVEL is converted to an ordinary Ru number by the bridge.
# 位段 belongs to native integer objects, not numbers. Test bit 13 without
# interpreting packed upper next-line levels as header flags. Normalize remainder
# explicitly so signed int32 values agree in interpreter and native-C backends.
算 是折头 层 为 数:
    若 层 % 1 != 0 或 层 < -2147483648 或 层 > 4294967295 则 得 假. 然
    得 ((层 % 16384)+16384)%16384 >= 8192.
法
