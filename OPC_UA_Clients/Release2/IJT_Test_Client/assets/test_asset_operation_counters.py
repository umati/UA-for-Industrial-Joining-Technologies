"""
test_asset_operation_counters.py — OperationCounters sub-tree tests.
Verifies that the first controller exposes an OperationCounters node (DI ns)
containing OperationCycleCounter, OperationDuration, and PowerOnDuration children,
and that counter values are non-negative numbers.
"""

import pytest

from helpers.namespaces import BN, NS_DI
from helpers.node_discovery import find_child_by_browse_name

pytestmark = [pytest.mark.live, pytest.mark.structure]


async def test_operation_counters_exists(controllers_instances, ns_indices):
    """First controller must expose an OperationCounters child node (DI namespace)."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered")
    asset_node = controllers_instances[0][1]
    op_counters = await find_child_by_browse_name(asset_node, BN.OPERATION_COUNTERS, ns_di)
    assert op_counters is not None, "OperationCounters node (DI ns) not found on first controller"


async def test_operation_cycle_counter_present(controllers_instances, ns_indices):
    """OperationCounters must contain an OperationCycleCounter child with a readable value."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered")
    asset_node = controllers_instances[0][1]
    op_counters = await find_child_by_browse_name(asset_node, BN.OPERATION_COUNTERS, ns_di)
    if op_counters is None:
        pytest.skip("OperationCounters node not found on first controller")
    counter_node = await find_child_by_browse_name(op_counters, BN.OPERATION_CYCLE_COUNTER, ns_di)
    assert counter_node is not None, "OperationCycleCounter node not found under OperationCounters"
    value = await counter_node.read_value()
    assert value is not None, "OperationCycleCounter value must not be None"


async def test_operation_duration_present(controllers_instances, ns_indices):
    """OperationCounters must contain an OperationDuration child with a readable value."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered")
    asset_node = controllers_instances[0][1]
    op_counters = await find_child_by_browse_name(asset_node, BN.OPERATION_COUNTERS, ns_di)
    if op_counters is None:
        pytest.skip("OperationCounters node not found on first controller")
    duration_node = await find_child_by_browse_name(op_counters, BN.OPERATION_DURATION, ns_di)
    assert duration_node is not None, "OperationDuration node not found under OperationCounters"
    value = await duration_node.read_value()
    assert value is not None, "OperationDuration value must not be None"


async def test_power_on_duration_present(controllers_instances, ns_indices):
    """OperationCounters must contain a PowerOnDuration child with a readable value."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered")
    asset_node = controllers_instances[0][1]
    op_counters = await find_child_by_browse_name(asset_node, BN.OPERATION_COUNTERS, ns_di)
    if op_counters is None:
        pytest.skip("OperationCounters node not found on first controller")
    power_on_node = await find_child_by_browse_name(op_counters, BN.POWER_ON_DURATION, ns_di)
    assert power_on_node is not None, "PowerOnDuration node not found under OperationCounters"
    value = await power_on_node.read_value()
    assert value is not None, "PowerOnDuration value must not be None"


async def test_counter_values_are_non_negative(controllers_instances, ns_indices):
    """OperationCycleCounter value must be a non-negative number."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered")
    asset_node = controllers_instances[0][1]
    op_counters = await find_child_by_browse_name(asset_node, BN.OPERATION_COUNTERS, ns_di)
    if op_counters is None:
        pytest.skip("OperationCounters node not found on first controller")
    counter_node = await find_child_by_browse_name(op_counters, BN.OPERATION_CYCLE_COUNTER, ns_di)
    if counter_node is None:
        pytest.skip("OperationCycleCounter node not found under OperationCounters")
    raw_value = await counter_node.read_value()
    numeric_value = float(raw_value)
    assert numeric_value >= 0, f"OperationCycleCounter must be >= 0, got {numeric_value}"
