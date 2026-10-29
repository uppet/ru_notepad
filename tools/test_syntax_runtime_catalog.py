#!/usr/bin/env python3
"""Execute unchanged syntax selection bodies with modeled native boundaries.

This checks configuration/lifecycle logic in both ordinary Ru backends. It is not
Windows lexer evidence; the Windows catalog suite must test the real DLL too.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def function(text, name):
    match = re.findall(r'^算 ' + re.escape(name) + r'[^\n]*\n.*?^法\n', text,
                       re.MULTILINE | re.DOTALL)
    if len(match) != 1:
        raise AssertionError('production function missing/ambiguous: ' + name)
    return match[0]


def prepare(directory):
    source = (ROOT / 'src/syntax.ru').read_text(encoding='utf-8')
    modules = {
        'state': """值 取 {'lexer':0,'creates':0,'missing':假,'large':假,'live':真,'thread':真,'status':0,'margin':0,'folds':0,'clear':0,'paint':0,'closed':0,'styles':{},'properties':{},'keywords':{}}.
""",
        'number': """形 数形:
    n 为 数.
    算 数: 得 其 n. 法
象
算 包 数值: 得 新 数形 n:数值. 法
""",
        'memory': """控 取 外言 './state.ru'.
形 缓形:
    文 为 句.
    算 关闭: (控 其 值) 其 增 'closed' ((控 其 值)['closed']+1). 得 空. 法
象
算 UTF8 文本: 得 新 缓形 文:文本. 法
""",
        'pointer': """算 重释 指: 得 指. 法
""",
        'create': """控 取 外言 './state.ru'.
形 指形:
    为空 为 事实.
    编号 为 数.
象
算 调用 参数:
    态 取 控 其 值.
    态 其 增 'creates' (态['creates']+1).
    号 取 3.
    若 (参数[0] 其 文) == 'python' 则 号 取 2. 然
    若 (参数[0] 其 文) == 'json' 则 号 取 120. 然
    若 (参数[0] 其 文) == 'markdown' 则 号 取 98. 然
    若 (参数[0] 其 文) == 'null' 则 号 取 1. 然
    得 新 指形 为空:态['missing'] 编号:号.
法
""",
        'window': """控 取 外言 './state.ru'.
数 取 外言 './number.ru'.
IP 取 外言 './pointer.ru'.
算 结果 果: 得 果. 法
算 发送 柄 号 宽 长:
    态 取 控 其 值.
    若 号 == 4033 则
        码 取 0. 若 长 != 0 则 码 取 长 其 编号. 然
        态 其 增 'lexer' 码.
        态 其 增 'keywords' {}.
        态 其 增 'properties' {}.
    然
    若 号 == 4002 则 得 数 其 包 态['lexer']. 然
    若 号 == 2383 则 得 数 其 包 态['status']. 然
    若 号 == 2243 则 得 数 其 包 态['margin']. 然
    若 号 == 2481 则 得 数 其 包 8947848. 然
    若 号 == 2482 则 得 数 其 包 16448250. 然
    若 号 == 2050 则 态 其 增 'styles' {}. 态 其 增 'clear' (态['clear']+1). 然
    若 号 == 2051 则 (态['styles']) 其 增 (宽 为 句) 长. 然
    若 号 == 2032 则 态 其 增 'paint' (态['paint']+1). 然
    得 数 其 包 0.
法
算 发文 柄 号 宽 文:
    若 号 != 4005 则 卒 'unexpected text operation'. 然
    ((控 其 值)['keywords']) 其 增 (宽 为 句) 文.
    得 数 其 包 0.
法
""",
        'ru': """控 取 外言 './state.ru'.
算 _存在 柄: 得 (控 其 值)['live']. 法
算 _同线程 柄: 得 (控 其 值)['thread']. 法
算 _受限 柄: 得 (控 其 值)['large']. 法
算 _配折叠 柄: (控 其 值) 其 增 'margin' 16. (控 其 值) 其 增 'folds' ((控 其 值)['folds']+1). 得 空. 法
算 选择 柄: 得 'ru'. 法
""",
        'markdown': """算 选择 柄: 得 'markdown'. 法
""",
        'catalog': """算 有语言 语: 得 语 == 'cpp' 或 语 == 'json' 或 语 == 'markdown' 或 语 == 'python' 或 语 == 'java' 或 语 == 'nfo' 或 语 == 'wrong'. 法
算 词法器 语:
    若 语 == 'java' 或 语 == 'wrong' 则 得 'cpp'. 然
    若 语 == 'nfo' 则 得 'null'. 然
    得 语.
法
算 词法号 语:
    若 语 == 'python' 则 得 2. 然
    若 语 == 'json' 则 得 120. 然
    若 语 == 'markdown' 则 得 98. 然
    若 语 == 'nfo' 则 得 1. 然
    若 语 == 'wrong' 则 得 999. 然
    得 3.
法
算 关键词 语:
    若 语 == 'python' 则 得 ['def class return','print']. 然
    若 语 == 'java' 则 得 ['class package public','']. 然
    得 [].
法
算 性质 语:
    若 语 == 'python' 则 得 ['fold','1','lexer.python.strings.b','1']. 然
    若 语 == 'java' 则 得 ['fold','1','lexer.cpp.track.preprocessor','0']. 然
    得 [].
法
算 色号 语: 若 语 == 'nfo' 则 得 []. 然 得 [5,50]. 法
算 色值 语: 若 语 == 'nfo' 则 得 []. 然 得 [12934144,1381795]. 法
算 可折叠 语: 得 语 == 'python' 或 语 == 'java' 或 语 == 'cpp'. 法
""",
    }
    for name, text in modules.items():
        (directory / (name + '.ru')).write_text(text, encoding='utf-8')
    prelude = """控 取 外言 './state.ru'.
窗 取 外言 './window.ru'.
如语 取 外言 './ru.ru'.
标语 取 外言 './markdown.ru'.
谱 取 外言 './catalog.ru'.
密 取 外言 './memory.ru'.
CreateLexer 取 外言 './create.ru'.
词法状态 取 {'ready':真,'warning':'','warningArgs':[]}.
次数 取 [0].
算 确认 条件 为 事实 文 为 句:
    若 非 条件 则 卒 'FAIL: '+文. 然
    次数[0] 取 次数[0]+1.
    显 'PASS: '+文.
    得 空.
法
算 _验选择 态 柄: 得 空. 法
算 _停止折叠 态 柄: (控 其 值) 其 增 'margin' 0. 得 空. 法
算 _性质 态 柄 键 为 句 值 为 句: ((控 其 值)['properties']) 其 增 键 值. 得 空. 法
"""
    bodies = ''.join(function(source, name) for name in
                     ('_发设', '_发文设', '_配色', '_清样式', '_纯文', '_选择', '_原生折叠'))
    probe = """态 取 控 其 值.
确认 ((_选择 空 1 'python') == 'python') 'catalog native language selected'.
确认 (态['lexer'] == 2 且 态['creates'] == 1) 'fresh exact lexer created'.
确认 ((态['keywords'] 其 查 '0') == 'def class return' 且 (态['keywords'] 其 查 '1') == 'print') 'all keyword slots applied'.
确认 ((态['properties'] 其 查 'fold') == '1' 且 (态['properties'] 其 查 'lexer.python.strings.b') == '1') 'all catalog property pairs applied'.
确认 ((态['styles'] 其 查 '50') == 1381795) 'embedded style above 39 configured'.
确认 ((态['styles'] 其 查 '33') == 8947848) 'line number palette preserved'.
确认 (态['margin'] == 16 且 _原生折叠 1) 'catalog native folding enabled'.
确认 (态['paint'] == 1) 'native styling cursor reset without full recolour'.
确认 ((_选择 空 1 'java') == 'java') 'shared cpp lexer language selected'.
确认 (态['creates'] == 2 且 态['lexer'] == 3) 'shared lexer gets new object'.
确认 ((态['properties'] 其 查 'lexer.python.strings.b') == 空) 'old properties cannot leak'.
确认 ((态['keywords'] 其 查 '1') == '') 'explicit empty word list applied'.
确认 ((_选择 空 1 'cpp') == 'cpp') 'legacy cpp remains selected'.
确认 ((态['styles'] 其 查 '50') == 空) 'high native style cleared on switch'.
确认 ((态['properties'] 其 查 'fold.preprocessor') == '1' 且 _原生折叠 1) 'legacy cpp folding preserved'.
确认 ((_选择 空 1 'json') == 'json') 'legacy json remains selected'.
确认 (非 (_原生折叠 1) 且 (态['keywords'] 其 查 '0') == 'true false null') 'json remains nonfolding with exact words'.
确认 ((_选择 空 1 'markdown') == 'markdown') 'custom Markdown remains selected'.
确认 (非 (_原生折叠 1)) 'Markdown never uses native folding dispatcher'.
确认 ((_选择 空 1 'nfo') == 'nfo' 且 态['lexer'] == 1) 'NFO null lexer retains explicit mode identity'.
确认 (非 (_原生折叠 1)) 'null lexer never folds'.
前 取 态['creates'].
确认 ((_选择 空 1 'unknown') == 'plain' 且 态['creates'] == 前) 'unknown language safely falls back without native creation'.
确认 ((_选择 空 1 'ru') == 'ru' 且 态['creates'] == 前) 'Ru custom lexer retains path'.
态 其 增 'large' 真.
确认 ((_选择 空 1 'python') == 'plain' 且 态['creates'] == 前) 'large document guard preserved'.
态 其 增 'large' 假.
词法状态 其 增 'ready' 假.
确认 ((_选择 空 1 'python') == 'plain' 且 态['creates'] == 前) 'unavailable library fails closed'.
词法状态 其 增 'ready' 真.
态 其 增 'missing' 真.
确认 ((_选择 空 1 'python') == 'plain' 且 词法状态['warning'] == 'error.syntax.language_unavailable') 'missing native lexer records warning'.
态 其 增 'missing' 假.
确认 ((_选择 空 1 'wrong') == 'plain' 且 词法状态['warning'] == 'error.syntax.language_configuration') 'wrong actual native identity rejected'.
态 其 增 'status' 1.
确认 ((_选择 空 1 'java') == 'plain') 'Scintilla failure rejected'.
态 其 增 'status' 0.
_选择 空 1 'python'.
态 其 增 'thread' 假.
确认 (非 (_原生折叠 1)) 'wrong thread never enters native folding'.
态 其 增 'thread' 真.
态 其 增 'live' 假.
确认 (非 (_原生折叠 1)) 'destroyed editor never enters native folding'.
确认 (态['closed'] == 态['creates']) 'every creation buffer closed'.
显 'TOTAL PASS: '+(次数[0] 为 句).
"""
    path = directory / 'probe.ru'
    path.write_text(prelude + bodies + probe, encoding='utf-8')
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ru-root', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    ru = args.ru_root.resolve() / 'ru'
    with tempfile.TemporaryDirectory(prefix='ru-syntax-catalog-') as temporary:
        directory = args.output.resolve() if args.output else Path(temporary)
        directory.mkdir(parents=True, exist_ok=True)
        probe = prepare(directory)
        binary = directory / 'probe'
        commands = [[sys.executable, str(ru), 'run', str(probe)],
                    [sys.executable, str(ru), 'build', '--cc', 'gcc', str(probe), '-o', str(binary)],
                    [str(binary)]]
        for i, command in enumerate(commands):
            result = subprocess.run(command, text=True, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, timeout=180)
            (directory / f'phase-{i}.log').write_text(result.stdout, encoding='utf-8')
            if result.returncode:
                raise SystemExit(result.stdout)
            if i != 1 and (result.stdout.count('PASS: ') != 32 or
                           re.findall(r'^TOTAL PASS: (\d+)$', result.stdout, re.M) != ['31']):
                raise SystemExit('incorrect assertion count:\n' + result.stdout)
        print('PASS: 31 extracted production configuration assertions in interpreter and C')


if __name__ == '__main__':
    main()
