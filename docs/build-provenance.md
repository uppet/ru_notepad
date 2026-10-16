# Building ru_notepad

This repository contains the editor’s source and build/test tools. The application is a Windows x64 executable generated from Ru through C; it does not embed a Python interpreter, libffi, or a Ru source interpreter. Python is a build-time compiler host and test driver.

## Pinned inputs

- **Ru 0.21.1:** public commit [`5626adb791a8b3949a40e2421b9620fba8d785bf`](https://github.com/uppet/ru-language/commit/5626adb791a8b3949a40e2421b9620fba8d785bf), tree `3a9972dfd17fd570ef992ecffd9b5bccec1cc88d`. Use a clean checkout of that exact commit. Its [language CI](https://github.com/uppet/ru-language/actions/runs/38854666925) passed all 13 jobs; that result validates the language toolchain, not this application.
- **Scintilla 5.6.7:** official source archive at <https://www.scintilla.org/scintilla567.zip>, SHA-256 `2309181e59e7da4659f890dbc128db7451ccd094748770e7be674b830494587c`. Verify the archive before extracting or building it. This is a reproducibility pin, not a claim that upstream signed the hash independently.
- **Application artwork:** original generated artwork and icon export details are documented in [assets/README.md](../assets/README.md).

Dependency archives and extracted source belong under the ignored `vendor/` directories. The packaged Scintilla DLL must be built from the pinned source and accompanied by its upstream license. The application’s own license is still pending the owner’s choice.

## Build tools

Use a Windows x64 GCC/MinGW-compatible toolchain with GCC, G++, windres, ar, ranlib, and make, plus Python 3.10+ and Git. `tools/build.py` accepts each compiler/tool path explicitly and checks the Ru checkout’s tree and clean working state. Run:

```sh
python tools/build.py --help
```

The build audits native-call argument counts, emits C, compiles the application or selected test source, embeds the app icon and manifest for the GUI executable, and copies the built Scintilla DLL beside it. A build receipt records input and output hashes. Generated files belong in ignored `build/` and `dist/` directories.

The normal build command does not silently launch the resulting program. Linux-to-MinGW cross-compilation can produce a Windows PE executable, but it does not establish native Windows runtime behavior. Wine results, when available, must likewise be identified separately from Windows results.

## Windows acceptance

The project’s Windows CI is the application execution gate. It must run the native test executables, inspect their logs and exit status, create the real application window, and close it normally within a bounded time. Uploading an EXE or observing a successful compiler exit alone is insufficient.

The first application CI result is pending. Preserve failures and platform skips separately from passes. File dialogs, clipboard/IME, accessibility, unsaved-change prompts, and NTFS permission/EFS behavior need their own applicable tests; the basic window smoke test does not certify them.

Do not distribute local tool caches, developer-only reports, raw user diagnostics, or unreviewed dependency binaries as source or release artifacts.
