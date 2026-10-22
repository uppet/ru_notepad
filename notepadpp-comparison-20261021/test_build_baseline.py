import hashlib, json, os, tempfile, unittest, zipfile, subprocess
from unittest.mock import patch
from types import SimpleNamespace
from pathlib import Path
import build_baseline as b

class Test(unittest.TestCase):
    def test_only_expected_ci_branch(self):
        env=dict(GITHUB_REPOSITORY='uppet/ru_notepad',GITHUB_REF='refs/heads/notepadpp-comparison',GITHUB_EVENT_NAME='push',GITHUB_SHA='a'*40)
        b.host_guard(env,'nt')
        for k,v in [('GITHUB_REF','refs/heads/mi-perf-prototype'),('GITHUB_REF','refs/heads/main'),('GITHUB_EVENT_NAME','pull_request'),('GITHUB_SHA','unknown')]:
            with self.subTest(k=k,v=v),self.assertRaises(ValueError):b.host_guard(dict(env,**{k:v}),'nt')
        with self.assertRaises(ValueError):b.host_guard(env,'posix')
    def test_hardlink_does_not_relax_data_paths(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'gcc.exe';a.write_bytes(b'a');q=Path(d)/'alias';os.link(a,q)
            self.assertEqual(b.compiler_file(a),a.resolve())
            with self.assertRaises(ValueError):b.plain(a)
            with self.assertRaises(ValueError):b.plain(q)
    def test_symlink_not_even_compiler(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'gcc.exe';a.write_bytes(b'a');q=Path(d)/'alias'
            try:q.symlink_to(a)
            except OSError:self.skipTest('symlink unavailable')
            with self.assertRaises(ValueError):b.compiler_file(q)
    def test_json_duplicate_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'receipt';p.write_text('{"schema":1,"schema":2}')
            with self.assertRaises(ValueError):b.read(p)
    def test_dependency_exact_hash_and_target(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'source.zip';v=root/'vendor';v.mkdir()
            with zipfile.ZipFile(p,'w') as z:z.writestr('scintilla/file.c','source')
            h=b.sha(p);size=p.stat().st_size
            with self.assertRaises(ValueError):b.extract_dependency(p,v,size,'0'*64,'scintilla')
            b.extract_dependency(p,v,size,h,'scintilla')
            self.assertEqual((v/'scintilla/file.c').read_text(),'source')
            with self.assertRaises(ValueError):b.extract_dependency(p,v,size,h,'scintilla')
    def test_dependency_wrong_root_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'source.zip';v=root/'vendor';v.mkdir()
            with zipfile.ZipFile(p,'w') as z:z.writestr('other/file','source')
            with self.assertRaises(ValueError):b.extract_dependency(p,v,p.stat().st_size,b.sha(p),'scintilla')
    def tools(self, root):
        for name in b.TOOLS:
            original=root/(name+'.package-original');original.write_bytes(('official-fixture:'+name).encode())
            os.link(original,root/name)
    def version(self,cmd,**kwargs):
        return subprocess.CompletedProcess(cmd,0,b'synthetic-version\n',b'')
    def test_all_six_hardlink_aliases_accepted_and_bound(self):
        with tempfile.TemporaryDirectory() as d,patch.object(b.subprocess,'run',side_effect=self.version):
            root=Path(d);self.tools(root);record=b.tool_snapshot(root)
            self.assertEqual(set(record),set(b.TOOLS));b.verify_tools(root,record)
            for name in b.TOOLS:self.assertEqual(record[name]['path'],str((root/name).resolve()))
    def test_alias_mutation_rejected_even_same_version(self):
        with tempfile.TemporaryDirectory() as d,patch.object(b.subprocess,'run',side_effect=self.version):
            root=Path(d);self.tools(root);record=b.tool_snapshot(root)
            (root/'g++.exe.package-original').write_bytes(b'mutated through alias')
            with self.assertRaises(ValueError):b.verify_tools(root,record)
    def test_equal_bytes_different_tool_directory_rejected(self):
        with tempfile.TemporaryDirectory() as d,patch.object(b.subprocess,'run',side_effect=self.version):
            a=Path(d)/'a';a.mkdir();c=Path(d)/'b';c.mkdir();self.tools(a);self.tools(c)
            record=b.tool_snapshot(a)
            with self.assertRaises(ValueError):b.verify_tools(c,record)
    def test_runtime_name_not_build_tool(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'Scintilla.dll';p.write_bytes(b'bytes');os.link(p,root/'alias')
            with self.assertRaises(ValueError):b.tool_file(root,'Scintilla.dll')
            with self.assertRaises(ValueError):b.plain(p)
    def test_tool_directory_is_not_regular_file(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'windres.exe').mkdir()
            with self.assertRaises(ValueError):b.tool_file(root,'windres.exe')
    def test_tool_reparse_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            # Windows temporary paths may contain 8.3 aliases; match the canonical path
            # used by tool_file so the injected reparse attribute is actually exercised.
            root=Path(d).resolve();target=root/'ar.exe';target.write_bytes(b'bytes');original=Path.lstat
            def inspect(path):
                if path==target:return SimpleNamespace(st_file_attributes=0x400,st_mode=original(path).st_mode)
                return original(path)
            with patch.object(Path,'lstat',inspect),self.assertRaises(ValueError):b.tool_file(root,'ar.exe')
    def test_real_source_archive_pins(self):
        root=Path(__file__).resolve().parent.parent/'public-recovery-20261021/markdown_edit_profile'
        if not root.exists():self.skipTest('reviewed source not present')
        for name,size,h,folder in b.ARCHIVES:
            files=list((root/'third_party/source_archives').rglob(name))
            if not files:self.skipTest('official archive bytes absent')
            self.assertEqual(files[0].stat().st_size,size);self.assertEqual(b.sha(files[0]),h)

if __name__=='__main__':unittest.main()
