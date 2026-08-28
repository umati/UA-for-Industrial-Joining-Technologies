#!/usr/bin/env python3
"""
run_target_server_cu.py — DEPRECATED compatibility shim for IJT Test Client.

.. deprecated::
   This script is a thin, logic-free compatibility forwarder kept only for
   existing scripts and muscle memory.  All behaviour is implemented once in
   ``helpers/target_server_execution.py`` and is also exposed through the
   canonical entry point:

       python run_all_tests.py --profile <FILE> [--preflight-only|--phase2]

   Prefer the canonical entry point for new usage.  This script will keep
   working (it calls the exact same functions) but may be removed in a
   future release.

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
  python run_target_server_cu.py --profile target_server_cu_profiles/template.profile.yaml --endpoint opc.tcp://10.0.0.1:40451 --mode automated

  # Classification only (no live spec tests, even if endpoint is set):
  python run_target_server_cu.py --profile my_profile.yaml --mode automated --skip-spec-tests

  # Guided/manual run with interactive prompts:
  python run_target_server_cu.py --profile my_profile.yaml --mode guided --interactive-prompts

  # Custom output directory:
  python run_target_server_cu.py --profile my_profile.yaml --output-dir test-results/target-server-cu/run-001

  # Use example profiles from the committed examples:
  python run_target_server_cu.py --profile target_server_cu_profiles/example_multi_operation_job.profile.yaml --preflight-only

Environment variables:

  OPCUA_SERVER_URL           Override the endpoint from the profile.
  OPCUA_CAPABILITIES_FILE    Override the capabilities_file from the profile.
  OPCUA_TRIGGER_CLASS        Override the trigger class (preserves existing behaviour).
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
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
# Canonical implementation — imported, never re-implemented here.
# ---------------------------------------------------------------------------

from helpers.target_server_cu_config import (
    TargetServerConfigError,
    TargetServerCuProfile,
    build_default_profile,
    load_target_server_profile,
)
from helpers.target_server_execution import (
    _build_spec_test_command,  # noqa: F401  (re-exported for existing tests)
    _build_spec_test_env,  # noqa: F401  (re-exported for existing tests)
    _c,
    _excluded_cus_for_result_scope,  # noqa: F401  (re-exported for existing tests)
    _log,
    apply_runtime_overrides,
    configure_colour,
    format_error,
    run_automated,
    run_live_spec_tests,  # noqa: F401  (re-exported for existing tests)
    run_preflight,
)

# ---------------------------------------------------------------------------
# Banner (the only CLI-only presentation left in this shim)
# ---------------------------------------------------------------------------


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


def _banner(title: str) -> None:
    width = 54
    bar = "═" * width
    pad = title.ljust(width - 2)
    _log("")
    _log(_c("\033[96m\033[1m", f"╔{bar}╗"))
    _log(_c("\033[96m\033[1m", f"║  {pad}║"))
    _log(_c("\033[96m\033[1m", f"╚{bar}╝"))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "IJT Target Server CU runner — preflight and classification for Target Server CU execution.\n"
            "DEPRECATED: prefer `python run_all_tests.py --profile FILE`.\n"
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
        "--capabilities-file",
        metavar="FILE",
        default=None,
        help="Override capabilities_file; environment: OPCUA_CAPABILITIES_FILE",
    )
    p.add_argument(
        "--tool-product-instance-uri",
        metavar="PIU",
        default=None,
        help="Override the Tool PIU; environment: OPCUA_TOOL_PRODUCT_INSTANCE_URI",
    )
    p.add_argument(
        "--joining-process-id",
        metavar="ID",
        default=None,
        help="Select one discovered JoiningProcess by stable ID; environment: OPCUA_JOINING_PROCESS_ID",
    )
    p.add_argument(
        "--joining-process-origin-id",
        metavar="ID",
        default=None,
        help="Optional stable origin ID; environment: OPCUA_JOINING_PROCESS_ORIGIN_ID",
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
    configure_colour(sys.stdout.isatty() and (os.name != "nt" or _enable_ansi_windows()))

    args = _build_parser().parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    _banner("IJT Target Server CU Runner")
    _log(
        format_error(
            "  [DEPRECATED] run_target_server_cu.py is a compatibility shim. "
            "Prefer: python run_all_tests.py --profile <FILE> "
            "(use --phase2 --profile <FILE> for specification tests only, or --preflight-only for configuration check)."
        )
    )

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
            _log(format_error(f"  [ERROR] Profile file not found: {exc}"))
            return 1
        except TargetServerConfigError as exc:
            _log(format_error(f"  [ERROR] Configuration error: {exc}"))
            return 1
    else:
        # Build a minimal default profile for discovery/smoke runs
        endpoint = args.endpoint or os.environ.get("OPCUA_SERVER_URL", "")
        profile = build_default_profile(endpoint=endpoint)
        _log("  Profile: (default — no --profile specified)")

    # -- Apply CLI/environment overrides ------------------------------------
    profile = apply_runtime_overrides(
        profile,
        endpoint=args.endpoint,
        scoring_mode=args.scoring_mode,
        capabilities_file=args.capabilities_file or os.environ.get("OPCUA_CAPABILITIES_FILE"),
        tool_product_instance_uri=(args.tool_product_instance_uri or os.environ.get("OPCUA_TOOL_PRODUCT_INSTANCE_URI")),
        joining_process_id=args.joining_process_id or os.environ.get("OPCUA_JOINING_PROCESS_ID"),
        joining_process_origin_id=(args.joining_process_origin_id or os.environ.get("OPCUA_JOINING_PROCESS_ORIGIN_ID")),
    )

    # -- Determine output dir -----------------------------------------------
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = profile.output_dir_path(base_dir=_HERE)

    _log(f"  Output:  {output_dir}")

    # -- Apply OPCUA_SERVER_URL override from environment -------------------
    env_url = os.environ.get("OPCUA_SERVER_URL")
    if env_url and not args.endpoint:
        profile = apply_runtime_overrides(profile, endpoint=env_url)
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
