#!/usr/bin/env python3
"""
run_fleet.py — Standalone multi-server fleet benchmark launcher for IJT Performance Client.

Orchestrates N local OPC UA server simulator instances, executes the Performance Client
across all endpoints, and prints/saves the latency benchmark report.

Usage:
  python run_fleet.py                        # Launch 50 servers, collect 500 samples (10/server), report & stop
  python run_fleet.py --servers 25           # Launch 25 servers (250 samples)
  python run_fleet.py --samples-per-server 5 # 5 samples per server
  python run_fleet.py --start-port 41001     # Custom starting TCP port
  python run_fleet.py --keep-running         # Keep servers running for manual inspection
  python run_fleet.py --help
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

# Stdlib-only runner helpers: simulator lifecycle and the shared venv bootstrap.
from run_all_tests import (
    _ENV_IS_PRE_ISOLATED,
    _REQUIREMENTS,
    _find_simulator_exe,
    _inside_venv,
    _launch_simulator_fleet,
    _print_status,
    _relaunch_under_venv,
    _stop_simulators,
)

# Runtime venv (requirements.txt only, pinned by requirements.lock), like setup_client.py elsewhere.
_RUNTIME_VENV = _HERE / ".venv"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="IJT Performance Client — Standalone Fleet Benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
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
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging",
    )
    return p


def validate_fleet_args(args: argparse.Namespace) -> str | None:
    """Pre-flight validation of fleet benchmark arguments before starting simulators."""
    if args.servers < 1:
        return f"Invalid --servers: must be >= 1 (got {args.servers})"
    if args.samples_per_server < 1:
        return f"Invalid --samples-per-server: must be >= 1 (got {args.samples_per_server})"
    end_port = args.start_port + args.servers - 1
    if args.start_port < 1024 or end_port > 65535:
        return f"Invalid port range: {args.start_port}..{end_port} must be within 1024..65535"
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


def main() -> int:
    args = build_parser().parse_args()
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    val_err = validate_fleet_args(args)
    if val_err:
        _print_status(f"[fleet] ERROR: {val_err}", file=sys.stderr)
        return 1

    if not _ENV_IS_PRE_ISOLATED and not _inside_venv(_RUNTIME_VENV):
        return _relaunch_under_venv(_RUNTIME_VENV, (_REQUIREMENTS,), Path(__file__).resolve())

    # Imported only after the venv switch: src.cli needs asyncua from the lock-pinned venv.
    from src.cli import main as client_main

    exe = _find_simulator_exe()
    if not exe:
        _print_status("[fleet] ERROR: OPC UA Server Simulator executable not found.", file=sys.stderr)
        return 1

    total_samples = args.servers * args.samples_per_server
    ports = list(range(args.start_port, args.start_port + args.servers))
    endpoints = [f"opc.tcp://127.0.0.1:{port}" for port in ports]
    endpoints_str = ",".join(endpoints)

    if args.duration is not None:
        duration = args.duration
    else:
        # Auto-scale duration to ensure all burst rounds have time to complete:
        # (samples_per_server * (burst_delay + 0.5s processing)) + connection setup buffer
        estimated_burst_time = args.samples_per_server * (args.burst_delay + 0.5)
        setup_buffer = max(30.0, args.servers * 0.06)
        duration = max(60.0, estimated_burst_time + setup_buffer)

    workers_display = f"{args.workers} (explicit)" if args.workers is not None else "auto-scaled"

    print("\n" + "=" * 72)
    print(f"  IJT Performance Client — Fleet Benchmark ({args.servers} Servers)")
    print("=" * 72)
    print(f"  Servers to launch:    {args.servers} (ports {args.start_port}..{args.start_port + args.servers - 1})")
    print(f"  Samples per server:   {args.samples_per_server} (Total target: {total_samples} samples)")
    print(f"  Burst delay:          {args.burst_delay}s between rounds")
    print(f"  Measurement window:   {duration:.1f}s")
    print(f"  Worker processes:     {workers_display}")
    print(f"  Simulator binary:     {exe.name}")
    print("=" * 72 + "\n")

    server_instances: list[tuple[subprocess.Popen, Path]] = []
    t_start = time.monotonic()

    try:
        # Step 1: Launch fleet
        server_instances = _launch_simulator_fleet(args.servers, start_port=args.start_port, exe=exe)
        if len(server_instances) < args.servers:
            _print_status(
                f"[fleet] ERROR: Only started {len(server_instances)}/{args.servers} instances.", file=sys.stderr
            )
            return 1

        _print_status(
            f"\n[fleet] All {args.servers} servers ready. Starting benchmark across {workers_display} worker processes...\n"
        )

        # Step 2: Execute client benchmark
        cli_args = [
            "-e",
            endpoints_str,
            "-d",
            str(duration),
            "-s",
            str(total_samples),
            "--samples-per-endpoint",
            str(args.samples_per_server),
            "-b",
            str(args.samples_per_server),
            "--burst-delay",
            str(args.burst_delay),
            "--mode",
            "both",
            "--require-full-coverage",
            "--skip-clock-skew",
            "--junit",
            str(_RESULTS_DIR / "junit-fleet.xml"),
            "--markdown",
            str(_RESULTS_DIR / "perf-fleet.md"),
            "--json",
            str(_RESULTS_DIR / "perf-fleet.json"),
            "--csv",
            str(_RESULTS_DIR / "perf-fleet.csv"),
        ]
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
        _stop_simulators(server_instances)


if __name__ == "__main__":
    sys.exit(main())
