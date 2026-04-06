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
from typing import List

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
        self._subscription = None

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

    def datachange_notification(self, node, val, data) -> None:
        """Required by asyncua handler interface; not used by EventCollector."""

    def status_change_notification(self, status) -> None:
        """Required by asyncua handler interface; not used by EventCollector."""

    # ── public API ────────────────────────────────────────────────────────
    async def subscribe(
        self,
        server_node,
        event_type_nodes,
        period_ms: int = 100,
        queue_size: int = 200,
    ) -> None:
        """
        Create a subscription and subscribe to the specified event types.
        Args:
            server_node:       Source node for the subscription (usually Server node).
            event_type_nodes:  A single event type node or list of event type nodes.
            period_ms:         Subscription publishing interval in milliseconds.
            queue_size:        Maximum queued notifications per monitored item.
        """
        subscription = await self._client.create_subscription(period_ms, self)
        self._subscription = subscription
        if not isinstance(event_type_nodes, (list, tuple)):
            event_type_nodes = [event_type_nodes]
        await subscription.subscribe_events(server_node, event_type_nodes, queuesize=queue_size)

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
            try:
                await asyncio.wait_for(self._subscription.delete(), timeout=5.0)
            except Exception as exc:
                logger.warning("Error deleting subscription: %s", exc)
            finally:
                self._subscription = None

    # ── context manager ───────────────────────────────────────────────────
    async def __aenter__(self) -> "EventCollector":
        return self

    async def __aexit__(self, _exc_type, _exc_val, _exc_tb) -> None:
        await self.unsubscribe()
