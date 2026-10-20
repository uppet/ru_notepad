# Third-party components and artwork

Project-owned application code and documentation are licensed under the MIT License in `LICENSE` (also included in portable packages). This grant excludes all third-party source, data and components, including Scintilla/Lexilla sources and components under `vendor/`, Unicode-derived data, and compiler/runtime dependencies. Their existing licenses and notices remain applicable. This project does not grant new rights to third-party material, including upstream examples whose historical provenance remains unresolved.

## Scintilla 5.6.7

The native editor component is built from the official source archive at https://www.scintilla.org/scintilla567.zip . The locally observed archive SHA-256 is `2309181e59e7da4659f890dbc128db7451ccd094748770e7be674b830494587c`. This pin is not an independently signed upstream checksum.

Scintilla is distributed under its permissive copyright/permission notice, available at https://www.scintilla.org/License.txt . The exact `License.txt` from the pinned source must accompany every binary package. No Notepad++ source, branding or logo is included.

## Lexilla 5.5.4

The syntax-lexer library is built from the official source archive at https://www.scintilla.org/lexilla554.zip . Its reproducibility SHA-256 pin is `5e0a21356e4e2f19d6a38ecd1c8172d5a2b7b4542940568b023386080db90fe0`; this is not an independently signed upstream checksum. The exact Lexilla `License.txt` from that source accompanies both portable ZIPs. Lexilla supplies C/C++ and JSON lexers. Ru highlighting uses the application's own Ru policy and bounded C scanner; structural folding remains Ru. It does not borrow another Lexilla language.

## Unicode classification data

The Ru scanner's generated identifier-classification intervals come from Python 3.12 / Unicode 15.0.0 `str.isalpha()` and `str.isalnum()` predicates, matching the pinned Ru frontend. The generated range data is distributed with the Unicode copyright and permission notice in `licenses/Unicode.txt` in both portable packages; the source copy is `packaging/licenses/Unicode.txt`, obtained from https://www.unicode.org/license.txt . Reproduction details are in `docs/ru-language-syntax.md`. This notice concerns Unicode data and does not assign an application license.

## Application-owned native helper

RuSyntax.dll is built from this repository's `native/` C sources. It accelerates bounded UTF-8 scanning and style-byte generation, using keyword/tag configuration and folding policy owned by the Ru application. It is not an additional third-party lexer. Its source and binary hashes are part of the same package receipts; the project-owned implementation is covered by the application MIT License, while Unicode-derived tables retain their separate notice.

## Compiler and Windows runtime support

Ru application source is compiled by the pinned Ru toolchain listed in `docs/build-provenance.md`. Python runs the build tools, not the distributed editor. Native executable/DLL builds use GCC/MinGW-w64; GCC runtime exception and MinGW-w64 notices must accompany statically linked support code. Package builders copy those notices from the actual toolchain distribution and retain their upstream terms unchanged.

Windows system DLLs are operating-system dependencies, not redistributed copies. A release inventory must list any non-system DLL shipped beside the application.

## Original artwork

The application icon was generated specifically for ru_notepad using GPT image generation. Generation provenance and the prompt are retained in `assets/README.md`. It does not reuse the Notepad++ chameleon or logo.
