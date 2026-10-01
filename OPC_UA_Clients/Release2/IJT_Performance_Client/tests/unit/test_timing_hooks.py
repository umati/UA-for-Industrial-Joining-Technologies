"""Unit tests for the asyncua wire timing hooks and the event-loop lag monitor."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from asyncua import ua
from asyncua.client.ua_client import UASocketProtocol
from asyncua.client.ua_session import UaSession
from asyncua.common.utils import Buffer
from asyncua.ua.ua_binary import nodeid_to_binary, struct_to_binary

from src.engine import timing_hooks
from src.engine.timing_hooks import LoopLagMonitor, current_publish_timing, install_timing_hooks


@pytest.fixture(scope="module", autouse=True)
def _hooks_installed():
    status = install_timing_hooks()
    assert status.installed, status.reason


def _body(object_id: int) -> Buffer:
    return Buffer(nodeid_to_binary(ua.FourByteNodeId(object_id)) + b"payload")


def _fake_protocol(future: asyncio.Future) -> SimpleNamespace:
    return SimpleNamespace(_callbackmap={1: future}, is_session_closing=None, logger=logging.getLogger("t"))


def test_self_test_passes_on_supported_asyncua():
    assert timing_hooks._self_test() is None


def test_install_is_idempotent_and_marks_wrappers():
    assert install_timing_hooks() is install_timing_hooks()
    assert getattr(UASocketProtocol._call_callback, timing_hooks._HOOKED_ATTR, False)
    assert getattr(UaSession.publish, timing_hooks._HOOKED_ATTR, False)


def test_install_falls_back_when_self_test_fails(monkeypatch):
    monkeypatch.setattr(timing_hooks, "_status", None)
    monkeypatch.setattr(timing_hooks, "_self_test", lambda: "internals changed")
    status = install_timing_hooks()
    assert status.installed is False
    assert status.reason == "internals changed"


def test_self_test_detects_signature_change(monkeypatch):
    monkeypatch.setattr(UASocketProtocol, "_call_callback", lambda self, rid: None)
    assert "signature changed" in (timing_hooks._self_test() or "")


@pytest.mark.asyncio
async def test_call_callback_records_arrival_only_for_publish_responses():
    loop = asyncio.get_running_loop()

    fut = loop.create_future()
    proto = _fake_protocol(fut)
    before = datetime.now(UTC)
    body = _body(ua.ObjectIds.PublishResponse_Encoding_DefaultBinary)
    UASocketProtocol._call_callback(proto, 1, body)
    assert before <= proto._ijt_publish_arrival <= datetime.now(UTC)
    # The original behaviour is preserved and the body is not consumed by the peek
    assert fut.result() is body
    assert body.copy().read(4) == nodeid_to_binary(
        ua.FourByteNodeId(ua.ObjectIds.PublishResponse_Encoding_DefaultBinary)
    )

    fut = loop.create_future()
    proto = _fake_protocol(fut)
    UASocketProtocol._call_callback(proto, 1, _body(ua.ObjectIds.ReadResponse_Encoding_DefaultBinary))
    assert not hasattr(proto, "_ijt_publish_arrival")

    fut = loop.create_future()
    proto = _fake_protocol(fut)
    UASocketProtocol._call_callback(proto, 1, ua.Acknowledge())
    assert isinstance(fut.result(), ua.Acknowledge)

    fut = loop.create_future()
    proto = _fake_protocol(fut)
    UASocketProtocol._call_callback(proto, 1, Buffer(b"\x01"))  # truncated type id must not break dispatch
    assert fut.done()


def _fake_session(arrival: datetime | None) -> SimpleNamespace:
    protocol = SimpleNamespace(_ijt_publish_arrival=datetime(2000, 1, 1, tzinfo=UTC))  # stale value must be reset

    async def _send_request(request, timeout=0):
        assert protocol._ijt_publish_arrival is None
        if arrival is not None:
            protocol._ijt_publish_arrival = arrival
        return Buffer(struct_to_binary(ua.PublishResponse()))

    return SimpleNamespace(
        logger=logging.getLogger("t"), _send_request=_send_request, _client=SimpleNamespace(protocol=protocol)
    )


@pytest.mark.asyncio
async def test_publish_hook_sets_timing_visible_to_dispatched_handler_tasks():
    arrival = datetime.now(UTC)

    async def publish_loop(session, arrival_value):
        response = await UaSession.publish(session, [])
        assert isinstance(response, ua.PublishResponse)

        # asyncua dispatches handlers with create_task, which copies the publish-loop context
        async def handler():
            return current_publish_timing()

        return await asyncio.create_task(handler())

    timing = await asyncio.create_task(publish_loop(_fake_session(arrival), arrival))
    assert timing is not None
    assert timing[0] == arrival
    assert timing[1] >= arrival

    # A separate session's publish loop has its own timing, so sessions never mix
    other = await asyncio.create_task(publish_loop(_fake_session(None), None))
    assert other is not None and other[0] is None
    assert current_publish_timing() is None


@pytest.mark.asyncio
async def test_loop_lag_monitor_measures_blocking():
    monitor = LoopLagMonitor(interval_s=0.01)
    monitor.start()
    await asyncio.sleep(0.03)
    time.sleep(0.1)  # block the event loop
    await asyncio.sleep(0.03)
    monitor.stop()
    monitor.stop()
    snap = monitor.snapshot()
    assert snap["ticks"] >= 2
    assert snap["max_ms"] >= 50.0
    assert 0.0 <= snap["mean_ms"] <= snap["max_ms"]


def test_loop_lag_monitor_snapshot_without_ticks():
    assert LoopLagMonitor().snapshot() == {"max_ms": 0.0, "mean_ms": 0.0, "ticks": 0}
