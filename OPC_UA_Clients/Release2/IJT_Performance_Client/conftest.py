"""
conftest.py for IJT Performance Client.
Ensures ijt_performance_client is importable regardless of test invocation directory.
"""

import sys
from pathlib import Path

_CLIENT_ROOT = Path(__file__).resolve().parent
if str(_CLIENT_ROOT) not in sys.path:
    sys.path.insert(0, str(_CLIENT_ROOT))
