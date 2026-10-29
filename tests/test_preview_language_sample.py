import hashlib
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import preview_language_sample as sample
class SampleTests(unittest.TestCase):
    def test_exact_utf8_unclosed_fence_reproducible(self):
        data=sample.content()
        self.assertEqual(len(data), 1000000)
        self.assertEqual(data, sample.content())
        self.assertEqual(sample.NAME,'samples/fence.md')
        for bad in (data+b' ',data[:-1],b'X'+data[1:],data+b' '*(1048576-len(data))):
            with self.subTest(size=len(bad)), self.assertRaises(RuntimeError):sample.validate(bad)
        self.assertEqual(hashlib.sha256(data).hexdigest(),'2d9f79ee715b217c00792cf18a67485cdec96a14ea2ac86689156941a022c719')
        self.assertEqual(data.decode('utf-8').count('~~~'),1)
        self.assertEqual(sample.record()['sha256'],hashlib.sha256(data).hexdigest())
        self.assertIn('does not claim manual acceptance',sample.record()['scope'])
    def test_preview_generates_then_exact_zip_inventory_checks(self):
        code=(Path(__file__).resolve().parents[1]/'tools/package_bootstrap_preview.py').read_text()
        self.assertIn("sample_path.write_bytes(language_sample.content())",code)
        self.assertIn("'manual_sample': language_sample.record()",code)
        self.assertIn("verify_zip(pending, files)",code)
if __name__=='__main__':unittest.main()
