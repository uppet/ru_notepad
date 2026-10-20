# Unreleased internationalization candidate

- Add seven Ru-owned UI catalogs, stable message keys, English fallback, single-pass placeholders and consistent menu mnemonics.
- Add immediate interface switching and explicit per-user language persistence, keeping syntax/document encoding independent.
- Localize known file/encoding failures without discarding API/system codes; retain technical diagnostics.
- Add UTF-16 dialog filters, measured/wrapping search controls and portable/native acceptance fixtures.
- Integrate the current C++ folding, Markdown bulk/direct publication, safe32 scalar policy, natural-paint and bounded MDP2 diagnostic repairs without reducing their 2,071-assertion / 39-result baseline; add 1,775 internationalization assertions across three mandatory native fixtures.
- Retain the reviewed public Ru 0.22.1 compiler with its unchanged 200,000-step analysis budget. Preserve exact source-derived nonfatal compiler style hints without allowing unexpected compile or runtime diagnostics.
- Windows native, visual, accessibility and CJK IME acceptance remain pending. This independent integrated candidate has not been published.

# Changelog

## 0.1.8-preview — candidate

- Add `.md` / `.markdown` recognition, Language > Markdown and Lexilla colors.
- Add independently bounded Ru heading-section folds, per-document fold toggle and existing margin/collapse/expand commands. Document the conservative ATX/setext, fence, HTML and container subset separately from Lexilla's coloring dialect.
- Retain encoding, undo/savepoint, document-owner guards and the >=32MB Plain/no-wrap path. Add fresh portable, native and GUI gates; full Windows acceptance is pending.
- Keep Enter continuation and rendered preview outside this stage. This is a new reconstruction after lost local snapshots; previous Markdown test reports are not reused as acceptance.
- Organize five unchanged streaming-fixture helpers into a small shared module. Preserve the original native declarations, same-process test history and all original assertions.

## 0.1.7-preview — 2026-10-17

- Evaluate a conservative common-token prefix in the Ru batch policy. Only an initially empty frame/pending-header context can use it; the first unsupported event and all remaining events use the original regular loop. No lexical or folding decision, native scanner ABI, scheduling budget or direct-publication route changes.
- Require full nested-state, ordered-output, byte-style and fold equivalence against the accepted policy, including incomplete syntax, cross-chunk states, checkpoint edits and failure states in both real Ru backends.
- Retain all 1,487 native assertions / 33 results and require a separate interleaved Windows comparison with direct publication enabled on both sides. The only compared source difference is the reviewed Ru policy. Windows acceptance and end-to-end benefit remain pending; Linux microbenchmarks do not establish either.
- Keep external-file-change/reload work separate from this candidate.

## 0.1.6-preview — 2026-10-16

- Add 36 required native route, output and lifetime assertions, retaining all 1,451 prior assertions for a total of 1,487 / 33 results.
- Evaluate the documented Scintilla direct export for three style-publication messages, only for explicitly registered, same-thread, exclusive-document editors with validated ownership and text-only notification masks. Fold publication and all editing, saving and Win32 routing retain their existing paths.
- Keep the borrowed direct pointer within one validated non-pumping batch; unregistered or ineligible editors retain message-based publication. No change to Ru lexical/folding decisions or the scanner DLL ABI.
- Require complete native equivalence/lifecycle tests and an interleaved, same-run direct-versus-message comparison with the unchanged corpus, 30-second styling gate and six edit probes. The [corrected product run](https://github.com/uppet/ru_notepad/actions/runs/38984124830) passed all 1,487 assertions / 33 results, including the complete 500,039,680-byte roundtrip; both original packages passed independent verification. The [paired run](https://github.com/uppet/ru_notepad/actions/runs/38984124849) passed all three preflights and eight interleaved runs. Its two GUI pairs observed 10.248–11.456 seconds with direct publication versus 15.126–15.128 seconds with messages. This is a limited same-run observation, not a general speed or parity guarantee.
- Correct whole-process elapsed reporting in benchmark receipts, separately from styling wall/work/gap. Historical evidence is preserved without invented timing fields.
- Repair two native-test issues exposed by the first run: explicitly group array-valued mutation arguments, and use a loadable, verified missing-export DLL for the wrong-Lexilla test. The strict original 36 and 8 assertions remain, with independent loader preflight and portable parser regressions.

## 0.1.5-preview — 2026-10-16

- Prepare an independent bulk-transport optimization candidate using the reviewed Ru 0.21.6 owned-memory `读U32LE阵` API. Keep the scanner DLL ABI and lexical/folding policy unchanged; validate high header bits before exact reconstruction and retain every event bound/order check.
- Add 24 native production-decoder assertions, raising the syntax suite to 149 and the required total to 1,451 assertions / 32 results. Require 23 production-decoder arithmetic/control-flow cases in each portable backend, with exact input and output evidence.
- Retain the same Chinese corpus, 30-second GUI completion deadline and all six edit measurements. The [actual 0.1.5 run](https://github.com/uppet/ru_notepad/actions/runs/38957923664) subsequently passed all 1,451 assertions / 32 results and both original packages passed independent verification. Its 1 MB GUI result was 16.652 seconds, with six edit completions of 1.472–3.307 seconds; these observations did not establish an end-to-end gain over 0.1.4.
- A later [exact-build run](https://github.com/uppet/ru_notepad/actions/runs/38974348825) also passed all gates after correcting a test assumption: the first bounded open tick may finish initialization without reading text. The revised fixture requires bounded progress over two ticks and retains cancellation before the full file is read. Production streaming behavior was unchanged.
- External-file-change notification and reload remain a separate proposal, outside this version's changes.

## 0.1.4-preview — 2026-10-16

- Add a real Ru 0.21.3 lexical policy and structural folding, with Ru keyword/structural policy, a bounded application-owned C scanning helper and Scintilla container styling. Recognize Unicode names, exact comments, strings/escapes, numbers, keywords and contextual block delimiters.
- Add `.ru` automatic selection, a Ru language menu, fold margin, collapse/expand commands and Ctrl+Shift+[ / ]. Preserve bytes, dirty/undo state and per-tab fold state.
- Process bounded background styling slices and lexical checkpoints; coalesce edits and reuse a converged unchanged suffix. Keep the existing 32 MB plain-text mode.
- Require pure-policy, native byte-style/fold, main-window and detached GUI regressions plus measured 100 KB / 1 MB initial/edit evidence. Windows acceptance was still pending at this stage.
- First 0.1.4 CI exposed a rescue-scope fixture error and a 1 MB GUI styling completion timeout. Fix the related initialization/cleanup diagnostic scope paths and retain strict completion gates with bounded progress diagnostics; the GUI timeout was not resolved at this stage.
- The scope-repair run passed all 1,379 native assertions but still reached only 470,180 styled bytes within the GUI's 30-second deadline. Subscribe the main application only to text modification events, retain the full-notification core control, and add exact-same-corpus work/cadence diagnostics. Performance acceptance was still pending at this stage.
- The notification-filter run confirmed zero unused style/fold callbacks, but still missed full GUI completion (947,418 bytes / 30 seconds). Exact-corpus synchronous scanning took 9.967 seconds; the main timer spent 17.844 seconds between callbacks. Add a coalesced, UI-yielding continuation path with the same work budget and strict completion deadline; real Windows acceptance remains required.

- The cooperative scheduler completed the native 1 MB case in 19.754 seconds, but the detached GUI still timed out at 646,656 bytes. Bound and measure the GUI observer's own message traffic, add capped numeric progress projections, and repair the closing fixture's queue-hint setup race. Those diagnostic/test changes required a new exact-build Windows run before acceptance.

- The subsequent [repair4 run 38952771302](https://github.com/uppet/ru_notepad/actions/runs/38952771302) passed Linux and Windows gates: the original evidence confirms 1,427 native assertions / 32 results and complete 1 MB GUI styling in 16.000 seconds, followed by all six edit measurements. See the [historical baseline and clock limitations](docs/preview-validation.md#014-ru-syntax-history-and-ci-status). Both original ZIPs subsequently passed independent verification and were delivered.

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
