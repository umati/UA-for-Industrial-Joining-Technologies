#!/usr/bin/env python3
"""
run_fleet.py — Standalone multi-server fleet benchmark launcher for IJT Performance Client.

Orchestrates N local OPC UA server simulator instances, executes the Performance Client
across all endpoints, and prints/saves the latency benchmark report.

Usage (from this client directory):
  python run_fleet.py                              # 50 servers, 10 samples/server, report & stop
  python run_fleet.py --servers 5 -w 2 --samples-per-server 3   # quick smoke
  python run_fleet.py --servers 25                 # 25 servers (250 samples)
  python run_fleet.py --start-port 41001           # avoid reserved live/CI ports when scaling up
  python run_fleet.py --keep-running               # leave sims up; press Enter to stop
  python run_fleet.py --profile profiles/work_pc_colocated.yaml
  python run_fleet.py --role serve-fleet --advertise-host <LAN-IP> --profile profiles/serve_fleet.yaml
  python run_fleet.py --role client-only --inventory-source test-results/fleet-inventory.json \\
      --profile profiles/client_only.yaml
  python run_fleet.py --help

Roles: colocated (default) = sims + client; serve-fleet = sims + inventory only;
client-only = consume inventory (no local sims). See README.md.
"""

from __future__ import annotations

import argparse
import math
import subprocess
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_RESULTS_DIR = _HERE / "test-results"

from run_all_tests import (
    _ENV_IS_PRE_ISOLATED,
    _find_simulator_exe,
    _inside_venv,
    _launch_simulator_fleet,
    _print_status,
    _relaunch_under_venv,
    _stop_simulators,
)

_RUNTIME_VENV = _HERE / ".venv"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="IJT Performance Client — Standalone Fleet Benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--profile",
        type=str,
        default=None,
        metavar="PATH",
        help="YAML profile (CLI flags override profile values)",
    )
    p.add_argument(
        "--role",
        choices=["colocated", "serve-fleet", "client-only"],
        default=None,
        help="Deployment role (default: colocated, or value from --profile)",
    )
    p.add_argument(
        "--inventory-source",
        type=str,
        default=None,
        help="Inventory file/URL for client-only (overrides profile inventory.source)",
    )
    p.add_argument(
        "--advertise-host",
        type=str,
        default=None,
        metavar="HOST",
        help=(
            "Host/IP written into inventory endpoint URLs for remote clients "
            "(default: 127.0.0.1). Required for usable serve-fleet → remote client-only."
        ),
    )
    p.add_argument(
        "--servers",
        "-n",
        type=int,
        default=50,
        metavar="COUNT",
        help="Number of local server simulator instances to launch (default: 50)",
    )
    p.add_argument(
        "--start-port",
        "-p",
        type=int,
        default=40001,
        metavar="PORT",
        help="Starting TCP port for server instances (default: 40001)",
    )
    p.add_argument(
        "--samples-per-server",
        "-s",
        type=int,
        default=10,
        metavar="SAMPLES",
        help="Number of joining result samples to collect per server (default: 10)",
    )
    p.add_argument(
        "--duration",
        "-d",
        type=float,
        default=None,
        metavar="SECONDS",
        help="Maximum benchmark measurement window in seconds (default: auto-scaled from samples and burst delay)",
    )
    p.add_argument(
        "--keep-running",
        action="store_true",
        help="Keep server instances running after benchmark (press Enter to stop)",
    )
    p.add_argument(
        "--workers",
        "-w",
        type=int,
        default=None,
        metavar="WORKERS",
        help="Number of CPU worker processes (default: auto-scale based on CPU cores and endpoints)",
    )
    p.add_argument(
        "--burst-delay",
        type=float,
        default=1.0,
        metavar="SECONDS",
        help="Delay in seconds between burst stimulation rounds (default: 1.0)",
    )
    p.add_argument(
        "--settle-timeout",
        type=float,
        default=None,
        metavar="SECONDS",
        help="Max wait after the last trigger round for results to arrive (default: client default, 5)",
    )
    p.add_argument(
        "--fail-p90",
        type=float,
        default=None,
        metavar="MS",
        help="Fail if the 90%%-under (P90) delivery time of VALID results exceeds this value",
    )
    p.add_argument(
        "--fail-p90-client-ready",
        type=float,
        default=None,
        metavar="MS",
        help="Fail if the 90%%-under (P90) client-ready time of VALID results exceeds this value",
    )
    p.add_argument(
        "--claim-intended",
        choices=["auto", "capacity", "split_path"],
        default=None,
        help=(
            "Override claim.intended from profile: capacity=Profile A, "
            "split_path=Profile B attempt (fail-closed if UNPROVEN), auto=decide from evidence"
        ),
    )
    p.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging",
    )
    return p


def validate_fleet_args(
    args: argparse.Namespace,
    *,
    role: str,
    inventory_source: str | None = None,
) -> str | None:
    """Pre-flight validation of fleet benchmark arguments before starting simulators."""
    if role != "client-only":
        if args.servers < 1:
            return f"Invalid --servers: must be >= 1 (got {args.servers})"
        end_port = args.start_port + args.servers - 1
        if args.start_port < 1024 or end_port > 65535:
            return f"Invalid port range: {args.start_port}..{end_port} must be within 1024..65535"
    if role == "client-only":
        if not (args.inventory_source or inventory_source):
            return "client-only role requires --inventory-source or inventory.source in --profile"
    if args.samples_per_server < 1:
        return f"Invalid --samples-per-server: must be >= 1 (got {args.samples_per_server})"
    if not math.isfinite(args.burst_delay) or args.burst_delay < 0.0:
        return f"Invalid --burst-delay: must be finite and >= 0.0 (got {args.burst_delay})"
    if args.workers is not None and not (1 <= args.workers <= 32):
        return f"Invalid --workers: must be between 1 and 32 (got {args.workers})"
    if args.duration is not None and (not math.isfinite(args.duration) or args.duration <= 0.0):
        return f"Invalid --duration: must be finite and > 0.0 (got {args.duration})"
    if args.settle_timeout is not None and (not math.isfinite(args.settle_timeout) or args.settle_timeout < 0.0):
        return f"Invalid --settle-timeout: must be finite and >= 0.0 (got {args.settle_timeout})"
    for flag, value in (("--fail-p90", args.fail_p90), ("--fail-p90-client-ready", args.fail_p90_client_ready)):
        if value is not None and (not math.isfinite(value) or value <= 0.0):
            return f"Invalid {flag}: must be finite and > 0.0 (got {value})"
    return None


def _load_fleet_profile(args: argparse.Namespace):
    from src.config import OpcUaPoolConfig, load_config, verify_packaged_profiles

    missing = verify_packaged_profiles()
    if missing:
        _print_status(f"[fleet] WARNING: packaged profiles missing under src/profiles: {', '.join(missing)}")

    if args.profile:
        cfg = load_config(args.profile)
    else:
        cfg = OpcUaPoolConfig()
    if args.role is not None:
        cfg.role = args.role
    elif not args.profile:
        cfg.role = "colocated"
    if args.inventory_source:
        cfg.inventory_source = args.inventory_source
    if args.claim_intended:
        cfg.claim_intended = args.claim_intended
    return cfg


def _build_client_cli_args(
    args: argparse.Namespace,
    cfg,
    *,
    endpoints_str: str | None = None,
    duration: float | None = None,
    total_samples: int | None = None,
) -> list[str]:
    """Shared CLI argv for colocated and client-only fleet launches (avoids flag drift)."""
    cli_args = [
        "--samples-per-endpoint",
        str(args.samples_per_server),
        "-b",
        str(args.samples_per_server),
        "--burst-delay",
        str(args.burst_delay),
        "--mode",
        "both",
        "--require-full-coverage",
        "--role",
        cfg.role,
        "--claim-intended",
        cfg.claim_intended,
        "--junit",
        str(_RESULTS_DIR / "junit-fleet.xml"),
        "--markdown",
        str(_RESULTS_DIR / "perf-fleet.md"),
        "--json",
        str(_RESULTS_DIR / "perf-fleet.json"),
        "--csv",
        str(_RESULTS_DIR / "perf-fleet.csv"),
    ]
    if cfg.role == "client-only":
        inv_src = cfg.inventory_source or args.inventory_source
        if inv_src:
            cli_args.extend(["--inventory-source", str(inv_src)])
        run_duration = duration if duration is not None else args.duration
        if run_duration is not None:
            cli_args.extend(["-d", str(run_duration)])
        if total_samples is not None:
            cli_args.extend(["-s", str(total_samples)])
    else:
        if not endpoints_str or duration is None or total_samples is None:
            raise ValueError("colocated/serve-fleet client args require endpoints_str, duration, and total_samples")
        cli_args.extend(
            [
                "-e",
                endpoints_str,
                "-d",
                str(duration),
                "-s",
                str(total_samples),
            ]
        )
        if cfg.inventory_write_file:
            cli_args.extend(["--inventory-path", cfg.inventory_path])
        if cfg.inventory_http:
            cli_args.append("--inventory-http")
            cli_args.extend(["--inventory-http-port", str(cfg.inventory_http_port)])
        from src.config import is_loopback_endpoint

        eps = [ep for ep in endpoints_str.split(",") if ep]
        if eps and all(is_loopback_endpoint(ep) for ep in eps):
            cli_args.append("--skip-clock-skew")
    if args.profile:
        cli_args.extend(["-c", str(args.profile)])
    if args.workers is not None:
        cli_args.extend(["-w", str(args.workers)])
    if args.settle_timeout is not None:
        cli_args.extend(["--settle-timeout", str(args.settle_timeout)])
    if args.fail_p90 is not None:
        cli_args.extend(["--fail-p90", str(args.fail_p90)])
    if args.fail_p90_client_ready is not None:
        cli_args.extend(["--fail-p90-client-ready", str(args.fail_p90_client_ready)])
    if args.verbose:
        cli_args.append("-v")
    return cli_args


def main() -> int:
    args = build_parser().parse_args()
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Relaunch under .venv before importing package deps (asyncua/yaml) when possible.
    # If src is already importable, continue; otherwise ImportError triggers relaunch below.
    if not _ENV_IS_PRE_ISOLATED and not _inside_venv(_RUNTIME_VENV):
        # Lightweight pre-check without src: client-only needs inventory on CLI or will re-check after load
        if args.role != "client-only":
            early = validate_fleet_args(args, role=args.role or "colocated", inventory_source=args.inventory_source)
            if early:
                _print_status(f"[fleet] ERROR: {early}", file=sys.stderr)
                return 1
        return _relaunch_under_venv(_RUNTIME_VENV, False, Path(__file__).resolve())

    try:
        from src.config import OpcUaPoolConfig, load_config
    except ImportError:
        if not _ENV_IS_PRE_ISOLATED and not _inside_venv(_RUNTIME_VENV):
            return _relaunch_under_venv(_RUNTIME_VENV, False, Path(__file__).resolve())
        raise

    try:
        preview = load_config(args.profile) if args.profile else OpcUaPoolConfig()
    except (FileNotFoundError, ValueError) as exc:
        _print_status(f"[fleet] ERROR: {exc}", file=sys.stderr)
        return 1
    role = args.role or preview.role or "colocated"
    if args.inventory_source:
        preview.inventory_source = args.inventory_source
    val_err = validate_fleet_args(args, role=role, inventory_source=preview.inventory_source)
    if val_err:
        _print_status(f"[fleet] ERROR: {val_err}", file=sys.stderr)
        return 1

    cfg = _load_fleet_profile(args)
    role = cfg.role

    from src.cli import main as client_main
    from src.inventory import (
        InventoryHttpServer,
        build_inventory,
        load_inventory,
        preflight_http_port,
        preflight_port_range,
        write_inventory_atomic,
    )

    if role == "client-only":
        # No local sims: load producer inventory so -s matches endpoint count × samples-per-server
        # (avoids profile target_sample_count drifting vs --samples-per-server).
        inv_src = cfg.inventory_source or args.inventory_source
        try:
            inv = load_inventory(inv_src, token=cfg.inventory_http_token)
        except (OSError, ValueError, FileNotFoundError, TypeError, KeyError) as exc:
            _print_status(f"[fleet] ERROR: Failed to load inventory from {inv_src}: {exc}", file=sys.stderr)
            return 1
        n_endpoints = len(inv.endpoint_urls())
        if n_endpoints < 1:
            _print_status(f"[fleet] ERROR: Inventory at {inv_src} contains no endpoints", file=sys.stderr)
            return 1
        total_samples = n_endpoints * args.samples_per_server
        if args.duration is not None:
            duration = args.duration
        else:
            estimated_burst_time = args.samples_per_server * (args.burst_delay + 0.5)
            setup_buffer = max(30.0, n_endpoints * 0.06)
            duration = max(60.0, estimated_burst_time + setup_buffer)
        return client_main(
            _build_client_cli_args(
                args,
                cfg,
                duration=duration,
                total_samples=total_samples,
            )
        )

    exe = _find_simulator_exe()
    if not exe:
        _print_status("[fleet] ERROR: OPC UA Server Simulator executable not found.", file=sys.stderr)
        return 1

    conflicts = preflight_port_range(args.start_port, args.servers)
    if conflicts:
        for msg in conflicts:
            _print_status(f"[fleet] ERROR: {msg}", file=sys.stderr)
        return 1

    total_samples = args.servers * args.samples_per_server
    ports = list(range(args.start_port, args.start_port + args.servers))
    advertise_host = (args.advertise_host or "127.0.0.1").strip()
    if role == "serve-fleet" and advertise_host in {"127.0.0.1", "localhost", "::1"}:
        _print_status(
            "[fleet] WARNING: serve-fleet inventory will list loopback URLs; "
            "a remote client-only host cannot use them. Pass --advertise-host <reachable-IP>.",
            file=sys.stderr,
        )
    endpoints = [f"opc.tcp://{advertise_host}:{port}" for port in ports]
    endpoints_str = ",".join(endpoints)

    if args.duration is not None:
        duration = args.duration
    else:
        estimated_burst_time = args.samples_per_server * (args.burst_delay + 0.5)
        setup_buffer = max(30.0, args.servers * 0.06)
        duration = max(60.0, estimated_burst_time + setup_buffer)

    workers_display = f"{args.workers} (explicit)" if args.workers is not None else "auto-scaled"

    print("\n" + "=" * 72)
    print(f"  IJT Performance Client — Fleet Benchmark ({args.servers} Servers, role={role})")
    print("=" * 72)
    print(f"  Servers to launch:    {args.servers} (ports {args.start_port}..{args.start_port + args.servers - 1})")
    print(f"  Samples per server:   {args.samples_per_server} (Total target: {total_samples} samples)")
    print(f"  Burst delay:          {args.burst_delay}s between rounds")
    print(f"  Measurement window:   {duration:.1f}s")
    print(f"  Worker processes:     {workers_display}")
    print(f"  Simulator binary:     {exe.name}")
    print("=" * 72 + "\n")

    server_instances: list[tuple[subprocess.Popen, Path]] = []
    inventory_http: InventoryHttpServer | None = None
    t_start = time.monotonic()

    try:
        server_instances = _launch_simulator_fleet(args.servers, start_port=args.start_port, exe=exe)
        if len(server_instances) < args.servers:
            _print_status(
                f"[fleet] ERROR: Only started {len(server_instances)}/{args.servers} instances.", file=sys.stderr
            )
            return 1

        if role == "serve-fleet":
            if cfg.inventory_ttl_seconds < 600:
                _print_status(
                    f"[fleet] WARNING: inventory TTL is {cfg.inventory_ttl_seconds}s — "
                    "remote client-only runs may expire while simulators stay up; "
                    "raise inventory.ttl_seconds (recommended >= 3600).",
                    file=sys.stderr,
                )
            inv = build_inventory(
                endpoints,
                ttl_seconds=cfg.inventory_ttl_seconds,
                role=role,
                extras={"claim_intended": cfg.claim_intended},
            )
            inv_path = write_inventory_atomic(cfg.inventory_path, inv)
            _print_status(f"\n[fleet] Inventory written: {inv_path}")
            if cfg.inventory_http:
                http_conflicts = preflight_http_port(cfg.inventory_http_port, cfg.inventory_http_host)
                if http_conflicts:
                    for msg in http_conflicts:
                        _print_status(f"[fleet] ERROR: {msg}", file=sys.stderr)
                    return 1
                inventory_http = InventoryHttpServer(
                    inv,
                    host=cfg.inventory_http_host,
                    port=cfg.inventory_http_port,
                    token=cfg.inventory_http_token,
                )
                inventory_http.start()
                _print_status(f"[fleet] Inventory HTTP: {inventory_http.url}")
            _print_status("\n[fleet] serve-fleet mode: simulators running; benchmark client not started.")
            _print_status("[fleet] Press Enter to terminate all servers...")
            try:
                input()
            except (KeyboardInterrupt, EOFError):
                pass
            return 0

        _print_status(
            f"\n[fleet] All {args.servers} servers ready. Starting benchmark across {workers_display} worker processes...\n"
        )

        cli_args = _build_client_cli_args(
            args,
            cfg,
            endpoints_str=endpoints_str,
            duration=duration,
            total_samples=total_samples,
        )
        exit_code = client_main(cli_args)

        elapsed = time.monotonic() - t_start
        _print_status(f"\n[fleet] Benchmark completed in {elapsed:.2f}s with exit code {exit_code}")
        _print_status("[fleet] Reports saved to:")
        print(f"  - Markdown: {_RESULTS_DIR / 'perf-fleet.md'}")
        print(f"  - JSON:     {_RESULTS_DIR / 'perf-fleet.json'}")
        print(f"  - CSV:      {_RESULTS_DIR / 'perf-fleet.csv'}")
        print(f"  - JUnit:    {_RESULTS_DIR / 'junit-fleet.xml'}")

        if args.keep_running:
            _print_status("\n[fleet] Servers are still running for manual inspection.")
            _print_status("[fleet] Press Enter to terminate all servers...")
            try:
                input()
            except (KeyboardInterrupt, EOFError):
                pass

        return exit_code

    finally:
        if inventory_http is not None:
            inventory_http.stop()
        _stop_simulators(server_instances)


if __name__ == "__main__":
    sys.exit(main())
