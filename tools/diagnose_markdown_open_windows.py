"""One fresh-process fence OPEN observation; NOT_ACCEPTED, never a GUI gate override."""
from contextlib import contextmanager
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time
from unittest.mock import patch

import windows_ci as ci

POST_SECONDS = (0.5, 15.0, 29.0)
FENCE_SHA256 = '2d9f79ee715b217c00792cf18a67485cdec96a14ea2ac86689156941a022c719'


class ProcessCpu:
    """Read only the Popen-owned handle, never OpenProcess or close/reopen it."""
    def __init__(self, process):
        if sys.platform != 'win32' or not getattr(process, '_handle', None):
            raise RuntimeError('actual Windows owned process handle required')
        self.handle = int(process._handle)
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.query = self.kernel.GetProcessTimes
        self.query.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
        self.query.restype = wintypes.BOOL

    def read(self):
        values = [wintypes.FILETIME() for _ in range(4)]
        if not self.query(self.handle, *(ctypes.byref(v) for v in values)):
            raise RuntimeError('GetProcessTimes failed')
        def ticks(v): return (int(v.dwHighDateTime) << 32) | int(v.dwLowDateTime)
        return {'kernel_100ns': ticks(values[2]), 'user_100ns': ticks(values[3])}


def cpu_sample(reader, clock=time.perf_counter):
    start = clock()
    try:
        values = reader.read()
        if (set(values) != {'kernel_100ns', 'user_100ns'} or
                any(type(v) is not int or v < 0 for v in values.values())):
            raise ValueError('invalid process CPU counter')
        return {'available': True, **values, 'query_wall_ms': (clock() - start) * 1000}
    except Exception as exc:
        return {'available': False, 'error_type': type(exc).__name__,
                'query_wall_ms': (clock() - start) * 1000}


def cpu_delta(start, end):
    if start.get('available') is not True or end.get('available') is not True:
        return {'available': False, 'reason': 'boundary sample unavailable'}
    delta = {k: end[k] - start[k] for k in ('kernel_100ns', 'user_100ns')}
    if any(v < 0 for v in delta.values()):
        return {'available': False, 'reason': 'nonmonotonic process CPU counter'}
    return {'available': True, **delta, 'total_cpu_ms': sum(delta.values()) / 10000}


class SchedulerProbe:
    def __init__(self, api, process, hwnd, record, clock=time.perf_counter):
        self.api, self.process, self.hwnd = api, process, hwnd
        self.record, self.clock, self.started, self.index = record, clock, None, 0
        self.original = api.no_dialog
        record.update(schedule_seconds=list(POST_SECONDS), requests=[], post_and_owner_check_wall_ms=0.0)

    def no_dialog(self, pid):
        windows = self.original(pid)  # Original modal exceptions must propagate.
        if self.started is None or pid != self.process.pid or self.process.poll() is not None:
            return windows
        elapsed = self.clock() - self.started
        if elapsed >= ci.GUI_MARKDOWN_TIMEOUT_SECONDS:
            return windows  # Never fill missing samples after the original deadline.
        due = []
        while self.index < len(POST_SECONDS) and elapsed >= POST_SECONDS[self.index]:
            due.append(self.index)
            self.index += 1
        for i in due:
            row = {'scheduled_ms': POST_SECONDS[i] * 1000, 'elapsed_ms': elapsed * 1000,
                   'sent': False}
            self.record['requests'].append(row)
            if i != due[-1]:
                row['reason'] = 'missed slot; no catch-up burst'
                continue
            begin = self.clock()
            try:
                self.api.verify_owned_handles(self.process.pid, self.hwnd)
                self.api.post_ru_snapshot(self.hwnd)
                row['sent'] = True
            finally:
                self.record['post_and_owner_check_wall_ms'] += (self.clock() - begin) * 1000
        return windows

    @contextmanager
    def installed(self):
        present = 'no_dialog' in self.api.__dict__
        saved = self.api.__dict__.get('no_dialog')
        self.api.no_dialog = self.no_dialog
        try:
            yield self
        finally:
            if present:
                self.api.no_dialog = saved
            else:
                del self.api.no_dialog


def verify_registry_removed(registry):
    import winreg
    prefix = 'Software\\ru_notepad\\SingleInstanceTests\\gui_'
    if not isinstance(registry, str) or not registry.startswith(prefix):
        raise ValueError('unexpected test registry namespace')
    suffix = registry[len(prefix):]
    if len(suffix) != 32 or any(c not in '0123456789abcdef' for c in suffix):
        raise ValueError('unexpected test registry token')
    for path in (registry, 'Software\\ru_notepad\\RecentTests\\gui_' + suffix):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path):
                raise RuntimeError('owned registry cleanup incomplete')
        except FileNotFoundError:
            pass


def run(runtime, hashes, evidence):
    import diagnose_instance_modal_windows as identity
    import gui_instance_tabs as instance
    identity.validate_runtime(runtime)
    if set(hashes) != set(ci.portable.RUNTIME_NAMES):
        raise ValueError('exact runtime hash inventory required')
    evidence = Path(evidence) / 'markdown-open'
    evidence.mkdir()
    owned = evidence.parent.parent / 'markdown-open-runtime'
    owned.mkdir()
    for name in ci.portable.RUNTIME_NAMES:
        shutil.copyfile(Path(runtime) / name, owned / name)
        if ci.sha(owned / name) != hashes[name]:
            raise ValueError('copied runtime mismatch')
    source = owned / 'unclosed-fence.md'
    data = ci.gui_markdown_fixture('unclosed-fence')[0]
    if len(data) != 1000000 or hashlib.sha256(data).hexdigest() != FENCE_SHA256:
        raise ValueError('original fence fixture changed')
    source.write_bytes(data)
    result = {'status': 'NOT_ACCEPTED', 'accepted': False, 'stage_passed': False,
              'measurement': 'Fresh process, only fence OPEN; not the prior multi-case workload. '
                  'Original 30-second deadline and all production stage predicates retained. '
                  'work/gap are callback wall intervals, CPU is whole-process kernel/user delta. '
                  'CPU-query and post/owner-check costs are recorded separately; scheduling-hook '
                  'clock/check overhead remains included in stage wall time, not separately subtracted.',
              'runtime_sha256': hashes, 'stage': {}, 'scheduler': {}, 'cpu': {},
              'registry_cleaned': False}
    registry = None
    def exercise(process, hwnd):
        api.verify_owned_handles(process.pid, hwnd)
        probe = SchedulerProbe(api, process, hwnd, result['scheduler'])
        try:
            reader = ProcessCpu(process)
        except Exception as exc:
            reader = None
            result['cpu']['initialization_error_type'] = type(exc).__name__
        def sample():
            return cpu_sample(reader) if reader is not None else {'available': False, 'reason': 'CPU reader unavailable'}
        def action():
            probe.started = time.perf_counter()
            result['cpu']['start'] = sample()
            api.drop(api.editor(hwnd), [source])
        try:
            with probe.installed():
                ci.run_gui_markdown_stage(api, process, hwnd, source, 'unclosed-fence', 'open', result['stage'], action)
            result['stage_passed'] = True
        finally:
            result['cpu']['end'] = sample()
            result['cpu']['delta'] = cpu_delta(result['cpu'].get('start', {}), result['cpu']['end'])
        return {}
    try:
        with patch.dict(os.environ, identity.child_environment(os.environ), clear=True):
            try:
                with instance.isolated_settings() as registry:
                    api = ci.Windows()
                    result['process'] = ci.run_gui(api, owned, evidence, name='markdown-open-diagnostic',
                        arguments=['--markdown-phase-diagnostics'], exercise=exercise, log_prefix='markdown-open')
            finally:
                if registry is not None:
                    verify_registry_removed(registry)
                    result['registry_cleaned'] = True
        logs = sorted(evidence.glob('markdown-open-*.log'))
        if len(logs) != 1:
            raise ValueError('one owned launcher log required')
        result['scheduler']['snapshots'] = ci.parse_gui_ru_snapshots(ci.bounded_text(logs[0]))
        sent = sum(x['sent'] for x in result['scheduler'].get('requests', []))
        if len(result['scheduler']['snapshots']) > sent:
            raise ValueError('unexpected additional scheduler snapshot')
        result['scheduler']['all_sent_snapshots_observed'] = len(result['scheduler']['snapshots']) == sent
    except Exception as exc:
        result['diagnostic_error_type'] = type(exc).__name__
    finally:
        result['source_bytes_unchanged'] = source.read_bytes() == data
        result['runtime_bytes_unchanged'] = all(ci.sha(owned / n) == h for n, h in hashes.items())
        (evidence / 'diagnostic.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    identity.validate_runtime(runtime)
    if not result['source_bytes_unchanged'] or not result['runtime_bytes_unchanged']:
        raise ValueError('diagnostic changed source or runtime bytes')
    return result
