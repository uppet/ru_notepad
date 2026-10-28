# Bootstrap LLVM preview scope

This candidate targets a Windows x64 preview with a recent-files list in the
File menu and an editor executable compiled by the native Ru bootstrap compiler
through the LLVM backend. Publication is conditional on fresh validation of the
exact source and executable. This document is a plan, not a passing test receipt.

## Separate evidence, without substituting one for another

- The compiler source must be pinned to an independently validated native-FFI
  integration. A language version, successful ordinary bootstrap fixed point,
  or green main/wip jobs alone does not establish native-FFI build capability.
  Both the native frontend/Windows gates and this editor's current module graph
  must be validated; an older compiler pin is not silently substituted.
- Bootstrap source, stage compiler, emitted IR, native dependencies and final
  executable identities are recorded. No Python compiler or generated-C route
  may silently replace the bootstrap LLVM editor build.
- The actual preview executable must pass the bootstrap pipeline smoke checks,
  all four existing GUI product gates, the recent-files tests, and the actual
  two-process single-instance / tab-menu GUI tests. Active deadlines and
  correctness assertions remain required. The one explicitly deprecated
  Markdown case below is not executed by default and is not recorded as passed.
- Five real-stage3 fixtures cover recent-file policy (25 assertions), native
  registry/encoding boundaries (22), actual main-module callback control flow
  (10), Ru lexical policy including 续 (422), and Markdown policy (221). These
  original 700 assertions remain required. Six additional fixtures cover tab
  close policy (16), single-instance protocol/settings policy (41), isolated
  native registry roundtrip (11), native tab callbacks (53), and actual enabled
  single-instance lifecycle (18), and real open-finalization BUSY/ACK behavior (23):
  eleven fixtures, 862 assertions. Receipt schema v4 rejects the former v1/v2/v3 receipts.
  The exact three dependency DLLs are copied beside the fixture executables;
  original and copied identities are checked before/after execution and again
  at product/package consumption. No PATH-only DLL substitution is accepted.
  These fixtures do not substitute for starting and testing the editor.
- Before expensive compilation, five complete production single-instance state
  functions run in the interpreter and generated C with explicit controlled OS
  boundaries. Dictionary-write, ACK/NACK, timeout and discovery mutations must
  fail. This is control-flow evidence, not Windows ABI or IPC acceptance; the
  native lifecycle and actual two-process GUI checks remain mandatory.
- The existing C-built native fixture suite remains separate baseline evidence.
  Its passing result does not claim those fixture executables were built with
  bootstrap LLVM, nor does a bootstrap smoke check replace product validation.
- The preview ZIP must contain the exact tested editor and DLL bytes. Packaging
  must independently verify those identities after reading the archive back.
  A ZIP existing is not, by itself, an acceptance result.

## Deliberately excluded

The `wij` Markdown incremental/dense experiment is not included in this preview.
Its disabled switches still import modules requiring the experimental dense
bridge, while the preview toolchain adds only the reviewed native-FFI support.
Historical timing results are not fresh evidence for this build. No unverified
optimization is enabled by default.

This is not full Notepad++ compatibility or a claim that all interaction latency
is solved. Manual IME, accessibility, different-DPI and Explorer drag-and-drop
checks remain distinct from automated GUI checks. Use copies of important files.

The final preview receipt must list actual passes, failures, untested coverage
and any known limits; it must not describe this candidate plan as completed work.

## Dependency baseline limitation

The first preview attempt built its DLLs with MSYS2 GCC 16.2.0-4 and
CRT/headers 14.0.0.r426.g4564ee4b5-1. Its separate, fully updated C-baseline
workflow instead selected GCC 16.2.0-6 and CRT/headers
14.0.0.r532.gdbbc8e99d-1 and failed linking Scintilla with an unresolved
`__mingw_fe_dfl_env`. Isolated probes did not reproduce that full-library
failure; it is not claimed fixed. These are different dependency toolchains,
not interchangeable passing evidence. Each preview build records the actual
tool and DLL identities; its own original product gates must still pass.
The C-baseline run must be disclosed as failed/uncompleted at that point, not
reported as a successful complete release suite.

## Native application graph evidence

The editor-owned `compile_bootstrap_native.py` calls the exact reviewed 26cc
`compile_native` API with native support and retained frontend evidence. During
main, probe and all ten fixture compilations it poisons seven Python application
frontend entry points (including the native emitter's source alias). Attempts,
even caught ones, fail the build. This does not replace stage3, the six frozen
LLVM executable identities, linker/source checks, native fixtures or GUI gates.

Only the main entry is checked against the independently generated, source-frozen
`packaging/application-native-oracle.json`: complete module byte identities,
complete native signature/callback sets, and every module initializer's callback
first-import guard before initializing state. Metadata initializer inventory does
not itself map bodies to source paths; exact proof dependencies bind source names
and bytes. The oracle is a development reference, not native execution evidence.
Its base anchor is b79; the enclosing source snapshot binds the candidate version
without an impossible self-referential commit hash.

The preview ZIP carries five bounded evidence files: application metadata C,
compile proof, native wrapper receipt, independent oracle, and oracle validation.
Their exact hashes are bound into provenance and the packaging receipt. Retained
frontend LLVM IR stays in CI evidence and its SHA-256 is recorded in the ZIP;
compiler executables and environment configuration are not packaged. Portable
negative controls validate contracts only; successful producer compilation and
Windows GUI execution must come from this candidate's actual CI run.

## Deprecated case and TODO (2026-10-27)

At the user's explicit request, only the **1,000,000-byte unclosed-fence
Markdown serial two-Undo folding-completion case** is retired from blocking
acceptance. Default acceptance does not execute that stage. Its record must say
`deprecated`, not executed and not passed; missing or forged retirement evidence
is not acceptance. The corpus's open, insert and Backspace stages remain required,
as do both other corpora's Undo stages, all their original 30-second limits,
style/fold/context checks, responsiveness, source preservation and normal cleanup.
No timeout is enlarged. The synthetic document left dirty after Backspace must
be explicitly discarded through the real confirmation flow, not marked clean
with a synthetic savepoint or described as successful Undo.

**TODO:** profile and optimize whole-document folding/recovery for this retired
case when time permits; restore a measured completion requirement only after
reviewed evidence. Text restoration and background-fold convergence are different
results. WM_NULL response samples do not measure input or frame latency.

Historical failure is preserved: exact editor commit
`5262c085f473474ba94cfe0d73fa2b025c42a123`, compiler
`26cc8a210d5cef2bd8ab37b6c270833884ea39a5`,
[Windows run 40467458570](https://github.com/uppet/ru_notepad/actions/runs/40467458570),
reported this stage at **30,007.113 ms**, still folding. The first fold status
completed at 16,503.333 ms, the second Undo returned at 16,508.560 ms, and
length/savepoint restoration was first observed at 16,765.055 ms. Open completed
in 26,739.650 ms and passed. These historical measurements are neither rewritten
as passes nor proof of full-byte restoration or eventual convergence. That run
also failed a separate single-instance GUI check and produced no accepted ZIP.

An explicit diagnostic call `run_gui_markdown(..., reproduce_deprecated=True)`
retains the original twelve-stage sequence and historical receipt contract. It
is not used by default acceptance or accepted by the current default validator.
The deterministic reproduction also remains in that exact historical source:
`gui_markdown_fixture('unclosed-fence')` has SHA-256
`2d9f79ee715b217c00792cf18a67485cdec96a14ea2ac86689156941a022c719`,
and `run_gui_markdown_stage` performs the original serial Undo actions and
30-second observations. The historical source, reports and failed CI are retained
for investigation; reproducing them is opt-in, not part of default acceptance.
The separate old Ru 0.22 C-native lane's signature-analysis complexity failure
remains a disclosed limitation, not a passed gate or a budget increase.
