"""
Console Client test configuration.
Adds the console client root to sys.path so bare-import modules
(event_handler, utils, serialize_data, etc.) are importable.
"""
import sys
from pathlib import Path

_CONSOLE_ROOT = Path(__file__).resolve().parent.parent
if str(_CONSOLE_ROOT) not in sys.path:
    sys.path.insert(0, str(_CONSOLE_ROOT))
