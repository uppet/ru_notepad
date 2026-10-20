#!/usr/bin/env python3
"""Run a fixed control inventory; raw unittest details stay in the private sink."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Stable IDs. Never derive public names, paths, or exception text from a test.
CASES = (
    'PublicationControls.test_actual_cli_failure_is_numeric_and_private',
    'PublicationControls.test_actual_product_build_entry_accepts_current_parameters',
    'PublicationControls.test_arbitrary_fields_paths_wrong_counts_gc_and_types_rejected',
    'PublicationControls.test_literal_numeric_hash_only_tree',
    'PublicationControls.test_public_path_directory_links_and_race_rejected',
    'PublicationControls.test_source_build_and_gc_contracts_are_reused',
    'PublicationControls.test_validated_atomic_noreplace_publication',
    'PublicationControls.test_write_fsync_and_link_failures_do_not_publish',
    'ReceiptControls.test_changed_source_generated_c_pe_compiler_and_helper_rejected',
    'ReceiptControls.test_complete_source_bound_two_fixture_inventory',
    'ReceiptControls.test_helper_actual_command_and_compiler_binding',
    'ReceiptControls.test_missing_receipt_and_added_exe_rejected',
    'ReceiptControls.test_receipt_fields_cannot_be_changed_or_omitted',
    'RuntimeControls.test_actual_console_child_gc_environment_exit_and_timeout',
    'RuntimeControls.test_complete_original_counts_and_parsers',
    'RuntimeControls.test_gc_and_routes_must_be_current_real_logs',
    'RuntimeControls.test_missing_oversize_and_invalid_utf8_logs',
    'RuntimeControls.test_timeout_exit_cleanup_unexecuted_and_receipt_counts',
    'RuntimeControls.test_wrong_counts_totals_fail_skip_and_stderr',
)


def identity(test):
    # _SubTest delegates its owning case. Its parameter repr is never inspected.
    parent = getattr(test, 'test_case', test)
    return type(parent).__name__ + '.' + getattr(parent, '_testMethodName', '')


def category(error):
    kind = error[0]
    for code, base in ((1, AssertionError), (5, UnicodeError),
                       (6, subprocess.TimeoutExpired), (2, ValueError),
                       (3, RuntimeError), (4, OSError)):
        if issubclass(kind, base):
            return code
    return 7


class NumericResult(unittest.TextTestResult):
    """Retain ordinary private tracebacks; record only bounded public integers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = {name: {'starts': 0, 'stops': 0, 'status': 4, 'category': 0, 'events': 0}
                        for name in CASES}
        self.protocol_error = False

    def record(self, test):
        record = self.records.get(identity(test))
        if record is None:
            self.protocol_error = True
        return record

    def startTest(self, test):
        super().startTest(test)
        record = self.record(test)
        if record is not None:
            record['starts'] += 1

    def stopTest(self, test):
        record = self.record(test)
        if record is not None:
            record['stops'] += 1
        super().stopTest(test)

    def mark(self, test, status, error=None):
        record = self.record(test)
        if record is None:
            return
        code = category(error) if error else 0
        if record['events'] and record['category'] != code:
            code = 8  # Multiple fixed exception categories in one case.
        record['category'] = code
        record['events'] += int(status != 0)
        if record['status'] == 4 or status > record['status']:
            record['status'] = status

    def addSuccess(self, test):
        self.mark(test, 0)
        super().addSuccess(test)

    def addFailure(self, test, err):
        self.mark(test, 1, err)
        super().addFailure(test, err)

    def addError(self, test, err):
        self.mark(test, 2, err)
        super().addError(test, err)

    def addSkip(self, test, reason):
        self.mark(test, 3)
        super().addSkip(test, reason)

    def addSubTest(self, test, subtest, err):
        if err is not None:
            self.mark(test, 1 if issubclass(err[0], test.failureException) else 2, err)
        super().addSubTest(test, subtest, err)


def numeric_lines(result):
    if (not isinstance(result, NumericResult) or result.protocol_error or
            set(result.records) != set(CASES) or type(result.testsRun) is not int or
            not 0 <= result.testsRun <= len(CASES)):
        raise ValueError('Invalid fixed control inventory')
    counts = [0] * 5
    lines = []
    for index, name in enumerate(CASES, 1):
        row = result.records[name]
        if (set(row) != {'starts', 'stops', 'status', 'category', 'events'} or
                any(type(value) is not int for value in row.values()) or
                row['starts'] != 1 or row['stops'] != 1 or
                not 0 <= row['status'] <= 3 or not 0 <= row['category'] <= 8 or
                not 0 <= row['events'] <= 65535 or
                (row['status'] == 0 and (row['category'] != 0 or row['events'] != 0))):
            raise ValueError('Incomplete fixed control inventory')
        counts[row['status']] += 1
        lines.append(f"FOCUSED_CONTROL id={index} status={row['status']} category={row['category']} events={row['events']}")
    if result.testsRun != len(CASES):
        raise ValueError('Incomplete fixed control inventory')
    passed, failed, errors, skipped, _ = counts
    code = int(passed != len(CASES) or not result.wasSuccessful())
    lines.append(f'FOCUSED_CONTROLS_RESULT code={code} cases={len(CASES)} passed={passed} failed={failed} errors={errors} skipped={skipped}')
    return lines, code


def main():
    try:
        if sys.argv[1:]:
            raise ValueError('No arguments accepted')
        import test_focused_native_diagnostic as controls
        suite = unittest.defaultTestLoader.loadTestsFromModule(controls)
        result = unittest.TextTestRunner(stream=sys.stderr, verbosity=2, resultclass=NumericResult).run(suite)
        lines, code = numeric_lines(result)
    except Exception:
        # No repr/traceback can cross the private log boundary through this marker.
        print('FOCUSED_CONTROLS_RESULT code=2 cases=0 passed=0 failed=0 errors=0 skipped=0')
        return 2
    print('\n'.join(lines))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
