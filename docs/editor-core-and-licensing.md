# ru_notepad: editor core, dependencies and licensing

Research date: 2026-10-16. This is an engineering decision note, not a legal opinion or a verified dependency manifest. No binaries were downloaded, installed or executed for this research.

## Decision

Use **Scintilla** for the long-term Windows editor core and **Lexilla** for reusable language lexers. Keep the application model, commands, menus, tabs, persistence and file policy in **Ru**. A small native ABI bridge is reasonable where Ru cannot directly express a Windows callback or component function signature.

RichEdit is acceptable for a deliberately temporary bootstrap proving the Ru compiler, Win32 window lifecycle and file dialogs. It should not become an accidental substitute for the intended programmer-editor core. If used first, put it behind a narrow editor adapter and label its feature limits.

## Scintilla versus Windows RichEdit

| Question | Scintilla | RichEdit | Implication for this project |
| --- | --- | --- | --- |
| First window | Extra component build/package step | Windows Msftedit.dll and MSFTEDIT_CLASS | RichEdit can reduce initial packaging work |
| Text model | Byte-based positions, normally UTF-8 in this design | Unicode control interface; paragraph semantics need care | Do not interchange byte, UTF-16 and display-column offsets |
| Programmer primitives | Styles, folds, markers, multi-selection, shared documents, completion, call tips, undo | General editing, Unicode, multilevel undo, rich text/typography | Scintilla reduces custom editor-mechanics work |
| Application completeness | Still only an editor component | Still only an editor component | Neither supplies tabs, sessions, safe save policy or complete search workflows |
| Language highlighting | Lexilla or custom styling | Application must build highlighting behavior | RichEdit-first increases migration/reimplementation risk |
| International text | Windows RTL support is explicitly limited/experimental | Complex-script/IME/TSF capabilities documented | Test actual target languages and input methods early |
| Runtime distribution | Pin and package compatible native components | Use Windows-provided component | Inspect actual binary imports; do not assume runtime dependencies |

Primary evidence: [Scintilla API](https://www.scintilla.org/ScintillaDoc.html), [Microsoft RichEdit overview](https://learn.microsoft.com/en-us/windows/win32/controls/about-rich-edit-controls), [Scintilla 5 migration guide](https://www.scintilla.org/Scintilla5Migration.html).

The Windows Scintilla documentation describes system-caret assistance for screen readers, not a guarantee of complete UI Automation behavior. Accessibility remains a release-test obligation. Stock regex is limited or C++11/ECMAScript-based; it does not establish Boost/NPP regex equivalence. Large-document options and full-width position APIs exist, but must be used consistently. These are integration risks to test rather than promises of parity. [Scintilla API reference](https://www.scintilla.org/ScintillaDoc.html).

## Suggested boundary

Ru owns:

- Stable document IDs; path, encoding, BOM, EOL, dirty and recovery metadata.
- Tab/view layout, active document, menus/toolbars/status, dialogs and keymap.
- Safe read/write behavior, external-change policy, recent files and sessions.
- Search scope, result lists, cancellation, replace transaction policy and regex dialect selection.
- Language-to-lexer mapping, keyword sets, themes and completion data.
- Named macros, preferences, localization resources and extension policy.

The native layer should expose a small audited interface. Keep pointer widths, signed positions, structure layout, callback calling convention and string lifetimes explicit. Avoid leaking raw Windows handles throughout business logic. Treat editor text as UTF-8 bytes internally only after defining how original encodings and invalid byte sequences are preserved. Use stable document IDs, not tab indexes, as durable identity.

Maintain a single authoritative edit history. Do not rebuild editor contents on every keystroke to keep a parallel Ru string synchronized; this would risk undo, selection and performance. Take deliberate snapshots for saving/searching, and keep component access on its owning UI thread unless the specific API explicitly permits background work.

## Obtaining and pinning the components

The official download pages currently advertise **Scintilla 5.6.7** and **Lexilla 5.5.4**. They provide source archives and state that standalone DLL-only downloads are not available, pointing to full SciTE downloads instead. Record the exact versions actually used, not these moving recommendations. [Scintilla download](https://www.scintilla.org/ScintillaDownload.html), [Lexilla download](https://www.scintilla.org/LexillaDownload.html).

Prefer pinned official source packages and reproducible builds. Record upstream URL, archive hash, version, compiler, architecture, flags, patches, output hashes and runtime imports. Keep dependency source/build output distinct from Ru-owned source so “mostly Ru” describes the application honestly.

Lexilla requires Scintilla headers and documents a sibling-directory layout: scintilla/ beside lexilla/. Its documented builds support make with GCC/Clang or nmake/MSVC. It can be static or shared. The C-facing API allows an opaque lexer pointer, so Ru need not implement the C++ lexer interface merely to select a lexer. [Lexilla build/API documentation](https://www.scintilla.org/LexillaDoc.html).

With Scintilla 5, create a lexer by name through Lexilla, then attach it with SCI_SETILEXER. Keep the loaded library alive for the lifetime of its lexer objects. A static build can avoid runtime lookup but changes the build/packaging workflow; a shared build gives a simpler opaque boundary. [Migration guide](https://www.scintilla.org/Scintilla5Migration.html).

Do not follow old SciLexer.dll tutorials blindly. The official [Windows starter page](https://www.scintilla.org/Steps.html) and some [SciTE download text](https://www.scintilla.org/SciTEDownload.html) still contain older naming, while current component pages describe Scintilla.DLL and Lexilla.DLL. Inspect the selected archive and exports. An archive's presence is not proof that its architecture or runtime requirements match the application.

Recommended startup checks:

1. Resolve component paths relative to a known application directory, not an arbitrary working directory.
2. Fail clearly if a required component is missing or architecture-mismatched.
3. Check required exports before constructing editor state.
4. Allow plain-text editing when an optional lexer is missing; distinguish this from a missing editor core.
5. Test the package on a clean Windows machine without the developer toolchain.

These are proposed engineering controls, not claims that a particular loader implementation has been verified.

## License and asset boundaries

Scintilla and Lexilla share a permissive license allowing use, modification and distribution with copyright and permission notices retained, and with warranty disclaimers. Preserve the exact upstream license and notices with vendored code and supporting documentation. Review notices in the exact selected archives and any added dependencies; do not assume every future extension has the same license. [Official license](https://www.scintilla.org/License.txt).

Notepad++ is GPL-licensed. Reusing its implementation, resource files, translations or other assets is a separate licensing decision from using Scintilla. This independent project should implement behavior from requirements and public APIs, avoid casually copying NPP code/assets, and keep provenance. If NPP code is intentionally reused, review the applicable GPL obligations before distributing the combined work. Private local development does not by itself authorize future publication. [Official repository](https://github.com/notepad-plus-plus/notepad-plus-plus), [license](https://github.com/notepad-plus-plus/notepad-plus-plus/blob/master/LICENSE).

The ru_notepad application license is a project-owner decision. Do not silently label the new application GPL merely because Notepad++ is the reference, or call it permissively licensed merely because Scintilla is.

Use original ru_notepad artwork, including the requested AI-created icon assets. Do not copy the Notepad++ name/logo/chameleon or imply endorsement. Keep source artwork, generation provenance and export sizes with the project. Inspect small-size readability separately from the larger concept image.

## Why NPP plugins are a separate compatibility project

An NPP plugin is not simply a Scintilla lexer. Its interface includes exported callbacks, a host window handle, two Scintilla view handles, menu-command structures and notifications. See the official [PluginInterface.h](https://github.com/notepad-plus-plus/notepad-plus-plus/blob/master/PowerEditor/src/MISC/PluginsManager/PluginInterface.h).

Plugins also rely on NPP-specific messages, document/buffer identities, command IDs, configuration paths, docking/dialog behavior and lifecycle ordering. See [plugin communication](https://github.com/notepad-plus-plus/npp-usermanual/blob/master/content/docs/plugin-communication.md) and [host message definitions](https://github.com/notepad-plus-plus/notepad-plus-plus/blob/master/PowerEditor/src/MISC/PluginsManager/Notepad_plus_msgs.h).

Consequences for this design:

- Shared use of Scintilla does not make existing NPP plugin DLLs compatible.
- A compatibility host would need ABI-correct structs/callbacks plus enough host behavior for each plugin, matched architecture, notification order and version testing.
- In-process plugins can crash or corrupt the host. Loading untrusted DLLs is code execution, not a harmless document feature.
- Start with no third-party plugin loading. Later prefer a small versioned ru_notepad API with a first-party example, documented capabilities and a safe-disable path.
- If NPP compatibility is still desired, select a narrow test set, inventory required host messages and license constraints, and publish only measured per-plugin results. Do not promise universal compatibility.

The official plugin ecosystem has architecture-specific packages and its own administration/security machinery; copying a plugin menu is not equivalent to reproducing that system. [Plugin manual](https://github.com/notepad-plus-plus/npp-usermanual/blob/master/content/docs/plugins.md).

## Next architectural decisions

1. Confirm Scintilla source/binary availability and the Ru-to-Win32/FFI path on the actual build system.
2. Pin a supported Windows/x64 baseline and initial language list; add ARM64/x86 only with separate evidence.
3. Choose the regex compatibility target explicitly before implementing replacement semantics. The NPP manual documents Boost 1.90 from NPP 8.9.1; other engines can be useful but should be named accurately. [Search reference](https://github.com/notepad-plus-plus/npp-usermanual/blob/master/content/docs/searching.md).
4. Define file-encoding error and safe-save policies before broadening features.
5. Keep first release claims limited to behavior actually exercised on Windows.
