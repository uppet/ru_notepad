# Small actual-core fixture for stage3 LLVM acceptance. No generated substitute.
核 取 外言 '../src/directory_text.ru'.
次数 取 [0].
作 确认 条件 名:
    若 非 条件 则 卒 ('FAIL: '+名). 然.
    次数[0] 取 次数[0]+1. 显 'PASS: '+名.
为.
算 元 长:
    得 {'generation':3,'fileSequence':5,'path':'local.txt','rawSize':长,'identity':'file-id','stamp':'stamp'}.
法.
算 测试 名 字节们 词 额 预算 有效 期态 期因 期编 期数 始 末 行 列:
    态 取 核 其 新建 (核 其 编译 词) (元 (字节们 其 量)) 额.
    位 取 0. 合规 取 真. 封 取 假.
    循 10000 次
        若 态['status'] == 'need-input' 则
            若 位 < (字节们 其 量) 则
                核 其 喂入 态 ([字节们[位]]) 位. 位 取 位+1.
            另
                若 封 则 卒 'FAIL: repeated EOF'. 然.
                封 取 真. 核 其 结束 态 有效.
            然.
        然.
        若 态['status'] == 'running' 则
            核 其 步进 态 预算.
            若 态['lastWork'] < 1 或 态['lastWork'] > 预算 则 合规 取 假. 然.
        然.
        若 态['status'] != 'complete' 且 (态['rows'] 其 量) != 0 则 合规 取 假. 然.
        若 态['rawConsumed'] > 态['rawReceived'] 或 态['retainedCount'] > 额 则 合规 取 假. 然.
        若 态['status'] != 'running' 且 态['status'] != 'need-input' 则 破. 然.
    环.
    确认 (态['status'] == 期态 且 态['reason'] == 期因) (名+' status').
    确认 合规 (名+' microsteps-and-isolation').
    确认 ((态['rows'] 其 量) == 期数 且 态['retainedCount'] == 期数) (名+' rows').
    确认 (期编 == '' 或 态['encoding'] == 期编) (名+' encoding').
    若 期数 > 0 则
        果 取 态['rows'][期数-1].
        确认 (果['startUtf8'] == 始 且 果['endUtf8'] == 末 且 果['line'] == 行 且 果['column'] == 列 且 (果['previewScalars'] 其 量) <= 96) (名+' coordinate-preview').
    另
        确认 ((态['rows'] 其 量) == 0) (名+' no-leak').
    然.
    得 态.
法.
测试 'utf8-bom' ([239,187,191,97]) ([97]) 2 1 真 'complete' '' 'utf-8' 1 0 1 1 1.
测试 'utf8-crlf' ([231,148,178,97,13,10,97]) ([97]) 3 1024 真 'complete' '' 'utf-8' 2 6 7 2 1.
测试 'utf16le' ([255,254,97,0,61,216,0,222,97,0]) ([128512]) 3 1 真 'complete' '' 'utf-16le' 1 1 5 1 2.
测试 'utf16be' ([254,255,0,97,216,61,222,0,0,97]) ([128512]) 3 17 真 'complete' '' 'utf-16be' 1 1 5 1 2.
测试 'empty' ([]) ([97]) 1 1 真 'complete' '' 'utf-8' 0 0 0 0 0.
测试 'bom-only' ([255,254]) ([97]) 1 1 真 'complete' '' 'utf-16le' 0 0 0 0 0.
测试 'utf32' ([255,254,0,0,97]) ([97]) 1 1 真 'skipped' 'unsupported-bom' '' 0 0 0 0 0.
测试 'late-nul' ([97,97,97,97,0]) ([97]) 1 1 真 'skipped' 'binary-nul' 'utf-8' 0 0 0 0 0.
测试 'late-surrogate' ([97,97,97,97,237,160,128]) ([97]) 1 1024 真 'skipped' 'invalid-utf8' 'utf-8' 0 0 0 0 0.
测试 'overlong' ([224,128,128]) ([97]) 2 1 真 'skipped' 'invalid-utf8' 'utf-8' 0 0 0 0 0.
测试 'utf8-tail' ([97,97,97,97,240,159]) ([97]) 2 1 真 'skipped' 'invalid-utf8' 'utf-8' 0 0 0 0 0.
测试 'utf16-tail' ([255,254,97,0,0,216]) ([97]) 1 1 真 'skipped' 'invalid-utf16' 'utf-16le' 0 0 0 0 0.
测试 'utf16-orphan' ([254,255,220,0]) ([97]) 1 17 真 'skipped' 'invalid-utf16' 'utf-16be' 0 0 0 0 0.
测试 'changed' ([97,97,97,97]) ([97]) 1 1 假 'skipped' 'changed-snapshot' 'utf-8' 0 0 0 0 0.
帽 取 测试 'cap' ([97,97,97,97]) ([97]) 1 1 真 'complete' '' 'utf-8' 1 0 1 1 1.
确认 (帽['capReached'] 且 帽['rawConsumed'] == 4) 'cap still validates EOF'.
零 取 测试 'zero-cap' ([97,97,97,97]) ([97]) 0 1024 真 'complete' '' 'utf-8' 0 0 0 0 0.
确认 (零['capReached'] 且 零['rawConsumed'] == 4) 'zero-cap validates EOF'.
测试 'kmp-nonoverlap' ([97,98,97,98,97,98,97,99,97,98,97,99]) ([97,98,97,99]) 4 1 真 'complete' '' 'utf-8' 2 8 12 1 9.
态 取 核 其 新建 (核 其 编译 ([97])) (元 4) 2.
核 其 喂入 态 ([97,97,97,97]) 0. 核 其 步进 态 1. 核 其 取消 态. 核 其 取消 态.
确认 (态['status'] == 'cancelled' 且 (态['rows'] 其 量) == 0 且 态['retainedCount'] == 0) 'cancel running idempotent'.
态 取 核 其 新建 (核 其 编译 ([97])) (元 2) 2.
核 其 结束 态 真.
确认 (态['status'] == 'skipped' 且 态['reason'] == 'incomplete-file') 'short EOF'.
态 取 核 其 新建 (核 其 编译 ([97])) (元 1) 2.
核 其 喂入 态 ([97]) 1.
确认 (态['status'] == 'error' 且 态['reason'] == 'invalid-argument') 'wrong offset'.
坏 取 核 其 编译 ([55296]).
确认 (坏['status'] == 'invalid-query') 'query surrogate rejected'.
显 'TOTAL PASS: '+(次数[0] 为 句).
