ru_notepad 0.1.4-preview · Windows x64

IMPORTANT: EXPERIMENTAL PORTABLE PREVIEW
Read BUILD.json for this exact package's verification results. A local cross-build
is not Windows execution. A Windows CI package is produced only after the listed
native suites and visible-window/normal-close smoke test pass; those automated
checks do not establish full interactive Windows 10/11 acceptance.
Test copies of files first. Do not use this preview as the only editor for
irreplaceable documents. IME, accessibility and broad failure testing remain open.

STARTUP REPAIR AND DIAGNOSTICS
Version 0.1.0 had a confirmed Windows startup failure caused by malformed Ru
argument arrays. This revision fixes all six occurrences and adds portable
regressions. BUILD.json states whether this exact build passed Windows CI.
A small native launcher creates a unique ru_notepad-*.log beside the executable,
or falls back to the current user's local AppData\Temp directory. Existing logs
are never overwritten. Startup phases and runtime stdout/stderr are captured
before Ru module initialization. Fatal exit/nonzero return shows the log path.
If logging cannot be prepared, startup stops with a visible error.
The launcher does not log document contents or command-line arguments itself,
but runtime errors can include file paths/context. Review logs before sharing.
No emergency save or crash recovery is performed. Not every OS-level crash,
forced termination or power loss can produce a diagnostic dialog.

RUN
1. Extract the complete ZIP into a writable directory.
2. Keep ru_notepad.exe, Scintilla.dll, Lexilla.dll and RuSyntax.dll together.
3. Run ru_notepad.exe. No Python, Ru compiler, installation or admin rights needed.
   Windows may warn about this unsigned, newly built application. No code-signing
   or SmartScreen reputation is claimed.
4. Use File > Open or Ctrl+O. Invalid UTF-8 is rejected; reopen with the explicit
   Windows-1252 or GBK command when that is the intended encoding.

FILE ENTRY AND DEFAULTS
Drag filesystem files onto the main window, or pass multiple Unicode paths on
its command line. Directories fail explicitly; later valid paths still open.
Duplicates select the existing document by file identity, preserving dirty text.
During open/save, Cancel/Esc cancels the operation and any remaining open queue;
close requests cancel first and leave existing documents open. Retry drop/open
after the operation finishes. Virtual cloud-shell items are not implemented.
File drops replace Scintilla's OLE text-drop target: external text drops and
selection drag-to-move are not supported in this version. Clipboard commands
are separate. CI injects real child-window drop messages; full Explorer mouse
drag interaction still requires manual acceptance.
Settings > Register Open With candidate explicitly registers only this user.
Settings > Choose defaults opens Windows Settings; select each type yourself.
No UserChoice or extension default is overwritten. Unregister at the old folder
before moving the portable copy, then register from its new location.

IMPLEMENTED, WITH ACCEPTANCE SCOPE RECORDED IN BUILD.json
Independent document tabs; open/save/save-as; UTF-8/BOM and UTF-16 LE/BE;
Windows-1252 and GBK; undo/redo; literal find/replace; case matching;
replace-all as one undo group; word wrap; zoom/reset; line numbers; native C/C++
and JSON highlighting, extension detection and a Language menu. Ru source files
use a dedicated Ru 0.21.3 container policy with structural folding. Keyword tables
and fold decisions stay in Ru; the application-owned RuSyntax.dll handles bounded
UTF-8 scanning and style-byte generation. This is tolerant
editing support, not a complete parser or syntax validator.

STATUS AND SHORTCUTS
Ln/Col are one-based. Col uses Scintilla tab-expanded Unicode codepoint columns,
not UTF-8 bytes, screen pixels or grapheme clusters; combining marks count separately.
Line EOL describes the caret line (CRLF/LF/CR/None at EOF); Enter describes the
new-line insertion mode. Mixed files are not claimed to have one uniform EOL.
Ctrl+Tab / Ctrl+Shift+Tab and Ctrl+PageDown / Ctrl+PageUp switch tabs.
Ctrl++ / Ctrl+- zoom; Ctrl+0 resets zoom. Ctrl+Alt/AltGr is left to input methods.
For Ru, click the fold margin or use Ctrl+Shift+[ to collapse all and Ctrl+Shift+]
to expand all. The View menu has the same commands. Tabs retain fold state.
Language > Ru / 如言 selects it manually; open/save-as .ru paths select it
automatically. Styling runs in bounded background slices; wait for completion
before folding. Switching to plain text reveals all previously hidden lines.

LIMITS
No fixed 4 MiB file limit; 64 tabs and 64 queued paths. Full text remains in RAM.
Files >=32,000,000 bytes use labelled plain-text mode without syntax/wrap/folding.
Files >500,000,000 bytes ask before any body read. Cancel/Esc stops between
bounded chunks; an individual disk call or long-line layout can still block.
Embedded NUL and invalid Unicode text are rejected; no binary-file editing.
Legacy text may expand substantially when held as UTF-8; sufficient RAM is needed.
Not full Notepad++ parity. No regex parity, additional language
catalogue, plugin ABI, macros, sessions/recovery, split views, project panels,
printing, installer, updater, or network features yet.
Accessibility, IME, high-DPI/multi-monitor, broad large-file behavior, and Windows
version compatibility have not been accepted. Windows 10/11 x64 is the target.

SAVE SAFETY
Writes encode in bounded chunks and reject lossy conversion before replacement.
A same-directory temporary file is written and flushed. Existing ordinary files
use ReplaceFileW with a recovery backup; new files use no-overwrite rename.
Read-only files, EFS-encrypted saves, hard-linked destinations and selected
reparse points are rejected. Existing-file staging uses a protected copy of the
source DACL. BUILD.json records the synthetic protected/inherited NTFS cases;
those cases do not establish all ACL/EFS/filesystem behavior.
File identity/time/size guards detect ordinary external changes, but there is
an unavoidable check-to-replace race; this is not a filesystem transaction.
If replacement or cleanup reports an error, keep the named .tmp/.bak recovery
files and the editor open. A reported failure after replacement may mean the
new contents are already on disk. Read the complete message before retrying.
Orderly sign-out/restart is vetoed while documents are dirty or I/O is pending, but Windows can
force termination. No autosave or crash recovery exists yet.

TESTS
The normal runtime ZIP has only the editor and its DLLs, with docs and licenses.
Download the separate tests ZIP only if you want executable checks and CI evidence.
That tests ZIP is self-contained and includes the identical tested runtime bytes.
Inside the tests ZIP, run-tests.cmd runs native executables against Win32 controls
and a fresh disposable folder within this package. It does not need Python.
The test runner includes a full >500MB text roundtrip; allow several minutes,
roughly 3 GiB free RAM and 2 GiB free disk. Generated large fixtures are not uploaded.
A test failure is a real failure; a build-only result is not a test pass.
Save test-results.txt when reporting a problem. GUI smoke tests may open windows.
The optional ACL script is not run automatically. It intentionally changes ACLs
only on a newly created synthetic fixture folder. Review OPTIONAL-ACL-TESTS.txt
before choosing to run it; do not use it on real documents.

MANUAL ACCEPTANCE
- New, edit, switch tabs, undo/redo independently.
- Open a COPY of UTF-8, UTF-8 BOM, UTF-16 LE/BE, GBK and Windows-1252 files.
- Save unchanged and compare bytes. Test Chinese and emoji filenames/content.
- Close a dirty tab: verify Save, Don't Save and Cancel; cancel Save As too.
- Make a destination read-only; failed save must retain dirty state/content.
- Modify the on-disk file elsewhere; ordinary Save should reject the conflict.
- Find next wraps; case option works; replace-all is reverted by one Undo.
- Try mixed line endings, Chinese IME, high DPI, keyboard-only controls.
- Open samples/example.ru; check comment/string colours and nested folds.
- Click a fold margin, switch tabs, then expand; bytes and dirty state must not change.
- Edit an unfinished string/comment, undo it, and wait for the syntax status to finish.

REPORT
Include Windows version/architecture, app build SHA from BUILD.json, steps to
reproduce, expected/actual result, and test-results.txt. Do not send passwords,
private document contents, or originals just to report a bug.

COMPONENTS
Application logic: Ru compiled to native C/Windows PE.
Editor core: Scintilla 5.6.7, built from official source; license in licenses/.
C/C++ and JSON syntax: Lexilla 5.5.4. Ru syntax: Ru policy plus the application-owned
RuSyntax.dll C scanning/style-buffer helper; structural folding decisions remain Ru.
Unicode classification data notice is included in licenses/Unicode.txt.
Icon: original GPT-generated artwork. No Notepad++ branding or source included.
Project-owned application code and documentation are licensed under MIT; see LICENSE.
Third-party code and data retain their existing licenses; see THIRD_PARTY_NOTICES.md and licenses/.
