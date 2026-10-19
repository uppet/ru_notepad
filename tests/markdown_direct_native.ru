# Windows x64 acceptance SOURCE. Actual pinned Scintilla/Lexilla controls;
# this file makes no Linux/Wine execution claim and imports no Ru scanner graph.
# Required process runs with RU_GC_THRESHOLD=64 and RU_GC_STATS=1; verify real
# collections, normal assertions and exit status, without modifying the runtime.
# Production has only file_drop. This controlled fixture adds an observation
# hook solely to prove bypass and inject at the LAST read-only 2185 acquisition.
# It assigns NO user semantics to messages bypassed by the native-only segment.
密 取 外言 '如:密'.
窗 取 外言 '../src/win32.ru'.
编 取 外言 '../src/editor.ru'.
折 取 外言 '../src/markdown_syntax.ru'.
拖 取 外言 '../src/file_drop.ru'.
基 取 外言 'markdown_native.ru'.
次数 取 [0].
路由 取 {}.
环境 取 {'parent':空,'instance':空,'callback':空,'recreated':空}.
源 取 '# 甲😀\r\nbody\r\n## Child\r\nitem\r\n# Next\r\nend\r\n'.
_GetWindowSubclass 取 (窗 其 控件) 其 绑定 'GetWindowSubclass' (密 其 签名 (窗 其 I) ([(窗 其 PTR),(窗 其 PTR),(窗 其 UP),(窗 其 PTR)]) 'win64').
_引用型 取 密 其 结构 [['value',窗 其 UP]].
作 确认 条件 为 事实 文 为 句:
    若 非 条件 则 卒 ('FAIL: '+文). 然
    次数[0] 取 次数[0]+1.
    显 'PASS: '+文.
为
算 过程 柄 消息 宽 长:
    得 基 其 过程 柄 消息 宽 长.
法
算 清计 柄:
    计 取 {'fold':0,'pointer':0,'mode':'','fired':假,'afterLevels':[],'afterText':'','afterHwnd':柄}.
    路由 其 增 (柄 其 句) 计.
    得 计.
法
算 层快照 柄:
    果 取 []. 位 取 0.
    循 (窗 其 发送 柄 2154 0 0) 其 数 次
        果 其 增 ((窗 其 发送 柄 2223 位 0) 其 数).
        位 取 位+1.
    环
    得 果.
法
算 层未变 柄 原:
    现 取 层快照 柄.
    若 现 其 量 != 原 其 量 则 得 假. 然
    位 取 0.
    循 原 其 量 次
        若 现[位] != 原[位] 则 得 假. 然
        位 取 位+1.
    环
    得 真.
法
算 同输出 甲 乙:
    若 非 (基 其 同折 甲 乙) 则 得 假. 然
    位 取 0.
    循 (窗 其 发送 甲 2183 0 0) 其 数 次
        若 (窗 其 发送 甲 2038 位 0) 其 数 != (窗 其 发送 乙 2038 位 0) 其 数 则 得 假. 然
        位 取 位+1.
    环
    位 取 0.
    循 (窗 其 发送 甲 2154 0 0) 其 数 次
        若 (窗 其 发送 甲 2228 位 0) 其 数 != (窗 其 发送 乙 2228 位 0) 其 数 或 (窗 其 发送 甲 2230 位 0) 其 数 != (窗 其 发送 乙 2230 位 0) 其 数 则 得 假. 然
        位 取 位+1.
    环
    得 真.
法
算 同全状态 甲 乙:
    若 非 (同输出 甲 乙) 则 得 假. 然
    号们 取 [2159,2174,2016,2009,2008,2143,2145]. 位 取 0.
    循 号们 其 量 次
        若 (窗 其 发送 甲 号们[位] 0 0) 其 数 != (窗 其 发送 乙 号们[位] 0 0) 其 数 则 得 假. 然
        位 取 位+1.
    环
    得 真.
法
作 三路排空 甲 乙 丁:
    (折 其 _直接策略) 其 增 'route' 'bulk'.
    折 其 排空 甲. 折 其 排空 乙.
    (折 其 _直接策略) 其 增 'route' 'perline'.
    折 其 排空 丁.
    (折 其 _直接策略) 其 增 'route' 'bulk'.
    配色 甲. 配色 乙. 配色 丁.
为
作 配色 柄:
    # Test-only colourisation ensures we compare EVERY Lexilla byte style.
    窗 其 发送 柄 4003 0 (-1).
为
算 就绪 柄 文 为 句:
    基 其 准备 柄 文.
    态 取 (折 其 _编辑们) 其 查 (柄 其 句).
    # Execute complete preparation and read/policy steps, but never publish.
    循
        折 其 _一步 柄 态.
        若 态['ranges'] 其 量 > 0 则 破. 然
    环
    得 态.
法
算 子过程 柄 消息 宽 长 号 引:
    计 取 路由 其 查 (柄 其 句).
    码 取 消息 其 数.
    若 计 != 空 且 码 == 2222 则 计 其 增 'fold' (计['fold']+1). 然
    若 计 != 空 且 码 == 2378 且 计['mode'] == 'registration-error' 则
        计 其 增 'mode' ''. 计 其 增 'fired' 真.
        卒 'Controlled Markdown registration callback error.'.
    然
    若 计 != 空 且 码 == 2185 则
        计 其 增 'pointer' (计['pointer']+1).
        若 计['mode'] == 'null' 则 计 其 增 'fired' 真. 得 0. 然
        若 计['mode'] == 'pointer-error' 则 计 其 增 'mode' ''. 计 其 增 'fired' 真. 卒 'Controlled Markdown pointer callback error.'. 然
    然
    # Borrow the REAL native pointer first. The post-forward callback may make
    # that return value stale; production must reject it without dereferencing.
    果 取 窗 其 结果 ((基 其 _DefSubclassProc) 其 调用 [柄,消息,宽,长]).
    若 计 != 空 且 码 == 2185 且 计['mode'] != '' 则
        动作 取 计['mode'].
        计 其 增 'mode' ''.
        计 其 增 'fired' 真.
        若 动作 == 'edit' 则
            窗 其 发送 柄 2190 0 0.
            窗 其 发送 柄 2192 1 0.
            窗 其 发文 柄 2194 1 ' '.
        然
        若 动作 == 'language' 则 折 其 停用 柄. 窗 其 发送 柄 4033 0 0. 然
        若 动作 == 'revoke' 则 折 其 撤销直属 柄. 然
        若 动作 == 'reregister' 则 折 其 登记直属 柄 环境['parent']. 然
        若 动作 == 'replace' 则
            折 其 遗忘 柄.
            流 取 编 其 开始载入 柄 0.
            编 其 追加文本 流 '# replacement\nbody\n'.
            编 其 完成载入 流.
            基 其 安装 柄.
        然
        若 动作 == 'mask' 则 窗 其 发送 柄 2359 65535 0. 然
        若 动作 == 'auto' 则 窗 其 发送 柄 2663 5 0. 然
        若 动作 == 'ready' 则 (折 其 _直库态) 其 增 'ready' 假. 然
        若 动作 == 'bulk-ready' 则 (折 其 _批库态) 其 增 'ready' 假. 然
        若 动作 == 'bulk-abi' 则 (折 其 _批库态) 其 增 'abi' 65535. 然
        若 动作 == 'close' 则
            折 其 遗忘 柄.
            窗 其 成功 ((基 其 _RemoveWindowSubclass) 其 调用 [柄,(环境['callback'] 其 地址),9919]) 'remove closing test hook'.
            窗 其 成功 ((窗 其 DestroyWindow) 其 调用 [柄]) 'close during pointer acquisition'.
            新柄 取 编 其 创建 环境['parent'] 环境['instance'] 3.
            拖 其 启用编辑器 新柄 环境['parent'].
            窗 其 发送 新柄 2359 3 0.
            基 其 准备 新柄 '# recreated\nbody\n'.
            窗 其 成功 ((基 其 _SetWindowSubclass) 其 调用 [新柄,(环境['callback'] 其 地址),9919,0]) 'controlled recreated test hook'.
            清计 新柄.
            环境 其 增 'recreated' 新柄.
            计 其 增 'afterHwnd' 新柄.
        然
        # Make the first intended stale assignment observably different even
        # when an old document already has the correct folds. These test-only
        # sentinel writes precede the callback-exit baseline/counter reset.
        若 动作 == 'edit' 或 动作 == 'language' 或 动作 == 'revoke' 或 动作 == 'reregister' 或 动作 == 'replace' 或 动作 == 'close' 则
            窗 其 发送 计['afterHwnd'] 2222 0 1124.
            计 其 增 'fold' 0.
        然
        # Counting intercepted2222 alone cannot detect forbidden direct writes.
        计 其 增 'afterLevels' (层快照 计['afterHwnd']).
        计 其 增 'afterText' (编 其 文本 计['afterHwnd']).
    然
    得 果.
法
作 拒借 柄 态 计 名 为 句:
    首项 取 态['ranges'][态['rangeIndex']].
    首行 取 首项[0]+态['rangeOffset'].
    首层 取 1024+首项[2]. 若 首项[3] 则 首层 取 首层+8192. 然
    拒 取 [假].
    试 折 其 _发布 柄 态. 救 原因 拒[0] 取 真. 终
    确认 (首行 == 0 且 首层 != 1124 且 计['afterLevels'][0] == 1124 且 拒[0] 且 计['fired'] 且 计['pointer'] == 1 且 计['fold'] == 0 且 态['published'] == 0 且 (层未变 计['afterHwnd'] 计['afterLevels']) 且 (编 其 文本 计['afterHwnd']) == 计['afterText']) 名.
为
作 回退批 柄 态 计 名 为 句:
    折 其 _发布 柄 态.
    确认 (计['fold'] > 0 且 计['fold'] == 态['published'] 且 态['published'] <= 64) 名.
为
算 同数阵 甲 乙:
    若 甲 其 量 != 乙 其 量 则 得 假. 然
    位 取 0.
    循 甲 其 量 次
        若 甲[位] != 乙[位] 则 得 假. 然
        位 取 位+1.
    环
    得 真.
法
作 批指标 路 为 句 态:
    有效 取 0. 若 态['bulkMetricsValid'] 则 有效 取 1. 然
    显 'FOLD_METRICS1 route='+路+' bulkCalls='+(态['bulkCalls'] 为 句)+' bulkLines='+(态['bulkLines'] 为 句)+' fallbackBatches='+(态['fallbackBatches'] 为 句)+' directCalls='+(态['directCalls'] 为 句)+' directLines='+(态['directLines'] 为 句)+' maxPlanBytes='+(态['maxPlanBytes'] 为 句)+' ownedBufferBytes='+(态['ownedBufferBytes'] 为 句)+' bulkUs='+(态['bulkUs'] 为 句)+' metric_valid='+(有效 为 句).
为
作 批果拒验:
    范围们 取 [[0,70,0,假]].
    果 取 折 其 _验批果 范围们 0 0 0 ([0,64,64,0,64,0,0,0]).
    确认 (果[0] == 0 且 果[1] == 64 且 果[2] == 64) 'independent Ru bulk cursor accepts exactly64 completed assignments'.
    坏们 取 [[0,63,63,0,63,0,0,0],[0,65,65,0,65,0,0,0],[0,64,65,0,64,0,0,0],[0,64,64,1,0,0,0,0],[0,64,64,0,64,0,1,0],[0,64,64,0,64,1,0,0],[1,1,0,0,1,0,0,0],[4,1,0,0,1,0,0,0],[5,0,0,0,0,0,0,0]].
    位 取 0.
    循 坏们 其 量 次
        坏 取 坏们[位]. 拒 取 [假].
        试 折 其 _验批果 范围们 0 0 坏[0] 坏. 救 原因 拒[0] 取 真. 终
        确认 拒[0] ('forged partial inconsistent or unsafe bulk result is rejected: '+(位 为 句)).
        位 取 位+1.
    环
    果 取 折 其 _验批果 范围们 0 0 1 ([1,0,0,0,0,0,0,0]).
    确认 (果[0] == 0 且 果[1] == 0 且 果[2] == 0) 'only a zero-attempt prewrite-ineligible result permits a fresh ordinary fallback'.
    果 取 折 其 _验批果 范围们 0 0 4 ([4,1,0,0,1,7,0,0]).
    确认 (果[0] == 0 且 果[1] == 1 且 果[2] == 1) 'error diagnostic cursor counts the uncertain attempted write and is never a resume token'.
为
作 批原生拒验 柄 态 父:
    计划 取 (折 其 _批计划型) 其 新建.
    结果存 取 (折 其 _批果型) 其 新建.
    字节数 取 折 其 _写批计划 计划 态 态['ranges'] 态['rangeIndex'] 态['rangeOffset'].
    文档 取 (窗 其 PTR) 其 重释 (窗 其 发送 柄 2357 0 0).
    直 取 (窗 其 PTR) 其 重释 (窗 其 发送 柄 2185 0 0).
    原层 取 层快照 柄.
    结果存 其 写 'status' 77. 结果存 其 写 'nextIndex' 88.
    原果 取 结果存 其 读U32LE阵 0 8.
    码 取 (窗 其 结果 ((折 其 _FoldApply) 其 调用 [柄,父,(折 其 _直库态)['module'],直,文档,态['length'],计划,字节数,结果存,28])) 其 数.
    确认 (码 == 5 且 (同数阵 原果 (结果存 其 读U32LE阵 0 8)) 且 (层未变 柄 原层)) 'actual helper rejects short result capacity without touching result or any fold'.
    码 取 (窗 其 结果 ((折 其 _FoldApply) 其 调用 [柄,父,(折 其 _直库态)['module'],直,文档,态['length'],计划,1057,结果存,32])) 其 数.
    确认 (码 == 5 且 (同数阵 原果 (结果存 其 读U32LE阵 0 8)) 且 (层未变 柄 原层)) 'actual helper rejects plan capacity above1056 before reading or writing'.
    码 取 (窗 其 结果 ((折 其 _FoldApply) 其 调用 [柄,父,(折 其 _直库态)['module'],直,文档,态['length'],计划,字节数,计划,32])) 其 数.
    确认 (码 == 5 且 (计划 其 读 'abi') 其 数 == 65536 且 (层未变 柄 原层)) 'actual helper rejects overlapping owned plan and result buffers'.
    字段们 取 ['abi','rangeCount','maxLines','reserved0']. 值们 取 [65535,65,65,1]. 位 取 0.
    循 字段们 其 量 次
        折 其 _写批计划 计划 态 态['ranges'] 态['rangeIndex'] 态['rangeOffset'].
        计划 其 写 字段们[位] 值们[位].
        码 取 (窗 其 结果 ((折 其 _FoldApply) 其 调用 [柄,父,(折 其 _直库态)['module'],直,文档,态['length'],计划,字节数,结果存,32])) 其 数.
        果 取 结果存 其 读U32LE阵 0 8.
        确认 (码 == 3 且 果[0] == 3 且 果[1] == 0 且 果[2] == 0 且 果[6] == 0 且 果[7] == 0 且 (层未变 柄 原层)) ('actual helper rejects malformed bounded header before any write: '+字段们[位]).
        位 取 位+1.
    环
    折 其 _写批计划 计划 态 态['ranges'] 态['rangeIndex'] 态['rangeOffset'].
    行存 取 计划 其 读 'range0'. 行存 其 写 'start' 4294967295. 行存 其 写 'count' 2. 行存 其 关闭.
    码 取 (窗 其 结果 ((折 其 _FoldApply) 其 调用 [柄,父,(折 其 _直库态)['module'],直,文档,态['length'],计划,字节数,结果存,32])) 其 数.
    确认 (码 == 3 且 (结果存 其 读 'attempted') 其 数 == 0 且 (层未变 柄 原层)) 'actual helper rejects unsigned range overflow before any fold write'.
    折 其 _写批计划 计划 态 态['ranges'] 态['rangeIndex'] 态['rangeOffset'].
    窗 其 发送 柄 2359 65535 0.
    码 取 (窗 其 结果 ((折 其 _FoldApply) 其 调用 [柄,父,(折 其 _直库态)['module'],直,文档,态['length'],计划,字节数,结果存,32])) 其 数.
    果 取 结果存 其 读U32LE阵 0 8.
    折 其 _验批果 态['ranges'] 态['rangeIndex'] 态['rangeOffset'] 码 果.
    确认 (码 == 1 且 果[1] == 0 且 果[2] == 0 且 (层未变 柄 原层)) 'actual native qualification produces the validated zero-attempt fallback result'.
    窗 其 发送 柄 2359 3 0.
    # Native errors must remain errors; never erase status or replay a batch.
    窗 其 发送 柄 2382 7 0.
    码 取 (窗 其 结果 ((折 其 _FoldApply) 其 调用 [柄,父,(折 其 _直库态)['module'],直,文档,态['length'],计划,字节数,结果存,32])) 其 数.
    果 取 结果存 其 读U32LE阵 0 8.
    确认 (码 == 4 且 果[1] == 0 且 果[2] == 0 且 果[5] == 7 且 (层未变 柄 原层)) 'actual helper preserves outstanding Scintilla error and performs zero writes'.
    窗 其 发送 柄 2382 0 0.
    直 取 空. 文档 取 空. 结果存 其 关闭. 计划 其 关闭.
为
算 元初 参数 为 句 阵:
    库 取 密 其 动态库 ((窗 其 目录)+'Scintilla.dll').
    实例 取 窗 其 成功 ((窗 其 GetModuleHandleW) 其 调用 [空]) 'instance'.
    类名 取 密 其 UTF16 'RuNotepad.MarkdownDirectFixture'.
    回调 取 密 其 回调 (窗 其 WNDPROC) (算 过程) 0.
    子回调 取 密 其 回调 (基 其 _子型) (算 子过程) 0.
    类 取 (窗 其 WNDCLASS) 其 新建.
    类 其 写 'size' ((窗 其 WNDCLASS) 其 大小).
    类 其 写 'proc' (回调 其 地址).
    类 其 写 'instance' 实例.
    类 其 写 'name' (类名 其 地址).
    窗 其 成功 ((窗 其 RegisterClassExW) 其 调用 [类]) 'register direct Markdown fixture'.
    父 取 窗 其 控制 空 实例 'RuNotepad.MarkdownDirectFixture' 'Markdown direct acceptance' 13565952 0.
    环境 其 增 'parent' 父. 环境 其 增 'instance' 实例. 环境 其 增 'callback' 子回调.
    甲 取 编 其 创建 父 实例 1. 乙 取 编 其 创建 父 实例 2.
    拖 其 启用编辑器 甲 父. 拖 其 启用编辑器 乙 父.
    窗 其 成功 ((基 其 _SetWindowSubclass) 其 调用 [甲,子回调 其 地址,9919,0]) 'controlled direct test hook'.
    窗 其 成功 ((基 其 _SetWindowSubclass) 其 调用 [乙,子回调 其 地址,9919,0]) 'controlled message test hook'.
    引存 取 _引用型 其 新建.
    原钩 取 窗 其 结果 (_GetWindowSubclass 其 调用 [甲,((拖 其 _子回调)[0] 其 地址),(拖 其 _子类编号),引存]).
    确认 (非 (原钩 其 为空) 且 (引存 其 读 'value') 其 句 == ((窗 其 UP) 其 重释 父) 其 句) 'real production file_drop hook is installed with the exact owned parent'.
    引存 其 关闭.
    确认 ((折 其 _直库态)['ready'] 且 (折 其 _直库态)['library'] != 空) 'pinned Scintilla exposes the preflighted typed direct export with a strong library root'.
    确认 ((折 其 _批库态)['ready'] 且 (折 其 _批库态)['abi'] == 65536 且 (折 其 _批库态)['library'] != 空 且 (窗 其 结果 ((折 其 _FoldABI) 其 调用 [])) 其 数 == 65536) 'actual app-private bulk helper exports the exact preflighted version and typed binding'.
    确认 (((折 其 _批计划型) 其 大小) == 1056 且 ((折 其 _批果型) 其 大小) == 32 且 ((折 其 _批计划型) 其 偏移 'range0') == 32 且 ((折 其 _批计划型) 其 偏移 'range63') == 1040) 'typed owned fixed-width plan and result have exact bounded ABI offsets and sizes'.
    批果拒验.
    确认 (非 (折 其 登记直属 空 父) 且 非 (折 其 登记直属 甲 乙)) 'null and wrong-parent owners cannot register a direct capability'.

    态 取 就绪 甲 源.
    确认 ((窗 其 发送 甲 2378 0 0) 其 数 != 3 且 非 (折 其 登记直属 甲 父)) 'default broad notification mask cannot acquire a direct capability'.
    甲计 取 清计 甲.
    回退批 甲 态 甲计 'unregistered unknown-hook fixture retains every original fold message'.
    窗 其 发送 甲 2359 3 0. 窗 其 发送 乙 2359 3 0.
    态 取 就绪 甲 源. 甲计 取 清计 甲. 甲计 其 增 'mode' 'registration-error'.
    拒 取 [假].
    试 折 其 登记直属 甲 父. 救 原因 拒[0] 取 (原因 为 句) 其 含 'Controlled Markdown registration callback error.'. 终
    确认 (拒[0] 且 甲计['fired'] 且 ((折 其 _直属们) 其 查 (甲 其 句)) == 空) 'real registration-query callback error propagates and removes only its provisional capability'.
    基 其 准备 乙 源. 乙计 取 清计 乙. 折 其 排空 乙. 配色 乙.
    态 取 就绪 甲 源. 甲计 取 清计 甲.
    折 其 排空 甲. 配色 甲.
    确认 (甲计['pointer'] == 0 且 甲计['fold'] > 0 且 (同输出 甲 乙)) 'mask3 without explicit owner registration remains message-only and exactly equivalent'.

    批指标 'fallback' (折 其 状态 乙).
    基 其 准备 甲 源.
    确认 (折 其 登记直属 甲 父) 'exclusive same-thread fixture explicitly attests its controlled chain and registers'.
    窗 其 发送 甲 2160 2 19.
    甲计 取 清计 甲. 态 取 折 其 排空 甲. 配色 甲.
    确认 (甲计['pointer'] > 0 且 甲计['fold'] == 0 且 态['published'] == 乙计['fold'] 且 态['published'] > 0 且 (同输出 甲 乙)) 'actual direct publication bypasses2222 while every text byte style fold visible and expanded bit equals fallback'.
    确认 (态['bulkCalls'] > 0 且 态['bulkLines'] == 态['published'] 且 态['directCalls'] == 0 且 态['fallbackBatches'] == 0 且 态['maxPlanBytes'] <= 1056 且 态['ownedBufferBytes'] == 1088 且 态['bulkMetricsValid'] 且 态['bulkUs'] >= 0 且 态['bulkUs']%1 == 0) 'default qualified route really uses bounded bulk calls with exact completed-line and integer timing counters'.
    确认 ((编 其 文本 甲) == 源 且 非 (编 其 已变 甲) 且 (窗 其 发送 甲 2174 0 0) 其 数 == 0 且 (窗 其 发送 甲 2016 0 0) 其 数 == 0 且 (窗 其 发送 甲 2009 0 0) 其 数 == 2 且 (窗 其 发送 甲 2008 0 0) 其 数 == 19) 'direct folds preserve clean savepoint empty undo redo and exact byte selection'.
    确认 (((折 其 _编辑们) 其 查 (甲 其 句)) 其 量 == 33 且 态['maxRead'] <= 1024 且 态['maxPublish'] <= 64 且 态['maxRanges'] <= 64) 'external capability adds no scan fields and preserves all bounded publication and read limits'.
    确认 ((折 其 全折 甲 0) 且 非 (基 其 全显 甲) 且 (折 其 全折 甲 1) 且 (基 其 全显 甲) 且 (基 其 全展开 甲)) 'completed direct folds still support native collapse and expand'.

    批指标 'bulk' 态.
    丁 取 编 其 创建 父 实例 5. 拖 其 启用编辑器 丁 父.
    窗 其 发送 丁 2359 3 0. 基 其 准备 丁 源. 折 其 登记直属 丁 父.
    窗 其 发送 丁 2160 2 19.
    (折 其 _直接策略) 其 增 'route' 'perline'.
    丁态 取 折 其 排空 丁. 配色 丁.
    (折 其 _直接策略) 其 增 'route' 'bulk'.
    确认 (丁态['bulkCalls'] == 0 且 丁态['directCalls'] == 丁态['published'] 且 丁态['directLines'] == 丁态['published'] 且 丁态['published'] > 0 且 (同输出 丁 甲) 且 (同输出 丁 乙)) 'retained explicit per-line source control matches every bulk and message text byte style fold visibility and expansion value'.
    确认 ((编 其 文本 丁) == 源 且 非 (编 其 已变 丁) 且 (窗 其 发送 丁 2174 0 0) 其 数 == 0 且 (窗 其 发送 丁 2016 0 0) 其 数 == 0 且 (窗 其 发送 丁 2009 0 0) 其 数 == 2 且 (窗 其 发送 丁 2008 0 0) 其 数 == 19) 'per-line comparison control preserves exact clean savepoint selection undo and redo state'.
    批指标 'perline' 丁态.
    窗 其 发送 乙 2160 2 19.
    确认 ((同全状态 甲 乙) 且 (同全状态 丁 乙)) 'three publication routes match complete clean text style fold visibility expansion savepoint selection undo and redo state'.
    对照柄们 取 [甲,乙,丁]. 位 取 0.
    循 3 次
        选柄 取 对照柄们[位]. 窗 其 发送 选柄 2160 0 1. 窗 其 发文 选柄 2170 0 ' '.
        位 取 位+1.
    环
    三路排空 甲 乙 丁.
    确认 ((编 其 已变 甲) 且 (同全状态 甲 乙) 且 (同全状态 丁 乙)) 'three routes preserve identical dirty savepoint exact selection and available undo after the same text edit'.
    位 取 0. 循 3 次 窗 其 发送 对照柄们[位] 2176 0 0. 位 取 位+1. 环
    三路排空 甲 乙 丁.
    确认 (非 (编 其 已变 甲) 且 (编 其 文本 甲) == 源 且 (同全状态 甲 乙) 且 (同全状态 丁 乙)) 'three routes undo to the identical source savepoint and complete style fold selection redo state'.
    位 取 0. 循 3 次 窗 其 发送 对照柄们[位] 2011 0 0. 位 取 位+1. 环
    三路排空 甲 乙 丁.
    确认 ((编 其 已变 甲) 且 (同全状态 甲 乙) 且 (同全状态 丁 乙)) 'three routes redo the identical text edit without changing any complete-state comparison'.
    位 取 0. 循 3 次 窗 其 发送 对照柄们[位] 2176 0 0. 位 取 位+1. 环
    三路排空 甲 乙 丁.
    折 其 遗忘 丁. 窗 其 成功 ((窗 其 DestroyWindow) 其 调用 [丁]) 'destroy per-line comparison'.

    # Same-document edits retain capability, but every revision is new. Repeated
    # publication and allocations also run under the mandatory GC-stress process.
    重 取 0.
    循 4 次
        窗 其 发送 甲 2160 0 1. 窗 其 发文 甲 2170 0 ' '.
        选始 取 (窗 其 发送 甲 2009 0 0) 其 数. 选末 取 (窗 其 发送 甲 2008 0 0) 其 数.
        新计 取 折 其 状态 甲.
        确认 (新计['bulkCalls'] == 0 且 新计['bulkLines'] == 0 且 新计['fallbackBatches'] == 0 且 新计['directCalls'] == 0 且 新计['ownedBufferBytes'] == 0) 'new text revision resets only its own bounded diagnostic counters'.
        甲计 取 清计 甲. 折 其 排空 甲. 配色 甲.
        基 其 准备 乙 (' '+源[1:]). 折 其 排空 乙. 配色 乙.
        确认 (甲计['pointer'] > 0 且 甲计['fold'] == 0 且 (编 其 已变 甲) 且 (同输出 甲 乙) 且 (窗 其 发送 甲 2009 0 0) 其 数 == 选始 且 (窗 其 发送 甲 2008 0 0) 其 数 == 选末) 'repeated same-length direct edit equals fresh fallback and preserves dirty selection'.
        窗 其 发送 甲 2176 0 0. 折 其 排空 甲. 配色 甲.
        基 其 准备 乙 源. 折 其 排空 乙. 配色 乙.
        确认 ((编 其 文本 甲) == 源 且 非 (编 其 已变 甲) 且 (同输出 甲 乙)) 'repeated undo restores the exact source savepoint styles and folds'.
        窗 其 发送 甲 2011 0 0. 折 其 排空 甲.
        确认 ((编 其 文本 甲) == ' '+源[1:] 且 (编 其 已变 甲)) 'repeated redo remains a text-only edit after direct folding'.
        窗 其 发送 甲 2176 0 0. 折 其 排空 甲.
        折 其 设置折叠 甲 假.
        确认 (非 (折 其 待办 甲) 且 (基 其 全显 甲) 且 (基 其 全展开 甲)) 'repeated fold disable completes visibility cleanup'.
        折 其 设置折叠 甲 真. 甲计 取 清计 甲. 折 其 排空 甲. 配色 甲.
        确认 (甲计['pointer'] > 0 且 甲计['fold'] == 0 且 (同输出 甲 乙)) 'repeated fold reenable prepares auto0 then resumes exact direct publication'.
        重 取 重+1.
    环

    段 取 'body\n'. 循 9 次 段 取 段+段. 环
    长文 取 段+'---\nlast'.
    基 其 准备 甲 长文. 折 其 登记直属 甲 父. 甲计 取 清计 甲.
    态 取 折 其 排空 甲.
    基 其 准备 乙 长文. 折 其 排空 乙.
    确认 (甲计['pointer'] > 1 且 甲计['fold'] == 0 且 态['maxPublish'] == 64 且 态['maxRead'] <= 1024 且 态['maxRanges'] <= 64 且 (基 其 同折 甲 乙) 且 非 态['pending']) 'retroactive Setext range really uses multiple at-most64-line direct segments and bounded reads'.

    确认 (态['bulkCalls'] > 1 且 态['bulkLines'] == 态['published'] 且 态['bulkLines'] <= 态['bulkCalls']*64 且 态['directCalls'] == 0 且 态['maxPlanBytes'] <= 1056 且 态['ownedBufferBytes'] == 1088) 'multi-batch retroactive Setext uses actual native calls capped at64 and at most1088 owned bytes'.
    折 其 登记直属 乙 父. 折 其 设置折叠 乙 假. 折 其 设置折叠 乙 真.
    (折 其 _直接策略) 其 增 'route' 'perline'.
    乙态 取 折 其 排空 乙. 配色 乙. 配色 甲.
    (折 其 _直接策略) 其 增 'route' 'bulk'.
    确认 (乙态['directLines'] == 乙态['published'] 且 乙态['bulkCalls'] == 0 且 乙态['maxPublish'] == 64 且 (同输出 甲 乙)) 'multi-batch compressed Setext also exactly matches retained per-line control'.

    围栏文 取 '# outside\n```\n'+段.
    基 其 准备 甲 围栏文. 折 其 登记直属 甲 父. 甲计 取 清计 甲.
    围栏态 取 折 其 排空 甲. 配色 甲.
    基 其 准备 乙 围栏文. 乙计 取 清计 乙. 折 其 排空 乙. 配色 乙.
    确认 (围栏态['bulkCalls'] > 1 且 围栏态['bulkLines'] == 围栏态['published'] 且 围栏态['maxPublish'] == 64 且 围栏态['maxRanges'] <= 64 且 甲计['fold'] == 0 且 (同输出 甲 乙)) 'many-line unclosed fence compresses ranges and completes multiple bounded bulk calls with exact fallback output'.
    确认 ((编 其 文本 甲) == 围栏文 且 非 (编 其 已变 甲) 且 (窗 其 发送 甲 2174 0 0) 其 数 == 0 且 (窗 其 发送 甲 2016 0 0) 其 数 == 0) 'unclosed-fence bulk work preserves source savepoint and empty undo redo'.

    态 取 就绪 甲 源. 折 其 登记直属 甲 父.
    批原生拒验 甲 态 父.
    甲计 取 清计 甲. 折 其 _发布 甲 态.
    确认 (甲计['fold'] == 0 且 (折 其 状态 甲)['bulkCalls'] == 1) 'invalid-plan fixtures leave ownership and later legitimate bulk publication intact'.

    态 取 就绪 甲 源. 折 其 登记直属 甲 父.
    (折 其 _批库态) 其 增 'ready' 假. 甲计 取 清计 甲.
    回退批 甲 态 甲计 'missing bulk helper selects original messages rather than the retained per-line control'.
    确认 (甲计['pointer'] == 0 且 (折 其 状态 甲)['bulkCalls'] == 0 且 (折 其 状态 甲)['directCalls'] == 0) 'missing bulk helper performs no native apply or direct write'.
    (折 其 _批库态) 其 增 'ready' 真.
    态 取 就绪 甲 源. 折 其 登记直属 甲 父.
    (折 其 _批库态) 其 增 'abi' 65535. 甲计 取 清计 甲.
    回退批 甲 态 甲计 'old helper ABI selects complete original messages before pointer acquisition'.
    确认 (甲计['pointer'] == 0 且 (折 其 状态 甲)['bulkCalls'] == 0) 'wrong helper ABI never invokes native bulk'.
    (折 其 _批库态) 其 增 'abi' 65536.
    态 取 就绪 甲 源. 折 其 登记直属 甲 父.
    (折 其 _直接策略) 其 增 'route' 'fallback'. 甲计 取 清计 甲.
    回退批 甲 态 甲计 'explicit source-only fallback control keeps original guarded messages'.
    (折 其 _直接策略) 其 增 'route' 'bulk'.

    态 取 就绪 甲 源. 折 其 登记直属 甲 父.
    窗 其 发送 甲 2359 65535 0. 甲计 取 清计 甲.
    回退批 甲 态 甲计 'broader mask before acquisition selects the complete original-message segment'.
    确认 (甲计['pointer'] == 0) 'pre-acquisition mask failure borrows no direct pointer'.
    窗 其 发送 甲 2359 3 0.
    态 取 就绪 甲 源. 折 其 登记直属 甲 父.
    窗 其 发送 甲 2663 5 0. 甲计 取 清计 甲.
    回退批 甲 态 甲计 'automatic folding enabled before acquisition selects original messages'.
    确认 (甲计['pointer'] == 0) 'pre-acquisition automatic-fold failure borrows no direct pointer'.
    态 取 就绪 甲 源. 折 其 登记直属 甲 父.
    (折 其 _直库态) 其 增 'ready' 假. 甲计 取 清计 甲.
    回退批 甲 态 甲计 'unavailable-ready missing-export outcome is safely simulated by the guarded fallback'.
    确认 (甲计['pointer'] == 0) 'disabled binding readiness never attempts pointer acquisition'.
    (折 其 _直库态) 其 增 'ready' 真.
    态 取 就绪 甲 源. 折 其 登记直属 甲 父.
    (折 其 _直接策略) 其 增 'enabled' 假. 甲计 取 清计 甲.
    回退批 甲 态 甲计 'disabled source-only direct policy preserves the original publication segment'.
    (折 其 _直接策略) 其 增 'enabled' 真.
    态 取 就绪 甲 源. 折 其 登记直属 甲 父.
    折 其 撤销直属 甲.
    窗 其 发送 甲 2190 0 0. 窗 其 发送 甲 2192 1 0. 窗 其 发文 甲 2194 1 ' '.
    折 其 设置折叠 甲 假. 折 其 设置折叠 甲 真.
    态 取 (折 其 _编辑们) 其 查 (甲 其 句).
    循
        折 其 _一步 甲 态.
        若 态['ranges'] 其 量 > 0 则 破. 然
    环
    甲计 取 清计 甲.
    回退批 甲 态 甲计 'explicit revocation survives same-document edit and fold toggles without reacquiring direct capability'.
    态 取 就绪 甲 源. 折 其 登记直属 甲 父.
    甲计 取 清计 甲. 甲计 其 增 'mode' 'pointer-error'.
    原层 取 层快照 甲. 拒 取 [假].
    试 折 其 _发布 甲 态. 救 原因 拒[0] 取 (原因 为 句) 其 含 'Controlled Markdown pointer callback error.'. 终
    确认 (拒[0] 且 甲计['fired'] 且 甲计['pointer'] == 1 且 甲计['fold'] == 0 且 态['published'] == 0 且 (折 其 状态 甲)['bulkCalls'] == 0 且 (层未变 甲 原层)) 'last2185 callback error propagates before native apply and before any stale write'.
    态 取 就绪 甲 源. 折 其 登记直属 甲 父.
    甲计 取 清计 甲. 甲计 其 增 'mode' 'null'.
    回退批 甲 态 甲计 'real2185 NULL result falls back before any mutation'.
    确认 (甲计['fired'] 且 甲计['pointer'] == 1) 'NULL negative control actually reaches the pointer-acquisition callback'.

    模式们 取 ['mask','auto','ready','bulk-ready','bulk-abi']. 位 取 0.
    循 模式们 其 量 次
        态 取 就绪 甲 源. 折 其 登记直属 甲 父.
        甲计 取 清计 甲. 甲计 其 增 'mode' 模式们[位].
        回退批 甲 态 甲计 ('configuration changed during2185 is checked again before direct writes: '+模式们[位]).
        确认 (甲计['fired'] 且 甲计['pointer'] == 1) 'configuration fallback is exercised after real pointer acquisition'.
        窗 其 发送 甲 2359 3 0. (折 其 _直库态) 其 增 'ready' 真.
        (折 其 _批库态) 其 增 'ready' 真. (折 其 _批库态) 其 增 'abi' 65536.
        位 取 位+1.
    环

    模式们 取 ['edit','language','revoke','reregister','replace']. 位 取 0.
    循 模式们 其 量 次
        态 取 就绪 甲 源. 折 其 登记直属 甲 父.
        甲计 取 清计 甲. 甲计 其 增 'mode' 模式们[位].
        拒借 甲 态 甲计 ('real2185 owner invalidation rejects even one stale direct fold write: '+模式们[位]).
        位 取 位+1.
    环
    确认 (((折 其 _直属们) 其 查 (甲 其 句)) == 空) 'owner-invalidated document replacement inherits no capability'.

    旧态 取 就绪 甲 源. 折 其 登记直属 甲 父.
    折 其 _统计 甲 旧态.
    窗 其 发送 甲 2190 0 0. 窗 其 发送 甲 2192 1 0. 窗 其 发文 甲 2194 1 ' '.
    新态 取 (折 其 _编辑们) 其 查 (甲 其 句).
    新计 取 折 其 _统计 甲 新态.
    折 其 _丢弃 甲 旧态.
    确认 (((折 其 _批统计们) 其 查 (甲 其 句)) == 新计 且 新计['identity'] == 新态['identity']) 'stale interrupted cleanup cannot delete replacement identity counters'.

    # Sharing is explicitly preceded by revocation; the added document watcher
    # is NEVER claimed safe for direct calls. The second view stays unregistered.
    基 其 准备 甲 源. 折 其 登记直属 甲 父. 折 其 撤销直属 甲.
    共享 取 编 其 创建 父 实例 4.
    窗 其 发送 共享 2358 0 (窗 其 发送 甲 2357 0 0).
    窗 其 发送 共享 2359 3 0. 基 其 安装 共享.
    窗 其 成功 ((基 其 _SetWindowSubclass) 其 调用 [共享,子回调 其 地址,9919,0]) 'controlled shared-view observation'.
    共计 取 清计 共享. 折 其 排空 共享.
    确认 (共计['pointer'] == 0 且 共计['fold'] > 0 且 (基 其 同折 共享 甲)) 'actual shared document with an extra watcher remains on original messages'.
    折 其 遗忘 共享.
    窗 其 成功 ((基 其 _RemoveWindowSubclass) 其 调用 [共享,子回调 其 地址,9919]) 'remove shared observation'.
    窗 其 成功 ((窗 其 DestroyWindow) 其 调用 [共享]) 'destroy shared view'.

    态 取 就绪 甲 源. 折 其 登记直属 甲 父.
    甲计 取 清计 甲. 甲计 其 增 'mode' 'close'.
    拒借 甲 态 甲计 'real2185 close and recreation reject the stale borrowed context before any direct write'.
    丙 取 环境['recreated'].
    确认 (((折 其 _直属们) 其 查 (丙 其 句)) == 空 且 非 态['alive']) 'recreated HWND needs a fresh capability even if its numeric handle is recycled'.
    确认 (折 其 登记直属 丙 父) 'recreated exclusive editor can explicitly acquire its own new capability'.
    丙计 取 清计 丙. 折 其 排空 丙.
    确认 (丙计['pointer'] > 0 且 丙计['fold'] == 0 且 (编 其 文本 丙) == '# recreated\nbody\n' 且 非 (编 其 已变 丙)) 'recreated direct editor remains editable and publishes independently'.
    戊 取 编 其 创建 父 实例 6. 拖 其 启用编辑器 戊 父. 窗 其 发送 戊 2359 3 0.
    戊态 取 就绪 戊 源. 折 其 登记直属 戊 父.
    计划 取 (折 其 _批计划型) 其 新建. 结果存 取 (折 其 _批果型) 其 新建.
    字节数 取 折 其 _写批计划 计划 戊态 戊态['ranges'] 0 0.
    文档 取 (窗 其 PTR) 其 重释 (窗 其 发送 戊 2357 0 0).
    直 取 (窗 其 PTR) 其 重释 (窗 其 发送 戊 2185 0 0).
    原层 取 层快照 丙.
    折 其 遗忘 戊. 窗 其 成功 ((窗 其 DestroyWindow) 其 调用 [戊]) 'destroy before invalid-HWND helper test'.
    码 取 (窗 其 结果 ((折 其 _FoldApply) 其 调用 [戊,父,(折 其 _直库态)['module'],直,文档,戊态['length'],计划,字节数,结果存,32])) 其 数.
    确认 (码 == 2 且 (结果存 其 读 'attempted') 其 数 == 0 且 (结果存 其 读 'completed') 其 数 == 0 且 (层未变 丙 原层)) 'actual destroyed HWND rejects stale opaque context before any dereference or fold assignment'.
    直 取 空. 文档 取 空. 计划 其 关闭. 结果存 其 关闭.
    折 其 遗忘 丙. 折 其 遗忘 乙.
    确认 ((折 其 _批统计们) 其 量 == 0) 'forget removes all identity-bounded diagnostic counters without history growth'.
    确认 ((折 其 _直属们) 其 量 == 0 且 (折 其 _编辑们) 其 量 == 0) 'forget removes every owned capability and scan state'.
    窗 其 成功 ((基 其 _RemoveWindowSubclass) 其 调用 [丙,子回调 其 地址,9919]) 'remove recreated observation'.
    窗 其 成功 ((基 其 _RemoveWindowSubclass) 其 调用 [乙,子回调 其 地址,9919]) 'remove message observation'.
    窗 其 成功 ((窗 其 DestroyWindow) 其 调用 [父]) 'destroy direct Markdown parent'.
    窗 其 成功 ((窗 其 UnregisterClassW) 其 调用 [类名,实例]) 'unregister direct Markdown fixture'.
    类 其 关闭. 类名 其 关闭. 回调 其 关闭. 子回调 其 关闭.
    显 'TOTAL PASS: '+(次数[0] 为 句).
    得 0.
法
