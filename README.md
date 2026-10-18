# ru_notepad

A small Windows text editor written mostly in **Ru**. Open a file, edit it in a native Scintilla control, and keep several documents in tabs. Ru handles the menus, document state, encoding choices, save policy, and search commands.

**Status: 0.1.8 preview candidate for Windows x64.** This candidate adds Markdown file detection, native syntax coloring and bounded Ru heading-folding. Its full Windows acceptance is pending. Markdown Enter continuation and rendered preview are not implemented. The last independently accepted product baseline is the [0.1.6 run](https://github.com/uppet/ru_notepad/actions/runs/38984124830), with 1,487 assertions / 33 results. Its limited same-machine direct-publication comparison improved the measured sample; it did not establish Notepad++ parity. The inherited 0.1.7 policy has completed its [same-route experiment](https://github.com/uppet/ru_notepad/actions/runs/38998372873), but its complete product acceptance remains separate. Use copies while testing.

## What is included

- A standalone Windows x64 app with Scintilla, Lexilla and the application-owned RuSyntax DLL; Python is not needed to run them
- Tabs, undo/redo, and prompts before closing unsaved documents
- UTF-8, UTF-8 BOM, UTF-16 LE/BE, explicit Windows-1252, and GBK
- Save-conflict checks and lossless-encoding checks
- Literal search/replace, case matching, and replace-all as one undo operation
- Ru lexical tables and structural-folding policy, with a bounded application-owned C scanner for the UTF-8 hot path and incremental background styling
- C/C++, JSON and Markdown syntax highlighting from native Lexilla; automatic extension detection and a Language menu
- Conservative Markdown heading folds, with a per-document on/off command
- Current-line EOL and Enter insertion mode shown separately, including mixed-EOL files
- Tab-expanded Unicode columns, reverse tab switching, and zoom reset
- Unicode multi-file command-line and filesystem drag/drop opening, with duplicate-file identity checks
- Opt-in per-user Open With / Default Apps candidate registration and removal, with a Windows Settings link
- Bounded streaming open/save, with a cancellable warning before reading files over 500,000,000 bytes
- An original AI-generated icon

There is no fixed 4 MiB file limit. At most 64 documents and 64 queued paths are allowed. Scintilla retains the full document in RAM, so available memory still limits usable sizes. Files of at least 32,000,000 bytes open in labelled plain-text large-file mode with highlighting and wrap disabled; this is a performance mode, not an opening limit. Files over exactly 500,000,000 bytes require consent before body reads. Cancel is checked between bounded I/O chunks; one slow disk call or long-line layout can still block. Embedded NUL and invalid Unicode are rejected rather than silently changed. There is no crash recovery yet. Additional languages, regex parity, plugins, macros, split views, accessibility validation, and broader performance validation remain future work. `.ru` files select the Ru-owned container lexer. Folding tolerates incomplete edits conservatively and is not a full parser or syntax validator.

For Ru files, click the folding margin or use View > Collapse all folds / Expand all folds (Ctrl+Shift+[ / Ctrl+Shift+]). New/opened and successfully saved-as `.ru` paths select Ru automatically; Language > Ru / 如言 enables it manually. Switching tabs retains fold state; switching to plain text restores all hidden lines. The 32 MB plain-text performance mode also disables Ru folding.

For Markdown, `.md` and `.markdown` suffixes are recognized case-insensitively. Language > Markdown selects it manually. The same fold margin and collapse/expand commands work with heading sections; View > Toggle Markdown heading folds disables or restores this feature per tab. Folding recognizes a documented conservative subset of ATX/setext headings, excluding fenced code, indented code and selected raw/container contexts. Lexilla's older coloring rules are distinct from this fold policy. See [Markdown editing scope](docs/markdown-editing.md).

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

`python tools/build.py --help` lists the explicit compiler and toolchain arguments. The two reviewed upstream source ZIPs and notices are tracked as fixed build inputs. Extracted dependencies, local tools, generated C, binaries and test output stay out of the source repository; source ZIPs are excluded from user packages.

## License status

The application license is **pending the project owner’s choice**. No MIT, GPL, or other application license is assigned by this repository yet. Third-party components retain their own licenses, and their required notices must accompany packaged copies.
