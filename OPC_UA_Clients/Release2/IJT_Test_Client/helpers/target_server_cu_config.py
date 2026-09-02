"""
Target Server CU execution configuration (internal typed model).

Holds the typed, validated execution policy used by the Target Server run
path: endpoint, CU execution policy, trigger modes, selection, workflow
execution, and reporting.

This module is **not** a tester-facing file schema. The single tester-facing
schema is the SUT manifest (``*.sut.yaml``, see :mod:`helpers.sut_manifest`),
which normalizes its own sections and calls :func:`build_execution_profile`
here so validation exists exactly once.

The stable outcome and reason-code vocabulary is defined in
:mod:`helpers.canonical_outcomes` and re-exported below for existing importers.

Usage::

    from helpers.sut_manifest import load_sut_manifest

    manifest = load_sut_manifest(Path("target_server_cu_profiles/simulator.sut.yaml"))
    cfg = manifest.to_execution_profile()

    if cfg.cu_execution.allow_state_changing_method("SelectJoiningProcess"):
        ...
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from helpers.canonical_outcomes import (
    ALL_OUTCOMES,
    OUTCOME_BLOCKED,
    OUTCOME_CLAIM_MISMATCH,
    OUTCOME_CONFIGURATION_ERROR,
    OUTCOME_FAILED,
    OUTCOME_MANUAL_REQUIRED,
    OUTCOME_PASSED,
    OUTCOME_UNSUPPORTED,
    REASON_CLAIM_METHOD_MISSING,
    REASON_CLAIM_STATUS_NOT_SUPPORTED,
    REASON_CONFIGURATION_INVALID,
    REASON_ENDPOINT_UNREACHABLE,
    REASON_JOINING_SYSTEM_NOT_FOUND,
    REASON_MANUAL_TRIGGER_REQUIRED,
    REASON_MISSING_RUNTIME_PRECONDITION,
    REASON_NAMESPACE_UNAVAILABLE,
    REASON_NO_PROCESS_CONFIGURED,
    REASON_SAFETY_INTERLOCK_ACTIVE,
    REASON_STATUS_NOT_SUPPORTED,
    REASON_TARGET_SERVER_NOT_READY,
    REASON_TOOL_DISCONNECTED,
    REASON_UNSAFE_METHOD_NOT_ENABLED,
)
from helpers.namespaces import ResultState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stable vocabulary constants
# ---------------------------------------------------------------------------

SUPPORTED_SCHEMA_VERSIONS: frozenset[int] = frozenset({1})

VALID_EXECUTION_MODES: frozenset[str] = frozenset({"automated", "guided", "preflight_only"})
VALID_SCORING_MODES: frozenset[str] = frozenset({"diagnostic", "strict_profile", "acceptance"})
VALID_PRECONDITION_POLICIES: frozenset[str] = frozenset({"blocked", "failed", "skip"})
VALID_STATE_CHANGING_POLICIES: frozenset[str] = frozenset({"require_explicit_opt_in", "allow_all", "deny_all"})

VALID_RESULT_TRIGGER_MODES: frozenset[str] = frozenset(
    {"simulate_methods", "start_selected_joining", "manual_trigger", "observe_only", "none"}
)
VALID_EVENT_TRIGGER_MODES: frozenset[str] = frozenset({"simulate_methods", "manual_trigger", "observe_only", "none"})
VALID_CONDITION_TRIGGER_MODES: frozenset[str] = frozenset(
    {"simulate_methods", "manual_trigger", "observe_only", "none"}
)

VALID_SELECTION_POLICIES: frozenset[str] = frozenset(
    {"first_available", "first_ready", "first_compatible", "exact_match"}
)
VALID_IDENTIFIER_STRATEGIES: frozenset[str] = frozenset(
    {"id_only", "id_with_origin", "id_with_selection_name", "all_available"}
)
VALID_CLEANUP_POLICIES: frozenset[str] = frozenset({"best_effort_with_evidence", "strict_cleanup", "no_cleanup"})
VALID_RESULT_CLASSIFICATIONS: frozenset[str] = frozenset(
    {"single", "batch", "sync", "job", "stitching", "intervention", "text", "any"}
)

# The outcome and reason-code vocabulary lives in helpers.canonical_outcomes —
# it is the single vocabulary source. These names are re-exported here so
# existing importers keep working without a second definition of the values.
__all__ = [
    "ALL_OUTCOMES",
    "OUTCOME_BLOCKED",
    "OUTCOME_CLAIM_MISMATCH",
    "OUTCOME_CONFIGURATION_ERROR",
    "OUTCOME_FAILED",
    "OUTCOME_MANUAL_REQUIRED",
    "OUTCOME_PASSED",
    "OUTCOME_UNSUPPORTED",
    "REASON_CLAIM_METHOD_MISSING",
    "REASON_CLAIM_STATUS_NOT_SUPPORTED",
    "REASON_CONFIGURATION_INVALID",
    "REASON_ENDPOINT_UNREACHABLE",
    "REASON_JOINING_SYSTEM_NOT_FOUND",
    "REASON_MANUAL_TRIGGER_REQUIRED",
    "REASON_MISSING_RUNTIME_PRECONDITION",
    "REASON_NAMESPACE_UNAVAILABLE",
    "REASON_NO_PROCESS_CONFIGURED",
    "REASON_SAFETY_INTERLOCK_ACTIVE",
    "REASON_STATUS_NOT_SUPPORTED",
    "REASON_TARGET_SERVER_NOT_READY",
    "REASON_TOOL_DISCONNECTED",
    "REASON_UNSAFE_METHOD_NOT_ENABLED",
    "SUPPORTED_SCHEMA_VERSIONS",
    "CleanupConfig",
    "CuExecutionConfig",
    "ExpectedResultsConfig",
    "ExpectedServerConfig",
    "JoiningProcessSelectionConfig",
    "ReportingConfig",
    "SelectionConfig",
    "StateChangingMethodsConfig",
    "TargetConfig",
    "TargetServerConfigError",
    "TargetServerCuProfile",
    "ToolSelectionConfig",
    "TriggerConfig",
    "TriggersConfig",
    "WorkflowExecutionConfig",
    "build_default_profile",
    "build_execution_profile",
    "parse_cu_execution",
    "parse_reporting",
    "parse_selection",
    "parse_target",
    "parse_triggers",
    "parse_workflow_execution",
    "require_bool",
    "require_enum",
    "require_int",
    "require_number",
    "require_str",
    "require_str_list",
]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class TargetServerConfigError(ValueError):
    """Raised for malformed or invalid target_server CU profile YAML."""


# ---------------------------------------------------------------------------
# Config dataclasses (typed, immutable)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StateChangingMethodsConfig:
    """Policy for state-changing OPC UA method calls."""

    default_policy: str = "require_explicit_opt_in"
    allowed_methods: tuple[str, ...] = field(default_factory=tuple)

    def allow_state_changing_method(self, method_name: str) -> bool:
        """Return True if *method_name* is allowed to be called on a real target_server."""
        if self.default_policy == "allow_all":
            return True
        if self.default_policy == "deny_all":
            return False
        # require_explicit_opt_in — check the allowed list
        return method_name in self.allowed_methods


@dataclass(frozen=True)
class CuExecutionConfig:
    """CU test execution policy."""

    default_mode: str = "automated"
    scoring_mode: str = "diagnostic"
    precondition_failure_policy: str = "blocked"
    allow_manual_steps: bool = False
    default_timeout_seconds: float = 60.0
    state_changing_methods: StateChangingMethodsConfig = field(default_factory=StateChangingMethodsConfig)
    method_status_policies: dict[str, str] = field(default_factory=dict)
    extension_fields: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TriggerConfig:
    """Configuration for a single trigger type (result, event, or condition)."""

    mode: str
    timeout_seconds: float = 60.0
    deselect_after_joining: bool = False


@dataclass(frozen=True)
class TriggersConfig:
    """Trigger configurations for result, event, and condition evidence."""

    result: TriggerConfig = field(default_factory=lambda: TriggerConfig(mode="none"))
    event: TriggerConfig = field(default_factory=lambda: TriggerConfig(mode="observe_only"))
    condition: TriggerConfig = field(default_factory=lambda: TriggerConfig(mode="observe_only"))


@dataclass(frozen=True)
class ToolSelectionConfig:
    """Tool discovery and selection policy."""

    policy: str = "first_ready"
    product_instance_uri: str = ""
    capability_tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class JoiningProcessSelectionConfig:
    """Joining process discovery and selection policy."""

    policy: str = "first_compatible"
    joining_process_id: str = ""
    joining_process_origin_id: str = ""
    selection_name: str = ""
    identifier_strategy: str = "id_only"
    capability_tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SelectionConfig:
    """Tool and joining-process selection configuration."""

    tool: ToolSelectionConfig = field(default_factory=ToolSelectionConfig)
    joining_process: JoiningProcessSelectionConfig = field(default_factory=JoiningProcessSelectionConfig)
    joining_processes: dict[str, JoiningProcessSelectionConfig] = field(default_factory=dict)


@dataclass(frozen=True)
class ExpectedResultsConfig:
    """Expected result evidence configuration."""

    classification: str = "single"
    intermediate_classifications: tuple[str, ...] = field(default_factory=tuple)
    final_result_required: bool = True
    timeout_seconds: float = 60.0
    expected_terminal_result_state: int = 1
    reject_ok_evaluation_on_abort: bool = False


@dataclass(frozen=True)
class CleanupConfig:
    """Cleanup policy after target_server CU execution."""

    policy: str = "best_effort_with_evidence"
    deselect_process: bool = True
    reset_identifiers: bool = False


@dataclass(frozen=True)
class WorkflowExecutionConfig:
    """Full joining workflow execution configuration."""

    approved_workflows: tuple[str, ...] = ()
    max_start_invocations: int = 6
    consecutive_start_delay_seconds: float = 0.25
    expected_results: ExpectedResultsConfig = field(default_factory=ExpectedResultsConfig)
    cleanup: CleanupConfig = field(default_factory=CleanupConfig)


@dataclass(frozen=True)
class ExpectedServerConfig:
    """Optional server identity cross-check (warn-only by default)."""

    application_name: str = ""
    application_version: str = ""
    warn_only_on_version_drift: bool = True


@dataclass(frozen=True)
class TargetConfig:
    """TargetServer endpoint and selection configuration."""

    endpoint: str = ""
    expected_server: ExpectedServerConfig = field(default_factory=ExpectedServerConfig)


@dataclass(frozen=True)
class ReportingConfig:
    """Reporting and output configuration."""

    output_dir: str = "test-results/target-server-cu"
    sanitize_shared_artifacts: bool = True
    keep_local_exact_debug_artifacts: bool = False


@dataclass(frozen=True)
class TargetServerCuProfile:
    """Complete target_server CU execution profile (built from a SUT manifest).

    Attributes:
        schema_version:     Execution config format version (in SUPPORTED_SCHEMA_VERSIONS).
        profile_name:       Human-readable label for the SUT.
        description:        Optional description for documentation.
        capabilities_file:  Path to the file that carries the authoritative CU
                            claims for this run — normally the SUT manifest itself.
        source_path:        Absolute path of the source manifest.
        target:             Endpoint and server selection.
        cu_execution:       CU test execution policy.
        selection:          Tool and process selection.
        triggers:           Result/event/condition trigger config.
        workflow_execution: Joining workflow execution config.
        reporting:          Output and sanitization config.
    """

    schema_version: int
    profile_name: str
    description: str
    capabilities_file: str
    source_path: str
    target: TargetConfig
    cu_execution: CuExecutionConfig
    selection: SelectionConfig
    triggers: TriggersConfig
    workflow_execution: WorkflowExecutionConfig
    reporting: ReportingConfig

    def output_dir_path(self, base_dir: Path | None = None) -> Path:
        """Return the absolute output directory path.

        Relative output directories are resolved against ``base_dir`` when provided,
        otherwise the current working directory. Capabilities files remain profile-
        relative, but generated evidence should land in the runner's stable output
        tree rather than under ``target_server_cu_profiles``.
        """
        out = Path(self.reporting.output_dir)
        if not out.is_absolute():
            return ((base_dir or Path.cwd()) / out).resolve()
        return out.resolve()

    def capabilities_file_path(self) -> Path | None:
        """Return the resolved capabilities_file path, or None if not set."""
        if not self.capabilities_file:
            return None
        caps = Path(self.capabilities_file)
        if caps.is_absolute():
            return caps
        if self.source_path:
            profile_dir = Path(self.source_path).parent
            return (profile_dir / caps).resolve()
        return caps


# ---------------------------------------------------------------------------
# Parser helpers
# ---------------------------------------------------------------------------


def require_str(mapping: dict, key: str, context: str) -> str:
    val = mapping.get(key, "")
    if not isinstance(val, str):
        raise TargetServerConfigError(f"{context}: '{key}' must be a string, got {type(val).__name__}")
    return val


def require_bool(mapping: dict, key: str, default: bool, context: str) -> bool:
    val = mapping.get(key, default)
    if not isinstance(val, bool):
        raise TargetServerConfigError(f"{context}: '{key}' must be a boolean, got {type(val).__name__}")
    return val


def require_number(mapping: dict, key: str, default: float, context: str, *, min_val: float | None = None) -> float:
    val = mapping.get(key, default)
    if not isinstance(val, (int, float)):
        raise TargetServerConfigError(f"{context}: '{key}' must be a number, got {type(val).__name__}")
    f_val = float(val)
    if min_val is not None and f_val < min_val:
        raise TargetServerConfigError(f"{context}: '{key}' must be >= {min_val}, got {f_val}")
    return f_val


def require_int(mapping: dict, key: str, default: int, context: str, *, min_val: int | None = None) -> int:
    val = mapping.get(key, default)
    if not isinstance(val, int) or isinstance(val, bool):
        raise TargetServerConfigError(f"{context}: '{key}' must be an integer, got {type(val).__name__}")
    if min_val is not None and val < min_val:
        raise TargetServerConfigError(f"{context}: '{key}' must be >= {min_val}, got {val}")
    return val


def require_enum(mapping: dict, key: str, default: str, valid: frozenset[str], context: str) -> str:
    val = mapping.get(key, default)
    if not isinstance(val, str):
        raise TargetServerConfigError(f"{context}: '{key}' must be a string, got {type(val).__name__}")
    if val not in valid:
        raise TargetServerConfigError(f"{context}: invalid value '{val}' for '{key}'. Valid values: {sorted(valid)}")
    return val


def require_str_list(mapping: dict, key: str, context: str) -> list[str]:
    val = mapping.get(key, [])
    if isinstance(val, tuple):
        val = list(val)
    if not isinstance(val, list):
        raise TargetServerConfigError(f"{context}: '{key}' must be a list, got {type(val).__name__}")
    for i, item in enumerate(val):
        if not isinstance(item, str):
            raise TargetServerConfigError(f"{context}: '{key}[{i}]' must be a string, got {type(item).__name__}")
    return val


def _parse_state_changing(raw: dict, context: str) -> StateChangingMethodsConfig:
    policy = require_enum(raw, "default_policy", "require_explicit_opt_in", VALID_STATE_CHANGING_POLICIES, context)
    allowed_methods = tuple(require_str_list(raw, "allowed_methods", context))
    return StateChangingMethodsConfig(default_policy=policy, allowed_methods=allowed_methods)


def parse_cu_execution(raw: dict, context: str = "cu_execution") -> CuExecutionConfig:
    mode = require_enum(raw, "default_mode", "automated", VALID_EXECUTION_MODES, context)
    scoring = require_enum(raw, "scoring_mode", "diagnostic", VALID_SCORING_MODES, context)
    precondition = require_enum(raw, "precondition_failure_policy", "blocked", VALID_PRECONDITION_POLICIES, context)
    allow_manual = require_bool(raw, "allow_manual_steps", False, context)
    timeout = require_number(raw, "default_timeout_seconds", 60.0, context, min_val=1.0)

    sc_raw = raw.get("state_changing_methods", {})
    if not isinstance(sc_raw, dict):
        raise TargetServerConfigError(f"{context}: 'state_changing_methods' must be a mapping")
    sc_cfg = _parse_state_changing(sc_raw, f"{context}.state_changing_methods")

    msp = raw.get("method_status_policies", {})
    if not isinstance(msp, dict):
        raise TargetServerConfigError(f"{context}: 'method_status_policies' must be a mapping")
    for k, v in msp.items():
        if not isinstance(k, str) or not isinstance(v, str):
            raise TargetServerConfigError(f"{context}: 'method_status_policies' must map string→string")

    ext = raw.get("extension_fields", {})
    if not isinstance(ext, dict):
        raise TargetServerConfigError(f"{context}: 'extension_fields' must be a mapping")

    return CuExecutionConfig(
        default_mode=mode,
        scoring_mode=scoring,
        precondition_failure_policy=precondition,
        allow_manual_steps=allow_manual,
        default_timeout_seconds=timeout,
        state_changing_methods=sc_cfg,
        method_status_policies=dict(msp),
        extension_fields=dict(ext),
    )


def _parse_trigger_config(raw: dict, context: str, valid_modes: frozenset[str], default_mode: str) -> TriggerConfig:
    mode = require_enum(raw, "mode", default_mode, valid_modes, context)
    timeout = require_number(raw, "timeout_seconds", 60.0, context, min_val=1.0)
    deselect = require_bool(raw, "deselect_after_joining", False, context)
    return TriggerConfig(mode=mode, timeout_seconds=timeout, deselect_after_joining=deselect)


def parse_triggers(raw: dict, context: str = "triggers") -> TriggersConfig:
    result_raw = raw.get("result", {})
    if not isinstance(result_raw, dict):
        raise TargetServerConfigError(f"{context}: 'result' must be a mapping")
    result_cfg = _parse_trigger_config(result_raw, f"{context}.result", VALID_RESULT_TRIGGER_MODES, "none")

    event_raw = raw.get("event", {})
    if not isinstance(event_raw, dict):
        raise TargetServerConfigError(f"{context}: 'event' must be a mapping")
    event_cfg = _parse_trigger_config(event_raw, f"{context}.event", VALID_EVENT_TRIGGER_MODES, "observe_only")

    cond_raw = raw.get("condition", {})
    if not isinstance(cond_raw, dict):
        raise TargetServerConfigError(f"{context}: 'condition' must be a mapping")
    cond_cfg = _parse_trigger_config(cond_raw, f"{context}.condition", VALID_CONDITION_TRIGGER_MODES, "observe_only")

    return TriggersConfig(result=result_cfg, event=event_cfg, condition=cond_cfg)


def _parse_tool_selection(raw: dict, context: str) -> ToolSelectionConfig:
    policy = require_enum(raw, "policy", "first_ready", VALID_SELECTION_POLICIES, context)
    piu = require_str(raw, "product_instance_uri", context)
    tags = tuple(require_str_list(raw, "capability_tags", context))
    return ToolSelectionConfig(policy=policy, product_instance_uri=piu, capability_tags=tags)


def _parse_jp_selection(raw: dict, context: str) -> JoiningProcessSelectionConfig:
    policy = require_enum(raw, "policy", "first_compatible", VALID_SELECTION_POLICIES, context)
    jp_id = require_str(raw, "joining_process_id", context)
    jp_origin = require_str(raw, "joining_process_origin_id", context)
    sel_name = require_str(raw, "selection_name", context)
    strat = require_enum(raw, "identifier_strategy", "id_only", VALID_IDENTIFIER_STRATEGIES, context)
    tags = tuple(require_str_list(raw, "capability_tags", context))
    return JoiningProcessSelectionConfig(
        policy=policy,
        joining_process_id=jp_id,
        joining_process_origin_id=jp_origin,
        selection_name=sel_name,
        identifier_strategy=strat,
        capability_tags=tags,
    )


def parse_selection(raw: dict, context: str = "selection") -> SelectionConfig:
    tool_raw = raw.get("tool", {})
    if not isinstance(tool_raw, dict):
        raise TargetServerConfigError(f"{context}: 'tool' must be a mapping")
    tool_cfg = _parse_tool_selection(tool_raw, f"{context}.tool")

    jp_raw = raw.get("joining_process", {})
    if not isinstance(jp_raw, dict):
        raise TargetServerConfigError(f"{context}: 'joining_process' must be a mapping")
    jp_cfg = _parse_jp_selection(jp_raw, f"{context}.joining_process")

    jps_raw = raw.get("joining_processes", {})
    if not isinstance(jps_raw, dict):
        raise TargetServerConfigError(f"{context}: 'joining_processes' must be a mapping")
    jps_dict: dict[str, JoiningProcessSelectionConfig] = {}
    for key, sub_raw in jps_raw.items():
        if not isinstance(key, str):
            raise TargetServerConfigError(f"{context}.joining_processes: keys must be strings")
        norm_key = key.lower().strip()
        if not isinstance(sub_raw, dict):
            raise TargetServerConfigError(f"{context}.joining_processes.{key}: value must be a mapping")
        jps_dict[norm_key] = _parse_jp_selection(sub_raw, f"{context}.joining_processes.{key}")

    return SelectionConfig(tool=tool_cfg, joining_process=jp_cfg, joining_processes=jps_dict)


def _parse_expected_results(raw: dict, context: str) -> ExpectedResultsConfig:
    classification = require_enum(raw, "classification", "single", VALID_RESULT_CLASSIFICATIONS, context)
    intermediate = tuple(require_str_list(raw, "intermediate_classifications", context))
    invalid_intermediate = sorted(set(intermediate) - (VALID_RESULT_CLASSIFICATIONS - {"any"}))
    if invalid_intermediate:
        raise TargetServerConfigError(
            f"{context}.intermediate_classifications contains invalid values: {invalid_intermediate}"
        )
    final_req = require_bool(raw, "final_result_required", True, context)
    timeout = require_number(raw, "timeout_seconds", 60.0, context, min_val=1.0)
    expected_state = require_int(raw, "expected_terminal_result_state", ResultState.COMPLETED, context)
    if expected_state not in ResultState.VALID_TERMINAL_STATES:
        raise TargetServerConfigError(
            f"{context}.expected_terminal_result_state must be one of "
            f"{sorted(ResultState.VALID_TERMINAL_STATES)} (1=COMPLETED, 3=ABORTED, 4=FAILED); got {expected_state}"
        )
    reject_ok_eval = require_bool(raw, "reject_ok_evaluation_on_abort", False, context)
    return ExpectedResultsConfig(
        classification=classification,
        intermediate_classifications=intermediate,
        final_result_required=final_req,
        timeout_seconds=timeout,
        expected_terminal_result_state=expected_state,
        reject_ok_evaluation_on_abort=reject_ok_eval,
    )


def _parse_cleanup(raw: dict, context: str) -> CleanupConfig:
    policy = require_enum(raw, "policy", "best_effort_with_evidence", VALID_CLEANUP_POLICIES, context)
    deselect = require_bool(raw, "deselect_process", True, context)
    reset = require_bool(raw, "reset_identifiers", False, context)
    return CleanupConfig(policy=policy, deselect_process=deselect, reset_identifiers=reset)


def parse_workflow_execution(raw: dict, context: str = "workflow_execution") -> WorkflowExecutionConfig:
    approved = tuple(require_str_list(raw, "approved_workflows", context)) if "approved_workflows" in raw else ()
    max_starts = require_int(raw, "max_start_invocations", 6, context, min_val=1)
    pacing = require_number(raw, "consecutive_start_delay_seconds", 0.25, context, min_val=0.0)

    er_raw = raw.get("expected_results", {})
    if not isinstance(er_raw, dict):
        raise TargetServerConfigError(f"{context}: 'expected_results' must be a mapping")
    er_cfg = _parse_expected_results(er_raw, f"{context}.expected_results")

    cleanup_raw = raw.get("cleanup", {})
    if not isinstance(cleanup_raw, dict):
        raise TargetServerConfigError(f"{context}: 'cleanup' must be a mapping")
    cleanup_cfg = _parse_cleanup(cleanup_raw, f"{context}.cleanup")

    return WorkflowExecutionConfig(
        approved_workflows=approved,
        max_start_invocations=max_starts,
        consecutive_start_delay_seconds=pacing,
        expected_results=er_cfg,
        cleanup=cleanup_cfg,
    )


def _parse_expected_server(raw: dict, context: str) -> ExpectedServerConfig:
    app_name = require_str(raw, "application_name", context)
    app_version = require_str(raw, "application_version", context)
    warn_only = require_bool(raw, "warn_only_on_version_drift", True, context)
    return ExpectedServerConfig(
        application_name=app_name,
        application_version=app_version,
        warn_only_on_version_drift=warn_only,
    )


def parse_target(raw: dict, context: str = "target") -> TargetConfig:
    endpoint = require_str(raw, "endpoint", context)
    es_raw = raw.get("expected_server", {})
    if not isinstance(es_raw, dict):
        raise TargetServerConfigError(f"{context}: 'expected_server' must be a mapping")
    es_cfg = _parse_expected_server(es_raw, f"{context}.expected_server")
    return TargetConfig(endpoint=endpoint, expected_server=es_cfg)


def parse_reporting(raw: dict, context: str = "reporting") -> ReportingConfig:
    output_dir = require_str(raw, "output_dir", context) or "test-results/target-server-cu"
    sanitize = require_bool(raw, "sanitize_shared_artifacts", True, context)
    keep_debug = require_bool(raw, "keep_local_exact_debug_artifacts", False, context)
    return ReportingConfig(
        output_dir=output_dir,
        sanitize_shared_artifacts=sanitize,
        keep_local_exact_debug_artifacts=keep_debug,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_execution_profile(raw: dict, source_path: str = "<in-memory>") -> TargetServerCuProfile:
    """Build a validated :class:`TargetServerCuProfile` from normalized sections.

    This is the internal execution-config constructor. It is **not** a
    tester-facing file schema: the only file schema is the SUT manifest
    (``*.sut.yaml``, see :mod:`helpers.sut_manifest`), which normalizes its
    own sections and calls this function to reuse the validation below.

    Raises
    ------
    TargetServerConfigError
        When a section is malformed, has the wrong type, or contains an
        invalid enum value. Messages carry the field path and valid values.
    """
    if not isinstance(raw, dict):
        raise TargetServerConfigError("Execution profile data must be a mapping (dict)")

    sv = raw.get("schema_version")
    if sv is None:
        raise TargetServerConfigError("Missing required field 'schema_version'")
    if not isinstance(sv, int) or isinstance(sv, bool):
        raise TargetServerConfigError(f"'schema_version' must be an integer, got {type(sv).__name__}")
    if sv not in SUPPORTED_SCHEMA_VERSIONS:
        raise TargetServerConfigError(
            f"Unsupported schema_version {sv}. Supported: {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
        )

    profile_name = require_str(raw, "profile_name", "root")
    description = require_str(raw, "description", "root")
    capabilities_file = require_str(raw, "capabilities_file", "root")

    sections: dict[str, Any] = {}
    parsers = {
        "target": parse_target,
        "cu_execution": parse_cu_execution,
        "selection": parse_selection,
        "triggers": parse_triggers,
        "workflow_execution": parse_workflow_execution,
        "reporting": parse_reporting,
    }
    for name, parser in parsers.items():
        section_raw = raw.get(name, {})
        if not isinstance(section_raw, dict):
            raise TargetServerConfigError(f"'{name}' must be a mapping")
        sections[name] = parser(section_raw)

    return TargetServerCuProfile(
        schema_version=sv,
        profile_name=profile_name,
        description=description,
        capabilities_file=capabilities_file,
        source_path=source_path,
        target=sections["target"],
        cu_execution=sections["cu_execution"],
        selection=sections["selection"],
        triggers=sections["triggers"],
        workflow_execution=sections["workflow_execution"],
        reporting=sections["reporting"],
    )


def build_default_profile(endpoint: str = "") -> TargetServerCuProfile:
    """Return a safe default profile suitable for automated read-only discovery runs."""
    return TargetServerCuProfile(
        schema_version=1,
        profile_name="Default (generated)",
        description="Minimal default profile with no state-changing methods allowed.",
        capabilities_file="",
        source_path="<default>",
        target=TargetConfig(endpoint=endpoint),
        cu_execution=CuExecutionConfig(),
        selection=SelectionConfig(),
        triggers=TriggersConfig(),
        workflow_execution=WorkflowExecutionConfig(),
        reporting=ReportingConfig(),
    )
