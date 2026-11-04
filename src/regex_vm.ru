# Bounded, case-sensitive Unicode scalar Pike VM. No native calls or recursion.
# API: 新建(program, scopeStart, scopeEnd, docLength, totalBudget),
# 喂入(state, chunk, absoluteStart, preceding, following, final), 步进(state,budget).
# All positions are absolute UTF-8 bytes. Context is a real adjacent scalar,
# or '' ONLY at the actual document edge. final means end of this search leg.
# Feed consecutive <=256-scalar/1024-byte chunks only on need-input. Never
# mutate a compiled program or VM state externally. NUL is not a Ru string.
# One operation is one bounded VM microstep (not one machine instruction).
# Each step performs at most budget microsteps; initialization and each class
# range comparison are resumable. Fixed field accesses are constant-sized;
# Ru string scalar indexing may scan at most this bounded 256-scalar chunk.
# feed/new-state do bounded argument/field validation, not NFA traversal.
# readCursor equals consumed cursor; real lookaround context is not consumed.
# Epsilon paths use ordered PC deduplication defensively. The compiler rejects
# nullable bodies under * or + rather than inventing empty-repeat loop semantics.

算 _错 态 码:
    态 其 增 'status' 'error'. 态 其 增 'error' 码. 得 态.
法.
算 _整数 值:
    得 值 >= 0 且 值 <= 9007199254740000 且 值 % 1 == 0.
法.
算 _宽 字:
    若 字 < '' 则 得 1. 然.
    若 字 < 'ࠀ' 则 得 2. 然.
    若 字 < '𐀀' 则 得 3. 然.
    得 4.
法.
算 新建 程, 始 为 数, 末 为 数, 文长 为 数, 总额 为 数:
    态 取 {'status':'need-input','error':'','start':-1,'end':-1,'cursor':始,'readCursor':始,'operations':0,'lastOperations':0,'program':程,'scopeStart':始,'scopeEnd':末,'docLength':文长,'totalBudget':总额,'phase':'init','init':0,'marks':[],'rootsPc':[],'rootsStart':[],'readyPc':[],'readyStart':[],'stackPc':[],'stackStart':[],'rootCount':0,'rootIndex':0,'readyCount':0,'readyIndex':0,'sp':0,'epoch':0,'spawned':假,'candidate':假,'candidateStart':-1,'candidateEnd':-1,'chunk':'','chunkIndex':0,'chunkLength':0,'previous':'','following':'','final':假,'fed':假,'char':'','width':0,'classPc':0,'classStart':0,'classIndex':0,'classEnd':0,'classHit':假}.
    若 非 (_整数 始) 或 非 (_整数 末) 或 非 (_整数 文长) 或 非 (_整数 总额) 或 始 > 末 或 末 > 文长 则 得 _错 态 'invalid-boundary'. 然.
    若 程['status'] != 'ok' 则 得 _错 态 'invalid-program'. 然.
    数目 取 程['count'].
    若 非 (_整数 数目) 或 数目 < 1 或 数目 > 512 则 得 _错 态 'invalid-program'. 然.
    若 非 (_整数 程['start']) 或 程['start'] >= 数目 则 得 _错 态 'invalid-program'. 然.
    若 (程['op'] 其 量) != 数目 或 (程['x'] 其 量) != 数目 或 (程['y'] 其 量) != 数目 或 (程['lo'] 其 量) != 数目 或 (程['hi'] 其 量) != 数目 或 (程['neg'] 其 量) != 数目 则 得 _错 态 'invalid-program'. 然.
    若 (程['rangesLo'] 其 量) > 64 或 (程['rangesLo'] 其 量) != (程['rangesHi'] 其 量) 则 得 _错 态 'invalid-program'. 然.
    得 态.
法.
算 喂入 态, 文 为 句, 始 为 数, 前 为 句, 后 为 句, 最终 为 事实:
    若 态['status'] != 'need-input' 则 得 _错 态 'feed-state'. 然.
    长 取 文 其 量.
    若 非 (_整数 始) 或 始 != 态['cursor'] 或 长 > 256 或 (前 其 量) > 1 或 (后 其 量) > 1 则 得 _错 态 'feed-boundary'. 然.
    若 (始 == 0 且 前 != '') 或 (始 > 0 且 前 == '') 则 得 _错 态 'feed-context'. 然.
    若 非 最终 且 (长 == 0 或 后 == '') 则 得 _错 态 'feed-boundary'. 然.
    若 最终 且 ((态['scopeEnd'] == 态['docLength'] 且 后 != '') 或 (态['scopeEnd'] < 态['docLength'] 且 后 == '')) 则 得 _错 态 'feed-context'. 然.
    若 态['fed'] 则
        若 前 != 态['previous'] 则 得 _错 态 'feed-context'. 然.
        若 长 > 0 则
            若 文[0] != 态['following'] 则 得 _错 态 'feed-context'. 然.
        另 得 _错 态 'feed-boundary'. 然.
    然.
    态 其 增 'chunk' 文. 态 其 增 'chunkLength' 长. 态 其 增 'chunkIndex' 0.
    态 其 增 'previous' 前. 态 其 增 'following' 后. 态 其 增 'final' 最终.
    态 其 增 'fed' 真. 态 其 增 'status' 'running'. 得 态.
法.
# Stack holds lower split branch first; top is always next highest priority.
# At most count+1 pending entries: each unique split increases stack by one.
算 _压 态 位 始:
    若 非 (_整数 位) 或 位 >= 态['program']['count'] 则 _错 态 'invalid-pc'. 得 假. 然.
    栈位 取 态['sp'].
    若 栈位 < 0 或 栈位 >= (态['stackPc'] 其 量) 则 _错 态 'stack-limit'. 得 假. 然.
    态['stackPc'][栈位] 取 位. 态['stackStart'][栈位] 取 始.
    态 其 增 'sp' (栈位+1). 得 真.
法.
算 _结果 态:
    若 态['candidate'] 则
        态 其 增 'start' 态['candidateStart']. 态 其 增 'end' 态['candidateEnd'].
        态 其 增 'status' 'match'.
    另 态 其 增 'status' 'no-match'. 然.
    得 态.
法.
算 _接续 态 位 始:
    若 非 (_整数 位) 或 位 >= 态['program']['count'] 则 得 _错 态 'invalid-pc'. 然.
    序 取 态['rootCount'].
    若 序 < 0 或 序 >= 态['program']['count'] 则 得 _错 态 'thread-limit'. 然.
    态['rootsPc'][序] 取 位. 态['rootsStart'][序] 取 始.
    态 其 增 'rootCount' (序+1). 得 态.
法.
算 _锚 态 种:
    位 取 态['cursor']. 前 取 态['previous']. 后 取 态['char'].
    若 种 == 'absstart' 则 得 位 == 0. 然.
    若 种 == 'absend' 则 得 位 == 态['docLength']. 然.
    若 种 == 'bol' 则 得 位 == 0 或 前 == '\n' 或 (前 == '\r' 且 后 != '\n'). 然.
    得 位 == 态['docLength'] 或 后 == '\r' 或 (后 == '\n' 且 前 != '\r').
法.
算 _一步 态:
    程 取 态['program']. 阶段 取 态['phase'].
    若 阶段 == 'init' 则
        # Reused vectors are allocated one slot per charged microstep.
        若 态['init'] <= 程['count'] 则
            态['marks'] 其 增 (-1). 态['rootsPc'] 其 增 0. 态['rootsStart'] 其 增 0.
            态['readyPc'] 其 增 0. 态['readyStart'] 其 增 0.
            态['stackPc'] 其 增 0. 态['stackStart'] 其 增 0.
            态 其 增 'init' (态['init']+1).
        另 态 其 增 'phase' 'position'. 然.
        得 态.
    然.
    若 阶段 == 'position' 则
        序 取 态['chunkIndex']. 长 取 态['chunkLength'].
        若 序 < 0 或 序 > 长 则 得 _错 态 'input-index'. 然.
        若 序 == 长 则
            若 非 态['final'] 则
                若 态['cursor'] >= 态['scopeEnd'] 则 得 _错 态 'feed-boundary'. 然.
                态 其 增 'status' 'need-input'. 得 态.
            然.
            若 态['cursor'] != 态['scopeEnd'] 则 得 _错 态 'feed-boundary'. 然.
            态 其 增 'char' 态['following']. 态 其 增 'width' 0.
        另
            字 取 态['chunk'][序]. 宽 取 _宽 字.
            若 态['cursor']+宽 > 态['scopeEnd'] 则 得 _错 态 'feed-boundary'. 然.
            态 其 增 'char' 字. 态 其 增 'width' 宽.
        然.
        态 其 增 'epoch' (态['epoch']+1). 态 其 增 'rootIndex' 0.
        态 其 增 'readyCount' 0. 态 其 增 'sp' 0.
        态 其 增 'spawned' 态['candidate']. 态 其 增 'phase' 'closure'. 得 态.
    然.
    若 阶段 == 'closure' 则
        若 态['sp'] == 0 则
            序 取 态['rootIndex'].
            若 序 < 态['rootCount'] 则
                若 序 < 0 或 序 >= 程['count'] 则 得 _错 态 'thread-index'. 然.
                _压 态 态['rootsPc'][序] 态['rootsStart'][序].
                态 其 增 'rootIndex' (序+1). 得 态.
            然.
            若 非 态['spawned'] 则
                态 其 增 'spawned' 真. _压 态 程['start'] 态['cursor']. 得 态.
            然.
            态 其 增 'phase' 'transition-start'. 得 态.
        然.
        序 取 态['sp']-1.
        若 序 < 0 或 序 >= (态['stackPc'] 其 量) 则 得 _错 态 'stack-index'. 然.
        位 取 态['stackPc'][序]. 始 取 态['stackStart'][序]. 态 其 增 'sp' 序.
        若 非 (_整数 位) 或 位 >= 程['count'] 则 得 _错 态 'invalid-pc'. 然.
        若 态['marks'][位] == 态['epoch'] 则 得 态. 然.
        态['marks'][位] 取 态['epoch']. 种 取 程['op'][位].
        若 种 == 'split' 则
            若 _压 态 程['y'][位] 始 则 _压 态 程['x'][位] 始. 然.
        另若 种 == 'jump' 则 _压 态 程['x'][位] 始.
        另若 种 == 'bol' 或 种 == 'eol' 或 种 == 'absstart' 或 种 == 'absend' 则
            若 _锚 态 种 则 _压 态 程['x'][位] 始. 然.
        另若 种 == 'match' 则
            # Retain acceptance, discard only lower-priority work. Higher
            # consuming threads already in ready remain live across ticks.
            态 其 增 'candidate' 真. 态 其 增 'candidateStart' 始.
            态 其 增 'candidateEnd' 态['cursor']. 态 其 增 'sp' 0.
            态 其 增 'phase' 'transition-start'.
        另若 种 == 'char' 或 种 == 'dot' 或 种 == 'class' 则
            序 取 态['readyCount'].
            若 序 >= 程['count'] 则 得 _错 态 'thread-limit'. 然.
            态['readyPc'][序] 取 位. 态['readyStart'][序] 取 始.
            态 其 增 'readyCount' (序+1).
        另 得 _错 态 'invalid-op'. 然.
        得 态.
    然.
    若 阶段 == 'transition-start' 则
        若 (态['candidate'] 且 态['readyCount'] == 0) 或 态['cursor'] == 态['scopeEnd'] 则 得 _结果 态. 然.
        态 其 增 'rootCount' 0. 态 其 增 'readyIndex' 0.
        态 其 增 'phase' 'transition'. 得 态.
    然.
    若 阶段 == 'transition' 则
        序 取 态['readyIndex'].
        若 序 == 态['readyCount'] 则 态 其 增 'phase' 'advance'. 得 态. 然.
        若 序 < 0 或 序 >= 程['count'] 则 得 _错 态 'thread-index'. 然.
        位 取 态['readyPc'][序]. 始 取 态['readyStart'][序].
        若 非 (_整数 位) 或 位 >= 程['count'] 则 得 _错 态 'invalid-pc'. 然.
        态 其 增 'readyIndex' (序+1). 种 取 程['op'][位]. 字 取 态['char'].
        若 种 == 'class' 则
            起 取 程['lo'][位]. 量 取 程['hi'][位].
            若 非 (_整数 起) 或 非 (_整数 量) 或 起+量 > (程['rangesLo'] 其 量) 则 得 _错 态 'class-index'. 然.
            态 其 增 'classPc' 位. 态 其 增 'classStart' 始.
            态 其 增 'classIndex' 起. 态 其 增 'classEnd' (起+量).
            态 其 增 'classHit' 假. 态 其 增 'phase' 'class'.
        另若 (种 == 'char' 且 字 == 程['lo'][位]) 或 (种 == 'dot' 且 字 != '\r' 且 字 != '\n') 则
            _接续 态 程['x'][位] 始.
        然.
        得 态.
    然.
    若 阶段 == 'class' 则
        序 取 态['classIndex'].
        若 序 < 态['classEnd'] 且 非 态['classHit'] 则
            若 序 < 0 或 序 >= (程['rangesLo'] 其 量) 则 得 _错 态 'class-index'. 然.
            若 态['char'] >= 程['rangesLo'][序] 且 态['char'] <= 程['rangesHi'][序] 则 态 其 增 'classHit' 真. 然.
            态 其 增 'classIndex' (序+1). 得 态.
        然.
        位 取 态['classPc'].
        若 态['classHit'] != 程['neg'][位] 则 _接续 态 程['x'][位] 态['classStart']. 然.
        态 其 增 'phase' 'transition'. 得 态.
    然.
    若 阶段 == 'advance' 则
        若 态['candidate'] 且 态['rootCount'] == 0 则 得 _结果 态. 然.
        若 态['width'] < 1 或 态['width'] > 4 则 得 _错 态 'input-width'. 然.
        态 其 增 'cursor' (态['cursor']+态['width']).
        态 其 增 'readCursor' 态['cursor']. 态 其 增 'previous' 态['char'].
        态 其 增 'chunkIndex' (态['chunkIndex']+1). 态 其 增 'phase' 'position'. 得 态.
    然.
    得 _错 态 'invalid-phase'.
法.
算 步进 态, 预算 为 数:
    态 其 增 'lastOperations' 0.
    若 态['status'] != 'running' 则 得 态. 然.
    若 非 (_整数 预算) 则 得 _错 态 'invalid-budget'. 然.
    循
        若 态['status'] != 'running' 或 态['lastOperations'] >= 预算 则 破. 然.
        若 态['operations'] >= 态['totalBudget'] 则 态 其 增 'status' 'limit'. 破. 然.
        态 其 增 'operations' (态['operations']+1).
        态 其 增 'lastOperations' (态['lastOperations']+1). _一步 态.
    环.
    得 态.
法.
