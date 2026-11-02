# Current/selected whole-line editing

Edit offers **Duplicate current/selected lines**, **Move current/selected lines
up/down**, and **Trim trailing spaces/tabs in current/selected lines**, in all
seven interface languages. Only menu access keys are added; no new editor shortcut bindings are assigned. Sorting and
removing duplicate lines are not part of this increment.

Without a selection these commands affect the caret's current line. With a
stream selection they affect all touched whole lines; a high endpoint exactly
at the next line's start excludes that next line, in either selection direction.
Trim removes only ASCII space and Tab at those lines' ends, not indentation,
Unicode spaces, or whitespace elsewhere. Select All explicitly opts into
whole-document trimming. Rectangular/multiple selections are rejected unchanged.

## Byte and selection rules

- Duplication inserts a whole copy after the selected block. Internal CRLF/LF/CR
  terminators are copied exactly. A terminated block uses its own last terminator
  between original and copy. An unterminated final block uses the previous line's
  terminator, or the independent Enter mode if it starts at the first line; the
  copied last line remains unterminated. Duplicating the terminal empty logical
  line adds a matching terminator. An entirely empty document is a no-op.
- Moving swaps a selected block with its adjacent real line. For original bytes
  `A + S + B`, the result is `B + S + A`: `S` is the original boundary terminator,
  while each block's internal terminators stay with that block. The terminator
  after the swapped range is untouched. Thus mixed endings are not normalized,
  and whether the document ends with a terminator is preserved. Moving past the
  first/last real line does nothing. The empty logical line created by a final
  terminator cannot be moved or crossed.
- After duplication or movement, the newly copied/moved block's content is
  selected, excluding its final terminator; the original selection direction is
  preserved. A caret-only invocation creates a forward selection. Trim uses
  Scintilla's ordinary position adjustment. Undo/Redo restore text, not a promise
  to restore the earlier user selection. Unicode codepoints are not split.

Each changing command is one Undo/Redo operation and respects the existing
savepoint. Empty/no-op commands do not create empty undo records. Encoding, BOM,
Enter insertion mode and other tabs are unchanged; there is no implicit save.
Readonly, busy I/O, modal, tab-menu and close-transaction barriers apply. Commands
are rejected for initial large-file mode or current buffers of at least
32,000,000 UTF-8 bytes. Duplication is also rejected if its resulting size would
reach that threshold. Existing large-file opening/saving and the 1 MiB
compatibility text-extraction fence remain unchanged.

Some mixed-ending empty-line arrangements would concatenate a CR and LF from
separate logical lines into one CRLF. Such a duplicate/move/trim is rejected
**before any edit**, with a non-modal localized status message asking the user to
unify line endings first. The app never converts them automatically; existing
Edit conversion commands are available. Rejection preserves text, selection,
savepoint and undo history, unlike silently losing an empty line.

## Implementation and evidence

Scintilla owns native UTF-8 buffers, target replacements, search and grouped undo.
The application copies only the affected line ranges into bounded native byte
buffers before editing; it does not extract or slice a whole-document Ru string,
use the clipboard, or implement an undo stack. Native Scintilla line movement
and duplication were inspected but not used directly: their Enter-mode boundary
rewriting does not satisfy the mixed-ending rules above. Trim uses a backward native single-character class `[^ \\t]` per line
to find the last non-space/Tab. This is linear in the selected text size; an
unanchored trailing-whitespace closure was rejected after a quadratic native
reproduction. There is no Ru loop over text bytes.

Native WM_COMMAND fixtures and the actual executable GUI gate cover the three
line-ending styles, CJK/emoji, forward/reverse selections, boundary and no-op
cases, one-step Undo/Redo, and guards. The GUI gate additionally verifies exact
saved bytes and fresh-process reopening, plus all seven localized menus. These
are required candidate-specific gates: portable test passes alone are not
Windows execution evidence. See the source-bound CI receipts for the exact
validated commit and tree. Existing lexer, folding, EOL and package gates remain
required without lowering their thresholds.
