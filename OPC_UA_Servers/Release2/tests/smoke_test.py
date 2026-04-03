#!/usr/bin/env python3
"""
OPC UA IJT Server Simulator — Smoke / Sanity Tests
====================================================
Verifies that the server is reachable, responds to OPC UA, and exposes the
correct IJT address space.  Runs against both Windows-native and Docker
deployments.

Usage:
    # Prerequisites: pip install asyncua
    python tests/smoke_test.py                        # default localhost:40451
    python tests/smoke_test.py --endpoint opc.tcp://192.168.1.10:40451
    python tests/smoke_test.py --tcp-timeout 60       # longer start-up wait

Exit codes:
    0 — all checks passed
    1 — one or more checks failed
    2 — server not reachable (TCP probe failed)
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import socket
import sys
import time
from typing import Any

# asyncua is a required dependency — all asyncua symbols are imported here so
# that a missing package is caught immediately with a clear error message.
try:
    from asyncua import Client as _Client
    from asyncua import ua as _ua
    _OpcUaError = _ua.UaError
except ImportError as exc:
    raise ImportError(
        "asyncua is required to run smoke tests. Install it with: pip install asyncua"
    ) from exc

# -- Namespace URIs (from OPC UA IJT companion specs) -------------------------
_NS_IJT_BASE = "http://opcfoundation.org/UA/IJT/Base/"
_NS_IJT_TIGHTENING = "http://opcfoundation.org/UA/IJT/Tightening/"
_NS_MACHINERY = "http://opcfoundation.org/UA/Machinery/"
_NS_MACHINERY_RESULT = "http://opcfoundation.org/UA/Machinery/Result/"
_NS_IJT_SERVER = "urn:AtlasCopco:IJT:Tightening:Server/"

_STATUS_PASS = "PASS"
_STATUS_FAIL = "FAIL"
_STATUS_SKIP = "SKIP"

_OPC_CONNECTION_RETRY_COUNT = 5
_OPC_CONNECTION_RETRY_DELAY = 3.0


def _result_line(status: str, name: str, detail: str = "") -> str:
    icon = {_STATUS_PASS: "[OK]", _STATUS_FAIL: "[FAIL]", _STATUS_SKIP: "[SKIP]"}[status]
    line = f"  {icon}  {name}"
    if detail:
        line += f"  ({detail})"
    return line


def _port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _parse_endpoint(endpoint: str) -> tuple[str, int]:
    """Return (host, port) from 'opc.tcp://host:port'.

    Raises:
        ValueError: If the endpoint is not in the expected format or the port
            is not a valid integer.
    """
    expected_scheme = "opc.tcp://"
    if not endpoint.startswith(expected_scheme):
        raise ValueError(f"Invalid OPC UA endpoint '{endpoint}': expected scheme '{expected_scheme}'.")

    without_scheme = endpoint[len(expected_scheme) :]
    host, sep, port_str = without_scheme.partition(":")

    if not host:
        raise ValueError(f"Invalid OPC UA endpoint '{endpoint}': host is missing.")

    if sep and port_str:
        # Port was provided explicitly; validate that it is numeric to avoid
        # exposing a generic ValueError from int().
        if not port_str.isdigit():
            raise ValueError(
                f"Invalid OPC UA endpoint '{endpoint}': port '{port_str}' is not a valid integer."
            )
        port = int(port_str)
    else:
        # No port specified; default to the well-known port used by these tests.
        port = 40451

    return host, port


# -- Individual checks ---------------------------------------------------------


async def check_tcp_port(host: str, port: int, wait_s: float) -> tuple[str, str]:
    """Poll TCP port until the server accepts connections or timeout."""
    deadline = time.monotonic() + wait_s
    while time.monotonic() < deadline:
        if _port_open(host, port, timeout=1.0):
            return _STATUS_PASS, f"port {port} is open"
        await asyncio.sleep(1.0)
    return _STATUS_FAIL, f"port {port} not reachable after {wait_s:.0f}s"


async def check_opc_connection(client: Any) -> tuple[str, str]:
    """Try to establish an OPC UA session, retrying briefly after TCP is open."""
    last_exc: Exception | None = None
    for attempt in range(_OPC_CONNECTION_RETRY_COUNT):
        try:
            await client.connect()
            return _STATUS_PASS, "OPC UA session established"
        except (_OpcUaError, ConnectionError, TimeoutError, OSError) as exc:
            last_exc = exc
            if attempt < 4:
                await asyncio.sleep(_OPC_CONNECTION_RETRY_DELAY)
    return _STATUS_FAIL, str(last_exc)


async def check_server_time(client: Any) -> tuple[str, str]:
    try:
        node = client.get_node("ns=0;i=2258")  # Server/ServerStatus/CurrentTime
        val = await node.read_value()
        return _STATUS_PASS, f"CurrentTime = {val}"
    except (_OpcUaError, AttributeError) as exc:
        return _STATUS_FAIL, str(exc)


async def check_namespaces(client: Any) -> tuple[str, str]:
    try:
        ns_array = await client.get_namespace_array()
        missing = [
            uri
            for uri in (
                _NS_IJT_BASE,
                _NS_IJT_TIGHTENING,
                _NS_MACHINERY,
                _NS_MACHINERY_RESULT,
            )
            if uri not in ns_array
        ]
        if missing:
            return _STATUS_FAIL, "missing namespaces: " + ", ".join(missing)
        return _STATUS_PASS, f"{len(ns_array)} namespaces, all IJT URIs present"
    except (_OpcUaError, AttributeError) as exc:
        return _STATUS_FAIL, str(exc)


async def check_tightening_system(client: Any) -> tuple[str, str]:
    try:
        ns1 = await client.get_namespace_index(_NS_IJT_SERVER)
        node = await client.nodes.root.get_child(
            ["0:Objects", f"{ns1}:TighteningSystem"]
        )
        bn = await node.read_browse_name()
        return _STATUS_PASS, f"TighteningSystem found ({bn})"
    except (_OpcUaError, ValueError, AttributeError) as exc:
        return _STATUS_FAIL, str(exc)


async def check_simulations_node(client: Any) -> tuple[str, str]:
    try:
        ns1 = await client.get_namespace_index(_NS_IJT_SERVER)
        node = await client.nodes.root.get_child(
            ["0:Objects", f"{ns1}:TighteningSystem", f"{ns1}:Simulations"]
        )
        children = await node.get_children()
        return _STATUS_PASS, f"Simulations node has {len(children)} method(s)"
    except (_OpcUaError, ValueError, AttributeError) as exc:
        return _STATUS_FAIL, str(exc)


async def check_result_management(client: Any) -> tuple[str, str]:
    try:
        ns1 = await client.get_namespace_index(_NS_IJT_SERVER)
        ns_r = await client.get_namespace_index(_NS_MACHINERY_RESULT)
        node = await client.nodes.root.get_child(
            ["0:Objects", f"{ns1}:TighteningSystem", f"{ns_r}:ResultManagement"]
        )
        await node.read_browse_name()
        return _STATUS_PASS, "ResultManagement node present"
    except (_OpcUaError, ValueError, AttributeError) as exc:
        return _STATUS_FAIL, str(exc)


async def check_asset_management(client: Any) -> tuple[str, str]:
    try:
        ns1 = await client.get_namespace_index(_NS_IJT_SERVER)
        ns_j = await client.get_namespace_index(_NS_IJT_BASE)
        node = await client.nodes.root.get_child(
            ["0:Objects", f"{ns1}:TighteningSystem", f"{ns_j}:AssetManagement"]
        )
        await node.read_browse_name()
        return _STATUS_PASS, "AssetManagement node present"
    except (_OpcUaError, ValueError, AttributeError) as exc:
        return _STATUS_FAIL, str(exc)


# -- Main runner ---------------------------------------------------------------


async def _run(endpoint: str, wait_s: float) -> int:
    host, port = _parse_endpoint(endpoint)
    checks: list[tuple[str, str, str]] = []  # (status, name, detail)
    failures = 0

    print("\nOPC UA IJT Server — Smoke Tests")
    print(f"  Endpoint : {endpoint}")
    print(f"  Timeout  : {wait_s:.0f}s")
    print("-" * 60)

    # 1. TCP reachability (polls until ready — useful right after docker start)
    status, detail = await check_tcp_port(host, port, wait_s)
    checks.append((status, "TCP port reachable", detail))
    if status != _STATUS_PASS:
        print(_result_line(status, "TCP port reachable", detail))
        print("\n[ABORT] Server not reachable — skipping OPC UA checks.")
        return 2

    # 2–8: OPC UA layer checks
    client = _Client(endpoint, timeout=30)
    try:
        status, detail = await check_opc_connection(client)
        checks.append((status, "OPC UA session", detail))
        if status != _STATUS_PASS:
            checks += [
                (_STATUS_SKIP, name, "server unreachable")
                for name in (
                    "Server CurrentTime",
                    "Namespace array",
                    "TighteningSystem node",
                    "Simulations node",
                    "ResultManagement node",
                    "AssetManagement node",
                )
            ]
        else:
            for fn, label in [
                (check_server_time, "Server CurrentTime"),
                (check_namespaces, "Namespace array"),
                (check_tightening_system, "TighteningSystem node"),
                (check_simulations_node, "Simulations node"),
                (check_result_management, "ResultManagement node"),
                (check_asset_management, "AssetManagement node"),
            ]:
                s, d = await fn(client)
                checks.append((s, label, d))
    finally:
        try:
            await client.disconnect()
        except (_OpcUaError, ConnectionError, OSError) as exc:
            print(
                f"[WARN] OPC UA client disconnect failed: {type(exc).__name__}: {exc}",
                file=sys.stderr,
            )

    # -- Report ----------------------------------------------------------------
    for status, name, detail in checks:
        print(_result_line(status, name, detail))
        if status == _STATUS_FAIL:
            failures += 1

    total = sum(1 for s, _, _ in checks if s != _STATUS_SKIP)
    passed = sum(1 for s, _, _ in checks if s == _STATUS_PASS)
    skipped = sum(1 for s, _, _ in checks if s == _STATUS_SKIP)

    print("-" * 60)
    summary = f"  {passed}/{total} passed"
    if skipped:
        summary += f", {skipped} skipped"
    if failures:
        summary += f", {failures} FAILED"
    print(summary)
    print()

    return 0 if failures == 0 else 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Smoke-test the OPC UA IJT Server Simulator."
    )
    parser.add_argument(
        "--endpoint",
        default="opc.tcp://localhost:40451",
        help="OPC UA endpoint URL (default: opc.tcp://localhost:40451)",
    )
    parser.add_argument(
        "--tcp-timeout",
        type=float,
        default=30.0,
        dest="tcp_timeout",
        help="Seconds to wait for the TCP port to open (default: 30). "
             "Does not affect the OPC UA session timeout (fixed at 30 s).",
    )
    args = parser.parse_args()
    sys.exit(asyncio.run(_run(args.endpoint, args.tcp_timeout)))


if __name__ == "__main__":
    main()
