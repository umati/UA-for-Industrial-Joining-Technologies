"""
test_asset_lifetime_counters.py — LifetimeCounters AddIn conformance tests.

MachineryLifetimeCounterType (Machinery spec §15) serves as an AddIn on asset
MachineryBuildingBlocks and must contain at least one <LifetimeVariable> child
(MandatoryPlaceholder, ModellingRule i=11510).

Per Machinery spec §15: if no lifetime variable data is available, the AddIn
shall NOT be provided on the instance. These tests are currently skipped because
the IJT OPC UA Server does not yet expose real lifetime counter data.

Enable and implement when real lifetime counter data is available on the server
(e.g. NumberOfTightenings per tool against a service-limit LimitValue).
"""

import pytest

from helpers.namespaces import BN, NS_MACHINERY
from helpers.node_discovery import find_child_by_browse_name

pytestmark = [pytest.mark.live, pytest.mark.structure]

_SKIP_REASON = (
    "LifetimeCounters AddIn omitted because no real lifetime-variable data is available; "
    "MachineryLifetimeCounterType requires at least one <LifetimeVariable> "
    "(MandatoryPlaceholder, i=11510), and Machinery §15 says the AddIn shall not be provided "
    "when no lifetime variable data exists."
)


def _require_ns_machinery(ns_indices):
    ns_m = ns_indices.get(NS_MACHINERY)
    if ns_m is None:
        pytest.skip("Machinery namespace not registered on server")
    return ns_m


# ---------------------------------------------------------------------------
# Tools — LifetimeCounters presence
# ---------------------------------------------------------------------------


@pytest.mark.skip(reason=_SKIP_REASON)
async def test_tools_mbb_has_lifetime_counters(tools_instances, ns_indices):
    """Every tool MachineryBuildingBlocks must contain a LifetimeCounters AddIn (Machinery ns)."""
    ns_m = _require_ns_machinery(ns_indices)
    missing = []
    for name, tool_node in tools_instances:
        mbb = await find_child_by_browse_name(tool_node, BN.MACHINERY_BUILDING_BLOCKS, ns_m)
        if mbb is None:
            missing.append(f"{name}(no MBB)")
            continue
        lc = await find_child_by_browse_name(mbb, BN.LIFETIME_COUNTERS, ns_m)
        if lc is None:
            missing.append(name)
    assert not missing, f"Tools without LifetimeCounters in MachineryBuildingBlocks: {missing}"


@pytest.mark.skip(reason=_SKIP_REASON)
async def test_tools_lifetime_counters_has_variable(tools_instances, ns_indices):
    """LifetimeCounters on each tool must have at least one LifetimeVariable child."""
    ns_m = _require_ns_machinery(ns_indices)
    empty = []
    for name, tool_node in tools_instances:
        mbb = await find_child_by_browse_name(tool_node, BN.MACHINERY_BUILDING_BLOCKS, ns_m)
        if mbb is None:
            continue
        lc = await find_child_by_browse_name(mbb, BN.LIFETIME_COUNTERS, ns_m)
        if lc is None:
            continue
        children = await lc.get_children()
        if not children:
            empty.append(name)
    assert not empty, f"Tools with empty LifetimeCounters (no LifetimeVariable children): {empty}"


# ---------------------------------------------------------------------------
# Controllers — LifetimeCounters presence
# ---------------------------------------------------------------------------


@pytest.mark.skip(reason=_SKIP_REASON)
async def test_controllers_mbb_has_lifetime_counters(controllers_instances, ns_indices):
    """Every controller MachineryBuildingBlocks must contain a LifetimeCounters AddIn (Machinery ns)."""
    ns_m = _require_ns_machinery(ns_indices)
    missing = []
    for name, ctrl_node in controllers_instances:
        mbb = await find_child_by_browse_name(ctrl_node, BN.MACHINERY_BUILDING_BLOCKS, ns_m)
        if mbb is None:
            missing.append(f"{name}(no MBB)")
            continue
        lc = await find_child_by_browse_name(mbb, BN.LIFETIME_COUNTERS, ns_m)
        if lc is None:
            missing.append(name)
    assert not missing, f"Controllers without LifetimeCounters in MachineryBuildingBlocks: {missing}"


@pytest.mark.skip(reason=_SKIP_REASON)
async def test_controllers_lifetime_counters_has_variable(controllers_instances, ns_indices):
    """LifetimeCounters on each controller must have at least one LifetimeVariable child."""
    ns_m = _require_ns_machinery(ns_indices)
    empty = []
    for name, ctrl_node in controllers_instances:
        mbb = await find_child_by_browse_name(ctrl_node, BN.MACHINERY_BUILDING_BLOCKS, ns_m)
        if mbb is None:
            continue
        lc = await find_child_by_browse_name(mbb, BN.LIFETIME_COUNTERS, ns_m)
        if lc is None:
            continue
        children = await lc.get_children()
        if not children:
            empty.append(name)
    assert not empty, f"Controllers with empty LifetimeCounters (no LifetimeVariable children): {empty}"
