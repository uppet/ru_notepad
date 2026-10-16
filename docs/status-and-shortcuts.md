# Status and keyboard scope in 0.1.6

## Status

The status bar shows one-based line and column numbers, document UTF-8 byte length, the current line's terminator, Enter's insertion mode, selected save encoding/BOM, and actual syntax mode.

Column uses Scintilla `SCI_GETCOLUMN`: tabs advance to tab stops, while each Unicode codepoint counts once. Han characters and emoji are not counted by their UTF-8 byte length. Combining codepoints count separately, so this is neither a grapheme count nor pixel/full-width-cell geometry. It is also independent of visual wrapping. See the [official Scintilla information API](https://www.scintilla.org/ScintillaDoc.html#SCI_GETCOLUMN).

`Line EOL` inspects only the caret line using `SCI_GETLINEENDPOSITION` and `SCI_GETCHARAT`. It reports CRLF, LF, CR, or `None (EOF)` for an unterminated final line. `Enter` comes from `SCI_GETEOLMODE` and describes future inserted line breaks. Mixed-EOL documents therefore are not mislabeled as uniformly one family. Reading status never normalizes file bytes or changes undo/savepoint state.

## Keyboard inventory

Existing application keys remain Ctrl+N/O/S, Ctrl+Shift+S, Ctrl+W, Ctrl+F/H, F3 and Escape for the search bar. Scintilla and the focused Windows edit control retain their standard editing/navigation keys, including undo, redo, cut, copy, paste and select-all.

Added: Ctrl+Shift+Tab for the previous tab; Ctrl+PageUp/PageDown as previous/next alternatives; Ctrl++/Ctrl+- for zoom, including keypad plus/minus; Ctrl+0 for zoom reset. Plain Ctrl+Tab still selects the next tab. Tab navigation wraps. Zoom remains per-document and does not dirty text.

The application never consumes Alt or Ctrl+Alt/AltGr combinations. Unsupported Shift combinations are left to the focused control rather than triggering the unshifted command. Shift+F3 backward search is not implemented or claimed.

For Ru folding, Ctrl+Shift+[ collapses all and Ctrl+Shift+] expands all. The View menu exposes the same commands. Re-selecting the active language preserves fold state; changing to plain reveals hidden text. These commands do not apply to the large-file plain-text mode.

The same pure shortcut policy is exercised by 42 portable assertions. Native status tests cover mixed EOLs, tab/Han/emoji/combining-character columns and unchanged text/savepoints. Main-level feature tests use real WM_COMMAND callback dispatch; physical keyboard layouts and IME composition still need manual acceptance.
