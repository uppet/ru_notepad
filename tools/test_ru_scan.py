#!/usr/bin/env python3
"""Bounded C scanner tests, with the independent pure-Ru oracle as authority.

--library accepts a prebuilt host-loadable DLL/.so. A Windows PE must be tested
on Windows, never through Wine. Default builds a local GCC shared object.
--ru-root runs real interpreter/native-C style+fold differential tests.
--benchmark measures C scanning plus real generated Ru event consumption.
"""
import argparse, ast, ctypes as C, hashlib, json, os, pathlib, random, re, subprocess, sys, time
ROOT=pathlib.Path(__file__).resolve().parents[1]
BUILD=ROOT/'build/logs/014/ru-scan'
class Event(C.Structure): _fields_=[('head',C.c_uint64),('tail',C.c_uint64)]
class Result(C.Structure):
    _fields_=[(n,C.c_uint32) for n in ('status','consumed','styled','events','line','done')]+[('start',C.c_uint64),('bytes',C.c_uint64)]
def q(s): return "'"+s.replace('\\','\\\\').replace("'","\\'").replace('\r','\\r').replace('\n','\\n').replace('\t','\\t')+"'"
def literal(v):
    if isinstance(v,bool): return '真' if v else '假'
    if isinstance(v,list):return '['+','.join(map(literal,v))+']'
    return str(v)
def configuration():
    s=(ROOT/'src/ru_lexical.ru').read_text(encoding='utf-8')
    tags=ast.literal_eval(re.search(r'^_语码 取 (.*)\.$',s,re.M)[1]);styles=ast.literal_eval(re.search(r'^_词色 取 (.*)\.$',s,re.M)[1])
    words={k:(v,styles.get(k,7 if v>=100 else 8)) for k,v in tags.items() if 0<v<200}
    words.update({k:(tags.get(k,0),v) for k,v in styles.items()})
    return ''.join(f'{tag}:{style}:{word}\n' for word,(tag,style) in words.items()).encode()
class Scanner:
    def __init__(self,path):
        self.dll=C.CDLL(str(path));d=self.dll;p=C.c_void_p;u=C.c_uint32
        for name,args in {'abi':[],'config_size':[],'state_size':[],'config_init':[p,u,p,u], 'state_init':[p,u], 'state_copy':[p,p,u],'state_equal':[p,p], 'feed':[p,p,p,u,u,u,p,u,p,u,p]}.items():
            f=getattr(d,'ru_scan_'+name);f.argtypes=args;f.restype=u
        assert d.ru_scan_abi()==0x10000 and C.sizeof(Result)==40 and C.sizeof(Event)==16
        self.config=C.create_string_buffer(d.ru_scan_config_size());cfg=configuration()
        assert d.ru_scan_config_init(self.config,len(self.config),cfg,len(cfg))==0
    def state(self):
        s=C.create_string_buffer(self.dll.ru_scan_state_size());assert self.dll.ru_scan_state_init(s,len(s))==0;return s
    def scan(self,data,chunk=1024,capacity=64,keep_batches=True):
        state=self.state();styles=bytearray([255])*len(data);batches=[];all_events=[];feed=0;done=False;calls=0;max_ns=0
        while not done:
            window=data[feed:feed+chunk];offset=0;eof=feed+len(window)==len(data)
            while True:
                out=(C.c_uint8*(len(window)+16))();events=(Event*capacity)();r=Result();before=bytes(state)
                start=time.perf_counter_ns();status=self.dll.ru_scan_feed(self.config,state,window,len(window),offset,eof,out,len(out),events,capacity,C.byref(r));max_ns=max(max_ns,time.perf_counter_ns()-start);calls+=1
                assert status in (0,1),(status,feed,offset,window)
                assert r.status==status and r.events<=capacity and r.consumed<=len(window)-offset
                assert r.bytes==r.start+r.styled and r.bytes<=len(data)
                styles[r.start:r.bytes]=bytes(out[:r.styled]);decoded=[]
                for e in events[:r.events]:
                    v=[e.head&255,(e.head>>8)&255,(e.head>>16)&255,(e.head>>24)&0xffffffff,e.tail&0xffffffff,e.tail>>32]
                    decoded.append(v);all_events.append(v)
                    if v[0]==1 and v[2]!=8:styles[v[3]:v[3]+v[4]]=bytes([v[2]])*v[4]
                if keep_batches:batches.append([decoded,int(r.bytes),r.line,bool(r.done)])
                offset+=r.consumed;done=bool(r.done)
                if status==1:assert r.consumed or r.styled or r.events,'OUTPUT_FULL must progress'
                if status==0 or done:break
                assert calls<max(100,20*len(data)+20),'unbounded feed loop'
            feed+=offset
            assert offset==len(window)
            if not done and not window:raise AssertionError('unexpected empty input stall')
        assert feed==len(data) and 255 not in styles
        # Repeated EOF is explicitly idempotent.
        r=Result();out=(C.c_uint8*16)();ev=(Event*8)();copy=bytes(state)
        assert self.dll.ru_scan_feed(self.config,state,None,0,0,1,out,16,ev,8,C.byref(r))==0
        assert r.done and not r.events and not r.styled and bytes(state)==copy
        return bytes(styles),all_events,batches,state,{'calls':calls,'max_call_ms':max_ns/1e6}
def fixtures():
    out=[]
    for line in (ROOT/'tests/ru_lexical_policy.ru').read_text(encoding='utf-8').splitlines():
        m=re.match(r"核例 ('(?:\\.|[^'\\])*'), ('(?:\\.|[^'\\])*'),",line)
        if m:out.append((ast.literal_eval(m[1]),ast.literal_eval(m[2])))
    out += [('empty',''),('cr-raw','若 真 则\r显 1.\n然\r\n'),('long-name','算'+'a'*2001+'\n显 1.\n'),('long-comment','解.'+'😀abc\r\n'*300+'释.\n'),('shared-if-ref','若 真 则 算 回 值:\n1.\n然\n'),('shared-if-lambda','若 真 则 回 取 算 值:\n得 值.\n法.\n然\n'),('shared-comment-ref','算 回 值: 解.\ncomment\n释. 1.\n'),('shared-open-ref','若 真 则 算 回 值:\n1')]
    return out
def run(cmd,log,env=None):
    p=subprocess.run(list(map(str,cmd)),cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',env=env)
    (BUILD/log).write_text(p.stdout,encoding='utf-8')
    if p.returncode:raise RuntimeError(f'{log}: exit {p.returncode}\n{p.stdout[-5000:]}')
    return p.stdout

def check_boundaries(sc):
    d=sc.dll
    for bad in (b'\0',b'\x80',b'\xc0\x80',b'\xed\xa0\x80',b'\xf4\x90\x80\x80',b'\xe0\x80\x80',b'\xf0\x80\x80\x80',b'\xc2',b'abc\xe2\x82'):
        s=sc.state();old=bytes(s);r=Result();out=(C.c_uint8*80)();ev=(Event*64)()
        assert d.ru_scan_feed(sc.config,s,bad,len(bad),0,1,out,80,ev,64,C.byref(r))==3
        assert bytes(s)==old and bytes(r)[4:]==bytes(36),'error result/state must not partially commit'
    for text in ('','9:8:x\n9:8:x\n','256:8:x\n','1:1:'+('a'*65)+'\n','1:2:\n','1:2:'+('a'*17)+'\n','1:2:\ud800\n'):
        cfg=C.create_string_buffer(d.ru_scan_config_size());data=text.encode('utf8','surrogatepass');status=d.ru_scan_config_init(cfg,len(cfg),data,len(data))
        assert status==(0 if text=='' else 2)
    # Config owns a copy: overwriting and releasing the source cannot change it.
    cfg=C.create_string_buffer(d.ru_scan_config_size());words=C.create_string_buffer(b'9:4:x\n')
    assert d.ru_scan_config_init(cfg,len(cfg),words,6)==0
    C.memset(words,0,len(words));del words
    state=sc.state();r=Result();out=(C.c_uint8*80)();ev=(Event*64)()
    assert d.ru_scan_feed(cfg,state,b'x ',2,0,1,out,80,ev,64,C.byref(r))==0
    assert r.events==1 and (ev[0].head&0xffffff)==(1|(9<<8)|(4<<16))
    # Malformed API calls and forged internal counters cannot partially commit.
    for length,offset,eof,stylecap,eventcap in ((1,2,1,80,64),(1,0,2,80,64),(1,0,1,16,64),(1,0,1,80,7),(1,0,1,80,65),(65537,0,1,80,64)):
        state=sc.state();old=bytes(state);r=Result();out=(C.c_uint8*80)();ev=(Event*65)()
        assert d.ru_scan_feed(sc.config,state,b'a',length,offset,eof,out,stylecap,ev,eventcap,C.byref(r))==2
        assert bytes(state)==old and bytes(r)[4:]==bytes(36)
    state=sc.state();fields=(C.c_uint32*16).from_buffer(state)
    fields[1]=1;fields[3]=1;fields[11]=1;fields[12]=64
    old=bytes(state);r=Result();out=(C.c_uint8*80)();ev=(Event*64)()
    assert d.ru_scan_feed(sc.config,state,b'aaaa',4,0,1,out,80,ev,64,C.byref(r))==4
    assert bytes(state)==old and bytes(r)[4:]==bytes(36)
    state=sc.state();r=Result()
    assert d.ru_scan_feed(sc.config,state,b'\xf0',1,0,0,out,80,ev,8,C.byref(r))==0 and r.consumed==1
    old=bytes(state)
    assert d.ru_scan_feed(sc.config,state,None,0,0,0,out,80,ev,8,C.byref(r))==0 and bytes(state)==old
    assert d.ru_scan_feed(sc.config,state,None,0,0,1,out,80,ev,8,C.byref(r))==3 and bytes(state)==old
    assert d.ru_scan_feed(sc.config,state,b'\x9f\x98\x80',3,0,1,out,80,ev,8,C.byref(r))==0 and r.done and r.styled==4
    a=sc.scan(b'a=1.\n',1)[3];b=sc.scan(b'b=1.\n',2)[3]
    assert d.ru_scan_state_equal(a,b)==1,'dead prefix must not block convergence'
    target=sc.state();assert d.ru_scan_state_copy(target,a,len(target))==0 and d.ru_scan_state_equal(target,a)==1
    target[16]=b'\1';assert d.ru_scan_state_equal(target,a)==0
    # All BMP/non-BMP range data is identical to the pure Ru payload.
    source=(ROOT/'src/ru_lexical.ru').read_text(encoding='utf-8');header=(ROOT/'native/ru_unicode_data.h').read_text(encoding='utf-8')
    for ru,c in (('_字母区','ru_alpha_ranges'),('_字数区','ru_alnum_ranges')):
        payload=re.search(r"^"+ru+r" 取 _制区 '([^']*)'\.$",source,re.M)[1]
        pairs=[tuple(map(ord,payload[i:i+2])) for i in range(0,len(payload),2)]
        part=header.split(c,1)[1].split('};',1)[0]
        actual=[(int(a,16),int(b,16)) for a,b in re.findall(r'\{0x([0-9a-fA-F]+)u?,\s*0x([0-9a-fA-F]+)u?\}',part)]
        assert actual==pairs,(c,len(actual),len(pairs))

def differential(sc,cases,ru_root):
    base=(ROOT/'tests/ru_lexical_policy.ru').read_text(encoding='utf-8').split('作 核例',1)[0].replace("'../src/ru_lexical.ru'",q(str(ROOT/'src/ru_lexical.ru')))
    code=base+'''
# Explicit transport-only empty-batch equivalence, including EOF/idempotence.
空甲 取 模 其 新状态.
空乙 取 模 其 新状态.
模 其 批处理 空甲, [], 7, 0, 假.
果甲 取 模 其 批处理 空甲, [], 7, 0, 真.
果乙 取 模 其 批处理 空乙, [], 7, 0, 真.
若 非 (模 其 等价 空甲 空乙) 则 卒 'empty policy batch changed final context'. 然
若 果甲['folds'] 其 量 != 1 或 果乙['folds'] 其 量 != 1 则 卒 'empty policy EOF lost line'. 然
若 果甲['folds'][0][0] != 果乙['folds'][0][0] 或 果甲['folds'][0][1] != 果乙['folds'][0][1] 或 果甲['folds'][0][2] != 果乙['folds'][0][2] 则 卒 'empty policy EOF changed folds'. 然
重空 取 模 其 批处理 空甲, [], 7, 0, 真.
若 重空['folds'] 其 量 != 0 或 重空['spans'] 其 量 != 0 则 卒 'policy EOF is not idempotent'. 然
作 本例 名 文 期色 批们:
    纯 取 运行 文 127.
    态 取 模 其 新状态.
    折 取 {}.
    位 取 0.
    循 批们 其 量 次
        批 取 批们[位].
        果 取 模 其 批处理 态 批[0] 批[1] 批[2] 批[3].
        子 取 0.
        循 果['folds'] 其 量 次
            项 取 果['folds'][子].
            折 其 增 项[0] ([项[1],项[2]]).
            子 取 子+1.
        环
        子 取 0.
        循 果['spans'] 其 量 次
            项 取 果['spans'][子].
            若 项[1] > 64 则 卒 'unbounded keyword correction'. 然
            字节 取 项[0].
            循 项[1] 次
                若 (期色[字节] 为 数) != 项[2] 则 卒 ('native fix mismatch '+名). 然
                字节 取 字节+1.
            环
            子 取 子+1.
        环
        位 取 位+1.
    环
    同 取 真.
    位 取 0.
    循 期色 其 量 次
        若 纯['styles'][位] != (期色[位] 为 数) 则 同 取 假. 然
        位 取 位+1.
    环
    确认 同 (名+' C/pure UTF8 styles').
    确认 (折叠同 纯['folds'] 折) (名+' shared Ru folds').
为
'''
    for i,(name,text) in enumerate(cases):
        styles,events,batches,state,metrics=sc.scan(text.encode(),[1,3,7,31,1024][i%5],[8,16,64][i%3])
        # Keep optimizer units bounded; a giant module initializer causes
        # pathological native compiler work unrelated to scanner throughput.
        batches=[b for b in batches if b[0] or b[3]]
        code+='作 案'+str(i)+':\n    本例 '+q(name)+', '+q(text)+', '+q(''.join(map(str,styles)))+', '+literal(batches)+'.\n为\n'
    for i in range(len(cases)):code+='案'+str(i)+'.\n'
    code+="显 'TOTAL PASS: '+(次数[0] 为 句).\n"
    path=BUILD/'differential.ru';path.write_text(code,encoding='utf-8')
    ru=ru_root/'ru'
    out=run([sys.executable,ru,'run',path],'differential-python.log');assert f'TOTAL PASS: {len(cases)*2}' in out
    run([sys.executable,ru,'build','--cc','gcc',path,'-o',BUILD/'differential'],'differential-build.log')
    out=run([BUILD/'differential'],'differential-c.log');assert f'TOTAL PASS: {len(cases)*2}' in out
    return len(cases)*2


def sanitize():
    code=r"""
#include "ru_scan.h"
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
static unsigned seed=0x213;
static unsigned next(void){seed=seed*1664525u+1013904223u;return seed;}
int main(void){
 size_t cs=ru_scan_config_size(),ss=ru_scan_state_size();
 unsigned char *cfg=malloc(cs+32),*state=malloc(ss+32),*old=malloc(ss);
 const char config[]="1:4:算\n100:7:.\n101:7::\n";
 memset(cfg,0xa5,cs+32);assert(!ru_scan_config_init(cfg+16,cs,config,sizeof(config)-1));
 for(unsigned trial=0;trial<20000;trial++){
  unsigned char input[512],styles[544],before[544];RuScanEvent events[66];RuScanResult r;
  unsigned n=next()%512,offset=0,iterations=0,cap=8+next()%57;
  memset(state,0xa5,ss+32);assert(!ru_scan_state_init(state+16,ss));
  for(unsigned j=0;j<n;j++)input[j]=trial%2?(unsigned char)(32+next()%95):(unsigned char)next();
  do{
   unsigned window=1+next()%31;if(window>n-offset)window=n-offset;
   unsigned used=0,status;
   do{
    memset(styles,0xa5,sizeof(styles));memcpy(before,styles,sizeof(styles));memset(events,0xa5,sizeof(events));memcpy(old,state+16,ss);
    status=ru_scan_feed(cfg+16,state+16,input+offset,window,used,offset+window==n,styles+16,sizeof(styles)-32,events+1,cap,&r);
    assert(status==r.status);
    if(status>1){assert(!memcmp(old,state+16,ss));assert(r.consumed==0&&r.events==0&&r.styled==0&&r.start==0&&r.bytes==0);break;}
    assert(r.consumed<=window-used&&r.events<=cap&&r.styled<=window+16&&r.bytes==r.start+r.styled);
    if(status==1)assert(r.consumed||r.styled||r.events);
    used+=r.consumed;
    assert(!memcmp(styles,before,16)&&!memcmp(styles+sizeof(styles)-16,before+sizeof(styles)-16,16));
    for(unsigned j=0;j<16;j++){assert(((unsigned char*)events)[j]==0xa5);assert(((unsigned char*)(events+1+cap))[j]==0xa5);}
    assert(++iterations<10000);
   }while(status==1);
   if(status>1)break;
   offset+=used;
   if(r.done)break;
  }while(offset<n);
  for(unsigned j=0;j<16;j++){assert(state[j]==0xa5&&state[ss+16+j]==0xa5&&cfg[j]==0xa5&&cfg[cs+16+j]==0xa5);}
 }
 for(unsigned field=1;field<15;field++){
  uint8_t input[4]={'a','a','a','a'},styles[32];RuScanEvent events[8];RuScanResult r;
  uint32_t invalid[15]={0,32000001u,1,6,0,2,2,2,3,1,1,1,65,17,2};
  if(field==4)continue;
  assert(!ru_scan_state_init(state+16,ss));((uint32_t*)(state+16))[field]=invalid[field];memcpy(old,state+16,ss);
  assert(ru_scan_feed(cfg+16,state+16,input,4,0,1,styles,32,events,8,&r)==RU_SCAN_BAD_STATE);
  assert(!memcmp(old,state+16,ss)&&r.status==RU_SCAN_BAD_STATE&&!r.events&&!r.consumed&&!r.styled&&!r.start&&!r.bytes);
 }
 free(old);free(state);free(cfg);puts("PASS: 20000 ASan/UBSan bounded random buffer cases");return 0;
}
"""
    path=BUILD/'sanitize.c';path.write_text(code,encoding='utf-8')
    exe=BUILD/'sanitize'
    run(['gcc','-std=c99','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I',ROOT/'native',path,ROOT/'native/ru_scan.c','-o',exe],'sanitize-build.log')
    # Full sanitizer defaults for ordinary CI. Explicit caller options are
    # honored, and must be recorded separately when they narrow coverage.
    env=dict(os.environ)
    env.setdefault('ASAN_OPTIONS','detect_leaks=1:halt_on_error=1:abort_on_error=1')
    env.setdefault('UBSAN_OPTIONS','halt_on_error=1:print_stacktrace=1')
    result=run([exe],'sanitize.log',env=env).strip()
    if re.search(r'(?:^|:)detect_leaks=0(?:$|:)',env['ASAN_OPTIONS']):
        result+=' (LSan disabled by caller)'
    return result


def check_sanitizer_environment():
    """Capture subprocess options without compiling or executing any program."""
    from unittest.mock import patch
    captured=[]
    def capture(cmd,log,env=None):
        if env is not None:captured.append(dict(env))
        return 'PASS: 20000 ASan/UBSan bounded random buffer cases'
    with patch(__name__+'.run',capture):
        with patch.dict(os.environ,{},clear=True):
            result=sanitize()
            assert captured[-1]['ASAN_OPTIONS']=='detect_leaks=1:halt_on_error=1:abort_on_error=1'
            assert captured[-1]['UBSAN_OPTIONS']=='halt_on_error=1:print_stacktrace=1'
            assert 'disabled' not in result
        with patch.dict(os.environ,{'ASAN_OPTIONS':'detect_leaks=1:abort_on_error=1','UBSAN_OPTIONS':'halt_on_error=1'},clear=True):
            sanitize()
            assert captured[-1]['ASAN_OPTIONS']=='detect_leaks=1:abort_on_error=1'
            assert captured[-1]['UBSAN_OPTIONS']=='halt_on_error=1'
        with patch.dict(os.environ,{'ASAN_OPTIONS':'detect_leaks=0:abort_on_error=1'},clear=True):
            assert sanitize().endswith('(LSan disabled by caller)')
            assert captured[-1]['ASAN_OPTIONS']=='detect_leaks=0:abort_on_error=1'

def benchmark(ru_root):
    ru=ru_root/'ru'
    source=BUILD/'combined.ru';source.write_text("模 取 外言 '"+str(ROOT/'src/ru_lexical.ru')+"'.\n显 模 其 新状态.\n",encoding='utf-8')
    run([sys.executable,ru,'build','--cc','gcc',source,'--emit-c',BUILD/'combined-generated.c','-o',BUILD/'combined-unused'],'benchmark-build.log')
    s=(BUILD/'combined-generated.c').read_text(encoding='utf-8');s=s[:s.index('int main(int argc, char **argv)')]
    head='#define _POSIX_C_SOURCE 200809L\n#include <time.h>\n#include "ru_scan.h"\nstatic double bench_now(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec/1e9;}\nstatic double bench_cpu(void){struct timespec t;clock_gettime(CLOCK_PROCESS_CPUTIME_ID,&t);return t.tv_sec+t.tv_nsec/1e9;}\n'
    main=r'''
    int main(int argc,char **argv){
     const char *pattern=argc>2&&strcmp(argv[2],"realistic")==0?"# Unicode 中😀 source example\n作 演示:\n    数值 取 42.\n    文字 取 '若 真 则'.\n    若 真 则\n        显 文字.\n    然\n为\n":argc>2&&strcmp(argv[2],"ru")==0?"x 取 1.\n":argc>2&&strcmp(argv[2],"line")==0?"a=1. ":"a=1.\n";
     size_t target=argc>1?strtoul(argv[1],NULL,10):100000,plen=strlen(pattern),size=target/plen*plen,at=0;
     uint8_t *text=malloc(size),styles[1040];RuScanEvent events[64];RuScanResult result;
     void *cfg=malloc(ru_scan_config_size()),*ctx=malloc(ru_scan_state_size());
     uint64_t calls=0,evcount=0;double begin=bench_now(),cpu_begin=bench_cpu(),maximum=0,max_cpu=0,scan_time=0,policy_time=0;
     const char *config=CONFIGURATION;
     for(size_t n=0;n<size;n++)text[n]=(uint8_t)pattern[n%plen];
     ru_source="combined C scanner / actual Ru policy benchmark";ru_init();
     Val mod=ru_module_1_init(),constructor=env_get(mod.module,"新状态",1),consumer=env_get(mod.module,"批处理",1);
     Val state=v_call(constructor,0,NULL,NULL,1);
     if(ru_scan_config_init(cfg,ru_scan_config_size(),config,(uint32_t)strlen(config))||ru_scan_state_init(ctx,ru_scan_state_size()))return 2;
     while(at<size){
       uint32_t length=(uint32_t)(size-at>1024?1024:size-at),offset=0;
       do{
         double tick=bench_now(),cpu_tick=bench_cpu(),scan_start=tick;
         uint32_t status=ru_scan_feed(cfg,ctx,text+at,length,offset,at+length==size,styles,sizeof(styles),events,64,&result);
         scan_time+=bench_now()-scan_start;
         if(status>1)return 3;
         Val rows[64];
         double policy_start=bench_now();
         for(uint32_t n=0;n<result.events;n++){
           uint64_t h=events[n].head,t=events[n].tail;
           Val fields[6]={v_num(h&255),v_num((h>>8)&255),v_num((h>>16)&255),v_num((h>>24)&0xffffffffu),v_num(t&0xffffffffu),v_num(t>>32)};
           rows[n]=v_array(6,fields,1);
         }
         Val list=v_array(result.events,rows,1);for(uint32_t n=0;n<result.events;n++)v_drop(rows[n]);
         Val args[5]={state,list,v_num((double)result.bytes),v_num(result.line),v_fact(result.done)};
         const char *keys[5]={NULL,NULL,NULL,NULL,NULL};
         Val output=v_call(consumer,5,keys,args,1);if(ru_panicking)return ru_panic_uncaught();
         v_drop(output);v_drop(list);policy_time+=bench_now()-policy_start;
         offset+=result.consumed;calls++;evcount+=result.events;
         double elapsed=bench_now()-tick,cpu_elapsed=bench_cpu()-cpu_tick;if(elapsed>maximum)maximum=elapsed;if(cpu_elapsed>max_cpu)max_cpu=cpu_elapsed;
         if(status==0)break;
       }while(offset<=length);
       at+=offset;
     }
     printf("bytes=%zu calls=%llu events=%llu total_ms=%.3f scanner_ms=%.3f decode_policy_ms=%.3f max_batch_ms=%.3f cpu_total_ms=%.3f max_cpu_batch_ms=%.3f\n",size,(unsigned long long)calls,(unsigned long long)evcount,(bench_now()-begin)*1000,scan_time*1000,policy_time*1000,maximum*1000,(bench_cpu()-cpu_begin)*1000,max_cpu*1000);
     v_drop(state);v_drop(constructor);v_drop(consumer);v_drop(mod);ru_shutdown();free(text);free(ctx);free(cfg);return 0;
    }
    '''.replace('CONFIGURATION',json.dumps(configuration().decode(),ensure_ascii=False))
    (BUILD/'combined.c').write_text(head+s+main,encoding='utf-8')
    run(['gcc','-std=c99','-O2','-I',ROOT/'native',BUILD/'combined.c',ROOT/'native/ru_scan.c','-lm','-o',BUILD/'combined'],'benchmark-harness-build.log')
    results=[]
    for size in (10000,100000,1000000):
        for shape in ('ascii','line','ru','realistic'):
            start=time.perf_counter()
            output=run([BUILD/'combined',size,shape],f'benchmark-{shape}-{size}.log').strip()
            results.append({'shape':shape,'target_bytes':size,'wall_seconds':time.perf_counter()-start,'metrics':output})
    report={'measurement':'Linux C scan + actual Ru event construction/structural policy; includes initialization. Excludes Windows FFI/field reads and Scintilla publishing.', 'source_sha256':hashlib.sha256((ROOT/'src/ru_lexical.ru').read_bytes()).hexdigest(),'generated_c_sha256':hashlib.sha256((BUILD/'combined.c').read_bytes()).hexdigest(),'results':results}
    (BUILD/'benchmark.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--library',type=pathlib.Path);ap.add_argument('--ru-root',type=pathlib.Path);ap.add_argument('--fuzz',type=int,default=100);ap.add_argument('--benchmark',action='store_true');ap.add_argument('--sanitize',action='store_true');args=ap.parse_args()
    BUILD.mkdir(parents=True,exist_ok=True)
    # A failed attempt must never leave an old success report in place.
    (BUILD/'report.json').unlink(missing_ok=True)
    lib=args.library
    if not lib:
        lib=BUILD/'libRuSyntax.so';run(['gcc','-std=c99','-O2','-Wall','-Wextra','-Werror','-fPIC','-shared',ROOT/'native/ru_scan.c','-o',lib],'scanner-build.log')
    sc=Scanner(lib.resolve());check_boundaries(sc);check_sanitizer_environment();cases=fixtures();rng=random.Random(0x213)
    atoms=['算','作','为','若','然','真','取','得','典','成','段','落','终','解.','释。','批.','#','//',"'",'“','”','\\','1e-2','0x12','(',')','[',']','{','}',':',',','.','_x','é٢','𐐀','😀','\n','\r','\t',' ']
    for i in range(args.fuzz):cases.append((f'fuzz-{i}',''.join(rng.choice(atoms) for _ in range(rng.randrange(1,45)))))
    total=0
    for name,text in cases:
        data=text.encode();baseline=sc.scan(data,max(1,len(data)) if len(data)<=65536 else 1024)
        for size,cap in ((1,8),(2,16),(3,64),(7,8),(31,64),(1024,64)):
            actual=sc.scan(data,size,cap)
            assert actual[:2]==baseline[:2],(name,size,cap)
            total+=1
    checks=differential(sc,cases,args.ru_root.resolve()) if args.ru_root else 0
    sanitizer=sanitize() if args.sanitize else None
    if args.benchmark:
        if not args.ru_root:raise SystemExit('--benchmark requires --ru-root')
        benchmark(args.ru_root.resolve())
    report={'sanitizer':sanitizer,'cases':len(cases),'chunk_checks':total,'ru_assertions_per_backend':checks,'library_sha256':hashlib.sha256(lib.read_bytes()).hexdigest(),'source_sha256':hashlib.sha256((ROOT/'native/ru_scan.c').read_bytes()).hexdigest()}
    (BUILD/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))
if __name__=='__main__':main()
