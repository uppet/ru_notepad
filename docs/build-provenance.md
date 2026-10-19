# Building ru_notepad

This repository contains the editor’s source and build/test tools. The application is a Windows x64 executable generated from Ru through C; it does not embed a Python interpreter, libffi, or a Ru source interpreter. Python is a build-time compiler host and test driver.

## Pinned inputs

- **Ru 0.22.1:** public commit [`85c7821fda35aa79deeaf67b4d430f24ddd7f07f`](https://github.com/uppet/ru-language/commit/85c7821fda35aa79deeaf67b4d430f24ddd7f07f), tree `a770e367e84d87a0d2fcb6d49ea6f06da2dbe4ba`. Use a clean checkout of that exact commit. Its [language CI](https://github.com/uppet/ru-language/actions/runs/39229099554) passed all 13 jobs, including ten new transient-root-index regressions on all three Windows/Python combinations. The bounded `读U32LE阵` transport remains available. This compiler adds an indexed synchronous-callback root snapshot; that language result does not validate this application or establish a performance gain. The controlled [two-compiler comparison](markdown-callback-cost.md) isolates this runtime change against the exact preceding compiler, while the full product gate validates the complete pin upgrade.
- **Scintilla 5.6.7:** official [SourceForge source archive](https://sourceforge.net/projects/scintilla/files/scintilla/5.6.7/scintilla567.zip/download), exactly 1,904,249 bytes, SHA-256 `2309181e59e7da4659f890dbc128db7451ccd094748770e7be674b830494587c`. These are the same pinned bytes previously obtained from <https://www.scintilla.org/scintilla567.zip>. Verify the archive before extracting or building it. This is a reproducibility pin, not a claim that upstream signed the hash independently.
- **Lexilla 5.5.4:** official [SourceForge source archive](https://sourceforge.net/projects/scintilla/files/lexilla/5.5.4/lexilla554.zip/download), exactly 1,598,324 bytes, SHA-256 `5e0a21356e4e2f19d6a38ecd1c8172d5a2b7b4542940568b023386080db90fe0`. These are the same pinned bytes previously obtained from <https://www.scintilla.org/lexilla554.zip>. Build it beside the pinned Scintilla source and retain its own `License.txt`.
- **Unicode classification data:** Python 3.12 / Unicode 15.0.0 identifier predicates are retained as compact generated tables; the exact official Unicode notice ships in both ZIPs. Regeneration is documented in [Ru syntax scope](ru-language-syntax.md).
- **Application artwork:** original generated artwork and icon export details are documented in [assets/README.md](../assets/README.md).

The unchanged dependency source ZIPs and their scoped notices are tracked in [`third_party/source_archives`](../third_party/source_archives/README.md). Verified working copies and extracted source belong under the ignored `vendor/` directories. The application-owned `RuSyntax.dll` is built from reviewed `native/` C inputs; its source/header/table, compiler and binary hashes are validated with every executable receipt. It does not add a third-party source dependency. Each packaged Scintilla/Lexilla DLL must be built from the pinned source and accompanied by its upstream license. The application’s own license is still pending the owner’s choice.

## Offline official archive inputs

Current product CI uses the unchanged reviewed ZIP bytes in [`third_party/source_archives`](../third_party/source_archives/README.md). The preparation helper requires their exact sizes/hashes and bounded ZIP CRC/member checks, rejects linked or substituted files, and creates or verifies only the fixed ignored working copies. It neither downloads nor extracts archives. The build validates them again before extraction. Dependency changes require an explicit pin/source/notice review; there is no automatic mirror, browser-challenge handling, or network fallback.

The [Scintilla homepage](https://www.scintilla.org/) identifies the [upstream SourceForge distribution](https://sourceforge.net/projects/scintilla/files/); the URLs above remain provenance references. The [earlier acquisition failure](https://github.com/uppet/ru_notepad/actions/runs/38996733336) passed 134 orchestration and 42 package checks before a browser-challenge response prevented native work. A [subsequent exact-size rejection](https://github.com/uppet/ru_notepad/actions/runs/38998372940) passed 137 orchestration and 42 package checks, then rejected unexpected download bytes before extraction. That log did not preserve the response size/type or identify which archive failed; no response-body conclusion is inferred. Neither run executed the native product gate or produced release ZIPs.

Offline preparation removes this recurring acquisition step. A complete fresh Windows run is still required for application acceptance. Source archives are not included in either portable ZIP; necessary binary notices remain.

## Build tools

Use a Windows x64 GCC/MinGW-compatible toolchain with GCC, G++, windres, ar, ranlib, and make, plus Python 3.10+ and Git. `tools/build.py` accepts each compiler/tool path explicitly and checks the Ru checkout’s tree and clean working state. Run:

```sh
python tools/build.py --help
```

The build audits native-call argument counts, emits C, compiles the application or selected test source, embeds the same app resource and Common Controls v6 manifest in every executable, and copies all three required DLLs beside it. Test executables retain the console subsystem; only the application uses the GUI diagnostic launcher. Every executable receipt covers the manifest, resource script, icon and version, along with all src/*.ru and tests/*.ru files. Missing or changed resource inputs block packaging. Generated files belong in ignored `build/` and `dist/` directories.

The normal build command does not silently launch the resulting program. Linux-to-MinGW cross-compilation can produce a Windows PE executable, but it does not establish native Windows runtime behavior. Wine results, when available, must likewise be identified separately from Windows results.

## Portable compiler diagnostics

The pinned compiler emits source-style warnings during CLI checks and builds. Portable gates derive the exact expected `missing-statement-dot` diagnostics from the same source graph, bind them to the complete command and compiler/source hashes, and reject any missing, additional, reordered or changed visible diagnostic. The sole transport normalization is CRLF to LF. Runtime stderr remains strictly empty. Both CI hosts execute the real-CLI positive and negative controls before the portable Markdown gate. Raw compiler diagnostics stay in ignored local evidence directories, outside the public artifact allowlists. This verifies the diagnostics exposed by the Ru CLI; it does not claim that successful underlying GCC invocations expose every GCC warning.

## Windows acceptance

The project’s Windows CI is the application execution gate. It must run the native test executables, inspect their logs and exit status, create the real application window, and close it normally within a bounded time. Uploading an EXE or observing a successful compiler exit alone is insufficient.

The [0.1.3 Windows run](https://github.com/uppet/ru_notepad/actions/runs/38887294845) passed 835 assertions, two GUI gates and the full 500,039,680-byte editor roundtrip. Version 0.1.4 added Ru-owned syntax/folding and measured incremental-styling gates. Its [repair4 run](https://github.com/uppet/ru_notepad/actions/runs/38952771302) has green Linux and Windows jobs, with 1,427 assertions / 32 results verified from the original native evidence; both original ZIPs also passed independent verification. The [0.1.5 run](https://github.com/uppet/ru_notepad/actions/runs/38957923664) subsequently passed its full Linux helper gate, 149 syntax assertions and 1,451 total assertions across 32 results, including the GUI deadline and six edit measurements. It did not establish an end-to-end performance gain. The [0.1.6 product run](https://github.com/uppet/ru_notepad/actions/runs/38984124830) passed 1,487 assertions / 33 results and independent original-package review; its [paired direct-publication experiment](https://github.com/uppet/ru_notepad/actions/runs/38984124849) also passed. The 0.1.7 Ru-only policy candidate retains the same compiler/dependency pins and all native gates, and requires a new exact-build run plus a same-direct-route policy comparison; the same-route comparison completed in [run38998372873](https://github.com/uppet/ru_notepad/actions/runs/38998372873), and its offline product revision later passed [run39175562835](https://github.com/uppet/ru_notepad/actions/runs/39175562835). The 0.1.8 Markdown candidate with the updated compiler requires fresh full product validation. Only the exact BUILD.json establishes results for a particular artifact. Preserve failures and platform skips separately from passes. File dialogs, clipboard/IME, accessibility, unsaved-change prompts, and NTFS permission/EFS behavior need their own applicable tests; the basic window smoke test does not certify them.

Do not distribute local tool caches, developer-only reports, raw user diagnostics, or unreviewed dependency binaries as source or release artifacts.

## Two portable packages

After native execution, CI packages the identical verified runtime into a normal runtime ZIP and a self-contained tests ZIP. The first contains only the editor, Scintilla/Lexilla/RuSyntax, necessary docs, samples, notices, hashes and compact provenance. The latter also contains native test executables, scripts and bounded synthetic evidence. All four runtime binary hashes must match across packages; missing dependencies, receipts, notices, required assertions, timeout/kill cleanup or unexpected skips block both packages. Original 0.1.1 artifacts stay frozen.

## Historical research workflows

The completed policy-prefix comparison is manual-only and checks out the exact public `f91d9e8d008c48b00f98b5a19000639c18a61518` source. That historical source uses its original acquisition contract. The current product workflow uses the fixed offline archives; this does not retroactively change historical measurements.
