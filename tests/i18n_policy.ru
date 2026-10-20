# Exact production localization policy; no Win32 substitutes or native capability.
本地 取 外言 '../src/i18n.ru'.
布局 取 外言 '../src/i18n_layout.ru'.
次数 取 [0].
作 确认 条件 为 事实, 名 为 句:
    若 非 条件 则 卒 ('FAIL: '+名). 然
    次数[0] 取 次数[0]+1.
    显 'PASS: '+名.
为
确认 ((本地 其 当前语言) == 'en') 'initial language is English'.
确认 (((本地 其 语言们) 其 量) == 7) 'exactly seven supported languages'.
例们 取 [
    ['en','&File','Untitled 17'],
    ['zh-CN','文件(&F)','未命名 17'],
    ['ja','ファイル(&F)','無題 17'],
    ['ko','파일(&F)','제목 없음 17'],
    ['es','Archivo(&F)','Sin título 17'],
    ['ru','Файл(&F)','Без имени 17'],
    ['it','File(&F)','Senza titolo 17']
].
位 取 0.
循 例们 其 量 次
    例 取 例们[位].
    确认 (本地 其 有语言 例[0]) ('supported language '+例[0]).
    确认 ((本地 其 索引 例[0]) == 位) ('stable language slot '+例[0]).
    确认 ((本地 其 设置 例[0]) == 例[0]) ('switch return '+例[0]).
    确认 ((本地 其 当前语言) == 例[0]) ('active language '+例[0]).
    确认 ((本地 其 文本 'menu.file') == 例[1]) ('Unicode menu '+例[0]).
    确认 ((本地 其 格式 'document.untitled' ([17])) == 例[2]) ('localized parameter '+例[0]).
    确认 ((本地 其 文本 'test.missing') == '[test.missing]') ('missing production key '+例[0]).
    确认 ((本地 其 文本 'language.en') == '&English') ('autonym unchanged '+例[0]).
    位 取 位+1.
环
# Revisit all languages in reverse, including selecting the active language again.
位 取 6.
循 7 次
    例 取 例们[位].
    本地 其 设置 例[0].
    本地 其 设置 例[0].
    确认 ((本地 其 当前语言) == 例[0]) ('repeated selection '+例[0]).
    确认 ((本地 其 文本 'menu.file') == 例[1]) ('reverse switch refresh '+例[0]).
    位 取 位-1.
环
未知们 取 ['','fr','EN','zh','zh-cn','zh-TW','JA','en-US','English','../en'].
位 取 0.
循 未知们 其 量 次
    未知 取 未知们[位].
    确认 (非 (本地 其 有语言 未知)) ('unknown language rejected '+(位 为 句)).
    确认 ((本地 其 设置 未知) == 'en') ('unknown language fallback '+(位 为 句)).
    确认 ((本地 其 文本 'menu.file') == '&File') ('unknown language uses English '+(位 为 句)).
    位 取 位+1.
环
# LANGID primary-language extraction covers real regional variants and neutral IDs.
系统们 取 [
    [1033,'en'],[2057,'en'],[3081,'en'],[4105,'en'],[5129,'en'],[9,'en'],
    [2052,'zh-CN'],[1028,'zh-CN'],[3076,'zh-CN'],[4100,'zh-CN'],[5124,'zh-CN'],[4,'zh-CN'],
    [1041,'ja'],[17,'ja'],[1042,'ko'],[18,'ko'],
    [1034,'es'],[2058,'es'],[3082,'es'],[4106,'es'],[21514,'es'],[22538,'es'],[10,'es'],
    [1049,'ru'],[2073,'ru'],[25,'ru'],[1040,'it'],[2064,'it'],[16,'it'],
    [1031,'en'],[1036,'en'],[1046,'en'],[0,'en'],[65535,'en']
].
位 取 0.
循 系统们 其 量 次
    例 取 系统们[位].
    确认 ((本地 其 系统选择 例[0]) == 例[1]) ('system LANGID '+(例[0] 为 句)).
    位 取 位+1.
环
# Exercise the same flat lookup used by production 文本, including missing keys.
目录 取 {
    'en:full':'English','zh-CN:full':'中文','ja:full':'日本語','ko:full':'한국어',
    'es:full':'Español','ru:full':'Русский','it:full':'Italiano',
    'en:short':'English fallback',
    'en:empty_translation':'English fallback','zh-CN:empty_translation':'',
    'ja:empty_translation':'','ko:empty_translation':'','es:empty_translation':'',
    'ru:empty_translation':'','it:empty_translation':'',
    'en:empty_english':'','zh-CN:empty_english':'中文',
    'en:empty_slots':'',
    'en:all_empty':'','zh-CN:all_empty':'','ja:all_empty':'','ko:all_empty':'',
    'es:all_empty':'','ru:all_empty':'','it:all_empty':''
}.
翻译们 取 ['English','中文','日本語','한국어','Español','Русский','Italiano'].
位 取 0.
循 7 次
    语言 取 (本地 其 语言们)[位].
    确认 ((本地 其 取词 目录 语言 'full') == 翻译们[位]) ('synthetic Unicode translation '+语言).
    确认 ((本地 其 取词 目录 语言 'short') == 'English fallback') ('missing slot English fallback '+语言).
    确认 ((本地 其 取词 目录 语言 'empty_translation') == 'English fallback') ('empty slot English fallback '+语言).
    位 取 位+1.
环
确认 ((本地 其 取词 目录 'zh-CN' 'empty_english') == '中文') 'available translation does not require English'.
确认 ((本地 其 取词 目录 'en' 'empty_english') == '[empty_english]') 'empty English is visible'.
确认 ((本地 其 取词 目录 'it' 'empty_english') == '[empty_english]') 'missing translation and English are visible'.
确认 ((本地 其 取词 目录 'en' 'empty_slots') == '[empty_slots]') 'empty catalog entry is visible'.
确认 ((本地 其 取词 目录 'ko' 'all_empty') == '[all_empty]') 'all empty translations are visible'.
确认 ((本地 其 取词 目录 'fr' 'full') == 'English') 'direct lookup unknown language uses English'.
确认 ((本地 其 取词 目录 'zh-CN' 'missing') == '[missing]') 'synthetic absent key is visible'.
确认 ((本地 其 取词 目录 'en' '') == '[]') 'empty absent key is visible'.
# Replacement text is appended once and never interpreted as a template.
格式们 取 [
    ['{0}',['文件{1}😀.txt','unexpected'],'文件{1}😀.txt'],
    ['{0} / {1}',['{1}','{0}'],'{1} / {0}'],
    ['{0}{0}',['{1}'],'{1}{1}'],
    ['{1}-{0}',['零','一'],'一-零'],
    ['{0}',['C:/路径/{0}/原名{1}.ru'],'C:/路径/{0}/原名{1}.ru'],
    ['{0}',['日本語 한국어 Español Русский Italiano 😀'],'日本語 한국어 Español Русский Italiano 😀'],
    ['{0}',['é'],'é'],
    ['Value {0}',[123],'Value 123'],
    ['{9}',['0','1','2','3','4','5','6','7','8','9'],'9'],
    ['{0}',[''],''],
    ['prefix {0} suffix',['中'],'prefix 中 suffix'],
    ['{0}\n{1}\t{0}',['a','b'],'a\nb\ta'],
    ['no fields',['unused'],'no fields'],
    ['',[],''],
    ['{0}',[],'{0}'],
    ['{1}',['zero'],'{1}'],
    ['{10}',['0','1','2','3','4','5','6','7','8','9'],'{10}'],
    ['{x}',['value'],'{x}'],
    ['{',[],'{'],
    ['{}',[],'{}'],
    ['{0',[],'{0'],
    ['0}',[],'0}'],
    ['{-1}',['value'],'{-1}'],
    ['{ 0}',['value'],'{ 0}'],
    ['{0!r}',['value'],'{0!r}'],
    ['{0:>3}',['value'],'{0:>3}']
].
位 取 0.
循 格式们 其 量 次
    例 取 格式们[位].
    确认 ((本地 其 格式文 例[0] 例[1]) == 例[2]) ('single-pass format '+(位 为 句)).
    位 取 位+1.
环
本地 其 设置 'en'.
确认 ((本地 其 格式 'dialog.unsaved' (['file{0}{1}😀.txt'])) == 'Save changes to file{0}{1}😀.txt?') 'production formatting preserves filename braces'.
确认 ((本地 其 当前语言) == 'en') 'test restores English'.
# Native GDI measurements are synthetic inputs here; this checks geometry only.
窗口宽们 取 [480,640,900,1600].
标签组们 取 [[48,65,74,75,40],[190,100,125,170,100],[440,60,90,120,70]].
窗位 取 0.
循 窗口宽们 其 量 次
    宽 取 窗口宽们[窗位].
    组位 取 0.
    循 标签组们 其 量 次
        标签宽们 取 标签组们[组位].
        值 取 布局 其 寻栏布局 宽 标签宽们.
        输入宽 取 值['inputWidth'].
        按们 取 值['buttons'].
        标识 取 (宽 为 句)+'/'+(组位 为 句).
        确认 (输入宽 >= 80) ('minimum input width '+标识).
        确认 (输入宽%1 == 0) ('integer input width '+标识).
        确认 (16+输入宽*2 <= 宽-8) ('inputs remain in viewport '+标识).
        确认 ((按们 其 量) == (标签宽们 其 量)) ('all controls are placed '+标识).
        界内 取 真.
        不叠 取 真.
        不盖输入 取 真.
        高足 取 值['height'] >= 31.
        输入们 取 [[8,5,输入宽,26],[16+输入宽,5,输入宽,26]].
        位 取 0.
        循 按们 其 量 次
            按 取 按们[位].
            若 按[0] < 8 或 按[1] < 5 或 按[2] != 标签宽们[位] 或 按[3] != 26 或 按[0]+按[2] > 宽-8 则 界内 取 假. 然
            若 按[1]+按[3] > 值['height'] 则 高足 取 假. 然
            另位 取 0.
            循 位 次
                另按 取 按们[另位].
                若 按[0] < 另按[0]+另按[2] 且 按[0]+按[2] > 另按[0] 且 按[1] < 另按[1]+另按[3] 且 按[1]+按[3] > 另按[1] 则 不叠 取 假. 然
                另位 取 另位+1.
            环
            另位 取 0.
            循 2 次
                另按 取 输入们[另位].
                若 按[0] < 另按[0]+另按[2] 且 按[0]+按[2] > 另按[0] 且 按[1] < 另按[1]+另按[3] 且 按[1]+按[3] > 另按[1] 则 不盖输入 取 假. 然
                另位 取 另位+1.
            环
            位 取 位+1.
        环
        确认 界内 ('buttons remain in viewport '+标识).
        确认 不叠 ('buttons never overlap '+标识).
        确认 不盖输入 ('buttons never cover inputs '+标识).
        确认 高足 ('layout height contains controls '+标识).
        组位 取 组位+1.
    环
    窗位 取 窗位+1.
环
显 'TOTAL PASS: '+(次数[0] 为 句).
