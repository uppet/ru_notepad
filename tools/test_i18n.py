#!/usr/bin/env python3
"""Validate every locale catalog and execute production Ru i18n in both backends.

--catalog-only checks catalog contracts and negative controls without claiming a
runtime pass. --ru-root executes the real Python Interpreter and a gcc-built C
executable from the unchanged fixture. Native Windows text measurement, dialogs,
settings persistence and screen-reader behavior require separate Windows tests.
"""
from __future__ import annotations
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import signal
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from ru_cli_diagnostics import prepare_compile_diagnostics, validate_stderr
ASSERTIONS = 289
RU_COMMIT = '85c7821fda35aa79deeaf67b4d430f24ddd7f07f'
RU_TREE = 'a770e367e84d87a0d2fcb6d49ea6f06da2dbe4ba'
LIMIT = 1024 * 1024
LANGUAGES = ('en', 'zh-CN', 'ja', 'ko', 'es', 'ru', 'it')
MENU_GROUPS = {
    'top': tuple('menu.' + key for key in
                 ('file', 'edit', 'search', 'encoding', 'language', 'view', 'settings', 'help', 'ui_language')),
    'file': tuple('command.' + key for key in
                  ('new', 'open', 'open_windows1252', 'open_gbk', 'save', 'save_as',
                   'close_tab', 'previous_tab', 'next_tab', 'exit')),
    'edit': tuple('command.' + key for key in ('undo', 'redo', 'cut', 'copy', 'paste', 'select_all')),
    'search': ('command.find', 'command.replace', 'command.find_next'),
    'encoding': tuple('command.' + key for key in
                      ('save_utf8', 'save_utf8_bom', 'save_utf16le', 'save_utf16be', 'save_windows1252', 'save_gbk')),
    'syntax': tuple('command.language_' + key for key in ('plain', 'cpp', 'json', 'ru', 'markdown')),
    'view': tuple('command.' + key for key in
                  ('toggle_wrap', 'zoom_in', 'zoom_out', 'zoom_reset', 'fold_all', 'unfold_all', 'toggle_markdown_folds')),
    'settings': tuple('command.' + key for key in
                      ('register_association', 'default_apps', 'unregister_association', 'registration_status')),
    'help': ('command.about',),
    'ui-language': tuple('language.' + key for key in ('system', 'en', 'zh_cn', 'ja', 'ko', 'es', 'ru', 'it')),
}
SHORTCUTS = {
    'new': 'Ctrl+N', 'open': 'Ctrl+O', 'save': 'Ctrl+S', 'save_as': 'Ctrl+Shift+S',
    'close_tab': 'Ctrl+W', 'previous_tab': 'Ctrl+Shift+Tab', 'next_tab': 'Ctrl+Tab',
    'undo': 'Ctrl+Z', 'redo': 'Ctrl+Y', 'cut': 'Ctrl+X', 'copy': 'Ctrl+C',
    'paste': 'Ctrl+V', 'select_all': 'Ctrl+A', 'find': 'Ctrl+F',
    'replace': 'Ctrl+H', 'find_next': 'F3', 'zoom_in': 'Ctrl++',
    'zoom_out': 'Ctrl+-', 'zoom_reset': 'Ctrl+0',
    'fold_all': 'Ctrl+Shift+[', 'unfold_all': 'Ctrl+Shift+]',
}


def load_generator():
    spec = importlib.util.spec_from_file_location('ru_notepad_generate_i18n', ROOT / 'tools/generate_i18n.py')
    if spec is None or spec.loader is None:
        raise RuntimeError('Catalog generator is unavailable')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GENERATOR = load_generator()


def mnemonic(label):
    """Parse Win32 ampersands; escaped ampersands are not access keys."""
    result = []
    index = 0
    while index < len(label):
        if label[index] != '&':
            index += 1
            continue
        if index + 1 >= len(label):
            raise ValueError('Dangling menu access-key marker')
        following = label[index + 1]
        if following == '&':
            index += 2
            continue
        if not re.fullmatch('[A-Za-z]', following):
            raise ValueError('Menu access keys must use ASCII letters')
        result.append(following.upper())
        index += 2
    if len(result) != 1:
        raise ValueError('Every menu entry requires exactly one access key')
    return result[0]


def validate_menus(data):
    covered = [key for keys in MENU_GROUPS.values() for key in keys]
    if len(covered) != len(set(covered)):
        raise ValueError('A menu entry belongs to more than one group')
    actual = {key for key in data if key.startswith(('menu.', 'command.', 'language.'))}
    if actual != set(covered):
        raise ValueError('Menu group coverage changed; review new or missing entries')
    for group, keys in MENU_GROUPS.items():
        for language in LANGUAGES:
            used = set()
            for key in keys:
                access = mnemonic(data[key][language].split('\t')[0])
                if access != mnemonic(data[key]['en'].split('\t')[0]):
                    raise ValueError(f'{key}/{language}: access key changed')
                if access in used:
                    raise ValueError(f'{group}/{language}: duplicate access key {access}')
                used.add(access)
    for language in LANGUAGES:
        used = set()
        for key in covered:
            pieces = data[key][language].split('\t')
            expected = SHORTCUTS.get(key.removeprefix('command.')) if key.startswith('command.') else None
            if pieces[1:] != ([] if expected is None else [expected]):
                raise ValueError(f'{key}/{language}: keyboard shortcut contract changed')
            if expected:
                normalized = expected.casefold()
                if normalized in used:
                    raise ValueError('A keyboard shortcut is assigned to more than one command')
                used.add(normalized)


def verify_output(data, count=ASSERTIONS, expected_names=None):
    if not isinstance(data, bytes) or len(data) > LIMIT or not data.endswith(b'\n'):
        raise RuntimeError('I18n policy output is missing or exceeds its fixed bound')
    text = data.decode('utf-8', 'strict').replace('\r\n', '\n')
    lines = text.splitlines()
    if (len(lines) != count + 1 or lines[-1] != f'TOTAL PASS: {count}' or
            any(not re.fullmatch(r'PASS: [^\r\n\x00-\x1f]+', line) for line in lines[:-1]) or
            len(set(lines[:-1])) != count):
        raise RuntimeError('I18n policy exact assertion output mismatch')
    if expected_names is not None and lines[:-1] != ['PASS: ' + name for name in expected_names]:
        raise RuntimeError('I18n catalog assertion identities or order changed')
    return text


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = GENERATOR.catalog(ROOT)

    def test_all_catalogs_have_complete_matching_parameter_contracts(self):
        self.assertEqual(tuple(GENERATOR.LANGUAGES), LANGUAGES)
        self.assertTrue(self.catalog)
        files = sorted((ROOT / 'locales').glob('*.json'))
        expected = set()
        for path in files:
            expected.update(json.loads(path.read_text(encoding='utf-8')))
        self.assertEqual(set(self.catalog), expected)
        for key, translations in self.catalog.items():
            with self.subTest(key=key):
                self.assertRegex(key, r'^[a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+$')
                self.assertEqual(set(translations), set(LANGUAGES))
                fields = Counter(re.findall(r'\{[0-9]\}', translations['en']))
                for language, message in translations.items():
                    self.assertIsInstance(message, str)
                    self.assertTrue(message)
                    self.assertEqual(Counter(re.findall(r'\{[0-9]\}', message)), fields)
                    self.assertIsNone(re.search('[\x00-\x08\x0b-\x1f]', message))
                    self.assertEqual(message.encode('utf-8').decode('utf-8'), message)

    def test_generated_catalog_matches_all_sources(self):
        expected = GENERATOR.render(self.catalog)
        self.assertEqual((ROOT / 'src/i18n_catalog.ru').read_text(encoding='utf-8'), expected,
                         'Generated catalog is stale; run tools/generate_i18n.py')
        self.assertEqual(expected, GENERATOR.render(dict(reversed(list(self.catalog.items())))))

    def test_menu_keys_shortcuts_and_collisions(self):
        validate_menus(self.catalog)

    def test_menu_collision_negative_control(self):
        data = deepcopy(self.catalog)
        data['menu.settings']['en'] = '&Settings'
        with self.assertRaises(ValueError):
            validate_menus(data)

    def test_translated_access_key_negative_control(self):
        data = deepcopy(self.catalog)
        data['menu.file']['ja'] = 'ファイル(&Q)'
        with self.assertRaises(ValueError):
            validate_menus(data)

    def test_shortcut_reassignment_negative_control(self):
        data = deepcopy(self.catalog)
        data['command.open']['it'] = 'Apri(&O)\tCtrl+N'
        with self.assertRaises(ValueError):
            validate_menus(data)

    def test_new_menu_requires_group_review(self):
        data = deepcopy(self.catalog)
        data['command.unreviewed'] = dict.fromkeys(LANGUAGES, '&Extra')
        with self.assertRaises(ValueError):
            validate_menus(data)

    def test_access_key_parser_negative_controls(self):
        self.assertEqual(mnemonic('Save && &Close'), 'C')
        for label in ('File', 'File&', '&文件', '&File &Open', '&&File'):
            with self.subTest(label=label), self.assertRaises(ValueError):
                mnemonic(label)

    def test_autonyms_are_stable_and_ui_strings_are_unicode(self):
        for key in ('en', 'zh_cn', 'ja', 'ko', 'es', 'ru', 'it'):
            values = self.catalog['language.' + key]
            self.assertEqual(len(set(values.values())), 1)
        values = self.catalog['menu.file']
        self.assertGreater(len(set(map(len, values.values()))), 1)
        for language in ('zh-CN', 'ja', 'ko', 'ru'):
            self.assertTrue(any(ord(char) > 127 for char in values[language]))
        for key, required in {
            'command.language_cpp': ('C / C++',), 'command.language_json': ('JSON',),
            'command.language_ru': ('Ru / 如言',), 'command.language_markdown': ('Markdown',),
            'command.save_utf8': ('UTF-8',), 'command.save_utf8_bom': ('UTF-8', 'BOM'),
            'command.save_utf16le': ('UTF-16 LE',), 'command.save_utf16be': ('UTF-16 BE',),
            'command.save_windows1252': ('Windows-1252',), 'command.save_gbk': ('GBK (CP936)',),
        }.items():
            for value in self.catalog[key].values():
                for token in required:
                    self.assertIn(token, value.replace('&', ''))

    def test_exact_catalog_oracle_is_independent_and_complete(self):
        data = read_catalog_oracle()
        self.assertEqual(data, self.catalog)
        source = exact_catalog_source(data)
        self.assertIn('键们 取 ' + json.dumps(sorted(data), ensure_ascii=False) + '.', source)
        values = [data[key][language] for language in LANGUAGES for key in sorted(data)]
        self.assertIn('期望们 取 ' + json.dumps(values, ensure_ascii=False) + '.', source)
        self.assertEqual(len(values), len(data) * len(LANGUAGES))
        self.assertEqual(source.count('确认 ((本地 其 文本 '), 1)
        self.assertEqual(source.count('本地 其 设置 '), 1)
        self.assertIn(json.dumps(self.catalog['about.body']['ja'], ensure_ascii=False), source)
        self.assertIn('"dialog.unsaved"', source)

    def test_filter_labels_cannot_introduce_native_field_separators(self):
        for key in ('file.filter.all', 'file.filter.text', 'file.filter.ru', 'file.filter.markdown'):
            for text in self.catalog[key].values():
                self.assertNotIn('|', text)
                self.assertNotIn('\0', text)

    def test_generator_rejects_native_filter_separators(self):
        for key in ('file.filter.all', 'file.filter.text', 'file.filter.ru', 'file.filter.markdown'):
            data = {key: dict.fromkeys(LANGUAGES, 'Text files')}
            data[key]['ja'] = 'Text|*.exe'
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.load_sample(data)

    def sample(self):
        return {'test.value': {language: 'Value {0}' for language in LANGUAGES}}

    def load_sample(self, data, extra=None):
        with tempfile.TemporaryDirectory(prefix='ru-i18n-catalog-control-') as temporary:
            root = Path(temporary)
            (root / 'locales').mkdir()
            (root / 'locales/a.json').write_text(json.dumps(data), encoding='utf-8')
            if extra is not None:
                (root / 'locales/b.json').write_text(json.dumps(extra), encoding='utf-8')
            return GENERATOR.catalog(root)

    def test_generator_accepts_valid_complete_catalog(self):
        self.assertEqual(self.load_sample(self.sample()), self.sample())
        for value in ('No fields', '{0}', '{9}', '{1} / {0}', '{0} {0}', 'Unicode 中文😀 {0}'):
            data = {'test.value': dict.fromkeys(LANGUAGES, value)}
            with self.subTest(value=value):
                self.assertEqual(self.load_sample(data), data)

    def test_generator_rejects_missing_extra_and_empty_translations(self):
        for mode in ('missing', 'extra', 'empty', 'number', 'null', 'NUL', 'CR'):
            data = self.sample()
            if mode == 'missing':
                del data['test.value']['ja']
            elif mode == 'extra':
                data['test.value']['fr'] = 'Value {0}'
            else:
                data['test.value']['ja'] = {'empty': '', 'number': 3, 'null': None,
                                          'NUL': 'Value {0}\0', 'CR': 'Value {0}\r'}[mode]
            with self.subTest(mode=mode), self.assertRaises((ValueError, TypeError)):
                self.load_sample(data)

    def test_generator_rejects_parameter_mismatch_and_unsupported_formats(self):
        for value in ('Value', 'Value {1}', 'Value {0} {0}', 'Value {10}', 'Value {name}',
                      'Value {0!r}', 'Value {0:>4}', 'Value {', 'Value }',
                      'Value {00}', 'Value {٠}', 'Value {０}', 'Value {{0}}',
                      'Value {{{0}}}', 'Value {}', 'Value {{', 'Value }}',
                      'Value {{0}', 'Value {0}}', 'Value {-1}', 'Value { 0}'):
            data = self.sample()
            data['test.value']['it'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.load_sample(data)
        # Reject unsupported syntax even when all languages contain the same
        # invalid token; a mere parameter-count mismatch cannot pass this test.
        for value in ('{00}', '{٠}', '{０}', '{{0}}', '{{{0}}}', '{}', '{{', '}}',
                      '{{0}', '{0}}', '{10}', '{x}', '{0!r}', '{0:>4}', '{', '}'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.load_sample({'test.value': dict.fromkeys(LANGUAGES, value)})

    def test_generator_rejects_unstable_keys_and_cross_file_duplicates(self):
        for key in ('test', 'test.bad-key', 'Test.value', 'test..value', 'test.value '):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.load_sample({key: self.sample()['test.value']})
        with self.assertRaises(ValueError):
            self.load_sample(self.sample(), self.sample())

    def test_generator_rejects_duplicate_json_fields(self):
        for pairs in ([('test.value', {}), ('test.value', {})], [('en', 'a'), ('en', 'b')]):
            with self.assertRaises(ValueError):
                GENERATOR.pairs_unique(pairs)

    def test_quote_preserves_unicode_and_escapes_source_delimiters(self):
        self.assertEqual(GENERATOR.quote("a'\\b\n\t中文😀"), "'a\\'\\\\b\\n\\t中文😀'")

    def test_exact_backend_output_positive_and_negative_controls(self):
        valid = b'PASS: synthetic\nTOTAL PASS: 1\n'
        self.assertEqual(verify_output(valid, 1), valid.decode())
        self.assertEqual(verify_output(valid.replace(b'\n', b'\r\n'), 1), valid.decode())
        self.assertEqual(verify_output(valid, 1, ['synthetic']), valid.decode())
        with self.assertRaises(RuntimeError):
            verify_output(valid, 1, ['wrong identity'])
        for invalid in (b'', valid + valid, valid.replace(b'1', b'2'), valid[:-1],
                        b'SKIP: synthetic\nTOTAL PASS: 1\n', b'PASS: \x00\nTOTAL PASS: 1\n',
                        b'PASS: \xff\nTOTAL PASS: 1\n', b'x' * (LIMIT + 1),
                        b'PASS: duplicate\nPASS: duplicate\nTOTAL PASS: 2\n'):
            with self.subTest(invalid=invalid[:40]), self.assertRaises((RuntimeError, UnicodeError)):
                verify_output(invalid, 1 if b'duplicate' not in invalid else 2)


def source_snapshot():
    pending = [ROOT / 'tests/i18n_policy.ru']
    snapshot = {}
    while pending:
        path = pending.pop()
        if path.is_symlink() or not path.is_file() or ROOT not in path.resolve().parents:
            raise RuntimeError('I18n source is missing, linked or outside its checkout')
        relative = path.resolve().relative_to(ROOT).as_posix()
        if relative in snapshot:
            continue
        data = path.read_bytes()
        snapshot[relative] = hashlib.sha256(data).hexdigest()
        for _, imported in re.findall(r'''外言\s+(['"])(.*?)\1''', data.decode('utf-8')):
            if imported.startswith('如:'):
                raise RuntimeError('Pure i18n policy must not import native capability')
            pending.append(path.parent / imported)
    for path in [Path(__file__), ROOT / 'tools/generate_i18n.py',
                 ROOT / 'tools/ru_cli_diagnostics.py', *sorted((ROOT / 'locales').glob('*.json'))]:
        snapshot[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return snapshot


class CleanupError(RuntimeError):
    """The owned process tree could still be using its private fixture."""


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(65536), b''):
            digest.update(chunk)
    return digest.hexdigest()


def stop_process_tree(process):
    if os.name == 'nt':
        result = subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
        if result.returncode:
            raise CleanupError('I18n backend process-tree cleanup failed')
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    process.wait(timeout=5)


def checked_run(command, directory, label, timeout, records=None, compile_diagnostics=None):
    out, err = directory / (label + '.stdout'), directory / (label + '.stderr')
    with out.open('xb') as stdout, err.open('xb') as stderr:
        options = {'creationflags': 0x00000200} if os.name == 'nt' else {'start_new_session': True}
        environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        started = time.monotonic()
        record = {'stage': label, 'timeout_seconds': timeout,
                  'command_sha256': hashlib.sha256(json.dumps(list(map(str, command))).encode('utf-8')).hexdigest()}
        if records is not None:
            records.append(record)
        process = subprocess.Popen(list(map(str, command)), stdout=stdout, stderr=stderr, env=environment, **options)
        try:
            (directory / (label + '.command.json')).write_text(
                json.dumps(list(map(str, command))) + '\n', encoding='utf-8', newline='\n')
            while True:
                if out.stat().st_size > LIMIT or err.stat().st_size > LIMIT:
                    raise RuntimeError('I18n backend output exceeded its fixed bound')
                remaining = timeout - (time.monotonic() - started)
                if remaining <= 0:
                    raise RuntimeError('I18n backend exceeded its execution deadline')
                try:
                    process.wait(timeout=min(0.05, remaining))
                    break
                except subprocess.TimeoutExpired:
                    pass
            if (time.monotonic() - started > timeout or process.returncode or
                    err.stat().st_size > LIMIT or out.stat().st_size > LIMIT):
                raise RuntimeError(f'I18n backend failed: {label}; exit={process.returncode}; '
                                   'raw diagnostic streams retained privately')
            validate_stderr(command, process.returncode, err.read_bytes(), compile_diagnostics)
        except BaseException:
            if os.name != 'nt' or process.poll() is None:
                try:
                    stop_process_tree(process)
                except Exception:
                    raise CleanupError('I18n backend process-tree cleanup failed') from None
            raise
        finally:
            active_error = sys.exc_info()[0] is not None
            try:
                record.update({'exit_code': process.returncode,
                               'elapsed_seconds': round(time.monotonic() - started, 3),
                               'stdout_bytes': out.stat().st_size, 'stderr_bytes': err.stat().st_size,
                               'stdout_sha256': file_sha256(out), 'stderr_sha256': file_sha256(err)})
            except Exception:
                if not active_error:
                    raise
    return out.read_bytes()


def policy_assertion_names():
    """Reviewed fixed identities, independent of backend output and Ru parsing."""
    names = ['initial language is English', 'exactly seven supported languages']
    for language in LANGUAGES:
        names.extend(prefix + language for prefix in (
            'supported language ', 'stable language slot ', 'switch return ',
            'active language ', 'Unicode menu ', 'localized parameter ',
            'missing production key ', 'autonym unchanged '))
    for language in reversed(LANGUAGES):
        names.extend(prefix + language for prefix in ('repeated selection ', 'reverse switch refresh '))
    for index in range(10):
        names.extend(prefix + str(index) for prefix in (
            'unknown language rejected ', 'unknown language fallback ', 'unknown language uses English '))
    for langid in (1033, 2057, 3081, 4105, 5129, 9, 2052, 1028, 3076, 4100, 5124, 4,
                   1041, 17, 1042, 18, 1034, 2058, 3082, 4106, 21514, 22538, 10,
                   1049, 2073, 25, 1040, 2064, 16, 1031, 1036, 1046, 0, 65535):
        names.append('system LANGID ' + str(langid))
    for language in LANGUAGES:
        names.extend(prefix + language for prefix in (
            'synthetic Unicode translation ', 'missing slot English fallback ', 'empty slot English fallback '))
    names.extend(('available translation does not require English', 'empty English is visible',
                  'missing translation and English are visible', 'empty catalog entry is visible',
                  'all empty translations are visible', 'direct lookup unknown language uses English',
                  'synthetic absent key is visible', 'empty absent key is visible'))
    names.extend('single-pass format ' + str(index) for index in range(26))
    names.extend(('production formatting preserves filename braces', 'test restores English'))
    for width in (480, 640, 900, 1600):
        for group in range(3):
            names.extend(prefix + f'{width}/{group}' for prefix in (
                'minimum input width ', 'integer input width ', 'inputs remain in viewport ',
                'all controls are placed ', 'buttons remain in viewport ', 'buttons never overlap ',
                'buttons never cover inputs ', 'layout height contains controls '))
    if len(names) != ASSERTIONS or len(set(names)) != ASSERTIONS:
        raise RuntimeError('I18n policy assertion oracle requires review')
    return names


def compiler_snapshot(compiler):
    def git(*args):
        return subprocess.check_output(['git', '-C', str(compiler), *args],
                                       stderr=subprocess.PIPE, timeout=15).decode('utf-8').strip()

    result = {'commit': git('rev-parse', 'HEAD'), 'tree': git('rev-parse', 'HEAD^{tree}'),
              'status': git('status', '--porcelain=v1', '--untracked-files=all')}
    if result != {'commit': RU_COMMIT, 'tree': RU_TREE, 'status': ''}:
        raise RuntimeError('I18n verification requires the pinned, clean Ru compiler checkout')
    return result


def read_catalog_oracle():
    # Parse source JSON independently of both production generator encoders and
    # generated Ru. CatalogTests separately verifies their complete contracts.
    result = {}
    for path in sorted((ROOT / 'locales').glob('*.json')):
        result.update(json.loads(path.read_text(encoding='utf-8')))
    return result


def exact_catalog_source(data):
    # Independently emit JSON double-quoted literals, not the production Ru
    # generator's single-quote encoder. No expected text comes from Ru output.
    def literal(value):
        return json.dumps(value, ensure_ascii=False)

    lines = ["# Test-only exact catalog oracle generated directly from reviewed JSON.",
             "本地 取 外言 " + literal(str(ROOT / 'src/i18n.ru')) + ".",
             "次数 取 [0].",
             "作 确认 条件 为 事实, 名 为 句:",
             "    若 非 条件 则 卒 ('FAIL: '+名). 然",
             "    次数[0] 取 次数[0]+1.",
             "    显 'PASS: '+名.", "为"]
    # Primitive arrays keep the oracle's generated C small enough for the pinned
    # compiler's ordinary 120-second limit. Every expected string still comes
    # directly from JSON, and the host validates every emitted language/key ID.
    lines.extend(['语言们 取 ' + literal(LANGUAGES) + '.',
                  '键们 取 ' + literal(sorted(data)) + '.',
                  '期望们 取 ' + literal([data[key][language] for language in LANGUAGES
                                         for key in sorted(data)]) + '.',
                  '语位 取 0.', '循 语言们 其 量 次',
                  '    语言 取 语言们[语位].', '    本地 其 设置 语言.',
                  '    键位 取 0.', '    循 键们 其 量 次',
                  '        键 取 键们[键位].',
                  '        期望 取 期望们[语位*(键们 其 量)+键位].',
                  '        确认 ((本地 其 文本 键) == 期望) (语言+"/"+键).',
                  '        键位 取 键位+1.', '    环',
                  '    语位 取 语位+1.', '环'])
    lines.append("显 'TOTAL PASS: '+(次数[0] 为 句).")
    return '\n'.join(lines) + '\n'


def run_backends(ru_root, cc, output):
    compiler = ru_root.resolve()
    if not (compiler / 'ru').is_file() or not (compiler / 'rulang/interpreter.py').is_file():
        raise RuntimeError('--ru-root does not contain the actual Ru compiler and interpreter')
    compiler_before = compiler_snapshot(compiler)
    before = source_snapshot()
    data = read_catalog_oracle()
    exact_count = len(data) * len(LANGUAGES)
    report = {'schema': 2, 'passed': False, 'source_sha256': before,
              'compiler': compiler_before, 'platform': platform.platform(),
              'python': sys.version, 'native_windows_ui_executed': False,
              'catalog_keys': len(data), 'catalog_languages': list(LANGUAGES),
              'catalog_exact_assertions': exact_count, 'cases': [], 'commands': []}
    if output is not None:
        output.mkdir(parents=True, exist_ok=False)
    try:
        private = Path(tempfile.mkdtemp(prefix='ru-i18n-backends-')).resolve()
        cleanup_allowed = True
        try:
            # Raw compiler text and absolute paths are retained privately. Only
            # exact validated runtime assertions and a closed receipt are public.
            logs = ROOT / 'build/i18n-policy-private' / private.name
            logs.mkdir(parents=True, exist_ok=False)
            exact_source = private / 'catalog_exact.ru'
            exact_source.write_text(exact_catalog_source(data), encoding='utf-8', newline='\n')
            report['catalog_exact_source_sha256'] = hashlib.sha256(exact_source.read_bytes()).hexdigest()
            (logs / 'catalog_exact.ru').write_bytes(exact_source.read_bytes())
            version = checked_run([cc, '--version'], logs, 'cc-version', 15, report['commands'])
            version.decode('utf-8', 'strict')
            report['cc_version_sha256'] = hashlib.sha256(version).hexdigest()
            code = ('import sys; from pathlib import Path; sys.dont_write_bytecode=True; '
                    'sys.path.insert(0,sys.argv[1]); '
                    'from rulang.frontend import parse; from rulang.interpreter import Interpreter; '
                    'p=Path(sys.argv[2]); Interpreter().execute(parse(p.read_text(encoding="utf-8")),source_path=p)')
            cases = [('i18n_policy', ROOT / 'tests/i18n_policy.ru', ASSERTIONS),
                     ('catalog_exact', exact_source, exact_count)]
            report['generated_c_sha256'] = {}
            for name, source, count in cases:
                expected_names = ([language + '/' + key for language in LANGUAGES for key in sorted(data)]
                                  if name == 'catalog_exact' else policy_assertion_names())
                interpreted = checked_run([sys.executable, '-I', '-c', code, compiler, source],
                                          logs, name + '-interpreter', 120, report['commands'])
                interpreted_text = verify_output(interpreted, count, expected_names)
                executable = private / (name + ('.exe' if os.name == 'nt' else ''))
                generated_c = private / (name + '.c')
                build_command = [sys.executable, compiler / 'ru', 'build', '--cc', cc, source,
                                 '--emit-c', generated_c, '-o', executable]
                diagnostics = prepare_compile_diagnostics(build_command, compiler, source)
                checked_run(build_command, logs, name + '-build', 180,
                            report['commands'], compile_diagnostics=diagnostics)
                compiled_text = verify_output(checked_run([executable], logs, name + '-host-c', 30,
                                                          report['commands']), count, expected_names)
                if interpreted_text != compiled_text:
                    raise RuntimeError(f'{name}: Interpreter and host-C assertion results differ')
                if (source_snapshot() != before or
                        file_sha256(exact_source) != report['catalog_exact_source_sha256']):
                    raise RuntimeError('I18n sources changed during backend verification')
                for backend, text in [('interpreter', interpreted_text), ('host-c', compiled_text)]:
                    report['cases'].append({'fixture': name, 'backend': backend, 'assertions': count})
                    if output is not None:
                        (output / (name + '-' + backend + '.log')).write_text(text, encoding='utf-8', newline='\n')
                report['generated_c_sha256'][name] = hashlib.sha256(generated_c.read_bytes()).hexdigest()
            if compiler_snapshot(compiler) != compiler_before:
                raise RuntimeError('Ru compiler checkout changed during backend verification')
            if source_snapshot() != before:
                raise RuntimeError('I18n sources changed during backend verification')
            report['passed'] = True
        except CleanupError:
            cleanup_allowed = False
            raise
        finally:
            if cleanup_allowed:
                shutil.rmtree(private)
    except BaseException:
        report['passed'] = False
        report['error'] = 'i18n_backend_failed'
        raise
    finally:
        if output is not None:
            (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(f'I18N_PORTABLE_PASS policy={ASSERTIONS}x2 exact_catalog={exact_count}x2 catalog_keys={len(data)}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ru-root', type=Path)
    parser.add_argument('--cc', default='gcc')
    parser.add_argument('--catalog-only', action='store_true')
    parser.add_argument('--output', type=Path, help='New directory for verified logs and source-hash receipt')
    args = parser.parse_args()
    if args.catalog_only and args.ru_root is not None:
        parser.error('choose either --catalog-only or --ru-root')
    if not args.catalog_only and args.ru_root is None:
        parser.error('--ru-root is required unless --catalog-only is selected')
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CatalogTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        return 1
    if args.catalog_only:
        print(f'I18N_CATALOG_PASS keys={len(GENERATOR.catalog(ROOT))} languages=7; runtime not executed')
    else:
        run_backends(args.ru_root, args.cc, args.output)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, OSError, UnicodeError, subprocess.SubprocessError):
        print('I18N_FAILED; raw diagnostics retained privately', file=sys.stderr)
        raise SystemExit(1)
