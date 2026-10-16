# Pure Ru language-selection policy, shared by production and portable tests.
# Ru's builtin 含 is string containment, not array membership. Compare whole
# string elements explicitly so suffixes and CLI flags never match substrings.
算 含词 列 为 句 阵, 词 为 句:
    位 取 0.
    循 列 其 量 次
        若 列[位] == 词 则 得 真. 然
        位 取 位+1.
    环
    得 假.
法
算 名称 语言 为 句:
    若 语言 == 'ru' 则 得 'Ru / 如言'. 然
    若 语言 == 'cpp' 则 得 'C / C++'. 然
    若 语言 == 'json' 则 得 'JSON'. 然
    得 'Plain text'.
法
算 识别 路 为 句:
    位 取 路 其 量.
    后缀 取 ''.
    循
        若 位 <= 0 则 得 'plain'. 然
        位 取 位-1.
        字 取 路[位].
        若 字 == '/' 或 字 == '\\' 则 得 'plain'. 然
        若 字 == '.' 则 破. 然
        后缀 取 字+后缀.
        若 (后缀 其 量) > 4 则 得 'plain'. 然
    环
    小写 取 ''.
    大字 取 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.
    小字 取 'abcdefghijklmnopqrstuvwxyz'.
    位 取 0.
    循 后缀 其 量 次
        字 取 后缀[位].
        字位 取 0.
        循 26 次
            若 字 == 大字[字位] 则
                字 取 小字[字位].
                破.
            然
            字位 取 字位+1.
        环
        小写 取 小写+字.
        位 取 位+1.
    环
    若 小写 == 'ru' 则 得 'ru'. 然
    若 小写 == 'json' 则 得 'json'. 然
    若 含词 ['c','h','cc','hh','cpp','hpp','cxx','hxx','c++','h++','inl'] 小写 则 得 'cpp'. 然
    得 'plain'.
法
