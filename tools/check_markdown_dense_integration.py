#!/usr/bin/env python3
"""Generate both actual main.ru arms; prove exact one-fact C difference.

This checks explicit build wiring, never links or starts a Windows GUI.
"""
import argparse,difflib,hashlib,json,sys,tempfile,time
from pathlib import Path
from test_markdown_dense import ROOT,need,sha
from markdown_dense_build import prepare_graph,verify_receipt

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--ru-root',type=Path,required=True);ap.add_argument('--manifest',type=Path,required=True);a=ap.parse_args();ru=a.ru_root.resolve();sys.path.insert(0,str(ru))
    from rulang.frontend import parse
    from rulang.modules import load_module_graph
    from rulang.compiler import Compiler
    parent=ROOT/'build/markdown-dense-private';parent.mkdir(parents=True,exist_ok=True);out=Path(tempfile.mkdtemp(prefix='main-',dir=parent));source=ROOT/'src/main.ru';results={};codes={}
    paths=[ru/'rulang'/p for p in ('frontend.py','compiler.py','mi_source.py','mi_ir.py','mi_bridge.h','native_c.py','native_runtime.h')]
    compiler_before={p.name:sha(p) for p in paths};report={'passed':False,'windows_executed':False,'compiler_inputs':compiler_before,'arms':results}
    try:
        for arm in ('ordinary','dense'):
            ast=parse(source.read_text(encoding='utf-8'));graph=load_module_graph(str(source),ast);receipt=prepare_graph(ROOT,graph,a.manifest,arm);t=time.monotonic()
            compiler=Compiler(ast,graph.root,modules=graph,allow_native=True,mi_manifest=a.manifest.resolve());code=compiler.compile();cp=out/(arm+'.c');cp.write_text(code,encoding='utf-8');codes[arm]=code
            verify_receipt(ROOT,a.manifest,arm,receipt)
            results[arm]={'generated_c_sha256':sha(cp),'bytes':cp.stat().st_size,'native_analysis_steps':compiler.native_plan._steps,'generation_seconds':time.monotonic()-t,'activation_receipt':receipt}
        changed=[x for x in difflib.ndiff(codes['ordinary'].splitlines(),codes['dense'].splitlines()) if x.startswith(('- ','+ '))]
        need(len(changed)==2 and 'v_fact(0)' in changed[0] and changed[0][2:].replace('v_fact(0)','v_fact(1)')==changed[1][2:],'not exactly one enabled fact')
        need(compiler_before=={p.name:sha(p) for p in paths},'compiler drift during verification')
        report.update(passed=True,generated_difference='one v_fact(0) -> v_fact(1)',source_unchanged=True)
        print('MARKDOWN_DENSE_MAIN passed=1 arms=2 changed_facts=1 windows_executed=0')
    finally:(out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
