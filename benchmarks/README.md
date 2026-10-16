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
