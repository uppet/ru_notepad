#!/usr/bin/env python3
"""Bounded regex Windows acceptance. Portable contracts are NOT execution proof.

All files are synthetic; no external user documents or private
Scintilla pointer messages are used. Ranges are explicit UTF-8 byte oracles,
not Python re (whose anchors, categories and Previous semantics differ).
"""
import ctypes
from ctypes import wintypes
import hashlib
import json
import math
from pathlib import Path
import time
import windows_ci as ci
from gui_instance_tabs import isolated_settings, _copy_runtime
from gui_fold_commands import activate_source, _Input
from gui_instance_tabs import _GUIThreadInfo
import gui_search_scope as scope_gui
import gui_open_search as open_gui

ROOT=Path(__file__).resolve().parents[1]
LANGUAGES=scope_gui.LANGUAGES
LAYOUT_SIZES=scope_gui.LAYOUT_SIZES
LITERAL, REGEX, STOP = 323,324,325
STRESS_BYTES=4*1024*1024
RESPONSE_SECONDS=2.0
CHECKS=('hidden_bar_shortcuts','mode_restore','strict_rejection','case_matrix','zero_progress','fixed_selection',
        'readonly','dirty_live','blocked_mutation','accepted_history','history_restart_empty','cancel_matrix',
        'input_responsiveness','limit_no_navigation','seven_language_layout','disk_unchanged')
CANCEL_ACTIONS=('stop','query','restart','scope','mode','wrap','history','clear_history','tab','edit','undo','bar_close','escape','caret','close_reopen')
ENGINE_GATES=('bounded_copy_vm_job_budgets','fresh_identity_revision_selection_validation',
              'scalar_cr_lf_progress','no_provisional_limit_navigation')
DISCLOSURES=('Portable receipt tests do not execute Windows.',
             'Layout samples cover seven languages and two sizes, not universal DPI coverage.',
             'Allocation-failure behavior has not been fault-injected; source cleanup review is not execution evidence.')


def cases():
    def c(name,source,pattern,expected,*,caret=0,backwards=False,wrap=False,scope=None):
        return dict(id=name,source=source.encode(),pattern=pattern,expected=expected,
                    caret=caret,backwards=backwards,wrap=wrap,scope=scope)
    return (
        c('alt-first','ab','(a|ab)',(0,1)),c('alt-long-first','ab','(ab|a)',(0,2)),
        c('greedy','aaa!','a*',(0,3)),c('lazy','aaa!','a*?',(0,0)),
        c('noncapturing','xy','(?:x|z)y',(0,2)),c('optional','b','a?b',(0,1)),
        c('unicode-range','汉😀乙','[汉-龥]',(0,3)),c('emoji-dot','😀x','.',(0,4)),
        c('combining-scalar','e\u0301','.',(0,1)),c('no-normalization','e\u0301','é',None),
        c('ascii-category','١2',r'\d',(2,3)),c('exact-case','Aa','a',(1,2)),
        c('crlf-dot','\r\nX','.',(2,3)),c('escaped-newlines','x\r\ny',r'\r\n',(1,3)),
        c('crlf-start','a\r\nb','^',(3,3),caret=1),
        c('crlf-end','a\r\nb','$',(4,4),caret=2),
        c('doc-start-not-scope','xabc',r'\Aabc',None,caret=1,scope=(1,4)),
        c('line-start-not-scope','xabc','^abc',None,caret=1,scope=(1,4)),
        c('doc-end-not-scope','abcx',r'abc\z',None,scope=(0,3)),
        c('line-end-not-scope','abcx','abc$',None,scope=(0,3)),
        c('scope-fits','xabcx','abc',(1,4),caret=1,scope=(1,4)),
        c('scope-clips','xabcx','abc',None,caret=1,scope=(1,3)),
        c('empty-anchors','','^$',(0,0)),
        c('previous-nonoverlap','ababa','aba',(0,3),caret=5,backwards=True),
        c('previous-ceiling','abc','abc',None,caret=2,backwards=True),
        c('previous-last','aba aba','aba',(4,7),caret=7,backwards=True),
        c('next-wrap','aba x','aba',(0,3),caret=5,wrap=True),
        c('previous-wrap','x aba','aba',(2,5),caret=0,backwards=True,wrap=True),
        c('no-wrap','aba x','aba',None,caret=5),
    )


REJECTED=(r'a{2}',r'a++',r'(a)\1',r'(?=a)',r'(?i)a',r'\p{L}',r'\q',r'(a?)*',r'()+',r'[')

def fixtures():
    return {**{c['id']+'.txt':c['source'] for c in cases()},
            'zero.txt':'😀\r\n'.encode(),'fixed.txt':b'x a a x a',
            'stress.txt':b'a'*STRESS_BYTES}


def inventory():
    return [dict(id=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()) for name,data in fixtures().items()]


def expected_cases():
    return [dict(id=c['id'],selection=list(c['expected'] or (c['caret'],c['caret'])),
                 matched=c['expected'] is not None,unchanged=True) for c in cases()]


def validate_result(row,hashes):
    if not isinstance(row,dict) or row.get('schema')!='ru-notepad-regex-search-gui-v1' or row.get('name')!='main-gui-regex-search':raise ValueError('Regex receipt identity differs')
    for key,value in (('passed',True),('executed',True),('cleanup_killed',False),('main_hwnd_seen',True),('close_posted',True),('detached_from_console',True)):
        if row.get(key) is not value:raise ValueError('Regex lifecycle failed')
    if type(row.get('exit_code')) is not int or row['exit_code']!=0 or row.get('error') or row.get('skips'):raise ValueError('Regex execution failed or skipped')
    reopen=row.get('reopen')
    if not isinstance(reopen,dict) or reopen.get('name')!='main-gui-regex-reopen' or reopen.get('fixture_binary_sha256')!=hashes:raise ValueError('Regex fresh session missing')
    for key,value in (('passed',True),('executed',True),('cleanup_killed',False),('main_hwnd_seen',True),('close_posted',True),('detached_from_console',True)):
        if reopen.get(key) is not value:raise ValueError('Regex fresh session lifecycle failed')
    if type(reopen.get('exit_code')) is not int or reopen['exit_code']!=0 or reopen.get('error') or reopen.get('skips'):raise ValueError('Regex fresh session failed')
    if not hashes or row.get('fixture_binary_sha256')!=hashes or any(not isinstance(v,str) or len(v)!=64 or any(c not in '0123456789abcdef' for c in v) for v in hashes.values()):raise ValueError('Regex runtime identity differs')
    for field,expected in (('fixtures',inventory()),('cases',expected_cases()),('rejected',list(range(len(REJECTED)))),('engine_gates',list(ENGINE_GATES)),('disclosures',list(DISCLOSURES))):
        if row.get(field)!=expected:raise ValueError('Regex inventory differs: '+field)
    if any(type(n) is not int for n in row['rejected']):raise ValueError('Regex rejection identities must be integers')
    if any(type(f['bytes']) is not int for f in row['fixtures']):raise ValueError('Regex fixture byte types differ')
    for c in row['cases']:
        if type(c['matched']) is not bool or c['unchanged'] is not True or any(type(n) is not int for n in c['selection']):raise ValueError('Regex case types differ')
    if row.get('checks')!=dict.fromkeys(CHECKS,True) or any(v is not True for v in row['checks'].values()):raise ValueError('Regex checks incomplete')
    cancellations=row.get('cancellations')
    if not isinstance(cancellations,list) or len(cancellations)!=len(CANCEL_ACTIONS):raise ValueError('Regex cancellation inventory differs')
    for item,action in zip(cancellations,CANCEL_ACTIONS):
        if set(item)!={'action','running_seen','stable','seconds'} or item['action']!=action or item['running_seen'] is not True or item['stable'] is not True:raise ValueError('Regex cancellation was not observed')
        value=item['seconds']
        if type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<RESPONSE_SECONDS:raise ValueError('Regex input response bound failed')
    if row.get('zero_ranges')!=[[0,0],[4,4],[5,5],[6,6],[0,0]]:raise ValueError('Regex scalar zero progression differs')
    if any(type(n) is not int for pair in row['zero_ranges'] for n in pair):raise ValueError('Regex zero types differ')
    scope_gui.validate_layouts(row.get('layouts'))
    open_gui.validate_layouts(row.get('results_layouts'))
    labels=row.get('labels')
    if not isinstance(labels,list) or len(labels)!=len(LANGUAGES):raise ValueError('Regex language inventory differs')
    for entry,language in zip(labels,LANGUAGES):
        if entry!={'language':language,'menu_verified':True,'scope_verified':True}:raise ValueError('Regex translated labels unverified')
        if entry['menu_verified'] is not True or entry['scope_verified'] is not True:raise ValueError('Regex label types differ')
    return True


def regex_shortcut(api,process,hwnd,editor,backwards):
    """Actual F3/Shift+F3, guarded like the existing folding shortcut harness.

    Posted Shift messages do not update GetKeyState. Real accelerator evidence
    needs native keyboard input, restricted to the owned foreground editor.
    Always release only our own keys and restore the prior foreground window.
    """
    u=api.user
    for name,args,result in (
        ('GetForegroundWindow',[],wintypes.HWND),
        ('SetForegroundWindow',[wintypes.HWND],wintypes.BOOL),
        ('GetAsyncKeyState',[ctypes.c_int],ctypes.c_int16),
        ('GetGUIThreadInfo',[ctypes.c_uint32,ctypes.POINTER(_GUIThreadInfo)],wintypes.BOOL),
        ('SendInput',[ctypes.c_uint32,ctypes.POINTER(_Input),ctypes.c_int],ctypes.c_uint32)):
        fn=getattr(u,name);fn.argtypes=args;fn.restype=result
    keys=(16,0x72) if backwards else (0x72,)
    if any(u.GetAsyncKeyState(k)&0x8000 for k in (16,17,18,91,92,0x72)):
        raise RuntimeError('Refusing regex shortcut with pre-existing held key')
    previous=u.GetForegroundWindow();pending=[];stage='foreground';activation=None
    def focus_state():
        info=_GUIThreadInfo();info.cbSize=ctypes.sizeof(info)
        thread=u.GetWindowThreadProcessId(hwnd,None)
        valid=bool(u.GetGUIThreadInfo(thread,ctypes.byref(info)))
        return {'stage':stage,'backwards':bool(backwards),'activation_returned':activation,
                'foreground':int(u.GetForegroundWindow() or 0),'expected_main':int(hwnd),
                'expected_editor':int(editor),'focus':int(info.hwndFocus or 0),
                'thread_info_valid':valid}
    def focused():
        info=_GUIThreadInfo();info.cbSize=ctypes.sizeof(info)
        thread=u.GetWindowThreadProcessId(hwnd,None)
        return u.GetForegroundWindow()==hwnd and u.GetGUIThreadInfo(thread,ctypes.byref(info)) and info.hwndFocus==editor
    def send(key,release=False):
        event=_Input();event.type=1;event.value.ki.wVk=key;event.value.ki.dwFlags=2 if release else 0
        if u.SendInput(1,ctypes.byref(event),ctypes.sizeof(event))!=1:raise RuntimeError('Regex shortcut native input failed')
    try:
        api.verify_owned_handles(process.pid,hwnd,editor)
        activation=bool(u.SetForegroundWindow(hwnd))
        ci.wait_gui(api,process,lambda:u.GetForegroundWindow()==hwnd,'Owned regex window did not become foreground')
        # Foreground activation does not guarantee child keyboard focus. Ask
        # the verified Scintilla itself to acquire focus on its own UI thread;
        # this scalar command does not alter text, selection, undo, or scope.
        stage='editor-focus'
        api.verify_owned_handles(process.pid,hwnd,editor)
        api.scalar(editor,2400)  # SCI_GRABFOCUS, no pointer or keyboard injection.
        ci.wait_gui(api,process,focused,'Owned regex editor did not acquire keyboard focus')
        api.verify_owned_handles(process.pid,hwnd,editor)
        stage='keys'
        for key in keys:
            if not focused():raise RuntimeError('Regex fixture lost focus before shortcut')
            send(key);pending.append(key)
        for key in reversed(keys):send(key,True);pending.remove(key)
        api.responsive(hwnd)
    except Exception as exc:
        # Bounded HWND/phase facts only, never query or document contents.
        raise RuntimeError(str(exc)+'; regex_focus='+json.dumps(focus_state(),sort_keys=True)) from exc
    finally:
        for key in reversed(pending):send(key,True)
        if previous and previous!=hwnd:u.SetForegroundWindow(previous)


def activate_regex_fixture(api,process,hwnd,name,paths,identities):
    """Learn an unambiguous clean fixture once, then use its live editor HWND.

    Dirty captions are deliberately not normalized. The caller must forget a
    closed editor before reopening, even if Windows later recycles its HWND.
    """
    if name not in identities:
        activate_source(api,hwnd,paths[name],len(paths))
        editor=api.editor(hwnd)
        api.verify_owned_handles(process.pid,hwnd,editor)
        identities[name]=editor
        return editor
    expected=identities[name]
    for _ in range(len(paths)+1):
        if api.editor(hwnd)==expected:
            api.verify_owned_handles(process.pid,hwnd,expected)
            return expected
        api.command(hwnd,112);api.responsive(hwnd)
    raise RuntimeError('Known regex fixture editor is not reachable: '+name)


def write_progress(evidence,progress,phase,case=None):
    """Diagnostic partial observations, never a substitute acceptance receipt."""
    progress['phase']=phase;progress['case']=case
    evidence=Path(evidence);evidence.mkdir(parents=True,exist_ok=True)
    ci.save_json(evidence/'regex-search-progress.json',progress)


def run(api,binary_dir,fixtures_dir,evidence):
    from gui_instance_tabs import _information_dialog, _information_shape, _post_command, _wait
    binary_dir,fixtures_dir,evidence=map(Path,(binary_dir,fixtures_dir,evidence))
    sources=fixtures();paths={}
    for name,data in sources.items():
        path=fixtures_dir/'regex-search'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);paths[name]=path
    hashes={name:ci.sha(binary_dir/name) for name in ci.portable.RUNTIME_NAMES}
    target=fixtures_dir/'regex-search-runtime';_copy_runtime(binary_dir,target,hashes)
    catalog=json.loads((ROOT/'locales/regex_search.json').read_text(encoding='utf-8'))
    ui_catalog=json.loads((ROOT/'locales/ui.json').read_text(encoding='utf-8'))
    progress=dict(phase='startup',case=None,checks={},cases=[],rejected=[],cancellations=[])
    def phase(name,case=None):write_progress(evidence,progress,name,case)
    phase('startup')
    u=api.user
    u.GetMenu.argtypes=[wintypes.HWND];u.GetMenu.restype=wintypes.HMENU
    u.GetMenuState.argtypes=[wintypes.HMENU,ctypes.c_uint,ctypes.c_uint];u.GetMenuState.restype=ctypes.c_uint
    u.GetMenuStringW.argtypes=[wintypes.HMENU,ctypes.c_uint,wintypes.LPWSTR,ctypes.c_int,ctypes.c_uint];u.GetMenuStringW.restype=ctypes.c_int
    u.IsWindowEnabled.argtypes=[wintypes.HWND];u.IsWindowEnabled.restype=wintypes.BOOL
    def exercise(process,hwnd):
        checks=progress['checks'];observed=progress['cases'];rejected=progress['rejected'];cancellations=progress['cancellations']
        layouts=[];results_layouts=[];labels=[];identities={}
        ci.wait_gui(api,process,lambda:api.text(hwnd)==paths['stress.txt'].name+' · ru_notepad' and not u.IsWindowVisible(api.control(hwnd,901)),'Regex fixtures did not finish opening')
        api.command(hwnd,851)
        def activate(name):return activate_regex_fixture(api,process,hwnd,name,paths,identities)
        def selection():return tuple(api.scalar(api.editor(hwnd),n) for n in (2143,2145))
        def caret(a,b=None):api.scalar(api.editor(hwnd),2160,a,a if b is None else b)
        def menu(command):
            b=ctypes.create_unicode_buffer(2048);u.GetMenuStringW(u.GetMenu(hwnd),command,b,len(b),0);return b.value
        def running():
            state=u.GetMenuState(u.GetMenu(hwnd),STOP,0)
            if state==0xffffffff:raise RuntimeError('Regex Stop menu missing')
            return not bool(state&3)
        def status(key):return api.text(api.control(hwnd,11)).startswith(catalog[key]['en'])
        def finish(timeout=40):
            ci.wait_gui(api,process,lambda:not running(),'Regex did not finish',timeout=timeout)
            api.no_dialog(process.pid)
        def query(text):scope_gui.set_text(api,api.control(hwnd,310),text)
        def start(text,backwards=False):query(text);api.command(hwnd,308 if backwards else 303)
        def document():api.command(hwnd,301);api.command(hwnd,314);api.command(hwnd,REGEX)
        def persistent_state():
            editor=api.editor(hwnd);length=api.scalar(editor,2006)
            positions=range(length) if length<=4096 else (0,1,length-2,length-1)
            digest=hashlib.sha256(bytes(api.scalar(editor,2007,n)&255 for n in positions)).hexdigest()
            return (editor,length,digest)+tuple(api.scalar(editor,n) for n in (2159,2174,2016,2152,2398,2191,2193,2199))
        def dialog(command,bodies):
            if callable(command):command()
            else:_post_command(api,hwnd,command)
            deadline=time.monotonic()+10;found=None
            while time.monotonic()<deadline:
                if process.poll() is not None:raise RuntimeError('Regex process exited during expected dialog')
                dialogs=[h for h,c,v in api.windows(process.pid) if c=='#32770' and v]
                if len(dialogs)==1:
                    shape=_information_dialog(api,process,dialogs[0],deadline)
                    button=_information_shape(shape,hwnd,bodies)
                    if button is None:raise RuntimeError('Regex error dialog shape or localized body differs')
                    found=(dialogs[0],button);break
                time.sleep(.01)
            if found is None:raise RuntimeError('Regex expected information dialog absent')
            api.verify_owned_handles(process.pid,hwnd,*found)
            if not u.PostMessageW(found[1],0xF5,0,0):raise ctypes.WinError(ctypes.get_last_error())
            _wait(api,process,lambda:not u.IsWindowVisible(found[0]),'Regex dialog did not dismiss',10,dialogs=True)
        phase('mode-restore')
        activate('alt-first.txt');api.command(hwnd,301);api.command(hwnd,LITERAL)
        api.scalar(api.control(hwnd,306),241,0);api.scalar(api.control(hwnd,309),241,1)
        api.command(hwnd,REGEX)
        if not u.GetMenuState(u.GetMenu(hwnd),REGEX,0)&8 or u.GetMenuState(u.GetMenu(hwnd),LITERAL,0)&8:raise RuntimeError('Regex mode menu check differs')
        if api.scalar(api.control(hwnd,306),240)!=1 or api.scalar(api.control(hwnd,309),240)!=0 or any(u.IsWindowEnabled(api.control(hwnd,n)) for n in (306,309,311,304,305)):
            raise RuntimeError('Regex controls not forced/disabled')
        api.command(hwnd,LITERAL)
        if not u.GetMenuState(u.GetMenu(hwnd),LITERAL,0)&8 or u.GetMenuState(u.GetMenu(hwnd),REGEX,0)&8:raise RuntimeError('Literal mode menu check differs')
        if api.scalar(api.control(hwnd,306),240)!=0 or api.scalar(api.control(hwnd,309),240)!=1:raise RuntimeError('Literal options were not restored')
        checks['mode_restore']=True
        phase('hidden-bar-shortcuts')
        activate('fixed.txt');document();query('a');api.scalar(api.control(hwnd,312),241,0)
        for backwards,position,expected in ((False,0,(2,3)),(True,9,(8,9))):
            caret(position);api.command(hwnd,307)
            if u.IsWindowVisible(api.control(hwnd,310)):raise RuntimeError('Regex bar was not hidden before accelerator')
            before=persistent_state()
            regex_shortcut(api,process,hwnd,api.editor(hwnd),backwards)
            ci.wait_gui(api,process,lambda:u.IsWindowVisible(api.control(hwnd,310)) and selection()==expected and not running(),'Hidden-bar regex shortcut did not reopen and finish')
            if persistent_state()!=before or api.text(api.control(hwnd,310))!='a':raise RuntimeError('Hidden-bar shortcut changed document or retained query')
        # Closing a captured selection still invalidates it. Reopening via a
        # shortcut must not silently reinterpret it as document scope.
        caret(2,5);api.command(hwnd,313);api.command(hwnd,307)
        before=(persistent_state(),selection())
        for backwards in (False,True):
            dialog(lambda:regex_shortcut(api,process,hwnd,api.editor(hwnd),backwards),{ui_catalog['search.scope_required']['en']})
            if (persistent_state(),selection())!=before or running():raise RuntimeError('Hidden-bar shortcut revived invalid captured scope')
        api.command(hwnd,301)
        if api.text(api.control(hwnd,316))!=catalog['regex.scope_invalid']['en']:raise RuntimeError('Captured scope did not stay invalid')
        checks['hidden_bar_shortcuts']=True
        for c in cases():
            phase('semantic-case',c['id'])
            activate(c['id']+'.txt');document();api.scalar(api.control(hwnd,312),241,int(c['wrap']))
            if c['scope']:
                caret(*c['scope']);api.command(hwnd,313)
            caret(c['caret']);before=persistent_state();start(c['pattern'],c['backwards']);finish()
            expected=c['expected'] or (c['caret'],c['caret'])
            if selection()!=expected or persistent_state()!=before:raise RuntimeError('Regex byte selection/nonmutation differs: '+c['id'])
            # Stop becoming disabled alone must not let failure masquerade as no-match.
            status_text=api.text(api.control(hwnd,11))
            if any(status_text.startswith(catalog[k]['en']) for k in ('regex.failed','regex.limit','regex.stale','regex.cancelled')):raise RuntimeError('Regex case terminated abnormally: '+c['id'])
            no_match=status_text.startswith(ui_catalog['search.no_match']['en'])
            if no_match!=(c['expected'] is None):raise RuntimeError('Regex terminal match/no-match differs: '+c['id'])
            observed.append(dict(id=c['id'],selection=list(selection()),matched=c['expected'] is not None,unchanged=True))
        checks['case_matrix']=True
        activate('alt-first.txt');document();api.command(hwnd,315)
        for index,pattern in enumerate(REJECTED):
            phase('rejected-pattern',str(index))
            query(pattern);before=(persistent_state(),selection());old_history=menu(1700)
            reasons=('regex.reason_nullable',) if index in (7,8) else ('regex.reason_unsupported','regex.reason_syntax')
            bodies={catalog['regex.pattern_error']['en'].replace('{0}',str(n)).replace('{1}',catalog[r]['en']) for r in reasons for n in range(1,len(pattern)+2)}
            dialog(303,bodies)
            if (persistent_state(),selection())!=before or menu(1700)!=old_history:raise RuntimeError('Rejected regex changed state/history')
            rejected.append(index)
        checks['strict_rejection']=True
        phase('accepted-history')
        caret(0);start('a');finish();before=(persistent_state(),selection());query('pending-input');api.command(hwnd,1700)
        if api.text(api.control(hwnd,310))!='a' or (persistent_state(),selection())!=before:raise RuntimeError('Accepted history selection executed search')
        checks['accepted_history']=True
        phase('zero-progress')
        activate('zero.txt');document();caret(0);api.scalar(api.control(hwnd,312),241,1);query('()');zero=[]
        for _ in range(5):api.command(hwnd,303);finish();zero.append(list(selection()))
        if zero!=[[0,0],[4,4],[5,5],[6,6],[0,0]]:raise RuntimeError('Zero regex did not advance/wrap at scalar boundaries')
        # An unchanged no-match must retain the last zero exclusion. Otherwise
        # a third F3 revives the sole position after the second F3 found none.
        def no_zero_repeats(expected):
            before=persistent_state()
            for _ in range(3):
                api.command(hwnd,303);finish()
                if selection()!=expected or persistent_state()!=before or not api.text(api.control(hwnd,11)).startswith(ui_catalog['search.no_match']['en']):
                    raise RuntimeError('Unchanged no-match revived the excluded zero position')
        activate('empty-anchors.txt');document();caret(0);start('^$');finish()
        if selection()!=(0,0) or api.text(api.control(hwnd,11)).startswith(ui_catalog['search.no_match']['en']):raise RuntimeError('Initial empty-document zero did not match')
        no_zero_repeats((0,0))
        # A sole end anchor in nonempty Unicode text exercises wrap as well.
        activate('zero.txt');document();caret(0);start(r'\z');finish()
        if selection()!=(6,6):raise RuntimeError('Initial document-end zero did not match')
        no_zero_repeats((6,6))
        for reset in ('query','caret','scope'):
            if reset=='query':query('()');query(r'\z')
            elif reset=='caret':caret(0)
            else:api.command(hwnd,314)
            api.command(hwnd,303);finish()
            if selection()!=(6,6) or api.text(api.control(hwnd,11)).startswith(ui_catalog['search.no_match']['en']):raise RuntimeError('Explicit query/caret/scope change did not reset zero exclusion')
            no_zero_repeats((6,6))
        checks['zero_progress']=True
        phase('fixed-selection')
        activate('fixed.txt');document();caret(2,5);api.command(hwnd,313);caret(2);query('a');api.scalar(api.control(hwnd,312),241,1)
        for expected in ((2,3),(4,5),(2,3)):
            api.command(hwnd,303);finish()
            if selection()!=expected:raise RuntimeError('Search highlight replaced fixed scope')
        checks['fixed_selection']=True
        phase('readonly')
        document();caret(0);api.scalar(api.editor(hwnd),2171,1)
        try:
            before=persistent_state();start('a');finish()
            if selection()!=(2,3) or persistent_state()!=before:raise RuntimeError('Read-only regex failed')
        finally:api.scalar(api.editor(hwnd),2171,0)
        checks['readonly']=True
        phase('dirty-live')
        caret(0);api.scalar(api.editor(hwnd),0x102,ord('Z'),1);before=persistent_state();start('Z');finish()
        if selection()!=(0,1) or persistent_state()!=before or not api.scalar(api.editor(hwnd),2159):raise RuntimeError('Regex ignored dirty live buffer')
        api.command(hwnd,201);checks['dirty_live']=True
        phase('blocked-mutation')
        # First establish real literal all-open results, then prove direct guards preserve them.
        api.command(hwnd,LITERAL);api.scalar(api.control(hwnd,306),241,1);api.scalar(api.control(hwnd,309),241,0);query('xy');api.command(hwnd,317)
        ci.wait_gui(api,process,lambda:not u.IsWindowEnabled(api.control(hwnd,318)),'Literal results did not finish',timeout=40)
        api.command(hwnd,REGEX);query('a');before=(persistent_state(),selection(),api.scalar(api.control(hwnd,320),0x18B),api.text(api.control(hwnd,321)))
        for command in (304,305,317):
            dialog(command,{catalog['regex.unavailable']['en']})
            if (persistent_state(),selection(),api.scalar(api.control(hwnd,320),0x18B),api.text(api.control(hwnd,321)))!=before:raise RuntimeError('Regex guarded command mutated state/results')
        checks['blocked_mutation']=True
        api.command(hwnd,319)
        for action in CANCEL_ACTIONS:
            phase('cancellation',action)
            activate('stress.txt');document();caret(0);api.scalar(api.control(hwnd,312),241,1)
            if action=='undo':api.scalar(api.editor(hwnd),0x102,ord('a'),1);caret(0)
            start('(a|aa)*b')
            if not running() or not status('regex.running'):raise RuntimeError('Cancellation fixture was not observed running')
            began=time.perf_counter()
            if action=='stop':api.command(hwnd,STOP)
            elif action=='query':query('a')
            elif action=='restart':start(r'\Aa');finish()
            elif action=='scope':api.command(hwnd,314)
            elif action=='mode':api.command(hwnd,LITERAL)
            elif action=='wrap':api.scalar(api.control(hwnd,312),0xF5)
            elif action=='history':api.command(hwnd,1700)
            elif action=='clear_history':api.command(hwnd,315)
            elif action=='tab':api.command(hwnd,112)
            elif action=='edit':api.scalar(api.editor(hwnd),0x102,ord('Z'),1)
            elif action=='undo':api.command(hwnd,201)
            elif action=='bar_close':api.command(hwnd,307)
            elif action=='escape':
                if not u.PostMessageW(api.control(hwnd,310),0x100,27,1):raise ctypes.WinError(ctypes.get_last_error())
            elif action=='caret':
                api.verify_owned_handles(process.pid,hwnd,api.editor(hwnd));api.post_navigation(api.editor(hwnd),'RIGHT')
                ci.wait_gui(api,process,lambda:selection()==(1,1),'Real navigation input was not serviced',timeout=RESPONSE_SECONDS)
            elif action=='close_reopen':
                del identities['stress.txt']
                api.command(hwnd,105)
            ci.wait_gui(api,process,lambda:not running(),'Regex cancellation did not stop',timeout=RESPONSE_SECONDS)
            elapsed=time.perf_counter()-began
            if elapsed>=RESPONSE_SECONDS:raise RuntimeError('Regex input/cancel exceeded two seconds')
            if action=='close_reopen':
                api.drop(hwnd,[paths['stress.txt']])
                ci.wait_gui(api,process,lambda:api.text(hwnd)==paths['stress.txt'].name+' · ru_notepad' and not u.IsWindowVisible(api.control(hwnd,901)),'Regex closed fixture did not reopen',timeout=30)
            if action=='restart' and selection()!=(0,1):raise RuntimeError('Restart did not select new query')
            after=(persistent_state(),selection());time.sleep(.12);api.responsive(hwnd)
            if (persistent_state(),selection())!=after:raise RuntimeError('Cancelled job applied stale navigation')
            cancellations.append(dict(action=action,running_seen=True,stable=True,seconds=elapsed))
            phase('cancellation-cleanup',action)
            activate('stress.txt')
            while api.scalar(api.editor(hwnd),2174):api.command(hwnd,201)
        checks['cancel_matrix']=True;checks['input_responsiveness']=True
        phase('limit-no-navigation')
        activate('stress.txt');document();caret(STRESS_BYTES);before=(persistent_state(),selection());start('a|(a|aa)*b',True);finish(timeout=900)
        if not status('regex.limit') or (persistent_state(),selection())!=before:raise RuntimeError('Work limit selected a provisional result or wrong terminal state')
        checks['limit_no_navigation']=True
        activate('fixed.txt');document()
        for index,language in enumerate(LANGUAGES):
            phase('layout',language)
            api.command(hwnd,851+index)
            for command,key in ((LITERAL,'regex.mode_literal'),(REGEX,'regex.mode_regular'),(STOP,'regex.stop')):
                if menu(command)!=catalog[key][language]:raise RuntimeError('Regex menu translation differs')
            for scope in ('selection','invalid','document'):
                if scope=='selection':caret(2,5);api.command(hwnd,313)
                elif scope=='invalid':
                    caret(0);dialog(313,{ui_catalog['search.selection_required'][language]})
                else:api.command(hwnd,314)
                if api.text(api.control(hwnd,316))!=catalog['regex.scope_'+scope][language]:raise RuntimeError('Regex scope translation differs')
                for size in LAYOUT_SIZES:layouts.append(scope_gui.native_layout(api,hwnd,language,scope,size))
            # Existing results stay visible when changing regex mode. Capture both bar states.
            api.command(hwnd,LITERAL);query('xy');api.command(hwnd,317)
            ci.wait_gui(api,process,lambda:not u.IsWindowEnabled(api.control(hwnd,318)),'Layout result search did not finish',timeout=40)
            api.command(hwnd,REGEX)
            for size in LAYOUT_SIZES:
                api.command(hwnd,307);results_layouts.append(open_gui.native_layout(api,hwnd,language,size,False))
                api.command(hwnd,301);results_layouts.append(open_gui.native_layout(api,hwnd,language,size,True))
            api.command(hwnd,319);labels.append(dict(language=language,menu_verified=True,scope_verified=True))
        scope_gui.validate_layouts(layouts);open_gui.validate_layouts(results_layouts);checks['seven_language_layout']=True
        phase('disk-unchanged')
        if any(path.read_bytes()!=sources[name] for name,path in paths.items()):raise RuntimeError('Regex wrote synthetic fixture files')
        checks['disk_unchanged']=True
        return dict(checks=checks,cases=observed,rejected=rejected,zero_ranges=zero,cancellations=cancellations,layouts=layouts,results_layouts=results_layouts,labels=labels)
    with isolated_settings():
        result=ci.run_gui(api,target,evidence,name='main-gui-regex-search',arguments=list(paths.values()),exercise=exercise,log_prefix='regex-search')
        phase('first-process-complete' if result['passed'] else progress['phase'],progress['case'])
        result['progress']=progress
        result.update(schema='ru-notepad-regex-search-gui-v1',fixture_binary_sha256=hashes,fixtures=inventory(),engine_gates=list(ENGINE_GATES),disclosures=list(DISCLOSURES))
        if result['passed']:
            phase('history-restart')
            reopen_target=fixtures_dir/'regex-search-reopen-runtime';_copy_runtime(binary_dir,reopen_target,hashes)
            def reopened(process,hwnd):
                ci.wait_gui(api,process,lambda:api.text(hwnd)==paths['fixed.txt'].name+' · ru_notepad' and not u.IsWindowVisible(api.control(hwnd,901)),'Regex new session did not open')
                api.command(hwnd,301)
                buf=ctypes.create_unicode_buffer(2048)
                for command in (1700,1720):
                    if u.GetMenuStringW(u.GetMenu(hwnd),command,buf,len(buf),0):raise RuntimeError('Regex history persisted across sessions')
                if api.text(api.control(hwnd,310)) or api.text(api.control(hwnd,311)):raise RuntimeError('Regex query persisted across sessions')
                result['checks']['history_restart_empty']=True
                return {}
            result['reopen']=ci.run_gui(api,reopen_target,evidence,name='main-gui-regex-reopen',arguments=[paths['fixed.txt']],exercise=reopened,log_prefix='regex-search-reopen')
            result['reopen']['fixture_binary_sha256']=hashes
            phase('complete' if result['reopen']['passed'] else 'history-restart')
            validate_result(result,hashes)
    return result
