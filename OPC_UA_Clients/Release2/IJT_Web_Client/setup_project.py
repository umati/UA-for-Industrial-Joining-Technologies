import os
import sys
import subprocess
import shutil
import logging
import webbrowser
import socket
import argparse
import json
import time
import shlex
import re
import zipfile
from pathlib import Path
from urllib.parse import urlparse

STATE_DIR = Path(".state")
LOGS_DIR = Path("logs")
STATE_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)


def _detect_repo_root(start_dir: Path) -> Path:
    """
    Find monorepo root by looking for both OPC_UA_Clients and OPC_UA_Servers.
    Falls back to start_dir when running from standalone/container layouts.
    """
    for candidate in [start_dir] + list(start_dir.parents):
        if (candidate / "OPC_UA_Clients").exists() and (
            candidate / "OPC_UA_Servers"
        ).exists():
            return candidate
    return start_dir

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOGS_DIR / "setup.log", mode="w", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants & Paths
# ---------------------------------------------------------------------------
IS_DOCKER = os.getenv("IS_DOCKER") == "true"
# Use an in-container venv path to avoid Windows bind-mount conflicts
VENV_DIR = Path("/opt/ijt_venv") if IS_DOCKER else Path("venv")
SETUP_TIMESTAMP_FILE = STATE_DIR / "setup_timestamp"
IS_WINDOWS = os.name == "nt"
PROJECT_DIR = Path(__file__).resolve().parent
REPO_ROOT = _detect_repo_root(PROJECT_DIR)
SIMULATOR_DIR = (
    REPO_ROOT / "OPC_UA_Servers" / "Release2" / "OPC_UA_IJT_Server_Simulator"
)
SIMULATOR_ZIP = (
    REPO_ROOT / "OPC_UA_Servers" / "Release2" / "OPC_UA_IJT_Server_Simulator.zip"
)
SIMULATOR_EXE_NAME = "opcua_ijt_demo_application.exe"


def _run_command(cmd: list[str], check: bool = True, capture_output: bool = False):
    if capture_output:
        return subprocess.check_output(cmd, text=True).strip()
    if check:
        subprocess.check_call(cmd)
        return None
    return subprocess.run(cmd, check=False)


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
        candidates: list[tuple[tuple[int, int], list[str], str]] = []

        for version in versions:
            try:
                major, minor = map(int, version.split("."))
                candidates.append(((major, minor), ["py", f"-{version}"], version))
            except Exception:
                continue

        # Also include the currently running interpreter to avoid downgrading when
        # 'py -0' is stale/misconfigured compared to PATH python.
        current_ver = f"{sys.version_info[0]}.{sys.version_info[1]}"
        candidates.append(
            (
                (sys.version_info[0], sys.version_info[1]),
                [sys.executable],
                current_ver,
            )
        )

        if not candidates:
            log.error("No Python 3.x interpreter candidates found on this system.")
            sys.exit(1)

        _, cmd, version = max(candidates, key=lambda row: row[0])
        if cmd and cmd[0] == "py":
            try:
                major, minor = version.split(".")
                local_appdata = os.getenv("LOCALAPPDATA")
                if local_appdata:
                    direct_py = (
                        Path(local_appdata)
                        / "Programs"
                        / "Python"
                        / f"Python{major}{minor}"
                        / "python.exe"
                    )
                    if direct_py.exists():
                        return ([str(direct_py)], version)
            except Exception:
                pass
        return (cmd, version)
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


def _require_python_314_or_newer(version_string: str | None = None) -> None:
    if version_string:
        try:
            major, minor = map(int, version_string.split("."))
        except Exception:
            major, minor = sys.version_info[0], sys.version_info[1]
    else:
        major, minor = sys.version_info[0], sys.version_info[1]

    if (major, minor) < (3, 14):
        log.error(
            "Python 3.14 or newer is required. Current interpreter: %s.%s",
            major,
            minor,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Utility: Internet availability
# ---------------------------------------------------------------------------
def _check_internet(host="8.8.8.8", port=53, timeout=3):
    sock = None
    try:
        socket.setdefaulttimeout(timeout)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        return True
    except socket.error:
        return False
    finally:
        if sock:
            sock.close()


def _is_port_in_use(host: str, port: int, timeout: float = 0.5) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        return sock.connect_ex((host, port)) == 0
    finally:
        sock.close()


def _parse_endpoint_host_port(endpoint: str) -> tuple[str, int]:
    parsed = urlparse(endpoint)
    host = parsed.hostname or "localhost"
    port = parsed.port or 40451
    return host, port


def _is_endpoint_reachable(endpoint: str, timeout: float = 1.0) -> bool:
    host, port = _parse_endpoint_host_port(endpoint)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        return sock.connect_ex((host, port)) == 0
    finally:
        sock.close()


def _env_float(name: str, default: float, minimum: float) -> float:
    raw = os.getenv(name, str(default))
    try:
        value = float(raw)
    except ValueError:
        log.warning("Invalid %s=%r. Falling back to %.2f.", name, raw, default)
        value = default
    return max(minimum, value)


def _wait_for_endpoint_ready(
    endpoint: str,
    timeout_seconds: float = 45.0,
    poll_interval: float = 0.5,
) -> bool:
    deadline = time.time() + max(1.0, timeout_seconds)
    while time.time() < deadline:
        if _is_endpoint_reachable(endpoint):
            return True
        time.sleep(max(0.1, poll_interval))
    return _is_endpoint_reachable(endpoint)


def _is_simulator_process_running() -> bool:
    if not IS_WINDOWS:
        return False
    try:
        output = subprocess.check_output(
            ["tasklist", "/FI", f"IMAGENAME eq {SIMULATOR_EXE_NAME}"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return SIMULATOR_EXE_NAME.lower() in output.lower()
    except Exception:
        return False


def _extract_simulator_zip_if_needed() -> None:
    if SIMULATOR_DIR.exists() or not SIMULATOR_ZIP.exists():
        return
    try:
        log.info("Extracting OPC UA simulator from ZIP: %s", SIMULATOR_ZIP)
        with zipfile.ZipFile(SIMULATOR_ZIP, "r") as zf:
            zf.extractall(SIMULATOR_ZIP.parent)
    except Exception as e:
        log.warning("Failed to extract simulator ZIP '%s': %s", SIMULATOR_ZIP, e)


def _find_simulator_executable() -> Path | None:
    if not SIMULATOR_DIR.exists():
        return None
    direct = SIMULATOR_DIR / SIMULATOR_EXE_NAME
    if direct.exists():
        return direct
    matches = list(SIMULATOR_DIR.rglob(SIMULATOR_EXE_NAME))
    return matches[0] if matches else None


def _ensure_opc_server_running(
    endpoint: str, *, allow_launch: bool, context: str
) -> bool:
    if _is_endpoint_reachable(endpoint):
        return True

    if allow_launch and not IS_DOCKER:
        _extract_simulator_zip_if_needed()
        exe = _find_simulator_executable()
        if exe:
            if _is_simulator_process_running():
                log.info(
                    "OPC UA simulator is already running. Reusing existing process."
                )
            else:
                try:
                    log.info("Launching OPC UA simulator in separate terminal: %s", exe)
                    popen_kwargs = {"cwd": str(exe.parent)}
                    if IS_WINDOWS:
                        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
                    subprocess.Popen([str(exe)], **popen_kwargs)
                    startup_timeout = _env_float("OPCUA_STARTUP_TIMEOUT_SEC", 45.0, 1.0)
                    startup_poll = _env_float("OPCUA_STARTUP_POLL_SEC", 0.5, 0.1)
                    if _wait_for_endpoint_ready(
                        endpoint,
                        timeout_seconds=startup_timeout,
                        poll_interval=startup_poll,
                    ):
                        log.info("OPC UA endpoint became reachable: %s", endpoint)
                        return True
                    log.warning(
                        "Simulator process launched but endpoint %s was not reachable after %.1fs.",
                        endpoint,
                        startup_timeout,
                    )
                except Exception as e:
                    log.warning("Failed to launch OPC UA simulator '%s': %s", exe, e)
    elif allow_launch and IS_DOCKER:
        log.info(
            "Docker mode detected (IS_DOCKER=true). Skipping local OPC UA simulator launch."
        )

    startup_timeout = _env_float("OPCUA_STARTUP_TIMEOUT_SEC", 45.0, 1.0)
    startup_poll = _env_float("OPCUA_STARTUP_POLL_SEC", 0.5, 0.1)
    if _wait_for_endpoint_ready(
        endpoint,
        timeout_seconds=startup_timeout,
        poll_interval=startup_poll,
    ):
        return True

    log.warning(
        "%s: No OPC UA server is running on %s. "
        "If your server is in a separate download/folder, start it manually before running tests.",
        context,
        endpoint,
    )
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
    # if os.getenv("IS_DOCKER") == "true":
    #     return Path(sys.executable)
    return _python_in_venv()


# ---------------------------------------------------------------------------
# Node / npm / npx helpers
# ---------------------------------------------------------------------------
def _get_npm_path():
    return shutil.which("npm")


def _get_npx_path():
    return shutil.which("npx")


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
            latest_cmd + ["-c", "import sys; print(sys.executable)"], text=True
        ).strip()
        if not exe:
            raise RuntimeError("Could not resolve target python executable.")
        return exe
    except Exception as e:
        log.error(
            "Failed to resolve Python executable from %s: %s", " ".join(latest_cmd), e
        )
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
    # if os.getenv("IS_DOCKER") == "true":
    #     log.info("Docker detected: skipping virtualenv creation.")
    #     return

    # Remove only the selected venv dir (in Docker this is /opt/ijt_venv, not your bind-mount)
    if VENV_DIR.exists():

        def _on_rm_error(func, path, exc_info):
            try:
                os.chmod(path, 0o700)
                func(path)
            except Exception:
                # As a last resort, leave the file in place and continue
                log.warning("Could not remove %s; continuing.", path)

        try:
            shutil.rmtree(VENV_DIR, onerror=_on_rm_error)
        except Exception as e:
            log.warning("Non-fatal: could not fully remove %s: %s", VENV_DIR, e)

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
        log.error(
            "Tip: run  py -0  to list Pythons; the one with '*' is the default. "
            'You can also try:  py -3.13 -c "import sys; print(sys.executable)"'
        )
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
    required_node_ver = os.getenv("NODE_VERSION", "24.0.0")

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
        # utf-8-sig tolerates accidental BOM and keeps parsing stable on Windows editors.
        with open(package_json_path, "r", encoding="utf-8-sig") as f:
            json.load(f)
        log.info("package.json is valid.")
    except json.JSONDecodeError as e:
        log.error("Invalid package.json: %s", e)
        sys.exit(1)


def _install_js_packages():
    npm = _get_npm_path()
    if not npm:
        log.error("npm not found. Node.js environment setup failed.")
        sys.exit(1)

    _validate_package_json()

    log.info("Installing JavaScript packages...")
    try:
        if Path("package-lock.json").exists():
            log.info("Found package-lock.json. Running 'npm ci'...")
            _run_command([str(npm), "ci"])
        else:
            log.warning(
                "package-lock.json not found. Running 'npm install' with --legacy-peer-deps..."
            )
            _run_command([str(npm), "install", "--legacy-peer-deps"])
    except subprocess.CalledProcessError as e:
        log.error("JavaScript package installation failed. Command failed: %s", e.cmd)
        sys.exit(1)

    # Log a couple of versions to assist troubleshooting
    try:
        eslint_version = subprocess.check_output(
            [str(npm), "list", "eslint", "--depth=0"], text=True
        )
        neostandard_version = subprocess.check_output(
            [str(npm), "list", "neostandard", "--depth=0"], text=True
        )
        log.info("Installed ESLint version:\n%s", eslint_version)
        log.info("Installed neostandard version:\n%s", neostandard_version)
    except subprocess.CalledProcessError as e:
        log.warning("Failed to retrieve installed JS package versions: %s", e)


# ---------------------------------------------------------------------------
# Web server & Python process runner
# ---------------------------------------------------------------------------
def _start_server(args):
    npx = _get_npx_path()
    if not npx:
        log.error("npx not found. Please ensure Node.js is installed.")
        sys.exit(1)

    http_port = os.getenv("HTTP_PORT", "3000")
    try:
        port_num = int(http_port)
    except ValueError:
        log.error("Invalid HTTP_PORT '%s'. Falling back to 3000.", http_port)
        port_num = 3000
        http_port = "3000"

    if _is_port_in_use("127.0.0.1", port_num):
        log.info(
            "HTTP port %s is already in use. Skipping frontend start (assumed already running).",
            http_port,
        )
        return

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
    try:
        ws_port = int(os.getenv("WS_PORT", "8001"))
    except ValueError:
        log.error("Invalid WS_PORT value. Falling back to 8001.")
        ws_port = 8001

    if _is_port_in_use("127.0.0.1", ws_port):
        log.info(
            "WebSocket port %s is already in use. Skipping backend start (assumed already running).",
            ws_port,
        )
        return

    if Path("index.py").exists():
        try:
            subprocess.Popen([str(python), "index.py"])
        except Exception as e:
            log.error("Failed to run index.py: %s", e)
    else:
        log.warning("index.py not found.")


def _load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        log.warning("python-dotenv is unavailable in controller interpreter; skipping .env load.")


def _run_tests_in_venv(integration: bool = False) -> None:
    python = _get_python_path()
    marker = "integration" if integration else "not integration"
    endpoint = os.getenv("OPCUA_TEST_ENDPOINT", "opc.tcp://localhost:40451")
    _ensure_opc_server_running(
        endpoint,
        allow_launch=True,
        context="Test pre-check",
    )
    try:
        _run_command([str(python), "-c", "import pytest, pytest_asyncio"])
    except Exception:
        req_dev = Path("requirements-dev.txt")
        if req_dev.exists():
            log.info(
                "Test dependencies missing in venv. Installing from %s ...",
                req_dev,
            )
            _run_command(
                [str(python), "-m", "pip", "install", "--upgrade", "-r", str(req_dev)]
            )
        else:
            log.error(
                "pytest is unavailable in venv and requirements-dev.txt is missing."
            )
            raise
    log.info("Running pytest via venv interpreter (%s), marker: %s", python, marker)
    _run_command([str(python), "-m", "pytest", "tests", "-m", marker])


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

    # Ensure runtime dependencies are present in the selected Python interpreter.
    try:
        _run_command(
            [
                str(python),
                "-c",
                (
                    "import asyncua, websockets, dotenv, requests, packaging, "
                    "pytz, aiofiles"
                ),
            ]
        )
    except Exception:
        log.info(
            "Runtime dependency check failed in %s. Triggering full setup.",
            python,
        )
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
    _require_python_314_or_newer()

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
    parser.add_argument(
        "--run-tests",
        action="store_true",
        help="Run pytest from the project venv after setup/runtime checks.",
    )
    parser.add_argument(
        "--integration-tests",
        action="store_true",
        help="Run integration pytest marker (requires OPCUA_TEST_ENDPOINT).",
    )
    args = parser.parse_args()

    # Fast path: if everything exists and isn't too old, just run.
    if not args.force_full and _is_runtime_ready():
        _load_dotenv_if_available()
        if args.run_tests or args.integration_tests:
            _run_tests_in_venv(integration=args.integration_tests)
            return
        endpoint = os.getenv("OPCUA_TEST_ENDPOINT", "opc.tcp://localhost:40451")
        _ensure_opc_server_running(
            endpoint,
            allow_launch=True,
            context="Startup pre-check",
        )
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
    _require_python_314_or_newer(latest_ver)
    log.info("Newest Python detected on this system: %s", latest_ver)

    # if os.getenv("IS_DOCKER") != "true":
    _create_virtualenv(latest_cmd)
    _install_python_packages()

    _create_nodeenv()
    _install_js_packages()
    _create_env_template()

    _load_dotenv_if_available()
    if args.run_tests or args.integration_tests:
        _run_tests_in_venv(integration=args.integration_tests)
        return
    endpoint = os.getenv("OPCUA_TEST_ENDPOINT", "opc.tcp://localhost:40451")
    _ensure_opc_server_running(
        endpoint,
        allow_launch=True,
        context="Startup pre-check",
    )
    _start_server(args)
    _run_index()
    _update_setup_timestamp()
    log.info("Setup complete.")


if __name__ == "__main__":
    main()
