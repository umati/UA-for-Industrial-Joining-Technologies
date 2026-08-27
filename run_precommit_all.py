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
import subprocess
import sys
import tempfile
from pathlib import Path

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
    format="%(levelname)s: %(message)s",
)

REPO_ROOT = Path(__file__).resolve().parent
WEB_CLIENT_DIR = REPO_ROOT / "OPC_UA_Clients" / "Release2" / "IJT_Web_Client"
NODE_CLIENT_DIR = REPO_ROOT / "OPC_UA_Clients" / "Release1" / "IJT_Node_Client"
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


def _run_precommit(cwd: Path, label: str) -> int:
    """Run pre-commit in the given directory."""
    log.info("[pre-commit] %s: %s", label, cwd)
    cmd = [*_precommit_command(), *PRECOMMIT_ARGS]
    completed = subprocess.run(cmd, cwd=cwd)  # noqa: S603 - fixed internal command list
    return completed.returncode


def _run_npm_lock_audit(cwd: Path, label: str) -> int:
    """Run npm audit on package-lock.json. Returns 0 if audit passes or is skipped."""
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

    log.info("[security] %s: npm audit --package-lock-only --audit-level=high", label)
    cmd = [npm, "audit", "--package-lock-only", "--audit-level=high"]
    completed = subprocess.run(cmd, cwd=cwd)  # noqa: S603 - fixed internal command list
    return completed.returncode


def _run_python_requirements_audit() -> int:
    """Run pip-audit on all Python requirements. Auto-installs pip-audit if missing."""
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
    # Resolve a canonical temp dir to avoid 8.3 short-name vs long-name path
    # mismatches on Windows (and any similar symlink/junction issues on other
    # platforms). tempfile.gettempdir() returns the real resolved path on all
    # platforms without any Windows-specific branching.
    canonical_tmp = str(Path(tempfile.gettempdir()).resolve())
    env = os.environ.copy()
    env["TMP"] = canonical_tmp
    env["TEMP"] = canonical_tmp
    env["TMPDIR"] = canonical_tmp
    completed = subprocess.run(cmd, cwd=REPO_ROOT, env=env)  # noqa: S603 - fixed internal command list
    return completed.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)

    if not find_cmd("git.exe", "git"):
        print(
            "Error: Git is not found in PATH. Install Git to run pre-commit checks.",
            file=sys.stderr,
        )
        return 1

    try:
        root_code = _run_precommit(REPO_ROOT, "IJT root")
        if root_code != 0:
            return root_code

        envelope_config = ENVELOPE_DIR / ".pre-commit-config.yaml"
        if envelope_config.exists():
            envelope_code = _run_precommit(ENVELOPE_DIR, "Envelope")
            if envelope_code != 0:
                return envelope_code
        else:
            print(f"[pre-commit] Envelope skipped: {envelope_config} not found")

        for label, cwd in (
            ("Node Client", NODE_CLIENT_DIR),
            ("Web Client", WEB_CLIENT_DIR),
            ("Envelope", ENVELOPE_DIR),
        ):
            audit_code = _run_npm_lock_audit(cwd, label)
            if audit_code != 0:
                return audit_code

        python_audit_code = _run_python_requirements_audit()
        if python_audit_code != 0:
            return python_audit_code
        return 0
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
