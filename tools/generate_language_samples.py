#!/usr/bin/env python3
"""Emit the fixed, reviewed lexical-token test corpus (never infer expected styles)."""
import argparse,json
from pathlib import Path
from generate_syntax_catalog import quote,value
ROOT=Path(__file__).resolve().parents[1]
def render(rows):
 out=['# Generated from tests/language_samples.json; expected styles are fixed test oracles.']
 for fn,key,default in [('文本','text',''),('标位','position',0),('标长','length',0),('预期','style',-2)]:
  out += [fn+'表 取 {']
  out += ['    '+quote(r['id'])+':'+value(r[key])+(',' if i+1<len(rows) else '') for i,r in enumerate(rows)]
  out += ['}.','算 '+fn+' 语言 为 句:','    果 取 '+fn+'表 其 查 语言.','    若 果 == 空 则 得 '+value(default)+'. 然','    得 果.','法']
 return '\n'.join(out)+'\n'
def main():
 p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args();out=ROOT/'tests/language_samples.ru';text=render(json.loads((ROOT/'tests/language_samples.json').read_text()))
 if a.check:
  if out.read_text()!=text:raise SystemExit('language sample source is stale')
 else:out.write_text(text,encoding='utf-8',newline='\n')
if __name__=='__main__':main()
