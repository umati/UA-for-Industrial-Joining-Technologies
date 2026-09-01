"""Read-only inventory of the IJT server address space."""

from __future__ import annotations

import asyncio
import json
from collections import deque
from pathlib import Path
from typing import Any

from asyncua import Client, ua
from asyncua.common.node import Node

from helpers.connection_security import ConnectionSecurity, apply_connection_security
from helpers.node_discovery import find_joining_system


def _namespace_uri(namespace_array: list[str], index: int) -> str:
    return namespace_array[index] if 0 <= index < len(namespace_array) else ""


async def _server_nodes(client: Client, *, timeout: float, max_nodes: int) -> tuple[list[dict[str, Any]], list[str]]:
    joining_system = await find_joining_system(client)
    if joining_system is None:
        raise RuntimeError("JoiningSystem node was not found")

    namespace_array = await asyncio.wait_for(client.get_namespace_array(), timeout=timeout)
    root_name = await asyncio.wait_for(joining_system.read_browse_name(), timeout=timeout)
    pending = deque([(joining_system, root_name.Name)])
    visited: set[str] = set()
    nodes: list[dict[str, Any]] = []
    warnings: list[str] = []

    while pending:
        node, path = pending.popleft()
        node_key = str(node.nodeid)
        if node_key in visited:
            continue
        if len(visited) >= max_nodes:
            raise RuntimeError(f"Address-space inventory exceeded the safety limit of {max_nodes} nodes")
        visited.add(node_key)

        try:
            # Single Browse call returns BrowseName, NodeClass, TypeDefinition, and
            # NodeId for every child — no redundant individual Read calls needed.
            references = await asyncio.wait_for(
                node.get_references(
                    refs=ua.NodeId(33, 0),
                    direction=ua.BrowseDirection.Forward,
                    includesubtypes=True,
                    nodeclassmask=ua.NodeClass.Unspecified,
                ),
                timeout=timeout,
            )
        except Exception as exc:  # noqa: BLE001 - preserve partial read-only evidence
            warnings.append(f"{path}: {type(exc).__name__}: {exc}")
            continue

        for ref in references:
            child_path = f"{path}/{ref.BrowseName.Name}"
            ns_idx = ref.BrowseName.NamespaceIndex
            type_def = str(ref.TypeDefinition) if ref.TypeDefinition else ""
            nodes.append(
                {
                    "path": child_path,
                    "node_id": str(ref.NodeId),
                    "node_class": ref.NodeClass.name,
                    "browse_name": {
                        "name": ref.BrowseName.Name,
                        "namespace_index": ns_idx,
                        "namespace_uri": _namespace_uri(namespace_array, ns_idx),
                    },
                    "type_definition": type_def,
                }
            )
            pending.append((Node(node.session, ref.NodeId), child_path))

    return nodes, warnings


async def build_model_inventory(
    endpoint: str,
    *,
    timeout: float = 15.0,
    max_nodes: int = 10_000,
    security: ConnectionSecurity | None = None,
) -> dict[str, Any]:
    """Build a complete read-only contract and server inventory."""
    client = Client(url=endpoint, timeout=timeout)
    if security is not None:
        await apply_connection_security(client, security)
    await client.connect()
    try:
        nodes, warnings = await _server_nodes(client, timeout=timeout, max_nodes=max_nodes)
    finally:
        await client.disconnect()

    return {
        "schema_version": 1,
        "endpoint": endpoint,
        "read_only": True,
        "complete": not warnings,
        "contract_inventory": None,
        "server_inventory": {
            "root": "JoiningSystem",
            "node_count": len(nodes),
            "warnings": warnings,
            "nodes": nodes,
        },
    }


def write_model_inventory(
    endpoint: str,
    output_path: Path,
    *,
    timeout: float = 15.0,
    security: ConnectionSecurity | None = None,
) -> dict[str, Any]:
    """Generate and persist one read-only inventory."""
    inventory = asyncio.run(build_model_inventory(endpoint, timeout=timeout, security=security))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    return inventory
