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

## Active acceptance and the retired case

All active correctness and original 30-second stage deadlines remain required.
On 2026-10-27 the user explicitly retired only the 1 MB unclosed-fence serial
two-Undo folding-completion case from blocking/default execution. It is recorded
as deprecated and unexecuted, never as passed. The other two Undo corpora and
all open/insert/Backspace stages remain. See the precise scope, historical
30,007.113 ms failure, reproduction and TODO in
[bootstrap preview scope](bootstrap-llvm-preview.md#deprecated-case-and-todo-2026-10-27).

This does not substitute back-to-back Undo, enlarge a timeout, or infer recovery
from a killed process. UI responsiveness and background convergence differ.
Historical wij/dense exclusions remain. Native lifecycle and real Windows
single-instance/tab-menu validation are still required for the exact binaries.
