"""Strict package is published before bulky diagnostic artifacts, never before gates."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'Package only the exact GUI-tested bootstrap preview and verify ZIP bytes'
UPLOAD = 'Upload labelled preview package (not all-native release acceptance)'
DIAGNOSTIC = 'Preserve exact tested runtime as NOT ACCEPTED diagnostic evidence'
GUI = 'Same-binary active GUI budgets, recent files, instance/tab and regex FIND acceptance'
IR = 'Preserve emitted IR for independent source and final-link identity review'

def validate(text):
    names = re.findall(r'^      - name: (.+)$', text, re.M)
    for name in (PACKAGE, UPLOAD, DIAGNOSTIC, GUI, IR):
        if names.count(name) != 1:
            raise ValueError('required unique pipeline stage missing')
    if names.index(UPLOAD) != names.index(PACKAGE) + 1:
        raise ValueError('accepted package must immediately follow strict verification')
    if not names.index(GUI) < names.index(PACKAGE) < names.index(UPLOAD) < names.index(DIAGNOSTIC) < names.index(IR):
        raise ValueError('acceptance and diagnostic ordering differs')
    block = text.split('      - name: '+UPLOAD+'\n',1)[1].split('      - name:',1)[0]
    required = ('        if: success()\n',
                '        uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02\n',
                '          name: ru-notepad-bootstrap-llvm-preview-${{ github.sha }}\n',
                '            ${{ runner.temp }}/ru-bootstrap-preview/dist/*.zip\n',
                '            ${{ runner.temp }}/ru-bootstrap-preview/dist/*.sha256\n',
                '            ${{ runner.temp }}/ru-bootstrap-preview/dist/*.receipt.json\n',
                '          if-no-files-found: error\n')
    if any(value not in block for value in required) or 'continue-on-error' in block:
        raise ValueError('strict accepted-artifact upload boundary differs')
    if re.findall(r'^    timeout-minutes: (.+)$',text,re.M) != ['60','90']:
        raise ValueError('reviewed per-job orchestration budgets changed')
    return True

class UploadOrder(unittest.TestCase):
    def setUp(self):self.text=(ROOT/'.github/workflows/bootstrap-preview.yml').read_text()
    def test_current_pipeline(self):self.assertTrue(validate(self.text))
    def test_reject_late_or_early_upload(self):
        for other in (PACKAGE,DIAGNOSTIC,GUI):
            bad=self.text.replace(UPLOAD,'SENTINEL').replace(other,UPLOAD).replace('SENTINEL',other)
            with self.subTest(other=other),self.assertRaises(ValueError):validate(bad)
    def test_reject_weakened_upload(self):
        for old,new in (('if: success()','if: always()'),('if-no-files-found: error','if-no-files-found: warn'),
                        ('dist/*.receipt.json','diagnostic-runtime/*.json'),('timeout-minutes: 60','timeout-minutes: 90'),('timeout-minutes: 90','timeout-minutes: 120')):
            with self.subTest(old=old),self.assertRaises(ValueError):validate(self.text.replace(old,new))
    def test_missing_or_duplicate_gate_rejected(self):
        for name in (PACKAGE,UPLOAD,DIAGNOSTIC,GUI,IR):
            with self.subTest(name=name),self.assertRaises(ValueError):validate(self.text.replace(name,'Removed'))
            with self.subTest(duplicate=name),self.assertRaises(ValueError):validate(self.text+'\n      - name: '+name+'\n')

if __name__ == '__main__':unittest.main()
