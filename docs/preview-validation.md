# Preview validation

Date: 2026-10-16 UTC. These are unsigned Windows x64 previews. Build/source checks and actual Windows acceptance are recorded separately.

## Released 0.1.1 evidence

[Windows run 38863597991](https://github.com/uppet/ru_notepad/actions/runs/38863597991), public commit `d8d678206787c924141449e339cee9ebff54fc79`, passed **277 native assertions**: document policy 23, UI arguments 19, file-attribute flags 80, editor 27, application lifecycle 23, file codec 77, and synthetic NTFS ACL fixtures 28. No required tests were skipped. A separate detached GUI smoke test observed a visible main HWND owned by the launched process, checked responsiveness, sent WM_CLOSE and obtained normal exit 0 without cleanup termination.

That run produced the 0.1.1 ZIP only after all required gates passed. CRC, full SHA-256 inventory, source/build receipts and dependency license checks were verified. These results establish those exact synthetic cases, not universal filesystem safety or complete interactive acceptance.

Earlier failures are retained rather than counted as passes: the 0.1.0 native menu argument grouping caused startup exit; the second 0.1.1 CI run exposed five mis-grouped attribute comparisons. The latter could report failure after creating a new destination file. The fixes and their exact malformed-expression regressions are documented in `startup-fix-0.1.1.md` and `file_codec_validation.md`.

## 0.1.2 acceptance gates

The new syntax, status and shortcut features require a new exact-commit Windows run. Local source checks, Linux policy execution and Windows cross-compilation do not establish their Windows runtime behavior.

Required acceptance retains every 0.1.1 assertion and adds:

- 34 shared shortcut-policy cases, also executable in the Ru interpreter and Linux native C.
- 21 real Scintilla status cases: mixed CRLF/LF/CR, final unterminated lines, insertion mode, tab/Han/emoji/combining-codepoint columns, unchanged text and savepoint.
- 23 main-level feature cases through real WM_COMMAND callback dispatch: tab navigation, zoom, language selection, independent documents, unchanged dirty/undo state and normal close.
- 82 real Lexilla C/C++ and JSON cases, plus two isolated startup fallback cases with 8 assertions each for missing DLL and missing CreateLexer export.

The total is **453 assertions across 13 required assertion results**, plus the separate visible-GUI/normal-close result. CI rejects missing results, skipped tests, inconsistent PASS-line totals, nonzero exits and timeouts. The actual Windows result and exact binary/source hashes are recorded in each successful package's BUILD.json; consult that receipt rather than treating this planned gate as a pass.

## Packaging

The ordinary runtime ZIP contains the application, Scintilla.dll, Lexilla.dll and necessary docs/licenses/samples. The separate tests ZIP is self-contained, includes byte-identical copies of those runtime files, and adds test executables, the test runner and bounded synthetic CI evidence. Both packages are made from the binaries that passed acceptance, without a rebuild between tests and packaging. Full inventory/hash and dependency-source/license gates apply to both.

## Source and build checks

- Pinned Ru native-C static checks and app-specific native argument audit, including conditional optional-library bindings and malformed-expression mutants.
- Shared document, UI-argument, flags and shortcut policies executed in both the interpreter and Linux native C.
- MinGW Windows x64 PE compilation, embedded original icon/manifest, pinned source-built Scintilla 5.6.7 and Lexilla 5.5.4, and system-only static import inspection.
- Independent source review of NUL/byte-count/UTF-8 guards, Scintilla status handling, grouped-undo cleanup, child-window rollback, canonical paths, file-dialog buffer ownership, orderly-shutdown veto, fatal-warning behavior and staged-save ownership.
- Launcher policy/source checks and four cross-built Win32 diagnostic fixtures. Detached GUI startup/logging/normal exit has real Windows coverage; failure-dialog, collision, fallback and reparse diagnostic fixtures still require dedicated execution.

## Remaining manual acceptance and limits

Physical keyboard layouts, IME composition, clipboard integration, file dialogs and dirty prompts require interactive acceptance. Further coverage is needed for shutdown veto, real-world ACL/EFS configurations, replacement/backup failures, fault injection, accessibility and rendering at different display scales. Local Wine never ran; it is not claimed as evidence.

No crash recovery exists. Use samples or copies first. The 4 MiB UTF-8 document/save limit and NUL rejection remain. Ru files remain plain text in 0.1.2. Save All, recent files, backward/whole-word/selection-scope search, explicit EOL conversion, tab reordering and localization are absent. Plugins, macros, sessions and full Notepad++ parity remain future work.
