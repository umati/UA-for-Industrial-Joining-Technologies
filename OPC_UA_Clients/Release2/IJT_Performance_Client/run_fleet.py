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
import subprocess
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_RESULTS_DIR = _HERE / "test-results"

# Import simulator lifecycle helpers from the runner
from run_all_tests import _find_simulator_exe, _launch_simulator_fleet, _stop_simulators
from src.cli import main as client_main


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
        default=60.0,
        metavar="SECONDS",
        help="Maximum benchmark measurement window in seconds (default: 60.0)",
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
        default=4,
        metavar="WORKERS",
        help="Number of CPU worker processes (default: 4)",
    )
    p.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging",
    )
    return p


def main() -> int:
    args = build_parser().parse_args()
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    exe = _find_simulator_exe()
    if not exe:
        print("[fleet] ERROR: OPC UA Server Simulator executable not found.", file=sys.stderr)
        return 1

    total_samples = args.servers * args.samples_per_server
    ports = list(range(args.start_port, args.start_port + args.servers))
    endpoints = [f"opc.tcp://127.0.0.1:{port}" for port in ports]
    endpoints_str = ",".join(endpoints)

    print("\n" + "=" * 72)
    print(f"  IJT Performance Client — Fleet Benchmark ({args.servers} Servers)")
    print("=" * 72)
    print(f"  Servers to launch:    {args.servers} (ports {args.start_port}..{args.start_port + args.servers - 1})")
    print(f"  Samples per server:   {args.samples_per_server} (Total target: {total_samples} samples)")
    print(f"  Worker processes:     {args.workers}")
    print(f"  Simulator binary:     {exe.name}")
    print("=" * 72 + "\n")

    server_instances: list[tuple[subprocess.Popen, Path]] = []
    t_start = time.monotonic()

    try:
        # Step 1: Launch fleet
        server_instances = _launch_simulator_fleet(args.servers, start_port=args.start_port, exe=exe)
        if len(server_instances) < args.servers:
            print(f"[fleet] ERROR: Only started {len(server_instances)}/{args.servers} instances.", file=sys.stderr)
            return 1

        print(f"\n[fleet] All {args.servers} servers ready. Starting benchmark across 4 worker processes...\n")

        # Step 2: Execute client benchmark
        cli_args = [
            "-e",
            endpoints_str,
            "-d",
            str(args.duration),
            "-s",
            str(total_samples),
            "-b",
            str(args.samples_per_server),
            "--mode",
            "both",
            "--require-full-coverage",
            "--junit",
            str(_RESULTS_DIR / "junit-fleet.xml"),
            "--markdown",
            str(_RESULTS_DIR / "perf-fleet.md"),
            "--json",
            str(_RESULTS_DIR / "perf-fleet.json"),
        ]
        if args.verbose:
            cli_args.append("-v")

        exit_code = client_main(cli_args)

        elapsed = time.monotonic() - t_start
        print(f"\n[fleet] Benchmark completed in {elapsed:.2f}s with exit code {exit_code}")
        print("[fleet] Reports saved to:")
        print(f"  - Markdown: {_RESULTS_DIR / 'perf-fleet.md'}")
        print(f"  - JSON:     {_RESULTS_DIR / 'perf-fleet.json'}")
        print(f"  - JUnit:    {_RESULTS_DIR / 'junit-fleet.xml'}")

        if args.keep_running:
            print("\n[fleet] Servers are still running for manual inspection.")
            print("[fleet] Press Enter to terminate all servers...")
            try:
                input()
            except (KeyboardInterrupt, EOFError):
                pass

        return exit_code

    finally:
        _stop_simulators(server_instances)


if __name__ == "__main__":
    sys.exit(main())
