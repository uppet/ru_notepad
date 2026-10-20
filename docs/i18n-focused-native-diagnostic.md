# Focused native fixture diagnostic

This isolated workflow builds and runs exactly two complete native
fixtures on Windows 2022 x64:

- `markdown_direct_native`: 114 assertions, with the existing child-only
  `RU_GC_THRESHOLD=64` and `RU_GC_STATS=1` stress settings and the original
  GC/three-route metric parsers
- `app_i18n_native`: 1606 assertions, using a newly created disposable Unicode
  fixture directory and the test-owned hidden-window maximum tracking guard

A successful diagnostic proves only these two fixture executions. It does not
satisfy the ordinary 4144-assertion, 42-result product acceptance contract, run
the complete GUI/ACL/large-file suite, or create a runtime/test/preview ZIP.
The normal build, package, and acceptance drivers and thresholds are unchanged.
Portable controls and cross-built PE files cannot establish Windows success.

The search-enhanced fixture adds 189 assertions to the previously accepted 1417-assertion baseline. Its Windows result remains pending; historical runs below validate only their original sources.

## Selection and isolation

The `i18n_focused_diagnostic` manual input is false by default. Only an explicit
`workflow_dispatch` on `refs/heads/wip`, with that input enabled and all other
diagnostic modes disabled, is admitted. The Python guard checks the actual event
payload before compiler checkout or toolchain setup. Other refs, all push events,
and mixed manual modes are rejected.

The temporary push title `诊断：验收七语原生完整流程` has been retired following
the successful focused Windows run below. Every push, including that former
title, selects ordinary complete acceptance rather than bypassing it.

The focused run has its own concurrency suffix. Normal acceptance, the retained
manual window-size experiment, and the retained manual C++ growth diagnostic
are separate selections. This separates cancellation groups, not GitHub runner
capacity. The former window-size one-time push title has already been retired.

## Fresh inputs and unchanged build contract

A fresh checkout is required. Existing focused output, generated fixture C,
resource object, native helper cache, or extracted dependency trees are rejected.
Both official source archives pass the existing offline archive validator and
fixed size/SHA-256 checks before extraction. Scintilla, Lexilla, both native
helper DLLs, and both test executables are built during this run. Lexilla's
Windows make target explicitly uses `windir=C:/Windows`.

The Ru compiler remains commit
`85c7821fda35aa79deeaf67b4d430f24ddd7f07f`, tree
`a770e367e84d87a0d2fcb6d49ea6f06da2dbe4ba`, with its unchanged 200000-step
native signature analysis limit. The ordinary `tools/build.py` arguments are
used without changing the driver or its import behavior. No product executable
or stand-in product receipt is created.

The diagnostic reuses existing PE, native-helper, dependency-source, and safe
source-path validators. Its explicit two-fixture receipt checks require the
actual entries, full source/resource snapshots, compiler identity and commands,
DLLs, actual generated C/translation units, sizes, and actual PE hashes. The
same bindings are checked again after execution. These subset checks do not
replace or masquerade as the full product receipt validator.

## Public evidence and failures

Only the literal file `build/focused-native-public/measurements.json` can be
uploaded, only on success. Its fixed schema contains numeric fields and hashes;
no arbitrary strings, paths, commands, stdout, stderr, or raw receipts are
allowed. Test IDs 1 and 2 identify Markdown and i18n. Markdown route IDs 0, 1,
and 2 identify fallback, bulk, and per-line controls. Source commit/tree and a
canonical source-snapshot hash bind the fresh artifacts to the checked source.

The report is validated before writing, flushed and reread privately, then
published by an atomic no-replace hard link into a new public directory.
Existing directories, links, malformed evidence, write/fsync failures, and
publication collisions fail closed. Raw build/runtime streams and failure
receipts stay private and are not uploaded.

The workflow emits only a fixed numeric execution marker. Failure stages are:
1 trigger/arguments, 2 real-Windows check, 3 freshness, 4 compiler/source identity,
5 archives, 6 dependency builds, 7 fixture builds, 8 receipt checks, 9 Markdown,
10 i18n, 11 final stability, and 12 publication. The marker includes bounded
observed assertion counts, never exception text. Setup/action infrastructure
failures can also stop the workflow before this marker exists.

Portable negative controls cover wrong/duplicate totals, wrong assertion counts,
missing/oversized/invalid logs, stderr, nonzero exits, timeout cleanup, forced GC,
route metrics, source/PE/C/compiler changes, receipt mutations, arbitrary public
path fields, no-replace races, and publication failures. These controls are
validation of the diagnostic, not native product execution evidence.

## Control failure identification

The fixed 19-case control suite now reports only numeric case IDs, status,
exception category, and bounded event counts. IDs are the immutable `CASES`
sequence in `tools/run_focused_controls.py`; changing the test inventory without
updating this sequence fails closed. Status 0 is pass, 1 assertion failure,
2 error, and 3 skip. Category 0 is none, 1 assertion, 2 value, 3 runtime,
4 operating-system error, 5 Unicode, 6 timeout, 7 other, and 8 mixed categories.
Raw test names, subtest parameters, paths, and exception messages remain private.
Only fully anchored bounded numeric lines are copied to the public workflow log.
Unknown, duplicate, incomplete, or malformed inventories return protocol code 2.

The Windows host-control failure in run 39386581890 occurred before either native
fixture was built or run; its original public log lacks individual case details.
Host reproduction identified two concrete portability defects in the controls:
an encoding-less source read under Python isolated mode (which ignores
`PYTHONUTF8`), and a simulated helper command that used a noncanonical temporary
path instead of the real builder's resolved compiler path. Both are corrected
with executable regression and old-behavior negative controls. These host
reproductions do not claim to identify the unavailable original Windows traceback.

## Observed focused Windows result

[Run 39392432786](https://github.com/uppet/ru_notepad/actions/runs/39392432786),
public commit `c5297e486afb8a016c1a1ba704c228f095027264`, tree
`ed1d55d8b99102ad578139ee6fc0942962bcbe45`, built fresh dependencies and both
fixtures, then passed all 114 Markdown-direct and 1,417 i18n assertions.
The fixed 19-case control suite passed before those builds. Independent review
validated the exact numeric report schema, source aggregate, entry hashes,
compiler identity and successful execution counts.

The sole uploaded `measurements.json` has SHA-256
`33be6ee6f528a10318eca5936e1f50f93e65b4e015335ffbbf30f9f0c6511652`.
This verifies the corrected owned filter buffer in the real seven-language
fixture. It is not the full 3,852-assertion / 42-result product gate or a ZIP
qualification. Those gates remain required after the temporary push selector
is retired.
