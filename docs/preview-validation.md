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

## 0.1.3 acceptance gates (pending)

The [first 0.1.3 Windows run](https://github.com/uppet/ru_notepad/actions/runs/38881489424) executed 797 assertions and passed 22 of 23 results, including both detached GUI gates and the complete 500,039,680-byte editor roundtrip. It did **not** qualify for packaging: the 38-assertion file-drop fixture failed before its first assertion because its console executable lacked the Common Controls v6 manifest required by GetWindowSubclass. Console tests now embed the application's same reviewed manifest while retaining their console subsystem; all 835 assertions and 23 results must pass together on the corrected build.

New native gates cover strict UTF-8/UTF-16/legacy boundaries, staged-write cancellation and ACL preservation, actual files beyond 4 MiB/16 MiB, zero-read cancellation above 500 MB, and a complete 500,039,680-byte valid-text editor load/save with independent full-output validation. Main-level tests exercise real timer dispatch, Unicode CLI/drop input, duplicate hard-link identity, per-file queue errors, preserved dirty state, same-length revision changes, Save As cancellation during close-all, and normal async-save close continuations.

Registration tests operate only inside a disposable HKCU test namespace; they do not choose defaults. HDROP tests cover bounded Unicode path ownership and malformed data. A separate detached GUI gate must inject file drops through the actual visible Scintilla child (rather than only the parent), observe exact opened text, responsiveness during a partial load, cancellation without a partial tab or remaining queue, and normal WM_CLOSE/exit0. Large generated fixtures are deleted and never uploaded; only bounded synthetic logs, hashes and counts are artifacts. The required total is 835 individual assertions across 21 assertion results, plus two detached GUI results (23 required results). This is a required gate, not an unexecuted claim of success.

## Packaging

The ordinary runtime ZIP contains the application, Scintilla.dll, Lexilla.dll and necessary docs/licenses/samples. The separate tests ZIP is self-contained, includes byte-identical copies of those runtime files, and adds test executables, the test runner and bounded synthetic CI evidence. Both packages are made from the binaries that passed acceptance, without a rebuild between tests and packaging. Full inventory/hash and dependency-source/license gates apply to both.

## Source and build checks

- Pinned Ru native-C static checks and app-specific native argument audit, including conditional optional-library bindings and malformed-expression mutants.
- Shared document, UI-argument, flags and shortcut policies executed in both the interpreter and Linux native C.
- MinGW Windows x64 PE compilation, embedded original icon/manifest, pinned source-built Scintilla 5.6.7 and Lexilla 5.5.4, and system-only static import inspection.
- Independent source review of NUL/byte-count/UTF-8 guards, Scintilla status handling, grouped-undo cleanup, child-window rollback, canonical paths, file-dialog buffer ownership, orderly-shutdown veto, fatal-warning behavior and staged-save ownership.
- Launcher policy/source checks and four cross-built Win32 diagnostic fixtures. Detached GUI startup/logging/normal exit has real Windows coverage; failure-dialog, collision, fallback and reparse diagnostic fixtures still require dedicated execution.

## Remaining manual acceptance and limits

Physical Explorer mouse dragging, keyboard layouts, IME composition, clipboard integration, file dialogs and dirty prompts require interactive acceptance. Editor child routing revokes Scintilla's OLE text target; external text drops and internal selection drag-to-move are unavailable in this version. Further coverage is needed for shutdown veto, real-world ACL/EFS configurations, replacement/backup failures, fault injection, accessibility and rendering at different display scales. Local Wine never ran; it is not claimed as evidence.

No crash recovery exists. Use samples or copies first. The fixed 4 MiB limit is removed in 0.1.3; NUL rejection remains. Scintilla keeps the entire text in memory, and bounded streaming does not promise unlimited size. At 32,000,000 bytes, opening uses labelled plain-text/no-wrap mode; above 500,000,000 bytes, consent precedes any body read. Cancel is between I/O chunks, not during one synchronous disk call. Replace-all and very long-line rendering can still block. Ru files remain plain text in 0.1.3. Save All, recent files, backward/whole-word/selection-scope search, explicit EOL conversion, tab reordering and localization are absent. Plugins, macros, sessions and full Notepad++ parity remain future work.
