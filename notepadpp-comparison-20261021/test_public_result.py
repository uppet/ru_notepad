import copy, unittest
import public_result as p
class Tests(unittest.TestCase):
    def fixture(self):return dict(schema=2,observer_revision=2,markdown_poll_seconds=.25,markdown_native_common_separate=0,markdown_diagnostics=1,feasibility_only=True,baseline_commit='6aa535d62c28cc9a03f33c3610fe99b3cf1bd14e',fixture_sha256='a'*64,harness_sha256='b'*64,receipt_sha256='c'*64,clock_resolution_seconds=1e-7,requested_poll_seconds=.005,stages_seconds=30.,process_seconds=120.,text_times_are_observable_upper_bounds=True,runs=[])
    def test_valid(self):self.assertEqual(p.project(self.fixture())['schema'],2)
    def test_extra_raw_path(self):
        x=self.fixture();x['raw_path']='secret'
        with self.assertRaises(ValueError):p.project(x)
    def test_nan(self):
        x=self.fixture();x['clock_resolution_seconds']=float('nan')
        with self.assertRaises(ValueError):p.project(x)
    def test_wrong_deadline(self):
        x=self.fixture();x['process_seconds']=125
        with self.assertRaises(ValueError):p.project(x)
    def test_context_hash_only(self):
        x=self.fixture();x['runs']=[dict(arm='A',executed=True,passed=False,stages=[dict(operation='open',completed=False,censored=True,last=dict(length=1000000,dirty=False,context=[97]*4))])]
        y=p.project(x);last=y['runs'][0]['stages'][0]['last'];self.assertNotIn('context',last);self.assertEqual(len(last['context_sha256']),64)
    def test_stage_extra_rejected(self):
        x=self.fixture();x['runs']=[dict(arm='A',executed=True,passed=False,stages=[dict(operation='open',raw_text='private')])]
        with self.assertRaises(ValueError):p.project(x)
if __name__=='__main__':unittest.main()
