#!/usr/bin/env python3
"""
Run pre-commit for the IJT repo, then for the Envelope submodule when present.

This is the simplest "before commit" helper for contributors: one command
handles the root repo and, when checked out, the private Envelope submodule.
"""

from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
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
        return 0
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
