"""Repository hygiene tests.

These tests catch common artefact / secret-leakage issues:
  - No .pyc files or __pycache__ dirs tracked by git
  - No node_modules/ tracked by git
  - The root .gitignore covers critical patterns
  - No obvious hardcoded secrets in Python source files
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
# The git repo root is three levels up from the IJT_Web_Client directory
_GIT_ROOT = _PROJECT_ROOT.parents[2]  # UA-for-Industrial-Joining-Technologies/


def _git_available() -> bool:
    return shutil.which("git") is not None


def _git_ls_files(pattern: str) -> list[str]:
    """Return git-tracked files matching pattern (empty list if none / git error)."""
    result = subprocess.run(
        ["git", "ls-files", pattern],
        capture_output=True,
        text=True,
        cwd=str(_GIT_ROOT),
    )
    if result.returncode != 0:
        return []
    lines = result.stdout.strip().splitlines()
    return [l for l in lines if l]


# ===========================================================================
# 1. Git-tracked artefacts
# ===========================================================================


@pytest.mark.skipif(
    not _git_available(),
    reason="git not installed — skipping tracked-artefact checks",
)
class TestGitTrackedArtefacts:
    def test_no_pyc_files_tracked(self):
        """No .pyc files should be committed to git."""
        tracked = _git_ls_files("*.pyc")
        assert tracked == [], (
            f"The following .pyc files are tracked by git:\n  "
            + "\n  ".join(tracked)
        )

    def test_no_pycache_dirs_tracked(self):
        """No __pycache__/ directories should be tracked by git."""
        tracked = _git_ls_files("*/__pycache__/*")
        assert tracked == [], (
            f"Files inside __pycache__/ are tracked by git:\n  "
            + "\n  ".join(tracked)
        )

    def test_no_node_modules_tracked(self):
        """No node_modules/ content should be committed to git."""
        tracked = _git_ls_files("*/node_modules/*")
        assert tracked == [], (
            f"Files inside node_modules/ are tracked by git:\n  "
            + "\n  ".join(tracked)
        )

    def test_no_pytest_cache_tracked(self):
        """No .pytest_cache/ content should be committed to git."""
        tracked = _git_ls_files("*/.pytest_cache/*")
        assert tracked == [], (
            f"Files inside .pytest_cache/ are tracked by git:\n  "
            + "\n  ".join(tracked)
        )

    def test_no_env_files_with_secrets_tracked(self):
        """Tracked .env files must not contain obvious secrets (passwords/tokens).

        Note: .env files with only configuration values (ports, flags) are acceptable.
        Files with actual secret values should use .env.local or be untracked.
        """
        tracked = _git_ls_files("*.env")
        # .env.example files are always fine
        real_env_files = [f for f in tracked if not f.endswith(".env.example")]

        secret_patterns = [
            re.compile(r'password\s*=\s*\S+', re.IGNORECASE),
            re.compile(r'secret\s*=\s*\S+', re.IGNORECASE),
            re.compile(r'api_key\s*=\s*\S+', re.IGNORECASE),
            re.compile(r'token\s*=\s*[A-Za-z0-9+/]{16,}', re.IGNORECASE),
            re.compile(r'private_key\s*=\s*\S+', re.IGNORECASE),
        ]

        for rel_path in real_env_files:
            full_path = _GIT_ROOT / rel_path
            if not full_path.exists():
                continue
            content = full_path.read_text(encoding="utf-8", errors="ignore")
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("#") or not stripped:
                    continue
                for pat in secret_patterns:
                    assert not pat.search(stripped), (
                        f"Possible secret in tracked file {rel_path}: {stripped!r}"
                    )


# ===========================================================================
# 2. .gitignore coverage
# ===========================================================================


class TestGitignoreCoverage:
    """Verify the root .gitignore covers all critical patterns."""

    _GITIGNORE_PATH = _GIT_ROOT / ".gitignore"

    def _gitignore_text(self) -> str:
        if not self._GITIGNORE_PATH.exists():
            pytest.skip(f".gitignore not found at {self._GITIGNORE_PATH}")
        return self._GITIGNORE_PATH.read_text(encoding="utf-8")

    def test_gitignore_covers_pycache(self):
        """__pycache__/ must be in .gitignore."""
        text = self._gitignore_text()
        assert "__pycache__/" in text, "__pycache__/ not found in .gitignore"

    def test_gitignore_covers_pyc_files(self):
        """*.pyc (or *.py[cod]) must be in .gitignore."""
        text = self._gitignore_text()
        has_pyc = "*.pyc" in text or "*.py[cod]" in text or "*.py[co]" in text
        assert has_pyc, "*.pyc pattern not found in .gitignore"

    def test_gitignore_covers_node_modules(self):
        """node_modules/ must be in .gitignore."""
        text = self._gitignore_text()
        assert "node_modules/" in text, "node_modules/ not found in .gitignore"

    def test_gitignore_covers_log_files(self):
        """*.log must be in .gitignore."""
        text = self._gitignore_text()
        assert "*.log" in text, "*.log not found in .gitignore"

    def test_gitignore_covers_venv(self):
        """venv/ must be in .gitignore."""
        text = self._gitignore_text()
        assert "venv/" in text, "venv/ not found in .gitignore"

    def test_gitignore_covers_code_workspace(self):
        """*.code-workspace must be in .gitignore (personal IDE workspace files)."""
        text = self._gitignore_text()
        assert "*.code-workspace" in text, "*.code-workspace not found in .gitignore"


# ===========================================================================
# 3. connectionpoints.json — default config enforcement
# ===========================================================================


class TestConnectionpointsDefault:
    """Enforce that committed connectionpoints.json files contain only the LOCAL entry.

    Developers may add extra entries locally, but must not push them.
    CI catches this automatically.
    """

    _LOCAL_NAMES = {"local", "localhost"}

    @pytest.mark.skipif(
        not _git_available(),
        reason="git not installed — skipping connectionpoints checks",
    )
    def test_web_client_connectionpoints_has_only_local(self):
        """src/resources/connectionpoints.json in IJT_Web_Client must have exactly one
        entry and it must be the LOCAL endpoint (127.0.0.1 / localhost)."""
        import json

        path = (
            _GIT_ROOT
            / "OPC_UA_Clients"
            / "Release2"
            / "IJT_Web_Client"
            / "src"
            / "resources"
            / "connectionpoints.json"
        )
        if not path.exists():
            pytest.skip(f"connectionpoints.json not found at {path}")

        data = json.loads(path.read_text(encoding="utf-8"))
        points = data.get("connectionpoints", [])

        assert len(points) == 1, (
            f"connectionpoints.json must contain exactly 1 entry (the LOCAL endpoint), "
            f"but found {len(points)} entries: "
            + ", ".join(p.get("name", "?") for p in points)
            + "\n  Remove personal/team endpoints before committing."
        )

        name = points[0].get("name", "").strip().lower()
        address = points[0].get("address", "")
        is_local = name in self._LOCAL_NAMES or "127.0.0.1" in address or "localhost" in address
        assert is_local, (
            f"The single entry in connectionpoints.json must be the LOCAL endpoint "
            f"(name 'LOCAL' or address 127.0.0.1/localhost), got: name={points[0].get('name')!r}, "
            f"address={address!r}"
        )

    @pytest.mark.skipif(
        not _git_available(),
        reason="git not installed — skipping connectionpoints checks",
    )
    def test_no_code_workspace_files_tracked(self):
        """*.code-workspace files must not be committed (personal IDE workspace files)."""
        tracked = _git_ls_files("*.code-workspace")
        assert tracked == [], (
            "The following *.code-workspace files are tracked by git and must be removed:\n  "
            + "\n  ".join(tracked)
            + "\n  Run: git rm --cached <file>  then commit the removal."
        )


# ===========================================================================
# 3. No hardcoded secrets in Python source
# ===========================================================================


_SECRET_PATTERNS = [
    re.compile(r'password\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
    re.compile(r'secret\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
    re.compile(r'api_key\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
    re.compile(r'token\s*=\s*["\'][^"\']{8,}["\']', re.IGNORECASE),
    re.compile(r'private_key\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
]

# Patterns that are legitimately in source files (not real secrets)
_ALLOWLIST_PATTERNS = [
    re.compile(r'password\s*=\s*["\']["\']'),       # empty string
    re.compile(r'password\s*=\s*None'),
    re.compile(r'password.*env.*get', re.IGNORECASE),  # from env var
    re.compile(r'#.*password', re.IGNORECASE),       # comment
]


def _is_allowlisted(line: str) -> bool:
    return any(pat.search(line) for pat in _ALLOWLIST_PATTERNS)


class TestNoHardcodedSecrets:
    def _scan_file(self, path: Path) -> list[str]:
        violations: list[str] = []
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return violations
        for lineno, line in enumerate(text.splitlines(), start=1):
            if _is_allowlisted(line):
                continue
            for pat in _SECRET_PATTERNS:
                if pat.search(line):
                    violations.append(f"{path.relative_to(_PROJECT_ROOT)}:{lineno}: {line.strip()}")
                    break
        return violations

    def test_no_hardcoded_secrets_in_python_source(self):
        """No hardcoded password/secret/token literals in src/python/."""
        src_python = _PROJECT_ROOT / "src" / "python"
        if not src_python.exists():
            pytest.skip("src/python/ not found")

        all_violations: list[str] = []
        for py_file in src_python.rglob("*.py"):
            all_violations.extend(self._scan_file(py_file))

        assert not all_violations, (
            "Possible hardcoded secrets found in Python source:\n  "
            + "\n  ".join(all_violations)
        )
