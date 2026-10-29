#!/usr/bin/env python3
"""Real main-menu routing, with scalar-only cross-process Scintilla inspection."""
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import windows_ci as ci
from gui_instance_tabs import isolated_settings, _copy_runtime
ROOT=Path(__file__).resolve().parents[1]
ROWS=json.loads((ROOT/'syntax/languages.json').read_text(encoding='utf-8'))['languages']
LEGACY={'plain':701,'cpp':702,'json':703,'ru':704,'markdown':705}
COMMANDS={r['id']:LEGACY.get(r['id'],2000+i) for i,r in enumerate(ROWS)}
TEXT=b'int value = 42;\n'
CHECKS=('menu_exact','text_preserved','selection_preserved','font_preserved','savepoint_preserved','undo_preserved','high_style_reset','cpp_token','java_token','source_unchanged')

def validate_result(record,hashes):
    if not isinstance(record,dict):raise ValueError('Language GUI receipt missing')
    if record.get('schema')!='ru-notepad-language-gui-v1' or record.get('name')!='main-gui-language-catalog':raise ValueError('Language GUI identity differs')
    for key,value in [('passed',True),('executed',True),('cleanup_killed',False),('main_hwnd_seen',True),('close_posted',True),('detached_from_console',True)]:
        if record.get(key) is not value:raise ValueError('Language GUI lifecycle failed')
    if type(record.get('exit_code')) is not int or record['exit_code']!=0 or record.get('fixture_binary_sha256')!=hashes:raise ValueError('Language GUI binary/exit differs')
    if record.get('error') or record.get('skips'):raise ValueError('Language GUI errored/skipped')
    if (not isinstance(record.get('checks'),dict) or set(record['checks'])!=set(CHECKS) or any(v is not True for v in record['checks'].values())):raise ValueError('Language GUI checks incomplete')
    expected=[{'language':r['id'],'command':COMMANDS[r['id']],'lexer':0 if r['id'] in ('plain','ru') else r['lexer_id']} for r in ROWS]
    if (not isinstance(record.get('modes'),list) or any(not isinstance(row,dict) or type(row.get('command')) is not int or type(row.get('lexer')) is not int for row in record['modes']) or record['modes']!=expected):raise ValueError('Language GUI exact mode/command/lexer inventory differs')
    if (not isinstance(record.get('menu_commands'),list) or any(type(v) is not int for v in record['menu_commands']) or record['menu_commands']!=sorted(COMMANDS.values())):raise ValueError('Language GUI menu inventory differs')
    return True

def menu_commands(api,hwnd):
    u=api.user
    for name,args,result in [('GetMenu',[wintypes.HWND],ctypes.c_void_p),('GetSubMenu',[ctypes.c_void_p,ctypes.c_int],ctypes.c_void_p),('GetMenuItemCount',[ctypes.c_void_p],ctypes.c_int),('GetMenuItemID',[ctypes.c_void_p,ctypes.c_int],ctypes.c_uint)]:
        fn=getattr(u,name);fn.argtypes=args;fn.restype=result
    seen=set();ids=[]
    def visit(menu,depth=0):
        if not menu or menu in seen or depth>8:raise RuntimeError('Missing/cyclic/deep menu')
        seen.add(menu);count=u.GetMenuItemCount(menu)
        if not 0<=count<=256:raise RuntimeError('Invalid menu item count')
        for i in range(count):
            sub=u.GetSubMenu(menu,i)
            if sub:visit(sub,depth+1)
            else:
                value=u.GetMenuItemID(menu,i)
                if 701<=value<=705 or 2000<=value<3000:ids.append(value)
    visit(u.GetMenu(hwnd));return sorted(ids)

def run(api,binary_dir,fixtures,evidence):
    binary_dir,fixtures,evidence=map(Path,(binary_dir,fixtures,evidence))
    hashes={n:ci.sha(binary_dir/n) for n in ci.portable.RUNTIME_NAMES}
    target=fixtures/'language-menu-runtime';_copy_runtime(binary_dir,target,hashes)
    source=fixtures/'language-menu-fixture.txt';source.write_bytes(TEXT)
    def exercise(process,hwnd):
        editor=api.editor(hwnd);api.verify_owned_handles(process.pid,hwnd,editor)
        ci.wait_gui(api,process,lambda:api.editor_bytes(hwnd)==TEXT,'language fixture not loaded')
        menu=menu_commands(api,hwnd)
        if menu!=sorted(COMMANDS.values()):raise RuntimeError('Language menu missing/duplicate/unexpected commands')
        font=api.scalar(editor,2485,32) # STYLEGETSIZE; no cross-process pointers
        api.scalar(editor,2160,1,4) # SETSEL
        modes=[];checks={k:False for k in CHECKS};checks['menu_exact']=True
        for row in ROWS:
            name=row['id'];api.command(hwnd,COMMANDS[name]);api.responsive(hwnd)
            expected=0 if name in ('plain','ru') else row['lexer_id']
            actual=api.scalar(editor,4002)
            if actual!=expected:raise RuntimeError('Wrong lexer via WM_COMMAND: '+name)
            if api.editor_bytes(hwnd)!=TEXT:raise RuntimeError('Mode changed text: '+name)
            if (api.scalar(editor,2008),api.scalar(editor,2009))!=(4,1):raise RuntimeError('Mode changed selection: '+name)
            if api.scalar(editor,2485,32)!=font:raise RuntimeError('Mode changed font: '+name)
            if api.scalar(editor,2159)!=0 or api.scalar(editor,2174)!=0:raise RuntimeError('Mode changed clean/undo state: '+name)
            modes.append({'language':name,'command':COMMANDS[name],'lexer':actual})
        for name,key in [('cpp','cpp_token'),('java','java_token')]:
            api.command(hwnd,COMMANDS[name]);api.scalar(editor,4003,0,-1) # tiny synthetic fixture only
            if [api.scalar(editor,2010,i) for i in range(3)]!=[5]*3:raise RuntimeError('Actual keyword styles wrong: '+name)
            checks[key]=True
        api.scalar(editor,2051,200,123456);api.command(hwnd,701)
        if api.scalar(editor,2481,200)!=api.scalar(editor,2481,32):raise RuntimeError('High style leaked')
        for key in CHECKS:
            if key not in ('cpp_token','java_token'):checks[key]=True
        if source.read_bytes()!=TEXT:raise RuntimeError('Source fixture changed')
        return {'checks':checks,'modes':modes,'menu_commands':menu}
    with isolated_settings():
        result=ci.run_gui(api,target,evidence,name='main-gui-language-catalog',arguments=[source.resolve()],exercise=exercise,log_prefix='language-catalog')
    result.update(schema='ru-notepad-language-gui-v1',fixture_binary_sha256=hashes)
    if result['passed']:validate_result(result,hashes)
    return result
