# Markdown publication callback experiment

This is a bounded research test, not a product change or a relaxed acceptance
gate. The normal Windows acceptance still requires every existing test and each
original 30-second Markdown stage. The research program is not distributed in
either user ZIP.

The compiler is the unchanged application workflow pin:
`a2f6faa0f914781dea74cb6f0a7574f1dd6808ce`, tree
`7b4331d51bc6ab2ec95fec1f8368465343fcd5af` (Ru 0.21.6).

## Why measure this path

The diagnostic run at public source `133623e26ec13e294a5fac16bf28d7194d16bfea`
reached 607,232 scanned bytes and 60,623 published fold assignments before the
one-million-byte unclosed-fence open stage reached its 30-second deadline. The
last sample was pending scan work with queued fold ranges. This establishes
unfinished scan/publication work, but does not identify its underlying cost.

Separate Linux experiments of the unchanged policy and a mocked native bridge
took about 5.1 and 5.5 seconds respectively. Those measurements exclude real
Win32 callback dispatch and are not predictions of Windows elapsed time. Small
private pure-Ru experiments saved less than half a second in the policy stage
or about ten percent in the mocked bridge. They are not part of this candidate.

Every normal editor has the production file-drop subclass. Even an unrelated
Scintilla query passes through that Ru callback before `DefSubclassProc`.
The experiment measures the cost of this actual route while retaining the
complete application module graph, the original publisher, and its guards.

## Controlled comparison

Four fresh processes use one instrumented research executable in interleaved
subclass-present / subclass-absent order. Only a benchmark-owned editor has its
production file-drop subclass removed and restored. The test verifies the
callback pointer, subclass identifier, and parent reference with
`GetWindowSubclass`; it does not replace the callback with a simplified one.

The exact one-million-byte unclosed-fence corpus is processed by the original
policy. Its 979 emitted ranges are checked and only adjacent equivalent ranges
are coalesced. The resulting three ranges preserve all 100,002 assignments to
100,001 physical lines, including the first line's retroactive header update.
Publication still uses the unchanged 64-assignment bounded publisher. This
isolates publication and guard cost; it does not reproduce timer scheduling,
the interleaving of policy feeds, natural paint, or the original live heap at
every instant.

A minimal generated-C instrument counts entry into the actual production
file-drop callback. The same counter code is present in both modes. It does
not change native dispatch, root snapshots, LastError capture, allocation, or
the callback's Ru body. Strict source/AST matching must identify exactly the
expected function and the fixture's counter-read stub. Unknown shapes fail
closed. Counter overflow or an inexact numeric conversion invalidates the run.
Counting adds a small branch and integer increment on callback entry. It is not
zero-cost instrumentation; the installed-route result includes that overhead.

For every successful batch of N assignments, the subclass-present route must
record exactly `3*N+7` callback entries; the absent route must record zero.
This is an assertion against actual measured entries, not a substituted
estimate. A callback failure before the counted function body would fail the
research process and cannot produce an accepted sample.

Coarse QPC timing surrounds publication and its per-batch validation, including
counter reads. No per-event clock calls are added. Both modes retain that
measurement overhead. Complete final text, fold levels, visibility, dirty and
selection state, and undo behavior are checked outside the timed publication.
The recorded experiment does not promise a general speedup or a safe production
fast path.

## Bounds and evidence

Each of the four executions has a 120-second process deadline; all four share a
480-second execution deadline including launch and validation. Build limits are
separate. These are research bounds and do not replace any product deadline.

The existing Windows workflow runs the research before ordinary product
acceptance. A failed research run leaves a failed, bounded receipt and does not
skip the product tests. Either failure makes the workflow unsuccessful. Public
research evidence contains fixed numeric/schema fields, digests, and validated
synthetic output only. Compiler output, paths, generated C, and unexpected
runtime diagnostics remain outside the uploaded evidence directory.

Both modes must complete normally with identical functional results before any
timing comparison is accepted. Windows execution and useful attribution remain
pending until the actual CI evidence has been reviewed.

This research revision requires its exact public parent and unchanged production
source bytes. The Windows checkout fetches two commits for that comparison. A
later production revision must explicitly retire or separately review this
research entry instead of silently accepting a different application graph.
