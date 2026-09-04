#!/usr/bin/env python3
"""
Run pre-commit for the IJT repo, then for the Envelope submodule when present.

This is the simplest "before commit" helper for contributors: one command
handles the root repo and, when checked out, the private Envelope submodule.

All external tool dependencies (pre-commit, pip-audit, npm) are auto-installed
if missing; npm audit is skipped if npm is unavailable.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Final

# Add scripts/ to path for dependency_helpers
if str(Path(__file__).parent / "scripts") not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from dependency_helpers import (
    ensure_python_package,
    find_cmd,
)

log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

REPO_ROOT = Path(__file__).resolve().parent
WEB_CLIENT_DIR = REPO_ROOT / "OPC_UA_Clients" / "Release2" / "IJT_Web_Client"
NODE_CLIENT_DIR = REPO_ROOT / "OPC_UA_Clients" / "Release1" / "IJT_Node_Client"
CSHARP_DIR = REPO_ROOT / "OPC_UA_Clients" / "Release2" / "IJT_CSharp_Client"
CSHARP_SLN = CSHARP_DIR / "IJT_CSharp_Client.sln"
ENVELOPE_DIR = WEB_CLIENT_DIR / "src" / "javascripts" / "views" / "envelope"
PYTHON_AUDIT_REQUIREMENTS: tuple[Path, ...] = (
    REPO_ROOT / "tests" / "requirements.txt",
    REPO_ROOT / "reporting" / "requirements.txt",
    REPO_ROOT / "OPC_UA_Servers" / "Release2" / "tests" / "requirements.txt",
    REPO_ROOT / "OPC_UA_Clients" / "Release2" / "IJT_Console_Client" / "requirements.txt",
    REPO_ROOT / "OPC_UA_Clients" / "Release2" / "IJT_Console_Client" / "requirements-dev.txt",
    REPO_ROOT / "OPC_UA_Clients" / "Release2" / "IJT_Test_Client" / "requirements.txt",
    REPO_ROOT / "OPC_UA_Clients" / "Release2" / "IJT_Test_Client" / "requirements-dev.txt",
    REPO_ROOT / "OPC_UA_Clients" / "Release2" / "IJT_Web_Client" / "requirements.txt",
    REPO_ROOT / "OPC_UA_Clients" / "Release2" / "IJT_Web_Client" / "requirements-dev.txt",
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
            constraints = REPO_ROOT / "constraints.txt"
            c_args = ["-c", str(constraints)] if constraints.is_file() else []
            result = subprocess.run(  # noqa: S603 - fixed internal command list
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--quiet",
                    "--disable-pip-version-check",
                    *c_args,
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
    """Run subprocess with kwargs, falling back to positional (cmd, cwd) if mocked in tests."""
    try:
        kwargs: dict[str, object] = {"capture_output": capture_output, "text": capture_output}
        if env is not None:
            kwargs["env"] = env
        if timeout is not None:
            kwargs["timeout"] = timeout
        return subprocess.run(cmd, cwd=cwd, **kwargs)  # noqa: S603 - fixed internal command list
    except TypeError:
        try:
            if env is not None:
                return subprocess.run(cmd, cwd=cwd, env=env)  # noqa: S603 - fixed internal command list
        except TypeError:
            pass
        return subprocess.run(cmd, cwd=cwd)  # noqa: S603 - fixed internal command list


def _run_npm_lock_audit(
    cwd: Path, label: str, retries: int = 2, timeout_seconds: float = 15.0
) -> int:
    """Run npm audit on package-lock.json with strict/offline policy."""
    package_lock = cwd / "package-lock.json"
    package_json = cwd / "package.json"
    if not package_json.exists():
        log.info("[security] %s skipped: %s not found", label, package_json)
        return 0
    if not package_lock.exists():
        log.info("[security] %s skipped: %s not found", label, package_lock)
        return 0

    npm = find_cmd("npm.cmd", "npm.exe", "npm")
    if npm is None:
        log.warning(
            "[security] %s skipped: npm not found in PATH. Install Node.js to enable npm audit.",
            label,
        )
        return 0

    audit_mode = os.environ.get(NPM_AUDIT_MODE_ENV, NPM_AUDIT_MODE_STRICT).strip().lower()
    if audit_mode not in (NPM_AUDIT_MODE_STRICT, NPM_AUDIT_MODE_OFFLINE):
        log.warning(
            "[security] %s: invalid %s=%r; defaulting to '%s'",
            label,
            NPM_AUDIT_MODE_ENV,
            audit_mode,
            NPM_AUDIT_MODE_STRICT,
        )
        audit_mode = NPM_AUDIT_MODE_STRICT
    log.info(
        "[security] %s: npm audit --package-lock-only --audit-level=high (network mode: %s via %s)",
        label,
        audit_mode,
        NPM_AUDIT_MODE_ENV,
    )
    cmd = [
        npm,
        "audit",
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
                log.info("[security] %s: npm audit passed (%.2fs)", label, elapsed)
                return 0

            output = f"{getattr(completed, 'stdout', '')}\n{getattr(completed, 'stderr', '')}"
            is_transient_network_error = any(
                pattern in output for pattern in NPM_AUDIT_NETWORK_PATTERNS
            )
            if is_transient_network_error:
                if attempt < retries:
                    log.warning(
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
                    log.warning(
                        "[security] %s: npm audit registry endpoint unreachable/timed out "
                        "(offline or restricted network); offline mode allows continuing.",
                        label,
                    )
                    return 0
                log.error(
                    "[security] %s: npm audit failed due to registry connectivity in strict mode. "
                    "Fix network/proxy access, or set %s=%s only for explicitly offline local "
                    "runs.",
                    label,
                    NPM_AUDIT_MODE_ENV,
                    NPM_AUDIT_MODE_OFFLINE,
                )
                return 1

            if getattr(completed, "stdout", None):
                sys.stdout.write(completed.stdout)
                sys.stdout.flush()
            if getattr(completed, "stderr", None):
                sys.stderr.write(completed.stderr)
                sys.stderr.flush()
            return completed.returncode
        except subprocess.TimeoutExpired:
            if attempt < retries:
                log.warning(
                    "[security] %s: npm audit timed out on attempt %d/%d, retrying in %ds...",
                    label,
                    attempt,
                    retries,
                    2 * attempt,
                )
                time.sleep(2 * attempt)
                continue
            if audit_mode == NPM_AUDIT_MODE_OFFLINE:
                log.warning(
                    "[security] %s: npm audit registry request timed out (offline/slow network); "
                    "offline mode allows continuing.",
                    label,
                )
                return 0
            log.error(
                "[security] %s: npm audit timed out in strict mode. "
                "Fix npm registry connectivity, or set %s=%s only for explicitly offline local "
                "runs.",
                label,
                NPM_AUDIT_MODE_ENV,
                NPM_AUDIT_MODE_OFFLINE,
            )
            return 1

    return 0


def _run_python_requirements_audit(retries: int = 2, timeout_seconds: float = 60.0) -> int:
    """Run pip-audit on all Python requirements with retries. Auto-installs pip-audit if missing."""
    if not ensure_python_package("pip-audit", import_name="pip_audit"):
        log.warning(
            "[security] Python requirements audit skipped: pip-audit could not be installed. "
            "Manual install: pip install pip-audit"
        )
        return 0

    requirements = [req for req in PYTHON_AUDIT_REQUIREMENTS if req.exists()]
    if not requirements:
        log.info("[security] Python requirements audit skipped: no requirements files found")
        return 0

    log.info("[security] Python requirements: pip-audit --requirement ...")
    cache_dir = REPO_ROOT / "tmp" / "pip-audit-cache"
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
                log.info("[security] Python requirements: pip-audit passed (%.2fs)", elapsed)
                return 0

            output = f"{getattr(completed, 'stdout', '')}\n{getattr(completed, 'stderr', '')}"
            is_network_error = any(
                pattern in output
                for pattern in ("ConnectionError", "Timeout", "ECONNRESET", "ETIMEDOUT")
            )
            if is_network_error and attempt < retries:
                log.warning(
                    "[security] Python requirements audit network error on attempt %d/%d, "
                    "retrying...",
                    attempt,
                    retries,
                )
                time.sleep(2 * attempt)
                continue

            if getattr(completed, "stdout", None):
                sys.stdout.write(completed.stdout)
                sys.stdout.flush()
            if getattr(completed, "stderr", None):
                sys.stderr.write(completed.stderr)
                sys.stderr.flush()
            return completed.returncode
        except subprocess.TimeoutExpired:
            log.warning(
                "[security] Python requirements audit timed out on attempt %d/%d",
                attempt,
                retries,
            )
            if attempt < retries:
                time.sleep(2 * attempt)
                continue
            return 1

    return 1


def _run_csharp_nuget_audit(timeout_seconds: float = 120.0) -> int:
    """Run dotnet list package --vulnerable on C# solution. Auto-skipped if dotnet is missing."""
    csharp_sln = (
        REPO_ROOT / "OPC_UA_Clients" / "Release2" / "IJT_CSharp_Client" / "IJT_CSharp_Client.sln"
    )
    if not csharp_sln.exists():
        log.info("[security] C# Client skipped: %s not found", csharp_sln)
        return 0

    dotnet = find_cmd("dotnet.exe", "dotnet")
    if dotnet is None:
        log.warning(
            "[security] C# Client skipped: dotnet not found in PATH. "
            "Install .NET SDK to enable NuGet audit."
        )
        return 0

    log.info("[security] C# Client: dotnet list package --vulnerable --include-transitive")
    cmd = [
        dotnet,
        "list",
        str(csharp_sln),
        "package",
        "--vulnerable",
        "--include-transitive",
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
            elapsed = time.monotonic() - t0
            log.info("[security] C# Client: NuGet audit passed (%.2fs)", elapsed)
            return 0

        if getattr(completed, "stdout", None):
            sys.stdout.write(completed.stdout)
            sys.stdout.flush()
        if getattr(completed, "stderr", None):
            sys.stderr.write(completed.stderr)
            sys.stderr.flush()
        return completed.returncode
    except subprocess.TimeoutExpired:
        log.warning("[security] C# Client: NuGet audit timed out")
        return 1


def _run_all_npm_lock_audits() -> int:
    """Run npm lock audits sequentially across JS projects to prevent registry rate-limiting."""
    for label, cwd in (
        ("Node Client", NODE_CLIENT_DIR),
        ("Web Client", WEB_CLIENT_DIR),
        ("Envelope", ENVELOPE_DIR),
    ):
        code = _run_npm_lock_audit(cwd, label)
        if code != 0:
            return code
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--audits-only",
        action="store_true",
        help="Run dependency vulnerability audits without pre-commit hooks.",
    )
    args = parser.parse_args(argv)

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

        # Run audits sequentially to prevent package managers from competing for
        # network sockets. Run every audit even after a failure so one unavailable
        # ecosystem never hides the security status of the remaining ecosystems.
        audit_failures: list[tuple[str, int]] = []
        for label, fn in [
            ("C# Client", _run_csharp_nuget_audit),
            ("npm audits", _run_all_npm_lock_audits),
            ("Python requirements", _run_python_requirements_audit),
        ]:
            code = fn()
            if code != 0:
                log.error("[security] %s audit failed with code %d", label, code)
                audit_failures.append((label, code))

        if audit_failures:
            log.error(
                "[security] %d dependency audit group(s) failed: %s",
                len(audit_failures),
                ", ".join(label for label, _code in audit_failures),
            )
            return 1

        elapsed = time.monotonic() - overall_t0
        if args.audits_only:
            log.info("All dependency vulnerability audits completed successfully in %.2fs", elapsed)
        else:
            log.info("All pre-commit checks and audits completed successfully in %.2fs", elapsed)
        return 0
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
