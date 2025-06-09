#!/usr/bin/env python3

import os
import subprocess
import sys
import venv
import shutil
import urllib.request
import zipfile
import webbrowser

def log(message):
    print(f"[LOG] {message}")

def check_command_exists(command):
    return shutil.which(command) is not None

def check_python():
    if not check_command_exists("python"):
        log("Python is not installed. Please install Python and try again.")
        sys.exit(1)

def create_virtualenv(env_dir="venv"):
    if not os.path.exists(env_dir):
        log("Creating virtual environment...")
        venv.create(env_dir, with_pip=True)
    else:
        log("Virtual environment already exists.")

def download_and_extract_node(env_dir="venv"):
    node_version = "v22.2.0"
    node_filename = f"node-{node_version}-win-x64"
    node_url = f"https://nodejs.org/dist/{node_version}/{node_filename}.zip"
    node_zip_path = os.path.join(env_dir, "node.zip")
    node_dir = os.path.join(env_dir, "node")

    if not os.path.exists(os.path.join(node_dir, node_filename, "node.exe")):
        log("Downloading Node.js...")
        urllib.request.urlretrieve(node_url, node_zip_path)
        log("Extracting Node.js...")
        with zipfile.ZipFile(node_zip_path, 'r') as zip_ref:
            zip_ref.extractall(node_dir)
        os.remove(node_zip_path)
    else:
        log("Node.js already exists in the virtual environment.")

def install_python_packages(env_dir="venv"):
    python_path = os.path.join(env_dir, "Scripts" if os.name == "nt" else "bin", "python")
    log("Installing Python packages...")
    subprocess.check_call([python_path, "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.check_call([python_path, "-m", "pip", "install", "-r", "requirements.txt"])

def install_js_packages(env_dir="venv"):
    node_path = os.path.join(env_dir, "node", "node-v22.2.0-win-x64")
    npm_path = os.path.join(node_path, "npm.cmd")
    if not os.path.exists("package.json"):
        log("package.json not found. Skipping npm install.")
        return
    if not os.path.exists(npm_path):
        log(f"npm not found at {npm_path}. Please check Node.js extraction.")
        sys.exit(1)
    log("Installing JavaScript packages using local npm...")
    try:
        if os.path.exists("package-lock.json"):
            subprocess.check_call([npm_path, "ci"])
        else:
            subprocess.check_call([npm_path, "install"])
    except subprocess.CalledProcessError as e:
        log(f"Error during npm install: {e}")
        sys.exit(1)

def start_live_server(env_dir="venv"):
    node_path = os.path.join(env_dir, "node", "node-v22.2.0-win-x64")
    npx_path = os.path.join(node_path, "npx.cmd")
    if not os.path.exists(npx_path):
        log(f"npx not found at {npx_path}. Please check Node.js extraction.")
        sys.exit(1)
    log("Starting Live Server on http://localhost:3000 ...")
    subprocess.Popen([npx_path, "serve", "-l", "3000"])
    webbrowser.open("http://localhost:3000")

def run_index(env_dir="venv"):
    python_path = os.path.join(env_dir, "Scripts" if os.name == "nt" else "bin", "python")
    log("Starting index.py (WebSocket server)...")
    subprocess.call([python_path, "index.py"])

def main():
    log("Starting project setup...")
    check_python()
    create_virtualenv()
    download_and_extract_node()
    install_python_packages()
    install_js_packages()
    start_live_server()
    run_index()

if __name__ == "__main__":
    main()
