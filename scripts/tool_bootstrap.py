"""Isolated, cross-process-safe preparation of Python command-line tools."""

from __future__ import annotations

import contextlib
import errno
import hashlib
import importlib
import logging
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Iterator, Sequence
from pathlib import Path

# Shared yamllint pin: Web Client dev group (pyproject/uv.lock), .pre-commit-config.yaml rev,
# and the Server runner's bootstrap venv all use this exact version
# (tests/test_shared_lint_tooling.py keeps them in lockstep).
# renovate: datasource=pypi depName=yamllint
YAMLLINT_VERSION = "1.38.0"
BOOTSTRAP_TIMEOUT = 180.0
log = logging.getLogger(__name__)

_DOCKERENV_MARKER = Path("/.dockerenv")
_DOCKER_TRUTHY = frozenset({"1", "true", "yes"})
_REPO_ROOT = Path(__file__).resolve().parents[1]
_UV_VERSION_FILE = _REPO_ROOT / ".uv-version"


def _load_uv_version() -> str:
    """Single pin from repo-root ``.uv-version`` (Renovate + CI + local bootstrap)."""
    try:
        text = _UV_VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise RuntimeError(f"Missing uv pin file: {_UV_VERSION_FILE}") from exc
    if not text or any(ch.isspace() for ch in text):
        raise RuntimeError(f"Invalid uv pin in {_UV_VERSION_FILE!s}: {text!r}")
    return text


UV_VERSION = _load_uv_version()


def running_in_docker() -> bool:
    """True inside a container: ``IS_DOCKER`` truthy (1/true/yes) or ``/.dockerenv`` exists."""
    if os.environ.get("IS_DOCKER", "").strip().lower() in _DOCKER_TRUTHY:
        return True
    try:
        return _DOCKERENV_MARKER.is_file()
    except OSError:
        return False


def import_simulator_extract(scripts_dir: Path):
    """Import ``simulator_extract`` from *scripts_dir* under the shared-script policy.

    This policy lives here (not in ``simulator_extract`` itself) because the
    caller cannot import ``simulator_extract`` to learn whether it may be absent.

    * Host, ``scripts/simulator_extract.py`` absent (partial checkout): return ``None``
      so callers soft-skip auto-extract.
    * Docker (:func:`running_in_docker`), file absent: raise ``RuntimeError``; the
      image must ship the module (Dockerfile ``base`` stage COPY + root ``.dockerignore``
      allowlist), so a missing file is a packaging bug, never a skip.
    * File present but the import fails: re-raise (never mask a broken module).
    """
    scripts_dir = Path(scripts_dir)
    module_file = scripts_dir / "simulator_extract.py"
    if not module_file.is_file():
        if running_in_docker():
            raise RuntimeError(
                f"{module_file} is missing inside Docker; the image must COPY "
                "scripts/simulator_extract.py (and root .dockerignore must allowlist it)."
            )
        return None
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    return importlib.import_module("simulator_extract")


def environment_python(directory: Path) -> Path:
    return directory / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


@contextlib.contextmanager
def preparation_lock(path: Path, timeout: float = BOOTSTRAP_TIMEOUT) -> Iterator[None]:
    """OS-held file locks release on process exit; the stable lock file is retained."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
        deadline = time.monotonic() + timeout
        while True:
            try:
                handle.seek(0)
                if sys.platform == "win32":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if exc.errno not in (errno.EACCES, errno.EAGAIN):
                    raise RuntimeError(f"Cannot acquire tooling lock: {path}") from exc
                if time.monotonic() >= deadline:
                    raise RuntimeError(
                        f"Timed out waiting for tooling preparation: {path}"
                    ) from exc
                time.sleep(0.1)
        try:
            yield
        finally:
            handle.seek(0)
            if sys.platform == "win32":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _run(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(  # noqa: S603 - internal tooling commands, no shell
            list(command),
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=BOOTSTRAP_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"Tool preparation could not run {command[0]}: {exc}") from exc
    if result.returncode:
        raise RuntimeError(
            "Tool preparation failed. Check internet/proxy/package-index access and "
            f"write permissions; offline first use requires a supplied package cache.\n"
            f"{result.stdout}\n{result.stderr}"
        )
    return result


def _assert_owned_environment_path(directory: Path, project: Path) -> Path:
    """Refuse to delete paths outside the project or its `.state/tools` tree."""
    resolved = directory.resolve()
    project_root = project.resolve()
    tools_root = (project_root / ".state" / "tools").resolve()
    under_project = resolved == project_root or project_root in resolved.parents
    under_tools = resolved == tools_root or tools_root in resolved.parents
    if not (under_project or under_tools):
        raise RuntimeError(
            f"Refusing to modify virtual environment outside project tree: {resolved}"
        )
    return resolved


def _environment_usable(python: Path) -> bool:
    try:
        result = subprocess.run(  # noqa: S603 - interpreter path from owned venv layout
            [str(python), "-c", "pass"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def _create_environment(directory: Path, project: Path) -> Path:
    python = environment_python(directory)
    cfg = directory / "pyvenv.cfg"
    recreate_reason: str | None = None
    if directory.exists() and python.is_file() and not cfg.is_file():
        recreate_reason = "missing pyvenv.cfg"
    elif (
        directory.exists()
        and python.is_file()
        and cfg.is_file()
        and not _environment_usable(python)
    ):
        recreate_reason = "interpreter probe failed"
    if recreate_reason is not None:
        owned = _assert_owned_environment_path(directory, project)
        log.warning("Removing incomplete virtual environment at %s (%s)", owned, recreate_reason)
        try:
            shutil.rmtree(owned)
        except OSError as exc:
            raise RuntimeError(f"Could not remove incomplete virtual environment: {owned}") from exc
        python = environment_python(directory)
    if not python.is_file():
        _run([sys.executable, "-m", "venv", str(directory)], project)
    return python


def _uv_usable(executable: str) -> bool:
    try:
        result = subprocess.run(  # noqa: S603 - executable selected for version verification
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and result.stdout.strip().split()[:2] == ["uv", UV_VERSION]


def ensure_uv(project: Path) -> str:
    """Reuse reviewed uv or install it once into a project-local tooling environment."""
    provisioned = shutil.which("uv")
    if provisioned and _uv_usable(provisioned):
        return provisioned
    if os.getenv("GITHUB_ACTIONS") == "true" or os.getenv("IS_DOCKER") == "true":
        raise RuntimeError(
            f"This isolated environment must provision uv {UV_VERSION}; "
            "no bootstrap download attempted."
        )
    project = project.resolve()
    tools = project / ".state" / "tools"
    directory = tools / f"uv-{UV_VERSION}-py{sys.version_info.major}{sys.version_info.minor}"
    executable = directory / ("Scripts/uv.exe" if os.name == "nt" else "bin/uv")
    with preparation_lock(tools / "uv.lock"):
        if executable.is_file() and _uv_usable(str(executable)):
            return str(executable)
        log.info("Preparing uv %s in %s (no global Python changes)", UV_VERSION, directory)
        python = _create_environment(directory, project)
        _run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-input",
                f"uv=={UV_VERSION}",
            ],
            project,
        )
        if not _uv_usable(str(executable)):
            raise RuntimeError(f"Installed uv could not be verified: {executable}")
    return str(executable)


def _requirements_fingerprint(path: Path, visited: set[Path]) -> bytes:
    path = path.resolve()
    if path in visited:
        return b""
    visited.add(path)
    data = path.read_bytes()
    nested = b""
    for line in data.decode("utf-8").splitlines():
        line = line.strip()
        for prefix in ("-r ", "--requirement ", "-c ", "--constraint "):
            if line.startswith(prefix):
                nested += _requirements_fingerprint(
                    path.parent / line[len(prefix) :].strip(), visited
                )
                break
    return str(path).encode() + data + nested


def ensure_requirements_environment(
    project: Path,
    requirements: Sequence[Path],
    modules: Sequence[str],
    name: str = "tests",
    packages: Sequence[str] = (),
) -> Path:
    """Prepare a venv+pip project from its requirements, never the user's global Python."""
    project = project.resolve()
    tools = project / ".state" / "tools"
    directory = tools / f"{name}-py{sys.version_info.major}{sys.version_info.minor}"
    fingerprint = hashlib.sha256(
        b"".join(_requirements_fingerprint(path, set()) for path in requirements)
        + repr(tuple(packages)).encode()
    ).hexdigest()
    with preparation_lock(tools / f"{name}.lock"):
        python = _create_environment(directory, project)
        marker = directory / ".requirements-hash"
        probe = (
            "import importlib.util,sys; "
            f"sys.exit(not all(importlib.util.find_spec(m) for m in {tuple(modules)!r}))"
        )
        healthy = (
            subprocess.run(  # noqa: S603 - managed interpreter and fixed import probe
                [str(python), "-c", probe],
                cwd=project,
                capture_output=True,
                timeout=10,
                check=False,
            ).returncode
            == 0
        )
        if marker.is_file() and marker.read_text() == fingerprint and healthy:
            return python
        command = [str(python), "-m", "pip", "install", "--disable-pip-version-check", "--no-input"]
        for path in requirements:
            command.extend(["-r", str(path.resolve())])
        command.extend(packages)
        _run(command, project)
        _run([str(python), "-c", probe], project)
        _run([str(python), "-m", "pip", "check"], project)
        marker.write_text(fingerprint, encoding="utf-8")
    return python
