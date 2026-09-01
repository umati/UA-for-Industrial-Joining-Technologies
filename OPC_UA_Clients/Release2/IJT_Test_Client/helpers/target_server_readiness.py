"""
Target Server readiness and preflight model for Target Server CU execution.

Provides reusable checks that classify whether a real target server is ready to
execute each class of CU test.  Results are returned as typed ReadinessOutcome
objects with stable reason codes, avoiding ambiguous pytest skip/fail mixes in
the runner layer.

Detailed outcome vocabulary (defined in helpers.canonical_outcomes):

  passed              All checked preconditions are met; execution can proceed.
  blocked             Target Server precondition unmet but config is valid.
                      Runner applies precondition_failure_policy from the manifest.
  failed              A hard check error that prevents any meaningful execution.
  unsupported         The CU/capability is not supported by this SUT manifest.
  manual_required     Evidence requires physical operator/tool action.
  claim_mismatch      Manifest claims support, but address-space probe disagrees.
  configuration_error Manifest is invalid or inconsistent; fix it before running.

Every outcome also carries a canonical final-report outcome
(``ReadinessOutcome.canonical_outcome``) — Passed, Failed, NotSupported,
Blocked, NotTested, or Inconclusive — which is what final JSON/Markdown/Excel
reports show. The detailed outcome and reason code above are preserved
alongside it.

Usage::

    from helpers.target_server_readiness import ReadinessOutcome, classify_preflight_outcome

    outcome = ReadinessOutcome(
        outcome=OUTCOME_BLOCKED,
        reason_code=REASON_NO_PROCESS_CONFIGURED,
        detail="No joining processes returned by GetJoiningProcessList",
    )
    if outcome.is_blocking:
        print(f"Blocked: {outcome.detail}")
"""

from __future__ import annotations

import logging
import socket
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping

from helpers.canonical_outcomes import (
    CANONICAL_OUTCOME_ORDER,
    CanonicalOutcome,
    canonical_for_legacy_outcome,
    reason_category,
)
from helpers.target_server_cu_config import (
    OUTCOME_BLOCKED,
    OUTCOME_CLAIM_MISMATCH,
    OUTCOME_CONFIGURATION_ERROR,
    OUTCOME_FAILED,
    OUTCOME_MANUAL_REQUIRED,
    OUTCOME_PASSED,
    OUTCOME_UNSUPPORTED,
    REASON_ENDPOINT_UNREACHABLE,
    REASON_JOINING_SYSTEM_NOT_FOUND,
    REASON_MANUAL_TRIGGER_REQUIRED,
    REASON_MISSING_RUNTIME_PRECONDITION,
    REASON_NAMESPACE_UNAVAILABLE,
    REASON_NO_PROCESS_CONFIGURED,
    REASON_TARGET_SERVER_NOT_READY,
    REASON_UNSAFE_METHOD_NOT_ENABLED,
    TargetServerCuProfile,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from helpers.connection_security import ConnectionSecurity

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Readiness outcome dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReadinessOutcome:
    """Result of a single readiness or preflight check.

    Attributes:
        outcome:     Stable outcome string from the target_server_cu_config vocabulary.
        reason_code: Stable machine-readable reason code (e.g. 'tool_disconnected').
        detail:      Human-readable description for operator/report output.
        check_name:  Which readiness check produced this outcome.
        evidence:    Optional dict of raw discovery evidence for report traceability.
    """

    outcome: str
    reason_code: str = ""
    detail: str = ""
    check_name: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    claimed: bool = False

    @property
    def canonical_outcome(self) -> CanonicalOutcome:
        """Return the canonical final-report outcome for this check."""
        return canonical_for_legacy_outcome(self.outcome, claimed=self.claimed)

    @property
    def canonical_label(self) -> str:
        """Return the public canonical label used by final reports."""
        return self.canonical_outcome.label

    @property
    def reason_category(self) -> str:
        """Return the stable category of :attr:`reason_code`."""
        return reason_category(self.reason_code)

    @property
    def passed(self) -> bool:
        """True when the check passed with no issues."""
        return self.outcome == OUTCOME_PASSED

    @property
    def is_blocking(self) -> bool:
        """True when the outcome prevents CU test execution."""
        return self.outcome in {
            OUTCOME_BLOCKED,
            OUTCOME_FAILED,
            OUTCOME_CONFIGURATION_ERROR,
            OUTCOME_CLAIM_MISMATCH,
        }

    @property
    def needs_manual_action(self) -> bool:
        """True when operator/physical action is needed before execution."""
        return self.outcome == OUTCOME_MANUAL_REQUIRED

    @property
    def is_unsupported(self) -> bool:
        """True when the CU/feature is not supported per profile."""
        return self.outcome == OUTCOME_UNSUPPORTED


@dataclass
class PreflightReport:
    """Aggregated preflight check results for a target_server CU run.

    Attributes:
        profile_name:   Name of the loaded target_server profile.
        endpoint:       Endpoint that was probed.
        checks:         Ordered list of individual check outcomes.
        discovery:      Raw discovery inventory (sanitized for shared artifacts).
    """

    profile_name: str = ""
    endpoint: str = ""
    checks: list[ReadinessOutcome] = field(default_factory=list)
    discovery: dict[str, Any] = field(default_factory=dict)

    def add(self, outcome: ReadinessOutcome) -> None:
        """Append *outcome* to the checks list."""
        self.checks.append(outcome)

    @property
    def all_passed(self) -> bool:
        """True when every check passed."""
        return all(c.passed for c in self.checks)

    @property
    def blocking_checks(self) -> list[ReadinessOutcome]:
        """Return checks with blocking outcomes."""
        return [c for c in self.checks if c.is_blocking]

    @property
    def manual_required_checks(self) -> list[ReadinessOutcome]:
        """Return checks that require manual operator action."""
        return [c for c in self.checks if c.needs_manual_action]

    @property
    def unsupported_checks(self) -> list[ReadinessOutcome]:
        """Return checks for unsupported capabilities."""
        return [c for c in self.checks if c.is_unsupported]

    def summary_lines(self) -> list[str]:
        """Return human-readable summary lines for operator output."""
        lines: list[str] = [
            f"Preflight: {self.profile_name} → {self.endpoint}",
            f"  Checks: {len(self.checks)} total, "
            f"{len([c for c in self.checks if c.passed])} passed, "
            f"{len(self.blocking_checks)} blocking, "
            f"{len(self.manual_required_checks)} manual_required, "
            f"{len(self.unsupported_checks)} unsupported",
        ]
        if self.blocking_checks:
            lines.append("  Blocking issues:")
            for c in self.blocking_checks:
                lines.append(f"    [{c.outcome}] {c.check_name}: {c.detail}")
        if self.manual_required_checks:
            lines.append("  Manual action required:")
            for c in self.manual_required_checks:
                lines.append(f"    [{c.outcome}] {c.check_name}: {c.detail}")
        return lines

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable dict for evidence reports.

        Final reports read ``canonical_outcome``; ``outcome``/``reason_code``
        are preserved for detail and backwards compatibility.
        """
        return {
            "profile_name": self.profile_name,
            "endpoint": self.endpoint,
            "all_passed": self.all_passed,
            "canonical_outcome": self.canonical_outcome.value,
            "canonical_label": self.canonical_outcome.label,
            "checks": [
                {
                    "outcome": c.outcome,
                    "canonical_outcome": c.canonical_outcome.value,
                    "canonical_label": c.canonical_label,
                    "reason_code": c.reason_code,
                    "reason_category": c.reason_category,
                    "detail": c.detail,
                    "check_name": c.check_name,
                }
                for c in self.checks
            ],
            "discovery": self.discovery,
        }

    @property
    def canonical_outcome(self) -> CanonicalOutcome:
        """Return the most severe canonical outcome across all checks."""
        if not self.checks:
            return CanonicalOutcome.NOT_TESTED
        return min(
            (check.canonical_outcome for check in self.checks),
            key=CANONICAL_OUTCOME_ORDER.index,
        )


# ---------------------------------------------------------------------------
# Individual check helpers (synchronous, no OPC UA dependency)
# ---------------------------------------------------------------------------


def check_endpoint_reachable(endpoint: str, *, timeout_s: float = 3.0) -> ReadinessOutcome:
    """Check whether the target_server endpoint TCP port is reachable.

    This is a synchronous TCP probe.  An OPC UA handshake is not attempted here
    — a passing probe only guarantees the TCP port is open.

    Parameters
    ----------
    endpoint:
        OPC UA endpoint URL (e.g. ``opc.tcp://10.0.0.1:40451``).
    timeout_s:
        TCP connection timeout in seconds.
    """
    check_name = "endpoint_reachable"
    host, port = _parse_endpoint(endpoint)
    if not host:
        return ReadinessOutcome(
            outcome=OUTCOME_CONFIGURATION_ERROR,
            reason_code="configuration_invalid",
            detail=f"Cannot parse host from endpoint '{endpoint}'",
            check_name=check_name,
        )
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            pass
        return ReadinessOutcome(
            outcome=OUTCOME_PASSED,
            detail=f"TCP port open at {host}:{port}",
            check_name=check_name,
        )
    except OSError as exc:
        return ReadinessOutcome(
            outcome=OUTCOME_BLOCKED,
            reason_code=REASON_ENDPOINT_UNREACHABLE,
            detail=f"Cannot reach {host}:{port}: {exc}",
            check_name=check_name,
        )


def resolve_profile_connection_security(profile: TargetServerCuProfile) -> ConnectionSecurity | None:
    """Return the connection security declared by the profile's SUT manifest.

    Returns ``None`` for ad hoc runs that have no manifest (``--endpoint``), which
    are anonymous by definition.
    """
    from helpers.connection_security import connection_security_from_manifest_path
    from helpers.sut_manifest import MANIFEST_SUFFIX

    source = profile.source_path or profile.capabilities_file
    if not source or not source.endswith(MANIFEST_SUFFIX):
        return None
    path = Path(source)
    if not path.exists():
        return None
    return connection_security_from_manifest_path(path)


def check_connection_security(
    security: ConnectionSecurity | None,
    *,
    env: Mapping[str, str] | None = None,
    allow_prompt: bool = True,
) -> ReadinessOutcome:
    """Check that the declared connection security/authentication can be applied.

    A declared mode that cannot be applied (missing certificate, key, credentials
    file, or environment secret) is a configuration error: it must stop the run
    before any test, instead of being silently ignored and producing an
    anonymous, unsecured session.

    ``allow_prompt`` is False for unattended runs; an interactive credential
    source is then reported as a configuration error rather than blocking on a
    console prompt no one will answer.
    """
    check_name = "connection_security"
    if security is None or security.is_default_anonymous:
        return ReadinessOutcome(
            outcome=OUTCOME_PASSED,
            detail="Anonymous session with no message security declared",
            check_name=check_name,
        )

    from helpers.connection_security import describe_connection_security, validate_connection_security

    summary = describe_connection_security(security)
    issues = validate_connection_security(security, env=env)
    if not allow_prompt and security.auth_source == "prompt":
        issues.append(
            "authentication.source is 'prompt' but this run is unattended. Run with --interactive-prompts, "
            "or use the 'file'/'environment' credential source."
        )
    if issues:
        return ReadinessOutcome(
            outcome=OUTCOME_CONFIGURATION_ERROR,
            reason_code="configuration_invalid",
            detail=f"Declared connection security cannot be applied ({summary}): " + "; ".join(issues),
            check_name=check_name,
            evidence={"issues": issues},
        )
    return ReadinessOutcome(
        outcome=OUTCOME_PASSED,
        detail=f"Connection security is applicable ({summary})",
        check_name=check_name,
    )


def check_endpoint_configured(endpoint: str) -> ReadinessOutcome:
    """Check that the profile has a non-empty, non-placeholder endpoint."""
    check_name = "endpoint_configured"
    if not endpoint or endpoint == "opc.tcp://<host>:40451" or "<" in endpoint:
        return ReadinessOutcome(
            outcome=OUTCOME_CONFIGURATION_ERROR,
            reason_code="configuration_invalid",
            detail=(
                "Profile endpoint is not set or is still the placeholder value. "
                "Set 'target.endpoint' to the real target_server URL."
            ),
            check_name=check_name,
        )
    return ReadinessOutcome(
        outcome=OUTCOME_PASSED,
        detail=f"Endpoint configured: {endpoint}",
        check_name=check_name,
    )


def check_result_trigger_mode(profile: TargetServerCuProfile) -> ReadinessOutcome:
    """Check that the result trigger mode is compatible with CU evidence needs.

    Returns manual_required when the profile uses manual_trigger mode.
    Returns blocked when mode is 'none' and no fallback is declared.
    """
    check_name = "result_trigger_mode"
    mode = profile.triggers.result.mode
    if mode == "none":
        return ReadinessOutcome(
            outcome=OUTCOME_BLOCKED,
            reason_code=REASON_MISSING_RUNTIME_PRECONDITION,
            detail=(
                "Result trigger mode is 'none'. Result-producing CUs will be blocked. "
                "Set triggers.result.mode to 'simulate_methods', 'start_selected_joining', "
                "or 'manual_trigger'."
            ),
            check_name=check_name,
        )
    if mode == "manual_trigger":
        return ReadinessOutcome(
            outcome=OUTCOME_MANUAL_REQUIRED,
            reason_code=REASON_MANUAL_TRIGGER_REQUIRED,
            detail=(
                "Result trigger mode is 'manual_trigger'. "
                "An operator must physically trigger the joining tool to produce results."
            ),
            check_name=check_name,
        )
    return ReadinessOutcome(
        outcome=OUTCOME_PASSED,
        detail=f"Result trigger mode: {mode}",
        check_name=check_name,
    )


def check_state_changing_methods_policy(
    profile: TargetServerCuProfile, required_methods: list[str]
) -> ReadinessOutcome:
    """Check whether all required state-changing methods are allowed by YAML policy.

    Parameters
    ----------
    profile:
        Loaded target_server profile.
    required_methods:
        State-changing OPC UA methods that must be allowed for the planned run.
    """
    check_name = "state_changing_methods_policy"
    blocked_methods = [
        m for m in required_methods if not profile.cu_execution.state_changing_methods.allow_state_changing_method(m)
    ]
    if blocked_methods:
        return ReadinessOutcome(
            outcome=OUTCOME_BLOCKED,
            reason_code=REASON_UNSAFE_METHOD_NOT_ENABLED,
            detail=(
                f"State-changing method(s) not allowed by profile: {blocked_methods}. "
                "Add them to cu_execution.state_changing_methods.allowed_methods or "
                "set default_policy to 'allow_all'."
            ),
            check_name=check_name,
            evidence={"blocked_methods": blocked_methods},
        )
    return ReadinessOutcome(
        outcome=OUTCOME_PASSED,
        detail=f"All required state-changing methods allowed: {required_methods}",
        check_name=check_name,
    )


def check_tool_piu_configured(profile: TargetServerCuProfile) -> ReadinessOutcome:
    """Check whether a tool ProductInstanceUri is available for workflow execution.

    When the profile provides an explicit PIU, returns passed immediately
    (runtime checks will verify it later).  When selection_policy is first_ready
    or first_available, returns a soft PASSED (runtime discovery is required).
    When exact_match is requested with no PIU, returns a configuration_error.
    """
    check_name = "tool_piu_configured"
    tool = profile.selection.tool
    if tool.product_instance_uri:
        return ReadinessOutcome(
            outcome=OUTCOME_PASSED,
            detail=f"Tool PIU configured: {tool.product_instance_uri}",
            check_name=check_name,
            evidence={"product_instance_uri": tool.product_instance_uri},
        )
    if tool.policy == "exact_match":
        return ReadinessOutcome(
            outcome=OUTCOME_CONFIGURATION_ERROR,
            reason_code="configuration_invalid",
            detail=(
                "selection.tool.policy is 'exact_match' but no product_instance_uri is configured. "
                "Either provide a PIU or change the policy to 'first_ready'."
            ),
            check_name=check_name,
        )
    return ReadinessOutcome(
        outcome=OUTCOME_PASSED,
        detail=f"Tool PIU will be discovered at runtime (policy={tool.policy})",
        check_name=check_name,
    )


def check_joining_process_configured(profile: TargetServerCuProfile) -> ReadinessOutcome:
    """Check whether a joining process is configured for workflow execution."""
    check_name = "joining_process_configured"
    jp = profile.selection.joining_process
    configured_identifiers = {
        "joining_process_id": jp.joining_process_id,
        "joining_process_origin_id": jp.joining_process_origin_id,
        "selection_name": jp.selection_name,
    }
    configured_identifiers = {key: value for key, value in configured_identifiers.items() if value}
    if configured_identifiers:
        return ReadinessOutcome(
            outcome=OUTCOME_PASSED,
            detail="Joining process exact-match selector configured: "
            + ", ".join(f"{key}={value}" for key, value in configured_identifiers.items()),
            check_name=check_name,
            evidence=configured_identifiers,
        )
    if jp.policy == "exact_match":
        return ReadinessOutcome(
            outcome=OUTCOME_CONFIGURATION_ERROR,
            reason_code="configuration_invalid",
            detail=(
                "selection.joining_process.policy is 'exact_match' but no process ID, origin ID, "
                "or SelectionName is configured. Provide at least one selector or change the policy."
            ),
            check_name=check_name,
        )
    if jp.policy in {"first_compatible", "first_available"}:
        return ReadinessOutcome(
            outcome=OUTCOME_PASSED,
            detail=f"Joining process will be selected at runtime (policy={jp.policy})",
            check_name=check_name,
        )
    return ReadinessOutcome(
        outcome=OUTCOME_PASSED,
        detail=f"Joining process selection policy: {jp.policy}",
        check_name=check_name,
    )


def check_start_selected_joining_methods_allowed(profile: TargetServerCuProfile) -> ReadinessOutcome:
    """Check that SelectJoiningProcess and StartSelectedJoining are allowed when mode is start_selected_joining."""
    check_name = "start_selected_joining_allowed"
    if profile.triggers.result.mode != "start_selected_joining":
        return ReadinessOutcome(
            outcome=OUTCOME_PASSED,
            detail="Result trigger mode is not start_selected_joining — no workflow method check needed",
            check_name=check_name,
        )
    required = ["SelectJoiningProcess", "StartSelectedJoining"]
    return check_state_changing_methods_policy(profile, required)


# ---------------------------------------------------------------------------
# Runtime readiness checks (async, require OPC UA connection)
# ---------------------------------------------------------------------------


async def check_joining_system_present(client: Any, joining_system_node: Any | None) -> ReadinessOutcome:
    """Check whether a JoiningSystem object was discovered in the address space."""
    check_name = "joining_system_present"
    if joining_system_node is None:
        return ReadinessOutcome(
            outcome=OUTCOME_BLOCKED,
            reason_code=REASON_JOINING_SYSTEM_NOT_FOUND,
            detail=(
                "No JoiningSystem node found in the server address space. "
                "Verify that the server exposes a JoiningSystemType instance."
            ),
            check_name=check_name,
        )
    try:
        node_id = joining_system_node.nodeid
        return ReadinessOutcome(
            outcome=OUTCOME_PASSED,
            detail=f"JoiningSystem found: {node_id}",
            check_name=check_name,
            evidence={"joining_system_node_id": str(node_id)},
        )
    except Exception as exc:  # noqa: BLE001
        return ReadinessOutcome(
            outcome=OUTCOME_BLOCKED,
            reason_code=REASON_JOINING_SYSTEM_NOT_FOUND,
            detail=f"JoiningSystem node id not readable: {exc}",
            check_name=check_name,
        )


async def check_namespaces_available(client: Any, required_uris: list[str]) -> ReadinessOutcome:
    """Check that required OPC UA namespaces are registered on the server.

    Parameters
    ----------
    client:
        Active asyncua Client instance.
    required_uris:
        Namespace URIs that must be present.
    """
    check_name = "namespaces_available"
    try:
        ns_array = await client.get_namespace_array()
        missing = [uri for uri in required_uris if uri not in ns_array]
        if missing:
            return ReadinessOutcome(
                outcome=OUTCOME_BLOCKED,
                reason_code=REASON_NAMESPACE_UNAVAILABLE,
                detail=f"Required namespaces missing from server: {missing}",
                check_name=check_name,
                evidence={"missing_namespaces": missing, "server_namespaces": ns_array},
            )
        return ReadinessOutcome(
            outcome=OUTCOME_PASSED,
            detail=f"All {len(required_uris)} required namespace(s) present",
            check_name=check_name,
            evidence={"server_namespace_count": len(ns_array)},
        )
    except Exception as exc:  # noqa: BLE001
        return ReadinessOutcome(
            outcome=OUTCOME_FAILED,
            reason_code=REASON_TARGET_SERVER_NOT_READY,
            detail=f"Cannot read server namespace array: {exc}",
            check_name=check_name,
        )


async def check_joining_process_list(
    joining_system_node: Any,
    product_instance_uri: str,
    ns_app: int,
) -> ReadinessOutcome:
    """Check whether GetJoiningProcessList returns at least one entry.

    Parameters
    ----------
    joining_system_node:
        The JoiningSystem OPC UA Node.
    product_instance_uri:
        PIU to pass to GetJoiningProcessList (empty string for target_server-level call).
    ns_app:
        Application namespace index.
    """
    check_name = "joining_process_list"
    from helpers.namespaces import BN
    from helpers.node_discovery import find_child_by_browse_name

    try:
        jpm_node = await find_child_by_browse_name(joining_system_node, BN.JOINING_PROCESS_MANAGEMENT, ns_app)
        if jpm_node is None:
            return ReadinessOutcome(
                outcome=OUTCOME_BLOCKED,
                reason_code=REASON_NO_PROCESS_CONFIGURED,
                detail="JoiningProcessManagement node not found under JoiningSystem",
                check_name=check_name,
            )

        from asyncua import ua

        from helpers.method_caller import find_and_call_method

        result = await find_and_call_method(
            jpm_node,
            BN.GET_JOINING_PROCESS_LIST,
            ns_app,
            ua.Variant(product_instance_uri, ua.VariantType.String),
        )
        if not result.success:
            return ReadinessOutcome(
                outcome=OUTCOME_BLOCKED,
                reason_code=REASON_NO_PROCESS_CONFIGURED,
                detail=f"GetJoiningProcessList failed: {result.error}",
                check_name=check_name,
            )
        process_list = result.output_list
        if not process_list or (len(process_list) == 1 and not process_list[0]):
            return ReadinessOutcome(
                outcome=OUTCOME_BLOCKED,
                reason_code=REASON_NO_PROCESS_CONFIGURED,
                detail="GetJoiningProcessList returned an empty list — no processes configured",
                check_name=check_name,
                evidence={"process_count": 0},
            )
        count = len(process_list[0]) if isinstance(process_list[0], (list, tuple)) else len(process_list)
        return ReadinessOutcome(
            outcome=OUTCOME_PASSED,
            detail=f"GetJoiningProcessList returned {count} process(es)",
            check_name=check_name,
            evidence={"process_count": count},
        )
    except Exception as exc:  # noqa: BLE001
        return ReadinessOutcome(
            outcome=OUTCOME_BLOCKED,
            reason_code=REASON_TARGET_SERVER_NOT_READY,
            detail=f"Unexpected error during joining process list check: {exc}",
            check_name=check_name,
        )


# ---------------------------------------------------------------------------
# Composite preflight — run all config-level checks synchronously
# ---------------------------------------------------------------------------


def run_config_preflight(
    profile: TargetServerCuProfile,
    *,
    security: ConnectionSecurity | None = None,
    env: Mapping[str, str] | None = None,
    allow_prompt: bool = True,
) -> PreflightReport:
    """Run all synchronous (no-network) configuration checks for a profile.

    Returns a PreflightReport with the results.  This can be called before
    any OPC UA connection is opened to detect configuration errors early.

    Parameters
    ----------
    profile:
        The loaded target_server profile to check.
    security:
        Declared connection security. Resolved from the profile's SUT manifest
        when omitted; pass it explicitly to check a specific declaration.
    env:
        Environment mapping used to resolve referenced secrets. Defaults to
        ``os.environ``.
    allow_prompt:
        False for unattended runs, where an interactive credential source is a
        configuration error rather than a console prompt.
    """
    report = PreflightReport(
        profile_name=profile.profile_name,
        endpoint=profile.target.endpoint,
    )

    # 1. Endpoint must be configured and not a placeholder
    report.add(check_endpoint_configured(profile.target.endpoint))

    # 2. Result trigger mode must be usable
    report.add(check_result_trigger_mode(profile))

    # 3. Tool selection config must be consistent
    report.add(check_tool_piu_configured(profile))

    # 4. Joining process selection config must be consistent
    report.add(check_joining_process_configured(profile))

    # 5. StartSelectedJoining requires explicit opt-in when mode demands it
    report.add(check_start_selected_joining_methods_allowed(profile))

    # 6. Declared session security/authentication must be appliable
    resolved_security = security if security is not None else resolve_profile_connection_security(profile)
    report.add(check_connection_security(resolved_security, env=env, allow_prompt=allow_prompt))

    return report


def classify_preflight_outcome(profile: TargetServerCuProfile) -> ReadinessOutcome:
    """Return a single top-level ReadinessOutcome for the config-level preflight.

    Convenience wrapper over run_config_preflight for callers that only need
    a go/no-go decision.  The first blocking or configuration_error check is
    returned; if all pass, returns OUTCOME_PASSED.
    """
    report = run_config_preflight(profile)
    for check in report.checks:
        if check.is_blocking:
            return check
    # Aggregate manual_required as a non-blocking advisory
    manual_checks = report.manual_required_checks
    if manual_checks:
        return manual_checks[0]
    return ReadinessOutcome(
        outcome=OUTCOME_PASSED,
        detail="All configuration preflight checks passed",
        check_name="config_preflight",
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _parse_endpoint(endpoint: str) -> tuple[str, int]:
    """Return (host, port) from an OPC UA endpoint URL."""
    try:
        from urllib.parse import urlparse

        parsed = urlparse(endpoint)
        return parsed.hostname or "", parsed.port or 4840
    except Exception:  # noqa: BLE001
        return "", 4840
