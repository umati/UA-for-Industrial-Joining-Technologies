from __future__ import annotations

import importlib.util
import logging
import subprocess
import sys
from pathlib import Path


def _load_root_runner():
    root = Path(__file__).resolve().parents[1]
    runner_path = root / "run_all_tests.py"
    spec = importlib.util.spec_from_file_location("ijt_root_run_all_tests", runner_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_runner = _load_root_runner()


def setup_function() -> None:
    _runner._server_smoke_requirements_ready = False


def teardown_function() -> None:
    _runner._server_smoke_requirements_ready = False


def _load_runner_at(relative_path: str, module_name: str):
    root = Path(__file__).resolve().parents[1]
    runner_path = root / relative_path
    spec = importlib.util.spec_from_file_location(module_name, runner_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_RUNNER_PATHS = [
    ("OPC_UA_Clients/Release1/IJT_Node_Client/run_all_tests.py", "ijt_node_runner"),
    ("OPC_UA_Clients/Release2/IJT_CSharp_Client/run_all_tests.py", "ijt_csharp_runner"),
    ("OPC_UA_Clients/Release2/IJT_Console_Client/run_all_tests.py", "ijt_console_runner"),
    ("OPC_UA_Clients/Release2/IJT_Test_Client/run_all_tests.py", "ijt_test_client_runner"),
    ("OPC_UA_Clients/Release2/IJT_Web_Client/run_all_tests.py", "ijt_web_client_runner"),
    ("OPC_UA_Servers/Release2/run_all_tests.py", "ijt_server_runner"),
]


def test_zizmor_rc13_medium_findings_is_pass() -> None:
    result = _runner._parse_zizmor_output(
        '[{"determinations":{"severity":"Medium"}},{"determinations":{"severity":"Medium"}}]',
        13,
    )
    assert result.status == "PASS"
    assert result.detail == "2 finding(s), none high/critical"


def test_zizmor_rc13_high_finding_is_fail() -> None:
    result = _runner._parse_zizmor_output('[{"determinations":{"severity":"High"}}]', 13)
    assert result.status == "FAIL"
    assert result.detail == "1 high/critical finding(s)"


def test_zizmor_rc1_tool_error_is_skip() -> None:
    result = _runner._parse_zizmor_output("", 1)
    assert result.status == "SKIP"
    assert result.detail == "zizmor error — skipping"


def test_zizmor_non_list_json_is_skip() -> None:
    non_list_payload = '{"results":[{"determinations":{"severity":"High"}}]}'
    result = _runner._parse_zizmor_output(non_list_payload, 13)
    assert result.status == "SKIP"
    assert result.detail == "Could not parse output — zizmor version mismatch"


def test_zizmor_empty_stdout_with_findings_exit_is_zero_findings_pass() -> None:
    result = _runner._parse_zizmor_output("", 13)
    assert result.status == "PASS"
    assert result.detail == "0 finding(s), none high/critical"


def test_zizmor_clean_run_is_zero_findings_pass() -> None:
    result = _runner._parse_zizmor_output("", 0)
    assert result.status == "PASS"
    assert result.detail == "0 finding(s), none high/critical"


def test_wait_for_port_missing_ok_logs_non_error(caplog) -> None:
    with caplog.at_level(logging.INFO, logger="run_all_tests"):
        ready = _runner._wait_for_port(65000, timeout=0, missing_ok=True)

    assert ready is False
    assert "No existing OPC UA server detected" in caplog.text
    assert "Server did not become ready" not in caplog.text


def test_server_linux_package_smoke_is_default_phase2_suite() -> None:
    assert "server-linux-package-smoke" in _runner.PHASE2_SUITES
    assert (
        _runner.PHASE2_SUITES["server-linux-package-smoke"]
        is _runner._suite_server_linux_package_smoke
    )


def test_webclient_live_suites_are_split_by_test_type(monkeypatch) -> None:
    calls: list[dict] = []

    def _fake_delegate_to_runner(**kwargs):
        calls.append(kwargs)
        return _runner.SuiteResult(kwargs["name"], True, 0.0)

    monkeypatch.setattr(_runner, "_delegate_to_runner", _fake_delegate_to_runner)

    results = [
        _runner._suite_webclient_live_python_opcua(),
        _runner._suite_webclient_live_python_backend(),
        _runner._suite_webclient_live_python_lifecycle(),
        _runner._suite_webclient_live_e2e_smoke(),
        _runner._suite_webclient_live_e2e_features(),
        _runner._suite_webclient_live_e2e_regression(),
        _runner._suite_webclient_docker_smoke(),
    ]

    assert all(result.ok for result in results)
    expected_suites = {
        "webclient-live-python-opcua",
        "webclient-live-python-backend",
        "webclient-live-python-lifecycle",
        "webclient-live-e2e-smoke",
        "webclient-live-e2e-features",
        "webclient-live-e2e-regression",
        "webclient-docker-smoke",
    }
    assert expected_suites <= set(_runner.PHASE2_SUITES)
    assert "webclient-live" not in _runner.PHASE2_SUITES
    assert [call["phase_args"] for call in calls] == [
        ["--python-opcua-only"],
        ["--python-backend-only"],
        ["--python-lifecycle-only"],
        ["--playwright-smoke-only"],
        ["--playwright-features-only"],
        ["--playwright-regression-only"],
        ["--docker-only"],
    ]
    assert calls[0]["extra_env"]["OPCUA_SERVER_PORT"] == str(_runner.OPCUA_SERVER_PORT_WEB_CLIENT)
    assert calls[0]["extra_env"]["IJT_WEB_TEST_RESULTS_DIR"] == str(
        _runner.WEB_CLIENT_RESULTS_DIR / "python-opcua"
    )
    assert (
        calls[1]["extra_env"]["WS_TEST_URL"]
        == f"ws://localhost:{_runner.WEB_CLIENT_WS_PORT_BACKEND}"
    )
    assert calls[3]["extra_env"]["IJT_WEB_TEST_RESULTS_DIR"] == str(
        _runner.WEB_CLIENT_RESULTS_DIR / "e2e-smoke"
    )
    assert calls[4]["extra_env"]["UI_TEST_PORT"] == str(_runner.WEB_CLIENT_UI_PORT_E2E_FEATURES)
    assert calls[4]["extra_env"]["IJT_WEB_TEST_RESULTS_DIR"] == str(
        _runner.WEB_CLIENT_RESULTS_DIR / "e2e-features"
    )
    assert calls[4]["extra_env"]["IJT_PLAYWRIGHT_FEATURE_WORKERS"] == str(
        _runner.WEB_CLIENT_E2E_FEATURE_WORKERS
    )
    assert calls[6]["extra_env"]["IJT_WEB_TEST_RESULTS_DIR"] == str(
        _runner.WEB_CLIENT_RESULTS_DIR / "docker-smoke"
    )
    assert calls[6]["timeout"] == _runner.DOCKER_BUILD_TIMEOUT + 180


def test_delegate_to_runner_reports_child_failure(monkeypatch, capsys) -> None:
    def _fake_run_captured(*_args, **_kwargs):
        return 1, "child runner failed\n"

    monkeypatch.setattr(_runner, "_run_captured", _fake_run_captured)

    result = _runner._delegate_to_runner(
        name="webclient-live-e2e-features",
        runner_dir=Path(__file__).resolve().parents[1],
        phase_args=["--playwright-features-only"],
        label="webclient runner (e2e-features)",
    )
    rc = _runner._print_summary([result], total_time=1.0)

    output = capsys.readouterr().out
    assert result.ok is False
    assert result.skipped is False
    assert rc == 1
    assert "webclient-live-e2e-features" in output
    assert "FAIL" in output
    assert "ONE OR MORE SUITES FAILED" in output


def test_server_linux_package_smoke_skips_without_docker(monkeypatch) -> None:
    monkeypatch.setattr(_runner, "_find_cmd", lambda names: None)

    result = _runner._suite_server_linux_package_smoke()

    assert result.ok
    assert result.skipped
    assert result.notes == ["docker not in PATH"]


def test_server_linux_package_smoke_fails_when_package_missing(monkeypatch) -> None:
    monkeypatch.setattr(_runner, "_find_cmd", lambda names: "docker")
    monkeypatch.setattr(_runner, "_docker_daemon_running", lambda docker: True)
    monkeypatch.setattr(_runner, "_LINUX_PACKAGE_ZIP", Path("missing.zip"))

    result = _runner._suite_server_linux_package_smoke()

    assert not result.ok
    assert not result.skipped
    assert result.notes == ["missing package: missing.zip"]


def test_server_linux_package_smoke_uses_dedicated_docker_port(monkeypatch) -> None:
    class _ExistingPath:
        def __init__(self, name: str) -> None:
            self.name = name

        def exists(self) -> bool:
            return True

        def __str__(self) -> str:
            return self.name

    package = _ExistingPath("OPC_UA_IJT_Server_Simulator_Linux.zip")
    smoke_test = _ExistingPath("smoke_test.py")
    commands: list[list[str]] = []
    timeouts: dict[str, int] = {}
    waited_ports: list[int] = []

    class _Completed:
        returncode = 0

    def _fake_subprocess_run(*args, **kwargs):
        return _Completed()

    def _fake_run_captured(cmd, **kwargs):
        commands.append(cmd)
        label = kwargs.get("label")
        if label:
            timeouts[label] = kwargs.get("timeout", _runner.SUITE_TIMEOUT)
        return 0, "ok"

    def _fake_wait_for_port(port, timeout=90, missing_ok=False):
        waited_ports.append(port)
        return True

    monkeypatch.setattr(_runner, "_find_cmd", lambda names: "docker")
    monkeypatch.setattr(_runner, "_docker_daemon_running", lambda docker: True)
    monkeypatch.setattr(_runner, "_LINUX_PACKAGE_ZIP", package)
    monkeypatch.setattr(_runner, "SMOKE_TEST", smoke_test)
    monkeypatch.setattr(_runner, "_current_python", lambda: "python")
    monkeypatch.setattr(_runner, "_run_captured", _fake_run_captured)
    monkeypatch.setattr(_runner, "_wait_for_port", _fake_wait_for_port)
    monkeypatch.setattr(_runner.subprocess, "run", _fake_subprocess_run)

    result = _runner._suite_server_linux_package_smoke()

    assert result.ok
    assert waited_ports == [_runner.OPCUA_SERVER_PORT_SERVER_DOCKER]
    assert timeouts["docker build (Linux package smoke)"] == _runner.DOCKER_BUILD_TIMEOUT
    docker_run = next(cmd for cmd in commands if cmd[:2] == ["docker", "run"])
    assert (
        f"{_runner.OPCUA_SERVER_PORT_SERVER_DOCKER}:{_runner.OPCUA_SERVER_PORT_SERVER_DOCKER}"
    ) in docker_run
    smoke_cmd = next(cmd for cmd in commands if str(smoke_test) in cmd)
    assert f"opc.tcp://localhost:{_runner.OPCUA_SERVER_PORT_SERVER_DOCKER}" in smoke_cmd


def test_all_runner_https_preflights_use_requests_rules_endpoint(monkeypatch) -> None:
    seen: list[tuple[str, float]] = []

    class _Response:
        def raise_for_status(self) -> None:
            return None

    class _Requests:
        @staticmethod
        def get(url: str, timeout: float):
            seen.append((url, timeout))
            return _Response()

    monkeypatch.setitem(sys.modules, "requests", _Requests)

    for relative_path, module_name in _RUNNER_PATHS:
        module = _load_runner_at(relative_path, module_name)
        assert module._is_https_reachable("semgrep.dev")

    assert seen == [("https://semgrep.dev/c/p/default", 5.0)] * len(_RUNNER_PATHS)


def test_all_runner_https_preflights_use_pypi_json_endpoint(monkeypatch) -> None:
    seen: list[tuple[str, float]] = []

    class _Response:
        def raise_for_status(self) -> None:
            return None

    class _Requests:
        @staticmethod
        def get(url: str, timeout: float):
            seen.append((url, timeout))
            return _Response()

    monkeypatch.setitem(sys.modules, "requests", _Requests)

    for relative_path, module_name in _RUNNER_PATHS:
        module = _load_runner_at(relative_path, f"{module_name}_pypi_endpoint")
        assert module._is_https_reachable("pypi.org")

    assert seen == [("https://pypi.org/pypi/pip/json", 5.0)] * len(_RUNNER_PATHS)


def test_all_runner_https_preflights_fail_fast_on_requests_tls_error(monkeypatch) -> None:
    seen: list[str] = []

    class _Requests:
        @staticmethod
        def get(url: str, timeout: float):
            seen.append(url)
            raise RuntimeError("certificate verify failed")

    monkeypatch.setitem(sys.modules, "requests", _Requests)

    for relative_path, module_name in _RUNNER_PATHS:
        module = _load_runner_at(relative_path, f"{module_name}_tls_error")
        assert not module._is_https_reachable("semgrep.dev")

    assert seen == ["https://semgrep.dev/c/p/default"] * len(_RUNNER_PATHS)


def test_node_and_web_npm_install_steps_suppress_funding_and_inline_audit_noise() -> None:
    node = _load_runner_at(
        "OPC_UA_Clients/Release1/IJT_Node_Client/run_all_tests.py",
        "ijt_node_runner_npm_flags",
    )
    web = _load_runner_at(
        "OPC_UA_Clients/Release2/IJT_Web_Client/run_all_tests.py",
        "ijt_web_client_runner_npm_flags",
    )

    for module in (node, web):
        assert "--no-audit" in module._NPM_INSTALL_FLAGS
        assert "--no-fund" in module._NPM_INSTALL_FLAGS


def test_optional_import_typing_guard_passes_current_files() -> None:
    result = _runner._check_optional_import_typing()

    assert result.status == "PASS"
    assert result.detail == "8 file(s) verified"


def test_optional_import_typing_guard_detects_unsuppressed_requests(monkeypatch) -> None:
    class _FakeRunnerPath:
        def exists(self) -> bool:
            return True

        def relative_to(self, root):
            return Path("fake/run_all_tests.py")

        def read_text(self, encoding: str) -> str:
            return "def check():\n    import requests\n"

    monkeypatch.setattr(_runner, "_OPTIONAL_IMPORT_GUARD_PATHS", (_FakeRunnerPath(),))

    result = _runner._check_optional_import_typing()

    assert result.status == "FAIL"
    assert result.detail == "1 optional import typing issue(s)"


def test_optional_import_typing_guard_detects_forward_annotation_reimport(monkeypatch) -> None:
    class _FakeScriptPath:
        def exists(self) -> bool:
            return True

        def relative_to(self, root):
            return Path("fake/make_ci_summary.py")

        def read_text(self, encoding: str) -> str:
            return "yaml: Any\ntry:\n    import yaml\nexcept ImportError:\n    yaml = None\n"

    monkeypatch.setattr(_runner, "_OPTIONAL_IMPORT_GUARD_PATHS", (_FakeScriptPath(),))

    result = _runner._check_optional_import_typing()

    assert result.status == "FAIL"
    assert result.detail == "1 optional import typing issue(s)"


def test_run_capture_forces_child_python_utf8(monkeypatch) -> None:
    captured: dict[str, str] = {}

    class _FakeProc:
        returncode = 0
        pid = 123

        def communicate(self, timeout=None):
            return b"ok", b""

    def _fake_popen(cmd, *, cwd, stdout, stderr, text, env, **kwargs):
        captured.update(env)
        assert stdout is subprocess.PIPE
        assert stderr is subprocess.PIPE
        assert text is False
        return _FakeProc()

    monkeypatch.setattr(_runner.subprocess, "Popen", _fake_popen)

    rc, output = _runner._run_captured(
        [sys.executable, "-c", "print('ok')"],
        cwd=_runner.REPO_ROOT,
    )

    assert rc == 0
    assert "ok" in output
    assert captured["PYTHONIOENCODING"] == "utf-8"
    assert captured["PYTHONUTF8"] == "1"
    assert captured["DOTNET_SKIP_FIRST_TIME_EXPERIENCE"] == "1"
    assert captured["DOTNET_CLI_TELEMETRY_OPTOUT"] == "1"
    assert captured["DOTNET_NOLOGO"] == "1"
    assert captured["DOTNET_ADD_GLOBAL_TOOLS_TO_PATH"] == "0"
    assert captured["DOTNET_GENERATE_ASPNET_CERTIFICATE"] == "false"
    assert Path(captured["npm_config_cache"]).parts[-3:] == ("tmp", "runner-env", "npm-cache")
    assert captured["npm_config_update_notifier"] == "false"
    assert Path(captured["PIP_CACHE_DIR"]).parts[-3:] == ("tmp", "runner-env", "pip-cache")


def test_node_runner_subprocess_env_disables_npm_update_notifier(monkeypatch) -> None:
    module = _load_runner_at(
        "OPC_UA_Clients/Release1/IJT_Node_Client/run_all_tests.py",
        "ijt_node_runner_npm_env",
    )
    captured: dict[str, str] = {}

    class _FakeCompleted:
        returncode = 0
        stdout = "ok"

    def _fake_run(cmd, *, cwd, env, check, stdout=None, text=None):
        captured.update(env)
        assert cwd == str(module._PROJECT_DIR)
        assert check is False
        return _FakeCompleted()

    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    rc, stdout = module._run(["npm", "--version"], capture_stdout=True)

    assert rc == 0
    assert stdout == "ok"
    assert captured["npm_config_cache"] == str(module._PROJECT_DIR / "tmp" / "npm-cache")
    assert captured["npm_config_update_notifier"] == "false"


def test_csharp_phase2_live_tests_clear_phase1_only_flag(monkeypatch) -> None:
    module = _load_runner_at(
        "OPC_UA_Clients/Release2/IJT_CSharp_Client/run_all_tests.py",
        "ijt_csharp_runner_phase2_env",
    )
    captured: dict[str, dict[str, str]] = {}

    def _fake_run(cmd, *, cwd=module._PROJECT_DIR, env=None, capture_stdout=False):
        captured["env"] = env or {}
        return 0, ""

    monkeypatch.setattr(module, "_run", _fake_run)
    monkeypatch.setattr(module, "_parse_trx", lambda path: (1, 0, 0, 1))

    result = module._step_live_tests("opc.tcp://localhost:40464")

    assert result.status == "PASS"
    assert captured["env"]["IJT_PHASE1_ONLY"] == "false"
    assert captured["env"]["OPCUA_SERVER_URL"] == "opc.tcp://localhost:40464"


def test_csharp_managed_live_all_skipped_is_failure() -> None:
    module = _load_runner_at(
        "OPC_UA_Clients/Release2/IJT_CSharp_Client/run_all_tests.py",
        "ijt_csharp_runner_managed_live",
    )
    result = module.StepResult(
        "Live Tests",
        "PHASE 2",
        "PASS",
        "0/110, 110 skipped",
        1.0,
        passed=0,
        failed=0,
        skipped=110,
        total=110,
    )

    enforced = module._enforce_managed_live_coverage(result, "40464")

    assert enforced.status == "FAIL"
    assert enforced.detail == "0/110, 110 skipped (managed server unavailable)"
