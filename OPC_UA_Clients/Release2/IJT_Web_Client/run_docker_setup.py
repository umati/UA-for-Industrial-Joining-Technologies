#!/usr/bin/env python3
"""
Docker setup automation for IJT Web Client.
Canonical location: run_docker_setup.py

Handles:
  - Auto-detect: uses Docker if available, falls back to local setup
  - Force docker: builds image, starts compose stack, optionally tails logs
  - Force local: runs setup_project.py directly
"""

import argparse
import shutil

# safe: subprocess used only to invoke docker/compose with no user-controlled input.
import subprocess  # nosec B404
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SETUP_SCRIPT = PROJECT_ROOT / "setup_project.py"
DOCKERFILE = PROJECT_ROOT / "Dockerfile"


def detect_repo_root(start_dir: Path) -> Path:
    for candidate in [start_dir] + list(start_dir.parents):
        if (candidate / "OPC_UA_Clients").exists() and (candidate / "OPC_UA_Servers").exists():
            return candidate
    return start_dir


REPO_ROOT = detect_repo_root(PROJECT_ROOT)

CONTAINER_NAME = "ijt_web_client"
IMAGE_NAME = "ijt_web_client"


def run_command(cmd: list[str], check: bool = True, cwd: Path | None = None) -> subprocess.CompletedProcess:
    print("Running:", " ".join(str(c) for c in cmd))
    return subprocess.run(cmd, check=check, cwd=str(cwd) if cwd else None)


def docker_available() -> bool:
    return shutil.which("docker") is not None


def docker_running() -> bool:
    if not docker_available():
        return False
    try:
        result = subprocess.run(
            ["docker", "info"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return result.returncode == 0
    except Exception:
        return False


def detect_compose_cmd() -> list[str]:
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    return ["docker", "compose"]


def run_docker(setup_args: list[str], follow_logs: bool = True) -> None:
    compose_cmd = detect_compose_cmd()

    print("Stopping/removing existing container if present...")
    run_command(["docker", "stop", CONTAINER_NAME], check=False)
    run_command(["docker", "rm", CONTAINER_NAME], check=False)

    print("Removing existing image if present...")
    run_command(["docker", "rmi", IMAGE_NAME], check=False)

    print("Cleaning stale docker resources...")
    run_command(compose_cmd + ["down", "-v"], check=False, cwd=PROJECT_ROOT)
    run_command(["docker", "image", "prune", "-f"], check=False)
    run_command(["docker", "volume", "prune", "-f"], check=False)

    print("Building docker image...")
    run_command(["docker", "build", "--no-cache", "-f", str(DOCKERFILE), "-t", IMAGE_NAME, str(REPO_ROOT)])

    print("Starting docker compose stack...")
    run_command(compose_cmd + ["up", "-d"], cwd=PROJECT_ROOT)

    if follow_logs:
        print("Streaming container logs (Ctrl+C to stop following)...")
        run_command(["docker", "logs", "-f", CONTAINER_NAME], check=False)
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
        help="Arguments passed through to setup_project.py",
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
    args = parser.parse_args()
    setup_args = args.setup_args if args.setup_args else ["--force_full"]

    if args.mode == "local":
        run_local(setup_args)
        return
    if args.mode == "docker":
        if not docker_running():
            raise RuntimeError("Docker mode requested but Docker is unavailable or not running.")
        run_docker(setup_args, follow_logs=not args.no_follow_logs)
        return

    # auto mode
    if docker_running():
        run_docker(setup_args, follow_logs=not args.no_follow_logs)
    else:
        print("Docker unavailable/not running. Falling back to local setup.")
        run_local(setup_args)


if __name__ == "__main__":
    main()
