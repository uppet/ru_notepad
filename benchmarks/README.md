# Performance evidence and next measurements

Windows execution evidence exists. Cross-build time is still not UI performance,
and passing the correctness gates does not establish Notepad++-level speed.

## Recorded Windows results

These are individual CI runs on Windows Server 2022 runners, not repeated trials
on a fixed physical computer. Preserve their different measurement boundaries.

| Measurement | 0.1.4 preview | 0.1.5 preview candidate |
| --- | ---: | ---: |
| Same 1,000,000-byte Ru corpus, synchronous native fixture | 10.453 s | 9.223 s |
| Same corpus, cooperative console fixture | 14.788 s | 14.272 s |
| Same corpus, detached GUI, opening through complete styling | 16.000 s | 16.652 s |
| Six 100,000-byte GUI insertion/deletion cases, complete restyling | 1.265–3.265 s | 1.472–3.307 s |

Sources: [0.1.4 Windows acceptance](https://github.com/uppet/ru_notepad/actions/runs/38952771302)
and [0.1.5 Windows acceptance](https://github.com/uppet/ru_notepad/actions/runs/38957923664).
The latter passed 1,451 native assertions in 32 result groups, including the
existing data-safety and GUI checks. It does **not** show an overall GUI speedup.

The common 1 MB corpus is exactly 1,000,000 UTF-8 bytes, 636,370 Unicode scalars,
and 90,909 LF newlines. SHA-256:
`ecf8dca884444a5e54e1f40dc6af01cf5e7830ed6fe902d3adf6fdf255f9b3fa`.
It is synthetic, mostly flat Ru text. Results on this corpus do not describe all
real programs, deeply nested structures, or very long single lines.

The GUI completion gate checks head and tail styles, full styled position,
status completion, exact length, clean state, and unchanged source bytes.
Separate fixtures check complete styles and fold levels. Editing measurements
cover insertion and deletion at the beginning, middle and end; they measure
completion of restyling, not how long keyboard input is blocked. Queued navigation
and natural paint servicing are also checked while styling is pending. They are
not physical input-to-pixel latency measurements.

0.1.5 uses Python `perf_counter` backed by QueryPerformanceCounter for the Windows
observer. The earlier observer clock was coarser. Sampling can delay the observed
first styled token, and synchronous query time can include waiting for the app.
Do not subtract observer time from application time or interpret a recorded zero
as zero overhead. See the raw CI evidence for clock metadata and observer counts.

## Large-file boundary

The old 4 MiB cap was removed in 0.1.3. Streaming native tests now load, save and
compare all **500,039,680 bytes** of a valid synthetic file with bounded temporary
I/O buffers. The test passes in both runs linked above. This is a full native
roundtrip, not a claim about every interactive large-file workload.

Opening a file larger than **500,000,000 bytes** requires consent before reading.
Documents at the separate **32,000,000-byte** performance threshold use a labelled
plain-text mode that pauses syntax highlighting. Scintilla still holds the
document in memory; streaming does not promise unlimited file sizes. Cancellation
is serviced between I/O chunks. Memory pressure, a slow synchronous disk call,
long-line layout and encoding expansion remain separate risks to measure.

## Next controlled measurements

Keep exact executable/dependency/source hashes, corpus hashes and encoding,
OS/CPU/RAM/storage, configuration, clock metadata, failure/cleanup outcomes, and
all observations. Separate fresh-process startup from cold filesystem-cache
claims; repeated runs on a hosted runner do not provide a guaranteed cold cache.

The next diagnostic experiment separates native lexical transport, Ru keyword
styling without structural folding, and the full Ru policy. Reduced modes are
benchmark controls only. Compare recording-disabled, counters-only and sparsely
timed builds to expose instrumentation overhead. Count event-array allocation,
function environments, empty-stack paths, fold rows, GC, and main/child callback
root snapshots before selecting an optimization. Keep normal console and GUI
paths, complete output validation, and the existing 30-second GUI gate.

A later fixed-version Notepad++ comparison should use the same Windows runner,
identical plain/C++/JSON bytes and comparable visible configuration. Report
startup, open, save, editing, search, styling and memory separately, with repeated
paired trials and dependency-version differences. Notepad++ plain text is not an
equivalent task to Ru structural highlighting and folding. No same-runner
Notepad++ performance result is claimed yet.

## Completed direct-style paired experiment

The completed eight-row direct/message comparison is recorded in
[Windows run 38984124849](https://github.com/uppet/ru_notepad/actions/runs/38984124849).
`direct-style-benchmark.yml` is now a manual-only historical replay, with no
arbitrary ref input. It always checks out public 0.1.6 commit
`a5f5fd825767cd5af662cba792f5ce352991c21e`, tree
`e8a402fb3eb551bfe416b8aee0aaaf942d2d4f4a`, and runs that checkout's original
closed 120-source inventory and tools. Its artifact name identifies the built
commit separately from the triggering workflow run. The comparison retains
that candidate's initialization, DLL roots, resources and Ru lexical/fold policy. It does not modify the old profiler's
accepted source locks or substitute its historical 109-file proof for this
candidate. A closed candidate manifest records every accepted source identity,
every independently reviewed change, the current commit/tree, compiler identity,
all copied module graphs, generated C, executable and dependency hashes.

The fixed schedule has eight fresh processes on one real Windows x64 runner:
GUI direct, cooperative message, GUI message, cooperative direct, cooperative
direct, GUI message, cooperative message, GUI direct. Each path has two paired
repeats. Four binaries differ only in execution path and the single private
copied-source direct-route enable value. The message control preserves all new
initialization and GC roots; it selects the original SendMessage publication.
No phase/callback hooks or hot counters run in either measured binary. Only
2032/2033/2073 may use direct publication; fold publication remains messages.

Both routes contain the same complete-byte/style checker and endpoint-only
eligibility scaffold. Before the 1 MB target starts styling, and after it
finishes, the scaffold verifies registration, same owner thread and parent,
same document/generation, revision zero, mask 3 and a non-null native context.
The context is discarded immediately. Exactly two numeric receipts are required;
these are endpoint eligibility evidence, not a count or trace of every batch.
The separate native fixture must actually pass its positive/negative subclass
controls for all three style messages and its full text/style/fold/lifecycle
checks. The exact-DLL scanner and existing off-level native boundary controls
also execute. Missing, skipped, timed-out or killed runs fail the experiment.

Every matrix run retains the exact 1,000,000-byte corpus above and the unchanged
30-second styling limit. Both routes check every input byte and style byte. GUI
runs retain all six BOF/middle/EOF edit probes, actual queued navigation, natural
paint-region service, ordinary WM_CLOSE and exit zero without cleanup killing.
The initial eligibility queries are inside styling wall time; the final
eligibility and full-byte checks follow completion. Common verification roots
and setup overhead can affect both variants. There is no claim that this
scaffolding has zero overhead or that subtraction isolates it.

The report shows every exact pair, direct-minus-message milliseconds and ratio,
measured process seconds and process-minus-styling time. That final difference
includes setup, other probes, verification, edits and closing. It is not an
isolated checker cost. Missing or invalid process clocks fail; old missing
seconds are never inferred. No performance success threshold, statistical
significance or broad speedup claim is attached to two pairs. A fully correct
result showing no gain is valid evidence. Full product CI remains independently
mandatory and is not replaced by this experiment.

The completed twenty-row historical profiler is now manual-only. Dispatching
`ru-syntax-profile.yml` always checks out accepted public commit
`e3256f0453b3b11dd26b671f38628cf411ab24e8`, tree
`a9636c81716f0788baa4a8ba505319d51b3775bc`, and executes those historical tools.
This also works when the workflow is launched from current wip; it does not
attempt to run the old locked experiment against direct-style product sources.
Its artifact name identifies the built historical SHA separately from the
workflow run ID, and its source receipts use the actual checkout. Historical
whole-process elapsed omissions remain historical. The completed direct-style paired experiment
executed the reporting fixes and their fail-closed host controls.


## Same-run policy-prefix candidate comparison

`policy-prefix-benchmark.yml` is a separate wip-only experiment for 0.1.7. It
compares the current candidate with itself, replacing only the privately copied
`src/ru_lexical.ru` with one of two reviewed blobs:

- Baseline policy from the accepted 0.1.6 tree: SHA-256
  `f78589e247186890855526f7bb3624d34e4004bb8fbc69587c96d38c826a602c`
- Conservative empty-stack/pending prefix policy: SHA-256
  `deb5629333f2e76125b396bfe640b327ea6f1fd42f95f24277c86c5209fb12ec`

Both sides retain direct styling enabled, the same current initialization and
roots, pinned compiler, dependencies, resources and common byte/style checker.
Neither side selects the old message route. Both endpoint proofs require actual
direct eligibility, registration, owner/parent, document/generation, revision,
notification mask and native pointer validity. There is no product route or
policy setting. Structural decisions and the fallback event loop remain Ru.

The four GUI/cooperative-console × baseline/prefix binaries run in eight fresh,
interleaved AB/BA processes on the same real Windows x64 runner. They retain the
same 1 MB corpus and unchanged 30-second full-style limit. Every run requires
full byte text/style equality. GUI runs retain all six unequal 100 KB
start/middle/end edit probes, fold and dirty/undo checks, genuine queued
navigation, natural paint, ordinary close and exit zero. Before any matrix row,
the fixed native controls must pass: route 36 assertions; scanner 157 cases and
942 chunk checks; boundary first/second longjmp and trap-OOM counts 2/1/1.
Skipped, timed-out or cleanup-killed runs cannot count as success.

A separate closed candidate manifest verifies the accepted 120-file source
base, exact reviewed additions and changes, current commit/tree and compiler.
Every source map is compared with a canonical current graph, rather than merely
with its partner. The full loaded module closure is reconstructed, and each
pair must differ in exactly the reviewed lexical module. Identical unauthorized
changes in both graphs fail. Generation uses explicit UTF-8/LF, rejects linked
or hostile paths, and checks source drift before/after build and execution.

Evidence retains per-variant source, generated-C, binary/dependency and command
hashes, QPC observer details and full measured process seconds. Command digests
identify the fixed declared launch/build argv; successful command stage receipts
identify what ran. Public artifacts contain only schema-validated bounded JSON
and sanitized synthetic numeric logs, including early failure receipts. Raw
private build logs, generated C, executables and machine paths are not uploaded.
No profiling hot counters are introduced.

Reports show each prefix-minus-baseline duration and ratio, with process time
separate from styling time. Two pairs per path do not establish statistical
significance or a broad speedup. A correct result showing no gain remains valid
evidence. Linux policy microbenchmarks are not Windows end-to-end measurements;
no Windows performance result is claimed until the exact frozen candidate runs.
The separate full product CI and its 1,487 native assertions / 33 result groups
remain mandatory. This benchmark never grants product acceptance or upgrades
the delivered main/Library preview.
