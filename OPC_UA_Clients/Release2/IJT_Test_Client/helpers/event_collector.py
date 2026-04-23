"""
OPC UA IJT Tightening Test Framework — Event collector for subscription tests.
EventCollector wraps an asyncua subscription and channels received OPC UA events
into an asyncio.Queue so test coroutines can await them.
Usage:
    async with EventCollector(subscription_client) as collector:
        await collector.subscribe(server_node, [event_type_node])
        events = await collector.collect(count=1, timeout_s=30)
The subscription_client must be a separate asyncua Client instance from the one
used for method calls — asyncua cannot safely handle concurrent calls on a single
client connection.
"""

import asyncio
import logging
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


class EventCollector:
    """
    Collects OPC UA events via asyncua subscription into an asyncio.Queue.
    Implements the asyncua subscription handler interface (sync callbacks).
    The event_notification method is called synchronously from the asyncio
    event loop; put_nowait is used to avoid blocking.
    """

    def __init__(self, client) -> None:
        self._client = client
        self._queue: asyncio.Queue = asyncio.Queue(
            maxsize=1_000
        )  # bounded; prevents unbounded memory growth in long sessions
        self._subscription: Optional[Any] = None

    # ── asyncua handler interface ──────────────────────────────────────────
    def event_notification(self, event) -> None:
        """
        Called by asyncua when a subscribed event arrives.
        Puts the event into the internal queue for consumption by collect().
        """
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("EventCollector queue full, dropping event: %s", event)

    def datachange_notification(self, _node, _val, _data) -> None:
        """Required by asyncua handler interface; not used by EventCollector."""

    def status_change_notification(self, _status) -> None:
        """Required by asyncua handler interface; not used by EventCollector."""

    # ── public API ────────────────────────────────────────────────────────
    async def _delete_subscription_ref(self, subscription: Any) -> None:
        """Best-effort deletion for a known subscription object.

        Logs at ERROR on failure because, with module-scoped subscription_client,
        a failed delete leaves a server-side subscription alive for the rest of the
        module.  asyncua routes incoming notifications by subscription ID, so a
        leaked subscription delivers to this collector's queue (not to the next
        test's collector), but it does consume server resources and may slow the
        simulator.  The queue is drained at the start of each subscribe() call to
        prevent any stale deliveries from accumulating.
        """
        try:
            await asyncio.wait_for(subscription.delete(), timeout=5.0)
        except Exception as exc:
            logger.error(
                "Subscription delete failed — server-side subscription may persist "
                "until module teardown closes the connection: %s", exc
            )

    async def subscribe(
        self,
        server_node,
        event_type_nodes,
        period_ms: int = 100,
        queue_size: int = 200,
        _max_retries: int = 3,
    ) -> None:
        """
        Create a subscription and subscribe to the specified event types.
        Retries up to _max_retries times on timeout — the simulator can be slow
        to respond to subscription requests after a long test run.
        Args:
            server_node:       Source node for the subscription (usually Server node).
            event_type_nodes:  A single event type node or list of event type nodes.
            period_ms:         Subscription publishing interval in milliseconds.
            queue_size:        Maximum queued notifications per monitored item.
        """
        if _max_retries < 1:
            raise ValueError("_max_retries must be >= 1")

        # Re-subscribe should be idempotent: clean up any previous subscription first.
        if self._subscription is not None:
            await self._delete_subscription_ref(self._subscription)
            self._subscription = None

        # Drain stale events that may have arrived after the previous subscription's
        # delete was issued (or if delete failed and delivery continued briefly).
        while not self._queue.empty():
            self._queue.get_nowait()

        last_exc: Optional[Exception] = None
        nodes = list(event_type_nodes) if isinstance(event_type_nodes, (list, tuple)) else [event_type_nodes]

        for attempt in range(1, _max_retries + 1):
            subscription = None
            try:
                subscription = await self._client.create_subscription(period_ms, self)
                await subscription.subscribe_events(server_node, nodes, queuesize=queue_size)
                self._subscription = subscription
                return
            except (TimeoutError, asyncio.TimeoutError) as exc:
                last_exc = exc
                # Prevent leaked server-side subscriptions when subscribe_events times out.
                if subscription is not None:
                    await self._delete_subscription_ref(subscription)
                logger.warning(
                    "Subscription setup timed out (attempt %d/%d): %s — retrying in %ds",
                    attempt,
                    _max_retries,
                    exc,
                    attempt * 2,
                )
                if attempt < _max_retries:
                    await asyncio.sleep(attempt * 2)

        if last_exc is not None:
            raise TimeoutError(f"Failed to create subscription after {_max_retries} attempts") from last_exc
        raise RuntimeError("Subscription setup failed without a captured exception")

    async def collect(self, count: int = 1, timeout_s: float = 30.0) -> List:
        """
        Collect up to `count` events, waiting up to `timeout_s` seconds total.
        Returns a list of received event objects (may be fewer than `count`
        if the timeout elapses before enough events arrive).
        """
        results: List = []
        loop = asyncio.get_event_loop()
        deadline = loop.time() + timeout_s
        while len(results) < count:
            remaining = deadline - loop.time()
            if remaining <= 0:
                break
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=remaining)
                results.append(event)
            except asyncio.TimeoutError:
                break
        return results

    async def unsubscribe(self) -> None:
        """Delete the subscription if one is active."""
        if self._subscription is not None:
            await self._delete_subscription_ref(self._subscription)
            self._subscription = None

    # ── context manager ───────────────────────────────────────────────────
    async def __aenter__(self) -> "EventCollector":
        return self

    async def __aexit__(self, _exc_type, _exc_val, _exc_tb) -> None:
        await self.unsubscribe()
