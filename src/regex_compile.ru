# Bounded, nonrecursive Thompson compiler. Internal program arrays are private
# to this module and regex_vm.ru; callers must not mutate a compiled program.
# Work units count bounded parser, patch, emission and range operations, not
# elapsed time. Every loop is charged; compilation also has a hard 32768 cap.
# Unbounded repetition of nullable bodies is explicitly rejected; this
# avoids differing empty-iteration behavior between Pike and backtracking VMs.
# Query <=256 scalars implies <=1024 UTF-8 bytes. Native strings exclude NUL.
算 _错 程 码 位:
    若 程['status'] == 'ok' 则
        程 其 增 'status' 'error'. 程 其 增 'error' 码.
        程 其 增 'code' 码. 程 其 增 'index' 位.
    然.
    得 假.
法.
算 _计 程:
    若 程['status'] != 'ok' 则 得 假. 然.
    若 程['operations'] >= 32768 则 得 _错 程 'compile-limit' 程['cursor']. 然.
    程 其 增 'operations' (程['operations']+1). 得 真.
法.
算 _发 程 类 左 右 下 上 反:
    若 非 (_计 程) 则 得 -1. 然.
    位 取 程['count'].
    若 位 >= 512 则 _错 程 'state-limit' 程['cursor']. 得 -1. 然.
    程['op'] 其 增 类. 程['x'] 其 增 左. 程['y'] 其 增 右.
    程['lo'] 其 增 下. 程['hi'] 其 增 上. 程['neg'] 其 增 反.
    程['patch'] 其 增 (-1). 程['patch'] 其 增 (-1).
    程 其 增 'count' (位+1). 得 位.
法.
算 _补 程 头 目标:
    循
        若 头 < 0 或 程['status'] != 'ok' 则 破. 然.
        若 非 (_计 程) 则 破. 然.
        若 头 >= (程['patch'] 其 量) 则 _错 程 'internal-patch' 程['cursor']. 破. 然.
        后 取 程['patch'][头]. 分 取 头%2. 位 取 (头-分)/2.
        若 分 == 0 则 程['x'][位] 取 目标. 另 程['y'][位] 取 目标. 然.
        头 取 后.
    环.
    得 程.
法.
算 _并 程 左 右:
    若 非 (_计 程) 则 得 左. 然.
    若 左[1] < 0 则 得 右. 然.
    若 右[1] < 0 则 得 左. 然.
    若 左[2] < 0 或 左[2] >= (程['patch'] 其 量) 则
        _错 程 'internal-patch' 程['cursor']. 得 左.
    然.
    程['patch'][左[2]] 取 右[1]. 得 [左[0],左[1],右[2],(左[3] 或 右[3])].
法.
算 _归 程:
    若 非 (_计 程) 则 得 假. 然.
    若 (程['operators'] 其 量) == 0 或 (程['fragments'] 其 量) < 2 则
        得 _错 程 'missing-operand' 程['cursor'].
    然.
    运 取 程['operators'] 其 弹.
    右 取 程['fragments'] 其 弹. 左 取 程['fragments'] 其 弹.
    若 运 == '.' 则
        _补 程 左[1] 右[0]. 程['fragments'] 其 增 [左[0],右[1],右[2],(左[3] 且 右[3])].
    另
        位 取 _发 程 'split' 左[0] 右[0] 0 0 假.
        若 位 < 0 则 得 假. 然.
        合 取 _并 程 左 右. 程['fragments'] 其 增 [位,合[1],合[2],(左[3] 或 右[3])].
    然.
    得 程['status'] == 'ok'.
法.
算 _前 程:
    若 非 程['expect'] 则
        循
            若 (程['operators'] 其 量) == 0 则 破. 然.
            若 非 (_计 程) 则 得 假. 然.
            尾 取 (程['operators'] 其 量)-1.
            若 程['operators'][尾] != '.' 则 破. 然.
            若 非 (_归 程) 则 得 假. 然.
        环.
        程['operators'] 其 增 '.'.
    然.
    得 真.
法.
算 _项 程 类 下 上 反:
    若 非 (_前 程) 则 得 假. 然.
    位 取 _发 程 类 (-1) (-1) 下 上 反.
    若 位 < 0 则 得 假. 然.
    可空 取 类 == 'jump' 或 类 == 'bol' 或 类 == 'eol' 或 类 == 'absstart' 或 类 == 'absend'.
    程['fragments'] 其 增 [位,位*2,位*2,可空].
    程 其 增 'expect' 假. 程 其 增 'quantified' 假. 得 真.
法.
算 _空项 程:
    若 程['expect'] 则 得 _项 程 'jump' 0 0 假. 然.
    得 真.
法.
算 _范围 程 下 上:
    若 非 (_计 程) 则 得 假. 然.
    若 (程['rangesLo'] 其 量) >= 64 则 得 _错 程 'class-range-limit' 程['cursor']. 然.
    若 下 > 上 则 得 _错 程 'reversed-range' 程['cursor']. 然.
    程['rangesLo'] 其 增 下. 程['rangesHi'] 其 增 上. 得 真.
法.
# Built-in classes use only ASCII ordinal ranges. Complement ranges also make
# \D, \W and \S usable inside a bracket union without changing its negation.
算 _短类 程 字:
    若 字 == 'd' 则 _范围 程 '0' '9'.
    另若 字 == 'w' 则
        _范围 程 '0' '9'. _范围 程 'A' 'Z'. _范围 程 '_' '_'. _范围 程 'a' 'z'.
    另若 字 == 's' 则 _范围 程 '\t' '\r'. _范围 程 ' ' ' '.
    另若 字 == 'D' 则 _范围 程 '' '/'. _范围 程 ':' '􏿿'.
    另若 字 == 'W' 则
        _范围 程 '' '/'. _范围 程 ':' '@'. _范围 程 '[' '^'.
        _范围 程 '`' '`'. _范围 程 '{' '􏿿'.
    另若 字 == 'S' 则
        _范围 程 '' ''. _范围 程 '' ''. _范围 程 '!' '􏿿'.
    然.
    得 程['status'] == 'ok'.
法.
# Returns [kind,scalar]. The cursor advances only after bounds checks.
算 _转 程 类内:
    词 取 程['pattern']. 位 取 程['cursor'].
    若 位+1 >= (词 其 量) 则 _错 程 'trailing-escape' 位. 得 ['error','']. 然.
    字 取 词[位+1]. 程 其 增 'cursor' (位+2).
    若 字 == 'n' 则 得 ['char','\n']. 然.
    若 字 == 'r' 则 得 ['char','\r']. 然.
    若 字 == 't' 则 得 ['char','\t']. 然.
    若 字 == 'd' 或 字 == 'D' 或 字 == 'w' 或 字 == 'W' 或 字 == 's' 或 字 == 'S' 则 得 ['class',字]. 然.
    若 字 == '\\' 或 字 == '.' 或 字 == '^' 或 字 == '$' 或 字 == '|' 或 字 == '?' 或 字 == '*' 或 字 == '+' 或 字 == '(' 或 字 == ')' 或 字 == '[' 或 字 == ']' 或 字 == '{' 或 字 == '}' 或 字 == '-' 则 得 ['char',字]. 然.
    若 非 类内 且 字 == 'A' 则 得 ['absstart','']. 然.
    若 非 类内 且 字 == 'z' 则 得 ['absend','']. 然.
    _错 程 'unsupported-escape' 位. 得 ['error',''].
法.
算 _类字 程:
    位 取 程['cursor']. 词 取 程['pattern'].
    若 位 >= (词 其 量) 则 _错 程 'unclosed-class' 位. 得 ['error','']. 然.
    若 词[位] == '\\' 则 得 _转 程 真. 然.
    程 其 增 'cursor' (位+1). 得 ['char',词[位]].
法.
算 _类 程:
    词 取 程['pattern']. 开 取 程['cursor']. 位 取 开+1.
    反 取 假. 若 位 < (词 其 量) 且 词[位] == '^' 则 反 取 真. 位 取 位+1. 然.
    始 取 程['rangesLo'] 其 量. 程 其 增 'cursor' 位. 闭 取 假.
    循
        若 程['status'] != 'ok' 则 得 假. 然.
        若 非 (_计 程) 则 得 假. 然.
        位 取 程['cursor'].
        若 位 >= (词 其 量) 则 破. 然.
        若 词[位] == ']' 则 程 其 增 'cursor' (位+1). 闭 取 真. 破. 然.
        左 取 _类字 程.
        若 左[0] == 'error' 则 得 假. 然.
        位 取 程['cursor'].
        若 位+1 < (词 其 量) 且 词[位] == '-' 且 词[位+1] != ']' 则
            程 其 增 'cursor' (位+1). 右 取 _类字 程.
            若 右[0] == 'error' 则 得 假. 然.
            若 左[0] != 'char' 或 右[0] != 'char' 则 得 _错 程 'class-range-endpoint' 位. 然.
            若 左[1] > 右[1] 则 得 _错 程 'reversed-range' 位. 然.
            若 非 (_范围 程 左[1] 右[1]) 则 得 假. 然.
        另若 左[0] == 'class' 则
            若 非 (_短类 程 左[1]) 则 得 假. 然.
        另
            若 非 (_范围 程 左[1] 左[1]) 则 得 假. 然.
        然.
    环.
    若 非 闭 则 得 _错 程 'unclosed-class' 开. 然.
    数量 取 (程['rangesLo'] 其 量)-始.
    若 数量 == 0 则 得 _错 程 'empty-class' 开. 然.
    得 _项 程 'class' 始 数量 反.
法.
算 _量词 程 字:
    位 取 程['cursor'].
    若 程['expect'] 或 (程['fragments'] 其 量) == 0 则 得 _错 程 'missing-operand' 位. 然.
    若 程['quantified'] 则 得 _错 程 'repeated-quantifier' 位. 然.
    词 取 程['pattern']. 后 取 位+1. 懒 取 假.
    若 后 < (词 其 量) 且 词[后] == '?' 则 懒 取 真. 后 取 后+1. 然.
    若 后 < (词 其 量) 且 词[后] == '+' 则 得 _错 程 'possessive-quantifier' 后. 然.
    段 取 程['fragments'] 其 弹.
    若 字 != '?' 且 段[3] 则 得 _错 程 'nullable_repeat' 位. 然.
    左 取 段[0]. 右 取 -1.
    若 懒 则 左 取 -1. 右 取 段[0]. 然.
    新位 取 _发 程 'split' 左 右 0 0 假.
    若 新位 < 0 则 得 假. 然.
    洞 取 新位*2+1. 若 懒 则 洞 取 新位*2. 然.
    若 字 == '?' 则
        合 取 _并 程, 段, [新位,洞,洞,真].
        程['fragments'] 其 增 [新位,合[1],合[2],真].
    另
        _补 程 段[1] 新位. 始 取 新位. 若 字 == '+' 则 始 取 段[0]. 然.
        程['fragments'] 其 增 [始,洞,洞,(字 == '*' 或 段[3])].
    然.
    程 其 增 'cursor' 后. 程 其 增 'quantified' 真. 得 真.
法.
算 编译 词 为 句:
    程 取 {'status':'ok','error':'','code':'','index':-1,'operations':0,'op':[],'x':[],'y':[],'lo':[],'hi':[],'neg':[],'rangesLo':[],'rangesHi':[],'start':-1,'count':0,'patch':[],'operators':[],'fragments':[],'groups':[],'pattern':词,'query':词,'cursor':0,'expect':真,'quantified':假}.
    若 (词 其 量) == 0 则 _错 程 'empty-pattern' 0. 得 程. 然.
    若 (词 其 量) > 256 则 _错 程 'pattern-limit' 256. 得 程. 然.
    循
        若 程['status'] != 'ok' 或 程['cursor'] >= (词 其 量) 则 破. 然.
        若 非 (_计 程) 则 破. 然.
        位 取 程['cursor']. 字 取 词[位].
        若 字 == '(' 则
            若 (程['groups'] 其 量) >= 16 则 _错 程 'group-depth-limit' 位. 破. 然.
            若 非 (_前 程) 则 破. 然.
            后 取 位+1.
            若 后 < (词 其 量) 且 词[后] == '?' 则
                若 后+1 >= (词 其 量) 或 词[后+1] != ':' 则 _错 程 'unsupported-group' 位. 破. 然.
                后 取 后+2.
            然.
            程['operators'] 其 增 '('. 程['groups'] 其 增 位.
            程 其 增 'cursor' 后. 程 其 增 'expect' 真. 程 其 增 'quantified' 假.
        另若 字 == ')' 或 字 == '|' 则
            若 字 == ')' 且 (程['groups'] 其 量) == 0 则 _错 程 'unmatched-close' 位. 破. 然.
            若 非 (_空项 程) 则 破. 然.
            循
                若 程['status'] != 'ok' 或 (程['operators'] 其 量) == 0 则 破. 然.
                若 非 (_计 程) 则 破. 然.
                尾 取 (程['operators'] 其 量)-1.
                若 程['operators'][尾] == '(' 则 破. 然.
                若 非 (_归 程) 则 破. 然.
            环.
            若 程['status'] != 'ok' 则 破. 然.
            若 字 == ')' 则
                若 (程['operators'] 其 量) == 0 则 _错 程 'internal-group' 位. 破. 然.
                程['operators'] 其 弹. 程['groups'] 其 弹.
                程 其 增 'expect' 假.
            另
                程['operators'] 其 增 '|'. 程 其 增 'expect' 真.
            然.
            程 其 增 'quantified' 假. 程 其 增 'cursor' (位+1).
        另若 字 == '*' 或 字 == '+' 或 字 == '?' 则
            若 非 (_量词 程 字) 则 破. 然.
        另若 字 == '[' 则
            若 非 (_类 程) 则 破. 然.
        另若 字 == '\\' 则
            转 取 _转 程 假.
            若 转[0] == 'error' 则 破. 然.
            若 转[0] == 'class' 则
                始 取 程['rangesLo'] 其 量.
                若 非 (_短类 程 转[1]) 则 破. 然.
                _项 程 'class' 始 ((程['rangesLo'] 其 量)-始) 假.
            另若 转[0] == 'char' 则 _项 程 'char' 转[1] 0 假.
            另 _项 程 转[0] 0 0 假. 然.
        另若 字 == '{' 或 字 == '}' 则 _错 程 'counted-quantifier' 位. 破.
        另若 字 == ']' 则 _错 程 'unmatched-class-close' 位. 破.
        另
            若 字 == '.' 则 _项 程 'dot' 0 0 假.
            另若 字 == '^' 则 _项 程 'bol' 0 0 假.
            另若 字 == '$' 则 _项 程 'eol' 0 0 假.
            另 _项 程 'char' 字 0 假. 然.
            程 其 增 'cursor' (位+1).
        然.
    环.
    若 程['status'] != 'ok' 则 得 程. 然.
    若 (程['groups'] 其 量) > 0 则 _错 程 'unclosed-group' 程['groups'][0]. 得 程. 然.
    _空项 程.
    循
        若 程['status'] != 'ok' 或 (程['operators'] 其 量) == 0 则 破. 然.
        若 非 (_归 程) 则 破. 然.
    环.
    若 程['status'] != 'ok' 则 得 程. 然.
    若 (程['fragments'] 其 量) != 1 则 _错 程 'internal-fragment' 程['cursor']. 得 程. 然.
    段 取 程['fragments'][0]. 末 取 _发 程 'match' (-1) (-1) 0 0 假.
    若 末 < 0 则 得 程. 然.
    _补 程 段[1] 末. 程 其 增 'start' 段[0]. 程 其 增 'nullable' 段[3].
    # Drop compiler-only graphs after success; execution keeps bounded arrays.
    程 其 增 'patch', []. 程 其 增 'operators', []. 程 其 增 'fragments', [].
    程 其 增 'groups', []. 程 其 增 'pattern' ''. 得 程.
法.
