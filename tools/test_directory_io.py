#!/usr/bin/env python3
"""Native directory I/O gates; portable success is NOT Windows acceptance.

Windows invocation requires a production DLL, a RU_DIR_TESTING fault DLL,
Windows host, symlink permission (Developer Mode or elevation), and ~280 MiB
free local disk. Missing prerequisites FAIL rather than silently skip gates.
Test-DLL fault modes model remote mapping, offline/recall attribute races,
blocked read cancellation, and NT reparse denial. They do not claim testing a
real cloud provider, remote filesystem, or indefinitely blocked kernel driver.
"""
import argparse
import csv
import ctypes
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import shutil
from types import SimpleNamespace
import time

ROOT = Path(__file__).resolve().parents[1]

def run(*args):
    subprocess.run([str(a) for a in args], check=True)

def portable():
    with tempfile.TemporaryDirectory(prefix="ru-dir-test-") as tmp:
        exe = Path(tmp) / ("host.exe" if os.name == "nt" else "host")
        run(os.environ.get("CC", "cc"), "-std=c11", "-Wall", "-Wextra", "-Werror", "-DRU_DIR_PORTABLE_TEST", ROOT / "tests/directory_io_host.c", "-o", exe)
        run(exe)

def require(condition, description):
    if not condition:
        raise AssertionError(description)

def windows(args):
    if os.name != "nt":
        raise SystemExit("FAIL: --windows requires real Windows; portable/Wine is not acceptance")
    if not all((args.dll, args.host, args.fault_dll)):
        raise SystemExit("FAIL: --windows needs --dll, --host and --fault-dll (RU_DIR_TESTING build)")
    dll, host, fault = (Path(p).resolve() for p in (args.dll, args.host, args.fault_dll))
    coverage = []
    evidence = getattr(args, "evidence", {"status": "running", "cases": [], "invocations": []})
    def command(*items, check=True, timeout=90):
        cmd = [str(item) for item in items]
        try:
            result = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired as error:
            evidence["invocations"].append({"argv": cmd, "returncode": None, "status": "timeout", "stdout": str(error.stdout or ""), "stderr": str(error.stderr or "")})
            raise
        evidence["invocations"].append({"argv": cmd, "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
        if check and result.returncode:
            raise RuntimeError(f"Command failed: {cmd!r}\n{result.stdout}\n{result.stderr}")
        return result
    def passed(case_id):
        evidence["cases"].append({"id": case_id, "status": "pass"})
    def scan(path, mode="scan", library=dll, fault_mode=None):
        cmd = [host, library, path, mode]
        if fault_mode is not None:
            cmd.append(str(fault_mode))
        output = command(*cmd).stdout
        print(output.strip())
        return json.loads(output.splitlines()[-1]) if mode in ("scan", "safe", "links", "reject", "positive-outside") else None
    with tempfile.TemporaryDirectory(prefix="ru-directory-io-") as tmp:
        root = Path(tmp).resolve()
        safe = root / "safe"
        safe.mkdir()
        (safe / "empty.txt").write_bytes(b"")
        (safe / "payload.txt").write_bytes(b"abcdef" * 20000)
        (safe / "中文-😀.txt").write_bytes(b"\xff\xfe" + "Unicode 目录".encode("utf-16le"))
        (safe / "binary.bin").write_bytes(bytes(range(256)) * 20)
        result = scan(safe, "safe")
        require(result["ends"] == 4 and result["files"] == 4, "regular/empty/Unicode-path/binary opaque transport")
        passed("regular-empty-unicode-binary")
        coverage.append("real OS regular/empty/UTF16 filename and byte-for-byte binary/Unicode transport against independent fixture reads")
        scan(safe, "abandon-once", fault, 6)
        for mode in ("cancel", "rapid", "unload"):
            scan(safe, mode)
            passed({"cancel": "queue-full-cancel-abandon", "rapid": "rapid-retirement-generations", "unload": "active-module-unload"}[mode])
        coverage.append("real OS full queue, 100 rapid cancel/release/restart cycles, stale generations, abandon, active caller DLL unload/reload")
        for mode in (1, 2, 3, 5):
            result = scan(safe, "reject", fault, mode)
            require(result["reads"] == 0 and result["starts"] == 0, f"fault {mode} must not read payload")
            passed({1: "fault-remote-drive", 2: "fault-offline", 3: "fault-recall", 5: "fault-reparse-open-race"}[mode])
        scan(safe, "cancel", fault, 4)
        passed("fault-blocked-read-cancel")
        scan(safe, "safe", fault, 0)
        passed("fault-wrapper-production-flags")
        coverage.append("test-build call substitutions: remote drive, offline/recall attribute rejection, NT reparse race denial, controlled stalled ReadFile cancellation; same production guards and ownership")
        outside = root / "outside"
        outside.mkdir()
        (outside / "secret.txt").write_bytes(b"OUTSIDE_ROOT_MUST_NOT_READ" * 100)
        (outside / "nested").mkdir()
        (outside / "nested" / "secret.txt").write_bytes(b"OUTSIDE_ROOT_MUST_NOT_READ" * 100)
        scan(outside / "nested", "positive-outside")
        os.symlink(outside, safe / "symlink", target_is_directory=True)
        command("cmd", "/c", "mklink", "/J", safe / "junction", outside)
        try:
            scan(safe, "links")
            for path in (safe / "symlink", safe / "junction", safe / "junction" / "nested"):
                scan(path, "reject")
        finally:
            os.rmdir(safe / "junction")
            os.rmdir(safe / "symlink")
        passed("symlink-junction-ancestors")
        coverage.append("real OS symlink, junction, and ancestor-junction rejection; forbidden outside payload asserted by host")
        letter = next((f"{c}:" for c in "ZYXWVUTSRQPONMLKJIHGFED" if not Path(f"{c}:\\").exists()), None)
        require(letter, "unused drive letter required for SUBST gate")
        command("subst", letter, safe)
        try:
            scan(letter + "\\", "reject")
        finally:
            command("subst", letter, "/D")
        # Device/UNC/ADS are syntax rejects, tested through production start.
        for invalid in (r"\\.\C:\safe", r"\\?\C:\safe", r"\\server\share", str(safe) + ":stream"):
            completed = command(host, dll, invalid, "reject", check=False)
            require(completed.returncode != 0 and "==RU_DIR_OK" in completed.stderr, "unsafe syntax must reject at start")
        passed("subst-device-unc-ads")
        coverage.append("real OS SUBST rejection; production API device/UNC/ADS syntax rejection")
        # Ordinary writable handle must exclude file access through sharing.
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateFileW.restype = ctypes.c_void_p
        kernel.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        target = safe / "payload.txt"
        handle = kernel.CreateFileW(str(target), 0x40000000, 7, None, 3, 0, None)
        require(handle not in (None, ctypes.c_void_p(-1).value), "create conflicting writer handle")
        try:
            require(scan(safe)["reasons"][3] >= 1, "ordinary writable handle excluded")
        finally:
            kernel.CloseHandle(handle)
        sid = next(csv.reader([command("whoami", "/user", "/fo", "csv", "/nh").stdout.strip()]))[1]
        command("icacls", target, "/deny", f"*{sid}:(R)")
        try:
            require(scan(safe)["reasons"][3] >= 1, "ACL denied file excluded")
        finally:
            command("icacls", target, "/remove:d", f"*{sid}")
        passed("acl-writer-sharing")
        coverage.append("real OS denied ACL and ordinary-writer sharing exclusion")
        # Concurrent ancestor substitutions: successful swaps before pinned
        # opens; blocked renames while pinned are expected safety behavior.
        raced = root / "race-root"
        raced.mkdir()
        branch, moved = raced / "branch", raced / "moved"
        branch.mkdir()
        (branch / "normal.txt").write_bytes(b"normal" * 10000)
        stop = threading.Event()
        counts = [0]
        def swap():
            while not stop.is_set():
                try:
                    branch.rename(moved)
                    try:
                        os.symlink(outside, branch, target_is_directory=True)
                        counts[0] += 1
                        time.sleep(0.001)
                    finally:
                        if branch.is_symlink():
                            os.rmdir(branch)
                        moved.rename(branch)
                except OSError:
                    time.sleep(0.001)
        thread = threading.Thread(target=swap)
        thread.start()
        try:
            for _ in range(20):
                scan(raced)
        finally:
            stop.set()
            thread.join(timeout=10)
        require(not thread.is_alive() and counts[0] > 0, "actual ancestor substitutions must occur")
        passed("concurrent-ancestor-substitution")
        coverage.append(f"real OS concurrent ancestor rename/symlink substitutions ({counts[0]} successful swaps); forbidden outside bytes never transported")
        deep = root / "deep"
        deep.mkdir()
        cursor = deep
        for _ in range(34):
            cursor = cursor / "d"
            cursor.mkdir()
        result = scan(deep)
        require(result["reasons"][8] > 0, "depth32 exclusion visible")
        passed("depth32")
        long_root = root / "long"
        long_root.mkdir()
        cursor = Path("\\\\?\\" + str(long_root))
        for i in range(5):
            cursor = cursor / (chr(97 + i) * 240)
            cursor.mkdir()
        require(scan(long_root)["reasons"][1] > 0, "1023-unit assembled path exclusion visible")
        passed("path1023")
        shutil.rmtree(Path("\\\\?\\" + str(long_root)))
        many_dirs = root / "dirs"
        many_dirs.mkdir()
        for i in range(2001):
            (many_dirs / str(i)).mkdir()
        result = scan(many_dirs)
        require(result["dirs"] == 2000 and result["status"] == 7, "directory budget includes skipped entries/root")
        passed("directories2000")
        many_files = root / "files"
        many_files.mkdir()
        for i in range(10001):
            (many_files / str(i)).touch()
        result = scan(many_files)
        require(result["files"] == 10000 and result["status"] == 6, "file budget bound")
        passed("files10000")
        sizes = root / "sizes"
        sizes.mkdir()
        with (sizes / "oversize").open("wb") as file:
            file.truncate(8388609)
        result = scan(sizes)
        require(result["starts"] == 0 and result["reasons"][5] == 1 and result["reads"] == 0, "8MiB pre-read exclusion")
        passed("file8mib")
        budget = root / "budget"
        budget.mkdir()
        chunk = b"x" * 1048576
        for i in range(33):
            with (budget / f"{i:02}.txt").open("wb") as file:
                for _ in range(8):
                    file.write(chunk)
        result = scan(budget)
        require(result["reads"] == 268435456 and result["status"] == 9 and result["ends"] == 31 and result["starts"] == 32, "actual read budget: exact exhaustion cannot emit unverified END")
        passed("read256mib-eof-discard")
        coverage.append("real OS recursive/depth32/path1023/dirs2000/files10000/file8MiB/read256MiB bounds, verified EOF and conservative final-file discard")
    evidence.update({"status": "pass", "coverage": coverage, "limitations": ["Controlled read stall is not a real kernel/device hang.", "Remote/offline/recall tests inject OS-call outcomes; no real cloud hydration or network provider is exercised.", "Ancestor swaps exercise concurrent races but do not claim exhaustive scheduling or mapped-writer snapshot immutability."]})
    require({case["id"] for case in evidence["cases"]} == set(REQUIRED_CASE_IDS), "required case evidence must be complete")
    return evidence


REQUIRED_CASE_IDS = (
    "regular-empty-unicode-binary", "queue-full-cancel-abandon", "rapid-retirement-generations", "active-module-unload",
    "fault-remote-drive", "fault-offline", "fault-recall", "fault-reparse-open-race", "fault-blocked-read-cancel", "fault-wrapper-production-flags",
    "symlink-junction-ancestors", "subst-device-unc-ads", "acl-writer-sharing", "concurrent-ancestor-substitution", "depth32", "path1023",
    "directories2000", "files10000", "file8mib", "read256mib-eof-discard",
)

def run_windows(dll, host, fault_dll, output=None):
    """Return structured evidence; optional JSON output is written on failure too.

    Production DLL must be the actual staged RuSyntax.dll. fault_dll is built
    from the same native source with RU_DIR_TESTING, never shipped.
    """
    evidence = {"status": "running", "required_case_ids": list(REQUIRED_CASE_IDS), "cases": [], "invocations": [], "skipped": []}
    args = SimpleNamespace(dll=dll, host=host, fault_dll=fault_dll, evidence=evidence)
    try:
        windows(args)
    except BaseException as error:
        evidence["status"] = "fail"
        evidence["error"] = str(error)
    if output:
        Path(output).write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    return evidence

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--windows", action="store_true")
    parser.add_argument("--dll")
    parser.add_argument("--host")
    parser.add_argument("--fault-dll")
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.windows:
        evidence = run_windows(args.dll, args.host, args.fault_dll, args.output)
        print(json.dumps(evidence, indent=2))
        if evidence["status"] != "pass":
            raise SystemExit(1)
    else:
        portable()

if __name__ == "__main__":
    main()
