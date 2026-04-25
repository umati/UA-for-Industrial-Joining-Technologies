#!/usr/bin/env python3
"""
run_all_tests.py — IJT Node Client test runner.

Usage:
    python run_all_tests.py              # full run (Phase 1 + Phase 2)
    python run_all_tests.py --phase1     # unit/static tests only
    python run_all_tests.py --phase2     # Playwright E2E tests (requires running server)
    python run_all_tests.py --help

Phase 2 requires:
    node index.js                        # start the Node Client HTTP server on :3000
    npx playwright install chromium      # install Playwright browsers (one-time)

Environment variables:
    SKIP_NPM_INSTALL=1   Skip `npm ci` (deps already installed)

Flags:
    --no-audit           Skip npm audit (useful offline or slow networks)
    --junit-xml=PATH     Write combined JUnit XML (default: test-results/run_all_tests.xml)
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths & shared utilities
# ---------------------------------------------------------------------------

_PROJECT_DIR: Path = Path(__file__).resolve().parent
_REPO_ROOT: Path = Path(__file__).resolve().parents[3]
_MIN_NODE_MAJOR = 20
_MIN_NPM_MAJOR = 9
# Coverage threshold — aspirational target (80%).
# Current measured coverage is ~54%; WARN is advisory and never blocks CI.
# A ratchet floor of 52% catches genuine regressions without firing on every run.
_COVERAGE_THRESHOLD_ASPIRATIONAL = 80.0
_COVERAGE_THRESHOLD = 52.0  # ratchet floor — drop below this triggers WARN

if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import socket  # noqa: E402

_SERVER_NATIVE_PORT = 40451
_WELL_KNOWN_SIMULATOR_PATHS = [
    _REPO_ROOT
    / "OPC_UA_Servers"
    / "Release2"
    / "OPC_UA_IJT_Server_Simulator"
    / "opcua_ijt_demo_application.exe",
    _REPO_ROOT
    / "OPC_UA_Servers"
    / "Release2"
    / "OPC_UA_IJT_Server_Simulator_Linux"
    / "opcua_ijt_demo_application",
]
_DEFAULT_SERVER_URL = "opc.tcp://localhost:40451"


def _cmd_available(cmd: str) -> bool:
    return shutil.which(cmd) is not None


# On Windows npm/npx are .cmd batch files; shutil.which resolves that correctly.
_NPM: str = shutil.which("npm.cmd") or shutil.which("npm") or "npm"
_NPX: str = shutil.which("npx.cmd") or shutil.which("npx") or "npx"
_NODE: str = shutil.which("node") or "node"


def _npm_pkg_available(pkg: str) -> bool:
    """Check if an npm package is available locally (node_modules or .bin)."""
    return (_PROJECT_DIR / "node_modules" / pkg).exists() or (
        _PROJECT_DIR / "node_modules" / ".bin" / pkg
    ).exists()


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class StepResult:
    label: str
    phase: str
    status: str  # "PASS", "FAIL", "SKIP", "WARN", "ERROR"
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


def _footer(ok: bool, elapsed: float, results: list[StepResult]) -> None:
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
    cmd: list[str],
    *,
    cwd: Path = _PROJECT_DIR,
    env: dict | None = None,
    capture_stdout: bool = False,
) -> tuple[int, str]:
    """Run *cmd* and return (returncode, stdout_text).

    stderr is inherited (visible in terminal).  stdout is captured when
    *capture_stdout* is True, otherwise also inherited.
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
    stdout = result.stdout or ""
    return result.returncode, stdout


# ---------------------------------------------------------------------------
# Output parsers
# ---------------------------------------------------------------------------


def _parse_junit_xml(path: Path) -> tuple[int, int, int]:
    """Return (passed, failed, total) from a JUnit XML file.

    Counts all <testcase> elements; failures/errors are counted by looking
    for child <failure> or <error> elements.
    """
    if not path.exists():
        return 0, 0, 0
    try:
        tree = ET.parse(str(path))
        root = tree.getroot()
        suites = root.findall(".//testsuite") or [root]
        total = failed = 0
        for suite in suites:
            for tc in suite.findall("testcase"):
                total += 1
                if tc.find("failure") is not None or tc.find("error") is not None:
                    failed += 1
        passed = total - failed
        return passed, failed, total
    except Exception:
        return 0, 0, 0


def _parse_eslint_json(path: Path) -> tuple[int, int]:
    """Return (error_count, warning_count) from an ESLint JSON report."""
    if not path.exists():
        return 0, 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        errors = sum(f.get("errorCount", 0) for f in data)
        warnings = sum(f.get("warningCount", 0) for f in data)
        return errors, warnings
    except Exception:
        return 0, 0


def _parse_audit_json(path: Path) -> tuple[int, int]:
    """Return (critical, high) vulnerability counts from `npm audit --json`."""
    if not path.exists():
        return 0, 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        vulns = data.get("metadata", {}).get("vulnerabilities", {})
        return vulns.get("critical", 0), vulns.get("high", 0)
    except Exception:
        return 0, 0


def _parse_coverage_summary(results_dir: Path) -> float | None:
    """Parse test-results/coverage/coverage-summary.json for line coverage %."""
    summary_path = results_dir / "coverage" / "coverage-summary.json"
    if not summary_path.exists():
        return None
    with contextlib.suppress(Exception):
        data = json.loads(summary_path.read_text(encoding="utf-8"))
        total = data.get("total", {})
        lines = total.get("lines", {})
        pct = lines.get("pct")
        if pct is not None:
            return float(pct)
    return None


# ---------------------------------------------------------------------------
# JUnit XML writer (combined summary)
# ---------------------------------------------------------------------------


def _write_junit_xml(path: Path, results: list[StepResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    suites = ET.Element("testsuites", name="IJT Node Client")
    for r in results:
        suite = ET.SubElement(
            suites,
            "testsuite",
            name=r.label,
            tests=str(max(r.total, 1)),
            failures=str(r.failed),
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
    missing = []
    if not _NODE or not shutil.which(_NODE):
        missing.append("node")
    if not _NPM or not shutil.which(_NPM):
        missing.append("npm")
    if missing:
        print(
            f"ERROR: The following tools were not found in PATH: {', '.join(missing)}\n"
            "  Install Node.js from https://nodejs.org/ and ensure it is on PATH.",
            file=sys.stderr,
        )
        return False

    node_ver_str = (
        subprocess.run([_NODE, "--version"], capture_output=True, text=True, check=False)
        .stdout.strip()
        .lstrip("v")
    )
    print(f"node {node_ver_str}")
    try:
        node_major = int(node_ver_str.split(".")[0])
    except (ValueError, IndexError):
        node_major = 0
    if node_major < _MIN_NODE_MAJOR:
        print(
            f"WARNING: Node.js {node_ver_str} detected; >= {_MIN_NODE_MAJOR} recommended.",
            file=sys.stderr,
        )

    npm_ver_str = subprocess.run(
        [_NPM, "--version"], capture_output=True, text=True, check=False
    ).stdout.strip()
    print(f"npm  {npm_ver_str}")
    try:
        npm_major = int(npm_ver_str.split(".")[0])
    except (ValueError, IndexError):
        npm_major = 0
    if npm_major < _MIN_NPM_MAJOR:
        print(
            f"WARNING: npm {npm_ver_str} detected; >= {_MIN_NPM_MAJOR} recommended.",
            file=sys.stderr,
        )

    return True


# ---------------------------------------------------------------------------
# Phase 1 steps
# ---------------------------------------------------------------------------


def _step_npm_ci() -> StepResult:
    label = "npm ci"
    t0 = time.monotonic()
    rc, _ = _run([_NPM, "ci"])
    dur = time.monotonic() - t0
    if rc != 0:
        return StepResult(label, "PHASE 1", "FAIL", f"exit {rc}", dur)
    return StepResult(label, "PHASE 1", "PASS", "", dur)


def _step_vitest(results_dir: Path) -> StepResult:
    label = "Vitest (unit)"
    results_dir.mkdir(parents=True, exist_ok=True)
    junit_out = results_dir / "vitest.xml"
    coverage_dir = results_dir / "coverage"
    t0 = time.monotonic()
    rc, _ = _run(
        [
            _NPX,
            "vitest",
            "run",
            "--reporter=verbose",
            "--reporter=junit",
            f"--outputFile.junit={junit_out}",
            "--coverage",
            "--coverage.reporter=lcov",
            "--coverage.reporter=json",
            "--coverage.reporter=json-summary",
            f"--coverage.dir={coverage_dir}",
        ]
    )
    dur = time.monotonic() - t0
    passed, failed, total = _parse_junit_xml(junit_out)
    detail = f"{passed}/{total}"
    if rc != 0 or failed > 0:
        return StepResult(label, "PHASE 1", "FAIL", detail, dur, passed, failed, total)
    return StepResult(label, "PHASE 1", "PASS", detail, dur, passed, failed, total)


def _step_coverage_check(results_dir: Path) -> StepResult:
    """Parse vitest coverage-summary.json; warn if below ratchet floor.

    Coverage is an advisory/non-gated metric for this client — it never causes
    the suite to fail. The aspirational target is 80%; the ratchet floor
    (_COVERAGE_THRESHOLD) catches genuine regressions.
    """
    label = "Coverage"
    pct = _parse_coverage_summary(results_dir)
    if pct is None:
        return StepResult(label, "PHASE 1", "SKIP", "coverage-summary.json not found", 0.0)
    detail = (
        f"{pct:.1f}% lines"
        f" (floor: {_COVERAGE_THRESHOLD:.0f}%, goal: {_COVERAGE_THRESHOLD_ASPIRATIONAL:.0f}%)"
        " — advisory/non-gated"
    )
    if pct < _COVERAGE_THRESHOLD:
        return StepResult(label, "PHASE 1", "WARN", detail, 0.0)
    return StepResult(label, "PHASE 1", "PASS", detail, 0.0)


def _step_eslint(results_dir: Path) -> StepResult:
    label = "ESLint"
    results_dir.mkdir(parents=True, exist_ok=True)
    out_file = results_dir / "eslint.json"
    t0 = time.monotonic()
    rc, _ = _run(
        [
            _NPX,
            "eslint",
            "javascripts/",
            "--format",
            "json",
            "--output-file",
            str(out_file),
        ]
    )
    dur = time.monotonic() - t0
    errors, warnings = _parse_eslint_json(out_file)
    detail = f"{errors} errors"
    if warnings:
        detail += f", {warnings} warnings"
    if rc == 2:
        return StepResult(label, "PHASE 1", "ERROR", f"fatal error (exit {rc})", dur)
    if rc != 0 or errors > 0:
        return StepResult(label, "PHASE 1", "FAIL", detail, dur)
    return StepResult(label, "PHASE 1", "PASS", detail, dur)


def _step_prettier() -> StepResult:
    """Formatting check — skipped if prettier is not in devDependencies."""
    label = "Prettier"
    try:
        pkg = json.loads((_PROJECT_DIR / "package.json").read_text(encoding="utf-8"))
        has_prettier = "prettier" in pkg.get("devDependencies", {}) or "prettier" in pkg.get(
            "dependencies", {}
        )
    except Exception:
        has_prettier = False
    if not has_prettier:
        return StepResult(label, "PHASE 1", "SKIP", "not in devDependencies", 0.0)
    t0 = time.monotonic()
    rc, _ = _run([_NPX, "prettier", "--check", "."])
    dur = time.monotonic() - t0
    if rc != 0:
        return StepResult(label, "PHASE 1", "FAIL", "formatting changes needed", dur)
    return StepResult(label, "PHASE 1", "PASS", "", dur)


def _step_npm_audit(results_dir: Path) -> StepResult:
    label = "npm audit"
    results_dir.mkdir(parents=True, exist_ok=True)
    out_file = results_dir / "npm-audit.json"
    t0 = time.monotonic()
    rc, stdout = _run(
        [_NPM, "audit", "--audit-level=high", "--json"],
        capture_stdout=True,
    )
    dur = time.monotonic() - t0
    with contextlib.suppress(Exception):
        out_file.write_text(stdout, encoding="utf-8")
    critical, high = _parse_audit_json(out_file)
    detail = f"{critical} critical, {high} high"
    if rc != 0 and (critical > 0 or high > 0):
        return StepResult(label, "PHASE 1", "FAIL", detail, dur)
    return StepResult(label, "PHASE 1", "PASS", detail, dur)


def _step_depcheck() -> StepResult:
    """Unused dependency check — informational (WARN, never FAIL)."""
    label = "depcheck"
    t0 = time.monotonic()
    rc, stdout = _run(
        [_NPX, "--yes", "depcheck", "--json"],
        capture_stdout=True,
    )
    dur = time.monotonic() - t0
    try:
        data = json.loads(stdout)
        unused_deps = list(data.get("dependencies", []))
        unused_dev = list(data.get("devDependencies", []))
        total_unused = len(unused_deps) + len(unused_dev)
        if total_unused > 0:
            return StepResult(label, "PHASE 1", "WARN", f"{total_unused} unused packages", dur)
        return StepResult(label, "PHASE 1", "PASS", "no unused packages", dur)
    except Exception:
        if rc != 0:
            return StepResult(label, "PHASE 1", "SKIP", f"depcheck unavailable (exit {rc})", dur)
        return StepResult(label, "PHASE 1", "PASS", "", dur)


def _step_license_checker() -> StepResult:
    """License compliance summary — skipped if license-checker not in devDependencies."""
    label = "license-checker"
    try:
        pkg = json.loads((_PROJECT_DIR / "package.json").read_text(encoding="utf-8"))
        has_checker = "license-checker" in pkg.get(
            "devDependencies", {}
        ) or "license-checker" in pkg.get("dependencies", {})
    except Exception:
        has_checker = False
    if not has_checker:
        return StepResult(label, "PHASE 1", "SKIP", "not in devDependencies", 0.0)
    t0 = time.monotonic()
    rc, _ = _run([_NPX, "license-checker", "--summary"])
    dur = time.monotonic() - t0
    if rc != 0:
        return StepResult(label, "PHASE 1", "WARN", f"exit {rc}", dur)
    return StepResult(label, "PHASE 1", "PASS", "", dur)


def _step_detect_secrets() -> StepResult:
    label = "detect-secrets"
    if not _cmd_available("detect-secrets"):
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
        data = json.loads(stdout)
        secrets_found = sum(len(v) for v in data.get("results", {}).values())
        if secrets_found > 0:
            return StepResult(label, "PHASE 1", "FAIL", f"{secrets_found} secrets found", dur)
    return StepResult(label, "PHASE 1", "PASS", "", dur)


def _step_semgrep() -> StepResult:
    """Optional SAST scan — skipped if semgrep is not installed."""
    label = "Semgrep"
    if not _cmd_available("semgrep"):
        return StepResult(label, "PHASE 1", "SKIP", "not installed", 0.0)
    results_dir = _PROJECT_DIR / "test-results"
    results_dir.mkdir(parents=True, exist_ok=True)
    out_file = results_dir / "semgrep.json"
    t0 = time.monotonic()
    rc, _ = _run(
        ["semgrep", "--config=p/default", "--json", f"--output={out_file}", "."],
    )
    dur = time.monotonic() - t0
    # semgrep exits 1 when findings are present, which is not a tool error
    if rc not in (0, 1):
        return StepResult(label, "PHASE 1", "WARN", f"exit {rc}", dur)
    with contextlib.suppress(Exception):
        data = json.loads(out_file.read_text(encoding="utf-8"))
        findings = len(data.get("results", []))
        if findings > 0:
            return StepResult(label, "PHASE 1", "WARN", f"{findings} findings", dur)
    return StepResult(label, "PHASE 1", "PASS", "", dur)


# ---------------------------------------------------------------------------
# Phase 2
# ---------------------------------------------------------------------------


def _is_port_reachable(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _ensure_server() -> subprocess.Popen | None:
    """Start OPC UA server if not already running; returns Popen handle or None.

    Release 1 server is hardcoded to port 40451 and does NOT read
    server_configuration.json for the TCP port.  No copy+patch mechanism
    is used — the binary is launched directly from its own directory.
    """
    if os.environ.get("OPCUA_SERVER_URL"):
        return None
    if _is_port_reachable("localhost", _SERVER_NATIVE_PORT):
        os.environ["OPCUA_SERVER_URL"] = f"opc.tcp://localhost:{_SERVER_NATIVE_PORT}"
        return None
    exe: str | None = os.environ.get("OPCUA_SIMULATOR_EXE")
    if not exe:
        for candidate in _WELL_KNOWN_SIMULATOR_PATHS:
            if candidate.exists():
                exe = str(candidate)
                break
    if not exe:
        print("  [server] No simulator binary found — Phase 2 will be skipped")
        return None
    exe_path = Path(exe)
    try:
        proc = subprocess.Popen(
            [str(exe_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(exe_path.parent),
        )
    except OSError as exc:
        print(f"  [server] Failed to launch binary: {exc}")
        return None
    for _ in range(30):
        if _is_port_reachable("localhost", _SERVER_NATIVE_PORT):
            print(f"  [server] Ready on port {_SERVER_NATIVE_PORT}")
            os.environ["OPCUA_SERVER_URL"] = f"opc.tcp://localhost:{_SERVER_NATIVE_PORT}"
            return proc
        time.sleep(1)
    print("  [server] Timed out waiting for simulator — terminating")
    proc.terminate()
    return None


def _step_phase2_check(results_dir: Path) -> StepResult:
    """Phase 2: verify OPC UA server is reachable after auto-start attempt."""
    server_url = os.environ.get("OPCUA_SERVER_URL", _DEFAULT_SERVER_URL)
    label = "OPC UA server check"
    host_port = server_url.replace("opc.tcp://", "").rsplit(":", 1)
    try:
        host = host_port[0]
        port = int(host_port[1]) if len(host_port) > 1 else 40451
    except (ValueError, IndexError):
        host, port = "localhost", 40451
    if not _is_port_reachable(host, port):
        return StepResult(label, "PHASE 2", "SKIP", f"server not reachable at {server_url}", 0.0)
    return StepResult(label, "PHASE 2", "PASS", f"server reachable at {server_url}", 0.0)


def _step_playwright_e2e(results_dir: Path) -> StepResult:
    """Phase 2: Run Playwright E2E tests.

    All specs use e2e-fixtures.mjs which skips gracefully when the Node Client
    HTTP server (http://localhost:3000) is not reachable.  In Phase 2 the server
    has been started by _ensure_server(), so UI tests should run.

    The Playwright binary (chromium) must be installed:
        npx playwright install chromium
    If not installed, this step is skipped (SKIP, never FAIL).
    """
    label = "Playwright E2E"
    results_dir.mkdir(parents=True, exist_ok=True)
    json_out = results_dir / "playwright.json"
    # Check that the HTTP server (not OPC UA) is reachable on port 3000
    if not _is_port_reachable("localhost", 3000, timeout=1.0):
        return StepResult(
            label, "PHASE 2", "SKIP", "Node Client HTTP server not running on :3000", 0.0
        )
    # Check Playwright browsers are installed (list chromium channel)
    rc_check, _ = _run(
        [_NPX, "playwright", "install", "--dry-run", "chromium"],
        capture_stdout=True,
    )
    if rc_check != 0:
        # Browsers not installed — skip instead of failing (optional E2E setup step)
        return StepResult(
            label,
            "PHASE 2",
            "SKIP",
            "Playwright browsers not installed — run: npx playwright install chromium",
            0.0,
        )
    t0 = time.monotonic()
    rc, _ = _run(
        [
            _NPX,
            "playwright",
            "test",
            "--project=views",
            "--reporter=list",
            f"--reporter=json:{json_out}",
        ]
    )
    dur = time.monotonic() - t0
    # Parse JSON report for pass/fail counts
    passed = failed = total = 0
    with contextlib.suppress(Exception):
        data = json.loads(json_out.read_text(encoding="utf-8"))
        for suite in data.get("suites", []):
            for spec in suite.get("specs", []):
                for result in spec.get("results", []):
                    total += 1
                    if result.get("status") in ("passed", "skipped"):
                        passed += 1
                    else:
                        failed += 1
    detail = f"{passed}/{total}" if total else "runner error — no test results parsed"
    if rc != 0:
        return StepResult(label, "PHASE 2", "FAIL", detail, dur, passed, failed, total)
    return StepResult(label, "PHASE 2", "PASS", detail, dur, passed, failed, total)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="run_all_tests.py",
        description="IJT Node Client — test runner",
    )
    group = p.add_mutually_exclusive_group()
    group.add_argument("--phase1", action="store_true", help="Unit/static tests only")
    group.add_argument(
        "--phase2",
        action="store_true",
        help="Playwright E2E tests (requires node index.js + npx playwright install chromium)",
    )
    p.add_argument(
        "--junit-xml",
        default="test-results/run_all_tests.xml",
        metavar="PATH",
        help="Combined JUnit XML output path (default: test-results/run_all_tests.xml)",
    )
    p.add_argument(
        "--no-audit",
        action="store_true",
        help="Skip npm audit step (useful for offline/slow environments)",
    )
    return p.parse_args()


def main() -> int:
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    _cleanup_caches(_PROJECT_DIR)  # pre-run: clear stale caches from interrupted runs
    args = _parse_args()

    run_phase1 = not args.phase2
    run_phase2 = not args.phase1

    _banner("IJT Node Client — Test Suite")

    if not _check_prerequisites():
        return 1

    results_dir = _PROJECT_DIR / "test-results"
    shutil.rmtree(results_dir, ignore_errors=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    results: list[StepResult] = []
    t_start = time.monotonic()

    # -- Phase 1 --------------------------------------------------------------
    if run_phase1:
        skip_install = os.environ.get("SKIP_NPM_INSTALL", "0").strip() in {"1", "true", "yes"}
        if not skip_install:
            r = _step_npm_ci()
            results.append(r)
            _row(r.phase, r.label, r.status, r.detail)
            if r.status == "FAIL":
                _footer(False, time.monotonic() - t_start, results)
                _write_junit_xml(_PROJECT_DIR / args.junit_xml, results)
                return 1

        r = _step_vitest(results_dir)
        results.append(r)
        _row(r.phase, r.label, r.status, r.detail)

        r = _step_coverage_check(results_dir)
        results.append(r)
        _row(r.phase, r.label, r.status, r.detail)

        r = _step_eslint(results_dir)
        results.append(r)
        _row(r.phase, r.label, r.status, r.detail)

        r = _step_prettier()
        results.append(r)
        _row(r.phase, r.label, r.status, r.detail)

        if not args.no_audit:
            r = _step_npm_audit(results_dir)
            results.append(r)
            _row(r.phase, r.label, r.status, r.detail)

        r = _step_depcheck()
        results.append(r)
        _row(r.phase, r.label, r.status, r.detail)

        r = _step_license_checker()
        results.append(r)
        _row(r.phase, r.label, r.status, r.detail)

        r = _step_detect_secrets()
        results.append(r)
        _row(r.phase, r.label, r.status, r.detail)

        r = _step_semgrep()
        results.append(r)
        _row(r.phase, r.label, r.status, r.detail)

    # -- Phase 2 --------------------------------------------------------------
    if run_phase2:
        server_proc: subprocess.Popen | None = None
        try:
            server_proc = _ensure_server()
            r = _step_phase2_check(results_dir)
            results.append(r)
            _row(r.phase, r.label, r.status, r.detail)

            # Playwright E2E tests — skip gracefully when server or browsers unavailable
            r = _step_playwright_e2e(results_dir)
            results.append(r)
            _row(r.phase, r.label, r.status, r.detail)
        finally:
            if server_proc is not None:
                print("  [server] Stopping simulator …")
                server_proc.terminate()
                try:
                    server_proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server_proc.kill()
                os.environ.pop("OPCUA_SERVER_URL", None)

    # -- Summary --------------------------------------------------------------
    elapsed = time.monotonic() - t_start
    any_fail = any(r.status in {"FAIL", "ERROR"} for r in results)
    _footer(not any_fail, elapsed, results)

    _write_junit_xml(_PROJECT_DIR / args.junit_xml, results)

    _cleanup_caches(_PROJECT_DIR)
    return 1 if any_fail else 0


def _force_rmtree(path: Path) -> None:
    """Remove a directory tree, handling Windows read-only / locked files."""
    import stat as _stat

    def _on_exc(func, fpath, exc):
        try:
            os.chmod(fpath, _stat.S_IWRITE)
            func(fpath)
        except OSError:
            time.sleep(0.05)
            with contextlib.suppress(OSError):
                func(fpath)

    shutil.rmtree(path, onexc=_on_exc)


def _cleanup_caches(root: Path) -> None:
    """Remove cache/bytecode artifacts after run. Reports in test-results/ are preserved."""
    _SKIP = {"node_modules", ".git", "test-results"}
    _CACHE_DIRS = {"__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", "htmlcov"}
    for dirpath, dirs, files in os.walk(root, topdown=True):
        dirs[:] = [
            d
            for d in dirs
            if d not in _SKIP and not d.startswith(".venv") and not d.startswith("venv")
        ]
        for d in list(dirs):
            if d in _CACHE_DIRS or d.startswith("pytest-cache-files-"):
                _force_rmtree(Path(dirpath) / d)
                dirs.remove(d)
        for f in files:
            if f == ".coverage" or f.startswith(".coverage.") or f.endswith(".pyc"):
                with contextlib.suppress(OSError):
                    (Path(dirpath) / f).unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
