# Implementation status — 2026-10-22

**77 Linux pure/mock/real-source-loading tests pass. Native Windows results are still required.** The retained local template has its historical gate; the reviewed publication candidate is windows-feasibility.yml, triggered only by pushes to notepadpp-comparison.

## Files

- `acquire_npp.py`: opt-in fixed official ZIP/checksum/size/hash verification; bounded safe extraction, rejects traversal/symlink/reparse/encrypted/duplicate members and reused destinations; isolated portable markers; full package hash receipt.
- `build_baseline.py`: independent push/branch guard for notepadpp-comparison only; baseline6aa535/compiler85/tree fixed; exact production dependency and executable commands; validates all source/build-input/generated C/TU/main/native-helper receipts. Six build tools have hash/version and dependency command provenance. Only the six explicitly selected tools (gcc/g++/mingw32-make/windres/ar/ranlib) permit regular hardlink aliases; symlink/reparse/non-regular tools are rejected. Private receipts bind each actual path, SHA256 and version output hash, rechecked after build and before/after each GUI run. Other source/runtime/config/receipt files remain single-link.
- `seal_receipt.py`: revalidates source/compiler/full build receipt, actual tools+versions, official dependency archives, runtime, and full NPP package inventory; binds combined receipt.
- `feasibility.py`: only A=Ru baseline plain text, B=stock NPP plain text, C=Ru baseline Markdown. Exact1M synthetic bytes; fresh per-arm runtime copy. Re-seals provenance before/after every run; closed inventories before/after launch; owns retained Popen and HWND/PID; no global input/injection.
- `public_result.py`: fail-closed fixed-field numeric/hash projection. Includes Windows build, CPU count/identity hash, runner-image hash, NPP version, tool and runtime hashes; no raw context bytes/private paths.
- `windows-feasibility.yml.template`: pinned actions, fixed source/compiler checkouts, independent branch guard, sequential build/acquire/seal/ABC steps. Review gate remains; artifact upload still requires separate review.
- `test_*.py`:77 tests, including source/runtime/generated-code/native-key/compiler tampering, safe extraction, natural1/2Undo, stage/process budgets, async exit/no post-deadline grace, extraDLL/copy mutation, uncertain dispatch evidence and stop-next-arm.

## Timing and completion

30s stage /120s entire owned-process bound. Cleanup spends only the remaining hard budget; uncertain exit stops later arms. Timing is first **observable upper bound**, not internal text-mutation timestamp. Undo attempted commands are recorded before send, acknowledgements afterward; timeout keeps delivery/completion unknown. `savepoint_text_upper_ms` separately identifies final clean restoration, while first-text/common may describe the first natural Undo round.

Plain .txt uses observed lexer0/1 and does not demand full endstyled; unattached/container lexers do not promise lexer-owned styling completion. Markdown requires98/full endstyled plus Ru's internal status-complete. NPP has no equivalent internal Markdown completion oracle; stock NPP has no selectable built-in Markdown language here. WM_NULL proves response, not rendered-frame completion. Title/status WM_GETTEXT is the explicit system-message marshalling exception; no local pointers to private Scintilla/WM_USER messages.

## Still required

Independent final review of connected workflow and receipt logic; actual native Windows feasibility proving observed lexer/config/Undo grouping. The feasibility build does not replace the original full native acceptance suite. Multi-sample balanced ordering and statistical claims remain a later phase, after this MVP works. Do not infer performance from the passing mock suite.

Run local controls: `python -m unittest discover -q` in this directory. Fixed baseline source is mandatory for full-receipt tests (local recovery checkout or CI sibling `baseline`). Integration CLI is documented directly in the workflow template. All output parent directories must already exist, all target directories must be new. Never upload private receipts/logs/runtime directories.

CLI exception paths now emit fixed numeric failure codes only; a subprocess negative test confirms no private path/traceback leakage. Argparse usage errors are not a benchmark evidence path. No native toolchain compatibility claim: the six-tool hardlink compatibility policy is exercised with synthetic aliases but still requires actual Windows verification. Alias writes changing executable bytes, even with unchanged mocked version output, are rejected; identical bytes at a different selected tool directory are rejected against the recorded path.

## Publication boundary

Only the fixed closed-schema comparison-results/result.json may be uploaded, after validate_public.py revalidation. A failed/censored run can publish its validated numeric partial evidence; build failures have no result artifact. No private receipt, runtime, build log, source content, or executable is uploaded by the comparison workflow.

Acquisition diagnostics use only closed numeric stage/reason enums and bounded HTTP status, never exception text or network bodies. Exact acquisition precedes the expensive baseline build, preserving all lock/hash/redirect/extraction controls. First Windows build succeeded; acquisition failed before GUI execution, so no timing conclusion exists yet.

The official package contains nonempty presence-flag markers (308/219 bytes). Extraction preserves those verified original bytes; missing flags alone are created empty. Closed inventory and pre/post hash verification still reject modified, removed, extra, nonregular, or reparse files.

Real Windows preparation smoke precedes MinGW/build: verifies canonical paths, fixed clean source/compiler and NPP inventory, imports the fixed baseline protocol, and binds actual ctypes/user32 signatures without starting a GUI or sending input. Entry failure diagnostics are finite numeric stage/error/source IDs and line numbers; no exception text or traceback source is printed. The previous full seal succeeded but the feasibility entry failed before producing a result; this is not a performance observation.
