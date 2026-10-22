"""Real Windows preparation controls: no GUI launch, input, or binary cache."""
import argparse
import sys
from pathlib import Path
import build_baseline as b
import acquire_npp as n
import feasibility as f

STAGE = 0


def main():
    global STAGE
    ap = argparse.ArgumentParser()
    for name in ('baseline', 'compiler', 'npp', 'receipt', 'future-output'):
        ap.add_argument('--' + name, type=Path, required=True)
    a = ap.parse_args()
    STAGE = 1
    b.host_guard()
    STAGE = 2
    a.baseline = b.plain(a.baseline, directory=True)
    a.compiler = b.plain(a.compiler, directory=True)
    a.npp = b.plain(a.npp, directory=True)
    a.receipt = b.plain(a.receipt)
    b.plain(a.future_output.absolute().parent, directory=True)
    b.need(not a.future_output.exists())
    STAGE = 3
    b.checkout(a.baseline, b.BASELINE)
    b.verify_compiler(a.compiler)
    STAGE = 4
    receipt = b.read(a.receipt)
    b.need(receipt['archive_sha256'] == n.PINS['npp.8.9.8.1.portable.x64.zip'][1])
    b.need(receipt['executed'] is False)
    f.closed_manifest(a.npp, receipt['files'])
    b.need(len(receipt['files']) == receipt['file_count'])
    b.need(b.sha(b.under(a.npp, 'notepad++.exe')) == receipt['executable_sha256'])
    for name in ('doLocalConf.xml', 'disableNppAutoUpdate.xml'):
        b.need(b.sha(b.under(a.npp, name)) == receipt['files'][name])
    STAGE = 5
    b.load_protocol(a.baseline)
    STAGE = 6
    ci = f.load_ci(a.baseline)
    STAGE = 7
    ci.Windows()  # Bind actual ctypes/user32 signatures; no process/window/input actions.
    print('COMPARISON_WINDOWS_SMOKE=1')


if __name__ == '__main__':
    try: main()
    except Exception as exc:
        print('COMPARISON_FAILURE_CODE=5', file=sys.stderr)
        stage, kind, source, line = f.failure_diagnostics(exc, STAGE)
        print(f'COMPARISON_PREP_STAGE={stage} ERROR_KIND={kind} SOURCE_ID={source} LINE={line}', file=sys.stderr)
        raise SystemExit(1)
