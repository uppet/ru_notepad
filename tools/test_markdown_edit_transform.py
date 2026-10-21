#!/usr/bin/env python3
"""Edit-only transform negative controls and optional real generated-TU audit."""
import argparse, copy, json, unittest
from pathlib import Path
import profile_markdown_edits as p
from test_markdown_phases import TransformControls

class EditTransformControls(TransformControls):
    def setUp(self):
        super().setUp()
        self.code += '''
typedef struct RuNativeTrap { int unchanged; } RuNativeTrap;
static void ru_fail(int line, const char *format, ...)
{
}
static void ru_panic_raise(Val reason, int line, int col)
{
}
static void rn_trap_restore(RuNativeTrap *trap)
{
}
static RuHeap *ru_new_heap(size_t size, int kind, int line)
{
}
static Val env_get(Env *env,const char *name,int line)
{
}
static Val v_index(Val v,Val index,int line)
{
}
static Val v_call(Val callable,size_t argc,const char **keys,Val *args,int line)
{
}
static Val rn_invoke(RuNative *function, Val parameters, int line)
{
    rn_platform_set_error(0);
    raw = ru_native_generated_call(sig->as.signature.id, function->as.function.address, args);
    error = rn_platform_error();
}
    /* This local root is included in the snapshot and survives logical close. */
    trap = rn_trap_new();
    if (!trap) {
    }
    v_drop(rn_value(callback));
    rn_platform_set_error(entry_error); return answer;
int main(int argc, char **argv) {
}
'''
        self.receipt['generated_c_sha256']=p.base.digest(self.code.encode())
        self.header=(Path(__file__).resolve().parents[1]/'native/markdown_edit_profile.h').read_text()
    def output(self,mapping=None):
        return p.transform(self.code,self.root,self.receipt,mapping or self.mapping(),self.header)
    def test_edit_transform_and_audit(self):
        output=self.output();result=p.audit(self.code,self.root,self.receipt,self.mapping(),output)
        self.assertEqual(result['selected_original_bodies_preserved'],6)
        self.assertIn('mpp_track_revision(',output)
        self.assertNotIn('mpp_identity_bound',output)
        self.assertEqual(output.count(p.OBSERVERS),1)
        self.assertNotIn('RU_MARKDOWN_PHASE_PROFILE ',output)
    def test_edit_stale_map(self):
        mapping=self.mapping();mapping['entries'][0]['body_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'Stale'):self.output(mapping)
    def test_old_header_rejected(self):
        with self.assertRaisesRegex(ValueError,'header'):p.transform(self.code,self.root,self.receipt,self.mapping(),'')
    def test_body_mutation_audit(self):
        output=self.output().replace('return v_null();','return changed();',1)
        with self.assertRaisesRegex(ValueError,'body'):p.audit(self.code,self.root,self.receipt,self.mapping(),output)
    def test_adjacency_mutation_audit(self):
        output=self.output().replace('    error = rn_platform_error();','    changed(); error = rn_platform_error();')
        with self.assertRaisesRegex(ValueError,'adjacency'):p.audit(self.code,self.root,self.receipt,self.mapping(),output)
    def test_trap_mutation_audit(self):
        output=self.output().replace('int unchanged;','int changed;')
        with self.assertRaisesRegex(ValueError,'layout'):p.audit(self.code,self.root,self.receipt,self.mapping(),output)
    def test_observer_mutation_audit(self):
        output=self.output().replace('feed.n>1000001','feed.n>1000002')
        with self.assertRaisesRegex(ValueError,'observer'):p.audit(self.code,self.root,self.receipt,self.mapping(),output)

def audit_actual(source,input_c,receipt,header):
    code=Path(input_c).read_text();r=json.loads(Path(receipt).read_text());m=p.make_map(code,source,r)
    output=p.transform(code,source,r,m,Path(header).read_text())
    return p.audit(code,source,r,m,output)


def observer_actual(input_c,cc='gcc'):
    """Compile real generated runtime layouts with the actual edit observer/header."""
    import os, subprocess, tempfile
    root=Path(__file__).resolve().parents[1]
    backend=(root/'tests/markdown_edit_profile_host.c').read_text().split('#include "../native/markdown_edit_profile.h"',1)[0]
    runtime=Path(input_c).read_text().split('/* RU_NATIVE_PLATFORM_BEGIN */',1)[0]+'\n#endif\n'
    harness=r"""
#include <assert.h>
static Val str(const char *s) { Val v={0};size_t n=strlen(s);v.kind=RU_STR;v.s=calloc(1,sizeof(RuString)+n+1);v.s->len=n;memcpy(v.s->data,s,n);return v; }
static Val num(double n) { Val v={0};v.kind=RU_NUM;v.n=n;return v; }
static Val fact(int n) { Val v=num(n);v.kind=RU_FACT;return v; }
static void put(RuMap *m,const char *k,Val v) {
    size_t i;for(i=0;i<m->len;i++) if(!strcmp(m->entries[i].key.s->data,k)) {
        if(m->entries[i].value.kind==RU_STR)free(m->entries[i].value.s);
        m->entries[i].value=v;return;
    }
    m->entries[i].key=str(k);m->entries[i].value=v;m->entries[i].state=1;m->len++;
}
int main(void) {
    RuMap m={0};RuMapEntry entries[64]={0};RuArray ranges={0};Val state={0},ra={0};
    m.entries=entries;m.capacity=64;state.kind=RU_MAP;state.heap=(RuHeap*)&m;ra.kind=RU_ARRAY;ra.heap=(RuHeap*)&ranges;
    put(&m,"generation",num(1));put(&m,"ranges",ra);put(&m,"rangeIndex",num(0));put(&m,"rangeOffset",num(0));
    put(&m,"language",str("markdown"));put(&m,"warning",str(""));put(&m,"chunk",str(""));
    put(&m,"alive",fact(1));put(&m,"foldEnabled",fact(1));put(&m,"restart",num(0));
    assert(mpp_init());
    for(unsigned i=0;i<5;i++) {
        double len=(i==1||i==3)?1000001:1000000;mpp_token r=mpp_begin(MPP_TIMER_ROOT),t;
        put(&m,"identity",num(i+1));put(&m,"revision",num(i));put(&m,"feed",num(0));put(&m,"length",num(-1));
        put(&m,"phase",str("prepare"));put(&m,"pending",fact(1));put(&m,"eof",fact(0));
        mpp_note_step();mpp_observe_step(state,0);assert(mpp.failure==0);
        t=mpp_begin(MPP_PURE_FEED);mpp_count(MPP_HOT_V_INDEX);mpp_leave(t);
        t=mpp_begin(MPP_BRIDGE_PUBLISH);mpp_leave(t);
        t=mpp_begin(MPP_NATIVE_BULK);mpp_note_raw_native_entry(1);mpp_leave(t);
        put(&m,"length",num(len));put(&m,"feed",num(len));put(&m,"pending",fact(0));put(&m,"eof",fact(1));put(&m,"phase",str("scan"));
        mpp_observe_step(state,1);mpp_leave(r);assert(mpp.failure==0&&mpp.snapshot_count==i+1);
    }
    assert(mpp.scan_bytes==5000002);
    /* Completed tuple reopening is not a new revision and must poison all rows. */
    mpp_token r=mpp_begin(MPP_TIMER_ROOT);put(&m,"pending",fact(1));mpp_observe_step(state,1);
    assert(mpp.failure==MPP_FAIL_PROGRESS);mpp_leave(r);assert(mpp.depth==1);assert(!mpp_finalize(stdout));
    for(size_t i=0;i<m.len;i++){free(entries[i].key.s);if(entries[i].value.kind==RU_STR)free(entries[i].value.s);}
    puts("MARKDOWN_EDIT_ACTUAL_OBSERVER_PASS=1");return 0;
}
"""
    with tempfile.TemporaryDirectory(prefix='markdown-edit-observer-') as tmp:
        source=Path(tmp)/'observer.c';exe=Path(tmp)/('observer.exe' if os.name=='nt' else 'observer')
        source.write_text(backend+(root/'native/markdown_edit_profile.h').read_text()+runtime+p.OBSERVERS+harness)
        subprocess.run([cc,'-std=c11','-O2','-Wall','-Wextra','-Wno-unused-function','-Wno-unused-variable','-Werror',str(source),'-lm','-pthread','-o',str(exe)],check=True,timeout=60)
        subprocess.run([str(exe)],check=True,timeout=10)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path);ap.add_argument('--input-c',type=Path)
    ap.add_argument('--receipt',type=Path);ap.add_argument('--header',type=Path);ap.add_argument('--output',type=Path)
    a=ap.parse_args();result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(EditTransformControls))
    if not result.wasSuccessful():raise SystemExit(1)
    if a.input_c:
        result=audit_actual(a.source_root,a.input_c,a.receipt,a.header)
        if a.output:a.output.write_text(json.dumps(result,indent=2)+'\n')
        observer_actual(a.input_c)
        print('ACTUAL_EDIT_GENERATED_TRANSFORM_CONTROLS_PASS=1')
