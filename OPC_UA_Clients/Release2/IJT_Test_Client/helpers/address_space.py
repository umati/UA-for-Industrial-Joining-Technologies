"""
helpers/address_space.py — Higher-level OPC UA address space introspection utilities.

Provides composable helpers for reading properties, verifying mandatory structure,
and finding type instances. All functions use asyncio.wait_for timeouts to prevent
hangs. All errors are handled gracefully — callers get None/empty rather than exceptions.
"""

from __future__ import annotations

import asyncio
import logging

from helpers.namespaces import RefTypes
from helpers.node_discovery import (
    _browse_refs,
    _node_from_ref,
    find_child_by_browse_name,
    get_children_by_reference,
    get_type_definition,
)

logger = logging.getLogger(__name__)


async def read_property_value(node, property_name: str, ns_index: int, timeout: float = 10.0) -> object | None:
    """
    Read the Value of a Property child identified by (ns_index, property_name).

    Locates the property by browse name under node, then reads its Value attribute.
    Returns None if the property child does not exist or any error occurs.

    Args:
        node: Parent OPC UA Node.
        property_name: Local name of the property's BrowseName.
        ns_index: Namespace index of the property's BrowseName.
        timeout: Maximum seconds for the entire operation.
    """
    try:
        property_node = await find_child_by_browse_name(node, property_name, ns_index, timeout=timeout)
        if property_node is None:
            return None
        return await asyncio.wait_for(property_node.read_value(), timeout=timeout)
    except Exception as exc:
        logger.debug("read_property_value('%s'): %s", property_name, exc)
        return None


async def read_variable_value_safe(node, timeout: float = 10.0) -> object | None:
    """
    Read the Value attribute of node, returning None on any error.

    Args:
        node: OPC UA Node to read.
        timeout: Maximum seconds to wait for the server response.
    """
    try:
        return await asyncio.wait_for(node.read_value(), timeout=timeout)
    except Exception as exc:
        logger.debug("read_variable_value_safe: %s", exc)
        return None


async def read_node_class(node, timeout: float = 5.0) -> int | None:
    """
    Read the NodeClass attribute of node, returning None on any error.

    Args:
        node: OPC UA Node to inspect.
        timeout: Maximum seconds to wait for the server response.
    """
    try:
        return await asyncio.wait_for(node.read_node_class(), timeout=timeout)
    except Exception as exc:
        logger.debug("read_node_class: %s", exc)
        return None


async def verify_mandatory_children(node, required: list[tuple[str, int]], timeout: float = 15.0) -> list[str]:
    """
    Check that each (browse_name, ns_index) in required exists as a child of node.

    Browses node's hierarchical children once and checks each required name
    against the result set. This avoids N individual browse calls.

    Args:
        node: Parent OPC UA Node to inspect.
        required: List of (local_name, ns_index) tuples that must be present.
        timeout: Maximum seconds for the initial browse call.

    Returns:
        A list of missing child names (empty list means all present).
    """
    try:
        refs = await _browse_refs(node, timeout=timeout)
    except Exception as exc:
        logger.debug("verify_mandatory_children: browse failed: %s", exc)
        # Cannot browse — report all as missing
        return [name for name, _ in required]

    present: set[tuple[str, int]] = {(ref.BrowseName.Name, ref.BrowseName.NamespaceIndex) for ref in refs}
    return [name for name, ns in required if (name, ns) not in present]


async def find_all_instances_of_type(
    client,
    objects_node,
    type_node_id,
    max_depth: int = 3,
    timeout: float = 20.0,
) -> list:
    """
    Traverse the address space from objects_node and collect all nodes whose
    HasTypeDefinition matches type_node_id.

    Args:
        client: asyncua Client (used to resolve the OPC UA namespace index).
        objects_node: Root Node to start traversal from (typically Objects folder).
        type_node_id: ua.NodeId of the type to match.
        max_depth: Maximum levels of hierarchy to descend.
        timeout: Maximum seconds for each individual browse call.

    Returns:
        List of matching OPC UA Node objects.
    """
    ns_opc_ua = await client.get_namespace_index("http://opcfoundation.org/UA/")
    matches: list = []
    visited: set[str] = set()

    async def _traverse(current_node, depth: int) -> None:
        node_id_str = str(current_node.nodeid)
        if node_id_str in visited or depth > max_depth:
            return
        visited.add(node_id_str)

        type_def = await get_type_definition(current_node, ns_opc_ua)
        if type_def is not None:
            if (
                type_def.Identifier == type_node_id.Identifier
                and type_def.NamespaceIndex == type_node_id.NamespaceIndex
            ):
                matches.append(current_node)

        if depth < max_depth:
            try:
                refs = await _browse_refs(current_node, timeout=timeout)
            except Exception as exc:
                logger.debug("find_all_instances_of_type: browse failed at depth %d: %s", depth, exc)
                return
            for ref in refs:
                child = _node_from_ref(current_node, ref.NodeId)
                await _traverse(child, depth + 1)

    await _traverse(objects_node, 0)
    return matches


async def read_browse_name(node, timeout: float = 5.0) -> tuple[str, int] | None:
    """
    Read the BrowseName attribute of node.

    Args:
        node: OPC UA Node to inspect.
        timeout: Maximum seconds to wait for the server response.

    Returns:
        (name, ns_index) tuple, or None on error.
    """
    try:
        bn = await asyncio.wait_for(node.read_browse_name(), timeout=timeout)
        return (bn.Name, bn.NamespaceIndex)
    except Exception as exc:
        logger.debug("read_browse_name: %s", exc)
        return None


async def read_display_name(node, timeout: float = 5.0) -> str | None:
    """
    Read the DisplayName attribute of node, returning its Text field.

    Args:
        node: OPC UA Node to inspect.
        timeout: Maximum seconds to wait for the server response.

    Returns:
        Display name string, or None on error.
    """
    try:
        dn = await asyncio.wait_for(node.read_display_name(), timeout=timeout)
        return dn.Text
    except Exception as exc:
        logger.debug("read_display_name: %s", exc)
        return None


async def check_node_exists(node, timeout: float = 5.0) -> bool:
    """
    Verify that node is accessible by attempting to read its BrowseName.

    Args:
        node: OPC UA Node to probe.
        timeout: Maximum seconds to wait for the server response.

    Returns:
        True if the node is reachable, False otherwise.
    """
    result = await read_browse_name(node, timeout=timeout)
    return result is not None


async def get_property_nodes(node, timeout: float = 10.0) -> list:
    """
    Return all child nodes reachable via HasProperty references from node.

    Args:
        node: Parent OPC UA Node.
        timeout: Maximum seconds for the browse call.

    Returns:
        List of OPC UA Node objects (may be empty).
    """
    try:
        return await asyncio.wait_for(
            get_children_by_reference(node, RefTypes.HAS_PROPERTY),
            timeout=timeout,
        )
    except Exception as exc:
        logger.debug("get_property_nodes: %s", exc)
        return []


async def get_component_nodes(node, timeout: float = 10.0) -> list:
    """
    Return all child nodes reachable via HasComponent references from node.

    Args:
        node: Parent OPC UA Node.
        timeout: Maximum seconds for the browse call.

    Returns:
        List of OPC UA Node objects (may be empty).
    """
    try:
        return await asyncio.wait_for(
            get_children_by_reference(node, RefTypes.HAS_COMPONENT),
            timeout=timeout,
        )
    except Exception as exc:
        logger.debug("get_component_nodes: %s", exc)
        return []
