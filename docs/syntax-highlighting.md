# Syntax highlighting in 0.1.4 preview

## Supported languages

The application owns colours and native integration in `src/syntax.ru`; its
`识别` / `名称` wrappers delegate to the exact pure production policy in
`src/syntax_policy.ru`. Scintilla
owns text, rendering, selection and undo. C/C++ and JSON use native Lexilla lexers; Ru uses its own container policy:

| File suffix, case-insensitive | Display | Implementation |
| --- | --- | --- |
| `.c`, `.h`, `.cc`, `.hh`, `.cpp`, `.hpp`, `.cxx`, `.hxx`, `.c++`, `.h++`, `.inl` | C / C++ | `cpp` (`SCLEX_CPP=3`) |
| `.json` | JSON | `json` (`SCLEX_JSON=120`) |
| `.ru` | Ru / 如言 | Ru-owned Scintilla container policy (`SCLEX_CONTAINER=0`) |
| Other suffixes, no suffix, new unsaved documents | Plain text | No lexer |

Only the final filename suffix is considered. The shared `含词` helper performs
explicit whole-string comparisons when checking string arrays; Ru
`其 含` is string containment and must not be used as array membership. A directory named `examples.cpp`
does not make its extensionless child a C++ document. `.jsonc` and `.json5` are
not advertised as JSON support. JSON comments are disabled. Keywords, numbers,
strings, property names, operators and escape sequences receive distinct styles.
C/C++ uses a shared C-family keyword list; this is colouring, not a compiler or a
language-version validator. Preprocessor branch evaluation is disabled rather
than guessing which branches are active without the project's build settings.

Ru keeps keyword tables and structural-folding rules in application Ru modules.
`RuSyntax.dll` accelerates bounded UTF-8 token scanning and fills style-byte buffers;
`ru_syntax.ru` owns Scintilla jobs, checkpoints and lifecycle. The original pure
`ru_lexical.ru` scanner remains the differential test oracle. Its exact language scope is in
[Ru lexical policy](ru-language-syntax.md). It works independently of Lexilla;
C/C++ and JSON still use their actual native Lexilla implementations.

Ru jobs are owned by a specific editor/document generation. Notifications only
invalidate or request work; the main scheduler budgets background slices. Checkpoints
bound restart distance, and equivalent same-length edits reuse a converged suffix.
Incomplete edits may require scanning farther. No styling operation edits text,
resets the savepoint, or clears undo. The existing 32 MB plain-text mode disables
Ru highlighting/folding too; large files remain editable.

The main application requests only insertion/deletion `SCN_MODIFIED` events
(`SCI_SETMODEVENTMASK=3`), and reads back that subscription for both new tabs
and pending file-load editors. Style-needed, savepoint, update-UI and margin
notifications remain independent. Scintilla completes its internal style/fold,
layout and undo handling before this parent-notification filter. Native controls
retain the default full subscription to test the unused-notification path.

The fold margin and View menu operate on Ru folds. Ctrl+Shift+[ / ] collapse/expand
all folds. Re-selecting Ru or switching tabs retains existing folds; changing to
plain/C++/JSON first restores hidden text. Fold state is in-memory only; sessions
and crash recovery are not implemented.

## Dependency and source pin

- Scintilla **5.6.7**, official source archive
  <https://www.scintilla.org/scintilla567.zip>, SHA-256:
  `2309181e59e7da4659f890dbc128db7451ccd094748770e7be674b830494587c`.
- Lexilla **5.5.4**, official source archive
  <https://www.scintilla.org/lexilla554.zip>, SHA-256:
  `5e0a21356e4e2f19d6a38ecd1c8172d5a2b7b4542940568b023386080db90fe0`.
- These are the matching components of the official September 28, 2026
  [SciTE 5.6.7 release](https://www.scintilla.org/SciTEHistory.html).
- Both use the permissive
  [License for Lexilla, Scintilla, and SciTE](https://www.scintilla.org/License.txt).
  The unmodified dependency license is shipped in both distribution packages. The application-owned RuSyntax DLL and Unicode data
notice are also included and hash-checked.

Lexilla is built from its official source. Its `src/makefile` expects the peer
`scintilla/include` directory. The Windows target is `../bin/lexilla.dll` with
`windir` set; the package uses the filename `Lexilla.dll`. Static MinGW runtime
linking avoids requiring a separate compiler installation or runtime DLL bundle.
Build receipts record the source archive and resulting DLL hashes. The build
checks the extracted source bytes against the pinned archive before compilation.

Official protocol and API references:

- [Lexilla API and build documentation](https://www.scintilla.org/LexillaDoc.html)
- [Scintilla lexer object API](https://www.scintilla.org/ScintillaDoc.html#SCI_SETILEXER)
- [Scintilla styling and byte positions](https://www.scintilla.org/ScintillaDoc.html#Styling)

## Ownership, failure and integration contract

Import `syntax.ru` and call `初始化` before registering the application's native
window callback. The module performs optional dependency loading at import, not
inside a notification or key handler. `初始化` returns a warning string or an empty
string on success; the application displays a startup warning once.

The DLL location is always `Lexilla.dll` beside the executable. An absolute path
and `LoadLibraryExW` flags `LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR |
LOAD_LIBRARY_SEARCH_SYSTEM32` (`0x900`) prevent current-working-directory DLL
searches. The module checks loading and the exact `CreateLexer` export through
ordinary Win32 return values before invoking the managed native binding. Missing,
incompatible or wrong-symbol DLLs therefore produce plain-text editing with a
clear warning in the normal startup path. They do not discard open documents.
A missing DLL does not prompt a download or relax the DLL search policy.

The managed library and its fixed-signature binding are retained at module scope
for the process lifetime. Only the extra preflight loader reference is released.
Each editor receives a fresh `ILexer5*` from `CreateLexer(const char*)`. Ownership
is transferred immediately to `SCI_SETILEXER`; the application must not free,
share between documents, or reuse that pointer. Scintilla's pinned
`LexInterface::SetInstance` and `LexerReleaser` release a replaced lexer or the
final lexer when its document is destroyed. Lexilla remains loaded until after
all editor windows and their documents are destroyed.

The binding uses Windows x64 pointer return and pointer argument types. Passing
the lexer pointer in Scintilla's `LPARAM` uses an explicit `intptr` reinterpret;
property-name pointers use explicit `uintptr` reinterprets. No pointer is routed
through Ru's floating-point `数` type. The app-specific native-argument audit
checks the conditional binding declaration and every native invocation.

The pinned Ru runtime treats native-library acquisition/binding failures as fatal
runtime errors, not `卒` exceptions. Preflight prevents ordinary absent-DLL and
absent-export failures from reaching those calls. It does not promise recovery
from memory exhaustion or a dependency being removed/its access being changed
between preflight and managed acquisition. A superficial `试`/`救` wrapper would
not make those runtime failures recoverable; the compiler is unchanged.

Public module operations:

- `初始化`: cached warning string, empty on success; no retry or late module loading.
- `识别 路`: extension mapping to `ru`, `cpp`, `json` or `plain`.
- `名称 语言`: truthful status-bar label.
- `选择 柄 语言`: applies the requested supported language, returning the actual
  language; unavailable or unknown languages return `plain`.

Successful selection checks both Scintilla's error status and the actual native
lexer identifier before reporting the chosen language. If either check fails,
the adopted lexer is detached through Scintilla and the actual mode is plain.

Changing a lexer touches style bytes, style colours and native lexer properties
only. It does not replace text, change EOL mode, set a savepoint, clear undo,
move the caret or change the selection. Clearing token styles deliberately
avoids `SCI_STYLECLEARALL`, which would also reset the editor's line-number style.
The document remains independently editable and undoable if highlighting is
unavailable.

## Incremental work and large-file mode

For C/C++ and JSON, lexer selection clears old style information once and
enables `SC_IDLESTYLING_TOVISIBLE`. It does not immediately force
`SCI_COLOURISE(0, -1)`. Scintilla requests native styling for the visible range
and invalidates the necessary ranges after text edits.

For Ru, bounded UTF-8 slices run outside notification callbacks. At most one
coalesced continuation message is queued; it carries a burst token rather than
a document pointer. The existing 10 ms timer provides a fallback when input,
paint, sent messages, hotkeys or other queued work needs control. A continuation
checks the current high word of
[GetQueueStatus](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getqueuestatus)
before starting or posting more work. Each slice keeps the existing 8 ms
admission budget; a single batch is not preemptible, so measured maximum slice
and response times are recorded rather than claiming a hard real-time limit.
Obsolete messages cannot advance a completed or replaced burst. This scheduling
change is subject to the complete 30-second Windows gate and actual queued
navigation/paint coverage.

Checkpoints retain lexical and structural context, including incomplete
strings/comments. Same-length, same-line-count edits may reuse an unchanged suffix
when the full state converges; edits that change later parsing can require a
longer suffix rescan. Jobs are tied to the actual document pointer and generation.
The scanner never extracts the whole document as one Ru string. Timing and read
counts for 100 KB and 1 MB fixtures are recorded by the native acceptance suite;
no universal latency or performance claim is made.

The fixed file-size limit has been removed. Files of at least 32,000,000 bytes
open in labelled plain-text large-file mode with no lexer or wrapping; choosing
highlighting/wrap is disabled for that document to control memory/layout cost.
Existing documents retain their own manual language and wrap choices. This mode
is independent of the strict >500,000,000-byte pre-read consent threshold.
Native syntax acceptance coverage includes a document of exactly 4 MiB, verifies that initial selection
and a bounded edit/style request do not eagerly mark the whole file styled, and
checks that undo restores the changed byte and original savepoint. The measured
elapsed time is a diagnostic, not a pass/fail speed threshold or a benchmark.

## Acceptance coverage

`tests/syntax_policy.ru` runs the exact `src/syntax_policy.ru` production module,
without importing Win32 or loading substitute DLLs. Its **108 assertions** run
in both the pinned Ru interpreter and compiled Linux C. They cover all supported
suffixes in lower/upper/mixed case, JSON, Unicode and network paths, directory
boundaries, unknown extensions, display names, and the same `含词` helper used by
the native test executable's CLI. CLI cases include empty arrays/strings, flags
in different positions, duplicates, nonmatching prefixes/suffixes, case and
whitespace significance, Unicode elements, and preservation of the input array.

This portable coverage was added after real Windows CI exposed two uses of
string-only `含` with an array receiver: production C-family suffix selection and
the native fixture's CLI argument checks. Both now use the same explicit equality
helper, rather than a test-only replacement. The original unsupported expression
is also retained as a negative regression fixture by the portable test runner.

`tests/syntax_native.ru` is a compiled Windows executable using the real
Scintilla and Lexilla DLLs. It is not a lexer mock. Normal execution has **82
assertions**, including:

- Actual `SCI_GETLEXER` identifiers and `SCI_GETSTYLEINDEXAT` token-style bytes.
- C/C++ keywords, identifier boundaries, numbers, strings, line/block comments
  and multiline comment state.
- JSON property names, operators, strings, numbers, keywords and escapes.
- Every byte of Han and four-byte emoji characters, and token offsets after them.
- Exact source preservation, anchor/caret, EOL insertion mode, line-number
  styling, clean/dirty state, savepoints, existing undo and redo history.
- C++ → JSON → plain transitions, clearing all old style bytes, unknown suffixes,
  case-insensitive suffixes, independent editors and repeated lexer replacement.
- Continued styling in a surviving editor after another live-lexer editor is
  destroyed; the 4 MiB lazy-styling case above.

Two additional real startup fixtures run the same executable in isolated
folders. `--expect-missing` omits `Lexilla.dll`; `--expect-bad-lexer` provides a
real DLL that has no `CreateLexer` export. Each has **8 assertions** covering the
specific warning, plain fallback, preserved Unicode text, continued editing and
undo/savepoint behavior. Neither fixture merely changes an in-memory ready flag.

Static checks and cross-compilation establish source/ABI/build viability only.
Only a successful native Windows CI run establishes that these acceptance tests
passed; see that run's exact-commit results and distribution validation receipt.

## Ru-owned native acceptance

The production lexical policy has **380 portable assertions**, replaying small
fixtures at different scalar boundaries. The real Scintilla bridge adds **125
assertions** for byte styles, fold levels, incomplete multiline edits, bounded
reads, checkpoint convergence, stale document generations, fallback visibility,
and text/savepoint/undo preservation. Length-changing insertion/deletion at the
beginning, middle and end is compared byte-for-byte and fold-for-fold with a fresh
scan; further edits while work is pending must converge to the latest document. An isolated **8-assertion** run omits
Lexilla.dll and proves that Ru styling and folding still work with RuSyntax.dll.
Three further **8-assertion** runs independently omit the helper, provide a DLL
without its exports, or provide an incompatible ABI version. Each requires a
clear ordinary warning and continued plain-text editing, without unsafe binding.

The main-window integration suite has **73 assertions**. It exercises real timer
dispatch, Unicode `.ru` CLI input, Language/View menu commands, Scintilla margin
hit-testing and the owning callback, independent tabs, dirty/undo preservation,
automatic selection after successful Save As, and closing a pending styling job.
It also compares a deliberately full-notification small control with the actual
text-only application subscription, including insertion, undo, redo, line
counts and savepoint transitions. Actual message-queue cases cover single-slot
coalescing, stale burst tokens, busy/input/paint deferral, timer resumption and
close while work is queued. Fixed diagnostic requests additionally verify
parameter rejection, busy/in-callback/active-document guards, ordinary failure
recovery and the three-request cap without text or dirty-state mutation. A separate **8-assertion** mode uses the
production scheduler on the exact 1 MB GUI corpus, records cumulative work,
callback gaps, successful posts, continuation ticks and yield/stale counts,
and requires completion within 30 seconds. Both fixture corpus
builders are executed in both portable backends and compared against every
byte of the existing GUI fixture before native CI runs.
The separate detached GUI gate checks actual style/fold values, hidden-line
visibility, unchanged source, responsiveness and normal close. During pending
styling, posted navigation must move/restore the caret and a real invalidation
must drain naturally, without forcing a paint or modifying the corpus. It also measures
1 MB completion with full snapshots at least 250 ms apart and WM_NULL probes
at least 50 ms apart, recording actual observer message counts and elapsed cost.
Up to three explicitly requested numeric projections expose work/progress only;
they do not scan or read document text. Diagnostic collection cannot turn a
post-deadline completion into a pass. The gate also measures representative
100 KB real insertion/Backspace at
the beginning, middle and end. These are required
Windows gates for 0.1.4; a local compile is not evidence that they passed.

Physical mouse interaction, non-US keyboard layouts and IME composition still
need manual acceptance. Keyboard shortcuts use Windows virtual-key positions;
the View menu and fold margin provide alternatives on layouts where brackets
require different modifier combinations.

## Conditional-chain editing validation

`另若` is recognized as one keyword and shares the existing conditional frame;
spaced `另 若` remains nested. The interpreter and native scanner consume the
same Ru-owned keyword table. This is editor support, not an upgrade of the
bundled compiler pin. Six new fixtures add 42 assertions to the existing 338,
for 380 total, preserving original fixture coverage and all acceptance gates.
