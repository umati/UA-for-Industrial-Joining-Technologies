import argparse
import contextlib
import logging
import os
import shlex

# Suppress __pycache__ / .pyc generation — matches Docker/CI behavior
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
import shutil
import socket
import subprocess  # nosec B404
import sys
import time
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def _detect_repo_root(start_dir: Path) -> Path:
    """
    Find repository root by looking for both OPC_UA_Clients and OPC_UA_Servers.
    Falls back to start_dir when running from standalone/container layouts.
    """
    for candidate in [start_dir] + list(start_dir.parents):
        if (candidate / "OPC_UA_Clients").exists() and (candidate / "OPC_UA_Servers").exists():
            return candidate
    return start_dir


logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger(__name__)

VENV_DIR = Path(".venv")  # Runtime venv — launch only (requirements.txt)
STATE_DIR = Path(".state")  # Persistent local state — gitignored, never committed
SETUP_TIMESTAMP_FILE = STATE_DIR / "setup_timestamp"  # Matches Web Client convention
IS_WINDOWS = os.name == "nt"
IS_DOCKER = os.getenv("IS_DOCKER") == "true"
PROJECT_DIR = Path(__file__).resolve().parent
REPO_ROOT = _detect_repo_root(PROJECT_DIR)
SIMULATOR_DIR = REPO_ROOT / "OPC_UA_Servers" / "Release2" / "OPC_UA_IJT_Server_Simulator"
SIMULATOR_ZIP = REPO_ROOT / "OPC_UA_Servers" / "Release2" / "OPC_UA_IJT_Server_Simulator.zip"
SIMULATOR_EXE_NAME = "opcua_ijt_demo_application.exe"

# Legacy venv directory names that pre-date the .venv / .venv_test convention.
# Detected and removed automatically so users who pull fresh code do not keep
# orphaned, potentially-conflicting environments on disk.
_STALE_VENV_NAMES: tuple[str, ...] = ("venv", "venv_test", "env", "ENV", ".venv_backup")


def _remove_stale_venvs(project_dir: Path) -> None:
    """Delete any legacy virtual-environment directories under *project_dir*.

    Only ``.venv`` (runtime) and ``.venv_test`` are canonical on all hosts.
    Anything matching :data:`_STALE_VENV_NAMES` is removed automatically so
    that fresh clones start from a known-clean state.
    """
    for name in _STALE_VENV_NAMES:
        stale = project_dir / name
        if stale.is_dir():
            log.info("[cleanup] Removing stale virtual environment: %s", stale)
            shutil.rmtree(stale, ignore_errors=True)


def _force_rmtree(path: Path) -> None:
    """Remove a directory tree, handling Windows read-only / locked files."""
    import stat as _stat

    def _on_exc(func, fpath, exc):
        try:
            os.chmod(fpath, _stat.S_IWRITE)
            func(fpath)
        except OSError:
            time.sleep(0.05)
            with contextlib.suppress(OSError):
                func(fpath)

    shutil.rmtree(path, onexc=_on_exc)


def _cleanup_local_project_artifacts(project_dir: Path) -> None:
    """Remove safe transient cache artifacts under the local project only.

    This is intentionally narrow and never touches virtual environments,
    reports, logs, or runtime state folders.
    """
    skip_dirs = {"node_modules", ".git", "test-results", "logs", ".state", "tmp"}
    cache_dirs = {"__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"}
    for dirpath, dirs, files in os.walk(project_dir, topdown=True):
        dirs[:] = [d for d in dirs if d not in skip_dirs and not (d.startswith(".venv") or d.startswith("venv"))]
        for d in list(dirs):
            if d in cache_dirs:
                _force_rmtree(Path(dirpath) / d)
                dirs.remove(d)
        for f in files:
            if f == ".coverage" or f.startswith(".coverage.") or f.endswith(".pyc"):
                with contextlib.suppress(OSError):
                    (Path(dirpath) / f).unlink(missing_ok=True)
    # Clean transient pip temp dir created by venv_bootstrap
    state_tmp = project_dir / STATE_DIR / "tmp"
    if state_tmp.exists():
        _force_rmtree(state_tmp)


def _python_in_venv() -> Path:
    return VENV_DIR / ("Scripts/python.exe" if IS_WINDOWS else "bin/python")


def _run_command(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess | None:
    if check:
        # safe: cmd is a hardcoded list assembled by this setup script, not user input.
        subprocess.check_call(cmd)  # nosec B603
        return None
    # safe: cmd is a hardcoded list assembled by this setup script, not user input.
    return subprocess.run(cmd, check=False)  # nosec B603


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _list_pythons_windows() -> list[str]:
    try:
        # safe: fixed Windows Python launcher command, no user-controlled input.
        out = subprocess.check_output(["py", "-0"], text=True, stderr=subprocess.STDOUT)  # nosec B603 B607
    except Exception as exc:
        log.debug("py -0 failed: %s", exc)
        return []

    versions: list[str] = []
    for line in out.splitlines():
        line = line.strip()
        if not line.startswith("-V:") and not line.startswith("-"):
            continue
        token = line.split()[0]
        version = token.replace("-V:", "").replace("-", "")
        if version.startswith("3.") and version.count(".") == 1:
            versions.append(version)
    return versions


def _find_latest_python_executable() -> tuple[list[str], str]:
    if IS_WINDOWS:
        candidates: list[tuple[tuple[int, int], list[str], str]] = []
        for version in _list_pythons_windows():
            try:
                major, minor = map(int, version.split("."))
                candidates.append(((major, minor), ["py", f"-{version}"], version))
            except ValueError as exc:
                log.debug("Skipping Python version '%s': %s", version, exc)
        _cur_ver = f"{sys.version_info[0]}.{sys.version_info[1]}"
        candidates.append(((sys.version_info[0], sys.version_info[1]), [sys.executable], _cur_ver))

        if not candidates:
            log.error("Could not find any Python 3.x interpreter.")
            sys.exit(1)

        _, cmd, version = max(candidates, key=lambda row: row[0])
        return (cmd, version)

    for minor in range(20, 9, -1):
        exe = f"python3.{minor}"
        try:
            # safe: fixed interpreter probe command, no user-controlled input.
            subprocess.check_call([exe, "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # nosec B603
            return ([exe], f"3.{minor}")
        except (OSError, subprocess.CalledProcessError) as exc:
            log.debug("Skipping Python executable '%s': %s", exe, exc)

    try:
        # safe: fixed interpreter probe command, no user-controlled input.
        subprocess.check_call(
            ["python3", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )  # nosec B603 B607
        # safe: fixed interpreter version command, no user-controlled input.
        version = subprocess.check_output(  # nosec B603 B607
            [
                "python3",
                "-c",
                "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')",
            ],
            text=True,
        ).strip()
        return (["python3"], version)
    except Exception:
        log.error("Could not find a usable Python 3 interpreter.")
        sys.exit(1)


def _relaunch_under_latest_python() -> None:
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
    # safe: cmd[0] is a Python interpreter path selected by this setup script.
    os.execvp(cmd[0], cmd)  # nosec B606


def _require_python_314_or_newer(version_string: str | None = None) -> None:
    if version_string:
        try:
            major, minor = map(int, version_string.split("."))
        except Exception:
            major, minor = sys.version_info[0], sys.version_info[1]
    else:
        major, minor = sys.version_info[0], sys.version_info[1]

    if (major, minor) < (3, 14):
        log.error("Python 3.14 or newer is required. Current interpreter: %s.%s", major, minor)
        sys.exit(1)


def _warn_if_untested_python(version_string: str | None = None) -> None:
    if not version_string:
        version_string = f"{sys.version_info[0]}.{sys.version_info[1]}"
    try:
        major, minor = map(int, version_string.split("."))
    except Exception:  # noqa: BLE001 — invalid version string format; skip version check
        return

    tested_max_minor_raw = os.getenv("PYTHON_TESTED_MAX_MINOR", "14").strip()
    try:
        tested_max_minor = int(tested_max_minor_raw)
    except Exception:
        log.warning(
            "Invalid PYTHON_TESTED_MAX_MINOR=%r. Expected integer (e.g. 14).",
            tested_max_minor_raw,
        )
        return

    if major == 3 and minor > tested_max_minor:
        log.warning(
            "Python %s detected. This project officially tests up to 3.%s; continuing in compatibility mode.",
            version_string,
            tested_max_minor,
        )


def _resolve_python_executable(latest_cmd: list[str]) -> str:
    try:
        # safe: fixed Python launcher resolution command, no shell string.
        exe = subprocess.check_output(  # nosec B603
            latest_cmd + ["-c", "import sys; print(sys.executable)"],
            text=True,
        ).strip()
    except Exception as exc:
        log.error("Failed to resolve Python executable from %s: %s", " ".join(latest_cmd), exc)
        sys.exit(1)

    if not exe:
        log.error("Resolved empty Python executable path.")
        sys.exit(1)
    return exe


def _check_internet(host: str = "8.8.8.8", port: int = 53, timeout: float = 3.0) -> bool:
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
        # safe: fixed tasklist query for the simulator executable name.
        output = subprocess.check_output(  # nosec B603 B607
            ["tasklist", "/FI", f"IMAGENAME eq {SIMULATOR_EXE_NAME}"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return SIMULATOR_EXE_NAME.lower() in output.lower()
    except Exception:  # noqa: BLE001 — tasklist call failed (non-Windows, access denied); assume not running
        return False


def _extract_simulator_zip_if_needed() -> None:
    if SIMULATOR_DIR.exists() or not SIMULATOR_ZIP.exists():
        return
    try:
        log.info("Extracting OPC UA simulator from ZIP: %s", SIMULATOR_ZIP)
        with zipfile.ZipFile(SIMULATOR_ZIP, "r") as zf:
            zf.extractall(SIMULATOR_ZIP.parent)
    except Exception as exc:
        log.warning("Failed to extract simulator ZIP '%s': %s", SIMULATOR_ZIP, exc)


def _find_simulator_executable() -> Path | None:
    if not SIMULATOR_DIR.exists():
        return None
    direct = SIMULATOR_DIR / SIMULATOR_EXE_NAME
    if direct.exists():
        return direct
    matches = list(SIMULATOR_DIR.rglob(SIMULATOR_EXE_NAME))
    return matches[0] if matches else None


def _ensure_opc_server_running(endpoint: str, *, context: str, allow_launch: bool = True) -> bool:
    startup_timeout = _env_float("OPCUA_STARTUP_TIMEOUT_SEC", 45.0, 1.0)
    startup_poll = _env_float("OPCUA_STARTUP_POLL_SEC", 0.5, 0.1)
    if _wait_for_endpoint_ready(
        endpoint,
        timeout_seconds=startup_timeout,
        poll_interval=startup_poll,
    ):
        return True

    if allow_launch and not IS_DOCKER:
        _extract_simulator_zip_if_needed()
        exe = _find_simulator_executable()
        if exe:
            if _is_simulator_process_running():
                log.info("OPC UA simulator is already running. Reusing existing process.")
            else:
                try:
                    log.info("Launching OPC UA simulator in separate terminal: %s", exe)
                    popen_kwargs: dict[str, Any] = {"cwd": str(exe.parent)}
                    if IS_WINDOWS:
                        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE  # type: ignore[attr-defined]
                    # safe: exe is selected from the unpacked simulator package path, not user input.
                    proc = subprocess.Popen([str(exe)], **popen_kwargs)  # nosec B603  # pylint: disable=consider-using-with
                    log.info("Launched OPC UA simulator with PID: %d", proc.pid)
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
                except Exception as exc:
                    log.warning("Failed to launch OPC UA simulator '%s': %s", exe, exc)

    if allow_launch and IS_DOCKER:
        log.info("Docker mode detected (IS_DOCKER=true). Skipping local OPC UA simulator launch.")

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


def _get_environment_age_days() -> float | None:
    try:
        if VENV_DIR.exists():
            return (time.time() - os.path.getmtime(VENV_DIR)) / (60 * 60 * 24)
    except Exception as exc:
        log.warning("Could not determine environment age: %s", exc)
    return None


def _get_last_setup_age_days() -> float | None:
    try:
        # Migrate legacy root-level .setup_timestamp to .state/setup_timestamp on first read.
        legacy = Path(".setup_timestamp")
        if legacy.exists() and not SETUP_TIMESTAMP_FILE.exists():
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            legacy.replace(SETUP_TIMESTAMP_FILE)
        elif legacy.exists():
            legacy.unlink(missing_ok=True)  # Both exist — remove stale root copy
        if SETUP_TIMESTAMP_FILE.exists():
            stamp = float(SETUP_TIMESTAMP_FILE.read_text(encoding="utf-8").strip())
            return (time.time() - stamp) / (60 * 60 * 24)
    except Exception as exc:
        log.warning("Could not read setup timestamp: %s", exc)
    return None


def _update_setup_timestamp() -> None:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        SETUP_TIMESTAMP_FILE.write_text(str(time.time()), encoding="utf-8")
    except Exception as exc:
        log.warning("Could not update setup timestamp: %s", exc)


def _create_virtualenv(latest_cmd: list[str]) -> None:
    if VENV_DIR.exists():

        def _on_rm_error(func, path, _exc):
            try:
                os.chmod(path, 0o700)
                func(path)
            except Exception:
                log.warning("Could not remove %s; continuing.", path)

        try:
            shutil.rmtree(VENV_DIR, onexc=_on_rm_error)
        except Exception as exc:
            log.warning("Non-fatal: could not fully remove %s: %s", VENV_DIR, exc)

    target_exe = _resolve_python_executable(latest_cmd)
    log.info("Creating virtual environment with interpreter: %s", target_exe)

    try:
        # safe: fixed venv creation command using the interpreter selected by this setup script.
        subprocess.check_call([target_exe, "-m", "venv", "--without-pip", str(VENV_DIR)])  # nosec B603
    except subprocess.CalledProcessError as exc:
        log.error("Venv creation failed: %s", exc)
        sys.exit(1)

    try:
        tmp_dir = STATE_DIR / "tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["TMPDIR"] = str(tmp_dir)
        env["TEMP"] = str(tmp_dir)
        env["TMP"] = str(tmp_dir)
        # safe: fixed ensurepip command using this project's virtual environment.
        subprocess.check_call(  # nosec B603
            [str(_python_in_venv()), "-m", "ensurepip", "--upgrade"],
            env=env,
        )
    except Exception as exc:
        log.warning("Failed to ensure pip in virtualenv via ensurepip: %s", exc)
        # safe: fixed pip bootstrap fallback command using this project's virtual environment.
        subprocess.check_call(  # nosec B603
            [
                sys.executable,
                "-m",
                "pip",
                "--python",
                str(_python_in_venv()),
                "install",
                "--upgrade",
                "pip",
            ]
        )


def _install_python_packages() -> None:
    python = _python_in_venv()
    req_file = Path("requirements.txt")

    if not req_file.exists():
        log.error("requirements.txt not found. Cannot continue.")
        sys.exit(1)

    log.info("Using Python executable: %s", python)
    # safe: fixed pip command using this project's virtual environment.
    subprocess.check_call([str(python), "-m", "pip", "install", "--upgrade", "pip"])  # nosec B603
    # safe: requirements.txt path is fixed to this project directory.
    subprocess.check_call([str(python), "-m", "pip", "install", "--upgrade", "-r", str(req_file)])  # nosec B603

    try:
        # safe: fixed optional crypto package upgrade command.
        subprocess.check_call(  # nosec B603
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
    except Exception as exc:
        log.debug("Optional crypto stack upgrade skipped: %s", exc)

    asyncua_spec = os.getenv("ASYNCUA_VERSION_SPEC", "asyncua>=1.2b2").strip()
    # asyncua 1.2b2+ is required for Python 3.14 support. Always install with --pre so pip
    # can find the current pre-release. --pre does NOT force a pre-release: once asyncua
    # 1.2.x stable is published, pip automatically picks that as the highest matching version.
    log.info("Installing asyncua (--pre enabled for 1.2b2+ / Python 3.14): %s", asyncua_spec)
    # safe: asyncua version spec comes from a dedicated package-spec env var, not a shell string.
    subprocess.check_call(  # nosec B603
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--upgrade",
            "--pre",
            asyncua_spec,
        ]
    )

    # Verify the installed asyncua satisfies the minimum version.
    try:
        # safe: fixed Python one-liner running inside this project's virtual environment.
        installed = subprocess.check_output(  # nosec B603
            [str(python), "-c", "import asyncua; print(asyncua.__version__)"],
            text=True,
        ).strip()
        log.info("asyncua installed version: %s", installed)
        from packaging.version import Version

        if Version(installed) < Version("1.2b2"):
            log.error(
                "asyncua %s is too old for Python 3.14. Minimum required: 1.2b2. "
                "Run setup_client.py --force_full for a clean reinstall.",
                installed,
            )
            sys.exit(1)
    except Exception as exc:
        log.warning("Could not verify asyncua version: %s", exc)


def _is_runtime_ready() -> bool:
    python = _python_in_venv()
    if not (VENV_DIR.exists() and python.exists()):
        return False

    _dep_check_cmd = (
        "import asyncua, sys; "
        "from packaging.version import Version; "
        "v = asyncua.__version__; "
        "sys.exit(0) if Version(v) >= Version('1.2b2') "
        "else sys.exit('asyncua ' + v + ' is too old; need >= 1.2b2')"
    )
    try:
        _run_command([str(python), "-c", _dep_check_cmd])
    except Exception:
        log.info("Runtime dependency check failed in %s. Triggering full setup.", python)
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


def _validate_url_or_default(url: str | None) -> str:
    default_url = "opc.tcp://localhost:40451"
    if not url:
        log.info("No --url provided. Using default: %s", default_url)
        return default_url
    if url.startswith("opc.tcp://"):
        return url

    log.warning(
        "Invalid OPC UA URL (must start with 'opc.tcp://'). Using default: %s",
        default_url,
    )
    return default_url


def _run_client(url_arg: str, passthrough: list[str] | None) -> None:
    main_file = Path("main.py")
    if not main_file.exists():
        log.error("main.py not found in current directory.")
        sys.exit(1)

    cmd = [str(_python_in_venv()), str(main_file), f"--url={url_arg}"]
    if passthrough:
        cmd.extend(passthrough)

    log.info("Launching IJT Console Client with URL: %s", url_arg)
    try:
        # safe: cmd is a fixed Python entry point plus an OPC UA URL argument, never a shell string.
        subprocess.call(cmd)  # nosec B603
    except KeyboardInterrupt:
        log.info("KeyboardInterrupt received in setup wrapper while waiting for console client. Exiting cleanly.")


def main() -> None:
    _relaunch_under_latest_python()
    _require_python_314_or_newer()
    _warn_if_untested_python()

    parser = argparse.ArgumentParser(description="Setup and run IJT Console Client.")
    parser.add_argument("--url", type=str, help="OPC UA server URL (opc.tcp://...)")
    parser.add_argument("--force", action="store_true", help="Force full setup")
    parser.add_argument("--force_full", action="store_true", help="Force full setup")
    parser.add_argument("--clean", action="store_true", help="Remove .venv and exit")
    args, unknown = parser.parse_known_args()

    latest_cmd, latest_ver = _find_latest_python_executable()
    _require_python_314_or_newer(latest_ver)
    _warn_if_untested_python(latest_ver)

    # Remove any stale legacy venv directories left from previous naming conventions.
    _remove_stale_venvs(PROJECT_DIR)
    _cleanup_local_project_artifacts(PROJECT_DIR)

    if args.clean:
        if VENV_DIR.exists():
            log.info("Removing virtual environment...")
            shutil.rmtree(VENV_DIR)
        else:
            log.info("No virtual environment to clean.")
        return

    force_full = args.force or args.force_full

    if not force_full and _is_runtime_ready():
        url_arg = _validate_url_or_default(args.url)
        _ensure_opc_server_running(url_arg, context="Startup pre-check", allow_launch=True)
        _run_client(url_arg, passthrough=unknown)
        return

    log.info("Starting full client setup...")
    if not _check_internet():
        log.error("No internet connection. Please connect to the internet and try again.")
        sys.exit(1)

    log.info("Newest Python detected on this system: %s", latest_ver)
    _create_virtualenv(latest_cmd)
    _install_python_packages()
    _update_setup_timestamp()

    url_arg = _validate_url_or_default(args.url)
    _ensure_opc_server_running(url_arg, context="Startup pre-check", allow_launch=True)
    _run_client(url_arg, passthrough=unknown)


if __name__ == "__main__":
    main()
