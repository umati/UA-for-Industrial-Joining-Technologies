"""Unit tests for the Web Client backend lifecycle manager."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from tests.test_infra.backend_manager import (
    UA_NAMESPACE_URI,
    BackendCrashedError,
    BackendHealthError,
    HealthStatus,
    WebTestBackendManager,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def workspace(request):
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", request.node.name)
    path = _PROJECT_ROOT / "tmp" / "backend-manager-unit" / safe_name
    path.mkdir(parents=True, exist_ok=True)
    return path


class _FakeWebSocket:
    def __init__(self, replies: list[dict]):
        self.replies = replies
        self.sent: list[dict] = []

    async def send(self, raw: str) -> None:
        self.sent.append(json.loads(raw))

    async def recv(self) -> str:
        return json.dumps(self.replies.pop(0))


class _FakeConnect:
    def __init__(self, websocket: _FakeWebSocket):
        self.websocket = websocket

    async def __aenter__(self) -> _FakeWebSocket:
        return self.websocket

    async def __aexit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
        return None


class _FakeProc:
    def __init__(self, returncode: int | None = None):
        self.returncode = returncode
        self.terminated = False
        self.killed = False
        self.wait_timeouts: list[float | None] = []

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True
        self.returncode = 0

    def wait(self, timeout: float | None = None) -> int | None:
        self.wait_timeouts.append(timeout)
        return self.returncode

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9


def _manager(workspace, **kwargs) -> WebTestBackendManager:
    return WebTestBackendManager(
        ws_port=8101,
        opcua_port=41463,
        label="unit",
        root=workspace,
        results_root=workspace / "results",
        **kwargs,
    )


def test_health_probe_runs_full_connect_namespaces_terminate_contract(monkeypatch, workspace):
    replies = [
        {"uniqueid": 1, "data": {}},
        {"uniqueid": 2, "data": {"namespaces": [UA_NAMESPACE_URI]}},
        {"uniqueid": 3, "data": {}},
    ]
    websocket = _FakeWebSocket(replies)

    def fake_connect(url, **kwargs):
        assert url == "ws://127.0.0.1:8101/"
        assert kwargs["open_timeout"] == 1
        return _FakeConnect(websocket)

    monkeypatch.setitem(sys.modules, "websockets", SimpleNamespace(connect=fake_connect))

    status = _manager(workspace).health()

    assert status.ok is True
    assert [payload["command"] for payload in websocket.sent] == ["connect to", "namespaces", "terminate connection"]
    assert all(payload["endpoint"] == "opc.tcp://localhost:41463" for payload in websocket.sent)


def test_health_probe_rejects_wrong_namespace_envelope(monkeypatch, workspace):
    replies = [
        {"uniqueid": 1, "data": {}},
        {"uniqueid": 2, "data": {"namespaces": ["urn:example"]}},
    ]

    monkeypatch.setitem(
        sys.modules,
        "websockets",
        SimpleNamespace(connect=lambda *_args, **_kwargs: _FakeConnect(_FakeWebSocket(replies))),
    )

    status = _manager(workspace).health()

    assert status.ok is False
    assert status.step == "namespaces"
    assert "UA namespace" in status.detail


def test_assert_healthy_reports_crashed_backend_with_typed_error(workspace):
    manager = _manager(workspace)
    manager._crashed = True
    (workspace / "results").mkdir(exist_ok=True)
    (workspace / "results" / "websocket.log").write_text("last backend line\n", encoding="utf-8")

    with pytest.raises(BackendCrashedError) as excinfo:
        manager.assert_healthy()

    assert "backend process exited unexpectedly" in str(excinfo.value)
    assert "last backend line" in str(excinfo.value)


def test_start_is_idempotent_after_services_are_started(monkeypatch, workspace):
    manager = _manager(workspace, opcua_command=["opcua-simulator"])
    popen_calls = []

    def fake_popen(cmd, **_kwargs):
        popen_calls.append(cmd)
        return _FakeProc()

    monkeypatch.setattr(manager, "health", lambda: HealthStatus(ok=True, step="terminate connection"))
    monkeypatch.setattr("tests.test_infra.backend_manager.subprocess.Popen", fake_popen)
    monkeypatch.setattr(manager, "_port_open", lambda _port: False)

    manager.start()
    manager.start()

    assert manager._started is True
    assert popen_calls == [["opcua-simulator"], [sys.executable, "index.py"]]
    assert (workspace / "results" / "backend-events.jsonl").exists()


def test_start_requires_opcua_launcher_when_port_is_closed(monkeypatch, workspace):
    manager = _manager(workspace)
    monkeypatch.setattr(manager, "_port_open", lambda _port: False)

    with pytest.raises(BackendHealthError, match="no opcua_command"):
        manager.start()


def test_start_fails_loudly_when_managed_port_is_already_in_use(monkeypatch, workspace):
    manager = _manager(workspace, opcua_command=["opcua-simulator"])
    monkeypatch.setattr(manager, "_port_open", lambda _port: True)

    with pytest.raises(BackendHealthError, match="already in use"):
        manager.start()


def test_stop_releases_ports_or_fails_loudly(monkeypatch, workspace):
    manager = _manager(workspace)
    manager._ws_proc = cast(Any, _FakeProc())
    manager._opcua_proc = cast(Any, _FakeProc())
    monkeypatch.setattr(manager, "_port_open", lambda _port: False)

    manager.stop()

    assert manager._ws_proc is None
    assert manager._opcua_proc is None


def test_stop_fails_when_port_remains_open(monkeypatch, workspace):
    manager = _manager(workspace)
    manager._ws_proc = cast(Any, _FakeProc())

    def fake_wait_for_port_free(_port: int) -> None:
        raise BackendHealthError("port 8101 was still listening after backend stop")

    monkeypatch.setattr(manager, "_wait_for_port_free", fake_wait_for_port_free)

    with pytest.raises(BackendHealthError, match="still listening"):
        manager.stop()
