#!/usr/bin/env python3
"""Exact .6/batch-fast-path differential using real Ru, without native imports.

The unchanged C scanner only supplies actual lexical events. Both policies run
in the interpreter and ordinary generated host C. This is semantic and policy
evidence, not Windows FFI, Scintilla, GUI, or end-to-end performance evidence.
"""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import random
import re
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import test_ru_scan as scanner

BASE_COMMIT = 'a5f5fd825767cd5af662cba792f5ce352991c21e'
BASE_POLICY_BLOB = '876a99f76db706cfd76427b9341ee5f05180ce0d'
BASE_SOURCE_SHA256 = 'f78589e247186890855526f7bb3624d34e4004bb8fbc69587c96d38c826a602c'
BASE_TREE = 'e8a402fb3eb551bfe416b8aee0aaaf942d2d4f4a'
RU_COMMIT = '85c7821fda35aa79deeaf67b4d430f24ddd7f07f'
RU_TREE = 'a770e367e84d87a0d2fcb6d49ea6f06da2dbe4ba'
OUT = ROOT / 'build/policy-fast'
PLAN_PATH = ROOT/'tests/fixtures/ru_policy_fast_plan.json'
CANONICAL_PLAN_SHA256 = 'a712c3b5c70e5bfe4ae09900d928f594c2c88bb49448d40ca15422b09a015e90'
PLAN_CONTENT_SHA256 = '0183679cfac0583d3a160e7ab7549967fe6b53b87b605647f2da3ce09c171616'
EXPECTED_TOTALS = {'cases':196,'batches':19627,'events':2554,'context_transitions':21504}
q = scanner.q

def literal(value):
    if isinstance(value,str):
        return q(value)
    if isinstance(value,(list,tuple)):
        return '['+','.join(literal(item) for item in value)+']'
    return scanner.literal(value)
SCRIPT_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def git(path, *args):
    return subprocess.check_output(['git', '-C', str(path), *args], text=True,encoding='utf-8',stderr=subprocess.PIPE).strip()


def uncomment(source):
    return '\n'.join(line.strip() for line in source.splitlines()
                     if line.strip() and not line.lstrip().startswith('#'))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')


def plan_sha(value):
    # Preserve the exact batch-plan serialization used in the measured proof.
    return sha(json.dumps(value,separators=(',',':')).encode('utf-8'))


def public_plan():
    data = PLAN_PATH.read_bytes()
    assert sha(data) == CANONICAL_PLAN_SHA256, 'Unknown public synthetic input contract'
    plan = json.loads(data)
    assert sha(canonical_bytes(plan)) == PLAN_CONTENT_SHA256
    return plan


def verify_sources(baseline, ru_root):
    assert git(baseline, 'rev-parse', 'HEAD') == BASE_COMMIT
    assert git(baseline, 'rev-parse', 'HEAD^{tree}') == BASE_TREE
    assert git(baseline, 'rev-parse', 'HEAD:src/ru_lexical.ru') == BASE_POLICY_BLOB
    assert sha((baseline/'src/ru_lexical.ru').read_bytes()) == BASE_SOURCE_SHA256
    public_plan()
    assert not git(baseline, 'status', '--porcelain'), 'baseline must remain clean'
    assert git(ru_root, 'rev-parse', 'HEAD') == RU_COMMIT
    assert git(ru_root, 'rev-parse', 'HEAD^{tree}') == RU_TREE
    assert not git(ru_root, 'status', '--porcelain'), 'toolchain must remain clean'
    before = (baseline / 'src/ru_lexical.ru').read_text(encoding='utf-8')
    after = (ROOT / 'src/ru_lexical.ru').read_text(encoding='utf-8')
    for path in ('native/ru_scan.c', 'native/ru_scan.h', 'src/ru_native_syntax.ru',
                 'src/ru_syntax.ru', 'tests/ru_lexical_policy.ru'):
        assert (baseline / path).read_bytes() == (ROOT / path).read_bytes(), path
    verify_transition(before, after)
    verify_guard_rejections(before, after)
    return before, after


PREFIX_SOURCE = r'''    # Only this empty-context prefix skips _记词. Its accepted transitions
    # cannot create a frame/header. At the first other event, stop until the
    # next batch and let the unchanged regular loop own every structural rule.
    若 态[14] 其 量 == 0 且 态[12] 其 量 == 0 则
        循 事件 其 量 次
            项 取 事件[位].
            种 取 项[0].
            态[0] 取 项[3].
            态[1] 取 项[5].
            若 种 == 1 或 种 == 2 或 种 == 3 或 种 == 4 则
                词 取 0.
                若 种 == 1 或 种 == 4 则 词 取 项[1]. 然
                若 非 (词 == 0 或 词 == 9 或 词 == 100 或 词 == 117) 则 破. 然
                态[13] 取 词 == 100.
                态[15] 取 词.
                若 种 == 1 则
                    若 项[2] != 8 则
                        若 项[4] > 64 则 卒 'Ru native keyword correction exceeds 64 bytes.'. 然
                        _加色 色们 项[3] 项[4] 项[2].
                    然
                然
            另
                若 种 == 7 则
                    _行折 态 折们.
                    态[1] 取 项[5]+1. 态[16] 取 态[24].
                另 破. 然
            然
            位 取 位+1.
        环
    然
    # A stopped event is still unconsumed; only its same byte/line metadata
    # may be written twice. No token transition, correction or fold is replayed.
'''


def verify_transition(before, after):
    # The complete old grammar/pure scanner, regular batch loop, validation and
    # finalization are authoritative. Only the exact prefix and remaining loop
    # count below may differ, never the fallback's per-event statements.
    old_pre, old_rest = before.split('算 批处理 ', 1)
    new_pre, new_rest = after.split('算 批处理 ', 1)
    assert uncomment(old_pre) == uncomment(new_pre)
    start = '    位 取 0.\n    循 事件 其 量 次\n'
    assert old_rest.count(start) == 1
    expected = old_rest.replace(start, '    位 取 0.\n'+PREFIX_SOURCE+
                                '    循 ((事件 其 量)-位) 次\n',1)
    assert new_rest == expected, 'Original regular loop must be byte-identical except remaining count'
    condition = '词 == 0 或 词 == 9 或 词 == 100 或 词 == 117'
    updates = '态[13] 取 词 == 100.\n态[15] 取 词.'
    pure = uncomment(after.split('算 _记词 ',1)[1].split('若 待 其 量 > 0',1)[0])
    fast = uncomment(PREFIX_SOURCE)
    assert f'若 待 其 量 == 0 且 态[12] 其 量 == 0 则\n若 {condition} 则\n{updates}\n得 空.' in pure
    assert f'若 非 ({condition}) 则 破. 然\n{updates}' in fast
    # Correction and newline operations are byte-equivalent to original
    # blocks after indentation is normalized, not independently redefined.
    correction = "若 项[2] != 8 则\n若 项[4] > 64 则 卒 'Ru native keyword correction exceeds 64 bytes.'. 然\n_加色 色们 项[3] 项[4] 项[2].\n然"
    newline = '_行折 态 折们.\n态[1] 取 项[5]+1. 态[16] 取 态[24].'
    assert correction in fast and correction in uncomment(old_rest)
    assert newline in fast and newline in uncomment(old_rest)


GUARD_MUTATIONS = [
    ('词 == 0 或 词 == 9', '词 == 1 或 词 == 9'),
    ('态[13] 取 词 == 100.', '态[13] 取 真.'),
    ('态[15] 取 词.', '态[15] 取 0.'),
    ('态[14] 其 量 == 0 且 ', ''),
    (' 且 态[12] 其 量 == 0', ''),
    ('另 破. 然', '另 位 取 位+1. 然'),
    ('位 取 位+1.', '位 取 位+2.'),
    ('((事件 其 量)-位)', '((事件 其 量)+位)'),
    ('_记词 态 5 0 项[5]', '_记词 态 4 0 项[5]'),
    ('项[2] != 8', '项[2] == 8'),
    ('_行折 态 折们.', '_清疑头 态 折们.'),
    ('若 种 == 1 或 种 == 4 则 词 取 项[1]. 然', '词 取 项[1].'),
]


def verify_guard_rejections(before, after):
    prefix, batch = after.split('算 批处理 ',1)
    for old,new in GUARD_MUTATIONS:
        assert old in batch
        try:
            verify_transition(before,prefix+'算 批处理 '+batch.replace(old,new,1))
        except AssertionError:
            continue
        raise AssertionError(f'Invariant guard accepted mutation: {old} -> {new}')


def scan_chunks(sc, data, sizes, capacity):
    """Keep raw scanner styles; policy corrections must actually fill them."""
    state = sc.state()
    raw = bytearray([255]) * len(data)
    batches = []
    at = step = 0
    done = False
    while not done:
        size = sizes[step % len(sizes)]
        step += 1
        window = data[at:at + size]
        offset = 0
        eof = at + len(window) == len(data)
        while True:
            styles = (C.c_uint8 * (len(window) + 16))()
            events = (scanner.Event * capacity)()
            result = scanner.Result()
            status = sc.dll.ru_scan_feed(sc.config, state, window, len(window), offset,
                                        eof, styles, len(styles), events, capacity,
                                        C.byref(result))
            assert status in (0, 1) and result.events <= capacity
            assert result.bytes == result.start + result.styled
            raw[result.start:result.bytes] = bytes(styles[:result.styled])
            decoded = [[e.head & 255, e.head >> 8 & 255, e.head >> 16 & 255,
                        e.head >> 24 & 0xffffffff, e.tail & 0xffffffff, e.tail >> 32]
                       for e in events[:result.events]]
            batches.append([decoded, int(result.bytes), int(result.line), bool(result.done)])
            offset += result.consumed
            done = bool(result.done)
            if status == 0 or done:
                break
            assert result.consumed or result.styled or result.events
        assert offset == len(window)
        at += offset
    assert at == len(data) and 255 not in raw
    return bytes(raw), batches


def encode_batches(batches):
    """RLE only empty, non-EOF, constant-line batches; never merge API calls.

    Tag 0 contains an untouched batch. Tag 1 contains the previous byte offset,
    constant line, at most 16 cyclic byte increments, and exact repetition count.
    """
    encoded = []
    at = 0
    while at < len(batches):
        batch = batches[at]
        if batch[0] or batch[3]:
            encoded.append([0,batch]); at += 1; continue
        end = at+1
        while end < len(batches) and not batches[end][0] and not batches[end][3] and batches[end][2] == batch[2]:
            end += 1
        encoded.append([0,batch]); at += 1
        while at < end:
            differences = [batches[i][1]-batches[i-1][1] for i in range(at,end)]
            best = None
            for period in range(1,min(16,len(differences)//2)+1):
                pattern = differences[:period]
                count = period
                while count < len(differences) and differences[count] == pattern[count%period]:
                    count += 1
                if count >= period*2 and count >= 4 and (best is None or count-period > best[0]-len(best[1])):
                    best = count,pattern
            if best is None:
                encoded.append([0,batches[at]]); at += 1
            else:
                count,pattern = best
                encoded.append([1,batches[at-1][1],batch[2],pattern,count])
                at += count
    assert decode_batches(encoded) == batches, 'RLE must reconstruct every field and boundary exactly'
    return encoded


def decode_batches(encoded):
    out = []
    for row in encoded:
        if row[0] == 0:
            out.append(row[1])
        else:
            assert row[0] == 1 and 1 <= len(row[3]) <= 16 and row[4] > 0
            byte = row[1]
            for index in range(row[4]):
                byte += row[3][index%len(row[3])]
                out.append([[],byte,row[2],False])
    return out


def batch_digest(batches):
    digest = 0
    for events,byte,line,done in batches:
        for value in [len(events),byte,line,int(done)]+[value for event in events for value in event]:
            digest = (digest*257+value)%1000000007
    return digest


CHECKS = r'''
旧 取 外言 './baseline.ru'.
核数 取 [0,0,0,0].
作 必须 条件 文:
    若 非 条件 则 卒 ('FAIL: '+文). 然
为
算 列同 左 右:
    若 左 其 量 != 右 其 量 则 得 假. 然
    位 取 0.
    循 左 其 量 次
        若 非 (样式同 左[位] 右[位]) 则 得 假. 然
        位 取 位+1.
    环
    得 真.
法
作 果同 甲 乙 名:
    必须 ((列同 甲['spans'] 乙['spans']) 且 (列同 甲['folds'] 乙['folds']) 且 甲['bytes'] == 乙['bytes'] 且 甲['line'] == 乙['line']) (名+' exact ordered outputs').
为
作 涂色 色 果:
    位 取 0.
    循 果['spans'] 其 量 次
        项 取 果['spans'][位].
        字节 取 项[0].
        循 项[1] 次 色[字节] 取 项[2]. 字节 取 字节+1. 环
        位 取 位+1.
    环
为
作 记折 折 果:
    位 取 0.
    循 果['folds'] 其 量 次
        项 取 果['folds'][位].
        折 其 增 项[0] ([项[1],项[2]]).
        位 取 位+1.
    环
为
作 本例 名 文 原色 批们 期摘要:
    实摘要 取 0.
    甲 取 旧 其 新状态.
    乙 取 模 其 新状态.
    甲色 取 []. 乙色 取 []. 甲折 取 {}. 乙折 取 {}.
    位 取 0.
    循 原色 其 量 次
        甲色 其 增 (原色[位] 为 数). 乙色 其 增 (原色[位] 为 数).
        位 取 位+1.
    环
    位 取 0.
    循 批们 其 量 次
        批 取 批们[位].
        # Record the exact arguments immediately before every actual API call.
        实摘要 取 批摘要 ([批]) 实摘要.
        # Every batch is also an independent deep-checkpoint event replay.
        单甲 取 旧 其 快照 甲. 单乙 取 模 其 快照 乙.
        果甲 取 旧 其 批处理 甲 批[0] 批[1] 批[2] 批[3].
        果乙 取 模 其 批处理 乙 批[0] 批[1] 批[2] 批[3].
        必须 (模 其 等价 甲 乙) (名+' batch full state').
        果同 果甲 果乙 名.
        涂色 甲色 果甲. 涂色 乙色 果乙.
        记折 甲折 果甲. 记折 乙折 果乙.
        子 取 0.
        循 批[0] 其 量 次
            项 取 批[0][子].
            一甲 取 旧 其 批处理 单甲 ([项]) (项[3]+项[4]) 项[5] 假.
            一乙 取 模 其 批处理 单乙 ([项]) (项[3]+项[4]) 项[5] 假.
            必须 (模 其 等价 单甲 单乙) (名+' event full state').
            果同 一甲 一乙 名.
            核数[1] 取 核数[1]+1.
            子 取 子+1.
        环
        一甲 取 旧 其 批处理 单甲, [], 批[1], 批[2], 批[3].
        一乙 取 模 其 批处理 单乙, [], 批[1], 批[2], 批[3].
        果同 一甲 一乙 名.
        必须 ((模 其 等价 单甲 甲) 且 (模 其 等价 单乙 乙)) (名+' checkpoint event replay').
        核数[0] 取 核数[0]+1.
        位 取 位+1.
    环
    必须 (实摘要 == 期摘要) (名+' actual-call input checksum').
    纯 取 运行 文 127.
    必须 ((样式同 甲色 乙色) 且 (样式同 乙色 纯['styles'])) (名+' full UTF8 styles oracle').
    必须 ((折叠同 甲折 乙折) 且 (折叠同 乙折 纯['folds'])) (名+' full folds oracle').
    必须 (模 其 等价 甲 乙) (名+' final full state').
    重甲 取 旧 其 批处理 甲, [], 甲[0], 甲[1], 真.
    重乙 取 模 其 批处理 乙, [], 乙[0], 乙[1], 真.
    果同 重甲 重乙 名.
    必须 (重乙['spans'] 其 量 == 0 且 重乙['folds'] 其 量 == 0 且 (模 其 等价 甲 乙)) (名+' repeated EOF').
    核数[2] 取 核数[2]+1.
    显 'PASS CASE: '+名.
为
作 枚举 前文:
    基 取 旧 其 新状态.
    旧 其 扫描 基 (前文+'  ') 假.
    种 取 1.
    循 4 次
        码 取 0.
        循 256 次
            甲 取 旧 其 快照 基. 乙 取 模 其 快照 基.
            项 取 [种,码,8,基[0],1,基[1]].
            果甲 取 旧 其 批处理 甲 ([项]) (基[0]+1) 基[1] 假.
            果乙 取 模 其 批处理 乙 ([项]) (基[0]+1) 基[1] 假.
            必须 (模 其 等价 甲 乙) ('tag/context full state '+前文).
            果同 果甲 果乙 前文.
            若 码 == 0 或 码 == 9 或 码 == 100 或 码 == 117 则
                # Exercise the unchanged pure scanner after transport, too.
                果甲 取 旧 其 扫描 甲 'x=1.\n' 假.
                果乙 取 模 其 扫描 乙 'x=1.\n' 假.
                必须 (模 其 等价 甲 乙) ('mixed transport/pure full state '+前文).
                果同 果甲 果乙 前文.
            然
            核数[3] 取 核数[3]+1.
            码 取 码+1.
        环
        种 取 种+1.
    环
为
作 加批 列 块:
    位 取 0.
    循 块 其 量 次 列 其 增 块[位]. 位 取 位+1. 环
为
算 展批 码们:
    批们 取 []. 位 取 0.
    循 码们 其 量 次
        码 取 码们[位].
        若 码[0] == 0 则 批们 其 增 码[1]. 另
            必须 (码[0] == 1 且 码[3] 其 量 >= 1 且 码[3] 其 量 <= 16 且 码[4] > 0) 'RLE record contract'.
            字节 取 码[1]. 子 取 0.
            循 码[4] 次
                字节 取 字节+码[3][子%(码[3] 其 量)].
                批们 其 增 [[],字节,码[2],假].
                子 取 子+1.
            环
        然
        位 取 位+1.
    环
    得 批们.
法
算 批摘要 批们 摘要:
    位 取 0.
    循 批们 其 量 次
        批 取 批们[位].
        摘要 取 (摘要*257+(批[0] 其 量))%1000000007.
        摘要 取 (摘要*257+批[1])%1000000007.
        摘要 取 (摘要*257+批[2])%1000000007.
        末 取 0. 若 批[3] 则 末 取 1. 然
        摘要 取 (摘要*257+末)%1000000007.
        子 取 0.
        循 批[0] 其 量 次
            字 取 0.
            循 6 次
                摘要 取 (摘要*257+批[0][子][字])%1000000007.
                字 取 字+1.
            环
            子 取 子+1.
        环
        位 取 位+1.
    环
    得 摘要.
法
作 接批 甲 乙 甲色 乙色 甲折 乙折 批们:
    位 取 0.
    循 批们 其 量 次
        批 取 批们[位].
        果甲 取 旧 其 批处理 甲 批[0] 批[1] 批[2] 批[3].
        果乙 取 模 其 批处理 乙 批[0] 批[1] 批[2] 批[3].
        必须 (模 其 等价 甲 乙) 'edit replay full state'.
        果同 果甲 果乙 'edit replay'.
        涂色 甲色 果甲. 涂色 乙色 果乙.
        记折 甲折 果甲. 记折 乙折 果乙.
        位 取 位+1.
    环
为
算 制色 文:
    列 取 []. 位 取 0.
    循 文 其 量 次 列 其 增 (文[位] 为 数). 位 取 位+1. 环
    得 列.
法
作 改例 名 新文 原色 新色 前批 原批 新批:
    甲 取 旧 其 新状态. 乙 取 模 其 新状态.
    甲色 取 制色 原色. 乙色 取 制色 原色.
    甲折 取 {}. 乙折 取 {}.
    接批 甲 乙 甲色 乙色 甲折 乙折 前批.
    存甲 取 旧 其 快照 甲. 存乙 取 模 其 快照 乙.
    接批 甲 乙 甲色 乙色 甲折 乙折 原批.
    # Keep previously published folds: an edited suffix must issue any needed
    # retroactive correction for opener lines preceding the restored snapshot.
    甲色 取 制色 新色. 乙色 取 制色 新色.
    鲜甲 取 旧 其 新状态. 鲜乙 取 模 其 新状态.
    鲜甲折 取 {}. 鲜乙折 取 {}.
    接批 鲜甲 鲜乙 甲色 乙色 鲜甲折 鲜乙折 前批.
    接批 存甲 存乙 甲色 乙色 甲折 乙折 新批.
    纯 取 运行 新文 127.
    必须 ((样式同 甲色 乙色) 且 (样式同 乙色 纯['styles'])) (名+' edited full styles').
    必须 ((折叠同 甲折 乙折) 且 (折叠同 乙折 纯['folds'])) (名+' edited full folds with stale publication').
    接批 鲜甲 鲜乙 甲色 乙色 鲜甲折 鲜乙折 新批.
    必须 ((模 其 等价 存甲 鲜甲) 且 (模 其 等价 存乙 鲜乙)) (名+' edit checkpoint matches fresh full state').
    显 'PASS EDIT: '+名.
为
'''


CHECKS += r'''
作 边界步 甲 乙 批 期错 名:
    单甲 取 旧 其 快照 甲. 单乙 取 模 其 快照 乙.
    错甲 取 ['']. 错乙 取 [''].
    果甲 取 [{}]. 果乙 取 [{}].
    试 果甲[0] 取 旧 其 批处理 甲 批[0] 批[1] 批[2] 批[3]. 救 原因 错甲[0] 取 原因. 终
    试 果乙[0] 取 模 其 批处理 乙 批[0] 批[1] 批[2] 批[3]. 救 原因 错乙[0] 取 原因. 终
    必须 (错甲[0] == 期错 且 错乙[0] == 期错) (名+' exact failure').
    必须 (模 其 等价 甲 乙) (名+' boundary full state').
    若 期错 == '' 则
        果同 果甲[0] 果乙[0] 名.
        位 取 0.
        循 批[0] 其 量 次
            项 取 批[0][位].
            一甲 取 旧 其 批处理 单甲 ([项]) (项[3]+项[4]) 项[5] 假.
            一乙 取 模 其 批处理 单乙 ([项]) (项[3]+项[4]) 项[5] 假.
            必须 (模 其 等价 单甲 单乙) (名+' boundary event full state').
            果同 一甲 一乙 名.
            位 取 位+1.
        环
        一甲 取 旧 其 批处理 单甲, [], 批[1], 批[2], 批[3].
        一乙 取 模 其 批处理 单乙, [], 批[1], 批[2], 批[3].
        果同 一甲 一乙 名.
        必须 ((模 其 等价 单甲 甲) 且 (模 其 等价 单乙 乙)) (名+' boundary checkpoint replay').
    然
为
作 边界例 名 种子 期栈 期待 期模 步们:
    甲 取 旧 其 新状态. 乙 取 模 其 新状态.
    边界步 甲 乙 种子 '' 名.
    必须 (甲[12] 其 量 == 期栈 且 甲[14] 其 量 == 期待 且 甲[3] == 期模) (名+' asserted entry context').
    位 取 0.
    循 步们 其 量 次
        边界步 甲 乙 步们[位][0] 步们[位][1] 名.
        位 取 位+1.
    环
    显 'PASS BOUNDARY: '+名.
为
'''

def boundary_cases():
    def event(kind,code=0,offset=0,line=0,length=1,style=8):
        return [kind,code,style,offset,length,line]
    def batch(events=(),byte=0,line=0,eof=False):
        return [list(events),byte,line,eof]
    def seq(*items):
        return [event(kind,code,i,i//4,style=4 if kind==1 and code else 8)
                for i,(kind,code) in enumerate(items)]
    empty = batch()
    names = seq((1,0),(1,9),(2,32),(3,33),(4,117),(4,100))
    pending = batch([event(1,32,style=4)],1)
    stack = batch([event(4,103)],1)
    comment = batch([event(5)],1)
    finished = 'Ru lexical policy state is already finished.'
    unknown = 'Unknown Ru lexical event.'
    out = [
        ('empty-eof-finished',empty,0,0,0,[(empty,''),(batch(eof=True),''),(batch(eof=True),''),(empty,finished),(batch(names,eof=True),finished)]),
        ('whole-fast-batch',empty,0,0,0,[(batch(names,6,1),''),(batch(byte=6,line=1,eof=True),'')]),
        ('stop-first-open-close',empty,0,0,0,[(batch(seq((1,32),(1,0),(4,101),(1,18),(4,100),(1,26),(1,0)),7,1),''),(batch(byte=7,line=1,eof=True),'')]),
        ('stop-last-then-close',empty,0,0,0,[(batch(seq((1,0),(4,100),(4,103)),3),''),(batch(seq((4,104),(1,0),(1,9),(4,100)),4),''),(batch(byte=4,eof=True),'')]),
        ('newlines-between-fast',empty,0,0,0,[(batch(seq((1,0),(7,0),(1,9),(7,0),(2,0),(4,100)),6,2),''),(batch(byte=6,line=2,eof=True),'')]),
        ('pending-cleared-midbatch',pending,0,6,0,[(batch(seq((2,0),(1,0),(4,117),(4,100)),4),''),(batch(byte=4,eof=True),'')]),
        ('stack-cleared-midbatch',stack,1,0,0,[(batch(seq((4,104),(1,0),(1,9),(4,100)),4),''),(batch(byte=4,eof=True),'')]),
        ('commentcarry-empty-entry',comment,0,0,4,[(batch(seq((7,0),(7,0),(6,0),(1,0),(4,100)),5,2),''),(batch(byte=5,line=2,eof=True),'')]),
        ('prefix-before-comment',empty,0,0,0,[(batch(seq((1,0),(5,0),(7,0),(6,0),(1,0),(4,100)),6,1),''),(batch(byte=6,line=1,eof=True),'')]),
        ('unknown-first',empty,0,0,0,[(batch([event(99)],1),unknown)]),
        ('unknown-after-prefix',empty,0,0,0,[(batch(seq((1,0),(7,0),(99,0),(1,0)),4,1),unknown)]),
        ('oversized-fast-correction',empty,0,0,0,[(batch([event(1,length=65,style=4)],65),'Ru native keyword correction exceeds 64 bytes.')]),
        ('overfull-batch',empty,0,0,0,[(batch([event(1)]*65,65),'Ru lexical event batch exceeds 64 events.')]),
    ]

    return [(name,seed,stack,pending,mode,[[batch,error] for batch,error in steps])
            for name,seed,stack,pending,mode,steps in out]


def cases():
    out = scanner.fixtures()
    rng = random.Random(0x213)
    atoms = ['算','作','为','若','然','真','取','得','典','成','段','落','终','解.',
             '释。','批.','#','//',"'",'“','”','\\','1e-2','0x12','(',')','[',']',
             '{','}',':',',','.','_x','é٢','𐐀','😀','\n','\r','\t',' ']
    for i in range(100):
        out.append((f'fuzz-{i}', ''.join(rng.choice(atoms) for _ in range(rng.randrange(1,45)))))
    assert len(out) == 157
    out += [
        ('fast-state-reset', '为 x 算 F:\n得 1.\n法\n为 1 算 G:1.\n为 "x" 算 H:1.\n'),
        ('fast-boundary-reset', '. x 若 真 则\n. = 若 真 则\n. 取 若 真 则\n'),
        ('pending-fast-codes', '算 F x = 1.\n作 P x 取 1.\n段 取 1.\n典 取 2.\n形 X 如 Y:\n象\n'),
        ('same-batch-stack-changes', 'a=1. 若 真 则 x=2. 然 z=3. (4) [5] {6} a=7.\n'),
        ('procedure-closer-reset', '作 P:\n完.\n为 x 取 1.\n算 F:\n得 2.\n法\n'),
        ('delayed-keyword-and-name', '算'+('甲'*2048)+' 取 1.\n__实用 取 2.\n'),
        ('delayed-header-name', '算 F '+('值'*2048)+' 为 数:\n得 1.\n法\n'),
        ('comment-string-stack', '若 真 则 解.\r\n释. x="a\\\\b". 然\n"若 真 则". 解.\n释. a=1.\n'),
        ('same-line-retroactive-proof', '若 真 则 算 回 值:\n得 值.\n法\n然\n'),
        ('same-line-retroactive-revoke', '若 真 则 算 回 值:\n1.\n然\n'),
        ('same-line-comment-revoke', '算 回 值: 解.\n释. 1.\n'),
        ('unfinished-delayed-token', '为 '+('界'*1500)),
        ('unfinished-pending-header', '算 F 参数 为 '),
    ]
    return out


STAGE = 'startup'
FAILURE_CODE = 'validation'
CREATED_OUTPUT = False


def run(command, label, timeout=900, expected_lines=None):
    """Keep all raw compiler output private; publish only exact successful stdout."""
    global STAGE, FAILURE_CODE
    STAGE = label
    start = time.monotonic()
    try:
        result = subprocess.run(list(map(str, command)), cwd=ROOT, capture_output=True,
                                timeout=timeout)
    except subprocess.TimeoutExpired as error:
        (OUT/'evidence'/f'{label}.stdout.log').write_bytes(error.stdout or b'')
        (OUT/'evidence'/f'{label}.stderr.log').write_bytes(error.stderr or b'')
        FAILURE_CODE = 'timeout'
        raise
    (OUT/'evidence'/f'{label}.stdout.log').write_bytes(result.stdout)
    (OUT/'evidence'/f'{label}.stderr.log').write_bytes(result.stderr)
    if result.returncode:
        FAILURE_CODE = 'command'
        raise RuntimeError('Subprocess failed: '+str(result.returncode))
    output = result.stdout.decode('utf-8')
    if expected_lines is not None:
        expected = ('\n'.join(expected_lines)+'\n').encode('utf-8')
        assert result.stdout == expected and not result.stderr, 'Unexpected backend output'
        (OUT/f'{label}.log').write_bytes(result.stdout)
    return output, round(time.monotonic()-start, 3)


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        global FAILURE_CODE
        FAILURE_CODE = 'usage'
        raise ValueError(message)


def progress(text):
    with (OUT/'evidence/progress.log').open('a',encoding='utf-8',newline='\n') as stream:
        stream.write(text+'\n')


def main():
    global STAGE, CREATED_OUTPUT
    if sys.flags.optimize:
        raise ValueError("Policy proof requires active assertions")
    parser = SafeParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--ru-root', type=Path, required=True)
    args = parser.parse_args()
    baseline, ru_root = args.baseline.resolve(), args.ru_root.resolve()
    STAGE = 'fresh-output'
    OUT.mkdir(parents=True, exist_ok=False)
    CREATED_OUTPUT = True
    (OUT / 'evidence').mkdir()
    STAGE = 'source-guards'
    before, after = verify_sources(baseline, ru_root)
    progress('SOURCE_GUARDS_PASS mutations='+str(len(GUARD_MUTATIONS)))
    (OUT / 'baseline.ru').write_text(before, encoding='utf-8',newline='\n')
    library = OUT / 'libRuSyntax.so'
    run(['gcc','-std=c99','-O2','-Wall','-Wextra','-Werror','-fPIC','-shared',
         ROOT/'native/ru_scan.c','-o',library], 'scanner-build')
    sc = scanner.Scanner(library)
    helper = (ROOT/'tests/ru_lexical_policy.ru').read_text(encoding='utf-8').split('作 核例',1)[0]
    helper = helper.replace("'../src/ru_lexical.ru'", q(str(ROOT/'src/ru_lexical.ru')))
    source = helper + CHECKS
    STAGE = 'fixture-generation'
    corpus = cases()
    rng = random.Random(0xF457)
    totals = {'cases':0, 'batches':0, 'events':0, 'context_transitions':0}
    encoded_count = 0
    manifest = []
    case_sources = []
    case_totals = []
    for index, (name, text) in enumerate(corpus):
        # Each input has independently randomized byte windows and capacities,
        # plus a one-byte/event-tight pass for explicit adversarial cases.
        schedules = [([rng.randint(1,41) for _ in range(23)], [8,16,64][index%3])]
        if index >= 157:
            schedules += [([1],8), ([1024],64)]
        for trial, (sizes, capacity) in enumerate(schedules):
            raw, batches = scan_chunks(sc, text.encode(), sizes, capacity)
            unit = totals['cases']
            encoded = encode_batches(batches)
            decoded = decode_batches(encoded)
            manifest.append({'case':name+'/'+str(trial),'original_batch_count':len(batches),
                             'encoded_records':len(encoded),'original_plan_sha256':plan_sha(batches),
                             'expanded_plan_sha256':plan_sha(decoded),'ru_input_checksum':batch_digest(batches),
                             'input_utf8_sha256':sha(text.encode('utf-8')),
                             'raw_scanner_styles_sha256':sha(raw),'byte_window_sizes':sizes,
                             'event_capacity':capacity,'events':sum(len(batch[0]) for batch in batches)})
            encoded_count += len(encoded)
            block_start = len(source)
            # Bound each native optimizer unit, including long one-byte feeds.
            for part in range(0,len(encoded),64):
                source += f'算 案{unit}块{part}: 得 {literal(encoded[part:part+64])}. 法\n'
            source += f'作 案{unit}:\n    批们 取 [].\n'
            for part in range(0,len(encoded),64):
                source += f'    加批 批们 (案{unit}块{part}).\n'
            source += f'    本例 {q(name+"/"+str(trial))}, {q(text)}, {q("".join(map(str,raw)))}, (展批 批们), {batch_digest(batches)}.\n为\n'
            case_sources.append(source[block_start:])
            case_totals.append({'cases':1,'batches':len(batches),'events':sum(len(batch[0]) for batch in batches),'context_transitions':0})
            totals['cases'] += 1
            totals['batches'] += len(batches)
            totals['events'] += sum(len(batch[0]) for batch in batches)
    for i in range(totals['cases']):
        source += f'案{i}.\n'
    extras_start = len(source)
    edits = [
        ('proof-revoke','算 回 值:\n','得 值.\n法\n','1.\n\n'),
        ('proof-add','算 回 值:\n','1.\n\n','得 值.\n法\n'),
        ('shared-if-proof-revoke','若 真 则 算 回 值:\n','得 值.\n法\n然\n','1.\n\n然\n'),
        ('shared-comment-proof-revoke','算 回 值: 解.\n释. ','得 值.\n法\n','1.\n\n'),
    ]
    edit_manifest = []
    for name,prefix,old,new in edits:
        cut = len(prefix.encode())
        old_raw, old_batches = scan_chunks(sc,(prefix+old).encode(),[cut,13],64)
        new_raw, new_batches = scan_chunks(sc,(prefix+new).encode(),[cut,13],64)
        # These bounded prefixes fit one feed. Preserve its non-EOF snapshot,
        # including any pending lexical token carried into either edited suffix.
        assert old_batches[0] == new_batches[0] and not old_batches[0][3]
        edit_manifest.append({'case':name,'prefix_utf8_bytes':cut,
            'original_input_utf8_sha256':sha((prefix+old).encode('utf-8')),
            'edited_input_utf8_sha256':sha((prefix+new).encode('utf-8')),
            'original_raw_styles_sha256':sha(old_raw),'edited_raw_styles_sha256':sha(new_raw),
            'original_plan_sha256':plan_sha(old_batches),'edited_plan_sha256':plan_sha(new_batches),
            'shared_first_batch_sha256':plan_sha(old_batches[:1]),
            'byte_window_sizes':[cut,13],'event_capacity':64})
        source += ('改例 '+q(name)+', '+q(prefix+new)+', '+q(''.join(map(str,old_raw)))+', '
                   +q(''.join(map(str,new_raw)))+', '+literal(old_batches[:1])+', '
                   +literal(old_batches[1:])+', '+literal(new_batches[1:])+'.\n')
    contexts = ['', '为', 'x', '1', '"s"', '.', '=', '取', '算 F', '算 F x 为',
                '作 P', '段', '典', '形 X 如', '若 真 则', '(', '[', '{',
                '回 取 算 值:', '试:\n救 原因:', '算 回 值: 解.\n释.']
    for prefix in contexts:
        source += f'枚举 {q(prefix)}.\n'
        totals['context_transitions'] += 1024
    boundary = boundary_cases()
    for name,seed,stack,pending,mode,steps in boundary:
        source += f'边界例 {q(name)}, {literal(seed)}, {stack}, {pending}, {mode}, {literal(steps)}.\n'
    extras = source[extras_start:]
    summary_source = "显 'POLICY_FAST_PASS batches='+(核数[0] 为 句)+' events='+(核数[1] 为 句)+' cases='+(核数[2] 为 句)+' transitions='+(核数[3] 为 句).\n"
    source += summary_source
    probe = OUT/'differential.ru'
    probe.write_text(source, encoding='utf-8',newline='\n')
    actual_plan = {'schema_version':1,'totals_per_backend':totals,'cases':manifest,
        'edits':edit_manifest,'contexts':{'prefixes':contexts,'nonfinal_scan_suffix':'  ',
                                        'event_kinds':[1,2,3,4],'codes':list(range(256))},
        'boundaries':[{'case':name,'seed_batch':seed,'expected_stack_length':stack,
                      'expected_pending_length':pending,'expected_lexical_mode':mode,'steps':steps}
                     for name,seed,stack,pending,mode,steps in boundary],
        'source_guard_mutations':[[old,new] for old,new in GUARD_MUTATIONS]}
    assert actual_plan == public_plan(), 'Actual generated inputs differ from frozen public contract'
    assert sha(canonical_bytes(actual_plan)) == PLAN_CONTENT_SHA256
    assert totals == EXPECTED_TOTALS and len(edits) == 4 and len(boundary) == 13
    assert len(GUARD_MUTATIONS) == 12 and encoded_count == 2812
    (OUT/'fixture-manifest.json').write_text(json.dumps(actual_plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    assert sha((OUT/'fixture-manifest.json').read_bytes()) == CANONICAL_PLAN_SHA256
    expected = (f"POLICY_FAST_PASS batches={totals['batches']} events={totals['events']} "
                f"cases={totals['cases']} transitions={totals['context_transitions']}")
    timings = {}
    case_lines = ['PASS CASE: '+item['case'] for item in manifest]
    extras_lines = ['PASS EDIT: '+item[0] for item in edits]+['PASS BOUNDARY: '+item[0] for item in boundary]
    py, timings['interpreter_seconds'] = run([sys.executable,ru_root/'ru','run',probe], 'interpreter',
                                           expected_lines=case_lines+extras_lines+[expected])
    assert py.splitlines()[-1] == expected, py[-1000:]
    progress('INTERPRETER: '+expected)
    # Independent cases are sharded only to bound GCC translation-unit size.
    # Every per-case API call and comparison remains identical to interpreter.
    native_lines = []
    shards = []
    for shard in range(4):
        indices = list(range(shard,len(case_sources),4))
        shard_totals = {key:sum(case_totals[i][key] for i in indices) for key in totals}
        shard_source = helper+CHECKS+''.join(case_sources[i] for i in indices)
        shard_source += ''.join(f'案{i}.\n' for i in indices)
        if shard == 3:
            shard_source += extras
            shard_totals['context_transitions'] = totals['context_transitions']
        shard_source += summary_source
        shard_probe = OUT/f'differential-{shard}.ru'
        generated = OUT/f'differential-{shard}-generated.c'
        executable = OUT/f'differential-{shard}'
        shard_probe.write_text(shard_source,encoding='utf-8',newline='\n')
        # Estimate the actual generated unit before invoking the unchanged
        # compiler CLI and its fixed 120-second GCC limit. No runtime override.
        sys.path.insert(0,str(ru_root))
        from rulang.compiler import Compiler
        from rulang.frontend import parse
        from rulang.modules import load_module_graph
        program = parse(shard_source)
        generated_preview = Compiler(program,str(shard_probe),modules=load_module_graph(shard_probe,program)).compile().encode('utf-8')
        preview = {'shard':shard,'bytes':len(generated_preview),
                   'sha256':hashlib.sha256(generated_preview).hexdigest()}
        (OUT/f'evidence/precompile-{shard}.json').write_text(json.dumps(preview,indent=2)+'\n',encoding='utf-8',newline='\n')
        progress('PRECOMPILE shard='+str(shard)+' bytes='+str(preview['bytes'])+' sha256='+preview['sha256'])
        _, build_seconds = run([sys.executable,ru_root/'ru','build','--cc','gcc',shard_probe,
                                '--emit-c',generated,'-o',executable],f'build-{shard}')
        assert hashlib.sha256(generated.read_bytes()).hexdigest() == preview['sha256']
        shard_expected = (f"POLICY_FAST_PASS batches={shard_totals['batches']} events={shard_totals['events']} "
                          f"cases={shard_totals['cases']} transitions={shard_totals['context_transitions']}")
        native, execute_seconds = run([executable],f'host-c-{shard}',
            expected_lines=[case_lines[i] for i in indices]+(extras_lines if shard == 3 else [])+[shard_expected])
        assert native.splitlines()[-1] == shard_expected
        native_lines.extend(native.splitlines()[:-1])
        shards.append({'shard':shard,'totals':shard_totals,'build_seconds':build_seconds,
                       'execute_seconds':execute_seconds,'generated_c_bytes':generated.stat().st_size,
                       'generated_c_sha256':hashlib.sha256(generated.read_bytes()).hexdigest(),
                       'probe_sha256':hashlib.sha256(shard_probe.read_bytes()).hexdigest(),
                       'executable_sha256':hashlib.sha256(executable.read_bytes()).hexdigest()})
        progress('HOST C SHARD '+str(shard)+': '+shard_expected)
    assert sorted(native_lines) == sorted(py.splitlines()[:-1])
    assert {key:sum(shard['totals'][key] for shard in shards) for key in totals} == totals
    timings['build_seconds'] = sum(shard['build_seconds'] for shard in shards)
    timings['host_c_seconds'] = sum(shard['execute_seconds'] for shard in shards)
    progress('HOST C: '+expected)
    STAGE = 'final-source-check'
    verify_sources(baseline, ru_root)
    assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest() == SCRIPT_SHA256
    assert hashlib.sha256((ROOT/'src/ru_lexical.ru').read_bytes()).hexdigest() == hashlib.sha256(after.encode()).hexdigest()
    report = {'schema_version':1,'status':'pending_order_verification',
              'baseline_commit':BASE_COMMIT,'baseline_tree':BASE_TREE,'baseline_policy_blob':BASE_POLICY_BLOB,
              'toolchain_commit':RU_COMMIT,'toolchain_tree':RU_TREE,
              'baseline_source_sha256':hashlib.sha256(before.encode()).hexdigest(),
              'candidate_sha256':hashlib.sha256(after.encode()).hexdigest(),
              'probe_sha256':hashlib.sha256(probe.read_bytes()).hexdigest(),
              'test_script_sha256':SCRIPT_SHA256,
              'fixture_manifest_sha256':hashlib.sha256((OUT/'fixture-manifest.json').read_bytes()).hexdigest(),
              'canonical_plan_sha256':CANONICAL_PLAN_SHA256,'plan_content_sha256':PLAN_CONTENT_SHA256,
              'host_c_shards':shards,
              'totals_per_backend':totals,'timings':timings,
              'edit_replay_cases':len(edits),'boundary_cases':[item[0] for item in boundary],'boundary_count':len(boundary),
              'boundary_main_calls':sum(1+len(item[5]) for item in boundary),
              'boundary_failure_calls':sum(bool(step[1]) for item in boundary for step in item[5]),'source_guard_negative_cases':len(GUARD_MUTATIONS),
              'fixture_compaction':{'original_batches':totals['batches'],'encoded_records':encoded_count,
                                    'python_exact_roundtrip':True,'canonical_input_plan_matched':True,
                                    'ru_per_case_input_checksum':True},
              'scope':'Actual interpreter and ordinary generated host C. No native import or platform guard substitution; no Windows/GUI speed claim.'}
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('POLICY_FAST_EXECUTION_PASS cases=196 batches=19627 events=2554 transitions=21504 shards=4 edits=4 boundaries=13 mutations=12',flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        private = traceback.format_exc().encode('utf-8')
        if CREATED_OUTPUT:
            (OUT/'report.json').unlink(missing_ok=True)
            (OUT/'ordered-output-validation.json').unlink(missing_ok=True)
            (OUT/'evidence/failure.log').write_bytes(private)
        print('POLICY_FAST_FAIL stage='+STAGE+' code='+FAILURE_CODE+' detail_sha256='+sha(private),file=sys.stderr)
        sys.exit(1)
