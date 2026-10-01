"""
Wire-level timestamps for subscription notifications (asyncua 2.0.1).

Why does this module exist?
The subscription handler runs in its own asyncio task after asyncua has received, decoded and
dispatched the PublishResponse. Timing only at handler entry mixes network delivery with client
decoding and event-loop scheduling. Two version-guarded hooks split those phases:

1. Bytes received: ``UASocketProtocol._call_callback`` runs once a complete (reassembled and, if
   secured, decrypted) message has been read from the socket. A cheap type-id peek records the time
   for PublishResponse messages on that connection. asyncua keeps only one Publish request in flight
   per session, so the latest PublishResponse time on a connection belongs to the response being decoded.
2. Decoded: ``UaSession.publish`` returns right after ``struct_from_binary`` has decoded the response.
   Both times are stored in a ContextVar inside the session's publish-loop task. asyncua dispatches each
   handler call with ``asyncio.create_task``, which copies that context, so every notification sees the
   timing of its own PublishResponse and sessions never mix.

Limits (documented in docs/PERFORMANCE_GUIDE.md):
- "Bytes received" is when the event loop read the data, so a busy loop delays it; the loop-lag
  monitor below reports how large that delay can be.
- Events wait on the server for up to one publishing interval before they are sent.

If the self-test fails (different asyncua internals), hooks are not installed and samples fall back
to handler-entry timing, labelled ``timing_source="handler"``.
"""

from __future__ import annotations

import asyncio
import contextvars
import inspect
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

_HOOKED_ATTR = "_ijt_timing_hooked"
_ARRIVAL_ATTR = "_ijt_publish_arrival"

# (bytes_received_time, decoded_time) for the PublishResponse currently being dispatched.
_publish_timing: contextvars.ContextVar[tuple[datetime | None, datetime] | None] = contextvars.ContextVar(
    "ijt_publish_timing", default=None
)


@dataclass(frozen=True)
class TimingHookStatus:
    installed: bool
    reason: str = ""


_status: TimingHookStatus | None = None


def current_publish_timing() -> tuple[datetime | None, datetime] | None:
    """Timing of the PublishResponse that triggered the current handler call, if hooks are active."""
    return _publish_timing.get()


def _self_test() -> str | None:
    """Return None when the asyncua internals match what the hooks expect, else the reason."""
    try:
        from asyncua import ua
        from asyncua.client.ua_client import UASocketProtocol
        from asyncua.client.ua_session import UaSession
        from asyncua.ua.ua_binary import nodeid_from_binary  # noqa: F401
    except ImportError as exc:
        return f"asyncua internals not importable: {exc}"
    call_cb = getattr(UASocketProtocol, "_call_callback", None)
    publish = getattr(UaSession, "publish", None)
    if call_cb is None or publish is None or not hasattr(UaSession, "_publish_loop"):
        return "asyncua hook targets missing (UASocketProtocol._call_callback / UaSession.publish)"
    if list(inspect.signature(call_cb).parameters) != ["self", "request_id", "body"]:
        return "UASocketProtocol._call_callback signature changed"
    if list(inspect.signature(publish).parameters) != ["self", "acks"] or not inspect.iscoroutinefunction(publish):
        return "UaSession.publish signature changed"
    if not hasattr(ua.ObjectIds, "PublishResponse_Encoding_DefaultBinary"):
        return "PublishResponse encoding id not available"
    return None


def install_timing_hooks() -> TimingHookStatus:
    """Install the hooks once per process. Safe to call repeatedly."""
    global _status
    if _status is not None:
        return _status
    reason = _self_test()
    if reason is not None:
        logger.warning(f"Wire timing hooks not installed ({reason}); using handler-entry timing.")
        _status = TimingHookStatus(installed=False, reason=reason)
        return _status

    from asyncua import ua
    from asyncua.client.ua_client import UASocketProtocol
    from asyncua.client.ua_session import UaSession
    from asyncua.ua.ua_binary import nodeid_from_binary

    publish_response_id = ua.NodeId(ua.Int32(ua.ObjectIds.PublishResponse_Encoding_DefaultBinary))
    original_call_callback = UASocketProtocol._call_callback
    original_publish = UaSession.publish
    if getattr(original_call_callback, _HOOKED_ATTR, False) or getattr(original_publish, _HOOKED_ATTR, False):
        _status = TimingHookStatus(installed=True)  # e.g. this module was reloaded; never wrap twice
        return _status

    def _call_callback(self: Any, request_id: int, body: Any) -> None:
        if not isinstance(body, ua.Acknowledge):
            try:
                if nodeid_from_binary(body.copy()) == publish_response_id:
                    setattr(self, _ARRIVAL_ATTR, datetime.now(UTC))
            except Exception:  # never let instrumentation break message handling
                pass
        original_call_callback(self, request_id, body)

    async def _publish(self: Any, acks: Any) -> Any:
        protocol = getattr(getattr(self, "_client", None), "protocol", None)
        if protocol is not None:
            setattr(protocol, _ARRIVAL_ATTR, None)
        response = await original_publish(self, acks)
        decoded = datetime.now(UTC)
        arrived = getattr(protocol, _ARRIVAL_ATTR, None) if protocol is not None else None
        _publish_timing.set((arrived, decoded))
        return response

    setattr(_call_callback, _HOOKED_ATTR, True)
    setattr(_publish, _HOOKED_ATTR, True)
    UASocketProtocol._call_callback = _call_callback  # type: ignore[method-assign]
    UaSession.publish = _publish  # type: ignore[method-assign]
    _status = TimingHookStatus(installed=True)
    logger.debug("Installed asyncua wire timing hooks")
    return _status


class LoopLagMonitor:
    """Measures event-loop scheduling lag with a self-rescheduling ``call_later`` callback.

    Lag is how late the callback runs versus when it was due. It bounds how long received bytes
    and ready handler tasks can wait before the loop serves them. Cost: one callback per interval.
    """

    def __init__(self, interval_s: float = 0.1) -> None:
        self.interval_s = interval_s
        self.max_lag_ms = 0.0
        self.total_lag_ms = 0.0
        self.ticks = 0
        self._due = 0.0
        self._handle: asyncio.TimerHandle | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._schedule()

    def _schedule(self) -> None:
        assert self._loop is not None
        self._due = time.perf_counter() + self.interval_s
        self._handle = self._loop.call_later(self.interval_s, self._tick)

    def _tick(self) -> None:
        lag_ms = max(0.0, (time.perf_counter() - self._due) * 1000.0)
        self.ticks += 1
        self.total_lag_ms += lag_ms
        self.max_lag_ms = max(self.max_lag_ms, lag_ms)
        self._schedule()

    def stop(self) -> None:
        if self._handle is not None:
            self._handle.cancel()
            self._handle = None

    def snapshot(self) -> dict[str, float | int]:
        mean = self.total_lag_ms / self.ticks if self.ticks else 0.0
        return {"max_ms": round(self.max_lag_ms, 3), "mean_ms": round(mean, 3), "ticks": self.ticks}
