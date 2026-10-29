# Executes the exact production helper, with no DLLs or Win32 substitutes.
策 取 外言 '../src/syntax_policy.ru'.
次数 取 [0].
作 确认 条件 为 事实, 文 为 句:
    若 非 条件 则 卒 ('FAIL: '+文). 然
    次数[0] 取 次数[0]+1.
    显 'PASS: '+文.
为
# Every supported C-family suffix: lowercase, uppercase and mixed-case spelling.
后缀们 取 [
    ['c','C','C'],['h','H','H'],['cc','CC','cC'],['hh','HH','hH'],
    ['cpp','CPP','CpP'],['hpp','HPP','hPp'],['cxx','CXX','CxX'],
    ['hxx','HXX','hXx'],['c++','C++','C++'],['h++','H++','H++'],['inl','INL','iNl']
].
位 取 0.
循 后缀们 其 量 次
    后缀 取 后缀们[位].
    子位 取 0.
    循 3 次
        路 取 'C:\\源码😀\\文件.'+后缀[子位].
        预期 取 'cpp'. 若 位 == 0 则 预期 取 'c'. 然
        确认 ((策 其 识别 路) == 预期) ('C-family suffix '+后缀[子位]).
        子位 取 子位+1.
    环
    位 取 位+1.
环
# Only the last filename component and exact final suffix select a lexer.
例们 取 [
    ['data.json','json'],['DATA.JSON','json'],['名字.JsOn','json'],
    ['C:/甲/😀.jSoN','json'],['\\\\server\\共享\\data.JSON','json'],
    ['','plain'],['README','plain'],['a.','plain'],['.','plain'],['..','plain'],
    ['source.ru','ru'],['source.RU','ru'],['data.jsonc','json5'],
    ['data.json5','json5'],['file.cppx','plain'],['file.xcpp','plain'],
    ['file.cxx.bak','plain'],['file.json.bak','plain'],['file.c++x','plain'],
    ['file.h++x','plain'],['file.json ','plain'],['file.cpp\n','plain'],
    ['file.ＣＰＰ','plain'],['file.中文','plain'],['名字😀','plain'],
    ['C:/folder.cpp/README','plain'],['C:\\folder.json\\README','plain'],
    ['C:/folder.json/x','plain'],['C:\\folder.cpp\\x','plain'],
    ['C:/folder.cpp/','plain'],['C:\\folder.json\\','plain'],
    ['C:/folder.cpp/file.json','json'],['C:\\folder.json\\file.cpp','cpp'],
    ['./relative.H','cpp'],['../relative.CXX','cpp'],
    ['a.b.c','c'],['.cpp','cpp'],['.json','json'],
    ['C:/name with spaces/文件名.Hpp','cpp'],
    ['C:\\emoji😀.cpp\\子目录\\main.c','c'],
    ['source.rU','ru'],['C:/源码😀/main.Ru','ru'],['.ru','ru'],
    ['source.rux','plain'],['source.ru.bak','plain'],['source.ru ','plain'],
    ['C:/folder.ru/README','plain'],['C:\\folder.ru\\main.ru','ru']
].
位 取 0.
循 例们 其 量 次
    例 取 例们[位].
    确认 ((策 其 识别 例[0]) == 例[1]) ('path policy '+(位 为 句)).
    位 取 位+1.
环
确认 ((策 其 名称 'cpp') == 'C++') 'C-family display label'.
确认 ((策 其 名称 'json') == 'JSON') 'JSON display label'.
确认 ((策 其 名称 'plain') == 'Plain text') 'plain display label'.
确认 ((策 其 名称 'ru') == 'Ru / 如言') 'Ru-owned lexer has its own display label'.
确认 ((策 其 名称 '') == 'Plain text') 'empty language label'.
确认 ((策 其 名称 'CPP') == 'Plain text') 'unknown language identifier label'.
# Same helper used by production suffix selection and the native fixture CLI.
确认 (非 (策 其 含词 [] '--expect-missing')) 'empty CLI list has no flag'.
确认 (非 (策 其 含词 [] '')) 'empty CLI list has no empty element'.
确认 (策 其 含词 ['--expect-missing'] '--expect-missing') 'single exact missing flag'.
确认 (策 其 含词 ['--expect-bad-lexer'] '--expect-bad-lexer') 'single exact bad-lexer flag'.
确认 (策 其 含词 ['first','--expect-missing','last'] '--expect-missing') 'middle CLI element'.
确认 (策 其 含词 ['first','last','--expect-missing'] '--expect-missing') 'last CLI element'.
确认 (策 其 含词 ['--expect-missing','--expect-missing'] '--expect-missing') 'duplicate CLI flags'.
确认 (非 (策 其 含词 ['--expect-bad-lexer'] '--expect-missing')) 'different exact CLI flag'.
确认 (非 (策 其 含词 ['--expect-missing-extra'] '--expect-missing')) 'flag prefix is not equality'.
确认 (非 (策 其 含词 ['prefix--expect-missing'] '--expect-missing')) 'flag suffix is not equality'.
确认 (非 (策 其 含词 ['--expect-missing=1'] '--expect-missing')) 'flag value suffix does not match'.
确认 (非 (策 其 含词 ['--EXPECT-MISSING'] '--expect-missing')) 'CLI flag matching is case-sensitive'.
确认 (非 (策 其 含词 [' --expect-missing'] '--expect-missing')) 'leading CLI whitespace stays significant'.
确认 (非 (策 其 含词 ['--expect-missing '] '--expect-missing')) 'trailing CLI whitespace stays significant'.
确认 (策 其 含词 [''] '') 'explicit empty string element'.
确认 (策 其 含词 ['','--expect-missing'] '--expect-missing') 'empty element does not hide following flag'.
确认 (策 其 含词 ['甲','😀'] '甲') 'Unicode string element'.
确认 (策 其 含词 ['甲','😀'] '😀') 'four-byte Unicode string element'.
确认 (非 (策 其 含词 ['甲😀'] '😀')) 'Unicode substring is not a whole element'.
原列 取 ['first','--expect-missing','last'].
策 其 含词 原列 '--expect-missing'.
确认 ((原列 其 量) == 3) 'membership never changes array length'.
确认 (原列[0] == 'first' 且 原列[1] == '--expect-missing' 且 原列[2] == 'last') 'membership never changes array contents'.
# Numeric header-bit regression: these exact values exercise the same pure
# helper called by the Win32 margin handler after native result -> number.
# Expected booleans are fixed bit-mask oracles, not recomputed by the helper.
确认 (非 (策 其 是折头 0)) 'numeric fold header bit 0'.
确认 (非 (策 其 是折头 1024)) 'numeric fold header bit 1024'.
确认 (非 (策 其 是折头 4096)) 'numeric fold header bit 4096'.
确认 (非 (策 其 是折头 8191)) 'numeric fold header bit 8191'.
确认 ((策 其 是折头 8192)) 'numeric fold header bit 8192'.
确认 ((策 其 是折头 9216)) 'numeric fold header bit 9216'.
确认 ((策 其 是折头 12288)) 'numeric fold header bit 12288'.
确认 ((策 其 是折头 16383)) 'numeric fold header bit 16383'.
确认 (非 (策 其 是折头 16384)) 'numeric fold header bit 16384'.
确认 (非 (策 其 是折头 17408)) 'numeric fold header bit 17408'.
确认 ((策 其 是折头 24576)) 'numeric fold header bit 24576'.
确认 (非 (策 其 是折头 65536)) 'numeric fold header bit 65536'.
确认 (非 (策 其 是折头 67109888)) 'numeric fold header bit 67109888'.
确认 ((策 其 是折头 67118080)) 'numeric fold header bit 67118080'.
确认 ((策 其 是折头 2147483647)) 'numeric fold header bit 2147483647'.
确认 (非 (策 其 是折头 2147483648)) 'numeric fold header bit 2147483648'.
确认 ((策 其 是折头 2147491840)) 'numeric fold header bit 2147491840'.
确认 ((策 其 是折头 4294967295)) 'numeric fold header bit 4294967295'.
确认 ((策 其 是折头 (-1))) 'numeric fold header bit -1'.
确认 (非 (策 其 是折头 (-8193))) 'numeric fold header bit -8193'.
确认 ((策 其 是折头 (-8192))) 'numeric fold header bit -8192'.
确认 (非 (策 其 是折头 (-2147483648))) 'numeric fold header bit -2147483648'.
确认 ((策 其 是折头 (-2147475456))) 'numeric fold header bit -2147475456'.
确认 (非 (策 其 是折头 8192.5)) 'numeric fold header bit 8192.5'.
确认 (非 (策 其 是折头 4294967296)) 'numeric fold header bit 4294967296'.
确认 (非 (策 其 是折头 (-2147483649))) 'numeric fold header bit -2147483649'.
显 'TOTAL PASS: '+(次数[0] 为 句).
