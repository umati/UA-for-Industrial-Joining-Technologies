"""
Import path tests.

- All Python source files use snake_case module names
- No imports from shared_python, IJT_Web_Client, or sibling client directories
- All imports are resolvable from the Console Client root
"""

import ast
import re
from pathlib import Path

import pytest

_CONSOLE_ROOT = Path(__file__).resolve().parent.parent.parent

_SOURCE_FILES = [
    f
    for f in _CONSOLE_ROOT.glob("*.py")
    if f.name not in ("setup_client.py",)  # setup_client uses stdlib only
    and not f.name.startswith("_")
]


# ---------------------------------------------------------------------------
# Snake-case module names
# ---------------------------------------------------------------------------


def test_all_source_files_are_snake_case():
    """All .py files must have snake_case names (no CamelCase)."""
    for f in _CONSOLE_ROOT.glob("*.py"):
        name = f.stem  # filename without .py
        assert name == name.lower(), f"{f.name} is not snake_case — Python modules must be lowercase"


# ---------------------------------------------------------------------------
# No cross-client imports
# ---------------------------------------------------------------------------

_FORBIDDEN_IMPORT_PATTERNS = [
    re.compile(r"from\s+shared_python"),
    re.compile(r"import\s+shared_python"),
    re.compile(r"from\s+IJT_Web_Client"),
    re.compile(r"import\s+IJT_Web_Client"),
    re.compile(r"IJT_Web_Client"),
]


@pytest.mark.parametrize("source_file", [f.name for f in _SOURCE_FILES])
def test_no_cross_client_imports_in_source(source_file):
    """Source files must not import from IJT_Web_Client or shared_python."""
    path = _CONSOLE_ROOT / source_file
    content = path.read_text(encoding="utf-8")
    for pattern in _FORBIDDEN_IMPORT_PATTERNS:
        assert not pattern.search(content), f"{source_file} imports from forbidden module: {pattern.pattern}"


# ---------------------------------------------------------------------------
# All imports are resolvable
# ---------------------------------------------------------------------------

_STDLIB_AND_THIRD_PARTY = {
    "asyncio",
    "os",
    "sys",
    "logging",
    "traceback",
    "socket",
    "time",
    "re",
    "json",
    "inspect",
    "pathlib",
    "datetime",
    "typing",
    "dataclasses",
    "asyncua",
    "pytz",
    "aiofiles",
    "orjson",
    "cryptography",
    "OpenSSL",
    "packaging",
    "argparse",
    "shlex",
    "shutil",
    "subprocess",
    "zipfile",
    "urllib",
    "contextlib",
    "asyncua.ua",
    "asyncua.ua.uaerrors",
}


def _get_top_level_imports(source_file: Path) -> list:
    """Parse AST and return all top-level imported module names."""
    try:
        tree = ast.parse(source_file.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module.split(".")[0])
    return imports


_LOCAL_MODULES = {
    "opcua_client",
    "event_handler",
    "result_event_handler",
    "serialize_data",
    "utils",
    "ijt_logger",
    "method_caller",
    "client_config",
    "main",
    "event_types",
    "setup_client",
}


@pytest.mark.parametrize("source_file", [f.name for f in _SOURCE_FILES])
def test_local_imports_exist_as_files(source_file):
    """Local module imports (not stdlib/3rd party) must resolve to actual files."""
    path = _CONSOLE_ROOT / source_file
    imports = _get_top_level_imports(path)
    for mod in imports:
        if mod in _STDLIB_AND_THIRD_PARTY:
            continue
        if mod in _LOCAL_MODULES:
            assert (_CONSOLE_ROOT / f"{mod}.py").exists(), f"{source_file} imports {mod!r} but {mod}.py does not exist"
