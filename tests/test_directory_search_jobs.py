"""Execute the unchanged Ru scheduler/core against a deterministic transport.

Portable evidence, NOT Windows native traversal/FFI or GUI acceptance. Only the
private transport import is rebound; no Python implementation of search is used.
"""
import json
import os
import sys
import shutil
import argparse
import re
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPILER = Path(os.environ['RU_ROOT']) if os.environ.get('RU_ROOT') else None
PIN = 'c3bb177c6a15e90821e5495cc74b0fdfc39b893a'


def literal(value):
    if isinstance(value, bool): return '真' if value else '假'
    if value is None: return '空'
    if isinstance(value, list):
        if len(value)>128 and all(v==97 for v in value[:-1]): return f'(批字 {len(value)-1} {value[-1]})'
        return '[' + ','.join(map(literal, value)) + ']'
    if isinstance(value, dict): return '{' + ','.join(literal(k)+':'+literal(v) for k,v in value.items()) + '}'
    return json.dumps(value, ensure_ascii=False)


def event(kind, seq, file=1, size=1, offset=0, data=None, **kw):
    e = dict(kind=kind,sequence=seq,fileSequence=file,generation=0,rawSize=size,
             offset=offset,flags=1 if kind==3 else 0,path='a',identity='4294967295:4294967295/0:1',
             stamp='4294967295:4294967295',readBytes=0,length=len(data or []),
             bytes=data or [],reason=0,status=0,files=file,dirs=1,skipped=0,errors=0)
    e.update(kw)
    return e


def file_events(raw, first=1, file=1):
    return [event(1,first,file,len(raw)),event(2,first+1,file,len(raw),data=raw),
            event(3,first+2,file,len(raw),len(raw))]


PRELUDE = """搜 取 外言 './directory_search.ru'.
假输 取 外言 './directory_io.ru'.
算 批字 长 尾:
    果 取 []. 循 长 次 果 其 增 97. 环. 果 其 增 尾. 得 果.
法.
算 确认 条 名:
    若 非 条 则 卒 名. 然 得 空.
法
算 完成 态:
    次数 取 0.
    循 10000 次
        若 态['status'] != 'running' 则 破. 然
        搜 其 步进 态. 次数 取 次数+1.
        确认 (态['lastRawBytes'] <= 4096) 'raw budget'.
        确认 (态['lastWork'] <= 8192) 'work budget'.
        确认 (态['lastPublished'] <= 16) 'publication budget'.
    环
    确认 (态['status'] != 'running') 'termination'.
    搜 其 维护. 得 态.
法
"""


def fixture():
    src = PRELUDE
    cases=[]
    cases.append(('literal',file_events([97])+[event(6,4)],'complete',1))
    cases.append(('nonoverlap',file_events([97]*7)+[event(6,4)],'complete',7))
    cases.append(('late-invalid',file_events([97,255])+[event(6,4)],'limited',0))
    cases.append(('nul-tail',file_events([97,0])+[event(6,4)],'limited',0))
    cases.append(('utf16',file_events([255,254,97,0])+[event(6,4)],'complete',1))
    cases.append(('chunked',file_events([97]*1025)+[event(6,4)],'complete',1025))
    cases.append(('row-cap',file_events([97]*2001)+[event(6,4)],'limited',2000))
    cases.append(('cap-malformed-tail',file_events([97]*2001+[255])+[event(6,4)],'limited',0))
    cases.append(('skip-in-file',[event(1,1),event(4,2,reason=4),event(6,3)],'limited',0))
    cases.append(('skip-directory',[event(4,1,file=0,reason=2,flags=4),event(6,2,file=0)],'limited',0))
    cases.append(('fatal-root',[event(5,1,file=0,reason=2,flags=6)],'failed',0))
    cases.append(('missing-terminal',file_events([97]),'failed',1))
    cases.append(('gap',[event(1,2)],'failed',0))
    cases.append(('wrong-generation',[event(1,1,generation=4294967295)],'failed',0))
    cases.append(('data-before-start',[event(2,1,data=[97])],'failed',0))
    cases.append(('duplicate-start',[event(1,1),event(1,2)],'failed',0))
    cases.append(('wrong-offset',[event(1,1),event(2,2,offset=1,data=[97])],'failed',0))
    cases.append(('wrong-file',[event(1,1),event(2,2,file=2,data=[97])],'failed',0))
    cases.append(('short-end',[event(1,1),event(3,2)],'failed',0))
    cases.append(('wrong-path',[event(1,1),event(2,2,data=[97],path='b')],'failed',0))
    cases.append(('wrong-identity',[event(1,1),event(2,2,data=[97],identity='0:0/0:0')],'failed',0))
    cases.append(('wrong-stamp',[event(1,1),event(2,2,data=[97],stamp='0:0')],'failed',0))
    cases.append(('gap-file',[event(1,1,file=2)],'failed',0))
    cases.append(('directory-skip-preserves-file',[event(1,1),event(4,2,file=0,flags=4,reason=2,files=1),event(2,3,data=[97]),event(3,4,offset=1),event(6,5)],'limited',1))
    cases.append(('wrong-size',[event(1,1),event(2,2,size=2,data=[97])],'failed',0))
    cases.append(('end-before-start',[event(3,1)],'failed',0))
    cases.append(('job-end-before-end',[event(1,1),event(6,2)],'failed',0))
    cases.append(('old-generation-discarded',[event(1,99,generation=1)]+file_events([97])+[event(6,4)],'complete',1))
    cases.append(('files-counter-regression',[event(1,1),event(4,2,file=0,flags=4,reason=2,files=0)],'failed',0))
    for key in ('dirs','skipped','errors','readBytes'):
        high={'dirs':2,'skipped':1,'errors':1,'readBytes':2}[key]
        a=event(1,1); b=event(2,2,data=[97]); a[key]=high; b[key]=high-1
        if key=='errors': a['skipped']=b['skipped']=1
        cases.append((key+'-counter-regression',[a,b],'failed',0))
    cases.append(('preserve-prior',file_events([97])+[event(1,4,file=2),event(2,6,file=2,data=[97])],'failed',1))
    for name,events,status,count in cases:
        src += '假输 其 设置 ('+literal(events)+').\n'
        src += "态 取 搜 其 新建 'root' 'a'. 完成 态.\n"
        src += f"确认 (态['status'] == '{status}') '{name} status'.\n"
        src += f"确认 ((态['results'] 其 量) == {count}) '{name} rows'.\n"
        src += f"显 'PASS {name}'.\n"
    limit_cases=[
        ('files-limit-accounting',[event(4,1,file=0,flags=4,reason=6,skipped=1),event(6,2,file=0,reason=6,status=6,skipped=1)],6,0,0),
        ('dirs-limit-accounting',[event(4,1,file=0,flags=4,reason=7,dirs=2000,skipped=1),event(6,2,file=0,reason=7,status=7,dirs=2000,skipped=1)],7,0,1),
        ('read-limit-accounting',[event(1,1),event(4,2,reason=9,readBytes=268435456,skipped=1),event(6,3,reason=9,status=9,readBytes=268435456,skipped=1)],9,1,0)]
    for name,events,reason,files,dirs in limit_cases:
        src+='假输 其 设置 ('+literal(events)+").\n态 取 搜 其 新建 'root' 'a'. 完成 态.\n"
        src+=f"确认 (态['status'] == 'limited' 且 态['partial']) '{name} partial'.\n"
        src+=f"确认 (态['limitReason'] == 'native-{reason}') '{name} reason'.\n"
        src+=f"确认 (态['reasonCounts']['native-{reason}'] == 1) '{name} exact occurrence'.\n"
        src+=f"确认 (态['filesSkipped'] == {files} 且 态['dirsSkipped'] == {dirs}) '{name} scope counts'.\n"
        src+=f"确认 ((态['results'] 其 量) == 0) '{name} no provisional rows'. 显 'PASS {name}'.\n"
    src+='假输 其 设置 ('+literal(file_events([97]*40)+[event(6,4)])+').\n'
    src+="""态 取 搜 其 新建 'root' 'a'.
循 1000 次
    若 (态['results'] 其 量) > 0 或 态['status'] != 'running' 则 破. 然.
    搜 其 步进 态.
环.
确认 (态['status'] == 'running' 且 态['filesSearched'] == 1) 'validated file counted at first publication'.
确认 ((态['results'] 其 量) == 16 且 态['lastPublished'] == 16) 'first publication batch'.
搜 其 取消 态.
确认 (态['status'] == 'cancelled' 且 态['filesSearched'] == 1 且 (态['results'] 其 量) == 16) 'cancel preserves validated file statistics'.
循 20 次 搜 其 步进 态. 搜 其 维护. 环.
确认 (态['filesSearched'] == 1 且 (态['results'] 其 量) == 16) 'no late rows or duplicate file count'.
确认 (非 (搜 其 忙)) 'cancel publication retires'.
显 'PASS cancel-during-publication'.
"""
    # Immediate cancellation before and after every tick of a multi-file job.
    events=file_events([97])+file_events([97]*100,4,2)+[event(6,7,file=2)]
    src += '中断事件 取 '+literal(events)+'.\n'
    src += """界 取 0.
循 30 次
    假输 其 设置 中断事件.
    # Rebuild events' generation, since the transport annotates its owned copies.
    位 取 0. 循 中断事件 其 量 次 中断事件[位] 其 增 'generation' 0. 位 取 位+1. 环
    态 取 搜 其 新建 'root' 'a'.
    循 界 次 若 态['status'] == 'running' 则 搜 其 步进 态. 然 环
    若 态['status'] == 'running' 则
        假输 其 拦住 真. 搜 其 取消 态.
        确认 (态['status'] == 'cancelled') 'cancel immediate'.
        确认 (搜 其 忙) 'retiring busy'.
        后 取 搜 其 新建 'root' 'a'. 确认 (后['error'] == 'directory-busy') 'no replacement'.
        数 取 态['results'] 其 量. 搜 其 步进 态.
        确认 ((态['results'] 其 量) == 数) 'no late publish'.
        假输 其 拦住 假. 搜 其 维护. 确认 (非 (搜 其 忙)) 'hidden maintenance'.
    另 搜 其 维护. 然
    界 取 界+1.
环
显 'PASS interrupt-all-ticks'.
确认 ((搜 其 检查查询 '')['status'] == 'invalid-query') 'empty query'.
长词 取 ''. 循 257 次 长词 取 长词+'a'. 环
确认 ((搜 其 检查查询 长词)['status'] == 'invalid-query') 'long query'.
确认 ((搜 其 检查查询 '😀')['utf8Bytes'] == 4) 'numeric unicode query'.
搜 其 关停.
态 取 搜 其 新建 'root' 'a'. 确认 (态['status'] == 'failed') 'shutdown prevents start'.
显 'PASS query-shutdown'.
"""
    src = re.sub(r'(?<!\w)(然|环|终|法)(?![\w.。])', r'\1.', src)
    return src, [f'PASS {c[0]}' for c in cases]+[f'PASS {c[0]}' for c in limit_cases]+['PASS cancel-during-publication','PASS interrupt-all-ticks','PASS query-shutdown']


class DirectorySearchJobsTests(unittest.TestCase):
    def test_production_adapter_decoder_interpreter_and_c(self):
        self.assertIsNotNone(COMPILER, 'Set RU_ROOT or --ru-root')
        sys.path.insert(0, str(COMPILER))
        from rulang.frontend import parse
        source=(ROOT/'src/directory_io.ru').read_text()
        nodes=parse(source); lines=source.splitlines(keepends=True); extracted=''
        for name in ('_半','_身份','解事件','数据'):
            index=next(i for i,n in enumerate(nodes) if n.kind=='function' and n.data['name']==name)
            first=nodes[index].token.line-1
            last=nodes[index+1].token.line-1 if index+1<len(nodes) else len(lines)
            extracted+=''.join(lines[first:last])
        # Only native Unicode rendering is substituted, arithmetic/validation and
        # raw DATA slicing are byte-for-byte production function bodies.
        code="""算 文本 点们: 得 'path'. 法.
算 确认 条 名: 若 非 条 则 卒 名. 然. 得 空. 法.
算 基础:
    字们 取 []. 循 2048 次 字们 其 增 0. 环.
    字们[0] 取 65536. 字们[1] 取 8192. 字们[2] 取 1.
    字们[4] 取 1. 字们[5] 取 1. 字们[6] 取 1.
    字们[8] 取 1. 字们[10] 取 1. 字们[11] 取 1.
    字们[18] 取 1. 字们[28] 取 97.
    字们[20] 取 4294967295. 字们[21] 取 4294967295.
    字们[24] 取 4294967295. 字们[25] 取 4294967295.
    得 字们.
法.
"""+extracted
        code+="""字们 取 基础. 事 取 解事件 字们.
确认 (事['identity'] == '4294967295:4294967295/0:0') 'exact identity'.
确认 (事['stamp'] == '4294967295:4294967295') 'exact stamp'.
显 'PASS decoder exact u64'.
字们 取 基础. 字们[2] 取 2. 字们[9] 取 4096. 字们[18] 取 4096.
位 取 540. 循 1024 次 字们[位] 取 4294967295. 位 取 位+1. 环.
事 取 解事件 字们. 位 取 0.
循 8 次
    块 取 数据 事 位. 确认 ((块 其 量) == 512) 'bounded detached data'.
    确认 (块[0] == 255 且 块[511] == 255) 'unsigned byte unpack'. 位 取 位+512.
环.
显 'PASS decoder data slices'.
"""
        cases=[(0,0),(1,8191),(2,0),(2,7),(3,13),(4,0),(5,0),(6,2),(6,0),(10,2),
               (7,3),(8,1024),(9,1),(10,10001),(11,2001),(13,1),(14,1),
               (15,1),(16,1),(17,1),(19,1),(27,1),(16,8388609),(18,8388609),
               (26,268435457),(28,0),(28,55296),(28,56320),(29,1),
               (540,1),(1564,1),(2047,1)]
        for i,(offset,value) in enumerate(cases):
            code+=f"字们 取 基础. 字们[{offset}] 取 {value}. 拒 取 [假].\n"
            code+="试 解事件 字们. 救 因 拒[0] 取 真. 终.\n"
            code+=f"确认 拒[0] 'reject {i}'. 显 'PASS decoder reject {i}'.\n"
        code+="""字们 取 基础. 字们[6] 取 10000. 字们[10] 取 10000. 字们[11] 取 2000.
事 取 解事件 字们. 确认 (事['files'] == 10000 且 事['dirs'] == 2000) 'exact charged limits accepted'.
显 'PASS decoder exact counter limits'.
字们[2] 取 4. 字们[3] 取 2. 字们[7] 取 4. 字们[6] 取 0.
位 取 16. 循 10 次 字们[位] 取 0. 位 取 位+1. 环.
事 取 解事件 字们. 确认 (事['fileSequence'] == 0 且 事['files'] == 10000) 'directory scope counters'.
显 'PASS decoder directory scope counter'.
字们[6] 取 1. 拒 取 [假]. 试 解事件 字们. 救 因 拒[0] 取 真. 终.
确认 拒[0] 'directory scope must be zero'. 显 'PASS decoder reject directory scope sequence'.
"""
        expected=['PASS decoder exact u64','PASS decoder data slices']+[f'PASS decoder reject {i}' for i in range(len(cases))]+['PASS decoder exact counter limits','PASS decoder directory scope counter','PASS decoder reject directory scope sequence']
        with tempfile.TemporaryDirectory(prefix='directory-adapter-') as directory:
            out=Path(directory); fixture=out/'fixture.ru'; fixture.write_text(code)
            binary=out/('fixture.exe' if os.name=='nt' else 'fixture')
            gcc=shutil.which('gcc'); self.assertIsNotNone(gcc)
            for i,cmd in enumerate([[sys.executable,str(COMPILER/'ru'),'run',str(fixture)],
                [sys.executable,str(COMPILER/'ru'),'build','--cc',gcc,str(fixture),'-o',str(binary)], [str(binary)]]):
                result=subprocess.run(cmd,text=True,capture_output=True,timeout=120)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                if i!=1:
                    self.assertEqual(result.stderr,'',result.stderr)
                    self.assertEqual(result.stdout.splitlines(),expected,result.stdout+result.stderr)

    def test_real_ru_orchestration_interpreter_and_c(self):
        self.assertIsNotNone(COMPILER, 'Set RU_ROOT or pass --ru-root to the clean pinned compiler')
        self.assertTrue((COMPILER/'ru').is_file(), 'Pinned compiler ru entry point is required')
        gcc = shutil.which('gcc')
        self.assertIsNotNone(gcc, 'GCC is required; no skipped backend')
        self.assertEqual(subprocess.check_output(['git','-C',str(COMPILER),'rev-parse','HEAD'],text=True).strip(),PIN)
        self.assertEqual(subprocess.check_output(['git','-C',str(COMPILER),'status','--porcelain'],text=True),'')
        with tempfile.TemporaryDirectory(prefix='directory-jobs-') as directory:
            out=Path(directory)
            source=(ROOT/'src/directory_search.ru').read_text()
            (out/'directory_search.ru').write_text(source.replace("'directory_text.ru'",literal(str(ROOT/'src/directory_text.ru'))))
            (out/'directory_io.ru').write_text((ROOT/'tests/directory_search_mock.ru').read_text())
            source,expected=fixture(); (out/'fixture.ru').write_text(source)
            outputs=[]
            binary = out/('fixture.exe' if os.name == 'nt' else 'fixture')
            commands=[[sys.executable,str(COMPILER/'ru'),'run',str(out/'fixture.ru')],
                      [sys.executable,str(COMPILER/'ru'),'build','--cc',gcc,str(out/'fixture.ru'),'-o',str(binary)],
                      [str(binary)]]
            for i,cmd in enumerate(commands):
                p=subprocess.run(cmd,text=True,capture_output=True,timeout=240)
                self.assertEqual(p.returncode,0,p.stdout[-3000:]+p.stderr[-3000:])
                if i!=1:
                    self.assertEqual(p.stderr,'',p.stderr)
                    self.assertEqual(p.stdout.splitlines(),expected,p.stdout+p.stderr)
                    outputs.append(p.stdout)
            self.assertEqual(outputs[0],outputs[1])

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--ru-root',type=Path); args,remaining=parser.parse_known_args()
    if args.ru_root: COMPILER=args.ru_root.resolve()
    unittest.main(argv=[sys.argv[0]]+remaining)
