# Pinned upstream source archives

These are unchanged source ZIPs previously obtained from the official Scintilla distribution. They are committed as reproducible build inputs, not as application executables. Current product and policy-pair CI copy and verify these exact bytes without downloading a replacement or trying a network fallback. Updating a dependency requires an explicit source/pin/notice change and a new review.

| Archive | Bytes | SHA-256 |
| --- | ---: | --- |
| `scintilla567.zip` | 1,904,249 | `2309181e59e7da4659f890dbc128db7451ccd094748770e7be674b830494587c` |
| `lexilla554.zip` | 1,598,324 | `5e0a21356e4e2f19d6a38ecd1c8172d5a2b7b4542940568b023386080db90fe0` |

Total compressed input is 3,502,573 bytes. The Scintilla ZIP has 271 file members totaling 5,906,269 uncompressed bytes. Lexilla has 922 file members and 81 directory entries, totaling 5,035,224 file bytes. These are local reproducibility pins, not independently signed upstream checksums.

## Origin and preparation

The [official Scintilla site](https://www.scintilla.org/) links the [upstream SourceForge project](https://sourceforge.net/projects/scintilla/files/). The versioned source locations are:

- Scintilla: <https://www.scintilla.org/scintilla567.zip> and <https://sourceforge.net/projects/scintilla/files/scintilla/5.6.7/scintilla567.zip/download>
- Lexilla: <https://www.scintilla.org/lexilla554.zip> and <https://sourceforge.net/projects/scintilla/files/lexilla/5.5.4/lexilla554.zip/download>

These URLs document provenance and explicit future update procedures. They are not automatic fallback endpoints. `tools/prepare_source_archives.py` validates ordinary independent files, exact sizes/digests and bounded ZIP members/CRC before creating or reusing the ignored `vendor/downloads` copies. It does not extract archives. The build verifies these bytes again before extraction.

The source ZIPs and these source-only accompanying notices are not copied into either runtime or tests release ZIP. Required binary dependency notices continue to accompany the binaries under the packaging rules.

## Retained and accompanying notices

The original archive bytes, including per-file attributions and notices, remain unchanged. The following adjacent notices supplement them; they do not relicense the application or imply that every upstream file has one author.

- `Scintilla-Lexilla-License.txt`: exact `License.txt` shared by these two archives. Some Cocoa files also offer an LGPL alternative; their original dual-license wording is retained. Other per-file author notices remain inside the archives.
- `Boost-License.txt`: exact `test/unit/LICENSE_1_0.txt` in both archives, for bundled Catch2 test material.
- `Mako-LICENSE.txt` and `Mako-AUTHORS.txt`: full upstream [Mako license](https://github.com/sqlalchemy/mako/blob/main/LICENSE) and referenced [authors](https://github.com/sqlalchemy/mako/blob/main/AUTHORS), for `lexilla/test/examples/hypertext/mako.html` and its `.folded` / `.styled` copies. The fixture explicitly cites the [Mako syntax documentation](https://docs.makotemplates.org/en/latest/syntax.html), whose footer licenses Mako and its documentation under MIT terms.
- `Nixpkgs-COPYING.txt`: upstream [Nixpkgs MIT notice](https://github.com/NixOS/nixpkgs/blob/master/COPYING), scoped to the `dockerTools.pullImage` example at `lexilla/test/examples/nix/AllStyles.nix` lines 300–347 and generated copies.
- `NixOS-samples-MIT.txt`: upstream [NixOS sample-code MIT notice](https://github.com/NixOS/nixos-homepage/blob/main/LICENSES/MIT.txt), retained for the earlier Nix tutorial examples. Historical tutorial provenance is not completely established. This is not a statement that every modern documentation page has the same license.
- `Unicode-V3.txt`: the [Unicode data/software permission notice](https://www.unicode.org/license.txt) accompanying Unicode 16-derived tables in `scintilla/src/CharacterCategoryMap.cxx` and `lexilla/lexlib/CharacterCategory.cxx`. Both identify Python 3.14 / Unicode 16.0.0 generation; [Unicode 16 provenance](https://www.unicode.org/Public/16.0.0/ucd/ReadMe.txt) is separate from the application's own Unicode 15 scanner tables.
- `Unicode-2016.txt`: only the opening Unicode copyright/permission section of [Unicode's ICU 58.2 license file](https://github.com/unicode-org/icu/blob/release-58-2/icu4c/LICENSE), for the explicitly copied Unicode 9 `PropList` values. The [official Unicode 9 data header](https://github.com/unicode-org/unicodetools/blob/main/unicodetools/data/ucd/9.0.0-Update/PropList.txt) supplies the corresponding 2016 attribution. Unrelated ICU third-party notices were not copied. The Unicode inventory also includes the Unicode 5.1 `BidiMirroring` reference in `lexilla/lexers/LexRaku.cxx` lines 239–274; its [official data header](https://github.com/unicode-org/unicodetools/blob/main/unicodetools/data/ucd/5.1.0-Update/BidiMirroring.txt) attributes Copyright (c) 1991–2008 Unicode, Inc. The adjacent current Unicode data/software notice is retained with these upstream data sources.

This is a scoped notice inventory, not an exhaustive provenance certification. Some examples also cite R manuals, Microsoft F#/PowerShell documentation, Zsh, and small Pascal/Verilog tutorials; complete historical source-page provenance is not established for every excerpt. Their original source comments are retained; this inventory records the limited uncertainty rather than inventing new permissions or a blanket legal-clearance claim. The application's project license remains undecided. The existing application `packaging/licenses/Unicode.txt` is unchanged.
