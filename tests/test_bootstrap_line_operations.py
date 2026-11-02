"""Include line GUI fail-closed contracts in the existing cheap preflight suite."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from test_gui_line_operations import Contract
