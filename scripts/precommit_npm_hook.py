#!/usr/bin/env python3
"""Run npm-backed pre-commit hooks with deterministic local dependencies."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path
from stat import S_IWRITE

REPO_ROOT = Path(__file__).resolve().parents[1]
_INSTALL_FLAGS = ("--no-audit", "--no-fund")
_MARKER_NAME = ".ijt-precommit-deps.sha256"


def _npm_command() -> str:
    return shutil.which("npm.cmd") or shutil.which("npm") or "npm"


def _resolve_project(project: str) -> Path:
    project_dir = (REPO_ROOT / project).resolve()
    project_dir.relative_to(REPO_ROOT.resolve())
    return project_dir


def _dependency_hash(project_dir: Path) -> str:
    digest = hashlib.sha256()
    for name in ("package.json", "package-lock.json"):
        path = project_dir / name
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _bin_exists(project_dir: Path, name: str) -> bool:
    bin_dir = project_dir / "node_modules" / ".bin"
    candidates = (bin_dir / name, bin_dir / f"{name}.cmd", bin_dir / f"{name}.ps1")
    return any(path.exists() for path in candidates)


def _dependencies_current(project_dir: Path, required_bins: list[str]) -> bool:
    node_modules = project_dir / "node_modules"
    marker = node_modules / _MARKER_NAME
    if not node_modules.is_dir() or not marker.is_file():
        return False
    if marker.read_text(encoding="utf-8").strip() != _dependency_hash(project_dir):
        return False
    return all(_bin_exists(project_dir, name) for name in required_bins)


def _npm_env(project_dir: Path) -> dict[str, str]:
    cache_dir = project_dir / "tmp" / "precommit-npm-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.setdefault("npm_config_cache", str(cache_dir))
    env.setdefault("npm_config_update_notifier", "false")
    return env


def _force_rmtree(path: Path) -> None:
    def _on_exc(func, fpath, _exc):
        try:
            os.chmod(fpath, S_IWRITE)
            func(fpath)
        except OSError:
            pass

    shutil.rmtree(path, onexc=_on_exc)


def _run(cmd: list[str], project_dir: Path) -> int:
    return subprocess.run(  # noqa: S603
        cmd,
        cwd=str(REPO_ROOT),
        env=_npm_env(project_dir),
        check=False,
    ).returncode


def _ensure_dependencies(project_dir: Path, required_bins: list[str]) -> int:
    if _dependencies_current(project_dir, required_bins):
        return 0

    npm = _npm_command()
    node_modules = project_dir / "node_modules"
    if node_modules.exists():
        _force_rmtree(node_modules)

    rc = _run([npm, "--prefix", str(project_dir), "ci", *_INSTALL_FLAGS], project_dir)
    if rc != 0:
        return rc

    marker = project_dir / "node_modules" / _MARKER_NAME
    marker.write_text(f"{_dependency_hash(project_dir)}\n", encoding="utf-8")

    missing = [name for name in required_bins if not _bin_exists(project_dir, name)]
    if missing:
        print(
            f"ERROR: npm ci completed but required bin(s) are missing: {', '.join(missing)}",
            file=sys.stderr,
        )
        return 1
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project",
        required=True,
        help="Project directory relative to repository root",
    )
    parser.add_argument("--script", required=True, help="npm script name to run")
    parser.add_argument(
        "--required-bin",
        action="append",
        default=[],
        help="Executable expected in project-local node_modules/.bin after npm ci",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    project_dir = _resolve_project(args.project)

    for required in ("package.json", "package-lock.json"):
        if not (project_dir / required).is_file():
            print(f"ERROR: missing {project_dir / required}", file=sys.stderr)
            return 1

    rc = _ensure_dependencies(project_dir, list(args.required_bin))
    if rc != 0:
        return rc

    npm = _npm_command()
    return _run([npm, "--prefix", str(project_dir), "run", args.script], project_dir)


if __name__ == "__main__":
    raise SystemExit(main())
