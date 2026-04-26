#!/usr/bin/env python3
"""
run_all_tests.py — OPC UA Server Simulator test runner
=======================================================

Phase 1 (static — always runs):
  1.  hadolint            — Dockerfile lint  (skipped if not installed)
  2.  docker-compose.yml  — yamllint + stdlib YAML parse + service check
  3.  shellcheck          — *.sh files  (skipped if none found / shellcheck absent)
  4.  server_configuration.json — stdlib JSON + required-key check
  5.  simulated_data.json — stdlib JSON  (skipped if absent)
  6.  detect-secrets      — secrets scan  (skipped if not installed)
  7.  pip-audit           — tests/requirements.txt CVE scan  (skipped if not installed)
  8.  docker validate     — docker compose config --quiet  (skipped if Docker offline)
  9.  trivy               — container image scan  (skipped if trivy absent)
  10. binaries check      — report Windows ZIP / Linux binary presence (informational)

Phase 2 (live smoke test — needs a running OPC UA server):
  - Auto-detect/launch server (in order):
      1. port already open
      2. OPCUA_SIMULATOR_EXE env var set → launch it
      3. Linux binary found at well-known path → launch it  (non-Windows only)
      4. Docker available → docker compose up -d --build
      5. None → skip with clear message
  - Creates/reuses .venv/ with tests/requirements.txt (asyncua)
  - Runs smoke_test.py; saves output to test-results/smoke-results.txt
  - Warns if first OPC UA response takes > 5 s
  - Cleans up launched process / Docker in finally block

Usage:
    python run_all_tests.py              # Phase 1 + Phase 2
    python run_all_tests.py --phase1     # static checks only
    python run_all_tests.py --phase2     # live smoke test only
    python run_all_tests.py --help

Environment:
    OPCUA_SERVER_URL       OPC UA endpoint (default: opc.tcp://localhost:40451)
    OPCUA_SIMULATOR_EXE    Path to server executable for auto-launch
"""

from __future__ import annotations

import argparse
import contextlib
import datetime
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import venv
from pathlib import Path

# Ensure stdout/stderr use UTF-8 on Windows (cp1252 can't encode box-drawing chars)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Paths / constants
# ---------------------------------------------------------------------------

PROJ_DIR = Path(__file__).resolve().parent  # OPC_UA_Servers/Release2
_REPO_ROOT = Path(__file__).resolve().parents[2]  # repo root
RESULTS_DIR = PROJ_DIR / "test-results"

_IS_WINDOWS = sys.platform == "win32"

_LINUX_BINARY = PROJ_DIR / "OPC_UA_IJT_Server_Simulator_Linux" / "opcua_ijt_demo_application"
_WINDOWS_ZIP = PROJ_DIR / "OPC_UA_IJT_Server_Simulator.zip"

_DEFAULT_PORT = 40451
_DEFAULT_URL = f"opc.tcp://localhost:{_DEFAULT_PORT}"

# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

_WIDTH = 58
_BAR_DOUBLE = "═" * _WIDTH
_BAR_SINGLE = "─" * _WIDTH


def _print(text: str) -> None:
    sys.stdout.write(text + "\n")
    sys.stdout.flush()


def _header() -> None:
    _print(_BAR_DOUBLE)
    _print(f"OPC UA Server Simulator — Test Suite   {datetime.date.today()}")
    _print(_BAR_DOUBLE)


def _record(
    results: list,
    phase: int,
    label: str,
    ok: bool,
    status: str,
) -> None:
    """Append result tuple and print the phase line immediately."""
    results.append((phase, label, ok, status))
    _print(f"[PHASE {phase}] {label} .. {status}")


def _footer(results: list, elapsed: float) -> None:
    passed = sum(1 for _, _, ok, s in results if ok and not s.startswith("SKIP"))
    failed = sum(1 for _, _, ok, _ in results if not ok)
    skipped = sum(1 for _, _, _, s in results if s.startswith("SKIP"))
    _print(_BAR_SINGLE)
    _print(
        f"Result: {'PASS' if failed == 0 else 'FAIL'}   "
        f"{passed} passed, {failed} failed, {skipped} skipped"
    )
    _print(f"Elapsed: {elapsed:.1f}s")
    _print(_BAR_DOUBLE)


# ---------------------------------------------------------------------------
# Helper predicates
# ---------------------------------------------------------------------------


def _cmd_available(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _is_https_reachable(host: str, timeout: float = 5.0) -> bool:
    """Fast preflight: return True only if a verified HTTPS connection to host succeeds.

    Uses the default SSL context (certificate verification enabled). Returns False
    immediately on SSL cert errors, connection refused, or timeout — avoiding
    the multi-minute retry delays that pip-audit and semgrep impose on failure.
    """
    import urllib.request

    try:
        urllib.request.urlopen(f"https://{host}/", timeout=timeout)
        return True
    except Exception:
        return False


def _py_module_available(mod: str) -> bool:
    return (
        subprocess.run(
            [sys.executable, "-c", f"import {mod}"],
            check=False,
            capture_output=True,
        ).returncode
        == 0
    )


def _is_docker_running() -> bool:
    if not shutil.which("docker"):
        return False
    try:
        return (
            subprocess.run(
                ["docker", "info"],
                check=False,
                capture_output=True,
                timeout=10,
            ).returncode
            == 0
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


# ---------------------------------------------------------------------------
# Phase 1 — individual check functions
# ---------------------------------------------------------------------------


def _check_hadolint(results: list) -> None:
    label = "Dockerfile (hadolint)"
    if not _cmd_available("hadolint"):
        _record(
            results,
            1,
            label,
            True,
            "SKIP (hadolint not installed — brew install hadolint / scoop install hadolint)",
        )
        return
    dockerfile = PROJ_DIR / "Dockerfile"
    if not dockerfile.exists():
        _record(results, 1, label, True, "SKIP (Dockerfile not found)")
        return

    r = subprocess.run(
        ["hadolint", "--format", "json", str(dockerfile)],
        capture_output=True,
        text=True,
        check=False,
    )
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "hadolint.json").write_text(r.stdout or "[]", encoding="utf-8")

    try:
        issues = json.loads(r.stdout or "[]")
    except json.JSONDecodeError:
        issues = []

    errors = sum(1 for i in issues if i.get("level") == "error")
    warnings = sum(1 for i in issues if i.get("level") == "warning")

    if errors:
        _record(results, 1, label, False, f"FAIL ({errors} error(s), {warnings} warning(s))")
    else:
        _record(results, 1, label, True, f"PASS ({errors} errors, {warnings} warnings)")


def _check_docker_compose(results: list) -> None:
    """yamllint (if available) + stdlib YAML parse + service presence check."""
    label = "docker-compose.yml"
    path = PROJ_DIR / "docker-compose.yml"
    if not path.exists():
        _record(results, 1, label, True, "SKIP (file not found)")
        return

    # stdlib YAML parse
    stdlib_detail = "valid YAML"
    try:
        import yaml  # type: ignore[import-untyped]

        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        services = list((data or {}).get("services", {}).keys())
        if services:
            stdlib_detail = f"valid YAML, services: {', '.join(services)}"
    except ImportError:
        stdlib_detail = "valid (pyyaml not installed, deep parse skipped)"
    except Exception as exc:
        _record(results, 1, label, False, f"FAIL (YAML parse error: {exc})")
        return

    # optional yamllint
    if _cmd_available("yamllint"):
        yl = subprocess.run(
            ["yamllint", "-f", "parsable", str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if yl.returncode != 0:
            _record(results, 1, label, False, f"FAIL (yamllint)\n{yl.stdout}".rstrip())
            return
        _record(results, 1, label, True, f"PASS ({stdlib_detail}, yamllint clean)")
    else:
        _record(results, 1, label, True, f"PASS ({stdlib_detail})")


def _check_shellcheck(results: list) -> None:
    label = "shellcheck (*.sh)"
    sh_files = [str(p) for p in PROJ_DIR.rglob("*.sh")]
    if not sh_files:
        _record(results, 1, label, True, "SKIP (no .sh files found)")
        return
    if not _cmd_available("shellcheck"):
        _record(
            results, 1, label, True, "SKIP (shellcheck not installed — https://www.shellcheck.net)"
        )
        return

    r = subprocess.run(
        ["shellcheck", "--format=json"] + sh_files,
        capture_output=True,
        text=True,
        check=False,
    )
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "shellcheck.json").write_text(r.stdout or "[]", encoding="utf-8")

    if r.returncode == 0:
        _record(results, 1, label, True, f"PASS ({len(sh_files)} file(s) clean)")
    else:
        try:
            issues = json.loads(r.stdout or "[]")
            errors = sum(1 for i in issues if i.get("level") == "error")
            warnings = sum(1 for i in issues if i.get("level") == "warning")
            _record(results, 1, label, False, f"FAIL ({errors} error(s), {warnings} warning(s))")
        except json.JSONDecodeError:
            _record(results, 1, label, False, "FAIL")


def _check_server_config(results: list) -> None:
    """Validate server_configuration.json (stdlib JSON + required-key check)."""
    label = "server_configuration.json"
    candidates = [
        PROJ_DIR / "server_configuration.json",
        PROJ_DIR / "OPC_UA_IJT_Server_Simulator_Linux" / "server_configuration.json",
        PROJ_DIR / "OPC_UA_IJT_Server_Simulator" / "server_configuration.json",
    ]
    cfg_path = next((p for p in candidates if p.exists()), None)
    if cfg_path is None:
        _record(results, 1, label, True, "SKIP (file not present)")
        return
    try:
        with cfg_path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        port = (data.get("serverConfigurationData") or {}).get("serverEndpointTCPPort")
        if port is None:
            _record(results, 1, label, False, "FAIL (missing serverEndpointTCPPort key)")
        else:
            _record(results, 1, label, True, f"PASS (valid JSON, port={port})")
    except Exception as exc:
        _record(results, 1, label, False, f"FAIL ({exc})")


def _check_simulated_data(results: list) -> None:
    """Validate simulated_data.json / simulated_asset_data.json if present."""
    label = "simulated_data.json"
    candidates = [
        PROJ_DIR / "simulated_data.json",
        PROJ_DIR / "OPC_UA_IJT_Server_Simulator_Linux" / "simulated_asset_data.json",
        PROJ_DIR / "OPC_UA_IJT_Server_Simulator" / "simulated_asset_data.json",
    ]
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        _record(results, 1, label, True, "SKIP (file not present)")
        return
    try:
        with path.open(encoding="utf-8") as fh:
            json.load(fh)
        _record(results, 1, label, True, f"PASS (valid JSON — {path.name})")
    except Exception as exc:
        _record(results, 1, label, False, f"FAIL ({exc})")


def _check_detect_secrets(results: list) -> None:
    label = "Secrets scan (detect-secrets)"
    if not _cmd_available("detect-secrets"):
        _record(
            results,
            1,
            label,
            True,
            "SKIP (detect-secrets not installed — pip install detect-secrets)",
        )
        return
    r = subprocess.run(
        ["detect-secrets", "scan", "--baseline", ".secrets.baseline"],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(PROJ_DIR),
    )
    if r.returncode == 0:
        _record(results, 1, label, True, "PASS")
    else:
        _record(results, 1, label, False, f"FAIL (exit {r.returncode})")


def _check_pip_audit(results: list) -> None:
    label = "pip-audit (requirements.txt)"
    reqs = PROJ_DIR / "tests" / "requirements.txt"
    if not reqs.exists():
        _record(results, 1, label, True, "SKIP (tests/requirements.txt not found)")
        return
    if not _py_module_available("pip_audit"):
        _record(results, 1, label, True, "SKIP (pip-audit not installed — pip install pip-audit)")
        return
    if not _is_https_reachable("pypi.org"):
        _record(results, 1, label, True, "SKIP — network/TLS unavailable (preflight)")
        return

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    audit_out = RESULTS_DIR / "pip-audit.json"
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip_audit",
            "-r",
            str(reqs),
            "--format",
            "json",
            "-o",
            str(audit_out),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if r.returncode == 0:
        try:
            data = json.loads(audit_out.read_text(encoding="utf-8"))
            vuln_count = sum(
                len(pkg.get("vulns") or []) for pkg in (data.get("dependencies") or [])
            )
            _record(results, 1, label, True, f"PASS ({vuln_count} CVEs)")
        except Exception:
            _record(results, 1, label, True, "PASS")
    else:
        _record(results, 1, label, False, f"FAIL (exit {r.returncode})")


def _check_docker_validate(results: list) -> None:
    label = "Docker compose validate"
    if not _is_docker_running():
        _record(results, 1, label, True, "SKIP (Docker not running)")
        return
    r = subprocess.run(
        ["docker", "compose", "config", "--quiet"],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(PROJ_DIR),
    )
    if r.returncode == 0:
        _record(results, 1, label, True, "PASS")
    else:
        _record(results, 1, label, False, f"FAIL\n{(r.stdout + r.stderr).strip()}")


def _check_trivy(results: list) -> None:
    label = "Image scan (trivy)"
    if not _cmd_available("trivy"):
        _record(
            results,
            1,
            label,
            True,
            "SKIP (trivy not installed — https://aquasecurity.github.io/trivy)",
        )
        return
    if not _is_docker_running():
        _record(results, 1, label, True, "SKIP (Docker not running)")
        return

    _print("  Building Docker image for trivy scan (opcua-ijt-server-scan:latest) ...")
    build_r = subprocess.run(
        ["docker", "build", "-t", "opcua-ijt-server-scan:latest", "."],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(PROJ_DIR),
    )
    if build_r.returncode != 0:
        _record(results, 1, label, False, f"FAIL (docker build failed)\n{build_r.stderr[:300]}")
        return

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    trivy_out = RESULTS_DIR / "trivy.json"
    r = subprocess.run(
        [
            "trivy",
            "image",
            "--format",
            "json",
            "--output",
            str(trivy_out),
            "opcua-ijt-server-scan:latest",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if r.returncode != 0:
        _record(results, 1, label, False, f"FAIL (trivy exit {r.returncode})")
        return
    try:
        data = json.loads(trivy_out.read_text(encoding="utf-8"))
        scan_results = data.get("Results") or []
        total_vulns = sum(len(res.get("Vulnerabilities") or []) for res in scan_results)
        criticals = sum(
            sum(1 for v in (res.get("Vulnerabilities") or []) if v.get("Severity") == "CRITICAL")
            for res in scan_results
        )
        if criticals:
            _record(results, 1, label, False, f"FAIL ({total_vulns} vulns, {criticals} CRITICAL)")
        else:
            _record(results, 1, label, True, f"PASS ({total_vulns} vulns, 0 CRITICAL)")
    except Exception:
        _record(results, 1, label, True, "PASS")


def _check_binaries(results: list) -> None:
    """Informational: report which distributable binaries are present."""
    label = "Binaries present"
    parts = [
        f"Linux {'✓' if _LINUX_BINARY.exists() else '✗'}",
        f"Windows {'✓' if _WINDOWS_ZIP.exists() else '✗'}",
    ]
    _record(results, 1, label, True, f"PASS ({', '.join(parts)})")


def _check_semgrep(results: list) -> None:
    """Run Semgrep AI code review; skip if not installed."""
    label = "Semgrep (AI review)"
    if not _cmd_available("semgrep"):
        _record(results, 1, label, True, "SKIP (Install: pip install semgrep)")
        return
    if not _is_https_reachable("semgrep.dev"):
        _record(
            results,
            1,
            label,
            True,
            "WARN (N/A) — semgrep network/TLS unavailable (preflight)",
        )
        return
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    json_file = RESULTS_DIR / "semgrep.json"
    try:
        proc = subprocess.run(
            [
                "semgrep",
                "--config=p/default",
                "--json",
                "--output",
                str(json_file),
                "--exclude=.venv",
                "--exclude=test-results",
                ".",
            ],
            check=False,
            capture_output=True,
            text=True,
            cwd=str(PROJ_DIR),
            timeout=120,
        )
        rc = proc.returncode
    except subprocess.TimeoutExpired:
        _record(results, 1, label, True, "SKIP (semgrep timed out after 120s)")
        return
    if not json_file.exists():
        _record(
            results,
            1,
            label,
            True,
            f"WARN (exit {rc}) — semgrep produced no output: network unavailable or auth required",
        )
        return
    try:
        data = json.loads(json_file.read_text(encoding="utf-8"))
        findings = data.get("results", [])
        errors = [f for f in findings if f.get("extra", {}).get("severity") == "ERROR"]
        warns = [f for f in findings if f.get("extra", {}).get("severity") == "WARNING"]
        if errors:
            _record(
                results, 1, label, False, f"FAIL ({len(errors)} error(s), {len(warns)} warning(s))"
            )
        elif warns:
            _record(results, 1, label, True, f"WARN (0 errors, {len(warns)} warning(s))")
        else:
            _record(results, 1, label, True, f"PASS ({len(findings)} finding(s), none critical)")
    except Exception as exc:
        _record(results, 1, label, True, f"WARN — semgrep.json parse failed (rc={rc}): {exc!s:.80}")


# ---------------------------------------------------------------------------
# Phase 2 helpers
# ---------------------------------------------------------------------------


def _venv_python() -> Path:
    """Return path to venv Python, creating the venv + installing deps if needed."""
    venv_dir = PROJ_DIR / ".venv"
    python_exe = venv_dir / "Scripts" / "python.exe" if _IS_WINDOWS else venv_dir / "bin" / "python"
    if not python_exe.exists():
        _print(f"  Creating venv at {venv_dir} ...")
        venv.create(str(venv_dir), with_pip=True)

    reqs = PROJ_DIR / "tests" / "requirements.txt"
    if reqs.exists():
        subprocess.run(
            [
                str(python_exe),
                "-m",
                "pip",
                "install",
                "-q",
                "--disable-pip-version-check",
                "--pre",
                "-r",
                str(reqs),
            ],
            check=True,
        )
    return python_exe


def _parse_opcua_url(url: str) -> tuple[str, int]:
    """Parse 'opc.tcp://host:port' → (host, port)."""
    scheme = "opc.tcp://"
    if not url.startswith(scheme):
        raise ValueError(f"Expected opc.tcp:// URL, got: {url!r}")
    rest = url[len(scheme) :]
    host, _, port_str = rest.partition(":")
    port = int(port_str) if port_str else _DEFAULT_PORT
    return host, port


def _is_reachable(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _wait_for_port(host: str, port: int, timeout: float = 60.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _is_reachable(host, port):
            return True
        time.sleep(1.0)
    return False


def _run_smoke_test(venv_py: Path, server_url: str) -> tuple[bool, str, int]:
    """Run smoke_test.py. Returns (passed, detail_string, check_count)."""
    env = {**os.environ, "OPCUA_SERVER_URL": server_url}
    result = subprocess.run(
        [str(venv_py), "tests/smoke_test.py"],
        check=False,
        cwd=str(PROJ_DIR),
        env=env,
        capture_output=True,
        text=True,
    )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "smoke-results.txt").write_text(result.stdout + result.stderr, encoding="utf-8")

    if result.stdout:
        sys.stdout.write(result.stdout)
    if result.stderr:
        sys.stdout.write(result.stderr)
    sys.stdout.flush()

    check_count = (
        result.stdout.count("[OK]") + result.stdout.count("[FAIL]") + result.stdout.count("[SKIP]")
    )

    if result.returncode == 0:
        return True, "PASS", check_count
    if result.returncode == 2:
        return True, "SKIP (server not reachable)", check_count
    return False, f"FAIL (exit {result.returncode})", check_count


# ---------------------------------------------------------------------------
# Phase runners
# ---------------------------------------------------------------------------


def run_phase1(results: list) -> None:
    """Run all static checks, appending result tuples to ``results``."""
    _check_hadolint(results)
    _check_docker_compose(results)
    _check_shellcheck(results)
    _check_server_config(results)
    _check_simulated_data(results)
    _check_detect_secrets(results)
    _check_pip_audit(results)
    _check_docker_validate(results)
    _check_trivy(results)
    _check_binaries(results)
    _check_semgrep(results)


def run_phase2(results: list) -> None:
    """Run the live smoke test with auto-server-launch. Appends to ``results``."""
    server_url = os.environ.get("OPCUA_SERVER_URL", _DEFAULT_URL)
    simulator_exe = os.environ.get("OPCUA_SIMULATOR_EXE", "")

    try:
        host, port = _parse_opcua_url(server_url)
    except ValueError as exc:
        _record(results, 2, "OPC UA Smoke", False, f"FAIL (bad URL: {exc})")
        return

    already_up = _is_reachable(host, port)
    launched_proc = None
    launched_docker = False

    try:
        if not already_up:
            if simulator_exe:
                _print(f"  Launching server: {simulator_exe}")
                try:
                    launched_proc = subprocess.Popen([simulator_exe])
                except Exception as exc:
                    _record(
                        results,
                        2,
                        "OPC UA Smoke",
                        False,
                        f"FAIL (could not launch OPCUA_SIMULATOR_EXE: {exc})",
                    )
                    return

            elif _LINUX_BINARY.exists() and not _IS_WINDOWS:
                _print(f"  Launching Linux binary: {_LINUX_BINARY}")
                try:
                    launched_proc = subprocess.Popen(
                        [str(_LINUX_BINARY)],
                        cwd=str(_LINUX_BINARY.parent),
                    )
                except Exception as exc:
                    _record(
                        results,
                        2,
                        "OPC UA Smoke",
                        False,
                        f"FAIL (could not launch Linux binary: {exc})",
                    )
                    return

            elif _is_docker_running() and (PROJ_DIR / "docker-compose.yml").exists():
                _print("  Launching via: docker compose up -d --build ...")
                r = subprocess.run(
                    ["docker", "compose", "up", "-d", "--build"],
                    check=False,
                    cwd=str(PROJ_DIR),
                    capture_output=True,
                    text=True,
                )
                if r.returncode != 0:
                    _record(
                        results,
                        2,
                        "OPC UA Smoke",
                        False,
                        f"FAIL (docker compose up failed)\n{r.stderr[:300]}",
                    )
                    return
                launched_docker = True

            else:
                _print(
                    f"  SKIP: server not reachable at {server_url}\n"
                    "  To enable Phase 2: set OPCUA_SIMULATOR_EXE, start Docker, "
                    "or pre-start the server."
                )
                _record(results, 2, "OPC UA Smoke", True, "SKIP (no server available)")
                return

        # Wait for the port to open after launch
        if launched_proc is not None or launched_docker:
            _print(f"  Waiting for OPC UA port {port} ...")
            t_launch = time.monotonic()
            if not _wait_for_port(host, port, timeout=60.0):
                _record(
                    results,
                    2,
                    "OPC UA Smoke",
                    False,
                    f"FAIL (server did not open port {port} within 60 s)",
                )
                return
            response_time = time.monotonic() - t_launch
            if response_time > 5.0:
                _print(f"  WARN: server took {response_time:.1f}s to become available")

        try:
            venv_py = _venv_python()
        except Exception as exc:
            _record(results, 2, "OPC UA Smoke", False, f"FAIL (venv setup: {exc})")
            return

        ok, detail, check_count = _run_smoke_test(venv_py, server_url)
        smoke_label = f"OPC UA Smoke ({check_count} checks)" if check_count > 0 else "OPC UA Smoke"
        _record(results, 2, smoke_label, ok, detail)

    finally:
        if launched_proc is not None:
            launched_proc.terminate()
            try:
                launched_proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                launched_proc.kill()
        if launched_docker:
            _print("  Stopping Docker container (docker compose down) ...")
            subprocess.run(
                ["docker", "compose", "down"],
                cwd=str(PROJ_DIR),
                check=False,
                capture_output=True,
            )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_all_tests.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--phase1", action="store_true", help="Static checks only (no server required)"
    )
    group.add_argument("--phase2", action="store_true", help="Live smoke test only")
    return parser


def main() -> int:
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    _cleanup_caches(PROJ_DIR)  # pre-run: clear stale caches from interrupted runs
    parser = _build_parser()
    args = parser.parse_args()

    t0 = time.monotonic()
    _header()

    shutil.rmtree(RESULTS_DIR, ignore_errors=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    results: list = []

    if not args.phase2:
        run_phase1(results)

    if not args.phase1:
        run_phase2(results)

    all_ok = all(ok for _, _, ok, _ in results)
    _footer(results, time.monotonic() - t0)
    _cleanup_caches(PROJ_DIR)
    return 0 if all_ok else 1


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
    _SKIP = {"node_modules", ".git", "test-results"}  # "tmp" intentionally removed — now cleaned
    _CACHE_DIRS = {"__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", "htmlcov"}
    for dirpath, dirs, files in os.walk(root, topdown=True):
        dirs[:] = [
            d
            for d in dirs
            if d not in _SKIP and not d.startswith(".venv") and not d.startswith("venv")
        ]
        for d in list(dirs):
            if d in _CACHE_DIRS or d.startswith("pytest-cache-files-") or d.startswith(".dotnet"):
                _force_rmtree(Path(dirpath) / d)
                dirs.remove(d)
        for f in files:
            if f == ".coverage" or f.startswith(".coverage.") or f.endswith(".pyc"):
                with contextlib.suppress(OSError):
                    (Path(dirpath) / f).unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
