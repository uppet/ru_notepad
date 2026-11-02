#!/usr/bin/env python3
"""Windows literal-scope/history gate. Portable receipt validation is not execution."""
import ctypes
from ctypes import wintypes
import hashlib
import json
import math
import time
from pathlib import Path
import windows_ci as ci
from gui_instance_tabs import isolated_settings, _copy_runtime, _information_dialog, _information_shape, _wait, _post_command
from gui_fold_commands import activate_source, LARGE_BYTES
from gui_eol_conversion import save_and_verify

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ('en', 'zh-CN', 'ja', 'ko', 'es', 'ru', 'it')
CASE_CHECKS = ('captured_direction', 'exact_match', 'utf8_boundary', 'text_undo_unchanged', 'disk_unchanged', 'saved_exact', 'fresh_reopen')
CHECKS = ('seven_languages', 'fixed_scope_repeated', 'outside_caret_clamped', 'replacement_blocked',
          'readonly_find_replace_guard', 'empty_capture_invalid', 'rectangular_capture_invalid',
          'multiple_capture_invalid', 'edit_undo_invalid', 'tab_invalid', 'close_reopen_invalid', 'close_tab_reopen_invalid',
          'explicit_document_recovery', 'empty_pattern_no_mutation', 'history_mru_bound',
          'history_reselect_no_execution', 'history_empty_replace', 'history_clear',
          'history_oversize_excluded', 'history_restart_empty', 'replace_all_one_undo',
          'large_search_bounded', 'f3_message_loop', 'modal_command_guard', 'nowrap_boundaries', 'seven_language_layout')


def cases():
    rows=[]
    for backwards in (False, True):
        for reverse in (False, True):
            for wrap in (False, True):
                for outside in (False, True):
                    source='汉😀 外|汉😀 a 汉😀|尾 汉😀'.encode(); pattern='汉😀'
                    lo=len('汉😀 外|'.encode()); hi=len('汉😀 外|汉😀 a 汉😀'.encode())
                    first=lo; last=hi-len(pattern.encode())
                    caret=(len(source) if backwards else 0) if outside else (hi if backwards else lo)
                    rows.append(dict(id=f'unicode-{int(backwards)}{int(reverse)}{int(wrap)}{int(outside)}',source=source,
                                     pattern=pattern,low=lo,high=hi,reverse=reverse,backwards=backwards,wrap=wrap,
                                     case=True,whole=False,caret=caret,expected=(last,hi) if backwards else (first,first+len(pattern.encode()))))
    for name,pattern,case,whole,expected in (
        ('case-sensitive','cat',True,False,(7,10)),('case-insensitive','cat',False,False,(2,5)),
        ('whole-sensitive','cat',True,True,(19,22)),('whole-insensitive','cat',False,True,(2,5)),
        ('no-match','dog',True,False,None),('no-normalization','é',True,False,None)):
        rows.append(dict(id=name,source=b'X|CAT scatter _cat cat|Y',pattern=pattern,low=2,high=22,
                         reverse=False,backwards=False,wrap=True,case=case,whole=whole,caret=2,expected=expected))
    for backwards in (False,True):
        source='外\r\n甲😀\r\n乙\r\n甲😀\r\n乙\r\n尾'.encode(); pattern='甲😀\r\n乙'
        lo=len('外\r\n'.encode()); hi=len(source)-len('\r\n尾'.encode())
        start=source.rfind(pattern.encode(),lo,hi) if backwards else lo
        rows.append(dict(id='multiline-'+str(int(backwards)),source=source,pattern=pattern,low=lo,high=hi,
                         reverse=backwards,backwards=backwards,wrap=True,case=True,whole=False,
                         caret=hi if backwards else lo,expected=(start,start+len(pattern.encode()))))
    return tuple(rows)

ALL_CASES=cases()

def expected_cases():
    return [dict(id=c['id'],source_sha256=hashlib.sha256(c['source']).hexdigest(),checks=dict.fromkeys(CASE_CHECKS,True)) for c in ALL_CASES]



LAYOUT_SIZES=((640,400),(1120,760))
SEARCH_CONTROLS=(310,311,316,306,309,312,308,303,304,305,307)
LAYOUT_CONTROLS=SEARCH_CONTROLS+(10,11,0)  # 0 denotes the visible editor


def disjoint(a,b):
    return a[2]<=b[0] or b[2]<=a[0] or a[3]<=b[1] or b[3]<=a[1]


def validate_layouts(rows):
    identities=[(language,scope,list(size)) for language in LANGUAGES for scope in ('selection','invalid','document') for size in LAYOUT_SIZES]
    if not isinstance(rows,list) or len(rows)!=len(identities): raise ValueError('Search layout inventory incomplete')
    for row,(language,scope,size) in zip(rows,identities):
        if not isinstance(row,dict) or set(row)!={'language','scope','requested','outer','client','rectangles','minimum_widths','scope_disabled'}: raise ValueError('Search layout fields differ')
        if (row['language'],row['scope'],row['requested'])!=(language,scope,size) or row['scope_disabled'] is not True: raise ValueError('Search layout identity or disabled scope differs')
        if not isinstance(row['outer'],list) or len(row['outer'])!=2 or any(type(n) is not int for n in row['outer']): raise ValueError('Search layout outer dimension types differ')
        if not (640<=row['outer'][0]<=size[0] and 400<=row['outer'][1]<=size[1]):raise ValueError('Search actual window dimensions outside supported requested range')
        client=row['client']
        if not isinstance(client,list) or len(client)!=2 or any(type(n) is not int or n<=0 for n in client): raise ValueError('Search layout client dimensions invalid')
        if client[0]>row['outer'][0] or client[1]>row['outer'][1]:raise ValueError('Search client exceeds native outer dimensions')
        rects=row['rectangles']; widths=row['minimum_widths']
        if not isinstance(rects,dict) or set(rects)!=set(map(str,LAYOUT_CONTROLS)) or not isinstance(widths,dict) or set(widths)!=set(map(str,SEARCH_CONTROLS)): raise ValueError('Search layout control inventory differs')
        for key,rect in rects.items():
            if not isinstance(rect,list) or len(rect)!=4 or any(type(n) is not int for n in rect): raise ValueError('Search layout rectangle invalid')
            if not (0<=rect[0]<rect[2]<=client[0] and 0<=rect[1]<rect[3]<=client[1]): raise ValueError('Search layout control outside client')
            if key in widths and (type(widths[key]) is not int or widths[key]<=0 or rect[2]-rect[0]<widths[key]): raise ValueError('Search layout text width insufficient')
        values=list(rects.values())
        if any(not disjoint(a,b) for i,a in enumerate(values) for b in values[i+1:]): raise ValueError('Search layout controls overlap')
    return True


def native_layout(api,hwnd,language,scope,size):
    u=api.user; gdi=ctypes.WinDLL('gdi32',use_last_error=True)
    u.MoveWindow.argtypes=[wintypes.HWND,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,wintypes.BOOL];u.MoveWindow.restype=wintypes.BOOL
    u.GetWindowRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)];u.GetWindowRect.restype=wintypes.BOOL
    u.ClientToScreen.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.POINT)];u.ClientToScreen.restype=wintypes.BOOL
    u.GetDC.argtypes=[wintypes.HWND];u.GetDC.restype=wintypes.HDC
    u.ReleaseDC.argtypes=[wintypes.HWND,wintypes.HDC];u.ReleaseDC.restype=ctypes.c_int
    gdi.SelectObject.argtypes=[wintypes.HDC,wintypes.HANDLE];gdi.SelectObject.restype=wintypes.HANDLE
    gdi.GetTextExtentPoint32W.argtypes=[wintypes.HDC,wintypes.LPCWSTR,ctypes.c_int,ctypes.POINTER(wintypes.SIZE)];gdi.GetTextExtentPoint32W.restype=wintypes.BOOL
    if not u.MoveWindow(hwnd,40,40,size[0],size[1],True):raise ctypes.WinError(ctypes.get_last_error())
    api.responsive(hwnd)
    outer=wintypes.RECT();client=wintypes.RECT();origin=wintypes.POINT(0,0)
    if not u.GetWindowRect(hwnd,ctypes.byref(outer)) or not u.GetClientRect(hwnd,ctypes.byref(client)) or not u.ClientToScreen(hwnd,ctypes.byref(origin)):raise ctypes.WinError(ctypes.get_last_error())
    actual=[outer.right-outer.left,outer.bottom-outer.top]  # Record native maxTrack clamping; never change production limits.
    rects={};widths={}
    for identifier in LAYOUT_CONTROLS:
        handle=api.editor(hwnd) if identifier==0 else api.control(hwnd,identifier)
        if not u.IsWindowVisible(handle):raise RuntimeError('Search layout control is hidden')
        r=wintypes.RECT()
        if not u.GetWindowRect(handle,ctypes.byref(r)):raise ctypes.WinError(ctypes.get_last_error())
        rects[str(identifier)]=[r.left-origin.x,r.top-origin.y,r.right-origin.x,r.bottom-origin.y]
        if identifier in (310,311):widths[str(identifier)]=80
        elif identifier in SEARCH_CONTROLS:
            text=api.text(handle);font=api.scalar(handle,0x31);dc=u.GetDC(handle)
            if not text or not font or not dc:raise RuntimeError('Search native text/font/DC unavailable')
            previous=None
            try:
                previous=gdi.SelectObject(dc,font)
                if not previous or previous==ctypes.c_void_p(-1).value:raise RuntimeError('Search native font selection failed')
                extent=wintypes.SIZE()
                if not gdi.GetTextExtentPoint32W(dc,text,len(text.encode('utf-16-le'))//2,ctypes.byref(extent)):raise ctypes.WinError(ctypes.get_last_error())
                widths[str(identifier)]=max(64,extent.cx+(44 if identifier in (306,309,312) else 26))
            finally:
                if previous and previous!=ctypes.c_void_p(-1).value:gdi.SelectObject(dc,previous)
                if not u.ReleaseDC(handle,dc):raise RuntimeError('Search native measurement DC release failed')
    return dict(language=language,scope=scope,requested=list(size),outer=actual,client=[client.right,client.bottom],rectangles=rects,
                minimum_widths=widths,scope_disabled=not bool(u.IsWindowEnabled(api.control(hwnd,316))))


def validate_result(record, hashes):
    if not isinstance(record,dict) or record.get('schema')!='ru-notepad-search-scope-gui-v1': raise ValueError('Search receipt schema differs')
    for row,name in ((record,'main-gui-search-scope'),(record.get('reopen'),'main-gui-search-reopen')):
        if not isinstance(row,dict) or row.get('name')!=name: raise ValueError('Search phase missing')
        for key,value in (('passed',True),('executed',True),('cleanup_killed',False),('main_hwnd_seen',True),('close_posted',True),('detached_from_console',True)):
            if row.get(key) is not value: raise ValueError('Search lifecycle differs')
        if type(row.get('exit_code')) is not int or row['exit_code']!=0 or row.get('error') or row.get('skips'): raise ValueError('Search phase failed or skipped')
        if row.get('fixture_binary_sha256')!=hashes: raise ValueError('Search runtime differs')
    if record.get('languages')!=list(LANGUAGES) or record.get('cases')!=expected_cases(): raise ValueError('Search inventory differs')
    if record.get('checks')!=dict.fromkeys(CHECKS,True) or any(v is not True for v in record['checks'].values()): raise ValueError('Search checks incomplete')
    for row in record['cases']:
        if any(v is not True for v in row['checks'].values()): raise ValueError('Search case check types differ')
    if type(record.get('large_bytes')) is not int or record['large_bytes']!=LARGE_BYTES: raise ValueError('Search large-mode fixture differs')
    validate_layouts(record.get('layouts'))
    value=record.get('large_search_seconds')
    if type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<5: raise ValueError('Search five-second bound failed')
    return True


def set_text(api, handle, value):
    # WM_SETTEXT is system-marshalled; never send process-local private pointers.
    buffer=ctypes.create_unicode_buffer(value)
    if not api.scalar(handle,12,0,ctypes.addressof(buffer)): raise RuntimeError('Search input setup failed')
    if api.text(handle)!=value: raise RuntimeError('Search input setup readback differs')


def run(api,binary_dir,fixtures,evidence):
    binary_dir,fixtures,evidence=map(Path,(binary_dir,fixtures,evidence))
    hashes={n:ci.sha(binary_dir/n) for n in ci.portable.RUNTIME_NAMES}
    paths=[]; progress=[dict(id=c['id'],source_sha256=hashlib.sha256(c['source']).hexdigest(),checks={}) for c in ALL_CASES]
    for c in ALL_CASES:
        path=fixtures/('search-'+c['id']+'.txt');path.write_bytes(c['source']);paths.append(path)
    large=fixtures/'search-large.txt';large.write_bytes(b'x'*1048576+b' needle '+b'x'*(LARGE_BYTES-1048584));large_hash=ci.sha(large)
    opened=paths+[large]
    u=api.user
    u.IsWindowEnabled.argtypes=[wintypes.HWND];u.IsWindowEnabled.restype=wintypes.BOOL
    u.GetMenu.argtypes=[wintypes.HWND];u.GetMenu.restype=ctypes.c_void_p
    u.GetMenuStringW.argtypes=[ctypes.c_void_p,ctypes.c_uint,wintypes.LPWSTR,ctypes.c_int,ctypes.c_uint];u.GetMenuStringW.restype=ctypes.c_int
    def menu(hwnd,command):
        buf=ctypes.create_unicode_buffer(2048);u.GetMenuStringW(u.GetMenu(hwnd),command,buf,len(buf),0);return buf.value
    def loaded(process,hwnd,last):
        ci.wait_gui(api,process,lambda:api.text(hwnd)==last.name+' · ru_notepad' and bool(u.IsWindowEnabled(api.control(hwnd,10))) and not u.IsWindowVisible(api.control(hwnd,901)), 'Search fixture batch did not finish')
    def selection(hwnd): return tuple(api.scalar(api.editor(hwnd),m) for m in (2143,2145))
    def state(hwnd): return (api.editor_bytes(hwnd),)+tuple(api.scalar(api.editor(hwnd),m) for m in (2008,2009,2159,2174))
    def inputs(hwnd,find,replacement=''):
        set_text(api,api.control(hwnd,310),find);set_text(api,api.control(hwnd,311),replacement)
    def scope(hwnd,low,high,reverse=False):
        api.scalar(api.editor(hwnd),2160,high if reverse else low,low if reverse else high);api.command(hwnd,313)
    active_process=[]; active_catalog=[]; modal_probe=[]
    def dialog_command(hwnd,command,key,number=None):
        process=active_process[0]; catalog=active_catalog[0]
        expected=catalog[key]['en']
        if number is not None: expected=expected.replace('{0}',str(number))
        _post_command(api,hwnd,command)
        deadline=time.monotonic()+10; found=None
        while time.monotonic()<deadline:
            if process.poll() is not None: raise RuntimeError('Search exited while waiting for expected information dialog')
            dialogs=[h for h,c,v in api.windows(process.pid) if c=='#32770' and v]
            if len(dialogs)==1:
                shape=_information_dialog(api,process,dialogs[0],deadline)
                button=_information_shape(shape,hwnd,{expected})
                if button is None: raise RuntimeError('Search dialog owner/text/button shape differs: '+key)
                found=(dialogs[0],button); break
            time.sleep(.01)
        if found is None: raise RuntimeError('Search information dialog missing: '+key)
        if not modal_probe:
            before=state(hwnd); texts=tuple(api.text(api.control(hwnd,n)) for n in (310,311,316))
            for blocked in (313,314,315,1700,1720,303,308,304,305): api.command(hwnd,blocked)
            if state(hwnd)!=before or tuple(api.text(api.control(hwnd,n)) for n in (310,311,316))!=texts:
                raise RuntimeError('Search command bypassed active modal guard')
            modal_probe.append(True)
        api.verify_owned_handles(process.pid,hwnd,*found)
        if not u.PostMessageW(found[1],0xF5,0,0): raise ctypes.WinError(ctypes.get_last_error())
        _wait(api,process,lambda:not u.IsWindowVisible(found[0]),'search information dismissed',10,dialogs=True)
        api.responsive(hwnd)
    def unchanged(hwnd,command,key=None):
        before=state(hwnd)
        if key:dialog_command(hwnd,command,key)
        else:api.command(hwnd,command)
        if state(hwnd)!=before: raise RuntimeError('Blocked search command changed text/selection/Undo: '+str(command))
    def invalid(hwnd):
        unchanged(hwnd,303,'search.scope_required');unchanged(hwnd,308,'search.scope_required');unchanged(hwnd,304,'search.replace_unavailable');unchanged(hwnd,305,'search.replace_unavailable')
    def exercise(process,hwnd):
        checks={};layouts=[]
        active_process.append(process)
        loaded(process,hwnd,large)
        catalog=json.loads((ROOT/'locales/ui.json').read_text(encoding='utf-8'));active_catalog.append(catalog)
        activate_source(api,hwnd,paths[0],len(opened));api.command(hwnd,301)
        for index,language in enumerate(LANGUAGES):
            api.command(hwnd,851+index)
            for command,key in ((313,'search.capture_selection'),(314,'search.current_document'),(315,'search.clear_history')):
                if menu(hwnd,command)!=catalog[key][language]: raise RuntimeError('Search menu translation differs')
            scope(hwnd,ALL_CASES[0]['low'],ALL_CASES[0]['high'])
            if api.text(api.control(hwnd,316))!=catalog['search.scope_selection'][language]: raise RuntimeError('Selection-only label missing')
            layouts.extend(native_layout(api,hwnd,language,'selection',size) for size in LAYOUT_SIZES)
            api.command(hwnd,307);api.command(hwnd,301)
            if api.text(api.control(hwnd,316))!=catalog['search.scope_invalid'][language]: raise RuntimeError('Invalid scope label missing')
            layouts.extend(native_layout(api,hwnd,language,'invalid',size) for size in LAYOUT_SIZES)
            api.command(hwnd,314)
            if api.text(api.control(hwnd,316))!=catalog['search.scope_document'][language]: raise RuntimeError('Document scope label missing')
            layouts.extend(native_layout(api,hwnd,language,'document',size) for size in LAYOUT_SIZES)
        validate_layouts(layouts);checks['seven_language_layout']=True
        checks['seven_languages']=True
        api.command(hwnd,851)
        for i,(path,c) in enumerate(zip(paths,ALL_CASES)):
            activate_source(api,hwnd,path,len(opened));api.command(hwnd,301);inputs(hwnd,c['pattern'])
            for control,value in ((306,c['case']),(309,c['whole']),(312,c['wrap'])):api.scalar(api.control(hwnd,control),241,int(value))
            scope(hwnd,c['low'],c['high'],c['reverse']);progress[i]['checks']['captured_direction']=True
            api.scalar(api.editor(hwnd),2160,c['caret'],c['caret'])
            before=state(hwnd)
            if c['expected'] is None:dialog_command(hwnd,308 if c['backwards'] else 303,'search.no_match')
            else:api.command(hwnd,308 if c['backwards'] else 303)
            expect=c['expected'] or (c['caret'],c['caret'])
            if selection(hwnd)!=expect: raise RuntimeError('Scoped search exact match differs: '+c['id']+' '+str(selection(hwnd))+' expected '+str(expect))
            for position in selection(hwnd):c['source'][:position].decode()
            if api.editor_bytes(hwnd)!=c['source'] or tuple(api.scalar(api.editor(hwnd),m) for m in (2159,2174))!=(0,0): raise RuntimeError('Scoped search changed text/Undo')
            if path.read_bytes()!=c['source']:raise RuntimeError('Search implicitly saved')
            for key in ('exact_match','utf8_boundary','text_undo_unchanged','disk_unchanged'):progress[i]['checks'][key]=True
            save_and_verify(api,process,hwnd,path,c['source']);progress[i]['checks']['saved_exact']=True
        checks['outside_caret_clamped']=True
        # Fixed range is exercised repeatedly, including wrap and out-of-range caret.
        activate_source(api,hwnd,paths[0],len(opened));c=ALL_CASES[0];inputs(hwnd,c['pattern'],'REPLACED')
        for control,value in ((306,1),(309,0),(312,1)):api.scalar(api.control(hwnd,control),241,value)
        scope(hwnd,c['low'],c['high']);expected=(c['low'],c['low']+len(c['pattern'].encode()))
        api.command(hwnd,303)
        if selection(hwnd)!=expected:raise RuntimeError('Initial scope wrap differs')
        api.command(hwnd,303)
        if selection(hwnd)!=(c['high']-len(c['pattern'].encode()),c['high']):raise RuntimeError('Match selection shrank captured range')
        api.command(hwnd,303)
        if selection(hwnd)!=expected:raise RuntimeError('Scoped wrap escaped fixed range')
        checks['fixed_scope_repeated']=True
        api.scalar(api.control(hwnd,312),241,0)
        api.scalar(api.editor(hwnd),2160,c['high'],c['high']);unchanged(hwnd,303,'search.no_match')
        api.scalar(api.editor(hwnd),2160,c['low'],c['low']);unchanged(hwnd,308,'search.no_match')
        checks['nowrap_boundaries']=True
        api.scalar(api.control(hwnd,312),241,1);api.command(hwnd,303)
        for command in (304,305):unchanged(hwnd,command,'search.replace_unavailable')
        for control in (304,305):
            if u.IsWindowEnabled(api.control(hwnd,control)):raise RuntimeError('Scoped replace button enabled')
        checks['replacement_blocked']=True
        # F3 enters the real app GetMessage/shortcut path without global input.
        before=selection(hwnd)
        if not u.PostMessageW(api.control(hwnd,310),0x100,0x72,1):raise ctypes.WinError(ctypes.get_last_error())
        ci.wait_gui(api,process,lambda:selection(hwnd)!=before,'F3 did not traverse actual shortcut loop')
        if selection(hwnd)!=(c['high']-len(c['pattern'].encode()),c['high']):raise RuntimeError('F3 escaped scope')
        checks['f3_message_loop']=True
        api.scalar(api.editor(hwnd),2160,0,0);dialog_command(hwnd,313,'search.selection_required');invalid(hwnd);checks['empty_capture_invalid']=True
        scope(hwnd,c['low'],c['high']);api.scalar(api.editor(hwnd),2422,1)
        dialog_command(hwnd,313,'search.selection_required');api.scalar(api.editor(hwnd),2422,0);invalid(hwnd);checks['rectangular_capture_invalid']=True
        scope(hwnd,c['low'],c['high']);api.scalar(api.editor(hwnd),2573,0,0)
        dialog_command(hwnd,313,'search.selection_required');api.scalar(api.editor(hwnd),2571);invalid(hwnd);checks['multiple_capture_invalid']=True
        scope(hwnd,c['low'],c['high']);api.command(hwnd,307);api.command(hwnd,301);invalid(hwnd);checks['close_reopen_invalid']=True
        scope(hwnd,c['low'],c['high']);api.command(hwnd,112);api.command(hwnd,111);invalid(hwnd);checks['tab_invalid']=True
        scope(hwnd,c['low'],c['high']);api.command(hwnd,105);invalid(hwnd)
        api.drop(hwnd,[paths[0]]);loaded(process,hwnd,paths[0]);invalid(hwnd)
        if api.editor_bytes(hwnd)!=c['source']:raise RuntimeError('Closed captured tab did not reopen exactly')
        checks['close_tab_reopen_invalid']=True
        scope(hwnd,c['low'],c['high']);api.scalar(api.editor(hwnd),0x102,ord('X'),1)  # real WM_CHAR; synthetic editor only
        invalid(hwnd);api.command(hwnd,201);invalid(hwnd)
        if api.editor_bytes(hwnd)!=c['source']:raise RuntimeError('Character edit/Undo lifecycle did not restore source')
        checks['edit_undo_invalid']=True
        api.command(hwnd,314);api.scalar(api.editor(hwnd),2160,0,0);api.command(hwnd,303)
        if selection(hwnd)!=(0,len(c['pattern'].encode())):raise RuntimeError('Explicit document scope recovery failed')
        checks['explicit_document_recovery']=True
        api.scalar(api.editor(hwnd),2171,1)
        try:
            unchanged(hwnd,304,'search.replace_unavailable');unchanged(hwnd,305,'search.replace_unavailable')
            api.command(hwnd,303)
            if selection(hwnd)!=expected:raise RuntimeError('Read-only document find unavailable')
            scope(hwnd,c['low'],c['high']);api.command(hwnd,303)
            if selection(hwnd)!=expected:raise RuntimeError('Read-only scoped find unavailable')
            unchanged(hwnd,304,'search.replace_unavailable');unchanged(hwnd,305,'search.replace_unavailable')
            if any(u.IsWindowEnabled(api.control(hwnd,n)) for n in (304,305)):raise RuntimeError('Read-only replace controls enabled')
        finally:api.scalar(api.editor(hwnd),2171,0)
        checks['readonly_find_replace_guard']=True
        api.command(hwnd,314);inputs(hwnd,'');unchanged(hwnd,303);checks['empty_pattern_no_mutation']=True
        # Histories are separate, bounded MRUs, and selection only fills a field.
        api.command(hwnd,315)
        for n in range(14):inputs(hwnd,'absent-'+str(n));dialog_command(hwnd,303,'search.no_match')
        if not menu(hwnd,1700) or not menu(hwnd,1711) or menu(hwnd,1712):raise RuntimeError('Find MRU is not exactly twelve bounded entries')
        before=state(hwnd);api.command(hwnd,1711)
        if api.text(api.control(hwnd,310))!='absent-2' or state(hwnd)!=before:raise RuntimeError('Oldest MRU/reselect differs')
        dialog_command(hwnd,303,'search.no_match');api.command(hwnd,1700)
        if api.text(api.control(hwnd,310))!='absent-2':raise RuntimeError('MRU dedup/promotion failed')
        api.command(hwnd,1711)
        if api.text(api.control(hwnd,310))!='absent-3':raise RuntimeError('MRU dedup consumed capacity')
        checks['history_mru_bound']=True;checks['history_reselect_no_execution']=True
        inputs(hwnd,'z'*1025);dialog_command(hwnd,303,'search.no_match');api.command(hwnd,1700)
        if api.text(api.control(hwnd,310))!='absent-2':raise RuntimeError('Oversize query collected in history')
        checks['history_oversize_excluded']=True
        for n in range(14):inputs(hwnd,'absent-replace','replacement-'+str(n));dialog_command(hwnd,305,'search.replacements',0)
        before=state(hwnd);api.command(hwnd,1731)
        if api.text(api.control(hwnd,311))!='replacement-2' or state(hwnd)!=before:raise RuntimeError('Replacement history bound/reselect differs')
        inputs(hwnd,'absent-replace','');dialog_command(hwnd,305,'search.replacements',0);inputs(hwnd,'absent-replace','temporary');api.command(hwnd,1720)
        if api.text(api.control(hwnd,311))!='':raise RuntimeError('Empty deletion replacement missing from history')
        checks['history_empty_replace']=True
        scope(hwnd,c['low'],c['high']);api.command(hwnd,307);api.command(hwnd,301);api.command(hwnd,1700);invalid(hwnd)
        api.command(hwnd,315)
        if api.text(api.control(hwnd,310)) or api.text(api.control(hwnd,311)) or menu(hwnd,1700) or menu(hwnd,1720):raise RuntimeError('Clear did not erase both histories and inputs')
        checks['history_clear']=True
        api.command(hwnd,314);inputs(hwnd,c['pattern'],'R');dialog_command(hwnd,305,'search.replacements',4)
        if api.editor_bytes(hwnd)!=c['source'].replace(c['pattern'].encode(),b'R'):raise RuntimeError('Document replace-all incorrect')
        api.command(hwnd,201)
        if api.editor_bytes(hwnd)!=c['source'] or api.scalar(api.editor(hwnd),2159):raise RuntimeError('Replace-all lost one-step Undo/savepoint')
        checks['replace_all_one_undo']=True
        # Big document remains search-only; no new product limit or byte rewrite.
        activate_source(api,hwnd,large,len(opened));api.command(hwnd,314);inputs(hwnd,'needle');scope(hwnd,1048576,1048584)
        start=time.perf_counter();api.command(hwnd,303);duration=time.perf_counter()-start
        if selection(hwnd)!=(1048577,1048583) or duration>=5:raise RuntimeError('Large scoped search failed bounded lookup')
        if api.scalar(api.editor(hwnd),2159) or api.scalar(api.editor(hwnd),2174) or ci.sha(large)!=large_hash:raise RuntimeError('Large find changed document/disk')
        api.no_dialog(process.pid)
        checks['large_search_bounded']=True
        if modal_probe!=[True]:raise RuntimeError('Modal command guard was not exercised')
        checks['modal_command_guard']=True
        return dict(checks=checks,layouts=layouts,languages=list(LANGUAGES),large_bytes=LARGE_BYTES,large_search_seconds=duration)
    def reopen(process,hwnd):
        loaded(process,hwnd,paths[-1]);api.command(hwnd,301)
        if menu(hwnd,1700) or menu(hwnd,1720) or api.text(api.control(hwnd,310)) or api.text(api.control(hwnd,311)):raise RuntimeError('Search history persisted across launches')
        result['checks']['history_restart_empty']=True
        for i,(path,c) in enumerate(zip(paths,ALL_CASES)):
            activate_source(api,hwnd,path,len(paths))
            if api.editor_bytes(hwnd)!=c['source'] or path.read_bytes()!=c['source'] or api.scalar(api.editor(hwnd),2159):raise RuntimeError('Search exact fresh reopen differs')
            progress[i]['checks']['fresh_reopen']=True
        return {}
    target=fixtures/'search-runtime';_copy_runtime(binary_dir,target,hashes)
    with isolated_settings():
        result=ci.run_gui(api,target,evidence,name='main-gui-search-scope',arguments=opened,exercise=exercise,log_prefix='search-scope')
        result.update(schema='ru-notepad-search-scope-gui-v1',fixture_binary_sha256=hashes,cases=progress)
        if result['passed']:
            target=fixtures/'search-reopen-runtime';_copy_runtime(binary_dir,target,hashes)
            result['reopen']=ci.run_gui(api,target,evidence,name='main-gui-search-reopen',arguments=paths,exercise=reopen,log_prefix='search-reopen')
            result['reopen']['fixture_binary_sha256']=hashes
            if result['reopen']['passed']:validate_result(result,hashes)
            else:result.update(passed=False,error='Search fresh-process reopen failed; see nested receipt')
    return result
