# Manual C++ growth measurement

Select only `syntax_growth_diagnostic` in workflow_dispatch. This separate job
has its own concurrency suffix and never produces a
runtime/test/preview ZIP. Normal product acceptance now requires 144 syntax assertions; this optional
measurement never replaces them. The diagnostic cannot certify a release.

The owned native program compares case 1 (the exact 22-byte failing fixture with
an empty final line) with case 2 (the same function followed by `int padding;`,
34 bytes, placing EOF on a visible base-level code line). They share one editor/document, fully reset by the production text setter and
language selection between cases. Both append real
1 MiB chunks 32 times in one undo action. Neither overrides fold levels.

Output is only fixed-case integer measurements, in `GROWTH case stage item value`
format. Stages: 0 selected, 1 collapsed, 2 first chunk appended, 3 all chunks
appended, 4 margin expansion attempted, 5 single undo, 6 collapse after undo.
Items: 1 byte length, 2 document options, 3 header expanded state, 4 packed
header level, 5 body line visibility, 6 all-lines visibility, 7 EOF-line
visibility, 8 EOF-line packed level, 9 last child (only at stage 1 because this
query can style), 10 modified state. Item 11 records each named stage's API
result; at stage 5 it records exact text restored. Stage 4 items 12 and 13 record
a second margin toggle and expand-all. Values are measurements, not substituted
acceptance assertions. The runner requires the complete fixed measurement set.

Pinned Scintilla 5.6.7 source gives a testable cause: `Editor::AppendText` calls
`Document::InsertString`; `NotifyModified` calls `NeedShown` before inserting
when any lines are hidden; automatic SHOW calls `EnsureLineVisible` on the EOF
line. Fold-compacted trailing blank lines can therefore expand their ancestor
before insertion. The Windows measurements below confirmed this source-derived mechanism. `Document::Options` is determined by immutable buffer
large-document/style settings, not the changing byte length.

No production source or existing top-level test source changes are included.
The compiler remains pinned and build.py checks full source/dependency hashes.
The standalone diagnostic entry has its own entry hash in its receipt. Final
repair still requires all original Windows functional acceptance assertions.

## Measured result and retirement of the one-shot trigger

Windows run 39365371547 completed both real cases (artifact 12238349495).
Case 1 folded through line 3, hiding EOF; the first append expanded the header
and body while options stayed 256. Case 2 folded only through line 2, leaving EOF
visible; it stayed collapsed after all 32 chunks, then margin expansion made
all lines visible. Both single undos restored exact clean text and folding.

This confirms native SHOW behavior, not a production folding defect. The normal
syntax fixture now uses visible code at EOF for threshold-growth recovery, and
adds separate assertions for the original hidden-EOF automatic expansion.
The one-shot push predicate has been removed from both workflow and runner.
All push/PR events, including the former diagnostic title, run normal acceptance.
Only the explicit manual input can run this optional measurement job now.
