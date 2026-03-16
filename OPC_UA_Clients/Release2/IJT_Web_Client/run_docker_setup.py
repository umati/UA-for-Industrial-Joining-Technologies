#!/usr/bin/env python3
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

CONTAINER_NAME = "ijt_web_client"
IMAGE_NAME = "ijt_web_client"
SETUP_SCRIPT = Path("setup_project.py")


def run_command(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    print("Running:", " ".join(cmd))
    return subprocess.run(cmd, check=check)


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


def run_docker(setup_args: list[str]) -> None:
    compose_cmd = detect_compose_cmd()

    print("Stopping/removing existing container if present...")
    run_command(["docker", "stop", CONTAINER_NAME], check=False)
    run_command(["docker", "rm", CONTAINER_NAME], check=False)

    print("Removing existing image if present...")
    run_command(["docker", "rmi", IMAGE_NAME], check=False)

    print("Cleaning stale docker resources...")
    run_command(compose_cmd + ["down", "-v"], check=False)
    run_command(["docker", "image", "prune", "-f"], check=False)
    run_command(["docker", "volume", "prune", "-f"], check=False)

    print("Building docker image...")
    run_command(["docker", "build", "--no-cache", "-t", IMAGE_NAME, "."])

    print("Starting docker compose stack...")
    run_command(compose_cmd + ["up", "-d"])

    print("Streaming container logs...")
    run_command(["docker", "logs", "-f", CONTAINER_NAME], check=False)


def run_local(setup_args: list[str]) -> None:
    if not SETUP_SCRIPT.exists():
        raise FileNotFoundError(f"{SETUP_SCRIPT} not found in current directory")

    print("Running local setup script...")
    run_command([sys.executable, str(SETUP_SCRIPT)] + setup_args)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run setup for IJT Web Client")
    parser.add_argument(
        "--setup-args",
        nargs=argparse.REMAINDER,
        help="Arguments passed through to setup_project.py",
    )
    args = parser.parse_args()

    setup_args = args.setup_args if args.setup_args else ["--force_full"]

    if docker_running():
        run_docker(setup_args)
    else:
        print("Docker unavailable/not running. Falling back to local setup.")
        run_local(setup_args)


if __name__ == "__main__":
    main()
