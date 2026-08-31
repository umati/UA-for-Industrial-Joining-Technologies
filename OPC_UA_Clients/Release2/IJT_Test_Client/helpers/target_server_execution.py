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
        "",
        "## Preflight Checks",
        "",
        "| Check Name | Status | Detail |",
        "|---|:---:|---|",
    ]
    for check in preflight_report.checks:
        status_icon = (
            "✅" if check.outcome == OUTCOME_PASSED else ("⚠️" if check.outcome == OUTCOME_MANUAL_REQUIRED else "❌")
        )
        lines.append(f"| `{check.check_name}` | {status_icon} `{check.outcome}` | {check.detail} |")

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


async def async_discover_target_server(endpoint: str, timeout: float = 15.0) -> dict:
    """Connect to a target OPC UA server, discover Tools and Joining Processes, and return structured metadata."""
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
                    pcls = int(getattr(p, "Classification", 1) or 1)
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

        # 3. Format suggested YAML snippet
        single_p = next(
            (
                p
                for p in discovery_data["processes"]
                if p["classification"] in (1, 2)
                or "program" in p["name"].lower()
                or "program" in p["selection_name"].lower()
            ),
            None,
        )
        job_p = next(
            (
                p
                for p in discovery_data["processes"]
                if p["classification"] in (3, 4, 5)
                or "job" in p["name"].lower()
                or "sequence" in p["name"].lower()
                or "sequence" in p["selection_name"].lower()
            ),
            None,
        )
        batch_p = next(
            (
                p
                for p in discovery_data["processes"]
                if p["classification"] == 3 or "batch" in p["name"].lower() or "batch" in p["selection_name"].lower()
            ),
            None,
        )

        yaml_lines = [
            "selection:",
            "  tool:",
            "    policy: first_ready",
            f'    product_instance_uri: "{piu}"',
            "  joining_processes:",
            "    single:",
            "      policy: exact_match",
            f'      joining_process_id: "{single_p["id"] if single_p else ""}"',
            f'      joining_process_origin_id: "{single_p["origin_id"] if single_p else ""}"',
            f'      selection_name: "{single_p["selection_name"] if single_p else ""}"',
            "    job:",
            "      policy: exact_match",
            f'      joining_process_id: "{job_p["id"] if job_p else ""}"',
            f'      joining_process_origin_id: "{job_p["origin_id"] if job_p else ""}"',
            f'      selection_name: "{job_p["selection_name"] if job_p else ""}"',
            "    batch:",
            "      policy: exact_match",
            f'      joining_process_id: "{batch_p["id"] if batch_p else ""}"',
            f'      joining_process_origin_id: "{batch_p["origin_id"] if batch_p else ""}"',
            f'      selection_name: "{batch_p["selection_name"] if batch_p else ""}"',
        ]
        discovery_data["suggested_yaml"] = "\n".join(yaml_lines)
    finally:
        await client.disconnect()

    return discovery_data


def run_discover_target(endpoint: str, timeout: float = 15.0) -> int:
    """CLI runner to discover target server tools and processes and print suggested YAML."""
    import asyncio

    _section(f"Target Server Auto-Discovery: {endpoint}")
    try:
        data = asyncio.run(async_discover_target_server(endpoint, timeout=timeout))
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
        cls_name = {1: "Single", 2: "Batch", 3: "Job", 4: "Job", 5: "Stitching", 6: "Intervention"}.get(
            p["classification"], "Other"
        )
        _log(f"    - [{cls_name}] ID: {p['id']} | Origin: {p['origin_id']} | SelectionName: {p['selection_name']}")

    _section("Suggested YAML Configuration Snippet")
    _log(data["suggested_yaml"])
    _log("")
    return 0


# ---------------------------------------------------------------------------
# Target server CU evidence reporting helpers
# ---------------------------------------------------------------------------


def _generate_excel_report(
    profile: TargetServerCuProfile,
    output_dir: Path,
    target_report_path: Path,
    *,
    run_result: str,
    base_dir: Path | None = None,
) -> dict:
    """Generate a workbook from artifacts belonging to this exact target run."""

    base_dir = base_dir or _HERE
    junit_xml = output_dir / "spec-tests.xml"
    cu_report = output_dir / "cu-coverage-report.json"
    workbook = output_dir / "report-controller.xlsx"
    default_workbook = base_dir / "test-results" / "report.xlsx"
    if not junit_xml.exists() or not cu_report.exists():
        return {
            "status": "skipped",
            "reason": "JUnit XML or run-scoped CU coverage JSON is unavailable",
            "path": None,
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
        return {"status": "failed", "reason": detail, "path": None}

    if workbook.exists():
        try:
            default_workbook.parent.mkdir(parents=True, exist_ok=True)
            if default_workbook.resolve() != workbook.resolve():
                shutil.copy2(workbook, default_workbook)
        except Exception as exc:
            logging.getLogger(__name__).warning(
                "Could not mirror workbook to default location %s: %s", default_workbook, exc
            )

    return {"status": "generated", "reason": "", "path": str(workbook)}


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
) -> dict[str, str]:
    """Populate environment variables consumed by specification_tests/ fixtures."""
    base_dir = base_dir or _HERE
    env = os.environ.copy()
    env["OPCUA_SERVER_URL"] = profile.target.endpoint
    if profile.source_path:
        env["OPCUA_TARGET_SERVER_PROFILE"] = profile.source_path
    env["OPCUA_TARGET_SERVER_MODE"] = profile.cu_execution.default_mode
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
    # Use result trigger timeout (or default timeout) for individual spec test assertions,
    # reserving the longer expected_results.timeout_seconds for full workflow sequences.
    result_timeout = (
        profile.triggers.result.timeout_seconds
        if profile.triggers.result.timeout_seconds > 0
        else (expected_results.timeout_seconds or 10)
    )
    env["OPCUA_TARGET_RESULT_TIMEOUT_SECONDS"] = str(result_timeout)
    env["OPCUA_TARGET_FINAL_RESULT_REQUIRED"] = str(expected_results.final_result_required).lower()
    required_classifications = {
        "single": 1,
        "sync": 2,
        "batch": 3,
        "job": 4,
        "stitching": 5,
        "intervention": 6,
        "text": 7,
    }
    required_classification = required_classifications.get(expected_results.classification)
    if required_classification is not None:
        env["OPCUA_TARGET_REQUIRED_RESULT_CLASSIFICATION"] = str(required_classification)
    else:
        env.pop("OPCUA_TARGET_REQUIRED_RESULT_CLASSIFICATION", None)

    caps = profile.capabilities_file_path()
    if caps and caps.exists():
        env["OPCUA_CAPABILITIES_FILE"] = str(caps)
    elif "OPCUA_CAPABILITIES_FILE" not in env:
        default_caps = base_dir / "target_server_cu_profiles" / "default.capabilities.yaml"
        if default_caps.exists():
            env["OPCUA_CAPABILITIES_FILE"] = str(default_caps)

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
        "-u",
        "-m",
        "pytest",
        str(spec_dir),
        "--tb=short",
        "-v",
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
    env = _build_spec_test_env(profile, base_dir=base_dir)

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
) -> int:
    """Run Target Server CU validation in automated or guided mode.

    Workflow:

    1. Configuration and TCP preflight.
    2. CU classification — which CUs can/cannot run for this profile.
    3. Live specification_tests/ run (when endpoint is configured and reachable).
       Pass ``skip_spec_tests=True`` (CLI: ``--skip-spec-tests``) to produce a
       classification-only report without running live tests.

    Returns 0 on success, 1 on configuration errors, blocking preflight issues,
    or spec test failures.
    """
    _section(f"Target Server CU run ({mode})")

    cfg_report = run_config_preflight(profile)
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

    # ── Live specification_tests/ run ──────────────────────────────────────
    spec_rc = 0
    spec_meta: dict | None = None
    endpoint = profile.target.endpoint
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
        )
        extra["excel_report"] = excel_meta
        report_path = _write_evidence_report(output_dir, profile, cfg_report, mode, run_start, extra)
        md_summary_path = _write_markdown_summary(
            output_dir, profile, cfg_report, mode, run_start, outcome_summary, extra
        )
        if excel_meta["status"] == "generated":
            _log(f"  Excel report:    {excel_meta['path']}")
        else:
            _log(_c(_ANSI_RED, f"  Excel report:    {excel_meta['status']} — {excel_meta['reason']}"))
            spec_rc = spec_rc or 1

    _log(f"\n  Evidence report: {report_path}")
    _log(f"  Human summary:   {summary_path}")
    _log(f"  Markdown report: {md_summary_path}")
    _log("")

    if spec_rc != 0:
        _log(_c(_ANSI_RED, "  Target Server CU run FAILED — spec tests had failures or errors."))
        return 1

    if spec_meta and spec_meta.get("status") == "skipped":
        _log(_c(_ANSI_YELLOW, "  Target Server CU classification complete (spec tests skipped)."))
    elif spec_meta is None and not skip_spec_tests:
        _log(_c(_ANSI_YELLOW, "  Target Server CU classification complete (no endpoint configured)."))
    else:
        _log(_c(_ANSI_GREEN, "  Target Server CU run complete."))
    return 0
