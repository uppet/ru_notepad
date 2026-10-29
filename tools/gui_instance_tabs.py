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
import json
import hashlib
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


def _owned_pid(api,process_id,hwnd):
    """Observation may include hidden HWNDs; ownership does not imply visible."""
    actual=wintypes.DWORD()
    if not api.user.GetWindowThreadProcessId(hwnd,ctypes.byref(actual)) or actual.value!=process_id:
        raise RuntimeError('Observed HWND does not belong to the fixture process')
    return actual.value


def _modal_observation(api,process,identifier):
    """Bounded read-only owned-window snapshot, never a modal success oracle."""
    result={'expected_pid':process.pid,'requested_button':identifier,'windows':[]}
    try:
        u=api.user
        u.GetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
        u.GetWindowTextW.restype=ctypes.c_int
        u.IsWindowEnabled.argtypes=[wintypes.HWND];u.IsWindowEnabled.restype=wintypes.BOOL
        u.GetWindow.argtypes=[wintypes.HWND,wintypes.UINT];u.GetWindow.restype=wintypes.HWND
        for hwnd,kind,visible in api.windows(process.pid)[:16]:
            _owned_pid(api,process.pid,hwnd)
            caption=ctypes.create_unicode_buffer(257)
            u.GetWindowTextW(hwnd,caption,len(caption))
            actual_pid=wintypes.DWORD();u.GetWindowThreadProcessId(hwnd,ctypes.byref(actual_pid))
            owner=u.GetWindow(hwnd,4)  # GW_OWNER; never follow it for caption/control reads.
            owner_pid=wintypes.DWORD()
            if owner:u.GetWindowThreadProcessId(owner,ctypes.byref(owner_pid))
            row={'hwnd':int(hwnd),'pid':actual_pid.value,'owner_hwnd':int(owner or 0),
                 'owner_pid':owner_pid.value,'class':kind[:128],'visible':bool(visible),
                 'enabled':bool(u.IsWindowEnabled(hwnd)),'caption':caption.value[:256],'buttons':{}}
            result['windows'].append(row)
            if kind=='#32770':
                for key in (1,2,6,7):
                    button=u.GetDlgItem(hwnd,key)
                    item={'present':bool(button),'visible':False,'enabled':False}
                    if button:
                        _owned_pid(api,process.pid,button)
                        item.update(visible=bool(u.IsWindowVisible(button)),enabled=bool(u.IsWindowEnabled(button)))
                    row['buttons'][str(key)]=item
    except Exception as exc:
        result['observation_error']=type(exc).__name__
    return result


def _registry_observation(registry):
    # Only this run's generated isolated namespace; no normal user preference reads.
    prefix='Software\\ru_notepad\\SingleInstanceTests\\gui_'
    if not registry.startswith(prefix) or len(registry[len(prefix):])!=32 or any(c not in '0123456789abcdef' for c in registry[len(prefix):]):
        return {'observation_error':'invalid isolated namespace'}
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,registry) as key:
            value,kind=winreg.QueryValueEx(key,'SingleInstance')
        return {'type':kind,'value':value if type(value) is int else None,
                'value_is_integer':type(value) is int}
    except Exception as exc:
        return {'observation_error':type(exc).__name__,'winerror':getattr(exc,'winerror',None)}


def _toggle_preference(api,process,hwnd,registry,observations,label):
    observations[label+' registry before']=_registry_observation(registry)
    try:
        _post_command(api,hwnd,805)
        _information_button(api,process,hwnd,observations=observations,label=label)
    finally:
        observations[label+' registry after']=_registry_observation(registry)


def _information_shape(dialog,owner,expected_bodies):
    """Only the command-805 informational box; never a generic ID2=OK alias."""
    if (dialog['owner']!=owner or dialog['caption']!='ru_notepad' or
            not dialog['visible'] or not dialog['enabled']):return None
    controls=dialog['controls']
    buttons=[c for c in controls if c['class']=='Button']
    # Count hidden/disabled buttons too: a second actionable choice is not MB_OK.
    if len(buttons)!=1:return None
    button=buttons[0]
    if button['id'] not in (1,2) or button['control_type'] not in (0,1) or not button['visible'] or not button['enabled']:return None
    if any(c['class'] not in ('Static','Button') for c in controls):return None
    if any(c['class']=='Static' and c['control_type'] not in (0,1,2,3,11,12,14) for c in controls):return None
    # SS_ICON/SS_BITMAP are decorative images, not text payloads. Unknown static types fail closed.
    texts=[c['text'] for c in controls if c['class']=='Static' and c['control_type'] in (0,1,2,11,12) and c['visible'] and c['text']]
    if len(texts)!=1 or texts[0] not in expected_bodies:return None
    return button['hwnd']


def _information_text(api,hwnd,deadline):
    # Read control text with a bounded message, never an unbounded GetDlgItemText.
    remaining=int((deadline-time.monotonic())*1000)
    if remaining<=0:raise RuntimeError('Timed out: command805 information box')
    buffer=ctypes.create_unicode_buffer(2049);copied=ctypes.c_size_t()
    if not api.user.SendMessageTimeoutW(hwnd,0x000D,len(buffer),ctypes.addressof(buffer),3,
                                       min(100,remaining),ctypes.byref(copied)):
        raise RuntimeError('Information box text query did not respond')
    if copied.value>=2048:raise RuntimeError('Information box text exceeds bound')
    return buffer.value


def _information_dialog(api,process,dialog,deadline):
    u=api.user
    u.GetWindow.argtypes=[wintypes.HWND,wintypes.UINT];u.GetWindow.restype=wintypes.HWND
    u.GetDlgCtrlID.argtypes=[wintypes.HWND];u.GetDlgCtrlID.restype=ctypes.c_int
    u.GetWindowLongPtrW.argtypes=[wintypes.HWND,ctypes.c_int];u.GetWindowLongPtrW.restype=ctypes.c_ssize_t
    u.IsWindowEnabled.argtypes=[wintypes.HWND];u.IsWindowEnabled.restype=wintypes.BOOL
    _owned_pid(api,process.pid,dialog)
    controls=[];errors=[]
    @api.callback_type
    def visit(child,_):
        try:
            if len(controls)>=32:raise RuntimeError('Information dialog control inventory exceeds bound')
            _owned_pid(api,process.pid,child)
            name=ctypes.create_unicode_buffer(128)
            if not u.GetClassNameW(child,name,len(name)):raise RuntimeError('Cannot read information control class')
            style=int(u.GetWindowLongPtrW(child,-16))
            controls.append({'hwnd':int(child),'class':name.value,'id':u.GetDlgCtrlID(child),
                             'control_type':style & (31 if name.value=='Static' else 15),
                             'visible':bool(u.IsWindowVisible(child)),'enabled':bool(u.IsWindowEnabled(child)),
                             'text':''})
            return True
        except Exception as exc:
            errors.append(exc);return False
    u.EnumChildWindows(dialog,visit,0)
    if errors:raise errors[0]
    for control in controls:
        if control['visible'] and (control['class']=='Button' or
                (control['class']=='Static' and control['control_type'] in (0,1,2,11,12))):
            control['text']=_information_text(api,control['hwnd'],deadline)
    return {'owner':int(u.GetWindow(dialog,4) or 0),'caption':_information_text(api,dialog,deadline),
            'visible':bool(u.IsWindowVisible(dialog)),'enabled':bool(u.IsWindowEnabled(dialog)),
            'controls':controls}


def _information_button(api,process,owner,timeout=10,*,observations=None,label=None):
    # MessageBox documents the return IDOK, not the internal child ID. Our
    # three real Windows diagnostics observed only child ID2 in this box.
    # Single-button dialogs can use IDCANCEL to support Esc. This exception
    # is restricted to exact command805 text/owner/one-button shape; the generic
    # save/cancel/Yes/No helper below retains its original exact ID contract.
    catalog=json.loads((Path(__file__).resolve().parents[1]/'locales'/'instance_tabs.json').read_text(encoding='utf-8'))
    expected_bodies=set(catalog['instance.next_launch'].values())
    deadline=time.monotonic()+timeout
    try:
        while time.monotonic()<deadline:
            if process.poll() is not None:raise RuntimeError('GUI exited: command805 information box')
            ds=[h for h,c,v in api.windows(process.pid) if c=='#32770' and v]
            if len(ds)==1:
                dialog=_information_dialog(api,process,ds[0],deadline)
                if observations is not None:observations['information '+str(label or '805')]=dialog
                button=_information_shape(dialog,owner,expected_bodies)
                if button is not None:
                    api.verify_owned_handles(process.pid,owner,ds[0],button)
                    if time.monotonic()>=deadline:break
                    if not api.user.PostMessageW(button,0xF5,0,0):raise ctypes.WinError(ctypes.get_last_error())
                    _wait(api,process,lambda:not api.user.IsWindowVisible(ds[0]),'clicked dialog dismissed',timeout,dialogs=True)
                    return ds[0]
            time.sleep(.01)
        raise RuntimeError('Timed out: command805 information box')
    except Exception:
        if observations is not None:
            observations['modal '+str(label or '805')]=_modal_observation(api,process,1)
        raise


def _button(api,process,identifier,timeout=10,exclude=None,*,observations=None,label=None):
    found=[]
    def find():
        ds=[h for h,c,v in api.windows(process.pid) if c=='#32770' and v and h!=exclude]
        if len(ds)!=1:return False
        child=api.user.GetDlgItem(ds[0],identifier)
        if child and api.user.IsWindowVisible(child):
            api.verify_owned_handles(process.pid,ds[0],child);found.append((ds[0],child));return True
        return False
    try:
        _wait(api,process,find,'actual modal button '+str(identifier),timeout,dialogs=True)
        if observations is not None:
            observations['modal '+str(label or identifier)+' found']=_modal_observation(api,process,identifier)
        if not api.user.PostMessageW(found[0][1],0xF5,0,0):raise ctypes.WinError(ctypes.get_last_error())
        _wait(api,process,lambda:not api.user.IsWindowVisible(found[0][0]),'clicked dialog dismissed',timeout,dialogs=True)
    except Exception:
        if observations is not None:
            observations['modal '+str(label or identifier)]=_modal_observation(api,process,identifier)
        raise
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


def _readiness_handle(api,handle,pid=None):
    """Read-only HWND identity. Missing dynamic editors are not fixed controls."""
    u=api.user
    u.IsWindow.argtypes=[wintypes.HWND];u.IsWindow.restype=wintypes.BOOL
    u.IsWindowEnabled.argtypes=[wintypes.HWND];u.IsWindowEnabled.restype=wintypes.BOOL
    u.GetParent.argtypes=[wintypes.HWND];u.GetParent.restype=wintypes.HWND
    result={'hwnd':int(handle),'exists':bool(u.IsWindow(handle))}
    if not result['exists']:return result
    actual=wintypes.DWORD();thread=u.GetWindowThreadProcessId(handle,ctypes.byref(actual))
    if not thread or (pid is not None and actual.value!=pid):
        if not u.IsWindow(handle):return {'hwnd':int(handle),'exists':False}
        raise RuntimeError('Readiness HWND belongs to another process or has no valid owner')
    name=ctypes.create_unicode_buffer(128)
    if not u.GetClassNameW(handle,name,len(name)):
        if not u.IsWindow(handle):return {'hwnd':int(handle),'exists':False}
        raise RuntimeError('Cannot identify live readiness HWND class')
    result.update(pid=actual.value,**{'class':name.value},parent=int(u.GetParent(handle) or 0),
                  visible=bool(u.IsWindowVisible(handle)),enabled=bool(u.IsWindowEnabled(handle)))
    return result


def _fixed_readiness(api,hwnd,pid,previous=None):
    main=_readiness_handle(api,hwnd,pid)
    if not main['exists'] or main['class']!=ci.MAIN_CLASS or not main['visible']:
        raise RuntimeError('Fixed readiness main window disappeared or changed')
    handles={};states={}
    for identifier,kind in ((10,'systabcontrol32'),(11,'static'),(901,'button')):
        handle=api.control(hwnd,identifier)
        if previous is not None and handle!=previous[identifier]:
            raise RuntimeError('Fixed readiness control identity changed')
        state=_readiness_handle(api,handle,pid)
        if not state['exists'] or state['class'].lower()!=kind or state['parent']!=hwnd:
            raise RuntimeError('Fixed readiness control disappeared or changed')
        handles[identifier]=handle;states[identifier]=state
    return handles,states


def _visible_readiness_editors(api,hwnd,pid):
    candidates=[];errors=[];unstable=[False];count=[0]
    @api.callback_type
    def visit(child,_):
        try:
            count[0]+=1
            if count[0]>128:raise RuntimeError('Readiness child inventory exceeds bound')
            state=_readiness_handle(api,child,pid)
            if not state['exists']:unstable[0]=True;return True
            if state['class']=='Scintilla':
                if state['parent']!=hwnd:raise RuntimeError('Readiness editor has the wrong parent')
                if state['visible']:candidates.append(state)
            return True
        except Exception as exc:errors.append(exc);return False
    api.user.EnumChildWindows(hwnd,visit,0)
    if errors:raise errors[0]
    return candidates,unstable[0]


def _readiness(api,hwnd,expected_count=None,pid=None):
    # Fixed controls must always be valid. Inspect them before obtaining a
    # dynamic editor handle; close operations destroy/switch those HWNDs.
    if pid is None:
        main=_readiness_handle(api,hwnd)
        if not main['exists']:raise RuntimeError('Fixed readiness main window disappeared')
        pid=main['pid']
    fixed,states=_fixed_readiness(api,hwnd,pid)
    observed={'tab_count':api.scalar(fixed[10],0x1304),'title':api.text(hwnd),
              'status':api.text(fixed[11]),'tabs_enabled':states[10]['enabled'],
              'cancel_visible':states[901]['visible'],'editor_enabled':False,
              'editor_readonly':None,'snapshot_stable':False}
    def pending(reason,candidates=None):
        observed['transient_reason']=reason
        if candidates is not None:
            observed['editor_candidate_count']=len(candidates)
            observed['editor_candidates']=[item['hwnd'] for item in candidates]
        _fixed_readiness(api,hwnd,pid,fixed)  # A missing fixed window is never transient.
        return observed
    if ((expected_count is not None and observed['tab_count']!=expected_count) or
            not observed['tabs_enabled'] or observed['cancel_visible'] or
            ci.status_startswith(observed['status'],'status.opening')):
        return pending('fixed-state-not-ready')
    candidates,changed=_visible_readiness_editors(api,hwnd,pid)
    if changed or len(candidates)!=1:return pending('editor-inventory-not-stable',candidates)
    before=candidates[0];editor=before['hwnd']
    immediate=_readiness_handle(api,editor,pid)
    if (not immediate['exists'] or immediate.get('class')!='Scintilla' or
            immediate.get('parent')!=hwnd or not immediate.get('visible')):
        return pending('editor-changed-before-query',candidates)
    try:
        readonly=api.scalar(editor,2140)
    except Exception:
        # Never catch by error-string or turn a still-valid editor timeout into
        # polling. Only directly observed destruction/replacement permits it.
        after=_readiness_handle(api,editor,pid)
        current,_=_visible_readiness_editors(api,hwnd,pid)
        replaced=(not after['exists'] or after.get('class')!='Scintilla' or
                  after.get('parent')!=hwnd or
                  (not after.get('visible') and len(current)==1 and current[0]['hwnd']!=editor))
        if replaced:return pending('editor-replaced-during-query',current)
        raise
    _fixed_readiness(api,hwnd,pid,fixed)
    final_count=api.scalar(fixed[10],0x1304)
    final_title=api.text(hwnd);final_status=api.text(fixed[11])
    _,final_states=_fixed_readiness(api,hwnd,pid,fixed)
    current,changed=_visible_readiness_editors(api,hwnd,pid)
    after=_readiness_handle(api,editor,pid)
    if (changed or final_count!=observed['tab_count'] or len(current)!=1 or
            current[0]['hwnd']!=editor or not after['exists'] or after.get('class')!='Scintilla' or
            after.get('parent')!=hwnd or not after.get('visible')):
        return pending('editor-epoch-changed',current)
    if (final_states[10]['enabled']!=observed['tabs_enabled'] or
            final_states[901]['visible']!=observed['cancel_visible'] or
            final_title!=observed['title'] or final_status!=observed['status']):
        observed.update(tabs_enabled=final_states[10]['enabled'],cancel_visible=final_states[901]['visible'],
                        title=final_title,status=final_status)
        return pending('fixed-epoch-changed',current)
    observed.update(editor_enabled=after['enabled'],editor_readonly=readonly,
                    editor_candidate_count=1,editor_candidates=[editor],snapshot_stable=True)
    return observed


def _is_ready(observed,count,title=None):
    return (observed.get('snapshot_stable') is True and observed['tab_count']==count and observed['tabs_enabled'] and
            observed['editor_enabled'] and not observed['cancel_visible'] and
            observed['editor_readonly']==0 and
            not ci.status_startswith(observed['status'],'status.opening') and
            (title is None or observed['title']==title))


def _scalar_window_state(api,process,main,target):
    """No synchronous messages: distinguish stale HWND from a nonresponsive owner."""
    result={'expected_pid':process.pid,'main_hwnd':int(main),'target_hwnd':int(target)}
    try:
        result['process_exit_code']=process.poll()
        u=api.user
        u.IsWindow.argtypes=[wintypes.HWND];u.IsWindow.restype=wintypes.BOOL
        u.IsWindowEnabled.argtypes=[wintypes.HWND];u.IsWindowEnabled.restype=wintypes.BOOL
        result['target_exists']=bool(u.IsWindow(target))
        pid=wintypes.DWORD();tid=u.GetWindowThreadProcessId(target,ctypes.byref(pid))
        result.update(target_pid=pid.value,target_thread=int(tid),target_owned=pid.value==process.pid,
                      target_visible=bool(u.IsWindowVisible(target)),target_enabled=bool(u.IsWindowEnabled(target)))
        if result['target_exists'] and result['target_owned']:
            name=ctypes.create_unicode_buffer(128)
            u.GetClassNameW(target,name,len(name));result['target_class']=name.value
        main_pid=wintypes.DWORD();main_tid=u.GetWindowThreadProcessId(main,ctypes.byref(main_pid))
        result.update(main_exists=bool(u.IsWindow(main)),main_pid=main_pid.value)
        if main_tid and main_pid.value==process.pid:
            u.GetGUIThreadInfo.argtypes=[ctypes.c_uint32,ctypes.POINTER(_GUIThreadInfo)]
            u.GetGUIThreadInfo.restype=wintypes.BOOL
            info=_GUIThreadInfo();info.cbSize=ctypes.sizeof(info)
            if u.GetGUIThreadInfo(main_tid,ctypes.byref(info)):
                result['gui_thread']={'flags':info.flags,'active':int(info.hwndActive or 0),
                    'focus':int(info.hwndFocus or 0),'capture':int(info.hwndCapture or 0),
                    'menu_owner':int(info.hwndMenuOwner or 0)}
            else:result['gui_thread_error']='GetGUIThreadInfo failed'
    except Exception as exc:result['observation_error']=type(exc).__name__
    return result


@contextmanager
def _scalar_failure_evidence(api,process,main,observations,label):
    original=api.scalar
    def measured(target,message,wparam=0,lparam=0):
        # Clear ctypes' thread-local saved error only; the original call and its
        # unchanged 5000 ms timeout remain the sole operation under measurement.
        clear=getattr(ctypes,'set_last_error',None)
        if clear:clear(0)
        started=time.perf_counter()
        try:return original(target,message,wparam,lparam)
        except Exception as original_error:
            try:
                get_error=getattr(ctypes,'get_last_error',None)
                last_error=get_error() if get_error else None
                elapsed=(time.perf_counter()-started)*1000
                if observations is not None:
                    detail={'message':int(message),'target_hwnd':int(target),'wparam':int(wparam),
                            'declared_timeout_ms':5000,'elapsed_ms':round(elapsed,3),'last_error':last_error}
                    # Do not record lparam: some queries carry a local buffer pointer.
                    detail['window']=_scalar_window_state(api,process,main,target)
                    observations['scalar failure '+label]=detail
            except Exception as diagnostic_error:
                original_error.add_note('Scalar failure observation failed: '+type(diagnostic_error).__name__)
            raise
    with patch.object(api,'scalar',measured):yield


def _wait_ready(api,process,hwnd,count,description,observations=None,title=None):
    transient_count=0;last_transient=None
    def ready():
        nonlocal transient_count,last_transient
        observed=_readiness(api,hwnd,count,process.pid)
        if not observed['snapshot_stable']:
            transient_count+=1
            last_transient={key:observed[key] for key in ('transient_reason','editor_candidate_count','editor_candidates') if key in observed}
        observed.update(transient_count=transient_count,last_transient=last_transient)
        if observations is not None:observations[description]=observed
        return _is_ready(observed,count,title)
    # Same 30-second wait budget, not an added sleep or a relaxed acceptance.
    with _scalar_failure_evidence(api,process,hwnd,observations,description):
        _wait(api,process,ready,description,timeout=30)


@contextmanager
def _failure_evidence(evidence,result,observations,expected):
    try:
        yield
    except Exception as exc:
        # Diagnostic only, never consumed as a passing acceptance receipt.
        # Preserve partial child/phase records even when run() raises.
        def bounded(value,depth=0):
            # Bound scalar leaves before container depth so nested menu RECT
            # coordinates survive without allowing deeper lists/dicts.
            if value is None or type(value) in (int,float,bool):return value
            if isinstance(value,str):return value[:2048]
            if depth>8:return '[depth limit]'
            if isinstance(value,dict):return {str(k)[:128]:bounded(v,depth+1) for k,v in list(value.items())[:64]}
            if isinstance(value,(list,tuple)):return [bounded(v,depth+1) for v in value[:64]]
            if value is None or type(value) in (int,float,bool):return value
            return str(value)[:2048]
        try:
            root=Path(__file__).resolve().parents[1]
            sources=('tools/gui_instance_tabs.py','tools/windows_ci.py','src/main.ru','src/single_instance.ru',
                     'src/single_instance_policy.ru','src/single_instance_settings.ru')
            payload={'schema':'ru-notepad-instance-tabs-partial-v1','accepted':False,'error':str(exc),
                     'record':result,'observations':observations,'expected_documents':expected,
                     'source_sha256':{name:ci.sha(root/name) for name in sources}}
            encoded=json.dumps(bounded(payload),ensure_ascii=False,indent=2).encode('utf-8')
            if len(encoded)>131072:
                payload={'schema':'ru-notepad-instance-tabs-partial-v1','accepted':False,
                         'error':str(exc)[:2048],'diagnostic_truncated':True,
                         'fixture_binary_sha256':result.get('fixture_binary_sha256'),
                         'partial_record_sha256':hashlib.sha256(encoded).hexdigest()}
                encoded=json.dumps(payload,ensure_ascii=False,indent=2).encode('utf-8')
            (Path(evidence)/'instance-tabs-partial.json').write_bytes(encoded+b'\n')
        except OSError as diagnostic_error:
            exc.add_note('Could not retain bounded GUI diagnostic: '+str(diagnostic_error))
        raise


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


# Fixed Win32 widths also keep portable ABI tests meaningful on LP64 Linux.
class _MouseInput(ctypes.Structure):
    _fields_=[('dx',ctypes.c_int32),('dy',ctypes.c_int32),('mouseData',ctypes.c_uint32),
              ('dwFlags',ctypes.c_uint32),('time',ctypes.c_uint32),('dwExtraInfo',ctypes.c_size_t)]
class _InputValue(ctypes.Union):
    _fields_=[('mi',_MouseInput)]
class _Input(ctypes.Structure):
    _fields_=[('type',ctypes.c_uint32),('value',_InputValue)]
class _Point(ctypes.Structure):
    _fields_=[('x',ctypes.c_int32),('y',ctypes.c_int32)]
class _Rect(ctypes.Structure):
    _fields_=[('left',ctypes.c_int32),('top',ctypes.c_int32),('right',ctypes.c_int32),('bottom',ctypes.c_int32)]
class _GUIThreadInfo(ctypes.Structure):
    _fields_=[('cbSize',ctypes.c_uint32),('flags',ctypes.c_uint32),
              *[(name,ctypes.c_void_p) for name in ('hwndActive','hwndFocus','hwndCapture','hwndMenuOwner','hwndMoveSize','hwndCaret')],
              ('rcCaret',_Rect)]
class _MenuBarInfo(ctypes.Structure):
    _fields_=[('cbSize',ctypes.c_uint32),('rcBar',_Rect),('hMenu',ctypes.c_void_p),
              ('hwndMenu',ctypes.c_void_p),('focusFlags',ctypes.c_uint32)]


def _menu_api(api):
    u=api.user
    signatures={
        'GetCursorPos':([ctypes.POINTER(_Point)],wintypes.BOOL),
        'SetCursorPos':([ctypes.c_int,ctypes.c_int],wintypes.BOOL),
        'ClientToScreen':([wintypes.HWND,ctypes.POINTER(_Point)],wintypes.BOOL),
        'WindowFromPoint':([_Point],wintypes.HWND),
        'GetForegroundWindow':([],wintypes.HWND),
        'SetForegroundWindow':([wintypes.HWND],wintypes.BOOL),
        'GetAsyncKeyState':([ctypes.c_int],ctypes.c_int16),
        'SendInput':([ctypes.c_uint32,ctypes.POINTER(_Input),ctypes.c_int],ctypes.c_uint32),
        'GetGUIThreadInfo':([ctypes.c_uint32,ctypes.POINTER(_GUIThreadInfo)],wintypes.BOOL),
        'GetMenuBarInfo':([wintypes.HWND,ctypes.c_int32,ctypes.c_int32,ctypes.POINTER(_MenuBarInfo)],wintypes.BOOL),
        'GetMenuItemCount':([ctypes.c_void_p],ctypes.c_int),
        'GetMenuItemID':([ctypes.c_void_p,ctypes.c_int],ctypes.c_uint32),
        'GetMenuState':([ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32],ctypes.c_uint32),
        'GetMenuItemRect':([wintypes.HWND,ctypes.c_void_p,ctypes.c_uint32,ctypes.POINTER(_Rect)],wintypes.BOOL),
        'GetMenuStringW':([ctypes.c_void_p,ctypes.c_uint32,wintypes.LPWSTR,ctypes.c_int,ctypes.c_uint32],ctypes.c_int),
        'IsWindow':([wintypes.HWND],wintypes.BOOL)}
    for name,(args,result) in signatures.items():
        fn=getattr(u,name);fn.argtypes=args;fn.restype=result


def _popup_state(api,process,hwnd):
    u=api.user;state={'pid':process.pid,'foreground':int(u.GetForegroundWindow() or 0),'popups':[]}
    try:
        _owned_pid(api,process.pid,hwnd)
        tid=u.GetWindowThreadProcessId(hwnd,None)
        info=_GUIThreadInfo();info.cbSize=ctypes.sizeof(info)
        if not u.GetGUIThreadInfo(tid,ctypes.byref(info)):raise RuntimeError('Cannot query fixture GUI thread')
        state.update(flags=info.flags,menu_owner=int(info.hwndMenuOwner or 0),focus=int(info.hwndFocus or 0),capture=int(info.hwndCapture or 0))
        for popup,kind,visible in api.windows(process.pid):
            if kind!='#32768' or not visible:continue
            _owned_pid(api,process.pid,popup)
            row={'hwnd':int(popup),'items':[]};state['popups'].append(row)
            menu=_MenuBarInfo();menu.cbSize=ctypes.sizeof(menu)
            if not u.GetMenuBarInfo(popup,-4,0,ctypes.byref(menu)) or not menu.hMenu:
                raise RuntimeError('Cannot inspect actual popup HMENU')
            row['hmenu']=int(menu.hMenu);count=u.GetMenuItemCount(menu.hMenu);row['count']=count
            if count!=6:raise RuntimeError('Tab popup item inventory differs')
            for index in range(count):
                rect=_Rect();text=ctypes.create_unicode_buffer(257)
                # NULL asks Windows to locate this displayed popup's menu window.
                if not u.GetMenuItemRect(None,menu.hMenu,index,ctypes.byref(rect)):
                    raise RuntimeError('Cannot inspect popup item rectangle')
                length=u.GetMenuStringW(menu.hMenu,index,text,len(text),0x400)
                if length<=0 or length>=256:raise RuntimeError('Popup item label is missing or unbounded')
                row['items'].append({'id':int(u.GetMenuItemID(menu.hMenu,index)),
                    'state':int(u.GetMenuState(menu.hMenu,index,0x400)),'label':text.value,
                    'rect':[rect.left,rect.top,rect.right,rect.bottom]})
    except Exception as exc:state['observation_error']=str(exc)[:256]
    return state


def _popup_target(state,hwnd,index,labels):
    if state.get('observation_error') or state.get('menu_owner')!=hwnd or not state.get('flags',0)&4:
        return None
    if len(state['popups'])!=1:return None
    popup=state['popups'][0]
    if popup.get('count')!=6 or [item['id'] for item in popup['items']]!=list(range(1300,1306)):return None
    if any(item['label'] not in labels[i] for i,item in enumerate(popup['items'])):return None
    target=popup['items'][index];left,top,right,bottom=target['rect']
    if target['state']==0xffffffff or target['state']&3 or right<=left or bottom<=top:return None
    return popup['hwnd'],_Point((left+right)//2,(top+bottom)//2)


def _physical_click(api,process,main,target,point,right,pending):
    u=api.user
    if u.GetForegroundWindow()!=main:raise RuntimeError('Refusing input outside foreground fixture')
    _owned_pid(api,process.pid,main);_owned_pid(api,process.pid,target)
    if not u.SetCursorPos(point.x,point.y):raise RuntimeError('Cannot position mouse over fixture')
    # Recheck after positioning; never inject into an occluding/foreign window.
    if u.WindowFromPoint(point)!=target or u.GetForegroundWindow()!=main:
        raise RuntimeError('Mouse target is not the owned fixture control')
    down,up=(8,16) if right else (2,4)
    inputs=(_Input*2)();inputs[0].value.mi.dwFlags=down;inputs[1].value.mi.dwFlags=up
    # Track before the API: a partial/uncertain batch may have pressed our button.
    pending.add(up)
    sent=u.SendInput(2,inputs,ctypes.sizeof(_Input))
    if sent==0:pending.remove(up)  # No event was inserted, so this test pressed nothing.
    if sent!=2:raise RuntimeError('SendInput did not deliver both fixture mouse events')
    pending.remove(up)


def _context(api,process,hwnd,index,menu_index,observations=None):
    _menu_api(api);u=api.user
    if u.GetAsyncKeyState(1)&0x8000 or u.GetAsyncKeyState(2)&0x8000:
        raise RuntimeError('Refusing mouse test while a pre-existing button is held')
    tabs=api.control(hwnd,10);rect=_item_rect(api,process,tabs,index)
    point=_Point((rect.left+rect.right)//2,(rect.top+rect.bottom)//2)
    original=_Point();previous=u.GetForegroundWindow();pending=set()
    if not u.GetCursorPos(ctypes.byref(original)) or not u.ClientToScreen(tabs,ctypes.byref(point)):
        raise RuntimeError('Cannot locate owned tab on screen')
    catalog=json.loads((Path(__file__).resolve().parents[1]/'locales'/'instance_tabs.json').read_text(encoding='utf-8'))
    labels=[set(catalog['tab.close_'+name].values()) for name in ('current','others','left','right','saved','all')]
    trace=[]
    if observations is not None:observations['popup '+str(index)+' '+str(menu_index)]=trace
    def observe(stage):
        state=_popup_state(api,process,hwnd)
        row={'stage':stage,**state}
        if trace and trace[-1]['stage']==stage:trace[-1]=row
        elif len(trace)<16:trace.append(row)
        return state
    try:
        if previous!=hwnd and not u.SetForegroundWindow(hwnd):raise RuntimeError('Cannot foreground owned fixture')
        observe('before right click')
        _physical_click(api,process,hwnd,tabs,point,True,pending)  # Normal DOWN+UP, no held-button workaround.
        selected=[];saw_popup=[False]
        def popup_ready():
            state=observe('after right click')
            if state['popups']:saw_popup[0]=True
            elif saw_popup[0]:raise RuntimeError('Popup disappeared after normal right-button release')
            target=_popup_target(state,hwnd,menu_index,labels)
            if target:selected.append(target);return True
            return False
        _wait(api,process,popup_ready,'actual native tab popup with exact items')
        popup,point=selected[0]
        # Capture the same visible menu immediately before input, not a stale item rectangle.
        target=_popup_target(observe('before left click'),hwnd,menu_index,labels)
        if target is None or target[0]!=popup:raise RuntimeError('Popup disappeared before ordinary selection')
        _physical_click(api,process,hwnd,popup,target[1],False,pending)
        _wait(api,process,lambda:not any(c=='#32768' and v for _,c,v in api.windows(process.pid)),
              'popup selection',dialogs=True)
        observe('after left click')
    finally:
        # Only release buttons this test may have pressed; never touch pre-held user keys.
        cleanup_errors=[]
        for up in pending:
            release=(_Input*1)();release[0].value.mi.dwFlags=up
            if u.SendInput(1,release,ctypes.sizeof(_Input))!=1:
                cleanup_errors.append('Could not release fixture-injected mouse button')
        if not u.SetCursorPos(original.x,original.y):cleanup_errors.append('Could not restore original cursor')
        if previous and previous!=hwnd and u.IsWindow(previous):
            if not u.SetForegroundWindow(previous) and u.GetForegroundWindow()!=previous:
                cleanup_errors.append('Could not restore original foreground window')
        if cleanup_errors:
            if observations is not None:observations['popup input cleanup errors']=cleanup_errors
            import sys
            original_error=sys.exception()
            if original_error is not None:original_error.add_note('; '.join(cleanup_errors))
            else:raise RuntimeError('; '.join(cleanup_errors))


def _race_launch_context(registry):
    try:
        namespace=os.environ.get('RU_NOTEPAD_INSTANCE_TEST_KEY','')
        return {'namespace_sha256':hashlib.sha256(namespace.encode('utf-8')).hexdigest(),
                'namespace_valid':namespace.startswith('gui_') and len(namespace)==36 and all(c in '0123456789abcdef' for c in namespace[4:]),
                'registry':_registry_observation(registry)}
    except Exception as exc:return {'namespace_valid':False,'observation_error':type(exc).__name__}


def _race_observation(api,participants,registry):
    """Diagnostic only: no UI messages, route changes, retries, or acceptance."""
    result={'config':_race_launch_context(registry),'participants':[]}
    try:
        namespace=os.environ.get('RU_NOTEPAD_INSTANCE_TEST_KEY','')
        if not result['config']['namespace_valid']:raise RuntimeError('Invalid isolated race namespace')
        property_name='RuNotepad.SingleInstance.v1.test.'+namespace
        u=api.user;k=api.kernel
        u.GetPropW.argtypes=[wintypes.HWND,wintypes.LPCWSTR];u.GetPropW.restype=wintypes.HANDLE
        u.GetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int];u.GetWindowTextW.restype=ctypes.c_int
        k.ProcessIdToSessionId.argtypes=[wintypes.DWORD,ctypes.POINTER(wintypes.DWORD)]
        k.ProcessIdToSessionId.restype=wintypes.BOOL
        for process,_ in participants[:2]:
            row={'pid':process.pid,'exit_code':process.poll(),'windows':[]};result['participants'].append(row)
            if row['exit_code'] is not None:continue
            session=wintypes.DWORD()
            if k.ProcessIdToSessionId(process.pid,ctypes.byref(session)):row['session_id']=session.value
            else:row['session_error']='ProcessIdToSessionId failed'
            try:
                for hwnd,kind,visible in api.windows(process.pid):
                    if kind!=ci.MAIN_CLASS:continue
                    if len(row['windows'])>=4:raise RuntimeError('Race main-window inventory exceeds bound')
                    _owned_pid(api,process.pid,hwnd)
                    caption=ctypes.create_unicode_buffer(257)
                    u.GetWindowTextW(hwnd,caption,len(caption))
                    # Revalidate after the caption observation before querying its property.
                    _owned_pid(api,process.pid,hwnd)
                    row['windows'].append({'hwnd':int(hwnd),'visible':bool(visible),'title':caption.value[:256],
                                           'owner_property_present':bool(u.GetPropW(hwnd,property_name))})
            except Exception as exc:row['observation_error']=type(exc).__name__
    except Exception as exc:result['observation_error']=type(exc).__name__
    return result


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
    observations={}
    expected_documents={p.name:{'bytes':p.stat().st_size,'sha256':ci.sha(p)} for p in paths}
    def ready(process,hwnd,count,label,title=None):
        _wait_ready(api,process,hwnd,count,label,observations,title)
    def documents(hwnd,expected,label):
        # Keep original exact Unicode-title/UTF8-byte validator unchanged. This
        # proxy records only bounded fixture metadata, not arbitrary user text.
        observed=[]
        class RecordingAPI:
            def __getattr__(self,name):return getattr(api,name)
            def text(self,handle):
                value=api.text(handle)
                if handle==hwnd:observed.append({'title':value})
                return value
            def editor_bytes(self,handle):
                value=api.editor_bytes(handle)
                if observed:observed[-1].update(bytes=len(value),sha256=hashlib.sha256(value).hexdigest())
                return value
        observations[label]={'expected':{n:{'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()} for n,v in expected.items()},'observed':observed}
        ci.verify_gui_documents(RecordingAPI(),hwnd,expected)
    def child_documents(process,hwnd,path,label):
        ready(process,hwnd,2,label)
        documents(hwnd,{path.name:path.read_bytes()},label+' exact documents')
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
    with _failure_evidence(evidence,result,observations,expected_documents), isolated_settings() as registry:
        def persisted(expected):
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,registry) as key:v,t=winreg.QueryValueEx(key,'SingleInstance')
            return t==winreg.REG_DWORD and v==expected
        def handoff(p,h):
            child('multi-path',[paths[0].name,paths[1].name],False)
            ready(p,h,3,'owner exact two paths')
            documents(h,{x.name:x.read_bytes() for x in paths[:2]},'handoff exact documents')
            checks.update(unicode_relative_multi_path_handoff=True,secondary_ack_normal_exit=True,no_secondary_visible_window=True,no_owner_extra_blank_tab=True)
            child('duplicate',[paths[0]],False)
            ready(p,h,3,'duplicate activation',paths[0].name+' · ru_notepad')
            if _tabs(api,h)!=3:raise RuntimeError('Duplicate path created tab')
            checks['duplicate_activates_existing']=True
            _toggle_preference(api,p,h,registry,observations,'disable')
            if not persisted(0):raise RuntimeError('Disable DWORD missing')
            child('disabled',[paths[2]],True,lambda cp,ch:child_documents(cp,ch,paths[2],'disabled file'))
            checks['persistent_disable_creates_window']=True
            _toggle_preference(api,p,h,registry,observations,'reenable')
            if not persisted(1):raise RuntimeError('Enable DWORD missing')
            child('reenabled',[paths[2]],False);ready(p,h,4,'reenabled handoff')
            documents(h,{x.name:x.read_bytes() for x in paths[:3]},'reenabled exact documents')
            checks['persistent_reenable_handoff']=True
            child('explicit-multi',['--multi-instance',paths[3]],True,lambda cp,ch:child_documents(cp,ch,paths[3],'multi file'))
            checks['explicit_multi_instance_creates_window']=True
            return {}
        phase('handoff',handoff)
        for menu_index,mode in enumerate(('current','others','left','right','saved','all')):
            def exercise(p,h,mode=mode,menu_index=menu_index):
                ready(p,h,5,'four menu files '+mode)
                saved_expected=None
                if mode=='saved':
                    editor=api.editor(h);api.user.PostMessageW(editor,0x102,ord('s'),1)
                    _wait(api,p,lambda:api.scalar(editor,2159)==1,'saved-only excludes modified tab')
                    saved_expected=(api.text(h),api.editor_bytes(h))
                before=_snapshot(api,h)
                api.command(h,111)  # active 3, deliberately not clicked tab 2
                _context(api,p,h,2,menu_index,observations)
                count={'current':4,'others':1,'left':3,'right':3,'saved':1,'all':1}[mode]
                ready(p,h,count,'menu '+mode);actual=_snapshot(api,h)
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
            ready(p,h,5,'dirty fixtures')
            # Dirty tab 1, not highest tab 4: a partial-close algorithm would
            # already have destroyed clean tabs 4/3/2 before this Cancel.
            for _ in range(3):api.command(h,111)
            editor=api.editor(h)
            api.user.PostMessageW(editor,0x102,ord('x'),1);_wait(api,p,lambda:api.scalar(editor,2159)==1,'dirty edit')
            before=_snapshot(api,h);_context(api,p,h,2,5,observations);_button(api,p,2,observations=observations,label='dirty cancel')
            ready(p,h,5,'cancel dismissal and unlocked documents')
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
            before=_snapshot(api,h);_context(api,p,h,2,5,observations);prompt=_button(api,p,6,observations=observations,label='save yes');_button(api,p,2,exclude=prompt,observations=observations,label='save-as cancel')
            ready(p,h,5,'save-as cancelled and unlocked documents')
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
            observations['startup-race launch config']=_race_launch_context(registry)
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
            if owner is None:
                observations['startup-race failure']=_race_observation(api,race_procs,registry)
                raise RuntimeError('Simultaneous startup did not converge to one acknowledged owner')
            rp,rh=owner
            ready(rp,rh,3,'race owner accepts both original paths')
            documents(rh,{q.name:q.read_bytes() for q in paths[:2]},'race exact documents')
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
            prompt=_button(api,sp,7,timeout=15,observations=observations,label='uncertain no')  # No: never automatically reopen uncertain paths.
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
            ready(op,oh,delivered+1,'late timeout owner delivery settled')
            timeout_record['owner_delivery_count']=delivered
            if _tabs(api,sh)!=1 or api.editor_bytes(sh)!=b'':raise RuntimeError('Uncertain handoff automatically opened files locally')
            checks['timeout_uncertain_no_automatic_open']=True
            _post_command(api,sh,113);_button(api,sp,6,observations=observations,label='pending yes')
            ready(sp,sh,2,'explicit open of retained uncertain paths')
            documents(sh,{paths[3].name:paths[3].read_bytes()},'pending exact documents')
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
