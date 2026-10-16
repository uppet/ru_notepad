# ru_notepad

A small Windows text editor written mostly in **Ru**. Open a file, edit it in a native Scintilla control, and keep several documents in tabs. Ru handles the menus, document state, encoding choices, save policy, and search commands.

**Status: 0.1.2 preview development for Windows x64.** The previous 0.1.1 build passed [277 native Windows assertions and the GUI smoke test](https://github.com/uppet/ru_notepad/actions/runs/38863597991). New 0.1.2 features require their own exact-build CI receipt; compiling an EXE is not proof that the application works. Use sample files or copies of your documents while testing. Notepad++ feature parity is a longer-term goal, not a claim about this preview.

## What is included

- A standalone Windows x64 app with Scintilla and Lexilla DLLs; Python is not needed to run them
- Tabs, undo/redo, and prompts before closing unsaved documents
- UTF-8, UTF-8 BOM, UTF-16 LE/BE, explicit Windows-1252, and GBK
- Save-conflict checks and lossless-encoding checks
- Literal search/replace, case matching, and replace-all as one undo operation
- C/C++ and JSON syntax highlighting from native Lexilla; automatic extension detection and a Language menu
- Current-line EOL and Enter insertion mode shown separately, including mixed-EOL files
- Tab-expanded Unicode columns, reverse tab switching, and zoom reset
- An original AI-generated icon

The current limits are 4 MiB files/UTF-8 loads and 64 open documents. Embedded NUL and invalid Unicode are rejected rather than silently changed. There is no crash recovery yet. Ru-specific highlighting, additional languages, regex parity, plugins, macros, split views, accessibility validation, and large-file performance remain future work. `.ru` files stay plain text; no substitute lexer is presented as Ru support.

## Trying the preview

Download the ordinary runtime ZIP for everyday use. Keep `ru_notepad.exe`, `Scintilla.dll`, and `Lexilla.dll` in the same folder. Read the warning and test instructions included with the package before opening important files. The portable app does not need installation or file-association changes.

A failed start should produce a visible diagnostic and, when possible, a diagnostic file. The separate, self-contained tests ZIP includes the same runtime bytes plus native test programs, scripts, and synthetic CI evidence. The ordinary runtime ZIP contains no test executables. The tests cover document policy, editor behavior, application lifecycle, syntax, status, keyboard policy, and file encoding. Their logs and exit codes matter; a package being present does not mean those tests passed.

For the current automated result, check this repository’s **Actions** page. Windows CI must build the app, run the native test executables, and verify an actual application window and orderly exit. Manual file-dialog, clipboard/IME, accessibility, and permission-sensitive checks remain separate from that smoke test.

## Building and understanding the project

Python is used only to run the Ru compiler and build/test tools. Application code is translated to C and compiled as a native Windows executable.

- [Build requirements and pinned dependencies](docs/build-provenance.md)
- [Syntax-highlighting scope](docs/syntax-highlighting.md)
- [Status and shortcuts](docs/status-and-shortcuts.md)
- [File encoding and save behavior](docs/file_codec.md)
- [Editor core and dependency licensing](docs/editor-core-and-licensing.md)
- [Feature roadmap](docs/notepadpp-parity-roadmap.md)
- [Icon provenance](assets/README.md)

`python tools/build.py --help` lists the explicit compiler and toolchain arguments. Downloaded dependencies, local tool installations, generated C, binaries, and test output are kept out of the source repository.

## License status

The application license is **pending the project owner’s choice**. No MIT, GPL, or other application license is assigned by this repository yet. Third-party components retain their own licenses, and their required notices must accompany packaged copies.
