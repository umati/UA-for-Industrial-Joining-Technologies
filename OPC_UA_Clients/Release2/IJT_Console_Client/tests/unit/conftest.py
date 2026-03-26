"""
Unit test configuration for IJT_Console_Client.
Adds the console client root to sys.path so modules are importable without installation.
"""
import sys
from pathlib import Path

_CONSOLE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_CONSOLE_ROOT) not in sys.path:
    sys.path.insert(0, str(_CONSOLE_ROOT))
