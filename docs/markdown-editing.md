# Markdown editing: Stage A, 0.1.8 preview candidate

This stage provides `.md` / `.markdown` detection, Language > Markdown, native Lexilla syntax colors and heading-section folding. It does not implement Enter continuation, a renderer, HTML preview, or a full CommonMark parser. The delivered seven-language baseline passed Windows acceptance in run 39395780914. Its 100,000-line double-Undo case still took about 20.7 seconds; further performance work remains separate. The later sections retain the historical investigation record.

## Editing controls

Use the fold margin or View > Collapse all folds / Expand all folds (Ctrl+Shift+[ / Ctrl+Shift+]). View > Toggle Markdown heading folds switches folding off per document while retaining syntax coloring. Disabling folds restores visible text; re-enabling queues a fresh scan. Plain text remains available in the Language menu. Language and fold commands do not edit source, clear undo, reset savepoints or change encoding/EOL choices.

Newly opened Markdown paths select the mode automatically. Untitled documents remain Plain until a manual choice or successful Save As to a Markdown suffix. Save As continues through the existing safe asynchronous writer. Tabs retain their own fold option. Options are in memory only; no session persistence is claimed.

## Separate coloring and folding rules

Lexilla 5.5.4 supplies its existing Markdown coloring dialect. It is not a CommonMark validator and does not provide native Markdown folds. Its ATX/coloring and fence rules can differ from the independent fold policy. The Ru policy recognizes conservative top-level ATX and multiline setext headings and suppresses structural markers in fenced code, indented code, selected HTML blocks and ambiguous container regions. It may omit otherwise valid headings. The [policy contract](markdown-policy-subset.md) lists exact accepted and excluded forms.

## Bounded work and ownership

Edits invalidate the current task and restart folding from byte zero. One task retains a six-entry-at-most heading stack, scalar paragraph state, one short UTF-8 chunk and at most 64 compressed ranges. It does not retain the full document or a per-line checkpoint array. Reads are at most 1024 bytes on a UTF-8 boundary; publication advances at most 64 lines per batch, including long retroactive setext ranges. Completion is reported only after EOF and the last publication range drain.

The shared scheduler admits roughly 8 ms slices. This cannot preempt one Scintilla call: native coloring may look ahead through a long line, and native FoldAll/ShowLines can traverse many lines. Actual Windows latency must be measured for single-line, fenced and many-line input. No hard 8 ms latency guarantee is claimed.

Each task belongs to its HWND, native document, thread, generation and text revision. Reads and publication check ownership around synchronous messages. A stale task cannot publish or run failure cleanup against a newer document. The application must invalidate before replacing a document or destroying its window. This does not make an arbitrary external subclass swapping the document while forwarding that same mutation safe.

On an ordinary failure, folding is disabled, a warning is exposed, and guarded visibility recovery is attempted. Recovery cannot promise to override a concurrently replaced or destroyed owner. Text, undo and dirty state are never deliberately rewritten by folding.

## Large files and verification

Files at least 32,000,000 bytes use the existing Plain/no-wrap/styles-none streaming path. Files larger than 500,000,000 bytes still require consent before body reads. These thresholds are not file-size ceilings.

The new portable policy and extension fixtures execute real Ru code. Native fixtures exercise actual Scintilla fold metadata, reentrant invalidation, text/selection/dirty/undo preservation, language changes and streamed large-file fallback. GUI acceptance uses bounded style samples and fold/status/length probes, source hashes, real navigation and paint, and a 30 s phase deadline. A sampled GUI probe is not a full-document style equality proof; native small-fixture comparisons cover complete text and fold levels. All runtime claims await those Windows results.

## Initial coloring regression

The initial Windows GUI check exposed a cleared-style lifecycle bug: after selecting Markdown, `SCI_CLEARDOCUMENTSTYLE` zeroed the style bytes and advanced Scintilla's styled prefix to EOF. With no subsequent Markdown keyword/property invalidation, ordinary painting skipped the lexer. Selection now uses the existing ownership-guarded `SCI_STARTSTYLING(0)` to invalidate that prefix; it does not synchronously colorize the whole document. The native fixture separately requires hidden mode reinitialization to leave the prefix invalid before message pumping, an ordinary message pump to paint the colored heading without `SCI_COLOURISE`, and stale initialization to leave a replacement document untouched. The older explicit-colorize assertion remains a lexer-output check. The repaired product still requires complete Windows native and detached GUI acceptance.

## Scan-cost regression work

The subsequent Windows run confirmed natural Markdown coloring and all four many-line GUI operations. It also exposed a test counter that included the replacement document's legitimate EOL setup and a 1 MB single-line, two-Undo phase exceeding the unchanged 30 s deadline. The lifecycle test now counts only the stale style-prefix mutation it is meant to forbid.

The policy avoids five closer-suffix checks except on `>` and avoids a redundant whole-chunk byte-count pass. The original 1024-scalar limit still runs before state access; each scalar contributes at most four bytes, and the consuming loop still accounts for every actual byte. UTF-8 validation, scheduling and ownership checks remain required. Boundary and full-state comparisons cover these optimizations; complete Windows acceptance, including the unclosed-fence shape, remains required.

The next policy revision indexes local windows of at most 32 Unicode scalars instead of repeatedly indexing the entire input chunk. A feed that begins inside a fence, outside HTML, contains a line ending and contains no `>` can defer transient line-text construction after that line is proven unable to close the fence. Original line transitions still run. Pending characters are replayed before any actual `>` and before EOF or return, preserving all public state fields and retained closer-flag aliases. Other feeds use the original scalar transitions with the same local windows. The input/range limits, UTF-8 byte accounting, folding rules, bridge ownership guards and scheduling budgets are unchanged. Twenty-two additional policy assertions bring that fixture to 221 and the native product total to 1,981 across 39 groups.

The preceding Windows run passed all 1,959 native assertions but the unclosed-fence two-Undo GUI stage exceeded its original shared 30-second deadline. Each real undo requires its own completed scan. Local policy comparisons do not establish whole-application Windows speed; the new policy must run the same three GUI shapes and unchanged deadline.

## Fold-publication regression work

The next Windows run passed all 1,818 console assertions, all four many-line operations and all four single-line operations (including the two-Undo phase in 27.50 s). The 1 MB unclosed-fence open phase still exceeded 30 s. It had no final probe, so that record alone does not identify its precise stopping point; the three following edits were not reached.

Source inspection found that each published line sent `SCI_FOLDLINE(Expand)` (2237), which traverses fold children, may request native styling, and refreshes scrollbars and painting. Preparation already calls `SCI_FOLDALL(Expand)`, resets every line's visible/expanded state, and disables automatic folding. All application fold actions reject pending scans, and edits replace the task before starting preparation again. Publication therefore no longer repeats the per-line expansion. This removes an incidental synchronous styling request; the original natural-paint, style-sample and three-corpus GUI gates remain required.

Each remaining `SCI_SETFOLDLEVEL` mutation retains a complete owner/thread/HWND/document/length check before and after it. Within one bounded publisher call, a completed post-check also serves as the next mutation's pre-check, with only built-in range/cursor arithmetic between them. No proof is carried across another native/reentrant call, a timer step, an exception or a return. The final post-check and status check still precede cursor completion. This contract assumes all document replacement, editing and folding follow the application's existing owner entrypoints; an external subclass issuing unannounced document or visibility changes is outside it.

The publisher now requires a prepared pending Markdown scan and still publishes at most 64 lines per call. Native regression fixtures require old nonheader and header expanded bits, hidden lines, new/removed headers, user collapse after completion, pending-action refusal, and post-mutation query/last-write invalidation. These are additional gates, not Windows results; complete acceptance remains pending.

### Bounded phase diagnostics

The later fold-publication run passed 1,832 console assertions but still timed out while opening the unchanged 1 MB unclosed-fence corpus. It had no final style probe. A missing final probe alone does not identify whether opening, scanning, fold publication, native styling or layout was responsible.

The CI-only `--markdown-phase-diagnostics` switch now projects existing numeric state into the status control with at most one additional status write per 250 ms and a shared 4,096-record process cap. If an identity completes within a reserved slot, its already-required final status refresh attaches one current-identity terminal record without another message or timer. This also replaces an existing pending record of that same identity. Repeated completed refreshes reuse the terminal record; if the shared cap prevents renewal, the stale pending record is withheld. Normal launches do not enable this output. The existing observer status read parses a fixed `MDP2` schema; there are no extra observer messages or document-text reads. Partial snapshots preserve only bounded numeric fields and closed status categories, never status prose, paths or typed content. Missing or malformed diagnostics cannot satisfy the GUI completion gate, and a diagnostic exception latches a fixed failure rather than reporting success.

Fields are sequence, origin (`via=0` for a periodic sample, `via=1` for an existing completion refresh), state identity, generation, revision, phase, pending, document byte length, bytes fed, published-line cursor, and the existing process-cumulative tick/work/gap counters. Phase codes are 0 (prepare), 1 (scan), 2 (queued fold ranges), 3 (visibility cleanup), and 4 (no pending fold work, including disabled folding). A phase is a sampled remaining-work category, not a measurement of time spent in that phase. Sequence and counters are process-cumulative, not per-operation totals. The completion-refresh record uses the preceding completed tick totals because the current callback has not yet committed its totals; it does not invent a sample timestamp or advance those counters. A cached sample can lag while work is pending; GUI completion requires a terminal numeric marker together with the original style/fold/context/status/visibility requirements.

The diagnostic uses the scheduler's existing QPC result. Its additional status write and slightly larger status read have real cost: the write occurs after the existing work counter is sampled, so its cost is in GUI wall time and the next in-burst gap when one exists. A final write after the timer stops has no subsequent in-burst gap. This is bounded diagnostic overhead, not a zero-overhead profile. The original 8 ms work budget, 10 ms timer, all three corpora, style expectations and 30 s per-operation deadline are unchanged. Thirteen native diagnostic controls bring the required console total to 1,845 across the same 38 product results; actual Windows phase evidence is still pending.

## Current acceptance exception (2026-10-27)

The earlier unchanged-deadline statements above describe historical experiments.
The user has now retired exactly the 1 MB unclosed-fence serial two-Undo folding
case from blocking/default acceptance and requested a TODO for later optimization.
It is not a pass or a performance fix. All other active stages, source/style/fold
correctness and UI checks remain required at their original limits. See
[the exact deprecated case, retained failure and TODO](bootstrap-llvm-preview.md#deprecated-case-and-todo-2026-10-27).
