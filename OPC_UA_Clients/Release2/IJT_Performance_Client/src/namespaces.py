"""
OPC UA IJT Performance Client - Namespace constants and type identifiers.
Self-contained module providing standard namespace URIs and Event Type IDs.
"""

from __future__ import annotations

import logging

from asyncua import Client

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
