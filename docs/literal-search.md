# Literal search, captured selection and session history

F3 / Next searches forward from the end of the selection. Shift+F3 / Previous searches backward from its start, irrespective of anchor direction. The Search menu exposes both commands. A match selects complete UTF-8 text and reveals folded endpoints; an unsuccessful search leaves selection, text, undo and savepoint unchanged. Empty patterns focus the search bar rather than searching. No shortcuts were reassigned.

Match case, Whole word and Wrap around retain their defaults: case-sensitive, not whole-word, wrapping enabled. Options remain application-wide for this run, including across tabs and search-bar closure; none are persisted. Whole word uses pinned Scintilla 5.6.7 native word-character rules, not dictionary-based Chinese/Japanese segmentation. Literal Unicode is not normalized. No regex or escape syntax is enabled.

## Explicit scope

The default is **current document**. Select one nonempty continuous text range, then choose **Search > Find in captured selection (no replace)**. The bar labels this mode **selection — find only**. This captures fixed UTF-8 byte boundaries; selecting each result never recaptures or shrinks them. Rectangular, multiple, empty and split-UTF-8 selections cannot be captured. Attempting an invalid capture discards any previous valid capture.

Next/Previous and optional wrapping stay inside those boundaries, including after manually moving the caret outside them. The initial selection remains intact at capture, so Next initially starts at its end and requires wrapping to return to its first occurrence; Previous starts at its beginning. With wrapping disabled, place the caret within the range to search from that position. Cross-line literals are supported by the search engine; this increment does not add multiline input controls or an escape language.

Any text edit (including undo/redo), switching tabs, or closing the search bar invalidates the capture. Returning to the old tab, reopening the bar, or selecting a history item does **not** restore it. The visible **scope lost** state blocks F3/Previous; it never silently searches the whole document. Explicitly capture a fresh selection or choose **Search current document** to continue. Closing/reopening the document likewise cannot revive an old capture. UI language changes and mere selection changes do not invalidate it.

**Selection-scoped replacement is not implemented.** Both replacement buttons are disabled in selection/invalid scope, and direct command dispatch is also rejected. Read-only documents allow searching but reject replacement. Busy/modal admission barriers remain in place. Selecting current-document scope explicitly restores normal replacement only for writable text.

In document scope, Replace checks the complete current selection against the case/whole-word options, replaces an eligible match and advances; otherwise it only finds the next match. Replace all scans the entire current document once, does not revisit inserted text, and retains its existing single undo group. It never edits another tab or disk file. No selection-only replacement or batch replacement is claimed.

## Private, bounded history

The Search menu has separate find-text and replacement-text histories, each holding at most 12 exact, case-sensitive most-recently-used entries **in memory for this process only**. Executing a valid nonempty search records its query even if it has no match. Allowed replacement commands also record replacement text, including an empty value for deletion. Rejected commands and empty queries are not recorded. Inputs longer than 1,024 Unicode scalar values still search normally but are not collected into history.

Choosing a history item only fills its corresponding input. It does not execute a search, change the document or scope, or clear an invalid capture. Menu previews are bounded and escape control characters and ampersands; the underlying value is preserved exactly. **Clear search history and inputs** clears both lists and both text boxes. No query or replacement history is written to preferences, registry, session files or disk.

## Acceptance boundary

The bootstrap preview requires all previous native/GUI gates plus native bounded-search/MRU/lifecycle assertions and a real-menu Windows search-scope gate: exact Unicode selections and saved bytes, fresh-process reopen, scope invalidation, replacement isolation, history limits/privacy and seven-language labels. Portable checks are contracts, not Windows execution. The editor-native fixture is now included in bootstrap execution, rather than relying on the separately blocked default-C application route. Source-bound receipts establish actual results and counts.

Regex, extended escapes, cross-file search, selection replacement, disk batch replacement and durable history remain out of scope.
