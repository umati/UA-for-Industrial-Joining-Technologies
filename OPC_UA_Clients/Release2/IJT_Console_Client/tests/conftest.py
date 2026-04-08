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


def pytest_configure(config):
    """Ensure tests/fixtures/ exists so --basetemp=tests/fixtures/tmp never fails."""
    del config  # required parameter name in pytest hookspec; not needed in body
    Path(__file__).parent.joinpath("fixtures").mkdir(parents=True, exist_ok=True)
