"""Verify IJT_Web_Client has no cross-client dependencies."""
import ast
import pathlib

SRC = pathlib.Path(__file__).parent.parent.parent / "src" / "python"
FORBIDDEN = ["shared_python", "IJT_Console_Client", "Console_Client"]


def test_no_cross_client_imports():
    for py_file in SRC.rglob("*.py"):
        source = py_file.read_text(encoding="utf-8")
        for forbidden in FORBIDDEN:
            assert forbidden not in source, (
                f"{py_file.name} imports from {forbidden} — clients must be self-contained"
            )
