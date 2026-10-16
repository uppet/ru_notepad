# Third-party components and artwork

The application has no selected public project license yet. Individual dependency licenses remain applicable; this notice does not choose a new license for their authors or for ru_notepad.

## Scintilla 5.6.7

The native editor component is built from the official source archive at https://www.scintilla.org/scintilla567.zip . The locally observed archive SHA-256 is `2309181e59e7da4659f890dbc128db7451ccd094748770e7be674b830494587c`. This pin is not an independently signed upstream checksum.

Scintilla is distributed under its permissive copyright/permission notice, available at https://www.scintilla.org/License.txt . The exact `License.txt` from the pinned source must accompany every binary package. No Notepad++ source, branding or logo is included. Lexilla is not bundled in this preview.

## Compiler and Windows runtime support

Ru application source is compiled by the pinned Ru toolchain listed in `docs/build-provenance.md`. Python runs the build tools, not the distributed editor. Native executable/DLL builds use GCC/MinGW-w64; GCC runtime exception and MinGW-w64 notices must accompany statically linked support code. Package builders copy those notices from the actual toolchain distribution and retain their upstream terms unchanged.

Windows system DLLs are operating-system dependencies, not redistributed copies. A release inventory must list any non-system DLL shipped beside the application.

## Original artwork

The application icon was generated specifically for ru_notepad using GPT image generation. Generation provenance and the prompt are retained in `assets/README.md`. It does not reuse the Notepad++ chameleon or logo.
