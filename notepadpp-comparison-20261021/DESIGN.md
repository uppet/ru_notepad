# Notepad++ comparison — design, not a benchmark result

Status: user-authorized independent comparison CI. The initial feasibility harness and publication guard are under final review; no native benchmark result is claimed by this design.

## Verified release and reproducibility

Pinned stable release v8.9.8.1, published 2026-09-24, latest official API release as checked 2026-10-21. See release-lock.json for official ZIP and checksum-file URLs, SHA256 and byte sizes. Download only in the authorized ephemeral Windows comparison CI job. Fail closed on size/hash mismatch; compare ZIP against both pinned hash and exact filename entry in downloaded checksums. This is digest verification, not a claim of independent signature verification. Record archive hash, executable hash/version, every loaded product DLL hash, config-file hashes, OS/build/CPU/runner image, source/build hashes, compiler pin, test-harness hash and command arguments. Never use a floating latest URL in the benchmark.

Official sources (all code links pinned to tested release):
- https://github.com/notepad-plus-plus/notepad-plus-plus/releases/tag/v8.9.8.1
- https://github.com/notepad-plus-plus/notepad-plus-plus/blob/v8.9.8.1/PowerEditor/src/MISC/PluginsManager/Notepad_plus_msgs.h
- https://github.com/notepad-plus-plus/notepad-plus-plus/blob/v8.9.8.1/PowerEditor/src/langs.model.xml
- https://github.com/notepad-plus-plus/notepad-plus-plus/blob/v8.9.8.1/PowerEditor/src/stylers.model.xml
- https://github.com/notepad-plus-plus/notepad-plus-plus/blob/v8.9.8.1/PowerEditor/src/Parameters.cpp
- https://github.com/notepad-plus-plus/notepad-plus-plus/blob/v8.9.8.1/PowerEditor/src/winmain.cpp
- https://github.com/notepad-plus-plus/notepad-plus-plus/blob/v8.9.8.1/PowerEditor/src/Notepad_plus_Window.h
- https://github.com/notepad-plus-plus/notepad-plus-plus/blob/v8.9.8.1/PowerEditor/src/ScintillaComponent/ScintillaEditView.cpp
- https://github.com/notepad-plus-plus/notepad-plus-plus/blob/v8.9.8.1/PowerEditor/src/menuCmdID.h
- https://github.com/notepad-plus-plus/notepad-plus-plus/blob/v8.9.8.1/lexilla/lexers/LexMarkdown.cxx
- https://npp-user-manual.org/docs/command-prompt/

## Critical feature mismatch

The pinned NPP LangType enum has NO L_MARKDOWN. Neither langs.model.xml nor stylers.model.xml defines Markdown. LexMarkdown.cxx exists in its source tree but this does not establish product UI support; its module registration supplies ColorizeMarkdownDoc and no fold function. Notepad_plus.cpp even uses Markdown as a UDL example. Do not invent a language ID, claim -lmarkdown succeeded, or force SCI_SETLEXER to change the stock product's behavior.

Primary arms: A=ru_notepad baseline6aa535 plain text; B=stock NPP plain text. Secondary arm: C=ru_notepad baseline6aa535 Markdown enabled. The existing independent A/B experiment already covers candidate8997645, so the comparison MVP does not duplicate it. Report A/B as text-editing baseline; B/C is an end-user responsiveness reference with unequal functionality, not equal-work engine performance. A successful pure-text oracle must be established in Ru before scheduling. A .txt twin of identical bytes is acceptable; note filename difference and verify actual lexer. UDL/plugin benchmarking requires separate configuration/authorization, not part of this design.

## Isolation and process ownership

Same windows-2022 job, sequential fresh processes; no parallel GUI timing. Separate immutable product/source directories and distinct per-run writable scratch directories. Every NPP run gets a fresh portable copy, doLocalConf.xml and disableNppAutoUpdate.xml presence flags alongside its EXE (preserve existing official bytes; create empty only if absent), and unique settingsDir. CLI: -multiInst -noPlugin -nosession -settingsDir=<unique path> -lnormal <fixture>. CLI is case-sensitive. No verified -noUpdate or -localConf switch exists; do not use these. Record the added config markers as deliberate modifications, preserve official archive hash separately.

Own Popen handle and PID from launch to reap; enumerate windows by that exact live PID, main class Notepad++, visible descendant Scintilla. Check PID ownership before every action and reject ambiguity. Never FindWindow globally and assume ownership. Never inject DLLs, use remote threads, allocate remote memory, or touch existing windows. Kill only the owned process on deadline; no name-based taskkill. Original input immutable and never saved; verify disk hash before/after.

NPP scalar APIs: NPPM_SETCURRENTLANGTYPE=2030 (lParam 0 for plain text); NPPM_GETCURRENTBUFFERID=2084; NPPM_GETBUFFERLANGTYPE=2088 (wParam buffer ID), require 0. NPPM_GETCURRENTVIEW=2112. Do NOT pass local pointers to NPPM_GETCURRENTLANGTYPE or NPPM_GETCURRENTSCINTILLA across processes. Class/pid/visibility and scalar lexer check avoid private pointer APIs. The inherited title/status readers use WM_GETTEXT with a bounded local buffer: this is the explicit system-message exception with Windows marshalling, never a WM_USER/Scintilla pointer. Actual undo menu command is 42003 via WM_COMMAND; NPPM_MENUCOMMAND=2072 also accepts scalar command ID. Retain Ru's application undo menu ID201.

## Workload and timing

Fixture exactly b'a' * 1_000_000; no newline/BOM. Hash generated bytes; no user contents involved. Open and reach verified initial state. Set caret byte8; WM_CHAR x; wait. Set caret9; WM_KEYDOWN/UP VK_BACK; wait. Undo once through app menu, observe resulting state. If still dirty and CANUNDO, wait for that revision's observable completion then Undo again. Maximum two commands matches the established Ru sequence; record naturally observed grouping and every intermediate text/dirty/history state. Never SCI_BEGINUNDOACTION, empty history, or insert undo barriers to manufacture two groups. If only one command reaches savepoint, report that difference instead of calling it two-Undo performance.

Separate timings (QPC/perf_counter_ns start BEFORE action):
1. action-dispatch return latency (bounded SendMessageTimeout; timeout is not success);
2. first observable expected text state via scalar GETLENGTH, GETCHARAT at fixed edit context and GETMODIFY, not a claim about the earlier inaccessible internal mutation time;
3. common observable convergence: correct length/context/dirty, expected lexer, caret-to-EOF/scroll action, GETENDSTYLED==length for Markdown (plain0/1 only records endstyled because no lexer-owned completion promise), fixed16 style probes, line0 no fold-header, responsive main/child WM_NULL;
4. Ru-only internal Markdown pending/phase completion, independently named.

Run fixed probes in same order in every arm. Do not SCI_COLOURISE to force artificial styling. First-observable timing precedes EOF/paint completion probes. A NPP synchronous handler can delay text observation until styling already happened; explicitly report that measurement limitation. Poll interval target5ms, record actual interpoll min/p50/p95/max and observer cost, timer resolution and clock implementation. Do not claim microsecond accuracy from clock precision alone. Fast timings below observation granularity are upper bounds/interval-censored; report raw samples, not misleading many-decimal ratios. Avoid foreground global SendInput; targeted window messages operate only on owned GUI in CI. If focus is needed use owned window only and log failure, never user desktop fallback.

NPP lacks Ru pending status. Endstyled/fold/style/WM_NULL are observable predicates, NOT proof of equal internal completion or all folding done. The singleline fixture contains no headings: fold check is a negative sanity check, not a fold performance workload. GUI frame response is not display-photon latency; do not label WM_NULL responsiveness as rendered-frame completion. A future paint acknowledgement needs its own explicit oracle.

30s stage gate unchanged; 120s per-process wall bound. Timeouts remain censored results with current predicates and executed-command count, never fabricated completion duration. Do not divide prior-machine baseline30s by a new-machine NPP number. Capture all arms on same job for ratios.

## Order and output

Initial feasibility one fresh A/B plus C run; then balanced ABBA/BAAB or predeclared three-arm rotation, equal replicate count. Keep exploratory runs out of final medians. Document OS file-cache warmth; do not call fresh process cold disk. Existing A/B branch permits only five added files, so this harness belongs on a new independently approved comparison branch/workflow, not the candidate899 branch.

Export numeric observations, enum IDs, fixed hashes, versions and provenance only; no document contents, screenshots, config secrets or raw process dumps. Use fixed field allowlist before upload. Local path strings should be normalized or hashed. Include missing-capability flags, stage deadlines, action counts, response/timeouts, clean-savepoint outcome, and per-arm completion definition. Comparison conclusion must keep algorithmic/functionality mismatch visible.

## Before implementing/executing

Pure tests: digest failure, archive traversal rejection, unique-run directory refusal on preexistence, PID/HWND mismatch, ambiguous Scintilla, process exit, SendMessageTimeout, one/two-Undo grouping, early-clean stop, 30s censored state, source/compiler receipt mismatch, metadata allowlist, unsupported Markdown refusal. Windows feasibility must confirm actual observed lexer and natural undo grouping; a Linux mock is not a GUI benchmark result.

Official marker semantics are verified at commit dd40fe45598791e9aa38f3aeb200e10fb3d6338a, PowerEditor/src/Parameters.cpp: both flags use doesFileExist, not XML parsing. The locked official ZIP contains doLocalConf.xml (308 bytes, SHA256 3ae00a975f3b7e6f0507e679e33b69f6c665908aab83deb2bdfd7250a404602f) and disableNppAutoUpdate.xml (219 bytes, SHA256 bcca2933d5759768aef2c3721895b5a7269da31a2940247f12f40a2ac3e538ff). These originals remain byte-identical and are included in the closed runtime seal.
