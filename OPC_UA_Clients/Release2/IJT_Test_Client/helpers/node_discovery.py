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
import os
from collections import Counter

from asyncua import ua
from asyncua.common.node import Node as UANode

from helpers.namespaces import NS_IJT_BASE, NS_OPC_UA, IJTTypes, RefTypes

logger = logging.getLogger(__name__)
_BROWSE_TIMEOUT = 15.0  # seconds — applies to all browse/reference calls


class ProductInstanceUriExposureUnavailable(LookupError):
    def __init__(self, reason_code: str, diagnostic: str) -> None:
        super().__init__(diagnostic)
        self.reason_code = reason_code


def _handle_discovery_error(exc: Exception) -> None:
    """Keep communication failures distinct from optional address-space absence."""
    if isinstance(exc, (OSError, TimeoutError)):
        raise exc
    if isinstance(exc, ua.UaStatusCodeError) and exc.code in {
        ua.StatusCodes.BadCommunicationError,
        ua.StatusCodes.BadConnectionClosed,
        ua.StatusCodes.BadNoCommunication,
        ua.StatusCodes.BadNotConnected,
        ua.StatusCodes.BadSecureChannelClosed,
        ua.StatusCodes.BadSecureChannelIdInvalid,
        ua.StatusCodes.BadServerNotConnected,
        ua.StatusCodes.BadSessionClosed,
        ua.StatusCodes.BadSessionIdInvalid,
        ua.StatusCodes.BadShutdown,
        ua.StatusCodes.BadTimeout,
    }:
        raise exc
    logger.warning("Node discovery failed; optional lookup unavailable: %s", exc)


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
    except Exception as exc:  # noqa: BLE001
        _handle_discovery_error(exc)
        return None
    children = [_node_from_ref(objects, r.NodeId) for r in refs]
    for child in children:
        type_def = await get_type_definition(child, ns_opc_ua)
        if type_def is not None and type_def == target_type_id:
            return child
    # Also search one level deeper (in case the system is inside a folder)
    for child in children:
        try:
            sub_refs = await _browse_refs(child)
        except Exception as exc:  # noqa: BLE001
            _handle_discovery_error(exc)
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
    except Exception as exc:  # noqa: BLE001
        _handle_discovery_error(exc)
        return None
    for ref in refs:
        if ref.BrowseName.Name == name and ref.BrowseName.NamespaceIndex == ns_index:
            return _node_from_ref(parent_node, ref.NodeId)
    return None


async def find_child_by_browse_name_any(
    parent_node: UANode,
    name: str,
    ns_indexes: list[int | None] | tuple[int | None, ...],
    timeout: float = _BROWSE_TIMEOUT,
) -> UANode | None:
    """
    Find a direct child by BrowseName across multiple namespace indexes.

    Some servers use the specification namespace for the BrowseName, while
    generated simulator nodes can use an application namespace for the same
    browse-name text. This helper keeps callers explicit about accepted
    namespaces without duplicating fallback loops.
    """
    seen: set[int] = set()
    for ns_index in ns_indexes:
        if ns_index is None or ns_index in seen:
            continue
        seen.add(ns_index)
        child = await find_child_by_browse_name(parent_node, name, ns_index, timeout=timeout)
        if child is not None:
            return child
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
    except Exception as exc:  # noqa: BLE001
        _handle_discovery_error(exc)
        return results
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
        _handle_discovery_error(exc)
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
    except Exception as exc:  # noqa: BLE001
        _handle_discovery_error(exc)
        return []


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
    except Exception as exc:  # noqa: BLE001
        _handle_discovery_error(exc)
        return []


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
    except Exception as exc:  # noqa: BLE001
        _handle_discovery_error(exc)
        return []


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
    except Exception as exc:  # noqa: BLE001
        _handle_discovery_error(exc)
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


async def read_exposed_product_instance_uris(client, ns_ijt: int) -> frozenset[str]:
    """Read PIUs throughout Objects, not merely the selected JoiningSystem's Assets."""
    deadline = asyncio.get_running_loop().time() + 60.0
    pending = [client.get_objects_node()]
    visited = set()
    identities: set[str] = set()
    while pending:
        if asyncio.get_running_loop().time() >= deadline:
            raise ProductInstanceUriExposureUnavailable(
                "piu_exposure_budget_exhausted",
                "Asset PIU discovery did not complete within its bounded observation period",
            )
        node = pending.pop()
        if node.nodeid in visited:
            continue
        visited.add(node.nodeid)
        for ref in await _browse_refs(node):
            if getattr(ref.NodeId, "ServerIndex", 0):
                raise ProductInstanceUriExposureUnavailable(
                    "piu_exposure_remote_reference",
                    "Remote address-space references prevent complete PIU exposure discovery",
                )
            child = _node_from_ref(node, ref.NodeId)
            if ref.BrowseName.Name == "ProductInstanceUri" and ref.NodeClass == ua.NodeClass.Variable:
                value = await asyncio.wait_for(child.read_value(), timeout=_BROWSE_TIMEOUT)
                if not isinstance(value, str) or not value:
                    raise ProductInstanceUriExposureUnavailable(
                        "piu_exposure_value_unavailable", "An exposed ProductInstanceUri is missing or invalid"
                    )
                identities.add(value)
            if ref.NodeClass in (ua.NodeClass.Object, ua.NodeClass.Variable):
                pending.append(child)
    return frozenset(identities)


async def _read_asset_ready_rank(asset, ns_ijt: int, ns_app: int | None = None) -> int | None:
    """Return readiness rank for an asset (0=Connected&Enabled, 1=partial True, 2=omitted, None=not ready)."""
    params = await find_child_by_browse_name_any(asset, "Parameters", (ns_ijt, ns_app))
    if params is None:
        return 2

    async def _read_bool(name: str) -> bool | None:
        child = await find_child_by_browse_name_any(params, name, (ns_ijt, ns_app))
        if child is None:
            return None
        val = await asyncio.wait_for(child.read_value(), timeout=_BROWSE_TIMEOUT)
        return val if isinstance(val, bool) else None

    connected = await _read_bool("Connected")
    enabled = await _read_bool("Enabled")
    if connected is False or enabled is False:
        return None
    if connected is True and enabled is True:
        return 0
    if connected is True or enabled is True:
        return 1
    return 2


async def _tool_process_rank(js, piu: str, ns_ijt: int, ns_app: int | None = None) -> int:
    """Return 0 when Tool advertises >=1 joining process, else 1 (or 0 when JPM is absent)."""
    try:
        jpm = await find_child_by_browse_name_any(js, "JoiningProcessManagement", (ns_ijt, ns_app))
        if jpm is None or not hasattr(jpm, "call_method"):
            return 0
        gjpl = await find_child_by_browse_name_any(jpm, "GetJoiningProcessList", (ns_ijt, ns_app))
        if gjpl is None or not hasattr(gjpl, "nodeid"):
            return 0
        out = await asyncio.wait_for(
            jpm.call_method(gjpl.nodeid, ua.Variant(piu, ua.VariantType.String)),
            timeout=_BROWSE_TIMEOUT,
        )
        procs = (
            out[0]
            if isinstance(out, (list, tuple)) and out and isinstance(out[0], (list, tuple))
            else (out if isinstance(out, (list, tuple)) else [])
        )
        return 0 if procs else 1
    except Exception:  # noqa: BLE001
        return 0


async def read_tool_product_instance_uri(
    client,
    ns_ijt: int,
    ns_di: int,
    ns_app: int | None = None,
    *,
    expected_tool_uri: str | None = None,
    policy: str | None = None,
) -> str:
    """
    Resolve a Tool ProductInstanceUri using an explicit URI or the active Tool selection policy.

    Navigation path: JoiningSystem → AssetManagement → Assets → Tools →
    <selected tool instance> → Identification → ProductInstanceUri.

    Policies when ``expected_tool_uri`` is not set:
      - ``first_ready`` (default): selects the first Connected & Enabled Tool in
        deterministic (BrowseName, ProductInstanceUri) order, preferring Tools
        with configured joining processes when several are ready.
      - ``first_available``: selects the first Tool with a unique ProductInstanceUri
        in deterministic (BrowseName, ProductInstanceUri) order.
      - ``discover_unique``: requires exactly one Tool Object on the server.
      - ``exact_match``: requires ``expected_tool_uri`` to be configured.
    """
    if expected_tool_uri is None and os.environ.get("OPCUA_TARGET_SERVER_PROFILE"):
        expected_tool_uri = os.environ.get("OPCUA_TOOL_PRODUCT_INSTANCE_URI") or None
    effective_policy = policy or os.environ.get("OPCUA_TOOL_SELECTION_POLICY") or "first_ready"
    if not expected_tool_uri and effective_policy == "exact_match":
        logger.warning("Tool selection policy 'exact_match' requires a configured Tool ProductInstanceUri.")
        return ""
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
        tool_refs = list(
            {
                ref.NodeId: ref for ref in await _browse_refs(tools_folder) if ref.NodeClass == ua.NodeClass.Object
            }.values()
        )
        if not tool_refs:
            return ""
        if not expected_tool_uri and effective_policy == "discover_unique" and len(tool_refs) != 1:
            logger.warning(
                "Automatic Tool discovery requires exactly one Tool, found %d. "
                "Configure the intended Tool ProductInstanceUri before running workflows.",
                len(tool_refs),
            )
            return ""
        discovered: list[tuple[str, str, object]] = []
        for tool_ref in tool_refs:
            browse_name = str(getattr(getattr(tool_ref, "BrowseName", None), "Name", "") or "")
            tool = _node_from_ref(tools_folder, tool_ref.NodeId)
            ident = await find_child_by_browse_name(tool, "Identification", ns_di)
            if ident is None:
                continue
            pi_node = await find_child_by_browse_name(ident, "ProductInstanceUri", ns_di)
            if pi_node is None and ns_app is not None:
                pi_node = await find_child_by_browse_name(ident, "ProductInstanceUri", ns_app)
            if pi_node is None:
                continue
            value = await asyncio.wait_for(pi_node.read_value(), timeout=_BROWSE_TIMEOUT)
            piu = str(value) if value is not None else ""
            if piu:
                discovered.append((browse_name, piu, tool))
        if not discovered:
            return ""
        if expected_tool_uri:
            matches = [piu for _bn, piu, _tool in discovered if piu == expected_tool_uri]
            return matches[0] if len(matches) == 1 else ""

        piu_counts = Counter(piu for _bn, piu, _tool in discovered)
        unique_tools = [(bn, piu, tool) for bn, piu, tool in discovered if piu_counts[piu] == 1]
        if not unique_tools:
            return ""
        if effective_policy == "discover_unique":
            return unique_tools[0][1] if len(unique_tools) == 1 else ""
        if effective_policy == "first_available":
            unique_tools.sort(key=lambda item: (item[0], item[1]))
            return unique_tools[0][1]
        if len(unique_tools) == 1:
            return unique_tools[0][1]

        ready_tools: list[tuple[int, str, str]] = []
        for bn, piu, tool in unique_tools:
            ready_rank = await _read_asset_ready_rank(tool, ns_ijt, ns_app)
            if ready_rank is not None:
                ready_tools.append((ready_rank, bn, piu))
        if not ready_tools:
            logger.warning(
                "No ready (Connected and Enabled) Tool found among %d Tool(s).",
                len(unique_tools),
            )
            return ""
        if len(ready_tools) == 1:
            return ready_tools[0][2]

        ranked_tools: list[tuple[int, int, str, str]] = []
        for ready_rank, bn, piu in ready_tools:
            proc_rank = await _tool_process_rank(js, piu, ns_ijt, ns_app)
            ranked_tools.append((ready_rank, proc_rank, bn, piu))
        ranked_tools.sort()
        return ranked_tools[0][3]
    except Exception as exc:  # noqa: BLE001
        _handle_discovery_error(exc)
        return ""


async def read_virtual_station_product_instance_uri(
    client,
    ns_ijt: int,
    ns_di: int,
    ns_app: int | None = None,
) -> str:
    """Resolve a unique VirtualStation ProductInstanceUri when only one (or one ready) station exists."""
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
        stations_folder = await find_child_by_browse_name(assets, "VirtualStations", ns_ijt)
        if stations_folder is None:
            return ""
        station_refs = list(
            {
                ref.NodeId: ref for ref in await _browse_refs(stations_folder) if ref.NodeClass == ua.NodeClass.Object
            }.values()
        )
        if not station_refs:
            return ""
        discovered: list[tuple[str, str, object]] = []
        for station_ref in station_refs:
            browse_name = str(getattr(getattr(station_ref, "BrowseName", None), "Name", "") or "")
            station = _node_from_ref(stations_folder, station_ref.NodeId)
            ident = await find_child_by_browse_name(station, "Identification", ns_di)
            if ident is None:
                continue
            pi_node = await find_child_by_browse_name(ident, "ProductInstanceUri", ns_di)
            if pi_node is None and ns_app is not None:
                pi_node = await find_child_by_browse_name(ident, "ProductInstanceUri", ns_app)
            if pi_node is None:
                continue
            value = await asyncio.wait_for(pi_node.read_value(), timeout=_BROWSE_TIMEOUT)
            piu = str(value) if value is not None else ""
            if piu:
                discovered.append((browse_name, piu, station))
        counts = Counter(piu for _bn, piu, _station in discovered)
        unique_stations = [(bn, piu, station) for bn, piu, station in discovered if counts[piu] == 1]
        if len(unique_stations) == 1:
            return unique_stations[0][1]
        ready_stations = []
        for bn, piu, station in unique_stations:
            if await _read_asset_ready_rank(station, ns_ijt, ns_app) is not None:
                ready_stations.append((bn, piu))
        return ready_stations[0][1] if len(ready_stations) == 1 else ""
    except Exception as exc:  # noqa: BLE001
        _handle_discovery_error(exc)
        return ""


async def read_tool_enabled(
    client,
    ns_ijt: int,
    ns_di: int,
    product_instance_uri: str,
    ns_app: int | None = None,
) -> bool | None:
    """Read Parameters.Enabled from the Tool identified by ProductInstanceUri."""
    try:
        joining_system = await find_joining_system(client)
        if joining_system is None:
            return None
        asset_management = await find_child_by_browse_name_any(joining_system, "AssetManagement", (ns_ijt, ns_app))
        if asset_management is None:
            return None
        assets = await find_child_by_browse_name_any(asset_management, "Assets", (ns_ijt, ns_app))
        if assets is None:
            return None
        tools = await find_child_by_browse_name_any(assets, "Tools", (ns_ijt, ns_app))
        if tools is None:
            return None

        for _name, tool in await browse_folder_instances(tools):
            identification = await find_child_by_browse_name_any(tool, "Identification", (ns_di, ns_ijt, ns_app))
            if identification is None:
                continue
            piu_node = await find_child_by_browse_name_any(
                identification, "ProductInstanceUri", (ns_di, ns_ijt, ns_app)
            )
            if piu_node is None:
                continue
            piu = await asyncio.wait_for(piu_node.read_value(), timeout=_BROWSE_TIMEOUT)
            if str(piu) != product_instance_uri:
                continue

            parameters = await find_child_by_browse_name_any(tool, "Parameters", (ns_ijt, ns_app))
            if parameters is None:
                return None
            enabled_node = await find_child_by_browse_name_any(parameters, "Enabled", (ns_ijt, ns_app))
            if enabled_node is None:
                return None
            enabled = await asyncio.wait_for(enabled_node.read_value(), timeout=_BROWSE_TIMEOUT)
            return enabled if isinstance(enabled, bool) else None
    except Exception as exc:  # noqa: BLE001
        _handle_discovery_error(exc)
    return None
