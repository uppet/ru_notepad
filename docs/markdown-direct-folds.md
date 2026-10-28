# Bounded Markdown bulk fold publication

This is a candidate optimization. Windows product acceptance and its three
original Markdown workloads remain required. It does not add Enter continuation
or a rendered Markdown preview.

## Evidence and scope

The completed [eight-process callback study](markdown-callback-cost.md) showed a
20.688% median reduction in its callback-present publication/check loop with the
accepted compiler, together with a 3.007% no-callback median regression. The full
product still exceeded the 30-second unclosed-fence deadline. Its final bounded
sample had scanning and publication incomplete; that sample does not by itself
attribute individual costs.

The existing publisher sends three Scintilla messages per line: SETFOLDLEVEL,
GETDOCPOINTER and GETLENGTH. Those ordinary messages all enter the application's
file-drop subclass. The candidate keeps the compressed ranges computed by Ru, then submits at most
64 line assignments in one typed call to the private RuSyntax.dll bulk helper.
The helper uses the named Scintilla_DirectFunction export for fixed getters and
fold writes inside a prepared, explicitly owned batch. It does not remove the
file-drop subclass or alter the callback runtime. A per-line direct route remains
a source-only test comparison, not an independently shipped intermediate fix.

Reading each old fold level before writing is not the proposed first-open fix:
Scintilla's default level is 1024, while the unclosed-fence body requires 1025.
Those rows genuinely need changing. Scintilla already suppresses notifications
when an assigned level is unchanged.

## Internal ownership capability

The ordinary API retains the message route by default. Only the application's
closed editor-creation/selection paths can opt in: an editor created from the
pinned Scintilla DLL, one private unshared document, the controlled UI parent and
thread, and the reviewed file-drop subclass as its only application hook.

This is an internal owner promise, not detection of arbitrary external hooks.
GetWindowSubclass can verify a particular callback and identifier; it cannot
prove that no other subclass exists. A caller adding a user-observable hook,
sharing a document or installing a custom document watcher must revoke the
capability first. Unknown or unregistered editors use ordinary messages. The
application currently has no document-sharing or arbitrary-hook installation
path.

Selection, forgetting, document replacement and destruction invalidate the old
capability. Same-document text edits replace the scanner revision synchronously;
a valid owner qualification can carry forward only for that same document and
generation, and preparation runs again. A stale batch is rejected, never replayed
against a replacement through fallback.

## Closed native segment

The fixed Scintilla 5.6.7 implementation was reviewed, including Document::SetLevel,
Editor::NotifyModified, RedrawSelMargin, the Windows rectangle implementation and
macro recording. The direct route requires automatic folding exactly zero and
the existing text-only modification mask exactly three. It never changes either
setting to make an otherwise ineligible editor qualify.

For an exclusive document these conditions exclude FoldChanged and synchronous
parent notifications for a fold-level change. The remaining work updates fold
metadata and invalidates a rectangle without synchronous painting. A shared
watcher would invalidate this argument, which is why a mask check alone is
insufficient.

Each publication batch still has at most 64 line assignments. It validates all
ranges, verifies the live capability and obtains GETDIRECTPOINTER through the
ordinary message route. After that potentially reentrant query, it rechecks
ownership and directly verifies document, length, mask and automatic-fold state.
Only then can any direct write occur. Non-stale eligibility failures select the
original message route before the first mutation, after a fresh full guard.

The pointer remains a native opaque PTR/IP value, never an ordinary floating
Ru number. It is local to one batch, is not saved in scanner state, and is
abandoned before status queries, recovery or return. The binding is the exact
named export from the absolute pinned DLL, with a strong managed library owner.
All calls use the existing typed native ABI and error propagation.

Before and after the single bulk call, Ru checks the complete capability and
scanner identity, generation and revision. The native helper checks window,
current thread/process, parent, exact class module and HWND extra-byte context
before dereferencing a direct pointer. Each mutation retains native pre/post
checks of that identity, document, length, line count, configuration and status.
The fixed implementation cannot enter application callbacks within this segment;
therefore Ru state cannot change between those outer checks. This conclusion
requires the closed ownership contract above, not merely a notification mask.

The helper is application-private. Its versioned wire plan has a 32-byte header
and at most 64 sixteen-byte ranges (at most 1,056 logical bytes). A separate
32-byte result reports status, attempted and completed assignments, diagnostic
cursor and Scintilla status. Ru owns both typed buffers for the complete call
and closes them on normal and error exits. The helper retains no pointers,
allocates no heap memory, and copies the bounded plan to its stack. It contains
no Markdown parser, heading recognition, task scheduling or range generation.

All header fields, capacities, reserved fields, range bounds, cursor bounds and
integer additions are validated before the first mutation, including unused
ranges beyond the current 64-line slice. Distinct aligned caller-owned buffers
are required; declared capacity checks are not a promise to safely dereference
arbitrary unreadable pointers. Native pointer values never pass through ordinary
Ru floating-point numbers.

An assignment is attempted immediately before SETFOLDLEVEL and completed only
after the post-guard and zero native error status. A failed call may already
have changed its last line: the diagnostic cursor is never resumed or replayed.
Only a validated successful result advances the Ru scheduler. Stale ownership,
malformed plans and native errors follow existing invalidation/visibility
recovery. Missing helper ABI, or a validated zero-attempt prewrite configuration
ineligibility, may select ordinary messages after a fresh complete Ru guard.
A partial or uncertain write can never take that fallback.

The existing generic mutation guards, cancellation/restart rules, 1024-byte
scanner bound, 64-range queue and 8 ms admission budget remain in force. Native
calls are not preemptible; no hard per-call responsiveness guarantee is added.

## Required verification

The original text, style, fold, visibility, expanded-state, selection, savepoint,
dirty, undo, close and document-switch assertions remain mandatory. The new
native fixture must additionally prove that the bulk route actually executes,
compare its complete results with the ordinary and per-line direct routes, and
exercise acquisition-time edits, revocation, mode/configuration changes, document replacement and
closure before any direct write. Unknown-hook cases must retain observable
ordinary messages. A generic fallback test alone is not proof of direct safety.

All three detached GUI workloads retain their exact style/content probes and
30-second limit for every opening and editing stage. No end-to-end improvement
is claimed until that exact candidate completes real Windows acceptance.

## Bounded measurements

The CI-only bulk metrics introduced in MDP2 (retained in current MDP3) retain its existing four-per-second cadence
and terminal refresh behavior. It adds identity-scoped actual bulk calls and
completed rows, fallback batches, per-line direct calls/rows, logical plan size,
and measured bulk-call microseconds. QPC failures mark the measurement invalid;
they cannot become fabricated zero-cost samples. Timing includes the typed call
and immediate result wrapper, with per-call microsecond rounding. It is not a
CPU hotspot profile. No document text or paths are included in these fields.

The maximum owned buffer capacity is 1,088 bytes per bulk invocation, distinct
from its logical plan size (at most 1,056 bytes). Closing the typed buffers ends
the borrowed lifetime; actual managed allocation reclamation follows the normal
collector. These sizes are not a process-memory measurement.

During existing GUI observer snapshots, a separate read-only query on the owned
child process handle samples its current working set and OS lifetime peak. The
receipt distinguishes the maximum sampled current value from the cumulative
process peak, records query time, and rejects API failure. This adds low-frequency
observer work; stage wall times include it. It does not establish an allocation
peak between samples or a causal memory difference against another CI run.

The native fixture keeps the original 61 assertions and adds bulk-specific ABI,
partial-failure, ownership, three-route full-state and metric controls, for 114
assertions. Complete product acceptance requires 1,959 assertions in 39 groups,
the bounded C helper's real Windows controls, and all original GUI deadlines.

## Separate native baseline and profiler capability

The same Windows job separately attempts a small C host baseline with the exact
product Scintilla/Lexilla DLLs and fixed unclosed-fence corpus. It reports explicit
full colouring, predetermined fold-level writes, and a native-host read/setup/
load/style/fold/forced-client-paint pipeline as separate measurements. The last
item is not the application's full open workflow. Process startup, DLL loading,
output verification and teardown are outside those timers; filesystem caches
are not cleared. See [the native baseline contract](markdown-native-baseline.md).
These optional diagnostics run after product acceptance and cannot change its
original result or turn an incomplete study into a successful measurement.

An independent read-only check can identify the installed, Microsoft-signed
Visual Studio profiling tools and hash their low-frequency CPU configuration.
It never launches a profiler or application, starts a session or changes system
settings. The currently documented PID attachment and 1–255 session identifiers
do not establish the required collection scope and partial-start ownership
contract. Therefore its result remains `profile_unavailable`, including when
the tools are installed. This is not an actual CPU hotspot profile; that request
remains open. No raw profiler trace is collected or uploaded by this candidate.
