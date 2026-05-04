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
