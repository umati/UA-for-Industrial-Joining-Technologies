"""
Target Server CU configuration loader and validator.

Loads and strictly validates Target Server CU execution profiles (YAML).
Keeps a clear separation from helpers/profile_loader.py which handles
official CU support declarations (profiles, facets, cu_overrides).

This module handles:
  - target server endpoint and server selection config
  - cu_execution policy (mode, scoring, preconditions, state-changing methods)
  - trigger modes (result, event, condition)
  - workflow_execution setup (selection, start policy, cleanup)
  - reporting options

Usage::

    from helpers.target_server_cu_config import load_target_server_profile, TargetServerConfigError

    try:
        cfg = load_target_server_profile(Path("target_server_cu_profiles/my_profile.yaml"))
    except TargetServerConfigError as exc:
        print(f"Configuration error: {exc}")
        sys.exit(1)

    if cfg.cu_execution.allow_state_changing_method("SelectJoiningProcess"):
        ...
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

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
VALID_START_INVOCATION_POLICIES: frozenset[str] = frozenset(
    {"single_start_produces_final_result", "one_start_per_operation", "manual_operation_trigger"}
)
VALID_CLEANUP_POLICIES: frozenset[str] = frozenset({"best_effort_with_evidence", "strict_cleanup", "no_cleanup"})
VALID_RESULT_CLASSIFICATIONS: frozenset[str] = frozenset({"single", "batch", "sync", "job", "any"})

# Stable outcome vocabulary used by readiness checks and runner reporting.
OUTCOME_PASSED = "passed"
OUTCOME_FAILED = "failed"
OUTCOME_BLOCKED = "blocked"
OUTCOME_UNSUPPORTED = "unsupported"
OUTCOME_MANUAL_REQUIRED = "manual_required"
OUTCOME_CLAIM_MISMATCH = "claim_mismatch"
OUTCOME_CONFIGURATION_ERROR = "configuration_error"

ALL_OUTCOMES: frozenset[str] = frozenset(
    {
        OUTCOME_PASSED,
        OUTCOME_FAILED,
        OUTCOME_BLOCKED,
        OUTCOME_UNSUPPORTED,
        OUTCOME_MANUAL_REQUIRED,
        OUTCOME_CLAIM_MISMATCH,
        OUTCOME_CONFIGURATION_ERROR,
    }
)

# Stable reason code vocabulary for blocked/failed outcomes.
REASON_TOOL_DISCONNECTED = "tool_disconnected"
REASON_NO_PROCESS_CONFIGURED = "no_process_configured"
REASON_MANUAL_TRIGGER_REQUIRED = "manual_trigger_required"
REASON_UNSAFE_METHOD_NOT_ENABLED = "unsafe_method_not_enabled"
REASON_CLAIM_METHOD_MISSING = "claim_method_missing"
REASON_CLAIM_STATUS_NOT_SUPPORTED = "claim_status_not_supported"
REASON_STATUS_NOT_SUPPORTED = "status_not_supported"
REASON_CONFIGURATION_INVALID = "configuration_invalid"
REASON_TARGET_SERVER_NOT_READY = "target_server_not_ready"
REASON_MISSING_RUNTIME_PRECONDITION = "missing_runtime_precondition"
REASON_SAFETY_INTERLOCK_ACTIVE = "safety_interlock_active"
REASON_NAMESPACE_UNAVAILABLE = "namespace_unavailable"
REASON_JOINING_SYSTEM_NOT_FOUND = "joining_system_not_found"
REASON_ENDPOINT_UNREACHABLE = "endpoint_unreachable"


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
    capability_tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SelectionConfig:
    """Tool and joining-process selection configuration."""

    tool: ToolSelectionConfig = field(default_factory=ToolSelectionConfig)
    joining_process: JoiningProcessSelectionConfig = field(default_factory=JoiningProcessSelectionConfig)


@dataclass(frozen=True)
class ExpectedResultsConfig:
    """Expected result evidence configuration."""

    classification: str = "single"
    final_result_required: bool = True
    timeout_seconds: float = 60.0


@dataclass(frozen=True)
class CleanupConfig:
    """Cleanup policy after target_server CU execution."""

    policy: str = "best_effort_with_evidence"
    deselect_process: bool = True
    reset_identifiers: bool = False


@dataclass(frozen=True)
class WorkflowExecutionConfig:
    """Full joining workflow execution configuration."""

    start_invocation_policy: str = "single_start_produces_final_result"
    expected_operation_count: int = 1
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
    """Complete target_server CU execution profile loaded from YAML.

    Attributes:
        schema_version:     Profile format version (must be in SUPPORTED_SCHEMA_VERSIONS).
        profile_name:       Human-readable label for the profile.
        description:        Optional description for documentation.
        capabilities_file:  Path (relative to profile) to server_capabilities.yaml.
        source_path:        Absolute path of the loaded YAML file.
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


def _require_str(mapping: dict, key: str, context: str) -> str:
    val = mapping.get(key, "")
    if not isinstance(val, str):
        raise TargetServerConfigError(f"{context}: '{key}' must be a string, got {type(val).__name__}")
    return val


def _require_bool(mapping: dict, key: str, default: bool, context: str) -> bool:
    val = mapping.get(key, default)
    if not isinstance(val, bool):
        raise TargetServerConfigError(f"{context}: '{key}' must be a boolean, got {type(val).__name__}")
    return val


def _require_number(mapping: dict, key: str, default: float, context: str, *, min_val: float | None = None) -> float:
    val = mapping.get(key, default)
    if not isinstance(val, (int, float)):
        raise TargetServerConfigError(f"{context}: '{key}' must be a number, got {type(val).__name__}")
    f_val = float(val)
    if min_val is not None and f_val < min_val:
        raise TargetServerConfigError(f"{context}: '{key}' must be >= {min_val}, got {f_val}")
    return f_val


def _require_int(mapping: dict, key: str, default: int, context: str, *, min_val: int | None = None) -> int:
    val = mapping.get(key, default)
    if not isinstance(val, int) or isinstance(val, bool):
        raise TargetServerConfigError(f"{context}: '{key}' must be an integer, got {type(val).__name__}")
    if min_val is not None and val < min_val:
        raise TargetServerConfigError(f"{context}: '{key}' must be >= {min_val}, got {val}")
    return val


def _require_enum(mapping: dict, key: str, default: str, valid: frozenset[str], context: str) -> str:
    val = mapping.get(key, default)
    if not isinstance(val, str):
        raise TargetServerConfigError(f"{context}: '{key}' must be a string, got {type(val).__name__}")
    if val not in valid:
        raise TargetServerConfigError(f"{context}: invalid value '{val}' for '{key}'. Valid values: {sorted(valid)}")
    return val


def _require_str_list(mapping: dict, key: str, context: str) -> list[str]:
    val = mapping.get(key, [])
    if not isinstance(val, list):
        raise TargetServerConfigError(f"{context}: '{key}' must be a list, got {type(val).__name__}")
    for i, item in enumerate(val):
        if not isinstance(item, str):
            raise TargetServerConfigError(f"{context}: '{key}[{i}]' must be a string, got {type(item).__name__}")
    return val


def _parse_state_changing(raw: dict, context: str) -> StateChangingMethodsConfig:
    policy = _require_enum(raw, "default_policy", "require_explicit_opt_in", VALID_STATE_CHANGING_POLICIES, context)
    allowed_methods = tuple(_require_str_list(raw, "allowed_methods", context))
    return StateChangingMethodsConfig(default_policy=policy, allowed_methods=allowed_methods)


def _parse_cu_execution(raw: dict, context: str = "cu_execution") -> CuExecutionConfig:
    mode = _require_enum(raw, "default_mode", "automated", VALID_EXECUTION_MODES, context)
    scoring = _require_enum(raw, "scoring_mode", "diagnostic", VALID_SCORING_MODES, context)
    precondition = _require_enum(raw, "precondition_failure_policy", "blocked", VALID_PRECONDITION_POLICIES, context)
    allow_manual = _require_bool(raw, "allow_manual_steps", False, context)
    timeout = _require_number(raw, "default_timeout_seconds", 60.0, context, min_val=1.0)

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
    mode = _require_enum(raw, "mode", default_mode, valid_modes, context)
    timeout = _require_number(raw, "timeout_seconds", 60.0, context, min_val=1.0)
    deselect = _require_bool(raw, "deselect_after_joining", False, context)
    return TriggerConfig(mode=mode, timeout_seconds=timeout, deselect_after_joining=deselect)


def _parse_triggers(raw: dict, context: str = "triggers") -> TriggersConfig:
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
    policy = _require_enum(raw, "policy", "first_ready", VALID_SELECTION_POLICIES, context)
    piu = _require_str(raw, "product_instance_uri", context)
    tags = tuple(_require_str_list(raw, "capability_tags", context))
    return ToolSelectionConfig(policy=policy, product_instance_uri=piu, capability_tags=tags)


def _parse_jp_selection(raw: dict, context: str) -> JoiningProcessSelectionConfig:
    policy = _require_enum(raw, "policy", "first_compatible", VALID_SELECTION_POLICIES, context)
    jp_id = _require_str(raw, "joining_process_id", context)
    jp_origin = _require_str(raw, "joining_process_origin_id", context)
    sel_name = _require_str(raw, "selection_name", context)
    tags = tuple(_require_str_list(raw, "capability_tags", context))
    return JoiningProcessSelectionConfig(
        policy=policy,
        joining_process_id=jp_id,
        joining_process_origin_id=jp_origin,
        selection_name=sel_name,
        capability_tags=tags,
    )


def _parse_selection(raw: dict, context: str = "selection") -> SelectionConfig:
    tool_raw = raw.get("tool", {})
    if not isinstance(tool_raw, dict):
        raise TargetServerConfigError(f"{context}: 'tool' must be a mapping")
    tool_cfg = _parse_tool_selection(tool_raw, f"{context}.tool")

    jp_raw = raw.get("joining_process", {})
    if not isinstance(jp_raw, dict):
        raise TargetServerConfigError(f"{context}: 'joining_process' must be a mapping")
    jp_cfg = _parse_jp_selection(jp_raw, f"{context}.joining_process")

    return SelectionConfig(tool=tool_cfg, joining_process=jp_cfg)


def _parse_expected_results(raw: dict, context: str) -> ExpectedResultsConfig:
    classification = _require_enum(raw, "classification", "single", VALID_RESULT_CLASSIFICATIONS, context)
    final_req = _require_bool(raw, "final_result_required", True, context)
    timeout = _require_number(raw, "timeout_seconds", 60.0, context, min_val=1.0)
    return ExpectedResultsConfig(
        classification=classification,
        final_result_required=final_req,
        timeout_seconds=timeout,
    )


def _parse_cleanup(raw: dict, context: str) -> CleanupConfig:
    policy = _require_enum(raw, "policy", "best_effort_with_evidence", VALID_CLEANUP_POLICIES, context)
    deselect = _require_bool(raw, "deselect_process", True, context)
    reset = _require_bool(raw, "reset_identifiers", False, context)
    return CleanupConfig(policy=policy, deselect_process=deselect, reset_identifiers=reset)


def _parse_workflow_execution(raw: dict, context: str = "workflow_execution") -> WorkflowExecutionConfig:
    sip = _require_enum(
        raw,
        "start_invocation_policy",
        "single_start_produces_final_result",
        VALID_START_INVOCATION_POLICIES,
        context,
    )
    op_count = _require_int(raw, "expected_operation_count", 1, context, min_val=1)

    er_raw = raw.get("expected_results", {})
    if not isinstance(er_raw, dict):
        raise TargetServerConfigError(f"{context}: 'expected_results' must be a mapping")
    er_cfg = _parse_expected_results(er_raw, f"{context}.expected_results")

    cleanup_raw = raw.get("cleanup", {})
    if not isinstance(cleanup_raw, dict):
        raise TargetServerConfigError(f"{context}: 'cleanup' must be a mapping")
    cleanup_cfg = _parse_cleanup(cleanup_raw, f"{context}.cleanup")

    return WorkflowExecutionConfig(
        start_invocation_policy=sip,
        expected_operation_count=op_count,
        expected_results=er_cfg,
        cleanup=cleanup_cfg,
    )


def _parse_expected_server(raw: dict, context: str) -> ExpectedServerConfig:
    app_name = _require_str(raw, "application_name", context)
    app_version = _require_str(raw, "application_version", context)
    warn_only = _require_bool(raw, "warn_only_on_version_drift", True, context)
    return ExpectedServerConfig(
        application_name=app_name,
        application_version=app_version,
        warn_only_on_version_drift=warn_only,
    )


def _parse_target(raw: dict, context: str = "target") -> TargetConfig:
    endpoint = _require_str(raw, "endpoint", context)
    es_raw = raw.get("expected_server", {})
    if not isinstance(es_raw, dict):
        raise TargetServerConfigError(f"{context}: 'expected_server' must be a mapping")
    es_cfg = _parse_expected_server(es_raw, f"{context}.expected_server")
    return TargetConfig(endpoint=endpoint, expected_server=es_cfg)


def _parse_reporting(raw: dict, context: str = "reporting") -> ReportingConfig:
    output_dir = _require_str(raw, "output_dir", context) or "test-results/target-server-cu"
    sanitize = _require_bool(raw, "sanitize_shared_artifacts", True, context)
    keep_debug = _require_bool(raw, "keep_local_exact_debug_artifacts", False, context)
    return ReportingConfig(
        output_dir=output_dir,
        sanitize_shared_artifacts=sanitize,
        keep_local_exact_debug_artifacts=keep_debug,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_target_server_profile(path: Path) -> TargetServerCuProfile:
    """Load and strictly validate a target_server CU profile YAML file.

    Parameters
    ----------
    path:
        Path to a YAML profile file.

    Returns
    -------
    TargetServerCuProfile
        Validated, typed configuration object.

    Raises
    ------
    TargetServerConfigError
        When the YAML is malformed, missing required fields, or contains
        invalid enum values.  The exception message contains the field path
        and the list of valid values to assist correction.
    FileNotFoundError
        When *path* does not exist.
    """
    if not path.exists():
        raise FileNotFoundError(f"Target Server profile not found: {path}")

    try:
        with path.open(encoding="utf-8") as fh:
            raw: dict = yaml.safe_load(fh) or {}
    except yaml.YAMLError as exc:
        raise TargetServerConfigError(f"YAML parse error in '{path}': {exc}") from exc

    if not isinstance(raw, dict):
        raise TargetServerConfigError(f"Profile '{path}' must be a YAML mapping at the top level")

    # schema_version — required, must be supported
    sv = raw.get("schema_version")
    if sv is None:
        raise TargetServerConfigError(f"Profile '{path}' is missing required field 'schema_version'")
    if not isinstance(sv, int) or isinstance(sv, bool):
        raise TargetServerConfigError(f"Profile '{path}': 'schema_version' must be an integer, got {type(sv).__name__}")
    if sv not in SUPPORTED_SCHEMA_VERSIONS:
        raise TargetServerConfigError(
            f"Profile '{path}': unsupported schema_version {sv}. "
            f"Supported versions: {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
        )

    profile_name = _require_str(raw, "profile_name", "root")
    description = _require_str(raw, "description", "root")
    capabilities_file = _require_str(raw, "capabilities_file", "root")

    target_raw = raw.get("target", {})
    if not isinstance(target_raw, dict):
        raise TargetServerConfigError("'target' must be a mapping")
    target_cfg = _parse_target(target_raw)

    cu_exec_raw = raw.get("cu_execution", {})
    if not isinstance(cu_exec_raw, dict):
        raise TargetServerConfigError("'cu_execution' must be a mapping")
    cu_exec_cfg = _parse_cu_execution(cu_exec_raw)

    sel_raw = raw.get("selection", {})
    if not isinstance(sel_raw, dict):
        raise TargetServerConfigError("'selection' must be a mapping")
    sel_cfg = _parse_selection(sel_raw)

    triggers_raw = raw.get("triggers", {})
    if not isinstance(triggers_raw, dict):
        raise TargetServerConfigError("'triggers' must be a mapping")
    triggers_cfg = _parse_triggers(triggers_raw)

    wf_raw = raw.get("workflow_execution", {})
    if not isinstance(wf_raw, dict):
        raise TargetServerConfigError("'workflow_execution' must be a mapping")
    wf_cfg = _parse_workflow_execution(wf_raw)

    rep_raw = raw.get("reporting", {})
    if not isinstance(rep_raw, dict):
        raise TargetServerConfigError("'reporting' must be a mapping")
    rep_cfg = _parse_reporting(rep_raw)

    profile = TargetServerCuProfile(
        schema_version=sv,
        profile_name=profile_name or path.stem,
        description=description,
        capabilities_file=capabilities_file,
        source_path=str(path.resolve()),
        target=target_cfg,
        cu_execution=cu_exec_cfg,
        selection=sel_cfg,
        triggers=triggers_cfg,
        workflow_execution=wf_cfg,
        reporting=rep_cfg,
    )
    logger.info(
        "Loaded Target Server profile '%s' (schema_version=%d, mode=%s, trigger.result=%s)",
        profile.profile_name,
        profile.schema_version,
        profile.cu_execution.default_mode,
        profile.triggers.result.mode,
    )
    return profile


def load_target_server_profile_from_dict(raw: dict, source_path: str = "<in-memory>") -> TargetServerCuProfile:
    """Build a TargetServerCuProfile from an already-parsed dict.

    Useful for testing without a filesystem.  Raises TargetServerConfigError
    for invalid data, same as load_target_server_profile().
    """
    if not isinstance(raw, dict):
        raise TargetServerConfigError("Profile data must be a YAML mapping (dict)")

    sv = raw.get("schema_version")
    if sv is None:
        raise TargetServerConfigError("Missing required field 'schema_version'")
    if not isinstance(sv, int) or isinstance(sv, bool):
        raise TargetServerConfigError(f"'schema_version' must be an integer, got {type(sv).__name__}")
    if sv not in SUPPORTED_SCHEMA_VERSIONS:
        raise TargetServerConfigError(
            f"Unsupported schema_version {sv}. Supported: {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
        )

    profile_name = _require_str(raw, "profile_name", "root")
    description = _require_str(raw, "description", "root")
    capabilities_file = _require_str(raw, "capabilities_file", "root")

    target_cfg = _parse_target(raw.get("target") or {})
    cu_exec_cfg = _parse_cu_execution(raw.get("cu_execution") or {})
    sel_cfg = _parse_selection(raw.get("selection") or {})
    triggers_cfg = _parse_triggers(raw.get("triggers") or {})
    wf_cfg = _parse_workflow_execution(raw.get("workflow_execution") or {})
    rep_cfg = _parse_reporting(raw.get("reporting") or {})

    return TargetServerCuProfile(
        schema_version=sv,
        profile_name=profile_name,
        description=description,
        capabilities_file=capabilities_file,
        source_path=source_path,
        target=target_cfg,
        cu_execution=cu_exec_cfg,
        selection=sel_cfg,
        triggers=triggers_cfg,
        workflow_execution=wf_cfg,
        reporting=rep_cfg,
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
