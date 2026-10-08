#!/usr/bin/env python3
"""
Run pre-commit for the IJT repo, then for the Envelope submodule when present.

This is the simplest "before commit" helper for contributors: one command
handles the root repo and, when checked out, the private Envelope submodule.

Python tools are prepared before audits start. Missing required tools or inputs
fail validation; only an absent optional Envelope checkout is skipped.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

# Add scripts/ to path for dependency_helpers
if str(Path(__file__).parent / "scripts") not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from dependency_helpers import (
    ensure_python_package,
    find_cmd,
)
from tool_bootstrap import ensure_requirements_environment, ensure_uv

log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

REPO_ROOT = Path(__file__).resolve().parent


def _python_client_dirs() -> tuple[Path, ...]:
    r2 = REPO_ROOT / "OPC_UA_Clients" / "Release2"
    return (
        r2 / "IJT_Console_Client",
        r2 / "IJT_Performance_Client",
        r2 / "IJT_Test_Client",
        r2 / "IJT_Web_Client",
    )


WEB_CLIENT_DIR = REPO_ROOT / "OPC_UA_Clients" / "Release2" / "IJT_Web_Client"


NODE_CLIENT_DIR = REPO_ROOT / "OPC_UA_Clients" / "Release1" / "IJT_Node_Client"
CSHARP_DIR = REPO_ROOT / "OPC_UA_Clients" / "Release2" / "IJT_CSharp_Client"
CSHARP_SLN = CSHARP_DIR / "IJT_CSharp_Client.sln"
ENVELOPE_DIR = (
    REPO_ROOT
    / "OPC_UA_Clients"
    / "Release2"
    / "IJT_Web_Client"
    / "src"
    / "javascripts"
    / "views"
    / "envelope"
)
# Python clients are audited through each client's uv.lock (uv export + pip-audit).
# This list covers the remaining non-client requirement files.
PYTHON_AUDIT_REQUIREMENTS: tuple[Path, ...] = (
    REPO_ROOT / "tests" / "requirements.txt",
    REPO_ROOT / "reporting" / "requirements.txt",
    REPO_ROOT / "OPC_UA_Servers" / "Release2" / "tests" / "requirements.txt",
    REPO_ROOT
    / "OPC_UA_Clients"
    / "Release2"
    / "IJT_Web_Client"
    / "src"
    / "javascripts"
    / "views"
    / "envelope"
    / "requirements-ci.txt",
)
PRECOMMIT_ARGS = ("run", "--all-files", "--show-diff-on-failure", "--color=always")
NPM_AUDIT_MODE_ENV: Final[str] = "IJT_NPM_AUDIT_MODE"
NPM_AUDIT_MODE_STRICT: Final[str] = "strict"
NPM_AUDIT_MODE_OFFLINE: Final[str] = "offline"
NPM_AUDIT_NETWORK_PATTERNS: Final[tuple[str, ...]] = (
    "ECONNRESET",
    "ETIMEDOUT",
    "ENOTFOUND",
    "ERR_SOCKET",
    "fetch failed",
    "network timeout at",
    "audit endpoint returned an error",
    "request to https://registry.npmjs.org",
)


class _AuditLog:
    """Buffer worker messages without redirecting process-wide output streams."""

    def __init__(self, output: list[str] | None):
        self.output = output

    def _write(self, level: int, message: str, *args: object) -> None:
        if self.output is None:
            log.log(level, message, *args)
        else:
            self.output.append(f"{logging.getLevelName(level)}: {message % args}\n")

    def info(self, message: str, *args: object) -> None:
        self._write(logging.INFO, message, *args)

    def warning(self, message: str, *args: object) -> None:
        self._write(logging.WARNING, message, *args)

    def error(self, message: str, *args: object) -> None:
        self._write(logging.ERROR, message, *args)


def _emit_audit_output(completed: subprocess.CompletedProcess, output: list[str] | None) -> None:
    for stream, text in ((sys.stdout, completed.stdout), (sys.stderr, completed.stderr)):
        if text:
            if output is None:
                stream.write(text)
                stream.flush()
            else:
                output.append(text.rstrip() + "\n")


def _envelope_available() -> bool:
    return any(
        (ENVELOPE_DIR / name).is_file()
        for name in ("package.json", "requirements-ci.txt", ".pre-commit-config.yaml")
    )


def _precommit_command() -> list[str]:
    """Get pre-commit command, auto-installing if needed."""
    if not ensure_python_package("pre-commit", import_name="pre_commit"):
        raise RuntimeError(
            "pre-commit could not be installed. Manual install: pip install pre-commit"
        )
    req = REPO_ROOT / "tests" / "requirements.txt"
    if req.is_file():
        import importlib.util

        if importlib.util.find_spec("pytest") is None or importlib.util.find_spec("yaml") is None:
            log.info("Installing root test dependencies (pytest, pyyaml)...")
            result = subprocess.run(  # noqa: S603 - fixed internal command list
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--quiet",
                    "--disable-pip-version-check",
                    "-r",
                    str(req),
                ],
                check=False,
            )
            if result.returncode != 0:
                log.warning(
                    "pip install for root test dependencies failed (rc=%d); "
                    "pytest hook may fail with ModuleNotFoundError",
                    result.returncode,
                )
    return [sys.executable, "-m", "pre_commit"]


_HOOK_RESULT_RE = re.compile(r"(Passed|Failed|Skipped)(\x1b\[[0-9;]*m)?\s*$")


def _run_precommit_stream(cmd: list[str], cwd: Path) -> int:
    """Stream pre-commit output line by line with timestamps and per-hook durations."""
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(  # noqa: S603 - fixed internal command list
        cmd,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    t_last = time.monotonic()
    assert proc.stdout is not None
    for line in proc.stdout:
        line_s = line.rstrip("\r\n")
        dt = time.monotonic() - t_last
        t_last = time.monotonic()
        now = time.strftime("%H:%M:%S")
        if _HOOK_RESULT_RE.search(line_s):
            sys.stdout.write(f"{now} [pre-commit] {line_s} ({dt:.2f}s)\n")
        elif line_s:
            sys.stdout.write(f"{now} [pre-commit] {line_s}\n")
        else:
            sys.stdout.write("\n")
        sys.stdout.flush()
    proc.wait()
    return proc.returncode


def _run_precommit(cwd: Path, label: str) -> int:
    """Run pre-commit in the given directory with timestamps and durations."""
    log.info("[pre-commit] %s: %s", label, cwd)
    t0 = time.monotonic()
    cmd = [*_precommit_command(), *PRECOMMIT_ARGS]
    # In test environments where subprocess.run is mocked, use subprocess.run
    if getattr(subprocess.run, "__name__", "") != "run":
        completed = subprocess.run(cmd, cwd=cwd)  # noqa: S603 - fixed internal command list
        returncode = completed.returncode
    else:
        returncode = _run_precommit_stream(cmd, cwd)
    log.info(
        "[pre-commit] %s finished in %.2fs (exit code %d)",
        label,
        time.monotonic() - t0,
        returncode,
    )
    return returncode


def _safe_subprocess_run(
    cmd: list[str],
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
    capture_output: bool = True,
) -> subprocess.CompletedProcess:
    """Run an audit subprocess without dropping its environment or timeout."""
    return subprocess.run(  # noqa: S603 - fixed internal command list
        cmd,
        cwd=cwd,
        env=env,
        timeout=timeout,
        capture_output=capture_output,
        text=capture_output,
    )


def _run_npm_lock_audit(
    cwd: Path,
    label: str,
    retries: int = 2,
    timeout_seconds: float = 15.0,
    *,
    output: list[str] | None = None,
) -> int:
    """Run npm audit on package-lock.json with strict/offline policy."""
    audit_log = _AuditLog(output)
    package_lock = cwd / "package-lock.json"
    package_json = cwd / "package.json"
    if not package_json.exists():
        audit_log.error("[security] %s: required input %s not found", label, package_json)
        return 1
    if not package_lock.exists():
        audit_log.error("[security] %s: required input %s not found", label, package_lock)
        return 1

    npm = find_cmd("npm.cmd", "npm.exe", "npm")
    if npm is None:
        audit_log.error(
            "[security] %s: npm not found in PATH. Install Node.js to enable npm audit.",
            label,
        )
        return 1

    audit_mode = os.environ.get(NPM_AUDIT_MODE_ENV, NPM_AUDIT_MODE_STRICT).strip().lower()
    if audit_mode not in (NPM_AUDIT_MODE_STRICT, NPM_AUDIT_MODE_OFFLINE):
        audit_log.warning(
            "[security] %s: invalid %s=%r; defaulting to '%s'",
            label,
            NPM_AUDIT_MODE_ENV,
            audit_mode,
            NPM_AUDIT_MODE_STRICT,
        )
        audit_mode = NPM_AUDIT_MODE_STRICT
    audit_log.info(
        "[security] %s: npm audit --omit=dev --package-lock-only --audit-level=high "
        "(network mode: %s via %s)",
        label,
        audit_mode,
        NPM_AUDIT_MODE_ENV,
    )
    cmd = [
        npm,
        "audit",
        "--omit=dev",
        "--package-lock-only",
        "--audit-level=high",
        "--fetch-timeout=10000",
        "--fetch-retries=1",
    ]
    npm_env = os.environ.copy()
    cache_dir = REPO_ROOT / "tmp" / "npm-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    npm_env["npm_config_cache"] = str(cache_dir)
    npm_env["npm_config_update_notifier"] = "false"

    t0 = time.monotonic()
    for attempt in range(1, retries + 1):
        try:
            completed = _safe_subprocess_run(
                cmd,
                cwd=cwd,
                env=npm_env,
                timeout=timeout_seconds,
                capture_output=True,
            )
            if completed.returncode == 0:
                elapsed = time.monotonic() - t0
                audit_log.info("[security] %s: npm audit passed (%.2fs)", label, elapsed)
                return 0

            diagnostic = f"{getattr(completed, 'stdout', '')}\n{getattr(completed, 'stderr', '')}"
            is_transient_network_error = any(
                pattern in diagnostic for pattern in NPM_AUDIT_NETWORK_PATTERNS
            )
            if is_transient_network_error:
                if attempt < retries:
                    audit_log.warning(
                        "[security] %s: npm audit network error on attempt %d/%d, "
                        "retrying in %ds...",
                        label,
                        attempt,
                        retries,
                        2 * attempt,
                    )
                    time.sleep(2 * attempt)
                    continue
                if audit_mode == NPM_AUDIT_MODE_OFFLINE:
                    audit_log.warning(
                        "[security] %s: npm audit registry endpoint unreachable/timed out "
                        "(offline or restricted network); offline mode allows continuing.",
                        label,
                    )
                    return 0
                audit_log.error(
                    "[security] %s: npm audit failed due to registry connectivity in strict mode. "
                    "Fix network/proxy access, or set %s=%s only for explicitly offline local "
                    "runs.",
                    label,
                    NPM_AUDIT_MODE_ENV,
                    NPM_AUDIT_MODE_OFFLINE,
                )
                return 1

            _emit_audit_output(completed, output)
            return completed.returncode
        except subprocess.TimeoutExpired:
            if attempt < retries:
                audit_log.warning(
                    "[security] %s: npm audit timed out on attempt %d/%d, retrying in %ds...",
                    label,
                    attempt,
                    retries,
                    2 * attempt,
                )
                time.sleep(2 * attempt)
                continue
            if audit_mode == NPM_AUDIT_MODE_OFFLINE:
                audit_log.warning(
                    "[security] %s: npm audit registry request timed out (offline/slow network); "
                    "offline mode allows continuing.",
                    label,
                )
                return 0
            audit_log.error(
                "[security] %s: npm audit timed out in strict mode. "
                "Fix npm registry connectivity, or set %s=%s only for explicitly offline local "
                "runs.",
                label,
                NPM_AUDIT_MODE_ENV,
                NPM_AUDIT_MODE_OFFLINE,
            )
            return 1

    return 0


def _run_python_requirements_audit(
    retries: int = 2,
    timeout_seconds: float = 60.0,
    *,
    prepared: bool | None = None,
    output: list[str] | None = None,
) -> int:
    """Audit non-client requirements; workers consume main-thread tool preparation."""
    audit_log = _AuditLog(output)
    if prepared is None:
        prepared = ensure_python_package("pip-audit", import_name="pip_audit")
    if not prepared:
        audit_log.error(
            "[security] Python requirements audit failed: pip-audit could not be installed. "
            "Manual install: pip install pip-audit"
        )
        return 1

    requirements = [
        req
        for req in PYTHON_AUDIT_REQUIREMENTS
        if req != ENVELOPE_DIR / "requirements-ci.txt" or _envelope_available()
    ]
    missing = [req for req in requirements if not req.is_file()]
    if missing:
        audit_log.error("[security] Required Python requirements missing: %s", missing)
        return 1
    if not requirements:
        audit_log.info("[security] Python requirements audit not applicable: no inputs configured")
        return 0

    audit_log.info("[security] Python requirements: pip-audit --requirement ...")
    cache_dir = REPO_ROOT / "tmp" / "pip-audit-cache" / "requirements"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "pip_audit",
        "--progress-spinner",
        "off",
        "--cache-dir",
        str(cache_dir),
    ]
    for req in requirements:
        cmd.extend(["--requirement", str(req)])
    canonical_tmp = str(Path(tempfile.gettempdir()).resolve())
    env = os.environ.copy()
    env["TMP"] = canonical_tmp
    env["TEMP"] = canonical_tmp
    env["TMPDIR"] = canonical_tmp

    t0 = time.monotonic()
    for attempt in range(1, retries + 1):
        try:
            completed = _safe_subprocess_run(
                cmd,
                cwd=REPO_ROOT,
                env=env,
                timeout=timeout_seconds,
                capture_output=True,
            )
            if completed.returncode == 0:
                elapsed = time.monotonic() - t0
                audit_log.info("[security] Python requirements: pip-audit passed (%.2fs)", elapsed)
                return 0

            diagnostic = f"{getattr(completed, 'stdout', '')}\n{getattr(completed, 'stderr', '')}"
            is_network_error = any(
                pattern in diagnostic
                for pattern in ("ConnectionError", "Timeout", "ECONNRESET", "ETIMEDOUT")
            )
            if is_network_error and attempt < retries:
                audit_log.warning(
                    "[security] Python requirements audit network error on attempt %d/%d, "
                    "retrying...",
                    attempt,
                    retries,
                )
                time.sleep(2 * attempt)
                continue

            _emit_audit_output(completed, output)
            return completed.returncode
        except subprocess.TimeoutExpired:
            audit_log.warning(
                "[security] Python requirements audit timed out on attempt %d/%d",
                attempt,
                retries,
            )
            if attempt < retries:
                time.sleep(2 * attempt)
                continue
            return 1

    return 1


AUDIT_CONCURRENCY: Final[int] = 2


@dataclass
class AuditResult:
    label: str
    returncode: int
    duration: float = 0.0
    output: str = ""
    error: str = ""
    stages: dict[str, float] = field(default_factory=dict)
    skipped: bool = False


def _run_single_python_client_lock_audit(
    client_dir: Path,
    uv: str | None = None,
    timeout_seconds: float = 180.0,
    cache_dir: Path | None = None,
) -> AuditResult:
    """Check one client's uv.lock, export frozen pinned requirements, and fast-audit them."""
    label = f"Python client lock ({client_dir.name})"
    t0 = time.monotonic()
    stages: dict[str, float] = {}

    if not (client_dir / "pyproject.toml").is_file():
        return AuditResult(
            label, 1, error=f"Required manifest missing: {client_dir / 'pyproject.toml'}"
        )

    if uv is None:
        uv = find_cmd("uv.exe", "uv")
    if not uv:
        return AuditResult(label, 1, duration=time.monotonic() - t0, error="uv not found on PATH")

    try:
        check = _safe_subprocess_run(
            [uv, "lock", "--check"],
            cwd=client_dir,
            timeout=timeout_seconds,
            capture_output=True,
        )
        stages["lock"] = time.monotonic() - t0
        if check.returncode != 0:
            err = f"{client_dir.name}/uv.lock is out of date: run 'uv lock' to update"
            if check.stderr:
                err += f"\n{check.stderr}"
            return AuditResult(
                label,
                check.returncode,
                duration=time.monotonic() - t0,
                output=check.stdout or "",
                error=err,
                stages=stages,
            )
    except subprocess.TimeoutExpired:
        return AuditResult(
            label,
            1,
            duration=time.monotonic() - t0,
            error=f"{client_dir.name} uv lock check timed out",
        )

    canonical_tmp = str(Path(tempfile.gettempdir()).resolve())
    audit_env = os.environ.copy()
    audit_env["TMP"] = canonical_tmp
    audit_env["TEMP"] = canonical_tmp
    audit_env["TMPDIR"] = canonical_tmp

    with tempfile.NamedTemporaryFile("w+", suffix=".txt", dir=canonical_tmp, delete=False) as tf:
        tmp_name = tf.name

    try:
        if cache_dir is None:
            cache_dir = REPO_ROOT / "tmp" / "pip-audit-cache" / client_dir.name
        cache_dir.mkdir(parents=True, exist_ok=True)
        stage_start = time.monotonic()
        export = _safe_subprocess_run(
            [
                uv,
                "export",
                "--frozen",
                "--all-groups",
                "--no-emit-project",
                "--format",
                "requirements-txt",
                "-o",
                tmp_name,
            ],
            cwd=client_dir,
            env=audit_env,
            timeout=timeout_seconds,
            capture_output=True,
        )
        stages["export"] = time.monotonic() - stage_start
        if export.returncode != 0:
            err = f"{client_dir.name} uv export failed: {export.stderr}"
            return AuditResult(
                label,
                export.returncode,
                duration=time.monotonic() - t0,
                output=export.stdout or "",
                error=err,
                stages=stages,
            )

        if not Path(tmp_name).is_file() or Path(tmp_name).stat().st_size == 0:
            return AuditResult(
                label,
                1,
                duration=time.monotonic() - t0,
                error=f"{client_dir.name} uv export produced an empty requirements file",
                stages=stages,
            )

        # Fast path: require hashes and disable pip to audit exact frozen pins
        # without invoking pip resolver or constructing a virtualenv.
        cmd = [
            sys.executable,
            "-m",
            "pip_audit",
            "--progress-spinner",
            "off",
            "--cache-dir",
            str(cache_dir),
            "-r",
            tmp_name,
            "--strict",
            "--disable-pip",
            "--require-hashes",
        ]
        stage_start = time.monotonic()
        completed = _safe_subprocess_run(
            cmd,
            cwd=client_dir,
            env=audit_env,
            timeout=timeout_seconds,
            capture_output=True,
        )
        stderr = completed.stderr or ""
        fallback_note = ""
        if completed.returncode == 2 and ("unrecognized arguments: --disable-pip" in stderr):
            fallback_note = (
                "Fast-path flags unsupported; audited with pip-based resolution instead.\n"
            )
            fallback_cmd = [
                sys.executable,
                "-m",
                "pip_audit",
                "--progress-spinner",
                "off",
                "--cache-dir",
                str(cache_dir),
                "-r",
                tmp_name,
                "--strict",
                "--require-hashes",
            ]
            completed = _safe_subprocess_run(
                fallback_cmd,
                cwd=client_dir,
                env=audit_env,
                timeout=timeout_seconds,
                capture_output=True,
            )

        stages["audit"] = time.monotonic() - stage_start
        out = fallback_note + (completed.stdout or "") + "\n" + (completed.stderr or "")
        return AuditResult(
            label,
            completed.returncode,
            duration=time.monotonic() - t0,
            output=out,
            stages=stages,
        )
    except subprocess.TimeoutExpired:
        return AuditResult(
            label,
            1,
            duration=time.monotonic() - t0,
            error=f"{client_dir.name} Python lock audit timed out",
            stages=stages,
        )
    finally:
        Path(tmp_name).unlink(missing_ok=True)


def _run_python_lock_audit(timeout_seconds: float = 180.0) -> int:
    """Check each client's uv.lock is current, export pinned requirements, then pip-audit them."""
    if not ensure_python_package("pip-audit", import_name="pip_audit"):
        log.error("[security] Python lock audit failed: pip-audit could not be installed")
        return 1
    uv = find_cmd("uv.exe", "uv")
    if not uv:
        log.error("[security] uv not found on PATH; required for uv.lock audit")
        return 1

    overall_rc = 0
    for client_dir in _python_client_dirs():
        res = _run_single_python_client_lock_audit(
            client_dir, uv=uv, timeout_seconds=timeout_seconds
        )
        if res.output:
            sys.stdout.write(res.output)
            sys.stdout.flush()
        if res.error:
            sys.stderr.write(res.error + "\n")
            sys.stderr.flush()
        if res.returncode != 0:
            overall_rc = res.returncode
    return overall_rc


def _run_csharp_nuget_audit(
    timeout_seconds: float = 120.0, *, output: list[str] | None = None
) -> int:
    """Audit NuGet JSON findings, since dotnet can exit zero with vulnerabilities."""
    audit_log = _AuditLog(output)
    csharp_sln = (
        REPO_ROOT / "OPC_UA_Clients" / "Release2" / "IJT_CSharp_Client" / "IJT_CSharp_Client.sln"
    )
    if not csharp_sln.exists():
        audit_log.error("[security] C# Client: required solution %s not found", csharp_sln)
        return 1

    dotnet = find_cmd("dotnet.exe", "dotnet")
    if dotnet is None:
        audit_log.error(
            "[security] C# Client: dotnet not found in PATH. "
            "Install .NET SDK to enable NuGet audit."
        )
        return 1

    audit_log.info("[security] C# Client: dotnet list package --vulnerable --include-transitive")
    cmd = [
        dotnet,
        "list",
        str(csharp_sln),
        "package",
        "--vulnerable",
        "--include-transitive",
        "--format",
        "json",
    ]
    t0 = time.monotonic()
    try:
        completed = _safe_subprocess_run(
            cmd,
            cwd=REPO_ROOT,
            timeout=timeout_seconds,
            capture_output=True,
        )
        if completed.returncode == 0:
            try:
                report = json.loads(completed.stdout)
                if not isinstance(report, dict) or not isinstance(report.get("projects"), list):
                    raise ValueError("NuGet report must contain a projects array")
                if report.get("problems"):
                    raise ValueError(f"NuGet reported problems: {report['problems']}")
                if not report["projects"]:
                    raise ValueError("NuGet report contains no projects")
                for project in report["projects"]:
                    if not isinstance(project, dict):
                        raise ValueError("Invalid NuGet project")
                    if "frameworks" not in project:
                        # NuGet omits frameworks when the filtered report has no findings.
                        if not isinstance(project.get("path"), str) or not project["path"].strip():
                            raise ValueError("NuGet project without framework results needs a path")
                        continue
                    frameworks = project["frameworks"]
                    if not isinstance(frameworks, list) or not frameworks:
                        raise ValueError("NuGet project contains no framework results")
                    for framework in frameworks:
                        if not isinstance(framework, dict):
                            raise ValueError("Invalid NuGet framework")
                        for category in ("topLevelPackages", "transitivePackages"):
                            packages = framework.get(category, [])
                            if not isinstance(packages, list):
                                raise ValueError("Invalid NuGet package list")
                            for package in packages:
                                if not isinstance(package, dict):
                                    raise ValueError("Invalid NuGet package")
                                if package.get("vulnerabilities"):
                                    _emit_audit_output(completed, output)
                                    audit_log.error("[security] C# Client: vulnerabilities found")
                                    return 1
            except (ValueError, TypeError, AttributeError) as exc:
                _emit_audit_output(completed, output)
                audit_log.error("[security] C# Client: invalid or incomplete audit report: %s", exc)
                return 1
            num_projects = len(report.get("projects", []))
            elapsed = time.monotonic() - t0
            audit_log.info(
                "[security] C# Client: NuGet audit passed across %d projects (%.2fs)",
                num_projects,
                elapsed,
            )
            return 0

        _emit_audit_output(completed, output)
        return completed.returncode
    except subprocess.TimeoutExpired:
        audit_log.warning("[security] C# Client: NuGet audit timed out")
        return 1


def _run_all_npm_lock_audits(*, output: list[str] | None = None) -> int:
    """Run npm lock audits sequentially across JS projects to prevent registry rate-limiting."""
    failed = False
    for label, cwd in (
        ("Node Client", NODE_CLIENT_DIR),
        ("Web Client", WEB_CLIENT_DIR),
        ("Envelope", ENVELOPE_DIR),
    ):
        if label == "Envelope" and not _envelope_available():
            _AuditLog(output).info("[security] Envelope: optional checkout absent")
            continue
        try:
            code = _run_npm_lock_audit(cwd, label, output=output)
            failed = failed or code != 0
        except Exception as exc:
            _AuditLog(output).error("[security] %s: audit failed: %s", label, exc)
            failed = True
    return int(failed)


def _run_all_audits_concurrently(
    max_workers: int = AUDIT_CONCURRENCY,
    *,
    strict: bool = False,
) -> list[AuditResult]:
    """Execute dependency vulnerability audits using a bounded ThreadPoolExecutor."""
    # Preparation failure must not prevent unrelated ecosystems from being audited.
    preparation_error = ""
    try:
        has_pip_audit = ensure_python_package("pip-audit", import_name="pip_audit")
    except Exception as exc:
        has_pip_audit = False
        preparation_error = str(exc)
    try:
        uv = ensure_uv(REPO_ROOT)
        uv_error = ""
    except RuntimeError as exc:
        uv = None
        uv_error = str(exc)

    tasks: list[tuple[str, Callable[[], AuditResult]]] = []

    def _buffered_task(label: str, fn: Callable[..., int]) -> Callable[[], AuditResult]:
        def run() -> AuditResult:
            t0 = time.monotonic()
            output: list[str] = []
            try:
                rc = fn(output=output)
                return AuditResult(label, rc, time.monotonic() - t0, "".join(output))
            except Exception as exc:
                return AuditResult(label, 1, time.monotonic() - t0, "".join(output), str(exc))

        return run

    def _system_task(
        label: str, candidates: tuple[str, ...], fn: Callable[..., int]
    ) -> Callable[[], AuditResult]:
        if find_cmd(*candidates) is None:

            def missing() -> AuditResult:
                return AuditResult(
                    label,
                    int(strict),
                    error=f"{candidates[-1]} unavailable; "
                    "install its system prerequisite to validate this component",
                    skipped=not strict,
                )

            return missing
        return _buffered_task(label, fn)

    tasks.append(
        (
            "C# Client",
            _system_task(
                "C# Client",
                ("dotnet.exe", "dotnet"),
                _run_csharp_nuget_audit,
            ),
        )
    )
    tasks.append(
        (
            "npm audits",
            _system_task(
                "npm audits",
                ("npm.cmd", "npm.exe", "npm"),
                _run_all_npm_lock_audits,
            ),
        )
    )

    # Python client locks: separate task per client project
    for client_dir in _python_client_dirs():
        label = f"Python client lock ({client_dir.name})"

        def _make_client_task(cd: Path, lbl: str) -> Callable[[], AuditResult]:
            def _task() -> AuditResult:
                t0 = time.monotonic()
                if not has_pip_audit:
                    return AuditResult(
                        lbl,
                        1,
                        error="pip-audit preparation failed"
                        + (f": {preparation_error}" if preparation_error else ""),
                    )
                if not uv:
                    return AuditResult(lbl, 1, duration=0.0, error=uv_error)
                try:
                    return _run_single_python_client_lock_audit(cd, uv=uv)
                except Exception as exc:
                    return AuditResult(lbl, 1, time.monotonic() - t0, error=str(exc))

            return _task

        tasks.append((label, _make_client_task(client_dir, label)))

    # Remaining Python requirements audit
    def _prepared_requirements(*, output: list[str]) -> int:
        return _run_python_requirements_audit(prepared=has_pip_audit, output=output)

    tasks.append(
        (
            "Python requirements",
            _buffered_task("Python requirements", _prepared_requirements),
        )
    )

    results_by_label: dict[str, AuditResult] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_label = {executor.submit(fn): label for label, fn in tasks}
        for future in concurrent.futures.as_completed(future_to_label):
            label = future_to_label[future]
            try:
                res = future.result()
            except Exception as exc:
                res = AuditResult(label, 1, duration=0.0, error=f"Unhandled exception: {exc}")
            results_by_label[label] = res

    results = [results_by_label[label] for label, _fn in tasks]
    return _render_results(results)


def _render_results(results: list[AuditResult]) -> list[AuditResult]:
    """Render audit results with pre-commit styled status badges, durations, and diagnostics."""
    for res in results:
        now = time.strftime("%H:%M:%S")
        status_word = "Skipped" if res.skipped else ("Passed" if res.returncode == 0 else "Failed")
        display_label = res.label
        offline_unvalidated = False
        if res.label == "C# Client":
            if res.skipped:
                display_label = "C# Client (.NET NuGet - skipped)"
            elif res.returncode == 0:
                m = re.search(r"across (\d+) projects", res.output)
                if m:
                    display_label = (
                        f"C# Client (.NET NuGet - {m.group(1)} projects, 0 vulnerabilities)"
                    )
                else:
                    display_label = "C# Client (.NET NuGet - 0 vulnerabilities)"
        elif res.label == "npm audits":
            if res.skipped:
                display_label = "npm package locks (skipped)"
            elif res.returncode == 0:
                offline_unvalidated = "offline mode allows continuing" in (res.output or "")
                scanned_projects = [
                    short_name
                    for label_name, short_name in (
                        ("Node Client", "Node"),
                        ("Web Client", "Web"),
                        ("Envelope", "Envelope"),
                    )
                    if f"[security] {label_name}: npm audit" in (res.output or "")
                ]
                proj_str = ", ".join(scanned_projects) if scanned_projects else "Node, Web"
                if offline_unvalidated:
                    status_word = "Not Validated"
                    display_label = f"npm package locks ({proj_str} - not validated)"
                else:
                    display_label = f"npm package locks ({proj_str} - 0 vulnerabilities)"

        use_color = (
            sys.stdout.isatty()
            or os.getenv("GITHUB_ACTIONS") == "true"
            or bool(os.getenv("COLORTERM"))
            or bool(os.getenv("TERM"))
        ) and (os.getenv("NO_COLOR") is None)
        if use_color:
            if status_word == "Passed":
                color_code = "\x1b[42m"
            elif status_word == "Failed":
                color_code = "\x1b[41m"
            elif status_word == "Skipped":
                color_code = "\x1b[46;30m"
            else:
                color_code = "\x1b[43;30m"
            colored_status = f"{color_code}{status_word}\x1b[0m"
        else:
            colored_status = status_word

        # [security] prefix is 2 chars shorter than [pre-commit], so 81 aligns the status
        # badge to the exact column 95 matching pre-commit's 79-column hook output.
        dots_count = max(1, 81 - len(display_label) - len(status_word))
        dots = "." * dots_count
        duration_str = f" ({res.duration:.2f}s)" if res.duration > 0 else ""
        sys.stdout.write(f"{now} [security] {display_label}{dots}{colored_status}{duration_str}\n")
        sys.stdout.flush()

        if res.returncode != 0:
            if res.output:
                for line in res.output.strip().splitlines():
                    sys.stdout.write(f"    [{res.label}] {line}\n")
            if res.error:
                sys.stdout.write(f"    [security ERROR] {res.label}: {res.error}\n")
            sys.stdout.flush()
        elif res.error and res.skipped:
            sys.stdout.write(f"    [security SKIP] {res.label}: {res.error}\n")
            sys.stdout.flush()
        elif offline_unvalidated:
            for line in res.output.strip().splitlines():
                if "offline mode allows continuing" in line or "WARNING" in line:
                    sys.stdout.write(f"    [security WARNING] {line.strip()}\n")
            sys.stdout.flush()
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--audits-only",
        action="store_true",
        help="Run dependency vulnerability audits without pre-commit hooks.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Require system audit tools; missing .NET/npm fails "
        "instead of reporting incomplete validation.",
    )
    args = parser.parse_args(argv)

    canonical_tmp = str(Path(tempfile.gettempdir()).resolve())
    os.environ["TMP"] = canonical_tmp
    os.environ["TEMP"] = canonical_tmp
    os.environ["TMPDIR"] = canonical_tmp

    if not find_cmd("git.exe", "git"):
        print(
            "Error: Git is not found in PATH. Install Git to run pre-commit checks.",
            file=sys.stderr,
        )
        return 1

    overall_t0 = time.monotonic()
    try:
        if not args.audits_only:
            root_code = _run_precommit(REPO_ROOT, "IJT root")
            if root_code != 0:
                return root_code

            envelope_config = ENVELOPE_DIR / ".pre-commit-config.yaml"
            if envelope_config.exists():
                envelope_code = _run_precommit(ENVELOPE_DIR, "Envelope")
                if envelope_code != 0:
                    return envelope_code
            else:
                log.info("[pre-commit] Envelope skipped: %s not found", envelope_config)

        # Run audits with bounded concurrency (AUDIT_CONCURRENCY=2).
        # Run every audit even after a failure so one unavailable ecosystem
        # never hides the security status of the remaining ecosystems.
        audit_results = _run_all_audits_concurrently(
            max_workers=AUDIT_CONCURRENCY, strict=args.strict
        )
        audit_failures = [r for r in audit_results if r.returncode != 0]

        if audit_failures:
            log.error(
                "[security] %d dependency audit group(s) failed: %s",
                len(audit_failures),
                ", ".join(r.label for r in audit_failures),
            )
            log.error("Dependency validation failed after %.2fs", time.monotonic() - overall_t0)
            return 1

        elapsed = time.monotonic() - overall_t0
        skipped = [r.label for r in audit_results if r.skipped]
        if skipped:
            log.warning(
                "Available checks passed in %.2fs; validation INCOMPLETE: %s",
                elapsed,
                ", ".join(skipped),
            )
            return 0
        if args.audits_only:
            log.info("All dependency vulnerability audits completed successfully in %.2fs", elapsed)
        else:
            log.info("All pre-commit checks and audits completed successfully in %.2fs", elapsed)
        return 0
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    try:
        if not ("--help" in sys.argv or "-h" in sys.argv) and not (
            os.getenv("GITHUB_ACTIONS") == "true" or os.getenv("IS_DOCKER") == "true"
        ):
            python = ensure_requirements_environment(
                REPO_ROOT,
                [REPO_ROOT / "tests" / "requirements.txt"],
                ("pre_commit", "pip_audit", "pytest", "yaml"),
                name="precommit",
                packages=("pre-commit~=4.0", "pip-audit~=2.9"),
            )
            if Path(sys.prefix).resolve() != python.parent.parent.resolve():
                raise SystemExit(
                    subprocess.run(  # noqa: S603 - managed Python and this entry point
                        [str(python), str(Path(__file__).resolve()), *sys.argv[1:]],
                        cwd=REPO_ROOT,
                        check=False,
                    ).returncode
                )
        raise SystemExit(main())
    except RuntimeError as exc:
        log.error("%s", exc)
        raise SystemExit(1) from exc
