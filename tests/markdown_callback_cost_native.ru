# RESEARCH ONLY. Full unchanged application graph, real app-created editor and
# production file_drop callback. Never a product/runtime acceptance executable.
# The runner instruments exactly one production generated-C function entry and
# this fixture's counter stub; the uninstrumented fixture fails closed.
应用 取 外言 '../src/main.ru'.
窗 取 外言 '../src/win32.ru'.
编 取 外言 '../src/editor.ru'.
语 取 外言 '../src/syntax.ru'.
折 取 外言 '../src/markdown_syntax.ru'.
策 取 外言 '../src/markdown_policy.ru'.
拖 取 外言 '../src/file_drop.ru'.
密 取 外言 '如:密'.
_GetWindowSubclass 取 (窗 其 控件) 其 绑定 'GetWindowSubclass' (密 其 签名 (窗 其 I) ([(窗 其 PTR),(窗 其 PTR),(窗 其 UP),(窗 其 PTR)]) 'win64').
_引用型 取 密 其 结构 [['value',窗 其 UP]].
_固定键 取 ['identity','generation','revision','hwnd','thread','document','length','lines','alive','language','foldEnabled','registered','warning','pending','inTick','phase','policy','feed','readEnd','chunk','eof','chunks','readBytes','maxRead','maxRanges','maxTickMs','maxChunkMs','restart'].

算 研究计数:
    # Exact stub replaced only in the separately receipted research C unit.
    得 -1.
法
作 须 条件 为 事实 名 为 句:
    若 非 条件 则 卒 ('FAIL: callback research '+名). 然
为
算 语料:
    填 取 'code text\n'.
    循 17 次 填 取 填+填. 环
    得 '# Heading\n\n~~~\n'+填[:999977]+'codebody'.
法
算 策略预检 文 为 句:
    # Real policy output is derived before timing. Coalesce only adjacent,
    # identical nonheader ranges, retaining the exact ordered assignment stream.
    # This keeps three ranges, not 979 extra live heap objects, during callbacks.
    态 取 策 其 新状态. 范围 取 []. 位 取 0. 调用 取 0. 项数 取 0. 赋值 取 0.
    循
        末 取 位+1024. 若 末 > 文 其 量 则 末 取 文 其 量. 然
        果 取 策 其 喂入 态 文[位:末] (末 == 文 其 量).
        须 (果['used'] == 末-位 且 果['bytes'] == 末 且 果['finished'] == (末 == 文 其 量)) 'policy input contract'.
        列 取 果['folds']. 子 取 0.
        循 列 其 量 次
            项 取 列[子].
            若 赋值 < 2 则
                须 (项[0] == 0 且 项[1] == 1 且 项[2] == 0 且 项[3] == (赋值 == 1)) 'policy header assignments'.
            另
                须 (项[0] == 赋值-1 且 项[1] > 0 且 项[2] == 1 且 非 项[3]) 'policy body assignments'.
            然
            若 范围 其 量 == 3 则
                须 (项[0] == 范围[2][0]+范围[2][1] 且 项[2] == 1 且 非 项[3]) 'coalescing order'.
                范围[2][1] 取 范围[2][1]+项[1].
            另 范围 其 增 [项[0],项[1],项[2],项[3]]. 然
            赋值 取 赋值+项[1]. 项数 取 项数+1. 子 取 子+1.
        环
        资源 取 策 其 资源 态.
        须 (资源['stack'] <= 6 且 资源['prefix'] <= 32 且 资源['tail'] <= 11 且 资源['state'] == 24) 'bounded real policy'.
        调用 取 调用+1. 位 取 末.
        若 位 == 文 其 量 则 破. 然
    环
    须 (位 == 1000000 且 调用 == 977 且 项数 == 979 且 赋值 == 100002 且 范围 其 量 == 3 且 范围[2][0] == 1 且 范围[2][1] == 100000) 'exact policy workload'.
    得 [范围,态].
法
作 验路由 柄 父 在 为 事实:
    存 取 _引用型 其 新建.
    试
        果 取 窗 其 结果 (_GetWindowSubclass 其 调用 [柄,((拖 其 _子回调)[0] 其 地址),(拖 其 _子类编号),存]).
        须 ((非 (果 其 为空)) == 在) 'GetWindowSubclass presence'.
        若 在 则 须 ((存 其 读 'value') 其 句 == ((窗 其 UP) 其 重释 父) 其 句) 'GetWindowSubclass parent reference'. 然
    救 原因 存 其 关闭. 卒 原因. 终
    存 其 关闭.
为
作 移除 柄 父:
    验路由 柄 父 真.
    窗 其 成功 ((拖 其 _RemoveWindowSubclass) 其 调用 [柄,((拖 其 _子回调)[0] 其 地址),(拖 其 _子类编号)]) 'Remove owned research subclass'.
    验路由 柄 父 假.
为
作 恢复 柄 父:
    验路由 柄 父 假.
    窗 其 成功 ((拖 其 _SetWindowSubclass) 其 调用 [柄,((拖 其 _子回调)[0] 其 地址),(拖 其 _子类编号),((窗 其 UP) 其 重释 父)]) 'Restore owned research subclass'.
    验路由 柄 父 真.
为
算 固定快照 态:
    原 取 []. 位 取 0.
    循 _固定键 其 量 次 原 其 增 态[_固定键[位]]. 位 取 位+1. 环
    得 原.
法
算 策略快照 态:
    原 取 []. 位 取 0.
    循 24 次
        若 位 == 3 则
            栈 取 []. 层 取 0.
            循 态[3] 其 量 次
                项 取 态[3][层]. 栈 其 增 [项[0],项[1],项[2],项[3]]. 层 取 层+1.
            环
            原 其 增 栈.
        另
            若 位 == 19 则
                项 取 态[19]. 原 其 增 [项[0],项[1],项[2],项[3],项[4]].
            另 原 其 增 态[位]. 然
        然
        位 取 位+1.
    环
    得 原.
法
作 核策略 态 原:
    须 (态 其 量 == 24) 'batch complete policy size'. 位 取 0.
    循 24 次
        若 位 == 3 则
            须 (态[3] 其 量 == 原[3] 其 量) 'batch policy stack size'. 层 取 0.
            循 原[3] 其 量 次
                须 (态[3][层] 其 量 == 4) 'batch policy frame size'. 项 取 0.
                循 4 次 须 (态[3][层][项] == 原[3][层][项]) 'batch policy frame value'. 项 取 项+1. 环
                层 取 层+1.
            环
        另
            若 位 == 19 则
                须 (态[19] 其 量 == 5) 'batch policy flags size'. 项 取 0.
                循 5 次 须 (态[19][项] == 原[19][项]) 'batch policy flag value'. 项 取 项+1. 环
            另 须 (态[位] == 原[位]) 'batch policy scalar'. 然
        然
        位 取 位+1.
    环
为
作 核批 柄 态 原 原策 范围 已 为 数:
    # Fixed-size scalar/identity proof only; no native query, growing snapshots,
    # log strings, timers, or retained per-batch arrays in the measured loop.
    须 (态 其 量 == 33 且 ((折 其 _编辑们) 其 查 (柄 其 句)) == 态) 'batch owner'.
    位 取 0.
    循 _固定键 其 量 次 须 (态[_固定键[位]] == 原[位]) 'batch immutable state'. 位 取 位+1. 环
    核策略 态['policy'] 原策.
    须 (范围 其 量 == 3 且 范围[0] 其 量 == 4 且 范围[1] 其 量 == 4 且 范围[2] 其 量 == 4) 'batch range sizes'.
    须 (范围[0][0] == 0 且 范围[0][1] == 1 且 范围[0][2] == 0 且 非 范围[0][3] 且 范围[1][0] == 0 且 范围[1][1] == 1 且 范围[1][2] == 0 且 范围[1][3] 且 范围[2][0] == 1 且 范围[2][1] == 100000 且 范围[2][2] == 1 且 非 范围[2][3]) 'batch complete range values'.
    须 (态['published'] == 已 且 态['maxPublish'] == 64) 'batch publication counters'.
    若 已 == 100002 则
        须 (态['ranges'] 其 量 == 0 且 态['rangeIndex'] == 0 且 态['rangeOffset'] == 0) 'final range drain'.
    另
        须 (态['ranges'] == 范围 且 态['rangeIndex'] == 2 且 态['rangeOffset'] == 已-2) 'batch exact range cursor'.
    然
为
作 核全文 柄 页 文 为 句:
    须 ((编 其 文本 柄) == 文 且 (窗 其 发送 柄 2183 0 0) 其 数 == 1000000 且 (窗 其 发送 柄 2154 0 0) 其 数 == 100001) 'complete text and line count'.
    须 (非 (编 其 已变 柄) 且 非 (应用 其 脏 页) 且 (页 其 查 'revision') == 0) 'dirty savepoint and revision'.
    须 ((窗 其 发送 柄 2009 0 0) 其 数 == 2 且 (窗 其 发送 柄 2008 0 0) 其 数 == 19) 'selection'.
    须 ((窗 其 发送 柄 2174 0 0) 其 数 == 0 且 (窗 其 发送 柄 2016 0 0) 其 数 == 0) 'empty undo and redo'.
    行 取 0.
    循 100001 次
        层 取 1025. 若 行 == 0 则 层 取 9216. 然
        须 ((窗 其 发送 柄 2223 行 0) 其 数 == 层) 'every final fold level'.
        须 ((窗 其 发送 柄 2228 行 0) 其 数 == 1 且 (窗 其 发送 柄 2230 行 0) 其 数 == 1) 'every visible expanded line'.
        行 取 行+1.
    环
    # No-op undo and redo additionally prove no publication-generated action.
    窗 其 发送 柄 2176 0 0. 窗 其 发送 柄 2011 0 0.
    须 ((编 其 文本 柄) == 文 且 非 (编 其 已变 柄) 且 (页 其 查 'revision') == 0) 'undo redo preserves all text'.
    须 ((窗 其 发送 柄 2009 0 0) 其 数 == 2 且 (窗 其 发送 柄 2008 0 0) 其 数 == 19 且 (窗 其 发送 柄 2174 0 0) 其 数 == 0 且 (窗 其 发送 柄 2016 0 0) 其 数 == 0) 'post undo redo selection and history'.
为
作 失败清理 主 柄 初:
    # Failure-only cleanup never asks to save or touches an unrelated window.
    # Restore the original callback before owned destruction whenever absent.
    存 取 _引用型 其 新建.
    果 取 窗 其 结果 (_GetWindowSubclass 其 调用 [柄,((拖 其 _子回调)[0] 其 地址),(拖 其 _子类编号),存]).
    存 其 关闭.
    若 果 其 为空 则 恢复 柄 主. 然
    验路由 初 主 真.
    应用 其 停止语法. (应用 其 A) 其 增 'ready' 假.
    文们 取 (应用 其 A) 其 查 'docs'. 位 取 0.
    循 文们 其 量 次 语 其 遗忘 (文们[位] 其 查 'editor'). 位 取 位+1. 环
    窗 其 成功 ((窗 其 DestroyWindow) 其 调用 [主]) 'Destroy owned failed research'.
为
算 元初 参数 为 句 阵:
    须 (参数 其 量 == 1) 'one mode argument'.
    模式 取 参数[0]. 须 (模式 == 'present' 或 模式 == 'absent') 'known mode'.
    须 (研究计数 >= 0) 'instrumented binary required'.
    文 取 语料. 预检 取 策略预检 文.
    主 取 应用 其 初始化 ([]) 假.
    初 取 应用 其 编辑柄.
    页 取 应用 其 新页 'callback-research.md' 文 65001 假 ''.
    柄 取 页 其 查 'editor'.
    试
        # Identical production initialization, live app graph, notification mask,
        # lexer, window ownership, document and preparation in both modes.
        须 (柄 其 句 != 初 其 句) 'separate app-created editor'.
        验路由 初 主 真. 验路由 柄 主 真.
        态 取 (折 其 _编辑们) 其 查 (柄 其 句).
        折 其 _一步 柄 态.
        须 (态['phase'] == 'scan' 且 态['published'] == 0 且 态['length'] == 1000000 且 态['lines'] == 100001) 'real preparation'.
        范围 取 预检[0].
        态 其 增 'ranges' 范围. 态 其 增 'policy' 预检[1].
        态 其 增 'feed' 1000000. 态 其 增 'readEnd' 1000000. 态 其 增 'eof' 真.
        态 其 增 'chunks' 977. 态 其 增 'readBytes' 1000000. 态 其 增 'maxRead' 1024. 态 其 增 'maxRanges' 3.
        窗 其 发送 柄 2160 2 19.
        原 取 固定快照 态. 原策 取 策略快照 态['policy'].
        若 模式 == 'absent' 则 移除 柄 主. 然
        验路由 柄 主 (模式 == 'present'). 验路由 初 主 真.
        已 取 0. 批 取 0. 回调数 取 0.
        起 取 折 其 时刻.
        循
            若 已 == 100002 则 破. 然
            数量 取 64. 若 100002-已 < 数量 则 数量 取 100002-已. 然
            前 取 研究计数.
            折 其 _发布 柄 态.
            后 取 研究计数.
            期 取 0. 若 模式 == 'present' 则 期 取 数量*3+7. 然
            须 (前 >= 0 且 后 >= 前 且 后-前 == 期) 'actual per-batch callback entries'.
            已 取 已+数量. 批 取 批+1. 回调数 取 回调数+后-前.
            核批 柄 态 原 原策 范围 已.
        环
        用时 取 (折 其 时刻)-起.
        须 (批 == 1563 且 用时 > 0 且 用时 <= 120000) 'bounded measured publication'.
        验路由 柄 主 (模式 == 'present'). 验路由 初 主 真.
        # Verification is deliberately outside timing with both measured editors'
        # routes absent; all three native properties are checked on every line.
        若 模式 == 'present' 则 移除 柄 主. 然
        折 其 _一步 柄 态.
        须 (非 态['pending'] 且 态['warning'] == '' 且 态['published'] == 100002) 'final publication completion'.
        核全文 柄 页 文.
        恢复 柄 主. 验路由 初 主 真.
        须 (((应用 其 A) 其 查 'errors') 其 量 == 0) 'no swallowed application error'.
        须 (应用 其 关程序) 'normal owned teardown'.
        须 (((应用 其 A) 其 查 'errors') 其 量 == 0) 'no teardown application error'.
        微秒 取 用时*1000. 微秒 取 微秒-微秒%1.
        显 ('MD_CALLBACK_RESULT mode='+模式+' elapsed_us='+(微秒 为 句)+' assignments='+(已 为 句)+' batches='+(批 为 句)+' callback_entries='+(回调数 为 句)+' verified_lines=100001 verified_bytes=1000000 state_checks=1563 route_restored=1 initial_route_untouched=1 text=1 folds=1 visible=1 expanded=1 dirty=1 selection=1 undo=1 teardown=1').
    救 原因
        试 失败清理 主 柄 初. 救 清因 显 'MD_CALLBACK_CLEANUP_FAILED'. 终
        卒 原因.
    终
    得 0.
法
