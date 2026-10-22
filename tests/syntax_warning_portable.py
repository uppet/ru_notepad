#!/usr/bin/env python3
"""Execute production warning storage/projection in both ordinary Ru backends.

Only window/scanner operations are modeled. Actual production selection, rescue,
warning formatting and status functions are extracted unchanged, with the real
seven-language catalog. This is not native Windows, document/undo, or HWND QA.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from ru_cli_diagnostics import prepare_compile_diagnostics
from test_i18n import CleanupError, checked_run, compiler_snapshot, file_sha256
LANGUAGES = ('en', 'zh-CN', 'ja', 'ko', 'es', 'ru', 'it')


def function_source(path, name, parse):
    source = path.read_text(encoding='utf-8')
    program = parse(source)
    matches = [i for i, node in enumerate(program)
               if node.kind == 'function' and node.data['name'] == name]
    if len(matches) != 1:
        raise AssertionError(f'Expected exactly one production function: {name}')
    index = matches[0]
    first = program[index].token.line - 1
    last = program[index + 1].token.line - 1 if index + 1 < len(program) else None
    return ''.join(source.splitlines(keepends=True)[first:last])


SHARED = """本地 取 外言 './i18n.ru'.
窗 取 外言 './window_stub.ru'.
次数 取 [0].
算 确认 条件 为 事实 文 为 句:
    若 非 条件 则 卒 'FAIL: '+文. 然
    次数[0] 取 次数[0]+1.
    得 空.
法
"""
WINDOW = """值 取 外言 './handle_stub.ru'.
调用 取 [0].
算 发送 柄 号 宽 长:
    调用[0] 取 调用[0]+1.
    得 值.
法
"""
SCANNER = """本地 取 外言 './i18n.ru'.
_模式 取 [0].
调用 取 [0].
_库态 取 {'ready':真,'warning':'','warningArgs':[]}.
算 设置 模式 为 数:
    _模式[0] 取 模式.
    _库态 其 增 'ready' (模式 != 3).
    _库态 其 增 'warning' ''.
    若 模式 == 3 则
        _库态 其 增 'warning' 'error.syntax.ru_missing'.
        _库态 其 增 'warningArgs' (['126']).
    然
    得 空.
法
算 可用: 得 _库态['ready']. 法
算 新状态:
    调用[0] 取 调用[0]+1.
    若 _模式[0] == 1 则 卒 'technical {0} new-state'. 然
    得 {'references':1}.
法
算 复制状态 态:
    调用[0] 取 调用[0]+1.
    若 _模式[0] == 2 则 卒 'technical {1} checkpoint'. 然
    得 {'references':1}.
法
算 释放 态:
    若 态 != 空 则
        调用[0] 取 调用[0]+1.
        若 态['references'] != 1 则 卒 'double release'. 然
        态 其 增 'references' 0.
    然
    得 空.
法
"""
RU = """词 取 外言 './scanner_stub.ru'.
_编辑们 取 {}. _序号 取 [0].
算 _存在 柄: 得 真. 法
算 _受限 柄: 得 假. 法
算 停用 柄: 得 空. 法
算 _全显 柄: 得 空. 法
算 _配折叠 柄: 得 空. 法
算 _状态 柄: 得 _编辑们 其 查 (柄 其 句). 法
"""
MD = """策 取 外言 './markdown_policy.ru'.
增策 取 外言 './markdown_incremental.ru'.
_编辑们 取 {}. _身份 取 [0].
_批统计们 取 {}. _直属们 取 {}.
_增量们 取 {}. _增量策略 取 {'enabled':假}.
清理 取 [0,假].
算 _线程: 得 'modeled-thread'. 法
算 _同线程 柄: 得 真. 法
算 _本态 柄 态: 得 态['alive']. 法
算 _可见完成 柄 态:
    清理[0] 取 清理[0]+1.
    若 清理[1] 则 卒 'technical {1} cleanup'. 然
    态 其 增 'pending' 假.
    态 其 增 'phase' 'disabled'.
    得 空.
法
"""
PROBE_RU = """柄 取 外言 './handle_stub.ru'.
算 检查切换 模式 为 数:
    词 其 设置 模式.
    本地 其 设置 'en'.
    选择 柄.
    态 取 _状态 柄.
    若 模式 == 0 则 _失败 柄 态 'technical {0} runtime'. 然
    前 取 状态 柄.
    扫描数 取 (词 其 调用)[0].
    消息数 取 (窗 其 调用)[0].
    键 取 态['warning'].
    参数 取 态['warningArgs'].
    初词 取 态['lexical'].
    初点 取 态['points'].
    位 取 0.
    循 8 次
        语言 取 (本地 其 语言们)[位%7].
        本地 其 设置 语言.
        后 取 状态 柄.
        确认 ((词 其 调用)[0] == 扫描数 且 (窗 其 调用)[0] == 消息数) 'status does not restart scanner or send native messages'.
        确认 (后['generation'] == 前['generation'] 且 后['revision'] == 前['revision'] 且 后['language'] == 前['language'] 且 后['pending'] == 前['pending']) 'status preserves generation and syntax identity'.
        确认 (态['warning'] == 键 且 态['warningArgs'] == 参数 且 态['lexical'] == 初词 且 态['points'] == 初点) 'status preserves raw reason and scanner roots'.
        显 'ru|'+(模式 为 句)+'|'+语言+'|'+后['warning'].
        位 取 位+1.
    环
    得 空.
法
检查切换 0. 检查切换 1. 检查切换 2. 检查切换 3.
显 'ASSERTIONS: '+(次数[0] 为 句).
"""
PROBE_MD = """柄 取 外言 './handle_stub.ru'.
算 检查切换 层数 为 数:
    本地 其 设置 'en'.
    态 取 _建态 柄 37 4 'modeled-document'.
    态 其 增 'registered' 真.
    _编辑们 其 增 (柄 其 句) 态.
    清理[1] 取 层数 > 0.
    _失败 柄 态 'technical {0} policy'.
    若 层数 == 2 则
        (态['warningRecovery']) 其 增 'technical {2} second cleanup'.
    然
    # The actual edit-invalidation path must retain every raw diagnostic layer.
    变化 柄 0 1 0 1.
    态 取 _编辑们 其 查 (柄 其 句).
    前 取 状态 柄.
    清理数 取 清理[0].
    消息数 取 (窗 其 调用)[0].
    键 取 态['warning'].
    参数 取 态['warningArgs'].
    恢复 取 态['warningRecovery'].
    位 取 0.
    循 8 次
        语言 取 (本地 其 语言们)[位%7].
        本地 其 设置 语言.
        后 取 状态 柄.
        确认 (清理[0] == 清理数 且 (窗 其 调用)[0] == 消息数) 'status does not restart policy or visibility recovery'.
        确认 (后['generation'] == 前['generation'] 且 后['revision'] == 前['revision'] 且 后['identity'] == 前['identity'] 且 后['language'] == 'markdown' 且 非 后['foldEnabled']) 'status preserves Markdown identities and disabled folds'.
        确认 (态['warning'] == 键 且 态['warningArgs'] == 参数 且 态['warningRecovery'] == 恢复 且 后['readBytes'] == 0 且 后['published'] == 0) 'status retains raw diagnostic layers without scanner work'.
        显 'md|'+(层数 为 句)+'|'+语言+'|'+后['warning'].
        位 取 位+1.
    环
    得 空.
法
检查切换 0. 检查切换 1. 检查切换 2.
显 'ASSERTIONS: '+(次数[0] 为 句).
"""


def prepare(directory, kind, parse):
    for name in ('i18n.ru', 'i18n_catalog.ru', 'markdown_policy.ru', 'markdown_ascii_kernel.ru', 'markdown_incremental.ru'):
        shutil.copyfile(ROOT / 'src' / name, directory / name)
    (directory / 'handle_stub.ru').write_text("句 取 'synthetic-editor'. 数 取 0.\n", encoding='utf-8', newline='\n')
    (directory / 'window_stub.ru').write_text(WINDOW, encoding='utf-8', newline='\n')
    native = ROOT / 'src/ru_native_syntax.ru'
    (directory / 'scanner_stub.ru').write_text(SCANNER + function_source(native, '初始化', parse), encoding='utf-8', newline='\n')
    path = ROOT / ('src/ru_syntax.ru' if kind == 'ru' else 'src/markdown_syntax.ru')
    names = (('_放点', '_放候', '_放态', '_警告', '_失败', '_初始化失败', '选择', '状态') if kind == 'ru'
             else ('_建态', '_统计', '_增量', '_丢弃', '撤销直属', '_警告', '_失败', '变化', '状态'))
    source = SHARED + (RU if kind == 'ru' else MD)
    source += ''.join(function_source(path, name, parse) for name in names)
    source += PROBE_RU if kind == 'ru' else PROBE_MD
    if "如:密" in source:
        raise AssertionError('Portable extraction unexpectedly contains native capability')
    target = directory / 'probe.ru'
    target.write_text(source, encoding='utf-8', newline='\n')
    return target


def expected_output(kind):
    catalog = json.loads((ROOT / 'locales/errors.json').read_text(encoding='utf-8'))
    rows = []
    cases = range(4) if kind == 'ru' else range(3)
    keys = ('ru_disabled', 'ru_initialization', 'ru_initialization', 'ru_missing')
    reasons = ('technical {0} runtime', 'technical {0} new-state', 'technical {1} checkpoint', '126')
    for case in cases:
        for language in (*LANGUAGES, 'en'):
            key = 'error.syntax.' + (keys[case] if kind == 'ru' else 'markdown_disabled')
            text = catalog[key][language].replace('{0}', reasons[case] if kind == 'ru' else 'technical {0} policy')
            if kind == 'md':
                for reason in ('technical {1} cleanup', 'technical {2} second cleanup')[:case]:
                    # Replace slots in one pass: inserted reasons containing {n}
                    # must remain literal, exactly as the production formatter.
                    template = catalog['error.syntax.visibility_recovery'][language]
                    text = template.format(text, reason)
            rows.append(f'{kind}|{case}|{language}|{text}')
    rows.append('ASSERTIONS: ' + str(len(cases) * 8 * 3))
    return '\n'.join(rows) + '\n'


def source_snapshot():
    # Every copied source, extracted body, JSON oracle and host consumer is bound
    # before parsing, and checked again before publishing any successful receipt.
    names = ('src/i18n.ru', 'src/i18n_catalog.ru', 'src/markdown_policy.ru',
             'src/markdown_ascii_kernel.ru', 'src/markdown_incremental.ru', 'src/ru_native_syntax.ru', 'src/ru_syntax.ru', 'src/markdown_syntax.ru',
             'locales/errors.json', 'locales/ui.json', 'tests/syntax_warning_portable.py',
             'tools/test_i18n.py', 'tools/generate_i18n.py', 'tools/ru_cli_diagnostics.py')
    result = {}
    for name in names:
        path = ROOT / name
        if path.is_symlink() or not path.is_file() or ROOT not in path.resolve().parents:
            raise RuntimeError('Warning fixture input is missing, linked or outside its checkout')
        result[name] = file_sha256(path)
    return result


def checked(command, timeout=120, *, compile_diagnostics=None, log, records=None):
    data = checked_run(command, log.parent, log.name, timeout, records,
                       compile_diagnostics=compile_diagnostics)
    return data.decode('utf-8', 'strict').replace('\r\n', '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ru-root', type=Path, required=True)
    parser.add_argument('--cc', default='gcc')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/syntax-warning-evidence')
    args = parser.parse_args()
    ru = args.ru_root.resolve()
    compiler_before = compiler_snapshot(ru)
    before = source_snapshot()
    args.output.mkdir(parents=True, exist_ok=False)
    report = {'schema': 1, 'passed': False, 'source_sha256': before,
              'compiler': compiler_before, 'native_windows_ui_executed': False,
              'fixture_source_sha256': {}, 'generated_c_sha256': {}, 'cases': [], 'commands': []}
    try:
        sys.path.insert(0, str(ru))
        from rulang.frontend import parse
        for kind in ('ru', 'md'):
            directory = Path(tempfile.mkdtemp(prefix='ru-warning-i18n-')).resolve()
            cleanup_allowed = True
            try:
                logs = ROOT / 'build/syntax-warning-private' / directory.name
                logs.mkdir(parents=True, exist_ok=False)
                source = prepare(directory, kind, parse)
                report['fixture_source_sha256'][kind] = {
                    path.name: file_sha256(path) for path in sorted(directory.glob('*.ru'))}
                shutil.copytree(directory, logs / 'fixture')
                executable = directory / ('probe.exe' if sys.platform == 'win32' else 'probe')
                generated_c = directory / 'probe.c'
                interpreted = checked([sys.executable, str(ru / 'ru'), 'run', str(source)],
                                      log=logs / (kind + '-interpreter'), records=report['commands'])
                build_command = [sys.executable, str(ru / 'ru'), 'build', '--cc', args.cc,
                                 str(source), '--emit-c', str(generated_c), '-o', str(executable)]
                diagnostics = prepare_compile_diagnostics(build_command, ru, source)
                checked(build_command, compile_diagnostics=diagnostics,
                        log=logs / (kind + '-build'), records=report['commands'])
                compiled = checked([str(executable)], 30, log=logs / (kind + '-host-c'),
                                   records=report['commands'])
                expected = expected_output(kind)
                if interpreted != expected or compiled != expected:
                    raise RuntimeError('Exact seven-language warning output or assertions differ')
                if (source_snapshot() != before or report['fixture_source_sha256'][kind] != {
                        path.name: file_sha256(path) for path in sorted(directory.glob('*.ru'))}):
                    raise RuntimeError('Warning fixture sources changed during backend verification')
                for backend, output in (('interpreter', interpreted), ('host-c', compiled)):
                    (args.output / (kind + '-' + backend + '.log')).write_text(
                        output, encoding='utf-8', newline='\n')
                    report['cases'].append({'fixture': kind, 'backend': backend,
                                            'warnings': len(expected.splitlines()) - 1})
                report['generated_c_sha256'][kind] = file_sha256(generated_c)
            except CleanupError:
                cleanup_allowed = False
                raise
            finally:
                if cleanup_allowed:
                    shutil.rmtree(directory)
        if compiler_snapshot(ru) != compiler_before or source_snapshot() != before:
            raise RuntimeError('Warning verification inputs changed during backend verification')
        report['passed'] = True
    except BaseException:
        report['error'] = 'syntax_warning_backend_failed'
        raise
    finally:
        (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n',
                                               encoding='utf-8', newline='\n')
    for case in report['cases'][::2]:
        print(f"SYNTAX_WARNING_PORTABLE_PASS: {case['fixture']} {case['warnings']} localized warnings x 2 backends")


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, ValueError, OSError, UnicodeError, subprocess.SubprocessError,
            AssertionError, ImportError):
        print('SYNTAX_WARNING_PORTABLE_FAILED; raw diagnostics retained privately', file=sys.stderr)
        raise SystemExit(1)
