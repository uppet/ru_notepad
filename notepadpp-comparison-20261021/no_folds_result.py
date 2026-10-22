"""Closed numeric/hash-only schema4; no source, private paths or log uploads."""
import json,sys
from pathlib import Path
from npp_udl_result import exact,integer,num,h,need,unique

def validate(x):
    exact(x,'schema observer_revision baseline_commit compiler_commit stages_seconds process_seconds poll_seconds order repetitions opening_compared disabled_marker_after_edits style_semantic_equivalence fixture_sha256 harness_sha256 receipt_sha256 runtime_sha256 udl_sha256 host runs')
    for key,value in [('schema',4),('observer_revision',4),('repetitions',1),('opening_compared',0),('disabled_marker_after_edits',0),('style_semantic_equivalence',0)]:integer(x[key],value,value)
    need(x['baseline_commit']=='6aa535d62c28cc9a03f33c3610fe99b3cf1bd14e' and x['compiler_commit']=='85c7821fda35aa79deeaf67b4d430f24ddd7f07f')
    need(x['poll_seconds']==[.005,.005,.250])
    need(x['stages_seconds']==30 and x['process_seconds']==120 and x['order']==[0,1,2])
    need(type(x['fixture_sha256']) is list and len(x['fixture_sha256'])==2)
    for v in x['fixture_sha256']:h(v)
    need(x['fixture_sha256']==['cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0','9c5273d9a114f3d9c2bdc39d427dc8fe783c6cfc6db1ddfafdb1a4417aa6c96a'])
    for k in ('harness_sha256','receipt_sha256','udl_sha256'):h(x[k])
    exact(x['runtime_sha256'],'ru npp')
    exact(x['runtime_sha256']['ru'],'ru_notepad.exe Scintilla.dll Lexilla.dll RuSyntax.dll')
    exact(x['runtime_sha256']['npp'],'notepad++.exe')
    for product in x['runtime_sha256'].values():
        for v in product.values():h(v)
    exact(x['host'],'windows_version cpu_count cpu_identifier_sha256 runner_image_sha256')
    need(type(x['host']['windows_version']) is list and len(x['host']['windows_version'])==3)
    for v in x['host']['windows_version']:integer(v)
    integer(x['host']['cpu_count'],1,4096);h(x['host']['cpu_identifier_sha256']);h(x['host']['runner_image_sha256'])
    need(type(x['runs']) is list and 1<=len(x['runs'])<=6)
    for i,r in enumerate(x['runs']):
        exact(r,'arm fixture passed executed cleanup_unconfirmed runtime_unchanged fixture_unchanged provenance_unchanged error_kind stages')
        integer(r['arm'],i%3,i%3);integer(r['fixture'],i//3,i//3)
        for k in ('passed','executed','cleanup_unconfirmed','runtime_unchanged','fixture_unchanged','provenance_unchanged'):integer(r[k],0,1)
        integer(r['error_kind'],0,99)
        if i<len(x['runs'])-1:need(r['passed']==1)
        need(type(r['stages']) is list and len(r['stages'])<=4)
        if r['passed']:need(len(r['stages'])==4 and r['executed']==1 and r['error_kind']==0 and r['cleanup_unconfirmed']==0 and all(r[k]==1 for k in ('runtime_unchanged','fixture_unchanged','provenance_unchanged')))
        for j,s in enumerate(r['stages']):
            exact(s,'operation completed censored rounds dispatches')
            integer(s['operation'],j,j);integer(s['completed'],0,1);integer(s['censored'],0,1)
            need(type(s['dispatches']) is list and len(s['dispatches'])<=2)
            for d in s['dispatches']:
                exact(d,'acknowledged delivery_completion_unknown upper_ms')
                integer(d['acknowledged'],0,1);integer(d['delivery_completion_unknown'],0,1);num(d['upper_ms'])
                need(d['acknowledged']+d['delivery_completion_unknown']==1)
            need(type(s['rounds']) is list and len(s['rounds'])<=(2 if j==3 else 1))
            for k,v in enumerate(s['rounds']):
                exact(v,'command length dirty text_upper_ms style_upper_ms ready_upper_ms total_upper_ms endstyled lexer styles')
                integer(v['command'],k+1 if j==3 else 0,k+1 if j==3 else 0)
                integer(v['length'],1,1000001)
                base_length=(1000000,14208)[r['fixture']]
                need(v['length']==base_length+int(j==1 or (j==3 and k==0 and v['dirty']==1)))
                if j!=3:need(v['dirty']==int(j in (1,2)))
                if j==3 and k==1:need(v['dirty']==0)
                integer(v['dirty'],0,1);integer(v['endstyled'],v['length'],v['length']);integer(v['lexer'],152 if r['arm']==1 else 98,152 if r['arm']==1 else 98)
                for t in ('text_upper_ms','style_upper_ms','ready_upper_ms','total_upper_ms'):num(v[t],0,120000)
                need(v['text_upper_ms']<=v['style_upper_ms']<=v['ready_upper_ms']<=v['total_upper_ms']+1)
                need(type(v['styles']) is list and len(v['styles'])==(19 if r['fixture'] else 16))
                for value in v['styles']:integer(value,0,255)
                need(all(value!=0 for value in v['styles'][-3:]) if r['fixture'] else v['styles']==[0]*16)
            if j==3 and len(s['rounds'])==2:need(s['rounds'][0]['dirty']==1)
            if s['completed']:
                need(s['censored']==0 and len(s['rounds'])>=1)
                need(s['rounds'][-1]['dirty']==int(j in (1,2)))
                need(len(s['dispatches'])==(0 if j==0 else len(s['rounds']) if j==3 else 1))
                need(all(d['acknowledged']==1 for d in s['dispatches']))
            if r['passed']:need(s['completed']==1)
    need(len(json.dumps(x,allow_nan=False).encode())<=65536)
    return x

if __name__=='__main__':
    try:
        p=Path(sys.argv[1]);need(p.is_file() and not p.is_symlink() and p.stat().st_nlink==1 and p.stat().st_size<=65536)
        validate(json.loads(p.read_text(encoding='utf-8'),object_pairs_hook=unique))
    except Exception:
        print('NO_FOLDS_PUBLIC_VALIDATION_FAILED',file=sys.stderr);raise SystemExit(1)
