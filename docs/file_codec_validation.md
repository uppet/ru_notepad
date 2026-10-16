# File codec validation receipt

Date: 2026-10-16 (UTC). Updated after the successful third real Windows CI run; prior failure evidence is retained below.

## Observed Windows failure and correction

The pre-correction codec failed on real Windows at `src/file_codec.ru:196` with `原生整数需要安全整数数、精确十进制句或原生整数`. Both the main codec suite and the ACL probe reached this failure; the ACL harness printed its protected-source fixture check, then failed ordinary replacement. These were executed failures, not skipped or never-run tests, and they establish no successful codec/ACL acceptance.

The parsed AST confirms the cause: `属性 其 位段 4 1 == 1` means a member call with arguments `4` and `(1 == 1)`. The bit width therefore becomes a fact rather than an integer. All five affected production checks have been changed to call `src/file_codec_flags.ru`:

- Directory attribute from `GetFileAttributesW`
- Reparse-point attribute from `GetFileAttributesW`
- Directory attribute from `GetFileInformationByHandle`
- EFS attribute before overwrite
- Read-only attribute before overwrite

The shared predicate uses `(属性 其 位段 起位 1) == 1`. Its AST has comparison outside the member call and numeric width `1`. The codec now contains exactly five shared-helper calls, with bit offsets `[0, 4, 4, 10, 14]`, and no raw `位段` call. Other member-call arguments were audited; buffer-size arithmetic, sequence increments, and the intentionally boolean missing-target parameter remain intentional.

This correction changes argument grouping only. Directory/reparse/EFS/read-only refusals, hard-link refusal, protected staging permissions, lossless conversion, conflict checks, and recovery/dirty-state behavior are retained. The previous expression could fail while inspecting an existing target or after a newly saved file was moved into place and its stamp was being read. Re-running actual Windows save and recovery tests is required; a portable predicate pass cannot establish that a file operation succeeded.

## Current portable verification

`tests/file_codec_flags.ru` imports the actual production helper. A pure-Ru receiver requires numeric offset and width, rejects width other than `1`, extracts the requested bit, and records calls. It covers all sixteen combinations of read-only/directory/reparse/EFS flags, normal attributes `128`, high unsigned bit `2147483648`, and maximum u32 value `4294967295`.

- Ru interpreter: **80/80 assertions passed**.
- Linux native C compiled with real Linux GCC: **80/80 assertions passed**.
- `tests/fixtures/bad_bitfield_arguments.ru` retains the original malformed expression: both runtimes exit 1 with `函数「位段」的实参「宽」须为数，实际收到事实`, before its method body runs.
- Current codec Python syntax/import and native-C static checks passed; no DLL was loaded by these checks.
- AST inspection verifies the five production call sites and the grouped shared expression. The repository's argument-shape checks provide additional regression protection, not a complete dynamic type proof.

These portable tests validate argument semantics using a strict receiver, not a Windows/native-u32 simulation. The pinned toolchain does not support importing `如:密` on Linux, even just to construct an integer. No platform guard was bypassed, no Windows macros were fabricated, and no Wine execution was attempted for this repair. Genuine native scalars and Windows APIs must be exercised by the Windows codec suite.

The earlier pure-Ru expected-failure scope smoke and extracted path-helper smoke also passed, but neither is a substitute for native file testing.

## Successful Windows verification of this correction

- `file_codec_tests.exe`: **77/77 assertions passed**, including the hard-link fixture. Coverage includes exact encoding bytes/round trips, UTF-16BE, NUL/invalid input, unchanged originals after failed conversion, conflicts, sharing/read-only/hard-link errors, and the inclusive 4 MiB boundary.
- `file_codec_security_tests.ps1` with `file_codec_security_probe.exe`: **28/28 assertions passed** over protected/inherited originals and a forced sharing-denied replacement. The earlier failed attempt is not counted as evidence.
- `file_codec_flags.exe`: **80/80 assertions passed** using the same production helper; real native-u32 checks are in the codec executable.

These results come from [Windows run 38863597991](https://github.com/uppet/ru_notepad/actions/runs/38863597991), public commit `d8d678206787c924141449e339cee9ebff54fc79`. All required fixtures executed, with no skips. Exact binary identities are in the 0.1.1 package BUILD.json. Pre-correction executables and their hashes do not validate the fix; later releases require their own full run.

The ACL comparisons cover sorted allow-only ACE tuples, not general effective access, ACE ordering, ownership, or conditional ACE preservation. The final original protection-flag assertion passed in that synthetic fixture. EFS refusal, denied security-descriptor reads, disk-full/flush errors, named-stream/metadata handling, and filesystem fault recovery need additional real-Windows checks even after ordinary codec tests pass.

## Corrected source SHA-256

```text
7bc9d72f8dda856cb2e10c67633004fd1167596cdc34b00b751215b494f76f95  src/file_codec.ru
5aa2376e2c9efca36aa2f8798a6d6526ec915bfeb9bc02003e21775176884bb2  src/file_codec_flags.ru
d5e549ee86b9900fff8a530d2baefc8f05abe4071e3c80876cdb8b072d8e71c1  tests/file_codec_flags.ru
7a27f613d072fb2bd08a9afe8e7a1041a767905c4db8ee69683a58012aba14c2  tests/fixtures/bad_bitfield_arguments.ru
```

The original codec integration and security-probe test sources remain unchanged by this grouping repair. The pinned Ru 0.21.1 toolchain is also unchanged; no language semantic change is part of this fix.
