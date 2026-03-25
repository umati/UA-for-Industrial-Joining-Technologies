"""
Unit-test conftest: overrides tmp_path to use a project-local directory.

On some Windows machines pytest cannot access AppData/Local/Temp/pytest-of-*
due to ACL restrictions. Using a path inside the repo avoids that problem.
The directory is cleaned up after each test via a finalizer.
"""
import shutil
import uuid
from pathlib import Path

import pytest

_UNIT_TMP_BASE = Path(__file__).parents[3] / "tests" / "fixtures" / "tmp"


@pytest.fixture
def tmp_path(request):
    """Project-local tmp_path replacement that avoids AppData permission issues."""
    _UNIT_TMP_BASE.mkdir(parents=True, exist_ok=True)
    d = _UNIT_TMP_BASE / ("t_" + uuid.uuid4().hex[:10])
    d.mkdir(parents=True)

    def _cleanup():
        shutil.rmtree(d, ignore_errors=True)

    request.addfinalizer(_cleanup)
    return d
