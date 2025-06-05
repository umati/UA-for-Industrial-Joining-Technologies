import os
import subprocess
import sys
import webbrowser
import shutil
import time
import atexit

processes = []

def log(message):
    print(f"[LOG] {message}")

def run_command(command, cwd=None, shell=False):
    try:
        result = subprocess.run(command, cwd=cwd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=shell)
        if result.stdout:
            log(result.stdout.strip())
        if result.stderr:
            log(f"Warnings:\n{result.stderr.strip()}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        log(f"Command failed: {command if isinstance(command, str) else ' '.join(command)}")
        log(f"STDOUT:\n{e.stdout}")
        log(f"STDERR:\n{e.stderr}")
        sys.exit(1)

def create_virtualenv(venv_path, venv_python):
    if not os.path.exists(venv_python):
        log("Creating virtual environment...")
        run_command([sys.executable, "-m", "venv", venv_path])
    else:
        log("Virtual environment already exists and is valid.")

def install_python_packages(venv_python):
    log("Installing Python packages...")
    run_command([venv_python, "-m", "pip", "install", "--upgrade", "pip"])
    run_command([
        venv_python, "-m", "pip", "install",
        "--index-url", "https://pypi.org/simple",
        "websockets", "asyncua"
    ])
    log("Python packages installed successfully.")

def check_node():
    log("Checking for Node.js and npm...")
    if shutil.which("node") is None:
        log("Error: Node.js is not installed.")
        sys.exit(1)
    if shutil.which("npm") is None:
        log("Error: npm is not installed.")
        sys.exit(1)
    try:
        result = subprocess.run(
            ["node", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True,
            timeout=10
        )
        if result.returncode != 0:
            log("Node.js is not working correctly.")
            sys.exit(1)
        log(f"Node.js version: {result.stdout.strip()}")
    except subprocess.TimeoutExpired:
        log("Node.js check timed out.")
        sys.exit(1)
    except Exception as e:
        log(f"Unexpected error while checking Node.js: {e}")
        sys.exit(1)

def install_js_packages():
    log("Installing JavaScript packages...")
    if not os.path.exists("package.json"):
        log("Error: package.json not found.")
        sys.exit(1)
    log(f"Current working directory: {os.getcwd()}")
    log(f"Files in directory: {os.listdir(os.getcwd())}")
    run_command("npm install", shell=True)
    log("JavaScript packages installed successfully.")

def start_servers(venv_python):
    log("Starting Python server...")
    if not os.path.exists("index.py"):
        log("Error: index.py not found.")
        sys.exit(1)

    try:
        python_server = subprocess.Popen([venv_python, "index.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        processes.append(python_server)
        log("Python server started successfully.")
    except Exception as e:
        log(f"Failed to start Python server: {e}")
        sys.exit(1)

    log("Starting live server on port 3000...")
    serve_cmd = os.path.join("node_modules", ".bin", "serve")
    if os.name == "nt":
        serve_cmd = serve_cmd.replace("/", "\\")

    try:
        live_server = subprocess.Popen([serve_cmd, "-l", "3000"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
        processes.append(live_server)
        log("Live server started successfully.")
    except Exception as e:
        log(f"Failed to start live server: {e}")
        python_server.terminate()
        sys.exit(1)

    time.sleep(1)

    try:
        while True:
            output = live_server.stdout.readline()
            if output == '' and live_server.poll() is not None:
                break
            if output:
                log(output.strip())
                if "Local:" in output:
                    url = output.split()[-1]
                    log(f"Live server is running at {url}")
                    if not os.environ.get("IS_DOCKER"):
                        log(f"Opening {url} in the default web browser...")
                        webbrowser.open(url)
                    break
        python_server.wait()
        live_server.wait()
    except KeyboardInterrupt:
        log("Keyboard interrupt received. Shutting down servers...")
    except Exception as e:
        log(f"Error while running servers: {e}")
    finally:
        for p in processes:
            if p and p.poll() is None:
                p.terminate()
                log("Terminated subprocess.")

def main():
    venv_path = os.path.join(os.getcwd(), "venv")
    venv_python = os.path.join(venv_path, "Scripts", "python.exe") if os.name == "nt" else os.path.join(venv_path, "bin", "python")

    log("Starting setup process...")
    create_virtualenv(venv_path, venv_python)
    install_python_packages(venv_python)
    check_node()
    install_js_packages()
    start_servers(venv_python)

if __name__ == "__main__":
    atexit.register(lambda: [p.terminate() for p in processes if p and p.poll() is None])
    main()
