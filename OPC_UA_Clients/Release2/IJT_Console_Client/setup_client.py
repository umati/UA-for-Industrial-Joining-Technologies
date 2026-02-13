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
import shlex

# ───────────────────────────────
# Logging
# ───────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger(__name__)

# ───────────────────────────────
# Constants
# ───────────────────────────────
VENV_DIR = Path("venv")
IS_WINDOWS = os.name == "nt"
URL_PATTERN = r"opc\.tcp://[a-zA-Z0-9\.\-]+:\d+"


def exe_in_venv(name: str) -> Path:
    return (
        VENV_DIR
        / ("Scripts" if IS_WINDOWS else "bin")
        / (name + (".exe" if IS_WINDOWS else ""))
    )


def python_in_venv() -> Path:
    return exe_in_venv("python")


def pip_in_venv() -> Path:
    return exe_in_venv("pip")


# ───────────────────────────────
# Pick the newest Python installed on the machine
# ───────────────────────────────
def list_pythons_windows():
    """Return a list of version strings like '3.14', '3.13' found by the py launcher."""
    try:
        out = subprocess.check_output(["py", "-0"], text=True, stderr=subprocess.STDOUT)
    except Exception as e:
        log.debug("py -0 failed: %s", e)
        return []

    vers = []
    for line in out.splitlines():
        # Lines look like: " -V:3.14 *        Python 3.14 (64-bit)"
        line = line.strip()
        if not line.startswith("-V:") and not line.startswith("-"):
            continue
        # Accept both "-V:3.14" and "-3.14" formats
        token = line.split()[0]  # "-V:3.14" or "-3.14"
        v = token.replace("-V:", "").replace("-", "")
        if v.count(".") == 1 and v.startswith("3."):
            vers.append(v)
    return vers


def find_latest_python_executable():
    """
    Returns a tuple (launcher_cmd, version) where launcher_cmd is a list like:
      - Windows: ["py", "-3.16"] or ["py", "-3.15"] ...
      - POSIX:   ["python3.16"] or ["python3.15"] ...
    and version is "3.16", "3.15", ...
    """
    if IS_WINDOWS:
        versions = list_pythons_windows()
        if not versions:
            log.error(
                "No Python 3.x found by the Windows 'py' launcher. Please install Python 3."
            )
            sys.exit(1)
        # pick numerically highest
        latest = sorted(
            versions, key=lambda s: tuple(map(int, s.split("."))), reverse=True
        )[0]
        return (["py", f"-{latest}"], latest)
    else:
        # Probe from newest to older
        for minor in range(
            16, 9, -1
        ):  # 3.16 down to 3.10 (adjust the floor as you prefer)
            exe = f"python3.{minor}"
            try:
                subprocess.check_call(
                    [exe, "--version"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return ([exe], f"3.{minor}")
            except Exception:
                continue
        # Fallback to python3 if present
        try:
            subprocess.check_call(
                ["python3", "--version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            # parse the actual minor
            out = subprocess.check_output(
                [
                    "python3",
                    "-c",
                    "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')",
                ],
                text=True,
            )
            version = out.strip()
            if not version.startswith("3."):
                raise RuntimeError("python3 not a Python 3 interpreter")
            return (["python3"], version)
        except Exception:
            log.error("Could not find a Python 3 interpreter on PATH.")
            sys.exit(1)


def relaunch_under_latest_python():
    """If current python is not the latest available, re-launch this script under the newest one."""
    latest_cmd, latest_ver = find_latest_python_executable()
    current_ver = f"{sys.version_info[0]}.{sys.version_info[1]}"
    if current_ver == latest_ver:
        log.info("Using latest Python %s", current_ver)
        return
    # Relaunch
    cmd = latest_cmd + [__file__] + sys.argv[1:]
    log.info(
        "Re-launching under Python %s: %s",
        latest_ver,
        " ".join(shlex.quote(c) for c in cmd),
    )
    os.execvp(cmd[0], cmd)


# ───────────────────────────────
# Venv creation and package install
# ───────────────────────────────
def create_venv_with(latest_cmd):
    """Create venv with the selected interpreter."""
    if VENV_DIR.exists():
        log.info("Virtual environment already exists.")
        return
    log.info(
        "Creating virtual environment with interpreter: %s",
        " ".join(latest_cmd + ["-V"]),
    )
    subprocess.check_call(latest_cmd + ["-m", "venv", str(VENV_DIR)])


def install_requirements():
    """Install dependencies. Then ensure asyncua is up-to-date, allowing pre-releases if needed."""
    py = str(python_in_venv())
    req = Path("requirements.txt")
    if not req.exists():
        log.error("requirements.txt missing! Cannot continue.")
        sys.exit(1)

    log.info("Upgrading pip...")
    subprocess.check_call([py, "-m", "pip", "install", "--upgrade", "pip"])

    # 1) Install the file as-is (stable channel)
    log.info("Installing dependencies from requirements.txt ...")
    subprocess.check_call([py, "-m", "pip", "install", "--upgrade", "-r", str(req)])

    # 2) Ensure asyncua can track newest Python by allowing pre-release if necessary.
    #    This safeguards future Python X.Y support without changing this script.
    log.info(
        "Ensuring asyncua is compatible with the latest Python (allowing pre-releases if available)..."
    )
    subprocess.check_call(
        [py, "-m", "pip", "install", "--upgrade", "--pre", "asyncua>=1.2b1"]
    )


def validate_url(url: str):
    if url and re.match(URL_PATTERN, url):
        return url
    if url:
        log.warning("Invalid OPC UA URL format: %s", url)
    return None


def run_client(url_arg=None, passthrough=None):
    py = str(python_in_venv())
    main_file = Path("main.py")
    if not main_file.exists():
        log.error("main.py not found in the current directory.")
        sys.exit(1)
    cmd = [py, str(main_file)]
    if url_arg:
        cmd.append(f"--url={url_arg}")
    if passthrough:
        cmd.extend(passthrough)
    log.info("Starting OPC UA client...")
    subprocess.call(cmd)


# ───────────────────────────────
# CLI
# ───────────────────────────────
def main():
    # First hop: ensure we're running under the newest Python on this system.
    # (Windows selection via 'py -0' / 'py -3.x'; POSIX via python3.x probe)
    relaunch_under_latest_python()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url", type=str, help="OPC UA server URL (opc.tcp://<ip>:<port>)"
    )
    parser.add_argument("--force", action="store_true", help="Recreate venv")
    parser.add_argument("--clean", action="store_true", help="Remove venv and exit")
    args, unknown = parser.parse_known_args()

    if args.clean:
        if VENV_DIR.exists():
            log.info("Removing virtual environment...")
            shutil.rmtree(VENV_DIR)
        else:
            log.info("No virtual environment to clean.")
        sys.exit(0)

    if args.force and VENV_DIR.exists():
        log.info("Force flag set. Removing existing venv...")
        shutil.rmtree(VENV_DIR)

    # Create venv with the same (latest) interpreter we relaunched under
    latest_cmd, _ = find_latest_python_executable()
    create_venv_with(latest_cmd)
    install_requirements()

    # Default OPC UA endpoint if none provided
    DEFAULT_URL = "opc.tcp://localhost:40451"

    # If user gave an URL → validate.
    # If not provided → use our default.
    url_arg = validate_url(args.url) if args.url else DEFAULT_URL
    if url_arg:
        run_client(url_arg, passthrough=unknown)
    else:
        log.info("\nSetup complete. Activate the venv and run:")
        if IS_WINDOWS:
            log.info("  venv\\Scripts\\activate")
        else:
            log.info("  source venv/bin/activate")
        log.info("Then start the client:")
        log.info("  python main.py --url opc.tcp://<ip>:<port>")


if __name__ == "__main__":
    main()
