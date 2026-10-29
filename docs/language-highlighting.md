# Language highlighting coverage

## Fixed scope

The catalog contains **95 selectable modes**: the **93 built-in selectable modes of Notepad++ v8.9.8.1** (Normal Text plus 92 language/format modes), together with the existing **Ru and Markdown** modes. The upstream `langs.model.xml` has 95 records, but its embedded JavaScript and internal search-result records are not separate selectable languages. User-defined languages and extra plugins are excluded.

`syntax/notepadpp-baseline.json` is an independent factual snapshot, extracted from upstream rather than from the application catalog. It fixes each official mode ID, name, lexer, extensions, source tag, source paths and SHA-256 hashes. `tools/test_language_catalog.py` requires an exact match of the 93 upstream IDs and their mappings; counting entries alone cannot pass. Display-only capitalization and Normal Text → Plain text aliases are explicit in the test.

## Behavior and boundaries

- NFO/MS-DOS uses the upstream null lexer: it is a plain-text display mode, not colored source code. This does not promise Notepad++'s OEM font/encoding presentation.
- JSON and JSON5 are distinct selectable configurations sharing Lexilla's JSON lexer. JSON5 enables permissive/comment syntax; `.jsonc` is additionally detected as JSON5. Highlighting is not a JSON5 parser or validator.
- `.tex` defaults to **TeX**, matching Notepad++'s reverse default-extension lookup; LaTeX remains manually selectable. `.m` defaults to MATLAB; Objective-C uses `.mm`.
- Special filenames such as Makefile and CMakeLists.txt are recognized case-insensitively. Existing C++ suffixes `c++`, `h++`, `inl`, Chinese Ru support, and Markdown remain available.
- This work covers lexing, highlighting, language selection, and detection. It does not add Notepad++ autocomplete/API databases, function lists, UDL/plugin infrastructure, or byte-for-byte theme/keyword parity. Keywords include independently specified language facts and permissively licensed upstream data; not every library API identifier is promised.

## Sources and licensing

Lexilla 5.5.4 supplies the actual language lexers, not a single approximate fallback lexer. Objective-C uses the separately permission-noticed `LexObjC.cxx` from the pinned Notepad++ tag. Its source header explicitly applies Lexilla's permissive license. Notepad++'s GPL keyword XML is **not** redistributed as the runtime keyword database. The baseline retains only factual identifiers/mappings and source hashes.

Most keyword/property data comes from the official **SciTE 5.6.7** source archive and its bundled Lexilla fixtures, under the associated permissive notices. Additional keyword sources are Godot's MIT-licensed tokenizer, Gui4Cli's MIT-licensed command table, and Pygments 2.21.0's BSD-licensed T-SQL table. Exact license texts ship in `packaging/licenses`; runtime configuration source paths/hashes are also recorded per catalog row.

### Reproducible source evidence

The following hashes identify the exact bytes used (a moving source URL alone is not a version pin).

- [SciTE 5.6.7 archive](https://www.scintilla.org/scite567.zip)
  SHA-256: `017ada7525c1fd2d50611fcdca88572807be730d7c548f31ede0f35dd950d8f5`
- [Godot tokenizer snapshot](https://raw.githubusercontent.com/godotengine/godot/master/modules/gdscript/gdscript_tokenizer.cpp)
  SHA-256: `e46b60d6e738be562aeb4471fa3c7908f270c61aa5b4b080a98c8404c8a1cd66`
- [Godot MIT license snapshot](https://raw.githubusercontent.com/godotengine/godot/master/LICENSE.txt)
  SHA-256: `b0435e3b3e4e55238f05f4b306f30524a1b2e20147810d436eaa554fa6855c80`
- [Gui4Cli CVS archive](https://sourceforge.net/code-snapshots/cvs/g/gu/gui4cli.zip)
  SHA-256: `3f08c17d13cd5bf4db678a6d973e3401cafb49736c45729db021c7662e1c7252`
- [Gui4Cli MIT license (CVS head of G4C/_LICENSE.txt,v in archive)](https://sourceforge.net/code-snapshots/cvs/g/gu/gui4cli.zip)
  SHA-256: `35aab0ec1cafcfd3129d046ac23b8239c9fa5ee7458bb28e6a0b5c34c17d273e`
- [Pygments 2.21.0 T-SQL table](https://raw.githubusercontent.com/pygments/pygments/2.21.0/pygments/lexers/_tsql_builtins.py)
  SHA-256: `330e949cc0728eed14f8e0604fc69fdc0e2eb5fad2d344e7e650e76b106d8fd7`
- [Pygments 2.21.0 BSD license](https://raw.githubusercontent.com/pygments/pygments/2.21.0/LICENSE)
  SHA-256: `a9d66f1d526df02e29dce73436d34e56e8632f46c275bbdffc70569e882f9f17`
- [Objective-C lexer](https://raw.githubusercontent.com/notepad-plus-plus/notepad-plus-plus/v8.9.8.1/lexilla/lexers/LexObjC.cxx)
  SHA-256: `62c74fa9c9167a608f6321938fdd002bcc16c474df0bc1da01bc27355a3eba50`
- [Objective-C Lexilla license](https://raw.githubusercontent.com/notepad-plus-plus/notepad-plus-plus/v8.9.8.1/lexilla/License.txt)
  SHA-256: `ac32743bd464c837e481beae20df65a9207f84d3ff1912f6003000343e9c753d`
- SciTE archive member `scite/License.txt`: `dd6e71c6cfdb007dde8cb2becbb0131f5ce1e3066c6698a8d7af20a097f326cb` (same archive URL above).
- SciTE archive member `lexilla/License.txt`: `185c5a37521316e940ead89cbf0b1ba5862d810c7c966e6c6a14a4a515b23625` (same archive URL above).

Gui4Cli extraction reads the first full CVS `text` block, unescaping `@@`, rather than concatenating historic reverse deltas. Godot data is a hash-pinned development snapshot, not a claim of a specific stable Godot release. Source hashes make the consumed bytes auditable; mutable URLs may subsequently serve different bytes.
