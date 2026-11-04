"""Portable regex GUI contract checks; actual Windows execution is separate."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from test_gui_regex_search import Contract
