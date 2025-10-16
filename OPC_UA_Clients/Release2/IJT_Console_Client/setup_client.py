#!/usr/bin/env python3
import os
import sys
import subprocess
import venv
import logging
from pathlib import Path
import shutil
import argparse
import re

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger()

# Constants
VENV_DIR = Path("venv")
PYTHON_EXECUTABLE = VENV_DIR / (
    "Scripts/python.exe" if os.name == "nt" else "bin/python"
)
REQUIRED_PACKAGES = ["asyncua", "pytz"]
URL_PATTERN = r"opc\.tcp://[a-zA-Z0-9\.\-]+:\d+"


def check_python_version():
    if sys.version_info < (3, 8):
        log.error("Python 3.8 or higher is required.")
        sys.exit(1)


def find_python_executable():
    python_exec = shutil.which("python3") or shutil.which("python")
    if not python_exec:
        log.error("Python is not installed or not found in PATH.")
        sys.exit(1)
    return python_exec


def create_virtualenv():
    if not VENV_DIR.exists():
        log.info("Creating virtual environment...")
        venv.create(VENV_DIR, with_pip=True)
    else:
        log.info("Virtual environment already exists.")


def install_and_upgrade_packages():
    log.info("Upgrading pip and installing required packages...")
    subprocess.check_call(
        [str(PYTHON_EXECUTABLE), "-m", "pip", "install", "--upgrade", "pip"]
    )
    for package in REQUIRED_PACKAGES:
        subprocess.check_call(
            [str(PYTHON_EXECUTABLE), "-m", "pip", "install", "--upgrade", package]
        )


def run_client(url_arg=None):
    main_file = Path("main.py")
    if not main_file.exists():
        log.error("main.py not found in the current directory.")
        sys.exit(1)

    log.info("Starting OPC UA client...")
    try:
        cmd = [str(PYTHON_EXECUTABLE), str(main_file)]
        if url_arg:
            cmd.append(f"--url={url_arg}")
        subprocess.call(cmd)
    except KeyboardInterrupt:
        log.info("Client interrupted by user (Ctrl+C).")
    except Exception as e:
        log.error(f"Failed to run client: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", type=str, help="OPC UA server URL")
    parser.add_argument(
        "--force", action="store_true", help="Force recreate virtual environment"
    )
    args = parser.parse_args()

    url_arg = args.url if args.url and re.match(URL_PATTERN, args.url) else None

    check_python_version()

    if args.force and VENV_DIR.exists():
        log.info("Force setup enabled. Removing existing virtual environment...")
        shutil.rmtree(VENV_DIR)

    create_virtualenv()
    install_and_upgrade_packages()
    run_client(url_arg)


if __name__ == "__main__":
    main()
