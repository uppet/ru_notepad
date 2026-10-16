# File codec: implementation contract

The application file layer is pure Ru source in `src/file_codec.ru`. Its only import is `如:密`; it binds Windows system APIs directly. It does not invoke Python, a C helper, a shell, or another executable when opening or saving. The Ru compiler may be hosted by Python at build time; the Windows executable has no Python runtime requirement.

## Public API

Import this module at application startup, before registering or entering a native UI callback. All native signatures, DLL bindings, layouts, and the `文件` object are initialized at module import.

```ru
文件库 取 外言 'file_codec.ru'.
文档 取 文件库 其 读文件 路径 0.
新戳 取 文件库 其 写文件 路径 新文本 文档['encoding'] 文档['bom'] 文档['stamp'].
```

Equivalent object methods are `文件库 其 文件 其 读取 路径 代码页` and `文件库 其 文件 其 写入 路径 文本 编码 BOM 预期stamp`. The top-level name `读取` is a protected Ru builtin, hence the module wrapper is named `读文件`.

`读文件` returns a map with these fields:

- `text`: exact decoded text, including its original line endings
- `encoding`: 65001 (UTF-8), 1200 (UTF-16LE), 1201 (UTF-16BE), 1252 (Windows-1252), or 936 (Windows GBK)
- `bom`: whether a recognized BOM was present
- `stamp`: opaque conflict token for the opened file
- `path`: canonical absolute path used for the read; retain this path in editor state

`绝对路径 路径` returns the same checked canonical absolute path without opening the file. Canonicalize command-line and dialog paths before storing them, because another file dialog may change the process working directory.

`写文件` returns the new conflict token. Preserve that token for the next save. An empty expected token allows an initial Save As selection; the caller must obtain overwrite confirmation in its file dialog. An empty token is not an instruction to overwrite whatever appears later.

Errors intended for the UI are raised with `卒` and should be caught with `试` / `救`. Opening should replace editor state only after the complete read has succeeded. Saving should clear the dirty flag only after the function returns successfully. Native allocation exhaustion and a fundamentally invalid native ABI are not recoverable file errors.

## Encoding and bounds

The maximum file length is 4,194,304 bytes (4 MiB), including any BOM. A file exactly at the limit is accepted if its encoding and text are valid. A save whose encoded bytes plus BOM exceed that limit fails before any destination replacement.

With code page 0, a recognized BOM determines the encoding; otherwise only strict UTF-8 is attempted. Invalid UTF-8 produces an explicit instruction to reopen with Windows-1252 or GBK. No statistical encoding detection, system ACP fallback, replacement character insertion, or silent legacy guessing occurs. A BOM takes precedence even if the caller specifies another code page. BOM-less UTF-16 is supported only when the caller explicitly chooses 1200 or 1201.

- UTF-8 is decoded by `MultiByteToWideChar` with `MB_ERR_INVALID_CHARS`.
- UTF-16 must contain an even number of bytes. UTF-16BE is byte-swapped into a separate buffer by `LCMapStringW` using only `LCMAP_BYTEREV`, then validated like UTF-16LE.
- UTF-16 is validated using `WideCharToMultiByte` with UTF-8 plus `WC_ERR_INVALID_CHARS` before Ru's strict decoder runs.
- Both UTF-32 BOM forms are rejected.
- Every decoded UTF-16 buffer has an owned, zero-filled extra terminator. The native string length must equal the explicit decoded length, so embedded NUL cannot silently truncate a document.
- Windows-1252 and CP936 are explicit choices. Legacy output uses `WC_NO_BEST_FIT_CHARS`, rejects a set `lpUsedDefaultChar`, and additionally requires an exact Unicode round trip. Unsupported characters are never changed to `?` or a visually similar character.
- Legacy encodings cannot have a BOM.

Native buffers are individually bounded at or below the `如:密` 16 MiB ceiling. Conversion counts use explicit byte or UTF-16-unit lengths. No pointer arithmetic or unbounded externally owned pointer decoding is used. Paths and text are passed through owned UTF-16 buffers. Binary data containing NUL, invalid UTF-8, and invalid UTF-16 is rejected; the layer does not claim to distinguish all binary formats from valid non-NUL text.

Reference contracts: [MultiByteToWideChar](https://learn.microsoft.com/en-us/windows/win32/api/stringapiset/nf-stringapiset-multibytetowidechar), [WideCharToMultiByte](https://learn.microsoft.com/en-us/windows/win32/api/stringapiset/nf-stringapiset-widechartomultibyte), [LCMapStringW](https://learn.microsoft.com/en-us/windows/win32/api/winnls/nf-winnls-lcmapstringw), and [LCMAP_BYTEREV](https://learn.microsoft.com/en-us/windows/win32/api/winnls/nf-winnls-lcmapstringex).

## Conflict detection and scope

The token consists of volume serial number, high/low file ID, last-write FILETIME high/low values, and file length high/low values. These values remain exact native integers until rendered as decimal components. The token is not a content hash; same-length content changes with a restored timestamp and matching identity can be missed.

Read handles permit read sharing only. Another writer or replacing process cannot ordinarily coexist with that read snapshot. Existing-file saves verify their token twice, including immediately before replacement. A read guard is closed immediately before the replacement API call because that call requires deletion access.

There is a check-to-replace race: this API is not a filesystem compare-and-swap transaction. Another process may replace or mutate the path after the final guard closes. Directory reparse changes, network filesystem semantics, malicious concurrent processes, hardware failure, and power-loss durability are outside this initial guarantee. A stamp mismatch aborts the save; the UI should offer reopen or Save As, without automatically overriding the conflict.

The codec supports normal file paths and rejects device namespaces (including mixed-slash spellings), reserved DOS device names and extension aliases, control characters, ambiguous trailing-space/dot components, alternate-data-stream paths, directories, and directly selected reparse points/symbolic links. Both raw and normalized paths are checked. It does not promise extended `\\?\` path support. Windows path-length and access restrictions are surfaced as errors. It does not change the original line endings. Read-only files, EFS-encrypted files, and files with multiple hard links can be opened, but cannot be replaced by this initial editor. EFS overwrite is rejected before staging because this version does not create encrypted staging files.

## Save and recovery sequence

1. Encode and validate the entire output before any replacement is attempted.
2. Inspect the selected target. Capture its current stamp even for a confirmed Save As overwrite. While the existing-file read guard is still held, read its DACL with `GetFileSecurityW`. Fail closed if security information cannot be obtained or validated.
3. Convert the owned self-relative security copy to an absolute descriptor using `MakeAbsoluteSD`, with separate owned component buffers. Set `SE_DACL_PROTECTED` only on this in-memory copy to prevent parent ACE inheritance from broadening temporary-file access. Supply it through `SECURITY_ATTRIBUTES` at `CREATE_NEW` for both the staged document and reserved backup. All referenced buffers stay alive throughout saving. New destinations without an existing security descriptor use normal creation permissions. Existing temporary files are never truncated.
4. Write the BOM and body using checked, explicit byte counts. A short write fails. Call `FlushFileBuffers`, then close the temporary handle.
5. For an existing destination, reserve a new same-directory recovery-backup name using `CREATE_NEW`, recheck the target stamp, and call `ReplaceFileW` with flags 0. No ACL or metadata-merge errors are ignored. The original file's metadata is preserved according to the Windows API contract, including DACL and named streams. This is not a promise to preserve every filesystem-specific property.
6. For a destination absent at the initial check, verify it is still absent and call `MoveFileExW` with `MOVEFILE_WRITE_THROUGH` only. `MOVEFILE_REPLACE_EXISTING` is deliberately omitted, so a file arriving in the final race window is not overwritten.
7. Reopen the result, obtain its new stamp, and remove the owned recovery backup. Only then return success.

The codec never opens an existing destination with truncating `CREATE_ALWAYS`. Failures before replacement leave its contents intact and clean up owned temporary files when possible. `ReplaceFileW` itself has documented partial-failure states, so a replacement failure does not mean the original pathname still exists. In that case the codec retains the temporary/recovery files and includes their exact paths in the error. A reserved `.bak` may still be an empty placeholder if replacement failed before moving the original; inspect the original and both recovery paths rather than assuming every backup contains data. Do not delete those recovery files before examining them. It does not silently retry using a less safe overwrite operation.

If replacement succeeded but the new stamp cannot be obtained, or the old recovery backup cannot be removed, the error explicitly says the file was written. The editor should keep the buffer and dirty state, show the message, and ask the user to reopen/check the file before another save. A `.bak` left after successful replacement contains the previous document, so the user should treat it as potentially sensitive. The backup is normally removed after successful verification.

No original file permissions are changed by the staging setup. The code does not use `SetFileSecurity` or relax ACL merge errors. The protected copied DACL is applied when each new staging file is created, before content is written. EFS overwrites fail closed. Actual resulting DACL inheritance and replacement behavior still require real Windows filesystem verification; static checks are not evidence of effective permissions.

`FlushFileBuffers` protects the completed temporary data; `ReplaceFileW` does not support its nominal write-through flag. No guarantee is made against every crash, power loss, storage-controller failure, or network filesystem behavior. This is a same-directory native replacement scheme with recovery, not a transactional database.

Security descriptor contracts: [GetFileSecurityW](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-getfilesecurityw), [MakeAbsoluteSD](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-makeabsolutesd), [SetSecurityDescriptorControl](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-setsecuritydescriptorcontrol), and [SECURITY_ATTRIBUTES](https://learn.microsoft.com/en-us/previous-versions/windows/desktop/legacy/aa379560(v=vs.85)).

References: [ReplaceFileW and its recovery/metadata behavior](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-replacefilew), [MoveFileExW](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-movefileexw), and [CreateFileW sharing and creation modes](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew).

## Native integration tests

`tests/file_codec_tests.ru` is a pure-Ru Windows x64 test executable. It requires an explicit disposable, existing directory argument and uses only `ru-codec-test-` prefixed fixtures there. It checks exact on-disk bytes and round trips for UTF-8 with/without BOM, UTF-16LE/BE with/without BOM, Windows-1252, CP936, and empty files; supplementary Unicode and non-ASCII filenames; malformed sequences and embedded NUL; refusal of lossy legacy saves; unchanged originals after conversion failure; external modification conflicts; sharing errors; read-only/hard-link replacement refusal; and exact/over-limit 4 MiB cases. The suite has 77 planned assertions, or 76 when its optional hard-link fixture is unsupported. These counts describe coverage, not a completed test run.

Static checks:

```text
python3 /path/to/ru check --target python src/file_codec.ru
python3 /path/to/ru check --target c --allow-native src/file_codec.ru
python3 /path/to/ru check --target c --allow-native tests/file_codec_tests.ru
```

Native build/run on an authorized Windows x64 environment:

```text
py -3 /path/to/ru build --allow-native tests/file_codec_tests.ru -o file_codec_tests.exe
file_codec_tests.exe C:\disposable-codec-test-directory
```

Syntax checks do not prove Windows API behavior. A Wine test is useful compatibility evidence but does not replace a real Windows x64 run, filesystem fault injection, or UI tests.

## Real Windows ACL regression

Build `tests/file_codec_security_probe.ru` as a Windows x64 executable, then explicitly run `tests/file_codec_security_tests.ps1 -ProbeExe <probe.exe> -TestDirectory <trusted disposable local NTFS directory>` on real Windows. This harness creates a unique directory of synthetic test data only. It deliberately gives that new fixture directory an inheritable permissive ACL, creates both a protected original and an inherited-ACE original, and checks:

- Successful replacement preserves the sorted access-rule tuples and original protection flag for the allow-only fixtures
- A deletion-denying read handle forces replacement failure after staging
- The unchanged original and retained new contents are recoverable in that sharing-failure case
- Retained `.tmp` and `.bak` files have protected DACLs and the same sorted access-rule tuples as the original

The harness compares trustee, allow/deny type, rights, inheritance flags, and propagation flags after sorting. It ignores inherited provenance and does not evaluate ACE ordering, ownership, conditional ACEs, or general Windows effective access. Passing these allow-only fixtures must not be presented as proof for arbitrary ACLs. The original protection-flag equality assertion deliberately remains: whether `ReplaceFileW` retains that flag when staging is protected needs runtime verification.

The harness removes only its uniquely created fixture folder. It must not be run on real documents or a shared untrusted test directory. The second real Windows CI attempt executed this harness but failed during the first ordinary replacement because of the attribute-bit argument error described below. The repaired run is pending; final protection-flag behavior is not established. EFS rejection, inaccessible DACLs, disk-full/flush errors, and unusual filesystems need separate real-Windows fault tests.

## Attribute-bit argument regression

All directory, reparse-point, EFS and read-only checks use `src/file_codec_flags.ru` as a shared predicate. Its full `位段` member call is grouped before comparison: `(属性 其 位段 起位 1) == 1`. Without these parentheses, Ru parses `1 == 1` as the second argument, so the native bit-width argument becomes a fact instead of a number. This was observed in real Windows CI before the correction. No language semantics, native permissions, destination restrictions, or save-failure retention policy were relaxed.

`tests/file_codec_flags.ru` runs this exact production helper against a strict pure-Ru receiver with numeric bit-offset/width parameters. It covers every combination of read-only/directory/reparse/EFS flags, normal attributes, a high unsigned bit, the maximum u32 value, and exact call counts: 80 assertions passed in both the interpreter and Linux native C. `tests/fixtures/bad_bitfield_arguments.ru` retains the original ungrouped expression; both runtimes reject its fact-valued width before the receiver method body runs. These are parameter-semantics tests, not a claim that native u32 or Windows APIs run on Linux. The actual codec integration suite must verify the repaired predicates with genuine Windows native scalars.
