import copy
import unittest
import public_result as p
import validate_public as v
import test_public_result

class Publication(unittest.TestCase):
    def fixture(self):
        x=test_public_result.Tests().fixture()
        x.update(host=dict(windows_version=[10,0,20348],cpu_count=4,cpu_identifier_sha256='d'*64,runner_image_sha256='e'*64),npp_version=[8,9,8,1],toolchain={name:dict(sha256='a'*64,version_stdout_sha256='b'*64,path_sha256='c'*64) for name in ('gcc.exe','g++.exe','windres.exe','ar.exe','ranlib.exe','mingw32-make.exe')},runtime_sha256={'ru':{name:'a'*64 for name in ('ru_notepad.exe','Scintilla.dll','Lexilla.dll','RuSyntax.dll')},'npp':{'notepad++.exe':'b'*64}},runs=[dict(arm='A',executed=True,passed=False,stages=[dict(operation='open',completed=False,censored=True,last=dict(length=1000000,dirty=False,context=[97]*4))])])
        return p.project(x)
    def test_valid(self): v.validate(self.fixture())
    def test_unknown_field(self):
        x=self.fixture();x['path']='secret'
        with self.assertRaises(ValueError):v.validate(x)
    def test_unknown_stage_field(self):
        x=self.fixture();x['runs'][0]['stages'][0]['text']='private'
        with self.assertRaises(ValueError):v.validate(x)
    def test_string_in_numeric(self):
        x=self.fixture();x['host']['cpu_count']='private'
        with self.assertRaises(ValueError):v.validate(x)
    def test_duplicate_key(self):
        with self.assertRaises(ValueError):v.unique([('schema',1),('schema',1)])
    def test_changed_deadline(self):
        x=self.fixture();x['process_seconds']=121
        with self.assertRaises(ValueError):v.validate(x)

    def test_container_in_numeric(self):
        for value in ({'private-key': 'a'*64}, [1]):
            x=self.fixture();x['host']['cpu_count']=value
            with self.assertRaises(ValueError):v.validate(x)

    def test_bool_not_numeric(self):
        x=self.fixture();x['host']['cpu_count']=True
        with self.assertRaises(ValueError):v.validate(x)
    def test_required_field(self):
        x=self.fixture();del x['host']
        with self.assertRaises(ValueError):v.validate(x)
    def test_unknown_schema(self):
        x=self.fixture();x['schema']=2
        with self.assertRaises(ValueError):v.validate(x)
    def test_nonfinite(self):
        x=self.fixture();x['host']['cpu_count']=float('inf')
        with self.assertRaises(ValueError):v.validate(x)
