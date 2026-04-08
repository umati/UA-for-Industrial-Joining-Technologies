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
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _find_git_root() -> Path:
    """Locate the repository root.

    Tries ``git rev-parse --show-toplevel`` first so the result is always
    correct regardless of where this file lives (native checkout, Docker,
    WSL, …).  Falls back to path arithmetic for environments without git,
    and ultimately to *_PROJECT_ROOT* if arithmetic also fails (e.g. the
    project is installed directly under ``/app`` in Docker).
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            cwd=str(_PROJECT_ROOT),
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except FileNotFoundError:
        pass  # git not on PATH — fall through to path-arithmetic fallback below
    # Path-arithmetic fallback: three levels up from IJT_Web_Client root.
    try:
        return _PROJECT_ROOT.parents[2]
    except IndexError:
        return _PROJECT_ROOT


_GIT_ROOT = _find_git_root()


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
    return [line for line in lines if line]


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
        assert tracked == [], "The following .pyc files are tracked by git:\n  " + "\n  ".join(tracked)

    def test_no_pycache_dirs_tracked(self):
        """No __pycache__/ directories should be tracked by git."""
        tracked = _git_ls_files("*/__pycache__/*")
        assert tracked == [], "Files inside __pycache__/ are tracked by git:\n  " + "\n  ".join(tracked)

    def test_no_node_modules_tracked(self):
        """No node_modules/ content should be committed to git."""
        tracked = _git_ls_files("*/node_modules/*")
        assert tracked == [], "Files inside node_modules/ are tracked by git:\n  " + "\n  ".join(tracked)

    def test_no_pytest_cache_tracked(self):
        """No .pytest_cache/ content should be committed to git."""
        tracked = _git_ls_files("*/.pytest_cache/*")
        assert tracked == [], "Files inside .pytest_cache/ are tracked by git:\n  " + "\n  ".join(tracked)

    def test_no_env_files_with_secrets_tracked(self):
        """Tracked .env files must not contain obvious secrets (passwords/tokens).

        Note: .env files with only configuration values (ports, flags) are acceptable.
        Files with actual secret values should use .env.local or be untracked.
        """
        tracked = _git_ls_files("*.env")
        # .env.example files are always fine
        real_env_files = [f for f in tracked if not f.endswith(".env.example")]

        secret_patterns = [
            re.compile(r"password\s*=\s*\S+", re.IGNORECASE),
            re.compile(r"secret\s*=\s*\S+", re.IGNORECASE),
            re.compile(r"api_key\s*=\s*\S+", re.IGNORECASE),
            re.compile(r"token\s*=\s*[A-Za-z0-9+/]{16,}", re.IGNORECASE),
            re.compile(r"private_key\s*=\s*\S+", re.IGNORECASE),
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
                    assert not pat.search(stripped), f"Possible secret in tracked file {rel_path}: {stripped!r}"

    def test_no_code_workspace_files_tracked(self):
        """*.code-workspace files must not be committed (personal IDE workspace files)."""
        tracked = _git_ls_files("*.code-workspace")
        assert tracked == [], (
            "The following *.code-workspace files are tracked by git and must be removed:\n  "
            + "\n  ".join(tracked)
            + "\n  Run: git rm --cached <file>  then commit the removal."
        )


# ===========================================================================
# 2. .gitignore coverage
# ===========================================================================


class TestGitignoreCoverage:
    """Verify the root .gitignore covers all critical patterns."""

    _GITIGNORE_PATH = _GIT_ROOT / ".gitignore"

    def _gitignore_text(self) -> str:
        if not self._GITIGNORE_PATH.exists():
            if (_GIT_ROOT / ".git").exists():
                pytest.fail(f".gitignore missing from git repo at {self._GITIGNORE_PATH}")
            pytest.skip(f".gitignore not found at {self._GITIGNORE_PATH} (no .git — Docker / non-checkout environment)")
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
            _GIT_ROOT / "OPC_UA_Clients" / "Release2" / "IJT_Web_Client" / "src" / "resources" / "connectionpoints.json"
        )
        if not path.exists():
            if (_GIT_ROOT / ".git").exists():
                pytest.fail(f"connectionpoints.json missing from git repo at {path}")
            pytest.skip(f"connectionpoints.json not found at {path} (no .git — Docker / non-checkout environment)")

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
    re.compile(r'password\s*=\s*["\']["\']'),  # empty string
    re.compile(r"password\s*=\s*None"),
    re.compile(r"password.*env.*get", re.IGNORECASE),  # from env var
    re.compile(r"#.*password", re.IGNORECASE),  # comment
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
            pytest.fail("src/python/ not found")

        all_violations: list[str] = []
        for py_file in src_python.rglob("*.py"):
            all_violations.extend(self._scan_file(py_file))

        assert not all_violations, "Possible hardcoded secrets found in Python source:\n  " + "\n  ".join(
            all_violations
        )


# ===========================================================================
# 4. JS source code quality — fix regression tests
# ===========================================================================


_JS_SRC_ROOT = _PROJECT_ROOT / "src" / "javascripts"


class TestJsCodeQuality:
    """Regression tests that catch specific known bugs so they cannot be reintroduced."""

    def test_model_to_html_no_variable_shadowing(self):
        """model-to-html.mjs must not redeclare onScreen with 'const' inside display().

        Regression test for M-6: 'const onScreen = this.toHTML(...)' inside the
        if-branch of display() shadows the outer 'let onScreen', making the outer
        variable permanently unassigned in that branch.
        """
        path = _JS_SRC_ROOT / "views" / "address-space" / "model-to-html.mjs"
        if not path.exists():
            pytest.fail(f"model-to-html.mjs not found at {path}")
        content = path.read_text(encoding="utf-8")
        # The fix removes 'const onScreen = this.toHTML(...)' and uses assignment instead
        assert "const onScreen = this.toHTML(" not in content, (
            "model-to-html.mjs still has 'const onScreen = this.toHTML(...)' inside display(). "
            "This shadows the outer 'let onScreen'. Change to assignment: 'onScreen = this.toHTML(...)'"
        )

    def test_result_manager_object_assign_filters_proto_keys(self):
        """result-manager.mjs handlePartial must not use bare Object.assign with newResult.

        Regression test for L-1: bare Object.assign(stored, newResult) allows prototype
        pollution if newResult contains __proto__, constructor, or prototype keys.
        The fix destructures to strip those keys first.
        """
        path = _JS_SRC_ROOT / "ijt-support" / "results" / "result-manager.mjs"
        if not path.exists():
            pytest.fail(f"result-manager.mjs not found at {path}")
        content = path.read_text(encoding="utf-8")
        assert "Object.assign(stored, newResult)" not in content, (
            "result-manager.mjs uses bare Object.assign(stored, newResult) which is vulnerable "
            "to prototype pollution. Destructure __proto__/constructor/prototype keys out first."
        )

    def test_connection_graphics_uses_textcontent_not_innerhtml(self):
        """connection-graphics.mjs must use textContent not innerHTML for status labels.

        Regression test: innerHTML = 'ESTABLISHED'/'LOST' triggers CodeQL XSS warnings
        even for hardcoded strings. textContent is semantically correct and safe.
        """
        path = _JS_SRC_ROOT / "views" / "connection" / "connection-graphics.mjs"
        if not path.exists():
            pytest.fail(f"connection-graphics.mjs not found at {path}")
        content = path.read_text(encoding="utf-8")
        assert "innerHTML = 'ESTABLISHED'" not in content, (
            "connection-graphics.mjs still uses innerHTML = 'ESTABLISHED'. "
            "Use textContent = 'ESTABLISHED' instead to avoid CodeQL XSS warnings."
        )
        assert "innerHTML = 'LOST'" not in content, (
            "connection-graphics.mjs still uses innerHTML = 'LOST'. Use textContent = 'LOST' instead."
        )
        assert "textContent = 'ESTABLISHED'" in content, "connection-graphics.mjs must set textContent = 'ESTABLISHED'."

    def test_settings_labels_use_textcontent_not_innerhtml(self):
        """settings.mjs must use textContent not innerHTML for static label text.

        Regression test: CodeQL flags all innerHTML assignments as potential XSS vectors,
        even hardcoded strings. textContent is the correct API for plain-text content.
        """
        path = _JS_SRC_ROOT / "views" / "graphic-support" / "settings.mjs"
        if not path.exists():
            pytest.fail(f"settings.mjs not found at {path}")
        content = path.read_text(encoding="utf-8")
        # None of the label assignments should use innerHTML any more
        for label in (
            "ProductId",
            "Button 1 selection",
            "Button 2 selection",
            "Joint 1 identity",
            "Joint 2 identity",
            "Default view level",
        ):
            assert f"innerHTML = '{label}" not in content, (
                f"settings.mjs still uses innerHTML for label '{label}'. Use textContent instead."
            )

    def test_joint_demo_thead_uses_dom_not_innerhtml(self):
        """joint-demo.mjs must build the tools table header with DOM methods, not innerHTML.

        Regression test: CodeQL CWE-79 flags all innerHTML assignments. The table header
        used a template literal with only hardcoded content, but the fix uses DOM construction
        which is safer and immune to future variable interpolation accidents.
        """
        path = _JS_SRC_ROOT / "views" / "standard-demo" / "joint-demo.mjs"
        if not path.exists():
            pytest.fail(f"joint-demo.mjs not found at {path}")
        content = path.read_text(encoding="utf-8")
        assert "thead.innerHTML" not in content, (
            "joint-demo.mjs still uses thead.innerHTML. Replace with DOM createElement/textContent/appendChild calls."
        )

    def test_address_space_readandstructure_rejects_on_error(self):
        """address-space.mjs readAndStructure Promise must call reject() on socket error.

        Regression test: the original readAndStructure Promise had no reject parameter —
        if socketHandler.readPromise failed, the Promise would hang forever (never
        resolve or reject), causing dependent code to silently stall.
        """
        path = _JS_SRC_ROOT / "ijt-support" / "address-space" / "address-space.mjs"
        if not path.exists():
            pytest.fail(f"address-space.mjs not found at {path}")
        content = path.read_text(encoding="utf-8")
        # The fix adds 'reject(error)' inside the readAndStructure error handler
        assert "reject(error)" in content, (
            "address-space.mjs readAndStructure does not call reject(error) on socket error. "
            "Add reject parameter to the Promise constructor and call reject(error) in the "
            "error handler to prevent the Promise from hanging forever."
        )


# ===========================================================================
# 5. Implicit string concatenation gate
# ===========================================================================


class TestImplicitStringConcatenation:
    def test_no_implicit_string_concatenation_in_lists(self):
        """No implicit string concat in source Python files (CodeQL py/implicit-string-concatenation)."""
        import io
        import tokenize

        _src_python = _PROJECT_ROOT / "src" / "python"
        issues = []
        for py_file in _src_python.rglob("*.py"):
            src = py_file.read_text(encoding="utf-8")
            try:
                tokens = list(tokenize.generate_tokens(io.StringIO(src).readline))
            except tokenize.TokenError:
                continue
            for i in range(len(tokens) - 1):
                if (
                    tokens[i].type == tokenize.STRING
                    and tokens[i + 1].type == tokenize.STRING
                    and tokens[i].end[0] <= tokens[i + 1].start[0]
                ):
                    issues.append(f"{py_file}:{tokens[i].start[0]}: implicit string concat")
        assert not issues, "Implicit string concatenation found:\n" + "\n".join(issues)
