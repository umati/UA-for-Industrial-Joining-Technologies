"""
Unit tests for process-sharded client pool, worker handlers,
message parsing, and coverage verification.
"""

import asyncio
import multiprocessing as mp
import queue
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from asyncua import ua

from src.engine.client_pool import (
    OpcUaClientPool,
    _DurableWorkerSubHandler,
    _find_child,
    _locate_simulate_method,
    _worker_process_entry,
)
from src.results import ClockCalibration, LatencySample


@pytest.fixture(autouse=True)
def _no_namespace_metadata_reads():
    """Worker tests use scripted get_node mocks; namespace metadata reading is tested separately."""
    with patch(
        "src.engine.client_pool.read_namespace_metadata",
        new=AsyncMock(return_value={"version": None, "publication_date": None}),
    ):
        yield


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

    with patch("src.engine.client_pool._find_child") as mock_find:
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
                    "integrity_status": "VALID",
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
                    "integrity_status": "VALID",
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
    from src.engine.client_pool import _worker_event_loop

    out_q = MagicMock()
    stop_event = MagicMock()
    # Stop immediately
    stop_event.is_set.side_effect = [False, True, True, True, True]

    with (
        patch("src.engine.client_pool.Client") as mock_client_cls,
        patch("src.engine.client_pool.load_ijt_type_definitions"),
        patch("src.engine.client_pool.calibrate_clock_skew", return_value=ClockCalibration()),
        patch("src.engine.client_pool.resolve_namespace_index", return_value=3),
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
    from src.engine.client_pool import _worker_event_loop

    out_q = MagicMock()
    stop_event = MagicMock()
    # Stop after burst round
    stop_event.is_set.side_effect = [False, False, False, True, True, True]

    with (
        patch("src.engine.client_pool.Client") as mock_client_cls,
        patch("src.engine.client_pool.load_ijt_type_definitions"),
        patch("src.engine.client_pool.calibrate_clock_skew", return_value=ClockCalibration()),
        patch("src.engine.client_pool.resolve_namespace_index", return_value=3),
        patch("src.engine.client_pool._locate_simulate_method") as mock_locate,
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
            settle_timeout_s=0.0,
            burst_trigger_count=1,
            max_retries=1,
        )

        mock_sim_res.call_method.assert_awaited_once()
        done = next(c.args[0] for c in out_q.put.call_args_list if c.args[0]["type"] == "DONE")
        stats = done["endpoint_stats"]["opc.tcp://mock-server:40451"]
        assert stats["calls_attempted"] == 1
        assert stats["calls_succeeded"] == 1
        assert stats["calls_failed"] == 0
        assert isinstance(stats["first_success_send_us"], int)


@pytest.mark.asyncio
async def test_worker_event_loop_connection_exhaustion():
    from src.engine.client_pool import _worker_event_loop

    out_q = MagicMock()
    stop_event = MagicMock()
    stop_event.is_set.return_value = False

    with patch("src.engine.client_pool.Client") as mock_client_cls:
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
    from src.engine.client_pool import _worker_process_entry

    out_q = MagicMock()
    stop_event = MagicMock()

    with patch("src.engine.client_pool._worker_event_loop", new_callable=AsyncMock) as mock_loop:
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
    from src.engine.client_pool import _worker_process_entry

    out_q = MagicMock()
    stop_event = MagicMock()

    proc_err = RuntimeError("Process failure")
    # Patch _worker_event_loop with a sync MagicMock to avoid creating an unawaited coroutine
    with (
        patch("src.engine.client_pool._worker_event_loop", new_callable=MagicMock, return_value=None),
        patch("src.engine.client_pool.asyncio.run", side_effect=proc_err),
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
                    "integrity_status": "VALID",
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
    from src.engine.client_pool import _worker_event_loop

    out_q = MagicMock()
    stop_event = MagicMock()
    stop_event.is_set.return_value = False

    with (
        patch("src.engine.client_pool.Client") as mock_client_cls,
        patch("src.engine.client_pool.load_ijt_type_definitions"),
        patch("src.engine.client_pool.calibrate_clock_skew", return_value=ClockCalibration()),
        patch("src.engine.client_pool.resolve_namespace_index", return_value=3),
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

    with patch("src.engine.client_pool._find_child") as mock_find:
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
                    "integrity_status": "VALID",
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
    from src.engine.client_pool import _worker_event_loop

    out_q = MagicMock()
    stop_event = MagicMock()
    # stop_event: run connect, then run burst, then stop
    stop_event.is_set.side_effect = [False, False, False, False, True, True, True, True, True]

    with (
        patch("src.engine.client_pool.Client") as mock_client_cls,
        patch("src.engine.client_pool.load_ijt_type_definitions"),
        patch("src.engine.client_pool.calibrate_clock_skew", return_value=ClockCalibration()),
        patch("src.engine.client_pool.resolve_namespace_index", return_value=2),
        patch("src.engine.client_pool._locate_simulate_method") as mock_loc_sim,
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
            settle_timeout_s=0.0,
            burst_trigger_count=1,
            max_retries=1,
        )

        out_q.put.assert_called()


@pytest.mark.asyncio
async def test_worker_event_loop_ns_missing_and_retry_backoff():
    from src.engine.client_pool import _worker_event_loop

    out_q = MagicMock()
    stop_event = MagicMock()
    stop_event.is_set.return_value = False

    with (
        patch("src.engine.client_pool.Client") as mock_client_cls,
        patch("src.engine.client_pool.load_ijt_type_definitions"),
        patch("src.engine.client_pool.calibrate_clock_skew", return_value=ClockCalibration()),
        patch("src.engine.client_pool.resolve_namespace_index", return_value=None),  # Missing NS
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
    from src.engine.client_pool import _worker_event_loop

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
        patch("src.engine.client_pool.Client") as mock_client_cls,
        patch("src.engine.client_pool.load_ijt_type_definitions"),
        patch("src.engine.client_pool.calibrate_clock_skew", return_value=ClockCalibration()),
        patch("src.engine.client_pool.resolve_namespace_index", return_value=2),
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
    from src.engine.client_pool import _worker_process_entry

    # Broken out_queue whose put raises
    bad_q = MagicMock()
    bad_q.put.side_effect = RuntimeError("Broken pipe")

    with patch(
        "src.engine.client_pool._worker_event_loop",
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
            verbose=True,
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
    from src.engine.client_pool import _worker_event_loop

    out_q = MagicMock()
    stop_event = MagicMock()
    # Let connect succeed, then set stop_event
    stop_event.is_set.side_effect = [False, False, False, True, True, True, True, True]

    with (
        patch("src.engine.client_pool.Client") as mock_client_cls,
        patch("src.engine.client_pool.load_ijt_type_definitions"),
        patch("src.engine.client_pool.calibrate_clock_skew", return_value=ClockCalibration()),
        patch("src.engine.client_pool.resolve_namespace_index", return_value=2),
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
                    settle_timeout_s=0.0,
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

    with patch("src.engine.client_pool.enumerate", side_effect=fake_enum):
        pool.start()

    # 1 process started, empty shard skipped via continue
    assert mock_ctx.Process.call_count == 1
    assert len(pool._processes) == 1


@pytest.mark.asyncio
async def test_worker_event_loop_periodic_flush_triggered():
    import asyncio
    import threading

    from src.engine.client_pool import _worker_event_loop

    out_q = MagicMock()
    stop_event = threading.Event()

    with (
        patch("src.engine.client_pool.Client") as mock_client_cls,
        patch("src.engine.client_pool.load_ijt_type_definitions"),
        patch("src.engine.client_pool.calibrate_clock_skew", return_value=ClockCalibration()),
        patch("src.engine.client_pool.resolve_namespace_index", return_value=2),
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

        with patch("src.engine.client_pool.asyncio.sleep", side_effect=fast_sleep):
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


def test_pool_max_workers_autoscaling():
    # 1. Single endpoint defaults to 1 worker
    pool_1 = OpcUaClientPool(endpoints=["opc.tcp://s1:4840"])
    assert pool_1.max_workers == 1

    # 2. 2 endpoints defaults to 2 workers
    pool_2 = OpcUaClientPool(endpoints=["opc.tcp://s1:4840", "opc.tcp://s2:4840"])
    assert pool_2.max_workers == 2

    # 3. 150 endpoints auto-scales with CPU count
    eps_150 = [f"opc.tcp://s{i}:4840" for i in range(150)]
    with patch("os.cpu_count", return_value=16):
        pool_150 = OpcUaClientPool(endpoints=eps_150)
        assert pool_150.max_workers == 8  # (150 + 19) // 20 = 8

    # 4. Large fleet capped by cpu_count
    with patch("os.cpu_count", return_value=4):
        pool_capped = OpcUaClientPool(endpoints=eps_150)
        assert pool_capped.max_workers == 4


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
    mock_queue.get.side_effect = queue.Empty
    mock_queue.get_nowait.side_effect = queue.Empty
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
    assert "dropped because the client buffer was full" in msg

    # Dropped samples with require_full_coverage=True (failure)
    pool.require_full_coverage = True
    valid, msg = pool.verify_coverage([sample])
    assert valid is False
    assert "Client buffer full" in msg

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


def test_process_queue_msg_restores_audit_and_clamping_fields():
    pool = OpcUaClientPool(endpoints=["opc.tcp://s1:4840"])
    raw_sample = {
        "sample_id": 1,
        "endpoint": "opc.tcp://s1:4840",
        "clock_skew_ms": -1.5,
        "joining_duration_ms": 1200.0,
        "server_processing_time_ms": 15.0,
        "network_transport_time_ms": 25.0,
        "total_result_transfer_time_ms": 40.0,
        "raw_network_transport_time_ms": 25.0,
        "raw_total_result_transfer_time_ms": 40.0,
        "is_clamped_to_zero": False,
        "result_id": "RES-001",
        "result_evaluation": "OK",
        "trace_curves_count": 3,
        "trace_total_points": 750,
        "trace_declared_points": 750,
        "trace_decoded_points": 750,
        "trace_is_incomplete": False,
        "start_time": "2026-10-01T12:00:00+00:00",
        "end_time": "2026-10-01T12:00:01.200000+00:00",
        "creation_time": "2026-10-01T12:00:01.205000+00:00",
        "event_time": "2026-10-01T12:00:01.215000+00:00",
        "client_received_time": "2026-10-01T12:00:01.240000+00:00",
    }
    pool._process_queue_msg({"type": "BATCH", "worker_id": 0, "samples": [raw_sample], "dropped_samples": 0})
    assert len(pool.collected_samples) == 1
    s = pool.collected_samples[0]
    assert s.trace_declared_points == 750
    assert s.trace_decoded_points == 750
    assert s.trace_is_incomplete is False
    assert s.raw_network_transport_time_ms == 25.0
    assert s.raw_total_result_transfer_time_ms == 40.0
    assert s.is_clamped_to_zero is False


@pytest.mark.asyncio
async def test_worker_event_loop_teardown_and_burst_failure_coverage():
    import threading

    from src.engine.client_pool import _worker_event_loop

    out_q = MagicMock()
    stop_event = threading.Event()

    def fail_and_stop(*args, **kwargs):
        stop_event.set()
        raise RuntimeError("Method call failed")

    with (
        patch("src.engine.client_pool.resolve_namespace_index", AsyncMock(return_value=2)),
        patch("src.engine.client_pool.load_ijt_type_definitions", AsyncMock()),
        patch("src.engine.client_pool.calibrate_clock_skew", AsyncMock(return_value=ClockCalibration())),
        patch("src.engine.client_pool.Client") as mock_client_cls,
        patch("src.engine.client_pool._locate_simulate_method") as mock_loc_sim,
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
                "src.engine.client_pool.disconnect_client",
                AsyncMock(side_effect=RuntimeError("Disconnect failed")),
            ),
            patch("src.engine.client_pool.asyncio.sleep", side_effect=fast_sleep),
        ):
            await _worker_event_loop(
                worker_id=0,
                endpoints=["opc.tcp://test:40451"],
                out_queue=out_q,
                stop_event=stop_event,
                connect_concurrency=1,
                sub_period_ms=50,
                mode="active_burst",
                settle_timeout_s=0.0,
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


def test_pool_burst_delay_validation():
    """Verify burst_delay validation and storage in OpcUaClientPool."""
    with pytest.raises(ValueError, match="burst_delay must be a finite non-negative number"):
        OpcUaClientPool(endpoints=["opc.tcp://localhost:40451"], burst_delay=-0.5)

    pool = OpcUaClientPool(endpoints=["opc.tcp://localhost:40451"], burst_delay=0.25)
    assert pool.burst_delay == 0.25


@pytest.mark.asyncio
async def test_worker_event_loop_connection_exception_and_method_cache_hit():
    import threading

    from src.engine.client_pool import _worker_event_loop

    out_q = MagicMock()
    stop_event = threading.Event()

    mock_client = MagicMock()
    mock_client.connect = AsyncMock()
    mock_client.create_subscription = AsyncMock()
    mock_sim = MagicMock()
    mock_sim.nodeid = 12345
    mock_sim.read_node_class = AsyncMock(return_value=ua.NodeClass.Object)
    mock_sim_bn = MagicMock()
    mock_sim_bn.Name = "SimulateResults"
    mock_sim.read_browse_name = AsyncMock(return_value=mock_sim_bn)
    mock_sim.call_method = AsyncMock()

    mock_meth = MagicMock()
    mock_meth.nodeid = 67890
    mock_meth.read_node_class = AsyncMock(return_value=ua.NodeClass.Method)
    mock_meth_bn = MagicMock()
    mock_meth_bn.Name = "SimulateSingleResult"
    mock_meth.read_browse_name = AsyncMock(return_value=mock_meth_bn)

    mock_sim.get_child = AsyncMock(return_value=mock_meth)
    mock_client.get_node = MagicMock(side_effect=[mock_sim, mock_meth])

    # First two connections succeed (ep1 populates method cache, ep2 hits cache), third raises BaseException
    call_count = 0
    captured_handlers = []

    class CustomBaseError(BaseException):
        pass

    def fake_create_sub(period, handler):
        captured_handlers.append(handler)
        mock_sub = MagicMock()
        mock_sub.subscribe_events = AsyncMock()
        mock_sub.delete = AsyncMock()
        return mock_sub

    def fake_client(url):
        nonlocal call_count
        call_count += 1
        cli = MagicMock()
        cli.connect = AsyncMock()
        cli.get_server_time = AsyncMock(return_value=datetime.now(UTC))
        if "fail" in url:
            cli.connect.side_effect = CustomBaseError("Fatal task error")
        cli.create_subscription = AsyncMock(side_effect=fake_create_sub)
        cli.get_node = MagicMock(side_effect=[mock_sim, mock_meth, mock_sim, mock_meth])
        return cli

    locate_mock = AsyncMock(return_value=(mock_sim, mock_meth))

    with (
        patch("src.engine.client_pool.Client", side_effect=fake_client),
        patch("src.engine.client_pool.load_ijt_type_definitions", new_callable=AsyncMock),
        patch("src.engine.client_pool.resolve_namespace_index", new_callable=AsyncMock, return_value=2),
        patch("src.engine.client_pool._locate_simulate_method", locate_mock),
    ):

        async def run_loop():
            task = asyncio.create_task(
                _worker_event_loop(
                    worker_id=0,
                    endpoints=["opc.tcp://ep1:40001", "opc.tcp://ep2:40002", "opc.tcp://fail:40003"],
                    out_queue=out_q,
                    stop_event=stop_event,
                    mode="both",
                    settle_timeout_s=0.0,
                    burst_trigger_count=1,
                    burst_delay=0.0,
                )
            )
            await asyncio.sleep(0.05)
            if captured_handlers:
                ev = MagicMock()
                ev.Time = datetime.now(UTC)
                ev.Result = None
                captured_handlers[0].event_notification(ev)
            stop_event.set()
            await task

        await run_loop()

    # Verify locate was called only once (ep1); ep2 safely reused cached candidate
    assert locate_mock.await_count == 1
    assert mock_sim.read_node_class.await_count >= 1
    assert mock_meth.read_node_class.await_count >= 1

    # Check that failed_endpoints captured the task error
    status_calls = [c[0][0] for c in out_q.put.call_args_list if c[0][0].get("type") == "FLEET_STATUS"]
    assert len(status_calls) >= 1
    assert any("opc.tcp://fail:40003" in sc.get("failed", {}) for sc in status_calls)


@pytest.mark.asyncio
async def test_worker_event_loop_method_not_found_and_burst_task_error():
    import threading

    from src.engine.client_pool import _worker_event_loop

    out_q = MagicMock()
    stop_event = threading.Event()

    mock_client = MagicMock()
    mock_client.connect = AsyncMock()
    mock_client.create_subscription = AsyncMock()

    with (
        patch("src.engine.client_pool.Client", return_value=mock_client),
        patch("src.engine.client_pool.load_ijt_type_definitions", new_callable=AsyncMock),
        patch("src.engine.client_pool.resolve_namespace_index", new_callable=AsyncMock, return_value=2),
        patch("src.engine.client_pool._locate_simulate_method", new_callable=AsyncMock, return_value=(None, None)),
        patch(
            "src.engine.client_pool.disconnect_client",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Disconnect fail"),
        ),
    ):

        async def run_loop():
            task = asyncio.create_task(
                _worker_event_loop(
                    worker_id=0,
                    endpoints=["opc.tcp://ep1:40001"],
                    out_queue=out_q,
                    stop_event=stop_event,
                    mode="active_burst",
                    settle_timeout_s=0.0,
                    burst_trigger_count=1,
                )
            )
            await asyncio.sleep(0.1)
            stop_event.set()
            await task

        await run_loop()

    # Verify teardown_errors recorded disconnect failure and burst_failures > 0
    done_calls = [c[0][0] for c in out_q.put.call_args_list if c[0][0].get("type") == "DONE"]
    assert len(done_calls) >= 1
    assert done_calls[0]["burst_failures"] >= 1
    assert any("Disconnect fail" in err for err in done_calls[0]["teardown_errors"])


@pytest.mark.asyncio
async def test_worker_event_loop_burst_task_exception_and_teardown_timeout():
    import threading

    from src.engine.client_pool import _worker_event_loop

    out_q = MagicMock()
    stop_event = threading.Event()

    mock_client = MagicMock()
    mock_client.connect = AsyncMock()
    mock_client.create_subscription = AsyncMock()

    mock_sim = MagicMock()
    mock_sim.nodeid = 111
    mock_meth = MagicMock()
    mock_meth.nodeid = 222
    # call_method raises BaseException
    mock_sim.call_method = AsyncMock(side_effect=BaseException("Base burst crash"))

    with (
        patch("src.engine.client_pool.Client", return_value=mock_client),
        patch("src.engine.client_pool.load_ijt_type_definitions", new_callable=AsyncMock),
        patch("src.engine.client_pool.resolve_namespace_index", new_callable=AsyncMock, return_value=2),
        patch(
            "src.engine.client_pool._locate_simulate_method", new_callable=AsyncMock, return_value=(mock_sim, mock_meth)
        ),
        patch("asyncio.wait_for", side_effect=TimeoutError("Teardown timeout")),
    ):

        async def run_loop():
            task = asyncio.create_task(
                _worker_event_loop(
                    worker_id=0,
                    endpoints=["opc.tcp://ep1:40001"],
                    out_queue=out_q,
                    stop_event=stop_event,
                    mode="active_burst",
                    settle_timeout_s=0.0,
                    burst_trigger_count=1,
                    burst_delay=0.01,
                )
            )
            await asyncio.sleep(0.1)
            stop_event.set()
            await task

        await run_loop()

    done_calls = [c[0][0] for c in out_q.put.call_args_list if c[0][0].get("type") == "DONE"]
    assert len(done_calls) >= 1
    assert any("Parallel teardown timed out" in err for err in done_calls[0]["teardown_errors"])
    assert any("unhandled burst task error" in err for err in done_calls[0]["burst_errors"])


def test_verify_coverage_target_sample_count_shortfall_strict():
    """Verify target sample count shortfall triggers failure in strict mode."""
    pool = OpcUaClientPool(endpoints=["opc.tcp://localhost:40451"], require_full_coverage=True)
    pool.connected_endpoints = {"opc.tcp://localhost:40451"}
    sample = LatencySample(sample_id=1, endpoint="opc.tcp://localhost:40451")
    valid, msg = pool.verify_coverage([sample], target_sample_count=5)
    assert valid is False
    assert "Sample target shortfall: collected 1/5 samples (20.0%). 4 samples short of target." in msg


def test_verify_coverage_target_sample_count_shortfall_warning():
    """Verify target sample count shortfall produces warning when allow_partial_samples is True."""
    pool = OpcUaClientPool(endpoints=["opc.tcp://localhost:40451"], require_full_coverage=False)
    pool.connected_endpoints = {"opc.tcp://localhost:40451"}
    sample = LatencySample(sample_id=1, endpoint="opc.tcp://localhost:40451")
    valid, msg = pool.verify_coverage([sample], target_sample_count=5, allow_partial_samples=True)
    assert valid is True
    assert "Warning: sample target shortfall: 1/5, 20.0%" in msg


def test_verify_coverage_target_sample_count_shortfall_single_server_fails_by_default():
    """Verify single-server run (require_full_coverage=False) still fails on sample shortfall by default."""
    pool = OpcUaClientPool(endpoints=["opc.tcp://localhost:40451"], require_full_coverage=False)
    pool.connected_endpoints = {"opc.tcp://localhost:40451"}
    sample = LatencySample(sample_id=1, endpoint="opc.tcp://localhost:40451")
    valid, msg = pool.verify_coverage([sample], target_sample_count=5)
    assert valid is False
    assert "Sample target shortfall: collected 1/5 samples (20.0%). 4 samples short of target." in msg


def test_verify_coverage_target_sample_count_satisfied():
    """Verify target sample count satisfied passes without warning or failure."""
    pool = OpcUaClientPool(endpoints=["opc.tcp://localhost:40451"], require_full_coverage=True)
    pool.connected_endpoints = {"opc.tcp://localhost:40451"}
    samples = [LatencySample(sample_id=i, endpoint="opc.tcp://localhost:40451") for i in range(5)]
    valid, msg = pool.verify_coverage(samples, target_sample_count=5)
    assert valid is True
    assert "shortfall" not in msg


@pytest.mark.asyncio
async def test_worker_event_loop_candidate_verification_failure_fallback():
    """Verify candidate method node verification failure falls back cleanly to _locate_simulate_method."""
    import threading

    from src.engine.client_pool import _worker_event_loop

    out_q = MagicMock()
    stop_event = threading.Event()

    mock_sim1 = MagicMock()
    mock_sim1.nodeid = 11111
    mock_sim1.call_method = AsyncMock()
    mock_meth1 = MagicMock()
    mock_meth1.nodeid = 22222

    # Candidate node for ep2 fails verification
    mock_sim2_cand = MagicMock()
    mock_sim2_cand.read_node_class = AsyncMock(side_effect=RuntimeError("Corrupt candidate node"))
    mock_meth2_cand = MagicMock()

    mock_sim2_located = MagicMock()
    mock_sim2_located.nodeid = 33333
    mock_sim2_located.call_method = AsyncMock()
    mock_meth2_located = MagicMock()
    mock_meth2_located.nodeid = 44444

    def fake_create_sub(period, handler):
        mock_sub = MagicMock()
        mock_sub.subscribe_events = AsyncMock()
        mock_sub.delete = AsyncMock()
        return mock_sub

    def fake_client(url):
        cli = MagicMock()
        cli.connect = AsyncMock()
        cli.get_server_time = AsyncMock(return_value=datetime.now(UTC))
        cli.create_subscription = AsyncMock(side_effect=fake_create_sub)
        if "ep1" in url:
            cli.get_node = MagicMock(side_effect=[mock_sim1, mock_meth1])
        else:
            cli.get_node = MagicMock(side_effect=[mock_sim2_cand, mock_meth2_cand])
        return cli

    locate_mock = AsyncMock(side_effect=[(mock_sim1, mock_meth1), (mock_sim2_located, mock_meth2_located)])

    with (
        patch("src.engine.client_pool.Client", side_effect=fake_client),
        patch("src.engine.client_pool.load_ijt_type_definitions", new_callable=AsyncMock),
        patch("src.engine.client_pool.resolve_namespace_index", new_callable=AsyncMock, return_value=2),
        patch("src.engine.client_pool._locate_simulate_method", locate_mock),
    ):

        async def run_loop():
            task = asyncio.create_task(
                _worker_event_loop(
                    worker_id=0,
                    endpoints=["opc.tcp://ep1:40001", "opc.tcp://ep2:40002"],
                    out_queue=out_q,
                    stop_event=stop_event,
                    mode="active_burst",
                    settle_timeout_s=0.0,
                    burst_trigger_count=1,
                    burst_delay=0.0,
                )
            )
            await asyncio.sleep(0.05)
            stop_event.set()
            await task

        await run_loop()

    # Verify ep2 actually attempted candidate node verification before falling back
    assert mock_sim2_cand.read_node_class.await_count >= 1

    # Both endpoints called _locate_simulate_method: ep1 initially, and ep2 after candidate verification failed
    assert locate_mock.await_count == 2


@pytest.mark.asyncio
async def test_worker_event_loop_method_setup_ns_missing_error():
    import threading

    from src.engine.client_pool import _worker_event_loop

    out_q = MagicMock()
    stop_event = threading.Event()

    def fake_create_sub(period, handler):
        mock_sub = MagicMock()
        mock_sub.subscribe_events = AsyncMock()
        mock_sub.delete = AsyncMock()
        return mock_sub

    cli = MagicMock()
    cli.connect = AsyncMock()
    cli.get_server_time = AsyncMock(return_value=datetime.now(UTC))
    cli.create_subscription = AsyncMock(side_effect=fake_create_sub)

    # First call to resolve_namespace_index is for subscription client (returns 2),
    # second call is for method client in setup_method_client (returns None, triggering RuntimeError).
    with (
        patch("src.engine.client_pool.Client", return_value=cli),
        patch("src.engine.client_pool.load_ijt_type_definitions", new_callable=AsyncMock),
        patch("src.engine.client_pool.resolve_namespace_index", new_callable=AsyncMock, side_effect=[2, None]),
    ):

        async def run_loop():
            task = asyncio.create_task(
                _worker_event_loop(
                    worker_id=0,
                    endpoints=["opc.tcp://ep1:40001"],
                    out_queue=out_q,
                    stop_event=stop_event,
                    mode="active_burst",
                    settle_timeout_s=0.0,
                    burst_trigger_count=1,
                    burst_delay=0.0,
                )
            )
            await asyncio.sleep(0.05)
            stop_event.set()
            await task

        await run_loop()

    done_calls = [c for c in out_q.put.call_args_list if c[0][0].get("type") == "DONE"]
    assert len(done_calls) == 1
    assert done_calls[0][0][0]["burst_failures"] == 1


def test_verify_coverage_per_endpoint_sample_shortfall():
    pool = OpcUaClientPool(
        endpoints=["opc.tcp://ep1:40001", "opc.tcp://ep2:40002"],
        require_full_coverage=True,
    )
    pool._num_workers_started = 1
    pool.completed_worker_ids = {0}
    pool.connected_endpoints = {"opc.tcp://ep1:40001", "opc.tcp://ep2:40002"}

    # 9 samples from ep1, 1 sample from ep2 = 10 total, but each needs 5
    now = datetime.now(UTC)
    samples = [
        LatencySample(sample_id=i, endpoint="opc.tcp://ep1:40001", client_received_time=now) for i in range(9)
    ] + [LatencySample(sample_id=10, endpoint="opc.tcp://ep2:40002", client_received_time=now)]

    # Strict mode: must fail due to uneven distribution / under-sampled ep2
    ok, msg = pool.verify_coverage(samples, target_sample_count=10)
    assert ok is False
    assert "Per-endpoint sample shortfall" in msg

    # Explicit target_samples_per_endpoint=5
    ok, msg = pool.verify_coverage(samples, target_samples_per_endpoint=5)
    assert ok is False
    assert "Per-endpoint sample shortfall" in msg

    # Partial allowed: warning emitted, result True
    ok, msg = pool.verify_coverage(samples, target_sample_count=10, allow_partial_samples=True)
    assert ok is True
    assert "Warning: per-endpoint sample shortfall" in msg


def test_collect_samples_non_finite_timing_validation():
    pool = OpcUaClientPool(endpoints=["opc.tcp://ep1:40001"])

    with pytest.raises(ValueError, match="duration_seconds must be a finite positive number"):
        pool.collect_samples(duration_seconds=float("nan"))

    with pytest.raises(ValueError, match="duration_seconds must be a finite positive number"):
        pool.collect_samples(duration_seconds=float("-inf"))

    with pytest.raises(ValueError, match="burst_delay must be a finite non-negative number"):
        OpcUaClientPool(endpoints=["opc.tcp://ep1:40001"], burst_delay=float("inf"))

    with pytest.raises(ValueError, match="burst_delay must be a finite non-negative number"):
        OpcUaClientPool(endpoints=["opc.tcp://ep1:40001"], burst_delay=float("nan"))


@pytest.mark.asyncio
async def test_worker_event_loop_mixed_namespace_collision():
    import threading

    from src.engine.client_pool import _worker_event_loop

    out_q = MagicMock()
    stop_event = threading.Event()

    cli1 = MagicMock()
    cli1.connect = AsyncMock()
    cli1.get_server_time = AsyncMock(return_value=datetime.now(UTC))
    cli1.create_subscription = AsyncMock(return_value=MagicMock())

    cli2 = MagicMock()
    cli2.connect = AsyncMock()
    cli2.get_server_time = AsyncMock(return_value=datetime.now(UTC))
    cli2.create_subscription = AsyncMock(return_value=MagicMock())

    # Return cli1 for ep1 and cli2 for ep2
    cli_instances = [cli1, cli2]

    def make_client(*args, **kwargs):
        return cli_instances.pop(0) if cli_instances else MagicMock()

    # resolve_namespace_index returns 2 for ep1, but 3 for ep2
    ns_returns = [2, 3]

    async def fake_resolve(cli, ns_uri):
        return ns_returns.pop(0) if ns_returns else 2

    with (
        patch("src.engine.client_pool.Client", side_effect=make_client),
        patch("src.engine.client_pool.load_ijt_type_definitions", new_callable=AsyncMock),
        patch("src.engine.client_pool.resolve_namespace_index", side_effect=fake_resolve),
    ):
        task = asyncio.create_task(
            _worker_event_loop(
                worker_id=0,
                endpoints=["opc.tcp://ep1:40001", "opc.tcp://ep2:40002"],
                out_queue=out_q,
                stop_event=stop_event,
                mode="passive",
                max_retries=1,
            )
        )
        await asyncio.sleep(0.1)
        stop_event.set()
        await task

    # Verify worker reported failure on ep2 due to mixed namespace collision
    fleet_status_calls = [c for c in out_q.put.call_args_list if c[0][0].get("type") == "FLEET_STATUS"]
    assert len(fleet_status_calls) >= 1
    last_status = fleet_status_calls[-1][0][0]
    assert "opc.tcp://ep2:40002" in last_status["failed"]
    assert "Mixed namespace indexes" in last_status["failed"]["opc.tcp://ep2:40002"]


def test_client_pool_connect_concurrency_partitioning():
    eps = [f"opc.tcp://10.0.0.{i}:4840" for i in range(1, 13)]
    pool = OpcUaClientPool(endpoints=eps, max_workers=4, connect_concurrency=20)
    # verify connect_concurrency is partitioned across workers
    assert pool.connect_concurrency == 20
    assert pool.max_workers == 4


def test_durable_worker_handler_deduplicates_result_ids():
    from types import SimpleNamespace
    from typing import Any

    from src.engine.client_pool import _DurableWorkerSubHandler
    from src.results import INTEGRITY_DUPLICATE, INTEGRITY_VALID

    buf: list[dict[str, Any]] = []
    handler = _DurableWorkerSubHandler(endpoint="opc.tcp://ep1:40001", local_buffer=buf)

    def spec_event():
        now = datetime.now(UTC)
        meta = SimpleNamespace(
            ResultId="RES-DUP-1",
            ResultEvaluation=1,
            ProcessingTimes=SimpleNamespace(StartTime=now, EndTime=now),
        )
        return SimpleNamespace(Time=now, Result=SimpleNamespace(ResultMetaData=meta))

    ev1 = spec_event()
    handler.event_notification(ev1)
    assert len(buf) == 1
    assert buf[0]["integrity_status"] == INTEGRITY_VALID
    assert "RES-DUP-1" in handler.seen_result_ids

    # Second event with exact same ResultId -> DUPLICATE
    ev2 = spec_event()
    handler.event_notification(ev2)
    assert len(buf) == 2
    assert buf[1]["integrity_status"] == INTEGRITY_DUPLICATE
    assert "Duplicate ResultId 'RES-DUP-1'" in buf[1]["integrity_reason"]


def test_evaluate_fleet_integrity_and_verify_coverage_gate():
    from src.engine import evaluate_fleet_integrity
    from src.results import (
        INTEGRITY_DUPLICATE,
        INTEGRITY_INCOMPLETE,
        INTEGRITY_UNMATCHED,
        INTEGRITY_VALID,
    )

    eps = ["opc.tcp://s1:4840", "opc.tcp://s2:4840"]
    s_valid1 = LatencySample(sample_id=1, endpoint=eps[0], result_id="R1", integrity_status=INTEGRITY_VALID)
    s_incomp = LatencySample(sample_id=2, endpoint=eps[0], result_id="R2", integrity_status=INTEGRITY_INCOMPLETE)
    s_dup = LatencySample(sample_id=3, endpoint=eps[1], result_id="R3", integrity_status=INTEGRITY_DUPLICATE)
    s_unmatch = LatencySample(sample_id=4, endpoint=eps[1], result_id="R4", integrity_status=INTEGRITY_UNMATCHED)

    # 1. Summary collects all categories
    summary = evaluate_fleet_integrity(
        samples=[s_valid1, s_incomp, s_dup, s_unmatch],
        endpoints=eps,
        min_valid_per_endpoint=2,
        dropped_samples=2,
        dropped_by_endpoint={eps[0]: 2},
    )
    assert summary.passed is False
    assert summary.total_valid == 1
    assert summary.total_incomplete == 1
    assert summary.total_duplicate == 1
    assert summary.total_unmatched == 1
    assert summary.total_dropped == 2
    assert summary.endpoints[eps[0]].dropped_count == 2
    assert summary.endpoints[eps[1]].dropped_count == 0
    # incomplete, duplicate, unmatched, quota; drops are counters only (run policy decides)
    assert len(summary.failure_reasons) == 4
    assert not any("dropped" in r for r in summary.failure_reasons)

    # 2. verify_coverage gate failure under strict mode
    pool = OpcUaClientPool(endpoints=eps, require_full_coverage=True)
    pool.connected_endpoints = set(eps)
    pool.completed_worker_ids = {0, 1}
    pool._num_workers_started = 2

    # Incomplete result fails strict verification (both endpoints covered, one incomplete)
    s_ep1_incomp = LatencySample(sample_id=5, endpoint=eps[1], integrity_status=INTEGRITY_INCOMPLETE)
    valid, msg = pool.verify_coverage([s_valid1, s_ep1_incomp], allow_partial_samples=False)
    assert valid is False
    assert "Benchmark Integrity Gate failed" in msg
    assert pool.fleet_integrity is not None
    assert pool.fleet_integrity.passed is False

    # allow_partial_samples relaxes only counts: invalid results still fail the gate
    valid, msg = pool.verify_coverage([s_valid1, s_ep1_incomp], allow_partial_samples=True)
    assert valid is False
    assert "Benchmark Integrity Gate failed" in msg
    assert pool.fleet_integrity.passed is False


def test_verify_coverage_allow_partial_relaxes_only_counts():
    eps = ["opc.tcp://s1:4840", "opc.tcp://s2:4840"]
    pool = OpcUaClientPool(endpoints=eps, require_full_coverage=True)
    pool.connected_endpoints = set(eps)
    pool.completed_worker_ids = {0}
    pool._num_workers_started = 1
    samples = [LatencySample(sample_id=i, endpoint=eps[i % 2], result_id=f"R{i}") for i in range(4)]

    valid, msg = pool.verify_coverage(samples, target_sample_count=10, target_samples_per_endpoint=5)
    assert valid is False
    assert pool.fleet_integrity is not None and pool.fleet_integrity.passed is False
    assert any("Sample target shortfall" in r for r in pool.fleet_integrity.failure_reasons)
    assert any("Per-endpoint sample shortfall" in r for r in pool.fleet_integrity.failure_reasons)
    assert "more failure(s)" in msg

    valid, msg = pool.verify_coverage(
        samples, target_sample_count=10, target_samples_per_endpoint=5, allow_partial_samples=True
    )
    assert valid is True
    assert pool.fleet_integrity.passed is True
    assert "Warning: sample target shortfall" in msg
    assert "Warning: per-endpoint sample shortfall" in msg


def test_verify_coverage_records_run_failures_in_integrity_summary():
    eps = ["opc.tcp://s1:4840"]
    pool = OpcUaClientPool(endpoints=eps, require_full_coverage=True)
    pool.connected_endpoints = set(eps)
    pool._num_workers_started = 1  # worker 0 never sent DONE
    pool.endpoint_stats = {eps[0]: {"dropped": 3}}
    pool.total_dropped_samples = 3

    valid, msg = pool.verify_coverage([LatencySample(sample_id=1, endpoint=eps[0], result_id="R1")])
    assert valid is False
    assert msg.startswith("Worker completion failure")
    fi = pool.fleet_integrity
    assert fi is not None
    assert fi.passed is False
    assert fi.total_valid == 1
    assert fi.endpoints[eps[0]].dropped_count == 3
    assert any("Worker completion failure" in r for r in fi.failure_reasons)
    assert any("Client buffer full" in r for r in fi.failure_reasons)


def test_process_queue_msg_merges_cumulative_endpoint_stats():
    eps = ["opc.tcp://s1:4840", "opc.tcp://s2:4840"]
    pool = OpcUaClientPool(endpoints=eps)
    pool._process_queue_msg(
        {"type": "BATCH", "worker_id": 0, "samples": [], "endpoint_stats": {eps[0]: {"dropped": 2}}}
    )
    pool._process_queue_msg(
        {"type": "BATCH", "worker_id": 0, "samples": [], "endpoint_stats": {eps[0]: {"dropped": 5}}}
    )
    # A stale, smaller cumulative value must not lower the counter
    pool._process_queue_msg({"type": "DONE", "worker_id": 0, "endpoint_stats": {eps[0]: {"dropped": 4}}})
    pool._process_queue_msg({"type": "DONE", "worker_id": 1, "endpoint_stats": {eps[1]: {"dropped": 1}}})
    assert pool.endpoint_stats == {eps[0]: {"dropped": 5}, eps[1]: {"dropped": 1}}


@pytest.mark.parametrize("bad", [-1.0, float("nan"), float("inf")])
def test_pool_rejects_invalid_clock_tolerance(bad):
    with pytest.raises(ValueError, match="clock_tolerance_ms must be a finite non-negative number"):
        OpcUaClientPool(endpoints=["opc.tcp://s1:4840"], clock_tolerance_ms=bad)


def test_clock_warnings_are_counted_but_never_fail_the_gate():
    from src.engine import evaluate_fleet_integrity
    from src.results import INTEGRITY_VALID

    ep = "opc.tcp://s1:4840"
    samples = [
        LatencySample(sample_id=1, endpoint=ep, result_id="R1", integrity_status=INTEGRITY_VALID, clock_warning=True),
        LatencySample(sample_id=2, endpoint=ep, result_id="R2", integrity_status=INTEGRITY_VALID),
    ]
    fi = evaluate_fleet_integrity(samples, [ep])
    assert fi.passed is True
    assert fi.total_clock_warnings == 1
    assert fi.endpoints[ep].clock_warning_count == 1

    pool = OpcUaClientPool(endpoints=[ep])
    pool.connected_endpoints = {ep}
    pool.completed_worker_ids = {0}
    pool._num_workers_started = 1
    valid, _msg = pool.verify_coverage(samples)
    assert valid is True
    assert pool.fleet_integrity is not None and pool.fleet_integrity.passed is True


def test_durable_worker_handler_forwards_clock_tolerance_and_rtt():
    from typing import Any

    from src.engine.client_pool import _DurableWorkerSubHandler

    buf: list[dict[str, Any]] = []
    start = datetime.now(UTC)
    handler = _DurableWorkerSubHandler(
        endpoint="opc.tcp://ep1:40001",
        local_buffer=buf,
        collection_start=start,
        clock_tolerance_ms=0.0,
        clock_rtt_ms=0.0,
    )
    old = start - timedelta(seconds=5)
    meta = SimpleNamespace(ResultId="R-OLD", ProcessingTimes=SimpleNamespace(StartTime=old, EndTime=old))
    handler.event_notification(SimpleNamespace(Time=old, Result=SimpleNamespace(ResultMetaData=meta)))
    assert buf[0]["clock_warning"] is True
    assert buf[0]["integrity_status"] == "VALID"


def test_durable_worker_handler_uses_wire_timing_from_publish_hooks():
    from typing import Any

    from src.engine.client_pool import _DurableWorkerSubHandler

    buf: list[dict[str, Any]] = []
    end = datetime.now(UTC) - timedelta(milliseconds=50)
    arrived, decoded = end + timedelta(milliseconds=20), end + timedelta(milliseconds=23)
    handler = _DurableWorkerSubHandler(endpoint="opc.tcp://ep1:40001", local_buffer=buf)
    meta = SimpleNamespace(ResultId="R1", ProcessingTimes=SimpleNamespace(StartTime=end, EndTime=end))
    with patch("src.engine.client_pool.current_publish_timing", return_value=(arrived, decoded)):
        handler.event_notification(SimpleNamespace(Time=end, Result=SimpleNamespace(ResultMetaData=meta)))
    sample = LatencySample.from_dict(buf[0])
    assert sample.timing_source == "wire"
    assert sample.delivery_time_ms == pytest.approx(20.0)
    assert sample.client_decode_time_ms == pytest.approx(3.0)
    assert sample.client_ready_time_ms == pytest.approx(23.0)
    assert sample.dispatch_delay_ms is not None and sample.dispatch_delay_ms >= 0.0


def test_pool_timing_summary_and_missing_hook_warning():
    ep = "opc.tcp://s1:4840"
    pool = OpcUaClientPool(endpoints=[ep])
    assert pool.timing_summary()["workers_reported"] == 0
    pool._process_queue_msg(
        {
            "type": "DONE",
            "worker_id": 0,
            "timing": {"hooks_installed": True, "hooks_reason": "", "loop_lag": {"max_ms": 12.5, "mean_ms": 1.0}},
        }
    )
    pool._process_queue_msg(
        {
            "type": "DONE",
            "worker_id": 1,
            "timing": {
                "hooks_installed": False,
                "hooks_reason": "internals changed",
                "loop_lag": {"max_ms": 3.0, "mean_ms": 2.0},
            },
        }
    )
    pool._process_queue_msg({"type": "DONE", "worker_id": 2, "timing": "not-a-dict"})
    summary = pool.timing_summary()
    assert summary == {
        "workers_reported": 2,
        "workers_without_hooks": 1,
        "hook_failure_reasons": ["internals changed"],
        "loop_lag_max_ms": 12.5,
        "loop_lag_worst_mean_ms": 2.0,
    }

    pool.connected_endpoints = {ep}
    pool.completed_worker_ids = {0, 1}
    pool._num_workers_started = 2
    samples = [LatencySample(sample_id=1, endpoint=ep, result_id="R1", integrity_status="VALID")]
    valid, msg = pool.verify_coverage(samples)
    assert valid is True  # a timing fallback is a warning, never a failure
    assert "Wire timing unavailable in 1 worker(s) (internals changed)" in msg


@pytest.mark.asyncio
async def test_worker_settles_until_timeout_when_results_are_missing():
    import time as _time

    from src.engine.client_pool import _worker_event_loop

    out_q = MagicMock()
    stop_event = MagicMock()

    with (
        patch("src.engine.client_pool.Client") as mock_client_cls,
        patch("src.engine.client_pool.load_ijt_type_definitions"),
        patch("src.engine.client_pool.resolve_namespace_index", return_value=3),
        patch("src.engine.client_pool._locate_simulate_method") as mock_locate,
    ):
        mock_cli = MagicMock()
        mock_cli.connect = AsyncMock()
        mock_sub = MagicMock(subscribe_events=AsyncMock(), delete=AsyncMock())
        mock_cli.create_subscription = AsyncMock(return_value=mock_sub)
        mock_client_cls.return_value = mock_cli
        sim = MagicMock(call_method=AsyncMock(side_effect=[None, RuntimeError("boom")]))
        mock_locate.return_value = (sim, MagicMock(nodeid=1))
        stop_event.is_set.side_effect = lambda: sim.call_method.await_count >= 2

        t0 = _time.monotonic()
        await _worker_event_loop(
            worker_id=0,
            endpoints=["opc.tcp://127.0.0.1:40451"],
            out_queue=out_q,
            stop_event=stop_event,
            mode="both",
            burst_trigger_count=2,
            burst_delay=0.0,
            max_retries=1,
            skip_clock_skew=True,
            settle_timeout_s=0.3,
        )
        assert _time.monotonic() - t0 >= 0.3  # no result arrived, so the full settle window was used

    done = next(c.args[0] for c in out_q.put.call_args_list if c.args[0]["type"] == "DONE")
    stats = done["endpoint_stats"]["opc.tcp://127.0.0.1:40451"]
    assert (stats["calls_attempted"], stats["calls_succeeded"], stats["calls_failed"]) == (2, 1, 1)


def _correlation_pool(mode, stats):
    ep = "opc.tcp://s1:4840"
    pool = OpcUaClientPool(endpoints=[ep], mode=mode, require_full_coverage=False)
    pool.connected_endpoints = {ep}
    pool.endpoint_stats = {ep: stats}
    return pool, ep


def _valid(ep, rid, received):
    return LatencySample(sample_id=1, endpoint=ep, result_id=rid, client_received_time=received)


def test_active_burst_marks_results_before_first_successful_call_unmatched():
    first = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    stats = {"calls_attempted": 1, "calls_succeeded": 1, "calls_failed": 0}
    stats["first_success_send_us"] = int(first.timestamp() * 1_000_000)
    pool, ep = _correlation_pool("active_burst", stats)
    early = _valid(ep, "R0", first - timedelta(milliseconds=1))
    on_time = _valid(ep, "R1", first + timedelta(milliseconds=5))
    valid, msg = pool.verify_coverage([early, on_time])
    assert early.integrity_status == "UNMATCHED"
    assert "before the first successful trigger call" in early.integrity_reason
    assert on_time.integrity_status == "VALID"
    assert valid is False  # UNMATCHED always fails the gate
    entry = pool.fleet_integrity.endpoints[ep]
    assert (entry.calls_attempted, entry.calls_succeeded, entry.valid_count) == (1, 1, 1)


def test_active_burst_without_successful_call_marks_all_unmatched():
    pool, ep = _correlation_pool("active_burst", {"calls_attempted": 1, "calls_succeeded": 0, "calls_failed": 1})
    sample = _valid(ep, "R1", datetime.now(UTC))
    pool.verify_coverage([sample])
    assert sample.integrity_status == "UNMATCHED"
    assert "no trigger call succeeded" in sample.integrity_reason


@pytest.mark.parametrize(
    ("mode", "valid_results", "succeeded", "ok", "text"),
    [
        ("active_burst", 2, 2, True, ""),
        ("active_burst", 1, 2, False, "fewer VALID results than successful trigger calls"),
        ("active_burst", 3, 2, False, "more VALID results than successful trigger calls"),
        ("both", 1, 2, False, "fewer VALID results than successful trigger calls"),
        ("both", 3, 2, True, "1 external event(s)"),
        ("passive", 0, 5, True, ""),
    ],
)
def test_call_result_correlation(mode, valid_results, succeeded, ok, text):
    first = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    stats = {"calls_attempted": succeeded, "calls_succeeded": succeeded, "calls_failed": 0}
    stats["first_success_send_us"] = int(first.timestamp() * 1_000_000)
    pool, ep = _correlation_pool(mode, stats)
    samples = [_valid(ep, f"R{i}", first + timedelta(seconds=1)) for i in range(valid_results)]
    valid, msg = pool.verify_coverage(samples, allow_partial_samples=True)
    assert valid is ok, msg
    assert text in msg
    if mode == "both" and valid_results > succeeded:
        assert pool.fleet_integrity.total_external_events == valid_results - succeeded
        assert pool.fleet_integrity.endpoints[ep].external_event_count == valid_results - succeeded


def test_pool_settle_timeout_validation_and_stop_drain_default():
    with pytest.raises(ValueError, match="settle_timeout_s"):
        OpcUaClientPool(endpoints=["opc.tcp://s:4840"], settle_timeout_s=-1.0)
    with pytest.raises(ValueError, match="settle_timeout_s"):
        OpcUaClientPool(endpoints=["opc.tcp://s:4840"], settle_timeout_s=float("nan"))
    assert OpcUaClientPool(endpoints=["opc.tcp://s:4840"], settle_timeout_s=0.0).settle_timeout_s == 0.0


def _ns_pool(meta):
    pool = OpcUaClientPool(endpoints=list(meta), require_full_coverage=False)
    pool.connected_endpoints = set(meta)
    pool._process_queue_msg({"type": "FLEET_STATUS", "connected": list(meta), "failed": {}, "namespace_metadata": meta})
    return pool


def test_namespace_metadata_consistent_passes_and_is_reported():
    meta = {
        ep: {"version": "1.01.0", "publication_date": "2024-06-01T00:00:00"}
        for ep in ("opc.tcp://a:1", "opc.tcp://b:2")
    }
    pool = _ns_pool(meta)
    valid, msg = pool.verify_coverage([])
    assert valid is True, msg
    assert "unverified" not in msg
    assert pool.fleet_integrity.endpoints["opc.tcp://a:1"].ijt_namespace_version == "1.01.0"


def test_namespace_version_mismatch_fails_even_with_partial_samples():
    pool = _ns_pool(
        {
            "opc.tcp://a:1": {"version": "1.01.0", "publication_date": None},
            "opc.tcp://b:2": {"version": "1.00.0", "publication_date": None},
        }
    )
    valid, msg = pool.verify_coverage([], allow_partial_samples=True)
    assert valid is False
    assert "IJT namespace model mismatch across endpoints (version: 1.01.0" in msg


def test_namespace_metadata_absent_is_unverified_warning_only():
    pool = _ns_pool(
        {
            "opc.tcp://a:1": {"version": None, "publication_date": None},
            "opc.tcp://b:2": {"version": "1.01.0", "publication_date": None, "ignored": "x"},
        }
    )
    valid, msg = pool.verify_coverage([])
    assert valid is True, msg
    assert "IJT namespace version unverified on 1 endpoint(s)" in msg
    assert pool.namespace_metadata["opc.tcp://b:2"] == {"version": "1.01.0", "publication_date": None}


@pytest.mark.asyncio
async def test_worker_rejects_second_endpoint_with_different_ijt_namespace_index():
    """Both endpoints connect concurrently; the one waiting on the type-load lock must still compare."""
    from src.engine.client_pool import _worker_event_loop

    out_q = MagicMock()
    stop_event = MagicMock()
    stop_event.is_set.return_value = False

    async def slow_load(_client):
        await asyncio.sleep(0.05)

    indexes = {"opc.tcp://a:1": 3, "opc.tcp://b:2": 4}

    def fake_client(url):
        cli = MagicMock(connect=AsyncMock())
        cli.url = url
        cli.create_subscription = AsyncMock(return_value=MagicMock(subscribe_events=AsyncMock(), delete=AsyncMock()))
        return cli

    async def resolve(cli, _uri):
        return indexes[cli.url]

    async def run():
        task = asyncio.create_task(
            _worker_event_loop(
                worker_id=0,
                endpoints=list(indexes),
                out_queue=out_q,
                stop_event=stop_event,
                max_retries=1,
                skip_clock_skew=True,
            )
        )
        while not any(c.args[0]["type"] == "FLEET_STATUS" for c in out_q.put.call_args_list):
            await asyncio.sleep(0.01)
        stop_event.is_set.return_value = True
        await task

    with (
        patch("src.engine.client_pool.Client", side_effect=lambda url: fake_client(url)),
        patch("src.engine.client_pool.load_ijt_type_definitions", side_effect=slow_load),
        patch("src.engine.client_pool.resolve_namespace_index", side_effect=resolve),
    ):
        await asyncio.wait_for(run(), timeout=10)

    status = next(c.args[0] for c in out_q.put.call_args_list if c.args[0]["type"] == "FLEET_STATUS")
    assert status["connected"] == ["opc.tcp://a:1"]
    assert "Mixed namespace indexes" in status["failed"]["opc.tcp://b:2"]


# --- Trigger-round completion: duration must never silently cut off requested rounds ---


class _FakeProc:
    def __init__(self, alive: bool = True) -> None:
        self.alive = alive

    def is_alive(self) -> bool:
        return self.alive


def _trigger_pool(mode: str = "both", rounds: int = 5, workers: int = 1) -> OpcUaClientPool:
    pool = OpcUaClientPool(endpoints=[f"opc.tcp://ep{i}:4000{i}" for i in range(workers)], mode=mode)
    pool._burst_trigger_count = rounds
    pool._worker_procs = {w: _FakeProc() for w in range(workers)}
    pool._out_queue = queue.Queue()
    return pool


def test_triggers_pending_until_every_live_worker_reports():
    pool = _trigger_pool(workers=3)
    assert pool._triggers_pending()
    pool._process_queue_msg({"type": "TRIGGERS_DONE", "worker_id": 0, "rounds_fired": 5, "endpoint_stats": {}})
    pool._process_queue_msg({"type": "ERROR", "worker_id": 1, "error": "boom"})
    assert pool._triggers_pending()
    pool._worker_procs[2].alive = False
    assert not pool._triggers_pending()
    assert pool.trigger_rounds_fired == {0: 5}


def test_triggers_not_pending_in_passive_mode_or_without_rounds():
    assert not _trigger_pool(mode="passive")._triggers_pending()
    assert not _trigger_pool(rounds=0)._triggers_pending()


def test_triggers_done_merges_call_stats():
    pool = _trigger_pool()
    stats = {"opc.tcp://ep0:40000": {"calls_attempted": 5, "calls_succeeded": 5}}
    pool._process_queue_msg({"type": "TRIGGERS_DONE", "worker_id": 0, "rounds_fired": 5, "endpoint_stats": stats})
    assert pool.endpoint_stats["opc.tcp://ep0:40000"]["calls_succeeded"] == 5


def test_done_records_rounds_without_overriding_triggers_done():
    pool = _trigger_pool(workers=2)
    pool._process_queue_msg({"type": "TRIGGERS_DONE", "worker_id": 0, "rounds_fired": 5})
    pool._process_queue_msg({"type": "DONE", "worker_id": 0, "trigger_rounds_fired": 5})
    pool._process_queue_msg({"type": "DONE", "worker_id": 1, "trigger_rounds_fired": 2})
    assert pool.trigger_rounds_fired == {0: 5, 1: 2}


def test_collect_samples_waits_past_duration_for_pending_triggers():
    import threading

    pool = _trigger_pool()
    # TRIGGERS_DONE arrives only after the 0.05 s duration has elapsed; collection must wait for it.
    timer = threading.Timer(
        0.3, pool._out_queue.put, args=({"type": "TRIGGERS_DONE", "worker_id": 0, "rounds_fired": 5},)
    )
    timer.start()
    try:
        pool.collect_samples(duration_seconds=0.05)
    finally:
        timer.cancel()
    assert pool.trigger_rounds_fired == {0: 5}
    assert not pool._triggers_pending()


def test_collect_samples_target_reached_still_waits_for_triggers():
    pool = _trigger_pool()
    pool.collected_samples.append(MagicMock())
    pool._out_queue.put({"type": "TRIGGERS_DONE", "worker_id": 0, "rounds_fired": 5})
    pool.collect_samples(duration_seconds=10.0, target_sample_count=1)
    assert pool.trigger_rounds_fired == {0: 5}


def test_collect_samples_extension_is_bounded():
    pool = _trigger_pool(rounds=1)
    pool.burst_delay = 0.0
    with patch("src.engine.client_pool._TRIGGER_COMPLETION_GRACE_S", 0.2):
        import time as _t

        t0 = _t.monotonic()
        pool.collect_samples(duration_seconds=0.05)
        assert _t.monotonic() - t0 < 2.0
    assert pool._triggers_pending()


def test_verify_coverage_reports_incomplete_trigger_rounds_first():
    pool = _trigger_pool()
    pool._num_workers_started = 1
    pool.completed_worker_ids = {0}
    pool.connected_endpoints = {"opc.tcp://ep0:40000"}
    pool._process_queue_msg({"type": "DONE", "worker_id": 0, "trigger_rounds_fired": 4})
    ok, msg = pool.verify_coverage([], target_sample_count=5)
    assert not ok
    assert msg.startswith("Trigger rounds incomplete: 1 worker(s)")
    assert "worker 0: 4/5" in msg
    assert "Sample target shortfall" in msg


def test_verify_coverage_passes_trigger_check_when_all_rounds_fired():
    pool = _trigger_pool()
    pool._process_queue_msg({"type": "TRIGGERS_DONE", "worker_id": 0, "rounds_fired": 5})
    _, msg = pool.verify_coverage([])
    assert "Trigger rounds incomplete" not in msg


@pytest.mark.asyncio
async def test_worker_reports_triggers_done_and_skips_pause_after_last_round():
    import threading

    from src.engine.client_pool import _worker_event_loop

    out_q = MagicMock()
    stop_event = threading.Event()
    mock_client = MagicMock()
    mock_client.connect = AsyncMock()
    mock_client.create_subscription = AsyncMock()
    sleeps: list[float] = []
    real_sleep = asyncio.sleep

    async def tracking_sleep(delay, *args, **kwargs):
        if delay == 0.3:
            sleeps.append(delay)
            delay = 0
        return await real_sleep(delay, *args, **kwargs)

    with (
        patch("src.engine.client_pool.Client", return_value=mock_client),
        patch("src.engine.client_pool.load_ijt_type_definitions", new_callable=AsyncMock),
        patch("src.engine.client_pool.resolve_namespace_index", new_callable=AsyncMock, return_value=2),
        patch("src.engine.client_pool._locate_simulate_method", new_callable=AsyncMock, return_value=(None, None)),
        patch("src.engine.client_pool.disconnect_client", new_callable=AsyncMock),
        patch("src.engine.client_pool.asyncio.sleep", side_effect=tracking_sleep),
    ):
        task = asyncio.create_task(
            _worker_event_loop(
                worker_id=0,
                endpoints=["opc.tcp://ep1:40001"],
                out_queue=out_q,
                stop_event=stop_event,
                mode="both",
                settle_timeout_s=0.0,
                burst_trigger_count=3,
                burst_delay=0.3,
            )
        )
        for _ in range(200):
            if any(c.args[0]["type"] == "TRIGGERS_DONE" for c in out_q.put.call_args_list):
                break
            await real_sleep(0.01)
        stop_event.set()
        await task

    msgs = [c.args[0] for c in out_q.put.call_args_list]
    done_trig = next(m for m in msgs if m["type"] == "TRIGGERS_DONE")
    assert done_trig["rounds_fired"] == 3 and done_trig["rounds_requested"] == 3
    assert next(m for m in msgs if m["type"] == "DONE")["trigger_rounds_fired"] == 3
    assert sleeps == [0.3, 0.3]  # pacing only between rounds, not after the last one


@pytest.mark.asyncio
async def test_worker_stopped_early_reports_fewer_rounds():
    import threading

    from src.engine.client_pool import _worker_event_loop

    out_q = MagicMock()
    stop_event = threading.Event()
    stop_event.set()
    mock_client = MagicMock()
    mock_client.connect = AsyncMock()
    mock_client.create_subscription = AsyncMock()

    with (
        patch("src.engine.client_pool.Client", return_value=mock_client),
        patch("src.engine.client_pool.load_ijt_type_definitions", new_callable=AsyncMock),
        patch("src.engine.client_pool.resolve_namespace_index", new_callable=AsyncMock, return_value=2),
        patch("src.engine.client_pool._locate_simulate_method", new_callable=AsyncMock, return_value=(None, None)),
        patch("src.engine.client_pool.disconnect_client", new_callable=AsyncMock),
    ):
        await _worker_event_loop(
            worker_id=0,
            endpoints=["opc.tcp://ep1:40001"],
            out_queue=out_q,
            stop_event=stop_event,
            mode="active_burst",
            settle_timeout_s=0.0,
            burst_trigger_count=4,
            burst_delay=0.0,
        )

    msgs = [c.args[0] for c in out_q.put.call_args_list]
    assert next(m for m in msgs if m["type"] == "TRIGGERS_DONE")["rounds_fired"] == 0
    assert next(m for m in msgs if m["type"] == "DONE")["trigger_rounds_fired"] == 0
