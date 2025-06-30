#!/usr/bin/env python3
import os
import sys
import subprocess
import venv
import shutil
import logging
import webbrowser
import platform
from pathlib import Path
from urllib.request import urlretrieve

if platform.system() == "Windows":
    import winreg

try:
    from dotenv import load_dotenv
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "python-dotenv"])
    from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler("setup.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger()

IS_WINDOWS = platform.system() == "Windows"
VENV_DIR = Path("venv")

def get_python_path():
    return VENV_DIR / ("Scripts/python.exe" if IS_WINDOWS else "bin/python")

def create_virtualenv():
    if VENV_DIR.exists():
        shutil.rmtree(VENV_DIR)
    log.info("Creating virtual environment...")
    venv.create(VENV_DIR, with_pip=True)

def install_python_packages():
    python = get_python_path()
    log.info("Installing Python packages...")
    subprocess.check_call([
        python, "-m", "pip", "install", "--upgrade", "pip",
        "requests", "python-dotenv", "nodeenv"
    ])
    if Path("requirements.txt").exists():
        subprocess.check_call([python, "-m", "pip", "install", "-r", "requirements.txt"])
    subprocess.call([python, "-m", "pip", "install", "websockets", "asyncua"])

def create_nodeenv():
    python = get_python_path()
    log.info("Creating Node.js environment inside venv...")
    has_global_node = shutil.which("node") is not None
    args = [python, "-m", "nodeenv"]
    if has_global_node:
        args.append("-p")
    else:
        log.warning("Global Node.js not found. Falling back to nodeenv without -p.")
    subprocess.check_call(args)
    npm = VENV_DIR / ("Scripts/npm.cmd" if IS_WINDOWS else "bin/npm")
    npx = VENV_DIR / ("Scripts/npx.cmd" if IS_WINDOWS else "bin/npx")
    if not npm.exists() or not npx.exists():
        log.error("npm or npx not found in virtual environment. Node.js setup may have failed.")
        sys.exit(1)

def install_js_packages():
    npm = VENV_DIR / ("Scripts/npm.cmd" if IS_WINDOWS else "bin/npm")
    if not npm.exists():
        log.error("npm not found. Node.js environment setup failed.")
        sys.exit(1)
    log.info("Installing JavaScript packages...")
    if Path("package-lock.json").exists():
        subprocess.check_call([str(npm), "ci"])
    else:
        subprocess.check_call([str(npm), "install"])

def start_server():
    npx = VENV_DIR / ("Scripts/npx.cmd" if IS_WINDOWS else "bin/npx")
    if not npx.exists():
        log.error("npx not found. Please ensure Node.js is installed.")
        sys.exit(1)
    log.info("Starting local server...")
    subprocess.Popen([str(npx), "serve", "-l", "3000"])
    webbrowser.open("http://localhost:3000")

def run_index():
    python = get_python_path()
    if Path("index.py").exists():
        subprocess.Popen([str(python), "index.py"])
    else:
        log.warning("index.py not found.")

def create_env_template():
    if not Path(".env").exists() and Path(".env.example").exists():
        shutil.copy(".env.example", ".env")
        log.info(".env file created from .env.example.")
    elif not Path(".env.example").exists():
        with open(".env.example", "w") as f:
            f.write("# Environment Configuration Example\n\n")
            f.write("# WebSocket Server Port\n")
            f.write("# This is the port on which the WebSocket server will listen for incoming connections.\n")
            f.write("# Default: 8001\n")
            f.write("WS_PORT=8001\n")
        log.info(".env.example created.")

def main():
    log.info("Starting full project setup...")
    create_virtualenv()
    install_python_packages()
    create_nodeenv()
    install_js_packages()
    create_env_template()
    load_dotenv()
    start_server()
    run_index()
    log.info("Setup complete.")

if __name__ == "__main__":
    main()
