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
from guard_markdown_owned_profile import ALLOWED_REF, ONE_SHOT_TITLE, validate_trigger

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
             owned=False, cpp=False, historical=False, window=False, focused=False):
    values = {
        "github.event.head_commit.message": title,
        "github.event_name": event,
        "github.ref": ref,
        "inputs.markdown_owned_profile": owned,
        "inputs.syntax_growth_diagnostic": cpp,
        "inputs.historical_callback": historical,
        "inputs.i18n_window_diagnostic": window,
        "inputs.i18n_focused_diagnostic": focused,
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
    def test_every_manual_mode_rejects_all_other_selected_modes(self):
        from guard_focused_native_diagnostic import validate_trigger as focused_trigger
        from guard_window_size_diagnostic import validate_trigger as window_trigger
        from run_cpp_growth_diagnostic import validate_trigger as cpp_trigger
        triggers = {
            "markdown_owned_profile": validate_trigger,
            "i18n_focused_diagnostic": focused_trigger,
            "i18n_window_diagnostic": window_trigger,
            "syntax_growth_diagnostic": cpp_trigger,
        }
        for selected, trigger in triggers.items():
            trigger("workflow_dispatch", ALLOWED_REF, {"inputs": {selected: "true"}})
            for conflict in (*triggers, "historical_callback"):
                if selected == conflict:
                    continue
                for value in (True, "true"):
                    with self.subTest(selected=selected, conflict=conflict, value=value):
                        with self.assertRaises((ValueError, RuntimeError)):
                            trigger("workflow_dispatch", ALLOWED_REF, {
                                "inputs": {selected: "true", conflict: value}})

    def test_only_explicit_manual_is_allowed(self):
        with self.assertRaises(ValueError):
            validate_trigger("push", ALLOWED_REF, {"head_commit": {"message": ONE_SHOT_TITLE}})
        for value in (True, "true"):
            validate_trigger("workflow_dispatch", ALLOWED_REF, {"inputs": {
                "markdown_owned_profile": value,
                "syntax_growth_diagnostic": "false",
                "historical_callback": False,
            }})

    def test_all_other_events_refs_and_titles_are_rejected(self):
        for event, ref, title in itertools.product(
            ("push", "pull_request", "pull_request_target", "schedule", "workflow_call", "PUSH"),
            (ALLOWED_REF, "refs/heads/WIP", "refs/heads/main", "refs/tags/wip", ALLOWED_REF + "-other"),
            (ONE_SHOT_TITLE, ONE_SHOT_TITLE + "\n", ONE_SHOT_TITLE + " extra", ONE_SHOT_TITLE.lower()),
        ):
            with self.subTest(event=event, ref=ref, title=title):
                with self.assertRaises(ValueError):
                    validate_trigger(event, ref, {"head_commit": {"message": title}})

    def test_manual_defaults_and_conflicts_fail_closed(self):
        for value in (False, "false", "", "TRUE", "True", 1, 0, None, [], {}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_trigger("workflow_dispatch", ALLOWED_REF, {"inputs": {"markdown_owned_profile": value}})
        for key in ("syntax_growth_diagnostic", "historical_callback",
                    "i18n_window_diagnostic", "i18n_focused_diagnostic"):
            for value in (True, "true", "TRUE", 1, None):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    validate_trigger("workflow_dispatch", ALLOWED_REF, {"inputs": {
                        "markdown_owned_profile": "true", key: value,
                    }})
        for ref in ("refs/heads/WIP", "refs/heads/main", "refs/tags/wip"):
            with self.assertRaises(ValueError):
                validate_trigger("workflow_dispatch", ref, {"inputs": {"markdown_owned_profile": "true"}})

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
            env = dict(os.environ, GITHUB_EVENT_NAME="workflow_dispatch", GITHUB_REF=ALLOWED_REF,
                       GITHUB_EVENT_PATH=str(path))
            command = [sys.executable, "-I", str(ROOT / "tools/guard_markdown_owned_profile.py"), "--guard-only"]
            for payload, accepted in (
                (json.dumps({"inputs": {"markdown_owned_profile": "true"}}), True),
                (json.dumps({"head_commit": {"message": ONE_SHOT_TITLE}}), False),
                ('{"private-path":"C:\\\\private\\\\document.md"}', False),
                ("invalid json", False),
            ):
                path.write_text(payload, encoding="utf-8")
                result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0 if accepted else 1)
                self.assertEqual(result.stdout, "MARKDOWN_OWNED_PROFILE_TRIGGER_ACCEPTED=1\n" if accepted else "")
                self.assertEqual(result.stderr, "" if accepted else "MARKDOWN_OWNED_PROFILE_TRIGGER_REJECTED=1\n")


class WorkflowControls(unittest.TestCase):
    def test_previous_owned_title_is_retired(self):
        previous = "诊断：测量七语基线 Markdown 分阶段耗时"
        self.assertNotIn(previous, WORKFLOW.read_text(encoding="utf-8"))
        for ref, title in itertools.product(
                (ALLOWED_REF, "refs/heads/WIP", "refs/heads/main"),
                (previous, previous + "\n", previous + " extra")):
            case = dict(event="push", ref=ref, title=title)
            self.assertFalse(evaluate(condition("markdown-owned-profile"), **case))
            for name in ("helper-policy", "windows-native"):
                self.assertTrue(evaluate(condition(name), **case))
            with self.assertRaises(ValueError):
                validate_trigger("push", ref, {"head_commit": {"message": title}})

    def test_all_mixed_options_are_rejected_by_workflow_before_checkout(self):
        modes = {
            "markdown-owned-profile": "owned",
            "focused-native-diagnostic": "focused",
            "window-size-diagnostic": "window",
            "cpp-growth-diagnostic": "cpp",
        }
        for name, selected in modes.items():
            early = job(name).split("    steps:\n", 1)[1].split("      - name: Preserve source bytes", 1)[0]
            conditions = re.findall(r"if: \$\{\{ (.*?) \}\}", early)
            self.assertTrue(conditions)
            self.assertIn("run: throw ", early)
            self.assertFalse(any(evaluate(expression, event="workflow_dispatch", **{selected: True})
                                 for expression in conditions))
            for conflict in (*modes.values(), "historical"):
                if conflict == selected:
                    continue
                case = dict(event="workflow_dispatch", **{selected: True, conflict: True})
                with self.subTest(mode=name, conflict=conflict):
                    self.assertTrue(any(evaluate(expression, **case) for expression in conditions))

    def test_default_off_and_one_shot_entry_retired(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        entry = source.split("      markdown_owned_profile:\n", 1)[1].split("      syntax_growth_diagnostic:\n", 1)[0]
        self.assertIn("type: boolean", entry)
        self.assertIn("default: false", entry)
        self.assertNotIn(ONE_SHOT_TITLE, source)
        self.assertNotIn("github.event.head_commit.message", condition("markdown-owned-profile"))
        self.assertEqual(condition("markdown-owned-profile"), "(github.event_name == 'workflow_dispatch' && inputs.markdown_owned_profile)")

    def test_complete_selection_matrix_keeps_product_separate(self):
        expressions = {name: condition(name) for name in (
            "helper-policy", "windows-native", "markdown-owned-profile", "cpp-growth-diagnostic",
            "window-size-diagnostic", "focused-native-diagnostic")}
        for event, ref, title, owned, cpp, historical, window, focused in itertools.product(
            ("push", "pull_request", "workflow_dispatch"),
            (ALLOWED_REF, "refs/heads/main", "refs/heads/WIP"),
            (ONE_SHOT_TITLE, ONE_SHOT_TITLE + "\n", "ordinary change"),
            (False, True), (False, True), (False, True), (False, True), (False, True),
        ):
            case = dict(event=event, ref=ref, title=title, owned=owned, cpp=cpp, historical=historical,
                        window=window, focused=focused)
            selected = {name: bool(evaluate(expression, **case)) for name, expression in expressions.items()}
            markdown = event == "workflow_dispatch" and owned
            growth = event == "workflow_dispatch" and cpp
            geometry = event == "workflow_dispatch" and window
            native = event == "workflow_dispatch" and focused
            self.assertEqual(selected["markdown-owned-profile"], markdown, case)
            self.assertEqual(selected["cpp-growth-diagnostic"], growth, case)
            self.assertEqual(selected["window-size-diagnostic"], geometry, case)
            self.assertEqual(selected["focused-native-diagnostic"], native, case)
            self.assertEqual(selected["helper-policy"], not (markdown or growth or geometry or native), case)
            self.assertEqual(selected["windows-native"], not (markdown or growth or geometry or native), case)

    def test_case_insensitive_workflow_is_followed_by_strict_guard(self):
        expression = condition("markdown-owned-profile")
        self.assertTrue(evaluate(expression, event="workflow_dispatch", ref="refs/heads/WIP", owned=True))
        with self.assertRaises(ValueError):
            validate_trigger("workflow_dispatch", "refs/heads/WIP", {"inputs": {"markdown_owned_profile": True}})
        body = job("markdown-owned-profile")
        guard = body.index("python -I tools/guard_markdown_owned_profile.py --guard-only")
        self.assertLess(guard, body.index("repository: uppet/ru-language"))
        self.assertLess(guard, body.index("uses: msys2/setup-msys2"))
        self.assertLess(guard, body.index("./tools/windows_ci.ps1"))

    def test_workflow_concurrency_is_independent(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        line = next(line for line in source.splitlines() if line.startswith("  group: "))
        expression = line.split("${{ ", 2)[2].removesuffix(" }}")
        product = evaluate(expression, title="ordinary change")
        markdown_push = evaluate(expression, title=ONE_SHOT_TITLE)
        markdown_manual = evaluate(expression, event="workflow_dispatch", owned=True)
        cpp_manual = evaluate(expression, event="workflow_dispatch", cpp=True)
        self.assertEqual(product, "")
        self.assertEqual(markdown_push, product)
        self.assertEqual(markdown_manual, "-markdown-owned-profile")
        self.assertEqual(cpp_manual, "-cpp-growth-diagnostic")
        window_manual = evaluate(expression, event="workflow_dispatch", window=True)
        focused_manual = evaluate(expression, event="workflow_dispatch", focused=True)
        self.assertEqual(window_manual, "-window-size-diagnostic")
        self.assertEqual(focused_manual, "-focused-native-diagnostic")
        self.assertEqual(len({product, markdown_manual, cpp_manual, window_manual, focused_manual}), 5)
        self.assertNotIn("needs:", job("markdown-owned-profile"))
        self.assertNotIn("needs: markdown-owned-profile", source)

    def test_diagnostic_upload_is_one_sanitized_file_only(self):
        body = job("markdown-owned-profile")
        paths = re.findall(r"(?m)^          path: (.*)$", body)
        self.assertEqual(paths, [".ci/ru-language",
                                "build/markdown-owned-profile/measurements/markdown-owned-profile.json"])
        self.assertEqual(body.count("uses: actions/upload-artifact@"), 1)
        for forbidden in ("*.log", "*.zip", ".build.json", "source-map.json",
                          "runner-receipt.json", "package.py", "package_manual_preview.py",
                          "build/windows-ci/", "-RunAclTests", "-RunCallbackResearch"):
            self.assertNotIn(forbidden, body)
        self.assertIn("if: always()", body)
        self.assertIn("-RunMarkdownOwnedProfile", body)
        self.assertNotIn("-RunMarkdownOwnedProfile", job("windows-native"))

    def test_each_diagnostic_refuses_conflicting_inputs(self):
        markdown = job("markdown-owned-profile")
        cpp = job("cpp-growth-diagnostic")
        self.assertIn("inputs.historical_callback || inputs.syntax_growth_diagnostic", markdown)
        self.assertIn("inputs.markdown_owned_profile", cpp)
        for name in ("window-size-diagnostic", "focused-native-diagnostic"):
            self.assertIn("inputs.markdown_owned_profile", job(name))
        self.assertIn("inputs.i18n_window_diagnostic", markdown)
        self.assertIn("inputs.i18n_focused_diagnostic", markdown)
        self.assertIn("throw 'Select only one diagnostic mode.'", markdown)
        self.assertIn("throw 'Select only one diagnostic mode.'", cpp)

    def test_reviewed_compiler_and_action_pins_remain_exact(self):
        body = job("markdown-owned-profile")
        self.assertIn("ref: 85c7821fda35aa79deeaf67b4d430f24ddd7f07f", body)
        self.assertIn("ref: ${{ github.sha }}", body)
        self.assertEqual(body.count("persist-credentials: false"), 2)
        for action in re.findall(r"uses: ([^\s]+)", body):
            self.assertRegex(action, r"^[\w/-]+@[0-9a-f]{40}$")


class PowershellControls(unittest.TestCase):
    def test_actual_private_command_sink_captures_both_streams(self):
        powershell = shutil.which("pwsh")
        if powershell is None:
            if sys.platform == "win32":
                self.fail("Windows CI must execute the real PowerShell diagnostic sink controls")
            self.skipTest("pwsh is absent on this non-Windows host")
        source = (ROOT / "tools/windows_ci.ps1").read_text(encoding="utf-8")
        wrapper = re.search(r"(?ms)^function Invoke-OwnedDiagnosticCommand\b.*?^}", source).group(0)
        quote = lambda value: "'" + str(value).replace("'", "''") + "'"
        with tempfile.TemporaryDirectory(prefix="owned-private-command-") as directory:
            evidence = Path(directory)
            child = evidence / "private-child.py"
            for status in (0, 7):
                child.write_text(
                    "import sys\nprint('PRIVATE_STDOUT_PATH=C:/private/input.md')\n"
                    "print('PRIVATE_STDERR_PATH=C:/private/input.md', file=sys.stderr)\n"
                    f"raise SystemExit({status})\n", encoding="utf-8")
                script = evidence / "probe.ps1"
                script.write_text(
                    "Set-StrictMode -Version Latest\n$ErrorActionPreference = 'Stop'\n" + wrapper + "\n"
                    f"$Evidence = {quote(evidence)}\n$script:MarkdownOwnedCommandSequence = 0\n"
                    "try {\n"
                    f"    Invoke-OwnedDiagnosticCommand {quote(sys.executable)} @({quote(child)})\n"
                    "} catch { Write-Host 'EXPECTED_PRIVATE_FAILURE=1' }\n",
                    encoding="utf-8")
                result = subprocess.run(
                    [powershell, "-NoProfile", "-NonInteractive", "-File", str(script)],
                    capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(result.stderr, "")
                expected = "MARKDOWN_OWNED_PROFILE_COMMAND_COMPLETE=1\n" if status == 0 else (
                    "MARKDOWN_OWNED_PROFILE_COMMAND_FAILED=1\nEXPECTED_PRIVATE_FAILURE=1\n")
                self.assertEqual(result.stdout, expected)
                log = (evidence / "command-001.log").read_text(encoding="utf-8-sig")
                self.assertIn("PRIVATE_STDOUT_PATH=C:/private/input.md", log)
                self.assertIn("PRIVATE_STDERR_PATH=C:/private/input.md", log)

    def test_actual_control_marker_projection_is_numeric_and_path_scoped(self):
        powershell = shutil.which("pwsh")
        if powershell is None:
            if sys.platform == "win32": self.fail("Windows requires PowerShell marker controls")
            self.skipTest("pwsh absent on non-Windows host")
        source = (ROOT / "tools/windows_ci.ps1").read_text(encoding="utf-8")
        wrapper = re.search(r"(?ms)^function Invoke-OwnedDiagnosticCommand\b.*?^}", source).group(0)
        quote = lambda value: "'" + str(value).replace("'", "''") + "'"
        with tempfile.TemporaryDirectory() as directory:
            evidence=Path(directory)
            for filename in ("test_markdown_owned_profile.py", "unrelated.py"):
                child=evidence/filename
                child.write_text("print('MARKDOWN_OWNED_CONTROL_STAGE=6')\n"
                    "print('MARKDOWN_OWNED_CONTROL_EXIT=7')\n"
                    "print('MARKDOWN_OWNED_CONTROL_STAGE=C:/private/secret')\n"
                    "print('MARKDOWN_OWNED_CONTROL_STAGE=6 extra')\n"
                    "print('MARKDOWN_OWNED_CONTROL_EXIT=12345678901')\n"
                    "print('PRIVATE_RAW_FAILURE')\nraise SystemExit(7)\n",encoding="utf-8")
                script=evidence/"probe.ps1"
                script.write_text("Set-StrictMode -Version Latest\n$ErrorActionPreference = 'Stop'\n"+wrapper+"\n"
                    +f"$Evidence = {quote(evidence)}\n$script:MarkdownOwnedCommandSequence = 0\n"
                    # Let PowerShell spell the fixture path exactly as the production
                    # guard does. Windows temp paths can use 8.3/case aliases;
                    # those aliases are intentionally not accepted by a lexical guard.
                    +f"try {{ Invoke-OwnedDiagnosticCommand {quote(sys.executable)} @((Join-Path $PSScriptRoot {quote(filename)})) }} catch {{ Write-Host 'EXPECTED=1' }}\n",encoding="utf-8")
                result=subprocess.run([powershell,"-NoProfile","-NonInteractive","-File",str(script)],capture_output=True,text=True,timeout=20)
                self.assertEqual(result.returncode,0);self.assertEqual(result.stderr,"")
                expected="MARKDOWN_OWNED_PROFILE_COMMAND_FAILED=1\n"
                if filename == "test_markdown_owned_profile.py":
                    expected+="MARKDOWN_OWNED_CONTROL_STAGE=6\nMARKDOWN_OWNED_CONTROL_EXIT=7\n"
                self.assertEqual(result.stdout,expected+"EXPECTED=1\n")

    def test_private_command_sink_is_scoped_to_diagnostic_only(self):
        source = (ROOT / "tools/windows_ci.ps1").read_text(encoding="utf-8")
        wrapper = re.search(r"(?ms)^function Invoke-OwnedDiagnosticCommand\b.*?^}", source).group(0)
        self.assertIn("& $Command @Arguments *> $Log", wrapper)
        self.assertNotIn("Write-Host ('> '", wrapper)
        self.assertNotIn("$_.", wrapper)
        self.assertIn("Set-Alias -Name Invoke-Checked -Value Invoke-OwnedDiagnosticCommand -Scope Local", source)
        tail = source[source.rindex("} catch {\n    if ($RunMarkdownOwnedProfile)"):]
        self.assertIn("MARKDOWN_OWNED_PROFILE_DIAGNOSTIC_FAILED=1", tail)
        self.assertIn("exit 1", tail)
        self.assertNotIn("$_.", tail)
        workflow = job("markdown-owned-profile")
        self.assertIn("tools/test_markdown_owned_workflow.py -v *> $Log", workflow)

    def test_diagnostic_guard_precedes_build_or_output(self):
        source = (ROOT / "tools/windows_ci.ps1").read_text(encoding="utf-8")
        guard = source.index("guard_markdown_owned_profile.py")
        self.assertLess(guard, source.index("$Ci = Join-Path $Root"))
        self.assertLess(guard, source.index("tools/build.py"))
        self.assertIn("if ($RunCallbackResearch -or $RunAclTests)", source[:guard])
        self.assertIn("$Ci = Join-Path $Root 'build/markdown-owned-profile'", source[:source.index("$Ci = Join-Path $Root 'build/windows-ci'")])
        self.assertIn("$Evidence = Join-Path $Ci 'private'", source)

    def test_gui_study_follows_controls_and_returns_before_acceptance(self):
        source = (ROOT / "tools/windows_ci.ps1").read_text(encoding="utf-8")
        build = source.index("Invoke-Checked $Python ($BuildArgs + @('--source','src/main.ru'")
        branch = source[build:source.index("# The bounded fold helper is a product input")]
        self.assertIn("if ($RunMarkdownOwnedProfile)", branch)
        self.assertIn("$Measurements = Join-Path $Ci 'measurements'", branch)
        self.assertIn("'--evidence-dir',$Measurements", branch)
        self.assertLess(branch.index("test_markdown_profile_public.py"),
                        branch.index("run_markdown_owned_profile.py"))
        controls = source.index("Invoke-Checked $Python @((Join-Path $PSScriptRoot 'test_markdown_owned_profile.py')")
        self.assertLess(controls, source.index("# Run the complete helper suite"))
        self.assertLess(controls, build)
        self.assertLess(branch.index("run_markdown_owned_profile.py"), branch.index("        return"))
        for forbidden in ("tools/windows_ci.py", "tools/package", "ResearchThenAcceptance"):
            self.assertNotIn(forbidden, branch)
        self.assertEqual(source.count("run_markdown_owned_profile.py"), 1)
        self.assertIn("if (-not $RunMarkdownOwnedProfile)", source[:build])
        self.assertIn("@('windir=C:/Windows')", source[:build])


if __name__ == "__main__":
    unittest.main()
