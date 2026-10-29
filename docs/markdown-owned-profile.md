# Owned Markdown phase study (diagnostic only)

This candidate does not change product policy, compiler pin, native DLL, 30-second acceptance limit, or runtime ZIP inventory. It adds an isolated diagnostic job containing one same-source release/profile pair. Ordinary feature push/PR builds do not run it. Its result is diagnostic and never certifies product acceptance.

## What is measured

Eight nested generated-body/native/callback wall intervals, four exact attempted-entry counts, outermost timer-thread user/kernel CPU, and inter-root QPC gaps. Every count belongs to the innermost measured phase. Valid exclusive wall ticks sum exactly to outermost timer ticks. This is not per-phase CPU, sampling, or whole-process CPU hotspot attribution. The runner separately reports whole scenario wall and whole owned-process CPU.

The root starts at the body of main.ru::语法时钟. Its initial caller argument binding, outer callback preparation, final callback cleanup and inter-root GUI work remain outside that root. Six selected generated bodies are preserved intact under private names and wrapped: five phase wrappers and the `_一步` progress observer wrapper. Native error capture stays immediately adjacent to its original native invocation. Panic, longjmp recovery or failed callback entry invalidate the study permanently; no profile or runtime stack is repaired.

The profile is bounded to eight aggregates, 32 frames, fixed counters and a scalar JSON record. It observes only one exact 1,000,000-byte synthetic unclosed-fence document (100,001 physical lines), one identity/generation/revision, complete feed, EOF and fully drained ranges. No document contents or native document pointers are retained in the report. This first pair measures initial full-document loading, not the repeated Undo acceptance scenario. It identifies initial scan costs; any conclusion about the remaining dual-Undo delay requires a subsequent matched edit/Undo measurement.

## MinGW thread ownership

MinGW GCC's ordinary __thread uses emulated TLS and is unsuitable for the no-call/no-allocation hot-counter contract. The private x64 profile uses a loader-owned PE TLS template, the actual TLS directory's raw-data base, and the current thread's TLS vector. Initialization validates directory bounds. Unsupported ABIs fail compilation. It never reads a foreign thread or process. Actual Windows normal/foreign-thread controls must pass before launching the GUI study; cross-compilation alone is not runtime proof.

## Commands

Host controls:

    python tools/test_markdown_owned_profile.py --cc gcc

This runs Python transform/owned-process controls and the actual C header with injected clock/thread/error tests. On Windows it additionally compiles and runs two fresh native TLS control processes. The actual generated-state observer is compiled and exercised during study preparation.

In the existing Windows native acceptance workflow, manually dispatch with markdown_owned_profile=true (default false). It cannot be combined with historical_callback, syntax_growth_diagnostic, i18n_focused_diagnostic, or i18n_window_diagnostic, and is restricted to refs/heads/wip. The earlier exact commit-title push exception `诊断：测量七语第八版 Markdown 分阶段耗时` is retired. All pushes now run normal full product acceptance. The retained manual diagnostic stays independent; retiring the exception is not a claim that its measurements passed. The workflow and script both enforce the event/ref guard. Its concurrency group has an owned-profile suffix so a manual diagnostic cannot cancel a feature-acceptance run. The independent job builds unchanged product inputs, runs host and Windows TLS controls, and invokes:

    python tools/run_markdown_owned_profile.py --ru-root .ci/ru-language --binary-dir build/markdown-owned-profile/bin --evidence-dir build/markdown-owned-profile/measurements --cc <gcc.exe> --windres <windres.exe>

The build helper checks the pinned clean compiler, all receipt inputs, exact regenerated product C/TU, original runtime hashes, selected source/name/body mappings and native call/error-read adjacency. The profile TU/EXE and copied reference runtime stay in a fresh private directory outside the product inventory. Only the strict numeric/hash projection markdown-owned-profile.json is uploaded after complete temporary-file write, flush/fsync and an atomic no-replace publication. Original receipts, source maps, exceptions, build output and process logs remain private to the runner. Unknown strings or dynamic fields cannot enter the public projection.

## Ownership, limits and interpretation

Each freshly launched application has one absolute 120-second deadline covering discovery, load, ordinary timer progress, bounded probes and shutdown. Cleanup uses only its retained Popen handle; it does not attach to or terminate unrelated processes. There is no global profiler session, WPR, suspended thread or debug privilege.

The unchanged launcher can write beyond 64 KiB between checks. Overflow invalidates the study immediately when detected; only a confirmed-exited owned log may be capped afterward. Unconfirmed cleanup or retained-output bounds are explicitly reported. No fallback Temp-log search is permitted.

Both variants use the same synthetic input, native DLLs, ordinary tail-styling request, bounded head/tail probes, polling cadence and environment snapshot. A single serial pair measures observed overhead, not a calibrated constant or confidence interval. Instrumentation can change 8 ms admission decisions and timer counts. Never subtract the pair's overhead from individual phases or use the profile for the 30-second acceptance gate.

## Local verification status

Portable transform/runner controls, actual C observer controls, actual-header arithmetic/reentrancy/error/longjmp controls and MinGW cross-compilation are available. Real Windows TLS control execution and the GUI release/profile pair remain pending until the independent candidate is reviewed and run in CI. Linux policy timings do not establish Windows end-to-end improvement.
