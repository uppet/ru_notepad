#!/usr/bin/env python3
"""Paired Linux policy microbenchmark, explicitly excluding Windows and GUI.

Uses the existing scanner benchmark's bounded C harness, adding exact GUI-corpus
input and an ordinary Ru counter-report function in instrumented copies.
All four modules use the same pinned compiler and identical lexical input.
"""
import argparse
import ast
import ctypes as C
import hashlib
import inspect
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys
import textwrap

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))

import test_ru_scan as scanner
import test_ru_policy_fast as proof
import windows_ci
import verify_ru_policy_fast_outputs as public_proof

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'build/policy-fast/benchmark'
SHAPES = ('gui','ascii','line','ru','realistic')
GUI_SHA256 = 'ecf8dca884444a5e54e1f40dc6af01cf5e7830ed6fe902d3adf6fdf255f9b3fa'
PATTERNS = {'ascii':'a=1.\n','line':'a=1. ','ru':'x 取 1.\n',
            'realistic':"# Unicode 中😀 source example\n作 演示:\n    数值 取 42.\n    文字 取 '若 真 则'.\n    若 真 则\n        显 文字.\n    然\n为\n"}
METRICS = {'bytes','calls','events','total_ms','scanner_ms','decode_policy_ms',
           'max_batch_ms','cpu_total_ms','max_cpu_batch_ms'}


def run(command, label):
    result = subprocess.run(list(map(str,command)),cwd=ROOT,capture_output=True,
                            text=True,encoding='utf-8',timeout=600)
    (OUT/f'{label}.log').write_text(result.stdout+result.stderr,encoding='utf-8',newline='\n')
    if result.returncode:
        raise RuntimeError(f'{label}: {result.returncode}\n{result.stdout[-2000:]}{result.stderr[-2000:]}')
    return result.stdout


def harness():
    tree = ast.parse(textwrap.dedent(inspect.getsource(scanner.benchmark)))
    assignments = {node.targets[0].id:node.value for node in tree.body[0].body
                   if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name)}
    head = ast.literal_eval(assignments['head'])
    main = ast.literal_eval(assignments['main'].func.value)
    for pattern in PATTERNS.values():
        assert json.dumps(pattern,ensure_ascii=False) in main
    main = main.replace('size=target/plen*plen,at=0;',
                        'size=argc>2&&strcmp(argv[2],"gui")==0?target:target/plen*plen,at=0;')
    fill = 'for(size_t n=0;n<size;n++)text[n]=(uint8_t)pattern[n%plen];'
    assert main.count(fill) == 1
    main = main.replace(fill,'if(argc>2&&strcmp(argv[2],"gui")==0){FILE *f=argc>3?fopen(argv[3],"rb"):NULL;if(!f||fread(text,1,size,f)!=size||fgetc(f)!=EOF)return 5;fclose(f);}else '+fill)
    return head, main.replace('CONFIGURATION',json.dumps(scanner.configuration().decode(),ensure_ascii=False))


def expected_input(data, gui=False):
    """Independent bounded scanner pass fixes expected bytes/feed/event totals."""
    sc = scanner.Scanner(proof.OUT/'libRuSyntax.so')
    state = sc.state()
    at = calls = count = tokens = prefix_bypasses = nonfast_tokens = 0
    while at < len(data):
        window = data[at:at+1024]
        offset = 0
        while True:
            styles = (C.c_uint8*1040)()
            events = (scanner.Event*64)()
            result = scanner.Result()
            status = sc.dll.ru_scan_feed(sc.config,state,window,len(window),offset,
                                        at+len(window)==len(data),styles,1040,events,64,C.byref(result))
            assert status in (0,1)
            calls += 1
            count += result.events
            tokens += sum(1 <= (event.head&255) <= 4 for event in events[:result.events])
            if gui:
                eligible = True
                for event in events[:result.events]:
                    kind,code = event.head&255,event.head>>8&255
                    assert kind in (1,2,3,4,7)
                    if 1 <= kind <= 4:
                        effective = 0 if kind in (2,3) else code
                        if effective not in (0,9,100,117):
                            assert kind == 1 and effective == 24
                            nonfast_tokens += 1
                            eligible = False
                        elif eligible:
                            prefix_bypasses += 1
            offset += result.consumed
            if status == 0:
                break
            assert result.consumed or result.events or result.styled
        assert offset == len(window)
        at += offset
    assert result.done and result.bytes == len(data)
    result = {'bytes':len(data),'calls':calls,'events':count,'tokens':tokens,
              'sha256':hashlib.sha256(data).hexdigest()}
    if gui:
        assert nonfast_tokens == 1
        result['expected_prefix_bypasses'] = prefix_bypasses
    return result


def read_measurement(text, counted, expected):
    lines = text.splitlines()
    assert len(lines) == (2 if counted else 1)
    pairs = [part.split('=',1) for part in lines[0].split()]
    assert len(pairs) == len(METRICS) and {item[0] for item in pairs} == METRICS
    metrics = {key:float(value) for key,value in pairs}
    assert all(math.isfinite(value) and value >= 0 for value in metrics.values())
    for key in ('bytes','calls','events'):
        assert metrics[key] == expected[key]
    assert metrics['total_ms'] > 0 and metrics['decode_policy_ms'] > 0
    counts = None
    if counted:
        parts = lines[1].split()
        assert parts[0] == 'COUNTS' and len(parts) == 4
        pairs = [part.split('=',1) for part in parts[1:]]
        assert {pair[0] for pair in pairs} == {'calls','inner_fast','bypass'}
        assert all(value.isdecimal() for _,value in pairs)
        counts = {key:int(value) for key,value in pairs}
        assert counts['calls']+counts['bypass'] == expected['tokens']
        assert counts['inner_fast'] <= counts['calls']
    return metrics,counts


def instrument(source, fast):
    source = '_统计 取 [0,0,0].\n'+source
    token = '算 _记词 态 类 词 行 为 数 折们:\n'
    assert source.count(token) == 1
    source = source.replace(token,token+'    _统计[0] 取 _统计[0]+1.\n',1)
    token = '        若 词 == 0 或 词 == 9 或 词 == 100 或 词 == 117 则\n'
    assert source.count(token) == 1
    source = source.replace(token,token+'            _统计[1] 取 _统计[1]+1.\n',1)
    if fast:
        token = '                若 非 (词 == 0 或 词 == 9 或 词 == 100 或 词 == 117) 则 破. 然\n'
        assert source.count(token) == 1
        source = source.replace(token,token+'                _统计[2] 取 _统计[2]+1.\n',1)
    return source+"\n作 报告统计:\n    显 'COUNTS calls='+(_统计[0] 为 句)+' inner_fast='+(_统计[1] 为 句)+' bypass='+(_统计[2] 为 句).\n为\n"


def build(label, source, ru_root, counted):
    module = OUT/f'{label}.ru'
    module.write_text(source,encoding='utf-8',newline='\n')
    entry = OUT/f'{label}-main.ru'
    entry.write_text('模 取 外言 '+scanner.q(str(module))+'.\n显 模 其 新状态.\n',encoding='utf-8',newline='\n')
    generated = OUT/f'{label}-generated.c'
    run([sys.executable,ru_root/'ru','build','--cc','gcc',entry,'--emit-c',generated,'-o',OUT/f'{label}-unused'],label+'-build')
    body = generated.read_text(encoding='utf-8').split('int main(int argc, char **argv)',1)[0]
    head, main = harness()
    if counted:
        target = '     v_drop(state);v_drop(constructor);'
        assert main.count(target) == 1
        main = main.replace(target,'     Val counter=env_get(mod.module,"报告统计",1);Val report=v_call(counter,0,NULL,NULL,1);v_drop(report);v_drop(counter);\n'+target)
    joined = OUT/f'{label}-combined.c'
    joined.write_text(head+body+main,encoding='utf-8',newline='\n')
    exe = OUT/label
    run(['gcc','-std=c99','-O2','-I',ROOT/'native',joined,ROOT/'native/ru_scan.c','-lm','-o',exe],label+'-harness-build')
    return exe


def main():
    if sys.flags.optimize:
        raise ValueError("Policy benchmark requires active assertions")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',type=Path,required=True)
    parser.add_argument('--ru-root',type=Path,required=True)
    parser.add_argument('--repeats',type=int,default=3)
    args = parser.parse_args()
    before, after = proof.verify_sources(args.baseline.resolve(),args.ru_root.resolve())
    # Require successful actual-Ru semantic proof of this exact source first.
    report = public_proof.validate_public_evidence(proof.OUT, public_proof.expected_inputs_from_source())
    assert report['candidate_sha256'] == hashlib.sha256(after.encode()).hexdigest()
    assert report['status'] == 'passed' and report['schema_version'] == 1
    assert report['ordered_output_validation']['status'] == 'passed'
    assert args.repeats >= 3
    OUT.mkdir(parents=True,exist_ok=False)
    identity = OUT/'identity'
    identity.mkdir(exist_ok=True)
    paths = ['tools/benchmark_ru_policy_fast.py','tools/test_ru_policy_fast.py',
             'tools/verify_ru_policy_fast_outputs.py','tools/test_ru_scan.py',
             'tools/windows_ci.py','tests/fixtures/ru_policy_fast_plan.json','src/ru_lexical.ru','native/ru_scan.c','native/ru_scan.h']
    source_identity = {}
    for relative in paths:
        data = (ROOT/relative).read_bytes()
        snapshot = identity/relative
        snapshot.parent.mkdir(parents=True,exist_ok=True)
        snapshot.write_bytes(data)
        source_identity[relative] = {'sha256':hashlib.sha256(data).hexdigest(),
                                     'snapshot':str(snapshot.relative_to(ROOT))}
    start_identity = {'stage':'Invocation, before build and measurement','files':source_identity}
    (identity/'invocation-sources.json').write_text(json.dumps(start_identity,indent=2)+'\n',encoding='utf-8',newline='\n')
    corpus,_ = windows_ci.gui_ru_timer_fixture()
    assert len(corpus) == 1000000 and hashlib.sha256(corpus).hexdigest() == GUI_SHA256
    (OUT/'gui-corpus.ru').write_bytes(corpus)
    inputs = {shape:expected_input(corpus if shape == 'gui' else
               PATTERNS[shape].encode()*(1000000//len(PATTERNS[shape].encode())),gui=shape=='gui') for shape in SHAPES}
    binaries = {}
    binary_identity = {}
    artifact_identity = {}
    for label,source,counted,fast in [('baseline',before,False,False),('candidate',after,False,True),
                                     ('baseline-counted',before,True,False),('candidate-counted',after,True,True)]:
        binaries[label] = build(label,instrument(source,fast) if counted else source,args.ru_root.resolve(),counted)
        binary_identity[label] = hashlib.sha256(binaries[label].read_bytes()).hexdigest()
        for suffix in ('.ru','-main.ru','-generated.c','-combined.c'):
            path = OUT/(label+suffix)
            artifact_identity[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    (identity/'pre-measurement-binaries.json').write_text(json.dumps(binary_identity,indent=2)+'\n',encoding='utf-8',newline='\n')
    (identity/'pre-measurement-artifacts.json').write_text(json.dumps(artifact_identity,indent=2)+'\n',encoding='utf-8',newline='\n')
    records = []
    for shape in SHAPES:
        for repeat in range(args.repeats):
            # Alternate order; count overhead is separately observable.
            order = list(binaries) if repeat%2 == 0 else list(reversed(binaries))
            for label in order:
                assert hashlib.sha256(binaries[label].read_bytes()).hexdigest() == binary_identity[label]
                text = run([binaries[label],1000000,shape,OUT/'gui-corpus.ru'],f'{shape}-{repeat}-{label}').strip()
                metrics,counts = read_measurement(text,label.endswith('-counted'),inputs[shape])
                records.append({'shape':shape,'target_bytes':1000000,'repeat':repeat,'variant':label,'metrics':metrics,'counts':counts})
                print(shape,repeat,label,text,flush=True)
    summary = {}
    for shape in SHAPES:
        medians = {label:statistics.median(item['metrics']['decode_policy_ms'] for item in records
                                         if item['shape']==shape and item['variant']==label) for label in binaries}
        summary[shape] = {'median_decode_policy_ms':medians,
                          'uninstrumented_speedup':medians['baseline']/medians['candidate'],
                          'observed_baseline_counted_off_ratio':medians['baseline-counted']/medians['baseline'],
                          'observed_candidate_counted_off_ratio':medians['candidate-counted']/medians['candidate']}
        stable = None
        for repeat in range(args.repeats):
            rows = [item for item in records if item['shape']==shape and item['repeat']==repeat]
            assert len(rows) == 4 and {item['variant'] for item in rows} == set(binaries)
            old = next(item['counts'] for item in rows if item['variant']=='baseline-counted')
            new = next(item['counts'] for item in rows if item['variant']=='candidate-counted')
            assert old['bypass'] == 0 and old['calls'] == new['calls']+new['bypass']
            assert old['inner_fast'] == new['inner_fast']+new['bypass']
            if stable is None:
                stable = (old,new)
            assert stable == (old,new), 'Counter totals changed across repeats'
        if shape == 'gui':
            assert stable == ({'calls':363631,'inner_fast':363630,'bypass':0},
                              {'calls':363631-inputs['gui']['expected_prefix_bypasses'],
                               'inner_fast':363630-inputs['gui']['expected_prefix_bypasses'],
                               'bypass':inputs['gui']['expected_prefix_bypasses']})
        if shape == 'realistic':
            assert stable == ({'calls':133798,'inner_fast':0,'bypass':0},)*2
    for relative,entry in source_identity.items():
        assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest() == entry['sha256']
    for label,path in binaries.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == binary_identity[label]
    for relative,sha256 in artifact_identity.items():
        assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest() == sha256
    proof.verify_sources(args.baseline.resolve(),args.ru_root.resolve())
    regression = {shape:100*(values['median_decode_policy_ms']['candidate']/
                             values['median_decode_policy_ms']['baseline']-1)
                  for shape,values in summary.items()}
    result = {'scope':'Linux scanner plus ordinary generated Ru array construction/policy only. Excludes Windows native ABI, Scintilla, GUI and direct/message route comparison.',
              'source_sha256':report['candidate_sha256'],'toolchain_commit':proof.RU_COMMIT,
              'toolchain_tree':proof.RU_TREE,'baseline_commit':proof.BASE_COMMIT,
              'baseline_source_sha256':report['baseline_source_sha256'],
              'semantic_report_sha256':hashlib.sha256((proof.OUT/'report.json').read_bytes()).hexdigest(),
              'benchmark_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'compiler':subprocess.check_output(['gcc','--version'],text=True,encoding='utf-8').splitlines()[0],
              'variant_source_sha256':{label:hashlib.sha256((OUT/f'{label}.ru').read_bytes()).hexdigest() for label in binaries},
              'variant_generated_c_sha256':{label:hashlib.sha256((OUT/f'{label}-combined.c').read_bytes()).hexdigest() for label in binaries},
              'gui_corpus_sha256':GUI_SHA256,
              'input_shapes':inputs,
              'execution_identity':{'invocation_sources':start_identity,'binary_sha256':binary_identity,
                                    'build_artifact_sha256':artifact_identity,
                                    'source_and_binary_drift_at_end':False},
              'counter_ratio_interpretation':'Observed counted/off ratios, not isolated instrumentation overhead. Values below one can reflect measurement/layout noise; no cost is subtracted.',
              'median_policy_change_percent':regression,
              'all_five_medians_nonregressing':all(value <= 0 for value in regression.values()),
              'repeats':args.repeats,'summary':summary,'records':records}
    (OUT/'report.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(summary,indent=2),flush=True)


if __name__ == '__main__':
    main()
