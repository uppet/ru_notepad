#!/usr/bin/env python3
"""Bounded 1 MB policy-consumer cost probe, NOT Windows/UI/end-to-end acceptance.

Both paths share one manifest-compiled binary/compiler/source and exact synthetic
fixture. Candidate timings include UTF8 allocation/copy, all borrow boundaries,
normal Ru state/byte/result work and cleanup. No parser counter replaces policy.
"""
from __future__ import annotations
import argparse,hashlib,json,os,re,subprocess,sys,tempfile,time
from pathlib import Path
from test_markdown_dense import ROOT,drift_check,lit,need,sha

ORDER=('ordinary','dense','dense','ordinary','ordinary','dense','dense','ordinary')

def fixture():
    head=b'# Heading\n\n~~~\n';tail=b'codebody';fill=b'code text\n';n=1000000-len(head)-len(tail)
    return head+(fill*(n//len(fill)+1))[:n]+tail

def source_text(data):
    chunks=[data[i:i+1024].decode() for i in range(0,len(data),1024)]
    unique=list(dict.fromkeys(chunks));indexes=[unique.index(x) for x in chunks]
    s='策 取 外言 '+lit((ROOT/'src/markdown_policy.ru').as_posix())+'.\n'
    s+='密策 取 外言 '+lit((ROOT/'src/markdown_dense.ru').as_posix())+'.\n'
    s+='块文们 取 ['+','.join(map(lit,unique))+'].\n块号们 取 ['+','.join(map(str,indexes))+'].\n'
    s+='''算 元初 参数 为 句 阵:
    若 参数 其 量 != 1 则 卒 'cost arm required'. 然
    快 取 参数[0] == 'dense'.
    若 非 快 且 参数[0] != 'ordinary' 则 卒 'cost arm invalid'. 然
    态 取 策 其 新状态. 位 取 0. 已用 取 0.
    循 块号们 其 量 次
        文 取 块文们[块号们[位]]. 末 取 位+1 == (块号们 其 量).
        若 快 则
            果 取 密策 其 喂入 态 文 末.
        另
            果 取 策 其 喂入 态 文 末.
        然
        若 果['used'] != (文 其 量) 或 果['finished'] != 末 则 卒 'cost feed mismatch'. 然
        已用 取 已用+果['used'].
        若 果['bytes'] != 已用 则 卒 'cost byte mismatch'. 然
        位 取 位+1.
    环
    若 非 态[2] 或 态[23] != 1000000 或 态[0] != 100000 则 卒 'cost final state mismatch'. 然
    显 'POLICY_COST_PASS bytes=1000000 lines=100001'.
    得 0.
法
'''
    return s,chunks

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--ru-root',type=Path,required=True);ap.add_argument('--baseline',type=Path,required=True);ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--cc',default='gcc');ap.add_argument('--posix-test-host',action='store_true');a=ap.parse_args()
    proof=drift_check(a.baseline.resolve());ru=a.ru_root.resolve();data=fixture();source,chunks=source_text(data)
    parent=ROOT/'build/markdown-dense-private';parent.mkdir(parents=True,exist_ok=True);out=Path(tempfile.mkdtemp(prefix='cost-',dir=parent));rp=out/'cost.ru';rp.write_text(source)
    report={'schema':1,'scope':'policy-consumer-only; not Windows GUI or end-to-end acceptance','passed':False,'source_sha256':sha(rp),'fixture_sha256':hashlib.sha256(data).hexdigest(),'manifest_sha256':sha(a.manifest.resolve()),'proof':proof,'raw':[]}
    def run(cmd,label,cap=180):
        from test_markdown_portable import checked_run
        begin=time.perf_counter();stdout=checked_run(cmd,out,label,cap)
        return stdout,time.perf_counter()-begin
    try:
        sys.path[:0]=[str(ru),str(ru/'tests')]
        from rulang.frontend import parse
        from rulang.modules import load_module_graph
        from rulang.compiler import Compiler
        program=parse(source);graph=load_module_graph(str(rp),program)
        compiler=Compiler(program,graph.root,modules=graph,allow_native=True,mi_manifest=a.manifest.resolve());code=compiler.compile()
        prod=out/'cost-production.c';prod.write_text(code);cp=prod
        report.update(production_c_sha256=sha(prod),native_analysis_steps=compiler.native_plan._steps)
        if os.name!='nt':
            need(a.posix_test_host,'explicit POSIX test adapter required')
            from test_native_c_runtime import TEST_PLATFORM
            code,n=re.subn(r'/\* RU_NATIVE_PLATFORM_BEGIN \*/.*?/\* RU_NATIVE_PLATFORM_END \*/',lambda _:TEST_PLATFORM,code,flags=re.S);need(n==1,'platform marker')
            guard='#error "Ru native C requires Windows x64"';need(code.count(guard)==1,'ABI guard');code=code.replace(guard,'/* POSIX test artifact, not Windows evidence. */')
            cp=out/'cost-host.c';cp.write_text(code);report.update(posix_test_host=True,test_c_sha256=sha(cp))
        exe=out/('cost.exe' if os.name=='nt' else 'cost');cmd=[a.cc,'-std=c99','-O2','-Wno-unused-function',str(cp),'-o',str(exe),'-lm']
        if os.name!='nt':cmd+=['-ldl','-pthread']
        run(cmd,'compile');report['binary_sha256']=sha(exe)
        for i,arm in enumerate(ORDER):
            stdout,wall=run([str(exe),arm],f'run-{i}')
            need(stdout.replace(b'\r\n',b'\n')==b'POLICY_COST_PASS bytes=1000000 lines=100001\n','cost exact output')
            report['raw'].append({'index':i,'arm':arm,'wall_seconds':wall});(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        report['pairs']=[{'ordinary_index':i,'dense_index':j,'dense_over_ordinary':report['raw'][j]['wall_seconds']/report['raw'][i]['wall_seconds']} for i,j in ((0,1),(3,2),(4,5),(7,6))]
        # The exact fixture makes every feed after the first eligible. This is
        # logical copied input plus NUL bytes, NOT allocator/GC measurement.
        adapted=chunks[1:]
        report['input_adaptation']={'feeds_total':len(chunks),'utf8_copies':len(adapted),'text_bytes':sum(len(x.encode()) for x in adapted),'nul_padding_bytes':len(adapted),'zero_copy':False}
        report['passed']=True;print('MARKDOWN_DENSE_COST '+json.dumps({'passed':True,'scope':'POSIX policy only' if os.name!='nt' else 'Windows policy only','pairs':report['pairs'],'out':str(out)},separators=(',',':')))
    finally:(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
