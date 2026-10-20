# Building ru_notepad

This repository contains the editor’s source and build/test tools. The application is a Windows x64 executable generated from Ru through C; it does not embed a Python interpreter, libffi, or a Ru source interpreter. Python is a build-time compiler host and test driver.

## Pinned inputs

- **Ru 0.21.3:** public commit [`dd6cb81b52a426408f7076d82a84c2fdfb644263`](https://github.com/uppet/ru-language/commit/dd6cb81b52a426408f7076d82a84c2fdfb644263), tree `346d9f3f19c64f50f25b9f47ce92df1ea804bdb8`. Use a clean checkout of that exact commit. Its [language CI](https://github.com/uppet/ru-language/actions/runs/38872812574) passed all 13 jobs; that result validates the language toolchain, not this application.
- **Scintilla 5.6.7:** official source archive at <https://www.scintilla.org/scintilla567.zip>, SHA-256 `2309181e59e7da4659f890dbc128db7451ccd094748770e7be674b830494587c`. Verify the archive before extracting or building it. This is a reproducibility pin, not a claim that upstream signed the hash independently.
- **Lexilla 5.5.4:** official archive <https://www.scintilla.org/lexilla554.zip>, SHA-256 `5e0a21356e4e2f19d6a38ecd1c8172d5a2b7b4542940568b023386080db90fe0`. Build it beside the pinned Scintilla source and retain its own `License.txt`.
- **Unicode classification data:** Python 3.12 / Unicode 15.0.0 identifier predicates are retained as compact generated tables; the exact official Unicode notice ships in both ZIPs. Regeneration is documented in [Ru syntax scope](ru-language-syntax.md).
- **Application artwork:** original generated artwork and icon export details are documented in [assets/README.md](../assets/README.md).

Dependency archives and extracted source belong under the ignored `vendor/` directories. The application-owned `RuSyntax.dll` is built from reviewed `native/` C inputs; its source/header/table, compiler and binary hashes are validated with every executable receipt. It does not add a third-party source dependency. Each packaged Scintilla/Lexilla DLL must be built from the pinned source and accompanied by its upstream license. Project-owned application code and documentation are covered by the root MIT License; third-party code and data retain their existing licenses and notices.

## Build tools

Use a Windows x64 GCC/MinGW-compatible toolchain with GCC, G++, windres, ar, ranlib, and make, plus Python 3.10+ and Git. `tools/build.py` accepts each compiler/tool path explicitly and checks the Ru checkout’s tree and clean working state. Run:

```sh
python tools/build.py --help
```

The build audits native-call argument counts, emits C, compiles the application or selected test source, embeds the same app resource and Common Controls v6 manifest in every executable, and copies all three required DLLs beside it. Test executables retain the console subsystem; only the application uses the GUI diagnostic launcher. Every executable receipt covers the manifest, resource script, icon and version, along with all src/*.ru and tests/*.ru files. Missing or changed resource inputs block packaging. Generated files belong in ignored `build/` and `dist/` directories.

The normal build command does not silently launch the resulting program. Linux-to-MinGW cross-compilation can produce a Windows PE executable, but it does not establish native Windows runtime behavior. Wine results, when available, must likewise be identified separately from Windows results.

## Windows acceptance

The project’s Windows CI is the application execution gate. It must run the native test executables, inspect their logs and exit status, create the real application window, and close it normally within a bounded time. Uploading an EXE or observing a successful compiler exit alone is insufficient.

The [0.1.3 Windows run](https://github.com/uppet/ru_notepad/actions/runs/38887294845) passed 835 assertions, two GUI gates and the full 500,039,680-byte editor roundtrip. Version 0.1.4 adds Ru-owned syntax/folding and measured incremental-styling gates; only its exact BUILD.json is authoritative for that artifact. Preserve failures and platform skips separately from passes. File dialogs, clipboard/IME, accessibility, unsaved-change prompts, and NTFS permission/EFS behavior need their own applicable tests; the basic window smoke test does not certify them.

Do not distribute local tool caches, developer-only reports, raw user diagnostics, or unreviewed dependency binaries as source or release artifacts.

## Two portable packages

After native execution, CI packages the identical verified runtime into a normal runtime ZIP and a self-contained tests ZIP. The first contains only the editor, Scintilla/Lexilla/RuSyntax, necessary docs, samples, notices, hashes and compact provenance. The latter also contains native test executables, scripts and bounded synthetic evidence. All four runtime binary hashes must match across packages; missing dependencies, receipts, notices, required assertions, timeout/kill cleanup or unexpected skips block both packages. Original 0.1.1 artifacts stay frozen.
