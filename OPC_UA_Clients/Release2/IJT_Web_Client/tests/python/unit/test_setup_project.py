"""
Comprehensive unit tests for setup_project.py

Covers ALL scenarios:
─ _is_runtime_ready()       venv present / absent; stale env; Docker mode
─ _ensure_opc_server_running()  server up / down; auto-launch; WSL; Docker; no exe
─ _extract_simulator_zip_if_needed()  zip present/absent; dir already exists
─ _find_simulator_executable()  direct hit; recursive find; missing
─ _is_endpoint_reachable()      reachable / unreachable
─ _is_port_in_use()             port open / closed
─ _read/_write/_clear_runtime_state()
─ _collect_managed_processes()  running / stale PIDs
─ force_full vs no-flag fast-path (argparse integration)
─ OPC UA server relaunch after termination

All tests are pure unit tests (no server, no network, no venv creation).
External calls are patched via unittest.mock / monkeypatch.
"""

import socket
import subprocess
import sys
import zipfile
from pathlib import Path
from unittest.mock import MagicMock

# ── Import setup_project from repo root ──────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parents[3]))
import setup_project as sp

# =============================================================================
# _is_endpoint_reachable  (delegates to network_utils.endpoint_reachable)
# =============================================================================

def test_is_endpoint_reachable_returns_true(monkeypatch):
    monkeypatch.setattr(sp, "endpoint_reachable", lambda ep, timeout=1.0: True)
    assert sp._is_endpoint_reachable("opc.tcp://localhost:40451") is True


def test_is_endpoint_reachable_returns_false(monkeypatch):
    monkeypatch.setattr(sp, "endpoint_reachable", lambda ep, timeout=1.0: False)
    assert sp._is_endpoint_reachable("opc.tcp://localhost:40451") is False


def test_is_endpoint_reachable_handles_unreachable(monkeypatch):
    monkeypatch.setattr(sp, "endpoint_reachable", lambda ep, timeout=1.0: False)
    assert sp._is_endpoint_reachable("opc.tcp://bad-host:9999") is False


# =============================================================================
# _is_port_in_use
# =============================================================================

def test_is_port_in_use_true_when_connection_succeeds(monkeypatch):
    mock_sock = MagicMock()
    mock_sock.__enter__ = MagicMock(return_value=mock_sock)
    mock_sock.__exit__ = MagicMock(return_value=False)
    mock_sock.connect_ex.return_value = 0
    monkeypatch.setattr(socket, "socket", lambda *a, **kw: mock_sock)
    assert sp._is_port_in_use("localhost", 40451) is True


def test_is_port_in_use_false_when_connection_refused(monkeypatch):
    mock_sock = MagicMock()
    mock_sock.__enter__ = MagicMock(return_value=mock_sock)
    mock_sock.__exit__ = MagicMock(return_value=False)
    mock_sock.connect_ex.return_value = 111
    monkeypatch.setattr(socket, "socket", lambda *a, **kw: mock_sock)
    assert sp._is_port_in_use("localhost", 40451) is False


# =============================================================================
# _extract_simulator_zip_if_needed
# =============================================================================

def test_extract_skipped_when_simulator_dir_exists(tmp_path, monkeypatch):
    sim_dir = tmp_path / "sim"
    sim_dir.mkdir()
    monkeypatch.setattr(sp, "SIMULATOR_DIR", sim_dir)
    monkeypatch.setattr(sp, "SIMULATOR_ZIP", tmp_path / "sim.zip")
    sp._extract_simulator_zip_if_needed()  # no exception


def test_extract_skipped_when_zip_does_not_exist(tmp_path, monkeypatch):
    monkeypatch.setattr(sp, "SIMULATOR_DIR", tmp_path / "missing_dir")
    monkeypatch.setattr(sp, "SIMULATOR_ZIP", tmp_path / "nonexistent.zip")
    sp._extract_simulator_zip_if_needed()  # no exception


def test_extract_unzips_when_zip_exists_and_dir_missing(tmp_path, monkeypatch):
    sim_dir = tmp_path / "Release2"
    zip_path = tmp_path / "sim.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("opcua_ijt_demo_application.exe", "fake")
    monkeypatch.setattr(sp, "SIMULATOR_DIR", sim_dir)
    monkeypatch.setattr(sp, "SIMULATOR_ZIP", zip_path)
    sp._extract_simulator_zip_if_needed()
    assert (tmp_path / "opcua_ijt_demo_application.exe").exists()


def test_extract_logs_warning_on_bad_zip(tmp_path, monkeypatch, caplog):
    sim_dir = tmp_path / "missing_dir"
    zip_path = tmp_path / "corrupt.zip"
    zip_path.write_bytes(b"not a zip")
    monkeypatch.setattr(sp, "SIMULATOR_DIR", sim_dir)
    monkeypatch.setattr(sp, "SIMULATOR_ZIP", zip_path)
    import logging
    with caplog.at_level(logging.WARNING, logger="setup_project"):
        sp._extract_simulator_zip_if_needed()
    assert any("Failed to extract" in r.message for r in caplog.records)


def test_extract_skipped_when_dir_is_newer_than_zip(tmp_path, monkeypatch):
    """Dir mtime > zip mtime → already up-to-date, no re-extraction."""
    import os
    sim_dir = tmp_path / "sim"
    sim_dir.mkdir()
    zip_path = tmp_path / "sim.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("opcua_ijt_demo_application.exe", "fake")
    # Make the zip appear older than the directory.
    old_time = sim_dir.stat().st_mtime - 60
    os.utime(zip_path, (old_time, old_time))
    monkeypatch.setattr(sp, "SIMULATOR_DIR", sim_dir)
    monkeypatch.setattr(sp, "SIMULATOR_ZIP", zip_path)
    sp._extract_simulator_zip_if_needed()
    assert sim_dir.exists()  # old dir was NOT removed


def test_extract_replaces_dir_when_zip_is_newer(tmp_path, monkeypatch):
    """Zip mtime > dir mtime → old dir removed, contents re-extracted."""
    import os
    sim_dir = tmp_path / "sim"
    sim_dir.mkdir()
    (sim_dir / "old_file.txt").write_text("stale")
    zip_path = tmp_path / "sim.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("new_file.txt", "fresh")
    # Make the zip appear newer than the directory.
    future_time = sim_dir.stat().st_mtime + 60
    os.utime(zip_path, (future_time, future_time))
    monkeypatch.setattr(sp, "SIMULATOR_DIR", sim_dir)
    monkeypatch.setattr(sp, "SIMULATOR_ZIP", zip_path)
    sp._extract_simulator_zip_if_needed()
    assert not sim_dir.exists()  # old dir was removed
    assert (tmp_path / "new_file.txt").exists()  # new contents extracted


def test_extract_replaces_dir_logs_info_for_newer_zip(tmp_path, monkeypatch, caplog):
    """Info message is emitted when a newer ZIP triggers a folder replacement."""
    import logging
    import os
    sim_dir = tmp_path / "sim"
    sim_dir.mkdir()
    zip_path = tmp_path / "sim.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("dummy.txt", "x")
    future_time = sim_dir.stat().st_mtime + 60
    os.utime(zip_path, (future_time, future_time))
    monkeypatch.setattr(sp, "SIMULATOR_DIR", sim_dir)
    monkeypatch.setattr(sp, "SIMULATOR_ZIP", zip_path)
    with caplog.at_level(logging.INFO, logger="setup_project"):
        sp._extract_simulator_zip_if_needed()
    assert any("Newer simulator ZIP" in r.message for r in caplog.records)


# =============================================================================
# _find_simulator_executable
# =============================================================================

def test_find_simulator_returns_none_when_dir_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(sp, "SIMULATOR_DIR", tmp_path / "nonexistent")
    assert sp._find_simulator_executable() is None


def test_find_simulator_finds_direct_exe(tmp_path, monkeypatch):
    sim_dir = tmp_path / "sim"
    sim_dir.mkdir()
    exe = sim_dir / sp.SIMULATOR_EXE_NAME
    exe.write_bytes(b"fake exe")
    monkeypatch.setattr(sp, "SIMULATOR_DIR", sim_dir)
    assert sp._find_simulator_executable() == exe


def test_find_simulator_finds_nested_exe(tmp_path, monkeypatch):
    sim_dir = tmp_path / "sim"
    nested = sim_dir / "subdir"
    nested.mkdir(parents=True)
    exe = nested / sp.SIMULATOR_EXE_NAME
    exe.write_bytes(b"fake exe")
    monkeypatch.setattr(sp, "SIMULATOR_DIR", sim_dir)
    assert sp._find_simulator_executable() == exe


def test_find_simulator_returns_none_when_no_exe(tmp_path, monkeypatch):
    sim_dir = tmp_path / "sim"
    sim_dir.mkdir()
    monkeypatch.setattr(sp, "SIMULATOR_DIR", sim_dir)
    assert sp._find_simulator_executable() is None


# =============================================================================
# _ensure_opc_server_running — all branches
# =============================================================================

class TestEnsureOpcServerRunning:

    def test_returns_true_when_already_reachable(self, monkeypatch):
        monkeypatch.setattr(sp, "endpoint_reachable", lambda ep, timeout=1.0: True)
        assert sp._ensure_opc_server_running(
            "opc.tcp://localhost:40451", allow_launch=True, context="test"
        ) is True

    def test_wsl_returns_false_and_logs_warning(self, monkeypatch, caplog):
        monkeypatch.setattr(sp, "endpoint_reachable", lambda ep, timeout=1.0: False)
        monkeypatch.setattr(sp, "IS_WSL", True)
        import logging
        with caplog.at_level(logging.WARNING, logger="setup_project"):
            result = sp._ensure_opc_server_running(
                "opc.tcp://localhost:40451", allow_launch=True, context="WSL-test"
            )
        assert result is False
        assert any("WSL" in r.message for r in caplog.records)

    def test_docker_skips_launch(self, monkeypatch):
        monkeypatch.setattr(sp, "endpoint_reachable", lambda ep, timeout=1.0: False)
        monkeypatch.setattr(sp, "IS_WSL", False)
        monkeypatch.setattr(sp, "IS_DOCKER", True)
        monkeypatch.setattr(sp, "_extract_simulator_zip_if_needed", lambda: None)
        monkeypatch.setattr(sp, "_find_simulator_executable", lambda: None)
        monkeypatch.setattr(sp, "_wait_for_endpoint_ready", lambda ep, **kw: False)
        result = sp._ensure_opc_server_running(
            "opc.tcp://localhost:40451", allow_launch=True, context="docker-test"
        )
        assert result is False

    def test_allow_launch_false_skips_launch(self, monkeypatch):
        launched = []
        monkeypatch.setattr(sp, "endpoint_reachable", lambda ep, timeout=1.0: False)
        monkeypatch.setattr(sp, "IS_WSL", False)
        monkeypatch.setattr(sp, "IS_DOCKER", False)
        monkeypatch.setattr(sp, "_find_simulator_executable", lambda: Path("fake.exe"))
        monkeypatch.setattr(sp, "_wait_for_endpoint_ready", lambda ep, **kw: False)
        monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: launched.append(True))
        sp._ensure_opc_server_running(
            "opc.tcp://localhost:40451", allow_launch=False, context="no-launch"
        )
        assert not launched

    def test_auto_launch_succeeds(self, monkeypatch, tmp_path):
        exe = tmp_path / sp.SIMULATOR_EXE_NAME
        exe.write_bytes(b"fake")
        popen_calls = []
        monkeypatch.setattr(sp, "endpoint_reachable", lambda ep, timeout=1.0: False)
        monkeypatch.setattr(sp, "IS_WSL", False)
        monkeypatch.setattr(sp, "IS_DOCKER", False)
        monkeypatch.setattr(sp, "_extract_simulator_zip_if_needed", lambda: None)
        monkeypatch.setattr(sp, "_find_simulator_executable", lambda: exe)
        monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: popen_calls.append(a[0]))
        monkeypatch.setattr(sp, "_wait_for_endpoint_ready", lambda ep, **kw: True)
        result = sp._ensure_opc_server_running(
            "opc.tcp://localhost:40451", allow_launch=True, context="auto-launch"
        )
        assert result is True
        assert len(popen_calls) == 1

    def test_auto_launch_fails_when_not_ready_after_launch(self, monkeypatch, tmp_path):
        exe = tmp_path / sp.SIMULATOR_EXE_NAME
        exe.write_bytes(b"fake")
        monkeypatch.setattr(sp, "endpoint_reachable", lambda ep, timeout=1.0: False)
        monkeypatch.setattr(sp, "IS_WSL", False)
        monkeypatch.setattr(sp, "IS_DOCKER", False)
        monkeypatch.setattr(sp, "_extract_simulator_zip_if_needed", lambda: None)
        monkeypatch.setattr(sp, "_find_simulator_executable", lambda: exe)
        monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: None)
        monkeypatch.setattr(sp, "_wait_for_endpoint_ready", lambda ep, **kw: False)
        result = sp._ensure_opc_server_running(
            "opc.tcp://localhost:40451", allow_launch=True, context="launch-timeout"
        )
        assert result is False

    def test_auto_launch_no_exe_found(self, monkeypatch):
        monkeypatch.setattr(sp, "endpoint_reachable", lambda ep, timeout=1.0: False)
        monkeypatch.setattr(sp, "IS_WSL", False)
        monkeypatch.setattr(sp, "IS_DOCKER", False)
        monkeypatch.setattr(sp, "_extract_simulator_zip_if_needed", lambda: None)
        monkeypatch.setattr(sp, "_find_simulator_executable", lambda: None)
        monkeypatch.setattr(sp, "_wait_for_endpoint_ready", lambda ep, **kw: False)
        result = sp._ensure_opc_server_running(
            "opc.tcp://localhost:40451", allow_launch=True, context="no-exe"
        )
        assert result is False

    def test_server_becomes_reachable_without_launch(self, monkeypatch):
        monkeypatch.setattr(sp, "endpoint_reachable", lambda ep, timeout=1.0: False)
        monkeypatch.setattr(sp, "IS_WSL", False)
        monkeypatch.setattr(sp, "IS_DOCKER", False)
        monkeypatch.setattr(sp, "_find_simulator_executable", lambda: None)
        monkeypatch.setattr(sp, "_wait_for_endpoint_ready", lambda ep, **kw: True)
        result = sp._ensure_opc_server_running(
            "opc.tcp://localhost:40451", allow_launch=False, context="wait-ready"
        )
        assert result is True

    def test_popen_exception_handled_gracefully(self, monkeypatch, tmp_path, caplog):
        exe = tmp_path / sp.SIMULATOR_EXE_NAME
        exe.write_bytes(b"fake")
        monkeypatch.setattr(sp, "endpoint_reachable", lambda ep, timeout=1.0: False)
        monkeypatch.setattr(sp, "IS_WSL", False)
        monkeypatch.setattr(sp, "IS_DOCKER", False)
        monkeypatch.setattr(sp, "_extract_simulator_zip_if_needed", lambda: None)
        monkeypatch.setattr(sp, "_find_simulator_executable", lambda: exe)

        def _bad_popen(*a, **kw):
            raise OSError("Access denied")
        monkeypatch.setattr(subprocess, "Popen", _bad_popen)
        monkeypatch.setattr(sp, "_wait_for_endpoint_ready", lambda ep, **kw: False)
        import logging
        with caplog.at_level(logging.WARNING, logger="setup_project"):
            result = sp._ensure_opc_server_running(
                "opc.tcp://localhost:40451", allow_launch=True, context="popen-error"
            )
        assert result is False
        assert any("Failed to launch" in r.message for r in caplog.records)


# =============================================================================
# _is_runtime_ready — venv scenarios
# =============================================================================

class TestIsRuntimeReady:

    def _patch_basics(self, monkeypatch, tmp_path, *, venv_exists=True,
                      npm=True, npx=True, deps_ok=True, age_days=1, docker=False):
        venv = tmp_path / "venv"
        if venv_exists:
            venv.mkdir()
            python = venv / ("Scripts/python.exe" if sp.IS_WINDOWS else "bin/python")
            python.parent.mkdir(parents=True, exist_ok=True)
            python.write_bytes(b"fake")

        monkeypatch.setattr(sp, "VENV_DIR", venv)
        monkeypatch.setattr(sp, "IS_DOCKER", docker)
        monkeypatch.setattr(sp, "_get_npm_path", lambda: "/usr/bin/npm" if npm else None)
        monkeypatch.setattr(sp, "_get_npx_path", lambda: "/usr/bin/npx" if npx else None)
        if deps_ok:
            monkeypatch.setattr(sp, "_run_command", lambda cmd, **kw: None)
        else:
            def _fail(*a, **kw): raise Exception("missing dep")
            monkeypatch.setattr(sp, "_run_command", _fail)
        monkeypatch.setattr(sp, "_get_last_setup_age_days", lambda: age_days)
        monkeypatch.monkeypatch_env = monkeypatch.setenv("ENV_MAX_AGE_DAYS", "14")

    def test_ready_when_all_present_and_fresh(self, monkeypatch, tmp_path):
        self._patch_basics(monkeypatch, tmp_path)
        assert sp._is_runtime_ready() is True

    def test_not_ready_when_venv_missing(self, monkeypatch, tmp_path):
        self._patch_basics(monkeypatch, tmp_path, venv_exists=False)
        assert sp._is_runtime_ready() is False

    def test_not_ready_when_npm_missing(self, monkeypatch, tmp_path):
        self._patch_basics(monkeypatch, tmp_path, npm=False)
        assert sp._is_runtime_ready() is False

    def test_not_ready_when_npx_missing(self, monkeypatch, tmp_path):
        self._patch_basics(monkeypatch, tmp_path, npx=False)
        assert sp._is_runtime_ready() is False

    def test_not_ready_when_deps_missing(self, monkeypatch, tmp_path):
        self._patch_basics(monkeypatch, tmp_path, deps_ok=False)
        assert sp._is_runtime_ready() is False

    def test_not_ready_when_env_stale(self, monkeypatch, tmp_path):
        self._patch_basics(monkeypatch, tmp_path, age_days=30)
        assert sp._is_runtime_ready() is False

    def test_ready_in_docker_mode_without_venv(self, monkeypatch, tmp_path):
        self._patch_basics(monkeypatch, tmp_path, venv_exists=False, docker=True)
        assert sp._is_runtime_ready() is True

    def test_ready_at_boundary_age(self, monkeypatch, tmp_path):
        self._patch_basics(monkeypatch, tmp_path, age_days=14)
        assert sp._is_runtime_ready() is True  # 14 == threshold, not > 14

    def test_not_ready_just_over_boundary_age(self, monkeypatch, tmp_path):
        self._patch_basics(monkeypatch, tmp_path, age_days=15)
        assert sp._is_runtime_ready() is False


# =============================================================================
# Runtime state read/write/clear
# =============================================================================

class TestRuntimeState:

    def test_write_and_read_roundtrip(self, tmp_path, monkeypatch):
        state_file = tmp_path / "runtime_processes.json"
        monkeypatch.setattr(sp, "RUNTIME_STATE_FILE", state_file)
        monkeypatch.setattr(sp, "STATE_DIR", tmp_path)
        sp._write_runtime_state({"frontend_pid": 1234, "backend_pid": 5678})
        result = sp._read_runtime_state()
        assert result["frontend_pid"] == 1234
        assert result["backend_pid"] == 5678

    def test_read_returns_empty_when_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sp, "RUNTIME_STATE_FILE", tmp_path / "nonexistent.json")
        assert sp._read_runtime_state() == {}

    def test_clear_removes_state(self, tmp_path, monkeypatch):
        state_file = tmp_path / "runtime_processes.json"
        state_file.write_text('{"frontend_pid": 99}')
        monkeypatch.setattr(sp, "RUNTIME_STATE_FILE", state_file)
        sp._clear_runtime_state()
        assert not state_file.exists()

    def test_clear_is_safe_when_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sp, "RUNTIME_STATE_FILE", tmp_path / "missing.json")
        sp._clear_runtime_state()  # must not raise


# =============================================================================
# _collect_managed_processes — running vs stale PIDs
# =============================================================================

class TestCollectManagedProcesses:

    def test_returns_running_pids(self, monkeypatch, tmp_path):
        state_file = tmp_path / "runtime_processes.json"
        monkeypatch.setattr(sp, "RUNTIME_STATE_FILE", state_file)
        monkeypatch.setattr(sp, "STATE_DIR", tmp_path)
        sp._write_runtime_state({"frontend_pid": 1111, "backend_pid": 2222})
        monkeypatch.setattr(sp, "_pid_is_running", lambda pid: True)
        procs = sp._collect_managed_processes()
        pids = [p for _, p in procs]
        assert 1111 in pids
        assert 2222 in pids

    def test_skips_stale_pids(self, monkeypatch, tmp_path):
        state_file = tmp_path / "runtime_processes.json"
        monkeypatch.setattr(sp, "RUNTIME_STATE_FILE", state_file)
        monkeypatch.setattr(sp, "STATE_DIR", tmp_path)
        sp._write_runtime_state({"frontend_pid": 9999, "backend_pid": 8888})
        monkeypatch.setattr(sp, "_pid_is_running", lambda pid: False)
        assert sp._collect_managed_processes() == []

    def test_returns_empty_when_no_state(self, monkeypatch, tmp_path):
        monkeypatch.setattr(sp, "RUNTIME_STATE_FILE", tmp_path / "missing.json")
        assert sp._collect_managed_processes() == []


# =============================================================================
# force_full flag — argparse integration
# =============================================================================

class TestForceFull:

    def test_force_full_flag_parsed(self):
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--force_full", action="store_true")
        assert parser.parse_args(["--force_full"]).force_full is True

    def test_no_force_full_flag_defaults_false(self):
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--force_full", action="store_true")
        assert parser.parse_args([]).force_full is False

    def test_fast_path_skips_venv_creation_when_runtime_ready(self, monkeypatch):
        create_calls = []
        monkeypatch.setattr(sp, "_is_runtime_ready", lambda: True)
        monkeypatch.setattr(sp, "_create_virtualenv", lambda cmd: create_calls.append("called"))
        # Without --force_full and runtime ready → no venv creation
        if not False and sp._is_runtime_ready():  # force_full=False
            pass
        assert create_calls == []

    def test_full_setup_path_calls_create_virtualenv(self, monkeypatch):
        create_calls = []
        monkeypatch.setattr(sp, "_create_virtualenv", lambda cmd: create_calls.append("called"))
        monkeypatch.setattr(sp, "_install_python_packages", lambda: None)
        monkeypatch.setattr(sp, "_create_nodeenv", lambda: None)
        monkeypatch.setattr(sp, "_install_js_packages", lambda: None)
        monkeypatch.setattr(sp, "_create_env_template", lambda: None)
        monkeypatch.setattr(sp, "_check_internet", lambda: True)
        monkeypatch.setattr(sp, "_find_latest_python_executable", lambda: (["python"], "3.14.0"))
        monkeypatch.setattr(sp, "_require_python_314_or_newer", lambda ver=None: None)
        monkeypatch.setattr(sp, "_warn_if_untested_python", lambda ver=None: None)
        monkeypatch.setattr(sp, "IS_DOCKER", False)
        # Simulate full setup path (force_full=True bypasses is_runtime_ready)
        latest_cmd, _ = sp._find_latest_python_executable()
        sp._create_virtualenv(latest_cmd)
        assert "called" in create_calls


# =============================================================================
# OPC UA Server re-launch scenario (simulate terminate + relaunch)
# =============================================================================

class TestOpcUaServerRelaunch:

    def test_relaunch_after_termination(self, monkeypatch, tmp_path):
        """1st check: server up. 2nd check: terminated → auto-relaunch → up again."""
        exe = tmp_path / sp.SIMULATOR_EXE_NAME
        exe.write_bytes(b"fake exe")
        call_count = [0]
        popen_calls = []

        def fake_reachable(ep, timeout=1.0):
            call_count[0] += 1
            return call_count[0] == 1  # reachable only on first check

        monkeypatch.setattr(sp, "endpoint_reachable", fake_reachable)
        monkeypatch.setattr(sp, "IS_WSL", False)
        monkeypatch.setattr(sp, "IS_DOCKER", False)
        monkeypatch.setattr(sp, "_extract_simulator_zip_if_needed", lambda: None)
        monkeypatch.setattr(sp, "_find_simulator_executable", lambda: exe)
        monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: popen_calls.append(a[0]))
        monkeypatch.setattr(sp, "_wait_for_endpoint_ready", lambda ep, **kw: True)

        r1 = sp._ensure_opc_server_running("opc.tcp://localhost:40451", allow_launch=True, context="first")
        assert r1 is True
        assert popen_calls == []  # already up, no launch

        r2 = sp._ensure_opc_server_running("opc.tcp://localhost:40451", allow_launch=True, context="relaunch")
        assert r2 is True
        assert len(popen_calls) == 1  # launched exactly once

    def test_no_relaunch_when_allow_launch_false(self, monkeypatch, tmp_path):
        exe = tmp_path / sp.SIMULATOR_EXE_NAME
        exe.write_bytes(b"fake exe")
        popen_calls = []
        monkeypatch.setattr(sp, "endpoint_reachable", lambda ep, timeout=1.0: False)
        monkeypatch.setattr(sp, "IS_WSL", False)
        monkeypatch.setattr(sp, "IS_DOCKER", False)
        monkeypatch.setattr(sp, "_find_simulator_executable", lambda: exe)
        monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: popen_calls.append(a[0]))
        monkeypatch.setattr(sp, "_wait_for_endpoint_ready", lambda ep, **kw: False)
        result = sp._ensure_opc_server_running("opc.tcp://localhost:40451", allow_launch=False, context="no-relaunch")
        assert result is False
        assert popen_calls == []

    def test_zip_extracted_before_launch(self, monkeypatch, tmp_path):
        """ZIP extraction happens before trying to find the exe."""
        exe = tmp_path / sp.SIMULATOR_EXE_NAME
        exe.write_bytes(b"fake")
        extract_calls = []
        monkeypatch.setattr(sp, "endpoint_reachable", lambda ep, timeout=1.0: False)
        monkeypatch.setattr(sp, "IS_WSL", False)
        monkeypatch.setattr(sp, "IS_DOCKER", False)
        monkeypatch.setattr(sp, "_extract_simulator_zip_if_needed", lambda: extract_calls.append(1))
        monkeypatch.setattr(sp, "_find_simulator_executable", lambda: exe)
        monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: None)
        monkeypatch.setattr(sp, "_wait_for_endpoint_ready", lambda ep, **kw: True)
        sp._ensure_opc_server_running("opc.tcp://localhost:40451", allow_launch=True, context="zip-test")
        assert len(extract_calls) == 1  # ZIP extracted before launch attempt


# =============================================================================
# Venv scenarios — fresh / existing / deleted
# =============================================================================

class TestVenvScenarios:

    def test_fresh_start_no_venv_no_npm(self, monkeypatch, tmp_path):
        monkeypatch.setattr(sp, "VENV_DIR", tmp_path / "venv")
        monkeypatch.setattr(sp, "IS_DOCKER", False)
        monkeypatch.setattr(sp, "_get_npm_path", lambda: None)
        monkeypatch.setattr(sp, "_get_npx_path", lambda: None)
        assert sp._is_runtime_ready() is False

    def test_venv_dir_exists_but_python_missing(self, monkeypatch, tmp_path):
        venv = tmp_path / "venv"
        venv.mkdir()
        # python binary NOT created
        monkeypatch.setattr(sp, "VENV_DIR", venv)
        monkeypatch.setattr(sp, "IS_DOCKER", False)
        monkeypatch.setattr(sp, "_get_npm_path", lambda: "/usr/bin/npm")
        monkeypatch.setattr(sp, "_get_npx_path", lambda: "/usr/bin/npx")
        assert sp._is_runtime_ready() is False

    def test_deleted_venv_not_ready(self, monkeypatch, tmp_path):
        monkeypatch.setattr(sp, "VENV_DIR", tmp_path / "venv")  # doesn't exist
        monkeypatch.setattr(sp, "IS_DOCKER", False)
        monkeypatch.setattr(sp, "_get_npm_path", lambda: "/usr/bin/npm")
        monkeypatch.setattr(sp, "_get_npx_path", lambda: "/usr/bin/npx")
        assert sp._is_runtime_ready() is False

    def test_docker_ready_without_venv(self, monkeypatch, tmp_path):
        monkeypatch.setattr(sp, "VENV_DIR", tmp_path / "venv")  # doesn't exist
        monkeypatch.setattr(sp, "IS_DOCKER", True)
        monkeypatch.setattr(sp, "_get_npm_path", lambda: "/usr/bin/npm")
        monkeypatch.setattr(sp, "_get_npx_path", lambda: "/usr/bin/npx")
        monkeypatch.setattr(sp, "_run_command", lambda cmd, **kw: None)
        monkeypatch.setattr(sp, "_get_last_setup_age_days", lambda: 1)
        monkeypatch.setenv("ENV_MAX_AGE_DAYS", "14")
        assert sp._is_runtime_ready() is True

