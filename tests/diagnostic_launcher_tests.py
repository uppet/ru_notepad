#!/usr/bin/env python3
"""Portable policy execution + real MinGW cross-builds; no Windows emulation.

Run after sourcing .tools/env.sh:
  python3 tests/diagnostic_launcher_tests.py

Actual Win32 file/CRT/dialog behavior remains UNRUN by this Linux suite.
"""
from __future__ import annotations

import re
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "diagnostic_launcher"


def command(arguments):
    return subprocess.run(arguments, check=True, capture_output=True, text=True)


class DiagnosticLauncherTests(unittest.TestCase):
    def test_portable_path_policy_executes_on_host(self):
        compiler = shutil.which("cc")
        if not compiler:
            self.skipTest("No native host C compiler; policy execution UNRUN")
        with tempfile.TemporaryDirectory(prefix="ru-diag-policy-") as folder:
            output = Path(folder) / "policy-test"
            command([compiler, "-std=c99", "-Wall", "-Wextra", "-Werror",
                     str(FIXTURES / "policy_fixture.c"), "-o", str(output)])
            result = command([str(output)])
            self.assertIn("portable path policy passed", result.stdout)

    def test_windows_fixtures_cross_build_with_real_windows_headers(self):
        compiler = shutil.which("x86_64-w64-mingw32-gcc")
        if not compiler:
            self.skipTest("MinGW not on PATH; source .tools/env.sh; cross-build UNRUN")
        with tempfile.TemporaryDirectory(prefix="ru-diag-cross-") as folder:
            for mode in range(4):
                with self.subTest(mode=mode):
                    output = Path(folder) / f"launcher-{mode}.exe"
                    command([compiler, "-std=c99", "-Wall", "-Wextra", "-Werror",
                             "-static-libgcc", "-mwindows", f"-DFIXTURE_MODE={mode}",
                             str(FIXTURES / "windows_fixture.c"), "-lshell32",
                             "-o", str(output)])
                    self.assertEqual(output.read_bytes()[:2], b"MZ")

    def test_no_overwrite_or_environment_temp_apis_in_launcher(self):
        source = (ROOT / "packaging" / "diagnostic_launcher.c").read_text()
        source = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
        self.assertIn("CREATE_NEW", source)
        for forbidden in ("CREATE_ALWAYS", "TRUNCATE_EXISTING", "OPEN_ALWAYS",
                          "GetTempPath", "GetEnvironmentVariable", "system(",
                          "ShellExecute", "DeleteFile", "TerminateProcess("):
            self.assertNotIn(forbidden, source)
        self.assertIn("SHGetFolderPathW", source)
        self.assertIn("FILE_ATTRIBUTE_REPARSE_POINT", source)
        self.assertIn("FILE_SHARE_READ, NULL,", source)

    @unittest.skip("UNRUN: native Windows GUI, real CRT, ACL/reparse, collision and fallback acceptance required")
    def test_native_windows_file_and_dialog_behavior(self):
        pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
