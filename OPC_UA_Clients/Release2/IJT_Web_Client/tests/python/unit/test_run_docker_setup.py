"""Unit tests for run_docker_setup.py (no Docker daemon required)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_MODULE_PATH = _PROJECT_ROOT / "run_docker_setup.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("ijt_run_docker_setup", _MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def rds():
    return _load_module()


def test_compose_project_name_is_stable_and_path_derived(rds):
    first = rds.compose_project_name(_PROJECT_ROOT)
    second = rds.compose_project_name(_PROJECT_ROOT)
    assert first == second
    assert first.startswith("ijtweb")
    assert len(first) > len("ijtweb")
    other = rds.compose_project_name(_PROJECT_ROOT.parent)
    assert other != first


def test_image_name_uses_project_suffix(rds):
    name = rds.image_name_for_checkout(_PROJECT_ROOT)
    assert name.startswith("ijt_web_client:ijtweb")


def test_compose_cmd_requires_compose_v2(rds, monkeypatch):
    monkeypatch.setattr(rds, "docker_available", lambda: True)

    class Result:
        returncode = 1
        stdout = ""
        stderr = "compose unknown"

    monkeypatch.setattr(rds.subprocess, "run", lambda *a, **k: Result())
    with pytest.raises(RuntimeError, match="Compose CLI v2"):
        rds.compose_cmd()


def test_docker_running_times_out_as_unavailable(rds, monkeypatch):
    monkeypatch.setattr(rds, "docker_available", lambda: True)

    def boom(*_a, **_k):
        raise rds.subprocess.TimeoutExpired(cmd=["docker", "info"], timeout=1)

    monkeypatch.setattr(rds.subprocess, "run", boom)
    assert rds.docker_running() is False


def test_run_docker_passes_setup_args_and_down_v(rds, monkeypatch):
    calls: list[list[str]] = []

    monkeypatch.setattr(rds, "compose_cmd", lambda: ["docker", "compose"])
    monkeypatch.setattr(rds, "compose_project_name", lambda: "ijtwebtest")
    monkeypatch.setattr(rds, "image_name_for_checkout", lambda: "ijt_web_client:ijtwebtest")

    def capture(cmd, check=True, cwd=None, env=None, timeout=None):
        calls.append(list(cmd))
        if env is not None:
            assert env["COMPOSE_PROJECT_NAME"] == "ijtwebtest"
            assert env["IJT_WEB_IMAGE"] == "ijt_web_client:ijtwebtest"
            assert env["IJT_SETUP_ARGS"] == "--force_full --skip-npm"
        return __import__("subprocess").CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(rds, "run_command", capture)
    rds.run_docker(["--force_full", "--skip-npm"], follow_logs=False, no_cache=True)

    assert any(cmd[:3] == ["docker", "compose", "down"] and "-v" in cmd for cmd in calls)
    assert any(cmd[:2] == ["docker", "build"] and "--no-cache" in cmd for cmd in calls)
    assert any(cmd[:3] == ["docker", "compose", "up"] for cmd in calls)
