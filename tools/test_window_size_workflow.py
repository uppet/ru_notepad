#!/usr/bin/env python3
"""Portable diagnostic isolation controls; never Windows execution evidence."""
import ast
import itertools
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guard_focused_native_diagnostic import ALLOWED_REF, ONE_SHOT_TITLE, validate_trigger
from guard_window_size_diagnostic import validate_trigger as window_trigger, ONE_SHOT_TITLE as RETIRED_TITLE

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github/workflows/windows.yml'


def job(name):
    source = WORKFLOW.read_text(encoding='utf-8')
    match = re.search(r'(?ms)^  ' + re.escape(name) + r':\n(.*?)(?=^  [a-z][a-z-]+:\n|\Z)', source)
    if match is None:
        raise AssertionError('Missing workflow job')
    return match.group(1)


class CaseInsensitiveStrings(ast.NodeTransformer):
    def visit_Constant(self, node):
        if isinstance(node.value, str):
            node.value = node.value.casefold()
        return node


def evaluate(expression, *, event='push', ref=ALLOWED_REF, title='ordinary change',
             owned=False, cpp=False, historical=False, focused=False):
    values = {'github.event.head_commit.message': title, 'github.event_name': event,
              'github.ref': ref, 'inputs.i18n_window_diagnostic': owned,
              'inputs.syntax_growth_diagnostic': cpp, 'inputs.historical_callback': historical,
              'inputs.i18n_focused_diagnostic': focused}
    for key in sorted(values, key=len, reverse=True):
        expression = expression.replace(key, repr(values[key]))
    expression = re.sub(r'!(?!=)', ' not ', expression.replace('&&', ' and ').replace('||', ' or ')).strip()
    tree = CaseInsensitiveStrings().visit(ast.parse(expression, mode='eval'))
    return eval(compile(tree, '<workflow-control>', 'eval'), {'__builtins__': {}}, {})


def condition(name):
    first = job(name).splitlines()[0].strip()
    if not first.startswith('if: ${{ ') or not first.endswith(' }}'):
        raise AssertionError('Explicit selection condition required')
    return first[len('if: ${{ '):-len(' }}')]


class TriggerControls(unittest.TestCase):
    def test_exact_push_and_explicit_manual_are_allowed(self):
        validate_trigger('push', ALLOWED_REF, {'head_commit': {'message': ONE_SHOT_TITLE}})
        for value in (True, 'true'):
            validate_trigger('workflow_dispatch', ALLOWED_REF, {'inputs': {'i18n_focused_diagnostic': value}})
            window_trigger('workflow_dispatch', ALLOWED_REF, {'inputs': {'i18n_window_diagnostic': value}})

    def test_all_other_events_refs_titles_are_rejected(self):
        for event, ref, title in itertools.product(
            ('push', 'pull_request', 'pull_request_target', 'schedule', 'workflow_call', 'PUSH'),
            (ALLOWED_REF, 'refs/heads/WIP', 'refs/heads/main', 'refs/tags/wip', ALLOWED_REF + '-other'),
            (ONE_SHOT_TITLE, ONE_SHOT_TITLE + '\n', ONE_SHOT_TITLE + ' extra', RETIRED_TITLE)):
            if event == 'push' and ref == ALLOWED_REF and title == ONE_SHOT_TITLE:
                continue
            with self.subTest(event=event, ref=ref, title=title), self.assertRaises(ValueError):
                validate_trigger(event, ref, {'head_commit': {'message': title}})

    def test_window_push_is_retired(self):
        for title in (RETIRED_TITLE, ONE_SHOT_TITLE, 'ordinary change'):
            with self.assertRaises(ValueError):
                window_trigger('push', ALLOWED_REF, {'head_commit': {'message': title}})

    def test_manual_defaults_and_conflicts_fail_closed(self):
        for value in (False, 'false', '', 'TRUE', 'True', 1, 0, None, [], {}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_trigger('workflow_dispatch', ALLOWED_REF, {'inputs': {'i18n_focused_diagnostic': value}})
        for key in ('syntax_growth_diagnostic', 'historical_callback', 'i18n_window_diagnostic'):
            for value in (True, 'true', 'TRUE', 1, None):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    validate_trigger('workflow_dispatch', ALLOWED_REF, {'inputs': {
                        'i18n_focused_diagnostic': 'true', key: value}})
        for ref in ('refs/heads/WIP', 'refs/heads/main', 'refs/tags/wip'):
            with self.assertRaises(ValueError):
                validate_trigger('workflow_dispatch', ref, {'inputs': {'i18n_focused_diagnostic': 'true'}})
        with self.assertRaises(ValueError):
            window_trigger('workflow_dispatch', ALLOWED_REF, {'inputs': {
                'i18n_window_diagnostic': True, 'i18n_focused_diagnostic': True}})

    def test_malformed_payloads_deleted_push_rejected(self):
        for event in ({}, [], None, {'head_commit': None}, {'head_commit': []},
                      {'head_commit': {'message': ONE_SHOT_TITLE}, 'deleted': True}):
            with self.assertRaises(ValueError):
                validate_trigger('push', ALLOWED_REF, event)
        for inputs in (None, [], True, 'true'):
            with self.assertRaises(ValueError):
                validate_trigger('workflow_dispatch', ALLOWED_REF, {'inputs': inputs})

    def test_actual_cli_has_fixed_markers_only(self):
        with tempfile.TemporaryDirectory(prefix='private-event-path-') as directory:
            path = Path(directory) / 'event.json'
            env = dict(os.environ, GITHUB_EVENT_NAME='push', GITHUB_REF=ALLOWED_REF, GITHUB_EVENT_PATH=str(path))
            command = [sys.executable, '-I', str(ROOT / 'tools/guard_focused_native_diagnostic.py'), '--guard-only']
            for payload, accepted in ((json.dumps({'head_commit': {'message': ONE_SHOT_TITLE}}), True),
                                      ('{"private-path":"C:\\\\private\\\\document.md"}', False), ('invalid json', False)):
                path.write_text(payload, encoding='utf-8')
                result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0 if accepted else 1)
                self.assertEqual(result.stdout, 'FOCUSED_NATIVE_TRIGGER_ACCEPTED=1\n' if accepted else '')
                self.assertEqual(result.stderr, '' if accepted else 'FOCUSED_NATIVE_TRIGGER_REJECTED=1\n')


class WorkflowControls(unittest.TestCase):
    def test_defaults_off_and_one_shot_replaced(self):
        source = WORKFLOW.read_text(encoding='utf-8')
        for name in ('i18n_focused_diagnostic', 'i18n_window_diagnostic', 'syntax_growth_diagnostic'):
            entry = source.split('      ' + name + ':\n', 1)[1].split('      historical_callback:\n', 1)[0]
            self.assertIn('type: boolean', entry)
            self.assertIn('default: false', entry)
        self.assertEqual(source.count(ONE_SHOT_TITLE), 4)
        self.assertNotIn(RETIRED_TITLE, source)
        self.assertIn(ALLOWED_REF, condition('focused-native-diagnostic'))

    def test_complete_selection_matrix_keeps_product_separate(self):
        expressions = {name: condition(name) for name in (
            'helper-policy', 'windows-native', 'window-size-diagnostic', 'cpp-growth-diagnostic', 'focused-native-diagnostic')}
        for event, ref, title, owned, cpp, historical, focused in itertools.product(
            ('push', 'pull_request', 'workflow_dispatch'), (ALLOWED_REF, 'refs/heads/main', 'refs/heads/WIP'),
            (ONE_SHOT_TITLE, ONE_SHOT_TITLE + '\n', RETIRED_TITLE, 'ordinary change'),
            (False, True), (False, True), (False, True), (False, True)):
            case = dict(event=event, ref=ref, title=title, owned=owned, cpp=cpp, historical=historical, focused=focused)
            selected = {name: bool(evaluate(expression, **case)) for name, expression in expressions.items()}
            window = event == 'workflow_dispatch' and owned
            growth = event == 'workflow_dispatch' and cpp
            focus = (event == 'workflow_dispatch' and focused) or (event == 'push' and ref.casefold() == ALLOWED_REF and title == ONE_SHOT_TITLE)
            self.assertEqual(selected['window-size-diagnostic'], window, case)
            self.assertEqual(selected['cpp-growth-diagnostic'], growth, case)
            self.assertEqual(selected['focused-native-diagnostic'], focus, case)
            self.assertEqual(selected['helper-policy'], not (window or growth or focus), case)
            self.assertEqual(selected['windows-native'], not (window or growth or focus), case)

    def test_case_insensitive_workflow_has_strict_guard_before_compiler(self):
        self.assertTrue(evaluate(condition('focused-native-diagnostic'), ref='refs/heads/WIP', title=ONE_SHOT_TITLE))
        with self.assertRaises(ValueError):
            validate_trigger('push', 'refs/heads/WIP', {'head_commit': {'message': ONE_SHOT_TITLE}})
        body = job('focused-native-diagnostic')
        guard = body.index('python -I tools/guard_focused_native_diagnostic.py --guard-only')
        self.assertLess(guard, body.index('repository: uppet/ru-language'))
        self.assertLess(guard, body.index('uses: msys2/setup-msys2'))
        self.assertLess(guard, body.index('tools/run_focused_native_diagnostic.py'))

    def test_workflow_concurrency_independent(self):
        source = WORKFLOW.read_text(encoding='utf-8')
        line = next(line for line in source.splitlines() if line.startswith('  group: '))
        expression = line.split('${{ ', 2)[2].removesuffix(' }}')
        values = [evaluate(expression), evaluate(expression, event='workflow_dispatch', owned=True),
                  evaluate(expression, event='workflow_dispatch', cpp=True), evaluate(expression, title=ONE_SHOT_TITLE)]
        self.assertEqual(values, ['', '-window-size-diagnostic', '-cpp-growth-diagnostic', '-focused-native-diagnostic'])
        self.assertEqual(evaluate(expression, event='workflow_dispatch', focused=True), values[-1])
        self.assertEqual(evaluate(expression, title=RETIRED_TITLE), '')
        self.assertNotIn('needs:', job('focused-native-diagnostic'))
        self.assertNotIn('needs: focused-native-diagnostic', source)

    def test_only_successful_literal_measurements_upload(self):
        for name, prefix in (('window-size-diagnostic', 'window-size-diagnostic'),
                             ('focused-native-diagnostic', 'focused-native')):
            body = job(name)
            paths = re.findall(r'(?m)^          path: (.*)$', body)
            self.assertEqual(paths, (['.ci/ru-language'] if name.startswith('focused') else []) +
                             ['build/' + prefix + '-public/measurements.json'])
            self.assertEqual(body.count('uses: actions/upload-artifact@'), 1)
            for forbidden in ('*.log', '*.zip', '.build.json', 'source-map.json', 'runner-receipt.json',
                              'package.py', 'package_manual_preview.py', 'windows_ci.ps1', '--source'):
                self.assertNotIn(forbidden, body)
            self.assertIn('if: success()', body)
            self.assertNotIn('if: always()', body)
        self.assertNotIn('run_focused_native_diagnostic.py', job('windows-native'))

    def test_conflicting_modes_refused(self):
        for name, keys in (
            ('window-size-diagnostic', ('historical_callback', 'syntax_growth_diagnostic', 'i18n_focused_diagnostic')),
            ('cpp-growth-diagnostic', ('historical_callback', 'i18n_window_diagnostic', 'i18n_focused_diagnostic')),
            ('focused-native-diagnostic', ('historical_callback', 'syntax_growth_diagnostic', 'i18n_window_diagnostic'))):
            body = job(name)
            for key in keys:
                self.assertIn('inputs.' + key, body)
            self.assertIn('run: throw ', body)

    def test_source_and_action_pins_exact(self):
        body = job('focused-native-diagnostic')
        self.assertIn('ref: ${{ github.sha }}', body)
        self.assertIn('ref: 85c7821fda35aa79deeaf67b4d430f24ddd7f07f', body)
        self.assertEqual(body.count('persist-credentials: false'), 2)
        for action in re.findall(r'uses: ([^\s]+)', body):
            self.assertRegex(action, r'^[\w/-]+@[0-9a-f]{40}$')

    def test_controls_and_execution_keep_raw_streams_private(self):
        body = job('focused-native-diagnostic')
        self.assertIn('tools/test_focused_native_diagnostic.py -v *> ', body)
        self.assertIn('tools/test_window_size_workflow.py -v *> ', body)
        self.assertIn('--msys-root "$env:MSYS2_ROOT" *> $Log', body)
        self.assertIn("'^FOCUSED_NATIVE_DIAGNOSTIC code=(?:[0-9]|1[0-2]) markdown=[0-9]{1,16} i18n=[0-9]{1,16}$'", body)
        self.assertIn('if ($Markers.Count -ne 1)', body)
        self.assertNotIn('Get-Content', body)
        self.assertNotIn('$_', body)

    def test_existing_native_contract_unchanged(self):
        text = (ROOT / 'tools/windows_ci.py').read_text(encoding='utf-8')
        assignments = {n.targets[0].id: n.value for n in ast.parse(text).body if isinstance(n, ast.Assign)
                       and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)}
        contracts = dict(ast.literal_eval(assignments['NATIVE_CONSOLE_TESTS']))
        self.assertEqual(contracts['app_i18n_native'], r'^TOTAL PASS: 1417\s*$')
        self.assertEqual(contracts['markdown_direct_native'], r'^TOTAL PASS: 114\s*$')
        self.assertEqual(contracts['i18n_policy'], r'^TOTAL PASS: 289\s*$')


if __name__ == '__main__':
    unittest.main()
