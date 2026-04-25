"""Static-analysis enforcement tests.

These tests run external analysis tools as CI gates.  If a tool is not
installed the test is skipped rather than failing (useful for minimal
environments).  They are designed to fail if someone introduces code that
violates lint or security policies, matching the same scope as CodeQL.
"""

from __future__ import annotations

import ast
import io
import platform
import re
import shutil
import subprocess
import sys
import tokenize
from pathlib import Path

import pytest

# Resolve project root relative to this file so tests work from any cwd.
_PROJECT_ROOT = Path(__file__).resolve().parents[3]  # = IJT_Web_Client root
_SRC_PYTHON = _PROJECT_ROOT / "src" / "python"

_SKIP_DIRS = {"__pycache__", "node_modules", ".git", ".state"}


def _all_py_files(root: Path) -> list[Path]:
    """All .py files in the project, excluding generated/dependency dirs."""

    def _skip(part: str) -> bool:
        return part in _SKIP_DIRS or part.startswith(".venv") or part.startswith("venv")

    return [f for f in root.rglob("*.py") if not any(_skip(part) for part in f.parts)]


def _tool_available(name: str) -> bool:
    """Return True only if the tool is available via the current venv Python."""
    return (
        subprocess.run(
            [sys.executable, "-m", name, "--version"],
            capture_output=True,
        ).returncode
        == 0
    )


def _npm_available() -> bool:
    return shutil.which("npm") is not None


def _is_wsl() -> bool:
    """Detect WSL: Linux kernel but accessing a Windows NTFS filesystem."""
    release = platform.release().lower()
    return "microsoft" in release or "wsl" in release


def _eslint_executable() -> bool:
    """Return True only if eslint is installed and runnable."""
    if not _npm_available():
        return False
    if _is_wsl():
        return False
    eslint_bin = _PROJECT_ROOT / "node_modules" / ".bin" / "eslint"
    return eslint_bin.exists()


# ===========================================================================
# 1. Bandit — Python security scanner
# ===========================================================================


@pytest.mark.skipif(
    not _tool_available("bandit"),
    reason="bandit not installed — skipping security scan",
)
def test_bandit_no_high_severity_issues():
    """bandit must find no HIGH or MEDIUM severity issues in src/python/."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "bandit",
            "-r",
            str(_SRC_PYTHON),
            "-ll",  # only MEDIUM and above
            "--exit-zero",  # don't fail on LOW — only care about return value
            "-f",
            "txt",
        ],
        capture_output=True,
        text=True,
        cwd=str(_PROJECT_ROOT),
    )
    assert result.returncode == 0, (
        f"bandit found HIGH/MEDIUM issues.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )


# ===========================================================================
# 2. ESLint — JavaScript source quality gate
# ===========================================================================


@pytest.mark.skipif(
    not _eslint_executable(),
    reason="eslint binary not executable in this environment — skipping JS lint gate",
)
def test_eslint_passes():
    """npm run lint must exit 0 (no ESLint errors in src/javascripts/)."""
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    result = subprocess.run(
        [npm_cmd, "run", "lint"],
        capture_output=True,
        text=True,
        cwd=str(_PROJECT_ROOT),
    )
    assert result.returncode == 0, (
        f"ESLint failed (exit {result.returncode}).\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )


# ===========================================================================
# 3. Empty except-block gate (all project Python files)
# ===========================================================================

_BROAD_EXCEPTION_NAMES = {"Exception", "BaseException"}


def _is_broad_except(handler: ast.ExceptHandler) -> bool:
    """Return True for bare except: or except Exception/BaseException:."""
    if handler.type is None:
        return True  # bare except:
    if isinstance(handler.type, ast.Name) and handler.type.id in _BROAD_EXCEPTION_NAMES:
        return True  # except Exception: or except BaseException:
    return False


def test_no_empty_except_blocks():
    """No empty except blocks in any project Python file (CodeQL py/empty-except).

    Catches two patterns:
    - bare ``except: pass``  (node.type is None)
    - broad ``except Exception: pass`` with no logging or re-raise
    Both are flagged by CodeQL as py/empty-except-clause.
    """
    issues = []
    for py_file in _all_py_files(_PROJECT_ROOT):
        src = py_file.read_text(encoding="utf-8")
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if len(node.body) == 1 and isinstance(node.body[0], ast.Pass) and _is_broad_except(node):
                    issues.append(f"{py_file}:{node.lineno}: empty except block")
    assert not issues, "Empty except blocks found:\n" + "\n".join(issues)


# ===========================================================================
# 4. Implicit string concatenation in list literals
#    CodeQL: py/implicit-string-concatenation
# ===========================================================================

_TOKEN_SKIP = {
    tokenize.NEWLINE,
    tokenize.NL,
    tokenize.COMMENT,
    tokenize.INDENT,
    tokenize.DEDENT,
}


def _find_implicit_concat_in_lists(source: str) -> list[int]:
    """Return line numbers with adjacent string literals inside list brackets."""
    found: list[int] = []
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except tokenize.TokenError:
        return found

    bracket_depth = 0
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.type == tokenize.OP:
            if tok.string == "[":
                bracket_depth += 1
            elif tok.string == "]":
                bracket_depth -= 1
        elif tok.type == tokenize.STRING and bracket_depth > 0:
            # Look ahead past whitespace/comments for another STRING token.
            j = i + 1
            while j < len(tokens) and tokens[j].type in _TOKEN_SKIP:
                j += 1
            if j < len(tokens) and tokens[j].type == tokenize.STRING:
                found.append(tok.start[0])
        i += 1
    return found


def test_no_implicit_string_concat_in_lists():
    """No adjacent string literals inside list brackets (CodeQL py/implicit-string-concatenation)."""
    issues = []
    for py_file in _all_py_files(_PROJECT_ROOT):
        source = py_file.read_text(encoding="utf-8")
        for lineno in _find_implicit_concat_in_lists(source):
            issues.append(f"{py_file}:{lineno}: implicit string concat inside list literal")
    assert not issues, "Implicit string concatenation in lists:\n" + "\n".join(issues)


# ===========================================================================
# 5. Mixed/inconsistent return statements  (CodeQL R1710)
# ===========================================================================

_SKIP_METHOD_NAMES = {
    "__init__",
    "__del__",
    "__set__",
    "__setattr__",
    "__setitem__",
    "__delitem__",
    "__enter__",
    "__exit__",
}


def _is_generator(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return True if function contains yield or yield from."""
    for node in ast.walk(func_node):
        if isinstance(node, (ast.Yield, ast.YieldFrom)):
            return True
    return False


def _has_abstract_decorator(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for dec in func_node.decorator_list:
        if isinstance(dec, ast.Name) and dec.id == "abstractmethod":
            return True
        if isinstance(dec, ast.Attribute) and dec.attr == "abstractmethod":
            return True
    return False


def _collect_returns_at_scope(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.Return]:
    """Collect Return nodes only at this function's direct scope (not nested)."""
    returns: list[ast.Return] = []

    def _walk(node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue  # don't descend into nested scopes
            if isinstance(child, ast.Return):
                returns.append(child)
            _walk(child)

    for stmt in func_node.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue  # top-level nested scope — skip entirely
        _walk(stmt)
    return returns


def _function_can_fall_through(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Heuristic: True if function body's last statement is not a definitive exit."""
    body = func_node.body
    if not body:
        return True
    last = body[-1]
    # Return/Raise are explicit exits; Try blocks that cover both
    # success and error paths also definitively return in practice.
    return not isinstance(last, (ast.Return, ast.Raise, ast.Try))


def _has_mixed_returns(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """True if function mixes return-with-value and implicit/explicit None return."""
    if func_node.name in _SKIP_METHOD_NAMES:
        return False
    if _is_generator(func_node):
        return False
    if _has_abstract_decorator(func_node):
        return False

    returns = _collect_returns_at_scope(func_node)
    returns_with_value = [r for r in returns if r.value is not None]
    returns_without_value = [r for r in returns if r.value is None]

    if not returns_with_value:
        return False  # no valued returns — consistent

    if returns_without_value:
        return True  # explicit bare return alongside a valued return

    if _function_can_fall_through(func_node):
        return True  # implicit None fall-through alongside valued returns

    return False


def test_no_mixed_return_statements():
    """No functions with inconsistent return values (CodeQL R1710)."""
    issues = []
    for py_file in _all_py_files(_PROJECT_ROOT):
        source = py_file.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if _has_mixed_returns(node):
                    issues.append(f"{py_file}:{node.lineno}: {node.name}() — mixed return statements")
    assert not issues, "Mixed return statements found:\n" + "\n".join(issues)


# ===========================================================================
# 6. Duplicate imports  (CodeQL py/duplicate-import)
# ===========================================================================


def _find_duplicate_imports(source: str) -> list[str]:
    """Find modules imported with both 'import X' and 'from X import ...'

    Uses exact module name matching so that submodule imports
    (e.g. ``import asyncua.client.ua_client``) do not collide with
    top-level ``from asyncua import ...`` imports.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    plain_imports: set[str] = set()
    from_imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                plain_imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            from_imports.add(node.module)
    return list(plain_imports & from_imports)


def test_no_duplicate_imports():
    """No module imported with both 'import X' and 'from X import Y' (CodeQL py/duplicate-import)."""
    issues = []
    for py_file in _all_py_files(_PROJECT_ROOT):
        source = py_file.read_text(encoding="utf-8")
        dups = _find_duplicate_imports(source)
        for dup in dups:
            issues.append(f"{py_file}: duplicate import of '{dup}'")
    assert not issues, "Duplicate imports found:\n" + "\n".join(issues)


# ===========================================================================
# 7. Unused global declarations  (CodeQL py/unused-global-variable)
# ===========================================================================

_KNOWN_UNUSED_GLOBAL_EXCEPTIONS = {
    # pytest reads pytestmark implicitly via __dict__ — CodeQL can't see it.
    "pytestmark",
}


def _collect_all_imported_names(root: Path) -> set[str]:
    """Return every name that is imported via 'from X import Y' in any .py file under root.

    Used to exclude cross-file exports from the unused-globals check:
    a module-level name that another file imports is not 'unused' even if it
    is never referenced in its own file.
    """
    imported: set[str] = set()
    for py_file in _all_py_files(root):
        try:
            src = py_file.read_text(encoding="utf-8")
            tree = ast.parse(src)
        except (SyntaxError, OSError):  # fmt: skip
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imported.add(alias.asname or alias.name)
    return imported


def _find_unused_global_decls(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Return global names declared inside a function but never read or written there."""
    declared: set[str] = set()
    for node in ast.walk(func_node):
        if isinstance(node, ast.Global):
            declared.update(node.names)

    used: set[str] = set()
    for node in ast.walk(func_node):
        if isinstance(node, ast.Name):
            used.add(node.id)

    return list(declared - used)


def _find_unused_module_globals(
    source: str,
    tree: ast.Module,
    cross_file_exports: set[str],
) -> list[tuple[int, str]]:
    """Return (lineno, name) for module-level names assigned but never read.

    Excludes:
    - Dunder names (protocol slots, re-exports)
    - Names in _KNOWN_UNUSED_GLOBAL_EXCEPTIONS (framework magic like pytestmark)
    - Names imported by other files in the project (cross-file exports)
    """
    assigned: dict[str, int] = {}
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if (
                    isinstance(target, ast.Name)
                    and not target.id.startswith("__")
                    and target.id != "_"
                    and target.id not in _KNOWN_UNUSED_GLOBAL_EXCEPTIONS
                    and target.id not in cross_file_exports
                ):
                    assigned[target.id] = stmt.lineno

    reads: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            reads.add(node.id)

    return [(lineno, name) for name, lineno in assigned.items() if name not in reads]


def test_no_unused_global_declarations():
    """No 'global x' inside a function where x is never referenced,
    AND no module-level assignment where the name is never read (anywhere in project)."""
    cross_file_exports = _collect_all_imported_names(_PROJECT_ROOT)
    issues = []
    for py_file in _all_py_files(_PROJECT_ROOT):
        source = py_file.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        # Check 'global x' declarations inside functions
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for name in _find_unused_global_decls(node):
                    issues.append(f"{py_file}:{node.lineno}: '{name}' declared global but never used in {node.name}()")
        # Check module-level assignments that are never read (CodeQL py/unused-global-variable)
        for lineno, name in _find_unused_module_globals(source, tree, cross_file_exports):
            issues.append(f"{py_file}:{lineno}: module-level '{name}' assigned but never read")
    assert not issues, "Unused global declarations:\n" + "\n".join(issues)


# ===========================================================================
# 8. Variable defined multiple times without intervening use
#     CodeQL: py/multiple-definition
# ===========================================================================


def _find_multiple_defs(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[tuple[str, int]]:
    """Find names assigned twice at function top scope without an intervening read."""
    issues: list[tuple[str, int]] = []
    # Maps name -> line of its last unread assignment at this scope level.
    last_assign: dict[str, int] = {}

    for stmt in func_node.body:
        if isinstance(stmt, ast.Assign):
            # Process the RHS for reads before recording the LHS assignment.
            for node in ast.walk(stmt.value):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    last_assign.pop(node.id, None)
            for target in stmt.targets:
                if isinstance(target, ast.Name):
                    if target.id in last_assign:
                        issues.append((target.id, last_assign[target.id]))
                    last_assign[target.id] = stmt.lineno

        elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
            for node in ast.walk(stmt.value):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    last_assign.pop(node.id, None)
            if isinstance(stmt.target, ast.Name):
                name = stmt.target.id
                if name in last_assign:
                    issues.append((name, last_assign[name]))
                last_assign[name] = stmt.lineno

        elif isinstance(stmt, ast.AugAssign):
            # AugAssign reads before writing — clears any "dead" status.
            if isinstance(stmt.target, ast.Name):
                last_assign.pop(stmt.target.id, None)

        else:
            # Any other statement (if/for/return/etc.) — scan for reads.
            for node in ast.walk(stmt):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    last_assign.pop(node.id, None)

    return issues


def test_no_multiple_definitions():
    """No variable assigned twice without intervening use (CodeQL py/multiple-definition)."""
    issues = []
    for py_file in _all_py_files(_PROJECT_ROOT):
        source = py_file.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for name, lineno in _find_multiple_defs(node):
                    issues.append(f"{py_file}:{lineno}: '{name}' assigned again without use in {node.name}()")
    assert not issues, "Multiple definitions found:\n" + "\n".join(issues)


# ===========================================================================
# 9. Unused pytest.importorskip assignments
#     Catches: X = pytest.importorskip(...) where X is never used as X.something
# ===========================================================================


def _find_unused_importorskip_assignments(source: str) -> list[str]:
    """Return variable names assigned from pytest.importorskip but never accessed as X.attr.

    Excludes '_' which is the Python discard convention for intentionally unused values.
    """
    assignments = re.findall(r"^(\w+)\s*=\s*pytest\.importorskip\(", source, re.MULTILINE)
    return [name for name in assignments if name != "_" and not re.search(r"\b" + re.escape(name) + r"\.", source)]


def test_no_unused_importorskip_assignments():
    """No X = pytest.importorskip(...) where X is never used as X.something.

    Use '_ = pytest.importorskip(...)' as the discard-pattern when the module
    object is not needed after the skip guard.
    Unused named assignments are dead code (CodeQL py/unused-local-variable).
    """
    issues = []
    for py_file in _all_py_files(_PROJECT_ROOT):
        source = py_file.read_text(encoding="utf-8")
        for name in _find_unused_importorskip_assignments(source):
            issues.append(f"{py_file}: '{name} = pytest.importorskip(...)' — '{name}' never used as attribute access")
    assert not issues, "Unused importorskip assignments:\n" + "\n".join(issues)


# ===========================================================================
# Regression tests — guard against previously fixed issues
# ===========================================================================


def test_setup_project_version_check_uses_sysexit_not_assert():
    """setup_project.py must not use 'assert' for the asyncua version check.

    Regression test: assert is stripped by 'python -O', making the guard
    ineffective.  The fix uses raise SystemExit(...) instead.
    """
    path = _PROJECT_ROOT / "setup_project.py"
    if not path.exists():
        pytest.fail("setup_project.py does not exist")
    content = path.read_text(encoding="utf-8")
    assert "assert Version(asyncua.__version__)" not in content, (
        "setup_project.py uses 'assert' for asyncua version check — "
        "assert is stripped by 'python -O'. Use raise SystemExit() instead."
    )
