# Portable execution of the exact production predicate, using a strict receiver.
# This does not emulate Windows APIs or claim native scalar execution on Linux.
标志 取 外言 '../src/file_codec_flags.ru'.
调用们 取 {'0':0,'4':0,'10':0,'14':0}.
次数 取 [0].
作 确认 条件 为 事实 名称 为 句:
    若 非 条件 则 卒 'FAIL: ' + 名称. 然
    次数[0] 取 次数[0] + 1.
    显 'PASS: ' + 名称.
为
形 位段替身:
    值 为 数.
    算 位段 起 为 数 宽 为 数:
        # Native 位段 also rejects facts as integer input. These annotations
        # ensure the original ungrouped expression fails before method entry.
        若 宽 != 1 则 卒 'Expected exactly one numeric bit'. 然
        若 起 != 0 且 起 != 4 且 起 != 10 且 起 != 14 则 卒 'Unexpected attribute bit'. 然
        调用们 其 增 (起 为 句) (调用们[起 为 句] + 1).
        因子 取 1.
        循 起 次 因子 取 因子 * 2. 环
        得 ((其 值 % (因子 * 2)) - (其 值 % 因子)) / 因子.
    法
象
# Complete truth table: readonly bit0, directory bit4, reparse bit10, EFS bit14.
样本们 取 [
    [0,假,假,假,假], [1,真,假,假,假],
    [16,假,真,假,假], [17,真,真,假,假],
    [1024,假,假,真,假], [1025,真,假,真,假],
    [1040,假,真,真,假], [1041,真,真,真,假],
    [16384,假,假,假,真], [16385,真,假,假,真],
    [16400,假,真,假,真], [16401,真,真,假,真],
    [17408,假,假,真,真], [17409,真,假,真,真],
    [17424,假,真,真,真], [17425,真,真,真,真],
    [128,假,假,假,假], [2147483648,假,假,假,假],
    [4294967295,真,真,真,真]
].
位们 取 [0,4,10,14].
样位 取 0.
循 样本们 其 量 次
    样本 取 样本们[样位].
    属性 取 新 位段替身 值:样本[0].
    位 取 0.
    循 位们 其 量 次
        结果 取 标志 其 已设 属性 位们[位].
        确认 (结果 == 样本[位 + 1]) ('mask=' + (样本[0] 为 句) + ' bit=' + (位们[位] 为 句)).
        位 取 位 + 1.
    环
    样位 取 样位 + 1.
环
位 取 0.
循 位们 其 量 次
    确认 (调用们[位们[位] 为 句] == 样本们 其 量) ('numeric width=1 and exact calls for bit=' + (位们[位] 为 句)).
    位 取 位 + 1.
环
显 'TOTAL PASS: ' + (次数[0] 为 句).
