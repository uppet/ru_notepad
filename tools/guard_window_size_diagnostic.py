#!/usr/bin/env python3
"""Admit only the explicit, isolated hidden-window size diagnostic invocation."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ONE_SHOT_TITLE = "诊断：确认七语验收窗口尺寸约束"
ALLOWED_REF = "refs/heads/wip"
MAX_EVENT_BYTES = 2 * 1024 * 1024


def enabled(value):
    return value is True or (type(value) is str and value == "true")


def disabled(value):
    return value is False or (type(value) is str and value in ("false", ""))


def validate_trigger(event_name, ref, event):
    """GitHub's expression comparisons ignore case; this final guard never does."""
    if ref != ALLOWED_REF or type(event) is not dict:
        raise ValueError("Rejected diagnostic trigger")
    allowed = False
    if event_name == "push":
        head = event.get("head_commit")
        allowed = (
            type(head) is dict
            and head.get("message") == ONE_SHOT_TITLE
            and event.get("deleted", False) is False
        )
    elif event_name == "workflow_dispatch":
        inputs = event.get("inputs")
        allowed = (
            type(inputs) is dict
            and enabled(inputs.get("i18n_window_diagnostic"))
            and disabled(inputs.get("syntax_growth_diagnostic", False))
            and disabled(inputs.get("historical_callback", False))
        )
    if not allowed:
        raise ValueError("Rejected diagnostic trigger")


def validate_environment():
    path = Path(os.environ["GITHUB_EVENT_PATH"])
    with path.open("rb") as stream:
        raw = stream.read(MAX_EVENT_BYTES + 1)
    if len(raw) > MAX_EVENT_BYTES:
        raise ValueError("Oversized diagnostic event")
    event = json.loads(raw)
    validate_trigger(os.environ["GITHUB_EVENT_NAME"], os.environ["GITHUB_REF"], event)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--guard-only", action="store_true")
    parser.parse_args()
    try:
        validate_environment()
    except (KeyError, OSError, ValueError, TypeError):
        print("WINDOW_SIZE_TRIGGER_REJECTED=1", file=sys.stderr)
        return 1
    print("WINDOW_SIZE_TRIGGER_ACCEPTED=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
