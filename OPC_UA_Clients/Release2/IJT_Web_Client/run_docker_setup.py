#!/usr/bin/env python3
"""
Docker setup automation for IJT Web Client.
Canonical location: run_docker_setup.py

Handles:
  - Auto-detect: uses Docker if available, falls back to local setup
  - Force docker: builds image, starts compose stack, optionally tails logs
  - Force local: runs setup_project.py directly

Uses Compose CLI v2 (`docker compose`) only. Container names are project-scoped
by Compose (no hardcoded global container_name). Parallel checkouts get a
path-derived COMPOSE_PROJECT_NAME and image tag so down/up cannot collide.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess  # nosec B404 - invokes docker/compose with fixed argv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SETUP_SCRIPT = PROJECT_ROOT / "setup_project.py"
DOCKERFILE = PROJECT_ROOT / "Dockerfile"
COMPOSE_SERVICE = "ijt_web_client"
_DOCKER_INFO_TIMEOUT_SEC = 20.0


def detect_repo_root(start_dir: Path) -> Path:
    for candidate in [start_dir] + list(start_dir.parents):
        if (candidate / "OPC_UA_Clients").exists() and (candidate / "OPC_UA_Servers").exists():
            return candidate
    return start_dir


REPO_ROOT = detect_repo_root(PROJECT_ROOT)


def compose_project_name(project_root: Path = PROJECT_ROOT) -> str:
    """Stable short name unique per absolute checkout path."""
    digest = hashlib.sha256(str(project_root.resolve()).encode("utf-8")).hexdigest()[:10]
    return f"ijtweb{digest}"


def image_name_for_checkout(project_root: Path = PROJECT_ROOT) -> str:
    return f"ijt_web_client:{compose_project_name(project_root)}"


def run_command(
    cmd: list[str],
    check: bool = True,
    cwd: Path | None = None,
    *,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
) -> subprocess.CompletedProcess:
    print("Running:", " ".join(str(c) for c in cmd))
    return subprocess.run(  # noqa: S603 - argv built from fixed docker/compose tokens
        cmd,
        check=check,
        cwd=str(cwd) if cwd else None,
        env=env,
        timeout=timeout,
    )


def docker_available() -> bool:
    return shutil.which("docker") is not None


def docker_running() -> bool:
    if not docker_available():
        return False
    try:
        result = subprocess.run(  # noqa: S603
            ["docker", "info"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=_DOCKER_INFO_TIMEOUT_SEC,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def compose_cmd() -> list[str]:
    if not docker_available():
        raise RuntimeError("Docker CLI not found on PATH")
    try:
        probe = subprocess.run(  # noqa: S603
            ["docker", "compose", "version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=_DOCKER_INFO_TIMEOUT_SEC,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("Compose CLI v2 preflight failed (docker compose version)") from exc
    if probe.returncode != 0:
        raise RuntimeError(
            "Compose CLI v2 required (`docker compose`). "
            f"Preflight exit {probe.returncode}: {(probe.stderr or probe.stdout or '').strip()}"
        )
    return ["docker", "compose"]


def _compose_env(
    *,
    setup_args: list[str],
    image_name: str,
    project_name: str,
) -> dict[str, str]:
    env = os.environ.copy()
    env["COMPOSE_PROJECT_NAME"] = project_name
    env["IJT_WEB_IMAGE"] = image_name
    # Consumed by docker-compose.yml service command.
    env["IJT_SETUP_ARGS"] = " ".join(setup_args)
    return env


def run_docker(
    setup_args: list[str],
    follow_logs: bool = True,
    *,
    no_cache: bool = False,
) -> None:
    compose = compose_cmd()
    project_name = compose_project_name()
    image_name = image_name_for_checkout()
    env = _compose_env(
        setup_args=setup_args,
        image_name=image_name,
        project_name=project_name,
    )

    # -v drops the named node_modules volume so rebuilt images see fresh
    # package-lock installs. Scoped to this Compose project only (no prune).
    print(f"Stopping Compose project {project_name!r} (if any)...")
    run_command(
        compose + ["down", "-v", "--remove-orphans"],
        check=False,
        cwd=PROJECT_ROOT,
        env=env,
    )

    print(f"Building docker image {image_name}...")
    build_cmd = ["docker", "build", "-f", str(DOCKERFILE), "-t", image_name]
    if no_cache:
        build_cmd.append("--no-cache")
    build_cmd.append(str(REPO_ROOT))
    run_command(build_cmd)

    print("Starting docker compose stack...")
    run_command(compose + ["up", "-d", "--no-build"], cwd=PROJECT_ROOT, env=env)

    if follow_logs:
        print(f"Streaming logs for service {COMPOSE_SERVICE} (Ctrl+C to stop following)...")
        run_command(
            compose + ["logs", "-f", COMPOSE_SERVICE],
            check=False,
            cwd=PROJECT_ROOT,
            env=env,
        )
    else:
        print("Skipping log follow (--no-follow-logs).")


def run_local(setup_args: list[str]) -> None:
    if not SETUP_SCRIPT.exists():
        raise FileNotFoundError(f"{SETUP_SCRIPT} not found. Run from the project root.")
    print("Running local setup script...")
    run_command([sys.executable, str(SETUP_SCRIPT)] + setup_args)


def main() -> None:
    parser = argparse.ArgumentParser(description="Docker or local setup for IJT Web Client")
    parser.add_argument(
        "--setup-args",
        nargs=argparse.REMAINDER,
        help="Arguments passed through to setup_project.py (local and docker modes).",
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "docker", "local"],
        default="auto",
        help="auto (default): use Docker if available, else local; docker: force Docker; local: force local.",
    )
    parser.add_argument(
        "--no-follow-logs",
        action="store_true",
        help="In docker mode, do not tail container logs after startup.",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="In docker mode, rebuild the image with docker build --no-cache.",
    )
    args = parser.parse_args()
    setup_args = args.setup_args if args.setup_args else ["--force_full"]

    if args.mode == "local":
        run_local(setup_args)
        return
    if args.mode == "docker":
        if not docker_running():
            raise RuntimeError("Docker mode requested but Docker is unavailable or not running.")
        run_docker(
            setup_args,
            follow_logs=not args.no_follow_logs,
            no_cache=args.no_cache,
        )
        return

    if docker_running():
        run_docker(
            setup_args,
            follow_logs=not args.no_follow_logs,
            no_cache=args.no_cache,
        )
    else:
        print("Docker unavailable/not running. Falling back to local setup.")
        run_local(setup_args)


if __name__ == "__main__":
    main()
