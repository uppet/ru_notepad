# Portable tests of the production pure-Ru policy, not a replacement parser.
模 取 外言 '../src/markdown_policy.ru'.
次数 取 [0].
作 确认 条件 为 事实 文 为 句:
    若 非 条件 则 卒 ('FAIL: '+文). 然
    次数[0] 取 次数[0]+1. 显 'PASS: '+文.
为
算 新包:
    得 [模 其 新状态,{},0,0,0,假,假].
法
作 接入 包 文 为 句 末 为 事实:
    位 取 0.
    循
        输入 取 文[位:].
        果 取 模 其 喂入 包[0] 输入 末.
        用 取 果['used'].
        若 用 < 0 或 用 > (输入 其 量) 则 卒 'bad consumed scalar count'. 然
        包[2] 取 包[2]+(模 其 字节数 输入[:用]).
        若 包[2] != 果['bytes'] 则 卒 'wrong consumed UTF8 count'. 然
        列 取 果['folds'].
        若 列 其 量 > 64 则 卒 'unbounded output batch'. 然
        若 列 其 量 > 包[3] 则 包[3] 取 列 其 量. 然
        包[4] 取 包[4]+1.
        若 用 < (输入 其 量) 则 包[5] 取 真. 然
        子 取 0.
        循 列 其 量 次
            项 取 列[子].
            若 项[0] < 0 或 项[1] <= 0 或 项[2] < 0 或 项[2] > 6 则 卒 'invalid fold range'. 然
            若 项[3] 且 项[1] != 1 则 卒 'non-singleton heading'. 然
            行 取 项[0].
            循 项[1] 次
                包[1] 其 增 (行) ([项[2],项[3]]). 行 取 行+1.
            环
            子 取 子+1.
        环
        源 取 模 其 资源 包[0].
        若 源['stack'] > 6 或 源['prefix'] > 32 或 源['tail'] > 11 或 源['state'] != 24 则 卒 'unbounded policy state'. 然
        位 取 位+用.
        包[6] 取 果['finished'].
        若 包[6] 且 位 != (文 其 量) 则 卒 'premature finished result'. 然
        若 位 == (文 其 量) 且 (非 末 或 包[6]) 则 破. 然
        若 用 == 0 且 列 其 量 == 0 则 卒 'policy made no progress'. 然
    环
为
算 摘要 包:
    文 取 ''. 位 取 0. 折 取 包[1].
    循 折 其 量 次
        项 取 折[位].
        若 项 == 空 则 卒 'missing physical line'. 然
        若 位 > 0 则 文 取 文+' '. 然
        文 取 文+(项[0] 为 句).
        若 项[1] 则 文 取 文+'H'. 另 文 取 文+'N'. 然
        位 取 位+1.
    环
    得 文.
法
算 运行 文 为 句 块 为 数:
    包 取 新包. 位 取 0. 长 取 文 其 量.
    循
        末 取 位+块. 若 末 > 长 则 末 取 长. 然
        接入 包 文[位:末] (末 == 长).
        位 取 末.
        若 位 == 长 则 破. 然
    环
    得 包.
法
作 核例 名 为 句 文 为 句 期 为 句:
    果 取 运行 文 1024.
    实 取 摘要 果.
    若 实 != 期 则 显 ('ACTUAL '+名+': '+实). 然
    确认 (实 == 期) (名+' expected folds').
    同 取 真. 块们 取 [1,2,3,7,31,127]. 位 取 0.
    循 块们 其 量 次
        若 (摘要 (运行 文 块们[位])) != 期 则 同 取 假. 然
        位 取 位+1.
    环
    确认 同 (名+' fixed chunk parity').
    同 取 真. 切 取 0.
    循 (文 其 量)+1 次
        包 取 新包.
        接入 包 文[:切] 假. 接入 包 文[切:] 真.
        若 (摘要 包) != 期 则 同 取 假. 然
        切 取 切+1.
    环
    确认 同 (名+' every two-way scalar split').
为
核例 'empty' '' '0N'.
核例 'single ATX EOF has no child' '# a' '0N'.
核例 'ATX body' '# a\ntext' '0H 1N'.
核例 'trailing empty line' '# a\n' '0H 1N'.
核例 'empty consecutive headings' '# a\n# b\n# c' '0N 0N 0N'.
核例 'nested skipped levels' '# a\n### b\nx\n## c\ny\n# d\nz' '0H 1H 2N 1H 2N 0H 1N'.
核例 'six heading levels' '# a\n## b\n### c\n#### d\n##### e\n###### f\nx' '0H 1H 2H 3H 4H 5H 6N'.
核例 'ATX space and tab delimiters' '   # a\ntext\n##\nmore\n###\tC\nbody' '0H 1N 1H 2N 2H 3N'.
核例 'invalid ATX delimiters' '#word\n####### bad\n＃ fake\n # fake\n\t# code\n    # code' '0N 0N 0N 0N 0N 0N'.
核例 'Unicode opaque text' '# 标题😀\né中😀\n## Δ\n中文' '0H 1N 1H 2N'.
核例 'mixed CR LF CRLF' '# a\rbody\r\n## b\nx\r' '0H 1N 1H 2N 2N'.
核例 'CRCR and CRLF' '# a\r\r\n# b\r\nz' '0H 1N 0H 1N'.
核例 'setext one line' 'Title\n===\nbody' '0H 1N 1N'.
核例 'setext multiline retroheader' 'Title\nsecond line\nthird\n---\nbody' '0H 1N 1N 1N 1N'.
核例 'setext replaces unconfirmed parent' '# old\nTitle\nsecond\n===\nbody' '0N 0H 1N 1N 1N'.
核例 'setext nested under parent' '# old\nTitle\nsecond\n---\nbody' '0H 1H 2N 2N 2N'.
核例 'setext reduction after deeper heading' '# old\nbody\n### deep\nTitle\n===\nbody' '0H 1N 1N 0H 1N 1N'.
核例 'setext trailing whitespace' 'Title\n   == \t\nbody' '0H 1N 1N'.
核例 'setext single hyphen' 'Title\n-\nbody' '0H 1N 1N'.
核例 'invalid setext' 'Title\n= =\n---x\n    ===\n===\nbody' '0N 0N 0N 0N 0N 0N'.
核例 'blank breaks paragraph' 'Title\n\n---\nbody' '0N 0N 0N 0N'.
核例 'reference definition excluded' '[link]: /url\n===\nbody' '0N 0N 0N'.
核例 'backslash starts excluded' '\\Title\n===\nbody' '0N 0N 0N'.
核例 'fenced backticks' '# real\n```ru\n# fake\nTitle\n===\n```\n## next\nbody' '0H 1N 1N 1N 1N 1N 1H 2N'.
核例 'tilde fence length' '~~~~\n# fake\n~~~\n## fake\n~~~~~ \t\n# real\nbody' '0N 0N 0N 0N 0N 0H 1N'.
核例 'wrong fence closer' '```\n~~~\n# fake\n```x\n## fake\n```\n# real\nbody' '0N 0N 0N 0N 0N 0N 0H 1N'.
核例 'indented fence closer excluded' '```\n    ```\n# fake\n```\n# real\nbody' '0N 0N 0N 0N 0H 1N'.
核例 'unfinished fence' '# real\n```\n# fake\nTitle\n---' '0H 1N 1N 1N 1N'.
核例 'backtick info rejects backtick' '```a`b\n# real\nbody' '0N 0H 1N'.
核例 'indented code' '    # fake\n\t## fake\n# real\nbody' '0N 0N 0H 1N'.
核例 'quote lazy paragraph suppressed' '> Title\nlazy\n===\n# real\nbody' '0N 0N 0N 0H 1N'.
核例 'list indentation after blank suppressed' '- item\n\n  # nested\n  body\n# real\nbody' '0N 0N 0N 0N 0H 1N'.
核例 'ordered list lazy paragraph suppressed' '123. item\nlazy\n---\n\nTop\n===\nbody' '0N 0N 0N 0N 0H 1N 1N'.
核例 'ordered close-paren list' '1) item\n  ## nested\n# real\nbody' '0N 0N 0H 1N'.
核例 'comment block' '<!--\n# fake\nTitle\n===\n-->\n# real\nbody' '0N 0N 0N 0N 0N 0H 1N'.
核例 'same-line comment close' '<!-- # fake -->\n# real\nbody' '0N 0H 1N'.
核例 'unfinished comment' '<!--\n# fake\nTitle\n===' '0N 0N 0N 0N'.
核例 'script case insensitive' '<ScRiPt type="x">\n# fake\n</SCRIPT>\n# real\nbody' '0N 0N 0N 0H 1N'.
核例 'pre block' '<pre>\n# fake\n</pre>\n# real\nbody' '0N 0N 0N 0H 1N'.
核例 'style block' '<style>\n# fake\n</style>\n# real\nbody' '0N 0N 0N 0H 1N'.
核例 'textarea block' '<textarea>\n# fake\n</textarea>\n# real\nbody' '0N 0N 0N 0H 1N'.
核例 'same-line raw tag close' '<script>x</script>\n# real\nbody' '0N 0H 1N'.
核例 'raw HTML is opaque past blank' '<pre>\n\n# fake\n</pre>\n# real\nbody' '0N 0N 0N 0N 0H 1N'.
核例 'generic HTML conservative blank boundary' '<div>\n# fake\n\n# real\nbody' '0N 0N 0N 0H 1N'.
核例 'raw-tag prefix not raw-tag name' '<scripture>\n# fake\n\n# real\nbody' '0N 0N 0N 0H 1N'.
核例 'unfinished raw HTML' '<textarea>\n# fake\nTitle\n---' '0N 0N 0N 0N'.
核例 'reference title continuation stays excluded' '[link]: /url\n"optional title"\n===\nbody' '0N 0N 0N 0N'.
核例 'escaped paragraph continuation stays excluded' '\\Title\nsecond line\n===\nbody' '0N 0N 0N 0N'.
核例 'emphasis paragraph continuation stays excluded' '_Title_\nsecond line\n===\nbody' '0N 0N 0N 0N'.
核例 'indented paragraph continuation stays excluded' 'Title\n    continuation\nsecond line\n===\nbody' '0N 0N 0N 0N 0N'.
核例 'invalid fence paragraph continuation stays excluded' '```a`b\nsecond line\n===\nbody' '0N 0N 0N 0N'.
核例 'excluded paragraph resets after blank' '\\old\ncontinuation\n\nTitle\n===\nbody' '0N 0N 0N 0H 1N 1N'.
核例 'native bridge ATX Unicode sample' '# 甲😀\nbody\n## next\nchild\n' '0H 1N 1H 2N 2N'.
核例 'native bridge setext CRLF sample' 'title\r\nsecond\r\n---\r\nbody\r\n# stop\r\nx' '0H 1N 1N 1N 0H 1N'.
核例 'native bridge fenced HTML sample' '# top\n```\n# fake\n```\n<!--\n# fake\n-->\n# next\nbody' '0H 1N 1N 1N 1N 1N 1N 0H 1N'.
核例 'list blank boundary must be immediate' '- item\n\n  nested\nlazy\n===\n# real\nbody' '0N 0N 0N 0N 0N 0H 1N'.
# Long data is constructed only by the test; production never retains it.
长块 取 ''. 循 1024 次 长块 取 长块+'😀'. 环
包 取 新包.
循 64 次 接入 包 长块 假. 环
确认 (包[1] 其 量 == 0 且 包[2] == 262144) '65536-scalar long line remains unmaterialized'.
源 取 模 其 资源 包[0].
确认 (源['prefix'] == 32 且 源['tail'] == 11 且 源['stack'] == 0) 'long line retains fixed prefix and tail only'.
接入 包 '\n===\nbody' 真.
确认 ((摘要 包) == '0H 1N 1N') 'long Unicode paragraph gains setext heading'.
# A long paragraph needs a singleton header and one retroactive body range;
# use 4096 tiny lines here to assert the same bounded-state property cheaply.
态 取 模 其 新状态. 最大 取 0. 字节 取 0.
循 4096 次
    果 取 模 其 喂入 态 'a\n' 假.
    若 果['folds'] 其 量 > 最大 则 最大 取 果['folds'] 其 量. 然
    字节 取 果['bytes'].
环
源 取 模 其 资源 态.
确认 (源['state'] == 24 且 源['stack'] == 0 且 字节 == 8192 且 最大 <= 1) '4096-line paragraph has constant retained state'.
果 取 模 其 喂入 态 '---' 真. 列 取 果['folds'].
确认 (列 其 量 == 2 且 列[0][0] == 0 且 列[0][3] 且 列[1][0] == 1 且 列[1][1] == 4096) 'long setext paragraph emits two compressed ranges'.
# Many sibling headers force partial input consumption and batch draining.
密 取 ''. 循 256 次 密 取 密+'#\nx\n'. 环
包 取 运行 密 1024.
确认 (包[5] 且 包[3] <= 64 且 包[6]) 'alternating headings drain bounded output and finish'.
确认 (包[1] 其 量 == 513 且 包[2] == 1024) 'partial consumption loses no lines or bytes'.
位 取 0. 同 取 真.
循 256 次
    若 非 包[1][位][1] 或 包[1][位][0] != 0 或 包[1][位+1][0] != 1 则 同 取 假. 然
    位 取 位+2.
环
确认 同 'all 256 headers survive bounded draining'.
# Every byte-width boundary is counted independently of ASCII structure.
确认 ((模 其 字节数 'Aé中😀') == 10) 'UTF8 widths 1 2 3 4'.
包 取 新包. 接入 包 长块 真.
确认 (包[2] == 4096 且 包[6]) 'exact 1024-scalar 4096-byte input accepted'.
失败 取 [假]. 态 取 模 其 新状态.
试 模 其 喂入 态 (长块+'x') 真. 救 原因 失败[0] 取 真. 终
确认 (失败[0] 且 态[0] == 0 且 态[23] == 0 且 态[11] == '') 'oversized input rejected before mutation'.
果 取 模 其 喂入 包[0] '' 真.
确认 (果['finished'] 且 果['folds'] 其 量 == 0 且 果['used'] == 0) 'EOF is idempotent'.
失败 取 [假].
试 模 其 喂入 包[0] 'x' 真. 救 原因 失败[0] 取 真. 终
确认 失败[0] 'finished policy rejects new input'.
# Check the entire fixed state, including both nested arrays; Ru array equality
# is identity equality and would not prove absence of mutation.
算 同全态 甲 乙:
    若 甲 其 量 != 24 或 乙 其 量 != 24 则 得 假. 然
    位 取 0.
    循 24 次
        若 位 == 3 则
            若 甲[3] 其 量 != 乙[3] 其 量 则 得 假. 然
            层 取 0.
            循 甲[3] 其 量 次
                若 甲[3][层] 其 量 != 4 或 乙[3][层] 其 量 != 4 则 得 假. 然
                项 取 0.
                循 4 次
                    若 甲[3][层][项] != 乙[3][层][项] 则 得 假. 然
                    项 取 项+1.
                环
                层 取 层+1.
            环
        另
            若 位 == 19 则
                若 甲[19] 其 量 != 5 或 乙[19] 其 量 != 5 则 得 假. 然
                项 取 0.
                循 5 次
                    若 甲[19][项] != 乙[19][项] 则 得 假. 然
                    项 取 项+1.
                环
            另
                若 甲[位] != 乙[位] 则 得 假. 然
            然
        然
        位 取 位+1.
    环
    得 真.
法
作 核输入边界 名 为 句 单元 为 句 重复 为 数 字节 为 数:
    文 取 ''. 循 重复 次 文 取 文+单元. 环
    态 取 模 其 新状态.
    果 取 模 其 喂入 态 文 真.
    确认 (文 其 量 == 1024 且 果['used'] == 1024 且 果['bytes'] == 字节 且 态[23] == 字节 且 果['finished']) (名+' accepts exactly 1024 scalars with exact bytes').
    态 取 模 其 新状态. 对照 取 模 其 新状态.
    模 其 喂入 态 '# root\nbody' 假. 模 其 喂入 对照 '# root\nbody' 假.
    拒 取 [假].
    试 模 其 喂入 态 (文+'x') 假.
    救 原因 拒[0] 取 (原因 为 句) 其 含 'Markdown input exceeds 1024 Unicode scalars.'. 终
    确认 (拒[0] 且 (同全态 态 对照)) (名+' rejects 1025 scalars before any state mutation').
    模 其 喂入 态 '' 真. 模 其 喂入 对照 '' 真.
    拒[0] 取 假.
    试 模 其 喂入 态 (文+'x') 假.
    救 原因 拒[0] 取 (原因 为 句) 其 含 'Markdown input exceeds 1024 Unicode scalars.'. 终
    确认 (拒[0] 且 (同全态 态 对照)) (名+' keeps scalar-limit error ahead of finished-state error').
为
核输入边界 'ASCII' 'a' 1024 1024.
核输入边界 'two-byte' 'é' 1024 2048.
核输入边界 'CJK' '中' 1024 3072.
核输入边界 'emoji' '😀' 1024 4096.
核输入边界 'combining' 'é' 512 1536.
核输入边界 'mixed-width' 'Aé中😀' 256 2560.
显 'TOTAL PASS: '+(次数[0] 为 句).
