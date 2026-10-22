"""Explicit experiment build activation; no default product behavior change.

Both A/B arms compile the same manifest/source/compiler. The only materialized
AST change is the reviewed enabled fact in markdown_syntax; its exact source and
compiled-text hashes are receipted. No source file is rewritten or hidden C edit.
"""
from pathlib import Path
import hashlib

SYNTAX='src/markdown_syntax.ru'
MANIFEST='experiments/markdown-dense-manifest.json'
DRIVER='tools/markdown_dense_build.py'
OFF="_密扫描策略 取 {'enabled':假}."
ON="_密扫描策略 取 {'enabled':真}."
EXPECTED = {'src/markdown_syntax.ru': 'bd844ff57b5de0d62f1aebb646d7e4d5c5601ee21d1943679df597e40af4bae8', 'src/markdown_policy.ru': '92b379312ea77bb442e09d58bf4543e2c38559249c5ad69818804232070da384', 'src/markdown_dense.ru': '173e80795914e8beb815eb41567b64b7b8c9fca142d80c0ac996e1a2cd951f8e', 'src/markdown_ascii_kernel.ru': 'cbc8a532cc5de0b863985b70225e176a1c39895401f13e349f07bff4419ad22a', 'experiments/markdown-dense-manifest.json': '5d519d4d5082ca09c6f3662d8a9b46ea463167cf68d4268c369091aaa453438a'}

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def require(value):
    if not value:raise ValueError('markdown_dense_experiment_rejected')

def plain(root,relative):
    root=root.resolve();p=root/relative
    require(p.is_file() and not p.is_symlink() and p.stat().st_nlink==1)
    require(all(not x.is_symlink() for x in (p,*p.parents)))
    require(p.resolve().is_relative_to(root))
    return p

def expected_receipt(root,manifest,arm):
    root=Path(root).resolve();manifest=Path(manifest).resolve()
    require(arm in ('ordinary','dense'))
    require(manifest==plain(root,MANIFEST).resolve())
    for rel,want in EXPECTED.items():require(sha(plain(root,rel))==want)
    source=plain(root,SYNTAX).read_text(encoding='utf-8')
    require(source.count(OFF)==1 and ON not in source)
    compiled=source.replace(OFF,ON) if arm=='dense' else source
    return {'schema':1,'arm':arm,'enabled':arm=='dense','manifest':MANIFEST,
            'input_sha256':dict(EXPECTED),'driver_sha256':sha(plain(root,DRIVER)),
            'syntax_compiled_sha256':hashlib.sha256(compiled.encode()).hexdigest(),
            'source_patch_count':int(arm=='dense')},compiled

def prepare_graph(root,graph,manifest,arm):
    from rulang.frontend import parse
    receipt,compiled=expected_receipt(root,manifest,arm)
    key=str((Path(root)/SYNTAX).resolve())
    require(not hasattr(graph,'_markdown_dense_experiment'))
    require(key in graph and graph.sources[key]==Path(key).read_text(encoding='utf-8'))
    targets=[n for n in graph[key] if n.kind=='bind' and n.data.get('name')=='_密扫描策略']
    replacements=[n for n in parse(compiled) if n.kind=='bind' and n.data.get('name')=='_密扫描策略']
    require(len(targets)==len(replacements)==1)
    old=targets[0].data['expr'];require(old.kind=='map' and len(old.data['entries'])==1)
    field,value=old.data['entries'][0]
    require(field.kind=='string' and field.data['value']=='enabled' and value.kind=='fact' and value.data['value'] is False)
    targets[0].data['expr']=replacements[0].data['expr']
    graph.sources[key]=compiled
    graph._markdown_dense_experiment=receipt
    return receipt

def verify_receipt(root,manifest,arm,receipt):
    expected,_=expected_receipt(root,manifest,arm)
    require(receipt==expected)
