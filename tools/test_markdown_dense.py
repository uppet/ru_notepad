#!/usr/bin/env python3
"""Source-bridge policy oracle. Local correctness, NOT Windows acceptance.

The frozen a09 policy is independent. Each candidate return compares all 24
slots, compressed fold results, retained stack/header/closer aliases and errors.
Array mode runs ordinary Ru AST in interpreter and generated C. Native mode
uses the actual ordinary NativeMemory adapter with an explicit source manifest.
"""
from __future__ import annotations
import argparse, ast, hashlib, json, os, re, subprocess, sys, tempfile, time
from pathlib import Path
import test_markdown_width_policy as old
ROOT=Path(__file__).resolve().parents[1]
BASE_SHA='e3606ac3806d4b4b0255b10c4600f088bcdacaffab9918f62c91bd5115d648e0'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def lit(s):return "'"+s.replace('\\','\\\\').replace("'","\\'").replace('\r','\\r').replace('\n','\\n').replace('\t','\\t')+"'"
def need(x,why):
    if not x:raise RuntimeError(why)

def dense_transform(original):
    out=original.replace('算 喂入 态 文 为 句 结束 为 事实:',
                         '算 喂入视图 态 文 为 句 结束 为 事实 字节块 字节末 为 数:',1)
    out=out.replace('    长 取 文 其 量.\n','    长 取 文 其 量.\n    块始字节 取 态[23].\n',1)
    a=out.index('            若 位 >= 窗末 则\n');b=out.index('        环\n        # EOF keeps line fields',a)
    injected='''            # The byte cursor is explicit: state bytes consumed since this feed.
            # Only ASCII makes byte run length equal the ordinary scalar count.
            连长 取 0.
            若 态[6] != '' 且 态[8] == '' 且 (态[9] > 3 或 (非 态[10] 且 态[13] != 态[6])) 则
                连长 取 _密核 其 ASCII段 字节块 (态[23]-块始字节) 字节末.
            然
            若 连长 > 0 则
                若 缓始 < 0 则 缓始 取 位. 然
                位 取 位+连长. 态[23] 取 态[23]+连长. 态[1] 取 假.
            另
'''
    return out[:a]+injected+''.join('    '+line if line.strip() else line for line in out[a:b].splitlines(keepends=True))+'            然\n'+out[b:]

def drift_check(base):
    p=base/'src/markdown_policy.ru';need(sha(p)==BASE_SHA,'baseline hash')
    original=p.read_text();candidate=(ROOT/'src/markdown_policy.ru').read_text()
    start=original.index('算 喂入 态 文 为 句 结束 为 事实:');end=original.index('算 资源 态:')
    body=original[start:end]
    a=candidate.index('算 喂入视图 ');b=candidate.index('算 资源 态:')
    need(candidate[a:b]==dense_transform(body),'dense duplicated body drift')
    comment=candidate.index('# Experimental source-generated readonly-u8 bridge entry.')
    restored=candidate[len("_密核 取 外言 'markdown_ascii_kernel.ru'.\n"):comment]+candidate[b:]
    need(restored==original,'ordinary oracle/helpers drift')
    return {'baseline_policy_sha256':sha(p),'candidate_policy_sha256':sha(ROOT/'src/markdown_policy.ru'),
            'ordinary_feed_sha256':hashlib.sha256(body.encode()).hexdigest()}

EXTRA=[
 ('ascii-after-utf8','```\r\n中😀é'+('abcdef'*12)+'\r\n~~~\n```\n'),
 ('unicode-before-ascii','~~~\n    中😀last-byte\r\n~~~\n'),
 ('last-one-byte','```\nq\r\nz'),
 ('cr-carry','```\r\n\r\n中ascii\r\nlast\r\n```'),
 ('fence-prefix-late-close','~~~~\r\n  ~~~\r\n  ~~~~ no\r\n    ~~~~\r\n~~~~\n'),
 ('closer-alias-no-batch','```\nabc中</StYlE>tail\r\n```'),
 ('closed-fence-other-lines','```\nword\n```\n# heading\nbody\n'),
]

def generate(base,out,mode):
    # Reuse the established fixture corpus/stepwise compare, not its old hash gate.
    old.generate(ROOT,base,out)
    p=out/'oracle.ru';s=p.read_text()
    # Every candidate result is the real alternate policy path, not a stand-in.
    s=s.replace('果乙 取 乙模 其 喂入 乙 文[位:] 末.', '果乙 取 候选 乙 文[位:] 末.')
    s=s.replace("试 乙模 其 喂入 乙 文 末.","试 候选 乙 文 末.")
    # Capture aliases before a call, then compare retained values and identities.
    before='''            旗甲 取 甲[19]. 旗乙 取 乙[19]. 栈甲 取 甲[3]. 栈乙 取 乙[3].
            头甲 取 []. 头乙 取 []. 头位 取 0.
            循 栈甲 其 量 次
                头甲 其 增 栈甲[头位]. 头乙 其 增 栈乙[头位]. 头位 取 头位+1.
            环
'''
    after='''            若 (旗甲 == 甲[19]) != (旗乙 == 乙[19]) 或 (栈甲 == 甲[3]) != (栈乙 == 乙[3]) 则 卒 'alias identity mismatch'. 然
            别位 取 0.
            循 5 次
                若 旗甲[别位] != 旗乙[别位] 则 卒 'retained closer mismatch'. 然
                别位 取 别位+1.
            环
            头位 取 0.
            循 头甲 其 量 次
                别位 取 0.
                循 4 次
                    若 头甲[头位][别位] != 头乙[头位][别位] 则 卒 'retained header mismatch'. 然
                    别位 取 别位+1.
                环
                头位 取 头位+1.
            环
'''
    s=s.replace('            果甲 取 甲模 其 喂入',before+'            果甲 取 甲模 其 喂入',1)
    s=s.replace('            同果 果甲 果乙.',after+'            同果 果甲 果乙.',1)
    more=''
    for _,text in EXTRA:more+='切分 '+lit(text)+'.\n'
    # Repeat the editing text revision vector, including the two distinct Undo
    # revisions, at all bounded chunk sizes. This is policy replay, not GUI Undo.
    rev0='# root\r\n```\r\n中😀'+('abcde\r\n'*30)+'last\r\n'
    rev1=rev0+'x';rev2=rev0;rev3=rev1;rev4=rev0
    for idx,text in enumerate((rev0,rev1,rev2,rev3,rev4)):
        for n in (1,2,31,32,127,1024):more+=f'块分 {lit(text)} {n}.\n'
    s=s.replace("若 次数[2] == 0",more+"若 次数[2] == 0",1)
    if mode=='native':
        # Data-driven fixture traversal avoids reanalyzing the same mutating
        # policy from hundreds of top-level static call sites. No analyzer guard
        # is lifted, no policy state is discarded, and every runtime case remains.
        fixture=(ROOT/'tests/markdown_policy.ru').read_text()
        texts=[ast.literal_eval(x) for x in re.findall(r"^核例 '(?:[^'\\]|\\.)*' ('(?:[^'\\]|\\.)*')",fixture,re.M)]
        texts += ['# h\r\n\x7f\x80\u07ff\u0800\uffff\U00010000😀\r\n---','```\r\n\x7f\x80\u07ff\u0800\uffff\U00010000😀\r\n```','<!--\r\n中😀\r\n-->\r\n# h','> # 中\r\n> 😀\r\n\r\n- 中\n  x']
        texts += [t for _,t in EXTRA]
        marker=re.search(r'(?m)^[ \t]*切分 ',s);need(marker is not None,'fixture body marker')
        s=s[:marker.start()]
        s+='切们 取 ['+','.join(lit(t) for t in texts)+']. 切位 取 0.\n'
        s+='循 切们 其 量 次 切分 (""+切们[切位]). 切位 取 切位+1. 环\n'
        longs=['```\n'+'a'*2300+'\r\n```\n','~~~\r\n'+('a中😀\x80'*400)+'\n~~~',''.join('# h\nbody\n' for _ in range(100)),rev0,rev1,rev2,rev3,rev4]
        s+='长们 取 ['+','.join(lit(t) for t in longs)+']. 长位 取 0. 块们 取 [1,2,31,32,127,1024].\n'
        s+='循 长们 其 量 次 块位 取 0. 循 6 次 块分 (""+长们[长位]) 块们[块位]. 块位 取 块位+1. 环 长位 取 长位+1. 环\n'
        s+='界们 取 ['+','.join(lit(t) for t in ['a','\x7f','\x80','\u07ff','\u0800','\uffff','\U00010000','😀'])+']. 界位 取 0.\n'
        s+='''循 8 次
    文 取 ''. 循 1024 次 文 取 文+界们[界位]. 环
    甲 取 甲模 其 新状态. 乙 取 乙模 其 新状态.
    拒绝 甲 乙 (文+'x') 假 'Markdown input exceeds 1024 Unicode scalars.'.
    接入 甲 乙 文 真.
    拒绝 甲 乙 (文+'x') 假 'Markdown input exceeds 1024 Unicode scalars.'.
    完后 甲 乙. 界位 取 界位+1.
环
若 次数[2] == 0 则 卒 'range pause uncovered'. 然
显 ('FULL_STATE_RETURNS '+(次数[0] 为 句)).
显 ('ERROR_ORDER_CHECKS '+(次数[1] 为 句)).
显 ('RANGE_PAUSES '+(次数[2] 为 句)).
显 'DIFFERENTIAL_PASS'.
'''
        header='密模 取 外言 '+lit((ROOT/'src/markdown_dense.ru').as_posix())+'.\n'
        header+='算 候选 态 文 为 句 末 为 事实: 得 密模 其 喂入 态 文 末. 法\n'
    else:
        # UTF8 adaptation here is a test oracle only. Native cost uses existing
        # 密.UTF8, not this intentionally slow number-array construction.
        chars=set(''.join(ast.literal_eval(x) for x in re.findall(r"'(?:[^'\\]|\\.)*'",s)))
        table=','.join(lit(c)+':['+','.join(map(str,c.encode()))+']' for c in sorted(chars))
        header='字节表 取 {'+table+'}.\n'
        header+='''算 候选 态 文 为 句 末 为 事实:
    字节们 取 []. 字位 取 0.
    循 文 其 量 次
        单 取 字节表[文[字位]]. 节位 取 0.
        循 单 其 量 次
            字节们 其 增 单[节位]. 节位 取 节位+1.
        环
        字位 取 字位+1.
    环
    得 乙模 其 喂入视图 态 文 末 字节们 (字节们 其 量).
法
'''
    p.write_text(header+s,encoding='utf-8')
    return p

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--baseline',type=Path,required=True);ap.add_argument('--ru-root',type=Path,required=True)
    ap.add_argument('--mode',choices=('array','native'),default='array');ap.add_argument('--manifest',type=Path);ap.add_argument('--cc',default='gcc');ap.add_argument('--posix-test-host',action='store_true')
    a=ap.parse_args();base=a.baseline.resolve();ru=a.ru_root.resolve();receipt=drift_check(base)
    parent=ROOT/'build/markdown-dense-private';parent.mkdir(parents=True,exist_ok=True);out=Path(tempfile.mkdtemp(prefix=a.mode+'-',dir=parent))
    source=generate(base,out,a.mode);receipt.update(mode=a.mode,passed=False,source_sha256=sha(source),results={})
    def run(cmd,label,timeout=240):
        begin=time.monotonic()
        with (out/(label+'.stdout')).open('xb') as stdout,(out/(label+'.stderr')).open('xb') as stderr:
            r=subprocess.run(cmd,stdout=stdout,stderr=stderr,timeout=timeout)
        need(r.returncode==0,label+' failed; private log '+str(out))
        data=(out/(label+'.stdout')).read_bytes().decode().replace('\r\n','\n')
        receipt['results'][label]={'elapsed_seconds':time.monotonic()-begin,'stdout_sha256':hashlib.sha256(data.encode()).hexdigest()}
        return data
    try:
        outputs=[]
        if a.mode=='array':
            code='import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); from rulang.frontend import parse; from rulang.interpreter import Interpreter; p=Path(sys.argv[2]); Interpreter().execute(parse(p.read_text()),source_path=p)'
            outputs.append(run([sys.executable,'-I','-c',code,str(ru),str(source)],'interpreter'))
        exe=out/('oracle.exe' if os.name=='nt' else 'oracle');cmd=[sys.executable,str(ru/'ru'),'build','--cc',a.cc,str(source),'-o',str(exe)]
        if a.mode=='native':
            need(a.manifest is not None,'native mode requires explicit manifest');cmd+=['--allow-native','--experimental-mi-manifest',str(a.manifest.resolve())]
        if a.mode=='native' and os.name!='nt':
            need(a.posix_test_host,'native POSIX requires explicit test-only platform adapter')
            sys.path[:0]=[str(ru),str(ru/'tests')]
            from rulang.frontend import parse
            from rulang.modules import load_module_graph
            from rulang.compiler import Compiler
            from test_native_c_runtime import TEST_PLATFORM
            program=parse(source.read_text());graph=load_module_graph(str(source),program)
            generated=Compiler(program,graph.root,modules=graph,allow_native=True,mi_manifest=a.manifest.resolve()).compile()
            (out/'oracle-production.c').write_text(generated)
            pattern=r'/\* RU_NATIVE_PLATFORM_BEGIN \*/.*?/\* RU_NATIVE_PLATFORM_END \*/'
            host,count=re.subn(pattern,lambda _:TEST_PLATFORM,generated,flags=re.S)
            need(count==1,'exact test-platform replacement')
            guard='#error "Ru native C requires Windows x64"';need(host.count(guard)==1,'production ABI guard')
            host=host.replace(guard,'/* POSIX test artifact only; not Windows acceptance. */')
            cp=out/'oracle-host.c';cp.write_text(host)
            receipt.update(posix_test_host=True,production_c_sha256=sha(out/'oracle-production.c'),test_c_sha256=sha(cp),manifest_sha256=sha(a.manifest.resolve()))
            run([a.cc,'-std=c99','-O2','-Wno-unused-function',str(cp),'-o',str(exe),'-lm','-ldl','-pthread'],'compile')
        else:run(cmd,'compile')
        outputs.append(run([str(exe)],'host-c'))
        need(all(x==outputs[0] for x in outputs),'backend outputs disagree')
        need(re.fullmatch(r'FULL_STATE_RETURNS [0-9]+\nERROR_ORDER_CHECKS [0-9]+\nRANGE_PAUSES [1-9][0-9]*\nDIFFERENTIAL_PASS\n',outputs[0]) is not None,'exact output control')
        receipt.update(passed=True,output=outputs[0],executable_sha256=sha(exe));need(drift_check(base)=={k:receipt[k] for k in drift_check(base)},'sources drifted')
        print('MARKDOWN_DENSE_ORACLE mode='+a.mode+' passed=1 '+outputs[0].replace('\n',' ').strip())
    finally:(out/'report.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
