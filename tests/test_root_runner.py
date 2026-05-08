from __future__ import annotations

import importlib.util
import logging
import re
import subprocess
import sys
from pathlib import Path

import pytest


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


def test_suite_ids_match_naming_pattern() -> None:
    suite_id_pattern = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)+$")
    focus_pattern = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
    components = tuple(
        sorted(
            (
                "repo",
                "server",
                "csharp-client",
                "console-client",
                "node-client",
                "web-client",
                "test-client",
            ),
            key=len,
            reverse=True,
        )
    )
    tier_phrases = tuple(
        sorted(
            (
                "static",
                "live",
                "e2e",
                "smoke",
                "docker-smoke",
                "linux-package-smoke",
            ),
            key=len,
            reverse=True,
        )
    )

    def parse_suite_id(suite_id: str) -> tuple[str, str, str]:
        component = next(
            (candidate for candidate in components if suite_id.startswith(f"{candidate}-")),
            None,
        )
        assert component is not None, suite_id

        rest = suite_id[len(component) + 1 :]
        tier = next(
            (
                candidate
                for candidate in tier_phrases
                if rest == candidate or rest.startswith(f"{candidate}-")
            ),
            None,
        )
        assert tier is not None, suite_id

        focus = "" if rest == tier else rest[len(tier) + 1 :]
        return component, tier, focus

    assert parse_suite_id("web-client-e2e-smoke") == ("web-client", "e2e", "smoke")
    assert parse_suite_id("web-client-docker-smoke") == (
        "web-client",
        "docker-smoke",
        "",
    )
    assert parse_suite_id("server-linux-package-smoke") == (
        "server",
        "linux-package-smoke",
        "",
    )
    assert parse_suite_id("server-smoke") == ("server", "smoke", "")

    expected_components = {
        "repo",
        "server",
        "csharp-client",
        "console-client",
        "node-client",
        "web-client",
        "test-client",
    }
    expected_tiers = {
        "static",
        "live",
        "e2e",
        "smoke",
        "docker-smoke",
        "linux-package-smoke",
    }

    for suite_id, spec in _runner.SUITE_REGISTRY.items():
        assert suite_id == spec.id
        assert suite_id_pattern.fullmatch(suite_id)

        component, tier, focus = parse_suite_id(suite_id)
        assert component in expected_components
        assert tier in expected_tiers
        if focus:
            assert focus_pattern.fullmatch(focus), suite_id


def test_suite_groups_are_known_enum_values() -> None:
    assert {group.value for group in _runner.SuiteGroup} == {
        "repo-checks",
        "phase1-static",
        "phase2-live",
        "phase2-package",
        "phase2-web-live",
    }
    assert all(
        isinstance(spec.group, _runner.SuiteGroup) for spec in _runner.SUITE_REGISTRY.values()
    )


def test_suite_registry_has_no_duplicate_ids() -> None:
    assert len(_runner.SUITE_REGISTRY) == 20
    assert len(set(_runner.SUITE_REGISTRY)) == len(_runner.SUITE_REGISTRY)

    runners = [spec.runner for spec in _runner.SUITE_REGISTRY.values()]
    assert len(set(runners)) == len(runners)


def test_workflow_matrix_uses_only_known_suite_ids() -> None:
    import yaml

    workflow_path = _runner.REPO_ROOT / ".github" / "workflows" / "integration.yml"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    known_suite_ids = set(_runner.SUITE_REGISTRY)
    referenced_suite_ids: list[str] = []

    for job_name, job in workflow.get("jobs", {}).items():
        steps = job.get("steps", [])
        for step in steps:
            run = step.get("run") if isinstance(step, dict) else None
            if not isinstance(run, str) or "--suite" not in run:
                continue

            referenced_suite_ids.extend(re.findall(r"--suite\s+[\"']?([a-z][a-z0-9-]+)[\"']?", run))

            if "matrix.suite" in run:
                matrix = job.get("strategy", {}).get("matrix", {})
                matrix_suite_ids: list[str] = []
                if isinstance(matrix.get("suite"), list):
                    matrix_suite_ids.extend(matrix["suite"])
                for entry in matrix.get("include", []):
                    if isinstance(entry, dict) and isinstance(entry.get("suite"), str):
                        matrix_suite_ids.append(entry["suite"])
                assert matrix_suite_ids, f"{job_name} uses matrix.suite without suite values"
                referenced_suite_ids.extend(matrix_suite_ids)

    assert referenced_suite_ids
    assert set(referenced_suite_ids) <= known_suite_ids


def test_unknown_legacy_suite_id_prints_slice1_guidance(capsys) -> None:
    parser = _runner._build_parser()
    args = parser.parse_args(["--suite", "webclient-live-e2e-features"])

    with pytest.raises(SystemExit) as excinfo:
        _runner._validate_suite_arg(parser, args)

    assert excinfo.value.code == 2
    stderr = capsys.readouterr().err
    assert "unknown suite: webclient-live-e2e-features" in stderr
    assert _runner.SUITE_RENAMED_GUIDANCE in stderr


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
    phase2_specs = _runner.phase2_specs()
    assert "server-linux-package-smoke" in phase2_specs
    assert (
        phase2_specs["server-linux-package-smoke"].runner
        is _runner._suite_server_linux_package_smoke
    )


def test_webclient_live_suites_are_split_by_test_type(monkeypatch) -> None:
    calls: list[dict] = []

    def _fake_delegate_to_runner(**kwargs):
        calls.append(kwargs)
        return _runner.SuiteResult(kwargs["name"], True, 0.0)

    monkeypatch.setattr(_runner, "_delegate_to_runner", _fake_delegate_to_runner)
    monkeypatch.setattr(_runner, "_find_cmd", lambda names: "docker")
    monkeypatch.setattr(_runner, "_docker_daemon_running", lambda docker: True)

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
        "web-client-live-opcua-direct",
        "web-client-live-websocket-api",
        "web-client-live-websocket-connection",
        "web-client-e2e-smoke",
        "web-client-e2e-features",
        "web-client-e2e-regression",
        "web-client-docker-smoke",
    }
    assert expected_suites <= set(_runner.phase2_specs())
    assert "webclient-live" not in _runner.SUITE_REGISTRY
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
        name="web-client-e2e-features",
        runner_dir=Path(__file__).resolve().parents[1],
        phase_args=["--playwright-features-only"],
        label="webclient runner (e2e-features)",
    )
    rc = _runner._print_summary([result], total_time=1.0)

    output = capsys.readouterr().out
    assert result.ok is False
    assert result.skipped is False
    assert rc == 1
    assert "Web Client - Browser feature coverage" in output
    assert "FAIL" in output
    assert "ONE OR MORE SUITES FAILED" in output


def test_server_linux_package_smoke_skips_without_docker(monkeypatch) -> None:
    monkeypatch.setattr(_runner, "_find_cmd", lambda names: None)

    result = _runner._suite_server_linux_package_smoke()

    assert result.ok
    assert result.skipped
    assert result.notes == ["docker not in PATH"]


def test_webclient_docker_smoke_skips_without_docker(monkeypatch) -> None:
    monkeypatch.setattr(_runner, "_find_cmd", lambda names: None)

    result = _runner._suite_webclient_docker_smoke()

    assert result.ok
    assert result.skipped
    assert result.notes == ["docker not in PATH"]


def test_webclient_docker_smoke_skips_when_docker_daemon_is_not_running(monkeypatch) -> None:
    def fail_if_delegated(**_kwargs):
        raise AssertionError("webclient docker smoke should skip before delegating")

    monkeypatch.setattr(_runner, "_find_cmd", lambda names: "docker")
    monkeypatch.setattr(_runner, "_docker_daemon_running", lambda docker: False)
    monkeypatch.setattr(_runner, "_delegate_to_runner", fail_if_delegated)

    result = _runner._suite_webclient_docker_smoke()

    assert result.ok
    assert result.skipped
    assert result.notes == ["Docker daemon not running"]


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


def test_root_feature_worker_count_can_be_overridden_for_ci(monkeypatch) -> None:
    monkeypatch.setenv("IJT_PLAYWRIGHT_FEATURE_WORKERS", "2")
    runner = _load_runner_at("run_all_tests.py", "ijt_root_runner_feature_workers")

    assert runner.WEB_CLIENT_E2E_FEATURE_WORKERS == 2


def test_root_feature_worker_count_handles_empty_env_var(monkeypatch) -> None:
    """Regression: integration.yml matrix passes IJT_PLAYWRIGHT_FEATURE_WORKERS=''
    for non-feature suites (e.g. ``${{ matrix.feature_workers || '' }}``).
    ``int(os.getenv(name, default))`` returns '' on set-but-empty vars and
    crashes the module at import time, taking down every Web Client live job."""
    monkeypatch.setenv("IJT_PLAYWRIGHT_FEATURE_WORKERS", "")
    runner = _load_runner_at("run_all_tests.py", "ijt_root_runner_feature_workers_empty")

    assert runner.WEB_CLIENT_E2E_FEATURE_WORKERS == 4


def test_root_feature_worker_count_handles_whitespace_env_var(monkeypatch) -> None:
    monkeypatch.setenv("IJT_PLAYWRIGHT_FEATURE_WORKERS", "   ")
    runner = _load_runner_at("run_all_tests.py", "ijt_root_runner_feature_workers_ws")

    assert runner.WEB_CLIENT_E2E_FEATURE_WORKERS == 4


def test_root_int_env_helper_rejects_garbage(monkeypatch) -> None:
    monkeypatch.setenv("IJT_SUITE_TIMEOUT", "not-a-number")

    with pytest.raises(ValueError, match="IJT_SUITE_TIMEOUT must be an integer"):
        _load_runner_at("run_all_tests.py", "ijt_root_runner_int_env_garbage")


def test_ci_web_client_splits_local_phase1_runner_by_language_lane() -> None:
    workflow = (_runner.REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    web_jobs = workflow.split("  web-client-python:", 1)[1].split("  console-client:", 1)[0]

    assert "python run_all_tests.py --phase1-python" in web_jobs
    assert "python run_all_tests.py --phase1-js" in web_jobs
    assert "results-web-client-python" in workflow
    assert "results-web-client-js" in workflow
    assert "python -m pytest tests/python/unit" not in web_jobs
    assert "npx vitest run --coverage" not in web_jobs
    assert "steps.web_python_runner.outcome" in web_jobs
    assert "steps.web_js_runner.outcome" in web_jobs


def test_integration_web_client_uses_local_live_suite_matrix() -> None:
    workflow = (_runner.REPO_ROOT / ".github" / "workflows" / "integration.yml").read_text(
        encoding="utf-8"
    )
    expected_suites = {
        "web-client-live-opcua-direct",
        "web-client-live-websocket-api",
        "web-client-live-websocket-connection",
        "web-client-e2e-smoke",
        "web-client-e2e-features",
        "web-client-e2e-regression",
    }

    for suite in expected_suites:
        assert suite in workflow

    assert 'python run_all_tests.py --suite "${{ matrix.suite }}" --verbose' in workflow
    assert "OPC_UA_Clients/Release2/IJT_Web_Client/tests/python/integration/" not in workflow
    assert "results-live-webclient-${{ matrix.suite }}" in workflow
    assert "all-results/results-live-webclient-*/**/*.xml" in workflow
    assert "Cache Playwright browsers" in workflow
    assert "npx playwright install --with-deps chromium" in workflow
    assert "if: startsWith(matrix.suite, 'web-client-e2e-')" in workflow


def test_integration_web_client_features_are_sharded() -> None:
    import yaml

    workflow_path = _runner.REPO_ROOT / ".github" / "workflows" / "integration.yml"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    live_webclient = workflow["jobs"]["live-webclient"]
    rows = live_webclient["strategy"]["matrix"]["include"]
    feature_rows = [row for row in rows if row.get("suite") == "web-client-e2e-features"]

    assert [row.get("feature_shard") for row in feature_rows] == ["1/2", "2/2"]
    assert [row.get("shard_suffix") for row in feature_rows] == ["-shard-1of2", "-shard-2of2"]
    assert [row.get("feature_workers") for row in feature_rows] == ["1", "1"]
    assert [row.get("label") for row in feature_rows] == [
        "Browser Features (1/2)",
        "Browser Features (2/2)",
    ]
    assert len({row["shard_suffix"] for row in feature_rows}) == 2
    assert workflow["jobs"]["report"]["needs"].count("live-webclient") == 1
    assert "live-webclient-shard" not in workflow["jobs"]["report"]["needs"]


def test_integration_playwright_install_is_skipped_on_cache_hit() -> None:
    """The Playwright browsers cache step must expose an id so the install step
    can skip on cache hit. Re-running ``playwright install`` on a warm cache
    costs ~3 min per shard and dwarfs the actual sharding benefit.
    """
    import yaml

    workflow_path = _runner.REPO_ROOT / ".github" / "workflows" / "integration.yml"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    live_webclient = workflow["jobs"]["live-webclient"]
    steps = live_webclient["steps"]

    cache_step = next(s for s in steps if s.get("name") == "Cache Playwright browsers")
    install_step = next(s for s in steps if s.get("name") == "Install Playwright browsers")

    assert cache_step.get("id") == "pw-cache", (
        "Cache step must expose id=pw-cache so install can reference its outputs"
    )
    if_clause = install_step.get("if", "")
    assert "steps.pw-cache.outputs.cache-hit != 'true'" in if_clause, (
        f"Install step must skip when cache hit; got if={if_clause!r}"
    )
    assert "startsWith(matrix.suite, 'web-client-e2e-')" in if_clause, (
        "Install step must remain gated to e2e matrix rows"
    )


def test_integration_report_surfaces_browser_feature_timings() -> None:
    workflow = (_runner.REPO_ROOT / ".github" / "workflows" / "integration.yml").read_text(
        encoding="utf-8"
    )

    assert "browser_feature_timings(" in workflow
    assert "results-live-webclient-web-client-e2e-features*/**/timing-latest.json" in workflow
    assert "### Browser Features Timing" in workflow
    assert "pip-install" in workflow
    assert "npm-install" in workflow
    assert "playwright-install" in workflow
    assert "playwright-features" in workflow


def test_integration_report_surfaces_csharp_live_timings() -> None:
    workflow = (_runner.REPO_ROOT / ".github" / "workflows" / "integration.yml").read_text(
        encoding="utf-8"
    )

    assert "csharp_live_timings(" in workflow
    assert "results-csharp-live/**/*.trx" in workflow
    assert "UnitTestResult" in workflow
    assert "### C# Live Timing" in workflow
    assert "#### Top C# Live Tests" in workflow


def test_integration_report_surfaces_job_durations() -> None:
    workflow = (_runner.REPO_ROOT / ".github" / "workflows" / "integration.yml").read_text(
        encoding="utf-8"
    )

    assert "actions: read" in workflow
    assert "GH_REPOSITORY:  ${{ github.repository }}" in workflow
    assert "GH_RUN_ID:      ${{ github.run_id }}" in workflow
    assert "GH_TOKEN:       ${{ github.token }}" in workflow
    assert 'REPORT_JOB_NAME: "📋 Extended Test Report"' in workflow
    assert "def job_durations(path):" in workflow
    assert "excluding this report job" in workflow
    assert "name == report_job_name" in workflow
    assert "Report job duration is excluded" in workflow
    assert "### ⏱️ Job Durations" in workflow
    assert "current workflow run jobs API" in workflow
    assert "format_optional_duration(duration)" in workflow
    assert "🏁" in workflow


def test_integration_report_uses_count_baseline_and_skip_drift_warnings() -> None:
    import json

    baseline_path = _runner.REPO_ROOT / "tests" / "baselines" / "integration-test-counts.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    workflow = (_runner.REPO_ROOT / ".github" / "workflows" / "integration.yml").read_text(
        encoding="utf-8"
    )

    assert baseline["schema_version"] == 1
    assert set(baseline["suites"]) == {
        "sd_smoke",
        "wd_py",
        "wd_js",
        "tc_smoke",
        "tc_tests",
        "wc_web",
        "con_live",
        "cs_live",
    }
    assert baseline["suites"]["tc_tests"]["skip_tolerance"] == 10
    assert "load_integration_baseline(" in workflow
    assert "format_count_delta(" in workflow
    assert 'return "" if delta == 0 else f" ({delta:+d})"' in workflow
    assert "integration_drift_warnings(" in workflow
    assert "tests/baselines/integration-test-counts.json" in workflow
    assert "### ⚠️ Report Warnings" in workflow
    assert "skip drift" in workflow
    assert "suite collection drift" in workflow


def test_ci_report_uses_declared_coverage_thresholds() -> None:
    workflow = (_runner.REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "| Component | Platform | Tests | Skipped | Coverage / Threshold |" in workflow
    assert "def cov(pct, threshold=None):" in workflow
    assert "cov(web_cov, 95)" in workflow
    assert "cov(web_js_cov, 95)" in workflow
    assert "cov(con_cov, 95)" in workflow
    assert "cov(nod_cov, 95)" in workflow
    assert "cov(cs_cov, 95)" in workflow
    assert "cov(tc_cov, 95)" in workflow
    assert "coverage_warnings" in workflow
    assert "### ⚠️ Coverage Threshold Warnings" in workflow


def test_ci_report_web_python_skip_budget_uses_expected_skip_identities() -> None:
    workflow = (_runner.REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert '"web-client (Python)":      2' in workflow
    assert "expected_skip_names" in workflow
    assert "test_required_static_asset_exists[node_modules/chart.js/dist/chart.umd.js]" in workflow
    assert "test_eslint_passes" in workflow
    assert "unexpected skips detected" in workflow
    assert "missing_expected_names" in workflow
    assert "expected skips not observed" in workflow


def test_ci_report_steps_skip_missing_artifacts_for_skipped_jobs() -> None:
    workflow = (_runner.REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "if: always() && needs.web-client-python.result != 'skipped'" in workflow
    assert "if: always() && needs.web-client-js.result != 'skipped'" in workflow
    assert "if: always() && needs.test-client.result != 'skipped'" in workflow
    assert "if: always() && needs.csharp-unit.result != 'skipped'" in workflow


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


def test_ci_mode_flag_is_advertised_in_help() -> None:
    parser = _runner._build_parser()
    help_text = parser.format_help()

    assert "--ci-mode" in help_text
    assert "CI=1" in help_text


def test_ci_mode_flag_parses_independently_of_phase_flags() -> None:
    parser = _runner._build_parser()

    args = parser.parse_args(["--ci-mode"])
    assert args.ci_mode is True
    assert args.phase1 is False
    assert args.phase2 is False

    args = parser.parse_args(["--ci-mode", "--phase1"])
    assert args.ci_mode is True
    assert args.phase1 is True


def test_ci_mode_flag_sets_ci_env_for_child_runners(monkeypatch, capsys) -> None:
    """--ci-mode must inject CI=1 into the environment so client subrunners
    take their CI codepath (skip venv relaunch, etc.). Without this, bugs
    that only fail in GitHub Actions cannot be reproduced locally."""
    import os as _os

    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setattr(sys, "argv", ["run_all_tests.py", "--ci-mode", "--list"])

    rc = _runner.main()
    captured = capsys.readouterr()

    assert rc == 0
    assert _os.environ.get("CI") == "1"
    # --list still works in ci-mode
    assert "Phase 1 static suites" in captured.out

    monkeypatch.delenv("CI", raising=False)


def test_delegate_to_runner_inherits_forced_ci_env(monkeypatch) -> None:
    captured: dict[str, str] = {}

    def _fake_run_captured(cmd, *, cwd, timeout, env, label):
        captured.update(env)
        return 0, "child ok\n"

    monkeypatch.setenv("CI", "1")
    monkeypatch.setattr(_runner, "_run_captured", _fake_run_captured)

    result = _runner._delegate_to_runner(
        name="repo-hygiene",
        runner_dir=_runner.REPO_ROOT,
        phase_args=["--list"],
        label="root runner probe",
    )

    assert result.ok is True
    assert captured["CI"] == "1"


def test_ci_mode_not_set_without_flag(monkeypatch, capsys) -> None:
    import os as _os

    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setattr(sys, "argv", ["run_all_tests.py", "--list"])

    rc = _runner.main()
    capsys.readouterr()

    assert rc == 0
    assert _os.environ.get("CI") is None
