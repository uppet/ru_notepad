# Changelog

## 0.1.4-preview — 2026-10-16

- Add a real Ru 0.21.3 lexical policy and structural folding, with Ru keyword/structural policy, a bounded application-owned C scanning helper and Scintilla container styling. Recognize Unicode names, exact comments, strings/escapes, numbers, keywords and contextual block delimiters.
- Add `.ru` automatic selection, a Ru language menu, fold margin, collapse/expand commands and Ctrl+Shift+[ / ]. Preserve bytes, dirty/undo state and per-tab fold state.
- Process bounded background styling slices and lexical checkpoints; coalesce edits and reuse a converged unchanged suffix. Keep the existing 32 MB plain-text mode.
- Require pure-policy, native byte-style/fold, main-window and detached GUI regressions plus measured 100 KB / 1 MB initial/edit evidence. Actual 0.1.4 Windows acceptance remains pending.
- First 0.1.4 CI exposed a rescue-scope fixture error and a 1 MB GUI styling completion timeout. Fix the related initialization/cleanup diagnostic scope paths and retain strict completion gates with bounded progress diagnostics; the GUI timeout is not yet claimed fixed.
- The scope-repair run passed all 1,379 native assertions but still reached only 470,180 styled bytes within the GUI's 30-second deadline. Subscribe the main application only to text modification events, retain the full-notification core control, and add exact-same-corpus work/cadence diagnostics. Performance acceptance remains pending.

## 0.1.3-preview — 2026-10-16

- Add explicit per-user Open With / Default Apps candidate registration, ownership-safe removal, status, and a Windows Settings link. Windows retains control of default choices.
- Route Unicode CLI, dialog and multi-file HDROP inputs through one bounded queue; retain dirty tabs, continue after per-file errors, and select duplicates by file identity.
- Replace whole-file open/save paths with bounded Unicode/legacy cursors and hidden pending editors. Remove the fixed 4 MiB limit; ask before any body read above 500,000,000 bytes. A separate 32,000,000-byte plain-text performance mode disables lexer/wrap.
- Advance open/save through bounded timer batches with Cancel/Esc, mutation locking, revision checks and safe asynchronous close continuations. Retain conflict checks, protected staging, recovery backups and checked final commits.
- Require native chunk-boundary/cancellation/registry/drop/main-operation tests, full 500,039,680-byte editor roundtrip, and detached GUI file-entry/cancel acceptance. The corrected exact-build Windows run 38887294845 passed these gates.
- Pin the independently validated Ru 0.21.3 toolchain; keep runtime/tests ZIPs separate and byte-identical for shared runtime files.
- First Windows run passed 797 assertions, both GUI gates and the complete 500,039,680-byte roundtrip, but could not package because the file-drop console fixture lacked the v6 manifest required by GetWindowSubclass. Embed the same reviewed manifest in every executable; keep all 38 file-drop assertions. The complete corrected run passed 835 assertions / 23 results, and both original CI ZIPs were independently verified.

## 0.1.2-preview — 2026-10-16

- Add native Lexilla 5.5.4 C/C++ and JSON highlighting, automatic extension selection, and an explicit Language menu. `.ru` remains plain text pending a dedicated lexer.
- Show current-line EOL separately from Enter insertion mode. Define columns as Scintilla tab-expanded Unicode codepoint columns and retain byte length/encoding.
- Add reverse/alternative tab navigation and zoom reset; preserve AltGr/input-method combinations.
- Split the ordinary runtime ZIP from a self-contained tests ZIP. Both contain byte-identical tested runtime files and dependency licenses; test executables/evidence stay out of the ordinary ZIP.
- Replace unsupported array `含` calls exposed by the first native run with a shared explicit-match policy, directly exercised by 100 interpreter/Linux C cases and required in the Windows suite. Preserve all original syntax assertions and an expected-failure fixture for the invalid API call.
- Require exact assertion counts, isolated missing-Lexilla fallback checks, stronger package-inventory/hash regressions, and real Windows execution before delivery. The repaired exact-build Windows run 38871195015 subsequently passed all 553 assertions and GUI acceptance.

## 0.1.1-preview — 2026-10-16

Repairs the first preview's confirmed Windows startup failure. The prior native library loading succeeded; a malformed Ru menu argument expression caused a fatal map-lookup arity error.

- Fix all six related native argument-array errors, not only the first failing call.
- Share actual GUI argument construction with 19 portable assertions, passing in both interpreter and Linux native C.
- Add fail-closed native argument audit: all 104 calls resolved, zero corrected mismatches.
- Add startup phases and a small native diagnostic launcher for visible fatal errors and unique local logs, without changing Ru runtime semantics or saving documents automatically.
- Fix five attribute bit-field comparisons found by real Windows codec testing. Use one production predicate, exercised by 80 strict-receiver assertions in both portable runtimes, plus exact malformed-expression regressions.
- Reject explicit boolean native arguments and swallowed bit-field comparisons in the project AST gate; eight mutation cases exercise the gate.
- Real Windows startup, normal close, and the document/UI/Scintilla/application suites passed. Codec and ACL tests blocked that attempt from packaging. The corrected third run subsequently passed all 277 native assertions, including codec77 and ACL28, plus visible GUI/normal close; run 38863597991 produced the verified release ZIP.
- Retain original failure evidence and keep all test/packaging gates fail-closed.

## 0.1.0-preview — 2026-10-16

First private Windows x64 portable preview, cross-built on Linux. Native Windows and Wine application execution remain unverified.

- Mostly-Ru Win32 application with independent Scintilla tabs, file dialogs and original GPT-generated icon.
- UTF-8/BOM, UTF-16 LE/BE, explicit Windows-1252 and GBK; strict encoding and NUL rejection.
- Same-directory staged save with conflict guards, flush, recovery backup, copied protected staging DACL, and fail-closed EFS/read-only/hard-link handling.
- Dirty/save prompts, independent undo/redo, literal find/replace, case matching, grouped replace-all, line numbers, wrap and zoom.
- Embedded-NUL/byte-count/status guards, transactional tab creation, fast dirty-document shutdown veto, and visible fatal-error reporting.
- 23 portable document-policy assertions pass both the Ru interpreter and Linux native C. Windows native test executables are included but have not run here.
- Pinned Ru 0.21.1 compiler candidate and Scintilla 5.6.7; binary/source hashes and dependency notices accompany the package.

Limits: 4 MiB file/save and UTF-8 editor-load bounds, 64 tabs, no crash recovery, regex, lexers, plugins, macros, split views or full Notepad++ parity. Use sample files or copies only until Windows acceptance is complete.
