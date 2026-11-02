# Stable line sorting and duplicate removal

Edit offers six explicitly scoped commands in all seven interface languages:
ascending sort, descending sort, and duplicate removal for **selected lines** or
for the **whole document**. Selected-line commands are disabled without a
selection; they never silently fall back to the whole document. No new editor
shortcut is assigned. A selection touches whole lines, except that an endpoint
exactly at the next line's beginning excludes that next line. Reverse selections
use the same range.

Sorting is stable, case-sensitive Unicode codepoint order. It is **not** natural
number order, Chinese pinyin order, locale collation, or Unicode normalization.
For example `A`, `a`, `a10`, `a2` is ascending. Combining and precomposed forms
remain distinct. Duplicate removal handles nonadjacent duplicates and retains
the first occurrence in original order. EOL style is not part of line identity.

## Exact line-ending policy

- Sorting moves only line contents. Every original separator remains in its
  original ordinal slot: mixed CRLF, LF and CR are not normalized.
- Duplicate removal retains each surviving line's own separator, except the
  last surviving line inherits the original range's last separator. This keeps
  the outer boundary and whether the file ended in a terminator unchanged.
- The virtual empty line after a final terminator is not a sortable record.
  Actual empty lines are records: `\n\n` deduplicates to `\n`, not empty text.
- A resulting join that would combine separate CR and LF separators into CRLF
  is rejected in full, before editing. A localized non-modal status explains
  that the user may explicitly unify endings first; the app never does so.

After a change the resulting content range is selected, excluding its final
separator, preserving selection direction. A caret-only whole-document command
creates a forward selection. No-op or rejected commands leave the original
selection, bytes, savepoint and undo history untouched. A change is one Undo /
Redo operation. Undo restores text, not a promise to restore the prior selection.
Encoding, BOM, Enter insertion mode and other tabs remain unchanged. There is no
implicit save.

## Bounded synchronous work

This first increment handles at most **10,000 real lines and 4 MiB (4,194,304
UTF-8 bytes) per affected range**, including separators. A larger range is
rejected before native buffers or line indexes are allocated, with a localized
status asking for a smaller selection. This is separate from the existing
32,000,000-byte/initial-large-file edit barrier. Readonly, busy I/O, modal,
close-transaction and tab-menu barriers remain enforced; rectangular and multiple
selections are rejected rather than reinterpreted.

The implementation is Ru-owned iterative stable mergesort over line indexes,
with native unsigned-byte `memcmp` and bounded byte copies. Valid UTF-8 byte
order matches Unicode scalar order. There is no per-character Ru scan, repeated
full-string slicing, quadratic duplicate search, clipboard use, or custom undo
stack. Worst-case comparison work is bounded by the selected bytes times the
logarithm of the line count; duplicate marking uses sorted adjacent identities
then emits survivors in original order. Owned source and result buffers remain
alive throughout all synchronous derived-pointer calls.

## Validation scope

Native actual-WM_COMMAND fixtures, actual executable menu operations, exact
save/Undo/Redo bytes, fresh-process reopening, localized menu/status checks and
resource-boundary timings are required candidate-specific gates. The original
line-operation, EOL, lexer/folding, extraction-fence and strict-package gates
remain mandatory. Portable contracts and Linux diagnostic timings alone are not
Windows application acceptance. See the source/tree/run/attempt-bound receipts
for the exact candidate actually validated. An asynchronous cancellable path for
larger ranges is future work, not an implicit relaxation of these limits.
