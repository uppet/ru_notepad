#!/usr/bin/env python3
"""Hostile stage-stream controls; synthetic data is not native execution."""
from pathlib import Path
import re
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_focused_native_diagnostic as runner


def expected():
    rows = [(0, 7, 0, 1)]
    for language in range(7):
        for stage, width, offset in ((1, 0, 9), (2, 0, 12), (3, 0, 90),
                (4, 0, 124), (5, 0, 154), (6, 640, 158), (6, 900, 181), (6, 1600, 204)):
            rows.append((stage, language, width, offset + language * 218))
    return rows + [(7, 7, 0, 1535), (8, 7, 0, 1596), (9, 7, 0, 1604), (10, 7, 0, 1606)]


def marker(row):
    return ('I18N_STAGE stage=%d language=%d width=%d next=%d\n' % row).encode('ascii')


def stream(rows=None, *, tail=0):
    rows = expected() if rows is None else rows
    output, passed = b'', 0
    for row in rows:
        output += b'PASS: synthetic private label\n' * (row[3] - passed - 1)
        passed = row[3] - 1
        output += marker(row)
    return output + b'PASS: synthetic private label\n' * tail


class StageProgressControls(unittest.TestCase):
    def reject(self, output, *, complete=False):
        with self.assertRaises(ValueError):
            runner.parse_i18n_progress(output, complete=complete)

    def test_exact_61_stage_search_enhanced_assertion_contract(self):
        self.assertEqual(len(expected()), 61)
        self.assertEqual(tuple(expected()), runner.I18N_STAGE_SEQUENCE)
        for ending in (b'\n', b'\r\n'):
            raw = (stream(tail=1) + b'TOTAL PASS: 1606\n').replace(b'\n', ending)
            self.assertEqual(runner.parse_i18n_progress(raw, complete=True),
                             dict(stage=10, language=7, width=0, next=1606))

    def test_every_prefix_can_report_only_its_last_stage(self):
        rows = expected()
        for count in range(1, len(rows) + 1):
            with self.subTest(count=count):
                last = rows[count - 1]
                self.assertEqual(runner.parse_i18n_progress(stream(rows[:count])),
                                 dict(zip(('stage', 'language', 'width', 'next'), last)))
                if count < len(rows):
                    self.reject(stream(rows[:count]), complete=True)

    def test_spanish_filter_stage_failure_never_exposes_private_strings(self):
        rows = expected()
        end = rows.index((5, 4, 0, 1026)) + 1
        raw = stream(rows[:end]) + 'runtime error C:\\private\\用户文档.txt\n'.encode('utf-8')
        with tempfile.TemporaryDirectory() as tmp:
            logs = Path(tmp)
            (logs / 'app_i18n_native.stdout.log').write_bytes(raw)
            self.assertEqual(runner.failure_progress(logs),
                             'FOCUSED_I18N_PROGRESS stage=5 language=4 width=0 next=1026')

    def test_historical_1417_contract_cannot_certify_current_fixture(self):
        # October 20's prior fixture stopped at 908, before Spanish filter
        # assertion 909. Preserve that historical count; do not relabel old
        # evidence as the new 1606-assertion search-enhanced contract.
        old_rows = [(0, 7, 0, 1)]
        for language in range(7):
            for stage, width, offset in ((1, 0, 9), (2, 0, 12), (3, 0, 89),
                    (4, 0, 115), (5, 0, 145), (6, 640, 149), (6, 900, 166), (6, 1600, 183)):
                old_rows.append((stage, language, width, offset + language * 191))
        old_rows.extend(((7, 7, 0, 1346), (8, 7, 0, 1407),
                         (9, 7, 0, 1415), (10, 7, 0, 1417)))
        spanish_end = old_rows.index((5, 4, 0, 909)) + 1
        self.reject(stream(old_rows[:spanish_end]))
        self.reject(stream(old_rows, tail=1) + b'TOTAL PASS: 1417\n', complete=True)

    def test_duplicate_missing_reordered_and_extra_markers_fail_closed(self):
        good = stream(tail=1)
        first, second, third = map(marker, expected()[:3])
        for bad in (good.replace(first, b'', 1), good.replace(second, b'', 1),
                    good.replace(second, second * 2, 1),
                    good.replace(second, third, 1), good + marker(expected()[-1]),
                    second + good, good.replace(second, b'PLACEHOLDER', 1).replace(third, second, 1).replace(b'PLACEHOLDER', third, 1)):
            self.reject(bad)

    def test_missing_middle_marker_cannot_borrow_later_pass_lines(self):
        rows = expected()
        partial = stream(rows[:3], tail=78)
        # The menu stage cannot consume more than 78 PASS records before text.
        self.assertEqual(runner.parse_i18n_progress(partial)['stage'], 2)
        self.reject(partial + b'PASS: unannounced later assertion\n')

    def test_wrong_ranges_types_labels_and_noncanonical_numbers_rejected(self):
        first = marker(expected()[0])
        for bad in (
                b'I18N_STAGE stage=11 language=7 width=0 next=1\n',
                b'I18N_STAGE stage=0 language=8 width=0 next=1\n',
                b'I18N_STAGE stage=0 language=0 width=0 next=1\n',
                b'I18N_STAGE stage=0 language=7 width=640 next=1\n',
                b'I18N_STAGE stage=0 language=7 width=0 next=0\n',
                b'I18N_STAGE stage=0 language=7 width=0 next=1608\n',
                first.replace(b'stage=0', b'stage=00'),
                first.replace(b'next=1', b'next=01'),
                first.replace(b'next=1', b'next=1.0'),
                first.replace(b'next=1', b'next=+1'),
                first.replace(b'next=1', b'next=true'),
                first.replace(b'next=1', b'next=9999999999999999999999999'),
                first.rstrip(b'\n') + b' path=C:\\private\\secret\n',
                first.replace(b'language=7 ', b''), first.replace(b' width=0', b' language=7 width=0'),
                first.replace(b'language=7 width=0', b'width=0 language=7'),
                first.replace(b'I18N_STAGE', b'prefix I18N_STAGE'),
                first.replace(b' next=', b'\t next=')):
            with self.subTest(bad=bad):
                self.reject(bad)

    def test_progress_is_tied_to_pass_position_and_complete_count(self):
        good = stream(tail=1)
        for bad in (b'PASS: unexpected\n' + good,
                    good.replace(b'PASS: synthetic private label\n', b'', 1),
                    good.replace(b'next=1026', b'next=1025', 1),
                    good + b'PASS: extra\n'):
            self.reject(bad)
        self.reject(stream(), complete=True)
        self.reject(stream(expected()[:2], tail=1607))

    def test_any_corrupt_marker_prevents_fallback_to_earlier_valid_one(self):
        good = stream(expected()[:2])
        for suffix in (b'I18N_STAGE private/path\n', b'I18N_STAGE stage=2 language=0 width=0 next=12',
                       b'error includes I18N_STAGE\n', b'I18N_STAGE\x00stage=2\n'):
            self.reject(good + suffix)
        for bad in (b'', b'PASS: no stage\n', 'I18N_STAGE', b'x' * (runner.ci.MAX_LOG_BYTES + 1)):
            self.reject(bad)

    def test_failure_wrapper_suppresses_missing_oversize_and_corrupt_streams(self):
        with tempfile.TemporaryDirectory() as tmp:
            logs = Path(tmp)
            self.assertIsNone(runner.failure_progress(logs))
            path = logs / 'app_i18n_native.stdout.log'
            for bad in (b'I18N_STAGE private/path\n', b'x' * (runner.ci.MAX_LOG_BYTES + 1),
                        stream(expected()[:2]) + b'I18N_STAGE invalid\n'):
                path.write_bytes(bad)
                self.assertIsNone(runner.failure_progress(logs))

    def test_workflow_exposes_only_one_optional_numeric_failure_marker(self):
        text = (Path(runner.__file__).resolve().parents[1] / '.github/workflows/windows.yml').read_text(encoding='utf-8')
        body = text.split('  focused-native-diagnostic:\n', 1)[1]
        match = re.search(r"\$Progress = @\(Select-String -LiteralPath \$Log -Pattern '([^']+)'\)", body)
        self.assertIsNotNone(match)
        pattern = match.group(1)
        self.assertRegex('FOCUSED_I18N_PROGRESS stage=5 language=4 width=0 next=1026', pattern)
        self.assertRegex('FOCUSED_I18N_PROGRESS stage=10 language=7 width=0 next=1606', pattern)
        self.assertRegex('FOCUSED_I18N_PROGRESS stage=10 language=7 width=0 next=1607', pattern)
        for invalid in ('FOCUSED_I18N_PROGRESS stage=11 language=4 width=0 next=1026',
                        'FOCUSED_I18N_PROGRESS stage=5 language=8 width=0 next=1026',
                        'FOCUSED_I18N_PROGRESS stage=5 language=4 width=0 next=1608',
                        'FOCUSED_I18N_PROGRESS stage=5 language=4 width=0 next=1026 C:\\private'):
            self.assertNotRegex(invalid, pattern)
        self.assertIn('$Progress.Count -gt 1', body)
        self.assertIn('$Result -eq 0 -or $Markers[0].Line -cnotmatch', body)
        self.assertIn('Write-Host $Progress[0].Line', body)
        self.assertIn("if ($Result -ne 0) { throw 'FOCUSED_NATIVE_EXECUTION_FAILED=1' }", body)
        self.assertNotIn('Get-Content', body)
        self.assertEqual(body.count('uses: actions/upload-artifact@'), 1)
        self.assertIn('if: success()', body)
        self.assertIn('path: build/focused-native-public/measurements.json', body)

    def test_filter_memory_adapter_is_private_posix_only_and_mandatory(self):
        text = (Path(runner.__file__).resolve().parents[1] / '.github/workflows/windows.yml').read_text(encoding='utf-8')
        helper = text.split('  helper-policy:\n', 1)[1].split('  windows-native:\n', 1)[0]
        step = helper.split('      - name: Verify localized filter bytes with private host memory controls\n', 1)[1].split('      - name:', 1)[0]
        self.assertIn("if: ${{ !(github.event_name == 'workflow_dispatch' && inputs.historical_callback) }}", step)
        self.assertIn('python -I tools/test_filter_buffers.py --ru-root .ci/ru-language --output build/filter-buffer-private', step)
        self.assertIn('> build/filter-buffer-controls-private/runner.stdout.log', step)
        self.assertIn('2> build/filter-buffer-controls-private/runner.stderr.log', step)
        self.assertIn("echo 'FILTER_BUFFER_MEMORY_CONTROLS_PASS=1'", step)
        self.assertNotIn('continue-on-error', step)
        self.assertNotIn('|| true', step)
        self.assertNotIn('cat ', step)
        self.assertNotIn('test_filter_buffers.py', text.split('  windows-native:\n', 1)[1])
        for artifact in re.findall(r'(?ms)^      - name: Upload.*?(?=^      - name:|^  [a-z]|\Z)', text):
            self.assertNotIn('filter-buffer', artifact)


if __name__ == '__main__':
    unittest.main()
