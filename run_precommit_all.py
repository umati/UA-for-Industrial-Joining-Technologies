#!/usr/bin/env python3
"""
Run pre-commit for the IJT repo, then for the Envelope submodule when present.

This is the simplest "before commit" helper for contributors: one command
handles the root repo and, when checked out, the private Envelope submodule.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

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
    if importlib.util.find_spec("pre_commit") is None:
        raise RuntimeError("pre-commit is not installed. Run `pip install pre-commit` first.")
    return [sys.executable, "-m", "pre_commit"]


def _run_precommit(cwd: Path, label: str) -> int:
    print(f"[pre-commit] {label}: {cwd}")
    cmd = [*_precommit_command(), *PRECOMMIT_ARGS]
    completed = subprocess.run(cmd, cwd=cwd)  # noqa: S603 - fixed internal command list
    return completed.returncode


def _npm_command() -> str | None:
    candidates = ("npm.cmd", "npm.exe", "npm") if os.name == "nt" else ("npm",)
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return None


def _run_npm_lock_audit(cwd: Path, label: str) -> int:
    package_lock = cwd / "package-lock.json"
    package_json = cwd / "package.json"
    if not package_json.exists():
        print(f"[security] {label} skipped: {package_json} not found")
        return 0
    if not package_lock.exists():
        print(f"[security] {label} skipped: {package_lock} not found")
        return 0
    npm = _npm_command()
    if npm is None:
        print(
            "Error: npm was not found on PATH. Install Node.js/npm or open "
            "a shell where npm is available.",
            file=sys.stderr,
        )
        return 1
    print(f"[security] {label}: npm audit --package-lock-only --audit-level=high")
    cmd = [npm, "audit", "--package-lock-only", "--audit-level=high"]
    completed = subprocess.run(cmd, cwd=cwd)  # noqa: S603 - fixed internal command list
    return completed.returncode


def _run_python_requirements_audit() -> int:
    if importlib.util.find_spec("pip_audit") is None:
        print(
            "Error: pip-audit is not installed. Run `pip install pip-audit` first.", file=sys.stderr
        )
        return 1
    requirements = [req for req in PYTHON_AUDIT_REQUIREMENTS if req.exists()]
    if not requirements:
        print("[security] Python requirements audit skipped: no requirements files found")
        return 0
    print("[security] Python requirements: pip-audit --requirement ...")
    cache_dir = REPO_ROOT / "tmp" / "pip-audit-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = REPO_ROOT / "tmp" / "pip-audit-temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
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
    env = os.environ.copy()
    long_temp_dir = str(temp_dir.resolve())
    env["TMP"] = long_temp_dir
    env["TEMP"] = long_temp_dir
    env["TMPDIR"] = long_temp_dir
    completed = subprocess.run(cmd, cwd=REPO_ROOT, env=env)  # noqa: S603 - fixed internal command list
    return completed.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)

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
