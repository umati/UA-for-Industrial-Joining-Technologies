"""
Conformance Unit registry for OPC 40450-1 (IJT Base Companion Specification).

This module is the single source of truth for all conformance unit identifiers.
Keys are meaningful names derived from the spec section titles — never numbers.
Numbers appear in the spec document and can change between spec revisions;
names reflect what the capability actually is and are stable.

Usage::

    from helpers.cu_registry import CU

    @pytest.mark.requires_cu(CU.GET_LATEST_RESULT)
    async def test_get_latest_result_returns_result_data(...):
        ...

    # Multiple CUs required by one test:
    @pytest.mark.requires_cu(CU.SEND_JOINT, CU.GET_JOINT)
    async def test_send_and_retrieve_joint_round_trip(...):
        ...
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import FrozenSet


@dataclass(frozen=True)
class ConformanceUnitMeta:
    """Metadata describing a single conformance unit."""

    key: str
    display_name: str
    description: str
    facets: FrozenSet[str]
    spec_section: str = ""


class CU:
    """
    Named constants for every conformance unit in OPC 40450-1 IJT Base.

    Each constant is a stable string key matching the spec section title.
    Use these constants everywhere — in markers, profile YAML, and assertions.
    Never reference spec sequence numbers in code or comments.
    """

    # ── Joining System Structure ──────────────────────────────────────────────
    JOINING_SYSTEM_BASE = "joining_system_base"
    JOINING_SYSTEM_IDENTIFICATION = "joining_system_identification"
    JOINING_SYSTEM_MACHINERY_BUILDING_BLOCKS = "joining_system_machinery_building_blocks"

    # ── Asset and Result Management top-level ────────────────────────────────
    ASSET_MANAGEMENT = "asset_management"
    RESULT_MANAGEMENT = "result_management"

    # ── Result data structure ─────────────────────────────────────────────────
    SINGLE_RESULT = "single_result"
    BASIC_RESULT = "basic_result"
    RESULT_ADDITIONAL_DATA = "result_additional_data"
    RESULT_EXTENDED_META_DATA = "result_extended_meta_data"
    RESULT_PROCESSING_TIMES = "result_processing_times"
    RESULT_PROCESSING_TIMES_DURATIONS = "result_processing_times_durations"
    RESULT_EVENT_ACCESS = "result_event_access"

    # ── Result access methods ─────────────────────────────────────────────────
    GET_LATEST_RESULT = "get_latest_result"
    GET_RESULT_BY_ID = "get_result_by_id"
    GET_RESULT_WITH_FILTER_CRITERIA = "get_result_with_filter_criteria"
    RESULT_VARIABLE_ACCESS = "result_variable_access"

    # ── Result identifiers ────────────────────────────────────────────────────
    RESULT_INTERNAL_IDENTIFIERS = "result_internal_identifiers"
    RESULT_EXTERNAL_IDENTIFIERS = "result_external_identifiers"

    # ── Joining result payload ────────────────────────────────────────────────
    JOINING_RESULT_FAILURE_REASON = "joining_result_failure_reason"
    JOINING_RESULT_OVERALL_RESULT_VALUES = "joining_result_overall_result_values"
    JOINING_RESULT_STEP_RESULTS = "joining_result_step_results"
    JOINING_RESULT_ERRORS = "joining_result_errors"
    JOINING_RESULT_TRACE = "joining_result_trace"
    RESULT_VALUE_TRACE_POINT_TIME_OFFSET = "result_value_trace_point_time_offset"
    RESULT_VALUE_TRACE_POINT_INDEX = "result_value_trace_point_index"

    # ── Consolidated / combined results ──────────────────────────────────────
    SYNC_RESULT = "sync_result"
    SYNC_RESULT_COUNTERS = "sync_result_counters"
    BATCH_RESULT = "batch_result"
    BATCH_RESULT_COUNTERS = "batch_result_counters"
    INTERVENTION_RESULT = "intervention_result"
    JOB_RESULT = "job_result"
    RESULT_VALUE_FINAL_TAG = "result_value_final_tag"
    SELF_CONTAINED_CONSOLIDATED_RESULT = "self_contained_consolidated_result"
    CONSOLIDATED_RESULT_WITH_REFERENCES = "consolidated_result_with_references"
    PARTIAL_CONSOLIDATED_RESULT = "partial_consolidated_result"
    RESULT_CONTENT = "result_content"

    # ── Result request / acknowledge ──────────────────────────────────────────
    REQUEST_RESULTS = "request_results"
    REQUESTED_RESULT_VARIABLE_ACCESS = "requested_result_variable_access"
    REQUESTED_RESULT_EVENT_ACCESS = "requested_result_event_access"
    ACKNOWLEDGE_RESULTS = "acknowledge_results"
    REQUEST_UNACKNOWLEDGED_RESULTS = "request_unacknowledged_results"

    # ── Asset types ────────────────────────────────────────────────────────────
    ASSET_MANAGEMENT_CONTROLLER = "asset_management_controller"
    ASSET_MANAGEMENT_TOOL = "asset_management_tool"
    ASSET_MANAGEMENT_SERVO = "asset_management_servo"
    ASSET_MANAGEMENT_MEMORY_DEVICE = "asset_management_memory_device"
    ASSET_MANAGEMENT_CABLE = "asset_management_cable"
    ASSET_MANAGEMENT_POWER_SUPPLY = "asset_management_power_supply"
    ASSET_MANAGEMENT_FEEDER = "asset_management_feeder"
    ASSET_MANAGEMENT_BATTERY = "asset_management_battery"
    ASSET_MANAGEMENT_SENSOR = "asset_management_sensor"
    ASSET_MANAGEMENT_ACCESSORY = "asset_management_accessory"
    ASSET_MANAGEMENT_SOFTWARE = "asset_management_software"
    ASSET_MANAGEMENT_SUB_COMPONENT = "asset_management_sub_component"
    ASSET_MANAGEMENT_VIRTUAL_STATION = "asset_management_virtual_station"
    ASSET_MANAGEMENT_OPERATION_COUNTERS = "asset_management_operation_counters"
    ASSET_MANAGEMENT_TOOL_OPERATION_CYCLE_COUNTER = "asset_management_tool_operation_cycle_counter"
    ASSET_MANAGEMENT_BATTERY_OPERATION_CYCLE_COUNTER = "asset_management_battery_operation_cycle_counter"
    ASSET_MANAGEMENT_HEALTH = "asset_management_health"
    ASSET_MANAGEMENT_MONITORING_HEALTH = "asset_management_monitoring_health"
    ASSET_MANAGEMENT_SERVICE = "asset_management_service"
    ASSET_MANAGEMENT_CALIBRATION = "asset_management_calibration"
    ASSET_MANAGEMENT_ADDITIONAL_INFORMATION = "asset_management_additional_information"
    ASSET_MANAGEMENT_MACHINERY_BUILDING_BLOCKS = "asset_management_machinery_building_blocks"
    # JoiningDataVariable internal structure — PhysicalQuantity reachable via HasComponent,
    # EnumStrings accessible, and per-asset parameter EU values correct.
    # ── Asset operations / methods ────────────────────────────────────────────
    METHOD_INPUT_ARGUMENT = "method_input_argument"
    DISCONNECT_ASSET = "disconnect_asset"
    ENABLE_TOOL = "enable_tool"
    SET_CALIBRATION = "set_calibration"
    REBOOT_ASSET = "reboot_asset"
    FEEDBACK_METHODS = "feedback_methods"
    SET_TIME = "set_time"
    SET_OFFLINE_TIMER = "set_offline_timer"
    IO_SIGNALS_METHODS = "io_signals_methods"
    GET_ERROR_INFORMATION = "get_error_information"
    EXECUTE_OPERATION = "execute_operation"

    # ── Identifiers ────────────────────────────────────────────────────────────
    SEND_IDENTIFIERS = "send_identifiers"
    GET_IDENTIFIERS = "get_identifiers"
    RESET_IDENTIFIERS = "reset_identifiers"

    # ── Events and conditions ─────────────────────────────────────────────────
    EVENT_PAYLOAD = "event_payload"
    EVENT_CONDITION_CLASSES = "event_condition_classes"
    ASSET_CONNECTION_EVENT = "asset_connection_event"
    ASSET_CONNECTION_STATE_EVENT = "asset_connection_state_event"
    ASSET_ENABLE_STATE_EVENT = "asset_enable_state_event"
    EVENT_PAYLOAD_ASSOCIATED_ENTITIES = "event_payload_associated_entities"
    EVENT_PAYLOAD_REPORTED_VALUES = "event_payload_reported_values"
    IDENTIFIERS_EVENT = "identifiers_event"
    SELECT_PROCESS_EVENT = "select_process_event"

    # ── Joining process management ────────────────────────────────────────────
    JOINING_PROCESS_MANAGEMENT = "joining_process_management"
    GET_JOINING_PROCESS_LIST = "get_joining_process_list"
    ABORT_JOINING_PROCESS = "abort_joining_process"
    START_SELECTED_JOINING = "start_selected_joining"
    SELECT_JOINING_PROCESS = "select_joining_process"
    DESELECT_JOINING_PROCESS = "deselect_joining_process"
    RESET_JOINING_PROCESS = "reset_joining_process"
    INCREMENT_JOINING_PROCESS_COUNTER = "increment_joining_process_counter"
    DECREMENT_JOINING_PROCESS_COUNTER = "decrement_joining_process_counter"
    SET_JOINING_PROCESS_SIZE = "set_joining_process_size"
    START_JOINING_PROCESS = "start_joining_process"
    DELETE_JOINING_PROCESS = "delete_joining_process"
    GET_SELECTED_JOINING_PROGRAM = "get_selected_joining_program"
    SEND_JOINING_PROCESS = "send_joining_process"
    GET_JOINING_PROCESS = "get_joining_process"
    SET_JOINING_PROCESS_COUNTER = "set_joining_process_counter"
    SET_JOINING_PROCESS_MAPPING = "set_joining_process_mapping"
    GET_JOINING_PROCESS_REVISION_LIST = "get_joining_process_revision_list"

    # ── Joint management ──────────────────────────────────────────────────────
    JOINT_MANAGEMENT = "joint_management"
    SEND_JOINT = "send_joint"
    GET_JOINT_LIST = "get_joint_list"
    SELECT_JOINT = "select_joint"
    GET_JOINT = "get_joint"
    JOINT_DATA = "joint_data"
    DELETE_JOINT = "delete_joint"
    SEND_JOINT_DESIGN = "send_joint_design"
    GET_JOINT_DESIGN_LIST = "get_joint_design_list"
    GET_JOINT_DESIGN = "get_joint_design"
    JOINT_DESIGN_DATA = "joint_design_data"
    DELETE_JOINT_DESIGN = "delete_joint_design"
    SEND_JOINT_COMPONENT = "send_joint_component"
    GET_JOINT_COMPONENT_LIST = "get_joint_component_list"
    GET_JOINT_COMPONENT = "get_joint_component"
    JOINT_COMPONENT_DATA = "joint_component_data"
    DELETE_JOINT_COMPONENT = "delete_joint_component"
    GET_JOINT_REVISION_LIST = "get_joint_revision_list"

    # ── Measurement quality ───────────────────────────────────────────────────
    ENGINEERING_UNITS = "engineering_units"

    # ── Convenience collections ───────────────────────────────────────────────

    ALL_JOINING_SYSTEM_STRUCTURE: tuple[str, ...] = (
        JOINING_SYSTEM_BASE,
        JOINING_SYSTEM_IDENTIFICATION,
        JOINING_SYSTEM_MACHINERY_BUILDING_BLOCKS,
    )

    ALL_RESULT_DATA_STRUCTURE: tuple[str, ...] = (
        SINGLE_RESULT,
        BASIC_RESULT,
        RESULT_ADDITIONAL_DATA,
        RESULT_EXTENDED_META_DATA,
        RESULT_PROCESSING_TIMES,
        RESULT_PROCESSING_TIMES_DURATIONS,
    )

    ALL_RESULT_ACCESS_METHODS: tuple[str, ...] = (
        GET_LATEST_RESULT,
        GET_RESULT_BY_ID,
        GET_RESULT_WITH_FILTER_CRITERIA,
        RESULT_VARIABLE_ACCESS,
        REQUEST_RESULTS,
        REQUESTED_RESULT_VARIABLE_ACCESS,
        REQUESTED_RESULT_EVENT_ACCESS,
        ACKNOWLEDGE_RESULTS,
        REQUEST_UNACKNOWLEDGED_RESULTS,
    )

    ALL_JOINING_RESULT_PAYLOAD: tuple[str, ...] = (
        JOINING_RESULT_FAILURE_REASON,
        JOINING_RESULT_OVERALL_RESULT_VALUES,
        JOINING_RESULT_STEP_RESULTS,
        JOINING_RESULT_ERRORS,
        JOINING_RESULT_TRACE,
        RESULT_VALUE_TRACE_POINT_TIME_OFFSET,
        RESULT_VALUE_TRACE_POINT_INDEX,
    )

    ALL_CONSOLIDATED_RESULT_TYPES: tuple[str, ...] = (
        SYNC_RESULT,
        SYNC_RESULT_COUNTERS,
        BATCH_RESULT,
        BATCH_RESULT_COUNTERS,
        INTERVENTION_RESULT,
        JOB_RESULT,
        RESULT_VALUE_FINAL_TAG,
        SELF_CONTAINED_CONSOLIDATED_RESULT,
        CONSOLIDATED_RESULT_WITH_REFERENCES,
        PARTIAL_CONSOLIDATED_RESULT,
        RESULT_CONTENT,
    )

    ALL_ASSET_TYPES: tuple[str, ...] = (
        ASSET_MANAGEMENT_CONTROLLER,
        ASSET_MANAGEMENT_TOOL,
        ASSET_MANAGEMENT_SERVO,
        ASSET_MANAGEMENT_MEMORY_DEVICE,
        ASSET_MANAGEMENT_CABLE,
        ASSET_MANAGEMENT_POWER_SUPPLY,
        ASSET_MANAGEMENT_FEEDER,
        ASSET_MANAGEMENT_BATTERY,
        ASSET_MANAGEMENT_SENSOR,
        ASSET_MANAGEMENT_ACCESSORY,
        ASSET_MANAGEMENT_SOFTWARE,
        ASSET_MANAGEMENT_SUB_COMPONENT,
        ASSET_MANAGEMENT_VIRTUAL_STATION,
    )

    ALL_ASSET_SUPPLEMENTARY: tuple[str, ...] = (
        ASSET_MANAGEMENT_OPERATION_COUNTERS,
        ASSET_MANAGEMENT_TOOL_OPERATION_CYCLE_COUNTER,
        ASSET_MANAGEMENT_BATTERY_OPERATION_CYCLE_COUNTER,
        ASSET_MANAGEMENT_HEALTH,
        ASSET_MANAGEMENT_MONITORING_HEALTH,
        ASSET_MANAGEMENT_SERVICE,
        ASSET_MANAGEMENT_CALIBRATION,
        ASSET_MANAGEMENT_ADDITIONAL_INFORMATION,
        ASSET_MANAGEMENT_MACHINERY_BUILDING_BLOCKS,
    )

    ALL_ASSET_OPERATION_METHODS: tuple[str, ...] = (
        METHOD_INPUT_ARGUMENT,
        DISCONNECT_ASSET,
        ENABLE_TOOL,
        SET_CALIBRATION,
        REBOOT_ASSET,
        FEEDBACK_METHODS,
        SET_TIME,
        SET_OFFLINE_TIMER,
        IO_SIGNALS_METHODS,
        GET_ERROR_INFORMATION,
        EXECUTE_OPERATION,
    )

    ALL_IDENTIFIER_METHODS: tuple[str, ...] = (
        SEND_IDENTIFIERS,
        GET_IDENTIFIERS,
        RESET_IDENTIFIERS,
    )

    ALL_EVENT_TYPES: tuple[str, ...] = (
        EVENT_PAYLOAD,
        EVENT_CONDITION_CLASSES,
        ASSET_CONNECTION_EVENT,
        ASSET_CONNECTION_STATE_EVENT,
        ASSET_ENABLE_STATE_EVENT,
        EVENT_PAYLOAD_ASSOCIATED_ENTITIES,
        EVENT_PAYLOAD_REPORTED_VALUES,
        IDENTIFIERS_EVENT,
        SELECT_PROCESS_EVENT,
    )

    ALL_JOINING_PROCESS_MANAGEMENT: tuple[str, ...] = (
        JOINING_PROCESS_MANAGEMENT,
        GET_JOINING_PROCESS_LIST,
        ABORT_JOINING_PROCESS,
        START_SELECTED_JOINING,
        SELECT_JOINING_PROCESS,
        DESELECT_JOINING_PROCESS,
        RESET_JOINING_PROCESS,
        INCREMENT_JOINING_PROCESS_COUNTER,
        DECREMENT_JOINING_PROCESS_COUNTER,
        SET_JOINING_PROCESS_SIZE,
        START_JOINING_PROCESS,
        DELETE_JOINING_PROCESS,
        GET_SELECTED_JOINING_PROGRAM,
        SEND_JOINING_PROCESS,
        GET_JOINING_PROCESS,
        SET_JOINING_PROCESS_COUNTER,
        SET_JOINING_PROCESS_MAPPING,
        GET_JOINING_PROCESS_REVISION_LIST,
    )

    ALL_JOINT_MANAGEMENT: tuple[str, ...] = (
        JOINT_MANAGEMENT,
        SEND_JOINT,
        GET_JOINT_LIST,
        SELECT_JOINT,
        GET_JOINT,
        JOINT_DATA,
        DELETE_JOINT,
        SEND_JOINT_DESIGN,
        GET_JOINT_DESIGN_LIST,
        GET_JOINT_DESIGN,
        JOINT_DESIGN_DATA,
        DELETE_JOINT_DESIGN,
        SEND_JOINT_COMPONENT,
        GET_JOINT_COMPONENT_LIST,
        GET_JOINT_COMPONENT,
        JOINT_COMPONENT_DATA,
        DELETE_JOINT_COMPONENT,
        GET_JOINT_REVISION_LIST,
    )


_CU_METHOD_NAMES: dict[str, tuple[str, ...]] = {
    CU.GET_LATEST_RESULT: ("GetLatestResult",),
    CU.GET_RESULT_BY_ID: ("GetResultById",),
    CU.GET_RESULT_WITH_FILTER_CRITERIA: ("GetResultIdListFiltered",),
    CU.REQUEST_RESULTS: ("RequestResults",),
    CU.ACKNOWLEDGE_RESULTS: ("AcknowledgeResults",),
    CU.REQUEST_UNACKNOWLEDGED_RESULTS: ("RequestUnacknowledgedResults",),
    CU.DISCONNECT_ASSET: ("DisconnectAsset",),
    CU.ENABLE_TOOL: ("EnableAsset",),
    CU.SET_CALIBRATION: ("SetCalibration",),
    CU.REBOOT_ASSET: ("RebootAsset",),
    CU.FEEDBACK_METHODS: ("GetFeedbackFileList", "SendFeedback"),
    CU.SET_TIME: ("SetTime",),
    CU.SET_OFFLINE_TIMER: ("SetOfflineTimer",),
    CU.IO_SIGNALS_METHODS: ("GetIOSignals", "SetIOSignals"),
    CU.GET_ERROR_INFORMATION: ("GetErrorInformation",),
    CU.EXECUTE_OPERATION: ("ExecuteOperation",),
    CU.SEND_IDENTIFIERS: ("SendIdentifiers", "SendTextIdentifiers"),
    CU.GET_IDENTIFIERS: ("GetIdentifiers",),
    CU.RESET_IDENTIFIERS: ("ResetIdentifiers",),
    CU.GET_JOINING_PROCESS_LIST: ("GetJoiningProcessList",),
    CU.ABORT_JOINING_PROCESS: ("AbortJoiningProcess",),
    CU.START_SELECTED_JOINING: ("StartSelectedJoining",),
    CU.SELECT_JOINING_PROCESS: ("SelectJoiningProcess",),
    CU.DESELECT_JOINING_PROCESS: ("DeselectJoiningProcess",),
    CU.RESET_JOINING_PROCESS: ("ResetJoiningProcess",),
    CU.INCREMENT_JOINING_PROCESS_COUNTER: ("IncrementJoiningProcessCounter",),
    CU.DECREMENT_JOINING_PROCESS_COUNTER: ("DecrementJoiningProcessCounter",),
    CU.SET_JOINING_PROCESS_SIZE: ("SetJoiningProcessSize",),
    CU.START_JOINING_PROCESS: ("StartJoiningProcess",),
    CU.DELETE_JOINING_PROCESS: ("DeleteJoiningProcess",),
    CU.GET_SELECTED_JOINING_PROGRAM: ("GetSelectedJoiningProgram",),
    CU.SEND_JOINING_PROCESS: ("SendJoiningProcess",),
    CU.GET_JOINING_PROCESS: ("GetJoiningProcess",),
    CU.SET_JOINING_PROCESS_COUNTER: ("SetJoiningProcessCounter",),
    CU.SET_JOINING_PROCESS_MAPPING: ("SetJoiningProcessMapping",),
    CU.GET_JOINING_PROCESS_REVISION_LIST: ("GetJoiningProcessRevisionList",),
    CU.SEND_JOINT: ("SendJoint",),
    CU.GET_JOINT_LIST: ("GetJointList",),
    CU.SELECT_JOINT: ("SelectJoint",),
    CU.GET_JOINT: ("GetJoint",),
    CU.DELETE_JOINT: ("DeleteJoint",),
    CU.SEND_JOINT_DESIGN: ("SendJointDesign",),
    CU.GET_JOINT_DESIGN_LIST: ("GetJointDesignList",),
    CU.GET_JOINT_DESIGN: ("GetJointDesign",),
    CU.DELETE_JOINT_DESIGN: ("DeleteJointDesign",),
    CU.SEND_JOINT_COMPONENT: ("SendJointComponent",),
    CU.GET_JOINT_COMPONENT_LIST: ("GetJointComponentList",),
    CU.GET_JOINT_COMPONENT: ("GetJointComponent",),
    CU.DELETE_JOINT_COMPONENT: ("DeleteJointComponent",),
    CU.GET_JOINT_REVISION_LIST: ("GetJointRevisionList",),
}

_METHOD_TO_CU: dict[str, str] = {method: cu_key for cu_key, methods in _CU_METHOD_NAMES.items() for method in methods}

_ACRONYMS = {
    "id": "ID",
    "io": "IO",
}


def _title_from_key(cu_key: str) -> str:
    words = []
    for token in cu_key.split("_"):
        words.append(_ACRONYMS.get(token, token.capitalize()))
    return " ".join(words)


def cu_display_name(cu_key: str) -> str:
    """Return the public report label for a CU key."""
    return f"IJT {_title_from_key(cu_key)}"


def cu_method_names(cu_key: str) -> tuple[str, ...]:
    """Return OPC UA method BrowseNames associated with a CU, if any."""
    return _CU_METHOD_NAMES.get(cu_key, ())


def cu_key_for_method(method_name: str) -> str | None:
    """Return the CU key associated with an OPC UA method BrowseName."""
    return _METHOD_TO_CU.get(method_name)


def format_cu_not_supported(cu_key: str) -> str:
    """Return a compact report label for unsupported CU skips."""
    methods = cu_method_names(cu_key)
    if not methods:
        return f"{cu_display_name(cu_key)} NOT SUPPORTED"
    method_label = "Method" if len(methods) == 1 else "Methods"
    return f"{cu_display_name(cu_key)} - {method_label}: {', '.join(methods)} NOT SUPPORTED"


def format_method_not_supported(method_name: str) -> str:
    """Return the matching unsupported-CU label for an OPC UA method BrowseName."""
    cu_key = _METHOD_TO_CU.get(method_name)
    if cu_key:
        return format_cu_not_supported(cu_key)
    display = re.sub(r"(?<!^)(?=[A-Z])", " ", method_name).replace("_", " ")
    return f"IJT {display} - Method: {method_name} NOT SUPPORTED"
