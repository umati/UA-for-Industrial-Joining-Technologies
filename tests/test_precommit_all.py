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
