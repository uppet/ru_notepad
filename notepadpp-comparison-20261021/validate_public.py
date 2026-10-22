"""Revalidate only the closed numeric/hash publication schema before upload."""
import json
import re
import sys
from pathlib import Path
from public_result import fields, h, need, number as raw_number


def number(x):
    need(type(x) in (int, float))
    return raw_number(x)


def validate(x):
    fields(x, 'schema observer_revision markdown_poll_seconds markdown_native_common_separate markdown_diagnostics feasibility_only baseline_commit fixture_sha256 harness_sha256 receipt_sha256 clock_resolution_seconds requested_poll_seconds stages_seconds process_seconds text_times_are_observable_upper_bounds runs host npp_version toolchain runtime_sha256')
    need(set(x) == set('schema observer_revision markdown_poll_seconds markdown_native_common_separate markdown_diagnostics feasibility_only baseline_commit fixture_sha256 harness_sha256 receipt_sha256 clock_resolution_seconds requested_poll_seconds stages_seconds process_seconds text_times_are_observable_upper_bounds runs host npp_version toolchain runtime_sha256'.split()))
    need(x['schema'] == 2 and x['feasibility_only'] == 1)
    need(type(x['observer_revision']) is int and x['observer_revision']==2)
    need(type(x['markdown_poll_seconds']) in (int,float) and x['markdown_poll_seconds']==.25)
    need(type(x['markdown_native_common_separate']) is int and x['markdown_native_common_separate']==0)
    need(type(x['markdown_diagnostics']) is int and x['markdown_diagnostics']==1)
    need(x['baseline_commit'] == '6aa535d62c28cc9a03f33c3610fe99b3cf1bd14e')
    need(x['stages_seconds'] == 30 and x['process_seconds'] == 120)
    need(type(x['npp_version']) is list and all(type(v) is int for v in x['npp_version']) and x['npp_version'] == [8, 9, 8, 1])
    for k in ('fixture_sha256', 'harness_sha256', 'receipt_sha256'): h(x[k])
    for k in ('schema', 'feasibility_only', 'clock_resolution_seconds', 'requested_poll_seconds', 'stages_seconds', 'process_seconds', 'text_times_are_observable_upper_bounds'): number(x[k])
    fields(x['host'], 'windows_version cpu_count cpu_identifier_sha256 runner_image_sha256')
    need(type(x['host']['windows_version']) is list and len(x['host']['windows_version']) == 3)
    for n in x['host']['windows_version']: number(n)
    number(x['host']['cpu_count'])
    for k in ('cpu_identifier_sha256','runner_image_sha256'): h(x['host'][k])
    fields(x['toolchain'], 'gcc.exe g++.exe windres.exe ar.exe ranlib.exe mingw32-make.exe')
    need(set(x['toolchain']) == set('gcc.exe g++.exe windres.exe ar.exe ranlib.exe mingw32-make.exe'.split()))
    for t in x['toolchain'].values():
        fields(t, 'sha256 version_stdout_sha256 path_sha256')
        need(set(t) == set('sha256 version_stdout_sha256 path_sha256'.split()))
        for v in t.values(): h(v)
    fields(x['runtime_sha256'], 'ru npp')
    need(set(x['runtime_sha256']) == {'ru', 'npp'})
    need(set(x['runtime_sha256']['ru']) == set('ru_notepad.exe Scintilla.dll Lexilla.dll RuSyntax.dll'.split()))
    need('notepad++.exe' in x['runtime_sha256']['npp'])
    for k, runtime in x['runtime_sha256'].items():
        fields(runtime, 'ru_notepad.exe Scintilla.dll Lexilla.dll RuSyntax.dll' if k == 'ru' else 'notepad++.exe SciLexer.dll Scintilla.dll Lexilla.dll')
        for v in runtime.values(): h(v)
    need(type(x['runs']) is list and 1 <= len(x['runs']) <= 3)
    for i, r in enumerate(x['runs']):
        fields(r, 'arm executed stages passed pid error_kind elapsed_upper_ms timed_out exit_code cleanup_unconfirmed fixture_unchanged runtime_unchanged provenance_unchanged')
        need({'arm','executed','stages','passed'} <= set(r))
        for k, value in r.items():
            if k != 'stages' and value is not None: number(value)
        need(r['arm'] == i and type(r['stages']) is list and len(r['stages']) <= 4)
        for j, s in enumerate(r['stages']):
            fields(s, 'operation completed censored pending_poll_count undo_commands undo_acknowledged first_text_upper_ms first_common_upper_ms savepoint_text_upper_ms rounds dispatches last wall_ms poll_count poll_gap_min_ms poll_gap_max_ms poll_gap_p50_ms poll_gap_p95_ms')
            need({'operation','completed','censored','rounds','dispatches','poll_count'} <= set(s))
            for k, value in s.items():
                if k not in ('rounds','dispatches','last') and value is not None: number(value)
            need(s['operation'] == j)
            need(type(s['rounds']) is list and type(s['dispatches']) is list)
            need(len(s['rounds']) <= 2 and len(s['dispatches']) <= 2)
            for v in s['rounds']:
                fields(v, 'command dirty length upper_ms')
                for n in v.values(): number(n)
            for v in s['dispatches']:
                fields(v, 'acknowledged delivery_completion_unknown upper_ms')
                for n in v.values(): number(n)
            if 'pending_poll_count' in s:need(type(s['pending_poll_count']) is int and 0<=s['pending_poll_count']<=25000)
            if i==2 and s['completed']:need('last' in s)
            if 'last' in s:
                fields(s['last'], 'length dirty lexer endstyled styles fold_header context_sha256 markdown_id markdown_gen markdown_rev markdown_pending markdown_length markdown_feed')
                for k, n in s['last'].items():
                    if k not in ('styles','context_sha256'): number(n)
                if 'styles' in s['last']:
                    need(type(s['last']['styles']) is list and len(s['last']['styles']) == 16)
                    for n in s['last']['styles']: number(n)
                if 'context_sha256' in s['last']: h(s['last']['context_sha256'])
                md=set('markdown_id markdown_gen markdown_rev markdown_pending markdown_length markdown_feed'.split())
                if md & set(s['last']):
                    need(md<=set(s['last']))
                    for key in md:need(type(s['last'][key]) is int and 0<=s['last'][key]<=1e12)
                    need(s['last']['markdown_id']>0 and s['last']['markdown_gen']>0 and s['last']['markdown_pending'] in (0,1))
                if i==2 and s['completed']:
                    need(md<=set(s['last']) and s['last']['markdown_pending']==0)
                    need(s['last']['markdown_length']==s['last']['markdown_feed']==s['last']['length'])
    def leaves(v):
        if type(v) is dict:
            for item in v.values(): leaves(item)
        elif type(v) is list:
            for item in v: leaves(item)
        elif type(v) is str:
            need(v == x['baseline_commit'] or re.fullmatch('[0-9a-f]{64}', v) is not None)
        elif v is not None: number(v)
    leaves(x)
    need(len(json.dumps(x, allow_nan=False).encode()) <= 65536)
    return x


def unique(pairs):
    d = {}
    for k, v in pairs:
        need(k not in d); d[k] = v
    return d


def main():
    p = Path(sys.argv[1])
    need(p.is_file() and not p.is_symlink() and p.stat().st_nlink == 1 and p.stat().st_size <= 65536)
    validate(json.loads(p.read_text(encoding='utf-8'), object_pairs_hook=unique))


if __name__ == '__main__':
    try: main()
    except Exception:
        print('COMPARISON_PUBLIC_VALIDATION_FAILED', file=sys.stderr)
        raise SystemExit(1)
