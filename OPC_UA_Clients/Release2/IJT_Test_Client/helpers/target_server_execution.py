"""
target_server_execution — canonical Target Server CU execution logic.

This module is the single implementation of Target Server CU preflight,
classification, live specification_tests/ orchestration, and evidence
reporting.  It is consumed by ``run_all_tests.py`` (``--profile``,
``--phase2 --profile``, ``--preflight-only --profile``).
"""

from __future__ import annotations

import datetime
import json
import logging
import math
import os
import shutil
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

from helpers.namespaces import result_classification_value
from helpers.target_server_cu_config import (
    OUTCOME_BLOCKED,
    OUTCOME_CLAIM_MISMATCH,
    OUTCOME_CONFIGURATION_ERROR,
    OUTCOME_FAILED,
    OUTCOME_MANUAL_REQUIRED,
    OUTCOME_PASSED,
    OUTCOME_UNSUPPORTED,
    TargetServerCuProfile,
)
from helpers.target_server_readiness import (
    PreflightReport,
    ReadinessOutcome,
    check_endpoint_reachable,
    run_config_preflight,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from helpers.connection_security import ConnectionSecurity, CredentialPrompt

# _HERE resolves to the IJT_Test_Client project root (parent of helpers/), which is
# identical to the ``_HERE`` computed independently by run_all_tests.py.
_HERE = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Colour / logging helpers (self-contained; deliberately not shared with
# run_all_tests.py's own colour helpers to avoid coupling unrelated CLIs).
# ---------------------------------------------------------------------------

_USE_COLOUR = False

_ANSI_GREEN = "\033[92m"
_ANSI_RED = "\033[91m"
_ANSI_YELLOW = "\033[93m"
_ANSI_CYAN = "\033[96m\033[1m"
_ANSI_RESET = "\033[0m"


def configure_colour(enabled: bool) -> None:
    """Enable or disable ANSI colour output for subsequent log lines."""
    global _USE_COLOUR
    _USE_COLOUR = enabled


def _c(ansi: str, text: str) -> str:
    return f"{ansi}{text}{_ANSI_RESET}" if _USE_COLOUR else text


def _log(msg: str) -> None:
    sys.stdout.write(msg + "\n")
    sys.stdout.flush()


def _section(title: str) -> None:
    _log(_c(_ANSI_CYAN, f"\n  ── {title} ──"))


def _divider() -> None:
    _log(_c(_ANSI_CYAN, "─" * 56))


def _outcome_colour(outcome: str) -> str:
    return {
        OUTCOME_PASSED: _ANSI_GREEN,
        OUTCOME_FAILED: _ANSI_RED,
        OUTCOME_BLOCKED: _ANSI_YELLOW,
        OUTCOME_CONFIGURATION_ERROR: _ANSI_RED,
        OUTCOME_CLAIM_MISMATCH: _ANSI_RED,
        OUTCOME_MANUAL_REQUIRED: _ANSI_YELLOW,
        OUTCOME_UNSUPPORTED: _ANSI_YELLOW,
    }.get(outcome, "")


def _print_check(check: ReadinessOutcome) -> None:
    width = 44
    label = check.check_name or "check"
    dots = "." * max(0, width - len(label))
    outcome_str = _c(_outcome_colour(check.outcome), check.outcome.upper())
    detail = f"  ({check.detail})" if check.detail else ""
    _log(f"  {label} {dots} {outcome_str}{detail}")


def format_error(text: str) -> str:
    """Return *text* rendered in the shared error (red) colour, if colour is enabled."""
    return _c(_ANSI_RED, text)


# ---------------------------------------------------------------------------
# Conformance-unit result-scope constants
# ---------------------------------------------------------------------------

_COMMON_CONSOLIDATED_RESULT_CUS = frozenset(
    {
        "self_contained_consolidated_result",
        "consolidated_result_with_references",
        "partial_consolidated_result",
    }
)

_RESULT_CUS_BY_CLASSIFICATION = {
    "single": frozenset(),
    "sync": frozenset({"sync_result", "sync_result_counters"}),
    "batch": frozenset({"batch_result", "batch_result_counters"}),
    "job": frozenset({"job_result"}),
    "stitching": frozenset(),
    "intervention": frozenset({"intervention_result"}),
    "text": frozenset(),
}
_CLASSIFICATION_RESULT_CUS = frozenset().union(*_RESULT_CUS_BY_CLASSIFICATION.values())
_CONSOLIDATED_CLASSIFICATIONS = frozenset({"sync", "batch", "job", "stitching"})


def _excluded_cus_for_result_scope(
    classification: str,
    intermediate_classifications: tuple[str, ...] = (),
    configured_classifications: tuple[str, ...] = (),
) -> frozenset[str]:
    """Return CUs that cannot be exercised by the configured result workflow."""
    if classification == "any":
        return frozenset()

    active = {classification, *intermediate_classifications, *configured_classifications}
    included_specific = frozenset().union(*(_RESULT_CUS_BY_CLASSIFICATION.get(item, frozenset()) for item in active))
    excluded = _CLASSIFICATION_RESULT_CUS - included_specific
    if active.isdisjoint(_CONSOLIDATED_CLASSIFICATIONS):
        excluded |= _COMMON_CONSOLIDATED_RESULT_CUS
    return excluded


# ---------------------------------------------------------------------------
# Runtime override application
# ---------------------------------------------------------------------------


def apply_runtime_overrides(
    profile: TargetServerCuProfile,
    *,
    endpoint: str | None = None,
    scoring_mode: str | None = None,
    capabilities_file: str | None = None,
    tool_product_instance_uri: str | None = None,
    joining_process_id: str | None = None,
    joining_process_origin_id: str | None = None,
    job_joining_process_id: str | None = None,
    job_joining_process_origin_id: str | None = None,
    batch_joining_process_id: str | None = None,
    batch_joining_process_origin_id: str | None = None,
    single_joining_process_id: str | None = None,
    single_joining_process_origin_id: str | None = None,
    sync_joining_process_id: str | None = None,
    sync_joining_process_origin_id: str | None = None,
) -> TargetServerCuProfile:
    """Apply installation-specific values without requiring a private YAML copy."""
    if endpoint:
        profile = replace(profile, target=replace(profile.target, endpoint=endpoint))
    if scoring_mode:
        profile = replace(profile, cu_execution=replace(profile.cu_execution, scoring_mode=scoring_mode))
    if capabilities_file:
        profile = replace(profile, capabilities_file=str(Path(capabilities_file).resolve()))
    if tool_product_instance_uri:
        tool = replace(
            profile.selection.tool,
            policy="exact_match",
            product_instance_uri=tool_product_instance_uri,
        )
        profile = replace(profile, selection=replace(profile.selection, tool=tool))
    if joining_process_id or joining_process_origin_id:
        process = replace(
            profile.selection.joining_process,
            policy="exact_match" if joining_process_id else profile.selection.joining_process.policy,
            joining_process_id=joining_process_id or profile.selection.joining_process.joining_process_id,
            joining_process_origin_id=(
                joining_process_origin_id or profile.selection.joining_process.joining_process_origin_id
            ),
        )
        profile = replace(profile, selection=replace(profile.selection, joining_process=process))

    updated_jps = dict(profile.selection.joining_processes)
    per_class_overrides = (
        ("job", job_joining_process_id, job_joining_process_origin_id),
        ("batch", batch_joining_process_id, batch_joining_process_origin_id),
        ("single", single_joining_process_id, single_joining_process_origin_id),
        ("sync", sync_joining_process_id, sync_joining_process_origin_id),
    )
    for key, ovr_id, ovr_origin in per_class_overrides:
        if ovr_id or ovr_origin:
            base_jp = updated_jps.get(key, profile.selection.joining_process)
            updated_jps[key] = replace(
                base_jp,
                policy="exact_match" if ovr_id else base_jp.policy,
                joining_process_id=ovr_id or base_jp.joining_process_id,
                joining_process_origin_id=ovr_origin or base_jp.joining_process_origin_id,
            )
    if updated_jps != profile.selection.joining_processes:
        profile = replace(profile, selection=replace(profile.selection, joining_processes=updated_jps))
    return profile


# ---------------------------------------------------------------------------
# Evidence report
# ---------------------------------------------------------------------------


def _write_evidence_report(
    output_dir: Path,
    profile: TargetServerCuProfile,
    preflight_report: PreflightReport,
    mode: str,
    run_start: str,
    extra: dict | None = None,
) -> Path:
    """Write a JSON evidence report to *output_dir*."""
    output_dir.mkdir(parents=True, exist_ok=True)
    report_data = {
        "schema_version": 1,
        "run_start": run_start,
        "mode": mode,
        "profile_name": profile.profile_name,
        "profile_source": profile.source_path,
        "endpoint": profile.target.endpoint,
        "scoring_mode": profile.cu_execution.scoring_mode,
        "canonical_outcome": preflight_report.canonical_outcome.value,
        "canonical_label": preflight_report.canonical_outcome.label,
        "workflow": {
            "result_trigger_mode": profile.triggers.result.mode,
            "event_trigger_mode": profile.triggers.event.mode,
            "condition_trigger_mode": profile.triggers.condition.mode,
            "primary_result_classification": profile.workflow_execution.expected_results.classification,
            "intermediate_result_classifications": list(
                profile.workflow_execution.expected_results.intermediate_classifications
            ),
            "joining_process_selection_policy": profile.selection.joining_process.policy,
        },
        "preflight": preflight_report.to_dict(),
        **(extra or {}),
    }
    report_path = output_dir / "target-server-cu-report.json"
    report_path.write_text(json.dumps(report_data, indent=2, default=str), encoding="utf-8")
    return report_path


def _write_human_summary(
    output_dir: Path,
    profile: TargetServerCuProfile,
    preflight_report: PreflightReport,
    mode: str,
    run_start: str,
    outcome_summary: str,
) -> Path:
    """Write a plain-text human summary."""
    output_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "IJT Target Server CU Run Summary",
        f"  Profile:  {profile.profile_name}",
        f"  Endpoint: {profile.target.endpoint}",
        f"  Mode:     {mode}",
        f"  Start:    {run_start}",
        f"  Outcome:  {outcome_summary}",
        f"  Preflight Outcome: {preflight_report.canonical_outcome.label}",
        "",
        *preflight_report.summary_lines(),
        "",
    ]
    summary_path = output_dir / "target-server-cu-summary.txt"
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    return summary_path


def _write_markdown_summary(
    output_dir: Path,
    profile: TargetServerCuProfile,
    preflight_report: PreflightReport,
    mode: str,
    run_start: str,
    outcome_summary: str,
    extra: dict | None = None,
) -> Path:
    """Write a structured GitHub-flavored Markdown summary report."""
    output_dir.mkdir(parents=True, exist_ok=True)
    badge = (
        "🟢 **PASSED**"
        if "PASSED" in outcome_summary
        else (
            "🟡 **SKIPPED / CLASSIFICATION ONLY**"
            if "SKIPPED" in outcome_summary or "CLASSIFICATION" in outcome_summary
            else "🔴 **FAILED**"
        )
    )
    lines = [
        "# Target Server Conformance Unit Run Summary",
        "",
        f"- **Profile:** `{profile.profile_name}`",
        f"- **Endpoint:** `{profile.target.endpoint}`",
        f"- **Mode:** `{mode}`",
        f"- **Start Time:** `{run_start}`",
        f"- **Outcome:** {badge} (`{outcome_summary}`)",
        f"- **Preflight Outcome:** `{preflight_report.canonical_outcome.label}`",
        "",
        "## Preflight Checks",
        "",
        "| Check Name | Status | Outcome | Detail |",
        "|---|:---:|:---:|---|",
    ]
    for check in preflight_report.checks:
        status_icon = (
            "✅" if check.outcome == OUTCOME_PASSED else ("⚠️" if check.outcome == OUTCOME_MANUAL_REQUIRED else "❌")
        )
        lines.append(
            f"| `{check.check_name}` | {status_icon} `{check.outcome}` | {check.canonical_label} | {check.detail} |"
        )

    lines.extend(
        [
            "",
            "## Conformance Unit Classification",
            "",
            "| Evidence Kind | Count |",
            "|---|:---:|",
        ]
    )
    cu_counts = (extra or {}).get("cu_classification", {})
    if cu_counts:
        for kind, count in sorted(cu_counts.items()):
            lines.append(f"| `{kind}` | {count} |")
    else:
        lines.append("| (Preflight only) | - |")

    spec_tests = (extra or {}).get("spec_tests")
    if spec_tests:
        lines.extend(
            [
                "",
                "## Specification Tests Execution",
                "",
                f"- **Status:** `{spec_tests.get('status')}`",
                f"- **Outcome:** `{spec_tests.get('outcome')}`",
                f"- **Exit Code:** `{spec_tests.get('exit_code')}`",
                f"- **Duration:** `{spec_tests.get('elapsed_seconds')}s`",
                f"- **JUnit XML:** `{spec_tests.get('junit_xml')}`",
            ]
        )

    excel_report = (extra or {}).get("excel_report")
    if excel_report:
        lines.extend(
            [
                "",
                "## Generated Artifacts",
                "",
                f"- **Excel Workbook:** `{excel_report.get('path') or 'N/A'}` (`{excel_report.get('status')}`)",
                "- **JSON Evidence Report:** `target-server-cu-report.json`",
                "- **Text Summary:** `target-server-cu-summary.txt`",
                "- **Markdown Summary:** `target-server-cu-summary.md`",
            ]
        )

    lines.append("")
    md_path = output_dir / "target-server-cu-summary.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path


# ---------------------------------------------------------------------------
# Target server auto-discovery
# ---------------------------------------------------------------------------

# Keyword hints used only when a process does not advertise a usable
# ResultClassification value.  Each keyword maps to exactly one classification
# key so a process can never be suggested under two conflicting keys.
_CLASSIFICATION_NAME_HINTS: tuple[tuple[str, str], ...] = (
    ("intervention", "intervention"),
    ("stitch", "stitching"),
    ("batch", "batch"),
    ("job", "job"),
    ("sequence", "job"),
    ("sync", "sync"),
    ("program", "single"),
    ("pset", "single"),
)

# Classification keys offered in the suggested YAML snippet, in output order.
_SUGGESTED_SELECTION_KEYS: tuple[str, ...] = ("single", "sync", "batch", "job", "stitching", "intervention")


def classify_discovered_process(process: dict) -> str:
    """Return the canonical classification key for one discovered joining process.

    The server-reported ``Classification`` value is authoritative and is mapped
    through the shared ``helpers.namespaces`` table (1 single, 2 sync, 3 batch,
    4 job, 5 stitching, 6 intervention, 7 text).  Name/selection-name keyword
    hints are only consulted when the server reports no usable classification.
    Returns an empty string when the process cannot be classified.
    """
    from helpers.namespaces import result_classification_name

    key = result_classification_name(process.get("classification"))
    if key:
        return key
    haystack = f"{process.get('name', '')} {process.get('selection_name', '')}".lower()
    for keyword, mapped_key in _CLASSIFICATION_NAME_HINTS:
        if keyword in haystack:
            return mapped_key
    return ""


def suggest_process_selection(processes: list[dict]) -> dict[str, dict]:
    """Map each classification key to at most one discovered process.

    A process is assigned to exactly one key, so the suggested YAML can never
    configure the same process under two conflicting classifications.
    """
    suggestion: dict[str, dict] = {}
    for process in processes:
        key = classify_discovered_process(process)
        if key and key not in suggestion:
            suggestion[key] = process
    return suggestion


def render_suggested_selection_yaml(product_instance_uri: str, suggestion: dict[str, dict]) -> str:
    """Render the suggested ``selection:`` YAML snippet for a discovery run."""
    lines = [
        "selection:",
        "  tool:",
        "    policy: first_ready",
        f'    product_instance_uri: "{product_instance_uri}"',
        "  joining_processes:",
    ]
    emitted = False
    for key in _SUGGESTED_SELECTION_KEYS:
        process = suggestion.get(key)
        if process is None:
            continue
        emitted = True
        lines.extend(
            [
                f"    {key}:",
                "      policy: exact_match",
                f'      joining_process_id: "{process.get("id", "")}"',
                f'      joining_process_origin_id: "{process.get("origin_id", "")}"',
                f'      selection_name: "{process.get("selection_name", "")}"',
            ]
        )
    if not emitted:
        lines.append("    # No joining process could be classified — configure selection.joining_process manually.")
    return "\n".join(lines)


async def async_discover_target_server(
    endpoint: str,
    timeout: float = 15.0,
    *,
    security: ConnectionSecurity | None = None,
    prompt: CredentialPrompt | None = None,
) -> dict:
    """Connect to a target OPC UA server, discover Tools and Joining Processes, and return structured metadata.

    ``security`` is an optional :class:`helpers.connection_security.ConnectionSecurity`
    declaration; when given, its message security and user identity are applied to
    the discovery session exactly as they are for the test session.
    """
    import asyncio

    from asyncua import Client, ua

    from helpers.namespaces import BN, NS_DI, NS_IJT_BASE
    from helpers.node_discovery import find_child_by_browse_name, find_joining_system, read_tool_product_instance_uri

    discovery_data: dict = {
        "endpoint": endpoint,
        "tools": [],
        "processes": [],
        "suggested_yaml": "",
    }

    client = Client(endpoint)
    if security is not None:
        from helpers.connection_security import apply_connection_security

        await apply_connection_security(client, security, prompt=prompt)
    async with asyncio.timeout(timeout):
        await client.connect()
    try:
        import contextlib

        with contextlib.suppress(Exception):
            await client.load_data_type_definitions()
        ns_ijt = await client.get_namespace_index(NS_IJT_BASE)
        ns_di = await client.get_namespace_index(NS_DI)
        js = await find_joining_system(client)
        if not js:
            discovery_data["error"] = "JoiningSystem node not found on server"
            return discovery_data

        # 1. Discover Tool PIU
        piu = await read_tool_product_instance_uri(client, ns_ijt, ns_di)
        if piu:
            discovery_data["tools"].append({"name": "PrimaryTool", "product_instance_uri": piu})

        # 2. Discover Joining Processes via GetJoiningProcessList
        jpm = await find_child_by_browse_name(js, BN.JOINING_PROCESS_MANAGEMENT, ns_ijt)
        if jpm:
            gjpl = await find_child_by_browse_name(jpm, BN.GET_JOINING_PROCESS_LIST, ns_ijt)
            if gjpl:
                call_out = await jpm.call_method(gjpl.nodeid, ua.Variant(piu, ua.VariantType.String))
                procs = (
                    call_out[0]
                    if isinstance(call_out, list) and call_out and isinstance(call_out[0], list)
                    else (call_out if isinstance(call_out, list) else [])
                )
                for p in procs:
                    jid = str(getattr(p, "JoiningProcessId", "") or "")
                    orig = str(getattr(p, "JoiningProcessOriginId", "") or "")
                    pname = str(getattr(p, "Name", "") or "")
                    # 0 = Undefined: do not guess "single" when the server
                    # reports nothing; the name hints decide instead.
                    raw_cls = getattr(p, "Classification", None)
                    try:
                        pcls = int(raw_cls) if raw_cls is not None else 0
                    except (TypeError, ValueError):
                        pcls = 0
                    sel_name = ""
                    for entity in getattr(p, "AssociatedEntities", []) or []:
                        if getattr(entity, "Name", "") == "SelectionName":
                            sel_name = str(getattr(entity, "EntityId", "") or "")
                    discovery_data["processes"].append(
                        {
                            "id": jid,
                            "origin_id": orig,
                            "name": pname,
                            "selection_name": sel_name,
                            "classification": pcls,
                        }
                    )

        # 3. Format suggested YAML snippet.  Classification values follow the
        # canonical ResultClassification enum (1 single, 2 sync, 3 batch,
        # 4 job, 5 stitching, 6 intervention, 7 text) via the shared table in
        # helpers/namespaces.py, so a process is never suggested under two
        # conflicting classification keys.
        discovery_data["suggested_selection"] = suggest_process_selection(discovery_data["processes"])
        discovery_data["suggested_yaml"] = render_suggested_selection_yaml(piu, discovery_data["suggested_selection"])
    finally:
        await client.disconnect()

    return discovery_data


def run_discover_target(
    endpoint: str,
    timeout: float = 15.0,
    *,
    security: ConnectionSecurity | None = None,
    prompt: CredentialPrompt | None = None,
) -> int:
    """CLI runner to discover target server tools and processes and print suggested YAML."""
    import asyncio

    _section(f"Target Server Auto-Discovery: {endpoint}")
    if security is not None:
        from helpers.connection_security import describe_connection_security

        _log(f"  Session security: {describe_connection_security(security)}")
    try:
        data = asyncio.run(async_discover_target_server(endpoint, timeout=timeout, security=security, prompt=prompt))
    except Exception as exc:  # noqa: BLE001
        _log(_c(_ANSI_RED, f"  [ERROR] Discovery failed: {exc}"))
        return 1

    if "error" in data:
        _log(_c(_ANSI_RED, f"  [ERROR] {data['error']}"))
        return 1

    _log(f"  Discovered Tools: {len(data['tools'])}")
    for t in data["tools"]:
        _log(f"    - {t['name']}: {t['product_instance_uri']}")

    _log(f"\n  Discovered Joining Processes: {len(data['processes'])}")
    for p in data["processes"]:
        key = classify_discovered_process(p)
        cls_name = key.capitalize() if key else "Unclassified"
        _log(
            f"    - [{cls_name}] ID: {p['id']} | Origin: {p['origin_id']} | "
            f"SelectionName: {p['selection_name']} | Classification: {p['classification']}"
        )

    _section("Suggested YAML Configuration Snippet")
    _log(data["suggested_yaml"])
    _log("")
    return 0


# ---------------------------------------------------------------------------
# Target server CU evidence reporting helpers
# ---------------------------------------------------------------------------

# Workbook generation outcome vocabulary.  ``skipped`` is reserved for
# deliberate policy decisions; anything that *should* have produced a workbook
# but did not is ``failed`` so the target run cannot report success on missing
# coverage evidence.
EXCEL_STATUS_GENERATED = "generated"
EXCEL_STATUS_SKIPPED = "skipped"
EXCEL_STATUS_FAILED = "failed"

EXCEL_REASON_NONE = ""
EXCEL_REASON_DISABLED = "excel_disabled"
EXCEL_REASON_ON_SUCCESS_AFTER_FAILURE = "on_success_after_failure"
EXCEL_REASON_MISSING_EVIDENCE = "missing_evidence"
EXCEL_REASON_GENERATOR_ERROR = "generator_error"

# Only these reason codes may skip workbook generation without failing the run.
BENIGN_EXCEL_SKIP_REASON_CODES = frozenset(
    {
        EXCEL_REASON_DISABLED,
        EXCEL_REASON_ON_SUCCESS_AFTER_FAILURE,
    }
)


def is_benign_excel_skip(excel_meta: dict) -> bool:
    """Return True when workbook generation was skipped by deliberate policy.

    Any other ``skipped`` result — for example one produced by an older or
    unknown code path — is treated as evidence loss, not as a benign skip.
    """
    if excel_meta.get("status") != EXCEL_STATUS_SKIPPED:
        return False
    return excel_meta.get("reason_code") in BENIGN_EXCEL_SKIP_REASON_CODES


def _generate_excel_report(
    profile: TargetServerCuProfile,
    output_dir: Path,
    target_report_path: Path,
    *,
    run_result: str,
    base_dir: Path | None = None,
    excel_mode: str = "always",
    excel_out: str | Path | None = None,
) -> dict:
    """Generate a workbook from artifacts belonging to this exact target run.

    The workbook is always written inside the run's own ``output_dir`` as
    ``report-controller.xlsx``.  It is copied to a second location only when the
    caller explicitly asked for one via ``--excel-out``; the shared simulator
    workbook at ``test-results/report.xlsx`` is never overwritten implicitly.

    The target run also never passes ``--write-baseline``, so it cannot
    overwrite the shared simulator regression baseline
    (``test-results/report-baseline.json``).

    Every returned dict carries a machine-readable ``reason_code`` so callers
    can distinguish a deliberate policy skip from a broken run without parsing
    the human-readable ``reason`` text.  ``status`` is one of:

      ``generated`` — workbook written;
      ``skipped``   — deliberately not generated (always a benign policy skip);
      ``failed``    — should have been generated but could not be.
    """

    base_dir = base_dir or _HERE
    if excel_mode == "never":
        return {
            "status": EXCEL_STATUS_SKIPPED,
            "reason_code": EXCEL_REASON_DISABLED,
            "reason": "disabled (--excel=never)",
            "path": None,
        }
    if excel_mode == "on-success" and run_result != "passed":
        return {
            "status": EXCEL_STATUS_SKIPPED,
            "reason_code": EXCEL_REASON_ON_SUCCESS_AFTER_FAILURE,
            "reason": "tests failed; skipped (--excel=on-success)",
            "path": None,
        }

    junit_xml = output_dir / "spec-tests.xml"
    cu_report = output_dir / "cu-coverage-report.json"
    workbook = output_dir / "report-controller.xlsx"
    if not junit_xml.exists() or not cu_report.exists():
        missing = [str(p) for p in (junit_xml, cu_report) if not p.exists()]
        return {
            "status": EXCEL_STATUS_FAILED,
            "reason_code": EXCEL_REASON_MISSING_EVIDENCE,
            "reason": (f"run-scoped coverage evidence is missing after a completed spec run: {', '.join(missing)}"),
            "path": None,
            "missing_artifacts": missing,
        }

    script = base_dir / "scripts" / "make_excel_report.py"
    cmd = [
        sys.executable,
        str(script),
        "--xml",
        str(junit_xml),
        "--out",
        str(workbook),
        "--cu-json",
        str(cu_report),
        "--target-report",
        str(target_report_path),
        "--run-result",
        run_result,
    ]
    capabilities = profile.capabilities_file_path()
    if capabilities and capabilities.exists():
        cmd.extend(["--capabilities", str(capabilities)])

    completed = subprocess.run(cmd, cwd=str(base_dir), text=True, capture_output=True)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "unknown report generator error").strip()
        return {
            "status": EXCEL_STATUS_FAILED,
            "reason_code": EXCEL_REASON_GENERATOR_ERROR,
            "reason": detail,
            "path": None,
        }

    generated: dict = {
        "status": EXCEL_STATUS_GENERATED,
        "reason_code": EXCEL_REASON_NONE,
        "reason": "",
        "path": str(workbook),
    }
    if workbook.exists() and excel_out:
        requested = Path(excel_out)
        try:
            requested.parent.mkdir(parents=True, exist_ok=True)
            if requested.resolve() != workbook.resolve():
                shutil.copy2(workbook, requested)
        except Exception as exc:  # noqa: BLE001 — copying is a convenience, not evidence
            logging.getLogger(__name__).warning(
                "Could not copy workbook to requested --excel-out location %s: %s", requested, exc
            )
        else:
            generated["copied_to"] = str(requested)

    return generated


# ---------------------------------------------------------------------------
# Live spec-test orchestration helpers
# ---------------------------------------------------------------------------


def _find_venv_python(base_dir: Path | None = None) -> str:
    """Return the venv Python used for running specification_tests/.

    Prefers the test-runner virtual environment created by run_all_tests.py.
    Falls back to the current interpreter when no venv is found.
    """
    base_dir = base_dir or _HERE
    for venv_name in (".venv_test", ".venv"):
        venv_dir = base_dir / venv_name
        py = venv_dir / ("Scripts" if os.name == "nt" else "bin") / ("python.exe" if os.name == "nt" else "python")
        if py.exists():
            return str(py)
    return sys.executable


def _build_spec_test_env(
    profile: TargetServerCuProfile,
    base_dir: Path | None = None,
    *,
    interactive_prompts: bool = False,
) -> dict[str, str]:
    """Populate environment variables consumed by specification_tests/ fixtures."""
    # Imported lazily: helpers.trigger pulls in asyncua, which is only available
    # inside the test virtual environment.
    from helpers.trigger import ENV_ACTIVE_RESULT_TIMEOUT, ENV_PASSIVE_OBSERVATION_TIMEOUT

    base_dir = base_dir or _HERE
    env = os.environ.copy()
    env["OPCUA_SERVER_URL"] = profile.target.endpoint
    if profile.source_path:
        env["OPCUA_TARGET_SERVER_PROFILE"] = profile.source_path
    env["OPCUA_TARGET_SERVER_MODE"] = profile.cu_execution.default_mode
    # Only an explicitly interactive run may prompt for credentials; unattended
    # runs must fail with a configuration error instead of blocking on stdin.
    if interactive_prompts:
        env["OPCUA_TARGET_INTERACTIVE_PROMPTS"] = "1"
    else:
        env.pop("OPCUA_TARGET_INTERACTIVE_PROMPTS", None)
    runtime_selection = {
        "OPCUA_TOOL_PRODUCT_INSTANCE_URI": profile.selection.tool.product_instance_uri,
        "OPCUA_TOOL_PIU": profile.selection.tool.product_instance_uri,
        "OPCUA_JOINING_PROCESS_ID": profile.selection.joining_process.joining_process_id,
        "OPCUA_JOINING_PROCESS_ORIGIN_ID": profile.selection.joining_process.joining_process_origin_id,
    }
    for name, value in runtime_selection.items():
        if value:
            env[name] = value
        else:
            env.pop(name, None)
    for prefix in ("job", "batch", "single", "sync", "stitching", "intervention"):
        jp = profile.selection.joining_processes.get(prefix)
        if jp:
            if jp.joining_process_id:
                env[f"OPCUA_{prefix.upper()}_JOINING_PROCESS_ID"] = jp.joining_process_id
            if jp.joining_process_origin_id:
                env[f"OPCUA_{prefix.upper()}_JOINING_PROCESS_ORIGIN_ID"] = jp.joining_process_origin_id
    expected_results = profile.workflow_execution.expected_results
    # Two distinct budgets, never conflated:
    #   passive  — evidence observed without the test starting anything.
    #   active   — a joining operation was actually started and a correlated
    #              result/event must arrive; sized for a full workflow cycle.
    passive_timeout = (
        profile.triggers.result.timeout_seconds
        if profile.triggers.result.timeout_seconds > 0
        else (expected_results.timeout_seconds or 10.0)
    )
    active_timeout = (
        expected_results.timeout_seconds if expected_results.timeout_seconds > 0 else max(passive_timeout, 10.0)
    )
    env["OPCUA_TARGET_RESULT_TIMEOUT_SECONDS"] = str(passive_timeout)
    env[ENV_PASSIVE_OBSERVATION_TIMEOUT] = str(passive_timeout)
    env[ENV_ACTIVE_RESULT_TIMEOUT] = str(active_timeout)
    env["OPCUA_TARGET_FINAL_RESULT_REQUIRED"] = str(expected_results.final_result_required).lower()
    required_classification = result_classification_value(expected_results.classification)
    if required_classification is not None:
        env["OPCUA_TARGET_REQUIRED_RESULT_CLASSIFICATION"] = str(required_classification)
    else:
        env.pop("OPCUA_TARGET_REQUIRED_RESULT_CLASSIFICATION", None)

    # The SUT manifest is its own claim source. When a run has no manifest (ad hoc
    # --endpoint), leave OPCUA_CAPABILITIES_FILE unset so every CU is treated as
    # applicable rather than silently adopting another server's claims.
    caps = profile.capabilities_file_path()
    if caps and caps.exists():
        env["OPCUA_CAPABILITIES_FILE"] = str(caps)

    excluded_cus = _excluded_cus_for_result_scope(
        expected_results.classification,
        expected_results.intermediate_classifications,
        configured_classifications=tuple(profile.selection.joining_processes.keys()),
    )
    if excluded_cus:
        env["OPCUA_TARGET_EXCLUDED_CUS"] = ",".join(sorted(excluded_cus))
    else:
        env.pop("OPCUA_TARGET_EXCLUDED_CUS", None)
    return env


def _build_spec_test_command(
    python_exe: str,
    spec_dir: Path,
    junit_xml: Path,
    *,
    exclude_simulation: bool = True,
    test_timeout_seconds: int = 120,
    verbose: bool = False,
) -> list[str]:
    """Build the pytest command for a target server specification_tests/ run.

    Parameters
    ----------
    python_exe:
        Path to the Python interpreter to use.
    spec_dir:
        Path to the specification_tests/ directory.
    junit_xml:
        Output path for the JUnit XML evidence file.
    exclude_simulation:
        When True, adds ``-m "not simulation"`` to skip simulator-only tests.
        Simulator tests skip naturally via conftest fixture anyway, but explicit
        exclusion is faster and produces clearer output.
    test_timeout_seconds:
        Per-test pytest timeout, sized for the configured target workflow.
    verbose:
        When True, passes ``-v`` instead of ``-q`` to pytest.
    """
    cmd: list[str] = [
        python_exe,
        # Unbuffered so live progress is visible while a slow target run streams.
        "-u",
        "-m",
        "pytest",
        str(spec_dir),
        "--tb=short",
        "-v" if verbose else "-q",
        f"--junit-xml={junit_xml}",
        f"--timeout={test_timeout_seconds}",
    ]
    if exclude_simulation:
        cmd += ["-m", "not simulation"]
    return cmd


def run_live_spec_tests(
    profile: TargetServerCuProfile,
    output_dir: Path,
    *,
    mode: str = "automated",
    timeout_seconds: int = 600,
    verbose: bool = False,
    base_dir: Path | None = None,
    interactive_prompts: bool = False,
) -> tuple[int, dict]:
    """Invoke specification_tests/ against the configured target server.

    This is the single live execution path for both the simulator (default
    ``run_all_tests.py`` Phase 2) and a real Target Server (``--profile``).
    It runs the full specification_tests/ pytest suite with OPCUA_SERVER_URL
    and OPCUA_CAPABILITIES_FILE set from the profile, and records evidence in
    the output directory.

    Returns ``(exit_code, metadata)`` where ``metadata`` is a JSON-serialisable
    dict included in the evidence report.  Returns ``(0, {"status": "skipped",
    ...})`` when the endpoint is a placeholder or specification_tests/ is missing.

    Parameters
    ----------
    profile:
        Loaded Target Server profile; must have ``target.endpoint`` configured.
    output_dir:
        Directory where the JUnit XML and other evidence will be written.
    mode:
        Execution mode label for logging only.
    timeout_seconds:
        Hard limit for the pytest subprocess.  Real joining operations can be
        slow; 600 s is a reasonable default for automated Target Server runs.
    verbose:
        Pass ``-v`` to pytest (instead of ``-q``) for detailed per-test output.
    base_dir:
        Project root used to locate specification_tests/ and the venv Python.
        Defaults to the IJT_Test_Client project root; overridable for tests.
    """
    base_dir = base_dir or _HERE
    endpoint = profile.target.endpoint

    # Placeholder or unconfigured endpoint — classification-only run is still useful.
    if not endpoint or "<" in endpoint:
        _log("  Endpoint not configured — live specification_tests run skipped.")
        _log("  Set target.endpoint in the profile or pass --endpoint <url> to run live tests.")
        return 0, {"status": "skipped", "reason": "endpoint_not_configured"}

    spec_dir = base_dir / "specification_tests"
    if not spec_dir.exists():
        _log("  specification_tests/ directory not found — live run skipped.")
        return 0, {"status": "skipped", "reason": "spec_dir_not_found"}

    python_exe = _find_venv_python(base_dir)
    env = _build_spec_test_env(profile, base_dir=base_dir, interactive_prompts=interactive_prompts)

    # Exclude simulator-only tests when the profile does not use simulate_methods.
    # The conftest fixture would skip them anyway (SimulateResults folder absent),
    # but explicit exclusion avoids the fixture error and speeds up collection.
    exclude_simulation = profile.triggers.result.mode not in {"simulate_methods"}

    output_dir.mkdir(parents=True, exist_ok=True)
    junit_xml = output_dir / "spec-tests.xml"
    cu_report = output_dir / "cu-coverage-report.json"
    env["IJT_CU_COVERAGE_REPORT_FILE"] = str(cu_report)

    cmd = _build_spec_test_command(
        python_exe,
        spec_dir,
        junit_xml,
        exclude_simulation=exclude_simulation,
        test_timeout_seconds=math.ceil(
            min(
                timeout_seconds,
                max(
                    120,
                    (
                        4 * profile.cu_execution.default_timeout_seconds
                        + profile.workflow_execution.expected_operation_count
                        * (
                            profile.cu_execution.default_timeout_seconds
                            + profile.workflow_execution.expected_results.timeout_seconds
                        )
                        + 30
                    ),
                ),
            ),
        ),
        verbose=verbose,
    )

    _log(f"\n  Python:           {python_exe}")
    _log(f"  Test suite:       {spec_dir.name}/")
    _log(f"  OPCUA_SERVER_URL: {endpoint}")
    _log(f"  Capabilities:     {env.get('OPCUA_CAPABILITIES_FILE', '(none)')}")
    _log(f"  JUnit XML:        {junit_xml}")
    _log(f"  Timeout:          {timeout_seconds}s")
    if exclude_simulation:
        _log("  Marker filter:    not simulation")
    _log("")

    t0 = time.monotonic()
    rc = 1
    timed_out = False
    error_msg: str | None = None

    try:
        result = subprocess.run(
            cmd,
            cwd=str(base_dir),
            env=env,
            check=False,
            timeout=timeout_seconds,
        )
        rc = result.returncode
    except subprocess.TimeoutExpired:
        _log(_c(_ANSI_RED, f"\n  [TIMEOUT] Spec tests exceeded {timeout_seconds}s — terminated."))
        timed_out = True
        rc = 1
    except Exception as exc:  # noqa: BLE001
        error_msg = str(exc)
        _log(_c(_ANSI_RED, f"\n  [ERROR] Failed to run spec tests: {exc}"))
        rc = 1

    elapsed = time.monotonic() - t0

    metadata: dict = {
        "status": "timeout" if timed_out else ("error" if error_msg else "completed"),
        "outcome": "passed" if rc == 0 else "failed",
        "exit_code": rc,
        "elapsed_seconds": round(elapsed, 1),
        "endpoint": endpoint,
        "junit_xml": str(junit_xml) if junit_xml.exists() else None,
        "cu_coverage_json": str(cu_report) if cu_report.exists() else None,
        "excluded_simulation": exclude_simulation,
        "mode": mode,
    }
    if error_msg:
        metadata["error"] = error_msg
    return rc, metadata


# ---------------------------------------------------------------------------
# Preflight runner
# ---------------------------------------------------------------------------


def run_preflight(profile: TargetServerCuProfile, output_dir: Path) -> int:
    """Run config + TCP preflight checks and produce an evidence report.

    Returns 0 when all checks pass or produce non-blocking outcomes,
    1 when blocking or configuration-error outcomes are found.
    """
    _section("Configuration preflight")
    cfg_report = run_config_preflight(profile)

    # Add TCP reachability probe for configured endpoint
    tcp_check = check_endpoint_reachable(profile.target.endpoint)
    cfg_report.add(tcp_check)

    for check in cfg_report.checks:
        _print_check(check)

    _divider()
    blocking = cfg_report.blocking_checks
    manual_required = cfg_report.manual_required_checks

    if blocking:
        _log(_c(_ANSI_RED, f"  {len(blocking)} blocking issue(s) found — fix before running."))
    elif manual_required:
        _log(_c(_ANSI_YELLOW, f"  {len(manual_required)} check(s) require manual operator action."))
    else:
        _log(_c(_ANSI_GREEN, "  All preflight checks passed."))

    outcome_summary = (
        f"BLOCKING ({len(blocking)} issues)"
        if blocking
        else f"MANUAL_REQUIRED ({len(manual_required)} checks)"
        if manual_required
        else "PASSED"
    )

    run_start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    report_path = _write_evidence_report(output_dir, profile, cfg_report, "preflight_only", run_start)
    summary_path = _write_human_summary(output_dir, profile, cfg_report, "preflight_only", run_start, outcome_summary)
    md_summary_path = _write_markdown_summary(
        output_dir, profile, cfg_report, "preflight_only", run_start, outcome_summary
    )

    _log(f"\n  Evidence report: {report_path}")
    _log(f"  Human summary:   {summary_path}")
    _log(f"  Markdown report: {md_summary_path}")

    return 1 if blocking else 0


# ---------------------------------------------------------------------------
# Automated / guided runner
# ---------------------------------------------------------------------------


def _capture_model_inventory(profile: TargetServerCuProfile, output_dir: Path) -> dict:
    """Capture required read-only Phase 2 model evidence for one target."""
    from helpers.connection_security import (
        ConnectionSecurity,
        connection_security_from_manifest_path,
    )
    from helpers.model_inventory import write_model_inventory

    endpoint = profile.target.endpoint
    security = ConnectionSecurity(endpoint=endpoint)
    source_path = Path(profile.source_path)
    if source_path.name.endswith(".sut.yaml") and source_path.is_file():
        security = connection_security_from_manifest_path(source_path)
    inventory_path = output_dir / "model-inventory.json"
    inventory = write_model_inventory(endpoint, inventory_path, timeout=15.0, security=security)
    return {
        "status": "completed" if inventory["complete"] else "inconclusive",
        "path": str(inventory_path),
        "server_node_count": inventory["server_inventory"]["node_count"],
        "warning_count": len(inventory["server_inventory"]["warnings"]),
    }


def run_automated(
    profile: TargetServerCuProfile,
    output_dir: Path,
    *,
    mode: str = "automated",
    interactive_prompts: bool = False,
    skip_spec_tests: bool = False,
    spec_tests_timeout: int = 600,
    verbose: bool = False,
    base_dir: Path | None = None,
    excel_mode: str = "always",
    excel_out: str | Path | None = None,
) -> int:
    """Run Target Server CU validation in automated or guided mode.

    Workflow:

    1. Configuration and TCP preflight.
    2. CU classification — which CUs can/cannot run for this profile.
    3. Live specification_tests/ run (when endpoint is configured and reachable).
       Pass ``skip_spec_tests=True`` (CLI: ``--skip-spec-tests``) to produce a
       classification-only report without running live tests.

    Returns 0 on success, 1 on configuration errors, blocking preflight issues,
    spec test failures, or missing/failed run-scoped coverage evidence.

    ``excel_mode`` and ``excel_out`` mirror the ``--excel``/``--excel-out`` CLI
    flags: ``never`` disables workbook generation entirely, ``on-success`` skips
    it after failures, and ``excel_out`` names an additional copy destination.
    Only those two deliberate policy skips are benign; a workbook that should
    have been produced but could not be (for example because the JUnit XML or
    run-scoped CU coverage JSON is missing) fails the target run.
    """
    _section(f"Target Server CU run ({mode})")

    cfg_report = run_config_preflight(profile, allow_prompt=interactive_prompts or mode == "guided")
    tcp_check = check_endpoint_reachable(profile.target.endpoint)
    cfg_report.add(tcp_check)

    for check in cfg_report.checks:
        _print_check(check)

    blocking = cfg_report.blocking_checks
    if blocking:
        _log(_c(_ANSI_RED, f"\n  {len(blocking)} blocking issue(s) — cannot proceed:"))
        for c in blocking:
            _log(f"    [{c.outcome}] {c.check_name}: {c.detail}")
        run_start = datetime.datetime.now(datetime.timezone.utc).isoformat()
        _write_evidence_report(output_dir, profile, cfg_report, mode, run_start)
        return 1

    manual_checks = cfg_report.manual_required_checks
    if manual_checks and mode == "automated":
        _log(
            _c(
                _ANSI_YELLOW,
                f"\n  {len(manual_checks)} check(s) require manual action — will be skipped in automated mode.",
            )
        )
    elif manual_checks and mode == "guided":
        _log(_c(_ANSI_YELLOW, f"\n  {len(manual_checks)} check(s) require manual action."))
        if interactive_prompts:
            for c in manual_checks:
                _log(f"\n  [MANUAL REQUIRED] {c.check_name}")
                _log(f"  Action: {c.detail}")
                try:
                    input("  Press Enter when ready to continue... ")
                except (EOFError, KeyboardInterrupt):
                    _log("  Guided run interrupted.")
                    return 1

    # Classify what would run
    from helpers.cu_evidence_map import cus_by_evidence_kind

    _section("Expected CU execution classification")
    trigger_mode = profile.triggers.result.mode

    structural_cus = cus_by_evidence_kind("structure")
    method_cus = cus_by_evidence_kind("method")
    result_cus = cus_by_evidence_kind("result")
    consolidated_cus = cus_by_evidence_kind("consolidated_result")
    event_cus = cus_by_evidence_kind("event")
    manual_cus = cus_by_evidence_kind("manual")

    _log(f"  Structure CUs      : {len(structural_cus)} — runnable directly via address-space browse")
    _log(f"  Method CUs         : {len(method_cus)} — runnable via OPC UA method calls")
    _log(f"  Result CUs         : {len(result_cus)} — require trigger mode: {trigger_mode}")
    _log(f"  Consolidated CUs   : {len(consolidated_cus)} — require batch/sync/job trigger")
    _log(f"  Event CUs          : {len(event_cus)} — require event trigger (mode: {profile.triggers.event.mode})")
    _log(f"  Manual-only CUs    : {len(manual_cus)} — require physical operator action")

    workflow_cus = cus_by_evidence_kind("workflow")
    optional_cus = cus_by_evidence_kind("optional_operation")
    negative_cus = cus_by_evidence_kind("negative_path")
    _log(f"  Workflow CUs       : {len(workflow_cus)} — require joining workflow execution")
    _log(f"  Optional CUs       : {len(optional_cus)} — gated by profile support")
    _log(f"  Negative-path CUs  : {len(negative_cus)} — require explicit state-changing opt-in")

    run_start = datetime.datetime.now(datetime.timezone.utc).isoformat()

    extra: dict = {
        "cu_classification": {
            "structure": len(structural_cus),
            "method": len(method_cus),
            "result": len(result_cus),
            "consolidated_result": len(consolidated_cus),
            "event": len(event_cus),
            "workflow": len(workflow_cus),
            "optional_operation": len(optional_cus),
            "negative_path": len(negative_cus),
            "manual": len(manual_cus),
        }
    }

    # Always capture the server's address space before Phase 2 methods can
    # change state. Inventory browsing never reads values or calls methods.
    endpoint = profile.target.endpoint
    if endpoint and "<" not in endpoint:
        try:
            extra["model_inventory"] = _capture_model_inventory(profile, output_dir)
            _log(
                f"  Model inventory    : {extra['model_inventory']['status']} "
                f"({extra['model_inventory']['server_node_count']} server nodes)"
            )
        except Exception as exc:  # noqa: BLE001 - convert inventory failure into explicit run evidence
            extra["model_inventory"] = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}
            _log(_c(_ANSI_RED, f"  Model inventory    : FAILED — {exc}"))

    # ── Live specification_tests/ run ──────────────────────────────────────
    spec_rc = 0
    spec_meta: dict | None = None
    inventory_failed = extra.get("model_inventory", {}).get("status") == "failed"
    if skip_spec_tests:
        _log("\n  Live specification_tests run skipped (--skip-spec-tests).")
        _log(f"  To run live tests: omit --skip-spec-tests (endpoint: {endpoint or '<not set>'})")
        outcome_summary = "CLASSIFICATION_ONLY"
    elif endpoint and "<" not in endpoint:
        _section("Live specification_tests run (Target Server)")
        spec_rc, spec_meta = run_live_spec_tests(
            profile,
            output_dir,
            mode=mode,
            timeout_seconds=spec_tests_timeout,
            verbose=verbose,
            base_dir=base_dir,
            interactive_prompts=interactive_prompts,
        )
        extra["spec_tests"] = spec_meta
        if spec_meta.get("status") == "completed":
            if spec_rc == 0:
                outcome_summary = "SPEC_TESTS_PASSED"
                _log(_c(_ANSI_GREEN, "\n  Live specification_tests: PASSED"))
            else:
                outcome_summary = "SPEC_TESTS_FAILED"
                _log(_c(_ANSI_RED, "\n  Live specification_tests: FAILED"))
        else:
            outcome_summary = f"SPEC_TESTS_{spec_meta.get('status', 'UNKNOWN').upper()}"
            _log(f"\n  Live specification_tests: {spec_meta.get('status', 'unknown')}")
    else:
        outcome_summary = "CLASSIFICATION_ONLY"
        _log("\n  Endpoint not configured — live specification_tests run skipped.")
        _log("  Configure target.endpoint in the profile or pass --endpoint <url>.")

    if inventory_failed:
        spec_rc = spec_rc or 1
        outcome_summary = "MODEL_INVENTORY_FAILED"

    report_path = _write_evidence_report(output_dir, profile, cfg_report, mode, run_start, extra)
    summary_path = _write_human_summary(output_dir, profile, cfg_report, mode, run_start, outcome_summary)
    md_summary_path = _write_markdown_summary(output_dir, profile, cfg_report, mode, run_start, outcome_summary, extra)
    if spec_meta and spec_meta.get("status") == "completed":
        excel_meta = _generate_excel_report(
            profile,
            output_dir,
            report_path,
            run_result="passed" if spec_rc == 0 else "failed",
            base_dir=base_dir,
            excel_mode=excel_mode,
            excel_out=excel_out,
        )
        extra["excel_report"] = excel_meta
        report_path = _write_evidence_report(output_dir, profile, cfg_report, mode, run_start, extra)
        md_summary_path = _write_markdown_summary(
            output_dir, profile, cfg_report, mode, run_start, outcome_summary, extra
        )
        if excel_meta["status"] == EXCEL_STATUS_GENERATED:
            _log(f"  Excel report:    {excel_meta['path']}")
            if excel_meta.get("copied_to"):
                _log(f"  Excel copy:      {excel_meta['copied_to']}")
        elif is_benign_excel_skip(excel_meta):
            _log(f"  Excel report:    skipped — {excel_meta['reason']}")
        else:
            _log(
                _c(
                    _ANSI_RED,
                    f"  Excel report:    {excel_meta['status']} — {excel_meta.get('reason') or 'no reason reported'}",
                )
            )
            _log(
                _c(
                    _ANSI_RED,
                    "  Coverage evidence for this run is incomplete — the target run cannot be reported as passed.",
                )
            )
            spec_rc = spec_rc or 1

    _log(f"\n  Evidence report: {report_path}")
    _log(f"  Human summary:   {summary_path}")
    _log(f"  Markdown report: {md_summary_path}")
    _log("")

    if spec_rc != 0:
        _log(
            _c(
                _ANSI_RED,
                "  Target Server CU run FAILED — spec tests had failures/errors, "
                "or run-scoped coverage evidence could not be produced.",
            )
        )
        return 1

    if spec_meta and spec_meta.get("status") == "skipped":
        _log(_c(_ANSI_YELLOW, "  Target Server CU classification complete (spec tests skipped)."))
    elif spec_meta is None and not skip_spec_tests:
        _log(_c(_ANSI_YELLOW, "  Target Server CU classification complete (no endpoint configured)."))
    else:
        _log(_c(_ANSI_GREEN, "  Target Server CU run complete."))
    return 0
