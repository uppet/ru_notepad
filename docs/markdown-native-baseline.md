# Bounded Windows native Markdown baseline

This is a research-only C host for the existing offline-built Scintilla 5.6.7 and
Lexilla 5.5.4 DLLs. It is not a replacement implementation of Markdown policy,
application acceptance, or a user-runtime executable. Its source is deliberately
under `benchmarks/`, outside `native/` and the product helper source snapshot.
The EXE, temporary input and raw build/process logs must not enter runtime or test
ZIPs. The runner creates those files in a unique private OS temporary directory,
not the public evidence directory, and removes them on exit.

## Run contract

From the same Windows job and built product checkout:

```
python tools/test_markdown_native_baseline.py
python tools/run_markdown_native_baseline.py --cc C:\msys64\mingw64\bin\gcc.exe --runtime-dir build\ci\bin --output build\ci\evidence\markdown-native-baseline.json
```

The report must be new. The runner never overwrites an existing report. It
reserves the report using exclusive creation and retains that owned descriptor.
An error produces a small failed report with a fixed error code, not success
statistics. A collector can import `validate_summary` to reject a malformed or
incomplete successful report. Do not weaken the original product's 30-second
Markdown budget or its three-corpus checks because of this separate experiment.
The pipeline runs irrespective of whether this research passes or fails, as
arranged by the separate CI coordinator.

No downloads, source replacement, Ru compiler build, Ru execution, generated-C
instrumentation, direct-function ABI, application file-drop subclass, or remote
operation is performed by this runner.

## Fixed corpus and dependencies

The corpus is extracted from `gui_markdown_fixture('unclosed-fence')` in the
current `tools/windows_ci.py`, without importing that module. It must also match
an independently constructed literal corpus byte for byte:

- 1,000,000 bytes, 100,000 LF characters, 100,001 document lines
- SHA-256 `2d9f79ee715b217c00792cf18a67485cdec96a14ea2ac86689156941a022c719`
- `# Heading\n\n~~~\n`, followed by 999,977 bytes of repeated `code text\n`, then
  `codebody`

The runner compares the installed product DLLs in `--runtime-dir` with the
current vendor build outputs, copies those exact bytes, and verifies their
hashes before and after execution. DLLs are loaded by absolute executable-local
paths using `LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_SYSTEM32`.
The two offline archive hashes are fixed. The two C ABI headers are checked
against the corresponding members of the verified Scintilla ZIP. The report
records compiler executable, native source, runner, corpus-source, headers, DLL,
archive and resulting EXE hashes and the exact fixed compiler flags. This is
same-run byte identity with the installed product DLLs, not a universal DLL hash
across toolchain builds.

## Three fresh processes and three fresh editors per process

Each of the three processes performs the following fixed-order measurements;
none reuses another component's editor or document:

1. **`colourise`**: setup, insertion and default-fold checks occur first on a
   hidden fresh editor. The only timed operation is one ordinary same-thread
   `SendMessageW(SCI_COLOURISE, 0, -1)`. No fold writes occur. Every line's fold
   level must remain its untouched default 1024. No preceding paint or lazy
   styling is allowed: `endStyled` must be zero immediately after insertion.
2. **`fold_writes`**: a different hidden fresh editor is loaded and fully styled
   outside the timer. Every initial fold level is rechecked as 1024 after styling.
   The timer contains exactly 100,001 ordinary `SCI_SETFOLDLEVEL` sends: line 0
   receives 9216 (`1024 | HEADERFLAG`), each other line receives 1025. These are
   predetermined final levels for this one corpus. This does not parse Markdown,
   emulate policy scheduling, or replay the production policy's 100,002 ordered
   assignments (which include a preliminary nonheader write to line 0).
3. **`read_to_paint`**: the timer starts before opening and reading the input
   file. It includes creation of a new parent window, editor and 64-bit-position
   document; native presentation/lexer setup; text insertion and clean-savepoint,
   undo and selection setup; one full explicit colourise; all 100,001 final fold
   writes; showing the window; and explicit full-client painting with GDI flush.
   Separate contiguous QPC tick segments report read, create/setup, load, style,
   fold, and show/paint work. Their sum must equal the total interval exactly.

All three component timers exclude process startup, DLL loading, window-class
registration, complete-content validation and teardown. Pipeline setup contains
small API/precondition checks as well as creation; it is not a bare allocation
microbenchmark. Pipeline segment QPC calls and painting observation overhead are
included. The pure style/fold timings include native message dispatch but no Ru
callback or foreign-function wrapper.

The fixed order, earlier component reads and Python's fixture creation leave the
filesystem and DLL/code caches warm or unspecified. There is no cache flush and
no claim of cold-disk or cold-process-start latency. No earlier Linux timings,
old acceptance runs or thresholds are imported as a current Windows pass.

## Explicit native first-client-paint boundary

The presentation is a 960 × 640 client, 96 DPI, requested `Consolas` 11-point font,
no wrap, GDI rendering, no scrollbars, a 56-pixel number margin and 20-pixel fold
margin. The font name/size, wrap, scrollbar, renderer and DPI settings are read
back; this does not prove a particular font binary or prohibit Windows font
substitution. A non-96-DPI environment fails rather than silently changing the
measurement.

The pipeline remains hidden until style and folds are complete. A minimal native
C window-procedure observer measures a real `WM_PAINT` entrance. Its update region
must equal the whole client region. After forwarding to the original Scintilla
window procedure, `UpdateWindow` and `GdiFlush` must return; there must have been
exactly one full client paint, and no update region may remain. These checks are
not a screenshot, desktop-compositor completion, monitor scanout or painting of
all 100,001 document lines. They demonstrate completion of the explicitly forced
visible-client paint in this host. They do not measure natural app paint latency
or user input responsiveness. The hidden style/fold components do not install
this observer.

## Exact verification outside all measurement intervals

Every component reads back all 1,000,000 text/style byte pairs using
`SCI_GETSTYLEDTEXTFULL`. Text bytes are compared individually with the fixed
literal corpus. Style bytes are independently expected as:

- offset 0: style 6
- offsets 1–8: style 0
- offsets 9 and 10: style 1 (the two LF characters)
- every offset from 11 through 999,999: style 21

Every one of the 100,001 fold levels is compared with its expected value. Each
line must also be visible and expanded. The FNV-1a hashes are summaries after
these comparisons, not the only correctness test:

- all styles: `f3e8304ab5c43d36`
- untouched default folds, serialized as little-endian unsigned 32-bit values:
  `08c4ea94396a8f49`
- predetermined final folds, same serialization: `14a0b025819607a9`

All components must end fully styled, clean, with anchor 2/caret 19, empty undo
and redo stacks, enabled undo collection, exact text/line counts and no Scintilla
error. These demonstrate the bounded native state only. They do not establish
semantic equivalence to the full application, its policy lifecycle, event
routing, dirty-tab model, undo after edits, cancellation, or mixed-language UI.

## Limits and failure behavior

- Exactly three fresh successful process records are required before computing
  min/median/max and the three raw sample timings for each component.
- Build: at most 60 seconds. Each process, including all three components and
  validation: at most 15 seconds. Runner: 120 seconds total. Cleanup has bounded
  waits (at most five seconds for process exit and five for job accounting) and
  must be confirmed. A failed run never gains success statistics.
- A process starts suspended, is assigned to a private kill-on-close Windows Job
  Object, then resumes. Assignment/resume failures terminate the still-owned
  process. The job owns all compiler descendants, allows at most 16 simultaneous
  processes, and has a 512 MiB job-memory limit. Only explicit stdin/stdout/stderr
  handles are inherited. All exit paths close the job, including failed queries.
- Per-stream output is monitored at 16 KiB; reads are also capped after exit.
  Raw errors and compiler logs remain private and temporary. Public diagnostics
  contain fixed codes and hashes, never arbitrary exceptions, paths or file text.
- Existing path components must be ordinary directories, inputs ordinary
  single-link files; symlinks/reparse points, traversal and unexpected identities
  fail closed. The explicitly supplied trusted compiler alone may have official
  hardlink aliases; its bytes are still checked before/after, and symlinks/reparse
  points remain rejected. This is a disposable CI workspace contract, not a claim of a
  sandbox against a privileged concurrent filesystem attacker.
- QPC frequency, every positive interval, segment sums, chronological order,
  whole-process measured span and the process-wall-time bounds are validated.
  Missing/extra/duplicate JSON fields, wrong numeric types, nonfinite numbers,
  wrong proofs, missing repetitions and altered statistics are rejected.

## Verification status before Windows CI

Linux host controls test the exact corpus/oracles, strict schemas, invalid QPC
values, incomplete runs, changed identities, path/link/output safety, and
sanitized failure reports. Windows-only controls separately exercise process
success, output/timeout cleanup and suspended-assignment failure. Those controls
are skipped on non-Windows hosts. A successful cross-build proves C compilation
and PE format only. Real DLL loading, Job Object controls and all three native
Windows measurements remain unverified until the same Windows CI job executes
them and validates the complete report.
