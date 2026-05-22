from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path
from unittest.mock import Mock, call
from uuid import uuid4

import pytest


def _load_script_module():
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts" / "start_server_on_port.py"
    spec = importlib.util.spec_from_file_location("ijt_start_server_on_port", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_mod = _load_script_module()


def _make_repo_temp_dir() -> Path:
    root = Path(__file__).resolve().parents[1]
    base = root / "tmp" / "pytest-root-tests"
    base.mkdir(parents=True, exist_ok=True)
    workdir = base / uuid4().hex
    workdir.mkdir()
    return workdir


def test_write_github_env_appends_key_value(monkeypatch: pytest.MonkeyPatch) -> None:
    workdir = _make_repo_temp_dir()
    try:
        env_file = workdir / "github.env"
        monkeypatch.setenv("GITHUB_ENV", str(env_file))

        _mod._write_github_env("OPCUA_SERVER_PORT", "40464")
        _mod._write_github_env("SERVER_PID", "1234")

        assert env_file.read_text(encoding="utf-8") == "OPCUA_SERVER_PORT=40464\nSERVER_PID=1234\n"
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def test_wait_for_opcua_hello_is_delegated_to_shared_module() -> None:
    """The script must import the shared HELLO probe; it must not reintroduce
    a private TCP-only ``_wait_for_port`` loop."""

    assert hasattr(_mod, "wait_for_opcua_hello"), (
        "start_server_on_port.py must import wait_for_opcua_hello from "
        "ijt_live_readiness so the OPC UA HELLO probe is the readiness "
        "contract."
    )
    assert not hasattr(_mod, "_wait_for_port"), (
        "Readiness must go through ijt_live_readiness.wait_for_opcua_hello. Do not reintroduce "
        "a TCP-only poll loop in start_server_on_port.py."
    )


def test_default_tmp_base_uses_runner_temp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RUNNER_TEMP", r"D:\a\_temp")

    tmp_base = _mod._default_tmp_base()

    assert tmp_base == Path(r"D:\a\_temp") / "ijt-sim"
    assert len(str(tmp_base / "server_40464")) <= 100


def test_default_tmp_base_falls_back_to_system_temp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RUNNER_TEMP", raising=False)
    monkeypatch.setattr(_mod.tempfile, "gettempdir", lambda: r"C:\Temp")

    assert _mod._default_tmp_base() == Path(r"C:\Temp") / "ijt-sim"


def _ok_readiness(port: int, *, elapsed: float = 1.25, attempts: int = 1):
    """Return a ReadinessResult-shaped success object suitable for monkeypatching."""

    import ijt_live_readiness  # type: ignore[import-not-found]

    return ijt_live_readiness.ReadinessResult(
        ok=True,
        probe="opcua_hello",
        host="localhost",
        port=port,
        elapsed_seconds=elapsed,
        attempts=attempts,
        started_at="2026-05-22T00:00:00.000+00:00",
        finished_at="2026-05-22T00:00:01.250+00:00",
        error=None,
        endpoint=f"opc.tcp://localhost:{port}",
    )


def _fail_readiness(port: int):
    import ijt_live_readiness  # type: ignore[import-not-found]

    return ijt_live_readiness.ReadinessResult(
        ok=False,
        probe="opcua_hello",
        host="localhost",
        port=port,
        elapsed_seconds=30.0,
        attempts=10,
        started_at="2026-05-22T00:00:00.000+00:00",
        finished_at="2026-05-22T00:00:30.000+00:00",
        error=f"OPC UA HELLO probe to localhost:{port} did not get ACK/ERR within 30.0s",
        endpoint=f"opc.tcp://localhost:{port}",
    )


def test_start_server_patches_config_and_exports_env(monkeypatch: pytest.MonkeyPatch) -> None:
    workdir = _make_repo_temp_dir()
    try:
        server_dir = workdir / "server_src"
        server_dir.mkdir()
        cfg_path = server_dir / "server_configuration.json"
        cfg_path.write_text(
            json.dumps({"serverConfigurationData": {"serverEndpointTCPPort": 40451}}),
            encoding="utf-8",
        )
        exe_path = server_dir / "opcua_ijt_demo_application.exe"
        exe_path.write_text("binary", encoding="utf-8")

        proc = Mock()
        proc.pid = 4321
        proc.stdout = Mock()
        proc.stderr = Mock()
        export = Mock()

        monkeypatch.setattr(_mod.subprocess, "Popen", lambda *args, **kwargs: proc)
        monkeypatch.setattr(_mod, "wait_for_opcua_hello", lambda *a, **kw: _ok_readiness(40464))
        monkeypatch.setattr(_mod, "_spawn_log_pump", lambda *a, **kw: Mock())
        monkeypatch.setattr(_mod, "write_diagnostic_manifest", lambda *a, **kw: None)
        monkeypatch.setattr(_mod, "_write_github_env", export)

        _mod.start_server(40464, server_dir, workdir / "tmp", 30)

        copied_cfg = workdir / "tmp" / "server_40464" / "server_configuration.json"
        copied_data = json.loads(copied_cfg.read_text(encoding="utf-8"))
        assert copied_data["serverConfigurationData"]["serverEndpointTCPPort"] == 40464
        export.assert_has_calls(
            [
                call("SERVER_PID", "4321"),
                call("OPCUA_SERVER_PORT", "40464"),
                call("OPCUA_SERVER_URL", "opc.tcp://localhost:40464"),
            ]
        )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def test_start_server_exits_when_config_missing() -> None:
    workdir = _make_repo_temp_dir()
    try:
        server_dir = workdir / "server_src"
        server_dir.mkdir()
        (server_dir / "opcua_ijt_demo_application.exe").write_text("binary", encoding="utf-8")

        with pytest.raises(SystemExit) as excinfo:
            _mod.start_server(40464, server_dir, workdir / "tmp", 30)

        assert excinfo.value.code == 1
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def test_start_server_timeout_kills_process_and_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    workdir = _make_repo_temp_dir()
    try:
        server_dir = workdir / "server_src"
        server_dir.mkdir()
        (server_dir / "server_configuration.json").write_text(
            json.dumps({"serverConfigurationData": {"serverEndpointTCPPort": 40451}}),
            encoding="utf-8",
        )
        (server_dir / "opcua_ijt_demo_application.exe").write_text("binary", encoding="utf-8")

        proc = Mock()
        proc.pid = 9876
        proc.stdout = Mock()
        proc.stderr = Mock()
        monkeypatch.setattr(_mod.subprocess, "Popen", lambda *args, **kwargs: proc)
        monkeypatch.setattr(_mod, "wait_for_opcua_hello", lambda *a, **kw: _fail_readiness(40464))
        monkeypatch.setattr(_mod, "_spawn_log_pump", lambda *a, **kw: Mock())
        monkeypatch.setattr(_mod, "write_diagnostic_manifest", lambda *a, **kw: None)
        monkeypatch.setattr(_mod, "capture_process_log_tail", lambda *a, **kw: None)

        with pytest.raises(SystemExit) as excinfo:
            _mod.start_server(40464, server_dir, workdir / "tmp", 30)

        assert excinfo.value.code == 1
        proc.kill.assert_called_once()
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def test_stop_server_windows_removes_tmp_dir_and_stops_pid(monkeypatch: pytest.MonkeyPatch) -> None:
    workdir = _make_repo_temp_dir()
    try:
        tmp_base = workdir / "tmp"
        dst_dir = tmp_base / "server_40464"
        dst_dir.mkdir(parents=True)
        (dst_dir / "marker.txt").write_text("x", encoding="utf-8")

        run_calls: list[list[str]] = []
        monkeypatch.setenv("SERVER_PID", "2468")
        monkeypatch.setattr(_mod.sys, "platform", "win32")
        monkeypatch.setattr(
            _mod.subprocess,
            "run",
            lambda cmd, **kwargs: run_calls.append(cmd),
        )

        _mod.stop_server(40464, tmp_base)

        assert run_calls == [["taskkill", "/F", "/PID", "2468"]]
        assert not dst_dir.exists()
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def test_stop_server_posix_removes_tmp_dir_and_stops_pid(monkeypatch: pytest.MonkeyPatch) -> None:
    workdir = _make_repo_temp_dir()
    try:
        tmp_base = workdir / "tmp"
        dst_dir = tmp_base / "server_40464"
        dst_dir.mkdir(parents=True)
        (dst_dir / "marker.txt").write_text("x", encoding="utf-8")

        kill_calls: list[tuple[int, int]] = []
        monkeypatch.setenv("SERVER_PID", "2468")
        monkeypatch.setattr(_mod.sys, "platform", "linux")
        monkeypatch.setattr(_mod.os, "kill", lambda pid, sig: kill_calls.append((pid, sig)))

        _mod.stop_server(40464, tmp_base)

        assert kill_calls == [(2468, _mod.signal.SIGTERM)]
        assert not dst_dir.exists()
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


class _DummySocket:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False
