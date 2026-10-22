"""Stock NPP plain vs official preinstalled Markdown UDL, no folding claim.
Fresh owned processes, same fixture/configuration, only selected language differs.
Text time is first observed length/dirty/context; ready adds sampled head/tail
styles, UDL endstyled, native response and exact language/menu/buffer proof.
No forced colourise, renderer, plugins, warmup, or Ru binary construction.
"""
import argparse,ctypes,hashlib,json,os,subprocess,sys,threading,time
from ctypes import wintypes
from pathlib import Path
import xml.etree.ElementTree as ET
import acquire_npp as acquire
import build_baseline as b
import feasibility as f
import npp_udl_result as public

UDL_PATH='userDefineLangs/markdown._preinstalled.udl.xml'
UDL_NAME='Markdown (preinstalled)'
UDL_CANONICAL='b5564310454e1c1a71127836ecc8ad7671c5ecaf5e024202d33e21c79b5107dc'
NPP_SOURCE='dd40fe45598791e9aa38f3aeb200e10fb3d6338a'
PREP=0


def diagnostics(exc,stage):
    stage,kind,origin,line=f.failure_diagnostics(exc,stage)
    tb=exc.__traceback__
    while tb:
        if Path(tb.tb_frame.f_code.co_filename).name in ('npp_udl_compare.py','npp_udl_result.py'):
            origin=8 if Path(tb.tb_frame.f_code.co_filename).name=='npp_udl_compare.py' else 9
            line=tb.tb_lineno if type(tb.tb_lineno) is int and 0<tb.tb_lineno<=10000 else 0
        tb=tb.tb_next
    return stage,kind,origin,line


def official_udl(path):
    path=b.plain(path);b.need(path.stat().st_size<=16384)
    data=path.read_bytes();text=data.decode('utf-8')
    b.need(hashlib.sha256(text.replace('\r\n','\n').encode()).hexdigest()==UDL_CANONICAL)
    root=ET.fromstring(data);b.need(root.tag=='NotepadPlus' and len(root)==1)
    lang=root[0];b.need(lang.tag=='UserLang' and lang.attrib=={'name':UDL_NAME,'ext':'md markdown','udlVersion':'2.1'})
    folding=[x for x in lang.findall('KeywordLists/Keywords') if x.attrib.get('name','').startswith('Folders in ')]
    b.need(len(folding)==9 and all(not (x.text or '').strip() for x in folding))
    b.need(lang.find('Settings/Global').attrib['allowFoldOfComments']=='no')
    return data


def settings_unchanged(settings,udl):
    # Owned writable settings outputs are never uploaded. The sole UDL stays exact.
    allowed={'config.xml','session.xml','langs.xml','stylers.xml','shortcuts.xml','contextMenu.xml',UDL_PATH}
    for p in settings.rglob('*'):
        relative=p.relative_to(settings).as_posix()
        if p.is_dir():
            b.plain(p,directory=True);b.need(relative=='userDefineLangs')
        else:
            b.plain(p);b.need(relative in allowed and p.stat().st_size<=10485760)
    b.need(official_udl(settings/UDL_PATH)==udl)


def configure_settings(settings,udl):
    settings.mkdir();target=settings/UDL_PATH;target.parent.mkdir()
    with target.open('xb') as out:out.write(udl)
    b.need(b.sha(b.plain(target))==hashlib.sha256(udl).hexdigest())
    return target


class NppAPI:
    def __init__(self,ci,process,deadline):
        self.base=f.owned_api(ci,process,deadline);self.process=process;self.deadline=deadline
        self.user=self.base.user;self.buffer_id=None;self.menu_cache=None
        specs={'GetMenu':([wintypes.HWND],wintypes.HMENU),'GetSubMenu':([wintypes.HMENU,ctypes.c_int],wintypes.HMENU),
               'GetMenuItemCount':([wintypes.HMENU],ctypes.c_int),'GetMenuItemID':([wintypes.HMENU,ctypes.c_int],wintypes.UINT),
               'GetMenuStringW':([wintypes.HMENU,wintypes.UINT,wintypes.LPWSTR,ctypes.c_int,wintypes.UINT],ctypes.c_int),
               'GetMenuState':([wintypes.HMENU,wintypes.UINT,wintypes.UINT],wintypes.UINT)}
        for name,(args,result) in specs.items():
            method=getattr(self.user,name);method.argtypes=args;method.restype=result
    def __getattr__(self,name):return getattr(self.base,name)
    def menu(self,hwnd,full=False):
        self.base.verify_owned_handles(self.process.pid,hwnd);self.deadline.remaining()
        root=self.user.GetMenu(hwnd)
        if not root:raise RuntimeError('missing owned menu')
        cache=getattr(self,'menu_cache',None)
        if cache is not None and not full:
            if root!=cache['root']:raise RuntimeError('owned menu root changed')
            states=[]
            for path,expected_menu,identifier in cache['items']:
                menu=root
                for index,expected_child in path:
                    menu=self.user.GetSubMenu(menu,index)
                    if not menu or menu!=expected_child:raise RuntimeError('owned menu path changed')
                if menu!=expected_menu or self.user.GetMenuItemID(menu,cache['positions'][identifier])!=identifier:
                    raise RuntimeError('owned menu item changed')
                state=self.user.GetMenuState(menu,identifier,0)
                if state==0xffffffff:raise RuntimeError('menu state unavailable')
                if identifier!=46016:
                    text=ctypes.create_unicode_buffer(513)
                    copied=self.user.GetMenuStringW(menu,identifier,text,len(text),0)
                    if not 0<=copied<512 or text.value!=UDL_NAME:raise RuntimeError('official UDL menu identity changed')
                states.append(int(bool(state&8)))
            self.base.verify_owned_handles(self.process.pid,hwnd);self.deadline.remaining()
            return cache['items'][0][2],states[0],states[1]
        found=[];plain=[];seen=set();count=0
        def walk(menu,depth,path):
            nonlocal count
            if depth>8 or menu in seen:raise RuntimeError('invalid menu graph')
            seen.add(menu);n=self.user.GetMenuItemCount(menu)
            if not 0<=n<=256:raise RuntimeError('menu bound')
            for i in range(n):
                count+=1
                if count>1024:raise RuntimeError('menu bound')
                self.deadline.remaining()
                child=self.user.GetSubMenu(menu,i)
                if child:walk(child,depth+1,path+((i,child),));continue
                identifier=self.user.GetMenuItemID(menu,i)
                if identifier==46016 or 46181<=identifier<=46210:
                    state=self.user.GetMenuState(menu,i,0x400)
                    if state==0xffffffff:raise RuntimeError('menu state unavailable')
                    if identifier==46016:plain.append((identifier,int(bool(state&8)),menu,path,i))
                    else:
                        text=ctypes.create_unicode_buffer(513)
                        copied=self.user.GetMenuStringW(menu,i,text,len(text),0x400)
                        if not 0<=copied<512:raise RuntimeError('menu text bound')
                        if text.value==UDL_NAME:found.append((identifier,int(bool(state&8)),menu,path,i))
        walk(root,0,())
        self.base.verify_owned_handles(self.process.pid,hwnd);self.deadline.remaining()
        if len(found)!=1 or len(plain)!=1:raise RuntimeError('official UDL menu identity absent or ambiguous')
        entries=(found[0],plain[0])
        self.menu_cache={'root':root,'items':[(x[3],x[2],x[0]) for x in entries],'positions':{x[0]:x[4] for x in entries}}
        return found[0][0],found[0][1],plain[0][1]
    def mode_proof(self,hwnd,editor,mode,full_menu=False):
        current=self.scalar(hwnd,2084)
        if not current:raise RuntimeError('no current owned buffer')
        if self.buffer_id is None:self.buffer_id=current
        language=self.scalar(hwnd,2088,current);lexer=self.scalar(editor,4002)
        count=self.scalar(hwnd,2031,0,0)
        identifier,udl_checked,plain_checked=self.menu(hwnd,full=full_menu)
        proof=dict(language_type=language,lexer=lexer,udl_menu_id=identifier,udl_menu_checked=udl_checked,
                   plain_menu_checked=plain_checked,file_count=count,same_buffer=int(current==self.buffer_id))
        if not (current==self.buffer_id and count==1 and language==(15 if mode else 0) and
                lexer in ((152,) if mode else (0,1)) and udl_checked==mode and plain_checked==1-mode):
            raise RuntimeError('actual selected mode mismatch')
        return proof


def stage(api,hwnd,editor,deadline,mode,operation,result,clock=time.perf_counter,sleep=time.sleep):
    if operation!='open':deadline.next_stage()
    started=deadline.started if operation=='open' else clock()
    result.update(operation=('open','insert','backspace','undo').index(operation),completed=0,censored=0,
                  first_text_upper_ms=None,first_common_upper_ms=None,savepoint_text_upper_ms=None,wall_ms=None,
                  undo_commands=0,undo_acknowledged=0,poll_count=0,dispatches=[],rounds=[],last=None,mode_proof=None)
    def dispatch(action):
        event=dict(acknowledged=0,delivery_completion_unknown=1,upper_ms=0);result['dispatches'].append(event);now=clock()
        try:action();event.update(acknowledged=1,delivery_completion_unknown=0)
        finally:event['upper_ms']=(clock()-now)*1000
    if operation=='insert':dispatch(lambda:(api.scalar(editor,2025,8),api.scalar(editor,0x102,120)))
    elif operation=='backspace':dispatch(lambda:(api.scalar(editor,2025,9),api.scalar(editor,0x100,8),api.scalar(editor,0x101,8)))
    elif operation=='undo':
        result['undo_commands']=1;dispatch(lambda:api.command(hwnd,42003));result['undo_acknowledged']=1
    tail=False;round_context=None;round_signature=None
    while True:
        deadline.remaining();result['poll_count']+=1
        snap={'length':api.scalar(editor,2006),'dirty':int(bool(api.scalar(editor,2159)))}
        if round_context is not None and round_signature!=(snap['length'],snap['dirty']):round_context=None
        fresh_context=round_context is None
        snap['context']=[api.scalar(editor,2007,i)&255 for i in range(6,10)] if fresh_context else round_context
        observed={k:v for k,v in snap.items() if k!='context'}
        if fresh_context:observed['context_sha256']=hashlib.sha256(bytes(snap['context'])).hexdigest()
        result['last']=observed
        match=f.text_matches(snap,operation,result['undo_commands'])
        if match and round_context is None:round_context=list(snap['context']);round_signature=(snap['length'],snap['dirty'])
        if match and result['first_text_upper_ms'] is None:result['first_text_upper_ms']=(clock()-started)*1000
        if match and operation=='undo' and not snap['dirty'] and result['savepoint_text_upper_ms'] is None:result['savepoint_text_upper_ms']=(clock()-started)*1000
        if match and not tail:api.scalar(editor,2025,snap['length']);api.scalar(editor,2169);tail=True
        if match and tail:
            positions=list(range(8))+list(range(snap['length']-8,snap['length']))
            lexer=api.scalar(editor,4002)
            if lexer not in ((152,) if mode else (0,1)):raise RuntimeError('unexpected actual lexer')
            endstyled=api.scalar(editor,2028)
            observed.update(lexer=lexer,endstyled=endstyled)
            ready=not mode or endstyled==snap['length']
            if ready:
                observed.update(styles=[api.scalar(editor,2010,i) for i in positions],fold_header=int(bool(api.scalar(editor,2223,0)&0x2000)))
                ready=observed['styles']==[0]*16 and observed['fold_header']==0
            if ready:
                before=api.mode_proof(hwnd,editor,mode)
                if api.scalar(editor,2006)!=snap['length'] or int(bool(api.scalar(editor,2159)))!=snap['dirty']:raise RuntimeError('unstable final document')
                if [api.scalar(editor,2010,i) for i in positions]!=[0]*16:raise RuntimeError('unstable final styles')
                if mode and api.scalar(editor,2028)!=snap['length']:raise RuntimeError('unstable endstyled')
                final_context=[api.scalar(editor,2007,i)&255 for i in range(6,10)]
                if final_context!=snap['context']:raise RuntimeError('unstable final context')
                observed['context_sha256']=hashlib.sha256(bytes(final_context)).hexdigest()
                api.scalar(hwnd,0);api.scalar(editor,0)
                result['mode_proof']=api.mode_proof(hwnd,editor,mode)
                if result['mode_proof']!=before:raise RuntimeError('unstable final mode')
                if result['first_common_upper_ms'] is None:result['first_common_upper_ms']=(clock()-started)*1000
                result['rounds'].append(dict(command=result['undo_commands'],dirty=snap['dirty'],length=snap['length'],upper_ms=(clock()-started)*1000))
                if operation=='undo' and snap['dirty']:
                    if result['undo_commands']>=2 or not api.scalar(editor,2174):raise RuntimeError('natural undo groups not clean')
                    result['undo_commands']+=1;dispatch(lambda:api.command(hwnd,42003));result['undo_acknowledged']+=1;tail=False;round_context=None;round_signature=None
                else:
                    deadline.remaining();result.update(completed=1,wall_ms=(clock()-started)*1000);return
        sleep(min(f.POLL,deadline.remaining()))


def run_one(ci,mode,exe,source,scratch,inventory,udl):
    settings=scratch/'settings';udl_target=configure_settings(settings,udl)
    deadline=f.Deadline();process=None;guard=None
    result=dict(mode=mode,executed=0,passed=0,pid=0,exit_code=-1,cleanup_unconfirmed=0,runtime_unchanged=0,
                fixture_unchanged=0,provenance_unchanged=0,udl_unchanged=0,error_kind=0,elapsed_upper_ms=0,stages=[])
    try:
        f.closed_manifest(exe.parent,inventory)
        argv=[str(exe),'-multiInst','-noPlugin','-nosession','-settingsDir='+str(settings),
              '-udl='+UDL_NAME if mode else '-lnormal',str(source)]
        process=subprocess.Popen(argv,cwd=exe.parent,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,close_fds=True)
        result.update(executed=1,pid=process.pid)
        def watchdog():
            try:
                if process.poll() is None:process.kill()
            except OSError:pass
        guard=threading.Timer(max(0,deadline.hard-time.perf_counter()),watchdog)
        guard.daemon=True;guard.start();api=NppAPI(ci,process,deadline)
        while True:
            deadline.remaining();windows=api.no_dialog(process.pid)
            main=[h for h,c,visible in windows if c=='Notepad++' and visible]
            if len(main)>1:raise RuntimeError('ambiguous owned main')
            if main:
                hwnd=main[0]
                try:editor=api.editor(hwnd)
                except RuntimeError:time.sleep(f.POLL);continue
                if api.scalar(editor,2006)==f.SIZE:break
            time.sleep(f.POLL)
        api.mode_proof(hwnd,editor,mode)
        for operation in ('open','insert','backspace','undo'):
            row={};result['stages'].append(row)
            try:stage(api,hwnd,editor,deadline,mode,operation,row)
            except TimeoutError:row['censored']=1;raise
        api.mode_proof(hwnd,editor,mode,full_menu=True)
        result['passed']=1
    except Exception as exc:
        _,kind,origin,line=diagnostics(exc,10);result['error_kind']=kind
        print(f'NPP_UDL_MODE={mode} ERROR_KIND={kind} SOURCE_ID={origin} LINE={line}',file=sys.stderr)
    finally:
        if guard:guard.cancel()
        if process:
            try:
                cleaned=f.cleanup_owned(process,deadline.hard)
                result['exit_code']=cleaned['exit_code'] if cleaned['exit_code'] is not None else -1
                result['cleanup_unconfirmed']=int(cleaned['cleanup_unconfirmed'])
            except OSError:result['cleanup_unconfirmed']=1
        result['elapsed_upper_ms']=(time.perf_counter()-deadline.started)*1000
        try:
            if result['cleanup_unconfirmed']:raise RuntimeError('cleanup uncertain')
            f.closed_manifest(exe.parent,inventory);result['runtime_unchanged']=1
            result['fixture_unchanged']=int(b.sha(b.plain(source))==hashlib.sha256(b'a'*f.SIZE).hexdigest())
            settings_unchanged(settings,udl);result['udl_unchanged']=1
        except (OSError,ValueError,RuntimeError):pass
        if result['cleanup_unconfirmed'] or not all(result[k] for k in ('runtime_unchanged','fixture_unchanged','udl_unchanged')):result['passed']=0
    return result


def main():
    global PREP
    ap=argparse.ArgumentParser()
    for name in ('source-root','npp-dir','npp-receipt','output-root'):ap.add_argument('--'+name,type=Path,required=True)
    a=ap.parse_args();PREP=1;b.host_guard()
    a.source_root=b.plain(a.source_root,directory=True);a.npp_dir=b.plain(a.npp_dir,directory=True);a.npp_receipt=b.plain(a.npp_receipt)
    a.output_root=Path(os.path.abspath(a.output_root));b.plain(a.output_root.parent,directory=True);b.need(not a.output_root.exists())
    PREP=2;source_seal=b.checkout(a.source_root,b.BASELINE);receipt=b.read(a.npp_receipt)
    b.need(set(receipt)=={'archive_sha256','executable_sha256','file_count','executed','files'})
    b.need(type(receipt['files']) is dict and type(receipt['file_count']) is int)
    b.need(receipt['executable_sha256']=='c52c9ed2ec6d0b5b3f243b29f2124f98db56b6ba92bb42a9af2665709464b3cf')
    for value in receipt['files'].values():public.h(value)
    b.need(receipt['archive_sha256']==acquire.PINS['npp.8.9.8.1.portable.x64.zip'][1] and receipt['executed'] is False)
    receipt_sha=b.sha(a.npp_receipt);inventory=receipt['files']
    b.need(len(inventory)==receipt['file_count'] and receipt['executable_sha256']==inventory['notepad++.exe'])
    for marker in ('doLocalConf.xml','disableNppAutoUpdate.xml'):b.need(marker in inventory)
    f.closed_manifest(a.npp_dir,inventory);udl=official_udl(b.under(a.npp_dir,UDL_PATH))
    harness_files=('npp_udl_compare.py','npp_udl_result.py','feasibility.py','build_baseline.py','public_result.py','acquire_npp.py','release-lock.json')
    harness={name:b.sha(b.plain(Path(__file__).with_name(name))) for name in harness_files}
    def revalidate():
        b.need(b.checkout(a.source_root,b.BASELINE)==source_seal and b.sha(a.npp_receipt)==receipt_sha)
        f.closed_manifest(a.npp_dir,inventory)
        b.need(official_udl(b.under(a.npp_dir,UDL_PATH))==udl)
        b.need({name:b.sha(b.plain(Path(__file__).with_name(name))) for name in harness_files}==harness)
    PREP=3;ci=f.load_ci(a.source_root);NppAPI(ci,None,f.Deadline())  # Bind actual ctypes APIs; no process/window enumeration or GUI launch.
    a.output_root.mkdir();report=dict(schema=3,observer_revision=3,feasibility_only=1,text_times_are_observable_upper_bounds=1,folding_completion_measured=0,npp_version=[8,9,8,1],helper_commit=b.BASELINE,official_source_commit=NPP_SOURCE,
      archive_sha256=receipt['archive_sha256'],udl_sha256=hashlib.sha256(udl).hexdigest(),udl_canonical_sha256=UDL_CANONICAL,
      executable_sha256=receipt['executable_sha256'],fixture_sha256=hashlib.sha256(b'a'*f.SIZE).hexdigest(),harness_sha256=b.digest(harness),receipt_sha256=receipt_sha,
      host=dict(windows_version=list(sys.getwindowsversion()[:3]),cpu_count=os.cpu_count() or 0,cpu_identifier_sha256=hashlib.sha256(os.environ.get('PROCESSOR_IDENTIFIER','').encode()).hexdigest(),runner_image_sha256=hashlib.sha256((os.environ.get('ImageOS','')+'|'+os.environ.get('ImageVersion','')).encode()).hexdigest()),
      clock_resolution_seconds=time.get_clock_info('perf_counter').resolution,requested_poll_seconds=f.POLL,stages_seconds=f.STAGE,process_seconds=f.HARD,official_fold_rules=9,official_nonempty_fold_rules=0,runs=[])
    PREP=4
    for mode in (0,1):
        revalidate();scratch=a.output_root/str(mode);scratch.mkdir();source=scratch/'fixture.txt';source.write_bytes(b'a'*f.SIZE)
        runtime=scratch/'runtime';f.copy_runtime(a.npp_dir,runtime,inventory)
        result=run_one(ci,mode,runtime/'notepad++.exe',source,scratch,inventory,udl)
        try:revalidate();result['provenance_unchanged']=1
        except (ValueError,OSError,subprocess.SubprocessError):result['passed']=0
        report['runs'].append(result)
        (a.output_root/'npp-udl-result.json').write_text(json.dumps(public.validate(report),indent=2,allow_nan=False)+'\n')
        if not result['passed']:break
    return 0 if len(report['runs'])==2 and all(r['passed'] for r in report['runs']) else 1

if __name__=='__main__':
    try:code=main()
    except Exception as exc:
        _,kind,origin,line=diagnostics(exc,PREP)
        print(f'NPP_UDL_PREP={PREP} ERROR_KIND={kind} SOURCE_ID={origin} LINE={line}',file=sys.stderr);code=1
    raise SystemExit(code)
