#!/usr/bin/env python3
"""Public-output allowlist controls. No GUI, product build, or real child launch."""
import contextlib
import copy
import hashlib
import io
import json
import math
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

import run_markdown_owned_profile as owned
import run_markdown_phase_profile as runner
from test_markdown_phase_profile import profile_record, route

SECRET='C:\\Users\\private-person\\workspace\\secret.ru: exception text'
HEADER='a'*64


def digest(label):
    return hashlib.sha256(label.encode()).hexdigest()


def sample():
    runtime={variant:{name:digest(name if name != 'ru_notepad.exe' else variant)
                      for name in owned.RUNTIME} for variant in ('release','profile')}
    runs=[]
    for variant,wall,user,kernel in (('release',100.0,300,40),('profile',150.0,500,50)):
        runs.append({'variant':variant,'executed':True,'passed':True,'cleanup_killed':False,
                     'cleanup_unconfirmed':False,'scenario_wall_ms':wall,
                     'process_cpu':{'user_100ns':user,'kernel_100ns':kernel,
                                    'scope':'whole_owned_process_lifetime','source':'retained_popen_handle'}})
    runs[1].update(phase_profile=profile_record(),probes={'route':route()})
    return {'schema':1,'diagnostic_only':True,'product_acceptance':'separate_not_claimed',
            'timing_kind':'nested_qpc_wall','cpu_kind':'outer_timer_thread_only',
            'sampling':False,'whole_process_hotspots':False,'passed':True,
            'fixture':{'bytes':1000000,'newlines':100000,'physical_lines':100001,'sha256':runner.FIXTURE_SHA256},
            'deadline_seconds':120.0,'runs':runs,'observed_wall_ratio':1.5,
            'output_retention_confirmed':True,
            'receipt':{'schema':1,'compiler_commit':'85c7821fda35aa79deeaf67b4d430f24ddd7f07f',
                       'receipt_sha256':digest('receipt'),'runtime_sha256':runtime,
                       'artifact_sha256':{key:digest(key) for key in ('release_tu','profile_tu','source_map')},
                       'source_manifest_sha256':digest('source'),'source_file_count':7}}


def leaves(value):
    if type(value) is dict:
        for child in value.values():
            yield from leaves(child)
    else:
        yield value


class ProjectionControls(unittest.TestCase):
    def project(self,value=None):
        return owned.public_projection(sample() if value is None else value,HEADER)

    def rejected(self,change):
        value=sample()
        change(value)
        with self.assertRaises(owned.PublicProjectionError) as caught:
            self.project(value)
        self.assertEqual(str(caught.exception),'invalid_public_projection')
        self.assertIsNone(caught.exception.__cause__)

    def test_full_fixed_numeric_hash_projection(self):
        value=sample()
        original=copy.deepcopy(value)
        public=self.project(value)
        self.assertEqual(value,original)
        self.assertEqual((public['passed'],public['valid'],public['complete'],public['invalid']),(1,1,1,0))
        self.assertEqual(tuple(public['phase_profile']['phases']),owned.PHASE_NAMES)
        self.assertEqual(public['phase_profile']['root_user_100ns'],100)
        self.assertEqual(public['phase_profile']['root_kernel_100ns'],20)
        self.assertEqual(public['phase_profile']['inter_root_gap_ticks'],20)
        for index,name in enumerate(owned.PHASE_NAMES):
            phase=public['phase_profile']['phases'][name]
            self.assertEqual(set(phase),{'entries','inclusive_ticks','exclusive_ticks',*owned.HOT_NAMES})
            self.assertEqual(phase['entries'],2)
            self.assertEqual(phase['inclusive_ticks'],80 if index == 0 else 10)
            self.assertEqual(phase['exclusive_ticks'],10)
            self.assertEqual([phase[key] for key in owned.HOT_NAMES],[1,2,3,4])
        self.assertEqual(public['observed_overhead']['wall_ratio'],1.5)
        self.assertEqual(public['observed_overhead']['wall_delta_ms'],50)
        self.assertEqual(public['observed_overhead']['cpu_delta_100ns'],210)
        self.assertAlmostEqual(public['observed_overhead']['cpu_ratio'],550/340)
        encoded=owned.public_bytes(public)
        self.assertLessEqual(len(encoded),owned.PUBLIC_LIMIT)
        self.assertEqual(json.loads(encoded),public)
        for leaf in leaves(public):
            self.assertNotIsInstance(leaf,bool)
            if type(leaf) is str:
                self.assertRegex(leaf,r'^(?:[0-9a-f]{40}|[0-9a-f]{64})$')
            else:
                self.assertIn(type(leaf),(int,float))
                self.assertTrue(math.isfinite(leaf))

    def test_unknown_paths_logs_pid_and_source_map_are_not_copied(self):
        value=sample()
        baseline=self.project(value)
        value.update({SECRET:SECRET,'source_map':{'entries':[{'source':SECRET,'name':SECRET}],
                                                  'binding':{'statement':SECRET}},
                      'failure':SECRET,'measurement':SECRET,'output_policy':SECRET,
                      'overhead_interpretation':SECRET,'observed_wall_ratio':SECRET})
        for run in value['runs']:
            run.update({SECRET:SECRET,'owned_pid':SECRET,'exit_code':SECRET,'failure':SECRET,
                        'launcher_log':SECRET,'raw_log':SECRET,'last_observed_wall_ms':SECRET})
        value['runs'][1]['probes']['source_path']=SECRET
        public=self.project(value)
        self.assertEqual(public,baseline)
        self.assertNotIn('private-person',owned.public_bytes(public).decode())

    def test_exact_boolean_types(self):
        for field in ('passed','diagnostic_only','sampling','output_retention_confirmed'):
            for bad in (1,0,'true',None,[],{}):
                with self.subTest(field=field,bad=bad):
                    self.rejected(lambda s:s.__setitem__(field,bad))
        for field in ('executed','passed','cleanup_killed','cleanup_unconfirmed',
                      'output_overflow','retained_output_unconfirmed'):
            self.rejected(lambda s:s['runs'][0].__setitem__(field,1))
        for field in ('valid','raw_counts_trusted'):
            self.rejected(lambda s:s['runs'][1]['phase_profile'].__setitem__(field,1))

    def test_wall_requires_finite_bounded_real_number(self):
        for bad in (True,False,-1,float('nan'),float('inf'),float('-inf'),
                    120001,10**1000,SECRET,None,[],{}):
            with self.subTest(bad_type=type(bad).__name__):
                self.rejected(lambda s:s['runs'][0].__setitem__('scenario_wall_ms',bad))
        self.rejected(lambda s:s['runs'][0].__setitem__('scenario_wall_ms',0))

    def test_all_phase_integers_are_exact_bounded_unsigned(self):
        for key in owned.PHASE_INTEGERS:
            for bad in (True,1.0,-1,2**64,SECRET):
                with self.subTest(key=key,bad=bad):
                    self.rejected(lambda s:s['runs'][1]['phase_profile'].__setitem__(key,bad))
        for key in owned.PROGRESS_INTEGERS:
            self.rejected(lambda s:s['runs'][1]['phase_profile']['progress'].__setitem__(key,True))
        for key in ('entries','inclusive_ticks','exclusive_ticks'):
            for bad in (True,1.0,-1,2**64,SECRET):
                self.rejected(lambda s:s['runs'][1]['phase_profile']['phases'][0].__setitem__(key,bad))
        for field in ('hot_totals',):
            self.rejected(lambda s:s['runs'][1]['phase_profile'][field].__setitem__(0,True))
        self.rejected(lambda s:s['runs'][1]['phase_profile']['phases'][0]['hot'].__setitem__(0,2**64))

    def test_cpu_and_file_count_bounds(self):
        for key in ('user_100ns','kernel_100ns'):
            for bad in (True,1.0,-1,2**64,SECRET):
                self.rejected(lambda s:s['runs'][0]['process_cpu'].__setitem__(key,bad))
        self.rejected(lambda s:s['runs'][0]['process_cpu'].update(user_100ns=owned.UINT64_MAX,kernel_100ns=1))
        for bad in (True,7.0,-1,0,6,513,SECRET):
            self.rejected(lambda s:s['receipt'].__setitem__('source_file_count',bad))

    def test_hash_validation_and_fixed_inventory(self):
        setters=[
            lambda s,v:s['receipt'].__setitem__('receipt_sha256',v),
            lambda s,v:s['receipt'].__setitem__('source_manifest_sha256',v),
            lambda s,v:s['receipt']['artifact_sha256'].__setitem__('source_map',v),
            lambda s,v:s['receipt']['runtime_sha256']['release'].__setitem__('ru_notepad.exe',v),
            lambda s,v:s['fixture'].__setitem__('sha256',v)]
        for setter in setters:
            for bad in (SECRET,'A'*64,'g'*64,'a'*63,'a'*65,'a'*64+'\n',64,True,None):
                self.rejected(lambda s:setter(s,bad))
        for bad in ('a'*39,'a'*41,'A'*40,SECRET,True):
            self.rejected(lambda s:s['receipt'].__setitem__('compiler_commit',bad))
        for bad in (SECRET,'A'*64,'a'*63,True):
            with self.assertRaises(owned.PublicProjectionError):
                owned.public_projection(sample(),bad)
        self.rejected(lambda s:s['receipt']['runtime_sha256']['release'].__setitem__(SECRET,HEADER))
        self.rejected(lambda s:s['receipt']['artifact_sha256'].__setitem__(SECRET,HEADER))
        self.rejected(lambda s:s['receipt'].__setitem__('path',SECRET))

    def test_phase_labels_shapes_and_partition_cannot_be_spoofed(self):
        changes=[
            lambda s:s['runs'][1]['phase_profile']['phases'][0].__setitem__('name',SECRET),
            lambda s:s['runs'][1]['phase_profile']['phases'][0].__setitem__(SECRET,1),
            lambda s:s['runs'][1]['phase_profile']['phases'][0].__setitem__('exclusive_ticks',81),
            lambda s:s['runs'][1]['phase_profile']['phases'][1].__setitem__('exclusive_ticks',0),
            lambda s:s['runs'][1]['phase_profile'].__setitem__('phases',[]),
            lambda s:s['runs'][1]['phase_profile'].__setitem__('hot_names',[SECRET]*4),
            lambda s:s['runs'][1]['phase_profile'].__setitem__('hot_totals',[1]*5),
            lambda s:s['runs'][1]['phase_profile'].__setitem__('depth',33),
            lambda s:s['runs'][1]['phase_profile'].__setitem__('complete',2),
            lambda s:s['runs'][1]['phase_profile'].__setitem__('failure_code',24),
            lambda s:s['runs'][1]['phase_profile']['progress'].__setitem__('eof',2),
            lambda s:s['runs'][1]['phase_profile'].__setitem__('raw_log',SECRET)]
        for change in changes:
            self.rejected(change)

    def test_fixed_semantics_and_success_consistency(self):
        changes=[
            lambda s:s.__setitem__('schema',True),
            lambda s:s.__setitem__('product_acceptance',SECRET),
            lambda s:s['fixture'].__setitem__('bytes',1000001),
            lambda s:s['runs'][0].__setitem__('variant',SECRET),
            lambda s:s['runs'].reverse(),
            lambda s:s['runs'].append(copy.deepcopy(s['runs'][1])),
            lambda s:s['runs'][0].__setitem__('cleanup_killed',True),
            lambda s:s['runs'][1].__setitem__('phase_profile',None),
            lambda s:s['runs'][0].__setitem__('phase_profile',profile_record()),
            lambda s:s.__setitem__('output_retention_confirmed',False),
            lambda s:s['runs'][0]['process_cpu'].__setitem__('scope',SECRET)]
        for change in changes:
            self.rejected(change)

    def test_absent_profile_is_explicitly_invalid_with_available_release_numbers(self):
        value=sample()
        value['passed']=False
        value['runs']=value['runs'][:1]
        value['failure']=SECRET
        public=self.project(value)
        self.assertEqual((public['valid'],public['complete'],public['invalid']),(0,0,1))
        self.assertEqual(public['runs']['release']['scenario_wall_ms'],100)
        self.assertEqual(public['runs']['profile']['present'],0)
        self.assertEqual(public['phase_profile']['present'],0)
        self.assertEqual(public['phase_profile']['invalid'],1)
        self.assertEqual(public['observed_overhead']['pair_count'],0)
        self.assertNotIn('private-person',owned.public_bytes(public).decode())

    def test_partial_failed_run_does_not_invent_measurements(self):
        value=sample()
        value['passed']=False
        value['runs']=[{'variant':'release','executed':False,'passed':False,'failure':SECRET}]
        public=self.project(value)
        self.assertEqual(public['runs']['release']['wall_available'],0)
        self.assertEqual(public['runs']['release']['cpu_available'],0)
        self.assertEqual(public['runs']['release']['process_user_100ns'],0)
        self.assertEqual(public['observed_overhead']['cpu_ratio_available'],0)

    def test_invalid_phase_counts_never_claim_validity(self):
        value=sample()
        value['passed']=False
        value['runs'][1]['passed']=False
        record=value['runs'][1]['phase_profile']
        record.update(valid=False,raw_counts_trusted=False,failure_code=13)
        public=self.project(value)
        self.assertEqual(public['phase_profile']['failure_code'],13)
        self.assertEqual(public['phase_profile']['valid'],0)
        self.assertEqual(public['phase_profile']['raw_counts_trusted'],0)
        self.assertEqual(public['phase_profile']['complete'],1)
        self.assertEqual(public['complete'],0)
        record['raw_counts_trusted']=True
        with self.assertRaises(owned.PublicProjectionError):
            self.project(value)

    def test_zero_cpu_ratio_and_negative_observed_overhead(self):
        value=sample()
        value['runs'][1]['scenario_wall_ms']=50
        value['runs'][1]['process_cpu'].update(user_100ns=100,kernel_100ns=10)
        public=self.project(value)
        self.assertEqual(public['observed_overhead']['wall_delta_ms'],-50)
        self.assertEqual(public['observed_overhead']['cpu_delta_100ns'],-230)
        value['runs'][0]['process_cpu'].update(user_100ns=0,kernel_100ns=0)
        public=self.project(value)
        self.assertEqual(public['observed_overhead']['cpu_ratio_available'],0)
        self.assertEqual(public['observed_overhead']['cpu_ratio'],0)
        self.assertEqual(public['observed_overhead']['cpu_delta_100ns'],110)

    def test_failure_records_are_small_fixed_numeric_schema(self):
        for code in range(1,owned.PUBLIC_WRITE_FAILED+1):
            record=owned.public_failure(code)
            self.assertTrue(all(type(value) is int for value in record.values()))
            self.assertEqual(record['failure_code'],code)
            self.assertEqual(record['invalid'],1)
            self.assertLess(len(owned.public_bytes(record)),256)
        for bad in (0,6,True,1.0,SECRET,None):
            with self.assertRaises(owned.PublicProjectionError):
                owned.public_failure(bad)

    def test_final_encoder_rejects_unsanitized_or_extended_records(self):
        for value in (sample(),{'schema':1,'failure':SECRET},[SECRET]):
            with self.assertRaises(owned.PublicProjectionError):
                owned.public_bytes(value)
        for mutate in (
                lambda s:s.__setitem__('source_map',SECRET),
                lambda s:s['artifacts']['release'].__setitem__(SECRET,HEADER),
                lambda s:s['phase_profile']['phases']['callback'].__setitem__('raw_log',SECRET),
                lambda s:s['runs']['release'].__setitem__('scenario_wall_ms',SECRET),
                lambda s:s['observed_overhead'].__setitem__('wall_ratio',float('nan')),
                lambda s:s['inputs'].__setitem__('profile_header_sha256',SECRET)):
            value=self.project()
            mutate(value)
            with self.assertRaises(owned.PublicProjectionError):
                owned.public_bytes(value)


class MainControls(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.evidence=self.root/'measurements'
        self.evidence.mkdir()
        (self.root/'build').mkdir()
        self.args=['--ru-root',str(self.root/'compiler'),'--binary-dir',str(self.root/'bin'),
                   '--evidence-dir',str(self.evidence),'--cc','fake-gcc','--windres','fake-windres']
    def tearDown(self):
        self.temp.cleanup()
    def run_main(self,prepare=None,summary=None,platform='win32'):
        output=io.StringIO()
        with patch.object(owned,'ROOT',self.root),patch.object(owned.sys,'platform',platform), \
             patch.object(owned,'prepare',side_effect=prepare if callable(prepare) else None,
                          return_value=(self.root/'release',self.root/'profile',self.root/'receipt',{'secret':SECRET})), \
             patch.object(runner,'run_pair',return_value=summary or sample()), \
             patch.object(owned,'sha',return_value=HEADER), \
             contextlib.redirect_stdout(output),contextlib.redirect_stderr(output):
            status=owned.main(self.args)
        return status,output.getvalue()
    def record(self):
        return json.loads((self.evidence/'markdown-owned-profile.json').read_text())

    def test_success_writes_only_fixed_public_basename(self):
        status,output=self.run_main()
        self.assertEqual(status,0)
        self.assertEqual([p.name for p in self.evidence.iterdir()],['markdown-owned-profile.json'])
        self.assertEqual(self.record(),owned.public_projection(sample(),HEADER))
        self.assertEqual(output,'MARKDOWN_OWNED_PROFILE_DIAGNOSTIC_COMPLETE=1\n')
        self.assertNotIn(SECRET,(self.evidence/'markdown-owned-profile.json').read_text())

    def test_prepare_exception_and_prints_stay_private(self):
        def failure(*args):
            print(SECRET)
            print(SECRET,file=owned.sys.stderr)
            raise RuntimeError(SECRET)
        status,output=self.run_main(prepare=failure)
        self.assertEqual(status,1)
        self.assertEqual(self.record(),owned.public_failure(owned.PUBLIC_PREPARE_FAILED))
        self.assertNotIn('private-person',output)
        private=list((self.root/'build').glob('ru-markdown-owned-*'))
        self.assertEqual(len(private),1)
        self.assertIn('private-person',(private[0]/'preparation.log').read_text())

    def test_private_output_is_bounded(self):
        def noisy(*args):
            print(SECRET*owned.MAX_LOG)
        status,output=self.run_main(prepare=noisy)
        self.assertEqual(status,1)
        self.assertNotIn('private-person',output)
        for path in (self.root/'build').glob('*/preparation.log'):
            self.assertLessEqual(path.stat().st_size,owned.MAX_LOG)

    def test_projection_exception_is_fixed_numeric_failure(self):
        value=sample()
        value['runs'][1]['phase_profile']['phases'][0]['name']=SECRET
        status,output=self.run_main(summary=value)
        self.assertEqual(status,1)
        self.assertEqual(self.record(),owned.public_failure(owned.PUBLIC_PROJECTION_FAILED))
        self.assertNotIn('private-person',output)

    def test_unsupported_host_does_not_prepare_or_launch(self):
        def forbidden(*args):
            self.fail('unsupported host prepared')
        status,output=self.run_main(prepare=forbidden,platform='linux')
        self.assertEqual(status,1)
        self.assertEqual(self.record(),owned.public_failure(owned.PUBLIC_UNSUPPORTED_HOST))
        self.assertEqual(list((self.root/'build').iterdir()),[])
        self.assertNotIn(str(self.root),output)

    def test_existing_public_file_is_not_overwritten(self):
        path=self.evidence/'markdown-owned-profile.json'
        path.write_text('previous-result')
        status,output=self.run_main()
        self.assertEqual(status,1)
        self.assertEqual(path.read_text(),'previous-result')
        self.assertIn('MARKDOWN_OWNED_PROFILE_FAILURE_CODE=5',output)
        self.assertNotIn(str(self.root),output)

    def test_linked_public_file_is_not_followed(self):
        target=self.root/'private-target'
        target.write_text('preserve')
        try:
            (self.evidence/'markdown-owned-profile.json').symlink_to(target)
        except OSError:
            self.skipTest('symlinks unavailable')
        status,output=self.run_main()
        self.assertEqual(status,1)
        self.assertEqual(target.read_text(),'preserve')
        self.assertNotIn(str(target),output)

    def test_failed_flush_never_publishes_partial_json(self):
        with patch.object(owned.os,'fsync',side_effect=OSError(SECRET)):
            status,output=self.run_main()
        self.assertEqual(status,1)
        self.assertEqual(list(self.evidence.iterdir()),[])
        self.assertNotIn('private-person',output)

    def test_failed_partial_write_never_publishes_json(self):
        original=owned.os.fdopen
        class BrokenWriter:
            def __init__(self,fd,mode):
                self.stream=original(fd,mode)
            def __enter__(self):
                return self
            def __exit__(self,*args):
                self.stream.close()
            def write(self,data):
                self.stream.write(data[:32])
                self.stream.flush()
                raise OSError(SECRET)
        with patch.object(owned.os,'fdopen',side_effect=BrokenWriter):
            status,output=self.run_main()
        self.assertEqual(status,1)
        self.assertEqual(list(self.evidence.iterdir()),[])
        self.assertNotIn('private-person',output)

    def test_nonthrowing_short_write_never_publishes_json(self):
        original=owned.os.fdopen
        class ShortWriter:
            def __init__(self,fd,mode):
                self.stream=original(fd,mode)
            def __enter__(self):
                return self
            def __exit__(self,*args):
                self.stream.close()
            def __getattr__(self,name):
                return getattr(self.stream,name)
            def write(self,data):
                return self.stream.write(data[:32])
        with patch.object(owned.os,'fdopen',side_effect=ShortWriter):
            status,output=self.run_main()
        self.assertEqual(status,1)
        self.assertEqual(list(self.evidence.iterdir()),[])
        self.assertNotIn('private-person',output)

    def test_install_failure_never_publishes_json(self):
        install='rename' if owned.os.name == 'nt' else 'link'
        with patch.object(owned.os,install,side_effect=OSError(SECRET)):
            status,output=self.run_main()
        self.assertEqual(status,1)
        self.assertEqual(list(self.evidence.iterdir()),[])
        self.assertNotIn('private-person',output)

    def test_final_creation_race_is_no_replace(self):
        install='rename' if owned.os.name == 'nt' else 'link'
        original=getattr(owned.os,install)
        def race(source,destination,*args,**kwargs):
            self.assertNotEqual(Path(source).suffix,'.json')
            # The entire staging object is valid before publication is attempted.
            self.assertEqual(json.loads(Path(source).read_text()),owned.public_projection(sample(),HEADER))
            Path(destination).write_text('racing-result')
            return original(source,destination,*args,**kwargs)
        with patch.object(owned.os,install,side_effect=race):
            status,output=self.run_main()
        self.assertEqual(status,1)
        self.assertEqual((self.evidence/'markdown-owned-profile.json').read_text(),'racing-result')
        self.assertEqual([p.name for p in self.evidence.iterdir()],['markdown-owned-profile.json'])
        self.assertNotIn(str(self.root),output)

    def test_linked_evidence_directory_is_rejected(self):
        linked=self.root/'linked-measurements'
        try:
            linked.symlink_to(self.evidence,target_is_directory=True)
        except OSError:
            self.skipTest('symlinks unavailable')
        with self.assertRaises(ValueError):
            owned.publish_public(linked,owned.public_failure(owned.PUBLIC_PREPARE_FAILED))
        self.assertEqual(list(self.evidence.iterdir()),[])

    def test_publisher_rejects_raw_summary_before_writing(self):
        with self.assertRaises(owned.PublicProjectionError):
            owned.publish_public(self.evidence,sample())
        self.assertEqual(list(self.evidence.iterdir()),[])

    def test_changed_staging_inode_is_rejected_before_publication(self):
        original=owned.plain
        def replace_stage(path):
            path=Path(path)
            if path.suffix == '.tmp':
                path.rename(path.with_suffix('.old'))
                path.write_text(SECRET)
            return original(path)
        with patch.object(owned,'plain',side_effect=replace_stage):
            status,output=self.run_main()
        self.assertEqual(status,1)
        self.assertFalse((self.evidence/'markdown-owned-profile.json').exists())
        self.assertNotIn('private-person',output)

    def test_changed_owned_final_contents_are_rejected_and_removed(self):
        install='rename' if owned.os.name == 'nt' else 'link'
        original=getattr(owned.os,install)
        def corrupt(source,destination,*args,**kwargs):
            original(source,destination,*args,**kwargs)
            # Same inode, so it remains this publisher's owned output.
            Path(destination).write_text(SECRET)
        with patch.object(owned.os,install,side_effect=corrupt):
            status,output=self.run_main()
        self.assertEqual(status,1)
        self.assertFalse((self.evidence/'markdown-owned-profile.json').exists())
        self.assertNotIn('private-person',output)

    def test_malformed_cli_never_echoes_arguments(self):
        output=io.StringIO()
        with contextlib.redirect_stdout(output),contextlib.redirect_stderr(output):
            status=owned.main(self.args+['--unrecognized-private',SECRET])
        self.assertEqual(status,1)
        self.assertNotIn('private-person',output.getvalue())
        self.assertNotIn('unrecognized-private',output.getvalue())
        self.assertEqual(list(self.evidence.iterdir()),[])


if __name__=='__main__':
    unittest.main(verbosity=2)
