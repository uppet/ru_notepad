# Localized file-filter buffer correction

## Observed failure and reproducible cause

The real Windows focused run 39387876194 completed all 114 Markdown-direct
assertions, then stopped after 908 i18n assertions. The public failure marker did
not include the private exception text. The fixed fixture ordering puts that
boundary immediately before the Spanish filter allocation assertion: eight setup
assertions, four complete languages at 191 each, then 136 Spanish assertions.
An exception while constructing the filter precedes that next assertion.

Independent execution of the original production constructor in both Ru backends
reproduced its failure. The Spanish filter needs 138 UTF-16 code units including
its final terminator, while the native structure API accepts at most 128 fields.
The previous constructor allocated one field per code unit. The first four
languages fit; Russian and Italian also fit when tested separately. This is a
production file-dialog construction defect, not only an incorrect test expected
value. The old fixture mirrored the same oversized structure and needed a
separate correction too. Host memory adapters establish that cause without
claiming real Windows ABI or User32 execution.

## Owned buffer, unchanged limits

The variable-length filter now remains in the managed memory returned by the
existing `密.UTF16` API. There are only two fixed one-WCHAR scratch structures,
not a variable-length native structure. The UTF-16 encoder's NUL rejection and
existing 16 MiB allocation ceiling remain unchanged. No compiler/runtime limit,
translation, wildcard, or filter pair is shortened or relaxed.

The constructor requires a nonempty even sequence of nonempty label/pattern
fields without the reserved pipe separator. It joins those fields with pipes,
including the final pipe, and encodes the result with its ordinary terminating
NUL. It then replaces only each pipe's two bytes with zero. The buffer length
stays exact, every other byte is preserved, and the final pipe plus encoder
terminator becomes the required double NUL.

`CharNextW` supplies opaque pointers while the original owned buffer stays alive;
no address is converted to a floating-point number or incremented by application
arithmetic. The next pointer is obtained before the current separator is zeroed.
Every traversal is bounded by the original UTF-16 code-unit count, including the
terminator, and must finish with the exact expected number of separators. The
Microsoft API can advance across combining marks; the ASCII separators must
still be visited. See [the CharNextW contract](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-charnextw).
Both scratch objects close before return; an ordinary failure closes all owned
memory and propagates the original failure. The caller retains its existing
close-after-dialog lifetime.

Invalid internal filter shapes have a new stable error key translated in all
seven languages. The current catalog consequently has 264 keys and 1,848 text
values. This does not change the explicit 289 policy assertion inventory.

## Independent validation and acceptance boundary

The native fixture reads the actual buffer through an independent, bounded
64-WCHAR-block structure. It compares every code unit against separately encoded
catalog text, checks exact allocation size, all four nonempty label/pattern pairs,
and exact final double NUL. Its four checks per language and total 1,417
assertions remain. The reader is test-only and does not construct production
filter bytes.

The maintained host memory probe extracts the production function body and uses
an independent byte oracle. Its owned test bridge and platform adapters are
explicit test models, including unit-wise and combining/surrogate-aware advance
models. These models do not certify the real `CharNextW` implementation. Long
labels, more than 128 code units, supplementary characters, leading combining
marks after separators, multiple filter pairs, rejected malformed inputs, and
ownership checks are distinct from Windows UI acceptance.

The maintained probe has 27 cases and 330 positive assertions in each real
backend, plus expected-error controls. Both traversal models also repeat the
long-filter lifecycle under C garbage-collection pressure and require zero live
objects at exit. The unchanged native structure limit is checked at 127, 128,
and 129 fields. The earlier constructor's Spanish failure is retained as
separate reproduction evidence, rather than described as a Windows error log.

The native fixture also emits a fixed 61-stage numeric sequence, identifying
language, requested width, and next assertion. It contains no user text, filenames,
paths, or exception messages. The focused runner only publishes a strictly
validated numeric prefix on failure. Missing, duplicated, reordered, malformed,
or incorrectly positioned markers suppress the extra progress record. Success
requires all 61 stages and all original assertions; older fixture output without
these stages is intentionally rejected by this updated focused runner.

Fresh focused Windows execution of the corrected production buffer is pending.
A complete 3,852-assertion / 42-result Windows product
run and strict preview eligibility remain necessary before shipping a ZIP.
