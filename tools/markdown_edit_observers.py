#!/usr/bin/env python3
"""Private diagnostic observer copies; no product source or globals are modified."""
import ast, hashlib, inspect
from pathlib import Path

MODULE_SHA256 = '5e87bfee0c516f3e805c6bbdd9b32d24f6d2f818474cfb7d0538ba4422389b8e'
OBJECT_SHA256 = {'GuiRuObserver': '16f4c422b6cf720b357d37f48b60a8ad428566fd48f5fe0611c663a15e1ab268', 'MarkdownProcessMemory': '8587c9d1b4d217490cdebd6fa74aa2e9747aac7acd486e918daa75b25701eed5', 'validate_gui_ru_observer': 'c7cea197156a80f44a3dcae4f294cd9de4aa45d12cc0308d9a8f5a2c04364170', 'validate_markdown_memory': 'a6a174ee17efb3106e90212dddb750700e4d8d17955b45c98460fcba3f7ab391'}
POLICY = {
    'GuiRuObserver': {'snapshot':1,'timeout':1,'message':1},
    'MarkdownProcessMemory': {'snapshot':1},
    'validate_gui_ru_observer': {'snapshot':1,'response':1},
    'validate_markdown_memory': {'snapshot':1},
}

def adapted(ci):
    if hashlib.sha256(Path(ci.__file__).read_bytes()).hexdigest()!=MODULE_SHA256:
        raise ValueError('edit_observer_module_changed')
    outputs={}
    for name,expected_hash in OBJECT_SHA256.items():
        original=getattr(ci,name);source=inspect.getsource(original)
        if hashlib.sha256(source.encode()).hexdigest()!=expected_hash:
            raise ValueError('edit_observer_object_changed')
        counts={};policy=POLICY[name]
        class Adapter(ast.NodeTransformer):
            def record(self,key):counts[key]=counts.get(key,0)+1
            def visit_Name(self,node):
                if node.id=='GUI_RU_TIMER_TIMEOUT_SECONDS':
                    self.record('timeout');return ast.copy_location(ast.Constant(120),node)
                return node
            def visit_Constant(self,node):
                if type(node.value) is int and node.value in (121,601):
                    key='snapshot' if node.value==121 else 'response';self.record(key)
                    return ast.copy_location(ast.Constant(481 if key=='snapshot' else 2401),node)
                if node.value=='GUI 1 MB open and Ru timer styling exceeded 30 seconds':
                    self.record('message')
                    return ast.copy_location(ast.Constant('Private Markdown diagnostic observer exceeded 120 seconds'),node)
                return node
        tree=Adapter().visit(ast.parse(source))
        if counts!=policy:raise ValueError('edit_observer_replacement_mismatch')
        ast.fix_missing_locations(tree)
        namespace=dict(vars(ci))
        exec(compile(tree,'<owned-markdown-edit-observer>','exec'),namespace)
        outputs[name]=namespace[name]
    return outputs
