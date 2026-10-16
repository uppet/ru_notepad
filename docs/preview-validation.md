# Preview validation

Date: 2026-10-16 UTC. These are unsigned Windows x64 previews. Build/source checks and actual Windows acceptance are recorded separately.

## Released 0.1.1 evidence

[Windows run 38863597991](https://github.com/uppet/ru_notepad/actions/runs/38863597991), public commit `d8d678206787c924141449e339cee9ebff54fc79`, passed **277 native assertions**: document policy 23, UI arguments 19, file-attribute flags 80, editor 27, application lifecycle 23, file codec 77, and synthetic NTFS ACL fixtures 28. No required tests were skipped. A separate detached GUI smoke test observed a visible main HWND owned by the launched process, checked responsiveness, sent WM_CLOSE and obtained normal exit 0 without cleanup termination.

That run produced the 0.1.1 ZIP only after all required gates passed. CRC, full SHA-256 inventory, source/build receipts and dependency license checks were verified. These results establish those exact synthetic cases, not universal filesystem safety or complete interactive acceptance.

Earlier failures are retained rather than counted as passes: the 0.1.0 native menu argument grouping caused startup exit; the second 0.1.1 CI run exposed five mis-grouped attribute comparisons. The latter could report failure after creating a new destination file. The fixes and their exact malformed-expression regressions are documented in `startup-fix-0.1.1.md` and `file_codec_validation.md`.

## 0.1.2 acceptance gates

The first [0.1.2 Windows run 38868967636](https://github.com/uppet/ru_notepad/actions/runs/38868967636) built all executables and passed the original 277 assertions, the new shortcut34/status21 groups, and real GUI startup/normal close. Four syntax-related groups failed because the string-only `含` operation was applied to arrays in suffix selection and test argument handling. No ZIP was produced. The corrected implementation uses an explicit array-equality loop in a shared pure policy, executed directly by 100 portable cases; the original invalid API usage is retained as an expected-failure fixture in both runtimes.

The corrected [0.1.2 Windows run 38871195015](https://github.com/uppet/ru_notepad/actions/runs/38871195015), commit 4b2be1a6a79f1df80156c2bcae89f0b08d2adce1, passed all 553 assertions and the detached GUI test. Both original CI ZIPs were independently verified; shared runtime files were byte-identical and matched the executed binaries.

Required acceptance retains every 0.1.1 assertion and adds:

- 100 production syntax-policy cases covering suffixes, language labels and exact argument-array matching, plus 34 shared shortcut-policy cases, also executable in the Ru interpreter and Linux native C.
- 21 real Scintilla status cases: mixed CRLF/LF/CR, final unterminated lines, insertion mode, tab/Han/emoji/combining-codepoint columns, unchanged text and savepoint.
- 23 main-level feature cases through real WM_COMMAND callback dispatch: tab navigation, zoom, language selection, independent documents, unchanged dirty/undo state and normal close.
- 82 real Lexilla C/C++ and JSON cases, plus two isolated startup fallback cases with 8 assertions each for missing DLL and missing CreateLexer export.

The total is **553 assertions across 14 required assertion results**, plus the separate visible-GUI/normal-close result. CI rejects missing results, skipped tests, inconsistent PASS-line totals, nonzero exits and timeouts. The actual Windows result and exact binary/source hashes are recorded in each successful package's BUILD.json; consult that receipt rather than treating this planned gate as a pass.

## Released 0.1.3 evidence

The [first 0.1.3 Windows run](https://github.com/uppet/ru_notepad/actions/runs/38881489424) executed 797 assertions and passed 22 of 23 results, including both detached GUI gates and the complete 500,039,680-byte editor roundtrip. It did **not** qualify for packaging: the 38-assertion file-drop fixture failed before its first assertion because its console executable lacked the Common Controls v6 manifest required by GetWindowSubclass. Console tests now embed the application's same reviewed manifest while retaining their console subsystem. The corrected [Windows run 38887294845](https://github.com/uppet/ru_notepad/actions/runs/38887294845), commit `6c67574a164a26e0629cc5e4e707351ec0059b71`, passed all **835 assertions / 23 results**, including the full 500,039,680-byte roundtrip in 18.844 seconds. Both original CI ZIPs were independently verified against the executed binaries.

New native gates cover strict UTF-8/UTF-16/legacy boundaries, staged-write cancellation and ACL preservation, actual files beyond 4 MiB/16 MiB, zero-read cancellation above 500 MB, and a complete 500,039,680-byte valid-text editor load/save with independent full-output validation. Main-level tests exercise real timer dispatch, Unicode CLI/drop input, duplicate hard-link identity, per-file queue errors, preserved dirty state, same-length revision changes, Save As cancellation during close-all, and normal async-save close continuations.

Registration tests operate only inside a disposable HKCU test namespace; they do not choose defaults. HDROP tests cover bounded Unicode path ownership and malformed data. A separate detached GUI gate must inject file drops through the actual visible Scintilla child (rather than only the parent), observe exact opened text, responsiveness during a partial load, cancellation without a partial tab or remaining queue, and normal WM_CLOSE/exit0. Large generated fixtures are deleted and never uploaded; only bounded synthetic logs, hashes and counts are artifacts. The required total is 835 individual assertions across 21 assertion results, plus two detached GUI results (23 required results). The successful run above establishes these exact synthetic cases, not every filesystem or interactive path.

## 0.1.4 Ru syntax gates (pending)

The first [0.1.4 run 38927433174](https://github.com/uppet/ru_notepad/actions/runs/38927433174)
passed the full Linux oracle/sanitizer job, including LeakSanitizer, but failed
Windows acceptance: 1,261 assertion lines and 29 of 31 results passed. The native
container fixture stopped after its first assertion because a rescue-local
scalar flag did not update its outer binding. The 1 MB detached GUI reached its
head-token styles in 156 ms and had a measured maximum WM_NULL response of
47 ms, but did **not** meet the unchanged 30-second complete-styling deadline;
the six subsequent editing measurements did not run. These partial metrics are
not a completed performance result, and no ZIP was produced.

The [scope-repair run 38934373024](https://github.com/uppet/ru_notepad/actions/runs/38934373024)
passed all 1,379 individual native assertions, including all 119 container
cases, and 30 of 31 results. The production initialization recovery and cleanup
controls also passed both portable backends. GUI styling still failed: after
30 seconds the 1 MB document was clean but only its first 470,180 bytes were
styled; tail probes were false and status remained `Styling Ru`. First-token
styles took 172 ms and maximum measured WM_NULL response was 47 ms. The core's
different, 200,000-line ASCII corpus completed synchronously in 20.22 seconds;
these different workloads do not establish the GUI's CPU or scheduling cost.
No ZIP was produced.

The [notification-filter run 38940854329](https://github.com/uppet/ru_notepad/actions/runs/38940854329)
passed 1,393 individual assertions and 30 of 32 results. The exact Chinese GUI
corpus completed synchronously in 9.967 seconds. The main-window timer recorded
12.005 seconds of work and 17.844 seconds between callbacks before its unchanged
30-second deadline, with 850,358 bytes processed. Actual style/fold notifications
were zero under the text-only subscription. The detached GUI reached 947,418
bytes, with first-token styles at 141 ms and maximum measured WM_NULL response
16 ms, but its tail remained unstyled. Its six editing measurements again did
not run. The timer's eight post-completion assertions did not execute. No ZIP
was produced; the faster partial progress is not a completed acceptance result.

The [cooperative-scheduler run 38946131401](https://github.com/uppet/ru_notepad/actions/runs/38946131401)
passed 1,417 assertions and 30 of 32 results. The same 1 MB corpus completed on
the main-window scheduler in 19.754 seconds, with 19.116 seconds of measured
work and 0.477 seconds between callbacks. The synchronous control took 14.215
seconds on that run. However, the detached GUI still timed out at 646,656 styled
bytes after 30 seconds. Head-token styles were first observed at 203 ms; queued navigation,
natural paint, and measured WM_NULL responses remained responsive. The six edit
measurements did not run. The normal application fixture passed 63 assertions
then rejected a setup state in which newly pending UI work could legitimately
defer posting. No ZIP was produced.

The next revision makes that fixture setup retry within a fixed bound while
still requiring a real queued continuation before close. It also bounds the
GUI observer: full completion snapshots are spaced by at least 250 ms and
WM_NULL probes by at least 50 ms, with actual synchronous message counts and
observer time recorded. Frequent synchronous inspection can itself affect the
scheduler's sent-message priority; this remains a hypothesis to measure, not a
claimed explanation or performance fix. At most three explicit diagnostic
requests project fixed numeric work/progress counters to the existing launcher
log, without scanning or reading document text. Ordinary projection failure
prints only a fixed failed-result marker. The complete final snapshot, all six
edits, real navigation/paint checks, and 30-second gate remain mandatory.

The text-only subscription, full-notification core control, single coalesced
continuation slot, timer fallback and 8 ms work budget remain unchanged. Both
actual corpus builders must still match the complete original UTF-8 bytes in
both portable backends. Portable diagnostic controls check fixed output,
privacy, failure recovery and request caps separately from native message proof.

This revision retains every 0.1.3 assertion and adds 8 shortcut and 8 suffix-policy
cases, 338 production lexer/fold-policy cases, 125 real Scintilla container cases,
73 main-window integration cases, 8 separate main-timer measurement cases,
and an isolated 8-case Ru run without Lexilla, and three 8-case helper rejection runs
for missing DLL, missing exports and ABI mismatch.
The required total is **1,427 individual assertions / 32 results**, including
three detached GUI results. The existing complete >500 MB roundtrip is retained.

New native gates check actual UTF-8 style bytes and fold levels, incomplete edits,
checkpoint convergence, 100 KB / 1 MB scanned-byte and timing diagnostics,
text/dirty/undo preservation, document generations, language-switch visibility,
main timer ownership, margin hit-testing, menu commands, tab state, and automatic
Ru selection after Save As. Portable tests run the pure Ru lexical/fold policy in both the pinned interpreter
and Linux C. The C scanner is compared against that oracle, and the exact Windows
DLL must pass the locked corpus/fuzz chunk configurations before native
acceptance. A required Linux job separately runs the full style/fold oracle
differential and ASan/UBSan checks; Windows packaging depends on its success. None of these portable checks replaces the Windows UI gates.

The detached Ru GUI gate additionally loads a 1,000,000-byte synthetic Chinese
Ru source through the actual child drop/timer path. It verifies byte length,
clean state, known head/tail style bytes and completed status while probing
WM_NULL responsiveness; completion must occur within 30 seconds. While styling
is still pending, queued Right/Left navigation must move and restore the caret
without changing text, and a real invalidation must naturally drain through
paint handling. Cross-thread paint sampling records whether the invalid region
was still pending at the first poll rather than treating an already completed
paint as failure. Its wall time
and maximum measured response time are retained independently of synchronous
scanner timings. A separate approximately 100 KB source exercises real insertion
and Backspace at the beginning, middle and end, with each response/completion
time recorded and final style/fold probes checked. Native cases compare all
text/style bytes and fold levels against fresh scans after unequal-length edits
and edits made while earlier work is pending. Passing a finite timing-value check alone is not a usability
claim. No 0.1.4 Windows pass is claimed until the exact-commit CI run succeeds.

## Packaging

The ordinary runtime ZIP contains the application, Scintilla.dll, Lexilla.dll, RuSyntax.dll and necessary docs/licenses/samples. The separate tests ZIP is self-contained, includes byte-identical copies of those runtime files, and adds test executables, the test runner and bounded synthetic CI evidence. Both packages are made from the binaries that passed acceptance, without a rebuild between tests and packaging. Full inventory/hash and dependency-source/license gates apply to both.

## Source and build checks

- Pinned Ru native-C static checks and app-specific native argument audit, including conditional optional-library bindings and malformed-expression mutants.
- Shared document, UI-argument, flags and shortcut policies executed in both the interpreter and Linux native C.
- MinGW Windows x64 PE compilation, embedded original icon/manifest, pinned source-built Scintilla 5.6.7 and Lexilla 5.5.4, and system-only static import inspection.
- Independent source review of NUL/byte-count/UTF-8 guards, Scintilla status handling, grouped-undo cleanup, child-window rollback, canonical paths, file-dialog buffer ownership, orderly-shutdown veto, fatal-warning behavior and staged-save ownership.
- Launcher policy/source checks and four cross-built Win32 diagnostic fixtures. Detached GUI startup/logging/normal exit has real Windows coverage; failure-dialog, collision, fallback and reparse diagnostic fixtures still require dedicated execution.

## Remaining manual acceptance and limits

Physical Explorer mouse dragging, keyboard layouts, IME composition, clipboard integration, file dialogs and dirty prompts require interactive acceptance. Editor child routing revokes Scintilla's OLE text target; external text drops and internal selection drag-to-move are unavailable in this version. Further coverage is needed for shutdown veto, real-world ACL/EFS configurations, replacement/backup failures, fault injection, accessibility and rendering at different display scales. Local Wine never ran; it is not claimed as evidence.

No crash recovery exists. Use samples or copies first. The fixed 4 MiB limit is removed in 0.1.3; NUL rejection remains. Scintilla keeps the entire text in memory, and bounded streaming does not promise unlimited size. At 32,000,000 bytes, opening uses labelled plain-text/no-wrap mode; above 500,000,000 bytes, consent precedes any body read. Cancel is between I/O chunks, not during one synchronous disk call. Replace-all and very long-line rendering can still block. Ru files were plain text in 0.1.3; 0.1.4 adds dedicated Ru highlighting and structural folding below the large-file threshold. Save All, recent files, backward/whole-word/selection-scope search, explicit EOL conversion, tab reordering and localization are absent. Plugins, macros, sessions and full Notepad++ parity remain future work.
