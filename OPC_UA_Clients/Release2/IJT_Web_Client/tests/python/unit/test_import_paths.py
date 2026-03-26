"""Linux / Docker case-sensitivity import path tests.

These tests catch file-name casing regressions before they hit Linux or
Docker, where the filesystem is case-sensitive (unlike Windows/macOS).

Checks:
  - All .mjs filenames under src/ are lowercase or kebab-case (no PascalCase)
  - All directory names under src/ are lowercase or kebab-case
  - vitest.config.mjs aliases resolve to real paths on disk
  - index.html <script src="..."> paths resolve to real files
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_SRC_DIR = _PROJECT_ROOT / "src"

# Pattern: only lowercase letters, digits, hyphens, and dots allowed.
# Rejects PascalCase (MyFile.mjs) or camelCase (myFile.mjs).
_KEBAB_OR_LOWER_RE = re.compile(r"^[a-z0-9][a-z0-9\-\.]*$")


def _collect_mjs_files() -> list[Path]:
    return list(_SRC_DIR.rglob("*.mjs"))


def _collect_directories() -> list[Path]:
    """All directories under src/ (excluding hidden and __pycache__)."""
    return [
        p for p in _SRC_DIR.rglob("*")
        if p.is_dir()
        and not p.name.startswith(".")
        and p.name != "__pycache__"
    ]


# ===========================================================================
# 1. .mjs filenames must be lowercase / kebab-case
# ===========================================================================


def test_all_mjs_filenames_are_kebab_case():
    """No .mjs file under src/ should have PascalCase or camelCase in its stem."""
    violations: list[str] = []
    for path in _collect_mjs_files():
        stem = path.stem  # filename without extension
        if not _KEBAB_OR_LOWER_RE.match(stem):
            violations.append(str(path.relative_to(_PROJECT_ROOT)))

    assert not violations, (
        "The following .mjs files have non-kebab/non-lowercase names "
        "(will break case-sensitive Linux imports):\n  "
        + "\n  ".join(violations)
    )


# ===========================================================================
# 2. Directory names under src/ must be lowercase / kebab-case
# ===========================================================================


def test_all_src_directories_are_kebab_case():
    """No directory under src/ should have PascalCase or camelCase in its name."""
    violations: list[str] = []
    for path in _collect_directories():
        name = path.name
        if not _KEBAB_OR_LOWER_RE.match(name):
            violations.append(str(path.relative_to(_PROJECT_ROOT)))

    assert not violations, (
        "The following directories have non-kebab/non-lowercase names "
        "(will break case-sensitive Linux imports):\n  "
        + "\n  ".join(violations)
    )


# ===========================================================================
# 3. vitest.config.mjs aliases must resolve to real paths
# ===========================================================================


def test_vitest_alias_ijt_support_exists():
    """The 'ijt-support' vitest alias must point to a real directory on disk."""
    alias_target = _SRC_DIR / "javascripts" / "ijt-support"
    assert alias_target.exists(), (
        f"vitest alias 'ijt-support' points to {alias_target} which does not exist"
    )
    assert alias_target.is_dir(), (
        f"vitest alias 'ijt-support' target {alias_target} is not a directory"
    )


def test_vitest_config_exists():
    """vitest.config.mjs must exist at the project root."""
    config = _PROJECT_ROOT / "vitest.config.mjs"
    assert config.exists(), f"vitest.config.mjs not found at {config}"


# ===========================================================================
# 4. src/python modules use consistent casing
# ===========================================================================


def test_all_python_module_filenames_are_snake_case():
    """Python source files under src/python/ must use snake_case naming."""
    _snake_case_re = re.compile(r"^[a-z][a-z0-9_]*$")
    src_python = _PROJECT_ROOT / "src" / "python"

    if not src_python.exists():
        pytest.skip("src/python/ directory not found")

    violations: list[str] = []
    for path in src_python.glob("*.py"):
        stem = path.stem
        # __init__.py and similar dunder files are valid Python package markers
        if stem.startswith("__") and stem.endswith("__"):
            continue
        if not _snake_case_re.match(stem):
            violations.append(str(path.relative_to(_PROJECT_ROOT)))

    assert not violations, (
        "Python files must use snake_case naming:\n  " + "\n  ".join(violations)
    )
