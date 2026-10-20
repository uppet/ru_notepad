# Manual C++ growth measurement

Select only `syntax_growth_diagnostic` in workflow_dispatch. This separate job
has its own concurrency suffix and never produces a
runtime/test/preview ZIP. Normal product acceptance and its 138 syntax assertions
are unchanged. The diagnostic cannot certify a release.

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
before insertion. This remains a hypothesis until the Windows states establish
which conjunct failed. `Document::Options` is determined by immutable buffer
large-document/style settings, not the changing byte length.

No production source or existing top-level test source changes are included.
The compiler remains pinned and build.py checks full source/dependency hashes.
The standalone diagnostic entry has its own entry hash in its receipt. Final
repair still requires all original Windows functional acceptance assertions.

## One-shot diagnostic trigger

Until the Windows measurement is obtained, the exact commit message
`测量自有折叠增长夹具状态【诊断20261020】` on a `push` to
`refs/heads/wip` selects this diagnostic alone. Other push messages, non-case-equivalent refs,
and every pull request keep the full normal acceptance matrix. An added newline
or suffix does not match. This one-shot alternative is needed because the
available publisher has no workflow_dispatch operation. The subsequent formal
repair must remove the one-shot predicate; the explicit manual input may remain.

GitHub expression equality ignores string case. The chosen Chinese/digit title
has no case variants. The ref expression can match a case-variant branch; the
first script guard uses strict Python equality and fails before measurement if
that happens. Such a same-title case-variant push fails closed instead of running
the normal matrix. This limitation is accepted for the verified existing
`refs/heads/wip` target; no case-variant branch is created. The runner repeats the
guard before building and cannot publish successful measurements on rejection.
