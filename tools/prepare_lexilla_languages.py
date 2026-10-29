#!/usr/bin/env python3
"""Add the permissively licensed Objective-C lexer without changing upstream files.

The two original official archives stay byte-identical. The replacement catalogue
is a separately named, reproducible translation unit selected with make OBJS.
Both build routes must prepare and verify these supplemental compilation inputs.
"""
from __future__ import annotations
import hashlib
from pathlib import Path

SOURCE = 'native/lexilla/LexObjC.cxx'
LICENSE = 'native/lexilla/License.txt'
INPUTS = (SOURCE, LICENSE, 'tools/prepare_lexilla_languages.py')
SOURCE_SHA256 = '62c74fa9c9167a608f6321938fdd002bcc16c474df0bc1da01bc27355a3eba50'
LICENSE_SHA256 = 'ac32743bd464c837e481beae20df65a9207f84d3ff1912f6003000343e9c753d'
CATALOGUE_SHA256 = 'd0a07287a100865d94f2702a6183fe97e26c5968d1ef6fe5f7465621ef12d9c5'
MAKE_OBJECT = 'OBJS=LexillaRu.o'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_file(root, relative):
    root = Path(root).absolute()
    file = root / relative
    if any(item.is_symlink() for item in (file, *file.parents)) or not file.is_file():
        raise RuntimeError('Missing or linked supplemental lexer input: ' + relative)
    return file


def source_inputs(root):
    result = {name: digest(safe_file(root, name).read_bytes()) for name in INPUTS}
    if result[SOURCE] != SOURCE_SHA256 or result[LICENSE] != LICENSE_SHA256:
        raise RuntimeError('Objective-C lexer source/license differs from reviewed upstream bytes')
    return result


def expected_files(root):
    source_inputs(root)
    original = safe_file(root, 'vendor/lexilla/src/Lexilla.cxx').read_bytes()
    if digest(original) != CATALOGUE_SHA256:
        raise RuntimeError('Official Lexilla catalogue differs from pinned 5.5.4')
    # Exactly one declaration and one registration, in the generated sections.
    before_decl = b'extern const LexerModule lmNull;'
    before_entry = b'\t\t&lmNull,'
    if original.count(before_decl) != 1 or original.count(before_entry) != 1:
        raise RuntimeError('Unexpected Lexilla catalogue shape')
    eol = b'\r\n' if b'\r\n' in original else b'\n'
    catalogue = original.replace(before_decl, before_decl + eol + b'extern const LexerModule lmObjC;')
    catalogue = catalogue.replace(before_entry, before_entry + eol + b'\t\t&lmObjC,')
    # These three constants are from N++ v8.9.8.1 lexilla/include/SciLexer.h.
    # Keep them local to the extra translation unit, not the official header.
    defines = (b'// ru_notepad compatibility constants; original lexer body follows unchanged.\n'
               b'#define SCLEX_OBJC 151\n#define SCE_OBJC_DIRECTIVE 20\n#define SCE_OBJC_QUALIFIER 21\n')
    return {
        'vendor/lexilla/src/LexillaRu.cxx': catalogue,
        'vendor/lexilla/lexers/LexObjC.cxx': defines + safe_file(root, SOURCE).read_bytes(),
    }


def prepare(root):
    root = Path(root)
    expected = expected_files(root)
    for name, data in expected.items():
        target = root / name
        if any(item.is_symlink() for item in (target, *target.parents)):
            raise RuntimeError('Linked supplemental lexer output: ' + name)
        if target.exists():
            if not target.is_file() or target.read_bytes() != data:
                raise RuntimeError('Supplemental lexer output differs: ' + name)
        else:
            with target.open('xb') as stream:
                stream.write(data)
    return verify(root)


def verify(root):
    expected = expected_files(root)
    for name, data in expected.items():
        if safe_file(root, name).read_bytes() != data:
            raise RuntimeError('Supplemental lexer compilation input changed: ' + name)
    return {'schema': 'ru-notepad-lexilla-extra-v1', 'make_object': MAKE_OBJECT,
            'source_sha256': source_inputs(root),
            'generated_sha256': {name: digest(data) for name, data in expected.items()}}
