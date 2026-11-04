"""Include the portable regex oracle and UI contracts in cheap preflight.

These tests inspect source and oracle contracts; they do not claim Windows GUI
execution or replace the required same-binary regex product gate.
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_regex_policy_runner import RegexOracleTests
from test_regex_ui_contract import RegexUIContract
