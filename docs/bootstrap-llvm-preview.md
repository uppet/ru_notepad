# Bootstrap LLVM preview scope

This candidate targets a Windows x64 preview with a recent-files list in the
File menu and an editor executable compiled by the native Ru bootstrap compiler
through the LLVM backend. Publication is conditional on fresh validation of the
exact source and executable. This document is a plan, not a passing test receipt.

## Separate evidence, without substituting one for another

- The compiler source is pinned to a reviewed native-FFI integration based on
  the validated `ru-language` main line. The unmerged `wip` interpreter-depth
  changes are not a prerequisite or part of that toolchain.
- Bootstrap source, stage compiler, emitted IR, native dependencies and final
  executable identities are recorded. No Python compiler or generated-C route
  may silently replace the bootstrap LLVM editor build.
- The actual preview executable must pass the bootstrap pipeline smoke checks,
  all four existing GUI product gates, and the recent-files tests. Existing
  deadlines and assertions remain unchanged.
- Three additional real-stage3 recent-file fixtures cover policy (25 assertions),
  native registry/encoding boundaries (22), and the actual main-module callback
  control flow (10). They do not substitute for starting and testing the editor.
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
