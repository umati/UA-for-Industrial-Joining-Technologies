"""
runner_plan — typed immutable run-plan resolution for run_all_tests.py.

Resolves CLI flag combinations, SUT manifest loading, and the
endpoint/claims precedence chain exactly once, before any phase
executes.  This avoids the classic "shared mutable state read at different
times" bug class: every downstream decision (which phases run, whether the
simulator is auto-launched, which endpoint/manifest is used) is
made from a single frozen :class:`RunPlan` instead of re-reading
``os.environ`` or CLI args at scattered call sites.

Precedence (see run_all_tests.py --help and docs/TARGET_SERVER_CU_GUIDE.md):

  Endpoint:      --endpoint > non-placeholder manifest endpoint > OPCUA_SERVER_URL
                 > simulator auto-launch (only when no manifest/external endpoint)
  CU claims:     --capabilities-file > the manifest itself > OPCUA_CAPABILITIES_FILE

``--profile`` now takes one ``*.sut.yaml`` manifest: the paired
``*.profile.yaml`` + ``*.capabilities.yaml`` model was replaced by a single
versioned manifest (see :mod:`helpers.sut_manifest`).

A manifest with an ``external`` lifecycle that still contains ``<placeholder>``
values fails fast here, before any I/O against a real server. A manifest that
resolves to an empty endpoint is never silently downgraded to the simulator:
the Target Server config-preflight machinery (helpers.target_server_readiness)
reports this as a blocking configuration error instead.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Mapping

from helpers.sut_manifest import SutManifest, load_sut_manifest, validate_live_ready
from helpers.target_server_cu_config import (
    TargetServerCuProfile,
    build_default_profile,
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
    manifest: SutManifest | None
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

    Loads and validates the SUT manifest (if any), so this must be
    called only once PyYAML/manifest dependencies are importable (i.e. after
    run_all_tests.py has re-launched itself under its managed venv).

    Raises
    ------
    RunnerConfigError
        For invalid flag combinations (also checked earlier by
        :func:`validate_flag_combinations` for a fast, dependency-free failure),
        or when an external SUT manifest still contains placeholders.
    FileNotFoundError, helpers.sut_manifest.SutManifestError
        Propagated unchanged from manifest loading so callers can report the
        original, specific error message (including the legacy paired-file error).
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
    manifest: SutManifest | None = None
    if profile_path_arg:
        manifest_file = Path(profile_path_arg)
        if not manifest_file.is_absolute():
            manifest_file = Path.cwd() / manifest_file
        manifest = load_sut_manifest(manifest_file)
        if not endpoint_arg:
            issues = validate_live_ready(manifest, env=env)
            if issues:
                raise RunnerConfigError(
                    f"SUT manifest '{manifest_file.name}' is not ready for a live run:\n  - "
                    + "\n  - ".join(issues)
                    + "\nReplace the placeholders (or pass --endpoint) before running against a real server."
                )
        profile = manifest.to_execution_profile()
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
        # Claim-source precedence is CLI > the manifest itself > env: only forward
        # an override when CLI wins outright, or when the profile carries no claim
        # source of its own and env is the only remaining source. This is deliberately
        # different from tool/process selection below, which always let CLI/env win
        # over the manifest (matching the Target Server CLI contract).
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

    # Simulator auto-launch when there is no externally supplied endpoint of any kind:
    # either no manifest at all, or a manifest whose lifecycle says this runner owns the
    # server process. A manifest with an unresolved *external* endpoint is NEVER
    # downgraded to the simulator here - helpers.target_server_readiness reports it as a
    # blocking configuration error via run_preflight/run_automated.
    launch_simulator = endpoint_source == "unset" and (
        not target_evidence_mode or (manifest is not None and manifest.is_auto_simulator)
    )

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
        manifest=manifest,
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


def with_resolved_endpoint(plan: RunPlan, endpoint: str) -> RunPlan:
    """Return a copy of *plan* using *endpoint*, for an auto-launched simulator.

    An ``auto_simulator`` manifest cannot know the port before the runner picks
    one, so the plan stays frozen and the runner replaces the endpoint once the
    simulator is ready. Returns *plan* unchanged when *endpoint* is empty.
    """
    if not endpoint or plan.profile is None:
        return plan
    profile = replace(plan.profile, target=replace(plan.profile.target, endpoint=endpoint))
    return replace(plan, profile=profile, endpoint=endpoint, endpoint_source="simulator")
