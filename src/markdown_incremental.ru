# Bounded immutable checkpoints for same-line-count, single completed revisions.
# No text, native pointer or owner is retained. All 24 policy slots participate
# in convergence, except the independently translated UTF-8 byte coordinate.
算 复制 态:
    副本 取 []. 位 取 0.
    循 24 次 副本 其 增 态[位]. 位 取 位+1. 环
    栈 取 []. 位 取 0.
    循 态[3] 其 量 次
        项 取 态[3][位]. 栈 其 增 [项[0],项[1],项[2],项[3]]. 位 取 位+1.
    环
    副本[3] 取 栈. 旗 取 态[19]. 副本[19] 取 [旗[0],旗[1],旗[2],旗[3],旗[4]].
    得 副本.
法
算 同态 甲 乙:
    位 取 0.
    循 23 次
        若 位 != 3 且 位 != 19 且 甲[位] != 乙[位] 则 得 假. 然
        位 取 位+1.
    环
    若 (甲[3] 其 量) != (乙[3] 其 量) 则 得 假. 然
    位 取 0.
    循 甲[3] 其 量 次
        子 取 0.
        循 4 次 若 甲[3][位][子] != 乙[3][位][子] 则 得 假. 然 子 取 子+1. 环
        位 取 位+1.
    环
    位 取 0.
    循 5 次 若 甲[19][位] != 乙[19][位] 则 得 假. 然 位 取 位+1. 环
    得 真.
法
算 新缓存:
    得 {'points':[],'next':0,'ready':假,'length':0,'lines':0,'final':空,'base':空,'probe':0,'start':0,'delta':0,'reused':0,'dirtyEnd':0,'dirtyLine':2147483647}.
法
算 稳定 态:
    # A skipped suffix must have no deferred retroactive fold writes into its
    # prefix. Pending paragraphs and unconfirmed heading entries violate this.
    若 态[4] >= 0 则 得 假. 然
    位 取 0.
    循 态[3] 其 量 次
        若 非 态[3][位][3] 则 得 假. 然
        位 取 位+1.
    环
    得 真.
法
算 记点 缓 态 强制 为 事实:
    点们 取 缓['points']. 数量 取 点们 其 量. 位置 取 态[23].
    若 态[2] 或 非 (稳定 态) 或 数量 >= 128 或 (数量 > 0 且 点们[数量-1][0] == 位置) 则 得 空. 然
    若 非 强制 且 位置 < 缓['next'] 则 得 空. 然
    冻 取 复制 态. 冻[23] 取 0. 点们 其 增 [位置,冻].
    后 取 位置+16384. 若 位置 == 0 则 后 取 1024. 然
    缓 其 增 'next' 后.
    得 空.
法
算 修订 旧 位置 为 数 长度 为 数 加行 为 数 修改 为 数 待办 为 事实:
    副本 取 新缓存. 类 取 修改%4.
    若 旧 == 空 或 非 旧['ready'] 或 待办 或 加行 != 0 或 长度 <= 0 或 位置 < 0 或 (类 != 1 且 类 != 2) 则 得 副本. 然
    删末 取 位置. 差 取 长度.
    若 类 == 2 则 删末 取 位置+长度. 差 取 0-长度. 然
    若 删末 > 旧['length'] 则 得 副本. 然
    点们 取 旧['points']. 位 取 0. 起点 取 -1.
    循 点们 其 量 次
        若 点们[位][0] > 位置 则 破. 然
        起点 取 位. 位 取 位+1.
    环
    若 起点 < 0 则 得 副本. 然
    位 取 0.
    循 起点+1 次 副本['points'] 其 增 点们[位]. 位 取 位+1. 环
    副本 其 增 'base' 旧. 副本 其 增 'start' 点们[起点][0]. 副本 其 增 'delta' 差.
    脏末 取 位置. 若 类 == 1 则 脏末 取 位置+长度. 然
    副本 其 增 'dirtyEnd' 脏末.
    副本 其 增 'next' (点们[起点][0]+16384).
    若 点们[起点][0] == 0 则 副本 其 增 'next' 1024. 然
    循
        若 位 >= (点们 其 量) 则 破. 然
        若 点们[位][0] >= 删末 且 点们[位][0]+差 > 副本['start'] 则 破. 然
        位 取 位+1.
    环
    副本 其 增 'probe' 位.
    得 副本.
法
算 开始 缓 长 为 数 行数 为 数:
    旧 取 缓['base'].
    缓 其 增 'length' 长. 缓 其 增 'lines' 行数.
    若 旧 == 空 则 得 空. 然
    若 长 != 旧['length']+缓['delta'] 或 行数 != 旧['lines'] 则
        缓 其 增 'base' 空. 缓 其 增 'points' ([]). 缓 其 增 'next' 0. 得 空.
    然
    点们 取 缓['points']. 态 取 复制 点们[(点们 其 量)-1][1].
    态[23] 取 缓['start'].
    得 态.
法
算 读末 缓 始 为 数 末 为 数:
    旧 取 缓['base'].
    若 旧 != 空 且 缓['probe'] < (旧['points'] 其 量) 则
        目标 取 旧['points'][缓['probe']][0]+缓['delta'].
        若 目标 > 始 且 目标 < 末 则 得 目标. 然
    然
    得 末.
法
算 观察 缓 态:
    旧 取 缓['base'].
    若 旧 != 空 且 缓['probe'] < (旧['points'] 其 量) 则
        点 取 旧['points'][缓['probe']]. 目标 取 点[0]+缓['delta'].
        若 态[23] == 目标 则
            缓 其 增 'probe' (缓['probe']+1).
            # Scintilla may invalidate the edited line's native fold metadata.
            # Complete and publish that line before trusting a cached suffix.
            若 态[0] > 缓['dirtyLine'] 且 (同态 态 点[1]) 则
                记点 缓 态 真.
                位 取 缓['probe'].
                循
                    若 位 >= (旧['points'] 其 量) 或 (缓['points'] 其 量) >= 128 则 破. 然
                    点 取 旧['points'][位]. 缓['points'] 其 增 [点[0]+缓['delta'],点[1]]. 位 取 位+1.
                环
                缓 其 增 'reused' (缓['length']-态[23]). 缓 其 增 'base' 空.
                末态 取 复制 旧['final']. 末态[23] 取 缓['length'].
                得 末态.
            然
        然
    然
    记点 缓 态 假.
    得 空.
法
算 完成 缓 态:
    冻 取 复制 态. 冻[23] 取 0.
    缓 其 增 'final' 冻. 缓 其 增 'ready' 真. 缓 其 增 'base' 空.
    得 空.
法
