"""Same-job diagnostic: unchanged Ru baseline/menu 507 vs exact official NPP UDL.
No product patch, forced colourise, forced undo grouping, or open-speed claim.
"""
import argparse, hashlib, json, os, subprocess, sys, threading, time
from pathlib import Path
import build_baseline as b
import feasibility as f
import npp_udl_compare as n
import seal_receipt

ORDER=(0,1,2)  # Ru off, NPP UDL, identical Ru on; one fresh process per fixture/arm.
TEXT=b'a'*1_000_000
MARKDOWN=(b'aaaaaaaaaaaaaaaa\n\n# Heading\n\nordinary **strong** and `code` text.\n\n## Section\n\n- item\n\n```python\nprint(1)\n```\n\n')*128


def diagnostics(exc):
    _,kind,origin,line=n.diagnostics(exc,10)
    tb=exc.__traceback__
    while tb:
        name=Path(tb.tb_frame.f_code.co_filename).name
        if name in ('no_folds_compare.py','no_folds_result.py'):
            origin=10 if name=='no_folds_compare.py' else 11
            line=tb.tb_lineno if 0<tb.tb_lineno<=10000 else 0
        tb=tb.tb_next
    return kind,origin,line


def fixture(kind):
    data=(TEXT,MARKDOWN)[kind]
    # Independent product-specific style IDs; never claim semantic equivalence.
    probes=list(range(8))+list(range(len(data)-8,len(data)))
    if kind:probes += [data.index(b'# Heading'),data.index(b'strong'),data.index(b'code')]
    return data,probes


def text_match(api,editor,data,operation,undo):
    length=api.scalar(editor,2006);dirty=int(bool(api.scalar(editor,2159)))
    inserted=operation=='insert' or (operation=='undo' and undo==1 and dirty)
    expected_length=len(data)+int(inserted)
    expected_context=data[6:8]+b'x'+data[8:9] if inserted else data[6:10]
    expected_dirty=int(operation in ('insert','backspace') or (operation=='undo' and dirty))
    context=bytes(api.scalar(editor,2007,i)&255 for i in range(6,10))
    return length==expected_length and dirty==expected_dirty and context==expected_context,length,dirty,inserted


def ru_proof(ci,api,hwnd,editor,arm,initial=False):
    api.verify_fixture_title(hwnd)
    b.need(api.scalar(editor,2357)==api.comparison_document)
    status=api.markdown_status(api.control(hwnd,11))
    state=f.markdown_state(ci,status)
    b.need(state[0]==1 and state[3:]==(0,0))
    if state!=(1,0,int(arm==0),0,0):
        if initial:return False
        b.need(False)
    b.need(api.scalar(editor,4002)==98)
    marker=ci.parse_markdown_diagnostic(status)
    if arm==0:
        b.need(api.scalar(editor,2664)==0)  # SCI_GETAUTOMATICFOLD
        if initial:
            if marker is None or marker['id']<=getattr(api,'before_disable_identity',0):return False
            if marker['phase']!=4 or marker['pending']!=0:return False
            b.need(marker['feed']==0 and marker['published']==0)
    else:
        b.need(marker is not None and f.marker_ready(api,api.scalar(editor,2006)))
    return True


def styles_ready(api,editor,arm,data,probes,inserted,reference=None):
    length=len(data)+int(inserted)
    if api.scalar(editor,2028)!=length:return None
    positions=[p+int(inserted and p>=8) for p in probes]
    styles=[api.scalar(editor,2010,p) for p in positions]
    if data is TEXT:b.need(styles==[0]*len(probes))
    else:
        # Heading, strong and code must actually have non-default styles.
        b.need(all(s!=0 for s in styles[-3:]))
    if reference is not None:b.need(styles==reference)
    return styles


def stage(ci,api,hwnd,editor,deadline,arm,data,probes,op,row,reference=None):
    # Preparation shares original opening deadline; all edits retain 30s/120s.
    if op!='prepare':deadline.next_stage()
    started=time.perf_counter()
    row.update(operation=('prepare','insert','backspace','undo').index(op),completed=0,censored=0,rounds=[],dispatches=[])
    undo=0;round_start=started;text_time=None;style_time=None;tail=False
    def dispatch(action):
        event={'acknowledged':0,'delivery_completion_unknown':1,'upper_ms':0};row['dispatches'].append(event);t=time.perf_counter()
        try:action();event.update(acknowledged=1,delivery_completion_unknown=0)
        finally:event['upper_ms']=(time.perf_counter()-t)*1000
    if op=='insert':dispatch(lambda:(api.scalar(editor,2025,8),api.scalar(editor,0x102,120)))
    if op=='backspace':dispatch(lambda:(api.scalar(editor,2025,9),api.scalar(editor,0x100,8),api.scalar(editor,0x101,8)))
    if op=='undo':undo=1;dispatch(lambda:api.command(hwnd,42003 if arm==1 else 201))
    while True:
        deadline.remaining()
        match,length,dirty,inserted=text_match(api,editor,data,op,undo)
        if match and text_time is None:text_time=(time.perf_counter()-round_start)*1000
        if match and not tail:api.scalar(editor,2025,length);api.scalar(editor,2169);tail=True
        if match:
            styles=styles_ready(api,editor,arm,data,probes,inserted,reference)
            if styles is not None:
                if style_time is None:style_time=(time.perf_counter()-round_start)*1000
                ready=False
                if arm==1:api.mode_proof(hwnd,editor,1);ready=True
                elif arm==0:
                    ready=ru_proof(ci,api,hwnd,editor,arm,initial=op=='prepare')
                else:
                    if api.markdown_done(hwnd) and f.marker_ready(api,length):
                        ru_proof(ci,api,hwnd,editor,arm);ready=True
                if ready:
                    api.scalar(hwnd,0);api.scalar(editor,0)
                    b.need(text_match(api,editor,data,op,undo)==(match,length,dirty,inserted))
                    b.need(styles_ready(api,editor,arm,data,probes,inserted,reference)==styles)
                    if arm==1:api.mode_proof(hwnd,editor,1)
                    elif arm==0:b.need(ru_proof(ci,api,hwnd,editor,arm,initial=op=='prepare'))
                    else:api.accepted_markdown_marker=dict(api.last_markdown_marker)
                    row['rounds'].append(dict(command=undo,length=length,dirty=dirty,text_upper_ms=text_time,
                      style_upper_ms=style_time,ready_upper_ms=(time.perf_counter()-round_start)*1000,total_upper_ms=(time.perf_counter()-started)*1000,
                      endstyled=length,lexer=152 if arm==1 else 98,styles=styles))
                    if op=='undo' and dirty:
                        b.need(undo<2 and api.scalar(editor,2174));undo+=1
                        round_start=time.perf_counter();text_time=None;style_time=None;tail=False
                        dispatch(lambda:api.command(hwnd,42003 if arm==1 else 201))
                    else:deadline.remaining();row['completed']=1;return styles
        time.sleep(min(f.MARKDOWN_POLL if arm==2 else f.POLL,deadline.remaining()))


def run_one(ci,arm,kind,exe,source,scratch,inventory,udl):
    data,probes=fixture(kind);deadline=f.Deadline();process=None;guard=None;started_filetime=None
    result=dict(arm=arm,fixture=kind,passed=0,executed=0,cleanup_unconfirmed=0,runtime_unchanged=0,
                fixture_unchanged=0,provenance_unchanged=0,error_kind=0,stages=[])
    if arm==1:
        settings=scratch/'settings';n.configure_settings(settings,udl)
        argv=[str(exe),'-multiInst','-noPlugin','-nosession','-settingsDir='+str(settings),'-udl='+n.UDL_NAME,str(source)]
    else:argv=[str(exe),'--markdown-phase-diagnostics',str(source)]
    try:
        f.closed_manifest(exe.parent,inventory);started_filetime=f.filetime_now()
        process=subprocess.Popen(argv,cwd=exe.parent,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,close_fds=True)
        result['executed']=1
        def watchdog():
            try:
                if process.poll() is None:process.kill()
            except OSError:pass
        guard=threading.Timer(max(0,deadline.hard-time.perf_counter()),watchdog);guard.daemon=True;guard.start()
        api=n.NppAPI(ci,process,deadline) if arm==1 else f.owned_api(ci,process,deadline)
        api.expected_fixture_title=source.name+' · ru_notepad'
        while True:
            deadline.remaining();windows=api.no_dialog(process.pid)
            matches=[h for h,c,v in windows if v and c==('Notepad++' if arm==1 else ci.MAIN_CLASS)]
            b.need(len(matches)<=1)
            if matches:
                hwnd=matches[0]
                try:editor=api.editor(hwnd)
                except RuntimeError:time.sleep(f.POLL);continue
                if api.scalar(editor,2006)==len(data):
                    if arm==1:break
                    state=f.title_state(api.markdown_status(hwnd),source,ci.comparison_initial_titles)
                    b.need(state!=2)
                    if state==1:break
            time.sleep(min(f.POLL,deadline.remaining()))
        if arm!=1:api.comparison_document=api.scalar(editor,2357);b.need(api.comparison_document!=0)
        if arm==0:
            previous=ci.parse_markdown_diagnostic(api.markdown_status(api.control(hwnd,11)))
            api.before_disable_identity=previous['id'] if previous else 0
            api.command(hwnd,507)  # Existing product command, before edit timing.
        reference=None
        for op in ('prepare','insert','backspace','undo'):
            row={};result['stages'].append(row)
            try:observed=stage(ci,api,hwnd,editor,deadline,arm,data,probes,op,row,reference)
            except TimeoutError:row['censored']=1;raise
            if op=='prepare':reference=observed
        result['passed']=1
    except Exception as exc:
        kind_id,origin,line=diagnostics(exc);result['error_kind']=kind_id
        print(f'NO_FOLDS_ARM={arm} FIXTURE={kind} ERROR_KIND={kind_id} SOURCE_ID={origin} LINE={line}',file=sys.stderr)
    finally:
        if guard:guard.cancel()
        if process:
            try:result['cleanup_unconfirmed']=int(f.cleanup_owned(process,deadline.hard)['cleanup_unconfirmed'])
            except OSError:result['cleanup_unconfirmed']=1
        try:
            b.need(not result['cleanup_unconfirmed'])
            if arm==1:f.closed_manifest(exe.parent,inventory);n.settings_unchanged(settings,udl)
            else:f.post_runtime(exe.parent,inventory,'C',process.pid if process else None,started_filetime,f.filetime_now(),True)
            result['runtime_unchanged']=1
            result['fixture_unchanged']=int(b.sha(b.plain(source))==hashlib.sha256(data).hexdigest())
        except (ValueError,OSError,RuntimeError):result['passed']=0
        if not all(result[k] for k in ('runtime_unchanged','fixture_unchanged')):result['passed']=0
    return result


def main():
    import no_folds_result as public
    ap=argparse.ArgumentParser()
    for name in ('source-root','compiler','cc','ru-dir','npp-dir','npp-receipt','receipt','output-root'):ap.add_argument('--'+name,type=Path,required=True)
    a=ap.parse_args();b.host_guard()
    for key in ('source_root','compiler','ru_dir','npp_dir'):setattr(a,key,b.plain(getattr(a,key),directory=True))
    for key in ('npp_receipt','receipt'):setattr(a,key,b.plain(getattr(a,key)))
    a.cc=b.compiler_file(a.cc);a.output_root=Path(os.path.abspath(a.output_root));b.plain(a.output_root.parent,directory=True);b.need(not a.output_root.exists())
    receipt=b.read(a.receipt)
    harness_files=('no_folds_compare.py','no_folds_result.py','npp_udl_compare.py','npp_udl_result.py','feasibility.py','build_baseline.py','public_result.py','acquire_npp.py','seal_receipt.py','release-lock.json')
    harness={name:b.sha(b.plain(Path(__file__).with_name(name))) for name in harness_files}
    udl=n.official_udl(b.under(a.npp_dir,n.UDL_PATH))
    def revalidate():
        f.verify_receipt(receipt,a.ru_dir,a.npp_dir)
        b.need(seal_receipt.seal(a.source_root,a.compiler,a.cc,a.ru_dir,a.npp_dir,a.npp_receipt)==receipt)
        b.need(n.official_udl(b.under(a.npp_dir,n.UDL_PATH))==udl)
        b.need({name:b.sha(b.plain(Path(__file__).with_name(name))) for name in harness_files}==harness)
    revalidate();ci=f.load_ci(a.source_root);a.output_root.mkdir()
    report=dict(schema=4,observer_revision=5,baseline_commit=b.BASELINE,compiler_commit=b.COMPILER,
      stages_seconds=f.STAGE,process_seconds=f.HARD,poll_seconds=[f.POLL,f.POLL,f.MARKDOWN_POLL],order=list(ORDER),repetitions=1,opening_compared=0,
      disabled_marker_after_edits=0,style_semantic_equivalence=0,
      fixture_sha256=[hashlib.sha256(fixture(k)[0]).hexdigest() for k in (0,1)],
      harness_sha256=b.digest(harness),receipt_sha256=b.sha(a.receipt),runtime_sha256={'ru':receipt['runtime']['ru'],'npp':{'notepad++.exe':receipt['runtime']['npp']['notepad++.exe']}},
      udl_sha256=hashlib.sha256(udl).hexdigest(),
      host=dict(windows_version=list(sys.getwindowsversion()[:3]),cpu_count=os.cpu_count() or 0,
        cpu_identifier_sha256=hashlib.sha256(os.environ.get('PROCESSOR_IDENTIFIER','').encode()).hexdigest(),
        runner_image_sha256=hashlib.sha256((os.environ.get('ImageOS','')+'|'+os.environ.get('ImageVersion','')).encode()).hexdigest()),runs=[])
    for kind in (0,1):
        for arm in ORDER:
            revalidate();scratch=a.output_root/f'{kind}-{arm}';scratch.mkdir();data,_=fixture(kind)
            source=scratch/'fixture.md';source.write_bytes(data)
            inventory=receipt['npp_all_files_sha256'] if arm==1 else receipt['runtime']['ru']
            runtime=scratch/'runtime';f.copy_runtime(a.npp_dir if arm==1 else a.ru_dir,runtime,inventory)
            result=run_one(ci,arm,kind,runtime/('notepad++.exe' if arm==1 else 'ru_notepad.exe'),source,scratch,inventory,udl)
            try:revalidate();result['provenance_unchanged']=1
            except (ValueError,OSError,subprocess.SubprocessError):result['passed']=0
            report['runs'].append(result)
            (a.output_root/'no-folds-result.json').write_text(json.dumps(public.validate(report),indent=2,allow_nan=False)+'\n')
            if not result['passed']:return 1
    return 0

if __name__=='__main__':
    try:code=main()
    except Exception as exc:
        kind,origin,line=diagnostics(exc)
        print(f'NO_FOLDS_PREP_ERROR={kind} SOURCE_ID={origin} LINE={line}',file=sys.stderr);code=1
    raise SystemExit(code)
