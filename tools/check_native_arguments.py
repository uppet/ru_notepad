"""ru_notepad-specific AST arity audit, not a language rule or Windows test.
The named-member checks are project conventions for builtin/native receivers;
Ru permits user members with other signatures. Native bindings are resolved.
"""
import sys, json, argparse
from pathlib import Path
ap=argparse.ArgumentParser()
ap.add_argument('--ru-root',type=Path,required=True)
ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
a=ap.parse_args()
sys.path.insert(0,str(a.ru_root.resolve()))
from rulang.frontend import parse, Node
ROOT=a.root.resolve()
paths=sorted(ROOT.glob("src/*.ru"))+sorted(ROOT.glob("tests/*.ru"))
programs={p.resolve():parse(p.read_text()) for p in paths}
def walk(x):
    if isinstance(x,Node):
        yield x
        for v in x.data.values():yield from walk(v)
    elif isinstance(x,(list,tuple)):
        for v in x:yield from walk(v)
    elif isinstance(x,dict):
        for v in x.values():yield from walk(v)
def known_fact(x):
    # A deliberately narrow syntax check, not general type inference. Native
    # scalar parameters do not accept Ru facts. Catch swallowed comparisons.
    return (x.kind == 'fact' or
            x.kind == 'unary' and x.data['op'] == '非' or
            x.kind == 'binary' and x.data['op'] in ('==','!=','<','>','<=','>=','且','或'))
def member(x,n): return isinstance(x,Node) and x.kind=="member" and x.data["name"]==n
def module_declarations(program):
    # Only module-level conditional branches, never function bodies/local rebinding.
    # Optional native DLL exports are declared here before GUI callbacks begin.
    for node in program:
        yield node
        if node.kind == 'if':
            yield from module_declarations(node.data['yes'])
            yield from module_declarations(node.data['no'])
def syntax_shape(value):
    if isinstance(value,Node):
        return (value.kind,tuple((key,syntax_shape(item)) for key,item in value.data.items()))
    if isinstance(value,(list,tuple)):
        return tuple(syntax_shape(item) for item in value)
    if isinstance(value,dict):
        return tuple((key,syntax_shape(item)) for key,item in value.items())
    return value
bindings={};binding_conflicts=[]
for p,program in programs.items():
    b={}
    for n in module_declarations(program):
        if n.kind=="function":
            body=n.data["body"]
            if len(body)==1 and body[0].kind=="return" and body[0].data["expr"].kind=="array":
                b[n.data["name"]]=("array_helper",len(body[0].data["expr"].data["items"]),len(n.data["params"]))
            continue
        if n.kind!="bind":continue
        x=n.data["expr"];name=n.data["name"]
        if x.kind=="import" and not x.data["path"].startswith("如:"):
            b[name]=("module",(p.parent/x.data["path"]).resolve())
        elif member(x,"绑定") and len(x.data["args"])==2:
            sig=x.data["args"][1][1]
            if member(sig,"签名") and len(sig.data["args"])==3:
                params=sig.data["args"][1][1]
                if params.kind=="array":
                    native=("native",len(params.data["items"]),syntax_shape(sig))
                    if name in b and b[name]!=native:
                        binding_conflicts.append({'path':str(p.relative_to(ROOT)),
                            'line':n.token.line,'name':name,'error':'conflicting module native declarations'})
                    b[name]=native
    bindings[p]=b
def resolve(p,x):
    if x.kind=="name":return bindings.get(p,{}).get(x.data["name"])
    if x.kind=="member":
        r=resolve(p,x.data["receiver"])
        if r and r[0]=="module":return bindings.get(r[1],{}).get(x.data["name"])
records=[];unknown=[];bad=[];member_bad=[];type_bad=[]
for p,program in programs.items():
    for n in walk(program):
        if n.kind=="member":
            name=n.data['name']; argc=len(n.data['args'])
            expected=2 if name=='位段' else 1 if name=='查' else 0 if name in ('量','大小','地址','数','句') else None
            if expected is not None and argc!=expected:
                member_bad.append({'path':str(p.relative_to(ROOT)),'line':n.token.line,'member':name,'expected':expected,'actual':argc})
            if name=='位段':
                for index, (_, value) in enumerate(n.data['args']):
                    if known_fact(value):
                        type_bad.append({'path':str(p.relative_to(ROOT)),'line':n.token.line,
                            'member':name,'argument':index+1,'error':'known fact used as native numeric bit-field argument'})
        if not member(n,"调用"):continue
        row={"path":str(p.relative_to(ROOT)),"line":n.token.line}
        native=resolve(p,n.data["receiver"])
        args=n.data["args"]
        if not native or native[0]!="native" or len(args)!=1:
            unknown.append(row);continue
        argument_array=args[0][1]
        if argument_array.kind=="array":
            actual=len(argument_array.data["items"]);construction="literal"
            for index,value in enumerate(argument_array.data['items']):
                if known_fact(value):
                    type_bad.append({**row,'member':'调用','argument':index+1,
                                     'error':'known fact used as native scalar argument'})
        else:
            helper=resolve(p,argument_array)
            if not helper or helper[0]!="array_helper" or len(argument_array.data.get("args",[]))!=helper[2]:
                unknown.append(row);continue
            actual=helper[1];construction="single-return helper"
        row.update(expected=native[1],actual=actual,construction=construction)
        records.append(row)
        if row["expected"]!=row["actual"]:bad.append(row)
print(json.dumps({"checked":len(records),"mismatches":bad,"unresolved":unknown,"member_mismatches":member_bad,"known_type_mismatches":type_bad,"binding_conflicts":binding_conflicts,"records":records},indent=2))

if bad or unknown or member_bad or type_bad or binding_conflicts:raise SystemExit(1)
