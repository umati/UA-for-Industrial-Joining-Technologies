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
_CI_REPORT_SCRIPT = _runner.REPO_ROOT / "reporting" / "ci_run_summary.py"
_INTEGRATION_REPORT_SCRIPT = _runner.REPO_ROOT / "reporting" / "system_tests_run_summary.py"


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
                "compatibility-smoke",
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
    assert parse_suite_id("web-client-compatibility-smoke") == (
        "web-client",
        "compatibility-smoke",
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
        "compatibility-smoke",
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
        "phase2-web-compatibility",
    }
    assert all(
        isinstance(spec.group, _runner.SuiteGroup) for spec in _runner.SUITE_REGISTRY.values()
    )


def test_suite_registry_has_no_duplicate_ids() -> None:
    assert len(_runner.SUITE_REGISTRY) == 21
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


def test_zizmor_rc14_medium_findings_is_pass() -> None:
    result = _runner._parse_zizmor_output(
        '[{"determinations":{"severity":"Medium"}}]',
        14,
    )
    assert result.status == "PASS"
    assert result.detail == "1 finding(s), none high/critical"


def test_zizmor_rc14_high_finding_is_fail() -> None:
    result = _runner._parse_zizmor_output('[{"determinations":{"severity":"High"}}]', 14)
    assert result.status == "FAIL"
    assert result.detail == "1 high/critical finding(s)"


def test_zizmor_parseable_json_fails_on_high_regardless_of_rc() -> None:
    result = _runner._parse_zizmor_output('[{"determinations":{"severity":"Critical"}}]', 1)
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


def test_connection_manager_session_id_uses_web_crypto_only() -> None:
    root = Path(__file__).resolve().parents[1]
    connection_manager_path = (
        root
        / "OPC_UA_Clients"
        / "Release2"
        / "IJT_Web_Client"
        / "src"
        / "javascripts"
        / "ijt-support"
        / "connection"
        / "connection-manager.mjs"
    )
    connection_manager = connection_manager_path.read_text(encoding="utf-8")
    create_session_id = connection_manager.split("function createSessionId ()", 1)[1].split(
        "export class ConnectionManager",
        1,
    )[0]
    eslint_config = (root / "OPC_UA_Clients/Release2/IJT_Web_Client/eslint.config.mjs").read_text(
        encoding="utf-8"
    )

    assert "globalThis.crypto.randomUUID()" in create_session_id
    assert "Math.random" not in create_session_id
    assert "Date.now" not in create_session_id
    assert "src/javascripts/ijt-support/connection/connection-manager.mjs" in eslint_config
    assert "src/javascripts/ijt-support/connection/auth/**/*.mjs" in eslint_config
    assert "src/javascripts/ijt-support/connection/token/**/*.mjs" in eslint_config
    assert "src/javascripts/ijt-support/connection/nonce/**/*.mjs" in eslint_config
    assert 'callee.object.name="Math"' in eslint_config
    assert 'callee.property.name="random"' in eslint_config


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


def test_webclient_compatibility_smoke_is_opt_in_suite(monkeypatch) -> None:
    calls: list[dict] = []

    def _fake_delegate_to_runner(**kwargs):
        calls.append(kwargs)
        return _runner.SuiteResult(kwargs["name"], True, 0.0)

    monkeypatch.setattr(_runner.platform, "system", lambda: "Windows")
    monkeypatch.setattr(_runner, "_edge_executable_available", lambda: True)
    monkeypatch.setattr(_runner, "_delegate_to_runner", _fake_delegate_to_runner)

    spec = _runner.SUITE_REGISTRY["web-client-compatibility-smoke"]
    result = _runner._suite_webclient_compatibility_smoke()

    assert _runner.SuiteGroup.PHASE2_WEB_COMPATIBILITY.value == "phase2-web-compatibility"
    assert spec.display_name == "Web Client - Edge compatibility smoke"
    assert spec.group is _runner.SuiteGroup.PHASE2_WEB_COMPATIBILITY
    assert spec.runner is _runner._suite_webclient_compatibility_smoke
    assert "web-client-compatibility-smoke" not in _runner.phase1_specs()
    assert "web-client-compatibility-smoke" not in _runner.phase2_specs()
    assert result.ok
    assert calls == [
        {
            "name": "web-client-compatibility-smoke",
            "runner_dir": _runner.WEB_CLIENT_DIR,
            "phase_args": ["--compatibility-smoke-only"],
            "label": "webclient runner (compatibility-smoke)",
            "extra_env": {
                "IJT_WEB_TEST_RESULTS_DIR": str(
                    _runner.WEB_CLIENT_RESULTS_DIR / "compatibility-smoke"
                )
            },
        }
    ]


def test_webclient_compatibility_smoke_skips_when_not_windows(monkeypatch) -> None:
    def fail_if_edge_checked():
        raise AssertionError("non-Windows skip should not inspect Edge")

    monkeypatch.setattr(_runner.platform, "system", lambda: "Linux")
    monkeypatch.setattr(_runner, "_edge_executable_available", fail_if_edge_checked)

    result = _runner._suite_webclient_compatibility_smoke()

    assert result.ok
    assert result.skipped
    assert result.notes == ["Windows-only suite"]


def test_webclient_compatibility_smoke_skips_without_edge(monkeypatch) -> None:
    def fail_if_delegated(**_kwargs):
        raise AssertionError("compatibility smoke should skip before delegating")

    monkeypatch.setattr(_runner.platform, "system", lambda: "Windows")
    monkeypatch.setattr(_runner, "_edge_executable_available", lambda: False)
    monkeypatch.setattr(_runner, "_delegate_to_runner", fail_if_delegated)

    result = _runner._suite_webclient_compatibility_smoke()

    assert result.ok
    assert result.skipped
    assert result.notes == ["Microsoft Edge not installed"]


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
    assert result.detail == "9 file(s) verified"


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
            return Path("fake/make_conformance_summary.py")

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


def test_node_runner_npm_ci_starts_from_clean_install_state(monkeypatch) -> None:
    module = _load_runner_at(
        "OPC_UA_Clients/Release1/IJT_Node_Client/run_all_tests.py",
        "ijt_node_runner_npm_clean_cache",
    )
    test_root = module._PROJECT_DIR / "tmp" / "unit-test-npm-clean-state"
    if test_root.exists():
        module._force_rmtree(test_root)
    try:
        cache = test_root / "npm-cache"
        stale_entry = cache / "_cacache" / "tmp" / "stale"
        stale_entry.parent.mkdir(parents=True)
        stale_entry.write_text("stale", encoding="utf-8")
        node_modules = test_root / "node_modules"
        stale_module = node_modules / "node-opcua-nodeset-ua" / "dist"
        stale_module.mkdir(parents=True)
        monkeypatch.setattr(module, "_NPM_CACHE", cache)
        monkeypatch.setattr(module, "_NODE_MODULES", node_modules)

        def _fake_run(cmd):
            assert cmd == [module._NPM, "ci", *module._NPM_INSTALL_FLAGS]
            assert cache.exists()
            assert not stale_entry.exists()
            assert not stale_module.exists()
            return 0, ""

        monkeypatch.setattr(module, "_run", _fake_run)

        result = module._step_npm_ci()

        assert result.status == "PASS"
    finally:
        if test_root.exists():
            module._force_rmtree(test_root)


def test_node_runner_cleanup_removes_runner_npm_cache() -> None:
    module = _load_runner_at(
        "OPC_UA_Clients/Release1/IJT_Node_Client/run_all_tests.py",
        "ijt_node_runner_npm_cleanup",
    )
    test_root = module._PROJECT_DIR / "tmp" / "unit-test-npm-cleanup"
    if test_root.exists():
        module._force_rmtree(test_root)
    try:
        cache = test_root / "tmp" / "npm-cache"
        (cache / "_cacache").mkdir(parents=True)

        module._cleanup_caches(test_root)

        assert not cache.exists()
    finally:
        if test_root.exists():
            module._force_rmtree(test_root)


def test_ci_csharp_jobs_do_not_use_blocking_nuget_cache() -> None:
    import yaml

    workflow_path = _runner.REPO_ROOT / ".github" / "workflows" / "ci.yml"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))

    for job_name in ("csharp-unit", "csharp-vuln"):
        steps = workflow["jobs"][job_name]["steps"]
        step_names = [step.get("name", "") for step in steps]
        assert "Cache NuGet Packages" not in step_names
        assert not any(step.get("uses", "").startswith("actions/cache") for step in steps)
        assert "Restore NuGet Packages" in step_names


def test_root_feature_worker_count_can_be_overridden_for_ci(monkeypatch) -> None:
    monkeypatch.setenv("IJT_PLAYWRIGHT_FEATURE_WORKERS", "2")
    runner = _load_runner_at("run_all_tests.py", "ijt_root_runner_feature_workers")

    assert runner.WEB_CLIENT_E2E_FEATURE_WORKERS == 2


def test_root_feature_worker_count_handles_empty_env_var(monkeypatch) -> None:
    """Regression: integration.yml matrix passes IJT_PLAYWRIGHT_FEATURE_WORKERS=''
    for non-feature suites (e.g. ``${{ matrix.feature_workers || '' }}``).
    ``int(os.getenv(name, default))`` returns '' on set-but-empty vars and
    crashes the module at import time, taking down every Web Client live job."""
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setenv("IJT_PLAYWRIGHT_FEATURE_WORKERS", "")
    runner = _load_runner_at("run_all_tests.py", "ijt_root_runner_feature_workers_empty")

    assert runner.WEB_CLIENT_E2E_FEATURE_WORKERS == 4


def test_root_feature_worker_count_handles_whitespace_env_var(monkeypatch) -> None:
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setenv("IJT_PLAYWRIGHT_FEATURE_WORKERS", "   ")
    runner = _load_runner_at("run_all_tests.py", "ijt_root_runner_feature_workers_ws")

    assert runner.WEB_CLIENT_E2E_FEATURE_WORKERS == 4


def test_root_feature_worker_count_defaults_to_two_in_ci(monkeypatch) -> None:
    monkeypatch.delenv("IJT_PLAYWRIGHT_FEATURE_WORKERS", raising=False)
    monkeypatch.setenv("CI", "true")
    runner = _load_runner_at("run_all_tests.py", "ijt_root_runner_feature_workers_ci")

    assert runner.WEB_CLIENT_E2E_FEATURE_WORKERS == 2


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


def test_integration_web_client_uses_split_live_and_browser_matrices() -> None:
    import yaml

    workflow_path = _runner.REPO_ROOT / ".github" / "workflows" / "integration.yml"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    live_rows = workflow["jobs"]["live-webclient"]["strategy"]["matrix"]["include"]
    browser_rows = workflow["jobs"]["live-webclient-browser"]["strategy"]["matrix"]["include"]
    live_suites = {row["suite"] for row in live_rows}
    browser_suites = {row["suite"] for row in browser_rows}

    assert live_suites == {
        "web-client-live-opcua-direct",
        "web-client-live-websocket-api",
        "web-client-live-websocket-connection",
    }
    assert browser_suites == {
        "web-client-e2e-smoke",
        "web-client-e2e-features",
        "web-client-e2e-regression",
    }
    assert workflow["jobs"]["live-webclient"]["runs-on"] == "windows-latest"
    assert workflow["jobs"]["live-webclient-browser"]["runs-on"] == "ubuntu-latest"

    workflow_text = workflow_path.read_text(encoding="utf-8")
    assert 'python run_all_tests.py --suite "${{ matrix.suite }}" --verbose' in workflow_text
    assert "OPC_UA_Clients/Release2/IJT_Web_Client/tests/python/integration/" not in workflow_text
    assert "results-live-webclient-${{ matrix.suite }}" in workflow_text
    integration_report = _INTEGRATION_REPORT_SCRIPT.read_text(encoding="utf-8")
    assert "all-results/results-live-webclient-web-client-e2e-*/**/*.xml" in integration_report
    assert "Cache Playwright browsers" not in workflow_text
    assert "npx playwright install --with-deps chromium" not in workflow_text


def test_integration_web_client_features_are_sharded() -> None:
    import yaml

    workflow_path = _runner.REPO_ROOT / ".github" / "workflows" / "integration.yml"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    browser_webclient = workflow["jobs"]["live-webclient-browser"]
    rows = browser_webclient["strategy"]["matrix"]["include"]
    feature_rows = [row for row in rows if row.get("suite") == "web-client-e2e-features"]

    assert [row.get("feature_shard") for row in feature_rows] == ["1/2", "2/2"]
    assert [row.get("shard_suffix") for row in feature_rows] == ["-shard-1of2", "-shard-2of2"]
    assert [row.get("feature_workers") for row in feature_rows] == [None, None]
    assert [row.get("label") for row in feature_rows] == [
        "Browser Features (1/2)",
        "Browser Features (2/2)",
    ]
    assert len({row["shard_suffix"] for row in feature_rows}) == 2
    assert workflow["jobs"]["report"]["needs"].count("live-webclient") == 1
    assert workflow["jobs"]["report"]["needs"].count("live-webclient-browser") == 1
    assert "live-webclient-shard" not in workflow["jobs"]["report"]["needs"]


def test_integration_web_client_e2e_jobs_run_on_stock_ubuntu_runner() -> None:
    """Browser e2e must run inside the owned ijt-browser-ci image with --network=none.

    History: a job-level ``container: image: mcr.microsoft.com/playwright:...``
    block once ran every browser suite, but a job-level container image is
    pulled by GitHub *before* any workflow step runs, so a transient registry
    outage took the whole job down with no in-job retry. The owned
    ``ghcr.io/.../ijt-browser-ci`` image is resolved to the reviewed
    ``image-pin.json`` digest and wired into this job via a step-level
    ``docker run --network=none``, so pull + run + diagnostics all happen
    inside steps the job controls end-to-end. This
    regression gate prevents re-introducing a job-level ``container:`` block,
    re-introducing live ``npx playwright install --with-deps`` on the host
    runner, or moving e2e onto Windows-hosted Chromium.
    """
    import yaml

    workflow_path = _runner.REPO_ROOT / ".github" / "workflows" / "integration.yml"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))

    for job_name, job in workflow["jobs"].items():
        rows = job.get("strategy", {}).get("matrix", {}).get("include", [])
        e2e_rows = [
            row
            for row in rows
            if isinstance(row, dict) and row.get("suite", "").startswith("web-client-e2e-")
        ]
        if not e2e_rows:
            continue

        assert job_name == "live-webclient-browser"
        assert job["runs-on"] == "ubuntu-latest"
        assert "container" not in job, (
            "live-webclient-browser must not use a job-level container image: "
            "GitHub pulls container-job images before any step runs, so a "
            "registry outage takes the whole job down with no in-job retry. "
            "The job uses a step-level `docker run` against the owned "
            "ijt-browser-ci image instead."
        )
        assert job.get("permissions", {}).get("packages") == "read", (
            "live-webclient-browser must declare `permissions: packages: read` "
            "to authenticate against GHCR for the ijt-browser-ci pull."
        )

        steps = job["steps"]
        step_names = [step.get("name") or step.get("uses", "") for step in steps]
        resolve_index = step_names.index(
            "Resolve IJT Browser CI image reference (digest-qualified)"
        )
        login_index = next(
            index
            for index, step in enumerate(steps)
            if step.get("uses", "").startswith("docker/login-action@")
        )
        assert login_index < resolve_index, (
            "Resolve step may pull the reviewed GHCR image digest; docker login "
            "must happen before resolving the browser image reference."
        )

        assert not any(
            step.get("uses", "").startswith("actions/setup-python@") for step in steps
        ), (
            "setup-python is baked into the ijt-browser-ci image; the host "
            "runner must not install its own Python."
        )
        assert not any(step.get("uses", "").startswith("actions/setup-node@") for step in steps), (
            "setup-node is baked into the ijt-browser-ci image; the host "
            "runner must not install its own Node."
        )

        resolve_step = next(
            step
            for step in steps
            if step.get("name") == "Resolve IJT Browser CI image reference (digest-qualified)"
        )
        assert (
            resolve_step.get("env", {}).get("PIN_PATH")
            == ".github/docker/ijt-browser-ci/image-pin.json"
        )
        assert "^sha256:[0-9a-f]{64}$" in resolve_step["run"], (
            "Resolve step must guard that the digest is sha256:<64hex>."
        )
        assert "PR_HEAD_SHA" in resolve_step["env"], (
            "Resolve step must know the PR head SHA so dependency-update PRs "
            "can use the PR-scoped browser image built from the same lockfile."
        )
        assert "PR_AUTHOR" in resolve_step["env"]
        assert "trusted_dependency_bot" in resolve_step["run"]
        assert r"app/renovate|renovate\[bot\]|dependabot\[bot\]" in resolve_step["run"]
        assert "dependency_image_inputs_changed" in resolve_step["run"]
        assert "OPC_UA_Clients/Release2/IJT_Web_Client/package-lock.json" in resolve_step["run"]
        assert "PR-scoped dependency image" in resolve_step["run"]
        assert "main SHA dependency image" in resolve_step["run"]
        assert 'docker pull "$tag"' in resolve_step["run"]
        assert "/opt/ijt-browser-ci/metadata.json" in resolve_step["run"]
        assert "actual_sha" in resolve_step["run"]
        assert "image_source=${image_source}" in resolve_step["run"]

        login_step = next(
            step for step in steps if step.get("uses", "").startswith("docker/login-action@")
        )
        assert login_step.get("with", {}).get("registry") == "ghcr.io"

        pull_step = next(
            step
            for step in steps
            if step.get("name") == "Pull IJT Browser CI image (3-attempt retry)"
        )
        pull_body = pull_step["run"]
        assert "docker pull" in pull_body
        assert "source:   ${IMAGE_SOURCE}" in pull_body
        assert "max_attempts=3" in pull_body, (
            "Pull step must retry 3x; transient GHCR errors must not fail "
            "the job on a single attempt."
        )
        assert "build-browser-ci-image.yml" in pull_body, (
            "Pull step diagnostic must name the image-build workflow so operators can republish."
        )
        # Match the precise diagnostic phrase from integration.yml so this
        # assertion can't be misread as URL-substring sanitization (CodeQL
        # py/incomplete-url-substring-sanitization false-positive on the
        # bare "ghcr.io" substring).
        assert "ghcr.io (GHCR)" in pull_body, (
            "Pull step diagnostic must name the registry as `ghcr.io (GHCR)` "
            "so the operator immediately knows which registry failed."
        )

        run_step = next(
            step
            for step in steps
            if step.get("name") == "Run Web Client browser e2e suite (offline, --network=none)"
        )
        run_body = run_step["run"]
        assert "docker run" in run_body
        assert "--network=none" in run_body
        assert '--user "$(id -u):$(id -g)"' in run_body
        assert '-v "${GITHUB_WORKSPACE}:/workspace"' in run_body
        assert "PIP_NO_INDEX=1" in run_body
        assert "npm_config_offline=true" in run_body
        assert "SKIP_VENV_INSTALL=1" in run_body
        assert "PLAYWRIGHT_BROWSERS_PATH=/ms-playwright" in run_body
        assert "python run_all_tests.py --suite" in run_body
        for required_env in (
            "GITHUB_RUN_ID",
            "GITHUB_RUN_ATTEMPT",
            "GITHUB_SHA",
            "GITHUB_REPOSITORY",
            "GITHUB_SERVER_URL",
        ):
            assert required_env in run_body, (
                f"Run step must propagate {required_env} into the container so "
                "in-container reports/summaries can stamp the run identity."
            )

        assert not any("Install setup-python OS helper" in name for name in step_names), (
            "The lsb-release helper step was only needed for the slim Playwright "
            "container image and must not be reintroduced."
        )
        assert not any("npx playwright install" in (step.get("run") or "") for step in steps), (
            "Live `npx playwright install --with-deps` on the host runner is "
            "forbidden; Chromium + deps are baked into the ijt-browser-ci image."
        )


def test_codeql_workflow_display_name_preserves_required_contexts() -> None:
    import yaml

    workflow_path = _runner.REPO_ROOT / ".github" / "workflows" / "codeql.yml"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))

    assert workflow["name"] == "Security — CodeQL"
    assert set(workflow["jobs"]) == {"analyze"}
    analyze = workflow["jobs"]["analyze"]
    assert analyze["name"] == "Analyze (${{ matrix.language }})"
    assert analyze["strategy"]["matrix"]["language"] == [
        "csharp",
        "python",
        "javascript",
    ]
    assert any(
        step.get("uses", "").startswith("github/codeql-action/analyze@")
        for step in analyze["steps"]
        if isinstance(step, dict)
    )


def test_compatibility_smoke_workflow_is_schedule_only_matrix_detection() -> None:
    import yaml

    workflow_path = (
        _runner.REPO_ROOT / ".github" / "workflows" / "web-client-compatibility-smoke.yml"
    )
    workflow_text = workflow_path.read_text(encoding="utf-8")
    workflow = yaml.safe_load(workflow_text)
    triggers = workflow.get("on", workflow.get(True, {}))

    assert workflow["name"] == "Web Client — Browser Compatibility Smoke"
    assert set(triggers) == {"schedule", "workflow_dispatch"}
    assert triggers["schedule"] == [{"cron": "30 4 * * *"}]
    assert "push" not in triggers
    assert "pull_request" not in triggers

    permissions = workflow["permissions"]
    assert permissions["contents"] == "read"
    assert permissions["issues"] == "write"
    assert permissions.get("contents") != "write"

    jobs = workflow["jobs"]
    assert set(jobs) == {"web-client-compatibility-smoke"}
    job = jobs["web-client-compatibility-smoke"]
    assert job["name"] == "Web Client — Browser Compatibility Smoke"
    assert job["runs-on"] == "${{ matrix.os }}"
    assert job["defaults"]["run"]["shell"] == "pwsh"
    assert job["strategy"]["fail-fast"] is False
    matrix_rows = job["strategy"]["matrix"]["include"]
    assert matrix_rows == [{"os": "windows-latest", "browser": "msedge"}]
    assert {row["os"] for row in matrix_rows} <= {"windows-latest"}
    browsers = {row["browser"] for row in matrix_rows}
    assert browsers <= {"msedge"}
    assert not browsers & {"firefox", "webkit", "safari"}

    steps = job["steps"]
    assert not any(
        step.get("continue-on-error") is True for step in steps if isinstance(step, dict)
    )
    upload_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("name") == "Upload Web Client — Browser Compatibility Smoke results"
    )
    issue_close_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("name") == "Close recovered compatibility smoke issue"
    )
    summary_index = next(
        index for index, step in enumerate(steps) if step.get("name") == "Render run summary"
    )
    summary_step = steps[summary_index]
    summary_run = summary_step["run"]
    assert summary_index > upload_index
    assert summary_index > issue_close_index
    assert summary_step["if"] == "always()"
    assert summary_step["shell"] == "pwsh"
    assert "GITHUB_STEP_SUMMARY" in summary_run
    assert (
        "OPC_UA_Clients/Release2/IJT_Web_Client/test-results/playwright-compatibility-smoke.xml"
        in summary_step["env"]["JUNIT_PATH"]
    )
    assert "### Specs" in summary_run
    assert "### Environment" in summary_run
    assert "## Web Client — Browser Compatibility Smoke - " in summary_run
    assert "Status: results unavailable." in summary_run
    assert "Status: failed - $failed of $total specs failed." in summary_run
    assert "Status: passed - all $total specs passed." in summary_run
    assert "results-web-client-compatibility-smoke-$($env:MATRIX_OS)-$($env:MATRIX_BROWSER)" in (
        summary_run
    )
    run_commands = "\n".join(
        step.get("run", "")
        for step in steps
        if isinstance(step, dict) and isinstance(step.get("run"), str)
    )
    assert "--compatibility-smoke-only" in run_commands
    assert "msedge.exe" in run_commands
    assert "VersionInfo.ProductVersion" in run_commands
    assert "& $edge --version" not in run_commands
    assert "gh issue list" in run_commands
    assert "gh issue create" in run_commands
    assert "gh issue comment" in run_commands
    assert "gh issue close" in run_commands
    assert "[Web Client Compatibility Smoke] $env:MATRIX_OS / $env:MATRIX_BROWSER" in run_commands
    assert "[Web Client — Browser Compatibility Smoke]" not in run_commands
    for forbidden_expression in (
        "${{ matrix.",
        "${{ steps.browser_probe.outputs.",
        "${{ github.workflow",
        "${{ github.sha",
        "${{ github.server_url",
        "${{ github.repository",
        "${{ github.run_id",
    ):
        assert forbidden_expression not in run_commands
    for forbidden in (
        "[L" + "2 Compat]",
        "legacy " + "fallback",
        "L" + "2 Compatibility",
        "L" + "2 Edge Compat",
    ):
        assert forbidden not in workflow_text


def test_phase_6_7_docs_do_not_keep_rejected_or_removed_workflow_terms() -> None:
    glossary = (
        _runner.REPO_ROOT
        / "OPC_UA_Clients"
        / "Release2"
        / "IJT_Test_Client"
        / "docs"
        / "REPORT_GLOSSARY.md"
    ).read_text(encoding="utf-8")
    root_skills = (_runner.REPO_ROOT / "docs" / "SKILLS.md").read_text(encoding="utf-8")
    test_tiers = (_runner.REPO_ROOT / "docs" / "TEST_TIERS.md").read_text(encoding="utf-8")
    web_skills = (
        _runner.REPO_ROOT / "OPC_UA_Clients" / "Release2" / "IJT_Web_Client" / "docs" / "SKILLS.md"
    ).read_text(encoding="utf-8")

    assert "CI — Required Checks" not in glossary
    assert "New display name (Phase 2)" not in glossary
    assert "CodeQL Analysis" not in glossary
    assert "Security — CodeQL" in glossary
    assert "Web Client — Browser Compatibility Smoke" in glossary
    assert "[Web Client Compatibility Smoke]" in glossary

    for text in (root_skills, web_skills):
        assert "matching PR/SHA" not in text
        assert "dependency-input updates" not in text
        assert "reviewed" in text
        assert "image-pin.json" in text
        assert "Web Client — Browser Compatibility Smoke" in text
        assert "[Web Client Compatibility Smoke]" in text

    assert "LiveIntegrationTests` × 15" not in test_tiers
    assert "C# live integration tests" in test_tiers
    assert "Web Client — Browser Compatibility Smoke" in test_tiers
    assert "[Web Client Compatibility Smoke]" in test_tiers


def test_compatibility_smoke_playwright_scope_is_two_edge_specs_only() -> None:
    web_root = _runner.REPO_ROOT / "OPC_UA_Clients" / "Release2" / "IJT_Web_Client"
    l1_config = (web_root / "playwright.config.mjs").read_text(encoding="utf-8")
    smoke_config = (web_root / "playwright.compatibility-smoke.config.mjs").read_text(
        encoding="utf-8"
    )
    spec_dir = web_root / "tests" / "e2e-compatibility-smoke"
    spec_files = sorted(path.name for path in spec_dir.glob("*.spec.mjs"))

    assert "testDir: './tests/e2e'" in l1_config
    assert "e2e-compatibility-smoke" not in l1_config

    assert "testDir: './tests/e2e-compatibility-smoke'" in smoke_config
    assert re.search(r"retries:\s*0", smoke_config)
    assert smoke_config.count("name: 'compatibility-smoke'") == 1
    assert re.findall(r"channel:\s*'([^']+)'", smoke_config) == ["msedge"]
    assert "chromium" in smoke_config
    assert "firefox" not in smoke_config
    assert "webkit" not in smoke_config
    assert "safari" not in smoke_config.lower()

    assert spec_files == [
        "edge-result-export-download-smoke.spec.mjs",
        "edge-result-import-filechooser-smoke.spec.mjs",
    ]
    test_count = sum(
        len(re.findall(r"\btest\(", (spec_dir / spec_file).read_text(encoding="utf-8")))
        for spec_file in spec_files
    )
    assert test_count == 2


def test_integration_report_surfaces_browser_feature_timings() -> None:
    report_script = _INTEGRATION_REPORT_SCRIPT.read_text(encoding="utf-8")

    assert "browser_feature_timings(" in report_script
    assert "results-live-webclient-web-client-e2e-features*/**/timing-latest.json" in report_script
    assert "Browser Feature Stage Timing" in report_script
    assert "pip-install" in report_script
    assert "npm-install" in report_script
    assert "playwright-install" in report_script
    assert "playwright-features" in report_script


def test_integration_report_surfaces_csharp_live_timings() -> None:
    report_script = _INTEGRATION_REPORT_SCRIPT.read_text(encoding="utf-8")

    assert "csharp_live_timings(" in report_script
    assert "results-csharp-live/**/*.trx" in report_script
    assert "UnitTestResult" in report_script
    assert "C# Live Timing Details" in report_script
    assert "#### Slowest C# Live Tests" in report_script


def test_integration_report_surfaces_job_durations() -> None:
    workflow = (_runner.REPO_ROOT / ".github" / "workflows" / "integration.yml").read_text(
        encoding="utf-8"
    )
    report_script = _INTEGRATION_REPORT_SCRIPT.read_text(encoding="utf-8")

    assert "actions: read" in workflow
    assert "GH_REPOSITORY:  ${{ github.repository }}" in workflow
    assert "GH_RUN_ID:      ${{ github.run_id }}" in workflow
    assert "GH_TOKEN:       ${{ github.token }}" in workflow
    assert 'REPORT_JOB_NAME: "📋 System Tests Summary"' in workflow
    assert "def job_durations(path):" in report_script
    assert "excluding this report job" in report_script
    assert "name == report_job_name" in report_script
    assert "### Duration and Bottlenecks" in report_script
    assert "Bottleneck Spotlight" in report_script
    assert "current workflow run jobs API" in report_script
    assert "Missing timing data" in report_script
    assert "omitted rather than estimated" in report_script
    assert "🏁" in report_script


def test_integration_report_uses_count_baseline_and_skip_drift_warnings() -> None:
    import json

    baseline_path = _runner.REPO_ROOT / "tests" / "baselines" / "integration-test-counts.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    report_script = _INTEGRATION_REPORT_SCRIPT.read_text(encoding="utf-8")

    assert baseline["schema_version"] == 1
    expected_suites = {
        "sd_smoke",
        "wd_py",
        "wd_js",
        "tc_smoke",
        "tc_tests",
        "wc_live",
        "wc_browser",
        "con_live",
        "cs_live",
    }
    assert set(baseline["suites"]) == expected_suites
    for key in expected_suites:
        entry = baseline["suites"][key]
        assert isinstance(entry["label"], str)
        assert isinstance(entry["tests"], int)
        assert entry["tests"] > 0
        assert isinstance(entry["skipped"], int)
        assert entry["skipped"] >= 0
        assert isinstance(entry["skip_tolerance"], int)
        assert entry["skip_tolerance"] >= 0
    assert "load_integration_baseline(" in report_script
    assert "format_count_delta(" in report_script
    assert 'return "" if delta == 0 else f" ({delta:+d})"' in report_script
    assert "def integration_drift_warnings(baseline, suite_counts, run_id):" in report_script
    assert 'E("GH_RUN_ID", "")' in report_script
    assert "non_test_client_skip_failures(" in report_script
    assert "skip_policy_failures" in report_script
    assert "#### Skip Policy Failures" in report_script
    assert "only IJT Test Client conformance" in report_script
    assert "sys.exit(1)" in report_script
    assert "tests/baselines/integration-test-counts.json" in report_script
    assert "### Warnings and Drift" in report_script
    assert "skip drift" in report_script
    assert "suite collection drift" in report_script
    assert "tests/tools/update_integration_baseline.py --run" in report_script
    assert "--suite {key}" in report_script


def test_update_integration_baseline_helper_is_guarded() -> None:
    helper = _runner.REPO_ROOT / "tests" / "tools" / "update_integration_baseline.py"
    text = helper.read_text(encoding="utf-8")
    module = _load_runner_at(
        "tests/tools/update_integration_baseline.py",
        "ijt_update_integration_baseline",
    )
    baseline = {
        "suites": {
            "wd_py": {
                "label": "Web Client - Docker Python Unit",
                "tests": 680,
                "skipped": 0,
            }
        }
    }

    assert "--run" in text
    assert "--suite" in text
    assert "--allow-decrease" in text
    assert "gh" in text
    assert "run" in text
    assert "download" in text
    assert "ARTIFACT_SPECS" in text
    assert "conclusion" in text
    assert "success" in text
    assert "System Tests — Live OPC UA, Browser, Docker, Conformance" in text
    assert "would decrease" in text
    assert "captured_from_run" in text
    assert set(module.ARTIFACT_SPECS) == {
        "sd_smoke",
        "wd_py",
        "wd_js",
        "tc_smoke",
        "tc_tests",
        "wc_live",
        "wc_browser",
        "con_live",
        "cs_live",
    }
    with pytest.raises(SystemExit, match="would decrease"):
        module._apply_update(
            baseline,
            {"tests": 679, "skipped": 0},
            run_id="123",
            captured_at="2026-05-11T20:33:34Z",
            suite="wd_py",
            allow_decrease=False,
        )
    updated = module._apply_update(
        baseline,
        {"tests": 681, "skipped": 0},
        run_id="123",
        captured_at="2026-05-11T20:33:34Z",
        suite="wd_py",
        allow_decrease=False,
    )
    assert updated["suites"]["wd_py"]["tests"] == 681
    assert updated["captured_from_run"] == 123


def test_web_client_live_suite_has_no_runtime_skip_calls() -> None:
    live_tests = (
        _runner.REPO_ROOT
        / "OPC_UA_Clients"
        / "Release2"
        / "IJT_Web_Client"
        / "tests"
        / "python"
        / "live"
        / "test_opcua_methods.py"
    ).read_text(encoding="utf-8")

    assert "pytest.skip(" not in live_tests
    assert "REGRESSION_RESULT_EVENT_JOINT" not in live_tests
    assert "REGRESSION_JOINT_" not in live_tests
    assert "_browse_tool_product_instance_uri" in live_tests
    assert "GetJointList must return at least one usable JointId" in live_tests
    assert "StartSelectedJoining can" in live_tests
    assert "ResultMetaData.ProcessingTimes" in live_tests


def test_console_client_live_suite_discovers_joint_ids_without_hidden_xfail() -> None:
    live_tests = (
        _runner.REPO_ROOT
        / "OPC_UA_Clients"
        / "Release2"
        / "IJT_Console_Client"
        / "tests"
        / "live"
        / "test_opcua_live_console.py"
    ).read_text(encoding="utf-8")

    assert "pytest.xfail(" not in live_tests
    assert "REGRESSION_JOINT_" not in live_tests
    assert "GetJointList must return at least one usable JointId" in live_tests
    assert "ProductInstanceUri must be configured on this server" in live_tests


def test_web_regression_discovers_product_and_joint_ids_before_joint_flow() -> None:
    source = (
        _runner.REPO_ROOT
        / "OPC_UA_Clients"
        / "Release2"
        / "IJT_Web_Client"
        / "scripts"
        / "run_regression.py"
    ).read_text(encoding="utf-8")

    assert 'send_recv("read product instance uri")' in source
    assert "PRODUCT_ID_OVERRIDE or discovered_product_id or DEFAULT_PRODUCT_ID" in source
    assert "GetJointList" in source
    assert "discovered_joint_ids" in source
    assert "JOINT_1_OVERRIDE = os.getenv" in source


def test_web_client_e2e_suite_has_no_runtime_skip_calls() -> None:
    e2e_root = (
        _runner.REPO_ROOT / "OPC_UA_Clients" / "Release2" / "IJT_Web_Client" / "tests" / "e2e"
    )
    offenders = [
        path.relative_to(e2e_root).as_posix()
        for path in e2e_root.glob("*.mjs")
        if "test.skip(" in path.read_text(encoding="utf-8")
    ]

    assert offenders == []


def test_ci_report_uses_declared_coverage_thresholds() -> None:
    report_script = _CI_REPORT_SCRIPT.read_text(encoding="utf-8")
    expected_header = (
        "| Component | Validation Scope | Tests Run | Skipped | Coverage / Threshold |"
    )

    assert expected_header in report_script
    assert "def cov(pct, threshold=None):" in report_script
    assert "cov(web_cov, 95)" in report_script
    assert "cov(web_js_cov, 95)" in report_script
    assert "cov(con_cov, 95)" in report_script
    assert "cov(nod_cov, 95)" in report_script
    assert "cov(cs_cov, 95)" in report_script
    assert "cov(tc_cov, 95)" in report_script
    assert "coverage_warnings" in report_script
    assert "### ⚠️ Coverage Threshold Warnings" in report_script


def test_ci_pre_commit_gate_is_required_and_reported() -> None:
    import yaml

    workflow_path = _runner.REPO_ROOT / ".github" / "workflows" / "ci.yml"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    workflow_text = workflow_path.read_text(encoding="utf-8")
    report_script = _CI_REPORT_SCRIPT.read_text(encoding="utf-8")

    assert "pre-commit" in workflow["jobs"]["report"]["needs"]
    assert "pre-commit" in workflow["jobs"]["all-required"]["needs"]
    pre_commit_env = workflow["jobs"]["pre-commit"]["env"]
    assert pre_commit_env["SKIP"] == (
        "eslint-node-client,css-node-client,eslint-web-client,stylelint-web-client"
    )
    install_steps = [
        step
        for step in workflow["jobs"]["pre-commit"]["steps"]
        if step.get("name") == "Install pre-commit and root test dependency"
    ]
    assert install_steps
    assert '"pre-commit==4.5.1" "pytest~=9.0"' in install_steps[0]["run"]
    pre_commit_steps = workflow["jobs"]["pre-commit"]["steps"]
    assert not any(step.get("uses", "").startswith("actions/cache") for step in pre_commit_steps)
    assert "PC_RESULT:       ${{ needs.pre-commit.result }}" in workflow_text
    assert 'pc_r = E("PC_RESULT"' in report_script
    assert "Pre-commit Hooks" in report_script
    assert (
        "${{ needs.pre-commit.result }}"
        in workflow["jobs"]["all-required"]["steps"][0]["env"]["RESULTS"]
    )


def test_workflows_do_not_depend_on_actions_cache_or_setup_caches() -> None:
    import yaml

    setup_actions = ("actions/setup-python@", "actions/setup-node@", "actions/setup-dotnet@")
    for workflow_path in (_runner.REPO_ROOT / ".github" / "workflows").glob("*.yml"):
        workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
        for job_name, job in workflow.get("jobs", {}).items():
            for step in job.get("steps", []):
                uses = step.get("uses", "")
                assert not uses.startswith("actions/cache"), (
                    f"{workflow_path.name} job '{job_name}' uses actions/cache. CI must not "
                    "depend on cache-service availability; install/restore commands are the "
                    "correctness gates."
                )
                if any(uses.startswith(action) for action in setup_actions):
                    step_with = step.get("with", {})
                    assert "cache" not in step_with, (
                        f"{workflow_path.name} job '{job_name}' uses built-in cache in {uses}. "
                        "Setup actions must only select toolchains; dependency install commands "
                        "own dependency resolution."
                    )
                    assert "cache-dependency-path" not in step_with


def test_ci_report_web_python_skip_budget_uses_expected_skip_identities() -> None:
    report_script = _CI_REPORT_SCRIPT.read_text(encoding="utf-8")

    assert '"web-client (Python)": 2' in report_script
    assert "expected_skip_names" in report_script
    assert (
        "test_required_static_asset_exists[node_modules/chart.js/dist/chart.umd.js]"
        in report_script
    )
    assert "test_eslint_passes" in report_script
    assert "unexpected skips detected" in report_script
    assert "missing_expected_names" in report_script
    assert "expected skips not observed" in report_script


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
