#!/usr/bin/env python3
"""
run_all_tests.py — Per-project test runner for IJT Performance Client.

Architecture: Two-phase execution matching repository convention:
  Phase 1 — static / quality analysis + unit tests (no OPC UA server required).
  Phase 2 — live integration tests (OPC UA server auto-started or must be reachable).

Usage:
  python run_all_tests.py                    # full run (Phase 1 + Phase 2)
  python run_all_tests.py --phase1           # unit / static only
  python run_all_tests.py --phase2           # live tests only
  python run_all_tests.py --junit-xml=PATH   # write JUnit XML to PATH
  python run_all_tests.py --verbose          # verbose pytest output
  python run_all_tests.py --help

Environment variables:
  OPCUA_SERVER_URL      Override server URL (default: opc.tcp://localhost:40485)
  OPCUA_SIMULATOR_EXE   Path to opcua_ijt_demo_application(.exe)
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

# Key directory paths
_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parents[2]
_RESULTS_DIR = _HERE / "test-results"
_DEFAULT_JUNIT = _RESULTS_DIR / "pytest.xml"
_OPCUA_SERVER_PORT = 40485
_DEFAULT_SERVER_URL = f"opc.tcp://localhost:{_OPCUA_SERVER_PORT}"


@dataclass
class _StepResult:
    name: str
    ok: bool = True
    note: str = ""


def _is_port_reachable(host: str, port: int, timeout: float = 2.0) -> bool:
    """Check if target TCP port is actively listening."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _find_simulator_exe() -> Path | None:
    """Locate the OPC UA simulator executable across Windows and Linux directories."""
    candidates = [
        _REPO_ROOT / "OPC_UA_Servers" / "Release2" / "OPC_UA_IJT_Server_Simulator" / "opcua_ijt_demo_application.exe",
        _REPO_ROOT / "OPC_UA_Servers" / "Release2" / "OPC_UA_IJT_Server_Simulator_Linux" / "opcua_ijt_demo_application",
    ]
    env_override = os.environ.get("OPCUA_SIMULATOR_EXE")
    if env_override:
        candidates.insert(0, Path(env_override))

    for path in candidates:
        if path.is_file():
            return path
    return None


def _parse_endpoint_host_port(url: str, default_port: int = _OPCUA_SERVER_PORT) -> tuple[str, int]:
    """Extract host and port from OPC UA endpoint string."""
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or "localhost"
    port = parsed.port or default_port
    return host, port


def _launch_simulator_on_port(port: int, exe: Path, quiet: bool = False) -> tuple[subprocess.Popen | None, Path | None]:
    """Copy the binary dir to a temp location, patch the port config, and launch."""
    exe_path = Path(exe)
    if not exe_path.exists():
        if not quiet:
            print(f"  [server] Binary not found: {exe}")
        return None, None

    src_dir = exe_path.parent
    tmp_base = Path(os.environ.get("RUNNER_TEMP") or tempfile.gettempdir()) / "ijt-sim"
    tmp_dir = tmp_base / f"server_instance_{port}_{int(time.time())}"
    if not quiet:
        print(f"  [server] Launching simulator on port {port} (copied to {tmp_dir})")
    try:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)
        shutil.copytree(src_dir, tmp_dir)
    except OSError as exc:
        if not quiet:
            print(f"  [server] Failed to copy binary dir: {exc}")
        return None, None

    cfg_path = tmp_dir / "server_configuration.json"
    if cfg_path.exists():
        try:
            with cfg_path.open(encoding="utf-8") as fh:
                cfg = json.load(fh)
            cfg.setdefault("serverConfigurationData", {})["serverEndpointTCPPort"] = port
            with cfg_path.open("w", encoding="utf-8") as fh:
                json.dump(cfg, fh, indent=2)
        except (OSError, ValueError) as exc:
            if not quiet:
                print(f"  [server] Failed to patch server_configuration.json: {exc}")
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return None, None

    try:
        proc = subprocess.Popen(  # nosec B603
            [str(tmp_dir / exe_path.name)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(tmp_dir),
        )
    except OSError as exc:
        if not quiet:
            print(f"  [server] Failed to launch binary: {exc}")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return None, None

    for _ in range(30):
        if _is_port_reachable("localhost", port):
            if not quiet:
                print(f"  [server] Ready on port {port}")
            return proc, tmp_dir
        time.sleep(1)

    if not quiet:
        print("  [server] Timed out waiting for simulator — terminating")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    shutil.rmtree(tmp_dir, ignore_errors=True)
    return None, None


def _launch_simulator_fleet(count: int, start_port: int, exe: Path) -> list[tuple[subprocess.Popen, Path]]:
    """Concurrently launch a fleet of N simulator instances."""
    print(
        f"  [fleet] Launching {count} simulator instances concurrently (ports {start_port}..{start_port + count - 1})..."
    )
    ports = list(range(start_port, start_port + count))
    instances: list[tuple[subprocess.Popen, Path]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(16, count)) as executor:
        futures = {executor.submit(_launch_simulator_on_port, port, exe, True): port for port in ports}
        for future in concurrent.futures.as_completed(futures):
            proc, tmp_dir = future.result()
            if proc is not None and tmp_dir is not None:
                instances.append((proc, tmp_dir))
            else:
                port = futures[future]
                print(f"  [fleet] Failed to launch simulator on port {port}")
    print(f"  [fleet] Successfully started {len(instances)}/{count} simulator instances.")
    return instances


def _stop_simulators(instances: list[tuple[subprocess.Popen, Path]]) -> None:
    """Terminate all simulator processes and remove their temporary directories."""
    if not instances:
        return
    print(f"  [server] Stopping {len(instances)} simulator instances...")
    for proc, _ in instances:
        try:
            proc.terminate()
        except OSError:
            pass
    for proc, _ in instances:
        try:
            proc.wait(timeout=3)
        except (subprocess.TimeoutExpired, OSError):
            try:
                proc.kill()
            except OSError:
                pass
    for _, tmp_dir in instances:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _step_ruff_lint() -> _StepResult:
    """Run Ruff lint checks."""
    res = subprocess.run([sys.executable, "-m", "ruff", "check", "."], cwd=_HERE, capture_output=True, text=True)
    return _StepResult("Ruff Lint", ok=res.returncode == 0, note=res.stdout.strip() if res.returncode != 0 else "Clean")


def _step_ruff_format() -> _StepResult:
    """Run Ruff format check."""
    res = subprocess.run(
        [sys.executable, "-m", "ruff", "format", "--check", "."], cwd=_HERE, capture_output=True, text=True
    )
    return _StepResult(
        "Ruff Format", ok=res.returncode == 0, note=res.stdout.strip() if res.returncode != 0 else "Clean"
    )


def _step_mypy() -> _StepResult:
    """Run mypy static type checking."""
    res = subprocess.run(
        [sys.executable, "-m", "mypy", "src", "--ignore-missing-imports", "--no-error-summary"],
        cwd=_HERE,
        capture_output=True,
        text=True,
    )
    return _StepResult(
        "Mypy Typing", ok=res.returncode == 0, note=res.stdout.strip() if res.returncode != 0 else "Clean"
    )


def _step_bandit() -> _StepResult:
    """Run Bandit security scan against medium+ severity."""
    root_cfg = _REPO_ROOT / "pyproject.toml"
    cmd = [sys.executable, "-m", "bandit", "-r", "."]
    if root_cfg.is_file():
        cmd.extend(["-c", str(root_cfg)])
    cmd.extend(["--severity-level", "medium"])
    res = subprocess.run(cmd, cwd=_HERE, capture_output=True, text=True)
    return _StepResult(
        "Bandit Security", ok=res.returncode == 0, note=res.stdout.strip() if res.returncode != 0 else "Clean"
    )


def _extract_pytest_summary(output: str) -> str:
    """Extract standard pytest summary line (e.g. '108 passed in 12.34s')."""
    for line in reversed(output.splitlines()):
        stripped = line.strip("= ").strip()
        if any(k in stripped for k in ("passed", "failed", "error", "skipped", "xfailed")):
            cleaned = re.sub(r",?\s*\d+\s+warnings?", "", stripped)
            return cleaned.strip()
    return "Passed"


def _step_unit_tests(junit_xml: str | None = None, verbose: bool = False) -> _StepResult:
    """Run pytest unit tests with coverage."""
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/unit/",
        "--cov=src",
        "--cov-report=xml:test-results/coverage.xml",
        "--cov-fail-under=95",
    ]
    if junit_xml:
        cmd.append(f"--junitxml={junit_xml}")
    if verbose:
        cmd.append("-v")

    res = subprocess.run(cmd, cwd=_HERE, capture_output=True, text=True)
    summary = _extract_pytest_summary(res.stdout) if res.returncode == 0 else "Failed"
    return _StepResult(
        "Unit Tests",
        ok=res.returncode == 0,
        note=summary if res.returncode == 0 else (res.stdout + res.stderr)[-500:],
    )


def _step_live_tests(
    server_url: str = _DEFAULT_SERVER_URL,
    fleet_endpoints: str | None = None,
    verbose: bool = False,
) -> _StepResult:
    """Run live performance benchmark against live target server(s)."""
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/live/",
        "-m",
        "live",
        "--junitxml=test-results/perf-live.xml",
    ]
    if verbose:
        cmd.append("-v")

    env = os.environ.copy()
    env["OPCUA_SERVER_URL"] = server_url
    if fleet_endpoints:
        env["OPCUA_FLEET_ENDPOINTS"] = fleet_endpoints

    res = subprocess.run(cmd, cwd=_HERE, env=env, capture_output=True, text=True)
    required_names = {
        "test_live_single_server_result_transfer_time",
        "test_live_single_server_burst_transfer_time",
    }
    if fleet_endpoints:
        required_names.add("test_live_multi_server_fleet_transfer_time")

    required_ran = False
    if res.returncode == 0:
        try:
            # Safe local XML: perf-live.xml is generated locally by pytest in this runner invocation
            root = ET.parse(_RESULTS_DIR / "perf-live.xml").getroot()  # nosec B314
            cases = {case.get("name"): case for case in root.iter("testcase") if case.get("name") in required_names}
            required_ran = required_names == cases.keys() and all(
                case.find("skipped") is None for case in cases.values()
            )
        except (OSError, ET.ParseError):
            required_ran = False
    summary = _extract_pytest_summary(res.stdout) if res.returncode == 0 else "Failed"
    return _StepResult(
        "Live Benchmark",
        ok=res.returncode == 0 and required_ran,
        note=(
            summary
            if res.returncode == 0 and required_ran
            else "Mandatory single-server benchmarks did not run"
            if res.returncode == 0
            else (res.stdout + res.stderr)[-500:]
        ),
    )


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="IJT Performance Client — per-project test runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = p.add_mutually_exclusive_group()
    group.add_argument("--phase1", action="store_true", help="Unit / static tests only (no server)")
    group.add_argument("--phase2", action="store_true", help="Live tests only (server must be up)")
    p.add_argument(
        "--fleet",
        type=int,
        default=0,
        metavar="N",
        help="Launch N local server simulator instances and execute live fleet test (e.g. --fleet 50)",
    )
    p.add_argument(
        "--fleet-start-port",
        type=int,
        default=40001,
        metavar="PORT",
        help="Starting TCP port for local fleet simulator instances (default: 40001)",
    )
    p.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    p.add_argument(
        "--junit-xml",
        metavar="PATH",
        default=str(_DEFAULT_JUNIT),
        help=f"Write JUnit XML to PATH (default: {_DEFAULT_JUNIT})",
    )
    return p


def main() -> int:
    args = _build_parser().parse_args()
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    run_phase1 = not args.phase2
    run_phase2 = not args.phase1

    print("\n" + "=" * 70)
    print("  IJT Performance Client — Test Suite Runner")
    print("=" * 70)

    results: list[_StepResult] = []
    t_start = time.monotonic()
    server_instances: list[tuple[subprocess.Popen, Path]] = []
    fleet_endpoints: str | None = None

    try:
        if run_phase1:
            print("\n[Phase 1] Static / Quality & Unit Tests")
            print("-" * 50)
            results.append(_step_ruff_lint())
            results.append(_step_ruff_format())
            results.append(_step_mypy())
            results.append(_step_bandit())
            results.append(_step_unit_tests(junit_xml=args.junit_xml, verbose=args.verbose))

        if run_phase2:
            print("\n[Phase 2] Live Benchmark Tests")
            print("-" * 50)
            server_url = os.environ.get("OPCUA_SERVER_URL", _DEFAULT_SERVER_URL)
            host, port = _parse_endpoint_host_port(server_url, default_port=_OPCUA_SERVER_PORT)

            exe = _find_simulator_exe()

            # Auto-start single-server simulator if not running
            if not _is_port_reachable(host, port):
                if exe:
                    proc, tmp_dir = _launch_simulator_on_port(port, exe)
                    if proc is not None and tmp_dir is not None:
                        server_instances.append((proc, tmp_dir))
                    else:
                        print(f"  [server] Failed to start simulator on port {port}.")
                else:
                    print("  [server] Simulator executable not found; skipping auto-launch.")

            # Auto-start fleet simulators if requested
            if args.fleet > 0:
                if exe:
                    fleet_inst = _launch_simulator_fleet(args.fleet, start_port=args.fleet_start_port, exe=exe)
                    server_instances.extend(fleet_inst)
                    fleet_endpoints = ",".join(
                        f"opc.tcp://127.0.0.1:{p}"
                        for p in range(args.fleet_start_port, args.fleet_start_port + args.fleet)
                    )
                else:
                    print("  [server] Simulator executable not found; skipping fleet auto-launch.")

            results.append(
                _step_live_tests(server_url=server_url, fleet_endpoints=fleet_endpoints, verbose=args.verbose)
            )

    finally:
        _stop_simulators(server_instances)

    # Print summary
    elapsed = time.monotonic() - t_start
    print("\n" + "=" * 70)
    print(f"  Execution Summary ({elapsed:.2f}s)")
    print("=" * 70)

    failed = False
    for r in results:
        status = "PASS" if r.ok else "FAIL"
        note = f" ({r.note})" if r.note and r.note != "Clean" and r.note != "Passed" else ""
        print(f"  {r.name:<25} ... {status}{note}")
        if not r.ok:
            failed = True

    print("=" * 70 + "\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
