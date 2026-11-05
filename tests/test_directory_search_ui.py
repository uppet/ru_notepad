"""Production directory UI contracts and portable boundary controls.

With --ru-root, extract unchanged production functions and execute them in the
interpreter and C backend. Only Win32 value/call/memory adapters are rebound to
recording functions. This is not Windows picker, layout or GUI acceptance.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

from test_regex_search_bridge import verify_compiler, gcc_path, executable_path, runtime_output

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'src/main.ru').read_text(encoding='utf-8')


def body(name):
    return SOURCE.split('算 ' + name, 1)[1].split('\n法', 1)[0]


class DirectoryUIContract(unittest.TestCase):
    def test_independent_modes_and_localized_command(self):
        self.assertIn("'resultMode':'open','directorySearch':空", SOURCE)
        command = body('命令 ')
        self.assertIn('号 <= 326', command)
        self.assertIn('若 号 == 326 则 启动目录搜索. 得 空.', command)
        restriction = command.split("若 (A 其 查 'regexMode') 且", 1)[1].split('\n', 1)[0]
        self.assertNotIn('326', restriction)
        menu = body('菜单:')
        counts = re.search(r'组量们 取 \[([^]]+)\]', menu).group(1)
        self.assertEqual([int(v) for v in counts.split(',')], [11,19,14,6,5,7,5,8,1])
        self.assertIn("'directory.find'", menu)
        self.assertIn('323, 324, 325, 326, 401', menu)

    def test_menu_stop_and_close_follow_current_result_mode(self):
        menu = body('结果菜单状态:')
        for text in ("A 其 查 'openSearch'", "A 其 查 'directorySearch'", "A 其 查 'resultMode'", "A 其 查 'openSearchVisible'", '[主,318,停旗]', '[主,319,关旗]'):
            self.assertIn(text, menu)
        self.assertIn('正则菜单状态. 行序菜单状态. 结果菜单状态.', SOURCE)
        self.assertIn("若 号 == 319 且 非 (A 其 查 'openSearchVisible')", body('菜单:'))

    def test_invalid_query_and_picker_cancel_preserve_results(self):
        start = body('启动目录搜索:')
        self.assertLess(start.index('GetWindowTextLengthW'), start.index('窗 其 取文'))
        self.assertIn('长 > 512', start)
        self.assertLess(start.index('目寻 其 检查查询'), start.index('界面目录对话'))
        self.assertLess(start.index("选['status'] == 'cancelled'"), start.index('停结果.'))
        self.assertLess(start.index('停结果.'), start.index('目寻 其 新建'))
        self.assertEqual(start.count('若 目寻 其 忙 则'), 2)

    def test_owned_picker_unwinds_on_success_and_failure(self):
        picker = body('界面目录对话:')
        self.assertEqual(picker.count("'modalDepth')+1"), 1)
        self.assertEqual(picker.count("'modalDepth')-1"), 2)
        self.assertIn("目寻 其 选目录 (A 其 查 'window')", picker)

    def test_directory_start_has_no_editor_or_preference_mutation(self):
        start = body('启动目录搜索:')
        for forbidden in ('编 其', '打开 ', '新页', "'case'", "'whole'", "'regexMode'", '正则模式', '停正则', "'searchScope'"):
            self.assertNotIn(forbidden, start)
        self.assertIn("A 其 增 'directorySearch' 查找态", start)
        self.assertIn("A 其 增 'resultMode' 'directory'", start)

    def test_activation_guard_precedes_selection_and_open_navigation(self):
        navigate = body('转到搜索结果:')
        guard = "若 (A 其 查 'resultMode') == 'directory' 则 得 空. 然"
        self.assertLess(navigate.index(guard), navigate.index('窗 其 发送'))
        self.assertLess(navigate.index(guard), navigate.index('开寻 其 定位'))
        self.assertIn("[(A 其 查 'resultOpen'),0]", body('结果状态:'))
        self.assertIn("((A 其 查 'resultList') 其 句) 则 命令 322", SOURCE)
        self.assertIn('若 键 == 13 则 命令 322', body('快捷 '))

    def test_retirement_before_busy_modal_or_visibility_admission(self):
        tick = body('搜索结果时钟:')
        maintenance = tick.index('目寻 其 维护')
        for guard in ('busy','modalDepth','closeRun','tabMenuOpen','closeIndex','openSearchVisible','resultMode'):
            self.assertLess(maintenance, tick.index("A 其 查 '"+guard+"'"))
        self.assertEqual(tick.count('目寻 其 步进'), 1)
        self.assertIn('循 16 次', tick)
        self.assertNotIn('KillTimer', tick)
        self.assertIn('目寻 其 忙', body('结果仍需时钟:'))
        self.assertIn("A 其 查 'directorySearch'", body('结果仍需时钟:'))
        self.assertIn('若 非 (结果仍需时钟)', body('结果时钟状态:'))

    def test_stop_and_hide_keep_retirement_owned(self):
        stop = body('停结果:')
        self.assertIn("(A 其 查 'resultMode') == 'directory'", stop)
        self.assertIn('目寻 其 取消', stop)
        self.assertIn('开寻 其 取消', stop)
        self.assertNotIn('KillTimer', stop)
        self.assertIn('结果时钟状态', stop)
        self.assertIn('停结果.', body('结果显示 '))
        self.assertIn("A 其 增 'resultMode' 'open'", body('启动全文档搜索:'))

    def test_editor_edits_only_stale_open_state_and_keep_regex_guard(self):
        invalidate = body('结果失效:')
        self.assertIn("停正则 'regex.stale'", invalidate)
        self.assertIn("A 其 查 'openSearch'", invalidate)
        self.assertNotIn('目录', invalidate)
        self.assertNotIn('目寻', invalidate)
        self.assertNotIn('KillTimer', invalidate)
        self.assertIn("若 (A 其 查 'ready') 且 非 (A 其 查 'busy') 则", body('正则状态:'))

    def test_shutdown_abandons_before_timer_stop(self):
        destroy = body('消息处理 ').split('若 号 == 2 则',1)[1].split("若 A 其 查 'ready'",1)[0]
        self.assertLess(destroy.index('目寻 其 关停'), destroy.index('KillTimer'))
        self.assertNotIn('等待', destroy)
        self.assertIn('目寻 其 关停', body('启动目录搜索:'))

    def test_details_are_readonly_scrollable_bounded_and_escaped(self):
        self.assertIn("'EDIT' '' 1084295236 327", SOURCE)
        style = 1084295236
        for bit in (0x800,0x4,0x40,0x200000): self.assertTrue(style & bit)
        self.assertFalse(style & 0x100000) # wrap, no horizontal scrollbar
        self.assertIn('循 1024 次', body('目录显示文本 '))
        details = body('目录详情 ')
        for key in ('root','query','policy','limits','exclusions','counts','draining'):
            self.assertIn('directory.'+key, details)
        for reason in range(1,13): self.assertIn("'native-"+str(reason)+"'",details)
        self.assertIn("'resultDetails'",body('界面文字:'))
        self.assertIn("'resultDetails'",body('结果显示 '))

    def test_all_locales_keep_explicit_list_only_policy(self):
        catalog = json.loads((ROOT/'locales/directory_search.json').read_text(encoding='utf-8'))
        languages = {'en','zh-CN','ja','ko','es','ru','it'}
        for key,values in catalog.items():
            self.assertEqual(set(values),languages,key)
            self.assertTrue(all(values.values()),key)
        for key in ('directory.find','directory.summary','directory.policy','directory.limits','directory.exclusions','directory.query_invalid','directory.busy','directory.retiring'):
            self.assertIn(key,catalog)


def production_functions():
    names = ('目录显示文本 ','目录详情 ','结果状态:','结果仍需时钟:','结果时钟状态:',
             '停结果:','结果失效:','界面目录对话:','启动目录搜索:','搜索结果时钟:','转到搜索结果:')
    source = '\n'.join('算 '+name+body(name)+'\n法' for name in names)
    # Replace only foreign call/value/owned-memory boundary expressions. Branches,
    # state updates, admission order, loops and publication cap remain unchanged.
    boundary = {
        "窗 其 结果 ((窗 其 KillTimer) 其 调用 [(A 其 查 'window'),903])": "窗 其 杀钟 ([(A 其 查 'window'),903])",
        "窗 其 结果 ((窗 其 EnableWindow) 其 调用 [(A 其 查 'resultStop'),活])": "窗 其 使能 ([(A 其 查 'resultStop'),活])",
        "窗 其 结果 ((窗 其 EnableWindow) 其 调用 [(A 其 查 'resultOpen'),0])": "窗 其 使能 ([(A 其 查 'resultOpen'),0])",
        "窗 其 结果 ((窗 其 EnableWindow) 其 调用 [(A 其 查 'resultOpen'),可去])": "窗 其 使能 ([(A 其 查 'resultOpen'),可去])",
        "(窗 其 结果 ((窗 其 GetWindowTextLengthW) 其 调用 [(A 其 查 'find')])) 其 数": "窗 其 长度 (A 其 查 'find')",
        "((窗 其 SetTimer) 其 调用 [(A 其 查 'window'),903,20,空]) 其 值 其 为空": "(窗 其 设钟 ([(A 其 查 'window'),903,20,空])) == 0",
        "存 其 关闭": "窗 其 释放 存",
        "(窗 其 发指 (A 其 查 'resultList') 384 0 存) 其 数": "窗 其 发指 (A 其 查 'resultList') 384 0 存",
        "(窗 其 发送 (A 其 查 'resultList') 392 0 0) 其 数": "窗 其 发送 (A 其 查 'resultList') 392 0 0",
    }
    for original,replacement in boundary.items():
        if original not in source: raise AssertionError('Native boundary changed: '+original)
        source=source.replace(original,replacement)
    return source


WINDOW = """记录 取 {'kills':0,'sets':0,'gets':0,'adds':0,'resets':0,'text':'a','length':1,'timer':1,'enabled':{},'titles':{},'detailWrites':0}.
算 杀钟 参数: 记录 其 增 'kills' (记录['kills']+1). 得 1. 法
算 使能 参数: 记录['enabled'] 其 增 参数[0] 参数[1]. 得 1. 法
算 设钟 参数: 记录 其 增 'sets' (记录['sets']+1). 得 记录['timer']. 法
算 长度 柄: 得 记录['length']. 法
算 取文 柄: 得 记录['text']. 法
算 标题 柄 文:
    若 柄 == 'details' 则 记录 其 增 'detailWrites' (记录['detailWrites']+1). 然
    记录['titles'] 其 增 柄 文. 得 空.
法
算 发送 柄 号 甲 乙:
    若 号 == 388 则 记录 其 增 'resets' (记录['resets']+1). 然
    若 号 == 392 则 记录 其 增 'gets' (记录['gets']+1). 然
    得 -1.
法
算 发指 柄 号 甲 文: 记录 其 增 'adds' (记录['adds']+1). 得 记录['adds']-1. 法
算 释放 存: 得 空. 法
"""
DIRECTORY = """记录 取 {'busy':假,'maintenance':0,'steps':0,'starts':0,'cancels':0,'pickers':0,'shutdown':0,'valid':真,'init':'','throwPicker':假,'choice':'cancelled','rows':0,'retire':假,'job':空}.
算 初始化: 得 记录['init']. 法
算 忙: 得 记录['busy']. 法
算 维护:
    记录 其 增 'maintenance' (记录['maintenance']+1).
    若 记录['retire'] 则 记录 其 增 'busy' 假. 记录['job'] 其 增 'workerPending' 假. 然
    得 记录['busy'].
法
算 检查查询 词:
    若 记录['valid'] 则 得 {'status':'ok'}. 然 得 {'status':'invalid-query'}.
法
算 选目录 主 标题:
    记录 其 增 'pickers' (记录['pickers']+1).
    若 记录['throwPicker'] 则 卒 'picker'. 然
    得 {'status':记录['choice'],'path':'C:\\\\chosen','error':''}.
法
算 新建 根 词:
    记录 其 增 'starts' (记录['starts']+1). 记录 其 增 'busy' 真.
    工作 取 {'status':'running','results':[],'root':根,'query':词,'filesSearched':0,'filesSkipped':0,'dirsSkipped':0,'rawBytes':0,'reasonCounts':{},'workerPending':真,'error':''}.
    记录 其 增 'job' 工作. 得 工作.
法
算 取消 工作:
    记录 其 增 'cancels' (记录['cancels']+1).
    若 工作['status'] == 'running' 则 工作 其 增 'status' 'cancelled'. 工作 其 增 'workerPending' 真. 记录 其 增 'busy' 真. 然
    得 工作.
法
算 步进 工作:
    记录 其 增 'steps' (记录['steps']+1).
    循 记录['rows'] 次 工作['results'] 其 增 'row'. 环
    得 工作.
法
算 行标签 行: 得 'safe row'. 法
算 关停: 记录 其 增 'shutdown' (记录['shutdown']+1). 得 空. 法
"""
OPEN = """记录 取 {'steps':0,'cancels':0,'navigation':0}.
算 取消 工作: 记录 其 增 'cancels' (记录['cancels']+1). 工作 其 增 'status' 'cancelled'. 得 工作. 法
算 步进 工作 文们: 记录 其 增 'steps' (记录['steps']+1). 得 工作. 法
算 行标签 行: 得 'open row'. 法
算 定位 工作 项 文们: 记录 其 增 'navigation' (记录['navigation']+1). 得 -1. 法
"""
PRELUDE = """窗 取 外言 'window.ru'.
目寻 取 外言 'directory.ru'.
开寻 取 外言 'open.ru'.
密 取 外言 'memory.ru'.
本地 取 外言 'i18n.ru'.
寻史 取 外言 'search_history.ru'.
A 取 {'window':'window','find':'find','resultList':'list','resultSummary':'summary','resultDetails':'details','resultOpen':'open','resultStop':'stop','directoryDetail':'','directoryHeader':'','directorySignature':'','directoryLanguage':'','openSearch':空,'directorySearch':空,'resultMode':'open','openSearchRows':0,'openSearchTick':假,'ready':真,'busy':假,'modalDepth':0,'closeRun':空,'tabMenuOpen':假,'closeIndex':-1,'openSearchVisible':真,'docs':[],'findHistory':[],'notice':'','regexNotice':'','regexMode':真,'regexCase':0,'regexWhole':1,'case':0,'whole':1,'editorText':'dirty unsaved','anchor':8,'caret':2,'undo':7}.
算 提示 文: A 其 增 'notice' 文. 得 空. 法
算 停正则 因: A 其 增 'regexNotice' 因. 得 空. 法
算 菜单: 得 空. 法
算 结果显示 显示: A 其 增 'openSearchVisible' 显示. 得 空. 法
算 切页 位: 卒 'Unexpected editor navigation'. 法
算 确认 条 名: 若 非 条 则 卒 名. 然 得 空. 法
"""
CASES = """
本地 其 设置 'en'.
确认 ((目录显示文本 'a\\n\\r\\t‮b') == 'a␊␍␉�b') 'safe captured text'.
显 'PASS: escaped capture'.
开放 取 {'status':'running','results':[],'documentCount':1}.
目录 取 目寻 其 新建 'C:\\\\first' 'fixed'.
A 其 增 'openSearch' 开放. A 其 增 'directorySearch' 目录. A 其 增 'resultMode' 'directory'.
旧杀 取 窗 其 记录['kills'].
停结果.
确认 (目录['status'] == 'cancelled' 且 开放['status'] == 'running') 'independent directory stop'.
确认 ((窗 其 记录['kills']) == 旧杀) 'running open job timer retained'.
确认 ((窗 其 记录['enabled']['open']) == 0) 'directory navigation disabled'.
显 'PASS: independent directory stop'.
A 其 增 'resultMode' 'open'. 停结果.
确认 (开放['status'] == 'cancelled') 'open stop'.
确认 ((窗 其 记录['kills']) == 旧杀) 'draining timer retained'.
目寻 其 记录 其 增 'busy' 假. 目录 其 增 'workerPending' 假.
结果时钟状态.
确认 ((窗 其 记录['kills']) == 旧杀+1) 'idle timer stopped'.
显 'PASS: retirement owns timer'.
目录 其 增 'status' 'running'. 目寻 其 记录 其 增 'busy' 真.
A 其 增 'resultMode' 'directory'. 结果失效.
确认 (目录['status'] == 'running' 且 开放['status'] == 'stale') 'disk results survive edit'.
确认 (A['regexNotice'] == 'regex.stale') 'regex stale preserved'.
显 'PASS: editor invalidation ownership'.
转到搜索结果.
确认 ((窗 其 记录['gets']) == 0 且 (开寻 其 记录['navigation']) == 0) 'no direct activation'.
显 'PASS: list only activation'.
旧步 取 目寻 其 记录['steps']. 旧护 取 目寻 其 记录['maintenance'].
A 其 增 'busy' 真. 搜索结果时钟. A 其 增 'busy' 假.
A 其 增 'modalDepth' 1. 搜索结果时钟. A 其 增 'modalDepth' 0.
A 其 增 'openSearchVisible' 假. 搜索结果时钟.
A 其 增 'resultMode' 'open'. 搜索结果时钟.
确认 ((目寻 其 记录['maintenance']) == 旧护+4) 'maintenance across guards'.
确认 ((目寻 其 记录['steps']) == 旧步) 'policy paused across guards'.
显 'PASS: maintenance across modal busy hidden and open mode'.
A 其 增 'resultMode' 'directory'. A 其 增 'openSearchVisible' 真.
目寻 其 记录 其 增 'rows' 20.
搜索结果时钟.
确认 ((窗 其 记录['adds']) == 16 且 A['openSearchRows'] == 16) 'bounded UI publication'.
确认 ((目录['results'] 其 量) == 20) 'mock overflow probe retained'.
显 'PASS: sixteen row publication cap'.
目录 其 增 'status' 'complete'. 目录 其 增 'workerPending' 假.
目寻 其 记录 其 增 'busy' 假. 目寻 其 记录 其 增 'rows' 0.
旧开 取 目寻 其 记录['starts']. 旧选 取 目寻 其 记录['pickers']. 旧清 取 窗 其 记录['resets'].
窗 其 记录 其 增 'length' 513. 启动目录搜索.
窗 其 记录 其 增 'length' 1. 目寻 其 记录 其 增 'valid' 假. 启动目录搜索.
确认 ((目寻 其 记录['pickers']) == 旧选 且 (窗 其 记录['resets']) == 旧清) 'invalid query preserves previous list'.
确认 (A['directorySearch']['query'] == 'fixed') 'invalid capture stable'.
显 'PASS: invalid query preserves results before picker'.
目寻 其 记录 其 增 'valid' 真. 启动目录搜索.
确认 ((目寻 其 记录['starts']) == 旧开 且 (窗 其 记录['resets']) == 旧清 且 A['modalDepth'] == 0) 'picker cancel preserves results'.
目寻 其 记录 其 增 'throwPicker' 真. 启动目录搜索. 目寻 其 记录 其 增 'throwPicker' 假.
确认 (A['modalDepth'] == 0 且 (窗 其 记录['resets']) == 旧清) 'picker error unwinds'.
显 'PASS: picker cancellation and error unwind'.
目寻 其 记录 其 增 'busy' 真. 旧选 取 目寻 其 记录['pickers']. 启动目录搜索.
确认 ((目寻 其 记录['pickers']) == 旧选 且 (目寻 其 记录['starts']) == 旧开) 'replacement prohibited'.
显 'PASS: active or retiring worker blocks replacement'.
目寻 其 记录 其 增 'busy' 假. 目寻 其 记录 其 增 'choice' 'chosen'.
窗 其 记录 其 增 'text' 'Captured'. 启动目录搜索.
确认 (A['resultMode'] == 'directory' 且 A['directorySearch']['query'] == 'Captured') 'new captured query'.
窗 其 记录 其 增 'text' 'Edited afterwards'.
确认 (A['directorySearch']['query'] == 'Captured') 'query edit does not retarget'.
确认 (A['regexMode'] 且 A['regexCase'] == 0 且 A['regexWhole'] == 1 且 A['case'] == 0 且 A['whole'] == 1) 'literal regex preferences untouched'.
确认 (A['editorText'] == 'dirty unsaved' 且 A['anchor'] == 8 且 A['caret'] == 2 且 A['undo'] == 7) 'editor unchanged'.
显 'PASS: captured query and editor preferences unchanged'.
语言们 取 ['en','zh-CN','ja','ko','es','ru','it']. 语位 取 0.
循 7 次
    本地 其 设置 语言们[语位]. 结果状态.
    头 取 本地 其 格式 'directory.root' ([(目录显示文本 A['directorySearch']['root'])]).
    详情 取 窗 其 记录['titles']['details'].
    确认 ((详情 其 量) > 100 且 详情[:(头 其 量)] == 头) 'localized details present'.
    确认 ((窗 其 记录['enabled']['open']) == 0) 'localized navigation stays disabled'.
    语位 取 语位+1.
环
显 'PASS: seven locale detail rendering'.
旧写 取 窗 其 记录['detailWrites']. 旧详情 取 窗 其 记录['titles']['details'].
结果状态. 结果状态.
确认 ((窗 其 记录['detailWrites']) == 旧写) 'unchanged details do not reset scroll'.
A['directorySearch']['reasonCounts'] 其 增 'native-8' 1.
结果状态.
确认 ((窗 其 记录['titles']['details']) != 旧详情 且 (窗 其 记录['detailWrites']) == 旧写+1) 'changed reasons render once'.
显 'PASS: cached details refresh only on changes'.
目寻 其 取消 A['directorySearch']. 结果状态.
目寻 其 记录 其 增 'retire' 真. A 其 增 'busy' 真. 搜索结果时钟. A 其 增 'busy' 假.
目寻 其 记录 其 增 'retire' 假.
确认 (非 A['directorySearch']['workerPending']) 'worker retired'.
期文 取 本地 其 格式 'directory.summary' ([(本地 其 文本 'directory.status_cancelled'),0,0]).
确认 ((窗 其 记录['titles']['summary']) == 期文) 'retirement projection while busy'.
显 'PASS: terminal retirement projection before busy guard'.

A['directorySearch'] 其 增 'status' 'complete'. 目寻 其 记录 其 增 'busy' 假.
窗 其 记录 其 增 'timer' 0. 启动目录搜索.
确认 (A['directorySearch']['status'] == 'failed' 且 (目寻 其 记录['shutdown']) == 1) 'no-timer abandon'.
显 'PASS: timer failure abandons without wait'.
显 'TOTAL PASS: 15'.
"""


def run_production(ru_root):
    verify_compiler(ru_root)
    with tempfile.TemporaryDirectory(prefix='directory-ui-') as directory:
        root=Path(directory)
        for name,text in [('window.ru',WINDOW),('directory.ru',DIRECTORY),('open.ru',OPEN),
                          ('memory.ru','算 UTF16 文: 得 文. 法\n')]:
            (root/name).write_text(text,encoding='utf-8')
        for name in ('i18n.ru','i18n_catalog.ru','search_history.ru'):
            (root/name).write_text((ROOT/'src'/name).read_text(encoding='utf-8'),encoding='utf-8')
        path=root/'ui.ru'
        path.write_text(PRELUDE+production_functions()+CASES,encoding='utf-8')
        exe=executable_path(root,'ui')
        outputs=[]
        for label,command in (
            ('interpreter',[sys.executable,str(ru_root/'ru'),'run',str(path)]),
            ('build',[sys.executable,str(ru_root/'ru'),'build','--cc',gcc_path(),str(path),'-o',str(exe)]),
            ('c',[str(exe)])):
            result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',timeout=180)
            if result.returncode: raise RuntimeError(f'{label}: {result.stdout}\n{result.stderr}')
            if label!='build':
                runtime_output(result.stdout,result.stderr,label)
                lines=result.stdout.splitlines()
                if len(lines)!=16 or lines[-1]!='TOTAL PASS: 15' or any(not x.startswith('PASS: ') for x in lines[:-1]):
                    raise AssertionError(result.stdout)
                outputs.append(result.stdout)
                print(f'{label}: 15 production UI controls passed')
        if outputs[0]!=outputs[1]: raise AssertionError('Interpreter and C disagree')
    verify_compiler(ru_root)
    if SOURCE != (ROOT/'src/main.ru').read_text(encoding='utf-8'):
        raise AssertionError('Production UI source changed during verification')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ru-root',type=Path)
    args,remaining=parser.parse_known_args()
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(DirectoryUIContract))
    if not result.wasSuccessful(): raise SystemExit(1)
    if args.ru_root: run_production(args.ru_root.resolve())
