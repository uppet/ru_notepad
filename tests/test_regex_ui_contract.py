"""Source-level UI safety contracts. Actual Windows behavior is a separate gate.

These tests intentionally assert production paths, not a second Python UI model.
"""
from pathlib import Path
import re
import unittest

SOURCE = (Path(__file__).resolve().parents[1] / 'src/main.ru').read_text()


def body(name):
    return SOURCE.split('算 ' + name, 1)[1].split('\n法', 1)[0]


class RegexUIContract(unittest.TestCase):
    def test_literal_is_default_and_modes_are_explicit(self):
        self.assertIn("'regexMode':假", SOURCE)
        for command, mode in ((323, '假'), (324, '真')):
            self.assertIn(f'若 号 == {command} 则 正则模式 {mode}. 得 空.', SOURCE)
        self.assertIn("若 号 == 323 且 非 (A 其 查 'regexMode') 则 标记 取 8", SOURCE)
        self.assertIn("若 号 == 324 且 (A 其 查 'regexMode') 则 标记 取 8", SOURCE)

    def test_menu_shape_and_stop_state(self):
        menu = body('菜单:')
        counts = re.search(r'组量们 取 \[([^]]+)\]', menu).group(1)
        self.assertEqual([int(v) for v in counts.split(',')], [11, 19, 14, 6, 5, 7, 5, 8, 1])
        self.assertIn('323, 324, 325', menu)
        self.assertIn("工作['status'] != 'running' 则 标记 取 3", menu)
        self.assertIn("工作['status'] == 'running' 则 旗 取 0", body('正则菜单状态:'))
        self.assertIn('正则菜单状态. 行序菜单状态.', SOURCE)

    def test_controls_and_shortcuts_are_not_added(self):
        self.assertIn("控们 取 ['find','replace','scope','case','whole','searchWrap','previous','next','one','all','hide']", body('寻栏 '))
        self.assertNotIn('regex', body('快捷 '))
        for ident in (323, 324, 325):
            self.assertNotRegex(SOURCE, rf'窗 其 控制[^\n]*\b{ident}\b')

    def test_literal_options_restore_and_regex_controls_disable(self):
        mode = body('正则模式 ')
        for name, saved, forced in (('case', 'regexCase', 1), ('whole', 'regexWhole', 0)):
            self.assertIn(f"A 其 增 '{saved}' ((窗 其 发送 (A 其 查 '{name}') 240 0 0) 其 数)", mode)
            self.assertIn(f"窗 其 发送 (A 其 查 '{name}') 241 {forced} 0", mode)
            self.assertIn(f"窗 其 发送 (A 其 查 '{name}') 241 (A 其 查 '{saved}') 0", mode)
        state = body('搜索状态:')
        self.assertIn("若 A 其 查 'regexMode' 则 可换 取 0. 可选 取 0", state)
        for name in ('case', 'whole', 'replace'):
            self.assertIn(f"[(A 其 查 '{name}'),可选]", state)
        self.assertNotIn("[(A 其 查 'searchWrap'),可选]", state)
        self.assertIn("'regex.scope_'+(A 其 查 'searchScope')", state)

    def test_disallowed_direct_dispatch_precedes_all_open_and_literal(self):
        command = body('命令 ')
        guard = "(号 == 302 或 号 == 304 或 号 == 305 或 号 == 317"
        self.assertLess(command.index(guard), command.index('若 号 == 317 则 启动全文档搜索'))
        self.assertLess(command.index(guard), command.index('若 号 == 301 或 号 == 302'))
        self.assertLess(command.index('启动正则搜索 号'), command.index('编 其 寻找范围'))
        self.assertIn("若 A 其 查 'regexMode' 则 提示", body('启动全文档搜索:'))

    def test_empty_query_and_rejected_program_do_not_enter_history(self):
        start = body('启动正则搜索 ')
        empty = "若 词 == '' 则 寻栏 真. 得 空. 然"
        self.assertLess(start.index(empty), start.index('正编 其 编译'))
        self.assertLess(start.index("程序['status'] != 'ok'"), start.index("A 其 增 'findHistory'"))
        rejected = start.split("程序['status'] != 'ok'", 1)[1].split('\n    然', 1)[0]
        self.assertIn('得 空.', rejected)
        self.assertNotIn('寻史', rejected)
        self.assertIn("(程序['index']+1)", rejected)
        self.assertIn('regex.pattern_error', rejected)
        self.assertNotIn('原因 为 句', start)

    def test_hidden_bar_shortcuts_show_before_scheduling_and_keep_scope_guard(self):
        command = body('命令 ')
        self.assertIn("(号 == 303 或 号 == 308) 则 启动正则搜索 号. 得 空.", command)
        start = body('启动正则搜索 ')
        show = "若 非 (A 其 查 'search') 则 寻栏 真. 然"
        self.assertIn(show, start)
        self.assertLess(start.index("'searchScope') == 'invalid'"), start.index(show))
        invalid = start.split("'searchScope') == 'invalid'", 1)[1].split('然', 1)[0]
        self.assertIn('得 空.', invalid)
        self.assertLess(start.index(show), start.index('正编 其 编译'))
        self.assertLess(start.index(show), start.index('正寻 其 新建'))
        self.assertLess(start.index(show), start.index('SetTimer'))

    def test_compile_reasons_are_localized_and_internal_is_generic(self):
        reason = body('正则编译原因 ')
        for code in ('nullable_repeat', 'pattern-limit', 'compile-limit', 'state-limit', 'unsupported-escape', 'possessive-quantifier'):
            self.assertIn(code, reason)
        self.assertIn("错[:9] == 'internal-'", reason)
        self.assertIn('regex.reason_internal', reason)

    def test_scope_is_captured_not_transient_selection(self):
        start = body('启动正则搜索 ')
        self.assertIn("始 取 A 其 查 'scopeStart'. 末 取 A 其 查 'scopeEnd'", start)
        self.assertNotIn('2143', start)
        self.assertNotIn('2145', start)
        self.assertIn("方向 取 'previous'", start)
        self.assertIn('正寻 其 新建 文档 程序 始 末 方向 循环 零', start)

    def test_timer_admission_and_one_slice(self):
        tick = body('正则时钟:')
        for guard in ('regexTick', 'busy', 'modalDepth', 'closeRun', 'tabMenuOpen', 'closeIndex'):
            self.assertIn(f"A 其 查 '{guard}'", tick.split('工作 取', 1)[0])
        self.assertEqual(tick.count('正寻 其 步进'), 1)
        self.assertIn('文档 取 正则当前', tick)
        self.assertIn("904,20,空", body('启动正则搜索 '))
        for forbidden in ('GetMessage', 'PeekMessage', '菜单.', '循'):
            self.assertNotIn(forbidden, tick)
        self.assertIn('== 904 则 正则时钟', SOURCE)

    def test_final_selection_once_and_own_selection_notifications_safe(self):
        tick = body('正则时钟:')
        self.assertEqual(tick.count('正寻 其 定位'), 1)
        self.assertLess(tick.index("'regexApplying' 真"), tick.index('正寻 其 定位'))
        self.assertLess(tick.index('正寻 其 定位'), tick.index('正则记选 文档'))
        self.assertIn('正寻 其 零标记 工作', tick)
        changed = body('正则选区变化 ')
        self.assertIn("A 其 查 'regexApplying'", changed)
        self.assertLess(changed.index("'untitledNumber'"), changed.index('窗 其 发送'))
        for field in ('regexAnchor', 'regexCaret'):
            self.assertIn(field, changed)
        self.assertIn('若 码 == 2007 则 正则选区变化 文档', SOURCE)

    def test_completed_zero_survives_only_unchanged_no_match(self):
        start = body('启动正则搜索 ')
        save = "零 取 A 其 查 'regexZero'"
        restore = "A 其 增 'regexZero' 零"
        self.assertLess(start.index(save), start.index("停正则 'regex.cancelled'"))
        self.assertLess(start.index('正则记选 文档'), start.index(restore))
        gate = start.split('若 零 != 空 则', 1)[1].split(restore, 1)[0]
        for field in ('query', 'scopeStart', 'scopeEnd', 'direction',
                      'untitledNumber', 'editorIdentity', 'revision', 'length', 'position'):
            self.assertIn(f"零['{field}']", gate)
        for selection in ('regexAnchor', 'regexCaret'):
            self.assertIn(selection, gate)
        end = body('正则结束 ')
        self.assertIn("若 工作['status'] != 'match' 且 工作['status'] != 'no-match' 则 A 其 增 'regexZero' 空", end)
        tick = body('正则时钟:')
        self.assertIn("A 其 增 'regexZero' (正寻 其 零标记 工作)", tick)
        self.assertIn("A 其 增 'regexZero' 空", body('停正则 '))

    def test_query_and_control_changes_cancel_and_clear_marker(self):
        handler = body('消息处理 ')
        branch = handler.split('== 310 且', 1)[1].split('== 320 且', 1)[0]
        self.assertIn('== 768', branch)
        self.assertIn("((A 其 查 'find') 其 句)", branch)
        self.assertIn("停正则 'regex.cancelled'", branch)
        command = body('命令 ')
        for ident in (312, 314):
            self.assertIn(f"若 号 == {ident} 则 停正则 'regex.cancelled'", command)
        self.assertIn("停正则 'regex.cancelled'", body('捕获搜索选区:'))
        self.assertIn("A 其 增 'regexZero' 空", body('停正则 '))
        self.assertIn("A 其 增 'regexJob' 空", body('停正则 '))

    def test_edit_tab_close_and_window_destroy_invalidate(self):
        self.assertIn("停正则 'regex.stale'", body('结果失效:'))
        self.assertIn("停正则 'regex.stale'", body('搜索失效:'))
        self.assertIn('搜索失效', body('切页 '))
        self.assertIn('结果失效', body('删除当前页:'))
        self.assertIn('搜索失效', body('寻栏 '))
        destroy = body('消息处理 ').split('若 号 == 2 则', 1)[1].split("若 A 其 查 'ready'", 1)[0]
        self.assertIn("停正则 'regex.cancelled'", destroy)
        self.assertIn(",904]", body('停正则 '))

    def test_result_statuses_are_distinct_and_nonmodal(self):
        end = body('正则结束 ')
        for status in ('match', 'no-match', 'limit', 'stale', 'cancelled'):
            self.assertIn(f"工作['status'] == '{status}'", end)
        for key in ('regex.failed', 'search.no_match', 'regex.limit', 'regex.stale', 'regex.cancelled'):
            self.assertIn(key, end)
        self.assertNotIn('提示', end)
        self.assertNotIn('提示', body('正则时钟:'))
        self.assertIn("(A 其 查 'statusBase')", body('正则状态:'))
        self.assertIn('正则状态文', body('刷新:'))

    def test_file_operation_status_owns_busy_interval_during_invalidation(self):
        status = body('正则状态:')
        self.assertIn("若 (A 其 查 'ready') 且 非 (A 其 查 'busy') 则", status)
        self.assertIn('正则状态.', body('停正则 '))
        self.assertIn("停正则 'regex.stale'", body('结果失效:'))
        self.assertIn("停正则 'regex.stale'", body('搜索失效:'))
        register = body('登记页 ')
        self.assertLess(register.index('结果失效.'), register.index('4926'))
        switch = body('切页 ')
        self.assertLess(switch.index('搜索失效.'), switch.index("A 其 增 'active'"))
        finish = body('结束工作:')
        self.assertLess(finish.index("A 其 增 'busy' 假"), finish.index('刷新.'))

    def test_no_local_status_module_shadowing_or_text_mutation(self):
        regex = SOURCE.split('# Regex jobs own no HWNDs.', 1)[1].split('# Read-only all-open-buffer', 1)[0]
        self.assertNotRegex(regex, r'(?m)^\s*态 取')
        for message in (2001, 2003, 2011, 2176, 2181, 2190, 2192, 2194, 2197, 2198):
            self.assertNotRegex(regex, rf'窗 其 (?:发送|发文|发指) [^\n]*\b{message}\b')


if __name__ == '__main__':
    unittest.main()
