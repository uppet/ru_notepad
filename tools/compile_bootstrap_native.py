#!/usr/bin/env python3
"""Pinned native-only host wrapper; application parsing belongs to stage3 EXE."""
import argparse
from contextlib import contextmanager, ExitStack
import importlib
import inspect
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bootstrap_provenance import require, sha, checked

CORE_COMMIT = '26cc8a210d5cef2bd8ab37b6c270833884ea39a5'
CORE_TREE = '847c68b4569e12ffaf8ae4c5b500fdbaad7b801d'
POISON_ENTRIES = ('frontend.parse', 'modules.load_module_graph', 'NativeCPlan.__init__',
                  'NativeCPlan.emit_c', 'Compiler.compile', 'LLVMCompiler.compile', 'cli.build')
API_PARAMETERS = ('compiler', 'source', 'output', 'toolchain', 'emit_llvm', 'keep_frontend',
                  'interpreter_host', 'allow_native', 'proof', 'source_roots', 'linker')
SCHEMA = 'ru-notepad-native-wrapper-v1'


def identity(path):
    path=Path(path)
    require(path.is_file() and not any(p.is_symlink() for p in [path,*path.parents]), 'missing/linked wrapper input')
    return {'path':str(path.resolve()),'sha256':sha(path),'size':path.stat().st_size}


def verify_core(root):
    def git(*args):
        return subprocess.check_output(['git','-C',str(root),*args],text=True,encoding='utf-8').strip()
    require(git('rev-parse','HEAD') == CORE_COMMIT and git('rev-parse','HEAD^{tree}') == CORE_TREE,
            'native wrapper requires exact reviewed core commit/tree')
    require(not git('status','--porcelain'), 'native wrapper core must be clean')
    checked(root,'tools/bootstrap.py')


def verify_api(function):
    parameters=inspect.signature(function).parameters
    require(tuple(parameters) == API_PARAMETERS, 'reviewed compile_native API changed')
    for name in API_PARAMETERS[:4]:
        require(parameters[name].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD, 'native positional API changed')
    for name in API_PARAMETERS[4:]:
        require(parameters[name].kind == inspect.Parameter.KEYWORD_ONLY, 'native keyword API changed')
    require(parameters['keep_frontend'].default is False and parameters['allow_native'].default is False
            and parameters['interpreter_host'].default is False, 'native capability defaults changed')


@contextmanager
def poison_frontends(targets):
    require(tuple(label for label,_,_ in targets) == POISON_ENTRIES, 'incomplete Python frontend poison inventory')
    attempts=[]
    with ExitStack() as stack:
        for label,owner,name in targets:
            original=getattr(owner,name)
            require(callable(original), 'missing frontend poison target')
            def denied(*args,_label=label,**kwargs):
                attempts.append(_label)
                raise RuntimeError('Python application frontend forbidden: '+_label)
            stack.enter_context(patch.object(owner,name,denied))
            # NativeCPlan.source is an existing alias of emit_c, not an eighth
            # permitted route around the same logical code-generation entry.
            if label == 'NativeCPlan.emit_c' and getattr(owner,'source',None) is original:
                stack.enter_context(patch.object(owner,'source',denied))
        yield attempts
        require(not attempts, 'Python application frontend was attempted')


def load_core(root):
    sys.path.insert(0,str(root))
    modules={name:importlib.import_module(name) for name in
             ('rulang.frontend','rulang.modules','rulang.native_c','rulang.compiler',
              'rulang.llvm_compiler','rulang.cli','tools.bootstrap')}
    require(all(Path(module.__file__).resolve().is_relative_to(root) for module in modules.values()),
            'native wrapper imported a different core')
    targets=(('frontend.parse',modules['rulang.frontend'],'parse'),
             ('modules.load_module_graph',modules['rulang.modules'],'load_module_graph'),
             ('NativeCPlan.__init__',modules['rulang.native_c'].NativeCPlan,'__init__'),
             ('NativeCPlan.emit_c',modules['rulang.native_c'].NativeCPlan,'emit_c'),
             ('Compiler.compile',modules['rulang.compiler'].Compiler,'compile'),
             ('LLVMCompiler.compile',modules['rulang.llvm_compiler'].LLVMCompiler,'compile'),
             ('cli.build',modules['rulang.cli'],'build'))
    return modules['tools.bootstrap'],targets


def validate_retained(proof, output):
    expected={'metadata':output.with_name(output.name+'.metadata.c'),
              'frontend_ir':output.with_name(output.name+'.frontend.ll')}
    for key,path in expected.items():
        record={'path':str(path.resolve()),'sha256':sha(path)}
        require(proof.get('artifacts',{}).get(key) == record, 'retained native artifact mismatch: '+key)
        digest_key='metadata_sha256' if key=='metadata' else 'source_ir_sha256'
        require(proof.get(digest_key) == record['sha256'], 'retained native digest mismatch: '+key)
        identity(path)


def validate_wrapper_receipt(proof, source, compiler, binary, proof_path, frozen):
    validate_retained(proof,binary)
    path=binary.with_name(binary.name+'.native-wrapper.json')
    record=json.loads(path.read_text(encoding='utf-8'))
    require(set(record)=={'schema','compiler_commit','compiler_tree','source','compiler','driver','proof',
                          'metadata','frontend_ir','poison_entries','python_frontend_attempts'}, 'unknown native wrapper receipt')
    require(record['schema']==SCHEMA and record['compiler_commit']==CORE_COMMIT and record['compiler_tree']==CORE_TREE
            and record['poison_entries']==list(POISON_ENTRIES) and record['python_frontend_attempts']==[],
            'native wrapper poison proof missing or changed')
    driver=Path(__file__).resolve()
    require(frozen.get(str(driver))==sha(driver),'native wrapper not in frozen source')
    paths={'source':source,'compiler':compiler,'driver':driver,'proof':proof_path,
           'metadata':binary.with_name(binary.name+'.metadata.c'),
           'frontend_ir':binary.with_name(binary.name+'.frontend.ll')}
    for key,file in paths.items():
        require(record[key]==identity(file),'native wrapper identity mismatch: '+key)
    return identity(path)


def compile_entry(args):
    require(sys.platform == 'win32', 'real Windows required for native wrapper')
    root=args.ru_root.resolve(); source=args.source.resolve(); output=args.output.resolve()
    verify_core(root)
    bootstrap,targets=load_core(root);verify_api(bootstrap.compile_native)
    with poison_frontends(targets) as attempts:
        toolchain=bootstrap.LLVMToolchain(str(args.llvm_clang.resolve()))
        evidence=bootstrap.compile_native(args.compiler.resolve(),source,output,toolchain,
            emit_llvm=args.emit_llvm.resolve(),keep_frontend=True,interpreter_host=False,
            allow_native=True,proof=args.proof.resolve(),source_roots=(args.source_root.resolve(),),
            linker=args.linker.resolve())
    proof=json.loads(args.proof.read_text(encoding='utf-8'))
    require(proof == evidence and not attempts, 'native wrapper proof/poison mismatch')
    validate_retained(proof,output);verify_core(root)
    receipt={'schema':SCHEMA,'compiler_commit':CORE_COMMIT,'compiler_tree':CORE_TREE,
             'source':identity(source),'compiler':identity(args.compiler),
             'driver':identity(Path(__file__)),'proof':identity(args.proof),
             'metadata':identity(output.with_name(output.name+'.metadata.c')),
             'frontend_ir':identity(output.with_name(output.name+'.frontend.ll')),
             'poison_entries':list(POISON_ENTRIES),'python_frontend_attempts':[]}
    target=output.with_name(output.name+'.native-wrapper.json')
    with target.open('x',encoding='utf-8',newline='\n') as stream:
        stream.write(json.dumps(receipt,indent=2)+'\n')
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('ru-root','source','source-root','compiler','llvm-clang','emit-llvm','proof','linker','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    compile_entry(parser.parse_args())


if __name__=='__main__':main()
