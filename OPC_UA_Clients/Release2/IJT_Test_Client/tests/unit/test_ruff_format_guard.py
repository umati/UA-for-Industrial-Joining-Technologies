"""
test_ruff_format_guard.py — Regression guard for ruff formatter bug #24041.

Ruff 0.15.x with target-version = "py314" silently rewrites:
    except (TypeError, ValueError):      # correct Python 3 — catches both types
to:
    except TypeError, ValueError:        # Python 2 syntax — catches only TypeError,
                                         # binds ValueError as a name (wrong!)

This test verifies that ruff format leaves except (A, B): clauses untouched.
It acts as a canary for two distinct regressions:
  1. target-version accidentally bumped back to "py314" while ruff bug is unfixed.
  2. ruff upgraded to a version that reintroduces the bug.

When ruff upstream fixes #24041 and we restore target-version = "py314":
  - This test continues to PASS (parens preserved by the fixed formatter).
  - At that point the test becomes a general regression guard — keep it forever.

References:
  https://github.com/astral-sh/ruff/issues/24041
"""

import subprocess
import sys
import textwrap

import pytest


def _ruff_available() -> bool:
    try:
        r = subprocess.run(
            [sys.executable, "-m", "ruff", "--version"],
            capture_output=True,
            timeout=10,
        )
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


_SNIPPET = textwrap.dedent("""\
    def handler():
        try:
            pass
        except (TypeError, ValueError):
            pass
        try:
            pass
        except (KeyError, AttributeError, RuntimeError):
            pass
""")


@pytest.mark.skipif(not _ruff_available(), reason="ruff not installed")
def test_ruff_format_preserves_multi_except_parens():
    """ruff format must not strip parentheses from except (A, B): clauses."""
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "format", "--stdin-filename", "test.py", "-"],
        input=_SNIPPET,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"ruff format failed unexpectedly:\n{result.stderr}"

    formatted = result.stdout
    assert "except (TypeError, ValueError):" in formatted, (
        "ruff format CORRUPTED a two-type except clause!\n"
        "Expected:  except (TypeError, ValueError):\n"
        f"Got output:\n{formatted}\n"
        "Root cause: target-version = 'py314' is set while ruff bug #24041 is unfixed.\n"
        "Fix: ensure target-version = 'py313' in [tool.ruff] across all pyproject.toml files."
    )
    assert "except (KeyError, AttributeError, RuntimeError):" in formatted, (
        f"ruff format CORRUPTED a three-type except clause!\nGot output:\n{formatted}\nSee ruff issue #24041."
    )
    assert "except TypeError, ValueError:" not in formatted, (
        "ruff format produced bare Python-2 except syntax — bug #24041 regression detected."
    )
    assert "except KeyError, AttributeError, RuntimeError:" not in formatted, (
        "ruff format produced bare Python-2 except syntax — bug #24041 regression detected."
    )
