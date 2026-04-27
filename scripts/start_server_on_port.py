#!/usr/bin/env python3
"""Start (or stop) the OPC UA IJT Server Simulator on a specific port.

The server EXE reads ``serverEndpointTCPPort`` from its own
``server_configuration.json`` in its working directory.  To run on a
non-default port without modifying source files, this script:

Start mode (default)
    1. Copies the entire server binary directory to ``tmp/server_<port>/``
    2. Patches ``serverEndpointTCPPort`` in the copy's
       ``server_configuration.json``
    3. Starts the executable from the copied directory
    4. Waits up to ``--timeout`` seconds for the port to open
    5. Exports ``SERVER_PID``, ``OPCUA_SERVER_PORT``, and
       ``OPCUA_SERVER_URL`` to ``GITHUB_ENV`` (no-op outside CI)

Stop mode (``--stop``)
    Reads ``SERVER_PID`` from the environment to terminate the server process.
    Uses ``--port`` to locate and remove the temp directory (``tmp/server_<port>/``).

This is the same copy-patch pattern used by:
  - Python clients  via ``run_all_tests.py``
  - C# xUnit tests  via ``OpcUaServerFixture.cs``

Examples (CI YAML)::

    - name: Start OPC UA server on port 40464
      working-directory: ${{ github.workspace }}
      run: python scripts/start_server_on_port.py --port 40464

    - name: Stop OPC UA server
      if: always()
      working-directory: ${{ github.workspace }}
      run: python scripts/start_server_on_port.py --port 40464 --stop

Examples (local dev, from repo root)::

    python scripts/start_server_on_port.py --port 40464
    python scripts/start_server_on_port.py --port 40464 --stop
"""

import argparse
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_SERVER_DIR = Path("OPC_UA_Servers/Release2/OPC_UA_IJT_Server_Simulator")
DEFAULT_TMP_BASE = Path("tmp")
DEFAULT_TIMEOUT = 60


def _write_github_env(key: str, value: str) -> None:
    github_env = os.environ.get("GITHUB_ENV")
    if github_env:
        with open(github_env, "a", encoding="utf-8") as f:
            f.write(f"{key}={value}\n")


def _wait_for_port(port: int, timeout: int) -> float:
    """Return seconds elapsed, or -1 on timeout."""
    start = time.monotonic()
    deadline = start + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("localhost", port), timeout=2):
                return time.monotonic() - start
        except OSError:
            time.sleep(2)
    return -1.0


def start_server(port: int, server_dir: Path, tmp_base: Path, timeout: int) -> None:
    dst_dir = tmp_base / f"server_{port}"
    cfg_name = "server_configuration.json"

    print(f"==> Starting OPC UA server on port {port}")
    print(f"    Source : {server_dir}")
    print(f"    Copy   : {dst_dir}")

    if dst_dir.exists():
        shutil.rmtree(dst_dir)
    shutil.copytree(server_dir, dst_dir)
    print("    Server directory copied.")

    cfg_path = dst_dir / cfg_name
    if not cfg_path.exists():
        print(f"ERROR: {cfg_name} not found in {dst_dir}", file=sys.stderr)
        sys.exit(1)

    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)

    old_port = cfg["serverConfigurationData"]["serverEndpointTCPPort"]
    cfg["serverConfigurationData"]["serverEndpointTCPPort"] = port
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    print(f"    Patched serverEndpointTCPPort: {old_port} -> {port}")

    # Find executable: prefer .exe on Windows, fall back to any executable file
    exe_candidates = sorted(dst_dir.glob("*.exe"))
    if not exe_candidates:
        exe_candidates = [
            p for p in dst_dir.iterdir() if p.is_file() and os.access(p, os.X_OK) and not p.suffix
        ]
    if not exe_candidates:
        print(f"ERROR: No executable found in {dst_dir}", file=sys.stderr)
        sys.exit(1)

    exe_path = exe_candidates[0]
    print(f"    EXE: {exe_path.name}")

    proc = subprocess.Popen(  # noqa: S603
        [str(exe_path)],
        cwd=str(dst_dir),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print(f"    Server started (PID {proc.pid})")

    elapsed = _wait_for_port(port, timeout)
    if elapsed < 0:
        print(
            f"ERROR: OPC UA server did not open port {port} within {timeout}s.",
            file=sys.stderr,
        )
        proc.kill()
        sys.exit(1)

    print(f"    Port {port} open after {elapsed:.1f}s — server ready.")

    _write_github_env("SERVER_PID", str(proc.pid))
    _write_github_env("OPCUA_SERVER_PORT", str(port))
    _write_github_env("OPCUA_SERVER_URL", f"opc.tcp://localhost:{port}")

    if os.environ.get("GITHUB_ENV"):
        print("    Exported SERVER_PID, OPCUA_SERVER_PORT, OPCUA_SERVER_URL to GITHUB_ENV.")
    else:
        print("    (Not in CI — GITHUB_ENV not set. Values for manual use:)")
        print(f"      SERVER_PID={proc.pid}")
        print(f"      OPCUA_SERVER_PORT={port}")
        print(f"      OPCUA_SERVER_URL=opc.tcp://localhost:{port}")


def stop_server(port: int, tmp_base: Path) -> None:
    pid_str = os.environ.get("SERVER_PID")
    if pid_str:
        try:
            pid = int(pid_str)
            if sys.platform == "win32":
                subprocess.run(  # noqa: S603
                    ["taskkill", "/F", "/PID", str(pid)],  # noqa: S607
                    capture_output=True,
                    check=False,
                )
            else:
                os.kill(pid, signal.SIGTERM)
            print(f"    Stopped server PID {pid}")
        except Exception as exc:  # noqa: BLE001
            print(f"    Warning: could not stop PID {pid_str}: {exc}")

    dst_dir = tmp_base / f"server_{port}"
    if dst_dir.exists():
        shutil.rmtree(dst_dir, ignore_errors=True)
        print(f"    Removed {dst_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Start or stop the OPC UA IJT Server Simulator on a specific port.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--port",
        type=int,
        required=True,
        help="TCP port number (1024–65535)",
    )
    parser.add_argument(
        "--stop",
        action="store_true",
        help="Stop mode: terminate the server process and remove the temp directory",
    )
    parser.add_argument(
        "--server-dir",
        type=Path,
        default=DEFAULT_SERVER_DIR,
        metavar="PATH",
        help=f"Server binary directory (default: {DEFAULT_SERVER_DIR})",
    )
    parser.add_argument(
        "--tmp-base",
        type=Path,
        default=DEFAULT_TMP_BASE,
        metavar="DIR",
        help=f"Base temp directory for copies (default: {DEFAULT_TMP_BASE})",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Seconds to wait for port to open (default: {DEFAULT_TIMEOUT})",
    )

    args = parser.parse_args()

    if not (1024 <= args.port <= 65535):
        print("ERROR: --port must be in range 1024–65535", file=sys.stderr)
        sys.exit(1)

    if args.stop:
        stop_server(args.port, args.tmp_base)
    else:
        start_server(args.port, args.server_dir, args.tmp_base, args.timeout)


if __name__ == "__main__":
    main()
