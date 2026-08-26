#!/usr/bin/env python3
"""Run pytest-backed pre-commit hooks with deterministic local dependencies."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _ensure_pytest_dependencies() -> int:
    if (
        importlib.util.find_spec("pytest") is not None
        and importlib.util.find_spec("yaml") is not None
    ):
        return 0

    req = REPO_ROOT / "tests" / "requirements.txt"
    if not req.is_file():
        return 0

    constraints = REPO_ROOT / "constraints.txt"
    c_args = ["-c", str(constraints)] if constraints.is_file() else []
    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--quiet",
        "--disable-pip-version-check",
        *c_args,
        "-r",
        str(req),
    ]
    return subprocess.run(cmd, check=False).returncode  # noqa: S603 - fixed internal command list


def main() -> int:
    rc = _ensure_pytest_dependencies()
    if rc != 0:
        print(
            "ERROR: Failed to auto-install root test dependencies for pre-commit",
            file=sys.stderr,
        )
        return rc

    cmd = [sys.executable, "-m", "pytest", *sys.argv[1:]]
    return subprocess.run(  # noqa: S603 - fixed internal command list
        cmd, cwd=str(REPO_ROOT), check=False
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
