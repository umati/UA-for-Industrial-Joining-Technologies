"""
test_namespace_registration.py — OPC UA namespace registration tests.
Verifies:
  - All required companion specification namespaces are registered on the server.
  - The application namespace is registered.
  - All resolved namespace indices are positive integers (index 0 is reserved for OPC UA).
"""
import pytest
from helpers.namespaces import (
    NS_OPC_UA,
    NS_DI, NS_AMB, NS_IA, NS_MACHINERY, NS_MACH_RESULT,
    NS_IJT_BASE, NS_IJT_TIGHTENING,
    NS_APP,
    ALL_NAMESPACE_URIS,
)
pytestmark = pytest.mark.live
_COMPANION_NAMESPACES = [
    NS_DI,
    NS_AMB,
    NS_IA,
    NS_MACHINERY,
    NS_MACH_RESULT,
    NS_IJT_BASE,
    NS_IJT_TIGHTENING,
]
@pytest.mark.parametrize("uri", _COMPANION_NAMESPACES)
async def test_all_companion_namespaces_registered(uri, ns_indices):
    """Every required companion specification namespace must have a non-None index."""
    index = ns_indices.get(uri)
    assert index is not None, (
        f"Required companion namespace not registered on server: {uri}"
    )
async def test_app_namespace_registered(ns_indices):
    """The application namespace (NS_APP) must be registered on the server."""
    index = ns_indices.get(NS_APP)
    assert index is not None, (
        f"Application namespace not registered on server: {NS_APP}"
    )
async def test_namespace_indices_are_positive(ns_indices):
    """
    All resolved (non-None) namespace indices must be > 0.
    Index 0 is always NS_OPC_UA and is not checked here; all companion and
    application namespaces must receive a positive runtime index.
    """
    for uri, index in ns_indices.items():
        if uri == NS_OPC_UA:
            continue
        if index is None:
            continue
        assert index > 0, (
            f"Namespace index for '{uri}' must be > 0, got {index}"
        )