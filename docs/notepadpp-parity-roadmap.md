# ru_notepad: Notepad++ parity roadmap

Research date: 2026-10-16. Target: a local Windows editor with mostly Ru application source and its own visual identity.

## Scope and status

Full functional parity is a long-term, testable program, not a claim about the first executable. This document records proposed requirements and acceptance gates. It does not certify the current implementation, Windows runtime behavior, or performance. All rows start as **planned / not independently validated**; the implementation owner should record passing tests separately.

“Parity” needs a pinned Notepad++ release, architecture, configuration, and plugin set. The official manual is a moving reference and can describe newer behavior. Capture the chosen release and test fixtures before declaring any feature equivalent. Do not count third-party plugins as built-in features.

## Recommended milestones

| Gate | Outcome | Required evidence before advancing |
| --- | --- | --- |
| M0: integration proof | Ru shell can host the selected editor component on Windows x64 | Clean build; dependency inventory; startup/resize/focus/typing/close on actual Windows; missing-DLL failure is understandable |
| M1: trustworthy daily basics | Multiple documents can be edited and saved without silent data loss | Byte-level file tests, dirty-state/undo tests, canceled dialogs, failed saves, clipboard/IME smoke tests |
| M2: programmer workflow | Code navigation, syntax, folding, completion and configurable search | Golden language fixtures, search corpus, keyboard tests, responsive cancellation |
| M3: recoverable workspace | Sessions, split views, macros, shortcut configuration and broad encodings | Crash/restart recovery tests, shared-buffer tests, deterministic macro replay, invalid-config tests |
| M4: scale and product quality | Large files, accessibility, printing, localization and polish | Reproducible Windows benchmarks; accessibility/print/localization test reports; explicit limits |
| M5: compatibility assessment | Measured closure of remaining built-in differences; separately scoped plugin strategy | Differential test results against the pinned baseline; documented intentional differences; per-plugin compatibility results only |

M1 must not wait for a plugin system or every language lexer. Accessibility, keyboard access and high-DPI checks begin in M0/M1 and deepen in M4.

## Feature matrix

Ownership shorthand: **Ru** means application policy, state and UI implemented in Ru; **core** means an editor-component primitive, still needing integration tests; **native** means a narrow platform/FFI adapter. The ownership column is a recommended design, not a claim of completed code.

| Area / target behavior | Gate | Recommended ownership and dependencies | Acceptance criteria |
| --- | --- | --- | --- |
| Text editing: insert/overwrite, selection, clipboard, navigation, zoom, wrap | M1 | Core + Ru command dispatch | Type Latin/Cyrillic/CJK/emoji; paste mixed text; keyboard movement does not split valid encoded characters; wrap/zoom never change file bytes |
| Undo/redo and dirty state | M1 | Core history + Ru save lifecycle | Edit/save/edit/undo/redo crosses the saved state correctly; replace-all is one undo operation; undo in one tab never affects another; failed save leaves dirty state intact |
| Open, New, Save, Save As, Save All, recent files | M1 | Ru + Windows file dialogs and safe file writer | Cancel preserves state; failed write preserves original; existing-file overwrite is explicit; read-only and externally changed files are handled; Unicode paths work |
| Tabs and multiple documents | M1; polish M3 | Ru document IDs, tab/view mapping, MRU | Reorder and switch tabs without losing undo/caret/scroll; close dirty tab offers save/discard/cancel; duplicate opens follow documented policy; close-all honors cancellation |
| Literal find/replace | M1 | Core range operations + Ru dialog/state | Forward/backward, wrap, case, whole-word, selection scope and replace-all match fixtures; empty pattern and zero-length selection are safe |
| Extended escapes and regex | M2; exact parity M5 | Ru search service + deliberately chosen regex engine | Separate literal/escaped/regex modes; test captures, replacements, multiline anchors, Unicode, invalid patterns and zero-width progress; report dialect honestly |
| Find/replace in files and open documents | M2; replace hardening M3 | Ru directory traversal, worker jobs, encoding and results model | Filters/exclusions, recursion, hidden files, cancellation, errors and result navigation tested; define treatment of unsaved open buffers; preview/count before bulk replacement; no unnoticed encoding conversion |
| Bookmarks, mark matches, occurrence navigation | M2 | Core markers/indicators + Ru commands | Multiple marks coexist; edits move markers sensibly; next/previous wrap correctly; clearing search marks preserves unrelated bookmarks |
| Rectangular selection and multi-caret editing | M2 | Core + Ru commands/preferences | Exercise unequal line lengths, tabs, virtual space, Unicode and rectangular clipboard; single undo restores all selections; column numbering is deterministic |
| Line operations | M2 | Ru transformation commands + grouped core edits | Duplicate/move/join/split, trim, case conversion, indentation and sorting preserve intended selection/EOL; one undo restores bytes |
| Encodings and BOM | UTF-8 M1; broader M3 | Ru decode/encode policy; Windows conversion or vetted library | Round-trip UTF-8 with/without BOM, UTF-16 LE/BE and selected Windows code pages; distinguish reinterpretation from conversion; reject or explicitly confirm lossy conversion; retain original bytes when decode fails |
| EOL modes | M1 | Ru metadata + core EOL commands | CRLF/LF/CR fixtures and no-final-newline survive untouched saves; mixed EOL is detected; conversion is explicit and undoable; new typed lines use selected mode |
| Syntax highlighting and themes | M2 | Lexilla or Ru lexer + Ru language/style registry | Start with Ru and a small declared set; extension/manual override work; strings/comments/numbers and incremental multiline edits match golden fixtures; theme change does not alter text |
| Folding | M2 | Lexer fold data + core + Ru commands | Nested fold/expand, fold-all and navigation into hidden text work after edits; selections/save include hidden content |
| Completion and call tips | M2 | Core popup + Ru candidate providers | Word, language and path candidates have explicit sources; accept/dismiss/typing behavior tested; no frozen UI on large buffers; hints handle multiple signatures |
| Split views and cloned document | M3 | Ru view model + shared core document | Horizontal/vertical split, move/clone, independent caret/scroll and synchronized edits; closing one clone retains buffer; no double-free or duplicate save prompt |
| Sessions and crash recovery | M3 | Ru versioned state and recovery journal | Restore tab order, active view, paths, cursor, language and bookmarks; distinguish saved session from unsaved-buffer recovery; corrupt state is recoverable; missing files are retained as explicit placeholders or reported |
| External change/reload and file monitoring | M3 | Ru watcher + conflict policy | Own saves are not false conflicts; external deletion/rename/modification is visible; reload never silently discards dirty content; stopped monitoring releases handles |
| Macros | M3 | Ru command log + core editing notifications | Record/replay/save/name/shortcut; repeat count and until-end modes terminate; record only documented actions; cancellation works; imported macros cannot silently execute shell commands |
| Shortcut mapper | M3 | Ru stable command registry | Rebinding, conflict detection, reset and persistence; menu hints match active bindings; editor/dialog accelerators do not steal IME or text input |
| Workspace/project and function panels | M3/M4 | Ru trees/indexing/parsers | Folder refresh and project persistence work; function navigation stays correct after edits; large trees cancel; missing paths and parser errors are visible |
| Large-file mode | M4 | Ru load policy and budgets + core limits | Measure 1/10/100/500 MiB fixtures, many short lines and huge single lines; test low memory, cancellation and save; >2 GiB remains an explicit separately verified goal |
| Printing | M4 | Core formatting + native print adapter + Ru settings | Actual Windows print-to-PDF checks selection/all, page ranges, margins, line numbers, colors, header/footer, long lines and cancel; printing never changes document state |
| Localization | Infrastructure M1; coverage M4 | Ru keyed string resources, separate from source language | Every visible command/dialog/error has a key; fallback works; longer translations, Unicode, mnemonic collisions and 200% DPI do not hide controls |
| Accessibility and international input | Baseline M1; deeper M4 | Core capability + native accessibility/UI + Ru labels | Keyboard-only file/search/tab workflows; visible focus, high contrast, Narrator/NVDA reading/editing, IME composition and text scaling tested on Windows; document limitations |
| Original icons, menus and high-DPI polish | M1/M4 | Ru UI + original artwork/assets | Distinct ru_notepad identity; icons remain legible at 16/20/24/32 px, dark/light/high contrast; text/tooltips expose function; no borrowed Notepad++ branding |
| Extensions / plugins | M5, separate decision | Versioned ru_notepad API; native bridge only if justified | First-party sample extension demonstrates bounded APIs; disable/recovery path exists; architecture/version mismatches are refused; existing NPP plugins are unsupported until individually demonstrated |

## Reference behavior and important traps

- Notepad++ includes stream/column selection, multi-editing, dual views and cloned documents. A clone shares the document; it is not a copied file. See the [official editing manual](https://github.com/notepad-plus-plus/npp-usermanual/blob/master/content/docs/editing.md).
- Search includes file/project scopes, marks and result panels. Its documented regex engine is Boost; its search and replacement syntaxes differ. Unsaved open buffers can take precedence over disk in find-in-files. These deserve explicit tests, not a generic “regex supported” checkbox. See the [search manual](https://github.com/notepad-plus-plus/npp-usermanual/blob/master/content/docs/searching.md).
- Encoding interpretation and conversion are different actions. “ANSI” means a system-dependent code page, not a universal encoding. See the [encoding manual](https://github.com/notepad-plus-plus/npp-usermanual/blob/master/content/docs/encoding.md).
- Manual sessions and automatic recovery do not have identical semantics; Notepad++ manual session files do not include new unnamed documents. See the [sessions manual](https://github.com/notepad-plus-plus/npp-usermanual/blob/master/content/docs/session.md).
- NPP completion candidates come from language definitions, document words and paths; syntax coloring alone does not provide completion data. See the [completion manual](https://github.com/notepad-plus-plus/npp-usermanual/blob/master/content/docs/auto-completion.md).
- NPP macro coverage is deliberately limited; recording is not a universal scripting language. See the [macro manual](https://github.com/notepad-plus-plus/npp-usermanual/blob/master/content/docs/macros.md).
- Large-file restrictions can turn off expensive features. A large address range alone does not establish useful performance. Printing and shortcut settings also have substantial application policy. See the [preferences manual](https://github.com/notepad-plus-plus/npp-usermanual/blob/master/content/docs/preferences.md).
- Localization includes menu/dialog strings and accelerators. See the [translation manual](https://github.com/notepad-plus-plus/npp-usermanual/blob/master/content/docs/binary-translation.md). A mostly-Ru implementation does not by itself specify the UI language.

Additional primary references: [tabs and UI](https://github.com/notepad-plus-plus/npp-usermanual/blob/master/content/docs/user-interface.md), [views](https://github.com/notepad-plus-plus/npp-usermanual/blob/master/content/docs/views.md), [languages](https://github.com/notepad-plus-plus/npp-usermanual/blob/master/content/docs/programing-languages.md), [function list](https://github.com/notepad-plus-plus/npp-usermanual/blob/master/content/docs/function-list.md).

## Verification policy

Record each test as **passed**, **failed**, **blocked**, or **not run**, with platform/build and evidence. Cross-compilation is not Windows runtime validation. A screenshot establishes appearance only. A smoke test is not full parity. Keep known deviations visible and avoid advertising unimplemented menu entries as working features.

For performance, record CPU, RAM, Windows version, architecture, storage, build mode, fixture bytes/line count, cold/warm load, peak working set, time-to-interactive, search duration and cancel latency. Set budgets from measured hardware, then gate regressions; do not publish invented throughput claims.
