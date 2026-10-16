# File codec validation receipt

Date: 2026-10-16 (UTC).

This records the 0.1.0 codec validation snapshot. The codec source is unchanged in the 0.1.1 startup repair. Current binary identities are in each rebuilt `.build.json` and the package `BUILD.json`; older executable hashes below are historical, not the new package hashes. The current source and Windows executables are cross-built previews. No Windows native integration test has run.

## Verified for the current source

- `src/file_codec.ru`: Python-target syntax/import check passed without execution or DLL loading; standalone C-target `--allow-native` static ABI/signature check passed.
- `src/file_codec.ru`, `tests/file_codec_tests.ru`, and `tests/file_codec_security_probe.ru`: included in the final ten-entry native-C static check, all passed. The local build log is `build/logs/static-checks.log`.
- Both test entries were emitted to standalone C and compiled with real MinGW Windows x64 GCC using `tools/build.py` and the pinned Ru 0.21.1 snapshot below. No fabricated platform macros or application C shim were used.
- `file` identifies both outputs as PE32+, Windows x86-64, console subsystem. Static PE imports are `KERNEL32.dll` and `msvcrt.dll`; no Python or libffi runtime dependency is present. Windows system functions such as `advapi32.dll` security APIs are additionally bound at runtime by the Ru native module.
- Source hashes were checked against both build receipts after compilation. The receipts explicitly record `runtime_tested: false`.

The expected-failure helper was separately extracted unchanged and executed as a pure-Ru non-native scope smoke test. It correctly catches `卒` by mutating a shared array and reported one pass. Exact path-helper source fragments were also executed on Linux: 15 assertions passed (eight reserved/trailing-character rejections and seven namespace checks), plus eight ordinary path-component calls returned normally. These narrow helper runs do not exercise any Windows API, native file access, conversion, security descriptor, or replacement behavior.

## Test coverage prepared, not executed

- `file_codec_tests.exe`: 77 planned assertions, or 76 if the filesystem cannot create the optional hard-link fixture. This includes 16 encoding/empty round trips with exact-byte checks, malformed/NUL input, strict legacy failure preservation, external-modification conflicts, filename guards, sharing/read-only/hard-link refusals, and the inclusive 4 MiB boundary.
- `file_codec_security_tests.ps1` with `file_codec_security_probe.exe`: 28 planned assertions across protected-original and inherited-original fixtures in a deliberately permissive synthetic parent directory. The script exercises successful replacement and a forced sharing-denied replacement, checking retained staging/backup contents, copied ACE tuples, and protection flags.
- The ACL script has been statically reviewed only. Its comparisons cover sorted allow-only ACE tuples, not general effective access, ACE ordering, owner or conditional-ACE preservation. Final original protection-flag equality remains an explicit test, not an established result.

The test executables have not run on Wine or real Windows. The execution environment could not start Wine's required socket server; no workaround for restricted host paths was attempted. No native runtime pass, screenshot, ACL result, crash-durability result, or UI acceptance is claimed.

UTF-16BE `LCMAP_BYTEREV`, strict encoding conversion, replacement/backup behavior, resulting NTFS permissions, inherited protection flags, and all failure branches require actual Windows execution. EFS refusal, denied security-descriptor reads, disk-full/flush failures, metadata/named streams, and filesystem fault recovery need additional real-Windows tests. A later Wine pass would be compatibility evidence, not a substitute for those checks.

## Reproducible build records

Pinned Ru commit: `7f1b4348e461c7dc98b8b9dfe0c831f6e40d1b34`.
Pinned Ru tree: `3a9972dfd17fd570ef992ecffd9b5bccec1cc88d`.

- `build/file_codec_tests.build.json`, built at 2026-10-16T05:14:55Z, records the current suite source, all application-source hashes, generated C, compiler command and PE digest.
- `build/file_codec_security_probe.build.json`, built at 2026-10-16T05:15:08Z, records the same information for the optional ACL probe.

The common build helper passes an explicit `.exe` output path to MinGW. An earlier baseline CLI attempt encountered a Linux-host MinGW temporary-output naming issue, and an earlier full-suite check hit that baseline's analyzer budget. Those older ignored artifacts under `tests/file_codec_artifacts/` predate the secure-staging changes and are not validation of the current source. Use the final common build receipts above; do not distribute the earlier artifacts.

## Current source/artifact SHA-256

```text
eb1b8a3a8d2f11ffe24b48fa700ceaa9593cd5f67259cb35f2c704e9f78d7b10  src/file_codec.ru
79198de222447c817c5ef35779b3e2b2db679f97fd5f5e1f1075032012ff1f13  tests/file_codec_tests.ru
8cae54600a49562d651fd29c31825861bbf95a827846d75b12c5d61b790a0624  tests/file_codec_security_probe.ru
746b1c4b066e4029602fbd69c4f401ba3055b329ac3bfe50c1d5b5c9f117b51b  tests/file_codec_security_tests.ps1
2e84ceb8b9f289c5ceb484311b26377bb5defc109b5f3fa3ca3fb5daba27d283  build/file_codec_tests.exe
e05525f33e3f8ea1730b290865afa84071c907fb77b1c897ca230c227dcce636  build/file_codec_security_probe.exe
```
