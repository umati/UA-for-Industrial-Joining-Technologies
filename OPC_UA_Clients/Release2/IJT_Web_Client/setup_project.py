import os
import subprocess
import sys
import webbrowser

def run_command(command, cwd=None, shell=False):
    """Run a system command and handle errors."""
    try:
        result = subprocess.run(command, cwd=cwd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=shell)
        print(result.stdout)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr}")
        sys.exit(1)

def create_virtualenv(venv_path):
    """Create a virtual environment."""
    if not os.path.exists(venv_path):
        print("Creating virtual environment...")
        run_command([sys.executable, "-m", "venv", venv_path])
    else:
        print("Virtual environment already exists.")

def install_python_packages(venv_python):
    """Install required Python packages."""
    print("Installing Python packages...")
    run_command([venv_python, "-m", "pip", "install", "--upgrade", "pip"])
    run_command([venv_python, "-m", "pip", "install", "websockets", "asyncua"])

def check_node():
    """Check if Node.js is installed, and install it if not."""
    try:
        subprocess.run(["node", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        print("Node.js is already installed.")
    except subprocess.CalledProcessError:
        print("Node.js is not installed. Installing Node.js...")

        if os.name == "nt":
            install_cmd = [
                "powershell", "-Command",
                "Invoke-WebRequest -Uri https://nodejs.org/dist/v22.16.0/node-v22.16.0-x64.msi -OutFile nodejs.msi; "
                "Start-Process msiexec.exe -ArgumentList '/i nodejs.msi /quiet' -NoNewWindow -Wait; "
                "Remove-Item nodejs.msi"
            ]
        else:
            install_cmd = [
                "bash", "-c",
                "curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - && sudo apt-get install -y nodejs"
            ]

        try:
            subprocess.run(install_cmd, check=True, shell=True)
            print("Node.js installed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to install Node.js: {e}")
            sys.exit(1)

def install_js_packages():
    """Install required JavaScript packages using npm."""
    print("Installing JavaScript packages...")
    run_command(["npm", "install"], shell=True)

def start_servers(venv_python):
    """Start the Python server and live server."""
    print("Starting Python server...")
    python_server = subprocess.Popen([venv_python, "index.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    print("Starting live server...")
    live_server = subprocess.Popen(["npx", "serve"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)

    try:
        while True:
            output = live_server.stdout.readline()
            if output == '' and live_server.poll() is not None:
                break
            if output:
                print(output.strip())
                if "Local:" in output:
                    url = output.split()[-1]
                    print(f"Opening {url} in the default web browser...")
                    webbrowser.open(url)
                    break

        python_server.wait()
        live_server.wait()
    except KeyboardInterrupt:
        python_server.terminate()
        live_server.terminate()
        print("Servers terminated.")

def main():
    venv_path = os.path.join(os.getcwd(), "venv")
    venv_python = os.path.join(venv_path, "Scripts", "python.exe") if os.name == "nt" else os.path.join(venv_path, "bin", "python")

    create_virtualenv(venv_path)
    install_python_packages(venv_python)
    check_node()
    install_js_packages()
    start_servers(venv_python)

if __name__ == "__main__":
    main()
