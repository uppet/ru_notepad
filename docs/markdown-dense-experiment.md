# Source-generated Markdown fence scan experiment

This is a bounded experiment, **not complete dense mode or S1 acceptance**, and
not a repair for unfenced single-line Markdown. No production branch merge,
keyboard change, or relaxed 30-second operation / 120-second process gate is
included.

## Source and consumer

Frozen ordinary oracle: `uppet/ru_notepad` commit
`a09a2eaf8d976493a01a7098de0ea516c3023cbc`, tree
`bf06849a4308753cba2ca98d5e1f5309ae6e6580`. The local baseline manifest verified
all 254 blobs against that GitHub tree. `markdown_policy.ru` keeps its original
`喂入` body and every existing helper byte-for-byte. A mechanical drift control
permits only the documented alternate-body injection and indentation change.

The algorithm is ordinary Ru in `src/markdown_ascii_kernel.ru`: a bounded loop
returns the length of consecutive bytes below 128 except CR, LF and `>`.
`experiments/markdown-dense-manifest.json` explicitly assigns readonly u8 view,
u32 begin/end/result and checked range/effect contracts. The language compiler
lowers this source AST through generic typed IR to C/JS; there is no handwritten
Markdown C kernel and no replacement counter.

Actual consumer wiring is `markdown_syntax._一步` → `markdown_dense.喂入` →
`markdown_policy.喂入视图` → manifest-selected `ASCII段`. Ordinary builds leave the
source-only experiment flag **off**. Passing a manifest alone is not activation.

## Safety and units

- `_读块` validates UTF8/no embedded NUL, decodes to an ordinary Ru sentence and
  closes its original NativeMemory. The experiment does **not** borrow it.
- `markdown_dense.喂入` makes an explicit UTF8 allocation/copy for an eligible
  synchronous feed and closes it on success and ordinary recoverable panic. Generated kernel/ABI
  failure releases the borrow first but retains the existing fatal runtime-error
  behavior; it is not caught by ordinary `试/救`. Nothing borrowed survives
  the function, a UI yield, edit/revision replacement or Undo.
- At most one adaptation occurs per **synchronous feed**, not necessarily per
  original `_读块`: after a 60-range pause the remaining ordinary sentence can
  need another adaptation. This cost is included; no zero-copy claim is made.
- Begin is the cumulative `态[23]` delta since entry, sampled **before** the next
  character is read/counted; end is the UTF8 memory size minus its final NUL.
  Ranges are half-open. The equivalence contract is for valid editor policy
  states: cumulative consumed bytes and the current chunk endpoint remain in the
  exact integer range through 2^53−1. Hand-forged NaN/out-of-range state slots are
  not covered. Unicode takes the original scalar/width path. Only an ASCII run
  permits byte length to advance the ordinary scalar index equally.
- The original whole-feed eligibility predicate remains: active fence, no raw
  HTML block, no `>`, at least one CR/LF. A run additionally requires the existing
  proof that this fence line cannot close. Possible closers, non-ASCII, CR/LF,
  `>` fallback, CR carry, range pauses and final deferred materialization retain
  their original paths. All 24 state slots and stack/header/closer aliases remain.
- The byte kernel accepts byte zero as ASCII and never treats it as a terminator;
  the actual editor input contract rejects embedded NUL earlier. Ru source string
  literals and native UTF8 adaptation also reject NUL. These are distinct layers.

## Explicit actual-application build

Use one reviewed compiler commit/tree for **both** arms, two clean sibling
checkouts at the **same notepad commit**, and the same manifest:

```
python tools/build.py <unchanged existing toolchain/build arguments> \
  --allow-toolchain-tree <reviewed-new-compiler-tree> \
  --experimental-mi-manifest experiments/markdown-dense-manifest.json \
  --experimental-markdown-dense ordinary

python tools/build.py <same toolchain/build arguments, other sibling root> \
  --allow-toolchain-tree <same-reviewed-new-compiler-tree> \
  --experimental-mi-manifest experiments/markdown-dense-manifest.json \
  --experimental-markdown-dense dense
```

Both explicit flags are required. `markdown_dense_build.py` verifies fixed hashes
of all four changed/imported Ru sources and the manifest. It changes exactly one
parsed fact (`enabled` false→true for dense) while retaining resolved imports;
source files are never rewritten. The build receipt records arm, source and
compiled-syntax hashes, manifest, driver and source-patch count, and rechecks
inputs after compilation. The ordinary arm compiles the same dense kernel but
never selects it, preventing a compiler-version difference being counted as the
kernel benefit. `check_markdown_dense_integration.py` generates both real
`src/main.ru` arms and requires exactly one `v_fact(0)`→`v_fact(1)` C difference.
This generation check is **not** Windows execution or GUI acceptance.

## Local evidence

1. Existing 252 portable assertions pass in interpreter and generated host C.
2. Independent a09 oracle vs alternate policy, each feed: **15,290** full-state
   returns, **3,998** error-order/state checks and **5** 60-range pauses, both
   ordinary-array interpreter/C and actual NativeMemory manifest C path.
   Retained stack, header and closer aliases are compared after each feed.
3. Corpus includes every two-way scalar split of existing policy examples,
   Unicode-width boundaries, Unicode→ASCII, CRLF across feeds, final-byte/empty
   ranges, possible fence closers, `>` fallback, long partial lines, 1024/1025
   limits and five edit-text revision replays including both Undo texts. Revision
   replay is policy-level coverage, **not an actual GUI Undo run**.
4. Actual kernel: **8,320** valid byte-range cases agree across ordinary Ru
   interpreter, source-generated C and source-generated JS. Invalid view/range,
   borrow lifetime and cleanup are separately exercised by the language bridge
   controls; compute-only C/JS helpers are not the ordinary bridge contract.
5. An additional native policy oracle run used UBSan and test-only
   kernel call instrumentation: **2,670 actual kernel calls**, all comparisons
   passed and GC live count zero. Production source was not instrumented.

POSIX native tests substitute only the language repository's existing owned
fixture platform block in generated **test artifacts**. The production C Windows
x64 guard is verified then retained in production artifacts, not weakened.

## Cost probe and limits

`run_markdown_dense_cost.py` uses the exact existing 1,000,000-byte unclosed-fence
fixture (SHA256 `2d9f79ee715b217c00792cf18a67485cdec96a14ea2ac86689156941a022c719`)
and one binary, source, compiler and manifest for both routes. Four ABBAABBA
ordered paired dense/ordinary wall-time ratios were **0.610, 0.693, 0.653, 0.675**
on the pinned compiler snapshot on this POSIX test host. The eight wall times
(seconds, in that order) were **2.743249, 1.672309, 1.809308, 2.612386,
2.619006, 1.708911, 1.866820, 2.765988**. The probe writes a fresh JSON receipt
with all raw observations and generated-source/binary hashes on each invocation.

These are **policy-consumer-only** costs, not bare-kernel timing and not editor
end-to-end timing. They include the UTF8 adapter/copy/NUL, borrow/owner boundary,
ordinary state/results and closing costs. For this fixture, 977 feeds cause 976
adaptations totaling 998,976 text bytes plus 976 NUL bytes. Those are logical
input-copy bytes, **not measured allocator bytes or GC attribution**. Four pairs
support neither a meaningful p95 nor a statistical-significance claim.

## Windows paired measurement remains pending

Do not run the old width A/B coordinator under changed pins: it intentionally
binds a different baseline/compiler and five-file source relation. The new `run_markdown_dense_ab.py` release-only coordinator (not yet Windows
executed) independently binds the same-job pair to:

- identical new notepad source and new compiler commit/tree, both activation
  receipts, generated C/GUI TU and complete build/source receipts;
- exact same fixture and identical dependency DLLs, with an explicit receipted
  same-job native handoff if linker output paths otherwise change DLL bytes;
- fresh directly owned processes in A B B A A B B A order, complete open/insert/
  backspace/five-revision/one-or-two-command Undo checks and original cleanup;
- original 30-second operation failures kept sticky and original 120-second
  owned-process lifetime. Diagnostic completion is never product-gate success;
- no next process after incomplete operation, uncertain retained-process/log or
  drop cleanup. Preserve partial evidence, never synthesize a missing sample.

Only after that real Windows run can editor latency or Undo improvements be
reported. No such Windows measurement is claimed by this local evidence.

The compiler pin is `d78a29d51844acf23ee0a49129d0211c006ac737`, tree
`a853464d36d70dc358537e76dee7711ec6dbfecf`. The language source-bridge experimental CI passed on real Windows and Linux;
that is not this editor experiment being executed. The coordinator requires these explicit
values, the exact notepad commit and GitHub run/attempt identity; no branch pin.

The measurement fixture is the exact existing 1 MB unclosed-fence fixture; both
arms include initial load plus insert, backspace and actual one/two-command Undo.
There are eight fresh owned processes, A B B A A B B A, maximum 8 × 120 seconds
for app lifetime (build/control time separate). A late stage is diagnostically
observed only within its original process budget, with the 30-second product
failure sticky. Raw late observations remain available, but a complete paired
speed ratio requires **both arms pass**, not merely finish. Censored/failed arms
never produce a complete paired speed ratio. Original single-line and unclosed-
fence GUI regressions must run separately under their unchanged strict gates;
this coordinator itself measures only the fenced fixture and does not claim
single-line coverage or benefit. Release-only measurement does not run the old
compiler-pinned profile instrumenter, and is not a full product acceptance run.

The new workflow `markdown-dense-ab.yml` first requires Linux correctness, then
real Windows ordinary/native oracles and existing owned-runner controls. It uses
`run_markdown_dense_ci.ps1` with the new explicit pin and arm; the old edit/width
workflows and their pins stay unchanged. Only bounded numeric/hash public JSON
is uploaded. Unconfirmed cleanup retains private files; no next process starts.
Separate checkout debug filenames are normalized **only for C relation checking**
at exact `ru_source = ...;` assignments; emitted production code is never changed.
All other C lines must differ only at the single enabled fact.
