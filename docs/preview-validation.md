# 0.1.1 preview validation

Date: 2026-10-16 UTC. This is an unsigned Windows x64 preview; this document separates source/host checks from native package evidence.

## Evidence completed

- Real MinGW Windows x64 PE compilation, embedded icon/manifest, bundled source-built Scintilla 5.6.7, and system-only static import inspection.
- Native launcher portable policy/source tests pass and four Win32 fixtures cross-build with real MinGW headers; actual Windows CRT/file/dialog behavior is explicitly unrun.
- Full Ru native-C static checks for the application and native test sources.
- Actual shared `src/ui_arguments.ru` GUI argument helpers: 19/19 in the interpreter and 19/19 in Linux native C. The original malformed expression fails with the expected arity error in both. All 104 native calls resolve with zero mismatches after the fix; see `startup-fix-0.1.1.md`.
- Actual shared `src/document.ru` policy tests: 23/23 in the Ru interpreter and 23/23 in Linux native C. These cover save-state commit-after-success, save failures, close confirmation/cancellation and encoding-dirty policy.
- Independent source review of NUL/byte-count/UTF-8 guards, Scintilla status handling, grouped-undo cleanup, child-window rollback, canonical paths, file-dialog buffer ownership, orderly-shutdown veto, fatal-warning behavior and staged-save ownership.
- Official Debian package-index signatures/package hashes and pinned Scintilla archive hash; ZIP CRC, SHA-256 inventory and binary import checks are packaging gates.

## Native package evidence

A later Windows CI package is created only after its required native suites and real visible-window/normal-close smoke test pass. Consult that exact package’s BUILD.json for platform, counts and hashes. This document retains the Linux-source-review evidence and does not replace the artifact’s runtime receipt.

## Not established

The 0.1.0 startup failure was reproduced on Windows; the precise cause and repair are documented separately. No successful application or native integration acceptance run is established. The repaired 0.1.1 GUI and launcher have not run here on Windows or Wine. The environment could not launch the required Wine server/display. Building a PE is not a runtime pass, and source review cannot establish effective NTFS permissions.

Included native executables exercise document policy, the actual Scintilla wrapper, the application lifecycle and the Win32 file codec. An optional synthetic-fixture ACL probe/script covers protected and inherited permissions; it is deliberately separate from the normal test runner.

Actual Windows acceptance must include UTF-8/UTF-16/legacy byte round trips, file dialogs, dirty prompts, failure retention, clipboard/IME, shutdown veto, missing DLL diagnostics, replacement/backup behavior, ACLs/EFS, fault injection and accessibility. No crash recovery exists. Test samples and copies first.

## Milestone status

M0 integration and M1 editing basics are implemented in source but not accepted on Windows. Save All, recent files, backward/whole-word/selection-scope search, explicit EOL conversion, tab reordering and localization are still absent even within the broader M1 roadmap. M2–M5 are future work. Notepad++ parity is not claimed.

The package BUILD.json records exact source and toolchain identities. Test reports must preserve failures and skips separately from passes; update this status only with actual execution evidence.
