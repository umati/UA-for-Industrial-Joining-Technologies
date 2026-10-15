"""Versioned fleet inventory: atomic file write/read + optional loopback HTTP serve."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request

from .host_fingerprint import generate_host_id

logger = logging.getLogger(__name__)

INVENTORY_SCHEMA_VERSION = 1
DEFAULT_TTL_SECONDS = 3600

# Named live / CI ports that must not be silently claimed by default fleet ranges.
RESERVED_LIVE_PORTS = frozenset({40451, 40461, 40463, 40465, 40485})


@dataclass
class InventoryEndpoint:
    url: str
    server_id: str
    port: int | None = None
    bind_host: str | None = None


@dataclass
class FleetInventory:
    schema_version: int
    run_id: str
    created_at: str
    expires_at: str
    producer_host_id: str
    producer_pid: int
    endpoints: list[InventoryEndpoint]
    expected_scale: int
    content_hash: str = ""
    simulator_build: str | None = None
    role: str = "serve-fleet"
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "producer_host_id": self.producer_host_id,
            "producer_pid": self.producer_pid,
            "expected_scale": self.expected_scale,
            "simulator_build": self.simulator_build,
            "role": self.role,
            "endpoints": [asdict(ep) for ep in self.endpoints],
            "extras": self.extras,
        }
        # Hash excludes content_hash itself
        payload = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
        data["content_hash"] = hashlib.sha256(payload).hexdigest()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FleetInventory:
        endpoints = [
            InventoryEndpoint(
                url=str(ep["url"]),
                server_id=str(ep.get("server_id", ep["url"])),
                port=ep.get("port"),
                bind_host=ep.get("bind_host"),
            )
            for ep in data.get("endpoints", [])
        ]
        inv = cls(
            schema_version=int(data.get("schema_version", 0)),
            run_id=str(data["run_id"]),
            created_at=str(data["created_at"]),
            expires_at=str(data["expires_at"]),
            producer_host_id=str(data["producer_host_id"]),
            producer_pid=int(data.get("producer_pid", 0)),
            endpoints=endpoints,
            expected_scale=int(data.get("expected_scale", len(endpoints))),
            content_hash=str(data.get("content_hash", "")),
            simulator_build=data.get("simulator_build"),
            role=str(data.get("role", "serve-fleet")),
            extras=dict(data.get("extras") or {}),
        )
        return inv

    def endpoint_urls(self) -> list[str]:
        return [ep.url for ep in self.endpoints]


def build_inventory(
    endpoints: list[str],
    *,
    run_id: str | None = None,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    simulator_build: str | None = None,
    role: str = "serve-fleet",
    extras: dict[str, Any] | None = None,
) -> FleetInventory:
    now = datetime.now(UTC)
    run = run_id or f"run-{now.strftime('%Y%m%dT%H%M%SZ')}-{os.getpid()}"
    eps = []
    for i, url in enumerate(endpoints):
        port = None
        try:
            from urllib.parse import urlparse

            port = urlparse(url).port
        except Exception:
            port = None
        eps.append(InventoryEndpoint(url=url, server_id=f"s{i:04d}", port=port, bind_host=None))
    inv = FleetInventory(
        schema_version=INVENTORY_SCHEMA_VERSION,
        run_id=run,
        created_at=now.isoformat(),
        expires_at=(now + timedelta(seconds=ttl_seconds)).isoformat(),
        producer_host_id=generate_host_id(),
        producer_pid=os.getpid(),
        endpoints=eps,
        expected_scale=len(eps),
        simulator_build=simulator_build,
        role=role,
        extras=extras or {},
    )
    inv.content_hash = inv.to_dict()["content_hash"]
    return inv


def write_inventory_atomic(path: str | Path, inventory: FleetInventory) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    data = inventory.to_dict()
    inventory.content_hash = data["content_hash"]
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.replace(target)
    logger.info("Wrote fleet inventory to %s (run_id=%s)", target, inventory.run_id)
    return target


def _fetch_inventory_url(url: str, *, token: str | None, timeout: float = 30.0) -> str:
    """Fetch inventory JSON without following redirects.

    Redirects are refused so a Bearer token cannot be forwarded to an unexpected hop
    (e.g. https → http). Prefer a local/shared file for remote client-only runs.
    """
    from urllib.request import HTTPRedirectHandler, build_opener

    class _RejectRedirects(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
            raise URLError(
                f"Refusing to follow HTTP redirect from inventory URL (status {code}); "
                "redirects are blocked to prevent bearer-token leakage"
            )

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, headers=headers)
    opener = build_opener(_RejectRedirects)
    with opener.open(req, timeout=timeout) as resp:  # nosec B310 — operator-supplied inventory URL
        raw = resp.read(2_000_000)
    return raw.decode("utf-8")


def load_inventory(source: str | Path, *, token: str | None = None) -> FleetInventory:
    """Load inventory from a file path or http(s) URL. Fail closed on expiry/mismatch."""
    text = str(source).strip()
    lower = text.lower()
    if lower.startswith("http://") or lower.startswith("https://"):
        if lower.startswith("http://") and token:
            raise ValueError("Refusing to send inventory bearer token over plaintext HTTP. Use HTTPS or a file path.")
        try:
            body = _fetch_inventory_url(text, token=token)
        except URLError as exc:
            raise FileNotFoundError(f"Failed to fetch inventory from {text}: {exc}") from exc
        data = json.loads(body)
    else:
        path = Path(source)
        if not path.is_file():
            raise FileNotFoundError(f"Inventory file not found: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ValueError("Inventory must be a JSON object")
    if int(data.get("schema_version", 0)) != INVENTORY_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported inventory schema_version {data.get('schema_version')}; expected {INVENTORY_SCHEMA_VERSION}"
        )

    claimed = str(data.get("content_hash") or "").strip()
    if not claimed:
        raise ValueError("Inventory missing required content_hash — refuse to consume")
    inv = FleetInventory.from_dict(data)
    recomputed = inv.to_dict()["content_hash"]
    if claimed != recomputed:
        raise ValueError("Inventory content_hash mismatch — refuse to consume stale or tampered inventory")

    try:
        expires = datetime.fromisoformat(inv.expires_at.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Inventory expires_at is not a valid ISO timestamp: {inv.expires_at!r}") from exc
    if datetime.now(UTC) > expires:
        raise ValueError(f"Inventory expired at {inv.expires_at}")

    return inv


def _port_appears_busy(port: int) -> bool:
    """Best-effort: connect to 127.0.0.1, then try exclusive bind on 127.0.0.1 (no SO_REUSEADDR)."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        if sock.connect_ex(("127.0.0.1", port)) == 0:
            return True
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return True
    return False


def preflight_port_range(start_port: int, count: int, *, reserved: frozenset[int] = RESERVED_LIVE_PORTS) -> list[str]:
    """Return human-readable conflict reasons before launching simulators. Empty = OK."""
    errors: list[str] = []
    end_port = start_port + count - 1
    overlap = sorted(p for p in range(start_port, end_port + 1) if p in reserved)
    if overlap:
        errors.append(
            f"Port range {start_port}..{end_port} overlaps reserved live/CI ports {overlap}. "
            "Choose --start-port that avoids 40451/40461/40463/40465/40485 or reduce --servers."
        )
    busy = [port for port in range(start_port, end_port + 1) if _port_appears_busy(port)]
    if busy:
        preview = busy[:10]
        more = f" (+{len(busy) - 10} more)" if len(busy) > 10 else ""
        errors.append(f"Ports already in use: {preview}{more}")
    return errors


def preflight_http_port(port: int, host: str = "127.0.0.1") -> list[str]:
    """Check inventory HTTP listen port before binding."""
    if _port_appears_busy(port):
        return [f"Inventory HTTP port {port} on {host} appears already in use"]
    return []


def remaining_ttl_seconds(inventory: FleetInventory) -> float | None:
    """Seconds until inventory expiry, or None if expires_at cannot be parsed."""
    try:
        expires = datetime.fromisoformat(inventory.expires_at.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return (expires - datetime.now(UTC)).total_seconds()


class _InventoryHandler(BaseHTTPRequestHandler):
    inventory_bytes: bytes = b"{}"
    auth_token: str | None = None

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        logger.debug("inventory-http: " + format, *args)

    def do_GET(self) -> None:  # noqa: N802
        if self.path not in ("/inventory", "/inventory.json", "/"):
            self.send_error(404)
            return
        if self.auth_token:
            header = self.headers.get("Authorization", "")
            if header != f"Bearer {self.auth_token}":
                self.send_error(401, "Unauthorized")
                return
        body = self.inventory_bytes
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("ETag", hashlib.sha256(body).hexdigest())
        self.end_headers()
        self.wfile.write(body)


class InventoryHttpServer:
    """Serve inventory JSON. Default bind is loopback only."""

    def __init__(
        self,
        inventory: FleetInventory,
        *,
        host: str = "127.0.0.1",
        port: int = 8765,
        token: str | None = None,
        allow_non_loopback: bool = False,
    ) -> None:
        if host not in ("127.0.0.1", "localhost", "::1") and not allow_non_loopback:
            raise ValueError(
                "Inventory HTTP refuses non-loopback bind by default. "
                "Pass allow_non_loopback=True explicitly and use TLS termination in front."
            )
        if allow_non_loopback and host not in ("127.0.0.1", "localhost", "::1") and not token:
            raise ValueError("Remote inventory HTTP requires an auth token")
        self._inventory = inventory
        payload = json.dumps(inventory.to_dict(), indent=2).encode("utf-8")

        class Handler(_InventoryHandler):
            pass

        Handler.inventory_bytes = payload
        Handler.auth_token = token
        self._httpd = ThreadingHTTPServer((host, port), Handler)
        self._thread: threading.Thread | None = None
        self.host = host
        self.port = port

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}/inventory"

    def start(self) -> None:
        self._thread = threading.Thread(target=self._httpd.serve_forever, name="inventory-http", daemon=True)
        self._thread.start()
        logger.info("Inventory HTTP listening on %s", self.url)

    def stop(self) -> None:
        self._httpd.shutdown()
        if self._thread:
            self._thread.join(timeout=5)
