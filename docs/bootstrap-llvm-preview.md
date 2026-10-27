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
  all four existing GUI product gates, and the recent-files tests. Existing
  deadlines and assertions remain unchanged.
- Five real-stage3 fixtures cover recent-file policy (25 assertions), native
  registry/encoding boundaries (22), actual main-module callback control flow
  (10), Ru lexical policy including 续 (422), and Markdown policy (221). These
  original 700 assertions remain required. Four additional fixtures cover tab
  close policy (16), single-instance protocol/settings policy (39), isolated
  native registry roundtrip (11), and native tab callbacks (53): nine fixtures,
  819 assertions. Receipt schema v3 rejects the former five-fixture/v2 receipt.
  The exact three dependency DLLs are copied beside the fixture executables;
  original and copied identities are checked before/after execution and again
  at product/package consumption. No PATH-only DLL substitution is accepted.
  These fixtures do not substitute for starting and testing the editor.
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
main, probe and all nine fixture compilations it poisons seven Python application
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
