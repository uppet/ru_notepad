#!/usr/bin/env python3
"""Private benchmark graph generation and checked generated-C instrumentation.
Never imported by product builds. Native guards, scanner ABI and compiler stay pinned.
"""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASELINE_COMMIT='b525b47dab6a51494cde29a3aa468cfe2d14703a'
BASELINE_TREE='a1fb1a02abf76d80d3daf6f385edf29901264d73'
COMPILER_COMMIT='a2f6faa0f914781dea74cb6f0a7574f1dd6808ce'
COMPILER_TREE='7b4331d51bc6ab2ec95fec1f8368465343fcd5af'
CORPUS={'sha256':'ecf8dca884444a5e54e1f40dc6af01cf5e7830ed6fe902d3adf6fdf255f9b3fa','bytes':1000000,'scalars':636370,'newline_bytes':90909}
MODES=('lex_transport','ru_no_folding','full')
PATHS=('console_pipeline','cooperative_console','gui','preflight')
LEVELS={'off':0,'counts':1,'sampled':2}
PINNED = {
    "src/associations.ru": "d08e14317f8fa74ec6538637a43f0f1ba072985de0e8adcc98750a061a6cc700",
    "src/associations_policy.ru": "3306be080d6e908995cea106fe2ffae8374b94ef7b9372002a5232cda4246c48",
    "src/document.ru": "e4aa40775fc73c27ae36d8806ecf7710a237c4eba6756e785d95b3172c9e1b8f",
    "src/editor.ru": "0a12a41e50eb0d85d73066ca092aa04ff87866164032f9abc0efdfeca8badeb1",
    "src/file_codec.ru": "f34328f5dadfaec6a2d2a5503cfeec7501c06ae55323a9c527ffd93baea1b03a",
    "src/file_codec_flags.ru": "5aa2376e2c9efca36aa2f8798a6d6526ec915bfeb9bc02003e21775176884bb2",
    "src/file_drop.ru": "8eb172ac42f27097bfe00f296fcaf31e241bb91656ec09c523d074159b3e4e9a",
    "src/main.ru": "7ac0852b07072301bafaddfc0b4585044d7a9a931ce742165ad4e1d20d596adf",
    "src/ru_lexical.ru": "f78589e247186890855526f7bb3624d34e4004bb8fbc69587c96d38c826a602c",
    "src/ru_native_syntax.ru": "99836515a3e79affd95182346d295818155da73e4cbe5e3b6ed373845bab68d7",
    "src/ru_syntax.ru": "6bae1951632886450d130909a0024ec13f89ced9294f7af4cb4d86c6d8fa9f5b",
    "src/shortcuts.ru": "df987c577c906a8603a90c7bc21ec16f85a69b7133ba6123682db99336842d3c",
    "src/status.ru": "35b2e78d588b5f9bdf550ee57c6a389cc3826bb215bcfe08854d89f09612261d",
    "src/syntax.ru": "4cb680b5920820bc1b696d181b1f2a7e8e7d20b8eae3cc3dda730893fda913f8",
    "src/syntax_policy.ru": "91e92ad7b451a65a6777c41501fad40fd63d725ab0d4d57322124a65ffad1945",
    "src/ui_arguments.ru": "d27989270478cf0772ed8aab567ee45116be30d9800ba58de6bdc1a8062a9307",
    "src/win32.ru": "d09a28a18d16e4f0c9d8430522d697236ce43c546293a22074cd031af3bc692e",
    "tests/app_features_native.ru": "2c70b91cd161761a915ea10bb8874215574cf7cd02fe2180ff065c730203067f",
    "tests/app_native.ru": "d172f30dc628ea43f5bd6202fd087e693c507b79516dca80e838336ec8dcc1f0",
    "tests/app_ru_native.ru": "e3edfa66bdf06381500d6148f08dd3833a4cad69c35acc9448ba842c61c63d8e",
    "tests/app_streaming_native.ru": "4a513546d68fb6fc2fba44a872d8d4bf6d9b29ddb89b5c7d061a619b22555925",
    "tests/associations_native.ru": "3a2b4f465a95b56572ffbf9a38ff3ba663b5f927aaa0eff54dab18b5c767ce21",
    "tests/associations_policy.ru": "0bcd48f0c47bc8a2b84d8dc87124499c834968d878ffbccb3939ba5422294004",
    "tests/document_policy.ru": "0eda2569f8c06cb39a400d4d6365b20177fce1dbc86754dc3dc34f6c82dade9a",
    "tests/drop_fixture.ru": "400631133586f1529c3969d4665e96fdb1ea12bdb87867f19625fea9fd65ea02",
    "tests/editor_native.ru": "f1057a6ed3f41aee96468235ba2b38fe9b5fe6ae0f0ff9be8f49ddd0e2c65cf3",
    "tests/editor_streaming_native.ru": "b8ed24ec27e8b23ac5710d6605ae575a76879f88a5fbd87185acd976f43f4547",
    "tests/file_codec_flags.ru": "d5e549ee86b9900fff8a530d2baefc8f05abe4071e3c80876cdb8b072d8e71c1",
    "tests/file_codec_security_probe.ru": "8cae54600a49562d651fd29c31825861bbf95a827846d75b12c5d61b790a0624",
    "tests/file_codec_tests.ru": "dfc20b11b96401d5e46baabeb9f42844cff885a7add3185c8bb1f6dec1af5bf1",
    "tests/file_drop_native.ru": "daece679fcb8894fd95de24f685056490ed4c0337cc693a56a76c9c6d4c829d9",
    "tests/file_streaming_native.ru": "c059062717021369af52b3ac1a168d0268793cab015cc17d9217a50263e8b17a",
    "tests/fixtures/bad_bitfield_arguments.ru": "7a27f613d072fb2bd08a9afe8e7a1041a767905c4db8ee69683a58012aba14c2",
    "tests/fixtures/malformed_menu_arguments.ru": "0ef2605b1501b49e9ac19d14b399e4a033081cac84f0634cc9b5aaaf8e8bcc1a",
    "tests/fixtures/unsupported_array_contains.ru": "360482e9132c2fe49c17fb0f06f4f9be8d62b23e0ceab5da452d5670e976de02",
    "tests/ru_lexical_policy.ru": "7166c706e2f4a59476d2d577551f410f0fadc889e030fdd009dc990628420c21",
    "tests/ru_syntax_native.ru": "6bd86a28410354cdbefd89c6649d64f7aefa83fa6e681d97892e2367f1e1740c",
    "tests/shortcuts.ru": "b1f0bc97f58e1dabc449ef126a90f8905924a586c5c36105451b5393de4829ea",
    "tests/status_native.ru": "05955c156143514480d9c30075ff9de4ee2d23823361300f62204cccbf89c6d3",
    "tests/syntax_native.ru": "04ec4389d775ffb1579e4d3c89b6474c3ce017b2410364442948bef7cf39a31b",
    "tests/syntax_policy.ru": "75f21efccf876e41cd379463f8b44a9c20e4868fbecd567e4e7c12b66208c297",
    "tests/ui_arguments.ru": "e2ea2593cc284e1a79e96218ed2ff79513f294b033862fa98de5c18466510fc3"
}
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def once(text,old,new):
    if text.count(old)!=1: raise ValueError(f'Expected one anchor {old[:80]!r}, found {text.count(old)}')
    return text.replace(old,new,1)
def octal(text): return ''.join(chr(b) if 32<=b<127 and chr(b) not in '\\"' else f'\\{b:03o}' for b in text.encode())
def git(root,*args): return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()
def ru_function(text,name):
    m=re.search(r'^(?:算|作) '+re.escape(name)+r'(?: |:).*?^(?:法|为)\n',text,re.M|re.S)
    if not m: raise ValueError('Missing Ru function '+name)
    return m.group()
CHECK_MODULE='''# Private untimed verification. The native call uses unchanged production guards.
密 取 外言 '如:密'.
窗 取 外言 './win32.ru'.
语 取 外言 './syntax.ru'.
范围型 取 密 其 结构 [['start',窗 其 IP],['end',窗 其 IP],['text',窗 其 PTR]].
算 _档案核对 存 双长 为 数 代 为 数:
    得 假.
法
算 检查 柄:
    态 取 语 其 状态 柄.
    若 态 == 空 或 态['pending'] 或 态['feed'] != 1000000 或 态['bytes'] != 1000000 则 卒 'Profile target is incomplete.'. 然
    若 (范围型 其 大小) != 24 或 (范围型 其 偏移 'text') != 16 则 卒 'Profile range layout mismatch.'. 然
    存 取 密 其 缓冲 2000002.
    域 取 范围型 其 新建.
    合格 取 [假].
    试
        域 其 写 'start' 0.
        域 其 写 'end' 1000000.
        域 其 写 'text' (存 其 地址).
        双长 取 (窗 其 发指 柄 2778 0 域) 其 数.
        合格[0] 取 _档案核对 存 双长 态['generation'].
    救 原因
        域 其 关闭. 存 其 关闭.
        卒 原因.
    终
    域 其 关闭. 存 其 关闭.
    若 非 合格[0] 则 卒 'Profile complete byte/style check failed.'. 然
    得 空.
法
'''
def policy(text,mode):
    if mode=='full': return text
    head="算 批处理 态 事件 字节 为 数 行 为 数 结束 为 事实:\n    若 事件 其 量 > 64 则 卒 'Ru lexical event batch exceeds 64 events.'. 然\n"
    if mode=='lex_transport': body="    色们 取 [].\n"
    else: body='''    色们 取 [].
    位 取 0.
    循 事件 其 量 次
        项 取 事件[位].
        若 项[0] == 1 且 项[2] != 8 则
            若 项[4] > 64 则 卒 'Ru native keyword correction exceeds 64 bytes.'. 然
            _加色 色们 项[3] 项[4] 项[2].
        然
        位 取 位+1.
    环
'''
    body+="    态[0] 取 字节. 态[1] 取 行. 态[19] 取 结束.\n    得 {'spans':色们,'folds':[],'bytes':字节,'line':行}.\n法\n"
    return once(text,ru_function(text,'批处理'),head+body)
def pipeline_fixture(mode):
    original=(ROOT/'tests/ru_syntax_native.ru').read_text(encoding='utf-8-sig')
    text='\n'.join(original.splitlines()[:14])+"\n档案 取 外言 '../src/profile_check.ru'.\n次数 取 [0].\n通知 取 {'text':0,'needed':0,'other':0}.\n"
    for name in ('确认','过程','计时源码','计时样式','计时同源性能'): text+=ru_function(original,name)
    if mode=='lex_transport': text=once(text,'[[0,3,8],[4,3,4],[8,1,3],[999988,3,4],[999992,6,3]]','[[0,3,8],[4,3,8],[8,1,3],[999988,3,8],[999992,6,3]]')
    line=next(x for x in text.splitlines() if "显 'RU_GUI_SYNC " in x)
    text=once(text,line,line+'\n    档案 其 检查 柄.')
    text+='''算 元初 参数 为 句 阵:
    库 取 密 其 动态库 ((窗 其 目录)+'Scintilla.dll').
    实例 取 窗 其 成功 ((窗 其 GetModuleHandleW) 其 调用 [空]) 'instance'.
    类名 取 密 其 UTF16 'RuNotepad.RuSyntaxProfile'.
    回调 取 密 其 回调 (窗 其 WNDPROC) (算 过程) 0.
    类 取 (窗 其 WNDCLASS) 其 新建.
    类 其 写 'size' ((窗 其 WNDCLASS) 其 大小).
    类 其 写 'proc' (回调 其 地址).
    类 其 写 'instance' 实例.
    类 其 写 'name' (类名 其 地址).
    窗 其 成功 ((窗 其 RegisterClassExW) 其 调用 [类]) 'register fixture'.
    父 取 窗 其 控制 空 实例 'RuNotepad.RuSyntaxProfile' 'Ru syntax profile' 13565952 0.
    甲 取 编 其 创建 父 实例 1.
    计时同源性能 甲.
    语 其 遗忘 甲.
    窗 其 成功 ((窗 其 DestroyWindow) 其 调用 [父]) 'destroy fixture'.
    窗 其 成功 ((窗 其 UnregisterClassW) 其 调用 [类名,实例]) 'unregister fixture'.
    类 其 关闭. 类名 其 关闭. 回调 其 关闭.
    显 'TOTAL PASS: '+(次数[0] 为 句).
    得 0.
法
'''
    return text


PREFLIGHT_SOURCE='''
密 取 外言 '如:密'.
作 断言 条件 为 事实 说明 为 句:
    若 非 条件 则 卒 说明. 然
为
算 确认 成果:
    若 (成果 其 回调错误) != 空 则 卒 (成果 其 回调错误). 然
    得 成果 其 值.
法
算 _档案开始: 得 空. 法
算 _档案内存失败: 得 空. 法
算 _档案恢复 结束 为 事实: 得 真. 法
算 档案阶段 调 参数: 得 调 其 调用 参数. 法
算 档案时钟 调 回 值: 得 档案阶段 调 ([回,值]). 法
算 档案坏阶段 值: 得 1/0. 法
算 档案恐慌阶段 值: 卒 'profile-contained-panic'. 法
算 元初 参数 为 句 阵:
    若 (参数 其 量) != 1 则 得 2. 然
    库 取 密 其 动态库 参数[0].
    原生调 取 库 其 绑定 'invoke_callback' (密 其 签名 (密 其 i64) ([密 其 指针,密 其 u64]) 'cdecl').
    回声 取 库 其 绑定 'echo_i64' (密 其 签名 (密 其 i64) ([密 其 i64]) 'cdecl').
    坏浮 取 库 其 绑定 'nonfinite_f64' (密 其 签名 (密 其 f64) ([]) 'cdecl').
    设错 取 库 其 绑定 'last_error_value' (密 其 签名 (密 其 i32) ([]) 'cdecl').
    外错 取 库 其 绑定 'callback_last_error' (密 其 签名 (密 其 u32) ([密 其 指针]) 'cdecl').
    签 取 密 其 签名 (密 其 i64) ([密 其 u64]) 'cdecl'.
    外次数 取 [0].
    内回 取 密 其 回调 签 (算 值: 得 确认 (档案阶段 回声 ([值])). 法) (-8).
    外回 取 密 其 回调 签 (算 值: 外次数[0] 取 外次数[0]+1. 得 确认 (档案时钟 原生调 内回 值). 法) (-9).
    坏回 取 密 其 回调 签 (算 值: 得 档案坏阶段 值. 法) (-13).
    慌回 取 密 其 回调 签 (算 值: 得 档案恐慌阶段 值. 法) (-17).
    错回 取 密 其 回调 签 (算 值:
        内果 取 档案阶段 设错 ([]).
        断言 ((内果 其 错误码) == 4321) 'nested LastError lost'.
        得 9.
    法) (-7).
    _档案开始.
    果 取 档案时钟 原生调 外回 42.
    断言 ((确认 果) 其 数 == 42) 'nested callback result changed'.
    断言 (_档案恢复 假) 'normal nested profile state not restored'.
    慌果 取 档案时钟 原生调 慌回 1.
    断言 ((慌果 其 值) 其 数 == -17 且 ((慌果 其 回调错误) 其 含 'profile-contained-panic')) 'ordinary panic not contained'.
    断言 (_档案恢复 假) 'ordinary panic profile state not restored'.
    首果 取 档案时钟 原生调 坏回 1.
    断言 ((首果 其 值) 其 数 == -13 且 (首果 其 回调错误) != 空) 'first longjmp not contained'.
    断言 (_档案恢复 假) 'first longjmp profile state not restored'.
    坏回 其 失败时 坏浮 ([]).
    次果 取 档案时钟 原生调 坏回 1.
    断言 ((次果 其 值) 其 数 == -13 且 (次果 其 回调错误) == (首果 其 回调错误)) 'failure hook changed original fallback or error'.
    断言 (_档案恢复 假) 'failure-hook longjmp profile state not restored'.
    错果 取 档案阶段 外错 ([错回]).
    断言 ((错果 其 值) 其 数 == 1234 且 (错果 其 错误码) == 1234 且 (错果 其 回调错误) == 空) 'outer LastError was not preserved'.
    前次数 取 外次数[0].
    _档案内存失败.
    缺果 取 档案时钟 原生调 外回 1.
    断言 ((缺果 其 值) 其 数 == -9 且 (缺果 其 回调错误) != 空 且 外次数[0] == 前次数) 'trap allocation failure changed safety boundary'.
    断言 (_档案恢复 假) 'trap OOM profile state not restored'.
    断言 ((确认 (档案阶段 回声 ([19]))) 其 数 == 19 且 非 (密 其 回调中)) 'later native call failed after recovery'.
    断言 (_档案恢复 真) 'profile boundary branch coverage or closure failed'.
    内回 其 关闭. 外回 其 关闭. 坏回 其 关闭. 慌回 其 关闭. 错回 其 关闭.
    显 'PASS: native profiling boundaries preserve nested callback results and recovery'.
    显 'RU_SYNTAX_PROFILE_PREFLIGHT_TESTS_PASS=1'.
    得 0.
法
'''
TEST_GLOBALS='static unsigned rp_test_first, rp_test_second, rp_test_oom, rp_test_oom_next;\n'
TEST_C=r'''
static Val rp_test_begin(void) {
#if RP_LEVEL
    rp_begin(NULL,1);rp.batches=63;rp_batch();
#endif
    return v_null();
}
static Val rp_test_arm_oom(void) { rp_test_oom_next=1;return v_null(); }
static Val rp_test_restored(Val finish) {
    RpError saved=RP_SAVE_ERROR();int ok=ru_native_depth==0 && ru_native_callback_depth==0 && !ru_native_handling_failure && ru_native_trap==NULL;
#if RP_LEVEL
    ok=ok && rp.active && rp.valid && rp.depth==0 && rp.phase==0 && rp.tick_depth==0 && rp.sampled==(RP_LEVEL==2);
#endif
    if(v_truth(finish)) {
        ok=ok && rp_test_first==2 && rp_test_second==1 && rp_test_oom==1 && !rp_test_oom_next;
#if RP_LEVEL
        ok=ok && rp.callback_max_depth>=2 && rp.restores>0;
        rp_finish(ok);ok=ok && !rp.active && rp.complete && !rp.sampled && !rp.depth && !rp.phase;
#endif
        printf("RU_SYNTAX_PROFILE_PREFLIGHT {\"schema\":1,\"instrumentation\":\"%s\",\"passed\":%s,\"first_longjmp\":%u,\"second_longjmp\":%u,\"trap_oom\":%u}\n",RP_LEVEL==0?"off":RP_LEVEL==1?"counts":"sampled",ok?"true":"false",rp_test_first,rp_test_second,rp_test_oom);
        fflush(stdout);
    }
    RP_RESTORE_ERROR(saved);return v_fact(ok);
}
'''

def prepare(ru_root:Path,output_dir:Path):
    started=time.monotonic()
    ru_root=Path(ru_root).resolve();output_dir=Path(output_dir).resolve()
    if git(ru_root,'rev-parse','HEAD^{tree}')!=COMPILER_TREE or git(ru_root,'status','--porcelain'): raise ValueError('Compiler is not the clean pinned tree')
    for name,digest in PINNED.items():
        if sha(ROOT/name)!=digest: raise ValueError('Baseline input mismatch: '+name)
    data=('值 取 1.\n'*90907+'#         \n显 987654.\n').encode()
    if len(data)!=1000000 or hashlib.sha256(data).hexdigest()!=CORPUS['sha256']: raise ValueError('Corpus identity mismatch')
    output_dir.mkdir(parents=True,exist_ok=True);sys.dont_write_bytecode=True;sys.path.insert(0,str(ru_root))
    from rulang.frontend import parse
    from rulang.modules import load_module_graph
    from rulang.compiler import Compiler
    manifest={'schema':1,'baseline_commit':BASELINE_COMMIT,'baseline_tree':BASELINE_TREE,'compiler_commit':COMPILER_COMMIT,'compiler_tree':COMPILER_TREE,'corpus':CORPUS,'baseline_inputs':PINNED,'units':[],
        'phase_contract':'Exclusive nested phases include v_call binding/annotation/callee env/body/scratch cleanup and count/hash observation; caller argument construction excluded. Snapshot counts only, no separate snapshot timing.',
        'counter_contract':'malloc/calloc/realloc actual instrumented requests, including profile checkpoint enlargement; no doublecount. env_comparisons includes find_local and set. gc_heap_scans covers root and sweep entries; gc_work covers marking edges. Callback heap_entries derives two successful trap scans from ru_live, excludes OOM and recovery scans. Counters cover whole first-to-last batch window, including inter-tick callbacks; no hidden replay. Untimed verification scaffolding common to off/counts/sampled.'}
    for path,mode in [('console_pipeline',m) for m in MODES]+[('cooperative_console','full'),('gui','full')]:
        unit_id=path+'_'+mode;folder=output_dir/'units'/unit_id;(folder/'src').mkdir(parents=True,exist_ok=True);(folder/'tests').mkdir(exist_ok=True)
        for source in sorted((ROOT/'src').glob('*.ru')):
            content=source.read_text(encoding='utf-8-sig')
            if source.name=='ru_lexical.ru': content=policy(content,mode)
            if source.name=='main.ru' and path=='gui':
                content="档案 取 外言 './profile_check.ru'.\n"+content
                anchor=next(x for x in content.splitlines() if "显 'RU_GUI_SNAPSHOT seq='" in x and 'ok=1' in x)
                content=once(content,anchor,anchor+"\n        若 序 == 3 且 非 扫['pending'] 且 扫['bytes'] == 1000000 则 档案 其 检查 (文们[活动] 其 查 'editor'). 然")
            (folder/'src'/source.name).write_text(content,encoding='utf-8')
        (folder/'src/profile_check.ru').write_text(CHECK_MODULE,encoding='utf-8')
        if path=='console_pipeline': source=folder/'tests/profile_pipeline.ru';source.write_text(pipeline_fixture(mode),encoding='utf-8');exe='ru_syntax_profile.exe'
        elif path=='cooperative_console':
            source=folder/'tests/app_ru_native.ru';text="档案 取 外言 '../src/profile_check.ru'.\n"+(ROOT/'tests/app_ru_native.ru').read_text(encoding='utf-8-sig')
            anchor=next(x for x in text.splitlines() if "显 'RU_GUI_TIMER " in x);text=once(text,anchor,anchor+'\n        档案 其 检查 柄.');source.write_text(text,encoding='utf-8');exe='app_ru_native.exe'
        else: source=folder/'src/main.ru';exe='ru_notepad.exe'
        text=source.read_text(encoding='utf-8');program=parse(text);graph=load_module_graph(str(source),program);graph.sources[graph.root]=text
        code=Compiler(program,graph.root,modules=graph,allow_native=True).compile();emitted=folder/'baseline.c';emitted.write_text(code,encoding='utf-8')
        manifest['units'].append({'id':unit_id,'path':path,'mode':mode,'source':source.relative_to(output_dir).as_posix(),'generated_c':emitted.relative_to(output_dir).as_posix(),'exe_name':exe,'console':path!='gui','source_sha256':sha(source),'generated_c_sha256':sha(emitted),'graph_sha256':{p.relative_to(output_dir).as_posix():sha(p) for p in sorted(folder.rglob('*.ru'))},'expected_pass_count':6 if path=='console_pipeline' else 8 if path=='cooperative_console' else None,'baseline_source':'tests/ru_syntax_native.ru' if path=='console_pipeline' else 'tests/app_ru_native.ru' if path=='cooperative_console' else 'src/main.ru'})
    pre=output_dir/'preflight';pre.mkdir(exist_ok=True)
    source=pre/'profile_boundary.ru';source.write_text(PREFLIGHT_SOURCE,encoding='utf-8')
    bridge_origin='tests/fixtures/native/c_backend_bridge.c'
    if sha(ru_root/bridge_origin)!='45689caba1b8552424a87dd6fd061818dbf1daab57d066461e7d91d93ea7e65f': raise ValueError('Pinned preflight bridge mismatch')
    bridge=pre/'profile_bridge.c';bridge.write_bytes((ru_root/bridge_origin).read_bytes())
    program=parse(PREFLIGHT_SOURCE);graph=load_module_graph(str(source),program);graph.sources[graph.root]=PREFLIGHT_SOURCE
    generated=pre/'baseline.c';generated.write_text(Compiler(program,graph.root,modules=graph,allow_native=True,full_runtime=True).compile(),encoding='utf-8')
    manifest['preflight']={'source':source.relative_to(output_dir).as_posix(),'source_sha256':sha(source),'generated_c':generated.relative_to(output_dir).as_posix(),'generated_c_sha256':sha(generated),'bridge_c':bridge.relative_to(output_dir).as_posix(),'bridge_sha256':sha(bridge),'bridge_origin':bridge_origin,'bridge_origin_sha256':'45689caba1b8552424a87dd6fd061818dbf1daab57d066461e7d91d93ea7e65f','exe_name':'profile_boundary.exe','dll_name':'profile_bridge.dll','expected_marker':'RU_SYNTAX_PROFILE_PREFLIGHT_TESTS_PASS=1','expected_pass_count':1}
    manifest['prepare_elapsed_seconds']=time.monotonic()-started
    (output_dir/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');return manifest

ALLOC_C=r'''
#include <stdlib.h>
static void *rp_malloc(size_t bytes) { void *p;rp_alloc_request(bytes);p=malloc(bytes);if(p)rp_alloc_success();return p; }
static __attribute__((noinline)) void *rp_calloc(size_t count,size_t bytes) { void *p;if(bytes && count>SIZE_MAX/bytes)rp_invalid("allocation_size_overflow");else rp_alloc_request(count*bytes);p=calloc(count,bytes);if(p)rp_alloc_success();return p; }
static void *rp_realloc(void *old,size_t bytes) { void *p;rp_realloc_request(bytes);p=realloc(old,bytes);if(p)rp_realloc_success();return p; }
'''
CHECK_C=r'''
/* Untimed borrowed-memory check. No allocations, retained pointers or native calls. */
static Val rp_expected_check(Val memory, Val returned, Val generation) {
    RpError saved=RP_SAVE_ERROR(); size_t i; int text_ok=1,style_ok=1,checked;
    uint64_t text_hash=UINT64_C(14695981039346656037),style_hash=UINT64_C(14695981039346656037);
    static const unsigned char body[]={0xe5,0x80,0xbc,32,0xe5,0x8f,0x96,32,49,46,10};
    static const unsigned char tail[]={35,32,32,32,32,32,32,32,32,32,10,0xe6,0x98,0xbe,32,57,56,55,54,53,52,46,10};
    static const unsigned char styles[]={8,8,8,0,4,4,4,0,3,7,0};
    RuNative *m=memory.kind==RU_NATIVE?(RuNative *)memory.heap:NULL,*parent;
    int ok=m && m->tag==RN_MEMORY && !m->closed && m->as.memory.size>=2000002 && returned.kind==RU_NUM && returned.n==2000000;
    if(ok) for(parent=m;parent;parent=parent->as.memory.parent) if(parent->closed) ok=0;
#if RP_LEVEL
    if(!rp.started || !rp.complete || rp.active || generation.kind!=RU_NUM || generation.n!=(double)rp.generation) ok=0;
#endif
    if(ok && (m->as.memory.data[2000000] || m->as.memory.data[2000001])) ok=0;
    checked=ok;
    if(ok) for(i=0;i<1000000;++i) {
        unsigned char expected,style,actual=m->as.memory.data[2*i],actual_style=m->as.memory.data[2*i+1];
        if(i<999977) { expected=body[i%11];style=styles[i%11]; }
        else { size_t t=i-999977;expected=tail[t];style=t<10?1:t==10?0:t<14?4:t==14?0:t<21?3:t==21?7:0; }
        if(!strcmp(RP_MODE,"lex_transport") && style==4) style=8;
        if(actual!=expected) text_ok=0;
        if(actual_style!=style) style_ok=0;
        text_hash=(text_hash^actual)*UINT64_C(1099511628211);style_hash=(style_hash^actual_style)*UINT64_C(1099511628211);
    }
    ok=ok && text_ok && style_ok;
    printf("RU_SYNTAX_PROFILE_CHECK {\"schema\":1,\"input_bytes\":1000000,\"input_preserved\":%s,\"style_bytes\":1000000,\"style_checksum\":\"%016" PRIx64 "\",\"input_checksum\":\"%016" PRIx64 "\",\"algorithm\":\"fnv1a64_bytes_v1\",\"expected_style_match\":%s,\"full_output_checked\":%s}\n",text_ok&&checked?"true":"false",style_hash,text_hash,style_ok&&checked?"true":"false",checked?"true":"false");
    fflush(stdout);(void)generation;RP_RESTORE_ERROR(saved);return v_fact(ok);
}
'''
HELPERS_C=r'''
static Val rp_map(Val value,const char *key) {
    size_t i;if(value.kind==RU_MAP) { RuMap *m=(RuMap*)value.heap;
        for(i=0;i<m->capacity;++i) if(m->entries[i].state==1 && m->entries[i].key.kind==RU_STR && !strcmp(m->entries[i].key.s->data,key)) return m->entries[i].value;
    } return v_null();
}
static uint64_t rp_number(Val value) {
    if((value.kind!=RU_NUM && value.kind!=RU_FACT) || !isfinite(value.n) || value.n<0 || value.n>32000000 || value.n!=(double)(uint64_t)value.n) { rp_invalid("invalid_numeric_observation");return 0; }return (uint64_t)value.n;
}
static void rp_step_open(Val state,Val length) {
    if(!rp.started && length.kind==RU_NUM && length.n==1000000 && rp_number(rp_map(state,"feed"))==0) rp_begin(state.heap,rp_number(rp_map(state,"generation")));
    if(rp.active) {
        if(state.heap!=rp.target) { rp_invalid("target_changed");rp_finish(0);return; }
        if(rp_number(rp_map(state,"generation"))!=rp.generation) { rp_invalid("generation_changed");rp_finish(0);return; }
        rp_batch();
    }
}
static void rp_step_close(Val state,int success) {
    if(!rp.active || state.heap!=rp.target) return;
    if(rp_number(rp_map(state,"generation"))!=rp.generation) { rp_invalid("generation_changed");rp_finish(0);return; }
    if(!success) { rp_invalid("step_panic");rp_finish(0);return; }
    if(rp_number(rp_map(state,"feed"))==1000000 && !v_truth(rp_map(state,"pending"))) rp_finish(1);else rp_batch_end();
}
static uint64_t rp_snapshot_visits(size_t live) {
    if((uint64_t)live>UINT64_MAX/2) { rp_invalid("counter_overflow");return 0; }
    return 2*(uint64_t)live;
}
static unsigned rp_callback_kind(RuNative *callback) {
    Val value;RuCallable *f;
    if(!callback || callback->edge_count<2) return 0;
    value=callback->edges[1];
    if(value.kind!=RU_FUNCTION || !value.heap) return 0;
    f=(RuCallable*)value.heap;
    return f->function?f->function->rp_kind:0;
}
static void rp_result(unsigned kind,Val *args,Val result) {
    size_t i,j;if(!rp.active || !rp.valid) return;
    if(kind==2 && result.kind==RU_ARRAY) {
        RuArray *a=(RuArray*)result.heap;RP_COUNT(decoded_events,a->len);RP_COUNT(snapshot_words,4*a->len);
        rp_hash_u32(UINT32_C(0x45564e54));rp_hash_u32((uint32_t)a->len);
        for(i=0;i<a->len;++i) { if(a->items[i].kind!=RU_ARRAY || ((RuArray*)a->items[i].heap)->len!=6) { rp_invalid("invalid_event_observation");return; }
            for(j=0;j<6;++j) rp_hash_u32((uint32_t)rp_number(((RuArray*)a->items[i].heap)->items[j])); }
    }
    if(kind==3) { Val folds=rp_map(result,"folds");if(folds.kind==RU_ARRAY) RP_COUNT(fold_rows,((RuArray*)folds.heap)->len); }
    if(kind==1) {
        Val buffer=rp_map(result,"styleBuffer");uint64_t bytes=rp_number(rp_map(result,"bytes")),line=rp_number(rp_map(result,"line")),done=rp_number(rp_map(result,"done")),count=rp_number(rp_map(result,"styleLength"));
        static const char *fields[]={"styleStart","styleLength","consumed","bytes","line","done"};
        rp_hash_u32(UINT32_C(0x42415443));for(i=0;i<6;++i) rp_hash_u32((uint32_t)rp_number(rp_map(result,fields[i])));
        RP_COUNT(trace_batches,1);rp.last_bytes=bytes;rp.last_line=line;rp.last_done=done;RP_COUNT(style_bytes,count);RP_COUNT(feed_bytes,rp_number(rp_map(result,"consumed")));
        if(buffer.kind!=RU_NATIVE || ((RuNative*)buffer.heap)->tag!=RN_MEMORY || ((RuNative*)buffer.heap)->closed || count>((RuNative*)buffer.heap)->as.memory.size) rp_invalid("invalid_style_observation");
        else rp_style_trace(((RuNative*)buffer.heap)->as.memory.data,(size_t)count);
    }(void)args;
}
'''
def decode_c_source_path(value):
    """Decode only the pinned Compiler.cstr byte-literal grammar, never eval."""
    decoded=bytearray();i=0
    while i<len(value):
        byte=ord(value[i])
        if byte==92:
            digits=value[i+1:i+4]
            if len(digits)!=3 or any(c not in '01234567' for c in digits) or int(digits,8)>255:
                raise ValueError('Unknown generated C source-path escape')
            decoded.append(int(digits,8));i+=4
        elif 32<=byte<=126 and byte!=34:
            decoded.append(byte);i+=1
        else:
            raise ValueError('Unexpected generated C source-path character')
    if 0 in decoded: raise ValueError('NUL in generated source path')
    text=decoded.decode('utf-8')
    if octal(text)!=value: raise ValueError('Noncanonical generated C source-path escape')
    return text.replace('\\','/')

def generated_functions(code):
    desc={int(m[1]):m[2] for m in re.finditer(r'static RuFunction ru_function_(\d+)_descriptor = \{"([^"\n]*)",',code)}
    result=[]
    for m in re.finditer(r'^static Val ru_function_(\d+)\(Env \*global, Val self, int call_line, Val \*args\) \{',code,re.M):
        end=code.index('\n}\n',m.end())+3;body=code[m.start():end];source=re.search(r'ru_source = "([^"\n]*)";',body)
        result.append((int(m[1]),desc[int(m[1])],decode_c_source_path(source[1]) if source else '',m.start(),end,body))
    return result

def instrument(input_c:Path,output_c:Path,*,instrumentation,path,mode):
    if instrumentation not in LEVELS or path not in PATHS or mode not in MODES or path!='console_pipeline' and mode!='full': raise ValueError('Unsupported variant')
    input_c=Path(input_c);output_c=Path(output_c);code=input_c.read_text(encoding='utf-8');level=LEVELS[instrumentation];anchors=[]
    header=(ROOT/'native/profile_counters.h').read_text(encoding='utf-8');prefix=f'#define RP_LEVEL {level}\n#define RP_PATH "{path}"\n#define RP_MODE "{mode}"\n#define RP_NATIVE_STYLE_TRACE 1\n'+header+'\n'
    kinds={('ru_native_syntax.ru','扫描'):1,('ru_native_syntax.ru','_解事件'):2,('ru_lexical.ru','批处理'):3,('ru_syntax.ru','_施样'):4,('ru_syntax.ru','_一步'):5,('ru_lexical.ru','_记词'):6,('main.ru','消息处理'):8,('file_drop.ru','_编辑子过程'):9,('main.ru','语法时钟'):10};kinds.update({('profile_boundary.ru','档案阶段'):2,('profile_boundary.ru','档案坏阶段'):3,('profile_boundary.ru','档案恐慌阶段'):4,('profile_boundary.ru','档案时钟'):10});id_kinds={}
    for ident,name,source,start,end,body in reversed(generated_functions(code)):
        kind=next((k for (file,ru_name),k in kinds.items() if source.endswith('/'+file) and name==octal(ru_name)),0);id_kinds[ident]=kind
        if source.endswith('/profile_check.ru') and name==octal('_档案核对'):
            body=body[:body.index('{')+1]+'\n    (void)global;(void)self;(void)call_line;return rp_expected_check(args[0],args[1],args[2]);\n}\n';anchors.append('expected_byte_check')
        if path=='preflight' and name in {octal('_档案开始'),octal('_档案内存失败'),octal('_档案恢复')}:
            call={octal('_档案开始'):'rp_test_begin()',octal('_档案内存失败'):'rp_test_arm_oom()',octal('_档案恢复'):'rp_test_restored(args[0])'}[name]
            body=body[:body.index('{')+1]+'\n    (void)global;(void)self;(void)call_line;(void)args;return '+call+';\n}\n'
        if level and kind==5:
            anchor=re.search(r'    env_bind\(env, "'+re.escape(octal('长'))+r'", (ru_v_\d+), \d+\);',body)
            if not anchor: raise ValueError('Missing step length binding')
            body=once(body,anchor[0],anchor[0]+'\n    rp_step_open(args[1], '+anchor[1]+');');anchors.append('first_batch_after_length')
        if level and kind==6:
            anchor='/* 如 source line 191: return */';body=once(body,anchor,'RP_COUNT(empty_fastpath_hits,1);\n            '+anchor)
        code=code[:start]+body+code[end:]
    expected={2,3,4,10} if path=='preflight' else {1,2,3,4,5,6}|({8,9,10} if path!='console_pipeline' else set())
    for required in expected:
        if list(id_kinds.values()).count(required)!=1: raise ValueError(f'Missing or duplicate stage anchor: {required}')
    if path!='preflight' and anchors.count('expected_byte_check')!=1: raise ValueError('Expected exactly one full-byte check marker')
    first=re.search(r'^static Val ru_function_\d+\(Env \*global',code,re.M).start();code=code[:first]+CHECK_C+(TEST_C if path=='preflight' else '')+'\n'+code[first:]
    if level:
        code=once(code,'RuCode code; int procedure; } RuFunction;','RuCode code; int procedure; unsigned rp_kind; } RuFunction;')
        code=re.sub(r'(static RuFunction ru_function_(\d+)_descriptor = \{[^\n]*)(\};)',lambda m:m[1]+', '+str(id_kinds[int(m[2])])+m[3],code)
        code=re.sub(r'(static RuFunction ru_method_\d+_descriptor = \{[^\n]*)(\};)',r'\1, 0\2',code)
        code=once(code,'    jmp_buf jump;','    jmp_buf jump;\n    RpCheckpoint rp_checkpoint;')
        code=re.sub(r'\bmalloc\(', 'rp_malloc(',code)
        code=re.sub(r'\bcalloc\(', 'rp_calloc(',code)
        code=re.sub(r'\brealloc\(', 'rp_realloc(',code)
        code=ALLOC_C+'\n'+code
        code=once(code,'ru_heap=h; ++ru_live;','ru_heap=h; ++ru_live; if(rp.active && ru_live>rp.peak_live) rp.peak_live=ru_live;')
        code=once(code,'    env->parent=parent; env->managed=1; env->scope=scope;','    RP_COUNT(env_creates,1);\n    env->parent=parent; env->managed=1; env->scope=scope;')
        code=once(code,'        if(!strcmp(binding->name,name)) return binding;','        if((RP_COUNT(env_comparisons,1), !strcmp(binding->name,name))) return binding;')
        code=once(code,'for(b=env->bindings;b;b=b->next) if(!strcmp(b->name,name)) {','for(b=env->bindings;b;b=b->next) if((RP_COUNT(env_comparisons,1), !strcmp(b->name,name))) {')
        code=once(code,'    b=(RuBinding *)ru_scratch_alloc(sizeof(*b),0);','    RP_COUNT(binding_creates,1);\n    b=(RuBinding *)ru_scratch_alloc(sizeof(*b),0);')
        code=once(code,'    ++ru_collections;','    ++ru_collections; RP_COUNT(gc_collections,1); RP_COUNT(gc_heap_scans,ru_live); RP_COUNT(gc_heap_scans,ru_live); /* root and sweep entries */')
        code=once(code,'        ru_heap_dispose(h); --ru_live; ++ru_freed;','        ru_heap_dispose(h); --ru_live; ++ru_freed; RP_COUNT(gc_freed,1);')
        code=once(code,'    free(todo);\n    slot = &ru_heap;','    RP_COUNT(gc_marked,used); RP_COUNT(gc_work,work);\n    free(todo);\n    slot = &ru_heap;')
        code=once(code,'static Val v_call(Val callable,size_t argc,const char **keys,Val *args,int line)\n{',HELPERS_C+'\nstatic Val v_call(Val callable,size_t argc,const char **keys,Val *args,int line)\n{')
        code=once(code,'    f=(RuCallable *)callable.heap;fn=f->function;','    f=(RuCallable *)callable.heap;fn=f->function;\n    RpCall profile_call=rp_call_enter(fn->rp_kind);')
        code=once(code,'ru_leave();ru_scratch_free(bound);return result;','ru_leave();\n    if(!ru_panicking) rp_result(fn->rp_kind,bound,result);\n    if(fn->rp_kind==5) rp_step_close(bound[1],!ru_panicking);\n    ru_scratch_free(bound);rp_call_leave(profile_call);return result;')
        code=once(code,'    RuNativeTrap *trap;\n    /* Immutable fields','    RuNativeTrap *trap;\n    RpCheckpoint profile_before;\n    /* Immutable fields')
        code=once(code,'    trap = rn_trap_new();','    profile_before=rp_checkpoint();\n    trap = rn_trap_new();\n    if(trap) { trap->rp_checkpoint=profile_before; rp_callback(rp_callback_kind(callback),ru_native_callback_depth,rp_snapshot_visits(ru_live),trap->root_count); }')
        code=once(code,'    if (!trap) {\n        rn_record_error','    if (!trap) {\n        rp_restore(profile_before);\n        rn_record_error')
        code=once(code,'static void rn_trap_restore(RuNativeTrap *trap)\n{\n    RuHeap *heap;','static void rn_trap_restore(RuNativeTrap *trap)\n{\n    RuHeap *heap;\n    rp_restore(trap->rp_checkpoint);')
        code=once(code,'        free(trap->roots); free(trap);','        rp_restore(trap->rp_checkpoint);\n        free(trap->roots); free(trap);')
        anchors+=['v_call_binding_to_cleanup_exclusive','callback_restore_normal_oom_panic_both_longjmp']
    if path=='preflight':
        code=TEST_GLOBALS+code
        code=once(code,'static RuNativeTrap *rn_trap_new(void)\n{','static RuNativeTrap *rn_trap_new(void)\n{\n    if(rp_test_oom_next) { rp_test_oom_next=0;++rp_test_oom;return NULL; }')
        code=once(code,'        }\n        if (trap->message[0]) {','        } else ++rp_test_first;\n        if (trap->message[0]) {')
        code=once(code,'                } else rn_trap_restore(trap);','                } else { ++rp_test_second;rn_trap_restore(trap); }')
    else:
        code=once(code,'int main(int argc, char **argv) {','int main(int argc, char **argv) {\n    atexit(rp_emit);')

    if level:
        code=once(code,'int main(int argc, char **argv) {','int main(int argc, char **argv) {\n    rp_calibrate(); /* Startup, before any original benchmark clock. */')
    if path!='preflight' and any(symbol in code for symbol in ('rp_test_oom','rp_test_first','rp_test_second')): raise ValueError('Fault injection escaped preflight')
    if not re.search(r'raw = ru_native_generated_call\([^;]+;\s*error = rn_platform_error\(\);',code): raise ValueError('Foreign return/error adjacency changed')
    output_c.parent.mkdir(parents=True,exist_ok=True);output_c.write_text(prefix+code,encoding='utf-8')
    return {'schema':1,'input_sha256':sha(input_c),'output_sha256':sha(output_c),'header_sha256':sha(ROOT/'native/profile_counters.h'),'instrumentation':instrumentation,'path':path,'mode':mode,'anchors':anchors,'function_kinds':{str(k):v for k,v in id_kinds.items() if v}}

def main():
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare');p.add_argument('--ru-root',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True)
    p=sub.add_parser('instrument');p.add_argument('--input-c',type=Path,required=True);p.add_argument('--output-c',type=Path,required=True);p.add_argument('--instrumentation',choices=LEVELS,required=True);p.add_argument('--path',choices=PATHS,required=True);p.add_argument('--mode',choices=MODES,required=True)
    args=vars(ap.parse_args());command=args.pop('command');print(json.dumps(globals()[command](**args),ensure_ascii=False,indent=2))
if __name__=='__main__': main()
