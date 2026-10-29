# Third-party components and artwork

Project-owned application code and documentation are licensed under the MIT License in `LICENSE` (also included in portable packages). This grant excludes all third-party source, data and components, including the unchanged Scintilla/Lexilla archives and accompanying notices in `third_party/source_archives/`, their extracted copies under `vendor/`, Unicode-derived data, and compiler/runtime dependencies. Their existing licenses and notices remain applicable. This project does not grant new rights to third-party material, including upstream examples whose historical provenance remains unresolved.

## Scintilla 5.6.7

The native editor component is built from the official source archive at https://www.scintilla.org/scintilla567.zip . The locally observed archive SHA-256 is `2309181e59e7da4659f890dbc128db7451ccd094748770e7be674b830494587c`. This pin is not an independently signed upstream checksum.

Scintilla is distributed under its permissive copyright/permission notice, available at https://www.scintilla.org/License.txt . The exact `License.txt` from the pinned source must accompany every binary package. No Notepad++ branding or logo is included. The separately licensed Objective-C lexer is identified below.

## Lexilla 5.5.4

The syntax-lexer library is built from the official source archive at https://www.scintilla.org/lexilla554.zip . Its reproducibility SHA-256 pin is `5e0a21356e4e2f19d6a38ecd1c8172d5a2b7b4542940568b023386080db90fe0`; this is not an independently signed upstream checksum. The exact Lexilla `License.txt` from that source accompanies both portable ZIPs. Lexilla supplies the bundled language lexers listed in `syntax/languages.json`. Ru highlighting uses the application's own Ru policy and bounded C scanner; structural folding remains Ru. It does not borrow another Lexilla language.

## Unicode classification data

The Ru scanner's generated identifier-classification intervals come from Python 3.12 / Unicode 15.0.0 `str.isalpha()` and `str.isalnum()` predicates, matching the pinned Ru frontend. The generated range data is distributed with the Unicode copyright and permission notice in `licenses/Unicode.txt` in both portable packages; the source copy is `packaging/licenses/Unicode.txt`, obtained from https://www.unicode.org/license.txt . Reproduction details are in `docs/ru-language-syntax.md`. This notice concerns Unicode data and does not assign an application license.

## Application-owned native helper

RuSyntax.dll is built from this repository's `native/` C sources. It accelerates bounded UTF-8 scanning and style-byte generation, using keyword/tag configuration and folding policy owned by the Ru application. It is not an additional third-party lexer. Its source and binary hashes are part of the same package receipts; the project-owned implementation is covered by the application MIT License, while Unicode-derived tables retain their separate notice.

## Source-only build archives

The unchanged pinned Scintilla/Lexilla source ZIPs are retained in `third_party/source_archives` for offline reproducible builds. The source repository’s `third_party/source_archives/README.md` preserves upstream notices and adds applicable Catch2/Boost, Mako, Nix example and Unicode data notices. These source archives are not included in the portable runtime/tests ZIPs; required binary notices remain. This inventory does not relicense any upstream source or example.

## Compiler and Windows runtime support

The generated executable contains Ru runtime code compiled from the unchanged
source pin `85c7821fda35aa79deeaf67b4d430f24ddd7f07f`. The project owner's MIT
declaration is recorded separately at [Ru commit
`52526172d31ba902241c69dc8020996e6038f24a`](https://github.com/uppet/ru-language/commit/52526172d31ba902241c69dc8020996e6038f24a).
The two complete repository trees differ only in `LICENSE`, `README.md`,
`docs/third-party-notices.md` and `rulang/thirdparty/如见/README.md`; compiler and
runtime code bytes are unchanged. The declaration's exact LICENSE bytes are
retained independently as `licenses/ru-language-MIT.txt` in both ordinary and
manual-preview packages, with Copyright (c) 2026 uppet. The compiler pin has not
been changed to the declaration commit. Ru third-party exclusions continue to
apply; this notice does not relicense dependencies or their upstream material.

Ru application source is compiled by the pinned Ru toolchain listed in `docs/build-provenance.md`. Python runs the build tools, not the distributed editor. Native executable/DLL builds use GCC/MinGW-w64; GCC runtime exception and MinGW-w64 notices must accompany statically linked support code. Package builders copy those notices from the actual toolchain distribution and retain their upstream terms unchanged.

Windows system DLLs are operating-system dependencies, not redistributed copies. A release inventory must list any non-system DLL shipped beside the application.

## Original artwork

The application icon was generated specifically for ru_notepad using GPT image generation. Generation provenance and the prompt are retained in `assets/README.md`. It does not reuse the Notepad++ chameleon or logo.
## Additional Objective-C lexer

The `LexObjC.cxx` addition is from the Lexilla subtree of Notepad++ 8.9.8.1,
under its explicit Scintilla/Lexilla permissive notice. Neil Hodgson's original
copyright and Don Ho's modification attribution remain in the source. See
`native/lexilla/README.md` for exact upstream identity and
`licenses/Lexilla-Objective-C.txt` in the runtime ZIP for the full license.
The official Lexilla 5.5.4 archive remains unchanged; a separately identified
build catalogue registers this additional lexer.


## Language keyword configuration

Keyword configuration is derived from SciTE/Scintilla's permissively licensed
properties and lexer sources. The exact SciTE 5.6.7 permission notice is
retained as `licenses/SciTE.txt`; it is distinct from the Lexilla archive notice.
GDScript keyword data derives from Godot's MIT-licensed tokenizer; Transact-SQL
builtin names derive from Pygments' BSD-licensed `_tsql_builtins.py`; Gui4Cli
keywords derive from its MIT-licensed source. Exact accompanying notices are
shipped as `licenses/Godot.txt`, `licenses/Pygments.txt` and
`licenses/Gui4Cli.txt` in both portable packages. These data and notices retain
their upstream licenses and are excluded from the project's MIT grant.
