"""
OPC UA IJT Tightening Test Framework — Async node discovery utilities.
Provides reusable helpers for:
  - Finding the JoiningSystem by type definition (never by browse name).
  - Browsing children by BrowseName (name + namespace index pair).
  - Traversing arbitrary reference types.
  - Checking HasInterface capabilities.
  - Finding method nodes.
All functions are async and work with asyncua Client/Node objects.
Namespace indices must be resolved by callers via ns_indices dict from conftest.

Design rule: never call get_children() directly — it can hang on nodes with
complex or large subtrees. Use _browse_refs() which calls get_references() with
HierarchicalReferences (id=33) and an asyncio.wait_for timeout instead.
"""

import asyncio
import logging

from asyncua import ua
from asyncua.common.node import Node as UANode

from helpers.namespaces import NS_IJT_BASE, NS_OPC_UA, IJTTypes, RefTypes

logger = logging.getLogger(__name__)
_BROWSE_TIMEOUT = 15.0  # seconds — applies to all browse/reference calls


def _ref_type_nodeid(ref_type_id: int) -> ua.NodeId:
    """Return a namespace-0 NodeId for a reference type id."""
    return ua.NodeId(ref_type_id, 0)


def _node_from_ref(source_node: UANode, expanded_nodeid) -> UANode:
    """Create a Node bound to the same session as source_node from a ref NodeId."""
    return UANode(source_node.session, expanded_nodeid)


async def _browse_refs(node: UANode, timeout: float = _BROWSE_TIMEOUT) -> list:
    """
    Browse HierarchicalReferences forward from node without reading node values.
    Uses asyncio.wait_for to prevent hanging on slow or unresponsive server nodes.
    Returns a list of ReferenceDescription objects (BrowseName, NodeId, NodeClass).
    HierarchicalReferences reference type id = 33 (ns=0, defined by OPC UA specification).
    """
    return await asyncio.wait_for(
        node.get_references(
            refs=33,  # HierarchicalReferences (OPC UA Core NodeSet, ns=0, id=33)
            direction=ua.BrowseDirection.Forward,
            includesubtypes=True,
            nodeclassmask=ua.NodeClass.Unspecified,
        ),
        timeout=timeout,
    )


async def find_joining_system(client) -> UANode | None:
    """
    Browse the Objects folder to find the JoiningSystem node.
    Discovery is by HasTypeDefinition = JoiningSystemType (IJT Base ns, local id=1005).
    The root browse name is implementation-defined and is never used for discovery.
    Returns the JoiningSystem Node or None if not found.
    """
    # Resolve from the outer Client object — the only place get_namespace_index exists.
    # node.session in asyncua 1.2+ is the internal AbstractSession, not the outer Client, so resolution
    # must happen here and be passed down explicitly.
    ns_opc_ua = await client.get_namespace_index(NS_OPC_UA)
    ns_ijt = await client.get_namespace_index(NS_IJT_BASE)
    target_type_id = ua.NodeId(IJTTypes.JOINING_SYSTEM_TYPE, ns_ijt)
    objects = client.get_objects_node()
    try:
        refs = await _browse_refs(objects)
    except Exception:  # noqa: BLE001 — broad catch intentional: server may raise any asyncua error
        return None  # Objects node unreachable — server has non-standard address space
    children = [_node_from_ref(objects, r.NodeId) for r in refs]
    for child in children:
        type_def = await get_type_definition(child, ns_opc_ua)
        if type_def is not None and type_def == target_type_id:
            return child
    # Also search one level deeper (in case the system is inside a folder)
    for child in children:
        try:
            sub_refs = await _browse_refs(child)
        except Exception:  # nosec B112
            # Deliberately continue to try the next child node.
            continue
        for sr in sub_refs:
            gc = _node_from_ref(child, sr.NodeId)
            type_def = await get_type_definition(gc, ns_opc_ua)
            if type_def is not None and type_def == target_type_id:
                return gc
    return None


async def find_child_by_browse_name(
    parent_node: UANode, name: str, ns_index: int, timeout: float = _BROWSE_TIMEOUT
) -> UANode | None:
    """
    Find a direct child of parent_node whose BrowseName matches (ns_index, name).
    Uses get_references() with a timeout instead of get_children() to avoid hangs.
    Returns the matching child Node or None if not found.
    """
    try:
        refs = await _browse_refs(parent_node, timeout=timeout)
    except Exception:  # noqa: BLE001 — broad catch intentional: server may raise any asyncua error
        return None  # Parent node unreachable — caller receives None and skips
    for ref in refs:
        if ref.BrowseName.Name == name and ref.BrowseName.NamespaceIndex == ns_index:
            return _node_from_ref(parent_node, ref.NodeId)
    return None


async def browse_folder_instances(folder_node: UANode, timeout: float = _BROWSE_TIMEOUT) -> list:
    """
    Return a list of (browse_name_str, Node) tuples for all children of folder_node.
    browse_name_str is formatted as "{ns_index}:{Name}" (e.g. "3:MyController").
    Useful for iterating asset instances without assuming their names.
    """
    results: list[tuple[str, UANode]] = []
    try:
        refs = await _browse_refs(folder_node, timeout=timeout)
    except Exception:  # noqa: BLE001 — broad catch intentional: server may raise any asyncua error
        return results  # Folder unreachable — return whatever was collected so far
    for ref in refs:
        results.append(
            (
                f"{ref.BrowseName.NamespaceIndex}:{ref.BrowseName.Name}",
                _node_from_ref(folder_node, ref.NodeId),
            )
        )
    return results


async def get_type_definition(node: UANode, ns_opc_ua: int = 0):
    """
    Return the HasTypeDefinition NodeId for the given node, or None.
    ns_opc_ua defaults to 0 — guaranteed by OPC UA specification §8.2.3.
    Pass ns_indices[NS_OPC_UA] explicitly when available for strictness.
    """
    try:
        refs = await node.get_references(
            refs=_ref_type_nodeid(RefTypes.HAS_TYPE_DEFINITION),  # ns=0; all OPC UA standard refs are in namespace 0
            direction=ua.BrowseDirection.Forward,
            includesubtypes=False,
            nodeclassmask=ua.NodeClass.Unspecified,
        )
        if refs:
            return refs[0].NodeId
    except Exception as exc:
        logger.debug("get_type_definition failed: %s", exc)
    return None


async def get_interface_types(node: UANode, ns_opc_ua: int = 0) -> list:
    """
    Return a list of NodeIds from HasInterface references on node.
    ns_opc_ua defaults to 0 — guaranteed by OPC UA specification §8.2.3.
    """
    try:
        refs = await node.get_references(
            refs=_ref_type_nodeid(RefTypes.HAS_INTERFACE),  # ns=0; all OPC UA standard refs are in namespace 0
            direction=ua.BrowseDirection.Forward,
            includesubtypes=True,
            nodeclassmask=ua.NodeClass.Unspecified,
        )
        return [ref.NodeId for ref in refs]
    except Exception:  # noqa: BLE001 — broad catch intentional: server may raise any asyncua error
        return []  # Node has no HasInterface references or is unreachable


async def has_interface(node: UANode, ns_index: int, type_local_id: int, ns_opc_ua: int = 0) -> bool:
    """
    Check whether node has a HasInterface reference pointing to the given type.
    ns_opc_ua defaults to 0 — guaranteed by OPC UA specification §8.2.3.
    """
    target = ua.NodeId(type_local_id, ns_index)  # type: ignore[arg-type]
    iface_types = await get_interface_types(node, ns_opc_ua)
    for nid in iface_types:
        if nid.Identifier == target.Identifier and nid.NamespaceIndex == target.NamespaceIndex:
            return True
    return False


async def get_associated_assets(node: UANode, ns_opc_ua: int = 0) -> list:
    """
    Return a list of Nodes referenced via AssociatedWith from node.
    ns_opc_ua defaults to 0 — guaranteed by OPC UA specification §8.2.3.
    """
    try:
        refs = await node.get_references(
            refs=_ref_type_nodeid(RefTypes.ASSOCIATED_WITH),  # ns=0; all OPC UA standard refs are in namespace 0
            direction=ua.BrowseDirection.Forward,
            includesubtypes=True,
            nodeclassmask=ua.NodeClass.Unspecified,
        )
        return [_node_from_ref(node, ref.NodeId) for ref in refs]
    except Exception:  # noqa: BLE001 — broad catch intentional: server may raise any asyncua error
        return []  # Node has no AssociatedWith references or is unreachable


async def get_children_by_reference(node: UANode, ref_type_id: int, ns_opc_ua: int = 0) -> list:
    """
    Return Nodes reachable from node via the given reference type.
    ns_opc_ua defaults to 0 — guaranteed by OPC UA specification §8.2.3.
    """
    try:
        refs = await node.get_references(
            refs=_ref_type_nodeid(ref_type_id),  # ns=0 for all standard OPC UA refs
            direction=ua.BrowseDirection.Forward,
            includesubtypes=True,
            nodeclassmask=ua.NodeClass.Unspecified,
        )
        return [_node_from_ref(node, ref.NodeId) for ref in refs]
    except Exception:  # noqa: BLE001 — broad catch intentional: server may raise any asyncua error
        return []  # Reference type not present on node or node is unreachable


async def find_method_node(parent: UANode, method_browse_name: str, method_ns_index: int) -> UANode | None:
    """
    Find a method child of parent matching the given browse name and namespace index.
    Returns the method Node or None if not found.
    """
    return await find_child_by_browse_name(parent, method_browse_name, method_ns_index)


async def get_add_in_nodes(node: UANode, ns_opc_ua: int = 0) -> list:
    """
    Return Nodes reachable via HasAddIn from the given node.
    ns_opc_ua defaults to 0 — guaranteed by OPC UA specification §8.2.3.
    """
    return await get_children_by_reference(node, RefTypes.HAS_ADD_IN, ns_opc_ua)


async def find_child_by_reference_type(
    parent_node: UANode,
    name: str,
    ns_index: int,
    ref_type_id: int,
    ns_opc_ua: int = 0,
    timeout: float = _BROWSE_TIMEOUT,
) -> UANode | None:
    """
    Find a direct child reachable from parent_node via a specific reference type whose
    BrowseName matches (ns_index, name).

    Unlike find_child_by_browse_name (which uses HierarchicalReferences and matches any
    reference type), this function strictly filters on ref_type_id so callers can assert
    that the expected OPC UA reference type is used — not merely that the child exists.

    Example — verify PhysicalQuantity is reached via HasComponent (not HasProperty):
        node = await find_child_by_reference_type(
            variable_node, "PhysicalQuantity", ns_ijt,
            RefTypes.HAS_COMPONENT
        )
        assert node is not None, "PhysicalQuantity must be HasComponent, not HasProperty"
    """
    try:
        refs = await asyncio.wait_for(
            parent_node.get_references(
                refs=_ref_type_nodeid(ref_type_id),
                direction=ua.BrowseDirection.Forward,
                includesubtypes=False,
                nodeclassmask=ua.NodeClass.Unspecified,
            ),
            timeout=timeout,
        )
    except Exception:  # noqa: BLE001
        return None
    for ref in refs:
        if ref.BrowseName.Name == name and ref.BrowseName.NamespaceIndex == ns_index:
            return _node_from_ref(parent_node, ref.NodeId)
    return None


async def find_method_set(
    parent_node: UANode,
    ns_di: int,
    ns_ijt: int | None = None,
    ns_app: int | None = None,
) -> UANode | None:
    """
    Locate the MethodSet child of parent_node.

    Tries namespace candidates in order to maximise vendor interoperability:
    1. ns_di  — DI-specification-conformant servers use the DI namespace browse name
    2. ns_ijt — the IJT Server Simulator uses IJT Base namespace for the MethodSet browse name
    3. ns_app — application-specific namespace as a last-resort fallback

    Confirmed from live simulator browse (QualifiedName(NamespaceIndex=7, Name='MethodSet')):
    the NodeId is in ns_app but the BrowseName NamespaceIndex is ns_ijt.
    """
    for ns in (ns_di, ns_ijt, ns_app):
        if ns is not None:
            ms = await find_child_by_browse_name(parent_node, "MethodSet", ns)
            if ms is not None:
                return ms
    return None


async def read_tool_product_instance_uri(client, ns_ijt: int, ns_di: int, ns_app: int | None = None) -> str:
    """
    Read ProductInstanceUri from the first tool in AssetManagement/Assets/Tools.

    Navigation path: JoiningSystem → AssetManagement → Assets → Tools →
    <first tool instance> → Identification → ProductInstanceUri.

    This is the ProductInstanceUri used by all JoiningProcessManagement and
    AssetManagement method calls per IJT spec and confirmed by the Web Client
    reference implementation.

    Returns empty string if any navigation step fails.
    """
    try:
        js = await find_joining_system(client)
        if js is None:
            return ""
        am = await find_child_by_browse_name(js, "AssetManagement", ns_ijt)
        if am is None:
            return ""
        assets = await find_child_by_browse_name(am, "Assets", ns_ijt)
        if assets is None:
            return ""
        tools_folder = await find_child_by_browse_name(assets, "Tools", ns_ijt)
        if tools_folder is None:
            return ""
        # Get first tool instance — do not hardcode the instance name; it varies by server
        tool_refs = await _browse_refs(tools_folder)
        if not tool_refs:
            return ""
        first_tool = _node_from_ref(tools_folder, tool_refs[0].NodeId)
        ident = await find_child_by_browse_name(first_tool, "Identification", ns_di)
        if ident is None:
            return ""
        # ProductInstanceUri browse name uses ns_di on standard servers
        pi_node = await find_child_by_browse_name(ident, "ProductInstanceUri", ns_di)
        if pi_node is None and ns_app is not None:
            pi_node = await find_child_by_browse_name(ident, "ProductInstanceUri", ns_app)
        if pi_node is None:
            return ""
        value = await asyncio.wait_for(pi_node.read_value(), timeout=_BROWSE_TIMEOUT)
        return str(value) if value is not None else ""
    except Exception:  # noqa: BLE001
        return ""
