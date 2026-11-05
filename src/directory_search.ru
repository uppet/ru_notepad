# List-only disk search. Never opens editor documents or retains native pointers.
输 取 外言 'directory_io.ru'.
文 取 外言 'directory_text.ru'.
_全 取 {'generation':0,'job':空,'shutdown':假}.
算 初始化: 得 输 其 初始化. 法.
算 可用: 得 输 其 可用. 法.
算 选目录 主 标题: 得 输 其 选目录 主 标题. 法.
算 检查查询 词:
    若 (词 其 量) < 1 或 (词 其 量) > 256 则 得 {'status':'invalid-query','error':'invalid-query'}. 然.
    试
        得 文 其 编译 (输 其 转点 词).
    救 因
        得 {'status':'invalid-query','error':'invalid-query'}.
    终.
法.
算 _记 态 因:
    # Finite reason vocabulary, not attacker-controlled dictionary growth.
    键 取 因 为 句. 计 取 态['reasonCounts'].
    若 (计 其 查 键) != 空 则 计 其 增 键 (计[键]+1). 另 计 其 增 键 1. 然.
    态 其 增 'partial' 真. 得 态.
法.
算 _退 态:
    若 态['workerPending'] 则 输 其 释放 态['generation']. 然.
    态 其 增 'retiring' 真. 得 态.
法.
算 _错 态 因:
    若 态['current'] != 空 则 文 其 取消 态['current']. 然.
    态 其 增 'current' 空. 态 其 增 'data' 空.
    态 其 增 'status' 'failed'. 态 其 增 'error' 因.
    若 (态['reasonCounts'] 其 查 因) == 空 则 _记 态 因. 然.
    态 其 增 'partial' 真. 得 _退 态.
法.
算 维护:
    态 取 _全['job'].
    若 态 == 空 则 得 假. 然.
    若 态['workerPending'] 且 态['retiring'] 则
        输 其 释放 态['generation'].
        若 (输 其 生命周期) == 0 则 态 其 增 'workerPending' 假. 然.
    然.
    得 态['workerPending'].
法.
算 忙:
    若 维护 则 得 真. 然.
    得 (输 其 生命周期) != 0.
法.
算 新建 根 词:
    态 取 {'status':'failed','results':[],'root':根,'query':词,'generation':0,'filesSearched':0,'filesSkipped':0,'dirsSkipped':0,'rawBytes':0,'reasonCounts':{},'limitReason':'','error':'','workerPending':假,'retiring':假,'partial':假,'current':空,'data':空,'dataIndex':0,'publishIndex':0,'sequence':0,'fileSequence':0,'program':空,'lastRawBytes':0,'lastWork':0,'lastPublished':0,'emptyFinished':假,'observedFiles':0,'observedDirs':0,'observedSkipped':0,'observedErrors':0}.
    程 取 检查查询 词.
    若 程['status'] != 'ok' 则 态 其 增 'error' 'invalid-query'. 得 态. 然.
    若 忙 则 态 其 增 'error' 'directory-busy'. 得 态. 然.
    若 _全['shutdown'] 或 _全['generation'] >= 4294967295 则 态 其 增 'error' 'directory-generation-exhausted'. 得 态. 然.
    初始化.
    若 非 可用 则 态 其 增 'error' 初始化. 得 态. 然.
    代 取 _全['generation']+1. _全 其 增 'generation' 代. 态 其 增 'generation' 代.
    试
        码 取 输 其 开始 代 根.
        若 码 != 0 则
            若 码 == 2 或 码 == 6 则 态 其 增 'error' 'directory-busy'.
            另 态 其 增 'error' 'directory-start-failed'. 然.
            得 态.
        然.
    救 因
        态 其 增 'error' (因 为 句). 得 态.
    终.
    态 其 增 'program' 程. 态 其 增 'workerPending' 真. 态 其 增 'status' 'running'. _全 其 增 'job' 态. 得 态.
法.
算 取消 态:
    若 态 == 空 或 态['status'] != 'running' 则 得 态. 然.
    # Logical invalidation precedes any native call; committed files survive.
    态 其 增 'status' 'cancelled'. 态 其 增 'partial' 真.
    若 态['current'] != 空 则 文 其 取消 态['current']. 然.
    态 其 增 'current' 空. 态 其 增 'data' 空.
    输 其 取消 态['generation']. 得 _退 态.
法.
算 关停:
    _全 其 增 'shutdown' 真.
    态 取 _全['job'].
    若 态 != 空 则 取消 态. 输 其 放弃 态['generation'].
    另 输 其 放弃 0. 然.
    得 空.
法.
算 _文件退 态:
    态 其 增 'current' 空. 态 其 增 'data' 空. 态 其 增 'publishIndex' 0. 得 态.
法.
算 _核心 态:
    心 取 态['current'].
    若 心['status'] == 'running' 则
        文 其 步进 心 1024. 态 其 增 'lastWork' 心['lastWork']. 得 态.
    然.
    若 心['status'] == 'complete' 则
        # Core complete is the file commit point. Publish only validated rows,
        # capped separately; cancellation retains rows already published.
        若 非 态['fileCounted'] 则 态 其 增 'filesSearched' (态['filesSearched']+1). 态 其 增 'fileCounted' 真. 然.
        位 取 态['publishIndex']. 数 取 0.
        循 16 次
            若 位 >= (心['rows'] 其 量) 则 破. 然.
            态['results'] 其 增 心['rows'][位]. 位 取 位+1. 数 取 数+1.
        环.
        态 其 增 'publishIndex' 位. 态 其 增 'lastPublished' 数.
        若 位 == (心['rows'] 其 量) 则
            若 心['capReached'] 则
                态 其 增 'status' 'limited'. 态 其 增 'limitReason' 'rows'. _记 态 'rows'. _文件退 态. _退 态.
            另 _文件退 态. 然.
        然.
        得 态.
    然.
    若 心['status'] == 'error' 则 得 _错 态 心['reason']. 然.
    若 心['status'] == 'skipped' 则
        # Keep receiving/discarding this file until its terminal native event,
        # so a malformed text tail cannot desynchronize the transport.
        若 非 态['coreSkipped'] 则 _记 态 心['reason']. 态 其 增 'filesSkipped' (态['filesSkipped']+1). 态 其 增 'coreSkipped' 真. 然.
    然.
    得 态.
法.
算 步进 态:
    维护.
    若 态['status'] != 'running' 则 得 态. 然.
    若 态['generation'] != _全['generation'] 则 得 _错 态 'directory-generation'. 然.
    态 其 增 'lastRawBytes' 0. 态 其 增 'lastWork' 0. 态 其 增 'lastPublished' 0.
    试
        心 取 态['current'].
        若 心 != 空 则
            若 心['status'] == 'running' 或 心['status'] == 'complete' 则 得 _核心 态. 然.
            _核心 态.
            若 态['status'] != 'running' 则 得 态. 然.
            若 态['ended'] 且 态['coreSkipped'] 则 得 _文件退 态. 然.
        然.
        若 态['data'] != 空 则
            事 取 态['data']. 位 取 态['dataIndex']. 字节 取 输 其 数据 事 位.
            若 心 == 空 则 得 _错 态 'directory-data-without-file'. 然.
            若 非 态['coreSkipped'] 则 文 其 喂入 心 字节 (事['offset']+位). 然.
            态 其 增 'lastRawBytes' (字节 其 量). 位 取 位+(字节 其 量). 态 其 增 'dataIndex' 位.
            若 位 == 事['length'] 则 态 其 增 'data' 空. 然.
            得 态.
        然.
        事 取 输 其 轮询 态['generation'].
        若 事 == 空 则
            若 (输 其 生命周期) == 3 则
                若 态['emptyFinished'] 则 得 _错 态 'directory-missing-terminal'. 然.
                态 其 增 'emptyFinished' 真.
            然.
            得 态.
        然.
        态 其 增 'emptyFinished' 假.
        若 事['generation'] < 态['generation'] 则 得 态. 然.
        若 事['generation'] != 态['generation'] 则 得 _错 态 'directory-event-generation'. 然.
        若 事['sequence'] != 态['sequence']+1 则 得 _错 态 'directory-event-sequence'. 然.
        若 事['readBytes'] < 态['rawBytes'] 则 得 _错 态 'directory-read-counter'. 然.
        若 事['files'] < 态['observedFiles'] 或 事['dirs'] < 态['observedDirs'] 或 事['skipped'] < 态['observedSkipped'] 或 事['errors'] < 态['observedErrors'] 则 得 _错 态 'directory-event-counter-regression'. 然.
        态 其 增 'observedFiles' 事['files']. 态 其 增 'observedDirs' 事['dirs'].
        态 其 增 'observedSkipped' 事['skipped']. 态 其 增 'observedErrors' 事['errors'].
        态 其 增 'sequence' 事['sequence']. 态 其 增 'rawBytes' 事['readBytes'].
        种 取 事['kind']. 号 取 事['fileSequence'].
        若 种 == 1 则
            若 心 != 空 或 号 != 态['fileSequence']+1 则 得 _错 态 'directory-file-sequence'. 然.
            态 其 增 'fileSequence' 号. 态 其 增 'offset' 0. 态 其 增 'coreSkipped' 假. 态 其 增 'ended' 假. 态 其 增 'fileCounted' 假.
            心 取 文 其 新建 态['program'] 事 (2000-(态['results'] 其 量)).
            态 其 增 'current' 心. 态 其 增 'publishIndex' 0. 得 态.
        然.
        若 种 == 2 或 种 == 3 则
            若 心 == 空 或 号 != 态['fileSequence'] 或 事['rawSize'] != 心['metadata']['rawSize'] 或 事['identity'] != 心['metadata']['identity'] 或 事['stamp'] != 心['metadata']['stamp'] 或 事['path'] != 心['metadata']['path'] 或 事['offset'] != 态['offset'] 则 得 _错 态 'directory-file-offset'. 然.
            若 种 == 2 则
                若 态['offset']+事['length'] > 事['rawSize'] 则 得 _错 态 'directory-file-overrun'. 然.
                态 其 增 'offset' (态['offset']+事['length']). 态 其 增 'data' 事. 态 其 增 'dataIndex' 0.
            另
                若 事['offset'] != 事['rawSize'] 或 事['flags'] != 1 则 得 _错 态 'directory-end-size'. 然.
                态 其 增 'ended' 真.
                若 态['coreSkipped'] 则 _文件退 态.
                另 文 其 结束 心 真. 然.
            然.
            得 态.
        然.
        若 种 == 4 或 种 == 5 则
            若 事['flags'] >= 4 则
                若 号 != 0 则 得 _错 态 'directory-exclusion-scope'. 然.
                # File-entry exhaustion stops traversal; it is not an excluded directory.
                若 事['reason'] != 6 则 态 其 增 'dirsSkipped' (态['dirsSkipped']+1). 然.
                _记 态 ('native-'+(事['reason'] 为 句)).
                若 事['flags'] == 6 则 得 _错 态 ('native-'+(事['reason'] 为 句)). 然.
                得 态.
            然.
            若 (心 == 空 且 号 != 态['fileSequence']+1) 或 (心 != 空 且 号 != 态['fileSequence']) 则 得 _错 态 'directory-skip-sequence'. 然.
            若 号 == 态['fileSequence'] 且 心 == 空 则 态 其 增 'dirsSkipped' (态['dirsSkipped']+1).
            另 若 心 == 空 或 非 态['coreSkipped'] 则 态 其 增 'filesSkipped' (态['filesSkipped']+1). 然. 然.
            态 其 增 'fileSequence' 号. _记 态 ('native-'+(事['reason'] 为 句)).
            若 心 != 空 则 文 其 取消 心. _文件退 态. 然.
            若 种 == 5 且 事['flags'] == 2 则 得 _错 态 ('native-'+(事['reason'] 为 句)). 然.
            得 态.
        然.
        若 种 != 6 或 心 != 空 或 号 != 态['fileSequence'] 则 得 _错 态 'directory-job-end'. 然.
        态 其 增 'nativeFiles' 事['files']. 态 其 增 'nativeDirectories' 事['dirs']. 态 其 增 'nativeSkipped' 事['skipped']. 态 其 增 'nativeErrors' 事['errors'].
        若 事['status'] != 0 则
            态 其 增 'status' 'limited'. 态 其 增 'limitReason' ('native-'+(事['status'] 为 句)).
            若 (态['reasonCounts'] 其 查 态['limitReason']) == 空 则 _记 态 态['limitReason']. 然.
            态 其 增 'partial' 真.
        另 若 态['partial'] 则 态 其 增 'status' 'limited'. 态 其 增 'limitReason' 'exclusions'.
        另 态 其 增 'status' 'complete'. 然. 然.
        得 _退 态.
    救 因
        得 _错 态 (因 为 句).
    终.
法.
算 _转义 点:
    若 点 < 32 或 (点 >= 127 且 点 < 160) 或 (点 >= 8232 且 点 <= 8238) 或 (点 >= 8294 且 点 <= 8297) 或 点 == 1564 或 点 == 8206 或 点 == 8207 则 得 '�'. 然.
    得 输 其 文本 [点].
法.
算 行标签 行:
    路 取 行['path']. 若 (路 其 量) > 180 则 路 取 路[:179]+'…'. 然.
    点们 取 输 其 转点 路. 果 取 ''. 位 取 0.
    循 点们 其 量 次 果 取 果+(_转义 点们[位]). 位 取 位+1. 环.
    果 取 果+' : '+(行['line'] 为 句)+':'+(行['column'] 为 句)+' : '.
    若 行['previewLeadingTruncated'] 则 果 取 果+'…'. 然.
    位 取 0. 点们 取 行['previewScalars'].
    循 96 次
        若 位 >= (点们 其 量) 则 破. 然.
        果 取 果+(_转义 点们[位]). 位 取 位+1.
    环.
    若 行['previewMatchTruncated'] 则 果 取 果+'…'. 然.
    得 果.
法.
