# ru_notepad

A small Windows text editor written mostly in **Ru**. Open a file, edit it in a native Scintilla control, and keep several documents in tabs. Ru handles the menus, document state, encoding choices, save policy, and search commands.

**Status: 0.1.3 preview development for Windows x64.** The released 0.1.2 build passed [553 native Windows assertions and the GUI smoke test](https://github.com/uppet/ru_notepad/actions/runs/38871195015). New 0.1.3 features require their own exact-build CI receipt; compiling an EXE is not proof that the application works. Use sample files or copies of your documents while testing. Notepad++ feature parity is a longer-term goal, not a claim about this preview.

## What is included

- A standalone Windows x64 app with Scintilla and Lexilla DLLs; Python is not needed to run them
- Tabs, undo/redo, and prompts before closing unsaved documents
- UTF-8, UTF-8 BOM, UTF-16 LE/BE, explicit Windows-1252, and GBK
- Save-conflict checks and lossless-encoding checks
- Literal search/replace, case matching, and replace-all as one undo operation
- C/C++ and JSON syntax highlighting from native Lexilla; automatic extension detection and a Language menu
- Current-line EOL and Enter insertion mode shown separately, including mixed-EOL files
- Tab-expanded Unicode columns, reverse tab switching, and zoom reset
- Unicode multi-file command-line and filesystem drag/drop opening, with duplicate-file identity checks
- Opt-in per-user Open With / Default Apps candidate registration and removal, with a Windows Settings link
- Bounded streaming open/save, with a cancellable warning before reading files over 500,000,000 bytes
- An original AI-generated icon

There is no fixed 4 MiB file limit. At most 64 documents and 64 queued paths are allowed. Scintilla retains the full document in RAM, so available memory still limits usable sizes. Files of at least 32,000,000 bytes open in labelled plain-text large-file mode with highlighting and wrap disabled; this is a performance mode, not an opening limit. Files over exactly 500,000,000 bytes require consent before body reads. Cancel is checked between bounded I/O chunks; one slow disk call or long-line layout can still block. Embedded NUL and invalid Unicode are rejected rather than silently changed. There is no crash recovery yet. Ru-specific highlighting, additional languages, regex parity, plugins, macros, split views, accessibility validation, and broader performance validation remain future work. `.ru` files stay plain text; no substitute lexer is presented as Ru support.

## Trying the preview

Download the ordinary runtime ZIP for everyday use. Keep `ru_notepad.exe`, `Scintilla.dll`, and `Lexilla.dll` in the same folder. Read the warning and test instructions included with the package before opening important files. Editor file drops replace the native OLE text-drop target; external text drops and selection drag-to-move are currently unavailable. Automated acceptance covers real child-window drop messages, while full Explorer mouse-drag interaction remains a manual check.

The portable app does not need installation. Settings > Register Open With candidate is an explicit optional action. Windows Settings lets you choose each default file type. Unregister at the old location before moving the portable folder, then register the new copy.

A failed start should produce a visible diagnostic and, when possible, a diagnostic file. The separate, self-contained tests ZIP includes the same runtime bytes plus native test programs, scripts, and synthetic CI evidence. The ordinary runtime ZIP contains no test executables. The tests cover document policy, editor behavior, application lifecycle, syntax, status, keyboard policy, and file encoding. Their logs and exit codes matter; a package being present does not mean those tests passed.

For the current automated result, check this repository’s **Actions** page. Windows CI must build the app, run the native test executables, and verify an actual application window and orderly exit. Manual file-dialog, clipboard/IME, accessibility, and permission-sensitive checks remain separate from that smoke test.

## Building and understanding the project

Python is used only to run the Ru compiler and build/test tools. Application code is translated to C and compiled as a native Windows executable.

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
