#!/usr/bin/env python3
"""Read-only comparison of retained native metadata with a reviewed source oracle.

The oracle is produced independently during development and frozen in the app
snapshot. This validator does not parse Ru source or generate expected ABI data.
"""
import hashlib
import json
from pathlib import Path
import re

from bootstrap_provenance import checked, require, sha
from compile_bootstrap_native import CORE_COMMIT, CORE_TREE, validate_retained

SCHEMA='ru-notepad-application-native-oracle-v1'
SCOPE='independent Python development oracle, not stage3/LLVM/Windows evidence'
ORACLE_PATH='packaging/application-native-oracle.json'
C_TYPES={'无值':'void','i8':'int8_t','u8':'uint8_t','i16':'int16_t','u16':'uint16_t',
         'i32':'int32_t','u32':'uint32_t','i64':'int64_t','u64':'uint64_t',
         'intptr':'intptr_t','uintptr':'uintptr_t','f32':'float','f64':'double','指针':'void*'}
APPLICATION_BASE_COMMIT='b79baa824b0a48f564ad95447e4ce64cc5b5911b'
TOP_KEYS={'schema','scope','application_base_commit','compiler_commit','compiler_tree','entry','modules','shapes','callbacks'}


def unique_json(data):
    def pairs(items):
        out={}
        for key,value in items:
            require(key not in out,'duplicate oracle JSON key');out[key]=value
        return out
    return json.loads(data,object_pairs_hook=pairs)


def ctype(value):
    return re.sub(r'\s+','',value)


def shapes(rows):
    require(isinstance(rows,list),'oracle shapes must be a list')
    out=[]
    for row in rows:
        require(isinstance(row,dict) and set(row)=={'result','parameters'}
                and row['result'] in C_TYPES and isinstance(row['parameters'],list)
                and all(isinstance(item,str) and item in C_TYPES and item!='无值' for item in row['parameters']),
                'invalid oracle ABI shape')
        out.append((C_TYPES[row['result']],tuple(C_TYPES[item] for item in row['parameters'])))
    require(len(set(out))==len(out),'duplicate oracle ABI shape')
    return set(out)


def metadata_sets(text, expected_modules):
    rows=re.findall(r'^typedef (.+) \(\*RuNativeCall_(\d+)\)\(([^\n]*)\);$',text,re.M)
    require(len(rows)==len(re.findall(r'^typedef .*RuNativeCall_',text,re.M)), 'unparsed native typedef')
    mapping={}
    for result,index,parameters in rows:
        index=int(index)
        require(index not in mapping,'duplicate native typedef ID')
        mapping[index]=(ctype(result),() if parameters=='void' else tuple(ctype(x) for x in parameters.split(',')))
    require(set(mapping)==set(range(len(mapping))) and len(set(mapping.values()))==len(mapping),
            'native typedef IDs/shapes must be unique and complete')
    callback_rows=re.findall(r'^static RuNativeCall_(\d+) const ru_native_callbacks_(\d+)\[1024\] = \{$',text,re.M)
    require(len(callback_rows)==len(re.findall(r'^static RuNativeCall_\d+ const ru_native_callbacks_',text,re.M)),
            'unparsed native callback table')
    callbacks=[]
    for first,second in callback_rows:
        index=int(first)
        require(first==second and index in mapping and index not in callbacks,'invalid/duplicate callback ID')
        callbacks.append(index)
        slots=[int(slot) for slot in re.findall(r'^static .+ ru_native_callback_'+str(index)+r'_(\d+)\([^\n]*\) \{$',text,re.M)]
        require(len(slots)==1024 and set(slots)==set(range(1024)),'incomplete callback thunk family')
    all_families={int(index) for index in re.findall(r'^static .+ ru_native_callback_(\d+)_\d+\(',text,re.M)}
    require(all_families==set(callbacks),'unlisted callback family')
    bodies=re.findall(r'static Val boot_m_(\d+)_init\(void\) \{(.*?\nboot_m_\1_state=2;[^\n]*)',text,re.S)
    ids=[int(index) for index,_ in bodies]
    require(len(ids)==expected_modules and set(ids)==set(range(expected_modules)), 'module initializer inventory differs')
    require(len(re.findall(r'static Val boot_m_\d+_init\(void\) \{',text))==expected_modules,
            'unparsed/extra module initializer')
    require(text.count('ru_native_builtins(ru_practical_builtins())')==expected_modules,
            'module native capability inventory differs')
    for index,body in bodies:
        state='boot_m_'+index+'_state=1;'
        require(body.count(state)==1 and 'ru_native_callback_depth' in body
                and body.index('ru_native_callback_depth')<body.index(state),
                'module first import lacks pre-state callback guard')
    return set(mapping.values()),{mapping[index] for index in callbacks}


def verify_application_oracle(proof, app_root, ru_root, source_hashes, binary):
    app_root,ru_root,binary=Path(app_root),Path(ru_root),Path(binary)
    path=checked(app_root,ORACLE_PATH)
    require(source_hashes['app_source'].get(ORACLE_PATH)==sha(path),'oracle not frozen in application snapshot')
    oracle=unique_json(path.read_text(encoding='utf-8'))
    require(isinstance(oracle,dict) and set(oracle)==TOP_KEYS and oracle['schema']==SCHEMA and oracle['scope']==SCOPE,
            'unknown application oracle contract')
    require(oracle['application_base_commit']==APPLICATION_BASE_COMMIT
            and oracle['compiler_commit']==CORE_COMMIT and oracle['compiler_tree']==CORE_TREE
            and oracle['entry']=='src/main.ru','wrong application oracle source scope')
    require(proof.get('source')==str((app_root/'src/main.ru').resolve()),'main oracle cannot validate another entry')
    expected={}
    require(isinstance(oracle['modules'],list) and bool(oracle['modules']),'missing oracle modules')
    for row in oracle['modules']:
        require(isinstance(row,dict) and set(row)=={'scope','path','sha256','git_blob'} and row['scope'] in ('app','compiler'),
                'invalid oracle module')
        root,key=(app_root,'app_source') if row['scope']=='app' else (ru_root,'ru_source')
        file=checked(root,row['path']);data=file.read_bytes();name=str(file.resolve())
        require(name not in expected,'duplicate oracle module')
        require(source_hashes[key].get(row['path'])==row['sha256']==hashlib.sha256(data).hexdigest()
                and row['git_blob']==hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest(),
                'oracle module bytes differ from frozen source')
        expected[name]={'path':name,'sha256':row['sha256'],'size':len(data)}
    dependencies=proof.get('dependencies')
    require(isinstance(dependencies,list) and len(dependencies)==len(expected)
            and all(isinstance(row,dict) and row==expected.get(row.get('path')) for row in dependencies)
            and len({row['path'] for row in dependencies})==len(expected), 'application dependency set differs from oracle')
    validate_retained(proof,binary)
    metadata=Path(proof['artifacts']['metadata']['path'])
    require(metadata.stat().st_size<=64*1024*1024,'application metadata exceeds bounded oracle input')
    actual_shapes,actual_callbacks=metadata_sets(metadata.read_text(encoding='utf-8'),len(expected))
    expected_shapes,expected_callbacks=shapes(oracle['shapes']),shapes(oracle['callbacks'])
    require(expected_callbacks<=expected_shapes and actual_shapes==expected_shapes and actual_callbacks==expected_callbacks,
            'application native ABI sets differ from independent oracle')
    return {'schema':'ru-notepad-application-native-oracle-validation-v1','oracle_sha256':sha(path),
            'metadata_sha256':sha(metadata),'modules':len(expected),'shapes':len(actual_shapes),
            'callbacks':len(actual_callbacks),'status':'passed'}
