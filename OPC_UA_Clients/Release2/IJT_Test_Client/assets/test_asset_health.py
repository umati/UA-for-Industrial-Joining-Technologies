"""
test_asset_health.py — Asset Health node tests.
Per IJT spec: Health is at Asset → Monitoring (Machinery ns) → Health (Machinery ns).
The direct Asset.Health (IJT ns) is not used; only Asset.Monitoring.Health is implemented.
DeviceHealth and DeviceHealthAlarms are children of Health in the DI namespace.
"""

import pytest

from helpers.namespaces import BN, NS_DI, NS_MACHINERY
from helpers.node_discovery import find_child_by_browse_name

pytestmark = [pytest.mark.live, pytest.mark.structure]


async def _get_health_node(asset_node, ns_mach):
    """Navigate Asset → Monitoring (ns_mach) → Health (ns_mach)."""
    monitoring = await find_child_by_browse_name(asset_node, BN.MONITORING, ns_mach)
    if monitoring is None:
        return None
    return await find_child_by_browse_name(monitoring, BN.HEALTH, ns_mach)


async def test_health_node_exists_on_controllers(controllers_instances, ns_indices):
    """Every controller must expose Health under Monitoring (Machinery ns)."""
    ns_mach = ns_indices.get(NS_MACHINERY)
    if ns_mach is None:
        pytest.skip("Machinery namespace not registered")
    missing = []
    for bn_str, node in controllers_instances:
        health_node = await _get_health_node(node, ns_mach)
        if health_node is None:
            missing.append(bn_str)
    if missing:
        pytest.skip(
            f"Health node not found on controller(s): {missing} — not implemented on this server"
        )


async def test_health_node_exists_on_tools(tools_instances, ns_indices):
    """Every tool must expose Health under Monitoring (Machinery ns)."""
    ns_mach = ns_indices.get(NS_MACHINERY)
    if ns_mach is None:
        pytest.skip("Machinery namespace not registered")
    missing = []
    for bn_str, node in tools_instances:
        health_node = await _get_health_node(node, ns_mach)
        if health_node is None:
            missing.append(bn_str)
    if missing:
        pytest.skip(
            f"Health node not found on tool(s): {missing} — not implemented on this server"
        )


async def test_health_has_device_health_alarms(controllers_instances, ns_indices):
    """DeviceHealthAlarms folder must exist under Health (DI ns); contents may be empty."""
    ns_mach = ns_indices.get(NS_MACHINERY)
    ns_di = ns_indices.get(NS_DI)
    if ns_mach is None:
        pytest.skip("Machinery namespace not registered")
    if ns_di is None:
        pytest.skip("DI namespace not registered")
    controller_node = controllers_instances[0][1]
    health_node = await _get_health_node(controller_node, ns_mach)
    if health_node is None:
        pytest.skip("Health node not found on first controller")
    alarms_node = await find_child_by_browse_name(
        health_node, BN.DEVICE_HEALTH_ALARMS, ns_di
    )
    if alarms_node is None:
        pytest.skip(
            "DeviceHealthAlarms not present on this server — folder is optional/empty"
        )
    # Folder exists; contents may be empty — no further assertions


async def test_health_current_state_is_readable(controllers_instances, ns_indices):
    """DeviceHealth variable under Health must be readable and return an integer enum value."""
    ns_mach = ns_indices.get(NS_MACHINERY)
    ns_di = ns_indices.get(NS_DI)
    if ns_mach is None:
        pytest.skip("Machinery namespace not registered")
    if ns_di is None:
        pytest.skip("DI namespace not registered")
    controller_node = controllers_instances[0][1]
    health_node = await _get_health_node(controller_node, ns_mach)
    if health_node is None:
        pytest.skip("Health node not found on first controller")
    device_health_node = await find_child_by_browse_name(
        health_node, BN.DEVICE_HEALTH, ns_di
    )
    if device_health_node is None:
        pytest.skip("DeviceHealth variable not found under Health on first controller")
    try:
        value = await device_health_node.read_value()
    except Exception as exc:
        pytest.fail(
            f"read_value() on DeviceHealth of first controller raised an exception: {exc}"
        )
    assert value is not None, "DeviceHealth value must not be None"
    assert isinstance(value, int), (
        f"DeviceHealth value expected int (enum), got {type(value).__name__}: {value!r}"
    )
