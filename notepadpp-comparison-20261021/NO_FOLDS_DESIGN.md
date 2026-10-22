# Markdown Undo and styling, heading folding disabled

Predeclared diagnostic, not statistical performance acceptance. Product baseline
6aa535d62c28cc9a03f33c3610fe99b3cf1bd14e and compiler
85c7821fda35aa79deeaf67b4d430f24ddd7f07f remain unchanged. No dense-line candidate.
Reuse reviewed build/acquisition/seal/inventory/owned-process controls.

## Order and scope

One Windows job builds one fixed Ru binary and acquires the exact official NPP
8.9.8.1 package. Each fixture runs fresh isolated processes in this fixed order:
0 Ru Markdown with heading folds OFF; 1 official NPP preinstalled Markdown UDL;
2 identical Ru Markdown with heading folds ON. One repetition, no warmups/retries
or selection of favorable samples. First fixture is exactly 1,000,000 ASCII a
bytes; second is a fixed 14,208-byte Markdown sample with headings, emphasis,
inline/fenced code and list items. Both use byte 8 insertion x, byte 9 backspace,
and native Undo until clean (one or two natural groups, never forced boundaries).

30 seconds per stage and 120 seconds per owned process are unchanged. Failure or
uncertain cleanup stops subsequent arms. Censored observations are not speeds
and never enter ratios. No machine-independent conclusion from old runs.

## Real disabling, no product patch

Once the opened buffer identity is established, Ru's actual menu command 507
invokes 设置折叠(false). The source replaces the state, sets policy=null and
foldEnabled=false, expands existing folds, hides the margin and completes the
visibility-only task. Subsequent SCN_MODIFIED creates a disabled, nonpending
revision with null policy: no policy feed or fold publication. Lexilla remains
Markdown lexer 98. Initial opening can have done folding before command 507;
opening and disable/visibility work are preparation, **not compared open times**
and not included in edit/Undo action times. Their original deadline still applies.

Initial proof requires a newer terminal MDP2 identity with feed=published=0,
heading-folds-off status, no warning, lexer 98 and automatic folding=0.
Subsequent disabled revisions deliberately have length=-1 and do not publish a
fresh MDP2 marker. Do not claim fresh per-edit internal counters: proof combines
unchanged pinned source, official command, each round's off/no-warning status,
unchanged document pointer and lexer, and native automatic folding=0.
Native visibility cleanup is not fold-policy computation. State allocation,
notifications, scheduling/status work and native Lexilla styling still exist.

## Timing and highlighting proof

Every natural Undo round reports time from that command dispatch separately:
first matching length/dirty/four-byte edit context, first full SCI_GETENDSTYLED
plus representative styles, and final joint mode/identity/response proof.
For normal Ru the joint proof also waits on a fresh completed fold MDP2 revision.
A single Undo grouping is reported as such, never invented as two.

Ru off/NPP poll at 5 ms; normal Ru preserves the established 250 ms low-intrusion
poll to avoid known observer starvation. All times are first-observable upper
bounds, not internal timestamps or rendered-frame measurements. Difference in
polling resolution is explicitly in schema4; do not describe a difference as
pure fold CPU cost. Normal-arm style time is separate from its joint fold-ready
time, but is still sampled at 250 ms.

The all-a fixture checks head/tail styles=0. Real Markdown additionally requires
nondefault heading/emphasis/code styles, then matches each product's own initial
sampled style vector after every edit/Undo. Full endstyled is mandatory. Native
styles are product-specific: Lexilla and UDL are **not equivalent highlighters**.
No forced colourise, plugins, global input or pointer-bearing cross-process IPC.

## Publication

Add only runner, closed numeric/hash validator, tests, this design and independent
.github/workflows/markdown-no-folds.yml on notepadpp-comparison. Existing workflow,
history, product sources and main/wip are untouched. Upload only validated
no-folds-result.json, never private paths, logs, runtime, executable or receipts.

## Observer revision 5: heading probe correction

Run 39748675377 at c0ccd2a passed all three 1 MB arms, then failed the
14,208-byte fixture's initial nondefault-style assertion. No Markdown-fixture
edit ran. Preserve that run and all original 1 MB observations; do not select
between reruns or treat this harness failure as a performance timeout.

Pinned official Lexilla 5.5.4 defaults lexer.markdown.header.eolfill to 0. Its
SetStateAndZoom styles the heading marker but leaves Heading text default. A
local native TestDocument probe against archive-hash-verified official sources
observed byte 18 (#)=6, byte 20 (Heading)=0, byte 40 (strong)=2 and byte 54
(code)=19. Observer revision 5 changes only the heading probe from byte 20 to
18, retaining strict nondefault styles for heading marker, emphasis and code.
No product property, fixture bytes, timing budget, order or repetition changes.
The complete fixed six-process plan is rerun, not a best-of 1 MB sample.

## Observer revision 6 / schema5: supplemental real-Markdown-only plan

Run 39750935369 at 03d0362 passed 1 MB Ru-off and NPP UDL, then the normal
folding arm's two-Undo stage hit its unchanged 30-second deadline. Its second
Undo was acknowledged, but joint completion was not established. Preserve that
censored result; do not retry 1 MB or choose favorable timings. Fail-stop meant
none of the real-Markdown fixture arms ran.

The supplemental workflow explicitly passes --fixture real-markdown. This selects
only the unchanged 14,208-byte fixture, followed by all three fixed arms once,
under the same 30/120-second bounds and fail-stop. Its purpose is to close the
unexecuted nondefault-style/folding-disabled proof, not replace earlier evidence.
CLI default --fixture all still selects the original [0,1] fixture plan. Schema5
records fixture_plan=[1] for the supplement, or [0,1] for that original plan.
No product, compiler, imported harness, fixture bytes, probes, style requirements,
observation timing, native messages, cleanup or provenance logic changes.
