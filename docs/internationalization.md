# Interface languages (development candidate)

This independent candidate adds an application-owned interface in English, Simplified Chinese, Japanese, Korean, Spanish, Russian and Italian. It is based on the current C++ folding and 0.1.8 Markdown candidate; its own full Windows acceptance remains pending. The interface-language menu is separate from the syntax-language menu. No eighth language is claimed.

## Choosing a language

On first start, the app uses the Windows user's UI language. Regional language IDs select the corresponding supported language; Chinese IDs currently select Simplified Chinese, including Traditional-Chinese system locales. Unsupported system languages use English. Use **UI language** to choose a language immediately or return to **System default**.

An explicit choice is saved as `InterfaceLanguage` under `HKCU\Software\ru_notepad\Preferences`. This is one per-user preference shared by portable copies, not a file beside the EXE. Starting the application only reads it; choosing a language writes it. It does not change Windows display/input languages, default applications, file associations or document encodings. A malformed/unknown stored language uses English. A read error uses the system language and reports the actual Windows code. A failed write leaves the chosen language active for that session and displays the actual Windows code.

Switching the interface updates menus, native labels, search cues, unnamed tab names, status presentation and subsequent application dialogs. It does not recreate the editor or change document text, selection, undo history, syntax selection, encoding, line endings or filename spelling. Named files keep their original Unicode names. Language names are shown in their own language so the menu remains recognizable after an accidental change.

## Catalog contract and Ru implementation

- `locales/ui.json` and `locales/errors.json` are UTF-8 source catalogs with stable semantic keys. Every key has exactly the same seven language entries.
- `python tools/generate_i18n.py` validates them and emits the deterministic `src/i18n_catalog.ru`. Builds and static checks reject stale generated data. Catalogs and the generator are covered by each build receipt.
- The generated resource table is embedded in the native executable. Runtime lookup, language policy, parameter substitution, preference handling, UI updates and layout policy are written in Ru. There is no runtime Python, JSON parsing, download or translation service.
- Missing/empty translations fall back to English. A completely unknown key is visibly rendered as `[key]`, rather than disappearing.
- Templates accept only exact ASCII `{0}` through `{9}` placeholders. Every locale must retain the same parameter multiset. Values are inserted in one pass: a filename such as `report{0}😀.txt` is never interpreted as a second template.
- ASCII menu mnemonics are consistent across locales and unique within each menu. Existing keyboard shortcuts retain their command IDs. Search buttons are sized using actual Windows font measurements and wrap into additional rows when needed. The top-level window has a 640×400 minimum tracking size. Very long status text may still be clipped at narrow widths.
- File-dialog labels and titles use UTF-16. Filter masks are application constants; translated labels cannot inject separators. File paths retain the existing Unicode Win32 APIs and strict encoding/file-safety policy.
- Known user-facing file, encoding and operating-system failures have localized text. Actual system codes, API names and unknown internal diagnostic details are retained. Technical logs remain diagnostic text.

## Verification and boundaries

See the [dated candidate validation record](i18n_candidate_validation.md) for observed passes, integration provenance and the remaining Windows/manual gates.

`python tools/test_i18n.py --ru-root PATH` checks catalog completeness, placeholders, missing/empty fallback, language IDs, mnemonic collisions, shortcut identity, literal filename substitution and narrow/wide layout policy. It executes the production Ru code with the actual interpreter and a host-C executable. It also compares every translated value against the JSON source in both backends.

`python tools/test_i18n_models.py` independently pins every original menu command and lexer style/color pair, with mismatch/deletion/reordering negative controls for the flattened primitive tables.

The Windows gate additionally requires `i18n_policy`, `i18n_settings_native` and `app_i18n_native`. Registry tests use a unique synthetic `I18nTests` subkey and clean it; they never write production Preferences. Application tests use disposable synthetic data and session-only language switching. A Linux/C pass or a cross-compiled PE is not a Windows execution pass.

This is interface localization. It does not certify CJK IME composition, font availability, grapheme-aware caret motion, accessibility or every legacy code page. The existing UTF-8/UTF-16/Windows-1252/GBK support is unchanged. Windows-owned Yes/No/Cancel buttons, common-dialog chrome and shell messages follow Windows' installed language resources; the application does not replace them. The independent pre-Ru diagnostic launcher still has English emergency diagnostics when the Ru runtime cannot start.

### Remaining Windows/manual acceptance

Use disposable copies and record the exact executable/source hashes and Windows build:

1. Select each of the seven languages, close and restart, and verify persistence; test System default, unsupported system locale, malformed preference and a denied write without losing its error code.
2. At 100%, 150% and 200% scaling, inspect all menu groups, search rows, cancel button, status and long prompts at the minimum window size and maximized. Check glyph fallback for Han, kana, Hangul and Cyrillic and repeated language switching.
3. Open, Save As, cancel and reject overwrite for filenames containing Chinese, Japanese, Korean, Cyrillic, accented Spanish/Italian, emoji and braces. Verify both real file bytes and exact displayed names; exercise filtered and All files views.
4. With Microsoft Chinese, Japanese and Korean IMEs, test composition start/update/commit/cancel, candidate selection, reconversion, switching tabs/windows, search inputs and save during/after composition. Check that an unfinished composition is not lost or accidentally treated as an editor command. These tests require a real Windows input session.
5. Check keyboard-only mnemonics, Tab/focus order, native dialog buttons, screen-reader names, clipboard round trips, selection and Undo/Redo. Confirm language changes do not alter text, encoding, newline mode, syntax state or dirty indicators.
6. Exercise missing DLLs, ordinary file errors and pending syntax warnings in each language. Confirm localized explanation plus the original API/system code; pre-runtime bootstrap failures retain their documented English fallback.

Do not describe the candidate as fully internationalization- or IME-accepted until the applicable automated and manual checks have recorded results.
