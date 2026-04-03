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
    python tests/smoke_test.py --timeout 60           # longer start-up wait

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

# asyncua is a required dependency — import its exception base at module level
# so all check functions can catch specific OPC UA errors.
try:
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

_PASS = "PASS"
_FAIL = "FAIL"
_SKIP = "SKIP"


def _result_line(status: str, name: str, detail: str = "") -> str:
    icon = {"PASS": "[OK]", "FAIL": "[FAIL]", "SKIP": "[SKIP]"}[status]
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
    """Return (host, port) from 'opc.tcp://host:port'."""
    without_scheme = endpoint.replace("opc.tcp://", "")
    host, _, port_str = without_scheme.partition(":")
    return host, int(port_str or "40451")


# -- Individual checks ---------------------------------------------------------


async def check_tcp_port(host: str, port: int, wait_s: float) -> tuple[str, str]:
    """Poll TCP port until the server accepts connections or timeout."""
    deadline = time.monotonic() + wait_s
    while time.monotonic() < deadline:
        if _port_open(host, port, timeout=1.0):
            return _PASS, f"port {port} is open"
        await asyncio.sleep(1.0)
    return _FAIL, f"port {port} not reachable after {wait_s:.0f}s"


async def check_opc_connection(client: Any) -> tuple[str, str]:
    """Try to establish an OPC UA session, retrying briefly after TCP is open."""
    last_exc: Exception | None = None
    for attempt in range(5):
        try:
            await client.connect()
            return _PASS, "OPC UA session established"
        except (_OpcUaError, ConnectionError, TimeoutError, OSError) as exc:
            last_exc = exc
            if attempt < 4:
                await asyncio.sleep(3)
    return _FAIL, str(last_exc)


async def check_server_time(client: Any) -> tuple[str, str]:
    try:
        node = client.get_node("ns=0;i=2258")  # Server/ServerStatus/CurrentTime
        val = await node.read_value()
        return _PASS, f"CurrentTime = {val}"
    except (_OpcUaError, AttributeError) as exc:
        return _FAIL, str(exc)


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
            return _FAIL, "missing namespaces: " + ", ".join(missing)
        return _PASS, f"{len(ns_array)} namespaces, all IJT URIs present"
    except (_OpcUaError, AttributeError) as exc:
        return _FAIL, str(exc)


async def check_tightening_system(client: Any) -> tuple[str, str]:
    try:
        ns1 = await client.get_namespace_index(_NS_IJT_SERVER)
        node = await client.nodes.root.get_child(
            ["0:Objects", f"{ns1}:TighteningSystem"]
        )
        bn = await node.read_browse_name()
        return _PASS, f"TighteningSystem found ({bn})"
    except (_OpcUaError, ValueError, AttributeError) as exc:
        return _FAIL, str(exc)


async def check_simulations_node(client: Any) -> tuple[str, str]:
    try:
        ns1 = await client.get_namespace_index(_NS_IJT_SERVER)
        node = await client.nodes.root.get_child(
            ["0:Objects", f"{ns1}:TighteningSystem", f"{ns1}:Simulations"]
        )
        children = await node.get_children()
        return _PASS, f"Simulations node has {len(children)} method(s)"
    except (_OpcUaError, ValueError, AttributeError) as exc:
        return _FAIL, str(exc)


async def check_result_management(client: Any) -> tuple[str, str]:
    try:
        ns1 = await client.get_namespace_index(_NS_IJT_SERVER)
        ns_r = await client.get_namespace_index(_NS_MACHINERY_RESULT)
        node = await client.nodes.root.get_child(
            ["0:Objects", f"{ns1}:TighteningSystem", f"{ns_r}:ResultManagement"]
        )
        await node.read_browse_name()
        return _PASS, "ResultManagement node present"
    except (_OpcUaError, ValueError, AttributeError) as exc:
        return _FAIL, str(exc)


async def check_asset_management(client: Any) -> tuple[str, str]:
    try:
        ns1 = await client.get_namespace_index(_NS_IJT_SERVER)
        ns_j = await client.get_namespace_index(_NS_IJT_BASE)
        node = await client.nodes.root.get_child(
            ["0:Objects", f"{ns1}:TighteningSystem", f"{ns_j}:AssetManagement"]
        )
        await node.read_browse_name()
        return _PASS, "AssetManagement node present"
    except (_OpcUaError, ValueError, AttributeError) as exc:
        return _FAIL, str(exc)


# -- Main runner ---------------------------------------------------------------


async def _run(endpoint: str, wait_s: float) -> int:
    try:
        from asyncua import Client
    except ImportError:
        print("ERROR: 'asyncua' not installed.  Run: pip install asyncua")
        return 1

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
    if status != _PASS:
        print(_result_line(status, "TCP port reachable", detail))
        print("\n[ABORT] Server not reachable — skipping OPC UA checks.")
        return 2

    # 2–8: OPC UA layer checks
    client = Client(endpoint, timeout=30)
    try:
        status, detail = await check_opc_connection(client)
        checks.append((status, "OPC UA session", detail))
        if status != _PASS:
            checks += [
                (_SKIP, name, "server unreachable")
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
        with contextlib.suppress(_OpcUaError, ConnectionError, OSError):
            await client.disconnect()

    # -- Report ----------------------------------------------------------------
    for status, name, detail in checks:
        print(_result_line(status, name, detail))
        if status == _FAIL:
            failures += 1

    total = sum(1 for s, _, _ in checks if s != _SKIP)
    passed = sum(1 for s, _, _ in checks if s == _PASS)
    skipped = sum(1 for s, _, _ in checks if s == _SKIP)

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
        "--timeout",
        type=float,
        default=30.0,
        help="Seconds to wait for TCP port to open (default: 30)",
    )
    args = parser.parse_args()
    sys.exit(asyncio.run(_run(args.endpoint, args.timeout)))


if __name__ == "__main__":
    main()
