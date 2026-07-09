"""Tests for the Web Client test runner environment."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

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


def _make_simulator_executable(tmp_path: Path) -> Path:
    src_dir = tmp_path / "simulator-src"
    src_dir.mkdir()
    executable = src_dir / ("simulator.exe" if os.name == "nt" else "simulator")
    executable.write_text("binary placeholder", encoding="utf-8")
    return executable


def _patch_simulator_launch_common(monkeypatch, runner, tmp_path: Path) -> Path:
    instance_dir = tmp_path / "instance"
    state_dir = tmp_path / "state"
    monkeypatch.setattr(runner, "_RESULTS_DIR", tmp_path / "results")
    monkeypatch.setattr(runner, "_STATE_DIR", state_dir)
    monkeypatch.setattr(runner, "_TIMING_HISTORY", state_dir / "timing-history.jsonl")
    monkeypatch.setattr(runner, "_MAX_SIMULATOR_INSTANCE_PATH", 4096)
    monkeypatch.setattr(runner, "_simulator_instance_dir", lambda _port: instance_dir)
    monkeypatch.setattr(runner, "_warn", lambda _message: None)
    monkeypatch.setattr(runner, "_info", lambda _message: None)
    monkeypatch.setattr(runner, "_ok", lambda _message: None)
    monkeypatch.setattr(runner.time, "sleep", lambda _seconds: None)
    runner._SIMULATOR_LAUNCH_NOTES.clear()
    return instance_dir


def test_precommit_hooks_are_not_installed_in_ci(monkeypatch):
    runner = _load_runner()
    monkeypatch.setattr(runner, "IS_CI", True)
    monkeypatch.setattr(runner, "_py_module_available", lambda name: True)

    def fail_check_call(*args, **kwargs):
        raise AssertionError("pre-commit hook install should not run in CI")

    monkeypatch.setattr(runner.subprocess, "check_call", fail_check_call)

    runner._ensure_precommit_hooks()


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


def test_pip_install_preserves_explicit_pip_cache_dir(monkeypatch, tmp_path):
    runner = _load_runner()
    venv_dir = tmp_path / ".venv_test"
    req = tmp_path / "requirements.txt"
    req.write_text("pytest\n", encoding="utf-8")
    runner_cache = tmp_path / "runner-pip-cache"
    caller_cache = tmp_path / "caller-pip-cache"
    envs: list[dict[str, str]] = []

    def fake_run(_cmd, **kwargs):
        envs.append(kwargs["env"])
        return 0

    monkeypatch.setattr(runner, "_VENV", venv_dir)
    monkeypatch.setattr(runner, "_PIP_CACHE", runner_cache)
    monkeypatch.setattr(runner, "_REQUIREMENTS", req)
    monkeypatch.setattr(runner, "_REQUIREMENTS_DEV", tmp_path / "missing-requirements-dev.txt")
    monkeypatch.setattr(runner, "_banner", lambda title: None)
    monkeypatch.setattr(runner, "_info", lambda msg: None)
    monkeypatch.setattr(runner, "_run", fake_run)
    monkeypatch.setattr(runner, "_requirements_hash", lambda: "abc123")
    monkeypatch.setattr(runner, "_ensure_precommit_hooks", lambda: None)
    monkeypatch.setattr(runner, "_missing_py_modules", lambda python, modules: [])
    monkeypatch.setenv("PIP_CACHE_DIR", str(caller_cache))
    monkeypatch.delenv("SKIP_VENV_INSTALL", raising=False)

    result = runner._stage_pip_install(Path(sys.executable))

    assert result.rc == 0
    assert envs
    assert all(env["PIP_CACHE_DIR"] == str(caller_cache) for env in envs)
    assert not runner_cache.exists()


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


def test_python_lint_fails_on_fixable_pip_audit_cve(monkeypatch, tmp_path):
    runner = _load_runner()
    monkeypatch.setattr(runner, "_RESULTS_DIR", tmp_path / "test-results")
    monkeypatch.setattr(runner, "_TMP_DIR", tmp_path / "tmp")
    monkeypatch.setattr(runner.shutil, "which", lambda name: None)
    monkeypatch.setattr(runner, "_py_module_available", lambda name: name == "pip_audit")
    monkeypatch.setattr(runner, "_cmd_available", lambda name: False)
    monkeypatch.setattr(runner, "_is_https_reachable", lambda host: True)
    monkeypatch.setattr(runner, "_banner", lambda title: None)
    monkeypatch.setattr(runner, "_skip", lambda msg: None)

    def fake_run_captured(cmd, **kwargs):
        if "pip_audit" in cmd:
            report = Path(cmd[cmd.index("-o") + 1])
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(
                json.dumps(
                    {
                        "dependencies": [
                            {
                                "name": "urllib3",
                                "vulns": [{"id": "CVE-2026-44431", "fix_versions": ["2.7.0"]}],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            return 1, ""
        return 0, ""

    monkeypatch.setattr(runner, "_run_captured", fake_run_captured)

    result = runner._stage_python_lint(Path(sys.executable))

    assert result.rc == 1
    assert any("1 fixable CVE" in note for note in result.notes)


def test_python_lint_allows_advisory_only_pip_audit_cve(monkeypatch, tmp_path):
    runner = _load_runner()
    monkeypatch.setattr(runner, "_RESULTS_DIR", tmp_path / "test-results")
    monkeypatch.setattr(runner, "_TMP_DIR", tmp_path / "tmp")
    monkeypatch.setattr(runner.shutil, "which", lambda name: None)
    monkeypatch.setattr(runner, "_py_module_available", lambda name: name == "pip_audit")
    monkeypatch.setattr(runner, "_cmd_available", lambda name: False)
    monkeypatch.setattr(runner, "_is_https_reachable", lambda host: True)
    monkeypatch.setattr(runner, "_banner", lambda title: None)
    monkeypatch.setattr(runner, "_skip", lambda msg: None)

    def fake_run_captured(cmd, **kwargs):
        if "pip_audit" in cmd:
            report = Path(cmd[cmd.index("-o") + 1])
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(
                json.dumps({"dependencies": [{"name": "package", "vulns": [{"id": "CVE-X", "fix_versions": []}]}]}),
                encoding="utf-8",
            )
            return 1, ""
        return 0, ""

    monkeypatch.setattr(runner, "_run_captured", fake_run_captured)

    result = runner._stage_python_lint(Path(sys.executable))

    assert result.rc == 0
    assert any("advisory CVE" in note for note in result.notes)


def test_python_lint_fails_when_pip_audit_reports_cves_without_json(monkeypatch, tmp_path):
    runner = _load_runner()
    monkeypatch.setattr(runner, "_RESULTS_DIR", tmp_path / "test-results")
    monkeypatch.setattr(runner, "_TMP_DIR", tmp_path / "tmp")
    monkeypatch.setattr(runner.shutil, "which", lambda name: None)
    monkeypatch.setattr(runner, "_py_module_available", lambda name: name == "pip_audit")
    monkeypatch.setattr(runner, "_cmd_available", lambda name: False)
    monkeypatch.setattr(runner, "_is_https_reachable", lambda host: True)
    monkeypatch.setattr(runner, "_banner", lambda title: None)
    monkeypatch.setattr(runner, "_skip", lambda msg: None)
    monkeypatch.setattr(
        runner,
        "_run_captured",
        lambda cmd, **kwargs: (1, "internal parsing failure") if "pip_audit" in cmd else (0, ""),
    )

    result = runner._stage_python_lint(Path(sys.executable))

    assert result.rc == 1
    assert any("report missing" in note for note in result.notes)


def test_python_lint_retries_pip_audit_before_failing(monkeypatch, tmp_path):
    runner = _load_runner()
    monkeypatch.setattr(runner, "_RESULTS_DIR", tmp_path / "test-results")
    monkeypatch.setattr(runner, "_TMP_DIR", tmp_path / "tmp")
    monkeypatch.setattr(runner.shutil, "which", lambda name: None)
    monkeypatch.setattr(runner, "_py_module_available", lambda name: name == "pip_audit")
    monkeypatch.setattr(runner, "_cmd_available", lambda name: False)
    monkeypatch.setattr(runner, "_is_https_reachable", lambda host: True)
    monkeypatch.setattr(runner, "_banner", lambda title: None)
    monkeypatch.setattr(runner, "_skip", lambda msg: None)
    monkeypatch.setattr(runner, "_warn", lambda msg: None)

    attempts = {"count": 0}

    def fake_run_captured(cmd, **kwargs):
        if "pip_audit" not in cmd:
            return 0, ""
        attempts["count"] += 1
        report = Path(cmd[cmd.index("-o") + 1])
        report.parent.mkdir(parents=True, exist_ok=True)
        if attempts["count"] == 1:
            return 1, "ReadTimeout while connecting to pypi.org"
        report.write_text(
            json.dumps(
                {
                    "dependencies": [
                        {
                            "name": "urllib3",
                            "vulns": [{"id": "CVE-2026-44431", "fix_versions": ["2.7.0"]}],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        return 1, ""

    monkeypatch.setattr(runner, "_run_captured", fake_run_captured)

    result = runner._stage_python_lint(Path(sys.executable))

    assert attempts["count"] == 2
    assert result.rc == 1
    assert any("fixable CVE" in note for note in result.notes)


def test_python_lint_skips_pip_audit_after_repeated_network_failures(monkeypatch, tmp_path):
    runner = _load_runner()
    monkeypatch.setattr(runner, "_RESULTS_DIR", tmp_path / "test-results")
    monkeypatch.setattr(runner, "_TMP_DIR", tmp_path / "tmp")
    monkeypatch.setattr(runner.shutil, "which", lambda name: None)
    monkeypatch.setattr(runner, "_py_module_available", lambda name: name == "pip_audit")
    monkeypatch.setattr(runner, "_cmd_available", lambda name: False)
    monkeypatch.setattr(runner, "_is_https_reachable", lambda host: True)
    monkeypatch.setattr(runner, "_banner", lambda title: None)
    monkeypatch.setattr(runner, "_skip", lambda msg: None)
    monkeypatch.setattr(runner, "_warn", lambda msg: None)
    monkeypatch.setattr(
        runner,
        "_run_captured",
        lambda cmd, **kwargs: (1, "ReadTimeout while connecting to pypi.org") if "pip_audit" in cmd else (0, ""),
    )

    result = runner._stage_python_lint(Path(sys.executable))

    assert result.rc == 0
    assert any("pip-audit skipped (network timeout)" in note for note in result.notes)


def test_python_lint_skips_pip_audit_when_network_leaves_partial_report(monkeypatch, tmp_path):
    runner = _load_runner()
    monkeypatch.setattr(runner, "_RESULTS_DIR", tmp_path / "test-results")
    monkeypatch.setattr(runner, "_TMP_DIR", tmp_path / "tmp")
    monkeypatch.setattr(runner.shutil, "which", lambda name: None)
    monkeypatch.setattr(runner, "_py_module_available", lambda name: name == "pip_audit")
    monkeypatch.setattr(runner, "_cmd_available", lambda name: False)
    monkeypatch.setattr(runner, "_is_https_reachable", lambda host: True)
    monkeypatch.setattr(runner, "_banner", lambda title: None)
    monkeypatch.setattr(runner, "_skip", lambda msg: None)
    monkeypatch.setattr(runner, "_warn", lambda msg: None)

    def fake_run_captured(cmd, **kwargs):
        if "pip_audit" not in cmd:
            return 0, ""
        report = Path(cmd[cmd.index("-o") + 1])
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text("{", encoding="utf-8")
        return 1, "ReadTimeout while connecting to pypi.org"

    monkeypatch.setattr(runner, "_run_captured", fake_run_captured)

    result = runner._stage_python_lint(Path(sys.executable))

    assert result.rc == 0
    assert any("pip-audit skipped (network)" in note for note in result.notes)


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


def test_optional_private_module_stage_skips_when_disabled(monkeypatch):
    runner = _load_runner()
    skips = []
    monkeypatch.setattr(runner, "_banner", lambda _title: None)
    monkeypatch.setattr(runner, "_skip", lambda message: skips.append(message))

    result = runner._stage_optional_private_module_static("skip")

    assert result.skipped is True
    assert result.rc == 0
    assert "disabled via --private-modules=skip" in result.notes[0]
    assert "disabled" in skips[0]


def test_optional_private_module_stage_skips_when_unavailable_in_auto_mode(monkeypatch, tmp_path):
    runner = _load_runner()
    skips = []
    monkeypatch.setattr(runner, "_banner", lambda _title: None)
    monkeypatch.setattr(runner, "_skip", lambda message: skips.append(message))
    monkeypatch.setattr(runner, "_OPTIONAL_PRIVATE_ENVELOPE_DIR", tmp_path / "missing-envelope")
    monkeypatch.setattr(
        runner,
        "_OPTIONAL_PRIVATE_ENVELOPE_ENTRYPOINT",
        tmp_path / "missing-envelope" / "ui" / "envelope-graphics.mjs",
    )

    result = runner._stage_optional_private_module_static("auto")

    assert result.skipped is True
    assert result.rc == 0
    assert "not checked out" in result.notes[0]
    assert "skipping optional private checks" in skips[0]


def test_optional_private_module_stage_fails_when_required_but_unavailable(monkeypatch, tmp_path):
    runner = _load_runner()
    failures = []
    monkeypatch.setattr(runner, "_banner", lambda _title: None)
    monkeypatch.setattr(runner, "_fail", lambda message: failures.append(message))
    monkeypatch.setattr(runner, "_OPTIONAL_PRIVATE_ENVELOPE_DIR", tmp_path / "missing-envelope")
    monkeypatch.setattr(
        runner,
        "_OPTIONAL_PRIVATE_ENVELOPE_ENTRYPOINT",
        tmp_path / "missing-envelope" / "ui" / "envelope-graphics.mjs",
    )

    result = runner._stage_optional_private_module_static("require")

    assert result.skipped is False
    assert result.rc == 1
    assert "not checked out" in result.notes[0]
    assert failures


def test_optional_private_module_stage_runs_lint_and_tests_when_available(monkeypatch, tmp_path):
    runner = _load_runner()
    envelope_dir = tmp_path / "envelope"
    (envelope_dir / "ui").mkdir(parents=True)
    (envelope_dir / "ui" / "envelope-graphics.mjs").write_text("export {}\n", encoding="utf-8")
    (envelope_dir / "package.json").write_text("{}\n", encoding="utf-8")
    (envelope_dir / "node_modules").mkdir()
    calls = []

    monkeypatch.setattr(runner, "_banner", lambda _title: None)
    monkeypatch.setattr(runner, "_OPTIONAL_PRIVATE_ENVELOPE_DIR", envelope_dir)
    monkeypatch.setattr(runner, "_OPTIONAL_PRIVATE_ENVELOPE_ENTRYPOINT", envelope_dir / "ui" / "envelope-graphics.mjs")
    monkeypatch.setattr(runner.shutil, "which", lambda name: "npm" if name in {"npm", "npm.cmd"} else None)
    monkeypatch.setattr(runner, "_missing_node_requirements", lambda **kwargs: [])

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs.get("cwd")))
        return 0

    monkeypatch.setattr(runner, "_run", fake_run)

    result = runner._stage_optional_private_module_static("auto")

    assert result.rc == 0
    assert result.skipped is False
    assert calls == [
        (["npm", "run", "lint:all"], envelope_dir),
        (["npm", "run", "test"], envelope_dir),
    ]


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


def test_js_unit_stage_writes_ci_junit_and_cobertura_coverage(monkeypatch, tmp_path):
    runner = _load_runner()
    captured = {"calls": []}
    original_exists = Path.exists
    performance_file = tmp_path / "automatic-stepwise-performance.test.mjs"
    performance_file.write_text("export {}\n", encoding="utf-8")

    monkeypatch.setattr(runner, "_banner", lambda title: None)
    monkeypatch.setattr(runner.shutil, "which", lambda name: name)
    monkeypatch.setattr(runner, "_RESULTS_DIR", _PROJECT_ROOT / "test-results")
    monkeypatch.setattr(runner, "_OPTIONAL_PRIVATE_ENVELOPE_PERFORMANCE_TEST", performance_file)

    def fake_exists(self):
        if "node_modules" in str(self):
            return True
        return original_exists(self)

    def fake_run(cmd, **kwargs):
        captured["calls"].append({"cmd": cmd, "label": kwargs.get("label")})
        return 0

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr(runner, "_run", fake_run)

    result = runner._stage_js_unit()

    assert result.rc == 0
    assert len(captured["calls"]) == 2
    assert captured["calls"][0]["label"] == "vitest --coverage"
    assert captured["calls"][1]["label"] == "vitest performance budgets"
    assert captured["calls"][0]["cmd"][:4] == [runner.shutil.which("npm"), "run", "test:unit:js:coverage", "--"]
    assert "--coverage.reporter=cobertura" in captured["calls"][0]["cmd"]
    assert any(str(part).endswith("vitest.xml") for part in captured["calls"][0]["cmd"])
    assert captured["calls"][1]["cmd"][:3] == [runner.shutil.which("npm"), "run", "test:unit:js:performance"]


def test_js_unit_stage_skips_private_performance_file_when_submodule_is_absent(monkeypatch, tmp_path):
    runner = _load_runner()
    calls = []
    skips = []
    original_exists = Path.exists

    monkeypatch.setattr(runner, "_banner", lambda title: None)
    monkeypatch.setattr(runner, "_skip", lambda message: skips.append(message))
    monkeypatch.setattr(runner.shutil, "which", lambda name: name)
    monkeypatch.setattr(runner, "_RESULTS_DIR", tmp_path / "test-results")
    monkeypatch.setattr(
        runner, "_OPTIONAL_PRIVATE_ENVELOPE_PERFORMANCE_TEST", tmp_path / "missing-performance.test.mjs"
    )

    def fake_exists(self):
        if "node_modules" in str(self):
            return True
        return original_exists(self)

    def fake_run(cmd, **kwargs):
        calls.append({"cmd": cmd, "label": kwargs.get("label")})
        return 0

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr(runner, "_run", fake_run)

    result = runner._stage_js_unit()

    assert result.rc == 0
    assert len(calls) == 1
    assert calls[0]["label"] == "vitest --coverage"
    assert result.notes == ["optional private Envelope performance tests not checked out"]
    assert skips == ["optional private Envelope performance tests not checked out"]


def test_js_unit_stage_respects_private_modules_skip_for_performance_file(monkeypatch, tmp_path):
    runner = _load_runner()
    calls = []
    skips = []
    original_exists = Path.exists
    performance_file = tmp_path / "automatic-stepwise-performance.test.mjs"
    performance_file.write_text("export {}\n", encoding="utf-8")

    monkeypatch.setattr(runner, "_banner", lambda title: None)
    monkeypatch.setattr(runner, "_skip", lambda message: skips.append(message))
    monkeypatch.setattr(runner.shutil, "which", lambda name: name)
    monkeypatch.setattr(runner, "_RESULTS_DIR", tmp_path / "test-results")
    monkeypatch.setattr(runner, "_OPTIONAL_PRIVATE_ENVELOPE_PERFORMANCE_TEST", performance_file)

    def fake_exists(self):
        if "node_modules" in str(self):
            return True
        return original_exists(self)

    def fake_run(cmd, **kwargs):
        calls.append({"cmd": cmd, "label": kwargs.get("label")})
        return 0

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr(runner, "_run", fake_run)

    result = runner._stage_js_unit("skip")

    assert result.rc == 0
    assert len(calls) == 1
    assert calls[0]["label"] == "vitest --coverage"
    assert result.notes == ["optional private Envelope performance tests disabled via --private-modules=skip"]
    assert skips == ["optional private Envelope performance tests disabled (--private-modules=skip)"]


def test_js_unit_stage_requires_private_performance_file_when_private_modules_required(monkeypatch, tmp_path):
    runner = _load_runner()
    calls = []
    failures = []
    original_exists = Path.exists

    monkeypatch.setattr(runner, "_banner", lambda title: None)
    monkeypatch.setattr(runner, "_fail", lambda message: failures.append(message))
    monkeypatch.setattr(runner.shutil, "which", lambda name: name)
    monkeypatch.setattr(runner, "_RESULTS_DIR", tmp_path / "test-results")
    monkeypatch.setattr(
        runner, "_OPTIONAL_PRIVATE_ENVELOPE_PERFORMANCE_TEST", tmp_path / "missing-performance.test.mjs"
    )

    def fake_exists(self):
        if "node_modules" in str(self):
            return True
        return original_exists(self)

    def fake_run(cmd, **kwargs):
        calls.append({"cmd": cmd, "label": kwargs.get("label")})
        return 0

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr(runner, "_run", fake_run)

    result = runner._stage_js_unit("require")

    assert result.rc == 1
    assert len(calls) == 1
    assert calls[0]["label"] == "vitest --coverage"
    assert result.notes == ["optional private Envelope performance tests not checked out"]
    assert failures == ["optional private Envelope performance tests not checked out"]


def test_js_lint_eslint_skip_mentions_production_image_probes(monkeypatch, tmp_path):
    runner = _load_runner()
    node_modules = tmp_path / "node_modules"
    node_modules.mkdir()
    skips = []

    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner.shutil, "which", lambda name: "npx" if name in {"npx", "npx.cmd"} else None)
    monkeypatch.setattr(runner, "_cmd_available", lambda _name: False)
    monkeypatch.setattr(runner, "_banner", lambda _title: None)
    monkeypatch.setattr(runner, "_skip", lambda message: skips.append(message))

    result = runner._stage_js_lint()

    assert result.rc == 0
    assert "eslint not installed in node_modules" in skips[0]
    assert "production-image probes" in skips[0]


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
    monkeypatch.setattr(runner, "wait_for_websocket_protocol_ready", lambda _ws_url, _endpoint, **_kwargs: None)

    started, ready, proc = runner._maybe_start_websocket_backend(Path("python"), "localhost", 8001)

    assert started is False
    assert ready is True
    assert proc is None


def test_websocket_backend_does_not_start_remote_host(monkeypatch):
    runner = _load_runner()
    monkeypatch.setattr(
        runner,
        "wait_for_websocket_protocol_ready",
        lambda _ws_url, _endpoint, **_kwargs: "ConnectionRefusedError: connection refused",
    )

    started, ready, proc = runner._maybe_start_websocket_backend(Path("python"), "example.com", 8001)

    assert started is False
    assert ready is False
    assert proc is None


def test_websocket_backend_auto_start_sets_ws_port(monkeypatch):
    runner = _load_runner()
    created = {}
    monkeypatch.setenv("OPCUA_TEST_ENDPOINT", "opc.tcp://localhost:40463")

    class FakeProc:
        def poll(self):
            return None

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
    probe_results = iter(["ConnectionRefusedError: connection refused", None])
    monkeypatch.setattr(
        runner,
        "wait_for_websocket_protocol_ready",
        lambda _ws_url, _endpoint, **_kwargs: next(probe_results),
    )
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
    monkeypatch.setattr(runner, "_probe_opcua_protocol", lambda _endpoint, **_kwargs: None)

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


def test_simulator_instance_dir_uses_short_temp_root(monkeypatch):
    runner = _load_runner()
    github_runner_temp = r"D:\a\_temp" if runner.IS_WINDOWS else "/home/runner/work/_temp"
    monkeypatch.setenv("RUNNER_TEMP", github_runner_temp)
    monkeypatch.delenv("IJT_SIMULATOR_INSTANCE_ROOT", raising=False)

    instance_dir = runner._simulator_instance_dir(40466)

    assert instance_dir.name == "40466"
    assert "ijt-sim" in instance_dir.parts
    assert len(os.fspath(instance_dir)) <= runner._MAX_SIMULATOR_INSTANCE_PATH
    assert _PROJECT_ROOT not in instance_dir.parents


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


def test_simulator_launch_fails_fast_when_process_exits_before_protocol_probe(monkeypatch, tmp_path):
    runner = _load_runner()
    executable = _make_simulator_executable(tmp_path)
    instance_dir = tmp_path / "instance"
    probe_called = False

    class FakeProc:
        def __init__(self):
            self.poll_results = iter([None, 1])

        def poll(self):
            return next(self.poll_results)

    def fail_probe(_endpoint, **_kwargs):
        nonlocal probe_called
        probe_called = True
        raise AssertionError("protocol probe must not run after simulator process exits")

    monkeypatch.setattr(runner, "_MAX_SIMULATOR_INSTANCE_PATH", 4096)
    monkeypatch.setattr(runner, "_simulator_instance_dir", lambda _port: instance_dir)
    monkeypatch.setattr(runner, "_start_process_with_opcua_logs", lambda _cmd, *, cwd, port: FakeProc())
    monkeypatch.setattr(runner, "_port_open", lambda _host, _port, timeout=1.0: False)
    monkeypatch.setattr(runner, "_probe_opcua_protocol", fail_probe)
    monkeypatch.setattr(runner.time, "sleep", lambda _seconds: None)

    result = runner._launch_simulator_instance(40470, str(executable))

    assert result is None
    assert probe_called is False
    assert not instance_dir.exists()


def test_simulator_launch_surfaces_err_log_signature_when_process_exits_mid_wait(monkeypatch, tmp_path):
    runner = _load_runner()
    executable = _make_simulator_executable(tmp_path)
    instance_dir = _patch_simulator_launch_common(monkeypatch, runner, tmp_path)
    warnings = []

    class FakeProc:
        def __init__(self):
            self.poll_results = iter([None, 1])

        def poll(self):
            return next(self.poll_results)

    def fake_start(_cmd, *, cwd, port):
        _, err_log = runner._opcua_server_log_paths(port)
        err_log.parent.mkdir(parents=True, exist_ok=True)
        err_log.write_text("server-instance creation failed: 0x80010000\n", encoding="utf-8")
        return FakeProc()

    def fail_probe(_endpoint, **_kwargs):
        raise AssertionError("protocol probe must not run after simulator process exits")

    monkeypatch.setattr(runner, "MAX_SIMULATOR_LAUNCH_ATTEMPTS", 1)
    monkeypatch.setattr(runner, "_start_process_with_opcua_logs", fake_start)
    monkeypatch.setattr(runner, "_port_open", lambda _host, _port, timeout=1.0: False)
    monkeypatch.setattr(runner, "_probe_opcua_protocol", fail_probe)
    monkeypatch.setattr(runner, "_warn", lambda message: warnings.append(message))

    result = runner._launch_simulator_instance(40470, str(executable))

    assert result is None
    assert not instance_dir.exists()
    assert any("0x80010000" in warning for warning in warnings)


def test_simulator_launch_fails_when_protocol_probe_fails_after_tcp_open(monkeypatch, tmp_path):
    runner = _load_runner()
    executable = _make_simulator_executable(tmp_path)
    instance_dir = tmp_path / "instance"

    class FakeProc:
        def __init__(self):
            self.terminated = False
            self.killed = False

        def poll(self):
            return None

        def terminate(self):
            self.terminated = True

        def wait(self, timeout=None):
            return 0

        def kill(self):
            self.killed = True

    proc = FakeProc()
    warnings = []

    monkeypatch.setattr(runner, "_MAX_SIMULATOR_INSTANCE_PATH", 4096)
    monkeypatch.setattr(runner, "_simulator_instance_dir", lambda _port: instance_dir)
    monkeypatch.setattr(runner, "_start_process_with_opcua_logs", lambda _cmd, *, cwd, port: proc)
    monkeypatch.setattr(runner, "_port_open", lambda _host, _port, timeout=1.0: True)
    monkeypatch.setattr(runner, "_probe_opcua_protocol", lambda _endpoint, **_kwargs: "BadServerNotConnected")
    monkeypatch.setattr(runner, "_warn", lambda message: warnings.append(message))

    result = runner._launch_simulator_instance(40470, str(executable))

    assert result is None
    assert proc.terminated is True
    assert proc.killed is False
    assert not instance_dir.exists()
    assert any("BadServerNotConnected" in warning for warning in warnings)


def test_launch_retries_once_on_known_signature(monkeypatch, tmp_path):
    runner = _load_runner()
    executable = _make_simulator_executable(tmp_path)
    instance_dir = _patch_simulator_launch_common(monkeypatch, runner, tmp_path)
    start_calls = []
    probe_errors = iter(["BadServerNotConnected", None])

    class FakeProc:
        def __init__(self):
            self.terminated = False
            self.killed = False

        def poll(self):
            return None

        def terminate(self):
            self.terminated = True

        def wait(self, timeout=None):
            return 0

        def kill(self):
            self.killed = True

    def fake_start(_cmd, *, cwd, port):
        proc = FakeProc()
        start_calls.append(proc)
        if len(start_calls) == 1:
            _, err_log = runner._opcua_server_log_paths(port)
            err_log.parent.mkdir(parents=True, exist_ok=True)
            err_log.write_text("server-instance creation failed: 0x80010000\n", encoding="utf-8")
        return proc

    monkeypatch.setattr(runner, "_start_process_with_opcua_logs", fake_start)
    monkeypatch.setattr(runner, "_port_open", lambda _host, _port, timeout=1.0: True)
    monkeypatch.setattr(runner, "_probe_opcua_protocol", lambda _endpoint, **_kwargs: next(probe_errors))

    result = runner._launch_simulator_instance(40470, str(executable))

    assert result is not None
    assert result.tmp_dir == instance_dir
    assert result.proc is start_calls[1]
    assert len(start_calls) == 2
    assert start_calls[0].terminated is True
    notes = runner._consume_simulator_launch_notes()
    assert any("simulator-launch-retry: attempt=1/2 signature=0x80010000" in note for note in notes)
    events = (runner._TIMING_HISTORY).read_text(encoding="utf-8").splitlines()
    assert len(events) == 1
    assert json.loads(events[0])["event"] == "simulator_launch_retry"


def test_launch_does_not_retry_on_unknown_failure(monkeypatch, tmp_path):
    runner = _load_runner()
    executable = _make_simulator_executable(tmp_path)
    _patch_simulator_launch_common(monkeypatch, runner, tmp_path)
    start_calls = []

    class FakeProc:
        def poll(self):
            return None

        def terminate(self):
            return None

        def wait(self, timeout=None):
            return 0

        def kill(self):
            return None

    def fake_start(_cmd, *, cwd, port):
        start_calls.append(port)
        _, err_log = runner._opcua_server_log_paths(port)
        err_log.parent.mkdir(parents=True, exist_ok=True)
        err_log.write_text("unexpected startup failure\n", encoding="utf-8")
        return FakeProc()

    monkeypatch.setattr(runner, "_start_process_with_opcua_logs", fake_start)
    monkeypatch.setattr(runner, "_port_open", lambda _host, _port, timeout=1.0: True)
    monkeypatch.setattr(runner, "_probe_opcua_protocol", lambda _endpoint, **_kwargs: "BadServerNotConnected")

    result = runner._launch_simulator_instance(40470, str(executable))

    assert result is None
    assert start_calls == [40470]
    assert not (runner._TIMING_HISTORY).exists()
    assert not any("simulator-launch-retry" in note for note in runner._consume_simulator_launch_notes())


def test_launch_caps_retries_at_two(monkeypatch, tmp_path):
    runner = _load_runner()
    executable = _make_simulator_executable(tmp_path)
    _patch_simulator_launch_common(monkeypatch, runner, tmp_path)
    start_calls = []

    class FakeProc:
        def poll(self):
            return None

        def terminate(self):
            return None

        def wait(self, timeout=None):
            return 0

        def kill(self):
            return None

    def fake_start(_cmd, *, cwd, port):
        start_calls.append(port)
        _, err_log = runner._opcua_server_log_paths(port)
        err_log.parent.mkdir(parents=True, exist_ok=True)
        err_log.write_text("server-instance creation failed: 0x80010000\n", encoding="utf-8")
        return FakeProc()

    monkeypatch.setattr(runner, "_start_process_with_opcua_logs", fake_start)
    monkeypatch.setattr(runner, "_port_open", lambda _host, _port, timeout=1.0: True)
    monkeypatch.setattr(runner, "_probe_opcua_protocol", lambda _endpoint, **_kwargs: "BadServerNotConnected")

    result = runner._launch_simulator_instance(40470, str(executable))

    assert result is None
    assert start_calls == [40470, 40470]
    events = (runner._TIMING_HISTORY).read_text(encoding="utf-8").splitlines()
    assert len(events) == 1


def test_feature_worker_pool_does_not_start_websocket_workers_after_simulator_readiness_failure(monkeypatch):
    runner = _load_runner()
    launched_ports = []
    stopped_ports = []

    class FakeProc:
        pass

    def fake_launch(port, _exe):
        launched_ports.append(port)
        if port == 4101:
            return None
        return runner._OpcuaServerInstance(port=port, proc=FakeProc(), tmp_dir=None)

    def fail_start_ws(*_args, **_kwargs):
        raise AssertionError("WebSocket workers must not start until every simulator is protocol-ready")

    monkeypatch.delenv("OPCUA_TEST_ENDPOINT", raising=False)
    monkeypatch.delenv("OPCUA_SERVER_URL", raising=False)
    monkeypatch.setenv("OPCUA_SERVER_PORT", "4100")
    monkeypatch.setattr(runner, "_port_open", lambda _host, _port, timeout=1.0: False)
    monkeypatch.setattr(runner, "_find_simulator_executable", lambda: "simulator.exe")
    monkeypatch.setattr(runner, "_launch_simulator_instance", fake_launch)
    monkeypatch.setattr(runner, "_maybe_start_websocket_backend", fail_start_ws)
    monkeypatch.setattr(runner, "_stop_opcua_server_instance", lambda instance: stopped_ports.append(instance.port))

    result = runner._run_playwright_features_with_owned_pool(
        python=Path("python"),
        name="playwright-features",
        ws_url="ws://localhost:9000",
        ui_url="http://127.0.0.1:3005",
        workers=2,
    )

    assert result.rc == 1
    assert result.notes == ["OPC UA worker 1 failed to start on port 4101"]
    assert launched_ports == [4100, 4101]
    assert stopped_ports == [4100]


def test_websocket_backend_readiness_failure_terminates_owned_backend(monkeypatch, tmp_path):
    runner = _load_runner()

    class FakeProc:
        def __init__(self):
            self.terminated = False
            self.killed = False

        def poll(self):
            return None

        def terminate(self):
            self.terminated = True

        def wait(self, timeout=None):
            return 0

        def kill(self):
            self.killed = True

    proc = FakeProc()

    monkeypatch.setattr(runner, "_RESULTS_DIR", tmp_path)
    monkeypatch.setattr(runner.subprocess, "Popen", lambda *_args, **_kwargs: proc)
    probe_results = iter(["ConnectionRefusedError: connection refused", "backend readiness response timed out"])
    monkeypatch.setattr(
        runner,
        "wait_for_websocket_protocol_ready",
        lambda _ws_url, _endpoint, **_kwargs: next(probe_results),
    )

    started, ready, returned_proc = runner._maybe_start_websocket_backend(
        Path(sys.executable),
        "localhost",
        9000,
        opcua_endpoint="opc.tcp://localhost:4100",
    )

    assert (started, ready, returned_proc) == (True, False, None)
    assert proc.terminated is True
    assert proc.killed is False


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


def test_simulator_package_order_follows_host_platform():
    runner = _load_runner()

    first_package = runner._SIMULATOR_PACKAGE_ZIPS[0].name
    first_executable = runner._WELL_KNOWN_SIMULATOR_PATHS[0].name
    if runner.IS_WINDOWS:
        assert first_package == "OPC_UA_IJT_Server_Simulator.zip"
        assert first_executable == "opcua_ijt_demo_application.exe"
    else:
        assert first_package == "OPC_UA_IJT_Server_Simulator_Linux.zip"
        assert first_executable == "opcua_ijt_demo_application"


def test_playwright_install_skips_with_deps_on_windows(monkeypatch):
    runner = _load_runner()
    calls = []

    monkeypatch.setattr(runner, "IS_WINDOWS", True)
    monkeypatch.setattr(runner, "_node_bin_path", lambda name: "playwright.cmd")
    monkeypatch.setattr(runner, "_banner", lambda title: None)
    monkeypatch.setattr(runner, "_warn", lambda message: None)
    monkeypatch.setattr(runner, "_playwright_chromium_available", lambda: False)
    monkeypatch.setattr(runner, "_node_tls_download_preflight", lambda node: None)

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return 0

    monkeypatch.setattr(runner, "_run", fake_run)

    result = runner._stage_playwright_install()

    assert result.rc == 0
    assert calls == [["playwright.cmd", "install", "chromium"]]


def test_playwright_install_uses_with_deps_on_linux(monkeypatch):
    """Linux ``_stage_playwright_install`` must invoke ``--with-deps`` when
    Chromium is not already present.

    Post-PR-B context: the Integration ``live-webclient-browser`` job runs
    each suite **inside** the owned ``ijt-browser-ci`` image (digest pinned
    via ``.github/docker/ijt-browser-ci/image-pin.json``) under
    ``docker run --network=none``. The image bakes Chromium at
    ``PLAYWRIGHT_BROWSERS_PATH=/ms-playwright`` against the locked
    ``@playwright/test`` version in ``package.json``, so in the real CI run
    ``_playwright_chromium_available()`` is True and this stage short-circuits
    (see ``test_playwright_install_short_circuits_when_chromium_present``).

    However, the ``--with-deps`` Linux path is still the contract for any
    Linux execution where Chromium is **not** already present — for example,
    a developer running the suite locally on a fresh Linux/WSL host, or a
    future contingency where someone runs this stage outside the
    ``ijt-browser-ci`` image. Dropping ``--with-deps`` from that path would
    silently install the browser binary without its Linux system libraries
    and fail at first launch. This test guards that fallback contract.
    """
    runner = _load_runner()
    calls = []

    monkeypatch.setattr(runner, "IS_WINDOWS", False)
    monkeypatch.setattr(runner, "IS_CI", True)
    monkeypatch.setattr(runner, "_node_bin_path", lambda name: "/usr/local/bin/playwright")
    monkeypatch.setattr(runner, "_banner", lambda title: None)
    monkeypatch.setattr(runner, "_warn", lambda message: None)
    monkeypatch.setattr(runner, "_playwright_chromium_available", lambda: False)
    monkeypatch.setattr(runner, "_node_tls_download_preflight", lambda node: None)

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return 0

    monkeypatch.setattr(runner, "_run", fake_run)

    result = runner._stage_playwright_install()

    assert result.rc == 0
    assert calls == [["/usr/local/bin/playwright", "install", "chromium", "--with-deps"]], (
        "Linux `_stage_playwright_install` must invoke "
        "`playwright install chromium --with-deps` whenever Chromium is not "
        "already present. In the Integration `live-webclient-browser` job "
        "this stage normally short-circuits because Chromium is baked into "
        "the `ijt-browser-ci` image, but if this Linux path is ever reached "
        "(local Linux dev, image regression, etc.) dropping `--with-deps` "
        "would leave Chromium without its Linux system libraries and fail "
        "at first launch."
    )


def test_playwright_install_fails_fast_in_ci_when_with_deps_fails(monkeypatch):
    """CI Linux must not silently fall back to bare ``playwright install chromium``.

    Post-PR-B the Integration ``live-webclient-browser`` job runs inside the
    owned ``ijt-browser-ci`` image where Chromium is pre-installed, so this
    stage normally short-circuits. But if a future image rebuild fails to bake
    Chromium, or a contributor runs the runner in a CI-shaped environment
    without the image, the only remaining path that installs system libraries
    is ``--with-deps``. A bare fallback would let install report success while
    the actual browser launch would fail later inside the Playwright suite
    with an opaque error. This test guards that CI fail-fast contract.
    """
    runner = _load_runner()
    calls = []

    monkeypatch.setattr(runner, "IS_WINDOWS", False)
    monkeypatch.setattr(runner, "IS_CI", True)
    monkeypatch.setattr(runner, "_node_bin_path", lambda name: "/usr/local/bin/playwright")
    monkeypatch.setattr(runner, "_banner", lambda title: None)
    monkeypatch.setattr(runner, "_warn", lambda message: None)
    monkeypatch.setattr(runner, "_playwright_chromium_available", lambda: False)
    monkeypatch.setattr(runner, "_node_tls_download_preflight", lambda node: None)

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return 1

    monkeypatch.setattr(runner, "_run", fake_run)

    result = runner._stage_playwright_install()

    assert result.rc == 1
    assert calls == [["/usr/local/bin/playwright", "install", "chromium", "--with-deps"]], (
        "In CI on Linux the install stage must fail fast on `--with-deps` "
        "failure and must NOT retry with a bare `playwright install chromium`. "
        "Falling back would mask missing system libraries and surface as an "
        "opaque browser-launch failure later in the Playwright suite."
    )
    assert "Browser download failed" in result.notes[0]


def test_playwright_install_retries_without_with_deps_on_local_linux(monkeypatch):
    """Local (non-CI) Linux retains the developer-convenience fallback.

    On a developer Linux machine the Chromium system libraries are
    almost always already installed by the distro, so ``--with-deps``
    can fail purely because ``sudo`` is unavailable or the package
    manager is locked. In that case retrying without ``--with-deps``
    succeeds and the developer gets a working browser without manual
    intervention. The fallback is gated to ``not IS_CI`` so it never
    masks the CI contract.
    """
    runner = _load_runner()
    calls = []

    monkeypatch.setattr(runner, "IS_WINDOWS", False)
    monkeypatch.setattr(runner, "IS_CI", False)
    monkeypatch.setattr(runner, "_node_bin_path", lambda name: "/usr/local/bin/playwright")
    monkeypatch.setattr(runner, "_banner", lambda title: None)
    monkeypatch.setattr(runner, "_warn", lambda message: None)
    monkeypatch.setattr(runner, "_playwright_chromium_available", lambda: False)
    monkeypatch.setattr(runner, "_node_tls_download_preflight", lambda node: None)

    rcs = iter([1, 0])

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return next(rcs)

    monkeypatch.setattr(runner, "_run", fake_run)

    result = runner._stage_playwright_install()

    assert result.rc == 0
    assert calls == [
        ["/usr/local/bin/playwright", "install", "chromium", "--with-deps"],
        ["/usr/local/bin/playwright", "install", "chromium"],
    ]


def test_playwright_install_retries_with_tls_bypass_when_preflight_fails(monkeypatch):
    runner = _load_runner()
    warnings: list[str] = []
    infos: list[str] = []
    captured_envs: list[dict] = []

    monkeypatch.setattr(runner, "_node_bin_path", lambda name: f"{name}.cmd")
    monkeypatch.setattr(runner, "_node_executable_path", lambda: "node.exe")
    monkeypatch.setattr(runner, "_banner", lambda title: None)
    monkeypatch.setattr(runner, "_warn", warnings.append)
    monkeypatch.setattr(runner, "_info", infos.append)
    monkeypatch.setattr(runner, "_playwright_chromium_available", lambda: False)
    monkeypatch.setattr(runner, "IS_WINDOWS", True)
    monkeypatch.setattr(
        runner,
        "_node_tls_download_preflight",
        lambda node: "Node cannot validate Playwright CDN TLS (UNABLE_TO_GET_ISSUER_CERT_LOCALLY)",
    )

    def mock_run(cmd, *, label="", env=None, **kwargs):
        captured_envs.append(env or {})
        return 0

    monkeypatch.setattr(runner, "_run", mock_run)

    result = runner._stage_playwright_install()

    assert result.rc == 0
    assert any("TLS bypass" in n for n in result.notes)
    assert captured_envs[0].get("NODE_TLS_REJECT_UNAUTHORIZED") == "0"
    assert any("UNABLE_TO_GET_ISSUER_CERT_LOCALLY" in w for w in warnings)


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
        "--compatibility-smoke-only",
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
        "compatibility_smoke_only",
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
        (_target_args(compatibility_smoke_only=True), (True, True)),
    ]

    for args, expected in cases:
        requirements = runner._target_only_dependency_requirements(args)
        assert (requirements.python, requirements.npm) == expected


def test_target_only_dependencies_run_before_target_stage(monkeypatch, tmp_path):
    runner = _load_runner()
    calls = []

    monkeypatch.setattr(sys, "argv", ["run_all_tests.py", "--playwright-features-only"])
    monkeypatch.setattr(runner, "IS_CI", True)
    monkeypatch.setattr(runner, "_ENV_IS_PRE_ISOLATED", True)
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


def test_compatibility_smoke_target_uses_owned_services_without_chromium_install(monkeypatch):
    runner = _load_runner()
    calls = []

    monkeypatch.setattr(sys, "argv", ["run_all_tests.py", "--compatibility-smoke-only"])
    monkeypatch.setattr(runner, "IS_CI", True)
    monkeypatch.setattr(runner, "_ENV_IS_PRE_ISOLATED", True)
    monkeypatch.setattr(runner, "_RESULTS_DIR", _PROJECT_ROOT / "test-results" / "unit-compatibility-smoke-target")
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

    def fail_if_chromium_install_runs():
        raise AssertionError("Compatibility smoke must use the configured real browser, not install Chromium")

    def fake_owned_services(**kwargs):
        calls.append(f"owned:{kwargs['name']}:{kwargs['need_ws']}")
        return kwargs["stage"]()

    monkeypatch.setattr(runner, "_stage_playwright_install", fail_if_chromium_install_runs)
    monkeypatch.setattr(
        runner,
        "_stage_playwright_ffmpeg_install",
        lambda: calls.append("ffmpeg") or runner.StageResult("playwright-ffmpeg-install", 0),
    )
    monkeypatch.setattr(runner, "_run_with_owned_services", fake_owned_services)
    monkeypatch.setattr(
        runner,
        "_stage_playwright_compatibility_smoke",
        lambda ws_url, ui_url: (
            calls.append(f"smoke:{ws_url}:{ui_url}") or runner.StageResult("playwright-compatibility-smoke", 0)
        ),
    )

    assert runner.main() == 0
    assert calls == [
        "pip",
        "npm",
        "ffmpeg",
        "owned:playwright-compatibility-smoke:True",
        "smoke:ws://localhost:8004:http://127.0.0.1:3007",
    ]


def test_target_only_dependency_failure_stops_before_live_stage(monkeypatch, tmp_path):
    runner = _load_runner()

    monkeypatch.setattr(sys, "argv", ["run_all_tests.py", "--python-opcua-only"])
    monkeypatch.setattr(runner, "IS_CI", True)
    monkeypatch.setattr(runner, "_ENV_IS_PRE_ISOLATED", True)
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


def _phase1_lane_runner(monkeypatch, tmp_path, argv):
    runner = _load_runner()
    calls = []

    monkeypatch.setattr(sys, "argv", ["run_all_tests.py", *argv])
    monkeypatch.setattr(runner, "IS_CI", True)
    monkeypatch.setattr(runner, "_ENV_IS_PRE_ISOLATED", True)
    monkeypatch.setattr(runner, "_RESULTS_DIR", tmp_path / "results")
    monkeypatch.setattr(runner, "_cleanup_caches", lambda root: None)
    monkeypatch.setattr(runner, "_prepare_tmp_dir", lambda: None)
    monkeypatch.setattr(runner, "_port_open", lambda *args, **kwargs: False)
    monkeypatch.setattr(runner, "_docker_available", lambda: False)
    monkeypatch.setattr(runner, "_write_timing_artifacts", lambda *args, **kwargs: None)

    def stage(name):
        return lambda *args, **kwargs: calls.append(name) or runner.StageResult(name, 0)

    monkeypatch.setattr(runner, "_stage_versions", stage("versions"))
    monkeypatch.setattr(runner, "_stage_pip_install", stage("pip-install"))
    monkeypatch.setattr(runner, "_stage_npm_install", stage("npm-install"))
    monkeypatch.setattr(runner, "_stage_python_lint", stage("python-lint"))
    monkeypatch.setattr(runner, "_stage_python_unit", stage("python-unit"))
    monkeypatch.setattr(runner, "_stage_js_lint", stage("js-lint"))
    monkeypatch.setattr(runner, "_stage_js_unit", stage("js-unit"))
    monkeypatch.setattr(runner, "_stage_optional_private_module_static", lambda _mode: stage("private-module-static")())
    monkeypatch.setattr(runner, "_stage_infra_lint", stage("infra-lint"))
    return runner, calls


def test_phase1_python_runs_python_lane_without_js(monkeypatch, tmp_path):
    runner, calls = _phase1_lane_runner(monkeypatch, tmp_path, ["--phase1-python"])

    assert runner.main() == 0
    assert calls == ["versions", "pip-install", "python-lint", "python-unit", "infra-lint"]


def test_phase1_js_runs_js_lane_without_python(monkeypatch, tmp_path):
    runner, calls = _phase1_lane_runner(monkeypatch, tmp_path, ["--phase1-js"])

    assert runner.main() == 0
    assert calls == ["versions", "npm-install", "js-lint", "js-unit", "private-module-static"]


def test_phase1_lane_flags_reject_conflicting_modes(monkeypatch, tmp_path):
    cases = [
        ["--phase1", "--phase1-python"],
        ["--phase1-python", "--phase1-js"],
        ["--phase2", "--phase1-js"],
        ["--docker-only", "--phase1-python"],
        ["--all", "--phase1-python"],
        ["--integration", "--phase1-python"],
        ["--e2e", "--phase1-js"],
        ["--python-opcua-only", "--phase1-python"],
    ]

    for argv in cases:
        runner, _calls = _phase1_lane_runner(monkeypatch, tmp_path, argv)
        with pytest.raises(SystemExit) as excinfo:
            runner.main()
        assert excinfo.value.code == 2


def test_phase1_lane_mode_names_are_distinct():
    runner = _load_runner()
    base = {
        "phase1": False,
        "phase1_python": False,
        "phase1_js": False,
        "phase2": False,
        "docker_only": False,
    }

    assert runner._mode_name(SimpleNamespace(**{**base, "phase1_python": True}), False) == "phase1-python"
    assert runner._mode_name(SimpleNamespace(**{**base, "phase1_js": True}), False) == "phase1-js"


def test_parse_int_env_treats_empty_and_whitespace_as_unset(monkeypatch, recwarn):
    """Regression: integration.yml passes IJT_PLAYWRIGHT_FEATURE_WORKERS='' when
    a matrix row omits feature_workers.  That deliberate empty-string fallback
    must not emit a UserWarning — treat it the same as an unset variable.
    """
    runner = _load_runner()
    monkeypatch.delenv("_IJT_RELAUNCHED", raising=False)

    monkeypatch.setenv("IJT_X_PARSE_INT_TEST", "")
    assert runner._parse_int_env("IJT_X_PARSE_INT_TEST", 7) == 7

    monkeypatch.setenv("IJT_X_PARSE_INT_TEST", "   ")
    assert runner._parse_int_env("IJT_X_PARSE_INT_TEST", 7) == 7

    assert not [w for w in recwarn.list if issubclass(w.category, UserWarning)]


def test_parse_int_env_warns_on_garbage_value(monkeypatch):
    """Non-empty, non-numeric values still warn so misconfiguration is visible."""
    runner = _load_runner()
    monkeypatch.delenv("_IJT_RELAUNCHED", raising=False)
    monkeypatch.setenv("IJT_X_PARSE_INT_TEST", "abc")

    with pytest.warns(UserWarning, match="not a valid integer"):
        assert runner._parse_int_env("IJT_X_PARSE_INT_TEST", 7) == 7


def test_parse_playwright_shard_returns_none_when_unset():
    runner = _load_runner()
    assert runner._parse_playwright_shard(None) == (None, "")
    assert runner._parse_playwright_shard("") == (None, "")
    assert runner._parse_playwright_shard("   ") == (None, "")


def test_parse_playwright_shard_valid_value():
    runner = _load_runner()
    assert runner._parse_playwright_shard("1/2") == ("--shard=1/2", "-shard-1of2")
    assert runner._parse_playwright_shard(" 2/3 ") == ("--shard=2/3", "-shard-2of3")
    assert runner._parse_playwright_shard("1/1") == ("--shard=1/1", "-shard-1of1")


def test_parse_playwright_shard_invalid_fails_closed():
    runner = _load_runner()

    for bad in ["abc", "1", "1/2/3", "0/2", "3/2", "1/0", "-1/2"]:
        with pytest.raises(ValueError, match="IJT_PLAYWRIGHT_SHARD"):
            runner._parse_playwright_shard(bad)


def test_playwright_project_passes_shard_arg_and_renames_junit(monkeypatch, tmp_path):
    runner = _load_runner()
    captured = {}

    monkeypatch.setattr(runner, "_node_bin_path", lambda name: "playwright.cmd")
    monkeypatch.setattr(runner, "_banner", lambda title: None)
    monkeypatch.setattr(runner, "_RESULTS_DIR", tmp_path)
    monkeypatch.setenv("IJT_PLAYWRIGHT_SHARD", "1/2")

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["env"] = kwargs["env"]
        captured["label"] = kwargs.get("label")
        return 0

    monkeypatch.setattr(runner, "_run", fake_run)

    result = runner._stage_playwright_project(
        project="features",
        name="playwright-features",
        title="test",
        ws_url="ws://localhost:8005",
        ui_url="http://127.0.0.1:3005",
        workers=2,
    )

    assert result.rc == 0
    assert "--shard=1/2" in captured["cmd"]
    assert "--workers=2" in captured["cmd"]
    expected_junit = str(tmp_path / "playwright-features-shard-1of2.xml")
    assert captured["env"]["PLAYWRIGHT_JUNIT_OUTPUT_FILE"] == expected_junit
    assert "shard-1of2" in (captured["label"] or "")


def test_playwright_project_reads_shard_from_extra_env(monkeypatch, tmp_path):
    runner = _load_runner()
    captured = {}

    monkeypatch.setattr(runner, "_node_bin_path", lambda name: "playwright.cmd")
    monkeypatch.setattr(runner, "_banner", lambda title: None)
    monkeypatch.setattr(runner, "_RESULTS_DIR", tmp_path)
    monkeypatch.delenv("IJT_PLAYWRIGHT_SHARD", raising=False)

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["env"] = kwargs["env"]
        return 0

    monkeypatch.setattr(runner, "_run", fake_run)

    runner._stage_playwright_project(
        project="features",
        name="playwright-features",
        title="test",
        ws_url="ws://localhost:8005",
        ui_url="http://127.0.0.1:3005",
        workers=2,
        extra_env={"IJT_PLAYWRIGHT_SHARD": "2/2"},
    )

    assert "--shard=2/2" in captured["cmd"]
    assert captured["env"]["PLAYWRIGHT_JUNIT_OUTPUT_FILE"].endswith("playwright-features-shard-2of2.xml")


def test_playwright_project_invalid_shard_fails_before_running(monkeypatch, tmp_path):
    runner = _load_runner()
    calls = []

    monkeypatch.setattr(runner, "_node_bin_path", lambda name: "playwright.cmd")
    monkeypatch.setattr(runner, "_banner", lambda title: None)
    monkeypatch.setattr(runner, "_RESULTS_DIR", tmp_path)
    monkeypatch.setenv("IJT_PLAYWRIGHT_SHARD", "2/1")
    monkeypatch.setattr(runner, "_run", lambda *args, **kwargs: calls.append(args) or 0)

    result = runner._stage_playwright_project(
        project="features",
        name="playwright-features",
        title="test",
        ws_url="ws://localhost:8005",
        ui_url="http://127.0.0.1:3005",
        workers=2,
    )

    assert result.rc == 1
    assert any("IJT_PLAYWRIGHT_SHARD" in note for note in result.notes)
    assert calls == []


def test_playwright_project_unset_shard_keeps_old_filename(monkeypatch, tmp_path):
    runner = _load_runner()
    captured = {}

    monkeypatch.setattr(runner, "_node_bin_path", lambda name: "playwright.cmd")
    monkeypatch.setattr(runner, "_banner", lambda title: None)
    monkeypatch.setattr(runner, "_RESULTS_DIR", tmp_path)
    monkeypatch.delenv("IJT_PLAYWRIGHT_SHARD", raising=False)

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["env"] = kwargs["env"]
        return 0

    monkeypatch.setattr(runner, "_run", fake_run)

    runner._stage_playwright_project(
        project="features",
        name="playwright-features",
        title="test",
        ws_url="ws://localhost:8005",
        ui_url="http://127.0.0.1:3005",
        workers=2,
    )

    assert not any(arg.startswith("--shard=") for arg in captured["cmd"])
    expected_junit = str(tmp_path / "playwright-features.xml")
    assert captured["env"]["PLAYWRIGHT_JUNIT_OUTPUT_FILE"] == expected_junit


def test_playwright_compatibility_smoke_stage_uses_smoke_config(monkeypatch):
    runner = _load_runner()
    captured = {}

    monkeypatch.setattr(runner, "_node_bin_path", lambda name: "playwright.cmd")
    monkeypatch.setattr(runner, "_banner", lambda title: None)
    monkeypatch.setattr(runner, "_RESULTS_DIR", _PROJECT_ROOT / "test-results" / "unit-compatibility-smoke-stage")

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["env"] = kwargs["env"]
        captured["timeout"] = kwargs["timeout"]
        return 0

    monkeypatch.setattr(runner, "_run", fake_run)

    result = runner._stage_playwright_compatibility_smoke("ws://localhost:8004", "http://127.0.0.1:3007")

    assert result.rc == 0
    assert "--project=compatibility-smoke" in captured["cmd"]
    assert "--config=playwright.compatibility-smoke.config.mjs" in captured["cmd"]
    assert "--workers=1" in captured["cmd"]
    assert captured["env"]["WS_TEST_URL"] == "ws://localhost:8004"
    assert captured["env"]["PLAYWRIGHT_TEST_BASE_URL"] == "http://127.0.0.1:3007"
    assert captured["env"]["PLAYWRIGHT_JUNIT_OUTPUT_FILE"].endswith("playwright-compatibility-smoke.xml")
    assert captured["timeout"] == 360


def test_playwright_ffmpeg_install_stage_installs_only_ffmpeg(monkeypatch):
    runner = _load_runner()
    captured = {}

    monkeypatch.setattr(runner, "_node_bin_path", lambda name: "playwright.cmd")
    monkeypatch.setattr(runner, "_banner", lambda title: None)

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["label"] = kwargs["label"]
        captured["timeout"] = kwargs["timeout"]
        return 0

    monkeypatch.setattr(runner, "_run", fake_run)

    result = runner._stage_playwright_ffmpeg_install()

    assert result.rc == 0
    assert captured["cmd"] == ["playwright.cmd", "install", "ffmpeg"]
    assert captured["label"] == "playwright install ffmpeg"
    assert captured["timeout"] == 180


def test_playwright_project_empty_shard_env_is_treated_as_unset(monkeypatch, tmp_path, recwarn):
    """Regression: integration.yml passes IJT_PLAYWRIGHT_SHARD='' on non-sharded
    matrix rows; the runner must accept that without warning or sharding."""
    runner = _load_runner()
    captured = {}

    monkeypatch.setattr(runner, "_node_bin_path", lambda name: "playwright.cmd")
    monkeypatch.setattr(runner, "_banner", lambda title: None)
    monkeypatch.setattr(runner, "_RESULTS_DIR", tmp_path)
    monkeypatch.setenv("IJT_PLAYWRIGHT_SHARD", "")
    monkeypatch.delenv("_IJT_RELAUNCHED", raising=False)

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["env"] = kwargs["env"]
        return 0

    monkeypatch.setattr(runner, "_run", fake_run)
    recwarn.clear()

    runner._stage_playwright_project(
        project="features",
        name="playwright-features",
        title="test",
        ws_url="ws://localhost:8005",
        ui_url="http://127.0.0.1:3005",
        workers=2,
    )

    assert not any(arg.startswith("--shard=") for arg in captured["cmd"])
    assert captured["env"]["PLAYWRIGHT_JUNIT_OUTPUT_FILE"].endswith("playwright-features.xml")
    assert not any("IJT_PLAYWRIGHT_SHARD" in str(w.message) for w in recwarn.list), "Empty shard env must not warn"


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
    # Browser e2e CI runs inside the owned `ijt-browser-ci` image (digest
    # pinned in `.github/docker/ijt-browser-ci/image-pin.json`); Chromium is
    # baked into the image and the locked `@playwright/test` version in
    # `package.json` is the single source of truth for the browser bundle.
    # This guard prevents anyone from re-introducing the old image-pin shape
    # that coupled the playwright.config to a specific MCR digest and silently
    # re-coupled CI to a registry SPOF.
    assert "canonicalPlaywrightImage" not in source, (
        "playwright.config.mjs must not export a canonicalPlaywrightImage "
        "metadata field. Browser e2e CI no longer runs inside a job-level "
        "Playwright container; the locked @playwright/test version in "
        "package.json is the single source of truth for the browser bundle."
    )
    assert "mcr.microsoft.com/playwright" not in source, (
        "playwright.config.mjs must not reference an MCR Playwright image "
        "digest. Browser e2e CI runs inside the owned `ijt-browser-ci` "
        "image (digest pinned in `.github/docker/ijt-browser-ci/image-pin.json`); "
        "any MCR reference in the config is stale and misleads contributors."
    )
    assert "baseURL: UI_BASE_URL" in source
    assert "reuseExistingServer: false" in source
    assert re.search(r"retries:\s*0", source)
    assert "fullyParallel: true" in source


def test_docker_smoke_skips_when_docker_engine_is_windows(monkeypatch):
    runner = _load_runner()

    monkeypatch.setattr(runner.shutil, "which", lambda name: "docker" if name == "docker" else None)
    monkeypatch.setattr(
        runner,
        "_docker_linux_engine_skip_note",
        lambda docker: "Docker is running Windows containers; switch Docker Desktop to Linux containers",
    )

    def fail_if_build_runs(*_args, **_kwargs):
        raise AssertionError("docker build should not run when Docker is in Windows-container mode")

    monkeypatch.setattr(runner, "_run", fail_if_build_runs)

    result = runner._stage_docker_smoke()

    assert result.rc == 0
    assert result.skipped
    assert "Windows containers" in result.notes[0]


def test_docker_linux_engine_skip_note_classifies_engine_modes(monkeypatch):
    runner = _load_runner()

    monkeypatch.setattr(runner, "_docker_engine_ostype", lambda docker: "linux")
    assert runner._docker_linux_engine_skip_note("docker") is None

    monkeypatch.setattr(runner, "_docker_engine_ostype", lambda docker: "windows")
    assert "Windows containers" in runner._docker_linux_engine_skip_note("docker")

    monkeypatch.setattr(runner, "_docker_engine_ostype", lambda docker: None)
    assert runner._docker_linux_engine_skip_note("docker") == "Docker daemon OSType could not be determined"


def test_node_tls_download_preflight_reports_corporate_ca_failure(monkeypatch):
    runner = _load_runner()

    class _Result:
        returncode = 1
        stderr = "UNABLE_TO_GET_ISSUER_CERT_LOCALLY"

    monkeypatch.setattr(runner.subprocess, "run", lambda *args, **kwargs: _Result())

    note = runner._node_tls_download_preflight(Path("node"))

    assert note is not None
    assert "UNABLE_TO_GET_ISSUER_CERT_LOCALLY" in note
    assert "NODE_EXTRA_CA_CERTS" in note


def test_node_tls_download_preflight_allows_success(monkeypatch):
    runner = _load_runner()

    class _Result:
        returncode = 0
        stderr = ""

    monkeypatch.setattr(runner.subprocess, "run", lambda *args, **kwargs: _Result())

    assert runner._node_tls_download_preflight(Path("node")) is None


def test_playwright_install_uses_path_node_for_tls_preflight(monkeypatch):
    runner = _load_runner()
    preflight_nodes: list[Path | None] = []

    monkeypatch.setattr(runner, "IS_WINDOWS", True)
    monkeypatch.setattr(runner, "_node_bin_path", lambda name: "playwright.cmd")
    monkeypatch.setattr(runner, "_node_executable_path", lambda: Path("C:/Tools/node.exe"))
    monkeypatch.setattr(runner, "_banner", lambda title: None)
    monkeypatch.setattr(runner, "_warn", lambda message: None)
    monkeypatch.setattr(runner, "_playwright_chromium_available", lambda: False)

    def fake_preflight(node):
        preflight_nodes.append(node)
        return None

    monkeypatch.setattr(runner, "_node_tls_download_preflight", fake_preflight)
    monkeypatch.setattr(runner, "_run", lambda *args, **kwargs: 0)

    result = runner._stage_playwright_install()

    assert result.rc == 0
    assert preflight_nodes == [Path("C:/Tools/node.exe")]


def test_e2e_fixture_passes_runtime_websocket_query():
    source = (_PROJECT_ROOT / "tests" / "e2e" / "e2e-fixtures.mjs").read_text(encoding="utf-8")

    assert "function runtimeAppUrl" in source
    assert "function runtimeForWorker" in source
    assert "function withPortOffset" in source
    assert "testInfo.parallelIndex" in source
    assert "IJT_E2E_BACKEND_WORKERS" in source
    assert "async function waitForBackendReachable" in source
    assert "backendUp: async ({ browserName: _browserName }, use, testInfo)" in source
    assert "wsProtocol" in source
    assert "wsHost" in source
    assert "wsPort" in source
    assert "new AppPage(page, runtime.appUrl)" in source


def test_docker_smoke_builds_web_image_from_repo_root():
    source = (_PROJECT_ROOT / "run_all_tests.py").read_text(encoding="utf-8")

    assert 'str(ROOT.relative_to(_REPO_ROOT) / "Dockerfile")' in source
    assert 'label="docker build (BuildKit)",' in source
    assert "cwd=_REPO_ROOT," in source


def test_joint_demo_uses_server_discovered_joint_ids():
    source = (_PROJECT_ROOT / "src" / "javascripts" / "views" / "standard-demo" / "joint-demo.mjs").read_text(
        encoding="utf-8"
    )

    assert "getMethod('GetJointList')" in source
    assert "_detectedJoints" in source
    assert "this._jointIdForButton(0)" in source
    assert "this._jointIdForButton(1)" in source
    assert "Joint_1" not in source
    assert "Joint_2" not in source


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
    monkeypatch.setattr(runner, "_node_tls_download_preflight", lambda node: None)
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
