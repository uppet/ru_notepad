# Same-job Markdown width experiment (not product acceptance)

## Hypothesis and isolated change

Baseline: `6aa535d62c28cc9a03f33c3610fe99b3cf1bd14e`.
Compiler: `85c7821fda35aa79deeaf67b4d430f24ddd7f07f`, tree
`a770e367e84d87a0d2fcb6d49ea6f06da2dbe4ba`.

Only the two per-character `_宽` calls in `src/markdown_policy.ru` are replaced
with the same four Unicode-scalar threshold branches and direct byte-count
increments. The original function remains for other callers. This avoids a
dynamic function call, one heap allocation and two environment lookups per
consumed scalar in the measured local compiler representation. These counts
are not a prediction of Windows wall-clock improvement.

No timer budget, 64-line limit, bounds/error ordering, source/product acceptance
control, keyboard behavior or compiler implementation changes. Candidate and
baseline tracked files must be byte-identical except this fixed-hash policy and
the five named experiment files. All existing workflow triggers are retained.

## Execution and source identity

The independent `markdown-width-ab.yml` workflow runs only experimental-branch
pushes on one Windows 2022 host. The whole job has 75 minutes; the original
**30-second operation gate and 120-second owned-process deadline do not change**.
Baseline, candidate and compiler are distinct sibling checkouts; credentials are
not persisted. No previous-job artifact or cache supplies a binary.

Each arm runs the existing diagnostic controls, archive verification,
dependency builds, static checks and application build. After verifying the
baseline's full build receipt, its same-job Scintilla/Lexilla DLL bytes are copied
to the candidate's already validated dependency outputs. Its RuSyntax DLL and
unmodified native receipt are copied to a previously absent candidate native
cache only after both roots' complete native inputs match: sources, drivers,
compiler path/hash/version, flags, libraries and build key. The candidate's
unchanged build_native_helpers validates this cache hit and its application
build generates its own application receipt. This is an explicitly shared
same-job native build, not a claim of independent identical DLL compilation.
The cached native receipt retains its baseline compiler_command paths as origin
evidence; they must not be rewritten to pretend it was compiled in candidate.

A private handoff stamp binds run ID, attempt, both commits and canonical roots,
baseline application/native receipt hashes, all three DLL hashes and native key.
The stamp and all inputs/outputs are rechecked after candidate build and for every
GUI process. A prior-job stamp or unknown existing cache is rejected.
All three final DLL hashes must match; fixed numeric DLL IDs 1 Scintilla, 2 Lexilla,
3 RuSyntax and both SHA values are checked/logged immediately after both builds,
before profile preparation. The existing no-insert-timestamp option alone does
not prove identical output bytes across different linker output directories.

Each arm prepares its own release/profile once in a separate Python process
using its own module root. The coordinator imports only the candidate protocol,
whose common source, catalog and tools bytes are identical to baseline.
Every GUI process uses its explicit arm source root and receipt. Before every GUI process and after each diagnostically complete process,
the coordinator verifies both full source/build receipts,
runtime bytes, private runner receipts, compiler pin/tree/clean state and the
complete tracked-file relation. Official MSYS2 compiler executable hardlink aliases are allowed only for the
explicit expected compiler path; its path, bytes, version and native build key
are still revalidated. Symlinks/reparse points are rejected everywhere; source,
runtime and receipt files additionally require a single filesystem link.
There is no module ROOT swapping and no
seven-file receipt substituted for the full build-source receipt.

## Measurements

Release sequence is **A B B A A B B A**, each in a fresh directly owned process:
A is baseline, B is candidate. Four ordered paired contrasts use zero-based
indices `(0,1), (3,2), (4,5), (7,6)`; each ratio is candidate/baseline for
open, insert, backspace and Undo independently. Preserve the eight raw records
and their order; four pairs do not support a meaningful tail/p95 estimate.

After these eight releases, each arm runs its unchanged release/profile pair
for explanation only. Those extra releases do not enter the four paired
contrasts. Profile costs do not replace release timing. Twelve total processes
at most, with unchanged complete editing and one-or-two-command Undo contract.
A late but fully completed operation remains a sticky product-gate failure.
The diagnostic may finish while the workflow correctly fails that gate.

The 1 MB unclosed-fence fixture is deliberately narrow. This result cannot
establish all-document performance, GC time, allocation bytes, or whole-process
CPU attribution. Profile exclusive phases partition syntax timer roots only.
`bulk_prepare` covers the complete exclusive batch-publication path, not pure
serialization.

## Failure and public evidence

Only `build/markdown-width-ab-public/markdown-width-ab.json` is uploaded.
It is bounded, strict-schema numeric/hash data; no raw logs, GUI text, local
paths or exception messages. Public command traces contain fixed module IDs
(1 coordinator, 2 owned preparation, 3 phase runner, 4 edit runner, 5 observers),
source line numbers, and exception kinds (1 ValueError, 2 OSError, 3 TimeoutError,
4 subprocess timeout, 5 KeyError, 6 TypeError, 7 other).

An initial validated blank record is created before builds. It is incomplete,
not success, if a pre-measure step fails. During measurement each result is
atomically saved immediately; verification flags are set only after its full
post-run receipt check. A failure must not erase earlier measured records.
A missing pair is incomplete, never filled with a fabricated sample.
Any incomplete operation, uncertain retained-process/output cleanup or failed
drop cleanup blocks subsequent GUI spawning. The original retained Popen handle
and original deadline perform cleanup; no process-name killing, outer-worker
termination, extra grace period or relaxed safety check is introduced.

The public native_origin_sha256 binds the verified private handoff stamp without
exporting its local paths. It must be nonzero before any release attempt.

Top-level failure codes: 0 complete pass; 1 initial/incomplete; 2 complete but
product gate failed; 3 incomplete/cleanup stop; 4 coordinator or receipt failure.
The strict schema reserves 5–7 but does not emit them. Individual old diagnostic
failure codes retain their original meaning. `release_verified` and
`profile_verified` mean complete post-run identity validation, not product pass.

## Regression entry points

- `python tools/test_markdown_width_ab.py`: synthetic ordering, partial failure,
  public projection, dual-root real loader/adapter and full-receipt negative
  controls; never starts a GUI.
- `python tools/test_markdown_width_policy.py --baseline PATH --ru-root PATH`:
  fixed policy/compiler identity, existing 252 portable assertions plus full
  24-slot state and every-return comparisons in interpreter and generated C,
  all two-way short splits, Unicode width boundaries, CRLF splits, 60-range
  pauses, 1024/1025 limits and post-finish error ordering.
- Existing diagnostic control suites run independently for each arm.

A successful A/B diagnostic does not merge the policy or replace formal product
acceptance. Review paired Windows evidence, functional controls and any regressions
before deciding whether to propose a production change.
