#!/usr/bin/env python3
import os
import sys
import subprocess
import venv
import logging
from pathlib import Path
import shutil
import importlib.util

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


def check_python_version():
    if sys.version_info < (3, 8):
        log.error("Python 3.8 or higher is required.")
        sys.exit(1)


def create_virtualenv():
    if not VENV_DIR.exists():
        log.info("Creating virtual environment...")
        venv.create(VENV_DIR, with_pip=True)
    else:
        log.info("Virtual environment already exists.")


def is_package_installed(package_name):
    return importlib.util.find_spec(package_name) is not None


def check_packages():
    missing = [pkg for pkg in REQUIRED_PACKAGES if not is_package_installed(pkg)]
    if missing:
        log.warning(f"Missing packages: {missing}")
        log.warning(
            "Please install them manually or ensure your proxy allows pip access."
        )
        sys.exit(1)
    else:
        log.info("All required packages are already installed.")


def run_client():
    main_file = Path("main.py")
    if not main_file.exists():
        log.error("main.py not found in the current directory.")
        sys.exit(1)

    log.info("Starting OPC UA client...")
    try:
        subprocess.call([str(PYTHON_EXECUTABLE), str(main_file)])
    except KeyboardInterrupt:
        log.info("Client interrupted by user (Ctrl+C).")
    except Exception as e:
        log.error(f"Failed to run client: {e}")
        sys.exit(1)


def main():
    force = "--force" in sys.argv
    check_python_version()

    if force and VENV_DIR.exists():
        log.info("Force setup enabled. Removing existing virtual environment...")
        shutil.rmtree(VENV_DIR)

    create_virtualenv()
    check_packages()
    run_client()


if __name__ == "__main__":
    main()
