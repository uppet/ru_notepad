#!/usr/bin/env python3
"""Owned same-source Markdown edit/Undo study; diagnostic, never acceptance.

Uses an exact-source private adapter of the product stage runner. Its two
30 s rejections become sticky product-gate failures while bounded diagnostic
observation may continue; real input/style/fold/paint proofs are preserved.
Each entire process also has the original 120 s absolute owned-process bound.
No attach, foreign process termination, forced savepoint, timeout relaxation,
whole-content upload, or replacement document fixture is permitted.
"""
from __future__ import annotations
import hashlib, json, math, os, re, stat, subprocess, sys, tempfile, time
from pathlib import Path
import run_markdown_phase_profile as base

OPERATIONS=('open','insert','backspace','undo')
PREFIX='RU_MARKDOWN_EDIT_PROFILE '
UINT64_MAX=(1<<64)-1
PUBLIC_LIMIT=64*1024


def require(value, code='edit_schema'):
    if not value: base.fail(code)


def integer(value, maximum=UINT64_MAX):
    require(type(value) is int and 0<=value<=maximum,'edit_integer')
    return value


def finite(value, maximum=120000):
    require(type(value) in (int,float) and math.isfinite(value) and 0<=value<=maximum,'edit_number')
    return value


def object_fields(value, keys):
    require(type(value) is dict and set(value)==set(keys))
    return value


def tuple_of(route):
    return tuple(integer(route[key],(1<<53)-1) for key in ('id','gen','rev'))



def diagnostic_stage(ci, gate):
    """Private exact-source adapter; product implementation/constant untouched.

    Only two original 30-second rejection statements become sticky gate-failure
    notifications. All actual input/proof and five-second response gates remain.
    The independently owned 120-second guard remains the absolute lifetime bound.
    """
    import ast,inspect
    require(base.digest(Path(ci.__file__))=='5e87bfee0c516f3e805c6bbdd9b32d24f6d2f818474cfb7d0538ba4422389b8e','edit_stage_source_changed')
    source=inspect.getsource(ci.run_gui_markdown_stage)
    tree=ast.parse(source)
    expected={'Markdown GUI open/edit exceeded its original 30-second deadline',
              'Markdown GUI final proof exceeded its original 30-second deadline'}
    found=[]
    class Adapter(ast.NodeTransformer):
        def visit_Raise(self,node):
            error=node.exc
            if (isinstance(error,ast.Call) and isinstance(error.func,ast.Name) and error.func.id=='RuntimeError'
                and len(error.args)==1 and isinstance(error.args[0],ast.Constant) and error.args[0].value in expected):
                found.append(error.args[0].value)
                return ast.copy_location(ast.Expr(ast.Call(ast.Name('_diagnostic_gate_failed',ast.Load()),[],[])),node)
            return node
    modified=Adapter().visit(tree)
    require(len(found)==2 and set(found)==expected,'edit_stage_adapter_mismatch')
    require(hashlib.sha256(source.encode()).hexdigest()=='53fac8b6592fbd5cf9614e7a79fe6b9b6ff706469c847f7b2eb711dabbddf8f6','edit_stage_function_changed')
    ast.fix_missing_locations(modified)
    namespace=dict(ci.run_gui_markdown_stage.__globals__)
    from markdown_edit_observers import adapted
    observers=adapted(ci)
    namespace.update({key:observers[key] for key in ('GuiRuObserver','MarkdownProcessMemory')})
    namespace['_diagnostic_gate_failed']=lambda:gate.update(product_gate_failed=True)
    exec(compile(modified,'<owned-markdown-diagnostic-stage>','exec'),namespace)
    return namespace['run_gui_markdown_stage']


def perform_edits(ci,api,process,deadline,source,logs,guard,sleeper,stages,gates):
    require(ci.GUI_MARKDOWN_TIMEOUT_SECONDS==30,'product_deadline_changed')
    def check():
        deadline.remaining()
        if guard.error: base.fail(guard.error)
        logs.inspect()
        if process.poll() is not None: base.fail('premature_gui_exit')
        return api.no_dialog(process.pid)
    hwnd=None
    while hwnd is None:
        mains=[h for h,name,visible in check() if name==base.MAIN_CLASS and visible]
        require(len(mains)<=1,'duplicate_main_window')
        if mains:
            hwnd=mains[0];api.verify_owned_handles(process.pid,hwnd)
        else: deadline.sleep(sleeper)
    for operation in OPERATIONS:
        check();stage={};stages.append(stage)
        gate={'product_gate_failed':False};gates.append(gate)
        editor=api.editor(hwnd);api.verify_owned_handles(process.pid,hwnd,editor)
        if operation!='open': api.scalar(editor,2025,9 if operation=='backspace' else 8)
        def action():
            check()
            if operation=='open': api.drop(editor,[source])
            elif operation=='insert':
                api.scalar(editor,0x0102,ord('x'),1);api.command(hwnd,504)
            elif operation=='backspace':
                api.scalar(editor,0x0100,8,1);api.scalar(editor,0x0101,8,0xc0000001);api.command(hwnd,504)
            else: api.command(hwnd,201)
        # Only the two timeout exceptions are adapted; functional proof is unchanged.
        # It issues the second Undo only when required by actual dirty/history.
        try:
            diagnostic_stage(ci,gate)(api,process,hwnd,source,'unclosed-fence',operation,stage,action)
        finally:
            if stage.get('wall_ms',0)>30000:gate['product_gate_failed']=True
        check()
    validate_stages(ci,stages,allow_late=True)
    base.verify_fixture(base.bounded_read(source,base.FIXTURE_SIZE))
    return hwnd


def validate_stages(ci,stages,*,allow_late=False):
    require(type(stages) is list and len(stages)==4,'edit_stage_count')
    previous=None
    if allow_late:
        from markdown_edit_observers import adapted
        observers=adapted(ci)
    for operation,stage in zip(OPERATIONS,stages):
        require(type(stage) is dict and set(stage)==ci.GUI_MARKDOWN_STAGE_FIELDS,'edit_stage_schema')
        data,styles,folds=ci.markdown_expected('unclosed-fence',operation)
        dirty=operation in ('insert','backspace')
        require(stage['operation']==operation and stage['length']==len(data) and stage['dirty'] is dirty)
        require(stage['source_sha256']==base.FIXTURE_SHA256 and stage['collapsed_before_edit'] is False)
        finite(stage['wall_ms'],120000 if allow_late else 30000);require(integer(stage['probes'])>0)
        commands=integer(stage['undo_commands'],2)
        require(1<=commands<=2 if operation=='undo' else commands==0)
        ci.validate_markdown_progress(stage['last_progress'],complete=True,expected_length=len(data),expected_dirty=dirty)
        route=stage['last_progress']['diagnostic'];current=tuple_of(route)
        if previous is not None:
            require(current[1]==previous[1] and current[0]>previous[0] and current[2]>previous[2],'edit_revision_order')
        previous=current
        observer_validator=observers['validate_gui_ru_observer'] if allow_late else ci.validate_gui_ru_observer
        memory_validator=observers['validate_markdown_memory'] if allow_late else ci.validate_markdown_memory
        observer_validator(stage['observer'],stage['wall_ms'],stage['probes'])
        memory_validator(stage['memory'],stage['observer'],stage['wall_ms'])
        if dirty: ci.validate_gui_markdown_responsiveness(stage['responsiveness'],stage['wall_ms'])
        else: require(stage['responsiveness']=={})
        p=stage['last_probe']
        object_fields(p,('length','dirty','end_styled','status_done','styles_match','style_samples','folds_match','context_match','lexer','tail_requested','children_visible'))
        require(p['length']==p['end_styled']==len(data) and p['dirty'] is dirty and p['lexer']==98)
        require(all(p[k] is True for k in ('status_done','styles_match','folds_match','context_match','tail_requested','children_visible')))
        positions=[n for probe in styles for n in range(probe['offset'],probe['offset']+probe['length'])]
        expected=[probe['style'] for probe in styles for _ in range(probe['length'])]
        object_fields(p['style_samples'],('positions','expected','actual'))
        require(len(positions)==16 and p['style_samples']==dict(positions=positions,expected=expected,actual=expected))


def validate_row(row):
    # Exact schema supplied by the diagnostic header; no arbitrary strings pass.
    fixed={'schema':1}
    numbers=('failure_code','foreign_thread_invalid','started','completion_requested','complete','closed','depth',
        'qpc_frequency','root_count','no_step_root_count','step_count','outermost_root_ticks','root_user_100ns',
        'root_kernel_100ns','inter_root_gap_ticks','inter_root_gap_max_ticks','raw_native_other_entries','raw_native_bulk_entries',
        'snapshot_index','scan_bytes')
    object_fields(row,(*fixed,*numbers,'hot_names','hot_totals','phases','progress'))
    require(all(type(row[k]) is type(v) and row[k]==v for k,v in fixed.items()),'edit_phase_claim')
    for k in numbers: integer(row[k])
    require(all(row[k]==0 for k in ('failure_code','foreign_thread_invalid','depth','completion_requested')))
    require(all(row[k]==1 for k in ('started','complete','closed')))
    require(row['qpc_frequency']>0 and row['root_count']>0 and row['step_count']>0)
    require(row['no_step_root_count']<row['root_count'] and row['inter_root_gap_max_ticks']<=row['inter_root_gap_ticks'])
    require(row['hot_names']==['v_index','env_get','heap_new','v_call'])
    require(type(row['hot_totals']) is list and len(row['hot_totals'])==4)
    for n in row['hot_totals']: integer(n)
    require(type(row['phases']) is list and len(row['phases'])==8)
    for phase,name in zip(row['phases'],base.PHASES):
        object_fields(phase,('name','entries','inclusive_ticks','exclusive_ticks','hot'))
        require(phase['name']==name)
        for k in ('entries','inclusive_ticks','exclusive_ticks'): integer(phase[k])
        require(phase['exclusive_ticks']<=phase['inclusive_ticks'])
        require(type(phase['hot']) is list and len(phase['hot'])==4)
        for n in phase['hot']: integer(n)
        require(phase['entries']!=0 or not (phase['inclusive_ticks'] or phase['exclusive_ticks'] or any(phase['hot'])))
    require(sum(p['exclusive_ticks'] for p in row['phases'])==row['outermost_root_ticks'],'edit_exclusive_partition')
    require(all(sum(p['hot'][i] for p in row['phases'])==row['hot_totals'][i] for i in range(4)),'edit_hot_partition')
    p=object_fields(row['progress'],('identity','generation','revision','feed','length','range_count','range_index','range_offset','eof','pending'))
    for n in p.values(): integer(n,(1<<53)-1)
    require(p['length'] in (1000000,1000001) and p['feed']==p['length'] and p['eof']==1)
    require(all(p[k]==0 for k in ('range_count','range_index','range_offset','pending')))
    return row


def row_tuple(row):
    p=row['progress'];return p['identity'],p['generation'],p['revision']


def counters(row):
    # Only additive quantities may be differenced. Maxima are deliberately absent.
    return [row[k] for k in ('root_count','no_step_root_count','step_count','outermost_root_ticks','root_user_100ns',
        'root_kernel_100ns','inter_root_gap_ticks','raw_native_other_entries','raw_native_bulk_entries','scan_bytes')]+list(row['hot_totals'])+[
        p[k] for p in row['phases'] for k in ('entries','inclusive_ticks','exclusive_ticks')]+[v for p in row['phases'] for v in p['hot']]


def validate_profile(record,stages):
    object_fields(record,('schema','record','diagnostic_only','product_acceptance','valid','raw_counts_trusted','failure_code','snapshot_count','records','final','timing_kind','cpu_kind','sampling','whole_process_hotspots'))
    fixed={'schema':1,'record':'markdown_edit_profile','diagnostic_only':True,'product_acceptance':'separate_not_claimed',
        'valid':True,'raw_counts_trusted':True,'failure_code':0,'timing_kind':'nested_qpc_wall',
        'cpu_kind':'outer_timer_thread_only','sampling':False,'whole_process_hotspots':False}
    require(all(type(record[k]) is type(v) and record[k]==v for k,v in fixed.items()),'edit_profile_invalid')
    rows=record['records'];require(type(rows) is list and len(rows)==record['snapshot_count'] and len(rows) in (4,5))
    require(len(rows)==3+stages[-1]['undo_commands'],'edit_undo_snapshot_count')
    previous=None
    scanned=0
    for index,row in enumerate(rows,1):
        validate_row(row);require(row['snapshot_index']==index)
        scanned+=row['progress']['length'];require(row['scan_bytes']==scanned,'edit_scan_bytes')
        require(row['step_count']>(previous['step_count'] if previous else 0),'edit_empty_revision')
        for phase_index in (2,3,6):
            require(row['phases'][phase_index]['entries']>(previous['phases'][phase_index]['entries'] if previous else 0),'edit_empty_phase')
        if previous is not None:
            a,b=row_tuple(previous),row_tuple(row)
            require(b[1]==a[1] and b[0]>a[0] and b[2]>a[2],'edit_snapshot_order')
            require(row['qpc_frequency']==previous['qpc_frequency'])
            require(all(b>=a for a,b in zip(counters(previous),counters(row))),'edit_counter_regression')
        previous=row
    final=validate_row(record['final'])
    require(final['snapshot_index']==len(rows) and row_tuple(final)==row_tuple(rows[-1]))
    require(final['qpc_frequency']==rows[-1]['qpc_frequency'])
    require(final['scan_bytes']==scanned,'edit_final_scan')
    require(all(b>=a for a,b in zip(counters(rows[-1]),counters(final))),'edit_final_regression')
    for stage,row in zip(stages[:3]+stages[-1:],rows[:3]+rows[-1:]):
        route=stage['last_progress']['diagnostic']
        require(row_tuple(row)==tuple_of(route),'edit_route_disagreement')
        require(row['progress']['length']==stage['length'])
    # A second Undo restores the original after an intermediate inserted state.
    if len(rows)==5: require(rows[3]['progress']['length']==1000001,'edit_intermediate_undo')
    return record


def validate_launcher(text,variant,stages):
    base.validate_launcher(text,False)
    lines=[line for line in text.splitlines() if PREFIX.rstrip() in line]
    require(len(lines)==int(variant=='profile'),'edit_profile_record_count')
    if not lines:return None
    require(lines[0].startswith(PREFIX) and len(lines[0].encode())<=49152,'edit_profile_record_size')
    return validate_profile(base.json_decode(lines[0][len(PREFIX):]),stages)


def windows_api(ci,process,deadline):
    # Keep the shared owned-handle + SendMessageTimeout implementation, but
    # dispatch WM_NULL directly to the unwrapped class primitive. Otherwise
    # GuiRuObserver would wrap responsive AND its nested self.scalar and count
    # one synchronous native call twice (including double wall accounting).
    import types
    api=base.windows_api(ci,process,deadline)
    primitive=type(api).scalar
    def responsive(self,hwnd):return primitive(self,hwnd,0)
    api.responsive=types.MethodType(responsive,api)
    return api


def run_owned(variant, directory, source, ci, styles, folds, *,
              spawn=subprocess.Popen, api_factory=windows_api, cpu_query=base.process_cpu,
              clock=time.monotonic, sleeper=time.sleep, guard_factory=base.OwnedGuard, environment=None):
    """The only function authorized to create or terminate an application."""
    result = {'variant': variant, 'executed': False, 'passed': False,
              'cleanup_killed': False, 'cleanup_unconfirmed': False}
    process = guard = logs = deadline = api = None
    result['stages'] = []
    result['gates'] = []
    result['diagnostic_complete'] = False
    try:
        base.verify_fixture(base.bounded_read(source, base.FIXTURE_SIZE))
        base.runtime_inventory(directory)
        # Starting before Popen is conservative: launch latency consumes budget.
        started = clock()
        deadline = base.Deadline(started, clock)
        process = spawn([str(directory / 'ru_notepad.exe'), '--markdown-phase-diagnostics'],
                        cwd=directory, creationflags=0x00000008,
                        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        close_fds=True, env=dict(os.environ if environment is None else environment))
        result['executed'] = True
        result['owned_pid'] = process.pid
        logs = base.OwnedLog(directory, process.pid)
        guard = guard_factory(process, deadline, logs)
        deadline.remaining()
        api = api_factory(ci, process, deadline)
        hwnd = perform_edits(ci, api, process, deadline, source, logs, guard, sleeper, result['stages'], result['gates'])
        api.close(hwnd)
        result['close_posted'] = True
        while process.poll() is None:
            deadline.remaining()
            if guard.error:
                base.fail(guard.error)
            api.no_dialog(process.pid)
            logs.inspect()
            deadline.sleep(sleeper)
        deadline.remaining()
        result['exit_code'] = process.returncode
        if process.returncode != 0:
            base.fail('nonzero_exit')
        if guard.error:
            base.fail(guard.error)
        result['scenario_wall_ms'] = round((deadline.now() - started) * 1000, 6)
        result['process_cpu'] = cpu_query(process)
        base.validate_process_cpu(result['process_cpu'])
        text = logs.read()
        record = validate_launcher(text, variant, result['stages'])
        if record is not None: result['edit_profile'] = record
        base.verify_fixture(base.bounded_read(source, base.FIXTURE_SIZE))
        # The child has already exited; validation does not extend its lifetime.
        result['diagnostic_complete'] = True
        result['passed'] = not any(g['product_gate_failed'] for g in result['gates'])
    except Exception as exc:
        result['failure'] = str(exc) if isinstance(exc, base.StudyError) else 'runner_exception'
    finally:
        if process is not None:
            if guard is not None:
                if process.poll() is None:
                    guard.kill()
                result['cleanup_killed'] = guard.killed
                guard.stop()
            elif process.poll() is None:
                result['cleanup_killed'] = True
                try:
                    process.kill()
                except OSError:
                    pass
            # No second grace period after 120s and no PID-based kill fallback.
            result['cleanup_unconfirmed'] = process.poll() is None
            if result['cleanup_killed'] or result['cleanup_unconfirmed']:
                result['passed'] = False
                result['diagnostic_complete'] = False
            if process.poll() is not None:
                result.setdefault('exit_code', process.returncode)
                if 'process_cpu' not in result:
                    try:
                        result['process_cpu'] = cpu_query(process)
                    except Exception:
                        result['process_cpu_unavailable'] = True
            if logs is not None:
                try:
                    logs.inspect()
                except base.StudyError as exc:
                    result['diagnostic_complete'] = False
                    if str(exc) == 'output_overflow':
                        result['passed'] = False
                        result['output_overflow'] = True
                        try:
                            logs.cap_after_exit(process)
                            result['retained_log_capped'] = True
                        except Exception:
                            result['retained_output_unconfirmed'] = True
                    else:
                        result['passed'] = False
                        result.setdefault('failure', str(exc))
                        if str(exc) != 'missing_owned_launcher_log':
                            result['retained_output_unconfirmed'] = True
            if deadline is not None:
                result['last_observed_wall_ms'] = round(max(0, clock() - deadline.started) * 1000, 6)
    if api is not None:
        try: api.release_drops()
        except Exception:
            result['passed'] = False
            result['drop_cleanup_failed'] = True
            result['diagnostic_complete'] = False
    return result



def run_pair(receipt,source_root,release_dir,profile_dir,output,*,ci=None,run=run_owned):
    manifest=base.verify_manifest(receipt,source_root,release_dir,profile_dir)
    output=Path(os.path.abspath(output));base.checked_path(output.parent,directory=True)
    output.mkdir(mode=0o700);base.ensure_local_launcher_directory(output)
    ci=ci or base.load_ci(source_root)
    data,styles,folds=base.fixture_bytes(ci)
    source=output/'unclosed-fence.md';base.write_new(source,data)
    summary={'passed':False,'runs':[],'receipt_sha256':base.digest(receipt)}
    for variant,original in (('release',release_dir),('profile',profile_dir)):
        base.verify_manifest(receipt,source_root,release_dir,profile_dir)
        directory=output/variant;base.copy_runtime(original,directory,manifest['runtime_sha256'][variant])
        result=run(variant,directory,source,ci,styles,folds,environment=os.environ.copy())
        summary['runs'].append(result)
        # A product-gate failure never becomes success, but an independently
        # owned profile may still run after confirmed cleanup of the first.
        if result.get('cleanup_unconfirmed') or result.get('retained_output_unconfirmed'):break
    summary['passed']=len(summary['runs'])==2 and all(r['passed'] for r in summary['runs'])
    return summary


# Numeric public contract: operation order is open/insert/backspace/undo;
# phase order is base.PHASES, hot order v_index/env_get/heap_new/v_call.
# snapshot vectors are cumulative, not per-revision maxima. Four operation
# delta vectors group BOTH Undo revisions into the final operation.
COUNTER_COUNT=10+4+8*3+8*4

def blank_public(code=3):
    return {'schema':1,'passed':0,'failure_code':code,'diagnostic_only':1,
        'product_acceptance_claimed':0,'gc_time_measured':0,'gc_root_snapshot_measured':0,
        'phase_cpu_measured':0,'phase_wall_measured':0,'compiler_pin_verified':0,
        'diagnostic_complete':0,'product_gate_failed':0,'diagnostic_late':0,
        'receipt_sha256':'0'*64,'header_sha256':'0'*64,
        'stage_deadline_seconds':30,'process_deadline_seconds':120,
        'runs':[{'executed':0,'passed':0,'diagnostic_complete':0,'product_gate_failed':0,'diagnostic_late':0,'cleanup_killed':0,'cleanup_unconfirmed':0,
                 'cpu_available':0,'user_100ns':0,'kernel_100ns':0,'scenario_wall_ms':0,
                 'stages':[{'observed':0,'product_gate_failed':0,'wall_ms':0,'probes':0,'undo_commands':0,
                            'response_available':0,'right_wall_ms':0,'left_wall_ms':0,'paint_wall_ms':0} for _ in OPERATIONS]} for _ in range(2)],
        'snapshot_count':0,'qpc_frequency':0,
        'operation_deltas':[[0]*COUNTER_COUNT for _ in OPERATIONS],
        'snapshots':[[0]*COUNTER_COUNT for _ in range(6)]}


def public_projection(summary,header_hash,ci):
    result=blank_public();result['receipt_sha256']=summary['receipt_sha256'];result['header_sha256']=header_hash
    result['compiler_pin_verified']=1
    require(type(summary['runs']) is list and len(summary['runs'])<=2)
    for index,run in enumerate(summary['runs']):
        require(run['variant']==('release','profile')[index])
        out=result['runs'][index]
        for key in ('executed','passed','cleanup_killed','cleanup_unconfirmed'):
            require(type(run.get(key)) is bool);out[key]=int(run[key])
        stages=run.get('stages',[]);require(type(stages) is list and len(stages)<=4)
        complete=run.get('diagnostic_complete',False);require(type(complete) is bool)
        out['diagnostic_complete']=int(complete)
        gates=run.get('gates',[]);require(len(gates)==len(stages))
        out['product_gate_failed']=int(any(g['product_gate_failed'] for g in gates))
        out['diagnostic_late']=int(complete and bool(out['product_gate_failed']))
        if complete:
            validate_stages(ci,stages,allow_late=True)
            require(all(st['wall_ms']<=30000 or g['product_gate_failed'] for st,g in zip(stages,gates)),'edit_late_gate_missing')
        require(not run['passed'] or (complete and not out['product_gate_failed']),'edit_success_claim')
        for stage,target,gate in zip(stages,out['stages'],gates):
            require(type(gate['product_gate_failed']) is bool)
            target['product_gate_failed']=int(gate['product_gate_failed'])
            # Failed stages expose ONLY already-recorded scalar facts. No path,
            # status, diagnostic exception, source text or unknown key is copied.
            if 'wall_ms' in stage:
                target['observed']=1;target['wall_ms']=finite(stage['wall_ms'])
                target['probes']=integer(stage.get('probes',0))
                target['undo_commands']=integer(stage.get('undo_commands',0),2)
            if complete and stage['responsiveness']:
                response=stage['responsiveness'];target['response_available']=1
                target['right_wall_ms']=response['navigation'][0]['wall_ms']
                target['left_wall_ms']=response['navigation'][1]['wall_ms']
                target['paint_wall_ms']=response['paint']['wall_ms']
        if 'process_cpu' in run:
            base.validate_process_cpu(run['process_cpu']);out['cpu_available']=1
            for key in ('user_100ns','kernel_100ns'):out[key]=run['process_cpu'][key]
        if 'scenario_wall_ms' in run:out['scenario_wall_ms']=finite(run['scenario_wall_ms'])
        if index==1 and complete:
            record=validate_profile(run['edit_profile'],stages);rows=record['records']
            result['snapshot_count']=len(rows);result['qpc_frequency']=rows[0]['qpc_frequency']
            result['phase_wall_measured']=1
            for n,row in enumerate(rows):result['snapshots'][n]=counters(row)
            result['snapshots'][5]=counters(record['final'])
            previous=[0]*COUNTER_COUNT
            for n,row in enumerate(rows[:3]+rows[-1:]):
                current=counters(row);result['operation_deltas'][n]=[b-a for a,b in zip(previous,current)];previous=current
    result['passed']=int(len(summary['runs'])==2 and all(r['passed'] for r in summary['runs']))
    require(bool(result['passed']) is summary['passed'])
    result['diagnostic_complete']=int(len(summary['runs'])==2 and all(r['diagnostic_complete'] for r in summary['runs']))
    result['product_gate_failed']=int(any(r['product_gate_failed'] for r in result['runs']))
    result['diagnostic_late']=int(bool(result['diagnostic_complete'] and result['product_gate_failed']))
    result['failure_code']=0 if result['passed'] else 3
    validate_public(result)
    return result


def validate_public(value):
    template=blank_public()
    def check(actual,model,key=''):
        if type(model) is dict:
            object_fields(actual,model)
            for name in model:check(actual[name],model[name],name)
        elif type(model) is list:
            require(type(actual) is list and len(actual)==len(model))
            for a,b in zip(actual,model):check(a,b,key)
        elif type(model) is str:require(type(actual) is str and re.fullmatch('[0-9a-f]{64}',actual) is not None)
        elif key.endswith('_ms'):finite(actual)
        else:integer(actual)
    check(value,template)
    for key in ('schema','diagnostic_only'):require(value[key]==1)
    for key in ('product_acceptance_claimed','gc_time_measured','gc_root_snapshot_measured','phase_cpu_measured'):require(value[key]==0)
    require(value['stage_deadline_seconds']==30 and value['process_deadline_seconds']==120)
    for key in ('passed','phase_wall_measured','compiler_pin_verified','diagnostic_complete','product_gate_failed','diagnostic_late'):integer(value[key],1)
    integer(value['failure_code'],5);integer(value['snapshot_count'],5)
    require(value['snapshot_count'] in (0,4,5))
    require(bool(value['phase_wall_measured'])==bool(value['snapshot_count']))
    require(not value['passed'] or (value['failure_code']==0 and value['phase_wall_measured']==1 and all(r['passed']==1 for r in value['runs'])))
    require(bool(value['passed'])==(value['failure_code']==0))
    require(not value['passed'] or (value['diagnostic_complete']==1 and value['product_gate_failed']==0))
    require(value['diagnostic_late']==int(bool(value['diagnostic_complete'] and value['product_gate_failed'])))
    require(value['diagnostic_complete']==int(all(run['diagnostic_complete']==1 for run in value['runs'])))
    require(value['product_gate_failed']==int(any(run['product_gate_failed']==1 for run in value['runs'])))
    require(value['passed']==int(all(run['passed']==1 for run in value['runs'])))
    require(value['phase_wall_measured']==value['runs'][1]['diagnostic_complete'])
    for run in value['runs']:
        for key in ('executed','passed','cleanup_killed','cleanup_unconfirmed','cpu_available','diagnostic_complete','product_gate_failed','diagnostic_late'):integer(run[key],1)
        require(not run['passed'] or (run['executed'] and run['diagnostic_complete'] and not run['product_gate_failed'] and not run['cleanup_killed'] and not run['cleanup_unconfirmed']))
        require(not run['diagnostic_complete'] or (run['executed'] and not run['cleanup_killed'] and not run['cleanup_unconfirmed']))
        require(run['diagnostic_late']==int(bool(run['diagnostic_complete'] and run['product_gate_failed'])))
        require(run['product_gate_failed']==int(any(stage['product_gate_failed']==1 for stage in run['stages'])))
        require(not run['diagnostic_complete'] or all(stage['observed']==1 for stage in run['stages']))
        for stage in run['stages']:
            for key in ('observed','response_available','product_gate_failed'):integer(stage[key],1)
            integer(stage['undo_commands'],2)
            require(stage['wall_ms']<=30000 or stage['product_gate_failed']==1)
            require(not stage['response_available'] or (stage['observed'] and run['diagnostic_complete']))
    if value['snapshot_count']:
        require(value['qpc_frequency']>0)
        count=value['snapshot_count'];previous=[0]*COUNTER_COUNT
        for index,vector in enumerate(value['snapshots'][:3]+[value['snapshots'][count-1]]):
            require(all(b>=a for a,b in zip(previous,vector)))
            require(value['operation_deltas'][index]==[b-a for a,b in zip(previous,vector)])
            previous=vector
        require(all(b>=a for a,b in zip(previous,value['snapshots'][5])))
        if count==4:require(not any(value['snapshots'][4]))
    else:
        require(value['qpc_frequency']==0 and not any(n for row in value['snapshots']+value['operation_deltas'] for n in row))
    data=(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
    require(len(data)<=PUBLIC_LIMIT)
    return data


def publish_public(evidence,value):
    """Flush a complete JSON file, then atomically publish without replacement.

    Windows rename refuses an existing destination. POSIX rename overwrites, so
    use an atomic no-replace hard-link installation there and unlink the staging
    name afterward. Both names are on the same filesystem. A failed write/flush
    never creates the public .json. Staging files are never upload candidates.
    """
    from run_markdown_owned_profile import plain
    data=validate_public(value)
    evidence=base.checked_path(evidence,directory=True).resolve(strict=True)
    require(evidence.is_dir())
    final=evidence/'markdown-edit-profile.json'
    temporary=None
    installed=False
    try:
        fd,name=tempfile.mkstemp(prefix='.markdown-edit-profile-',suffix='.tmp',dir=evidence)
        temporary=Path(name)
        with os.fdopen(fd,'wb') as stream:
            require(stream.write(data) == len(data))
            stream.flush()
            os.fsync(stream.fileno())
            identity=os.fstat(stream.fileno())
        def verify(path,links):
            plain(path)
            info=path.lstat()
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == links and
                    (info.st_dev,info.st_ino,info.st_size) ==
                    (identity.st_dev,identity.st_ino,len(data)))
            with os.fdopen(os.open(path,os.O_RDONLY|getattr(os,'O_BINARY',0)|getattr(os,'O_NOFOLLOW',0)),'rb') as stream:
                opened=os.fstat(stream.fileno())
                require((opened.st_dev,opened.st_ino) == (identity.st_dev,identity.st_ino))
                require(stream.read(PUBLIC_LIMIT+1) == data)
        base.checked_path(evidence,directory=True)
        verify(temporary,1)
        if os.name == 'nt':
            os.rename(temporary,final)
        else:
            os.link(temporary,final,follow_symlinks=False)
        installed=True
        verify(final,1 if os.name == 'nt' else 2)
    except BaseException:
        if installed:
            # Only a destination installed by this call is eligible for cleanup.
            # A stale/racing pre-existing destination is never removed.
            info=final.lstat()
            if (info.st_dev,info.st_ino) == (identity.st_dev,identity.st_ino):
                final.unlink()
        raise
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass  # No partial .json; an unpublishable .tmp stays private.


def main(argv=None):
    import argparse,contextlib,tempfile
    import run_markdown_owned_profile as owned
    parser=owned.PublicArgumentParser(prog='run_markdown_edit_profile.py',description=__doc__)
    for name in ('ru-root','binary-dir','evidence-dir','cc','windres'):parser.add_argument('--'+name,type=Path,required=True)
    public=blank_public(2);evidence=None
    try:
        args=parser.parse_args(argv);evidence=base.checked_path(args.evidence_dir,directory=True)
        if sys.platform!='win32':public=blank_public(1)
        else:
            private=Path(tempfile.mkdtemp(prefix='ru-markdown-edit-',dir=owned.ROOT/'build'))
            with (private/'preparation.log').open('xb') as stream:
                sink=owned.PrivateOutput(stream)
                with contextlib.redirect_stdout(sink),contextlib.redirect_stderr(sink):
                    release,profile,receipt,_=owned.prepare(args.ru_root,args.binary_dir,args.cc,args.windres,private,edit_profile=True)
                    public=blank_public(3)
                    summary=run_pair(receipt,owned.ROOT,release,profile,private/'runs')
                    public=blank_public(4)
                    public=public_projection(summary,base.digest(owned.ROOT/'native/markdown_edit_profile.h'),base.load_ci(owned.ROOT))
    except SystemExit as exc:
        if exc.code==0:return 0
    except Exception:pass  # Never echo private paths, source or raw exception text.
    try:publish_public(evidence,public)
    except Exception:
        print('MARKDOWN_EDIT_PROFILE_DIAGNOSTIC_COMPLETE=0');print('MARKDOWN_EDIT_PROFILE_FAILURE_CODE=5');return 1
    print('MARKDOWN_EDIT_PROFILE_DIAGNOSTIC_COMPLETE='+str(public['diagnostic_complete']))
    print('MARKDOWN_EDIT_PROFILE_PRODUCT_GATE_FAILED='+str(public['product_gate_failed']))
    if not public['passed']:print('MARKDOWN_EDIT_PROFILE_FAILURE_CODE='+str(public['failure_code']))
    return 0 if public['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
