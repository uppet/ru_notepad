"""Portable receipt/source checks only; not a Windows execution receipt."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(0,str(ROOT/'tests'))
from test_gui_open_search import Contract
# Engine architecture checks are mandatory; absent modules must fail closed.
from test_open_search_contract import OpenSearchContract
