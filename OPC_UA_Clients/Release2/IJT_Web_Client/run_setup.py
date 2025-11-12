#!/usr/bin/env python3
import argparse
import subprocess
import sys
import shutil
import os

CONTAINER_NAME = "ijt_web_client"
IMAGE_NAME = "ijt_web_client"
PORTS = ["3000:3000", "8001:8001"]
SETUP_SCRIPT = "setup_project.py"

def run_command(cmd, shell=False, check=True):
    print(f"Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    result = subprocess.run(cmd, shell=shell)
    if check and result.returncode != 0:
        print(f"❌ Command failed: {cmd}")
        sys.exit(result.returncode)

def docker_available():
    return shutil.which("docker") is not None

def docker_running():
    try:
        subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def get_local_python():
    return "venv\\Scripts\\python.exe" if os.name == "nt" else "venv/bin/python"

def run_docker(setup_args):
    print("🛑 Stopping and removing existing container...")
    subprocess.run(["docker", "stop", CONTAINER_NAME], stderr=subprocess.DEVNULL)
    subprocess.run(["docker", "rm", CONTAINER_NAME], stderr=subprocess.DEVNULL)

    print("🗑️ Removing existing Docker image...")
    subprocess.run(["docker", "rmi", IMAGE_NAME], stderr=subprocess.DEVNULL)

    print("🔨 Performing full Docker cleanup...")
    subprocess.run(['docker-compose', 'down', '-v'], check=False)
    subprocess.run(['docker', 'image', 'prune', '-f'], check=False)
    subprocess.run(['docker', 'volume', 'prune', '-f'], check=False)

    print("🔨 Rebuilding Docker image (no cache)...")
    run_command(["docker", "build", "--no-cache", "-t", IMAGE_NAME, "."])

    print("🚀 Starting container...")
    run_command(["docker-compose", "up", "-d"])

    print("📄 Following Docker logs...")
    subprocess.run(["docker", "logs", "-f", CONTAINER_NAME])

def run_local(setup_args):
    print("🐍 Running setup_project.py locally...")
    local_python = get_local_python()
    if not os.path.exists(SETUP_SCRIPT):
        print("❌ setup_project.py not found in local directory.")
        sys.exit(1)
    run_command([local_python, SETUP_SCRIPT] + setup_args)

def main():
    parser = argparse.ArgumentParser(description="Run setup for IJT Web Client")
    parser.add_argument("--setup-args", nargs=argparse.REMAINDER, help="Arguments to pass to setup_project.py")
    args = parser.parse_args()
    setup_args = ['--force_full']

    if docker_available() and docker_running():
        run_docker(setup_args)
    else:
        print("⚠️ Docker not available or not running. Falling back to local setup.")
        run_local(setup_args)

if __name__ == "__main__":
    main()