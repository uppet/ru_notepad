"""Bind verified baseline build and verified stock package before GUI launch."""
import argparse, json, hashlib, subprocess
from pathlib import Path
import build_baseline as b
import acquire_npp as n


def seal(root,compiler,cc,ru,npp,npp_receipt):
    source=b.checkout(root,b.BASELINE);b.verify_compiler(compiler)
    p=b.load_protocol(root);build=b.full_receipt(root,ru,cc,p)
    record=b.read(ru/'comparison-build.json')
    nonruntime=b.nonruntime_build(root,ru,p)
    b.need(record['nonruntime_build_sha256']==nonruntime)
    b.need(record['tracked_source_sha256']==source)
    b.need(record['build_receipt_sha256']==b.sha(ru/'ru_notepad.build.json'))
    b.need(record['native_receipt_sha256']==b.sha(ru/'RuSyntax.native-build.json'))
    b.need(record['compiler_sha256']==b.sha(b.compiler_file(cc)))
    b.need(record['baseline_commit']==b.BASELINE and record['compiler_commit']==b.COMPILER and record['compiler_tree']==b.COMPILER_TREE)
    b.need(record['runtime']['ru']=={name:b.sha(b.under(ru,name)) for name in p.base.RUNTIME_NAMES})
    b.need(record['generated_c_sha256']==build['generated_c_sha256'] and record['translation_unit_sha256']==build['translation_unit_sha256'])
    b.need(record['build_input_sha256']==build['build_input_sha256'])
    b.verify_tools(cc.parent,record['tools'])
    for name,size,h,folder in b.ARCHIVES:
        archive=b.under(root,'vendor/downloads/'+name);b.need(archive.stat().st_size==size and b.sha(archive)==h)
    package=b.read(npp_receipt)
    b.need(package['archive_sha256']==n.PINS['npp.8.9.8.1.portable.x64.zip'][1])
    b.need(package['executed'] is False)
    actual={x.relative_to(npp).as_posix():b.sha(b.plain(x)) for x in sorted(npp.rglob('*')) if x.is_file()}
    b.need(actual==package['files'] and len(actual)==package['file_count'])
    b.need(actual['notepad++.exe']==package['executable_sha256'])
    for marker in ('doLocalConf.xml','disableNppAutoUpdate.xml'):
        b.need(b.sha(b.under(npp,marker)) == actual[marker])
    runtime={'ru':{name:b.sha(b.under(ru,name)) for name in p.base.RUNTIME_NAMES},
             'npp':{name:h for name,h in actual.items() if '/' not in name}}
    result={'schema':1,'baseline_commit':b.BASELINE,'compiler_commit':b.COMPILER,'compiler_tree':b.COMPILER_TREE,
            'nonruntime_build_sha256':nonruntime,'runtime':runtime,'npp_all_files_sha256':actual,'npp_archive_sha256':package['archive_sha256'],
            'baseline_source_snapshot_sha256':b.digest(source),'build_provenance_sha256':b.sha(ru/'comparison-build.json'),
            'build_receipt_sha256':b.sha(ru/'ru_notepad.build.json'),'native_receipt_sha256':b.sha(ru/'RuSyntax.native-build.json'),'npp_receipt_sha256':b.sha(npp_receipt),
            'tools':{name:{'sha256':v['sha256'],'version_stdout_sha256':v['version_stdout_sha256'],'path_sha256':hashlib.sha256(v['path'].encode()).hexdigest()} for name,v in record['tools'].items()},'npp_version':[8,9,8,1],
            'generated_c_sha256':build['generated_c_sha256'],'translation_unit_sha256':build['translation_unit_sha256'],
            'native_helper_build_key':build['native_helper_build_key'],'compiler_sha256':record['compiler_sha256'],
            'compiler_version_sha256':record['compiler_version_sha256'],'build_input_sha256':build['build_input_sha256']}
    # Apply the exact runtime gate now, not only after successful sealing.
    from feasibility import verify_receipt
    verify_receipt(result,ru,npp)
    return result


def main():
    a=argparse.ArgumentParser()
    for name in ('baseline','compiler','cc','ru-dir','npp-dir','npp-receipt','output'):a.add_argument('--'+name,type=Path,required=True)
    x=a.parse_args();b.host_guard()
    result=seal(x.baseline.absolute(),x.compiler.absolute(),x.cc.absolute(),x.ru_dir.absolute(),x.npp_dir.absolute(),x.npp_receipt.absolute())
    with x.output.open('x') as stream:json.dump(result,stream,sort_keys=True)

if __name__ == '__main__':
    try:
        result = main()
    except Exception:
        import sys
        print('COMPARISON_FAILURE_CODE=3', file=sys.stderr)
        raise SystemExit(1)
    raise SystemExit(result or 0)
