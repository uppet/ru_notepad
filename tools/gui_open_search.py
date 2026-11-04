#!/usr/bin/env python3
"""Synthetic Windows Find All gate; portable receipt tests are NOT GUI evidence.

run() uses the existing owned-process Windows API and isolated fixtures/settings.
Tick budgets, identity bookkeeping, allocation failures and tab permutation need
companion native engine tests; this black-box gate does not claim those proofs.
Reconstructed from reviewed task history after the old workspace was lost.
"""
import ctypes
from ctypes import wintypes
import hashlib
import json
from pathlib import Path
import re
import time
import windows_ci as ci
from gui_instance_tabs import isolated_settings, _copy_runtime
from gui_search_scope import set_text, disjoint, SEARCH_CONTROLS

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ('en', 'zh-CN', 'ja', 'ko', 'es', 'ru', 'it')
START, STOP, HIDE, LIST, SUMMARY, OPEN = 317, 318, 319, 320, 321, 322
MAX_ROWS, STARTS_PER_TICK, HITS_PER_TICK, TIMER_MS = 2000, 65536, 16, 20
LAYOUT_SIZES = ((640, 400), (1120, 760))
RESULT_CONTROLS = (LIST, SUMMARY, OPEN, STOP, HIDE)
CHECKS = ('literal_matrix', 'duplicate_basename_identity', 'dirty_live_buffer',
          'untitled_live_buffer', 'readonly_find', 'no_implicit_mutation',
          'exact_byte_navigation', 'enter_navigation', 'double_click_navigation',
          'unfold_endpoints', 'cancel', 'repeat_start', 'hide_cancels',
          'independent_search_bar', 'edit_invalidates', 'undo_does_not_revive',
          'close_reopen_invalidates', 'row_cap', 'empty_query',
          'seven_language_layout', 'disk_unchanged')
ENGINE_GATES = ('65536_candidate_starts_per_tick', '16_hits_per_tick', '20ms_timer',
                '2000_row_cap', 'identity_revision_byte_ranges',
                'reorder_preserves_identity', 'failed_status_and_cleanup',
                'literal_only_no_disk_reads_no_replacement',
                'case_sensitive_4096_casefold_12288_lookahead')
# These are disclosures, not fabricated required/achieved native UI flows.
MANUAL_GATES = ('No tab-reorder UI exists; native unit coverage verifies document permutation.',
                'No native allocation-failure injection is performed; native unit coverage verifies internal failure status.')


def fixtures():
    return {
        'left/same.txt': 'A|CAT scatter _cat cat\r\n汉😀\r\n乙\r\n'.encode(),
        'right/same.txt': 'B|cat Cat cat_\n汉😀\n乙\n'.encode(),
        'cr.txt': 'C|cat\r汉😀\r乙\r'.encode(),
        'fold.c': b'int main(void) {\n  /* endpoint needle */\n  return 0;\n}\n',
        'boundary.txt': b'x' * 65534 + '汉😀edge'.encode() + b' y',
        'casefold.txt': b'z' * 65533 + 'Straße'.encode() + b' end',
        'cap.txt': b' capword' * (MAX_ROWS + 1),
        'slow.txt': b'x' * (4 * 1024 * 1024),
    }


def cases():
    # Explicit fixture expectations, not a replacement for Scintilla semantics.
    return (
        ('case', 'cat', True, False, 6),
        ('nocase', 'cat', False, False, 8),
        ('word', 'cat', True, True, 3),
        ('word-nocase', 'cat', False, True, 5),
        ('unicode', '汉😀', True, False, 4),
        ('crlf', '汉😀\r\n乙', True, False, 1),
        ('lf', '汉😀\n乙', True, False, 1),
        ('cr', '汉😀\r乙', True, False, 1),
        ('boundary', '汉😀edge', True, False, 1),
        ('fold-expansion-boundary', 'STRASSE', False, False, 1),
        ('literal-not-regex', 'cat.*', True, False, 0),
        ('no-match', 'absent-acceptance-needle', True, False, 0),
    )


def inventory():
    return [{'id': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
            for name, data in fixtures().items()]


def expected_ranges(data, query, match_case, whole):
    """Bounded synthetic-fixture oracle only; production uses Scintilla."""
    if query == 'STRASSE' and not match_case and not whole:
        source = 'Straße'.encode(); at = data.find(source)
        return [] if at < 0 else [(at, at + len(source))]
    needle = query.encode(); haystack = data
    if not match_case:
        if not needle.isascii(): raise ValueError('Unicode folding is not this oracle')
        haystack, needle = haystack.lower(), needle.lower()
    if not needle: raise ValueError('Empty query is not a fixture search')
    found = []; offset = 0
    word = lambda byte: byte == 95 or 48 <= byte <= 57 or 65 <= byte <= 90 or 97 <= byte <= 122
    while True:
        at = haystack.find(needle, offset)
        if at < 0: return found
        end = at + len(needle)
        if not whole or ((at == 0 or not word(data[at-1])) and (end == len(data) or not word(data[end]))):
            found.append((at, end))
        offset = end


def validate_layouts(rows):
    identities = [(language, list(size), bar) for language in LANGUAGES for size in LAYOUT_SIZES for bar in (False, True)]
    if not isinstance(rows, list) or len(rows) != len(identities): raise ValueError('Open search layout inventory differs')
    fields = {'language','requested','search_bar','client','outer','rectangles','minimum_widths','list_item_height','list_client_height'}
    for row, identity in zip(rows, identities):
        if not isinstance(row, dict) or set(row) != fields: raise ValueError('Open search layout fields differ')
        if (row['language'], row['requested'], row['search_bar']) != identity or type(row['search_bar']) is not bool:
            raise ValueError('Open search layout identity differs')
        for key in ('client','outer'):
            if not isinstance(row[key], list) or len(row[key]) != 2 or any(type(n) is not int or n <= 0 for n in row[key]):
                raise ValueError('Invalid native dimensions')
        item_height = row['list_item_height']; list_height = row['list_client_height']
        if type(item_height) is not int or item_height <= 0 or type(list_height) is not int or list_height < item_height:
            raise ValueError('Result list cannot display one complete native row')
        w, h = row['client']; ow, oh = row['outer']
        if not (640 <= ow <= row['requested'][0] and 400 <= oh <= row['requested'][1] and w <= ow and h <= oh):
            raise ValueError('Unsupported outer/client dimensions')
        ids = (0, 10, 11) + RESULT_CONTROLS + (SEARCH_CONTROLS if row['search_bar'] else ())
        if not isinstance(row['rectangles'], dict) or not isinstance(row['minimum_widths'], dict): raise ValueError('Invalid control geometry maps')
        if set(row['rectangles']) != set(map(str, ids)) or set(row['minimum_widths']) != set(map(str, (OPEN, STOP, HIDE))):
            raise ValueError('Open search control inventory differs')
        for key, rect in row['rectangles'].items():
            if not isinstance(rect, list) or len(rect) != 4 or any(type(n) is not int for n in rect): raise ValueError('Invalid native rectangle')
            if not (0 <= rect[0] < rect[2] <= w and 0 <= rect[1] < rect[3] <= h): raise ValueError('Result control outside client')
            if key in row['minimum_widths']:
                minimum = row['minimum_widths'][key]
                if type(minimum) is not int or minimum <= 0 or rect[2]-rect[0] < minimum: raise ValueError('Translated button clipped')
        rects = list(row['rectangles'].values())
        if any(not disjoint(a,b) for i,a in enumerate(rects) for b in rects[i+1:]): raise ValueError('Open search controls overlap')
        list_rect = row['rectangles'][str(LIST)]
        if list_height > list_rect[3]-list_rect[1]: raise ValueError('Result list client exceeds outer rectangle')
        if row['rectangles']['0'][3] > list_rect[1]: raise ValueError('Results must be below editor')
        if row['search_bar'] and list_rect[3] > row['rectangles']['310'][1]: raise ValueError('Results must be above search bar')
    return True


def validate_result(row, hashes):
    if not isinstance(row, dict) or row.get('schema') != 'ru-notepad-open-search-gui-v1' or row.get('name') != 'main-gui-open-search':
        raise ValueError('Open search receipt identity differs')
    for key,value in (('passed',True),('executed',True),('cleanup_killed',False),('main_hwnd_seen',True),('close_posted',True),('detached_from_console',True)):
        if row.get(key) is not value: raise ValueError('Open search lifecycle failed')
    if type(row.get('exit_code')) is not int or row['exit_code'] != 0 or row.get('error') or row.get('skips'):
        raise ValueError('Open search failed or skipped')
    if row.get('fixture_binary_sha256') != hashes or row.get('fixtures') != inventory(): raise ValueError('Open search fixture/runtime identity differs')
    if row.get('checks') != dict.fromkeys(CHECKS,True) or any(v is not True for v in row['checks'].values()): raise ValueError('Open search checks incomplete')
    if row.get('cases') != [c[0] for c in cases()]: raise ValueError('Open search case inventory differs')
    if row.get('engine_gates') != list(ENGINE_GATES) or row.get('manual_gates') != list(MANUAL_GATES): raise ValueError('Companion gates must be disclosed')
    validate_layouts(row.get('layouts'))
    return True


def native_layout(api, hwnd, language, size, bar):
    u = api.user; gdi = ctypes.WinDLL('gdi32', use_last_error=True)
    u.MoveWindow.argtypes=[wintypes.HWND,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,wintypes.BOOL];u.MoveWindow.restype=wintypes.BOOL
    u.GetWindowRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)];u.GetWindowRect.restype=wintypes.BOOL
    u.ClientToScreen.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.POINT)];u.ClientToScreen.restype=wintypes.BOOL
    u.GetDC.argtypes=[wintypes.HWND];u.GetDC.restype=wintypes.HDC
    u.ReleaseDC.argtypes=[wintypes.HWND,wintypes.HDC];u.ReleaseDC.restype=ctypes.c_int
    gdi.SelectObject.argtypes=[wintypes.HDC,wintypes.HANDLE];gdi.SelectObject.restype=wintypes.HANDLE
    gdi.GetTextExtentPoint32W.argtypes=[wintypes.HDC,wintypes.LPCWSTR,ctypes.c_int,ctypes.POINTER(wintypes.SIZE)];gdi.GetTextExtentPoint32W.restype=wintypes.BOOL
    if not u.MoveWindow(hwnd,40,40,*size,True): raise ctypes.WinError(ctypes.get_last_error())
    api.responsive(hwnd); origin=wintypes.POINT();outer=wintypes.RECT();client=wintypes.RECT()
    if not u.GetWindowRect(hwnd,ctypes.byref(outer)) or not u.GetClientRect(hwnd,ctypes.byref(client)) or not u.ClientToScreen(hwnd,ctypes.byref(origin)):
        raise ctypes.WinError(ctypes.get_last_error())
    rects={}; widths={}
    for identifier in (0,10,11)+RESULT_CONTROLS+(SEARCH_CONTROLS if bar else ()):
        handle = api.editor(hwnd) if identifier == 0 else api.control(hwnd,identifier)
        if not u.IsWindowVisible(handle): raise RuntimeError('Required result control hidden')
        r=wintypes.RECT()
        if not u.GetWindowRect(handle,ctypes.byref(r)): raise ctypes.WinError(ctypes.get_last_error())
        rects[str(identifier)]=[r.left-origin.x,r.top-origin.y,r.right-origin.x,r.bottom-origin.y]
        if identifier in (OPEN,STOP,HIDE):
            label=api.text(handle);font=api.scalar(handle,0x31);dc=u.GetDC(handle);previous=None
            if not label or not font or not dc: raise RuntimeError('Native result label/font/DC unavailable')
            try:
                previous=gdi.SelectObject(dc,font);extent=wintypes.SIZE()
                if not previous or previous==ctypes.c_void_p(-1).value: raise RuntimeError('Native result font unavailable')
                if not gdi.GetTextExtentPoint32W(dc,label,len(label.encode('utf-16-le'))//2,ctypes.byref(extent)): raise ctypes.WinError(ctypes.get_last_error())
                widths[str(identifier)]=extent.cx+20
            finally:
                if previous and previous!=ctypes.c_void_p(-1).value:gdi.SelectObject(dc,previous)
                u.ReleaseDC(handle,dc)
    list_handle=api.control(hwnd,LIST);list_client=wintypes.RECT()
    if not u.GetClientRect(list_handle,ctypes.byref(list_client)): raise ctypes.WinError(ctypes.get_last_error())
    item_height=api.scalar(list_handle,0x1A1,0)  # LB_GETITEMHEIGHT, native pixels
    return dict(list_item_height=item_height,list_client_height=list_client.bottom-list_client.top,
                language=language,requested=list(size),search_bar=bar,outer=[outer.right-outer.left,outer.bottom-outer.top],
                client=[client.right,client.bottom],rectangles=rects,minimum_widths=widths)


def run(api, binary_dir, fixtures_dir, evidence):
    binary_dir,fixtures_dir,evidence=map(Path,(binary_dir,fixtures_dir,evidence))
    sources=fixtures(); paths={}
    for name,data in sources.items():
        path=fixtures_dir/'open-search'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);paths[name]=path
    hashes={name:ci.sha(binary_dir/name) for name in ci.portable.RUNTIME_NAMES}
    target=fixtures_dir/'open-search-runtime';_copy_runtime(binary_dir,target,hashes)
    def exercise(process,hwnd):
        checks={};layouts=[];handles={}
        ci.wait_gui(api,process,lambda:api.text(hwnd)==paths['slow.txt'].name+' · ru_notepad' and not api.user.IsWindowVisible(api.control(hwnd,901)), 'Open search fixtures not loaded')
        # Identity by length and bounded prefix, never ambiguous basename alone.
        for _ in range(len(paths)+1):
            editor=api.editor(hwnd);length=api.scalar(editor,2006)
            prefix=bytes(api.scalar(editor,2007,i)&255 for i in range(min(32,length)))
            for name,data in sources.items():
                if len(data)==length and data[:32]==prefix:handles[name]=editor
            api.command(hwnd,112)
        if set(handles)!=set(sources):raise RuntimeError('Synthetic documents missing or ambiguous')
        def activate(handle):
            for _ in range(len(paths)+3):
                if api.editor(hwnd)==handle:return
                api.command(hwnd,112)
            raise RuntimeError('Expected live editor no longer reachable')
        def state(handle):
            # Big fixtures use bounded probes, NOT a claimed live-buffer hash.
            length=api.scalar(handle,2006)
            positions=range(length) if length<=4096 else sorted(p for p in {0,1,length-1,65534,65535,65536} if 0<=p<length)
            data=bytes(api.scalar(handle,2007,p)&255 for p in positions)
            return (hashlib.sha256(data).hexdigest(),length)+tuple(api.scalar(handle,m) for m in (2008,2009,2159,2174,2016,2152,2398,2191,2193,2199))
        def snapshot():return dict(active_editor=api.editor(hwnd),documents={name:state(handle) for name,handle in handles.items()})
        def count():return api.scalar(api.control(hwnd,LIST),0x18B)
        def summary():return api.text(api.control(hwnd,SUMMARY))
        catalog=json.loads((ROOT/'locales/open_search.json').read_text(encoding='utf-8'))
        def has_status(status):
            key='search.results_'+status
            if key not in catalog:raise RuntimeError('Missing required summary catalog key: '+key)
            pattern=re.escape(catalog[key]['en']);pattern=re.sub(r'\\\{\d+\\\}',r'\\d+',pattern)
            return re.fullmatch(pattern,summary()) is not None
        def finish(status='complete'):
            ci.wait_gui(api,process,lambda:has_status(status),'Open search did not reach '+status,timeout=30)
            api.no_dialog(process.pid)
        def start(query,case=True,whole=False):
            api.command(hwnd,301);set_text(api,api.control(hwnd,310),query)
            for control,value in ((306,case),(309,whole)):api.scalar(api.control(hwnd,control),241,int(value))
            api.command(hwnd,START)
        def navigate(index):
            result=api.scalar(api.control(hwnd,LIST),0x186,index)
            if result!=index:raise RuntimeError('Result row could not be selected')
            api.command(hwnd,OPEN)
            return api.editor(hwnd),tuple(api.scalar(api.editor(hwnd),m) for m in (2143,2145))
        api.command(hwnd,851)
        # Opening panels resizes the viewport. Establish final geometry before
        # strict engine nonmutation comparisons; no timer navigation is allowed.
        start('absent-acceptance-needle');finish();api.responsive(hwnd)
        for name,query,case,whole,total in cases():
            before=snapshot();start(query,case,whole);finish()
            if count()!=total or snapshot()!=before:raise RuntimeError('Literal count or nonmutation failed: '+name)
            expected={(handles[k],a,b) for k,data in sources.items() for a,b in expected_ranges(data,query,case,whole)}
            observed=set()
            for index in range(total):
                handle,(a,b)=navigate(index);observed.add((handle,a,b))
            if observed!=expected or len(observed)!=total:raise RuntimeError('Result byte range or document identity differs: '+name)
        checks['literal_matrix']=True;checks['duplicate_basename_identity']=True
        checks['no_implicit_mutation']=True;checks['exact_byte_navigation']=True
        activate(handles['cr.txt']);api.scalar(api.editor(hwnd),2171,1)
        try:
            before=snapshot();start('汉😀');finish()
            if count()!=4 or snapshot()!=before:raise RuntimeError('Read-only search failed')
        finally:api.scalar(handles['cr.txt'],2171,0)
        checks['readonly_find']=True
        activate(handles['cr.txt']);api.scalar(api.editor(hwnd),2160,0,0)
        for char in 'dirtyneedle ':api.scalar(api.editor(hwnd),0x102,ord(char),1)
        before=snapshot();start('dirtyneedle');finish()
        if count()!=1 or snapshot()!=before or not api.scalar(handles['cr.txt'],2159):raise RuntimeError('Dirty buffer was not searched in place')
        checks['dirty_live_buffer']=True
        activate(handles['cr.txt'])
        while api.scalar(api.editor(hwnd),2174):api.command(hwnd,201)
        api.command(hwnd,101);untitled=api.editor(hwnd);handles['untitled']=untitled
        for char in 'untitledneedle':api.scalar(untitled,0x102,ord(char),1)
        before=snapshot();start('untitledneedle');finish()
        if count()!=1 or snapshot()!=before or navigate(0)!=(untitled,(0,14)):raise RuntimeError('Untitled live result differs')
        checks['untitled_live_buffer']=True
        activate(untitled)
        while api.scalar(untitled,2174):api.command(hwnd,201)
        api.command(hwnd,105);del handles['untitled']
        activate(handles['fold.c'])
        ci.wait_gui(api,process,lambda:bool(api.scalar(api.editor(hwnd),2223,0)&0x2000),'Fold fixture header not ready')
        api.command(hwnd,505)
        if api.scalar(api.editor(hwnd),2228,1):raise RuntimeError('Fold fixture did not collapse before navigation')
        start('endpoint needle');finish();navigate(0)
        a,b=tuple(api.scalar(api.editor(hwnd),m) for m in (2143,2145))
        for position in (a,b):
            line=api.scalar(api.editor(hwnd),2166,position)
            if not api.scalar(api.editor(hwnd),2228,line):raise RuntimeError('Result endpoint remained folded')
        checks['unfold_endpoints']=True
        expected=(a,b);editor=api.editor(hwnd);result_list=api.control(hwnd,LIST)
        api.scalar(editor,2160,0,0);api.scalar(result_list,0x186,0)
        api.verify_owned_handles(process.pid,hwnd,editor,result_list)
        if not api.user.PostMessageW(result_list,0x100,13,1):raise ctypes.WinError(ctypes.get_last_error())
        ci.wait_gui(api,process,lambda:tuple(api.scalar(editor,m) for m in (2143,2145))==expected,'Enter did not navigate result through message loop')
        checks['enter_navigation']=True
        api.scalar(editor,2160,0,0);api.scalar(result_list,0x197,0)  # LB_SETTOPINDEX
        try:
            api.scalar(result_list,0x203,1,5|(5<<16))  # owned LISTBOX WM_LBUTTONDBLCLK
        finally:
            api.scalar(result_list,0x202,0,5|(5<<16))  # matching button-up releases capture
        if tuple(api.scalar(editor,m) for m in (2143,2145))!=expected:raise RuntimeError('Native list double-click did not navigate')
        checks['double_click_navigation']=True
        for action,key in ((STOP,'cancel'),(HIDE,'hide_cancels')):
            before=snapshot();start('absent-acceptance-needle');api.command(hwnd,action)
            finish('cancelled')
            if action==HIDE and api.user.IsWindowVisible(api.control(hwnd,LIST)):raise RuntimeError('Hide did not hide results')
            stopped_count=count();time.sleep(.1);api.responsive(hwnd)
            if snapshot()!=before or count()!=stopped_count or not has_status('cancelled'):raise RuntimeError('Cancellation changed document state or search kept running')
            checks[key]=True
        start('absent-acceptance-needle');start('汉😀');finish()
        if count()!=4:raise RuntimeError('Repeated start retained old rows or job')
        checks['repeat_start']=True
        start('capword');finish('limited')
        if count()!=MAX_ROWS:raise RuntimeError('Result row cap differs')
        checks['row_cap']=True
        start('cat');finish()
        for index in range(count()):
            if navigate(index)[0]==handles['cr.txt']:break
        else:raise RuntimeError('Missing stale-test result')
        api.scalar(api.editor(hwnd),2160,0,0)
        api.scalar(api.editor(hwnd),0x102,ord('Z'),1);before=snapshot()
        api.command(hwnd,OPEN)
        if snapshot()!=before:raise RuntimeError('Stale edited result navigated')
        finish('stale');checks['edit_invalidates']=True
        api.command(hwnd,201);before=snapshot();api.command(hwnd,OPEN)
        if snapshot()!=before:raise RuntimeError('Undo revived stale result')
        checks['undo_does_not_revive']=True
        start('cat');finish()
        for index in range(count()):
            if navigate(index)[0]==handles['cr.txt']:break
        else:raise RuntimeError('Missing close/reopen result')
        api.command(hwnd,105)
        del handles['cr.txt'];api.drop(hwnd,[paths['cr.txt']])
        ci.wait_gui(api,process,lambda:api.text(hwnd)==paths['cr.txt'].name+' · ru_notepad','Closed fixture failed reopen')
        handles['cr.txt']=api.editor(hwnd);before=snapshot();api.command(hwnd,OPEN)
        if snapshot()!=before:raise RuntimeError('Closed/reopened identity revived result')
        finish('stale');checks['close_reopen_invalidates']=True
        before=snapshot();old_count=count();old_summary=summary();start('');api.responsive(hwnd)
        if snapshot()!=before or count()!=old_count or summary()!=old_summary:raise RuntimeError('Empty query discarded prior results or mutated documents')
        checks['empty_query']=True
        start('cat');finish()
        for index,language in enumerate(LANGUAGES):
            api.command(hwnd,851+index)
            for size in LAYOUT_SIZES:
                api.command(hwnd,307)
                if not api.user.IsWindowVisible(api.control(hwnd,LIST)):raise RuntimeError('Search bar hide also hid results')
                layouts.append(native_layout(api,hwnd,language,size,False))
                api.command(hwnd,301);layouts.append(native_layout(api,hwnd,language,size,True))
        validate_layouts(layouts);checks['independent_search_bar']=True;checks['seven_language_layout']=True
        if any(path.read_bytes()!=sources[name] for name,path in paths.items()):raise RuntimeError('Search wrote synthetic source files')
        checks['disk_unchanged']=True
        return dict(checks=checks,layouts=layouts,cases=[c[0] for c in cases()])
    with isolated_settings():
        result=ci.run_gui(api,target,evidence,name='main-gui-open-search',arguments=list(paths.values()),exercise=exercise,log_prefix='open-search')
    result.update(schema='ru-notepad-open-search-gui-v1',fixture_binary_sha256=hashes,fixtures=inventory(),
                  engine_gates=list(ENGINE_GATES),manual_gates=list(MANUAL_GATES))
    if result['passed']:validate_result(result,hashes)
    return result
