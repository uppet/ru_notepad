"""Fail-closed numeric/hash projection; never publish private receipts or logs."""
import hashlib, json, math, re


def need(x):
    if not x:raise ValueError('invalid_public_result')


def number(x):
    need(type(x) in (int,float,bool) and math.isfinite(x) and -2**32<=x<=1e12)
    return int(x) if type(x) is bool else x


def h(x):
    need(type(x) is str and re.fullmatch('[0-9a-f]{64}',x) is not None);return x


def fields(obj, allowed):need(type(obj) is dict and set(obj)<=set(allowed.split()))


def project(raw):
    fields(raw,'schema observer_revision markdown_poll_seconds markdown_native_common_separate markdown_diagnostics feasibility_only baseline_commit fixture_sha256 harness_sha256 receipt_sha256 clock_resolution_seconds requested_poll_seconds stages_seconds process_seconds text_times_are_observable_upper_bounds runs host npp_version toolchain runtime_sha256')
    need(raw['schema']==2 and raw['feasibility_only'] is True)
    need(type(raw['observer_revision']) is int and raw['observer_revision']==2)
    need(type(raw['markdown_poll_seconds']) in (int,float) and raw['markdown_poll_seconds']==.25)
    need(type(raw['markdown_native_common_separate']) is int and raw['markdown_native_common_separate']==0)
    need(type(raw['markdown_diagnostics']) is int and raw['markdown_diagnostics']==1)
    need(raw['baseline_commit']=='6aa535d62c28cc9a03f33c3610fe99b3cf1bd14e')
    need(raw['stages_seconds']==30 and raw['process_seconds']==120)
    out={'schema':2,'observer_revision':2,'markdown_poll_seconds':.25,'markdown_native_common_separate':0,'markdown_diagnostics':1,'feasibility_only':1,'baseline_commit':raw['baseline_commit'],'runs':[]}
    if 'host' in raw:
        host=raw['host'];fields(host,'windows_version cpu_count cpu_identifier_sha256 runner_image_sha256')
        need(len(host['windows_version'])==3)
        out['host']={'windows_version':[number(x) for x in host['windows_version']], 'cpu_count':number(host['cpu_count']),
                     'cpu_identifier_sha256':h(host['cpu_identifier_sha256']),'runner_image_sha256':h(host['runner_image_sha256'])}
    if 'npp_version' in raw:
        need(raw['npp_version']==[8,9,8,1]);out['npp_version']=raw['npp_version']
    if 'toolchain' in raw:
        tools=raw['toolchain'];fields(tools,'gcc.exe g++.exe windres.exe ar.exe ranlib.exe mingw32-make.exe')
        out['toolchain']={}
        for name,item in tools.items():
            fields(item,'sha256 version_stdout_sha256 path_sha256');out['toolchain'][name]={key:h(value) for key,value in item.items()}
    if 'runtime_sha256' in raw:
        runtime=raw['runtime_sha256'];fields(runtime,'ru npp');out['runtime_sha256']={}
        for arm,item in runtime.items():
            # Only executable/DLL identities belong in public output, not config names.
            names=('ru_notepad.exe','Scintilla.dll','Lexilla.dll','RuSyntax.dll') if arm=='ru' else ('notepad++.exe','SciLexer.dll','Scintilla.dll','Lexilla.dll')
            out['runtime_sha256'][arm]={name:h(item[name]) for name in names if name in item}
    for key in ('fixture_sha256','harness_sha256','receipt_sha256'):out[key]=h(raw[key])
    for key in ('clock_resolution_seconds','requested_poll_seconds','stages_seconds','process_seconds','text_times_are_observable_upper_bounds'):out[key]=number(raw[key])
    need(type(raw['runs']) is list and len(raw['runs'])<=3)
    for index,row in enumerate(raw['runs']):
        fields(row,'arm executed stages passed pid error_type elapsed_upper_ms timed_out exit_code cleanup_unconfirmed fixture_unchanged runtime_unchanged provenance_unchanged')
        need(row['arm']=='ABC'[index])
        r={'arm':index,'stages':[]}
        for key,value in row.items():
            if key in ('arm','stages','error_type'):continue
            r[key]=None if value is None else number(value)
        if 'error_type' in row:
            kinds=('ValueError','RuntimeError','TimeoutError','OSError','FileNotFoundError','PermissionError','TimeoutExpired')
            r['error_kind']=kinds.index(row['error_type'])+1 if row['error_type'] in kinds else 99
        need(len(row['stages'])<=4)
        for j,stage in enumerate(row['stages']):
            fields(stage,'operation completed censored pending_poll_count undo_commands undo_acknowledged first_text_upper_ms first_common_upper_ms savepoint_text_upper_ms rounds poll_gaps_ms dispatches last wall_ms')
            need(stage['operation']==('open','insert','backspace','undo')[j])
            s={'operation':j}
            for key,value in stage.items():
                if key in ('operation','rounds','poll_gaps_ms','dispatches','last'):continue
                s[key]=None if value is None else number(value)
            gaps=stage.get('poll_gaps_ms',[]);need(type(gaps) is list and len(gaps)<=25000)
            values=sorted(number(v) for v in gaps)
            s['poll_count']=len(values)
            if values:
                s['poll_gap_min_ms']=values[0];s['poll_gap_max_ms']=values[-1]
                s['poll_gap_p50_ms']=values[(len(values)-1)//2];s['poll_gap_p95_ms']=values[int((len(values)-1)*.95)]
            s['rounds']=[]
            for item in stage.get('rounds',[]):
                fields(item,'command dirty length upper_ms');s['rounds'].append({k:number(v) for k,v in item.items()})
            need(len(s['rounds'])<=2)
            s['dispatches']=[]
            for item in stage.get('dispatches',[]):
                fields(item,'acknowledged delivery_completion_unknown upper_ms');s['dispatches'].append({k:number(v) for k,v in item.items()})
            need(len(s['dispatches'])<=2)
            if 'last' in stage:
                last=stage['last'];fields(last,'length dirty context lexer endstyled styles fold_header markdown_id markdown_gen markdown_rev markdown_pending markdown_length markdown_feed')
                s['last']={k:number(v) for k,v in last.items() if k not in ('context','styles')}
                if 'context' in last:
                    need(type(last['context']) is list and len(last['context'])==4 and all(type(v) is int and 0<=v<=255 for v in last['context']))
                    s['last']['context_sha256']=hashlib.sha256(bytes(last['context'])).hexdigest()
                if 'styles' in last:
                    need(len(last['styles'])==16);s['last']['styles']=[number(v) for v in last['styles']]
            r['stages'].append(s)
        out['runs'].append(r)
    encoded=json.dumps(out,allow_nan=False).encode();need(len(encoded)<=65536)
    return out
