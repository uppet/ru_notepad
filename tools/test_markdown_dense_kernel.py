#!/usr/bin/env python3
"""Actual notepad source-kernel valid-range differential; no performance claim."""
import argparse,hashlib,json,os,random,subprocess,sys,tempfile
from pathlib import Path
from test_markdown_dense import ROOT,need,sha

def cases():
    vectors=[b'',b'\x00',b'a',b'>',b'\r',b'\n',b'\x7f',b'\x80',b'\xff',b'last\x00byte',b'ABC\r\n>XYZ','中😀ASCII'.encode()]
    vectors += [bytes([97,x,98]) for x in range(256)]
    rng=random.Random(20261022);vectors += [bytes(rng.randrange(256) for _ in range(rng.randrange(1,25))) for _ in range(50)]
    out=[]
    for data in vectors:
        for begin in range(len(data)+1):
            for end in range(begin,len(data)+1):
                at=begin
                while at<end and data[at]<128 and data[at] not in (10,13,62):at+=1
                out.append([list(data),begin,end,at-begin])
    return out

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--ru-root',type=Path,required=True);ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--cc',default='gcc');a=ap.parse_args()
    ru=a.ru_root.resolve();sys.path.insert(0,str(ru));from rulang.frontend import parse
    from rulang.modules import load_module_graph
    from rulang.mi_source import MiSourcePlan
    from rulang.interpreter import Interpreter
    p=ROOT/'src/markdown_ascii_kernel.ru';program=parse(p.read_text());graph=load_module_graph(str(p),program);plan=MiSourcePlan(graph,a.manifest.resolve());tests=cases()
    parent=ROOT/'build/markdown-dense-private';parent.mkdir(parents=True,exist_ok=True);out=Path(tempfile.mkdtemp(prefix='kernel-',dir=parent));receipt={'passed':False,'source_sha256':sha(p),'manifest_sha256':sha(a.manifest.resolve()),'case_count':len(tests),'includes_zero_byte':True,'invalid_ranges':'ordinary bridge separately; not this compute-only harness'}
    try:
        i=Interpreter();i.execute(program,source_path=p);fn=i.function_values['ASCII段']
        for data,begin,end,want in tests:
            got=i.invoke_value(fn.node,fn,[(None,list(map(float,data))),(None,float(begin)),(None,float(end))]);need(got==want,'ordinary source oracle')
        c=plan.compute_source('c')+'\n#include <stdio.h>\nint main(void){\n'
        for idx,(data,begin,end,want) in enumerate(tests):
            c+='{uint8_t data[]={' + ','.join(map(str,data or [0]))+'};RuMiResult r=ru_mi_kernel_0((RuMiView){data,'+str(len(data))+'},'+str(begin)+','+str(end)+');if(r.status!=0||r.value!='+str(want)+')return 1;}\n'
        c+='puts("KERNEL_PASS");return 0;}\n';cp=out/'kernel.c';cp.write_text(c);exe=out/('kernel.exe' if os.name=='nt' else 'kernel');subprocess.run([a.cc,'-std=c99','-O2',str(cp),'-o',str(exe)],check=True,timeout=120)
        got=subprocess.check_output([str(exe)],timeout=30);need(got.replace(b'\r\n',b'\n')==b'KERNEL_PASS\n','generated C output')
        js=out/'kernel.js';js.write_text(plan.compute_source('js'));fixtures=out/'cases.json';fixtures.write_text(json.dumps(tests))
        harness=out/'runner.js';harness.write_text("const k=require('./kernel.js').ru_mi_kernel_0;const t=require('./cases.json');for(const [d,b,e,w] of t){const r=k(Uint8Array.from(d),b,e);if(r.status!==0||r.value!==w)throw Error('kernel mismatch');}console.log('KERNEL_PASS');\n")
        got=subprocess.check_output(['node',str(harness)],timeout=30);need(got.replace(b'\r\n',b'\n')==b'KERNEL_PASS\n','generated JS output')
        receipt.update(passed=True,c_sha256=sha(cp),js_sha256=sha(js),fixture_sha256=sha(fixtures),backends=['ordinary-interpreter','generated-c','generated-js']);print('MARKDOWN_DENSE_KERNEL passed=1 cases='+str(len(tests))+' backends=3')
    finally:(out/'report.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
