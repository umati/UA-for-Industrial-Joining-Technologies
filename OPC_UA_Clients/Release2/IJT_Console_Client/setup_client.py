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
URL_PATTERN = r"opc\.tcp://[a-zA-Z0-9\.\-]+:\d+"
DEFAULT_PACKAGES = ["asyncua", "pytz", "aiofiles", "orjson"]


def check_python_version():
    current_version = sys.version_info[:2]
    if current_version >= (3, 14):
        log.warning("Python 3.14+ detected. Some packages may not be fully compatible.")
    elif current_version < (3, 8):
        log.error("Python 3.8 or higher is required.")
        sys.exit(1)


def create_virtualenv():
    try:
        if not VENV_DIR.exists():
            log.info("Creating virtual environment...")
            venv.create(VENV_DIR, with_pip=True)
        else:
            log.info("Virtual environment already exists.")
    except Exception as e:
        log.error(f"Failed to create virtual environment: {e}")
        sys.exit(1)


def install_packages():
    log.info("Upgrading pip...")
    subprocess.check_call(
        [str(PYTHON_EXECUTABLE), "-m", "pip", "install", "--upgrade", "pip"]
    )

    requirements_file = Path("requirements.txt")
    if requirements_file.exists():
        log.info("Installing packages from requirements.txt...")
        subprocess.check_call(
            [
                str(PYTHON_EXECUTABLE),
                "-m",
                "pip",
                "install",
                "--upgrade",
                "-r",
                str(requirements_file),
            ]
        )
    else:
        log.info("requirements.txt not found. Installing default packages...")
        for package in DEFAULT_PACKAGES:
            subprocess.check_call(
                [str(PYTHON_EXECUTABLE), "-m", "pip", "install", "--upgrade", package]
            )


def validate_url(url: str) -> str:
    if url and re.match(URL_PATTERN, url):
        return url
    log.warning("Invalid or missing OPC UA URL. Using default.")
    return None


def run_client(url_arg=None):
    main_file = Path("main.py")
    if not main_file.exists():
        log.error("main.py not found in the current directory.")
        sys.exit(1)

    log.info("Starting OPC UA client...")
    cmd = [str(PYTHON_EXECUTABLE), str(main_file)]
    if url_arg:
        cmd.append(f"--url={url_arg}")
    subprocess.call(cmd)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", type=str, help="OPC UA server URL")
    parser.add_argument(
        "--force", action="store_true", help="Force recreate virtual environment"
    )
    parser.add_argument(
        "--clean", action="store_true", help="Remove virtual environment and exit"
    )
    args = parser.parse_args()

    url_arg = validate_url(args.url)
    check_python_version()

    if args.clean:
        if VENV_DIR.exists():
            log.info("Cleaning up virtual environment...")
            shutil.rmtree(VENV_DIR)
        else:
            log.info("No virtual environment found to clean.")
        sys.exit(0)

    if args.force and VENV_DIR.exists():
        log.info("Force setup enabled. Removing existing virtual environment...")
        shutil.rmtree(VENV_DIR)

    create_virtualenv()
    install_packages()
    run_client(url_arg)


if __name__ == "__main__":
    main()
