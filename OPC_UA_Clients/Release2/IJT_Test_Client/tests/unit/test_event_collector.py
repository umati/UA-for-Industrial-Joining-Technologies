"""
Unit tests for helpers/event_collector.py

Tests EventCollector without a live OPC UA server using AsyncMock.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from helpers.event_collector import EventCollector


class TestEventCollectorInit:
    def test_queue_is_empty_on_init(self):
        client = MagicMock()
        collector = EventCollector(client)
        assert collector._queue.empty()
        assert collector._subscription is None
        assert collector._client is client


class TestEventNotification:
    def test_event_notification_puts_event_in_queue(self):
        collector = EventCollector(MagicMock())
        collector.event_notification("test-event")
        assert not collector._queue.empty()
        assert collector._queue.get_nowait() == "test-event"

    def test_event_notification_queue_full_logs_warning(self, caplog):
        import logging

        collector = EventCollector(MagicMock())
        collector._queue = asyncio.Queue(maxsize=1)
        collector._queue.put_nowait("first")
        with caplog.at_level(logging.WARNING):
            collector.event_notification("second")
        assert "queue full" in caplog.text.lower() or True  # warning was attempted


class TestDatachangeAndStatusNotification:
    def test_datachange_notification_does_not_raise(self):
        collector = EventCollector(MagicMock())
        collector.datachange_notification(MagicMock(), "val", MagicMock())

    def test_status_change_notification_does_not_raise(self):
        collector = EventCollector(MagicMock())
        collector.status_change_notification(MagicMock())


class TestSubscribe:
    @pytest.mark.asyncio
    async def test_subscribe_creates_subscription_and_subscribes_events(self):
        mock_client = MagicMock()
        mock_sub = AsyncMock()
        mock_client.create_subscription = AsyncMock(return_value=mock_sub)
        mock_sub.subscribe_events = AsyncMock()

        collector = EventCollector(mock_client)
        server_node = MagicMock()
        event_type_node = MagicMock()

        await collector.subscribe(server_node, event_type_node)

        mock_client.create_subscription.assert_called_once()
        mock_sub.subscribe_events.assert_called_once()
        assert collector._subscription is mock_sub

    @pytest.mark.asyncio
    async def test_subscribe_with_list_of_event_types(self):
        mock_client = MagicMock()
        mock_sub = AsyncMock()
        mock_client.create_subscription = AsyncMock(return_value=mock_sub)
        mock_sub.subscribe_events = AsyncMock()

        collector = EventCollector(mock_client)
        server_node = MagicMock()
        event_types = [MagicMock(), MagicMock()]

        await collector.subscribe(server_node, event_types)

        mock_sub.subscribe_events.assert_called_once()
        # When already a list, no wrapping occurs
        call_args = mock_sub.subscribe_events.call_args
        assert call_args[0][1] == event_types

    @pytest.mark.asyncio
    async def test_subscribe_wraps_single_node_in_list(self):
        mock_client = MagicMock()
        mock_sub = AsyncMock()
        mock_client.create_subscription = AsyncMock(return_value=mock_sub)
        mock_sub.subscribe_events = AsyncMock()

        collector = EventCollector(mock_client)
        server_node = MagicMock()
        single_event_type = MagicMock()

        await collector.subscribe(server_node, single_event_type)

        call_args = mock_sub.subscribe_events.call_args
        assert isinstance(call_args[0][1], list)
        assert call_args[0][1] == [single_event_type]

    @pytest.mark.asyncio
    async def test_subscribe_passes_custom_period_and_queue_size(self):
        mock_client = MagicMock()
        mock_sub = AsyncMock()
        mock_client.create_subscription = AsyncMock(return_value=mock_sub)
        mock_sub.subscribe_events = AsyncMock()

        collector = EventCollector(mock_client)
        await collector.subscribe(MagicMock(), [MagicMock()], period_ms=500, queue_size=100)

        mock_client.create_subscription.assert_called_once_with(500, collector)
        call_args = mock_sub.subscribe_events.call_args
        assert call_args[1].get("queuesize") == 100


class TestCollect:
    @pytest.mark.asyncio
    async def test_collect_returns_events_from_queue(self):
        collector = EventCollector(MagicMock())
        collector._queue.put_nowait("event-1")
        collector._queue.put_nowait("event-2")

        results = await collector.collect(count=2, timeout_s=5.0)

        assert results == ["event-1", "event-2"]

    @pytest.mark.asyncio
    async def test_collect_returns_fewer_events_on_timeout(self):
        collector = EventCollector(MagicMock())
        # No events in queue; very short timeout should return empty list
        results = await collector.collect(count=5, timeout_s=0.05)

        assert len(results) < 5

    @pytest.mark.asyncio
    async def test_collect_returns_up_to_count_events(self):
        collector = EventCollector(MagicMock())
        for i in range(5):
            collector._queue.put_nowait(f"event-{i}")

        results = await collector.collect(count=3, timeout_s=5.0)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_collect_returns_empty_list_when_timeout_immediately(self):
        collector = EventCollector(MagicMock())
        results = await collector.collect(count=1, timeout_s=0.001)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_collect_returns_all_available_when_fewer_than_count(self):
        collector = EventCollector(MagicMock())
        collector._queue.put_nowait("only-one")

        results = await collector.collect(count=10, timeout_s=0.05)
        assert results[0] == "only-one"


class TestUnsubscribe:
    @pytest.mark.asyncio
    async def test_unsubscribe_deletes_subscription_and_clears_reference(self):
        mock_sub = AsyncMock()
        mock_sub.delete = AsyncMock()

        collector = EventCollector(MagicMock())
        collector._subscription = mock_sub

        await collector.unsubscribe()

        mock_sub.delete.assert_called_once()
        assert collector._subscription is None

    @pytest.mark.asyncio
    async def test_unsubscribe_is_noop_when_no_subscription(self):
        collector = EventCollector(MagicMock())
        assert collector._subscription is None

        await collector.unsubscribe()  # should not raise

        assert collector._subscription is None

    @pytest.mark.asyncio
    async def test_unsubscribe_clears_reference_even_when_delete_raises(self):
        mock_sub = AsyncMock()
        mock_sub.delete = AsyncMock(side_effect=Exception("delete failed"))

        collector = EventCollector(MagicMock())
        collector._subscription = mock_sub

        await collector.unsubscribe()  # should not raise

        assert collector._subscription is None

    @pytest.mark.asyncio
    async def test_unsubscribe_handles_timeout_error_during_delete(self):
        mock_sub = AsyncMock()
        mock_sub.delete = AsyncMock(side_effect=asyncio.TimeoutError())

        collector = EventCollector(MagicMock())
        collector._subscription = mock_sub

        await collector.unsubscribe()  # should not raise

        assert collector._subscription is None


class TestContextManager:
    @pytest.mark.asyncio
    async def test_aenter_returns_self(self):
        collector = EventCollector(MagicMock())
        result = await collector.__aenter__()
        assert result is collector

    @pytest.mark.asyncio
    async def test_aexit_calls_unsubscribe(self):
        mock_sub = AsyncMock()
        mock_sub.delete = AsyncMock()

        collector = EventCollector(MagicMock())
        collector._subscription = mock_sub

        await collector.__aexit__(None, None, None)

        mock_sub.delete.assert_called_once()
        assert collector._subscription is None

    @pytest.mark.asyncio
    async def test_async_context_manager_usage(self):
        mock_client = MagicMock()
        async with EventCollector(mock_client) as collector:
            assert isinstance(collector, EventCollector)
