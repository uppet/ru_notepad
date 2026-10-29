# Markdown Stage A heading-fold subset

This policy was reconstructed against Ru 0.21.6; the current reproducible build uses the exact Ru 0.22.1 pin in [build provenance](build-provenance.md). It is not a byte-for-byte restoration of earlier files or evidence. The production folding policy is `src/markdown_policy.ru`; its portable fixture is `tests/markdown_policy.ru`. Syntax coloring is a separate concern. No renderer or Enter behavior is implemented here.

## Streaming contract

- `新状态()` returns a fresh state for a scan beginning at byte zero. Restart from byte zero after edits. There are no per-file line arrays or checkpoints.
- `喂入(state, text, final)` accepts at most 1,024 Unicode scalars and 4,096 UTF-8 bytes. Rejecting an oversized input does not mutate the state.
- The result has `folds`, `used`, `line`, `bytes`, and `finished` keys. `used` is the number of consumed input scalars; `bytes` is the cumulative consumed UTF-8 byte count; `line` is the current zero-based physical line.
- `folds` contains at most 64 ordered assignments `[startLine, count, depth, header]`. Later assignments replace earlier assignments over overlapping lines. Depth is 0–6. A true header always has count 1. False-header adjacent equal-depth assignments are compressed.
- A call may consume only a prefix. Drain its result, then submit the unconsumed input suffix. If all input was consumed but `final` was true and `finished` is false, call again with empty input and `final=true`. EOF is finished only after the final physical line has been published.
- A compressed range can cover an arbitrarily long paragraph. The native bridge must keep a cursor and apply a bounded number of lines per UI callback. Expanding an entire result range immediately would violate the scheduling contract, even though policy memory stays bounded.
- Repeated empty final calls after completion return no assignments. New input or a non-final call after completion is rejected.

The retained state has 24 slots: scalar offsets and flags, one paragraph start line, one six-entry-at-most heading stack, at most 32 prefix scalars, at most 11 rolling suffix scalars, and five HTML-close flags. No complete physical line or paragraph text is retained. Input and each returned output batch are separately bounded. A long physical line produces no assignments until its line ending or EOF.

CR, LF, and CRLF are accepted, including a CR/LF pair split across calls. A trailing line ending creates a final empty physical line, matching the editor's line model. Structural recognition uses ASCII markers, spaces, and tabs; other Unicode is opaque text. UTF-8 byte accounting supports 1–4-byte scalars.

## Recognized structure

- Top-level ATX headings: 1–6 consecutive `#` after 0–3 spaces, followed by an ASCII space, tab, or line end. An opening tab or four leading columns makes a line opaque.
- Top-level setext headings: a contiguous eligible paragraph, potentially many lines, followed by a nonempty uninterrupted run of `=` or `-`, with only trailing ASCII spaces/tabs, indented at most three spaces. The paragraph's first line becomes the header. Remaining title lines and the underline become child lines.
- Heading depth follows the actual active heading stack, not skipped numerical levels. An H3 directly under H1 has fold depth 1. A same- or lower-level heading closes the prior active heading(s).
- An ATX line is initially a non-header. It becomes a fold header only once subordinate content exists. A paragraph that might become a setext heading does not prematurely confirm the previous heading. Empty consecutive sibling headings therefore do not gain misleading fold headers.
- Fenced code: backtick or tilde runs of at least three characters, after at most three spaces. A closer must use the same character, be at least as long, and contain only trailing ASCII whitespace. A backtick fence opener with a backtick in its info suffix is not accepted as a fence. Unfinished fences remain opaque through EOF.
- HTML comments and `script`, `pre`, `style`, and `textarea` blocks are opaque, including the closing line. Tag matching is ASCII case-insensitive. Literal matching close sequences are recognized across chunk boundaries. Unfinished blocks remain opaque through EOF.

## Deliberately conservative exclusions

This is not a CommonMark parser. It may omit valid folds; unsupported constructs must not be presented as fully parsed Markdown.

- Quote and unordered/ordered list starts suppress heading recognition in their container region, including lazy continuation text. The policy exits this suppression at a zero-column ATX heading, or at a zero-column non-container line immediately following a blank boundary. An intervening suppressed nonblank line consumes that boundary. Indented list headings remain suppressed even after a blank line. Ordered markers recognize at most nine ASCII digits and `.` or `)` followed by whitespace or line end.
- Four leading columns, including any leading tab, are opaque. When encountered inside a pending paragraph, they suppress its continuation until a blank/zero-column-ATX boundary. The policy does not implement CommonMark's paragraph-continuation exception for indentation.
- Unknown `<...` starts are conservatively opaque until a blank line. Their HTML block-category rules are not fully parsed.
- Paragraph lines beginning with `[`, backslash, `=`, `-`, `*`, or `_` are ineligible for setext conversion unless the line itself is a recognized underline for an already eligible paragraph. Their entire ambiguous paragraph continuation is suppressed until a blank/zero-column-ATX boundary, avoiding a false shifted header on a later line. This also applies to invalid backtick-fence-like paragraph starts. Reference-definition title continuations and ambiguous punctuation/thematic-break forms are therefore not promoted to headings.
- Inline emphasis, links, escapes, HTML inline syntax, extension syntax, container nesting, and renderer semantics are not interpreted. No folds are opened for fences, lists, HTML blocks, or inline constructs.

## Fresh portable validation

Set `RU_ROOT` to the exact pinned Ru 0.22.1 compiler checkout, then run both paths from the application repository:

```
python "$RU_ROOT/ru" run tests/markdown_policy.ru
python "$RU_ROOT/ru" build --cc gcc tests/markdown_policy.ru -o build/markdown_policy_linux
build/markdown_policy_linux
```

The fixture checks explicit expected assignments, six fixed chunk sizes, every two-way scalar split for each small fixture, mixed line endings, Unicode, raw blocks, container exclusions, delayed headers, and retroactive multiline setext conversion. Resource fixtures cover a 65,536-scalar / 262,144-byte single line, a 4,096-line paragraph producing two retroactive ranges, output-budget partial consumption, maximum-size valid input, invalid-input atomicity, and idempotent EOF. Test-only maps expand results for assertions; production does not.

These tests do not establish Windows GUI behavior or performance. The separate native bridge and Windows smoke evidence are required for those claims.
