from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    script = root / "run_precommit_all.py"
    spec = importlib.util.spec_from_file_location("ijt_run_precommit_all", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_runs_root_then_envelope_when_config_exists(tmp_path, monkeypatch):
    module = _load_module()
    root = tmp_path / "root"
    envelope = (
        root
        / "OPC_UA_Clients"
        / "Release2"
        / "IJT_Web_Client"
        / "src"
        / "javascripts"
        / "views"
        / "envelope"
    )
    envelope.mkdir(parents=True)
    (envelope / ".pre-commit-config.yaml").write_text("repos: []\n", encoding="utf-8")
    monkeypatch.setattr(module, "REPO_ROOT", root)
    monkeypatch.setattr(module, "ENVELOPE_DIR", envelope)
    monkeypatch.setattr(module, "PYTHON_AUDIT_REQUIREMENTS", ())
    monkeypatch.setattr(module, "_precommit_command", lambda: ["pre-commit"])
    monkeypatch.setattr(module, "_run_npm_lock_audit", lambda *args: 0)
    calls = []

    def _run(cmd, cwd):
        calls.append((cmd, cwd))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(module.subprocess, "run", _run)
    assert module.main([]) == 0
    assert calls == [
        (["pre-commit", "run", "--all-files", "--show-diff-on-failure", "--color=always"], root),
        (
            ["pre-commit", "run", "--all-files", "--show-diff-on-failure", "--color=always"],
            envelope,
        ),
    ]


def test_skips_envelope_when_config_missing(tmp_path, monkeypatch):
    module = _load_module()
    root = tmp_path / "root"
    envelope = (
        root
        / "OPC_UA_Clients"
        / "Release2"
        / "IJT_Web_Client"
        / "src"
        / "javascripts"
        / "views"
        / "envelope"
    )
    envelope.mkdir(parents=True)
    monkeypatch.setattr(module, "REPO_ROOT", root)
    monkeypatch.setattr(module, "ENVELOPE_DIR", envelope)
    monkeypatch.setattr(module, "PYTHON_AUDIT_REQUIREMENTS", ())
    monkeypatch.setattr(module, "_precommit_command", lambda: ["pre-commit"])
    monkeypatch.setattr(module, "_run_npm_lock_audit", lambda *args: 0)
    calls = []

    def _run(cmd, cwd):
        calls.append((cmd, cwd))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(module.subprocess, "run", _run)
    assert module.main([]) == 0
    assert calls == [
        (["pre-commit", "run", "--all-files", "--show-diff-on-failure", "--color=always"], root),
    ]


def test_npm_lock_audit_retries_on_network_error(tmp_path, monkeypatch):
    module = _load_module()
    d = tmp_path / "proj"
    d.mkdir()
    (d / "package.json").write_text("{}", encoding="utf-8")
    (d / "package-lock.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(module, "find_cmd", lambda *args: "npm")
    monkeypatch.setattr(module.time, "sleep", lambda *args: None)

    attempts = 0

    def mock_run(cmd, cwd, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return subprocess.CompletedProcess(
                cmd, 1, stdout="", stderr="npm warn audit request failed, reason: read ECONNRESET"
            )
        return subprocess.CompletedProcess(cmd, 0, stdout="{}", stderr="")

    monkeypatch.setattr(module.subprocess, "run", mock_run)
    monkeypatch.delenv("IJT_NPM_AUDIT_MODE", raising=False)
    assert module._run_npm_lock_audit(d, "test-label", retries=3) == 0
    assert attempts == 2


def test_npm_lock_audit_fails_on_network_error_in_strict_mode(tmp_path, monkeypatch):
    module = _load_module()
    d = tmp_path / "proj"
    d.mkdir()
    (d / "package.json").write_text("{}", encoding="utf-8")
    (d / "package-lock.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(module, "find_cmd", lambda *args: "npm")
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda cmd, cwd, **kwargs: subprocess.CompletedProcess(
            cmd, 1, stdout="", stderr="ETIMEDOUT"
        ),
    )
    monkeypatch.setenv("IJT_NPM_AUDIT_MODE", "strict")
    assert module._run_npm_lock_audit(d, "test-label", retries=1) == 1


def test_npm_lock_audit_allows_network_error_in_degraded_mode(tmp_path, monkeypatch):
    module = _load_module()
    d = tmp_path / "proj"
    d.mkdir()
    (d / "package.json").write_text("{}", encoding="utf-8")
    (d / "package-lock.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(module, "find_cmd", lambda *args: "npm")
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda cmd, cwd, **kwargs: subprocess.CompletedProcess(
            cmd, 1, stdout="", stderr="ETIMEDOUT"
        ),
    )
    monkeypatch.setenv("IJT_NPM_AUDIT_MODE", "degraded")
    assert module._run_npm_lock_audit(d, "test-label", retries=1) == 0


def test_audit_failure_returns_non_zero(tmp_path, monkeypatch):
    module = _load_module()
    root = tmp_path / "root"
    monkeypatch.setattr(module, "REPO_ROOT", root)
    monkeypatch.setattr(module, "ENVELOPE_DIR", root / "missing_envelope")
    monkeypatch.setattr(module, "PYTHON_AUDIT_REQUIREMENTS", ())
    monkeypatch.setattr(module, "_precommit_command", lambda: ["pre-commit"])
    monkeypatch.setattr(
        module.subprocess, "run", lambda cmd, cwd: subprocess.CompletedProcess(cmd, 0)
    )
    monkeypatch.setattr(module, "_run_npm_lock_audit", lambda *args: 1)
    assert module.main([]) != 0


def test_csharp_nuget_audit_skipped_when_sln_missing(tmp_path, monkeypatch):
    module = _load_module()
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    assert module._run_csharp_nuget_audit() == 0


def test_csharp_nuget_audit_runs_when_sln_present(tmp_path, monkeypatch):
    module = _load_module()
    sln_dir = tmp_path / "OPC_UA_Clients" / "Release2" / "IJT_CSharp_Client"
    sln_dir.mkdir(parents=True)
    sln = sln_dir / "IJT_CSharp_Client.sln"
    sln.write_text("Microsoft Visual Studio Solution File", encoding="utf-8")
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(module, "find_cmd", lambda *args: "dotnet")

    called_cmd = []

    def mock_run(cmd, cwd, capture_output=False, text=False, timeout=None):
        called_cmd.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="No vulnerable packages", stderr="")

    monkeypatch.setattr(module.subprocess, "run", mock_run)
    assert module._run_csharp_nuget_audit() == 0
    assert len(called_cmd) == 1
    assert "package" in called_cmd[0] and "--vulnerable" in called_cmd[0]
