"""Isolated, cross-process-safe preparation of Python command-line tools."""

from __future__ import annotations

import contextlib
import errno
import hashlib
import logging
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Iterator, Sequence
from pathlib import Path

# renovate: datasource=pypi depName=uv
UV_VERSION = "0.12.24"
BOOTSTRAP_TIMEOUT = 180.0
log = logging.getLogger(__name__)


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


def _create_environment(directory: Path, project: Path) -> Path:
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
