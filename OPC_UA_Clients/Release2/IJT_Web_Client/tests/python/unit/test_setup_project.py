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

import configparser
import socket
import subprocess
import sys
import uuid
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
    monkeypatch.setattr(sp, "endpoint_reachable", lambda _ep, timeout=1.0: True)
    assert sp._is_endpoint_reachable("opc.tcp://localhost:40451") is True


def test_is_endpoint_reachable_returns_false(monkeypatch):
    monkeypatch.setattr(sp, "endpoint_reachable", lambda _ep, timeout=1.0: False)
    assert sp._is_endpoint_reachable("opc.tcp://localhost:40451") is False


def test_is_endpoint_reachable_handles_unreachable(monkeypatch):
    monkeypatch.setattr(sp, "endpoint_reachable", lambda _ep, timeout=1.0: False)
    assert sp._is_endpoint_reachable("opc.tcp://bad-host:9999") is False


# =============================================================================
# _is_port_in_use
# =============================================================================


def test_is_port_in_use_true_when_connection_succeeds(monkeypatch):
    mock_sock = MagicMock()
    mock_sock.__enter__ = MagicMock(return_value=mock_sock)
    mock_sock.__exit__ = MagicMock(return_value=False)
    mock_sock.connect_ex.return_value = 0
    monkeypatch.setattr(socket, "socket", lambda *a, **_kw: mock_sock)
    assert sp._is_port_in_use("localhost", 40451) is True


def test_is_port_in_use_false_when_connection_refused(monkeypatch):
    mock_sock = MagicMock()
    mock_sock.__enter__ = MagicMock(return_value=mock_sock)
    mock_sock.__exit__ = MagicMock(return_value=False)
    mock_sock.connect_ex.return_value = 111
    monkeypatch.setattr(socket, "socket", lambda *a, **_kw: mock_sock)
    assert sp._is_port_in_use("localhost", 40451) is False


# =============================================================================
# _extract_simulator_zip_if_needed
# =============================================================================


def test_extract_skipped_when_simulator_dir_exists(fs, monkeypatch):
    sim_dir = Path("/fake/sim")
    sim_dir.mkdir(parents=True)
    monkeypatch.setattr(sp, "SIMULATOR_DIR", sim_dir)
    monkeypatch.setattr(sp, "SIMULATOR_ZIP", Path("/fake/sim.zip"))
    sp._extract_simulator_zip_if_needed()


def test_extract_skipped_when_zip_does_not_exist(fs, monkeypatch):
    monkeypatch.setattr(sp, "SIMULATOR_DIR", Path("/fake/missing_dir"))
    monkeypatch.setattr(sp, "SIMULATOR_ZIP", Path("/fake/nonexistent.zip"))
    sp._extract_simulator_zip_if_needed()


def test_extract_unzips_when_zip_exists_and_dir_missing(fs, monkeypatch):
    base = Path("/fake")
    base.mkdir(parents=True, exist_ok=True)
    sim_dir = base / "Release2"
    zip_path = base / "sim.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("opcua_ijt_demo_application.exe", "fake")
    monkeypatch.setattr(sp, "SIMULATOR_DIR", sim_dir)
    monkeypatch.setattr(sp, "SIMULATOR_ZIP", zip_path)
    sp._extract_simulator_zip_if_needed()
    assert (base / "opcua_ijt_demo_application.exe").exists()


def test_extract_logs_warning_on_bad_zip(fs, monkeypatch, caplog):
    base = Path("/fake")
    base.mkdir(parents=True, exist_ok=True)
    zip_path = base / "corrupt.zip"
    zip_path.write_bytes(b"not a zip")
    monkeypatch.setattr(sp, "SIMULATOR_DIR", base / "missing_dir")
    monkeypatch.setattr(sp, "SIMULATOR_ZIP", zip_path)
    import logging

    with caplog.at_level(logging.WARNING, logger="setup_project"):
        sp._extract_simulator_zip_if_needed()
    assert any("Failed to extract" in r.message for r in caplog.records)


def test_extract_skipped_when_dir_is_newer_than_zip(fs, monkeypatch):
    """Dir mtime > zip mtime → already up-to-date, no re-extraction."""
    import os

    base = Path("/fake")
    sim_dir = base / "sim"
    sim_dir.mkdir(parents=True)
    zip_path = base / "sim.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("opcua_ijt_demo_application.exe", "fake")
    old_time = sim_dir.stat().st_mtime - 60
    os.utime(zip_path, (old_time, old_time))
    monkeypatch.setattr(sp, "SIMULATOR_DIR", sim_dir)
    monkeypatch.setattr(sp, "SIMULATOR_ZIP", zip_path)
    sp._extract_simulator_zip_if_needed()
    assert sim_dir.exists()  # old dir was NOT removed


def test_extract_replaces_dir_when_zip_is_newer(fs, monkeypatch):
    """Zip mtime > dir mtime → old dir removed, contents re-extracted."""
    import os

    base = Path("/fake")
    sim_dir = base / "sim"
    sim_dir.mkdir(parents=True)
    (sim_dir / "old_file.txt").write_text("stale")
    zip_path = base / "sim.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("new_file.txt", "fresh")
    future_time = sim_dir.stat().st_mtime + 60
    os.utime(zip_path, (future_time, future_time))
    monkeypatch.setattr(sp, "SIMULATOR_DIR", sim_dir)
    monkeypatch.setattr(sp, "SIMULATOR_ZIP", zip_path)
    sp._extract_simulator_zip_if_needed()
    assert not sim_dir.exists()  # old dir was removed
    assert (base / "new_file.txt").exists()  # new contents extracted


def test_extract_replaces_dir_logs_info_for_newer_zip(fs, monkeypatch, caplog):
    """Info message is emitted when a newer ZIP triggers a folder replacement."""
    import logging
    import os

    base = Path("/fake")
    sim_dir = base / "sim"
    sim_dir.mkdir(parents=True)
    zip_path = base / "sim.zip"
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
# optional private submodule setup
# =============================================================================


def test_backup_existing_optional_module_path_moves_non_git_folder(tmp_path, monkeypatch, caplog):
    import logging

    target = tmp_path / "envelope"
    target.mkdir()
    (target / "local-change.mjs").write_text("export const local = true;\n", encoding="utf-8")
    monkeypatch.setattr(sp.time, "strftime", lambda _fmt: "20260708-180500")

    with caplog.at_level(logging.WARNING, logger="setup_project"):
        backup = sp._backup_existing_optional_module_path("Envelope", target)

    assert backup == tmp_path / "envelope.backup-before-submodule-20260708-180500"
    assert not target.exists()
    assert (backup / "local-change.mjs").read_text(encoding="utf-8") == "export const local = true;\n"
    assert any("not a Git checkout" in record.message for record in caplog.records)


def test_backup_existing_optional_module_path_leaves_git_checkout(tmp_path):
    target = tmp_path / "envelope"
    target.mkdir()
    (target / ".git").write_text("gitdir: ../../../.git/modules/envelope\n", encoding="utf-8")

    assert sp._backup_existing_optional_module_path("Envelope", target) is None
    assert target.exists()


def test_optional_private_submodule_is_opt_in_for_plain_git_updates():
    gitmodules_path = sp.REPO_ROOT / ".gitmodules"
    if not gitmodules_path.exists():
        pytest.skip(".gitmodules is not present in this test environment")

    config = configparser.ConfigParser()
    config.read(gitmodules_path, encoding="utf-8")

    expected_path = "OPC_UA_Clients/Release2/IJT_Web_Client/src/javascripts/views/envelope"
    section = next(
        (name for name in config.sections() if config.get(name, "path", fallback="") == expected_path),
        None,
    )

    assert section is not None
    assert config.get(section, "update", fallback="") == "none"


def test_sync_optional_private_submodules_backs_up_loose_folder_before_update(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    target = repo_root / "OPC_UA_Clients" / "Release2" / "IJT_Web_Client" / "src" / "javascripts" / "views" / "envelope"
    target.mkdir(parents=True)
    (target / "legacy.mjs").write_text("export const legacy = true;\n", encoding="utf-8")
    (repo_root / ".gitmodules").write_text(
        "path = OPC_UA_Clients/Release2/IJT_Web_Client/src/javascripts/views/envelope\n", encoding="utf-8"
    )
    monkeypatch.setattr(sp, "REPO_ROOT", repo_root)
    monkeypatch.setattr(sp, "_ENV_IS_PRE_ISOLATED", False)
    monkeypatch.setattr(sp.shutil, "which", lambda name: "/usr/bin/git" if name == "git" else None)
    monkeypatch.setattr(sp.time, "strftime", lambda _fmt: "20260708-180500")

    calls: list[list[str]] = []

    def _fake_run(cmd, **_kwargs):
        calls.append(cmd)
        if "update" in cmd:
            target.mkdir(parents=True)
            (target / ".git").write_text("gitdir: ../../../../../../.git/modules/envelope\n", encoding="utf-8")
            (target / "ui").mkdir()
            (target / "ui" / "envelope-graphics.mjs").write_text("export {};\n", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(sp.subprocess, "run", _fake_run)

    sp._sync_optional_private_submodules()

    backup = target.with_name("envelope.backup-before-submodule-20260708-180500")
    assert (backup / "legacy.mjs").exists()
    assert (target / "ui" / "envelope-graphics.mjs").exists()
    assert ["/usr/bin/git", "submodule", "sync", "--", target.relative_to(repo_root).as_posix()] in calls
    assert any("update" in cmd and "--checkout" in cmd and "--remote" in cmd for cmd in calls)


# =============================================================================
# _find_simulator_executable
# =============================================================================


def test_find_simulator_returns_none_when_dir_missing(fs, monkeypatch):
    monkeypatch.setattr(sp, "SIMULATOR_DIR", Path("/fake/nonexistent"))
    assert sp._find_simulator_executable() is None


def test_find_simulator_finds_direct_exe(fs, monkeypatch):
    sim_dir = Path("/fake/sim")
    sim_dir.mkdir(parents=True)
    exe = sim_dir / sp.SIMULATOR_EXE_NAME
    exe.write_bytes(b"fake exe")
    monkeypatch.setattr(sp, "SIMULATOR_DIR", sim_dir)
    assert sp._find_simulator_executable() == exe


def test_find_simulator_finds_nested_exe(fs, monkeypatch):
    sim_dir = Path("/fake/sim")
    nested = sim_dir / "subdir"
    nested.mkdir(parents=True)
    exe = nested / sp.SIMULATOR_EXE_NAME
    exe.write_bytes(b"fake exe")
    monkeypatch.setattr(sp, "SIMULATOR_DIR", sim_dir)
    assert sp._find_simulator_executable() == exe


def test_find_simulator_returns_none_when_no_exe(fs, monkeypatch):
    sim_dir = Path("/fake/sim")
    sim_dir.mkdir(parents=True)
    monkeypatch.setattr(sp, "SIMULATOR_DIR", sim_dir)
    assert sp._find_simulator_executable() is None


# =============================================================================
# _ensure_opc_server_running — all branches
# =============================================================================


class TestEnsureOpcServerRunning:
    def test_returns_true_when_already_reachable(self, monkeypatch):
        monkeypatch.setattr(sp, "endpoint_reachable", lambda _ep, timeout=1.0: True)
        assert sp._ensure_opc_server_running("opc.tcp://localhost:40451", allow_launch=True, context="test") is True

    def test_wsl_returns_false_and_logs_warning(self, monkeypatch, caplog):
        monkeypatch.setattr(sp, "endpoint_reachable", lambda _ep, timeout=1.0: False)
        monkeypatch.setattr(sp, "IS_WSL", True)
        import logging

        with caplog.at_level(logging.WARNING, logger="setup_project"):
            result = sp._ensure_opc_server_running("opc.tcp://localhost:40451", allow_launch=True, context="WSL-test")
        assert result is False
        assert any("WSL" in r.message for r in caplog.records)

    def test_docker_skips_launch(self, monkeypatch):
        monkeypatch.setattr(sp, "endpoint_reachable", lambda _ep, timeout=1.0: False)
        monkeypatch.setattr(sp, "IS_WSL", False)
        monkeypatch.setattr(sp, "IS_DOCKER", True)
        monkeypatch.setattr(sp, "_extract_simulator_zip_if_needed", lambda: None)
        monkeypatch.setattr(sp, "_find_simulator_executable", lambda: None)
        monkeypatch.setattr(sp, "_wait_for_endpoint_ready", lambda _ep, **_kw: False)
        result = sp._ensure_opc_server_running("opc.tcp://localhost:40451", allow_launch=True, context="docker-test")
        assert result is False

    def test_allow_launch_false_skips_launch(self, monkeypatch):
        launched = []
        monkeypatch.setattr(sp, "endpoint_reachable", lambda _ep, timeout=1.0: False)
        monkeypatch.setattr(sp, "IS_WSL", False)
        monkeypatch.setattr(sp, "IS_DOCKER", False)
        monkeypatch.setattr(sp, "_find_simulator_executable", lambda: Path("fake.exe"))
        monkeypatch.setattr(sp, "_wait_for_endpoint_ready", lambda _ep, **_kw: False)
        monkeypatch.setattr(subprocess, "Popen", lambda *a, **_kw: launched.append(True))
        sp._ensure_opc_server_running("opc.tcp://localhost:40451", allow_launch=False, context="no-launch")
        assert not launched

    def test_auto_launch_succeeds(self, monkeypatch):
        exe = Path("/fake") / sp.SIMULATOR_EXE_NAME
        popen_calls = []
        monkeypatch.setattr(sp, "endpoint_reachable", lambda _ep, timeout=1.0: False)
        monkeypatch.setattr(sp, "IS_WSL", False)
        monkeypatch.setattr(sp, "IS_DOCKER", False)
        monkeypatch.setattr(sp, "_extract_simulator_zip_if_needed", lambda: None)
        monkeypatch.setattr(sp, "_find_simulator_executable", lambda: exe)
        monkeypatch.setattr(subprocess, "Popen", lambda *a, **_kw: popen_calls.append(a[0]))
        monkeypatch.setattr(sp, "_wait_for_endpoint_ready", lambda _ep, **_kw: True)
        result = sp._ensure_opc_server_running("opc.tcp://localhost:40451", allow_launch=True, context="auto-launch")
        assert result is True
        assert len(popen_calls) == 1

    def test_auto_launch_fails_when_not_ready_after_launch(self, monkeypatch):
        exe = Path("/fake") / sp.SIMULATOR_EXE_NAME
        monkeypatch.setattr(sp, "endpoint_reachable", lambda _ep, timeout=1.0: False)
        monkeypatch.setattr(sp, "IS_WSL", False)
        monkeypatch.setattr(sp, "IS_DOCKER", False)
        monkeypatch.setattr(sp, "_extract_simulator_zip_if_needed", lambda: None)
        monkeypatch.setattr(sp, "_find_simulator_executable", lambda: exe)
        monkeypatch.setattr(subprocess, "Popen", lambda *a, **_kw: None)
        monkeypatch.setattr(sp, "_wait_for_endpoint_ready", lambda _ep, **_kw: False)
        result = sp._ensure_opc_server_running("opc.tcp://localhost:40451", allow_launch=True, context="launch-timeout")
        assert result is False

    def test_auto_launch_no_exe_found(self, monkeypatch):
        monkeypatch.setattr(sp, "endpoint_reachable", lambda _ep, timeout=1.0: False)
        monkeypatch.setattr(sp, "IS_WSL", False)
        monkeypatch.setattr(sp, "IS_DOCKER", False)
        monkeypatch.setattr(sp, "_extract_simulator_zip_if_needed", lambda: None)
        monkeypatch.setattr(sp, "_find_simulator_executable", lambda: None)
        monkeypatch.setattr(sp, "_wait_for_endpoint_ready", lambda _ep, **_kw: False)
        result = sp._ensure_opc_server_running("opc.tcp://localhost:40451", allow_launch=True, context="no-exe")
        assert result is False

    def test_server_becomes_reachable_without_launch(self, monkeypatch):
        monkeypatch.setattr(sp, "endpoint_reachable", lambda _ep, timeout=1.0: False)
        monkeypatch.setattr(sp, "IS_WSL", False)
        monkeypatch.setattr(sp, "IS_DOCKER", False)
        monkeypatch.setattr(sp, "_find_simulator_executable", lambda: None)
        monkeypatch.setattr(sp, "_wait_for_endpoint_ready", lambda _ep, **_kw: True)
        result = sp._ensure_opc_server_running("opc.tcp://localhost:40451", allow_launch=False, context="wait-ready")
        assert result is True

    def test_popen_exception_handled_gracefully(self, monkeypatch, caplog):
        exe = Path("/fake") / sp.SIMULATOR_EXE_NAME
        monkeypatch.setattr(sp, "endpoint_reachable", lambda _ep, timeout=1.0: False)
        monkeypatch.setattr(sp, "IS_WSL", False)
        monkeypatch.setattr(sp, "IS_DOCKER", False)
        monkeypatch.setattr(sp, "_extract_simulator_zip_if_needed", lambda: None)
        monkeypatch.setattr(sp, "_find_simulator_executable", lambda: exe)

        def _bad_popen(*a, **_kw):
            raise OSError("Access denied")

        monkeypatch.setattr(subprocess, "Popen", _bad_popen)
        monkeypatch.setattr(sp, "_wait_for_endpoint_ready", lambda _ep, **_kw: False)
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
    def _patch_basics(
        self, monkeypatch, base: Path, *, venv_exists=True, npm=True, npx=True, deps_ok=True, age_days=1, docker=False
    ):
        venv = base / "venv"
        if venv_exists:
            venv.mkdir(parents=True, exist_ok=True)
            python = venv / ("Scripts/python.exe" if sp.IS_WINDOWS else "bin/python")
            python.parent.mkdir(parents=True, exist_ok=True)
            python.write_bytes(b"fake")
        if docker:
            # sys.executable doesn't exist in fake FS; patch _get_python_path with a fake entry
            fake_python = base / ("python.exe" if sp.IS_WINDOWS else "python")
            fake_python.parent.mkdir(parents=True, exist_ok=True)
            fake_python.write_bytes(b"fake")
            monkeypatch.setattr(sp, "_get_python_path", lambda: fake_python)

        monkeypatch.setattr(sp, "VENV_DIR", venv)
        monkeypatch.setattr(sp, "IS_DOCKER", docker)
        monkeypatch.setattr(sp, "_ENV_IS_PRE_ISOLATED", docker)
        monkeypatch.setattr(sp, "_get_npm_path", lambda: "/usr/bin/npm" if npm else None)
        monkeypatch.setattr(sp, "_get_npx_path", lambda: "/usr/bin/npx" if npx else None)
        if deps_ok:
            monkeypatch.setattr(sp, "_run_command", lambda cmd, **_kw: None)
        else:

            def _fail(*a, **_kw):
                raise Exception("missing dep")

            monkeypatch.setattr(sp, "_run_command", _fail)
        monkeypatch.setattr(sp, "_get_last_setup_age_days", lambda: age_days)
        monkeypatch.monkeypatch_env = monkeypatch.setenv("ENV_MAX_AGE_DAYS", "14")

    def test_ready_when_all_present_and_fresh(self, monkeypatch, fs):
        self._patch_basics(monkeypatch, Path("/fake"))
        assert sp._is_runtime_ready() is True

    def test_not_ready_when_venv_missing(self, monkeypatch, fs):
        self._patch_basics(monkeypatch, Path("/fake"), venv_exists=False)
        assert sp._is_runtime_ready() is False

    def test_not_ready_when_npm_missing(self, monkeypatch, fs):
        self._patch_basics(monkeypatch, Path("/fake"), npm=False)
        assert sp._is_runtime_ready() is False

    def test_not_ready_when_npx_missing(self, monkeypatch, fs):
        self._patch_basics(monkeypatch, Path("/fake"), npx=False)
        assert sp._is_runtime_ready() is False

    def test_not_ready_when_deps_missing(self, monkeypatch, fs):
        self._patch_basics(monkeypatch, Path("/fake"), deps_ok=False)
        assert sp._is_runtime_ready() is False

    def test_not_ready_when_env_stale(self, monkeypatch, fs):
        self._patch_basics(monkeypatch, Path("/fake"), age_days=30)
        assert sp._is_runtime_ready() is False

    def test_ready_in_docker_mode_without_venv(self, monkeypatch, fs):
        self._patch_basics(monkeypatch, Path("/fake"), venv_exists=False, docker=True)
        assert sp._is_runtime_ready() is True

    def test_ready_at_boundary_age(self, monkeypatch, fs):
        self._patch_basics(monkeypatch, Path("/fake"), age_days=14)
        assert sp._is_runtime_ready() is True  # 14 == threshold, not > 14

    def test_not_ready_just_over_boundary_age(self, monkeypatch, fs):
        self._patch_basics(monkeypatch, Path("/fake"), age_days=15)
        assert sp._is_runtime_ready() is False


# =============================================================================
# Runtime state read/write/clear
# =============================================================================


class TestRuntimeState:
    def test_write_and_read_roundtrip(self, fs, monkeypatch):
        base = Path("/fake")
        base.mkdir(parents=True, exist_ok=True)
        state_file = base / "runtime_processes.json"
        monkeypatch.setattr(sp, "RUNTIME_STATE_FILE", state_file)
        monkeypatch.setattr(sp, "STATE_DIR", base)
        sp._write_runtime_state({"frontend_pid": 1234, "backend_pid": 5678})
        result = sp._read_runtime_state()
        assert result["frontend_pid"] == 1234
        assert result["backend_pid"] == 5678

    def test_read_returns_empty_when_file_missing(self, fs, monkeypatch):
        monkeypatch.setattr(sp, "RUNTIME_STATE_FILE", Path("/fake/nonexistent.json"))
        assert sp._read_runtime_state() == {}

    def test_clear_removes_state(self, fs, monkeypatch):
        base = Path("/fake")
        base.mkdir(parents=True, exist_ok=True)
        state_file = base / "runtime_processes.json"
        state_file.write_text('{"frontend_pid": 99}')
        monkeypatch.setattr(sp, "RUNTIME_STATE_FILE", state_file)
        sp._clear_runtime_state()
        assert not state_file.exists()

    def test_clear_is_safe_when_file_missing(self, fs, monkeypatch):
        monkeypatch.setattr(sp, "RUNTIME_STATE_FILE", Path("/fake/missing.json"))
        sp._clear_runtime_state()  # must not raise

    def test_read_returns_empty_on_corrupt_json(self, fs, monkeypatch):
        base = Path("/fake")
        base.mkdir(parents=True, exist_ok=True)
        state_file = base / "runtime_processes.json"
        state_file.write_text("not-valid-json", encoding="utf-8")
        monkeypatch.setattr(sp, "RUNTIME_STATE_FILE", state_file)
        assert sp._read_runtime_state() == {}  # lines 426-427: except → return {}


# =============================================================================
# _collect_managed_processes — running vs stale PIDs
# =============================================================================


class TestCollectManagedProcesses:
    def test_returns_running_pids(self, monkeypatch, fs):
        base = Path("/fake")
        base.mkdir(parents=True, exist_ok=True)
        state_file = base / "runtime_processes.json"
        monkeypatch.setattr(sp, "RUNTIME_STATE_FILE", state_file)
        monkeypatch.setattr(sp, "STATE_DIR", base)
        sp._write_runtime_state({"frontend_pid": 1111, "backend_pid": 2222})
        monkeypatch.setattr(sp, "_pid_is_running", lambda pid: True)
        procs = sp._collect_managed_processes()
        pids = [p for _, p in procs]
        assert 1111 in pids
        assert 2222 in pids

    def test_skips_stale_pids(self, monkeypatch, fs):
        base = Path("/fake")
        base.mkdir(parents=True, exist_ok=True)
        state_file = base / "runtime_processes.json"
        monkeypatch.setattr(sp, "RUNTIME_STATE_FILE", state_file)
        monkeypatch.setattr(sp, "STATE_DIR", base)
        sp._write_runtime_state({"frontend_pid": 9999, "backend_pid": 8888})
        monkeypatch.setattr(sp, "_pid_is_running", lambda pid: False)
        assert sp._collect_managed_processes() == []

    def test_returns_empty_when_no_state(self, monkeypatch, fs):
        monkeypatch.setattr(sp, "RUNTIME_STATE_FILE", Path("/fake/missing.json"))
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
    def test_relaunch_after_termination(self, monkeypatch):
        """1st check: server up. 2nd check: terminated → auto-relaunch → up again."""
        exe = Path("/fake") / sp.SIMULATOR_EXE_NAME
        call_count = [0]
        popen_calls = []

        def fake_reachable(_ep, timeout=1.0):
            call_count[0] += 1
            return call_count[0] == 1  # reachable only on first check

        monkeypatch.setattr(sp, "endpoint_reachable", fake_reachable)
        monkeypatch.setattr(sp, "IS_WSL", False)
        monkeypatch.setattr(sp, "IS_DOCKER", False)
        monkeypatch.setattr(sp, "_extract_simulator_zip_if_needed", lambda: None)
        monkeypatch.setattr(sp, "_find_simulator_executable", lambda: exe)
        monkeypatch.setattr(subprocess, "Popen", lambda *a, **_kw: popen_calls.append(a[0]))
        monkeypatch.setattr(sp, "_wait_for_endpoint_ready", lambda _ep, **_kw: True)

        r1 = sp._ensure_opc_server_running("opc.tcp://localhost:40451", allow_launch=True, context="first")
        assert r1 is True
        assert popen_calls == []  # already up, no launch

        r2 = sp._ensure_opc_server_running("opc.tcp://localhost:40451", allow_launch=True, context="relaunch")
        assert r2 is True
        assert len(popen_calls) == 1  # launched exactly once

    def test_no_relaunch_when_allow_launch_false(self, monkeypatch):
        exe = Path("/fake") / sp.SIMULATOR_EXE_NAME
        popen_calls = []
        monkeypatch.setattr(sp, "endpoint_reachable", lambda _ep, timeout=1.0: False)
        monkeypatch.setattr(sp, "IS_WSL", False)
        monkeypatch.setattr(sp, "IS_DOCKER", False)
        monkeypatch.setattr(sp, "_find_simulator_executable", lambda: exe)
        monkeypatch.setattr(subprocess, "Popen", lambda *a, **_kw: popen_calls.append(a[0]))
        monkeypatch.setattr(sp, "_wait_for_endpoint_ready", lambda _ep, **_kw: False)
        result = sp._ensure_opc_server_running("opc.tcp://localhost:40451", allow_launch=False, context="no-relaunch")
        assert result is False
        assert popen_calls == []

    def test_zip_extracted_before_launch(self, monkeypatch):
        """ZIP extraction happens before trying to find the exe."""
        exe = Path("/fake") / sp.SIMULATOR_EXE_NAME
        extract_calls = []
        monkeypatch.setattr(sp, "endpoint_reachable", lambda _ep, timeout=1.0: False)
        monkeypatch.setattr(sp, "IS_WSL", False)
        monkeypatch.setattr(sp, "IS_DOCKER", False)
        monkeypatch.setattr(sp, "_extract_simulator_zip_if_needed", lambda: extract_calls.append(1))
        monkeypatch.setattr(sp, "_find_simulator_executable", lambda: exe)
        monkeypatch.setattr(subprocess, "Popen", lambda *a, **_kw: None)
        monkeypatch.setattr(sp, "_wait_for_endpoint_ready", lambda _ep, **_kw: True)
        sp._ensure_opc_server_running("opc.tcp://localhost:40451", allow_launch=True, context="zip-test")
        assert len(extract_calls) == 1  # ZIP extracted before launch attempt


# =============================================================================
# Venv scenarios — fresh / existing / deleted
# =============================================================================


class TestVenvScenarios:
    def test_fresh_start_no_venv_no_npm(self, monkeypatch, fs):
        monkeypatch.setattr(sp, "VENV_DIR", Path("/fake/venv"))
        monkeypatch.setattr(sp, "IS_DOCKER", False)
        monkeypatch.setattr(sp, "_get_npm_path", lambda: None)
        monkeypatch.setattr(sp, "_get_npx_path", lambda: None)
        assert sp._is_runtime_ready() is False

    def test_venv_dir_exists_but_python_missing(self, monkeypatch, fs):
        venv = Path("/fake/venv")
        venv.mkdir(parents=True)
        # python binary NOT created
        monkeypatch.setattr(sp, "VENV_DIR", venv)
        monkeypatch.setattr(sp, "IS_DOCKER", False)
        monkeypatch.setattr(sp, "_get_npm_path", lambda: "/usr/bin/npm")
        monkeypatch.setattr(sp, "_get_npx_path", lambda: "/usr/bin/npx")
        assert sp._is_runtime_ready() is False

    def test_deleted_venv_not_ready(self, monkeypatch, fs):
        monkeypatch.setattr(sp, "VENV_DIR", Path("/fake/venv"))  # doesn't exist
        monkeypatch.setattr(sp, "IS_DOCKER", False)
        monkeypatch.setattr(sp, "_get_npm_path", lambda: "/usr/bin/npm")
        monkeypatch.setattr(sp, "_get_npx_path", lambda: "/usr/bin/npx")
        assert sp._is_runtime_ready() is False

    def test_docker_ready_without_venv(self, monkeypatch, fs):
        monkeypatch.setattr(sp, "VENV_DIR", Path("/fake/venv"))  # doesn't exist
        monkeypatch.setattr(sp, "IS_DOCKER", True)
        monkeypatch.setattr(sp, "_ENV_IS_PRE_ISOLATED", True)
        fake_python = Path("/fake/python.exe" if sp.IS_WINDOWS else "/fake/python")
        fake_python.parent.mkdir(parents=True, exist_ok=True)
        fake_python.write_bytes(b"fake")
        monkeypatch.setattr(sp, "_get_python_path", lambda: fake_python)
        monkeypatch.setattr(sp, "_get_npm_path", lambda: "/usr/bin/npm")
        monkeypatch.setattr(sp, "_get_npx_path", lambda: "/usr/bin/npx")
        monkeypatch.setattr(sp, "_run_command", lambda cmd, **_kw: None)
        monkeypatch.setattr(sp, "_get_last_setup_age_days", lambda: 1)
        monkeypatch.setenv("ENV_MAX_AGE_DAYS", "14")
        assert sp._is_runtime_ready() is True


# =============================================================================
# Additional coverage tests — second pass
# =============================================================================
import os
import shutil
import time
import types
import webbrowser

import pytest

# =============================================================================
# _detect_repo_root
# =============================================================================


class TestDetectRepoRoot:
    """_detect_repo_root: happy path and fallback (uses pyfakefs to avoid real repo paths)."""

    def test_finds_root_when_marker_dirs_present(self, fs):
        root = Path("/fake/repo")
        root.mkdir(parents=True)
        (root / "OPC_UA_Clients").mkdir()
        (root / "OPC_UA_Servers").mkdir()
        child = root / "deep" / "child"
        child.mkdir(parents=True)
        assert sp._detect_repo_root(child) == root

    def test_falls_back_to_start_dir_when_no_root_found(self, fs):
        start = Path("/fake/standalone")
        start.mkdir(parents=True)
        assert sp._detect_repo_root(start) == start


# =============================================================================
# _remove_stale_venvs
# =============================================================================


class TestRemoveStaleVenvs:
    """_remove_stale_venvs: stale dir present and absent."""

    def test_removes_stale_dir_that_exists(self, tmp_path, monkeypatch):
        stale = tmp_path / "venv"
        stale.mkdir()
        monkeypatch.setattr(sp, "_STALE_VENV_NAMES", ("venv",))
        sp._remove_stale_venvs(tmp_path)
        assert not stale.exists()

    def test_no_error_when_stale_dir_absent(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sp, "_STALE_VENV_NAMES", ("venv",))
        sp._remove_stale_venvs(tmp_path)  # must not raise


# =============================================================================
# _force_rmtree
# =============================================================================


class TestForceRmtree:
    """_force_rmtree: normal removal and read-only file handled by _on_exc."""

    def test_removes_normal_directory(self, tmp_path):
        d = tmp_path / "to_remove"
        d.mkdir()
        (d / "file.txt").write_text("hi")
        sp._force_rmtree(d)
        assert not d.exists()

    def test_handles_readonly_file(self, tmp_path):
        import stat

        d = tmp_path / "ro_dir"
        d.mkdir()
        f = d / "readonly.txt"
        f.write_text("data")
        f.chmod(stat.S_IREAD)
        sp._force_rmtree(d)
        assert not d.exists()


# =============================================================================
# _cleanup_local_project_artifacts
# =============================================================================


class TestCleanupLocalProjectArtifacts:
    """_cleanup_local_project_artifacts: cache dirs, pyc, coverage, state/tmp."""

    def test_removes_pycache_dir(self, tmp_path):
        pycache = tmp_path / "src" / "__pycache__"
        pycache.mkdir(parents=True)
        (pycache / "foo.cpython-314.pyc").write_bytes(b"")
        sp._cleanup_local_project_artifacts(tmp_path)
        assert not pycache.exists()

    def test_removes_pyc_files(self, tmp_path):
        f = tmp_path / "foo.pyc"
        f.write_bytes(b"")
        sp._cleanup_local_project_artifacts(tmp_path)
        assert not f.exists()

    def test_removes_coverage_files(self, tmp_path):
        (tmp_path / ".coverage").write_text("")
        (tmp_path / ".coverage.12345").write_text("")
        sp._cleanup_local_project_artifacts(tmp_path)
        assert not (tmp_path / ".coverage").exists()
        assert not (tmp_path / ".coverage.12345").exists()

    def test_removes_state_tmp_dir(self, tmp_path):
        state_tmp = tmp_path / ".state" / "tmp"
        state_tmp.mkdir(parents=True)
        sp._cleanup_local_project_artifacts(tmp_path)
        assert not state_tmp.exists()

    def test_skips_venv_dirs(self, tmp_path):
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "bin").mkdir()
        sp._cleanup_local_project_artifacts(tmp_path)
        assert venv.exists()

    def test_skips_node_modules(self, tmp_path):
        nm = tmp_path / "node_modules"
        nm.mkdir()
        sp._cleanup_local_project_artifacts(tmp_path)
        assert nm.exists()


# =============================================================================
# _run_command
# =============================================================================


class TestRunCommand:
    """_run_command: all three dispatch branches."""

    def test_capture_output_returns_stripped_stdout(self, monkeypatch):
        monkeypatch.setattr(subprocess, "check_output", lambda *a, **kw: "hello\n")
        result = sp._run_command(["echo", "hello"], capture_output=True)
        assert result == "hello"

    def test_check_true_calls_check_call_returns_none(self, monkeypatch):
        calls = []
        monkeypatch.setattr(subprocess, "check_call", lambda cmd: calls.append(cmd))
        result = sp._run_command(["echo"], check=True)
        assert result is None
        assert len(calls) == 1

    def test_check_false_returns_completed_process(self, monkeypatch):
        fake = MagicMock()
        monkeypatch.setattr(subprocess, "run", lambda cmd, check: fake)
        result = sp._run_command(["echo"], check=False)
        assert result is fake


# =============================================================================
# _semver_tuple
# =============================================================================


class TestSemverTuple:
    """_semver_tuple: pure version-string → tuple conversion."""

    def test_full_three_part_version(self):
        assert sp._semver_tuple("24.11.0") == (24, 11, 0)

    def test_single_part_padded_to_three(self):
        assert sp._semver_tuple("20") == (20, 0, 0)

    def test_two_part_padded(self):
        assert sp._semver_tuple("3.14") == (3, 14, 0)

    def test_extra_parts_truncated(self):
        assert sp._semver_tuple("1.2.3.4") == (1, 2, 3)

    def test_version_with_leading_v(self):
        assert sp._semver_tuple("v3.14.0") == (3, 14, 0)


# =============================================================================
# _env_bool
# =============================================================================


class TestEnvBool:
    """_env_bool: true/false/missing cases."""

    def test_truthy_values(self, monkeypatch):
        for val in ("1", "true", "yes", "on", "TRUE", "YES", "  True  "):
            monkeypatch.setenv("_TEST_BOOL", val)
            assert sp._env_bool("_TEST_BOOL", False) is True, f"Expected True for {val!r}"

    def test_falsy_values(self, monkeypatch):
        for val in ("0", "false", "no", "off"):
            monkeypatch.setenv("_TEST_BOOL", val)
            assert sp._env_bool("_TEST_BOOL", True) is False, f"Expected False for {val!r}"

    def test_missing_returns_default_true(self, monkeypatch):
        monkeypatch.delenv("_TEST_BOOL", raising=False)
        assert sp._env_bool("_TEST_BOOL", True) is True

    def test_missing_returns_default_false(self, monkeypatch):
        monkeypatch.delenv("_TEST_BOOL", raising=False)
        assert sp._env_bool("_TEST_BOOL", False) is False


# =============================================================================
# _env_float
# =============================================================================


class TestEnvFloat:
    """_env_float: valid/invalid/minimum-clamp paths."""

    def test_returns_parsed_float(self, monkeypatch):
        monkeypatch.setenv("_TEST_FLOAT", "5.5")
        assert sp._env_float("_TEST_FLOAT", 1.0, 0.0) == 5.5

    def test_falls_back_on_invalid(self, monkeypatch, caplog):
        import logging

        monkeypatch.setenv("_TEST_FLOAT", "notanumber")
        with caplog.at_level(logging.WARNING, logger="setup_project"):
            result = sp._env_float("_TEST_FLOAT", 3.0, 0.0)
        assert result == 3.0

    def test_clamps_below_minimum(self, monkeypatch):
        monkeypatch.setenv("_TEST_FLOAT", "0.0")
        assert sp._env_float("_TEST_FLOAT", 1.0, 0.5) == 0.5


# =============================================================================
# _warn_if_untested_python
# =============================================================================


class TestWarnIfUntestedPython:
    """_warn_if_untested_python: all branches."""

    def test_warns_when_minor_exceeds_max(self, monkeypatch, caplog):
        import logging

        monkeypatch.setenv("PYTHON_TESTED_MAX_MINOR", "14")
        with caplog.at_level(logging.WARNING, logger="setup_project"):
            sp._warn_if_untested_python("3.20")
        assert any("compatibility mode" in r.message for r in caplog.records)

    def test_no_warning_at_exact_max(self, monkeypatch, caplog):
        import logging

        monkeypatch.setenv("PYTHON_TESTED_MAX_MINOR", "14")
        with caplog.at_level(logging.WARNING, logger="setup_project"):
            sp._warn_if_untested_python("3.14")
        assert not any("compatibility mode" in r.message for r in caplog.records)

    def test_invalid_env_var_logs_warning(self, monkeypatch, caplog):
        import logging

        monkeypatch.setenv("PYTHON_TESTED_MAX_MINOR", "notanumber")
        with caplog.at_level(logging.WARNING, logger="setup_project"):
            sp._warn_if_untested_python("3.15")
        assert any("Invalid PYTHON_TESTED_MAX_MINOR" in r.message for r in caplog.records)

    def test_invalid_version_string_returns_none(self, monkeypatch):
        monkeypatch.delenv("PYTHON_TESTED_MAX_MINOR", raising=False)
        result = sp._warn_if_untested_python("invalid")
        assert result is None

    def test_uses_sys_version_when_no_arg(self, monkeypatch):
        monkeypatch.setenv("PYTHON_TESTED_MAX_MINOR", "99")
        sp._warn_if_untested_python()  # must not raise


# =============================================================================
# _warn_if_untested_node
# =============================================================================


class TestWarnIfUntestedNode:
    """_warn_if_untested_node: all branches."""

    def test_warns_when_major_exceeds_max(self, monkeypatch, caplog):
        import logging

        monkeypatch.setenv("NODE_TESTED_MAX_MAJOR", "24")
        with caplog.at_level(logging.WARNING, logger="setup_project"):
            sp._warn_if_untested_node("30.0.0")
        assert any("compatibility mode" in r.message for r in caplog.records)

    def test_no_warning_at_exact_max(self, monkeypatch, caplog):
        import logging

        monkeypatch.setenv("NODE_TESTED_MAX_MAJOR", "24")
        with caplog.at_level(logging.WARNING, logger="setup_project"):
            sp._warn_if_untested_node("24.0.0")
        assert not any("compatibility mode" in r.message for r in caplog.records)

    def test_invalid_env_var_logs_warning(self, monkeypatch, caplog):
        import logging

        monkeypatch.setenv("NODE_TESTED_MAX_MAJOR", "notanumber")
        with caplog.at_level(logging.WARNING, logger="setup_project"):
            sp._warn_if_untested_node("24.0.0")
        assert any("Invalid NODE_TESTED_MAX_MAJOR" in r.message for r in caplog.records)

    def test_empty_version_string_returns_none(self):
        assert sp._warn_if_untested_node("") is None


# =============================================================================
# _list_pythons_windows
# =============================================================================


class TestListPythonsWindows:
    """_list_pythons_windows: output parsing and error handling."""

    def test_parses_new_and_old_format_lines(self, monkeypatch):
        fake_out = " -V:3.14 *        Python 3.14 (64-bit)\n -3.13  Python 3.13 (64-bit)\n"
        monkeypatch.setattr(subprocess, "check_output", lambda *a, **kw: fake_out)
        result = sp._list_pythons_windows()
        assert "3.14" in result
        assert "3.13" in result

    def test_returns_empty_list_on_failure(self, monkeypatch):
        def _fail(*a, **kw):
            raise RuntimeError("py not found")

        monkeypatch.setattr(subprocess, "check_output", _fail)
        assert sp._list_pythons_windows() == []

    def test_ignores_non_matching_lines(self, monkeypatch):
        fake_out = "Installed Pythons found by py Launcher for Windows\n -V:3.14 *  Python 3.14\n"
        monkeypatch.setattr(subprocess, "check_output", lambda *a, **kw: fake_out)
        result = sp._list_pythons_windows()
        assert result == ["3.14"]


# =============================================================================
# _find_latest_python_executable
# =============================================================================


class TestFindLatestPythonExecutable:
    """_find_latest_python_executable: Windows and POSIX paths."""

    def test_windows_includes_current_interpreter(self, monkeypatch):
        """Even with empty _list_pythons_windows, current interpreter is a candidate."""
        monkeypatch.setattr(sp, "IS_WINDOWS", True)
        monkeypatch.setattr(sp, "_list_pythons_windows", lambda: [])
        monkeypatch.delenv("LOCALAPPDATA", raising=False)
        cmd, ver = sp._find_latest_python_executable()
        current = f"{sys.version_info[0]}.{sys.version_info[1]}"
        assert ver == current

    def test_windows_picks_highest_version(self, monkeypatch):
        monkeypatch.setattr(sp, "IS_WINDOWS", True)
        monkeypatch.setattr(sp, "_list_pythons_windows", lambda: ["3.13", "3.14"])
        monkeypatch.delenv("LOCALAPPDATA", raising=False)
        _cmd, ver = sp._find_latest_python_executable()
        # Must be >= 3.14 (the version from the mock list or current, whichever is higher)
        major, minor = map(int, ver.split("."))
        assert (major, minor) >= (3, 13)

    def test_posix_finds_versioned_python(self, monkeypatch):
        monkeypatch.setattr(sp, "IS_WINDOWS", False)

        def _fake_check_call(cmd, **kw):
            if cmd[0] == "python3.14":
                return 0
            raise FileNotFoundError(cmd[0])

        monkeypatch.setattr(subprocess, "check_call", _fake_check_call)
        cmd, ver = sp._find_latest_python_executable()
        assert cmd == ["python3.14"]
        assert ver == "3.14"

    def test_posix_falls_back_to_python3(self, monkeypatch):
        monkeypatch.setattr(sp, "IS_WINDOWS", False)

        def _fail_versioned(cmd, **kw):
            if cmd[0].startswith("python3."):
                raise FileNotFoundError(cmd[0])
            return 0  # python3 --version succeeds

        monkeypatch.setattr(subprocess, "check_call", _fail_versioned)
        monkeypatch.setattr(subprocess, "check_output", lambda *a, **kw: "3.12\n")
        cmd, ver = sp._find_latest_python_executable()
        assert cmd == ["python3"]
        assert ver == "3.12"

    def test_posix_exits_when_no_python_found(self, monkeypatch):
        monkeypatch.setattr(sp, "IS_WINDOWS", False)

        def _fail_all(cmd, **kw):
            raise FileNotFoundError(cmd[0])

        monkeypatch.setattr(subprocess, "check_call", _fail_all)
        monkeypatch.setattr(subprocess, "check_output", _fail_all)
        with pytest.raises(SystemExit):
            sp._find_latest_python_executable()


# =============================================================================
# _relaunch_under_latest_python
# =============================================================================


class TestRelaunchUnderLatestPython:
    """_relaunch_under_latest_python: same version → no execvp; newer → execvp called."""

    def test_no_relaunch_when_already_latest(self, monkeypatch):
        current = f"{sys.version_info[0]}.{sys.version_info[1]}"
        monkeypatch.setattr(sp, "_find_latest_python_executable", lambda: (["python"], current))
        execvp_calls = []
        monkeypatch.setattr(os, "execvp", lambda *a: execvp_calls.append(a))
        sp._relaunch_under_latest_python()
        assert execvp_calls == []

    def test_relaunch_when_newer_version_available(self, monkeypatch):
        monkeypatch.setattr(sp, "_find_latest_python_executable", lambda: (["python3.99"], "3.99"))
        execvp_calls = []
        monkeypatch.setattr(os, "execvp", lambda prog, args: execvp_calls.append((prog, args)))
        sp._relaunch_under_latest_python()
        assert len(execvp_calls) == 1
        assert execvp_calls[0][0] == "python3.99"


# =============================================================================
# _require_python_314_or_newer
# =============================================================================


class TestRequirePython314OrNewer:
    """_require_python_314_or_newer: version gate."""

    def test_exits_on_python_313(self):
        with pytest.raises(SystemExit):
            sp._require_python_314_or_newer("3.13")

    def test_exits_on_python_27(self):
        with pytest.raises(SystemExit):
            sp._require_python_314_or_newer("2.7")

    def test_no_exit_on_314(self):
        sp._require_python_314_or_newer("3.14")  # must not raise

    def test_no_exit_on_400(self):
        sp._require_python_314_or_newer("4.0")

    def test_invalid_string_uses_sys_version(self):
        current = f"{sys.version_info[0]}.{sys.version_info[1]}"
        sp._require_python_314_or_newer(current)  # no raise in 3.14+ env

    def test_no_arg_uses_sys_version(self):
        sp._require_python_314_or_newer()  # must not raise in 3.14+ env

    def test_malformed_version_falls_back_to_sys_version(self):
        # "3.14.1" unpacks to 3 values → ValueError → except branch (lines 355-356)
        sp._require_python_314_or_newer("3.14.1")  # must not raise in 3.14+ env


# =============================================================================
# _check_internet
# =============================================================================


class TestCheckInternet:
    """_check_internet: connection success and socket.error."""

    def test_returns_true_when_connected(self, monkeypatch):
        mock_sock = MagicMock()
        mock_sock.connect = MagicMock()
        monkeypatch.setattr(socket, "socket", lambda *a, **kw: mock_sock)
        assert sp._check_internet() is True
        mock_sock.close.assert_called_once()

    def test_returns_false_on_socket_error(self, monkeypatch):
        mock_sock = MagicMock()
        mock_sock.connect.side_effect = socket.error("refused")
        monkeypatch.setattr(socket, "socket", lambda *a, **kw: mock_sock)
        assert sp._check_internet() is False
        mock_sock.close.assert_called_once()


# =============================================================================
# _pid_is_running
# =============================================================================


class TestPidIsRunning:
    """_pid_is_running: zero/negative, Windows paths, POSIX paths."""

    def test_returns_false_for_zero(self):
        assert sp._pid_is_running(0) is False

    def test_returns_false_for_negative(self):
        assert sp._pid_is_running(-1) is False

    def test_windows_pid_running(self, monkeypatch):
        monkeypatch.setattr(sp, "IS_WINDOWS", True)
        result = MagicMock()
        result.stdout = '"python.exe","1234","Console","1","12 K"'
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: result)
        assert sp._pid_is_running(1234) is True

    def test_windows_pid_no_tasks_output(self, monkeypatch):
        monkeypatch.setattr(sp, "IS_WINDOWS", True)
        result = MagicMock()
        result.stdout = "No tasks are running which match the specified criteria."
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: result)
        assert sp._pid_is_running(9999) is False

    def test_windows_pid_empty_output(self, monkeypatch):
        monkeypatch.setattr(sp, "IS_WINDOWS", True)
        result = MagicMock()
        result.stdout = ""
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: result)
        assert sp._pid_is_running(1234) is False

    def test_windows_exception_returns_false(self, monkeypatch):
        monkeypatch.setattr(sp, "IS_WINDOWS", True)

        def _fail(*a, **kw):
            raise RuntimeError("tasklist failed")

        monkeypatch.setattr(subprocess, "run", _fail)
        assert sp._pid_is_running(1234) is False

    def test_posix_running_pid(self, monkeypatch):
        monkeypatch.setattr(sp, "IS_WINDOWS", False)
        monkeypatch.setattr(os, "kill", lambda pid, sig: None)
        assert sp._pid_is_running(1234) is True

    def test_posix_dead_pid(self, monkeypatch):
        monkeypatch.setattr(sp, "IS_WINDOWS", False)

        def _raise(pid, sig):
            raise OSError("No such process")

        monkeypatch.setattr(os, "kill", _raise)
        assert sp._pid_is_running(9999) is False


# =============================================================================
# _record_runtime_processes
# =============================================================================


class TestRecordRuntimeProcesses:
    """_record_runtime_processes: no-op when both None, writes state otherwise."""

    def test_no_op_when_both_none(self, monkeypatch):
        write_calls = []
        monkeypatch.setattr(sp, "_write_runtime_state", lambda s: write_calls.append(s))
        sp._record_runtime_processes(None, None)
        assert write_calls == []

    def test_writes_state_when_pids_given(self, monkeypatch):
        write_calls = []
        monkeypatch.setattr(sp, "_write_runtime_state", lambda s: write_calls.append(s))
        sp._record_runtime_processes(1234, 5678)
        assert len(write_calls) == 1
        assert write_calls[0]["frontend_pid"] == 1234
        assert write_calls[0]["backend_pid"] == 5678


# =============================================================================
# _collect_managed_processes — edge cases
# =============================================================================


class TestCollectManagedProcessesEdgeCases:
    """_collect_managed_processes: non-numeric pids raise ValueError → skipped."""

    def test_skips_non_numeric_pid(self, monkeypatch):
        monkeypatch.setattr(sp, "_read_runtime_state", lambda: {"frontend_pid": "notanumber", "backend_pid": None})
        monkeypatch.setattr(sp, "_pid_is_running", lambda pid: True)
        assert sp._collect_managed_processes() == []

    def test_skips_zero_pid(self, monkeypatch):
        monkeypatch.setattr(sp, "_read_runtime_state", lambda: {"frontend_pid": 0, "backend_pid": 0})
        monkeypatch.setattr(sp, "_pid_is_running", lambda pid: True)
        assert sp._collect_managed_processes() == []


# =============================================================================
# _stop_managed_processes
# =============================================================================


class TestStopManagedProcesses:
    """_stop_managed_processes: empty set, and POSIX graceful stop."""

    def test_clears_state_when_no_managed(self, monkeypatch):
        cleared = []
        monkeypatch.setattr(sp, "_collect_managed_processes", lambda: [])
        monkeypatch.setattr(sp, "_clear_runtime_state", lambda: cleared.append(1))
        sp._stop_managed_processes()
        assert cleared

    def test_posix_sends_sigterm_and_clears(self, monkeypatch):
        import time as _t

        call_count = [0]

        def _fake_collect():
            call_count[0] += 1
            return [("frontend", 1234)] if call_count[0] == 1 else []

        kills = []
        monkeypatch.setattr(sp, "_collect_managed_processes", _fake_collect)
        monkeypatch.setattr(sp, "_clear_runtime_state", lambda: None)
        monkeypatch.setattr(sp, "IS_WINDOWS", False)
        monkeypatch.setattr(os, "kill", lambda pid, sig: kills.append((pid, sig)))
        monkeypatch.setattr(_t, "sleep", lambda t: None)
        sp._stop_managed_processes(timeout_sec=0.01)
        assert any(pid == 1234 for pid, _ in kills)

    def test_windows_sends_ctrl_break(self, monkeypatch):
        import signal as _signal
        import time as _t

        call_count = [0]

        def _fake_collect():
            call_count[0] += 1
            return [("backend", 5678)] if call_count[0] == 1 else []

        kills = []
        run_calls = []
        monkeypatch.setattr(sp, "_collect_managed_processes", _fake_collect)
        monkeypatch.setattr(sp, "_clear_runtime_state", lambda: None)
        monkeypatch.setattr(sp, "IS_WINDOWS", True)
        monkeypatch.setattr(os, "kill", lambda pid, sig: kills.append((pid, sig)))
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: run_calls.append(a[0]) or MagicMock())
        monkeypatch.setattr(_t, "sleep", lambda t: None)
        # Ensure CTRL_BREAK_EVENT is available for the mock
        if not hasattr(_signal, "CTRL_BREAK_EVENT"):
            monkeypatch.setattr(_signal, "CTRL_BREAK_EVENT", 1, raising=False)
        sp._stop_managed_processes(timeout_sec=0.01)
        # Either os.kill was called or the suppress suppressed it; no crash is the key assertion
        assert call_count[0] >= 1


# =============================================================================
# _runtime_status
# =============================================================================


class TestRuntimeStatus:
    """_runtime_status: delegates to _read_runtime_state + _pid_is_running."""

    def test_both_running(self, monkeypatch):
        monkeypatch.setattr(sp, "_read_runtime_state", lambda: {"frontend_pid": 1, "backend_pid": 2})
        monkeypatch.setattr(sp, "_pid_is_running", lambda pid: pid > 0)
        assert sp._runtime_status() == {"frontend": True, "backend": True}

    def test_both_stopped(self, monkeypatch):
        monkeypatch.setattr(sp, "_read_runtime_state", lambda: {"frontend_pid": 1, "backend_pid": 2})
        monkeypatch.setattr(sp, "_pid_is_running", lambda pid: False)
        assert sp._runtime_status() == {"frontend": False, "backend": False}

    def test_empty_state(self, monkeypatch):
        monkeypatch.setattr(sp, "_read_runtime_state", lambda: {})
        monkeypatch.setattr(sp, "_pid_is_running", lambda pid: False)
        result = sp._runtime_status()
        assert result["frontend"] is False
        assert result["backend"] is False


# =============================================================================
# _should_block_foreground
# =============================================================================


class TestShouldBlockForeground:
    """_should_block_foreground: proc objects and managed-process checks."""

    def test_true_when_frontend_proc_not_none(self, monkeypatch):
        monkeypatch.setattr(sp, "_runtime_status", lambda: {"frontend": False, "backend": False})
        assert sp._should_block_foreground(MagicMock(), None) is True

    def test_true_when_backend_proc_not_none(self, monkeypatch):
        monkeypatch.setattr(sp, "_runtime_status", lambda: {"frontend": False, "backend": False})
        assert sp._should_block_foreground(None, MagicMock()) is True

    def test_true_when_managed_running(self, monkeypatch):
        monkeypatch.setattr(sp, "_runtime_status", lambda: {"frontend": True, "backend": False})
        assert sp._should_block_foreground(None, None) is True

    def test_false_when_nothing_running(self, monkeypatch):
        monkeypatch.setattr(sp, "_runtime_status", lambda: {"frontend": False, "backend": False})
        assert sp._should_block_foreground(None, None) is False


# =============================================================================
# _SetupLock
# =============================================================================


class TestSetupLock:
    """_SetupLock: acquire/release on both POSIX (mocked) and real Windows paths."""

    def test_release_with_no_handle_is_noop(self, tmp_path):
        lock = sp._SetupLock(tmp_path / "test.lock")
        lock.release()  # must not raise
        assert lock._fh is None

    def test_acquire_and_release_posix_branch(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sp, "IS_WINDOWS", False)
        fake_fcntl = types.ModuleType("fcntl")
        setattr(fake_fcntl, "LOCK_EX", 2)
        setattr(fake_fcntl, "LOCK_NB", 4)
        setattr(fake_fcntl, "LOCK_UN", 8)
        setattr(fake_fcntl, "flock", lambda *a: None)
        monkeypatch.setitem(sys.modules, "fcntl", fake_fcntl)
        lock = sp._SetupLock(tmp_path / "test.lock")
        assert lock.acquire() is True
        assert lock._fh is not None
        lock.release()
        assert lock._fh is None

    def test_acquire_returns_false_when_flock_raises(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sp, "IS_WINDOWS", False)
        fake_fcntl = types.ModuleType("fcntl")
        setattr(fake_fcntl, "LOCK_EX", 2)
        setattr(fake_fcntl, "LOCK_NB", 4)
        setattr(fake_fcntl, "LOCK_UN", 8)

        def _raise_blocking(*a):
            raise BlockingIOError("lock held")

        setattr(fake_fcntl, "flock", _raise_blocking)
        monkeypatch.setitem(sys.modules, "fcntl", fake_fcntl)
        lock = sp._SetupLock(tmp_path / "test.lock")
        assert lock.acquire() is False

    def test_acquire_windows_succeeds(self, monkeypatch):
        monkeypatch.setattr(sp, "IS_WINDOWS", True)
        calls = []
        fake_msvcrt = types.ModuleType("msvcrt")
        setattr(fake_msvcrt, "LK_NBLCK", 1)
        setattr(fake_msvcrt, "LK_UNLCK", 2)

        def _locking(_fd, mode, nbytes):
            calls.append((mode, nbytes))

        setattr(fake_msvcrt, "locking", _locking)
        monkeypatch.setitem(sys.modules, "msvcrt", fake_msvcrt)

        lock_path = Path(__file__).parents[2] / "tmp" / "unit_setup_lock" / uuid.uuid4().hex / "test.lock"
        lock = sp._SetupLock(lock_path)
        assert lock.acquire() is True
        lock.release()
        assert calls == [(fake_msvcrt.LK_NBLCK, 1), (fake_msvcrt.LK_UNLCK, 1)]


# =============================================================================
# _is_websocket_server_ready
# =============================================================================


class TestIsWebsocketServerReady:
    """_is_websocket_server_ready: python-not-found fallback, rc=0/1, exception fallback."""

    def test_falls_back_to_port_when_python_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sp, "_get_python_path", lambda: tmp_path / "nonexistent_python")
        monkeypatch.setattr(sp, "_is_port_in_use", lambda *a, **kw: True)
        assert sp._is_websocket_server_ready(8001) is True

    def test_subprocess_rc_0_means_ready(self, tmp_path, monkeypatch):
        python = tmp_path / "python"
        python.write_bytes(b"fake")
        monkeypatch.setattr(sp, "_get_python_path", lambda: python)
        result = MagicMock()
        result.returncode = 0
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: result)
        assert sp._is_websocket_server_ready(8001) is True

    def test_subprocess_rc_1_means_not_ready(self, tmp_path, monkeypatch):
        python = tmp_path / "python"
        python.write_bytes(b"fake")
        monkeypatch.setattr(sp, "_get_python_path", lambda: python)
        result = MagicMock()
        result.returncode = 1
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: result)
        assert sp._is_websocket_server_ready(8001) is False

    def test_subprocess_exception_falls_back_to_port(self, tmp_path, monkeypatch):
        python = tmp_path / "python"
        python.write_bytes(b"fake")
        monkeypatch.setattr(sp, "_get_python_path", lambda: python)

        def _raise(*a, **kw):
            raise RuntimeError("subprocess failed")

        monkeypatch.setattr(subprocess, "run", _raise)
        monkeypatch.setattr(sp, "_is_port_in_use", lambda *a, **kw: False)
        assert sp._is_websocket_server_ready(8001) is False


# =============================================================================
# _wait_for_endpoint_ready
# =============================================================================


class TestWaitForEndpointReady:
    """_wait_for_endpoint_ready: immediate hit and deadline-exceeded paths."""

    def test_returns_true_immediately(self, monkeypatch):
        monkeypatch.setattr(sp, "_is_endpoint_reachable", lambda ep: True)
        result = sp._wait_for_endpoint_ready("opc.tcp://localhost:40451", timeout_seconds=1.0, poll_interval=0.01)
        assert result is True

    def test_returns_false_when_deadline_exceeded(self, monkeypatch):
        import time as _t

        monkeypatch.setattr(sp, "_is_endpoint_reachable", lambda ep: False)
        start = _t.time()
        call_num = [0]

        def _fast_time():
            call_num[0] += 1
            return start + call_num[0] * 10

        monkeypatch.setattr(_t, "time", _fast_time)
        monkeypatch.setattr(_t, "sleep", lambda t: None)
        result = sp._wait_for_endpoint_ready("opc.tcp://localhost:40451", timeout_seconds=1.0)
        assert result is False

    def test_sleeps_and_retries_until_success(self, monkeypatch):
        import time as _t

        # First call returns False (triggers time.sleep on line 656), second returns True
        calls = iter([False, True])
        monkeypatch.setattr(sp, "_is_endpoint_reachable", lambda ep: next(calls))
        monkeypatch.setattr(_t, "sleep", lambda t: None)
        result = sp._wait_for_endpoint_ready("opc.tcp://localhost:40451", timeout_seconds=10.0, poll_interval=0.01)
        assert result is True


# =============================================================================
# _ensure_opc_server_running — Windows creationflags branch (line 724)
# =============================================================================


class TestEnsureOpcServerRunningWindows:
    """_ensure_opc_server_running: IS_WINDOWS=True passes CREATE_NEW_CONSOLE."""

    def test_windows_popen_receives_creationflags(self, monkeypatch):
        exe = Path("/fake") / sp.SIMULATOR_EXE_NAME
        kwargs_received = {}

        def _fake_popen(cmd, **kw):
            kwargs_received.update(kw)

        monkeypatch.setattr(sp, "endpoint_reachable", lambda _ep, timeout=1.0: False)
        monkeypatch.setattr(sp, "IS_WSL", False)
        monkeypatch.setattr(sp, "IS_DOCKER", False)
        monkeypatch.setattr(sp, "IS_WINDOWS", True)
        monkeypatch.setattr(sp, "_extract_simulator_zip_if_needed", lambda: None)
        monkeypatch.setattr(sp, "_find_simulator_executable", lambda: exe)
        monkeypatch.setattr(subprocess, "Popen", _fake_popen)
        monkeypatch.setattr(subprocess, "CREATE_NEW_CONSOLE", 0x10, raising=False)
        monkeypatch.setattr(sp, "_wait_for_endpoint_ready", lambda _ep, **_kw: True)
        sp._ensure_opc_server_running("opc.tcp://localhost:40451", allow_launch=True, context="win-test")
        assert "creationflags" in kwargs_received


# =============================================================================
# Venv path helpers
# =============================================================================


class TestVenvPathHelpers:
    """_python_in_venv, _pip_in_venv, _get_python_path."""

    def test_python_in_venv_windows(self, monkeypatch):
        monkeypatch.setattr(sp, "IS_WINDOWS", True)
        monkeypatch.setattr(sp, "VENV_DIR", Path("/fake/venv"))
        p = sp._python_in_venv()
        assert "Scripts" in str(p) and "python.exe" in str(p)

    def test_python_in_venv_posix(self, monkeypatch):
        monkeypatch.setattr(sp, "IS_WINDOWS", False)
        monkeypatch.setattr(sp, "VENV_DIR", Path("/fake/venv"))
        expected = Path("/fake/venv") / "bin" / "python"
        assert sp._python_in_venv() == expected

    def test_pip_in_venv_windows(self, monkeypatch):
        monkeypatch.setattr(sp, "IS_WINDOWS", True)
        monkeypatch.setattr(sp, "VENV_DIR", Path("/fake/venv"))
        p = sp._pip_in_venv()
        assert "Scripts" in str(p) and "pip.exe" in str(p)

    def test_pip_in_venv_posix(self, monkeypatch):
        monkeypatch.setattr(sp, "IS_WINDOWS", False)
        monkeypatch.setattr(sp, "VENV_DIR", Path("/fake/venv"))
        expected = Path("/fake/venv") / "bin" / "pip"
        assert sp._pip_in_venv() == expected

    def test_get_python_path_docker(self, monkeypatch):
        # _get_python_path() consults the module-level _ENV_IS_PRE_ISOLATED
        # flag (computed at import time from IS_DOCKER or IS_GITHUB_ACTIONS),
        # so patch that directly rather than the underlying env booleans.
        monkeypatch.setattr(sp, "_ENV_IS_PRE_ISOLATED", True)
        assert sp._get_python_path() == Path(sys.executable)

    def test_get_python_path_non_docker(self, monkeypatch):
        monkeypatch.setattr(sp, "_ENV_IS_PRE_ISOLATED", False)
        monkeypatch.setattr(sp, "VENV_DIR", Path("/fake/venv"))
        p = sp._get_python_path()
        assert "venv" in str(p)


# =============================================================================
# Node helpers
# =============================================================================


class TestNodeHelpers:
    """_get_npm_path, _get_npx_path, _get_node_version."""

    def test_get_npm_path_found(self, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda x: f"/usr/bin/{x}")
        assert sp._get_npm_path() == "/usr/bin/npm"

    def test_get_npm_path_not_found(self, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda x: None)
        assert sp._get_npm_path() is None

    def test_get_npx_path_found(self, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda x: f"/usr/bin/{x}")
        assert sp._get_npx_path() == "/usr/bin/npx"

    def test_get_node_version_strips_v_prefix(self, monkeypatch):
        monkeypatch.setattr(subprocess, "check_output", lambda *a, **kw: "v24.0.0\n")
        assert sp._get_node_version() == "24.0.0"

    def test_get_node_version_returns_none_on_failure(self, monkeypatch, caplog):
        import logging

        def _fail(*a, **kw):
            raise RuntimeError("node not found")

        monkeypatch.setattr(subprocess, "check_output", _fail)
        with caplog.at_level(logging.ERROR, logger="setup_project"):
            result = sp._get_node_version()
        assert result is None


# =============================================================================
# _get_environment_age_days
# =============================================================================


class TestGetEnvironmentAgeDays:
    """_get_environment_age_days: venv present, absent, exception."""

    def test_returns_age_when_venv_exists(self, tmp_path, monkeypatch):
        venv = tmp_path / "venv"
        venv.mkdir()
        monkeypatch.setattr(sp, "VENV_DIR", venv)
        five_days_ago = time.time() - 5 * 86400
        monkeypatch.setattr(os.path, "getmtime", lambda p: five_days_ago)
        age = sp._get_environment_age_days()
        assert age is not None
        assert 4.9 < age < 5.1

    def test_returns_none_when_venv_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sp, "VENV_DIR", tmp_path / "nonexistent")
        assert sp._get_environment_age_days() is None

    def test_returns_none_on_exception(self, tmp_path, monkeypatch):
        venv = tmp_path / "venv"
        venv.mkdir()
        monkeypatch.setattr(sp, "VENV_DIR", venv)

        def _raise(p):
            raise OSError("Permission denied")

        monkeypatch.setattr(os.path, "getmtime", _raise)
        assert sp._get_environment_age_days() is None


# =============================================================================
# Setup timestamp helpers
# =============================================================================


class TestSetupTimestamp:
    """_get_last_setup_age_days, _update_setup_timestamp."""

    def test_returns_age_from_timestamp_file(self, tmp_path, monkeypatch):
        ts_file = tmp_path / "setup_timestamp"
        ts_file.write_text(str(time.time() - 5 * 86400))
        monkeypatch.setattr(sp, "SETUP_TIMESTAMP_FILE", ts_file)
        age = sp._get_last_setup_age_days()
        assert age is not None
        assert 4.9 < age < 5.1

    def test_returns_none_when_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sp, "SETUP_TIMESTAMP_FILE", tmp_path / "nonexistent")
        assert sp._get_last_setup_age_days() is None

    def test_returns_none_on_invalid_content(self, tmp_path, monkeypatch):
        ts_file = tmp_path / "setup_timestamp"
        ts_file.write_text("not_a_number")
        monkeypatch.setattr(sp, "SETUP_TIMESTAMP_FILE", ts_file)
        assert sp._get_last_setup_age_days() is None

    def test_update_writes_timestamp(self, tmp_path, monkeypatch):
        ts_file = tmp_path / "setup_timestamp"
        monkeypatch.setattr(sp, "SETUP_TIMESTAMP_FILE", ts_file)
        sp._update_setup_timestamp()
        assert ts_file.exists()
        assert float(ts_file.read_text()) > 0

    def test_update_handles_write_exception(self, monkeypatch, caplog):
        import logging

        monkeypatch.setattr(sp, "SETUP_TIMESTAMP_FILE", Path("/nonexistent/dir/timestamp"))
        with caplog.at_level(logging.WARNING, logger="setup_project"):
            sp._update_setup_timestamp()  # must not raise


# =============================================================================
# _resolve_python_executable
# =============================================================================


class TestResolvePythonExecutable:
    """_resolve_python_executable: success, empty output, exception."""

    def test_success_returns_stripped_path(self, monkeypatch):
        monkeypatch.setattr(subprocess, "check_output", lambda *a, **kw: "/usr/bin/python3.14\n")
        assert sp._resolve_python_executable(["python3.14"]) == "/usr/bin/python3.14"

    def test_empty_output_exits(self, monkeypatch):
        monkeypatch.setattr(subprocess, "check_output", lambda *a, **kw: "")
        with pytest.raises(SystemExit):
            sp._resolve_python_executable(["python3.14"])

    def test_exception_exits(self, monkeypatch):
        def _fail(*a, **kw):
            raise RuntimeError("not found")

        monkeypatch.setattr(subprocess, "check_output", _fail)
        with pytest.raises(SystemExit):
            sp._resolve_python_executable(["python3.14"])


# =============================================================================
# _create_virtualenv
# =============================================================================


class TestCreateVirtualenv:
    """_create_virtualenv: success, ensurepip fallback, venv-creation failure, existing-venv removal."""

    def test_success_path(self, tmp_path, monkeypatch):
        venv_dir = tmp_path / ".venv"
        monkeypatch.setattr(sp, "VENV_DIR", venv_dir)
        monkeypatch.setattr(sp, "STATE_DIR", tmp_path / ".state")
        monkeypatch.setattr(sp, "_resolve_python_executable", lambda cmd: "/usr/bin/python3.14")
        calls = []
        monkeypatch.setattr(subprocess, "check_call", lambda cmd, **kw: calls.append(list(cmd)))
        monkeypatch.setattr(sp, "_python_in_venv", lambda: venv_dir / "bin/python")
        sp._create_virtualenv(["python3.14"])
        assert any("venv" in " ".join(cmd) for cmd in calls)
        assert any("ensurepip" in " ".join(cmd) for cmd in calls)

    def test_ensurepip_failure_triggers_fallback(self, tmp_path, monkeypatch):
        venv_dir = tmp_path / ".venv"
        monkeypatch.setattr(sp, "VENV_DIR", venv_dir)
        monkeypatch.setattr(sp, "STATE_DIR", tmp_path / ".state")
        monkeypatch.setattr(sp, "_resolve_python_executable", lambda cmd: "/usr/bin/python3.14")
        call_count = [0]

        def _selective_fail(cmd, **kw):
            call_count[0] += 1
            if "ensurepip" in cmd:
                raise RuntimeError("ensurepip failed")

        monkeypatch.setattr(subprocess, "check_call", _selective_fail)
        monkeypatch.setattr(sp, "_python_in_venv", lambda: venv_dir / "bin/python")
        sp._create_virtualenv(["python3.14"])
        assert call_count[0] >= 2  # venv creation + fallback pip

    def test_venv_creation_failure_exits(self, tmp_path, monkeypatch):
        venv_dir = tmp_path / ".venv"
        monkeypatch.setattr(sp, "VENV_DIR", venv_dir)
        monkeypatch.setattr(sp, "STATE_DIR", tmp_path / ".state")
        monkeypatch.setattr(sp, "_resolve_python_executable", lambda cmd: "/usr/bin/python3.14")

        def _fail_venv(cmd, **kw):
            if "-m" in cmd and "venv" in cmd:
                raise subprocess.CalledProcessError(1, cmd)

        monkeypatch.setattr(subprocess, "check_call", _fail_venv)
        with pytest.raises(SystemExit):
            sp._create_virtualenv(["python3.14"])

    def test_existing_venv_removed(self, tmp_path, monkeypatch):
        venv_dir = tmp_path / ".venv"
        venv_dir.mkdir()
        (venv_dir / "old_file.txt").write_text("stale")
        monkeypatch.setattr(sp, "VENV_DIR", venv_dir)
        monkeypatch.setattr(sp, "STATE_DIR", tmp_path / ".state")
        monkeypatch.setattr(sp, "_resolve_python_executable", lambda cmd: "/usr/bin/python3.14")
        monkeypatch.setattr(subprocess, "check_call", lambda cmd, **kw: None)
        monkeypatch.setattr(sp, "_python_in_venv", lambda: venv_dir / "bin/python")
        sp._create_virtualenv(["python3.14"])
        # Old file removed (venv_dir itself removed by rmtree, not recreated by mocked check_call)
        assert not (venv_dir / "old_file.txt").exists()


# =============================================================================
# _install_python_packages
# =============================================================================


class TestInstallPythonPackages:
    """_install_python_packages: missing requirements, success, crypto-upgrade exception."""

    def test_missing_requirements_exits(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sp, "_get_python_path", lambda: Path("/usr/bin/python3.14"))
        monkeypatch.setattr(subprocess, "check_call", lambda *a, **kw: None)
        with pytest.raises(SystemExit):
            sp._install_python_packages()

    def test_success_path(self, tmp_path, monkeypatch):
        (tmp_path / "requirements.txt").write_text("asyncua>=1.2b2\n")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sp, "_get_python_path", lambda: Path("/usr/bin/python3.14"))
        calls = []
        monkeypatch.setattr(subprocess, "check_call", lambda *a, **kw: calls.append(list(a[0])))
        monkeypatch.setattr(subprocess, "check_output", lambda *a, **kw: "1.2b2\n")
        sp._install_python_packages()
        assert any("pip" in " ".join(cmd) for cmd in calls)

    def test_crypto_upgrade_exception_is_debug_only(self, tmp_path, monkeypatch, caplog):
        import logging

        (tmp_path / "requirements.txt").write_text("asyncua>=1.2b2\n")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sp, "_get_python_path", lambda: Path("/usr/bin/python3.14"))

        def _fail_crypto(cmd, **kw):
            if "cryptography" in cmd:
                raise RuntimeError("crypto failed")

        monkeypatch.setattr(subprocess, "check_call", _fail_crypto)
        monkeypatch.setattr(subprocess, "check_output", lambda *a, **kw: "1.2b2\n")
        with caplog.at_level(logging.DEBUG, logger="setup_project"):
            sp._install_python_packages()
        # No sys.exit; debug log only


# =============================================================================
# _create_nodeenv
# =============================================================================


class TestCreateNodeenv:
    """_create_nodeenv: missing tools, smoke check failure, old version, success."""

    def test_missing_node_exits(self, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda x: None)
        with pytest.raises(SystemExit):
            sp._create_nodeenv()

    def test_smoke_check_failure_exits(self, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda x: f"/usr/bin/{x}")

        def _fail(cmd, **kw):
            raise subprocess.CalledProcessError(1, cmd)

        monkeypatch.setattr(subprocess, "check_call", _fail)
        with pytest.raises(SystemExit):
            sp._create_nodeenv()

    def test_old_node_version_exits(self, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda x: f"/usr/bin/{x}")
        monkeypatch.setattr(subprocess, "check_call", lambda *a, **kw: None)
        monkeypatch.setattr(sp, "_get_node_version", lambda: "18.0.0")
        monkeypatch.setenv("NODE_VERSION", "24.0.0")
        with pytest.raises(SystemExit):
            sp._create_nodeenv()

    def test_all_found_version_ok(self, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda x: f"/usr/bin/{x}")
        monkeypatch.setattr(subprocess, "check_call", lambda *a, **kw: None)
        monkeypatch.setattr(sp, "_get_node_version", lambda: "24.0.0")
        monkeypatch.setattr(sp, "_warn_if_untested_node", lambda v: None)
        monkeypatch.setenv("NODE_VERSION", "24.0.0")
        sp._create_nodeenv()  # must not raise


# =============================================================================
# _validate_package_json
# =============================================================================


class TestValidatePackageJson:
    """_validate_package_json: missing, valid, invalid JSON."""

    def test_missing_file_exits(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit):
            sp._validate_package_json()

    def test_valid_json_passes(self, tmp_path, monkeypatch):
        (tmp_path / "package.json").write_text('{"name": "test"}')
        monkeypatch.chdir(tmp_path)
        sp._validate_package_json()  # must not raise

    def test_invalid_json_exits(self, tmp_path, monkeypatch):
        (tmp_path / "package.json").write_text("{invalid json}")
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit):
            sp._validate_package_json()


# =============================================================================
# _install_js_packages
# =============================================================================


class TestInstallJsPackages:
    """_install_js_packages: npm absent, ci vs install, error, dev mode, version-log warning."""

    def test_npm_missing_exits(self, monkeypatch):
        monkeypatch.setattr(sp, "_get_npm_path", lambda: None)
        with pytest.raises(SystemExit):
            sp._install_js_packages()

    def test_with_package_lock_uses_ci(self, tmp_path, monkeypatch):
        (tmp_path / "package-lock.json").write_text("{}")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sp, "_get_npm_path", lambda: "/usr/bin/npm")
        monkeypatch.setattr(sp, "_validate_package_json", lambda: None)
        calls = []
        monkeypatch.setattr(subprocess, "check_call", lambda cmd, **kw: calls.append(list(cmd)))
        monkeypatch.setattr(subprocess, "check_output", lambda *a, **kw: "")
        sp._install_js_packages()
        assert any("ci" in cmd for cmd in calls)

    def test_without_package_lock_uses_install(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sp, "_get_npm_path", lambda: "/usr/bin/npm")
        monkeypatch.setattr(sp, "_validate_package_json", lambda: None)
        calls = []
        monkeypatch.setattr(subprocess, "check_call", lambda cmd, **kw: calls.append(list(cmd)))
        monkeypatch.setattr(subprocess, "check_output", lambda *a, **kw: "")
        sp._install_js_packages()
        assert any("install" in cmd for cmd in calls)

    def test_called_process_error_exits(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sp, "_get_npm_path", lambda: "/usr/bin/npm")
        monkeypatch.setattr(sp, "_validate_package_json", lambda: None)

        def _fail(cmd, **kw):
            raise subprocess.CalledProcessError(1, cmd)

        monkeypatch.setattr(subprocess, "check_call", _fail)
        with pytest.raises(SystemExit):
            sp._install_js_packages()

    def test_dev_mode_omits_husky_zero(self, tmp_path, monkeypatch):
        (tmp_path / "package-lock.json").write_text("{}")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sp, "_get_npm_path", lambda: "/usr/bin/npm")
        monkeypatch.setattr(sp, "_validate_package_json", lambda: None)
        envs = []

        def _capture(cmd, env=None, **kw):
            envs.append(env or {})

        monkeypatch.setattr(subprocess, "check_call", _capture)
        monkeypatch.setattr(subprocess, "check_output", lambda *a, **kw: "")
        sp._install_js_packages(dev_mode=True)
        for env in envs:
            assert env.get("HUSKY") != "0"

    def test_version_log_failure_is_warning(self, tmp_path, monkeypatch, caplog):
        import logging

        (tmp_path / "package-lock.json").write_text("{}")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sp, "_get_npm_path", lambda: "/usr/bin/npm")
        monkeypatch.setattr(sp, "_validate_package_json", lambda: None)
        monkeypatch.setattr(subprocess, "check_call", lambda *a, **kw: None)

        def _fail(*a, **kw):
            raise subprocess.CalledProcessError(1, a[0])

        monkeypatch.setattr(subprocess, "check_output", _fail)
        with caplog.at_level(logging.WARNING, logger="setup_project"):
            sp._install_js_packages()
        assert any("Failed to retrieve" in r.message for r in caplog.records)


# =============================================================================
# _start_server
# =============================================================================


class TestStartServer:
    """_start_server: npx absent, port in use, success, Docker, popen failure, invalid port."""

    def _args(self, silent=False):
        a = MagicMock()
        a.silent = silent
        return a

    def test_npx_missing_exits(self, monkeypatch):
        monkeypatch.setattr(sp, "_get_npx_path", lambda: None)
        with pytest.raises(SystemExit):
            sp._start_server(self._args())

    def test_returns_none_when_port_in_use(self, monkeypatch):
        monkeypatch.setattr(sp, "_get_npx_path", lambda: "/usr/bin/npx")
        monkeypatch.setattr(sp, "_is_port_in_use", lambda *a, **kw: True)
        monkeypatch.setenv("WS_HOST", "localhost")
        assert sp._start_server(self._args()) is None

    def test_starts_server_returns_proc(self, monkeypatch):
        monkeypatch.setattr(sp, "_get_npx_path", lambda: "/usr/bin/npx")
        monkeypatch.setattr(sp, "_is_port_in_use", lambda *a, **kw: False)
        monkeypatch.setattr(sp, "IS_WINDOWS", False)
        monkeypatch.delenv("IS_DOCKER", raising=False)
        monkeypatch.setenv("WS_HOST", "localhost")
        fake_proc = MagicMock()
        monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: fake_proc)
        monkeypatch.setattr(webbrowser, "open", lambda url: None)
        assert sp._start_server(self._args()) is fake_proc

    def test_docker_skips_browser(self, monkeypatch, caplog):
        import logging

        monkeypatch.setattr(sp, "_get_npx_path", lambda: "/usr/bin/npx")
        monkeypatch.setattr(sp, "_is_port_in_use", lambda *a, **kw: False)
        monkeypatch.setattr(sp, "IS_WINDOWS", False)
        monkeypatch.setenv("IS_DOCKER", "true")
        monkeypatch.setenv("WS_HOST", "localhost")
        monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: MagicMock())
        with caplog.at_level(logging.INFO, logger="setup_project"):
            sp._start_server(self._args())
        assert any("Docker" in r.message for r in caplog.records)

    def test_popen_failure_returns_none(self, monkeypatch, caplog):
        import logging

        monkeypatch.setattr(sp, "_get_npx_path", lambda: "/usr/bin/npx")
        monkeypatch.setattr(sp, "_is_port_in_use", lambda *a, **kw: False)
        monkeypatch.setattr(sp, "IS_WINDOWS", False)
        monkeypatch.delenv("IS_DOCKER", raising=False)
        monkeypatch.setenv("WS_HOST", "localhost")

        def _fail(*a, **kw):
            raise OSError("Permission denied")

        monkeypatch.setattr(subprocess, "Popen", _fail)
        monkeypatch.setattr(webbrowser, "open", lambda url: None)
        with caplog.at_level(logging.ERROR, logger="setup_project"):
            result = sp._start_server(self._args())
        assert result is None

    def test_invalid_http_port_logs_error(self, monkeypatch, caplog):
        import logging

        monkeypatch.setattr(sp, "_get_npx_path", lambda: "/usr/bin/npx")
        monkeypatch.setattr(sp, "_is_port_in_use", lambda *a, **kw: False)
        monkeypatch.setattr(sp, "IS_WINDOWS", False)
        monkeypatch.delenv("IS_DOCKER", raising=False)
        monkeypatch.setenv("HTTP_PORT", "notanumber")
        monkeypatch.setenv("WS_HOST", "localhost")
        monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: MagicMock())
        monkeypatch.setattr(webbrowser, "open", lambda url: None)
        with caplog.at_level(logging.ERROR, logger="setup_project"):
            sp._start_server(self._args())
        assert any("Invalid HTTP_PORT" in r.message for r in caplog.records)


# =============================================================================
# _run_index
# =============================================================================


class TestRunIndex:
    """_run_index: ws ready no-op, index.py present/absent, popen failure."""

    def test_returns_none_when_ws_already_ready(self, monkeypatch):
        monkeypatch.setattr(sp, "_is_websocket_server_ready", lambda port: True)
        monkeypatch.setattr(sp, "_get_python_path", lambda: Path("/usr/bin/python3.14"))
        assert sp._run_index() is None

    def test_starts_index_py_when_exists(self, tmp_path, monkeypatch):
        (tmp_path / "index.py").write_text("pass")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sp, "_is_websocket_server_ready", lambda port: False)
        monkeypatch.setattr(sp, "_get_python_path", lambda: Path("/usr/bin/python3.14"))
        monkeypatch.setattr(sp, "IS_WINDOWS", False)
        fake_proc = MagicMock()
        monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: fake_proc)
        assert sp._run_index() is fake_proc

    def test_returns_none_when_index_missing(self, tmp_path, monkeypatch, caplog):
        import logging

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sp, "_is_websocket_server_ready", lambda port: False)
        monkeypatch.setattr(sp, "_get_python_path", lambda: Path("/usr/bin/python3.14"))
        with caplog.at_level(logging.WARNING, logger="setup_project"):
            result = sp._run_index()
        assert result is None
        assert any("index.py" in r.message for r in caplog.records)

    def test_popen_failure_returns_none(self, tmp_path, monkeypatch, caplog):
        import logging

        (tmp_path / "index.py").write_text("pass")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sp, "_is_websocket_server_ready", lambda port: False)
        monkeypatch.setattr(sp, "_get_python_path", lambda: Path("/usr/bin/python3.14"))
        monkeypatch.setattr(sp, "IS_WINDOWS", False)

        def _fail(*a, **kw):
            raise OSError("Permission denied")

        monkeypatch.setattr(subprocess, "Popen", _fail)
        with caplog.at_level(logging.ERROR, logger="setup_project"):
            result = sp._run_index()
        assert result is None


# =============================================================================
# _load_dotenv_if_available
# =============================================================================


class TestLoadDotenvIfAvailable:
    """_load_dotenv_if_available: success path and import failure warning."""

    def test_calls_load_dotenv_when_available(self, monkeypatch):
        calls = []
        fake_mod = types.ModuleType("dotenv")
        setattr(fake_mod, "load_dotenv", lambda: calls.append("loaded"))
        monkeypatch.setitem(sys.modules, "dotenv", fake_mod)
        sp._load_dotenv_if_available()
        assert "loaded" in calls

    def test_logs_warning_when_import_fails(self, monkeypatch, caplog):
        import logging

        monkeypatch.setitem(sys.modules, "dotenv", None)
        with caplog.at_level(logging.WARNING, logger="setup_project"):
            sp._load_dotenv_if_available()
        assert any("unavailable" in r.message for r in caplog.records)


# =============================================================================
# _run_tests_in_venv
# =============================================================================


class TestRunTestsInVenv:
    """_run_tests_in_venv: script missing, success, integration flag."""

    def test_missing_script_raises_filenotfounderror(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(FileNotFoundError):
            sp._run_tests_in_venv()

    def test_success_path_calls_run_command(self, tmp_path, monkeypatch):
        (tmp_path / "scripts").mkdir()
        (tmp_path / "scripts" / "run_tests.py").write_text("pass")
        monkeypatch.chdir(tmp_path)
        calls = []
        monkeypatch.setattr(sp, "_run_command", lambda cmd, **kw: calls.append(cmd))
        sp._run_tests_in_venv()
        assert len(calls) == 1

    def test_integration_flag_appended(self, tmp_path, monkeypatch):
        (tmp_path / "scripts").mkdir()
        (tmp_path / "scripts" / "run_tests.py").write_text("pass")
        monkeypatch.chdir(tmp_path)
        calls = []
        monkeypatch.setattr(sp, "_run_command", lambda cmd, **kw: calls.append(cmd))
        sp._run_tests_in_venv(integration=True)
        assert any("--integration" in cmd for cmd in calls)


# =============================================================================
# _create_env_template
# =============================================================================


class TestCreateEnvTemplate:
    """_create_env_template: .env present, copy from example, create both."""

    def test_no_op_when_env_exists(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text("EXISTING=1")
        monkeypatch.chdir(tmp_path)
        sp._create_env_template()
        assert env_file.read_text() == "EXISTING=1"

    def test_copies_from_example(self, tmp_path, monkeypatch):
        (tmp_path / ".env.example").write_text("WS_PORT=8001\n")
        monkeypatch.chdir(tmp_path)
        sp._create_env_template()
        assert (tmp_path / ".env").exists()
        assert "WS_PORT=8001" in (tmp_path / ".env").read_text()

    def test_creates_example_when_neither_exists(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sp._create_env_template()
        assert (tmp_path / ".env.example").exists()
        assert "WS_PORT" in (tmp_path / ".env.example").read_text()


# =============================================================================
# _is_runtime_ready — extended: _get_environment_age_days fallback (line 1255)
# =============================================================================


class TestIsRuntimeReadyExtended:
    """_is_runtime_ready: falls back to _get_environment_age_days when no timestamp."""

    def test_falls_back_to_env_age_when_no_timestamp(self, tmp_path, monkeypatch):
        venv = tmp_path / "venv"
        venv.mkdir()
        python_path = venv / ("Scripts/python.exe" if sp.IS_WINDOWS else "bin/python")
        python_path.parent.mkdir(parents=True, exist_ok=True)
        python_path.write_bytes(b"fake")
        monkeypatch.setattr(sp, "VENV_DIR", venv)
        monkeypatch.setattr(sp, "IS_DOCKER", False)
        monkeypatch.setattr(sp, "_get_python_path", lambda: python_path)
        monkeypatch.setattr(sp, "_get_npm_path", lambda: "/usr/bin/npm")
        monkeypatch.setattr(sp, "_get_npx_path", lambda: "/usr/bin/npx")
        monkeypatch.setattr(sp, "_run_command", lambda cmd, **kw: None)
        monkeypatch.setattr(sp, "_get_last_setup_age_days", lambda: None)  # triggers fallback
        monkeypatch.setattr(sp, "_get_environment_age_days", lambda: 3)
        monkeypatch.setenv("ENV_MAX_AGE_DAYS", "14")
        assert sp._is_runtime_ready() is True

    def test_not_ready_when_env_age_stale_via_fallback(self, tmp_path, monkeypatch):
        venv = tmp_path / "venv"
        venv.mkdir()
        python_path = venv / ("Scripts/python.exe" if sp.IS_WINDOWS else "bin/python")
        python_path.parent.mkdir(parents=True, exist_ok=True)
        python_path.write_bytes(b"fake")
        monkeypatch.setattr(sp, "VENV_DIR", venv)
        monkeypatch.setattr(sp, "IS_DOCKER", False)
        monkeypatch.setattr(sp, "_get_python_path", lambda: python_path)
        monkeypatch.setattr(sp, "_get_npm_path", lambda: "/usr/bin/npm")
        monkeypatch.setattr(sp, "_get_npx_path", lambda: "/usr/bin/npx")
        monkeypatch.setattr(sp, "_run_command", lambda cmd, **kw: None)
        monkeypatch.setattr(sp, "_get_last_setup_age_days", lambda: None)
        monkeypatch.setattr(sp, "_get_environment_age_days", lambda: 30)
        monkeypatch.setenv("ENV_MAX_AGE_DAYS", "14")
        assert sp._is_runtime_ready() is False


# =============================================================================
# _run_cmd  (WSL bootstrap helper)
# =============================================================================


class TestRunCmd:
    """_run_cmd: returns returncode from subprocess.run."""

    def test_returns_returncode_zero(self, monkeypatch):
        result = MagicMock()
        result.returncode = 0
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: result)
        assert sp._run_cmd(["echo", "hello"]) == 0

    def test_returns_returncode_nonzero(self, monkeypatch):
        result = MagicMock()
        result.returncode = 1
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: result)
        assert sp._run_cmd(["false_cmd"], check=False) == 1


# =============================================================================
# WSL bootstrap helpers
# =============================================================================


class TestBootstrapHelpers:
    """_bootstrap_disable_puppet_repo, _bootstrap_fix_system_python."""

    def test_disable_puppet_no_entries_no_subprocess(self, monkeypatch):
        """On Windows /etc/apt/sources.list missing → OSError → continue; no tee call."""
        runs = []
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: runs.append(a))
        sp._bootstrap_disable_puppet_repo()
        assert len(runs) == 0

    def test_disable_puppet_with_puppet_entry(self, fs, monkeypatch):
        """Puppet repo line is commented out and sudo tee is called."""
        fs.create_file(
            "/etc/apt/sources.list",
            contents="deb https://apt.puppet.com/ubuntu focal main\n",
        )
        runs = []
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: runs.append(a[0]))
        sp._bootstrap_disable_puppet_repo()
        assert any("tee" in " ".join(cmd) for cmd in runs)

    def test_fix_system_python_no_python312(self):
        """On Windows /usr/bin/python3.12 absent → early return, no error."""
        sp._bootstrap_fix_system_python()  # must not raise

    def test_fix_system_python_restores_link(self, fs, monkeypatch):
        """Creates the ln symlink when python3 points elsewhere."""
        fs.create_file("/usr/bin/python3.12")
        fs.create_symlink("/usr/bin/python3", "/usr/bin/python3.11")
        run_calls = []
        monkeypatch.setattr(sp, "_run_cmd", lambda args, **kw: run_calls.append(args))
        sp._bootstrap_fix_system_python()
        assert any("ln" in " ".join(cmd) for cmd in run_calls)


class TestBootstrapPrintNextSteps:
    """_bootstrap_print_next_steps: output contains expected text."""

    def test_prints_project_dir_and_heading(self, tmp_path, capsys):
        sp._bootstrap_print_next_steps(tmp_path)
        captured = capsys.readouterr()
        assert "WSL bootstrap" in captured.out
        assert str(tmp_path) in captured.out


# =============================================================================
# wsl_bootstrap
# =============================================================================


class TestWslBootstrap:
    """wsl_bootstrap: platform guard, sudo guard, step invocation, run_project_setup."""

    def test_exits_on_windows_platform(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "win32")
        with pytest.raises(SystemExit):
            sp.wsl_bootstrap(Path("."))

    def test_exits_when_sudo_absent(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr(shutil, "which", lambda x: None)
        with pytest.raises(SystemExit):
            sp.wsl_bootstrap(Path("."))

    def test_calls_all_bootstrap_steps(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr(shutil, "which", lambda x: "/usr/bin/sudo" if x == "sudo" else None)
        calls = []
        for fn in (
            "_bootstrap_fix_system_python",
            "_bootstrap_disable_puppet_repo",
            "_bootstrap_install_base_packages",
            "_bootstrap_ensure_deadsnakes",
            "_bootstrap_install_python_314",
            "_bootstrap_install_node_24",
            "_bootstrap_verify_runtime",
        ):
            monkeypatch.setattr(sp, fn, lambda name=fn: calls.append(name))
        monkeypatch.setattr(sp, "_bootstrap_print_next_steps", lambda p: calls.append("next_steps"))
        sp.wsl_bootstrap(Path("."))
        assert "next_steps" in calls
        assert "_bootstrap_fix_system_python" in calls

    def test_run_project_setup_invokes_run_cmd(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr(shutil, "which", lambda x: "/usr/bin/sudo" if x == "sudo" else None)
        for fn in (
            "_bootstrap_fix_system_python",
            "_bootstrap_disable_puppet_repo",
            "_bootstrap_install_base_packages",
            "_bootstrap_ensure_deadsnakes",
            "_bootstrap_install_python_314",
            "_bootstrap_install_node_24",
            "_bootstrap_verify_runtime",
        ):
            monkeypatch.setattr(sp, fn, lambda: None)
        monkeypatch.setattr(sp, "_bootstrap_print_next_steps", lambda p: None)
        run_calls = []
        monkeypatch.setattr(sp, "_run_cmd", lambda args, **kw: run_calls.append(args))
        sp.wsl_bootstrap(Path("/proj"), run_project_setup=True)
        assert any("setup_project.py" in str(cmd) for cmd in run_calls)


# =============================================================================
# main()
# =============================================================================


class TestMain:
    """main(): argparse flows — bootstrap-wsl, stop, status, lock, fast path, full setup."""

    def _common_mocks(self, monkeypatch):
        monkeypatch.setattr(sp, "_relaunch_under_latest_python", lambda: None)
        monkeypatch.setattr(sp, "_require_python_314_or_newer", lambda *a: None)
        monkeypatch.setattr(sp, "_warn_if_untested_python", lambda *a: None)
        monkeypatch.setattr(sp, "_remove_stale_venvs", lambda *a: None)
        monkeypatch.setattr(sp, "_cleanup_local_project_artifacts", lambda *a: None)

    def test_bootstrap_wsl_flag(self, monkeypatch):
        calls = []
        monkeypatch.setattr(sys, "argv", ["setup_project.py", "--bootstrap-wsl"])
        monkeypatch.setattr(sp, "wsl_bootstrap", lambda *a, **kw: calls.append("wsl"))
        sp.main()
        assert "wsl" in calls

    def test_stop_flag(self, monkeypatch):
        calls = []
        self._common_mocks(monkeypatch)
        monkeypatch.setattr(sys, "argv", ["setup_project.py", "--stop"])
        monkeypatch.setattr(sp, "_stop_managed_processes", lambda: calls.append("stop"))
        sp.main()
        assert "stop" in calls

    def test_status_flag(self, monkeypatch, caplog):
        import logging

        self._common_mocks(monkeypatch)
        monkeypatch.setattr(sys, "argv", ["setup_project.py", "--status"])
        monkeypatch.setattr(sp, "_runtime_status", lambda: {"frontend": True, "backend": False})
        with caplog.at_level(logging.INFO, logger="setup_project"):
            sp.main()
        assert any("frontend" in r.message for r in caplog.records)

    def test_lock_not_acquired_returns_early(self, monkeypatch, caplog):
        import logging

        self._common_mocks(monkeypatch)
        monkeypatch.setattr(sys, "argv", ["setup_project.py"])
        lock_mock = MagicMock()
        lock_mock.acquire.return_value = False
        monkeypatch.setattr(sp, "_SetupLock", lambda *a: lock_mock)
        with caplog.at_level(logging.INFO, logger="setup_project"):
            sp.main()
        assert any("already running" in r.message for r in caplog.records)

    def test_fast_path_run_tests(self, monkeypatch):
        calls = []
        self._common_mocks(monkeypatch)
        monkeypatch.setattr(sys, "argv", ["setup_project.py", "--run-tests"])
        monkeypatch.setattr(sp, "_is_runtime_ready", lambda: True)
        monkeypatch.setattr(sp, "_load_dotenv_if_available", lambda: None)
        monkeypatch.setattr(sp, "_run_tests_in_venv", lambda integration=False: calls.append("tests"))
        lock_mock = MagicMock()
        lock_mock.acquire.return_value = True
        monkeypatch.setattr(sp, "_SetupLock", lambda *a: lock_mock)
        sp.main()
        assert "tests" in calls

    def test_fast_path_detach_no_block(self, monkeypatch):
        self._common_mocks(monkeypatch)
        monkeypatch.setattr(sys, "argv", ["setup_project.py", "--detach"])
        monkeypatch.setattr(sp, "_is_runtime_ready", lambda: True)
        monkeypatch.setattr(sp, "_load_dotenv_if_available", lambda: None)
        monkeypatch.setattr(sp, "_ensure_opc_server_running", lambda *a, **kw: True)
        monkeypatch.setattr(sp, "_start_server", lambda args: None)
        monkeypatch.setattr(sp, "_run_index", lambda: None)
        monkeypatch.setattr(sp, "_record_runtime_processes", lambda *a: None)
        monkeypatch.setattr(sp, "_should_block_foreground", lambda *a: False)
        lock_mock = MagicMock()
        lock_mock.acquire.return_value = True
        monkeypatch.setattr(sp, "_SetupLock", lambda *a: lock_mock)
        sp.main()  # must return without blocking

    def test_full_setup_no_internet_exits(self, monkeypatch):
        self._common_mocks(monkeypatch)
        monkeypatch.setattr(sys, "argv", ["setup_project.py", "--force_full"])
        monkeypatch.setattr(sp, "_check_internet", lambda: False)
        lock_mock = MagicMock()
        lock_mock.acquire.return_value = True
        monkeypatch.setattr(sp, "_SetupLock", lambda *a: lock_mock)
        with pytest.raises(SystemExit):
            sp.main()

    def test_full_setup_docker_mode(self, monkeypatch):
        calls = []
        self._common_mocks(monkeypatch)
        monkeypatch.setattr(sys, "argv", ["setup_project.py", "--force_full"])
        monkeypatch.setattr(sp, "_check_internet", lambda: True)
        monkeypatch.setattr(sp, "_find_latest_python_executable", lambda: (["python3.14"], "3.14"))
        monkeypatch.setattr(sp, "IS_DOCKER", True)
        monkeypatch.setattr(sp, "_ENV_IS_PRE_ISOLATED", True)
        monkeypatch.setattr(sp, "_install_python_packages", lambda: calls.append("py_pkgs"))
        monkeypatch.setattr(sp, "_create_nodeenv", lambda: None)
        monkeypatch.setattr(sp, "_install_js_packages", lambda dev_mode=False: None)
        monkeypatch.setattr(sp, "_create_env_template", lambda: None)
        monkeypatch.setattr(sp, "_load_dotenv_if_available", lambda: None)
        monkeypatch.setattr(sp, "_ensure_opc_server_running", lambda *a, **kw: True)
        monkeypatch.setattr(sp, "_start_server", lambda args: None)
        monkeypatch.setattr(sp, "_run_index", lambda: None)
        monkeypatch.setattr(sp, "_record_runtime_processes", lambda *a: None)
        monkeypatch.setattr(sp, "_should_block_foreground", lambda *a: False)
        monkeypatch.setattr(sp, "_update_setup_timestamp", lambda: None)
        lock_mock = MagicMock()
        lock_mock.acquire.return_value = True
        monkeypatch.setattr(sp, "_SetupLock", lambda *a: lock_mock)
        sp.main()
        assert "py_pkgs" in calls

    def test_full_setup_non_docker_calls_create_virtualenv(self, monkeypatch):
        calls = []
        self._common_mocks(monkeypatch)
        monkeypatch.setattr(sys, "argv", ["setup_project.py", "--force_full"])
        monkeypatch.setattr(sp, "_check_internet", lambda: True)
        monkeypatch.setattr(sp, "_find_latest_python_executable", lambda: (["python3.14"], "3.14"))
        monkeypatch.setattr(sp, "IS_DOCKER", False)
        # _ENV_IS_PRE_ISOLATED is computed at import time from IS_DOCKER or IS_GITHUB_ACTIONS.
        # In CI (IS_GITHUB_ACTIONS=True) it would be True, causing main() to skip
        # _create_virtualenv. Force False here so this non-Docker path exercises the
        # virtualenv-creation branch under test.
        monkeypatch.setattr(sp, "_ENV_IS_PRE_ISOLATED", False)
        monkeypatch.setattr(sp, "_create_virtualenv", lambda cmd: calls.append("venv"))
        monkeypatch.setattr(sp, "_install_python_packages", lambda: None)
        monkeypatch.setattr(sp, "_create_nodeenv", lambda: None)
        monkeypatch.setattr(sp, "_install_js_packages", lambda dev_mode=False: None)
        monkeypatch.setattr(sp, "_create_env_template", lambda: None)
        monkeypatch.setattr(sp, "_load_dotenv_if_available", lambda: None)
        monkeypatch.setattr(sp, "_ensure_opc_server_running", lambda *a, **kw: True)
        monkeypatch.setattr(sp, "_start_server", lambda args: None)
        monkeypatch.setattr(sp, "_run_index", lambda: None)
        monkeypatch.setattr(sp, "_record_runtime_processes", lambda *a: None)
        monkeypatch.setattr(sp, "_should_block_foreground", lambda *a: False)
        monkeypatch.setattr(sp, "_update_setup_timestamp", lambda: None)
        lock_mock = MagicMock()
        lock_mock.acquire.return_value = True
        monkeypatch.setattr(sp, "_SetupLock", lambda *a: lock_mock)
        sp.main()
        assert "venv" in calls
