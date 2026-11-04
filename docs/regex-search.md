# Bounded regular-expression find

Choose **Search > Regular expression (case-sensitive)**, enter a pattern in the
existing find box, and use Next/F3 or Previous/Shift+F3. **Literal search** remains
the default. Switching back restores the literal Match case and Whole word
choices. Regex mode fixes exact case, disables Whole word and all replacement
controls, and rejects direct replacement and Find All in Open Documents commands.
There are no new keyboard shortcuts. An empty query only shows/focuses the bar;
it does not compile, search or enter history.

This increment searches the current live document or an explicitly captured
selection, including unsaved and read-only buffers. The selection keeps its
existing sticky invalidation rules: edits, tab changes and bar closure do not
silently change the scope to the whole document. Search history remains bounded,
in memory only, and selecting an entry does not execute it. Successfully compiled
nonempty patterns enter find history; rejected syntax does not.

## Deliberate dialect

This is a small Ru-owned engine, not Boost, PCRE, JavaScript, Scintilla REGEXP or
CXX11REGEX compatibility. It matches Unicode scalar values, returns exact UTF-8
byte ranges, and performs no case folding, normalization or grapheme segmentation.

Supported syntax:

- Literal scalars, escaped regex metacharacters, and `\n`, `\r`, `\t`.
- `.` matches one scalar except CR or LF.
- Positive/negative classes and ordinal ranges, such as `[a-z]`, `[^0-9]` and
  `[汉-龥]`. Categories `\d`, `\w`, `\s` and their uppercase complements are
  ASCII-only. `\w` is letters, digits and underscore; `\s` is space, Tab, LF,
  vertical Tab, form feed and CR. A Unicode digit is not automatically `\d`.
- Structural groups `(...)` and `(?:...)`, alternation `|`, and greedy/lazy
  `*`, `+`, `?`, `*?`, `+?`, `??`. Groups have no captured-output API.
- `^` and `$` are always multiline against actual document boundaries and
  CR/LF/CRLF separators. They never match between CR and LF of one CRLF.
  `\A` and `\z` mean absolute document start and end.

Unknown escapes, backreferences, lookaround, inline flags, Unicode properties,
counted repetitions `{m,n}`, and possessive repetitions are rejected with a
localized error and a one-based scalar position. They are never silently treated
as literals or delegated to an unbounded native engine.

An unbounded `*` or `+` whose body can match empty is also rejected, including lazy
forms: `(a?)*`, `(|a)+` and `()*` are invalid. This avoids ambiguous empty-loop
priority semantics. Nullable nonempty patterns such as `()`, `^$` and `a?` remain
valid. `?` over a nullable group is allowed.

## Match order, boundaries and zero-length progress

Next uses prioritized leftmost-first matching. Alternation preserves written
order: `(a|ab)` matches `a` in `ab`, while `(ab|a)` matches `ab`. Greedy and lazy
operators preserve that priority even when a failed higher-priority path has read
past the final accepted end. Navigation uses the accepted range, not the furthest
read position.

Previous enumerates the same **nonoverlapping forward matches** within its search
leg and returns the last. It is not a rightmost-overlapping search: Previous for
`aba` in `ababa` returns bytes 0–3, not 2–5. Each match must fit entirely before
the Previous caret ceiling. Next starts at the selection end; Previous starts at
its beginning, regardless of anchor direction.

Captured bounds and caret/wrap legs limit consumed text, but do not create new
`^`, `$`, `\A` or `\z` boundaries. Chunk edges likewise have no regex meaning.
Wrapping makes at most one additional leg inside the current scope. After a
zero-length match, repeating the same direction skips that exact result for the
entire invocation, including wrapping. Progress advances one Unicode scalar,
including CR and LF separately. At the sole position of an empty document, a
repeated zero-length searches keep ending with no match instead of looping; an unchanged no-match does not forget the last zero result. Explicit query, scope, direction or caret changes reset that progress.

## Work and resource limits

Compilation is iterative and limited to 256 pattern scalars, at most 1,024 UTF-8
bytes, 512 emitted states, 16 nested groups, 64 class ranges and 32,768 charged
operations. Matching uses an iterative prioritized Thompson/Pike state machine,
not recursive backtracking or a whole-document string. A native text copy is at
most 256 bytes plus separately bounded neighbor-scalar reads.

A 20 ms timer schedules cooperative work. Each slice shares at most 4,096 VM
microsteps, 8,192 combined work units, 2,048 copied bytes and 16 bridge phases.
The entire search, including retries, Previous enumeration and wrapping, has a
67,108,864-work-unit limit. Previous enumeration can rescan suffixes, so its total
cost is not claimed linear. Limits mean **incomplete search**, never “not found.”
No provisional match is selected when a limit, error or cancellation occurs.

**Stop regex search**, changed query/options/scope, typing, Undo, manual caret
movement, tab changes and closing the bar cancel pending navigation. Every native
read and final navigation rechecks current document identity, editor identity,
revision, byte length and invocation selection. The job retains no raw editor
pointer. Reading preserves Scintilla target/search flags, text, Undo and savepoint.
Allocator and operating-system latency are not bounded by work counters. Allocation failure has not been fault-injected; source cleanup review is not execution evidence. Large or
complex searches can be slow; no throughput guarantee is claimed.

## Acceptance and remaining scope

Portable contracts do not establish Windows behavior. Required preview gates add
365 pure policy assertions and 41 native bridge assertions to the existing 2,366
stage3 assertions, and run the actual executable through 29 byte-range cases,
10 rejected patterns, 15 interruption flows, real input/Stop responsiveness,
limit-without-navigation, fresh-session privacy, and seven-language layout checks.
The response deadline is 2 seconds; the intentionally exhausting limit scenario
has a separate 900-second terminal deadline. Existing product gates remain required.
Only exact-source Windows receipts and verified package hashes establish delivery.

The compiler remains pinned to ru-language c3bb177. The application's preexisting
200,000-step default C analysis exhaustion is still disclosed separately. The
explicit 2,000,000-step development ABI oracle is not a production C build, native
execution or Windows acceptance. The preview application must still be built by
its actual stage3 LLVM path.

Regex replacement/capture expansion, all-open-document regex, folder search,
Unicode-aware categories/case folding, counted repetitions and full Notepad++
regex parity remain out of scope.
