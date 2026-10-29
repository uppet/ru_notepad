#!/usr/bin/env python3
"""Profile-only exact-source generated-C transformation. Never a release input.
Map first, then transform against that immutable map; no compiler or Ru edits.
"""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path
from profile_ru_syntax import generated_functions, decode_c_source_path, octal

KINDS = {
 ('src/main.ru','语法时钟'): ('MPP_TIMER_ROOT', 0),
 ('src/markdown_syntax.ru','推进'): ('MPP_BRIDGE_ADVANCE', 2),
 ('src/markdown_policy.ru','喂入'): ('MPP_PURE_FEED', 3),
 ('src/markdown_syntax.ru','_发布'): ('MPP_BRIDGE_PUBLISH', 2),
 ('src/markdown_syntax.ru','_批发布'): ('MPP_BULK_PREPARE', 5),
 ('src/markdown_syntax.ru','_一步'): ('step', 2),
}
def digest(data): return hashlib.sha256(data).hexdigest()
def sha(p): return digest(Path(p).read_bytes())
def once(code, old, new):
    if code.count(old) != 1: raise ValueError(f'Expected unique anchor: {old[:100]}')
    return code.replace(old, new, 1)
def make_map(code, root, receipt):
    root=Path(root).resolve(strict=True)
    # Path text I/O normalizes platform CRLF. Accept only either complete canonical
    # LF or complete Windows-CRLF byte serialization, never an unchecked input.
    if receipt['generated_c_sha256'] not in {digest(code.encode()), digest(code.replace('\n','\r\n').encode())}: raise ValueError('Generated C receipt mismatch')
    if receipt['ru_commit'] != '85c7821fda35aa79deeaf67b4d430f24ddd7f07f': raise ValueError('Compiler identity mismatch')
    for relative, expected in receipt['source_sha256'].items():
        path=(root/relative).resolve(strict=True)
        if not path.is_relative_to(root) or sha(path)!=expected: raise ValueError('Source receipt mismatch: '+relative)
    entries=[]
    for ident,name,source,start,end,body in generated_functions(code):
        if not source: continue
        path=Path(source).resolve(strict=True)
        if not path.is_relative_to(root):
            if (path.name, decode_c_source_path(name)) in {(Path(p).name,n) for p,n in KINDS}: raise ValueError('Selected source outside approved root')
            continue
        rel=path.relative_to(root).as_posix()
        if rel not in receipt['source_sha256']: raise ValueError('Unreceipted generated source')
        key=(rel,decode_c_source_path(name))
        if key not in KINDS: continue
        phase, expected_count=KINDS[key]
        descriptor=re.findall(r'^static RuFunction ru_function_'+str(ident)+r'_descriptor = \{"[^"\n]*", (\d+), .*?\};$',code,re.M)
        if descriptor!=[str(expected_count)]: raise ValueError('Unexpected function signature: '+str(key))
        entries.append(dict(id=ident,source=rel,name=key[1],phase=phase,count=expected_count,body_sha256=digest(body.encode()),source_sha256=sha(path)))
    if len(entries)!=len(KINDS) or len({(x['source'],x['name']) for x in entries})!=len(KINDS): raise ValueError('Missing or duplicate selected function')
    binding=re.findall(r'^(\s*env_bind\(env, "_FoldApply", (ru_v_\d+), (\d+)\);)$',code,re.M)
    if len(binding)!=1: raise ValueError('Missing or duplicate bulk binding')
    lineno=int(binding[0][2]); line=(root/'src/markdown_syntax.ru').read_text().splitlines()[lineno-1]
    if "_FoldApply 取" not in line or "'ru_markdown_fold_apply_v1'" not in line: raise ValueError('Bulk source identity mismatch')
    return {'schema':1,'generated_c_sha256':digest(code.encode()),'compiler_commit':receipt['ru_commit'],'entries':entries,'binding':{'line':lineno,'value':binding[0][1],'statement':binding[0][0]}}

OBSERVERS = r"""
/* Observation only: borrowed values are inspected synchronously, never retained. */
static void *mpp_bulk_address;
static int mpp_bulk_binding_ok, mpp_identity_bound;
static double mpp_identity, mpp_generation, mpp_revision;
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
        length.kind!=RU_NUM || (length.n!=1000000 && !(!after && !mpp_identity_bound && length.n==-1)) ||
        pending.kind!=RU_FACT || eof.kind!=RU_FACT || ranges.kind!=RU_ARRAY || !ranges.heap || ((RuArray*)ranges.heap)->len>64 ||
        !mpp_text_is(mpp_field_direct(state,"language"),"markdown") || !mpp_text_is(mpp_field_direct(state,"warning"),"") ||
        !(mpp_text_is(phase,"prepare")||mpp_text_is(phase,"scan")) || feed.n>1000000 ||
        (!mpp_text_is(mpp_field_direct(state,"chunk"),"") && !pending.n)) { mpp_invalidate(MPP_FAIL_PROGRESS); return; }
    Val alive=mpp_field_direct(state,"alive"), enabled=mpp_field_direct(state,"foldEnabled"), restart=mpp_field_direct(state,"restart");
    if (alive.kind!=RU_FACT || !alive.n || enabled.kind!=RU_FACT || !enabled.n || restart.kind!=RU_NUM || restart.n!=0) { mpp_invalidate(MPP_FAIL_PROGRESS); return; }
    if (!mpp_identity_bound) { mpp_identity=identity.n; mpp_generation=generation.n; mpp_revision=revision.n; mpp_identity_bound=1; }
    else if (identity.n!=mpp_identity||generation.n!=mpp_generation||revision.n!=mpp_revision) { mpp_invalidate(MPP_FAIL_PROGRESS); return; }
    if (after) mpp_set_progress((uint64_t)identity.n,(uint64_t)generation.n,(uint64_t)revision.n,(uint64_t)feed.n,(uint64_t)length.n,((RuArray*)ranges.heap)->len,(uint64_t)index.n,(uint64_t)offset.n,!!eof.n,!!pending.n);
    if (after && !pending.n) {
        if (feed.n!=1000000 || length.n!=1000000 || !eof.n || ((RuArray*)ranges.heap)->len || index.n || offset.n || !mpp_text_is(phase,"scan")) mpp_invalidate(MPP_FAIL_PROGRESS);
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
    actual=make_map(code,root,receipt)
    if actual!=mapping: raise ValueError('Stale or mutated source/body mapping')
    entries={x['id']:x for x in mapping['entries']}
    for ident,name,source,start,end,body in reversed(generated_functions(code)):
        if ident not in entries: continue
        row=entries[ident]; original=f'ru_function_{ident}'; private=original+'_mpp_body'
        renamed=once(body,original+'(Env *global',private+'(Env *global')
        if row['phase']=='step':
            pre='mpp_note_step(); mpp_observe_step(args[1],0);'
            post='mpp_observe_step(args[1],1);'
        else:
            pre='mpp_token token=mpp_begin('+row['phase']+');'
            if row['phase']=='MPP_TIMER_ROOT': pre+=' if(mpp_is_active() && !mpp_bulk_binding_ok) mpp_invalidate(MPP_FAIL_PROGRESS);'
            post='mpp_leave(token);'
        wrapper=f'\nstatic Val {original}(Env *global, Val self, int call_line, Val *args) {{\n    {pre}\n    Val result={private}(global,self,call_line,args);\n    {post}\n    return result;\n}}\n'
        code=code[:start]+renamed+wrapper+code[end:]
    # Observer helpers follow runtime type declarations and precede functions.
    code=once(code,'static void ru_fail(int line, const char *format, ...)\n{',OBSERVERS+'\nstatic void ru_fail(int line, const char *format, ...)\n{\n    mpp_invalidate(MPP_FAIL_RU_FAIL);')
    for anchor,hook in [
      ('static void ru_panic_raise(Val reason, int line, int col)\n{','mpp_invalidate(MPP_FAIL_PANIC);'),
      ('static void rn_trap_restore(RuNativeTrap *trap)\n{','mpp_invalidate(MPP_FAIL_TRAP_RESTORE);'),
      ('static RuHeap *ru_new_heap(size_t size, int kind, int line)\n{','mpp_count(MPP_HOT_HEAP_NEW);'),
      ('static Val env_get(Env *env,const char *name,int line)\n{','mpp_count(MPP_HOT_ENV_GET);'),
      ('static Val v_index(Val v,Val index,int line)\n{','mpp_count(MPP_HOT_V_INDEX);'),
      ('static Val v_call(Val callable,size_t argc,const char **keys,Val *args,int line)\n{','mpp_count(MPP_HOT_V_CALL);'),
    ]: code=once(code,anchor,anchor+'\n    '+hook)
    begin='static Val rn_invoke(RuNative *function, Val parameters, int line)\n{'
    start=code.index(begin); end=code.index('\n}\n',start)+3; body=code[start:end]
    body=once(body,begin,'static Val rn_invoke_mpp_body(RuNative *function, Val parameters, int line)\n{')
    body=once(body,'    rn_platform_set_error(0);','    mpp_note_raw_native_entry(function->as.function.address==mpp_bulk_address);\n    rn_platform_set_error(0);')
    wrapper='''\nstatic Val rn_invoke(RuNative *function, Val parameters, int line) {
    mpp_token token=mpp_begin(mpp_is_active() && function->as.function.address==mpp_bulk_address?MPP_NATIVE_BULK:MPP_NATIVE_OTHER);
    Val result=rn_invoke_mpp_body(function,parameters,line);
    mpp_leave(token); return result;
}
'''
    code=code[:start]+body+wrapper+code[end:]
    code=once(code,'    /* This local root is included in the snapshot and survives logical close. */','    const mpp_token mpp_callback_token=mpp_begin(MPP_CALLBACK);\n    /* This local root is included in the snapshot and survives logical close. */')
    code=once(code,'    trap = rn_trap_new();\n    if (!trap) {','    trap = rn_trap_new();\n    if (!trap) {\n        mpp_invalidate(MPP_FAIL_TRAP_OOM);')
    code=once(code,'    v_drop(rn_value(callback));\n    rn_platform_set_error(entry_error); return answer;','    v_drop(rn_value(callback));\n    mpp_leave(mpp_callback_token);\n    rn_platform_set_error(entry_error); return answer;')
    binding=mapping['binding']; code=once(code,binding['statement'],binding['statement']+'\n                mpp_register_bulk('+binding['value']+');')
    code=once(code,'int main(int argc, char **argv) {','static int mpp_program_body(int argc, char **argv) {')
    code+='\nint main(int argc,char **argv) {\n    mpp_init();\n    int status=mpp_program_body(argc,argv);\n    (void)mpp_finalize(stdout);\n    return status;\n}\n'
    adjacency='raw = ru_native_generated_call(sig->as.signature.id, function->as.function.address, args);\n    error = rn_platform_error();'
    if code.count(adjacency)!=1: raise ValueError('Native error-read adjacency changed')
    return header+'\n'+code

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('command',choices=['map','instrument']);ap.add_argument('--source-root',type=Path,required=True);ap.add_argument('--input-c',type=Path,required=True);ap.add_argument('--receipt',type=Path,required=True);ap.add_argument('--map',type=Path,required=True);ap.add_argument('--output-c',type=Path);ap.add_argument('--header',type=Path)
    a=ap.parse_args();code=a.input_c.read_text();receipt=json.loads(a.receipt.read_text());mapping=make_map(code,a.source_root,receipt)
    if a.command=='map':
        with a.map.open('x') as f: json.dump(mapping,f,indent=2);f.write('\n')
    else:
        if not a.output_c or not a.header: ap.error('--output-c and --header required')
        sealed=json.loads(a.map.read_text());result=transform(code,a.source_root,receipt,sealed,a.header.read_text())
        with a.output_c.open('x') as f:f.write(result)
if __name__=='__main__':main()
