from copy import deepcopy
import unittest
from unittest.mock import Mock
import ast
from pathlib import Path
import gui_instance_tabs as subject
HASHES={n:'a'*64 for n in ('ru_notepad.exe','Scintilla.dll','Lexilla.dll','RuSyntax.dll')}
def receipt():
    result={'schema':'ru-notepad-instance-tabs-gui-v1','name':'main-gui-instance-tabs','passed':True,'executed':True,'cleanup_killed':False,'exit_code':0,'checks':dict.fromkeys(subject.CHECKS,True),'fixture_binary_sha256':dict(HASHES),'phases':[{'phase':phase,'passed':True,'executed':True,'cleanup_killed':False,'exit_code':0,'fixture_binary_sha256':dict(HASHES)} for phase in subject.PHASES], 'secondary_processes':[{'purpose':purpose,'exit_code':0,'cleanup_killed':False,'visible_main_seen':purpose in ('disabled','explicit-multi'),'fixture_binary_sha256':dict(HASHES)} for purpose in subject.CHILDREN]}
    for phase in result['phases']:
        if phase['phase'] in ('startup-race','timeout-uncertain'):phase['participants']=[{'exit_code':0,'cleanup_killed':False} for _ in range(2)]
        if phase['phase']=='timeout-uncertain':phase.update(controlled_ui_suspend=True,owner_delivery_count=0)
    return result
class ReceiptTests(unittest.TestCase):
    def test_modal_commands_are_posted_to_owned_window(self):
        api=Mock()
        api.user.PostMessageW.return_value=True
        subject._post_command(api,123,805)
        api.user.PostMessageW.assert_called_once_with(123,0x111,805,0)
        api.scalar.assert_not_called()
        tree=ast.parse(Path(subject.__file__).read_text())
        for node in ast.walk(tree):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='command' and len(node.args)>1:
                self.assertFalse(isinstance(node.args[1],ast.Constant) and node.args[1].value in (805,113),'modal command was synchronously sent')

    def test_complete_synthetic_contract(self):self.assertTrue(subject.validate_result(receipt(),HASHES))
    def test_reject_incomplete_or_forged_receipts(self):
        mutations=[lambda r:r.update(extra=True),lambda r:r.pop('schema'),lambda r:r.update(schema='old'),lambda r:r.update(name='other'),lambda r:r.update(passed=False),lambda r:r.update(executed=False),lambda r:r.update(cleanup_killed=True),lambda r:r.update(exit_code=False),lambda r:r.update(exit_code=1),lambda r:r['fixture_binary_sha256'].update({'ru_notepad.exe':'b'*64}),lambda r:r['checks'].pop(subject.CHECKS[0]),lambda r:r['checks'].update(unknown=True),lambda r:r['checks'].update({subject.CHECKS[0]:1}),lambda r:r['checks'].update({subject.CHECKS[0]:False}),lambda r:r['phases'].pop(),lambda r:r['phases'].reverse(),lambda r:r['phases'][0].update(executed=False),lambda r:r['phases'][0].update(exit_code=False),lambda r:r['phases'][0].update(cleanup_killed=True),lambda r:r['phases'][0].update(fixture_binary_sha256={}),lambda r:r['secondary_processes'].pop(),lambda r:r['secondary_processes'].reverse(),lambda r:r['secondary_processes'][0].update(exit_code=False),lambda r:r['secondary_processes'][0].update(cleanup_killed=True),lambda r:r['secondary_processes'][0].update(visible_main_seen=True),lambda r:r['secondary_processes'][2].update(visible_main_seen=False),lambda r:r['secondary_processes'][0].update(visible_main_seen=0),lambda r:r['secondary_processes'][0].update(fixture_binary_sha256={}),lambda r:r['secondary_processes'][0].update(extra='unvalidated'),lambda r:r['phases'][-1].update(owner_delivery_count=True),lambda r:r['phases'][-1].update(owner_delivery_count=2),lambda r:r['phases'][-1].update(controlled_ui_suspend=False),lambda r:r['phases'][-2]['participants'].pop(),lambda r:r['phases'][-1]['participants'][0].update(exit_code=False),lambda r:r['phases'].__setitem__(0,None),lambda r:r['secondary_processes'].__setitem__(0,None),lambda r:r['phases'][-1]['participants'].__setitem__(0,None)]
        for i,mutate in enumerate(mutations):
            r=deepcopy(receipt());mutate(r)
            with self.subTest(mutation=i):
                with self.assertRaises(ValueError):subject.validate_result(r,HASHES)
if __name__=='__main__':unittest.main()
