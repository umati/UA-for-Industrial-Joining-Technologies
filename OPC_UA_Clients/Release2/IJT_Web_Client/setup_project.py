#!/usr/bin/env python3
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
from pathlib import Path

try:
    from packaging import version
except ImportError:
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "--user", "packaging"]
    )
    from packaging import version

try:
    from dotenv import load_dotenv
except ImportError:
    if os.getenv("IS_DOCKER") == "true":
        print("⚠️ Skipping dotenv import check inside Docker.")
    else:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--user", "python-dotenv"]
        )
        from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.FileHandler("log.txt", mode="w"), logging.StreamHandler()],
)
log = logging.getLogger()

VENV_DIR = Path("venv")


def get_environment_age_days():
    try:
        if VENV_DIR.exists():
            creation_time = os.path.getmtime(VENV_DIR)
            age_days = (time.time() - creation_time) / (60 * 60 * 24)
            return age_days
    except Exception as e:
        log.warning("Could not determine environment age: " + str(e))
    return None


SETUP_TIMESTAMP_FILE = Path(".setup_timestamp")


def get_last_setup_age_days():
    """Returns the number of days since the last setup based on the timestamp file."""
    try:
        if SETUP_TIMESTAMP_FILE.exists():
            with open(SETUP_TIMESTAMP_FILE, "r") as f:
                timestamp = float(f.read().strip())
            age_days = (time.time() - timestamp) / (60 * 60 * 24)
            return age_days
    except Exception as e:
        log.warning(f"Could not read setup timestamp file: {e}")
    return None


def update_setup_timestamp():
    """Updates the setup timestamp file with the current time."""
    try:
        with open(SETUP_TIMESTAMP_FILE, "w") as f:
            f.write(str(time.time()))
    except Exception as e:
        log.warning(f"Could not update setup timestamp file: {e}")


def check_python_version():
    if sys.version_info < (3, 8):
        log.error("Python 3.8 or higher is required.")
        sys.exit(1)


def check_internet(host="8.8.8.8", port=53, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error:
        return False


def get_python_path():
    if os.getenv("IS_DOCKER") == "true":
        return Path(sys.executable)  # Use system Python inside Docker
    return VENV_DIR / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def get_npm_path():
    return shutil.which("npm") or VENV_DIR / (
        "Scripts/npm.cmd" if os.name == "nt" else "bin/npm"
    )


def get_npx_path():
    return shutil.which("npx") or VENV_DIR / (
        "Scripts/npx.cmd" if os.name == "nt" else "bin/npx"
    )


def get_node_version():
    try:
        output = subprocess.check_output(["node", "-v"], text=True).strip()
        return output.lstrip("v")
    except Exception as e:
        log.error(f"Failed to get Node.js version: {e}")
        return None


def create_virtualenv():
    if os.getenv("IS_DOCKER") == "true":
        log.info("Skipping virtualenv creation inside Docker.")
        return
    if VENV_DIR.exists():
        try:
            shutil.rmtree(VENV_DIR)
        except PermissionError as e:
            log.error(f"Failed to delete virtual environment: {e}")
            log.error(
                "Please ensure no Python processes are using the virtual environment."
            )
            sys.exit(1)
    log.info("Creating virtual environment...")
    venv.create(VENV_DIR, with_pip=True)
    # Ensure pip is available
    python = get_python_path()
    try:
        subprocess.check_call([str(python), "-m", "ensurepip"])
    except Exception as e:
        log.warning(f"Failed to ensure pip in virtualenv: {e}")


def install_python_packages():
    python = get_python_path()
    log.info(f"Using Python executable: {python}")
    log.info("Installing Python packages...")
    core_packages = [
        "requests",
        "python-dotenv",
        "nodeenv",
        "websockets",
        "asyncua",
        "packaging",
    ]
    try:
        if os.getenv("IS_DOCKER") == "true":
            log.info("Installing Python packages using sys.executable inside Docker...")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "--upgrade", "pip"]
            )
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install"] + core_packages
            )
        else:
            subprocess.check_call(
                [str(python), "-m", "pip", "install", "--upgrade", "pip"]
            )
            subprocess.check_call([str(python), "-m", "pip", "install"] + core_packages)
    except subprocess.CalledProcessError as e:
        log.error("❌ Failed to install core Python packages.")
        log.error(f"Command failed: {e.cmd}")
        sys.exit(1)

    # Optionally install from requirements.txt
    req_file = Path("requirements.txt")
    if req_file.exists():
        log.info("Installing additional packages from requirements.txt...")
        try:
            if os.getenv("IS_DOCKER") == "true":
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "-r", str(req_file)]
                )
            else:
                subprocess.check_call(
                    [str(python), "-m", "pip", "install", "-r", str(req_file)]
                )
        except subprocess.CalledProcessError as e:
            log.error("❌ Failed to install packages from requirements.txt.")
            log.error(f"Command failed: {e.cmd}")
            sys.exit(1)
    else:
        log.warning(
            "requirements.txt not found. Skipping additional package installation."
        )


def create_nodeenv():
    log.info("Creating Node.js environment...")

    # Sanity check: verify Node.js tools are available
    log.info("Checking Node.js installation...")
    node_path = shutil.which("node")
    npm_path = shutil.which("npm")
    npx_path = shutil.which("npx")

    if not node_path or not npm_path or not npx_path:
        missing = []
        if not node_path:
            missing.append("node")
        if not npm_path:
            missing.append("npm")
        if not npx_path:
            missing.append("npx")
        log.error(f"Missing global tools: {', '.join(missing)}")
        log.error(
            "Please install Node.js with npm and npx, or ensure they are in your system PATH."
        )
        sys.exit(1)

    try:
        subprocess.check_call([node_path, "-v"])
        subprocess.check_call([npm_path, "-v"])
        subprocess.check_call([npx_path, "--version"])
    except Exception as e:
        log.error("Node.js tools are not functioning correctly.")
        log.error(str(e))
        sys.exit(1)

    node_ver = get_node_version()
    required_node_version = os.getenv("NODE_VERSION", "24.11.0")

    log.info("Global Node.js installation detected. Skipping nodeenv setup.")
    log.info(f"Using Node.js from: {node_path}")
    log.info(f"Using npm from: {npm_path}")
    log.info(f"Using npx from: {npx_path}")

    if node_ver and version.parse(node_ver) < version.parse(required_node_version):
        log.error(
            f"❌ Node.js version {node_ver} is older than required {required_node_version}. Please upgrade Node.js."
        )
        sys.exit(1)
    else:
        log.info(f"Node.js version {node_ver} meets the minimum requirement.")


def validate_package_json():
    package_json_path = Path("package.json")
    if not package_json_path.exists():
        log.error("package.json not found.")
        sys.exit(1)
    try:
        with open(package_json_path, "r", encoding="utf-8") as f:
            json.load(f)
        log.info("package.json is valid.")
    except json.JSONDecodeError as e:
        log.error(f"Invalid package.json: {e}")
        sys.exit(1)


def install_js_packages():
    npm = get_npm_path()
    if not npm or not Path(npm).exists():
        log.error("npm not found. Node.js environment setup failed.")
        sys.exit(1)

    validate_package_json()

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
        log.error("JavaScript package installation failed. Please check npm logs.")
        log.error(f"Command failed: {e.cmd}")
        sys.exit(1)

    # Log installed versions
    try:
        eslint_version = subprocess.check_output(
            [str(npm), "list", "eslint", "--depth=0"]
        ).decode()
        neostandard_version = subprocess.check_output(
            [str(npm), "list", "neostandard", "--depth=0"]
        ).decode()
        log.info("Installed ESLint version:\n" + eslint_version)
        log.info("Installed neostandard version:\n" + neostandard_version)
    except subprocess.CalledProcessError as e:
        log.warning("Failed to retrieve installed package versions.")
        log.warning(str(e))


def start_server(args):
    npx = get_npx_path()
    if not Path(npx).exists():
        log.error("npx not found. Please ensure Node.js is installed.")
        sys.exit(1)

    http_port = os.getenv("HTTP_PORT", "3000")
    browser_host = os.getenv("WS_HOST") or socket.gethostbyname(socket.gethostname())
    browser_url = f"http://{browser_host}:{http_port}"

    log.info(f"Starting local server on {browser_url} ...")

    try:
        # Base command
        cmd = [
            str(npx),
            "serve",
            "--listen",
            f"tcp://0.0.0.0:{http_port}",
            "--no-clipboard",  # Avoid extra clipboard messages
        ]

        # Suppress request logs if silent mode is enabled
        if args.silent:
            cmd.append("--no-request-logging")

        subprocess.Popen(cmd)

        # Open browser only if not running inside Docker
        if os.getenv("IS_DOCKER") != "true":
            webbrowser.open(browser_url)
        else:
            log.info("Skipping browser launch inside Docker.")
    except Exception as e:
        log.error("Failed to start server or open browser.")
        log.error(str(e))


def run_index():
    python = get_python_path()
    if Path("index.py").exists():
        try:
            subprocess.Popen([str(python), "index.py"])
        except Exception as e:
            log.error("Failed to run index.py")
            log.error(str(e))
    else:
        log.warning("index.py not found.")


def create_env_template():
    if not Path(".env").exists():
        if Path(".env.example").exists():
            shutil.copy(".env.example", ".env")
            log.info(".env file created from .env.example.")
        else:
            with open(".env.example", "w") as f:
                f.write("# Environment Configuration Example\n\n")
                f.write("# WebSocket Server Port\n")
                f.write(
                    "# This is the port on which the WebSocket server will listen for incoming connections.\n"
                )
                f.write("# Default: 8001\n")
                f.write("WS_PORT=8001\n")
            log.info(".env.example created.")


def is_runtime_ready():
    python = get_python_path()
    npm = get_npm_path()
    npx = get_npx_path()

    if not (
        VENV_DIR.exists()
        and python.exists()
        and Path(npm).exists()
        and Path(npx).exists()
    ):
        return False

    env_max_age = int(
        os.getenv("ENV_MAX_AGE_DAYS", "14")
    )  # Default to 14 days if not set

    # Prefer setup timestamp if available
    age_days = get_last_setup_age_days()
    source = ".setup_timestamp"

    # Fallback to venv modification time if timestamp is missing
    if age_days is None:
        age_days = get_environment_age_days()
        source = "venv directory"

    if age_days is not None:
        log.info(
            f"Environment was last set up {int(age_days)} days ago (based on {source}). "
            f"It will be refreshed after {env_max_age} days."
        )
        if age_days > env_max_age:
            log.info(
                f"Environment is {int(age_days)} days old (threshold: {env_max_age}). "
                "Triggering full setup for updates."
            )
            return False

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Setup and run the IJT Web Client environment.",
        epilog="""Default behavior:
 If the environment is already set up (venv, npm, npx exist), the script runs in runtime-only mode.
 Use --force_full to override and perform full setup regardless of environment state.
""",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "--force_full",
        action="store_true",
        help="Force full setup even if environment is already prepared",
    )

    parser.add_argument(
        "--silent",
        action="store_true",
        help="Suppress info logs and only show warnings/errors",
    )

    args = parser.parse_args()

    log_level = logging.WARNING if args.silent else logging.INFO
    logging.getLogger().setLevel(log_level)

    if not args.force_full and is_runtime_ready():
        log.info("Detected existing environment. Running runtime-only setup...")
        load_dotenv()
        start_server(args)
        run_index()
    else:
        log.info("Starting full project setup...")
        check_python_version()
        if not check_internet():
            log.error(
                "No internet connection. Please connect to the internet and try again."
            )
            sys.exit(1)
        if os.getenv("IS_DOCKER") != "true":
            create_virtualenv()
            install_python_packages()
            create_nodeenv()
            install_js_packages()
            create_env_template()
        load_dotenv()
        start_server(args)
        run_index()
        log.info("Setup complete.")
        update_setup_timestamp()


if __name__ == "__main__":
    main()
