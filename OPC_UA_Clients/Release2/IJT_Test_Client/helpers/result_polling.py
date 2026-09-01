"""
Bounded polling for result evidence that a server publishes asynchronously.

A joining operation accepted by a trigger does not have to be visible the
instant ``StartSelectedJoining`` (or a simulator method) returns.  Reading the
evidence once after a fixed one-second sleep either wastes a second on a fast
simulator or fails a slower real controller for no good reason.

``poll_until_result_id_changes`` closes that gap: it reads immediately, returns
as soon as a *new, non-empty* ResultId is observed, and otherwise re-reads at a
short interval until the caller's budget — normally
``result_trigger.active_result_timeout_s`` — is spent.  The full budget is only
ever consumed when the evidence genuinely never arrives.

Usage::

    poll = await poll_until_result_id_changes(
        lambda: meta_node.read_value(),
        baseline_id,
        timeout_s=result_trigger.active_result_timeout_s,
    )
    assert poll.changed, f"no new result after {poll.timeout_s}s ({poll.reads} reads)"

The ``sleep`` and ``clock`` hooks exist so unit tests can prove both the
delayed-success and the timeout path without real waiting.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

# Re-read cadence.  Short enough that a fast simulator is not held up, long
# enough that a slow controller is not flooded with reads.
DEFAULT_POLL_INTERVAL_S = 0.25


def extract_result_id(payload: Any) -> str:
    """Return the ResultId string carried by *payload*, or ``""``."""
    if payload is None:
        return ""
    cls_name = type(payload).__name__
    if cls_name in ("ExtensionObject", "Variant"):
        body = getattr(payload, "Body", None)
        if body is not None:
            payload = body
        else:
            val = getattr(payload, "Value", None)
            if val is not None:
                payload = val
    meta = getattr(payload, "ResultMetaData", payload)
    if meta is None:
        return ""
    result_id = getattr(meta, "ResultId", None)
    if result_id is None:
        return ""
    return str(result_id)


@dataclass(frozen=True)
class ResultIdPollOutcome:
    """Evidence produced by a bounded ResultId poll.

    Attributes:
        changed:      True when a new, non-empty ResultId was observed.
        result_id:    The last ResultId read (``""`` when unreadable/empty).
        baseline_id:  The ResultId the poll started from.
        value:        The last payload returned by the read callable.
        reads:        How many reads were issued.
        elapsed_s:    Seconds spent polling, measured on the injected clock.
        timeout_s:    The budget the poll was allowed to spend.
    """

    changed: bool
    result_id: str
    baseline_id: str
    value: Any
    reads: int
    elapsed_s: float
    timeout_s: float


async def _default_sleep(delay: float) -> None:
    await asyncio.sleep(delay)


def _default_clock() -> float:
    return time.monotonic()


async def poll_until_result_id_changes(
    read_payload: Callable[[], Awaitable[Any]],
    baseline_id: str,
    *,
    timeout_s: float,
    poll_interval_s: float = DEFAULT_POLL_INTERVAL_S,
    sleep: Callable[[float], Awaitable[None]] | None = None,
    clock: Callable[[], float] | None = None,
) -> ResultIdPollOutcome:
    """Poll *read_payload* until it reports a new ResultId or *timeout_s* expires.

    The first read happens immediately, so evidence that is already present
    costs no wall-clock time at all.  An empty or unreadable ResultId is never
    treated as a change, which keeps a transient read failure from being
    mistaken for a new result.

    Args:
        read_payload:    Async callable returning a result/ResultMetaData payload.
                         Exceptions propagate to the caller unchanged.
        baseline_id:     ResultId observed before the operation was triggered.
        timeout_s:       Total budget, normally ``trigger.active_result_timeout_s``.
        poll_interval_s: Delay between reads; never overshoots the deadline.
        sleep:           Await-able delay hook (defaults to ``asyncio.sleep``).
        clock:           Monotonic clock hook (defaults to ``time.monotonic``).

    Returns:
        A :class:`ResultIdPollOutcome` describing what was observed.
    """
    do_sleep = sleep or _default_sleep
    now = clock or _default_clock
    interval = max(poll_interval_s, 0.0)

    baseline = str(baseline_id or "")
    started_at = now()
    deadline = started_at + max(timeout_s, 0.0)

    payload: Any = None
    result_id = ""
    reads = 0

    while True:
        payload = await read_payload()
        reads += 1
        result_id = extract_result_id(payload)
        if result_id and result_id != baseline:
            return ResultIdPollOutcome(
                changed=True,
                result_id=result_id,
                baseline_id=baseline,
                value=payload,
                reads=reads,
                elapsed_s=now() - started_at,
                timeout_s=timeout_s,
            )
        remaining = deadline - now()
        if remaining <= 0:
            return ResultIdPollOutcome(
                changed=False,
                result_id=result_id,
                baseline_id=baseline,
                value=payload,
                reads=reads,
                elapsed_s=now() - started_at,
                timeout_s=timeout_s,
            )
        await do_sleep(min(interval, remaining))
