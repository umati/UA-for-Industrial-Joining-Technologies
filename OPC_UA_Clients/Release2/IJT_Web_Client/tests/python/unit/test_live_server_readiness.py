"""Unit coverage for live fixture startup diagnostics and readiness probes."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

from tests.python import _live_server_readiness as readiness


def test_fixture_fail_fast_when_marker_port_closed_includes_log_paths(tmp_path):
    message = readiness.prestarted_port_closed_message(tmp_path, 40463)

    assert "Runner prestarted OPC UA server on port 40463" in message
    assert str(tmp_path / "test-results" / "opcua-server-40463.out.log") in message
    assert str(tmp_path / "test-results" / "opcua-server-40463.err.log") in message


def test_start_process_with_opcua_logs_appends_and_closes_parent_handles(monkeypatch, tmp_path):
    captured = {}

    class FakeProc:
        pass

    def fake_popen(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["cwd"] = kwargs["cwd"]
        captured["stdin"] = kwargs["stdin"]
        captured["stdout"] = kwargs["stdout"]
        captured["stderr"] = kwargs["stderr"]
        captured["stdout_name"] = kwargs["stdout"].name
        captured["stderr_name"] = kwargs["stderr"].name
        return FakeProc()

    monkeypatch.setattr(readiness.subprocess, "Popen", fake_popen)

    proc = readiness.start_process_with_opcua_logs(
        ["simulator.exe"],
        cwd=tmp_path,
        web_client_root=tmp_path,
        port=40463,
    )

    assert isinstance(proc, FakeProc)
    assert captured["cmd"] == ["simulator.exe"]
    assert captured["cwd"] == str(tmp_path)
    assert captured["stdin"] is readiness.subprocess.DEVNULL
    assert Path(captured["stdout_name"]) == tmp_path / "test-results" / "opcua-server-40463.out.log"
    assert Path(captured["stderr_name"]) == tmp_path / "test-results" / "opcua-server-40463.err.log"
    assert captured["stdout"].closed is True
    assert captured["stderr"].closed is True


def test_protocol_warmup_retries_first_opcua_connect(monkeypatch):
    attempts = []
    sleeps = []
    connects = 0

    class FakeClient:
        def __init__(self, endpoint, timeout):
            assert endpoint == "opc.tcp://localhost:40463"
            assert timeout == 1.25

        async def connect(self):
            nonlocal connects
            connects += 1
            attempts.append("connect")
            if connects < 3:
                raise TimeoutError("server still warming")

        async def disconnect(self):
            attempts.append("disconnect")

    monkeypatch.setitem(sys.modules, "asyncua", SimpleNamespace(Client=FakeClient))
    monkeypatch.setattr(readiness.time, "sleep", lambda seconds: sleeps.append(seconds))

    error = readiness.wait_for_opcua_protocol_ready("opc.tcp://localhost:40463")

    assert error is None
    assert attempts == ["connect", "disconnect", "connect", "disconnect", "connect", "disconnect"]
    assert sleeps == [1.0, 1.0]


def test_protocol_warmup_retries_first_websocket_ping(monkeypatch):
    attempts = []
    sleeps = []

    class FakeWebSocket:
        def ping(self):
            attempts.append("ping")
            if len(attempts) < 3:
                raise TimeoutError("websocket still warming")
            return None

    class FakeConnect:
        def __init__(self, url, **kwargs):
            assert url == "ws://localhost:8001"
            assert kwargs["open_timeout"] == 1.25
            assert kwargs["close_timeout"] == 0.5

        async def __aenter__(self):
            return FakeWebSocket()

        async def __aexit__(self, _exc_type, _exc, _tb):
            return None

    monkeypatch.setitem(sys.modules, "websockets", SimpleNamespace(connect=FakeConnect))
    monkeypatch.setattr(readiness.time, "sleep", lambda seconds: sleeps.append(seconds))

    error = readiness.wait_for_websocket_protocol_ready("ws://localhost:8001", "opc.tcp://localhost:40463")

    assert error is None
    assert attempts == ["ping", "ping", "ping"]
    assert sleeps == [1.0, 1.0]
