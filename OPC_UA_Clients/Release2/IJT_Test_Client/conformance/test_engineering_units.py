"""
Conformance tests for Engineering Units — OPC 40450-1 IJT Base.

Covered conformance unit:

    engineering_units
        The Server uses EUInformation type for ResultValueDataType.EngineeringUnits
        as defined in OPC UA Part 8. The UnitId maps to UNECE codes.
        DisplayName and Description describe the physical unit.
"""

import logging

import pytest
from asyncua import ua

from helpers.cu_registry import CU
from helpers.method_caller import call_method
from helpers.method_signature import JOINT_METHOD_INPUTS, assert_input_argument_names
from helpers.namespaces import NS_APP, NS_DI, NS_IJT_BASE, ResultType
from helpers.node_discovery import find_child_by_browse_name, find_joining_system, read_tool_product_instance_uri
from helpers.result_collector import ResultCollector
from helpers.result_navigation import collect_result_values, unwrap_variant
from helpers.result_validator import (
    ResultValueValidator,
    ValidationContext,
    ValidationResult,
)
from helpers.skip_reasons import skip_accepted_policy

logger = logging.getLogger(__name__)
pytestmark = [pytest.mark.live, pytest.mark.conformance]

# UNECE namespace URI mandated by OPC UA Part 8
_UNECE_NAMESPACE_URI = "http://www.opcfoundation.org/UA/units/un/cefact"

# PhysicalQuantityEnumeration values (OPC 40450-1, ResultValueDataType.PhysicalQuantity)
_PHYSICAL_QUANTITY_TORQUE: int = 2  # torque physical quantity
_PHYSICAL_QUANTITY_ANGLE: int = 3  # angle physical quantity

# EUInformation UnitIds for tightening-relevant physical quantities.
# Source: OPC UA Part 8 Annex C (EUInformation); values are signed Int32
# derived from the four-character UNECE unit codes.
_NEWTON_METRE_EU_IDENTIFIER: int = 20053  # newton-metre (N·m), UNECE code "NU"
_POUND_FORCE_FOOT_EU_IDENTIFIER: int = 4609340  # pound-force foot (lbf·ft)
_NEWTON_CENTIMETRE_EU_IDENTIFIER: int = 4740940  # newton-centimetre (N·cm)
_NEWTON_MILLIMETRE_EU_IDENTIFIER: int = 4477132  # newton-millimetre (N·mm)

_DEGREE_OF_ARC_EU_IDENTIFIER: int = 17476  # degree of arc (°), UNECE code "DD"
_RADIAN_EU_IDENTIFIER: int = 4405297  # radian (rad)
_MILLIRADIAN_EU_IDENTIFIER: int = 4870725  # milliradian (mrad)

# Sets of known-good EU identifiers grouped by physical quantity
_KNOWN_TORQUE_EU_IDENTIFIERS: frozenset[int] = frozenset(
    {
        _NEWTON_METRE_EU_IDENTIFIER,
        _POUND_FORCE_FOOT_EU_IDENTIFIER,
        _NEWTON_CENTIMETRE_EU_IDENTIFIER,
        _NEWTON_MILLIMETRE_EU_IDENTIFIER,
    }
)
_KNOWN_ANGLE_EU_IDENTIFIERS: frozenset[int] = frozenset(
    {
        _DEGREE_OF_ARC_EU_IDENTIFIER,
        _RADIAN_EU_IDENTIFIER,
        _MILLIRADIAN_EU_IDENTIFIER,
    }
)


# ---------------------------------------------------------------------------
# Module helpers
# ---------------------------------------------------------------------------


async def _trigger_and_get_result(subscription_client, result_trigger, ns_indices, result_type, include_traces=False):
    """Trigger a result and collect it via IJTResultEventType events."""
    async with ResultCollector(subscription_client, ns_indices, is_simulator=result_trigger.is_simulator) as rc:
        outcome = await result_trigger.trigger_single(result_type, include_traces=include_traces)
        if not outcome.triggered and result_trigger.is_simulator:
            return None
        return await rc.collect_single()


def _collect_all_result_values(result_data) -> list:
    """Return every ResultValueDataType from a result and its sub-results."""
    return collect_result_values(result_data)


def _values_with_eu(all_values: list) -> list:
    """Filter to only ResultValueDataType entries that carry EngineeringUnits."""
    return [v for v in (unwrap_variant(v) for v in all_values) if getattr(v, "EngineeringUnits", None) is not None]


def _values_for_quantity(all_values: list, physical_quantity_int: int) -> list:
    """Filter to values whose PhysicalQuantity matches the given integer."""
    result = []
    for v in all_values:
        v = unwrap_variant(v)
        pq = getattr(v, "PhysicalQuantity", None)
        if pq is None:
            continue
        try:
            if int(pq) == physical_quantity_int:
                result.append(v)
        except (TypeError, ValueError):
            pass
    return result


# ─── engineering_units ───


@pytest.mark.requires_cu(CU.ENGINEERING_UNITS)
async def test_result_values_engineering_units_use_eu_information_type(subscription_client, result_trigger, ns_indices):
    """The Server uses EUInformation type for ResultValueDataType.EngineeringUnits as defined in OPC UA Part 8. The UnitId maps to UNECE codes. DisplayName and Description describe the physical unit."""
    result_data = await _trigger_and_get_result(
        subscription_client, result_trigger, ns_indices, ResultType.MULTI_STEP_OK_RESULT
    )
    if result_data is None:
        pytest.skip("Could not retrieve multi-step result for EU type check")

    all_values = _collect_all_result_values(result_data)
    if not all_values:
        pytest.skip("No ResultValueDataType entries found in result")

    failures: list[str] = []
    for idx, value in enumerate(all_values):
        eu = getattr(value, "EngineeringUnits", None)
        if eu is None:
            continue
        eu = getattr(eu, "Value", eu)  # unwrap nested Variant

        if not hasattr(eu, "UnitId"):
            failures.append(
                f"value[{idx}].EngineeringUnits has no .UnitId attribute "
                f"(expected EUInformation, got {type(eu).__name__!r})"
            )

        ns_uri = getattr(eu, "NamespaceUri", None)
        if ns_uri is not None and str(ns_uri).strip():
            if str(ns_uri) != _UNECE_NAMESPACE_URI:
                failures.append(
                    f"value[{idx}].EngineeringUnits.NamespaceUri={ns_uri!r}, expected {_UNECE_NAMESPACE_URI!r}"
                )

    assert not failures, "EngineeringUnits validation failures:\n  " + "\n  ".join(failures)


@pytest.mark.requires_cu(CU.ENGINEERING_UNITS)
async def test_torque_values_have_expected_engineering_units_identifier(
    subscription_client, result_trigger, ns_indices
):
    """Torque ResultValues must use a known UNECE torque EU identifier (newton-metre, pound-force foot, etc.)."""
    result_data = await _trigger_and_get_result(
        subscription_client, result_trigger, ns_indices, ResultType.MULTI_STEP_OK_RESULT
    )
    if result_data is None:
        pytest.skip("Could not retrieve multi-step result for torque EU check")

    all_values = _collect_all_result_values(result_data)
    torque_values = _values_for_quantity(all_values, _PHYSICAL_QUANTITY_TORQUE)
    if not torque_values:
        pytest.skip("No torque ResultValues found — cannot verify torque EU identifiers")

    torque_with_eu = _values_with_eu(torque_values)
    if not torque_with_eu:
        pytest.skip(
            "Torque values present but none carry EngineeringUnits — EU is optional per spec; skipping identifier check"
        )

    failures: list[str] = []
    for idx, value in enumerate(torque_with_eu):
        eu = value.EngineeringUnits
        eu = getattr(eu, "Value", eu)  # unwrap nested Variant
        identifier = getattr(eu, "UnitId", None)
        if identifier is None:
            failures.append(f"torque_value[{idx}].EngineeringUnits.UnitId is None")
            continue
        try:
            id_int = int(identifier)
        except (TypeError, ValueError):
            failures.append(f"torque_value[{idx}].EngineeringUnits.UnitId={identifier!r} is not an integer")
            continue
        if id_int not in _KNOWN_TORQUE_EU_IDENTIFIERS:
            failures.append(
                f"torque_value[{idx}].EngineeringUnits.UnitId={id_int!r} not in "
                f"known torque set {sorted(_KNOWN_TORQUE_EU_IDENTIFIERS)}"
            )

    assert not failures, "Torque EU identifier failures:\n  " + "\n  ".join(failures)


@pytest.mark.requires_cu(CU.ENGINEERING_UNITS)
async def test_angle_values_have_expected_engineering_units_identifier(subscription_client, result_trigger, ns_indices):
    """Angle ResultValues must use a known UNECE angle EU identifier (degree, radian, milliradian)."""
    result_data = await _trigger_and_get_result(
        subscription_client, result_trigger, ns_indices, ResultType.MULTI_STEP_OK_RESULT
    )
    if result_data is None:
        pytest.skip("Could not retrieve multi-step result for angle EU check")

    all_values = _collect_all_result_values(result_data)
    angle_values = _values_for_quantity(all_values, _PHYSICAL_QUANTITY_ANGLE)
    if not angle_values:
        pytest.skip("No angle ResultValues found — cannot verify angle EU identifiers")

    angle_with_eu = _values_with_eu(angle_values)
    if not angle_with_eu:
        pytest.skip(
            "Angle values present but none carry EngineeringUnits — EU is optional per spec; skipping identifier check"
        )

    failures: list[str] = []
    for idx, value in enumerate(angle_with_eu):
        eu = value.EngineeringUnits
        eu = getattr(eu, "Value", eu)  # unwrap Variant → EUInformation
        identifier = getattr(eu, "UnitId", None)
        if identifier is None:
            failures.append(f"angle_value[{idx}].EngineeringUnits.UnitId is None")
            continue
        try:
            id_int = int(identifier)
        except (TypeError, ValueError):
            failures.append(f"angle_value[{idx}].EngineeringUnits.UnitId={identifier!r} is not an integer")
            continue
        if id_int not in _KNOWN_ANGLE_EU_IDENTIFIERS:
            failures.append(
                f"angle_value[{idx}].EngineeringUnits.UnitId={id_int!r} not in "
                f"known angle set {sorted(_KNOWN_ANGLE_EU_IDENTIFIERS)}"
            )

    assert not failures, "Angle EU identifier failures:\n  " + "\n  ".join(failures)


@pytest.mark.requires_cu(CU.ENGINEERING_UNITS)
async def test_engineering_units_identifier_is_a_positive_integer(subscription_client, result_trigger, ns_indices):
    """EngineeringUnits.UnitId must be a positive integer — all UNECE codes are positive."""
    result_data = await _trigger_and_get_result(
        subscription_client, result_trigger, ns_indices, ResultType.MULTI_STEP_OK_RESULT
    )
    if result_data is None:
        pytest.skip("Could not retrieve multi-step result for EU identifier type check")

    all_values = _collect_all_result_values(result_data)
    checked = 0
    failures: list[str] = []

    for idx, value in enumerate(all_values):
        eu = getattr(value, "EngineeringUnits", None)
        if eu is None:
            continue
        eu = getattr(eu, "Value", eu)  # unwrap nested Variant
        identifier = getattr(eu, "UnitId", None)
        if identifier is None:
            failures.append(f"value[{idx}].EngineeringUnits.UnitId is None")
            continue
        try:
            id_int = int(identifier)
        except (TypeError, ValueError):
            failures.append(f"value[{idx}].EngineeringUnits.UnitId={identifier!r} cannot be converted to int")
            continue
        if id_int <= 0:
            failures.append(
                f"value[{idx}].EngineeringUnits.UnitId={id_int!r} is not positive "
                f"(all UNECE codes must be greater than zero)"
            )
        checked += 1

    if checked == 0:
        pytest.skip(
            "CU.ENGINEERING_UNITS declared but EU field absent in ResultValues — "
            "server declared CU.ENGINEERING_UNITS but no ResultValues carry an EngineeringUnits field; "
            "verify server populates EU on result values"
        )

    assert not failures, "EU UnitId type failures:\n  " + "\n  ".join(failures)


@pytest.mark.requires_cu(CU.ENGINEERING_UNITS)
async def test_all_result_value_eu_identifiers_pass_result_value_validator(
    subscription_client, result_trigger, ns_indices
):
    """Every ResultValueDataType in a multi-step result must pass the ResultValueValidator EU check."""
    result_data = await _trigger_and_get_result(
        subscription_client, result_trigger, ns_indices, ResultType.MULTI_STEP_OK_RESULT
    )
    if result_data is None:
        pytest.skip("Could not retrieve multi-step result for comprehensive EU check")

    all_values = _collect_all_result_values(result_data)
    values_with_eu = _values_with_eu(all_values)
    if not values_with_eu:
        pytest.skip(
            "CU.ENGINEERING_UNITS declared but EU field absent in ResultValues — "
            "server declared CU.ENGINEERING_UNITS but no ResultValues carry an EngineeringUnits field; "
            "verify server populates EU on result values"
        )

    vr = ValidationResult()
    validator = ResultValueValidator()
    for idx, value in enumerate(values_with_eu):
        validator.validate(value, ValidationContext(f"ResultValue[{idx}]"), vr)

    vr.assert_no_failures()


@pytest.mark.requires_cu(CU.ENGINEERING_UNITS)
@pytest.mark.parametrize(
    "result_type,description",
    [
        (ResultType.ONE_STEP_OK_RESULT, "one-step"),
        (ResultType.MULTI_STEP_OK_RESULT, "multi-step"),
    ],
)
async def test_engineering_units_are_consistent_within_same_physical_quantity(
    subscription_client,
    result_trigger,
    ns_indices,
    result_type,
    description,
):
    """For the same PhysicalQuantity within a single result, EU identifiers must be consistent."""
    async with ResultCollector(subscription_client, ns_indices, is_simulator=result_trigger.is_simulator) as rc:
        outcome = await result_trigger.trigger_single(result_type=result_type, include_traces=False)
        if not outcome.triggered and result_trigger.is_simulator:
            pytest.skip(outcome.skip_reason if hasattr(outcome, "skip_reason") else "Trigger failed")
        result_data = await rc.collect_single()
    if result_data is None:
        pytest.skip(f"No result received for {description} result type")

    all_values = _collect_all_result_values(result_data)

    by_quantity: dict[int, list[int]] = {}
    for value in all_values:
        eu = getattr(value, "EngineeringUnits", None)
        if eu is None:
            continue
        eu = getattr(eu, "Value", eu)  # unwrap nested Variant
        pq = getattr(value, "PhysicalQuantity", None)
        if pq is None:
            continue
        identifier = getattr(eu, "UnitId", None)
        if identifier is None:
            continue
        try:
            by_quantity.setdefault(int(pq), []).append(int(identifier))
        except (TypeError, ValueError):
            pass

    if not by_quantity:
        pytest.skip(
            f"No ResultValues with both PhysicalQuantity and EngineeringUnits found "
            f"in {description} result — cannot check consistency"
        )

    failures: list[str] = []
    for pq_int, identifiers in by_quantity.items():
        unique_ids = set(identifiers)
        if len(unique_ids) > 1:
            failures.append(
                f"PhysicalQuantity={pq_int}: inconsistent EU identifiers within "
                f"{description} result: {sorted(unique_ids)}"
            )

    assert not failures, f"EU consistency failures in {description} result:\n  " + "\n  ".join(failures)


# ---------------------------------------------------------------------------
# ─── engineering_units additional tests ───
# ---------------------------------------------------------------------------


@pytest.mark.requires_cu(CU.ENGINEERING_UNITS)
async def test_trace_content_data_type_has_engineering_units(subscription_client, result_trigger, ns_indices):
    """Every TraceContentDataType in a multi-step result must carry EngineeringUnits with UnitId and NamespaceUri."""
    result_data = await _trigger_and_get_result(
        subscription_client,
        result_trigger,
        ns_indices,
        ResultType.MULTI_STEP_OK_RESULT,
        include_traces=True,
    )
    if result_data is None:
        pytest.skip("Could not retrieve multi-step result for trace content EU check")

    content = getattr(result_data, "ResultContent", None)
    if not isinstance(content, (list, tuple)):
        pytest.skip("No ResultContent in result — trace content EU check not possible")

    trace_values: list = []
    for item in content:
        item = getattr(item, "Value", item)  # unwrap asyncua Variant
        step_results = getattr(item, "StepResults", None)
        if not isinstance(step_results, (list, tuple)):
            continue
        for step in step_results:
            step = unwrap_variant(step)
            step_traces = getattr(step, "StepTraces", None)
            if not isinstance(step_traces, (list, tuple)):
                continue
            for trace in step_traces:
                trace = unwrap_variant(trace)
                trace_content = getattr(trace, "StepTraceContent", None)
                if isinstance(trace_content, (list, tuple)):
                    trace_values.extend(unwrap_variant(tc) for tc in trace_content)

    if not trace_values:
        skip_accepted_policy(
            "trace content is not present in this result; result-value engineering-unit coverage remains available",
            method="Result Trace",
        )

    failures: list[str] = []
    for idx, tc in enumerate(trace_values):
        eu = getattr(tc, "EngineeringUnits", None)
        if eu is None:
            continue
        eu = getattr(eu, "Value", eu)  # unwrap nested Variant
        if not hasattr(eu, "UnitId"):
            failures.append(
                f"TraceContent[{idx}].EngineeringUnits has no UnitId attribute (type: {type(eu).__name__!r})"
            )
            continue
        identifier = getattr(eu, "UnitId", None)
        if identifier is None:
            failures.append(f"TraceContent[{idx}].EngineeringUnits.UnitId is None")
        ns_uri = getattr(eu, "NamespaceUri", None)
        if ns_uri is None:
            logger.info("TraceContent[%d].EngineeringUnits.NamespaceUri absent — optional", idx)

    assert not failures, "TraceContent EngineeringUnits validation failures:\n  " + "\n  ".join(failures)


@pytest.mark.requires_cu(CU.ENGINEERING_UNITS)
async def test_reported_value_data_type_in_event_has_engineering_units(subscription_client, result_trigger, ns_indices):
    """Every ReportedValueDataType in a result must carry EngineeringUnits with a valid UnitId."""
    result_data = await _trigger_and_get_result(
        subscription_client, result_trigger, ns_indices, ResultType.MULTI_STEP_OK_RESULT
    )
    if result_data is None:
        pytest.skip("Could not retrieve multi-step result for reported value EU check")

    reported_values: list = []
    for attr in ("ReportedValues", "OverallReportedValues"):
        vals = getattr(result_data, attr, None)
        if isinstance(vals, (list, tuple)):
            reported_values.extend(unwrap_variant(v) for v in vals)

    meta = getattr(result_data, "ResultMetaData", None)
    if meta is not None:
        for attr in ("ReportedValues", "OverallReportedValues"):
            vals = getattr(meta, attr, None)
            if isinstance(vals, (list, tuple)):
                reported_values.extend(unwrap_variant(v) for v in vals)

    content = getattr(result_data, "ResultContent", None)
    if isinstance(content, (list, tuple)):
        for item in content:
            item = getattr(item, "Value", item)  # unwrap asyncua Variant
            for attr in ("ReportedValues",):
                vals = getattr(item, attr, None)
                if isinstance(vals, (list, tuple)):
                    reported_values.extend(unwrap_variant(v) for v in vals)

    if not reported_values:
        logger.info("No ReportedValueDataType entries found in result — optional field absent")
        return

    failures: list[str] = []
    for idx, rv in enumerate(reported_values):
        eu = getattr(rv, "EngineeringUnits", None)
        if eu is None:
            continue
        eu = getattr(eu, "Value", eu)  # unwrap nested Variant
        identifier = getattr(eu, "UnitId", None)
        if identifier is None:
            failures.append(f"ReportedValue[{idx}].EngineeringUnits.UnitId is None")

    assert not failures, "ReportedValue EngineeringUnits failures:\n  " + "\n  ".join(failures)


@pytest.mark.requires_cu(CU.ENGINEERING_UNITS)
async def test_design_value_data_type_has_engineering_units(opcua_client, ns_indices):
    """Every DesignValueDataType in a joint design must carry EngineeringUnits with a valid UnitId."""
    ns_di = ns_indices.get(NS_DI)
    if ns_di is None:
        pytest.skip("DI namespace not registered on server")
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered on server")

    js = await find_joining_system(opcua_client)
    if js is None:
        pytest.skip("JoiningSystem not found — server may not be running")

    jm = await find_child_by_browse_name(js, "JointManagement", ns_ijt)
    if jm is None:
        pytest.skip("JointManagement not found — skipping design value EU check")

    list_node = await find_child_by_browse_name(jm, "GetJointDesignList", ns_ijt)
    if list_node is None:
        skip_accepted_policy(
            "optional joint-design data is unavailable; result-value engineering-unit coverage remains available",
            method="GetJointDesignList",
        )
    await assert_input_argument_names(
        list_node,
        JOINT_METHOD_INPUTS["GetJointDesignList"],
        method_name="GetJointDesignList",
    )

    piu = await read_tool_product_instance_uri(opcua_client, ns_ijt, ns_di, ns_indices.get(NS_APP))
    list_result = await call_method(
        jm,
        list_node,
        ua.Variant(piu or "", ua.VariantType.String),
        timeout=15.0,
        method_name="GetJointDesignList",
    )
    if not list_result.success:
        skip_accepted_policy(
            "optional joint-design data is unavailable; result-value engineering-unit coverage remains available",
            method="GetJointDesignList",
            status=str(list_result.error),
        )

    outputs = list_result.output_list
    design_list = outputs[0] if outputs and isinstance(outputs[0], (list, tuple)) else outputs

    if not design_list:
        skip_accepted_policy(
            "no joint designs are configured on the server; result-value engineering-unit coverage remains available",
            method="GetJointDesignList",
        )

    first_id = str(design_list[0] if isinstance(design_list, (list, tuple)) else design_list)
    get_node = await find_child_by_browse_name(jm, "GetJointDesign", ns_ijt)
    if get_node is None:
        skip_accepted_policy(
            "optional joint-design data is unavailable; result-value engineering-unit coverage remains available",
            method="GetJointDesign",
        )
    await assert_input_argument_names(
        get_node,
        JOINT_METHOD_INPUTS["GetJointDesign"],
        method_name="GetJointDesign",
    )

    get_result = await call_method(
        jm,
        get_node,
        ua.Variant(piu or "", ua.VariantType.String),
        ua.Variant(first_id, ua.VariantType.String),
        timeout=15.0,
        method_name="GetJointDesign",
    )
    if not get_result.success:
        skip_accepted_policy(
            "optional joint-design data is unavailable; result-value engineering-unit coverage remains available",
            method="GetJointDesign",
            status=str(get_result.error),
        )
    design_data = get_result.output_list[0] if get_result.output_list else None

    if design_data is None:
        skip_accepted_policy(
            "joint-design data was empty; result-value engineering-unit coverage remains available",
            method="GetJointDesign",
        )

    design_values: list = []
    for attr in ("DesignValues", "Values"):
        vals = getattr(design_data, attr, None)
        if isinstance(vals, (list, tuple)):
            design_values.extend(vals)

    if not design_values:
        skip_accepted_policy(
            "joint design has no DesignValueDataType entries; result-value engineering-unit coverage remains available",
            method="GetJointDesign",
        )

    failures: list[str] = []
    for idx, dv in enumerate(design_values):
        eu = getattr(dv, "EngineeringUnits", None)
        if eu is None:
            continue
        eu = getattr(eu, "Value", eu)  # unwrap nested Variant
        identifier = getattr(eu, "UnitId", None)
        if identifier is None:
            failures.append(f"DesignValue[{idx}].EngineeringUnits.UnitId is None")

    assert not failures, "DesignValue EngineeringUnits failures:\n  " + "\n  ".join(failures)


@pytest.mark.requires_cu(CU.ENGINEERING_UNITS)
@pytest.mark.negative
async def test_result_values_with_absent_eu_information_are_non_conformant(
    subscription_client, result_trigger, ns_indices
):
    """Any ResultValue with EngineeringUnits present must have non-None UnitId — null UnitId is non-conformant."""
    result_data = await _trigger_and_get_result(
        subscription_client, result_trigger, ns_indices, ResultType.MULTI_STEP_OK_RESULT
    )
    if result_data is None:
        pytest.skip("Could not retrieve multi-step result for negative EU conformance check")

    all_values = _collect_all_result_values(result_data)
    values_with_eu = _values_with_eu(all_values)

    if not values_with_eu:
        pytest.skip(
            "CU.ENGINEERING_UNITS declared but EU field absent in ResultValues — "
            "server declared CU.ENGINEERING_UNITS but no ResultValues carry an EngineeringUnits field; "
            "negative check not applicable"
        )

    violations: list[str] = []
    for idx, value in enumerate(values_with_eu):
        eu = value.EngineeringUnits
        eu = getattr(eu, "Value", eu)  # unwrap Variant → EUInformation
        identifier = getattr(eu, "UnitId", None)
        if identifier is None:
            violations.append(
                f"value[{idx}].EngineeringUnits.UnitId is None — "
                "EngineeringUnits present but UnitId field is null (non-conformant)"
            )

    assert not violations, (
        "ResultValues have EngineeringUnits with null UnitId (conformance violation):\n  " + "\n  ".join(violations)
    )
