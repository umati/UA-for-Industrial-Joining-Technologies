from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest


def _load_hook():
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "precommit_pytest_hook.py"
    spec = importlib.util.spec_from_file_location("ijt_precommit_pytest_hook", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("returncode", [0, 1])
def test_pytest_temp_directory_is_unique_and_cleaned(monkeypatch, returncode):
    module = _load_hook()
    monkeypatch.setattr(module, "_ensure_pytest_dependencies", lambda: 0)
    monkeypatch.setattr(sys, "argv", ["precommit_pytest_hook.py", "tests/example.py"])
    seen = []

    def fake_run(cmd, *, cwd, check):
        basetemp = Path(cmd[4])
        assert cmd[:4] == [sys.executable, "-m", "pytest", "--basetemp"]
        assert cmd[5:] == ["tests/example.py"]
        assert basetemp.is_dir()
        assert cwd == str(module.REPO_ROOT)
        assert check is False
        seen.append(basetemp)
        return subprocess.CompletedProcess(cmd, returncode)

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    assert module.main() == returncode
    assert len(seen) == 1
    assert not seen[0].exists()
