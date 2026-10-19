#!/usr/bin/env python3
"""Build-time helper only. The distributed app does not execute Python."""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, sys, time, zipfile
from package import (DEPENDENCIES, RESOURCE_INPUTS, NATIVE_HELPER_NAME, NATIVE_COMPILE_SOURCES,
                     NATIVE_BUILD_DRIVERS, NATIVE_CFLAGS, NATIVE_LINK_LIBRARIES,
                     native_source_snapshot, native_build_key)
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCINTILLA_SHA256 = DEPENDENCIES['Scintilla.dll']['sha256']
LEXILLA_SHA256 = DEPENDENCIES['Lexilla.dll']['sha256']
BASELINE_TREE = 'a770e367e84d87a0d2fcb6d49ea6f06da2dbe4ba'

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def run(args, **kw):
    print('+', ' '.join(map(str,args)), flush=True)
    subprocess.run(list(map(str,args)), check=True, **kw)
def git(root, *args):
    return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()

def source_snapshot():
    # Imported test helpers are build inputs too. Every executable is tied to
    # one common source/test snapshot, including helpers without an entry point.
    return {p.relative_to(ROOT).as_posix(): sha(p)
            for folder in ('src', 'tests') for p in sorted((ROOT / folder).glob('*.ru'))} | native_source_snapshot(ROOT)

def build_input_paths(console):
    # Native console fixtures must use the same common-controls v6 activation
    # context as the GUI. GetWindowSubclass is unavailable without this manifest.
    return RESOURCE_INPUTS + (() if console else ('packaging/diagnostic_launcher.c',))

def compile_resources(windres, build):
    resource = build / 'app-resource.o'
    run([windres, '-I', ROOT / 'packaging', ROOT / 'packaging/app.rc', resource])
    return resource

def native_build_inputs(cc, name):
    compiler = Path(shutil.which(cc) or cc).resolve(strict=True)
    version = subprocess.check_output([str(compiler), '--version'], timeout=30)
    return {'output_name': name, 'compile_sources': list(NATIVE_COMPILE_SOURCES[name]),
            'source_sha256': native_source_snapshot(ROOT),
            'driver_sha256': {relative: sha(ROOT / relative) for relative in NATIVE_BUILD_DRIVERS},
            'compiler_path': str(compiler), 'compiler_sha256': sha(compiler),
            'compiler_version_sha256': hashlib.sha256(version).hexdigest(),
            'compiler_flags': list(NATIVE_CFLAGS), 'link_libraries': list(NATIVE_LINK_LIBRARIES)}


def build_native_helpers(cc, build):
    cache = build / 'native-helper'
    if cache.is_symlink():
        raise RuntimeError('Refusing a linked native helper cache directory.')
    cache.mkdir(parents=True, exist_ok=True)
    results = {}
    for name in NATIVE_COMPILE_SOURCES:
        inputs = native_build_inputs(cc, name)
        key = native_build_key(inputs)
        output = cache / name
        receipt_path = cache / (Path(name).stem + '.native-build.json')
        try:
            if receipt_path.is_symlink():
                raise ValueError('Linked helper cache receipt is never trusted')
            cached = json.loads(receipt_path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            cached = {}
        if (output.is_file() and not output.is_symlink() and cached.get('name') == name and
                cached.get('build_inputs') == inputs and cached.get('build_key') == key and
                cached.get('dll_sha256') == sha(output)):
            results[name] = cached
            continue
        pending = cache / (Path(name).stem + '.pending.dll')
        pending.unlink(missing_ok=True)
        command = [inputs['compiler_path'], *NATIVE_CFLAGS, *NATIVE_COMPILE_SOURCES[name],
                   '-o', str(pending), *('-l' + name for name in NATIVE_LINK_LIBRARIES)]
        try:
            run(command, cwd=ROOT, timeout=600)
            if native_build_inputs(cc, name) != inputs:
                raise RuntimeError('Native helper inputs changed during compilation; no cache receipt published.')
            receipt = {'schema': 1, 'name': name, 'build_inputs': inputs,
                       'build_key': key, 'dll_sha256': sha(pending), 'compiler_command': command}
            os.replace(pending, output)
            pending_receipt = receipt_path.with_suffix('.json.pending')
            pending_receipt.unlink(missing_ok=True)
            pending_receipt.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
            os.replace(pending_receipt, receipt_path)
            results[name] = receipt
        finally:
            pending.unlink(missing_ok=True)
    return results


def copy_native_helpers(build, destination):
    for name in NATIVE_COMPILE_SOURCES:
        for filename in (name, Path(name).stem + '.native-build.json'):
            source = build / 'native-helper' / filename
            target = destination / filename
            if source.is_symlink() or target.is_symlink():
                raise RuntimeError('Refusing a linked native helper binary or receipt.')
            if source.resolve() != target.resolve():
                shutil.copy2(source, target)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--ru-root', type=Path, required=True)
    ap.add_argument('--cc', required=True)
    ap.add_argument('--cxx', required=True)
    ap.add_argument('--windres', required=True)
    ap.add_argument('--ar', required=True)
    ap.add_argument('--ranlib', required=True)
    ap.add_argument('--allow-toolchain-tree', default=BASELINE_TREE)
    ap.add_argument('--source',type=Path,default=ROOT/'src/main.ru')
    ap.add_argument('--output',type=Path,default=ROOT/'build/ru_notepad.exe')
    ap.add_argument('--console',action='store_true')
    ap.add_argument('--skip-scintilla',action='store_true')
    ap.add_argument('--skip-lexilla',action='store_true')
    args=ap.parse_args()
    ru=args.ru_root.resolve()
    tree=git(ru,'rev-parse','HEAD^{tree}')
    if tree != args.allow_toolchain_tree:
        raise SystemExit(f'Toolchain tree mismatch: {tree}; expected {args.allow_toolchain_tree}')
    if git(ru,'status','--porcelain'):
        raise SystemExit('Toolchain contains uncommitted changes; use a reviewed pinned snapshot.')
    audit=subprocess.run([sys.executable,str(ROOT/'tools/check_native_arguments.py'),'--ru-root',str(ru)],text=True,stdout=subprocess.PIPE)
    if audit.returncode:
        print(audit.stdout);raise SystemExit('Native argument audit failed; refusing build.')
    for dependency in DEPENDENCIES.values():
        archive=ROOT/'vendor/downloads'/dependency['archive']
        if not archive.is_file() or sha(archive)!=dependency['sha256']:
            raise SystemExit(f'Missing or mismatched official {dependency["folder"]} source archive.')
        # Make may add objects, but all original source bytes must remain pinned.
        with zipfile.ZipFile(archive) as pinned:
            for member in pinned.infolist():
                if not member.is_dir():
                    source=ROOT/'vendor'/member.filename
                    if source.is_symlink() or not source.is_file() or source.read_bytes()!=pinned.read(member):
                        raise SystemExit(f'Dependency source differs from pinned archive: {member.filename}')
    build=ROOT/'build'; build.mkdir(exist_ok=True)
    if not args.skip_scintilla:
        run(['make','-j2','-C',ROOT/'vendor/scintilla/win32','../bin/Scintilla.dll',
             'CXX='+args.cxx,'WINDRES='+args.windres,'AR='+args.ar,'RANLIB='+args.ranlib])
    if not args.skip_lexilla:
        run(['make','-j2','-C',ROOT/'vendor/lexilla/src','../bin/lexilla.dll',
             'windir=C:/Windows','CXX='+args.cxx,'WINDRES='+args.windres,
             'AR='+args.ar,'RANLIB='+args.ranlib,
             'LDFLAGS=-shared -static -mwindows -Wl,--kill-at -s'])
    sys.path.insert(0,str(ru))
    from rulang.frontend import parse
    from rulang.modules import load_module_graph
    from rulang.compiler import Compiler
    source=args.source.resolve()
    snapshot=source_snapshot()
    build_inputs={rel:sha(ROOT/rel) for rel in build_input_paths(args.console)}
    entry_sha=sha(source)
    text=source.read_text(encoding='utf-8-sig')
    program=parse(text)
    graph=load_module_graph(str(source),program)
    graph.sources[graph.root]=text
    started=time.monotonic()
    native_helpers=build_native_helpers(args.cc, build)
    code=Compiler(program,graph.root,modules=graph,allow_native=True).compile()
    emitted=build/(source.stem+'.c')
    emitted.write_text(code,encoding='utf-8')
    translation=emitted
    if not args.console:
        translation=build/(source.stem+'-gui.c')
        launcher=(ROOT/'packaging/diagnostic_launcher.c').read_text()
        translation.write_text('#define main ru_program_main\n'+code+'\n#undef main\n'+launcher,encoding='utf-8')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    res=compile_resources(args.windres,build)
    cmd=[args.cc,'-std=c99','-O2','-Wall','-Wextra','-Wno-unused-function','-static-libgcc',str(translation),'-o',str(args.output),'-lm',str(res)]
    if not args.console:
        cmd += ['-mwindows','-lshell32','-luser32']
    run(cmd,timeout=600)
    if build_inputs != {rel:sha(ROOT/rel) for rel in build_inputs}:
        raise SystemExit('Launcher/resource inputs changed during build; no receipt published.')
    if any(native_build_inputs(args.cc, name) != receipt['build_inputs']
           for name, receipt in native_helpers.items()):
        raise SystemExit('Native helper inputs changed during executable build; no receipt published.')
    if snapshot != source_snapshot() or entry_sha != sha(source):
        raise SystemExit('Source changed during build; no verified receipt will be published. Rebuild from a stable snapshot.')
    shutil.copy2(ROOT/'vendor/scintilla/bin/Scintilla.dll',args.output.parent/'Scintilla.dll')
    shutil.copy2(ROOT/'vendor/lexilla/bin/lexilla.dll',args.output.parent/'Lexilla.dll')
    copy_native_helpers(build, args.output.parent)
    receipt={'schema':1,'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
             'ru_commit':git(ru,'rev-parse','HEAD'),'ru_tree':tree,
             'app_version':(ROOT/'VERSION').read_text().strip(),
             'scintilla_version':'5.6.7','scintilla_archive_sha256':SCINTILLA_SHA256,
             'lexilla_version':'5.5.4','lexilla_archive_sha256':LEXILLA_SHA256,
             'entry_source':source.relative_to(ROOT).as_posix(),'entry_sha256':entry_sha,
             'source_sha256':snapshot,
             'build_input_sha256':build_inputs,
             'translation_unit_sha256':sha(translation),'translation_unit_bytes':translation.stat().st_size,
             'exe_sha256':sha(args.output),'exe_bytes':args.output.stat().st_size,
             'dll_sha256':sha(args.output.parent/'Scintilla.dll'),
             'lexilla_dll_sha256':sha(args.output.parent/'Lexilla.dll'),
             'native_helper_sha256':sha(args.output.parent/NATIVE_HELPER_NAME),
             'native_helper_build_key':native_helpers[NATIVE_HELPER_NAME]['build_key'],
             'generated_c_sha256':sha(emitted),'generated_c_bytes':emitted.stat().st_size,
             'seconds':time.monotonic()-started,'runtime_tested':False,
             'compiler_command':cmd}
    (args.output.with_suffix('.build.json')).write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))

if __name__=='__main__': main()
