#!/usr/bin/env python3
"""Strictly admit only explicit manual two-fixture Windows diagnostics."""
import json
import os
from pathlib import Path
import sys

ALLOWED_REF = 'refs/heads/wip'
MAX_EVENT_BYTES = 2 * 1024 * 1024


def enabled(value):
    return value is True or (type(value) is str and value == 'true')


def disabled(value):
    return value is False or (type(value) is str and value in ('false', ''))


def validate_trigger(event_name, ref, event):
    """Retired push titles never bypass this case-sensitive manual-only guard."""
    allowed = False
    if event_name == 'workflow_dispatch' and ref == ALLOWED_REF and type(event) is dict:
        inputs = event.get('inputs')
        allowed = (type(inputs) is dict and enabled(inputs.get('i18n_focused_diagnostic'))
                   and all(disabled(inputs.get(key, False)) for key in (
                       'i18n_window_diagnostic', 'syntax_growth_diagnostic', 'historical_callback', 'markdown_owned_profile')))
    if not allowed:
        raise ValueError('Rejected diagnostic trigger')


def validate_environment():
    with Path(os.environ['GITHUB_EVENT_PATH']).open('rb') as stream:
        raw = stream.read(MAX_EVENT_BYTES + 1)
    if len(raw) > MAX_EVENT_BYTES:
        raise ValueError('Rejected diagnostic trigger')
    validate_trigger(os.environ['GITHUB_EVENT_NAME'], os.environ['GITHUB_REF'], json.loads(raw))


def main():
    try:
        if sys.argv[1:] != ['--guard-only']:
            raise ValueError('Rejected diagnostic trigger')
        validate_environment()
    except Exception:
        print('FOCUSED_NATIVE_TRIGGER_REJECTED=1', file=sys.stderr)
        return 1
    print('FOCUSED_NATIVE_TRIGGER_ACCEPTED=1')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
