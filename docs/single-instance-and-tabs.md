# Configurable single instance and tab closing (candidate)

This increment is implemented in Ru, with narrow Windows x64 FFI declarations.
It is not accepted until the exact candidate passes the bootstrap LLVM, native
fixture and visible two-process GUI gates. No new Windows result is claimed here.

## Single instance

- Enabled by default. Settings → Single instance persists an independent HKCU
  DWORD. The preference affects subsequent launches, not existing windows.
  Turning it off never kills an existing window. Turning it on does not merge
  windows already open. The first participating owner receives later requests.
- `--multi-instance` before file arguments bypasses routing for that launch only.
  Existing `--markdown-phase-diagnostics` may precede or follow that option.
- Sender argv uses the existing Unicode launcher. Absolute paths are frozen in
  the launching working directory before routing; spaces and quoted arguments
  are not reassembled into a shell command. An existing file identity activates
  its existing tab, using the existing normal file-open policy.
- A secondary accepted launch never shows its temporary window and does not add
  an empty tab to the existing window. Empty argv activates the existing owner.
- Routing is bounded to 64 paths and 256 KiB UTF-16 per message. Excess or invalid
  requests do not partially enter the receiver's queue. Normal file decoding,
  path permissions, file identity, large-file confirmation and errors still apply.
- Discovery waits at most five seconds for a ready owner. A single send waits at
  most one second. ACK means a fully copied, validated batch entered the normal
  asynchronous queue, not that all files have finished loading.
- A definite rejection can use a separate window. A send timeout or unavailable
  starting owner does **not** automatically retransmit/open the same files.
  The secondary retains its frozen paths and asks explicitly whether to open
  them separately. Choosing No leaves File → Open Pending Shell Files available.
  Choosing Yes can intentionally duplicate an already accepted request.

Names include the user's SID and Windows session, with normal mutex ACLs,
desktop restrictions and UIPI left intact. Checking the claimed sender HWND is
routing validation, **not cryptographic or strong sender authentication**:
WM_COPYDATA lets a sender supply that HWND. The receiver accepts bounded file
paths only, never executable commands. There is no elevation, message-filter
relaxation, cross-session service, or claim to defend against a malicious process
already operating on the same desktop with equivalent access.

`RU_NOTEPAD_INSTANCE_TEST_KEY` selects an isolated test namespace only when it
matches a bounded 64-character ASCII suffix. It isolates both preference storage
and owner discovery. Invalid values fail closed rather than touching production
preferences. This is a test route, not a configurable arbitrary registry path.

## Tab context menu

Right-click first selects the clicked tab, then offers:

1. Close
2. Close other tabs
3. Close tabs to the left
4. Close tabs to the right
5. Close unmodified tabs
6. Close all tabs

Unavailable actions are disabled. There are no fake pinned-tab or split-view
commands. The keyboard menu's existing close shortcut remains unchanged.

Close batches snapshot stable document identities, not shifting tab indices.
Editors are temporarily read-only while all save/discard confirmations finish.
Cancel, cancelled Save As, or failed asynchronous save leaves all candidate tabs
open. Already committed disk saves are not rolled back. Revision and identity
are checked again before deletion. A successful all-close creates exactly one
clean blank tab. The selected document is preserved if it was not removed.

This uniform, conservative cancellation policy is a deliberate Ru choice.
Notepad++'s operations have differing historical partial-close semantics.

## Behavioral source reference (not copied code)

Reviewed official Notepad++ v8.8.7 commit
`e214d73fe2a29be00eff3822413df00a3baea0fa`:

- [TabBar.cpp](https://github.com/notepad-plus-plus/notepad-plus-plus/blob/e214d73fe2a29be00eff3822413df00a3baea0fa/PowerEditor/src/WinControls/TabBar/TabBar.cpp):
  right-button handling first selects the clicked tab.
- [NppNotification.cpp](https://github.com/notepad-plus-plus/notepad-plus-plus/blob/e214d73fe2a29be00eff3822413df00a3baea0fa/PowerEditor/src/NppNotification.cpp):
  close/other/left/right/unchanged context actions.
- [NppIO.cpp](https://github.com/notepad-plus-plus/notepad-plus-plus/blob/e214d73fe2a29be00eff3822413df00a3baea0fa/PowerEditor/src/NppIO.cpp):
  Close All preconfirmation and differing partial-close behavior in Other/Left/Right.
- [winmain.cpp](https://github.com/notepad-plus-plus/notepad-plus-plus/blob/e214d73fe2a29be00eff3822413df00a3baea0fa/PowerEditor/src/winmain.cpp):
  instance selection, absolute path conversion and inter-window transfer.

These links document behavior. No GPL implementation was copied into the MIT
application. Ru's wire format, bounded uncertainty handling and close transaction
are original implementations.

## Regression evidence required

The four GUI gate groups, active 30-second Markdown stage limits and recent-file
acceptance remain mandatory. Only the 1 MB unclosed-fence serial two-Undo stage
is explicitly deprecated, unexecuted by default and not passed; see the
[scope and TODO](bootstrap-llvm-preview.md#deprecated-case-and-todo-2026-10-27). New stage3 fixtures cover close policy,
routing policy, isolated settings and real Win32 close/save/cancel behavior.
Visible tests exercise real second processes, configuration persistence, Unicode
relative paths, duplicate identity activation, six actual popup actions, and
cancellation. Controlled suspended-owner tests are failure-path tests, not normal
UI latency measurements. Receipts bind the exact four runtime binaries.

The previous delivered b79 bootstrap preview passed its own original GUI gates.
Its separate C-built baseline failed the 1 MB unclosed-fence serial two-Undo stage
at 30.006871 seconds: length/savepoint was observed restored at 20.818713 seconds
but folding was still pending. That separate baseline is not a passing release
suite; this candidate must earn fresh acceptance, not inherit the previous ZIP's
result.
