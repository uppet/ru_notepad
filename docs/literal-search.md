# Literal search options (candidate)

F3 / Next searches forward from the end of the selection. Shift+F3 / Previous searches backward from its start, irrespective of the selection's anchor direction. The Search menu exposes both commands. A successful search selects the complete UTF-8 match and reveals its fold endpoints; an unsuccessful search leaves selection, text, undo and savepoint unchanged. Empty patterns focus the search bar rather than searching.

The search bar offers Match case, Whole word and Wrap around. Defaults remain case-sensitive, not whole-word, with wrapping enabled. With wrapping disabled, search stops at the corresponding document boundary. When enabled, it searches the remaining opposite segment once, including the current match if it is the only occurrence. Options are application-wide for this run, survive closing/reopening the search bar and switching tabs/languages, and are not saved between launches.

Whole word uses Scintilla 5.6.7 `SCFIND_WHOLEWORD` and its current native word-character rules. ASCII letters, digits and underscore are word characters; this is not dictionary-based Chinese/Japanese segmentation or grapheme-aware matching. Literal Unicode text is matched as supplied, without normalization. No regex or escape syntax is enabled.

Replace acts only when the complete current selection matches all selected options, then advances forward. If the selection is not an eligible match, it only finds the next one. Wrap affects this advance, not replace-all. Replace all always scans the entire current document once from start to finish, honors case and whole-word, does not revisit inserted text, and retains one undo group. It does not operate on other tabs or disk files. Existing failure diagnostics and save protection remain unchanged.

This batch does not implement selection-only scope, regex, extended escapes, search history, cross-file searches or persistent search preferences. No full Notepad++ search parity is claimed. Added native tests and seven-language layout checks must pass on Windows before the preview is delivered; a host model or generated-C check is not native execution.
