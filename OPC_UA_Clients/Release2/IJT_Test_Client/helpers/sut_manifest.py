"""
SUT manifest - the one versioned tester-facing schema (``*.sut.yaml``).

One file describes one System Under Test (SUT): how to reach it, how to
authenticate, what it claims to support, which workflows are approved, how it
may be triggered, which risky operations were approved, its timeout budgets,
its scoring strictness, and its reporting/redaction settings.

This replaces the old paired ``*.profile.yaml`` + ``*.capabilities.yaml``
model. There is exactly one schema and one runtime input file.

Design rules
------------
* **Schema metadata is authoritative.** :data:`MANIFEST_SCHEMA` describes every
  field once (type, default, choices, description, placeholder/secret rules).
  Parsing, the commented YAML template, the Markdown field reference, and the
  built-in presets are all derived from it, so they cannot drift apart.
* **No secrets.** A reusable manifest may reference credentials (a local file,
  or environment variable names) but must never contain a literal secret.
  :func:`load_sut_manifest` rejects known secret keys and inline passwords.
* **Claims are authoritative.** The CU claims in the manifest define the scope
  that is scored. Discovery observations never silently mutate them.
* **Strict claimed scope by default.** ``scoring.mode`` defaults to
  ``strict_profile`` (strict claimed scope) with ``claimed_scope_only: true``.
* **Placeholders fail fast for live runs.** The committed template uses
  ``<...>`` placeholders in its *operational* fields. :func:`validate_live_ready`
  reports them, and an ``external`` lifecycle run must not proceed while any
  remain. Descriptive prose (``name``, ``description``) is never scanned, so
  documenting the word ``<placeholder>`` cannot block a filled-in manifest.

Public API (stable for the next workstream)::

    from helpers.sut_manifest import (
        load_sut_manifest,        # load + validate one *.sut.yaml
        parse_sut_manifest,       # validate an already-parsed mapping
        validate_live_ready,      # placeholder / live-readiness issues
        render_manifest_yaml,     # generate a fully commented manifest
        render_field_reference,   # generate the Markdown field reference
        preset_names, build_preset,
        SutManifest, SutManifestError, LegacyPairedFileError,
    )
"""

from __future__ import annotations

import copy
import functools
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

import yaml

from helpers.target_server_cu_config import (
    VALID_CLEANUP_POLICIES,
    VALID_CONDITION_TRIGGER_MODES,
    VALID_EVENT_TRIGGER_MODES,
    VALID_EXECUTION_MODES,
    VALID_PRECONDITION_POLICIES,
    VALID_RESULT_CLASSIFICATIONS,
    VALID_RESULT_TRIGGER_MODES,
    VALID_SCORING_MODES,
    VALID_SELECTION_POLICIES,
    VALID_START_INVOCATION_POLICIES,
    VALID_STATE_CHANGING_POLICIES,
    TargetServerConfigError,
    TargetServerCuProfile,
    build_execution_profile,
)

logger = logging.getLogger(__name__)

MANIFEST_SUFFIX = ".sut.yaml"
SUPPORTED_MANIFEST_SCHEMA_VERSIONS: frozenset[int] = frozenset({1})
CURRENT_MANIFEST_SCHEMA_VERSION = 1

VALID_LIFECYCLE_MODES: frozenset[str] = frozenset({"auto_simulator", "external"})
VALID_AUTH_SOURCES: frozenset[str] = frozenset({"anonymous", "prompt", "file", "environment"})
VALID_SECURITY_MODES: frozenset[str] = frozenset({"None", "Sign", "SignAndEncrypt"})
VALID_SECURITY_POLICIES: frozenset[str] = frozenset(
    {"None", "Basic256Sha256", "Aes128_Sha256_RsaOaep", "Aes256_Sha256_RsaPss"}
)
VALID_CLAIM_DISPOSITIONS: frozenset[str] = frozenset({"supported", "unsupported", "manual_required"})
VALID_ENABLE_ASSET_POLICIES: frozenset[str] = frozenset({"when_disabled", "always"})

#: Keys that must never appear anywhere in a reusable manifest.
FORBIDDEN_SECRET_KEYS: frozenset[str] = frozenset(
    {
        "password",
        "passwd",
        "pwd",
        "secret",
        "token",
        "api_key",
        "apikey",
        "access_key",
        "private_key",
        "private_key_password",
        "certificate_password",
        "client_secret",
        "credentials",
    }
)

_PLACEHOLDER_OPEN = "<"
_PLACEHOLDER_CLOSE = ">"
#: An unresolved placeholder is an ``<identifier>`` token: no whitespace and no
#: nested angle brackets. Prose such as "a < b and c > d" therefore never counts.
_PLACEHOLDER_TOKEN_RE = re.compile(r"<[^<>\s]+>")


class SutManifestError(ValueError):
    """Raised for a malformed, unsafe, or unsupported SUT manifest."""


class LegacyPairedFileError(SutManifestError):
    """Raised when a legacy ``*.profile.yaml`` / ``*.capabilities.yaml`` file is supplied."""


# ---------------------------------------------------------------------------
# Schema metadata - the single authoritative description of the manifest
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FieldSpec:
    """One manifest field: how it is validated, documented, and templated."""

    name: str
    kind: str  # str | bool | int | number | str_list | str_map | mapping
    description: str
    default: Any = None
    choices: frozenset[str] | None = None
    required: bool = False
    min_value: float | None = None
    value_choices: frozenset[str] | None = None  # for str_map values
    secret_reference: bool = False  # value names a secret, never holds one
    prose: bool = False  # free text for humans; never scanned for placeholders

    def default_value(self) -> Any:
        """Return a fresh copy of the declared default."""
        if self.default is None:
            return {"str": "", "bool": False, "int": 0, "number": 0.0}.get(self.kind, _empty_for(self.kind))
        return copy.deepcopy(self.default)


@dataclass(frozen=True)
class SectionSpec:
    """One manifest section (a YAML mapping) with its fields and subsections."""

    name: str
    description: str
    fields: tuple[FieldSpec, ...] = ()
    subsections: tuple["SectionSpec", ...] = ()


def _empty_for(kind: str) -> Any:
    if kind == "str_list":
        return []
    if kind in {"str_map", "mapping"}:
        return {}
    return ""


def _sorted_choices(choices: frozenset[str]) -> list[str]:
    return sorted(choices)


MANIFEST_SCHEMA: tuple[SectionSpec, ...] = (
    SectionSpec(
        name="",
        description="Identity of this System Under Test manifest.",
        fields=(
            FieldSpec(
                "schema_version",
                "int",
                "Manifest schema version. Must be 1 for this release.",
                default=CURRENT_MANIFEST_SCHEMA_VERSION,
                required=True,
                min_value=1,
            ),
            FieldSpec("name", "str", "Human-readable SUT name used in reports.", required=True, prose=True),
            FieldSpec("description", "str", "Short description of this SUT and its scope.", prose=True),
        ),
    ),
    SectionSpec(
        name="lifecycle",
        description="Who starts and stops the server under test.",
        fields=(
            FieldSpec(
                "mode",
                "str",
                "auto_simulator: the runner launches the built-in simulator. "
                "external: the SUT is started and owned outside this tool.",
                default="external",
                choices=VALID_LIFECYCLE_MODES,
                required=True,
            ),
            FieldSpec(
                "startup_timeout_seconds",
                "number",
                "How long to wait for an auto-launched simulator to accept connections.",
                default=60.0,
                min_value=1.0,
            ),
        ),
    ),
    SectionSpec(
        name="connection",
        description="Endpoint, security, and certificate material for the OPC UA session.",
        fields=(
            FieldSpec(
                "endpoint",
                "str",
                "OPC UA endpoint URL of the SUT. Required for external lifecycle runs.",
                default="",
            ),
            FieldSpec(
                "security_mode",
                "str",
                "OPC UA message security mode.",
                default="None",
                choices=VALID_SECURITY_MODES,
            ),
            FieldSpec(
                "security_policy",
                "str",
                "OPC UA security policy.",
                default="None",
                choices=VALID_SECURITY_POLICIES,
            ),
            FieldSpec("client_certificate_path", "str", "Path to the client application certificate (DER/PEM)."),
            FieldSpec(
                "client_private_key_path",
                "str",
                "Path to the client private key. Never inline key material here.",
                secret_reference=True,
            ),
            FieldSpec("server_certificate_path", "str", "Path to the expected server certificate, when pinned."),
            FieldSpec("trust_store_path", "str", "Directory holding trusted issuer/peer certificates."),
        ),
        subsections=(
            SectionSpec(
                name="expected_server",
                description="Optional server identity cross-check (warn-only by default).",
                fields=(
                    FieldSpec("application_name", "str", "Expected ApplicationName; empty disables the check."),
                    FieldSpec("application_version", "str", "Expected application version; empty disables the check."),
                    FieldSpec(
                        "warn_only_on_version_drift",
                        "bool",
                        "Warn instead of failing when the version differs.",
                        default=True,
                    ),
                ),
            ),
        ),
    ),
    SectionSpec(
        name="authentication",
        description=(
            "How the client obtains credentials. The manifest holds references only - "
            "never a literal password, token, or key."
        ),
        fields=(
            FieldSpec(
                "source",
                "str",
                "anonymous: no user identity. prompt: ask the operator at run time. "
                "file: read a local, git-ignored credentials file. "
                "environment: read environment/CI secret variables.",
                default="anonymous",
                choices=VALID_AUTH_SOURCES,
                required=True,
            ),
            FieldSpec("username", "str", "Non-secret user name. Leave empty for anonymous or prompt."),
            FieldSpec(
                "credentials_file",
                "str",
                "Path to a local credentials file (git-ignored). Required when source is 'file'.",
                secret_reference=True,
            ),
            FieldSpec(
                "username_env_var",
                "str",
                "Environment variable holding the user name. Used when source is 'environment'.",
                secret_reference=True,
            ),
            FieldSpec(
                "password_env_var",
                "str",
                "Environment variable holding the password. Required when source is 'environment'.",
                secret_reference=True,
            ),
        ),
    ),
    SectionSpec(
        name="capability_claims",
        description=(
            "Authoritative Conformance Unit (CU) claims for this SUT. These claims define the "
            "scored scope; discovery never silently changes them."
        ),
        fields=(
            FieldSpec(
                "active_profile",
                "str",
                "Base CU profile from profiles/ that this SUT claims.",
                default="full_specification_coverage",
            ),
            FieldSpec("supported_facets", "str_list", "Extra facet names claimed on top of the active profile."),
            FieldSpec(
                "cu_overrides",
                "str_map",
                "Per-CU claim overrides: supported, unsupported, or manual_required.",
                value_choices=VALID_CLAIM_DISPOSITIONS,
            ),
            FieldSpec(
                "claims_are_authoritative",
                "bool",
                "Keep true: manifest claims win over discovery observations.",
                default=True,
            ),
            FieldSpec(
                "allow_discovery_to_relax_claims",
                "bool",
                "Keep false: discovery must not silently downgrade a claim to unsupported.",
                default=False,
            ),
        ),
    ),
    SectionSpec(
        name="workflows",
        description="Selected and approved workflows, plus the tool/process selectors they use.",
        fields=(
            FieldSpec(
                "approved",
                "str_list",
                "Workflow names approved for this SUT (documentation and audit trail).",
            ),
            FieldSpec(
                "start_invocation_policy",
                "str",
                "How many start calls produce the required result evidence.",
                default="single_start_produces_final_result",
                choices=VALID_START_INVOCATION_POLICIES,
            ),
            FieldSpec(
                "expected_operation_count",
                "int",
                "Expected number of joining operations for batch/sync workflows.",
                default=1,
                min_value=1,
            ),
        ),
        subsections=(
            SectionSpec(
                name="tool_selector",
                description="How the Tool under test is discovered or pinned.",
                fields=(
                    FieldSpec(
                        "policy",
                        "str",
                        "Tool selection policy.",
                        default="first_ready",
                        choices=VALID_SELECTION_POLICIES,
                    ),
                    FieldSpec(
                        "product_instance_uri",
                        "str",
                        "Exact Tool ProductInstanceUri. Leave empty for runtime discovery. "
                        "Do not commit real serial numbers.",
                    ),
                    FieldSpec("capability_tags", "str_list", "Optional tags used to narrow tool selection."),
                ),
            ),
            SectionSpec(
                name="process_selector",
                description="Default joining-process selection for all result classifications.",
                fields=(
                    FieldSpec(
                        "policy",
                        "str",
                        "Joining process selection policy. first_ready: picks the first ready program automatically — good for simple controllers. exact_match: pin a specific joining_process_id for deterministic selection on controllers with many programs.",
                        default="first_compatible",
                        choices=VALID_SELECTION_POLICIES,
                    ),
                    FieldSpec("joining_process_id", "str", "Exact JoiningProcessId. Do not commit real IDs."),
                    FieldSpec(
                        "joining_process_origin_id",
                        "str",
                        "Stable fallback when a controller regenerates its primary process ID.",
                    ),
                    FieldSpec("selection_name", "str", "Final controller-specific selection fallback."),
                    FieldSpec("capability_tags", "str_list", "Optional tags used to narrow process selection."),
                ),
            ),
            SectionSpec(
                name="process_selectors_by_classification",
                description=(
                    "Optional per-classification process selectors (single, batch, job, sync ...). "
                    "Each entry uses the same fields as process_selector."
                ),
                fields=(),
            ),
            SectionSpec(
                name="expected_results",
                description="Result evidence this SUT is expected to produce.",
                fields=(
                    FieldSpec(
                        "classification",
                        "str",
                        "Primary/final result classification.",
                        default="single",
                        choices=VALID_RESULT_CLASSIFICATIONS,
                    ),
                    FieldSpec(
                        "intermediate_classifications",
                        "str_list",
                        "Result classifications emitted before or alongside the final result.",
                    ),
                    FieldSpec(
                        "final_result_required",
                        "bool",
                        "Require a final result before the workflow counts as complete.",
                        default=True,
                    ),
                ),
            ),
            SectionSpec(
                name="cleanup",
                description="What the runner restores after a workflow.",
                fields=(
                    FieldSpec(
                        "policy",
                        "str",
                        "Cleanup policy after the run.",
                        default="best_effort_with_evidence",
                        choices=VALID_CLEANUP_POLICIES,
                    ),
                    FieldSpec("deselect_process", "bool", "Deselect the joining process after the run.", default=True),
                    FieldSpec("reset_identifiers", "bool", "Reset identifiers after the run.", default=False),
                ),
            ),
        ),
    ),
    SectionSpec(
        name="triggers",
        description="How result, event, and condition evidence is produced on this SUT.",
        subsections=(
            SectionSpec(
                name="result",
                description="Result evidence trigger.",
                fields=(
                    FieldSpec(
                        "mode",
                        "str",
                        "Result trigger mode (simulator, remote start, manual operator, or passive).",
                        default="none",
                        choices=VALID_RESULT_TRIGGER_MODES,
                    ),
                    FieldSpec(
                        "deselect_after_joining",
                        "bool",
                        "Deselect the joining process after each joining operation.",
                        default=False,
                    ),
                ),
            ),
            SectionSpec(
                name="event",
                description="Event evidence trigger.",
                fields=(
                    FieldSpec(
                        "mode",
                        "str",
                        "Event trigger mode.",
                        default="observe_only",
                        choices=VALID_EVENT_TRIGGER_MODES,
                    ),
                ),
            ),
            SectionSpec(
                name="condition",
                description="Condition evidence trigger.",
                fields=(
                    FieldSpec(
                        "mode",
                        "str",
                        "Condition trigger mode.",
                        default="observe_only",
                        choices=VALID_CONDITION_TRIGGER_MODES,
                    ),
                ),
            ),
        ),
    ),
    SectionSpec(
        name="execution_policy",
        description="State/method execution policy and the risk approvals that back it.",
        fields=(
            FieldSpec(
                "default_mode",
                "str",
                "Execution mode for this SUT.",
                default="automated",
                choices=VALID_EXECUTION_MODES,
            ),
            FieldSpec("allow_manual_steps", "bool", "Allow operator prompts and waits.", default=False),
            FieldSpec(
                "precondition_failure_policy",
                "str",
                "What to do when a claimed CU's runtime preconditions are missing.",
                default="blocked",
                choices=VALID_PRECONDITION_POLICIES,
            ),
            FieldSpec(
                "method_status_policies",
                "str_map",
                "Per-method status classification overrides (method BrowseName -> accepted|warning|fail).",
            ),
        ),
        subsections=(
            SectionSpec(
                name="state_changing_methods",
                description="Which state-changing OPC UA methods may be called on this SUT.",
                fields=(
                    FieldSpec(
                        "default_policy",
                        "str",
                        "Safety default for state-changing method calls.",
                        default="require_explicit_opt_in",
                        choices=VALID_STATE_CHANGING_POLICIES,
                    ),
                    FieldSpec(
                        "allowed_methods",
                        "str_list",
                        "Safety permissions only: methods explicitly approved for this SUT. "
                        "This list never creates or enables tests.",
                    ),
                ),
            ),
            SectionSpec(
                name="risk_approvals",
                description="Explicit approvals for operations that change or disturb the SUT.",
                fields=(
                    FieldSpec(
                        "allow_disable_asset",
                        "bool",
                        "Allow EnableAsset(false) on a real tool. Tests always restore true.",
                        default=False,
                    ),
                    FieldSpec(
                        "enable_asset_policy",
                        "str",
                        "when_disabled: only re-enable when found disabled. always: reassert before every workflow.",
                        default="when_disabled",
                        choices=VALID_ENABLE_ASSET_POLICIES,
                    ),
                    FieldSpec(
                        "allow_destructive_methods",
                        "bool",
                        "Allow abort/reset style methods that disturb production state.",
                        default=False,
                    ),
                    FieldSpec("approved_by", "str", "Who approved these risk settings (name or role)."),
                    FieldSpec("approval_reference", "str", "Change request, ticket, or document reference."),
                ),
            ),
            SectionSpec(
                name="intervention",
                description="Method used to generate InterventionResult evidence, when applicable.",
                fields=(
                    FieldSpec(
                        "method",
                        "str",
                        "Intervention method BrowseName. Must also appear in allowed_methods.",
                        default="",
                    ),
                    FieldSpec("count", "int", "Counter value for counter-style intervention methods.", default=1),
                    FieldSpec("message", "str", "Message recorded with the intervention.", default=""),
                ),
                subsections=(
                    SectionSpec(
                        name="parent_process",
                        description=(
                            "Parent batch/job process some controllers require before counter or abort methods. "
                            "Any one selector is enough."
                        ),
                        fields=(
                            FieldSpec("joining_process_id", "str", "Parent process ID."),
                            FieldSpec("joining_process_origin_id", "str", "Parent process origin ID."),
                            FieldSpec("selection_name", "str", "Parent process selection name."),
                        ),
                    ),
                ),
            ),
        ),
    ),
    SectionSpec(
        name="timeouts",
        description=(
            "Separated time budgets. Passive observation, active result completion, whole-workflow, "
            "and operator budgets are independent so one slow phase cannot mask another."
        ),
        fields=(
            FieldSpec(
                "passive_observation_seconds",
                "number",
                "Budget for evidence the client did not trigger itself (observe_only).",
                default=5.0,
                min_value=1.0,
            ),
            FieldSpec(
                "active_result_seconds",
                "number",
                "Budget for result completion after the client started a joining operation.",
                default=60.0,
                min_value=1.0,
            ),
            FieldSpec(
                "workflow_seconds",
                "number",
                "Budget for a complete workflow, including setup and cleanup.",
                default=120.0,
                min_value=1.0,
            ),
            FieldSpec(
                "operator_seconds",
                "number",
                "Budget for a physical operator action (manual trigger modes).",
                default=300.0,
                min_value=1.0,
            ),
            FieldSpec(
                "method_call_seconds",
                "number",
                "Budget for a single OPC UA method call or read.",
                default=15.0,
                min_value=1.0,
            ),
        ),
    ),
    SectionSpec(
        name="scoring",
        description="How the run is scored. Strict claimed scope is the default.",
        fields=(
            FieldSpec(
                "mode",
                "str",
                "strict_profile: strict claimed scope (default). diagnostic: report everything, no gate. "
                "acceptance: zero failed CUs and zero claim mismatches in claimed scope.",
                default="strict_profile",
                choices=VALID_SCORING_MODES,
            ),
            FieldSpec(
                "claimed_scope_only",
                "bool",
                "Keep true: score only what this manifest claims; unclaimed gaps stay informational.",
                default=True,
            ),
        ),
    ),
    SectionSpec(
        name="reporting",
        description="Report output location and redaction settings.",
        fields=(
            FieldSpec(
                "output_dir",
                "str",
                "Directory for evidence reports, relative to the runner root or absolute.",
                default="test-results/target-server-cu",
            ),
            FieldSpec(
                "sanitize_shared_artifacts",
                "bool",
                "Redact hostnames, serial numbers, PIUs, and process IDs in shared artifacts.",
                default=True,
            ),
            FieldSpec(
                "keep_local_exact_debug_artifacts",
                "bool",
                "Keep unredacted local debug artifacts. Keep false for shared or committed runs.",
                default=False,
            ),
            FieldSpec(
                "redact_fields",
                "str_list",
                "Extra field names to redact in shared artifacts.",
                default=["endpoint", "product_instance_uri", "joining_process_id", "serial_number"],
            ),
        ),
    ),
)


def iter_field_specs(
    schema: Sequence[SectionSpec] = MANIFEST_SCHEMA, prefix: str = ""
) -> Iterator[tuple[str, FieldSpec]]:
    """Yield ``(dotted_path, FieldSpec)`` for every field in *schema*."""
    for section in schema:
        section_path = f"{prefix}{section.name}." if section.name else prefix
        for spec in section.fields:
            yield f"{section_path}{spec.name}", spec
        yield from iter_field_specs(section.subsections, section_path)


# ---------------------------------------------------------------------------
# Generic, schema-driven validation
# ---------------------------------------------------------------------------


def _validate_scalar(value: Any, spec: FieldSpec, path: str) -> Any:
    if spec.kind == "str":
        if not isinstance(value, str):
            raise SutManifestError(f"{path}: must be a string, got {type(value).__name__}")
        if spec.choices is not None and value not in spec.choices:
            raise SutManifestError(f"{path}: invalid value '{value}'. Valid values: {_sorted_choices(spec.choices)}")
        return value
    if spec.kind == "bool":
        if not isinstance(value, bool):
            raise SutManifestError(f"{path}: must be a boolean, got {type(value).__name__}")
        return value
    if spec.kind == "int":
        if not isinstance(value, int) or isinstance(value, bool):
            raise SutManifestError(f"{path}: must be an integer, got {type(value).__name__}")
        if spec.min_value is not None and value < spec.min_value:
            raise SutManifestError(f"{path}: must be >= {int(spec.min_value)}, got {value}")
        return value
    if spec.kind == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise SutManifestError(f"{path}: must be a number, got {type(value).__name__}")
        number = float(value)
        if spec.min_value is not None and number < spec.min_value:
            raise SutManifestError(f"{path}: must be >= {spec.min_value}, got {number}")
        return number
    if spec.kind == "str_list":
        if not isinstance(value, list):
            raise SutManifestError(f"{path}: must be a list, got {type(value).__name__}")
        for index, item in enumerate(value):
            if not isinstance(item, str):
                raise SutManifestError(f"{path}[{index}]: must be a string, got {type(item).__name__}")
        return list(value)
    if spec.kind == "str_map":
        if not isinstance(value, dict):
            raise SutManifestError(f"{path}: must be a mapping, got {type(value).__name__}")
        for key, item in value.items():
            if not isinstance(key, str) or not isinstance(item, str):
                raise SutManifestError(f"{path}: must map string keys to string values")
            if spec.value_choices is not None and item not in spec.value_choices:
                raise SutManifestError(
                    f"{path}.{key}: invalid value '{item}'. Valid values: {_sorted_choices(spec.value_choices)}"
                )
        return dict(value)
    raise SutManifestError(f"{path}: unsupported field kind '{spec.kind}'")  # pragma: no cover - guard


def _validate_section(
    raw: Any,
    section: SectionSpec,
    prefix: str,
    *,
    extra_known: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    section_path = f"{prefix}{section.name}" if section.name else prefix.rstrip(".")
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise SutManifestError(f"{section_path or 'manifest'}: must be a mapping, got {type(raw).__name__}")

    known = {spec.name for spec in section.fields} | {sub.name for sub in section.subsections} | set(extra_known)
    if section.name != "process_selectors_by_classification":
        unknown = sorted(set(raw) - known)
        if unknown:
            raise SutManifestError(
                f"{section_path or 'manifest'}: unknown field(s) {unknown}. "
                f"Known fields: {sorted(known)}. Run scripts/generate_sut_manifest_docs.py for the reference."
            )

    result: dict[str, Any] = {}
    dotted = f"{section_path}." if section_path else ""
    for spec in section.fields:
        if spec.name in raw:
            result[spec.name] = _validate_scalar(raw[spec.name], spec, f"{dotted}{spec.name}")
        elif spec.required:
            raise SutManifestError(f"{dotted}{spec.name}: required field is missing")
        else:
            result[spec.name] = spec.default_value()

    for sub in section.subsections:
        result[sub.name] = _validate_section(raw.get(sub.name), sub, dotted)
    return result


def _validate_process_selectors(raw: Any) -> dict[str, dict[str, Any]]:
    """Validate the free-keyed per-classification selector mapping.

    The enclosing section validation has already established that *raw* is a
    mapping (or absent); this adds the per-classification key rules.
    """
    if raw is None:
        raw = {}
    selector_spec = _find_section(("workflows", "process_selector"))
    selectors: dict[str, dict[str, Any]] = {}
    for key, value in raw.items():
        if not isinstance(key, str):
            raise SutManifestError("workflows.process_selectors_by_classification: keys must be strings")
        normalized = key.lower().strip()
        if normalized not in VALID_RESULT_CLASSIFICATIONS:
            raise SutManifestError(
                f"workflows.process_selectors_by_classification.{key}: unknown classification. "
                f"Valid values: {_sorted_choices(VALID_RESULT_CLASSIFICATIONS)}"
            )
        selectors[normalized] = _validate_section(
            value, selector_spec, f"workflows.process_selectors_by_classification.{key}."
        )
    return selectors


def _find_section(path: Sequence[str]) -> SectionSpec:
    sections: Sequence[SectionSpec] = MANIFEST_SCHEMA
    found: SectionSpec | None = None
    for name in path:
        found = next((section for section in sections if section.name == name), None)
        if found is None:  # pragma: no cover - schema is static
            raise SutManifestError(f"Unknown schema section: {'.'.join(path)}")
        sections = found.subsections
    if found is None:  # pragma: no cover - schema is static
        raise SutManifestError("Empty schema section path")
    return found


# ---------------------------------------------------------------------------
# Secret and placeholder guards
# ---------------------------------------------------------------------------


def _walk_raw(node: Any, path: str = "") -> Iterator[tuple[str, Any]]:
    if isinstance(node, dict):
        for key, value in node.items():
            child = f"{path}.{key}" if path else str(key)
            yield child, value
            yield from _walk_raw(value, child)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            child = f"{path}[{index}]"
            yield child, value
            yield from _walk_raw(value, child)


def reject_secret_values(raw: Mapping[str, Any]) -> None:
    """Raise :class:`SutManifestError` when *raw* contains a secret-bearing key.

    A reusable manifest may reference a secret (a local file path or an
    environment variable name) but must never carry the value itself.
    """
    for path, value in _walk_raw(dict(raw)):
        leaf = path.split(".")[-1].split("[")[0].lower()
        if leaf in FORBIDDEN_SECRET_KEYS:
            raise SutManifestError(
                f"{path}: manifests must never contain secret values. "
                f"Use authentication.credentials_file or authentication.password_env_var to reference a secret instead."
            )
        if isinstance(value, str) and leaf.endswith("_password"):
            raise SutManifestError(f"{path}: inline passwords are not allowed in a SUT manifest")


def _is_placeholder(value: Any) -> bool:
    """Return True when *value* contains an unresolved ``<placeholder>`` token.

    Deliberately strict: only an ``<identifier>`` token counts, so ordinary text
    containing ``<`` and ``>`` (comparisons, XML-ish snippets, arrows) is not
    mistaken for an unreplaced value. Prose fields are excluded from scanning
    altogether by :func:`operational_placeholder_issues`.
    """
    return isinstance(value, str) and _PLACEHOLDER_TOKEN_RE.search(value) is not None


def prose_field_paths() -> frozenset[str]:
    """Return the dotted paths of every free-text (prose) manifest field."""
    return frozenset(path for path, spec in iter_field_specs() if spec.prose)


def _is_prose_path(path: str, prose_paths: frozenset[str]) -> bool:
    """Return True when *path* (or its parent list entry) is a prose field."""
    return path.split("[")[0] in prose_paths


def operational_placeholder_issues(data: Mapping[str, Any]) -> list[str]:
    """Return one issue per unresolved placeholder in an *operational* field.

    Descriptive prose (``name``, ``description``) is never scanned: documenting
    that a copy must "replace every <placeholder>" is not itself an unresolved
    value, and flagging it would make every generated example permanently
    non-live-ready for the wrong reason.
    """
    prose_paths = prose_field_paths()
    return [
        f"{path}: replace the placeholder '{value}'"
        for path, value in _walk_raw(dict(data))
        if _is_placeholder(value) and not _is_prose_path(path, prose_paths)
    ]


# ---------------------------------------------------------------------------
# Typed manifest model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CapabilityClaims:
    """Authoritative CU claims declared by a SUT manifest.

    Facet/profile resolution lives in :mod:`helpers.profile_loader`; this type
    only carries the claim data so it has exactly one definition.
    """

    active_profile: str = "full_specification_coverage"
    supported_facets: tuple[str, ...] = ()
    cu_overrides: Mapping[str, str] = field(default_factory=dict)
    claims_are_authoritative: bool = True
    allow_discovery_to_relax_claims: bool = False


@dataclass(frozen=True)
class AuthenticationConfig:
    """Credential *references* for the SUT session - never credential values."""

    source: str = "anonymous"
    username: str = ""
    credentials_file: str = ""
    username_env_var: str = ""
    password_env_var: str = ""

    @property
    def requires_operator_prompt(self) -> bool:
        """True when the operator must supply credentials interactively."""
        return self.source == "prompt"

    def missing_references(self) -> list[str]:
        """Return the reference fields this auth source needs but does not have."""
        if self.source == "file" and not self.credentials_file:
            return ["authentication.credentials_file"]
        if self.source == "environment" and not self.password_env_var:
            return ["authentication.password_env_var"]
        return []

    def unresolved_environment_vars(self, env: Mapping[str, str] | None = None) -> list[str]:
        """Return referenced environment variables that are not set."""
        if self.source != "environment":
            return []
        environ = os.environ if env is None else env
        names = [name for name in (self.username_env_var, self.password_env_var) if name]
        return [name for name in names if name not in environ]


@dataclass(frozen=True)
class TimeoutBudgets:
    """Separated timeout budgets so one phase cannot mask another."""

    passive_observation_seconds: float = 5.0
    active_result_seconds: float = 60.0
    workflow_seconds: float = 120.0
    operator_seconds: float = 300.0
    method_call_seconds: float = 15.0

    def result_trigger_seconds(self, trigger_mode: str) -> float:
        """Return the budget that applies to *trigger_mode* result evidence.

        This is the *passive* observation budget for every automated mode: a
        result the client started itself is completed within
        :attr:`active_result_seconds` instead. Only a manual trigger waits on
        the operator budget.
        """
        if trigger_mode == "manual_trigger":
            return self.operator_seconds
        return self.passive_observation_seconds


@dataclass(frozen=True)
class RiskApprovals:
    """Explicit approvals for operations that change or disturb the SUT."""

    allow_disable_asset: bool = False
    enable_asset_policy: str = "when_disabled"
    allow_destructive_methods: bool = False
    approved_by: str = ""
    approval_reference: str = ""

    @property
    def has_elevated_risk(self) -> bool:
        """True when any approval beyond the safe default is enabled."""
        return self.allow_disable_asset or self.allow_destructive_methods


@dataclass(frozen=True)
class SutManifest:
    """One validated SUT manifest - the single runtime input file."""

    schema_version: int
    name: str
    description: str
    lifecycle_mode: str
    startup_timeout_seconds: float
    authentication: AuthenticationConfig
    capability_claims: CapabilityClaims
    timeouts: TimeoutBudgets
    risk_approvals: RiskApprovals
    scoring_mode: str
    claimed_scope_only: bool
    approved_workflows: tuple[str, ...]
    redact_fields: tuple[str, ...]
    source_path: str
    data: Mapping[str, Any]

    # -- derived views ----------------------------------------------------

    @property
    def endpoint(self) -> str:
        """Return the configured OPC UA endpoint."""
        return str(self.data["connection"]["endpoint"])

    @property
    def is_auto_simulator(self) -> bool:
        """True when the runner owns the server lifecycle."""
        return self.lifecycle_mode == "auto_simulator"

    @property
    def result_trigger_mode(self) -> str:
        """Return the configured result trigger mode."""
        return str(self.data["triggers"]["result"]["mode"])

    def to_execution_profile(self) -> TargetServerCuProfile:
        """Build the internal typed execution profile used by the run path."""
        return build_execution_profile(self._execution_sections(), source_path=self.source_path)

    def to_dict(self) -> dict[str, Any]:
        """Return the validated manifest as a plain nested dict."""
        return copy.deepcopy(dict(self.data))

    # -- internals --------------------------------------------------------

    def _execution_sections(self) -> dict[str, Any]:
        data = self.data
        workflows = data["workflows"]
        triggers = data["triggers"]
        policy = data["execution_policy"]
        intervention = policy["intervention"]
        timeouts = self.timeouts

        extension_fields: dict[str, Any] = {
            "allow_disable_asset": self.risk_approvals.allow_disable_asset,
            "enable_asset_policy": self.risk_approvals.enable_asset_policy,
            "allow_destructive_methods": self.risk_approvals.allow_destructive_methods,
            "workflow_timeout_seconds": timeouts.workflow_seconds,
            "operator_timeout_seconds": timeouts.operator_seconds,
        }
        if intervention["method"]:
            extension_fields["intervention_method"] = intervention["method"]
            extension_fields["intervention_count"] = intervention["count"]
            extension_fields["intervention_message"] = intervention["message"]
            extension_fields["counter_parent_process"] = dict(intervention["parent_process"])

        selection: dict[str, Any] = {
            "tool": dict(workflows["tool_selector"]),
            "joining_process": dict(workflows["process_selector"]),
        }
        selectors_by_classification = workflows.get("process_selectors_by_classification") or {}
        if selectors_by_classification:
            selection["joining_processes"] = {
                key: dict(value) for key, value in dict(selectors_by_classification).items()
            }

        return {
            "schema_version": CURRENT_MANIFEST_SCHEMA_VERSION,
            "profile_name": self.name,
            "description": self.description,
            "capabilities_file": self.source_path if self.source_path.endswith(MANIFEST_SUFFIX) else "",
            "target": {
                "endpoint": data["connection"]["endpoint"],
                "expected_server": dict(data["connection"]["expected_server"]),
            },
            "cu_execution": {
                "default_mode": policy["default_mode"],
                "scoring_mode": self.scoring_mode,
                "precondition_failure_policy": policy["precondition_failure_policy"],
                "allow_manual_steps": policy["allow_manual_steps"],
                "default_timeout_seconds": timeouts.method_call_seconds,
                "state_changing_methods": dict(policy["state_changing_methods"]),
                "method_status_policies": dict(policy["method_status_policies"]),
                "extension_fields": extension_fields,
            },
            "selection": selection,
            "triggers": {
                "result": {
                    "mode": triggers["result"]["mode"],
                    "timeout_seconds": timeouts.result_trigger_seconds(str(triggers["result"]["mode"])),
                    "deselect_after_joining": triggers["result"]["deselect_after_joining"],
                },
                "event": {
                    "mode": triggers["event"]["mode"],
                    "timeout_seconds": timeouts.passive_observation_seconds,
                },
                "condition": {
                    "mode": triggers["condition"]["mode"],
                    "timeout_seconds": timeouts.passive_observation_seconds,
                },
            },
            "workflow_execution": {
                "start_invocation_policy": workflows["start_invocation_policy"],
                "expected_operation_count": workflows["expected_operation_count"],
                "expected_results": {
                    **dict(workflows["expected_results"]),
                    "timeout_seconds": timeouts.active_result_seconds,
                },
                "cleanup": dict(workflows["cleanup"]),
            },
            "reporting": {
                "output_dir": data["reporting"]["output_dir"],
                "sanitize_shared_artifacts": data["reporting"]["sanitize_shared_artifacts"],
                "keep_local_exact_debug_artifacts": data["reporting"]["keep_local_exact_debug_artifacts"],
            },
        }


# ---------------------------------------------------------------------------
# Load / parse / validate
# ---------------------------------------------------------------------------


def _reject_legacy_layout(raw: Mapping[str, Any], path: Path | None) -> None:
    name = path.name if path is not None else ""
    legacy_capability_file = name.endswith(".capabilities.yaml")
    legacy_profile_file = name.endswith(".profile.yaml")
    legacy_capability_keys = {"active_profile", "cu_overrides", "supported_facets"} & set(raw)
    legacy_profile_keys = {"profile_name", "capabilities_file", "cu_execution", "workflow_execution"} & set(raw)

    if legacy_capability_file or (legacy_capability_keys and "capability_claims" not in raw):
        raise LegacyPairedFileError(
            f"'{name or '<in-memory>'}' is a legacy capability declaration. The paired "
            "*.profile.yaml + *.capabilities.yaml model was replaced by one versioned "
            "*.sut.yaml manifest. Move active_profile/supported_facets/cu_overrides under "
            "'capability_claims' in a single manifest - see target_server_cu_profiles/template.sut.yaml."
        )
    if legacy_profile_file or (legacy_profile_keys and "capability_claims" not in raw):
        raise LegacyPairedFileError(
            f"'{name or '<in-memory>'}' is a legacy execution profile. The paired "
            "*.profile.yaml + *.capabilities.yaml model was replaced by one versioned "
            "*.sut.yaml manifest - see target_server_cu_profiles/template.sut.yaml."
        )


def parse_sut_manifest(raw: Mapping[str, Any], source_path: str = "<in-memory>") -> SutManifest:
    """Validate an already-parsed manifest mapping and return a :class:`SutManifest`."""
    if not isinstance(raw, dict):
        raise SutManifestError(f"SUT manifest must be a YAML mapping, got {type(raw).__name__}")

    path = Path(source_path) if source_path and source_path != "<in-memory>" else None
    _reject_legacy_layout(raw, path)

    version = raw.get("schema_version")
    if version is None:
        raise SutManifestError("SUT manifest is missing required field 'schema_version'")
    if not isinstance(version, int) or isinstance(version, bool):
        raise SutManifestError(f"schema_version: must be an integer, got {type(version).__name__}")
    if version not in SUPPORTED_MANIFEST_SCHEMA_VERSIONS:
        raise SutManifestError(
            f"Unsupported manifest schema_version {version}. "
            f"Supported versions: {sorted(SUPPORTED_MANIFEST_SCHEMA_VERSIONS)}"
        )

    reject_secret_values(raw)

    data: dict[str, Any] = {}
    top_level_sections = frozenset(section.name for section in MANIFEST_SCHEMA if section.name)
    for section in MANIFEST_SCHEMA:
        if section.name == "":
            data.update(_validate_section(raw, section, "", extra_known=top_level_sections))
        else:
            data[section.name] = _validate_section(raw.get(section.name), section, "")
    data["workflows"]["process_selectors_by_classification"] = _validate_process_selectors(
        (raw.get("workflows") or {}).get("process_selectors_by_classification")
    )

    manifest = SutManifest(
        schema_version=int(data["schema_version"]),
        name=str(data["name"]),
        description=str(data["description"]),
        lifecycle_mode=str(data["lifecycle"]["mode"]),
        startup_timeout_seconds=float(data["lifecycle"]["startup_timeout_seconds"]),
        authentication=AuthenticationConfig(**data["authentication"]),
        capability_claims=CapabilityClaims(
            active_profile=str(data["capability_claims"]["active_profile"]),
            supported_facets=tuple(data["capability_claims"]["supported_facets"]),
            cu_overrides=dict(data["capability_claims"]["cu_overrides"]),
            claims_are_authoritative=bool(data["capability_claims"]["claims_are_authoritative"]),
            allow_discovery_to_relax_claims=bool(data["capability_claims"]["allow_discovery_to_relax_claims"]),
        ),
        timeouts=TimeoutBudgets(**data["timeouts"]),
        risk_approvals=RiskApprovals(**data["execution_policy"]["risk_approvals"]),
        scoring_mode=str(data["scoring"]["mode"]),
        claimed_scope_only=bool(data["scoring"]["claimed_scope_only"]),
        approved_workflows=tuple(data["workflows"]["approved"]),
        redact_fields=tuple(data["reporting"]["redact_fields"]),
        source_path=str(path.resolve()) if path is not None else source_path,
        data=data,
    )
    _validate_consistency(manifest)
    return manifest


def _validate_consistency(manifest: SutManifest) -> None:
    """Cross-field rules that a single field cannot express."""
    auth = manifest.authentication
    missing = auth.missing_references()
    if missing:
        raise SutManifestError(
            f"authentication.source '{auth.source}' requires {missing[0]} to be set (a reference, not a secret)"
        )
    if auth.source == "anonymous" and auth.username:
        raise SutManifestError("authentication.username must be empty when authentication.source is 'anonymous'")

    policy = manifest.data["execution_policy"]
    intervention_method = str(policy["intervention"]["method"])
    allowed = list(policy["state_changing_methods"]["allowed_methods"])
    if (
        intervention_method
        and policy["state_changing_methods"]["default_policy"] == "require_explicit_opt_in"
        and intervention_method not in allowed
    ):
        raise SutManifestError(
            f"execution_policy.intervention.method '{intervention_method}' must also appear in "
            "execution_policy.state_changing_methods.allowed_methods"
        )

    expected = manifest.data["workflows"]["expected_results"]
    primary = str(expected["classification"])
    intermediate = list(expected["intermediate_classifications"])
    if primary in intermediate:
        raise SutManifestError(
            f"workflows.expected_results: primary classification '{primary}' must not repeat in "
            "intermediate_classifications"
        )
    invalid = sorted(set(intermediate) - (VALID_RESULT_CLASSIFICATIONS - {"any"}))
    if invalid:
        raise SutManifestError(f"workflows.expected_results.intermediate_classifications: invalid values {invalid}")

    try:
        manifest.to_execution_profile()
    except TargetServerConfigError as exc:  # pragma: no cover - defensive
        raise SutManifestError(f"Manifest is not a valid execution configuration: {exc}") from exc


@functools.lru_cache(maxsize=8)
def load_sut_manifest(path: Path) -> SutManifest:
    """Load and validate one ``*.sut.yaml`` manifest from disk.

    Raises
    ------
    FileNotFoundError
        When *path* does not exist.
    LegacyPairedFileError
        When a legacy ``*.profile.yaml`` / ``*.capabilities.yaml`` file is given.
    SutManifestError
        For malformed, unsafe, or unsupported manifests.
    """
    if not path.exists():
        raise FileNotFoundError(f"SUT manifest not found: {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise SutManifestError(f"YAML parse error in '{path}': {exc}") from exc
    if not isinstance(raw, dict):
        raise SutManifestError(f"SUT manifest '{path}' must be a YAML mapping at the top level")
    manifest = parse_sut_manifest(raw, source_path=str(path))
    logger.info(
        "Loaded SUT manifest '%s' (schema_version=%d, lifecycle=%s, result trigger=%s)",
        manifest.name,
        manifest.schema_version,
        manifest.lifecycle_mode,
        manifest.result_trigger_mode,
    )
    return manifest


def validate_live_ready(manifest: SutManifest, *, env: Mapping[str, str] | None = None) -> list[str]:
    """Return the issues that block using *manifest* for a live external run.

    An empty list means the manifest is ready. Simulator manifests are always
    ready because the runner supplies the endpoint itself.
    """
    if manifest.is_auto_simulator:
        return []

    issues: list[str] = operational_placeholder_issues(manifest.to_dict())
    if not manifest.endpoint:
        issues.append("connection.endpoint: required for an external SUT")
    for name in manifest.authentication.unresolved_environment_vars(env):
        issues.append(f"authentication: environment variable '{name}' is referenced but not set")
    return sorted(set(issues))


def load_capability_claims(path: Path) -> CapabilityClaims:
    """Load only the authoritative CU claims from a manifest.

    Used by the pytest CU gate and the report generators so claim resolution
    exists in exactly one place.
    """
    return load_sut_manifest(path).capability_claims


# ---------------------------------------------------------------------------
# Built-in presets (code/data - never required companion files)
# ---------------------------------------------------------------------------

_SIMULATOR_UNSUPPORTED_CUS: tuple[str, ...] = (
    "acknowledge_results",
    "delete_joining_process",
    "delete_joint_component",
    "delete_joint_design",
    "disconnect_asset",
    "execute_operation",
    "feedback_methods",
    "get_error_information",
    "get_joining_process",
    "get_joining_process_revision_list",
    "get_joint_component",
    "get_joint_component_list",
    "get_joint_design",
    "get_joint_design_list",
    "get_joint_revision_list",
    "joint_component_data",
    "joint_design_data",
    "reboot_asset",
    "request_unacknowledged_results",
    "send_joining_process",
    "send_joint_component",
    "send_joint_design",
    "set_calibration",
    "set_joining_process_mapping",
    "set_offline_timer",
)

_REMOTE_START_FACETS: tuple[str, ...] = (
    "batch_result_server_facet",
    "event_management_server_facet",
    "identifiers_methods_server_facet",
    "enable_tool_server_facet",
    "asset_connection_server_facet",
    "general_process_operations_server_facet",
    "sequential_process_operations_server_facet",
    "asset_management_assets_server_facet",
)

#: Claims carried over verbatim from the previous paired capability declaration
#: for the multi-operation job example. Do not drop entries: they are the
#: authoritative claim set for that generic controller workflow.
_REMOTE_START_CU_OVERRIDES: dict[str, str] = {
    "acknowledge_results": "unsupported",
    "asset_management_accessory": "unsupported",
    "asset_management_battery": "unsupported",
    "asset_management_battery_operation_cycle_counter": "unsupported",
    "asset_management_cable": "unsupported",
    "asset_management_feeder": "unsupported",
    "asset_management_health": "unsupported",
    "asset_management_memory_device": "supported",
    "asset_management_monitoring_health": "supported",
    "asset_management_power_supply": "unsupported",
    "asset_management_sensor": "unsupported",
    "asset_management_servo": "unsupported",
    "asset_management_software": "unsupported",
    "asset_management_sub_component": "unsupported",
    "delete_joint": "unsupported",
    "delete_joint_component": "unsupported",
    "delete_joint_design": "unsupported",
    "deselect_joining_process": "unsupported",
    "disconnect_asset": "unsupported",
    "execute_operation": "unsupported",
    "feedback_methods": "unsupported",
    "get_error_information": "unsupported",
    "get_joining_process_revision_list": "unsupported",
    "get_joint": "unsupported",
    "get_joint_component": "unsupported",
    "get_joint_component_list": "unsupported",
    "get_joint_design": "unsupported",
    "get_joint_design_list": "unsupported",
    "get_joint_list": "unsupported",
    "get_joint_revision_list": "unsupported",
    "get_latest_result": "unsupported",
    "get_result_by_id": "unsupported",
    "get_result_with_filter_criteria": "unsupported",
    "intervention_result": "supported",
    "io_signals_methods": "unsupported",
    "job_result": "supported",
    "joint_component_data": "unsupported",
    "joint_data": "unsupported",
    "joint_design_data": "unsupported",
    "joint_management": "unsupported",
    "partial_consolidated_result": "supported",
    "reboot_asset": "unsupported",
    "request_results": "unsupported",
    "request_unacknowledged_results": "unsupported",
    "requested_result_event_access": "unsupported",
    "requested_result_variable_access": "unsupported",
    "result_extended_meta_data": "unsupported",
    "result_value_final_tag": "supported",
    "result_value_trace_point_index": "unsupported",
    "result_value_trace_point_time_offset": "unsupported",
    "select_joint": "unsupported",
    "send_joint": "unsupported",
    "send_joint_component": "unsupported",
    "send_joint_design": "unsupported",
    "set_calibration": "unsupported",
    "set_joining_process_counter": "unsupported",
    "set_joining_process_mapping": "unsupported",
    "set_offline_timer": "unsupported",
    "set_time": "unsupported",
    "start_joining_process": "unsupported",
    "sync_result": "unsupported",
    "sync_result_counters": "unsupported",
}

_PRESETS: Mapping[str, dict[str, Any]] = {
    "template": {
        "name": "Template SUT",
        "description": (
            "Copy this template, replace every <placeholder>, and keep controller-specific "
            "copies outside the repository or sanitized."
        ),
        "lifecycle": {"mode": "external"},
        "connection": {"endpoint": "opc.tcp://<host>:40451"},
        "authentication": {"source": "anonymous"},
        "capability_claims": {"active_profile": "full_specification_coverage"},
        "triggers": {"result": {"mode": "none"}},
        "execution_policy": {"default_mode": "preflight_only"},
        "scoring": {"mode": "strict_profile"},
    },
    "simulator": {
        "name": "OPC UA IJT Server Simulator",
        "description": (
            "Checked-in Release 2 IJT server simulator. Complete and placeholder-free: "
            "the runner launches it and supplies the endpoint."
        ),
        "lifecycle": {"mode": "auto_simulator"},
        "connection": {"endpoint": ""},
        "authentication": {"source": "anonymous"},
        "capability_claims": {
            "active_profile": "full_specification_coverage",
            "cu_overrides": {key: "unsupported" for key in _SIMULATOR_UNSUPPORTED_CUS},
        },
        "workflows": {
            "approved": ["simulated_single_result", "simulated_events", "simulated_conditions"],
            "expected_results": {"classification": "single"},
        },
        "triggers": {
            "result": {"mode": "simulate_methods"},
            "event": {"mode": "simulate_methods"},
            "condition": {"mode": "simulate_methods"},
        },
        "execution_policy": {
            "default_mode": "automated",
            "state_changing_methods": {
                "default_policy": "require_explicit_opt_in",
                "allowed_methods": [
                    "SimulateResult",
                    "SimulateEvent",
                    "SimulateCondition",
                    "SelectJoiningProcess",
                    "StartSelectedJoining",
                    "DeselectJoiningProcess",
                ],
            },
        },
        "timeouts": {"passive_observation_seconds": 5.0, "active_result_seconds": 30.0},
        "scoring": {"mode": "strict_profile"},
    },
    "remote_start_multi_operation": {
        "name": "Generic remote-start multi-operation controller",
        "description": (
            "Generic sanitized example for any vendor controller that runs a multi-operation job "
            "started remotely. GetJoiningProcessList may return several programs, batches, or jobs; "
            "this manifest pins one Job-producing JoiningProcess so the starts and result layers are "
            "deterministic. Six remote starts exercise two batches of three operations, producing "
            "SingleResult, BatchResult, and a final JobResult. IncrementJoiningProcessCounter produces "
            "companion InterventionResult evidence."
        ),
        "lifecycle": {"mode": "external"},
        "connection": {"endpoint": "opc.tcp://<target-server-host>:40451"},
        "authentication": {"source": "anonymous"},
        "capability_claims": {
            "active_profile": "general_joining_system",
            "supported_facets": list(_REMOTE_START_FACETS),
            "cu_overrides": dict(_REMOTE_START_CU_OVERRIDES),
        },
        "workflows": {
            "approved": ["remote_start_multi_operation_job", "counter_intervention"],
            "start_invocation_policy": "single_start_produces_final_result",
            "expected_operation_count": 1,
            "process_selector": {
                "policy": "first_ready",
                "joining_process_id": "",
                "joining_process_origin_id": "",
            },
            "process_selectors_by_classification": {
                "single": {
                    "policy": "first_ready",
                    "joining_process_id": "",
                    "joining_process_origin_id": "",
                },
                "job": {
                    "policy": "first_ready",
                    "joining_process_id": "",
                    "joining_process_origin_id": "",
                },
                "batch": {
                    "policy": "first_ready",
                    "joining_process_id": "",
                    "joining_process_origin_id": "",
                },
            },
            "expected_results": {
                "classification": "job",
                "intermediate_classifications": ["single", "batch", "sync", "intervention"],
                "final_result_required": False,
            },
            "cleanup": {"policy": "best_effort_with_evidence", "deselect_process": False},
        },
        "triggers": {
            "result": {"mode": "start_selected_joining", "deselect_after_joining": False},
            "event": {"mode": "none"},
            "condition": {"mode": "none"},
        },
        "execution_policy": {
            "default_mode": "automated",
            "allow_manual_steps": False,
            "precondition_failure_policy": "blocked",
            "state_changing_methods": {
                "default_policy": "require_explicit_opt_in",
                "allowed_methods": [
                    "EnableAsset",
                    "SelectJoiningProcess",
                    "StartSelectedJoining",
                    "IncrementJoiningProcessCounter",
                    "DecrementJoiningProcessCounter",
                    "AbortJoiningProcess",
                    "ResetJoiningProcess",
                ],
            },
            "intervention": {"method": "IncrementJoiningProcessCounter", "count": 1},
            "risk_approvals": {
                "allow_disable_asset": False,
                "enable_asset_policy": "always",
                "allow_destructive_methods": True,
                "approved_by": "test-user",
                "approval_reference": "controller-test-run",
            },
        },
        "timeouts": {
            "passive_observation_seconds": 5.0,
            "active_result_seconds": 8.0,
            "workflow_seconds": 300.0,
            "operator_seconds": 300.0,
            "method_call_seconds": 15.0,
        },
        "scoring": {"mode": "strict_profile"},
    },
    "manual_trigger": {
        "name": "Generic manually triggered controller",
        "description": (
            "Generic sanitized example for a controller where joining results are produced by a "
            "physical operator/tool trigger rather than a remote StartSelectedJoining. The client "
            "subscribes first and then waits for the operator. Replace <target-server-host> and keep "
            "any manifest holding real identifiers outside the repository."
        ),
        "lifecycle": {"mode": "external"},
        "connection": {"endpoint": "opc.tcp://<target-server-host>:40451"},
        "authentication": {"source": "prompt"},
        "capability_claims": {
            "active_profile": "full_specification_coverage",
            "cu_overrides": {"start_selected_joining": "manual_required"},
        },
        "workflows": {
            "approved": ["manual_operator_single_result"],
            "start_invocation_policy": "manual_operation_trigger",
            "expected_operation_count": 1,
            "expected_results": {"classification": "single", "final_result_required": True},
            "cleanup": {"policy": "best_effort_with_evidence", "deselect_process": False},
        },
        "triggers": {
            "result": {"mode": "manual_trigger"},
            "event": {"mode": "observe_only"},
            "condition": {"mode": "observe_only"},
        },
        "execution_policy": {
            "default_mode": "guided",
            "allow_manual_steps": True,
            "precondition_failure_policy": "blocked",
            "state_changing_methods": {"default_policy": "require_explicit_opt_in", "allowed_methods": []},
        },
        "timeouts": {
            "passive_observation_seconds": 5.0,
            "active_result_seconds": 180.0,
            "workflow_seconds": 600.0,
            "operator_seconds": 180.0,
            "method_call_seconds": 15.0,
        },
        "scoring": {"mode": "strict_profile"},
    },
}


def preset_names() -> tuple[str, ...]:
    """Return the built-in preset names."""
    return tuple(_PRESETS)


def _deep_merge(base: dict[str, Any], overlay: Mapping[str, Any]) -> dict[str, Any]:
    for key, value in overlay.items():
        if isinstance(value, Mapping) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = copy.deepcopy(value)
    return base


def _schema_defaults(schema: Sequence[SectionSpec] = MANIFEST_SCHEMA) -> dict[str, Any]:
    defaults: dict[str, Any] = {}
    for section in schema:
        target = defaults if section.name == "" else defaults.setdefault(section.name, {})
        for spec in section.fields:
            target[spec.name] = spec.default_value()
        for sub in section.subsections:
            target[sub.name] = _schema_defaults((sub,))[sub.name]
    return defaults


def preset_data(name: str) -> dict[str, Any]:
    """Return the fully-defaulted raw mapping for preset *name*."""
    if name not in _PRESETS:
        raise SutManifestError(f"Unknown preset '{name}'. Available presets: {list(preset_names())}")
    data = _schema_defaults()
    return _deep_merge(data, _PRESETS[name])


def build_preset(name: str) -> SutManifest:
    """Return a validated :class:`SutManifest` for the built-in preset *name*."""
    return parse_sut_manifest(preset_data(name), source_path=f"<preset:{name}>")


# ---------------------------------------------------------------------------
# Generation: commented template YAML and Markdown field reference
# ---------------------------------------------------------------------------

_HEADER = """\
# {title}
#
# One SUT manifest describes one System Under Test end to end: connection,
# authentication references, authoritative Conformance Unit claims, approved
# workflows, trigger modes, execution/risk policy, timeout budgets, scoring
# strictness, and reporting/redaction.
#
# GENERATED FILE - do not edit by hand.
# Regenerate with:  python scripts/generate_sut_manifest_docs.py
# Check for drift:  python scripts/generate_sut_manifest_docs.py --check
#
# Security:
#   Never put a password, token, or key in this file. Reference a local
#   credentials file or environment variable names instead.
#   Do not commit real endpoints, ProductInstanceUris, or process IDs.
#
# Placeholders written as <like-this> must be replaced before an external
# (non-simulator) run; the runner fails fast while any remain.
#
# This report describes what this client observed. It is not an OPC Foundation
# certification and makes no certification claim.
"""


def _yaml_scalar(value: Any) -> str:
    dumped = yaml.safe_dump(value, default_flow_style=True, sort_keys=False).strip()
    if dumped.endswith("..."):
        dumped = dumped[: -len("...")].strip()
    return dumped


def _comment_lines(spec: FieldSpec, indent: str) -> list[str]:
    lines = [f"{indent}# {line}" for line in _wrap(spec.description, 100 - len(indent))]
    if spec.choices:
        lines.append(f"{indent}# Values: {', '.join(_sorted_choices(spec.choices))}")
    if spec.value_choices:
        lines.append(f"{indent}# Entry values: {', '.join(_sorted_choices(spec.value_choices))}")
    if spec.required:
        lines.append(f"{indent}# REQUIRED")
    if spec.secret_reference:
        lines.append(f"{indent}# Reference only - never place the secret value itself here.")
    return lines


def _wrap(text: str, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > max(width, 20) and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [""]


def _render_value(value: Any, indent: str) -> list[str]:
    """Render a non-empty mapping or list value under its field name."""
    if isinstance(value, dict):
        return [f"{indent}  {key}: {_yaml_scalar(item)}" for key, item in value.items()]
    return [f"{indent}  - {_yaml_scalar(item)}" for item in value]


def _render_section(section: SectionSpec, values: Mapping[str, Any], indent: str, lines: list[str]) -> None:
    for spec in section.fields:
        value = values.get(spec.name, spec.default_value())
        lines.append("")
        lines.extend(_comment_lines(spec, indent))
        if isinstance(value, (dict, list)) and value:
            lines.append(f"{indent}{spec.name}:")
            lines.extend(_render_value(value, indent))
        else:
            lines.append(f"{indent}{spec.name}: {_yaml_scalar(value)}")
    for sub in section.subsections:
        sub_values = values.get(sub.name) or {}
        lines.append("")
        lines.extend(f"{indent}# {line}" for line in _wrap(sub.description, 100 - len(indent)))
        if sub.name == "process_selectors_by_classification" and not sub_values:
            lines.append(f"{indent}{sub.name}: {{}}")
            continue
        if sub.name == "process_selectors_by_classification":
            lines.append(f"{indent}{sub.name}:")
            for key, entry in dict(sub_values).items():
                lines.append(f"{indent}  {key}:")
                for field_name, field_value in dict(entry).items():
                    lines.append(f"{indent}    {field_name}: {_yaml_scalar(field_value)}")
            continue
        lines.append(f"{indent}{sub.name}:")
        _render_section(sub, sub_values, indent + "  ", lines)


def render_manifest_yaml(preset: str = "template", title: str | None = None) -> str:
    """Render a fully commented manifest for *preset*, generated from schema metadata."""
    values = preset_data(preset)
    parse_sut_manifest(values, source_path=f"<preset:{preset}>")  # never generate an invalid file
    heading = title or f"SUT Manifest - {values['name']}"
    lines: list[str] = [_HEADER.format(title=heading).rstrip()]
    for section in MANIFEST_SCHEMA:
        if section.name == "":
            _render_section(section, values, "", lines)
            continue
        lines.append("")
        lines.append("# " + "-" * 74)
        lines.extend(f"# {line}" for line in _wrap(f"{section.name}: {section.description}", 98))
        lines.append("# " + "-" * 74)
        lines.append(f"{section.name}:")
        _render_section(section, values.get(section.name) or {}, "  ", lines)
    return "\n".join(lines).replace("\n\n\n", "\n\n") + "\n"


def _reference_row(path: str, spec: FieldSpec) -> str:
    kind = {"str_list": "list of strings", "str_map": "mapping", "number": "number"}.get(spec.kind, spec.kind)
    allowed = ", ".join(f"`{item}`" for item in _sorted_choices(spec.choices)) if spec.choices else ""
    if not allowed and spec.value_choices:
        allowed = ", ".join(f"`{item}`" for item in _sorted_choices(spec.value_choices))
    default = _yaml_scalar(spec.default_value())
    required = "Yes" if spec.required else "No"
    description = spec.description.replace("|", "\\|")
    if spec.secret_reference:
        description += " Reference only - never a secret value."
    return f"| `{path}` | {kind} | {required} | `{default}` | {allowed or '-'} | {description} |"


def render_field_reference() -> str:
    """Render the Markdown field reference table from the schema metadata."""
    lines = [
        "# SUT Manifest Field Reference",
        "",
        "<!-- GENERATED FILE - do not edit by hand. -->",
        "<!-- Regenerate: python scripts/generate_sut_manifest_docs.py -->",
        "<!-- Check drift: python scripts/generate_sut_manifest_docs.py --check -->",
        "",
        (
            f"One System Under Test is described by exactly one `*{MANIFEST_SUFFIX}` manifest "
            f"(schema version {CURRENT_MANIFEST_SCHEMA_VERSION}). It replaces the previous paired "
            "`*.profile.yaml` + `*.capabilities.yaml` files."
        ),
        "",
        "Rules that the loader enforces:",
        "",
        "- A manifest never contains a secret. Reference a local credentials file or environment variable names.",
        "- Capability claims are authoritative; discovery observations never silently change them.",
        "- Scoring defaults to strict claimed scope.",
        "- `<placeholder>` values must be replaced before an external (non-simulator) run.",
        "",
        "Outcomes in the final report use the canonical vocabulary "
        "(Passed, Failed, Not Supported, Blocked, Not Tested, Inconclusive). "
        "This client reports observations only and makes no OPC Foundation certification claim.",
        "",
        "## Fields",
        "",
        "| Field | Type | Required | Default | Allowed values | Description |",
        "|---|---|:---:|---|---|---|",
    ]
    lines.extend(_reference_row(path, spec) for path, spec in iter_field_specs())
    lines.extend(
        [
            "",
            "## Built-in presets",
            "",
            "Presets are code, not companion files. They seed generation of the committed "
            "examples; at run time you supply exactly one manifest.",
            "",
            "| Preset | Name | Lifecycle | Result trigger |",
            "|---|---|---|---|",
        ]
    )
    for name in preset_names():
        manifest = build_preset(name)
        lines.append(f"| `{name}` | {manifest.name} | `{manifest.lifecycle_mode}` | `{manifest.result_trigger_mode}` |")
    lines.append("")
    return "\n".join(lines)
