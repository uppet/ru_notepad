#!/usr/bin/env python3
"""Actual same-binary two-process and native tab-menu Windows acceptance.
Recovered source after workspace loss; requires fresh review and actual CI.
Only random synthetic HKCU namespaces and freshly created fixture documents.
"""
from __future__ import annotations
import ctypes
from ctypes import wintypes
from contextlib import contextmanager
import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid
from unittest.mock import patch
import windows_ci as ci

CHECKS=('unicode_relative_multi_path_handoff','secondary_ack_normal_exit','no_secondary_visible_window',
        'no_owner_extra_blank_tab','duplicate_activates_existing','persistent_disable_creates_window',
        'persistent_reenable_handoff','explicit_multi_instance_creates_window','clicked_tab_target',
        'menu_current','menu_others','menu_left','menu_right','menu_saved','menu_all',
        'dirty_batch_cancel_preserves_all','save_as_cancel_preserves_all',
        'startup_race_single_owner', 'startup_race_all_paths_once',
          'timeout_uncertain_no_automatic_open', 'timeout_pending_explicit_open',
          'synthetic_sources_unchanged', 'isolated_registry_cleaned')
PHASES=('handoff','menu-current','menu-others','menu-left','menu-right',
        'menu-saved', 'menu-all', 'dirty-cancel', 'startup-race', 'timeout-uncertain')
CHILDREN=('multi-path','duplicate','disabled','reenabled','explicit-multi')


def validate_result(record,hashes):
    fields={'schema','name','passed','executed','cleanup_killed','exit_code','checks','phases',
            'fixture_binary_sha256','secondary_processes'}
    if not isinstance(record,dict) or set(record)!=fields:raise ValueError('Instance/tab schema differs')
    if record['schema']!='ru-notepad-instance-tabs-gui-v1' or record['name']!='main-gui-instance-tabs':raise ValueError('Instance/tab identity differs')
    if record['passed'] is not True or record['executed'] is not True or record['cleanup_killed'] is not False:raise ValueError('Instance/tab GUI did not pass')
    if type(record['exit_code']) is not int or record['exit_code']!=0 or record['fixture_binary_sha256']!=hashes:raise ValueError('Instance/tab runtime or exit differs')
    if not isinstance(record['checks'],dict) or set(record['checks'])!=set(CHECKS) or any(v is not True for v in record['checks'].values()):raise ValueError('Instance/tab check inventory differs')
    if not isinstance(record['phases'],list) or len(record['phases'])!=len(PHASES):raise ValueError('Instance/tab phases missing')
    for name,item in zip(PHASES,record['phases']):
        if not isinstance(item,dict) or item.get('phase')!=name or item.get('passed') is not True or item.get('executed') is not True or item.get('cleanup_killed') is not False or type(item.get('exit_code')) is not int or item['exit_code']!=0 or item.get('fixture_binary_sha256')!=hashes:
            raise ValueError('Single-instance/tab phase lacks normal same-binary lifecycle')
        if name in ('startup-race','timeout-uncertain'):
            participants=item.get('participants')
            if not isinstance(participants,list) or len(participants)!=2 or any(not isinstance(x,dict) or set(x)!={'exit_code','cleanup_killed'} or type(x.get('exit_code')) is not int or x['exit_code']!=0 or x.get('cleanup_killed') is not False for x in participants):
                raise ValueError('Controlled two-process phase lacks normal participant exits')
        if name=='timeout-uncertain':
            if item.get('controlled_ui_suspend') is not True or type(item.get('owner_delivery_count')) is not int or item['owner_delivery_count'] not in (0,1):
                raise ValueError('Controlled timeout evidence is incomplete')
    rows=record['secondary_processes']
    if not isinstance(rows,list) or len(rows)!=len(CHILDREN):raise ValueError('Secondary evidence missing')
    for row,purpose in zip(rows,CHILDREN):
        if not isinstance(row,dict) or set(row)!={'purpose','exit_code','cleanup_killed','visible_main_seen','fixture_binary_sha256'} or row['purpose']!=purpose or type(row['exit_code']) is not int or row['exit_code']!=0 or row['cleanup_killed'] is not False or type(row['visible_main_seen']) is not bool or row['fixture_binary_sha256']!=hashes:raise ValueError('Secondary lifecycle or hash differs')
        if row['visible_main_seen']!=(purpose in ('disabled','explicit-multi')):raise ValueError('Secondary visibility contradicts route')
    return True


@contextmanager
def isolated_settings():
    import winreg
    token='gui_'+uuid.uuid4().hex
    roots=['Software\\ru_notepad\\SingleInstanceTests\\'+token,'Software\\ru_notepad\\RecentTests\\'+token]
    for path in roots:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,path):raise RuntimeError('Refusing existing test key')
        except FileNotFoundError:pass
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER,path,0,winreg.KEY_SET_VALUE):pass
    try:
        with patch.dict(os.environ,{'RU_NOTEPAD_INSTANCE_TEST_KEY':token,'RU_NOTEPAD_RECENT_TEST_KEY':token}):yield roots[0]
    finally:
        for path in roots:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER,path)
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER,path):raise RuntimeError('Test key survived cleanup')
            except FileNotFoundError:pass


def _wait(api,process,predicate,description,timeout=30,dialogs=False):
    until=time.monotonic()+timeout
    while time.monotonic()<until:
        if process.poll() is not None:raise RuntimeError('GUI exited: '+description)
        if not dialogs:api.no_dialog(process.pid)
        if predicate():return
        time.sleep(.01)
    raise RuntimeError('Timed out: '+description)


def _button(api,process,identifier,timeout=10,exclude=None):
    found=[]
    def find():
        ds=[h for h,c,v in api.windows(process.pid) if c=='#32770' and v and h!=exclude]
        if len(ds)!=1:return False
        child=api.user.GetDlgItem(ds[0],identifier)
        if child and api.user.IsWindowVisible(child):
            api.verify_owned_handles(process.pid,ds[0],child);found.append((ds[0],child));return True
        return False
    _wait(api,process,find,'actual modal button '+str(identifier),timeout,dialogs=True)
    if not api.user.PostMessageW(found[0][1],0xF5,0,0):raise ctypes.WinError(ctypes.get_last_error())
    _wait(api,process,lambda:not api.user.IsWindowVisible(found[0][0]),'clicked dialog dismissed',timeout,dialogs=True)
    return found[0][0]


def _copy_runtime(binary_dir,destination,hashes):
    destination.mkdir()
    for name,digest in hashes.items():
        shutil.copyfile(binary_dir/name,destination/name)
        if ci.sha(destination/name)!=digest:raise RuntimeError('Runtime copy identity differs')


def _post_command(api,hwnd,command):
    # Modal commands cannot be SendMessageTimeout'ed then acknowledged later:
    # their dialog lives inside the command callback. Post, then drive its HWND.
    if not api.user.PostMessageW(hwnd,0x111,command,0):
        raise ctypes.WinError(ctypes.get_last_error())


def _tabs(api,hwnd):return api.scalar(api.control(hwnd,10),0x1304)


def _snapshot(api,hwnd):
    result=[]
    for _ in range(_tabs(api,hwnd)):
        result.append((api.text(hwnd),api.editor_bytes(hwnd)));api.command(hwnd,112)
    return sorted(result)


def _item_rect(api,process,tabs,index):
    # TCM_GETITEMRECT is not a marshalled system message: remote bounded storage.
    k=api.kernel
    k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];k.OpenProcess.restype=wintypes.HANDLE
    k.VirtualAllocEx.argtypes=[wintypes.HANDLE,ctypes.c_void_p,ctypes.c_size_t,wintypes.DWORD,wintypes.DWORD];k.VirtualAllocEx.restype=ctypes.c_void_p
    k.ReadProcessMemory.argtypes=[wintypes.HANDLE,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)];k.ReadProcessMemory.restype=wintypes.BOOL
    k.VirtualFreeEx.argtypes=[wintypes.HANDLE,ctypes.c_void_p,ctypes.c_size_t,wintypes.DWORD];k.VirtualFreeEx.restype=wintypes.BOOL
    k.CloseHandle.argtypes=[wintypes.HANDLE];k.CloseHandle.restype=wintypes.BOOL
    api.verify_owned_handles(process.pid,tabs);handle=k.OpenProcess(0x8|0x10,False,process.pid)
    if not handle:raise ctypes.WinError(ctypes.get_last_error())
    remote=None;completed=False
    try:
        remote=k.VirtualAllocEx(handle,None,ctypes.sizeof(wintypes.RECT),0x3000,4)
        if not remote:raise ctypes.WinError(ctypes.get_last_error())
        got=api.scalar(tabs,0x130A,index,remote)
        completed=True
        if not got:raise RuntimeError('TCM_GETITEMRECT failed')
        rect=wintypes.RECT();copied=ctypes.c_size_t()
        if not k.ReadProcessMemory(handle,remote,ctypes.byref(rect),ctypes.sizeof(rect),ctypes.byref(copied)) or copied.value!=ctypes.sizeof(rect):raise RuntimeError('Tab RECT read failed')
        return rect
    finally:
        # On timeout the remote message may still be running; leave these 16
        # fixture-only bytes owned by the process until its guaranteed cleanup.
        if remote and completed:k.VirtualFreeEx(handle,remote,0,0x8000)
        k.CloseHandle(handle)


def _context(api,process,hwnd,index,menu_index):
    u=api.user;tabs=api.control(hwnd,10);rect=_item_rect(api,process,tabs,index)
    point=wintypes.POINT((rect.left+rect.right)//2,(rect.top+rect.bottom)//2)
    local=(point.x&0xffff)|((point.y&0xffff)<<16)
    u.GetCursorPos.argtypes=[ctypes.POINTER(wintypes.POINT)];u.GetCursorPos.restype=wintypes.BOOL
    u.SetCursorPos.argtypes=[ctypes.c_int,ctypes.c_int];u.SetCursorPos.restype=wintypes.BOOL
    u.ClientToScreen.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.POINT)];u.ClientToScreen.restype=wintypes.BOOL
    original=wintypes.POINT()
    if not u.GetCursorPos(ctypes.byref(original)) or not u.ClientToScreen(tabs,ctypes.byref(point)):raise ctypes.WinError(ctypes.get_last_error())
    try:
        if not u.SetCursorPos(point.x,point.y):raise ctypes.WinError(ctypes.get_last_error())
        for message,wparam in ((0x204,2),(0x205,0)):
            if not u.PostMessageW(tabs,message,wparam,local):raise ctypes.WinError(ctypes.get_last_error())
        _wait(api,process,lambda:any(c=='#32768' and v for _,c,v in api.windows(process.pid)),'actual native tab popup')
        # Select actual popup item; no direct product close WM_COMMAND is sent.
        for key in [0x24]+[0x28]*menu_index+[0x0d]:
            for message,lparam in ((0x100,1),(0x101,0xc0000001)):
                if not u.PostMessageW(hwnd,message,key,lparam):raise ctypes.WinError(ctypes.get_last_error())
        _wait(api,process,lambda:not any(c=='#32768' and v for _,c,v in api.windows(process.pid)),'popup selection',dialogs=True)
    finally:u.SetCursorPos(original.x,original.y)


def run(api,binary_dir,fixtures,evidence):
    import winreg
    binary_dir,fixtures,evidence=map(Path,(binary_dir,fixtures,evidence))
    root=fixtures/'instance-tabs-gui';root.mkdir();paths=[]
    for i in range(4):
        p=root/f'{i} 中文 & 😀 spaced.txt';p.write_bytes(f'fixture {i} 中文😀\r\n'.encode());paths.append(p.resolve())
    originals={str(p):ci.sha(p) for p in paths}
    hashes={n:ci.sha(binary_dir/n) for n in ci.portable.RUNTIME_NAMES}
    result={'schema':'ru-notepad-instance-tabs-gui-v1','name':'main-gui-instance-tabs','passed':False,'executed':False,'cleanup_killed':False,'exit_code':None,'checks':{},'phases':[],'fixture_binary_sha256':hashes,'secondary_processes':[]}
    checks=result['checks']
    def phase(label,exercise,args=()):
        target=root/label;_copy_runtime(binary_dir,target,hashes)
        item=ci.run_gui(api,target,evidence,name='main-gui-instance-'+label,arguments=args,exercise=exercise,log_prefix='instance-'+label)
        item['phase']=label;item['fixture_binary_sha256']=dict(hashes);result['phases'].append(item)
        result['executed']|=item['executed'];result['cleanup_killed']|=item['cleanup_killed']
        if not item['passed']:raise RuntimeError(label+': '+item.get('error','failed'))
    def child(purpose,arguments,visible,exercise=None):
        target=root/('child-'+purpose);_copy_runtime(binary_dir,target,hashes)
        p=subprocess.Popen([str(target/'ru_notepad.exe'),*map(str,arguments)],cwd=root,creationflags=8)
        row={'purpose':purpose,'exit_code':None,'cleanup_killed':False,'visible_main_seen':False,'fixture_binary_sha256':dict(hashes)}
        result['secondary_processes'].append(row)
        try:
            deadline=time.monotonic()+30;hwnd=None
            while time.monotonic()<deadline:
                mains=[h for h,c,v in api.no_dialog(p.pid) if c==ci.MAIN_CLASS and v]
                row['visible_main_seen']|=bool(mains)
                if len(mains)>1:raise RuntimeError('Secondary has multiple main windows')
                if visible and mains:hwnd=mains[0];break
                if p.poll() is not None:break
                time.sleep(.01)
            if visible:
                if hwnd is None:raise RuntimeError('Independent window missing')
                if exercise:exercise(p,hwnd)
                api.close(hwnd)
            elif row['visible_main_seen']:raise RuntimeError('ACK handoff showed secondary main')
            p.wait(timeout=15);row['exit_code']=p.returncode
            if p.returncode!=0:raise RuntimeError('Secondary exit not zero')
        finally:
            row['cleanup_killed']=ci.cleanup_process(p);result['cleanup_killed']|=row['cleanup_killed']
            for i,log in enumerate(sorted(target.glob('ru_notepad-*.log'))[:2]):
                ci.cap_log(log);shutil.copyfile(log,evidence/f'instance-{purpose}-{i}.log')
    with isolated_settings() as registry:
        def persisted(expected):
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,registry) as key:v,t=winreg.QueryValueEx(key,'SingleInstance')
            return t==winreg.REG_DWORD and v==expected
        def handoff(p,h):
            child('multi-path',[paths[0].name,paths[1].name],False)
            _wait(api,p,lambda:_tabs(api,h)==3,'owner exact two paths')
            ci.verify_gui_documents(api,h,{x.name:x.read_bytes() for x in paths[:2]})
            checks.update(unicode_relative_multi_path_handoff=True,secondary_ack_normal_exit=True,no_secondary_visible_window=True,no_owner_extra_blank_tab=True)
            child('duplicate',[paths[0]],False)
            _wait(api,p,lambda:api.text(h)==paths[0].name+' · ru_notepad','duplicate activation')
            if _tabs(api,h)!=3:raise RuntimeError('Duplicate path created tab')
            checks['duplicate_activates_existing']=True
            _post_command(api,h,805);_button(api,p,1)
            if not persisted(0):raise RuntimeError('Disable DWORD missing')
            child('disabled',[paths[2]],True,lambda cp,ch:ci.wait_gui(api,cp,lambda:_tabs(api,ch)==2,'disabled file'))
            checks['persistent_disable_creates_window']=True
            _post_command(api,h,805);_button(api,p,1)
            if not persisted(1):raise RuntimeError('Enable DWORD missing')
            child('reenabled',[paths[2]],False);_wait(api,p,lambda:_tabs(api,h)==4,'reenabled handoff')
            checks['persistent_reenable_handoff']=True
            child('explicit-multi',['--multi-instance',paths[3]],True,lambda cp,ch:ci.wait_gui(api,cp,lambda:_tabs(api,ch)==2,'multi file'))
            checks['explicit_multi_instance_creates_window']=True
            return {}
        phase('handoff',handoff)
        for menu_index,mode in enumerate(('current','others','left','right','saved','all')):
            def exercise(p,h,mode=mode,menu_index=menu_index):
                _wait(api,p,lambda:_tabs(api,h)==5,'four menu files')
                saved_expected=None
                if mode=='saved':
                    editor=api.editor(h);api.user.PostMessageW(editor,0x102,ord('s'),1)
                    _wait(api,p,lambda:api.scalar(editor,2159)==1,'saved-only excludes modified tab')
                    saved_expected=(api.text(h),api.editor_bytes(h))
                before=_snapshot(api,h)
                api.command(h,111)  # active 3, deliberately not clicked tab 2
                _context(api,p,h,2,menu_index)
                count={'current':4,'others':1,'left':3,'right':3,'saved':1,'all':1}[mode]
                _wait(api,p,lambda:_tabs(api,h)==count,'menu '+mode);actual=_snapshot(api,h)
                names={'current':[0,2,3],'others':[1],'left':[1,2,3],'right':[0,1],'saved':[],'all':[]}[mode]
                expected=[(paths[i].name+' · ru_notepad',paths[i].read_bytes()) for i in names]
                if mode in ('current','right'):expected += [x for x in before if not any(x[0]==q.name+' · ru_notepad' for q in paths)]
                if mode=='saved':
                    if actual!=[saved_expected] or not api.scalar(api.editor(h),2159):raise RuntimeError('Unmodified close removed or changed dirty tab')
                    api.command(h,201)
                    _wait(api,p,lambda:api.scalar(api.editor(h),2159)==0,'restore saved-only fixture')
                elif mode=='all':
                    if len(actual)!=1 or actual[0][1]!=b'' or api.scalar(api.editor(h),2159):raise RuntimeError('Close all replacement blank differs')
                elif actual!=sorted(expected):raise RuntimeError('Menu closed wrong documents: '+mode)
                checks['menu_'+mode]=True;checks['clicked_tab_target']=True
                return {}
            phase('menu-'+mode,exercise,paths)
        def cancel(p,h):
            _wait(api,p,lambda:_tabs(api,h)==5,'dirty fixtures')
            # Dirty tab 1, not highest tab 4: a partial-close algorithm would
            # already have destroyed clean tabs 4/3/2 before this Cancel.
            for _ in range(3):api.command(h,111)
            editor=api.editor(h)
            api.user.PostMessageW(editor,0x102,ord('x'),1);_wait(api,p,lambda:api.scalar(editor,2159)==1,'dirty edit')
            before=_snapshot(api,h);_context(api,p,h,2,5);_button(api,p,2)
            _wait(api,p,lambda:not any(c=='#32770' and v for _,c,v in api.windows(p.pid)),'cancel dismissal',dialogs=True)
            if _snapshot(api,h)!=before:raise RuntimeError('Cancel partially closed documents')
            checks['dirty_batch_cancel_preserves_all']=True
            for _ in range(5):
                if api.scalar(api.editor(h),2159):api.command(h,201);break
                api.command(h,112)
            for _ in range(5):
                if api.editor_bytes(h)==b'':break
                api.command(h,112)
            api.user.PostMessageW(api.editor(h),0x102,ord('z'),1)
            _wait(api,p,lambda:api.scalar(api.editor(h),2159)==1,'untitled dirty edit')
            before=_snapshot(api,h);_context(api,p,h,2,5);prompt=_button(api,p,6);_button(api,p,2,exclude=prompt)
            _wait(api,p,lambda:not any(c=='#32770' and v for _,c,v in api.windows(p.pid)),'save-as cancelled',dialogs=True)
            if _snapshot(api,h)!=before:raise RuntimeError('Save As cancellation partially closed documents')
            checks['save_as_cancel_preserves_all']=True
            for _ in range(5):
                if api.scalar(api.editor(h),2159):api.command(h,201);break
                api.command(h,112)
            return {}
        phase('dirty-cancel',cancel,paths)
        # Start both fresh GUI processes without waiting for either HWND/ready flag.
        race={'phase':'startup-race','passed':False,'executed':False,'cleanup_killed':False,
              'exit_code':None,'fixture_binary_sha256':dict(hashes),'participants':[]}
        result['phases'].append(race);race_procs=[]
        try:
            race_dirs=[]
            for i in range(2):
                d=root/('startup-race-'+str(i));_copy_runtime(binary_dir,d,hashes);race_dirs.append(d)
            # Prepare all byte-identical directories BEFORE either start, then
            # launch back-to-back without a ready-window wait or intervening I/O.
            for i,d in enumerate(race_dirs):
                rp=subprocess.Popen([str(d/'ru_notepad.exe'),str(paths[i])],cwd=d,creationflags=8)
                race_procs.append((rp,d))
            race['executed']=True
            until=time.monotonic()+30;owner=None
            while time.monotonic()<until:
                visible=[]
                for rp,d in race_procs:
                    visible.extend((rp,h) for h,c,v in api.no_dialog(rp.pid) if c==ci.MAIN_CLASS and v)
                exited=[rp for rp,d in race_procs if rp.poll() is not None]
                if len(visible)==1 and len(exited)==1:
                    owner=visible[0];break
                time.sleep(.02)
            if owner is None:raise RuntimeError('Simultaneous startup did not converge to one acknowledged owner')
            rp,rh=owner
            _wait(api,rp,lambda:_tabs(api,rh)==3,'race owner accepts both original paths')
            ci.verify_gui_documents(api,rh,{q.name:q.read_bytes() for q in paths[:2]})
            checks['startup_race_single_owner']=True;checks['startup_race_all_paths_once']=True
            api.close(rh)
            for rp,d in race_procs:
                rp.wait(timeout=15)
                if rp.returncode!=0:raise RuntimeError('Startup race process did not exit normally')
            race['passed']=True;race['exit_code']=0
        finally:
            for i,(rp,d) in enumerate(race_procs):
                killed=ci.cleanup_process(rp);race['cleanup_killed']|=killed
                race['participants'].append({'exit_code':rp.returncode,'cleanup_killed':killed})
                for j,log in enumerate(sorted(d.glob('ru_notepad-*.log'))[:2]):
                    ci.cap_log(log);shutil.copyfile(log,evidence/f'instance-race-{i}-{j}.log')
            result['cleanup_killed']|=race['cleanup_killed']

        # A controlled, documented UI-thread suspend exercises the uncertain ACK path.
        # This is fault injection, explicitly NOT a user responsiveness measurement.
        timeout_record={'phase':'timeout-uncertain','passed':False,'executed':False,
                        'cleanup_killed':False,'exit_code':None,'fixture_binary_sha256':dict(hashes),
                        'participants':[],'controlled_ui_suspend':True,'owner_delivery_count':None}
        result['phases'].append(timeout_record)
        timeout_procs=[];thread=None;suspended=False
        k=api.kernel
        k.OpenThread.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];k.OpenThread.restype=wintypes.HANDLE
        k.SuspendThread.argtypes=[wintypes.HANDLE];k.SuspendThread.restype=wintypes.DWORD
        k.ResumeThread.argtypes=[wintypes.HANDLE];k.ResumeThread.restype=wintypes.DWORD
        k.CloseHandle.argtypes=[wintypes.HANDLE];k.CloseHandle.restype=wintypes.BOOL
        def visible_main(proc):
            windows=[h for h,c,v in api.windows(proc.pid) if c==ci.MAIN_CLASS and v]
            return windows[0] if len(windows)==1 else None
        try:
            od=root/'timeout-owner';_copy_runtime(binary_dir,od,hashes)
            op=subprocess.Popen([str(od/'ru_notepad.exe')],cwd=od,creationflags=8);timeout_procs.append((op,od))
            _wait(api,op,lambda:visible_main(op) is not None,'timeout owner visible')
            oh=visible_main(op);api.responsive(oh)
            owner_pid=wintypes.DWORD();tid=api.user.GetWindowThreadProcessId(oh,ctypes.byref(owner_pid))
            if owner_pid.value!=op.pid:raise RuntimeError('Refusing suspend of non-owned UI thread')
            thread=k.OpenThread(2,False,tid)
            if not thread:raise ctypes.WinError(ctypes.get_last_error())
            previous=k.SuspendThread(thread)
            suspended=previous!=0xffffffff
            if previous!=0:raise RuntimeError('Fixture UI thread was already suspended or suspend failed')
            sd=root/'timeout-sender';_copy_runtime(binary_dir,sd,hashes)
            sp=subprocess.Popen([str(sd/'ru_notepad.exe'),paths[3].name],cwd=root,creationflags=8);timeout_procs.append((sp,sd))
            timeout_record['executed']=True
            prompt=_button(api,sp,7,timeout=15)  # No: never automatically reopen uncertain paths.
            if k.ResumeThread(thread)!=1:raise RuntimeError('Owned fixture UI thread resume state differs')
            suspended=False
            _wait(api,sp,lambda:visible_main(sp) is not None,'uncertain sender remains visible')
            sh=visible_main(sp)
            _wait(api,sp,lambda:not any(c=='#32770' and v for _,c,v in api.windows(sp.pid)),'uncertain warning dismissed',dialogs=True)
            api.responsive(oh)
            # Allow late original delivery to settle, but never infer it was cancelled.
            until=time.monotonic()+2
            while time.monotonic()<until:
                api.no_dialog(op.pid);api.no_dialog(sp.pid);time.sleep(.02)
            delivered=_tabs(api,oh)-1
            if delivered not in (0,1):raise RuntimeError('Timed-out request was delivered more than once')
            timeout_record['owner_delivery_count']=delivered
            if _tabs(api,sh)!=1 or api.editor_bytes(sh)!=b'':raise RuntimeError('Uncertain handoff automatically opened files locally')
            checks['timeout_uncertain_no_automatic_open']=True
            _post_command(api,sh,113);_button(api,sp,6)
            _wait(api,sp,lambda:_tabs(api,sh)==2,'explicit open of retained uncertain paths')
            ci.verify_gui_documents(api,sh,{paths[3].name:paths[3].read_bytes()})
            if _tabs(api,oh)!=delivered+1:raise RuntimeError('Explicit local open resent original IPC')
            checks['timeout_pending_explicit_open']=True
            api.close(sh);api.close(oh)
            for proc,d in timeout_procs:
                proc.wait(timeout=15)
                if proc.returncode!=0:raise RuntimeError('Controlled timeout participant did not exit normally')
            timeout_record['passed']=True;timeout_record['exit_code']=0
        finally:
            if suspended and thread:k.ResumeThread(thread)
            if thread:k.CloseHandle(thread)
            for i,(proc,d) in enumerate(timeout_procs):
                killed=ci.cleanup_process(proc);timeout_record['cleanup_killed']|=killed
                timeout_record['participants'].append({'exit_code':proc.returncode,'cleanup_killed':killed})
                for j,log in enumerate(sorted(d.glob('ru_notepad-*.log'))[:2]):
                    ci.cap_log(log);shutil.copyfile(log,evidence/f'instance-timeout-{i}-{j}.log')
            result['cleanup_killed']|=timeout_record['cleanup_killed']
        if any(ci.sha(Path(path))!=digest for path,digest in originals.items()):raise RuntimeError('Synthetic source changed')
        checks['synthetic_sources_unchanged']=True
    checks['isolated_registry_cleaned']=True;result['passed']=True;result['exit_code']=0
    validate_result(result,hashes)
    return result
