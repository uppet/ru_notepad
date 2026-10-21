#!/usr/bin/env python3
"""Local diagnostic only: bounded cumulative real Markdown revision observations.
Reuses exact-source mapping and wrappers; does not change compiler or Ru bodies.
"""
from __future__ import annotations
import argparse, json, re
from pathlib import Path
import profile_markdown_phases as base
make_map = base.make_map
OBSERVERS = r"""
/* Observation only: borrowed values are inspected synchronously, never retained. */
static void *mpp_bulk_address;
static int mpp_bulk_binding_ok;
static Val mpp_field_direct(Val value, const char *key) {
    Val absent = {0}; size_t i, n = strlen(key); absent.kind = RU_NULL;
    if (value.kind != RU_MAP || !value.heap) { mpp_invalidate(MPP_FAIL_PROGRESS); return absent; }
    RuMap *map = (RuMap *)value.heap;
    if (map->capacity > 256 || map->len > 64) { mpp_invalidate(MPP_FAIL_PROGRESS); return absent; }
    for (i=0;i<map->capacity;i++) {
        RuMapEntry *entry=map->entries+i;
        if (entry->state==1 && entry->key.kind==RU_STR && entry->key.s && entry->key.s->len==n && !memcmp(entry->key.s->data,key,n)) return entry->value;
    }
    mpp_invalidate(MPP_FAIL_PROGRESS); return absent;
}
static int mpp_text_is(Val v, const char *s) {
    size_t n=strlen(s); return v.kind==RU_STR && v.s && v.s->len==n && !memcmp(v.s->data,s,n);
}
static int mpp_number(Val v) { return v.kind==RU_NUM && isfinite(v.n) && v.n>=0 && v.n<=9007199254740991.0 && floor(v.n)==v.n; }
static void mpp_observe_step(Val state, int after) {
    if (!mpp_is_active()) return;
    Val identity=mpp_field_direct(state,"identity"), generation=mpp_field_direct(state,"generation"), revision=mpp_field_direct(state,"revision");
    Val length=mpp_field_direct(state,"length"), feed=mpp_field_direct(state,"feed"), pending=mpp_field_direct(state,"pending"), eof=mpp_field_direct(state,"eof");
    Val ranges=mpp_field_direct(state,"ranges"), index=mpp_field_direct(state,"rangeIndex"), offset=mpp_field_direct(state,"rangeOffset");
    Val phase=mpp_field_direct(state,"phase");
    if (!mpp_number(identity)||!mpp_number(generation)||!mpp_number(revision)||!mpp_number(feed)||!mpp_number(index)||!mpp_number(offset)||
        length.kind!=RU_NUM || (length.n!=1000000 && length.n!=1000001 && !(!after && length.n==-1)) ||
        pending.kind!=RU_FACT || eof.kind!=RU_FACT || ranges.kind!=RU_ARRAY || !ranges.heap || ((RuArray*)ranges.heap)->len>64 ||
        !mpp_text_is(mpp_field_direct(state,"language"),"markdown") || !mpp_text_is(mpp_field_direct(state,"warning"),"") ||
        !(mpp_text_is(phase,"prepare")||mpp_text_is(phase,"scan")) || feed.n>1000001 ||
        (!mpp_text_is(mpp_field_direct(state,"chunk"),"") && !pending.n)) { mpp_invalidate(MPP_FAIL_PROGRESS); return; }
    Val alive=mpp_field_direct(state,"alive"), enabled=mpp_field_direct(state,"foldEnabled"), restart=mpp_field_direct(state,"restart");
    if (alive.kind!=RU_FACT || !alive.n || enabled.kind!=RU_FACT || !enabled.n || restart.kind!=RU_NUM || restart.n!=0) { mpp_invalidate(MPP_FAIL_PROGRESS); return; }
    mpp_track_revision((uint64_t)identity.n,(uint64_t)generation.n,(uint64_t)revision.n,(uint64_t)feed.n,(int64_t)length.n,after);
    if (!mpp_is_active()) return;
    if (after) mpp_set_progress((uint64_t)identity.n,(uint64_t)generation.n,(uint64_t)revision.n,(uint64_t)feed.n,(uint64_t)length.n,((RuArray*)ranges.heap)->len,(uint64_t)index.n,(uint64_t)offset.n,!!eof.n,!!pending.n);
    if (after && !pending.n) {
        if (feed.n!=length.n || !eof.n || ((RuArray*)ranges.heap)->len || index.n || offset.n || !mpp_text_is(phase,"scan")) mpp_invalidate(MPP_FAIL_PROGRESS);
        else mpp_request_completion();
    }
}
static void mpp_register_bulk(Val value) {
    static const int expected[10]={RN_PTR,RN_PTR,RN_PTR,RN_PTR,RN_PTR,RN_INTPTR,RN_PTR,RN_U32,RN_PTR,RN_U32};
    size_t i; RuNative *function,*sig;
    if(value.kind!=RU_NATIVE || !value.heap) return;
    function=(RuNative*)value.heap;
    if(function->tag!=RN_FUNCTION || function->closed || !function->as.function.address) return;
    sig=function->as.function.signature;
    if(!sig || sig->tag!=RN_SIGNATURE || sig->as.signature.count!=10 || sig->as.signature.result->as.type.code!=RN_U32) return;
    for(i=0;i<10;i++) if(sig->as.signature.params[i]->as.type.code!=expected[i]) return;
    mpp_bulk_address=function->as.function.address; mpp_bulk_binding_ok=1;
}
"""

def transform(code, root, receipt, mapping, header):
    if 'RU_MARKDOWN_EDIT_PROFILE_H' not in header or 'RU_MARKDOWN_EDIT_PROFILE ' not in header:
        raise ValueError('Edit profile header required')
    output=base.transform(code,root,receipt,mapping,header)
    return base.once(output,base.OBSERVERS,OBSERVERS)

def audit(code, root, receipt, mapping, transformed):
    if make_map(code,root,receipt)!=mapping: raise ValueError('Stale or mutated source/body mapping')
    selected={e['id'] for e in mapping['entries']}
    for ident,name,path,start,end,body in base.generated_functions(code):
        if ident not in selected: continue
        renamed=base.once(body,f'ru_function_{ident}(Env *global',f'ru_function_{ident}_mpp_body(Env *global')
        if transformed.count(renamed)!=1: raise ValueError('Selected original body modified')
    adjacency='raw = ru_native_generated_call(sig->as.signature.id, function->as.function.address, args);\n    error = rn_platform_error();'
    if transformed.count(adjacency)!=1: raise ValueError('Native error-read adjacency changed')
    traps=re.findall(r'typedef struct RuNativeTrap \{.*?\} RuNativeTrap;',code,re.S)
    if len(traps)!=1 or transformed.count(traps[0])!=1: raise ValueError('Trap layout changed')
    if transformed.count(OBSERVERS)!=1 or base.OBSERVERS in transformed: raise ValueError('Incorrect edit observer')
    return {'schema':1,'passed':True,'selected_original_bodies_preserved':len(selected),
            'native_error_read_adjacent':True,'trap_layout_unchanged':True,
            'source_map':mapping,'instrumented_tu_sha256':base.digest(transformed.encode())}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('command',choices=['map','instrument']);ap.add_argument('--source-root',type=Path,required=True)
    ap.add_argument('--input-c',type=Path,required=True);ap.add_argument('--receipt',type=Path,required=True)
    ap.add_argument('--map',type=Path,required=True);ap.add_argument('--output-c',type=Path);ap.add_argument('--header',type=Path)
    a=ap.parse_args();code=a.input_c.read_text();receipt=json.loads(a.receipt.read_text());mapping=make_map(code,a.source_root,receipt)
    if a.command=='map':
        with a.map.open('x') as f: json.dump(mapping,f,indent=2);f.write('\n')
    else:
        if not a.output_c or not a.header: ap.error('--output-c and --header required')
        sealed=json.loads(a.map.read_text());output=transform(code,a.source_root,receipt,sealed,a.header.read_text())
        audit(code,a.source_root,receipt,sealed,output)
        with a.output_c.open('x') as f:f.write(output)
if __name__=='__main__':main()
