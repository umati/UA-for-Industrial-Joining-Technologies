#!/usr/bin/env python3
import os
import sys
import subprocess
import venv
import shutil
import logging
import webbrowser
import socket
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "python-dotenv"])
    from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler("log.txt", mode='w'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger()

VENV_DIR = Path("venv")

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
    return VENV_DIR / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

def get_npm_path():
    return VENV_DIR / ("Scripts/npm.cmd" if os.name == "nt" else "bin/npm")

def get_npx_path():
    return VENV_DIR / ("Scripts/npx.cmd" if os.name == "nt" else "bin/npx")

def create_virtualenv():
    if VENV_DIR.exists():
        shutil.rmtree(VENV_DIR)
    log.info("Creating virtual environment...")
    venv.create(VENV_DIR, with_pip=True)

def install_python_packages():
    python = get_python_path()
    log.info("Installing Python packages...")
    subprocess.check_call([python, "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.check_call([python, "-m", "pip", "install", "requests", "python-dotenv", "nodeenv"])
    if Path("requirements.txt").exists():
        subprocess.check_call([python, "-m", "pip", "install", "-r", "requirements.txt"])
    subprocess.check_call([python, "-m", "pip", "install", "websockets", "asyncua"])

def create_nodeenv():
    python = get_python_path()
    log.info("Creating Node.js environment inside venv...")
    has_global_node = shutil.which("node") is not None
    args = [python, "-m", "nodeenv"]
    if has_global_node:
        args.append("-p")
    else:
        log.warning("Global Node.js not found. Falling back to nodeenv without -p.")
    try:
        subprocess.check_call(args)
    except subprocess.CalledProcessError:
        log.error("Node.js environment setup failed. Please ensure nodeenv can download Node.js or install Node.js globally.")
        sys.exit(1)

    npm = get_npm_path()
    npx = get_npx_path()
    if not npm.exists() or not npx.exists():
        log.error("npm or npx not found in virtual environment. Node.js setup may have failed.")
        sys.exit(1)

def install_js_packages():
    npm = get_npm_path()
    if not npm.exists():
        log.error("npm not found. Node.js environment setup failed.")
        sys.exit(1)

    log.info("Installing JavaScript packages...")

    try:
        if Path("package-lock.json").exists():
            log.info("Found package-lock.json. Running 'npm ci'...")
            subprocess.check_call([str(npm), "ci"])
        else:
            log.warning("package-lock.json not found. Running 'npm install' instead...")
            subprocess.check_call([str(npm), "install"])
    except subprocess.CalledProcessError as e:
        log.error("JavaScript package installation failed. Please check npm logs.")
        log.error(f"Command failed: {e.cmd}")
        sys.exit(1)

def start_server():
    npx = get_npx_path()
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
    check_python_version()
    if not check_internet():
        log.error("No internet connection. Please connect to the internet and try again.")
        sys.exit(1)
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
