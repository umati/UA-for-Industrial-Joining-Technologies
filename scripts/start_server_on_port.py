#!/usr/bin/env python3
"""Start (or stop) the OPC UA IJT Server Simulator on a specific port.

The server EXE reads ``serverEndpointTCPPort`` from its own
``server_configuration.json`` in its working directory.  To run on a
non-default port without modifying source files, this script:

Start mode (default)
    1. Copies the entire server binary directory to a short temp path
       (``RUNNER_TEMP/ijt-sim/server_<port>/`` on GitHub-hosted runners)
    2. Patches ``serverEndpointTCPPort`` in the copy's
       ``server_configuration.json``
    3. Starts the executable from the copied directory
    4. Waits up to ``--timeout`` seconds for the OPC UA HELLO handshake to
       succeed on the patched port (via the shared
       :func:`ijt_live_readiness.wait_for_opcua_hello` probe — TCP-port
       liveness alone is NOT sufficient)
    5. Exports ``SERVER_PID``, ``OPCUA_SERVER_PORT``, and
       ``OPCUA_SERVER_URL`` to ``GITHUB_ENV`` (no-op outside CI)
    6. On readiness failure, writes a JSON manifest plus the last lines of
       the simulator's stdout/stderr to ``--diagnostics-dir`` (when set) so
       the calling CI job's upload-artifact step can attach them.

Stop mode (``--stop``)
    Reads ``SERVER_PID`` from the environment to terminate the server process.
    Uses ``--port`` to locate and remove the temp directory.

This is the same copy-patch pattern used by:
  - Python clients  via ``run_all_tests.py``
  - C# xUnit tests  via ``OpcUaServerFixture.cs``

Examples (CI YAML)::

    - name: Start OPC UA server on port 40464
      working-directory: ${{ github.workspace }}
      run: python scripts/start_server_on_port.py --port 40464 \\
             --diagnostics-dir test-results/readiness

    - name: Stop OPC UA server
      if: always()
      working-directory: ${{ github.workspace }}
      run: python scripts/start_server_on_port.py --port 40464 --stop

Examples (local dev, from repo root)::

    python scripts/start_server_on_port.py --port 40464
    python scripts/start_server_on_port.py --port 40464 --stop
"""

import argparse
import contextlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

# The shared readiness module is a sibling file. Adding the script's directory
# to sys.path is automatic when this file is invoked as ``python scripts/...``;
# the explicit insert here keeps both ``python -m`` and direct invocation
# working from any cwd.
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

# Stdlib-only sibling: this import MUST NOT pull in any third-party package
# because this script runs in CI before ``pip install`` (notably C# Live).
from ijt_live_readiness import (  # noqa: E402
    capture_process_log_tail,
    wait_for_opcua_hello,
    write_diagnostic_manifest,
)

DEFAULT_SERVER_DIR = Path("OPC_UA_Servers/Release2/OPC_UA_IJT_Server_Simulator")
DEFAULT_TIMEOUT = 60
_PROCESS_LOG_BUFFER_LIMIT = 400


def _write_github_env(key: str, value: str) -> None:
    github_env = os.environ.get("GITHUB_ENV")
    if github_env:
        with open(github_env, "a", encoding="utf-8") as f:
            f.write(f"{key}={value}\n")


def _spawn_log_pump(stream, buffer: list[str], stream_name: str) -> threading.Thread:
    """Drain ``stream`` line-by-line into ``buffer`` (rolling) on a daemon thread.

    Replaces the previous ``stdout=DEVNULL`` so that, on a readiness failure,
    we can dump the simulator's last few lines into the job-scoped diagnostics
    directory. The buffer is bounded; old lines are dropped.
    """

    def _pump() -> None:
        with contextlib.suppress(Exception):
            try:
                for raw in iter(stream.readline, b""):
                    if not raw:
                        break
                    line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                    buffer.append(f"{stream_name}: {line}")
                    if len(buffer) > _PROCESS_LOG_BUFFER_LIMIT:
                        del buffer[: len(buffer) - _PROCESS_LOG_BUFFER_LIMIT]
            finally:
                with contextlib.suppress(Exception):
                    stream.close()

    thread = threading.Thread(target=_pump, name=f"ijt-sim-{stream_name}", daemon=True)
    thread.start()
    return thread


def _default_tmp_base() -> Path:
    """Return the short default root for copied simulator instances."""
    base = os.environ.get("RUNNER_TEMP") or tempfile.gettempdir()
    return Path(base) / "ijt-sim"


def start_server(
    port: int,
    server_dir: Path,
    tmp_base: Path,
    timeout: int,
    diagnostics_dir: Path | None = None,
) -> None:
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
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    print(f"    Server started (PID {proc.pid})")

    # Drain stdout/stderr into a rolling buffer so we can emit a tail on
    # failure. Without this, simulator startup output is silently lost and
    # CI diagnostics show only "port did not open".
    log_buffer: list[str] = []
    _spawn_log_pump(proc.stdout, log_buffer, "stdout")
    _spawn_log_pump(proc.stderr, log_buffer, "stderr")

    # Protocol-level readiness wait. We do not gate on raw TCP-port open
    # because the OPC UA stack may be initialising after the port becomes
    # reachable. wait_for_opcua_hello returns success only when the server
    # replies to a binary HELLO with ACK or ERR, either of which proves the
    # OPC UA stack is alive.
    result = wait_for_opcua_hello("localhost", port, timeout=float(timeout))
    write_diagnostic_manifest(
        diagnostics_dir,
        result,
        caller=f"start_server_on_port-{port}",
        extra={"server_dir": str(dst_dir), "exe": exe_path.name, "pid": proc.pid},
    )
    if not result.ok:
        capture_process_log_tail(
            diagnostics_dir,
            name=f"opcua-server-{port}",
            lines=log_buffer,
        )
        print(
            f"ERROR: OPC UA server did not respond to HELLO on port {port} "
            f"within {timeout}s ({result.error}).",
            file=sys.stderr,
        )
        proc.kill()
        sys.exit(1)

    print(f"    Port {port} ready after {result.elapsed_seconds:.1f}s — server ready.")

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
        default=None,
        metavar="DIR",
        help="Base temp directory for copies (default: RUNNER_TEMP/ijt-sim or system temp/ijt-sim)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Seconds to wait for OPC UA HELLO/ACK (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "--diagnostics-dir",
        type=Path,
        default=None,
        metavar="DIR",
        help=(
            "Directory to write the readiness diagnostic manifest "
            "(readiness-diagnostic-start_server_on_port-<port>.json) and, on "
            "failure, the simulator stdout/stderr tail. The directory is "
            "created if it does not exist."
        ),
    )

    args = parser.parse_args()

    if not (1024 <= args.port <= 65535):
        print("ERROR: --port must be in range 1024–65535", file=sys.stderr)
        sys.exit(1)

    if args.stop:
        stop_server(args.port, args.tmp_base or _default_tmp_base())
    else:
        start_server(
            args.port,
            args.server_dir,
            args.tmp_base or _default_tmp_base(),
            args.timeout,
            diagnostics_dir=args.diagnostics_dir,
        )


if __name__ == "__main__":
    main()
