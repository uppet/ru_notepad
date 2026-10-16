ru_notepad 0.1.1-preview · Windows x64

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
2. Keep ru_notepad.exe and Scintilla.dll together.
3. Run ru_notepad.exe. No Python, Ru compiler, installation or admin rights needed.
   Windows may warn about this unsigned, newly built application. No code-signing
   or SmartScreen reputation is claimed.
4. Use File > Open or Ctrl+O. Invalid UTF-8 is rejected; reopen with the explicit
   Windows-1252 or GBK command when that is the intended encoding.

IMPLEMENTED, WITH ACCEPTANCE SCOPE RECORDED IN BUILD.json
Independent document tabs; open/save/save-as; UTF-8/BOM and UTF-16 LE/BE;
Windows-1252 and GBK; undo/redo; literal find/replace; case matching;
replace-all as one undo group; word wrap; zoom; line numbers.

LIMITS
4 MiB file/save and UTF-8 editor-load limit, 64 tabs.
Embedded NUL and invalid Unicode text are rejected; no binary-file editing.
A legacy-encoded file may expand beyond the UTF-8 editor-load limit.
Not full Notepad++ parity. No regex, syntax
lexers, plugin ABI, macros, sessions/recovery, split views, project panels,
printing, installer/file associations, updater, or network features yet.
Accessibility, IME, high-DPI/multi-monitor, large-file behavior, and Windows
version compatibility have not been accepted. Windows 10/11 x64 is the target.

SAVE SAFETY
Writes encode fully and reject lossy legacy conversion before replacing files.
A same-directory temporary file is written and flushed. Existing ordinary files
use ReplaceFileW with a recovery backup; new files use no-overwrite rename.
Read-only files, EFS-encrypted saves, hard-linked destinations and selected
reparse points are rejected. Existing-file staging uses a protected copy of the
source DACL; actual NTFS permission preservation still needs runtime acceptance.
File identity/time/size guards detect ordinary external changes, but there is
an unavoidable check-to-replace race; this is not a filesystem transaction.
If replacement or cleanup reports an error, keep the named .tmp/.bak recovery
files and the editor open. A reported failure after replacement may mean the
new contents are already on disk. Read the complete message before retrying.
Orderly sign-out/restart is vetoed while documents are dirty, but Windows can
force termination. No autosave or crash recovery exists yet.

TESTS
run-tests.cmd runs included native test executables against real Win32 controls
and a fresh disposable folder within this package. It does not need Python.
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

REPORT
Include Windows version/architecture, app build SHA from BUILD.json, steps to
reproduce, expected/actual result, and test-results.txt. Do not send passwords,
private document contents, or originals just to report a bug.

COMPONENTS
Application logic: Ru compiled to native C/Windows PE.
Editor core: Scintilla 5.6.7, built from official source; license in licenses/.
Icon: original GPT-generated artwork. No Notepad++ branding or source included.
This local prototype has no selected public project license.
