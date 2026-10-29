#!/usr/bin/env python3
"""Portable, independent regression oracles for the flattened Ru UI models.

Run: python tools/test_i18n_models.py

The old menu IDs/order and every old Lexilla style/colour pair were reviewed
against src/main.ru and src/syntax.ru at 5a619410ea93ec0b8fb5197a4780b615a308e4f9.
The constants below deliberately do not read git, import the catalog generator,
or derive expected values from the production arrays. The eight UI-language
commands, Find Previous, Open Pending Shell Files and Single Instance are the
explicit additions to the original 42 commands (53 total). English labels anchor the catalog keys' meanings as well as their ID/group associations.

This is source-model and consumer-wiring verification, not a Ru interpreter,
compiler-budget check, native Windows execution, or GUI acceptance test.
"""
from __future__ import annotations

import ast
from copy import deepcopy
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]

# Fixed independent expectations: (group key, English title, ordered commands).
# Commands are (Win32 command ID, catalog key, English label).
EXPECTED_MENUS = (
    ('menu.file', '&File', (
        (101, 'command.new', '&New\tCtrl+N'),
        (102, 'command.open', '&Open...\tCtrl+O'),
        (108, 'command.open_windows1252', 'Open as &Windows-1252...'),
        (109, 'command.open_gbk', 'Open as &GBK (CP936)...'),
        (103, 'command.save', '&Save\tCtrl+S'),
        (104, 'command.save_as', 'Save &As...\tCtrl+Shift+S'),
        (105, 'command.close_tab', '&Close tab\tCtrl+W'),
        (111, 'command.previous_tab', '&Previous tab\tCtrl+Shift+Tab'),
        (112, 'command.next_tab', 'Next &tab\tCtrl+Tab'),
        (113, 'command.open_pending_shell', 'Open Pending Shell Files… (&Q)'),
        (106, 'command.exit', 'E&xit'),
    )),
    ('menu.edit', '&Edit', (
        (201, 'command.undo', '&Undo\tCtrl+Z'),
        (202, 'command.redo', '&Redo\tCtrl+Y'),
        (203, 'command.cut', 'Cu&t\tCtrl+X'),
        (204, 'command.copy', '&Copy\tCtrl+C'),
        (205, 'command.paste', '&Paste\tCtrl+V'),
        (206, 'command.select_all', 'Select &All\tCtrl+A'),
    )),
    ('menu.search', '&Search', (
        (301, 'command.find', '&Find...\tCtrl+F'),
        (302, 'command.replace', '&Replace...\tCtrl+H'),
        (303, 'command.find_next', 'Find &Next\tF3'),
        (308, 'command.find_previous', 'Find &Previous\tShift+F3'),
    )),
    ('menu.encoding', 'E&ncoding', (
        (401, 'command.save_utf8', 'Save as &UTF-8'),
        (402, 'command.save_utf8_bom', 'Save as UTF-8 with &BOM'),
        (403, 'command.save_utf16le', 'Save as UTF-16 &LE'),
        (404, 'command.save_utf16be', 'Save as UTF-16 B&E'),
        (405, 'command.save_windows1252', 'Save as &Windows-1252'),
        (406, 'command.save_gbk', 'Save as &GBK (CP936)'),
    )),
    ('menu.language', '&Language', (
        (701, 'command.language_plain', '&Plain text'),
        (702, 'command.language_cpp', '&C / C++'),
        (703, 'command.language_json', '&JSON'),
        (704, 'command.language_ru', '&Ru / 如言'),
        (705, 'command.language_markdown', '&Markdown'),
    )),
    ('menu.view', '&View', (
        (501, 'command.toggle_wrap', 'Toggle word &wrap'),
        (502, 'command.zoom_in', 'Zoom &in\tCtrl++'),
        (503, 'command.zoom_out', 'Zoom &out\tCtrl+-'),
        (504, 'command.zoom_reset', '&Reset zoom\tCtrl+0'),
        (505, 'command.fold_all', '&Collapse all folds\tCtrl+Shift+['),
        (506, 'command.unfold_all', '&Expand all folds\tCtrl+Shift+]'),
        (507, 'command.toggle_markdown_folds', 'Toggle &Markdown heading folds'),
    )),
    ('menu.settings', 'Se&ttings', (
        (801, 'command.register_association', '&Register Open With candidate...'),
        (802, 'command.default_apps', 'Choose &defaults in Windows Settings...'),
        (803, 'command.unregister_association', '&Unregister this copy...'),
        (804, 'command.registration_status', 'Registration &status'),
        (805, 'command.single_instance', 'Single instance (next launch) (&I)'),
    )),
    ('menu.ui_language', '&UI language', (
        (850, 'language.system', 'System &default'),
        (851, 'language.en', '&English'),
        (852, 'language.zh_cn', '简体中文(&C)'),
        (853, 'language.ja', '日本語(&J)'),
        (854, 'language.ko', '한국어(&K)'),
        (855, 'language.es', 'E&spañol'),
        (856, 'language.ru', 'Русский(&R)'),
        (857, 'language.it', '&Italiano'),
    )),
    ('menu.help', '&Help', (
        (601, 'command.about', '&About ru_notepad'),
    )),
)

# A second, compact record of the pre-i18n menu's complete group/ID ordering.
LEGACY_COMMAND_GROUPS = (
    ('menu.file', (101, 102, 108, 109, 103, 104, 105, 111, 112, 106)),
    ('menu.edit', (201, 202, 203, 204, 205, 206)),
    ('menu.search', (301, 302, 303)),
    ('menu.encoding', (401, 402, 403, 404, 405, 406)),
    ('menu.language', (701, 702, 703, 704, 705)),
    ('menu.view', (501, 502, 503, 504, 505, 506, 507)),
    ('menu.settings', (801, 802, 803, 804)),
    ('menu.help', (601,)),
)

# Original nested palettes, transcribed in full; never reconstructed from the
# new production style-ID and colour arrays under test.
EXPECTED_PALETTES = {
    'cpp': (
        (1, 3573283), (2, 3573283), (3, 3573283), (4, 12665455),
        (5, 12934144), (6, 1381795), (7, 1381795), (9, 12665455),
        (10, 4473924), (12, 3023567), (15, 3573283), (17, 3573283),
        (18, 3023567), (20, 1381795), (23, 3573283), (24, 3573283),
        (27, 12665455),
    ),
    'json': (
        (1, 12665455), (2, 1381795), (3, 3023567), (4, 2514553),
        (5, 12665455), (8, 4473924), (9, 1381795), (10, 1381795),
        (11, 12934144), (12, 12934144), (13, 3023567),
    ),
    'markdown': (
        (2, 12934144), (3, 12934144), (4, 12665455), (5, 12665455),
        (6, 12934144), (7, 12934144), (8, 12934144), (9, 12934144),
        (10, 12934144), (11, 12934144), (13, 2514553), (14, 2514553),
        (15, 3573283), (16, 8421504), (17, 4473924), (18, 12665455),
        (19, 1381795), (20, 1381795), (21, 1381795),
    ),
}

MENU_ARRAY_TYPES = {'组键们': str, '组量们': int, '号们': int, '键们': str}


def function_body(source, name):
    matches = list(re.finditer(
        rf'^算 {re.escape(name)}(?:[ :]).*?\n(?P<body>.*?)^法[ \t]*$',
        source, re.MULTILINE | re.DOTALL))
    if len(matches) != 1:
        raise ValueError(f'Expected one Ru function {name}')
    return matches[0].group('body')


def literal_array(source, name, item_type):
    matches = list(re.finditer(
        rf'^[ \t]*{re.escape(name)} 取 (?P<value>\[.*?\])\.[ \t]*$',
        source, re.MULTILINE))
    assignments = re.findall(rf'^[ \t]*{re.escape(name)} 取 ', source, re.MULTILINE)
    if len(matches) != 1 or len(assignments) != 1:
        raise ValueError(f'Expected exactly one literal assignment for {name}')
    try:
        value = ast.literal_eval(matches[0].group('value'))
    except (SyntaxError, ValueError) as error:
        raise ValueError(f'Invalid literal for {name}') from error
    if type(value) is not list or any(type(item) is not item_type for item in value):
        raise ValueError(f'{name} must be a flat {item_type.__name__} array')
    return value


def require_wiring(source, fragment):
    """Check only documented consumer statements, ignoring indentation/comments."""
    def normalized(text):
        return '\n'.join(line.strip() for line in text.splitlines()
                         if line.strip() and not line.lstrip().startswith('#'))
    if normalized(fragment) not in normalized(source):
        raise ValueError('Parallel-array consumer wiring changed')


def read_menu_arrays(source):
    body = function_body(source, '菜单')
    return {name: literal_array(body, name, kind)
            for name, kind in MENU_ARRAY_TYPES.items()}


def decode_menu(arrays):
    groups, counts = arrays['组键们'], arrays['组量们']
    ids, keys = arrays['号们'], arrays['键们']
    if (len(groups) != len(counts) or len(ids) != len(keys)
            or any(count <= 0 for count in counts) or sum(counts) != len(ids)):
        raise ValueError('Menu parallel-array lengths or group bounds differ')
    result = []
    start = 0
    for group, count in zip(groups, counts):
        end = start + count
        result.append((group, tuple(zip(ids[start:end], keys[start:end]))))
        start = end
    return tuple(result)


def validate_menu(source):
    arrays = read_menu_arrays(source)
    actual = decode_menu(arrays)
    expected = tuple((group, tuple((number, key) for number, key, _ in commands))
                     for group, _, commands in EXPECTED_MENUS)
    if actual != expected:
        raise ValueError('Menu ID, catalog meaning, group, or order changed')
    body = function_body(source, '菜单')
    require_wiring(body, '''
        组位 取 0.
        位 取 0.
        循 组键们 其 量 次
            子 取 窗 其 成功 ((窗 其 CreatePopupMenu) 其 调用 []) 'CreatePopupMenu'.
            循 组量们[组位] 次
                号 取 号们[位].
    ''')
    require_wiring(body, '''
        窗 其 菜单项 子 标记 号 (本地 其 文本 键们[位]).
        位 取 位+1.
        环
        若 组位 == 0 则 近期菜单 子. 然
        窗 其 菜单项 主 16 ((窗 其 UP) 其 重释 子) (本地 其 文本 组键们[组位]).
        子 取 空.
        组位 取 组位+1.
        环
    ''')
    return actual


def validate_menu_catalog(catalog):
    labels = {}
    for group, title, commands in EXPECTED_MENUS:
        labels[group] = title
        labels.update((key, label) for _, key, label in commands)
    actual = {key for key in catalog if key.startswith(('menu.', 'command.', 'language.'))}
    if actual != set(labels):
        raise ValueError('Menu catalog key coverage changed')
    for key, english in labels.items():
        if catalog[key].get('en') != english:
            raise ValueError(f'Catalog meaning changed for {key}')


def palette_sections(source):
    body = function_body(source, '_选择')
    match = re.search(
        r"^[ \t]*若 语言 == 'cpp' 则\n(?P<cpp>.*?)"
        r"^[ \t]*另 若 语言 == 'json' 则\n(?P<json>.*?)"
        r'^[ \t]*另\n(?P<markdown>.*?)^[ \t]*然 然[ \t]*$',
        body, re.MULTILINE | re.DOTALL)
    if match is None:
        raise ValueError('Expected C++, JSON, and Markdown palette branches')
    return match.groupdict()


def validate_palettes(source):
    sections = palette_sections(source)
    actual = {}
    for language, section in sections.items():
        ids = literal_array(section, '色号们', int)
        colors = literal_array(section, '色值们', int)
        if len(ids) != len(colors):
            raise ValueError(f'{language}: palette arrays differ in length')
        actual[language] = tuple(zip(ids, colors))
        if actual[language] != EXPECTED_PALETTES[language]:
            raise ValueError(f'{language}: style, colour, or pair order changed')
    require_wiring(function_body(source, '_选择'), '''
        位 取 0.
        循 色号们 其 量 次
            _配色 态 柄 色号们[位] 色值们[位].
            位 取 位+1.
        环
    ''')
    return actual


def replace_array(source, name, value):
    """Mutate one source assignment; negative controls never touch repo files."""
    pattern = rf'^([ \t]*{re.escape(name)} 取 )\[.*?\](\.[ \t]*)$'
    changed, count = re.subn(pattern, lambda match: match[1] + repr(value) + match[2],
                             source, flags=re.MULTILINE)
    if count != 1:
        raise AssertionError(f'Negative control expected one {name} assignment')
    return changed


class FlatModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = (ROOT / 'src/main.ru').read_text(encoding='utf-8')
        cls.syntax = (ROOT / 'src/syntax.ru').read_text(encoding='utf-8')
        cls.menu_arrays = read_menu_arrays(cls.main)
        cls.catalog = {}
        for path in sorted((ROOT / 'locales').glob('*.json')):
            entries = json.loads(path.read_text(encoding='utf-8'))
            if set(entries) & set(cls.catalog):
                raise ValueError('Duplicate catalog key across locale files')
            cls.catalog.update(entries)

    def mutated_menu(self, **arrays):
        body = function_body(self.main, '菜单')
        changed = body
        for name, value in arrays.items():
            changed = replace_array(changed, name, value)
        return self.main.replace(body, changed, 1)

    def mutated_palette(self, language, **arrays):
        section = palette_sections(self.syntax)[language]
        changed = section
        for name, value in arrays.items():
            changed = replace_array(changed, name, value)
        return self.syntax.replace(section, changed, 1)

    def test_exact_nine_groups_and_fifty_three_command_mappings(self):
        model = validate_menu(self.main)
        self.assertEqual(len(model), 9)
        commands = [command for _, group in model for command in group]
        self.assertEqual(len(commands), 53)
        self.assertEqual(len({number for number, _ in commands}), 53)
        self.assertEqual(len({key for _, key in commands}), 53)

    def test_all_original_command_ids_keep_their_group_and_order(self):
        original = tuple((group, tuple(number for number, _ in commands if number not in (308, 113, 805)))
                         for group, commands in validate_menu(self.main)
                         if group != 'menu.ui_language')
        self.assertEqual(original, LEGACY_COMMAND_GROUPS)
        self.assertEqual(sum(len(ids) for _, ids in original), 42)

    def test_new_instance_commands_missing_wrong_group_or_duplicate_rejected(self):
        for number, source_group, wrong_group in ((113, 0, 6), (805, 6, 0)):
            for mutation in ('missing', 'wrong-group', 'duplicate'):
                model = [(group, list(commands)) for group, commands in decode_menu(self.menu_arrays)]
                command = next(row for row in model[source_group][1] if row[0] == number)
                if mutation != 'duplicate':
                    model[source_group][1].remove(command)
                if mutation != 'missing':
                    model[wrong_group][1].append(command)
                arrays = {'组键们': [group for group, _ in model],
                          '组量们': [len(commands) for _, commands in model],
                          '号们': [item[0] for _, commands in model for item in commands],
                          '键们': [item[1] for _, commands in model for item in commands]}
                with self.subTest(number=number, mutation=mutation), self.assertRaises(ValueError):
                    validate_menu(self.mutated_menu(**arrays))

    def test_catalog_keys_have_the_reviewed_command_and_group_meanings(self):
        validate_menu_catalog(self.catalog)

    def test_menu_arrays_are_primitive_with_exact_group_boundaries(self):
        self.assertEqual(self.menu_arrays['组量们'], [11, 6, 4, 6, 5, 7, 5, 8, 1])
        for name, kind in MENU_ARRAY_TYPES.items():
            self.assertTrue(all(type(value) is kind for value in self.menu_arrays[name]))

    def test_every_changed_command_id_is_rejected(self):
        for index in range(53):
            ids = self.menu_arrays['号们'].copy()
            ids[index] += 1000
            with self.subTest(index=index), self.assertRaises(ValueError):
                validate_menu(self.mutated_menu(号们=ids))

    def test_every_command_key_misassignment_is_rejected(self):
        for index in range(53):
            keys = self.menu_arrays['键们'].copy()
            following = (index + 1) % len(keys)
            keys[index], keys[following] = keys[following], keys[index]
            with self.subTest(index=index), self.assertRaises(ValueError):
                validate_menu(self.mutated_menu(键们=keys))

    def test_every_removed_command_is_rejected_even_with_consistent_lengths(self):
        for index in range(53):
            arrays = deepcopy(self.menu_arrays)
            del arrays['号们'][index]
            del arrays['键们'][index]
            end = 0
            for group, count in enumerate(arrays['组量们']):
                end += count
                if index < end:
                    arrays['组量们'][group] -= 1
                    break
            with self.subTest(index=index), self.assertRaises(ValueError):
                validate_menu(self.mutated_menu(**arrays))

    def test_every_adjacent_command_reordering_is_rejected(self):
        for index in range(52):
            arrays = deepcopy(self.menu_arrays)
            for name in ('号们', '键们'):
                array = arrays[name]
                array[index], array[index + 1] = array[index + 1], array[index]
            with self.subTest(index=index), self.assertRaises(ValueError):
                validate_menu(self.mutated_menu(**arrays))

    def test_every_adjacent_whole_group_reordering_is_rejected(self):
        for index in range(8):
            model = list(decode_menu(self.menu_arrays))
            model[index], model[index + 1] = model[index + 1], model[index]
            arrays = {
                '组键们': [group for group, _ in model],
                '组量们': [len(commands) for _, commands in model],
                '号们': [number for _, commands in model for number, _ in commands],
                '键们': [key for _, commands in model for _, key in commands],
            }
            with self.subTest(index=index), self.assertRaises(ValueError):
                validate_menu(self.mutated_menu(**arrays))

    def test_every_shifted_group_boundary_is_rejected(self):
        for index in range(8):
            counts = self.menu_arrays['组量们'].copy()
            counts[index] -= 1
            counts[index + 1] += 1
            with self.subTest(index=index), self.assertRaises(ValueError):
                validate_menu(self.mutated_menu(组量们=counts))

    def test_menu_parallel_array_length_mismatches_are_rejected(self):
        for name in MENU_ARRAY_TYPES:
            shortened = self.menu_arrays[name][:-1]
            with self.subTest(array=name), self.assertRaises(ValueError):
                validate_menu(self.mutated_menu(**{name: shortened}))

    def test_nested_or_wrong_type_menu_arrays_are_rejected(self):
        for name in MENU_ARRAY_TYPES:
            for bad in ([self.menu_arrays[name][0]], None, True):
                values = self.menu_arrays[name].copy()
                values[0] = bad
                with self.subTest(array=name, bad=bad), self.assertRaises(ValueError):
                    validate_menu(self.mutated_menu(**{name: values}))

    def test_duplicate_or_missing_menu_array_assignments_are_rejected(self):
        for name in MENU_ARRAY_TYPES:
            body = function_body(self.main, '菜单')
            line = re.search(rf'^[ \t]*{name} 取 .*$', body, re.MULTILINE).group()
            for replacement in ('', line + '\n' + line):
                changed = self.main.replace(body, body.replace(line, replacement), 1)
                with self.subTest(array=name, replacement=replacement), self.assertRaises(ValueError):
                    validate_menu(changed)

    def test_menu_consumer_index_and_loop_changes_are_rejected(self):
        changes = (
            ('循 组键们 其 量 次', '循 组量们 其 量 次'),
            ('循 组量们[组位] 次', '循 组量们[位] 次'),
            ('号 取 号们[位].', '号 取 号们[组位].'),
            ('本地 其 文本 键们[位]', '本地 其 文本 键们[组位]'),
            ('本地 其 文本 组键们[组位]', '本地 其 文本 组键们[位]'),
            ('位 取 位+1.', '位 取 位+2.'),
            ('组位 取 组位+1.', '组位 取 组位+2.'),
        )
        body = function_body(self.main, '菜单')
        for old, new in changes:
            self.assertIn(old, body)
            changed = self.main.replace(body, body.replace(old, new), 1)
            with self.subTest(statement=old), self.assertRaises(ValueError):
                validate_menu(changed)

    def test_catalog_semantic_swaps_are_rejected(self):
        keys = self.menu_arrays['键们']
        for index, key in enumerate(keys):
            data = deepcopy(self.catalog)
            following = keys[(index + 1) % len(keys)]
            data[key], data[following] = data[following], data[key]
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_menu_catalog(data)

    def test_missing_or_unreviewed_menu_catalog_keys_are_rejected(self):
        data = deepcopy(self.catalog)
        del data['command.about']
        with self.assertRaises(ValueError):
            validate_menu_catalog(data)
        data = deepcopy(self.catalog)
        data['command.unreviewed'] = {'en': '&Extra'}
        with self.assertRaises(ValueError):
            validate_menu_catalog(data)

    def test_all_47_original_style_colour_pairs_are_preserved(self):
        palettes = validate_palettes(self.syntax)
        self.assertEqual({language: len(pairs) for language, pairs in palettes.items()},
                         {'cpp': 17, 'json': 11, 'markdown': 19})
        self.assertEqual(sum(map(len, palettes.values())), 47)

    def test_every_changed_style_id_is_rejected(self):
        for language, pairs in EXPECTED_PALETTES.items():
            for index in range(len(pairs)):
                ids = [style for style, _ in pairs]
                ids[index] += 100
                with self.subTest(language=language, index=index), self.assertRaises(ValueError):
                    validate_palettes(self.mutated_palette(language, 色号们=ids))

    def test_every_changed_colour_is_rejected(self):
        for language, pairs in EXPECTED_PALETTES.items():
            for index in range(len(pairs)):
                colors = [color for _, color in pairs]
                colors[index] ^= 1
                with self.subTest(language=language, index=index), self.assertRaises(ValueError):
                    validate_palettes(self.mutated_palette(language, 色值们=colors))

    def test_every_removed_palette_pair_is_rejected(self):
        for language, pairs in EXPECTED_PALETTES.items():
            for index in range(len(pairs)):
                shortened = list(pairs)
                del shortened[index]
                with self.subTest(language=language, index=index), self.assertRaises(ValueError):
                    validate_palettes(self.mutated_palette(
                        language, 色号们=[style for style, _ in shortened],
                        色值们=[color for _, color in shortened]))

    def test_every_adjacent_palette_pair_reordering_is_rejected(self):
        for language, pairs in EXPECTED_PALETTES.items():
            for index in range(len(pairs) - 1):
                reordered = list(pairs)
                reordered[index], reordered[index + 1] = reordered[index + 1], reordered[index]
                with self.subTest(language=language, index=index), self.assertRaises(ValueError):
                    validate_palettes(self.mutated_palette(
                        language, 色号们=[style for style, _ in reordered],
                        色值们=[color for _, color in reordered]))

    def test_palette_parallel_array_length_mismatches_are_rejected(self):
        for language, pairs in EXPECTED_PALETTES.items():
            for name, column in (('色号们', 0), ('色值们', 1)):
                values = [pair[column] for pair in pairs][:-1]
                with self.subTest(language=language, array=name), self.assertRaises(ValueError):
                    validate_palettes(self.mutated_palette(language, **{name: values}))

    def test_nested_or_wrong_type_palette_arrays_are_rejected(self):
        for language, pairs in EXPECTED_PALETTES.items():
            for name, column in (('色号们', 0), ('色值们', 1)):
                for bad in ([pairs[0][column]], '1', True):
                    values = [pair[column] for pair in pairs]
                    values[0] = bad
                    with self.subTest(language=language, array=name, bad=bad), self.assertRaises(ValueError):
                        validate_palettes(self.mutated_palette(language, **{name: values}))

    def test_crosswired_palette_language_branches_are_rejected(self):
        languages = tuple(EXPECTED_PALETTES)
        for index, language in enumerate(languages):
            pairs = EXPECTED_PALETTES[languages[(index + 1) % len(languages)]]
            with self.subTest(language=language), self.assertRaises(ValueError):
                validate_palettes(self.mutated_palette(
                    language, 色号们=[style for style, _ in pairs],
                    色值们=[color for _, color in pairs]))

    def test_palette_consumer_index_and_loop_changes_are_rejected(self):
        changes = (
            ('循 色号们 其 量 次', '循 色值们 其 量 次'),
            ('色号们[位] 色值们[位]', '色值们[位] 色号们[位]'),
            ('色号们[位] 色值们[位]', '色号们[位] 色值们[0]'),
            ('位 取 位+1.', '位 取 位+2.'),
        )
        body = function_body(self.syntax, '_选择')
        for old, new in changes:
            self.assertIn(old, body)
            changed = self.syntax.replace(body, body.replace(old, new), 1)
            with self.subTest(statement=old), self.assertRaises(ValueError):
                validate_palettes(changed)


if __name__ == '__main__':
    unittest.main(verbosity=2)
