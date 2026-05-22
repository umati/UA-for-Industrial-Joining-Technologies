"""
Console Client live test conftest — guaranteed zero skips.

AUTO-STARTS the OPC UA server if it is not already running so that live tests
never silently skip due to a missing server.  Any startup failure raises
pytest.fail() immediately (loud, not silent).

Strategy
--------
• Windows (local / CI): extracts OPC UA server ZIP → runs EXE
• Linux (CI Docker)   : starts the server through Docker Compose
• Port already open   : reuse only for unmanaged live tests

Auto-marks
----------
Every test collected from tests/live/ is tagged with pytest.mark.live so that
unit-only runs can exclude them via  -m "not live"  without any silent skip.
"""

from __future__ import annotations

import contextlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import pytest

# ── Path constants ─────────────────────────────────────────────────────────────
_LIVE_DIR = Path(__file__).resolve().parent
# _LIVE_DIR = tests/live/
# parents: [0]=tests/, [1]=IJT_Console_Client/, [2]=Release2/, [3]=OPC_UA_Clients/, [4]=repo root
_CONSOLE_ROOT = _LIVE_DIR.parents[1]
_REPO_ROOT = _LIVE_DIR.parents[4]
_SERVER_RELEASE2 = _REPO_ROOT / "OPC_UA_Servers" / "Release2"
_SERVER_DOCKER_IMAGE = "opcua-ijt-server:latest"

# The shared readiness module lives at ``<repo>/scripts/ijt_live_readiness.py``.
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if _SCRIPTS_DIR.is_dir() and str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from ijt_live_readiness import (  # noqa: E402
    COMPOSE_WAIT_TIMEOUT_COLD_SECONDS,
    COMPOSE_WAIT_TIMEOUT_WARM_SECONDS,
    capture_compose_logs_on_failure,
    wait_for_opcua_hello,
    wait_for_tcp,
)

_SERVER_LINUX_ZIP = _SERVER_RELEASE2 / "OPC_UA_IJT_Server_Simulator_Linux.zip"
_SERVER_ZIP = _SERVER_RELEASE2 / "OPC_UA_IJT_Server_Simulator.zip"
_SERVER_DIR = _SERVER_RELEASE2 / "OPC_UA_IJT_Server_Simulator"
_SERVER_EXE = _SERVER_DIR / "opcua_ijt_demo_application.exe"
_SERVER_COPY_ROOT = _CONSOLE_ROOT / "tmp" / "server-copies"
_SERVER_PKI_ROOT = _CONSOLE_ROOT / "tmp" / "p"
_CLIENT_PKI_ROOT = _CONSOLE_ROOT / "tmp" / "client-pki"
_DOCKER_OVERRIDE_ROOT = _CONSOLE_ROOT / "tmp" / "docker-overrides"

_OPCUA_PORT = 40451

# Readiness diagnostics (compose-log capture on failure) are written next to
# pytest test-results so the Console Live integration job's
# ``upload-artifact: test-results/`` step picks them up automatically.
_READINESS_DIAGNOSTICS_DIR = _CONSOLE_ROOT / "test-results" / "readiness"


def _console_readiness_diagnostics_dir() -> Path:
    """Return the directory under ``test-results/`` where compose-log capture
    and any future readiness diagnostics should land."""
    return _READINESS_DIAGNOSTICS_DIR


sys.path.insert(0, str(_CONSOLE_ROOT))

from docker_freshness import is_image_stale  # noqa: E402
from opcua_security_support import (  # noqa: E402
    console_application_uri,
    console_opcua_security_common_name,
    load_opcua_security_users,
    preserve_test_artifacts,
    trust_application_certificate,
    trust_user_token_certificate,
    unique_temp_dir,
    write_self_signed_certificate,
    write_simulator_user_identity_configuration,
)


@dataclass
class StartedServer:
    process: subprocess.Popen | None = None
    temp_dir: Path | None = None
    pki_dir: Path | None = None
    compose_dir: Path | None = None
    compose_project: str | None = None


# ── Port / URL utilities ───────────────────────────────────────────────────────
def _resolve_server_host_port() -> tuple[str, int]:
    url = os.environ.get("OPCUA_SERVER_URL", "")
    port_override = os.environ.get("OPCUA_SERVER_PORT", "")
    if url:
        try:
            parsed = urlparse(url.replace("opc.tcp://", "http://"))
            port = parsed.port or int(port_override or _OPCUA_PORT)
            return parsed.hostname or "localhost", port
        except (ValueError, AttributeError):
            pass
    if port_override:
        with contextlib.suppress(ValueError):
            return "localhost", int(port_override)
    return "localhost", _OPCUA_PORT


def _port_open(host: str, port: int, timeout: float = 1.5) -> bool:
    return wait_for_tcp(host, port, timeout=timeout, interval=timeout, connect_timeout=timeout).ok


def _isolated_server_requested() -> bool:
    return bool(os.environ.get("IJT_OPCUA_SECURITY_TARGET")) or (
        bool(os.environ.get("IJT_OPCUA_SECURITY_SUT")) and bool(os.environ.get("OPCUA_SERVER_PORT"))
    )


def _stop_docker_containers_publishing_port(port: int) -> bool:
    docker = shutil.which("docker")
    if docker is None:
        return False

    try:
        result = subprocess.run(
            [docker, "ps", "--filter", f"publish={port}", "--format", "{{.ID}}"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    if result.returncode != 0:
        return False

    container_ids = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    for container_id in container_ids:
        try:
            subprocess.run(
                [docker, "stop", container_id],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=20,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
    return bool(container_ids)


def _kill_process_on_port(port: int) -> None:
    if _stop_docker_containers_publishing_port(port):
        return

    if os.environ.get("IJT_OPCUA_SECURITY_SUT", "").strip().lower() == "linux":
        return

    if platform.system() == "Windows":
        try:
            result = subprocess.run(
                ["netstat.exe", "-ano"],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            return
        if result.returncode != 0:
            return

        pids: set[str] = set()
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) < 5:
                continue
            if not parts[0].lower().startswith("tcp"):
                continue
            if parts[3].upper() != "LISTENING":
                continue
            if parts[1].rsplit(":", 1)[-1] == str(port):
                pids.add(parts[-1])

        for pid in sorted(pids):
            if pid == "0":
                continue
            with contextlib.suppress(OSError, subprocess.TimeoutExpired):
                subprocess.run(
                    ["taskkill.exe", "/F", "/T", "/PID", pid],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                    timeout=10,
                )
        return

    fuser = shutil.which("fuser")
    if fuser is not None:
        with contextlib.suppress(OSError, subprocess.TimeoutExpired):
            subprocess.run(
                [fuser, "-k", f"{port}/tcp"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=10,
            )


def _wait_for_opcua_hello(host: str, port: int, timeout: float) -> bool:
    """Confirm an OPC UA server (not just an open TCP port) is reachable.

    Delegates to the shared readiness module so the Console fixture, the C#
    fixture, ``scripts/start_server_on_port.py``, and the Web Client all use
    one binary-protocol HELLO probe.
    """

    return wait_for_opcua_hello(host, port, timeout=timeout).ok


# ── Server launcher ───────────────────────────────────────────────────────────
def _prepare_opcua_security_client_certificate() -> None:
    if not os.environ.get("IJT_OPCUA_SECURITY_TARGET"):
        return

    target = os.environ.get("IJT_OPCUA_SECURITY_TARGET", "local").lower()

    # 1) Secure-channel (application) certificate. Reused as the "self" cert
    #    for the OPC UA secure channel; trusted into DefaultApplicationGroup.
    if not (os.environ.get("CONSOLE_SECURITY_CLIENT_CERT") and os.environ.get("CONSOLE_SECURITY_CLIENT_KEY")):
        cert_dir = unique_temp_dir(_CLIENT_PKI_ROOT, target)
        generated = write_self_signed_certificate(
            cert_dir,
            console_opcua_security_common_name(target),
            application_uri=console_application_uri(),
        )
        os.environ["CONSOLE_SECURITY_CLIENT_CERT"] = str(generated.certificate_pem)
        os.environ["CONSOLE_SECURITY_CLIENT_CERT_DER"] = str(generated.certificate_der)
        os.environ["CONSOLE_SECURITY_CLIENT_KEY"] = str(generated.private_key_pem)

    # 2) Known user-identity certificate for the X509 happy-path case.
    #    The managed simulator copy receives this certificate's SHA-1
    #    thumbprint in user_identity_configuration.json before startup.
    if not (os.environ.get("CONSOLE_X509_USER_CERT") and os.environ.get("CONSOLE_X509_USER_KEY")):
        user_cert_dir = unique_temp_dir(_CLIENT_PKI_ROOT, f"{target}_user1")
        user_generated = write_self_signed_certificate(
            user_cert_dir,
            "user1",
            application_uri=console_application_uri(),
        )
        os.environ["CONSOLE_X509_USER_CERT"] = str(user_generated.certificate_pem)
        os.environ["CONSOLE_X509_USER_CERT_DER"] = str(user_generated.certificate_der)
        os.environ["CONSOLE_X509_USER_KEY"] = str(user_generated.private_key_pem)


def _users_file() -> Path:
    configured = os.environ.get("OPCUA_SECURITY_USERS_FILE")
    if configured:
        return Path(configured)
    shared = _SERVER_RELEASE2 / "opcua_security.users.yaml"
    if shared.exists():
        return shared
    return _CONSOLE_ROOT / "tests" / "opcua_security.users.yaml"


def _write_opcua_security_user_identity_configuration(server_dir: Path) -> None:
    user_cert_der = os.environ.get("CONSOLE_X509_USER_CERT_DER")
    write_simulator_user_identity_configuration(
        server_dir / "user_identity_configuration.json",
        load_opcua_security_users(_users_file()),
        x509_user_certificate_der=Path(user_cert_der) if user_cert_der else None,
    )


def _compose_bind_path(path: Path) -> str:
    return path.resolve().as_posix()


def _write_docker_compose_override(root: Path, pki_dir: Path) -> Path:
    _write_opcua_security_user_identity_configuration(root)
    config_path = root / "user_identity_configuration.json"
    override_path = root / "docker-compose.opcua-security.yml"
    override_path.write_text(
        "\n".join(
            [
                "services:",
                "  opcua-ijt-server:",
                "    volumes:",
                f'      - "{_compose_bind_path(config_path)}:/app/user_identity_configuration.json:ro"',
                f'      - "{_compose_bind_path(pki_dir)}:/app/pki"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    return override_path


def _trust_docker_certificate(pki_mount_dir: Path, group: str, certificate_der: Path) -> None:
    target_dir = pki_mount_dir / group / "trusted" / "certs"
    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(certificate_der, target_dir / certificate_der.name)


def _allow_container_write(path: Path) -> None:
    if platform.system() == "Windows":
        return
    for child in [path, *path.rglob("*")]:
        mode = 0o777 if child.is_dir() else 0o666
        with contextlib.suppress(OSError):
            child.chmod(mode)


def _patch_server_configuration(config_path: Path, port: int, pki_dir: Path) -> None:
    if not config_path.exists():
        return

    with config_path.open(encoding="utf-8") as fh:
        config = json.load(fh)
    server_data = config.setdefault("serverConfigurationData", {})
    server_data["serverEndpointTCPPort"] = port
    server_data["pkiDirectoryPath"] = str(pki_dir)
    if os.environ.get("IJT_OPCUA_SECURITY_TARGET"):
        server_data["autoTrustCertificates"] = False
    with config_path.open("w", encoding="utf-8") as fh:
        json.dump(config, fh, indent=2)


def _prepare_copied_windows_server(port: int) -> tuple[Path, Path, Path] | None:
    if not _SERVER_EXE.exists() and _SERVER_ZIP.exists():
        with zipfile.ZipFile(_SERVER_ZIP) as zf:
            zf.extractall(_SERVER_RELEASE2)

    if not _SERVER_EXE.exists():
        return None

    server_dir = unique_temp_dir(_SERVER_COPY_ROOT, f"opcua_console_{port}")
    shutil.copytree(_SERVER_DIR, server_dir, dirs_exist_ok=True)
    copied_exe = server_dir / _SERVER_EXE.name
    pki_dir = unique_temp_dir(_SERVER_PKI_ROOT, str(port))
    _patch_server_configuration(server_dir / "server_configuration.json", port, pki_dir)
    if os.environ.get("IJT_OPCUA_SECURITY_TARGET"):
        _write_opcua_security_user_identity_configuration(server_dir)

    cert_der = os.environ.get("CONSOLE_SECURITY_CLIENT_CERT_DER")
    if cert_der:
        # Trust the client app cert only for secure-channel validation.
        # X509 user-identity certs use DefaultUserTokenGroup below.
        trust_application_certificate(pki_dir, Path(cert_der))

    user_cert_der = os.environ.get("CONSOLE_X509_USER_CERT_DER")
    if user_cert_der:
        # Happy-path X509 user identity. The same certificate thumbprint is
        # written into user_identity_configuration.json above.
        trust_user_token_certificate(pki_dir, Path(user_cert_der))

    return server_dir, copied_exe, pki_dir


def _start_windows_server(port: int) -> StartedServer | None:
    if platform.system() != "Windows":
        return None

    prepared = _prepare_copied_windows_server(port)
    if prepared is None:
        return None

    server_dir, copied_exe, pki_dir = prepared
    proc = subprocess.Popen(
        [str(copied_exe)],
        cwd=str(server_dir),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return StartedServer(process=proc, temp_dir=server_dir, pki_dir=pki_dir)


def _start_docker_server(port: int) -> StartedServer | None:
    docker = shutil.which("docker")
    if docker is None:
        return None

    compose_file = _SERVER_RELEASE2 / "docker-compose.yml"
    if not compose_file.exists():
        return None

    project = os.environ.get("COMPOSE_PROJECT_NAME") or (
        f"ijt-console-{os.environ.get('IJT_OPCUA_SECURITY_TARGET', 'local').lower()}-{uuid.uuid4().hex[:8]}"
    )
    env = os.environ.copy()
    env["OPCUA_SERVER_PORT"] = str(port)
    env["COMPOSE_PROJECT_NAME"] = project
    compose_args = [docker, "compose"]
    override_dir: Path | None = None
    pki_dir: Path | None = None
    if os.environ.get("IJT_OPCUA_SECURITY_TARGET"):
        override_dir = unique_temp_dir(_DOCKER_OVERRIDE_ROOT, f"console_{port}")
        pki_dir = unique_temp_dir(_SERVER_PKI_ROOT, f"docker_{port}")
        cert_der = os.environ.get("CONSOLE_SECURITY_CLIENT_CERT_DER")
        if cert_der:
            _trust_docker_certificate(pki_dir, "DefaultApplicationGroup", Path(cert_der))
        user_cert_der = os.environ.get("CONSOLE_X509_USER_CERT_DER")
        if user_cert_der:
            _trust_docker_certificate(pki_dir, "DefaultUserTokenGroup", Path(user_cert_der))
        _allow_container_write(pki_dir)
        override_file = _write_docker_compose_override(override_dir, pki_dir)
        compose_args.extend(["-f", str(compose_file), "-f", str(override_file)])
    compose_args.extend(["up", "-d", "--wait", "--wait-timeout", str(COMPOSE_WAIT_TIMEOUT_WARM_SECONDS)])
    wait_budget_seconds = COMPOSE_WAIT_TIMEOUT_WARM_SECONDS
    if _should_build_docker_image(docker):
        compose_args.append("--build")
        # Cold build path: replace the warm budget with the cold budget.
        idx = compose_args.index("--wait-timeout")
        compose_args[idx + 1] = str(COMPOSE_WAIT_TIMEOUT_COLD_SECONDS)
        wait_budget_seconds = COMPOSE_WAIT_TIMEOUT_COLD_SECONDS
    # Outer subprocess timeout = compose --wait-timeout budget + 60s slack for
    # the docker CLI / daemon / image pull itself (--wait-timeout only bounds
    # the healthcheck poll, not docker build or registry I/O).
    outer_timeout = wait_budget_seconds + 60
    diagnostics_dir = _console_readiness_diagnostics_dir()
    try:
        result = subprocess.run(
            compose_args,
            cwd=str(_SERVER_RELEASE2),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=outer_timeout,
        )
    except subprocess.TimeoutExpired:
        # Compose itself hung past the outer ceiling — capture logs and abort
        # the auto-start path so live tests fail loudly instead of silently
        # waiting forever.
        capture_compose_logs_on_failure(
            diagnostics_dir,
            _SERVER_RELEASE2,
            "opcua-server",
            project=project,
            docker_executable=docker,
        )
        return None
    if result.returncode != 0:
        capture_compose_logs_on_failure(
            diagnostics_dir,
            _SERVER_RELEASE2,
            "opcua-server",
            project=project,
            docker_executable=docker,
        )
        if not preserve_test_artifacts():
            for path in (override_dir, pki_dir):
                if path is not None:
                    shutil.rmtree(path, ignore_errors=True)
        return None
    return StartedServer(
        temp_dir=override_dir,
        pki_dir=pki_dir,
        compose_dir=_SERVER_RELEASE2,
        compose_project=project,
    )


def _should_build_docker_image(docker: str) -> bool:
    if os.environ.get("IJT_DOCKER_COMPOSE_BUILD", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return True
    return is_image_stale(
        docker,
        _SERVER_DOCKER_IMAGE,
        _SERVER_LINUX_ZIP,
        cwd=_SERVER_RELEASE2,
    )


def _start_opcua_server(port: int) -> StartedServer | None:
    sut = os.environ.get("IJT_OPCUA_SECURITY_SUT", "").strip().lower()
    if sut == "linux":
        return _start_docker_server(port)
    if sut == "windows":
        return _start_windows_server(port)

    return _start_windows_server(port) or _start_docker_server(port)


def _stop_opcua_server(started: StartedServer) -> None:
    if started.process is not None:
        with contextlib.suppress(Exception):
            started.process.terminate()
            started.process.wait(timeout=5)

    if started.compose_dir is not None and started.compose_project is not None:
        docker = shutil.which("docker")
        if docker is not None:
            env = os.environ.copy()
            env["COMPOSE_PROJECT_NAME"] = started.compose_project
            subprocess.run(
                [docker, "compose", "down"],
                cwd=str(started.compose_dir),
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )

    if preserve_test_artifacts():
        return

    for path in (started.temp_dir, started.pki_dir):
        if path is not None:
            shutil.rmtree(path, ignore_errors=True)


# ── Session fixture: guarantee OPC UA server is up before any test runs ────────
@pytest.fixture(scope="session", autouse=True)
def ensure_opcua_server():
    """Auto-start OPC UA server for Console Client live tests.

    Never silently skips — calls pytest.fail() if the server cannot start.
    Only tears down the process that THIS fixture started.
    """
    host, port = _resolve_server_host_port()
    started_server: StartedServer | None = None
    _prepare_opcua_security_client_certificate()
    isolated_server = _isolated_server_requested()

    if isolated_server and _port_open(host, port):
        _kill_process_on_port(port)
        time.sleep(0.5)

    if not _port_open(host, port):
        server = _start_opcua_server(port)
        if server:
            started_server = server
            if not _wait_for_opcua_hello(host, port, timeout=60):
                _stop_opcua_server(server)
                pytest.fail(
                    f"OPC UA server process/container started but did not respond to a "
                    f"HELLO handshake on {host}:{port} within 60 s. Check server output "
                    f"or readiness diagnostics."
                )
        else:
            pytest.fail(
                f"OPC UA server is not running on {host}:{port} and cannot be "
                f"auto-started on {platform.system()}. "
                f"Start it manually or via Docker before running live tests."
            )
    elif isolated_server:
        pytest.fail(f"OPC UA port {port} is already in use and could not be cleared for an isolated managed run.")
    elif not _wait_for_opcua_hello(host, port, timeout=30):
        pytest.fail(
            f"OPC UA TCP port {port} is open, but the server did not answer a "
            f"HELLO handshake within 30 s. Start a real OPC UA simulator or "
            f"free the stale port before running live tests."
        )

    os.environ.setdefault("OPCUA_SERVER_URL", f"opc.tcp://{host}:{port}")

    yield

    if started_server is not None:
        _stop_opcua_server(started_server)


# ── Auto-mark all live tests ──────────────────────────────────────────────────
def pytest_collection_modifyitems(items):
    """Tag every test in tests/live/ with pytest.mark.live."""
    for item in items:
        if item.fspath and "live" in str(item.fspath):
            item.add_marker(pytest.mark.live)
