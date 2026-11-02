# Explicit line-ending conversion

Edit offers **Convert entire text to CRLF / LF / CR (and Enter)** in all seven UI
languages. These commands act on the entire active document, not just the selected
range. They convert existing ASCII line terminators and set the document's future
Enter insertion mode. They never save automatically, change encoding/BOM, or add
a newline at an unterminated end of file. Other Unicode separators are unchanged.
There is no new shortcut or Show EOL command in this increment.

One Undo restores the exact original text, including mixed CRLF/LF/CR. One Redo
restores the converted text. **Enter is an independent insertion preference and
keeps the last explicitly selected target even after Undo.** Status continues to
show the caret line's actual terminator separately from Enter. The menu entries
are actions, not checked assertions that every line has that format. Thus Undo
may restore mixed line endings while Enter remains LF; saving preserves those
actual mixed bytes, not the Enter preference.

Empty and newline-free documents only change Enter; no text is added, no dirty
savepoint or empty Undo action is introduced. Repeating the current uniform
format is likewise a text no-op. A conversion changes the text savepoint only
when bytes change. Existing encoding-only dirty state is independent and is not
cleared by conversion or Undo. Save uses the selected encoding and BOM exactly;
reopening detects Enter with the existing CRLF-first, otherwise LF, otherwise CR
rule (CRLF for empty/newline-free files). Enter preferences are not stored in a
file's bytes or a session sidecar.

Conversion preserves forward/reversed selection locations through Scintilla's
native byte-position adjustment; CJK and emoji are not rewritten. Undo/Redo use
Scintilla's normal caret/selection placement, **not restoration of an earlier
user selection**. Neither operation may split a UTF-8 codepoint. Existing
readonly, busy/save/open, modal, close-transaction and tab-menu barriers apply.
Conversion is a synchronous full-document operation, so it is disabled for the
large-file plain-text mode and for any document whose current UTF-8 buffer has
reached 32,000,000 bytes, even if it originally opened below that threshold.
Large files are otherwise still editable and saveable under existing policy.

## Implementation and verification scope

`SCI_CONVERTEOLS` performs the native grouped edit; `SCI_SETEOLMODE` independently
sets Enter. No full-buffer text-copy rewrite or handcrafted undo stack is used.
The pinned Scintilla 5.6.7 `Document::ConvertLineEnds` owns its `UndoGroup`.
See [Scintilla line endings](https://www.scintilla.org/ScintillaDoc.html#LineEndings).
The [Notepad++ editing manual](https://github.com/notepad-plus-plus/npp-usermanual/blob/master/content/docs/editing.md)
also defines EOL Conversion as whole-file conversion. We do not claim identical
Notepad++ undo internals or its Show Symbol UI.

The new native WM_COMMAND checks reuse the main-linked tab fixture (89 total,
36 new EOL checks): all three conversions, single Undo/Redo, mixed Unicode text,
empty/newline-free/uniform no-ops, readonly and busy/modal/close/tab-menu guards,
and current-byte threshold independent of initial large mode.
The mandatory actual-EXE GUI gate covers all three modes, both selection
directions, UTF-8 with/without BOM and UTF-16 LE/BE with BOM, save after conversion,
save after Undo, Redo/save, and a fresh-process reopen. It checks exact disk bytes,
status, menus in seven languages, large-file no-op and no implicit save.
Portable receipt tests are not Windows execution evidence. A candidate is not
validated until these gates pass on its exact published commit/runtime.

## Ru feedback collected in this increment

No new Ru semantic defect is currently confirmed. Native conversion keeps the
buffer/undo operation in Scintilla rather than amplifying it into Ru string
copies. Existing per-change callback/analysis scaling limitations remain relevant
for many-line files; this increment does not change the compiler or its default
200,000-step analysis limit. The independent development ABI oracle is regenerated
from all current sources with the already disclosed isolated 2,000,000-step
budget; it is not evidence that the ordinary C-backend analysis succeeds.
A useful future language/tool improvement is a typed, generated Scintilla message
binding, so swapped integer constants and parameter units can be diagnosed
without handwritten API-number reviews. This is a proposal, not a reproduced
compiler bug. The UTF-8 checksum-manifest fix for descriptive Chinese ZIP names
is a Python packaging defect, not a Ru defect.
