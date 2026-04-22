"""Unit tests for scripts/normalize_multi_except.py.

These tests serve as a regression gate for the ruff 0.15.x formatter bug that
strips parentheses from 'except (A, B):' clauses, rewriting them to the
Python-2-only 'except A, B:' form (a logic bug in Python 3).

NOTE: test_ruff_format_bug_still_present_guard below is an INTENTIONAL SENTINEL.
It currently PASSES because the bug is present. When a future ruff version fixes
the stripping behaviour, that test will FAIL with a clear removal message — that
failure is the signal to delete scripts/normalize_multi_except.py, the pre-commit
hooks, the Phase 1 runner steps, and this test file in a single PR.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

# Repo root → scripts/normalize_multi_except.py
_SCRIPT = Path(__file__).parents[5] / "scripts" / "normalize_multi_except.py"
# Always use the ruff from the same venv as the running Python
_RUFF_EXE = str(Path(sys.executable).parent / ("ruff.exe" if sys.platform == "win32" else "ruff"))


# ── helpers ──────────────────────────────────────────────────────────────────


def _run_script(*args: str) -> tuple[int, str]:
    """Run the normalize script and return (returncode, combined output)."""
    cmd = [sys.executable, str(_SCRIPT), *args]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return result.returncode, result.stdout + result.stderr


# ── script existence ──────────────────────────────────────────────────────────


def test_script_exists() -> None:
    assert _SCRIPT.exists(), f"normalize_multi_except.py not found at {_SCRIPT}"


# ── _fix_text logic (import the module directly) ──────────────────────────────


def test_fix_text_rewrites_bare_comma_form() -> None:
    """Core regex: 'except A, B:' → 'except (A, B):'."""
    sys.path.insert(0, str(_SCRIPT.parent))
    try:
        import importlib
        mod = importlib.import_module("normalize_multi_except")
        fixed, count = mod._fix_text("    except TypeError, ValueError:\n        pass\n")
        assert count == 1
        assert "except (TypeError, ValueError):" in fixed
    finally:
        sys.path.pop(0)


def test_fix_text_leaves_parenthesised_form_unchanged() -> None:
    """Already-correct syntax must not be touched."""
    sys.path.insert(0, str(_SCRIPT.parent))
    try:
        import importlib
        mod = importlib.import_module("normalize_multi_except")
        src = "    except (TypeError, ValueError):\n        pass\n"
        fixed, count = mod._fix_text(src)
        assert count == 0
        assert fixed == src
    finally:
        sys.path.pop(0)


# ── CLI --check mode ──────────────────────────────────────────────────────────


def test_check_mode_fails_on_bare_comma() -> None:
    """--check must exit 1 when unparenthesised multi-except is present."""
    with tempfile.TemporaryDirectory() as tmp:
        bad = Path(tmp) / "bad.py"
        bad.write_text("try:\n    pass\nexcept TypeError, ValueError:\n    pass\n", encoding="utf-8")
        rc, _ = _run_script("--check", str(bad))
    assert rc == 1, "Expected exit 1 for forbidden syntax"


def test_check_mode_passes_on_correct_syntax() -> None:
    """--check must exit 0 when syntax is already parenthesised."""
    with tempfile.TemporaryDirectory() as tmp:
        good = Path(tmp) / "good.py"
        good.write_text("try:\n    pass\nexcept (TypeError, ValueError):\n    pass\n", encoding="utf-8")
        rc, _ = _run_script("--check", str(good))
    assert rc == 0, "Expected exit 0 for correct syntax"


# ── CLI --write mode ──────────────────────────────────────────────────────────


def test_write_mode_fixes_file_in_place() -> None:
    """--write must rewrite the file and exit 0."""
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "fixme.py"
        f.write_text("try:\n    pass\nexcept KeyError, IndexError:\n    pass\n", encoding="utf-8")
        rc, _ = _run_script("--write", str(f))
        content = f.read_text(encoding="utf-8")
    assert rc == 0
    assert "except (KeyError, IndexError):" in content
    assert "except KeyError, IndexError:" not in content


# ── ruff format regression gate ───────────────────────────────────────────────


def test_ruff_format_bug_still_present_guard() -> None:
    """Sentinel: asserts the ruff 0.15.x formatter bug is still present.

    This test PASSES while the bug exists and FAILS when ruff fixes it.
    A failure here is the decommission signal — remove in the same PR:
      - scripts/normalize_multi_except.py
      - .pre-commit-config.yaml normalize-multi-except + except-syntax-gate hooks
      - Phase 1 _step_normalize_multi_except() + _step_verify_multi_except() in all runners
      - This test file
    """
    src = textwrap.dedent("""\
        def f():
            try:
                pass
            except (TypeError, ValueError):
                pass
            except (KeyError, IndexError):
                pass
    """)
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "ruff_test.py"
        f.write_text(src, encoding="utf-8")

        # Pass the project pyproject.toml explicitly — the bug is triggered by
        # target-version = "py314" in pyproject.toml. Ruff picks up this config
        # when run from inside the project; we pass it explicitly for portability.
        _PYPROJECT = Path(__file__).parents[2] / "pyproject.toml"
        diff_result = subprocess.run(
            [_RUFF_EXE, "format", "--diff", "--config", str(_PYPROJECT), str(f)],
            capture_output=True, text=True, check=False,
        )
    bug_present = "except TypeError, ValueError" in diff_result.stdout or "except KeyError, IndexError" in diff_result.stdout
    assert bug_present, (
        "ruff format no longer strips except parens with target-version=py314 — "
        "the normalize workaround can now be removed! Delete: scripts/normalize_multi_except.py, "
        "the pre-commit hooks, Phase 1 runner steps, and this test."
    )
