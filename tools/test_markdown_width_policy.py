#!/usr/bin/env python3
"""Bounded local width-inline equivalence oracle; never Windows GUI acceptance.

The two immutable policy hashes and compiler commit/tree are intentional review
boundaries. Raw diagnostics and generated sources stay in a unique build/private
folder. stdout contains only a fixed numeric summary. No network or publication.
"""
from pathlib import Path
import argparse, ast, hashlib, json, os, re, sys, tempfile, time, traceback
from test_markdown_portable import checked_run, source_snapshot
from ru_cli_diagnostics import prepare_compile_diagnostics

ROOT=Path(__file__).resolve().parents[1]
PIN='85c7821fda35aa79deeaf67b4d430f24ddd7f07f'
TREE='a770e367e84d87a0d2fcb6d49ea6f06da2dbe4ba'
BASE_HASH='e9658000e1c5fbe5fb49403af2a27eb11a0efb9d4bf5261617b760688ea2d720'
CANDIDATE_HASH='e3606ac3806d4b4b0255b10c4600f088bcdacaffab9918f62c91bd5115d648e0'
FIXTURE_HASH='31ebd820a4e92b91008b0b03eff639cc956bc64a6f13dcfc14a613c6e76ae10f'
EXPECTED=b'FULL_STATE_RETURNS 12690\nERROR_ORDER_CHECKS 3446\nRANGE_PAUSES 5\nDIFFERENTIAL_PASS\n'

def require(value):
    if not value: raise RuntimeError('width_oracle_control')

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def check_sources(base):
    for path,wanted in ((base/'src/markdown_policy.ru',BASE_HASH),
                        (ROOT/'src/markdown_policy.ru',CANDIDATE_HASH),
                        (ROOT/'tests/markdown_policy.ru',FIXTURE_HASH)):
        require(path.is_file() and not path.is_symlink() and digest(path)==wanted)
    return source_snapshot(ROOT)

def normalized(data):
    text=data.decode('utf-8','strict').replace('\r\n','\n').encode()
    require(text==EXPECTED)
    return text

def generate(root,base,out):
    fixture=(root/'tests/markdown_policy.ru').read_text(encoding='utf-8')
    cases=[(ast.literal_eval(a),ast.literal_eval(b)) for a,b in re.findall(r"^核例 ('(?:[^'\\]|\\.)*') ('(?:[^'\\]|\\.)*')",fixture,re.M)]
    cases += [('width-boundaries','# h\r\n\x7f\x80\u07ff\u0800\uffff\U00010000😀\r\n---'),('fence-width','```\r\n\x7f\x80\u07ff\u0800\uffff\U00010000😀\r\n```'),('html-width','<!--\r\n中😀\r\n-->\r\n# h'),('container-width','> # 中\r\n> 😀\r\n\r\n- 中\n  x')]
    def lit(s):return "'"+s.replace('\\','\\\\').replace("'","\\'").replace('\r','\\r').replace('\n','\\n').replace('\t','\\t')+"'"
    source='甲模 取 外言 '+lit((base/'src/markdown_policy.ru').as_posix())+'.\n乙模 取 外言 '+lit((root/'src/markdown_policy.ru').as_posix())+'.\n次数 取 [0,0,0].\n'
    source+=fixture[fixture.index('算 同全态'):fixture.index('作 核输入边界')]
    source+='''作 同果 甲 乙:
        键们 取 ['used','line','bytes','finished']. 位 取 0.
        循 4 次
            若 甲[键们[位]] != 乙[键们[位]] 则 卒 'return scalar mismatch'. 然
            位 取 位+1.
        环
        列甲 取 甲['folds']. 列乙 取 乙['folds'].
        若 列甲 其 量 != 列乙 其 量 则 卒 'fold count mismatch'. 然
        位 取 0.
        循 列甲 其 量 次
            项 取 0.
            循 4 次
                若 列甲[位][项] != 列乙[位][项] 则 卒 'fold value mismatch'. 然
                项 取 项+1.
            环
            位 取 位+1.
        环
    为
    作 接入 甲 乙 文 为 句 末 为 事实:
        位 取 0.
        循
            果甲 取 甲模 其 喂入 甲 文[位:] 末.
            果乙 取 乙模 其 喂入 乙 文[位:] 末.
            同果 果甲 果乙.
            若 非 (同全态 甲 乙) 则 卒 'full state mismatch'. 然
            次数[0] 取 次数[0]+1.
            用 取 果甲['used']. 位 取 位+用.
            若 (果甲['folds'] 其 量) >= 60 则 次数[2] 取 次数[2]+1. 然
            若 位 == (文 其 量) 且 (非 末 或 果甲['finished']) 则 破. 然
            若 用 == 0 且 (果甲['folds'] 其 量) == 0 则 卒 'no progress'. 然
        环
    为
    作 拒绝 甲 乙 文 为 句 末 为 事实 期 为 句:
        错 取 ['', ''].
        试 甲模 其 喂入 甲 文 末. 救 原因 错[0] 取 原因 为 句. 终
        试 乙模 其 喂入 乙 文 末. 救 原因 错[1] 取 原因 为 句. 终
        若 错[0] != 错[1] 或 非 (错[0] 其 含 期) 则 卒 'error ordering mismatch'. 然
        若 非 (同全态 甲 乙) 则 卒 'error state mismatch'. 然
        次数[1] 取 次数[1]+1.
    为
    作 完后 甲 乙:
        接入 甲 乙 '' 真.
        拒绝 甲 乙 'x' 真 'Markdown state is already finished.'.
        拒绝 甲 乙 '' 假 'Markdown state is already finished.'.
    为
    作 切分 文 为 句:
        切 取 0.
        循 (文 其 量)+1 次
            甲 取 甲模 其 新状态. 乙 取 乙模 其 新状态.
            接入 甲 乙 文[:切] 假. 接入 甲 乙 文[切:] 真. 完后 甲 乙.
            切 取 切+1.
        环
    为
    作 块分 文 为 句 块 为 数:
        甲 取 甲模 其 新状态. 乙 取 乙模 其 新状态. 位 取 0.
        循
            末 取 位+块. 若 末 > (文 其 量) 则 末 取 文 其 量. 然
            接入 甲 乙 文[位:末] (末 == (文 其 量)). 位 取 末.
            若 位 == (文 其 量) 则 破. 然
        环
        完后 甲 乙.
    为
    '''
    for name,s in cases:source+='切分 '+lit(s)+'.\n'
    longcases=[('long-ascii','```\n'+'a'*2300+'\r\n```\n'),('long-mixed','~~~\r\n'+('a中😀\x80'*400)+'\n~~~'),('range60', ''.join('# h\nbody\n' for _ in range(100)))]
    for name,s in longcases:
     for n in (1,2,31,32,127,1024):source+=f'块分 {lit(s)} {n}.\n'
    for char in ['a','\x7f','\x80','\u07ff','\u0800','\uffff','\U00010000','😀']:
     s=char*1024
     source+=f"甲 取 甲模 其 新状态. 乙 取 乙模 其 新状态.\n拒绝 甲 乙 {lit(s+'x')} 假 'Markdown input exceeds 1024 Unicode scalars.'.\n接入 甲 乙 {lit(s)} 真.\n拒绝 甲 乙 {lit(s+'x')} 假 'Markdown input exceeds 1024 Unicode scalars.'.\n完后 甲 乙.\n"
    source+="若 次数[2] == 0 则 卒 'range pause uncovered'. 然\n显 ('FULL_STATE_RETURNS '+(次数[0] 为 句)).\n显 ('ERROR_ORDER_CHECKS '+(次数[1] 为 句)).\n显 ('RANGE_PAUSES '+(次数[2] 为 句)).\n显 'DIFFERENTIAL_PASS'.\n"
    (out/'oracle.ru').write_text(source,encoding='utf-8',newline='\n')
    inputs={name:{'scalars':len(s),'sha256':hashlib.sha256(s.encode()).hexdigest()} for name,s in cases+longcases}
    for char in ['a','\x7f','\x80','\u07ff','\u0800','\uffff','\U00010000','😀']:
        for extra in ('','x'):
            text=char*1024+extra
            inputs[f'boundary-{ord(char)}-{len(text)}']={'scalars':len(text),'sha256':hashlib.sha256(text.encode()).hexdigest()}
    (out/'inputs.json').write_text(json.dumps({'split_cases':len(cases),'split_runs':sum(len(s)+1 for _,s in cases),'long_cases':len(longcases),'long_chunk_sizes':[1,2,31,32,127,1024],'inputs':inputs,'oracle_sha256':hashlib.sha256(source.encode()).hexdigest(),'baseline_sha256':hashlib.sha256((base/'src/markdown_policy.ru').read_bytes()).hexdigest(),'candidate_sha256':hashlib.sha256((root/'src/markdown_policy.ru').read_bytes()).hexdigest()},indent=2),encoding='utf-8')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',type=Path,required=True)
    parser.add_argument('--ru-root',type=Path,required=True)
    parser.add_argument('--cc',default='gcc')
    args=parser.parse_args(argv)
    base=args.baseline.resolve();ru=args.ru_root.resolve()
    parent=ROOT/'build/markdown-width-private';parent.mkdir(parents=True,exist_ok=True)
    out=Path(tempfile.mkdtemp(prefix='oracle-',dir=parent))
    report={'schema':1,'passed':False,'compiler_pin':PIN,'compiler_tree':TREE,
            'baseline_sha256':BASE_HASH,'candidate_sha256':CANDIDATE_HASH}
    started=time.monotonic();stage=0
    def run(command,label,cap,diagnostics=None):
        remaining=600-(time.monotonic()-started)
        require(remaining>0)
        return checked_run(command,out,label,min(cap,remaining),compile_diagnostics=diagnostics)
    def compiler_check(suffix):
        require(run(['git','-C',str(ru),'rev-parse','HEAD'],'pin-'+suffix,15).strip().decode()==PIN)
        require(run(['git','-C',str(ru),'rev-parse','HEAD^{tree}'],'tree-'+suffix,15).strip().decode()==TREE)
        require(not run(['git','-C',str(ru),'status','--porcelain','--untracked-files=all'],'clean-'+suffix,15).strip())
    try:
        stage=1;before=check_sources(base);compiler_check('before')
        # Negative output controls ensure success cannot be inferred from suffixes.
        for bad in (b'',EXPECTED+EXPECTED,EXPECTED.replace(b'12690',b'12689'),EXPECTED+b'PRIVATE'):
            try:normalized(bad)
            except (RuntimeError,UnicodeError):pass
            else:raise RuntimeError('width_output_control')
        stage=2
        portable=out/'portable'
        data=run([sys.executable,str(ROOT/'tools/test_markdown_portable.py'),
                  '--ru-root',str(ru),'--cc',args.cc,'--output',str(portable)],'portable',360)
        require(data.decode().replace('\r\n','\n')=='MARKDOWN_PORTABLE_PASS markdown_policy=221x2 markdown_selection_policy=31x2\n')
        proof=json.loads((portable/'report.json').read_text(encoding='utf-8'))
        require(proof['passed'] is True and len(proof['cases'])==4)
        require({(x['fixture'],x['backend'],x['assertions']) for x in proof['cases']}==
                {(n,b,c) for n,c in [('markdown_policy',221),('markdown_selection_policy',31)] for b in ('interpreter','host-c')})
        stage=3;generate(ROOT,base,out);source=out/'oracle.ru'
        code=('import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); '
              'from rulang.frontend import parse; from rulang.interpreter import Interpreter; '
              'p=Path(sys.argv[2]); Interpreter().execute(parse(p.read_text(encoding="utf-8")),source_path=p)')
        a=normalized(run([sys.executable,'-I','-c',code,str(ru),str(source)],'interpreter',180))
        stage=4;exe=out/('oracle.exe' if os.name=='nt' else 'oracle')
        command=[sys.executable,str(ru/'ru'),'build','--cc',args.cc,str(source),'-o',str(exe)]
        run(command,'compile',180,prepare_compile_diagnostics(command,ru,source))
        stage=5;b=normalized(run([str(exe)],'host-c',120));require(a==b)
        stage=6;require(check_sources(base)==before);compiler_check('after')
        report.update(passed=True,source_sha256=before,oracle_sha256=digest(source),
                      inputs_sha256=digest(out/'inputs.json'),output_sha256=hashlib.sha256(a).hexdigest(),
                      full_state_returns_per_backend=12690,error_checks_per_backend=3446,
                      range_pauses_per_backend=5,portable_assertions_per_backend=252)
        print('MARKDOWN_WIDTH_POLICY passed=1 portable=252 backends=2 returns=12690 errors=3446 pauses=5')
        return 0
    except Exception:
        # Private traceback is local-only; never forwarded to stdout or CI upload.
        (out/'runner-private.stderr').write_text(traceback.format_exc(),encoding='utf-8')
        # Never forward compiler stderr, path-bearing exception text or GUI data.
        print(f'MARKDOWN_WIDTH_POLICY passed=0 stage={stage}')
        return 1
    finally:
        report['stage']=stage
        (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':raise SystemExit(main())
