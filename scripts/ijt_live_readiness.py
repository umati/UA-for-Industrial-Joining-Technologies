"""
Shared live-test readiness contract for the IJT repository.

Architectural principle (carried forward from the Browser CI synchronization
commit):

    No external waits. No inferred identity. No timeout-as-sync.
    Producer and consumer share a dependency edge with a passed-forward output.

For live tests, the analogous contract is:

    Wait by protocol handshake, not by TCP port liveness.
    Capture deterministic diagnostics into a job-scoped directory whenever a
    wait fails. Use compose-native --wait/healthcheck synchronization when
    docker compose is the producer; otherwise issue a real protocol probe.

Two import tiers:

1. Mandatory (stdlib-only). The functions ``wait_for_tcp``,
   ``wait_for_opcua_hello``, ``write_diagnostic_manifest``,
   ``capture_compose_logs_on_failure``, and ``capture_process_log_tail`` import
   nothing outside the Python standard library at module-import time. This
   tier MUST stay importable from ``scripts/start_server_on_port.py``, which
   runs in CI jobs (notably C# Live) before any ``pip install`` step.

2. Optional (``asyncua`` / ``websockets``). The functions
   ``wait_for_opcua_session`` and ``wait_for_websocket_backend`` perform
   *deferred* third-party imports inside their function bodies. Importing
   ``ijt_live_readiness`` itself stays dependency-light; only callers that
   actually invoke these functions need the optional dependencies installed.

Diagnostic contract:

    Every public ``wait_for_*`` function returns a :class:`ReadinessResult`.
    Callers that pass ``diagnostics_dir=<path>`` get a JSON manifest written
    to ``<path>/readiness-diagnostic-<caller>.json`` regardless of outcome,
    plus compose-log / process-log tails on failure when applicable.

This module is the single source of truth for what "ready" means across the
C# fixture, Python live conftests, runner scripts, and the CI workflows that
invoke ``start_server_on_port.py``.
"""

from __future__ import annotations

import contextlib
import dataclasses
import json
import os
import socket
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

__all__ = [
    "COMPOSE_WAIT_TIMEOUT_WARM_SECONDS",
    "COMPOSE_WAIT_TIMEOUT_COLD_SECONDS",
    "OPCUA_HELLO_DEFAULT_TIMEOUT_SECONDS",
    "ReadinessResult",
    "capture_compose_logs_on_failure",
    "capture_process_log_tail",
    "wait_for_opcua_hello",
    "wait_for_opcua_session",
    "wait_for_tcp",
    "wait_for_websocket_backend",
    "write_diagnostic_manifest",
]

# ─────────────────────────────────────────────────────────────────────────────
# Named timeout budgets
#
# Server compose healthcheck (OPC_UA_Servers/Release2/docker-compose.yml):
#   start_period 20s + interval 10s × retries 6 ≈ 80s budget.
# Web Client compose healthcheck (IJT_Web_Client/docker-compose.yml):
#   start_period 20s + interval 30s × retries 3 ≈ 110s budget.
# WARM covers both with safety margin; COLD covers the additional image build.
# These two are the only allowed values for compose ``--wait-timeout``.
# ─────────────────────────────────────────────────────────────────────────────
COMPOSE_WAIT_TIMEOUT_WARM_SECONDS = 120
COMPOSE_WAIT_TIMEOUT_COLD_SECONDS = 300
OPCUA_HELLO_DEFAULT_TIMEOUT_SECONDS = 60.0

_MANIFEST_SCHEMA_VERSION = 1


@dataclasses.dataclass(frozen=True)
class ReadinessResult:
    """Outcome of one ``wait_for_*`` call.

    ``ok`` is True iff the probe succeeded within budget. ``error`` is None
    on success and a single-line summary on failure. ``elapsed_seconds`` is
    monotonic wall-clock time spent inside the wait, not CPU time.
    """

    ok: bool
    probe: str
    host: str
    port: int
    elapsed_seconds: float
    attempts: int
    started_at: str
    finished_at: str
    error: str | None = None
    endpoint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


# ─────────────────────────────────────────────────────────────────────────────
# Tier 1 — stdlib-only probes
# ─────────────────────────────────────────────────────────────────────────────


def wait_for_tcp(
    host: str,
    port: int,
    *,
    timeout: float = OPCUA_HELLO_DEFAULT_TIMEOUT_SECONDS,
    interval: float = 1.0,
    connect_timeout: float = 2.0,
) -> ReadinessResult:
    """Wait until ``host:port`` accepts a TCP connection or timeout elapses.

    This is the weakest probe. Prefer :func:`wait_for_opcua_hello` for OPC UA
    servers and :func:`wait_for_websocket_backend` for the WS bridge — open
    TCP does not imply protocol readiness.
    """

    started_at = _utcnow_iso()
    start = time.monotonic()
    deadline = start + timeout
    attempts = 0
    last_error: str | None = None
    while time.monotonic() < deadline:
        attempts += 1
        try:
            with socket.create_connection((host, port), timeout=connect_timeout):
                elapsed = time.monotonic() - start
                return ReadinessResult(
                    ok=True,
                    probe="tcp",
                    host=host,
                    port=port,
                    elapsed_seconds=round(elapsed, 3),
                    attempts=attempts,
                    started_at=started_at,
                    finished_at=_utcnow_iso(),
                    error=None,
                )
        except OSError as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            time.sleep(interval)

    elapsed = time.monotonic() - start
    return ReadinessResult(
        ok=False,
        probe="tcp",
        host=host,
        port=port,
        elapsed_seconds=round(elapsed, 3),
        attempts=attempts,
        started_at=started_at,
        finished_at=_utcnow_iso(),
        error=f"TCP {host}:{port} not accepting connections within {timeout:.1f}s "
        f"(last error: {last_error or 'no attempts made'})",
    )


def _build_opcua_hello_message(host: str, port: int) -> bytes:
    """Build the minimal well-formed OPC UA Binary HELLO message.

    Layout per OPC UA Part 6 §7.1.2.3 (MessageType + Chunk + Length + Hello):
        Bytes  0..3  : 'HEL' + 'F'
        Bytes  4..7  : MessageSize (LE)
        Bytes  8..11 : ProtocolVersion = 0
        Bytes 12..15 : ReceiveBufferSize = 65536
        Bytes 16..19 : SendBufferSize    = 65536
        Bytes 20..23 : MaxMessageSize    = 0 (unlimited)
        Bytes 24..27 : MaxChunkCount     = 0 (unlimited)
        Bytes 28..31 : EndpointUrl length (LE)
        Bytes 32..   : EndpointUrl bytes (ASCII)

    Mirrors the Console live conftest probe and the C# fixture
    ProbeOpcUaReady helper.
    """

    endpoint_url = f"opc.tcp://{host}:{port}".encode("ascii")
    url_len = len(endpoint_url)
    total_len = 32 + url_len
    hello = bytearray()
    hello += b"HELF"
    hello += total_len.to_bytes(4, "little")
    hello += (0).to_bytes(4, "little")
    hello += (65536).to_bytes(4, "little")
    hello += (65536).to_bytes(4, "little")
    hello += (0).to_bytes(4, "little")
    hello += (0).to_bytes(4, "little")
    hello += url_len.to_bytes(4, "little")
    hello += endpoint_url
    return bytes(hello)


def wait_for_opcua_hello(
    host: str,
    port: int,
    *,
    timeout: float = OPCUA_HELLO_DEFAULT_TIMEOUT_SECONDS,
    interval: float = 1.0,
    socket_timeout: float = 3.0,
) -> ReadinessResult:
    """Wait until the OPC UA server responds to a raw HELLO with ACK or ERR.

    Either response means the OPC UA stack is alive — ACK is the happy path,
    ERR is the server politely rejecting our minimal HELLO (still proves
    binary-protocol readiness). Any other reply, EOF, or connection failure
    is treated as not-yet-ready and retried until ``timeout`` elapses.

    Stdlib-only by design. Safe to call from
    ``scripts/start_server_on_port.py`` in CI jobs that have not run
    ``pip install`` yet (notably the C# Live job).
    """

    started_at = _utcnow_iso()
    start = time.monotonic()
    deadline = start + timeout
    attempts = 0
    last_error: str | None = None
    hello = _build_opcua_hello_message(host, port)

    while time.monotonic() < deadline:
        attempts += 1
        try:
            with socket.create_connection((host, port), timeout=socket_timeout) as sock:
                sock.settimeout(socket_timeout)
                sock.sendall(hello)
                header = sock.recv(8)
                if len(header) >= 4 and header[:3] in (b"ACK", b"ERR") and header[3:4] == b"F":
                    elapsed = time.monotonic() - start
                    return ReadinessResult(
                        ok=True,
                        probe="opcua_hello",
                        host=host,
                        port=port,
                        elapsed_seconds=round(elapsed, 3),
                        attempts=attempts,
                        started_at=started_at,
                        finished_at=_utcnow_iso(),
                        error=None,
                        endpoint=f"opc.tcp://{host}:{port}",
                    )
                last_error = f"unexpected reply: {header!r}"
        except (TimeoutError, OSError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        time.sleep(interval)

    elapsed = time.monotonic() - start
    return ReadinessResult(
        ok=False,
        probe="opcua_hello",
        host=host,
        port=port,
        elapsed_seconds=round(elapsed, 3),
        attempts=attempts,
        started_at=started_at,
        finished_at=_utcnow_iso(),
        error=f"OPC UA HELLO probe to {host}:{port} did not get ACK/ERR within "
        f"{timeout:.1f}s (last error: {last_error or 'no attempts made'})",
        endpoint=f"opc.tcp://{host}:{port}",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Tier 2 — deferred third-party probes (asyncua, websockets)
# ─────────────────────────────────────────────────────────────────────────────


def opcua_session_probe_once(
    endpoint_url: str,
    *,
    connect_timeout: float = 5.0,
) -> str | None:
    """Run a single asyncua connect+disconnect against ``endpoint_url``.

    Returns ``None`` on success, a single-line error string on failure. Use
    this when the caller wants to own the retry loop (so it can interleave
    progress logging, sleep policy, or alternative probes). Higher-level
    callers should prefer :func:`wait_for_opcua_session`.
    """

    try:
        import asyncio

        from asyncua import Client as _AsyncuaClient
    except ImportError as exc:  # pragma: no cover — environment-specific
        return f"ImportError: asyncua not installed: {exc}"

    async def _probe_once() -> None:
        # asyncua's Client is positional ``(url, timeout)``; using kwargs here
        # breaks call-site fakes that pin the constructor shape.
        client = _AsyncuaClient(endpoint_url, connect_timeout)
        try:
            await client.connect()
        finally:
            # asyncua's connect() raises before any state is set when the
            # server is not yet listening; disconnect() then is a no-op
            # except for resource cleanup, hence the broad suppression.
            with contextlib.suppress(Exception):
                await client.disconnect()

    try:
        asyncio.run(_probe_once())
    except Exception as exc:  # noqa: BLE001 — asyncua raises many shapes
        return f"{type(exc).__name__}: {exc}"
    return None


def wait_for_opcua_session(
    endpoint_url: str,
    *,
    timeout: float = OPCUA_HELLO_DEFAULT_TIMEOUT_SECONDS,
    interval: float = 2.0,
    connect_timeout: float = 5.0,
) -> ReadinessResult:
    """Wait until an asyncua client can connect+disconnect from ``endpoint_url``.

    Stronger than :func:`wait_for_opcua_hello` because it negotiates a real
    secure channel and session. Use this from Python clients that already
    depend on ``asyncua`` (Web Client, Test Client). Do not call from
    ``start_server_on_port.py`` — that script runs without ``asyncua``.
    """

    host, port = _parse_opcua_endpoint(endpoint_url)
    started_at = _utcnow_iso()
    start = time.monotonic()
    deadline = start + timeout
    attempts = 0
    last_error: str | None = None

    while time.monotonic() < deadline:
        attempts += 1
        last_error = opcua_session_probe_once(endpoint_url, connect_timeout=connect_timeout)
        if last_error is None:
            elapsed = time.monotonic() - start
            return ReadinessResult(
                ok=True,
                probe="opcua_session",
                host=host,
                port=port,
                elapsed_seconds=round(elapsed, 3),
                attempts=attempts,
                started_at=started_at,
                finished_at=_utcnow_iso(),
                error=None,
                endpoint=endpoint_url,
            )
        time.sleep(interval)

    elapsed = time.monotonic() - start
    return ReadinessResult(
        ok=False,
        probe="opcua_session",
        host=host,
        port=port,
        elapsed_seconds=round(elapsed, 3),
        attempts=attempts,
        started_at=started_at,
        finished_at=_utcnow_iso(),
        error=f"asyncua session probe to {endpoint_url} did not succeed within "
        f"{timeout:.1f}s (last error: {last_error or 'no attempts made'})",
        endpoint=endpoint_url,
    )


def websocket_probe_once(
    probe_url: str,
    *,
    payload_json: str,
    handshake_id: str,
    open_timeout: float = 5.0,
    close_timeout: float = 2.0,
    response_timeout: float = 5.0,
    max_response_frames: int = 5,
) -> str | None:
    """Run a single WebSocket open → send(payload) → recv(handshake reply) round.

    Returns ``None`` on success, an error string on failure. ``response_timeout``
    is an *absolute* budget: the total time spent in recv() loops will never
    exceed it, regardless of how many frames the backend sends. The caller
    owns retries (sleep/jitter) so it can apply call-site-specific policy.

    The probe succeeds as soon as it receives any frame whose JSON text
    contains ``handshake_id``. The backend may answer with a normal payload
    or with ``{"exception": "..."}``; both are treated as success because the
    contract being tested is "WebSocket plumbing works", not "this particular
    backend command succeeded".
    """

    try:
        import asyncio

        import websockets
    except ImportError as exc:  # pragma: no cover — environment-specific
        return f"ImportError: websockets not installed: {exc}"

    def _reply_matches_handshake(reply: object) -> bool:
        """Return True iff ``reply`` carries an exact ``uniqueid == handshake_id``.

        The reply must be a JSON object whose ``uniqueid`` field equals the
        expected handshake id. Substring containment is intentionally NOT
        accepted: an attacker (or a buggy backend) returning
        ``"not-<handshake_id>"`` MUST be rejected, otherwise the probe would
        treat the wrong session as success.
        """

        text = reply if isinstance(reply, str) else str(reply)
        try:
            obj = json.loads(text)
        except (TypeError, ValueError):
            return False
        if not isinstance(obj, dict):
            return False
        return obj.get("uniqueid") == handshake_id

    async def _probe_once() -> None:
        async with websockets.connect(
            probe_url,
            open_timeout=open_timeout,
            close_timeout=close_timeout,
        ) as ws:
            await ws.send(payload_json)
            recv_deadline = time.monotonic() + response_timeout
            last_reply: object | None = None
            for _ in range(max_response_frames):
                remaining = recv_deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(
                        f"no handshake-correlated frame within {response_timeout:.1f}s budget"
                    )
                reply = await asyncio.wait_for(ws.recv(), timeout=remaining)
                last_reply = reply
                if _reply_matches_handshake(reply):
                    return
            raise RuntimeError(
                f"no reply with uniqueid=={handshake_id!r} "
                f"after {max_response_frames} frames; last={last_reply!r}"
            )

    try:
        asyncio.run(_probe_once())
    except Exception as exc:  # noqa: BLE001 — websockets/asyncio raise many shapes
        return f"{type(exc).__name__}: {exc}"
    return None


def wait_for_websocket_backend(
    probe_url: str,
    *,
    payload_json: str,
    handshake_id: str,
    timeout: float = 30.0,
    interval: float = 1.0,
    open_timeout: float = 5.0,
    close_timeout: float = 2.0,
    response_timeout: float = 5.0,
) -> ReadinessResult:
    """Retry :func:`websocket_probe_once` until success or ``timeout`` elapses.

    The caller supplies the JSON ``payload_json`` to send and the
    ``handshake_id`` to look for in the reply. This keeps the IJT-specific
    handshake shape (which command, which endpoint name, which uniqueid) out
    of the shared module — see the Web Client adapter for the actual contract.
    """

    host, port = _parse_ws_endpoint(probe_url)
    started_at = _utcnow_iso()
    start = time.monotonic()
    deadline = start + timeout
    attempts = 0
    last_error: str | None = None

    while time.monotonic() < deadline:
        attempts += 1
        last_error = websocket_probe_once(
            probe_url,
            payload_json=payload_json,
            handshake_id=handshake_id,
            open_timeout=open_timeout,
            close_timeout=close_timeout,
            response_timeout=response_timeout,
        )
        if last_error is None:
            elapsed = time.monotonic() - start
            return ReadinessResult(
                ok=True,
                probe="websocket_backend",
                host=host,
                port=port,
                elapsed_seconds=round(elapsed, 3),
                attempts=attempts,
                started_at=started_at,
                finished_at=_utcnow_iso(),
                error=None,
                endpoint=probe_url,
            )
        time.sleep(interval)

    elapsed = time.monotonic() - start
    return ReadinessResult(
        ok=False,
        probe="websocket_backend",
        host=host,
        port=port,
        elapsed_seconds=round(elapsed, 3),
        attempts=attempts,
        started_at=started_at,
        finished_at=_utcnow_iso(),
        error=f"WebSocket backend at {probe_url} did not complete handshake "
        f"{handshake_id!r} within {timeout:.1f}s "
        f"(last error: {last_error or 'no attempts made'})",
        endpoint=probe_url,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Endpoint parsing helpers (stdlib-only)
# ─────────────────────────────────────────────────────────────────────────────


def _parse_opcua_endpoint(endpoint_url: str) -> tuple[str, int]:
    """Parse ``opc.tcp://host:port[/...]`` → (host, port)."""

    if not endpoint_url.startswith("opc.tcp://"):
        raise ValueError(f"Not an opc.tcp:// URL: {endpoint_url!r}")
    rest = endpoint_url[len("opc.tcp://") :]
    authority = rest.split("/", 1)[0]
    if ":" not in authority:
        raise ValueError(f"opc.tcp URL missing :port — {endpoint_url!r}")
    host, port_str = authority.rsplit(":", 1)
    return host, int(port_str)


def _parse_ws_endpoint(probe_url: str) -> tuple[str, int]:
    """Parse ``ws://host:port[/...]`` or ``wss://host:port[/...]`` → (host, port)."""

    for scheme in ("ws://", "wss://"):
        if probe_url.startswith(scheme):
            rest = probe_url[len(scheme) :]
            authority = rest.split("/", 1)[0]
            if ":" not in authority:
                # Default ws=80, wss=443; the IJT backend always specifies a port.
                raise ValueError(f"ws URL missing :port — {probe_url!r}")
            host, port_str = authority.rsplit(":", 1)
            return host, int(port_str)
    raise ValueError(f"Not a ws:// or wss:// URL: {probe_url!r}")


# ─────────────────────────────────────────────────────────────────────────────
# Diagnostic capture (stdlib-only)
# ─────────────────────────────────────────────────────────────────────────────


def _slugify(caller: str) -> str:
    return (
        "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in caller).strip("_") or "caller"
    )


def write_diagnostic_manifest(
    directory: Path | str | None,
    result: ReadinessResult,
    *,
    caller: str,
    extra: dict[str, Any] | None = None,
) -> Path | None:
    """Write a JSON manifest summarising one readiness wait into ``directory``.

    Returns the manifest path on success, ``None`` when ``directory`` is None
    or empty. Always safe — never raises through caller stacks (best-effort
    write; logs to stderr on failure but does not re-raise).
    """

    if not directory:
        return None
    target = Path(directory)
    try:
        target.mkdir(parents=True, exist_ok=True)
        path = target / f"readiness-diagnostic-{_slugify(caller)}.json"
        payload: dict[str, Any] = {
            "schema_version": _MANIFEST_SCHEMA_VERSION,
            "caller": caller,
            "result": result.to_dict(),
        }
        if extra:
            payload["extra"] = extra
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return path
    except OSError as exc:
        # Best-effort: a diagnostics-write failure must not mask the real test
        # outcome. Print and move on.
        import sys

        print(
            f"[ijt_live_readiness] WARN: could not write diagnostic manifest to {target!r}: {exc}",
            file=sys.stderr,
        )
        return None


def capture_compose_logs_on_failure(
    directory: Path | str | None,
    compose_dir: Path | str,
    service: str,
    *,
    project: str | None = None,
    docker_executable: str = "docker",
    tail: int = 200,
) -> Path | None:
    """Save ``docker compose logs --no-color --tail=<N> <service>`` into ``directory``.

    Intended to be called from the failure branch of a readiness wait, after
    the manifest is written. Best-effort: returns ``None`` when ``directory``
    is empty or the docker invocation fails.
    """

    if not directory:
        return None
    target = Path(directory)
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None

    env = os.environ.copy()
    if project:
        env["COMPOSE_PROJECT_NAME"] = project

    args = [
        docker_executable,
        "compose",
        "logs",
        "--no-color",
        "--tail",
        str(int(tail)),
        service,
    ]
    try:
        completed = subprocess.run(  # noqa: S603 — explicit argv, env-scoped
            args,
            cwd=str(compose_dir),
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        path = target / f"compose-logs-{_slugify(service)}.txt"
        path.write_text(
            f"[ijt_live_readiness] failed to capture compose logs: {exc}\n",
            encoding="utf-8",
        )
        return path

    path = target / f"compose-logs-{_slugify(service)}.txt"
    body = (
        f"# docker compose logs --no-color --tail={tail} {service}\n"
        f"# cwd: {compose_dir}\n"
        f"# exit_code: {completed.returncode}\n"
        f"# captured_at: {_utcnow_iso()}\n"
        f"\n--- stdout ---\n{completed.stdout}\n--- stderr ---\n{completed.stderr}\n"
    )
    path.write_text(body, encoding="utf-8")
    return path


def capture_process_log_tail(
    directory: Path | str | None,
    name: str,
    lines: list[str],
    *,
    tail: int = 200,
) -> Path | None:
    """Write the last ``tail`` lines of an in-memory log buffer to ``directory``.

    Useful for callers (notably ``start_server_on_port.py``) that capture a
    subprocess's stdout/stderr into a rolling buffer instead of streaming to
    DEVNULL. Best-effort, never raises through the caller stack.
    """

    if not directory or not lines:
        return None
    target = Path(directory)
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None

    snippet = lines[-int(tail) :] if len(lines) > tail else list(lines)
    path = target / f"process-log-{_slugify(name)}.txt"
    body = (
        f"# process log tail (last {len(snippet)} of {len(lines)} captured lines)\n"
        f"# name: {name}\n"
        f"# captured_at: {_utcnow_iso()}\n\n" + "\n".join(snippet) + "\n"
    )
    path.write_text(body, encoding="utf-8")
    return path
