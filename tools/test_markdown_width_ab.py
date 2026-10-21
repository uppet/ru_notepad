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
        x=a.blank(P,COMMIT);x['prepared']=[1,1];x['runner_receipt_sha256']=['a'*64,'c'*64]
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
            with patch.object(a,'load_protocol',return_value=P),patch.object(a,'verify_roots',side_effect=verify),patch.object(a,'verify_arm',side_effect=arm),patch.object(base,'load_ci',return_value=ci),patch.object(edit,'run_pair',side_effect=pair),patch.object(edit,'run_owned',side_effect=owned_run):
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
            candidate=Path(t)/'candidate';candidate.mkdir()
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
        self.home = Path(self.temp.name)
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
    def test_hardlinked_inputs_rejected(self):
        for kind in ('source', 'runtime', 'compiler', 'receipt'):
            f = self.fresh()
            target = {'source': f.root / 'src/unselected.ru', 'runtime': f.binary / 'Scintilla.dll',
                      'compiler': f.cc, 'receipt': f.binary / 'ru_notepad.build.json'}[kind]
            try:
                os.link(target, f.home / ('hardlink-' + kind))
            except (OSError, NotImplementedError):
                self.skipTest('host does not permit hardlink creation')
            with self.subTest(kind=kind), self.assertRaises((ValueError, RuntimeError, OSError)):
                f.verify()



if __name__=='__main__':unittest.main()
