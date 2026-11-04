"""Cheap architecture checks; behavioral/native assertions live in open_search_native.ru."""
from pathlib import Path
import re
import unittest

SOURCE = (Path(__file__).resolve().parents[1] / 'src/open_search.ru').read_text()


class OpenSearchContract(unittest.TestCase):
    def test_fixed_work_and_result_budgets(self):
        for text in ('候选上限 取 65536.', '每步上限 取 16.', '结果上限 取 2000.',
                     '词上限 取 1024.', "'overlap' 12288", "(界+态['overlap'])", '循 每步上限 次'):
            self.assertIn(text, SOURCE)

    def test_snapshot_does_not_read_text(self):
        snapshot = SOURCE.split('算 新建 ', 1)[1].split('\n法', 1)[0]
        self.assertNotIn('_范围文本', snapshot)
        self.assertNotIn('_搜', snapshot)
        self.assertNotIn('其 文本', snapshot)

    def test_search_uses_stateless_native_find(self):
        self.assertIn('窗 其 发指 柄 2196 标记 范围', SOURCE)
        for message in ('2190', '2192', '2194', '2197', '2198', '2181', '2001', '2011', '2176'):
            self.assertNotRegex(SOURCE, rf'窗 其 (?:发送|发文|发指) [^\n]*\b{message}\b')

    def test_timer_has_no_navigation_or_focus(self):
        tick = SOURCE.split('算 步进 ', 1)[1].split('\n法', 1)[0]
        self.assertNotIn('2160', tick)
        self.assertNotIn('2169', tick)
        self.assertNotIn('SetFocus', SOURCE)
        self.assertLess(tick.index('_有效'), tick.index("文档们[索引]['editor']"))

    def test_state_does_not_capture_native_handles(self):
        snapshot = SOURCE.split("态['documents'] 其 增 ", 1)[1].split('\n', 1)[0]
        self.assertIn("'editorIdentity':(柄 其 句)", snapshot)
        self.assertNotIn("'editor':", snapshot)
        for status in ('running', 'complete', 'cancelled', 'stale', 'limited', 'failed'):
            self.assertIn("'" + status + "'", SOURCE)

    def test_failure_does_not_expose_arbitrary_native_error_text(self):
        self.assertNotIn("'error' (原因 为 句)", SOURCE)
        self.assertIn("若 态['status'] == 'stale' 则 得 假", SOURCE)
        tick = SOURCE.split('算 步进 ', 1)[1].split('\n法', 1)[0]
        guard = "若 态['documentIndex'] < 0 或 态['documentIndex'] >= (态['documents'] 其 量) 则"
        self.assertIn(guard, tick)
        boundary = tick.split(guard, 1)[1].split('\n    然', 1)[0]
        self.assertIn("态 其 增 'status' 'failed'", boundary)
        self.assertIn("态 其 增 'error' 'Open-buffer search could not continue.'", boundary)
        self.assertIn('得 态.', boundary)
        self.assertNotIn('卒 ', boundary)
        self.assertLess(tick.index(guard), tick.index('_有效'))
        self.assertLess(tick.index(guard), tick.index("快照 取 态['documents'][态['documentIndex']]"))

    def test_only_fixed_imports_no_disk_or_replace(self):
        imports = re.findall("外言 '([^']+)'", SOURCE)
        self.assertEqual(imports, ['如:密', 'win32.ru', 'editor.ru', 'search_history.ru'])
        self.assertNotIn('file_codec', SOURCE)


if __name__ == '__main__':
    unittest.main()
