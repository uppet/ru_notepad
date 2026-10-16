# Native streaming file tests

`tests/file_streaming_native.ru` is a real Windows x64 integration suite. Compile it with the approved Ru native C backend and run the resulting executable with one existing disposable directory:

```powershell
file_streaming_native.exe C:\path\to\disposable-test-directory
```

The directory must support sparse files (the standard NTFS GitHub-hosted Windows runner does). The suite requires no Python, PowerShell, fixture download, or external codec at runtime. It uses Windows system DLLs through `如:密` and creates only `ru-stream-test-*` fixture names. Successful runs delete their fixtures; failed runs retain them for investigation. `FILE_STREAMING_TESTS_PASS=99` and exactly 99 `PASS:` lines mark successful completion.

## Coverage

- UTF-8 with BOM above 4 MiB, UTF-8 without BOM above 16 MiB, and UTF-16LE with BOM above 4 MiB.
- Exact encoded-byte comparisons of every byte, with an independent Win32 reader and independently generated expected buffers. No checksum-only or file-size-only substitute.
- Exact decoded text compared incrementally against bounded producer patterns, with encoding, BOM, path, stamp, byte-count and read-call checks.
- UTF-8 three- and four-byte characters, UTF-16LE/BE surrogate pairs, and GBK double-byte characters crossing a 64 KiB boundary; Windows-1252 byte preservation.
- Invalid, partial and NUL-containing Unicode/legacy input; malformed UTF-8 and NUL at a 64 KiB boundary, incomplete GBK and UTF-16 pairs at 64 KiB EOF, and a partial UTF-8 tail after a full 64 KiB chunk.
- Producer failure after a staged write, late lossy legacy conversion, an oversized producer chunk and explicit cursor cancellation preserve the original bytes and stamp; a subsequent save still succeeds. Empty streams with and without Unicode BOMs also round-trip.
- Exactly 500,000,000 bytes opens without a confirmation callback. A 500,000,001-byte fixture prompts before any `ReadFile` or body buffer allocation; cancellation yields no text. Approval permits bounded first-chunk decoding. An unapproved cursor refuses reads; a failed confirmation callback closes its handle without touching the body.
- A 4,294,967,297-byte sparse fixture verifies precise 64-bit sizes and cancellation before reading.

## Memory and fixture bounds

Large round trips reuse a 10,240-codepoint pattern. Producers never assemble a whole file string; raw comparisons use a 65,536-byte read buffer and expected chunks below that bound. Sparse threshold fixtures contain only a 65,536-byte ASCII prefix followed by sparse holes. Tests intentionally stop after the first decoded chunk on accepted 500 MB files; they do not claim a complete 500 MB round trip.

Allow a 300-second runtime timeout and 128 MiB of physical scratch space. The sparse logical file size is larger than its allocated disk space.

The existing `file_codec_tests.ru` continues compatibility and security/error coverage (73 passes when hard links are supported). Its obsolete assertions that reads or saves above 4 MiB must fail were removed; the streaming suite replaces those assertions with successful real large-file operations.

## Verification scope

A successful `ru check --target c --allow-native` validates parsing and native signature analysis, not Windows execution or filesystem behavior. Native runtime results must come from the Windows CI job; Linux checks must not be reported as Windows test passes.

## Actual Scintilla large-document acceptance

`tests/editor_streaming_native.ru` requires Scintilla.dll beside its compiled executable and an existing disposable directory argument. Its normal mode emits exactly `EDITOR_STREAMING_TESTS_PASS=21`. It loads and saves 16,908,288 bytes through the real editor, verifies every output byte independently, checks supplementary UTF-8 range boundaries and CR|LF, and confirms failed NUL saves preserve the original and dirty state.

The separate mandatory large mode takes `DIRECTORY --large` and emits exactly `EDITOR_LARGEFILE_TESTS_PASS=10`. It creates 500,039,680 bytes of actual ASCII text, proves approval precedes any ReadFile/content buffer, loads the entire document with TEXT_LARGE|STYLES_NONE, saves the entire native buffer through bounded ranges, and compares every output byte independently. It is not satisfied by accepting only the first block of a sparse file. Budget roughly 3 GiB available memory, 2 GiB free disk and 15 minutes; these are conservative harness budgets, not measured performance claims.

Both modes are native Windows execution obligations. C syntax/generation or a successful Linux-to-Windows cross-build does not establish their runtime result.

## Main-window and detached GUI integration

`tests/app_streaming_native.ru` has 63 planned assertions through the real main
WNDPROC and WM_TIMER pump. It uses a 33,030,144-byte text fixture to exercise
streaming beyond the previous limits and the 32 MB plain-text performance mode,
with partial-load cancellation, native hard-link duplicate identity, dirty-tab
preservation, on-disk temporary-file deletion, revision guards and asynchronous
close continuations. A separate detached GUI gate opens Unicode CLI/drop files,
checks exact content, observes a responsive partial 128 MiB open, cancels its
remaining queue and obtains normal exit. These tests do not turn synchronous
slow I/O or long-line layout into a guaranteed-latency operation.
