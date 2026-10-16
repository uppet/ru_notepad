# Changelog

## 0.1.2-preview — 2026-10-16

- Add native Lexilla 5.5.4 C/C++ and JSON highlighting, automatic extension selection, and an explicit Language menu. `.ru` remains plain text pending a dedicated lexer.
- Show current-line EOL separately from Enter insertion mode. Define columns as Scintilla tab-expanded Unicode codepoint columns and retain byte length/encoding.
- Add reverse/alternative tab navigation and zoom reset; preserve AltGr/input-method combinations.
- Split the ordinary runtime ZIP from a self-contained tests ZIP. Both contain byte-identical tested runtime files and dependency licenses; test executables/evidence stay out of the ordinary ZIP.
- Require exact assertion counts, isolated missing-Lexilla fallback checks, stronger package-inventory/hash regressions, and real Windows execution before delivery. These additions are pending their own CI receipt.

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
