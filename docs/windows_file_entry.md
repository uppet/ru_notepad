# Windows file-entry integration

`src/associations.ru`, `src/associations_policy.ru`, and `src/file_drop.ru` are
Ru modules using fixed Windows x64 `如:密` signatures. The distributed program
does not need Python or an installer.

## Default-editor candidates

Registration is an explicit application UI action. Import and application startup
do not write the registry. The UI confirms registration/removal before calling
`注册()` / `注销()`; these production functions obtain the exact current executable
path with `GetModuleFileNameW`. `查询状态()` is read-only and returns `none`,
`registered`, `partial`, or `otherowner` for that executable.

Registration creates only the current user's candidate information:

- `HKCU\Software\Classes\Applications\ru_notepad.exe`, its open command and
  explicit `SupportedTypes` values
- `HKCU\Software\Classes\RuNotepad.Text`, its icon and open command
- `HKCU\Software\RuNotepad\Capabilities` and explicit file associations
- The `ru_notepad` value in `HKCU\Software\RegisteredApplications`
- A `RuNotepad.Text` `REG_NONE` value in each supported extension's
  `OpenWithProgids` key

The explicit extension list is `.txt`, `.ru`, `.md`, `.log`, `.csv`, `.json`,
`.xml`, `.yaml`, `.yml`, `.ini`, `.cfg`, `.c`, `.h`, `.cpp`, and `.hpp`.
There is no wildcard handler, elevation, HKLM write, extension default-value
change, or `UserChoice`/hash manipulation. Both open commands are exactly
`"<absolute current executable>" "%1"`, preserving Unicode and spaces.

`打开设置(hwnd)` opens Microsoft's universal `ms-settings:defaultapps` URI.
The user makes the actual default-app choice in Windows. Registration alone
does not make ru_notepad the default editor. This release deliberately avoids
version-specific app deep links or unsupported default-association interfaces.
If Settings cannot be opened, the application reports that instead of claiming
the default changed.

Every planned value is checked for a conflict before registration starts. A
second portable copy cannot overwrite or unregister an existing owner's entries.
Unregistration checks current-executable ownership, deletes only values whose
type and contents still match the plan, and preserves modified values and
foreign child keys. Only empty, fixed application-owned keys are pruned; shared
`RegisteredApplications` and extension keys are left in place. This is not a
registry transaction: simultaneous edits by another process are not covered by
an atomic compare-and-delete guarantee. Access failure can leave a partial
registration, which the read-only status query exposes. Move a registered
portable application only after removing its candidate registration at the old
location, then register from the new location.

Registry strings are bounded to 128 KiB and strictly validated with
`WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS)` before the native UTF-16
decoder. Malformed, nonterminated, embedded-NUL, oversized, or wrong-type values
do not count as matching ownership.

## Shell drag-and-drop

Call `启用(hwnd)` for the receiving window. On `WM_DROPFILES` (`0x0233`), reinterpret
the pointer-width `wParam` as a native pointer and pass it once to `接收(hdrop)`.
This transfers ownership. The function copies the complete ordered path list
and calls `DragFinish` once before returning. Its ordinary error path also calls
`DragFinish` once. Do not call `DragFinish` again or forward a consumed drop to
`DefWindowProc`.

Call `启用编辑器(editorHwnd, parentHwnd)` for every Scintilla editor child after
creation. The pinned Scintilla source registers a text-only OLE target during
`WM_CREATE`; accepting files only on the main window is insufficient when the
pointer is over the editor body. The helper verifies the real parent and current
window thread, installs one module-lifetime six-argument `SUBCLASSPROC`, revokes
the child's OLE target, and enables `DragAcceptFiles` on the child. Only `S_OK`
and `DRAGDROP_E_NOTREGISTERED` are accepted from `RevokeDragDrop`. Repeated setup
updates the same subclass instead of stacking callbacks.

The subclass forwards `WM_DROPFILES` synchronously to the verified parent, which
alone consumes the HDROP. It removes itself on `WM_NCDESTROY` and delegates other
messages through `DefSubclassProc`. A fatal native callback failure posts a
nonzero quit message. Microsoft documents that OLE file drag loops simulate
`WM_DROPFILES` for non-OLE file-drop targets. This explicitly prioritizes opening
files over Scintilla OLE text drops: external text dragging and drag-to-move text
inside the editor are unavailable through this revoked OLE target. Normal typing,
selection, copy/paste, and application file-drop opening remain separate paths.

Each path uses a `DragQueryFileW(..., NULL, 0)` length query followed by a precisely
sized UTF-16 buffer, with strict Unicode validation before decoding. There is
no `MAX_PATH` truncation. A drop has at most 64 paths, each at most 32,000 UTF-16
units, and a total storage bound of 2,097,152 units including terminators. An
over-limit or malformed drop fails as a whole, with a visible error; no partial
list is opened. Paths are not split on spaces and are not converted through an
ANSI code page.

The caller feeds the copied paths to the same queued-open path used for menus
and command-line files. Document identity, directories, duplicates, dirty tabs,
large-file cancellation, and per-file errors remain application policy.

## Acceptance fixtures

- `tests/associations_policy.ru`: 19 portable assertions, run in the interpreter
  and emitted native C, covering exact quoting, explicit candidate-only plans,
  test-prefix validation, and no extension default or UserChoice writes.
- `tests/associations_native.ru`: 36 real-Windows assertions. The production
  registration implementation receives an injectable prefix constrained to a
  newly created `HKCU\Software\RuNotepad.Tests\native-<PID>-<tick>` subtree.
  Synthetic foreign defaults and UserChoice values are tripwires inside that
  subtree. Tests cover all 56 typed values, second-copy ownership, conflict
  preflight, idempotence, safe removal, malformed high/low surrogates, foreign
  children, and exact fixture cleanup. The runner's actual defaults are never
  queried or changed by this fixture.
- `tests/file_drop_native.ru`: 38 real-Windows assertions. A registered HWND
  receives an actual `WM_DROPFILES` with a `GlobalAlloc`/`DROPFILES` fixture.
  Tests cover multiple paths, Chinese/emoji/spaces, paths above `MAX_PATH`, empty
  lists, high/low surrogate rejection, count/length limits, the 32,000-unit
  boundary, and repeated drops. `GlobalFlags` verifies each consumed HDROP was
  freed, including rejection paths. A real Scintilla child additionally proves
  its OLE target is revoked, `WS_EX_ACCEPTFILES` and the parent-bearing subclass
  are installed, repeated enable does not duplicate forwarding, wrong-parent
  routing is rejected, child-body drops preserve all paths without editing text,
  malformed drops recover, and destruction/new editor creation is safe.
- `tests/drop_fixture.ru`: reusable native synthetic HDROP construction for
  application-level queue tests; it is a helper, not a standalone test target.

Cross-compilation and static checks are not Windows runtime acceptance. The
native fixtures must execute in the real Windows CI lane, never Wine.

## Microsoft API references

- [Application registration](https://learn.microsoft.com/windows/win32/shell/app-registration)
- [Default programs registration](https://learn.microsoft.com/windows/win32/shell/default-programs)
- [Launch Windows Settings](https://learn.microsoft.com/windows/apps/develop/launch/launch-settings-app)
- [Default Apps Settings and per-user registration](https://learn.microsoft.com/windows/apps/develop/launch/launch-default-apps-settings)
- [DragAcceptFiles](https://learn.microsoft.com/windows/win32/api/shellapi/nf-shellapi-dragacceptfiles)
- [DragQueryFileW](https://learn.microsoft.com/windows/win32/api/shellapi/nf-shellapi-dragqueryfilew)
- [DragFinish](https://learn.microsoft.com/windows/win32/api/shellapi/nf-shellapi-dragfinish)
- [DROPFILES](https://learn.microsoft.com/windows/win32/api/shlobj_core/ns-shlobj_core-dropfiles)
- [CF_HDROP OLE-to-WM_DROPFILES fallback](https://learn.microsoft.com/windows/win32/shell/clipboard)
- [SetWindowSubclass](https://learn.microsoft.com/windows/win32/api/commctrl/nf-commctrl-setwindowsubclass)
- [SUBCLASSPROC](https://learn.microsoft.com/windows/win32/api/commctrl/nc-commctrl-subclassproc)
- [RevokeDragDrop](https://learn.microsoft.com/windows/win32/api/ole2/nf-ole2-revokedragdrop)
