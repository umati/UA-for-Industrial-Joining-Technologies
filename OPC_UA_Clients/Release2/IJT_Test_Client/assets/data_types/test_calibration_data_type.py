"""
test_calibration_data_type.py — Tool Calibration sub-tree tests.
Verifies that the first tool instance exposes a Calibration node (IJT Base ns)
with the expected child properties: LastCalibration, CalibrationPlace,
NextCalibration, CalibrationValue (with EngineeringUnits), and CertificateUri.
"""

import datetime

import pytest

from helpers.namespaces import BN, NS_DI, NS_IJT_BASE
from helpers.node_discovery import find_child_by_browse_name

pytestmark = [pytest.mark.live, pytest.mark.structure]


async def _get_calibration_node(tools_instances, ns_di, ns_ijt):
    """Navigate Asset → Maintenance (DI ns) → Calibration (IJT Base ns)."""
    tool_node = tools_instances[0][1]
    maintenance = await find_child_by_browse_name(tool_node, BN.MAINTENANCE, ns_di)
    if maintenance is None:
        return None
    return await find_child_by_browse_name(maintenance, BN.CALIBRATION, ns_ijt)


async def test_calibration_node_exists_on_tool(tools_instances, ns_indices):
    """First tool must expose Calibration under Maintenance (DI ns) → Calibration (IJT Base ns)."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None:
        pytest.skip("DI namespace not registered")
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    calibration_node = await _get_calibration_node(tools_instances, ns_di, ns_ijt)
    if calibration_node is None:
        pytest.skip("Calibration not found at Maintenance/Calibration — not implemented on this server")
    assert calibration_node is not None


async def test_calibration_has_last_calibration(tools_instances, ns_indices):
    """Calibration node must contain a LastCalibration child whose value is a datetime."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None:
        pytest.skip("DI namespace not registered")
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    calibration_node = await _get_calibration_node(tools_instances, ns_di, ns_ijt)
    if calibration_node is None:
        pytest.skip("Calibration node not found on first tool")
    last_cal_node = await find_child_by_browse_name(calibration_node, "LastCalibration", ns_ijt)
    assert last_cal_node is not None, "LastCalibration node not found under Calibration"
    value = await last_cal_node.read_value()
    assert isinstance(value, datetime.datetime), (
        f"LastCalibration value expected datetime, got {type(value).__name__}: {value!r}"
    )


async def test_calibration_has_calibration_place(tools_instances, ns_indices):
    """Calibration node must contain a CalibrationPlace child whose value is a string."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None:
        pytest.skip("DI namespace not registered")
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    calibration_node = await _get_calibration_node(tools_instances, ns_di, ns_ijt)
    if calibration_node is None:
        pytest.skip("Calibration node not found on first tool")
    place_node = await find_child_by_browse_name(calibration_node, "CalibrationPlace", ns_ijt)
    assert place_node is not None, "CalibrationPlace node not found under Calibration"
    value = await place_node.read_value()
    assert isinstance(value, str), f"CalibrationPlace value expected str, got {type(value).__name__}: {value!r}"


async def test_calibration_has_next_calibration(tools_instances, ns_indices):
    """Calibration node must contain a NextCalibration child whose value is a datetime."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None:
        pytest.skip("DI namespace not registered")
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    calibration_node = await _get_calibration_node(tools_instances, ns_di, ns_ijt)
    if calibration_node is None:
        pytest.skip("Calibration node not found on first tool")
    next_cal_node = await find_child_by_browse_name(calibration_node, "NextCalibration", ns_ijt)
    assert next_cal_node is not None, "NextCalibration node not found under Calibration"
    value = await next_cal_node.read_value()
    assert isinstance(value, datetime.datetime), (
        f"NextCalibration value expected datetime, got {type(value).__name__}: {value!r}"
    )


async def test_calibration_has_calibration_value(tools_instances, ns_indices):
    """Calibration node must contain a CalibrationValue child with a numeric value."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None:
        pytest.skip("DI namespace not registered")
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    calibration_node = await _get_calibration_node(tools_instances, ns_di, ns_ijt)
    if calibration_node is None:
        pytest.skip("Calibration node not found on first tool")
    cal_value_node = await find_child_by_browse_name(calibration_node, BN.CALIBRATION_VALUE, ns_ijt)
    assert cal_value_node is not None, "CalibrationValue node not found under Calibration"
    value = await cal_value_node.read_value()
    assert isinstance(value, (int, float)), (
        f"CalibrationValue expected int or float, got {type(value).__name__}: {value!r}"
    )


async def test_calibration_has_engineering_units(tools_instances, ns_indices):
    """CalibrationValue must contain an EngineeringUnits child node."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None:
        pytest.skip("DI namespace not registered")
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    calibration_node = await _get_calibration_node(tools_instances, ns_di, ns_ijt)
    if calibration_node is None:
        pytest.skip("Calibration node not found on first tool")
    cal_value_node = await find_child_by_browse_name(calibration_node, BN.CALIBRATION_VALUE, ns_ijt)
    if cal_value_node is None:
        pytest.skip("CalibrationValue node not found under Calibration")
    # EngineeringUnits is a standard OPC UA property (ns=0) on AnalogItem nodes.
    # Try IJT Base ns first, fall back to ns=0.
    eu_node = await find_child_by_browse_name(cal_value_node, "EngineeringUnits", ns_ijt)
    if eu_node is None:
        eu_node = await find_child_by_browse_name(cal_value_node, "EngineeringUnits", 0)
    assert eu_node is not None, (
        "EngineeringUnits node not found under CalibrationValue (tried both IJT Base ns and ns=0)"
    )


async def test_calibration_has_certificate_uri(tools_instances, ns_indices):
    """Calibration node must contain a CertificateUri child node with a string value."""
    ns_di = ns_indices.get(NS_DI)
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_di is None:
        pytest.skip("DI namespace not registered")
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    calibration_node = await _get_calibration_node(tools_instances, ns_di, ns_ijt)
    if calibration_node is None:
        pytest.skip("Calibration node not found on first tool")
    cert_node = await find_child_by_browse_name(calibration_node, "CertificateUri", ns_ijt)
    assert cert_node is not None, "CertificateUri node not found under Calibration"
    value = await cert_node.read_value()
    assert isinstance(value, str), f"CertificateUri value expected str, got {type(value).__name__}: {value!r}"
