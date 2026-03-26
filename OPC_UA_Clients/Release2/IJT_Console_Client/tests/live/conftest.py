import sys
from pathlib import Path

_CONSOLE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_CONSOLE_ROOT) not in sys.path:
    sys.path.insert(0, str(_CONSOLE_ROOT))
