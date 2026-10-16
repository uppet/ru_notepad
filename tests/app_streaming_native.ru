# Real main-window message/pending-operation tests. Synthetic disposable data only.
应用 取 外言 '../src/main.ru'.
窗 取 外言 '../src/win32.ru'.
编 取 外言 '../src/editor.ru'.
件库 取 外言 '../src/file_codec.ru'.
辅 取 外言 './file_streaming_native.ru'.
拖例 取 外言 './drop_fixture.ru'.
密 取 外言 '如:密'.
Sleep 取 (窗 其 内核) 其 绑定 'Sleep' (密 其 签名 (窗 其 V) ([(窗 其 U)]) 'win64').
Attr 取 (窗 其 内核) 其 绑定 'GetFileAttributesW' (密 其 签名 (窗 其 U) ([(窗 其 PTR)]) 'win64').
Link 取 (窗 其 内核) 其 绑定 'CreateHardLinkW' (密 其 签名 (窗 其 I) ([(窗 其 PTR),(窗 其 PTR),(窗 其 PTR)]) 'win64').
次数 取 [0].
作 确认 条件 为 事实, 名 为 句:
    若 非 条件 则 卒 ('FAIL: '+名). 然
    次数[0] 取 次数[0]+1.
    显 'PASS: '+名.
为
算 计时:
    得 (窗 其 结果 ((窗 其 GetTickCount64) 其 调用 [])) 其 数.
法
作 泵:
    消 取 (窗 其 MSG) 其 新建.
    起 取 计时.
    循
        若 非 ((应用 其 A) 其 查 'busy') 则 破. 然
        若 计时-起 > 120000 则 消 其 关闭. 卒 'File operation timer did not finish within120s.'. 然
        若 非 ((窗 其 结果 ((窗 其 PeekMessageW) 其 调用 [消,空,0,0,1])) 其 为空) 则
            若 (消 其 读 'message') 其 数 == 18 则 消 其 关闭. 卒 'Unexpected WM_QUIT during operation.'. 然
            窗 其 结果 ((窗 其 TranslateMessage) 其 调用 [消]).
            窗 其 结果 ((窗 其 DispatchMessageW) 其 调用 [消]).
        另
            Sleep 其 调用 [1].
        然
    环
    消 其 关闭.
为
作 删文件 路 为 句:
    存 取 密 其 UTF16 路.
    (辅 其 Delete) 其 调用 [存].
    存 其 关闭.
为
算 元初 参数 为 句 阵:
    若 (参数 其 量) != 1 则 显 'Usage: app_streaming_native.exe EXISTING_DISPOSABLE_DIRECTORY'. 得 2. 然
    根 取 参数[0]+'\\ru-app-stream-'.
    一路 取 根+'甲 space & (one).txt'.
    二路 取 根+'😀 two.json'.
    三路 取 根+'drop 中 & (three).txt'.
    大路 取 根+'large.txt'.
    巨路 取 根+'over500MB.txt'.
    出路 取 根+'target.txt'.
    件库 其 写文件 一路 'first α\r\n' 65001 假 ''.
    件库 其 写文件 二路 '{"two":2}\n' 65001 假 ''.
    件库 其 写文件 三路 'third 中' 65001 假 ''.
    原戳 取 件库 其 写文件 出路 'original target' 65001 假 ''.
    块 取 (辅 其 重复 'x' 65535)+'\n'.
    写态 取 件库 其 准备写入 大路 65001 假 ''.
    循 504 次 件库 其 写入一段 写态 块. 环
    件库 其 完成写入 写态.
    辅 其 稀疏文件 巨路 500000001.
    主 取 应用 其 初始化 [一路,二路] 假.
    状态 取 应用 其 A.
    确认 (状态 其 查 'busy') 'Unicode command-line paths enter asynchronous queue'.
    确认 (((状态 其 查 'docs') 其 量) == 1) 'CLI body load has not committed a tab synchronously'.
    泵.
    确认 ((状态 其 查 'ticks') > 0) 'real WM_TIMER messages advanced the file operation'.
    确认 (((状态 其 查 'docs') 其 量) == 3) 'both CLI paths commit separate complete tabs'.
    文们 取 状态 其 查 'docs'.
    确认 ((编 其 文本 (文们[1] 其 查 'editor')) == 'first α\r\n') 'Unicode CLI first file content exact'.
    确认 ((编 其 文本 (文们[2] 其 查 'editor')) == '{"two":2}\n') 'Unicode CLI second file content exact'.
    确认 ((文们[2] 其 查 'language') == 'json') 'small streamed file retains extension-based syntax'.
    确认 ((状态 其 查 'errors') 其 量 == 0) 'normal CLI queue reports no failures'.
    应用 其 切页 1.
    第一 取 应用 其 编辑柄.
    窗 其 发文 第一 2282 1 '!'.
    坏宽 取 辅 其 字节结构 ([0,216,0,0]).
    坏拒 取 [假].
    试 窗 其 解宽 坏宽 1. 救 原因 坏拒[0] 取 真. 终
    坏宽 其 关闭.
    低宽 取 辅 其 字节结构 ([0,220,0,0]).
    低拒 取 [假].
    试 窗 其 解宽 低宽 1. 救 原因 低拒[0] 取 真. 终
    低宽 其 关闭.
    确认 (坏拒[0] 且 低拒[0]) 'shared dialog/input decoder rejects lone high and low UTF16 surrogates as ordinary errors'.
    确认 ((状态 其 查 'ready') 且 (编 其 文本 第一) == 'first α\r\n!' 且 (应用 其 脏 文们[1])) 'invalid external UTF16 leaves application and dirty text intact'.
    修订 取 (应用 其 当前) 其 查 'revision'.
    确认 (修订 > 0) 'SCN_MODIFIED records a real content revision'.
    别路 取 根+'identity-alias.txt'.
    别存 取 密 其 UTF16 别路.
    原存 取 密 其 UTF16 一路.
    窗 其 成功 (Link 其 调用 [别存,原存,空]) 'CreateHardLinkW(fixture)'.
    别存 其 关闭.
    原存 其 关闭.
    拖柄 取 拖例 其 创建 [别路].
    窗 其 发送 (应用 其 编辑柄) 563 ((窗 其 UP) 其 重释 拖柄) 0.
    确认 (拖例 其 已释放 拖柄) 'editor child forwards duplicate HDROP exactly once'.
    泵.
    确认 ((文们 其 量) == 3 且 (状态 其 查 'active') == 1) 'duplicate file identity selects existing tab'.
    确认 ((状态 其 查 'lastReader')['readCalls'] == 0) 'duplicate identity never reads file body'.
    确认 ((编 其 文本 第一) == 'first α\r\n!' 且 (应用 其 脏 文们[1])) 'duplicate open preserves dirty editor bytes'.
    删文件 别路.
    拖柄 取 拖例 其 创建 [参数[0],三路].
    窗 其 发送 (应用 其 编辑柄) 563 ((窗 其 UP) 其 重释 拖柄) 0.
    确认 (拖例 其 已释放 拖柄) 'editor child forwards multi-path HDROP before asynchronous opens'.
    泵.
    确认 (((状态 其 查 'errors') 其 量) == 1) 'directory entry is explicitly rejected'.
    确认 ((文们 其 量) == 4 且 (编 其 文本 (应用 其 编辑柄)) == 'third 中') 'later valid drop path opens after directory failure'.
    确认 ((编 其 文本 第一) == 'first α\r\n!' 且 (应用 其 脏 文们[1])) 'failed batch entry leaves unrelated dirty document intact'.
    应用 其 切页 1.
    应用 其 命令 702.
    应用 其 命令 501.
    应用 其 打开 大路 0.
    窗 其 发送 主 275 901 0.
    读态 取 状态 其 查 'lastReader'.
    确认 (状态 其 查 'busy') 'multi-chunk open remains pending after bounded timer tick'.
    确认 (读态['readBytes'] > 0 且 读态['readBytes'] < 33030144) 'one tick reads a bounded prefix rather than all33MB'.
    确认 ((文们 其 量) == 4) 'pending large editor is absent from committed tabs'.
    确认 ((窗 其 发送 第一 2140 0 0) 其 数 == 1) 'existing documents are readonly during file operation'.
    确认 ((窗 其 发送 主 17 0 0) 其 数 == 0) 'busy state vetoes orderly session termination'.
    原错数 取 (状态 其 查 'errors') 其 量.
    拖柄 取 拖例 其 创建 [三路].
    窗 其 发送 (应用 其 编辑柄) 563 ((窗 其 UP) 其 重释 拖柄) 0.
    确认 (拖例 其 已释放 拖柄) 'busy editor child still forwards and releases HDROP'.
    确认 (((状态 其 查 'errors') 其 量) == 原错数+1) 'busy drop gives explicit retry error'.
    窗 其 发送 主 273 101 0.
    确认 ((文们 其 量) == 4) 'new-tab command cannot mutate a pending operation'.
    窗 其 发送 主 273 901 0.
    泵.
    确认 ((状态 其 查 'lastOutcome') == 'cancelled' 且 读态['closed']) 'Cancel button closes active reader'.
    确认 ((文们 其 量) == 4 且 (状态 其 查 'operation') == 空) 'cancel discards only pending editor without new tab'.
    确认 ((窗 其 发送 第一 2140 0 0) 其 数 == 0) 'cancel restores prior writable state'.
    确认 ((编 其 文本 第一) == 'first α\r\n!' 且 (应用 其 脏 文们[1])) 'open cancellation preserves unrelated dirty document'.
    确认 ((文们[1] 其 查 'language') == 'cpp' 且 (文们[1] 其 查 'wrap')) 'large-file cancellation preserves other tabs manual language and wrap'.
    过量 取 [].
    循 65 次 过量 其 增 一路. 环
    拒 取 [假].
    试 应用 其 入队 过量 0. 救 原因 拒[0] 取 真. 终
    确认 (拒[0] 且 非 (状态 其 查 'busy') 且 (文们 其 量) == 4) 'over64 paths are rejected as a whole without truncation'.
    询数 取 [0].
    状态 其 增 'confirmLarge' (算 大小 为 数: 询数[0] 取 询数[0]+1. 得 假. 法).
    应用 其 打开 巨路 0.
    泵.
    读态 取 状态 其 查 'lastReader'.
    确认 (询数[0] == 1 且 读态['size'] == 500000001) 'main >500MB confirmation uses exact decimal threshold'.
    确认 (读态['readCalls'] == 0 且 读态['readBytes'] == 0 且 读态['bufferBytes'] == 0) 'main large-file decline happens before any body read or buffer'.
    确认 (读态['closed'] 且 (文们 其 量) == 4) 'declined giant open closes snapshot and keeps tabs unchanged'.
    应用 其 打开 大路 0.
    泵.
    大文档 取 应用 其 当前.
    确认 ((文们 其 量) == 5 且 (窗 其 发送 (应用 其 编辑柄) 2183 0 0) 其 数 == 33030144) 'main completes actual33MB open beyond both old buffer limits'.
    确认 (非 (应用 其 脏 大文档)) 'completed pending document reaches clean savepoint'.
    确认 ((大文档 其 查 'large') 且 (大文档 其 查 'language') == 'plain' 且 非 (大文档 其 查 'wrap')) '33MB open uses labelled plain-text performance mode'.
    确认 ((窗 其 发送 (应用 其 编辑柄) 2379 0 0) 其 数 == 257) 'main large-file mode uses64-bit positions and no style allocation'.
    窗 其 发文 (应用 其 编辑柄) 2282 1 '!'.
    应用 其 保存到 出路 原戳 ''.
    窗 其 发送 主 275 901 0.
    写态 取 状态 其 查 'lastWriter'.
    确认 (状态 其 查 'busy') 'large main save advances asynchronously'.
    确认 (写态['bytes'] > 0 且 写态['bytes'] < 33030144 且 非 写态['committed']) 'save writes bounded protected staging before commit'.
    窗 其 发送 主 273 901 0.
    泵.
    确认 ((件库 其 读文件 出路 0)['text'] == 'original target') 'cancelled save preserves original target bytes'.
    确认 ((大文档 其 查 'path') == (件库 其 绝对路径 大路)) 'cancelled Save As does not change document path'.
    临存 取 密 其 UTF16 写态['tempPath'].
    临属 取 Attr 其 调用 [临存].
    临存 其 关闭.
    确认 (写态['closed'] 且 非 写态['tempExists'] 且 (临属 其 值) 其 数 == 4294967295 且 (临属 其 错误码) == 2) 'cancelled save removes owned staged file on disk'.
    确认 (应用 其 脏 大文档) 'save cancellation retains dirty source state'.
    编 其 记保存 (大文档 其 查 'editor').
    # Same-length programmatic mutation must also be detected, not only byte count.
    应用 其 切页 1.
    应用 其 保存到 出路 原戳 ''.
    窗 其 发送 第一 2171 0 0.
    窗 其 发文 第一 2181 0 'other α\r\n!'.
    泵.
    确认 ((状态 其 查 'lastOutcome') == 'failed') 'revision guard rejects same-length programmatic save mutation'.
    确认 ((件库 其 读文件 出路 0)['text'] == 'original target') 'revision failure leaves original target bytes intact'.
    确认 (应用 其 脏 文们[1]) 'revision failure retains dirty document'.
    应用 其 保存到 出路 原戳 ''.
    泵.
    确认 ((状态 其 查 'lastOutcome') == 'saved') 'main streaming save commits successfully'.
    确认 ((件库 其 读文件 出路 0)['text'] == 'other α\r\n!') 'successful main streaming save writes exact bytes'.
    确认 ((文们[1] 其 查 'path') == (件库 其 绝对路径 出路) 且 非 (应用 其 脏 文们[1])) 'path and clean metadata change only after successful commit'.
    应用 其 打开 巨路 0.
    窗 其 发送 主 16 0 0.
    泵.
    确认 ((状态 其 查 'ready') 且 (状态 其 查 'lastOutcome') == 'cancelled') 'WM_CLOSE during work cancels but keeps application alive'.
    确认 ((文们 其 量) == 5) 'WM_CLOSE cancellation preserves every committed tab'.
    # Closing may span async saves, but a cancelled Save As must stop close-all.
    应用 其 新页 '' '' 65001 假 ''.
    草稿 取 应用 其 当前.
    窗 其 发文 (应用 其 编辑柄) 2282 5 'draft'.
    旧问 取 状态 其 查 'confirmClose'.
    旧选路 取 状态 其 查 'chooseSavePath'.
    状态 其 增 'confirmClose' (算 文档: 得 6. 法).
    状态 其 增 'chooseSavePath' (算 原路 为 句: 得 ''. 法).
    确认 (非 (应用 其 关程序)) 'cancelled Save As prevents close-all'.
    确认 ((状态 其 查 'ready') 且 (状态 其 查 'closeIndex') == -1 且 非 (状态 其 查 'busy')) 'cancelled close-all resets continuation without quitting'.
    确认 (应用 其 脏 草稿) 'cancelled close-all retains untitled dirty draft'.
    确认 ((文们 其 量) == 6) 'cancelled close-all preserves every tab'.
    状态 其 增 'chooseSavePath' 旧选路.
    状态 其 增 'confirmClose' 旧问.
    新出 取 根+'close-tab.txt'.
    应用 其 保存到 新出 '' 'tab'.
    泵.
    确认 ((文们 其 量) == 5 且 (件库 其 读文件 新出 0)['text'] == 'draft') 'close-tab continuation runs only after streamed save commits'.
    删文件 新出.
    应用 其 切页 1.
    窗 其 发文 (应用 其 编辑柄) 2282 1 '?'.
    状态 其 增 'confirmClose' (算 文档: 得 6. 法).
    确认 (非 (应用 其 关程序)) 'close-all waits for an asynchronous dirty save'.
    确认 (状态 其 查 'busy') 'close-all save uses the same operation state'.
    泵.
    确认 (非 (状态 其 查 'ready')) 'successful close-all continuation destroys main normally'.
    确认 ((件库 其 读文件 出路 0)['text'] == 'other α\r\n!?') 'close-all saves final dirty bytes before normal shutdown'.
    路们 取 [一路,二路,三路,大路,巨路,出路].
    位 取 0.
    循 路们 其 量 次 删文件 路们[位]. 位 取 位+1. 环
    显 'APP_STREAMING_TESTS_PASS='+(次数[0] 为 句).
    得 0.
法
