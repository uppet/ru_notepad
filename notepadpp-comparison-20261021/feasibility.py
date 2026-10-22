"""Owned-process, synthetic 1MB edit feasibility. Not a performance acceptance test.
No download, injection, global input, or publishing. Windows execution is opt-in.
"""
from __future__ import annotations
import argparse, ctypes, hashlib, importlib.util, json, os
from pathlib import Path
import subprocess, sys, threading, time, shutil
import build_baseline as provenance
from public_result import project as public_projection

BASELINE = '6aa535d62c28cc9a03f33c3610fe99b3cf1bd14e'
SIZE = 1_000_000
POLL = .005
STAGE = 30.
HARD = 120.


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_ci(root):
    path = Path(root).resolve() / 'tools/windows_ci.py'
    spec = importlib.util.spec_from_file_location('_comparison_ci', path)
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    if Path(module.portable.__file__).resolve() != path.with_name('package.py'):
        raise RuntimeError('wrong packaging module')
    return module


class Deadline:
    def __init__(self, clock=time.perf_counter):
        self.clock = clock
        self.started = clock()
        self.hard = self.started + HARD
        self.stage = self.started + STAGE
    def remaining(self):
        left = min(self.hard, self.stage) - self.clock()
        if left <= 0:
            raise TimeoutError('deadline')
        return left
    def next_stage(self):
        self.stage = min(self.hard, self.clock() + STAGE)
    def timeout_ms(self):
        return max(1, min(1000, int(self.remaining() * 1000)))


def target(operation, undo_index=0, clean=False):
    inserted = operation == 'insert' or (operation == 'undo' and undo_index == 1 and not clean)
    return SIZE + int(inserted), (97, 97, 120, 97) if inserted else (97, 97, 97, 97)


def text_matches(snap, operation, undo_index=0):
    # A single natural group can restore savepoint. Never force group boundaries.
    clean = operation == 'undo' and not snap['dirty']
    length, context = target(operation, undo_index, clean)
    dirty = operation in ('insert', 'backspace') or (operation == 'undo' and not clean)
    return snap['length'] == length and tuple(snap['context']) == context and snap['dirty'] == dirty


def common_ready(snap, arm):
    lexer_ok = snap['lexer'] == 98 if arm == 'C' else snap['lexer'] in (0, 1)
    # An unattached/container lexer has no lexer-owned styling completion promise.
    end_ok = snap['endstyled'] == snap['length'] if arm == 'C' else True
    return lexer_ok and end_ok and snap['styles'] == [0] * 16 and not snap['fold_header']


def run_stage(api, hwnd, editor, deadline, arm, operation, result, clock=time.perf_counter, sleep=time.sleep):
    if operation != 'open':
        deadline.next_stage()
    started = deadline.started if operation == 'open' else clock()
    result.update(operation=operation, completed=False, censored=False, undo_commands=0, undo_acknowledged=0,
                  first_text_upper_ms=None, first_common_upper_ms=None, savepoint_text_upper_ms=None, rounds=[], poll_gaps_ms=[])
    previous = started
    def dispatch(action):
        a = clock(); event = {'acknowledged': False, 'delivery_completion_unknown': True}
        result.setdefault('dispatches', []).append(event)
        try:
            action()
            event.update(acknowledged=True, delivery_completion_unknown=False)
        finally:
            event['upper_ms'] = (clock() - a) * 1000
    if operation == 'insert':
        dispatch(lambda: (api.scalar(editor, 2025, 8), api.scalar(editor, 0x102, 120)))
    elif operation == 'backspace':
        dispatch(lambda: (api.scalar(editor, 2025, 9), api.scalar(editor, 0x100, 8), api.scalar(editor, 0x101, 8)))
    elif operation == 'undo':
        result['undo_commands'] = 1
        dispatch(lambda: api.command(hwnd, 42003 if arm == 'B' else 201))
        result['undo_acknowledged'] = 1
    tail = False
    while True:
        deadline.remaining()
        now = clock()
        result['poll_gaps_ms'].append((now - previous) * 1000)
        previous = now
        snap = {'length': api.scalar(editor, 2006), 'dirty': bool(api.scalar(editor, 2159)),
                'context': [api.scalar(editor, 2007, i) & 255 for i in range(6, 10)]}
        result['last'] = snap
        matches = text_matches(snap, operation, result['undo_commands'])
        if matches and operation == 'undo' and not snap['dirty'] and result['savepoint_text_upper_ms'] is None:
            result['savepoint_text_upper_ms'] = (clock() - started) * 1000
        if matches and result['first_text_upper_ms'] is None:
            result['first_text_upper_ms'] = (clock() - started) * 1000
        if matches and not tail:
            api.scalar(editor, 2025, snap['length']); api.scalar(editor, 2169)
            tail = True
        if matches and tail:
            positions = list(range(8)) + list(range(snap['length'] - 8, snap['length']))
            snap.update(lexer=api.scalar(editor, 4002), endstyled=api.scalar(editor, 2028),
                        styles=[api.scalar(editor, 2010, i) for i in positions],
                        fold_header=bool(api.scalar(editor, 2223, 0) & 0x2000))
            if common_ready(snap, arm):
                api.scalar(hwnd, 0); api.scalar(editor, 0)
                if result['first_common_upper_ms'] is None:
                    result['first_common_upper_ms'] = (clock() - started) * 1000
                pending_done = arm != 'C' or api.markdown_done(hwnd)
                if pending_done:
                    result['rounds'].append({'command': result['undo_commands'], 'dirty': snap['dirty'],
                                            'length': snap['length'], 'upper_ms': (clock() - started) * 1000})
                    if operation == 'undo' and snap['dirty']:
                        if result['undo_commands'] >= 2 or not api.scalar(editor, 2174):
                            raise RuntimeError('undo did not reach savepoint in two natural groups')
                        result['undo_commands'] += 1
                        dispatch(lambda: api.command(hwnd, 42003 if arm == 'B' else 201))
                        result['undo_acknowledged'] += 1
                        tail = False
                    else:
                        deadline.remaining()
                        result.update(completed=True, wall_ms=(clock() - started) * 1000)
                        return
        sleep(min(POLL, deadline.remaining()))


def owned_api(ci, process, deadline):
    class API(ci.Windows):
        def scalar(self, hwnd, message, wparam=0, lparam=0):
            if process.poll() is not None:
                raise RuntimeError('owned process exited')
            self.verify_owned_handles(process.pid, hwnd)
            result = ctypes.c_size_t()
            if not self.user.SendMessageTimeoutW(hwnd, message, wparam, lparam, 3,
                                                deadline.timeout_ms(), ctypes.byref(result)):
                raise TimeoutError('owned message timeout')
            deadline.remaining()
            return result.value
        def markdown_done(self, hwnd):
            status = self.markdown_status(self.control(hwnd, 11))
            return ci.markdown_status_complete(status)
    return API()


def closed_manifest(root, expected):
    root = provenance.plain(root, directory=True)
    actual = {}
    for path in root.rglob('*'):
        if path.is_dir():
            provenance.plain(path, directory=True)
        else:
            provenance.plain(path)
            actual[path.relative_to(root).as_posix()] = digest(path)
    if actual != expected:
        raise ValueError('runtime inventory mismatch')
    return actual


def copy_runtime(source, target, expected):
    # Copy only sealed files; never recursively carry arbitrary DLL/config files.
    target.mkdir()
    for name, value in expected.items():
        parts = name.split('/')
        if not parts or any(x in ('', '.', '..') or ':' in x or '\\' in x for x in parts):
            raise ValueError('unsafe inventory path')
        original = provenance.under(source, name)
        if digest(original) != value: raise ValueError('source changed before copy')
        dest = target.joinpath(*parts)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with original.open('rb') as inp, dest.open('xb') as out:
            shutil.copyfileobj(inp, out)
    closed_manifest(target, expected)


def verify_receipt(receipt, ru_dir, npp_dir):
    if receipt.get('baseline_commit') != BASELINE or receipt.get('compiler_commit') != provenance.COMPILER or receipt.get('compiler_tree') != provenance.COMPILER_TREE:
        raise ValueError('wrong source baseline/compiler')
    required = {'ru_notepad.exe', 'Scintilla.dll', 'Lexilla.dll', 'RuSyntax.dll'}
    if set(receipt['runtime']['ru']) != required: raise ValueError('incomplete Ru receipt')
    allowed_ru = dict(receipt['runtime']['ru'])
    for filename,key in [('ru_notepad.build.json','build_receipt_sha256'),('comparison-build.json','build_provenance_sha256'),('RuSyntax.native-build.json','native_receipt_sha256')]:
        allowed_ru[filename] = receipt[key]
    closed_manifest(ru_dir, allowed_ru)
    closed_manifest(npp_dir, receipt['npp_all_files_sha256'])
    for name,value in receipt['runtime']['npp'].items():
        if '/' in name or receipt['npp_all_files_sha256'].get(name)!=value:raise ValueError('NPP root inventory mismatch')
    if receipt['npp_archive_sha256'] != __import__('acquire_npp').PINS['npp.8.9.8.1.portable.x64.zip'][1]:raise ValueError('NPP archive mismatch')
    for marker in ('disableNppAutoUpdate.xml','doLocalConf.xml'):
        if (npp_dir/marker).stat().st_size != 0:raise ValueError('invalid isolation marker')


def cleanup_owned(process, hard, clock=time.perf_counter):
    if process.poll() is None: process.kill()
    remaining = hard - clock()
    if process.poll() is None and remaining > 0:
        try: process.wait(timeout=remaining)
        except subprocess.TimeoutExpired: pass
    code = process.poll()
    return {'exit_code': code, 'cleanup_unconfirmed': code is None}


def run_one(ci, arm, executable, source, scratch, inventory):
    deadline = Deadline()
    result = {'arm': arm, 'executed': False, 'stages': [{'operation': 'open', 'completed': False, 'censored': False}], 'passed': False}
    argv = [str(executable)]
    if arm == 'B':
        settings = scratch / 'settings'; settings.mkdir()
        argv += ['-multiInst', '-noPlugin', '-nosession', '-lnormal', '-settingsDir=' + str(settings)]
    argv += [str(source)]
    process = None; guard = None
    try:
        closed_manifest(executable.parent, inventory)
        process = subprocess.Popen(argv, cwd=executable.parent, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
        result.update(executed=True, pid=process.pid)
        # Guard holds exact Popen, never PID/name lookup; independent of blocked GUI thread.
        guard = threading.Timer(max(0, deadline.hard - time.perf_counter()),
                                lambda: process.kill() if process.poll() is None else None)
        guard.daemon = True; guard.start()
        api = owned_api(ci, process, deadline)
        classname = 'Notepad++' if arm == 'B' else ci.MAIN_CLASS
        while True:
            deadline.remaining()
            windows = api.no_dialog(process.pid)
            matches = [h for h, c, visible in windows if c == classname and visible]
            if len(matches) > 1: raise RuntimeError('ambiguous main window')
            if matches:
                hwnd = matches[0]
                try: editor = api.editor(hwnd)
                except RuntimeError: time.sleep(POLL); continue
                if api.scalar(editor, 2006) == SIZE: break
            time.sleep(POLL)
        if arm == 'B':
            buffer_id = api.scalar(hwnd, 2084)
            if api.scalar(hwnd, 2088, buffer_id) != 0: raise RuntimeError('NPP not plain text')
        else:
            if api.text(hwnd).removeprefix('* ') != source.name + ' · ru_notepad':
                raise RuntimeError('wrong opened fixture')
        for operation in ('open', 'insert', 'backspace', 'undo'):
            if operation == 'open': stage = result['stages'][0]
            else:
                stage = {}; result['stages'].append(stage)
            run_stage(api, hwnd, editor, deadline, arm, operation, stage)
        result['passed'] = True
    except Exception as exc:
        result['error_type'] = type(exc).__name__
        result['elapsed_upper_ms'] = (time.perf_counter() - deadline.started) * 1000
        result['timed_out'] = isinstance(exc, TimeoutError)
        if result['stages']:
            result['stages'][-1]['censored'] = isinstance(exc, TimeoutError)
    finally:
        if guard: guard.cancel()
        if process:
            try:
                result.update(cleanup_owned(process, deadline.hard))
            except OSError:
                result['cleanup_unconfirmed'] = True
            if result['cleanup_unconfirmed']: result['passed'] = False
        try:
            closed_manifest(executable.parent, inventory)
            result['runtime_unchanged'] = True
        except (ValueError, OSError):
            result['runtime_unchanged'] = False
            result['passed'] = False
        try:
            result['fixture_unchanged'] = digest(source) == hashlib.sha256(b'a' * SIZE).hexdigest()
        except OSError:
            result['fixture_unchanged'] = False
        if not result['fixture_unchanged']: result['passed'] = False
    return result


def drive_arms(launch, results, checkpoint):
    for arm in 'ABC':
        try: result = launch(arm)
        except (ValueError,OSError,subprocess.SubprocessError) as exc:
            result = {'arm':arm,'executed':False,'passed':False,'error_type':type(exc).__name__,'stages':[]}
        results.append(result)
        checkpoint()
        if not result['passed'] or result.get('cleanup_unconfirmed',False): break


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source-root', type=Path, required=True)
    ap.add_argument('--ru-dir', type=Path, required=True)
    ap.add_argument('--npp-dir', type=Path, required=True)
    ap.add_argument('--receipt', type=Path, required=True)
    ap.add_argument('--compiler', type=Path, required=True)
    ap.add_argument('--cc', type=Path, required=True)
    ap.add_argument('--npp-receipt', type=Path, required=True)
    ap.add_argument('--output-root', type=Path, required=True)
    args = ap.parse_args()
    if os.name != 'nt': raise RuntimeError('native Windows required; no emulation')
    provenance.host_guard()
    for key in ('source_root','ru_dir','npp_dir','compiler'):
        setattr(args,key,provenance.plain(getattr(args,key),directory=True))
    for key in ('receipt','npp_receipt'):
        setattr(args,key,provenance.plain(getattr(args,key)))
    args.cc=provenance.compiler_file(args.cc)
    args.output_root=Path(os.path.abspath(args.output_root))
    provenance.plain(args.output_root.parent,directory=True)
    receipt = provenance.read(args.receipt)
    import seal_receipt
    def revalidate():
        verify_receipt(receipt, args.ru_dir, args.npp_dir)
        if seal_receipt.seal(args.source_root,args.compiler,args.cc,args.ru_dir,args.npp_dir,args.npp_receipt) != receipt:
            raise ValueError('sealed provenance changed')
    revalidate()
    head = subprocess.check_output(['git', '-C', str(args.source_root), 'rev-parse', 'HEAD'], text=True).strip()
    if head != BASELINE: raise ValueError('source checkout mismatch')
    if subprocess.check_output(['git', '-C', str(args.source_root), 'status', '--porcelain', '--untracked-files=no'], text=True).strip():
        raise ValueError('modified source checkout')
    args.output_root.mkdir()  # Refuse re-use; never overwrite prior evidence.
    ci = load_ci(args.source_root)
    report = {'schema': 1, 'feasibility_only': True, 'baseline_commit': BASELINE,
              'host': {'windows_version':list(sys.getwindowsversion()[:3]),'cpu_count':os.cpu_count() or 0,
                       'cpu_identifier_sha256':hashlib.sha256(os.environ.get('PROCESSOR_IDENTIFIER','').encode()).hexdigest(),
                       'runner_image_sha256':hashlib.sha256((os.environ.get('ImageOS','')+'|'+os.environ.get('ImageVersion','')).encode()).hexdigest()},
              'npp_version':[8,9,8,1],'toolchain':receipt['tools'],
              'runtime_sha256':receipt['runtime'],
              'fixture_sha256': hashlib.sha256(b'a' * SIZE).hexdigest(),
              'harness_sha256': provenance.digest({name: digest(Path(__file__).with_name(name)) for name in ('feasibility.py','build_baseline.py','public_result.py','acquire_npp.py','seal_receipt.py')}), 'receipt_sha256': digest(args.receipt),
              'clock_resolution_seconds': time.get_clock_info('perf_counter').resolution,
              'requested_poll_seconds': POLL, 'stages_seconds': STAGE, 'process_seconds': HARD,
              'text_times_are_observable_upper_bounds': True, 'runs': []}
    def launch(arm):
        scratch = args.output_root / arm; scratch.mkdir()
        source = scratch / ('fixture.md' if arm == 'C' else 'fixture.txt')
        source.write_bytes(b'a' * SIZE)
        runtime = scratch / 'runtime'
        inventory = receipt['npp_all_files_sha256'] if arm == 'B' else receipt['runtime']['ru']
        revalidate()
        copy_runtime(args.npp_dir if arm == 'B' else args.ru_dir, runtime, inventory)
        # Isolated writable portable/runtime copy for each fresh owned process.
        exe = runtime / ('notepad++.exe' if arm == 'B' else 'ru_notepad.exe')
        result = run_one(ci, arm, exe, source, scratch, inventory)
        try:
            revalidate()
            result['provenance_unchanged'] = True
        except (ValueError, OSError, subprocess.SubprocessError):
            result['provenance_unchanged'] = False
            result['passed'] = False
        return result
    def checkpoint():
        (args.output_root / 'result.json').write_text(json.dumps(public_projection(report), indent=2, allow_nan=False) + '\n')
    drive_arms(launch, report['runs'], checkpoint)
    return 0 if all(r['passed'] for r in report['runs']) else 1


if __name__ == '__main__':
    try:
        result = main()
    except Exception:
        import sys
        print('COMPARISON_FAILURE_CODE=4', file=sys.stderr)
        raise SystemExit(1)
    raise SystemExit(result or 0)
