# Native dependencies

Scintilla and Lexilla build inputs are copied from the exact reviewed source ZIPs in `third_party/source_archives` by `tools/prepare_source_archives.py`. Current product and policy CI do not fetch replacement archives or use a network fallback. The ignored downloads and extracted source here are build outputs; never use unreviewed DLLs. Required upstream notices accompany each portable binary package.

A failed preparation may leave a newly created partial archive. Retry in a fresh clean checkout; the helper neither overwrites nor automatically deletes partial outputs, and each attempt requires a new receipt path.

The application code does not use the Notepad++ source, branding, or plugin ABI.
