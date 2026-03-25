#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCKER_CONFIG_DIR = PROJECT_ROOT / ".state" / "docker-config"


def _docker_env() -> dict[str, str]:
    env = dict(os.environ)
    DOCKER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    env["DOCKER_CONFIG"] = str(DOCKER_CONFIG_DIR)
    return env


def _run(cmd: list[str], timeout: int = 600, check: bool = True) -> subprocess.CompletedProcess:
    print("Running:", " ".join(cmd))
    return subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        timeout=timeout,
        check=check,
        env=_docker_env(),
    )


def _docker_running() -> bool:
    try:
        result = subprocess.run(
            ["docker", "info"],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=20,
            env=_docker_env(),
        )
        return result.returncode == 0
    except Exception:
        return False


def _container_running(name: str) -> bool:
    try:
        result = subprocess.run(
            [
                "docker",
                "ps",
                "--filter",
                f"name={name}",
                "--format",
                "{{.Names}}",
            ],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
            env=_docker_env(),
        )
        return name in result.stdout.splitlines()
    except Exception:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke/integration checks for run_docker_setup.py")
    parser.add_argument(
        "--live-docker",
        action="store_true",
        help="Run a live docker-mode setup check (build + compose up) without log tailing.",
    )
    parser.add_argument(
        "--docker-timeout",
        type=int,
        default=900,
        help="Timeout in seconds for live docker setup command.",
    )
    args = parser.parse_args()

    python = sys.executable

    _run([python, "run_docker_setup.py", "--help"], timeout=60)
    _run([python, "run_docker_setup.py", "--mode", "local", "--setup-args", "--help"], timeout=120)

    if not args.live_docker:
        print("Skipping live docker test (use --live-docker to enable).")
        return 0

    if not _docker_running():
        print("[ERROR] Docker is unavailable or not running.")
        return 1

    _run(
        [
            python,
            "run_docker_setup.py",
            "--mode",
            "docker",
            "--no-follow-logs",
        ],
        timeout=max(120, args.docker_timeout),
    )
    if not _container_running("ijt_web_client"):
        print("[ERROR] Expected docker container 'ijt_web_client' is not running after setup.")
        return 1

    print("Docker setup tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
