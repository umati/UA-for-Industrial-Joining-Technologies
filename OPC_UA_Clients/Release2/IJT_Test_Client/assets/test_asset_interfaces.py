"""
test_asset_interfaces.py — Asset HasInterface reference tests.

Verifies that every asset instance carries the correct IJT interface type via
HasInterface (RefType i=17603).  The IJT Base spec defines a concrete interface
type for every asset category; each is a subtype of IJoiningSystemAssetType
(IJT Base i=1002) in the NodeSet type hierarchy.

Servers may declare only the most-derived interface on each instance — per OPC UA
convention. The reference simulator follows this pattern.

Interface placement (authoritative — from asset_management_t.cpp + NodeSet):
  - Asset instance node  → concrete interface (IControllerType, IToolType, etc.)
  - Identification node  → IJoiningAdditionalInformationType (IJT Base i=1017)
                           Properties AssetId/ComponentName/Location already present;
                           HasInterface reference added in asset_management_t.cpp.
  - Tool/Parameters node → ITighteningToolParametersType (IJT Tightening i=1003)
  - All other Parameters → no additional interface beyond the default type definition.

Source of truth: NodesetFiles/ in this repository, cross-checked with namespace_helper_t.h.
"""

import pytest

from helpers.namespaces import (
    BN,
    NS_DI,
    NS_IJT_BASE,
    NS_IJT_TIGHTENING,
    IJTTighteningTypes,
    IJTTypes,
)
from helpers.node_discovery import (
    _browse_refs,
    _node_from_ref,
    browse_folder_instances,
    find_child_by_browse_name,
    get_interface_types,
    has_interface,
)

pytestmark = [pytest.mark.live, pytest.mark.structure]

# Applied per-test (not module-level) so tests that already pass on the live server
# (Identification/Parameters interfaces) remain visible as real pass/fail results.
# strict=True: an unexpected pass (xpass) fails CI, forcing the marker to be removed
# once the server emits HasInterface on asset instance nodes.
_XFAIL_HAS_INTERFACE = pytest.mark.xfail(
    reason=(
        "The current server binary does not yet emit HasInterface references on asset "
        "instance nodes. These tests document the spec-mandated behaviour (IJT Base §7.3) "
        "and will become xpass once the server adds the missing references. "
        "This is a server-implementation gap, not a client defect."
    ),
    strict=True,
)

# ─── Internal helpers ────────────────────────────────────────────────────────


async def _assert_all_have_interface(instances, ns_idx: int, type_id: int, type_name: str):
    for name, node in instances:
        ok = await has_interface(node, ns_idx, type_id)
        assert ok, f"'{name}' does not implement {type_name} (ns={ns_idx}, id={type_id}) via HasInterface"


async def _instances_from(folder, label: str):
    instances = await browse_folder_instances(folder)
    if not instances:
        pytest.skip(f"{label} folder has no instances")
    return instances


# ─── Concrete per-asset-type interface tests ─────────────────────────────────


@_XFAIL_HAS_INTERFACE
async def test_controllers_implement_i_controller_type(controllers_instances, ns_indices):
    """Every controller must implement IControllerType (IJT Base i=1003).
    IControllerType is a subtype of IJoiningSystemAssetType per the NodeSet.
    """
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    await _assert_all_have_interface(controllers_instances, ns_ijt, IJTTypes.ICONTROLLER_TYPE, "IControllerType")


@_XFAIL_HAS_INTERFACE
async def test_tools_implement_i_tool_type(tools_instances, ns_indices):
    """Every tool must implement IToolType (IJT Base i=1004)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    await _assert_all_have_interface(tools_instances, ns_ijt, IJTTypes.ITOOL_TYPE, "IToolType")


@_XFAIL_HAS_INTERFACE
async def test_servos_implement_i_servo_type(servos_folder, ns_indices):
    """Every servo must implement IServoType (IJT Base i=1008)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    instances = await _instances_from(servos_folder, "Servos")
    await _assert_all_have_interface(instances, ns_ijt, IJTTypes.ISERVO_TYPE, "IServoType")


@_XFAIL_HAS_INTERFACE
async def test_power_supplies_implement_i_power_supply_type(power_supplies_folder, ns_indices):
    """Every power supply must implement IPowerSupplyType (IJT Base i=1009)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    instances = await _instances_from(power_supplies_folder, "PowerSupplies")
    await _assert_all_have_interface(instances, ns_ijt, IJTTypes.IPOWER_SUPPLY_TYPE, "IPowerSupplyType")


@_XFAIL_HAS_INTERFACE
async def test_batteries_implement_i_battery_type(batteries_folder, ns_indices):
    """Every battery must implement IBatteryType (IJT Base i=1010)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    instances = await _instances_from(batteries_folder, "Batteries")
    await _assert_all_have_interface(instances, ns_ijt, IJTTypes.IBATTERY_TYPE, "IBatteryType")


@_XFAIL_HAS_INTERFACE
async def test_sensors_implement_i_sensor_type(sensors_folder, ns_indices):
    """Every sensor must implement ISensorType (IJT Base i=1011)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    instances = await _instances_from(sensors_folder, "Sensors")
    await _assert_all_have_interface(instances, ns_ijt, IJTTypes.ISENSOR_TYPE, "ISensorType")


@_XFAIL_HAS_INTERFACE
async def test_feeders_implement_i_feeder_type(feeders_folder, ns_indices):
    """Every feeder must implement IFeederType (IJT Base i=1012)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    instances = await _instances_from(feeders_folder, "Feeders")
    await _assert_all_have_interface(instances, ns_ijt, IJTTypes.IFEEDER_TYPE, "IFeederType")


@_XFAIL_HAS_INTERFACE
async def test_memory_devices_implement_i_memory_device_type(memory_devices_folder, ns_indices):
    """Every memory device must implement IMemoryDeviceType (IJT Base i=1013)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    instances = await _instances_from(memory_devices_folder, "MemoryDevices")
    await _assert_all_have_interface(instances, ns_ijt, IJTTypes.IMEMORY_DEVICE_TYPE, "IMemoryDeviceType")


@_XFAIL_HAS_INTERFACE
async def test_cables_implement_i_cable_type(cables_folder, ns_indices):
    """Every cable must implement ICableType (IJT Base i=1014)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    instances = await _instances_from(cables_folder, "Cables")
    await _assert_all_have_interface(instances, ns_ijt, IJTTypes.ICABLE_TYPE, "ICableType")


@_XFAIL_HAS_INTERFACE
async def test_accessories_implement_i_accessory_type(accessories_folder, ns_indices):
    """Every accessory must implement IAccessoryType (IJT Base i=1015)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    instances = await _instances_from(accessories_folder, "Accessories")
    await _assert_all_have_interface(instances, ns_ijt, IJTTypes.IACCESSORY_TYPE, "IAccessoryType")


@_XFAIL_HAS_INTERFACE
async def test_sub_components_implement_i_sub_component_type(sub_components_folder, ns_indices):
    """Every sub-component must implement ISubComponentType (IJT Base i=1016)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    instances = await _instances_from(sub_components_folder, "SubComponents")
    await _assert_all_have_interface(instances, ns_ijt, IJTTypes.ISUB_COMPONENT_TYPE, "ISubComponentType")


@_XFAIL_HAS_INTERFACE
async def test_software_components_implement_i_software_type(software_components_folder, ns_indices):
    """Every software component must implement ISoftwareType (IJT Base i=1019).
    Software exposes limited Identification only: ProductInstanceUri, Manufacturer,
    ManufacturerUri, Model, SoftwareRevision, ComponentName, ProductCode, SerialNumber,
    JoiningTechnology. Other asset nodes may not be present (spec §7.3.15).
    """
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    instances = await _instances_from(software_components_folder, "SoftwareComponents")
    await _assert_all_have_interface(instances, ns_ijt, IJTTypes.ISOFTWARE_TYPE, "ISoftwareType")


@_XFAIL_HAS_INTERFACE
async def test_virtual_stations_implement_i_virtual_station_type(virtual_stations_folder, ns_indices):
    """Every virtual station must implement IVirtualStationType (IJT Base i=1031).
    VirtualStation exposes limited Identification only: ProductInstanceUri, Manufacturer,
    ManufacturerUri, ComponentName, JoiningTechnology, SerialNumber (may be empty string).
    Other asset nodes may not be present (spec §7.3.16).
    """
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    instances = await _instances_from(virtual_stations_folder, "VirtualStations")
    await _assert_all_have_interface(instances, ns_ijt, IJTTypes.IVIRTUAL_STATION_TYPE, "IVirtualStationType")


# ─── Interface namespace validation ──────────────────────────────────────────


async def test_controller_interface_node_ids_are_in_ijt_base_namespace(controllers_instances, ns_indices):
    """All HasInterface NodeIds on controllers must belong to the IJT Base namespace."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    name, node = controllers_instances[0]
    iface_ids = await get_interface_types(node)
    if not iface_ids:
        pytest.skip(f"No HasInterface references found on '{name}'")
    for nid in iface_ids:
        assert nid.NamespaceIndex == ns_ijt, (
            f"Interface NodeId {nid} on '{name}' has ns={nid.NamespaceIndex}, expected IJT Base ns={ns_ijt}"
        )


# ─── Identification interface tests ─────────────────────────────────────────


@_XFAIL_HAS_INTERFACE
async def test_tool_parameters_implement_i_tightening_tool_parameters_type(tools_instances, ns_indices):
    """Tool Parameters folders must implement ITighteningToolParametersType
    (IJT Tightening ns, i=1003).  Only Tools have this special Parameters interface.
    Server does not yet emit HasInterface on Tool/Parameters nodes — tracked gap.
    """
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    ns_tight = ns_indices.get(NS_IJT_TIGHTENING)
    if ns_ijt is None or ns_tight is None:
        pytest.skip("IJT Base or IJT Tightening namespace not registered")
    for name, node in tools_instances:
        params = await find_child_by_browse_name(node, BN.PARAMETERS, ns_ijt)
        if params is None:
            pytest.skip(f"Tool '{name}' has no Parameters folder")
        ok = await has_interface(params, ns_tight, IJTTighteningTypes.ITIGHTENING_TOOL_PARAMETERS_TYPE)
        assert ok, (
            f"Tool '{name}' Parameters does not implement ITighteningToolParametersType "
            f"(IJT Tightening ns={ns_tight}, "
            f"id={IJTTighteningTypes.ITIGHTENING_TOOL_PARAMETERS_TYPE})"
        )


@_XFAIL_HAS_INTERFACE
async def test_all_asset_identification_implements_i_joining_additional_information_type(assets_folder, ns_indices):
    """Every asset's Identification object must implement IJoiningAdditionalInformationType
    (IJT Base i=1017) via HasInterface.

    IJoiningAdditionalInformationType applies ONLY to the Identification object.
    Properties AssetId/ComponentName are in the DI namespace (BrowseName="1:AssetId" in
    Opc.Ua.Di.NodeSet2.xml). The HasInterface reference is added in asset_management_t.cpp.
    OpcUaId_IJoiningAdditionalInformationType=1017 in namespace_helper_t.h.
    """
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    ns_di = ns_indices.get(NS_DI)
    if ns_ijt is None or ns_di is None:
        pytest.skip("IJT Base or DI namespace not registered")
    all_folder_refs = await _browse_refs(assets_folder)
    all_folders = [_node_from_ref(assets_folder, r.NodeId) for r in all_folder_refs]
    checked = 0
    for folder in all_folders:
        instances = await browse_folder_instances(folder)
        for name, node in instances:
            ident = await find_child_by_browse_name(node, BN.IDENTIFICATION, ns_di)
            if ident is None:
                continue
            ok = await has_interface(ident, ns_ijt, IJTTypes.IJOINING_ADDITIONAL_INFORMATION_TYPE)
            assert ok, (
                f"'{name}' Identification does not implement "
                f"IJoiningAdditionalInformationType "
                f"(IJT Base ns={ns_ijt}, id={IJTTypes.IJOINING_ADDITIONAL_INFORMATION_TYPE})"
            )
            checked += 1
    if checked == 0:
        pytest.skip("No asset instances with Identification nodes found")
