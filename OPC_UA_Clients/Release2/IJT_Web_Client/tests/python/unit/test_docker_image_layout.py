"""Image-layout contract for the shared repo-root ``scripts/`` helpers.

Runs in BOTH places with no skips:

* host (full clone): verifies the repo-root ``scripts/`` really contains every file the
  Dockerfile COPYs and that ``tool_bootstrap.import_simulator_extract`` imports it;
* inside the ``test`` image (``docker run -e IS_DOCKER=true ... pytest``): the same
  assertions against ``/app/scripts`` — proof that the build context allowlist
  (root ``.dockerignore``) delivered what the Dockerfile COPYs, and that
  ``simulator_extract`` is importable there (the runners must FAIL, never soft-skip, in Docker).

CI runs this file against the ``--target test`` image before the production smoke build.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DOCKERFILE = _PROJECT_ROOT / "Dockerfile"


def _host_repo_root() -> Path | None:
    for parent in _PROJECT_ROOT.parents:
        if (
            (parent / ".dockerignore").is_file()
            and (parent / "scripts" / "tool_bootstrap.py").is_file()
            and (parent / "OPC_UA_Clients").is_dir()
        ):
            return parent
    return None


def _shared_scripts_dir() -> Path:
    """Repo-root ``scripts/`` on the host, ``/app/scripts`` inside the image."""
    root = _host_repo_root()
    return (root or _PROJECT_ROOT) / "scripts"


def _copied_script_names() -> list[str]:
    text = _DOCKERFILE.read_text(encoding="utf-8")
    joined = re.sub(r"\\[ \t]*\r?\n", " ", text)
    names: set[str] = set()
    for line in joined.splitlines():
        stripped = line.strip()
        if not re.match(r"^COPY\b", stripped, re.IGNORECASE):
            continue
        tokens = [t for t in stripped.split()[1:] if not t.startswith("--")]
        names.update(Path(t).name for t in tokens[:-1] if t.startswith("scripts/"))
    return sorted(names)


@pytest.fixture
def shared_scripts_on_path():
    scripts_dir = str(_shared_scripts_dir())
    added = scripts_dir not in sys.path
    if added:
        sys.path.insert(0, scripts_dir)
    try:
        yield _shared_scripts_dir()
    finally:
        if added and scripts_dir in sys.path:
            sys.path.remove(scripts_dir)


def test_dockerfile_copies_simulator_extract_and_peers():
    names = _copied_script_names()
    assert "simulator_extract.py" in names
    assert "tool_bootstrap.py" in names


def test_every_dockerfile_copied_script_exists_in_shared_scripts_dir():
    scripts_dir = _shared_scripts_dir()
    missing = [name for name in _copied_script_names() if not (scripts_dir / name).is_file()]
    assert not missing, f"missing from {scripts_dir}: {missing}"


def test_simulator_extract_imports_under_shared_policy(shared_scripts_on_path):
    import tool_bootstrap

    module = tool_bootstrap.import_simulator_extract(shared_scripts_on_path)
    assert module is not None, f"simulator_extract.py not importable from {shared_scripts_on_path}"
    assert callable(module.ensure_present_simulator_packages)
    assert callable(module.default_server_dir)


def test_policy_fails_hard_in_docker_but_soft_skips_on_host(tmp_path, monkeypatch, shared_scripts_on_path):
    import tool_bootstrap

    empty_scripts = tmp_path / "scripts"
    empty_scripts.mkdir()

    monkeypatch.setenv("IS_DOCKER", "true")
    with pytest.raises(RuntimeError, match="simulator_extract"):
        tool_bootstrap.import_simulator_extract(empty_scripts)

    monkeypatch.delenv("IS_DOCKER", raising=False)
    monkeypatch.setattr(tool_bootstrap, "_DOCKERENV_MARKER", tmp_path / "absent.dockerenv")
    assert tool_bootstrap.import_simulator_extract(empty_scripts) is None
