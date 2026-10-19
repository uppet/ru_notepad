# Conservative top-level Markdown heading folds; pure Ru 0.21.6.
# The bridge drains ordered [startLine,count,depth,header] assignments.
# It must not expand a long retroactive paragraph range in one UI callback.
# State: line, CR, finished, heading stack, paragraph start, container,
# fence character/run, HTML closer, indentation, leading, prefix, body length,
# first character/run, run ended, whitespace-only tail, backtick in suffix,
# rolling HTML tail, closer flags, had characters, blank, container blank, bytes.
# Each stack entry is [heading level, header line, fold depth, confirmed].
算 新状态:
    得 [0,假,假,[],-1,假,'',0,'',0,真,'',0,'',0,假,真,假,'',[假,假,假,假,假],假,真,假,0].
法
算 _小 字 为 句:
    若 字 < 'A' 或 字 > 'Z' 则 得 字. 然
    大 取 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.
    小 取 'abcdefghijklmnopqrstuvwxyz'.
    位 取 0.
    循 26 次
        若 字 == 大[位] 则 得 小[位]. 然
        位 取 位+1.
    环
    得 字.
法
算 _宽 字 为 句:
    若 字 < '' 则 得 1. 然
    若 字 < 'ࠀ' 则 得 2. 然
    若 字 < '𐀀' 则 得 3. 然
    得 4.
法
算 字节数 文 为 句:
    若 文 其 量 > 1024 则 卒 'Markdown input exceeds 1024 Unicode scalars.'. 然
    数量 取 0. 位 取 0.
    循 文 其 量 次
        数量 取 数量+(_宽 文[位]). 位 取 位+1.
    环
    得 数量.
法
算 _空 字 为 句:
    得 字 == ' ' 或 字 == '\t'.
法
算 _末为 文 为 句 尾 为 句:
    长 取 文 其 量. 尾长 取 尾 其 量.
    若 长 < 尾长 则 得 假. 然
    得 文[长-尾长:长] == 尾.
法
算 _开为 文 为 句 头 为 句:
    长 取 头 其 量.
    若 文 其 量 < 长 则 得 假. 然
    得 文[0:长] == 头.
法
算 _标签 文 为 句 名 为 句:
    若 非 (_开为 文 名) 则 得 假. 然
    长 取 名 其 量.
    若 文 其 量 == 长 则 得 真. 然
    得 (_空 文[长]) 或 文[长] == '>'.
法
算 _加 列 始 为 数 长 为 数 深 为 数 头 为 事实:
    若 长 <= 0 则 得 空. 然
    若 始 < 0 或 深 < 0 或 深 > 6 则 卒 'Invalid Markdown fold assignment.'. 然
    若 头 且 长 != 1 则 卒 'Markdown headers must be singleton ranges.'. 然
    量 取 列 其 量.
    若 量 > 0 且 非 头 则
        尾 取 列[量-1].
        若 尾[0]+尾[1] == 始 且 尾[2] == 深 且 非 尾[3] 则
            尾[1] 取 尾[1]+长. 得 空.
        然
    然
    若 量 >= 64 则 卒 'Markdown output exceeds 64 compressed ranges.'. 然
    列 其 增 [始,长,深,头].
    得 空.
法
算 _证头 态 列:
    栈 取 态[3]. 量 取 栈 其 量.
    若 量 > 0 则
        顶 取 栈[量-1].
        若 非 顶[3] 则
            _加 列 顶[1] 1 顶[2] 真. 顶[3] 取 真.
        然
    然
    得 空.
法
算 _完段 态 列:
    若 态[4] >= 0 则 _证头 态 列. 然
    态[4] 取 -1.
    得 空.
法
算 _新头 态 级 为 数 行 为 数 列:
    栈 取 态[3].
    循
        量 取 栈 其 量.
        若 量 == 0 则 破. 然
        若 栈[量-1][0] < 级 则 破. 然
        栈 其 弹.
    环
    _证头 态 列.
    深 取 栈 其 量.
    若 深 >= 6 则 卒 'Markdown heading stack exceeds six levels.'. 然
    栈 其 增 [级,行,深,假].
    得 深.
法
算 _清行 态:
    态[9] 取 0. 态[10] 取 真. 态[11] 取 ''. 态[12] 取 0.
    态[13] 取 ''. 态[14] 取 0. 态[15] 取 假. 态[16] 取 真.
    态[17] 取 假. 态[18] 取 ''. 态[19] 取 [假,假,假,假,假].
    态[20] 取 假. 态[21] 取 真.
    得 空.
法
算 _字符 态 字 为 句:
    态[20] 取 真.
    若 非 (_空 字) 则 态[21] 取 假. 然
    若 态[10] 则
        若 字 == ' ' 则
            若 态[9] < 4 则 态[9] 取 态[9]+1. 然
            得 空.
        然
        若 字 == '\t' 则 态[9] 取 4. 得 空. 然
        态[10] 取 假. 态[13] 取 字.
    然
    小字 取 _小 字.
    若 态[11] 其 量 < 32 则 态[11] 取 态[11]+小字. 然
    态[12] 取 态[12]+1.
    若 非 态[15] 且 字 == 态[13] 则
        态[14] 取 态[14]+1.
    另
        态[15] 取 真.
        若 非 (_空 字) 则 态[16] 取 假. 然
        若 字 == '`' 则 态[17] 取 真. 然
    然
    尾 取 态[18]+小字.
    若 尾 其 量 > 11 则 尾 取 尾[(尾 其 量)-11:]. 然
    态[18] 取 尾.
    # Every recognized closer ends in >. Keep the exact rolling tail, but
    # avoid five pure suffix calls when none can possibly match.
    若 字 == '>' 则
        若 _末为 尾 '-->' 则 态[19][0] 取 真. 然
        若 _末为 尾 '</script>' 则 态[19][1] 取 真. 然
        若 _末为 尾 '</pre>' 则 态[19][2] 取 真. 然
        若 _末为 尾 '</style>' 则 态[19][3] 取 真. 然
        若 _末为 尾 '</textarea>' 则 态[19][4] 取 真. 然
    然
    得 空.
法
算 _容器 文 为 句:
    长 取 文 其 量.
    若 长 == 0 则 得 假. 然
    首 取 文[0].
    若 首 == '>' 则 得 真. 然
    若 首 == '-' 或 首 == '+' 或 首 == '*' 则
        若 长 == 1 则 得 真. 然
        若 _空 文[1] 则 得 真. 然
    然
    位 取 0.
    循
        若 位 >= 长 或 位 >= 9 则 破. 然
        若 文[位] < '0' 或 文[位] > '9' 则 破. 然
        位 取 位+1.
    环
    若 位 == 0 或 位 >= 长 则 得 假. 然
    若 文[位] != '.' 且 文[位] != ')' 则 得 假. 然
    若 位+1 == 长 则 得 真. 然
    得 _空 文[位+1].
法
算 _标题 态:
    若 态[9] > 3 或 态[13] != '#' 则 得 0. 然
    数量 取 态[14].
    若 数量 < 1 或 数量 > 6 则 得 0. 然
    若 态[12] == 数量 则 得 数量. 然
    若 _空 态[11][数量] 则 得 数量. 然
    得 0.
法
算 _闭块 态:
    种 取 态[8].
    若 种 == '-->' 则 得 态[19][0]. 然
    若 种 == '</script>' 则 得 态[19][1]. 然
    若 种 == '</pre>' 则 得 态[19][2]. 然
    若 种 == '</style>' 则 得 态[19][3]. 然
    若 种 == '</textarea>' 则 得 态[19][4]. 然
    得 态[21].
法
算 _行 态 列:
    行 取 态[0].
    深 取 态[3] 其 量.
    级 取 _标题 态.
    文 取 态[11].
    # A raw block remains opaque even on its closing line.
    若 态[8] != '' 则
        _完段 态 列. _证头 态 列.
        _加 列 行 1 深 假.
        若 _闭块 态 则 态[8] 取 ''. 然
        得 空.
    然
    若 态[6] != '' 则
        _完段 态 列. _证头 态 列.
        _加 列 行 1 深 假.
        若 态[9] <= 3 且 态[13] == 态[6] 且 态[14] >= 态[7] 且 态[16] 则
            态[6] 取 ''. 态[7] 取 0.
        然
        得 空.
    然
    若 态[21] 则
        _完段 态 列. _证头 态 列. _加 列 行 1 深 假.
        若 态[5] 则 态[22] 取 真. 然
        得 空.
    然
    # Containers are deliberately under-recognized: zero-column ATX exits;
    # otherwise require a blank boundary and a zero-column non-container line.
    容 取 _容器 文.
    若 态[5] 则
        若 态[9] == 0 且 (级 > 0 或 (态[22] 且 非 容)) 则
            态[5] 取 假. 态[22] 取 假.
        另
            态[22] 取 假.
            _完段 态 列. _证头 态 列. _加 列 行 1 深 假.
            得 空.
        然
    然
    # Four leading columns (including a tab) are opaque, even in a paragraph.
    若 态[9] > 3 则
        若 态[4] >= 0 则 态[5] 取 真. 态[22] 取 假. 然
        _完段 态 列. _证头 态 列. _加 列 行 1 深 假. 得 空.
    然
    若 级 > 0 则
        _完段 态 列.
        新深 取 _新头 态 级 行 列.
        _加 列 行 1 新深 假.
        得 空.
    然
    # Setext can retroactively replace a multi-line paragraph, without text.
    若 态[4] >= 0 且 (态[13] == '=' 或 态[13] == '-') 且 态[16] 则
        始 取 态[4]. 级 取 1.
        若 态[13] == '-' 则 级 取 2. 然
        新深 取 _新头 态 级 始 列.
        _加 列 始 1 新深 真.
        _加 列 (始+1) (行-始) (新深+1) 假.
        栈 取 态[3]. 栈[(栈 其 量)-1][3] 取 真.
        态[4] 取 -1.
        得 空.
    然
    若 容 则
        _完段 态 列. _证头 态 列. _加 列 行 1 深 假.
        态[5] 取 真. 态[22] 取 假.
        得 空.
    然
    若 (态[13] == '`' 或 态[13] == '~') 且 态[14] >= 3 则
        _完段 态 列. _证头 态 列. _加 列 行 1 深 假.
        若 态[13] != '`' 或 非 态[17] 则
            态[6] 取 态[13]. 态[7] 取 态[14].
        另
            态[5] 取 真. 态[22] 取 假.
        然
        得 空.
    然
    若 态[13] == '<' 则
        _完段 态 列. _证头 态 列. _加 列 行 1 深 假.
        态[8] 取 'blank'.
        若 _开为 文 '<!--' 则 态[8] 取 '-->'. 然
        若 _标签 文 '<script' 则 态[8] 取 '</script>'. 然
        若 _标签 文 '<pre' 则 态[8] 取 '</pre>'. 然
        若 _标签 文 '<style' 则 态[8] 取 '</style>'. 然
        若 _标签 文 '<textarea' 则 态[8] 取 '</textarea>'. 然
        若 _闭块 态 则 态[8] 取 ''. 然
        得 空.
    然
    # Ambiguous punctuation, reference definitions, and thematic-break-like
    # starts suppress the whole ambiguous paragraph, not merely its first line.
    若 态[13] == '[' 或 态[13] == '\\' 或 态[13] == '=' 或 态[13] == '-' 或 态[13] == '*' 或 态[13] == '_' 则
        态[5] 取 真. 态[22] 取 假.
        _完段 态 列. _证头 态 列. _加 列 行 1 深 假. 得 空.
    然
    若 态[4] < 0 则 态[4] 取 行. 然
    _加 列 行 1 深 假.
    得 空.
法
算 喂入 态 文 为 句 结束 为 事实:
    # _宽 returns at most four bytes per scalar. Keep the original scalar-limit
    # check before any state access; a separate full byte-count pass is redundant.
    若 文 其 量 > 1024 则 卒 'Markdown input exceeds 1024 Unicode scalars.'. 然
    列 取 []. 位 取 0.
    若 态[2] 则
        若 文 != '' 或 非 结束 则 卒 'Markdown state is already finished.'. 然
        得 {'folds':列,'used':0,'line':态[0],'bytes':态[23],'finished':真}.
    然
    长 取 文 其 量.
    窗 取 ''. 窗始 取 0. 窗末 取 0.
    # Local deferral is eligible only after this active-fence line cannot close.
    # Keep the original route for chunks with no newline, including long lines.
    若 态[6] != '' 且 态[8] == '' 且 非 (文 其 含 '>') 且 ((文 其 含 '\r') 或 (文 其 含 '\n')) 则
        缓始 取 -1.
        循
            若 位 >= 长 或 (列 其 量) >= 60 则 破. 然
            若 位 >= 窗末 则
                窗始 取 位. 窗末 取 位+32.
                若 窗末 > 长 则 窗末 取 长. 然
                窗 取 文[窗始:窗末].
            然
            字 取 窗[位-窗始]. 位 取 位+1.
            态[23] 取 态[23]+(_宽 字).
            若 字 == '\n' 且 态[1] 则
                态[1] 取 假.
            另
                态[1] 取 假.
                若 字 == '\r' 或 字 == '\n' 则
                    _行 态 列. 缓始 取 -1.
                    态[0] 取 态[0]+1. _清行 态.
                    若 字 == '\r' 则 态[1] 取 真. 然
                另
                    若 字 != '>' 且 态[6] != '' 且 态[8] == '' 且 (态[9] > 3 或 (非 态[10] 且 态[13] != 态[6])) 则
                        若 缓始 < 0 则 缓始 取 位-1. 然
                    另
                        # A retained closer-flags array must observe every >.
                        若 缓始 >= 0 则
                            循
                                若 缓始 >= 位-1 则 破. 然
                                _字符 态 文[缓始]. 缓始 取 缓始+1.
                            环
                            缓始 取 -1.
                        然
                        _字符 态 字.
                    然
                然
            然
        环
        # EOF keeps line fields, and every public return exposes all 24 slots.
        若 缓始 >= 0 则
            循
                若 缓始 >= 位 则 破. 然
                _字符 态 文[缓始]. 缓始 取 缓始+1.
            环
        然
    另
        循
            若 位 >= 长 或 (列 其 量) >= 60 则 破. 然
            若 位 >= 窗末 则
                窗始 取 位. 窗末 取 位+32.
                若 窗末 > 长 则 窗末 取 长. 然
                窗 取 文[窗始:窗末].
            然
            字 取 窗[位-窗始]. 位 取 位+1.
            态[23] 取 态[23]+(_宽 字).
            若 字 == '\n' 且 态[1] 则
                态[1] 取 假.
            另
                态[1] 取 假.
                若 字 == '\r' 或 字 == '\n' 则
                    _行 态 列. 态[0] 取 态[0]+1. _清行 态.
                    若 字 == '\r' 则 态[1] 取 真. 然
                另
                    _字符 态 字.
                然
            然
        环
    然
    若 结束 且 位 == 长 且 (列 其 量) < 60 则
        _行 态 列. _完段 态 列. 态[2] 取 真.
    然
    得 {'folds':列,'used':位,'line':态[0],'bytes':态[23],'finished':态[2]}.
法
算 资源 态:
    得 {'stack':态[3] 其 量,'prefix':态[11] 其 量,'tail':态[18] 其 量,'state':态 其 量,'ranges':64,'scalars':1024,'bytes':4096}.
法
