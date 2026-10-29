#!/usr/bin/env python3
"""Build one private same-source profile, then run one owned Windows pair.
Diagnostic only. Never replaces acceptance status or adds files to product bin.
"""
from __future__ import annotations
import argparse, contextlib, hashlib, json, math, os, re, shutil, stat, subprocess, sys, tempfile, time
from pathlib import Path
import profile_markdown_phases as transform

ROOT=Path(__file__).resolve().parents[1]
RUNTIME=('ru_notepad.exe','Scintilla.dll','Lexilla.dll','RuSyntax.dll')
MAX_LOG=65536
PUBLIC_LIMIT=16384
UINT64_MAX=(1 << 64)-1
PUBLIC_OK=0
PUBLIC_UNSUPPORTED_HOST=1
PUBLIC_PREPARE_FAILED=2
PUBLIC_RUN_FAILED=3
PUBLIC_PROJECTION_FAILED=4
PUBLIC_WRITE_FAILED=5
PHASE_NAMES=('timer_root','bridge_advance','pure_feed','bridge_publish',
             'bulk_prepare','native_other','native_bulk','callback')
HOT_NAMES=('v_index','env_get','heap_new','v_call')
PHASE_INTEGERS=('failure_code','foreign_thread_invalid','started','completion_requested',
                'complete','closed','depth','qpc_frequency','root_count','no_step_root_count',
                'step_count','outermost_root_ticks','root_user_100ns','root_kernel_100ns',
                'inter_root_gap_ticks','inter_root_gap_max_ticks','raw_native_other_entries',
                'raw_native_bulk_entries')
PROGRESS_INTEGERS=('identity','generation','revision','feed','length','range_count',
                   'range_index','range_offset','eof','pending')
RUNTIME_HASH_KEYS=('exe_sha256','scintilla_sha256','lexilla_sha256','native_helper_sha256')


class PublicProjectionError(ValueError):
    """One fixed message; never format an untrusted value, key, path or exception."""
    def __init__(self):
        super().__init__('invalid_public_projection')


def require(condition):
    if not condition:
        raise PublicProjectionError()


def object_fields(value, fields=None):
    require(type(value) is dict)
    if fields is not None:
        require(set(value) == set(fields))
    return value


def uint(value, maximum=UINT64_MAX):
    require(type(value) is int and 0 <= value <= maximum)
    return value


def bit(value):
    require(type(value) is bool)
    return int(value)


def number(value, maximum):
    require(type(value) in (int,float) and math.isfinite(value) and 0 <= value <= maximum)
    return value


def hash_value(value, length=64):
    require(type(value) is str and re.fullmatch('[0-9a-f]{'+str(length)+'}',value) is not None)
    return value


def fixed_fields(value, fields):
    for key, expected in fields.items():
        require(type(value[key]) is type(expected) and value[key] == expected)


def public_failure(code):
    """The only public record when preparation or projection cannot be trusted.

    Codes: 1 unsupported host, 2 preparation, 3 owned run, 4 projection,
    5 public write. No exception or raw diagnostic is accepted as an argument.
    """
    uint(code,PUBLIC_WRITE_FAILED)
    require(code != PUBLIC_OK)
    return {'schema':1,'diagnostic_only':1,'product_acceptance_claimed':0,
            'passed':0,'valid':0,'complete':0,'invalid':1,'failure_code':code}


def project_run(value):
    """Copy a fixed set of numeric run fields. PIDs, probes and errors stay private."""
    present=value is not None
    value=object_fields(value) if present else {}
    result={'present':int(present)}
    for key in ('executed','passed','cleanup_killed','cleanup_unconfirmed',
                'output_overflow','retained_output_unconfirmed'):
        result[key]=bit(value.get(key,False))
    result['wall_available']=int('scenario_wall_ms' in value)
    result['scenario_wall_ms']=number(value.get('scenario_wall_ms',0),120000)
    result['cpu_available']=int('process_cpu' in value)
    cpu=value.get('process_cpu')
    if cpu is not None:
        object_fields(cpu,('user_100ns','kernel_100ns','scope','source'))
        fixed_fields(cpu,{'scope':'whole_owned_process_lifetime','source':'retained_popen_handle'})
    else:
        require(not result['cpu_available'])
        cpu={}
    result['process_user_100ns']=uint(cpu.get('user_100ns',0))
    result['process_kernel_100ns']=uint(cpu.get('kernel_100ns',0))
    uint(result['process_user_100ns']+result['process_kernel_100ns'])
    if result['passed']:
        require(result['executed'] == result['wall_available'] == result['cpu_available'] == 1)
        require(result['scenario_wall_ms'] > 0)
        require(not any(result[k] for k in ('cleanup_killed','cleanup_unconfirmed',
                                            'output_overflow','retained_output_unconfirmed')))
    return result


def project_phase(record, route):
    """Validate the actual header schema; emit only fixed numeric aggregates.

    Invalid records can describe bounded, untrusted observations, but cannot
    claim valid counts. The normal runner retains only a validated valid record.
    """
    from run_markdown_phase_profile import validate_phase_record
    flags=('valid','raw_counts_trusted')
    fixed={'schema':1,'record':'markdown_phase_profile','diagnostic_only':True,
           'product_acceptance':'separate_not_claimed','timing_kind':'nested_qpc_wall',
           'cpu_kind':'outer_timer_thread_only','cpu_bounds':'slightly_enclose_qpc_root',
           'sampling':False,'whole_process_hotspots':False}
    present=record is not None
    if present:
        object_fields(record,(*fixed,*flags,*PHASE_INTEGERS,'hot_names','hot_totals','phases','progress'))
        fixed_fields(record,fixed)
        require(type(record['hot_names']) is list and len(record['hot_names']) == 4)
        require(all(type(v) is str and v == name for v,name in zip(record['hot_names'],HOT_NAMES)))
        require(type(record['phases']) is list and len(record['phases']) == 8)
        require(type(record['hot_totals']) is list and len(record['hot_totals']) == 4)
        object_fields(record['progress'],PROGRESS_INTEGERS)
    else:
        record={}
    result={'present':int(present),'valid':bit(record.get('valid',False)),
            'invalid':int(not record.get('valid',False)),
            'raw_counts_trusted':bit(record.get('raw_counts_trusted',False))}
    for key in PHASE_INTEGERS:
        maximum=23 if key == 'failure_code' else 32 if key == 'depth' else 1 if key in (
            'foreign_thread_invalid','started','completion_requested','complete','closed') else UINT64_MAX
        result[key]=uint(record.get(key,0),maximum)
    progress=record.get('progress',{})
    result['progress']={key:uint(progress.get(key,0),1 if key in ('eof','pending') else UINT64_MAX)
                        for key in PROGRESS_INTEGERS}
    result['hot_totals']={name:uint(record['hot_totals'][i] if present else 0)
                          for i,name in enumerate(HOT_NAMES)}
    result['phases']={}
    for index,name in enumerate(PHASE_NAMES):
        row=record['phases'][index] if present else {}
        if present:
            object_fields(row,('name','entries','inclusive_ticks','exclusive_ticks','hot'))
            fixed_fields(row,{'name':name})
            require(type(row['hot']) is list and len(row['hot']) == 4)
        clean={key:uint(row.get(key,0)) for key in ('entries','inclusive_ticks','exclusive_ticks')}
        require(clean['exclusive_ticks'] <= clean['inclusive_ticks'])
        clean.update({hot:uint(row['hot'][i] if present else 0) for i,hot in enumerate(HOT_NAMES)})
        result['phases'][name]=clean
    if present:
        require(result['valid'] == result['raw_counts_trusted'])
        if result['valid']:
            # Reuse the runner's partition, coverage and final-route checks.
            validate_phase_record(record,route)
        else:
            require(result['failure_code'] != 0)
    return result


def public_projection(summary, profile_header_sha256):
    """Reconstruct a fixed public schema from private diagnostics.

    The allowlist is structural, not a recursive scrubber. No source-map entry,
    receipt path, PID, log, exception, unknown key, or arbitrary string is copied.
    All string leaves are validated lowercase SHA-1/SHA-256 digests. Boolean
    inputs require the exact bool type and become numeric 0/1 output.
    """
    try:
        object_fields(summary)
        fixed_fields(summary,{'schema':1,'diagnostic_only':True,'product_acceptance':'separate_not_claimed',
                              'timing_kind':'nested_qpc_wall','cpu_kind':'outer_timer_thread_only',
                              'sampling':False,'whole_process_hotspots':False})
        passed=bit(summary['passed'])
        receipt=object_fields(summary['receipt'],('schema','compiler_commit','receipt_sha256',
            'runtime_sha256','artifact_sha256','source_manifest_sha256','source_file_count'))
        fixed_fields(receipt,{'schema':1})
        fixture=object_fields(summary['fixture'],('bytes','newlines','physical_lines','sha256'))
        from run_markdown_phase_profile import FIXTURE_SHA256
        fixed_fields(fixture,{'bytes':1000000,'newlines':100000,'physical_lines':100001,'sha256':FIXTURE_SHA256})
        require(type(summary['runs']) is list and len(summary['runs']) <= 2)
        runs=summary['runs']
        for index,run in enumerate(runs):
            object_fields(run)
            fixed_fields(run,{'variant':('release','profile')[index]})
        release=project_run(runs[0] if runs else None)
        profile=project_run(runs[1] if len(runs) == 2 else None)
        record=runs[1].get('phase_profile') if len(runs) == 2 else None
        route=runs[1].get('probes',{}).get('route') if record is not None else None
        phase=project_phase(record,route)
        if runs:
            require('phase_profile' not in runs[0])
        complete=int(release['passed'] and profile['passed'] and phase['complete'])
        retained=bit(summary['output_retention_confirmed'])
        if passed:
            require(complete == phase['valid'] == retained == 1)
        result={'schema':1,'diagnostic_only':1,'product_acceptance_claimed':0,
                'sampling':0,'whole_process_hotspots':0,'passed':passed,'valid':passed,
                'complete':complete,'invalid':1-passed,'failure_code':0 if passed else PUBLIC_RUN_FAILED,
                'output_retention_confirmed':retained,
                'inputs':{'fixture_bytes':fixture['bytes'],'fixture_newlines':fixture['newlines'],
                          'fixture_physical_lines':fixture['physical_lines'],
                          'fixture_sha256':hash_value(fixture['sha256']),
                          'compiler_commit':hash_value(receipt['compiler_commit'],40),
                          'source_file_count':uint(receipt['source_file_count'],512),
                          'source_manifest_sha256':hash_value(receipt['source_manifest_sha256']),
                          'runner_receipt_sha256':hash_value(receipt['receipt_sha256']),
                          'profile_header_sha256':hash_value(profile_header_sha256)},
                'artifacts':{},'runs':{'release':release,'profile':profile},'phase_profile':phase}
        require(result['inputs']['source_file_count'] >= 7)
        runtime=object_fields(receipt['runtime_sha256'],('release','profile'))
        for variant in ('release','profile'):
            hashes=object_fields(runtime[variant],RUNTIME)
            result['artifacts'][variant]={key:hash_value(hashes[name]) for key,name in zip(RUNTIME_HASH_KEYS,RUNTIME)}
        require(runtime['release']['ru_notepad.exe'] != runtime['profile']['ru_notepad.exe'])
        require(all(runtime['release'][name] == runtime['profile'][name] for name in RUNTIME[1:]))
        artifacts=object_fields(receipt['artifact_sha256'],('release_tu','profile_tu','source_map'))
        for key in ('release_tu','profile_tu','source_map'):
            result['artifacts'][key+'_sha256']=hash_value(artifacts[key])
        require(artifacts['release_tu'] != artifacts['profile_tu'])
        wall_available=int(release['passed'] and profile['passed'])
        release_cpu=release['process_user_100ns']+release['process_kernel_100ns']
        profile_cpu=profile['process_user_100ns']+profile['process_kernel_100ns']
        cpu_available=int(wall_available and release_cpu > 0)
        wall_ratio=profile['scenario_wall_ms']/release['scenario_wall_ms'] if wall_available else 0
        cpu_ratio=profile_cpu/release_cpu if cpu_available else 0
        result['observed_overhead']={
            'pair_count':wall_available,'wall_ratio_available':wall_available,
            'wall_ratio':number(wall_ratio,UINT64_MAX),
            'wall_delta_ms':profile['scenario_wall_ms']-release['scenario_wall_ms'] if wall_available else 0,
            'cpu_ratio_available':cpu_available,'cpu_ratio':number(cpu_ratio,UINT64_MAX),
            'cpu_delta_100ns':profile_cpu-release_cpu if wall_available else 0}
        # Explicit negative deltas describe observed overhead; they are never
        # subtracted from a phase. There is one pair, not a confidence interval.
        require(len(public_bytes(result)) <= PUBLIC_LIMIT)
        return result
    except Exception:
        # Includes runner validation failures. No exception chaining may expose
        # a private path or an untrusted field in a caller's traceback.
        raise PublicProjectionError() from None


def validate_public(value):
    """Defense in depth at the file boundary: reject even an unsanitized caller."""
    status={'schema':('fixed',1),'diagnostic_only':('fixed',1),
            'product_acceptance_claimed':('fixed',0),'passed':'bit','valid':'bit',
            'complete':'bit','invalid':'bit','failure_code':('uint',PUBLIC_WRITE_FAILED)}
    object_fields(value)
    if set(value) == set(status):
        require(value == public_failure(value['failure_code']))
        for key in status:
            require(type(value[key]) is int)
        return
    run={key:'bit' for key in ('present','executed','passed','cleanup_killed','cleanup_unconfirmed',
                              'output_overflow','retained_output_unconfirmed','wall_available','cpu_available')}
    run.update(scenario_wall_ms='wall',process_user_100ns='u64',process_kernel_100ns='u64')
    phase={key:'u64' for key in PHASE_INTEGERS}
    phase.update({key:'bit' for key in ('present','valid','invalid','raw_counts_trusted',
                                      'foreign_thread_invalid','started','completion_requested','complete','closed')})
    phase.update(failure_code=('uint',23),depth=('uint',32))
    phase['progress']={key:'bit' if key in ('eof','pending') else 'u64' for key in PROGRESS_INTEGERS}
    phase['hot_totals']={key:'u64' for key in HOT_NAMES}
    phase['phases']={name:{key:'u64' for key in ('entries','inclusive_ticks','exclusive_ticks',*HOT_NAMES)}
                     for name in PHASE_NAMES}
    shape=dict(status,sampling=('fixed',0),whole_process_hotspots=('fixed',0),
               output_retention_confirmed='bit',phase_profile=phase,runs={'release':run,'profile':run},
               inputs={'fixture_bytes':('fixed',1000000),'fixture_newlines':('fixed',100000),
                       'fixture_physical_lines':('fixed',100001),'fixture_sha256':'hash',
                       'compiler_commit':'commit','source_file_count':('uint',512),
                       'source_manifest_sha256':'hash','runner_receipt_sha256':'hash','profile_header_sha256':'hash'},
               artifacts={variant:{key:'hash' for key in RUNTIME_HASH_KEYS} for variant in ('release','profile')},
               observed_overhead={'pair_count':'bit','wall_ratio_available':'bit','wall_ratio':'ratio',
                                  'wall_delta_ms':'signed_wall','cpu_ratio_available':'bit','cpu_ratio':'ratio',
                                  'cpu_delta_100ns':'signed_u64'})
    shape['artifacts'].update({key+'_sha256':'hash' for key in ('release_tu','profile_tu','source_map')})
    def check(item,spec):
        if type(spec) is dict:
            object_fields(item,spec)
            for key in spec:
                check(item[key],spec[key])
        elif type(spec) is tuple:
            if spec[0] == 'fixed':
                require(type(item) is int and item == spec[1])
            else:
                uint(item,spec[1])
        elif spec in ('hash','commit'):
            hash_value(item,40 if spec == 'commit' else 64)
        elif spec in ('bit','u64'):
            uint(item,1 if spec == 'bit' else UINT64_MAX)
        elif spec == 'signed_u64':
            require(type(item) is int and -UINT64_MAX <= item <= UINT64_MAX)
        elif spec == 'signed_wall':
            require(type(item) in (int,float) and math.isfinite(item) and -120000 <= item <= 120000)
        else:
            number(item,120000 if spec == 'wall' else UINT64_MAX)
    check(value,shape)


def public_bytes(value):
    validate_public(value)
    data=(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
    require(len(data) <= PUBLIC_LIMIT)
    return data


def publish_public(evidence,value):
    """Flush a complete JSON file, then atomically publish without replacement.

    Windows rename refuses an existing destination. POSIX rename overwrites, so
    use an atomic no-replace hard-link installation there and unlink the staging
    name afterward. Both names are on the same filesystem. A failed write/flush
    never creates the public .json. Staging files are never upload candidates.
    """
    data=public_bytes(value)
    evidence=plain(evidence).resolve(strict=True)
    require(evidence.is_dir())
    final=evidence/'markdown-owned-profile.json'
    temporary=None
    installed=False
    try:
        fd,name=tempfile.mkstemp(prefix='.markdown-owned-profile-',suffix='.tmp',dir=evidence)
        temporary=Path(name)
        with os.fdopen(fd,'wb') as stream:
            require(stream.write(data) == len(data))
            stream.flush()
            os.fsync(stream.fileno())
            identity=os.fstat(stream.fileno())
        def verify(path,links):
            plain(path)
            info=path.lstat()
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == links and
                    (info.st_dev,info.st_ino,info.st_size) ==
                    (identity.st_dev,identity.st_ino,len(data)))
            with os.fdopen(os.open(path,os.O_RDONLY|getattr(os,'O_BINARY',0)|getattr(os,'O_NOFOLLOW',0)),'rb') as stream:
                opened=os.fstat(stream.fileno())
                require((opened.st_dev,opened.st_ino) == (identity.st_dev,identity.st_ino))
                require(stream.read(PUBLIC_LIMIT+1) == data)
        plain(evidence)
        verify(temporary,1)
        if os.name == 'nt':
            os.rename(temporary,final)
        else:
            os.link(temporary,final,follow_symlinks=False)
        installed=True
        verify(final,1 if os.name == 'nt' else 2)
    except BaseException:
        if installed:
            # Only a destination installed by this call is eligible for cleanup.
            # A stale/racing pre-existing destination is never removed.
            info=final.lstat()
            if (info.st_dev,info.st_ino) == (identity.st_dev,identity.st_ino):
                final.unlink()
        raise
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass  # No partial .json; an unpublishable .tmp stays private.


class PrivateOutput:
    """Bound Python/compiler diagnostic text in the private preparation log."""
    def __init__(self,stream):
        self.stream=stream
    def write(self,text):
        data=text.encode('utf-8',errors='replace')
        if self.stream.tell()+len(data) > MAX_LOG:
            raise RuntimeError('private_output_overflow')
        self.stream.write(data)
        return len(text)
    def flush(self):
        self.stream.flush()


class PublicArgumentParser(argparse.ArgumentParser):
    def error(self,message):
        # argparse's default error includes unrecognized user-supplied strings.
        raise PublicProjectionError()

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(path,data):
    with Path(path).open('x',encoding='utf-8',newline='\n') as f:json.dump(data,f,indent=2);f.write('\n')
def plain(path):
    p=Path(path).absolute()
    for part in (p,*p.parents):
        if part.is_symlink() or (part.exists() and bool(getattr(part.lstat(),'st_file_attributes',0)&0x400)):raise ValueError('Linked/reparse study path')
    return p

def bounded_command(command,cwd,log,seconds):
    # Fresh owned file and retained direct child only. No shell/session-wide tools.
    with log.open('xb') as stream:
        process=subprocess.Popen(list(map(str,command)),cwd=cwd,stdout=stream,stderr=subprocess.STDOUT)
        deadline=time.monotonic()+seconds
        try:
            while process.poll() is None:
                if time.monotonic()>=deadline:raise RuntimeError('Owned build deadline exceeded')
                if log.stat().st_size>MAX_LOG:raise RuntimeError('Owned build output overflow')
                time.sleep(.05)
            if log.stat().st_size>MAX_LOG:raise RuntimeError('Owned build output overflow')
            if process.returncode:raise RuntimeError('Owned build failed: '+log.name)
        finally:
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill();process.wait(timeout=5)


def prepare(ru_root,binary_dir,cc,windres,private):
    ru_root=plain(ru_root).resolve(strict=True);binary_dir=plain(binary_dir).resolve(strict=True)
    receipt=json.loads((binary_dir/'ru_notepad.build.json').read_text())
    if receipt['ru_commit']!='85c7821fda35aa79deeaf67b4d430f24ddd7f07f':raise ValueError('Product compiler pin mismatch')
    for relative,expected in receipt['source_sha256'].items():
        p=plain(ROOT/relative).resolve(strict=True)
        if not p.is_relative_to(ROOT) or sha(p)!=expected:raise ValueError('Product source identity mismatch')
    for relative,expected in receipt['build_input_sha256'].items():
        if sha(plain(ROOT/relative))!=expected:raise ValueError('Launcher/resource identity mismatch')
    expected=[receipt[k] for k in ('exe_sha256','dll_sha256','lexilla_dll_sha256','native_helper_sha256')]
    for name,want in zip(RUNTIME,expected):
        if sha(plain(binary_dir/name))!=want:raise ValueError('Product runtime identity mismatch')
    compiler_head=subprocess.check_output(['git','-C',str(ru_root),'rev-parse','HEAD'],timeout=20,text=True,stderr=subprocess.STDOUT).strip()
    compiler_tree=subprocess.check_output(['git','-C',str(ru_root),'rev-parse','HEAD^{tree}'],timeout=20,text=True,stderr=subprocess.STDOUT).strip()
    dirty=subprocess.check_output(['git','-C',str(ru_root),'status','--porcelain'],timeout=20,text=True,stderr=subprocess.STDOUT).strip()
    if compiler_head!=receipt['ru_commit'] or compiler_tree!=receipt['ru_tree'] or dirty:raise ValueError('Unsealed compiler source')
    sys.path.insert(0,str(ru_root))
    from rulang.frontend import parse
    from rulang.modules import load_module_graph
    from rulang.compiler import Compiler
    source=(ROOT/'src/main.ru').resolve();text=source.read_text(encoding='utf-8-sig');program=parse(text)
    graph=load_module_graph(str(source),program);graph.sources[graph.root]=text
    code=Compiler(program,graph.root,modules=graph,allow_native=True).compile()
    emitted=private/'main.c';emitted.write_text(code,encoding='utf-8')
    if sha(emitted)!=receipt['generated_c_sha256']:raise ValueError('Regenerated product C differs from receipt')
    mapping=transform.make_map(code,ROOT,receipt);mapfile=private/'source-map.json';write(mapfile,mapping)
    input_receipt=private/'input-receipt.json';write(input_receipt,receipt)
    header=ROOT/'native/markdown_phase_profile.h'
    transformed=transform.transform(code,ROOT,receipt,mapping,header.read_text())
    profile_c=private/'main-profile.c';profile_c.write_text(transformed,encoding='utf-8')
    launcher=(ROOT/'packaging/diagnostic_launcher.c').read_text()
    release_tu=private/'main-release-gui.c';release_tu.write_text('#define main ru_program_main\n'+code+'\n#undef main\n'+launcher,encoding='utf-8')
    if sha(release_tu)!=receipt['translation_unit_sha256']:raise ValueError('Regenerated product GUI TU differs from receipt')
    profile_tu=private/'main-profile-gui.c';profile_tu.write_text('#define main ru_program_main\n'+transformed+'\n#undef main\n'+launcher,encoding='utf-8')
    from test_markdown_phases import audit_actual
    audit_actual(ROOT,emitted,input_receipt,header)
    # The unchanged controls run in a bounded direct child so compiler error
    # paths/source snippets cannot escape to public CI stdout/stderr.
    bounded_command([sys.executable,ROOT/'tools/test_markdown_phase_observer.py',
                     '--input-c',emitted,'--cc',cc],ROOT,private/'observer.log',45)
    release=private/'release';profile=private/'profile';release.mkdir();profile.mkdir()
    for name in RUNTIME:
        shutil.copyfile(binary_dir/name,release/name)
        if name!='ru_notepad.exe':shutil.copyfile(binary_dir/name,profile/name)
    resource=private/'resource.o'
    bounded_command([windres,'-I',ROOT/'packaging',ROOT/'packaging/app.rc',resource],ROOT,private/'resource.log',30)
    command=[cc,'-std=c99','-O2','-Wall','-Wextra','-Wno-unused-function','-static-libgcc',profile_tu,'-o',profile/'ru_notepad.exe','-lm',resource,'-mwindows','-lshell32','-luser32']
    bounded_command(command,ROOT,private/'compile.log',180)
    # Recheck source and runtime inputs after compilation, before any launch.
    for relative,want in receipt['source_sha256'].items():
        if sha(ROOT/relative)!=want:raise ValueError('Source changed during diagnostic build')
    for name,want in zip(RUNTIME,expected):
        if sha(binary_dir/name)!=want:raise ValueError('Runtime changed during diagnostic build')
    required=['src/main.ru','src/markdown_syntax.ru','src/markdown_policy.ru','src/file_drop.ru','packaging/diagnostic_launcher.c','tools/windows_ci.py','tools/package.py']
    manifest={'schema':1,'compiler_commit':compiler_head,'source_sha256':{relative:sha(ROOT/relative) for relative in required},
      'runtime_sha256':{kind:{name:sha(folder/name) for name in RUNTIME} for kind,folder in [('release',release),('profile',profile)]},
      'artifacts':{kind:{'path':p.relative_to(private).as_posix(),'sha256':sha(p)} for kind,p in [('release_tu',release_tu),('profile_tu',profile_tu),('source_map',mapfile)]}}
    manifest_file=private/'runner-receipt.json';write(manifest_file,manifest)
    return release,profile,manifest_file,mapping

def main(argv=None):
    ap=PublicArgumentParser(prog='run_markdown_owned_profile.py',description=__doc__);ap.add_argument('--ru-root',type=Path,required=True);ap.add_argument('--binary-dir',type=Path,required=True);ap.add_argument('--evidence-dir',type=Path,required=True);ap.add_argument('--cc',type=Path,required=True);ap.add_argument('--windres',type=Path,required=True)
    try:
        a=ap.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 1
    except Exception:
        print('MARKDOWN_OWNED_PROFILE_DIAGNOSTIC_COMPLETE=0')
        print('MARKDOWN_OWNED_PROFILE_FAILURE_CODE='+str(PUBLIC_PREPARE_FAILED))
        return 1
    stage=PUBLIC_PREPARE_FAILED
    evidence=None
    public=public_failure(stage)
    try:
        evidence=plain(a.evidence_dir).resolve(strict=True)
        require(evidence.is_dir())
        if sys.platform!='win32':
            public=public_failure(PUBLIC_UNSUPPORTED_HOST)
        else:
            # The raw logs, source map, paths and build receipt never leave this
            # fresh private directory, which is outside product bin and ZIP.
            private=Path(tempfile.mkdtemp(prefix='ru-markdown-owned-',dir=plain(ROOT/'build')))
            with (private/'preparation.log').open('xb') as stream:
                sink=PrivateOutput(stream)
                with contextlib.redirect_stdout(sink),contextlib.redirect_stderr(sink):
                    release,profile,receipt,_=prepare(a.ru_root,a.binary_dir,a.cc,a.windres,private)
                    from run_markdown_phase_profile import run_pair
                    stage=PUBLIC_RUN_FAILED
                    summary=run_pair(receipt,ROOT,release,profile,private/'runs')
                    stage=PUBLIC_PROJECTION_FAILED
                    public=public_projection(summary,sha(ROOT/'native/markdown_phase_profile.h'))
    except (Exception,SystemExit):
        public=public_failure(stage)
    try:
        require(evidence is not None)
        publish_public(evidence,public)
    except Exception:
        print('MARKDOWN_OWNED_PROFILE_DIAGNOSTIC_COMPLETE=0')
        print('MARKDOWN_OWNED_PROFILE_FAILURE_CODE='+str(PUBLIC_WRITE_FAILED))
        return 1
    print('MARKDOWN_OWNED_PROFILE_DIAGNOSTIC_COMPLETE='+str(public['passed']))
    if not public['passed']:
        print('MARKDOWN_OWNED_PROFILE_FAILURE_CODE='+str(public['failure_code']))
    return 0 if public['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
