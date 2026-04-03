"""
OPC UA IJT Tightening Test Framework — OPC UA simulator process lifecycle manager.
Supports two workflows:
  - Dev workflow: reuses an already-running server (port already open).
  - CI workflow: launches the simulator executable found via the
    OPCUA_SIMULATOR_EXE environment variable or well-known install paths.
Only terminates the simulator process if this manager started it.
"""

import asyncio
import logging
import os
import socket
import subprocess  # nosec B404 - intentional: launches OPC UA simulator binary
import time
from typing import Optional

logger = logging.getLogger(__name__)


def is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """Return True if a TCP connection to host:port succeeds within *timeout* seconds."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def wait_for_port(host: str, port: int, timeout_s: float = 30.0) -> bool:
    """
    Poll host:port until it accepts connections or *timeout_s* elapses.
    Returns True if the port opened within the timeout, False otherwise.
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if is_port_open(host, port):
            return True
        time.sleep(0.5)
    return False


async def _opcua_probe(url: str, timeout: float) -> bool:
    """Attempt a real OPC UA connect/disconnect with a short timeout."""
    from asyncua import Client

    client = Client(url, timeout=timeout)
    try:
        await asyncio.wait_for(client.connect(), timeout=timeout)
        await client.disconnect()
        return True
    except Exception:
        return False


def wait_for_opcua_ready(url: str, timeout_s: float = 30.0) -> bool:
    """
    Poll the OPC UA server until it completes the OPC UA handshake or
    *timeout_s* elapses.  TCP-open alone is not sufficient — the OPC UA
    stack may still be initialising after the port becomes reachable.
    Returns True if the server accepted an OPC UA connection within the
    timeout, False otherwise.
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        probe_timeout = min(3.0, max(0.5, remaining))
        try:
            ready = asyncio.run(_opcua_probe(url, probe_timeout))
            if ready:
                return True
        except Exception as exc:
            logger.debug("OPC UA probe attempt failed: %s", exc)
        time.sleep(0.5)
    return False


class ServerManager:
    """
    Manages the OPC UA simulator process lifecycle.
    Priority order for finding the executable:
      1. OPCUA_SIMULATOR_EXE environment variable.
      2. Well-known installation paths (Windows and Linux/macOS).
    If the server is already running when ensure_running() is called,
    no subprocess is spawned and teardown() is a no-op.
    """

    WELL_KNOWN_PATHS: list = [
        # Windows — built from windows_app VS project
        r"C:\DDrive\SourceControl\monorepo\ProtocolAdaptersExternal\OPCUAProtocolAdapter\OPC_UA\SDK_Application\windows_app\bin\x64\Release\opcua_ijt_demo_application.exe",
        r"C:\DDrive\SourceControl\monorepo\ProtocolAdaptersExternal\OPCUAProtocolAdapter\OPC_UA\SDK_Application\windows_app\bin\x64\Debug\opcua_ijt_demo_application.exe",
        r"C:\DDrive\SourceControl\GIT_HUB\UA-for-Industrial-Joining-Technologies\OPC_UA_Servers\Release2\OPC_UA_IJT_Server_Simulator\opcua_ijt_demo_application.exe",
        # Relative paths — if run from repo root or test directory
        "./opcua_ijt_demo_application.exe",
        "./opcua_ijt_demo_application",
        # Linux
        "/usr/local/bin/opcua_ijt_demo_application",
    ]

    def __init__(self, host: str = "localhost", port: int = 40451) -> None:
        self._host = host
        self._port = port
        self._process: Optional[subprocess.Popen] = None

    def ensure_running(self) -> bool:
        """
        Ensure the OPC UA server is accepting connections on host:port.
        Returns True if the server is available (already running or started
        successfully), False if it cannot be reached and no executable was found.
        """
        server_url = f"opc.tcp://{self._host}:{self._port}"
        if is_port_open(self._host, self._port):
            logger.info(
                "OPC UA server TCP port open at %s:%d — waiting for OPC UA handshake",
                self._host,
                self._port,
            )
            ready = wait_for_opcua_ready(server_url, timeout_s=30.0)
            if ready:
                logger.info("OPC UA server ready at %s:%d", self._host, self._port)
            else:
                logger.warning(
                    "OPC UA server TCP is open but OPC UA handshake timed out after 30 s"
                )
            return ready
        exe_path = self._find_simulator_exe()
        if exe_path is None:
            logger.warning(
                "OPC UA server not running at %s:%d and no simulator executable found. "
                "Set OPCUA_SIMULATOR_EXE env var or start the server manually.",
                self._host,
                self._port,
            )
            return False
        logger.info("Launching OPC UA simulator: %s", exe_path)
        try:
            self._process = subprocess.Popen(  # nosec B603 - exe_path is validated above, not user input
                [exe_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=os.path.dirname(os.path.abspath(exe_path)),
            )
        except OSError as exc:
            logger.error("Failed to launch simulator '%s': %s", exe_path, exc)
            return False
        available = wait_for_opcua_ready(server_url, timeout_s=30.0)
        if not available:
            logger.error(
                "Simulator launched (pid=%d) but OPC UA did not become ready within 30 s",
                self._process.pid,
            )
            self._process.terminate()
            self._process = None
        return available

    def _find_simulator_exe(self) -> Optional[str]:
        """Return the first usable simulator executable path, or None."""
        env_exe = os.environ.get("OPCUA_SIMULATOR_EXE")
        if env_exe:
            if os.path.isfile(env_exe):
                return env_exe
            logger.warning("OPCUA_SIMULATOR_EXE='%s' set but file not found", env_exe)
        for path in self.WELL_KNOWN_PATHS:
            if os.path.isfile(path):
                return path
        return None

    def teardown(self) -> None:
        """Terminate the simulator process if this manager started it."""
        if self._process is not None:
            logger.info("Terminating simulator process (pid=%d)", self._process.pid)
            self._process.terminate()
            try:
                self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning("Simulator did not exit cleanly; killing it")
                self._process.kill()
            self._process = None
