"""
High-Performance Process-Sharded OPC UA Client Pool.

Controlled-validation concurrency architecture targeting 1 to 500+ industrial controllers:
1. Multi-Process Sharding:
   Endpoints are distributed evenly across up to 4 worker processes by default.
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
import multiprocessing as mp
import queue
import time
from datetime import UTC, datetime
from typing import Any

from asyncua import Client, ua

from .namespaces import (
    BN_SIMULATE_RESULTS,
    BN_SIMULATE_SINGLE_RESULT,
    JOINING_SYSTEM_RESULT_READY_EVENT_TYPE_ID,
    NS_APP,
    NS_IJT_BASE,
    resolve_namespace_index,
)
from .result_transfer_latency import LatencySample, calibrate_clock_skew, extract_sample_from_event
from .session_policy import (
    apply_session_policy,
    disconnect_client,
    load_ijt_type_definitions,
    patch_asyncua_subtype_serializer,
)

logger = logging.getLogger(__name__)

# Bounded process sizing: 4 workers default is plenty for 500 endpoints (125 sockets/worker)
DEFAULT_MAX_WORKERS: int = 4
MAX_SAFE_WORKER_PROCESSES: int = 32
MAX_WORKER_BUFFER_SIZE: int = 5000


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
    ) -> None:
        self.endpoint = endpoint
        self.local_buffer = local_buffer
        self.clock_skew_ms = clock_skew_ms
        self.max_buffer_size = max_buffer_size
        self.counter = 0
        self.dropped_samples = 0

    def event_notification(self, event: Any) -> None:
        if len(self.local_buffer) >= self.max_buffer_size:
            self.dropped_samples += 1
            logger.warning(
                f"Worker buffer overflow on {self.endpoint} (capacity {self.max_buffer_size}). "
                f"Dropped {self.dropped_samples} sample(s)."
            )
            return

        t_received = datetime.now(UTC)
        self.counter += 1

        sample = extract_sample_from_event(
            event=event,
            client_received=t_received,
            sample_id=self.counter,
            endpoint=self.endpoint,
            clock_skew_ms=self.clock_skew_ms,
        )

        # Append to process-local buffer; flushed periodically by background coroutine
        self.local_buffer.append(
            {
                "sample_id": sample.sample_id,
                "endpoint": sample.endpoint,
                "start_time": sample.start_time.isoformat() if sample.start_time else None,
                "end_time": sample.end_time.isoformat() if sample.end_time else None,
                "creation_time": sample.creation_time.isoformat() if sample.creation_time else None,
                "event_time": sample.event_time.isoformat() if sample.event_time else None,
                "client_received_time": sample.client_received_time.isoformat()
                if sample.client_received_time
                else None,
                "clock_skew_ms": sample.clock_skew_ms,
                "joining_duration_ms": sample.joining_duration_ms,
                "server_processing_time_ms": sample.server_processing_time_ms,
                "network_transport_time_ms": sample.network_transport_time_ms,
                "total_result_transfer_time_ms": sample.total_result_transfer_time_ms,
            }
        )

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
) -> None:
    """The async task loop that runs inside each worker process."""
    patch_asyncua_subtype_serializer()

    clients: list[tuple[str, Client, Any]] = []
    method_clients: list[tuple[str, Client, Any, Any]] = []
    local_buffer: list[dict[str, Any]] = []
    handlers: list[_DurableWorkerSubHandler] = []
    connected_endpoints: list[str] = []
    failed_endpoints: dict[str, str] = {}
    burst_failures: int = 0
    burst_errors: list[str] = []
    teardown_errors: list[str] = []
    last_reported_drops: int = 0

    connect_sem = asyncio.Semaphore(connect_concurrency)

    async def connect_and_subscribe(url: str) -> None:
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
                    await load_ijt_type_definitions(client)
                    skew = 0.0 if skip_clock_skew else await calibrate_clock_skew(client)

                    # Namespace resolution MUST be strict — do not guess ns=1
                    ns_ijt = await resolve_namespace_index(client, NS_IJT_BASE)
                    if ns_ijt is None:
                        raise RuntimeError(f"Server at {url} does not register required namespace {NS_IJT_BASE}")

                    event_node_id = ua.NodeId(JOINING_SYSTEM_RESULT_READY_EVENT_TYPE_ID, ns_ijt)  # type: ignore[arg-type]
                    handler = _DurableWorkerSubHandler(endpoint=url, local_buffer=local_buffer, clock_skew_ms=skew)
                    handlers.append(handler)

                    sub = await client.create_subscription(sub_period_ms, handler)
                    await sub.subscribe_events(client.nodes.server, client.get_node(event_node_id), queuesize=500)

                    clients.append((url, client, sub))
                    connected_endpoints.append(url)
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
        }
    )

    # Background periodic batch flush task
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
                    }
                )
                last_reported_drops = total_dropped

    flush_task = asyncio.create_task(periodic_flush())

    # Setup dedicated method clients for active burst mode
    if mode in ("active_burst", "both") and burst_trigger_count > 0:
        for url, _, _ in clients:
            m_cli: Client | None = None
            try:
                m_cli = Client(url=url)
                apply_session_policy(m_cli)
                await m_cli.connect()
                ns_app = await resolve_namespace_index(m_cli, NS_APP)
                sim_res, meth_node = await _locate_simulate_method(m_cli, ns_app)
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

        # Execute concurrent burst rounds across all tools simultaneously
        for burst_idx in range(burst_trigger_count):
            if stop_event.is_set():
                break

            async def fire_one(url: str, sim_node: Any, meth_id: Any) -> None:
                nonlocal burst_failures
                try:
                    await sim_node.call_method(
                        meth_id.nodeid,
                        ua.Variant(2, ua.VariantType.UInt32),  # MULTI_STEP_OK_RESULT
                        ua.Variant(True, ua.VariantType.Boolean),  # Traces
                    )
                except Exception as exc:
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
            await asyncio.sleep(1.0)

    # Listen until stop signal is set
    while not stop_event.is_set():
        await asyncio.sleep(0.1)

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
            }
        )

    # Clean teardown: delete subscriptions explicitly, then disconnect clients
    for _, m_cli, _, _ in method_clients:
        try:
            await disconnect_client(m_cli, settle_delay=0.01)
        except Exception as exc:
            teardown_errors.append(f"Method client disconnect: {exc}")

    for url, client, sub in clients:
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

    # Signal completion to master process
    total_dropped = sum(h.dropped_samples for h in handlers)
    out_queue.put(
        {
            "type": "DONE",
            "worker_id": worker_id,
            "connected_count": len(connected_endpoints),
            "dropped_samples": total_dropped,
            "burst_failures": burst_failures,
            "burst_errors": burst_errors,
            "teardown_errors": teardown_errors,
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
) -> None:
    """The entry point for each background worker process."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] [Worker %(process)d] %(message)s",
    )
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
    ) -> None:
        self.endpoints = endpoints
        if max_workers is not None:
            if not isinstance(max_workers, int) or max_workers < 1 or max_workers > MAX_SAFE_WORKER_PROCESSES:
                raise ValueError(
                    f"max_workers must be an integer between 1 and {MAX_SAFE_WORKER_PROCESSES}, got {max_workers}"
                )
            self.max_workers = max_workers
        else:
            self.max_workers = min(DEFAULT_MAX_WORKERS, max(1, len(endpoints)))
        self.connect_concurrency = connect_concurrency
        self.sub_period_ms = sub_period_ms
        self.mode = mode
        self.require_full_coverage = len(endpoints) > 1 if require_full_coverage is None else require_full_coverage
        self.skip_clock_skew = skip_clock_skew

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
        self.burst_trigger_failures: int = 0
        self.burst_trigger_errors: list[str] = []
        self.teardown_errors: list[str] = []

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
        self.burst_trigger_failures = 0
        self.burst_trigger_errors.clear()
        self.teardown_errors.clear()
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
                    self.connect_concurrency,
                    self.sub_period_ms,
                    self.mode,
                    burst_trigger_count,
                    self.skip_clock_skew,
                ),
                daemon=True,
            )
            proc.start()
            self._processes.append(proc)

    def _process_queue_msg(self, msg: dict[str, Any]) -> None:
        """Internal helper to process IPC messages from workers."""
        msg_type = msg.get("type")
        if msg_type in ("BATCH", "DONE") and "dropped_samples" in msg:
            worker_id = msg.get("worker_id")
            dropped = msg["dropped_samples"]
            if isinstance(worker_id, int) and isinstance(dropped, int) and dropped >= 0:
                self._dropped_by_worker[worker_id] = max(self._dropped_by_worker.get(worker_id, 0), dropped)
                self.total_dropped_samples = sum(self._dropped_by_worker.values())
        if msg_type == "BATCH":
            for raw in msg.get("samples", []):
                sample = LatencySample(
                    sample_id=raw["sample_id"],
                    endpoint=raw["endpoint"],
                    clock_skew_ms=raw["clock_skew_ms"],
                    joining_duration_ms=raw.get("joining_duration_ms"),
                    server_processing_time_ms=raw.get("server_processing_time_ms"),
                    network_transport_time_ms=raw.get("network_transport_time_ms"),
                    total_result_transfer_time_ms=raw.get("total_result_transfer_time_ms"),
                )
                if raw["start_time"]:
                    sample.start_time = datetime.fromisoformat(raw["start_time"])
                if raw["end_time"]:
                    sample.end_time = datetime.fromisoformat(raw["end_time"])
                if raw["creation_time"]:
                    sample.creation_time = datetime.fromisoformat(raw["creation_time"])
                if raw["event_time"]:
                    sample.event_time = datetime.fromisoformat(raw["event_time"])
                if raw["client_received_time"]:
                    sample.client_received_time = datetime.fromisoformat(raw["client_received_time"])
                self.collected_samples.append(sample)
        elif msg_type == "FLEET_STATUS":
            self.connected_endpoints.update(msg.get("connected", []))
            self.failed_endpoints.update(msg.get("failed", {}))
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

    def collect_samples(
        self,
        duration_seconds: float = 10.0,
        target_sample_count: int | None = None,
    ) -> list[LatencySample]:
        """Collect incoming LatencySamples from worker processes via IPC queue.
        Enforces explicit FLEET_STATUS tracking, BATCH handling, and coverage checks.
        """
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

    def stop(self, drain_timeout_s: float = 3.0) -> list[LatencySample]:
        """Signal workers to stop, drain final batch and DONE messages, inspect exitcodes, and cleanly close queues."""
        if self._stopped:
            return list(self.collected_samples)

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

    def verify_coverage(self, samples: list[LatencySample] | None = None) -> tuple[bool, str]:
        """Verifies fleet coverage, clean worker completion, and connection success.
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

        # 1. Require all started worker processes to complete cleanly with DONE
        expected_worker_ids = set(range(self._num_workers_started))
        missing_done = expected_worker_ids - self.completed_worker_ids
        if missing_done:
            return (
                False,
                f"Worker completion failure: workers {sorted(missing_done)} did not confirm clean shutdown. {msg}",
            )

        # 2. Check for worker process crashes, non-zero exits, uncaught exceptions, or teardown errors
        worker_failures = [*self.worker_errors, *self.teardown_errors]
        if worker_failures:
            return False, f"Worker process failures detected: {'; '.join(worker_failures)}. {msg}"

        # 3. Check connection failures
        if failed_count > 0:
            err_details = "; ".join(f"{ep}: {err}" for ep, err in list(self.failed_endpoints.items())[:3])
            return False, f"Connection failures on {failed_count} endpoints ({err_details}). {msg}"

        # 4. Check dropped samples due to backpressure
        if self.total_dropped_samples > 0:
            if self.require_full_coverage:
                return (
                    False,
                    f"Buffer overflow backpressure: dropped {self.total_dropped_samples} samples. {msg}",
                )
            msg += f" (Warning: {self.total_dropped_samples} samples dropped due to buffer backpressure)"

        # 5. Check active burst trigger failures
        if self.burst_trigger_failures > 0 and self.mode in ("active_burst", "both"):
            details = "; ".join(self.burst_trigger_errors[:3])
            if self.require_full_coverage:
                return (
                    False,
                    f"Active burst trigger failure: {self.burst_trigger_failures} setup/call failures"
                    f" ({details}). {msg}",
                )
            msg += f" (Warning: {self.burst_trigger_failures} active trigger failures: {details})"

        # 6. Incomplete coverage check
        if self.require_full_coverage and missing_sample_endpoints:
            return (
                False,
                f"Incomplete coverage: {len(missing_sample_endpoints)} endpoints produced zero samples. {msg}",
            )

        return True, msg
