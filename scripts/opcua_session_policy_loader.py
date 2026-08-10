"""Helpers for locating and importing the shared OPC UA session policy."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType


def locate_repo_scripts_dir(start_file: str | Path) -> Path:
    """Return the repo-level ``scripts`` directory for *start_file*.

    Walks upward from the caller location until it finds the shared session
    policy module. This avoids brittle fixed parent-depth assumptions across the
    Test, Console, and Web client folder layouts.
    """

    current = Path(start_file).resolve()
    search_roots = [current] if current.is_dir() else [current.parent]
    for root in search_roots:
        for base in (root, *root.parents):
            scripts_dir = base / "scripts"
            if (scripts_dir / "opcua_session_policy.py").is_file():
                return scripts_dir
    raise ModuleNotFoundError(
        "The shared IJT OPC UA session policy module was not found. "
        "Use the full UA-for-Industrial-Joining-Technologies repository checkout "
        "or include the top-level scripts\\opcua_session_policy.py file."
    )


def load_shared_session_policy(start_file: str | Path) -> ModuleType:
    """Import and return the shared OPC UA session policy module."""

    scripts_dir = locate_repo_scripts_dir(start_file)
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    import opcua_session_policy  # pylint: disable=import-outside-toplevel

    return opcua_session_policy
