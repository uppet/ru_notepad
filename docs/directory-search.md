# Directory search preview

This incremental search mode searches disk files under a folder the user explicitly chooses. It is separate from the current-document, fixed-selection, and all-open-document modes. It does not search unsaved buffer contents, change editor content, or replace files.

## First increment

- Recursive, case-sensitive literal matching only. The current-buffer case, whole-word, regex and selection settings are preserved, not applied.
- Strict Unicode scalar matching, without normalization or case folding. UTF-8, with or without BOM, and BOM-marked UTF-16LE/BE are accepted. UTF-32 BOMs, invalid sequences, incomplete code units and NUL-containing files are excluded in full. No legacy-code-page guessing.
- Results contain path, one-based line and Unicode-scalar column, and a bounded escaped preview. Byte positions refer to decoded BOM-free UTF-8, not on-disk UTF-16 bytes. CR, LF and CRLF each count as one line break.
- Results are a list only in this increment. Direct activation is disabled. Reopening a path and jumping to an old position would be unsafe if the file changed or a dirty tab already occupied that path. No read-only snapshot tabs are created. Verified ordinary-editor navigation is a separate increment.
- The captured query and root remain associated with the job even when the Find field or active tab changes. Invalid queries or a cancelled folder picker preserve the old results.

## Traversal and resource limits

Only local fixed-drive roots are supported. The worker validates the drive mapping and opens each component relative to a pinned parent directory handle. It rejects reparse points, junctions, mount points, substituted drives, network/device roots, and offline/recall objects. There is no permissive path-based fallback if the guarded native operations are unavailable. Hidden and system entries are not silently filtered; otherwise eligible disk text participates.

The worker copies events into a four-slot bounded queue. It never invokes Ru or Scintilla on the worker thread or retains pointers into Ru memory. Parsing, matching, result commitment and presentation remain in bounded Ru UI steps.

| Bound | Value |
| --- | --- |
| Query | 1–256 Unicode scalars and at most 1,024 UTF-8 bytes |
| Raw file | 8 MiB |
| Decoded UTF-8 per file | 16 MiB |
| Aggregate actual reads | 256 MiB |
| Charged file entries | 10,000 |
| Directories, including root | 2,000 |
| Descendant depth | 32 |
| Assembled path | At most 1,023 UTF-16 code units |
| Retained results | 2,000 |
| Preview | At most 32 preceding and 64 matched scalars |

Limit exits, cancellation, errors and exclusions must be visible; they are not a claim that every file was searched. A file contributes no rows until its complete bytes pass decoding and the worker confirms EOF and matching before/after identity, size and timestamp checks. When the result budget is filled inside a file, the remaining file bytes still undergo validation before its rows can be committed.

## Cancellation and consistency

Stop invalidates the current logical search immediately, retains previously committed rows and discards the unfinished file. A worker may still be retiring. No second worker starts until retirement completes. UI polling and cancellation never wait for filesystem I/O or join a thread; closing the results panel still permits cleanup. Application shutdown abandons the session without waiting, while the native helper retains its own lifetime until the worker exits.

The list describes observed file bytes, not a filesystem-wide atomic snapshot. Pinned handles and restricted sharing exclude ordinary rename/delete/write races; metadata and EOF checks catch ordinary changes. They cannot prove immutability against every pre-existing writable mapping or a privileged writer restoring metadata. Hard links may have names outside the selected tree. The first increment therefore makes no ownership or navigation guarantee from a path alone.

## Verification scope

Portable tests must exercise the actual Ru decoder and matcher with independent expected outputs on the interpreter and emitted C, including chunk splits, malformed tails, EOF, small work budgets, cancellation, capacity and protocol errors. Native Windows tests must exercise the actual transport, guarded traversal and cleanup. Controlled fault tests are identified separately from real filesystem cases. GUI tests must cover repeated and interrupted jobs, mode transitions, preserved document state, disabled result activation and all seven interface languages. The accepted preview must bind these checks to the same source, compiler and runtime bytes.

The separate historical C-native workflow is not replaced by this layered LLVM preview acceptance. Its failures must be reported separately; portable or source checks alone do not constitute Windows acceptance.
