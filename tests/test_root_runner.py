from __future__ import annotations

import importlib.util
import json
import logging
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from defusedxml import ElementTree as ET


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


def test_python_dependency_security_floors_are_centralized() -> None:
    constraints = _runner.REPO_ROOT / "constraints.txt"
    assert constraints.exists(), "Add repo-wide Python security floors to constraints.txt"

    constraints_text = constraints.read_text(encoding="utf-8")
    assert "idna>=3.15" in constraints_text

    requirement_files = [
        _runner.CONSOLE_DIR / "requirements.txt",
        _runner.CONSOLE_DIR / "requirements-dev.txt",
        _runner.TEST_CLIENT_DIR / "requirements.txt",
        _runner.TEST_CLIENT_DIR / "requirements-dev.txt",
        _runner.WEB_CLIENT_DIR / "requirements.txt",
        _runner.WEB_CLIENT_DIR / "requirements-dev.txt",
        _runner.SERVER_DIR / "tests" / "requirements.txt",
    ]
    for req_file in requirement_files:
        text = req_file.read_text(encoding="utf-8")
        assert "constraints.txt" in text, f"{req_file} must document repo-wide constraints usage"
        assert not re.search(r"(?im)^idna\s*[<>=!~]", text), (
            f"{req_file} must not pin transitive idna directly; use constraints.txt"
        )


def test_python_requirement_installs_use_constraints_file() -> None:
    checked_files = [
        _runner.REPO_ROOT / "run_all_tests.py",
        _runner.SERVER_DIR / "run_all_tests.py",
        _runner.CONSOLE_DIR / "run_all_tests.py",
        _runner.CONSOLE_DIR / "setup_client.py",
        _runner.TEST_CLIENT_DIR / "run_all_tests.py",
        _runner.WEB_CLIENT_DIR / "run_all_tests.py",
        _runner.WEB_CLIENT_DIR / "setup_project.py",
        _runner.WEB_CLIENT_DIR / "scripts" / "venv_bootstrap.py",
        _runner.WEB_CLIENT_DIR / "Dockerfile",
        _runner.WEB_CLIENT_DIR / "docker-compose.yml",
        _runner.REPO_ROOT / ".github" / "docker" / "ijt-browser-ci" / "Dockerfile",
        _runner.REPO_ROOT / ".github" / "workflows" / "ci.yml",
        _runner.REPO_ROOT / ".github" / "workflows" / "integration.yml",
        _runner.REPO_ROOT / ".github" / "workflows" / "build-browser-ci-image.yml",
    ]
    missing: list[str] = []
    for path in checked_files:
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            stripped = line.strip()
            if (
                stripped.startswith(("_skip(", "result.note =", "log.", "logger.", "print("))
                or "not installed" in stripped
                or "Install:" in stripped
            ):
                continue
            starts_pip_command = (
                stripped.startswith(
                    (
                        "pip install",
                        "python -m pip install",
                        "RUN pip install",
                        "RUN python -m pip install",
                        "&& pip install",
                        "&& python -m pip install",
                    )
                )
                or stripped in {'"pip",', "'pip',"}
                or '"pip", "install"' in stripped
                or "'pip', 'install'" in stripped
            )
            if not starts_pip_command:
                continue
            if stripped in {'"pip",', "'pip',"}:
                block_lines = []
                for command_line in lines[index : index + 20]:
                    block_lines.append(command_line)
                    if command_line.strip().startswith("]"):
                        break
                block = "\n".join(block_lines)
            else:
                block = "\n".join(lines[index : index + 20])
            if "install" not in block:
                continue
            if "-r" not in block and "requirements" not in block and "pip_package" not in block:
                package_names = (
                    "asyncua_spec",
                    "asyncua>=",
                    '"cryptography"',
                    "'cryptography'",
                    '"pyOpenSSL"',
                    "'pyOpenSSL'",
                )
                if not any(token in block for token in package_names):
                    continue
            installs_dependencies = any(
                token in block
                for token in (
                    "requirements.txt",
                    "requirements-dev.txt",
                    '"-r"',
                    "'-r'",
                    "pip_package",
                    "asyncua_spec",
                    "asyncua>=",
                    '"cryptography"',
                    "'cryptography'",
                    '"pyOpenSSL"',
                    "'pyOpenSSL'",
                )
            )
            if (
                installs_dependencies
                and "constraints.txt" not in block
                and "PYTHON_CONSTRAINTS" not in block
                and "_pip_constraint_args" not in block
            ):
                rel_path = path.relative_to(_runner.REPO_ROOT)
                missing.append(f"{rel_path}:{index + 1}")

    assert not missing, (
        "Python dependency install surfaces must use repo-wide constraints.txt. "
        "Add -c <repo>/constraints.txt or _pip_constraint_args() at: " + ", ".join(missing)
    )


def test_test_client_pyright_resolves_reporting_scripts() -> None:
    pyproject = tomllib.loads(
        (_runner.TEST_CLIENT_DIR / "pyproject.toml").read_text(encoding="utf-8")
    )

    assert "scripts" in pyproject["tool"]["pyright"]["extraPaths"]


def test_negative_service_tests_use_request_helpers() -> None:
    add_nodes_tests = (
        _runner.TEST_CLIENT_DIR / "conformance" / "test_joining_system_base.py"
    ).read_text(encoding="utf-8")
    delete_nodes_tests = (
        _runner.TEST_CLIENT_DIR / "conformance" / "test_result_management.py"
    ).read_text(encoding="utf-8")

    assert "ua.ExpandedNodeId(ua.NodeId(" not in add_nodes_tests
    assert "uaclient.delete_nodes([" not in delete_nodes_tests


def test_local_ci_mode_uses_isolated_python_client_venvs() -> None:
    root_runner = (_runner.REPO_ROOT / "run_all_tests.py").read_text(encoding="utf-8")
    console_runner = (_runner.CONSOLE_DIR / "run_all_tests.py").read_text(encoding="utf-8")
    test_client_runner = (_runner.TEST_CLIENT_DIR / "run_all_tests.py").read_text(encoding="utf-8")
    web_runner = (_runner.WEB_CLIENT_DIR / "run_all_tests.py").read_text(encoding="utf-8")
    web_setup = (_runner.WEB_CLIENT_DIR / "setup_project.py").read_text(encoding="utf-8")

    for runner_source in (console_runner, test_client_runner, web_runner):
        assert ".venv_ci" in runner_source
        assert "GITHUB_ACTIONS" in runner_source
        assert "_ENV_IS_PRE_ISOLATED" in runner_source

    assert "if not _ENV_IS_PRE_ISOLATED and not _inside_venv()" in web_runner
    assert "if not IS_CI and not IS_DOCKER and not _inside_venv()" not in web_runner
    assert "skip venv relaunch" not in root_runner
    assert "_ENV_IS_PRE_ISOLATED = IS_DOCKER or IS_GITHUB_ACTIONS" in web_setup
    assert "if _ENV_IS_PRE_ISOLATED:" in web_setup


def test_live_clients_preserve_legacy_then_data_type_loader_order() -> None:
    console_client = (_runner.CONSOLE_DIR / "opcua_client.py").read_text(encoding="utf-8")
    web_connection = (_runner.WEB_CLIENT_DIR / "src" / "python" / "connection.py").read_text(
        encoding="utf-8"
    )
    web_live = (
        _runner.WEB_CLIENT_DIR / "tests" / "python" / "live" / "test_opcua_methods.py"
    ).read_text(encoding="utf-8")
    test_client_conftest = (_runner.TEST_CLIENT_DIR / "conftest.py").read_text(encoding="utf-8")

    assert '_load_ijt_type_definitions(self.client, "console client")' in console_client
    assert '_load_ijt_type_definitions(self.client, "method client")' in web_connection
    assert (
        '_load_ijt_type_definitions(self.subscription_client, "subscription client")'
        in web_connection
    )

    web_legacy_loader = web_live.index("await c.load_type_definitions()")
    web_data_loader = web_live.index("await c.load_data_type_definitions()")
    assert web_legacy_loader < web_data_loader
    assert "OPC Binary dictionary" in web_live
    assert "load_type_definitions is deprecated upstream and dispatches" not in web_live

    test_client_legacy_loader = test_client_conftest.index("await client.load_type_definitions()")
    test_client_data_loader = test_client_conftest.index(
        "await client.load_data_type_definitions()"
    )
    assert test_client_legacy_loader < test_client_data_loader
    assert "OPC Binary dictionary" in test_client_conftest


def test_live_clients_do_not_duplicate_modern_loader_calls() -> None:
    """Guard against duplicate ``load_data_type_definitions()`` invocations.

    asyncua's modern loader walks ~200 sequential nodes; calling it twice on
    the same client adds avoidable CI latency.  After the IJT compatibility
    bridge (``_load_ijt_type_definitions``) loads types once per client,
    subsequent standalone ``load_data_type_definitions()`` calls must be
    removed. This contract prevents a regression to the previous duplicate-call
    pattern.
    """
    console_client = (_runner.CONSOLE_DIR / "opcua_client.py").read_text(encoding="utf-8")
    web_connection = (_runner.WEB_CLIENT_DIR / "src" / "python" / "connection.py").read_text(
        encoding="utf-8"
    )
    web_live = (
        _runner.WEB_CLIENT_DIR / "tests" / "python" / "live" / "test_opcua_methods.py"
    ).read_text(encoding="utf-8")
    test_client_conftest = (_runner.TEST_CLIENT_DIR / "conftest.py").read_text(encoding="utf-8")

    # Console runtime: exactly one bridge call (in connect()).  No standalone
    # ``self.client.load_data_type_definitions()`` may remain after the bridge.
    assert console_client.count("_load_ijt_type_definitions(self.client") == 1
    assert "await self.client.load_data_type_definitions()" not in console_client

    # Web runtime: two bridge calls (method client + subscription client),
    # no standalone modern-loader calls on either client.
    assert web_connection.count("await _load_ijt_type_definitions(") == 2
    assert "await asyncio.wait_for(self.client.load_data_type_definitions()" not in web_connection
    stale_subscription_loader = (
        "await asyncio.wait_for(\n"
        "                        self.subscription_client.load_data_type_definitions"
    )
    assert stale_subscription_loader not in web_connection

    # The exact legacy+modern loader count is intentional here: asyncua 1.2b2
    # still needs both loader APIs for generated IJT types, while duplicates
    # reopen the old slow/flaky fixture path.
    assert web_live.count("await c.load_type_definitions()") == 1
    assert web_live.count("await c.load_data_type_definitions()") == 1

    # Test Client conftest: exactly one legacy + one modern call in the
    # session-scoped client fixture.
    assert test_client_conftest.count("await client.load_type_definitions()") == 1
    assert test_client_conftest.count("await client.load_data_type_definitions()") == 1


def test_opcua_security_jobs_do_not_force_compose_rebuilds() -> None:
    workflow = _runner.REPO_ROOT / ".github" / "workflows" / "integration.yml"
    workflow_text = workflow.read_text(encoding="utf-8")
    import yaml

    workflow_data = yaml.safe_load(workflow_text)
    security_jobs = {
        name: job
        for name, job in workflow_data["jobs"].items()
        if any(
            "run_all_tests.py --opcua-security" in str(step.get("run", ""))
            for step in job.get("steps", [])
        )
    }

    assert 'IJT_DOCKER_COMPOSE_BUILD: "1"' not in workflow_text
    assert {"csharp-client-opcua-security", "console-client-opcua-security"} <= set(security_jobs)
    for job_name, job in security_jobs.items():
        run_steps = [
            step
            for step in job.get("steps", [])
            if "run_all_tests.py --opcua-security" in str(step.get("run", ""))
        ]
        assert run_steps, job_name
        assert all(step.get("env", {}).get("IJT_DOCKER_COMPOSE_BUILD") == "0" for step in run_steps)
    assert "docker compose builds the image once when needed" in workflow_text
    assert "Do not force" in workflow_text


def test_opcua_security_docker_rebuilds_when_linux_zip_is_newer() -> None:
    csharp_fixture = (
        _runner.CSHARP_DIR / "Tests" / "IJT_CSharp_Client.Tests" / "OpcUaServerFixture.cs"
    ).read_text(encoding="utf-8")
    console_fixture = (_runner.CONSOLE_DIR / "tests" / "live" / "conftest.py").read_text(
        encoding="utf-8"
    )
    docker_freshness_source = (_runner.CONSOLE_DIR / "docker_freshness.py").read_text(
        encoding="utf-8"
    )

    assert "ShouldBuildDockerImage(dockerExe, composeDir)" in csharp_fixture
    assert "DockerImageIsMissingOrOlderThanSimulatorZip" in csharp_fixture
    assert "OPC_UA_IJT_Server_Simulator_Linux.zip" in csharp_fixture
    assert "docker image inspect" not in csharp_fixture
    assert 'inspect.StartInfo.ArgumentList.Add("image");' in csharp_fixture
    assert 'inspect.StartInfo.ArgumentList.Add("inspect");' in csharp_fixture
    assert "File.GetLastWriteTimeUtc(zipPath) > imageCreatedUtc.Value.UtcDateTime" in csharp_fixture

    # C# scales compose launch timeout when freshness asks Docker to build.
    # Compose launch timeouts use two named ``--wait-timeout`` budgets
    # (120s warm / 300s cold), so the constants are derived rather than
    # literal magic numbers. The earlier 30s warm WaitForExit was unsafe
    # because the server compose healthcheck alone needs roughly 80s.
    assert "DockerComposeWarmWaitTimeoutSeconds = 120" in csharp_fixture
    assert "DockerComposeColdWaitTimeoutSeconds = 300" in csharp_fixture
    assert (
        "DockerComposeCachedUpTimeoutMs = (DockerComposeWarmWaitTimeoutSeconds + 30) * 1000"
        in csharp_fixture
    )
    assert (
        "DockerComposeBuildUpTimeoutMs = (DockerComposeColdWaitTimeoutSeconds + 60) * 1000"
        in csharp_fixture
    )
    assert "var timeoutMs = DockerComposeUpTimeoutMs(wantsBuild);" in csharp_fixture
    assert "if (!r.WaitForExit(timeoutMs))" in csharp_fixture
    assert "KillProcessTree(r);" in csharp_fixture
    assert "r.BeginOutputReadLine();" in csharp_fixture
    assert "r.BeginErrorReadLine();" in csharp_fixture
    # The unsafe 30s WaitForExit happy-path is forbidden.
    assert "r.WaitForExit(30_000);\n            if (r.ExitCode == 0)" not in csharp_fixture
    # Compose ``--wait`` must be wired into the launch invocation.
    assert 'startInfo.ArgumentList.Add("--wait");' in csharp_fixture

    # Console fixture delegates to the shared, dependency-free helper module
    # so this regression test never has to import cryptography / asyncua.
    assert "_should_build_docker_image(docker)" in console_fixture
    assert "_SERVER_LINUX_ZIP = _SERVER_RELEASE2 /" in console_fixture
    assert '"OPC_UA_IJT_Server_Simulator_Linux.zip"' in console_fixture
    assert "from docker_freshness import is_image_stale" in console_fixture
    assert "is_image_stale(" in console_fixture

    # Helper module owns the actual Docker freshness contract.
    assert "def parse_docker_created_timestamp(value: str)" in docker_freshness_source
    assert "def is_image_stale(" in docker_freshness_source
    assert "reference_path.stat().st_mtime > image_created" in docker_freshness_source
    assert '[docker_exe, "image", "inspect", image, "--format", "{{.Created}}"]' in (
        docker_freshness_source
    )


def test_console_docker_created_timestamp_parses_nanosecond_precision() -> None:
    module = _load_runner_at(
        "OPC_UA_Clients/Release2/IJT_Console_Client/docker_freshness.py",
        "ijt_console_docker_freshness",
    )

    timestamp = module.parse_docker_created_timestamp("2026-05-21T13:41:19.204798168Z")

    assert timestamp is not None
    assert timestamp > 0
    assert module.parse_docker_created_timestamp("") is None
    assert module.parse_docker_created_timestamp("not-a-timestamp") is None


def test_managed_console_opcua_security_does_not_reuse_stale_server_port() -> None:
    fixture_source = (_runner.CONSOLE_DIR / "tests" / "live" / "conftest.py").read_text(
        encoding="utf-8"
    )

    assert "def _isolated_server_requested()" in fixture_source
    assert "IJT_OPCUA_SECURITY_TARGET" in fixture_source
    assert "def _stop_docker_containers_publishing_port(port: int)" in fixture_source
    assert "def _kill_process_on_port(port: int)" in fixture_source
    assert "_stop_docker_containers_publishing_port(port)" in fixture_source
    assert "if isolated_server and _port_open(host, port):" in fixture_source
    assert "_kill_process_on_port(port)" in fixture_source
    assert "could not be cleared for an isolated managed run" in fixture_source


def test_csharp_fixture_clears_docker_port_before_native_kill() -> None:
    fixture_source = (
        _runner.CSHARP_DIR / "Tests" / "IJT_CSharp_Client.Tests" / "OpcUaServerFixture.cs"
    ).read_text(encoding="utf-8")

    assert "StopDockerContainersPublishingPort(port)" in fixture_source
    assert "FindDockerExecutable()" in fixture_source
    assert 'FindInPath("docker.exe")' in fixture_source
    assert "ps --filter publish={port}" in fixture_source
    assert 'Environment.GetEnvironmentVariable("IJT_OPCUA_SECURITY_SUT")' in fixture_source
    assert '"linux"' in fixture_source


def test_dotnet_runners_disable_worker_reuse() -> None:
    csharp_runner = (_runner.CSHARP_DIR / "run_all_tests.py").read_text(encoding="utf-8")
    root_runner = (_runner.REPO_ROOT / "run_all_tests.py").read_text(encoding="utf-8")

    for source in (root_runner, csharp_runner):
        assert "MSBUILDDISABLENODEREUSE" in source
        assert "UseSharedCompilation" in source


def test_parse_suite_counts_keeps_failed_pytest_counts() -> None:
    output = "======================= 2 failed, 795 passed in 22.26s ========================"

    assert _runner._parse_suite_counts(output) == "2 failed, 795 passed"


def test_parse_suite_counts_keeps_skipped_pytest_counts() -> None:
    output = "================= 713 passed, 140 skipped in 88.01s (0:01:28) ================="

    assert _runner._parse_suite_counts(output) == "713 passed, 140 skipped"


def test_parse_suite_counts_keeps_web_python_and_js_counts() -> None:
    output = """
    ============================ 707 passed in 48.90s =============================
     Test Files  32 passed (32)
          Tests  634 passed (634)
    """

    assert _runner._parse_suite_counts(output) == "707 passed (py), 634 passed (js)"


def test_parse_suite_counts_handles_static_check_summary() -> None:
    output = "Result: PASS   Checks: 7 passed, 0 failed, 2 skipped"

    assert _runner._parse_suite_counts(output) == "7 passed, 2 skipped"


def test_parse_suite_counts_handles_fraction_smoke_summary() -> None:
    output = "  10/10 passed"

    assert _runner._parse_suite_counts(output) == "10 passed"


def test_parse_suite_counts_handles_playwright_failure_summary() -> None:
    output = """
      1 failed
        [chromium] › tests/e2e/features.spec.ts:12:1 › feature flow
      64 passed (2.0m)
    """

    assert _runner._parse_suite_counts(output) == "1 failed, 64 passed"


def test_parse_suite_counts_handles_ansi_playwright_summary() -> None:
    output = "\x1b[32m  65 passed\x1b[39m (2.0m)"

    assert _runner._parse_suite_counts(output) == "65 passed"


def test_parse_suite_counts_handles_single_child_runner_check() -> None:
    output = """
    TEST SUMMARY
    =================================================================
      [PASS]  docker-smoke                        exit=0  14.5s

      Total time: 24.0s
      ALL TESTS PASSED
    """

    assert _runner._parse_suite_counts(output) == "1 check passed"


def test_parse_suite_counts_handles_multiple_child_runner_checks() -> None:
    output = """
    TEST SUMMARY
    =================================================================
      [PASS]  pip-install                         exit=0  0.2s
      [PASS]  playwright-install                  exit=0  0.4s
      [PASS]  playwright-features                 exit=0  122.6s
    """

    assert _runner._parse_suite_counts(output) == "3 checks passed"


def test_parse_suite_counts_handles_mixed_child_runner_checks() -> None:
    output = """
    TEST SUMMARY
    =================================================================
      [PASS]  pip-install                         exit=0  0.2s
      [FAIL]  docker-smoke                        exit=1  14.5s
      [PASS]  docker-cleanup                      exit=0  1.0s
    """

    assert _runner._parse_suite_counts(output) == "2 checks passed, 1 check failed"


def test_count_tests_from_detail_sums_only_test_outcomes() -> None:
    detail = "707 passed (py), 634 passed (js), 2 warnings, 1 deselected"

    assert _runner._count_tests_from_detail(detail) == 1341


def test_check_counts_do_not_contribute_to_test_totals() -> None:
    assert _runner._count_tests_from_detail("1 check passed") == 0
    assert not _runner._test_outcome_counts_from_detail("2 checks passed, 1 check failed")


def test_count_tests_from_results_ignores_non_test_notes() -> None:
    results = [
        _runner.SuiteResult(
            "repo-static-gitignore-check",
            True,
            notes=["586 source files checked"],
        ),
        _runner.SuiteResult("web-client-static", True, counts="707 passed (py), 634 passed (js)"),
        _runner.SuiteResult("web-client-e2e-features", False, counts="1 failed, 64 passed"),
    ]

    assert _runner._count_tests_from_results(results) == 1406


def test_total_test_outcomes_show_pass_fail_skip_breakdown() -> None:
    results = [
        _runner.SuiteResult("web-client-static", True, counts="707 passed (py), 634 passed (js)"),
        _runner.SuiteResult("web-client-e2e-features", False, counts="1 failed, 64 passed"),
        _runner.SuiteResult("test-client-live-conformance", True, counts="713 passed, 140 skipped"),
    ]

    totals = _runner._test_outcome_counts_from_results(results)

    assert _runner._format_total_test_outcomes(totals) == (
        "2,259 total tests; 2,118 passed, 1 failed, 0 errors, 140 skipped"
    )


def test_root_runner_writes_timing_artifacts(monkeypatch) -> None:
    scratch = _runner.REPO_ROOT / "test-results" / "root-runner-timing-unit"
    if scratch.exists():
        shutil.rmtree(scratch)
    monkeypatch.setattr(_runner, "ROOT", scratch)
    result = _runner.SuiteResult(
        "repo-static-gitignore-check",
        True,
        duration=1.25,
        notes=["ok"],
    )

    try:
        _runner._write_timing_artifacts([result], 2.5, "suite:repo-static-gitignore-check")

        aggregate_path = scratch / "test-results" / "timing" / "timing-aggregate.json"
        per_job_path = scratch / "test-results" / "timing" / "jobs" / "01-local-root-runner.json"
        payload = json.loads(aggregate_path.read_text(encoding="utf-8"))
        per_job = json.loads(per_job_path.read_text(encoding="utf-8"))
        assert payload["schema_version"] == 1
        assert payload["source"]["mode"] == "suite:repo-static-gitignore-check"
        assert payload["jobs"][0]["stages"][0]["name"] == "repo-static-gitignore-check"
        assert per_job["jobs"][0]["name"] == "Local Root Runner"
    finally:
        if scratch.exists():
            shutil.rmtree(scratch)


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
                "opcua-security",
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
        "opcua-security",
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
        "phase2-opcua-security",
        "phase2-web-live",
        "phase2-web-compatibility",
    }
    assert all(
        isinstance(spec.group, _runner.SuiteGroup) for spec in _runner.SUITE_REGISTRY.values()
    )


def test_suite_registry_has_no_duplicate_ids() -> None:
    required_suite_ids = {
        "repo-static-gitignore-check",
        "repo-static-markdown-leak-check",
        "server-static",
        "node-client-static",
        "test-client-static",
        "console-client-static",
        "web-client-static",
        "csharp-client-static",
        "server-smoke",
        "server-linux-package-smoke",
        "csharp-client-live",
        "console-client-live",
        "csharp-client-opcua-security-windows",
        "csharp-client-opcua-security-linux",
        "console-client-opcua-security-windows",
        "console-client-opcua-security-linux",
        "test-client-live-conformance",
        "web-client-live-opcua-direct",
        "web-client-live-websocket-api",
        "web-client-live-websocket-connection",
        "web-client-e2e-smoke",
        "web-client-e2e-features",
        "web-client-e2e-regression",
        "web-client-docker-smoke",
        "web-client-compatibility-smoke",
    }
    registered_ids = set(_runner.SUITE_REGISTRY)

    assert required_suite_ids <= registered_ids
    assert len(registered_ids) == len(_runner.SUITE_REGISTRY)
    assert all(
        suite_id and suite_id == spec.id for suite_id, spec in _runner.SUITE_REGISTRY.items()
    )


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


def test_opcua_security_suites_are_opt_in_phase2_suites() -> None:
    opcua_security_suite_ids = {
        "csharp-client-opcua-security-windows",
        "csharp-client-opcua-security-linux",
        "console-client-opcua-security-windows",
        "console-client-opcua-security-linux",
    }

    assert opcua_security_suite_ids.isdisjoint(_runner.phase2_specs())
    assert opcua_security_suite_ids <= set(_runner.phase2_specs(include_opcua_security=True))


def test_opcua_security_suites_delegate_to_sub_runners(monkeypatch) -> None:
    calls: list[dict] = []

    def _fake_delegate_to_runner(**kwargs):
        calls.append(kwargs)
        return _runner.SuiteResult(kwargs["name"], True, 0.0)

    monkeypatch.setattr(_runner, "_delegate_to_runner", _fake_delegate_to_runner)

    results = [
        _runner._suite_csharp_opcua_security_windows(),
        _runner._suite_csharp_opcua_security_linux(),
        _runner._suite_console_opcua_security_windows(),
        _runner._suite_console_opcua_security_linux(),
    ]

    assert all(result.ok for result in results)
    assert [call["name"] for call in calls] == [
        "csharp-client-opcua-security-windows",
        "csharp-client-opcua-security-linux",
        "console-client-opcua-security-windows",
        "console-client-opcua-security-linux",
    ]
    assert [call["phase_args"][:5] for call in calls] == [
        [
            "--opcua-security",
            "--opcua-security-target",
            "csharp-client-opcua-security-windows",
            "--opcua-security-sut",
            "windows",
        ],
        [
            "--opcua-security",
            "--opcua-security-target",
            "csharp-client-opcua-security-linux",
            "--opcua-security-sut",
            "linux",
        ],
        [
            "--opcua-security",
            "--opcua-security-target",
            "console-client-opcua-security-windows",
            "--opcua-security-sut",
            "windows",
        ],
        [
            "--opcua-security",
            "--opcua-security-target",
            "console-client-opcua-security-linux",
            "--opcua-security-sut",
            "linux",
        ],
    ]
    assert calls[0]["extra_env"]["OPCUA_SERVER_PORT"] == str(
        _runner.OPCUA_SERVER_PORT_CSHARP_OPCUA_SECURITY_WINDOWS
    )
    assert calls[0]["extra_env"]["IJT_SERVER_URL"].endswith(":40475")
    assert calls[1]["extra_env"]["IJT_DOCKER_COMPOSE_BUILD"] == "0"
    assert calls[2]["extra_env"]["OPCUA_SERVER_URL"].endswith(":40477")
    assert calls[3]["extra_env"]["IJT_DOCKER_COMPOSE_BUILD"] == "0"
    assert all(call["timeout"] == 1200 for call in calls)


def test_csharp_client_and_generated_types_share_default_opc_foundation_version() -> None:
    client_project = (
        _runner.REPO_ROOT
        / "OPC_UA_Clients"
        / "Release2"
        / "IJT_CSharp_Client"
        / "IJT_CSharp_Client.csproj"
    )
    types_props = (
        _runner.REPO_ROOT
        / "OPC_UA_Clients"
        / "Release2"
        / "IJT_CSharp_Client"
        / "Types"
        / "Directory.Build.props"
    )

    client_root = ET.parse(client_project).getroot()
    types_root = ET.parse(types_props).getroot()
    client_version = next(
        ref.attrib["Version"]
        for ref in client_root.iter("PackageReference")
        if ref.attrib.get("Include") == "OPCFoundation.NetStandard.Opc.Ua"
    )
    default_types_version = next(
        prop.text
        for prop in types_root.iter("OpcFoundationVersion")
        if prop.attrib.get("Condition") == "'$(OpcUaClientOnly)' != 'true'"
    )

    assert default_types_version == client_version


def test_csharp_lockfiles_track_generated_type_opc_foundation_ranges() -> None:
    csharp_root = _runner.REPO_ROOT / "OPC_UA_Clients" / "Release2" / "IJT_CSharp_Client"
    types_props = csharp_root / "Types" / "Directory.Build.props"
    default_types_version = next(
        prop.text
        for prop in ET.parse(types_props).getroot().iter("OpcFoundationVersion")
        if prop.attrib.get("Condition") == "'$(OpcUaClientOnly)' != 'true'"
    )
    expected_range = f"[{default_types_version}, )"
    generated_type_projects = {
        "uamodel.amb",
        "uamodel.di",
        "uamodel.ia",
        "uamodel.ijtbase",
        "uamodel.ijttightening",
        "uamodel.machinery",
        "uamodel.machineryresult",
    }
    lock_paths = [
        csharp_root / "packages.lock.json",
        csharp_root / "Tests" / "IJT_CSharp_Client.Tests" / "packages.lock.json",
    ]

    for lock_path in lock_paths:
        lock_data = json.loads(lock_path.read_text(encoding="utf-8"))
        dependencies = lock_data["dependencies"]["net10.0"]
        for project_name in generated_type_projects:
            core_range = dependencies[project_name]["dependencies"][
                "OPCFoundation.NetStandard.Opc.Ua.Core"
            ]
            assert core_range == expected_range, f"{lock_path}: {project_name}"


def test_csharp_security_x509_user_role_is_merged_after_tryadd() -> None:
    fixture = (
        _runner.REPO_ROOT
        / "OPC_UA_Clients"
        / "Release2"
        / "IJT_CSharp_Client"
        / "Tests"
        / "IJT_CSharp_Client.Tests"
        / "OpcUaServerFixture.cs"
    ).read_text(encoding="utf-8")

    assert 'EnsureUserHasRole(configuredUsers["user1"], "SecurityAdmin");' in fixture
    assert 'configuredUsers["user1"]["x509ThumbprintSha1Hex"]' in fixture
    assert 'TryAdd("user1", User("user1", "password", ["SecurityAdmin"]' not in fixture


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
    assert calls[5]["timeout"] == _runner.WEB_CLIENT_E2E_REGRESSION_TIMEOUT
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


def test_print_summary_reports_suite_and_test_totals(capsys) -> None:
    results = [
        _runner.SuiteResult("server-smoke", True, duration=1.0, counts="10 passed"),
        _runner.SuiteResult("web-client-docker-smoke", True, duration=2.0),
        _runner.SuiteResult(
            "csharp-client-opcua-security-windows",
            True,
            duration=2.5,
            counts="9 passed",
        ),
        _runner.SuiteResult(
            "test-client-live-conformance",
            True,
            duration=3.0,
            counts="713 passed, 140 skipped",
        ),
    ]

    rc = _runner._print_summary(results, total_time=6.0)

    output = capsys.readouterr().out
    assert rc == 0
    assert "Server - Native smoke" in output
    assert "10 passed" in output
    assert "Web Client - Docker image smoke" in output
    assert "C# OPC UA Security - Windows" in output
    assert "Not reported" in output
    assert "4 total suites; 4 passed, 0 failed, 0 skipped" in output
    assert "872 total tests; 732 passed, 0 failed, 0 errors, 140 skipped" in output


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
    assert captured["MSBUILDDISABLENODEREUSE"] == "1"
    assert captured["UseSharedCompilation"] == "false"
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
        assert job["timeout-minutes"] == 45, (
            "live-webclient-browser must leave overhead above the root runner's "
            "30-minute web-client-e2e-regression timeout; otherwise GitHub can "
            "kill the job before the runner emits diagnostics and artifacts."
        )
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

        # Image identity is provided by the resolve-browser-image job via
        # `needs:` + an explicit output expression. The legacy in-job resolver
        # step (which polled GHCR tags with a 10-minute blind budget and
        # raced the producer workflow) is intentionally gone.
        needs = job.get("needs")
        if isinstance(needs, str):
            needs = [needs]
        assert "resolve-browser-image" in (needs or []), (
            "live-webclient-browser must declare `needs: resolve-browser-image` "
            "so image identity flows through one execution DAG, not through "
            "cross-workflow tag polling."
        )

        steps = job["steps"]
        step_names = [step.get("name") or step.get("uses", "") for step in steps]
        assert "Resolve IJT Browser CI image reference (digest-qualified)" not in step_names, (
            "The in-job resolver step was deleted in the Browser CI "
            "synchronization commit. Image identity now comes from "
            "needs.resolve-browser-image.outputs.image_ref."
        )
        assert "Pull IJT Browser CI image (3-attempt retry)" not in step_names, (
            "The 3-attempt retry pull step is deleted; resolve-browser-image "
            "already pulled and validated the digest on its runner, so the "
            "matrix job only needs a per-runner cache warm-up pull."
        )

        login_index = next(
            index
            for index, step in enumerate(steps)
            if step.get("uses", "").startswith("docker/login-action@")
        )
        pull_index = step_names.index(
            "Pull IJT Browser CI image (digest from resolve-browser-image)"
        )
        assert login_index < pull_index, (
            "docker login must happen before the per-runner cache warm-up pull."
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

        pull_step = steps[pull_index]
        pull_body = pull_step["run"]
        # Cache warm-up pull must consume the resolver's digest-qualified
        # image_ref via env, never re-derive it from a tag.
        assert (
            pull_step.get("env", {}).get("IMG")
            == "${{ needs.resolve-browser-image.outputs.image_ref }}"
        ), "Pull step must source IMG from the resolve-browser-image job output."
        assert "@sha256:[0-9a-f]{64}" in pull_body, (
            "Pull step must guard that IMG is digest-qualified."
        )
        assert 'docker pull "$IMG"' in pull_body

        login_step = next(
            step for step in steps if step.get("uses", "").startswith("docker/login-action@")
        )
        assert login_step.get("with", {}).get("registry") == "ghcr.io"

        run_step = next(
            step
            for step in steps
            if step.get("name") == "Run Web Client browser e2e suite (offline, --network=none)"
        )
        # The image fed to docker run is the resolver's job output. Critical
        # invariant: it does not come from a step-output produced inside this
        # job (which is what enabled the historical race).
        assert (
            run_step.get("env", {}).get("IMG")
            == "${{ needs.resolve-browser-image.outputs.image_ref }}"
        ), (
            "Run step's IMG must come from needs.resolve-browser-image.outputs.image_ref, "
            "not from a step-output side effect."
        )
        run_body = run_step["run"]
        assert "docker run" in run_body
        assert "--network=none" in run_body
        assert '--user "$(id -u):$(id -g)"' in run_body
        assert '-v "${GITHUB_WORKSPACE}:/workspace"' in run_body
        assert "PIP_NO_INDEX=1" in run_body
        assert "npm_config_offline=true" in run_body
        assert "IS_DOCKER=true" in run_body, (
            "The in-container Web runner must use the baked Docker Python "
            "environment instead of creating a local CI-mode .venv."
        )
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
    assert 'REPORT_JOB_NAME: "📋 System Test Report"' in workflow
    assert "def job_durations(path):" in report_script
    assert "excluding this report job" in report_script
    assert "name == report_job_name" in report_script
    assert "### ⏱️ Performance Hotspots" in report_script
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
    assert "must_not_skip_failures(" in report_script
    assert "skip_policy_failures" in report_script
    assert "#### Skip Policy Failures" in report_script
    assert "smoke and unit suites" in report_script
    assert "sys.exit(1)" in report_script
    assert "tests/baselines/integration-test-counts.json" in report_script
    assert "### ⚠️ Warnings and Drift" in report_script
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
        "| Component | Validation Scope | Test Cases | Skipped | Coverage / Threshold |"
    )

    assert expected_header in report_script
    assert "def cov(pct, threshold=None, job_result=None):" in report_script
    assert "cov(web_cov, 95, web_py_r)" in report_script
    assert "cov(web_js_cov, 95, web_js_r)" in report_script
    assert "cov(con_cov, 95, con_r)" in report_script
    assert "cov(nod_cov, 95, nod_r)" in report_script
    assert "cov(cs_cov, 95, cs_u_r)" in report_script
    assert "cov(tc_cov, 95, tc_r)" in report_script
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
        if step.get("name") == "Install pre-commit and root test dependencies"
    ]
    assert install_steps
    install_run = install_steps[0]["run"]
    assert '"pre-commit==4.5.1"' in install_run
    assert "-r" in install_run and "tests/requirements.txt" in install_run
    pre_commit_steps = workflow["jobs"]["pre-commit"]["steps"]
    assert not any(step.get("uses", "").startswith("actions/cache") for step in pre_commit_steps)
    config_path = _runner.REPO_ROOT / ".pre-commit-config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    local_hooks = next(repo for repo in config["repos"] if repo["repo"] == "local")["hooks"]
    workflow_guard = next(hook for hook in local_hooks if hook["id"] == "workflow-policy-guard")
    assert "^\\.pre-commit-config\\.yaml$" in workflow_guard["files"]
    assert "^tests/requirements\\.txt$" in workflow_guard["files"]
    assert "PC_RESULT:       ${{ needs.pre-commit.result }}" in workflow_text
    assert 'pc_r = E("PC_RESULT"' in report_script
    assert "Pre-commit Hooks" in report_script
    assert (
        "${{ needs.pre-commit.result }}"
        in workflow["jobs"]["all-required"]["steps"][0]["env"]["RESULTS"]
    )


def test_pre_commit_bandit_covers_python_surfaces() -> None:
    import yaml

    config_path = _runner.REPO_ROOT / ".pre-commit-config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    bandit_repo = next(
        repo for repo in config["repos"] if repo["repo"] == "https://github.com/PyCQA/bandit"
    )
    hooks = bandit_repo["hooks"]
    assert len(hooks) == 1
    hook = hooks[0]
    args = hook["args"]

    assert hook["name"] == "Bandit (Python SAST, Medium+)"
    assert hook["pass_filenames"] is False
    assert hook["files"] == r"(\.py$|^pyproject\.toml$|^\.pre-commit-config\.yaml$)"
    assert "-r" in args and "." in args
    assert "-c" in args and "pyproject.toml" in args
    assert "--severity-level" in args and "medium" in args

    root_pyproject = tomllib.loads((_runner.REPO_ROOT / "pyproject.toml").read_text())
    bandit_config = root_pyproject["tool"]["bandit"]
    exclude_dirs = set(bandit_config["exclude_dirs"])
    expected_globs = {
        "*/.venv/*",
        "*\\.venv\\*",
        "*/node_modules/*",
        "*\\node_modules\\*",
        "*/tmp/*",
        "*\\tmp\\*",
        "*/test-results/*",
        "*\\test-results\\*",
        "*OPC_UA_Clients/Release2/IJT_CSharp_Client/Types/*",
        "*OPC_UA_Clients\\Release2\\IJT_CSharp_Client\\Types\\*",
        "*OPC_UA_Servers/Release2/OPC_UA_IJT_Server_Simulator/*",
        "*OPC_UA_Servers\\Release2\\OPC_UA_IJT_Server_Simulator\\*",
        "*OPC_UA_Servers/Release2/OPC_UA_IJT_Server_Simulator_Linux/*",
        "*OPC_UA_Servers\\Release2\\OPC_UA_IJT_Server_Simulator_Linux\\*",
    }
    assert expected_globs <= exclude_dirs
    assert not any(path == "tests" for path in exclude_dirs)
    assert bandit_config["skips"] == ["B101"]


def test_report_jobs_install_reporting_requirements() -> None:
    import yaml

    workflow_paths = [
        _runner.REPO_ROOT / ".github" / "workflows" / "ci.yml",
        _runner.REPO_ROOT / ".github" / "workflows" / "integration.yml",
    ]
    for workflow_path in workflow_paths:
        workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
        report_job = workflow["jobs"]["report"]
        install_step = next(
            step
            for step in report_job["steps"]
            if step.get("name") == "Install reporting dependencies"
        )
        install_run = install_step["run"]
        assert "constraints.txt" in install_run
        assert "-r reporting/requirements.txt" in install_run


def test_phase1_bandit_gates_are_medium_plus() -> None:
    console_runner = (_runner.CONSOLE_DIR / "run_all_tests.py").read_text(encoding="utf-8")
    test_client_runner = (_runner.TEST_CLIENT_DIR / "run_all_tests.py").read_text(encoding="utf-8")
    web_runner = (_runner.WEB_CLIENT_DIR / "run_all_tests.py").read_text(encoding="utf-8")
    server_runner = (_runner.SERVER_DIR / "run_all_tests.py").read_text(encoding="utf-8")

    for runner_text in (console_runner, test_client_runner, web_runner, server_runner):
        assert '"bandit"' in runner_text
        assert '"--severity-level"' in runner_text
        assert '"medium"' in runner_text
        assert "_BANDIT_CONFIG" in runner_text
        assert '/ "pyproject.toml"' in runner_text

    assert "if rc != 0:" in web_runner
    assert "def _check_bandit(results: list) -> None:" in server_runner
    assert "_check_bandit(results)" in server_runner


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


def test_csharp_phase1_filter_excludes_dedicated_live_and_security_suites() -> None:
    module = _load_runner_at(
        "OPC_UA_Clients/Release2/IJT_CSharp_Client/run_all_tests.py",
        "ijt_csharp_runner_phase1_filter",
    )

    assert "FullyQualifiedName!~LiveIntegration" in module._PHASE1_TEST_FILTER
    assert "Category!=Live" in module._PHASE1_TEST_FILTER
    assert "Category!=OpcUaSecurity" in module._PHASE1_TEST_FILTER
    assert module._OPCUA_SECURITY_TEST_FILTER == "Category=OpcUaSecurity"


def test_csharp_junit_writer_expands_trx_skip_details(tmp_path) -> None:
    module = _load_runner_at(
        "OPC_UA_Clients/Release2/IJT_CSharp_Client/run_all_tests.py",
        "ijt_csharp_runner_junit",
    )
    trx = tmp_path / "security.trx"
    trx.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<TestRun xmlns="http://microsoft.com/schemas/VisualStudio/TeamTest/2010">
  <Results>
    <UnitTestResult testName="IJT.Security.Passes"
        duration="00:00:01.5000000" outcome="Passed" />
    <UnitTestResult testName="IJT.Security.Skips"
        duration="00:00:00.0000000" outcome="NotExecuted">
      <Output>
        <ErrorInfo>
          <Message>server not reachable</Message>
        </ErrorInfo>
      </Output>
    </UnitTestResult>
    <UnitTestResult testName="IJT.Security.Fails"
        duration="00:00:00.1250000" outcome="Failed">
      <Output>
        <ErrorInfo>
          <Message>boom</Message>
          <StackTrace>stack line</StackTrace>
        </ErrorInfo>
      </Output>
    </UnitTestResult>
  </Results>
</TestRun>
""",
        encoding="utf-8",
    )
    result = module.StepResult(
        "OPC UA Security csharp-client-opcua-security-windows (windows)",
        "MATRIX",
        "FAIL",
        "1/3, 1 skipped",
        1.625,
        1,
        1,
        1,
        3,
        trx,
    )
    output = tmp_path / "junit.xml"

    module._write_junit_xml(output, [result])

    root = ET.parse(output).getroot()
    suite = root.find(".//testsuite")
    assert suite is not None
    assert suite.get("tests") == "3"
    assert suite.get("failures") == "1"
    assert suite.get("skipped") == "1"

    cases = {tc.get("name"): tc for tc in root.findall(".//testcase")}
    assert result.label not in cases
    skipped = cases["IJT.Security.Skips"].find("skipped")
    failure = cases["IJT.Security.Fails"].find("failure")
    assert skipped is not None
    assert skipped.get("message") == "server not reachable"
    assert failure is not None
    assert failure.get("message") == "boom"
    assert failure.text == "stack line"

    theory_name = (
        "IJT_CSharp_Client.Tests.OpcUaSecurityTests.UserName_WrongPassword_IsRejected"
        '(securityPolicyUri: "http://opcfoundation.org/UA/SecurityPolicy#Basic256")'
    )
    assert module._trx_classname(theory_name) == "IJT_CSharp_Client.Tests.OpcUaSecurityTests"


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
    assert "--opcua-security" in help_text
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

    args = parser.parse_args(["--opcua-security", "--phase2"])
    assert args.opcua_security is True
    assert args.phase2 is True
    assert _runner._timing_mode(args) == "phase2+opcua-security"

    args = parser.parse_args(["--opcua-security"])
    assert args.opcua_security is True
    assert _runner._timing_mode(args) == "full+opcua-security"


def test_opcua_security_flag_rejects_invalid_combinations(capsys) -> None:
    parser = _runner._build_parser()

    args = parser.parse_args(["--phase1", "--opcua-security"])
    with pytest.raises(SystemExit) as excinfo:
        _runner._validate_suite_arg(parser, args)
    assert excinfo.value.code == 2
    assert "--opcua-security requires a full run or --phase2" in capsys.readouterr().err

    args = parser.parse_args(
        ["--suite", "csharp-client-opcua-security-windows", "--opcua-security"]
    )
    with pytest.raises(SystemExit) as excinfo:
        _runner._validate_suite_arg(parser, args)
    assert excinfo.value.code == 2
    assert "--opcua-security is not needed with --suite" in capsys.readouterr().err


def test_ci_mode_flag_sets_ci_env_for_child_runners(monkeypatch, capsys) -> None:
    """--ci-mode must inject CI=1 into the environment so client subrunners
    take their CI codepath. Without this, bugs that only fail in GitHub Actions
    cannot be reproduced locally."""
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
