#!/usr/bin/env python3
"""Portable fail-closed workflow controls; never Windows execution evidence."""
from __future__ import annotations

import ast
import itertools
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guard_window_size_diagnostic import ALLOWED_REF, ONE_SHOT_TITLE, validate_trigger

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/windows.yml"


def job(name):
    source = WORKFLOW.read_text(encoding="utf-8")
    match = re.search(r"(?ms)^  " + re.escape(name) + r":\n(.*?)(?=^  [a-z][a-z-]+:\n|\Z)", source)
    if match is None:
        raise AssertionError("Missing workflow job: " + name)
    return match.group(1)


class CaseInsensitiveStrings(ast.NodeTransformer):
    """Match GitHub's case-insensitive equality, then test the strict guard."""

    def visit_Constant(self, node):
        if isinstance(node.value, str):
            node.value = node.value.casefold()
        return node


def evaluate(expression, *, event="push", ref=ALLOWED_REF, title="ordinary change",
             owned=False, cpp=False, historical=False):
    values = {
        "github.event.head_commit.message": title,
        "github.event_name": event,
        "github.ref": ref,
        "inputs.i18n_window_diagnostic": owned,
        "inputs.syntax_growth_diagnostic": cpp,
        "inputs.historical_callback": historical,
    }
    for key in sorted(values, key=len, reverse=True):
        expression = expression.replace(key, repr(values[key]))
    expression = expression.replace("&&", " and ").replace("||", " or ")
    expression = re.sub(r"!(?!=)", " not ", expression).strip()
    tree = CaseInsensitiveStrings().visit(ast.parse(expression, mode="eval"))
    return eval(compile(tree, "<workflow-control>", "eval"), {"__builtins__": {}}, {})


def condition(name):
    first = job(name).splitlines()[0].strip()
    if not first.startswith("if: ${{ ") or not first.endswith(" }}"):
        raise AssertionError("Job must start with an explicit selection condition")
    return first[len("if: ${{ "):-len(" }}")]


class TriggerControls(unittest.TestCase):
    def test_exact_push_and_explicit_manual_are_allowed(self):
        validate_trigger("push", ALLOWED_REF, {"head_commit": {"message": ONE_SHOT_TITLE}})
        for value in (True, "true"):
            validate_trigger("workflow_dispatch", ALLOWED_REF, {"inputs": {
                "i18n_window_diagnostic": value,
                "syntax_growth_diagnostic": "false",
                "historical_callback": False,
            }})

    def test_all_other_events_refs_and_titles_are_rejected(self):
        for event, ref, title in itertools.product(
            ("push", "pull_request", "pull_request_target", "schedule", "workflow_call", "PUSH"),
            (ALLOWED_REF, "refs/heads/WIP", "refs/heads/main", "refs/tags/wip", ALLOWED_REF + "-other"),
            (ONE_SHOT_TITLE, ONE_SHOT_TITLE + "\n", ONE_SHOT_TITLE + " extra", ONE_SHOT_TITLE.lower()),
        ):
            if event == "push" and ref == ALLOWED_REF and title == ONE_SHOT_TITLE:
                continue
            with self.subTest(event=event, ref=ref, title=title):
                with self.assertRaises(ValueError):
                    validate_trigger(event, ref, {"head_commit": {"message": title}})

    def test_manual_defaults_and_conflicts_fail_closed(self):
        for value in (False, "false", "", "TRUE", "True", 1, 0, None, [], {}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_trigger("workflow_dispatch", ALLOWED_REF, {"inputs": {"i18n_window_diagnostic": value}})
        for key in ("syntax_growth_diagnostic", "historical_callback"):
            for value in (True, "true", "TRUE", 1, None):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    validate_trigger("workflow_dispatch", ALLOWED_REF, {"inputs": {
                        "i18n_window_diagnostic": "true", key: value,
                    }})
        for ref in ("refs/heads/WIP", "refs/heads/main", "refs/tags/wip"):
            with self.assertRaises(ValueError):
                validate_trigger("workflow_dispatch", ref, {"inputs": {"i18n_window_diagnostic": "true"}})

    def test_malformed_payloads_and_deleted_push_are_rejected(self):
        for event in ({}, [], None, {"head_commit": None}, {"head_commit": []},
                      {"head_commit": {"message": ONE_SHOT_TITLE}, "deleted": True}):
            with self.assertRaises(ValueError):
                validate_trigger("push", ALLOWED_REF, event)
        for inputs in (None, [], True, "true"):
            with self.assertRaises(ValueError):
                validate_trigger("workflow_dispatch", ALLOWED_REF, {"inputs": inputs})

    def test_actual_cli_has_only_fixed_markers(self):
        with tempfile.TemporaryDirectory(prefix="private-event-path-") as directory:
            path = Path(directory) / "event.json"
            env = dict(os.environ, GITHUB_EVENT_NAME="push", GITHUB_REF=ALLOWED_REF,
                       GITHUB_EVENT_PATH=str(path))
            command = [sys.executable, "-I", str(ROOT / "tools/guard_window_size_diagnostic.py"), "--guard-only"]
            for payload, accepted in (
                (json.dumps({"head_commit": {"message": ONE_SHOT_TITLE}}), True),
                ('{"private-path":"C:\\\\private\\\\document.md"}', False),
                ("invalid json", False),
            ):
                path.write_text(payload, encoding="utf-8")
                result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0 if accepted else 1)
                self.assertEqual(result.stdout, "WINDOW_SIZE_TRIGGER_ACCEPTED=1\n" if accepted else "")
                self.assertEqual(result.stderr, "" if accepted else "WINDOW_SIZE_TRIGGER_REJECTED=1\n")


class WorkflowControls(unittest.TestCase):
    def test_default_off_and_exact_one_shot_entry(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        entry = source.split("      i18n_window_diagnostic:\n", 1)[1].split("      syntax_growth_diagnostic:\n", 1)[0]
        self.assertIn("type: boolean", entry)
        self.assertIn("default: false", entry)
        self.assertIn(ONE_SHOT_TITLE, condition("window-size-diagnostic"))
        self.assertIn(ALLOWED_REF, condition("window-size-diagnostic"))
        self.assertEqual(source.count(ONE_SHOT_TITLE), 4)

    def test_complete_selection_matrix_keeps_product_separate(self):
        expressions = {name: condition(name) for name in (
            "helper-policy", "windows-native", "window-size-diagnostic", "cpp-growth-diagnostic")}
        for event, ref, title, owned, cpp, historical in itertools.product(
            ("push", "pull_request", "workflow_dispatch"),
            (ALLOWED_REF, "refs/heads/main", "refs/heads/WIP"),
            (ONE_SHOT_TITLE, ONE_SHOT_TITLE + "\n", "ordinary change"),
            (False, True), (False, True), (False, True),
        ):
            case = dict(event=event, ref=ref, title=title, owned=owned, cpp=cpp, historical=historical)
            selected = {name: bool(evaluate(expression, **case)) for name, expression in expressions.items()}
            markdown = (event == "workflow_dispatch" and owned) or (
                event == "push" and ref.casefold() == ALLOWED_REF and title == ONE_SHOT_TITLE)
            growth = event == "workflow_dispatch" and cpp
            self.assertEqual(selected["window-size-diagnostic"], markdown, case)
            self.assertEqual(selected["cpp-growth-diagnostic"], growth, case)
            self.assertEqual(selected["helper-policy"], not (markdown or growth), case)
            self.assertEqual(selected["windows-native"], not (markdown or growth), case)

    def test_case_insensitive_workflow_is_followed_by_strict_guard(self):
        expression = condition("window-size-diagnostic")
        self.assertTrue(evaluate(expression, ref="refs/heads/WIP", title=ONE_SHOT_TITLE))
        with self.assertRaises(ValueError):
            validate_trigger("push", "refs/heads/WIP", {"head_commit": {"message": ONE_SHOT_TITLE}})
        body = job("window-size-diagnostic")
        guard = body.index("python -I tools/guard_window_size_diagnostic.py --guard-only")
        self.assertNotIn("repository: uppet/ru-language", body)
        self.assertLess(guard, body.index("uses: msys2/setup-msys2"))
        self.assertLess(guard, body.index("tools/run_window_size_diagnostic.py"))

    def test_workflow_concurrency_is_independent(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        line = next(line for line in source.splitlines() if line.startswith("  group: "))
        expression = line.split("${{ ", 2)[2].removesuffix(" }}")
        product = evaluate(expression, title="ordinary change")
        markdown_push = evaluate(expression, title=ONE_SHOT_TITLE)
        markdown_manual = evaluate(expression, event="workflow_dispatch", owned=True)
        cpp_manual = evaluate(expression, event="workflow_dispatch", cpp=True)
        self.assertEqual(product, "")
        self.assertEqual(markdown_push, "-window-size-diagnostic")
        self.assertEqual(markdown_manual, markdown_push)
        self.assertEqual(cpp_manual, "-cpp-growth-diagnostic")
        self.assertEqual(len({product, markdown_push, cpp_manual}), 3)
        self.assertNotIn("needs:", job("window-size-diagnostic"))
        self.assertNotIn("needs: window-size-diagnostic", source)

    def test_diagnostic_upload_is_one_sanitized_file_only(self):
        body = job("window-size-diagnostic")
        paths = re.findall(r"(?m)^          path: (.*)$", body)
        self.assertEqual(paths, ["build/window-size-diagnostic-public/measurements.json"])
        self.assertEqual(body.count("uses: actions/upload-artifact@"), 1)
        for forbidden in ("*.log", "*.zip", ".build.json", "source-map.json",
                          "runner-receipt.json", "package.py", "package_manual_preview.py",
                          "windows_ci.ps1", "--source", "--ru-root"):
            self.assertNotIn(forbidden, body)
        self.assertIn("if: success()", body)
        self.assertNotIn("if: always()", body)
        self.assertIn("tools/run_window_size_diagnostic.py", body)
        self.assertNotIn("run_window_size_diagnostic.py", job("windows-native"))

    def test_each_diagnostic_refuses_conflicting_inputs(self):
        window = job("window-size-diagnostic")
        cpp = job("cpp-growth-diagnostic")
        self.assertIn("inputs.historical_callback || inputs.syntax_growth_diagnostic", window)
        self.assertIn("if: ${{ inputs.i18n_window_diagnostic }}", cpp)
        self.assertIn("throw 'Select only one diagnostic mode.'", window)
        self.assertIn("throw 'Select only one diagnostic mode.'", cpp)

    def test_source_and_action_pins_are_exact(self):
        body = job("window-size-diagnostic")
        self.assertIn("ref: ${{ github.sha }}", body)
        self.assertEqual(body.count("persist-credentials: false"), 1)
        for action in re.findall(r"uses: ([^\s]+)", body):
            self.assertRegex(action, r"^[\w/-]+@[0-9a-f]{40}$")

    def test_controls_keep_raw_streams_private(self):
        body = job("window-size-diagnostic")
        self.assertIn("tools/test_window_size_diagnostic.py -v *> (Join-Path $LogRoot 'parser.log')", body)
        self.assertIn("tools/test_window_size_workflow.py -v *> (Join-Path $LogRoot 'workflow.log')", body)
        self.assertIn("if ($LASTEXITCODE -ne 0)", body)
        self.assertIn("if (Test-Path -LiteralPath $LogRoot)", body)
        self.assertNotIn("$_.", body)
        self.assertNotIn("Get-Content", body)

    def test_existing_native_contract_is_unchanged(self):
        text = (ROOT / "tools/windows_ci.py").read_text(encoding="utf-8")
        assignments = {node.targets[0].id: node.value for node in ast.parse(text).body
                       if isinstance(node, ast.Assign) and len(node.targets) == 1
                       and isinstance(node.targets[0], ast.Name)}
        contracts = dict(ast.literal_eval(assignments['NATIVE_CONSOLE_TESTS']))
        self.assertEqual(contracts['app_i18n_native'], r'^TOTAL PASS: 1417\s*$')
        self.assertEqual(contracts['markdown_direct_native'], r'^TOTAL PASS: 114\s*$')
        self.assertEqual(contracts['i18n_policy'], r'^TOTAL PASS: 289\s*$')


if __name__ == "__main__":
    unittest.main()
