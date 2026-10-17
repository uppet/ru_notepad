# ru_notepad

A small Windows text editor written mostly in **Ru**. Open a file, edit it in a native Scintilla control, and keep several documents in tabs. Ru handles the menus, document state, encoding choices, save policy, and search commands.

**Status: 0.1.7 preview candidate for Windows x64.** This candidate evaluates a small Ru-only common-token fast path while preserving the existing scanner, structural policy, guarded direct-style route and file-safety behavior. Its own complete Windows acceptance and same-route comparison are pending. The [0.1.6 product run](https://github.com/uppet/ru_notepad/actions/runs/38984124830) passed 1,487 native assertions / 33 results. Its [same-run direct-versus-message experiment](https://github.com/uppet/ru_notepad/actions/runs/38984124849) observed 1 MB GUI styling at 10.248–11.456 seconds with direct publication versus 15.126–15.128 seconds through messages, with two samples per route. Those limited observations do not predict this candidate's performance or establish Notepad++ parity. See the [Ru policy experiment](docs/ru-policy-fastpath-experiment.md) and [direct-publication contract](docs/direct-style-publication.md). Use samples or copies while testing; full Notepad++ parity remains a longer-term goal.

## What is included

- A standalone Windows x64 app with Scintilla, Lexilla and the application-owned RuSyntax DLL; Python is not needed to run them
- Tabs, undo/redo, and prompts before closing unsaved documents
- UTF-8, UTF-8 BOM, UTF-16 LE/BE, explicit Windows-1252, and GBK
- Save-conflict checks and lossless-encoding checks
- Literal search/replace, case matching, and replace-all as one undo operation
- Ru lexical tables and structural-folding policy, with a bounded application-owned C scanner for the UTF-8 hot path and incremental background styling
- C/C++ and JSON syntax highlighting from native Lexilla; automatic extension detection and a Language menu
- Current-line EOL and Enter insertion mode shown separately, including mixed-EOL files
- Tab-expanded Unicode columns, reverse tab switching, and zoom reset
- Unicode multi-file command-line and filesystem drag/drop opening, with duplicate-file identity checks
- Opt-in per-user Open With / Default Apps candidate registration and removal, with a Windows Settings link
- Bounded streaming open/save, with a cancellable warning before reading files over 500,000,000 bytes
- An original AI-generated icon

There is no fixed 4 MiB file limit. At most 64 documents and 64 queued paths are allowed. Scintilla retains the full document in RAM, so available memory still limits usable sizes. Files of at least 32,000,000 bytes open in labelled plain-text large-file mode with highlighting and wrap disabled; this is a performance mode, not an opening limit. Files over exactly 500,000,000 bytes require consent before body reads. Cancel is checked between bounded I/O chunks; one slow disk call or long-line layout can still block. Embedded NUL and invalid Unicode are rejected rather than silently changed. There is no crash recovery yet. Additional languages, regex parity, plugins, macros, split views, accessibility validation, and broader performance validation remain future work. `.ru` files select the Ru-owned container lexer. Folding tolerates incomplete edits conservatively and is not a full parser or syntax validator.

For Ru files, click the folding margin or use View > Collapse all Ru folds / Expand all Ru folds (Ctrl+Shift+[ / Ctrl+Shift+]). New/opened and successfully saved-as `.ru` paths select Ru automatically; Language > Ru / 如言 enables it manually. Switching tabs retains fold state; switching to plain text restores all hidden lines. The 32 MB plain-text performance mode also disables Ru folding.

## Trying the preview

Download the ordinary runtime ZIP for everyday use. Keep `ru_notepad.exe`, `Scintilla.dll`, `Lexilla.dll`, and `RuSyntax.dll` in the same folder. Read the warning and test instructions included with the package before opening important files. Editor file drops replace the native OLE text-drop target; external text drops and selection drag-to-move are currently unavailable. Automated acceptance covers real child-window drop messages, while full Explorer mouse-drag interaction remains a manual check.

The portable app does not need installation. Settings > Register Open With candidate is an explicit optional action. Windows Settings lets you choose each default file type. Unregister at the old location before moving the portable folder, then register the new copy.

A failed start should produce a visible diagnostic and, when possible, a diagnostic file. The separate, self-contained tests ZIP includes the same runtime bytes plus native test programs, scripts, and synthetic CI evidence. The ordinary runtime ZIP contains no test executables. The tests cover document policy, editor behavior, application lifecycle, syntax, status, keyboard policy, and file encoding. Their logs and exit codes matter; a package being present does not mean those tests passed.

For the current automated result, check this repository’s **Actions** page. Windows CI must build the app, run the native test executables, and verify an actual application window and orderly exit. Manual file-dialog, clipboard/IME, accessibility, and permission-sensitive checks remain separate from that smoke test.

## Building and understanding the project

Python is used only to run the Ru compiler and build/test tools. Ru application code is translated to C and compiled as a native Windows executable. A small application-owned C DLL accelerates UTF-8 token scanning and style-byte generation; Ru still owns keyword tables, structural folding and UI policy. The pure Ru scanner remains an independently executable test oracle.

- [Build requirements and pinned dependencies](docs/build-provenance.md)
- [Syntax-highlighting scope](docs/syntax-highlighting.md)
- [Status and shortcuts](docs/status-and-shortcuts.md)
- [File encoding and save behavior](docs/file_codec.md)
- [Default-app candidates, drag/drop and Unicode paths](docs/windows_file_entry.md)
- [Bounded streaming and large-file tests](docs/file_streaming_tests.md)
- [Editor core and dependency licensing](docs/editor-core-and-licensing.md)
- [Feature roadmap](docs/notepadpp-parity-roadmap.md)
- [Icon provenance](assets/README.md)

`python tools/build.py --help` lists the explicit compiler and toolchain arguments. Downloaded dependencies, local tool installations, generated C, binaries, and test output are kept out of the source repository.

## License status

The application license is **pending the project owner’s choice**. No MIT, GPL, or other application license is assigned by this repository yet. Third-party components retain their own licenses, and their required notices must accompany packaged copies.
