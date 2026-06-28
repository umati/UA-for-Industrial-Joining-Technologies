"""
specification tests for JoiningDataVariableType node structure — OPC 40450-1.

Covers official asset-management conformance units:
    Every JoiningDataVariable parameter node (CableLength, FeedingSpeed, NominalVoltage,
    Capacity, NominalPower, ActualPower, MeasuredValue, MaxTorque, MinTorque, MaxSpeed)
    must expose its PhysicalQuantity child via a HasComponent reference — NOT HasProperty.
    PhysicalQuantity (MultiStateDiscreteType) must in turn expose EnumStrings via
    HasProperty so that conformance validators can discover its enum labels.
    Battery Capacity must use engineering unit Ah (UNECE 4279624), not A (UNECE 4279632).
    Sensor MeasuredValue must be navigable under the Sensor's Parameters node
    (no doubled path in the NodeId).

Background:
    The IJT Base NodeSet defines:
        JoiningDataVariableType
            HasComponent (47) → PhysicalQuantity : MultiStateDiscreteType
                HasProperty (46) → EnumStrings : PropertyType

    If PhysicalQuantity is connected via HasProperty (46) instead of HasComponent (47),
    a spec-conformant client that walks HasComponent references will fail to find it,
    and the EnumStrings child will be unreachable. The VDMA Test Tool reports this as
    "Mandatory child with BrowseName EnumStrings not found" with a fallback to
    "Possible matching Custom Objects" — confirming the reference type is wrong.

    This bug affects Cable, Feeder, Battery, PowerSupply, and Sensor in affected
    IJT server builds when PhysicalQuantity is wired via the wrong reference type in
    address_space_helper_t.cpp.

    These tests are the authoritative regression gate: they MUST fail when the bug is
    present and MUST pass when address_space_helper_t.cpp uses OpcUaId_HasComponent (47).
"""

from __future__ import annotations

import pytest
from asyncua import ua

from helpers.cu_registry import CU
from helpers.namespaces import (
    BN,
    NS_IJT_BASE,
    RefTypes,
)
from helpers.node_discovery import (
    browse_folder_instances,
    find_child_by_browse_name,
    find_child_by_reference_type,
)

pytestmark = [pytest.mark.live, pytest.mark.conformance]

# UNECE unit codes verified against IJT Base spec and common_type_utilities_t.h
_EU_AMPERE_HOUR_ID = 4279624  # Ah — electric charge / capacity
_EU_AMPERE_ID = 4279632  # A  — electric current (wrong for battery capacity)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


async def _get_joining_variable_and_ns(folder_node, variable_bn, ns_indices):
    """
    Navigate from an asset folder to a JoiningDataVariable parameter node.

    Returns (asset_name, variable_node, ns_ijt) or raises pytest.skip.
    """
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None or folder_node is None:
        pytest.skip("Folder or IJT Base namespace not available")

    instances = await browse_folder_instances(folder_node)
    if not instances:
        pytest.skip("No instances found — at least one instance expected")

    _name, asset_node = instances[0]
    params = await find_child_by_browse_name(asset_node, BN.PARAMETERS, ns_ijt)
    if params is None:
        pytest.skip(f"Asset '{_name}' has no Parameters node")

    variable_node = await find_child_by_browse_name(params, variable_bn, ns_ijt)
    if variable_node is None:
        pytest.skip(f"Asset '{_name}' Parameters has no {variable_bn!r} node")

    return _name, variable_node, ns_ijt


async def _assert_physical_quantity_via_has_component(variable_node, variable_label, ns_ijt):
    """
    Assert that a JoiningDataVariable exposes PhysicalQuantity via HasComponent (47).

    This is the direct regression test for the HasProperty → HasComponent bug.
    If this fails, the VDMA Test Tool will also report "EnumStrings not found".
    """
    pq_via_component = await find_child_by_reference_type(
        variable_node, BN.PHYSICAL_QUANTITY, ns_ijt, RefTypes.HAS_COMPONENT
    )
    assert pq_via_component is not None, (
        f"{variable_label}: PhysicalQuantity must be reachable via HasComponent (47) "
        f"per IJT Base NodeSet spec (JoiningDataVariableType → HasComponent → PhysicalQuantity). "
        f"If this fails, address_space_helper_t.cpp is using OpcUaId_HasProperty (46) "
        f"instead of OpcUaId_HasComponent (47). The VDMA Test Tool reports this as "
        f"'Mandatory child with BrowseName EnumStrings not found'."
    )
    return pq_via_component


async def _assert_enum_strings_accessible(pq_node, variable_label):
    """
    Assert that PhysicalQuantity exposes EnumStrings via HasProperty (46).

    EnumStrings is a standard Property of MultiStateDiscreteType (ns=0, id=46 = HasProperty).
    It must be present and have namespace 0 BrowseName.
    """
    enum_strings = await find_child_by_reference_type(pq_node, BN.ENUM_STRINGS, 0, RefTypes.HAS_PROPERTY)
    assert enum_strings is not None, (
        f"{variable_label}: PhysicalQuantity must expose EnumStrings via HasProperty (46). "
        f"MultiStateDiscreteType mandates EnumStrings as a mandatory Property child. "
        f"If PhysicalQuantity was wired via HasProperty to the variable, this node will "
        f"be unreachable through proper OPC UA reference traversal."
    )


# ---------------------------------------------------------------------------
# Cable — CableLength
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_CABLE)
async def test_cable_length_physical_quantity_via_has_component(cables_folder, ns_indices):
    """Cable CableLength PhysicalQuantity must be reachable via HasComponent."""
    _name, var_node, ns_ijt = await _get_joining_variable_and_ns(cables_folder, BN.CABLE_LENGTH, ns_indices)
    await _assert_physical_quantity_via_has_component(var_node, f"Cable '{_name}' CableLength", ns_ijt)


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_CABLE)
async def test_cable_length_enum_strings_accessible(cables_folder, ns_indices):
    """Cable CableLength PhysicalQuantity must expose EnumStrings via HasProperty."""
    _name, var_node, ns_ijt = await _get_joining_variable_and_ns(cables_folder, BN.CABLE_LENGTH, ns_indices)
    pq = await _assert_physical_quantity_via_has_component(var_node, f"Cable '{_name}' CableLength", ns_ijt)
    await _assert_enum_strings_accessible(pq, f"Cable '{_name}' CableLength")


# ---------------------------------------------------------------------------
# Feeder — FeedingSpeed
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_FEEDER)
async def test_feeder_feeding_speed_physical_quantity_via_has_component(feeders_folder, ns_indices):
    """Feeder FeedingSpeed PhysicalQuantity must be reachable via HasComponent."""
    _name, var_node, ns_ijt = await _get_joining_variable_and_ns(feeders_folder, BN.FEEDING_SPEED, ns_indices)
    await _assert_physical_quantity_via_has_component(var_node, f"Feeder '{_name}' FeedingSpeed", ns_ijt)


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_FEEDER)
async def test_feeder_feeding_speed_enum_strings_accessible(feeders_folder, ns_indices):
    """Feeder FeedingSpeed PhysicalQuantity must expose EnumStrings via HasProperty."""
    _name, var_node, ns_ijt = await _get_joining_variable_and_ns(feeders_folder, BN.FEEDING_SPEED, ns_indices)
    pq = await _assert_physical_quantity_via_has_component(var_node, f"Feeder '{_name}' FeedingSpeed", ns_ijt)
    await _assert_enum_strings_accessible(pq, f"Feeder '{_name}' FeedingSpeed")


# ---------------------------------------------------------------------------
# Battery — NominalVoltage
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_BATTERY)
async def test_battery_nominal_voltage_physical_quantity_via_has_component(batteries_folder, ns_indices):
    """Battery NominalVoltage PhysicalQuantity must be reachable via HasComponent."""
    _name, var_node, ns_ijt = await _get_joining_variable_and_ns(batteries_folder, BN.NOMINAL_VOLTAGE, ns_indices)
    await _assert_physical_quantity_via_has_component(var_node, f"Battery '{_name}' NominalVoltage", ns_ijt)


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_BATTERY)
async def test_battery_nominal_voltage_enum_strings_accessible(batteries_folder, ns_indices):
    """Battery NominalVoltage PhysicalQuantity must expose EnumStrings via HasProperty."""
    _name, var_node, ns_ijt = await _get_joining_variable_and_ns(batteries_folder, BN.NOMINAL_VOLTAGE, ns_indices)
    pq = await _assert_physical_quantity_via_has_component(var_node, f"Battery '{_name}' NominalVoltage", ns_ijt)
    await _assert_enum_strings_accessible(pq, f"Battery '{_name}' NominalVoltage")


# ---------------------------------------------------------------------------
# Battery — Capacity
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_BATTERY)
async def test_battery_capacity_physical_quantity_via_has_component(batteries_folder, ns_indices):
    """Battery Capacity PhysicalQuantity must be reachable via HasComponent."""
    _name, var_node, ns_ijt = await _get_joining_variable_and_ns(batteries_folder, BN.CAPACITY, ns_indices)
    await _assert_physical_quantity_via_has_component(var_node, f"Battery '{_name}' Capacity", ns_ijt)


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_BATTERY)
async def test_battery_capacity_enum_strings_accessible(batteries_folder, ns_indices):
    """Battery Capacity PhysicalQuantity must expose EnumStrings via HasProperty."""
    _name, var_node, ns_ijt = await _get_joining_variable_and_ns(batteries_folder, BN.CAPACITY, ns_indices)
    pq = await _assert_physical_quantity_via_has_component(var_node, f"Battery '{_name}' Capacity", ns_ijt)
    await _assert_enum_strings_accessible(pq, f"Battery '{_name}' Capacity")


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_BATTERY, CU.ENGINEERING_UNITS)
async def test_battery_capacity_engineering_unit_is_ampere_hour(batteries_folder, ns_indices):
    """
    Battery Capacity must use engineering unit Ah (UNECE 4279624), not A (UNECE 4279632).

    Battery Capacity is electric charge (coulombs expressed as Ah), NOT electric current.
    The IJT server had a copy-paste bug in asset_management_t.cpp where CURRENT_UNIT (A,
    UNECE 4279632) was used as the default EU for Capacity instead of CAPACITY_UNIT
    (Ah, UNECE 4279624). This test is the authoritative regression gate for that bug.

    Note: PhysicalQuantity enum value CURRENT (6) is intentionally correct for Capacity —
    IJT Base spec has no separate CHARGE enum entry; CURRENT is the designated category
    for Ah-based battery capacity per spec design.
    """
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None or batteries_folder is None:
        pytest.skip("Batteries folder or IJT Base namespace not available")

    instances = await browse_folder_instances(batteries_folder)
    if not instances:
        pytest.skip("No Battery instances found")

    _name, battery_node = instances[0]
    params = await find_child_by_browse_name(battery_node, BN.PARAMETERS, ns_ijt)
    if params is None:
        pytest.skip(f"Battery '{_name}' has no Parameters node")

    capacity = await find_child_by_browse_name(params, BN.CAPACITY, ns_ijt)
    if capacity is None:
        pytest.skip(f"Battery '{_name}' Parameters has no Capacity node")

    # EngineeringUnits is a HasProperty child of the JoiningDataVariable (ns=0 BrowseName)
    eu_node = await find_child_by_browse_name(capacity, "EngineeringUnits", 0)
    if eu_node is None:
        eu_node = await find_child_by_browse_name(capacity, "EngineeringUnits", ns_ijt)
    if eu_node is None:
        pytest.skip(f"Battery '{_name}' Capacity has no EngineeringUnits node — EU check skipped")

    eu_value = await eu_node.read_value()
    unit_id = getattr(eu_value, "UnitId", None)

    assert unit_id != _EU_AMPERE_ID, (
        f"Battery '{_name}' Capacity.EngineeringUnits.UnitId = {unit_id} (A, ampere) — "
        f"this is WRONG. Capacity must use Ah (ampere hour, UNECE {_EU_AMPERE_HOUR_ID}). "
        f"Root cause: copy-paste of CURRENT_UNIT in asset_management_t.cpp lines for "
        f"Battery Capacity. Fix: change CURRENT_UNIT → CAPACITY_UNIT at both the null "
        f"check and the AddJoiningVariableNode default EU argument."
    )
    assert unit_id == _EU_AMPERE_HOUR_ID, (
        f"Battery '{_name}' Capacity.EngineeringUnits.UnitId = {unit_id}, "
        f"expected {_EU_AMPERE_HOUR_ID} (Ah, ampere hour). "
        f"UNECE {_EU_AMPERE_HOUR_ID} = ampere hour (electric charge unit). "
        f"UNECE {_EU_AMPERE_ID} = ampere (electric current unit — wrong for capacity)."
    )


# ---------------------------------------------------------------------------
# PowerSupply — NominalPower and ActualPower
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_POWER_SUPPLY)
async def test_power_supply_nominal_power_physical_quantity_via_has_component(power_supplies_folder, ns_indices):
    """PowerSupply NominalPower PhysicalQuantity must be reachable via HasComponent."""
    _name, var_node, ns_ijt = await _get_joining_variable_and_ns(power_supplies_folder, BN.NOMINAL_POWER, ns_indices)
    await _assert_physical_quantity_via_has_component(var_node, f"PowerSupply '{_name}' NominalPower", ns_ijt)


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_POWER_SUPPLY)
async def test_power_supply_nominal_power_enum_strings_accessible(power_supplies_folder, ns_indices):
    """PowerSupply NominalPower PhysicalQuantity must expose EnumStrings via HasProperty."""
    _name, var_node, ns_ijt = await _get_joining_variable_and_ns(power_supplies_folder, BN.NOMINAL_POWER, ns_indices)
    pq = await _assert_physical_quantity_via_has_component(var_node, f"PowerSupply '{_name}' NominalPower", ns_ijt)
    await _assert_enum_strings_accessible(pq, f"PowerSupply '{_name}' NominalPower")


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_POWER_SUPPLY)
async def test_power_supply_actual_power_physical_quantity_via_has_component(power_supplies_folder, ns_indices):
    """PowerSupply ActualPower PhysicalQuantity must be reachable via HasComponent."""
    _name, var_node, ns_ijt = await _get_joining_variable_and_ns(power_supplies_folder, BN.ACTUAL_POWER, ns_indices)
    await _assert_physical_quantity_via_has_component(var_node, f"PowerSupply '{_name}' ActualPower", ns_ijt)


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_POWER_SUPPLY)
async def test_power_supply_actual_power_enum_strings_accessible(power_supplies_folder, ns_indices):
    """PowerSupply ActualPower PhysicalQuantity must expose EnumStrings via HasProperty."""
    _name, var_node, ns_ijt = await _get_joining_variable_and_ns(power_supplies_folder, BN.ACTUAL_POWER, ns_indices)
    pq = await _assert_physical_quantity_via_has_component(var_node, f"PowerSupply '{_name}' ActualPower", ns_ijt)
    await _assert_enum_strings_accessible(pq, f"PowerSupply '{_name}' ActualPower")


# ---------------------------------------------------------------------------
# Sensor — MeasuredValue
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_SENSOR)
async def test_sensor_measured_value_physical_quantity_via_has_component(sensors_folder, ns_indices):
    """Sensor MeasuredValue PhysicalQuantity must be reachable via HasComponent."""
    _name, var_node, ns_ijt = await _get_joining_variable_and_ns(sensors_folder, BN.MEASURED_VALUE, ns_indices)
    await _assert_physical_quantity_via_has_component(var_node, f"Sensor '{_name}' MeasuredValue", ns_ijt)


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_SENSOR)
async def test_sensor_measured_value_enum_strings_accessible(sensors_folder, ns_indices):
    """Sensor MeasuredValue PhysicalQuantity must expose EnumStrings via HasProperty."""
    _name, var_node, ns_ijt = await _get_joining_variable_and_ns(sensors_folder, BN.MEASURED_VALUE, ns_indices)
    pq = await _assert_physical_quantity_via_has_component(var_node, f"Sensor '{_name}' MeasuredValue", ns_ijt)
    await _assert_enum_strings_accessible(pq, f"Sensor '{_name}' MeasuredValue")


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_SENSOR)
async def test_sensor_measured_value_is_navigable(sensors_folder, ns_indices):
    """
    Sensor MeasuredValue must be a direct child of Parameters — not have a doubled path.

    Root cause of the bug: asset_management_t.cpp AddSensor() was building the
    MeasuredValue NodeId string with an extra path segment prepended, causing the
    physical NodeId to contain the Sensor's path twice:
        WRONG: …/TorqueSensor/Maintenance/TighteningSystem/…/TorqueSensor/Parameters/MeasuredValue
        RIGHT: …/TorqueSensor/Parameters/MeasuredValue

    When the NodeId is doubled, the node is registered under the wrong parent path and
    cannot be discovered by browsing Parameters' children.
    """
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None or sensors_folder is None:
        pytest.skip("Sensors folder or IJT Base namespace not available")

    instances = await browse_folder_instances(sensors_folder)
    if not instances:
        pytest.skip("No Sensor instances found")

    _name, sensor_node = instances[0]
    params = await find_child_by_browse_name(sensor_node, BN.PARAMETERS, ns_ijt)
    if params is None:
        pytest.skip(f"Sensor '{_name}' has no Parameters node")

    measured_value = await find_child_by_browse_name(params, BN.MEASURED_VALUE, ns_ijt)
    assert measured_value is not None, (
        f"Sensor '{_name}' Parameters has no MeasuredValue child. "
        f"This indicates the NodeId contains a doubled path. "
        f"Fix: in asset_management_t.cpp AddSensor(), remove the extra "
        f"BROWSE_NAME_MAINTENANCE + inputPath segment from the MeasuredValue NodeId string."
    )

    # Confirm the node is actually readable (not just listed via a stale ref)
    try:
        node_class = await measured_value.read_node_class()
        assert node_class == ua.NodeClass.Variable, (
            f"Sensor '{_name}' MeasuredValue node class is {node_class!r}, expected Variable"
        )
    except ua.UaError as exc:
        pytest.fail(
            f"Sensor '{_name}' MeasuredValue was listed but is not readable: {exc}. "
            f"This suggests a doubled NodeId path — the node ID points to a non-existent node."
        )


# ---------------------------------------------------------------------------
# Tool — MaxTorque, MinTorque, MaxSpeed
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_TOOL)
async def test_tool_max_torque_physical_quantity_via_has_component(tools_folder, ns_indices):
    """Tool MaxTorque PhysicalQuantity must be reachable via HasComponent."""
    _name, var_node, ns_ijt = await _get_joining_variable_and_ns(tools_folder, BN.MAX_TORQUE, ns_indices)
    await _assert_physical_quantity_via_has_component(var_node, f"Tool '{_name}' MaxTorque", ns_ijt)


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_TOOL)
async def test_tool_min_torque_physical_quantity_via_has_component(tools_folder, ns_indices):
    """Tool MinTorque PhysicalQuantity must be reachable via HasComponent."""
    _name, var_node, ns_ijt = await _get_joining_variable_and_ns(tools_folder, BN.MIN_TORQUE, ns_indices)
    await _assert_physical_quantity_via_has_component(var_node, f"Tool '{_name}' MinTorque", ns_ijt)


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_TOOL)
async def test_tool_max_speed_physical_quantity_via_has_component(tools_folder, ns_indices):
    """Tool MaxSpeed PhysicalQuantity must be reachable via HasComponent."""
    _name, var_node, ns_ijt = await _get_joining_variable_and_ns(tools_folder, BN.MAX_SPEED, ns_indices)
    await _assert_physical_quantity_via_has_component(var_node, f"Tool '{_name}' MaxSpeed", ns_ijt)


@pytest.mark.requires_cu(CU.ASSET_MANAGEMENT_TOOL)
async def test_tool_max_torque_enum_strings_accessible(tools_folder, ns_indices):
    """Tool MaxTorque PhysicalQuantity must expose EnumStrings via HasProperty."""
    _name, var_node, ns_ijt = await _get_joining_variable_and_ns(tools_folder, BN.MAX_TORQUE, ns_indices)
    pq = await _assert_physical_quantity_via_has_component(var_node, f"Tool '{_name}' MaxTorque", ns_ijt)
    await _assert_enum_strings_accessible(pq, f"Tool '{_name}' MaxTorque")
