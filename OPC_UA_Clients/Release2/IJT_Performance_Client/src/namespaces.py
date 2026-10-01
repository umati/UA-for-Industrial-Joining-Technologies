"""
OPC UA IJT Performance Client - Namespace constants and type identifiers.
Self-contained module providing standard namespace URIs and Event Type IDs.
"""

from __future__ import annotations

import logging

from asyncua import Client, ua

logger = logging.getLogger(__name__)

# Standard Namespace URIs
NS_OPC_UA = "http://opcfoundation.org/UA/"
NS_DI = "http://opcfoundation.org/UA/DI/"
NS_MACHINERY = "http://opcfoundation.org/UA/Machinery/"
NS_MACH_RESULT = "http://opcfoundation.org/UA/Machinery/Result/"
NS_IJT_BASE = "http://opcfoundation.org/UA/IJT/Base/"
NS_IJT_TIGHTENING = "http://opcfoundation.org/UA/IJT/Tightening/"
NS_APP = "urn:AtlasCopco:IJT:Tightening:Server/"

# Numeric Event Type Local IDs in NS_IJT_BASE (OPC 40450-1)
JOINING_SYSTEM_RESULT_READY_EVENT_TYPE_ID = 1007
REQUESTED_RESULT_EVENT_TYPE_ID = 1006

# Standard BrowseNames
BN_JOINING_SYSTEM = "JoiningSystem"
BN_TIGHTENING_SYSTEM = "TighteningSystem"
BN_SIMULATIONS = "Simulations"
BN_SIMULATE_RESULTS = "SimulateResults"
BN_SIMULATE_SINGLE_RESULT = "SimulateSingleResult"


async def resolve_namespace_index(client: Client, uri: str) -> int | None:
    """Resolve namespace index on an active OPC UA client connection.
    Returns index integer if found, None otherwise.
    """
    try:
        idx = await client.get_namespace_index(uri)
        return idx
    except Exception as exc:
        logger.debug(f"Namespace {uri} not found on server {client.server_url}: {exc}")
        return None


async def read_namespace_metadata(client: Client, uri: str) -> dict[str, str | None]:
    """Read NamespaceVersion and NamespacePublicationDate for ``uri`` from Server/Namespaces.

    Both values are optional in OPC UA; a value the server does not expose is returned as None so
    callers can report it as unverified instead of guessing.
    """
    result: dict[str, str | None] = {"version": None, "publication_date": None}
    try:
        namespaces = client.get_node(ua.NodeId(ua.Int32(ua.ObjectIds.Server_Namespaces)))
        for child in await namespaces.get_children():
            try:
                if await (await child.get_child("0:NamespaceUri")).read_value() != uri:
                    continue
            except Exception:
                continue
            for key, browse_name in (
                ("version", "0:NamespaceVersion"),
                ("publication_date", "0:NamespacePublicationDate"),
            ):
                try:
                    value = await (await child.get_child(browse_name)).read_value()
                except Exception:
                    continue
                if value is not None and value != "":
                    result[key] = value.isoformat() if hasattr(value, "isoformat") else str(value)
            break
    except Exception as exc:
        logger.debug(f"Namespace metadata for {uri} not readable on {client.server_url}: {exc}")
    return result
