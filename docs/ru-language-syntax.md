# Ru highlighting and structural folding

`ru_notepad` 0.1.7 preserves a source-derived Ru lexical and folding policy in `src/ru_lexical.ru`, with a bounded application-internal C scanning hot path in `native/ru_scan.c` (`RuSyntax.dll`). The independent pure-Ru scanner remains the test oracle. Scintilla owns document/style storage; Ru supplies the exact keyword/style table and owns all structural pairing and fold decisions. This is not a renamed C, Python, or generic Chinese-keyword lexer. Ru highlighting does not depend on the optional Lexilla DLL used for C/C++ and JSON.

## Language baseline

The unchanged lexical/folding policy was derived from the Ru 0.21.3 language source (public baseline `dd6cb81b`). The build now pins Ru 0.21.6 for the generic owned-memory bulk-read transport; this dependency update does not change the policy rules below:

- `rulang/frontend.py`: `KEYWORDS`, `NUMBER`, `comment_marker`, `block_comment_end`, `lex`, and the `Parser` declaration, literal, reference, statement and expression rules
- `rulang/language-spec.md`: sections 2–4, including contextual scope/recovery delimiters

The complete reserved-word set is:

```text
显 取 为 得 完 破 若 则 另 然 循 次 环 算 作 法 其
且 或 非 空 真 假 典 成 对 形 象 如 新 外言 尽取 尽 试 救 卒
```

`数`, `句`, `阵`, and `事实` receive a type style. Protected built-in names, including `件`, `录`, `件作成果`, `读`, `读取`, `显出`, and `错误`, receive a separate built-in style. Library members remain ordinary names. `段`, `落`, and `终` are contextual names, not globally reserved keywords; their displayed style stays the ordinary-name style even when the structural scanner recognizes them as delimiters.

Names use the frontend's Unicode `isalpha()` start and `isalnum()` continuation rules, with `_` additionally allowed. A whole name is never split to color a keyword prefix. Non-BMP letters are supported; emoji and combining marks are not silently accepted as name characters. Decimal numbers follow the frontend pattern, including `.5` and signed exponents. Signs are operators. A trailing dot in `1.` is a statement terminator, not part of the number. This editing lexer identifies numeric spelling without attempting runtime numeric-overflow validation.

ASCII and Chinese full-width punctuation follow the exact frontend aliases. `:=` and `：=` require adjacent characters. Full-width arithmetic operators are not aliases. The four string pairs are `'…'`, `"…"`, `‘…’`, and `“…”`; actual line breaks are allowed. Only the language's eight escape spellings are accepted. An unknown escape is marked invalid while the surrounding string remains a string.

## Comments and incomplete input

- `#`, `//`, `批.`, and `批。` introduce line comments. They end at LF, exactly as the frontend does. A lone CR advances Scintilla's displayed line but does not end a Ru line comment.
- `解.` and `解。` begin a **non-nesting** block comment. The first exact `释.` or `释。` ends it, even inside quote-like text or after another `解.`. A closer does not require a name boundary.
- Chinese opening markers require a name boundary and an adjacent dot. `总批.`, `解释`, `1解.`, and `解 .` are not comment openers.
- Strings and comments never create keyword, brace, or delimiter folds from their contents.
- Unfinished strings, block comments, names, and headers remain valid scanner states. They do not throw parse errors while the user is typing. Malformed characters receive an invalid style rather than stopping highlighting.

The scanner is intentionally an editing policy, not a compiler or syntax validator. A colored document is not evidence that it parses or runs.

## Folding rules

The structural state recognizes the following actual Ru constructs:

- `若 … 则 … [另 …] 然`
- `循 [expression 次] … 环`
- Named and anonymous `算 … : … 法` and `作 … : … 为`
- `形 … 象`, including methods and function-valued field annotations
- `试 … 救 name … 终`
- Statement-position `段 : … 落 .`
- Symbolic `{ … }` scopes and dictionaries, plus `典 : … 成` dictionaries
- Multiline block comments

Parentheses and array brackets track expression context without being advertised as independent syntax folds. A one-line construct has no fold header. Closing lines return to the enclosing level. CR, LF, and CRLF have Scintilla-compatible physical line numbers; CRLF counts once.

A function type annotation or reference, such as `参数 为 算`, `回 取 算 函数.`, or `算 回 值:1.`, must not open an ordinary function fold. Untyped headers can be ambiguous with named reference calls. These frames are tentative until statement-only syntax proves a body or a matching closer establishes it. Expression boundaries cancel unresolved speculation before an enclosing dictionary, array, or parenthesis can be swallowed. For safety, a valid untyped callable whose first body statement is only a bare expression may have no callable fold. Highlighting remains accurate. Open, unambiguous blocks can fold while being edited; unresolved ambiguous prefixes do not advertise a fold header.

For a multiline callable, `段`, or `典` header, the fold body starts on the line containing its confirming colon. Earlier header lines remain visible. This conservative rule avoids buffering an unlimited parameter header or retroactively rewriting an unlimited run of previously scanned lines. Full multiline declarations are still recognized, and their bodies and closers nest correctly.

## Bounded incremental interface

### Production native transport

`native/ru_scan.h` defines ABI version `0x00010000`. All buffers belong to the caller. Configuration initialization validates and copies the Ru-provided vocabulary into a fixed-size configuration buffer. No native function retains an input pointer, document handle, callback, or Scintilla pointer. Checkpoints copy independent native lexical state and Ru structural state; temporary input/output buffers are not checkpointed.

One feed accepts at most 65,536 input bytes and returns at most 64 packed lexical events (two `uint64_t` words each), plus a raw per-byte style buffer. The bridge uses a smaller retained input window and an explicit input offset, so a capacity-limited batch does not reread the document. Result fields distinguish newly accepted input bytes from styled absolute bytes. Lookahead and partial UTF-8 carry total at most 16 bytes; names retain at most 16 scalars/64 bytes, never their whole text. `OUTPUT_FULL` preserves unaccepted input and always makes observable progress. Empty non-EOF input may wait for more text. EOF can be resumed after `OUTPUT_FULL` and repeated safely after completion.

The adapter takes one `读U32LE阵` snapshot of at most 256 words from its existing 1,024-byte event buffer per batch. The words retain the same ABI layout: low header, high header, length and line. It rejects a high header word of 131,072 or greater before combining an exact header below 2^49, then preserves all lexical bounds and ordering checks before policy dispatch. The API returns detached ordinary numeric arrays from live owned memory; it does not expose or dereference raw pointers. Native Windows application validation and same-corpus timing remain separate release gates.

Native events describe completed names, number/string starts, punctuation, block-comment boundaries and physical line ends. `批处理` consumes them through the very same `_记词` and `_行折` functions used by the pure-Ru oracle. Exact names are classified using `词表配置`; ordinary long names never generate a document-length correction. Styles are published in one `SCI_SETSTYLINGEX` batch, followed by bounded keyword corrections and Ru fold updates. Tentative-header cancellation explicitly repairs earlier header flags, preserving other constructs sharing the same line.

UTF-8 validation rejects NUL, overlong sequences, surrogates, values above U+10FFFF and incomplete EOF scalars. Bad input leaves the lexical state unchanged and clears the output descriptor except its error status. The bridge can abandon the pass safely. The C code performs no allocation, text edits, undo actions, file access or operating-system calls.

### Pure-Ru oracle and shared policy

The pure policy exports:

```text
新状态() -> opaque mutable state
扫描(state, textChunk, eof) -> result
复制状态(state) / 快照(state) -> independent snapshot
等价(leftState, rightState) -> exact context equality
字节数(textChunk) -> UTF-8 byte count
```

A chunk must contain at most 1,024 Unicode scalars and begin/end at scalar boundaries. This scalar API is retained for portable oracle tests; production uses the bounded byte transport above. A very long physical line is still processed in bounded work units. It must not pass a whole line or a whole document merely because it fits in memory.

The result contains:

```text
spans:  [absolute UTF-8 byte start, byte length, style ID] entries
folds:  [zero-based Scintilla line, nesting depth, header boolean] entries
bytes:  absolute byte position consumed by the scanner
line:   current physical line
carry:  unconsumed trailing scalar count, at most 4
scanned: scalars consumed by this call, at most input length + 4
```

All result arrays are bounded by the input chunk. A later short keyword correction may restyle an earlier byte range; a confirmed tentative body may update its earlier opener line. Apply events in returned order. Styling offsets are bytes, not Ru string indices, UTF-16 units, or display columns.

The native feed cursor and `bytes` are distinct: the scanner may retain up to four input scalars for lookahead. A checkpoint therefore stores the **feed cursor plus a copied state**, including that tail. Snapshot equality compares every state field and nested frame; it is not a hash or array-identity comparison. Replaying a snapshot gives the same styles and folds for the same input. An empty repeated EOF flush is harmless; feeding additional text to a finished state is rejected.

The state retains at most sixteen scalars of a name, a bounded lookahead tail, scalar lexical context, and 128 structural frames. Long names, comments and strings do not accumulate their contents. The scanner never concatenates the whole document or returns a whole-document token array. A structural-depth overflow or invalid API input raises an ordinary recoverable Ru error; the native layer can fall back safely rather than block the message loop. The application's existing 32,000,000-byte plain-text mode remains in force.

Style IDs are `0` plain, `1` comment, `2` string, `3` number, `4` reserved keyword, `5` type spelling, `6` built-in name, `7` punctuation/operator, `8` ordinary name, and `9` invalid character/escape. Internal numeric lexical and grammar tags are separate from these style IDs; `_语码` is their source-readable mapping.

## Unicode table provenance and regeneration

Both the pure-Ru endpoint payloads and `native/ru_unicode_data.h` were derived with Python **3.12.14**, `unicodedata.unidata_version == '15.0.0'`, from the very predicates used by the pinned frontend. They are data, not a Python runtime dependency. The module builds small pages of endpoint text rather than thousands of permanent pair objects, which also avoids the native ABI analyzer's alternative-value limit. Common ASCII and CJK fast paths are exact subsets of those tables.

To reproduce each endpoint payload using a Python 3.12 / Unicode 15.0 environment:

```python
import unicodedata
assert unicodedata.unidata_version == '15.0.0'

def endpoints(predicate):
    result = []
    start = None
    for codepoint in range(0x110001):
        matches = codepoint < 0x110000 and predicate(chr(codepoint))
        if matches and start is None:
            start = codepoint
        if not matches and start is not None:
            result.extend((chr(start), chr(codepoint - 1)))
            start = None
    return ''.join(result)

alpha = endpoints(str.isalpha)
alnum = endpoints(str.isalnum)
```

The payload for `_字母区` is `alpha`; `_字数区` is `alnum`. Preserve all code points exactly, without Unicode normalization. Both strings contain consecutive inclusive start/end pairs. Unicode attribution and the applicable data license are included in the distribution's third-party notices. Updating the language baseline or Unicode version requires regenerating the tables and rerunning the boundary fixtures.

## Verification

`tests/ru_lexical_policy.ru` executes the pure oracle and shared grammar policy directly in both the pinned interpreter and generated Linux C. It checks byte-exact styles, explicit fold levels, malformed editing prefixes, all comment forms, four quotes, escapes, Unicode boundary cases, contextual words, references, declarations, embedded anonymous functions, dictionaries, CR/LF/CRLF, snapshots and safe limits. Each small fixture is replayed with one-, two-, three-, five-, and thirteen-scalar chunk boundaries and compared with one-shot output.

`tools/test_ru_scan.py` checks C chunk/byte-boundary invariance, fixed event capacities, malformed UTF-8, state independence, canonical checkpoint equality and Unicode table parity. With `--ru-root`, it compares all final byte styles and line folds against the pure-Ru oracle in both interpreter and generated Linux C. `--sanitize` runs a separate ASan/UBSan random-buffer harness. `--library` validates the exact host-loadable DLL; Windows PE binaries are tested on Windows.

`tests/ru_syntax_native.ru` covers the real Scintilla container bridge separately. Pure policy tests do not prove Win32 message-loop latency, native styling, undo/dirty preservation, multiview isolation, or GUI interaction; those require the native acceptance run. Throughput and slice latency must be measured on the final native build without competing benchmark jobs. The scanner is asynchronous and bounded, but this is not a claim that a megabyte is colored instantly.
