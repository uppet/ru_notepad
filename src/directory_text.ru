# Numeric streaming text policy. No native calls, strings-as-bytes, or full-file buffers.
# A step is one byte, scalar setup, KMP comparison/fallback, preview scalar,
# retained row, or commit reference. Public input copying is bounded at 512 bytes.
# Program and state are private after construction; new validates/copies program.
算 _整数 值:
    若 值 == 空 或 值 == 真 或 值 == 假 则 得 假. 然.
    得 值 >= 0 且 值 <= 9007199254740000 且 值%1 == 0.
法.
算 _宽 点:
    若 点 < 128 则 得 1. 然.
    若 点 < 2048 则 得 2. 然.
    若 点 < 65536 则 得 3. 然.
    得 4.
法.
算 编译 点们:
    程 取 {'status':'invalid-query','error':'invalid-query','scalars':[],'prefix':[],'utf8Bytes':0}.
    若 点们 == 空 则 得 程. 然.
    长 取 点们 其 量.
    若 长 < 1 或 长 > 256 则 得 程. 然.
    位 取 0. 宽 取 0.
    循 长 次
        点 取 点们[位].
        若 非 (_整数 点) 或 点 == 0 或 点 > 1114111 或 (点 >= 55296 且 点 <= 57343) 则 得 程. 然.
        宽 取 宽+(_宽 点). 程['scalars'] 其 增 点. 程['prefix'] 其 增 0. 位 取 位+1.
    环.
    若 宽 > 1024 则 得 程. 然.
    位 取 1. 匹 取 0.
    循 长-1 次
        循
            若 匹 == 0 则 破. 然.
            若 匹 < 0 或 匹 >= 长 则 得 程. 然.
            若 程['scalars'][位] == 程['scalars'][匹] 则 破. 然.
            匹 取 程['prefix'][匹-1].
        环.
        若 匹 < 0 或 匹 >= 长 则 得 程. 然.
        若 程['scalars'][位] == 程['scalars'][匹] 则 匹 取 匹+1. 然.
        程['prefix'][位] 取 匹. 位 取 位+1.
    环.
    程 其 增 'status' 'ok'. 程 其 增 'error' ''. 程 其 增 'utf8Bytes' 宽. 得 程.
法.
算 _止 态 状因 原因:
    态 其 增 'status' 状因. 态 其 增 'reason' 原因.
    态 其 增 'rows' ([]). 态 其 增 'pendingRows' ([]). 态 其 增 'commitRows' ([]).
    态 其 增 'retainedCount' 0. 态 其 增 'row' 空. 得 态.
法.
算 新建 程 元 额:
    态 取 {'status':'need-input','reason':'','metadata':{},'rawReceived':0,'rawConsumed':0,'utf8Bytes':0,'encoding':'pending','bom':假,'rows':[],'retainedCount':0,'capReached':假,'lastWork':0,'program':{},'slots':额,'chunk':[],'chunkIndex':0,'initial':[],'initialIndex':0,'phase':'byte','eof':假,'need':0,'acc':0,'minimum':0,'odd':-1,'high':0,'scalar':0,'match':0,'index':0,'line':1,'column':1,'lineStart':0,'previous':0,'points':[],'coordinates':[],'pendingRows':[],'commitRows':[],'commitIndex':0,'row':空,'copyIndex':0,'copyEnd':0,'queryCopy':0}.
    若 元 == 空 或 程 == 空 则 得 _止 态 'error' 'invalid-argument'. 然.
    若 元['path'] == 空 或 元['identity'] == 空 或 元['stamp'] == 空 则 得 _止 态 'error' 'invalid-argument'. 然.
    若 非 (_整数 额) 或 额 > 2000 则 得 _止 态 'error' 'invalid-argument'. 然.
    若 非 (_整数 元['generation']) 或 非 (_整数 元['fileSequence']) 或 非 (_整数 元['rawSize']) 或 元['rawSize'] > 8388608 则 得 _止 态 'error' 'invalid-argument'. 然.
    态 其 增 'metadata' {'generation':元['generation'],'fileSequence':元['fileSequence'],'path':元['path'],'rawSize':元['rawSize'],'identity':元['identity'],'stamp':元['stamp']}.
    若 程['status'] != 'ok' 或 程['scalars'] == 空 或 程['prefix'] == 空 则 得 _止 态 'error' 'invalid-argument'. 然.
    副 取 编译 程['scalars'].
    若 副['status'] != 'ok' 或 (程['prefix'] 其 量) != (副['prefix'] 其 量) 或 程['utf8Bytes'] != 副['utf8Bytes'] 则 得 _止 态 'error' 'invalid-argument'. 然.
    位 取 0.
    循 副['prefix'] 其 量 次
        若 程['prefix'][位] != 副['prefix'][位] 则 得 _止 态 'error' 'invalid-argument'. 然.
        位 取 位+1.
    环.
    态 其 增 'program' 副.
    若 额 == 0 则 态 其 增 'capReached' 真. 然.
    得 态.
法.
算 喂入 态 字节们 偏:
    若 态['status'] != 'need-input' 则 得 _止 态 'error' 'invalid-sequence'. 然.
    长 取 字节们 其 量.
    若 非 (_整数 偏) 或 偏 != 态['rawReceived'] 或 长 < 1 或 长 > 512 或 偏+长 > 态['metadata']['rawSize'] 则 得 _止 态 'error' 'invalid-argument'. 然.
    副 取 []. 位 取 0.
    循 长 次
        字 取 字节们[位].
        若 非 (_整数 字) 或 字 > 255 则 得 _止 态 'error' 'invalid-argument'. 然.
        副 其 增 字. 位 取 位+1.
    环.
    态 其 增 'chunk' 副. 态 其 增 'chunkIndex' 0. 态 其 增 'rawReceived' (偏+长). 态 其 增 'status' 'running'. 得 态.
法.
算 结束 态 有效:
    若 态['status'] != 'need-input' 则 得 _止 态 'error' 'invalid-sequence'. 然.
    若 有效 != 真 且 有效 != 假 则 得 _止 态 'error' 'invalid-argument'. 然.
    若 非 有效 则 得 _止 态 'skipped' 'changed-snapshot'. 然.
    若 态['rawReceived'] != 态['metadata']['rawSize'] 则 得 _止 态 'skipped' 'incomplete-file'. 然.
    态 其 增 'eof' 真. 态 其 增 'status' 'running'. 得 态.
法.
算 取消 态:
    若 态['status'] == 'complete' 或 态['status'] == 'skipped' 或 态['status'] == 'error' 或 态['status'] == 'cancelled' 则 得 态. 然.
    得 _止 态 'cancelled' ''.
法.
# Decide only after four initial bytes or actual EOF; UTF32 precedes UTF16.
算 _识 态:
    字 取 态['initial']. 长 取 字 其 量. 跳 取 0. 编码 取 'utf-8'.
    若 长 == 4 则
        若 (字[0] == 0 且 字[1] == 0 且 字[2] == 254 且 字[3] == 255) 或 (字[0] == 255 且 字[1] == 254 且 字[2] == 0 且 字[3] == 0) 则 得 _止 态 'skipped' 'unsupported-bom'. 然.
    然.
    若 长 >= 3 则
        若 字[0] == 239 且 字[1] == 187 且 字[2] == 191 则 跳 取 3. 然.
    然.
    若 长 >= 2 且 跳 == 0 则
        若 字[0] == 255 且 字[1] == 254 则 跳 取 2. 编码 取 'utf-16le'.
        另若 字[0] == 254 且 字[1] == 255 则 跳 取 2. 编码 取 'utf-16be'. 然.
    然.
    态 其 增 'encoding' 编码. 态 其 增 'bom' (跳 > 0). 态 其 增 'initialIndex' 跳. 得 态.
法.
算 _点 态 点:
    若 点 == 0 则 得 _止 态 'skipped' 'binary-nul'. 然.
    态 其 增 'scalar' 点. 态 其 增 'phase' 'scalar'. 得 态.
法.
算 _解 态 字:
    若 态['encoding'] == 'utf-8' 则
        若 态['need'] == 0 则
            若 字 < 128 则 得 _点 态 字. 然.
            若 字 >= 194 且 字 <= 223 则 态 其 增 'need' 1. 态 其 增 'acc' (字-192). 态 其 增 'minimum' 128.
            另若 字 >= 224 且 字 <= 239 则 态 其 增 'need' 2. 态 其 增 'acc' (字-224). 态 其 增 'minimum' 2048.
            另若 字 >= 240 且 字 <= 244 则 态 其 增 'need' 3. 态 其 增 'acc' (字-240). 态 其 增 'minimum' 65536.
            另 得 _止 态 'skipped' 'invalid-utf8'. 然.
        另
            若 字 < 128 或 字 > 191 则 得 _止 态 'skipped' 'invalid-utf8'. 然.
            点 取 态['acc']*64+字-128. 态 其 增 'acc' 点. 态 其 增 'need' (态['need']-1).
            若 态['need'] == 0 则
                若 点 < 态['minimum'] 或 点 > 1114111 或 (点 >= 55296 且 点 <= 57343) 则 得 _止 态 'skipped' 'invalid-utf8'. 然.
                得 _点 态 点.
            然.
        然.
        得 态.
    然.
    若 态['odd'] < 0 则 态 其 增 'odd' 字. 得 态. 然.
    单 取 态['odd']*256+字.
    若 态['encoding'] == 'utf-16le' 则 单 取 字*256+态['odd']. 然.
    态 其 增 'odd' (-1).
    若 态['high'] > 0 则
        若 单 < 56320 或 单 > 57343 则 得 _止 态 'skipped' 'invalid-utf16'. 然.
        点 取 65536+(态['high']-55296)*1024+单-56320. 态 其 增 'high' 0. 得 _点 态 点.
    然.
    若 单 >= 55296 且 单 <= 56319 则 态 其 增 'high' 单. 得 态. 然.
    若 单 >= 56320 且 单 <= 57343 则 得 _止 态 'skipped' 'invalid-utf16'. 然.
    得 _点 态 单.
法.
算 _一步 态:
    阶 取 态['phase'].
    若 阶 == 'byte' 则
        位 取 态['chunkIndex']. 长 取 态['chunk'] 其 量.
        若 非 (_整数 位) 或 位 > 长 或 长 > 512 则 得 _止 态 'error' 'invalid-argument'. 然.
        若 态['encoding'] == 'pending' 则
            若 (态['initial'] 其 量) == 4 或 (态['eof'] 且 位 == 长) 则 得 _识 态. 然.
            若 位 < 长 则
                态['initial'] 其 增 态['chunk'][位]. 态 其 增 'chunkIndex' (位+1). 态 其 增 'rawConsumed' (态['rawConsumed']+1). 得 态.
            然.
        另
            初 取 态['initialIndex'].
            若 非 (_整数 初) 或 初 > (态['initial'] 其 量) 则 得 _止 态 'error' 'invalid-argument'. 然.
            若 初 < (态['initial'] 其 量) 则
                字 取 态['initial'][初]. 态 其 增 'initialIndex' (初+1). 得 _解 态 字.
            然.
            若 位 < 长 则
                字 取 态['chunk'][位]. 态 其 增 'chunkIndex' (位+1). 态 其 增 'rawConsumed' (态['rawConsumed']+1). 得 _解 态 字.
            然.
        然.
        若 非 态['eof'] 则 态 其 增 'status' 'need-input'. 得 态. 然.
        若 态['need'] != 0 则 得 _止 态 'skipped' 'invalid-utf8'. 然.
        若 态['odd'] >= 0 或 态['high'] > 0 则 得 _止 态 'skipped' 'invalid-utf16'. 然.
        态 其 增 'phase' 'commit'. 得 态.
    然.
    若 阶 == 'scalar' 则
        点 取 态['scalar']. 前 取 态['previous']. 序 取 态['index'].
        若 前 == 10 或 (前 == 13 且 点 != 10) 则
            态 其 增 'line' (态['line']+1). 态 其 增 'column' 1. 态 其 增 'lineStart' 序.
        然.
        若 态['utf8Bytes']+(_宽 点) > 16777216 则 得 _止 态 'skipped' 'invalid-argument'. 然.
        槽 取 序%288. 坐槽 取 序%256.
        若 槽 < 0 或 槽 > (态['points'] 其 量) 或 坐槽 < 0 或 坐槽 > (态['coordinates'] 其 量) 则 得 _止 态 'error' 'invalid-argument'. 然.
        若 槽 == (态['points'] 其 量) 则 态['points'] 其 增 点. 另 态['points'][槽] 取 点. 然.
        坐 取 {'byte':态['utf8Bytes'],'line':态['line'],'column':态['column'],'lineStart':态['lineStart']}.
        若 坐槽 == (态['coordinates'] 其 量) 则 态['coordinates'] 其 增 坐. 另 态['coordinates'][坐槽] 取 坐. 然.
        态 其 增 'utf8Bytes' (态['utf8Bytes']+(_宽 点)). 态 其 增 'column' (态['column']+1). 态 其 增 'previous' 点.
        态 其 增 'phase' 'match'. 得 态.
    然.
    若 阶 == 'match' 则
        若 态['capReached'] 则 态 其 增 'phase' 'advance'. 得 态. 然.
        程 取 态['program']. 匹 取 态['match']. 长 取 程['scalars'] 其 量.
        若 非 (_整数 匹) 或 匹 >= 长 或 长 < 1 或 长 > 256 或 (程['prefix'] 其 量) != 长 则 得 _止 态 'error' 'invalid-argument'. 然.
        若 态['scalar'] != 程['scalars'][匹] 则
            若 匹 > 0 则
                后 取 程['prefix'][匹-1].
                若 非 (_整数 后) 或 后 >= 匹 则 得 _止 态 'error' 'invalid-argument'. 然.
                态 其 增 'match' 后. 得 态.
            然.
            态 其 增 'phase' 'advance'. 得 态.
        然.
        匹 取 匹+1. 态 其 增 'match' 匹.
        若 匹 != 长 则 态 其 增 'phase' 'advance'. 得 态. 然.
        始 取 态['index']+1-长. 槽 取 始%256.
        若 始 < 0 或 槽 < 0 或 槽 >= (态['coordinates'] 其 量) 则 得 _止 态 'error' 'invalid-argument'. 然.
        坐 取 态['coordinates'][槽]. 首 取 始-32.
        若 首 < 坐['lineStart'] 则 首 取 坐['lineStart']. 然.
        元 取 态['metadata'].
        行 取 {'generation':元['generation'],'fileSequence':元['fileSequence'],'path':元['path'],'identity':元['identity'],'stamp':元['stamp'],'encoding':态['encoding'],'bom':态['bom'],'startUtf8':坐['byte'],'endUtf8':态['utf8Bytes'],'line':坐['line'],'column':坐['column'],'previewScalars':[],'previewLeadingTruncated':(首 > 坐['lineStart']),'previewMatchTruncated':(长 > 64)}.
        态 其 增 'row' 行. 态 其 增 'copyIndex' 首. 态 其 增 'copyEnd' 始. 态 其 增 'queryCopy' 0. 态 其 增 'match' 0. 态 其 增 'phase' 'preview'. 得 态.
    然.
    若 阶 == 'preview' 则
        位 取 态['copyIndex'].
        若 位 < 态['copyEnd'] 则
            槽 取 位%288.
            若 位 < 0 或 槽 < 0 或 槽 >= (态['points'] 其 量) 则 得 _止 态 'error' 'invalid-argument'. 然.
            态['row']['previewScalars'] 其 增 态['points'][槽]. 态 其 增 'copyIndex' (位+1). 得 态.
        然.
        位 取 态['queryCopy']. 长 取 态['program']['scalars'] 其 量.
        若 位 < 0 或 位 > 长 则 得 _止 态 'error' 'invalid-argument'. 然.
        若 位 < 长 且 位 < 64 则
            态['row']['previewScalars'] 其 增 态['program']['scalars'][位]. 态 其 增 'queryCopy' (位+1). 得 态.
        然.
        态['pendingRows'] 其 增 态['row']. 态 其 增 'retainedCount' (态['retainedCount']+1). 态 其 增 'row' 空.
        若 态['retainedCount'] >= 态['slots'] 则 态 其 增 'capReached' 真. 然.
        态 其 增 'phase' 'advance'. 得 态.
    然.
    若 阶 == 'advance' 则 态 其 增 'index' (态['index']+1). 态 其 增 'phase' 'byte'. 得 态. 然.
    若 阶 == 'commit' 则
        位 取 态['commitIndex']. 长 取 态['pendingRows'] 其 量.
        若 非 (_整数 位) 或 位 > 长 或 长 > 2000 则 得 _止 态 'error' 'invalid-argument'. 然.
        若 位 < 长 则
            态['commitRows'] 其 增 态['pendingRows'][位]. 态 其 增 'commitIndex' (位+1). 得 态.
        然.
        态 其 增 'rows' 态['commitRows']. 态 其 增 'pendingRows' ([]). 态 其 增 'status' 'complete'. 得 态.
    然.
    得 _止 态 'error' 'invalid-sequence'.
法.
算 步进 态 预算:
    态 其 增 'lastWork' 0.
    若 非 (_整数 预算) 或 预算 < 1 或 预算 > 1024 则 得 _止 态 'error' 'invalid-argument'. 然.
    若 态['status'] != 'running' 则 得 态. 然.
    循 预算 次
        若 态['status'] != 'running' 则 破. 然.
        态 其 增 'lastWork' (态['lastWork']+1). _一步 态.
    环.
    得 态.
法.
