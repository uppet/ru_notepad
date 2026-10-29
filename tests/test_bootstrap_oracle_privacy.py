import hashlib
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from refresh_language_native_oracle import public_failure

class OraclePrivacyTests(unittest.TestCase):
    def test_only_machine_prefix_is_removed(self):
        relative='src/file_codec.ru:845:12: error: 编译复杂度上限\n          状态 其 增\n'.encode()
        self.assertEqual(public_failure(b'/private/example/editor/'+relative),relative)
        self.assertEqual(public_failure(relative),relative)
        windows=b'Z:\\example\\editor\\'+relative.replace(b'/',b'\\')
        self.assertEqual(public_failure(windows),relative)
        with self.assertRaises(ValueError):public_failure(b'unknown diagnostic')
    def test_public_diagnostic_proof_hash_and_redaction_disclosure(self):
        data=(ROOT/'packaging/application-native-oracle-default-failure.txt').read_bytes()
        proof=json.loads((ROOT/'packaging/application-native-oracle-development.json').read_text())
        self.assertTrue(data.startswith(b'src/file_codec.ru:845:12: error:'))
        self.assertEqual(public_failure(data),data)
        self.assertEqual(hashlib.sha256(data).hexdigest(),proof['default_limit_failure']['sha256'])
        self.assertIn('prefix removed',proof['default_limit_failure']['path_redaction'])
        self.assertIn('原生签名静态分析超过复杂度上限',data.decode())
if __name__=='__main__':unittest.main()
