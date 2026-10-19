# Markdown callback and root-snapshot comparison

## Current status

This bounded research revision uses the accepted Ru 0.22.1 compiler, public
commit `85c7821fda35aa79deeaf67b4d430f24ddd7f07f`, tree
`a770e367e84d87a0d2fcb6d49ea6f06da2dbe4ba`. Its
[language CI](https://github.com/uppet/ru-language/actions/runs/39229099554)
passed all 13 jobs, including the ten new root-index regressions on all three
Windows/Python versions. The product pin is updated to that exact compiler.
Application acceptance and the eight-process comparison are still pending;
language acceptance does not establish application performance.

The complete Windows product acceptance remains separate and mandatory:
1,845 original console assertions, 38 result groups, all three Markdown corpora,
and the original 30-second limit for each initial/edit stage. Research executables
are private build products and never enter either user ZIP.

## Evidence motivating the comparison

[The four-process Windows experiment](https://github.com/uppet/ru_notepad/actions/runs/39218747010)
used exact application source `8e9e9c80146b7ae29c5336e7f643226014533c9e`
and the then-current product compiler
`a2f6faa0f914781dea74cb6f0a7574f1dd6808ce`, tree
`7b4331d51bc6ab2ec95fec1f8368465343fcd5af` (Ru 0.21.6).
The two subclass-present publication samples were 19.797315 and 19.879784 seconds;
the subclass-absent samples were 11.220830 and 11.449661 seconds. Actual entries
into the production file-drop callback were 310,947 in each present sample and
zero in each absent sample. One instrumented PE and identical dependency bytes
were used for all four fresh processes. Every functional proof passed.

The difference between medians was 8.503304 seconds. It includes native dispatch,
callback protection, the Ru callback body and the small counter instrumentation;
it does not identify any individual component's Windows cost. The timed loop also
includes the fixed per-batch checks. The original product still failed its
one-million-byte unclosed-fence open stage at the unchanged 30-second limit.
The research was successful; product acceptance was not.

Private host-only attribution using an existing portable native-test adapter
found whole-heap snapshot traversal to be a strong cost when many heaps had few
transient roots. Those host measurements motivated a separate language change;
they do not establish the Windows application's heap population or speedup.

## Controlled eight-process design

The application graph, fixture, corpus, native dependencies, compiler flags,
publication code, ownership checks and expected results are identical in both
compiler builds. The old research compiler is public commit
`95ee638f705f0fd75292da7eda150559dbe8fc3a`, tree
`f4c871d89e26c8eef03fd901f8f9aa0ad4d7e354`. Its only comparison partner may be the
separately reviewed Ru 0.22.1 root-list revision identified above. In particular,
this does not compare all intervening language changes against Ru 0.21.6 and
attribute the difference to root snapshots.

Eight fresh processes use this fixed balanced order:

1. Old compiler, subclass present
2. New compiler, subclass present
3. New compiler, subclass absent
4. Old compiler, subclass absent
5. Old compiler, subclass absent
6. New compiler, subclass absent
7. New compiler, subclass present
8. Old compiler, subclass present

Each compiler uses one instrumented PE for its four processes. The two PE hashes
are recorded separately and checked before and after every process, as are all
three dependency DLLs. Compiler checkouts, production sources and the complete
loaded module graph must match their exact recorded identities throughout.
Generated C must differ only by an independently reviewed finite set of exact
runtime replacements and the separately identified compiler-version banner.
Unrecognized differences, including changes to the emitted application body,
fail the comparison. No broad runtime stripping or wildcard normalization is used.

The no-subclass samples are important: maintaining a transient-root index can
add work to ordinary root transitions even when there are no callbacks. Report
all four cells and both repetitions, including any regressions. Two repetitions
per cell support a controlled observation, not a broad statistical guarantee.

## Preserved workload and proofs

Only the benchmark-owned editor has its production file-drop subclass removed
and restored. `GetWindowSubclass` checks the exact callback pointer, identifier
and parent reference. The initial editor's route is checked independently. User
application callback behavior is not changed.

The exact one-million-byte unclosed-fence corpus is processed by the unchanged
policy. Its 979 emitted ranges are checked and adjacent equivalent ranges are
coalesced into three ranges without changing the 100,002 ordered assignments to
100,001 physical lines, including the first line's retroactive header update.
Publication uses the unchanged 64-assignment bounded publisher and all guards.
This isolates publication and guard cost. It does not reproduce timer scheduling,
interleaved policy feeds or natural paint at every instant of the GUI workload.

Reversible generated-C hooks count actual entry to the production file-drop
callback and read the counter from a fixture-only stub. Overflow and inexact
integer conversion invalidate the run. For each successful batch of N
assignments, measured callback entries must equal `3*N+7` in present mode and
zero in absent mode. No callback, error, longjmp, GC-root, LastError or ownership
protection is bypassed by the research instrumentation.

Coarse QPC timing surrounds publication and its fixed-size checks, including two
counter reads per batch. There are no per-event clock calls. Complete final text,
every fold level, visibility, expanded state, dirty/savepoint state, selection,
undo/redo, route restoration and teardown are verified outside the timed loop.
Every state check and final proof is mandatory for all eight samples.

## Resource and observation bounds

Based on the prior four-process total of 123.453 seconds, eight-process execution
is expected to take roughly four to five minutes. This is an estimate, not a
performance promise. Each process retains a 120-second deadline; all eight share
a 960-second execution deadline, including launch and validation. Each compiler
build has separate emission/resource/compilation bounds of 120/30/180 seconds.
A 1,680-second aggregate research deadline bounds the complete research stage.
These limits do not change any product deadline.

The parent samples process memory with
[GetProcessMemoryInfo](https://learn.microsoft.com/en-us/windows/win32/api/psapi/nf-psapi-getprocessmemoryinfo)
at most four times per second, identically for both compiler groups. The
[extended counters](https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-process_memory_counters_ex)
separate working set, private committed memory, and their available OS peaks. Sample counts and
observer duration are recorded. A sample exceeding the fixed 512 MiB acceptance
bound is rejected and its owned process tree is stopped. These are observed
private/working-set and OS peak counters, not an OS allocation cap: polling has a
bounded reaction interval and cannot prevent every transient allocation.
There is no Job Object, system-memory setting, process-priority change or new
permission. The observation has nonzero overhead and is not subtracted from the
measured results. At the two already-existing counter reads per publication batch, a fixed scalar
hook also samples the existing `ru_live` count. It performs no heap traversal,
allocation or clock query. A non-timed reset excludes initialization; non-timed
getters report the exact sampling count, sampled peak and `sizeof(RuHeap)`.
Both compiler builds use identical hooks. The sampled live count is not a proof
of the true instantaneous peak. The layout difference multiplied by a sampled
live count is only an estimate of extra object-header storage; allocator rounding,
other allocations and working-set accounting mean it is not the measured RSS
difference. Memory and runtime-layout evidence are reported separately from
elapsed-time observations.

## Pipeline and evidence

The existing Windows workflow runs this research before ordinary product
acceptance with both fixed compiler pins and the reviewed generated-C comparison.
A research failure retains bounded failure metadata and still attempts
the full product tests. Either failure makes the workflow unsuccessful.

Public evidence contains fixed-schema numeric results, digests and validated
synthetic output. Compiler output, generated C, local paths and unexpected native
diagnostics remain private. A missing sample, failed cleanup, extra output,
changed source, unknown compiler, exceeded resource bound or failed functional
proof rejects the entire comparison. The final report must distinguish observed
research results from the independent full product GUI outcome.
