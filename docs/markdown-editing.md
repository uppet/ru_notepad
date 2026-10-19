# Markdown editing: Stage A, 0.1.8 preview candidate

This stage provides `.md` / `.markdown` detection, Language > Markdown, native Lexilla syntax colors and heading-section folding. It does not implement Enter continuation, a renderer, HTML preview, or a full CommonMark parser. Windows acceptance of this reconstructed candidate is pending.

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

## Fold-publication regression work

The next Windows run passed all 1,818 console assertions, all four many-line operations and all four single-line operations (including the two-Undo phase in 27.50 s). The 1 MB unclosed-fence open phase still exceeded 30 s. It had no final probe, so that record alone does not identify its precise stopping point; the three following edits were not reached.

Source inspection found that each published line sent `SCI_FOLDLINE(Expand)` (2237), which traverses fold children, may request native styling, and refreshes scrollbars and painting. Preparation already calls `SCI_FOLDALL(Expand)`, resets every line's visible/expanded state, and disables automatic folding. All application fold actions reject pending scans, and edits replace the task before starting preparation again. Publication therefore no longer repeats the per-line expansion. This removes an incidental synchronous styling request; the original natural-paint, style-sample and three-corpus GUI gates remain required.

Each remaining `SCI_SETFOLDLEVEL` mutation retains a complete owner/thread/HWND/document/length check before and after it. Within one bounded publisher call, a completed post-check also serves as the next mutation's pre-check, with only built-in range/cursor arithmetic between them. No proof is carried across another native/reentrant call, a timer step, an exception or a return. The final post-check and status check still precede cursor completion. This contract assumes all document replacement, editing and folding follow the application's existing owner entrypoints; an external subclass issuing unannounced document or visibility changes is outside it.

The publisher now requires a prepared pending Markdown scan and still publishes at most 64 lines per call. Native regression fixtures require old nonheader and header expanded bits, hidden lines, new/removed headers, user collapse after completion, pending-action refusal, and post-mutation query/last-write invalidation. These are additional gates, not Windows results; complete acceptance remains pending.
