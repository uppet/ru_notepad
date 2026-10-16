# File codec: implementation contract

The application file layer is pure Ru source in `src/file_codec.ru`. It imports `如:密` and the small attribute predicate module; it binds Windows system APIs directly. It does not invoke Python, a C helper, a shell, or another executable when opening or saving. The Ru compiler may be hosted by Python at build time; the Windows executable has no Python runtime requirement.

## Streaming API and ownership

Import the module at application startup before entering native UI callbacks. The production open/save paths use step cursors, never whole-document Ru strings:

- `准备读取 路径 代码页` opens an ordinary-file read guard, obtains exact 64-bit size, `stamp`, `fileIdentity` (volume/file ID), and canonical `path`. It performs **no ReadFile**, including BOM reads, and allocates no file-content buffer.
- `确认读取 状态 确认` invokes `确认(size)` only when the original file is **strictly greater than 500,000,000 bytes**. A false result closes the snapshot and returns false. An exception also closes it. Reconfirming the same approved cursor does not prompt twice.
- `读取一步 状态` returns one bounded decoded text chunk. It refuses an unapproved cursor. A final `空` is returned only after a one-byte EOF growth probe and an unchanged identity/size/write-time stamp, with the reader closed. Unexpected short reads fail closed rather than returning partial text. `关闭读取 状态` cancels idempotently.
- Reader metadata includes `size` / `bytes` (original bytes including BOM), `textBytes` (decoded UTF-8 bytes), `encoding`, `bom`, `position`, `readCalls`, `readBytes`, `bufferBytes`, `done`, and `closed`. Counters are per cursor. `bufferBytes` is the raw-buffer high-water bound, not total process memory; decoder scratch and Scintilla are separate.
- `准备写入 路径 编码 BOM 预期stamp` performs target/ACL preflight and creates protected same-directory staging. `写入一段 状态 文本` validates, losslessly encodes, and writes a bounded chunk. `完成写入 状态` flushes and performs the original guarded replacement/recovery sequence, returning the new stamp. Successful writer metadata also contains `fileIdentity` and `stamp`.
- `取消写入 状态` closes resources and deletes only owned staging files before replacement. Cleanup failure is reported with paths. Replacement-phase failures retain recovery files and their paths, as described below.

The parent UI advances one or a few bounded steps per message-loop tick; it must never call into Ru from a background native thread. It owns the pending hidden editor, obtains large-file approval before constructing that editor, and commits a tab only after checked EOF. During saving it locks the source read-only and verifies document revision before each step and before commit. Path, identity, encoding state, and the savepoint change only after successful file commit. Cancelling or failing preserves the previously committed tabs and their dirty state.

`editor.ru` exposes `开始载入(hwnd,size)`, `追加文本(loadState,text)`, `完成载入(loadState)`, `开始取文(hwnd)`, and `取文一步(sourceState)`. Loads disable undo collection until completion and retain CR/LF boundary state. New Scintilla documents use `SC_DOCUMENTOPTION_TEXT_LARGE`; files at least 32,000,000 bytes also use `STYLES_NONE` as a separate performance threshold, not a size limit or confirmation threshold. The application uses plain text and disables wrapping for these large-file loads. `SCI_CREATEDOCUMENT` / `SCI_SETDOCPOINTER` / `SCI_RELEASEDOCUMENT` ownership is balanced. Save extraction uses `SCI_GETTEXTRANGEFULL` with full-width positions and strict UTF-8/NUL validation of each owned range.

`流读文件(path, codepage, confirm, consume)` and `流写文件(path, produce, encoding, bom, stamp)` are synchronous streaming adapters for tests and non-UI callers. `consume(text)` receives one bounded string; `produce()` returns one string of at most 65,536 Unicode code points or `空` at EOF. These adapters do not collect all chunks.

The compatibility whole-string helpers `读文件` and `editor.文本` explicitly refuse inputs over 1 MiB so accidental callers cannot regress to unbounded concatenation. **That is a convenience-API guard, not an editor document-size limit.** `写文件` slices its already-existing input string into bounded output chunks. The UI does not use these helpers for document open/save. `绝对路径` remains the checked path canonicalizer. The `文件.读取/写入` methods retain compatibility-helper semantics.

Errors use `卒` and should be caught with `试` / `救`. Native allocation exhaustion and an invalid native ABI are not guaranteed recoverable. Streaming bounds scratch buffers; Scintilla still holds the complete editable document and may require substantially more RAM than the file's encoded size. There is no claim of infinite-memory editing. Before native-to-Ru conversion, size words are checked against Ru's precise integer range (2^53−1) and the two native size probes must agree; extreme unsupported sizes raise a recoverable error rather than rounding or invoking a fatal native conversion.

## Encoding and bounded chunks

There is no 4 MiB, 16 MiB, or 500 MB file-size cap. The 500 MB value is a cancellable pre-read warning. Each raw read is at most 65,536 bytes; owned conversion buffers and text fragments are bounded independently of document length and remain far below the unchanged `如:密` 16 MiB per-allocation ceiling. Saving accepts at most 65,536 code points per step; at worst its UTF-16/UTF-8 scratch is approximately 256 KiB. Paths and copied security descriptors retain their separate pre-existing API bounds.

With code page 0, a recognized BOM determines the encoding; otherwise only strict UTF-8 is attempted. A BOM takes precedence over an explicitly selected code page. BOM-less UTF-16 requires explicit selection. Both UTF-32 BOMs are rejected. No guessing, system ACP fallback, replacement insertion, or silent legacy fallback occurs.

Each nonfinal raw block is decoded whole first. Only on failure may a valid prefix ending up to three bytes earlier be used (one byte for CP936). The remaining bytes are reread by seeking the same guarded handle to the positively advancing accepted offset. This covers UTF-8 multibyte sequences, UTF-16 surrogate pairs/odd bytes, and CP936 double-byte characters without classifying a valid CP936 trail byte as a lead. Final incomplete sequences always fail. An invalid interior or NUL eventually fails and the pending editor is discarded.

- UTF-8 and explicit legacy input use `MultiByteToWideChar(MB_ERR_INVALID_CHARS)`.
- UTF-16BE is byte-swapped with `LCMAP_BYTEREV`; UTF-16 is validated with `WideCharToMultiByte(UTF8, WC_ERR_INVALID_CHARS)`.
- Prefix copies use bounded `RtlMoveMemory` into owned buffers with extra zero terminators. Native string length must equal the decoded explicit length, preventing NUL truncation. There is no bare pointer arithmetic or decoding of externally owned pointers.
- Windows-1252 and GBK output use `WC_NO_BEST_FIT_CHARS`, reject `lpUsedDefaultChar`, and require an exact Unicode round trip. Legacy BOMs are rejected.
- Original line-ending bytes are retained. Detection remembers a trailing CR between chunks so CR|LF is recognized correctly.

Reading and writing use synchronous bounded Windows calls. The UI can cancel between steps; a slow or stalled individual filesystem call, including UNC access, can delay cancellation. This implementation does not promise interruptible in-flight I/O.

Reference contracts: [MultiByteToWideChar](https://learn.microsoft.com/en-us/windows/win32/api/stringapiset/nf-stringapiset-multibytetowidechar), [WideCharToMultiByte](https://learn.microsoft.com/en-us/windows/win32/api/stringapiset/nf-stringapiset-widechartomultibyte), [LCMapStringW](https://learn.microsoft.com/en-us/windows/win32/api/winnls/nf-winnls-lcmapstringw), and [Scintilla document ownership and options](https://www.scintilla.org/ScintillaDoc.html#SCI_CREATEDOCUMENT).

## Conflict detection and scope

The token consists of volume serial number, high/low file ID, last-write FILETIME high/low values, and file length high/low values. These values remain exact native integers until rendered as decimal components. The token is not a content hash; same-length content changes with a restored timestamp and matching identity can be missed.

Read handles permit read sharing only. Another writer or replacing process cannot ordinarily coexist with that read snapshot. Existing-file saves verify their token twice, including immediately before replacement. A read guard is closed immediately before the replacement API call because that call requires deletion access.

There is a check-to-replace race: this API is not a filesystem compare-and-swap transaction. Another process may replace or mutate the path after the final guard closes. Directory reparse changes, network filesystem semantics, malicious concurrent processes, hardware failure, and power-loss durability are outside this initial guarantee. A stamp mismatch aborts the save; the UI should offer reopen or Save As, without automatically overriding the conflict.

The codec supports normal file paths and rejects device namespaces (including mixed-slash spellings), reserved DOS device names and extension aliases, control characters, ambiguous trailing-space/dot components, alternate-data-stream paths, directories, and directly selected reparse points/symbolic links. Both raw and normalized paths are checked. It does not promise extended `\\?\` path support. Windows path-length and access restrictions are surfaced as errors. It does not change the original line endings. Read-only files, EFS-encrypted files, and files with multiple hard links can be opened, but cannot be replaced by this initial editor. EFS overwrite is rejected before staging because this version does not create encrypted staging files.

## Save and recovery sequence

1. Validate encoding/BOM policy, then encode and validate each bounded chunk into staging. All chunks must succeed before replacement is attempted; a late conversion/source failure removes owned staging and leaves the destination intact.
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

`tests/file_codec_tests.ru` is a pure-Ru Windows x64 test executable. It requires an explicit disposable, existing directory argument and uses only `ru-codec-test-` prefixed fixtures there. It checks exact on-disk bytes and round trips for UTF-8 with/without BOM, UTF-16LE/BE with/without BOM, Windows-1252, CP936, and empty files; supplementary Unicode and non-ASCII filenames; malformed sequences and embedded NUL; refusal of lossy legacy saves; unchanged originals after conversion failure; external modification conflicts; sharing errors; read-only/hard-link replacement refusal; and compatibility API behavior. Historical 4 MiB rejection assertions were removed; new streaming suites cover successful larger files. The legacy suite has 73 planned assertions, or 72 when its optional hard-link fixture is unsupported. These counts describe coverage, not a completed test run. See [streaming coverage](file_streaming_tests.md) for the additional 99 codec assertions and 21 normal / 10 >500 MB editor assertions.

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
