"""
Conformance tests for MachineryBuildingBlocks (MBB) and Monitoring structure.

Per OPC 40450-1 IJT Base and the OPC UA Machinery specification, every
Controller and Tool asset instance must expose a MachineryBuildingBlocks
folder (Machinery namespace) containing a Monitoring folder.  Monitoring
in turn must contain Notifications and MachineryItemState.

Conformance unit: asset_management_machinery_building_blocks

Note — LifetimeCounters:
  MachineryLifetimeCounterType requires at least one <LifetimeVariable>
  child (MandatoryPlaceholder, NodeId i=11510).  Per Machinery spec §15,
  the AddIn shall not be provided on instances when no lifetime variable
  data is available.  LifetimeCounter tests are in
  test_asset_lifetime_counters.py and are currently skipped.

Layer: structure (read-only; uses session_client / tools_instances /
       controllers_instances fixtures from conftest.py).
"""

import pytest

from helpers.namespaces import BN, NS_MACHINERY
from helpers.node_discovery import find_child_by_browse_name
from helpers.skip_reasons import skip_companion_spec_note

pytestmark = [pytest.mark.live, pytest.mark.conformance, pytest.mark.structure]


# ─── helpers ──────────────────────────────────────────────────────────────────


def _require_ns_machinery(ns_indices):
    ns_m = ns_indices.get(NS_MACHINERY)
    if ns_m is None:
        pytest.skip("Machinery namespace not registered on server")
    return ns_m


async def _mbb_of(asset_node, ns_m):
    return await find_child_by_browse_name(asset_node, BN.MACHINERY_BUILDING_BLOCKS, ns_m)


async def _monitoring_of(mbb_node, ns_m):
    return await find_child_by_browse_name(mbb_node, BN.MONITORING, ns_m)


# ─── Controllers — MachineryBuildingBlocks ────────────────────────────────────


async def test_controllers_have_machinery_building_blocks(controllers_instances, ns_indices):
    """Each controller instance must expose a MachineryBuildingBlocks folder (Machinery ns)."""
    ns_m = _require_ns_machinery(ns_indices)
    missing = []
    for name, controller_node in controllers_instances:
        node = await _mbb_of(controller_node, ns_m)
        if node is None:
            missing.append(name)
    assert not missing, f"Controllers without MachineryBuildingBlocks: {missing}"


async def test_controllers_mbb_has_monitoring_folder(controllers_instances, ns_indices):
    """MachineryBuildingBlocks on each controller must contain a Monitoring folder."""
    ns_m = _require_ns_machinery(ns_indices)
    missing = []
    for name, controller_node in controllers_instances:
        mbb = await _mbb_of(controller_node, ns_m)
        if mbb is None:
            missing.append(f"{name}(no MBB)")
            continue
        mon = await _monitoring_of(mbb, ns_m)
        if mon is None:
            missing.append(f"{name}(no Monitoring)")
    assert not missing, f"Controllers without Monitoring in MachineryBuildingBlocks: {missing}"


async def test_controllers_monitoring_has_notifications(controllers_instances, ns_indices):
    """Monitoring folder on each controller must contain a Notifications node."""
    ns_m = _require_ns_machinery(ns_indices)
    missing = []
    for name, controller_node in controllers_instances:
        mbb = await _mbb_of(controller_node, ns_m)
        if mbb is None:
            continue
        mon = await _monitoring_of(mbb, ns_m)
        if mon is None:
            continue
        notif = await find_child_by_browse_name(mon, BN.NOTIFICATIONS, ns_m)
        if notif is None:
            missing.append(name)
    if missing:
        skip_companion_spec_note(
            f"Monitoring.Notifications not exposed for controller(s) in this server profile: {missing}"
        )


async def test_controllers_monitoring_has_machinery_item_state(controllers_instances, ns_indices):
    """Monitoring folder on each controller must contain a MachineryItemState node."""
    ns_m = _require_ns_machinery(ns_indices)
    missing = []
    for name, controller_node in controllers_instances:
        mbb = await _mbb_of(controller_node, ns_m)
        if mbb is None:
            continue
        mon = await _monitoring_of(mbb, ns_m)
        if mon is None:
            continue
        mis = await find_child_by_browse_name(mon, BN.MACHINERY_ITEM_STATE, ns_m)
        if mis is None:
            missing.append(name)
    if missing:
        skip_companion_spec_note(
            f"Monitoring.MachineryItemState not exposed for controller(s) in this server profile: {missing}"
        )


# ─── Tools — MachineryBuildingBlocks ─────────────────────────────────────────


async def test_tools_have_machinery_building_blocks(tools_instances, ns_indices):
    """Each tool instance must expose a MachineryBuildingBlocks folder (Machinery ns)."""
    ns_m = _require_ns_machinery(ns_indices)
    missing = []
    for name, tool_node in tools_instances:
        node = await _mbb_of(tool_node, ns_m)
        if node is None:
            missing.append(name)
    assert not missing, f"Tools without MachineryBuildingBlocks: {missing}"


async def test_tools_mbb_has_monitoring_folder(tools_instances, ns_indices):
    """MachineryBuildingBlocks on each tool must contain a Monitoring folder."""
    ns_m = _require_ns_machinery(ns_indices)
    missing = []
    for name, tool_node in tools_instances:
        mbb = await _mbb_of(tool_node, ns_m)
        if mbb is None:
            missing.append(f"{name}(no MBB)")
            continue
        mon = await _monitoring_of(mbb, ns_m)
        if mon is None:
            missing.append(f"{name}(no Monitoring)")
    assert not missing, f"Tools without Monitoring in MachineryBuildingBlocks: {missing}"


async def test_tools_monitoring_has_notifications(tools_instances, ns_indices):
    """Monitoring folder on each tool must contain a Notifications node."""
    ns_m = _require_ns_machinery(ns_indices)
    missing = []
    for name, tool_node in tools_instances:
        mbb = await _mbb_of(tool_node, ns_m)
        if mbb is None:
            continue
        mon = await _monitoring_of(mbb, ns_m)
        if mon is None:
            continue
        notif = await find_child_by_browse_name(mon, BN.NOTIFICATIONS, ns_m)
        if notif is None:
            missing.append(name)
    if missing:
        skip_companion_spec_note(f"Monitoring.Notifications not exposed for tool(s) in this server profile: {missing}")


async def test_tools_monitoring_has_machinery_item_state(tools_instances, ns_indices):
    """Monitoring folder on each tool must contain a MachineryItemState node."""
    ns_m = _require_ns_machinery(ns_indices)
    missing = []
    for name, tool_node in tools_instances:
        mbb = await _mbb_of(tool_node, ns_m)
        if mbb is None:
            continue
        mon = await _monitoring_of(mbb, ns_m)
        if mon is None:
            continue
        mis = await find_child_by_browse_name(mon, BN.MACHINERY_ITEM_STATE, ns_m)
        if mis is None:
            missing.append(name)
    if missing:
        skip_companion_spec_note(
            f"Monitoring.MachineryItemState not exposed for tool(s) in this server profile: {missing}"
        )


async def test_tools_monitoring_has_health_folder(tools_instances, ns_indices):
    """Monitoring.Health must be present on each tool (OPC UA Machinery spec — required sub-folder)."""
    ns_m = _require_ns_machinery(ns_indices)
    missing = []
    for name, tool_node in tools_instances:
        mbb = await _mbb_of(tool_node, ns_m)
        if mbb is None:
            missing.append(f"{name}(no MBB)")
            continue
        mon = await _monitoring_of(mbb, ns_m)
        if mon is None:
            missing.append(f"{name}(no Monitoring)")
            continue
        health = await find_child_by_browse_name(mon, BN.HEALTH, ns_m)
        if health is None:
            missing.append(name)
    assert not missing, f"Tools without Monitoring.Health: {missing}"


async def test_tools_monitoring_health_has_device_health(tools_instances, ns_indices):
    """Monitoring.Health on each tool must expose a DeviceHealth variable (OPC UA DI)."""
    from helpers.namespaces import NS_DI

    ns_m = _require_ns_machinery(ns_indices)
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered — cannot look up DeviceHealth")
    missing = []
    for name, tool_node in tools_instances:
        mbb = await _mbb_of(tool_node, ns_m)
        if mbb is None:
            continue
        mon = await _monitoring_of(mbb, ns_m)
        if mon is None:
            continue
        health = await find_child_by_browse_name(mon, BN.HEALTH, ns_m)
        if health is None:
            continue
        dh = await find_child_by_browse_name(health, BN.DEVICE_HEALTH, ns_di)
        if dh is None:
            missing.append(name)
    assert not missing, f"Tools without Monitoring.Health.DeviceHealth: {missing}"


async def test_tools_monitoring_has_consumption_folder(tools_instances, ns_indices):
    """Monitoring.Consumption must be present on each tool (OPC UA Machinery spec)."""
    ns_m = _require_ns_machinery(ns_indices)
    missing = []
    for name, tool_node in tools_instances:
        mbb = await _mbb_of(tool_node, ns_m)
        if mbb is None:
            continue
        mon = await _monitoring_of(mbb, ns_m)
        if mon is None:
            continue
        node = await find_child_by_browse_name(mon, BN.CONSUMPTION, ns_m)
        if node is None:
            missing.append(name)
    assert not missing, f"Tools without Monitoring.Consumption: {missing}"


async def test_tools_monitoring_has_process_folder(tools_instances, ns_indices):
    """Monitoring.Process must be present on each tool (OPC UA Machinery spec)."""
    ns_m = _require_ns_machinery(ns_indices)
    missing = []
    for name, tool_node in tools_instances:
        mbb = await _mbb_of(tool_node, ns_m)
        if mbb is None:
            continue
        mon = await _monitoring_of(mbb, ns_m)
        if mon is None:
            continue
        node = await find_child_by_browse_name(mon, BN.PROCESS, ns_m)
        if node is None:
            missing.append(name)
    assert not missing, f"Tools without Monitoring.Process: {missing}"


async def test_tools_monitoring_has_status_folder(tools_instances, ns_indices):
    """Monitoring.Status must be present on each tool (OPC UA Machinery spec)."""
    ns_m = _require_ns_machinery(ns_indices)
    missing = []
    for name, tool_node in tools_instances:
        mbb = await _mbb_of(tool_node, ns_m)
        if mbb is None:
            continue
        mon = await _monitoring_of(mbb, ns_m)
        if mon is None:
            continue
        node = await find_child_by_browse_name(mon, BN.STATUS, ns_m)
        if node is None:
            missing.append(name)
    assert not missing, f"Tools without Monitoring.Status: {missing}"
