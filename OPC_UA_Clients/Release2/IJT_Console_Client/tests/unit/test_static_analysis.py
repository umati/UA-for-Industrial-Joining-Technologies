"""
Static-analysis enforcement tests.

Runs pylint, bandit, and AST-based checks that mirror every CodeQL quality
finding type that has ever appeared on the GitHub security/quality page.
All checks scan the full IJT_Console_Client tree (excluding venv / .state /
__pycache__ / node_modules) — the same scope as the codeql-config.yml.
"""

from __future__ import annotations

import ast
import io
import re
import shutil
import subprocess
import sys
import tokenize
from pathlib import Path

import pytest

_CONSOLE_ROOT = Path(__file__).resolve().parent.parent.parent  # = IJT_Console_Client

_SKIP_DIRS = {"venv", ".state", "__pycache__", "node_modules", ".git"}


def _all_py_files(root: Path) -> list[Path]:
    """All .py files in the project, excluding generated/dependency dirs."""
    return [
        f for f in root.rglob("*.py")
        if not any(part in _SKIP_DIRS for part in f.parts)
    ]


_PYLINT_AVAILABLE = shutil.which("pylint") is not None or (
    subprocess.run(
        [sys.executable, "-m", "pylint", "--version"],
        capture_output=True,
    ).returncode == 0
)

_BANDIT_AVAILABLE = subprocess.run(
    [sys.executable, "-m", "bandit", "--version"],
    capture_output=True,
).returncode == 0


def _parse_pylint_score(output: str) -> float | None:
    """Extract the pylint score from 'Your code has been rated at X.XX/10'."""
    match = re.search(r"rated at\s+([\-\d.]+)/10", output)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


# ===========================================================================
# 1. Pylint — minimum score (all project Python files)
# ===========================================================================


@pytest.mark.skipif(not _PYLINT_AVAILABLE, reason="pylint not installed")
def test_pylint_score_above_threshold():
    """pylint must score >= 7.0 across all project Python files."""
    all_files = [str(f) for f in _all_py_files(_CONSOLE_ROOT)]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pylint",
            "--fail-under=7.0",
            "--output-format=text",
            "--score=yes",
        ] + all_files,
        cwd=str(_CONSOLE_ROOT),
        capture_output=True,
        text=True,
    )
    combined = result.stdout + result.stderr
    score = _parse_pylint_score(combined)

    if score is not None:
        assert score >= 7.0, (
            f"pylint score {score:.2f}/10 is below threshold 7.0:\n{result.stdout}"
        )
    else:
        # Couldn't parse score — only fail on fatal/usage errors (exit codes 1, 32)
        assert result.returncode not in (1, 32), (
            f"pylint failed with exit code {result.returncode}:\n"
            f"{result.stdout}\n{result.stderr}"
        )


# ===========================================================================
# 2. Bandit — security scan
# ===========================================================================


@pytest.mark.skipif(not _BANDIT_AVAILABLE, reason="bandit not installed")
def test_bandit_no_high_severity():
    """bandit must find no high-severity issues."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "bandit",
            "-r",
            ".",
            "-ll",
            "--exclude",
            "./tests,./venv,./.state",
        ],
        cwd=str(_CONSOLE_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"bandit found security issues:\n{result.stdout}\n{result.stderr}"
    )


# ===========================================================================
# 3. pylint unused-imports gate (all project Python files)
# ===========================================================================


@pytest.mark.skipif(not _PYLINT_AVAILABLE, reason="pylint not installed")
def test_no_unused_imports_in_source():
    """pylint must find no unused imports (W0611) across all project Python files."""
    all_files = [str(f) for f in _all_py_files(_CONSOLE_ROOT)]
    result = subprocess.run(
        [sys.executable, "-m", "pylint", *all_files,
         "--disable=all", "--enable=W0611", "--score=no", "--output-format=text"],
        capture_output=True, text=True, cwd=str(_CONSOLE_ROOT)
    )
    assert result.returncode == 0, f"Unused imports found:\n{result.stdout}"


# ===========================================================================
# 4. Empty except-block gate (all project Python files)
#    CodeQL: py/empty-except-clause
# ===========================================================================

_BROAD_EXCEPTION_NAMES = {"Exception", "BaseException"}


def _is_broad_except(handler: ast.ExceptHandler) -> bool:
    """Return True for bare except: or except Exception/BaseException:."""
    if handler.type is None:
        return True
    if isinstance(handler.type, ast.Name) and handler.type.id in _BROAD_EXCEPTION_NAMES:
        return True
    return False


def test_no_empty_except_blocks():
    """No empty except blocks in any project Python file (CodeQL py/empty-except)."""
    issues = []
    for py_file in _all_py_files(_CONSOLE_ROOT):
        src = py_file.read_text(encoding="utf-8")
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if (len(node.body) == 1
                        and isinstance(node.body[0], ast.Pass)
                        and _is_broad_except(node)):
                    issues.append(f"{py_file}:{node.lineno}: empty except block")
    assert not issues, "Empty except blocks found:\n" + "\n".join(issues)


# ===========================================================================
# 5. Implicit string concatenation in list literals
#    CodeQL: py/implicit-string-concatenation
# ===========================================================================

_TOKEN_SKIP = {
    tokenize.NEWLINE, tokenize.NL, tokenize.COMMENT,
    tokenize.INDENT, tokenize.DEDENT,
}


def _find_implicit_concat_in_lists(source: str) -> list[int]:
    """Return line numbers with adjacent string literals inside list brackets."""
    found = []
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
    for py_file in _all_py_files(_CONSOLE_ROOT):
        source = py_file.read_text(encoding="utf-8")
        for lineno in _find_implicit_concat_in_lists(source):
            issues.append(f"{py_file}:{lineno}: implicit string concat inside list literal")
    assert not issues, "Implicit string concatenation in lists:\n" + "\n".join(issues)


# ===========================================================================
# 6. Mixed/inconsistent return statements  (CodeQL R1710)
# ===========================================================================

_SKIP_METHOD_NAMES = {
    "__init__", "__del__", "__set__", "__setattr__",
    "__setitem__", "__delitem__", "__enter__", "__exit__",
}


def _is_generator(func_node: ast.FunctionDef) -> bool:
    """Return True if function contains yield or yield from."""
    for node in ast.walk(func_node):
        if isinstance(node, (ast.Yield, ast.YieldFrom)):
            return True
    return False


def _has_abstract_decorator(func_node: ast.FunctionDef) -> bool:
    for dec in func_node.decorator_list:
        if isinstance(dec, ast.Name) and dec.id == "abstractmethod":
            return True
        if isinstance(dec, ast.Attribute) and dec.attr == "abstractmethod":
            return True
    return False


def _collect_returns_at_scope(func_node: ast.FunctionDef) -> list[ast.Return]:
    """Collect Return nodes only at this function's direct scope (not nested)."""
    returns: list[ast.Return] = []

    def _walk(node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if isinstance(child, ast.Return):
                returns.append(child)
            _walk(child)

    for stmt in func_node.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue  # top-level nested scope — skip entirely
        _walk(stmt)
    return returns


def _function_can_fall_through(func_node: ast.FunctionDef) -> bool:
    """Heuristic: True if function body's last statement is not a definitive exit."""
    body = func_node.body
    if not body:
        return True
    last = body[-1]
    # Return/Raise are explicit exits; Try blocks that cover both
    # success and error paths also definitively return in practice.
    return not isinstance(last, (ast.Return, ast.Raise, ast.Try))


def _has_mixed_returns(func_node: ast.FunctionDef) -> bool:
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
        return False

    if returns_without_value:
        return True

    if _function_can_fall_through(func_node):
        return True

    return False


def test_no_mixed_return_statements():
    """No functions with inconsistent return values (CodeQL R1710)."""
    issues = []
    for py_file in _all_py_files(_CONSOLE_ROOT):
        source = py_file.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if _has_mixed_returns(node):
                    issues.append(
                        f"{py_file}:{node.lineno}: {node.name}() — mixed return statements"
                    )
    assert not issues, "Mixed return statements found:\n" + "\n".join(issues)


# ===========================================================================
# 7. Duplicate imports  (CodeQL py/duplicate-import)
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
    for py_file in _all_py_files(_CONSOLE_ROOT):
        source = py_file.read_text(encoding="utf-8")
        dups = _find_duplicate_imports(source)
        for dup in dups:
            issues.append(f"{py_file}: duplicate import of '{dup}'")
    assert not issues, "Duplicate imports found:\n" + "\n".join(issues)


# ===========================================================================
# 8. Unused global declarations  (CodeQL-style)
# ===========================================================================


def _find_unused_global_decls(func_node: ast.FunctionDef) -> list[str]:
    """Return global names declared but never read or written in the function."""
    declared: set[str] = set()
    for node in ast.walk(func_node):
        if isinstance(node, ast.Global):
            declared.update(node.names)

    used: set[str] = set()
    for node in ast.walk(func_node):
        if isinstance(node, ast.Name):
            used.add(node.id)

    return list(declared - used)


def test_no_unused_global_declarations():
    """No 'global x' inside a function where x is never referenced."""
    issues = []
    for py_file in _all_py_files(_CONSOLE_ROOT):
        source = py_file.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for name in _find_unused_global_decls(node):
                    issues.append(
                        f"{py_file}:{node.lineno}: "
                        f"'{name}' declared global but never used in {node.name}()"
                    )
    assert not issues, "Unused global declarations:\n" + "\n".join(issues)


# ===========================================================================
# 9. Variable defined multiple times without intervening use
#    CodeQL: py/multiple-definition
# ===========================================================================


def _find_multiple_defs(func_node: ast.FunctionDef) -> list[tuple[str, int]]:
    """Find names assigned twice at function top scope without an intervening read."""
    issues: list[tuple[str, int]] = []
    last_assign: dict[str, int] = {}

    for stmt in func_node.body:
        if isinstance(stmt, ast.Assign):
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
            if isinstance(stmt.target, ast.Name):
                last_assign.pop(stmt.target.id, None)

        else:
            for node in ast.walk(stmt):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    last_assign.pop(node.id, None)

    return issues


def test_no_multiple_definitions():
    """No variable assigned twice without intervening use (CodeQL py/multiple-definition)."""
    issues = []
    for py_file in _all_py_files(_CONSOLE_ROOT):
        source = py_file.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for name, lineno in _find_multiple_defs(node):
                    issues.append(
                        f"{py_file}:{lineno}: "
                        f"'{name}' assigned again without use in {node.name}()"
                    )
    assert not issues, "Multiple definitions found:\n" + "\n".join(issues)


# ===========================================================================
# 10. Unused pytest.importorskip assignments
#     Catches: X = pytest.importorskip(...) where X is never used as X.something
# ===========================================================================


def _find_unused_importorskip_assignments(source: str) -> list[str]:
    """Return variable names assigned from pytest.importorskip but never accessed as X.attr.

    Excludes '_' which is the Python discard convention for intentionally unused values.
    """
    assignments = re.findall(r"^(\w+)\s*=\s*pytest\.importorskip\(", source, re.MULTILINE)
    return [
        name for name in assignments
        if name != "_" and not re.search(r"\b" + re.escape(name) + r"\.", source)
    ]


def test_no_unused_importorskip_assignments():
    """No X = pytest.importorskip(...) where X is never used as X.something.

    Use '_ = pytest.importorskip(...)' as the discard-pattern when the module
    object is not needed after the skip guard.
    Unused named assignments are dead code (CodeQL py/unused-local-variable).
    """
    issues = []
    for py_file in _all_py_files(_CONSOLE_ROOT):
        source = py_file.read_text(encoding="utf-8")
        for name in _find_unused_importorskip_assignments(source):
            issues.append(
                f"{py_file}: '{name} = pytest.importorskip(...)'"
                f" — '{name}' never used as attribute access"
            )
    assert not issues, "Unused importorskip assignments:\n" + "\n".join(issues)


# ===========================================================================
# 11. Unused local variables  (pylint W0612)
# ===========================================================================


@pytest.mark.skipif(not _PYLINT_AVAILABLE, reason="pylint not installed")
def test_no_unused_local_variables():
    """pylint must find no unused local variables (W0612) across all project Python files."""
    all_files = [str(f) for f in _all_py_files(_CONSOLE_ROOT)]
    result = subprocess.run(
        [sys.executable, "-m", "pylint", *all_files,
         "--disable=all", "--enable=W0612", "--score=no", "--output-format=text"],
        capture_output=True, text=True, cwd=str(_CONSOLE_ROOT)
    )
    assert result.returncode == 0, f"Unused local variables found:\n{result.stdout}"


# ===========================================================================
# Regression tests — guard against previously fixed issues
# ===========================================================================


_BROAD_EXCEPTION_FILES = [
    ("serialize_data.py", "except ImportError"),
    ("utils.py", "except ImportError"),
    ("method_caller.py", "except (ValueError, TypeError)"),
]


@pytest.mark.parametrize("filename,expected_except", _BROAD_EXCEPTION_FILES)
def test_import_exception_specificity(filename, expected_except):
    """Source files must use specific exception types, not bare 'except Exception'.

    Regression tests for M-4 and M-5: broad except Exception was masking real
    errors during orjson import and method return status parsing.
    """
    path = _CONSOLE_ROOT / filename
    if not path.exists():
        pytest.skip(f"{filename} does not exist")
    content = path.read_text(encoding="utf-8")
    assert expected_except in content, (
        f"{filename}: expected '{expected_except}' but not found. "
        f"Using 'except Exception' is too broad — use a specific exception type."
    )


def test_setup_client_version_check_uses_sys_exit_not_assert():
    """setup_client.py must use sys.exit() for the asyncua version check, not assert.

    Regression test for M-3: assert is stripped by Python -O optimized mode.
    """
    path = _CONSOLE_ROOT / "setup_client.py"
    if not path.exists():
        pytest.skip("setup_client.py does not exist")
    content = path.read_text(encoding="utf-8")
    assert "assert Version(asyncua.__version__)" not in content, (
        "setup_client.py uses 'assert' for asyncua version check — "
        "assert is stripped by 'python -O'. Use sys.exit() instead."
    )


def test_format_local_time_uses_valueerror_not_broad_exception():
    """utils.py format_local_time() must catch ValueError, not bare Exception.

    Regression test: datetime.fromisoformat() raises ValueError for malformed
    input — catching bare Exception is too broad and hides unrelated bugs.
    """
    path = _CONSOLE_ROOT / "utils.py"
    if not path.exists():
        pytest.skip("utils.py does not exist")
    content = path.read_text(encoding="utf-8")
    assert "except ValueError:" in content, (
        "utils.py does not use 'except ValueError:'. "
        "format_local_time() should catch ValueError (from fromisoformat) "
        "rather than bare except Exception."
    )
