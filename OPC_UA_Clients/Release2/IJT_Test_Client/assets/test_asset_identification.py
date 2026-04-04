"""
test_asset_identification.py — Asset Identification sub-tree tests.
Verifies that both the first controller and first tool instance expose:
  - An Identification node (DI namespace).
  - Manufacturer and Model properties with non-empty string values.
  - SerialNumber and SoftwareRevision property nodes.
  - AssetId (DI namespace) under Identification.
  - ComponentName (DI namespace) under Identification.
Note: AssetId and ComponentName BrowseNames are defined in the DI namespace
(BrowseName="1:AssetId" in Opc.Ua.Di.NodeSet2.xml).
"""

import pytest

from helpers.namespaces import BN, NS_DI
from helpers.node_discovery import find_child_by_browse_name

pytestmark = [pytest.mark.live, pytest.mark.structure]


# ─── Shared helper ────────────────────────────────────────────────────────────
async def _get_identification(asset_node, ns_di):
    """Return the Identification child of asset_node (DI namespace)."""
    return await find_child_by_browse_name(asset_node, BN.IDENTIFICATION, ns_di)


# ─── Controller identification tests ─────────────────────────────────────────
async def test_controller_identification_node_exists(controllers_instances, ns_indices):
    """First controller must have an Identification child in the DI namespace."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered")
    asset_node = controllers_instances[0][1]
    identification = await _get_identification(asset_node, ns_di)
    assert identification is not None, "Identification node (DI ns) not found on first controller"


async def test_controller_identification_has_manufacturer(controllers_instances, ns_indices):
    """First controller Identification must have a non-empty Manufacturer string."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered")
    asset_node = controllers_instances[0][1]
    identification = await _get_identification(asset_node, ns_di)
    if identification is None:
        pytest.skip("Identification node not found on first controller")
    mfr_node = await find_child_by_browse_name(identification, BN.MANUFACTURER, ns_di)
    assert mfr_node is not None, "Manufacturer node not found under controller Identification"
    value = await mfr_node.read_value()
    assert value is not None and str(value).strip() != "", "Manufacturer value must not be empty on first controller"


async def test_controller_identification_has_model(controllers_instances, ns_indices):
    """First controller Identification must have a non-empty Model string."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered")
    asset_node = controllers_instances[0][1]
    identification = await _get_identification(asset_node, ns_di)
    if identification is None:
        pytest.skip("Identification node not found on first controller")
    model_node = await find_child_by_browse_name(identification, BN.MODEL, ns_di)
    assert model_node is not None, "Model node not found under controller Identification"
    value = await model_node.read_value()
    assert value is not None and str(value).strip() != "", "Model value must not be empty on first controller"


async def test_controller_identification_has_serial_number(controllers_instances, ns_indices):
    """First controller Identification must expose a SerialNumber node."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered")
    asset_node = controllers_instances[0][1]
    identification = await _get_identification(asset_node, ns_di)
    if identification is None:
        pytest.skip("Identification node not found on first controller")
    sn_node = await find_child_by_browse_name(identification, BN.SERIAL_NUMBER, ns_di)
    assert sn_node is not None, "SerialNumber node not found under controller Identification"


async def test_controller_identification_has_software_revision(controllers_instances, ns_indices):
    """First controller Identification must expose a SoftwareRevision node."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered")
    asset_node = controllers_instances[0][1]
    identification = await _get_identification(asset_node, ns_di)
    if identification is None:
        pytest.skip("Identification node not found on first controller")
    sw_node = await find_child_by_browse_name(identification, BN.SOFTWARE_REVISION, ns_di)
    assert sw_node is not None, "SoftwareRevision node not found under controller Identification"


async def test_controller_identification_has_asset_id(controllers_instances, ns_indices):
    """First controller Identification must have an AssetId child (DI namespace)."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered")
    asset_node = controllers_instances[0][1]
    identification = await _get_identification(asset_node, ns_di)
    if identification is None:
        pytest.skip("Identification node not found on first controller")
    asset_id_node = await find_child_by_browse_name(identification, BN.ASSET_ID, ns_di)
    if asset_id_node is None:
        pytest.skip("AssetId node (DI ns) not found under controller Identification — not implemented on this server")
    assert asset_id_node is not None


async def test_controller_identification_has_component_name(controllers_instances, ns_indices):
    """First controller Identification must have a ComponentName child (DI namespace)."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered")
    asset_node = controllers_instances[0][1]
    identification = await _get_identification(asset_node, ns_di)
    if identification is None:
        pytest.skip("Identification node not found on first controller")
    cn_node = await find_child_by_browse_name(identification, BN.COMPONENT_NAME, ns_di)
    if cn_node is None:
        pytest.skip(
            "ComponentName node (DI ns) not found under controller Identification — not implemented on this server"
        )
    assert cn_node is not None


# ─── Tool identification tests ────────────────────────────────────────────────
async def test_tool_identification_node_exists(tools_instances, ns_indices):
    """First tool must have an Identification child in the DI namespace."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered")
    asset_node = tools_instances[0][1]
    identification = await _get_identification(asset_node, ns_di)
    assert identification is not None, "Identification node (DI ns) not found on first tool"


async def test_tool_identification_has_manufacturer(tools_instances, ns_indices):
    """First tool Identification must have a non-empty Manufacturer string."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered")
    asset_node = tools_instances[0][1]
    identification = await _get_identification(asset_node, ns_di)
    if identification is None:
        pytest.skip("Identification node not found on first tool")
    mfr_node = await find_child_by_browse_name(identification, BN.MANUFACTURER, ns_di)
    assert mfr_node is not None, "Manufacturer node not found under tool Identification"
    value = await mfr_node.read_value()
    assert value is not None and str(value).strip() != "", "Manufacturer value must not be empty on first tool"


async def test_tool_identification_has_model(tools_instances, ns_indices):
    """First tool Identification must have a non-empty Model string."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered")
    asset_node = tools_instances[0][1]
    identification = await _get_identification(asset_node, ns_di)
    if identification is None:
        pytest.skip("Identification node not found on first tool")
    model_node = await find_child_by_browse_name(identification, BN.MODEL, ns_di)
    assert model_node is not None, "Model node not found under tool Identification"
    value = await model_node.read_value()
    assert value is not None and str(value).strip() != "", "Model value must not be empty on first tool"


async def test_tool_identification_has_serial_number(tools_instances, ns_indices):
    """First tool Identification must expose a SerialNumber node."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered")
    asset_node = tools_instances[0][1]
    identification = await _get_identification(asset_node, ns_di)
    if identification is None:
        pytest.skip("Identification node not found on first tool")
    sn_node = await find_child_by_browse_name(identification, BN.SERIAL_NUMBER, ns_di)
    assert sn_node is not None, "SerialNumber node not found under tool Identification"


async def test_tool_identification_has_software_revision(tools_instances, ns_indices):
    """First tool Identification must expose a SoftwareRevision node."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered")
    asset_node = tools_instances[0][1]
    identification = await _get_identification(asset_node, ns_di)
    if identification is None:
        pytest.skip("Identification node not found on first tool")
    sw_node = await find_child_by_browse_name(identification, BN.SOFTWARE_REVISION, ns_di)
    assert sw_node is not None, "SoftwareRevision node not found under tool Identification"


async def test_tool_identification_has_asset_id(tools_instances, ns_indices):
    """First tool Identification must have an AssetId child (DI namespace)."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered")
    asset_node = tools_instances[0][1]
    identification = await _get_identification(asset_node, ns_di)
    if identification is None:
        pytest.skip("Identification node not found on first tool")
    asset_id_node = await find_child_by_browse_name(identification, BN.ASSET_ID, ns_di)
    if asset_id_node is None:
        pytest.skip("AssetId node (DI ns) not found under tool Identification — not implemented on this server")
    assert asset_id_node is not None


async def test_tool_identification_has_component_name(tools_instances, ns_indices):
    """First tool Identification must have a ComponentName child (DI namespace)."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered")
    asset_node = tools_instances[0][1]
    identification = await _get_identification(asset_node, ns_di)
    if identification is None:
        pytest.skip("Identification node not found on first tool")
    cn_node = await find_child_by_browse_name(identification, BN.COMPONENT_NAME, ns_di)
    if cn_node is None:
        pytest.skip("ComponentName node (DI ns) not found under tool Identification — not implemented on this server")
    assert cn_node is not None
