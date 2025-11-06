#!/usr/bin/env python3
import os
import subprocess
import sys
import shutil

CONTAINER_NAME = "ijt_web_client"
IMAGE_NAME = "ijt_web_client"
PORTS = ["3000:3000", "8001:8001"]


def run_command(cmd, shell=False, check=True):
    print(f"Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    result = subprocess.run(cmd, shell=shell)
    if check and result.returncode != 0:
        print(f"❌ Command failed: {cmd}")
        sys.exit(result.returncode)


def check_docker():
    if shutil.which("docker") is None:
        print("❌ Docker is not installed or not in PATH.")
        sys.exit(1)
    try:
        subprocess.run(
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except subprocess.CalledProcessError:
        print("❌ Docker daemon is not running.")
        sys.exit(1)


def main():
    check_docker()

    print("🛑 Stopping and removing existing container...")
    subprocess.run(["docker", "stop", CONTAINER_NAME], stderr=subprocess.DEVNULL)
    subprocess.run(["docker", "rm", CONTAINER_NAME], stderr=subprocess.DEVNULL)

    print("🗑 Removing existing Docker image...")
    subprocess.run(["docker", "rmi", IMAGE_NAME], stderr=subprocess.DEVNULL)

    print("🔨 Rebuilding Docker image (no cache)...")
    run_command(["docker", "build", "--no-cache", "-t", IMAGE_NAME, "."])

    print("🚀 Running Docker container...")
    run_command(
        ["docker", "run", "--name", CONTAINER_NAME, "-d"]
        + [f"-p {p}" for p in PORTS]
        + [IMAGE_NAME]
    )

    print("✅ Container started successfully.")

    print("📦 Executing setup_project.py inside container with --force_full...")
    run_command(
        ["docker", "exec", CONTAINER_NAME, "python", "setup_project.py", "--force_full"]
    )

    print("📜 Following Docker container logs...")
    subprocess.run(["docker", "logs", "-f", CONTAINER_NAME])


if __name__ == "__main__":
    main()
