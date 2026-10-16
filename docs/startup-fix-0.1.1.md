# 0.1.1 startup repair

## Observed failure and cause

A real Windows run of 0.1.0 loaded Scintilla and the required Windows DLLs, then exited before the main window appeared. This is a confirmed failed startup, not a missing-DLL assumption.

Original executable SHA-256: `f67b2e4c695c141974cf523e8d799f62f7dcbc5be0c2e0b68a252882eab553b8`.

The recorded return RVAs map against the retained original PE symbol table:

| RVA | Function |
| --- | --- |
| 0x2424 | ru_fail + 0x124 |
| 0x344e | ru_bind + 0x21e: positional-arity failure |
| 0x20b02 | v_member + 0x5c2 |
| 0x2398b | v_member_finish + 0x7b |
| 0xb8c8c | ru_function_25: 菜单 |
| 0x10d58c | ru_function_28: 初始化 |
| 0xaaeab | ru_function_29: 元初 |

The original `src/main.ru:336` used `[A 其 查 'window',主]`. Ru parses the comma as a second argument to `查`, producing a one-item array. The generated C explicitly invokes `查` with argc=2 and source line 336; the same values appear in the disassembly. Map lookup requires one argument, so the runtime calls `ru_fail`. Ordinary runtime contract failures are not explicit `卒` exceptions and do not enter the application rescue. A GUI-subsystem executable had no visible stderr, explaining the silent exit.

## Repair and regression evidence

Six malformed native argument arrays existed at original main.ru lines 47, 89, 120, 137, 336 and 503. All now call pure Ru helpers with explicitly grouped array elements. The menu test executes the exact helper used by SetMenu; the other five constructions share tested helpers too.

- Original minimal malformed expression: fails with the expected arity error in both the actual Ru interpreter and Linux native C.
- Actual shared UI argument helpers: 19/19 assertions pass in both runtimes.
- Existing document policy: 23/23 assertions pass in both runtimes.
- Native-argument AST gate resolves all 104 native calls. Original snapshot: 6 mismatches. Corrected snapshot: 0 mismatches, 0 unresolved, with 98 literal arrays and 6 shared-helper constructions.
- The member-name arity conventions in this project gate are not a universal Ru language rule.

A narrow native launcher initializes local diagnostic logging before Ru module initialization and shows a visible diagnostic on unhandled exit/nonzero return. Ru still owns the editor UI, document handling and application policy. No language runtime semantics are changed and no emergency save is attempted.

## Verification boundary

The Linux cross-build and portable checks do not establish Windows GUI or diagnostic behavior. A later Windows CI artifact must record its own native suite and main-window results in BUILD.json; only those listed checks count as executed. Broader interactive Windows acceptance remains open. The original 0.1.0 ZIP, PE, build receipt, generated C and symbol mapping are retained for reproducibility. The repair does not turn the previous build-only checks into a Windows pass.

## Additional file-attribute regression found by Windows CI

The second Windows run passed startup and editor/application tests but failed codec and ACL tests at the first existing-file attribute check. The original `属性 其 位段 4 1 == 1` parses as `位段(4, 1 == 1)`: a fact is passed as numeric width. Five directory/reparse/EFS/read-only checks had this form. They now call the same explicitly grouped predicate in `src/file_codec_flags.ru`.

A strict pure-Ru receiver executes that production predicate with 80 cases on both interpreter and Linux C. It checks the four attribute bits across all combinations and unrelated high bits. The exact old expression fails type checking in both runtimes. Eight parser/gate mutants additionally verify that known boolean scalar arguments and swallowed comparisons are rejected. These are argument-semantic checks, not substitutes for actual Windows native-scalar and file operations.

The failed run must not be described as universally leaving targets unchanged: an existing file fails during preflight, but a new-file rename may already succeed before the subsequent metadata read reaches the malformed test. No ZIP was published from that failed run. A corrected full Windows codec/ACL pass is required before packaging.
