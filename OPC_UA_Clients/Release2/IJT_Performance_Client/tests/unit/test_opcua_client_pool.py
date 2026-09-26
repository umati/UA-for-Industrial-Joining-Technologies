"""
Unit tests for process-sharded client pool, worker handlers,
message parsing, and coverage verification.
"""

import asyncio
import multiprocessing as mp
import queue
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ijt_performance_client.opcua_client_pool import (
    OpcUaClientPool,
    _DurableWorkerSubHandler,
    _find_child,
    _locate_simulate_method,
    _worker_process_entry,
)
from ijt_performance_client.result_transfer_latency import LatencySample


@pytest.mark.asyncio
async def test_find_child():
    mock_parent = MagicMock()
    mock_child = MagicMock()
    mock_parent.get_child = AsyncMock(return_value=mock_child)

    # Fast path: found by get_child
    found = await _find_child(mock_parent, ns_idx=2, browse_name="TestName")
    assert found is mock_child

    # Fallback path: get_child raises, iterate get_children
    mock_parent.get_child = AsyncMock(side_effect=RuntimeError("Not found"))
    mock_child1 = MagicMock()
    mock_bn1 = MagicMock()
    mock_bn1.Name = "OtherName"
    mock_bn1.NamespaceIndex = 2
    mock_child1.read_browse_name = AsyncMock(return_value=mock_bn1)

    mock_child2 = MagicMock()
    mock_bn2 = MagicMock()
    mock_bn2.Name = "TestName"
    mock_bn2.NamespaceIndex = 2
    mock_child2.read_browse_name = AsyncMock(return_value=mock_bn2)

    mock_parent.get_children = AsyncMock(return_value=[mock_child1, mock_child2])
    found_fallback = await _find_child(mock_parent, ns_idx=2, browse_name="TestName")
    assert found_fallback is mock_child2


@pytest.mark.asyncio
async def test_locate_simulate_method():
    mock_client = MagicMock()
    mock_objects = MagicMock()
    mock_client.nodes.objects = mock_objects

    with patch("ijt_performance_client.opcua_client_pool._find_child") as mock_find:
        # 1. Finds TighteningSystem -> Simulations -> SimulateResults -> SimulateSingleResult
        mock_ts = MagicMock()
        mock_sim = MagicMock()
        mock_res = MagicMock()
        mock_meth = MagicMock()
        mock_find.side_effect = [mock_ts, mock_sim, mock_res, mock_meth]

        parent, method = await _locate_simulate_method(mock_client, ns_app=2)
        assert parent is mock_res
        assert method is mock_meth


def test_durable_worker_sub_handler():
    buf = []
    handler = _DurableWorkerSubHandler(
        endpoint="opc.tcp://localhost:40451",
        local_buffer=buf,
        clock_skew_ms=5.0,
    )

    # Event notification
    mock_event = MagicMock()
    mock_event.Time = datetime.now(UTC)
    mock_event.Result = None

    handler.event_notification(mock_event)
    assert len(buf) == 1
    assert buf[0]["endpoint"] == "opc.tcp://localhost:40451"
    assert buf[0]["sample_id"] == 1
    assert buf[0]["clock_skew_ms"] == 5.0

    # Safe no-ops
    handler.datachange_notification(None, None, None)
    handler.status_change_notification(None)


def test_fleet_client_pool_init_and_sharding():
    eps = [f"opc.tcp://10.0.0.{i}:4840" for i in range(1, 11)]
    pool = OpcUaClientPool(endpoints=eps, max_workers=3)
    assert len(pool.endpoints) == 10
    assert pool.max_workers == 3
    assert pool.require_full_coverage is True


def test_fleet_client_pool_collect_samples_and_coverage():
    pool = OpcUaClientPool(endpoints=["opc.tcp://server1:4840", "opc.tcp://server2:4840"])

    # Mock the out_queue with BATCH, FLEET_STATUS, and ERROR messages
    mock_q = MagicMock()
    pool._out_queue = mock_q

    now_iso = datetime.now(UTC).isoformat()
    mock_q.get.side_effect = [
        {
            "type": "FLEET_STATUS",
            "connected": ["opc.tcp://server1:4840", "opc.tcp://server2:4840"],
            "failed": {},
        },
        {
            "type": "BATCH",
            "samples": [
                {
                    "sample_id": 1,
                    "endpoint": "opc.tcp://server1:4840",
                    "start_time": now_iso,
                    "end_time": now_iso,
                    "creation_time": now_iso,
                    "event_time": now_iso,
                    "client_received_time": now_iso,
                    "clock_skew_ms": 0.0,
                    "joining_duration_ms": 500.0,
                    "server_processing_time_ms": 20.0,
                    "network_transport_time_ms": 10.0,
                    "total_result_transfer_time_ms": 35.0,
                },
                {
                    "sample_id": 2,
                    "endpoint": "opc.tcp://server2:4840",
                    "start_time": now_iso,
                    "end_time": now_iso,
                    "creation_time": now_iso,
                    "event_time": now_iso,
                    "client_received_time": now_iso,
                    "clock_skew_ms": 0.0,
                    "joining_duration_ms": 600.0,
                    "server_processing_time_ms": 25.0,
                    "network_transport_time_ms": 12.0,
                    "total_result_transfer_time_ms": 42.0,
                },
            ],
        },
        queue.Empty(),
    ]

    samples = pool.collect_samples(duration_seconds=0.1, target_sample_count=2)
    assert len(samples) == 2
    assert "opc.tcp://server1:4840" in pool.connected_endpoints
    assert "opc.tcp://server2:4840" in pool.connected_endpoints

    # Coverage verification
    valid, msg = pool.verify_coverage(samples)
    assert valid is True
    assert "2/2 endpoints produced samples" in msg


def test_fleet_client_pool_coverage_failures():
    pool = OpcUaClientPool(
        endpoints=["opc.tcp://s1:4840", "opc.tcp://s2:4840"],
        require_full_coverage=True,
    )

    # 1. Worker error detected
    pool.worker_errors.append("Worker 0 crashed")
    valid, msg = pool.verify_coverage([])
    assert valid is False
    assert "Worker process failures detected" in msg

    # 2. Connection failure
    pool.worker_errors.clear()
    pool.failed_endpoints["opc.tcp://s2:4840"] = "ECONNREFUSED"
    valid, msg = pool.verify_coverage([])
    assert valid is False
    assert "Connection failures on 1 endpoints" in msg

    # 3. Missing samples when require_full_coverage is True
    pool.failed_endpoints.clear()
    sample = LatencySample(sample_id=1, endpoint="opc.tcp://s1:4840")
    valid, msg = pool.verify_coverage([sample])
    assert valid is False
    assert "Incomplete coverage: 1 endpoints produced zero samples" in msg

    # 4. Incomplete samples acceptable when require_full_coverage is False
    pool.require_full_coverage = False
    valid, msg = pool.verify_coverage([sample])
    assert valid is True


def test_fleet_client_pool_stop():
    pool = OpcUaClientPool(endpoints=["opc.tcp://localhost:4840"])
    mock_proc = MagicMock()
    mock_proc.is_alive.return_value = False
    mock_proc.exitcode = 0
    pool._processes = [mock_proc]

    mock_q = MagicMock()
    mock_q.get.side_effect = queue.Empty()
    mock_q.get_nowait.side_effect = queue.Empty()
    pool._out_queue = mock_q

    pool.stop(drain_timeout_s=0.01)
    mock_proc.join.assert_called_once()
    assert len(pool._processes) == 0


@pytest.mark.asyncio
async def test_worker_event_loop_mocked():
    from ijt_performance_client.opcua_client_pool import _worker_event_loop

    out_q = MagicMock()
    stop_event = MagicMock()
    # Stop immediately
    stop_event.is_set.side_effect = [False, True, True, True, True]

    with (
        patch("ijt_performance_client.opcua_client_pool.Client") as mock_client_cls,
        patch("ijt_performance_client.opcua_client_pool.load_ijt_type_definitions"),
        patch("ijt_performance_client.opcua_client_pool.calibrate_clock_skew", return_value=0.0),
        patch("ijt_performance_client.opcua_client_pool.resolve_namespace_index", return_value=3),
    ):
        mock_cli = MagicMock()
        mock_cli.connect = AsyncMock()
        mock_sub = MagicMock()
        mock_sub.subscribe_events = AsyncMock()
        mock_sub.delete = AsyncMock()
        mock_cli.create_subscription = AsyncMock(return_value=mock_sub)
        mock_client_cls.return_value = mock_cli

        await _worker_event_loop(
            worker_id=0,
            endpoints=["opc.tcp://mock-server:40451"],
            out_queue=out_q,
            stop_event=stop_event,
            connect_concurrency=5,
            sub_period_ms=50,
            mode="passive",
            burst_trigger_count=0,
            max_retries=1,
        )

        mock_cli.connect.assert_awaited_once()
        mock_sub.subscribe_events.assert_awaited_once()
        mock_sub.delete.assert_awaited_once()
        out_q.put.assert_called()


@pytest.mark.asyncio
async def test_worker_event_loop_active_burst():
    from ijt_performance_client.opcua_client_pool import _worker_event_loop

    out_q = MagicMock()
    stop_event = MagicMock()
    # Stop after burst round
    stop_event.is_set.side_effect = [False, False, False, True, True, True]

    with (
        patch("ijt_performance_client.opcua_client_pool.Client") as mock_client_cls,
        patch("ijt_performance_client.opcua_client_pool.load_ijt_type_definitions"),
        patch("ijt_performance_client.opcua_client_pool.calibrate_clock_skew", return_value=0.0),
        patch("ijt_performance_client.opcua_client_pool.resolve_namespace_index", return_value=3),
        patch("ijt_performance_client.opcua_client_pool._locate_simulate_method") as mock_locate,
    ):
        mock_cli = MagicMock()
        mock_cli.connect = AsyncMock()
        mock_sub = MagicMock()
        mock_sub.subscribe_events = AsyncMock()
        mock_sub.delete = AsyncMock()
        mock_cli.create_subscription = AsyncMock(return_value=mock_sub)
        mock_client_cls.return_value = mock_cli

        mock_sim_res = MagicMock()
        mock_sim_res.call_method = AsyncMock()
        mock_meth_node = MagicMock()
        mock_meth_node.nodeid = 1234
        mock_locate.return_value = (mock_sim_res, mock_meth_node)

        await _worker_event_loop(
            worker_id=1,
            endpoints=["opc.tcp://mock-server:40451"],
            out_queue=out_q,
            stop_event=stop_event,
            connect_concurrency=5,
            sub_period_ms=50,
            mode="active_burst",
            burst_trigger_count=1,
            max_retries=1,
        )

        mock_sim_res.call_method.assert_awaited_once()


@pytest.mark.asyncio
async def test_worker_event_loop_connection_exhaustion():
    from ijt_performance_client.opcua_client_pool import _worker_event_loop

    out_q = MagicMock()
    stop_event = MagicMock()
    stop_event.is_set.return_value = False

    with patch("ijt_performance_client.opcua_client_pool.Client") as mock_client_cls:
        mock_cli = MagicMock()
        mock_cli.connect = AsyncMock(side_effect=ConnectionRefusedError("Offline"))
        mock_client_cls.return_value = mock_cli

        # Let it exhaust 1 retry then set stop_event
        stop_event.is_set.side_effect = [False, False, True, True, True]

        await _worker_event_loop(
            worker_id=2,
            endpoints=["opc.tcp://dead-server:40451"],
            out_queue=out_q,
            stop_event=stop_event,
            connect_concurrency=5,
            sub_period_ms=50,
            mode="passive",
            burst_trigger_count=0,
            max_retries=1,
        )

        # FLEET_STATUS sent reporting failure
        out_q.put.assert_called()


def test_worker_process_entry_calls_event_loop():
    from ijt_performance_client.opcua_client_pool import _worker_process_entry

    out_q = MagicMock()
    stop_event = MagicMock()

    with patch("ijt_performance_client.opcua_client_pool._worker_event_loop", new_callable=AsyncMock) as mock_loop:
        _worker_process_entry(
            worker_id=3,
            endpoints=["opc.tcp://test:4840"],
            out_queue=out_q,
            stop_event=stop_event,
            connect_concurrency=10,
            sub_period_ms=100,
            mode="passive",
            burst_trigger_count=0,
        )
        mock_loop.assert_awaited_once()


def test_worker_process_entry_handles_exception():
    from ijt_performance_client.opcua_client_pool import _worker_process_entry

    out_q = MagicMock()
    stop_event = MagicMock()

    proc_err = RuntimeError("Process failure")
    # Patch _worker_event_loop with a sync MagicMock to avoid creating an unawaited coroutine
    with (
        patch("ijt_performance_client.opcua_client_pool._worker_event_loop", new_callable=MagicMock, return_value=None),
        patch("ijt_performance_client.opcua_client_pool.asyncio.run", side_effect=proc_err),
    ):
        _worker_process_entry(
            worker_id=4,
            endpoints=["opc.tcp://test:4840"],
            out_queue=out_q,
            stop_event=stop_event,
            connect_concurrency=10,
            sub_period_ms=100,
            mode="passive",
            burst_trigger_count=0,
        )
        out_q.put.assert_called_with(
            {
                "type": "ERROR",
                "worker_id": 4,
                "error": "Process failure",
            }
        )


def test_stop_preserves_final_batch_samples():
    pool = OpcUaClientPool(endpoints=["opc.tcp://localhost:4840"])
    mock_proc = MagicMock()
    mock_proc.is_alive.return_value = False
    mock_proc.exitcode = 0
    pool._processes = [mock_proc]
    pool._num_workers_started = 1

    now_iso = datetime.now(UTC).isoformat()
    mock_q = MagicMock()
    mock_q.get.side_effect = [
        {
            "type": "BATCH",
            "samples": [
                {
                    "sample_id": 99,
                    "endpoint": "opc.tcp://localhost:4840",
                    "start_time": now_iso,
                    "end_time": now_iso,
                    "creation_time": now_iso,
                    "event_time": now_iso,
                    "client_received_time": now_iso,
                    "clock_skew_ms": 0.0,
                    "joining_duration_ms": 500.0,
                    "server_processing_time_ms": 20.0,
                    "network_transport_time_ms": 10.0,
                    "total_result_transfer_time_ms": 35.0,
                }
            ],
        },
        {"type": "DONE", "worker_id": 0, "connected_count": 1},
        queue.Empty(),
    ]
    mock_q.get_nowait.side_effect = queue.Empty()
    pool._out_queue = mock_q

    samples = pool.stop(drain_timeout_s=0.05)
    assert len(samples) == 1
    assert samples[0].sample_id == 99
    assert 0 in pool.completed_worker_ids
    valid, msg = pool.verify_coverage(samples)
    assert valid is True


def test_verify_coverage_detects_missing_done():
    pool = OpcUaClientPool(endpoints=["opc.tcp://s1:4840"])
    pool._num_workers_started = 2
    pool.completed_worker_ids = {0}  # Worker 1 is missing DONE

    valid, msg = pool.verify_coverage([])
    assert valid is False
    assert "Worker completion failure: workers [1] did not confirm clean shutdown" in msg


def test_verify_coverage_detects_nonzero_exitcode():
    pool = OpcUaClientPool(endpoints=["opc.tcp://s1:4840"])
    mock_proc = MagicMock()
    mock_proc.is_alive.return_value = False
    mock_proc.exitcode = 137  # E.g. OOM killed
    pool._processes = [mock_proc]
    pool._num_workers_started = 1
    pool.completed_worker_ids = {0}

    mock_q = MagicMock()
    mock_q.get.side_effect = queue.Empty()
    mock_q.get_nowait.side_effect = queue.Empty()
    pool._out_queue = mock_q

    pool.stop(drain_timeout_s=0.01)
    assert len(pool.worker_errors) == 1
    assert "crashed with exitcode 137" in pool.worker_errors[0]

    valid, msg = pool.verify_coverage([])
    assert valid is False
    assert "Worker process failures detected" in msg


def test_verify_coverage_detects_forced_termination():
    pool = OpcUaClientPool(endpoints=["opc.tcp://s1:4840"])
    mock_proc = MagicMock()
    mock_proc.is_alive.return_value = True

    def fake_terminate():
        mock_proc.is_alive.return_value = False

    mock_proc.terminate.side_effect = fake_terminate
    mock_proc.exitcode = None
    pool._processes = [mock_proc]
    pool._num_workers_started = 1
    pool.completed_worker_ids = {0}

    mock_q = MagicMock()
    mock_q.get.side_effect = queue.Empty()
    mock_q.get_nowait.side_effect = queue.Empty()
    pool._out_queue = mock_q

    pool.stop(drain_timeout_s=0.01)
    mock_proc.terminate.assert_called_once()
    assert len(pool.worker_errors) == 1
    assert "did not exit within timeout; forcefully terminated" in pool.worker_errors[0]

    valid, msg = pool.verify_coverage([])
    assert valid is False
    assert "Worker process failures detected" in msg


@pytest.mark.asyncio
async def test_partial_subscription_cleanup_on_connect_failure():
    from ijt_performance_client.opcua_client_pool import _worker_event_loop

    out_q = MagicMock()
    stop_event = MagicMock()
    stop_event.is_set.return_value = False

    with (
        patch("ijt_performance_client.opcua_client_pool.Client") as mock_client_cls,
        patch("ijt_performance_client.opcua_client_pool.load_ijt_type_definitions"),
        patch("ijt_performance_client.opcua_client_pool.calibrate_clock_skew", return_value=0.0),
        patch("ijt_performance_client.opcua_client_pool.resolve_namespace_index", return_value=3),
    ):
        mock_cli = MagicMock()
        mock_cli.connect = AsyncMock()
        mock_sub = MagicMock()
        # subscribe_events fails after create_subscription succeeded
        mock_sub.subscribe_events = AsyncMock(side_effect=RuntimeError("Sub events failed"))
        mock_sub.delete = AsyncMock()
        mock_cli.create_subscription = AsyncMock(return_value=mock_sub)
        mock_client_cls.return_value = mock_cli

        stop_event.is_set.side_effect = [False, False, True, True, True]

        await _worker_event_loop(
            worker_id=0,
            endpoints=["opc.tcp://flaky-server:40451"],
            out_queue=out_q,
            stop_event=stop_event,
            connect_concurrency=1,
            sub_period_ms=50,
            mode="passive",
            burst_trigger_count=0,
            max_retries=1,
        )

        mock_sub.delete.assert_awaited()


def test_fleet_client_pool_start():
    pool = OpcUaClientPool(endpoints=["opc.tcp://s1:4840", "opc.tcp://s2:4840"], max_workers=2)

    with (
        patch.object(pool._ctx, "Process") as mock_proc_cls,
        patch.object(pool._ctx, "Queue"),
        patch.object(pool._ctx, "Event"),
    ):
        mock_proc = MagicMock()
        mock_proc_cls.return_value = mock_proc

        pool.start(burst_trigger_count=0)

        assert pool._num_workers_started == 2
        assert len(pool._processes) == 2
        assert mock_proc.start.call_count == 2


def test_real_spawn_worker_emits_status_and_done_without_network():
    """Exercise the real spawn and queue protocol without opening OPC UA sockets."""
    ctx = mp.get_context("spawn")
    out_queue = ctx.Queue()
    stop_event = ctx.Event()
    stop_event.set()
    process = ctx.Process(
        target=_worker_process_entry,
        args=(0, [], out_queue, stop_event, 1, 100, "passive", 0, True),
    )

    try:
        process.start()
        process.join(timeout=10)
        assert not process.is_alive()
        assert process.exitcode == 0

        messages = [out_queue.get(timeout=2), out_queue.get(timeout=2)]
        assert [message["type"] for message in messages] == ["FLEET_STATUS", "DONE"]
        assert messages[1]["worker_id"] == 0
    finally:
        if process.is_alive():
            process.terminate()
            process.join(timeout=2)
        out_queue.close()
        out_queue.join_thread()


@pytest.mark.asyncio
async def test_find_child_edge_cases():
    mock_parent = MagicMock()
    mock_parent.get_child = AsyncMock(side_effect=RuntimeError("Direct lookup failed"))

    # 1. get_children() itself fails
    mock_parent.get_children = AsyncMock(side_effect=RuntimeError("Children lookup failed"))
    assert await _find_child(mock_parent, ns_idx=2, browse_name="Target") is None

    # 2. Child read_browse_name fails or namespace does not match (fallback child)
    mock_parent.get_children = AsyncMock()
    bad_child = MagicMock()
    bad_child.read_browse_name = AsyncMock(side_effect=RuntimeError("Corrupt child"))

    fallback_child = MagicMock()
    bn_fallback = MagicMock()
    bn_fallback.Name = "Target"
    bn_fallback.NamespaceIndex = 99  # different namespace
    fallback_child.read_browse_name = AsyncMock(return_value=bn_fallback)

    mock_parent.get_children.return_value = [bad_child, fallback_child]
    found = await _find_child(mock_parent, ns_idx=2, browse_name="Target")
    assert found is fallback_child


@pytest.mark.asyncio
async def test_locate_simulate_method_none_branches():
    mock_client = MagicMock()
    mock_client.nodes.objects = MagicMock()

    with patch("ijt_performance_client.opcua_client_pool._find_child") as mock_find:
        # 1. TighteningSystem None, JoiningSystem None -> (None, None)
        mock_find.side_effect = [None, None]
        p, m = await _locate_simulate_method(mock_client, ns_app=2)
        assert p is None and m is None

        # 2. Simulations None -> (None, None)
        mock_ts = MagicMock()
        mock_find.side_effect = [mock_ts, None]
        p, m = await _locate_simulate_method(mock_client, ns_app=2)
        assert p is None and m is None

        # 3. SimulateResults None -> (None, None)
        mock_sim = MagicMock()
        mock_find.side_effect = [mock_ts, mock_sim, None]
        p, m = await _locate_simulate_method(mock_client, ns_app=2)
        assert p is None and m is None


def test_fleet_client_pool_edge_cases():
    # Empty endpoints in start()
    pool_empty = OpcUaClientPool(endpoints=[])
    with pytest.raises(ValueError, match="No endpoints provided"):
        pool_empty.start()

    # ERROR message parsing in _process_queue_msg
    pool = OpcUaClientPool(endpoints=["opc.tcp://localhost:40451"])
    pool._process_queue_msg({"type": "ERROR", "worker_id": 5, "error": "Fatal socket drop"})
    assert any("Worker 5 error: Fatal socket drop" in err for err in pool.worker_errors)

    # collect_samples duration timeout break
    mock_q = MagicMock()
    mock_q.get.side_effect = queue.Empty()
    pool._out_queue = mock_q
    samples = pool.collect_samples(duration_seconds=0.01)
    assert samples == []

    # Phase 3 final drain in stop()
    mock_q.get_nowait.side_effect = [
        {
            "type": "BATCH",
            "worker_id": 0,
            "samples": [
                {
                    "sample_id": 1,
                    "endpoint": "opc.tcp://localhost:40451",
                    "network_transport_time_ms": 12.0,
                    "server_processing_time_ms": 5.0,
                    "total_result_transfer_time_ms": 17.0,
                    "joining_duration_ms": 0.0,
                    "start_time": None,
                    "end_time": None,
                    "creation_time": None,
                    "event_time": None,
                    "client_received_time": None,
                    "clock_skew_ms": 0.0,
                }
            ],
        },
        queue.Empty(),
    ]
    res_samples = pool.stop(drain_timeout_s=0.01)
    assert len(res_samples) == 1


@pytest.mark.asyncio
async def test_worker_event_loop_retries_and_burst():
    from ijt_performance_client.opcua_client_pool import _worker_event_loop

    out_q = MagicMock()
    stop_event = MagicMock()
    # stop_event: run connect, then run burst, then stop
    stop_event.is_set.side_effect = [False, False, False, False, True, True, True, True, True]

    with (
        patch("ijt_performance_client.opcua_client_pool.Client") as mock_client_cls,
        patch("ijt_performance_client.opcua_client_pool.load_ijt_type_definitions"),
        patch("ijt_performance_client.opcua_client_pool.calibrate_clock_skew", return_value=0.0),
        patch("ijt_performance_client.opcua_client_pool.resolve_namespace_index", return_value=2),
        patch("ijt_performance_client.opcua_client_pool._locate_simulate_method") as mock_loc_sim,
    ):
        mock_cli = MagicMock()
        mock_cli.connect = AsyncMock()
        mock_sub = MagicMock()
        mock_sub.delete = AsyncMock(side_effect=RuntimeError("Sub del fail"))
        mock_sub.subscribe_events = AsyncMock()
        mock_cli.create_subscription = AsyncMock(return_value=mock_sub)

        # Method client
        mock_sim_res = MagicMock()
        mock_sim_res.call_method = AsyncMock(side_effect=RuntimeError("Call method fail"))
        mock_meth_node = MagicMock()
        mock_meth_node.nodeid = 1234
        mock_loc_sim.return_value = (mock_sim_res, mock_meth_node)

        mock_client_cls.return_value = mock_cli

        await _worker_event_loop(
            worker_id=0,
            endpoints=["opc.tcp://test:40451"],
            out_queue=out_q,
            stop_event=stop_event,
            connect_concurrency=1,
            sub_period_ms=50,
            mode="active_burst",
            burst_trigger_count=1,
            max_retries=1,
        )

        out_q.put.assert_called()


@pytest.mark.asyncio
async def test_worker_event_loop_ns_missing_and_retry_backoff():
    from ijt_performance_client.opcua_client_pool import _worker_event_loop

    out_q = MagicMock()
    stop_event = MagicMock()
    stop_event.is_set.return_value = False

    with (
        patch("ijt_performance_client.opcua_client_pool.Client") as mock_client_cls,
        patch("ijt_performance_client.opcua_client_pool.load_ijt_type_definitions"),
        patch("ijt_performance_client.opcua_client_pool.calibrate_clock_skew", return_value=0.0),
        patch("ijt_performance_client.opcua_client_pool.resolve_namespace_index", return_value=None),  # Missing NS
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        mock_cli = MagicMock()
        mock_cli.connect = AsyncMock()
        mock_client_cls.return_value = mock_cli

        # stop after 2 retry attempts
        stop_event.is_set.side_effect = [False, False, False, True, True, True]

        await _worker_event_loop(
            worker_id=0,
            endpoints=["opc.tcp://no-ns:40451"],
            out_queue=out_q,
            stop_event=stop_event,
            connect_concurrency=1,
            sub_period_ms=50,
            mode="passive",
            burst_trigger_count=0,
            max_retries=2,
        )

        # Exponential backoff sleep was invoked
        mock_sleep.assert_awaited()


@pytest.mark.asyncio
async def test_worker_event_loop_stop_before_connect_and_sub_delete_error():
    from ijt_performance_client.opcua_client_pool import _worker_event_loop

    out_q = MagicMock()
    # 1. Stop event already set before connect -> line 184
    stop_event_early = MagicMock()
    stop_event_early.is_set.return_value = True

    await _worker_event_loop(
        worker_id=0,
        endpoints=["opc.tcp://test:40451"],
        out_queue=out_q,
        stop_event=stop_event_early,
        connect_concurrency=1,
        sub_period_ms=50,
        mode="passive",
        burst_trigger_count=0,
        max_retries=1,
    )

    # 2. Sub delete error on connect failure -> lines 214-215
    stop_event_retry = MagicMock()
    stop_event_retry.is_set.side_effect = [False, False, True, True, True]

    with (
        patch("ijt_performance_client.opcua_client_pool.Client") as mock_client_cls,
        patch("ijt_performance_client.opcua_client_pool.load_ijt_type_definitions"),
        patch("ijt_performance_client.opcua_client_pool.calibrate_clock_skew", return_value=0.0),
        patch("ijt_performance_client.opcua_client_pool.resolve_namespace_index", return_value=2),
    ):
        mock_cli = MagicMock()
        mock_cli.connect = AsyncMock()
        mock_sub = MagicMock()
        # sub.delete raises during failure cleanup
        mock_sub.delete = AsyncMock(side_effect=RuntimeError("Sub del err"))
        mock_sub.subscribe_events = AsyncMock(side_effect=RuntimeError("Subscribe failed"))
        mock_cli.create_subscription = AsyncMock(return_value=mock_sub)
        mock_client_cls.return_value = mock_cli

        await _worker_event_loop(
            worker_id=0,
            endpoints=["opc.tcp://del-err:40451"],
            out_queue=out_q,
            stop_event=stop_event_retry,
            connect_concurrency=1,
            sub_period_ms=50,
            mode="passive",
            burst_trigger_count=0,
            max_retries=1,
        )
        mock_sub.delete.assert_awaited()


def test_worker_process_entry_crash_reporting():
    from ijt_performance_client.opcua_client_pool import _worker_process_entry

    # Broken out_queue whose put raises
    bad_q = MagicMock()
    bad_q.put.side_effect = RuntimeError("Broken pipe")

    with patch(
        "ijt_performance_client.opcua_client_pool._worker_event_loop",
        side_effect=RuntimeError("Loop startup fatal crash"),
    ):
        # Should catch error, attempt put, swallow broken pipe without unhandled crash
        _worker_process_entry(
            worker_id=1,
            endpoints=["opc.tcp://crash:40451"],
            out_queue=bad_q,
            stop_event=MagicMock(),
            connect_concurrency=1,
            sub_period_ms=100,
            mode="passive",
            burst_trigger_count=0,
        )
        bad_q.put.assert_called()


def test_pool_stop_sets_stop_event():
    pool = OpcUaClientPool(endpoints=["opc.tcp://localhost:40451"])
    mock_stop_event = MagicMock()
    pool._stop_event = mock_stop_event
    pool._out_queue = MagicMock()
    pool._out_queue.get.side_effect = queue.Empty()
    pool._out_queue.get_nowait.side_effect = queue.Empty()

    pool.stop(drain_timeout_s=0.01)
    mock_stop_event.set.assert_called_once()


@pytest.mark.asyncio
async def test_worker_event_loop_method_connect_fail_and_buffer_flush():
    from ijt_performance_client.opcua_client_pool import _worker_event_loop

    out_q = MagicMock()
    stop_event = MagicMock()
    # Let connect succeed, then set stop_event
    stop_event.is_set.side_effect = [False, False, False, True, True, True, True, True]

    with (
        patch("ijt_performance_client.opcua_client_pool.Client") as mock_client_cls,
        patch("ijt_performance_client.opcua_client_pool.load_ijt_type_definitions"),
        patch("ijt_performance_client.opcua_client_pool.calibrate_clock_skew", return_value=0.0),
        patch("ijt_performance_client.opcua_client_pool.resolve_namespace_index", return_value=2),
    ):
        mock_cli_sub = MagicMock()
        mock_cli_sub.connect = AsyncMock()
        mock_sub = MagicMock()
        mock_sub.delete = AsyncMock()
        mock_sub.subscribe_events = AsyncMock()

        # Capture the handler to send a sample into local_buffer
        captured_handler = None

        def fake_create_sub(period, handler):
            nonlocal captured_handler
            captured_handler = handler
            return mock_sub

        mock_cli_sub.create_subscription = AsyncMock(side_effect=fake_create_sub)

        # Method client connect raises to test lines 269-270
        mock_cli_method = MagicMock()
        mock_cli_method.connect = AsyncMock(side_effect=RuntimeError("Method client connect fail"))

        mock_client_cls.side_effect = [mock_cli_sub, mock_cli_method]

        async def run_with_sample():
            task = asyncio.create_task(
                _worker_event_loop(
                    worker_id=0,
                    endpoints=["opc.tcp://test:40451"],
                    out_queue=out_q,
                    stop_event=stop_event,
                    connect_concurrency=1,
                    sub_period_ms=50,
                    mode="active_burst",
                    burst_trigger_count=2,
                    max_retries=1,
                )
            )
            # Give loop moment to establish sub, then emit an event
            await asyncio.sleep(0.02)
            if captured_handler:
                ev = MagicMock()
                ev.Time = datetime.now(UTC)
                ev.Result = None
                captured_handler.event_notification(ev)
            await task

        import asyncio

        await run_with_sample()
        # Verify BATCH with sample was flushed
        assert any(call[0][0].get("type") == "BATCH" for call in out_q.put.call_args_list)


def test_fleet_client_pool_start_with_empty_shard():
    pool = OpcUaClientPool(endpoints=["opc.tcp://localhost:40451"], max_workers=1)
    mock_proc = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.Process.return_value = mock_proc
    pool._ctx = mock_ctx

    orig_enum = enumerate

    def fake_enum(seq):
        if seq == [["opc.tcp://localhost:40451"]]:
            return orig_enum([["opc.tcp://localhost:40451"], []])
        return orig_enum(seq)

    with patch("ijt_performance_client.opcua_client_pool.enumerate", side_effect=fake_enum):
        pool.start()

    # 1 process started, empty shard skipped via continue
    assert mock_ctx.Process.call_count == 1
    assert len(pool._processes) == 1


@pytest.mark.asyncio
async def test_worker_event_loop_periodic_flush_triggered():
    import asyncio
    import threading

    from ijt_performance_client.opcua_client_pool import _worker_event_loop

    out_q = MagicMock()
    stop_event = threading.Event()

    with (
        patch("ijt_performance_client.opcua_client_pool.Client") as mock_client_cls,
        patch("ijt_performance_client.opcua_client_pool.load_ijt_type_definitions"),
        patch("ijt_performance_client.opcua_client_pool.calibrate_clock_skew", return_value=0.0),
        patch("ijt_performance_client.opcua_client_pool.resolve_namespace_index", return_value=2),
    ):
        mock_cli_sub = MagicMock()
        mock_cli_sub.connect = AsyncMock()
        mock_sub = MagicMock()
        mock_sub.delete = AsyncMock()
        mock_sub.subscribe_events = AsyncMock()

        captured_handler = None

        def fake_create_sub(period, handler):
            nonlocal captured_handler
            captured_handler = handler
            return mock_sub

        mock_cli_sub.create_subscription = AsyncMock(side_effect=fake_create_sub)
        mock_client_cls.return_value = mock_cli_sub

        orig_sleep = asyncio.sleep

        async def fast_sleep(dur):
            if dur >= 1.0:
                if captured_handler and not stop_event.is_set():
                    ev = MagicMock()
                    ev.Time = datetime.now(UTC)
                    ev.Result = None
                    captured_handler.event_notification(ev)
                    await orig_sleep(0.01)
                    # Let periodic flush drain, then signal stop
                    stop_event.set()
                return
            await orig_sleep(0.005)

        with patch("ijt_performance_client.opcua_client_pool.asyncio.sleep", side_effect=fast_sleep):
            await _worker_event_loop(
                worker_id=0,
                endpoints=["opc.tcp://test:40451"],
                out_queue=out_q,
                stop_event=stop_event,
                connect_concurrency=1,
                sub_period_ms=50,
                mode="passive",
                burst_trigger_count=0,
                max_retries=1,
            )

        assert any(
            call[0][0].get("type") == "BATCH" and len(call[0][0].get("samples", [])) > 0
            for call in out_q.put.call_args_list
        )


def test_durable_handler_buffer_overflow():
    local_buf = []
    handler = _DurableWorkerSubHandler(
        endpoint="opc.tcp://s1:4840",
        local_buffer=local_buf,
        max_buffer_size=2,
    )
    ev = MagicMock()
    ev.Time = datetime.now(UTC)
    ev.Result = None

    handler.event_notification(ev)
    handler.event_notification(ev)
    assert len(local_buf) == 2
    assert handler.dropped_samples == 0

    # 3rd event exceeds max_buffer_size=2
    handler.event_notification(ev)
    assert len(local_buf) == 2
    assert handler.dropped_samples == 1


def test_pool_max_workers_validation():
    # Negative / zero / exceeded max workers
    with pytest.raises(ValueError, match="max_workers must be an integer between 1 and 32"):
        OpcUaClientPool(endpoints=["opc.tcp://s1:4840"], max_workers=0)

    with pytest.raises(ValueError, match="max_workers must be an integer between 1 and 32"):
        OpcUaClientPool(endpoints=["opc.tcp://s1:4840"], max_workers=33)

    with pytest.raises(ValueError, match="max_workers must be an integer between 1 and 32"):
        OpcUaClientPool(endpoints=["opc.tcp://s1:4840"], max_workers="bad")  # type: ignore[arg-type]


def test_pool_stop_idempotent_and_queue_cleanup():
    pool = OpcUaClientPool(endpoints=["opc.tcp://s1:4840"])
    pool._stopped = True
    samples = pool.stop()
    assert samples == []

    # Queue close exception handling
    pool._stopped = False
    mock_queue = MagicMock()
    mock_queue.close.side_effect = RuntimeError("Queue closed")
    mock_queue.join_thread.side_effect = RuntimeError("Thread joined")
    pool._out_queue = mock_queue
    pool._processes = []
    pool.stop()
    assert pool._stopped is True


def test_verify_coverage_dropped_samples_and_burst_failures():
    pool = OpcUaClientPool(endpoints=["opc.tcp://s1:4840"], require_full_coverage=False)
    pool.connected_endpoints = {"opc.tcp://s1:4840"}
    pool.completed_worker_ids = {0}
    pool._num_workers_started = 1
    sample = LatencySample(sample_id=1, endpoint="opc.tcp://s1:4840")

    # Dropped samples with require_full_coverage=False (warning only)
    pool.total_dropped_samples = 3
    valid, msg = pool.verify_coverage([sample])
    assert valid is True
    assert "dropped due to buffer backpressure" in msg

    # Dropped samples with require_full_coverage=True (failure)
    pool.require_full_coverage = True
    valid, msg = pool.verify_coverage([sample])
    assert valid is False
    assert "Buffer overflow backpressure" in msg

    # Burst trigger failures with 0 samples and require_full_coverage=True
    pool.total_dropped_samples = 0
    pool.burst_trigger_failures = 2
    pool.mode = "active_burst"
    valid, msg = pool.verify_coverage([])
    assert valid is False
    assert "Active burst trigger failure" in msg

    # Teardown errors propagate to worker_errors
    pool.teardown_errors = ["Teardown subscription failed"]
    valid, msg = pool.verify_coverage([sample])
    assert valid is False
    assert "Teardown subscription failed" in msg
    assert pool.worker_errors == []


def test_dropped_sample_totals_are_cumulative_not_additive():
    pool = OpcUaClientPool(endpoints=["opc.tcp://s1:4840"])

    pool._process_queue_msg({"type": "BATCH", "worker_id": 0, "samples": [], "dropped_samples": 2})
    pool._process_queue_msg({"type": "BATCH", "worker_id": 0, "samples": [], "dropped_samples": 3})
    pool._process_queue_msg({"type": "DONE", "worker_id": 0, "dropped_samples": 3})
    pool._process_queue_msg({"type": "DONE", "worker_id": 1, "dropped_samples": 4})

    assert pool.total_dropped_samples == 7


@pytest.mark.asyncio
async def test_worker_event_loop_teardown_and_burst_failure_coverage():
    import threading

    from ijt_performance_client.opcua_client_pool import _worker_event_loop

    out_q = MagicMock()
    stop_event = threading.Event()

    def fail_and_stop(*args, **kwargs):
        stop_event.set()
        raise RuntimeError("Method call failed")

    with (
        patch("ijt_performance_client.opcua_client_pool.resolve_namespace_index", AsyncMock(return_value=2)),
        patch("ijt_performance_client.opcua_client_pool.load_ijt_type_definitions", AsyncMock()),
        patch("ijt_performance_client.opcua_client_pool.calibrate_clock_skew", AsyncMock(return_value=0.0)),
        patch("ijt_performance_client.opcua_client_pool.Client") as mock_client_cls,
        patch("ijt_performance_client.opcua_client_pool._locate_simulate_method") as mock_loc_sim,
    ):
        mock_cli = MagicMock()
        mock_cli.connect = AsyncMock()
        mock_sub = MagicMock()
        # sub.delete raises exception
        mock_sub.delete = AsyncMock(side_effect=RuntimeError("Sub delete failed"))
        mock_sub.subscribe_events = AsyncMock()
        mock_cli.create_subscription = AsyncMock(return_value=mock_sub)

        # disconnect_client in teardown raises
        mock_client_cls.return_value = mock_cli

        # active burst simulation method
        mock_sim_res = MagicMock()
        mock_sim_meth = MagicMock()
        mock_sim_res.call_method = AsyncMock(side_effect=fail_and_stop)
        mock_loc_sim.return_value = (mock_sim_res, mock_sim_meth)

        orig_sleep = asyncio.sleep

        async def fast_sleep(dur):
            await orig_sleep(0.001)

        with (
            patch(
                "ijt_performance_client.opcua_client_pool.disconnect_client",
                AsyncMock(side_effect=RuntimeError("Disconnect failed")),
            ),
            patch("ijt_performance_client.opcua_client_pool.asyncio.sleep", side_effect=fast_sleep),
        ):
            await _worker_event_loop(
                worker_id=0,
                endpoints=["opc.tcp://test:40451"],
                out_queue=out_q,
                stop_event=stop_event,
                connect_concurrency=1,
                sub_period_ms=50,
                mode="active_burst",
                burst_trigger_count=1,
                max_retries=1,
            )

        # Check DONE payload contains teardown errors and burst failures
        done_msgs = [c[0][0] for c in out_q.put.call_args_list if c[0][0].get("type") == "DONE"]
        assert len(done_msgs) == 1
        assert done_msgs[0]["burst_failures"] == 1
        assert len(done_msgs[0]["teardown_errors"]) > 0


def test_verify_coverage_warning_when_partial_coverage_allowed():
    """Covers line 726: burst failures generate warning when require_full_coverage is False."""
    pool = OpcUaClientPool(endpoints=["opc.tcp://localhost:40451"], require_full_coverage=False, mode="active_burst")
    pool.burst_trigger_failures = 2
    pool.burst_trigger_errors = ["call failed"]
    pool.connected_endpoints = {"opc.tcp://localhost:40451"}
    ok, msg = pool.verify_coverage()
    assert ok is True
    assert "Warning: 2 active trigger failures" in msg


def test_collect_samples_queue_error_raises_runtime_error():
    """Covers lines 610-611: queue closed during collection raises RuntimeError."""
    pool = OpcUaClientPool(endpoints=["opc.tcp://localhost:40451"])
    mock_queue = MagicMock()
    mock_queue.get.side_effect = EOFError("Queue broken")
    pool._out_queue = mock_queue
    pool._stopped = False
    with pytest.raises(RuntimeError, match="Worker result queue closed during collection"):
        pool.collect_samples(duration_seconds=5.0)


def test_stop_queue_error_handling():
    """Covers lines 632-634 and 656-658: queue errors during shutdown and final drain."""
    pool = OpcUaClientPool(endpoints=["opc.tcp://localhost:40451"])
    mock_queue = MagicMock()
    mock_queue.get.side_effect = OSError("Queue OS error")
    mock_queue.get_nowait.side_effect = ValueError("Queue bad value")
    pool._out_queue = mock_queue
    pool._stop_event = MagicMock()
    pool._processes = []
    pool._stopped = False
    pool.stop(drain_timeout_s=0.1)
    assert any("Worker result queue closed during shutdown:" in err for err in pool.worker_errors)
    assert any("Worker result queue closed during final drain:" in err for err in pool.worker_errors)
