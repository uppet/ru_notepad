# Ru batch-policy fast prefix

The 0.1.7 preview candidate evaluates one small optimization in
`src/ru_lexical.ru`. Its Windows product acceptance and same-direct-route
performance comparison are separate gates. Linux policy timings do not establish
editor responsiveness or Notepad++ parity.

## Policy contract

At batch entry, the fast prefix is eligible only when both pending headers and
the frame stack are empty. Token event kinds 1/2/3/4 keep their original policy
class mapping 1/2/5/6. Number/string events use effective token code zero;
name/punctuation events retain their supplied code. Only codes 0, 9, 100 and 117
skip `_记词`, preserving both original writes: statement boundary becomes
`code == 100`, and previous token becomes `code`. Name correction follows in its
original order. Newline events call the original `_行折` and update the same
line/depth fields.

These accepted transitions cannot create a pending header or frame. At the
first other token, comment or unknown event, prefix execution stops permanently
for that batch. The original loop consumes that event and every remaining one,
even if structural state is later cleared. Only a new batch can re-enable the
prefix. An initially nonempty context goes directly to the original loop.

The original validation, finished-state rejection, EOF handling and finalization
remain authoritative. The regular loop is byte-guarded, permitting only its
parenthesized remaining-iteration count to change. The small duplicated
shortcut/correction/newline operations are bound to the originals by source
guards and 12 negative mutations. There is no new function call, event slice,
state slot or per-token eligibility check on the fallback path. The stopping
event may receive identical byte/line metadata twice; no token, correction or
fold is replayed. Failure tests compare the complete state after errors.

A preliminary per-token eligibility design regressed the structured workload.
The conservative prefix keeps that path's original per-token work and retains
the structured workload as a required regression check.

## Reproducible semantic gate

Use Linux, Python 3, Git and GCC with these exact clean checkouts:

- Public baseline: `a5f5fd825767cd5af662cba792f5ce352991c21e` from
  [uppet/ru_notepad](https://github.com/uppet/ru_notepad), tree
  `e8a402fb3eb551bfe416b8aee0aaaf942d2d4f4a`.
- Baseline policy blob: `876a99f76db706cfd76427b9341ee5f05180ce0d`, SHA-256
  `f78589e247186890855526f7bb3624d34e4004bb8fbc69587c96d38c826a602c`.
- Current semantic-gate compiler, Ru 0.22.1: `85c7821fda35aa79deeaf67b4d430f24ddd7f07f` from
  [uppet/ru-language](https://github.com/uppet/ru-language), tree
  `a770e367e84d87a0d2fcb6d49ea6f06da2dbe4ba`.

These pins apply to the current semantic gate. Historical Windows benchmark
workflows retain their original source/compiler identities.

For example, from a candidate checkout:

```sh
git clone https://github.com/uppet/ru_notepad.git ../ru-policy-baseline
git -C ../ru-policy-baseline checkout --detach a5f5fd825767cd5af662cba792f5ce352991c21e
git clone https://github.com/uppet/ru-language.git ../ru-policy-toolchain
git -C ../ru-policy-toolchain checkout --detach 85c7821fda35aa79deeaf67b4d430f24ddd7f07f
python -I tools/test_ru_policy_fast.py \
  --baseline ../ru-policy-baseline --ru-root ../ru-policy-toolchain
python -I tools/verify_ru_policy_fast_outputs.py
```

The first command requires `build/policy-fast` to be absent. Preserve an earlier
run separately before rerunning; it never overwrites a previous proof. Compile
serially. The toolchain's 120-second C compilation limit is unchanged. No native
platform guard overrides or Wine are used.

The proof runs the actual baseline and candidate in the interpreter and four
fixed host-C shards. Each complete case remains in one shard. Every backend
must execute:

- 196 input/chunk plans: all 157 existing oracle inputs plus 13 adversarial
  inputs under three schedules; 19,627 main batch calls and 2,554 main events.
- 21,504 class/code/context transitions, plus four checkpoint/suffix-edit
  replays, including retroactive same-line fold proof/revocation.
- 13 explicit boundaries comprising 39 main calls and six expected failures:
  empty/all-fast batches, first/last prefix stops, newline/comment carry,
  pending/frame creation or clearing, EOF/repeated EOF, unknown events and bounds.
- Full nested 25-slot state and ordered style/fold outputs after each batch and
  event replay, plus complete UTF-8 styles and final folds against the pure oracle.

`tests/fixtures/ru_policy_fast_plan.json` fixes the synthetic inputs, raw scanner
styles, schedules, capacities, batch sequence digests, contexts, edits and
boundaries. Its exact byte SHA-256 is
`a712c3b5c70e5bfe4ae09900d928f594c2c88bb49448d40ca15422b09a015e90`.
The separately named canonical-content SHA-256 is
`0183679cfac0583d3a160e7ab7549967fe6b53b87b605647f2da3ce09c171616`.
CI recomputes the plan rather than trusting a saved local receipt. RLE compacts
only construction of consecutive empty, non-EOF batches on the same line. Python
requires exact expansion; Ru checks each actual call's ordered events/bytes/line/
EOF digest and totals. Every API call and state/output comparison still occurs.
Semantic comparisons themselves are exact, not digest comparisons.

The execution wrapper prints one fixed success marker. The independent verifier
checks actual generated Ru/C and executable identities, every shard's ordered
case identities, and exact reassembly of all 214 interpreter output lines.
It also runs 38 retained negative controls against staged receipts, covering
source/pin/schema/count/order changes, missing/oversized output, diagnostic
leaks, and linked/reparse paths. Their separate `validator_negative_controls`
count does not change semantic totals. Only then does `report.json` become
`status: passed`. A successful execution
wrapper alone is insufficient. Exceptions and compiler diagnostics stay in
ignored private logs; public failures contain only a fixed stage/code/hash.

The public receipt consists of exactly eight selected files under
`build/policy-fast`: `report.json` (64 KiB cap), `fixture-manifest.json` (256 KiB),
`ordered-output-validation.json` (16 KiB), `interpreter.log` and `host-c-0.log`
through `host-c-3.log` (64 KiB each). The read-only
`validate_public_evidence(directory, expected_inputs)` API verifies these files
against prepared source hashes, exact pins, input plan, counts and ordered raw
output. Other generated artifacts are local and are not public attachments.
The Windows product's 1,487 native assertions / 33 results remain independently
required; this portable proof is additional evidence.

## Policy microbenchmark

After the complete semantic gate, a fresh optional Linux measurement is:

```sh
python -I tools/benchmark_ru_policy_fast.py \
  --baseline ../ru-policy-baseline --ru-root ../ru-policy-toolchain --repeats 3
```

The benchmark requires an absent `build/policy-fast/benchmark` directory. It
records all five shapes, all repetitions and four variants: uninstrumented
baseline/candidate plus separately counted copies. Invocation source snapshots,
generated C and actual executable identities are checked before measurements
and for end-of-run drift. Every repeat verifies actual input/event totals and
counts; no outliers are discarded. Counted/off ratios are observations, not
isolated instrumentation costs, and are never subtracted from timings.

An earlier isolated Linux run of this same production policy
(SHA-256 `deb5629333f2e76125b396bfe640b327ea6f1fd42f95f24277c86c5209fb12ec`)
retained all 60 samples. These are historical observations from the measured
prototype scripts, before public baseline/receipt hardening, rather than a new
measurement of the current public scripts. Median uninstrumented event-array
construction plus policy times were:

| Input shape | Actual UTF-8 bytes | Baseline ms | Candidate ms | Change |
| --- | ---: | ---: | ---: | ---: |
| Exact GUI corpus | 1,000,000 | 1,771.480 | 1,194.448 | -32.6% |
| ASCII lines | 1,000,000 | 3,357.297 | 1,922.656 | -42.7% |
| One long ASCII line | 1,000,000 | 2,426.355 | 1,202.331 | -50.4% |
| Short Ru lines | 999,999 | 2,346.470 | 1,406.209 | -40.1% |
| Structured realistic | 999,964 | 1,592.945 | 1,506.838 | -5.4% |

All 15 uninstrumented pairs favored the candidate in that run. The realistic
shape retained 133,798 calls and zero bypasses in both variants; its last pair,
1,496.363 to 1,496.190 ms, was effectively tied. This did not reproduce the
preliminary regression, but does not establish a reliable 5.4% algorithmic gain.
Cloud timing variability and baseline drift remain visible. Batch maxima did
not improve uniformly; no worst-case latency guarantee follows.

The exact GUI corpus produced 363,631 baseline `_记词` calls; the candidate
bypassed 363,628 and retained three calls. Its corpus SHA-256 is
`ecf8dca884444a5e54e1f40dc6af01cf5e7830ed6fe902d3adf6fdf255f9b3fa`.
The flat-input result supports the function/environment-cost hypothesis. These
measurements exclude Windows native ABI decoding, Scintilla publication,
rendering, timers and GUI responsiveness. Windows evaluation must compare the
baseline and candidate in the same run with the same direct-style route; older
message-route timings are not a valid baseline.

## Current toolchain note

The measurements and compiler identifiers above are historical Ru 0.21.6 evidence. Current product build and policy-proof scripts and the product workflow pin reviewed Ru 0.22.1 as documented in [build provenance](build-provenance.md). Run the current scripts with that exact current pin; do not treat old measurements as results from the new compiler. The three manual historical replay workflows retain their original Ru 0.21.6 pin because they check out frozen historical application sources. The policy baseline and corpus identities remain unchanged.
