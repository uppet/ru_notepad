# Recent files

The File menu shows up to ten successfully opened file paths, most recent first.
Selecting an entry uses the same bounded opening queue as the ordinary Open
command. It does not replace an unsaved document or bypass encoding, size,
cancellation, or file-error checks. An unsuccessful or cancelled open is not
promoted into the list.

Opening a path again moves it to the front. Windows ordinal case-insensitive
comparison is used, not Unicode case folding: distinct names such as `straße`
and `strasse` are not merged. History is path-based; two different hard-link
paths can appear separately, while the existing document-identity check still
prevents duplicate editor tabs for the same file.

Long paths are shortened only for menu display. Ampersands and control
characters cannot inject menu shortcuts; the stored original path is used when
opening. Explicit Windows-1252 or GBK opening choices are remembered. Other
encodings use the normal automatic detection on reopening.

History is a bounded preference stored for the current Windows user under
`HKEY_CURRENT_USER\Software\ru_notepad\Preferences`, in `RecentFilesV1`.
It stores paths and opening code-page choices, not document contents. It is not
a crash-recovery session and never automatically reopens files on startup.
Moving the portable application does not clear this per-user preference.

Use **File > Clear recent files** to clear the list. If preferences cannot be
written, an otherwise successful file open still succeeds; history may not
survive a restart. A missing history entry produces the normal open error and
does not discard current text. Invalid, truncated or oversized persisted data
is rejected rather than partially interpreted.

Menu headings and messages follow the selected one of seven interface
languages. File paths themselves are not translated.

This feature is part of the bootstrap LLVM preview candidate; consult its
exact-build validation receipt for actual automated coverage.
