"""Verify IJT_Console_Client has no cross-client dependencies."""
import pathlib

# Only scan production source files, not the tests directory itself
# (test files may reference forbidden strings as list constants, docstrings, etc.)
SRC = pathlib.Path(__file__).parent.parent.parent
TESTS_DIR = pathlib.Path(__file__).parent.parent
FORBIDDEN = ["shared_python", "IJT_Web_Client", "Web_Client"]

SKIP_DIRS = {"venv", "__pycache__", ".venv", "node_modules", "result_logs", "logs"}


def _source_files():
    for py_file in SRC.rglob("*.py"):
        # Skip non-source directories
        if any(part in SKIP_DIRS for part in py_file.parts):
            continue
        # Skip the tests directory — test support files may legitimately mention
        # other client names in fixture strings, skip lists, or docstrings.
        if py_file.is_relative_to(TESTS_DIR):
            continue
        yield py_file


def test_no_cross_client_imports():
    for py_file in _source_files():
        source = py_file.read_text(encoding="utf-8")
        for forbidden in FORBIDDEN:
            assert forbidden not in source, (
                f"{py_file.name} references {forbidden} — clients must be self-contained"
            )
