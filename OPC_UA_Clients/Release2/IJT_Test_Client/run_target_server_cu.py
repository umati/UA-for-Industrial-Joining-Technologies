#!/usr/bin/env python3
"""
run_target_server_cu.py — Target Server CU execution runner for IJT Test Client.

Runs conformance unit validation against a real OPC UA IJT server under test using a
Target Server CU profile (YAML).  Produces a structured evidence report in
test-results/target-server-cu/ (or the path set in the profile or --output-dir).

Modes:

  preflight-only  Discover and classify expected outcomes without executing
                  state-changing tests.  Safe to run against any server.

  automated       No manual waits.  When a real endpoint is configured, runs the
                  specification_tests/ pytest suite with OPCUA_SERVER_URL set to
                  the target server and OPCUA_CAPABILITIES_FILE from the profile.
                  Manual-only evidence is skipped with a clear reason.
                  Suitable for unattended CI runs against a target server that
                  supports StartSelectedJoining.

  guided          Interactive prompts and manual waits are allowed for physical
                  tool triggers and operator confirmations.  Like automated mode
                  but may pause for operator action.  Use --interactive-prompts
                  to enable terminal interaction.

Usage:

  # Preflight only — safe for any target server:
  python run_target_server_cu.py --profile target_server_cu_profiles/my_profile.yaml --preflight-only

  # Automated run against a configured target server:
  python run_target_server_cu.py --profile target_server_cu_profiles/my_profile.yaml --mode automated

  # Automated run with a real endpoint override:
  python run_target_server_cu.py --profile template.yaml --endpoint opc.tcp://10.0.0.1:40451 --mode automated

  # Classification only (no live spec tests, even if endpoint is set):
  python run_target_server_cu.py --profile my_profile.yaml --mode automated --skip-spec-tests

  # Guided/manual run with interactive prompts:
  python run_target_server_cu.py --profile my_profile.yaml --mode guided --interactive-prompts

  # Custom output directory:
  python run_target_server_cu.py --profile my_profile.yaml --output-dir test-results/target-server-cu/run-001

  # Use example profiles from the committed examples:
  python run_target_server_cu.py --profile target_server_cu_profiles/example_remote_start.yaml --preflight-only

Environment variables:

  OPCUA_SERVER_URL           Override the endpoint from the profile.
  OPCUA_CAPABILITIES_FILE    Override the capabilities_file from the profile.
  OPCUA_TRIGGER_CLASS        Override the trigger class (preserves existing behaviour).
"""

from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

# Ensure stdout/stderr use UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

_HERE = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run_target_server_cu")
logging.getLogger("asyncua").setLevel(logging.ERROR)

# ---------------------------------------------------------------------------
# Outcome vocabulary (imported from config module)
# ---------------------------------------------------------------------------

from helpers.target_server_cu_config import (
    OUTCOME_BLOCKED,
    OUTCOME_CLAIM_MISMATCH,
    OUTCOME_CONFIGURATION_ERROR,
    OUTCOME_FAILED,
    OUTCOME_MANUAL_REQUIRED,
    OUTCOME_PASSED,
    OUTCOME_UNSUPPORTED,
    TargetServerConfigError,
    TargetServerCuProfile,
    build_default_profile,
    load_target_server_profile,
)
from helpers.target_server_readiness import (
    PreflightReport,
    ReadinessOutcome,
    check_endpoint_reachable,
    run_config_preflight,
)

# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

_USE_COLOUR = False

_ANSI_GREEN = "\033[92m"
_ANSI_RED = "\033[91m"
_ANSI_YELLOW = "\033[93m"
_ANSI_CYAN = "\033[96m\033[1m"
_ANSI_RESET = "\033[0m"


def _enable_ansi_windows() -> bool:
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
            return True
        return False
    except Exception:
        return False


def _c(ansi: str, text: str) -> str:
    return f"{ansi}{text}{_ANSI_RESET}" if _USE_COLOUR else text


def _log(msg: str) -> None:
    sys.stdout.write(msg + "\n")
    sys.stdout.flush()


def _banner(title: str) -> None:
    width = 54
    bar = "═" * width
    pad = title.ljust(width - 2)
    _log("")
    _log(_c(_ANSI_CYAN, f"╔{bar}╗"))
    _log(_c(_ANSI_CYAN, f"║  {pad}║"))
    _log(_c(_ANSI_CYAN, f"╚{bar}╝"))


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


# ---------------------------------------------------------------------------
# Live spec-test orchestration helpers
# ---------------------------------------------------------------------------


def _find_venv_python() -> str:
    """Return the venv Python used for running specification_tests/.

    Prefers the test-runner virtual environment created by run_all_tests.py.
    Falls back to the current interpreter when no venv is found.
    """
    for venv_name in (".venv_test", ".venv"):
        venv_dir = _HERE / venv_name
        py = venv_dir / ("Scripts" if os.name == "nt" else "bin") / ("python.exe" if os.name == "nt" else "python")
        if py.exists():
            return str(py)
    return sys.executable


def _build_spec_test_env(profile: TargetServerCuProfile) -> dict[str, str]:
    """Return env vars for the specification_tests/ subprocess.

    Sets OPCUA_SERVER_URL from the profile endpoint.
    Sets OPCUA_CAPABILITIES_FILE from the profile capabilities_file if resolvable,
    otherwise falls back to the default server_capabilities.yaml next to the runner.
    """
    env = os.environ.copy()
    env["OPCUA_SERVER_URL"] = profile.target.endpoint
    if profile.source_path:
        env["OPCUA_TARGET_SERVER_PROFILE"] = profile.source_path
    env["OPCUA_TARGET_SERVER_MODE"] = profile.cu_execution.default_mode
    caps = profile.capabilities_file_path()
    if caps and caps.exists():
        env["OPCUA_CAPABILITIES_FILE"] = str(caps)
    elif "OPCUA_CAPABILITIES_FILE" not in env:
        default_caps = _HERE / "server_capabilities.yaml"
        if default_caps.exists():
            env["OPCUA_CAPABILITIES_FILE"] = str(default_caps)
    return env


def _build_spec_test_command(
    python_exe: str,
    spec_dir: Path,
    junit_xml: Path,
    *,
    exclude_simulation: bool = True,
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
    verbose:
        When True, passes ``-v`` instead of ``-q`` to pytest.
    """
    cmd: list[str] = [
        python_exe,
        "-m",
        "pytest",
        str(spec_dir),
        "--tb=short",
        "-v" if verbose else "-q",
        f"--junit-xml={junit_xml}",
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
) -> tuple[int, dict]:
    """Invoke specification_tests/ against the configured target server.

    This is the live execution path for automated and guided modes when a real
    target server endpoint is available.  It runs the full specification_tests/
    pytest suite with OPCUA_SERVER_URL and OPCUA_CAPABILITIES_FILE set from the
    profile, and records evidence in the output directory.

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
    """
    endpoint = profile.target.endpoint

    # Placeholder or unconfigured endpoint — classification-only run is still useful.
    if not endpoint or "<" in endpoint:
        _log("  Endpoint not configured — live specification_tests run skipped.")
        _log("  Set target.endpoint in the profile or pass --endpoint <url> to run live tests.")
        return 0, {"status": "skipped", "reason": "endpoint_not_configured"}

    spec_dir = _HERE / "specification_tests"
    if not spec_dir.exists():
        _log("  specification_tests/ directory not found — live run skipped.")
        return 0, {"status": "skipped", "reason": "spec_dir_not_found"}

    python_exe = _find_venv_python()
    env = _build_spec_test_env(profile)

    # Exclude simulator-only tests when the profile does not use simulate_methods.
    # The conftest fixture would skip them anyway (SimulateResults folder absent),
    # but explicit exclusion avoids the fixture error and speeds up collection.
    exclude_simulation = profile.triggers.result.mode not in {"simulate_methods"}

    output_dir.mkdir(parents=True, exist_ok=True)
    junit_xml = output_dir / "spec-tests.xml"

    cmd = _build_spec_test_command(
        python_exe,
        spec_dir,
        junit_xml,
        exclude_simulation=exclude_simulation,
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
            cwd=str(_HERE),
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

    _log(f"\n  Evidence report: {report_path}")
    _log(f"  Human summary:   {summary_path}")

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

    _log(f"\n  Evidence report: {report_path}")
    _log(f"  Human summary:   {summary_path}")
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


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "IJT Target Server CU runner — preflight and classification for Target Server CU execution.\n"
            "Use --preflight-only for safe discovery without state changes."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--profile",
        metavar="FILE",
        help="Path to Target Server CU profile YAML (e.g. target_server_cu_profiles/my_profile.yaml)",
    )
    p.add_argument(
        "--preflight-only",
        action="store_true",
        help="Run configuration and TCP preflight only; do not execute state-changing tests",
    )
    p.add_argument(
        "--mode",
        choices=["automated", "guided", "preflight_only"],
        default="automated",
        help="Execution mode (default: automated)",
    )
    p.add_argument(
        "--scoring-mode",
        choices=["diagnostic", "strict_profile", "acceptance"],
        default=None,
        help="Override the scoring mode from the profile",
    )
    p.add_argument(
        "--output-dir",
        metavar="DIR",
        default=None,
        help="Override the output directory for evidence reports (default: from profile or test-results/target-server-cu)",
    )
    p.add_argument(
        "--interactive-prompts",
        action="store_true",
        help="Enable interactive terminal prompts in guided mode (requires --mode guided)",
    )
    p.add_argument(
        "--endpoint",
        metavar="URL",
        default=None,
        help="Override the endpoint from the profile (e.g. opc.tcp://10.0.0.1:40451)",
    )
    p.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )
    p.add_argument(
        "--skip-spec-tests",
        action="store_true",
        help=(
            "Skip the live specification_tests/ run in automated/guided mode. "
            "Produces a classification-only report without running the live specification_tests/ suite. "
            "Endpoint TCP preflight still runs when an endpoint is configured. "
            "Has no effect in --preflight-only mode."
        ),
    )
    p.add_argument(
        "--spec-tests-timeout",
        metavar="SECONDS",
        type=int,
        default=600,
        help="Timeout in seconds for the live specification_tests/ run (default: 600)",
    )
    return p


def main() -> int:
    """Entry point; returns 0 on success, 1 on errors or blocking preflight issues."""
    global _USE_COLOUR

    _USE_COLOUR = sys.stdout.isatty() and (os.name != "nt" or _enable_ansi_windows())

    args = _build_parser().parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    _banner("IJT Target Server CU Runner")

    # -- Load profile --------------------------------------------------------
    profile: TargetServerCuProfile

    if args.profile:
        profile_path = Path(args.profile)
        if not profile_path.is_absolute():
            profile_path = Path.cwd() / profile_path
        try:
            profile = load_target_server_profile(profile_path)
            _log(f"  Profile: {profile.profile_name}")
            _log(f"  Source:  {profile.source_path}")
        except FileNotFoundError as exc:
            _log(_c(_ANSI_RED, f"  [ERROR] Profile file not found: {exc}"))
            return 1
        except TargetServerConfigError as exc:
            _log(_c(_ANSI_RED, f"  [ERROR] Configuration error: {exc}"))
            return 1
    else:
        # Build a minimal default profile for discovery/smoke runs
        endpoint = args.endpoint or os.environ.get("OPCUA_SERVER_URL", "")
        profile = build_default_profile(endpoint=endpoint)
        _log("  Profile: (default — no --profile specified)")

    # -- Apply CLI overrides ------------------------------------------------
    if args.endpoint:
        # Re-parse with endpoint override (frozen dataclass replacement)
        from dataclasses import replace as _replace

        profile = _replace(profile, target=_replace(profile.target, endpoint=args.endpoint))

    if args.scoring_mode:
        from dataclasses import replace as _replace

        profile = _replace(profile, cu_execution=_replace(profile.cu_execution, scoring_mode=args.scoring_mode))

    # -- Determine output dir -----------------------------------------------
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = profile.output_dir_path(base_dir=_HERE)

    _log(f"  Output:  {output_dir}")

    # -- Apply OPCUA_SERVER_URL override from environment -------------------
    env_url = os.environ.get("OPCUA_SERVER_URL")
    if env_url and not args.endpoint:
        from dataclasses import replace as _replace

        profile = _replace(profile, target=_replace(profile.target, endpoint=env_url))
        _log(f"  Endpoint (env override): {env_url}")

    # -- Run -----------------------------------------------------------------
    mode = "preflight_only" if args.preflight_only else args.mode

    if mode == "preflight_only":
        return run_preflight(profile, output_dir)

    return run_automated(
        profile,
        output_dir,
        mode=mode,
        interactive_prompts=args.interactive_prompts,
        skip_spec_tests=getattr(args, "skip_spec_tests", False),
        spec_tests_timeout=getattr(args, "spec_tests_timeout", 600),
        verbose=args.verbose,
    )


if __name__ == "__main__":
    sys.exit(main())
