# Hidden-window size measurement

This optional diagnostic investigates the seven-language fixture's failed
1600-pixel client-width precondition in Windows run 39376899291. The actual
fixture passed its 640- and 900-pixel geometry checks. Its existing failure log
did not include actual dimensions, so the cause is not inferred from the log.

The small C executable creates only its own hidden windows. It uses the same
13565952 window style, English nine-menu labels, unchanged application manifest,
640 by 400 minimum tracking size, and two-step outer/client correction as the
Ru fixture. It measures 640, 900, and 1600 requested client widths with a
720-pixel client height. One independent control changes only the maximum
tracking size to at least 4096 by 4096. It captures numeric screen/work-area,
DPI, window-style, incoming/outgoing MINMAXINFO, outer/client, and requested
size values. It does not inspect existing user windows or content.

This is a Win32 geometry experiment, not a run of the Ru application, a UI
acceptance pass, or a performance result. It cannot establish that the editor's
seven-language controls fit at a given width. That still requires the actual
1417-assertion application fixture. The 114-assertion Markdown direct fixture,
3852 total native assertions, and 42-result product contract are unchanged.

The one-time experiment completed on real Windows in run
[39384167995](https://github.com/uppet/ru_notepad/actions/runs/39384167995).
The screen was 1024 by 768 pixels, default maximum tracking size was 1044 by
788, and DPI was 96. The default-policy 1600-pixel request produced a
1028-pixel client width; the independent maximum-tracking override produced
exactly a 1600 by 720 client area. These are Win32 measurements only, not a Ru
fixture or product acceptance result.

The temporary one-shot push title `诊断：确认七语验收窗口尺寸约束` is retired
and no longer selects this diagnostic. The `i18n_window_diagnostic` manual
input remains available and false by default, with a strict case-sensitive
wip/event guard and rejection of conflicting diagnostic inputs. Its concurrency
suffix remains independent of product acceptance; this does not guarantee
independent GitHub runner capacity. The next two-fixture Windows step is
specified in [the focused diagnostic scope](i18n-focused-native-diagnostic.md).

Only `build/window-size-diagnostic-public/measurements.json` is uploaded. It
contains validated fixed numeric fields and source/executable SHA-256 hashes.
Commands, compiler output, raw native streams, paths, and exception details
remain in non-uploaded private directories. The report is published only after
successful native execution, exact schema validation, and input hash rechecks.
