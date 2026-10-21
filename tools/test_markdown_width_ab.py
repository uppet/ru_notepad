#!/usr/bin/env python3
"""Synthetic A/B controls. No desktop, process spawn or raw public output."""
import copy, json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import run_markdown_width_ab as a
import run_markdown_edit_profile as edit
import run_markdown_phase_profile as base
import run_markdown_owned_profile as owned
import package
import test_markdown_edit_profile as fixtures
import test_markdown_phase_profile as old
import windows_ci as ci

ROOT=Path(__file__).resolve().parents[1]
P=SimpleNamespace(edit=edit,base=base,owned=owned,package=package)
COMMIT='b'*40

class PublicControls(unittest.TestCase):
    def test_blank_roundtrip_bounded(self):
        x=a.blank(P,COMMIT);self.assertLess(len(a.validate(x,P)),a.LIMIT)
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'public.json';a.save(p,x,P);self.assertEqual(a.read(p),x)
            a.save(p,x,P);self.assertFalse(p.with_suffix('.pending').exists())
    def test_injection_types_and_constants(self):
        mutations=[
            lambda x:x.update(raw='private'),lambda x:x.update(passed=True),
            lambda x:x.update(candidate_commit='private'),lambda x:x.update(stage_deadline_seconds=31),
            lambda x:x.update(process_deadline_seconds=121),lambda x:x.update(order=[1]*8),
            lambda x:x.update(pair_indices=[[0,1]]*4),lambda x:x.update(failure_code=8),
            lambda x:x['release_attempted'].__setitem__(1,1),
            lambda x:x['pair_ratios'][0].__setitem__(0,float('nan')),
            lambda x:x['release_results'][0].update(raw_path='private'),
            lambda x:x['release_verified'].__setitem__(0,1)]
        for change in mutations:
            with self.subTest(change=change):
                x=a.blank(P,COMMIT);change(x)
                with self.assertRaises(Exception):a.validate(x,P)
    def test_partial_ratios_and_wrong_arm_receipt(self):
        x=a.blank(P,COMMIT);x['prepared']=[1,1];x['native_origin_sha256']='e'*64;x['runner_receipt_sha256']=['a'*64,'c'*64]
        for i in (0,1):
            summary=fixtures.summary();summary['runs']=summary['runs'][:1];summary['passed']=False
            summary['receipt_sha256']=x['runner_receipt_sha256'][i]
            if i==1:
                for s in summary['runs'][0]['stages']:s['wall_ms']*=0.9
            x['release_results'][i]=edit.public_projection(summary,'d'*64,ci)
            x['release_attempted'][i]=x['release_verified'][i]=1
        a.recompute(x);a.validate(x,P)
        self.assertEqual(x['pair_complete'],[1,0,0,0]);self.assertEqual(x['diagnostic_complete'],0)
        self.assertTrue(all(abs(n-.9)<1e-9 for n in x['pair_ratios'][0]))
        x['release_results'][1]['receipt_sha256']='a'*64
        with self.assertRaises(Exception):a.validate(x,P)
    def test_duplicate_json_and_path_boundaries(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p=root/'a';p.write_text('{"a":1,"a":2}')
            with self.assertRaises(Exception):a.read(p)
            with self.assertRaises(Exception):a.under(root,'../outside')
            q=root/'hard';os.link(p,q)
            with self.assertRaises(Exception):a.plain(q)
            q.unlink()
            try:q.symlink_to(p)
            except OSError:return
            with self.assertRaises(Exception):a.plain(q)
    def test_original_thresholds_and_sequence(self):
        x=a.blank(P,COMMIT)
        self.assertEqual(x['stage_deadline_seconds'],30);self.assertEqual(x['process_deadline_seconds'],120)
        self.assertEqual(a.ORDER,(0,1,1,0,0,1,1,0))
        self.assertEqual(a.PAIRS,((0,1),(3,2),(4,5),(7,6)))

class CoordinatorControls(unittest.TestCase):
    def run_case(self,*,late=False,fail_at=None,check_fail_at=None,pair_incomplete=False):
        with tempfile.TemporaryDirectory() as t:
            top=Path(t);roots=(top/'baseline',top/'candidate');output=top/'public';output.mkdir()
            hashes=[]
            for n,r in enumerate(roots):
                private=r/'build/markdown-width-ab-private';private.mkdir(parents=True)
                (private/'runner-receipt.json').write_text(str(n));hashes.append(a.sha(private/'runner-receipt.json'))
                (r/'native').mkdir();(r/'native/markdown_edit_profile.h').write_text('header')
            calls=[];checks=[0]
            def verify(*args):
                checks[0]+=1
                if checks[0]==check_fail_at:raise ValueError('private-path')
                return 'f'*64
            def arm(root,*args):
                n=roots.index(root)
                return ({'build_receipt_sha256':str(n+1)*64,'runner_receipt_sha256':hashes[n]},
                        {'runtime_sha256':{'release':{k:'d'*64 for k in base.RUNTIME_NAMES}}})
            def release(root,private,out,p,c):
                i=len(calls);calls.append(('release',roots.index(root)))
                s=fixtures.summary(late);s['receipt_sha256']=hashes[roots.index(root)];s['runs']=s['runs'][:1];s['passed']=False
                raw=s['runs'][0]
                if i==fail_at:raw.update(diagnostic_complete=False,passed=False,cleanup_unconfirmed=True)
                return raw,edit.public_projection(s,'d'*64,ci)
            def pair(receipt,root,release,profile,out,*,ci,run):
                n=roots.index(root);rows=[]
                for variant in ('release','profile'):
                    rows.append(run(variant,n))
                return {'passed':all(r['passed'] for r in rows),'runs':rows,'receipt_sha256':hashes[n]}
            def owned_run(variant,n):
                calls.append((variant,n));raw=fixtures.summary(late)['runs'][0 if variant=='release' else 1]
                if pair_incomplete and variant=='release':
                    raw.update(diagnostic_complete=False,passed=False,drop_cleanup_failed=True)
                return raw
            with patch.object(a,'load_protocol',return_value=P),patch.object(a,'verify_roots',side_effect=verify),patch.object(a,'verify_arm',side_effect=arm),patch.object(a,'verify_native_origin',return_value='f'*64),patch.object(base,'load_ci',return_value=ci),patch.object(edit,'run_pair',side_effect=pair),patch.object(edit,'run_owned',side_effect=owned_run):
                value=a.measure(*roots,COMMIT,top/'compiler',top/'cc',output,release_runner=release)
            saved=a.read(output/'markdown-width-ab.json');self.assertEqual(saved,value);a.validate(value,P)
            return value,calls,checks[0]
    def test_all_twelve_processes_and_complete_pairs(self):
        value,calls,checks=self.run_case()
        self.assertEqual([n for _,n in calls[:8]],list(a.ORDER));self.assertEqual(len(calls),12)
        self.assertEqual(value['pair_complete'],[1]*4);self.assertEqual(value['passed'],1)
        self.assertGreaterEqual(checks,26)
    def test_late_keeps_failed_gate_not_failed_diagnostic(self):
        value,calls,_=self.run_case(late=True)
        self.assertEqual(len(calls),12)
        self.assertEqual((value['diagnostic_complete'],value['passed'],value['product_gate_failed'],value['failure_code']),(1,0,1,2))
    def test_unconfirmed_stops_no_fabricated_pair(self):
        value,calls,_=self.run_case(fail_at=2)
        self.assertEqual(len(calls),3);self.assertEqual(value['pair_complete'],[1,0,0,0])
        self.assertEqual(value['release_verified'],[1,1,0,0,0,0,0,0]);self.assertEqual(value['failure_code'],3)
    def test_post_release_receipt_failure_retains_observation(self):
        value,calls,_=self.run_case(check_fail_at=3)
        self.assertEqual(len(calls),1);self.assertEqual(value['release_results'][0]['runs'][0]['executed'],1)
        self.assertEqual(value['release_verified'],[0]*8);self.assertEqual(value['failure_code'],4)
    def test_pair_partial_failure_blocks_profile_retains_release(self):
        value,calls,_=self.run_case(pair_incomplete=True)
        self.assertEqual(len(calls),9);self.assertEqual(value['profile_results'][0]['runs'][0]['executed'],1)
        self.assertEqual(value['profile_results'][0]['runs'][1]['executed'],0);self.assertEqual(value['profile_verified'],[0,0])
    def test_pair_receipt_changed_before_profile_retains_release(self):
        # initial1 + 8*(pre/post)=17; pair pre18, release pre19/post20.
        value,calls,_=self.run_case(check_fail_at=20)
        self.assertEqual(len(calls),9);self.assertEqual(value['profile_results'][0]['runs'][0]['executed'],1)
        self.assertEqual(value['profile_results'][0]['runs'][1]['executed'],0);self.assertEqual(value['failure_code'],4)

class WorkflowControls(unittest.TestCase):
    def test_workflow_contract_and_public_only_upload(self):
        text=(ROOT/'.github/workflows/markdown-width-ab.yml').read_text()
        self.assertIn('branches: [mi-perf-prototype]',text)
        self.assertIn('timeout-minutes: 75',text)
        self.assertEqual(text.count('persist-credentials: false'),3)
        self.assertIn('ref: '+a.BASELINE,text);self.assertIn('ref: '+a.COMPILER,text)
        self.assertIn('cancel-in-progress: false',text)
        self.assertEqual(text.count('-Stage controls'),2)
        self.assertEqual(text.count('-Stage dependencies'),2)
        self.assertEqual(text.count('-Stage application'),2)
        self.assertEqual(text.count('uses: actions/upload-artifact@'),1)
        self.assertIn('path: candidate/build/markdown-width-ab-public/markdown-width-ab.json',text)
        self.assertIn('if: always()',text);self.assertIn('cache: false',text)
        self.assertLess(text.index('sync-dlls'),text.index('name: Check and build candidate application'))
        self.assertLess(text.index('check-built --baseline'),text.index('prepare --arm 0'))
        self.assertLess(text.index('prepare --arm 0'),text.index('prepare --arm 1'))
        self.assertLess(text.index('prepare --arm 1'),text.index('run_markdown_width_ab.py measure'))
    def test_safe_failure_trace_no_messages_or_paths(self):
        import contextlib,io
        output=io.StringIO()
        with contextlib.redirect_stdout(output):
            try:raise ValueError('PRIVATE path or GUI text')
            except Exception as error:a.failure_trace(error)
        self.assertEqual(output.getvalue(),'WIDTH_AB_EXCEPTION_KIND=1\n')

class SourceControls(unittest.TestCase):
    def test_inventory_rejects_unrelated_diff_missing_and_nested(self):
        with tempfile.TemporaryDirectory() as t:
            top=Path(t);roots=[top/x for x in ('a','b','cc')]
            for p in roots:p.mkdir()
            av={a.POLICY:a.POLICIES[0],'src/main.ru':'d'*64}
            bv=dict(av);bv[a.POLICY]=a.POLICIES[1];bv.update({p:'f'*64 for p in a.ADDED})
            def run(b):
                with patch.object(a,'checkout',side_effect=[av,b]),patch.object(a,'verify_compiler'):
                    return a.verify_roots(*roots[:2],COMMIT,roots[2])
            self.assertEqual(len(run(bv)),64)
            for b in (dict(bv,**{'src/main.ru':'e'*64}),{k:v for k,v in bv.items() if k!='src/main.ru'},dict(bv,unapproved='c'*64)):
                with self.assertRaises(Exception):run(b)
            with self.assertRaises(Exception):a.verify_roots(roots[0],roots[0],COMMIT,roots[2])
    def test_real_two_root_loader_fixture_locale_and_source_receipt(self):
        # Real private loader + adapter construction, no mocked ci.ROOT.
        with tempfile.TemporaryDirectory() as t:
            candidate=Path(t).resolve()/'candidate';candidate.mkdir()
            shutil.copytree(ROOT/'tools',candidate/'tools',ignore=shutil.ignore_patterns('__pycache__'))
            shutil.copytree(ROOT/'locales',candidate/'locales')
            previous=sys.modules.pop('package',None)
            try:canonical=base.load_ci(candidate)
            finally:
                sys.modules.pop('package',None)
                if previous is not None:sys.modules['package']=previous
            self.assertEqual(canonical.ROOT,candidate)
            self.assertEqual(base.fixture_bytes(canonical),base.fixture_bytes(ci))
            from markdown_edit_observers import adapted as adapt
            adapted=adapt(canonical)
            self.assertIsNotNone(adapted)
            f=old.Controls();f.setUp()
            try:
                receipt,root,release,profile,_=f.make_manifest();calls=[]
                def run(variant,*args,**kwargs):
                    calls.append(variant);return dict(variant=variant,passed=False,cleanup_unconfirmed=True)
                result=edit.run_pair(receipt,root,release,profile,f.base/'pair',ci=canonical,run=run)
                self.assertEqual(calls,['release']);self.assertEqual(len(result['runs']),1)
                (root/'src/main.ru').write_text('changed')
                with self.assertRaises(Exception):edit.run_pair(receipt,root,release,profile,f.base/'pair2',ci=canonical,run=run)
                self.assertEqual(calls,['release'])
            finally:f.tearDown()


"""Synthetic on-disk full-receipt controls. No compilation or GUI processes."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import run_markdown_width_ab as a
import package as receipt_package
import run_markdown_phase_profile as receipt_base


class FullReceiptFixture:
    VERSION = b'synthetic compiler version 1\n'
    def __init__(self):
        self.temp = tempfile.TemporaryDirectory(prefix='width-full-receipt-')
        self.home = Path(self.temp.name).resolve()
        self.root = self.home / 'application'
        self.binary = self.home / 'binary'
        self.binary.mkdir()
        self.cc = self.home / 'cc-fixture'
        self.cc.write_bytes(b'synthetic compiler identity; never executed')
        self.p = SimpleNamespace(package=receipt_package, base=receipt_base)
        paths = {'src/main.ru', 'src/unselected.ru', 'tests/extra-policy.ru',
                 'locales/test.json', 'tools/generate_i18n.py',
                 'native/nested/extra.h', 'build/main.c', 'build/main-gui.c',
                 'build/app-resource.o', 'packaging/diagnostic_launcher.c',
                 *receipt_package.RESOURCE_INPUTS, *receipt_package.NATIVE_BUILD_DRIVERS}
        paths.update(source for sources in receipt_package.NATIVE_COMPILE_SOURCES.values() for source in sources)
        for relative in paths:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(('synthetic:' + relative).encode())
        for name in receipt_base.RUNTIME_NAMES:
            (self.binary / name).write_bytes(('runtime:' + name).encode())
        native = dict(output_name='RuSyntax.dll',
                      source_sha256=receipt_package.native_source_snapshot(self.root),
                      driver_sha256={rel: a.sha(self.root / rel) for rel in receipt_package.NATIVE_BUILD_DRIVERS},
                      compile_sources=list(receipt_package.NATIVE_COMPILE_SOURCES['RuSyntax.dll']),
                      compiler_flags=list(receipt_package.NATIVE_CFLAGS),
                      link_libraries=list(receipt_package.NATIVE_LINK_LIBRARIES),
                      compiler_path=str(self.cc), compiler_sha256=a.sha(self.cc),
                      compiler_version_sha256=hashlib.sha256(self.VERSION).hexdigest())
        self.helper = dict(schema=1, name='RuSyntax.dll', build_inputs=native,
                           build_key=receipt_package.native_build_key(native),
                           dll_sha256=a.sha(self.binary / 'RuSyntax.dll'))
        self.receipt = dict(schema=1, ru_commit=a.COMPILER, ru_tree=a.COMPILER_TREE,
                            entry_source='src/main.ru', entry_sha256=a.sha(self.root / 'src/main.ru'),
                            source_sha256=a.source_snapshot(self.root, self.p),
                            build_input_sha256={rel: a.sha(self.root / rel) for rel in (*receipt_package.RESOURCE_INPUTS, 'packaging/diagnostic_launcher.c')},
                            generated_c_sha256=a.sha(self.root / 'build/main.c'),
                            translation_unit_sha256=a.sha(self.root / 'build/main-gui.c'),
                            native_helper_build_key=self.helper['build_key'],
                            compiler_command=[str(self.cc), '-std=c99', '-O2', '-Wall', '-Wextra', '-Wno-unused-function', '-static-libgcc',
                                              str(self.root / 'build/main-gui.c'), '-o', str(self.binary / 'ru_notepad.exe'), '-lm',
                                              str(self.root / 'build/app-resource.o'), '-mwindows', '-lshell32', '-luser32'])
        for name, key in zip(receipt_base.RUNTIME_NAMES, ('exe_sha256', 'dll_sha256', 'lexilla_dll_sha256', 'native_helper_sha256')):
            self.receipt[key] = a.sha(self.binary / name)
        self.write()
    def write(self):
        (self.binary / 'ru_notepad.build.json').write_text(json.dumps(self.receipt))
        (self.binary / 'RuSyntax.native-build.json').write_text(json.dumps(self.helper))
    def reseal_native_key(self):
        self.helper['build_key'] = receipt_package.native_build_key(self.helper['build_inputs'])
        self.receipt['native_helper_build_key'] = self.helper['build_key']
    def verify(self, *, version=None, returncode=0):
        def compiler_version(command, **kwargs):
            if command != [str(self.cc), '--version']:
                raise AssertionError('unexpected external command')
            return subprocess.CompletedProcess(command, returncode, self.VERSION if version is None else version, b'')
        # Only the version subprocess is mocked: all receipts, source scanning,
        # hashes, constants, source/layout checks and native build keys are real.
        with patch.object(a.subprocess, 'run', side_effect=compiler_version):
            return a.full_receipt(self.root, self.binary, self.cc, self.p)
    def close(self):
        self.temp.cleanup()


class FullReceiptControls(unittest.TestCase):
    def fresh(self):
        fixture = FullReceiptFixture()
        self.addCleanup(fixture.close)
        return fixture
    def reject(self, mutate, *, reseal=False):
        f = self.fresh()
        mutate(f)
        if reseal:
            f.reseal_native_key()
        f.write()
        with self.assertRaises((ValueError, RuntimeError, KeyError, OSError)):
            f.verify()
    def test_full_real_snapshot_and_receipt_accepted(self):
        f = self.fresh()
        self.assertEqual(f.verify(), f.receipt)
        self.assertIn('src/unselected.ru', f.receipt['source_sha256'])
        self.assertIn('tests/extra-policy.ru', f.receipt['source_sha256'])
        self.assertIn('native/nested/extra.h', f.receipt['source_sha256'])
    def test_non_selected_source_bytes_rejected(self):
        for relative in ('src/unselected.ru', 'tests/extra-policy.ru', 'locales/test.json', 'tools/generate_i18n.py', 'native/nested/extra.h'):
            with self.subTest(relative=relative):
                self.reject(lambda f: (f.root / relative).write_bytes(b'changed'))
    def test_extra_unreceipted_source_rejected(self):
        for relative in ('src/new.ru', 'tests/new.ru', 'locales/new.json', 'native/new.h'):
            with self.subTest(relative=relative):
                self.reject(lambda f: (f.root / relative).write_bytes(b'extra'))
    def test_missing_source_file_rejected(self):
        self.reject(lambda f: (f.root / 'src/unselected.ru').unlink())
    def test_omitted_source_receipt_entry_rejected(self):
        self.reject(lambda f: f.receipt['source_sha256'].pop('src/unselected.ru'))
    def test_extra_source_receipt_entry_rejected(self):
        self.reject(lambda f: f.receipt['source_sha256'].update({'src/absent.ru': '0' * 64}))
    def test_build_input_bytes_and_receipt_coverage_rejected(self):
        for relative in (*receipt_package.RESOURCE_INPUTS, 'packaging/diagnostic_launcher.c'):
            with self.subTest(relative=relative):
                self.reject(lambda f: (f.root / relative).write_bytes(b'changed'))
        self.reject(lambda f: f.receipt['build_input_sha256'].pop('VERSION'))
        self.reject(lambda f: f.receipt['build_input_sha256'].update({'unexpected': '0' * 64}))
    def test_fixture_canonicalizes_noncanonical_temp_spelling(self):
        original=tempfile.TemporaryDirectory
        def alternate(*args,**kwargs):
            value=original(*args,**kwargs)
            path=Path(value.name)
            value.name=str(path/'..'/path.name)
            return value
        with patch.object(tempfile,'TemporaryDirectory',side_effect=alternate):
            f=self.fresh()
            self.assertEqual(f.home,f.home.resolve())
            f.verify()

    def test_all_runtime_hashes_rejected(self):
        for name in receipt_base.RUNTIME_NAMES:
            with self.subTest(name=name):
                self.reject(lambda f: (f.binary / name).write_bytes(b'changed-runtime'))
    def test_generated_c_and_translation_unit_rejected(self):
        for relative in ('build/main.c', 'build/main-gui.c'):
            with self.subTest(relative=relative):
                self.reject(lambda f: (f.root / relative).write_bytes(b'changed-code'))
    def test_compiler_command_shape_and_tokens_rejected(self):
        self.reject(lambda f: f.receipt['compiler_command'].append('-DUNREVIEWED=1'))
        for index in (1, 2, 3, 4, 5, 6, 8, 10, 12, 13, 14):
            with self.subTest(index=index):
                self.reject(lambda f: f.receipt['compiler_command'].__setitem__(index, 'unexpected'))
    def test_compiler_command_wrong_existing_paths_rejected(self):
        for index in (0, 7, 9, 11):
            with self.subTest(index=index):
                def change(f):
                    wrong = f.home / 'other-file'
                    wrong.write_bytes(b'other')
                    f.receipt['compiler_command'][index] = str(wrong)
                self.reject(change)
    def test_native_driver_bytes_rejected_even_with_consistent_build_key(self):
        for relative in receipt_package.NATIVE_BUILD_DRIVERS:
            with self.subTest(relative=relative):
                self.reject(lambda f: (f.root / relative).write_bytes(b'changed-driver'), reseal=True)
    def test_native_driver_receipt_hash_rejected_after_reseal(self):
        self.reject(lambda f: f.helper['build_inputs']['driver_sha256'].update({'tools/build.py': '0' * 64}), reseal=True)
    def test_native_compile_contract_rejected_after_reseal(self):
        for key, value in (('compile_sources', []), ('compiler_flags', ['-O0']), ('link_libraries', []), ('output_name', 'other.dll')):
            with self.subTest(key=key):
                self.reject(lambda f: f.helper['build_inputs'].__setitem__(key, value), reseal=True)
    def test_native_source_receipt_rejected_after_reseal(self):
        self.reject(lambda f: f.helper['build_inputs']['source_sha256'].pop('native/nested/extra.h'), reseal=True)
    def test_native_compiler_path_rejected_after_reseal(self):
        def change(f):
            other = f.home / 'other-compiler'
            other.write_bytes(f.cc.read_bytes())
            f.helper['build_inputs']['compiler_path'] = str(other)
        self.reject(change, reseal=True)
    def test_native_extra_source_entry_rejected_after_reseal(self):
        self.reject(lambda f: f.helper['build_inputs']['source_sha256'].update({'native/absent.h': '0' * 64}), reseal=True)
    def test_symlinked_parent_directory_rejected(self):
        f = self.fresh()
        directory = f.root / 'src'
        original = f.home / 'original-src'
        directory.rename(original)
        try:
            directory.symlink_to(original, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('host does not permit directory symlinks')
        with self.assertRaises((ValueError, RuntimeError, OSError)):
            f.verify()
    def test_compiler_hash_identity_rejected_after_reseal(self):
        self.reject(lambda f: f.helper['build_inputs'].__setitem__('compiler_sha256', '0' * 64), reseal=True)
        self.reject(lambda f: f.cc.write_bytes(b'changed-compiler'), reseal=True)
    def test_compiler_version_receipt_and_actual_version_rejected(self):
        self.reject(lambda f: f.helper['build_inputs'].__setitem__('compiler_version_sha256', '0' * 64), reseal=True)
        for kwargs in ({'version': b'different compiler\n'}, {'returncode': 1}):
            f = self.fresh()
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                f.verify(**kwargs)
    def test_native_key_and_runtime_binding_rejected(self):
        self.reject(lambda f: f.helper.__setitem__('build_key', '0' * 64))
        self.reject(lambda f: f.receipt.__setitem__('native_helper_build_key', '0' * 64))
        self.reject(lambda f: f.helper.__setitem__('dll_sha256', '0' * 64))
    def test_compiler_pin_tree_and_entry_rejected(self):
        for key, value in (('ru_commit', '0' * 40), ('ru_tree', '0' * 40), ('entry_source', 'src/unselected.ru'), ('entry_sha256', '0' * 64)):
            with self.subTest(key=key):
                self.reject(lambda f: f.receipt.__setitem__(key, value))
    def test_symlinked_inputs_rejected(self):
        for kind in ('source', 'runtime', 'compiler', 'receipt'):
            f = self.fresh()
            target = {'source': f.root / 'src/unselected.ru', 'runtime': f.binary / 'Scintilla.dll',
                      'compiler': f.cc, 'receipt': f.binary / 'ru_notepad.build.json'}[kind]
            other = f.home / ('symlink-target-' + kind)
            other.write_bytes(target.read_bytes())
            target.unlink()
            try:
                target.symlink_to(other)
            except (OSError, NotImplementedError):
                self.skipTest('host does not permit symlink creation')
            with self.subTest(kind=kind), self.assertRaises((ValueError, RuntimeError, OSError)):
                f.verify()
    def test_compiler_regular_hardlink_alias_is_identity_bound(self):
        f=self.fresh();alias=f.home/'gcc-alias'
        os.link(f.cc,alias)
        self.assertGreater(f.cc.stat().st_nlink,1)
        with self.assertRaises(ValueError):a.plain(f.cc)
        self.assertEqual(a.compiler_file(f.cc),f.cc)
        f.verify()
        alias.write_bytes(b'changed through compiler hardlink')
        with self.assertRaises(ValueError):f.verify()
    def test_compiler_alias_cannot_change_expected_receipt_path(self):
        f=self.fresh();alias=f.home/'gcc-alias';os.link(f.cc,alias)
        f.helper['build_inputs']['compiler_path']=str(alias);f.reseal_native_key();f.write()
        with self.assertRaises(ValueError):f.verify()
    def test_compiler_exception_does_not_admit_runtime_alias(self):
        f=self.fresh();os.link(f.cc,f.home/'gcc-alias')
        target=f.binary/'RuSyntax.dll';os.link(target,f.home/'runtime-alias')
        with self.assertRaises(ValueError):f.verify()

    def test_hardlinked_inputs_rejected(self):
        for kind in ('source', 'runtime', 'receipt'):
            f = self.fresh()
            target = {'source': f.root / 'src/unselected.ru', 'runtime': f.binary / 'Scintilla.dll',
                      'compiler': f.cc, 'receipt': f.binary / 'ru_notepad.build.json'}[kind]
            try:
                os.link(target, f.home / ('hardlink-' + kind))
            except (OSError, NotImplementedError):
                self.skipTest('host does not permit hardlink creation')
            with self.subTest(kind=kind), self.assertRaises((ValueError, RuntimeError, OSError)):
                f.verify()



"""Same-job native provenance controls; synthetic files, real receipt/cache checks."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from contextlib import ExitStack
from unittest.mock import patch

import run_markdown_width_ab as a
import build as native_builder


class NativeOriginFixture:
    JOB = {'GITHUB_RUN_ID': '123456', 'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_SHA': 'a' * 40}
    def __init__(self):
        self.f = FullReceiptFixture()
        f = self.f
        old = f.binary
        f.binary = f.root / 'build/markdown-edit-experiment/bin'
        f.binary.parent.mkdir(parents=True)
        old.rename(f.binary)
        f.receipt['compiler_command'][9] = str(f.binary / 'ru_notepad.exe')
        f.helper['compiler_command'] = [str(f.cc), *f.p.package.NATIVE_CFLAGS,
            *f.p.package.NATIVE_COMPILE_SOURCES['RuSyntax.dll'], '-o',
            str(f.root / 'build/native-helper/RuSyntax.pending.dll'),
            *('-l' + x for x in f.p.package.NATIVE_LINK_LIBRARIES)]
        f.write()
        self.candidate = f.home / 'candidate'
        shutil.copytree(f.root, self.candidate)
        self.cbin = self.candidate / 'build/markdown-edit-experiment/bin'
        shutil.rmtree(self.cbin)
        for relative in ('vendor/scintilla/bin/Scintilla.dll', 'vendor/lexilla/bin/lexilla.dll'):
            path = self.candidate / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'candidate vendor before sync')
        self.cache = self.candidate / 'build/native-helper'
        self.stamp = self.candidate / 'build/markdown-width-native-origin.json'
    def close(self): self.f.close()
    def context(self):
        f = self.f
        stack = ExitStack()
        def version(command, **kwargs):
            if command != [str(f.cc), '--version']:
                raise AssertionError('unexpected external command: only compiler version allowed')
            return subprocess.CompletedProcess(command, 0, f.VERSION, b'')
        stack.enter_context(patch.dict(os.environ, self.JOB))
        stack.enter_context(patch.object(a, 'load_protocol', return_value=f.p))
        stack.enter_context(patch.object(a.subprocess, 'run', side_effect=version))
        return stack
    def sync(self):
        f = self.f
        return a.sync_dlls(f.root, self.candidate, f.binary, f.cc)
    def verify(self, require_candidate=True):
        f = self.f
        return a.verify_native_origin(f.root, self.candidate, f.cc, f.p, require_candidate=require_candidate)
    def candidate_receipt(self):
        f = self.f
        self.cbin.mkdir(parents=True)
        for name in f.p.base.RUNTIME_NAMES:
            shutil.copyfile(f.binary / name, self.cbin / name)
        shutil.copyfile(self.cache / 'RuSyntax.native-build.json', self.cbin / 'RuSyntax.native-build.json')
        receipt = copy.deepcopy(f.receipt)
        for index in (7, 9, 11):
            receipt['compiler_command'][index] = str(self.candidate / Path(receipt['compiler_command'][index]).relative_to(f.root))
        receipt['source_sha256'] = a.source_snapshot(self.candidate, f.p)
        (self.cbin / 'ru_notepad.build.json').write_text(json.dumps(receipt))
    def ready(self):
        self.sync()
        self.candidate_receipt()


class NativeOriginControls(unittest.TestCase):
    def fresh(self):
        x = NativeOriginFixture()
        self.addCleanup(x.close)
        self.enterContext(x.context())
        return x
    def reject(self, change, *, ready=True):
        x = self.fresh()
        if ready: x.ready()
        change(x)
        with self.assertRaises((ValueError, RuntimeError, OSError, KeyError)):
            x.verify() if ready else x.sync()
    def test_sync_and_both_receipts_verified(self):
        x = self.fresh(); x.sync()
        self.assertEqual(x.verify(False), a.sha(x.stamp))
        x.candidate_receipt()
        self.assertEqual(x.verify(), a.sha(x.stamp))
        for name in ('RuSyntax.dll', 'RuSyntax.native-build.json'):
            self.assertEqual((x.cache / name).read_bytes(), (x.f.binary / name).read_bytes())
        for name, rel in (('Scintilla.dll','vendor/scintilla/bin/Scintilla.dll'),('Lexilla.dll','vendor/lexilla/bin/lexilla.dll')):
            self.assertEqual((x.candidate / rel).read_bytes(), (x.f.binary / name).read_bytes())
    def test_candidate_native_source_mutation_before_sync(self):
        self.reject(lambda x: (x.candidate / 'native/nested/extra.h').write_bytes(b'changed'), ready=False)
    def test_candidate_driver_mutation_before_sync(self):
        self.reject(lambda x: (x.candidate / 'tools/build.py').write_bytes(b'changed'), ready=False)
    def test_existing_cache_rejected(self):
        self.reject(lambda x: x.cache.mkdir(), ready=False)
    def test_cross_job_rejected(self):
        for key, value in (('GITHUB_RUN_ID','123457'),('GITHUB_RUN_ATTEMPT','2'),('GITHUB_SHA','b'*40)):
            with self.subTest(key=key):
                x = self.fresh(); x.ready()
                with patch.dict(os.environ,{key:value}), self.assertRaises(ValueError): x.verify()
    def test_stamp_tamper_rejected(self):
        self.reject(lambda x: x.stamp.write_text('{}'))
    def test_stamp_each_identity_and_hash_field_tamper_rejected(self):
        paths = [('schema',), ('baseline_build_receipt_sha256',), ('helper_receipt_sha256',), ('native_build_key',)]
        paths += [('job', key) for key in ('run_id','run_attempt','candidate_commit','baseline_commit','baseline_root','candidate_root')]
        paths += [('dll_sha256', name) for name in ('Scintilla.dll','Lexilla.dll','RuSyntax.dll')]
        for keys in paths:
            with self.subTest(keys=keys):
                def change(x):
                    value=json.loads(x.stamp.read_text()); cursor=value
                    for key in keys[:-1]: cursor=cursor[key]
                    cursor[keys[-1]]='wrong'
                    x.stamp.write_text(json.dumps(value))
                self.reject(change)
    def test_absent_or_invalid_job_rejected_before_sync(self):
        for key in NativeOriginFixture.JOB:
            with self.subTest(key=key):
                x=self.fresh()
                with patch.dict(os.environ,{key:''}), self.assertRaises(ValueError): x.sync()
                self.assertFalse(x.cache.exists())
    def test_candidate_receipt_required_only_after_build(self):
        x=self.fresh(); x.sync()
        self.assertEqual(x.verify(False),a.sha(x.stamp))
        with self.assertRaises((ValueError,OSError)): x.verify()
    def test_candidate_helper_command_cannot_claim_recompile(self):
        def change(x):
            path=x.cbin / 'RuSyntax.native-build.json'
            value=json.loads(path.read_text())
            value['compiler_command'][-2]=str(x.candidate / 'different-output')
            path.write_text(json.dumps(value))
        self.reject(change)
    def test_compiler_hardlink_alias_write_rejected(self):
        def change(x):
            alias = x.f.home / 'cc-alias'
            os.link(x.f.cc, alias)
            alias.write_bytes(b'compiler identity changed through alias')
        self.reject(change)
    def test_candidate_native_source_mutation_after_sync(self):
        self.reject(lambda x: (x.candidate / 'native/nested/extra.h').write_bytes(b'changed'))
    def test_candidate_driver_mutation_after_sync(self):
        self.reject(lambda x: (x.candidate / 'tools/build.py').write_bytes(b'changed'))
    def test_cache_dll_mutation_rejected(self):
        self.reject(lambda x: (x.cache / 'RuSyntax.dll').write_bytes(b'changed'))
    def test_cache_receipt_mutation_rejected(self):
        self.reject(lambda x: (x.cache / 'RuSyntax.native-build.json').write_text('{}'))
    def test_cache_native_key_mutation_rejected(self):
        def change(x):
            path=x.cache / 'RuSyntax.native-build.json'
            value=json.loads(path.read_text()); value['build_key']='0'*64
            path.write_text(json.dumps(value))
        self.reject(change)
    def test_baseline_dll_mutation_rejected(self):
        self.reject(lambda x: (x.f.binary / 'RuSyntax.dll').write_bytes(b'changed'))
    def test_baseline_native_receipt_mutation_rejected(self):
        self.reject(lambda x: (x.f.binary / 'RuSyntax.native-build.json').write_text('{}'))
    def test_candidate_binary_dll_mutation_rejected(self):
        self.reject(lambda x: (x.cbin / 'RuSyntax.dll').write_bytes(b'changed'))
    def test_candidate_binary_native_receipt_mutation_rejected(self):
        self.reject(lambda x: (x.cbin / 'RuSyntax.native-build.json').write_text('{}'))
    def test_candidate_binary_app_receipt_mutation_rejected(self):
        self.reject(lambda x: (x.cbin / 'ru_notepad.build.json').write_text('{}'))
    def test_early_built_identity_outputs_only_fixed_hash_rows(self):
        import contextlib,io,re
        x=self.fresh();x.ready();output=io.StringIO()
        with contextlib.redirect_stdout(output):
            origin=a.check_built(x.f.root,x.candidate,x.f.cc,x.f.p)
        self.assertEqual(origin,a.sha(x.stamp));rows=output.getvalue().splitlines();self.assertEqual(len(rows),3)
        for i,row in enumerate(rows,1):
            self.assertRegex(row,r'^WIDTH_AB_DLL index='+str(i)+r' equal=1 baseline=[0-9a-f]{64} candidate=[0-9a-f]{64}$')
    def test_early_built_mismatch_fails_before_prepare(self):
        import contextlib,io
        x=self.fresh();x.ready();target=x.cbin/'Scintilla.dll';target.write_bytes(b'other valid recorded DLL')
        receipt=a.read(x.cbin/'ru_notepad.build.json');receipt['dll_sha256']=a.sha(target)
        (x.cbin/'ru_notepad.build.json').write_text(json.dumps(receipt))
        output=io.StringIO()
        with contextlib.redirect_stdout(output),self.assertRaises(ValueError):
            a.check_built(x.f.root,x.candidate,x.f.cc,x.f.p)
        rows=output.getvalue().splitlines();self.assertEqual(len(rows),3);self.assertTrue(rows[0].startswith('WIDTH_AB_DLL index=1 equal=0 '))
    def test_unknown_existing_origin_rejected_before_sync(self):
        x=self.fresh();x.stamp.write_text('{}')
        with self.assertRaises(ValueError):x.sync()
        self.assertFalse(x.cache.exists())

    def test_real_build_cache_hit_preserves_baseline_compiler_command(self):
        x=self.fresh(); x.sync(); f=x.f
        def version(command, **kwargs):
            self.assertEqual(command,[str(f.cc),'--version'])
            return f.VERSION
        with patch.object(native_builder,'ROOT',x.candidate), \
             patch.object(native_builder,'NATIVE_COMPILE_SOURCES',{'RuSyntax.dll': f.p.package.NATIVE_COMPILE_SOURCES['RuSyntax.dll']}), \
             patch.object(native_builder.subprocess,'check_output',side_effect=version):
            # No mocked build_native_helpers/native_build_inputs/hash/cache checks.
            # Any compile would hit the version-only subprocess guard and fail.
            result=native_builder.build_native_helpers(str(f.cc),x.candidate / 'build')
        self.assertEqual(result['RuSyntax.dll'],f.helper)
        self.assertEqual(result['RuSyntax.dll']['compiler_command'],f.helper['compiler_command'])
        self.assertIn(str(f.root / 'build/native-helper/RuSyntax.pending.dll'),result['RuSyntax.dll']['compiler_command'])
        self.assertEqual(x.verify(False),a.sha(x.stamp))


class ReporterControls(unittest.TestCase):
    def test_numeric_reporter_hides_private_errors_and_subtests(self):
        import contextlib,io,re
        class Probe(unittest.TestCase):
            def test_a(self):self.fail('PRIVATE_GUI_AND_PATH')
            def test_b(self):
                with self.subTest(private='PRIVATE_GUI_AND_PATH'):raise ValueError('PRIVATE_GUI_AND_PATH')
        output=io.StringIO()
        with contextlib.redirect_stdout(output):code=public_controls(unittest.defaultTestLoader.loadTestsFromTestCase(Probe))
        self.assertEqual(code,1);self.assertNotIn('PRIVATE',output.getvalue())
        rows=output.getvalue().splitlines()
        self.assertEqual(len(rows),3)
        for row in rows[:2]:self.assertRegex(row,r'^WIDTH_AB_CONTROL case=[12] status=[12] module=[012] line=[0-9]+ exception=[123]$')
        self.assertEqual(rows[-1],'WIDTH_AB_CONTROL cases=2 failed=1 errors=1 skipped=0')
    def test_numeric_reporter_success_and_skip_counts(self):
        import contextlib,io
        class Probe(unittest.TestCase):
            def test_a(self):pass
            @unittest.skip('PRIVATE')
            def test_b(self):pass
        output=io.StringIO()
        with contextlib.redirect_stdout(output):code=public_controls(unittest.defaultTestLoader.loadTestsFromTestCase(Probe))
        self.assertEqual(code,0)
        self.assertEqual(output.getvalue(),'WIDTH_AB_CONTROL cases=2 failed=0 errors=0 skipped=1\n')

def public_controls(suite=None):
    """Stable sorted case IDs and reviewed-module line numbers, never messages."""
    import contextlib,io
    suite=suite or unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    def flatten(node):
        for test in node:
            if isinstance(test,unittest.TestSuite):yield from flatten(test)
            else:yield test
    identities=sorted({test.id() for test in flatten(suite)})
    rows=[]
    class Result(unittest.TextTestResult):
        def numeric(self,test,error,status):
            identity=getattr(test,'test_case',test).id()
            if identity not in identities:identity=getattr(test,'_test_case',test).id()
            case=identities.index(identity)+1
            module=line=0;tb=error[2]
            while tb is not None:
                name=Path(tb.tb_frame.f_code.co_filename).name
                if name in ('test_markdown_width_ab.py','run_markdown_width_ab.py') and tb.tb_frame.f_code.co_name!='need':
                    module=1 if name=='test_markdown_width_ab.py' else 2;line=tb.tb_lineno
                tb=tb.tb_next
            kind=1 if issubclass(error[0],AssertionError) else 2 if issubclass(error[0],OSError) else 3
            rows.append((case,status,module,line,kind))
        def addFailure(self,test,error):
            self.numeric(test,error,1);super().addFailure(test,error)
        def addError(self,test,error):
            self.numeric(test,error,2);super().addError(test,error)
        def addSubTest(self,test,subtest,error):
            if error is not None:self.numeric(test,error,1 if issubclass(error[0],AssertionError) else 2)
            super().addSubTest(test,subtest,error)
    sink=io.StringIO()
    with contextlib.redirect_stdout(sink),contextlib.redirect_stderr(sink):
        result=unittest.TextTestRunner(stream=sink,resultclass=Result,verbosity=0).run(suite)
    for row in rows:
        print('WIDTH_AB_CONTROL case=%d status=%d module=%d line=%d exception=%d'%row)
    print('WIDTH_AB_CONTROL cases=%d failed=%d errors=%d skipped=%d'%(result.testsRun,len(result.failures),len(result.errors),len(result.skipped)))
    return 0 if result.wasSuccessful() else 1

if __name__=='__main__':
    if sys.argv[1:]==['--public']:raise SystemExit(public_controls())
    unittest.main()
