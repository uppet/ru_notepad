# Syntax highlighting in 0.1.2 preview

## Supported languages

The application owns colours and native integration in `src/syntax.ru`; its
`识别` / `名称` wrappers delegate to the exact pure production policy in
`src/syntax_policy.ru`. Scintilla
owns text, rendering, selection and undo. Lexilla supplies real native lexers:

| File suffix, case-insensitive | Display | Lexilla lexer |
| --- | --- | --- |
| `.c`, `.h`, `.cc`, `.hh`, `.cpp`, `.hpp`, `.cxx`, `.hxx`, `.c++`, `.h++`, `.inl` | C / C++ | `cpp` (`SCLEX_CPP=3`) |
| `.json` | JSON | `json` (`SCLEX_JSON=120`) |
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

`.ru` is deliberately plain text in this version. Lexilla 5.5.4 has `rust`, but
that is Rust, not the unrelated Ru language. The application never labels a
C++, Rust or Python lexer as Ru support.

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
  The unmodified dependency license is shipped in both distribution packages.

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
- `识别 路`: extension mapping to `cpp`, `json` or `plain`.
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

## Incremental work and the 4 MiB limit

Lexer selection clears old style information once and enables
`SC_IDLESTYLING_TOVISIBLE`. It does not immediately force
`SCI_COLOURISE(0, -1)`. Scintilla requests native styling for the visible range and
invalidates the necessary ranges after text edits. Ru does not extract the entire
document or scan it on each keypress. A large multiline construct may still
require native lexer work up to the visible location; no universal latency or
performance claim is made.

The existing 4 MiB UTF-8 document/save limit remains unchanged. Native acceptance
coverage includes a document of exactly 4 MiB, verifies that initial selection
and a bounded edit/style request do not eagerly mark the whole file styled, and
checks that undo restores the changed byte and original savepoint. The measured
elapsed time is a diagnostic, not a pass/fail speed threshold or a benchmark.

## Acceptance coverage

`tests/syntax_policy.ru` runs the exact `src/syntax_policy.ru` production module,
without importing Win32 or loading substitute DLLs. Its **100 assertions** run
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

## A future Ru-owned lexer

The pinned Ru frontend contains language-specific rules absent from upstream
Lexilla: Unicode identifiers, Chinese punctuation aliases, four quote pairs,
multiline strings, `#` / `//` / `批.` line comments, and exact `解.` … `释.` block
comments. Treating these as C++ would visibly miscolour ordinary Ru programs.

The smallest truthful next step is a restricted container lexer written in Ru,
with `SCI_SETILEXER(NULL)` and `SCN_STYLENEEDED`. It should obtain only the changed
line/range, preserve UTF-8 byte offsets, and store per-line lexical state for
strings and block comments. State changes need to propagate forward until they
converge; a whole-document restart on every keystroke is unacceptable. Initial
support should explicitly name its supported lexical classes and exclusions,
with native byte-style tests for punctuation, quote/escape pairs, identifier
boundaries and edits that change multiline state. It should remain a separate
milestone until those rules and incremental behavior are proven. This version
does not ship or advertise that future lexer.
