import os
import sys
import subprocess
import venv
import shutil
import logging
import webbrowser
import socket
import argparse
import json
import time
import shlex
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("log.txt", mode="w", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants & Paths
# ---------------------------------------------------------------------------
VENV_DIR = Path("venv")
SETUP_TIMESTAMP_FILE = Path(".setup_timestamp")
IS_WINDOWS = os.name == "nt"


def _semver_tuple(ver: str):
    """
    Convert a version string like '24.11.0' or '20.11.1' to a comparable tuple (24, 11, 0).
    Non-digit parts are ignored; missing parts default to 0.
    """
    nums = [int(x) for x in re.findall(r"\d+", ver)]
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums[:3])


# ---------------------------------------------------------------------------
# Windows/Posix: Find newest Python & relaunch under it (future-proof)
# ---------------------------------------------------------------------------


def _list_pythons_windows():
    """
    Use 'py -0' to list installed Python versions and return a list of '3.X' strings.
    Example lines: ' -V:3.14 *        Python 3.14 (64-bit)' or ' -3.12  Python 3.12 (64-bit)'
    """
    try:
        out = subprocess.check_output(["py", "-0"], text=True, stderr=subprocess.STDOUT)
    except Exception as e:
        log.debug("py -0 failed: %s", e)
        return []
    vers = []
    for line in out.splitlines():
        line = line.strip()
        if not line.startswith("-V:") and not line.startswith("-"):
            continue
        token = line.split()[0]  # '-V:3.14' or '-3.12'
        v = token.replace("-V:", "").replace("-", "")
        if v.startswith("3.") and v.count(".") == 1:
            vers.append(v)
    return vers


def _find_latest_python_executable():
    """
    Return (cmd_list, version_string) for the newest Python 3.x on this system.
    - On Windows: ['py', '-3.16'], '3.16'
    - On POSIX:   ['python3.16'], '3.16' (falls back to python3)
    """
    if IS_WINDOWS:
        versions = _list_pythons_windows()
        if not versions:
            log.error("No Python 3.x found by the Windows 'py' launcher.")
            sys.exit(1)
        latest = sorted(
            versions, key=lambda s: tuple(map(int, s.split("."))), reverse=True
        )[0]
        return (["py", f"-{latest}"], latest)
    else:
        # Probe newer to older (extend upper bound periodically, harmless if missing)
        for minor in range(20, 9, -1):  # 3.20 down to 3.10
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
        # Fallback: python3
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
                raise RuntimeError("python3 isn't a Python 3 interpreter")
            return (["python3"], v)
        except Exception:
            log.error("Could not find a usable Python 3 interpreter on this system.")
            sys.exit(1)


def _relaunch_under_latest_python():
    """
    If current interpreter is not the newest available, re-exec the script under it,
    forwarding all arguments. This guarantees the rest of the script and the venv
    will use the newest Python version on the machine.
    """
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


# ---------------------------------------------------------------------------
# Utility: Internet availability
# ---------------------------------------------------------------------------
def _check_internet(host="8.8.8.8", port=53, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error:
        return False


# ---------------------------------------------------------------------------
# Venv & Python paths
# ---------------------------------------------------------------------------
def _python_in_venv() -> Path:
    return VENV_DIR / ("Scripts/python.exe" if IS_WINDOWS else "bin/python")


def _pip_in_venv() -> Path:
    return VENV_DIR / ("Scripts/pip.exe" if IS_WINDOWS else "bin/pip")


def _get_python_path() -> Path:
    """
    Inside Docker, use system python. Otherwise use venv python.
    """
    if os.getenv("IS_DOCKER") == "true":
        return Path(sys.executable)
    return _python_in_venv()


# ---------------------------------------------------------------------------
# Node / npm / npx helpers
# ---------------------------------------------------------------------------
def _get_npm_path():
    return shutil.which("npm") or VENV_DIR / (
        "Scripts/npm.cmd" if IS_WINDOWS else "bin/npm"
    )


def _get_npx_path():
    return shutil.which("npx") or VENV_DIR / (
        "Scripts/npx.cmd" if IS_WINDOWS else "bin/npx"
    )


def _get_node_version():
    try:
        output = subprocess.check_output(["node", "-v"], text=True).strip()
        return output.lstrip("v")
    except Exception as e:
        log.error("Failed to get Node.js version: %s", e)
        return None


# ---------------------------------------------------------------------------
# Environment age / timestamp
# ---------------------------------------------------------------------------
def _get_environment_age_days():
    try:
        if VENV_DIR.exists():
            creation_time = os.path.getmtime(VENV_DIR)
            return (time.time() - creation_time) / (60 * 60 * 24)
    except Exception as e:
        log.warning("Could not determine environment age: %s", e)
    return None


def _get_last_setup_age_days():
    try:
        if SETUP_TIMESTAMP_FILE.exists():
            timestamp = float(SETUP_TIMESTAMP_FILE.read_text().strip())
            return (time.time() - timestamp) / (60 * 60 * 24)
    except Exception as e:
        log.warning("Could not read setup timestamp: %s", e)
    return None


def _update_setup_timestamp():
    try:
        SETUP_TIMESTAMP_FILE.write_text(str(time.time()))
    except Exception as e:
        log.warning("Could not update setup timestamp: %s", e)


def _resolve_python_executable(latest_cmd):
    """
    Resolve the absolute path to the interpreter behind latest_cmd.
    Example: latest_cmd == ["py", "-3.13"]  -> returns "C:\\...\\python.exe"
             latest_cmd == ["python3.16"]   -> returns "/usr/bin/python3.16"
    """
    try:
        exe = subprocess.check_output(
            latest_cmd + ["-c", "import sys; print(sys.executable)"],
            text=True
        ).strip()
        if not exe:
            raise RuntimeError("Could not resolve target python executable.")
        return exe
    except Exception as e:
        log.error("Failed to resolve Python executable from %s: %s", " ".join(latest_cmd), e)
        sys.exit(1)

# ---------------------------------------------------------------------------
# Python: Create venv with newest interpreter
# ---------------------------------------------------------------------------
def _create_virtualenv(latest_cmd):
    """
    Create venv with the newest Python interpreter.
    - Resolves the real python.exe (or python3.x) behind 'latest_cmd'
    - Calls that interpreter directly for ' -m venv '
    - Gives clear guidance if creation fails (Store / broken association cases)
    """
    if os.getenv("IS_DOCKER") == "true":
        log.info("Docker detected: skipping virtualenv creation.")
        return

    if VENV_DIR.exists():
        try:
            shutil.rmtree(VENV_DIR)
        except PermissionError as e:
            log.error("Failed to delete existing virtualenv: %s", e)
            log.error("Please close any processes using the 'venv' and retry.")
            sys.exit(1)

    target_exe = _resolve_python_executable(latest_cmd)
    log.info("Creating virtual environment with interpreter: %s", target_exe)

    try:
        subprocess.check_call([target_exe, "-m", "venv", str(VENV_DIR)])
    except subprocess.CalledProcessError as e:
        log.error("Venv creation failed with %s", e)
        log.error(
            "This can happen on Windows when the 'py' launcher points to a Store/stub install "
            "or a conflicting association. Please install Python from python.org or the Microsoft Store, "
            "ensure the 'py' launcher is installed, and that 'py -0' lists your interpreter correctly."
        )
        log.error("Tip: run  py -0  to list Pythons; the one with '*' is the default. "
                  "You can also try:  py -3.13 -c \"import sys; print(sys.executable)\"")
        sys.exit(1)

    # Ensure pip inside the new venv
    py = _python_in_venv()
    try:
        subprocess.check_call([str(py), "-m", "ensurepip", "--upgrade"])
    except Exception as e:
        log.warning("Failed to ensure pip in virtualenv: %s", e)


# ---------------------------------------------------------------------------
# Python: Install packages (requirements + asyncua pre-release support)
# ---------------------------------------------------------------------------
def _install_python_packages():
    """
    Install from requirements.txt, then ensure 'asyncua' is upgraded allowing pre-releases.
    (asyncua first shipped explicit Python 3.14 support in v1.2b1; using --pre helps future X.Y)  # noqa
    """
    python = _get_python_path()
    log.info("Using Python executable: %s", python)

    # Upgrade pip first
    subprocess.check_call([str(python), "-m", "pip", "install", "--upgrade", "pip"])

    req_file = Path("requirements.txt")
    if not req_file.exists():
        log.error("requirements.txt not found. Cannot continue.")
        sys.exit(1)

    # Install core from requirements (stable channel)
    log.info("Installing packages from requirements.txt (stable channel)...")
    subprocess.check_call(
        [str(python), "-m", "pip", "install", "--upgrade", "-r", str(req_file)]
    )

    # Proactively upgrade crypto stack for asyncua (often required by newer wheels)
    # (The asyncua project lists cryptography / pyOpenSSL among dependencies.)
    # https://github.com/FreeOpcUa/opcua-asyncio/network/dependencies
    try:
        subprocess.check_call(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--upgrade",
                "cryptography",
                "pyOpenSSL",
            ]
        )
    except Exception:
        pass

    # Finally, allow asyncua pre-releases to support newest Python versions automatically
    log.info(
        "Ensuring asyncua supports the newest Python (allowing pre-releases if needed)..."
    )
    subprocess.check_call(
        [str(python), "-m", "pip", "install", "--upgrade", "--pre", "asyncua>=1.2b1"]
    )


# ---------------------------------------------------------------------------
# Node / npm / npx: checks & install
# ---------------------------------------------------------------------------
def _create_nodeenv():
    """
    Ensure Node.js (node, npm, npx) are present and at/above the required version.
    JS toolchain remains global (unchanged from your workflow).
    """
    log.info("Checking Node.js installation...")
    node_path = shutil.which("node")
    npm_path = shutil.which("npm")
    npx_path = shutil.which("npx")

    missing = []
    if not node_path:
        missing.append("node")
    if not npm_path:
        missing.append("npm")
    if not npx_path:
        missing.append("npx")
    if missing:
        log.error("Missing global tools: %s", ", ".join(missing))
        log.error(
            "Please install Node.js with npm and npx, and ensure they are in your PATH."
        )
        sys.exit(1)

    # quick smoke checks
    try:
        subprocess.check_call([node_path, "-v"])
        subprocess.check_call([npm_path, "-v"])
        subprocess.check_call([npx_path, "--version"])
    except Exception as e:
        log.error("Node.js tools aren't functioning correctly: %s", e)
        sys.exit(1)

    node_ver = _get_node_version() or "0.0.0"
    required_node_ver = os.getenv("NODE_VERSION", "24.11.0")

    if _semver_tuple(node_ver) < _semver_tuple(required_node_ver):
        log.error(
            "Node.js version %s is older than required %s. Please upgrade Node.js.",
            node_ver,
            required_node_ver,
        )
        sys.exit(1)

    log.info("Node.js %s OK (>= %s). npm and npx found.", node_ver, required_node_ver)
    log.info("Using node: %s", node_path)
    log.info("Using npm:  %s", npm_path)
    log.info("Using npx:  %s", npx_path)


def _validate_package_json():
    package_json_path = Path("package.json")
    if not package_json_path.exists():
        log.error("package.json not found.")
        sys.exit(1)
    try:
        with open(package_json_path, "r", encoding="utf-8") as f:
            json.load(f)
        log.info("package.json is valid.")
    except json.JSONDecodeError as e:
        log.error("Invalid package.json: %s", e)
        sys.exit(1)


def _install_js_packages():
    npm = _get_npm_path()
    if not npm or not Path(npm).exists():
        log.error("npm not found. Node.js environment setup failed.")
        sys.exit(1)

    _validate_package_json()

    log.info("Installing JavaScript packages...")
    try:
        if Path("package-lock.json").exists():
            log.info("Found package-lock.json. Running 'npm ci'...")
            subprocess.check_call([str(npm), "ci"])
        else:
            log.warning(
                "package-lock.json not found. Running 'npm install' with --legacy-peer-deps..."
            )
            subprocess.check_call([str(npm), "install", "--legacy-peer-deps"])
    except subprocess.CalledProcessError as e:
        log.error("JavaScript package installation failed. Command failed: %s", e.cmd)
        sys.exit(1)

    # Log a couple of versions to assist troubleshooting
    try:
        eslint_version = subprocess.check_output(
            [str(npm), "list", "eslint", "--depth=0"]
        ).decode()
        neostandard_version = subprocess.check_output(
            [str(npm), "list", "neostandard", "--depth=0"]
        ).decode()
        log.info("Installed ESLint version:\n%s", eslint_version)
        log.info("Installed neostandard version:\n%s", neostandard_version)
    except subprocess.CalledProcessError as e:
        log.warning("Failed to retrieve installed JS package versions: %s", e)


# ---------------------------------------------------------------------------
# Web server & Python process runner
# ---------------------------------------------------------------------------
def _start_server(args):
    npx = _get_npx_path()
    if not Path(npx).exists():
        log.error("npx not found. Please ensure Node.js is installed.")
        sys.exit(1)

    http_port = os.getenv("HTTP_PORT", "3000")
    browser_host = os.getenv("WS_HOST") or socket.gethostbyname(socket.gethostname())
    browser_url = f"http://{browser_host}:{http_port}"

    log.info("Starting local server on %s ...", browser_url)

    try:
        cmd = [
            str(npx),
            "--yes",
            "serve",
            "--listen",
            f"tcp://0.0.0.0:{http_port}",
            "--no-clipboard",
            "--no-request-logging",
        ]
        if args.silent:
            cmd.append("--no-request-logging")

        subprocess.Popen(cmd)

        if os.getenv("IS_DOCKER") != "true":
            webbrowser.open(browser_url)
        else:
            log.info("Skipping browser launch inside Docker.")
    except Exception as e:
        log.error("Failed to start server or open browser: %s", e)


def _run_index():
    python = _get_python_path()
    if Path("index.py").exists():
        try:
            subprocess.Popen([str(python), "index.py"])
        except Exception as e:
            log.error("Failed to run index.py: %s", e)
    else:
        log.warning("index.py not found.")


# ---------------------------------------------------------------------------
# .env template
# ---------------------------------------------------------------------------
def _create_env_template():
    if not Path(".env").exists():
        if Path(".env.example").exists():
            shutil.copy(".env.example", ".env")
            log.info(".env file created from .env.example.")
        else:
            with open(".env.example", "w", encoding="utf-8") as f:
                f.write("# Environment Configuration Example\n\n")
                f.write("# WebSocket Server Port\n")
                f.write("# Default: 8001\n")
                f.write("WS_PORT=8001\n")
            log.info(".env.example created.")


# ---------------------------------------------------------------------------
# Runtime readiness check (reuse your original aging logic)
# ---------------------------------------------------------------------------
def _is_runtime_ready():
    python = _get_python_path()
    npm = _get_npm_path()
    npx = _get_npx_path()

    if not (VENV_DIR.exists() and python.exists() and npm and npx):
        return False

    env_max_age = int(os.getenv("ENV_MAX_AGE_DAYS", "14"))
    age_days = _get_last_setup_age_days()
    if age_days is None:
        age_days = _get_environment_age_days()

    if age_days is not None:
        log.info(
            "Environment last set up %d days ago. Will refresh after %d days.",
            int(age_days),
            env_max_age,
        )
        if age_days > env_max_age:
            log.info(
                "Environment is %d days old (threshold: %d). Triggering full setup.",
                int(age_days),
                env_max_age,
            )
            return False
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    # Always ensure we run under the newest Python available.
    _relaunch_under_latest_python()

    parser = argparse.ArgumentParser(
        description="Setup and run the IJT Web Client environment.",
        epilog=(
            "Default behavior:\n"
            "If the environment is already set up (venv, npm, npx exist), the script runs in "
            "runtime-only mode. Use --force_full to perform full setup regardless."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--force_full", action="store_true", help="Force full setup")
    parser.add_argument(
        "--silent", action="store_true", help="Show only warnings/errors"
    )
    args = parser.parse_args()

    # Fast path: if everything exists and isn't too old, just run.
    if not args.force_full and _is_runtime_ready():
        try:
            from dotenv import load_dotenv
        except Exception:
            # Install python-dotenv into the CONTROLLER interpreter (not venv)
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "--upgrade", "python-dotenv"]
            )
            from dotenv import load_dotenv

        load_dotenv()
        _start_server(args)
        _run_index()
        return

    # Full setup path
    log.info("Starting full project setup...")
    if not _check_internet():
        log.error(
            "No internet connection. Please connect to the internet and try again."
        )
        sys.exit(1)

    latest_cmd, latest_ver = _find_latest_python_executable()
    # --- REQUIRE PYTHON 3.14 OR NEWER -----------------------------------------
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
            "  PYTHON 3.14 OR NEWER IS REQUIRED FOR THIS IJT WEB CLIENT\n"
            "=====================================================================\n"
            "Your system only has Python %s installed.\n\n"
            "Please install Python 3.14, 3.15, or newer from:\n"
            "  https://www.python.org/downloads/\n\n"
            "WINDOWS USERS:\n"
            "  1. Install Python 3.14+ using the official installer.\n"
            "  2. Ensure the 'py' launcher is installed.\n"
            "  3. Verify using:\n"
            "         py -0\n"
            "     You must see something like:\n"
            "         -3.14-64  *\n"
            "     (the * indicates your latest default Python)\n\n"
            "After installing Python 3.14+, re-run:\n"
            "     python setup_project.py --force_full\n"
            "=====================================================================\n"
            , latest_ver
        )
        sys.exit(1)
# --------------------------------------------------------------------------

    if os.getenv("IS_DOCKER") != "true":
        _create_virtualenv(latest_cmd)
        _install_python_packages()

    _create_nodeenv()
    _install_js_packages()
    _create_env_template()

    try:
        from dotenv import load_dotenv
    except Exception:
        # Install python-dotenv into the CONTROLLER interpreter (not venv)
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--upgrade", "python-dotenv"]
        )
        from dotenv import load_dotenv

    load_dotenv()
    _start_server(args)
    _run_index()
    _update_setup_timestamp()
    log.info("Setup complete.")


if __name__ == "__main__":
    main()
