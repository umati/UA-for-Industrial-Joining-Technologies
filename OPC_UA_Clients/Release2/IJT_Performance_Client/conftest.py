"""
conftest.py for IJT Performance Client.
Ensures ijt_performance_client is importable regardless of test invocation directory.
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True

_CLIENT_ROOT = Path(__file__).resolve().parent
if str(_CLIENT_ROOT) not in sys.path:
    sys.path.insert(0, str(_CLIENT_ROOT))
