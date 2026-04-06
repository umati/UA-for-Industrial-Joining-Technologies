#!/usr/bin/env python3
"""
run_all_tests.py — IJT C# Client test runner.

Usage:
    python run_all_tests.py              # full run (Phase 1 + Phase 2 if server reachable)
    python run_all_tests.py --phase1     # build + unit tests only (no server)
    python run_all_tests.py --phase2     # live integration tests only
    python run_all_tests.py --help

Environment variables:
    OPCUA_SERVER_URL         OPC UA server endpoint (default: opc.tcp://localhost:40451)
    OPCUA_SERVER_PORT        Alt: port only — constructs opc.tcp://localhost:PORT
    OPCUA_SIMULATOR_EXE      Path to OPC UA simulator EXE (auto-launched if server unreachable)
    SKIP_DOTNET_RESTORE=1    Skip `dotnet restore` (deps already restored in CI)

Flags:
    --junit-xml=PATH         Write combined JUnit XML (default: test-results/run_all_tests.xml)
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# Paths & shared utilities
# ---------------------------------------------------------------------------

_PROJECT_DIR: Path = Path(__file__).resolve().parent
_REPO_ROOT: Path = Path(__file__).resolve().parents[3]
_SLN = _PROJECT_DIR / "IJT_CSharp_Client.sln"
_TEST_PROJ = _PROJECT_DIR / "Tests" / "IJT_CSharp_Client.Tests" / "IJT_CSharp_Client.Tests.csproj"
_RESULTS_DIR = _PROJECT_DIR / "test-results"
_DEFAULT_SERVER_URL = "opc.tcp://localhost:40465"
_MIN_DOTNET_MAJOR = 10
_COVERAGE_THRESHOLD = 80.0

if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_SERVER_NATIVE_PORT = 40451
_WELL_KNOWN_SIMULATOR_PATHS = [
    _REPO_ROOT / "OPC_UA_Servers" / "Release2" / "OPC_UA_IJT_Server_Simulator" / "opcua_ijt_demo_application.exe",
    _REPO_ROOT / "OPC_UA_Servers" / "Release2" / "OPC_UA_IJT_Server_Simulator_Linux" / "opcua_ijt_demo_application",
]


def _is_port_reachable(host: str, port: int, timeout: float = 2.0) -> bool:
    import socket
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _parse_opcua_endpoint(url: str) -> Tuple[str, int]:
    from urllib.parse import urlparse
    stripped = url.strip()
    if "://" in stripped:
        parsed = urlparse(stripped)
        return (parsed.hostname or "localhost"), (parsed.port or 40451)
    if ":" in stripped:
        host, _, port_str = stripped.rpartition(":")
        try:
            return host, int(port_str)
        except ValueError:
            return stripped, 40451
    return stripped, 40451


def _dotnet_available() -> bool:
    return shutil.which("dotnet") is not None


def _dotnet_version() -> str:
    result = subprocess.run(
        ["dotnet", "--version"], capture_output=True, text=True, check=False
    )
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class StepResult:
    label: str
    phase: str
    status: str          # "PASS", "FAIL", "SKIP", "WARN", "ERROR"
    detail: str = ""
    duration: float = 0.0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    total: int = 0


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

_W = 58


def _banner(title: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    header = f"{title}   {ts}"
    print("\n" + "=" * _W)
    print(header)
    print("=" * _W)


def _footer(ok: bool, elapsed: float, results: List[StepResult]) -> None:
    n_pass = sum(1 for r in results if r.status == "PASS")
    n_fail = sum(1 for r in results if r.status in {"FAIL", "ERROR"})
    n_skip = sum(1 for r in results if r.status == "SKIP")
    status = "PASS" if ok else "FAIL"
    print("-" * _W)
    print(f"Result: {status}   Checks: {n_pass} passed, {n_fail} failed, {n_skip} skipped")
    print(f"Elapsed: {elapsed:.1f}s")
    print("=" * _W + "\n")


def _row(phase: str, label: str, status: str, detail: str = "") -> None:
    tag = f"[{phase}] {label}"
    pad = max(1, 52 - len(tag))
    dots = "." * pad
    suffix = f" ({detail})" if detail else ""
    print(f"{tag} {dots} {status}{suffix}")


# ---------------------------------------------------------------------------
# Subprocess helper
# ---------------------------------------------------------------------------

def _run(
    cmd: List[str],
    *,
    cwd: Path = _PROJECT_DIR,
    env: Optional[dict] = None,
    capture_stdout: bool = False,
) -> Tuple[int, str]:
    """Run *cmd* and return (returncode, stdout_text).

    stderr is inherited (visible in terminal).
    """
    merged_env = {**os.environ, **(env or {})}
    result = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=merged_env,
        check=False,
        stdout=subprocess.PIPE if capture_stdout else None,
        text=True,
    )
    return result.returncode, (result.stdout or "")


# ---------------------------------------------------------------------------
# Output parsers
# ---------------------------------------------------------------------------

def _parse_trx(path: Path) -> Tuple[int, int, int, int]:
    """Return (passed, failed, skipped, total) from a dotnet TRX file."""
    if not path.exists():
        return 0, 0, 0, 0
    try:
        tree = ET.parse(str(path))
        root = tree.getroot()
        ns_match = re.match(r"\{[^}]+\}", root.tag)
        ns = ns_match.group(0) if ns_match else ""
        counters = root.find(f".//{ns}Counters")
        if counters is None:
            return 0, 0, 0, 0
        total = int(counters.get("total", "0"))
        executed = int(counters.get("executed", "0"))
        passed = int(counters.get("passed", "0"))
        failed = int(counters.get("failed", "0"))
        skipped = total - executed
        return passed, failed, skipped, total
    except Exception:
        return 0, 0, 0, 0


def _parse_build_warnings(stdout: str) -> int:
    """Extract warning count from `dotnet build` output."""
    match = re.search(r"(\d+)\s+Warning\(s\)", stdout, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 0


def _parse_nuget_vulnerabilities(stdout: str) -> Tuple[int, int]:
    """Return (critical_count, high_count) from `dotnet list package --vulnerable` output."""
    if "has the following vulnerable packages" not in stdout:
        return 0, 0
    critical = len(re.findall(r"\bCritical\b", stdout, re.IGNORECASE))
    high = len(re.findall(r"\bHigh\b", stdout, re.IGNORECASE))
    return critical, high


def _find_cobertura_file() -> Optional[Path]:
    """Search test-results/ for a Cobertura coverage XML produced by coverlet."""
    for candidate in [
        _RESULTS_DIR / "coverage.xml",
        _RESULTS_DIR / "coverage.cobertura.xml",
    ]:
        if candidate.exists():
            return candidate
    for found in _RESULTS_DIR.rglob("coverage.cobertura.xml"):
        return found
    return None


def _parse_cobertura_coverage(path: Path) -> Optional[float]:
    """Return line coverage % (0-100) for IJT_CSharp_Client.* classes only.

    Auto-generated UAModel.* type bindings and the Program entry point are
    excluded — they skew the overall rate to ~30% despite good coverage of the
    actual application code.
    """
    if not path.exists():
        return None
    with contextlib.suppress(Exception):
        tree = ET.parse(str(path))
        root = tree.getroot()
        total_lines = 0
        covered_lines = 0
        for cls in root.iter("class"):
            name = cls.get("name", "")
            # Only count application code, not generated type bindings
            if not name.startswith("IJT_CSharp_Client."):
                continue
            for line in cls.iter("line"):
                total_lines += 1
                if int(line.get("hits", "0")) > 0:
                    covered_lines += 1
        if total_lines > 0:
            return (covered_lines / total_lines) * 100.0
        # Fallback to top-level rate if no matching classes found
        rate_str = root.get("line-rate")
        if rate_str is not None:
            return float(rate_str) * 100.0
    return None


# ---------------------------------------------------------------------------
# JUnit XML writer (combined summary)
# ---------------------------------------------------------------------------

def _write_junit_xml(path: Path, results: List[StepResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    suites = ET.Element("testsuites", name="IJT C# Client")
    for r in results:
        suite = ET.SubElement(
            suites,
            "testsuite",
            name=r.label,
            tests=str(max(r.total, 1)),
            failures=str(r.failed),
            skipped=str(r.skipped),
            time=f"{r.duration:.3f}",
        )
        tc = ET.SubElement(suite, "testcase", name=r.label, time=f"{r.duration:.3f}")
        if r.status == "FAIL":
            ET.SubElement(tc, "failure", message=r.detail)
        elif r.status == "SKIP":
            ET.SubElement(tc, "skipped")
    tree = ET.ElementTree(suites)
    ET.indent(tree, space="  ")
    tree.write(str(path), encoding="utf-8", xml_declaration=True)


# ---------------------------------------------------------------------------
# Prerequisite check
# ---------------------------------------------------------------------------

def _check_prerequisites() -> bool:
    if not _dotnet_available():
        print(
            "ERROR: 'dotnet' was not found in PATH.\n"
            "  Install the .NET SDK from https://dotnet.microsoft.com/download\n"
            "  and ensure 'dotnet' is on your PATH.",
            file=sys.stderr,
        )
        return False
    ver = _dotnet_version()
    try:
        major = int(ver.split(".")[0])
    except (ValueError, IndexError):
        major = 0
    if major < _MIN_DOTNET_MAJOR:
        print(
            f"ERROR: dotnet {ver} found, but >= {_MIN_DOTNET_MAJOR} is required.\n"
            "  Install a newer .NET SDK from https://dotnet.microsoft.com/download",
            file=sys.stderr,
        )
        return False
    print(f"dotnet {ver}")
    return True


# ---------------------------------------------------------------------------
# Phase 1 steps
# ---------------------------------------------------------------------------

def _step_restore() -> StepResult:
    label = "dotnet restore"
    t0 = time.monotonic()
    rc, _ = _run(["dotnet", "restore", str(_SLN)])
    dur = time.monotonic() - t0
    if rc != 0:
        return StepResult(label, "PHASE 1", "FAIL", f"exit {rc}", dur)
    return StepResult(label, "PHASE 1", "PASS", "", dur)


def _step_build() -> StepResult:
    label = "dotnet build"
    t0 = time.monotonic()
    rc, stdout = _run(
        ["dotnet", "build", str(_SLN), "--no-restore", "-warnaserror",
         "--configuration", "Release"],
        capture_stdout=True,
    )
    if stdout:
        print(stdout, end="")
    dur = time.monotonic() - t0
    warnings = _parse_build_warnings(stdout)
    detail = f"{warnings} warnings"
    if rc != 0:
        return StepResult(label, "PHASE 1", "FAIL", detail, dur)
    return StepResult(label, "PHASE 1", "PASS", detail, dur)


def _step_format() -> StepResult:
    label = "dotnet format"
    t0 = time.monotonic()
    rc, _ = _run(
        ["dotnet", "format", str(_SLN), "--verify-no-changes", "--no-restore"],
    )
    dur = time.monotonic() - t0
    if rc != 0:
        return StepResult(label, "PHASE 1", "FAIL", "formatting changes needed", dur)
    return StepResult(label, "PHASE 1", "PASS", "", dur)


def _step_nuget_cve() -> StepResult:
    label = "NuGet CVE scan"
    t0 = time.monotonic()
    rc, stdout = _run(
        ["dotnet", "list", str(_SLN), "package",
         "--vulnerable", "--include-transitive"],
        capture_stdout=True,
    )
    if stdout:
        print(stdout, end="")
    dur = time.monotonic() - t0
    critical, high = _parse_nuget_vulnerabilities(stdout)
    if critical > 0 or high > 0:
        detail = f"{critical} critical, {high} high"
        return StepResult(label, "PHASE 1", "FAIL", detail, dur)
    return StepResult(label, "PHASE 1", "PASS", "0 vulnerable", dur)


def _step_nuget_outdated() -> StepResult:
    """Informational check — never fails the suite."""
    label = "NuGet outdated"
    t0 = time.monotonic()
    rc, stdout = _run(
        ["dotnet", "list", str(_SLN), "package", "--outdated"],
        capture_stdout=True,
    )
    if stdout:
        print(stdout, end="")
    dur = time.monotonic() - t0
    outdated = len(re.findall(r"^\s*>", stdout, re.MULTILINE))
    if outdated > 0:
        return StepResult(label, "PHASE 1", "WARN", f"{outdated} outdated", dur)
    return StepResult(label, "PHASE 1", "PASS", "all up-to-date", dur)


def _step_detect_secrets() -> StepResult:
    label = "detect-secrets"
    if not shutil.which("detect-secrets"):
        return StepResult(label, "PHASE 1", "SKIP", "not installed", 0.0)
    t0 = time.monotonic()
    rc, stdout = _run(
        ["detect-secrets", "scan"],
        capture_stdout=True,
    )
    dur = time.monotonic() - t0
    if rc != 0:
        return StepResult(label, "PHASE 1", "FAIL", f"exit {rc}", dur)
    with contextlib.suppress(Exception):
        import json as _json
        data = _json.loads(stdout)
        secrets_found = sum(len(v) for v in data.get("results", {}).values())
        if secrets_found > 0:
            return StepResult(label, "PHASE 1", "FAIL", f"{secrets_found} secrets found", dur)
    return StepResult(label, "PHASE 1", "PASS", "", dur)


def _step_test_unit() -> StepResult:
    """Run dotnet test with XPlat Code Coverage — live tests auto-skip via SkippableFact."""
    label = "dotnet test (unit)"
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    trx_path = _RESULTS_DIR / "tests.trx"
    t0 = time.monotonic()
    rc, _ = _run(
        [
            "dotnet", "test", str(_TEST_PROJ),
            "--no-restore",
            "--configuration", "Release",
            "--logger", "trx;LogFileName=tests.trx",
            "--results-directory", str(_RESULTS_DIR),
            "--collect", "XPlat Code Coverage",
            "--settings", str(_PROJECT_DIR / "coverlet.runsettings"),
        ],
        env={"IJT_AUTO_ACCEPT": "true"},
    )
    dur = time.monotonic() - t0
    passed, failed, skipped, total = _parse_trx(trx_path)
    detail = f"{passed}/{total}, {skipped} skipped" if skipped else f"{passed}/{total}"
    if rc != 0 or failed > 0:
        return StepResult(label, "PHASE 1", "FAIL", detail, dur, passed, failed, skipped, total)
    return StepResult(label, "PHASE 1", "PASS", detail, dur, passed, failed, skipped, total)


def _step_coverage_check() -> StepResult:
    """Parse Cobertura coverage produced by coverlet; warn if below threshold."""
    label = "Coverage"
    cov_file = _find_cobertura_file()
    if cov_file is None:
        return StepResult(label, "PHASE 1", "SKIP", "coverage.cobertura.xml not found", 0.0)
    pct = _parse_cobertura_coverage(cov_file)
    if pct is None:
        return StepResult(label, "PHASE 1", "SKIP", "could not parse coverage", 0.0)
    detail = f"{pct:.1f}% (threshold: {_COVERAGE_THRESHOLD:.0f}%)"
    if pct < _COVERAGE_THRESHOLD:
        return StepResult(label, "PHASE 1", "WARN", detail, 0.0)
    return StepResult(label, "PHASE 1", "PASS", detail, 0.0)


def _step_semgrep() -> StepResult:
    """Run Semgrep AI code review (supports C# rules); skip if not installed."""
    label = "Semgrep (AI review)"
    if not shutil.which("semgrep"):
        return StepResult(label, "PHASE 1", "SKIP", "Install: pip install semgrep", 0.0)
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    subprocess.run(
        ["semgrep", "--config=p/default", "--json",
         "--output", str(_RESULTS_DIR / "semgrep.json"), "."],
        check=False, capture_output=True, text=True, cwd=str(_PROJECT_DIR),
    )
    dur = time.monotonic() - t0
    try:
        data = json.loads((_RESULTS_DIR / "semgrep.json").read_text(encoding="utf-8"))
        findings = data.get("results", [])
        errors = [f for f in findings if f.get("extra", {}).get("severity") == "ERROR"]
        warns = [f for f in findings if f.get("extra", {}).get("severity") == "WARNING"]
        if errors:
            return StepResult(label, "PHASE 1", "FAIL",
                              f"{len(errors)} error(s), {len(warns)} warning(s)", dur)
        if warns:
            return StepResult(label, "PHASE 1", "WARN",
                              f"0 errors, {len(warns)} warning(s)", dur)
        return StepResult(label, "PHASE 1", "PASS",
                          f"{len(findings)} finding(s), none critical", dur)
    except Exception:
        return StepResult(label, "PHASE 1", "WARN", "could not parse semgrep output", dur)


# ---------------------------------------------------------------------------
# Phase 2 steps
# ---------------------------------------------------------------------------

def _resolve_server_url() -> str:
    port_env = os.environ.get("OPCUA_SERVER_PORT", "").strip()
    if port_env:
        with contextlib.suppress(ValueError):
            return f"opc.tcp://localhost:{int(port_env)}"
    return os.environ.get("OPCUA_SERVER_URL", "").strip() or _DEFAULT_SERVER_URL


def _try_launch_simulator() -> Optional[subprocess.Popen]:
    """Launch the OPC UA simulator and wait up to 30s for it to open its port.

    Checks OPCUA_SIMULATOR_EXE first, then well-known paths.
    Sets os.environ["OPCUA_SERVER_URL"] to the server's native port when launched.
    Returns a Popen handle on success, None on failure.
    """
    exe: Optional[str] = os.environ.get("OPCUA_SIMULATOR_EXE", "").strip() or None
    if not exe:
        for candidate in _WELL_KNOWN_SIMULATOR_PATHS:
            if candidate.exists():
                exe = str(candidate)
                break
    if not exe:
        return None
    exe_path = Path(exe)
    if not exe_path.exists():
        print(f"[PHASE 2] Simulator not found: {exe}", file=sys.stderr)
        return None
    print(f"[PHASE 2] Launching simulator: {exe}")
    try:
        proc = subprocess.Popen([str(exe_path)], cwd=str(exe_path.parent))
    except OSError as exc:
        print(f"[PHASE 2] Failed to launch simulator: {exc}", file=sys.stderr)
        return None
    for _ in range(30):
        time.sleep(1)
        if _is_port_reachable("localhost", _SERVER_NATIVE_PORT):
            print(f"[PHASE 2] Simulator ready on port {_SERVER_NATIVE_PORT}.")
            os.environ["OPCUA_SERVER_URL"] = f"opc.tcp://localhost:{_SERVER_NATIVE_PORT}"
            return proc
    print("[PHASE 2] Simulator did not become ready within 30s.", file=sys.stderr)
    proc.terminate()
    return None


def _step_live_tests(server_url: str) -> StepResult:
    label = "Live Tests"
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    trx_path = _RESULTS_DIR / "live-tests.trx"
    t0 = time.monotonic()
    rc, _ = _run(
        [
            "dotnet", "test", str(_TEST_PROJ),
            "--no-restore",
            "--configuration", "Release",
            "--logger", "trx;LogFileName=live-tests.trx",
            "--results-directory", str(_RESULTS_DIR),
        ],
        env={
            "IJT_AUTO_ACCEPT": "true",
            "OPCUA_SERVER_URL": server_url,
        },
    )
    dur = time.monotonic() - t0
    passed, failed, skipped, total = _parse_trx(trx_path)
    detail = f"{passed}/{total}" if not skipped else f"{passed}/{total}, {skipped} skipped"
    if rc != 0 or failed > 0:
        return StepResult(label, "PHASE 2", "FAIL", detail, dur, passed, failed, skipped, total)
    return StepResult(label, "PHASE 2", "PASS", detail, dur, passed, failed, skipped, total)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="run_all_tests.py",
        description="IJT C# Client — test runner",
    )
    group = p.add_mutually_exclusive_group()
    group.add_argument("--phase1", action="store_true", help="Build + unit tests only (no server)")
    group.add_argument("--phase2", action="store_true", help="Live integration tests only")
    p.add_argument(
        "--junit-xml",
        default="test-results/run_all_tests.xml",
        metavar="PATH",
        help="Combined JUnit XML output path (default: test-results/run_all_tests.xml)",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()

    run_phase1 = not args.phase2
    run_phase2 = not args.phase1

    _banner("IJT C# Client — Test Suite")

    if not _check_prerequisites():
        return 1

    shutil.rmtree(_RESULTS_DIR, ignore_errors=True)
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    results: List[StepResult] = []
    t_start = time.monotonic()

    skip_restore = os.environ.get("SKIP_DOTNET_RESTORE", "0").strip() in {"1", "true", "yes"}

    # -- Phase 1 --------------------------------------------------------------
    if run_phase1:
        if not skip_restore:
            r = _step_restore()
            results.append(r)
            _row(r.phase, r.label, r.status, r.detail)
            if r.status == "FAIL":
                _footer(False, time.monotonic() - t_start, results)
                _write_junit_xml(_PROJECT_DIR / args.junit_xml, results)
                return 1

        r = _step_build()
        results.append(r)
        _row(r.phase, r.label, r.status, r.detail)
        if r.status == "FAIL":
            _footer(False, time.monotonic() - t_start, results)
            _write_junit_xml(_PROJECT_DIR / args.junit_xml, results)
            return 1

        r = _step_format()
        results.append(r)
        _row(r.phase, r.label, r.status, r.detail)

        r = _step_nuget_cve()
        results.append(r)
        _row(r.phase, r.label, r.status, r.detail)

        r = _step_nuget_outdated()
        results.append(r)
        _row(r.phase, r.label, r.status, r.detail)

        r = _step_detect_secrets()
        results.append(r)
        _row(r.phase, r.label, r.status, r.detail)

        r = _step_test_unit()
        results.append(r)
        _row(r.phase, r.label, r.status, r.detail)

        r = _step_coverage_check()
        results.append(r)
        _row(r.phase, r.label, r.status, r.detail)

        r = _step_semgrep()
        results.append(r)
        _row(r.phase, r.label, r.status, r.detail)

    # -- Phase 2 --------------------------------------------------------------
    if run_phase2:
        sim_proc: Optional[subprocess.Popen] = None
        user_url_was_set = bool(os.environ.get("OPCUA_SERVER_URL"))
        if not user_url_was_set:
            server_url = _resolve_server_url()
            host, port = _parse_opcua_endpoint(server_url)
            server_ready = _is_port_reachable(host, port)
            if not server_ready and not _is_port_reachable("localhost", _SERVER_NATIVE_PORT):
                sim_proc = _try_launch_simulator()
                server_ready = sim_proc is not None
            elif not server_ready and _is_port_reachable("localhost", _SERVER_NATIVE_PORT):
                os.environ["OPCUA_SERVER_URL"] = f"opc.tcp://localhost:{_SERVER_NATIVE_PORT}"
                server_ready = True
        else:
            server_url = _resolve_server_url()
            host, port = _parse_opcua_endpoint(server_url)
            server_ready = _is_port_reachable(host, port)
        try:
            # Re-read URL in case _try_launch_simulator updated it
            server_url = _resolve_server_url()
            if server_ready:
                print(f"[PHASE 2] OPC UA server reachable at {server_url}")
                r = _step_live_tests(server_url)
            else:
                print(
                    f"[PHASE 2] OPC UA server not reachable at {server_url}"
                    " — skipping live tests"
                )
                r = StepResult(
                    "Live Tests", "PHASE 2", "SKIP",
                    f"server not reachable ({server_url})",
                )
        finally:
            if sim_proc is not None:
                sim_proc.terminate()
                try:
                    sim_proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    sim_proc.kill()
                if not user_url_was_set:
                    os.environ.pop("OPCUA_SERVER_URL", None)
        results.append(r)
        _row(r.phase, r.label, r.status, r.detail)

    # -- Summary --------------------------------------------------------------
    elapsed = time.monotonic() - t_start
    any_fail = any(r.status in {"FAIL", "ERROR"} for r in results)
    _footer(not any_fail, elapsed, results)

    _write_junit_xml(_PROJECT_DIR / args.junit_xml, results)

    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())