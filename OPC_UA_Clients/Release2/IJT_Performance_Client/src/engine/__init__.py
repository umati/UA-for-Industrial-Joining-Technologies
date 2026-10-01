"""OPC UA high-scale client engine and connection pool."""

from .client_pool import (
    EndpointIntegrity,
    FleetIntegritySummary,
    OpcUaClientPool,
    evaluate_fleet_integrity,
)
from .session_policy import (
    apply_session_policy,
    disconnect_client,
    load_ijt_type_definitions,
    patch_asyncua_subtype_serializer,
    verify_asyncua_version_compatibility,
)

__all__ = [
    "EndpointIntegrity",
    "FleetIntegritySummary",
    "OpcUaClientPool",
    "apply_session_policy",
    "disconnect_client",
    "evaluate_fleet_integrity",
    "load_ijt_type_definitions",
    "patch_asyncua_subtype_serializer",
    "verify_asyncua_version_compatibility",
]
