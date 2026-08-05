#!/usr/bin/env python3
"""
Shared dependency management helpers for IJT test runners.

Provides graceful handling of optional tools (docker, dotnet, npm) and
automatic Python package installation from requirements files.

This is the single source of truth for how the repo handles missing
dependencies — all runners should use these helpers.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

log = logging.getLogger(__name__)


class ToolStatus(NamedTuple):
    """Status of a required tool."""

    available: bool
    path: str | None
    reason: str | None = None


def find_cmd(*candidates: str) -> str | None:
    """Find first available command from candidates in PATH.

    Args:
        *candidates: Command names to search for (e.g., "docker", "docker.exe")

    Returns:
        Full path to the command if found, None otherwise.
    """
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return None


def check_tool(*candidates: str, name: str | None = None) -> ToolStatus:
    """Check if a tool is available in PATH.

    Args:
        *candidates: Command names to search for
        name: Display name for the tool (defaults to first candidate)

    Returns:
        ToolStatus with availability and optional reason for unavailability
    """
    cmd = find_cmd(*candidates)
    tool_name = name or candidates[0]
    if cmd:
        return ToolStatus(available=True, path=cmd)
    return ToolStatus(
        available=False,
        path=None,
        reason=f"'{tool_name}' not found in PATH",
    )


def skip_suite(name: str, reason: str) -> dict:
    """Return a suite result that represents a skipped test.

    Use this when a suite is skipped due to missing dependencies.

    Args:
        name: Suite name
        reason: Why the suite was skipped

    Returns:
        Dict compatible with SuiteResult for skipped tests
    """
    return {
        "name": name,
        "ok": True,
        "skipped": True,
        "notes": [reason],
    }


def ensure_python_package(
    package_name: str,
    import_name: str | None = None,
    *pip_args: str,
    quiet: bool = True,
) -> bool:
    """Install a Python package if not already installed.

    Args:
        package_name: Package name as it appears in PyPI (e.g., "pre-commit")
        import_name: Name to use for import check (defaults to package_name)
        *pip_args: Extra args to pass to pip install (e.g., "--upgrade")
        quiet: If True, suppress pip output

    Returns:
        True if package is available (was or is now installed), False if install failed

    Example:
        ensure_python_package("pre-commit", import_name="pre_commit")
        ensure_python_package("pip-audit", import_name="pip_audit")
    """
    import importlib.util

    check_name = import_name or package_name.replace("-", "_")

    # Already installed?
    if importlib.util.find_spec(check_name) is not None:
        return True

    # Not installed — try to install
    log.info("Installing %s...", package_name)
    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        package_name,
        *pip_args,
    ]
    if quiet:
        cmd.append("--quiet")

    result = subprocess.run(cmd, capture_output=quiet)  # noqa: S603
    if result.returncode != 0:
        log.warning("Failed to install %s (exit=%d)", package_name, result.returncode)
        return False

    log.info("Successfully installed %s", package_name)
    return importlib.util.find_spec(check_name) is not None


def ensure_npm_packages(
    cwd: Path,
    quiet: bool = True,
) -> bool:
    """Install npm dependencies (package-lock.json) if needed.

    Args:
        cwd: Working directory containing package.json and package-lock.json
        quiet: If True, suppress npm output

    Returns:
        True if packages are installed or already present, False if install failed
    """
    package_json = cwd / "package.json"
    package_lock = cwd / "package-lock.json"
    node_modules = cwd / "node_modules"

    if not package_json.exists() or not package_lock.exists():
        return True  # Nothing to install

    # Already installed? Skip to avoid redundant npm ci
    if node_modules.exists():
        log.info("[npm] Dependencies already present in %s", cwd)
        return True

    npm = find_cmd("npm.cmd", "npm.exe", "npm")
    if not npm:
        log.warning("npm not found in PATH; skipping npm install for %s", cwd.name)
        return False

    log.info("[npm] Installing dependencies in %s...", cwd)
    cmd = [npm, "ci"]  # ci = "clean install" (respects package-lock.json)
    kwargs = {"cwd": str(cwd)}
    if quiet:
        kwargs.update({"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL})

    result = subprocess.run(cmd, **kwargs)  # noqa: S603
    if result.returncode != 0:
        log.warning("[npm] ci failed in %s (exit=%d)", cwd, result.returncode)
        return False

    log.info("[npm] Dependencies installed in %s", cwd)
    return True


def ensure_python_venv(
    venv_dir: Path,
) -> Path | None:
    """Create a Python virtual environment if it doesn't exist.

    Args:
        venv_dir: Path to venv directory

    Returns:
        Path to venv python executable, or None if creation failed
    """
    venv_py = (
        venv_dir / "Scripts" / "python.exe"
        if sys.platform == "win32"
        else venv_dir / "bin" / "python"
    )

    if venv_py.exists():
        return venv_py

    log.info("Creating venv in %s...", venv_dir)
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "venv", str(venv_dir)],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        log.error("Failed to create venv: %s", result.stderr)
        return None

    return venv_py


def pip_constraint_args(repo_root: Path | None = None) -> list[str]:
    """Get pip constraint args for dependency resolution.

    Args:
        repo_root: Repository root (auto-detected if None)

    Returns:
        List of pip args (e.g., ["-c", "constraints.txt"]) if constraints exist
    """
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[1]

    constraints = repo_root / "constraints.txt"
    if constraints.exists():
        return ["-c", str(constraints)]
    return []


def log_skip_reason(
    suite_name: str,
    tool_name: str,
    status: ToolStatus,
) -> None:
    """Log a formatted skip reason for a suite.

    Args:
        suite_name: Name of the test suite being skipped
        tool_name: Name of the tool that's missing
        status: ToolStatus from check_tool()
    """
    reason = status.reason or f"{tool_name} not available"
    log.warning(
        "⊘ %s (skipped) — %s. Install %s to run this suite.",
        suite_name,
        reason,
        tool_name,
    )
