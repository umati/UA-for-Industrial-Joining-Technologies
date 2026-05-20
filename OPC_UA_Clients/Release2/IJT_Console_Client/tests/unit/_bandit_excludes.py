"""Shared bandit --exclude path list for subprocess-bandit tests.

Centralised so test_security.py and test_static_analysis.py cannot drift
when a new local venv name is introduced (e.g. .venv_ci was missed in CI
mode and caused bandit to scan upstream pytest source code).

Source of truth for IDE/CLI bandit invocations remains pyproject.toml's
tool.bandit.exclude_dirs; this constant covers the additional generic
user-created venv/env patterns that pyproject does not need to enumerate.
"""

BANDIT_EXCLUDES: str = "./tests,./.state,./venv,./venv_test,./.venv,./.venv_test,./.venv_ci,./.venv_wsl,./env,./ENV"
