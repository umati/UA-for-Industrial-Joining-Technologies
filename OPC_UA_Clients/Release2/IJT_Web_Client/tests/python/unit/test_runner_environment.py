"""Tests for the Web Client test runner environment."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_RUNNER_PATH = _PROJECT_ROOT / "run_all_tests.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("ijt_web_run_all_tests", _RUNNER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_subprocess_env_uses_project_npm_cache(monkeypatch):
    monkeypatch.delenv("npm_config_cache", raising=False)
    monkeypatch.delenv("npm_config_update_notifier", raising=False)
    runner = _load_runner()

    env = runner._subprocess_env({})

    assert env["npm_config_cache"] == str(_PROJECT_ROOT / "tmp" / "npm-cache")
    assert env["npm_config_update_notifier"] == "false"


def test_subprocess_env_inherits_opcua_prestarted_marker(monkeypatch):
    runner = _load_runner()
    monkeypatch.setenv("IJT_OPCUA_PRESTARTED_PORT", "40463")

    env = runner._subprocess_env({})

    assert env["IJT_OPCUA_PRESTARTED_PORT"] == "40463"


def test_pip_install_creates_venv_dir_for_hash_file_in_ci(monkeypatch, tmp_path):
    """Regression: in CI, .venv_test/ does not exist (relaunch is skipped),
    so the hash file write must create the parent directory first."""
    runner = _load_runner()
    venv_dir = tmp_path / ".venv_test"
    pip_cache = tmp_path / "pip-cache"
    monkeypatch.setattr(runner, "_VENV", venv_dir)
    monkeypatch.setattr(runner, "_PIP_CACHE", pip_cache)
    monkeypatch.setattr(runner, "_REQUIREMENTS", tmp_path / "missing-requirements.txt")
    monkeypatch.setattr(runner, "_REQUIREMENTS_DEV", tmp_path / "missing-requirements-dev.txt")
    monkeypatch.setattr(runner, "_banner", lambda title: None)
    monkeypatch.setattr(runner, "_info", lambda msg: None)
    monkeypatch.setattr(runner, "_run", lambda *args, **kwargs: 0)
    monkeypatch.setattr(runner, "_requirements_hash", lambda: "abc123")
    monkeypatch.setattr(runner, "_ensure_precommit_hooks", lambda: None)
    monkeypatch.delenv("SKIP_VENV_INSTALL", raising=False)

    assert not venv_dir.exists()
    result = runner._stage_pip_install(Path(sys.executable))

    assert result.rc == 0
    assert (venv_dir / ".req-hash").read_text() == "abc123"


def test_pip_install_reinstalls_when_hash_matches_but_required_modules_missing(monkeypatch, tmp_path):
    runner = _load_runner()
    venv_dir = tmp_path / ".venv_test"
    venv_dir.mkdir()
    (venv_dir / ".req-hash").write_text("abc123", encoding="utf-8")
    req = tmp_path / "requirements.txt"
    req.write_text("pytest\n", encoding="utf-8")
    calls = []
    missing_sequence = iter([["pytest"], []])

    monkeypatch.setattr(runner, "_VENV", venv_dir)
    monkeypatch.setattr(runner, "_PIP_CACHE", tmp_path / "pip-cache")
    monkeypatch.setattr(runner, "_REQUIREMENTS", req)
    monkeypatch.setattr(runner, "_REQUIREMENTS_DEV", tmp_path / "missing-requirements-dev.txt")
    monkeypatch.setattr(runner, "_banner", lambda title: None)
    monkeypatch.setattr(runner, "_info", lambda msg: None)
    monkeypatch.setattr(runner, "_run", lambda *args, **kwargs: calls.append(args[0]) or 0)
    monkeypatch.setattr(runner, "_requirements_hash", lambda: "abc123")
    monkeypatch.setattr(runner, "_ensure_precommit_hooks", lambda: None)
    monkeypatch.setattr(runner, "_missing_py_modules", lambda python, modules: next(missing_sequence))
    monkeypatch.delenv("SKIP_VENV_INSTALL", raising=False)

    result = runner._stage_pip_install(Path(sys.executable), required_modules=("pytest",))

    assert result.rc == 0
    assert any("-r" in cmd for cmd in calls)


def test_pip_install_does_not_mark_hash_current_when_required_modules_remain_missing(monkeypatch, tmp_path):
    runner = _load_runner()
    venv_dir = tmp_path / ".venv_test"
    req = tmp_path / "requirements.txt"
    req.write_text("pytest\n", encoding="utf-8")

    monkeypatch.setattr(runner, "_VENV", venv_dir)
    monkeypatch.setattr(runner, "_PIP_CACHE", tmp_path / "pip-cache")
    monkeypatch.setattr(runner, "_REQUIREMENTS", req)
    monkeypatch.setattr(runner, "_REQUIREMENTS_DEV", tmp_path / "missing-requirements-dev.txt")
    monkeypatch.setattr(runner, "_banner", lambda title: None)
    monkeypatch.setattr(runner, "_info", lambda msg: None)
    monkeypatch.setattr(runner, "_warn", lambda msg: None)
    monkeypatch.setattr(runner, "_run", lambda *args, **kwargs: 0)
    monkeypatch.setattr(runner, "_requirements_hash", lambda: "abc123")
    monkeypatch.setattr(runner, "_ensure_precommit_hooks", lambda: None)
    monkeypatch.setattr(runner, "_missing_py_modules", lambda python, modules: ["pytest"])
    monkeypatch.delenv("SKIP_VENV_INSTALL", raising=False)

    result = runner._stage_pip_install(Path(sys.executable), required_modules=("pytest",))

    assert result.rc == 1
    assert not (venv_dir / ".req-hash").exists()


def test_npm_install_uses_ci_in_ci_when_lockfile_exists(monkeypatch):
    runner = _load_runner()
    monkeypatch.setattr(runner, "IS_CI", True)

    args = runner._npm_install_args("npm")

    assert args[:2] == ["npm", "ci"]
    assert "--no-audit" in args
    assert "--no-fund" in args


def test_npm_install_repairs_incomplete_node_modules(monkeypatch, tmp_path):
    runner = _load_runner()
    node_modules = tmp_path / "node_modules"
    node_modules.mkdir()
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        (node_modules / "@playwright" / "test").mkdir(parents=True)
        (node_modules / "playwright").mkdir()
        bin_dir = node_modules / ".bin"
        bin_dir.mkdir()
        (bin_dir / ("playwright.cmd" if runner.IS_WINDOWS else "playwright")).write_text("", encoding="utf-8")
        return 0

    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "_NPM_CACHE", tmp_path / "npm-cache")
    monkeypatch.setattr(runner.shutil, "which", lambda name: "npm" if name in {"npm", "npm.cmd"} else None)
    monkeypatch.setattr(runner, "_banner", lambda title: None)
    monkeypatch.setattr(runner, "_info", lambda msg: None)
    monkeypatch.setattr(runner, "_run", fake_run)

    result = runner._stage_npm_install(
        required=True,
        required_packages=("@playwright/test", "playwright"),
        required_bins=("playwright",),
    )

    assert result.rc == 0
    assert calls


def test_runner_results_dir_can_be_isolated_per_parallel_suite(monkeypatch):
    isolated = _PROJECT_ROOT / "test-results" / "webclient-live-e2e-smoke"
    monkeypatch.setenv("IJT_WEB_TEST_RESULTS_DIR", str(isolated))

    runner = _load_runner()

    assert runner._RESULTS_DIR == isolated


def test_python_unit_stage_writes_ci_junit_and_coverage_paths(monkeypatch, tmp_path):
    runner = _load_runner()
    captured = {}

    monkeypatch.setattr(runner, "_RESULTS_DIR", tmp_path)
    monkeypatch.setattr(runner, "_banner", lambda title: None)
    monkeypatch.setattr(runner, "_py_module_available", lambda name: name == "pytest_cov")

    def fake_run(cmd, **kwargs):
        captured["cmd"] = [str(part) for part in cmd]
        captured["label"] = kwargs["label"]
        return 0

    monkeypatch.setattr(runner, "_run", fake_run)

    result = runner._stage_python_unit(Path("python"))

    assert result.rc == 0
    assert captured["label"] == "pytest unit"
    assert f"--junitxml={tmp_path / 'pytest.xml'}" in captured["cmd"]
    assert f"--cov-report=xml:{tmp_path / 'coverage.xml'}" in captured["cmd"]
    assert f"--cov-report=html:{tmp_path / 'htmlcov-py'}" in captured["cmd"]


def test_js_unit_stage_writes_ci_junit_and_cobertura_coverage(monkeypatch):
    runner = _load_runner()
    captured = {}
    original_exists = Path.exists

    monkeypatch.setattr(runner, "_banner", lambda title: None)
    monkeypatch.setattr(runner.shutil, "which", lambda name: name)
    monkeypatch.setattr(runner, "_RESULTS_DIR", _PROJECT_ROOT / "test-results")

    def fake_exists(self):
        if "node_modules" in str(self):
            return True
        return original_exists(self)

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return 0

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr(runner, "_run", fake_run)

    result = runner._stage_js_unit()

    assert result.rc == 0
    assert "--coverage.reporter=cobertura" in captured["cmd"]
    assert any(str(part).endswith("vitest.xml") for part in captured["cmd"])


def test_timing_artifacts_are_written_to_results_and_persistent_history(monkeypatch, tmp_path):
    runner = _load_runner()
    results_dir = tmp_path / "results"
    state_dir = tmp_path / "state"
    monkeypatch.setattr(runner, "_RESULTS_DIR", results_dir)
    monkeypatch.setattr(runner, "_STATE_DIR", state_dir)
    monkeypatch.setattr(runner, "_TIMING_HISTORY", state_dir / "timing-history.jsonl")

    runner._write_timing_artifacts(
        [
            runner.StageResult("python-lint", 0, duration=1.25),
            runner.StageResult("playwright-features", 1, duration=2.5, notes=["failed"]),
        ],
        total_time=3.75,
        mode="phase1",
    )

    latest = json.loads((results_dir / "timing-latest.json").read_text(encoding="utf-8"))
    result_history = (results_dir / "timing-history.jsonl").read_text(encoding="utf-8").splitlines()
    persistent_history = (state_dir / "timing-history.jsonl").read_text(encoding="utf-8").splitlines()

    assert latest["mode"] == "phase1"
    assert latest["total_seconds"] == 3.75
    assert latest["stages"][0]["name"] == "python-lint"
    assert latest["stages"][0]["status"] == "passed"
    assert latest["stages"][1]["status"] == "failed"
    assert len(result_history) == 1
    assert len(persistent_history) == 1
    assert json.loads(result_history[0]) == json.loads(persistent_history[0])


def test_subprocess_env_preserves_explicit_npm_cache(monkeypatch):
    monkeypatch.delenv("npm_config_update_notifier", raising=False)
    runner = _load_runner()
    custom_cache = _PROJECT_ROOT / "tmp" / "custom-npm-cache-for-test"

    env = runner._subprocess_env({"npm_config_cache": str(custom_cache)})

    assert env["npm_config_cache"] == str(custom_cache)
    assert env["npm_config_update_notifier"] == "false"


def test_websocket_backend_uses_existing_port(monkeypatch):
    runner = _load_runner()
    monkeypatch.setattr(runner, "_port_open", lambda host, port, timeout=1.0: True)

    started, ready, proc = runner._maybe_start_websocket_backend(Path("python"), "localhost", 8001)

    assert started is False
    assert ready is True
    assert proc is None


def test_websocket_backend_does_not_start_remote_host(monkeypatch):
    runner = _load_runner()
    monkeypatch.setattr(runner, "_port_open", lambda host, port, timeout=1.0: False)

    started, ready, proc = runner._maybe_start_websocket_backend(Path("python"), "example.com", 8001)

    assert started is False
    assert ready is False
    assert proc is None


def test_websocket_backend_auto_start_sets_ws_port(monkeypatch):
    runner = _load_runner()
    created = {}
    monkeypatch.setenv("OPCUA_TEST_ENDPOINT", "opc.tcp://localhost:40463")

    class FakeProc:
        def terminate(self):
            created["terminated"] = True

        def wait(self, timeout=None):
            created["wait_timeout"] = timeout

        def kill(self):
            created["killed"] = True

    def fake_popen(cmd, **kwargs):
        created["cmd"] = cmd
        created["kwargs"] = kwargs
        return FakeProc()

    monkeypatch.setattr(runner, "ROOT", _PROJECT_ROOT)
    monkeypatch.setattr(runner, "_port_open", lambda host, port, timeout=1.0: False)
    monkeypatch.setattr(runner, "_wait_for_port", lambda host, port, timeout=30: True)
    monkeypatch.setattr(runner.subprocess, "Popen", fake_popen)

    started, ready, proc = runner._maybe_start_websocket_backend(Path("python"), "localhost", 9001)

    assert started is True
    assert ready is True
    assert proc is not None
    assert created["cmd"] == ["python", "index.py"]
    assert created["kwargs"]["cwd"] == str(_PROJECT_ROOT)
    assert created["kwargs"]["env"]["WS_PORT"] == "9001"
    assert created["kwargs"]["env"]["OPCUA_TEST_ENDPOINT"] == "opc.tcp://localhost:40463"


def test_existing_opcua_port_sets_test_endpoint(monkeypatch):
    runner = _load_runner()
    monkeypatch.delenv("OPCUA_TEST_ENDPOINT", raising=False)
    monkeypatch.delenv("OPCUA_SERVER_URL", raising=False)
    monkeypatch.delenv("OPCUA_SERVER_PORT", raising=False)
    monkeypatch.setenv("IJT_OPCUA_PRESTARTED_PORT", "40463")
    monkeypatch.setattr(runner, "_port_open", lambda host, port, timeout=1.0: True)

    started, ready, proc = runner._maybe_start_opcua_server()

    assert started is False
    assert ready is True
    assert proc is None
    assert runner.os.environ["OPCUA_TEST_ENDPOINT"] == "opc.tcp://localhost:40463"
    assert "IJT_OPCUA_PRESTARTED_PORT" not in runner.os.environ


def test_opcua_log_process_uses_append_logs_and_closes_parent_handles(monkeypatch, tmp_path):
    runner = _load_runner()
    captured = {}

    class FakeProc:
        pass

    def fake_popen(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["cwd"] = kwargs["cwd"]
        captured["stdout"] = kwargs["stdout"]
        captured["stderr"] = kwargs["stderr"]
        captured["stdin"] = kwargs["stdin"]
        captured["stdout_name"] = kwargs["stdout"].name
        captured["stderr_name"] = kwargs["stderr"].name
        return FakeProc()

    monkeypatch.setattr(runner, "_RESULTS_DIR", tmp_path / "results")
    monkeypatch.setattr(runner.subprocess, "Popen", fake_popen)

    proc = runner._start_process_with_opcua_logs(["simulator.exe"], cwd=tmp_path, port=40463)

    assert isinstance(proc, FakeProc)
    assert captured["cmd"] == ["simulator.exe"]
    assert captured["cwd"] == str(tmp_path)
    assert captured["stdin"] is runner.subprocess.DEVNULL
    assert Path(captured["stdout_name"]) == tmp_path / "results" / "opcua-server-40463.out.log"
    assert Path(captured["stderr_name"]) == tmp_path / "results" / "opcua-server-40463.err.log"
    assert captured["stdout"].closed is True
    assert captured["stderr"].closed is True


def test_owned_opcua_launch_sets_endpoint_and_prestarted_marker(monkeypatch, tmp_path):
    runner = _load_runner()

    class FakeProc:
        pass

    monkeypatch.delenv("OPCUA_TEST_ENDPOINT", raising=False)
    monkeypatch.delenv("IJT_OPCUA_PRESTARTED_PORT", raising=False)
    monkeypatch.setattr(
        runner,
        "_launch_simulator_instance",
        lambda port, exe: runner._OpcuaServerInstance(port=port, proc=FakeProc(), tmp_dir=tmp_path),
    )

    proc = runner._launch_simulator_on_port(40466, "simulator.exe")

    assert isinstance(proc, FakeProc)
    assert runner.os.environ["OPCUA_TEST_ENDPOINT"] == "opc.tcp://localhost:40466"
    assert runner.os.environ["IJT_OPCUA_PRESTARTED_PORT"] == "40466"


def test_simulator_package_is_extracted_when_binary_is_missing(monkeypatch, tmp_path):
    runner = _load_runner()
    server_dir = tmp_path / "Release2"
    package = server_dir / "OPC_UA_IJT_Server_Simulator.zip"
    executable = server_dir / "OPC_UA_IJT_Server_Simulator" / "opcua_ijt_demo_application.exe"
    package.parent.mkdir(parents=True)
    package.write_text("zip placeholder", encoding="utf-8")
    extracted = {}

    class FakeZipFile:
        def __init__(self, path):
            extracted["path"] = path

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extractall(self, destination):
            extracted["destination"] = destination
            executable.parent.mkdir(parents=True)
            executable.write_text("exe", encoding="utf-8")

    monkeypatch.delenv("OPCUA_SIMULATOR_EXE", raising=False)
    monkeypatch.setattr(runner, "_SERVER_COMPOSE_DIR", server_dir)
    monkeypatch.setattr(runner, "_WELL_KNOWN_SIMULATOR_PATHS", [executable])
    monkeypatch.setattr(runner, "_SIMULATOR_PACKAGE_ZIPS", [package])
    monkeypatch.setattr(runner.zipfile, "ZipFile", FakeZipFile)

    assert runner._find_simulator_executable() == str(executable)
    assert extracted == {"path": package, "destination": server_dir}


def test_playwright_install_skips_with_deps_on_windows(monkeypatch):
    runner = _load_runner()
    calls = []

    monkeypatch.setattr(runner, "IS_WINDOWS", True)
    monkeypatch.setattr(runner, "_node_bin_path", lambda name: "playwright.cmd")
    monkeypatch.setattr(runner, "_banner", lambda title: None)
    monkeypatch.setattr(runner, "_warn", lambda message: None)
    monkeypatch.setattr(runner, "_playwright_chromium_available", lambda: False)

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return 0

    monkeypatch.setattr(runner, "_run", fake_run)

    result = runner._stage_playwright_install()

    assert result.rc == 0
    assert calls == [["playwright.cmd", "install", "chromium"]]


def test_e2e_local_connection_waits_for_endpoint_state_not_visual_status():
    source = (_PROJECT_ROOT / "tests" / "e2e" / "page-objects.mjs").read_text(encoding="utf-8")
    start = source.index("async connectToLocal")
    end = source.index("/** Assert the page title", start)
    body = source[start:end]

    assert re.search(
        r"SEL\.ENDPOINT_STATE\(\s*['\"]LOCAL['\"]\s*,\s*['\"]connection['\"]\s*,\s*['\"]connected['\"]\s*\)",
        body,
    )
    assert re.search(
        r"SEL\.ENDPOINT_STATE\(\s*['\"]LOCAL['\"]\s*,\s*['\"]subscription['\"]\s*,\s*['\"]connected['\"]\s*\)",
        body,
    )
    assert re.search(r"waitFor\(\s*\{\s*state:\s*['\"]visible['\"]\s*,\s*timeout\s*\}\s*\)", body)
    assert "state: 'attached'" not in body
    assert 'state: "attached"' not in body
    assert "SEL.ON_COLOR" not in body
    assert "statusTimeout" not in body


def test_e2e_address_space_uses_visible_tab_label():
    source = (_PROJECT_ROOT / "tests" / "e2e" / "page-objects.mjs").read_text(encoding="utf-8")
    start = source.index("async openAddressSpace")
    end = source.index("async openServers", start)
    body = source[start:end]

    assert re.search(r"clickTab\(\s*['\"]Address Space['\"]\s*\)", body)
    assert "clickTab('AddressSpace')" not in body
    assert 'clickTab("AddressSpace")' not in body


def test_e2e_result_selectors_use_semantic_result_controls():
    page_objects = (_PROJECT_ROOT / "tests" / "e2e" / "page-objects.mjs").read_text(encoding="utf-8")
    result_graphics = (
        _PROJECT_ROOT / "src" / "javascripts" / "views" / "complex-result" / "result-graphics.mjs"
    ).read_text(encoding="utf-8")

    assert 'data-ijt-result-control", "type"' in result_graphics.replace("'", '"')
    assert 'data-ijt-result-control", "result"' in result_graphics.replace("'", '"')
    assert "RESULT_TYPE_SELECT: '.resultheader select[data-ijt-result-control=\"type\"]'" in page_objects
    assert "RESULT_ITEM_SELECT: '.resultheader select[data-ijt-result-control=\"result\"]'" in page_objects
    assert ".resultheader select:first-of-type" not in page_objects
    assert ".resultheader select:nth-of-type(2)" not in page_objects


def test_ws_e2e_asserts_backend_response_envelopes():
    connection_spec = (_PROJECT_ROOT / "tests" / "e2e" / "connection.spec.mjs").read_text(encoding="utf-8")
    address_space_spec = (_PROJECT_ROOT / "tests" / "e2e" / "address-space.spec.mjs").read_text(encoding="utf-8")

    assert "resp.data?.namespaces" in connection_spec
    assert "resp.data?.nodes" in connection_spec
    assert "resp.data?.nodes" in address_space_spec
    assert "Array.isArray(resp.data)" not in connection_spec
    assert "const nodes = resp.data ?? []" not in address_space_spec


def test_ws_namespace_assertion_uses_real_namespace_uris():
    connection_spec = (_PROJECT_ROOT / "tests" / "e2e" / "connection.spec.mjs").read_text(encoding="utf-8")

    assert "http://opcfoundation.org/UA/" in connection_spec
    assert "http://opcfoundation.org/UA/IJT/Base/" in connection_spec
    assert "http://opcfoundation.org/UA/IJT/Tightening/" in connection_spec
    assert "OpcUa" not in connection_spec


def test_address_space_expansion_uses_stable_browse_names():
    page_objects = (_PROJECT_ROOT / "tests" / "e2e" / "page-objects.mjs").read_text(encoding="utf-8")
    address_space_spec = (_PROJECT_ROOT / "tests" / "e2e" / "address-space.spec.mjs").read_text(encoding="utf-8")
    address_space_graphics = (
        _PROJECT_ROOT / "src" / "javascripts" / "views" / "address-space" / "address-space-graphics.mjs"
    ).read_text(encoding="utf-8")

    assert "data-opcua-node-class" in address_space_graphics
    assert "data-opcua-browse-name" in address_space_graphics
    assert "TREE_BUTTON_BY_BROWSE_NAME" in page_objects
    assert "expandByBrowseName" in page_objects
    assert "expandByBrowseName(['Server']" in address_space_spec
    assert "ServerStatus" in address_space_spec
    assert "CLOSED_OBJECT_TREE_BUTTON" not in page_objects
    assert "expandFirstClosedObjectNode" not in page_objects
    assert "expandFirstClosedObjectNode" not in address_space_spec
    assert "toggleFirstNode" not in address_space_spec


def test_phase2_can_skip_docker_for_root_runner_split(monkeypatch):
    monkeypatch.delenv("IJT_DOCKER_BUILD_TIMEOUT", raising=False)
    runner = _load_runner()

    assert "--skip-docker" in _RUNNER_PATH.read_text(encoding="utf-8")
    assert "--docker-only" in _RUNNER_PATH.read_text(encoding="utf-8")
    assert runner._DOCKER_BUILD_TIMEOUT == 1200


def test_targeted_live_suite_flags_are_available():
    source = _RUNNER_PATH.read_text(encoding="utf-8")

    for flag in [
        "--python-opcua-only",
        "--python-backend-only",
        "--python-lifecycle-only",
        "--playwright-smoke-only",
        "--playwright-features-only",
        "--playwright-regression-only",
    ]:
        assert flag in source


def _target_args(**enabled):
    names = [
        "python_opcua_only",
        "python_backend_only",
        "python_lifecycle_only",
        "playwright_smoke_only",
        "playwright_features_only",
        "playwright_regression_only",
    ]
    values = {name: False for name in names}
    values.update(enabled)
    return SimpleNamespace(**values)


def test_target_only_dependency_requirements_are_explicit():
    runner = _load_runner()

    cases = [
        (_target_args(python_opcua_only=True), (True, False)),
        (_target_args(python_backend_only=True), (True, False)),
        (_target_args(python_lifecycle_only=True), (True, False)),
        (_target_args(playwright_smoke_only=True), (False, True)),
        (_target_args(playwright_features_only=True), (True, True)),
        (_target_args(playwright_regression_only=True), (True, True)),
    ]

    for args, expected in cases:
        requirements = runner._target_only_dependency_requirements(args)
        assert (requirements.python, requirements.npm) == expected


def test_target_only_dependencies_run_before_target_stage(monkeypatch, tmp_path):
    runner = _load_runner()
    calls = []

    monkeypatch.setattr(sys, "argv", ["run_all_tests.py", "--playwright-features-only"])
    monkeypatch.setattr(runner, "IS_CI", True)
    monkeypatch.setattr(runner, "_RESULTS_DIR", tmp_path / "results")
    monkeypatch.setattr(runner, "_cleanup_caches", lambda root: None)
    monkeypatch.setattr(runner, "_prepare_tmp_dir", lambda: None)
    monkeypatch.setattr(runner, "_port_open", lambda *args, **kwargs: False)
    monkeypatch.setattr(runner, "_docker_available", lambda: False)
    monkeypatch.setattr(runner, "_write_timing_artifacts", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        runner,
        "_stage_pip_install",
        lambda python, required_modules=(): calls.append("pip") or runner.StageResult("pip-install", 0),
    )
    monkeypatch.setattr(
        runner,
        "_stage_npm_install",
        lambda **kwargs: calls.append("npm") or runner.StageResult("npm-install", 0),
    )
    monkeypatch.setattr(
        runner,
        "_stage_playwright_install",
        lambda: calls.append("playwright-install") or runner.StageResult("playwright-install", 0),
    )
    monkeypatch.setattr(
        runner,
        "_run_playwright_features_with_owned_pool",
        lambda **kwargs: calls.append("playwright-features") or runner.StageResult("playwright-features", 0),
    )

    assert runner.main() == 0
    assert calls == ["pip", "npm", "playwright-install", "playwright-features"]


def test_target_only_dependency_failure_stops_before_live_stage(monkeypatch, tmp_path):
    runner = _load_runner()

    monkeypatch.setattr(sys, "argv", ["run_all_tests.py", "--python-opcua-only"])
    monkeypatch.setattr(runner, "IS_CI", True)
    monkeypatch.setattr(runner, "_RESULTS_DIR", tmp_path / "results")
    monkeypatch.setattr(runner, "_cleanup_caches", lambda root: None)
    monkeypatch.setattr(runner, "_prepare_tmp_dir", lambda: None)
    monkeypatch.setattr(runner, "_port_open", lambda *args, **kwargs: False)
    monkeypatch.setattr(runner, "_docker_available", lambda: False)
    monkeypatch.setattr(runner, "_write_timing_artifacts", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        runner,
        "_stage_pip_install",
        lambda python, required_modules=(): runner.StageResult("pip-install", 1, notes=["missing pytest"]),
    )

    def fail_if_live_stage_runs(**kwargs):
        raise AssertionError("live stage must not run when dependency setup fails")

    monkeypatch.setattr(runner, "_run_with_owned_services", fail_if_live_stage_runs)

    assert runner.main() == 1


def test_playwright_config_uses_runtime_ui_port_and_no_retries():
    source = (_PROJECT_ROOT / "playwright.config.mjs").read_text(encoding="utf-8")

    assert "const UI_PORT = process.env.UI_TEST_PORT" in source
    assert "const UI_BASE_URL" in source
    assert "const TEST_RESULTS_DIR = process.env.IJT_WEB_TEST_RESULTS_DIR" in source
    assert "outputDir: `${TEST_RESULTS_DIR}/artifacts`" in source
    assert "outputFolder: `${TEST_RESULTS_DIR}/html`" in source
    assert "outputFile: `${TEST_RESULTS_DIR}/results.json`" in source
    assert "outputFile: `${TEST_RESULTS_DIR}/playwright.xml`" in source
    assert "const PLAYWRIGHT_WORKERS" in source
    assert "process.env.IJT_PLAYWRIGHT_WORKERS" in source
    assert "baseURL: UI_BASE_URL" in source
    assert "reuseExistingServer: false" in source
    assert re.search(r"retries:\s*0", source)
    assert "fullyParallel: true" in source


def test_e2e_fixture_passes_runtime_websocket_query():
    source = (_PROJECT_ROOT / "tests" / "e2e" / "e2e-fixtures.mjs").read_text(encoding="utf-8")

    assert "function runtimeAppUrl" in source
    assert "function runtimeForWorker" in source
    assert "function withPortOffset" in source
    assert "testInfo.parallelIndex" in source
    assert "IJT_E2E_BACKEND_WORKERS" in source
    assert "wsProtocol" in source
    assert "wsHost" in source
    assert "wsPort" in source
    assert "new AppPage(page, runtime.appUrl)" in source


def test_playwright_feature_stage_passes_worker_pool_environment(monkeypatch):
    runner = _load_runner()
    captured = {}

    monkeypatch.setattr(runner, "_node_bin_path", lambda name: "playwright.cmd")
    monkeypatch.setattr(runner, "_banner", lambda title: None)

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["env"] = kwargs["env"]
        captured["timeout"] = kwargs["timeout"]
        return 0

    monkeypatch.setattr(runner, "_run", fake_run)

    result = runner._stage_playwright_features(
        "ws://localhost:8005",
        "http://127.0.0.1:3005",
        workers=4,
        extra_env={"OPCUA_TEST_ENDPOINT": "opc.tcp://localhost:40469"},
    )

    assert result.rc == 0
    assert "--workers=4" in captured["cmd"]
    assert captured["env"]["IJT_PLAYWRIGHT_WORKERS"] == "4"
    assert captured["env"]["IJT_E2E_BACKEND_WORKERS"] == "4"
    assert captured["env"]["OPCUA_TEST_ENDPOINT"] == "opc.tcp://localhost:40469"
    assert captured["timeout"] == 600


def test_playwright_feature_pool_owns_one_backend_pair_per_worker(monkeypatch):
    runner = _load_runner()
    launched_opcua_ports: list[int] = []
    launched_ws: list[tuple[int, str | None, str]] = []
    stopped_opcua_ports: list[int] = []
    stopped_ws_ports: list[int] = []
    stage_call = {}

    class FakeProc:
        def __init__(self, port: int):
            self.port = port

    monkeypatch.delenv("OPCUA_TEST_ENDPOINT", raising=False)
    monkeypatch.delenv("OPCUA_SERVER_URL", raising=False)
    monkeypatch.setenv("OPCUA_SERVER_PORT", "4100")
    monkeypatch.setattr(runner, "_port_open", lambda host, port, timeout=1.0: False)
    monkeypatch.setattr(runner, "_find_simulator_executable", lambda: "simulator.exe")

    def fake_launch(port, exe):
        launched_opcua_ports.append(port)
        return runner._OpcuaServerInstance(port=port, proc=FakeProc(port), tmp_dir=None)

    def fake_start_ws(python, host, port, *, opcua_endpoint=None, log_name="websocket-backend.log"):
        launched_ws.append((port, opcua_endpoint, log_name))
        return True, True, FakeProc(port)

    def fake_stage(ws_url, ui_url, *, workers=None, extra_env=None):
        stage_call.update(
            {
                "ws_url": ws_url,
                "ui_url": ui_url,
                "workers": workers,
                "extra_env": extra_env,
            }
        )
        return runner.StageResult("playwright-features", 0)

    monkeypatch.setattr(runner, "_launch_simulator_instance", fake_launch)
    monkeypatch.setattr(runner, "_maybe_start_websocket_backend", fake_start_ws)
    monkeypatch.setattr(runner, "_stage_playwright_features", fake_stage)
    monkeypatch.setattr(runner, "_stop_websocket_backend", lambda proc: stopped_ws_ports.append(proc.port))
    monkeypatch.setattr(
        runner, "_stop_opcua_server_instance", lambda instance: stopped_opcua_ports.append(instance.port)
    )

    result = runner._run_playwright_features_with_owned_pool(
        python=Path("python"),
        name="playwright-features",
        ws_url="ws://localhost:9000",
        ui_url="http://127.0.0.1:3005",
        workers=3,
    )

    assert result.rc == 0
    assert launched_opcua_ports == [4100, 4101, 4102]
    assert launched_ws == [
        (9000, "opc.tcp://localhost:4100", "websocket-backend-9000.log"),
        (9001, "opc.tcp://localhost:4101", "websocket-backend-9001.log"),
        (9002, "opc.tcp://localhost:4102", "websocket-backend-9002.log"),
    ]
    assert stage_call == {
        "ws_url": "ws://localhost:9000",
        "ui_url": "http://127.0.0.1:3005",
        "workers": 3,
        "extra_env": {
            "OPCUA_TEST_ENDPOINT": "opc.tcp://localhost:4100",
            "IJT_E2E_BACKEND_WORKERS": "3",
        },
    }
    assert stopped_ws_ports == [9002, 9001, 9000]
    assert stopped_opcua_ports == [4102, 4101, 4100]


def test_config_uses_runtime_websocket_port_not_static_service_port():
    config_source = (_PROJECT_ROOT / "config.js").read_text(encoding="utf-8")
    index_source = (_PROJECT_ROOT / "index.html").read_text(encoding="utf-8")

    assert "window.__IJT_RUNTIME__" in config_source
    assert "query.get('wsPort')" in config_source
    assert "WS_PORT: '8001'" not in config_source
    assert "window.__IJT_RUNTIME__ = { WS_PORT: '8001' }" in index_source


def test_runner_summary_treats_negative_stage_rc_as_failure(capsys):
    runner = _load_runner()

    rc = runner._print_summary([runner.StageResult("timed-out-stage", -1)], total_time=1.0)

    output = capsys.readouterr().out
    assert rc == 1
    assert "[FAIL]" in output
    assert "SOME TESTS FAILED" in output
    assert "ALL TESTS PASSED" not in output


def test_playwright_install_passes_without_network_when_chromium_exists(monkeypatch):
    runner = _load_runner()

    monkeypatch.setattr(runner, "_node_bin_path", lambda name: "playwright.cmd")
    monkeypatch.setattr(runner, "_playwright_chromium_available", lambda: True)

    def fail_if_install_runs(*_args, **_kwargs):
        raise AssertionError("playwright install should not run when chromium is already installed")

    monkeypatch.setattr(runner, "_run", fail_if_install_runs)

    result = runner._stage_playwright_install()

    assert result.rc == 0
    assert result.skipped is False
    assert result.notes == ["chromium browser already installed"]


def test_playwright_install_failure_is_not_reported_as_skip(monkeypatch):
    runner = _load_runner()

    monkeypatch.setattr(runner, "_node_bin_path", lambda name: "playwright.cmd")
    monkeypatch.setattr(runner, "_playwright_chromium_available", lambda: False)
    monkeypatch.setattr(runner, "_run", lambda *_args, **_kwargs: -1)

    result = runner._stage_playwright_install()

    assert result.rc == 1
    assert result.skipped is False
    assert "Browser download failed" in result.notes[0]


def test_servers_tab_uses_descriptive_label():
    server_graphics = (_PROJECT_ROOT / "src" / "javascripts" / "views" / "servers" / "server-graphics.mjs").read_text(
        encoding="utf-8"
    )
    page_objects = (_PROJECT_ROOT / "tests" / "e2e" / "page-objects.mjs").read_text(encoding="utf-8")
    settings = (_PROJECT_ROOT / "src" / "javascripts" / "views" / "graphic-support" / "settings.mjs").read_text(
        encoding="utf-8"
    )

    assert "super('Servers')" in server_graphics
    assert "super('+')" not in server_graphics
    assert "clickTab('Servers')" in page_objects
    assert "SETTINGS_SCREEN: '.settingsScreen'" in page_objects
    assert "String(level) === '5'" in page_objects
    assert "settingsScreen" in settings


def test_address_space_buttons_expose_stable_node_identity_attributes():
    address_space_graphics = (
        _PROJECT_ROOT / "src" / "javascripts" / "views" / "address-space" / "address-space-graphics.mjs"
    ).read_text(encoding="utf-8")

    assert "setTreeButtonIdentity" in address_space_graphics
    assert "data-opcua-node-id" in address_space_graphics
    assert "data-opcua-browse-name" in address_space_graphics
    assert "data-opcua-node-class" in address_space_graphics
    assert "nodeClassToText" in address_space_graphics
    assert "Consumed by E2E tests" in address_space_graphics


def test_endpoint_tabs_expose_session_identity_for_readiness_checks():
    endpoint_tab_state = (
        _PROJECT_ROOT / "src" / "javascripts" / "views" / "tab-setup" / "endpoint-tab-state.mjs"
    ).read_text(encoding="utf-8")
    endpoint_graphics = (
        _PROJECT_ROOT / "src" / "javascripts" / "views" / "tab-setup" / "endpoint-graphics.mjs"
    ).read_text(encoding="utf-8")
    connection_manager = (
        _PROJECT_ROOT / "src" / "javascripts" / "ijt-support" / "connection" / "connection-manager.mjs"
    ).read_text(encoding="utf-8")

    assert "data-opcua-session-id" in endpoint_tab_state
    assert "this.connectionManager.sessionId" in endpoint_graphics
    assert "createSessionId" in connection_manager
