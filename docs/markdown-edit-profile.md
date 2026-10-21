# Owned Markdown edit/Undo diagnostic (local candidate)

This is a diagnostic, not a product acceptance replacement. It uses the pinned
compiler `85c7821fda35aa79deeaf67b4d430f24ddd7f07f` and exact c86 product sources.
No product source, official acceptance deadline, workflow trigger, or compiler
implementation is changed. The original first-load profiler remains available.

## Scenario and limits

One fresh owned release process and one fresh owned instrumented process each
open the existing synthetic 1,000,000-byte / 100,000-newline unclosed-fence
Markdown fixture by file drop. They perform the existing actual `x` input,
Backspace, and menu Undo scenario. The existing dirty/history rule decides
whether one or two Undo commands are needed. Fixed head/tail styles, folds,
context bytes, native lexer, source hash, dirty state, queued navigation and
natural paint completion are still checked. No whole-document text or style
export, forced savepoint, forced colourise, or forced undo grouping is added.

The product gate is **30 seconds per operation**. A private exact-source adapter
records a sticky `product_gate_failed` instead of throwing at the two time checks,
allowing diagnostic completion only within the original **120-second total
owned-process lifetime**, including launch, all operations and ordinary shutdown.
A completed late run has `diagnostic_complete=1`, `diagnostic_late=1`, and
`passed=0`; it still exits the diagnostic CLI unsuccessfully. Other functional,
ownership, sampling, five-second responsiveness, log and cleanup errors remain
fatal. The stdout completion marker reports diagnostic completion, not passing.
If the first process fails a gate but is confirmed cleaned up, a separate owned
profile may run. Unconfirmed cleanup/output retention blocks the next launch.

The private adapter also accounts for the original observer's hidden limits:

| Source location | Product | Private diagnostic only |
| --- | --- | --- |
| stage loop + final proof | 30-second rejection | sticky product failure |
| `GuiRuObserver.wrap` | 30-second observer timeout | 120-second bound |
| `GuiRuObserver.snapshot` | 121 snapshots | 481 snapshots |
| `MarkdownProcessMemory.sample` | 121 samples | 481 samples |
| observer validator | 121 snapshots / 601 responses | 481 / 2401 |
| memory validator | 121 samples | 481 samples |

The 50ms response interval, 250ms full-snapshot interval and 32 synchronous
messages per snapshot remain unchanged. Module and individual function/class
hashes plus exact AST replacement counts fail closed on drift. Original Python
objects, globals and product source bytes are not mutated. An independent
retained-Popen guard enforces the total deadline; no PID reopen or foreign
process termination is used. The diagnostic bounded WM_NULL implementation
bypasses a nested observer wrapper so one native message is counted once.

## What the numbers mean

The header records at most five **cumulative completed-revision snapshots** in
memory and emits one bounded numeric aggregate on normal shutdown. An incomplete,
foreign-thread, reopened, non-monotonic or unbalanced profile invalidates the
whole aggregate. The final shutdown snapshot is separate. If the hard limit
kills the process before a valid final record, no trusted phase attribution is
claimed; only available bounded stage facts are projected.

`operation_deltas` are differences between consecutive completed snapshots,
ordered open / insert / Backspace / Undo. The last delta groups both Undo
revisions when two commands occurred. These intervals can include intervening
no-step timer roots and inter-root idle gaps: **they are not pure input-to-edit
latencies**. Actual operation `wall_ms` is separately reported. Inclusive phase
times overlap and must not be added. Exclusive phase times partition timer-root
wall time; they do not partition whole-process lifetime. The six `snapshots`
slots contain up to five revision vectors (unused slot zero) and the final
shutdown vector at index 5. Shutdown work is not silently included in Undo.

Each vector has 70 values:

1. root count, no-step root count, step count, outermost-root QPC ticks,
   root user CPU (100ns), root kernel CPU (100ns), inter-root gap ticks,
   raw native-other entries, raw native-bulk entries, scanned feed bytes;
2. four hot call counts: `v_index`, `env_get`, `heap_new`, `v_call`;
3. entries / inclusive QPC ticks / exclusive QPC ticks for each of eight phases;
4. four hot call counts for each of those same eight phases.

Phase order: timer_root, bridge_advance, pure_feed, bridge_publish, bulk_prepare,
native_other, native_bulk, callback. Convert QPC ticks using `qpc_frequency`.
Root CPU is outer-root thread CPU; whole-owned-process user/kernel CPU is separate.
This is not CPU sampling or proof of whole-process hotspots. `heap_new` counts
allocation entry calls, **not allocated bytes or GC elapsed time**. GC collection
cost, root-snapshot cost and work outside the syntax timer root remain unmeasured.
Navigation/paint wall observations are responsiveness evidence, not renderer CPU.
No conclusion that GC or FFI dominates may be drawn before real measurements.

## Local controls and future Windows run

Run from repository root:

```sh
python tools/test_markdown_control_markers.py
python tools/test_markdown_owned_workflow.py
python tools/test_markdown_edit_transform.py
python tools/test_markdown_edit_profile.py
python tools/test_markdown_edit_late.py
python tools/test_markdown_edit_observers.py
gcc -std=c11 -O2 -Wall -Wextra -Werror -pthread tests/markdown_edit_profile_host.c -o /tmp/edit-profile-host
/tmp/edit-profile-host
```

Actual generated-C audit (generated input/receipt stay private):

```sh
python tools/test_markdown_edit_transform.py --source-root . --input-c PRIVATE/main.c --receipt PRIVATE/receipt.json --header native/markdown_edit_profile.h --output PRIVATE/audit.json
```

After separate publication/CI authorization, a Windows host with the matching
product build receipt and compiler checkout can invoke:

```text
python tools/run_markdown_edit_profile.py --ru-root PINNED_COMPILER --binary-dir MATCHING_PRODUCT_BIN --cc GCC --windres WINDRES --evidence-dir FRESH_EXISTING_DIRECTORY
```

The prepare path verifies the unchanged source/build/runtime hashes, regenerates
matching product C and audits selected function bodies, native error adjacency
and trap layout. Only the profile executable differs; native DLLs are identical.
Compilation/raw logs and source maps stay in a fresh private build directory.
Only `markdown-edit-profile.json` is eligible numeric/hash output (64KiB cap,
no-replace atomic publication). No upload or CI dispatch occurs in this tool.
Do not put private build directories or diagnostic binaries in product ZIPs.

Host tests use deterministic fake clocks/APIs and actual header/observer logic;
they do not establish Windows performance. Actual Windows compile, native TLS
control/disassembly, owned GUI run, full functional proofs and numeric artifact
inspection are still required before bottleneck attribution.
