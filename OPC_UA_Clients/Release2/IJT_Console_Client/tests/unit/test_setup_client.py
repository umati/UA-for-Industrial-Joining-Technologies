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
import setup_client as sc


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
        monkeypatch.setattr(socket, "socket", lambda *a, **kw: mock_sock)
        assert sc._is_endpoint_reachable("opc.tcp://localhost:40451") is True

    def test_returns_false_when_connect_ex_nonzero(self, monkeypatch):
        mock_sock = self._make_mock_socket(111)
        monkeypatch.setattr(socket, "socket", lambda *a, **kw: mock_sock)
        assert sc._is_endpoint_reachable("opc.tcp://localhost:40451") is False

    def test_uses_parse_endpoint_host_port(self, monkeypatch):
        captured = []
        mock_sock = self._make_mock_socket(0)

        def fake_connect_ex(addr):
            captured.append(addr)
            return 0

        mock_sock.connect_ex.side_effect = fake_connect_ex
        monkeypatch.setattr(socket, "socket", lambda *a, **kw: mock_sock)
        sc._is_endpoint_reachable("opc.tcp://myhost:9999")
        assert captured == [("myhost", 9999)]

    def test_socket_close_called_on_success(self, monkeypatch):
        mock_sock = self._make_mock_socket(0)
        monkeypatch.setattr(socket, "socket", lambda *a, **kw: mock_sock)
        sc._is_endpoint_reachable("opc.tcp://localhost:40451")
        mock_sock.close.assert_called_once()

    def test_socket_close_called_on_failure(self, monkeypatch):
        mock_sock = self._make_mock_socket(111)
        monkeypatch.setattr(socket, "socket", lambda *a, **kw: mock_sock)
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
        monkeypatch.setattr(subprocess, "check_output", lambda *a, **kw: output)
        assert sc._is_simulator_process_running() is True

    def test_returns_false_when_exe_not_in_tasklist(self, monkeypatch):
        monkeypatch.setattr(sc, "IS_WINDOWS", True)
        output = "Image Name                     PID\nnotepad.exe    5678\n"
        monkeypatch.setattr(subprocess, "check_output", lambda *a, **kw: output)
        assert sc._is_simulator_process_running() is False

    def test_returns_false_when_tasklist_raises(self, monkeypatch):
        monkeypatch.setattr(sc, "IS_WINDOWS", True)

        def _fail(*a, **kw):
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
        monkeypatch.setattr(sc, "_wait_for_endpoint_ready", lambda _ep, **kw: True)
        assert sc._ensure_opc_server_running("opc.tcp://localhost:40451", context="test", allow_launch=True) is True

    def test_docker_skips_launch_returns_false(self, monkeypatch):
        call_count = [0]

        def fake_wait(_ep, **kw):
            call_count[0] += 1
            return False

        monkeypatch.setattr(sc, "_wait_for_endpoint_ready", fake_wait)
        monkeypatch.setattr(sc, "IS_DOCKER", True)
        result = sc._ensure_opc_server_running("opc.tcp://localhost:40451", context="docker", allow_launch=True)
        assert result is False

    def test_allow_launch_false_skips_popen(self, monkeypatch):
        popen_calls = []
        exe = Path("/fake") / sc.SIMULATOR_EXE_NAME
        monkeypatch.setattr(sc, "_wait_for_endpoint_ready", lambda _ep, **kw: False)
        monkeypatch.setattr(sc, "IS_DOCKER", False)
        monkeypatch.setattr(sc, "_find_simulator_executable", lambda: exe)
        monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: popen_calls.append(a[0]))
        result = sc._ensure_opc_server_running("opc.tcp://localhost:40451", context="no-launch", allow_launch=False)
        assert result is False
        assert popen_calls == []

    def test_auto_launch_succeeds(self, monkeypatch):
        exe = Path("/fake") / sc.SIMULATOR_EXE_NAME
        popen_calls = []
        wait_count = [0]

        def fake_wait(_ep, **kw):
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
        monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: (popen_calls.append(a[0]), mock_proc)[1])

        result = sc._ensure_opc_server_running("opc.tcp://localhost:40451", context="auto-launch", allow_launch=True)
        assert result is True
        assert len(popen_calls) == 1

    def test_auto_launch_fails_when_endpoint_not_ready_after_launch(self, monkeypatch):
        exe = Path("/fake") / sc.SIMULATOR_EXE_NAME
        mock_proc = MagicMock()
        mock_proc.pid = 9999
        monkeypatch.setattr(sc, "_wait_for_endpoint_ready", lambda _ep, **kw: False)
        monkeypatch.setattr(sc, "IS_DOCKER", False)
        monkeypatch.setattr(sc, "_extract_simulator_zip_if_needed", lambda: None)
        monkeypatch.setattr(sc, "_find_simulator_executable", lambda: exe)
        monkeypatch.setattr(sc, "_is_simulator_process_running", lambda: False)
        monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: mock_proc)
        result = sc._ensure_opc_server_running("opc.tcp://localhost:40451", context="launch-timeout", allow_launch=True)
        assert result is False

    def test_no_exe_found_returns_false(self, monkeypatch):
        monkeypatch.setattr(sc, "_wait_for_endpoint_ready", lambda _ep, **kw: False)
        monkeypatch.setattr(sc, "IS_DOCKER", False)
        monkeypatch.setattr(sc, "_extract_simulator_zip_if_needed", lambda: None)
        monkeypatch.setattr(sc, "_find_simulator_executable", lambda: None)
        result = sc._ensure_opc_server_running("opc.tcp://localhost:40451", context="no-exe", allow_launch=True)
        assert result is False

    def test_popen_oserror_returns_false_with_warning(self, monkeypatch, caplog):
        exe = Path("/fake") / sc.SIMULATOR_EXE_NAME

        def _bad_popen(*a, **kw):
            raise OSError("Access denied")

        monkeypatch.setattr(sc, "_wait_for_endpoint_ready", lambda _ep, **kw: False)
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

        def fake_wait(_ep, **kw):
            wait_count[0] += 1
            return wait_count[0] >= 2

        monkeypatch.setattr(sc, "_wait_for_endpoint_ready", fake_wait)
        monkeypatch.setattr(sc, "IS_DOCKER", False)
        monkeypatch.setattr(sc, "_extract_simulator_zip_if_needed", lambda: None)
        monkeypatch.setattr(sc, "_find_simulator_executable", lambda: exe)
        monkeypatch.setattr(sc, "_is_simulator_process_running", lambda: True)
        monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: popen_calls.append(1))
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
            monkeypatch.setattr(sc, "_run_command", lambda cmd, **kw: None)
        else:

            def _fail(*a, **kw):
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
        monkeypatch.setattr(sc, "_run_command", lambda cmd, **kw: None)
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
        monkeypatch.setattr(subprocess, "check_output", lambda *a, **kw: output)
        versions = sc._list_pythons_windows()
        assert "3.14" in versions
        assert "3.13" in versions

    def test_parses_version_from_dash_prefix(self, monkeypatch):
        output = " -3.14 *          Python 3.14.0\n"
        monkeypatch.setattr(subprocess, "check_output", lambda *a, **kw: output)
        versions = sc._list_pythons_windows()
        assert "3.14" in versions

    def test_returns_empty_list_when_py_fails(self, monkeypatch):
        def _fail(*a, **kw):
            raise FileNotFoundError("py not found")

        monkeypatch.setattr(subprocess, "check_output", _fail)
        assert sc._list_pythons_windows() == []

    def test_ignores_non_version_lines(self, monkeypatch):
        output = "Installed Pythons found by py Launcher for Windows\n -V:3.14 *\n"
        monkeypatch.setattr(subprocess, "check_output", lambda *a, **kw: output)
        versions = sc._list_pythons_windows()
        # Should only have 3.14, not the header line
        assert versions == ["3.14"]

    def test_ignores_three_part_versions(self, monkeypatch):
        output = " -V:3.14.1        Python 3.14.1\n"
        monkeypatch.setattr(subprocess, "check_output", lambda *a, **kw: output)
        versions = sc._list_pythons_windows()
        # 3.14.1 has two dots, so count(".") != 1 — should be excluded
        assert "3.14.1" not in versions

    def test_returns_empty_on_empty_output(self, monkeypatch):
        monkeypatch.setattr(subprocess, "check_output", lambda *a, **kw: "")
        assert sc._list_pythons_windows() == []

