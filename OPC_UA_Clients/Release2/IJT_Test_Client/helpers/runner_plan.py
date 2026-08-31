"""
runner_plan — typed immutable run-plan resolution for run_all_tests.py.

Resolves CLI flag combinations, Target Server profile loading, and the
endpoint/capabilities precedence chain exactly once, before any phase
executes.  This avoids the classic "shared mutable state read at different
times" bug class: every downstream decision (which phases run, whether the
simulator is auto-launched, which endpoint/capabilities file is used) is
made from a single frozen :class:`RunPlan` instead of re-reading
``os.environ`` or CLI args at scattered call sites.

Precedence (see run_all_tests.py --help and docs/TARGET_SERVER_CU_GUIDE.md):

  Endpoint:      --endpoint > non-placeholder profile endpoint > OPCUA_SERVER_URL
                 > simulator auto-launch (only when no profile/external endpoint)
  Capabilities:  --capabilities-file > profile capabilities_file > OPCUA_CAPABILITIES_FILE
                 > built-in simulator capability (only when the simulator is launched)

A profile (``--profile`` / deprecated ``--target-server-profile``) that resolves to an
empty/placeholder endpoint is never silently downgraded to the simulator: the
existing Target Server config-preflight machinery (helpers.target_server_readiness)
reports this as a blocking configuration error instead.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from helpers.target_server_cu_config import (
    TargetServerCuProfile,
    build_default_profile,
    load_target_server_profile,
)
from helpers.target_server_execution import apply_runtime_overrides


class RunnerConfigError(ValueError):
    """Raised for invalid CLI flag combinations or an unresolvable profile target."""


def _is_placeholder_endpoint(endpoint: str) -> bool:
    return not endpoint or "<" in endpoint


def validate_flag_combinations(args: argparse.Namespace) -> None:
    """Fail fast on nonsensical flag combinations, before any I/O happens.

    This is pure (no file/network access) so it can run immediately after
    argparse, before the venv bootstrap and profile loading.
    """
    profile_arg = getattr(args, "profile", None)
    deprecated_arg = getattr(args, "target_server_profile", None)
    endpoint_arg = getattr(args, "endpoint", None)

    if profile_arg and deprecated_arg and profile_arg != deprecated_arg:
        raise RunnerConfigError(
            "--profile and --target-server-profile were both given with different values; "
            "--target-server-profile is a deprecated alias for --profile, pass only one."
        )

    if getattr(args, "phase1", False) and (profile_arg or deprecated_arg or endpoint_arg):
        raise RunnerConfigError(
            "--phase1 cannot be combined with --profile/--target-server-profile or --endpoint "
            "(Phase 1 is static analysis only and never starts or contacts a server)."
        )

    if getattr(args, "preflight_only", False) and not (
        profile_arg or deprecated_arg or endpoint_arg or os.environ.get("OPCUA_SERVER_URL")
    ):
        raise RunnerConfigError(
            "--preflight-only requires --profile (or --target-server-profile), --endpoint, "
            "or OPCUA_SERVER_URL to know which Target Server to check."
        )

    timeout = getattr(args, "spec_tests_timeout", None)
    if timeout is not None:
        try:
            t_val = int(timeout)
            if t_val <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            raise RunnerConfigError(f"--spec-tests-timeout must be a positive integer, got '{timeout}'.")


@dataclass(frozen=True)
class RunPlan:
    """Fully-resolved, immutable description of one run_all_tests.py invocation."""

    run_phase1: bool
    run_target: bool
    preflight_only: bool

    profile: TargetServerCuProfile | None
    profile_requested: bool
    used_deprecated_profile_flag: bool
    target_evidence_mode: bool

    endpoint: str
    endpoint_source: str  # "cli" | "profile" | "env" | "unset"
    launch_simulator: bool

    capabilities_file: str | None
    capabilities_source: str  # "cli" | "profile" | "env" | "unset"
    tool_product_instance_uri: str | None
    joining_process_id: str | None
    joining_process_origin_id: str | None

    mode: str
    scoring_mode: str | None
    output_dir: Path | None
    interactive_prompts: bool
    skip_spec_tests: bool
    spec_tests_timeout: int
    verbose: bool
    pytest_args: list[str]


def resolve_run_plan(args: argparse.Namespace, *, env: Mapping[str, str] | None = None) -> RunPlan:
    """Resolve a complete :class:`RunPlan` from parsed CLI args + environment.

    Loads and validates the Target Server profile (if any), so this must be
    called only once PyYAML/profile dependencies are importable (i.e. after
    run_all_tests.py has re-launched itself under its managed venv).

    Raises
    ------
    RunnerConfigError
        For invalid flag combinations (also checked earlier by
        :func:`validate_flag_combinations` for a fast, dependency-free failure).
    FileNotFoundError, helpers.target_server_cu_config.TargetServerConfigError
        Propagated unchanged from profile loading so callers can report the
        original, specific error message.
    """
    env = os.environ if env is None else env
    validate_flag_combinations(args)

    profile_arg: str | None = getattr(args, "profile", None)
    deprecated_arg: str | None = getattr(args, "target_server_profile", None)
    used_deprecated_profile_flag = bool(deprecated_arg) and not profile_arg
    profile_path_arg = profile_arg or deprecated_arg

    cli_capabilities = getattr(args, "capabilities_file", None)
    tool_piu_override = getattr(args, "tool_product_instance_uri", None) or env.get("OPCUA_TOOL_PRODUCT_INSTANCE_URI")
    jp_id_override = getattr(args, "joining_process_id", None) or env.get("OPCUA_JOINING_PROCESS_ID")
    jp_origin_override = getattr(args, "joining_process_origin_id", None) or env.get("OPCUA_JOINING_PROCESS_ORIGIN_ID")
    endpoint_arg: str | None = getattr(args, "endpoint", None)
    scoring_mode_arg: str | None = getattr(args, "scoring_mode", None)

    profile: TargetServerCuProfile | None = None
    if profile_path_arg:
        profile_file = Path(profile_path_arg)
        if not profile_file.is_absolute():
            profile_file = Path.cwd() / profile_file
        profile = load_target_server_profile(profile_file)
    elif endpoint_arg:
        # No profile file, but an explicit endpoint was given: build a minimal
        # default profile so the same run_preflight/run_automated execution
        # path (with full target evidence) is used — one execution path for
        # both ad hoc endpoints and profile-driven runs.
        profile = build_default_profile(endpoint=endpoint_arg)
    elif getattr(args, "preflight_only", False):
        # --preflight-only with neither --profile nor --endpoint is only valid
        # (per validate_flag_combinations) when OPCUA_SERVER_URL is set; build a
        # default profile from it so preflight has a target to check.
        profile = build_default_profile(endpoint=str(env.get("OPCUA_SERVER_URL", "")))

    if profile is not None:
        # Capabilities precedence is CLI > profile's own value > env: only forward
        # an override when CLI wins outright, or when the profile has no capabilities
        # file of its own and env is the only remaining source. This is deliberately
        # different from tool/process selection below, which always let CLI/env win
        # over the profile (matching the Target Server CLI contract).
        profile_had_own_capabilities = bool(profile.capabilities_file)
        capabilities_override = cli_capabilities
        if not capabilities_override and not profile_had_own_capabilities:
            capabilities_override = env.get("OPCUA_CAPABILITIES_FILE")
        profile = apply_runtime_overrides(
            profile,
            endpoint=endpoint_arg,
            scoring_mode=scoring_mode_arg,
            capabilities_file=capabilities_override,
            tool_product_instance_uri=tool_piu_override,
            joining_process_id=jp_id_override,
            joining_process_origin_id=jp_origin_override,
        )
    else:
        profile_had_own_capabilities = False

    target_evidence_mode = profile is not None

    # -- Endpoint precedence: CLI > non-placeholder profile file > OPCUA_SERVER_URL > unset --
    if endpoint_arg:
        endpoint, endpoint_source = endpoint_arg, "cli"
    elif profile_path_arg and profile is not None and not _is_placeholder_endpoint(profile.target.endpoint):
        endpoint, endpoint_source = profile.target.endpoint, "profile"
    elif env.get("OPCUA_SERVER_URL"):
        endpoint, endpoint_source = str(env["OPCUA_SERVER_URL"]), "env"
    else:
        endpoint, endpoint_source = "", "unset"

    # Simulator auto-launch only when there is no profile and no externally
    # supplied endpoint of any kind. A profile with an unresolved endpoint is
    # NEVER downgraded to the simulator here — helpers.target_server_readiness
    # reports it as a blocking configuration error via run_preflight/run_automated.
    launch_simulator = endpoint_source == "unset" and not target_evidence_mode

    # -- Capabilities precedence: CLI > profile > env > unset (simulator default applied later) --
    # Uses profile_had_own_capabilities (captured before apply_runtime_overrides) so an
    # env-sourced value forwarded into the profile above is still correctly labelled "env".
    if cli_capabilities:
        capabilities_source = "cli"
    elif profile_had_own_capabilities:
        capabilities_source = "profile"
    elif env.get("OPCUA_CAPABILITIES_FILE"):
        capabilities_source = "env"
    else:
        capabilities_source = "unset"
    capabilities_file = (
        profile.capabilities_file if profile is not None else (cli_capabilities or env.get("OPCUA_CAPABILITIES_FILE"))
    )

    # -- Phase selection --
    if getattr(args, "preflight_only", False):
        run_phase1, run_target, preflight_only = False, True, True
    elif getattr(args, "phase1", False):
        run_phase1, run_target, preflight_only = True, False, False
    elif getattr(args, "phase2", False):
        run_phase1, run_target, preflight_only = False, True, False
    else:
        run_phase1, run_target, preflight_only = True, True, False

    output_dir_arg = getattr(args, "output_dir", None)

    return RunPlan(
        run_phase1=run_phase1,
        run_target=run_target,
        preflight_only=preflight_only,
        profile=profile,
        profile_requested=bool(profile_path_arg),
        used_deprecated_profile_flag=used_deprecated_profile_flag,
        target_evidence_mode=target_evidence_mode,
        endpoint=endpoint,
        endpoint_source=endpoint_source,
        launch_simulator=launch_simulator,
        capabilities_file=capabilities_file,
        capabilities_source=capabilities_source,
        tool_product_instance_uri=tool_piu_override,
        joining_process_id=jp_id_override,
        joining_process_origin_id=jp_origin_override,
        mode=getattr(args, "mode", "automated"),
        scoring_mode=scoring_mode_arg,
        output_dir=Path(output_dir_arg) if output_dir_arg else None,
        interactive_prompts=bool(getattr(args, "interactive_prompts", False)),
        skip_spec_tests=bool(getattr(args, "skip_spec_tests", False)),
        spec_tests_timeout=int(getattr(args, "spec_tests_timeout", 600)),
        verbose=bool(getattr(args, "verbose", False)),
        pytest_args=list(getattr(args, "pytest_args", None) or []),
    )
