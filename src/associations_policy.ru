# Pure registration policy: candidates only, never Windows' selected defaults.
本地 取 外言 'i18n.ru'.
程序标识 取 'RuNotepad.Text'.
应用键 取 'Software\\Classes\\Applications\\ru_notepad.exe'.
类型键 取 'Software\\Classes\\RuNotepad.Text'.
能力键 取 'Software\\RuNotepad\\Capabilities'.
注册应用键 取 'Software\\RegisteredApplications'.
扩展名 取 ['.txt','.ru','.md','.log','.csv','.json','.xml','.yaml','.yml','.ini','.cfg','.c','.h','.cpp','.hpp'].

算 命令 可执行 为 句:
    若 可执行 其 量 < 4 则 卒 (本地 其 文本 'error.association.absolute_path'). 然
    绝对 取 假.
    若 可执行[1] == ':' 且 可执行[2] == '\\' 则
        若 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz' 其 含 可执行[0] 则 绝对 取 真. 然
    然
    若 可执行[:2] == '\\\\' 则 绝对 取 真. 然
    若 非 绝对 则 卒 (本地 其 文本 'error.association.absolute_path'). 然
    位 取 0.
    循 可执行 其 量 次
        字 取 可执行[位].
        若 字 < ' ' 或 字 == '"' 或 字 == '*' 或 字 == '?' 则 卒 (本地 其 文本 'error.association.path_characters'). 然
        位 取 位+1.
    环
    得 '"'+可执行+'" "%1"'.
法

算 计划 可执行 为 句:
    开启 取 命令 可执行.
    项们 取 [
        [应用键,'RuNotepadOwner',可执行,1],
        [应用键,'FriendlyAppName','ru_notepad',1],
        [应用键+'\\shell\\open\\command','',开启,1],
        [类型键,'RuNotepadOwner',可执行,1],
        [类型键,'','ru_notepad text document',1],
        [类型键+'\\DefaultIcon','','"'+可执行+'",0',1],
        [类型键+'\\shell\\open\\command','',开启,1],
        [能力键,'RuNotepadOwner',可执行,1],
        [能力键,'ApplicationName','ru_notepad',1],
        [能力键,'ApplicationDescription','Edit text and source files with ru_notepad.',1],
        [注册应用键,'ru_notepad',能力键,1]
    ].
    位 取 0.
    循 扩展名 其 量 次
        后缀 取 扩展名[位].
        项们 其 增 [应用键+'\\SupportedTypes',后缀,'',1].
        项们 其 增 [能力键+'\\FileAssociations',后缀,程序标识,1].
        项们 其 增 ['Software\\Classes\\'+后缀+'\\OpenWithProgids',程序标识,'',0].
        位 取 位+1.
    环
    得 项们.
法

算 测试前缀 前缀 为 句:
    始 取 'Software\\RuNotepad.Tests\\'.
    若 前缀 其 量 <= 始 其 量 或 前缀[:始 其 量] != 始 则 卒 '测试注册表必须位于隔离的 RuNotepad.Tests 子键。'. 然
    位 取 始 其 量.
    循 (前缀 其 量)-(始 其 量) 次
        若 非 ('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-' 其 含 前缀[位]) 则
            卒 '测试注册表标识只能包含字母、数字及连字符。'.
        然
        位 取 位+1.
    环
    得 前缀+'\\'.
法
