策 取 外言 '../src/associations_policy.ru'.
次数 取 [0].
作 确认 条件 为 事实, 文 为 句:
    若 非 条件 则 卒 'FAIL: '+文. 然
    次数[0] 取 次数[0]+1.
    显 'PASS: '+文.
为
作 应失败 工作 为 算, 文 为 句:
    失败 取 [假].
    试 工作(). 救 原因 失败[0] 取 真. 终
    确认 失败[0] 文.
为
执行 取 'C:\\便携 editor\\如记事本😀\\ru_notepad.exe'.
确认 ((策 其 命令 执行) == '"C:\\便携 editor\\如记事本😀\\ru_notepad.exe" "%1"') 'exact quoted Unicode executable and quoted single file argument'.
确认 ((策 其 命令 '\\\\server\\share with spaces\\ru_notepad.exe') == '"\\\\server\\share with spaces\\ru_notepad.exe" "%1"') 'UNC executable remains exactly quoted'.
应失败 (算: 得 策 其 命令 'ru_notepad.exe'. 法) 'relative executable rejected'.
应失败 (算: 得 策 其 命令 'C:ru_notepad.exe'. 法) 'drive-relative executable rejected'.
应失败 (算: 得 策 其 命令 'C:\\bad"path\\app.exe'. 法) 'embedded quote rejected'.
应失败 (算: 得 策 其 命令 'C:\\bad\npath\\app.exe'. 法) 'control character rejected'.
应失败 (算: 得 策 其 命令 'C:\\wild*card\\app.exe'. 法) 'wildcard rejected'.
确认 ((策 其 测试前缀 'Software\\RuNotepad.Tests\\123-fixture') == 'Software\\RuNotepad.Tests\\123-fixture\\') 'isolated test prefix normalized'.
应失败 (算: 得 策 其 测试前缀 ''. 法) 'empty live prefix rejected by fixture API'.
应失败 (算: 得 策 其 测试前缀 'Software\\Classes'. 法) 'live association prefix rejected by fixture API'.
应失败 (算: 得 策 其 测试前缀 'Software\\RuNotepad.Tests\\'. 法) 'test root without unique child rejected'.
应失败 (算: 得 策 其 测试前缀 'Software\\RuNotepad.Tests\\abc\\child'. 法) 'nested fixture identifier rejected'.
项们 取 策 其 计划 执行.
确认 ((项们 其 量) == 56) 'plan contains only documented candidate values'.
确认 (((策 其 扩展名) 其 量) == 15) 'candidate extension list is explicit and bounded'.
位 取 0.
命令数 取 0.
默认数 取 0.
打开数 取 0.
安全 取 真.
唯一 取 真.
循环 取 0.
循 项们 其 量 次
    项 取 项们[位].
    若 (项[0] 其 含 'UserChoice') 或 (项[0] 其 含 'FileExts') 或 (项[0] 其 含 '*') 或 (项[0] 其 含 'Directory') 则 安全 取 假. 然
    若 项[0] 其 含 '\\shell\\open\\command' 则
        命令数 取 命令数+1.
        若 项[2] != (策 其 命令 执行) 则 安全 取 假. 然
    然
    若 项[0] 其 含 '\\OpenWithProgids' 则
        打开数 取 打开数+1.
        若 项[1] != (策 其 程序标识) 或 项[3] != 0 或 项[2] != '' 则 安全 取 假. 然
    然
    若 项[1] == '' 则
        默认数 取 默认数+1.
        若 非 (项[0] 其 含 'RuNotepad.Text') 且 非 (项[0] 其 含 'Applications\\ru_notepad.exe') 则 安全 取 假. 然
    然
    循环 取 0.
    循 位 次
        旧 取 项们[循环].
        若 旧[0] == 项[0] 且 旧[1] == 项[1] 则 唯一 取 假. 然
        循环 取 循环+1.
    环
    位 取 位+1.
环
确认 安全 'no selected defaults, wildcard handlers, or unquoted commands in plan'.
确认 唯一 'all planned key and value pairs are unique'.
确认 (命令数 == 2) 'application and ProgID both expose exact shell command'.
确认 (默认数 == 4) 'only owned ProgID and command/icon keys use default values'.
确认 (打开数 == 15) 'each supported extension has candidate-only OpenWithProgids value'.
显 'TOTAL PASS: '+(次数[0] 为 句).
