# Seven-language integration validation, 2026-10-20

## Current candidate and acceptance boundary

The seven-language interface has been integrated locally onto the current C++
folding application: public commit `cc6e07c0ddb1eb2dd67513819ecd9e77511a4d6f`,
tree `08e3b3253d11dd91c3549cd2c7f17e028ef7dc2d`. The compiler remains public Ru
0.22.1 commit `85c7821fda35aa79deeaf67b4d430f24ddd7f07f`, tree
`a770e367e84d87a0d2fcb6d49ea6f06da2dbe4ba`. Both public identities were checked
read-only. The compiler is a clean, exact checkout and its 200,000-step native
analysis budget is unchanged.

The inherited C++ margin header-bit runtime error is repaired with the complete
nine-file candidate `225795d8723ea310336534f3fe7aaf5cb5f4f9b6` (tree
`84c8f19a4bd6254b9bc400173b27dc2b3e73be95`), including the shared numeric
predicate and 26 additional policy controls. The subsequent Windows run passed
the production/app-features cases but exposed a separate test-fixture allocation:
one 32 MiB UTF-8 buffer exceeded the unchanged Ru 16 MiB buffer cap. Reviewed
candidate `c00d233a0cc586e3702bc781130335610728b03d` replaces that one allocation
with 32 real 1 MiB appends inside one Scintilla undo transaction. That Windows
run reached the actual 33,554,454-byte length but exposed a separate invalid
fixture premise: its folded trailing blank line was automatically expanded by
native SHOW on append. Dedicated Windows measurement 39365371547 confirmed that
mechanism, with document options unchanged at 256. A visible code line at EOF
preserves the collapsed function through real growth instead.

Reviewed candidate `521d0982225c575b82f78513ceee6f50785ad9fb` therefore uses a
34-byte visible-EOF fixture and verifies 33,554,466 actual bytes after growth,
while retaining the original 22-byte hidden-EOF automatic-expansion regression.
Five assertions cover that original behavior and undo, and one checks the new
precondition. All threshold, reachability and single-undo checks remain; the
inherited requirement is now 2,077 / 39. Production sources were not changed by
either fixture repair. The supplementary POSIX memory controls use explicitly
identified test adapters; they do not prove Windows ABI or Scintilla behavior.
The diagnostic measurements do not replace a complete Windows run of this
integrated seven-language source. That acceptance is still pending, and no
earlier failed run is relabeled.

This candidate is not yet Windows accepted or released. The older October 19
local integration used compiler 0.21.8 and a different application tree; its
static/PE results and 3,607 / 41 native expectation do not validate this tree.

This integration also packages the application MIT License and an independent
Ru runtime MIT notice. The runtime notice is copied exactly from declaration
commit `52526172d31ba902241c69dc8020996e6038f24a`; the compiler remains pinned to
`85c7821fda35aa79deeaf67b4d430f24ddd7f07f`. Complete repository-tree comparison
verified that this declaration changes only license/notice/README files, not
compiler or runtime code. See `THIRD_PARTY_NOTICES.md` for the distinct scope and
unchanged third-party exclusions.

The required current native inventory is **3,852 assertions / 42 results**:
all 2,077 / 39 current C++ and Markdown gates, plus `i18n_policy` (289),
`i18n_settings_native` (69), and `app_i18n_native` (1,417). Counts are requirements,
not observed Windows passes. The unchanged strict Markdown GUI deadline and
manual-preview eligibility remain independent gates. A deadline failure cannot
be relabeled as acceptance merely because the localization tests pass.

## Local evidence and the header-bit repair boundary

- Catalogs have 263 stable keys in exactly seven languages, or 1,841 entries.
  All exact values and 289 language/fallback/format/layout policy assertions
  passed in both the actual Ru interpreter and generated host C.
- All 19 catalog contract/negative controls and 25 menu/palette equivalence
  controls passed. Every original command ID and all 47 lexer style/color pairs
  are pinned with mutation, removal, reordering and type controls.
- Live syntax warnings rerender without resetting scanner state: 32 Ru and
  24 Markdown localized outputs passed in both ordinary Ru backends.
- The current Windows orchestration suite ran 189 controls: 184 passed and five
  platform-specific controls were skipped on Linux. Packaging ran 45 passing
  controls. Manual-preview safety ran 25 controls: 24 passed and one Windows-only
  control was skipped. These synthetic host tests do not execute the application
  on Windows.
- After the header-bit repair, before the bounded growth-fixture update, all 56
  Ru source/test entries passed
  native-C static checking with the exact compiler and unchanged budget. The
  native argument audit and all 20 malformed-expression/FFI negative controls
  passed again on the repaired source snapshot.
- The strict compiler-diagnostics controls (21), bounded localization runner
  controls (21), current Markdown policies (252 per backend), existing portable
  policy/cleanup/diagnostic/event suites and prefix replay gates passed. The
  scanner differential fixture passed all 314 assertions in each backend.
- Leak-enabled scanner and Markdown helper sanitizer runs are blocked in this
  execution environment: LeakSanitizer exits fatally because it cannot run under
  ptrace. These failures remain failures; leak detection was not disabled. The
  unsanitized helper host/cross-build controls passed, but they do not replace
  sanitizer acceptance.
- The pre-header-bit-fix localization snapshot completed all 35 PE objects / 31
  EXEs, including exact source, generated C, resource, import and embedded
  common-controls manifest checks. Those receipts are retained only as historical
  pre-fix evidence. The shared source snapshot changed with the repair, so all
  EXE receipts must be rebuilt; none is relabeled as a post-fix pass. Post-header-bit
  static, backend and host controls passed. Adding the MIT package inputs
  also changes the native helper build-driver key, so final PE builds must use
  that new key rather than relabeling either earlier batch's receipts. The
  complete MIT-driver batch subsequently passed all 35 PE / 31 EXE checks, but
  still used the oversized growth fixture. That batch is also historical: the
  bounded fixture changed the common source snapshot. Its fresh batch also
  passed all 35 PE / 31 EXE checks, but the subsequent visible-EOF fixture update
  changes the snapshot again. Every final EXE receipt must be freshly rebuilt
  and all current static checks source-verified again; neither prior batch is
  relabeled as a new-source pass.

## Preservation and evidence rules

The current C++ fold properties, fold commands, header-deletion and real large
file boundary tests remain. Markdown policy, native bulk helper, bounded direct
publication, full ownership guards, natural-paint invalidation and numeric MDP2
phase diagnostics remain. Localized status prose is distinct from fixed numeric
CI markers; failure/pending recognition covers all seven languages.

Build receipts include the complete source/test Ru snapshot, locale source
catalogs, their generator and all current native helper/resource inputs. Native
console and GUI entries use the same reviewed common-controls v6 manifest.
Portable compiler diagnostics must exactly match the pinned compiler's
source-derived style issues, command and source hashes. Nonzero exits, unexpected
warnings and any runtime stderr fail closed. Raw source-path-bearing diagnostic
streams are retained privately; public artifacts contain only validated synthetic
outputs and bounded receipts.

The optional C++ growth measurement remains manual-only, in a separate
concurrency group, with no runtime/test/preview ZIP or acceptance substitution.
Its upload is a literal `measurements.json` whitelist: complete fixed numeric
measurements are validated before atomic publication. Raw build/native streams,
complete compiler-command receipts and temporary output are not uploaded. The
standalone diagnostic entry is checked separately from the 31 product EXEs and
the 42 required result groups.

The original seven-language implementation is still independently identifiable:
local integration commit `2175d31750b01188919e2d4d961557f990335a78`, tree
`d59d02802598be0a58330a4421e65c3c75f649eb`. This provenance does not substitute for
new integrated tests.

## Remaining actual Windows and manual validation

Run all three new fixtures and every retained gate using the exact same fresh
binary/source snapshot. Required native coverage includes all seven menu/label/
cue/status languages, actual UTF-16 filters, measured layout at 640/900/1600,
synthetic isolated-registry roundtrips and malformed values, unchanged document
state/undo, and real Unicode filenames through open and Save As. Preference
fixtures never modify production Preferences; application language switches in
fixtures are session-only.

Real CJK IME composition/candidate windows, fonts/glyph fallback, 100/150/200%
DPI, translated dialogs, keyboard mnemonics and screen-reader presentation still
need manual Windows checks. OS-owned common-dialog chrome follows the Windows
language; pre-runtime bootstrap diagnostics retain English. App-owned titles,
filters and ordinary explanations are localized, with real API names and error
codes retained. See [interface-language documentation](internationalization.md)
for exact scope and the manual checklist. No Traditional Chinese eighth-language
or IME acceptance is claimed.
