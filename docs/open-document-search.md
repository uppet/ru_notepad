# Find All in Open Documents

The Search menu searches every currently open buffer, including unsaved changes and unnamed documents. It does not reread disk files, open directories, or replace text. The query is literal and uses the existing native case-sensitive and whole-word options; regex and escape modes are not implemented. Queries must contain 1–1,024 Unicode scalar values. Empty or longer queries leave earlier results unchanged.

## Results and navigation

A separate results panel shows a bounded document name and path, a process-unique document number, one-based line number and escaped text preview. Double-click a row, select it and press Enter, or use Go to result to activate the owning tab, reveal folded endpoints and select the exact match. Merely collecting or selecting a list row does not edit or reposition document text.

Find All records its query in the existing session-only search history. Results and previews stay in memory and are not persisted. Clear search history clears the existing search inputs/history; closing results cancels pending work and hides the panel. A new valid Find All replaces the previous job and results. No new global shortcut is assigned.

## Snapshot safety

The job snapshots document identity, revision and length. Text changes, including undo/redo, or adding/removing a document invalidate the job and its results. Closing and reopening a file cannot revive old offsets, even if Windows reuses a handle. Changing the active tab does not invalidate this all-document job. Every tick and every navigation independently validates the live document set before touching native handles. Stale results are labelled and cannot navigate; rerun the search.

## Bounded work and explicit incompleteness

The UI timer requests one step every 20 ms, with at most 65,536 bytes of candidate starting positions and 16 result rows per step. Native matching has bounded overlap so literals crossing a chunk boundary are found. Case-sensitive search uses 4,096 bytes of overlap; native Unicode case folding requires 12,288 bytes. These are work limits, not a guarantee of a specific input/frame latency on every computer.

At most 2,000 non-overlapping results are retained. Reaching that limit explicitly marks the output incomplete. Stop keeps valid partial results and labels them incomplete; close results also stops the job. Failures and document changes never appear as a completed search. Large files with no matches are searched incrementally rather than copied into one large Ru string.

## Acceptance boundary

Portable contracts, source-bound native fixture execution and actual Windows GUI cases are separate evidence. Required cases include Unicode and case folding, cross-chunk matches, mixed EOL, dirty/unnamed/read-only buffers, duplicate names, exact result navigation, cancellation/restarts, cap/truncation, stale edits/close/reopen, seven-language layout and all earlier product regressions. This document describes the candidate contract; only the final exact-source CI receipts establish passing execution.

Directory search, regular expressions, cross-document replacement and persistent search history are deliberately outside this increment. There is no tab-reorder UI in this candidate; the native fixture tests document-order permutation. Native allocation-failure injection is not claimed as executed GUI coverage.
