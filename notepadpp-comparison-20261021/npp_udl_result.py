"""Closed schema3: two stock NPP modes, no invented Ru provenance or prose."""
import hashlib,json,math,re,sys
from pathlib import Path
from public_result import need,fields,h

def num(x,lo=0,hi=1e12):
    need(type(x) in (int,float) and math.isfinite(x) and lo<=x<=hi)
def integer(x,lo=0,hi=2**32-1):
    need(type(x) is int and lo<=x<=hi)
def exact(x,names):
    fields(x,names);need(set(x)==set(names.split()))
def validate(x):
    exact(x,'schema observer_revision feasibility_only text_times_are_observable_upper_bounds folding_completion_measured npp_version helper_commit official_source_commit archive_sha256 udl_sha256 udl_canonical_sha256 executable_sha256 fixture_sha256 harness_sha256 receipt_sha256 host clock_resolution_seconds requested_poll_seconds stages_seconds process_seconds official_fold_rules official_nonempty_fold_rules runs')
    for key,value in [('feasibility_only',1),('text_times_are_observable_upper_bounds',1),('folding_completion_measured',0)]:integer(x[key],value,value)
    need(type(x['schema']) is int and x['schema']==3)
    need(type(x['observer_revision']) is int and x['observer_revision']==3)
    need(x['npp_version']==[8,9,8,1] and all(type(v) is int for v in x['npp_version']))
    need(x['helper_commit']=='6aa535d62c28cc9a03f33c3610fe99b3cf1bd14e')
    need(x['official_source_commit']=='dd40fe45598791e9aa38f3aeb200e10fb3d6338a')
    for key in ('archive_sha256','udl_sha256','udl_canonical_sha256','executable_sha256','fixture_sha256','harness_sha256','receipt_sha256'):h(x[key])
    need(x['archive_sha256']=='beddf5548e75c97930d1575ba1c7d113e6e2b33d0a200310e734ca08e225f414')
    need(x['udl_canonical_sha256']=='b5564310454e1c1a71127836ecc8ad7671c5ecaf5e024202d33e21c79b5107dc')
    for key,value in [('requested_poll_seconds',.005),('stages_seconds',30),('process_seconds',120),('official_fold_rules',9),('official_nonempty_fold_rules',0)]:num(x[key]);need(x[key]==value)
    num(x['clock_resolution_seconds'],1e-12,1)
    exact(x['host'],'windows_version cpu_count cpu_identifier_sha256 runner_image_sha256')
    need(type(x['host']['windows_version']) is list and len(x['host']['windows_version'])==3)
    for v in x['host']['windows_version']:integer(v)
    integer(x['host']['cpu_count'],1,4096)
    h(x['host']['cpu_identifier_sha256']);h(x['host']['runner_image_sha256'])
    need(type(x['runs']) is list and 1<=len(x['runs'])<=2)
    if len(x['runs'])==2:need(x['runs'][0]['passed']==1)
    for i,r in enumerate(x['runs']):
        exact(r,'mode executed passed pid exit_code cleanup_unconfirmed runtime_unchanged fixture_unchanged provenance_unchanged udl_unchanged error_kind elapsed_upper_ms stages')
        integer(r['mode'],i,i)
        for key in ('executed','passed','cleanup_unconfirmed','runtime_unchanged','fixture_unchanged','provenance_unchanged','udl_unchanged'):integer(r[key],0,1)
        integer(r['pid']);integer(r['exit_code'],-1,2**32-1);integer(r['error_kind'],0,99);num(r['elapsed_upper_ms'])
        need(type(r['stages']) is list and len(r['stages'])<=4)
        if r['passed']:need(r['error_kind']==0 and r['pid']>0 and len(r['stages'])==4 and r['executed']==1 and r['cleanup_unconfirmed']==0 and all(r[k]==1 for k in ('runtime_unchanged','fixture_unchanged','provenance_unchanged','udl_unchanged')))
        for j,s in enumerate(r['stages']):
            exact(s,'operation completed censored first_text_upper_ms first_common_upper_ms savepoint_text_upper_ms wall_ms undo_commands undo_acknowledged poll_count dispatches rounds last mode_proof')
            integer(s['operation'],j,j)
            for k in ('completed','censored'):integer(s[k],0,1)
            for k in ('first_text_upper_ms','first_common_upper_ms','savepoint_text_upper_ms','wall_ms'):
                if s[k] is not None:num(s[k])
            for k in ('undo_commands','undo_acknowledged'):integer(s[k],0,2)
            integer(s['poll_count'],0,25000)
            need(type(s['dispatches']) is list and len(s['dispatches'])<=2)
            for d in s['dispatches']:
                exact(d,'acknowledged delivery_completion_unknown upper_ms')
                integer(d['acknowledged'],0,1);integer(d['delivery_completion_unknown'],0,1);num(d['upper_ms'])
            need(type(s['rounds']) is list and len(s['rounds'])<=2)
            for v in s['rounds']:
                exact(v,'command dirty length upper_ms');integer(v['command'],0,2);integer(v['dirty'],0,1);integer(v['length']);num(v['upper_ms'])
            if s['last'] is not None:
                fields(s['last'],'length dirty context_sha256 lexer endstyled fold_header styles')
                need({'length','dirty'}<=set(s['last']))
                for k,v in s['last'].items():
                    if k=='context_sha256':h(v)
                    elif k=='styles':
                        need(type(v) is list and len(v)==16)
                        for n in v:integer(n,0,255)
                    else:integer(v)
            if s['mode_proof'] is not None:
                q=s['mode_proof'];exact(q,'language_type lexer udl_menu_id udl_menu_checked plain_menu_checked total_buffer_count primary_buffer_count secondary_buffer_count current_view current_doc_index secondary_hidden single_visible_editor same_buffer')
                for v in q.values():integer(v)
                need(q['language_type']==(0 if i==0 else 15) and q['lexer'] in ((0,1) if i==0 else (152,)))
                need(46181<=q['udl_menu_id']<=46210 and q['udl_menu_checked']==i and q['plain_menu_checked']==1-i and q['total_buffer_count']==2 and q['primary_buffer_count']==1 and q['secondary_buffer_count']==1 and q['current_view']==0 and q['current_doc_index']==0 and q['secondary_hidden']==1 and q['single_visible_editor']==1 and q['same_buffer']==1)
            if s['completed']:
                need(s['mode_proof'] is not None and s['last'] is not None and s['wall_ms'] is not None and s['first_text_upper_ms'] is not None and s['first_common_upper_ms'] is not None)
                v=s['last'];exact(v,'length dirty context_sha256 lexer endstyled fold_header styles')
                need(v['length']==1000000+int(j==1) and v['dirty']==int(j in (1,2)) and v['styles']==[0]*16 and v['fold_header']==0)
                need(v['context_sha256']==hashlib.sha256(bytes((97,97,120 if j==1 else 97,97))).hexdigest())
                need(v['lexer'] in ((0,1) if i==0 else (152,)))
                if i:need(v['endstyled']==v['length'])
            if r['passed']:need(s['completed']==1 and s['censored']==0)
    need(len(json.dumps(x,allow_nan=False).encode())<=65536)
    return x

def unique(pairs):
    d={}
    for k,v in pairs:need(k not in d);d[k]=v
    return d
if __name__=='__main__':
    try:
        p=Path(sys.argv[1]);need(p.is_file() and not p.is_symlink() and p.stat().st_nlink==1 and p.stat().st_size<=65536)
        validate(json.loads(p.read_text(encoding='utf-8'),object_pairs_hook=unique))
    except Exception:
        print('NPP_UDL_PUBLIC_VALIDATION_FAILED',file=sys.stderr);raise SystemExit(1)
