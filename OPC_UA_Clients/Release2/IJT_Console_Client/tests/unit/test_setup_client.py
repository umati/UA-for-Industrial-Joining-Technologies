"""
Unit tests for setup_client.py — Console Client launcher/setup script.

All tests are pure unit tests (no server, no network, no venv creation).
External calls (subprocess, socket) are patched via monkeypatch.
"""

import logging
import socket
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ── Import setup_client from project root ────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parents[2]))
import setup_client as sc  # noqa: I001  (must follow sys.path manipulation)


# =============================================================================
# _env_bool
# =============================================================================


class TestEnvBool:
    def test_true_values(self, monkeypatch):
        for val in ("1", "true", "yes", "on", "TRUE", "YES", "ON"):
            monkeypatch.setenv("TEST_BOOL", val)
            assert sc._env_bool("TEST_BOOL", False) is True, f"Expected True for {val!r}"

    def test_false_values(self, monkeypatch):
        for val in ("0", "false", "no", "off", "anything"):
            monkeypatch.setenv("TEST_BOOL", val)
            assert sc._env_bool("TEST_BOOL", True) is False, f"Expected False for {val!r}"

    def test_none_returns_default_true(self, monkeypatch):
        monkeypatch.delenv("TEST_BOOL", raising=False)
        assert sc._env_bool("TEST_BOOL", True) is True

    def test_none_returns_default_false(self, monkeypatch):
        monkeypatch.delenv("TEST_BOOL", raising=False)
        assert sc._env_bool("TEST_BOOL", False) is False

    def test_empty_string_returns_false(self, monkeypatch):
        monkeypatch.setenv("TEST_BOOL", "")
        assert sc._env_bool("TEST_BOOL", True) is False


# =============================================================================
# _require_python_314_or_newer
# =============================================================================


class TestRequirePython314OrNewer:
    def test_exits_on_313(self):
        with pytest.raises(SystemExit) as exc_info:
            sc._require_python_314_or_newer("3.13")
        assert exc_info.value.code == 1

    def test_exits_on_27(self):
        with pytest.raises(SystemExit) as exc_info:
            sc._require_python_314_or_newer("2.7")
        assert exc_info.value.code == 1

    def test_no_exit_on_314(self):
        sc._require_python_314_or_newer("3.14")  # must not raise

    def test_no_exit_on_315(self):
        sc._require_python_314_or_newer("3.15")  # must not raise

    def test_no_exit_on_400(self):
        sc._require_python_314_or_newer("4.0")  # must not raise

    def test_invalid_string_falls_back_to_sys_version(self, monkeypatch):
        # Falls back to sys.version_info — current runtime is 3.14, so no exit.
        monkeypatch.setattr(sys, "version_info", (3, 14, 0, "final", 0))
        sc._require_python_314_or_newer("not.a.version")  # must not raise

    def test_no_arg_uses_sys_version_info_passes_when_314(self, monkeypatch):
        monkeypatch.setattr(sys, "version_info", (3, 14, 0, "final", 0))
        sc._require_python_314_or_newer()  # must not raise

    def test_no_arg_uses_sys_version_info_exits_when_313(self, monkeypatch):
        monkeypatch.setattr(sys, "version_info", (3, 13, 0, "final", 0))
        with pytest.raises(SystemExit) as exc_info:
            sc._require_python_314_or_newer()
        assert exc_info.value.code == 1


# =============================================================================
# _warn_if_untested_python
# =============================================================================


class TestWarnIfUntestedPython:
    def test_warns_when_minor_exceeds_tested_max(self, monkeypatch, caplog):
        monkeypatch.delenv("PYTHON_TESTED_MAX_MINOR", raising=False)
        with caplog.at_level(logging.WARNING, logger="setup_client"):
            sc._warn_if_untested_python("3.15")
        assert any("compatibility mode" in r.message for r in caplog.records)

    def test_no_warning_at_tested_max(self, monkeypatch, caplog):
        monkeypatch.delenv("PYTHON_TESTED_MAX_MINOR", raising=False)
        with caplog.at_level(logging.WARNING, logger="setup_client"):
            sc._warn_if_untested_python("3.14")
        assert not any("compatibility mode" in r.message for r in caplog.records)

    def test_no_warning_below_tested_max(self, monkeypatch, caplog):
        monkeypatch.delenv("PYTHON_TESTED_MAX_MINOR", raising=False)
        with caplog.at_level(logging.WARNING, logger="setup_client"):
            sc._warn_if_untested_python("3.13")
        assert not any("compatibility mode" in r.message for r in caplog.records)

    def test_no_crash_on_invalid_version_string(self, monkeypatch):
        monkeypatch.delenv("PYTHON_TESTED_MAX_MINOR", raising=False)
        sc._warn_if_untested_python("not-a-version")  # must not raise

    def test_respects_python_tested_max_minor_env_var(self, monkeypatch, caplog):
        monkeypatch.setenv("PYTHON_TESTED_MAX_MINOR", "15")
        with caplog.at_level(logging.WARNING, logger="setup_client"):
            sc._warn_if_untested_python("3.15")
        assert not any("compatibility mode" in r.message for r in caplog.records)

    def test_warns_when_above_custom_tested_max(self, monkeypatch, caplog):
        monkeypatch.setenv("PYTHON_TESTED_MAX_MINOR", "15")
        with caplog.at_level(logging.WARNING, logger="setup_client"):
            sc._warn_if_untested_python("3.16")
        assert any("compatibility mode" in r.message for r in caplog.records)

    def test_invalid_env_var_returns_without_crash(self, monkeypatch, caplog):
        monkeypatch.setenv("PYTHON_TESTED_MAX_MINOR", "notanint")
        with caplog.at_level(logging.WARNING, logger="setup_client"):
            sc._warn_if_untested_python("3.15")
        assert any("Invalid PYTHON_TESTED_MAX_MINOR" in r.message for r in caplog.records)

    def test_no_arg_uses_sys_version(self, monkeypatch):
        monkeypatch.setattr(sys, "version_info", (3, 14, 0, "final", 0))
        monkeypatch.delenv("PYTHON_TESTED_MAX_MINOR", raising=False)
        sc._warn_if_untested_python()  # must not raise


# =============================================================================
# _parse_endpoint_host_port
# =============================================================================


class TestParseEndpointHostPort:
    def test_standard_url_returns_host_and_port(self):
        host, port = sc._parse_endpoint_host_port("opc.tcp://myhost:12345")
        assert host == "myhost"
        assert port == 12345

    def test_localhost_url(self):
        host, port = sc._parse_endpoint_host_port("opc.tcp://localhost:40451")
        assert host == "localhost"
        assert port == 40451

    def test_no_port_defaults_to_40451(self):
        host, port = sc._parse_endpoint_host_port("opc.tcp://somehost")
        assert host == "somehost"
        assert port == 40451

    def test_no_host_defaults_to_localhost(self):
        _, port = sc._parse_endpoint_host_port("opc.tcp://:40451")
        assert port == 40451

    def test_ip_address_url(self):
        host, port = sc._parse_endpoint_host_port("opc.tcp://192.168.1.100:4840")
        assert host == "192.168.1.100"
        assert port == 4840


# =============================================================================
# _is_endpoint_reachable
# =============================================================================


class TestIsEndpointReachable:
    def _make_mock_socket(self, connect_ex_result):
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = connect_ex_result
        return mock_sock

    def test_returns_true_when_connect_ex_is_zero(self, monkeypatch):
        mock_sock = self._make_mock_socket(0)
        monkeypatch.setattr(socket, "socket", lambda *a, **_kw: mock_sock)
        assert sc._is_endpoint_reachable("opc.tcp://localhost:40451") is True

    def test_returns_false_when_connect_ex_nonzero(self, monkeypatch):
        mock_sock = self._make_mock_socket(111)
        monkeypatch.setattr(socket, "socket", lambda *a, **_kw: mock_sock)
        assert sc._is_endpoint_reachable("opc.tcp://localhost:40451") is False

    def test_uses_parse_endpoint_host_port(self, monkeypatch):
        captured = []
        mock_sock = self._make_mock_socket(0)

        def fake_connect_ex(addr):
            captured.append(addr)
            return 0

        mock_sock.connect_ex.side_effect = fake_connect_ex
        monkeypatch.setattr(socket, "socket", lambda *a, **_kw: mock_sock)
        sc._is_endpoint_reachable("opc.tcp://myhost:9999")
        assert captured == [("myhost", 9999)]

    def test_socket_close_called_on_success(self, monkeypatch):
        mock_sock = self._make_mock_socket(0)
        monkeypatch.setattr(socket, "socket", lambda *a, **_kw: mock_sock)
        sc._is_endpoint_reachable("opc.tcp://localhost:40451")
        mock_sock.close.assert_called_once()

    def test_socket_close_called_on_failure(self, monkeypatch):
        mock_sock = self._make_mock_socket(111)
        monkeypatch.setattr(socket, "socket", lambda *a, **_kw: mock_sock)
        sc._is_endpoint_reachable("opc.tcp://localhost:40451")
        mock_sock.close.assert_called_once()


# =============================================================================
# _env_float
# =============================================================================


class TestEnvFloat:
    def test_returns_parsed_float(self, monkeypatch):
        monkeypatch.setenv("TEST_FLOAT", "3.5")
        assert sc._env_float("TEST_FLOAT", 1.0, 0.0) == 3.5

    def test_warns_and_returns_default_on_invalid(self, monkeypatch, caplog):
        monkeypatch.setenv("TEST_FLOAT", "notanumber")
        with caplog.at_level(logging.WARNING, logger="setup_client"):
            result = sc._env_float("TEST_FLOAT", 2.0, 0.0)
        assert result == 2.0
        assert any("Invalid" in r.message or "TEST_FLOAT" in r.message for r in caplog.records)

    def test_enforces_minimum(self, monkeypatch):
        monkeypatch.setenv("TEST_FLOAT", "0.05")
        result = sc._env_float("TEST_FLOAT", 1.0, 0.1)
        assert result == 0.1

    def test_minimum_not_applied_when_above_it(self, monkeypatch):
        monkeypatch.setenv("TEST_FLOAT", "5.0")
        result = sc._env_float("TEST_FLOAT", 1.0, 0.1)
        assert result == 5.0

    def test_uses_default_when_env_not_set(self, monkeypatch):
        monkeypatch.delenv("TEST_FLOAT", raising=False)
        result = sc._env_float("TEST_FLOAT", 7.5, 0.0)
        assert result == 7.5


# =============================================================================
# _is_simulator_process_running
# =============================================================================


class TestIsSimulatorProcessRunning:
    def test_returns_false_on_non_windows(self, monkeypatch):
        monkeypatch.setattr(sc, "IS_WINDOWS", False)
        assert sc._is_simulator_process_running() is False

    def test_returns_true_when_exe_in_tasklist(self, monkeypatch):
        monkeypatch.setattr(sc, "IS_WINDOWS", True)
        output = f"Image Name                     PID\n{sc.SIMULATOR_EXE_NAME}    1234\n"
        monkeypatch.setattr(subprocess, "check_output", lambda *a, **_kw: output)
        assert sc._is_simulator_process_running() is True

    def test_returns_false_when_exe_not_in_tasklist(self, monkeypatch):
        monkeypatch.setattr(sc, "IS_WINDOWS", True)
        output = "Image Name                     PID\nnotepad.exe    5678\n"
        monkeypatch.setattr(subprocess, "check_output", lambda *a, **_kw: output)
        assert sc._is_simulator_process_running() is False

    def test_returns_false_when_tasklist_raises(self, monkeypatch):
        monkeypatch.setattr(sc, "IS_WINDOWS", True)

        def _fail(*a, **_kw):
            raise OSError("No such command")

        monkeypatch.setattr(subprocess, "check_output", _fail)
        assert sc._is_simulator_process_running() is False


# =============================================================================
# _extract_simulator_zip_if_needed
# =============================================================================


class TestExtractSimulatorZipIfNeeded:
    def test_skipped_when_simulator_dir_exists(self, fs, monkeypatch):
        sim_dir = Path("/fake/sim")
        sim_dir.mkdir(parents=True)
        monkeypatch.setattr(sc, "SIMULATOR_DIR", sim_dir)
        monkeypatch.setattr(sc, "SIMULATOR_ZIP", Path("/fake/sim.zip"))
        sc._extract_simulator_zip_if_needed()  # no exception

    def test_skipped_when_zip_does_not_exist(self, fs, monkeypatch):
        monkeypatch.setattr(sc, "SIMULATOR_DIR", Path("/fake/missing_dir"))
        monkeypatch.setattr(sc, "SIMULATOR_ZIP", Path("/fake/nonexistent.zip"))
        sc._extract_simulator_zip_if_needed()  # no exception

    def test_extracts_when_zip_exists_and_dir_missing(self, fs, monkeypatch):
        base = Path("/fake")
        base.mkdir(parents=True, exist_ok=True)
        sim_dir = base / "Release2"
        zip_path = base / "sim.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("opcua_ijt_demo_application.exe", "fake")
        monkeypatch.setattr(sc, "SIMULATOR_DIR", sim_dir)
        monkeypatch.setattr(sc, "SIMULATOR_ZIP", zip_path)
        sc._extract_simulator_zip_if_needed()
        assert (base / "opcua_ijt_demo_application.exe").exists()

    def test_logs_warning_on_corrupt_zip(self, fs, monkeypatch, caplog):
        zip_path = Path("/fake/corrupt.zip")
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        zip_path.write_bytes(b"not a zip")
        monkeypatch.setattr(sc, "SIMULATOR_DIR", Path("/fake/missing_dir"))
        monkeypatch.setattr(sc, "SIMULATOR_ZIP", zip_path)
        with caplog.at_level(logging.WARNING, logger="setup_client"):
            sc._extract_simulator_zip_if_needed()
        assert any("Failed to extract" in r.message for r in caplog.records)


# =============================================================================
# _find_simulator_executable
# =============================================================================


class TestFindSimulatorExecutable:
    def test_returns_none_when_dir_missing(self, fs, monkeypatch):
        monkeypatch.setattr(sc, "SIMULATOR_DIR", Path("/fake/nonexistent"))
        assert sc._find_simulator_executable() is None

    def test_finds_direct_exe(self, fs, monkeypatch):
        sim_dir = Path("/fake/sim")
        sim_dir.mkdir(parents=True)
        exe = sim_dir / sc.SIMULATOR_EXE_NAME
        exe.write_bytes(b"fake exe")
        monkeypatch.setattr(sc, "SIMULATOR_DIR", sim_dir)
        assert sc._find_simulator_executable() == exe

    def test_finds_nested_exe_via_rglob(self, fs, monkeypatch):
        sim_dir = Path("/fake/sim")
        nested = sim_dir / "subdir" / "deeper"
        nested.mkdir(parents=True)
        exe = nested / sc.SIMULATOR_EXE_NAME
        exe.write_bytes(b"fake exe")
        monkeypatch.setattr(sc, "SIMULATOR_DIR", sim_dir)
        assert sc._find_simulator_executable() == exe

    def test_returns_none_when_no_exe_found(self, fs, monkeypatch):
        sim_dir = Path("/fake/sim")
        sim_dir.mkdir(parents=True)
        (sim_dir / "readme.txt").write_text("no exe here")
        monkeypatch.setattr(sc, "SIMULATOR_DIR", sim_dir)
        assert sc._find_simulator_executable() is None


# =============================================================================
# _ensure_opc_server_running
# =============================================================================


class TestEnsureOpcServerRunning:
    def test_returns_true_when_already_reachable(self, monkeypatch):
        monkeypatch.setattr(sc, "_wait_for_endpoint_ready", lambda _ep, **_kw: True)
        assert sc._ensure_opc_server_running("opc.tcp://localhost:40451", context="test", allow_launch=True) is True

    def test_docker_skips_launch_returns_false(self, monkeypatch):
        call_count = [0]

        def fake_wait(_ep, **_kw):
            call_count[0] += 1
            return False

        monkeypatch.setattr(sc, "_wait_for_endpoint_ready", fake_wait)
        monkeypatch.setattr(sc, "IS_DOCKER", True)
        result = sc._ensure_opc_server_running("opc.tcp://localhost:40451", context="docker", allow_launch=True)
        assert result is False

    def test_allow_launch_false_skips_popen(self, monkeypatch):
        popen_calls = []
        exe = Path("/fake") / sc.SIMULATOR_EXE_NAME
        monkeypatch.setattr(sc, "_wait_for_endpoint_ready", lambda _ep, **_kw: False)
        monkeypatch.setattr(sc, "IS_DOCKER", False)
        monkeypatch.setattr(sc, "_find_simulator_executable", lambda: exe)
        monkeypatch.setattr(subprocess, "Popen", lambda *a, **_kw: popen_calls.append(a[0]))
        result = sc._ensure_opc_server_running("opc.tcp://localhost:40451", context="no-launch", allow_launch=False)
        assert result is False
        assert popen_calls == []

    def test_auto_launch_succeeds(self, monkeypatch):
        exe = Path("/fake") / sc.SIMULATOR_EXE_NAME
        popen_calls = []
        wait_count = [0]

        def fake_wait(_ep, **_kw):
            wait_count[0] += 1
            # 1st call: not ready; 2nd call (post-launch): ready
            return wait_count[0] >= 2

        monkeypatch.setattr(sc, "_wait_for_endpoint_ready", fake_wait)
        monkeypatch.setattr(sc, "IS_DOCKER", False)
        monkeypatch.setattr(sc, "_extract_simulator_zip_if_needed", lambda: None)
        monkeypatch.setattr(sc, "_find_simulator_executable", lambda: exe)
        monkeypatch.setattr(sc, "_is_simulator_process_running", lambda: False)

        mock_proc = MagicMock()
        mock_proc.pid = 9999
        monkeypatch.setattr(subprocess, "Popen", lambda *a, **_kw: (popen_calls.append(a[0]), mock_proc)[1])

        result = sc._ensure_opc_server_running("opc.tcp://localhost:40451", context="auto-launch", allow_launch=True)
        assert result is True
        assert len(popen_calls) == 1

    def test_auto_launch_fails_when_endpoint_not_ready_after_launch(self, monkeypatch):
        exe = Path("/fake") / sc.SIMULATOR_EXE_NAME
        mock_proc = MagicMock()
        mock_proc.pid = 9999
        monkeypatch.setattr(sc, "_wait_for_endpoint_ready", lambda _ep, **_kw: False)
        monkeypatch.setattr(sc, "IS_DOCKER", False)
        monkeypatch.setattr(sc, "_extract_simulator_zip_if_needed", lambda: None)
        monkeypatch.setattr(sc, "_find_simulator_executable", lambda: exe)
        monkeypatch.setattr(sc, "_is_simulator_process_running", lambda: False)
        monkeypatch.setattr(subprocess, "Popen", lambda *a, **_kw: mock_proc)
        result = sc._ensure_opc_server_running("opc.tcp://localhost:40451", context="launch-timeout", allow_launch=True)
        assert result is False

    def test_no_exe_found_returns_false(self, monkeypatch):
        monkeypatch.setattr(sc, "_wait_for_endpoint_ready", lambda _ep, **_kw: False)
        monkeypatch.setattr(sc, "IS_DOCKER", False)
        monkeypatch.setattr(sc, "_extract_simulator_zip_if_needed", lambda: None)
        monkeypatch.setattr(sc, "_find_simulator_executable", lambda: None)
        result = sc._ensure_opc_server_running("opc.tcp://localhost:40451", context="no-exe", allow_launch=True)
        assert result is False

    def test_popen_oserror_returns_false_with_warning(self, monkeypatch, caplog):
        exe = Path("/fake") / sc.SIMULATOR_EXE_NAME

        def _bad_popen(*a, **_kw):
            raise OSError("Access denied")

        monkeypatch.setattr(sc, "_wait_for_endpoint_ready", lambda _ep, **_kw: False)
        monkeypatch.setattr(sc, "IS_DOCKER", False)
        monkeypatch.setattr(sc, "_extract_simulator_zip_if_needed", lambda: None)
        monkeypatch.setattr(sc, "_find_simulator_executable", lambda: exe)
        monkeypatch.setattr(sc, "_is_simulator_process_running", lambda: False)
        monkeypatch.setattr(subprocess, "Popen", _bad_popen)
        with caplog.at_level(logging.WARNING, logger="setup_client"):
            result = sc._ensure_opc_server_running(
                "opc.tcp://localhost:40451", context="popen-error", allow_launch=True
            )
        assert result is False
        assert any("Failed to launch" in r.message for r in caplog.records)

    def test_simulator_already_running_skips_popen(self, monkeypatch):
        exe = Path("/fake") / sc.SIMULATOR_EXE_NAME
        popen_calls = []
        wait_count = [0]

        def fake_wait(_ep, **_kw):
            wait_count[0] += 1
            return wait_count[0] >= 2

        monkeypatch.setattr(sc, "_wait_for_endpoint_ready", fake_wait)
        monkeypatch.setattr(sc, "IS_DOCKER", False)
        monkeypatch.setattr(sc, "_extract_simulator_zip_if_needed", lambda: None)
        monkeypatch.setattr(sc, "_find_simulator_executable", lambda: exe)
        monkeypatch.setattr(sc, "_is_simulator_process_running", lambda: True)
        monkeypatch.setattr(subprocess, "Popen", lambda *a, **_kw: popen_calls.append(1))
        sc._ensure_opc_server_running("opc.tcp://localhost:40451", context="already-running", allow_launch=True)
        assert popen_calls == []


# =============================================================================
# _get_last_setup_age_days
# =============================================================================


class TestGetLastSetupAgeDays:
    def test_returns_none_when_file_missing(self, fs, monkeypatch):
        monkeypatch.setattr(sc, "SETUP_TIMESTAMP_FILE", Path("/fake/.setup_timestamp"))
        assert sc._get_last_setup_age_days() is None

    def test_returns_correct_float_age(self, fs, monkeypatch):
        ts_file = Path("/fake/.setup_timestamp")
        ts_file.parent.mkdir(parents=True, exist_ok=True)
        one_day_ago = time.time() - (60 * 60 * 24)
        ts_file.write_text(str(one_day_ago), encoding="utf-8")
        monkeypatch.setattr(sc, "SETUP_TIMESTAMP_FILE", ts_file)
        age = sc._get_last_setup_age_days()
        assert age is not None
        assert 0.99 < age < 1.01  # approximately 1 day

    def test_warns_and_returns_none_on_invalid_content(self, fs, monkeypatch, caplog):
        ts_file = Path("/fake/.setup_timestamp")
        ts_file.parent.mkdir(parents=True, exist_ok=True)
        ts_file.write_text("not-a-number", encoding="utf-8")
        monkeypatch.setattr(sc, "SETUP_TIMESTAMP_FILE", ts_file)
        with caplog.at_level(logging.WARNING, logger="setup_client"):
            result = sc._get_last_setup_age_days()
        assert result is None
        assert any("setup timestamp" in r.message.lower() for r in caplog.records)

    def test_migrates_legacy_root_timestamp_to_state_dir(self, fs, monkeypatch):
        """Legacy .setup_timestamp at project root is moved into .state/ on first read."""
        state_dir = Path(".state")
        new_path = state_dir / "setup_timestamp"
        monkeypatch.setattr(sc, "STATE_DIR", state_dir)
        monkeypatch.setattr(sc, "SETUP_TIMESTAMP_FILE", new_path)
        one_day_ago = time.time() - (60 * 60 * 24)
        Path(".setup_timestamp").write_text(str(one_day_ago), encoding="utf-8")

        age = sc._get_last_setup_age_days()

        assert age is not None
        assert 0.99 < age < 1.01
        assert not Path(".setup_timestamp").exists(), "legacy file must be removed after migration"
        assert new_path.exists(), "timestamp must exist in .state/ after migration"

    def test_removes_stale_legacy_when_both_exist(self, fs, monkeypatch):
        """If both old root .setup_timestamp and new .state/setup_timestamp exist, stale root copy is deleted."""
        state_dir = Path(".state")
        new_path = state_dir / "setup_timestamp"
        state_dir.mkdir()
        one_day_ago = time.time() - (60 * 60 * 24)
        new_path.write_text(str(one_day_ago), encoding="utf-8")
        Path(".setup_timestamp").write_text("stale", encoding="utf-8")
        monkeypatch.setattr(sc, "STATE_DIR", state_dir)
        monkeypatch.setattr(sc, "SETUP_TIMESTAMP_FILE", new_path)

        age = sc._get_last_setup_age_days()

        assert age is not None
        assert not Path(".setup_timestamp").exists(), "stale root copy must be removed"
        assert new_path.exists(), "canonical .state/ copy must remain"


# =============================================================================
# _update_setup_timestamp
# =============================================================================


class TestUpdateSetupTimestamp:
    def test_writes_parseable_float(self, fs, monkeypatch):
        ts_file = Path("/fake/.setup_timestamp")
        ts_file.parent.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(sc, "SETUP_TIMESTAMP_FILE", ts_file)
        before = time.time()
        sc._update_setup_timestamp()
        after = time.time()
        assert ts_file.exists()
        content = ts_file.read_text(encoding="utf-8").strip()
        stamp = float(content)  # must not raise
        assert before <= stamp <= after

    def test_overwrites_existing_file(self, fs, monkeypatch):
        ts_file = Path("/fake/.setup_timestamp")
        ts_file.parent.mkdir(parents=True, exist_ok=True)
        ts_file.write_text("0.0", encoding="utf-8")
        monkeypatch.setattr(sc, "SETUP_TIMESTAMP_FILE", ts_file)
        sc._update_setup_timestamp()
        stamp = float(ts_file.read_text(encoding="utf-8").strip())
        assert stamp > 1_000_000_000  # should be a real Unix timestamp, not 0.0

    def test_creates_state_dir_if_missing(self, fs, monkeypatch):
        """STATE_DIR is created automatically — no manual mkdir needed before first setup."""
        state_dir = Path(".state")
        ts_file = state_dir / "setup_timestamp"
        monkeypatch.setattr(sc, "STATE_DIR", state_dir)
        monkeypatch.setattr(sc, "SETUP_TIMESTAMP_FILE", ts_file)
        assert not state_dir.exists()

        sc._update_setup_timestamp()

        assert state_dir.exists(), "STATE_DIR must be created automatically"
        assert ts_file.exists(), "timestamp file must be written inside STATE_DIR"


# =============================================================================
# _is_runtime_ready
# =============================================================================


class TestIsRuntimeReady:
    def _make_venv(self, base: Path) -> Path:
        venv = base / "venv"
        venv.mkdir(parents=True, exist_ok=True)
        python = venv / ("Scripts/python.exe" if sc.IS_WINDOWS else "bin/python")
        python.parent.mkdir(parents=True, exist_ok=True)
        python.write_bytes(b"fake python")
        return venv

    def _patch_basics(self, monkeypatch, base, *, venv_exists=True, deps_ok=True, age_days=1):
        if venv_exists:
            venv = self._make_venv(base)
        else:
            venv = base / "venv"
        monkeypatch.setattr(sc, "VENV_DIR", venv)
        if deps_ok:
            monkeypatch.setattr(sc, "_run_command", lambda cmd, **_kw: None)
        else:

            def _fail(*a, **_kw):
                raise Exception("missing dep")

            monkeypatch.setattr(sc, "_run_command", _fail)
        monkeypatch.setattr(sc, "_get_last_setup_age_days", lambda: age_days)
        monkeypatch.setattr(sc, "_get_environment_age_days", lambda: age_days)
        monkeypatch.setenv("ENV_MAX_AGE_DAYS", "14")

    def test_true_when_all_present_and_fresh(self, fs, monkeypatch):
        base = Path("/fake")
        base.mkdir()
        self._patch_basics(monkeypatch, base)
        assert sc._is_runtime_ready() is True

    def test_false_when_venv_missing(self, fs, monkeypatch):
        base = Path("/fake")
        base.mkdir()
        self._patch_basics(monkeypatch, base, venv_exists=False)
        assert sc._is_runtime_ready() is False

    def test_false_when_python_exe_missing(self, fs, monkeypatch):
        base = Path("/fake")
        venv = base / "venv"
        venv.mkdir(parents=True)
        # python binary deliberately NOT created
        monkeypatch.setattr(sc, "VENV_DIR", venv)
        monkeypatch.setattr(sc, "_get_last_setup_age_days", lambda: 1)
        monkeypatch.setenv("ENV_MAX_AGE_DAYS", "14")
        assert sc._is_runtime_ready() is False

    def test_false_when_dep_check_fails(self, fs, monkeypatch):
        base = Path("/fake")
        base.mkdir()
        self._patch_basics(monkeypatch, base, deps_ok=False)
        assert sc._is_runtime_ready() is False

    def test_false_when_age_stale(self, fs, monkeypatch):
        base = Path("/fake")
        base.mkdir()
        self._patch_basics(monkeypatch, base, age_days=30)
        assert sc._is_runtime_ready() is False

    def test_true_at_exact_boundary_age(self, fs, monkeypatch):
        base = Path("/fake")
        base.mkdir()
        self._patch_basics(monkeypatch, base, age_days=14)
        assert sc._is_runtime_ready() is True  # 14 == threshold, not > 14

    def test_false_just_over_boundary(self, fs, monkeypatch):
        base = Path("/fake")
        base.mkdir()
        self._patch_basics(monkeypatch, base, age_days=15)
        assert sc._is_runtime_ready() is False

    def test_true_when_age_is_none(self, fs, monkeypatch):
        base = Path("/fake")
        base.mkdir()
        venv = self._make_venv(base)
        monkeypatch.setattr(sc, "VENV_DIR", venv)
        monkeypatch.setattr(sc, "_run_command", lambda cmd, **_kw: None)
        monkeypatch.setattr(sc, "_get_last_setup_age_days", lambda: None)
        monkeypatch.setattr(sc, "_get_environment_age_days", lambda: None)
        monkeypatch.setenv("ENV_MAX_AGE_DAYS", "14")
        assert sc._is_runtime_ready() is True


# =============================================================================
# _validate_url_or_default
# =============================================================================


class TestValidateUrlOrDefault:
    DEFAULT = "opc.tcp://localhost:40451"

    def test_returns_default_when_none(self):
        assert sc._validate_url_or_default(None) == self.DEFAULT

    def test_returns_default_when_empty_string(self):
        assert sc._validate_url_or_default("") == self.DEFAULT

    def test_returns_url_when_valid(self):
        url = "opc.tcp://myserver:4840"
        assert sc._validate_url_or_default(url) == url

    def test_returns_default_with_warning_on_invalid_scheme(self, caplog):
        with caplog.at_level(logging.WARNING, logger="setup_client"):
            result = sc._validate_url_or_default("http://myserver:4840")
        assert result == self.DEFAULT
        assert any("Invalid OPC UA URL" in r.message or "opc.tcp" in r.message for r in caplog.records)

    def test_returns_default_with_warning_on_plain_host(self, caplog):
        with caplog.at_level(logging.WARNING, logger="setup_client"):
            result = sc._validate_url_or_default("localhost:40451")
        assert result == self.DEFAULT

    def test_valid_url_no_warning(self, caplog):
        with caplog.at_level(logging.WARNING, logger="setup_client"):
            sc._validate_url_or_default("opc.tcp://localhost:40451")
        assert not any("Invalid" in r.message for r in caplog.records)


# =============================================================================
# _run_client
# =============================================================================


class TestRunClient:
    def test_exits_when_main_py_missing(self, fs, monkeypatch):
        rundir = Path("/fake/rundir")
        rundir.mkdir(parents=True)
        monkeypatch.chdir(rundir)
        monkeypatch.setattr(sc, "VENV_DIR", rundir / "venv")
        with pytest.raises(SystemExit) as exc_info:
            sc._run_client("opc.tcp://localhost:40451", passthrough=None)
        assert exc_info.value.code == 1

    def test_calls_subprocess_call_with_url_arg(self, fs, monkeypatch):
        rundir = Path("/fake/rundir")
        rundir.mkdir(parents=True)
        monkeypatch.chdir(rundir)
        (rundir / "main.py").write_text("# fake main")
        monkeypatch.setattr(sc, "VENV_DIR", rundir / "venv")
        call_args = []
        monkeypatch.setattr(subprocess, "call", lambda cmd: call_args.append(cmd))
        sc._run_client("opc.tcp://localhost:40451", passthrough=None)
        assert len(call_args) == 1
        assert "--url=opc.tcp://localhost:40451" in call_args[0]
        assert "main.py" in call_args[0][1]

    def test_passthrough_args_appended(self, fs, monkeypatch):
        rundir = Path("/fake/rundir")
        rundir.mkdir(parents=True)
        monkeypatch.chdir(rundir)
        (rundir / "main.py").write_text("# fake main")
        monkeypatch.setattr(sc, "VENV_DIR", rundir / "venv")
        call_args = []
        monkeypatch.setattr(subprocess, "call", lambda cmd: call_args.append(cmd))
        sc._run_client("opc.tcp://localhost:40451", passthrough=["--verbose", "--timeout=30"])
        cmd = call_args[0]
        assert "--verbose" in cmd
        assert "--timeout=30" in cmd

    def test_keyboard_interrupt_handled_gracefully(self, fs, monkeypatch):
        rundir = Path("/fake/rundir")
        rundir.mkdir(parents=True)
        monkeypatch.chdir(rundir)
        (rundir / "main.py").write_text("# fake main")
        monkeypatch.setattr(sc, "VENV_DIR", rundir / "venv")

        def _raise_interrupt(cmd):
            raise KeyboardInterrupt

        monkeypatch.setattr(subprocess, "call", _raise_interrupt)
        sc._run_client("opc.tcp://localhost:40451", passthrough=None)  # must not propagate

    def test_no_passthrough_when_none(self, fs, monkeypatch):
        rundir = Path("/fake/rundir")
        rundir.mkdir(parents=True)
        monkeypatch.chdir(rundir)
        (rundir / "main.py").write_text("# fake main")
        monkeypatch.setattr(sc, "VENV_DIR", rundir / "venv")
        call_args = []
        monkeypatch.setattr(subprocess, "call", lambda cmd: call_args.append(cmd))
        sc._run_client("opc.tcp://localhost:40451", passthrough=None)
        # cmd should be [python, main.py, --url=...]  — exactly 3 elements
        assert len(call_args[0]) == 3


# =============================================================================
# _list_pythons_windows
# =============================================================================


class TestListPythonsWindows:
    def test_parses_version_from_v_colon_prefix(self, monkeypatch):
        output = " -V:3.14 *       Python 3.14.0\n -V:3.13          Python 3.13.0\n"
        monkeypatch.setattr(subprocess, "check_output", lambda *a, **_kw: output)
        versions = sc._list_pythons_windows()
        assert "3.14" in versions
        assert "3.13" in versions

    def test_parses_version_from_dash_prefix(self, monkeypatch):
        output = " -3.14 *          Python 3.14.0\n"
        monkeypatch.setattr(subprocess, "check_output", lambda *a, **_kw: output)
        versions = sc._list_pythons_windows()
        assert "3.14" in versions

    def test_returns_empty_list_when_py_fails(self, monkeypatch):
        def _fail(*a, **_kw):
            raise FileNotFoundError("py not found")

        monkeypatch.setattr(subprocess, "check_output", _fail)
        assert sc._list_pythons_windows() == []

    def test_ignores_non_version_lines(self, monkeypatch):
        output = "Installed Pythons found by py Launcher for Windows\n -V:3.14 *\n"
        monkeypatch.setattr(subprocess, "check_output", lambda *a, **_kw: output)
        versions = sc._list_pythons_windows()
        # Should only have 3.14, not the header line
        assert versions == ["3.14"]

    def test_ignores_three_part_versions(self, monkeypatch):
        output = " -V:3.14.1        Python 3.14.1\n"
        monkeypatch.setattr(subprocess, "check_output", lambda *a, **_kw: output)
        versions = sc._list_pythons_windows()
        # 3.14.1 has two dots, so count(".") != 1 — should be excluded
        assert "3.14.1" not in versions

    def test_returns_empty_on_empty_output(self, monkeypatch):
        monkeypatch.setattr(subprocess, "check_output", lambda *a, **_kw: "")
        assert sc._list_pythons_windows() == []


# =============================================================================
# Additional imports for new test classes
# =============================================================================
import os  # noqa: E402  (appended after sys.path manipulation block)
import shutil  # noqa: E402

# =============================================================================
# _detect_repo_root
# =============================================================================


class TestDetectRepoRoot:
    """Tests for _detect_repo_root() — walks parent chain to find repo root."""

    def test_finds_root_in_grandparent(self, tmp_path):
        (tmp_path / "OPC_UA_Clients").mkdir()
        (tmp_path / "OPC_UA_Servers").mkdir()
        start_dir = tmp_path / "deep" / "nested"
        start_dir.mkdir(parents=True)
        assert sc._detect_repo_root(start_dir) == tmp_path

    def test_returns_start_dir_when_markers_absent(self, fs):
        # Use pyfakefs to avoid the real repo root being found via parent traversal
        start_dir = Path("/isolated/project/src")
        start_dir.mkdir(parents=True)
        assert sc._detect_repo_root(start_dir) == start_dir

    def test_finds_root_when_start_dir_is_root(self, tmp_path):
        (tmp_path / "OPC_UA_Clients").mkdir()
        (tmp_path / "OPC_UA_Servers").mkdir()
        assert sc._detect_repo_root(tmp_path) == tmp_path

    def test_only_one_marker_present_falls_back(self, fs):
        # Use pyfakefs so no real repo markers exist in parent chain
        start_dir = Path("/isolated/sub")
        start_dir.mkdir(parents=True)
        (Path("/isolated") / "OPC_UA_Clients").mkdir()
        # OPC_UA_Servers intentionally absent
        assert sc._detect_repo_root(start_dir) == start_dir


# =============================================================================
# _force_rmtree
# =============================================================================


class TestForceRmtree:
    """Tests for _force_rmtree() — robust directory removal with error handler."""

    def test_removes_directory_tree(self, tmp_path):
        target = tmp_path / "to_remove"
        target.mkdir()
        (target / "file.txt").write_text("content")
        (target / "sub").mkdir()
        sc._force_rmtree(target)
        assert not target.exists()

    def test_passes_onexc_kwarg_to_shutil_rmtree(self, tmp_path, monkeypatch):
        target = tmp_path / "to_remove"
        target.mkdir()
        captured = {}
        monkeypatch.setattr(
            shutil,
            "rmtree",
            lambda path, onexc=None: captured.update({"path": path, "onexc": onexc}),
        )
        sc._force_rmtree(target)
        assert captured["onexc"] is not None, "error handler must be supplied to rmtree"

    def test_on_exc_handler_calls_chmod_and_retries_func(self, tmp_path, monkeypatch):
        """Capture the onexc handler then invoke it — verifies chmod+retry path."""
        target = tmp_path / "locked"
        target.mkdir()
        captured_onexc = [None]

        def fake_rmtree(path, onexc=None):
            captured_onexc[0] = onexc

        monkeypatch.setattr(shutil, "rmtree", fake_rmtree)
        sc._force_rmtree(target)
        assert captured_onexc[0] is not None

        chmod_calls = []
        func_calls = []
        monkeypatch.setattr(os, "chmod", lambda p, m: chmod_calls.append((p, m)))

        def mock_func(p):
            func_calls.append(p)

        captured_onexc[0](mock_func, "/some/locked/file", OSError("locked"))
        assert len(chmod_calls) == 1
        assert len(func_calls) == 1


# =============================================================================
# _cleanup_local_project_artifacts
# =============================================================================


class TestCleanupLocalProjectArtifacts:
    """Tests for _cleanup_local_project_artifacts() — removes caches and temp files."""

    def test_removes_pycache_directory(self, tmp_path):
        pycache = tmp_path / "__pycache__"
        pycache.mkdir()
        (pycache / "mod.cpython-314.pyc").write_bytes(b"")
        sc._cleanup_local_project_artifacts(tmp_path)
        assert not pycache.exists()

    def test_removes_pyc_file(self, tmp_path):
        pyc = tmp_path / "module.pyc"
        pyc.write_bytes(b"fake pyc")
        sc._cleanup_local_project_artifacts(tmp_path)
        assert not pyc.exists()

    def test_removes_coverage_file(self, tmp_path):
        cov = tmp_path / ".coverage"
        cov.write_text("fake coverage")
        sc._cleanup_local_project_artifacts(tmp_path)
        assert not cov.exists()

    def test_removes_coverage_variant_file(self, tmp_path):
        cov = tmp_path / ".coverage.worker1"
        cov.write_text("fake")
        sc._cleanup_local_project_artifacts(tmp_path)
        assert not cov.exists()

    def test_skips_venv_directory_and_its_contents(self, tmp_path):
        venv_dir = tmp_path / ".venv"
        venv_dir.mkdir()
        pyc_inside = venv_dir / "module.pyc"
        pyc_inside.write_bytes(b"")
        sc._cleanup_local_project_artifacts(tmp_path)
        assert venv_dir.exists()
        assert pyc_inside.exists()

    def test_removes_state_tmp_subdir(self, tmp_path):
        state_tmp = tmp_path / ".state" / "tmp"
        state_tmp.mkdir(parents=True)
        (state_tmp / "pip_work").write_text("temp")
        sc._cleanup_local_project_artifacts(tmp_path)
        assert not state_tmp.exists()

    def test_removes_pytest_cache(self, tmp_path):
        cache = tmp_path / ".pytest_cache"
        cache.mkdir()
        (cache / "v" / "cache").mkdir(parents=True)
        sc._cleanup_local_project_artifacts(tmp_path)
        assert not cache.exists()


# =============================================================================
# _find_latest_python_executable
# =============================================================================


class TestFindLatestPythonExecutable:
    """Tests for _find_latest_python_executable() — picks newest Python."""

    # ── Windows branch ────────────────────────────────────────────────────────

    def test_windows_picks_highest_version_from_launcher(self, monkeypatch):
        monkeypatch.setattr(sc, "IS_WINDOWS", True)
        monkeypatch.setattr(sc, "_list_pythons_windows", lambda: ["3.13", "3.14"])
        monkeypatch.setattr(sys, "version_info", (3, 12, 0, "final", 0))
        cmd, ver = sc._find_latest_python_executable()
        assert ver == "3.14"
        assert cmd == ["py", "-3.14"]

    def test_windows_current_interpreter_included_in_candidates(self, monkeypatch):
        monkeypatch.setattr(sc, "IS_WINDOWS", True)
        monkeypatch.setattr(sc, "_list_pythons_windows", lambda: ["3.13"])
        monkeypatch.setattr(sys, "version_info", (3, 14, 0, "final", 0))
        cmd, ver = sc._find_latest_python_executable()
        assert ver == "3.14"
        assert cmd == [sys.executable]

    # ── POSIX branch ──────────────────────────────────────────────────────────

    def test_posix_finds_python3_14(self, monkeypatch):
        monkeypatch.setattr(sc, "IS_WINDOWS", False)

        def mock_check_call(args, **kwargs):
            if args[0] == "python3.14":
                return 0
            raise FileNotFoundError(f"{args[0]} not found")

        monkeypatch.setattr(subprocess, "check_call", mock_check_call)
        cmd, ver = sc._find_latest_python_executable()
        assert cmd == ["python3.14"]
        assert ver == "3.14"

    def test_posix_falls_back_to_python3(self, monkeypatch):
        monkeypatch.setattr(sc, "IS_WINDOWS", False)

        def mock_check_call(args, **kwargs):
            if args[0] == "python3":
                return 0
            raise FileNotFoundError(f"{args[0]} not found")

        def mock_check_output(args, **kwargs):
            return "3.11\n"

        monkeypatch.setattr(subprocess, "check_call", mock_check_call)
        monkeypatch.setattr(subprocess, "check_output", mock_check_output)
        cmd, ver = sc._find_latest_python_executable()
        assert cmd == ["python3"]
        assert ver == "3.11"

    def test_posix_all_fail_calls_sys_exit(self, monkeypatch):
        monkeypatch.setattr(sc, "IS_WINDOWS", False)
        monkeypatch.setattr(
            subprocess, "check_call", lambda args, **kw: (_ for _ in ()).throw(FileNotFoundError("not found"))
        )
        with pytest.raises(SystemExit) as exc_info:
            sc._find_latest_python_executable()
        assert exc_info.value.code == 1


# =============================================================================
# _relaunch_under_latest_python
# =============================================================================


class TestRelaunchUnderLatestPython:
    """Tests for _relaunch_under_latest_python() — re-execs under newest Python."""

    def test_same_version_does_not_call_execvp(self, monkeypatch):
        monkeypatch.setattr(sys, "version_info", (3, 14, 0, "final", 0))
        monkeypatch.setattr(sc, "_find_latest_python_executable", lambda: (["python3.14"], "3.14"))
        execvp_calls = []
        monkeypatch.setattr(os, "execvp", lambda cmd, args: execvp_calls.append((cmd, args)))
        sc._relaunch_under_latest_python()
        assert execvp_calls == []

    def test_different_version_calls_execvp_with_correct_args(self, monkeypatch):
        monkeypatch.setattr(sys, "version_info", (3, 13, 0, "final", 0))
        monkeypatch.setattr(sc, "_find_latest_python_executable", lambda: (["python3.14"], "3.14"))
        monkeypatch.setattr(sys, "argv", ["setup_client.py", "--verbose"])
        execvp_calls = []
        monkeypatch.setattr(os, "execvp", lambda cmd, args: execvp_calls.append((cmd, args)))
        sc._relaunch_under_latest_python()
        assert len(execvp_calls) == 1
        assert execvp_calls[0][0] == "python3.14"
        assert "--verbose" in execvp_calls[0][1]


# =============================================================================
# _check_internet
# =============================================================================


class TestCheckInternet:
    """Tests for _check_internet() — connectivity probe via raw socket."""

    def test_returns_true_on_successful_connect(self, monkeypatch):
        mock_sock = MagicMock()
        mock_sock.connect.return_value = None
        monkeypatch.setattr(socket, "socket", lambda *a, **kw: mock_sock)
        assert sc._check_internet("8.8.8.8", 53, 1.0) is True

    def test_returns_false_on_socket_error(self, monkeypatch):
        mock_sock = MagicMock()
        mock_sock.connect.side_effect = socket.error("connection refused")
        monkeypatch.setattr(socket, "socket", lambda *a, **kw: mock_sock)
        assert sc._check_internet("8.8.8.8", 53, 1.0) is False

    def test_socket_close_called_on_success(self, monkeypatch):
        mock_sock = MagicMock()
        mock_sock.connect.return_value = None
        monkeypatch.setattr(socket, "socket", lambda *a, **kw: mock_sock)
        sc._check_internet()
        mock_sock.close.assert_called_once()

    def test_socket_close_called_on_failure(self, monkeypatch):
        mock_sock = MagicMock()
        mock_sock.connect.side_effect = socket.error("refused")
        monkeypatch.setattr(socket, "socket", lambda *a, **kw: mock_sock)
        sc._check_internet()
        mock_sock.close.assert_called_once()


# =============================================================================
# _wait_for_endpoint_ready
# =============================================================================


class TestWaitForEndpointReady:
    """Tests for _wait_for_endpoint_ready() — polls endpoint until reachable or timeout."""

    def test_returns_true_immediately_if_reachable(self, monkeypatch):
        monkeypatch.setattr(sc, "_is_endpoint_reachable", lambda ep, **kw: True)
        monkeypatch.setattr(time, "sleep", lambda s: None)
        monkeypatch.setattr(time, "time", lambda: 100.0)
        assert sc._wait_for_endpoint_ready("opc.tcp://localhost:40451", timeout_seconds=30.0) is True

    def test_returns_false_after_timeout(self, monkeypatch):
        monkeypatch.setattr(sc, "_is_endpoint_reachable", lambda ep, **kw: False)
        monkeypatch.setattr(time, "sleep", lambda s: None)
        # deadline = 100.0 + 1.0 = 101.0; first loop at 100.0, second at 102.0 (exits)
        time_seq = [100.0, 100.0, 102.0, 102.0]
        idx = [0]

        def fake_time():
            v = time_seq[min(idx[0], len(time_seq) - 1)]
            idx[0] += 1
            return v

        monkeypatch.setattr(time, "time", fake_time)
        assert sc._wait_for_endpoint_ready("opc.tcp://localhost:40451", timeout_seconds=1.0) is False

    def test_returns_true_on_second_poll(self, monkeypatch):
        call_count = [0]

        def fake_reachable(ep, **kw):
            call_count[0] += 1
            return call_count[0] >= 2

        monkeypatch.setattr(sc, "_is_endpoint_reachable", fake_reachable)
        monkeypatch.setattr(time, "sleep", lambda s: None)
        monkeypatch.setattr(time, "time", lambda: 100.0)  # never expire
        assert sc._wait_for_endpoint_ready("opc.tcp://localhost:40451", timeout_seconds=30.0) is True
        assert call_count[0] == 2


# =============================================================================
# _get_environment_age_days
# =============================================================================


class TestGetEnvironmentAgeDays:
    """Tests for _get_environment_age_days() — venv mtime → age in days."""

    def test_returns_correct_age_when_venv_exists(self, fs, monkeypatch):
        venv_path = Path("/fake/.venv")
        venv_path.mkdir(parents=True)
        monkeypatch.setattr(sc, "VENV_DIR", venv_path)
        one_day_secs = 86400.0
        monkeypatch.setattr(time, "time", lambda: 2 * one_day_secs)
        monkeypatch.setattr(os.path, "getmtime", lambda p: one_day_secs)
        result = sc._get_environment_age_days()
        assert result is not None
        assert 0.99 < result < 1.01

    def test_returns_none_when_venv_missing(self, fs, monkeypatch):
        monkeypatch.setattr(sc, "VENV_DIR", Path("/fake/.venv_nonexistent"))
        assert sc._get_environment_age_days() is None

    def test_returns_none_and_warns_when_getmtime_raises(self, fs, monkeypatch, caplog):
        venv_path = Path("/fake/.venv")
        venv_path.mkdir(parents=True)
        monkeypatch.setattr(sc, "VENV_DIR", venv_path)

        def raise_oserror(p):
            raise OSError("permission denied")

        monkeypatch.setattr(os.path, "getmtime", raise_oserror)
        with caplog.at_level(logging.WARNING, logger="setup_client"):
            result = sc._get_environment_age_days()
        assert result is None
        assert any("environment age" in r.message.lower() for r in caplog.records)


# =============================================================================
# _resolve_python_executable
# =============================================================================


class TestResolvePythonExecutable:
    """Tests for _resolve_python_executable() — asks Python to print its own path."""

    def test_returns_stripped_executable_path(self, monkeypatch):
        monkeypatch.setattr(subprocess, "check_output", lambda args, **kw: "/usr/bin/python3.14\n")
        result = sc._resolve_python_executable(["python3.14"])
        assert result == "/usr/bin/python3.14"

    def test_subprocess_failure_calls_sys_exit(self, monkeypatch):
        def fail(*a, **kw):
            raise subprocess.CalledProcessError(1, "python3.14")

        monkeypatch.setattr(subprocess, "check_output", fail)
        with pytest.raises(SystemExit) as exc_info:
            sc._resolve_python_executable(["python3.14"])
        assert exc_info.value.code == 1

    def test_empty_output_calls_sys_exit(self, monkeypatch):
        monkeypatch.setattr(subprocess, "check_output", lambda *a, **kw: "   \n")
        with pytest.raises(SystemExit) as exc_info:
            sc._resolve_python_executable(["python3.14"])
        assert exc_info.value.code == 1


# =============================================================================
# _create_virtualenv
# =============================================================================


class TestCreateVirtualenv:
    """Tests for _create_virtualenv() — creates .venv and installs pip."""

    def test_success_calls_venv_and_ensurepip(self, tmp_path, monkeypatch):
        venv_path = tmp_path / ".venv"
        state_path = tmp_path / ".state"
        monkeypatch.setattr(sc, "VENV_DIR", venv_path)
        monkeypatch.setattr(sc, "STATE_DIR", state_path)
        monkeypatch.setattr(sc, "_resolve_python_executable", lambda cmd: "/usr/bin/python3.14")
        calls = []
        monkeypatch.setattr(subprocess, "check_call", lambda args, **kw: calls.append(list(args)))
        sc._create_virtualenv(["python3.14"])
        venv_calls = [c for c in calls if "venv" in c and "--without-pip" in c]
        ensurepip_calls = [c for c in calls if "ensurepip" in c]
        assert len(venv_calls) == 1
        assert len(ensurepip_calls) == 1

    def test_ensurepip_failure_triggers_fallback_pip(self, tmp_path, monkeypatch):
        venv_path = tmp_path / ".venv"
        state_path = tmp_path / ".state"
        monkeypatch.setattr(sc, "VENV_DIR", venv_path)
        monkeypatch.setattr(sc, "STATE_DIR", state_path)
        monkeypatch.setattr(sc, "_resolve_python_executable", lambda cmd: "/usr/bin/python3.14")
        calls = []

        def controlled_check_call(args, **kw):
            calls.append(list(args))
            if "ensurepip" in args:
                raise OSError("ensurepip not available")

        monkeypatch.setattr(subprocess, "check_call", controlled_check_call)
        sc._create_virtualenv(["python3.14"])
        fallback_calls = [c for c in calls if "--python" in c and "pip" in c]
        assert len(fallback_calls) == 1

    def test_venv_creation_failure_calls_sys_exit(self, tmp_path, monkeypatch):
        venv_path = tmp_path / ".venv"
        state_path = tmp_path / ".state"
        monkeypatch.setattr(sc, "VENV_DIR", venv_path)
        monkeypatch.setattr(sc, "STATE_DIR", state_path)
        monkeypatch.setattr(sc, "_resolve_python_executable", lambda cmd: "/usr/bin/python3.14")

        def failing_check_call(args, **kw):
            if "venv" in args:
                raise subprocess.CalledProcessError(1, args)

        monkeypatch.setattr(subprocess, "check_call", failing_check_call)
        with pytest.raises(SystemExit) as exc_info:
            sc._create_virtualenv(["python3.14"])
        assert exc_info.value.code == 1

    def test_existing_venv_dir_is_removed_first(self, tmp_path, monkeypatch):
        venv_path = tmp_path / ".venv"
        venv_path.mkdir()
        state_path = tmp_path / ".state"
        monkeypatch.setattr(sc, "VENV_DIR", venv_path)
        monkeypatch.setattr(sc, "STATE_DIR", state_path)
        monkeypatch.setattr(sc, "_resolve_python_executable", lambda cmd: "/usr/bin/python3.14")
        rmtree_calls = []

        def mock_rmtree(path, onexc=None, ignore_errors=False):
            rmtree_calls.append(path)

        monkeypatch.setattr(shutil, "rmtree", mock_rmtree)
        monkeypatch.setattr(subprocess, "check_call", lambda args, **kw: None)
        sc._create_virtualenv(["python3.14"])
        assert venv_path in rmtree_calls


# =============================================================================
# _install_python_packages
# =============================================================================


class TestInstallPythonPackages:
    """Tests for _install_python_packages() — pip installs into .venv."""

    def test_missing_requirements_txt_calls_sys_exit(self, fs, monkeypatch):
        rundir = Path("/fake/rundir")
        rundir.mkdir(parents=True)
        monkeypatch.chdir(rundir)
        monkeypatch.setattr(sc, "VENV_DIR", rundir / ".venv")
        with pytest.raises(SystemExit) as exc_info:
            sc._install_python_packages()
        assert exc_info.value.code == 1

    def test_success_installs_all_packages(self, fs, monkeypatch):
        rundir = Path("/fake/rundir")
        rundir.mkdir(parents=True)
        monkeypatch.chdir(rundir)
        (rundir / "requirements.txt").write_text("requests\n")
        monkeypatch.setattr(sc, "VENV_DIR", rundir / ".venv")
        calls = []
        monkeypatch.setattr(subprocess, "check_call", lambda args, **kw: calls.append(list(args)))
        monkeypatch.setattr(subprocess, "check_output", lambda args, **kw: "1.2.0\n")
        sc._install_python_packages()
        assert any("requirements.txt" in str(c) for c in calls)
        assert any("asyncua" in str(c) for c in calls)

    def test_crypto_upgrade_exception_does_not_exit(self, fs, monkeypatch):
        rundir = Path("/fake/rundir")
        rundir.mkdir(parents=True)
        monkeypatch.chdir(rundir)
        (rundir / "requirements.txt").write_text("requests\n")
        monkeypatch.setattr(sc, "VENV_DIR", rundir / ".venv")

        def selective_check_call(args, **kw):
            if "cryptography" in args or "pyOpenSSL" in args:
                raise subprocess.CalledProcessError(1, args)

        monkeypatch.setattr(subprocess, "check_call", selective_check_call)
        monkeypatch.setattr(subprocess, "check_output", lambda args, **kw: "1.2.0\n")
        sc._install_python_packages()  # must not raise

    def test_asyncua_too_old_calls_sys_exit(self, fs, monkeypatch):
        rundir = Path("/fake/rundir")
        rundir.mkdir(parents=True)
        monkeypatch.chdir(rundir)
        (rundir / "requirements.txt").write_text("requests\n")
        monkeypatch.setattr(sc, "VENV_DIR", rundir / ".venv")
        monkeypatch.setattr(subprocess, "check_call", lambda args, **kw: None)
        monkeypatch.setattr(subprocess, "check_output", lambda args, **kw: "1.1.0\n")
        with pytest.raises(SystemExit) as exc_info:
            sc._install_python_packages()
        assert exc_info.value.code == 1

    def test_asyncua_version_check_failure_logs_warning_no_exit(self, fs, monkeypatch, caplog):
        rundir = Path("/fake/rundir")
        rundir.mkdir(parents=True)
        monkeypatch.chdir(rundir)
        (rundir / "requirements.txt").write_text("requests\n")
        monkeypatch.setattr(sc, "VENV_DIR", rundir / ".venv")
        monkeypatch.setattr(subprocess, "check_call", lambda args, **kw: None)

        def failing_output(args, **kw):
            raise subprocess.CalledProcessError(1, args)

        monkeypatch.setattr(subprocess, "check_output", failing_output)
        with caplog.at_level(logging.WARNING, logger="setup_client"):
            sc._install_python_packages()  # must not raise
        assert any("asyncua" in r.message.lower() for r in caplog.records)


# =============================================================================
# main
# =============================================================================


class TestMain:
    """Tests for main() — argument parsing and setup orchestration flows."""

    def _mock_basics(self, monkeypatch):
        """Patch all main() side-effectful calls to safe no-ops."""
        monkeypatch.setattr(sc, "_relaunch_under_latest_python", lambda: None)
        monkeypatch.setattr(sc, "_require_python_314_or_newer", lambda *a: None)
        monkeypatch.setattr(sc, "_warn_if_untested_python", lambda *a: None)
        monkeypatch.setattr(sc, "_find_latest_python_executable", lambda: (["python3.14"], "3.14"))
        monkeypatch.setattr(sc, "_remove_stale_venvs", lambda *a: None)
        monkeypatch.setattr(sc, "_cleanup_local_project_artifacts", lambda *a: None)
        monkeypatch.setattr(sc, "_is_runtime_ready", lambda: False)
        monkeypatch.setattr(sc, "_validate_url_or_default", lambda url: "opc.tcp://localhost:40451")
        monkeypatch.setattr(sc, "_ensure_opc_server_running", lambda *a, **kw: True)
        monkeypatch.setattr(sc, "_run_client", lambda *a, **kw: None)
        monkeypatch.setattr(sc, "_check_internet", lambda: True)
        monkeypatch.setattr(sc, "_create_virtualenv", lambda cmd: None)
        monkeypatch.setattr(sc, "_install_python_packages", lambda: None)
        monkeypatch.setattr(sc, "_update_setup_timestamp", lambda: None)
        monkeypatch.setattr(shutil, "rmtree", lambda *a, **kw: None)

    def test_clean_with_venv_present_calls_rmtree(self, fs, monkeypatch):
        venv_path = Path("/fake/.venv")
        venv_path.mkdir(parents=True)
        monkeypatch.setattr(sc, "VENV_DIR", venv_path)
        self._mock_basics(monkeypatch)
        rmtree_calls = []
        monkeypatch.setattr(shutil, "rmtree", lambda p: rmtree_calls.append(p))
        monkeypatch.setattr(sys, "argv", ["setup_client.py", "--clean"])
        sc.main()
        assert venv_path in rmtree_calls

    def test_clean_without_venv_logs_message(self, fs, monkeypatch, caplog):
        monkeypatch.setattr(sc, "VENV_DIR", Path("/fake/.venv_missing"))
        self._mock_basics(monkeypatch)
        monkeypatch.setattr(sys, "argv", ["setup_client.py", "--clean"])
        with caplog.at_level(logging.INFO, logger="setup_client"):
            sc.main()
        assert any("No virtual environment to clean" in r.message for r in caplog.records)

    def test_fast_path_when_runtime_ready(self, monkeypatch):
        self._mock_basics(monkeypatch)
        monkeypatch.setattr(sc, "_is_runtime_ready", lambda: True)
        run_calls = []
        monkeypatch.setattr(sc, "_run_client", lambda *a, **kw: run_calls.append(a))
        monkeypatch.setattr(sys, "argv", ["setup_client.py"])
        sc.main()
        assert len(run_calls) == 1

    def test_force_full_skips_fast_path_even_when_runtime_ready(self, monkeypatch):
        self._mock_basics(monkeypatch)
        monkeypatch.setattr(sc, "_is_runtime_ready", lambda: True)
        create_calls = []
        monkeypatch.setattr(sc, "_create_virtualenv", lambda cmd: create_calls.append(cmd))
        monkeypatch.setattr(sys, "argv", ["setup_client.py", "--force_full"])
        sc.main()
        assert len(create_calls) == 1

    def test_full_setup_with_internet_calls_create_and_install(self, monkeypatch):
        self._mock_basics(monkeypatch)
        create_calls = []
        install_calls = []
        stamp_calls = []
        monkeypatch.setattr(sc, "_create_virtualenv", lambda cmd: create_calls.append(cmd))
        monkeypatch.setattr(sc, "_install_python_packages", lambda: install_calls.append(1))
        monkeypatch.setattr(sc, "_update_setup_timestamp", lambda: stamp_calls.append(1))
        monkeypatch.setattr(sys, "argv", ["setup_client.py"])
        sc.main()
        assert len(create_calls) == 1
        assert len(install_calls) == 1
        assert len(stamp_calls) == 1

    def test_full_setup_no_internet_calls_sys_exit(self, monkeypatch):
        self._mock_basics(monkeypatch)
        monkeypatch.setattr(sc, "_check_internet", lambda: False)
        monkeypatch.setattr(sys, "argv", ["setup_client.py"])
        with pytest.raises(SystemExit) as exc_info:
            sc.main()
        assert exc_info.value.code == 1
