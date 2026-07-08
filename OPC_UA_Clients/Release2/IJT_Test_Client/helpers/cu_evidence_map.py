"""
CU evidence metadata for target server execution.

Maps each conformance unit (CU) key to the evidence kind and execution flags
needed to validate it against a real target server or simulator.  This is execution
metadata only — the official CU registry and profile/facet definitions are
unchanged.

Evidence kinds (stable vocabulary):

  structure           Browse/read address-space structure; no server-state changes.
  method              Call an OPC UA method; may change server state.
  result              Requires a live tightening result (event or variable).
  consolidated_result Requires batch, sync, or job result evidence.
  event               Requires a live OPC UA event emission.
  condition           Requires retained condition validation.
  workflow            Requires full joining workflow orchestration.
  optional_operation  Optional server operation; gated by CU profile support.
  negative_path       Tests invalid or rejected operations.
  manual              Evidence that normally requires physical operator/tool action.

Usage::

    from helpers.cu_evidence_map import cu_evidence_meta, cus_by_evidence_kind

    meta = cu_evidence_meta(CU.START_SELECTED_JOINING)
    if meta and meta.state_changing:
        # check that the target server profile opts in before calling
        ...

    result_cus = cus_by_evidence_kind("result")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import FrozenSet

from helpers.cu_registry import CU

# ---------------------------------------------------------------------------
# Evidence metadata dataclass
# ---------------------------------------------------------------------------

_VALID_EVIDENCE_KINDS: frozenset[str] = frozenset(
    {
        "structure",
        "method",
        "result",
        "consolidated_result",
        "event",
        "condition",
        "workflow",
        "optional_operation",
        "negative_path",
        "manual",
    }
)


@dataclass(frozen=True)
class CuEvidenceMeta:
    """Execution metadata describing how a conformance unit should be validated.

    Attributes:
        cu_key:         The stable CU registry key (e.g. ``CU.START_SELECTED_JOINING``).
        evidence_kind:  The evidence type required (see module docstring).
        state_changing: True when validation requires OPC UA calls that may change
                        target server state (e.g. selecting/starting a joining process).
                        State-changing CUs require explicit opt-in via target server YAML.
        manual_only:    True when the evidence normally requires physical operator
                        or tool action and cannot be automated via OPC UA.
        notes:          Optional human-readable note for documentation/runner output.
    """

    cu_key: str
    evidence_kind: str
    state_changing: bool = False
    manual_only: bool = False
    notes: str = field(default="")

    def __post_init__(self) -> None:
        if self.evidence_kind not in _VALID_EVIDENCE_KINDS:
            raise ValueError(
                f"Invalid evidence_kind '{self.evidence_kind}' for CU '{self.cu_key}'. "
                f"Valid kinds: {sorted(_VALID_EVIDENCE_KINDS)}"
            )


# ---------------------------------------------------------------------------
# Evidence metadata table
# ---------------------------------------------------------------------------
#
# Every CU in the registry should have an entry here.  Unknown CU keys default
# to CuEvidenceMeta(cu_key=key, evidence_kind="structure") at lookup time so
# that newly added CUs are handled gracefully without crashing the runner.

_CU_EVIDENCE: list[CuEvidenceMeta] = [
    # ── Joining System Structure ─────────────────────────────────────────────
    CuEvidenceMeta(CU.JOINING_SYSTEM_BASE, "structure"),
    CuEvidenceMeta(CU.JOINING_SYSTEM_IDENTIFICATION, "structure"),
    CuEvidenceMeta(CU.JOINING_SYSTEM_MACHINERY_BUILDING_BLOCKS, "structure"),
    # ── Asset and Result Management top-level ────────────────────────────────
    CuEvidenceMeta(CU.ASSET_MANAGEMENT, "structure"),
    CuEvidenceMeta(CU.RESULT_MANAGEMENT, "structure"),
    # ── Result data structure ─────────────────────────────────────────────────
    CuEvidenceMeta(CU.SINGLE_RESULT, "result"),
    CuEvidenceMeta(CU.BASIC_RESULT, "result"),
    CuEvidenceMeta(CU.RESULT_ADDITIONAL_DATA, "result"),
    CuEvidenceMeta(CU.RESULT_EXTENDED_META_DATA, "result"),
    CuEvidenceMeta(CU.RESULT_PROCESSING_TIMES, "result"),
    CuEvidenceMeta(CU.RESULT_PROCESSING_TIMES_DURATIONS, "result"),
    CuEvidenceMeta(CU.RESULT_EVENT_ACCESS, "event"),
    # ── Result access methods ─────────────────────────────────────────────────
    CuEvidenceMeta(CU.GET_LATEST_RESULT, "method"),
    CuEvidenceMeta(CU.GET_RESULT_BY_ID, "method"),
    CuEvidenceMeta(CU.GET_RESULT_WITH_FILTER_CRITERIA, "method"),
    CuEvidenceMeta(CU.RESULT_VARIABLE_ACCESS, "result"),
    CuEvidenceMeta(CU.REQUEST_RESULTS, "method"),
    CuEvidenceMeta(CU.REQUESTED_RESULT_VARIABLE_ACCESS, "method"),
    CuEvidenceMeta(CU.REQUESTED_RESULT_EVENT_ACCESS, "event"),
    CuEvidenceMeta(CU.ACKNOWLEDGE_RESULTS, "method", state_changing=True),
    CuEvidenceMeta(CU.REQUEST_UNACKNOWLEDGED_RESULTS, "method"),
    # ── Result identifiers ────────────────────────────────────────────────────
    CuEvidenceMeta(CU.RESULT_INTERNAL_IDENTIFIERS, "result"),
    CuEvidenceMeta(CU.RESULT_EXTERNAL_IDENTIFIERS, "result"),
    # ── Joining result payload ────────────────────────────────────────────────
    CuEvidenceMeta(CU.JOINING_RESULT_FAILURE_REASON, "result"),
    CuEvidenceMeta(CU.JOINING_RESULT_OVERALL_RESULT_VALUES, "result"),
    CuEvidenceMeta(CU.JOINING_RESULT_STEP_RESULTS, "result"),
    CuEvidenceMeta(CU.JOINING_RESULT_ERRORS, "result"),
    CuEvidenceMeta(CU.JOINING_RESULT_TRACE, "result"),
    CuEvidenceMeta(CU.RESULT_VALUE_TRACE_POINT_TIME_OFFSET, "result"),
    CuEvidenceMeta(CU.RESULT_VALUE_TRACE_POINT_INDEX, "result"),
    # ── Consolidated / combined results ──────────────────────────────────────
    CuEvidenceMeta(CU.SYNC_RESULT, "consolidated_result"),
    CuEvidenceMeta(CU.SYNC_RESULT_COUNTERS, "consolidated_result"),
    CuEvidenceMeta(CU.BATCH_RESULT, "consolidated_result"),
    CuEvidenceMeta(CU.BATCH_RESULT_COUNTERS, "consolidated_result"),
    CuEvidenceMeta(CU.INTERVENTION_RESULT, "consolidated_result"),
    CuEvidenceMeta(CU.JOB_RESULT, "consolidated_result"),
    CuEvidenceMeta(CU.RESULT_VALUE_FINAL_TAG, "consolidated_result"),
    CuEvidenceMeta(CU.SELF_CONTAINED_CONSOLIDATED_RESULT, "consolidated_result"),
    CuEvidenceMeta(CU.CONSOLIDATED_RESULT_WITH_REFERENCES, "consolidated_result"),
    CuEvidenceMeta(CU.PARTIAL_CONSOLIDATED_RESULT, "consolidated_result"),
    CuEvidenceMeta(CU.RESULT_CONTENT, "result"),
    # ── Asset types ────────────────────────────────────────────────────────────
    CuEvidenceMeta(CU.ASSET_MANAGEMENT_CONTROLLER, "structure"),
    CuEvidenceMeta(CU.ASSET_MANAGEMENT_TOOL, "structure"),
    CuEvidenceMeta(CU.ASSET_MANAGEMENT_SERVO, "structure"),
    CuEvidenceMeta(CU.ASSET_MANAGEMENT_MEMORY_DEVICE, "structure"),
    CuEvidenceMeta(CU.ASSET_MANAGEMENT_CABLE, "structure"),
    CuEvidenceMeta(CU.ASSET_MANAGEMENT_POWER_SUPPLY, "structure"),
    CuEvidenceMeta(CU.ASSET_MANAGEMENT_FEEDER, "structure"),
    CuEvidenceMeta(CU.ASSET_MANAGEMENT_BATTERY, "structure"),
    CuEvidenceMeta(CU.ASSET_MANAGEMENT_SENSOR, "structure"),
    CuEvidenceMeta(CU.ASSET_MANAGEMENT_ACCESSORY, "structure"),
    CuEvidenceMeta(CU.ASSET_MANAGEMENT_SOFTWARE, "structure"),
    CuEvidenceMeta(CU.ASSET_MANAGEMENT_SUB_COMPONENT, "structure"),
    CuEvidenceMeta(CU.ASSET_MANAGEMENT_VIRTUAL_STATION, "structure"),
    CuEvidenceMeta(CU.ASSET_MANAGEMENT_OPERATION_COUNTERS, "structure"),
    CuEvidenceMeta(CU.ASSET_MANAGEMENT_TOOL_OPERATION_CYCLE_COUNTER, "structure"),
    CuEvidenceMeta(CU.ASSET_MANAGEMENT_BATTERY_OPERATION_CYCLE_COUNTER, "structure"),
    CuEvidenceMeta(CU.ASSET_MANAGEMENT_HEALTH, "structure"),
    CuEvidenceMeta(CU.ASSET_MANAGEMENT_MONITORING_HEALTH, "structure"),
    CuEvidenceMeta(CU.ASSET_MANAGEMENT_SERVICE, "structure"),
    CuEvidenceMeta(CU.ASSET_MANAGEMENT_CALIBRATION, "structure"),
    CuEvidenceMeta(CU.ASSET_MANAGEMENT_ADDITIONAL_INFORMATION, "structure"),
    CuEvidenceMeta(CU.ASSET_MANAGEMENT_MACHINERY_BUILDING_BLOCKS, "structure"),
    # ── Asset operations / methods ────────────────────────────────────────────
    CuEvidenceMeta(CU.METHOD_INPUT_ARGUMENT, "method"),
    CuEvidenceMeta(
        CU.DISCONNECT_ASSET,
        "optional_operation",
        state_changing=True,
        notes="Disconnects a physical asset; target-server-damaging if misused",
    ),
    CuEvidenceMeta(CU.ENABLE_TOOL, "optional_operation", state_changing=True),
    CuEvidenceMeta(CU.SET_CALIBRATION, "optional_operation", state_changing=True),
    CuEvidenceMeta(
        CU.REBOOT_ASSET,
        "optional_operation",
        state_changing=True,
        notes="Reboots a physical asset; requires explicit opt-in",
    ),
    CuEvidenceMeta(CU.FEEDBACK_METHODS, "optional_operation"),
    CuEvidenceMeta(CU.SET_TIME, "optional_operation", state_changing=True),
    CuEvidenceMeta(CU.SET_OFFLINE_TIMER, "optional_operation", state_changing=True),
    CuEvidenceMeta(CU.IO_SIGNALS_METHODS, "optional_operation"),
    CuEvidenceMeta(CU.GET_ERROR_INFORMATION, "method"),
    CuEvidenceMeta(CU.EXECUTE_OPERATION, "optional_operation", state_changing=True),
    # ── Identifiers ────────────────────────────────────────────────────────────
    CuEvidenceMeta(CU.SEND_IDENTIFIERS, "method", state_changing=True),
    CuEvidenceMeta(CU.GET_IDENTIFIERS, "method"),
    CuEvidenceMeta(CU.RESET_IDENTIFIERS, "method", state_changing=True),
    # ── Events and conditions ─────────────────────────────────────────────────
    CuEvidenceMeta(CU.EVENT_PAYLOAD, "event"),
    CuEvidenceMeta(CU.EVENT_CONDITION_CLASSES, "condition"),
    CuEvidenceMeta(CU.ASSET_CONNECTION_EVENT, "manual", manual_only=True),
    CuEvidenceMeta(CU.ASSET_CONNECTION_STATE_EVENT, "manual", manual_only=True),
    CuEvidenceMeta(CU.ASSET_ENABLE_STATE_EVENT, "manual", manual_only=True),
    CuEvidenceMeta(CU.EVENT_PAYLOAD_ASSOCIATED_ENTITIES, "event"),
    CuEvidenceMeta(CU.EVENT_PAYLOAD_REPORTED_VALUES, "event"),
    CuEvidenceMeta(CU.IDENTIFIERS_EVENT, "event"),
    CuEvidenceMeta(CU.SELECT_PROCESS_EVENT, "event"),
    # ── Joining process management ────────────────────────────────────────────
    CuEvidenceMeta(CU.JOINING_PROCESS_MANAGEMENT, "structure"),
    CuEvidenceMeta(CU.GET_JOINING_PROCESS_LIST, "method"),
    CuEvidenceMeta(CU.ABORT_JOINING_PROCESS, "method", state_changing=True),
    CuEvidenceMeta(CU.START_SELECTED_JOINING, "workflow", state_changing=True),
    CuEvidenceMeta(CU.SELECT_JOINING_PROCESS, "method", state_changing=True),
    CuEvidenceMeta(CU.DESELECT_JOINING_PROCESS, "method", state_changing=True),
    CuEvidenceMeta(CU.RESET_JOINING_PROCESS, "method", state_changing=True),
    CuEvidenceMeta(CU.INCREMENT_JOINING_PROCESS_COUNTER, "method", state_changing=True),
    CuEvidenceMeta(CU.DECREMENT_JOINING_PROCESS_COUNTER, "method", state_changing=True),
    CuEvidenceMeta(CU.SET_JOINING_PROCESS_SIZE, "method", state_changing=True),
    CuEvidenceMeta(CU.START_JOINING_PROCESS, "workflow", state_changing=True),
    CuEvidenceMeta(
        CU.DELETE_JOINING_PROCESS,
        "negative_path",
        state_changing=True,
        notes="Destructive; requires explicit opt-in per YAML allowed_methods",
    ),
    CuEvidenceMeta(CU.GET_SELECTED_JOINING_PROGRAM, "method"),
    CuEvidenceMeta(CU.SEND_JOINING_PROCESS, "optional_operation", state_changing=True),
    CuEvidenceMeta(CU.GET_JOINING_PROCESS, "method"),
    CuEvidenceMeta(CU.SET_JOINING_PROCESS_COUNTER, "method", state_changing=True),
    CuEvidenceMeta(CU.SET_JOINING_PROCESS_MAPPING, "optional_operation", state_changing=True),
    CuEvidenceMeta(CU.GET_JOINING_PROCESS_REVISION_LIST, "method"),
    # ── Joint management ──────────────────────────────────────────────────────
    CuEvidenceMeta(CU.JOINT_MANAGEMENT, "structure"),
    CuEvidenceMeta(CU.SEND_JOINT, "optional_operation", state_changing=True),
    CuEvidenceMeta(CU.GET_JOINT_LIST, "method"),
    CuEvidenceMeta(CU.SELECT_JOINT, "method", state_changing=True),
    CuEvidenceMeta(CU.GET_JOINT, "method"),
    CuEvidenceMeta(CU.JOINT_DATA, "structure"),
    CuEvidenceMeta(
        CU.DELETE_JOINT,
        "negative_path",
        state_changing=True,
        notes="Destructive; requires explicit opt-in per YAML allowed_methods",
    ),
    CuEvidenceMeta(CU.SEND_JOINT_DESIGN, "optional_operation", state_changing=True),
    CuEvidenceMeta(CU.GET_JOINT_DESIGN_LIST, "method"),
    CuEvidenceMeta(CU.GET_JOINT_DESIGN, "method"),
    CuEvidenceMeta(CU.JOINT_DESIGN_DATA, "structure"),
    CuEvidenceMeta(
        CU.DELETE_JOINT_DESIGN,
        "negative_path",
        state_changing=True,
        notes="Destructive; requires explicit opt-in per YAML allowed_methods",
    ),
    CuEvidenceMeta(CU.SEND_JOINT_COMPONENT, "optional_operation", state_changing=True),
    CuEvidenceMeta(CU.GET_JOINT_COMPONENT_LIST, "method"),
    CuEvidenceMeta(CU.GET_JOINT_COMPONENT, "method"),
    CuEvidenceMeta(CU.JOINT_COMPONENT_DATA, "structure"),
    CuEvidenceMeta(
        CU.DELETE_JOINT_COMPONENT,
        "negative_path",
        state_changing=True,
        notes="Destructive; requires explicit opt-in per YAML allowed_methods",
    ),
    CuEvidenceMeta(CU.GET_JOINT_REVISION_LIST, "method"),
    # ── Measurement quality ───────────────────────────────────────────────────
    CuEvidenceMeta(CU.ENGINEERING_UNITS, "structure"),
]

# Build fast lookup dictionaries once at module load time.
_BY_KEY: dict[str, CuEvidenceMeta] = {m.cu_key: m for m in _CU_EVIDENCE}
_BY_KIND: dict[str, frozenset[str]] = {}
for _m in _CU_EVIDENCE:
    _BY_KIND.setdefault(_m.evidence_kind, set()).add(_m.cu_key)  # type: ignore[arg-type]
_BY_KIND = {k: frozenset(v) for k, v in _BY_KIND.items()}  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def cu_evidence_meta(cu_key: str) -> CuEvidenceMeta:
    """Return execution metadata for *cu_key*.

    Returns the registered entry when present.  Falls back to a safe
    default (evidence_kind="structure", state_changing=False) for CU keys
    added to the registry after this module was last updated, so unknown
    keys do not crash the runner.
    """
    return _BY_KEY.get(cu_key, CuEvidenceMeta(cu_key=cu_key, evidence_kind="structure"))


def cus_by_evidence_kind(kind: str) -> FrozenSet[str]:
    """Return all CU keys mapped to the given evidence *kind*.

    Returns an empty frozenset for unknown or unmapped kinds.
    """
    return _BY_KIND.get(kind, frozenset())


def is_state_changing(cu_key: str) -> bool:
    """Return True if the CU requires state-changing OPC UA calls."""
    return _BY_KEY.get(cu_key, CuEvidenceMeta(cu_key=cu_key, evidence_kind="structure")).state_changing


def is_manual_only(cu_key: str) -> bool:
    """Return True if the CU normally requires physical operator/tool action."""
    return _BY_KEY.get(cu_key, CuEvidenceMeta(cu_key=cu_key, evidence_kind="structure")).manual_only


def all_registered_cu_keys() -> FrozenSet[str]:
    """Return the set of all CU keys that have explicit evidence registrations."""
    return frozenset(_BY_KEY.keys())


def valid_evidence_kinds() -> FrozenSet[str]:
    """Return the set of valid evidence kind strings."""
    return _VALID_EVIDENCE_KINDS
