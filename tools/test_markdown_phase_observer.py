#!/usr/bin/env python3
"""Compile and execute the actual generated-TU observer against runtime layouts."""
import argparse, os, subprocess, tempfile
from pathlib import Path
from profile_markdown_phases import OBSERVERS

def run(input_c,cc='gcc'):
    code=Path(input_c).read_text().split('/* RU_NATIVE_PLATFORM_BEGIN */',1)[0]+'\n#endif\n'
    stub=r'''
static int invalid, completion;
static uint64_t final_feed,final_length;
#define MPP_FAIL_PROGRESS 17
static int mpp_is_active(void) { return !invalid; }
static void mpp_invalidate(int why) { invalid=why; }
static void mpp_request_completion(void) { completion=1; }
static void mpp_set_progress(uint64_t a,uint64_t b,uint64_t c,uint64_t feed,uint64_t length,uint64_t d,uint64_t e,uint64_t f,int g,int h) {
(void)a;(void)b;(void)c;(void)d;(void)e;(void)f;(void)g;(void)h; final_feed=feed;final_length=length;
}
'''
    harness=r'''
#include <assert.h>
static Val str(const char *text) {
    Val v={0};size_t n=strlen(text);v.kind=RU_STR;v.s=calloc(1,sizeof(RuString)+n+1);v.s->len=n;memcpy(v.s->data,text,n);return v;
}
static Val num(double n) { Val v={0};v.kind=RU_NUM;v.n=n;return v; }
static Val fact(int n) { Val v=num(n);v.kind=RU_FACT;return v; }
static void put(RuMap *map,const char *key,Val value) {
    size_t i;
    for(i=0;i<map->len;i++) if(!strcmp(map->entries[i].key.s->data,key)) {
        if(map->entries[i].value.kind==RU_STR)free(map->entries[i].value.s);
        map->entries[i].value=value;return;
    }
    map->entries[i].key=str(key);map->entries[i].value=value;map->entries[i].state=1;map->len++;
}
static void reset(void) { invalid=completion=0; mpp_identity_bound=0;final_feed=final_length=0; }
int main(void) {
    RuMap map={0}; RuMapEntry entries[64]={0};RuArray ranges={0};Val state={0},ra={0};
    state.kind=RU_MAP;state.heap=(RuHeap*)&map;ra.kind=RU_ARRAY;ra.heap=(RuHeap*)&ranges;
    map.entries=entries;map.capacity=64;
    put(&map,"identity",num(11));put(&map,"generation",num(12));put(&map,"revision",num(13));
    put(&map,"length",num(-1));put(&map,"feed",num(0));put(&map,"pending",fact(1));put(&map,"eof",fact(0));
    put(&map,"ranges",ra);put(&map,"rangeIndex",num(0));put(&map,"rangeOffset",num(0));put(&map,"phase",str("prepare"));
    put(&map,"language",str("markdown"));put(&map,"warning",str(""));put(&map,"chunk",str(""));
    put(&map,"alive",fact(1));put(&map,"foldEnabled",fact(1));put(&map,"restart",num(0));
    reset();mpp_observe_step(state,0);assert(!invalid && mpp_identity_bound);
    put(&map,"length",num(1000000));put(&map,"phase",str("scan"));mpp_observe_step(state,1);assert(!invalid&&!completion);
    put(&map,"feed",num(1000000));put(&map,"eof",fact(1));put(&map,"pending",fact(0));mpp_observe_step(state,1);
    assert(!invalid&&completion&&final_feed==1000000&&final_length==1000000);
    reset();put(&map,"warning",str("unexpected"));mpp_observe_step(state,1);assert(invalid&&!completion);put(&map,"warning",str(""));
    reset();mpp_observe_step(state,0);put(&map,"revision",num(14));mpp_observe_step(state,1);assert(invalid&&!completion);put(&map,"revision",num(13));
    reset();put(&map,"feed",num(999999));mpp_observe_step(state,1);assert(invalid&&!completion);put(&map,"feed",num(1000000));
    reset();put(&map,"rangeOffset",num(1));mpp_observe_step(state,1);assert(invalid&&!completion);put(&map,"rangeOffset",num(0));
    reset();put(&map,"chunk",str("pending"));mpp_observe_step(state,1);assert(invalid&&!completion);put(&map,"chunk",str(""));
    reset();put(&map,"restart",num(1));mpp_observe_step(state,1);assert(invalid&&!completion);put(&map,"restart",num(0));
    reset();map.capacity=257;mpp_observe_step(state,1);assert(invalid&&!completion);map.capacity=64;
    reset();put(&map,"language",str("plain"));mpp_observe_step(state,1);assert(invalid&&!completion);put(&map,"language",str("markdown"));
    reset();put(&map,"identity",num(NAN));mpp_observe_step(state,1);assert(invalid&&!completion);
    RuNative f={0},sig={0},types[11]={0};Val binding={0};int expected[10]={RN_PTR,RN_PTR,RN_PTR,RN_PTR,RN_PTR,RN_INTPTR,RN_PTR,RN_U32,RN_PTR,RN_U32};
    f.tag=RN_FUNCTION;f.as.function.address=(void*)(uintptr_t)1234;f.as.function.signature=&sig;sig.tag=RN_SIGNATURE;sig.as.signature.count=10;sig.as.signature.result=&types[10];types[10].as.type.code=RN_U32;
    for(int i=0;i<10;i++){types[i].as.type.code=expected[i];sig.as.signature.params[i]=&types[i];}
    binding.kind=RU_NATIVE;binding.heap=(RuHeap*)&f;mpp_register_bulk(binding);assert(mpp_bulk_binding_ok&&mpp_bulk_address==f.as.function.address);
    mpp_bulk_binding_ok=0;types[5].as.type.code=RN_I32;mpp_register_bulk(binding);assert(!mpp_bulk_binding_ok);
    for(size_t i=0;i<map.len;i++){free(entries[i].key.s);if(entries[i].value.kind==RU_STR)free(entries[i].value.s);}
    puts("MARKDOWN_PHASE_OBSERVER_CONTROLS_PASS=12");return 0;
}
'''
    with tempfile.TemporaryDirectory(prefix='markdown-phase-observer-') as tmp:
        source=Path(tmp)/'observer.c';exe=Path(tmp)/('observer.exe' if os.name=='nt' else 'observer');source.write_text(code+stub+OBSERVERS+harness)
        subprocess.run([cc,'-std=c99','-O2','-Wall','-Wextra','-Wno-unused-function','-Wno-unused-variable','-Werror',str(source),'-lm','-o',str(exe)],check=True,timeout=30)
        subprocess.run([str(exe)],check=True,timeout=10)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--input-c',type=Path,required=True);ap.add_argument('--cc',default='gcc');a=ap.parse_args();run(a.input_c,a.cc)
