#!/usr/bin/env python3
"""Independent Unicode byte-span oracle against production Ru, interpreter and C.

Python re is used only for the explicitly shared subset. Mixed CR/LF anchors and
scope boundaries use handwritten expected spans, never Python's anchor policy.
No compiler limits are raised. This is portable evidence, not Windows evidence.
"""
import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PIN = 'c3bb177c6a15e90821e5495cc74b0fdfc39b893a'
TREE = '5dedbf06f9fb6e00fbfe779b33f172aa35b61334'


def verify_compiler(root):
    def git(*arguments):
        return subprocess.check_output(
            ['git', '-C', str(root), *arguments], text=True, encoding='utf-8').strip()
    commit, tree = git('rev-parse', 'HEAD'), git('rev-parse', 'HEAD^{tree}')
    if commit != PIN or tree != TREE:
        raise RuntimeError(f'Wrong compiler identity: commit={commit}, tree={tree}')
    if git('status', '--porcelain=v1', '--untracked-files=all'):
        raise RuntimeError('Compiler source must be clean, including untracked files')
    return commit


def runtime_output(stdout, stderr, label):
    if stderr:
        raise AssertionError(f'{label}: unexpected runtime stderr:\n{stderr}')
    if re.search(r'\b(?:FAIL|SKIP)\b', stdout, re.IGNORECASE):
        raise AssertionError(f'{label}: failure or skip marker in runtime output')


def executable_path(directory, stem):
    return directory / (stem + ('.exe' if os.name == 'nt' else ''))


def gcc_path():
    compiler = shutil.which('gcc')
    if not compiler:
        raise RuntimeError('A gcc C compiler must be available on PATH')
    return compiler


COMMON = [
    ('first-arm', '(a|ab)', 'ab'), ('long-arm', '(ab|a)', 'ab'),
    ('saved-end', '(abc|a)', 'abx'), ('later-start', '(abc|b)', 'zabx'),
    ('greedy-star', 'a*', 'aaab'), ('greedy-plus', 'a+', 'baaab'),
    ('greedy-question', 'ab?', 'abb'), ('empty-group', '()', 'a'),
    ('empty-arm', 'a|', 'b'), ('nullable-optional', '(a?)?', 'aaa'),
    ('empty-optional', '(|a)?', 'aaa'),
    ('backtrack-saved', '(ab|a)b?', 'ab'), ('no-match', 'xyz', 'abc'),
    ('empty-document', 'a*', ''), ('dot-emoji', '.', '😀'),
    ('unicode-offset', '😀+', '甲😀😀z'), ('ordinal-range', '[α-ω]+', 'xαβω!'),
    ('negated-class', '[^a-c]+', 'abc😀Z'), ('no-normalize', 'é', 'e\u0301'),
    ('combining', 'e.', 'xe\u0301'), ('case-sensitive', 'Ab', 'ab'),
    ('escaped-dot', r'\.', 'a.b'), ('escaped-controls', r'\n\t', 'x\n\t'),
    ('lazy-star', 'a*?', 'aaa'), ('lazy-plus', 'a+?', 'aaa'),
    ('lazy-question', 'a??', 'a'), ('noncapturing', '(?:ab|a)', 'ab'),
    ('ascii-digit', r'\d+', 'x123'), ('ascii-word', r'\w+', '!ab_2'),
    ('ascii-space', r'\s+', 'x \t\r\n'), ('category-class', r'[\dA]+', 'xA12'),
]
# name, pattern, full document, scalar scope start/end, absolute byte span or None
MANUAL = [
    ('dot-no-cr', '.', '\r', 0, 1, None), ('dot-no-lf', '.', '\n', 0, 1, None),
    ('cr-start', '^b', 'a\rb', 0, 3, (2, 3)),
    ('lf-start', '^b', 'a\nb', 0, 3, (2, 3)),
    ('crlf-start', '^b', 'a\r\nb', 0, 4, (3, 4)),
    ('crlf-no-middle-start', '^\\n', '\r\n', 0, 2, None),
    ('crlf-end', 'a$', 'a\r\nb', 0, 4, (0, 1)),
    ('crlf-no-middle-end', '\\r$', '\r\n', 0, 2, None),
    ('scope-not-start', '^b', 'ab', 1, 2, None),
    ('scope-not-end', 'a$', 'ab', 0, 1, None),
    ('scope-real-start', '^b', 'a\nbx', 2, 3, (2, 3)),
    ('scope-real-end', 'a$', 'xa\nb', 1, 2, (1, 2)),
    ('absolute-start', r'\Aa', 'ab', 0, 2, (0, 1)),
    ('absolute-no-scope-start', r'\Ab', 'ab', 1, 2, None),
    ('absolute-end', r'b\z', 'ab', 0, 2, (1, 2)),
    ('absolute-no-scope-end', r'a\z', 'ab', 0, 1, None),
    ('empty-eof', '$', 'a', 1, 1, (1, 1)),
    ('empty-not-eof', '$', 'ab', 1, 1, None),
    ('ascii-not-unicode-digit', r'\d', '١', 0, 1, None),
    ('ascii-not-unicode-word', r'\w', 'α', 0, 1, None),
    ('ascii-not-unicode-space', r'\s', '\u00a0', 0, 1, None),
]
REJECT = ['', 'a{2}', 'a{1,2}', 'a++', 'a*+', 'a?+', r'(a)\1', '(?=a)',
          '(?!a)', '(?<=a)', '(?i)a', r'\p{L}', r'\q', r'\b', '[', '(', ')',
          '[z-a]', '[]', '[^]', '*a', '+a', '?a', 'a**', '\\', '[a-\\q]']


def bytepos(text, at):
    return len(text[:at].encode('utf-8'))


def feeds(text, lo, hi, cuts):
    points = [lo] + list(cuts) + [hi]
    return [[text[a:b], bytepos(text, a), text[a-1:a] if a else '',
             text[b:b+1], b == hi] for a, b in zip(points, points[1:])]


def cases():
    rows = []
    samples = list(MANUAL)
    for name, pattern, text in COMMON:
        # Categories are explicitly ASCII in this product, not Python default.
        flags = re.ASCII if re.search(r'\\[dDsSwW]', pattern) else 0
        match = re.search(pattern, text, flags)
        span = None if match is None else tuple(bytepos(text, i) for i in match.span())
        samples.append((name, pattern, text, 0, len(text), span))
    for name, pattern, text, lo, hi, span in samples:
        # Whole chunk, every single cut, plus a scalar-at-a-time partition.
        partitions = [()] + [(i,) for i in range(lo+1, hi)]
        if hi-lo > 2:
            partitions.append(tuple(range(lo+1, hi)))
        partitions = list(dict.fromkeys(partitions))
        for split, cuts in enumerate(partitions):
            for budget in (1, 64):
                rows.append([f'{name}-s{split}-b{budget}', pattern, bytepos(text,lo),
                             bytepos(text,hi), bytepos(text,len(text)), feeds(text,lo,hi,cuts),
                             budget, 100000, 'no-match' if span is None else 'match',
                             -1 if span is None else span[0], -1 if span is None else span[1]])
    for i, pattern in enumerate(REJECT + ['a'*257, '('*17+'a'+')'*17, '['+'ab'*65+']']):
        rows.append([f'reject-{i}',pattern,0,0,0,[],1,100000,'compile-error',-1,-1])
    for i, pattern in enumerate(('(a?)*', '(|a)*', '(a|)*', '(a*)*', '()+', '(a?)+?', '(a?)*b')):
        rows.append([f'nullable-repeat-{i}',pattern,0,0,0,[],1,100000,'compile-error',-1,-1,'nullable_repeat'])
    for n in (16,32,64):
        for i, pattern in enumerate(('(a+)+$', '(a|aa)*b')):
            text = 'a'*n+'!'
            rows.append([f'linear-{i}-{n}',pattern,0,len(text),len(text),feeds(text,0,len(text),()),64,100000,'no-match',-1,-1])
    for name, pattern, text in [('max-query','a'*256,'a'*256),
                                 ('max-utf8-query','😀'*256,'😀'*256),
                                 ('max-depth','('*16+'a'+')'*16,'a'),
                                 ('max-class','['+'ab'*32+']','a')]:
        end=bytepos(text,len(text))
        rows.append([name,pattern,0,end,end,feeds(text,0,len(text),()),64,100000,'compile-ok',-1,-1])
    rows.extend([
        ['feed-too-large','a',0,257,257,[['a'*257,0,'','',True]],1,100000,'error',-1,-1],
        ['feed-wrong-offset','a',0,1,1,[['a',1,'','',True]],1,100000,'error',-1,-1],
        ['feed-missing-left-context','a',1,2,2,[['a',1,'','',True]],1,100000,'error',-1,-1],
        ['feed-missing-right-context','a',0,1,2,[['a',0,'','',True]],1,100000,'error',-1,-1],
    ])
    for i, (key, value) in enumerate([('count',0), ('count',513), ('start',999),
                                     ('op',[]), ('x',[]), ('y',[]), ('lo',[]),
                                     ('hi',[]), ('neg',[]), ('rangesHi',['a']),
                                     ('x',[999,-1]), ('op',['unknown','match'])]):
        rows.append([f'program-bounds-{i}','a',0,1,1,[['a',0,'','',True]],1,100000,'error',-1,-1,key,value])
    text = 'a'*32+'!'
    rows.append(['total-limit','(a|aa)*b',0,len(text),len(text),feeds(text,0,len(text),()),1,10,'limit',-1,-1])
    return rows


def ru_literal(value):
    if value is True: return '真'
    if value is False: return '假'
    if isinstance(value, list): return '['+','.join(map(ru_literal,value))+']'
    return json.dumps(value,ensure_ascii=False)


def prepare(out, rows):
    source=(ROOT/'tests/regex_policy.ru').read_text(encoding='utf-8')
    source=source.replace("'../src/regex_compile.ru'",json.dumps(str(ROOT/'src/regex_compile.ru')))
    source=source.replace("'../src/regex_vm.ru'",json.dumps(str(ROOT/'src/regex_vm.ru')))
    start=source.index('# BEGIN CASES'); end=source.index('# END CASES')
    table='案例们 取 [\n'+',\n'.join('    '+ru_literal(row) for row in rows)+'\n].\n'
    assert source[start:end] == '# BEGIN CASES\n'+table, 'Canonical Ru fixture differs from independent oracle table'
    # Keep the checked-in fixture byte-for-byte except module paths, so Windows
    # can run precisely the same assertions without Python-generated substitutes.
    path=out/'regex_policy.ru'; path.write_text(source, encoding='utf-8'); return path


def verify(output, rows):
    runtime_output(output, '', 'oracle')
    if any(not line.startswith(('PASS: ', 'RESULT ', 'TOTAL PASS: ')) for line in output.splitlines()):
        raise AssertionError('Unexpected runtime output line')
    expected=['PASS: '+r[0] for r in rows]
    actual=[line for line in output.splitlines() if line.startswith('PASS: ')]
    assert actual == expected, 'Individual assertion list differs: '+output[-4000:]
    assert output.splitlines()[-1] == f'TOTAL PASS: {len(rows)}'
    results={}
    for line in output.splitlines():
        if line.startswith('RESULT '):
            _,name,status,start,end,operations,cursor=line.split()
            results[name]=(status,int(start),int(end),int(operations),int(cursor))
    for row in rows:
        if row[8].startswith('compile-'): continue
        assert results[row[0]][:3] == (row[8],row[9],row[10])
        if row[0].endswith('-b1'):
            assert results[row[0]] == results[row[0][:-1]+'64'], ('budget-dependent result/work',row[0])
    for i in (0,1):
        values=[results[f'linear-{i}-{n}'][3] for n in (16,32,64)]
        assert values[1] <= 3*values[0] and values[2] <= 3*values[1], ('superlinear counted work',values)
    assert results['total-limit'][3] <= 10
    return results


def run(ru, out):
    out.mkdir(parents=True,exist_ok=True)
    commit = verify_compiler(ru)
    executable = executable_path(out, 'regex_policy')
    compiler = gcc_path()
    environment = dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
    paths=[ROOT/'src/regex_compile.ru', ROOT/'src/regex_vm.ru', ROOT/'tests/regex_policy.ru', Path(__file__).resolve()]
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    rows=cases(); fixture=prepare(out,rows); logs={}
    commands=[('interpreter',[sys.executable,str(ru/'ru'),'run',str(fixture)]),
              ('build',[sys.executable,str(ru/'ru'),'build','--cc',compiler,str(fixture),'-o',str(executable)]),
              ('native',[str(executable)])]
    for label,command in commands:
        process=subprocess.run(command,text=True,encoding='utf-8',capture_output=True,timeout=240,env=environment)
        log=process.stdout+process.stderr; (out/(label+'.log')).write_text(log, encoding='utf-8')
        assert process.returncode == 0, f'{label} failed:\n{log[-6000:]}'
        if label != 'build':
            runtime_output(process.stdout, process.stderr, label)
            verify(process.stdout, rows)
            logs[label] = process.stdout
    assert logs['interpreter']==logs['native'], 'Backend full output differs'
    assert hashes == {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}, 'Sources changed during acceptance run; rerun required'
    verify_compiler(ru)
    receipt={'compiler':commit,'compiler_tree':TREE,'cases':len(rows),'portable_only':True,
             'files':hashes,
             'fixture_sha256':hashlib.sha256(fixture.read_bytes()).hexdigest(),
             'output_sha256':hashlib.sha256(logs['native'].encode()).hexdigest()}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n', encoding='utf-8')
    print(f'REGEX_POLICY_PASS {len(rows)} exact assertions each backend; full outputs identical; not Windows evidence')

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--ru-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True); args=parser.parse_args()
    run(args.ru_root.resolve(),args.output.resolve())
