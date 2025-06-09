#!/usr/bin/env python3
import os
import subprocess
import sys
import venv
import shutil
import logging
import argparse
import webbrowser
import urllib.request
import zipfile

try:
    from dotenv import load_dotenv
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "python-dotenv"])
    from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("setup.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger()

NVM_NOINSTALL_URL = "https://github.com/coreybutler/nvm-windows/releases/download/1.1.8/nvm-noinstall.zip"
NVM_NOINSTALL_PATH = "nvm-noinstall.zip"
NVM_DIR = ".nvm"
DEFAULT_NODE_VERSION = "20.11.1"

def is_virtualenv_broken(env_dir="venv"):
    return not os.path.exists(os.path.join(env_dir, "pyvenv.cfg"))

def create_virtualenv(env_dir="venv", force=False):
    if force and os.path.exists(env_dir):
        shutil.rmtree(env_dir)
    if not os.path.exists(env_dir) or is_virtualenv_broken(env_dir):
        log.info("Creating virtual environment...")
        venv.create(env_dir, with_pip=True)
    else:
        log.info("Virtual environment already exists and is valid.")

def get_python_path(env_dir="venv"):
    return os.path.join(env_dir, "Scripts", "python.exe") if os.name == "nt" else os.path.join(env_dir, "bin", "python")

def install_python_packages(env_dir="venv"):
    python_path = get_python_path(env_dir)
    log.info("Installing Python packages...")
    subprocess.check_call([python_path, "-m", "pip", "install", "--upgrade", "pip", "requests", "python-dotenv"])
    if os.path.exists("requirements.txt"):
        subprocess.check_call([python_path, "-m", "pip", "install", "-r", "requirements.txt"])
    else:
        log.warning("requirements.txt not found. Skipping additional Python packages.")

    check_script = (
        "try:\n"
        " import websockets, asyncua\n"
        "except ImportError:\n"
        " exit(1)\n"
        "else:\n"
        " exit(0)"
    )
    result = subprocess.call([python_path, "-c", check_script])
    if result != 0:
        log.warning("websockets or asyncua not found. Installing manually...")
        subprocess.check_call([python_path, "-m", "pip", "install", "websockets", "asyncua"])

def download_and_extract_nvm():
    log.info("Downloading nvm-noinstall.zip...")
    urllib.request.urlretrieve(NVM_NOINSTALL_URL, NVM_NOINSTALL_PATH)
    log.info("Extracting nvm-noinstall.zip...")
    with zipfile.ZipFile(NVM_NOINSTALL_PATH, 'r') as zip_ref:
        zip_ref.extractall(NVM_DIR)
    os.remove(NVM_NOINSTALL_PATH)
    log.info("nvm extracted successfully.")

def configure_nvm():
    nvm_home = os.path.abspath(NVM_DIR)
    nvm_symlink = os.path.join(nvm_home, "symlink")
    os.makedirs(nvm_symlink, exist_ok=True)

    os.environ["NVM_HOME"] = nvm_home
    os.environ["NVM_SYMLINK"] = nvm_symlink
    os.environ["PATH"] += os.pathsep + nvm_home + os.pathsep + nvm_symlink

    settings_path = os.path.join(nvm_home, "settings.txt")
    with open(settings_path, "w") as f:
        f.write(f"root: {nvm_home}\n")
        f.write(f"path: {nvm_symlink}\n")
        f.write("arch: 64\n")
        f.write("proxy: none\n")

def get_latest_lts_node_version():
    nvm_exe = os.path.join(os.environ["NVM_HOME"], "nvm.exe")
    try:
        result = subprocess.run([nvm_exe, "list", "available"], capture_output=True, text=True, shell=True)
        lines = result.stdout.splitlines()
        for line in lines:
            if "LTS" in line:
                return line.split()[0]
    except Exception as e:
        log.warning(f"Failed to detect latest LTS version: {e}")
    return DEFAULT_NODE_VERSION

def install_node_with_nvm():
    log.info("Installing Node.js using nvm (insecure mode)...")
    nvm_exe = os.path.join(os.environ["NVM_HOME"], "nvm.exe")
    version = get_latest_lts_node_version()
    subprocess.check_call([nvm_exe, "install", version, "--insecure"], shell=True)
    subprocess.check_call([nvm_exe, "use", version], shell=True)
    log.info(f"Node.js {version} installed and activated.")

def install_js_packages():
    npm_path = shutil.which("npm")
    if not npm_path:
        if not os.path.exists(NVM_DIR):
            download_and_extract_nvm()
        configure_nvm()
        install_node_with_nvm()
        npm_path = shutil.which("npm")

        if not npm_path:
            log.error("npm still not found after nvm setup. Please restart your terminal or log out and back in.")
            sys.exit(1)

    log.info("Installing JavaScript packages using npm...")
    try:
        if os.path.exists("package-lock.json"):
            subprocess.check_call(["npm", "ci"], shell=True)
        else:
            subprocess.check_call(["npm", "install"], shell=True)
    except subprocess.CalledProcessError as e:
        log.error(f"Error during npm install: {e}")
        sys.exit(1)

def start_live_server():
    npx_path = shutil.which("npx")
    if not npx_path:
        log.error("npx not found. Please ensure Node.js is installed.")
        sys.exit(1)
    log.info("Starting live server using npx...")
    subprocess.Popen(["npx", "serve", "-l", "3000"], shell=True)
    webbrowser.open("http://localhost:3000")

def run_index(env_dir="venv"):
    log.info("Running index.py...")
    python_path = get_python_path(env_dir)
    subprocess.Popen([python_path, "index.py"])

def create_env_template():
    if not os.path.exists(".env") and not os.path.exists(".env.example"):
        with open(".env.example", "w") as f:
            f.write("# Add your environment variables here\n")
        log.info(".env.example created.")

def initialize_git():
    if not os.path.exists(".git"):
        subprocess.call(["git", "init"])
        log.info("Initialized empty Git repository.")

def main():
    parser = argparse.ArgumentParser(description="Setup project environment.")
    parser.add_argument("--no-node", action="store_true", help="Skip Node.js setup")
    parser.add_argument("--no-server", action="store_true", help="Skip starting the live server")
    parser.add_argument("--no-python", action="store_true", help="Skip Python setup")
    parser.add_argument("--force", action="store_true", help="Force recreate environments")
    args = parser.parse_args()

    log.info("Starting project setup...")

    if not args.no_python:
        create_virtualenv(force=args.force)
        install_python_packages()
        load_dotenv()

    if not args.no_node:
        install_js_packages()

    create_env_template()
    initialize_git()

    if not args.no_server:
        start_live_server()
        run_index()

    log.info("Project setup completed successfully.")

if __name__ == "__main__":
    main()
