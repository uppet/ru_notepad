# Ru 0.24 editor candidate (not yet a validated preview)

This increment targets usable editor improvements, not a Notepad++ parity claim.
It preserves the r3 known limitations until the exact new Windows binary passes
its existing checks. No main, wip, tag or release publication is implied.

## Included changes

- `续` is a Ru keyword with no fold-opening/closing effect. Reserved-name and
  provisional callable-body recognition follow the same token. Strings, comments,
  longer names and UTF-8 split input retain their existing behavior.
- Markdown streaming inlines the scalar UTF-8 width calculation and defers pure
  heading/prefix lookup until after opaque raw/fence branches. State layout,
  closer-array alias semantics, chunk sizes, publication limits, generations and
  the 8 ms admission budget are unchanged.
- Existing Windows Markdown snapshots record length/savepoint observations,
  per-Undo status observations and WM_NULL probe elapsed time separately. These
  are sampled observations, not full text hashes, exact completion timestamps,
  input latency or frame latency. Final style/fold/byte-context checks remain.

## Evidence boundary

Portable tests cover Ru lexical fixtures (422 assertions per interpreter/GCC),
99 native scanner cases / 594 byte-chunk checks, Markdown fixtures (221 assertions
per interpreter/GCC), and a separate baseline/candidate differential covering
16,741 feeds per backend with every state slot, fold result and retained closer
alias checked. These do not prove Windows GUI behavior or bootstrap LLVM parity.
The preview pipeline additionally requires actual stage3 compilation/execution
of lexical and Markdown fixtures, alongside the three existing MRU fixtures.

One local exploratory GCC run alternated baseline/candidate on the same synthetic
1,310,731-byte unclosed fence. Whole-process times were baseline 7.109 / 7.128 /
7.214 s and candidate 6.749 / 6.686 / 6.657 s; fold checksum, consumed bytes, lines
and calls matched. This is a narrow parser experiment, not a pure-C algorithm
control, Windows measurement, Undo measurement or proof the 30 s failure is fixed.

## Acceptance remains unchanged

The original Undo stage waits for first-fold completion before issuing a second
Undo when still dirty; both scans share its original 30 s wall deadline. This
candidate does not replace it with back-to-back Undo, widen its timeout, or infer
natural recovery from a timed-out/killed process. UI responsiveness and background
fold convergence are different results. Historical wij/dense exclusions remain.

Next evidence: exact compiler/app/source identity, bootstrap + LLVM build, actual
Windows native DLL and same-binary GUI tests, then an explicitly scoped preview.
If the original gate still fails, retain its known-limit label and phase evidence.
