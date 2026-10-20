#!/usr/bin/env python3
"""Small Win32 measurement only: no Ru build, product edits, or release claim."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import stat
import sys

ROOT = Path(__file__).resolve().parents[1]
STYLE = 13565952
MAX_BYTES = 65536
SOURCE_PATHS = {
    'fixture': 'tests/fixtures/window_size_diagnostic.c',
    'runner': 'tools/run_window_size_diagnostic.py',
    'guard': 'tools/guard_window_size_diagnostic.py',
    'manifest': 'packaging/app.manifest',
    'production': 'src/main.ru',
    'acceptance': 'tests/app_i18n_native.ru',
    'catalog': 'src/i18n_catalog.ru',
}


def require(condition):
    if not condition:
        raise ValueError('Invalid fixed-schema window-size measurement')


def exact_keys(value, expected):
    require(type(value) is dict and set(value) == set(expected.split()))


def integer(value, low=-1000000, high=1000000):
    require(type(value) is int and low <= value <= high)


def vector(value, size):
    require(type(value) is list and len(value) == size)
    for item in value:
        integer(item)


def rect(value):
    vector(value, 4)
    require(value[2] > value[0] and value[3] > value[1])


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result)
        result[key] = value
    return result


def validate_measurements(stdout, stderr):
    require(type(stdout) is bytes and type(stderr) is bytes)
    require(0 < len(stdout) <= MAX_BYTES and stderr == b'')
    data = json.loads(stdout.decode('ascii'), object_pairs_hook=unique_object)
    exact_keys(data, 'schema system modes')
    integer(data['schema'], 1, 1)
    system = data['system']
    exact_keys(system, 'screen virtual_screen work max_track min_track maximized dpi_aware device_dpi pointer_bits compiled_style override_max_track')
    for key in ('screen', 'max_track', 'min_track', 'maximized', 'device_dpi', 'override_max_track'):
        vector(system[key], 2)
        require(all(v > 0 for v in system[key]))
    vector(system['virtual_screen'], 4)
    require(system['virtual_screen'][2] > 0 and system['virtual_screen'][3] > 0)
    rect(system['work'])
    integer(system['dpi_aware'], 1, 1)  # Unchanged manifest must be active.
    integer(system['pointer_bits'], 64, 64)
    integer(system['compiled_style'], STYLE, STYLE)
    require(system['override_max_track'] == [4096, 4096])
    require(type(data['modes']) is list and len(data['modes']) == 2)
    for policy, mode in enumerate(data['modes']):
        exact_keys(mode, 'policy states minmax')
        integer(mode['policy'], policy, policy)
        events = mode['minmax']
        require(type(events) is list and 1 <= len(events) <= 64)
        last_stage = 0
        for event in events:
            exact_keys(event, 'stage before after')
            integer(event['stage'], last_stage, 7)
            last_stage = event['stage']
            vector(event['before'], 10)
            vector(event['after'], 10)
            require(event['before'][8] > 0 and event['before'][9] > 0)
            expected = event['before'].copy()
            expected[6:8] = [640, 400]
            if policy:
                expected[8:10] = [max(4096, v) for v in expected[8:10]]
            require(event['after'] == expected)
        states = mode['states']
        require(type(states) is list and len(states) == 8)
        for stage, state in enumerate(states):
            exact_keys(state, 'stage target_width target_height iteration requested_outer outer client client_screen style exstyle visible dpi menu_count callback_count monitor work')
            integer(state['stage'], stage, stage)
            target = 0 if stage < 2 else (640, 900, 1600)[(stage - 2) // 2]
            integer(state['target_width'], target, target)
            height = 0 if stage < 2 else 720
            integer(state['target_height'], height, height)
            iteration = 0 if stage < 2 else (stage - 2) % 2 + 1
            integer(state['iteration'], iteration, iteration)
            vector(state['requested_outer'], 2)
            for key in ('outer', 'client', 'monitor', 'work'):
                rect(state[key])
            require(state['client'][0:2] == [0, 0])
            vector(state['client_screen'], 2)
            integer(state['style'], 0, 4294967295)
            require(state['style'] & 0x10000000 == 0)  # Hidden; retain OS-added style bits.
            require(state['style'] == states[0]['style'])
            integer(state['exstyle'], 0, 4294967295)
            integer(state['visible'], 0, 0)
            integer(state['dpi'], 0, 9600)  # 0 means API unavailable.
            integer(state['menu_count'], 0 if stage == 0 else 9, 0 if stage == 0 else 9)
            count = sum(e['stage'] <= stage for e in events)
            integer(state['callback_count'], count, count)
            if stage == 0:
                require(state['requested_outer'] == [1120, 760])
            elif stage == 1:
                require(state['requested_outer'] == [0, 0])
            else:
                previous = states[stage - 1]
                outer, client = previous['outer'], previous['client']
                require(state['requested_outer'] == [
                    target + outer[2] - outer[0] - client[2] + client[0],
                    720 + outer[3] - outer[1] - client[3] + client[1],
                ])
                require(all(v > 0 for v in state['requested_outer']))
    return data


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes():
    return {key: sha(ROOT / value) for key, value in SOURCE_PATHS.items()}


def make_report(data, sources, executable_sha256):
    require(set(sources) == set(SOURCE_PATHS))
    for digest in [*sources.values(), executable_sha256]:
        require(type(digest) is str and len(digest) == 64 and
                all(c in '0123456789abcdef' for c in digest))
    # Revalidate the entire allowlisted numeric tree, including publication calls.
    validate_measurements(json.dumps(data, separators=(',', ':')).encode('ascii'), b'')
    return {'schema': 1, 'measurement_only': 1, 'windows_executed': 1,
            'source_sha256': sources, 'exe_sha256': executable_sha256, 'measurements': data}


def publish_report(private, public, report):
    exact_keys(report, 'schema measurement_only windows_executed source_sha256 exe_sha256 measurements')
    for key in ('schema', 'measurement_only', 'windows_executed'):
        integer(report[key], 1, 1)
    make_report(report['measurements'], report['source_sha256'], report['exe_sha256'])
    payload = (json.dumps(report, sort_keys=True, separators=(',', ':')) + '\n').encode('ascii')
    require(len(payload) <= MAX_BYTES)
    temporary = private / 'measurements.validated.json'
    with temporary.open('xb') as stream:
        require(stream.write(payload) == len(payload))
        stream.flush()
        os.fsync(stream.fileno())
    require(temporary.stat().st_size == len(payload) and read_bounded(temporary) == payload)
    # mkdir is exclusive; hard-link is an atomic no-replace publication, unlike
    # rename on POSIX (which can silently replace a pre-existing destination).
    public.mkdir(exist_ok=False)
    final = public / 'measurements.json'
    os.link(temporary, final)
    try:
        source_stat, final_stat = temporary.stat(), final.lstat()
        require(stat.S_ISREG(final_stat.st_mode) and
                (source_stat.st_dev, source_stat.st_ino) == (final_stat.st_dev, final_stat.st_ino) and
                source_stat.st_size == final_stat.st_size == len(payload) and
                read_bounded(final) == payload)
    except Exception:
        # Remove only the link we created, never a raced-in replacement file.
        if final.exists() and not final.is_symlink() and os.path.samefile(temporary, final):
            final.unlink()
        raise


def read_bounded(path):
    with path.open('rb') as stream:
        value = stream.read(MAX_BYTES + 1)
    require(len(value) <= MAX_BYTES)
    return value


def main():
    # Fixed guard belongs to the separately reviewed one-time workflow control.
    sys.path.insert(0, str(ROOT / 'tools'))
    from guard_window_size_diagnostic import validate_environment
    validate_environment()
    parser = argparse.ArgumentParser()
    parser.add_argument('--msys-root', type=Path, required=True)
    args = parser.parse_args()
    require(os.name == 'nt')  # A PE compile or emulation is not Windows evidence.
    source_before = source_hashes()
    private = ROOT / 'build/window-size-diagnostic-private'
    public = ROOT / 'build/window-size-diagnostic-public'
    require(not public.exists() and not public.is_symlink())
    private.mkdir(parents=True, exist_ok=False)
    binpath = args.msys_root.resolve() / 'mingw64/bin'
    gcc, windres = binpath / 'gcc.exe', binpath / 'windres.exe'
    require(gcc.is_file() and windres.is_file())
    env = dict(os.environ)
    env['PATH'] = str(binpath) + os.pathsep + env.get('PATH', '')
    env['PYTHONDONTWRITEBYTECODE'] = '1'

    def run(tag, command, timeout):
        with (private / (tag + '.stdout.log')).open('xb') as out, (private / (tag + '.stderr.log')).open('xb') as err:
            result = subprocess.run([str(c) for c in command], cwd=ROOT, env=env,
                                    stdout=out, stderr=err, timeout=timeout, check=False)
        require(result.returncode == 0)

    resource = private / 'manifest.rc'
    # ROOT is the resource compiler's cwd; no interpolated path enters this file.
    resource.write_text('1 24 "packaging/app.manifest"\n', encoding='ascii')
    obj, exe = private / 'manifest.o', private / 'window_size_diagnostic.exe'
    run('resource', [windres, '-I', ROOT, resource, '-O', 'coff', '-o', obj], 30)
    run('compile', [gcc, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                    ROOT / SOURCE_PATHS['fixture'], obj, '-o', exe, '-luser32', '-lgdi32'], 120)
    exe_before = sha(exe)
    run('native', [exe], 30)
    data = validate_measurements(read_bounded(private / 'native.stdout.log'),
                                 read_bounded(private / 'native.stderr.log'))
    require(source_hashes() == source_before and sha(exe) == exe_before)
    report = make_report(data, source_before, exe_before)
    publish_report(private, public, report)
    print('WINDOW_SIZE_DIAGNOSTIC 1')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # Raw exceptions, commands, paths, and logs stay outside public output.
        print('WINDOW_SIZE_DIAGNOSTIC 0', file=sys.stderr)
        raise SystemExit(1)
