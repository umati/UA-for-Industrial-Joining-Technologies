import os
import sys
import subprocess
import venv
import logging
from pathlib import Path
import shutil
import argparse
import shlex

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Paths / constants
# ─────────────────────────────────────────────────────────────────────────────
VENV_DIR = Path("venv")
IS_WINDOWS = os.name == "nt"


def _py_in_venv() -> Path:
    return VENV_DIR / ("Scripts/python.exe" if IS_WINDOWS else "bin/python")


def _pip_in_venv() -> Path:
    return VENV_DIR / ("Scripts/pip.exe" if IS_WINDOWS else "bin/pip")


# ─────────────────────────────────────────────────────────────────────────────
# Windows: list/select newest Python via 'py' launcher; POSIX: probe python3.X
# ─────────────────────────────────────────────────────────────────────────────
def _list_pythons_windows() -> list[str]:
    """Return versions ['3.16','3.15','3.14',...] from 'py -0'."""
    try:
        out = subprocess.check_output(["py", "-0"], text=True, stderr=subprocess.STDOUT)
    except Exception as e:
        log.debug("py -0 failed: %s", e)
        return []
    vers = []
    for line in out.splitlines():
        line = line.strip()
        if not (line.startswith("-V:") or line.startswith("-")):
            continue
        token = line.split()[0]  # '-V:3.14' or '-3.14'
        v = token.replace("-V:", "").replace("-", "")
        if v.startswith("3.") and v.count(".") == 1:
            vers.append(v)
    return vers


def _find_latest_python_executable() -> tuple[list[str], str]:
    """
    Return (cmd_list, '3.X') for the newest Python 3.x:
      - Windows: (['py','-3.16'], '3.16')
      - POSIX:   (['python3.16'], '3.16') or (['python3'], '3.X')
    """
    if IS_WINDOWS:
        versions = _list_pythons_windows()
        if not versions:
            log.error(
                "No Python 3.x installation was found by the Windows 'py' launcher.\n"
                "Install Python 3.14+ from https://www.python.org/downloads/ or the Microsoft Store,\n"
                "ensure the 'py' launcher is installed, and verify with:  py -0"
            )
            sys.exit(1)
        latest = sorted(
            versions, key=lambda s: tuple(map(int, s.split("."))), reverse=True
        )[0]
        return (["py", f"-{latest}"], latest)

    # POSIX
    for minor in range(20, 9, -1):  # 3.20 down to 3.10
        exe = f"python3.{minor}"
        try:
            subprocess.check_call(
                [exe, "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return ([exe], f"3.{minor}")
        except Exception:
            continue
    try:
        subprocess.check_call(
            ["python3", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        out = subprocess.check_output(
            [
                "python3",
                "-c",
                "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')",
            ],
            text=True,
        )
        v = out.strip()
        if not v.startswith("3."):
            raise RuntimeError("python3 is not Python 3")
        return (["python3"], v)
    except Exception:
        log.error(
            "Could not find a usable Python 3 interpreter. Please install Python 3.14 or newer.\n"
            "Ubuntu/Debian:  sudo apt-get install python3\n"
            "macOS (Homebrew):  brew install python"
        )
        sys.exit(1)


def _relaunch_under_latest_python() -> None:
    """If current interpreter isn't newest, relaunch this script under it."""
    latest_cmd, latest_ver = _find_latest_python_executable()
    current_ver = f"{sys.version_info[0]}.{sys.version_info[1]}"
    if current_ver == latest_ver:
        log.info("Using latest Python %s", current_ver)
        return
    cmd = latest_cmd + [__file__] + sys.argv[1:]
    log.info(
        "Re-launching with Python %s: %s",
        latest_ver,
        " ".join(shlex.quote(c) for c in cmd),
    )
    os.execvp(cmd[0], cmd)


# ─────────────────────────────────────────────────────────────────────────────
# Resolve concrete interpreter path & venv helpers
# ─────────────────────────────────────────────────────────────────────────────
def _resolve_python_executable(latest_cmd: list[str]) -> str:
    """Return absolute interpreter path behind latest_cmd (e.g. 'C:\\...\\python.exe')."""
    try:
        exe = subprocess.check_output(
            latest_cmd + ["-c", "import sys; print(sys.executable)"], text=True
        ).strip()
        if not exe:
            raise RuntimeError("Resolved empty sys.executable")
        return exe
    except Exception as e:
        log.error(
            "Failed to resolve Python executable from %s: %s", " ".join(latest_cmd), e
        )
        sys.exit(1)


def _venv_python_version() -> str | None:
    """Return '3.X' from venv's interpreter, or None if unavailable."""
    py = _py_in_venv()
    if not py.exists():
        return None
    try:
        out = subprocess.check_output(
            [
                str(py),
                "-c",
                "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')",
            ],
            text=True,
        ).strip()
        return out
    except Exception:
        return None


def _venv_is_latest(latest_ver: str) -> bool:
    """
    Determine if an existing venv already uses the newest Python version.
    We only short-circuit venv creation if:
      - venv exists AND
      - venv python reports exactly the newest '3.X' AND
      - newest >= 3.14
    """
    if not VENV_DIR.exists():
        return False
    venv_ver = _venv_python_version()
    if not venv_ver:
        return False
    try:
        l_major, l_minor = map(int, latest_ver.split("."))
        v_major, v_minor = map(int, venv_ver.split("."))
    except Exception:
        return False
    return (v_major, v_minor) >= (3, 14) and venv_ver == latest_ver


# ─────────────────────────────────────────────────────────────────────────────
# Venv creation & package install
# ─────────────────────────────────────────────────────────────────────────────
def _create_venv_with(latest_cmd: list[str]) -> None:
    if VENV_DIR.exists():
        try:
            shutil.rmtree(VENV_DIR)
        except PermissionError as e:
            log.error("Failed to remove existing venv: %s", e)
            log.error("Close any processes using 'venv' and retry.")
            sys.exit(1)

    target_exe = _resolve_python_executable(latest_cmd)
    log.info("Creating virtual environment with interpreter: %s", target_exe)

    try:
        subprocess.check_call([target_exe, "-m", "venv", str(VENV_DIR)])
    except subprocess.CalledProcessError as e:
        log.error("Venv creation failed: %s", e)
        log.error(
            "On Windows this can happen if a Store/AppX stub is selected.\n"
            "Install Python from python.org (with the 'py' launcher), then verify with:  py -0"
        )
        sys.exit(1)

    # ensure pip inside venv
    py = _py_in_venv()
    try:
        subprocess.check_call([str(py), "-m", "ensurepip", "--upgrade"])
    except Exception as e:
        log.warning("ensurepip failed: %s", e)


def _install_packages() -> None:
    py = _py_in_venv()
    log.info("Upgrading pip...")
    subprocess.check_call([str(py), "-m", "pip", "install", "--upgrade", "pip"])

    req = Path("requirements.txt")
    if req.exists():
        log.info("Installing packages from requirements.txt...")
        subprocess.check_call(
            [str(py), "-m", "pip", "install", "--upgrade", "-r", str(req)]
        )
    else:
        # minimal defaults if no requirements.txt
        for pkg in ["pytz", "aiofiles", "orjson"]:
            subprocess.check_call([str(py), "-m", "pip", "install", "--upgrade", pkg])

    # keep crypto stack modern (asyncua deps)
    try:
        subprocess.check_call(
            [str(py), "-m", "pip", "install", "--upgrade", "cryptography", "pyOpenSSL"]
        )
    except Exception:
        pass

    # ensure asyncua is new enough; allow pre-releases for future Python support
    # (asyncua added explicit Python 3.14 support in v1.2b1)
    subprocess.check_call(
        [str(py), "-m", "pip", "install", "--upgrade", "--pre", "asyncua>=1.2b1"]
    )


# ─────────────────────────────────────────────────────────────────────────────
# URL handling & client launcher
# ─────────────────────────────────────────────────────────────────────────────
def _validate_url_or_default(url: str | None) -> str:
    DEFAULT_URL = "opc.tcp://localhost:40451"
    if not url:
        log.info("No --url provided. Using default: %s", DEFAULT_URL)
        return DEFAULT_URL
    if url.startswith("opc.tcp://"):
        return url
    log.warning(
        "Invalid OPC UA URL (must start with 'opc.tcp://'). Using default: %s",
        DEFAULT_URL,
    )
    return DEFAULT_URL


def _run_client(url_arg: str, passthrough: list[str] | None) -> None:
    main_file = Path("main.py")
    if not main_file.exists():
        log.error("main.py not found in current directory.")
        sys.exit(1)

    cmd = [str(_py_in_venv()), str(main_file), f"--url={url_arg}"]
    if passthrough:
        cmd.extend(passthrough)

    log.info("Launching IJT Console Client with URL: %s", url_arg)
    subprocess.call(cmd)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main():
    # Ensure we run under the newest Python available (Windows: py; POSIX: python3.X)
    _relaunch_under_latest_python()

    parser = argparse.ArgumentParser()
    parser.add_argument("--url", type=str, help="OPC UA server URL (opc.tcp://...)")
    parser.add_argument("--force", action="store_true", help="Recreate venv")
    parser.add_argument("--clean", action="store_true", help="Remove venv and exit")
    args, unknown = parser.parse_known_args()

    latest_cmd, latest_ver = _find_latest_python_executable()

    # Enforce Python >= 3.14; loud guidance if not satisfied
    try:
        major, minor = map(int, latest_ver.split("."))
    except Exception:
        log.error("Could not parse detected Python version: %s", latest_ver)
        sys.exit(1)

    log.info("Newest Python detected on this system: %s", latest_ver)
    if (major, minor) < (3, 14):
        log.error(
            "\n"
            "=====================================================================\n"
            "  PYTHON 3.14 OR NEWER IS REQUIRED FOR THIS IJT CONSOLE CLIENT\n"
            "=====================================================================\n"
            "Your system only has Python %s installed.\n\n"
            "Please install Python 3.14, 3.15, or newer from:\n"
            "  https://www.python.org/downloads/\n\n"
            "WINDOWS USERS:\n"
            "  1) Install Python 3.14+ (ensure the 'py' launcher is installed)\n"
            "  2) Verify with:  py -0   (the newest should be listed, e.g. '-3.14-64 *')\n\n"
            "After installing Python 3.14+, re-run:\n"
            "  python setup_client.py --force\n"
            "=====================================================================\n",
            latest_ver,
        )
        sys.exit(1)

    # --clean: remove venv and exit
    if args.clean:
        if VENV_DIR.exists():
            log.info("Removing virtual environment...")
            shutil.rmtree(VENV_DIR)
        else:
            log.info("No virtual environment to clean.")
        sys.exit(0)

    # --force: recreate venv unconditionally
    if args.force and VENV_DIR.exists():
        log.info("Force flag set. Removing existing venv...")
        shutil.rmtree(VENV_DIR)

    # If venv exists and already uses the newest Python (>= 3.14), skip creating it
    if _venv_is_latest(latest_ver):
        log.info(
            "Existing virtual environment already uses newest Python %s — skipping venv creation.",
            latest_ver,
        )
    else:
        _create_venv_with(latest_cmd)

    # Always ensure packages are in place/up-to-date
    _install_packages()

    # Decide URL & run client
    url_arg = _validate_url_or_default(args.url)
    _run_client(url_arg, passthrough=unknown)


if __name__ == "__main__":
    main()
