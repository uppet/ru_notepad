#!/usr/bin/env python3
"""Independent strict-codec/literal oracle for production directory_text.ru.

Runs the same checked-in fixture in the pinned interpreter and emitted C, with
identical complete output required. Portable evidence is NOT Windows acceptance.
"""
import argparse
import codecs
import hashlib
import json
import os
from pathlib import Path
import re
import random
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PIN = 'c3bb177c6a15e90821e5495cc74b0fdfc39b893a'
TREE = '5dedbf06f9fb6e00fbfe779b33f172aa35b61334'


def verify_compiler(root):
    def git(*args):
        return subprocess.check_output(['git', '-C', str(root), *args], text=True, encoding='utf-8').strip()
    commit, tree = git('rev-parse', 'HEAD'), git('rev-parse', 'HEAD^{tree}')
    if (commit, tree) != (PIN, TREE):
        raise RuntimeError(f'Wrong compiler identity: commit={commit}, tree={tree}')
    if git('status', '--porcelain=v1', '--untracked-files=all'):
        raise RuntimeError('Compiler source must be clean, including untracked files')
    return commit


def runtime_output(stdout, stderr, label):
    if stderr:
        raise AssertionError(f'{label}: unexpected runtime stderr:\n{stderr}')
    if re.search(r'\b(?:FAIL|SKIP)\b', stdout, re.I):
        raise AssertionError(f'{label}: failure or skip marker in runtime output')


def executable_path(directory, stem):
    return directory / (stem + ('.exe' if os.name == 'nt' else ''))


def gcc_path():
    value = shutil.which('gcc')
    if not value:
        raise RuntimeError('A gcc C compiler must be available on PATH')
    return value


def decode(raw):
    """Use Python's independent incremental strict decoder, not a Ru port."""
    raw = bytes(raw)
    if raw.startswith((b'\xff\xfe\x00\x00', b'\x00\x00\xfe\xff')):
        return '', 'pending', False, 'unsupported-bom'
    encoding, bom, skip = 'utf-8', False, 0
    for marker, codec in ((codecs.BOM_UTF8, 'utf-8'), (codecs.BOM_UTF16_LE, 'utf-16le'), (codecs.BOM_UTF16_BE, 'utf-16be')):
        if raw.startswith(marker):
            encoding, bom, skip = codec, True, len(marker)
            break
    decoder = codecs.getincrementaldecoder(encoding)(errors='strict')
    text = ''
    try:
        for value in raw[skip:]:
            piece = decoder.decode(bytes([value]), final=False)
            if '\0' in piece:
                return text, encoding, bom, 'binary-nul'
            text += piece
        text += decoder.decode(b'', final=True)
    except UnicodeError:
        return text, encoding, bom, 'invalid-utf8' if encoding == 'utf-8' else 'invalid-utf16'
    return text, encoding, bom, ''


def oracle(raw, query, slots=2000):
    text, encoding, bom, reason = decode(raw)
    rows = []
    if reason:
        return {'status': 'skipped', 'reason': reason, 'encoding': encoding, 'bom': bom, 'rows': []}
    coordinates = []
    line, column, offset, start = 1, 1, 0, 0
    for index, char in enumerate(text):
        if index and (text[index-1] == '\n' or (text[index-1] == '\r' and char != '\n')):
            line, column, start = line+1, 1, index
        coordinates.append((offset, line, column, start))
        column += 1
        offset += len(char.encode('utf-8'))
    cursor = 0
    while len(rows) < slots:
        at = text.find(query, cursor)
        if at < 0:
            break
        byte, line, column, line_start = coordinates[at]
        pre_start = max(line_start, at-32)
        preview = [ord(c) for c in text[pre_start:at]+query[:64]]
        rows.append([byte, byte+len(query.encode('utf-8')), line, column,
                     preview, pre_start > line_start, len(query) > 64])
        cursor = at+len(query)
    return {'status': 'complete', 'reason': '', 'encoding': encoding, 'bom': bom,
            'utf8Bytes': offset, 'rows': rows, 'capReached': len(rows) == slots}


def signature(result):
    # Skipped decoder progress/encoding need not be identical between backends
    # by contract, but complete results are fully specified and checked.
    if result['status'] != 'complete':
        return result['status']+'|'+result['reason']
    parts = ['complete', '', result['encoding'], str(int(result['bom'])),
             str(result['utf8Bytes']), str(int(result['capReached']))]
    for row in result['rows']:
        parts.append(','.join(map(str, row[:4]))+':'+','.join(map(str,row[4]))+':'+str(int(row[5]))+','+str(int(row[6])))
    return '|'.join(parts)


def cases():
    result = []
    def add(name, raw, query='a', slots=2000, mode='normal', splits=True, budgets=(1,17,1024)):
        raw = list(raw)
        expected = oracle(raw, query, slots)
        if mode == 'changed': expected = {'status':'skipped','reason':'changed-snapshot'}
        if mode == 'short': expected = {'status':'skipped','reason':'incomplete-file'}
        if mode == 'cancel': expected = {'status':'cancelled','reason':''}
        result.append([name, [ord(c) for c in query], raw, slots, mode, splits, list(budgets), signature(expected)])
    texts = [('empty',''), ('ascii','baaabaaa'), ('nonoverlap','aaaaa'),
             ('unicode','甲😀aéa𝄞'), ('crlf','a\r\na\ra\na'),
             ('terminators','x\r\ny\rz\n'), ('no-normalize','e\u0301é'),
             ('kmp-fallback','ababababacababac'), ('control','\t\x01a\u202ea')]
    for encoding, bom in [('utf-8', b''), ('utf-8', codecs.BOM_UTF8), ('utf-16le',codecs.BOM_UTF16_LE), ('utf-16be',codecs.BOM_UTF16_BE)]:
        for name, text in texts:
            query = 'aa' if name == 'nonoverlap' else 'ababac' if name == 'kmp-fallback' else 'é' if name == 'no-normalize' else 'a'
            add(name+'-'+encoding+('-bom' if bom else ''), bom+text.encode(encoding), query)
        for query in ('\r','\n','\r\n','😀a'):
            add('coordinate-'+str(ord(query[0]))+'-'+str(len(query))+'-'+encoding+('-bom' if bom else ''),bom+'甲😀a\r\na\rb\nc'.encode(encoding),query)
    malformed = [b'\xc0\xaf', b'\xc1\xbf', b'\xe0\x80\x80',b'\xed\xa0\x80', b'\xf0\x80\x80\x80',b'\xf4\x90\x80\x80',b'\xf5\x80\x80\x80', b'\x80', b'\xff',b'\xc2',b'\xe1\x80',b'\xf0\x90\x80',b'\xc2a',b'\xe1\x80a',b'\xf0\x90a\x80',b'\x00',b'\xff\xfe\x00\x00',b'\x00\x00\xfe\xff',b'\xff\xfe\x00\xd8',b'\xfe\xff\xdc\x00',b'\xff\xfea',b'\xfe\xff\xd8\x00\x00a',b'\xff\xfea\x00\x00',b'\xff\xfe\x00\x00a\x00']
    for i, raw in enumerate(malformed): add('invalid-'+str(i),raw)
    for i, tail in enumerate((b'\x00', b'\xc2',b'\xed\xa0\x80')):
        add('late-invalid-cap-'+str(i), b'aaaa'+tail, slots=1)
    for encoding,bom in [('utf-16le',codecs.BOM_UTF16_LE),('utf-16be',codecs.BOM_UTF16_BE)]:
        add('late-utf16-'+encoding,bom+'aaaa'.encode(encoding)+b'\xd8',slots=1)
    for slots in (0,1,2,3): add('cap-'+str(slots),b'aaaaa',slots=slots)
    for mode in ('changed','short','cancel'): add(mode,b'aaaa',slots=1,mode=mode)
    add('budget-sweep',b'ababababac\r\na','ababac',splits=False,budgets=range(1,1025))
    add('long-line',b'x'*4096+b'a\r\na','a',splits=False)
    add('preview-64',b'x'*40+b'a'*64,'a'*64,splits=False)
    add('preview-65',b'x'*40+b'a'*65,'a'*65,splits=False)
    add('max-query',b'a'*256,'a'*256,splits=False)
    add('max-query-utf8',('😀'*256).encode(),'😀'*256,splits=False)
    add('kmp-stress',b'a'*2048+b'b','a'*255+'b',splits=False)
    boundary=''.join(map(chr,[1,127,128,2047,2048,55295,57344,65535,65536,1114111]))
    for encoding,bom in [('utf-8',b''),('utf-16le',codecs.BOM_UTF16_LE),('utf-16be',codecs.BOM_UTF16_BE)]:
        add('scalar-edges-'+encoding,bom+boundary.encode(encoding),boundary[2:9])
    rng=random.Random(20261104)
    for i in range(20):
        text=''.join(rng.choice('abé甲😀\r\n') for _ in range(24))
        begin=rng.randrange(20); query=text[begin:begin+rng.randrange(1,5)]
        for encoding,bom in [('utf-8',b''),('utf-8',codecs.BOM_UTF8),('utf-16le',codecs.BOM_UTF16_LE),('utf-16be',codecs.BOM_UTF16_BE)]:
            add('random-'+str(i)+'-'+encoding+('-bom' if bom else ''),bom+text.encode(encoding),query,splits=False,budgets=(17,))
    return result


def ru_literal(value):
    if value is True: return '真'
    if value is False: return '假'
    if isinstance(value,list):
        if len(value)>32 and all(type(x) is int for x in value):
            if value==list(range(value[0],value[0]+len(value))):
                return '(序列 '+str(value[0])+' '+str(len(value))+')'
            runs=[]
            for x in value:
                if runs and runs[-2]==x: runs[-1]+=1
                else: runs.extend([x,1])
            if len(runs)<len(value): return '(展开 ['+','.join(map(str,runs))+'])'
        return '['+','.join(map(ru_literal,value))+']'
    return json.dumps(value,ensure_ascii=False)


def table(rows):
    return '案例们 取 [\n'+',\n'.join('    '+ru_literal(row) for row in rows)+'\n].\n'


def prepare(out,rows):
    source=(ROOT/'tests/directory_text_policy.ru').read_text(encoding='utf-8')
    start=source.index('# BEGIN CASES'); end=source.index('# END CASES')
    assert source[start:end] == '# BEGIN CASES\n'+table(rows), 'Canonical fixture differs from independent oracle'
    source=source.replace("'../src/directory_text.ru'",json.dumps(str(ROOT/'src/directory_text.ru')))
    fixture=out/'directory_text_policy.ru'; fixture.write_text(source,encoding='utf-8'); return fixture


def expected_runs(rows):
    for row in rows:
        cuts = [-1]+list(range(len(row[2])+1)) if row[5] else [-1]
        for cut in cuts:
            for budget in row[6]:
                yield row[0]+'-'+str(cut)+'-'+str(budget),row[7]


def verify(output,rows):
    runtime_output(output,'','runtime')
    lines=output.splitlines()
    expected=['RESULT '+name+' '+value for name,value in expected_runs(rows)]
    actual=[line for line in lines if line.startswith('RESULT ')]
    if actual != expected:
        for i,(got,want) in enumerate(zip(actual,expected)):
            if got != want: raise AssertionError(f'Oracle differs at {i}: {got}\nExpected: {want}')
        raise AssertionError(f'Result count differs: {len(actual)} != {len(expected)}')
    protocols=['invalid-queries']+[f'size-{i}' for i in range(6)]+[f'slots-{i}' for i in range(6)]+[f'bytes-{i}' for i in range(7)]
    protocols += ['chunk-limit','wrong-offset','declared-overrun','feed-running','eof-running','eof-nonboolean','eof-null']
    protocols += [f'budget-{i}' for i in range(7)]+[f'program-{i}' for i in range(6)]+['cancel-preview','cancel-commit','maximum-cap']+[f'metadata-{i}' for i in range(3)]
    actual_protocols=[line[9:] for line in lines if line.startswith('PROTOCOL ')]
    assert actual_protocols == protocols, 'Missing or different protocol checks'
    assert lines[-1] == 'TOTAL PASS: '+str(len(expected)), 'Missing exact total'
    assert all(line.startswith(('RESULT ','PROTOCOL ','TOTAL PASS: ')) for line in lines), 'Unexpected output'
    return len(expected)


def run(ru,out):
    out.mkdir(parents=True,exist_ok=True)
    commit=verify_compiler(ru); rows=cases(); fixture=prepare(out,rows)
    files=[ROOT/'src/directory_text.ru',ROOT/'tests/directory_text_policy.ru',Path(__file__).resolve()]
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    executable=executable_path(out,'directory_text_policy')
    commands=[('interpreter',[sys.executable,str(ru/'ru'),'run',str(fixture)]),('build',[sys.executable,str(ru/'ru'),'build','--cc',gcc_path(),str(fixture),'-o',str(executable)]),('native',[str(executable)])]
    logs={}; count=0
    for label,command in commands:
        log_path=out/(label+'.log')
        with log_path.open('w',encoding='utf-8') as stream:
            p=subprocess.run(command,text=True,encoding='utf-8',stdout=stream,stderr=subprocess.PIPE,timeout=1200,env=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8',PYTHONUNBUFFERED='1'))
        stdout=log_path.read_text(encoding='utf-8')
        if p.stderr: (out/(label+'.stderr.log')).write_text(p.stderr,encoding='utf-8')
        assert p.returncode==0, f'{label} failed:\n{(stdout+p.stderr)[-8000:]}'
        if label!='build':
            runtime_output(stdout,p.stderr,label); count=verify(stdout,rows); logs[label]=stdout
    assert logs['interpreter']==logs['native'], 'Backend full output differs'
    assert hashes=={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}, 'Sources changed during acceptance; rerun'
    verify_compiler(ru)
    receipt={'compiler':commit,'compiler_tree':TREE,'cases':count,'portable_only':True,'files':hashes,'fixture_sha256':hashlib.sha256(fixture.read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(logs['native'].encode()).hexdigest()}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(f'DIRECTORY_TEXT_POLICY_PASS {count} exact results per backend; full outputs identical; not Windows evidence')

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--ru-root',type=Path,required=True); parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); run(args.ru_root.resolve(),args.output.resolve())
