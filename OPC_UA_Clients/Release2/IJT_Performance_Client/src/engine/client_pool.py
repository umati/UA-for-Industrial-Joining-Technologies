"""
High-Performance Process-Sharded OPC UA Client Pool.

Controlled-validation concurrency architecture targeting 1 to 500+ industrial controllers:
1. Multi-Process Sharding:
   Endpoints are distributed evenly across worker processes (auto-scaled up to min(cpu_count, 32)
   processes based on endpoint count, or explicitly configured via -w / --workers).
   Each worker process runs an isolated CPython interpreter with its own GIL.
2. Non-Blocking AsyncIO Socket Multiplexing:
   Inside each process, a single async event loop manages its assigned sockets via OS kernel events.
3. Resilient Connection Lifecycle:
   Bounded connection retries with exponential backoff.
   Explicit error propagation from connection tasks (no silent partial fleet runs).
4. Worker-Local Buffering & Accounted Batch Flushes:
   Result callbacks append to worker-local memory; a background flush task periodically sends
   batches over multiprocessing IPC. Final flush and explicit DONE/ERROR handshake
   expose incomplete delivery; bounded buffers can still drop samples.
5. Explicit Subscription Teardown:
   Calls sub.delete() before client.disconnect() to reduce server-side session leakage.
"""

from __future__ import annotations

import asyncio
import logging
import math
import multiprocessing as mp
import os
import queue
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from asyncua import Client, ua

from ..config import is_loopback_endpoint
from ..namespaces import (
    BN_SIMULATE_RESULTS,
    BN_SIMULATE_SINGLE_RESULT,
    JOINING_SYSTEM_RESULT_READY_EVENT_TYPE_ID,
    NS_APP,
    NS_IJT_BASE,
    read_namespace_metadata,
    resolve_namespace_index,
)
from ..results import (
    DEFAULT_CLOCK_TOLERANCE_MS,
    INTEGRITY_DUPLICATE,
    INTEGRITY_INCOMPLETE,
    INTEGRITY_UNMATCHED,
    INTEGRITY_VALID,
    ClockCalibration,
    LatencySample,
    calibrate_clock_skew,
    extract_sample_from_event,
)
from .session_policy import (
    apply_session_policy,
    disconnect_client,
    load_ijt_type_definitions,
    patch_asyncua_subtype_serializer,
)
from .timing_hooks import LoopLagMonitor, current_publish_timing, install_timing_hooks

logger = logging.getLogger(__name__)

# Auto worker sizing baseline: one worker per endpoint up to this value, then about one worker per
# 20 endpoints, capped at min(CPU count, MAX_SAFE_WORKER_PROCESSES). See OpcUaClientPool.__init__.
DEFAULT_MAX_WORKERS: int = 4
MAX_SAFE_WORKER_PROCESSES: int = 32
MAX_WORKER_BUFFER_SIZE: int = 5000
# Bounded wait after the last trigger round for results of successful calls to arrive.
DEFAULT_SETTLE_TIMEOUT_S: float = 5.0
_NS_META_KEYS = ("version", "publication_date")
# Worker teardown budget (subscription delete + disconnect) plus margin, added to the settle time
# when the master waits for workers to finish.
_WORKER_SHUTDOWN_BUDGET_S: float = 8.0


@dataclass
class EndpointIntegrity:
    """Integrity audit counters for a single OPC UA endpoint."""

    endpoint: str
    received_count: int = 0
    valid_count: int = 0
    incomplete_count: int = 0
    duplicate_count: int = 0
    unmatched_count: int = 0
    dropped_count: int = 0
    clock_warning_count: int = 0
    calls_attempted: int = 0
    calls_succeeded: int = 0
    calls_failed: int = 0
    external_event_count: int = 0  # mode 'both': VALID results beyond successful calls
    ijt_namespace_version: str | None = None  # None: not exposed by the server (unverified)
    ijt_namespace_publication_date: str | None = None


@dataclass
class FleetIntegritySummary:
    """Fleet-wide Benchmark Integrity Gate evaluation summary."""

    total_received: int = 0
    total_valid: int = 0
    total_incomplete: int = 0
    total_duplicate: int = 0
    total_unmatched: int = 0
    total_dropped: int = 0
    total_clock_warnings: int = 0
    total_calls_attempted: int = 0
    total_calls_succeeded: int = 0
    total_calls_failed: int = 0
    total_external_events: int = 0
    endpoints: dict[str, EndpointIntegrity] = field(default_factory=dict)
    passed: bool = False
    failure_reasons: list[str] = field(default_factory=list)


def evaluate_fleet_integrity(
    samples: list[LatencySample],
    endpoints: list[str],
    min_valid_per_endpoint: int = 0,
    dropped_samples: int = 0,
    dropped_by_endpoint: dict[str, int] | None = None,
) -> FleetIntegritySummary:
    """Evaluate result validity and optional per-endpoint VALID quotas.

    Dropped samples are recorded as counters only; whether drops fail a run is a run-level
    policy decided by ``OpcUaClientPool.verify_coverage``.
    """
    summary = FleetIntegritySummary(total_dropped=dropped_samples)
    for ep in endpoints:
        summary.endpoints[ep] = EndpointIntegrity(endpoint=ep)
    for ep, dropped in (dropped_by_endpoint or {}).items():
        summary.endpoints.setdefault(ep, EndpointIntegrity(endpoint=ep)).dropped_count = dropped

    for s in samples:
        ep_entry = summary.endpoints.setdefault(s.endpoint, EndpointIntegrity(endpoint=s.endpoint))
        ep_entry.received_count += 1
        summary.total_received += 1
        if s.clock_warning:
            ep_entry.clock_warning_count += 1
            summary.total_clock_warnings += 1

        if s.integrity_status == INTEGRITY_VALID:
            ep_entry.valid_count += 1
            summary.total_valid += 1
        elif s.integrity_status == INTEGRITY_INCOMPLETE:
            ep_entry.incomplete_count += 1
            summary.total_incomplete += 1
        elif s.integrity_status == INTEGRITY_DUPLICATE:
            ep_entry.duplicate_count += 1
            summary.total_duplicate += 1
        elif s.integrity_status == INTEGRITY_UNMATCHED:
            ep_entry.unmatched_count += 1
            summary.total_unmatched += 1

    if summary.total_incomplete > 0:
        summary.failure_reasons.append(
            f"{summary.total_incomplete} samples failed validation (incomplete or missing data)"
        )

    if summary.total_duplicate > 0:
        summary.failure_reasons.append(f"{summary.total_duplicate} duplicate ResultIds detected")

    if summary.total_unmatched > 0:
        summary.failure_reasons.append(f"{summary.total_unmatched} stale or unmatched events detected")

    if min_valid_per_endpoint > 0:
        under_quota = [
            f"{ep}: {entry.valid_count}/{min_valid_per_endpoint}"
            for ep, entry in summary.endpoints.items()
            if entry.valid_count < min_valid_per_endpoint
        ]
        if under_quota:
            summary.failure_reasons.append(
                f"{len(under_quota)} endpoint(s) did not meet the per-server target of VALID results ({'; '.join(under_quota[:3])})"
            )

    summary.passed = len(summary.failure_reasons) == 0
    return summary


async def _find_child(parent_node: Any, ns_idx: int | None, browse_name: str) -> Any | None:
    """Helper to find a child node under a parent by its BrowseName."""
    if ns_idx is not None:
        try:
            return await parent_node.get_child(f"{ns_idx}:{browse_name}")
        except Exception as exc:
            logger.debug(f"Direct child lookup failed for {ns_idx}:{browse_name}: {exc}")

    try:
        children = await parent_node.get_children()
    except Exception as exc:
        logger.debug(f"get_children failed on parent node: {exc}")
        return None

    fallback_child = None
    for child in children:
        try:
            bn = await child.read_browse_name()
            if getattr(bn, "Name", None) == browse_name:
                if ns_idx is None or getattr(bn, "NamespaceIndex", None) == ns_idx:
                    return child
                if fallback_child is None:
                    fallback_child = child
        except Exception as exc:
            logger.debug(f"read_browse_name skipped for child: {exc}")
            continue
    return fallback_child


async def _locate_simulate_method(client: Client, ns_app: int | None) -> tuple[Any | None, Any | None]:
    """Helper to find Objects -> TighteningSystem -> Simulations -> SimulateResults -> SimulateSingleResult."""
    objects = client.nodes.objects
    js = await _find_child(objects, ns_app, "TighteningSystem")
    if js is None:
        js = await _find_child(objects, ns_app, "JoiningSystem")
    if js is None:
        return None, None

    sim = await _find_child(js, ns_app, "Simulations")
    if sim is None:
        return None, None

    sim_results = await _find_child(sim, ns_app, BN_SIMULATE_RESULTS)
    if sim_results is None:
        return None, None

    method_node = await _find_child(sim_results, ns_app, BN_SIMULATE_SINGLE_RESULT)
    return sim_results, method_node


class _DurableWorkerSubHandler:
    """Store event samples in bounded worker-local memory before batched IPC.

    Overflow is counted and reported rather than hidden.
    """

    def __init__(
        self,
        endpoint: str,
        local_buffer: list[dict[str, Any]],
        clock_skew_ms: float = 0.0,
        max_buffer_size: int = MAX_WORKER_BUFFER_SIZE,
        trace_expected: bool = False,
        collection_start: datetime | None = None,
        clock_tolerance_ms: float = DEFAULT_CLOCK_TOLERANCE_MS,
        clock_rtt_ms: float | None = None,
    ) -> None:
        self.endpoint = endpoint
        self.clock_tolerance_ms = clock_tolerance_ms
        self.clock_rtt_ms = clock_rtt_ms
        self.local_buffer = local_buffer
        self.clock_skew_ms = clock_skew_ms
        self.max_buffer_size = max_buffer_size
        self.trace_expected = trace_expected
        self.collection_start = collection_start
        self.counter = 0
        self.dropped_samples = 0
        self.seen_result_ids: set[str] = set()

    def event_notification(self, event: Any) -> None:
        if len(self.local_buffer) >= self.max_buffer_size:
            self.dropped_samples += 1
            logger.warning(
                f"Worker buffer overflow on {self.endpoint} (capacity {self.max_buffer_size}). "
                f"Dropped {self.dropped_samples} sample(s)."
            )
            return

        t_received = datetime.now(UTC)
        publish_timing = current_publish_timing()
        self.counter += 1

        sample = extract_sample_from_event(
            event=event,
            client_received=t_received,
            sample_id=self.counter,
            endpoint=self.endpoint,
            clock_skew_ms=self.clock_skew_ms,
            trace_expected=self.trace_expected,
            t_collection_start=self.collection_start,
            clock_tolerance_ms=self.clock_tolerance_ms,
            clock_rtt_ms=self.clock_rtt_ms,
            bytes_received=publish_timing[0] if publish_timing else None,
            decoded=publish_timing[1] if publish_timing else None,
        )

        if sample.result_id:
            if sample.result_id in self.seen_result_ids:
                sample.integrity_status = INTEGRITY_DUPLICATE
                sample.integrity_reason = (
                    f"Duplicate ResultId '{sample.result_id}' received on endpoint {self.endpoint}"
                )
            else:
                self.seen_result_ids.add(sample.result_id)

        # Append to process-local buffer; flushed periodically by background coroutine
        self.local_buffer.append(sample.to_dict())

    def datachange_notification(self, node: Any, val: Any, data: Any) -> None:
        pass

    def status_change_notification(self, status: Any) -> None:
        pass


async def _worker_event_loop(
    worker_id: int,
    endpoints: list[str],
    out_queue: Any,
    stop_event: Any,
    connect_concurrency: int = 20,
    sub_period_ms: int = 100,
    mode: str = "passive",
    burst_trigger_count: int = 0,
    max_retries: int = 3,
    skip_clock_skew: bool = False,
    burst_delay: float = 1.0,
    clock_tolerance_ms: float = DEFAULT_CLOCK_TOLERANCE_MS,
    settle_timeout_s: float = DEFAULT_SETTLE_TIMEOUT_S,
) -> None:
    """The async task loop that runs inside each worker process."""
    patch_asyncua_subtype_serializer()
    hook_status = install_timing_hooks()
    loop_lag = LoopLagMonitor()
    loop_lag.start()

    clients: list[tuple[str, Client, Any]] = []
    method_clients: list[tuple[str, Client, Any, Any]] = []
    local_buffer: list[dict[str, Any]] = []
    handlers: list[_DurableWorkerSubHandler] = []
    connected_endpoints: list[str] = []
    failed_endpoints: dict[str, str] = {}
    namespace_metadata: dict[str, dict[str, str | None]] = {}
    burst_failures: int = 0
    burst_errors: list[str] = []
    teardown_errors: list[str] = []
    last_reported_drops: int = 0
    # Per-endpoint trigger-call counters; first_success_send_us is the client send time (epoch
    # microseconds) of the first call that succeeded, used by the master for UNMATCHED detection.
    call_stats: dict[str, dict[str, int]] = {}

    type_definitions_loaded = False
    loaded_ns_ijt: int | None = None
    type_definitions_lock = asyncio.Lock()
    connect_sem = asyncio.Semaphore(connect_concurrency)

    async def connect_and_subscribe(url: str) -> None:
        nonlocal type_definitions_loaded, loaded_ns_ijt
        last_err: Exception | None = None
        for attempt in range(1, max_retries + 1):
            if stop_event.is_set():
                return
            async with connect_sem:
                client = Client(url=url)
                apply_session_policy(client)
                sub: Any = None
                try:
                    await client.connect()

                    # Namespace resolution MUST be strict — do not guess ns=1
                    ns_ijt = await resolve_namespace_index(client, NS_IJT_BASE)
                    if ns_ijt is None:
                        raise RuntimeError(f"Server at {url} does not register required namespace {NS_IJT_BASE}")

                    # Every endpoint is checked under the lock: a task that waited for the first load
                    # must still compare its index (type registration is process-global).
                    async with type_definitions_lock:
                        if not type_definitions_loaded:
                            await load_ijt_type_definitions(client)
                            loaded_ns_ijt = ns_ijt
                            type_definitions_loaded = True
                        elif ns_ijt != loaded_ns_ijt:
                            raise RuntimeError(
                                f"Server at {url} registers {NS_IJT_BASE} at ns={ns_ijt}, but worker loaded type "
                                f"definitions for ns={loaded_ns_ijt}. Mixed namespace indexes within a single worker "
                                f"process are unsupported due to process-global OPC UA type registration."
                            )

                    ns_meta = await read_namespace_metadata(client, NS_IJT_BASE)

                    calibration = (
                        ClockCalibration()
                        if (skip_clock_skew or is_loopback_endpoint(url))
                        else await calibrate_clock_skew(client)
                    )
                    skew = calibration.skew_ms

                    trace_expected = mode in ("active_burst", "both")
                    collection_start = datetime.now(UTC)
                    event_node_id = ua.NodeId(JOINING_SYSTEM_RESULT_READY_EVENT_TYPE_ID, ns_ijt)  # type: ignore[arg-type]
                    handler = _DurableWorkerSubHandler(
                        endpoint=url,
                        local_buffer=local_buffer,
                        clock_skew_ms=skew,
                        trace_expected=trace_expected,
                        collection_start=collection_start,
                        clock_tolerance_ms=clock_tolerance_ms,
                        clock_rtt_ms=calibration.rtt_ms,
                    )
                    sub = await client.create_subscription(sub_period_ms, handler)
                    await sub.subscribe_events(client.nodes.server, client.get_node(event_node_id), queuesize=500)

                    handlers.append(handler)
                    clients.append((url, client, sub))
                    connected_endpoints.append(url)
                    namespace_metadata[url] = ns_meta
                    logger.debug(f"[Worker {worker_id}] Subscribed to {url} (skew={skew:.1f}ms)")
                    return
                except Exception as exc:
                    last_err = exc
                    if sub is not None:
                        try:
                            await sub.delete()
                        except Exception as del_exc:
                            logger.debug(
                                f"[Worker {worker_id}] Failed to delete partial subscription on {url}: {del_exc}"
                            )
                    await disconnect_client(client, settle_delay=0.05)
                    if attempt < max_retries:
                        backoff = min(2.0, 0.5 * (2 ** (attempt - 1)))
                        await asyncio.sleep(backoff)

        failed_endpoints[url] = str(last_err)
        logger.warning(f"[Worker {worker_id}] Exhausted {max_retries} retries connecting to {url}: {last_err}")

    # Launch all connection tasks
    tasks = [connect_and_subscribe(ep) for ep in endpoints]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for i, result in enumerate(results):
        if isinstance(result, BaseException):
            failed_endpoints[endpoints[i]] = f"Unhandled connection task error: {result}"
            logger.error(f"[Worker {worker_id}] Unhandled error connecting to {endpoints[i]}: {result}")

    # Report fleet connection status to master process
    out_queue.put(
        {
            "type": "FLEET_STATUS",
            "worker_id": worker_id,
            "connected": connected_endpoints,
            "failed": failed_endpoints,
            "namespace_metadata": namespace_metadata,
        }
    )

    # Background periodic batch flush task
    def endpoint_stats() -> dict[str, dict[str, int]]:
        """Cumulative per-endpoint counters; the master keeps the latest snapshot per endpoint."""
        stats: dict[str, dict[str, int]] = {h.endpoint: {"dropped": h.dropped_samples} for h in handlers}
        for url, counters in call_stats.items():
            stats.setdefault(url, {}).update(counters)
        return stats

    async def periodic_flush() -> None:
        nonlocal last_reported_drops
        while not stop_event.is_set():
            await asyncio.sleep(1.0)
            total_dropped = sum(h.dropped_samples for h in handlers)
            if local_buffer or total_dropped != last_reported_drops:
                # Drain local buffer atomically
                batch = local_buffer[:]
                del local_buffer[: len(batch)]
                out_queue.put(
                    {
                        "type": "BATCH",
                        "worker_id": worker_id,
                        "samples": batch,
                        "dropped_samples": total_dropped,
                        "endpoint_stats": endpoint_stats(),
                    }
                )
                last_reported_drops = total_dropped

    flush_task = asyncio.create_task(periodic_flush())

    # Setup dedicated method clients for active burst mode
    if mode in ("active_burst", "both") and burst_trigger_count > 0:
        cached_sim_nodeid: Any = None
        cached_meth_nodeid: Any = None
        cached_ns_app: int | None = None
        cache_lock = asyncio.Lock()
        discovery_lock = asyncio.Lock()

        async def _validate_candidate_nodes(
            cli: Client,
            sim_id: Any,
            meth_id: Any,
            ns: int,
        ) -> tuple[Any | None, Any | None]:
            """Validate candidate simulation object and method nodes on a server connection.

            Confirms:
            1. Simulation object has ua.NodeClass.Object and BrowseName BN_SIMULATE_RESULTS
            2. Method node has ua.NodeClass.Method and BrowseName BN_SIMULATE_SINGLE_RESULT
            3. Method node is a verified child of the simulation object
            """
            try:
                cand_sim = cli.get_node(sim_id)
                cand_meth = cli.get_node(meth_id)
                sim_cls = await cand_sim.read_node_class()
                sim_bn = await cand_sim.read_browse_name()
                meth_cls = await cand_meth.read_node_class()
                meth_bn = await cand_meth.read_browse_name()
                if (
                    sim_cls == ua.NodeClass.Object
                    and getattr(sim_bn, "Name", None) == BN_SIMULATE_RESULTS
                    and meth_cls == ua.NodeClass.Method
                    and getattr(meth_bn, "Name", None) == BN_SIMULATE_SINGLE_RESULT
                ):
                    child_meth = await _find_child(cand_sim, ns, BN_SIMULATE_SINGLE_RESULT)
                    if child_meth is not None and getattr(child_meth, "nodeid", None) == meth_id:
                        return cand_sim, cand_meth
            except Exception as verify_exc:
                logger.debug(
                    f"[Worker {worker_id}] Candidate method verification failed on {cli.server_url}: {verify_exc}"
                )
            return None, None

        async def setup_method_client(url: str) -> None:
            nonlocal burst_failures, cached_sim_nodeid, cached_meth_nodeid, cached_ns_app
            m_cli: Client | None = None
            try:
                async with connect_sem:
                    m_cli = Client(url=url)
                    apply_session_policy(m_cli)
                    await m_cli.connect()
                    ns_app = await resolve_namespace_index(m_cli, NS_APP)
                    if ns_app is None:
                        raise RuntimeError(f"Namespace {NS_APP} not found on {url}")

                    sim_res = None
                    meth_node = None

                    # 1. Fast path: check cached candidate nodes
                    cand_sim_id = None
                    cand_meth_id = None
                    async with cache_lock:
                        if cached_sim_nodeid is not None and cached_meth_nodeid is not None and cached_ns_app == ns_app:
                            cand_sim_id = cached_sim_nodeid
                            cand_meth_id = cached_meth_nodeid

                    if cand_sim_id is not None and cand_meth_id is not None:
                        sim_res, meth_node = await _validate_candidate_nodes(m_cli, cand_sim_id, cand_meth_id, ns_app)

                    # 2. Slow path: serialize discovery across endpoints to prevent redundant browsing
                    if sim_res is None or meth_node is None:
                        async with discovery_lock:
                            # Re-check cache under discovery lock in case another endpoint just populated it
                            cand_sim_id = None
                            cand_meth_id = None
                            async with cache_lock:
                                if (
                                    cached_sim_nodeid is not None
                                    and cached_meth_nodeid is not None
                                    and cached_ns_app == ns_app
                                ):
                                    cand_sim_id = cached_sim_nodeid
                                    cand_meth_id = cached_meth_nodeid

                            if cand_sim_id is not None and cand_meth_id is not None:
                                sim_res, meth_node = await _validate_candidate_nodes(
                                    m_cli, cand_sim_id, cand_meth_id, ns_app
                                )

                            if sim_res is None or meth_node is None:
                                sim_res, meth_node = await _locate_simulate_method(m_cli, ns_app)
                                if sim_res is not None and meth_node is not None:
                                    async with cache_lock:
                                        cached_sim_nodeid = sim_res.nodeid
                                        cached_meth_nodeid = meth_node.nodeid
                                        cached_ns_app = ns_app

                    if sim_res is None or meth_node is None:
                        raise RuntimeError("SimulateSingleResult method not found")
                    method_clients.append((url, m_cli, sim_res, meth_node))
            except Exception as exc:
                burst_failures += 1
                burst_errors.append(f"{url}: method trigger setup failed: {exc}")
                logger.error(f"[Worker {worker_id}] {burst_errors[-1]}")
                if m_cli is not None:
                    try:
                        await disconnect_client(m_cli, settle_delay=0.01)
                    except Exception as disconnect_exc:
                        teardown_errors.append(f"Method client disconnect on {url}: {disconnect_exc}")

        # Setup method clients concurrently across all connected endpoints
        await asyncio.gather(*(setup_method_client(url) for url, _, _ in clients), return_exceptions=True)

        # Execute concurrent burst rounds across all tools simultaneously
        for burst_idx in range(burst_trigger_count):
            if stop_event.is_set():
                break

            async def fire_one(url: str, sim_node: Any, meth_id: Any) -> None:
                nonlocal burst_failures
                counters = call_stats.setdefault(url, {"calls_attempted": 0, "calls_succeeded": 0, "calls_failed": 0})
                counters["calls_attempted"] += 1
                sent_us = int(datetime.now(UTC).timestamp() * 1_000_000)
                try:
                    await sim_node.call_method(
                        meth_id.nodeid,
                        ua.Variant(2, ua.VariantType.UInt32),  # MULTI_STEP_OK_RESULT
                        ua.Variant(True, ua.VariantType.Boolean),  # Traces
                    )
                    counters["calls_succeeded"] += 1
                    counters.setdefault("first_success_send_us", sent_us)
                except Exception as exc:
                    counters["calls_failed"] += 1
                    burst_failures += 1
                    burst_errors.append(f"{url}: burst call failed: {exc}")
                    logger.error(f"[Worker {worker_id}] {burst_errors[-1]}")

            # Simultaneous execution via asyncio.gather
            burst_calls = [fire_one(url, sim_node, meth_id) for url, _, sim_node, meth_id in method_clients]
            if burst_calls:
                call_results = await asyncio.gather(*burst_calls, return_exceptions=True)
                for (url, _, _, _), result in zip(method_clients, call_results):
                    if isinstance(result, BaseException):
                        burst_failures += 1
                        burst_errors.append(f"{url}: unhandled burst task error: {result}")
                        logger.error(f"[Worker {worker_id}] {burst_errors[-1]}")
            if burst_delay > 0:
                await asyncio.sleep(burst_delay)

    # Listen until stop signal is set
    while not stop_event.is_set():
        await asyncio.sleep(0.1)

    # Settle: give results of successful calls a bounded time to arrive before the final flush.
    # The master performs the exact VALID-based correlation; this only avoids cutting off late events.
    if call_stats:
        received = {h.endpoint: h for h in handlers}
        settle_deadline = time.monotonic() + settle_timeout_s
        while time.monotonic() < settle_deadline and any(
            (received[url].counter if url in received else 0) < c.get("calls_succeeded", 0)
            for url, c in call_stats.items()
        ):
            await asyncio.sleep(0.05)

    # Cancel periodic flush task
    flush_task.cancel()
    try:
        await flush_task
    except asyncio.CancelledError:
        pass

    # Final flush of all remaining buffered samples
    if local_buffer:
        batch = local_buffer[:]
        del local_buffer[: len(batch)]
        out_queue.put(
            {
                "type": "BATCH",
                "worker_id": worker_id,
                "samples": batch,
                "dropped_samples": sum(h.dropped_samples for h in handlers),
                "endpoint_stats": endpoint_stats(),
            }
        )

    # Clean teardown: delete subscriptions explicitly, then disconnect clients in parallel
    async def _teardown_method_client(m_cli: Any) -> None:
        try:
            await disconnect_client(m_cli, settle_delay=0.01)
        except Exception as exc:
            teardown_errors.append(f"Method client disconnect: {exc}")

    async def _teardown_subscription_client(url: str, client: Any, sub: Any) -> None:
        if sub is not None:
            try:
                await sub.delete()
            except Exception as exc:
                err_msg = f"Subscription deletion on {url} error: {exc}"
                logger.warning(f"[Worker {worker_id}] {err_msg}")
                teardown_errors.append(err_msg)
        try:
            await disconnect_client(client, settle_delay=0.01)
        except Exception as exc:
            err_msg = f"Client disconnect on {url} error: {exc}"
            logger.warning(f"[Worker {worker_id}] {err_msg}")
            teardown_errors.append(err_msg)

    teardown_tasks = [_teardown_method_client(m_cli) for _, m_cli, _, _ in method_clients] + [
        _teardown_subscription_client(url, client, sub) for url, client, sub in clients
    ]
    if teardown_tasks:
        try:
            await asyncio.wait_for(asyncio.gather(*teardown_tasks, return_exceptions=True), timeout=5.0)
        except TimeoutError:
            teardown_errors.append(f"[Worker {worker_id}] Parallel teardown timed out after 5.0s")

    # Signal completion to master process
    loop_lag.stop()
    total_dropped = sum(h.dropped_samples for h in handlers)
    out_queue.put(
        {
            "type": "DONE",
            "worker_id": worker_id,
            "connected_count": len(connected_endpoints),
            "dropped_samples": total_dropped,
            "endpoint_stats": endpoint_stats(),
            "burst_failures": burst_failures,
            "burst_errors": burst_errors,
            "teardown_errors": teardown_errors,
            "timing": {
                "hooks_installed": hook_status.installed,
                "hooks_reason": hook_status.reason,
                "loop_lag": loop_lag.snapshot(),
            },
        }
    )


def _worker_process_entry(
    worker_id: int,
    endpoints: list[str],
    out_queue: Any,
    stop_event: Any,
    connect_concurrency: int,
    sub_period_ms: int,
    mode: str,
    burst_trigger_count: int,
    skip_clock_skew: bool = False,
    burst_delay: float = 1.0,
    verbose: bool = False,
    clock_tolerance_ms: float = DEFAULT_CLOCK_TOLERANCE_MS,
    settle_timeout_s: float = DEFAULT_SETTLE_TIMEOUT_S,
) -> None:
    """The entry point for each background worker process."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] [Worker %(process)d] %(message)s",
    )
    if verbose:
        logging.getLogger("asyncua").setLevel(logging.DEBUG)
    else:
        logging.getLogger("asyncua").setLevel(logging.CRITICAL)
    try:
        asyncio.run(
            _worker_event_loop(
                worker_id=worker_id,
                endpoints=endpoints,
                out_queue=out_queue,
                stop_event=stop_event,
                connect_concurrency=connect_concurrency,
                sub_period_ms=sub_period_ms,
                mode=mode,
                burst_trigger_count=burst_trigger_count,
                skip_clock_skew=skip_clock_skew,
                burst_delay=burst_delay,
                clock_tolerance_ms=clock_tolerance_ms,
                settle_timeout_s=settle_timeout_s,
            )
        )
    except Exception as exc:
        try:
            out_queue.put(
                {
                    "type": "ERROR",
                    "worker_id": worker_id,
                    "error": str(exc),
                }
            )
        except Exception:
            pass


class OpcUaClientPool:
    """Process-sharded OPC UA multi-endpoint pool for controlled performance validation."""

    def __init__(
        self,
        endpoints: list[str],
        max_workers: int | None = None,
        connect_concurrency: int = 20,
        sub_period_ms: int = 100,
        mode: str = "passive",
        require_full_coverage: bool | None = None,
        skip_clock_skew: bool = False,
        burst_delay: float = 1.0,
        verbose: bool = False,
        clock_tolerance_ms: float = DEFAULT_CLOCK_TOLERANCE_MS,
        settle_timeout_s: float = DEFAULT_SETTLE_TIMEOUT_S,
    ) -> None:
        self.endpoints = endpoints
        if max_workers is not None:
            if not isinstance(max_workers, int) or max_workers < 1 or max_workers > MAX_SAFE_WORKER_PROCESSES:
                raise ValueError(
                    f"max_workers must be an integer between 1 and {MAX_SAFE_WORKER_PROCESSES}, got {max_workers}"
                )
            self.max_workers = max_workers
        else:
            cpu_cnt = os.cpu_count() or 4
            target_workers = max(
                len(endpoints) if len(endpoints) <= DEFAULT_MAX_WORKERS else DEFAULT_MAX_WORKERS,
                (len(endpoints) + 19) // 20,
            )
            self.max_workers = min(target_workers, min(cpu_cnt, MAX_SAFE_WORKER_PROCESSES))
        self.connect_concurrency = connect_concurrency
        self.sub_period_ms = sub_period_ms
        self.mode = mode
        self.require_full_coverage = len(endpoints) > 1 if require_full_coverage is None else require_full_coverage
        self.skip_clock_skew = skip_clock_skew
        if not math.isfinite(burst_delay) or burst_delay < 0:
            raise ValueError(f"burst_delay must be a finite non-negative number, got {burst_delay}")
        self.burst_delay = burst_delay
        if not math.isfinite(clock_tolerance_ms) or clock_tolerance_ms < 0:
            raise ValueError(f"clock_tolerance_ms must be a finite non-negative number, got {clock_tolerance_ms}")
        self.clock_tolerance_ms = clock_tolerance_ms
        if not math.isfinite(settle_timeout_s) or settle_timeout_s < 0:
            raise ValueError(f"settle_timeout_s must be a finite non-negative number, got {settle_timeout_s}")
        self.settle_timeout_s = settle_timeout_s
        self.verbose = verbose

        self._ctx = mp.get_context("spawn")
        self._out_queue: Any = None
        self._stop_event: Any = None
        self._processes: list[Any] = []
        self._num_workers_started = 0
        self._stopped = False

        # Fleet coverage and samples tracking
        self.collected_samples: list[LatencySample] = []
        self.connected_endpoints: set[str] = set()
        self.failed_endpoints: dict[str, str] = {}
        self.worker_errors: list[str] = []
        self.completed_worker_ids: set[int] = set()
        self.total_dropped_samples: int = 0
        self._dropped_by_worker: dict[int, int] = {}
        self.endpoint_stats: dict[str, dict[str, int]] = {}
        self.burst_trigger_failures: int = 0
        self.burst_trigger_errors: list[str] = []
        self.teardown_errors: list[str] = []
        self.fleet_integrity: FleetIntegritySummary | None = None
        self.worker_timing: dict[int, dict[str, Any]] = {}
        self.namespace_metadata: dict[str, dict[str, str | None]] = {}

    def start(self, burst_trigger_count: int = 0) -> None:
        """Start all worker processes and begin connecting to controllers."""
        if not self.endpoints:
            raise ValueError("No endpoints provided to OpcUaClientPool")

        self._out_queue = self._ctx.Queue()
        self._stop_event = self._ctx.Event()
        self.collected_samples.clear()
        self.connected_endpoints.clear()
        self.failed_endpoints.clear()
        self.worker_errors.clear()
        self.completed_worker_ids.clear()
        self.total_dropped_samples = 0
        self._dropped_by_worker.clear()
        self.endpoint_stats.clear()
        self.burst_trigger_failures = 0
        self.burst_trigger_errors.clear()
        self.teardown_errors.clear()
        self.fleet_integrity = None
        self.worker_timing.clear()
        self.namespace_metadata.clear()
        self._stopped = False

        # Split endpoints evenly across worker processes
        num_workers = min(self.max_workers, len(self.endpoints))
        shards: list[list[str]] = [[] for _ in range(num_workers)]
        for idx, ep in enumerate(self.endpoints):
            shards[idx % num_workers].append(ep)

        self._num_workers_started = sum(1 for s in shards if s)
        logger.info(
            f"Starting OpcUaClientPool with {len(self.endpoints)} endpoints across {self._num_workers_started} processes"
        )

        # Partition connection concurrency across workers to prevent fleet-wide connection storms
        worker_connect_concurrency = max(1, self.connect_concurrency // max(1, self._num_workers_started))

        for w_id, ep_shard in enumerate(shards):
            if not ep_shard:
                continue
            proc = self._ctx.Process(
                target=_worker_process_entry,
                args=(
                    w_id,
                    ep_shard,
                    self._out_queue,
                    self._stop_event,
                    worker_connect_concurrency,
                    self.sub_period_ms,
                    self.mode,
                    burst_trigger_count,
                    self.skip_clock_skew,
                    self.burst_delay,
                    self.verbose,
                    self.clock_tolerance_ms,
                    self.settle_timeout_s,
                ),
                daemon=True,
            )
            proc.start()
            self._processes.append(proc)

    def timing_summary(self) -> dict[str, Any]:
        """Wire-timing hook status and worst event-loop lag across workers that reported DONE."""
        reasons = sorted(
            {str(t.get("hooks_reason", "")) for t in self.worker_timing.values() if not t.get("hooks_installed")}
        )
        lags = [t["loop_lag"] for t in self.worker_timing.values() if isinstance(t.get("loop_lag"), dict)]
        return {
            "workers_reported": len(self.worker_timing),
            "workers_without_hooks": sum(1 for t in self.worker_timing.values() if not t.get("hooks_installed")),
            "hook_failure_reasons": reasons,
            "loop_lag_max_ms": max((float(lag.get("max_ms", 0.0)) for lag in lags), default=0.0),
            "loop_lag_worst_mean_ms": max((float(lag.get("mean_ms", 0.0)) for lag in lags), default=0.0),
        }

    def _process_queue_msg(self, msg: dict[str, Any]) -> None:
        """Internal helper to process IPC messages from workers."""
        msg_type = msg.get("type")
        if msg_type in ("BATCH", "DONE") and "dropped_samples" in msg:
            worker_id = msg.get("worker_id")
            dropped = msg["dropped_samples"]
            if isinstance(worker_id, int) and isinstance(dropped, int) and dropped >= 0:
                self._dropped_by_worker[worker_id] = max(self._dropped_by_worker.get(worker_id, 0), dropped)
                self.total_dropped_samples = sum(self._dropped_by_worker.values())
        if msg_type in ("BATCH", "DONE"):
            raw_stats = msg.get("endpoint_stats")
            if isinstance(raw_stats, dict):
                for ep, counters in raw_stats.items():
                    if not isinstance(ep, str) or not isinstance(counters, dict):
                        continue
                    current = self.endpoint_stats.setdefault(ep, {})
                    for key, value in counters.items():
                        # Counters are cumulative per worker; keep the highest snapshot seen.
                        if isinstance(key, str) and isinstance(value, int) and value >= 0:
                            current[key] = max(current.get(key, 0), value)
        if msg_type == "BATCH":
            for raw in msg.get("samples", []):
                self.collected_samples.append(LatencySample.from_dict(raw))
        elif msg_type == "FLEET_STATUS":
            self.connected_endpoints.update(msg.get("connected", []))
            self.failed_endpoints.update(msg.get("failed", {}))
            raw_meta = msg.get("namespace_metadata")
            if isinstance(raw_meta, dict):
                for ep, meta in raw_meta.items():
                    if isinstance(ep, str) and isinstance(meta, dict):
                        self.namespace_metadata[ep] = {
                            k: (v if isinstance(v, str) else None) for k, v in meta.items() if k in _NS_META_KEYS
                        }
        elif msg_type == "ERROR":
            err = f"Worker {msg.get('worker_id')} error: {msg.get('error')}"
            self.worker_errors.append(err)
            logger.error(err)
        elif msg_type == "DONE":
            w_id = msg.get("worker_id")
            if w_id is not None:
                self.completed_worker_ids.add(w_id)
            self.burst_trigger_failures += msg.get("burst_failures", 0)
            self.burst_trigger_errors.extend(msg.get("burst_errors", []))
            self.teardown_errors.extend(msg.get("teardown_errors", []))
            timing = msg.get("timing")
            if isinstance(w_id, int) and isinstance(timing, dict):
                self.worker_timing[w_id] = timing

    def collect_samples(
        self,
        duration_seconds: float = 10.0,
        target_sample_count: int | None = None,
    ) -> list[LatencySample]:
        """Collect incoming LatencySamples from worker processes via IPC queue.
        Enforces explicit FLEET_STATUS tracking, BATCH handling, and coverage checks.
        """
        if not math.isfinite(duration_seconds) or duration_seconds <= 0:
            raise ValueError(f"duration_seconds must be a finite positive number, got {duration_seconds}")
        start_t = time.monotonic()

        while True:
            elapsed = time.monotonic() - start_t
            if elapsed >= duration_seconds:
                break
            if target_sample_count and len(self.collected_samples) >= target_sample_count:
                break

            try:
                msg = self._out_queue.get(timeout=0.1)
                self._process_queue_msg(msg)
            except queue.Empty:
                continue
            except (OSError, ValueError, EOFError) as exc:
                raise RuntimeError("Worker result queue closed during collection") from exc

        return list(self.collected_samples)

    def stop(self, drain_timeout_s: float | None = None) -> list[LatencySample]:
        """Signal workers to stop, drain final batch and DONE messages, inspect exitcodes, and cleanly close queues.

        The default drain window covers the worker settle time plus teardown, so workers that are
        still waiting for results of successful calls are not terminated early.
        """
        if self._stopped:
            return list(self.collected_samples)
        if drain_timeout_s is None:
            drain_timeout_s = self.settle_timeout_s + _WORKER_SHUTDOWN_BUDGET_S

        if self._stop_event:
            self._stop_event.set()

        # Phase 1: Drain queue messages while processes shut down
        drain_start = time.monotonic()
        while time.monotonic() - drain_start < drain_timeout_s:
            try:
                msg = self._out_queue.get(timeout=0.05)
                self._process_queue_msg(msg)
            except queue.Empty:
                if all(not p.is_alive() for p in self._processes):
                    break
            except (OSError, ValueError, EOFError) as exc:
                self.worker_errors.append(f"Worker result queue closed during shutdown: {exc}")
                break

        # Phase 2: Check process termination, forced kills, and exit codes
        for w_id, proc in enumerate(self._processes):
            proc.join(timeout=1.0)
            if proc.is_alive():
                self.worker_errors.append(f"Worker {w_id} did not exit within timeout; forcefully terminated.")
                proc.terminate()
                proc.join(timeout=0.5)
            elif proc.exitcode is not None and proc.exitcode != 0:
                self.worker_errors.append(f"Worker {w_id} crashed with exitcode {proc.exitcode}.")

        # Phase 3: Final drain of any in-flight messages flushed just before exit
        if self._out_queue:
            drained_count = 0
            while drained_count < 100000:
                try:
                    msg = self._out_queue.get_nowait()
                    self._process_queue_msg(msg)
                    drained_count += 1
                except queue.Empty:
                    break
                except (OSError, ValueError, EOFError) as exc:
                    self.worker_errors.append(f"Worker result queue closed during final drain: {exc}")
                    break

        # Phase 4: Clean queue feeder thread cleanup
        if self._out_queue is not None:
            try:
                self._out_queue.close()
                self._out_queue.join_thread()
            except Exception as q_exc:
                logger.debug(f"Queue cleanup notice: {q_exc}")

        self._processes.clear()
        self._stopped = True
        return list(self.collected_samples)

    def verify_coverage(
        self,
        samples: list[LatencySample] | None = None,
        target_sample_count: int | None = None,
        target_samples_per_endpoint: int | None = None,
        allow_partial_samples: bool = False,
    ) -> tuple[bool, str]:
        """Verify run health, coverage, sample counts, and result integrity.

        Always builds ``self.fleet_integrity`` (also on early run failures) so reports never
        fall back to optimistic defaults. ``fleet_integrity.passed`` equals the returned verdict.

        ``allow_partial_samples`` relaxes only count checks (total target and per-endpoint
        quota). Invalid results (INCOMPLETE, DUPLICATE, UNMATCHED) always fail the gate.
        ``require_full_coverage`` controls endpoint coverage, dropped samples, and
        active-trigger failures.

        Call/result correlation (per endpoint, never relaxed):
        - ``active_burst``: VALID results received before the first successful call was sent are
          marked UNMATCHED; VALID results must then equal successful calls.
        - ``both``: fewer VALID results than successful calls fails; extra results are reported as
          external events.
        - ``passive``: no correlation.

        Returns (is_valid, summary_message).
        """
        active_samples = self.collected_samples if samples is None else samples
        total_endpoints = len(self.endpoints)
        connected_count = len(self.connected_endpoints)
        failed_count = len(self.failed_endpoints)

        sampled_endpoints = {s.endpoint for s in active_samples}
        missing_sample_endpoints = set(self.endpoints) - sampled_endpoints

        msg = (
            f"Fleet Coverage: {len(sampled_endpoints)}/{total_endpoints} endpoints produced samples "
            f"({connected_count} connected, {failed_count} connection failures)."
        )

        if self.mode == "active_burst":
            self._mark_unmatched_before_first_call(active_samples)

        min_required_per_ep = 0
        if target_samples_per_endpoint is not None and target_samples_per_endpoint > 0:
            min_required_per_ep = target_samples_per_endpoint
        elif (
            self.require_full_coverage
            and target_sample_count is not None
            and target_sample_count > 0
            and total_endpoints > 0
            and (target_sample_count % total_endpoints == 0)
        ):
            min_required_per_ep = target_sample_count // total_endpoints

        # Result-level integrity (validity, duplicates, stale events, drops). Quotas are handled below.
        fi = evaluate_fleet_integrity(
            samples=active_samples,
            endpoints=self.endpoints,
            min_valid_per_endpoint=0,
            dropped_samples=self.total_dropped_samples,
            dropped_by_endpoint={ep: c.get("dropped", 0) for ep, c in self.endpoint_stats.items()},
        )
        self.fleet_integrity = fi

        failures: list[str] = []
        warnings: list[str] = []

        # 1. All started workers must confirm clean shutdown with DONE
        missing_done = set(range(self._num_workers_started)) - self.completed_worker_ids
        if missing_done:
            failures.append(f"Worker completion failure: workers {sorted(missing_done)} did not confirm clean shutdown")

        # 2. Worker crashes, uncaught exceptions, or teardown errors
        worker_failures = [*self.worker_errors, *self.teardown_errors]
        if worker_failures:
            failures.append(f"Worker process failures detected: {'; '.join(worker_failures)}")

        # 3. Connection failures
        if failed_count > 0:
            err_details = "; ".join(f"{ep}: {err}" for ep, err in list(self.failed_endpoints.items())[:3])
            failures.append(f"Connection failures on {failed_count} endpoints ({err_details})")

        # 4. Dropped samples
        if self.total_dropped_samples > 0:
            if self.require_full_coverage:
                failures.append(f"Client buffer full: dropped {self.total_dropped_samples} samples")
            else:
                warnings.append(
                    f"Warning: {self.total_dropped_samples} samples dropped because the client buffer was full"
                )

        # 5. Active trigger failures
        if self.burst_trigger_failures > 0 and self.mode in ("active_burst", "both"):
            details = "; ".join(self.burst_trigger_errors[:3])
            if self.require_full_coverage:
                failures.append(
                    f"Active burst trigger failure: {self.burst_trigger_failures} setup/call failures ({details})"
                )
            else:
                warnings.append(f"Warning: {self.burst_trigger_failures} active trigger failures: {details}")

        # 6. Endpoint coverage
        if self.require_full_coverage and missing_sample_endpoints:
            failures.append(f"Incomplete coverage: {len(missing_sample_endpoints)} endpoints produced zero samples")

        # 7. Total sample target (count check: relaxed by allow_partial_samples)
        if target_sample_count is not None and target_sample_count > 0:
            actual_count = len(active_samples)
            if actual_count < target_sample_count:
                shortfall = target_sample_count - actual_count
                pct = (actual_count / target_sample_count) * 100.0
                if allow_partial_samples:
                    warnings.append(
                        f"Warning: sample target shortfall: {actual_count}/{target_sample_count}, {pct:.1f}%"
                    )
                else:
                    failures.append(
                        f"Sample target shortfall: collected {actual_count}/{target_sample_count} "
                        f"samples ({pct:.1f}%). {shortfall} samples short of target"
                    )

        # 8. Per-endpoint VALID quota (count check: relaxed by allow_partial_samples)
        if min_required_per_ep > 0:
            under_sampled = {
                ep: entry.valid_count for ep, entry in fi.endpoints.items() if entry.valid_count < min_required_per_ep
            }
            if under_sampled:
                details = "; ".join(f"{ep}: {cnt}/{min_required_per_ep}" for ep, cnt in list(under_sampled.items())[:3])
                if allow_partial_samples:
                    warnings.append(f"Warning: per-endpoint sample shortfall: {details}")
                else:
                    failures.append(
                        f"Per-endpoint sample shortfall: {len(under_sampled)} endpoints produced fewer than "
                        f"{min_required_per_ep} valid samples ({details})"
                    )

        # 9. Call/result correlation (never relaxed)
        if self.mode in ("active_burst", "both"):
            failures.extend(self._correlate_calls(fi))

        # 10. IJT namespace model consistency (never relaxed)
        ns_failure, unverified = self._check_namespace_metadata(fi)
        if ns_failure:
            failures.append(ns_failure)
        if unverified:
            warnings.append(
                f"IJT namespace version unverified on {len(unverified)} endpoint(s) "
                f"(server does not expose NamespaceVersion/NamespacePublicationDate)"
            )

        # 11. Result validity (never relaxed)
        if fi.failure_reasons:
            failures.append(f"Benchmark Integrity Gate failed: {'; '.join(fi.failure_reasons)}")

        # Single source of truth: the integrity summary carries every run-level failure too.
        for reason in failures:
            if reason not in fi.failure_reasons:
                fi.failure_reasons.append(reason)
        fi.passed = not failures

        if fi.total_clock_warnings > 0:
            warnings.append(
                f"Clock health warning: {fi.total_clock_warnings} events appear older than collection start "
                f"beyond the clock tolerance; check server/client time synchronization"
            )

        timing = self.timing_summary()
        if timing["workers_without_hooks"]:
            warnings.append(
                f"Wire timing unavailable in {timing['workers_without_hooks']} worker(s) "
                f"({'; '.join(timing['hook_failure_reasons'])}); delivery metrics use handler-entry time"
            )

        if fi.total_external_events > 0:
            warnings.append(
                f"{fi.total_external_events} external event(s): VALID results beyond successful trigger calls"
            )

        if warnings:
            msg += " (" + "; ".join(warnings) + ")"
        if failures:
            return False, f"{failures[0]}. {msg}" + (
                f" (+{len(failures) - 1} more failure(s): {' | '.join(failures[1:])})" if len(failures) > 1 else ""
            )
        return True, msg

    def _mark_unmatched_before_first_call(self, samples: list[LatencySample]) -> None:
        """In ``active_burst`` mode, mark VALID results that cannot belong to a successful call.

        A result is UNMATCHED when its endpoint had no successful trigger call, or when the client
        received it before the first successful call was sent (same client clock, no skew involved).
        """
        for s in samples:
            if s.integrity_status != INTEGRITY_VALID:
                continue
            first_us = self.endpoint_stats.get(s.endpoint, {}).get("first_success_send_us")
            if first_us is None:
                s.integrity_status = INTEGRITY_UNMATCHED
                s.integrity_reason = "Result received but no trigger call succeeded on this endpoint"
            elif s.client_received_time is not None and s.client_received_time.timestamp() * 1_000_000 < first_us:
                s.integrity_status = INTEGRITY_UNMATCHED
                s.integrity_reason = "Result received before the first successful trigger call was sent"

    def _correlate_calls(self, fi: FleetIntegritySummary) -> list[str]:
        """Copy call counters into ``fi`` and return correlation failures (see ``verify_coverage``)."""
        shortfall: list[str] = []
        surplus: list[str] = []
        for ep in self.endpoints:
            entry = fi.endpoints.setdefault(ep, EndpointIntegrity(endpoint=ep))
            stats = self.endpoint_stats.get(ep, {})
            entry.calls_attempted = stats.get("calls_attempted", 0)
            entry.calls_succeeded = stats.get("calls_succeeded", 0)
            entry.calls_failed = stats.get("calls_failed", 0)
            fi.total_calls_attempted += entry.calls_attempted
            fi.total_calls_succeeded += entry.calls_succeeded
            fi.total_calls_failed += entry.calls_failed
            diff = entry.valid_count - entry.calls_succeeded
            if diff < 0:
                shortfall.append(f"{ep}: {entry.valid_count}/{entry.calls_succeeded}")
            elif diff > 0 and self.mode == "active_burst":
                surplus.append(f"{ep}: {entry.valid_count}/{entry.calls_succeeded}")
            elif diff > 0:
                entry.external_event_count = diff
                fi.total_external_events += diff

        failures = []
        if shortfall:
            failures.append(
                f"Call/result correlation failure: {len(shortfall)} endpoint(s) produced fewer VALID results "
                f"than successful trigger calls (VALID/succeeded: {'; '.join(shortfall[:3])})"
            )
        if surplus:
            failures.append(
                f"Call/result correlation failure: {len(surplus)} endpoint(s) produced more VALID results "
                f"than successful trigger calls (VALID/succeeded: {'; '.join(surplus[:3])})"
            )
        return failures

    def _check_namespace_metadata(self, fi: FleetIntegritySummary) -> tuple[str | None, list[str]]:
        """Compare IJT NamespaceVersion/PublicationDate across connected endpoints.

        Returns (failure message or None, endpoints exposing neither value). Each value is compared
        only among endpoints that expose it.
        """
        unverified: list[str] = []
        distinct: dict[str, dict[str, list[str]]] = {key: {} for key in _NS_META_KEYS}
        for ep in sorted(self.namespace_metadata):
            meta = self.namespace_metadata[ep]
            entry = fi.endpoints.setdefault(ep, EndpointIntegrity(endpoint=ep))
            entry.ijt_namespace_version = meta.get("version")
            entry.ijt_namespace_publication_date = meta.get("publication_date")
            if not any(meta.get(key) for key in _NS_META_KEYS):
                unverified.append(ep)
            for key in _NS_META_KEYS:
                value = meta.get(key)
                if value:
                    distinct[key].setdefault(value, []).append(ep)
        mismatches = [
            f"{key}: " + ", ".join(f"{value} ({len(eps)} endpoint(s), e.g. {eps[0]})" for value, eps in values.items())
            for key, values in distinct.items()
            if len(values) > 1
        ]
        if mismatches:
            return f"IJT namespace model mismatch across endpoints ({'; '.join(mismatches)})", unverified
        return None, unverified
