# Diagnostic launcher checks

Run from the repository root after sourcing `.tools/env.sh`:

```
python3 tests/diagnostic_launcher_tests.py
```

This executes portable C path/failure-display policy tests on the actual host,
checks narrowly forbidden log-creation APIs, and cross-builds four GUI fixtures
with the installed official MinGW compiler and real Windows headers. It does not
fake `_WIN32`, execute Windows binaries, invoke Wine, or prove Windows behavior.
The native-Windows acceptance test is explicitly reported as skipped/unrun.

## Native Windows acceptance, still unrun

On a native Windows test machine, build `windows_fixture.c` in each mode using
`-DFIXTURE_MODE=0`, `1`, `2`, or `3`, `-mwindows`, `-lshell32`, and `-luser32`. Modes 0–2
respectively return 0, return 7, and call `exit(23)`; mode 3 creates a
synthetic native window before `exit(23)`. They write only fixed
synthetic stdout/stderr markers. Do not run modes 1–3 unattended: their expected
error message boxes must be dismissed manually.

Check all of these before claiming runtime acceptance:

- Explorer double-click, without an attached console: mode 0 creates one new
  `ru_notepad-*.log`, containing startup, both fixture markers, and status 0.
  There is no error dialog. A normal nonzero return has its status in the log
  and shows the log-location dialog. Fatal `exit(23)` logs the early exit and
  shows the same dialog. Return/exit codes remain 0, 7, and 23 respectively.
- Launch from a console too. This GUI launcher intentionally redirects its
  stdout/stderr into the new log; it does not promise console mirroring.
- Rerun/concurrently launch multiple instances. Existing logs must retain their
  original bytes; every new instance must own a distinct CREATE_NEW file.
- Use copied fixture executables under paths with spaces and non-ASCII text.
  Verify log paths display correctly, including in the modal error dialog.
- With an unwritable executable directory, the existing per-user
  LocalAppData/Temp directory receives the new log. TMP/TEMP environment changes
  must not change this fallback. No directory is created by the launcher.
- With both eligible directories unwritable or unavailable, startup stops with
  a visible error and debug output. The stub does not run. Never use real
  document directories when testing permissions.
- Test fallback directory reparse points, a network executable location, and
  drive/path failures in disposable fixtures. Reparse/network candidates must
  not be used as log destinations. A preexisting filename, including a reparse
  entry, must never be opened, followed, overwritten, truncated, or deleted.
- Exercise low-disk/write/redirect failure through an appropriate disposable
  Windows test environment. Diagnostic setup failures must remain visible;
  an incomplete log must not be presented as fully written.

The launcher does not recover from arbitrary native crashes or forced process
termination. It installs an `atexit` handler, not an exception handler. It never
saves documents. The fatal message warns that a Save in progress may already have
changed the target file. Logs inherit their containing directory's permissions;
there is no claim that logs beside an executable are confidential. Runtime
stdout/stderr is captured without filtering, so inspect logs before sharing.
